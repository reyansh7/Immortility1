import asyncio
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from immortility_broker.app import create_app
from immortility_broker.config import ROOT, Settings
from immortility_broker.contracts import BrokerError, TaskRequest, validate
from immortility_broker.policy import (
    MODEL,
    allow_tool,
    free_model,
    inference_payload,
    verify_catalog,
)
from immortility_broker.store import Store

TOKEN = "test-session-credential-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class FakeHermes:
    def __init__(self, mode="ok"):
        self.mode = mode
        self.stopped = False
        self.history = []

    async def run(self, content, history):
        self.history = history
        if self.mode == "429":
            raise BrokerError("quota_exhausted", "Free quota exhausted.")
        if self.mode == "disconnect":
            raise BrokerError("hermes_lost", "Hermes process lost.")
        yield "Hello "
        if self.mode == "slow":
            await asyncio.sleep(30)
        yield "world"

    async def stop(self):
        self.stopped = True


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, data_dir=tmp_path, openrouter_api_key="")


def start(client, content="Hello", request_id="request-1", session_id=None):
    session_id = session_id or client.post("/v1/sessions", headers=AUTH).json()["id"]
    body = {
        "session_id": session_id,
        "request_id": request_id,
        "content": content,
        "cloud_consent": True,
    }
    return client.post("/v1/tasks", headers=AUTH, json=body), body


def settled(client, task_id):
    for _ in range(200):
        task = client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()
        if task["status"] in {
            "succeeded",
            "failed",
            "cancelled",
            "blocked",
            "rate_limited",
            "disconnected",
        }:
            return task
        time.sleep(0.01)
    pytest.fail("Task did not settle")


def test_provider_key_is_stored_and_never_returned(settings, monkeypatch):
    secret = "dummy-gemini-key-value"
    saved = {}

    class FakeVault:
        def __init__(self, namespace="Immortility", provider="openrouter"):
            self.provider = provider

        def write(self, value):
            saved[self.provider] = value

        def read(self):
            return saved.get(self.provider)

    monkeypatch.setattr("immortility_broker.secrets.CredentialManager", FakeVault)
    monkeypatch.setattr("immortility_broker.app.CredentialManager", FakeVault)
    monkeypatch.setattr("immortility_broker.app.remove_env_assignments", lambda *_: None)
    with TestClient(create_app(settings, TOKEN)) as client:
        saved_response = client.post(
            "/v1/settings/provider-key",
            headers=AUTH,
            json={"provider": "gemini", "api_key": secret},
        )
        assert saved_response.status_code == 200
        assert saved_response.json() == {"provider": "gemini", "stored": True}
        assert secret not in saved_response.text
        health = client.get("/health/ready", headers=AUTH)
        assert secret not in health.text
        assert health.json()["providers"]["gemini"] == (
            "key stored locally; dispatch requires a broker-verified free route"
        )
        nvidia = "dummy-nvidia-key-value"
        nvidia_response = client.post(
            "/v1/settings/provider-key",
            headers=AUTH,
            json={"provider": "nvidia", "api_key": nvidia},
        )
        assert nvidia_response.status_code == 200
        assert nvidia_response.json() == {"provider": "nvidia", "stored": True}
        health = client.get("/health/ready", headers=AUTH)
        assert nvidia not in health.text
        assert health.json()["providers"]["nvidia"] == (
            "key stored locally; dispatch requires a broker-verified free route"
        )
        assert health.json()["model"] == "openrouter/free"
        rejected = client.post(
            "/v1/settings/provider-key",
            headers=AUTH,
            json={"provider": "groq", "api_key": secret, "extra": secret},
        )
        assert rejected.status_code == 422
        assert secret not in rejected.text


