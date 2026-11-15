"""Fixed local UIA worker. Native consent is checked by Engine, never by model text.

Results are transient personal data: no cloud, recall, event-body or task-result
text retention. A Windows job bounds lifetime/commit, not filesystem/network access.
"""

import asyncio
import hashlib
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from .capabilities import StrictModel
from .config import ROOT
from .contracts import BrokerError
from .process_owner import reap, spawn_owned


class ObservationBegin(StrictModel):
    session_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    request_id: str = Field(pattern=r"^[a-f0-9-]{36}$")


class NativeWindowApproval(StrictModel):
    lease_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    hwnd: int = Field(gt=0, lt=2**63)
    pid: int = Field(gt=0, lt=2**32)
    created: int = Field(gt=0, lt=2**63)
    title: str = Field(min_length=1, max_length=4095)
    executable: str = Field(default="unavailable", min_length=1, max_length=260)
    indicator_hwnd: int = Field(gt=0, lt=2**63)
    indicator_pid: int = Field(gt=0, lt=2**32)
    indicator_created: int = Field(gt=0, lt=2**63)


@dataclass
class ObservationLease:
    task_id: str
    session_id: str
    nonce: str
    expires: float
    response: asyncio.Future[dict[str, Any] | None]
    consumed: bool = False
    cleanup: asyncio.TimerHandle | None = None


@dataclass
class PickerSession:
    selection: NativeWindowApproval
    stopped: asyncio.Task[bytes]


