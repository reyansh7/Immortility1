"""Local CPU intelligibility checks and matched preview packaging. Never uploads audio."""

import json
import runpy
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))


def main() -> None:
    from immortility_broker.voice_worker import WhisperSTT

    helper = runpy.run_path(str(ROOT / "scripts/analyze-infernal.py"))
    report = json.loads((ROOT / "data/audits/reference-tts-latest.json").read_text())
    cases = json.loads((ROOT / "config/reference-tts-evaluation.json").read_text())
    stt = WhisperSTT(Path.home() / "AppData/Local/Immortility/models", device="cpu")
    results = []
    for row in report["results"]:
        if row["kind"] != "done":
            continue
        case = row["case"]
        sources = {
            "original_onyx": ROOT / "data/reference-tts/kokoro" / (case + "-onyx.wav"),
            "cloned_dry": ROOT / row["path"],
            "cloned_metal": ROOT / row["metal_path"],
        }
        for label, path in sources.items():
            if not path.resolve().is_relative_to((ROOT / "data/reference-tts").resolve()):
                raise ValueError("unapproved_audio_path")
            text = stt.transcribe(path, "en")
            entry = {
                "case": case,
                "variant": label,
                "transcript": text,
                "word_error_rate": helper["word_error_rate"](cases[case], text),
                **helper["metrics"](path),
            }
            results.append(entry)
            print(json.dumps(entry), flush=True)
    (ROOT / "data/audits/reference-tts-intelligibility.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
    destination = ROOT / "data/previews/reference-matched"
    destination.mkdir(parents=True, exist_ok=True)
    normal = next(row for row in report["results"] if row.get("case") == "normal")
    for name, path in {
        "Original-Onyx": ROOT / "data/reference-tts/kokoro/normal-onyx.wav",
        "Reference-Dry": ROOT / normal["path"],
        "Reference-Metal": ROOT / normal["metal_path"],
    }.items():
        target = destination / (name + ".wav")
        if target.exists():
            raise ValueError("preview_already_exists")
        shutil.copyfile(path, target)
    model = json.loads((ROOT / "config/reference-tts-models.json").read_text())
    license_path = (
        Path.home()
        / "AppData/Local/Immortility/models/reference-tts"
        / model["revision"]
        / "LICENSE.txt"
    )
    shutil.copyfile(license_path, destination / "LICENSE-XTTS.txt")
    print("Matched previews saved:", destination, flush=True)


if __name__ == "__main__":
    main()
