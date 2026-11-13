"""One long-lived Qwen3-TTS process. Requests are JSON lines; library logs stay off stdout."""

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

REAL_STDOUT = sys.stdout

CANCEL = threading.Event()
GPU = threading.Lock()
ENGINE: dict[str, Any] = {}


def emit(kind: str, **payload: Any) -> None:
    REAL_STDOUT.write(json.dumps({"kind": kind, **payload}) + "\n")
    REAL_STDOUT.flush()


def cuda_ready() -> str | None:
    import torch

    if not torch.cuda.is_available():
        return "cuda_unavailable"
    major, _minor = torch.cuda.get_device_capability()
    if major < 8:
        return "cuda_unavailable"
    return None


def load_model() -> Any:
    if "model" in ENGINE:
        return ENGINE["model"]
    reason = cuda_ready()
    if reason:
        raise RuntimeError(reason)
    import torch
    from qwen_tts import Qwen3TTSModel

    from . import MODEL_ID, MODEL_REVISION

    started = time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32 = True
    model = Qwen3TTSModel.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    ENGINE["model"] = model
    ENGINE["load_seconds"] = round(time.perf_counter() - started, 3)
    return model


def build(message: dict[str, Any]) -> None:
    if message.get("consent") is not True:
        emit("error", id=message["id"], code="clone_consent_required")
        return
    source = Path(message["source"])
    reference = Path(message["reference"])
    profile = Path(message["profile"])
    metadata = Path(message["metadata"])
    transcript = str(message["transcript"])
    if not source.is_file():
        emit("error", id=message["id"], code="reference_missing")
        return
    from importlib.metadata import version

    from .profile import convert_reference, write_profile

    started = time.perf_counter()
    stats = convert_reference(source, reference)
    reference.with_name("transcript.txt").write_text(transcript + "\n", encoding="utf-8")
    model = load_model()
    import torch

    torch.cuda.reset_peak_memory_stats()
    prompt = model.create_voice_clone_prompt(
        ref_audio=str(reference),
        ref_text=transcript,
        x_vector_only_mode=False,
    )
    write_profile(
        prompt[0],
        profile,
        metadata,
        reference,
        transcript,
        version("qwen-tts"),
        stats,
    )
    ENGINE["prompt"] = prompt
    emit(
        "ok",
        id=message["id"],
        load_seconds=ENGINE.get("load_seconds", 0),
        build_seconds=round(time.perf_counter() - started, 3),
        peak_vram_mb=round(torch.cuda.max_memory_allocated() / 1e6, 1),
        retained_vram_mb=round(torch.cuda.memory_allocated() / 1e6, 1),
        **{key: stats[key] for key in ("duration_seconds", "peak", "sample_rate")},
    )


def ensure_prompt(profile: Path, metadata: Path) -> list[Any]:
    cached = ENGINE.get("prompt")
    if cached is not None:
        return list(cached)
    started = time.perf_counter()
    from dataclasses import replace

    from .profile import load_profile

    prompt = load_profile(profile, metadata)
    model = load_model()
    device = next(model.model.parameters()).device
    dtype = next(model.model.parameters()).dtype
    moved = []
    for item in prompt:
        code = None if item.ref_code is None else item.ref_code.to(device)
        embedding = item.ref_spk_embedding.to(device=device, dtype=dtype)
        moved.append(replace(item, ref_code=code, ref_spk_embedding=embedding))
    ENGINE["prompt"] = moved
    ENGINE["profile_seconds"] = round(time.perf_counter() - started, 3)
    return moved


def synthesize(message: dict[str, Any]) -> None:
    if CANCEL.is_set():
        emit("cancelled", id=message["id"])
        return
    profile = Path(message["profile"])
    metadata = Path(message["metadata"])
    if not profile.is_file() or not metadata.is_file():
        emit("error", id=message["id"], code="profile_missing")
        return
    out = Path(message["out"])
    text = str(message["text"]).strip()
    if not text:
        emit("error", id=message["id"], code="empty_speech")
        return
    with GPU:
        if CANCEL.is_set():
            emit("cancelled", id=message["id"])
            return
        model = load_model()
        prompt = ensure_prompt(profile, metadata)
        import numpy as np
        import torch

        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        with torch.inference_mode():
            wavs, rate = model.generate_voice_clone(
                text=text,
                language="English",
                voice_clone_prompt=prompt,
                non_streaming_mode=True,
            )
        if CANCEL.is_set():
            emit("cancelled", id=message["id"])
            return
        samples = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
        duration = len(samples) / int(rate) if rate else 0.0
        rms = float(np.sqrt(np.mean(samples * samples))) if len(samples) else 0.0
        if duration < 0.2 or rms < 1e-4:
            emit("error", id=message["id"], code="silent_audio")
            return
        peak = float(np.max(np.abs(samples))) or 1.0
        pcm = np.clip(samples / max(peak, 1.0), -1, 1)
        import wave

        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(int(rate))
            audio.writeframes((pcm * 32767).astype(np.int16).tobytes())
        emit(
            "ok",
            id=message["id"],
            path=str(out),
            sample_rate=int(rate),
            duration_seconds=round(duration, 3),
            rms=round(rms, 4),
            seconds=round(time.perf_counter() - started, 3),
            load_seconds=ENGINE.get("load_seconds", 0),
            profile_seconds=ENGINE.get("profile_seconds", 0),
            peak_vram_mb=round(torch.cuda.max_memory_allocated() / 1e6, 1),
            retained_vram_mb=round(torch.cuda.memory_allocated() / 1e6, 1),
        )


def shutdown() -> None:
    model = ENGINE.pop("model", None)
    ENGINE.clear()
    if model is not None:
        del model
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def handle(message: dict[str, Any]) -> None:
    op = message.get("op")
    if op == "cancel":
        CANCEL.set()
        emit("ok", id=message["id"])
        return
    if op == "status":
        emit(
            "ok",
            id=message["id"],
            loaded="model" in ENGINE,
            profile_cached="prompt" in ENGINE,
            load_seconds=ENGINE.get("load_seconds", 0),
        )
        return
    if op == "build":
        CANCEL.clear()
        build(message)
        return
    if op == "synthesize":
        synthesize(message)
        return
    if op == "shutdown":
        shutdown()
        emit("ok", id=message["id"])
        return
    emit("error", id=message.get("id", ""), code="operation_denied")


def main() -> None:
    sys.stdout = sys.stderr
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            emit("error", id="", code="invalid_request")
            continue
        if not isinstance(message, dict) or "id" not in message:
            emit("error", id="", code="invalid_request")
            continue
        try:
            handle(message)
        except RuntimeError as error:
            code = str(error) if str(error) in {"cuda_unavailable"} else "tts_failed"
            sys.stderr.write(code + "\n")
            emit("error", id=message["id"], code=code)
        except Exception:
            sys.stderr.write("tts_failed\n")
            emit("error", id=message["id"], code="tts_failed")
        if message.get("op") == "shutdown":
            return


if __name__ == "__main__":
    main()
