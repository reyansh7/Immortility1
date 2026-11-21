"""Warm Hermes 0.23.2 client. The broker remains the permission authority.

The official v0.23.2 checkout pins its core dependencies to Python 3.14.
On 3.13 the source is installed side by side and this client stays idle.
"""

import asyncio
import contextlib
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

# Reviewed gateway pins. ``home`` is the HERMES_HOME under %LOCALAPPDATA% (kept short because
# the Hermes package workspace exceeds MAX_PATH under longer roots); ``source`` is the checkout
# under %LOCALAPPDATA%. A ``canary_only`` pin is refused unless the broker data directory is an
# isolated ``canary-*`` directory, so a candidate can never become the desktop runtime by a flag.
GATEWAY_PINS: dict[str, dict[str, Any]] = {
    "0.23.2": {
        "revision": GATEWAY_REVISION,
        "home": "h0232",
        "source": "Immortility/hermes-0.23.2",
        "canary_only": False,
    },
    "0.23.3": {
        "revision": "caafe5389ae585ef77387a962aee05b1bcf17029",
        # Junction to %LOCALAPPDATA%\Immortility\canary-0233-home (files live in the canary dir).
        "home": "h0233",
        "source": "Immortility/canary-0233-src",
        "canary_only": True,
    },
}


def gateway_pin(version: str, data_dir: Path) -> dict[str, Any]:
    """The reviewed pin for ``version``; candidate pins only inside a canary data dir."""
    pin = GATEWAY_PINS.get(version)
    if pin is None:
        raise BrokerError("hermes_incompatible", "No reviewed pin for that Hermes version.", 503)
    if pin["canary_only"] and not Path(data_dir).name.startswith("canary-"):
        raise BrokerError(
            "hermes_incompatible",
            "Hermes " + version + " is a canary candidate and cannot run outside a canary.",
            503,
        )
    return pin


def run_phase(status: str) -> str:
    """A stop acknowledgement is still in progress. It is not a finished cancellation."""
    return {
        "queued": "running",
        "claimed": "running",
        "started": "running",
        "running": "running",
        "waiting_for_approval": "awaiting_approval",
        "stopping": "stopping",
        "cancelled": "cancelled",
        "completed": "completed",
        "failed": "failed",
        "interrupted": "recovery_required",
        "unknown": "recovery_required",
    }.get(status, "recovery_required")


