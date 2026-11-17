"""Read-only profile storage report and File Explorer reveal. Nothing is deleted."""

import ctypes
import json
import os
import re
import shutil
import subprocess
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable

from .contracts import BrokerError

REBUILDABLE = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "target",
        "dist",
        ".cache",
        "pip-cache",
        "cache",
        "gpucache",
        "code cache",
    }
)
PROFILE_FOLDERS = ("Downloads", "Documents", "Desktop", "Videos", "Pictures")
USER_DATA = frozenset({"documents", "desktop", "pictures", "videos"})
INSTALLERS = frozenset({".exe", ".msi", ".msix"})
ARCHIVES = frozenset({".zip", ".7z", ".rar", ".iso"})
MEDIA = frozenset({".mp4", ".mkv", ".mov", ".avi"})
RISK = {
    "rebuildable-candidate": "low",
    "installer-candidate": "medium",
    "archive": "medium",
    "potential-cache": "medium",
    "user-data": "high",
    "user-media": "high",
    "unknown": "high",
}


def apply_laptop_file(settings: Any) -> None:
    path = settings.data_dir / "laptop.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return
    if isinstance(data, dict) and isinstance(data.get("enabled"), bool):
        settings.laptop_tools_enabled = data["enabled"]


def intent(content: str) -> tuple[str, dict[str, str]] | None:
    text = " ".join(content.casefold().split())
    named = re.search(r"\bshow\s+(.+?)\s+in\s+(?:my\s+)?downloads\b", content, re.IGNORECASE)
    if named:
        filename = named.group(1).strip().strip("\"'")
        if filename and "folder" not in filename.casefold():
            return "desktop.reveal.v1", {"target": "downloads-file", "name": filename}
    if any(phrase in text for phrase in ("downloads folder", "my downloads")) and any(
        word in text for word in ("open", "show", "explorer")
    ):
        return "desktop.reveal.v1", {"target": "downloads"}
    if "largest" in text and any(word in text for word in ("folder", "explorer", "show")):
        return "desktop.reveal.v1", {"target": "largest-rebuildable"}
    if any(
        phrase in text
        for phrase in ("most ram", "most memory", "using the most memory", "consuming the most")
    ):
        return "laptop.resources.v1", {}
    if any(
        phrase in text
        for phrase in (
            "analyze my laptop",
            "analyse my laptop",
            "taking up space",
            "disk usage",
            "laptop storage",
        )
    ):
        return "laptop.storage.v1", {}
    return None


def classify(name: str, parent: str) -> str:
    folded = name.casefold()
    suffix = Path(name).suffix.casefold()
    if folded in REBUILDABLE or folded.endswith(".tmp"):
        return "rebuildable-candidate"
    if suffix in MEDIA:
        return "user-media"
    if parent.casefold() == "downloads" and suffix in INSTALLERS:
        return "installer-candidate"
    if parent.casefold() == "downloads" and suffix in ARCHIVES:
        return "archive"
    if parent.casefold() in USER_DATA:
        return "user-data"
    if folded in {"temp", "tmp", "logs"}:
        return "potential-cache"
    return "unknown"


