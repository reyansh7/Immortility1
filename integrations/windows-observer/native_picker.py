"""Broker-owned native consent UI. No auto-approval, target argument or input tool.

The private stdin accepts only a fresh broker nonce. Only an explicit human
selection and Allow click emits a target; the same window becomes the indicator.
Closing/Stop/expiry emits revocation. Screen contents never travel through here.
"""

import ctypes
import json
import os
import runpy
import sys
import time
import uuid
from ctypes import wintypes as w
from pathlib import Path

api = runpy.run_path(str(Path(__file__).with_name("inspect_window.py")))
user, kernel, adv = api["native"]()
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
ENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)


class WindowClass(ctypes.Structure):
    _fields_ = [
        ("style", w.UINT),
        ("procedure", WNDPROC),
        ("class_extra", ctypes.c_int),
        ("window_extra", ctypes.c_int),
        ("instance", w.HINSTANCE),
        ("icon", w.HICON),
        ("cursor", w.HANDLE),
        ("background", w.HBRUSH),
        ("menu", w.LPCWSTR),
        ("name", w.LPCWSTR),
    ]


user.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
user.DefWindowProcW.restype = ctypes.c_ssize_t
user.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
user.RegisterClassW.restype = w.WORD
user.CreateWindowExW.argtypes = [
    w.DWORD,
    w.LPCWSTR,
    w.LPCWSTR,
    w.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    w.HWND,
    w.HMENU,
    w.HINSTANCE,
    ctypes.c_void_p,
]
user.CreateWindowExW.restype = w.HWND
user.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
user.SendMessageW.restype = ctypes.c_ssize_t
user.SetWindowTextW.argtypes = [w.HWND, w.LPCWSTR]
user.DestroyWindow.argtypes = [w.HWND]
user.EnableWindow.argtypes = [w.HWND, w.BOOL]
user.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
user.SetWindowPos.argtypes = [
    w.HWND,
    w.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    w.UINT,
]
user.SetTimer.argtypes = [w.HWND, ctypes.c_size_t, w.UINT, ctypes.c_void_p]
user.GetMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT]
user.IsDialogMessageW.argtypes = [w.HWND, ctypes.POINTER(w.MSG)]
user.TranslateMessage.argtypes = [ctypes.POINTER(w.MSG)]
user.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
user.EnumWindows.argtypes = [ENUMPROC, w.LPARAM]
kernel.GetModuleHandleW.argtypes = [w.LPCWSTR]
kernel.GetModuleHandleW.restype = w.HMODULE

DENIED_EXE = api["SENSITIVE_EXECUTABLES"]


def send(body):
    sys.stdout.buffer.write((json.dumps(body, ensure_ascii=True) + "\n").encode("ascii"))
    sys.stdout.buffer.flush()


