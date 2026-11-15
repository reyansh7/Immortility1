"""Content-free provider diagnostics and trusted identity configuration regressions."""

from provider_fixtures import free_account_response

import asyncio

import httpx
import pytest

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.hermes import capability_context
from immortility_broker.policy import MODEL
from test_inference_grants import grant


def test_capability_snapshot_is_bounded_truthful_and_has_no_credentials(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path, openrouter_api_key="SECRET_CANARY")
    text = capability_context(settings)
    assert "SECRET_CANARY" not in text and len(text) < 1200
    assert "local clock=disabled" in text and "Wikipedia lookup=disabled" in text
    assert "not tools you can call directly" in text
    settings.local_tools_enabled = True
    settings.web_research_enabled = True
    settings.workspace_tools_enabled = True
    text = capability_context(settings)
    assert "local clock=enabled" in text and "Wikipedia lookup=enabled" in text
    assert "workspace edit proposals=disabled" in text  # No approved folder.
    settings.workspace_root = tmp_path
    assert "workspace edit proposals=enabled" in capability_context(settings)


def test_lower_call_ceiling_is_enforced_by_the_durable_ledger(tmp_path):
    from immortility_broker.contracts import BrokerError

    app = create_app(Settings(_env_file=None, data_dir=tmp_path, model_call_cap=1), "x" * 40)
    try:
        task_id, _ = grant(app, "one-call")
        engine = app.state.engine
        assert engine.call_limit == 1
        ledger = app.state.store.ledger
        ledger.reserve(engine.attempt_id, 10, 100)
        with pytest.raises(BrokerError):
            ledger.reserve(engine.attempt_id, 10, 100)
        assert ledger.summary(task_id)["calls"] == 1
    finally:
        app.state.store.db.close()


@pytest.mark.parametrize(
    "body",
    [
        "data: {bad SECRET_CANARY}\n\n",
        'data: {"error":{"message":"SECRET_CANARY"}}\n\n',
        "data: []\n\n",
    ],
)
async def test_stream_error_is_classified_without_leaking_upstream_body(tmp_path, body):
    def provider(request):
        if request.url.path == "/api/v1/key":
            return free_account_response(request)
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, client=upstream)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            task_id, key = grant(app, "stream")
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + key},
                json={"model": MODEL, "messages": []},
            )
            assert "CANARY" not in response.text
            issue = app.state.engine.provider_error
            assert issue.code == "provider_stream_failed" and "CANARY" not in issue.message
            assert app.state.store.ledger.summary(task_id)["unknown_calls"] == 1
    finally:
        await upstream.aclose()
        app.state.store.db.close()


async def test_old_rejected_completion_cannot_poison_a_new_task(tmp_path):
    entered, release = asyncio.Event(), asyncio.Event()

    async def provider(request):
        if request.url.path == "/api/v1/key":
            return free_account_response(request)
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        entered.set()
        await release.wait()
        return httpx.Response(503, text="SECRET_CANARY")

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, client=upstream)
    try:
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
            assert response.status_code == 503 and "CANARY" not in response.text
            assert app.state.engine.provider_error is None
            assert app.state.store.ledger.summary(first)["unknown_calls"] == 1
            assert app.state.store.ledger.summary(second)["calls"] == 0
    finally:
        await upstream.aclose()
        app.state.store.db.close()