# A run in one of these phases has no live executor left inside Hermes.
CONFIRMED_STOPPED = frozenset({"cancelled", "completed", "failed"})
HERMES_TERMINAL = frozenset({"completed", "failed", "cancelled", "interrupted"})
MAX_RUN_EVENTS = 20000
MAX_RUN_TEXT_BYTES = 1_000_000
MAX_STREAM_RECONNECTS = 3


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
    hook_decision = interpret_hook(hook, crashed=crashed, timed_out=timed_out, disabled=disabled)
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
        self.runs: dict[str, str] = {}
        self.duplicates_dropped = 0
        self.reconnects = 0
        self.native_approvals_denied = 0
        self.cancelled_during_create = 0

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
        on_run: Any = None,
        instructions: str | None = None,
    ) -> AsyncIterator[str]:
        await self.ensure()
        headers = self._headers()
        if idempotency_key and idempotency_key.isascii() and 1 <= len(idempotency_key) <= 255:
            headers["Idempotency-Key"] = idempotency_key
        body: dict[str, Any] = {"input": content, "conversation_history": history}
        if instructions:
            # Ephemeral per-run instructions (M2/P1 run binding); Hermes appends them to
            # the system prompt at API-call time and never persists them.
            body["instructions"] = instructions
        creating = asyncio.ensure_future(
            self.client.post(self.base_url + "/v1/runs", headers=headers, json=body)
        )
        try:
            opened = await asyncio.shield(creating)
        except asyncio.CancelledError:
            # Cancelled while Hermes was creating the run. Hermes may already have started it;
            # learn its id and stop it, so it cannot keep running and borrow the next task's
            # inference grant through the shared warm key.
            await self._stop_run_created_during_cancel(creating, on_run)
            raise
        except httpx.HTTPError as error:
            raise BrokerError(
                "hermes_unavailable", "Hermes gateway rejected the run.", 503
            ) from error
        if opened.status_code != 202:
            raise BrokerError("hermes_unavailable", "Hermes gateway did not start a run.", 503)
        body = opened.json()
        run_id = body.get("run_id")
        if not isinstance(run_id, str) or not run_id.startswith("run_"):
            raise BrokerError("hermes_unavailable", "Hermes gateway returned no run id.", 503)
        self.active_run = run_id
        self.runs[run_id] = "running"
        if on_run is not None:
            on_run(run_id)
        yielded = False
        last_seq = -1
        seen = 0
        text_bytes = 0
        reconnects = 0
        try:
            while True:
                stream_headers = self._headers()
                if last_seq >= 0:
                    stream_headers["Last-Event-ID"] = str(last_seq)
                try:
                    async with self.client.stream(
                        "GET",
                        self.base_url + "/v1/runs/" + run_id + "/events",
                        headers=stream_headers,
                    ) as events:
                        if events.status_code != 200:
                            raise BrokerError(
                                "hermes_lost", "Hermes run events are unavailable.", 503
                            )
                        async for line in events.aiter_lines():
                            if not line.startswith("data:"):
                                continue
                            try:
                                event = json.loads(line[5:].strip())
                            except json.JSONDecodeError:
                                continue
                            if not isinstance(event, dict):
                                continue
                            seq = event.get("seq")
                            if type(seq) is int:
                                # A reconnect replays from Last-Event-ID. Never apply one event twice.
                                if seq <= last_seq:
                                    self.duplicates_dropped += 1
                                    continue
                                last_seq = seq
                            seen += 1
                            if seen > MAX_RUN_EVENTS:
                                raise BrokerError(
                                    "hermes_lost", "Hermes run produced too many events.", 503
                                )
                            kind = (
                                event.get("event")
                                if isinstance(event.get("event"), str)
                                else event.get("type")
                            )
                            if kind == "replay.truncated":
                                raise BrokerError(
                                    "hermes_lost", "Hermes run events were lost on reconnect.", 503
                                )
                            if kind == "approval.request":
                                # Native Hermes tools are off. A native approval is never relayed
                                # as consent: deny that exact request and keep the broker in charge.
                                await self._deny_native_approval(run_id, event)
                                continue
                            if kind == "message.delta":
                                piece = event.get("delta", event.get("text"))
                                if isinstance(piece, str) and piece:
                                    text_bytes += len(piece.encode())
                                    if text_bytes > MAX_RUN_TEXT_BYTES:
                                        raise BrokerError(
                                            "hermes_lost",
                                            "Hermes run text exceeded its bound.",
                                            503,
                                        )
                                    yielded = True
                                    yield piece
                            elif kind == "run.completed":
                                self.runs[run_id] = "completed"
                                if not yielded:
                                    piece = event.get("output", event.get("text"))
                                    if isinstance(piece, str) and piece:
                                        yield piece
                                return
                            elif kind in {"run.cancelled", "run.interrupted"}:
                                self.runs[run_id] = kind[4:]
                                raise BrokerError(
                                    "hermes_lost",
                                    "Hermes ended the run without a broker stop request.",
                                    503,
                                )
                            elif kind == "run.failed":
                                self.runs[run_id] = "failed"
                                detail = event.get("error") or event.get("message") or ""
                                if not isinstance(detail, str):
                                    detail = ""
                                detail = " ".join(detail.split())[:160]
                                raise BrokerError(
                                    "runtime_error",
                                    "Hermes run failed." + (f" {detail}" if detail else ""),
                                    503,
                                )
                except httpx.HTTPError:
                    pass
                # The stream closed without a terminal event. Reconnect with Last-Event-ID.
                reconnects += 1
                self.reconnects += 1
                if reconnects > MAX_STREAM_RECONNECTS:
                    raise BrokerError(
                        "hermes_lost", "Hermes run stream ended without a result.", 503
                    )
                await asyncio.sleep(0.1 * reconnects)
        finally:
            if self.active_run == run_id:
                self.active_run = None

    async def _deny_native_approval(self, run_id: str, event: dict[str, Any]) -> None:
        request_id = event.get("request_id")
        if not isinstance(request_id, str):
            approval = event.get("approval")
            request_id = approval.get("request_id") if isinstance(approval, dict) else None
        body: dict[str, Any] = {"choice": "deny"}
        if isinstance(request_id, str) and 0 < len(request_id) <= 256:
            body["request_id"] = request_id
        self.native_approvals_denied += 1
        try:
            await self.client.post(
                self.base_url + "/v1/runs/" + run_id + "/approval",
                headers=self._headers(),
                json=body,
            )
        except httpx.HTTPError:
            pass

    async def status(self, run_id: str) -> str:
        try:
            response = await self.client.get(
                self.base_url + "/v1/runs/" + run_id, headers=self._headers()
            )
        except httpx.HTTPError:
            return "unknown"
        if response.status_code != 200:
            return "unknown"
        try:
            status = response.json().get("status")
        except ValueError:
            return "unknown"
        return status if isinstance(status, str) else "unknown"

    async def _stop_run_created_during_cancel(self, creating: Any, on_run: Any) -> None:
        try:
            opened = await asyncio.wait_for(asyncio.shield(creating), 5.0)
            run_id = opened.json().get("run_id") if opened.status_code == 202 else None
        except Exception:
            creating.cancel()
            return
        if not isinstance(run_id, str) or not run_id.startswith("run_"):
            return
        self.runs[run_id] = "running"
        self.cancelled_during_create += 1
        if on_run is not None:
            on_run(run_id)
        with contextlib.suppress(Exception):
            await self.stop_and_confirm(run_id)

    async def stop_and_confirm(self, run_id: str, timeout: float = 5.0) -> str:
        """Ask Hermes to stop one run, then poll until it reports a terminal status.

        Returns the broker phase. Anything other than cancelled/completed/failed means the
        executor was not confirmed stopped and the task needs recovery.
        """
        known = self.runs.get(run_id)
        if known in HERMES_TERMINAL:
            return run_phase(known)
        try:
            await self.client.post(
                self.base_url + "/v1/runs/" + run_id + "/stop", headers=self._headers()
            )
        except httpx.HTTPError:
            pass
        deadline = time.monotonic() + timeout
        phase = "recovery_required"
        while True:
            status = await self.status(run_id)
            phase = run_phase(status)
            if status in HERMES_TERMINAL:
                self.runs[run_id] = status
                break
            if time.monotonic() >= deadline:
                break
            await asyncio.sleep(0.05)
        return phase

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
    stop_timeout = 5.0

    def __init__(self, gateway: WarmGateway):
        self.gateway = gateway
        self.broker_schemas: list[dict[str, Any]] = []
        self.response_length = "normal"
        self.idempotency_key = ""
        self.spawn_ms: float | None = None
        self.ready_ms: float | None = None
        self.reused = False
        self.run_id: str | None = None
        self.stop_phase: str | None = None
        self.on_run: Any = None
        self.supervisor: Any = None
        self.run_binding: str | None = None

    def _bind(self, run_id: str) -> None:
        self.run_id = run_id
        if self.on_run is not None:
            self.on_run(run_id)

    async def run(
        self, content: str, history: list[dict[str, str]], role: str | None = None
    ) -> AsyncIterator[str]:
        del role
        if self.supervisor is not None:
            # A gateway that died between turns is restarted (bounded) before this turn.
            await self.supervisor.recover_if_crashed()
            if self.supervisor.gateway is not None:
                self.gateway = self.supervisor.gateway
        from .run_binding import marker

        async for piece in self.gateway.run(
            content,
            history,
            self.idempotency_key or None,
            on_run=self._bind,
            instructions=marker(self.run_binding) if self.run_binding else None,
        ):
            yield piece

    async def stop(self) -> None:
        """Stop this turn's run and record whether Hermes confirmed it stopped."""
        if self.run_id is None:
            self.stop_phase = "not_started"
            return
        self.stop_phase = await self.gateway.stop_and_confirm(self.run_id, self.stop_timeout)


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
    """One loopback Hermes gateway API server (reviewed pin), owned by a Windows job."""

    # Class defaults keep the reviewed 0.23.2 pin for callers that bypass __init__.
    version = GATEWAY_VERSION
    revision = GATEWAY_REVISION
    settings: Any = None

    def __init__(self, settings: Any, broker_url: str):
        self.data_dir = settings.data_dir
        self.settings = settings
        self.version = str(getattr(settings, "hermes_gateway_version", GATEWAY_VERSION))
        pin = gateway_pin(self.version, self.data_dir)
        self.revision = str(pin["revision"])
        local = os.environ.get("LOCALAPPDATA", "")
        self.home = Path(local) / str(pin["home"])
        self.source = Path(local) / str(pin["source"])
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
        self.python: Path | None = None
        self.last_stop: dict[str, Any] = {}
        self.reclaimed_orphan = False
        self.graceful_timeout = 8.0
        self.ready_timeout = 120.0
        self.crash_restarts = 0
        self.max_crash_restarts = 3

    def session(self) -> GatewayRuntime:
        if self.gateway is None or self.state != "ready":
            raise BrokerError("hermes_unavailable", "Hermes gateway is not ready.", 503)
        runtime = GatewayRuntime(self.gateway)
        runtime.supervisor = self
        if self._sessions == 0 and self.cold_start_ms is not None:
            runtime.spawn_ms = self.cold_start_ms
            runtime.ready_ms = self.cold_start_ms
        else:
            runtime.reused = True
        self._sessions += 1
        return runtime

    def _python(self) -> Path:
        matches = sorted(self.home.glob("installs/*/environments/*/venv/Scripts/python.exe"))
        if len(matches) != 1:
            raise BrokerError(
                "hermes_unavailable",
                "The isolated Hermes " + self.version + " interpreter is not installed.",
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
                "hermes_unavailable",
                "Cannot confirm the Hermes " + self.version + " checkout.",
                503,
            ) from error
        if revision != self.revision:
            raise BrokerError(
                "hermes_incompatible",
                "Hermes " + self.version + " revision differs from the reviewed pin.",
                503,
            )

    def _write_config(self) -> None:
        from .hermes import isolated_config

        typed = bool(getattr(self.settings, "typed_tool_schemas_enabled", False))
        outputs = {
            "clock.now.v1": {"timestamp": {}},
            "arithmetic.multiply.v1": {"result": {}},
            "project.outline.v1": {},
        }
        schemas = []
        for name, output in outputs.items():
            if typed:
                # Exact strict input schemas from the broker's Pydantic models (the same
                # models that validate every proposal), not hand-written placeholders.
                from .agent_bridge import capability_input

                full = capability_input(name).model_json_schema()
                input_schema = {
                    "properties": full.get("properties", {}),
                    "required": full.get("required", []),
                    "$defs": full.get("$defs", {}),
                }
            else:
                fields = ["a", "b"] if name == "arithmetic.multiply.v1" else []
                input_schema = {
                    "properties": {field: {} for field in fields},
                    "required": fields,
                    "$defs": {},
                }
            schemas.append(
                {
                    "manifest": {"name": name},
                    "input_schema": input_schema,
                    "output_schema": {"properties": output},
                }
            )
        config = isolated_config(
            self.source,
            self.broker_url + "/inference/v1",
            self.inference_key,
            broker_schemas=schemas,
            typed_tools=typed,
        )
        config["agent"]["max_turns"] = 8
        config["approvals"] = {
            "mode": "manual",
            "cron_mode": "deny",
            "single_query_mode": "deny",
            "unattended_mode": "deny",
        }
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
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

    def _owner_record(self) -> Path:
        return self.home / "immortility-gateway-owner.json"

    def _write_owner_record(self) -> None:
        from .process_owner import process_identity

        if self.process is None:
            return
        identity = process_identity(self.process.pid)
        record = {
            "pid": self.process.pid,
            "created": identity[0] if identity else None,
            "image": identity[1] if identity else "",
            "port": 8642,
            "broker_pid": os.getpid(),
        }
        try:
            self._owner_record().write_text(json.dumps(record), encoding="utf-8")
        except OSError:
            pass

    def _clear_owner_record(self) -> None:
        try:
            self._owner_record().unlink()
        except OSError:
            pass

    async def _reclaim_orphan(self) -> bool:
        """Stop a gateway an earlier broker of ours started and could not clean up.

        Only the exact recorded process (PID + start time + image inside this Hermes home) is
        stopped. Any other listener on 8642 is left running.
        """
        from .process_owner import terminate_recorded_tree

        try:
            record = json.loads(self._owner_record().read_text(encoding="utf-8"))
            pid, created = int(record["pid"]), int(record["created"])
            image = str(record["image"])
            # The recorded image must be the Hermes interpreter this supervisor launches.
            expected = os.path.normcase(str(Path(self._python()).parent))
        except (OSError, ValueError, KeyError, TypeError, BrokerError):
            return False
        if not image or not os.path.normcase(image).startswith(expected):
            return False
        if not terminate_recorded_tree(pid, created, image):
            self._clear_owner_record()
            return False
        self._clear_owner_record()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not await loopback_port_open(8642):
                self.reclaimed_orphan = True
                self._step("reclaimed orphan gateway pid " + str(pid))
                return True
            await asyncio.sleep(0.1)
        return False

    async def start(self) -> None:
        if self.runtime_ready:
            return
        if await loopback_port_open(8642) and not await self._reclaim_orphan():
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
        self.python = python
        self._step("python")
        self._write_config()
        self._step("config")
        log_path = self.home / "logs" / "gateway-stderr.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = open(log_path, "ab", buffering=0)
        from .process_owner import spawn_owned

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
            self._write_owner_record()
            self._step("spawned")
        except Exception:
            self._log.close()
            self._log = None
            raise
        deadline = time.monotonic() + self.ready_timeout
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

    async def recover_if_crashed(self) -> None:
        """Restart a gateway process that exited on its own. Bounded, never silent."""
        process = self.process
        if process is None or process.returncode is None:
            return
        if self.crash_restarts >= self.max_crash_restarts:
            raise BrokerError(
                "hermes_unavailable", "Hermes gateway keeps exiting. Restart Immortility.", 503
            )
        self.crash_restarts += 1
        self._step("gateway exited with " + str(process.returncode) + "; restarting")
        await self.stop()
        await self.start()

    async def _graceful_stop(self, process: Any) -> bool:
        """Ask Hermes to drain and exit through its own planned-stop marker.

        Windows cannot deliver SIGTERM to a windowless child, so `hermes gateway stop` writes a
        planned-stop marker that the gateway polls. We use the same Hermes function.
        """
        if self.python is None or process is None or process.returncode is not None:
            return process is not None and process.returncode is not None
        script = (
            "from gateway.status import get_running_pid, write_planned_stop_marker\n"
            "pid = get_running_pid()\n"
            "if pid:\n"
            "    write_planned_stop_marker(pid)\n"
            "print(pid or 0)\n"
        )
        try:
            marker = await asyncio.create_subprocess_exec(
                str(self.python),
                "-c",
                script,
                cwd=str(self.home),
                env=self._environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            output, _ = await asyncio.wait_for(marker.communicate(), 20)
        except (OSError, asyncio.TimeoutError):
            return False
        if marker.returncode != 0 or not output.strip().isdigit() or int(output.strip()) == 0:
            return False
        try:
            await asyncio.wait_for(process.wait(), self.graceful_timeout)
        except asyncio.TimeoutError:
            return False
        return True

    async def stop(self) -> None:
        self.state = "stopping"
        self.runtime_ready = False
        started = time.perf_counter()
        gateway, self.gateway = self.gateway, None
        if gateway is not None:
            await gateway.shutdown()
        process, owner = self.process, self.owner
        self.process = None
        self.owner = None
        graceful = False
        if process is not None:
            from .process_owner import descendants, reap

            graceful = await self._graceful_stop(process)
            remaining = descendants(process.pid) if process.returncode is None else []
            await reap(process, owner)
            self._clear_owner_record()
            self.last_stop = {
                "graceful": graceful,
                "forced": not graceful,
                "pid": process.pid,
                "descendants_at_reap": len(remaining),
                "stop_ms": round((time.perf_counter() - started) * 1000, 1),
            }
            self._step("stopped graceful=" + str(graceful).lower())
        if self._log is not None:
            self._log.close()
            self._log = None
        self.state = "stopped"
