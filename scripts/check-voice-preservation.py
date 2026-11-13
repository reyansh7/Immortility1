"""Fingerprint private voice assets locally; never decode, modify or upload them."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/audits/voice-preservation.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    # Path.home is stable in the desktop sandbox; LOCALAPPDATA may be redirected.
    voice = Path.home() / "AppData/Local/Immortility/voice"
    source = ROOT / "immortility's_voice"
    files = []
    for folder in (voice, source):
        if folder.is_dir():
            files.extend(
                p
                for p in folder.rglob("*")
                if p.is_file()
                and not p.is_symlink()
                and not {"hf-cache", "torch-cache", "playback"}.intersection(
                    p.relative_to(folder).parts
                )
            )
    if args.record:
        if MANIFEST.exists():
            raise SystemExit("Refusing to overwrite the original preservation manifest")
        payload = {str(p): {"bytes": p.stat().st_size, "sha256": digest(p)} for p in files}
        if not payload:
            raise SystemExit("No private voice assets found; preservation was not recorded")
        MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(
            f"Recorded {len(payload)} private voice asset fingerprints locally. No audio decoded."
        )
    else:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        changed = sum(
            not Path(p).is_file()
            or Path(p).stat().st_size != item["bytes"]
            or digest(Path(p)) != item["sha256"]
            for p, item in payload.items()
        )
        print(f"Preservation: {len(payload)} assets checked; {changed} missing/changed.")
        if changed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
