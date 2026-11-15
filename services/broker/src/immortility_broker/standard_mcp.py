"""Fixed, default-off SDK interoperability path, independent of Hermes tool access."""

import asyncio
import hashlib
import json
import math
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import ROOT
from .contracts import BrokerError
from .process_owner import reap, spawn_owned


@dataclass
class SdkProbe:
    """Optional local measurements. No arguments, stderr bodies or paths retained."""

    started: float = field(default_factory=time.perf_counter)
    phases_ms: dict[str, float] = field(default_factory=dict)
    worker_ms: dict[str, float] = field(default_factory=dict)
    resources: dict[str, int | float] = field(default_factory=dict)
    status: str = "started"
    cleanup_confirmed: bool = False

    def mark(self, phase: str) -> None:
        self.phases_ms[phase] = round((time.perf_counter() - self.started) * 1000, 3)

    def worker(self, raw: bytes) -> None:
        try:
            value = json.loads(raw)
            phase, milliseconds = value["phase"], value["milliseconds"]
            if (
                phase
                in {
                    "dependency_metadata",
                    "client_import",
                    "client_construct",
                    "server_spawn",
                    "server_import",
                    "server_construct",
                    "handshake",
                    "discovery",
                    "first_invocation",
                    "client_cleanup",
                    "stdio_cleanup",
                }
                and type(milliseconds) in {float, int}
                and math.isfinite(milliseconds)
                and 0 <= milliseconds <= 60000
            ):
                self.worker_ms[phase] = milliseconds
        except (ValueError, KeyError, TypeError):
            pass


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewed_runtime() -> Path:
    """No executable, args, package, or URL comes from the model/server/user call."""
    try:
        manifest = json.loads((ROOT / "config/mcp-standard-runtime.json").read_text())
        python = ROOT / ".venv-mcp/Scripts/python.exe"
        if file_hash(python) != manifest["python_sha256"]:
            raise ValueError
        for name, expected in manifest["files"].items():
            path = ROOT / name
            if file_hash(path) != expected:
                raise ValueError
        return python
    except (OSError, ValueError, KeyError, TypeError):
        raise BrokerError(
            "mcp_unavailable", "Reviewed SDK runtime or fixed manifest changed.", 503
        ) from None


def reviewed_agent_bridge() -> tuple[Path, Path]:
    python = reviewed_runtime()
    script = ROOT / "integrations/mcp-standard/agent_bridge.py"
    try:
        manifest = json.loads((ROOT / "config/agent-bridge-runtime.json").read_text())
        if file_hash(script) != manifest["script_sha256"]:
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise BrokerError("mcp_unavailable", "Reviewed broker bridge changed.", 503) from None
    return python, script


async def sdk_request(
    operation: str,
    a: int = 0,
    b: int = 0,
    *,
    enabled: bool = False,
    probe: SdkProbe | None = None,
) -> dict[str, Any]:
    if not enabled or operation not in {"discover", "add"}:
        raise BrokerError(
            "tool_denied", "Standard MCP is disabled or the operation is not allowed.", 403
        )
    if type(a) is not int or type(b) is not int or abs(a) > 10**9 or abs(b) > 10**9:
        raise BrokerError("invalid_request", "Bounded integer arguments required.", 400)
    python = reviewed_runtime()
    if probe:
        probe.mark("manifest_validated")
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    env.update(
        PYTHONUTF8="1", PYTHONUNBUFFERED="1", HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1"
    )
    with tempfile.TemporaryDirectory(prefix="mcp-", dir=ROOT / ".cache") as directory:
        env.update(USERPROFILE=directory, APPDATA=directory, LOCALAPPDATA=directory)
        process, owner = await spawn_owned(
            str(python),
            "-I",
            str(ROOT / "integrations/mcp-standard/sdk_client.py"),
            cwd=directory,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=65536,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if probe:
            probe.mark("spawned")
        stage = "startup"

        async def diagnostics() -> None:
            nonlocal stage
            assert process.stderr is not None
            total = 0
            while line := await process.stderr.readline():
                total += len(line)
                if total > 16000:
                    return
                if probe and line.startswith(b"IMMORTILITY_MCP_TIMING "):
                    probe.worker(line[len(b"IMMORTILITY_MCP_TIMING ") :])
                if line.startswith(b"IMMORTILITY_MCP_STAGE "):
                    value = line.decode("ascii", "ignore").strip().split()[-1]
                    if value in {
                        "import",
                        "input",
                        "initialize",
                        "ready",
                        "listed",
                        "closing",
                        "completed",
                    }:
                        stage = value

        diagnostic = asyncio.create_task(diagnostics())
        try:
            assert process.stdin is not None and process.stdout is not None
            async with asyncio.timeout(10):
                process.stdin.write(
                    (json.dumps({"operation": operation, "a": a, "b": b}) + "\n").encode()
                )
                await process.stdin.drain()
                process.stdin.close()
                if probe:
                    probe.mark("request_sent")
                line = await process.stdout.readline()
                if probe:
                    probe.mark("result_delivered")
                if len(line) > 16000:
                    raise BrokerError("output_limit", "MCP output exceeds the manifest limit.", 413)
                result = json.loads(line)
                if not isinstance(result, dict) or "error" in result:
                    raise ValueError
                await process.wait()
                if process.returncode != 0:
                    raise ValueError
                if probe:
                    probe.mark("worker_exited")
                    probe.status = "passed"
                return dict(result)
        except (TimeoutError, OSError, ValueError):
            if probe:
                probe.status = "failed"
            raise BrokerError(
                "mcp_failed", f"The standard MCP operation failed during {stage}.", 503
            ) from None
        except asyncio.CancelledError:
            if probe:
                probe.status = "cancelled"
            raise
        finally:
            try:
                if probe:
                    probe.mark("cleanup_started")
                    try:
                        probe.resources = owner.statistics()
                    except OSError:
                        pass
            finally:
                # Even a programming error in optional counters cannot skip reaping.
                try:
                    await reap(process, owner)
                    if probe:
                        probe.cleanup_confirmed = True
                finally:
                    await diagnostic
                    if probe:
                        probe.mark("cleanup_finished")
