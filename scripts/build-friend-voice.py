"""Build the local friend-voice profile and three listening samples.

Run with the isolated environment:

    .venv-tts\\Scripts\\python.exe scripts\\build-friend-voice.py

The original OGG is left in place. Nothing is uploaded.
"""

import json
import os
import sys
import time
import wave
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/tts/src"))

from immortility_tts.profile import convert_reference, wav_stats, write_profile  # noqa: E402
from immortility_tts.worker import ENGINE, ensure_prompt, load_model, shutdown  # noqa: E402

TRANSCRIPT = (
    "Hey, good morning! How are you doing today? I was just thinking about how quickly "
    "everything changes. Some days are exciting, and some are a little confusing. But that's "
    "okay. We can figure things out together, one step at a time."
)

SAMPLES = {
    "a-greeting.wav": "Hey! I'm Immortility. It's really nice to hear from you again.",
    "b-conversation.wav": (
        "Of course! I can help you with your project. Tell me what you're working on, "
        "and we'll figure it out together."
    ),
    "c-longer.wav": (
        "I've been looking through your project structure, and I think we can make a few "
        "improvements. We should start by checking the existing implementation, identifying "
        "anything unnecessary, and making sure everything runs smoothly."
    ),
}


def write_pcm(path: Path, samples: np.ndarray, rate: int) -> None:
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(pcm.tobytes())


def voice_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    return base / "Immortility" / "voice"


def main() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HOME", str(voice_dir() / "hf-cache"))
    source = ROOT / "immortility's_voice" / "audio1.ogg"
    if not source.is_file():
        raise SystemExit("Reference recording is missing.")
    root = voice_dir()
    root.mkdir(parents=True, exist_ok=True)
    reference = root / "reference.wav"
    profile = root / "friend_voice.pt"
    metadata = root / "friend_voice.json"
    report: dict[str, object] = {
        "model": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "revision": "5d83992436eae1d760afd27aff78a71d676296fc",
        "source": source.name,
        "transcript_flag": (
            "Supplied transcript used. Local Whisper base disagrees on the final clause only."
        ),
    }
    started = time.perf_counter()
    if not profile.is_file():
        stats = convert_reference(source, reference)
        (root / "transcript.txt").write_text(TRANSCRIPT + "\n", encoding="utf-8")
        model = load_model()
        torch.cuda.reset_peak_memory_stats()
        built = time.perf_counter()
        prompt = model.create_voice_clone_prompt(
            ref_audio=str(reference),
            ref_text=TRANSCRIPT,
            x_vector_only_mode=False,
        )
        write_profile(
            prompt[0],
            profile,
            metadata,
            reference,
            TRANSCRIPT,
            version("qwen-tts"),
            stats,
        )
        ENGINE["prompt"] = prompt
        report["profile_build_seconds"] = round(time.perf_counter() - built, 3)
        report["reference"] = stats
        report["build_peak_vram_mb"] = round(torch.cuda.max_memory_allocated() / 1e6, 1)
    else:
        report["profile"] = "reused"
    ready = time.perf_counter()
    model = load_model()
    prompt = ensure_prompt(profile, metadata)
    report["model_ready_seconds"] = round(time.perf_counter() - ready, 3)
    report["load_seconds"] = ENGINE.get("load_seconds", 0)
    samples = root / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    rendered = []
    for name, text in SAMPLES.items():
        torch.cuda.reset_peak_memory_stats()
        sample_started = time.perf_counter()
        with torch.inference_mode():
            wavs, rate = model.generate_voice_clone(
                text=text,
                language="English",
                voice_clone_prompt=prompt,
                non_streaming_mode=True,
            )
        samples = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
        out = (root / "samples") / name
        write_pcm(out, samples, int(rate))
        rendered.append(
            {
                "file": str(out),
                "text_words": len(text.split()),
                "synthesis_seconds": round(time.perf_counter() - sample_started, 3),
                "time_to_file_seconds": round(time.perf_counter() - sample_started, 3),
                "peak_vram_mb": round(torch.cuda.max_memory_allocated() / 1e6, 1),
                "retained_vram_mb": round(torch.cuda.memory_allocated() / 1e6, 1),
                **wav_stats(out),
            }
        )
    report["samples"] = rendered
    report["total_seconds"] = round(time.perf_counter() - started, 3)
    shutdown()
    destination = ROOT / "data" / "benchmarks" / "qwen-tts.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
