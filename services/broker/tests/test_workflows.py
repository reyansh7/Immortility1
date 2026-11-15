import asyncio
import json
import sqlite3
import threading
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.store import Store
from immortility_broker.workflows import WorkflowRequest
from test_workspace import AUTH, TOKEN


def configured(tmp_path, **kwargs):
    return Settings(
        _env_file=None,
        data_dir=tmp_path,
        durable_workflows_enabled=True,
        local_tools_enabled=True,
        hermes_source=tmp_path / "absent-hermes",
        **kwargs,
    )


def specification(client, *, steps=None, resume=True):
    session = client.post("/v1/sessions", headers=AUTH).json()["id"]
    return {
        "session_id": session,
        "request_id": "read-work",
        "label": "Synthetic local workflow",
        "steps": steps
        or [
            {"id": "first", "capability": "clock.now.v1"},
            {"id": "second", "capability": "clock.now.v1", "depends_on": ["first"]},
        ],
        "local_read_consent": True,
        "no_cloud": True,
        "resume_on_restart": resume,
        "max_retries": 1,
        "deadline_seconds": 60,
    }


def wait(client, task_id, states):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        task = client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()
        if task["status"] in states:
            return task
        time.sleep(0.01)
    pytest.fail("Workflow did not reach expected state")


def test_real_broker_dag_uses_registered_sdk_clock_and_zero_model_calls(tmp_path):
    app = create_app(configured(tmp_path, standard_mcp_enabled=True), TOKEN)
    with TestClient(app) as client:
        request = specification(
            client,
            steps=[
                {"id": "sum", "capability": "arithmetic.add.v1", "arguments": {"a": 2, "b": 3}},
                {
                    "id": "dependent",
                    "capability": "arithmetic.add.v1",
                    "arguments": {"b": 8},
                    "depends_on": ["sum"],
                    "bindings": {"a": {"step_id": "sum", "field": "result"}},
                },
                {"id": "stamp", "capability": "clock.now.v1", "depends_on": ["dependent"]},
            ],
        )
        response = client.post("/v1/workflows", headers=AUTH, json=request)
        assert response.status_code == 200, response.text
        task_id = response.json()["task_id"]
        task = wait(client, task_id, {"succeeded", "failed", "blocked"})
        assert task["status"] == "succeeded", task.get("error")
        assert task["result"]["steps"]["sum"] == {"result": 5}
        assert task["result"]["steps"]["dependent"] == {"result": 13}
        assert task["input"]["no_cloud"] and task["recall_excluded"]
        assert app.state.store.ledger.summary(task_id)["calls"] == 0
        duplicate = client.post("/v1/workflows", headers=AUTH, json=request)
        assert duplicate.json()["task_id"] == task_id
        view = client.get(f"/v1/workflows/{task_id}", headers=AUTH).json()
        assert all(step["attempts"] == 1 for step in view["steps"])
        assert client.get(f"/v1/tasks/{task_id}/trace", headers=AUTH).json()["agent"] == {
            "runtime": "deterministic",
            "route": "workflow.local.v1",
        }


def test_default_off_and_local_only_boundary_reject_privileged_routes(tmp_path):
    with TestClient(
        create_app(Settings(_env_file=None, data_dir=tmp_path / "off"), TOKEN)
    ) as client:
        request = specification(client)
        assert client.post("/v1/workflows", headers=AUTH, json=request).status_code == 403
    with TestClient(
        create_app(configured(tmp_path / "local", local_only_mode=True), TOKEN)
    ) as client:
        for path in (
            "/v1/settings/provider-key",
            "/v1/settings/workspace",
            "/v1/voice/record",
            "/inference/v1/chat/completions",
            "/v1/tasks",
        ):
            response = client.post(path, headers=AUTH, json={"secret": "CANARY"})
            assert response.status_code == 403 and "CANARY" not in response.text
        request = specification(client)
        request["steps"] = [{"id": "escape", "capability": "terminal", "arguments": {}}]
        assert client.post("/v1/workflows", headers=AUTH, json=request).status_code == 403
        assert app_task_count(client) == 0


def app_task_count(client):
    sessions = client.get("/v1/sessions", headers=AUTH).json()
    return sum(
        len(client.get(f"/v1/sessions/{session['id']}/tasks", headers=AUTH).json())
        for session in sessions
    )


def pending_second(tmp_path):
    app = create_app(configured(tmp_path), TOKEN)
    entered = threading.Event()
    calls = []

    async def observe(arguments):
        calls.append(1)
        if len(calls) == 2:
            entered.set()
            await asyncio.sleep(60)
        return {"timestamp": "2026-11-14T00:00:00+00:00"}

    name = "clock.now.v1"
    app.state.engine.gateway.registrations[name] = replace(
        app.state.engine.gateway.registrations[name], execute=observe
    )
    return app, entered, calls


