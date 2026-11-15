"""Broker-gated specialists stay on Hermes and never receive tools."""

import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.delegation import orchestrate
from immortility_broker.local_tools import call_local_tool
from immortility_broker.policy import MODEL, inference_payload, route_model
from immortility_broker.traces import execution_trace
from immortility_broker.store import Store
from immortility_broker.contracts import TaskRequest

TOKEN = "test-session-credential-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class Specialist:
    def __init__(self, seen: list[str]):
        self.seen = seen

    async def run(self, content: str, history: list[dict[str, str]], role: str | None = None):
        self.seen.append(role or "parent")
        if role == "review":
            assert "Research:" in content and "Coding:" in content
            yield "Notes look consistent.\nVERDICT: pass"
            return
        if role == "coding":
            yield "Change the label in text only."
            return
        if role == "research":
            yield "The request is a wording change."
            return
        assert "VERDICT: pass" in content
        yield "Combined: update the label. Review passed. No tools ran."

    async def stop(self) -> None:
        return None


def test_only_the_free_router_is_selectable():
    assert route_model(None) == MODEL
    with pytest.raises(BrokerError) as raised:
        route_model("gemini-2.5-flash")
    assert raised.value.code == "inference_denied"


def test_delegate_tool_payload_stays_blocked():
    with pytest.raises(BrokerError):
        inference_payload(
            {
                "model": MODEL,
                "tools": [{"name": "delegate_task"}],
                "messages": [{"role": "user", "content": "go"}],
            }
        )


def test_clock_is_allowed_and_terminal_is_rejected():
    assert call_local_tool("clock", True)["name"] == "clock"
    with pytest.raises(BrokerError) as denied:
        call_local_tool("terminal", True)
    assert denied.value.code == "tool_denied"
    with pytest.raises(BrokerError):
        call_local_tool("clock", False)


def test_tool_endpoint_audits_the_allowlist(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path, local_tools_enabled=True)
    with TestClient(create_app(settings, TOKEN)) as client:
        allowed = client.post("/v1/tools/call", headers=AUTH, json={"name": "clock"})
        rejected = client.post("/v1/tools/call", headers=AUTH, json={"name": "terminal"})
    assert allowed.status_code == 200 and allowed.json()["name"] == "clock"
    assert "key" not in allowed.text.lower() or "clock" in allowed.text
    assert rejected.status_code == 403


async def test_two_specialists_are_verified_and_combined(tmp_path):
    seen: list[str] = []
    events: list[tuple[str, str]] = []
    store = Store(tmp_path / "state.sqlite3")
    session = store.session()
    task, _ = store.create(
        TaskRequest(
            session_id=session["id"],
            request_id="deleg",
            content="Rename the label",
            cloud_consent=True,
        )
    )
    store.state(task["task_id"], "queued")
    store.state(task["task_id"], "running")

    def emit(role: str, status: str) -> None:
        events.append((role, status))
        kind = "agent.completed" if status != "started" else "agent.started"
        store.event(task["task_id"], kind, {"role": role, "status": status})

    text = ""
    async for delta in orchestrate(lambda: Specialist(seen), "Rename the label", [], "", emit):
        text += delta
    trace = execution_trace(store, task["task_id"])
    store.db.close()
    assert seen[:2] == ["research", "coding"] or seen[:2] == ["coding", "research"]
    assert seen[2:] == ["review", "parent"]
    assert "No tools ran." in text
    assert ("review", "succeeded") in events
    assert trace["tools"] == {"status": "disabled", "calls": []}
    roles = [item["role"] for item in trace["delegations"]]
    assert roles.count("research") >= 1 and roles.count("coding") >= 1 and "review" in roles


def test_tool_discovery_stays_empty_until_enabled(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings, TOKEN)) as client:
        hidden = client.get("/v1/tools", headers=AUTH)
        assert hidden.json() == {"tools": [], "unrestricted": False}
        client.post("/v1/settings/local-tools", headers=AUTH, json={"enabled": True})
        listed = client.get("/v1/tools", headers=AUTH)
        assert listed.json()["tools"] == ["clock"]
        assert listed.json()["unrestricted"] is False


def test_delegation_flag_is_off_until_requested(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings, TOKEN)) as client:
        assert client.get("/health/ready", headers=AUTH).json()["delegation_enabled"] is False
        turned = client.post("/v1/settings/delegation", headers=AUTH, json={"enabled": True})
        assert turned.json()["enabled"] is True
        assert client.get("/health/ready", headers=AUTH).json()["delegation_enabled"] is True
