"""Broker-mediated pointer moves (M2, D18). Move only: no clicks, no typing.

Safety model:
- Only a whole, explicit user command parses into a request (``parse_pointer_command``).
  Model output, screen text, memories and attachments never reach this module.
- Every move needs a fresh single-use approval and the ``pointer-control.json`` flag.
- Targets are clamped to the virtual screen (all monitors).
- Emergency stop: Esc, the broker stop button, the user moving the mouse during a
  smooth move, or a cursor parked in a screen corner (checked before and during).
- Win32 SetCursorPos/GetCursorPos via ctypes (stdlib; no new dependency), non-admin.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field

MAX_COORD = 100_000
CORNER_PX = 3
DRIFT_PX = 6
STEP_S = 0.01


class MoveCursorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    x: int = Field(ge=-MAX_COORD, le=MAX_COORD)
    y: int = Field(ge=-MAX_COORD, le=MAX_COORD)
    duration_ms: int = Field(default=0, ge=0, le=1500)
    center: bool = False


_NUM = r"(-?\d{1,6})"
_COMMAND = re.compile(
    r"^\s*(?:please\s+)?(?:move|put|place)\s+(?:the\s+|my\s+)?(?:mouse(?:\s+cursor)?|cursor|pointer)"
    r"(?:\s+(?:to|at))?\s*(?:"
    rf"\(?\s*{_NUM}\s*(?:,\s*|\s+)\s*{_NUM}\s*\)?"
    r"|(?:the\s+)?(?P<center>cent(?:er|re))(?:\s+of\s+(?:the\s+)?(?:main\s+)?screen)?"
    r")"
    r"(?:\s+(?P<smooth>smoothly|slowly)|\s+over\s+(?P<ms>\d{1,4})\s*ms)?\s*[.!]?\s*$",
    re.IGNORECASE,
)


def parse_pointer_command(content: str) -> MoveCursorRequest | None:
    """Return a request only when the WHOLE message is an explicit pointer command."""
    if not isinstance(content, str) or len(content) > 120 or "\n" in content:
        return None
    match = _COMMAND.match(content)
    if match is None:
        return None
    duration = 0
    if match.group("ms"):
        duration = min(1500, int(match.group("ms")))
    elif match.group("smooth"):
        duration = 400
    if match.group("center"):
        return MoveCursorRequest(x=0, y=0, duration_ms=duration, center=True)
    x, y = int(match.group(1)), int(match.group(2))
    if abs(x) > MAX_COORD or abs(y) > MAX_COORD:
        return None
    return MoveCursorRequest(x=x, y=y, duration_ms=duration)


@dataclass(frozen=True)
class Screen:
    left: int
    top: int
    width: int
    height: int
    primary_width: int
    primary_height: int

    @property
    def right(self) -> int:
        return self.left + self.width - 1

    @property
    def bottom(self) -> int:
        return self.top + self.height - 1

    def clamp(self, x: int, y: int) -> tuple[int, int]:
        return min(max(x, self.left), self.right), min(max(y, self.top), self.bottom)

    def in_corner(self, x: int, y: int) -> bool:
        near_x = x <= self.left + CORNER_PX or x >= self.right - CORNER_PX
        near_y = y <= self.top + CORNER_PX or y >= self.bottom - CORNER_PX
        return near_x and near_y


class Backend:
    """Win32 cursor backend. Tests inject a fake with the same four methods."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("pointer control is Windows-only")
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.point = wintypes.POINT
        self.user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        self.user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]

    def screen(self) -> Screen:
        m = self.user32.GetSystemMetrics
        return Screen(m(76), m(77), m(78), m(79), m(0), m(1))

    def position(self) -> tuple[int, int]:
        p = self.point()
        if not self.user32.GetCursorPos(self.ctypes.byref(p)):
            raise OSError("GetCursorPos failed")
        return p.x, p.y

    def set_position(self, x: int, y: int) -> None:
        if not self.user32.SetCursorPos(int(x), int(y)):
            raise OSError("SetCursorPos failed")

    def escape_pressed(self) -> bool:
        return bool(self.user32.GetAsyncKeyState(0x1B) & 0x8000)

    def dpi_aware(self) -> Callable[[], None]:
        # Per-monitor-aware v2 for this thread only, so coordinates are physical pixels.
        old = self.user32.SetThreadDpiAwarenessContext(self.ctypes.c_void_p(-4))
        return lambda: self.user32.SetThreadDpiAwarenessContext(self.ctypes.c_void_p(old))


def move_cursor(
    request: MoveCursorRequest,
    stopped: Callable[[], bool],
    backend: Backend | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    backend = backend or Backend()
    restore = backend.dpi_aware()
    started = time.perf_counter()
    try:
        screen = backend.screen()
        if request.center:
            wanted = (screen.primary_width // 2, screen.primary_height // 2)
        else:
            wanted = (request.x, request.y)
        target = screen.clamp(*wanted)
        start = backend.position()
        result: dict[str, object] = {
            "requested": list(wanted),
            "target": list(target),
            "clamped": target != wanted,
            "start": list(start),
            "virtual_screen": [screen.left, screen.top, screen.width, screen.height],
            "duration_ms": request.duration_ms,
            "aborted": None,
        }
        if screen.in_corner(*start):
            result["aborted"] = "corner_failsafe"
        elif backend.escape_pressed() or stopped():
            result["aborted"] = "stopped"
        elif request.duration_ms == 0:
            backend.set_position(*target)
        else:
            steps = max(1, round(request.duration_ms / 1000 / STEP_S))
            last = start
            for index in range(1, steps + 1):
                now = backend.position()
                if abs(now[0] - last[0]) > DRIFT_PX or abs(now[1] - last[1]) > DRIFT_PX:
                    result["aborted"] = "user_moved"
                    break
                if screen.in_corner(*now) and now != start:
                    result["aborted"] = "corner_failsafe"
                    break
                if backend.escape_pressed():
                    result["aborted"] = "escape"
                    break
                if stopped():
                    result["aborted"] = "stopped"
                    break
                t = index / steps
                eased = t * t * (3 - 2 * t)
                last = (
                    round(start[0] + (target[0] - start[0]) * eased),
                    round(start[1] + (target[1] - start[1]) * eased),
                )
                backend.set_position(*last)
                sleep(STEP_S)
        result["final"] = list(backend.position())
        result["reached"] = result["aborted"] is None and tuple(result["final"]) == target
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        return result
    finally:
        restore()


def describe(result: dict[str, object]) -> str:
    if result.get("aborted"):
        reasons = {
            "corner_failsafe": "the cursor is parked in a screen corner (emergency stop)",
            "user_moved": "you moved the mouse",
            "escape": "Esc was pressed",
            "stopped": "it was stopped",
        }
        return f"Pointer move cancelled: {reasons.get(str(result['aborted']), 'stopped')}."
    x, y = result["final"]  # type: ignore[misc]
    note = " (clamped to the screen edge)" if result.get("clamped") else ""
    if not result.get("reached"):
        return f"Pointer moved, but Windows placed it at {x}, {y}."
    return f"Pointer moved to {x}, {y}{note}. No click was made."