def test_auth_origins_and_input_redaction(settings):
    with TestClient(create_app(settings, TOKEN)) as client:
        assert client.get("/health/live").status_code == 200
        for path in ["/health/ready", "/v1/sessions", "/v1/tasks/no/events"]:
            assert client.get(path).status_code == 401
        assert (
            client.get("/health/ready", headers={**AUTH, "Origin": "https://evil.test"}).status_code
            == 403
        )
        assert client.get("/health/ready", headers={**AUTH, "Host": "evil.test"}).status_code == 400
        response = client.get("/health/ready", headers={**AUTH, "Origin": "http://tauri.localhost"})
        assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"
        assert "test-session" not in response.text
        secret = "sk-private-key-do-not-echo"
        response = client.post("/v1/tasks", headers=AUTH, json={"content": secret, "key": secret})
        assert response.status_code == 422 and secret not in response.text
        assert (
            client.post("/inference/v1/chat/completions", headers=AUTH, json={}).status_code == 401
        )
        assert client.post("/v1/tools/terminal", headers=AUTH, json={}).status_code == 404


def test_lifecycle_stream_replay_history_idempotency(settings):
    fake = FakeHermes()
    app = create_app(settings, TOKEN, factory=lambda: fake)
    with TestClient(app) as client:
        response, body = start(client)
        task_id = response.json()["task_id"]
        task = settled(client, task_id)
        assert task["status"] == "succeeded" and task["result"]["text"] == "Hello world"
        validate("task", task)
        replay = client.get(f"/v1/tasks/{task_id}/events", headers=AUTH).text
        events = [json.loads(line[6:]) for line in replay.splitlines() if line.startswith("data: ")]
        assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
        assert [e["data"]["text"] for e in events if e["type"] == "message.delta"] == [
            "Hello ",
            "world",
        ]
        for event in events:
            validate("event", event)
        partial = client.get(
            f"/v1/tasks/{task_id}/events", headers={**AUTH, "Last-Event-ID": "4"}
        ).text
        assert "id: 1\n" not in partial and "id: 5\n" in partial
        assert client.post("/v1/tasks", headers=AUTH, json=body).json()["task_id"] == task_id
        assert (
            client.post(
                "/v1/tasks", headers=AUTH, json={**body, "content": "different"}
            ).status_code
            == 409
        )
        again, _ = start(client, request_id="request-2", session_id=body["session_id"])
        settled(client, again.json()["task_id"])
        assert fake.history == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hello world"},
        ]
        assert client.get(f"/v1/tasks/{task_id}/events?after=-1", headers=AUTH).status_code == 400
    # Committed history survives reopening the database.
    store = Store(settings.data_dir / "state.sqlite3")
    assert store.get(task_id)["result"]["text"] == "Hello world"
    store.db.close()


def test_cancel_and_backpressure(settings):
    fake = FakeHermes("slow")
    with TestClient(create_app(settings, TOKEN, factory=lambda: fake)) as client:
        response, _ = start(client)
        task_id = response.json()["task_id"]
        assert start(client, request_id="second")[0].status_code == 429
        result = client.post(f"/v1/tasks/{task_id}/cancel", headers=AUTH)
        assert result.json()["status"] == "cancelled" and fake.stopped
        assert (
            client.post(f"/v1/tasks/{task_id}/cancel", headers=AUTH).json()["status"] == "cancelled"
        )


@pytest.mark.parametrize("mode,status", [("429", "rate_limited"), ("disconnect", "disconnected")])
def test_honest_failure(settings, mode, status):
    with TestClient(create_app(settings, TOKEN, factory=lambda: FakeHermes(mode))) as client:
        response, _ = start(client)
        task = settled(client, response.json()["task_id"])
        assert task["status"] == status and "result" not in task


def test_missing_key_is_blocked(settings):
    with TestClient(create_app(settings, TOKEN)) as client:
        response, _ = start(client)
        assert response.json()["status"] == "blocked"
        assert response.json()["error"]["code"] == "missing_key"


def test_created_task_cannot_skip_to_succeeded(tmp_path):
    store = Store(tmp_path / "db")
    session = store.session()
    task, _ = store.create(
        TaskRequest(
            session_id=session["id"], request_id="skip", content="hello", cloud_consent=True
        )
    )
    with pytest.raises(BrokerError) as raised:
        store.state(task["task_id"], "succeeded")
    assert raised.value.code == "invalid_transition"
    assert store.get(task["task_id"])["status"] == "created"
    store.db.close()


