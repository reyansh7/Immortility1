"""One read-only UIA snapshot. No mouse/keyboard/capture/launch/shell operation.

Experimental worker: not registered as an Immortility agent tool. The caller
must be the broker permission authority, not model text. Native picker/indicator
acceptance and a wider application/session corpus are required before promotion.
"""

import ctypes
import hashlib
import json
import math
import os
import sys
import time
import uuid
from collections import deque
from ctypes import wintypes as w
from pathlib import Path


class Denied(Exception):
    pass


SENSITIVE_EXECUTABLES = {
    "consent.exe", "credentialuibroker.exe", "logonui.exe", "lockapp.exe", "msmpeng.exe",
    "securityhealthsystray.exe", "sechealthui.exe", "keepass.exe", "keepassxc.exe",
    "1password.exe", "bitwarden.exe", "codex.exe", "chatgpt.exe", "windowsterminal.exe",
    "cmd.exe", "powershell.exe", "pwsh.exe", "immortility.exe", "immortility-desktop.exe",
}


def native():
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    user.IsWindow.argtypes = [w.HWND]
    user.IsWindowVisible.argtypes = [w.HWND]
    user.IsIconic.argtypes = [w.HWND]
    user.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    user.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    user.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    user.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
    user.GetForegroundWindow.restype = w.HWND
    user.OpenInputDesktop.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    user.OpenInputDesktop.restype = w.HANDLE
    user.CloseDesktop.argtypes = [w.HANDLE]
    user.GetProcessWindowStation.restype = w.HANDLE
    user.GetUserObjectInformationW.argtypes = [
        w.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.POINTER(w.DWORD),
    ]
    user.GetThreadDesktop.argtypes = [w.DWORD]
    user.GetThreadDesktop.restype = w.HANDLE
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.GetProcessTimes.argtypes = [
        w.HANDLE,
        ctypes.POINTER(w.FILETIME),
        ctypes.POINTER(w.FILETIME),
        ctypes.POINTER(w.FILETIME),
        ctypes.POINTER(w.FILETIME),
    ]
    kernel.ProcessIdToSessionId.argtypes = [w.DWORD, ctypes.POINTER(w.DWORD)]
    kernel.QueryFullProcessImageNameW.argtypes = [
        w.HANDLE,
        w.DWORD,
        w.LPWSTR,
        ctypes.POINTER(w.DWORD),
    ]
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [
        w.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.POINTER(w.DWORD),
    ]
    return user, kernel, adv


def object_name(user, handle):
    buffer = ctypes.create_unicode_buffer(256)
    needed = w.DWORD()
    if not handle or not user.GetUserObjectInformationW(
        handle, 2, buffer, ctypes.sizeof(buffer), ctypes.byref(needed)
    ):
        raise Denied("desktop_unavailable")
    return buffer.value


def interactive(user):
    if object_name(user, user.GetProcessWindowStation()).casefold() != "winsta0":
        raise Denied("desktop_unavailable")
    desktop = user.OpenInputDesktop(0, False, 1)
    try:
        if not desktop or object_name(user, desktop) != "Default":
            raise Denied("desktop_unavailable")
        receiving = w.BOOL()
        needed = w.DWORD()
        if (
            not user.GetUserObjectInformationW(
                desktop, 6, ctypes.byref(receiving), ctypes.sizeof(receiving), ctypes.byref(needed)
            )
            or not receiving.value
        ):
            raise Denied("desktop_unavailable")
    finally:
        if desktop:
            user.CloseDesktop(desktop)


def title_of(user, hwnd):
    buffer = ctypes.create_unicode_buffer(4096)
    user.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def identity(user, kernel, adv, hwnd, pid, created):
    actual = w.DWORD()
    thread = user.GetWindowThreadProcessId(hwnd, ctypes.byref(actual))
    if (
        not user.IsWindow(hwnd)
        or actual.value != pid
        or not user.IsWindowVisible(hwnd)
        or user.IsIconic(hwnd)
    ):
        raise Denied("stale_window")
    session, current = w.DWORD(), w.DWORD()
    if (
        not kernel.ProcessIdToSessionId(pid, ctypes.byref(session))
        or not kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(current))
        or session.value != current.value
    ):
        raise Denied("wrong_session")
    if object_name(user, user.GetThreadDesktop(thread)) != "Default":
        raise Denied("desktop_unavailable")
    process = kernel.OpenProcess(0x1000, False, pid)
    token = w.HANDLE()
    try:
        if not process:
            raise Denied("target_unavailable")
        born, ended, cpu, user_cpu = w.FILETIME(), w.FILETIME(), w.FILETIME(), w.FILETIME()
        if (
            not kernel.GetProcessTimes(
                process,
                ctypes.byref(born),
                ctypes.byref(ended),
                ctypes.byref(cpu),
                ctypes.byref(user_cpu),
            )
            or ((born.dwHighDateTime << 32) | born.dwLowDateTime) != created
        ):
            raise Denied("stale_process")
        if not adv.OpenProcessToken(process, 8, ctypes.byref(token)):
            raise Denied("target_unavailable")
        elevation, needed = w.DWORD(), w.DWORD()
        if (
            not adv.GetTokenInformation(
                token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(needed)
            )
            or elevation.value
        ):
            raise Denied("elevated_target_denied")
        filename = ctypes.create_unicode_buffer(4096)
        length = w.DWORD(len(filename))
        if not kernel.QueryFullProcessImageNameW(process, 0, filename, ctypes.byref(length)):
            raise Denied("target_unavailable")
        if Path(filename.value).name.casefold() in SENSITIVE_EXECUTABLES:
            raise Denied("sensitive_window_denied")
    finally:
        if token:
            kernel.CloseHandle(token)
        if process:
            kernel.CloseHandle(process)


