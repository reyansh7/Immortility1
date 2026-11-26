"""K29: verify every repo file pinned by SHA-256 in config/*.json matches byte-for-byte.

Line-ending conversion on checkout (core.autocrlf) silently breaks these pins, which turns
reviewed runtimes (screen observer, MCP, artifacts, voice models) into "unavailable".
Read-only; prints JSON and exits 1 on any mismatch of a tracked file.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEX = re.compile(r"^[0-9a-f]{64}$")


def pins(node, out):
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and HEX.match(value.lower()) and "/" in key:
                out.append((key, value.lower()))
            else:
                pins(value, out)
    elif isinstance(node, list):
        for item in node:
            pins(item, out)


def main() -> int:
    tracked = set(
        subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    )
    report = {"checked": 0, "tracked_mismatch": [], "untracked_mismatch": 0}
    for manifest in sorted((ROOT / "config").glob("*.json")):
        found: list[tuple[str, str]] = []
        pins(json.loads(manifest.read_text(encoding="utf-8")), found)
        for name, expected in found:
            path = ROOT / name
            if not path.is_file():
                continue
            report["checked"] += 1
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                if name in tracked:
                    report["tracked_mismatch"].append(f"{manifest.name}: {name}")
                else:
                    report["untracked_mismatch"] += 1
    print(json.dumps(report, indent=1))
    return 1 if report["tracked_mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
