"""Long-lived client for the isolated Qwen3-TTS process."""

import asyncio
import contextlib
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

from .config import ROOT
from .contracts import BrokerError, uid
from .voice_store import metadata_path, playback_dir, profile_path, voice_root

ERRORS = {
    "cuda_unavailable": "CUDA is not available for local speech. CPU fallback is disabled.",
    "clone_consent_required": "Confirm your friend authorized this voice before using it.",
    "reference_missing": "The reference recording was not found. Nothing was synthesized.",
    "profile_missing": "The cloned voice profile is missing. Create it before speaking.",
    "silent_audio": "Local speech produced silence and was discarded.",
    "tts_failed": "Local speech failed. Text chat is unchanged.",
    "tts_runtime_missing": "Install the local Qwen3-TTS environment with scripts/install-qwen-tts.ps1.",
    "corrupt_profile": "The cloned voice profile could not be read and was not loaded.",
    "experimental_qwen_disabled": "Experimental Qwen speech is disabled pending security and native verification. Select LJ or Joe for local Piper speech.",
}


def tts_python() -> Path:
    candidate = ROOT / ".venv-tts" / "Scripts" / "python.exe"
    if candidate.is_file():
        return candidate
    raise BrokerError("tts_runtime_missing", ERRORS["tts_runtime_missing"])


