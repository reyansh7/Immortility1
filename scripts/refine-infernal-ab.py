"""Two non-promoted Onyx auditions from one identical performance; earlier WAVs retained."""

import hashlib
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


def write_wave(path, audio, rate):
    import numpy as np

    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes((audio * 32767).astype(np.int16).tobytes())


def main():
    import numpy as np
    import psutil
    import torch
    from immortility_broker.infernal import Coloration, InfernalDSP
    from immortility_broker.infernal_tts import chunks

    destination = ROOT / "data/previews/infernal-refinement-v3"
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(
            "Refusing to overwrite earlier auditions; archive/review them explicitly first."
        )
    destination.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "config/infernal-refinement.json").read_text())
    text = config["text"]
    torch.manual_seed(42)
    process = psutil.Process()
    cpu_before = process.cpu_times()
    working_set = [process.memory_info().rss]
    stop = threading.Event()

    def sample_memory():
        while not stop.wait(0.05):
            working_set.append(process.memory_info().rss)

    monitor = threading.Thread(target=sample_memory, daemon=True)
    monitor.start()
    started = time.perf_counter()
    first = None
    dry = []
    try:
        options = {
            **config["candidates"]["A-Subtle"],
            "robotic_intensity": 0.0,
            "effects_strength": 0.0,
            "volume": 1.0,
        }
        for chunk in chunks(
            Path.home() / "AppData/Local/Immortility/models/infernal", text, options
        ):
            if first is None:
                first = time.perf_counter() - started
            rate = chunk.sample_rate
            dry.append(
                np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768
            )
    finally:
        stop.set()
        monitor.join()
    elapsed = time.perf_counter() - started
    cpu_after = process.cpu_times()
    cpu_seconds = cpu_after.user + cpu_after.system - cpu_before.user - cpu_before.system
    source = np.concatenate(dry)
    write_wave(destination / "source-performance.wav", source, rate)
    results = []
    for label, options in config["candidates"].items():
        dsp = InfernalDSP(
            Coloration(
                options["pitch_semitones"],
                options["robotic_intensity"],
                options["effects_strength"],
                options["resonance_style"],
            )
        )
        start = time.perf_counter()
        output = np.concatenate([dsp.process(part, rate) for part in dry])
        processing_ms = (time.perf_counter() - start) * 1000
        # Identical RMS and peak ceiling; both use exactly the same dry PCM performance.
        output *= 0.1 / max(1e-6, float(np.sqrt(np.mean(output * output))))
        output *= min(1.0, 0.9 / max(1e-6, float(np.max(np.abs(output)))))
        path = destination / f"{label}.wav"
        write_wave(path, output, rate)
        result = {
            "label": label,
            "options": options,
            "processing_ms": round(processing_ms, 3),
            "duration_seconds": round(len(output) / rate, 3),
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        results.append(result)
        print(json.dumps(result), flush=True)
    report = {
        "status": config["status"],
        "text": text,
        "candidates": results,
        "source_performance_sha256": hashlib.sha256(
            (destination / "source-performance.wav").read_bytes()
        ).hexdigest(),
        "one_shared_cpu_performance": True,
        "pitch_shift_semitones": 0,
        "render_seconds": round(elapsed, 3),
        "first_chunk_seconds": round(first or 0, 3),
        "cpu_seconds": round(cpu_seconds, 3),
        "peak_working_set_mib": round(max(working_set) / 1024**2, 1),
        "gpu_utilization_measured": False,
        "inference_device": "cpu",
    }
    (ROOT / "data/audits/infernal-refinement-v3.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
