"""Speech text, consent, profile metadata, and clone playback ordering."""

import asyncio
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError, TaskRequest
from immortility_broker.speech_text import for_speech, ready_sentences
from immortility_broker.store import Store
from immortility_broker.voice import VoiceOptions, VoiceService
from immortility_broker.voice_store import (
    consent_granted,
    delete_clone,
    profile_path,
    profile_ready,
    require_source,
    write_consent,
)


@pytest.fixture
def setup(tmp_path):
    from unittest.mock import AsyncMock

    settings = Settings(_env_file=None, data_dir=tmp_path)
    store = Store(tmp_path / "state.sqlite3")
    session = store.session()["id"]
    voice = VoiceService(settings, store, AsyncMock(), AsyncMock())
    yield voice, store, session
    store.db.close()


def test_speech_text_drops_markdown_and_code() -> None:
    spoken = for_speech(
        "Hello **there**. ```\nprint('secret')\n``` See [docs](https://example.test)."
    )
    assert "secret" not in spoken
    assert "https://" not in spoken
    assert spoken.startswith("Hello there.")
    assert "docs" in spoken


def test_sentences_wait_for_punctuation_then_flush() -> None:
    partial, count = ready_sentences("Hello there. I am", 0, False)
    assert partial == ["Hello there."] and count == 1
    finished, count = ready_sentences("Hello there. I am ready", count, True)
    assert finished == ["I am ready"] and count == 2


def test_missing_reference_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("IMMORTILITY_VOICE_SOURCE", str(tmp_path / "missing.ogg"))
    with pytest.raises(FileNotFoundError):
        require_source()


def test_profile_roundtrip_and_corruption(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path))
    blob = tmp_path / "friend_voice.pt"
    blob.write_bytes(b"tensor-bytes")
    meta = {
        "format_version": 1,
        "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "model_revision": "5d83992436eae1d760afd27aff78a71d676296fc",
        "profile_sha256": __import__("hashlib").sha256(b"tensor-bytes").hexdigest(),
    }
    (tmp_path / "friend_voice.json").write_text(json.dumps(meta), encoding="utf-8")
    assert profile_ready() and profile_path() == blob
    blob.write_bytes(b"tampered")
    assert not profile_ready()
    write_consent(True)
    assert consent_granted()
    delete_clone()
    assert not blob.exists() and not consent_granted()


def test_friend_voice_requires_explicit_consent() -> None:
    with pytest.raises(ValidationError):
        VoiceOptions.model_validate({"clone_consent": "yes"})
    assert VoiceOptions().voice == "ljspeech" and VoiceOptions().voice_output is False


async def test_text_only_until_voice_output_is_enabled(setup) -> None:  # type: ignore[no-untyped-def]
    voice, *_ = setup
    voice.note_assistant_text("task", "Hello there.", True)
    assert voice.job is None


async def test_clone_sentences_stay_ordered_and_cancel(setup, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    voice, *_ = setup
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(voice.settings.data_dir))
    write_consent(True)
    spoken: list[str] = []
    started = asyncio.Event()

    async def utter(sentence: str) -> None:
        spoken.append(sentence)
        if len(spoken) == 1:
            started.set()
            await asyncio.sleep(30)

    monkeypatch.setattr(voice, "_utter", utter)
    voice.options = VoiceOptions(voice="friend", voice_output=True, clone_consent=True)
    voice.note_assistant_text("task", "Hello there. Second sentence.", True)
    await asyncio.wait_for(started.wait(), 1)
    await asyncio.wait_for(voice.cancel(), 1)
    assert spoken == ["Hello there."]
    assert voice.level == 0


async def test_disabled_output_does_not_call_clone(setup, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    voice, *_ = setup
    called = False

    async def utter(_sentence: str) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(voice, "_utter", utter)
    voice.options = VoiceOptions(voice="friend", voice_output=False, clone_consent=True)
    voice.note_assistant_text("task", "Hello there.", True)
    await asyncio.sleep(0.05)
    assert called is False


def test_worker_refuses_clone_build_without_consent() -> None:
    from immortility_tts.worker import build

    captured: list[dict[str, object]] = []

    def fake_emit(kind: str, **payload: object) -> None:
        captured.append({"kind": kind, **payload})

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("immortility_tts.worker.emit", fake_emit)
    try:
        build({"id": "1", "consent": False})
    finally:
        monkeypatch.undo()
    assert captured[0]["code"] == "clone_consent_required"


def test_speak_task_rejects_friend_without_consent(setup) -> None:  # type: ignore[no-untyped-def]
    voice, store, session, *_ = setup
    task, _ = store.create(
        TaskRequest(session_id=session, request_id="clone", content="hi", cloud_consent=True)
    )
    for state in ("queued", "running", "verifying"):
        store.state(task["task_id"], state)
    store.state(task["task_id"], "succeeded", result={"text": "Hello."})
    with pytest.raises(BrokerError) as raised:
        voice.speak_task(task["task_id"], VoiceOptions(voice="friend", clone_consent=False))
    assert raised.value.code == "clone_consent_required"
    assert voice.state == "IDLE"


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg is not available in this environment",
)
def test_clone_playback_tempo_shortens_audio(tmp_path: Path) -> None:
    import wave

    from immortility_broker.playback import CLONE_PLAYBACK_TEMPO, stretch_wav

    source = tmp_path / "tone.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\x00\x00" * 24000)
    faster = stretch_wav(source, CLONE_PLAYBACK_TEMPO)
    with wave.open(str(source), "rb") as original, wave.open(str(faster), "rb") as sped:
        ratio = original.getnframes() / sped.getnframes()
    assert source.is_file()
    assert 1.2 < ratio < 1.4
