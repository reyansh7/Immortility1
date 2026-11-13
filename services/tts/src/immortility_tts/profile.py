"""Reference-audio preparation. The original recording is never modified or uploaded."""

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import MODEL_ID, MODEL_REVISION

REFERENCE_RATE = 24000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def convert_reference(source: Path, destination: Path) -> dict[str, float | int]:
    if not source.is_file() or source.is_symlink():
        raise FileNotFoundError("reference recording is missing")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        str(REFERENCE_RATE),
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not destination.is_file():
        raise RuntimeError("reference conversion failed")
    return wav_stats(destination)


def wav_stats(path: Path) -> dict[str, float | int]:
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(str(path), always_2d=False)
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    rms = float(np.sqrt(np.mean(samples * samples))) if len(samples) else 0.0
    return {
        "sample_rate": int(rate),
        "channels": 1,
        "duration_seconds": round(len(samples) / rate, 3) if rate else 0.0,
        "peak": round(peak, 4),
        "rms": round(rms, 4),
        "clipped": peak >= 0.999,
    }


def write_profile(
    prompt_item: object,
    profile: Path,
    metadata: Path,
    reference: Path,
    transcript: str,
    package_version: str,
    audio_qc: dict[str, float | int | bool | str],
) -> None:
    import torch

    ref_code = getattr(prompt_item, "ref_code")
    embedding = getattr(prompt_item, "ref_spk_embedding")
    if not isinstance(embedding, torch.Tensor):
        raise TypeError("speaker embedding is not a tensor")
    code = None if ref_code is None else ref_code.detach().to("cpu").contiguous()
    if code is not None and not isinstance(code, torch.Tensor):
        raise TypeError("reference codes are not a tensor")
    profile.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"ref_code": code, "ref_spk_embedding": embedding.detach().to("cpu").contiguous()}, profile
    )
    payload = {
        "format_version": 1,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "package": "qwen-tts",
        "package_version": package_version,
        "reference_sha256": sha256(reference),
        "profile_sha256": sha256(profile),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "language": "English",
        "x_vector_only_mode": False,
        "icl_mode": True,
        "ref_text": transcript,
        "audio": audio_qc,
        "transcript_flag": (
            "Supplied transcript used. Local Whisper base disagrees on the final clause only."
        ),
        "serialization": "torch tensor dict loaded with weights_only=True",
    }
    metadata.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_profile(profile: Path, metadata: Path) -> list[object]:
    import torch
    from qwen_tts.inference.qwen3_tts_model import VoiceClonePromptItem

    meta = json.loads(metadata.read_text(encoding="utf-8"))
    if meta.get("format_version") != 1 or meta.get("model_id") != MODEL_ID:
        raise ValueError("voice profile metadata does not match this runtime")
    if meta.get("model_revision") != MODEL_REVISION:
        raise ValueError("voice profile revision does not match this runtime")
    if sha256(profile) != meta.get("profile_sha256"):
        raise ValueError("voice profile checksum does not match")
    blob = torch.load(profile, map_location="cpu", weights_only=True)
    if not isinstance(blob, dict):
        raise ValueError("voice profile payload is not a tensor dict")
    code = blob.get("ref_code")
    embedding = blob.get("ref_spk_embedding")
    if not isinstance(embedding, torch.Tensor):
        raise ValueError("voice profile is missing a speaker embedding")
    if code is not None and not isinstance(code, torch.Tensor):
        raise ValueError("voice profile reference codes are invalid")
    return [
        VoiceClonePromptItem(
            ref_code=code,
            ref_spk_embedding=embedding,
            x_vector_only_mode=False,
            icl_mode=True,
            ref_text=str(meta["ref_text"]),
        )
    ]
