import time

import pytest
from pydantic import ValidationError

from immortility_broker.capabilities import Capability, ClockOutput, EmptyInput, Grant, Registration
from immortility_broker.contracts import BrokerError
from test_standard_mcp import setup_gateway


async def test_exact_arguments_and_capability_cannot_be_swapped(tmp_path):
    gateway, grant = setup_gateway(tmp_path)
    try:
        token = gateway.issue(grant, {"a": 1, "b": 2}, enabled=True)
        with pytest.raises(BrokerError, match="tool_denied"):
            await gateway.invoke(token, "arithmetic.add.v1", {"a": 10, "b": 20}, enabled=True)
        with pytest.raises(BrokerError, match="tool_denied"):
            await gateway.invoke(token, "terminal", {}, enabled=True)
        assert await gateway.invoke(token, "arithmetic.add.v1", {"a": 1, "b": 2}, enabled=True) == {
            "result": 3
        }
    finally:
        gateway.store.db.close()


def test_progressive_discovery_returns_only_registered_enabled_requested_schemas(tmp_path):
    gateway, _ = setup_gateway(tmp_path)

    async def clock(arguments):
        return {"timestamp": "2026-11-14T00:00:00+00:00"}

    gateway.register(
        Registration(
            Capability(name="clock.now.v1", provider="local-python"),
            EmptyInput,
            ClockOutput,
            clock,
            lambda: False,
        )
    )
    try:
        assert gateway.discover(("terminal", "clock.now.v1")) == []
        selected = gateway.discover(("arithmetic.add.v1",))
        assert [entry["manifest"]["name"] for entry in selected] == ["arithmetic.add.v1"]
        selected[0]["manifest"]["name"] = "mutated external data"
        assert (
            gateway.discover(("arithmetic.add.v1",))[0]["manifest"]["name"] == "arithmetic.add.v1"
        )
        with pytest.raises(ValueError, match="unique"):
            gateway.register(gateway.registrations["arithmetic.add.v1"])
        with pytest.raises(ValidationError):
            Capability(network=True)
        with pytest.raises(ValidationError):
            Capability(irreversible=True)
    finally:
        gateway.store.db.close()


async def test_feature_revocation_and_foreign_attempt_are_checked_at_dispatch(tmp_path):
    gateway, grant = setup_gateway(tmp_path)
    token = gateway.issue(grant, {"a": 1, "b": 2}, enabled=True)
    registration = gateway.registrations[grant.capability]
    from dataclasses import replace

    gateway.registrations[grant.capability] = replace(registration, enabled=lambda: False)
    try:
        with pytest.raises(BrokerError, match="tool_denied"):
            await gateway.invoke(token, grant.capability, {"a": 1, "b": 2}, enabled=True)
        gateway.registrations[grant.capability] = registration
        with pytest.raises(BrokerError, match="tool_denied"):
            gateway.issue(
                grant.model_copy(update={"attempt_id": "foreign"}), {"a": 1, "b": 2}, enabled=True
            )
    finally:
        gateway.store.db.close()


async def test_invalid_or_secret_error_output_is_redacted_and_finishes_trace(tmp_path):
    async def bad(arguments):
        return {"result": "SECRET_CANARY"}

    gateway, grant = setup_gateway(tmp_path, bad)
    try:
        token = gateway.issue(grant, {"a": 1, "b": 2}, enabled=True)
        with pytest.raises(BrokerError, match="tool_output_invalid") as result:
            await gateway.invoke(token, grant.capability, {"a": 1, "b": 2}, enabled=True)
        assert "CANARY" not in result.value.message
        completed = [
            e for e in gateway.store.events(grant.task_id) if e["type"] == "tool.completed"
        ]
        assert completed[-1]["data"]["status"] == "error"
        assert "CANARY" not in str(completed)
    finally:
        gateway.store.db.close()


async def test_controller_wait_respects_grant_deadline(tmp_path):
    gateway, grant = setup_gateway(tmp_path)
    grant = grant.model_copy(update={"expires": time.monotonic() + 0.02})
    token = gateway.issue(grant, {"a": 1, "b": 2}, enabled=True)
    await gateway.lock.acquire()
    try:
        with pytest.raises(BrokerError, match="timeout"):
            await gateway.invoke(token, grant.capability, {"a": 1, "b": 2}, enabled=True)
    finally:
        gateway.lock.release()
        gateway.store.db.close()


def test_registry_does_not_accept_unbounded_or_nonfinite_grants(tmp_path):
    gateway, grant = setup_gateway(tmp_path)
    try:
        with pytest.raises(ValidationError):
            Grant(**(grant.model_dump() | {"expires": float("nan")}))
    finally:
        gateway.store.db.close()


def test_real_production_clock_route_requires_no_model_or_hermes(tmp_path):
    from datetime import datetime, timezone
    from fastapi.testclient import TestClient
    from immortility_broker.app import create_app
    from immortility_broker.config import Settings
    from test_workspace import AUTH, TOKEN, _wait

    app = create_app(
        Settings(
            _env_file=None,
            data_dir=tmp_path,
            local_tools_enabled=True,
            hermes_source=tmp_path / "absent",
        ),
        TOKEN,
    )
    with TestClient(app) as client:
        sid = client.post("/v1/sessions", headers=AUTH).json()["id"]
        task_id = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": sid,
                "request_id": "time",
                "content": "what time is it?",
                "cloud_consent": True,
            },
        ).json()["task_id"]
        task = _wait(client, task_id, {"succeeded", "failed", "blocked", "disconnected"})
        assert task["status"] == "succeeded", task.get("error")
        assert task["result"]["model"] == "clock.now.v1"
        parsed = datetime.fromisoformat(task["result"]["text"].removeprefix("UTC time: "))
        assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 3
        assert app.state.store.ledger.summary(task_id)["calls"] == 0
        assert (
            client.get(f"/v1/tasks/{task_id}/trace", headers=AUTH).json()["agent"]["route"]
            == "clock.now.v1"
        )
