"""Broker-owned workspace tools.

Path checks reject links, drive roots, and protected names. They are not a
sandbox. Untrusted Python is not executed: Windows Sandbox is an optional VM
feature, and AppContainer is not a verified boundary for this process.
Writes happen only after approval, and only when the file bytes still match
the snapshot taken at proposal time.
"""

import difflib
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .contracts import BrokerError

PROTECTED = {
    ".env",
    ".git",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    ".aws",
    ".ssh",
    ".codex",
    ".agents",
    ".cache",
    "node_modules",
    "target",
}
DEVICES = {"con", "prn", "aux", "nul", "conin$", "conout$"} | {
    f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
}


@contextmanager
def _directory_guard(parent: Path) -> Iterator[None]:
    """Windows ancestors cannot be renamed or converted to reparse points mid-I/O."""
    if os.name != "nt":
        # Non-Windows workspace tools are not a claimed hostile-filesystem sandbox.
        yield
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handles = []
    try:
        for directory in [*reversed(parent.parents), parent]:
            if _linked(directory):
                raise BrokerError("tool_denied", "A workspace ancestor is a link.", 403)
            handle = kernel.CreateFileW(str(directory), 0, 1, None, 3, 0x02200000, None)
            if handle in {None, ctypes.c_void_p(-1).value}:
                raise BrokerError("tool_denied", "Cannot lock workspace directory identity.", 403)
            handles.append(handle)
            if _linked(directory):
                raise BrokerError("tool_denied", "Workspace directory changed.", 403)
        yield
    finally:
        for handle in reversed(handles):
            kernel.CloseHandle(handle)


