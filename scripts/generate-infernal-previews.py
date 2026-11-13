"""Generate comparable public-text samples locally. No cloned profiles or cloud calls."""

import argparse
import json
import os
import sys
import threading
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
os.environ.update(
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
    HF_HUB_DISABLE_TELEMETRY="1",
    OMP_NUM_THREADS="2",
)
TEXT = "All systems are online. I am ready to assist. Give me a task, and I will handle it with precision. Your instructions remain in control."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base", choices=["piper_northern", "kokoro_george", "kokoro_fable"], required=True
    )
    args = parser.parse_args()
    import numpy as np
    import psutil
    from immortility_broker.infernal import PRESETS
    from immortility_broker.infernal_tts import chunks

    process = psutil.Process()
    peak = [0]
    stop = threading.Event()

    def monitor() -> None:
        while not stop.wait(0.02):
            peak[0] = max(peak[0], process.memory_info().rss)

    sampler = threading.Thread(target=monitor, daemon=True)
    sampler.start()
    destination = ROOT / "data/previews/infernal"
    destination.mkdir(parents=True, exist_ok=True)
    models = Path.home() / "AppData/Local/Immortility/models/infernal"
    results = []
    try:
        for name, preset in PRESETS.items():
            started = time.perf_counter()
            cpu_start = sum(process.cpu_times()[:2])
            audio = list(
                chunks(models, TEXT, {**preset, "infernal_base": args.base, "volume": 0.85})
            )
            elapsed = time.perf_counter() - started
            samples = np.concatenate(
                [
                    np.frombuffer(c.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768
                    for c in audio
                ]
            )
            rms = float(np.sqrt(np.mean(samples * samples)))
            samples *= 0.10 / max(rms, 1e-6)
            # Fair comparison level, with a bounded common peak and no clipping.
            samples *= min(1.0, 0.90 / max(float(np.max(np.abs(samples))), 1e-6))
            path = destination / f"{args.base}-{name}.wav"
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(audio[0].sample_rate)
                output.writeframes((samples * 32767).astype(np.int16).tobytes())
            row = {
                "base": args.base,
                "preset": name,
                "path": str(path.relative_to(ROOT)),
                "text": TEXT,
                "render_seconds": round(elapsed, 4),
                "processing_ms": round(sum(c.processing_ms for c in audio), 3),
                "duration_seconds": round(len(samples) / audio[0].sample_rate, 3),
                "cpu_seconds": round(sum(process.cpu_times()[:2]) - cpu_start, 4),
                "peak_working_set_mb": round(peak[0] / 1e6, 2),
                "rms_dbfs": round(
                    20 * np.log10(max(float(np.sqrt(np.mean(samples * samples))), 1e-8)), 2
                ),
                "peak_dbfs": round(20 * np.log10(max(float(np.max(np.abs(samples))), 1e-8)), 2),
                "inference_device": "cpu",
                "preset_options": preset,
            }
            results.append(row)
            print(json.dumps(row), flush=True)
    finally:
        stop.set()
        sampler.join(timeout=1)
    (ROOT / f"data/audits/infernal-{args.base}.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
