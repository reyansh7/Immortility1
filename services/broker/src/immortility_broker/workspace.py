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
from pathlib import Path
from typing import Any

from .contracts import BrokerError

PROTECTED = {".env", ".git", "id_rsa", "credentials.json"}
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
    if not root.exists() or not root.is_dir() or _linked(root):
        raise BrokerError("tool_denied", "Workspace root is missing or is a link.", 403)
    resolved = root.resolve()
    if resolved == Path(resolved.anchor):
        raise BrokerError("tool_denied", "The workspace cannot be a drive root.", 403)
    return resolved


def locate(root: Path, relative: str) -> Path:
    raw = relative.strip().replace("\\", "/")
    if not raw or raw.startswith("/") or ":" in raw or "\x00" in raw:
        raise BrokerError("tool_denied", "That path is not in the workspace.", 403)
    parts = Path(raw).parts
    if ".." in parts or any(part in PROTECTED or part.endswith((".pem", ".key")) for part in parts):
        raise BrokerError("tool_denied", "That path is protected.", 403)
    current = real_root(root)
    for part in parts:
        current = current / part
        if _linked(current):
            raise BrokerError("tool_denied", "Links are not followed.", 403)
    resolved = current.resolve()
    if not resolved.is_relative_to(real_root(root)):
        raise BrokerError("tool_denied", "That path is not in the workspace.", 403)
    return current


def list_sources(root: Path, limit: int = 20) -> list[str]:
    base = real_root(root)
    found: list[str] = []
    for path in base.rglob("*"):
        if len(found) >= limit:
            break
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
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
    data = path.read_bytes()
    if len(data) > limit:
        raise BrokerError("context_limit", "File is too large for this tool.")
    try:
        return data.decode("utf-8")
    except UnicodeError as error:
        raise BrokerError("tool_denied", "Only UTF-8 text files can be read.", 403) from error


def parse_patch(text: str) -> tuple[str, str] | None:
    match = _PATCH.search(text)
    if not match:
        return None
    body = match.group(2)
    if len(body) > 32000:
        raise BrokerError("output_limit", "Proposed file exceeds the local limit.")
    return match.group(1), body


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_proposed(root: Path, relative: str, new_text: str, expected: str) -> None:
    path = locate(root, relative)
    if path.suffix.lower() not in SOURCE_SUFFIXES:
        raise BrokerError("tool_denied", "That file cannot be written.", 403)
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    if fingerprint(current) != expected:
        raise BrokerError("stale_workspace", "The file changed before approval.", 409)
    temporary = path.with_name(path.name + ".immortility-tmp")
    temporary.write_text(new_text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def preview_diff(before: str, after: str, relative: str) -> str:
    lines = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=relative,
        tofile=relative,
        lineterm="",
    )
    return "\n".join(list(lines)[:200])[:4000]


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
    path.write_text(json.dumps(payload), encoding="utf-8")


def load_rollback(data_dir: Path, task_id: str) -> dict[str, str]:
    path = data_dir / "rollbacks" / f"{_proposal_path(data_dir, task_id).name}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as error:
        raise BrokerError("not_found", "There is no rollback for this task.", 404) from error
    required = {"relative", "previous", "applied", "root"}
    if not isinstance(data, dict) or not required <= data.keys():
        raise BrokerError("not_found", "There is no rollback for this task.", 404)
    return {key: str(data[key]) for key in required}


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
        json.dumps({"enabled": enabled, "root": stored}) + "\n", encoding="utf-8"
    )


def _proposal_path(data_dir: Path, task_id: str) -> Path:
    if not task_id or any(char not in "0123456789abcdef-" for char in task_id.lower()):
        raise BrokerError("invalid_request", "Invalid task.", 400)
    return data_dir / "approvals" / f"{task_id}.json"


def save_proposal(data_dir: Path, task_id: str, payload: dict[str, str]) -> None:
    path = _proposal_path(data_dir, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def load_proposal(data_dir: Path, task_id: str) -> dict[str, str]:
    try:
        data = json.loads(_proposal_path(data_dir, task_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as error:
        raise BrokerError("not_found", "The approval expired.", 404) from error
    required = {"relative", "content", "expected", "root", "previous", "preview"}
    if not isinstance(data, dict) or not required <= data.keys():
        raise BrokerError("not_found", "The approval expired.", 404)
    return {key: str(data[key]) for key in required}


def delete_proposal(data_dir: Path, task_id: str) -> None:
    _proposal_path(data_dir, task_id).unlink(missing_ok=True)
