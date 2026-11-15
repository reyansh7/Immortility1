"""Offline broker consent-boundary tests. Native UI acceptance is separate.

The mocked picker here stands for a private native pipe, not human acceptance.
Real UIA/identity/indicator fixtures run in smoke-windows-observer.py.
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import ROOT, Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.windows_observer import NativeWindowApproval, PickerSession, WindowSnapshot
from immortility_broker.process_owner import reap, spawn_owned
from test_workspace import AUTH, TOKEN

CANARY = "SYNTHETIC_OBSERVATION_TEXT_ONLY_829172"


def configured(tmp_path, **kwargs):
    return Settings(_env_file=None, data_dir=tmp_path, hermes_source=tmp_path / "absent", **kwargs)


def request(client, **extra):
    session = client.post("/v1/sessions", headers=AUTH).json()["id"]
    return {"session_id": session, "request_id": str(uuid4()), **extra}


def install_fakes(monkeypatch, *, mode="ok", text=CANARY):
    entered, closed = threading.Event(), threading.Event()

    @asynccontextmanager
    async def picker(lease):
        stopped = asyncio.create_task(asyncio.Event().wait())
        try:
            if mode == "denied":
                raise BrokerError("consent_declined", "Window inspection was not authorized.", 403)
            if mode == "waiting":
                entered.set()
                await asyncio.Event().wait()
            selection = NativeWindowApproval(
                lease_id=lease.nonce,
                hwnd=123,
                pid=456,
                created=789,
                title="Synthetic offline fixture",
                indicator_hwnd=321,
                indicator_pid=654,
                indicator_created=987,
            )
            if mode == "indicator_closed":
                stopped.cancel()
            yield PickerSession(selection, stopped)
        finally:
            stopped.cancel()
            try:
                await stopped
            except asyncio.CancelledError:
                pass
            closed.set()

    async def inspect(arguments):
        entered.set()
        if mode in {"slow", "indicator_closed"}:
            await asyncio.Event().wait()
        now = time.time()
        return {
            "schema_version": "1.0",
            "kind": "untrusted_ui_data",
            "task_id": str(uuid4()) if mode == "foreign" else arguments["task_id"],
            "lease_id": arguments["lease_id"],
            "hwnd": 123,
            "pid": 456,
            "created": 789,
            "observed_at": now,
            "valid_until": now + 2,
            "window_rect": [0, 0, 600, 500],
            "dpi": 120,
            "foreground": False,
            "truncated": False,
            "cloud_allowed": False,
            "screenshots": 0,
            "input_actions": 0,
            "nodes": [
                {
                    "id": 0,
                    "depth": 0,
                    "protected": False,
                    "text": text,
                    "control_type": "Edit",
                    "rect": [20, 30, 500, 200],
                }
            ],
        }

    monkeypatch.setattr("immortility_broker.app.select_window", picker)
    monkeypatch.setattr("immortility_broker.app.inspect_window", inspect)
    return entered, closed


def no_model(*args):
    raise AssertionError("Local observation must never start Hermes")


def test_observation_uses_same_gateway_zero_cloud_and_no_screen_text_retention(
    tmp_path, monkeypatch
):
    _, closed = install_fakes(monkeypatch)
    app = create_app(configured(tmp_path), TOKEN, factory=no_model)
    with TestClient(app) as client:
        body = request(client)
        initial = client.post("/v1/observations", json=body, headers=AUTH)
        assert initial.status_code == 200
        task = initial.json()
        assert task["input"]["no_cloud"] and task["recall_excluded"]
        result = client.get(f"/v1/observations/{task['task_id']}", headers=AUTH).json()
        assert result["task"]["status"] == "succeeded"
        assert result["snapshot"]["nodes"][0]["text"] == CANARY
        assert closed.is_set()
        assert app.state.engine.active is None
        assert app.state.engine.gateway.grants == {}
        assert app.state.engine.gateway.discover(("window.inspect.v1",)) == []
        usage = client.get(f"/v1/tasks/{task['task_id']}/usage", headers=AUTH).json()
        assert usage["summary"]["calls"] == 0
        assert usage["summary"]["charged_tokens"] == 0
        events = app.state.store.events(task["task_id"])
        assert [e["type"] for e in events if e["type"].startswith("observation.")] == [
            "observation.authorized",
            "observation.completed",
            "observation.revoked",
        ]
        assert sum(e["type"] == "tool.started" for e in events) == 1
        assert CANARY not in json.dumps(events)
        assert CANARY not in json.dumps(
            client.get(f"/v1/tasks/{task['task_id']}", headers=AUTH).json()
        )
        trace = client.get(f"/v1/tasks/{task['task_id']}/trace", headers=AUTH)
        assert trace.status_code == 200
        assert trace.json()["agent"] == {"runtime": "deterministic", "route": "windows.uia.v1"}
        assert app.state.store.recall(body["session_id"], "SYNTHETIC") == []
        assert client.get(f"/v1/observations/{task['task_id']}", headers=AUTH).status_code == 404
        assert client.post("/v1/observations", json=body, headers=AUTH).status_code == 409
    for path in tmp_path.glob("*"):
        if path.is_file():
            assert CANARY.encode() not in path.read_bytes()


@pytest.mark.parametrize(
    "field,value",
    [
        ("hwnd", 123),
        ("consent", True),
        ("no_cloud", False),
        ("command", "click"),
    ],
)
def test_frontend_cannot_supply_source_or_native_consent(tmp_path, monkeypatch, field, value):
    entered, _ = install_fakes(monkeypatch)
    with TestClient(create_app(configured(tmp_path), TOKEN, factory=no_model)) as client:
        assert (
            client.post(
                "/v1/observations", json=request(client, **{field: value}), headers=AUTH
            ).status_code
            == 422
        )
        assert not entered.is_set()
        assert (
            client.post("/native/v1/observation/prepare", headers=AUTH, json={}).status_code == 404
        )


def test_unauthenticated_and_headless_observation_are_denied(tmp_path):
    with TestClient(create_app(configured(tmp_path, local_only_mode=True), TOKEN)) as client:
        assert (
            client.post("/v1/observations", headers=AUTH, json=request(client)).status_code == 403
        )
    with TestClient(create_app(configured(tmp_path), TOKEN)) as client:
        assert client.post("/v1/observations", json={}).status_code == 401


@pytest.mark.parametrize("mode", ["denied", "indicator_closed", "foreign"])
def test_denied_revoked_or_foreign_snapshot_never_delivered(tmp_path, monkeypatch, mode):
    install_fakes(monkeypatch, mode=mode)
    with TestClient(create_app(configured(tmp_path), TOKEN, factory=no_model)) as client:
        task = client.post("/v1/observations", headers=AUTH, json=request(client)).json()
        result = client.get(f"/v1/observations/{task['task_id']}", headers=AUTH).json()
        assert result["snapshot"] is None
        assert result["task"]["status"] == ("failed" if mode == "foreign" else "cancelled")


@pytest.mark.parametrize("mode", ["waiting", "slow"])
def test_stop_cancels_native_wait_and_inspection(tmp_path, monkeypatch, mode):
    entered, closed = install_fakes(monkeypatch, mode=mode)
    app = create_app(configured(tmp_path), TOKEN, factory=no_model)
    with TestClient(app) as client:
        task = client.post("/v1/observations", headers=AUTH, json=request(client)).json()
        assert entered.wait(3)
        assert client.post("/v1/stop", headers=AUTH, json={}).status_code == 200
        result = client.get(f"/v1/observations/{task['task_id']}", headers=AUTH).json()
        assert result["snapshot"] is None
        assert result["task"]["status"] == "cancelled"
        assert closed.is_set()
        assert app.state.engine.gateway.pending == {}


def test_configured_credential_in_local_ui_text_never_reaches_frontend(tmp_path, monkeypatch):
    install_fakes(monkeypatch, text=CANARY)
    with TestClient(create_app(configured(tmp_path, gemini_api_key=CANARY), TOKEN)) as client:
        task = client.post("/v1/observations", headers=AUTH, json=request(client)).json()
        result = client.get(f"/v1/observations/{task['task_id']}", headers=AUTH)
        assert result.json()["snapshot"] is None
        assert result.json()["task"]["error"]["code"] == "secret_egress_denied"
        assert CANARY not in result.text


def test_durable_workflow_cannot_replay_an_active_window_read(tmp_path, monkeypatch):
    entered, _ = install_fakes(monkeypatch, mode="slow")
    app = create_app(configured(tmp_path, durable_workflows_enabled=True), TOKEN)
    with TestClient(app) as client:
        body = request(client)
        client.post("/v1/observations", headers=AUTH, json=body)
        assert entered.wait(3)
        workflow = {
            "session_id": body["session_id"],
            "request_id": "forbidden-resume",
            "label": "No UI replay",
            "local_read_consent": True,
            "no_cloud": True,
            "steps": [{"id": "read", "capability": "window.inspect.v1"}],
        }
        response = client.post("/v1/workflows", headers=AUTH, json=workflow)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "tool_denied"
        client.post("/v1/stop", headers=AUTH, json={})


def test_shared_snapshot_schema_matches_actual_typed_output():
    assert (
        json.loads((ROOT / "packages/contracts/schemas/window-snapshot.schema.json").read_text())
        == WindowSnapshot.model_json_schema()
    )


@pytest.mark.skipif(os.name != "nt", reason="Native Windows helper protocol")
async def test_real_native_picker_rejects_approval_fields_before_opening_any_ui():
    process, owner = await spawn_owned(
        sys.executable,
        "-I",
        str(ROOT / "integrations/windows-observer/native_picker.py"),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        job_memory_limit=64 * 1024**2,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        # Only a nonce is accepted, never consent/target/auto-approve.
        output, _ = await asyncio.wait_for(
            process.communicate(
                json.dumps({"lease_id": uuid4().hex, "consent": True, "hwnd": 123}).encode() + b"\n"
            ),
            5,
        )
        assert json.loads(output) == {"error": "native_picker_failed"}
        assert process.returncode == 1
    finally:
        await reap(process, owner)
