"""Local audio lifecycle around the existing task engine, never an alternate chat engine."""

import asyncio
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import ROOT, Settings
from .contracts import BrokerError, TaskRequest, TERMINAL, uid
from .playback import CLONE_PLAYBACK_TEMPO, play_wav
from .speech_text import for_speech, ready_sentences
from .store import Store
from .tts_client import ERRORS as TTS_ERRORS
from .tts_client import QwenWorker
from .voice_models import ready
from .voice_store import (
    PREVIEW_PHRASE,
    REFERENCE_TRANSCRIPT,
    consent_granted,
    delete_clone,
    load_voice_settings,
    profile_ready,
    reference_wav,
    require_source,
    save_voice_settings,
    write_consent,
)

VoiceState = Literal[
    "IDLE", "LISTENING", "TRANSCRIBING", "THINKING", "SPEAKING", "CANCELLED", "ERROR"
]
TRANSITIONS: dict[str, set[str]] = {
    "IDLE": {"LISTENING", "SPEAKING", "ERROR"},
    "LISTENING": {"TRANSCRIBING", "CANCELLED", "ERROR"},
    "TRANSCRIBING": {"THINKING", "IDLE", "CANCELLED", "ERROR"},
    "THINKING": {"SPEAKING", "IDLE", "CANCELLED", "ERROR"},
    "SPEAKING": {"IDLE", "CANCELLED", "ERROR"},
    "CANCELLED": {"IDLE", "LISTENING", "SPEAKING", "ERROR"},
    "ERROR": {"IDLE", "LISTENING", "SPEAKING", "ERROR"},
}


class VoiceOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    input_device: int | None = Field(default=None, ge=0, le=1000)
    output_device: int | None = Field(default=None, ge=0, le=1000)
    language: Literal["en", "hi", "es", "fr", "de", "ja", "auto"] = "en"
    stt_device: Literal["cpu", "auto"] = "cpu"
    voice: Literal["ljspeech", "joe", "friend"] = "ljspeech"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=0.7, ge=0, le=1)
    response_length: Literal["brief", "normal", "detailed"] = "brief"
    auto_speak: bool = True
    voice_output: bool = False
    clone_consent: bool = False


