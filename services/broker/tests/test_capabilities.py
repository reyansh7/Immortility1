import httpx
import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.store import Store
from immortility_broker.web import guard_url, research_page
from immortility_broker.workspace import run_unittest

TOKEN = "test-session-credential-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_untrusted_code_execution_stays_disabled(tmp_path):
    with pytest.raises(BrokerError) as raised:
        run_unittest(tmp_path)
    assert raised.value.code == "tool_denied"
    settings = Settings(_env_file=None, data_dir=tmp_path, code_execution_enabled=True)
    assert settings.code_execution_enabled is False
    assert Settings(_env_file=None, experimental_qwen_tts=True).experimental_qwen_tts is False


def test_web_guard_rejects_private_and_off_allowlist_targets():
    with pytest.raises(BrokerError):
        guard_url("http://en.wikipedia.org/wiki/SQLite")
    with pytest.raises(BrokerError):
        guard_url("https://127.0.0.1/")
    with pytest.raises(BrokerError):
        guard_url("https://example.com/private")


def test_research_collects_the_wikipedia_citation(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if "opensearch" in str(request.url):
            return httpx.Response(
                200,
                json=["SQLite", ["SQLite"], [""], ["https://en.wikipedia.org/wiki/SQLite"]],
            )
        if request.url.path.endswith("/SQLite"):
            return httpx.Response(200, json={"extract": "SQLite is a database library."})
        return httpx.Response(403)

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    page = research_page("SQLite", client)
    assert page["url"] == "https://en.wikipedia.org/wiki/SQLite"
    assert page["extract"] == "SQLite is a database library."
    monkeypatch.setattr(
        "immortility_broker.web.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    refused = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(403)),
        trust_env=False,
    )
    with pytest.raises(BrokerError) as raised:
        research_page("SQLite", refused)
    assert raised.value.code == "tool_denied"


def test_memory_survives_restart_and_stays_in_its_session(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = Store(path)
    first = store.session()["id"]
    second = store.session()["id"]
    from immortility_broker.contracts import TaskRequest

    task, _ = store.create(
        TaskRequest(
            session_id=first, request_id="memory", content="python length", cloud_consent=True
        )
    )
    task_id = task["task_id"]
    store.remember(first, task_id, "The broker stores python length notes")
    store.db.close()
    reopened = Store(path)
    assert reopened.fts
    found = reopened.recall(first, "python length")
    assert any("python" in item["body"] for item in found)
    assert reopened.recall(second, "python length") == []
    assert reopened.forget(first, task_id) == 1
    assert reopened.recall(first, "python length") == []
    reopened.db.close()


def test_local_mcp_add_is_allowed_and_shell_is_denied(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    with TestClient(create_app(settings, TOKEN)) as client:
        hidden = client.get("/v1/mcp/tools", headers=AUTH).json()
    assert hidden == {"tools": [], "external": False}
    settings.mcp_enabled = True
    with TestClient(create_app(settings, TOKEN)) as client:
        listed = client.get("/v1/mcp/tools", headers=AUTH).json()
        allowed = client.post("/v1/mcp/call", headers=AUTH, json={"name": "add", "a": 2, "b": 2})
        denied = client.post("/v1/mcp/call", headers=AUTH, json={"name": "shell", "a": 1, "b": 1})
    names = {tool["name"]: tool["authorized"] for tool in listed["tools"]}
    assert names["add"] is True and names["shell"] is False
    assert allowed.status_code == 200 and allowed.json()["result"] == "4"
    assert denied.status_code == 403
