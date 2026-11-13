"""Deterministic orchestration tests; no test in this file opens a microphone."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from jsonschema import ValidationError as SchemaError

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError, TaskRequest, validate
from immortility_broker.store import Store
from immortility_broker.traces import execution_trace
from immortility_broker.voice import RecordRequest, VoiceOptions, VoiceService
from immortility_broker.voice_worker import record
from test_broker import FakeHermes

TOKEN = "voice-test-" + "x" * 40
AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    store = Store(tmp_path / "state.sqlite3")
    session = store.session()["id"]
    admit = AsyncMock()
    cancel = AsyncMock()
    voice = VoiceService(settings, store, admit, cancel)
    monkeypatch.setattr("immortility_broker.voice.ready", lambda _: True)
    yield voice, store, session, admit, cancel
    store.db.close()


@pytest.mark.parametrize("value", [False, None, "true", 1])
def test_explicit_microphone_consent(value):
    with pytest.raises(ValidationError):
        RecordRequest(session_id="s", microphone_consent=value)


def test_worker_denies_capture_without_consent(capsys):
    record({})  # Denial occurs before sounddevice is imported or any device opened.
    assert json.loads(capsys.readouterr().out)["code"] == "microphone_consent_required"


def test_voice_routes_auth_and_validation(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN)
    with TestClient(app) as client:
        assert client.get("/v1/voice/status").status_code == 401
        assert (
            client.post(
                "/v1/voice/record",
                headers=AUTH,
                json={
                    "session_id": "s",
                    "microphone_consent": False,
                },
            ).status_code
            == 422
        )
        result = client.get("/v1/voice/status", headers=AUTH).json()
        assert result["state"] == "IDLE" and not result["microphone_active"]
        assert not result["cloud_audio"] and not result["wake_word"]


async def test_local_review_cleans_audio_and_never_calls_agent(setup):
    voice, _, session, admit, _ = setup
    paths = []

    async def worker(operation, **options):
        if operation == "record":
            path = Path(options["path"])
            path.write_bytes(b"synthetic test")
            paths.append(path)
        return {"text": "Private local transcript"}

    voice.worker = worker
    assert (
        voice.start(RecordRequest(session_id=session, microphone_consent=True))["state"]
        == "LISTENING"
    )
    await voice.finish_recording()  # Release can arrive before worker startup.
    assert voice.stop_requested
    await voice.job
    assert voice.state == "IDLE" and voice.transcript == "Private local transcript"
    assert all(not path.exists() for path in paths)
    admit.assert_not_awaited()


async def test_voice_reuses_session_and_task_history(setup):
    voice, store, session, admit, _ = setup
    prior = TaskRequest(
        session_id=session, request_id="typed", content="Typed first", cloud_consent=True
    )
    first, _ = store.create(prior)
    for state in ["queued", "running", "verifying"]:
        store.state(first["task_id"], state)
    store.state(first["task_id"], "succeeded", result={"text": "Typed answer"})

    async def admitted(request):
        assert store.history(request.session_id)[0]["content"] == "Typed first"
        task, _ = store.create(request)
        for state in ["queued", "running", "verifying"]:
            store.state(task["task_id"], state)
        store.state(task["task_id"], "succeeded", result={"text": "Spoken answer"})
        return store.get(task["task_id"])

    admit.side_effect = admitted
    voice.worker = AsyncMock(return_value={"text": "Spoken follow up"})
    voice.start(RecordRequest(session_id=session, microphone_consent=True, cloud_consent=True))
    await voice.job
    assert voice.state == "IDLE"
    request = admit.await_args.args[0]
    assert request.source == "voice" and request.session_id == session
    assert voice.worker.await_args_list[-1].args == ("speak",)
    assert store.history(session)[-2:] == [
        {"role": "user", "content": "Spoken follow up"},
        {"role": "assistant", "content": "Spoken answer"},
    ]


@pytest.mark.parametrize("phase", ["record", "transcribe", "speak"])
async def test_global_stop_cancels_each_audio_phase(setup, phase):
    voice, store, session, admit, _ = setup
    entered = asyncio.Event()

    async def worker(operation, **options):
        if operation == phase:
            entered.set()
            await asyncio.sleep(60)
        return {"text": "test"}

    voice.worker = worker
    if phase == "speak":
        task, _ = store.create(
            TaskRequest(session_id=session, request_id="r", content="test", cloud_consent=True)
        )
        for state in ["queued", "running", "verifying"]:
            store.state(task["task_id"], state)
        store.state(task["task_id"], "succeeded", result={"text": "test"})
        voice.speak_task(task["task_id"], VoiceOptions())
    else:
        voice.start(RecordRequest(session_id=session, microphone_consent=True))
    await asyncio.wait_for(entered.wait(), 1)
    await asyncio.wait_for(voice.cancel(), 1)
    assert voice.state == "CANCELLED" and voice.level == 0 and voice.process is None
    assert not list(voice.settings.data_dir.glob("voice-*"))
    admit.assert_not_awaited()


async def test_device_failure_is_sanitized_and_no_cloud(setup):
    voice, _, session, admit, _ = setup
    voice.worker = AsyncMock(side_effect=OSError("sensitive device details"))
    voice.start(RecordRequest(session_id=session, microphone_consent=True, cloud_consent=True))
    await voice.job
    assert voice.state == "ERROR" and "sensitive" not in voice.error
    admit.assert_not_awaited()
    assert not list(voice.settings.data_dir.glob("voice-*"))


async def test_no_speech_never_goes_to_cloud(setup):
    voice, _, session, admit, _ = setup
    voice.worker = AsyncMock(return_value={"text": "  "})
    voice.start(RecordRequest(session_id=session, microphone_consent=True, cloud_consent=True))
    await voice.job
    assert voice.state == "ERROR" and "No speech" in voice.error
    admit.assert_not_awaited()


async def test_prepare_cancel_before_first_tick_and_invalid_transition(setup):
    voice, *_ = setup
    voice.begin_prepare()
    await voice.cancel()
    assert not voice.preparing
    with pytest.raises(BrokerError):
        voice.transition("THINKING")


def test_restart_only_cleans_marked_capture_directories(tmp_path):
    marked = tmp_path / "voice-owned"
    marked.mkdir()
    (marked / ".voice-capture").touch()
    (marked / "capture.wav").write_bytes(b"private")
    other = tmp_path / "voice-user-files"
    other.mkdir()
    store = Store(tmp_path / "db")
    voice = VoiceService(
        Settings(_env_file=None, data_dir=tmp_path), store, AsyncMock(), AsyncMock()
    )
    assert voice.state == "IDLE" and not marked.exists() and other.exists()
    store.db.close()


def test_trace_has_stable_attempt_and_no_content(tmp_path):
    store = Store(tmp_path / "db")
    session = store.session()["id"]
    task, _ = store.create(
        TaskRequest(
            session_id=session,
            request_id="r",
            content="private prompt",
            cloud_consent=True,
            source="voice",
        )
    )
    task_id = task["task_id"]
    for state in ["queued", "running"]:
        store.state(task_id, state)
    store.event(task_id, "message.delta", {"text": "private answer"})
    store.state(task_id, "verifying")
    store.state(task_id, "succeeded", result={"text": "private answer"})
    trace = execution_trace(store, task_id)
    assert trace["attempt_id"] == execution_trace(store, task_id)["attempt_id"]
    assert trace["modality"] == "voice" and trace["completion_evidence"]["streamed_chunks"] == 1
    assert "private" not in json.dumps(trace)
    assert trace["verification_evidence"] == []
    with pytest.raises(SchemaError):
        validate(
            "execution-trace",
            {**trace, "tools": {"status": "disabled", "calls": [], "prompt": "secret"}},
        )
    with pytest.raises(SchemaError):
        validate("execution-trace", {**trace, "artifact_refs": ["C:/private/screenshot.png"]})
    store.db.close()


def test_http_voice_turn_uses_existing_engine_and_trace(tmp_path, monkeypatch):
    monkeypatch.setattr("immortility_broker.voice.ready", lambda _: True)
    fake = FakeHermes()
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN, factory=lambda: fake)
    with TestClient(app) as client:
        # Use this test's auth token for the typed and spoken turn alike.
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        request = {
            "session_id": session,
            "request_id": "typed",
            "content": "First typed turn",
            "cloud_consent": True,
        }
        task = client.post("/v1/tasks", headers=AUTH, json=request).json()
        for _ in range(100):
            result = client.get(f"/v1/tasks/{task['task_id']}", headers=AUTH).json()
            if result["status"] == "succeeded":
                break
            import time

            time.sleep(0.01)
        assert result["status"] == "succeeded"
        app.state.voice.worker = AsyncMock(return_value={"text": "Follow up by voice"})
        response = client.post(
            "/v1/voice/record",
            headers=AUTH,
            json={
                "session_id": session,
                "microphone_consent": True,
                "cloud_consent": True,
                "auto_speak": False,
            },
        )
        assert response.json()["state"] == "LISTENING"
        client.portal.call(lambda: app.state.voice.job)
        state = client.get("/v1/voice/status", headers=AUTH).json()
        assert state["state"] == "IDLE"
        rows = client.get(f"/v1/sessions/{session}/tasks", headers=AUTH).json()
        assert len(rows) == 2 and rows[-1]["input"]["source"] == "voice"
        assert fake.history[0]["content"] == "First typed turn"
        trace = client.get(f"/v1/tasks/{state['task_id']}/trace", headers=AUTH).json()
        assert trace["modality"] == "voice" and trace["outcome"] == "succeeded"


def test_unified_stop_reaps_thinking_turn(tmp_path, monkeypatch):
    monkeypatch.setattr("immortility_broker.voice.ready", lambda _: True)
    fake = FakeHermes("slow")
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN, factory=lambda: fake)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        app.state.voice.worker = AsyncMock(return_value={"text": "test utterance"})
        client.post(
            "/v1/voice/record",
            headers=AUTH,
            json={"session_id": session, "microphone_consent": True, "cloud_consent": True},
        )
        import time

        for _ in range(100):
            state = client.get("/v1/voice/status", headers=AUTH).json()
            if state["state"] == "THINKING" and state["task_id"]:
                break
            time.sleep(0.01)
        assert state["state"] == "THINKING"
        assert client.post("/v1/stop", headers=AUTH).json()["stopped"]
        assert client.get("/v1/voice/status", headers=AUTH).json()["state"] == "CANCELLED"
        task = client.get(f"/v1/tasks/{state['task_id']}", headers=AUTH).json()
        assert task["status"] == "cancelled" and fake.stopped


def test_global_stop_still_cancels_agent_when_audio_cleanup_fails(tmp_path):
    fake = FakeHermes("slow")
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN, factory=lambda: fake)
    with TestClient(app) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        task = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "stop-failure",
                "content": "test",
                "cloud_consent": True,
            },
        ).json()
        original = app.state.voice.cancel
        app.state.voice.cancel = AsyncMock(side_effect=TimeoutError("private audio details"))
        response = client.post("/v1/stop", headers=AUTH)
        app.state.voice.cancel = original
        assert response.status_code == 503 and "private" not in response.text
        assert (
            client.get(f"/v1/tasks/{task['task_id']}", headers=AUTH).json()["status"] == "cancelled"
        )
        assert fake.stopped