class RecordRequest(VoiceOptions):
    session_id: str = Field(min_length=1, max_length=64)
    microphone_consent: Literal[True]
    cloud_consent: bool = False

    @field_validator("microphone_consent", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit microphone consent is required.")
        return value


ERRORS = {
    "audio_device_or_engine_unavailable": "Audio device or local engine unavailable. Check device selection, Windows microphone permission and installed models.",
    "recording_too_short": "Hold push-to-talk a little longer before releasing.",
    "microphone_consent_required": "Enable microphone consent before recording.",
    "no_speech": "No speech was detected. Nothing was sent to the cloud.",
    "voice_timeout": "Local voice operation timed out and was stopped.",
}


class VoiceService:
    def __init__(
        self,
        settings: Settings,
        store: Store,
        admit: Callable[[TaskRequest], Awaitable[dict[str, Any]]],
        cancel_task: Callable[[str], Awaitable[None]],
    ):
        self.settings, self.store, self.admit, self.cancel_task = (
            settings,
            store,
            admit,
            cancel_task,
        )
        self.state: VoiceState = "IDLE"
        self.models = settings.data_dir / "models"
        self.level = 0.0
        self.error: str | None = None
        self.transcript = ""
        self.task_id: str | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.worker_lock = asyncio.Lock()
        self.job: asyncio.Task[None] | None = None
        self.stop_requested = False
        self.options = VoiceOptions()
        self.latency: dict[str, float] = {}
        self.preparing = False
        self.utterance_id: str | None = None
        self.qwen = QwenWorker(enabled=settings.experimental_qwen_tts)
        self.playback_stop = threading.Event()
        self.speech_generation = 0
        self.speech_buffer = ""
        self.speech_spoken = 0
        self.speech_final = False
        self.speech_task: str | None = None
        self.tts_state = "cold"
        self.tts_error: str | None = None
        self.idle_at: float | None = None
        saved = load_voice_settings(settings.data_dir)
        if saved:
            with contextlib.suppress(ValueError):
                self.options = VoiceOptions.model_validate(saved)
        if self.options.clone_consent and not consent_granted():
            self.options = self.options.model_copy(update={"clone_consent": False})
        # Only our marked ephemeral capture directories are eligible for crash cleanup.
        for path in settings.data_dir.glob("voice-*"):
            if (
                not path.is_symlink()
                and path.resolve().parent == settings.data_dir.resolve()
                and (path / ".voice-capture").is_file()
            ):
                shutil.rmtree(path)

    def transition(self, state: VoiceState) -> None:
        if state not in TRANSITIONS[self.state]:
            raise BrokerError("voice_transition", "Invalid voice state transition.")
        self.state = state
        self.level = 0.0

    def snapshot(self) -> dict[str, Any]:
        self._maybe_unload()
        return {
            "schema_version": "1.0",
            "utterance_id": self.utterance_id,
            "state": self.state,
            "level": self.level,
            "error": self.error,
            "transcript": self.transcript,
            "task_id": self.task_id,
            "models_ready": ready(self.models),
            "preparing": self.preparing,
            "latency_ms": self.latency,
            "microphone_active": self.state == "LISTENING",
            "cloud_audio": False,
            "wake_word": False,
            "profile_ready": profile_ready(),
            "tts_state": self.tts_state,
            "tts_error": self.tts_error,
            "cloned_voice": self.options.voice == "friend" and self.state == "SPEAKING",
            "metrics": self.qwen.metrics,
            "options": self.options.model_dump(),
            "experimental_qwen_enabled": self.settings.experimental_qwen_tts,
        }

    def _maybe_unload(self) -> None:
        process = self.qwen.process
        if (
            self.idle_at is None
            or self.state != "IDLE"
            or (self.job and not self.job.done())
            or time.monotonic() - self.idle_at < 600
            or process is None
            or process.returncode is not None
        ):
            return
        self.idle_at = None
        with contextlib.suppress(RuntimeError):
            asyncio.get_running_loop().create_task(self.qwen.shutdown())

    async def worker(self, operation: str, **options: Any) -> dict[str, Any]:
        async with self.worker_lock:
            return await self._worker(operation, **options)

    async def _worker(self, operation: str, **options: Any) -> dict[str, Any]:
        if operation == "speak" and options.get("voice") == "friend":
            await self.play_clone_text(str(options.get("text", "")))
            return {"kind": "done"}
        env = {
            k: v
            for k, v in os.environ.items()
            if k.upper()
            in {
                "SYSTEMROOT",
                "WINDIR",
                "PATH",
                "TEMP",
                "TMP",
                "COMSPEC",
                "PATHEXT",
                "USERPROFILE",
                "LOCALAPPDATA",
                "APPDATA",
            }
        }
        env.update(
            PYTHONPATH=str(ROOT / "services/broker/src"),
            PYTHONUTF8="1",
            PYTHONUNBUFFERED="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
            OMP_NUM_THREADS="2",
        )
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "immortility_broker.voice_worker",
            env=env,
            cwd=ROOT,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert self.process.stdin and self.process.stdout
        self.process.stdin.write(
            (
                json.dumps({"operation": operation, "models": str(self.models), **options}) + "\n"
            ).encode()
        )
        if operation == "record" and self.stop_requested:
            self.process.stdin.write(b"stop\n")
        await self.process.stdin.drain()
        try:
            timeout = 600 if operation == "prepare" else 40 if operation == "record" else 120
            started = time.monotonic()
            async with asyncio.timeout(timeout):
                while line := await self.process.stdout.readline():
                    frame = json.loads(line)
                    if frame["kind"] == "error":
                        code = str(frame.get("code", "audio_device_or_engine_unavailable"))
                        raise BrokerError(code, ERRORS.get(code, "Local voice operation failed."))
                    if frame["kind"] == "meter":
                        self.level = float(frame["level"])
                    if frame["kind"] == "ready" and operation == "speak":
                        self.latency["tts_first_audio"] = 1000 * (time.monotonic() - started)
                    if frame["kind"] == "done":
                        return dict(frame)
            raise BrokerError("voice_worker_lost", "Local audio worker exited before completion.")
        except TimeoutError:
            raise BrokerError("voice_timeout", ERRORS["voice_timeout"]) from None
        finally:
            await self.stop_worker()

    async def stop_worker(self) -> None:
        if self.process and self.process.returncode is None:
            if os.name == "nt":
                killer = await asyncio.create_subprocess_exec(
                    "taskkill.exe",
                    "/PID",
                    str(self.process.pid),
                    "/T",
                    "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                await asyncio.wait_for(killer.wait(), 3)
            else:
                self.process.kill()
            await asyncio.wait_for(self.process.wait(), 3)
        self.process = None

    def ensure_idle(self) -> None:
        if (self.job and not self.job.done()) or self.preparing or self.worker_lock.locked():
            raise BrokerError("voice_busy", "Stop the current voice operation first.")

    async def prepare(self) -> dict[str, Any]:
        self.ensure_idle()
        self.preparing = True
        try:
            return await self.worker("prepare")
        finally:
            self.preparing = False

    def begin_prepare(self) -> dict[str, Any]:
        self.ensure_idle()
        self.preparing = True
        self.error = None

        async def run() -> None:
            try:
                await self.worker("prepare")
            except asyncio.CancelledError:
                raise
            except Exception:
                self.error = "Model download failed. Check the network and try again; no microphone was opened."
            finally:
                self.preparing = False

        self.job = asyncio.create_task(run())
        return self.snapshot()

    async def devices(self) -> dict[str, Any]:
        self.ensure_idle()
        return await self.worker("devices")

    def start(self, request: RecordRequest) -> dict[str, Any]:
        self.ensure_idle()
        if not ready(self.models):
            raise BrokerError("voice_setup", "Download the local speech models before recording.")
        if not self.store.db.execute(
            "SELECT 1 FROM sessions WHERE id=?", (request.session_id,)
        ).fetchone():
            raise BrokerError("not_found", "Session not found.", 404)
        self.options = VoiceOptions.model_validate(
            request.model_dump(exclude={"session_id", "microphone_consent", "cloud_consent"})
        )
        if self.options.clone_consent:
            write_consent(True)
        self.error = None
        self.utterance_id = uid()
        self.transcript = ""
        self.task_id = None
        self.stop_requested = False
        self.latency = {}
        self.transition("LISTENING")
        self.job = asyncio.create_task(self.conversation(request))
        return self.snapshot()

    async def finish_recording(self) -> dict[str, Any]:
        if self.state != "LISTENING":
            return self.snapshot()
        self.stop_requested = True
        if self.process and self.process.stdin:
            self.process.stdin.write(b"stop\n")
            with contextlib.suppress(OSError, ConnectionError):
                await self.process.stdin.drain()
        return self.snapshot()

    async def conversation(self, request: RecordRequest) -> None:
        try:
            with tempfile.TemporaryDirectory(
                prefix="voice-", dir=self.settings.data_dir
            ) as directory:
                path = Path(directory) / "capture.wav"
                Path(directory, ".voice-capture").touch()
                await self.worker(
                    "record",
                    path=str(path),
                    microphone_consent=True,
                    input_device=request.input_device,
                )
                self.transition("TRANSCRIBING")
                started = time.monotonic()
                result = await self.worker(
                    "transcribe",
                    path=str(path),
                    language=request.language,
                    stt_device=request.stt_device,
                )
                self.latency["stt"] = 1000 * (time.monotonic() - started)
                self.transcript = str(result["text"]).strip()
            if not self.transcript:
                raise BrokerError("no_speech", ERRORS["no_speech"])
            if not request.cloud_consent:
                self.transition("IDLE")
                return
            self.transition("THINKING")
            task = await self.admit(
                TaskRequest(
                    session_id=request.session_id,
                    request_id=uid(),
                    content=self.transcript,
                    cloud_consent=True,
                    source="voice",
                    response_length=request.response_length,
                )
            )
            task_id = str(task["task_id"])
            self.task_id = task_id
            while task["status"] not in TERMINAL:
                await asyncio.sleep(0.1)
                task = self.store.get(task_id)
            if task["status"] != "succeeded":
                raise BrokerError(
                    "voice_task_failed",
                    task.get("error", {}).get("message", "The conversation was interrupted."),
                )
            if request.auto_speak:
                self.transition("SPEAKING")
                started = time.monotonic()
                await self.worker("speak", text=task["result"]["text"], **self.options.model_dump())
                self.latency["tts_total"] = 1000 * (time.monotonic() - started)
            self.transition("IDLE")
        except asyncio.CancelledError:
            if self.state not in {"CANCELLED", "IDLE"}:
                self.transition("CANCELLED")
            raise
        except Exception as error:
            self.error = (
                error.message if isinstance(error, BrokerError) else "Local voice operation failed."
            )
            self.transition("ERROR")
        finally:
            self.level = 0.0

    def _require_clone_consent(self, options: VoiceOptions) -> None:
        if options.voice == "friend" and not (options.clone_consent and consent_granted()):
            raise BrokerError(
                "clone_consent_required",
                "Confirm your friend authorized this cloned voice before enabling it.",
            )

    def apply_options(self, options: VoiceOptions) -> dict[str, Any]:
        if options.voice == "friend" and not options.clone_consent:
            raise BrokerError(
                "clone_consent_required",
                "Confirm your friend authorized this cloned voice before enabling it.",
            )
        write_consent(options.clone_consent)
        self.options = options
        save_voice_settings(self.settings.data_dir, options.model_dump())
        self.tts_error = None
        return self.snapshot()

    def note_assistant_text(self, task_id: str, text: str, final: bool) -> None:
        if not self.options.voice_output:
            return
        if self.speech_task not in {None, task_id}:
            return
        if self.speech_task != task_id:
            self.speech_generation += 1
            self.speech_spoken = 0
            self.speech_task = task_id
            self.playback_stop.clear()
        self.speech_buffer = text
        self.speech_final = final
        generation = self.speech_generation
        if self.job and not self.job.done():
            return
        self.job = asyncio.create_task(self._drive_speech(generation))

    async def _drive_speech(self, generation: int) -> None:
        self.qwen.stop.clear()
        try:
            if self.options.voice == "friend":
                self._require_clone_consent(self.options)
                await self._stream_clone(generation)
            elif self.speech_final and generation == self.speech_generation:
                if not ready(self.models):
                    raise BrokerError("voice_setup", "Download local speech models first.")
                if self.state != "SPEAKING":
                    self.transition("SPEAKING")
                await self.worker(
                    "speak", text=for_speech(self.speech_buffer), **self.options.model_dump()
                )
            if generation == self.speech_generation and self.state == "SPEAKING":
                self.transition("IDLE")
                self.tts_state = "ready" if self.options.voice == "friend" else self.tts_state
        except asyncio.CancelledError:
            if self.state == "SPEAKING":
                self.transition("CANCELLED")
            raise
        except Exception as error:
            self.error = (
                error.message
                if isinstance(error, BrokerError)
                else "Local speech failed. Text chat is unchanged."
            )
            self.tts_error = self.error
            self.tts_state = "error"
            self.transition("ERROR")
        finally:
            self.level = 0.0
            self.idle_at = time.monotonic()

    async def _stream_clone(self, generation: int) -> None:
        self.tts_state = "loading"
        while generation == self.speech_generation:
            fresh, self.speech_spoken = ready_sentences(
                self.speech_buffer, self.speech_spoken, self.speech_final
            )
            if not fresh:
                if self.speech_final:
                    return
                await asyncio.sleep(0.05)
                continue
            for sentence in fresh:
                if generation != self.speech_generation or self.playback_stop.is_set():
                    return
                await self._utter(sentence)

    async def play_clone_text(self, text: str) -> None:
        self.qwen.stop.clear()
        self.playback_stop.clear()
        self._require_clone_consent(self.options)
        self.tts_state = "loading"
        sentences, _count = ready_sentences(text, 0, True)
        try:
            for sentence in sentences:
                if self.playback_stop.is_set():
                    return
                await self._utter(sentence)
            self.tts_state = "ready"
        finally:
            self.idle_at = time.monotonic()

    async def _utter(self, sentence: str) -> None:
        if not profile_ready():
            await self._build_profile()
        self.tts_error = None
        started = time.monotonic()
        wav = await self.qwen.synthesize(sentence)
        if wav is None or self.playback_stop.is_set():
            if wav is not None:
                wav.unlink(missing_ok=True)
            return
        if self.state != "SPEAKING":
            self.transition("SPEAKING")
        self.tts_state = "speaking"
        if "tts_first_audio" not in self.latency:
            self.latency["tts_first_audio"] = 1000 * (time.monotonic() - started)
        try:
            await asyncio.to_thread(
                play_wav,
                wav,
                self.options.volume,
                self.playback_stop,
                self._set_level,
                CLONE_PLAYBACK_TEMPO,
            )
        finally:
            wav.unlink(missing_ok=True)

    def _set_level(self, level: float) -> None:
        self.level = level

    async def _build_profile(self) -> None:
        try:
            source = require_source()
        except FileNotFoundError:
            raise BrokerError("reference_missing", TTS_ERRORS["reference_missing"]) from None
        self.tts_state = "loading"
        await self.qwen.build(source, reference_wav(), REFERENCE_TRANSCRIPT)
        if not profile_ready():
            raise BrokerError("corrupt_profile", TTS_ERRORS["corrupt_profile"])

    def speak_task(self, task_id: str, options: VoiceOptions) -> dict[str, Any]:
        self.ensure_idle()
        task = self.store.get(task_id)
        if task["status"] != "succeeded":
            raise BrokerError(
                "tts_no_response", "Only completed assistant responses can be spoken."
            )
        if options.voice != "friend" and not ready(self.models):
            raise BrokerError("voice_setup", "Download local speech models first.")
        if options.clone_consent:
            write_consent(True)
        self._require_clone_consent(options)
        self.error = None
        self.tts_error = None
        self.options = options
        save_voice_settings(self.settings.data_dir, options.model_dump())
        self.task_id = task_id
        self.playback_stop.clear()
        self.transition("SPEAKING")

        async def run() -> None:
            try:
                spoken = for_speech(str(task["result"]["text"]))
                if options.voice == "friend":
                    await self.play_clone_text(spoken)
                else:
                    await self.worker("speak", text=spoken, **options.model_dump())
                self.transition("IDLE")
            except asyncio.CancelledError:
                self.transition("CANCELLED")
                raise
            except Exception as error:
                self.error = (
                    error.message
                    if isinstance(error, BrokerError)
                    else ERRORS["audio_device_or_engine_unavailable"]
                )
                self.tts_error = self.error
                self.tts_state = "error"
                self.transition("ERROR")

        self.job = asyncio.create_task(run())
        return self.snapshot()

    def preview(self, options: VoiceOptions) -> dict[str, Any]:
        self.ensure_idle()
        self.apply_options(options)
        self._require_clone_consent(options)
        if options.voice != "friend" and not ready(self.models):
            raise BrokerError("voice_setup", "Download local speech models first.")
        self.playback_stop.clear()
        self.error = None
        self.transition("SPEAKING")

        async def run() -> None:
            try:
                if options.voice == "friend":
                    await self.play_clone_text(PREVIEW_PHRASE)
                else:
                    await self.worker("speak", text=PREVIEW_PHRASE, **options.model_dump())
                if self.state == "SPEAKING":
                    self.transition("IDLE")
            except asyncio.CancelledError:
                if self.state == "SPEAKING":
                    self.transition("CANCELLED")
                raise
            except Exception as error:
                self.tts_error = (
                    error.message if isinstance(error, BrokerError) else "Local speech failed."
                )
                self.tts_state = "error"
                if self.state == "SPEAKING":
                    self.transition("ERROR")

        self.job = asyncio.create_task(run())
        return self.snapshot()

    async def delete_profile(self) -> dict[str, Any]:
        self.ensure_idle()
        await self.qwen.shutdown()
        self.qwen = QwenWorker(enabled=self.settings.experimental_qwen_tts)
        delete_clone()
        self.options = self.options.model_copy(
            update={"voice": "ljspeech", "clone_consent": False, "voice_output": False}
        )
        save_voice_settings(self.settings.data_dir, self.options.model_dump())
        self.tts_state = "cold"
        self.tts_error = None
        return self.snapshot()

    async def interrupt(self, task_id: str) -> None:
        if self.speech_task == task_id:
            await self.cancel()

    async def cancel(self) -> dict[str, Any]:
        self.speech_generation += 1
        self.playback_stop.set()
        self.qwen.stop.set()
        if self.job and not self.job.done():
            self.job.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.job
        await self.stop_worker()
        with contextlib.suppress(OSError, ConnectionError):
            await self.qwen.cancel()
        self.preparing = False
        if self.state not in {"IDLE", "CANCELLED", "ERROR"}:
            self.transition("CANCELLED")
        if self.task_id and self.store.get(self.task_id)["status"] not in TERMINAL:
            await self.cancel_task(self.task_id)
        self.level = 0.0
        return self.snapshot()