class QwenWorker:
    """One process, one GPU request at a time. Spoken text is not logged."""

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled
        self.process: asyncio.subprocess.Process | None = None
        self.pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self.outputs: dict[str, Path] = {}
        self.reader: asyncio.Task[None] | None = None
        self.turn = asyncio.Lock()
        self.lifecycle = asyncio.Lock()
        self.stop = asyncio.Event()
        self.metrics: dict[str, float] = {}

    async def start(self) -> None:
        if not self.enabled:
            raise BrokerError("experimental_qwen_disabled", ERRORS["experimental_qwen_disabled"])
        async with self.lifecycle:
            await self._start()

    async def _start(self) -> None:
        if self.process and self.process.returncode is None:
            return
        python = tts_python()
        root = voice_root()
        root.mkdir(parents=True, exist_ok=True)
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper()
            in {
                "SYSTEMROOT",
                "WINDIR",
                "PATH",
                "TEMP",
                "TMP",
                "COMSPEC",
                "PATHEXT",
                "USERPROFILE",
                "USERNAME",
                "USER",
                "LOCALAPPDATA",
                "APPDATA",
                "CUDA_PATH",
            }
        }
        account = os.environ.get("USERNAME") or os.environ.get("USER") or "immortility"
        env.update(
            USERNAME=account,
            USER=account,
            PYTHONPATH=str(ROOT / "services/tts/src"),
            PYTHONUTF8="1",
            PYTHONUNBUFFERED="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
            HF_HUB_DISABLE_PROGRESS_BARS="1",
            HF_HOME=str(root / "hf-cache"),
            TORCHINDUCTOR_CACHE_DIR=str(root / "torch-cache"),
            TRANSFORMERS_VERBOSITY="error",
            TQDM_DISABLE="1",
            TOKENIZERS_PARALLELISM="false",
        )
        self.process = await asyncio.create_subprocess_exec(
            str(python),
            "-m",
            "immortility_tts.worker",
            cwd=ROOT,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            # Upstream exception/warning payloads can contain private text or paths.
            # The worker's fixed protocol error codes are the supported diagnostic surface.
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.reader = asyncio.create_task(self._read())

    async def _read(self) -> None:
        assert self.process and self.process.stdout
        process = self.process
        assert process.stdout
        while line := await process.stdout.readline():
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            request_id = str(message.get("id", ""))
            future = self.pending.pop(request_id, None)
            expected = self.outputs.get(request_id)
            reported = message.get("path")
            try:
                valid_path = (
                    expected is not None
                    and isinstance(reported, str)
                    and Path(reported).resolve() == expected.resolve()
                )
            except (OSError, ValueError):
                valid_path = False
            if reported is not None and not valid_path:
                message = {"kind": "error", "code": "tts_failed"}
            if self.stop.is_set() and expected is not None:
                self._discard(expected)
            if future and not future.done():
                future.set_result(message)
        for future in self.pending.values():
            if not future.done():
                future.set_exception(BrokerError("tts_failed", ERRORS["tts_failed"]))
        self.pending.clear()

    async def request(self, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        expected = self._output(Path(payload["out"])) if "out" in payload else None
        # Serialize startup too: simultaneous first requests must not spawn two GPU models.
        async with self.turn:
            await self.start()
            assert self.process and self.process.stdin
            request_id = str(payload["id"])
            future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
            self.pending[request_id] = future
            if expected is not None:
                self.outputs[request_id] = expected
            try:
                self.process.stdin.write((json.dumps(payload) + "\n").encode())
                await self.process.stdin.drain()
                return await asyncio.wait_for(asyncio.shield(future), timeout)
            except TimeoutError:
                await self._kill()
                raise BrokerError(
                    "voice_timeout", "Local speech timed out and was stopped."
                ) from None
            except asyncio.CancelledError:
                await self._kill()
                raise
            except (OSError, ConnectionError):
                await self._kill()
                raise BrokerError("tts_failed", ERRORS["tts_failed"]) from None
            finally:
                self.pending.pop(request_id, None)
                self.outputs.pop(request_id, None)
                if not future.done():
                    future.cancel()
                elif not future.cancelled():
                    future.exception()  # Consume an EOF error even when cancellation won the race.
                if self.stop.is_set() and expected is not None:
                    self._discard(expected)

    @staticmethod
    def _output(path: Path) -> Path:
        if (
            path.is_symlink()
            or path.suffix != ".wav"
            or path.resolve().parent != playback_dir().resolve()
        ):
            raise BrokerError("tts_failed", ERRORS["tts_failed"])
        return path

    def _discard(self, path: Path) -> None:
        # Never delete a path supplied by the worker; only a broker-owned expected output.
        with contextlib.suppress(OSError, BrokerError):
            self._output(path).unlink(missing_ok=True)

    def _raise(self, message: dict[str, Any]) -> None:
        if message.get("kind") == "error":
            code = str(message.get("code", "tts_failed"))
            raise BrokerError(code, ERRORS.get(code, ERRORS["tts_failed"]))

    async def synthesize(self, text: str) -> Path | None:
        if self.stop.is_set():
            return None
        out = playback_dir() / f"{uuid.uuid4().hex}.wav"
        message = await self.request(
            {
                "op": "synthesize",
                "id": uid(),
                "text": text,
                "profile": str(profile_path()),
                "metadata": str(metadata_path()),
                "out": str(out),
            },
            180,
        )
        self._remember(message)
        if message.get("kind") == "cancelled" or self.stop.is_set():
            out.unlink(missing_ok=True)
            return None
        self._raise(message)
        return out

    async def build(self, source: Path, reference: Path, transcript: str) -> dict[str, Any]:
        message = await self.request(
            {
                "op": "build",
                "id": uid(),
                "consent": True,
                "source": str(source),
                "reference": str(reference),
                "profile": str(profile_path()),
                "metadata": str(metadata_path()),
                "transcript": transcript,
            },
            900,
        )
        self._remember(message)
        self._raise(message)
        return message

    def _remember(self, message: dict[str, Any]) -> None:
        for key in (
            "seconds",
            "load_seconds",
            "profile_seconds",
            "build_seconds",
            "peak_vram_mb",
            "retained_vram_mb",
            "duration_seconds",
        ):
            if isinstance(message.get(key), (int, float)):
                self.metrics[key] = float(message[key])

    async def cancel(self) -> None:
        self.stop.set()
        # The worker handles inference synchronously: a queued JSON cancel cannot interrupt
        # a CUDA forward. Reap the owned process instead of claiming it has stopped.
        await self._kill()

    async def shutdown(self) -> None:
        self.stop.set()
        await self._kill()

    async def _kill(self) -> None:
        # A concurrent new request must not start while the old reader/process is reaped.
        async with self.lifecycle:
            await self._kill_owned()

    async def _kill_owned(self) -> None:
        process = self.process
        # Idle workers can exit on EOF without a platform taskkill/WMI round trip.
        if process and process.returncode is None and process.stdin:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), 0.2)
            except TimeoutError:
                pass
        if process and process.returncode is None:
            if os.name == "nt":
                killer = await asyncio.create_subprocess_exec(
                    "taskkill.exe",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    env={
                        key: value
                        for key, value in os.environ.items()
                        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH"}
                    },
                )
                try:
                    await asyncio.wait_for(killer.wait(), 3)
                except TimeoutError:
                    killer.kill()
                    await asyncio.wait_for(killer.wait(), 3)
                    if process.returncode is None:
                        process.kill()
                        await asyncio.wait_for(process.wait(), 3)
                    raise BrokerError(
                        "tts_failed",
                        "Audio tree cleanup could not be confirmed. Quit the app to close its owned process tree.",
                    ) from None
            else:
                process.kill()
            await asyncio.wait_for(process.wait(), 3)
        if self.reader and self.reader is not asyncio.current_task():
            self.reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.reader
            self.reader = None
        for future in self.pending.values():
            if not future.done():
                future.set_exception(BrokerError("tts_failed", ERRORS["tts_failed"]))
        self.pending.clear()
        self.process = None
