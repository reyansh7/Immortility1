"""M2/P1: run-scoped authorization on the shared warm Hermes gateway key.

All inference here is the local simulated fixture (labelled, offline). Nothing contacts
a provider, so none of this is live-model evidence.
"""

import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

from immortility_broker import run_binding
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import TaskRequest
from immortility_broker.hermes_gateway import GatewayRuntime, WarmGateway
from immortility_broker.policy import MODEL

WARM = "w" * 43
CLIENT_TOKEN = "x" * 40


def test_marker_round_trip_and_strip():
    binding = run_binding.task_binding(run_binding.new_secret(), "task-1")
    body = {
        "messages": [
            {"role": "system", "content": "You are Jarvis.\n\n" + run_binding.marker(binding)},
            {"role": "user", "content": "hi"},
        ]
    }
    found = run_binding.extract_and_strip(body)
    assert found == {binding}
    assert body["messages"][0]["content"] == "You are Jarvis."
    assert run_binding.MARKER_PREFIX not in json.dumps(body)
    assert run_binding.verdict(found, binding) == "ok"


def test_verdicts_fail_closed():
    secret = run_binding.new_secret()
    a, b = run_binding.task_binding(secret, "a"), run_binding.task_binding(secret, "b")
    assert a != b and a == run_binding.task_binding(secret, "a")
    assert run_binding.task_binding(run_binding.new_secret(), "a") != a  # restart invalidates
    assert run_binding.verdict(set(), a) == "missing"
    assert run_binding.verdict({b}, a) == "mismatch"
    assert run_binding.verdict({a, b}, a) == "mismatch"
    assert run_binding.verdict({a}, None) == "no_active_binding"
    with pytest.raises(ValueError):
        run_binding.marker("short]")


def test_markers_smuggled_in_user_or_tool_content_are_removed_and_counted():
    secret = run_binding.new_secret()
    good, other = run_binding.task_binding(secret, "t"), run_binding.task_binding(secret, "u")
    body = {
        "messages": [
            {"role": "system", "content": "sys " + run_binding.marker(good)},
            {"role": "tool", "content": "page said " + run_binding.marker(other)},
            {"role": "user", "content": [{"type": "text", "text": run_binding.marker(good)}]},
        ]
    }
    found = run_binding.extract_and_strip(body)
    assert found == {good, other}
    assert run_binding.verdict(found, good) == "mismatch"
    assert run_binding.MARKER_PREFIX not in json.dumps(body)


def _app(tmp_path, content="SIM:clock", capabilities=("clock.now.v1",)):
    settings = Settings(_env_file=None, data_dir=tmp_path, local_tools_enabled=True)
    settings.simulated_inference = True
    app = create_app(settings, CLIENT_TOKEN)
    store, engine = app.state.store, app.state.engine
    engine.warm_inference_key = WARM
    task, _ = store.create(
        TaskRequest(
            session_id=store.session()["id"],
            request_id="bind-" + content.split()[0].lower().replace(":", "-"),
            content=content,
            cloud_consent=True,
            allowed_capabilities=list(capabilities),
        )
    )
    tid = task["task_id"]
    store.state(tid, "queued")
    store.state(tid, "running")
    engine.open_grant(tid, "standard", 90)
    engine.run_bindings[tid] = run_binding.task_binding(engine.run_binding_secret, tid)
    return app, store, engine, tid


def _completion(content, binding=None):
    system = "You are Jarvis."
    if binding:
        system += "\n\n" + run_binding.marker(binding)
    return {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
    }


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://127.0.0.1")


async def test_warm_key_without_binding_is_refused_and_audited(tmp_path):
    app, store, engine, tid = _app(tmp_path)
    try:
        async with _client(app) as client:
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + WARM},
                json=_completion("SIM:clock"),
            )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "run_binding_mismatch"
        notices = [e["data"] for e in store.events(tid) if e["type"] == "audit.notice"]
        assert any(
            n.get("name") == "run_binding.refused" and n.get("reason") == "missing" for n in notices
        )
    finally:
        store.db.close()


