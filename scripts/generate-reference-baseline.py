"""Matched stock Onyx baseline, with no cloning or FX, in the existing isolated runtime."""

import json
import os
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
os.environ.update(
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
    OMP_NUM_THREADS="2",
)


def main() -> None:
    import numpy as np
    from immortility_broker.infernal import PRESETS
    from immortility_broker.infernal_tts import chunks

    cases = json.loads((ROOT / "config/reference-tts-evaluation.json").read_text())
    folder = ROOT / "data/reference-tts/kokoro"
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for case, text in cases.items():
        path = folder / (case + "-onyx.wav")
        if path.exists():
            continue
        started = time.perf_counter()
        audio, first = [], None
        for chunk in chunks(
            Path.home() / "AppData/Local/Immortility/models/infernal",
            text,
            {**PRESETS["natural"], "infernal_base": "kokoro_onyx", "volume": 1.0},
        ):
            if first is None:
                first = time.perf_counter() - started
            audio.append(
                np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768
            )
            rate = chunk.sample_rate
        samples = np.concatenate(audio)
        samples *= min(3.0, 0.1 / max(1e-9, float(np.sqrt(np.mean(samples * samples)))))
        samples *= min(1.0, 0.9 / max(1e-9, float(np.max(np.abs(samples)))))
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes((samples * 32767).astype("<i2").tobytes())
        result = {
            "case": case,
            "first_chunk_seconds": first,
            "render_seconds": time.perf_counter() - started,
            "duration_seconds": len(samples) / rate,
            "device": "cpu",
            "voice": "am_onyx",
            "effects": False,
        }
        results.append(result)
        print(json.dumps(result), flush=True)
    if results:
        (ROOT / "data/audits/reference-tts-kokoro.json").write_text(
            json.dumps(results, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
