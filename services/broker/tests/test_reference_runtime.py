"""Offline broker runtime contracts; real GPU and speaker checks are separately invoked."""

import asyncio
import threading
from unittest.mock import AsyncMock

import pytest

from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.reference_client import ReferenceVoice
from immortility_broker.store import Store
from immortility_broker.voice import VoiceOptions, VoiceService


async def test_reference_runtime_default_deny_never_spawns(monkeypatch):
    spawn = AsyncMock()
    monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
    with pytest.raises(BrokerError, match="reference_disabled"):
        await ReferenceVoice().prepare()
    spawn.assert_not_called()


async def test_next_sentence_renders_during_playback_and_audio_is_cleaned(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "unused-profile"))
    store = Store(tmp_path / "state.db")
    voice = VoiceService(
        Settings(_env_file=None, data_dir=tmp_path, reference_voice_enabled=True),
        store,
        AsyncMock(),
        AsyncMock(),
    )
    voice.options = VoiceOptions(voice="reference")
    playback = threading.Event()
    overlap = threading.Event()
    files = []

    async def render(text, speed):
        if files:
            assert await asyncio.to_thread(playback.wait, 2)
            overlap.set()
        path = tmp_path / (str(len(files)) + ".wav")
        path.write_bytes(b"fake deterministic audio; playback is mocked")
        files.append(path)
        return path

    def play(*args):
        playback.set()
        assert overlap.wait(2)
        args[3](0.2)

    voice.reference.render = render
    monkeypatch.setattr("immortility_broker.voice.play_wav", play)
    try:
        await asyncio.wait_for(voice._reference_speech("First sentence. Second sentence."), 5)
        assert overlap.is_set() and len(files) == 2
        assert all(not path.exists() for path in files) and voice.level == 0
    finally:
        await voice.cancel()
        store.db.close()


async def test_global_stop_does_not_restart_reference_warmup(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "unused-profile"))
    store = Store(tmp_path / "state.db")
    voice = VoiceService(
        Settings(_env_file=None, data_dir=tmp_path, reference_voice_enabled=True),
        store,
        AsyncMock(),
        AsyncMock(),
    )
    voice.options = VoiceOptions(voice="reference", voice_output=True)
    prepare = AsyncMock()
    voice.reference.prepare = prepare
    try:
        await voice.cancel()
        voice.snapshot()
        await asyncio.sleep(0)
        prepare.assert_not_called()
        assert voice.reference_paused and not voice.reference.ready
    finally:
        store.db.close()


async def test_following_chat_turn_is_spoken_and_duplicate_final_is_not(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "unused-profile"))
    monkeypatch.setattr("immortility_broker.voice.ready", lambda _: True)
    store = Store(tmp_path / "state.db")
    voice = VoiceService(
        Settings(_env_file=None, data_dir=tmp_path), store, AsyncMock(), AsyncMock()
    )
    voice.options = VoiceOptions(voice_output=True)
    voice.worker = AsyncMock(return_value={"kind": "done"})
    try:
        for task in ("one", "two"):
            voice.note_assistant_text(task, "Completed sentence.", True)
            await voice.job
            voice.note_assistant_text(task, "Completed sentence.", True)
            assert voice.completed_speech_task == task
        assert voice.worker.await_count == 2
    finally:
        await voice.cancel()
        store.db.close()