def check(request, user, kernel, adv):
    interactive(user)
    if time.time() >= request["expires_at"]:
        raise Denied("grant_expired")
    identity(user, kernel, adv, request["hwnd"], request["pid"], request["created"])
    identity(
        user,
        kernel,
        adv,
        request["indicator_hwnd"],
        request["indicator_pid"],
        request["indicator_created"],
    )
    if (
        title_of(user, request["indicator_hwnd"])
        != "Immortility observing local only " + request["lease_id"]
    ):
        raise Denied("indicator_unavailable")
    title = title_of(user, request["hwnd"])
    if hashlib.sha256(title.encode()).hexdigest() != request["title_sha256"]:
        raise Denied("stale_window")
    name = ctypes.create_unicode_buffer(256)
    user.GetClassNameW(request["hwnd"], name, len(name))
    if name.value == "#32770" or any(
        word in title.casefold()
        for word in ("credential", "windows security", "sign in", "user account control")
    ):
        raise Denied("sensitive_window_denied")


def validate(request):
    keys = {
        "operation",
        "task_id",
        "session_id",
        "lease_id",
        "hwnd",
        "pid",
        "created",
        "title_sha256",
        "expires_at",
        "indicator_hwnd",
        "indicator_pid",
        "indicator_created",
        "consent",
        "no_cloud",
    }
    if (
        not isinstance(request, dict)
        or set(request) != keys
        or request["operation"] != "inspect"
        or request["consent"] is not True
        or request["no_cloud"] is not True
    ):
        raise Denied("tool_denied")
    for name in ("task_id", "session_id", "lease_id"):
        try:
            uuid.UUID(request[name])
        except (ValueError, TypeError, AttributeError):
            raise Denied("invalid_request") from None
    for name in ("hwnd", "pid", "created", "indicator_hwnd", "indicator_pid", "indicator_created"):
        if type(request[name]) is not int or not 0 < request[name] < 2**63:
            raise Denied("invalid_request")
    if (
        type(request["expires_at"]) not in {int, float}
        or not math.isfinite(request["expires_at"])
        or not time.time() < request["expires_at"] <= time.time() + 30
    ):
        raise Denied("grant_expired")
    if (
        not isinstance(request["title_sha256"], str)
        or len(request["title_sha256"]) != 64
        or any(c not in "0123456789abcdef" for c in request["title_sha256"])
    ):
        raise Denied("invalid_request")


