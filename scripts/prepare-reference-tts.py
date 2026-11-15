"""Download only the pinned public XTTS evaluation model; never read or upload voice data."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    manifest = json.loads((ROOT / "config/reference-tts-models.json").read_text(encoding="utf-8"))
    root = Path.home() / "AppData/Local/Immortility/models/reference-tts" / manifest["revision"]
    root.mkdir(parents=True, exist_ok=True)
    for name, item in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("invalid_model_filename")
        target = root / name
        digest = hashlib.sha256()
        if target.is_file() and not target.is_symlink():
            with target.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            if target.stat().st_size == item["bytes"] and digest.hexdigest() == item["sha256"]:
                continue
        temporary = target.with_suffix(target.suffix + ".download")
        digest = hashlib.sha256()
        try:
            with urlopen(item["url"], timeout=60) as response, temporary.open("wb") as output:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    digest.update(block)
                    output.write(block)
            if temporary.stat().st_size != item["bytes"] or digest.hexdigest() != item["sha256"]:
                raise ValueError("model_checksum_mismatch")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print("Verified public asset:", name, flush=True)


if __name__ == "__main__":
    main()
