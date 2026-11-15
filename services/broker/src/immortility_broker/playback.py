"""Play a local PCM WAV. Cancellation is checked between short blocks."""

import subprocess
import threading
import wave
from collections.abc import Callable
from pathlib import Path

# Pitch-preserving tempo for the cloned voice. Matches the samples kept after listening.
CLONE_PLAYBACK_TEMPO = 1.3


def stretch_wav(path: Path, tempo: float) -> Path:
    """Write a faster WAV beside the source. The source file is left unchanged."""
    if not 0.5 <= tempo <= 2.0:
        raise ValueError("Playback tempo must stay between 0.5 and 2.0.")
    if abs(tempo - 1.0) < 0.01:
        return path
    target = path.with_name(f"{path.stem}.tempo.wav")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-filter:a",
            f"atempo={tempo:.2f}",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        check=True,
        timeout=60,
    )
    return target


def play_wav(
    path: Path,
    volume: float,
    stop: threading.Event,
    on_level: Callable[[float], None],
    tempo: float = 1.0,
    output_device: int | None = None,
) -> None:
    source = stretch_wav(path, tempo) if abs(tempo - 1.0) >= 0.01 else path
    try:
        _play_pcm(source, volume, stop, on_level, output_device)
    finally:
        if source != path:
            source.unlink(missing_ok=True)


def _play_pcm(
    path: Path,
    volume: float,
    stop: threading.Event,
    on_level: Callable[[float], None],
    output_device: int | None = None,
) -> None:
    import numpy as np
    import sounddevice as sd

    with wave.open(str(path), "rb") as audio:
        rate = audio.getframerate()
        channels = audio.getnchannels()
        frames = audio.readframes(audio.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768
    samples *= max(0.0, min(1.0, volume))
    block = max(1, int(rate * 0.02) * channels)
    with sd.OutputStream(
        samplerate=rate, channels=channels, dtype="float32", device=output_device
    ) as stream:
        for offset in range(0, len(samples), block):
            if stop.is_set():
                break
            chunk = samples[offset : offset + block]
            stream.write(chunk.reshape(-1, channels))
            level = float(np.sqrt(np.mean(chunk * chunk))) if len(chunk) else 0.0
            on_level(0.0 if level != level else min(1.0, level))
    on_level(0.0)
