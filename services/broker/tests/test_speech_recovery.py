"""Speech regressions without microphone capture, speaker output or model downloads."""

import ctypes
import asyncio
import json
import sys
import wave
from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest

from immortility_broker import voice_worker as worker
from immortility_broker.voice import VoiceOptions


def whisper(monkeypatch, factory):
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=factory))
    monkeypatch.setitem(
        sys.modules,
        "ctranslate2",
        SimpleNamespace(
            get_cuda_device_count=lambda: 1, get_supported_compute_types=lambda _: {"float16"}
        ),
    )
    monkeypatch.setattr("immortility_broker.gpu_budget.free_vram_mib", lambda: 4000)
    monkeypatch.setattr("immortility_broker.gpu_budget.allow_light_gpu", lambda _: True)
    monkeypatch.setattr(ctypes, "WinDLL", lambda _: object(), raising=False)


def test_cpu_is_default_and_never_probes_cuda(monkeypatch, tmp_path):
    calls = []

    def factory(*args, **options):
        calls.append(options)
        return SimpleNamespace(
            transcribe=lambda *a, **kw: (iter([SimpleNamespace(text="CPU answer")]), None)
        )

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=factory))
    monkeypatch.setitem(sys.modules, "ctranslate2", None)
    assert VoiceOptions().stt_device == "cpu"
    assert worker.WhisperSTT(tmp_path).transcribe(tmp_path / "synthetic.wav", "en") == "CPU answer"
    assert calls == [
        {
            "device": "cpu",
            "compute_type": "int8",
            "cpu_threads": 2,
            "num_workers": 1,
            "local_files_only": True,
        }
    ]


@pytest.mark.parametrize("failure", ["initialization", "lazy_iterator"])
def test_cuda_falls_back_once_and_does_not_duplicate_partial_segments(
    monkeypatch, tmp_path, failure, capsys
):
    calls = []

    def factory(*args, **options):
        calls.append(options["device"])
        if options["device"] == "cuda":
            if failure == "initialization":
                raise RuntimeError("PRIVATE_CANARY")

            def broken(*args, **kwargs):
                def segments():
                    yield SimpleNamespace(text="discard this GPU partial")
                    raise RuntimeError("PRIVATE_CANARY")

                return segments(), None

            return SimpleNamespace(transcribe=broken)
        return SimpleNamespace(
            transcribe=lambda *a, **kw: (iter([SimpleNamespace(text="Complete CPU answer")]), None)
        )

    whisper(monkeypatch, factory)
    recognizer = worker.WhisperSTT(tmp_path, "auto")
    assert recognizer.transcribe(tmp_path / "synthetic.wav", "en") == "Complete CPU answer"
    assert recognizer.device == "cpu" and calls == ["cuda", "cpu"]
    metadata = capsys.readouterr().out
    assert "stt_cpu_fallback" in metadata and "PRIVATE_CANARY" not in metadata


def test_cpu_failure_is_not_retried_indefinitely(monkeypatch, tmp_path):
    calls = []

    def factory(*args, **kwargs):
        calls.append(kwargs["device"])
        raise OSError("CPU model absent")

    whisper(monkeypatch, factory)
    with pytest.raises(OSError):
        worker.WhisperSTT(tmp_path, "auto")
    assert calls == ["cuda", "cpu"]


def test_multisentence_render_sets_wave_format_once(monkeypatch, tmp_path):
    chunk = SimpleNamespace(sample_channels=1, sample_rate=16000, audio_int16_bytes=b"\0\0" * 160)
    monkeypatch.setattr(
        worker, "PiperTTS", lambda *args: SimpleNamespace(chunks=lambda _: iter([chunk, chunk]))
    )
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace())
    destination = tmp_path / "fixture.wav"
    worker.speak(
        {
            "text": "First sentence. Second sentence.",
            "models": str(tmp_path),
            "path": str(destination),
        },
        render=True,
    )
    with wave.open(str(destination), "rb") as audio:
        assert (audio.getnchannels(), audio.getframerate(), audio.getnframes()) == (1, 16000, 320)


def test_failure_reports_operation_without_exception_text(monkeypatch, tmp_path, capsys):
    def broken(*args, **kwargs):
        raise RuntimeError("PRIVATE_AUDIO_OR_KEY_CANARY")

    monkeypatch.setattr(worker, "WhisperSTT", broken)
    worker.handle({"operation": "transcribe", "models": str(tmp_path), "path": "fixture.wav"})
    output = capsys.readouterr().out
    assert "CANARY" not in output
    error = json.loads(output.splitlines()[-1])
    assert error == {
        "kind": "error",
        "code": "speech_recognition_unavailable",
        "stage": "speech_recognition",
        "error_type": "runtime_error",
    }


@pytest.mark.parametrize("failure", [OSError, asyncio.CancelledError])
async def test_control_pipe_setup_failure_always_reaps_owned_voice_worker(
    monkeypatch, tmp_path, failure
):
    from immortility_broker.config import Settings
    from immortility_broker.store import Store
    from immortility_broker.voice import VoiceService

    class Sink:
        def write(self, data):
            pass

        async def drain(self):
            raise failure()

    process = SimpleNamespace(stdin=Sink(), stdout=object(), returncode=0)
    monkeypatch.setattr(
        "immortility_broker.voice.spawn_owned", AsyncMock(return_value=(process, object()))
    )
    store = Store(tmp_path / "voice.sqlite3")
    voice = VoiceService(
        Settings(_env_file=None, data_dir=tmp_path), store, AsyncMock(), AsyncMock()
    )
    voice.stop_worker = AsyncMock()
    try:
        with pytest.raises(failure):
            await voice.worker("devices")
        voice.stop_worker.assert_awaited_once()
        assert "cleanup_ms" in voice.diagnostic
    finally:
        store.db.close()
