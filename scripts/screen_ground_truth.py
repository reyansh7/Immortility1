"""Benchmark helper (not product code): ground-truth screen points via UI Automation.

Run with the observer venv. stdin JSON: {"title": substring, "find": [words...],
"password": bool, "canvas": bool, "select": word|null}. Prints, per word, the screen centre of
its first match (TextPattern.DocumentRange.FindText -> GetBoundingRectangles), plus the centre
of a password field / canvas when asked. Optionally selects one word (TextPatternRange.Select)
in the benchmark's own window. Never reads or prints any field's contents.
"""

import ctypes
import json
import sys
import time

from pywinauto.uia_defines import IUIA

from ctypes import wintypes as w

user = ctypes.WinDLL("user32")
user.WindowFromPoint.argtypes = [w.POINT]
user.WindowFromPoint.restype = w.HWND
user.GetAncestor.argtypes = [w.HWND, ctypes.c_uint]
user.GetAncestor.restype = w.HWND
user.SetWindowPos.argtypes = [
    w.HWND,
    w.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
if hasattr(user, "SetProcessDpiAwarenessContext"):
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))


def centre(rects):
    values = list(rects or [])
    if len(values) < 4:
        return None
    left, top, width, height = values[:4]
    return {
        "x": int(left + width / 2),
        "y": int(top + height / 2),
        "h": int(height),
        "left": int(left),
        "top": int(top),
        "bottom": int(top + height),
    }


def main() -> int:
    request = json.loads(sys.stdin.read())
    uia = IUIA()
    iuia, mod = uia.iuia, uia.UIA_dll
    root = iuia.GetRootElement()
    condition = iuia.CreateTrueCondition()
    window = None
    deadline = time.time() + 15
    while window is None and time.time() < deadline:
        children = root.FindAll(mod.TreeScope_Children, condition)
        for i in range(children.Length):
            element = children.GetElement(i)
            if request["title"].casefold() in (element.CurrentName or "").casefold():
                window = element
                break
        if window is None:
            time.sleep(0.3)
    if window is None:
        print(json.dumps({"error": "window_not_found"}))
        return 0
    hwnd = int(window.CurrentNativeWindowHandle or 0)
    if request.get("topmost") and hwnd:
        # Show the benchmark's own window above others WITHOUT taking focus (SWP_NOACTIVATE).
        user.SetWindowPos(hwnd, w.HWND(-1), 0, 0, 0, 0, 0x1 | 0x2 | 0x10 | 0x40)
        time.sleep(0.4)
    out = {"window": {"name": window.CurrentName[:120], "hwnd": hwnd}, "points": {}}
    docs = []
    deadline = time.time() + 10
    while not docs and time.time() < deadline:
        found = window.FindAll(mod.TreeScope_Descendants, condition)
        for i in range(found.Length):
            element = found.GetElement(i)
            try:
                pattern = element.GetCurrentPattern(mod.UIA_TextPatternId)
            except Exception:
                pattern = None
            if pattern:
                docs.append(pattern.QueryInterface(mod.IUIAutomationTextPattern))
            if request.get("password") and element.CurrentIsPassword:
                rect = element.CurrentBoundingRectangle
                out["points"]["__password__"] = {
                    "x": int((rect.left + rect.right) / 2),
                    "y": int((rect.top + rect.bottom) / 2),
                }
            if request.get("canvas") and element.CurrentControlType == mod.UIA_ImageControlTypeId:
                rect = element.CurrentBoundingRectangle
                out["points"].setdefault(
                    "__canvas__",
                    {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                    },
                )
        if not docs:
            time.sleep(0.5)
    for word in request.get("find", []):
        for pattern in docs:
            try:
                hit = pattern.DocumentRange.FindText(word, 0, 0)
            except Exception:
                hit = None
            if hit:
                point = centre(hit.GetBoundingRectangles())
                if point:
                    out["points"][word] = point
                    break
    if request.get("select"):
        for pattern in docs:
            hit = pattern.DocumentRange.FindText(request["select"], 0, 0)
            if hit:
                hit.Select()
                out["selected"] = True
                break
    for index, point in enumerate(request.get("check") or []):
        out["points"][f"__check_{index}__"] = {"x": int(point["x"]), "y": int(point["y"])}
    for point in out["points"].values():
        if "x" in point:
            at = user.WindowFromPoint(w.POINT(point["x"], point["y"]))
            point["occluded"] = int(user.GetAncestor(at, 2) or 0) != hwnd if at else True
    dpi = user.GetDpiForSystem() if hasattr(user, "GetDpiForSystem") else 96
    out["dpi"] = int(dpi)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
