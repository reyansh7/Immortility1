"""Broker-owned, keyless, on-demand reference voice process. No agent tools or cloud APIs."""

import asyncio
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .process_owner import ProcessOwner, reap, spawn_owned
from .contracts import BrokerError
from .reference_contracts import ROOT, ReferenceRequest, sha256, is_junction


class ReferenceVoice:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.process: asyncio.subprocess.Process | None = None
        self.owner: ProcessOwner | None = None
        self.turn = asyncio.Lock()
        self.lifecycle = asyncio.Lock()
        self.ready = False
        self.used_at = time.monotonic()
        self.metrics: dict[str, float] = {}
        self.diagnostic_path: Path | None = None
        self.diagnostic_log: Any = None

    async def start(self) -> None:
        if not self.enabled:
            raise BrokerError("reference_disabled", "The reference voice is disabled.")
        async with self.lifecycle:
            if self.process and self.process.returncode is None:
                return
            python = ROOT / ".venv-reference-tts/Scripts/python.exe"
            if not python.is_file():
                raise BrokerError(
                    "reference_setup", "Install the isolated reference voice runtime first."
                )
            folder = ROOT / ".cache/reference-tts"
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
                    "USERPROFILE",
                    "LOCALAPPDATA",
                    "APPDATA",
                }
            }
            env.update(
                PYTHONPATH=str(ROOT / "services/broker/src"),
                PYTHONUTF8="1",
                PYTHONUNBUFFERED="1",
                IMMORTILITY_REFERENCE_EVALUATION="1",
                TORCH_FORCE_WEIGHTS_ONLY_LOAD="1",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                HF_HUB_DISABLE_TELEMETRY="1",
                HF_HOME=str(folder / "hf"),
                TORCH_HOME=str(folder / "torch"),
                WANDB_MODE="disabled",
                TOKENIZERS_PARALLELISM="false",
                OMP_NUM_THREADS="2",
            )
            if self.diagnostic_path is not None:
                self.diagnostic_log = self.diagnostic_path.open("w", encoding="utf-8")
            self.process, self.owner = await spawn_owned(
                str(python),
                "-m",
                "immortility_broker.reference_worker",
                cwd=ROOT,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=self.diagnostic_log if self.diagnostic_log else asyncio.subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

    async def request(self, operation: str, text: str = "", speed: float = 1.0) -> dict[str, Any]:
        async with self.turn:
            if not self.enabled:
                raise BrokerError("reference_disabled", "The reference voice is disabled.")
            request = ReferenceRequest.model_validate(
                {
                    "evaluation_authorized": True,
                    "run_id": uuid.uuid4().hex,
                    "operation": operation,
                    "text": text,
                    "speed": speed,
                    "model_manifest_sha256": sha256(ROOT / "config/reference-tts-models.json"),
                    "reference_manifest_sha256": sha256(
                        ROOT / "data/reference-tts/reference/reference.json"
                    ),
                }
            )
            await self.start()
            assert self.process and self.process.stdin and self.process.stdout
            started = time.monotonic()
            try:
                async with asyncio.timeout(120):
                    self.process.stdin.write((request.model_dump_json() + "\n").encode())
                    await self.process.stdin.drain()
                    while line := await self.process.stdout.readline():
                        frame = json.loads(line)
                        if frame["kind"] == "error":
                            if frame.get("code") == "insufficient_available_ram":
                                raise BrokerError(
                                    "reference_ram",
                                    "Reference voice needs at least 2 GiB of free RAM after runtime imports. Close an unused app and try again.",
                                )
                            raise BrokerError(
                                "reference_failed",
                                "Reference voice failed. Check available RAM, CUDA and the pinned runtime/model setup.",
                            )
                        if frame["kind"] == "done":
                            self.ready = True
                            self.used_at = time.monotonic()
                            self.metrics["last_render_ms"] = 1000 * (self.used_at - started)
                            for key in (
                                "load_seconds",
                                "resident_ram_mib",
                                "gpu_allocated_mib",
                                "gpu_reserved_mib",
                            ):
                                if key in frame:
                                    self.metrics[key] = float(frame[key])
                            return dict(frame)
                    raise BrokerError("reference_lost", "The reference voice worker exited.")
            except BaseException:
                await self.close()
                folder = ROOT / "data/reference-tts/runs" / request.run_id
                if not folder.is_symlink() and not is_junction(folder):
                    for name in (
                        "normal-conditioned-dry.partial.wav",
                        "normal-conditioned-dry.wav",
                        "mechanical.wav",
                    ):
                        path = folder / name
                        if (
                            path.is_file()
                            and not path.is_symlink()
                            and path.resolve().parent == folder.resolve()
                        ):
                            path.unlink()
                raise

    async def prepare(self) -> None:
        await self.request("prepare")

    async def render(self, text: str, speed: float) -> Path:
        frame = await self.request("speak", text, speed)
        path = (ROOT / str(frame["path"])).resolve()
        allowed = (ROOT / "data/reference-tts/runs").resolve()
        if (
            not path.is_relative_to(allowed)
            or path.name != "mechanical.wav"
            or not path.is_file()
            or path.stat().st_size > 2_000_000
        ):
            raise BrokerError("reference_output", "Reference voice returned an invalid output.")
        return path

    async def close(self) -> None:
        async with self.lifecycle:
            process, self.process = self.process, None
            self.ready = False
            owner, self.owner = self.owner, None
            if process is not None:
                await reap(process, owner)
            if self.diagnostic_log:
                self.diagnostic_log.close()
                self.diagnostic_log = None
