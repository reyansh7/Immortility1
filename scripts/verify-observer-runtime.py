"""Verify the isolated experimental UIA runtime; --record is a review operation.

No packages are imported, installed or upgraded. Generated COM wrappers and
bytecode are deliberately excluded; they are Windows/Python runtime caches.
This is change detection, not protection from a hostile same-user process.
"""

import argparse
import hashlib
import json
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/observer-runtime.json"
SITE = ROOT / ".venv-observer/Lib/site-packages"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    paths = [
        ROOT / ".venv-observer/Scripts/python.exe",
        ROOT / ".venv-observer/pyvenv.cfg",
        ROOT / "config/observer-requirements.in",
        ROOT / "config/observer-requirements.lock",
        ROOT / "integrations/windows-observer/inspect_window.py",
        ROOT / "integrations/windows-observer/scratch_window.py",
        ROOT / "integrations/windows-observer/native_picker.py",
    ]
    for path in SITE.rglob("*"):
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = path.relative_to(SITE).as_posix()
        if "__pycache__" in path.parts or relative.startswith("comtypes/gen/"):
            continue
        paths.append(path)
    return {path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(paths)}


def record():
    packages = []
    for dist in sorted(distributions(path=[str(SITE)]), key=lambda d: d.metadata["Name"]):
        meta = dist.metadata
        files = [
            str(path).replace("\\", "/")
            for path in dist.files or []
            if "license" in str(path).lower() or "copying" in str(path).lower()
        ]
        packages.append(
            {
                "name": meta["Name"],
                "version": dist.version,
                "license_expression": meta.get("License-Expression"),
                "license": meta.get("License"),
                "license_classifiers": [
                    c for c in meta.get_all("Classifier", []) if c.startswith("License")
                ],
                "bundled_license_files": files,
            }
        )
    (ROOT / "docs/implementation/OBSERVER_LICENSE_INVENTORY.json").write_text(
        json.dumps(packages, indent=2) + "\n", encoding="utf-8"
    )
    data = {
        "status": "experimental scratch evaluation; no product tool registered",
        "files": snapshot(),
        "excluded": ["bytecode", "OS-generated comtypes/gen wrappers"],
        "not_a_sandbox": True,
    }
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(data['files'])} reviewed runtime file hashes; {len(packages)} packages")


def verify():
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    if snapshot() != expected:
        raise SystemExit("Observer runtime changed; review before another native evaluation")
    print(f"Observer runtime verified: {len(expected)} file hashes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    record() if args.record else verify()
