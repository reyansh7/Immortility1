"""Read the text under the cursor, the selection and the window under it (M2/P4).

Read-only UI Automation. No input, click, capture, launch or shell operation; OCR is a
separate fixed script the broker runs only when this worker found no text and did not deny.
Order of preference: TextPattern.RangeFromPoint -> ExpandToEnclosingUnit(word/line), then
the element's own Name. Password controls and sensitive applications are refused before
any text is read. The caller is the broker permission authority, never model text.

stdin:  {"x": int, "y": int, "unit": "word"|"line", "selection": bool}
stdout: one JSON object (see ``result``); exit 0 even for denials.
"""

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes as w

SENSITIVE_EXECUTABLES = {
    "consent.exe",
    "credentialuibroker.exe",
    "logonui.exe",
    "lockapp.exe",
    "msmpeng.exe",
    "securityhealthsystray.exe",
    "sechealthui.exe",
    "keepass.exe",
    "keepassxc.exe",
    "1password.exe",
    "bitwarden.exe",
    "dashlane.exe",
    "lastpass.exe",
}
SENSITIVE_TITLE_WORDS = ("password", "passcode", "sign in", "credential", "pin code", "otp")
MAX_WORD, MAX_LINE, MAX_SELECTION, MAX_NAME = 120, 600, 4000, 300

user = ctypes.WinDLL("user32", use_last_error=True)
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
user.GetForegroundWindow.restype = w.HWND
user.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
user.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user.GetWindowLongW.argtypes = [w.HWND, ctypes.c_int]
user.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
user.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
user.WindowFromPoint.argtypes = [w.POINT]
user.WindowFromPoint.restype = w.HWND
user.GetAncestor.argtypes = [w.HWND, ctypes.c_uint]
user.GetAncestor.restype = w.HWND
kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
kernel.OpenProcess.restype = w.HANDLE
kernel.CloseHandle.argtypes = [w.HANDLE]
kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]


class Denied(Exception):
    pass


def executable(pid: int) -> str:
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return "unavailable"
    try:
        size = w.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return "unavailable"
        return os.path.basename(buffer.value).lower()
    finally:
        kernel.CloseHandle(handle)


def describe(hwnd) -> dict:
    if not hwnd:
        return {"hwnd": 0, "title": "", "process": "unavailable", "pid": 0}
    title = ctypes.create_unicode_buffer(512)
    user.GetWindowTextW(hwnd, title, len(title))
    pid = w.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {
        "hwnd": int(hwnd),
        "title": title.value[:200],
        "process": executable(pid.value),
        "pid": int(pid.value),
    }


def foreground() -> dict:
    return describe(user.GetForegroundWindow())


def window_at(x: int, y: int) -> dict:
    hwnd = user.WindowFromPoint(w.POINT(x, y))
    return describe(user.GetAncestor(hwnd, 2) if hwnd else None)  # GA_ROOT


def sensitive(window: dict) -> bool:
    return window["process"] in SENSITIVE_EXECUTABLES or any(
        word in window["title"].casefold() for word in SENSITIVE_TITLE_WORDS
    )


def root_handle(element, iuia, walker) -> int:
    """Top-level HWND that contains a UIA element (0 when unknown)."""
    root, current, handle = iuia.GetRootElement(), element, 0
    for _ in range(40):
        try:
            handle = int(current.CurrentNativeWindowHandle or 0) or handle
            parent = walker.GetParentElement(current)
            if parent is None or iuia.CompareElements(parent, root):
                break
        except Exception:
            break
        current = parent
    return int(user.GetAncestor(handle, 2) or 0) if handle else 0


def guard(element, uia_dll) -> None:
    """Refuse before reading: password controls, sensitive processes, secure windows."""
    try:
        if element.CurrentIsPassword:
            raise Denied("password_field")
    except Denied:
        raise
    except Exception:
        raise Denied("element_unreadable") from None
    hwnd = element.CurrentNativeWindowHandle
    if hwnd and user.GetWindowLongW(hwnd, -16) & 0x20:  # ES_PASSWORD
        raise Denied("password_field")
    if executable(int(element.CurrentProcessId)) in SENSITIVE_EXECUTABLES:
        raise Denied("sensitive_application")


def text_pattern(element, uia, mod, walker, depth: int = 6):
    current = element
    for _ in range(depth):
        if current is None:
            return None, None
        try:
            pattern = current.GetCurrentPattern(mod.UIA_TextPatternId)
            if pattern:
                return pattern.QueryInterface(mod.IUIAutomationTextPattern), current
        except Exception:
            pass
        try:
            current = walker.GetParentElement(current)
        except Exception:
            return None, None
    return None, None


