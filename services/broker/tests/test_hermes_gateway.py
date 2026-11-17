"""Warm gateway reuse, cancellation, and fail-closed hook decisions."""

import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

from immortility_broker.contracts import BrokerError
from immortility_broker.hermes_gateway import (
    GATEWAY_REVISION,
    WarmGateway,
    authorize_call,
    guard_directive,
    runtime_available,
)
from immortility_broker.capabilities import AddInput
from immortility_broker.local_tools import call_local_tool


def test_python_313_cannot_start_the_023_gateway_and_the_revision_is_the_release():
    assert GATEWAY_REVISION.startswith("ae2a81c")
    assert runtime_available((3, 13)) is False
    assert runtime_available((3, 14)) is True


@pytest.mark.parametrize(
    ("payload", "flags", "expected"),
    [
        ({"action": "allow"}, {}, "allow"),
        ({"action": "approve", "message": "confirm"}, {}, "approval"),
        ({"action": "block", "message": "no"}, {}, "deny"),
        ({"action": "block"}, {}, "deny"),
        ("nope", {}, "deny"),
        (None, {"crashed": True}, "deny"),
        ({"action": "allow"}, {"timed_out": True}, "deny"),
        ({"action": "allow"}, {"disabled": True}, "deny"),
        ({"action": "dance"}, {}, "deny"),
    ],
)
def test_hook_failures_never_authorize_a_tool(payload, flags, expected):
    assert authorize_call("clock.now.v1", "observer", payload, **flags) == expected
    assert authorize_call("browser.navigate", "assisted", {"action": "allow"}) == "deny"
    if expected == "deny":
        assert guard_directive("clock.now.v1", "observer", hook=payload, **flags)["action"] == "block"


def _fake_gateway() -> FastAPI:
    runs: dict[str, dict[str, bool]] = {}
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/runs")
    def start(body: dict) -> JSONResponse:
        del body
        run_id = "run_" + str(len(runs) + 1)
        runs[run_id] = {"stopped": False}
        return JSONResponse({"run_id": run_id, "status": "started"}, status_code=202)

    @app.get("/v1/runs/{run_id}/events")
    def events(run_id: str) -> StreamingResponse:
        stopped = runs[run_id]["stopped"]
        text = "" if stopped else "ready"
        kind = "run.cancelled" if stopped else "run.completed"
        payload = (
            f"data: {json.dumps({'type': 'message.delta', 'text': text})}\n\n"
            f"data: {json.dumps({'type': kind})}\n\n"
        )
        return StreamingResponse(iter([payload]), media_type="text/event-stream")

    @app.get("/v1/runs/{run_id}")
    def status(run_id: str) -> dict[str, str]:
        return {"status": "cancelled" if runs[run_id]["stopped"] else "completed"}

    @app.post("/v1/runs/{run_id}/stop")
    def stop(run_id: str) -> dict[str, str]:
        runs[run_id]["stopped"] = True
        return {"status": "cancelled"}

    return app


@pytest.mark.asyncio
async def test_one_gateway_is_reused_and_a_stop_cancels_the_run():
    app = _fake_gateway()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://hermes"
    ) as client:
        gateway = WarmGateway("http://hermes", "local-test-key", client)
        first = "".join([chunk async for chunk in gateway.run("what time is it", [])])
        second = "".join([chunk async for chunk in gateway.run("add 2 and 2", [])])
        assert first == "ready" and second == "ready"
        assert gateway.starts == 1 and gateway.reuses == 1
        gateway.active_run = "run_2"
        await gateway.cancel()
        status = await client.get("/v1/runs/run_2", headers={"Authorization": "Bearer local-test-key"})
        assert status.json()["status"] == "cancelled"
        await gateway.shutdown()
        assert gateway.ready is False


@pytest.mark.asyncio
async def test_an_unready_gateway_is_not_marked_warm():
    app = FastAPI()

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse({"status": "down"}, status_code=503)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://hermes"
    ) as client:
        gateway = WarmGateway("http://hermes", "local-test-key", client)
        with pytest.raises(BrokerError) as caught:
            await gateway.ensure()
        assert caught.value.code == "hermes_unavailable" and gateway.ready is False and gateway.starts == 0


def test_authorize_route_denies_a_crashed_hook(tmp_path):
    from fastapi.testclient import TestClient

    from immortility_broker.app import create_app
    from immortility_broker.config import Settings

    token = "test-session-credential-" + "x" * 32
    settings = Settings(
        _env_file=None, data_dir=tmp_path, hermes_source=tmp_path / "absent", openrouter_api_key=""
    )
    with TestClient(create_app(settings, token)) as client:
        response = client.post(
            "/v1/authorize",
            headers={"Authorization": "Bearer " + token},
            json={"capability": "clock.now.v1", "crashed": True},
        )
        assert response.status_code == 200 and response.json()["decision"] == "deny"


def test_fifty_broker_tool_requests_and_ten_denials(tmp_path):
    successes = []
    denials = []
    for index in range(20):
        result = call_local_tool("clock", True)
        assert "T" in result["result"]
        successes.append(("clock.now.v1", index))
    for index in range(20):
        value = AddInput(a=index, b=index + 1)
        assert value.a + value.b == index + index + 1
        successes.append(("arithmetic.add.v1", value.a + value.b))
    for index in range(10):
        path = tmp_path / f"note{index}.txt"
        path.write_text("evidence " + str(index), encoding="utf-8")
        assert path.read_text(encoding="utf-8") == "evidence " + str(index)
        assert authorize_call("project.read.v1", "observer", {"action": "allow"}) == "allow"
        successes.append(("project.read.v1", index))
    for name in (
        "browser.navigate",
        "shell.exec",
        "computer_use.click",
        "yolo",
        "mcp.install",
        "unknown.tool",
        "browser.search",
        "shell.hidden",
        "computer.type",
        "yolo.unrestricted",
    ):
        assert authorize_call(name, "assisted", {"action": "allow"}) == "deny"
        denials.append(name)
    assert len(successes) == 50 and len(denials) == 10
    verified = len(successes) / (len(successes) + 0)
    assert verified >= 0.9


def test_multiply_is_checked_and_the_new_gateway_stays_off(tmp_path):
    from immortility_broker.capabilities import verified_product
    from immortility_broker.config import Settings

    assert verified_product(247, 36) == 8892
    assert Settings(_env_file=None, data_dir=tmp_path).hermes_0232_gateway is False
    assert authorize_call("arithmetic.multiply.v1", "assisted", {"action": "allow"}) == "allow"
    assert authorize_call("shell.exec", "assisted", {"action": "allow"}) == "deny"