def bounded_edit_text(user, info, request, limit):
    """Legacy Win32 Edit may have ValuePattern only (unbounded BSTR).

    WM_GETTEXT copies at most the caller's buffer size. Only the reviewed
    native Edit class, within the exact target subtree, is eligible; no generic
    model-selected messages, input events or ValuePattern fallback exist.
    """
    hwnd = info.handle
    pid = w.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    user.IsChild.argtypes = [w.HWND, w.HWND]
    name = ctypes.create_unicode_buffer(256)
    user.GetClassNameW(hwnd, name, len(name))
    if (
        pid.value != request["pid"]
        or not user.IsChild(request["hwnd"], hwnd)
        or name.value != "Edit"
    ):
        return "[text pattern unavailable]"
    user.GetWindowLongW.argtypes = [w.HWND, ctypes.c_int]
    # ES_PASSWORD is checked independently of the provider's IsPassword bit.
    if user.GetWindowLongW(hwnd, -16) & 0x20 or info.element.CurrentIsPassword:
        raise Denied("protected_control")
    user.SendMessageTimeoutW.argtypes = [
        w.HWND,
        w.UINT,
        w.WPARAM,
        ctypes.c_void_p,
        w.UINT,
        w.UINT,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    user.SendMessageTimeoutW.restype = ctypes.c_ssize_t
    buffer = ctypes.create_unicode_buffer(limit + 1)
    copied = ctypes.c_size_t()
    if not user.SendMessageTimeoutW(
        hwnd, 0x000D, len(buffer), buffer, 0x0002 | 0x0020, 100, ctypes.byref(copied)
    ):
        return "[text unavailable]"
    if user.GetWindowLongW(hwnd, -16) & 0x20 or info.element.CurrentIsPassword:
        raise Denied("protected_control")
    return buffer.value[:limit]


def observe(request):
    validate(request)
    user, kernel, adv = native()
    if hasattr(user, "SetProcessDpiAwarenessContext"):
        user.SetProcessDpiAwarenessContext.argtypes = [w.HANDLE]
        user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    check(request, user, kernel, adv)
    from pywinauto import Desktop
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.uia_element_info import UIAElementInfo
    from pywinauto.uia_defines import IUIA

    root = (
        Desktop(backend="uia", allow_magic_lookup=False)
        .window(handle=request["hwnd"])
        .wrapper_object()
    )
    if (
        root.element_info.handle != request["hwnd"]
        or root.element_info.process_id != request["pid"]
    ):
        raise Denied("stale_window")
    pending = deque([(root, 0)])
    nodes = []
    remaining = 8000
    scheduled = 1
    truncated = False
    walker = IUIA().iuia.ControlViewWalker
    visited = 0
    while pending and visited < 64 and remaining > 0:
        item, depth = pending.popleft()
        visited += 1
        info = item.element_info
        if info.process_id != request["pid"]:
            continue
        try:
            protected = bool(info.element.CurrentIsPassword)
        except Exception:
            protected = True
        if protected:
            nodes.append(
                {"id": len(nodes), "depth": depth, "protected": True, "text": "[protected]"}
            )
            continue
        try:
            if info.element.CurrentIsOffscreen:
                continue
            kind = str(info.control_type)[:40]
            text = str(info.name or "")[: min(remaining, 256)]
            if kind in {"Edit", "Document"}:
                try:
                    text = str(item.iface_text.DocumentRange.GetText(min(remaining, 2000)))
                except Exception:
                    text = bounded_edit_text(user, info, request, min(remaining, 2000))
            text = text[: min(remaining, 2000)]
            if info.element.CurrentIsPassword:
                raise Denied("protected_control")
            rectangle = info.rectangle
            nodes.append(
                {
                    "id": len(nodes),
                    "depth": depth,
                    "protected": False,
                    "control_type": kind,
                    "text": text,
                    "rect": [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom],
                }
            )
            remaining -= len(text)
        except Exception:
            nodes.append(
                {"id": len(nodes), "depth": depth, "protected": True, "text": "[unavailable]"}
            )
            continue
        # FindAll/children() may allocate an unbounded COM array. Walk at most
        # 64 nodes total, including queued/skipped nodes, without that array.
        try:
            child = walker.GetFirstChildElement(info.element)
            if depth >= 4:
                truncated = truncated or bool(child)
                continue
            while child and scheduled < 64:
                pending.append((UIAWrapper(UIAElementInfo(child)), depth + 1))
                scheduled += 1
                child = walker.GetNextSiblingElement(child)
            truncated = truncated or bool(child)
        except Exception:
            truncated = True
    check(request, user, kernel, adv)
    rect = w.RECT()
    if not user.GetWindowRect(request["hwnd"], ctypes.byref(rect)):
        raise Denied("stale_window")
    dpi = 96
    if hasattr(user, "GetDpiForWindow"):
        user.GetDpiForWindow.argtypes = [w.HWND]
        user.GetDpiForWindow.restype = w.UINT
        dpi = int(user.GetDpiForWindow(request["hwnd"]))
    return {
        "schema_version": "1.0",
        "kind": "untrusted_ui_data",
        "task_id": request["task_id"],
        "lease_id": request["lease_id"],
        "hwnd": request["hwnd"],
        "pid": request["pid"],
        "created": request["created"],
        "observed_at": time.time(),
        "valid_until": min(request["expires_at"], time.time() + 2),
        "window_rect": [rect.left, rect.top, rect.right, rect.bottom],
        "dpi": dpi,
        "foreground": user.GetForegroundWindow() == request["hwnd"],
        "nodes": nodes,
        "truncated": truncated or bool(pending),
        "cloud_allowed": False,
        "screenshots": 0,
        "input_actions": 0,
    }


if __name__ == "__main__":
    try:
        line = sys.stdin.buffer.readline(4097)
        if len(line) > 4096:
            raise Denied("input_limit")
        result = observe(json.loads(line))
        encoded = json.dumps(result, ensure_ascii=False)
        if len(encoded.encode()) > 64000:
            raise Denied("output_limit")
        sys.stdout.buffer.write(encoded.encode("utf-8") + b"\n")
        sys.stdout.buffer.flush()
    except Denied as error:
        print(json.dumps({"error": str(error)}), flush=True)
        sys.exit(1)
    except Exception:
        print('{"error":"observer_failed"}', flush=True)
        sys.exit(1)