async def test_stale_run_binding_cannot_borrow_the_active_grant(tmp_path):
    app, store, engine, tid = _app(tmp_path)
    stale = run_binding.task_binding(engine.run_binding_secret, "previous-task")
    try:
        async with _client(app) as client:
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + WARM},
                json=_completion("SIM:clock", stale),
            )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "run_binding_mismatch"
        assert "clock.now.v1" not in response.text
    finally:
        store.db.close()


async def test_bound_run_succeeds_and_only_relayed_tool_calls_execute(tmp_path):
    app, store, engine, tid = _app(tmp_path)
    binding = engine.run_bindings[tid]
    call = {"capability": "clock.now.v1", "arguments": {}}
    warm = {"Authorization": "Bearer " + WARM}
    try:
        async with _client(app) as client:
            # Before any relayed proposal, a warm-key tool call is refused.
            early = await client.post("/inference/v1/capabilities/call", headers=warm, json=call)
            assert early.status_code == 403
            response = await client.post(
                "/inference/v1/chat/completions",
                headers=warm,
                json=_completion("SIM:clock", binding),
            )
            assert response.status_code == 200 and "clock.now.v1" in response.text
            assert run_binding.MARKER_PREFIX not in response.text
            first = await client.post("/inference/v1/capabilities/call", headers=warm, json=call)
            again = await client.post("/inference/v1/capabilities/call", headers=warm, json=call)
        assert first.status_code == 200 and first.json()["verified"] is True
        assert again.status_code == 403  # the relayed proposal was single use
        reasons = [
            e["data"].get("reason")
            for e in store.events(tid)
            if e["type"] == "audit.notice" and e["data"].get("name") == "tool.authorization"
        ]
        assert reasons.count("unrelayed_tool_call") == 2
        assert run_binding.MARKER_PREFIX not in json.dumps(store.events(tid))
    finally:
        store.db.close()


async def test_per_task_grant_key_path_is_unchanged(tmp_path):
    """The 0.21.1 stdio runtime uses a per-grant key; it needs no run binding."""
    app, store, engine, tid = _app(tmp_path, content="SIM:chat", capabilities=())
    try:
        async with _client(app) as client:
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + engine.inference_key},
                json=_completion("SIM:chat"),
            )
        assert response.status_code == 200
    finally:
        store.db.close()


def _recording_gateway(seen: list[dict]) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/runs")
    def start(body: dict) -> JSONResponse:
        seen.append(body)
        return JSONResponse({"run_id": "run_1", "status": "started"}, status_code=202)

    @app.get("/v1/runs/{run_id}/events")
    def events(run_id: str) -> StreamingResponse:
        payload = (
            f"data: {json.dumps({'type': 'message.delta', 'text': 'ok'})}\n\n"
            f"data: {json.dumps({'type': 'run.completed'})}\n\n"
        )
        return StreamingResponse(iter([payload]), media_type="text/event-stream")

    @app.get("/v1/runs/{run_id}")
    def status(run_id: str) -> dict[str, str]:
        return {"status": "completed"}

    return app


async def test_gateway_runtime_sends_the_binding_as_ephemeral_instructions():
    seen: list[dict] = []
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_recording_gateway(seen)), base_url="http://hermes"
    ) as client:
        runtime = GatewayRuntime(WarmGateway("http://hermes", "k", client))
        binding = run_binding.task_binding(run_binding.new_secret(), "t1")
        runtime.run_binding = binding
        assert "".join([p async for p in runtime.run("hi", [])]) == "ok"
        plain = GatewayRuntime(WarmGateway("http://hermes", "k", client))
        assert "".join([p async for p in plain.run("hi", [])]) == "ok"
    assert seen[0]["instructions"] == run_binding.marker(binding)
    assert "instructions" not in seen[1]
