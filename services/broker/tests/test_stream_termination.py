from provider_fixtures import free_account_response

import asyncio
import json

import httpx
from pydantic import SecretStr
import pytest

from immortility_broker.app import create_app
from immortility_broker.contracts import TaskRequest
from immortility_broker.config import Settings
from immortility_broker.policy import MODEL


@pytest.mark.parametrize(
    "case,termination",
    [
        ("json", "json_decode"),
        ("deep_json", "json_decode"),
        ("truncated", "truncated_sse"),
        ("provider", "provider_error"),
        ("transport", "stream_transport"),
        ("timeout", "stream_timeout"),
        ("cancel", "cancelled"),
        ("semantic_limit", "bridge_output_limit"),
        ("missing_usage", "completed"),
    ],
)
async def test_every_stream_termination_settles_usage_and_keeps_only_safe_metadata(
    tmp_path, case, termination
):
    entered = asyncio.Event()

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            if case == "json":
                yield b"data: {invalid\n\n"
            elif case == "deep_json":
                yield b'data: {"choices":' + b"[" * 3000 + b"0" + b"]" * 3000 + b"}\n\n"
            elif case == "provider":
                yield b'data: {"error":{"code":"context_length_exceeded","message":"PRIVATE_CANARY"}}\n\n'
            elif case == "semantic_limit":
                for _ in range(2):
                    yield (
                        "data: "
                        + json.dumps({"choices": [{"index": 0, "delta": {"content": "x" * 65000}}]})
                        + "\n\n"
                    ).encode()
            elif case in {"transport", "timeout", "cancel"}:
                entered.set()
                if case == "transport":
                    raise httpx.ReadError("PRIVATE_CANARY")
                if case == "timeout":
                    raise httpx.ReadTimeout("PRIVATE_CANARY")
                await asyncio.sleep(60)
            else:
                yield b'data: {"choices":[{"index":0,"delta":{"content":"public fixture"},"finish_reason":"stop"}]}\n\n'
                if case == "missing_usage":
                    yield b"data: [DONE]\n\n"

    def upstream(request):
        if request.url.path == "/api/v1/key":
            return free_account_response(request)
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        return httpx.Response(200, stream=Stream(), headers={"content-type": "text/event-stream"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_app(
        Settings(
            _env_file=None,
            data_dir=tmp_path,
            openrouter_fallback_enabled=True,
            openrouter_api_key=SecretStr("synthetic-fixture-key"),
        ),
        "x" * 40,
        client=http,
    )
    store, engine = app.state.store, app.state.engine
    task, _ = store.create(
        TaskRequest(
            session_id=store.session()["id"],
            request_id=case,
            content="Public fixture",
            cloud_consent=True,
            allowed_capabilities=["clock.now.v1"],
        )
    )
    tid = task["task_id"]
    engine.open_grant(tid, "fast", 30)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            operation = asyncio.create_task(
                client.post(
                    "/inference/v1/chat/completions",
                    headers={"Authorization": "Bearer " + engine.inference_key},
                    json={
                        "model": MODEL,
                        "messages": [{"role": "user", "content": "Public fixture"}],
                    },
                )
            )
            if case == "cancel":
                await asyncio.wait_for(entered.wait(), 3)
                operation.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await operation
            else:
                response = await operation
                assert "PRIVATE_CANARY" not in response.text
        notices = [
            json.loads(row[0])["data"]
            for row in store.db.execute("SELECT body FROM events WHERE task_id=?", (tid,))
        ]
        diagnostic = next(
            value for value in notices if value.get("name") == "provider_call_diagnostics"
        )
        assert diagnostic["termination"] == termination
        assert diagnostic["usage_status"] == "unknown"
        assert diagnostic["max_tokens"] > 0 and diagnostic["input_reserved"] > 0
        assert diagnostic["http_status"] == 200 and diagnostic["dispatch_attempted"] is True
        assert diagnostic["provider_error_category"] == (
            "context_length_exceeded" if case == "provider" else None
        )
        assert "PRIVATE_CANARY" not in json.dumps(notices)
        assert store.ledger.summary(tid)["unknown_calls"] == 1
        assert store.ledger.summary(tid)["charged_tokens"] > 0
    finally:
        await http.aclose()
        store.db.close()


async def test_cancelled_preflight_is_provably_unsent_and_releases_its_reservation(tmp_path):
    entered = asyncio.Event()

    async def upstream(request):
        assert request.method == "GET"
        entered.set()
        await asyncio.sleep(60)
        raise AssertionError("Cancelled preflight continued")

    http = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_app(
        Settings(
            _env_file=None,
            data_dir=tmp_path,
            openrouter_fallback_enabled=True,
            openrouter_api_key=SecretStr("synthetic-fixture-key"),
        ),
        "x" * 40,
        client=http,
    )
    store, engine = app.state.store, app.state.engine
    task, _ = store.create(
        TaskRequest(
            session_id=store.session()["id"],
            request_id="preflight-cancel",
            content="Public fixture",
            cloud_consent=True,
        )
    )
    tid = task["task_id"]
    engine.open_grant(tid, "fast", 30)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            operation = asyncio.create_task(
                client.post(
                    "/inference/v1/chat/completions",
                    headers={"Authorization": "Bearer " + engine.inference_key},
                    json={"model": MODEL, "messages": []},
                )
            )
            await asyncio.wait_for(entered.wait(), 3)
            operation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await operation
        usage = store.ledger.summary(tid)
        assert (
            usage["charged_tokens"] == 0
            and usage["not_sent_calls"] == 1
            and usage["unknown_calls"] == 0
        )
        notices = [
            json.loads(row[0])["data"]
            for row in store.db.execute("SELECT body FROM events WHERE task_id=?", (tid,))
        ]
        assert any(
            n.get("termination") == "preflight_cancelled" and n.get("dispatch_attempted") is False
            for n in notices
        )
    finally:
        await http.aclose()
        store.db.close()
