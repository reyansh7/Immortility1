"""On-demand, keyless audio worker. Only a fixed operation enum is accepted.

JSON stdin/stdout is private to the broker. Audio and transcripts are never logged.
No microphone is opened by import, enumeration, model setup, STT, or TTS.
"""

import json
import math
import queue
import sys
import threading
import time
import wave
from pathlib import Path
from typing import Any, Protocol

from .voice_models import prepare, voice_path

PROTOCOL: Any = None


def emit(kind: str, **data: Any) -> None:
    output = PROTOCOL or sys.stdout
    output.write(json.dumps({"kind": kind, **data}) + "\n")
    output.flush()


class SpeechToText(Protocol):
    def transcribe(self, path: Path, language: str) -> str: ...


class TextToSpeech(Protocol):
    def chunks(self, text: str) -> Any: ...


class WhisperSTT:
    def __init__(self, root: Path, device: str = "cpu"):
        from faster_whisper import WhisperModel

        selected = "cpu"
        if device == "auto":
            import ctranslate2

            try:
                if (
                    ctranslate2.get_cuda_device_count()
                    and "float16" in ctranslate2.get_supported_compute_types("cuda")
                ):
                    selected = "cuda"
            except (RuntimeError, OSError):
                pass
            if selected == "cuda" and sys.platform == "win32":
                import ctypes

                try:
                    ctypes.WinDLL("cublas64_12.dll")
                    ctypes.WinDLL("cudnn64_9.dll")
                except OSError:
                    selected = "cpu"
        try:
            self.model = WhisperModel(
                str(root / "whisper"),
                device=selected,
                compute_type="float16" if selected == "cuda" else "int8",
                cpu_threads=2,
                num_workers=1,
                local_files_only=True,
            )
        except (RuntimeError, OSError):
            if selected != "cuda":
                raise
            self.model = WhisperModel(
                str(root / "whisper"),
                device="cpu",
                compute_type="int8",
                cpu_threads=2,
                num_workers=1,
                local_files_only=True,
            )

    def transcribe(self, path: Path, language: str) -> str:
        segments, _ = self.model.transcribe(
            str(path),
            language=None if language == "auto" else language,
            beam_size=3,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


class PiperTTS:
    def __init__(self, root: Path, voice: str, speed: float, volume: float):
        from piper import PiperVoice, SynthesisConfig

        self.voice = PiperVoice.load(voice_path(root, voice), use_cuda=False)
        self.config = SynthesisConfig(length_scale=1 / speed, volume=volume)

    def chunks(self, text: str) -> Any:
        return self.voice.synthesize(text, syn_config=self.config)


def devices() -> list[dict[str, Any]]:
    import sounddevice as sd

    apis = sd.query_hostapis()
    return [
        {
            "id": index,
            "name": str(d["name"]),
            "host": str(apis[d["hostapi"]]["name"]),
            "input": d["max_input_channels"] > 0,
            "output": d["max_output_channels"] > 0,
        }
        for index, d in enumerate(sd.query_devices())
        if d["max_input_channels"] or d["max_output_channels"]
    ]


def record(options: dict[str, Any]) -> None:
    # Defense in depth: a direct worker launch without consent also cannot capture.
    if options.get("microphone_consent") is not True:
        emit("error", code="microphone_consent_required")
        return
    import numpy as np
    import sounddevice as sd

    device = options.get("input_device")
    info = sd.query_devices(device, "input")
    rate = int(info["default_samplerate"])
    stop = threading.Event()

    def control() -> None:
        for line in sys.stdin:
            if line.strip() == "stop":
                stop.set()
                return
        stop.set()  # Parent closure never leaves recording active.

    threading.Thread(target=control, daemon=True).start()
    chunks = []
    started = time.monotonic()
    with sd.RawInputStream(
        device=device, samplerate=rate, channels=1, dtype="int16", blocksize=int(rate * 0.05)
    ) as stream:
        emit("ready")
        while not stop.is_set() and time.monotonic() - started < 30:
            data, overflow = stream.read(int(rate * 0.05))
            if overflow:
                raise RuntimeError("audio_overflow")
            raw = bytes(data)
            chunks.append(raw)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
            emit("meter", level=min(1.0, float(np.sqrt(np.mean(samples * samples)))))
    duration = sum(len(chunk) for chunk in chunks) / (rate * 2)
    if duration < 0.2:
        emit("error", code="recording_too_short")
        return
    with wave.open(options["path"], "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"".join(chunks))
    emit("done", duration_seconds=duration)


def speak(options: dict[str, Any], render: bool = False) -> None:
    import numpy as np
    import sounddevice as sd

    text = str(options["text"])[:6000]
    infernal = options.get("voice") == "infernal"
    if infernal:
        if options.get("infernal_authorized") is not True:
            raise ValueError("infernal_disabled")
        from .infernal_tts import chunks as infernal_chunks

        generated = infernal_chunks(Path(options["models"]) / "infernal", text, options)
    else:
        tts = PiperTTS(
            Path(options["models"]),
            options.get("voice", "ljspeech"),
            float(options.get("speed", 1)),
            float(options.get("volume", 0.7)),
        )
        generated = tts.chunks(text)
    if render:
        with wave.open(options["path"], "wb") as output:
            for render_chunk in generated:
                output.setnchannels(render_chunk.sample_channels)
                output.setsampwidth(2)
                output.setframerate(render_chunk.sample_rate)
                output.writeframes(render_chunk.audio_int16_bytes)
        emit("done")
        return
    chunks: queue.Queue[Any] = queue.Queue(maxsize=3)

    def produce() -> None:
        try:
            for chunk in generated:
                chunks.put(chunk)
        except Exception:
            chunks.put(False)
        finally:
            chunks.put(None)

    threading.Thread(target=produce, daemon=True).start()
    stream = None
    try:
        while True:
            chunk = chunks.get(timeout=30)
            if chunk is None:
                break
            if chunk is False:
                raise RuntimeError("tts_failed")
            if stream is None:
                stream = sd.RawOutputStream(
                    device=options.get("output_device"),
                    samplerate=chunk.sample_rate,
                    channels=chunk.sample_channels,
                    dtype="int16",
                    latency="low",
                )
                stream.start()
                emit("ready", output_latency_ms=round(float(stream.latency) * 1000, 3))
            raw = chunk.audio_int16_bytes
            step = max(2, int(chunk.sample_rate * 0.02) * 2 * chunk.sample_channels)
            for offset in range(0, len(raw), step):
                block = raw[offset : offset + step]
                stream.write(block)
                data = np.frombuffer(block, dtype=np.int16).astype(np.float32) / 32768
                level = float(np.sqrt(np.mean(data * data))) if len(data) else 0.0
                emit("meter", level=0.0 if not math.isfinite(level) else min(1.0, level))
        if stream is not None:
            stream.stop()  # Drain the last buffer before reporting completed playback.
        emit("done")
    finally:
        if stream is not None:
            stream.abort()
            stream.close()
        emit("meter", level=0.0)


def handle(options: dict[str, Any]) -> None:
    try:
        mode = options["operation"]
        if mode == "devices":
            emit("done", devices=devices())
        elif mode == "prepare":
            emit("done", **prepare(Path(options["models"])))
        elif mode == "record":
            record(options)
        elif mode == "transcribe":
            text = WhisperSTT(Path(options["models"]), options.get("stt_device", "cpu")).transcribe(
                Path(options["path"]), options.get("language", "en")
            )
            emit("done", text=text)
        elif mode in {"speak", "render"}:
            speak(options, mode == "render")
        else:
            emit("error", code="operation_denied")
    except Exception:
        # Never forward exception payloads or model text to process logs.
        emit("error", code="audio_device_or_engine_unavailable")


def main() -> None:
    global PROTOCOL
    PROTOCOL = sys.stdout
    for line in sys.stdin:
        try:
            options = json.loads(line)
            if not isinstance(options, dict):
                raise ValueError("invalid_request")
        except (ValueError, TypeError):
            emit("error", code="invalid_request")
            return
        handle(options)
        if options.get("voice") != "infernal" or options.get("keep_alive") is not True:
            return


if __name__ == "__main__":
    main()
