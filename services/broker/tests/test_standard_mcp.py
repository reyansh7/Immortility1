import asyncio
import time

import pytest

from immortility_broker.capabilities import (
    AddInput,
    AddOutput,
    Capability,
    Gateway,
    Grant,
    Registration,
)
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError, TaskRequest
from immortility_broker.standard_mcp import reviewed_runtime, sdk_request
from immortility_broker.store import Store

try:
    reviewed_runtime()
except BrokerError:
    REVIEWED_MCP_RUNTIME_AVAILABLE = False
else:
    REVIEWED_MCP_RUNTIME_AVAILABLE = True


@pytest.mark.skipif(
    not REVIEWED_MCP_RUNTIME_AVAILABLE,
    reason="Reviewed MCP runtime is unavailable in this environment",
)
async def test_real_official_sdk_stdio_discovery_and_call():
    tools = await sdk_request("discover", enabled=True)
    assert [t["name"] for t in tools["tools"]] == ["add"]
    assert await sdk_request("add", 7, 8, enabled=True) == {"result": {"result": 15}}


async def test_standard_mcp_denies_default_and_forbidden_operation():
    with pytest.raises(BrokerError, match="tool_denied"):
        await sdk_request("add", 1, 2)
    with pytest.raises(BrokerError, match="tool_denied"):
        await sdk_request("terminal", enabled=True)


def setup_gateway(tmp_path, execute=None):
    store = Store(tmp_path / "db")
    session = store.session()["id"]
    task, _ = store.create(
        TaskRequest(session_id=session, request_id="math", content="synthetic", cloud_consent=True)
    )
    store.state(task["task_id"], "queued")
    store.state(task["task_id"], "running")
    gateway = Gateway(store)

    async def add(arguments):
        return {"result": arguments["a"] + arguments["b"]}

    gateway.register(Registration(Capability(), AddInput, AddOutput, execute or add, lambda: True))
    attempt = store.ledger.begin(task["task_id"], 4000, 2, "local")
    grant = Grant(
        task_id=task["task_id"],
        session_id=session,
        attempt_id=attempt,
        expires=time.monotonic() + 10,
    )
    return gateway, grant


async def test_gateway_consumes_exact_scope_once_and_refuses_foreign_or_disabled(tmp_path):
    gateway, grant = setup_gateway(tmp_path)
    arguments = {"a": 1, "b": 2}
    try:
        with pytest.raises(BrokerError, match="tool_denied"):
            gateway.issue(grant, arguments)
        with pytest.raises(BrokerError, match="tool_denied"):
            gateway.issue(
                grant.model_copy(update={"session_id": "foreign"}), arguments, enabled=True
            )
        token = gateway.issue(grant, arguments, enabled=True)
        result = await gateway.invoke(token, "arithmetic.add.v1", arguments, enabled=True)
        assert result["result"] == 3
        with pytest.raises(BrokerError, match="tool_denied"):
            await gateway.invoke(token, "arithmetic.add.v1", arguments, enabled=True)
    finally:
        gateway.store.db.close()


async def test_gateway_stop_revokes_and_cancels_inflight_call(tmp_path):
    entered = asyncio.Event()

    async def hung(arguments):
        entered.set()
        await asyncio.sleep(60)
        return {"result": 0}

    gateway, grant = setup_gateway(tmp_path, hung)
    arguments = {"a": 1, "b": 1}
    token = gateway.issue(grant, arguments, enabled=True)
    operation = asyncio.create_task(
        gateway.invoke(token, "arithmetic.add.v1", arguments, enabled=True)
    )
    await entered.wait()
    await gateway.revoke(grant.task_id)
    with pytest.raises(asyncio.CancelledError):
        await operation
    assert not gateway.grants and not gateway.pending
    gateway.store.db.close()


@pytest.mark.skipif(
    not REVIEWED_MCP_RUNTIME_AVAILABLE,
    reason="Reviewed MCP runtime is unavailable in this environment",
)
def test_real_broker_local_arithmetic_uses_no_hermes_or_cloud(tmp_path):
    from fastapi.testclient import TestClient
    from immortility_broker.app import create_app
    from test_workspace import AUTH, TOKEN

    def forbidden_factory():
        pytest.fail("Deterministic arithmetic must not start Hermes")

    settings = Settings(_env_file=None, data_dir=tmp_path, standard_mcp_enabled=True)
    app = create_app(settings, TOKEN, factory=forbidden_factory)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        task_id = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "local-math",
                "content": "add 7 and 8",
                "cloud_consent": True,
            },
        ).json()["task_id"]
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            task = client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()
            if task["status"] in {"succeeded", "failed", "blocked"}:
                break
            time.sleep(0.01)
        assert task["status"] == "succeeded", task.get("error")
        assert task["result"]["text"] == "7 + 8 = 15"
        assert app.state.store.ledger.summary(task_id)["calls"] == 0
        trace = client.get(f"/v1/tasks/{task_id}/trace", headers=AUTH).json()
        assert trace["agent"] == {"runtime": "deterministic", "route": "arithmetic.add.v1"}


def test_runtime_error_canary_is_never_forwarded():
    from immortility_broker.hermes import _failure_detail

    assert "SECRET_CANARY" not in _failure_detail(
        {"error": "SECRET_CANARY", "error_surface": {"code": "SECRET_CANARY"}}
    )


@pytest.mark.skipif(
    not REVIEWED_MCP_RUNTIME_AVAILABLE,
    reason="Reviewed MCP runtime is unavailable in this environment",
)
def test_production_admission_allows_local_work_without_provider_or_hermes(tmp_path):
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    from immortility_broker.app import create_app
    from test_workspace import AUTH, TOKEN

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        standard_mcp_enabled=True,
        openrouter_api_key=SecretStr(""),
        hermes_source=tmp_path / "absent-hermes",
    )
    app = create_app(settings, TOKEN)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        task_id = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "production-local",
                "content": "add 2 and 4",
                "cloud_consent": True,
            },
        ).json()["task_id"]
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            task = client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()
            if task["status"] in {"succeeded", "failed", "blocked", "disconnected"}:
                break
            time.sleep(0.01)
        assert task["status"] == "succeeded", task.get("error")
        assert task["result"]["text"] == "2 + 4 = 6"
        usage = app.state.store.ledger.details(task_id)
        assert usage["attempts"][0]["route"] == "arithmetic.add.v1"
        assert usage["summary"]["calls"] == 0


@pytest.mark.skipif(
    not REVIEWED_MCP_RUNTIME_AVAILABLE,
    reason="Reviewed MCP runtime is unavailable in this environment",
)
async def test_sdk_interoperates_with_an_independent_ndjson_peer(tmp_path):
    import os
    import subprocess
    from immortility_broker.config import ROOT
    from immortility_broker.process_owner import spawn_owned, reap

    python = ROOT / ".venv-mcp/Scripts/python.exe"
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    process, owner = await spawn_owned(
        str(python),
        "-I",
        str(ROOT / "integrations/mcp-standard/conformance.py"),
        env=env,
        cwd=tmp_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 10)
        assert process.returncode == 0 and b"PASS" in output
    finally:
        await reap(process, owner)