def born(pid):
    process = kernel.OpenProcess(0x1000, False, pid)
    try:
        if not process:
            raise ValueError
        values = [w.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(process, *(ctypes.byref(value) for value in values)):
            raise ValueError
        return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime
    finally:
        if process:
            kernel.CloseHandle(process)


def target(hwnd):
    if not user.IsWindowVisible(hwnd) or user.IsIconic(hwnd):
        raise ValueError
    pid = w.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        raise ValueError
    name = ctypes.create_unicode_buffer(256)
    user.GetClassNameW(hwnd, name, len(name))
    if name.value == "#32770":
        raise ValueError
    title = api["title_of"](user, hwnd)
    if not title or any(
        word in title.casefold()
        for word in (
            "sign in",
            "sign-in",
            "log in",
            "password",
            "windows security",
            "user account control",
        )
    ):
        raise ValueError
    created = born(pid.value)
    api["identity"](user, kernel, adv, hwnd, pid.value, created)
    process = kernel.OpenProcess(0x1000, False, pid.value)
    try:
        filename = ctypes.create_unicode_buffer(4096)
        length = w.DWORD(len(filename))
        if not process or not kernel.QueryFullProcessImageNameW(
            process, 0, filename, ctypes.byref(length)
        ):
            raise ValueError
        executable = Path(filename.value).name
        if executable.casefold() in DENIED_EXE:
            raise ValueError
    finally:
        if process:
            kernel.CloseHandle(process)
    return {
        "hwnd": int(hwnd),
        "pid": pid.value,
        "created": created,
        "title": title,
        "executable": executable,
    }


def main():
    line = sys.stdin.buffer.readline(257)
    request = json.loads(line)
    if (
        len(line) > 256
        or set(request) != {"lease_id"}
        or request["lease_id"] != uuid.UUID(hex=request["lease_id"]).hex
    ):
        raise ValueError
    api["interactive"](user)
    if hasattr(user, "SetProcessDpiAwarenessContext"):
        user.SetProcessDpiAwarenessContext.argtypes = [w.HANDLE]
        user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    nonce = request["lease_id"]
    instance = kernel.GetModuleHandleW(None)
    state = {"rows": [], "approved": False, "ended": False, "deadline": time.monotonic() + 55}
    controls = {}

    def close(hwnd):
        if not state["ended"]:
            state["ended"] = True
            send({"stopped": True} if state["approved"] else {"declined": True})
        user.DestroyWindow(hwnd)

    def refresh():
        state["rows"].clear()
        user.SendMessageW(controls["list"], 0x0184, 0, 0)  # LB_RESETCONTENT

        @ENUMPROC
        def enumerate_window(hwnd, _):
            if len(state["rows"]) >= 64:
                return False
            try:
                item = target(hwnd)
                state["rows"].append(item)
                readable = "".join(c if c.isprintable() else " " for c in item["title"])
                display = ctypes.create_unicode_buffer(
                    f"{item['executable']} [PID {item['pid']}] — {readable[:180]}"
                )
                user.SendMessageW(controls["list"], 0x0180, 0, ctypes.addressof(display))
            except Exception:
                pass
            return True

        user.EnumWindows(enumerate_window, 0)
        user.EnableWindow(controls["allow"], False)

    @WNDPROC
    def procedure(hwnd, message, first, second):
        try:
            if message == 0x0113:  # WM_TIMER, no polling of screen contents
                api["interactive"](user)
                if time.monotonic() >= state["deadline"]:
                    close(hwnd)
                return 0
            if message == 0x0010:  # WM_CLOSE
                close(hwnd)
                return 0
            if message == 0x0002:
                user.PostQuitMessage(0)
                return 0
            if message == 0x0100 and first == 27:
                close(hwnd)
                return 0
            if message == 0x0111:
                identifier, notification = first & 0xFFFF, first >> 16
                if identifier == 2:
                    close(hwnd)
                elif identifier == 3 and not state["approved"]:
                    refresh()
                elif identifier == 10 and notification == 1 and not state["approved"]:
                    user.EnableWindow(controls["allow"], True)
                elif identifier == 1 and not state["approved"]:
                    index = user.SendMessageW(controls["list"], 0x0188, 0, 0)  # LB_GETCURSEL
                    if not 0 <= index < len(state["rows"]):
                        return 0
                    selected = state["rows"][index]
                    if target(selected["hwnd"]) != selected:
                        user.SetWindowTextW(
                            controls["status"], "Window changed. Refresh and select again."
                        )
                        user.EnableWindow(controls["allow"], False)
                        return 0
                    state["approved"] = True
                    state["deadline"] = time.monotonic() + 12
                    user.SetWindowTextW(hwnd, "Immortility observing local only " + nonce)
                    user.SetWindowTextW(
                        controls["heading"], "LOCAL READ-ONLY INSPECTION — Stop revokes permission"
                    )
                    user.SetWindowTextW(
                        controls["status"],
                        "One accessibility snapshot. No screenshots, typing, clicks or cloud upload.",
                    )
                    for name in ("list", "allow", "refresh"):
                        user.ShowWindow(controls[name], 0)
                    user.SetWindowTextW(controls["cancel"], "Stop inspection")
                    user.SetWindowPos(hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x0013)
                    send(
                        selected
                        | {
                            "lease_id": nonce,
                            "indicator_hwnd": int(hwnd),
                            "indicator_pid": os.getpid(),
                            "indicator_created": born(os.getpid()),
                        }
                    )
                return 0
        except Exception:
            close(hwnd)
            return 0
        return user.DefWindowProcW(hwnd, message, first, second)

    name = "ImmortilityPermissionPicker_" + nonce
    definition = WindowClass(
        procedure=procedure, instance=instance, background=ctypes.c_void_p(6), name=name
    )
    if not user.RegisterClassW(ctypes.byref(definition)):
        raise ValueError
    hwnd = user.CreateWindowExW(
        0x00010000,
        name,
        "Immortility — Choose a window (local only)",
        0x00C80000,
        220,
        150,
        820,
        460,
        None,
        None,
        instance,
        None,
    )
    if not hwnd:
        raise ValueError

    def control(key, kind, text, x, y, width, height, identifier=0, style=0):
        result = user.CreateWindowExW(
            0,
            kind,
            text,
            0x40000000 | 0x10000000 | style,
            x,
            y,
            width,
            height,
            hwnd,
            ctypes.c_void_p(identifier),
            instance,
            None,
        )
        if not result:
            raise ValueError
        controls[key] = result

    control("heading", "STATIC", "Authorize ONE local accessibility snapshot", 18, 14, 780, 28)
    control(
        "status",
        "STATIC",
        "Select a window yourself. Text is shown locally, not saved or sent to a model. Password fields are excluded.",
        18,
        46,
        775,
        46,
    )
    control(
        "list", "LISTBOX", "", 18, 98, 775, 225, 10, 0x00800000 | 0x00200000 | 0x0001 | 0x00010000
    )
    control("allow", "BUTTON", "Allow one local read", 18, 344, 225, 42, 1, 0x00010000)
    control("refresh", "BUTTON", "Refresh windows", 258, 344, 210, 42, 3, 0x00010000)
    control("cancel", "BUTTON", "Cancel", 572, 344, 220, 42, 2, 0x00010000)
    refresh()
    if not user.SetTimer(hwnd, 1, 250, None):
        raise ValueError
    user.ShowWindow(hwnd, 5)
    message = w.MSG()
    while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
        if not user.IsDialogMessageW(hwnd, ctypes.byref(message)):
            user.TranslateMessage(ctypes.byref(message))
            user.DispatchMessageW(ctypes.byref(message))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        send({"error": "native_picker_failed"})
        sys.exit(1)