def _read_bytes(path: Path, limit: int) -> bytes:
    """Read one nonlinked file with bounded allocation and handle identity checks."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetFileInformationByHandleEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
        if handle in {None, ctypes.c_void_p(-1).value}:
            raise BrokerError("tool_denied", "Cannot open a stable workspace file.", 403)
        tags = (wintypes.DWORD * 2)()
        if (
            not kernel.GetFileInformationByHandleEx(handle, 9, tags, ctypes.sizeof(tags))
            or tags[0] & 0x400
        ):
            kernel.CloseHandle(handle)
            raise BrokerError("tool_denied", "Reparse files are not followed.", 403)
        descriptor = msvcrt.open_osfhandle(int(handle), flags)
    else:
        descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        if os.fstat(stream.fileno()).st_nlink != 1:
            raise BrokerError("tool_denied", "Hard-linked files are not allowed.", 403)
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise BrokerError("context_limit", "File is too large for this tool.")
        return data


SOURCE_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml"}
_PATCH = re.compile(r"PATCH[ \t]+(\S+)\r?\n<<<\r?\n(.*?)\r?\n>>>", re.DOTALL)


def _linked(path: Path) -> bool:
    if path.is_symlink():
        return True
    junction = getattr(path, "is_junction", None)
    if callable(junction) and junction():
        return True
    if os.name != "nt" or not path.exists():
        return False
    attrs = ctypes_attributes(str(path))
    return bool(attrs is not None and attrs & 0x400)


def ctypes_attributes(path: str) -> int | None:
    if os.name != "nt":
        return None
    import ctypes

    value = ctypes.windll.kernel32.GetFileAttributesW(path)
    if value == 0xFFFFFFFF:
        return None
    return int(value)


def real_root(root: Path) -> Path:
    if str(root).startswith(("\\\\", "//")):
        raise BrokerError("tool_denied", "Network and device workspaces are not allowed.", 403)
    if not root.exists() or not root.is_dir() or _linked(root):
        raise BrokerError("tool_denied", "Workspace root is missing or is a link.", 403)
    resolved = root.resolve()
    if resolved == Path(resolved.anchor):
        raise BrokerError("tool_denied", "The workspace cannot be a drive root.", 403)
    return resolved


def locate(root: Path, relative: str) -> Path:
    raw = relative.replace("\\", "/")
    if not raw or raw.startswith("/") or ":" in raw or any(ord(c) < 32 for c in raw):
        raise BrokerError("tool_denied", "That path is not in the workspace.", 403)
    parts = raw.split("/")
    for part in parts:
        normalized = unicodedata.normalize("NFKC", part).casefold()
        if (
            not part
            or part in {".", ".."}
            or part != part.strip()
            or part.endswith(".")
            or normalized != part.casefold()
            or normalized in PROTECTED
            or normalized.startswith(".env.")
            or normalized.endswith((".pem", ".key"))
            or normalized.split(".")[0] in DEVICES
            or any(c in part for c in '<>"|?*~')
        ):
            raise BrokerError("tool_denied", "That path is protected or ambiguous.", 403)
    current = real_root(root)
    for part in parts:
        current = current / part
        if _linked(current):
            raise BrokerError("tool_denied", "Links are not followed.", 403)
        if current.is_file() and current.stat().st_nlink != 1:
            raise BrokerError("tool_denied", "Hard-linked files are not allowed.", 403)
    resolved = current.resolve()
    if not resolved.is_relative_to(real_root(root)):
        raise BrokerError("tool_denied", "That path is not in the workspace.", 403)
    return current


def list_sources(root: Path, limit: int = 20) -> list[str]:
    base = real_root(root)
    found: list[str] = []
    scanned = 0
    for folder, directories, files in os.walk(base, followlinks=False):
        kept = []
        for name in directories:
            try:
                locate(base, (Path(folder) / name).relative_to(base).as_posix())
                if not name.casefold().startswith(".venv"):
                    kept.append(name)
            except BrokerError:
                pass
        directories[:] = kept
        for name in files:
            scanned += 1
            if len(found) >= limit or scanned > 2000:
                return found
            path = Path(folder) / name
            if path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            relative = path.relative_to(base).as_posix()
            try:
                locate(base, relative)
            except BrokerError:
                continue
            found.append(relative)
    return found


def read_source(root: Path, relative: str, limit: int = 8000) -> str:
    path = locate(root, relative)
    if path.suffix.lower() not in SOURCE_SUFFIXES or not path.is_file():
        raise BrokerError("tool_denied", "That file cannot be read.", 403)
    with _directory_guard(path.parent):
        path = locate(root, relative)
        data = _read_bytes(path, limit)
    try:
        return data.decode("utf-8")
    except UnicodeError as error:
        raise BrokerError("tool_denied", "Only UTF-8 text files can be read.", 403) from error


def parse_patch(text: str) -> tuple[str, str] | None:
    match = _PATCH.search(text)
    if not match:
        return None
    body = match.group(2)
    if len(body.encode("utf-8")) > 32000:
        raise BrokerError("output_limit", "Proposed file exceeds the local limit.")
    return match.group(1), body


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_proposed(
    root: Path, relative: str, new_text: str, expected: str, *, expected_exists: bool | None = None
) -> None:
    with _directory_guard(locate(root, relative).parent):
        _apply_locked(root, relative, new_text, expected, expected_exists)


def _apply_locked(
    root: Path, relative: str, new_text: str, expected: str, expected_exists: bool | None
) -> None:
    if len(new_text.encode("utf-8")) > 32000:
        raise BrokerError("output_limit", "Proposed file exceeds the local limit.")
    path = locate(root, relative)
    if expected_exists is not None and path.exists() != expected_exists:
        raise BrokerError("stale_workspace", "File existence changed before approval.", 409)
    if path.suffix.lower() not in SOURCE_SUFFIXES:
        raise BrokerError("tool_denied", "That file cannot be written.", 403)
    current = _read_bytes(path, 32000).decode("utf-8") if path.is_file() else ""
    if fingerprint(current) != expected:
        raise BrokerError("stale_workspace", "The file changed before approval.", 409)
    handle, name = tempfile.mkstemp(prefix=".immortility-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(new_text.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck after staging: never trust a root/path snapshot across model latency.
        if locate(root, relative) != path:
            raise BrokerError("tool_denied", "Workspace identity changed.", 403)
        if expected_exists is not None and path.exists() != expected_exists:
            raise BrokerError("stale_workspace", "File existence changed before replacement.", 409)
        current = _read_bytes(path, 32000).decode("utf-8") if path.is_file() else ""
        if fingerprint(current) != expected:
            raise BrokerError("stale_workspace", "The file changed before replacement.", 409)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def preview_diff(before: str, after: str, relative: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=relative,
        tofile=relative,
        lineterm="",
    )
    return "\n".join(list(lines)[:200])[:4000]


def action_digest(payload: dict[str, str]) -> str:
    return fingerprint(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def remove_created(root: Path, relative: str, expected: str) -> None:
    with _directory_guard(locate(root, relative).parent):
        path = locate(root, relative)
        if fingerprint(_read_bytes(path, 32000).decode("utf-8")) != expected:
            raise BrokerError("stale_workspace", "The created file changed before rollback.", 409)
        path.unlink()


def run_unittest(root: Path) -> tuple[int, str]:
    """Untrusted code execution stays off until an isolation boundary is verified."""
    del root
    raise BrokerError(
        "tool_denied",
        "Untrusted code execution is disabled. No Windows isolation boundary is verified.",
        403,
    )


def save_rollback(data_dir: Path, task_id: str, payload: dict[str, str]) -> None:
    path = data_dir / "rollbacks" / f"{_proposal_path(data_dir, task_id).name}"
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(path, payload)


def load_rollback(data_dir: Path, task_id: str) -> dict[str, str]:
    path = data_dir / "rollbacks" / f"{_proposal_path(data_dir, task_id).name}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as error:
        raise BrokerError("not_found", "There is no rollback for this task.", 404) from error
    required = {"relative", "previous", "applied", "root"}
    if not isinstance(data, dict) or not required <= data.keys():
        raise BrokerError("not_found", "There is no rollback for this task.", 404)
    return {key: str(data[key]) for key in required} | {
        "previous_existed": str(data.get("previous_existed", "true"))
    }


def delete_rollback(data_dir: Path, task_id: str) -> None:
    path = data_dir / "rollbacks" / f"{_proposal_path(data_dir, task_id).name}"
    path.unlink(missing_ok=True)


def apply_workspace_file(settings: Any) -> None:
    data_dir = getattr(settings, "data_dir")
    path = Path(data_dir) / "workspace.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return
    if not isinstance(data, dict) or not isinstance(data.get("enabled"), bool):
        return
    settings.workspace_tools_enabled = data["enabled"]
    settings.project_read_enabled = data.get("project_read_enabled") is True
    root = data.get("root")
    if isinstance(root, str) and root:
        settings.workspace_root = Path(root)


def save_workspace_file(settings: Any, enabled: bool, root: str | None) -> None:
    if enabled:
        if not root:
            raise BrokerError("invalid_request", "Choose a workspace folder.", 400)
        checked = real_root(Path(root))
        settings.workspace_root = checked
        stored = str(checked)
    else:
        stored = str(getattr(settings, "workspace_root") or "")
    settings.workspace_tools_enabled = enabled
    data_dir = Path(getattr(settings, "data_dir"))
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "workspace.json").write_text(
        json.dumps(
            {
                "enabled": enabled,
                "root": stored,
                "project_read_enabled": settings.project_read_enabled,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _proposal_path(data_dir: Path, task_id: str) -> Path:
    if not task_id or any(char not in "0123456789abcdef-" for char in task_id.lower()):
        raise BrokerError("invalid_request", "Invalid task.", 400)
    return data_dir / "approvals" / f"{task_id}.json"


def save_proposal(data_dir: Path, task_id: str, payload: dict[str, str]) -> None:
    path = _proposal_path(data_dir, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(path, payload)


def _atomic_json(path: Path, payload: dict[str, str]) -> None:
    fd, name = tempfile.mkstemp(prefix=".record-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(payload).encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load_proposal(data_dir: Path, task_id: str) -> dict[str, str]:
    try:
        data = json.loads(_proposal_path(data_dir, task_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as error:
        raise BrokerError("not_found", "The approval expired.", 404) from error
    required = {
        "relative",
        "content",
        "expected",
        "root",
        "previous",
        "preview",
        "task_id",
        "session_id",
        "attempt_id",
        "previous_existed",
    }
    if not isinstance(data, dict) or not required <= data.keys():
        raise BrokerError("not_found", "The approval expired.", 404)
    return {key: str(data[key]) for key in required}


def delete_proposal(data_dir: Path, task_id: str) -> None:
    _proposal_path(data_dir, task_id).unlink(missing_ok=True)
