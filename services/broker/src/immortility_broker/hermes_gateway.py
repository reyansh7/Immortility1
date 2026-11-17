"""Warm Hermes 0.23.2 client. The broker remains the permission authority.

The official v0.23.2 checkout pins its core dependencies to Python 3.14.
On 3.13 the source is installed side by side and this client stays idle.
"""

import asyncio
import json
import os
import secrets
import subprocess
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx

from .contracts import BrokerError
from .permission_policy import govern

GATEWAY_VERSION = "0.23.2"
GATEWAY_REVISION = "ae2a81ccc00e9b7c06301523e5bb09608397149c"
REQUIRED_PYTHON = (3, 14)


def run_phase(status: str) -> str:
    """A stop acknowledgement is still in progress. It is not a finished cancellation."""
    return {
        "started": "running",
        "running": "running",
        "stopping": "stopping",
        "cancelled": "cancelled",
        "completed": "completed",
        "failed": "failed",
        "interrupted": "recovery_required",
        "unknown": "recovery_required",
    }.get(status, "recovery_required")


def runtime_available(version: tuple[int, int] | None = None) -> bool:
    import sys

    return (version or sys.version_info[:2]) >= REQUIRED_PYTHON


def interpret_hook(
    payload: Any, *, crashed: bool = False, timed_out: bool = False, disabled: bool = False
) -> str:
    """Hermes skips a bad pre_tool_call result. Immortility denies it instead."""
    if crashed or timed_out or disabled:
        return "deny"
    if not isinstance(payload, dict):
        return "deny"
    action = payload.get("action")
    message = payload.get("message")
    if action == "block":
        if not isinstance(message, str) or not message.strip():
            return "deny"
        return "deny"
    if action == "approve" and (message is None or isinstance(message, str)):
        return "approval"
    if action == "allow":
        return "allow"
    return "deny"


def authorize_call(
    capability: str,
    profile: str,
    hook: Any = None,
    *,
    crashed: bool = False,
    timed_out: bool = False,
    disabled: bool = False,
    policy: dict[str, object] | None = None,
) -> str:
    hook_decision = interpret_hook(
        hook, crashed=crashed, timed_out=timed_out, disabled=disabled
    )
    if hook_decision == "deny":
        return "deny"
    decision = govern(capability, profile, policy)
    if decision != "allow":
        return decision
    if hook_decision == "approval":
        return "approval"
    return "allow"


def guard_directive(capability: str, profile: str, **flags: Any) -> dict[str, str]:
    decision = authorize_call(capability, profile, **flags)
    if decision == "allow":
        return {"action": "allow"}
    return {"action": "block", "message": "BLOCKED: broker denied " + capability}


class WarmGateway:
    """One HTTP session reused across runs. A failed health check does not mark it warm."""

    def __init__(self, base_url: str, key: str, client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.key = key
        self.client = client
        self.ready = False
        self.starts = 0
        self.reuses = 0
        self.active_run: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self.key}

    async def ensure(self) -> None:
        if self.ready:
            self.reuses += 1
            return
        try:
            response = await self.client.get(self.base_url + "/health", headers=self._headers())
        except httpx.HTTPError as error:
            raise BrokerError(
                "hermes_unavailable", "Hermes gateway is not answering.", 503
            ) from error
        if response.status_code != 200:
            raise BrokerError("hermes_unavailable", "Hermes gateway is not ready.", 503)
        self.ready = True
        self.starts += 1

    async def run(
        self,
        content: str,
        history: list[dict[str, str]],
        idempotency_key: str | None = None,
    ) -> AsyncIterator[str]:
        await self.ensure()
        headers = self._headers()
        if idempotency_key and idempotency_key.isascii() and 1 <= len(idempotency_key) <= 255:
            headers["Idempotency-Key"] = idempotency_key
        try:
            opened = await self.client.post(
                self.base_url + "/v1/runs",
                headers=headers,
                json={"input": content, "conversation_history": history},
            )
        except httpx.HTTPError as error:
            raise BrokerError("hermes_unavailable", "Hermes gateway rejected the run.", 503) from error
        if opened.status_code != 202:
            raise BrokerError("hermes_unavailable", "Hermes gateway did not start a run.", 503)
        body = opened.json()
        run_id = body.get("run_id")
        if not isinstance(run_id, str) or not run_id.startswith("run_"):
            raise BrokerError("hermes_unavailable", "Hermes gateway returned no run id.", 503)
        self.active_run = run_id
        yielded = False
        try:
            async with self.client.stream(
                "GET", self.base_url + "/v1/runs/" + run_id + "/events", headers=self._headers()
            ) as events:
                async for line in events.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        event = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    kind = event.get("event") if isinstance(event.get("event"), str) else event.get("type")
                    if kind == "message.delta":
                        piece = event.get("delta", event.get("text"))
                        if isinstance(piece, str) and piece:
                            yielded = True
                            yield piece
                    elif kind == "run.completed":
                        if not yielded:
                            piece = event.get("output", event.get("text"))
                            if isinstance(piece, str) and piece:
                                yield piece
                        return
                    elif kind == "run.cancelled":
                        return
                    elif kind == "run.failed":
                        detail = event.get("error") or event.get("message") or ""
                        if not isinstance(detail, str):
                            detail = ""
                        detail = " ".join(detail.split())[:160]
                        raise BrokerError(
                            "runtime_error",
                            "Hermes run failed." + (f" {detail}" if detail else ""),
                            503,
                        )
        finally:
            if self.active_run == run_id:
                self.active_run = None

    async def cancel(self) -> None:
        run_id = self.active_run
        if not run_id:
            return
        await self.client.post(
            self.base_url + "/v1/runs/" + run_id + "/stop", headers=self._headers()
        )

    async def shutdown(self) -> None:
        self.ready = False
        await self.client.aclose()


