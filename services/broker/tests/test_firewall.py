import json

import httpx
import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.policy import MODEL
from immortility_broker.contracts import TaskRequest
from pydantic import SecretStr


def grant(app):
    if not app.state.engine.settings.openrouter_api_key.get_secret_value():
        app.state.engine.settings.openrouter_api_key = SecretStr("synthetic-offline-credential")
    store = app.state.store
    session = store.session()["id"]
    task, _ = store.create(
        TaskRequest(session_id=session, request_id="fixture", content="test", cloud_consent=True)
    )
    app.state.engine.open_grant(task["task_id"], "fast", 90)
    return app.state.engine.inference_key


@pytest.mark.parametrize("provider_status", [429, 402, 503])
def test_real_http_policy_no_paid_fallback_or_upstream_error_leak(tmp_path, provider_status):
    outbound = []

    def upstream(request):
        outbound.append(request)
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        return httpx.Response(provider_status, json={"error": "private-upstream-error"})

    settings = Settings(_env_file=None, data_dir=tmp_path, openrouter_api_key="private-test-key")
    app = create_app(
        settings, "x" * 40, client=httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    )
    with TestClient(app) as client:
        token = grant(app)
        response = client.post(
            "/inference/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "test"}],
                "models": ["paid"],
                "plugins": ["web"],
            },
        )
        assert response.status_code == 503
        assert "private" not in response.text
        assert len(outbound) == 2
        sent = json.loads(outbound[1].content)
        assert sent["model"] == MODEL and "models" not in sent and "plugins" not in sent
        assert app.state.engine.provider_error.code == (
            "quota_exhausted" if provider_status == 429 else "provider_rejected"
        )
        app.state.engine.inference_allowed = False


def test_nonzero_catalog_prevents_any_completion(tmp_path):
    outbound = []

    def upstream(request):
        outbound.append(request)
        return httpx.Response(
            200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0.001"}}]}
        )

    app = create_app(
        Settings(_env_file=None, data_dir=tmp_path),
        "x" * 40,
        client=httpx.AsyncClient(transport=httpx.MockTransport(upstream)),
    )
    with TestClient(app) as client:
        token = grant(app)
        response = client.post(
            "/inference/v1/chat/completions",
            headers={"Authorization": "Bearer " + token},
            json={"model": MODEL, "messages": []},
        )
        assert response.status_code == 409
        assert len(outbound) == 1 and outbound[0].method == "GET"
        app.state.engine.calls = 2
        assert (
            client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + token},
                json={},
            ).status_code
            == 403
        )
        assert len(outbound) == 1
