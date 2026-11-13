"""Read-only local analysis of public voice previews; ASR is a clarity proxy, not a listening score."""

import json
import argparse
import re
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))


def words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def word_error_rate(expected: str, actual: str) -> float:
    reference, hypothesis = words(expected), words(actual)
    row = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        next_row = [i]
        for j, right in enumerate(hypothesis, 1):
            next_row.append(min(row[j] + 1, next_row[-1] + 1, row[j - 1] + (left != right)))
        row = next_row
    return row[-1] / max(1, len(reference))


def metrics(path: Path) -> dict:
    with wave.open(str(path), "rb") as source:
        assert source.getnchannels() == 1 and source.getsampwidth() == 2
        rate = source.getframerate()
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2") / 32768.0
    # Indicative autocorrelation F0 only; timbre, accent and perceived character need listening.
    size, step = round(rate * 0.05), round(rate * 0.025)
    pitches, energies = [], []
    for start in range(0, len(samples) - size, step):
        frame = samples[start : start + size]
        rms = float(np.sqrt(np.mean(frame**2)))
        energies.append(rms)
        if rms < 0.025:
            continue
        frame = (frame - np.mean(frame)) * np.hanning(size)
        correlation = np.correlate(frame, frame, mode="full")[size - 1 :]
        low, high = round(rate / 300), round(rate / 65)
        lag = int(np.argmax(correlation[low:high])) + low
        if correlation[lag] > 0.65 * correlation[0]:
            pitches.append(rate / lag)
    rms = float(np.sqrt(np.mean(samples**2)))
    width = round(rate * 0.01)
    frames = samples[: len(samples) // width * width].reshape(-1, width)
    active = np.flatnonzero(np.sqrt(np.mean(frames**2, axis=1)) >= 0.003)
    gaps = np.diff(active) - 1
    return {
        "duration_seconds": round(len(samples) / rate, 3),
        "rms_dbfs": round(20 * np.log10(max(rms, 1e-12)), 2),
        "peak_dbfs": round(20 * np.log10(max(float(np.max(np.abs(samples))), 1e-12)), 2),
        "clipped_samples": int(np.sum(np.abs(samples) >= 32767 / 32768)),
        "internal_quiet_gaps_ge_250ms_seconds": [
            round(float(gap) * 0.01, 2) for gap in gaps if gap >= 25
        ],
        "gap_method": "10ms RMS <0.003 (-50.5 dBFS); includes breath/word tails, not phoneme alignment",
        "quiet_frame_fraction_below_minus_40_dbfs": round(
            float(np.mean(np.array(energies) < 0.01)), 3
        ),
        "indicative_voiced_median_f0_hz": round(float(np.median(pitches)), 1) if pitches else None,
        "f0_method": "50ms autocorrelation, 65-300Hz, confidence >0.65; not a perceptual rating",
    }


def main() -> None:
    from immortility_broker.voice_worker import WhisperSTT

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ab", action="store_true")
    args = parser.parse_args()
    root = ROOT / "data/previews" / ("infernal-refinement-v3" if args.ab else "infernal-refinement")
    expected = json.loads((ROOT / "config/infernal-refinement.json").read_text())["text"]
    stt = WhisperSTT(Path.home() / "AppData/Local/Immortility/models", device="cpu")
    result = []
    names = (
        ("A-Subtle", "B-Colder")
        if args.ab
        else ("kokoro_onyx", "kokoro_fenrir", "Current", "Cinematic", "Ultron-Inspired")
    )
    for name in names:
        path = root / f"{name}.wav"
        entry = {"label": name, **metrics(path)}
        start = time.perf_counter()
        transcript = stt.transcribe(path, "en")
        entry.update(
            local_asr_text=transcript,
            word_error_rate=round(word_error_rate(expected, transcript), 4),
            asr_seconds=round(time.perf_counter() - start, 3),
        )
        result.append(entry)
        print(json.dumps(entry), flush=True)
    report = (
        "infernal-refinement-v3-analysis.json" if args.ab else "infernal-refinement-analysis.json"
    )
    (ROOT / "data/audits" / report).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