@asynccontextmanager
async def select_window(lease: ObservationLease) -> AsyncIterator[PickerSession]:
    """Only a pinned owned native UI process can return the selected target.

    No endpoint accepts this approval object. Closing its indicator/pipe revokes
    permission; the caller must race stopped against inspection and reap both.
    """
    await asyncio.to_thread(reviewed_observer)
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    with tempfile.TemporaryDirectory(prefix="window-picker-", dir=ROOT / ".cache") as folder:
        env.update(USERPROFILE=folder, APPDATA=folder, LOCALAPPDATA=folder)
        process, owner = await spawn_owned(
            str(ROOT / ".venv/Scripts/python.exe"),
            "-I",
            str(ROOT / "integrations/windows-observer/native_picker.py"),
            env=env,
            cwd=folder,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=8192,
            job_memory_limit=64 * 1024**2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stopped = None
        try:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write((json.dumps({"lease_id": lease.nonce}) + "\n").encode())
            await process.stdin.drain()
            process.stdin.close()
            async with asyncio.timeout_at(lease.expires):
                line = await process.stdout.readline()
                if len(line) > 8000:
                    raise ValueError
                body = json.loads(line)
                if body == {"declined": True}:
                    raise BrokerError(
                        "consent_declined", "Window inspection was not authorized.", 403
                    )
                selection = NativeWindowApproval.model_validate(body)
                if selection.lease_id != lease.nonce or not owner.contains(selection.indicator_pid):
                    raise ValueError
                stopped = asyncio.create_task(process.stdout.readline())
                yield PickerSession(selection, stopped)
        except (OSError, ValueError):
            raise BrokerError(
                "native_consent_failed", "Native window consent could not be verified.", 503
            ) from None
        finally:
            if stopped is not None:
                stopped.cancel()
                try:
                    await stopped
                except asyncio.CancelledError:
                    pass
            await reap(process, owner)


class WindowInput(StrictModel):
    operation: Literal["inspect"] = "inspect"
    task_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    session_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    lease_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    hwnd: int = Field(gt=0, lt=2**63)
    pid: int = Field(gt=0, lt=2**32)
    created: int = Field(gt=0, lt=2**63)
    title_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expires_at: float = Field(gt=0, allow_inf_nan=False)
    indicator_hwnd: int = Field(gt=0, lt=2**63)
    indicator_pid: int = Field(gt=0, lt=2**32)
    indicator_created: int = Field(gt=0, lt=2**63)
    consent: Literal[True] = True
    no_cloud: Literal[True] = True


class WindowNode(StrictModel):
    id: int = Field(ge=0, lt=64)
    depth: int = Field(ge=0, le=4)
    protected: bool
    text: str = Field(max_length=2000)
    control_type: str | None = Field(default=None, max_length=40)
    rect: list[int] | None = Field(default=None, min_length=4, max_length=4)

    @model_validator(mode="after")
    def protected_value(self) -> "WindowNode":
        if self.protected and self.text not in {"[protected]", "[unavailable]"}:
            raise ValueError("Protected fields cannot contain values")
        return self


class WindowSnapshot(StrictModel):
    schema_version: Literal["1.0"]
    kind: Literal["untrusted_ui_data"]
    task_id: str
    lease_id: str
    hwnd: int = Field(gt=0)
    pid: int = Field(gt=0)
    created: int = Field(gt=0)
    observed_at: float = Field(gt=0, allow_inf_nan=False)
    valid_until: float = Field(gt=0, allow_inf_nan=False)
    window_rect: list[int] = Field(min_length=4, max_length=4)
    dpi: int = Field(ge=48, le=960)
    foreground: bool
    nodes: list[WindowNode] = Field(max_length=64)
    truncated: bool
    cloud_allowed: Literal[False]
    screenshots: Literal[0]
    input_actions: Literal[0]

    @model_validator(mode="after")
    def bounded_tree(self) -> "WindowSnapshot":
        if [node.id for node in self.nodes] != list(range(len(self.nodes))):
            raise ValueError("Invalid node sequence")
        if sum(len(node.text) for node in self.nodes) > 9000:
            raise ValueError("Text envelope exceeded")
        if not self.observed_at <= self.valid_until <= self.observed_at + 2.1:
            raise ValueError("Invalid freshness window")
        return self


def reviewed_observer() -> Path:
    """Fixed executable/scripts only; verify source/dependencies on every dispatch."""
    try:
        if os.name != "nt":
            raise ValueError
        manifest = json.loads((ROOT / "config/observer-runtime.json").read_text())
        for name, expected in manifest["files"].items():
            path = ROOT / name
            if path.resolve().is_relative_to(ROOT) is False:
                raise ValueError
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError
        python = ROOT / ".venv-observer/Scripts/python.exe"
        if not python.is_file() or len(manifest["files"]) < 4:
            raise ValueError
        return python
    except (OSError, ValueError, KeyError, TypeError):
        raise BrokerError(
            "observer_unavailable",
            "Reviewed local observation runtime changed or is unavailable.",
            503,
        ) from None


async def inspect_window(arguments: dict[str, Any]) -> dict[str, Any]:
    scope = WindowInput.model_validate(arguments)
    if not time.time() < scope.expires_at <= time.time() + 30:
        raise BrokerError("grant_expired", "Window observation permission expired.", 403)
    python = await asyncio.to_thread(reviewed_observer)
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    with tempfile.TemporaryDirectory(prefix="observation-", dir=ROOT / ".cache") as folder:
        env.update(USERPROFILE=folder, APPDATA=folder, LOCALAPPDATA=folder)
        process, owner = await spawn_owned(
            str(python),
            "-I",
            str(ROOT / "integrations/windows-observer/inspect_window.py"),
            env=env,
            cwd=folder,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=65536,
            job_memory_limit=256 * 1024**2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            assert process.stdin is not None and process.stdout is not None
            async with asyncio.timeout(10):
                process.stdin.write((scope.model_dump_json() + "\n").encode())
                await process.stdin.drain()
                process.stdin.close()
                line = await process.stdout.readline()
                if len(line) > 64000:
                    raise BrokerError("output_limit", "Observation output exceeded its limit.", 413)
                body = json.loads(line)
                if isinstance(body, dict) and "error" in body:
                    raise BrokerError(
                        "observation_denied",
                        "Window changed, is protected or permission ended.",
                        403,
                    )
                result = WindowSnapshot.model_validate(body)
                await process.wait()
                if process.returncode != 0 or any(
                    getattr(result, key) != getattr(scope, key)
                    for key in ("task_id", "lease_id", "hwnd", "pid", "created")
                ):
                    raise ValueError
                if time.time() >= min(scope.expires_at, result.valid_until):
                    raise BrokerError(
                        "stale_observation", "Window context expired before delivery.", 409
                    )
                return dict(result.model_dump(mode="json"))
        except (OSError, ValueError, TimeoutError):
            raise BrokerError(
                "observation_failed", "Local observation failed; no screen data retained.", 503
            ) from None
        finally:
            await reap(process, owner)
