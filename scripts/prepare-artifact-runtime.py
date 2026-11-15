"""Record an inspected isolated report runtime; never install or download anything."""

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
expected = {"python-docx": "1.2.0", "reportlab": "4.4.9", "pypdf": "6.21.4", "pypdfium2": "5.13.0", "lxml": "6.1.1", "pillow": "13.0.0", "typing_extensions": "4.16.0", "charset-normalizer": "3.5.2"}
files, licenses = {}, []
for name, version in expected.items():
    distribution = importlib.metadata.distribution(name)
    if distribution.version != version:
        raise SystemExit("Artifact runtime version differs from reviewed pins")
    licenses.append({"name": name, "version": version, "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License"), "license_files": [str(f) for f in distribution.files or [] if "license" in str(f).lower() or "copying" in str(f).lower()]})
    for entry in distribution.files or []:
        path = Path(distribution.locate_file(entry)).resolve()
        if "__pycache__" in path.parts or path.suffix == ".pyc" or not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
script = "integrations/artifacts/report_worker.py"
files[script] = hashlib.sha256((ROOT / script).read_bytes()).hexdigest()
manifest = {"python_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(), "packages": expected, "files": files, "enabled_by_default": False, "bytecode_cache": "fresh per-worker prefix with writes disabled"}
(ROOT / "config/artifact-runtime.json").write_text(json.dumps(manifest, indent=2)+"\n")
(ROOT / "docs/implementation/M2_ARTIFACT_LICENSES.json").write_text(json.dumps({"packages": licenses, "note": "Declared licenses and retained wheel notices; packaging/redistribution remains a separate review. PDFium includes dependency notices."}, indent=2)+"\n")
print(json.dumps({"packages": len(expected), "pinned_files": len(files)}))
