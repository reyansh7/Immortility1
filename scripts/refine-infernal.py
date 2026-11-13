"""Original American baritone comparisons. No actor reference audio or private voice data."""

import argparse
import json
import os
import shutil
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audition", action="store_true")
    parser.add_argument("--base", choices=["kokoro_onyx", "kokoro_fenrir"], default="kokoro_onyx")
    args = parser.parse_args()
    import numpy as np
    import psutil
    from immortility_broker.infernal import PRESETS
    from immortility_broker.infernal_tts import chunks

    text = json.loads((ROOT / "config/infernal-refinement.json").read_text())["text"]
    destination = ROOT / "data/previews/infernal-refinement"
    destination.mkdir(parents=True, exist_ok=True)
    if args.audition:
        jobs = [(base, base, PRESETS["natural"]) for base in ["kokoro_onyx", "kokoro_fenrir"]]
    else:
        shutil.copyfile(
            ROOT / "data/previews/infernal/kokoro_george-infernal.wav", destination / "Current.wav"
        )
        jobs = [
            ("Cinematic", args.base, PRESETS["cinematic_v2"]),
            ("Ultron-Inspired", args.base, PRESETS["ultron_inspired"]),
        ]
    results = []
    for label, base, preset in jobs:
        process = psutil.Process()
        cpu_start = process.cpu_times()
        working_set = [process.memory_info().rss]
        stop = threading.Event()

        def sample_memory() -> None:
            while not stop.wait(0.05):
                working_set.append(process.memory_info().rss)

        monitor = threading.Thread(target=sample_memory, daemon=True)
        monitor.start()
        started = time.perf_counter()
        first = None
        audio = []
        processing = 0.0
        rate = 24000
        for chunk in chunks(
            Path.home() / "AppData/Local/Immortility/models/infernal",
            text,
            {**preset, "infernal_base": base, "volume": 0.85},
        ):
            if first is None:
                first = time.perf_counter() - started
            rate = chunk.sample_rate
            audio.append(
                np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768
            )
            processing += chunk.processing_ms
        elapsed = time.perf_counter() - started
        stop.set()
        monitor.join()
        cpu_end = process.cpu_times()
        cpu_seconds = cpu_end.user + cpu_end.system - cpu_start.user - cpu_start.system
        samples = np.concatenate(audio)
        rms = float(np.sqrt(np.mean(samples * samples)))
        samples *= 0.10 / max(rms, 1e-6)
        samples *= min(1.0, 0.90 / max(float(np.max(np.abs(samples))), 1e-6))
        path = destination / f"{label}.wav"
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes((samples * 32767).astype(np.int16).tobytes())
        result = {
            "label": label,
            "base": base,
            "spoken_text": text,
            "options": preset,
            "render_seconds": round(elapsed, 3),
            "first_chunk_seconds": round(first or 0, 3),
            "processing_ms": round(processing, 3),
            "duration_seconds": round(len(samples) / rate, 3),
            "cpu_seconds": round(cpu_seconds, 3),
            "cpu_percent_one_core_equivalent": round(100 * cpu_seconds / elapsed, 1),
            "peak_working_set_mib": round(max(working_set) / 1024**2, 1),
            "inference_device": "cpu",
            "gpu_utilization_measured": False,
            "path": str(path.relative_to(ROOT)),
        }
        results.append(result)
        print(json.dumps(result), flush=True)
    name = "infernal-american-auditions.json" if args.audition else "infernal-refinement.json"
    (ROOT / "data/audits" / name).write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
