"""Owned synthetic native UIA fixture. No accounts, user documents or input hooks."""

import ctypes
import json
import os
import sys
import uuid
from ctypes import wintypes as w

user = ctypes.WinDLL("user32", use_last_error=True)
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)


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
user.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
user.UpdateWindow.argtypes = [w.HWND]
user.GetMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT]
user.TranslateMessage.argtypes = [ctypes.POINTER(w.MSG)]
user.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
user.DispatchMessageW.restype = ctypes.c_ssize_t
kernel.GetModuleHandleW.argtypes = [w.LPCWSTR]
kernel.GetModuleHandleW.restype = w.HMODULE


@WNDPROC
def procedure(hwnd, message, first, second):
    if message == 2:
        user.PostQuitMessage(0)
        return 0
    return user.DefWindowProcW(hwnd, message, first, second)


def main():
    if hasattr(user, "SetProcessDpiAwarenessContext"):
        user.SetProcessDpiAwarenessContext.argtypes = [w.HANDLE]
        user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    nonce = uuid.uuid4().hex
    title = "Immortility observing local only " + nonce
    instance = kernel.GetModuleHandleW(None)
    name = "IMMORTILITY_OBSERVER_" + nonce
    definition = WindowClass(
        procedure=procedure, instance=instance, background=ctypes.c_void_p(6), name=name
    )
    if not user.RegisterClassW(ctypes.byref(definition)):
        raise RuntimeError("Scratch window registration failed")
    # NOACTIVATE avoids stealing the user's keyboard focus. UIA reading needs no input.
    hwnd = user.CreateWindowExW(
        0x08000000, name, title, 0x00CF0000, 100, 100, 720, 470, None, None, instance, None
    )
    if not hwnd:
        raise RuntimeError("Scratch window creation failed")
    child = 0x40000000 | 0x10000000
    user.CreateWindowExW(
        0,
        "STATIC",
        "LOCAL READ-ONLY OBSERVATION TEST — synthetic content only",
        child,
        20,
        15,
        670,
        30,
        hwnd,
        None,
        instance,
        None,
    )
    code = "def add(a, b):\r\n    return a - b\r\n\r\nFixture note: the subtraction is intentional test evidence."
    user.CreateWindowExW(
        0,
        "EDIT",
        code,
        child | 0x00800000 | 0x0004 | 0x0800,
        20,
        60,
        660,
        230,
        hwnd,
        None,
        instance,
        None,
    )
    user.CreateWindowExW(
        0,
        "STATIC",
        "Synthetic protected field (never read its value):",
        child,
        20,
        310,
        480,
        25,
        hwnd,
        None,
        instance,
        None,
    )
    user.CreateWindowExW(
        0,
        "EDIT",
        "IMMORTILITY_SYNTHETIC_PASSWORD_CANARY",
        child | 0x00800000 | 0x0020,
        20,
        340,
        380,
        30,
        hwnd,
        None,
        instance,
        None,
    )
    user.CreateWindowExW(
        0,
        "BUTTON",
        "Explanation only — no click requested",
        child,
        420,
        340,
        260,
        35,
        hwnd,
        None,
        instance,
        None,
    )
    if "--wide" in sys.argv[1:]:
        for number in range(100):
            user.CreateWindowExW(
                0,
                "STATIC",
                f"Bounded synthetic node {number}",
                child,
                20,
                385,
                300,
                20,
                hwnd,
                None,
                instance,
                None,
            )
    user.ShowWindow(hwnd, 4)
    user.UpdateWindow(hwnd)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.GetProcessTimes.argtypes = [
        w.HANDLE,
        ctypes.POINTER(w.FILETIME),
        ctypes.POINTER(w.FILETIME),
        ctypes.POINTER(w.FILETIME),
        ctypes.POINTER(w.FILETIME),
    ]
    born, exited, cpu, user_cpu = w.FILETIME(), w.FILETIME(), w.FILETIME(), w.FILETIME()
    if not kernel.GetProcessTimes(
        kernel.GetCurrentProcess(),
        ctypes.byref(born),
        ctypes.byref(exited),
        ctypes.byref(cpu),
        ctypes.byref(user_cpu),
    ):
        raise RuntimeError("Scratch identity unavailable")
    created = (born.dwHighDateTime << 32) | born.dwLowDateTime
    print(
        json.dumps(
            {
                "hwnd": int(hwnd),
                "pid": os.getpid(),
                "created": created,
                "title": title,
                "nonce": nonce,
            }
        ),
        flush=True,
    )
    message = w.MSG()
    while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
        user.TranslateMessage(ctypes.byref(message))
        user.DispatchMessageW(ctypes.byref(message))


if __name__ == "__main__":
    main()
