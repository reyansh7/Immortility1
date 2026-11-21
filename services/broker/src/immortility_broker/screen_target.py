"""Hover/selection target extraction (M2/P4). Local-first, read-only, never cloud.

The broker runs two fixed, hash-pinned workers (``config/observer-runtime.json``):
``integrations/windows-observer/screen_target.py`` (UI Automation: ElementFromPoint ->
TextPattern.RangeFromPoint -> ExpandToEnclosingUnit; selection; foreground window) and,
only if UIA found no text and refused nothing, ``ocr_crop.ps1`` (Windows.Media.Ocr over a
small in-memory crop around the point). Results are transient: never stored in the
database, events or task results by this module, and never sent to a provider here.

Only the desktop session token can call this (``/v1/screen/target``); it is not a model
capability. While a read is in progress ``ScreenAccess`` is active, which the runtime status
reports so the UI shows the privacy indicator.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import Field

from .capabilities import StrictModel
from .config import ROOT
from .contracts import BrokerError
from .process_owner import reap, spawn_owned

WORKER = ROOT / "integrations/windows-observer/screen_target.py"
OCR_SCRIPT = ROOT / "integrations/windows-observer/ocr_crop.ps1"


class TargetRequest(StrictModel):
    x: int | None = Field(default=None, ge=-32768, le=32767)
    y: int | None = Field(default=None, ge=-32768, le=32767)
    unit: Literal["word", "line"] = "word"
    selection: bool = True
    ocr_fallback: bool = True


@dataclass
class ScreenAccess:
    """Visible state for the privacy indicator. Counts, never content."""

    active: bool = False
    kind: str = ""
    since: float = 0.0
    reads: int = 0
    last_ms: float | None = None
    last_source: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "kind": self.kind,
            "reads": self.reads,
            "last_ms": self.last_ms,
            "last_source": self.last_source,
            "cloud": False,
        }


def _environment(folder: str) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    env.update(USERPROFILE=folder, APPDATA=folder, LOCALAPPDATA=folder)
    return env


async def _run(command: list[str], stdin: bytes, timeout: float, folder: str) -> dict[str, Any]:
    process, owner = await spawn_owned(
        *command,
        env=_environment(folder),
        cwd=folder,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=65536,
        job_memory_limit=384 * 1024**2,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        assert process.stdin is not None and process.stdout is not None
        async with asyncio.timeout(timeout):
            process.stdin.write(stdin)
            await process.stdin.drain()
            process.stdin.close()
            line = await process.stdout.readline()
            await process.wait()
        if len(line) > 64000:
            raise ValueError
        body = json.loads(line.decode("utf-8-sig"))
        if not isinstance(body, dict):
            raise ValueError
        return body
    except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
        raise BrokerError(
            "screen_target_failed", "Local screen reading failed; nothing was retained.", 503
        ) from None
    finally:
        await reap(process, owner)


def pick_ocr_word(ocr: dict[str, Any], x: int, y: int, unit: str) -> dict[str, Any] | None:
    """The OCR word under (x, y), or the nearest within 12 px, and its line."""
    best: tuple[float, str, str] | None = None
    for line in ocr.get("lines") or []:
        for word in line.get("words") or []:
            left, top, width, height = word["x"], word["y"], word["w"], word["h"]
            dx = max(left - x, 0, x - (left + width))
            dy = max(top - y, 0, y - (top + height))
            distance = (dx * dx + dy * dy) ** 0.5
            if distance <= 12 and (best is None or distance < best[0]):
                best = (distance, str(word["t"]), str(line.get("text", "")))
    if best is None:
        return None
    distance, word_text, line_text = best
    return {
        "target": (line_text if unit == "line" else word_text)[:600],
        "line": line_text[:600],
        "exact": distance == 0,
    }


async def read_target(
    request: TargetRequest, access: ScreenAccess, notify: Any = None
) -> dict[str, Any]:
    if os.name != "nt":
        raise BrokerError("screen_target_unavailable", "Screen reading needs Windows.", 503)
    from .windows_observer import reviewed_observer

    python = await asyncio.to_thread(reviewed_observer)  # verifies the pinned scripts
    access.active, access.kind, access.since = True, "hover_target", time.time()
    if notify:
        notify()
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="screen-", dir=ROOT / ".cache") as folder:
            body = await _run(
                [str(python), "-I", str(WORKER)],
                (request.model_dump_json(exclude={"ocr_fallback"}) + "\n").encode(),
                8.0,
                folder,
            )
            result = {
                "source": body.get("source", "none"),
                "target": str(body.get("target", ""))[:600],
                "line": str(body.get("line", ""))[:600],
                "selection": str(body.get("selection", ""))[:4000],
                "exact": bool(body.get("exact")),
                "denied": body.get("denied"),
                "window": body.get("window") or {},
                "element": body.get("element") or {},
                "point": {"x": body.get("x"), "y": body.get("y")},
                "uia_ms": body.get("elapsed_ms"),
                "ocr_ms": None,
                "cloud": False,
            }
            if (
                request.ocr_fallback
                and not result["denied"]
                and result["source"] in {"none", "uia_name"}
                and isinstance(body.get("x"), int)
                and isinstance(body.get("y"), int)
            ):
                powershell = (
                    os.environ.get("SYSTEMROOT", r"C:\Windows")
                    + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
                )
                ocr = await _run(
                    [
                        powershell,
                        "-NoLogo",
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(OCR_SCRIPT),
                        "-X",
                        str(body["x"]),
                        "-Y",
                        str(body["y"]),
                    ],
                    b"",
                    12.0,
                    folder,
                )
                result["ocr_ms"] = ocr.get("elapsed_ms")
                picked = (
                    pick_ocr_word(ocr, body["x"], body["y"], request.unit)
                    if ocr.get("ok")
                    else None
                )
                if picked:
                    result.update(source="ocr", **picked)
                elif not ocr.get("ok"):
                    result["ocr_error"] = str(ocr.get("error", ""))[:120]
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        access.reads += 1
        access.last_ms, access.last_source = result["elapsed_ms"], str(result["source"])
        return result
    finally:
        access.active, access.kind = False, ""
        if notify:
            notify()
