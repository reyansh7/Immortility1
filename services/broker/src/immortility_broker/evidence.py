"""Content-free source-state evidence for explicit engineering acceptance scripts."""

import hashlib
import importlib.metadata
import platform
import subprocess
import json
import tempfile
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from .config import ROOT


def engineering_output_path(stem: str, output: Path | None = None) -> Path:
    """Validate before any operation; new JSON only, never clobber history."""
    path = (
        output if output is not None else ROOT / ".cache/verification" / f"{stem}-{uuid4()}.json"
    ).resolve()
    allowed = [
        (ROOT / ".cache").resolve(),
        (ROOT / "docs/implementation").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    if path.suffix.lower() != ".json" or not any(
        path.is_relative_to(root) and path != root for root in allowed
    ):
        raise ValueError(
            "Evidence output must be a new JSON file in project cache, implementation docs or TEMP."
        )
    if path.exists():
        raise FileExistsError("Evidence output already exists; choose a new filename.")
    return path


def write_engineering_evidence(
    record: dict[str, object], stem: str, output: Path | None = None
) -> Path:
    """Exclusive creation also closes the validation-to-write collision race."""
    path = engineering_output_path(stem, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    return path


def implementation_provenance() -> dict[str, object]:
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(ROOT), *args],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None

    status = git("status", "--porcelain", "--untracked-files=normal")
    names = [
        "services/broker/src/immortility_broker/" + name
        for name in (
            "app.py",
            "agent_bridge.py",
            "semantic_stream.py",
            "provider_stream.py",
            "policy.py",
            "ledger.py",
            "providers.py",
            "hermes.py",
            "artifacts.py",
            "evidence.py",
        )
    ] + [
        "scripts/smoke-research-report.py",
        "integrations/artifacts/report_worker.py",
        "integrations/mcp-standard/agent_bridge.py",
        "packages/contracts/schemas/task-request.schema.json",
        "packages/contracts/schemas/event.schema.json",
        "config/agent-bridge-runtime.json",
    ]
    packages = {}
    for package in ("httpx", "pydantic", "fastapi"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = "missing"
    return {
        "diagnostic_schema_version": "1.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "git_head": git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(status) if status is not None else None,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in names
            if (ROOT / name).is_file()
        },
        "contract_version": "1.0",
        "database_schema_version": 4,
        "python": platform.python_version(),
        "platform": platform.system(),
        "packages": packages,
    }
