"""Bounded local project reads through the existing broker gateway; no execution."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Literal

from pydantic import Field, field_validator

from .capabilities import StrictModel
from .config import Settings
from .contracts import BrokerError
from .policy import SECRET_FORMAT, guard_secret_egress
from .workspace import PROTECTED, _atomic_json, _directory_guard, _read_bytes, locate, real_root

SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".rs",
    ".css",
    ".html",
    ".yaml",
    ".yml",
}
MAX_FILE = 262144
MAX_TOTAL = 2 * 1024 * 1024


class ProjectChoice(StrictModel):
    enabled: bool
    root: str | None = Field(default=None, max_length=1024)
    local_read_consent: Literal[True]

    @field_validator("local_read_consent", mode="before")
    @classmethod
    def explicit(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit local read permission required")
        return value


class SearchInput(StrictModel):
    scope_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    query: str = Field(min_length=1, max_length=120)


class ReadInput(StrictModel):
    scope_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    path: str = Field(min_length=1, max_length=240)
    start_line: int = Field(default=1, ge=1, le=100000)
    lines: int = Field(default=60, ge=1, le=100)


class Hit(StrictModel):
    path: str = Field(max_length=240)
    line: int = Field(ge=1)
    text: str = Field(max_length=240)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SearchOutput(StrictModel):
    hits: list[Hit] = Field(max_length=32)
    files_scanned: int = Field(ge=0, le=2000)
    bytes_read: int = Field(ge=0, le=MAX_TOTAL)
    skipped_files: int = Field(ge=0, le=2000)
    truncated: bool
    scope_id: str
    source_trust: Literal["untrusted-data"] = "untrusted-data"


class ReadOutput(StrictModel):
    path: str = Field(max_length=240)
    text: str = Field(max_length=8000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    start_line: int
    end_line: int
    truncated: bool
    scope_id: str
    source_trust: Literal["untrusted-data"] = "untrusted-data"


def identity(root: Path) -> str:
    checked = real_root(root)
    stat = checked.stat()
    return hashlib.sha256(
        json.dumps([os.path.normcase(str(checked)), stat.st_dev, stat.st_ino]).encode()
    ).hexdigest()


def scope(settings: Settings) -> dict[str, Any]:
    if not settings.project_read_enabled or settings.workspace_root is None:
        return {"available": False, "scope_id": None, "folder_name": None}
    try:
        return {
            "available": True,
            "scope_id": identity(settings.workspace_root),
            "folder_name": settings.workspace_root.name,
        }
    except (OSError, BrokerError):
        return {"available": False, "scope_id": None, "folder_name": None}


def select(settings: Settings, choice: ProjectChoice) -> dict[str, Any]:
    root = (
        real_root(Path(choice.root)) if choice.enabled and choice.root else settings.workspace_root
    )
    if choice.enabled and (not choice.root or root is None):
        raise BrokerError("invalid_request", "Choose one project folder.", 400)
    guard_secret_egress([{"content": str(root or "")}], _keys(settings))
    same = root == settings.workspace_root
    enabled_edits = settings.workspace_tools_enabled and same
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _atomic_json(
        settings.data_dir / "workspace.json",
        {
            "root": str(root) if root else "",
            "enabled": enabled_edits,
            "project_read_enabled": choice.enabled,
        },
    )
    settings.workspace_root = root
    settings.workspace_tools_enabled = enabled_edits
    settings.project_read_enabled = choice.enabled
    return scope(settings)


def checked_root(settings: Settings, scope_id: str) -> Path:
    root = settings.workspace_root
    if not settings.project_read_enabled or root is None or identity(root) != scope_id:
        raise BrokerError(
            "project_scope_changed",
            "Project read permission changed; choose the folder again.",
            403,
        )
    return real_root(root)


def _keys(settings: Settings) -> list[str]:
    return [
        key.get_secret_value()
        for key in (
            settings.groq_api_key,
            settings.gemini_api_key,
            settings.nvidia_api_key,
            settings.openrouter_api_key,
        )
    ]


def _safe_text(text: str, keys: list[str]) -> str:
    for key in keys:
        if key:
            text = text.replace(key, "[redacted]")
    return SECRET_FORMAT.sub("[redacted]", text)


def _read(root: Path, relative: str, scope_id: str) -> bytes:
    path = locate(root, relative)
    if path.suffix.casefold() not in SUFFIXES or not path.is_file():
        raise BrokerError("tool_denied", "Only supported project text files can be read.", 403)
    with _directory_guard(path.parent):
        if identity(root) != scope_id:
            raise BrokerError("project_scope_changed", "Project directory identity changed.", 403)
        return _read_bytes(locate(root, relative), MAX_FILE)


def search(settings: Settings, arguments: SearchInput, stopped: threading.Event) -> dict[str, Any]:
    root = checked_root(settings, arguments.scope_id)
    keys = _keys(settings)
    guard_secret_egress([{"content": arguments.query}], keys)
    query = arguments.query.casefold()
    hits: list[dict[str, Any]] = []
    folders = [root]
    entries_seen = files = size = skipped = 0
    truncated = False
    deadline = time.monotonic() + 3
    while folders:
        if stopped.is_set():
            raise BrokerError("tool_cancelled", "Project inspection was stopped.", 409)
        if entries_seen >= 2000 or size >= MAX_TOTAL or time.monotonic() >= deadline:
            truncated = True
            break
        folder = folders.pop()
        try:
            if folder != root:
                locate(root, folder.relative_to(root).as_posix())
            with _directory_guard(folder), os.scandir(folder) as iterator:
                if identity(root) != arguments.scope_id:
                    raise BrokerError("project_scope_changed", "Project directory identity changed.", 403)
                entries = []
                for entry in iterator:
                    if entries_seen >= 2000:
                        truncated = True
                        break
                    entries_seen += 1
                    entries.append(entry)
                entries.sort(key=lambda item: item.name.casefold())
        except (OSError, BrokerError):
            continue
        for entry in entries:
            if stopped.is_set():
                raise BrokerError("tool_cancelled", "Project inspection was stopped.", 409)
            if len(hits) >= 32 or time.monotonic() >= deadline:
                truncated = True
                break
            if entry.name.startswith(".") or entry.name.casefold() in PROTECTED:
                continue
            relative = (folder / entry.name).relative_to(root).as_posix()
            try:
                if len(relative) > 240:
                    continue
                guard_secret_egress([{"content": relative}], keys)
                path = locate(root, relative)
                if path.is_dir():
                    folders.append(path)
                    continue
                if path.suffix.casefold() not in SUFFIXES:
                    continue
                files += 1
                # Size admission avoids allocating beyond the aggregate read budget.
                file_size = path.stat().st_size
                if file_size > MAX_FILE:
                    skipped += 1
                    continue
                if file_size > MAX_TOTAL - size:
                    truncated = True
                    break
                data = _read(root, relative, arguments.scope_id)
                if size + len(data) > MAX_TOTAL:
                    truncated = True
                    break
                size += len(data)
                text = data.decode("utf-8")
                guard_secret_egress([{"content": text}], keys)
                if "\0" in text:
                    skipped += 1
                    continue
                digest = hashlib.sha256(data).hexdigest()
                for number, line in enumerate(text.splitlines(), 1):
                    if query in line.casefold():
                        hits.append(
                            {
                                "path": relative,
                                "line": number,
                                "text": _safe_text(line, keys)[:240],
                                "sha256": digest,
                            }
                        )
                        if len(hits) >= 32:
                            truncated = True
                            break
            except (OSError, UnicodeError, BrokerError):
                skipped += 1
        if truncated:
            break
    checked_root(settings, arguments.scope_id)
    return {
        "hits": hits,
        "files_scanned": files,
        "bytes_read": size,
        "skipped_files": skipped,
        "truncated": truncated,
        "scope_id": arguments.scope_id,
        "source_trust": "untrusted-data",
    }


def read(settings: Settings, arguments: ReadInput, stopped: threading.Event) -> dict[str, Any]:
    if stopped.is_set():
        raise BrokerError("tool_cancelled", "Project inspection was stopped.", 409)
    root = checked_root(settings, arguments.scope_id)
    keys = _keys(settings)
    guard_secret_egress([{"content": arguments.path}], keys)
    data = _read(root, arguments.path, arguments.scope_id)
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise BrokerError("tool_denied", "Only UTF-8 project text is supported.", 403) from None
    if "\0" in text:
        raise BrokerError("tool_denied", "Binary files are not supported.", 403)
    guard_secret_egress([{"content": text}], keys)
    lines = text.splitlines()
    selected = lines[arguments.start_line - 1 : arguments.start_line - 1 + arguments.lines]
    selected_text = _safe_text("\n".join(selected), keys)
    checked_root(settings, arguments.scope_id)
    if stopped.is_set():
        raise BrokerError("tool_cancelled", "Project inspection was stopped.", 409)
    return {
        "path": arguments.path,
        "text": selected_text[:8000],
        "sha256": hashlib.sha256(data).hexdigest(),
        "start_line": arguments.start_line,
        "end_line": arguments.start_line + len(selected) - 1,
        "truncated": arguments.start_line - 1 + len(selected) < len(lines)
        or len(selected_text) > 8000,
        "scope_id": arguments.scope_id,
        "source_trust": "untrusted-data",
    }


async def invoke(settings: Settings, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    stopped = threading.Event()

    def run() -> dict[str, Any]:
        if name == "search":
            return search(settings, SearchInput.model_validate(arguments), stopped)
        return read(settings, ReadInput.model_validate(arguments), stopped)

    worker = asyncio.create_task(asyncio.to_thread(run))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        stopped.set()
        try:
            await worker
        except (BrokerError, asyncio.CancelledError):
            pass
        raise
