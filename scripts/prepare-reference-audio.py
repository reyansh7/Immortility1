"""Prepare the specifically supplied local reference; never upload or change its source."""

import hashlib
import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\reyan\Downloads\now_im_free.mp3")
EXPECTED = "d161839fe97adf85ded67ce74fbbe413f996bd4a11049276c5bbee5852ddff71"


def main() -> None:
    import numpy as np
    from pedalboard import HighpassFilter, Pedalboard
    from pedalboard.io import AudioFile

    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError("reference_substitution_rejected")
    folder = ROOT / "data/reference-tts/reference"
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "reference.json"
    if manifest_path.exists():
        print("Reference already prepared; refusing to overwrite its review manifest.")
        return
    with AudioFile(str(SOURCE)) as source:
        rate = int(source.samplerate)
        audio = source.read(source.frames).mean(axis=0)
    # Conservative 100-160 ms margins around the previously measured speech.
    # Cropping/low-cut cannot remove overlapping music or undo cinematic effects.
    regions = [(0.20, 2.56), (4.14, 8.70)]
    raw = np.concatenate([audio[round(a * rate) : round(b * rate)] for a, b in regions])
    clean = Pedalboard([HighpassFilter(cutoff_frequency_hz=65)])(raw.reshape(1, -1), rate).reshape(
        -1
    )
    clean *= min(3.0, 0.1 / max(1e-9, float(np.sqrt(np.mean(clean * clean)))))
    clean *= min(1.0, 0.85 / max(1e-9, float(np.max(np.abs(clean)))))
    records = {}
    for name, samples in (("speech-crop", raw), ("conditioned", clean)):
        if not np.isfinite(samples).all():
            raise ValueError("nonfinite_reference")
        path = folder / (name + ".wav")
        if path.exists():
            raise ValueError("reference_asset_already_exists")
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())
        records[name] = {
            "name": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
    report = {
        "source_sha256": EXPECTED,
        "source_unchanged": True,
        "duration_seconds": round(len(raw) / rate, 3),
        "regions_seconds": regions,
        "files": records,
        "limitations": "Short, already processed mixed reference. Cropping and 65 Hz high-pass do not isolate a dry speaker.",
        "upload": False,
    }
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
