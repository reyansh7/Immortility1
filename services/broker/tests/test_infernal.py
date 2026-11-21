"""Security and compatibility boundaries. Native DSP/playback has separate real tests."""

from unittest.mock import AsyncMock, Mock
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.infernal import Coloration, PRESETS, delivery_plan
from immortility_broker.store import Store
from immortility_broker.voice import VoiceOptions, VoiceService


@pytest.mark.parametrize(
    "payload",
    [
        {"pitch_semitones": -7},
        {"effects_strength": 1.1},
        {"robotic_intensity": float("nan")},
        {"infernal_base": "arbitrary/model"},
    ],
)
def test_infernal_arguments_are_bounded(payload):
    with pytest.raises(ValidationError):
        VoiceOptions.model_validate(payload)


def test_original_defaults_and_qwen_gate_are_preserved():
    options = VoiceOptions()
    assert options.voice == "ljspeech" and not options.voice_output
    settings = Settings(_env_file=None)
    assert not settings.infernal_voice_enabled and not settings.experimental_qwen_tts
    for name, preset in PRESETS.items():
        options = VoiceOptions.model_validate({"voice": "infernal", **preset})
        assert options.voice_preset == name
    with pytest.raises(ValueError):
        Coloration(pitch_semitones=float("inf"))


async def test_disabled_preset_never_spawns_worker_or_writes_consent(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "private"))
    store = Store(tmp_path / "state.db")
    try:
        voice = VoiceService(
            Settings(_env_file=None, data_dir=tmp_path), store, AsyncMock(), AsyncMock()
        )
        spawn = AsyncMock()
        monkeypatch.setattr("asyncio.create_subprocess_exec", spawn)
        with pytest.raises(BrokerError, match="infernal_disabled"):
            await voice.worker("speak", voice="infernal", text="public test")
        with pytest.raises(BrokerError, match="infernal_disabled"):
            voice.apply_options(VoiceOptions(voice="infernal"))
        spawn.assert_not_called()
        assert not (tmp_path / "private/consent.json").exists()
    finally:
        store.db.close()


def test_public_voice_settings_do_not_rewrite_clone_consent(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "private"))
    store = Store(tmp_path / "state.db")
    try:
        voice = VoiceService(
            Settings(_env_file=None, data_dir=tmp_path, infernal_voice_enabled=True),
            store,
            AsyncMock(),
            AsyncMock(),
        )
        consent = Mock()
        monkeypatch.setattr("immortility_broker.voice.write_consent", consent)
        voice.apply_options(VoiceOptions(voice="infernal"))
        consent.assert_not_called()
        assert voice.qwen.process is None
    finally:
        store.db.close()


def test_deliberate_delivery_preserves_words_and_has_bounded_pauses():
    text = "All systems are online. Your instructions remain in control."
    plan = delivery_plan(text, 0.96, True)
    assert " ".join(row[0] for row in plan) == text
    assert len(plan) == 2 and plan[-1][2] == 0
    assert all(0.5 <= rate <= 2 and 0 <= pause <= 0.3 for _, rate, pause, _ in plan)


def test_ab_candidates_are_not_promoted_and_keep_natural_pitch():
    root = Path(__file__).resolve().parents[3]
    config = json.loads((root / "config/infernal-refinement.json").read_text())
    assert config["status"] == "audition_only_pending_user_approval"
    for candidate in config["candidates"].values():
        options = VoiceOptions.model_validate({"voice": "infernal", **candidate})
        assert options.pitch_semitones == 0 and options.infernal_base == "kokoro_onyx"
        assert options.delivery == "conversational"
    assert PRESETS["ultron_inspired"]["delivery"] == "deliberate"
    assert PRESETS["ultron_conversational"] == {
        **config["candidates"]["A-Subtle"],
        "voice_preset": "ultron_conversational",
    }
    plan = delivery_plan("First sentence. Second sentence. Third sentence.", 1, False, True)
    assert all(pause == 0 for _, _, pause, _ in plan)


async def test_broken_worker_pipe_is_reaped_and_meter_cleared(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "private"))
    python = tmp_path / ".venv-infernal/Scripts/python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr("immortility_broker.voice.ROOT", tmp_path)
    store = Store(tmp_path / "state.db")
    try:
        voice = VoiceService(
            Settings(_env_file=None, data_dir=tmp_path, infernal_voice_enabled=True),
            store,
            AsyncMock(),
            AsyncMock(),
        )
        worker = Mock(returncode=None)
        worker.stdin.drain = AsyncMock(side_effect=BrokenPipeError)
        worker.wait = AsyncMock(return_value=1)
        voice.infernal_process = worker
        voice.level = 0.4
        with pytest.raises(BrokenPipeError):
            await voice.worker("speak", voice="infernal", text="public test")
        worker.kill.assert_called_once()
        worker.wait.assert_awaited_once()
        assert voice.infernal_process is None and voice.level == 0
    finally:
        store.db.close()


@pytest.mark.asyncio
async def test_reap_failure_does_not_mask_broken_pipe_or_leave_meter(tmp_path, monkeypatch):
    """M2/P0: a cleanup failure must not replace the original error or leak meter state."""
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "private"))
    python = tmp_path / ".venv-infernal/Scripts/python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr("immortility_broker.voice.ROOT", tmp_path)
    store = Store(tmp_path / "state.db")
    try:
        voice = VoiceService(
            Settings(_env_file=None, data_dir=tmp_path, infernal_voice_enabled=True),
            store,
            AsyncMock(),
            AsyncMock(),
        )
        worker = Mock(returncode=None, pid=0)
        worker.stdin.drain = AsyncMock(side_effect=BrokenPipeError)
        worker.wait = AsyncMock(side_effect=TimeoutError)
        voice.infernal_process = worker
        voice.level = 0.7
        with pytest.raises(BrokenPipeError):
            await voice.worker("speak", voice="infernal", text="public test")
        worker.kill.assert_called_once()
        assert voice.infernal_process is None and voice.level == 0
    finally:
        store.db.close()


@pytest.mark.asyncio
async def test_reap_kills_owned_child_when_descendant_lookup_fails(monkeypatch):
    from immortility_broker import process_owner

    def broken_lookup(_root: int) -> None:
        raise OSError("toolhelp snapshot failed")

    monkeypatch.setattr(process_owner, "_terminate_descendants", broken_lookup)
    child = Mock(returncode=None, pid=4242)
    child.wait = AsyncMock(return_value=1)
    await process_owner.reap(child, None)
    child.kill.assert_called_once()
    child.wait.assert_awaited_once()
