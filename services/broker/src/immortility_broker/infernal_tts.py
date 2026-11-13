"""Pinned stock TTS voices, CPU only. No cloning, accounts or runtime downloads."""

import contextlib
import functools
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .infernal import Coloration, InfernalDSP, delivery_plan


@dataclass
class AudioChunk:
    audio_int16_bytes: bytes
    sample_rate: int
    sample_channels: int = 1
    processing_ms: float = 0.0


def conversational_edges(samples: Any, rate: int) -> Any:
    """Remove generated boundary silence, retaining 40/60 ms consonant guards.

    Used only by audition candidates. Quiet speech inside the phrase is untouched.
    A 5 ms RMS threshold of -54 dBFS avoids using individual zero crossings.
    """
    import numpy as np

    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    width = max(1, round(rate * 0.005))
    count = len(audio) // width
    if not count:
        return audio
    energy = np.sqrt(np.mean(audio[: count * width].reshape(count, width) ** 2, axis=1))
    speech = np.flatnonzero(energy >= 0.002)
    if not len(speech):
        return audio
    start = max(0, int(speech[0]) * width - round(rate * 0.04))
    end = min(len(audio), (int(speech[-1]) + 1) * width + round(rate * 0.06))
    return np.ascontiguousarray(audio[start:end])


@functools.lru_cache(maxsize=2)
def verify_models(root: Path, base: str) -> None:
    manifest = json.loads(
        (Path(__file__).resolve().parents[4] / "config/infernal-models.json").read_text(
            encoding="utf-8"
        )
    )
    for name, item in manifest["files"].items():
        if base == "piper_northern" and not name.startswith("piper/"):
            continue
        if base != "piper_northern" and not name.startswith("kokoro/"):
            continue
        path = root / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size != item["bytes"]:
            raise ValueError("infernal_model_missing")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for data in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(data)
        if digest.hexdigest() != item["sha256"]:
            raise ValueError("infernal_model_integrity")


@functools.lru_cache(maxsize=1)
def piper_model(root: Path) -> Any:
    from piper import PiperVoice

    verify_models(root, "piper_northern")
    return PiperVoice.load(root / "piper/en_GB-northern_english_male-medium.onnx", use_cuda=False)


@functools.lru_cache(maxsize=1)
def kokoro_model(root: Path) -> Any:
    import torch
    from kokoro import KModel

    verify_models(root, "kokoro_george")
    torch.set_num_threads(2)
    with contextlib.redirect_stdout(sys.stderr):
        model = (
            KModel(
                repo_id="hexgrad/Kokoro-82M",
                config=str(root / "kokoro/config.json"),
                model=str(root / "kokoro/kokoro-v1_0.pth"),
            )
            .to("cpu")
            .eval()
        )
        return model


@functools.lru_cache(maxsize=2)
def kokoro_pipeline(root: Path, language: str = "b") -> Any:
    import spacy
    from kokoro import KPipeline

    if not spacy.util.is_package("en_core_web_sm"):
        raise ValueError("infernal_pronunciation_model_missing")
    with contextlib.redirect_stdout(sys.stderr):
        return KPipeline(
            lang_code=language, repo_id="hexgrad/Kokoro-82M", model=kokoro_model(root), device="cpu"
        )


def chunks(root: Path, text: str, options: dict[str, Any]) -> Iterator[AudioChunk]:
    import numpy as np

    base = str(options.get("infernal_base", "piper_northern"))
    voices = {
        "kokoro_george": ("b", "bm_george"),
        "kokoro_fable": ("b", "bm_fable"),
        "kokoro_onyx": ("a", "am_onyx"),
        "kokoro_fenrir": ("a", "am_fenrir"),
    }
    if base not in {"piper_northern", *voices}:
        raise ValueError("infernal_voice_unknown")
    speed = float(options.get("speed", 0.94))
    if not 0.5 <= speed <= 2:
        raise ValueError("invalid_speech_speed")
    dsp = InfernalDSP(
        Coloration(
            float(options.get("pitch_semitones", -2.4)),
            float(options.get("robotic_intensity", 0.45)),
            float(options.get("effects_strength", 0.6)),
            str(options.get("resonance_style", "classic")),
        )
    )
    generated: Iterator[tuple[Any, int]]
    if base == "piper_northern":
        from piper import SynthesisConfig

        generated = (
            (chunk.audio_float_array, chunk.sample_rate)
            for chunk in piper_model(root).synthesize(
                text, syn_config=SynthesisConfig(length_scale=1 / speed)
            )
        )
    else:
        import torch

        language, voice = voices[base]
        pipeline = kokoro_pipeline(root, language)
        pack = torch.load(root / f"kokoro/{voice}.pt", map_location="cpu", weights_only=True)

        def generate() -> Iterator[tuple[Any, int]]:
            with contextlib.redirect_stdout(sys.stderr):
                for phrase, rate, pause, gain in delivery_plan(
                    text,
                    speed,
                    options.get("delivery") == "deliberate",
                    conversational=options.get("delivery") == "conversational",
                ):
                    for result in pipeline(phrase, voice=pack, speed=rate):
                        audio = result.audio.numpy()
                        if options.get("delivery") == "conversational":
                            audio = conversational_edges(audio, 24000)
                        yield audio * gain, 24000
                    if pause:
                        yield np.zeros(round(24000 * pause), dtype=np.float32), 24000

        generated = generate()
    for samples, rate in generated:
        started = time.perf_counter()
        processed = dsp.process(samples, rate)
        volume = max(0.0, min(1.0, float(options.get("volume", 0.7))))
        pcm = np.clip(processed * volume, -1, 1)
        yield AudioChunk(
            (pcm * 32767).astype(np.int16).tobytes(),
            rate,
            processing_ms=1000 * (time.perf_counter() - started),
        )