def test_restart_reconciles_without_reexecution(tmp_path):
    store = Store(tmp_path / "db")
    session = store.session()
    request = TaskRequest(
        session_id=session["id"], request_id="r", content="hello", cloud_consent=True
    )
    task, _ = store.create(request)
    store.state(task["task_id"], "queued")
    store.state(task["task_id"], "running")
    store.db.close()
    store = Store(tmp_path / "db")
    assert store.get(task["task_id"])["status"] == "disconnected"
    assert store.db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert store.db.execute("PRAGMA user_version").fetchone()[0] == 4
    with pytest.raises(BrokerError):
        store.state(task["task_id"], "succeeded")
    store.db.close()


@pytest.mark.parametrize(
    "model,price",
    [
        ("paid-model", {"prompt": "0", "completion": "0"}),
        (MODEL, {"prompt": "0.01", "completion": "0"}),
        (MODEL, {}),
        (MODEL, {"prompt": "NaN", "completion": "0"}),
        (MODEL, {"prompt": "0", "completion": "0", "request": "0.1"}),
    ],
)
def test_zero_spend_denies_unknown_and_nonzero(model, price):
    with pytest.raises(BrokerError):
        free_model(model, price)


def test_only_free_plain_text_payload():
    free_model(MODEL, {"prompt": "0", "completion": "0", "request": "0"})
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "hello"}],
        "models": ["paid"],
        "plugins": [{"id": "web"}],
    }
    result = inference_payload(body)
    assert "models" not in result and "plugins" not in result and result["max_tokens"] == 2048
    for extra in [
        {"model": "paid"},
        {"tools": [{"function": {}}]},
        {"messages": [{"role": "user", "content": [{"type": "image_url"}]}]},
    ]:
        with pytest.raises(BrokerError):
            inference_payload({**body, **extra})


@pytest.mark.parametrize(
    "name,args",
    [
        ("terminal", {"command": "whoami"}),
        ("write_file", {"path": "../../secret"}),
        ("read_file", {"path": "\\\\server\\share"}),
        ("screen_capture", {}),
        ("microphone", {}),
        ("plugin_install", {}),
        ("unknown", {}),
    ],
)
def test_prompt_injection_cannot_grant_tools(name, args):
    with pytest.raises(BrokerError):
        allow_tool(name, args)


def test_paid_setting_cannot_be_enabled():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allow_paid_inference=True)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, monthly_paid_budget_usd=1)


def test_zero_lock_parses_real_env_strings_without_loosening_policy(tmp_path):
    env = tmp_path / "settings.env"
    env.write_text("ALLOW_PAID_INFERENCE=false\nMONTHLY_PAID_BUDGET_USD=0\n")
    assert Settings(_env_file=env).allow_paid_inference is False
    env.write_text("ALLOW_PAID_INFERENCE=true\nMONTHLY_PAID_BUDGET_USD=0\n")
    with pytest.raises(ValidationError):
        Settings(_env_file=env)


def test_newer_database_cannot_be_downgraded(tmp_path):
    store = Store(tmp_path / "db")
    store.db.execute("PRAGMA user_version=99")
    store.db.close()
    with pytest.raises(BrokerError):
        Store(tmp_path / "db")


async def test_expired_or_unavailable_catalog_fails_closed():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(503))
    ) as client:
        with pytest.raises(BrokerError):
            await verify_catalog(client)


def test_blueprint_fixtures():
    for name in ["task", "event"]:
        validate(
            name,
            json.loads((ROOT / f"packages/contracts/fixtures/{name}.example.json").read_text()),
        )
    for path in (ROOT / "packages/contracts/schemas").glob("*.json"):
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(json.loads(path.read_text()))


def test_inference_capability_separate_from_ui_and_bounded(settings):
    app = create_app(settings, TOKEN, factory=lambda: FakeHermes())
    with TestClient(app) as client:
        response = client.post(
            "/inference/v1/chat/completions",
            headers={"Authorization": "Bearer " + app.state.inference_token},
            json={},
        )
        assert response.status_code == 403
