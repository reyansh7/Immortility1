"""Explicit public model setup. Never reads profiles, microphone, credentials or user audio."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    manifest = json.loads((ROOT / "config/infernal-models.json").read_text())
    destination = Path.home() / "AppData/Local/Immortility/models/infernal"
    for name, entry in manifest["files"].items():
        target = destination / name
        if target.is_file() and target.stat().st_size == entry["bytes"]:
            if hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".download")
        digest = hashlib.sha256()
        try:
            with urlopen(entry["url"], timeout=60) as response, partial.open("wb") as output:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    digest.update(block)
                    output.write(block)
            if partial.stat().st_size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
                raise ValueError("Public model checksum mismatch")
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
        print("Verified public model:", name)


if __name__ == "__main__":
    main()
