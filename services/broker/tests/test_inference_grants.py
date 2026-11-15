import asyncio
import json

import httpx

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import TaskRequest
from immortility_broker.policy import MODEL
from immortility_broker.policy import guard_secret_egress
from immortility_broker.contracts import BrokerError
import pytest
from pydantic import SecretStr


def grant(app, name):
    # These fixtures use an injected MockTransport, never a real credential.
    app.state.engine.settings.openrouter_api_key = SecretStr("synthetic-offline-credential")
    session = app.state.store.session()["id"]
    task, _ = app.state.store.create(
        TaskRequest(session_id=session, request_id=name, content="synthetic", cloud_consent=True)
    )
    app.state.engine.open_grant(task["task_id"], "fast", 90)
    return task["task_id"], app.state.engine.inference_key


async def test_revoked_preflight_cannot_send_or_poison_the_following_task(tmp_path):
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def provider(request):
        calls.append(request.method)
        entered.set()
        await release.wait()
        return httpx.Response(503, json={"private": "SECRET_CANARY"})

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, client=upstream)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
    ) as client:
        first, key = grant(app, "first")
        old = asyncio.create_task(
            client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + key},
                json={"model": MODEL, "messages": []},
            )
        )
        await entered.wait()
        second, _ = grant(app, "second")
        release.set()
        response = await old
        assert response.status_code >= 400 and "CANARY" not in response.text
        assert app.state.engine.provider_error is None
        assert calls == ["GET"]
        assert app.state.store.ledger.summary(first)["charged_tokens"] == 0
        assert app.state.store.ledger.summary(second)["calls"] == 0
        assert (
            await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + key},
                json={},
            )
        ).status_code == 401
    await upstream.aclose()
    app.state.store.db.close()


async def test_credential_rotation_during_preflight_never_switches_account(tmp_path):
    entered, release = asyncio.Event(), asyncio.Event()
    methods = []

    async def provider(request):
        methods.append(request.method)
        entered.set()
        await release.wait()
        return httpx.Response(
            200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
        )

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, client=upstream)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            tid, key = grant(app, "rotation")
            operation = asyncio.create_task(
                client.post(
                    "/inference/v1/chat/completions",
                    headers={"Authorization": "Bearer " + key},
                    json={"model": MODEL, "messages": []},
                )
            )
            await asyncio.wait_for(entered.wait(), 2)
            app.state.engine.settings.openrouter_api_key = SecretStr(
                "new-synthetic-offline-credential"
            )
            release.set()
            response = await operation
            assert response.status_code == 403 and methods == ["GET"]
            assert app.state.store.ledger.summary(tid)["charged_tokens"] == 0
            assert app.state.store.ledger.summary(tid)["dispatch_attempts"] == 0
            assert app.state.store.ledger.summary(tid)["not_sent_calls"] == 1
    finally:
        await upstream.aclose()
        app.state.store.db.close()


@pytest.mark.parametrize(
    "value",
    ["known-synthetic-key-without-any-prefix", "-----BEGIN PRIVATE KEY-----", "ghp_" + "x" * 36],
)
def test_secrets_in_documents_or_prompts_are_denied_without_echo(value):
    with pytest.raises(BrokerError, match="secret_egress_denied") as captured:
        guard_secret_egress(
            [{"role": "user", "content": "source: " + value}],
            ["known-synthetic-key-without-any-prefix"],
        )
    assert value not in captured.value.message


async def test_transport_error_is_unknown_and_usage_endpoint_contains_no_content(tmp_path):
    def provider(request):
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        raise httpx.ConnectError("SECRET_CANARY", request=request)

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, client=upstream)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
    ) as client:
        task_id, key = grant(app, "error")
        response = await client.post(
            "/inference/v1/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={"model": MODEL, "messages": [{"role": "user", "content": "PRIVATE_PROMPT"}]},
        )
        assert response.status_code == 503 and "CANARY" not in response.text
        usage = await client.get(
            f"/v1/tasks/{task_id}/usage", headers={"Authorization": "Bearer " + "x" * 40}
        )
        assert usage.status_code == 200
        assert "PRIVATE_PROMPT" not in usage.text
        body = json.loads(usage.text)
        assert body["summary"]["unknown_calls"] == 1
        assert body["summary"]["charged_tokens"] > 0
    await upstream.aclose()
    app.state.store.db.close()