def test_restart_resumes_only_unfinished_read_step_and_keeps_original_deadline(tmp_path):
    app, entered, calls = pending_second(tmp_path)
    with TestClient(app) as client:
        request = specification(client)
        task_id = client.post("/v1/workflows", headers=AUTH, json=request).json()["task_id"]
        assert entered.wait(3)
        expires = client.get(f"/v1/workflows/{task_id}", headers=AUTH).json()["expires_at"]
    assert len(calls) == 2
    restarted = create_app(configured(tmp_path), TOKEN)
    with TestClient(restarted) as client:
        task = wait(client, task_id, {"succeeded", "failed", "blocked"})
        assert task["status"] == "succeeded", task.get("error")
        assert task["result"]["steps"]["first"]["timestamp"] == "2026-11-14T00:00:00+00:00"
        view = client.get(f"/v1/workflows/{task_id}", headers=AUTH).json()
        assert view["expires_at"] == expires
        assert {s["step_id"]: s["attempts"] for s in view["steps"]} == {"first": 1, "second": 2}


def test_stop_cancels_active_and_queued_work_and_never_resumes_them(tmp_path):
    app, entered, _ = pending_second(tmp_path)
    with TestClient(app) as client:
        request = specification(client)
        first = client.post("/v1/workflows", headers=AUTH, json=request).json()["task_id"]
        assert entered.wait(3)
        request["request_id"] = "second-workflow"
        second = client.post("/v1/workflows", headers=AUTH, json=request).json()["task_id"]
        assert client.post("/v1/stop", headers=AUTH).status_code == 200
        assert wait(client, first, {"cancelled"})["status"] == "cancelled"
        assert wait(client, second, {"cancelled"})["status"] == "cancelled"
    with TestClient(create_app(configured(tmp_path), TOKEN)) as client:
        assert client.get(f"/v1/tasks/{first}", headers=AUTH).json()["status"] == "cancelled"
        assert client.get(f"/v1/tasks/{second}", headers=AUTH).json()["status"] == "cancelled"


def test_corrupt_checkpoint_fails_closed_instead_of_repeating_completed_step(tmp_path):
    app, entered, _ = pending_second(tmp_path)
    with TestClient(app) as client:
        task_id = client.post("/v1/workflows", headers=AUTH, json=specification(client)).json()[
            "task_id"
        ]
        assert entered.wait(3)
    with sqlite3.connect(tmp_path / "state.sqlite3") as db:
        db.execute(
            "UPDATE workflow_steps SET result=? WHERE task_id=? AND step_id='first'",
            (json.dumps({"timestamp": "tampered"}), task_id),
        )
    with TestClient(create_app(configured(tmp_path), TOKEN)) as client:
        task = wait(client, task_id, {"failed", "blocked"})
        assert task["error"]["code"] == "checkpoint_corrupt"


def test_disabling_recovery_never_replays_an_authorized_local_workflow(tmp_path):
    app, entered, _ = pending_second(tmp_path)
    with TestClient(app) as client:
        task_id = client.post("/v1/workflows", headers=AUTH, json=specification(client)).json()[
            "task_id"
        ]
        assert entered.wait(3)
    with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN)) as client:
        assert client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()["status"] == "disconnected"


def test_only_one_broker_can_own_the_same_task_database(tmp_path):
    store = Store(tmp_path / "db")
    with pytest.raises(BrokerError, match="broker_already_running"):
        Store(tmp_path / "db")
    store.db.close()
    reopened = Store(tmp_path / "db")
    reopened.db.close()


@pytest.mark.parametrize(
    "failures,retries,expected,attempts",
    [(0, 1, "succeeded", 1), (1, 1, "succeeded", 2), (2, 1, "failed", 2), (1, 0, "failed", 1)],
)
def test_read_step_retry_allowance_is_exact_and_does_not_repeat_completed_steps(
    tmp_path, failures, retries, expected, attempts
):
    app = create_app(configured(tmp_path), TOKEN)
    invocations = []

    async def observed(arguments):
        invocations.append(1)
        if len(invocations) <= failures:
            raise BrokerError("mcp_failed", "Synthetic local startup failure.", 503)
        return {"timestamp": "2026-11-15T00:00:00+00:00"}

    name = "clock.now.v1"
    app.state.engine.gateway.registrations[name] = replace(
        app.state.engine.gateway.registrations[name], execute=observed
    )
    with TestClient(app) as client:
        request = specification(client, steps=[{"id": "read", "capability": name}])
        request["max_retries"] = retries
        tid = client.post("/v1/workflows", headers=AUTH, json=request).json()["task_id"]
        task = wait(client, tid, {expected})
        view = client.get(f"/v1/workflows/{tid}", headers=AUTH).json()
        assert view["steps"][0]["attempts"] == attempts == len(invocations)
        assert client.post("/v1/workflows", headers=AUTH, json=request).json()["task_id"] == tid
        assert len(invocations) == attempts
        assert task["status"] == expected
        assert app.state.store.ledger.summary(tid)["calls"] == 0


def test_cycles_unknown_dependencies_and_nonexplicit_consent_are_rejected():
    base = {
        "session_id": "session",
        "request_id": "request",
        "label": "test",
        "local_read_consent": True,
    }
    with pytest.raises(ValidationError):
        WorkflowRequest(
            **base,
            steps=[
                {"id": "a", "capability": "clock.now.v1", "depends_on": ["b"]},
                {"id": "b", "capability": "clock.now.v1", "depends_on": ["a"]},
            ],
        )
    with pytest.raises(ValidationError):
        WorkflowRequest(
            **(base | {"local_read_consent": 1}), steps=[{"id": "a", "capability": "clock.now.v1"}]
        )