def _is_reparse(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        junction = getattr(path, "is_junction", None)
        return bool(junction and junction())
    except OSError:
        return True


def _skip(entry: os.DirEntry[str]) -> bool:
    try:
        if entry.is_symlink():
            return True
        is_junction = getattr(entry, "is_junction", None)
        return bool(is_junction and is_junction())
    except OSError:
        return True


def _measure(path: Path, deadline: float, remaining: list[int]) -> tuple[int, bool]:
    total = 0
    truncated = False
    pending = [path]
    while pending:
        if time.monotonic() >= deadline or remaining[0] <= 0:
            return total, True
        folder = pending.pop()
        try:
            with os.scandir(folder) as iterator:
                children = list(iterator)
        except OSError:
            continue
        for entry in children:
            remaining[0] -= 1
            if remaining[0] <= 0 or time.monotonic() >= deadline:
                return total, True
            if _skip(entry):
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                    continue
                total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return total, truncated


def scan(
    root: Path,
    *,
    seconds: float = 8,
    max_entries: int = 3000,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Measure selected profile folders. File contents are not opened or uploaded."""
    root = Path(os.path.realpath(root))
    deadline = time.monotonic() + seconds
    usage = shutil.disk_usage(root.anchor or root)
    items: list[dict[str, Any]] = []
    truncated = False
    stopped = False
    per_folder = max(1, max_entries // len(PROFILE_FOLDERS))

    def halt() -> bool:
        return cancelled is not None and cancelled()

    for folder_name in PROFILE_FOLDERS:
        if halt():
            stopped = True
            break
        if time.monotonic() >= deadline:
            truncated = True
            break
        try:
            folder = authorize(root, root / folder_name)
        except BrokerError:
            continue
        if not folder.is_dir():
            continue
        remaining = [per_folder]
        try:
            with os.scandir(folder) as iterator:
                children = [entry for entry in iterator if not _skip(entry)]
        except OSError:
            continue
        for entry in children:
            if halt():
                stopped = True
                break
            if time.monotonic() >= deadline or remaining[0] <= 0:
                truncated = True
                break
            kind = classify(entry.name, folder_name)
            try:
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat(follow_symlinks=False).st_size
                    item_truncated = False
                else:
                    size, item_truncated = _measure(Path(entry.path), deadline, remaining)
            except OSError:
                continue
            truncated = truncated or item_truncated
            items.append(
                {
                    "path": str(Path(entry.path)),
                    "name": entry.name,
                    "parent": folder_name,
                    "bytes": size,
                    "class": kind,
                    "risk": RISK.get(kind, "high"),
                }
            )
        if stopped:
            break
    items.sort(key=lambda item: int(item["bytes"]), reverse=True)
    shown = items[:12]
    seen: dict[tuple[str, int], str] = {}
    duplicates: list[dict[str, Any]] = []
    for item in shown:
        key = (str(item["name"]).casefold(), int(item["bytes"]))
        if key in seen and int(item["bytes"]) > 0:
            duplicates.append(
                {"name": item["name"], "bytes": item["bytes"], "also": seen[key]}
            )
        else:
            seen[key] = str(item["path"])
    reclaimable = sum(
        int(item["bytes"]) for item in shown if item["class"] == "rebuildable-candidate"
    )
    return {
        "root": str(root),
        "drive_total": usage.total,
        "drive_free": usage.free,
        "items": shown,
        "duplicates": duplicates[:5],
        "reclaimable_bytes": reclaimable,
        "truncated": truncated,
        "cancelled": stopped,
        "deleted": False,
        "uploaded": False,
    }


def render(report: dict[str, Any]) -> str:
    def amount(value: int) -> str:
        step = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if step < 1024 or unit == "TB":
                return f"{step:.1f} {unit}"
            step /= 1024
        return f"{value} B"

    lines = [
        "Local storage scan of profile folders. No files were opened or deleted.",
        (
            f"Drive free {amount(int(report['drive_free']))} of "
            f"{amount(int(report['drive_total']))}."
        ),
        "Largest items:",
    ]
    if not report["items"]:
        lines.append("No readable items were found in Downloads, Documents, Desktop, Videos, or Pictures.")
    for item in report["items"]:
        lines.append(
            f"- {item['parent']}\\{item['name']} — {amount(int(item['bytes']))} — "
            f"{item['class']} — risk {item['risk']}"
        )
    if report["truncated"]:
        lines.append("The scan stopped at its time or entry limit, so some sizes are incomplete.")
    if report.get("cancelled"):
        lines.append("The scan was cancelled. No files were changed.")
    reclaimable = int(report.get("reclaimable_bytes", 0))
    lines.append(
        f"Estimated reclaimable space among rebuildable candidates: {amount(reclaimable)}. "
        "Installers, videos, and user data are not included."
    )
    duplicates = report.get("duplicates") or []
    if duplicates:
        lines.append("Duplicate candidates have the same name and size. Contents were not compared.")
        for item in duplicates:
            lines.append(f"- {item['name']} — {amount(int(item['bytes']))}")
    lines.append(
        "Rebuildable candidates may be safe to remove later, but only after an exact approval. "
        "User data is not a cleanup target."
    )
    return "\n".join(lines)


def _saved_report(data_dir: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((data_dir / "storage-last.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return data if isinstance(data, dict) else None


def save_report(data_dir: Path, report: dict[str, Any]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "storage-last.json").write_text(
        json.dumps(report, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _protected_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    for name in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        value = os.environ.get(name)
        if not value:
            continue
        try:
            roots.append(Path(os.path.realpath(value)))
        except OSError:
            continue
    return tuple(roots)


def _unc(path: Path) -> bool:
    text = str(path)
    return text.startswith("\\\\") or text.startswith("//")


def authorize(home: Path, candidate: Path) -> Path:
    """Canonicalize a path and keep it inside the profile. Reparse escapes are refused."""
    if _unc(candidate):
        raise BrokerError("tool_denied", "Refusing to open a network path.", 403)
    root = Path(os.path.abspath(home))
    raw = candidate if candidate.is_absolute() else root / candidate
    if _unc(raw):
        raise BrokerError("tool_denied", "Refusing to open a network path.", 403)
    normalized = Path(os.path.normpath(str(raw)))
    try:
        inside = normalized.is_relative_to(root)
    except ValueError:
        inside = False
    if not inside:
        raise BrokerError("tool_denied", "Refusing to open a path outside the user profile.", 403)
    try:
        real_root = Path(os.path.realpath(root))
        real = Path(os.path.realpath(normalized))
    except OSError as error:
        raise BrokerError("tool_denied", "That path could not be resolved.", 403) from error
    try:
        stayed = real.is_relative_to(real_root)
    except ValueError:
        stayed = False
    if not stayed:
        raise BrokerError("tool_denied", "Refusing to follow a symlink or junction.", 403)
    for protected in _protected_roots():
        try:
            blocked = real == protected or real.is_relative_to(protected)
        except ValueError:
            blocked = False
        if blocked:
            raise BrokerError("tool_denied", "Refusing to open a protected Windows folder.", 403)
    return real


def _named_file(folder: Path, name: str) -> Path:
    if (
        not name
        or name != Path(name).name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or len(name) > 180
    ):
        raise BrokerError("tool_denied", "That file name is not allowed.", 403)
    folded = name.casefold()
    try:
        with os.scandir(folder) as iterator:
            for entry in iterator:
                if _skip(entry) or entry.name.casefold() != folded:
                    continue
                if entry.is_file(follow_symlinks=False):
                    return Path(entry.path)
    except OSError as error:
        raise BrokerError("tool_denied", "That folder could not be read.", 403) from error
    raise BrokerError("tool_denied", "That file is not in the authorized folder.", 403)


def allowed_target(home: Path, target: str, data_dir: Path, name: str = "") -> tuple[Path, bool]:
    if target == "downloads":
        path = authorize(home, Path(home) / "Downloads")
        if not path.is_dir():
            raise BrokerError("tool_denied", "That folder is not available.", 403)
        return path, False
    if target == "downloads-file":
        folder = authorize(home, Path(home) / "Downloads")
        if not folder.is_dir():
            raise BrokerError("tool_denied", "That folder is not available.", 403)
        found = authorize(home, _named_file(folder, name))
        if not found.is_file():
            raise BrokerError("tool_denied", "That file is not in the authorized folder.", 403)
        return found, True
    if target == "largest-rebuildable":
        report = _saved_report(data_dir)
        match = next(
            (
                item
                for item in (report or {}).get("items", [])
                if item.get("class") == "rebuildable-candidate"
            ),
            None,
        )
        if match is None:
            raise BrokerError(
                "tool_denied",
                "No rebuildable folder is available from the last scan.",
                403,
            )
        path = authorize(home, Path(str(match["path"])))
        if not path.is_dir():
            raise BrokerError("tool_denied", "That folder is not available.", 403)
        return path, False
    raise BrokerError("tool_denied", "That folder is not an approved reveal target.", 403)


def select_in_explorer(path: Path) -> None:
    """Show one existing file selected. Explorer UI is opened on a new STA thread."""
    if os.name != "nt":
        raise OSError("Explorer selection is only available on Windows.")
    error: list[OSError] = []

    def run() -> None:
        try:
            _select_in_explorer(path)
        except OSError as caught:
            error.append(caught)

    worker = threading.Thread(target=run, name="explorer-select")
    worker.start()
    worker.join(timeout=8)
    if worker.is_alive():
        raise OSError("Explorer selection timed out.")
    if error:
        raise error[0]


def _select_in_explorer(path: Path) -> None:
    ole32 = ctypes.WinDLL("ole32")
    shell32 = ctypes.WinDLL("shell32")
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = ctypes.HRESULT
    ole32.CoUninitialize.argtypes = []
    shell32.ILCreateFromPathW.argtypes = [wintypes.LPCWSTR]
    shell32.ILCreateFromPathW.restype = ctypes.c_void_p
    shell32.ILFree.argtypes = [ctypes.c_void_p]
    shell32.SHOpenFolderAndSelectItems.argtypes = [
        ctypes.c_void_p,
        wintypes.UINT,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    shell32.SHOpenFolderAndSelectItems.restype = ctypes.HRESULT
    initialized = ole32.CoInitialize(None) in {0, 1}
    pidl = shell32.ILCreateFromPathW(str(path))
    if not pidl:
        if initialized:
            ole32.CoUninitialize()
        raise OSError("Explorer could not resolve that file.")
    try:
        result = shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
        if result != 0:
            raise OSError(f"Explorer selection failed ({result})")
    finally:
        shell32.ILFree(pidl)
        if initialized:
            ole32.CoUninitialize()


def reveal(
    home: Path,
    target: str,
    data_dir: Path,
    launcher: Callable[[list[str]], None] | None = None,
    name: str = "",
    select_item: Callable[[Path], None] | None = None,
) -> str:
    path, selecting = allowed_target(home, target, data_dir, name)

    def launch(args: list[str]) -> None:
        subprocess.Popen(args)

    try:
        if selecting:
            (select_item or select_in_explorer)(path)
        else:
            (launcher or launch)(["explorer.exe", str(path)])
    except OSError as error:
        raise BrokerError("tool_failed", "File Explorer could not be opened.", 503) from error
    action = "selected" if selecting else "opened"
    return f"File Explorer {action} {path}. No files were changed."


def resource_summary(sample: Callable[[], list[tuple[str, int]]] | None = None) -> str:
    """Read process working sets. Command lines are not collected."""

    def amount(value: int) -> str:
        step = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if step < 1024 or unit == "TB":
                return f"{step:.1f} {unit}"
            step /= 1024
        return f"{value} B"

    rows = sample() if sample is not None else _process_memory()
    if not rows:
        return "No process memory sample was available. No files were opened."
    name, working = rows[0]
    lines = [
        "Local process memory sample. No files were opened.",
        f"Highest working set: {name} — {amount(working)}.",
    ]
    for item_name, item_bytes in rows[1:5]:
        lines.append(f"- {item_name} — {amount(item_bytes)}")
    return "\n".join(lines)


def _process_memory() -> list[tuple[str, int]]:
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-Process | Sort-Object WorkingSet64 -Descending | "
            "Select-Object -First 5 -Property Name, WorkingSet64 | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        payload = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return []
    rows = payload if isinstance(payload, list) else [payload]
    result: list[tuple[str, int]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("Name", "")).strip()
        working = row.get("WorkingSet64", 0)
        if label and isinstance(working, int) and working >= 0:
            result.append((label, working))
    return result
