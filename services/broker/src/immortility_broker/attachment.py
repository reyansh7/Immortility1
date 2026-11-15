"""Opt-in current-user DPAPI rendezvous for an independently started local broker.

No service or autorun installation. The native UI reads this fixed data-root file;
credentials never enter the webview. DPAPI is not isolation from other code already
running as the same Windows user. Identity is rechecked before attachment.
"""

import ctypes
import os
import tempfile
from ctypes import wintypes as w
from pathlib import Path
from urllib.parse import urlsplit
from typing import Literal

from pydantic import Field, model_validator

from .capabilities import StrictModel
from .config import ROOT
from .contracts import BrokerError

FILENAME = "background-connection.dpapi"
ENTROPY = b"Immortility local headless connection v1"


class ConnectionRecord(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    runtime: Literal["local-read-workflows"] = "local-read-workflows"
    instance_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    url: str = Field(max_length=128)
    token: str = Field(min_length=32, max_length=128, repr=False)
    pid: int = Field(gt=0, lt=2**32)
    created: int = Field(gt=0, lt=2**63)
    executable: str = Field(min_length=3, max_length=4096)
    project_root: str = Field(min_length=3, max_length=4096)
    data_root: str = Field(min_length=3, max_length=4096)

    @model_validator(mode="after")
    def loopback_only(self) -> "ConnectionRecord":
        try:
            parts = urlsplit(self.url)
            if (
                parts.scheme != "http"
                or parts.hostname != "127.0.0.1"
                or not parts.port
                or parts.username
                or parts.password
                or parts.path
                or parts.query
                or parts.fragment
                or self.url != f"http://127.0.0.1:{parts.port}"
            ):
                raise ValueError
        except ValueError:
            raise ValueError("A literal loopback endpoint is required") from None
        return self


class Blob(ctypes.Structure):
    _fields_ = [("length", w.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, *, decrypt: bool = False) -> bytes:
    if os.name != "nt" or not 0 < len(data) <= 32000:
        raise BrokerError(
            "attachment_unavailable", "Bounded current-user Windows DPAPI is required.", 503
        )
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.POINTER(Blob),
    ]
    function.restype = w.BOOL
    kernel.LocalFree.argtypes = [w.HLOCAL]
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    extra = (ctypes.c_ubyte * len(ENTROPY)).from_buffer_copy(ENTROPY)
    source = Blob(len(data), buffer)
    entropy = Blob(len(ENTROPY), extra)
    output = Blob()
    try:
        # UI_FORBIDDEN only. Never LOCAL_MACHINE (which would allow other users).
        if not function(
            ctypes.byref(source), None, ctypes.byref(entropy), None, None, 1, ctypes.byref(output)
        ):
            raise BrokerError(
                "attachment_invalid", "Protected local connection could not be verified.", 403
            )
        if not 0 < output.length <= 32000:
            raise BrokerError(
                "attachment_invalid", "Protected local connection exceeds its bound.", 403
            )
        return ctypes.string_at(output.data, output.length)
    finally:
        if output.data:
            if decrypt:
                ctypes.memset(output.data, 0, output.length)
            kernel.LocalFree(output.data)
        ctypes.memset(buffer, 0, len(data))


def process_identity(pid: int | None = None) -> dict[str, int | str]:
    if os.name != "nt":
        raise BrokerError(
            "attachment_unavailable", "Native Windows process identity is required.", 503
        )
    pid = pid or os.getpid()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.GetProcessTimes.argtypes = [w.HANDLE, *([ctypes.POINTER(w.FILETIME)] * 4)]
    kernel.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
    kernel.QueryFullProcessImageNameW.argtypes = [
        w.HANDLE,
        w.DWORD,
        w.LPWSTR,
        ctypes.POINTER(w.DWORD),
    ]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    process = kernel.OpenProcess(0x1000, False, pid)
    try:
        times = [w.FILETIME() for _ in range(4)]
        name = ctypes.create_unicode_buffer(4096)
        length = w.DWORD(len(name))
        exit_code = w.DWORD()
        if (
            not process
            or not kernel.GetExitCodeProcess(process, ctypes.byref(exit_code))
            or exit_code.value != 259
            or not kernel.GetProcessTimes(process, *(ctypes.byref(value) for value in times))
            or not kernel.QueryFullProcessImageNameW(process, 0, name, ctypes.byref(length))
        ):
            raise BrokerError("attachment_stale", "Background runtime is no longer available.", 409)
        return {
            "pid": pid,
            "created": (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime,
            "executable": name.value,
        }
    finally:
        if process:
            kernel.CloseHandle(process)


def publish(data_root: Path, url: str, token: str, instance_id: str) -> tuple[Path, bytes]:
    """Caller must already own the opened SQLite data root and local-only runtime."""
    identity = process_identity()
    record = ConnectionRecord(
        instance_id=instance_id,
        url=url,
        token=token,
        pid=int(identity["pid"]),
        created=int(identity["created"]),
        executable=str(identity["executable"]),
        project_root=str(ROOT.resolve()),
        data_root=str(data_root.resolve()),
    )
    payload = _dpapi(record.model_dump_json().encode())
    path = data_root / FILENAME
    fd, temporary = tempfile.mkstemp(prefix=".connection-", suffix=".tmp", dir=data_root)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path, payload


def read(data_root: Path) -> ConnectionRecord:
    """Private test/native-client counterpart, never exposed through a broker route."""
    path = data_root / FILENAME
    try:
        with path.open("rb") as handle:
            encrypted = handle.read(32001)
        record = ConnectionRecord.model_validate_json(_dpapi(encrypted, decrypt=True))
        actual = process_identity(record.pid)
        if (
            actual["created"] != record.created
            or Path(str(actual["executable"])).resolve() != Path(record.executable).resolve()
            or Path(record.project_root).resolve() != ROOT.resolve()
            or Path(record.data_root).resolve() != data_root.resolve()
        ):
            raise ValueError
        return record
    except (ValueError, OSError):
        raise BrokerError(
            "attachment_invalid", "Local connection identity could not be verified.", 403
        ) from None


def unpublish(path: Path, owned: bytes) -> None:
    """Remove only this publisher's unchanged record; never a successor's file."""
    try:
        with path.open("rb") as handle:
            current = handle.read(32001)
        if current == owned:
            path.unlink()
    except FileNotFoundError:
        pass