def contains(rects, x: float, y: float, slack: float = 3.0) -> bool:
    values = list(rects or [])
    for i in range(0, len(values) - 3, 4):
        left, top, width, height = values[i : i + 4]
        if left - slack <= x <= left + width + slack and top - slack <= y <= top + height + slack:
            return True
    return False


def clean(text: str, limit: int) -> str:
    return " ".join((text or "").replace("\r", " ").split())[:limit]


def read(request: dict) -> dict:
    started = time.perf_counter()
    if hasattr(user, "SetProcessDpiAwarenessContext"):
        user.SetProcessDpiAwarenessContext.argtypes = [w.HANDLE]
        user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2
    from pywinauto.uia_defines import IUIA

    uia = IUIA()
    iuia, mod = uia.iuia, uia.UIA_dll
    walker = iuia.ControlViewWalker
    x, y = request.get("x"), request.get("y")
    if x is None or y is None:
        cursor = w.POINT()
        user.GetCursorPos(ctypes.byref(cursor))
        x, y = cursor.x, cursor.y
    unit = mod.TextUnit_Line if request.get("unit") == "line" else mod.TextUnit_Word
    window, front = window_at(int(x), int(y)), foreground()
    result = {
        "x": int(x),
        "y": int(y),
        "window": {k: window[k] for k in ("title", "process")},
        "foreground": {k: front[k] for k in ("title", "process")},
        "source": "none",
        "target": "",
        "line": "",
        "element": {},
        "selection": "",
        "exact": False,
        "denied": None,
    }
    if sensitive(front):
        result["foreground"]["title"] = "[withheld]"
    if sensitive(window):
        result["denied"] = "sensitive_window"
        result["window"]["title"] = "[withheld]"
        return result
    point = mod.tagPOINT()
    point.x, point.y = int(x), int(y)
    try:
        element = iuia.ElementFromPoint(point)
        guard(element, mod)
        result["element"] = {
            "control_type": int(element.CurrentControlType),
            "class": clean(element.CurrentClassName, 80),
            "process": executable(int(element.CurrentProcessId)),
        }
        pattern, owner = text_pattern(element, iuia, mod, walker)
        if pattern is not None:
            guard(owner, mod)
            at = pattern.RangeFromPoint(point)
            word = at.Clone()
            word.ExpandToEnclosingUnit(unit)
            text = clean(
                word.GetText(MAX_LINE if unit == mod.TextUnit_Line else MAX_WORD),
                MAX_LINE if unit == mod.TextUnit_Line else MAX_WORD,
            )
            exact = contains(word.GetBoundingRectangles(), x, y)
            line = at.Clone()
            line.ExpandToEnclosingUnit(mod.TextUnit_Line)
            if text and exact:
                result.update(
                    source="uia_text",
                    target=text,
                    exact=True,
                    line=clean(line.GetText(MAX_LINE), MAX_LINE),
                )
        if result["source"] == "none":
            name = clean(element.CurrentName, MAX_NAME)
            if name:
                result.update(source="uia_name", target=name, exact=False)
        if request.get("selection"):
            # Selection in the hovered document first; the focused element only when it is
            # inside the same top-level window (never another app's selection).
            candidates = [pattern] if pattern is not None else []
            focused = iuia.GetFocusedElement()
            if focused is not None and root_handle(focused, iuia, walker) == window["hwnd"]:
                guard(focused, mod)
                focused_pattern, focused_owner = text_pattern(focused, iuia, mod, walker)
                if focused_pattern is not None:
                    guard(focused_owner, mod)
                    candidates.append(focused_pattern)
            for selection_pattern in candidates:
                ranges = selection_pattern.GetSelection()
                parts = [
                    ranges.GetElement(i).GetText(MAX_SELECTION)
                    for i in range(min(ranges.Length, 8))
                ]
                text = clean(" ".join(parts), MAX_SELECTION)
                if text:
                    result["selection"] = text
                    break
    except Denied as denied:
        result.update(denied=str(denied), source="none", target="", line="", selection="")
    except Exception as error:  # UIA providers throw COMError for many benign reasons
        result["error"] = type(error).__name__
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


def main() -> int:
    try:
        request = json.loads(sys.stdin.read(4096) or "{}")
        if not isinstance(request, dict):
            raise ValueError
        for key in ("x", "y"):
            if request.get(key) is not None and not isinstance(request[key], int):
                raise ValueError
    except ValueError:
        print(json.dumps({"denied": "invalid_request"}))
        return 0
    print(json.dumps(read(request)))  # ASCII-only: pipe code page safe
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