class GatewayRuntime:
    """One turn on the already-running gateway. Stopping a turn does not stop the process."""

    accepts_broker_schemas = True

    def __init__(self, gateway: WarmGateway):
        self.gateway = gateway
        self.broker_schemas: list[dict[str, Any]] = []
        self.response_length = "normal"
        self.idempotency_key = ""
        self.spawn_ms: float | None = None
        self.ready_ms: float | None = None
        self.reused = False

    async def run(
        self, content: str, history: list[dict[str, str]], role: str | None = None
    ) -> AsyncIterator[str]:
        del role
        async for piece in self.gateway.run(
            content, history, self.idempotency_key or None
        ):
            yield piece

    async def stop(self) -> None:
        await self.gateway.cancel()


async def loopback_port_open(port: int) -> bool:
    """True when something is already accepting connections. Does not send data."""
    try:
        _reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), 0.4)
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return True


def _broker_already_in_job() -> bool:
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.IsProcessInJob.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.BOOL),
    ]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    inside = wintypes.BOOL()
    return bool(
        kernel.IsProcessInJob(kernel.GetCurrentProcess(), None, ctypes.byref(inside))
        and inside.value
    )


class GatewaySupervisor:
    """One loopback Hermes 0.23.2 API server, owned by a Windows job."""

    def __init__(self, settings: Any, broker_url: str):
        self.data_dir = settings.data_dir
        local = os.environ.get("LOCALAPPDATA", "")
        self.home = Path(local) / "h0232"
        self.source = Path(local) / "Immortility" / "hermes-0.23.2"
        self.broker_url = broker_url.rstrip("/")
        self.url = "http://127.0.0.1:8642"
        self.api_key = secrets.token_hex(32)
        self.inference_key = secrets.token_urlsafe(32)
        self.runtime_ready = False
        self.state = "unavailable"
        self.cold_start_ms: float | None = None
        self._sessions = 0
        self.gateway: WarmGateway | None = None
        self.process: Any = None
        self.owner: Any = None
        self._log: Any = None

    def session(self) -> GatewayRuntime:
        if self.gateway is None or self.state != "ready":
            raise BrokerError("hermes_unavailable", "Hermes gateway is not ready.", 503)
        runtime = GatewayRuntime(self.gateway)
        if self._sessions == 0 and self.cold_start_ms is not None:
            runtime.spawn_ms = self.cold_start_ms
            runtime.ready_ms = self.cold_start_ms
        else:
            runtime.reused = True
        self._sessions += 1
        return runtime

    def _python(self) -> Path:
        matches = sorted(
            self.home.glob("installs/*/environments/*/venv/Scripts/python.exe")
        )
        if len(matches) != 1:
            raise BrokerError(
                "hermes_unavailable",
                "The isolated Hermes 0.23.2 interpreter is not installed.",
                503,
            )
        return matches[0]

    def _verify_checkout(self) -> None:
        try:
            head = (self.source / ".git" / "HEAD").read_text(encoding="utf-8").strip()
            if head.startswith("ref: "):
                revision = (self.source / ".git" / head[5:]).read_text(encoding="utf-8").strip()
            else:
                revision = head
        except OSError as error:
            raise BrokerError(
                "hermes_unavailable", "Cannot confirm the Hermes 0.23.2 checkout.", 503
            ) from error
        if revision != GATEWAY_REVISION:
            raise BrokerError(
                "hermes_incompatible", "Hermes 0.23.2 revision differs from the reviewed pin.", 503
            )

    def _write_config(self) -> None:
        from .hermes import isolated_config

        schemas = [
            {
                "manifest": {"name": "clock.now.v1"},
                "input_schema": {"properties": {}, "required": [], "$defs": {}},
                "output_schema": {"properties": {"timestamp": {}}},
            },
            {
                "manifest": {"name": "arithmetic.multiply.v1"},
                "input_schema": {
                    "properties": {"a": {}, "b": {}},
                    "required": ["a", "b"],
                    "$defs": {},
                },
                "output_schema": {"properties": {"result": {}}},
            },
            {
                "manifest": {"name": "project.outline.v1"},
                "input_schema": {"properties": {}, "required": [], "$defs": {}},
                "output_schema": {"properties": {}},
            },
        ]
        config = isolated_config(
            self.source,
            self.broker_url + "/inference/v1",
            self.inference_key,
            broker_schemas=schemas,
        )
        config["agent"]["max_turns"] = 8
        config["approvals"] = {
            "mode": "manual",
            "cron_mode": "deny",
            "single_query_mode": "deny",
            "unattended_mode": "deny",
        }
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "config.yaml").write_text(
            json.dumps(config), encoding="utf-8"
        )
        (self.home / ".env").write_text(
            "\n".join(
                [
                    "API_SERVER_ENABLED=true",
                    "API_SERVER_HOST=127.0.0.1",
                    "API_SERVER_PORT=8642",
                    "API_SERVER_KEY=" + self.api_key,
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _environment(self) -> dict[str, str]:
        root = os.environ.get("SYSTEMROOT", r"C:\Windows")
        return {
            "SYSTEMROOT": root,
            "WINDIR": os.environ.get("WINDIR", root),
            "COMSPEC": os.environ.get("COMSPEC", root + r"\System32\cmd.exe"),
            "PATHEXT": os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD"),
            "PATH": os.environ.get("PATH", ""),
            "TEMP": os.environ.get("TEMP", ""),
            "TMP": os.environ.get("TMP", ""),
            "HERMES_HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "LOCALAPPDATA": str(self.home / "AppData" / "Local"),
            "APPDATA": str(self.home / "AppData" / "Roaming"),
            "API_SERVER_ENABLED": "true",
            "API_SERVER_HOST": "127.0.0.1",
            "API_SERVER_PORT": "8642",
            "API_SERVER_KEY": self.api_key,
            "HERMES_NONINTERACTIVE": "1",
            "HERMES_GATEWAY_NO_SUPERVISE": "1",
            "HERMES_GATEWAY_INSTALL_START_ON_LOGIN": "0",
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONNOUSERSITE": "1",
        }

    def _step(self, text: str) -> None:
        if not self.data_dir.name.startswith("canary-"):
            return
        path = self.data_dir / "gateway-steps.log"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")

    async def start(self) -> None:
        if self.runtime_ready:
            return
        if await loopback_port_open(8642):
            raise BrokerError(
                "hermes_unavailable",
                "Gateway port 8642 is already in use. The existing listener was left running.",
                503,
            )
        self.state = "starting"
        started = time.perf_counter()
        self._step("start")
        self._verify_checkout()
        self._step("verified")
        python = self._python()
        self._step("python")
        self._write_config()
        self._step("config")
        log_path = self.home / "logs" / "gateway-stderr.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = open(log_path, "ab", buffering=0)
        from .process_owner import reap, spawn_owned

        self._step("spawn")
        try:
            command = (
                str(python),
                "-m",
                "hermes_cli.main",
                "gateway",
                "run",
            )
            spawned = dict(
                cwd=str(self.home),
                env=self._environment(),
                stdin=subprocess.DEVNULL,
                stdout=self._log,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            # The desktop already owns the broker in a kill-on-close job. A second
            # suspended job inside that job never reaches the gateway listener.
            if _broker_already_in_job():
                self.process = await asyncio.create_subprocess_exec(*command, **spawned)
                self.owner = None
            else:
                self.process, self.owner = await spawn_owned(*command, **spawned)
            self._step("spawned")
        except Exception:
            self._log.close()
            self._log = None
            raise
        deadline = time.monotonic() + 120
        async with httpx.AsyncClient(trust_env=False, timeout=5) as probe:
            while time.monotonic() < deadline:
                if self.process.returncode is not None:
                    await self.stop()
                    raise BrokerError(
                        "hermes_unavailable", "Hermes gateway exited during startup.", 503
                    )
                try:
                    response = await probe.get(
                        self.url + "/health",
                        headers={"Authorization": "Bearer " + self.api_key},
                    )
                except httpx.HTTPError:
                    await asyncio.sleep(0.5)
                    continue
                self._step("health " + str(response.status_code))
                if response.status_code == 200:
                    client = httpx.AsyncClient(trust_env=False, timeout=120)
                    self.gateway = WarmGateway(self.url, self.api_key, client)
                    self.gateway.ready = True
                    self.gateway.starts = 1
                    self.cold_start_ms = round((time.perf_counter() - started) * 1000, 1)
                    self.runtime_ready = True
                    self.state = "ready"
                    return
                await asyncio.sleep(0.5)
        await self.stop()
        raise BrokerError("hermes_unavailable", "Hermes gateway did not become ready.", 503)

    async def stop(self) -> None:
        self.state = "stopping"
        self.runtime_ready = False
        gateway, self.gateway = self.gateway, None
        if gateway is not None:
            await gateway.shutdown()
        process, owner = self.process, self.owner
        self.process = None
        self.owner = None
        if process is not None:
            from .process_owner import reap

            await reap(process, owner)
        if self._log is not None:
            self._log.close()
            self._log = None
        self.state = "stopped"
