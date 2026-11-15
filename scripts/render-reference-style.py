"""Render a separately named mechanical preview from the selected dry cloned performance."""

import hashlib
import json
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))


def main() -> None:
    import numpy as np
    from pedalboard import HighpassFilter, PeakFilter, Pedalboard
    from immortility_broker.infernal import Coloration, InfernalDSP

    source = ROOT / "data/previews/reference-matched/Reference-Dry.wav"
    target = ROOT / "data/previews/reference-matched/Reference-Mechanical-Metal.wav"
    if target.exists():
        raise SystemExit("Refusing to overwrite an earlier preview")
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    with wave.open(str(source), "rb") as audio:
        assert audio.getnchannels() == 1 and audio.getsampwidth() == 2
        rate = audio.getframerate()
        samples = (
            np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32)
            / 32768
        )
    started = time.perf_counter()
    output = InfernalDSP(Coloration(-1.8, 0.95, 0.75, "clear_baritone")).process(samples, rate)
    phase = np.arange(len(output), dtype=np.float32) / rate
    carrier = (np.sin(2 * np.pi * 90 * phase) + 0.3 * np.sin(2 * np.pi * 133 * phase)) / 1.3
    output = 0.76 * output + 0.24 * output * carrier
    dry = output.copy()
    for milliseconds, gain in ((1.3, 0.12), (2.1, -0.07), (3.7, 0.06)):
        delay = round(rate * milliseconds / 1000)
        output[delay:] += dry[:-delay] * gain
    output = Pedalboard(
        [
            HighpassFilter(cutoff_frequency_hz=65),
            PeakFilter(cutoff_frequency_hz=780, gain_db=3.0, q=5.5),
            PeakFilter(cutoff_frequency_hz=1400, gain_db=2.5, q=5),
            PeakFilter(cutoff_frequency_hz=2600, gain_db=1.0, q=3),
        ]
    )(output.reshape(1, -1), rate).reshape(-1)
    output *= 0.1 / max(1e-9, float(np.sqrt(np.mean(output * output))))
    output *= min(1.0, 0.9 / max(1e-9, float(np.max(np.abs(output)))))
    assert len(output) == len(samples) and np.isfinite(output).all()
    with wave.open(str(target), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes((output * 32767).astype("<i2").tobytes())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original
    report = {
        "source": str(source),
        "output": str(target),
        "pitch_semitones": -1.8,
        "preserve_formants": True,
        "robotic_intensity": 0.95,
        "effects_strength": 0.75,
        "parallel_ring_modulation_wet": 0.24,
        "ring_frequencies_hz": [90, 133],
        "duration_seconds": len(output) / rate,
        "processing_ms": (time.perf_counter() - started) * 1000,
        "dry_source_unchanged": True,
        "default_changed": False,
        "new_synthesis": False,
    }
    (ROOT / "data/audits/reference-tts-mechanical-metal.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
