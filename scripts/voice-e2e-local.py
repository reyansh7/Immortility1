"""M2 voice end-to-end with SYNTHETIC audio only (never opens a microphone).

Piper renders a spoken question -> faster-whisper (local, CPU) transcribes it ->
the real broker answers as a voice task on the local Qwen route (cloud keys blanked)
-> the Ultron-inspired INFERNAL voice renders the reply to a WAV file. Also checks
playback cancel (volume 0) and an unavailable output device. Inference is LIVE local,
audio input is synthetic; live microphone tests stay PENDING (see VOICE_LIVE_PROCEDURE).
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import tempfile
import threading
import time
import urllib.request
import wave
from pathlib import Path

import numpy as np
import uvicorn
from pydantic import SecretStr

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import uid
from immortility_broker.store import Store
from immortility_broker.voice import VoiceService

MODELS = Path(os.environ["LOCALAPPDATA"]) / "Immortility" / "models"
CLOUD = ("openrouter_api_key", "gemini_api_key", "groq_api_key", "nvidia_api_key")
QUESTIONS = [
    ("What is the capital of France?", ["paris"]),
    ("Name one planet with rings.", ["saturn", "jupiter", "uranus", "neptune"]),
    ("How many days are in a week?", ["seven", "7"]),
]
ULTRON = {"voice": "infernal", "voice_preset": "ultron_conversational", "infernal_base": "kokoro_onyx",
          "pitch_semitones": 0.0, "robotic_intensity": 0.36, "effects_strength": 0.45, "speed": 1.0,
          "resonance_style": "clear_baritone", "delivery": "conversational", "volume": 0.7}


def wer(expected: str, actual: str) -> float:
    e = expected.lower().replace(".", "").replace("?", "").replace(",", "").split()
    a = actual.lower().replace(".", "").replace("?", "").replace(",", "").split()
    row = list(range(len(a) + 1))
    for i, word in enumerate(e, 1):
        nxt = [i]
        for j, other in enumerate(a, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (word != other)))
        row = nxt
    return row[-1] / max(1, len(e))


def audio_stats(path: Path) -> dict:
    with wave.open(str(path), "rb") as w:
        rate, frames = w.getframerate(), w.readframes(w.getnframes())
    x = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    rms = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
    return {"seconds": round(x.size / rate, 2), "rate": rate, "peak_dbfs": round(20 * np.log10(max(peak, 1e-9)), 1),
            "rms_dbfs": round(20 * np.log10(max(rms, 1e-9)), 1),
            "clipped_fraction": round(float(np.mean(np.abs(x) > 0.999)), 5)}


async def main() -> int:  # noqa: C901
    out_dir = Path(os.environ["LOCALAPPDATA"]) / "Immortility" / "canary-m2-voice"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "local-model.json").write_text(json.dumps({"enabled": True, "model": "immortility-qwen3.5-4b"}))
    settings = Settings(_env_file=None, data_dir=out_dir)
    for f in CLOUD:
        setattr(settings, f, SecretStr(""))
    token = os.urandom(32).hex()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    url = f"http://127.0.0.1:{listener.getsockname()[1]}"
    app = create_app(settings, token, url)
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    thread = threading.Thread(target=lambda: asyncio.run(server.serve(sockets=[listener])), daemon=True)
    thread.start()
    while not server.started:
        await asyncio.sleep(0.05)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def call(method, path, body=None):
        req = urllib.request.Request(url + path, method=method, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")

    call("POST", "/v1/settings/model-mode", {"mode": "local_qwen", "route_id": None})
    report: dict = {"schema_version": "1.0", "microphone_opened": False, "audio_input": "synthetic_piper",
                    "inference": "live_local_qwen", "cloud_calls": 0, "turns": []}

    async def forbidden(*args):
        raise AssertionError("The voice helper must not start tasks itself")

    with tempfile.TemporaryDirectory(prefix="imm-voice-e2e-") as tmp:
        vs = Settings(_env_file=None, data_dir=Path(tmp), infernal_voice_enabled=True)
        store = Store(Path(tmp) / "db")
        voice = VoiceService(vs, store, forbidden, forbidden)
        voice.models = MODELS
        try:
            for index, (question, accept) in enumerate(QUESTIONS):
                turn: dict = {"question": question}
                fixture = Path(tmp) / f"q{index}.wav"
                t = time.monotonic()
                await voice.worker("render", text=question, voice="ljspeech", path=str(fixture))
                turn["fixture_render_ms"] = round((time.monotonic() - t) * 1000)
                t = time.monotonic()
                stt = await voice.worker("transcribe", path=str(fixture), language="en", stt_device="cpu")
                turn["stt_ms"] = round((time.monotonic() - t) * 1000)
                turn["transcript"] = str(stt.get("text", "")).strip()
                turn["wer"] = round(wer(question, turn["transcript"]), 3)
                session = call("POST", "/v1/sessions")["id"]
                t = time.monotonic()
                task = call("POST", "/v1/tasks", {"schema_version": "1.0", "session_id": session,
                                                  "request_id": uid(), "content": turn["transcript"],
                                                  "cloud_consent": True, "source": "voice",
                                                  "response_length": "brief", "allowed_capabilities": []})
                while task.get("status") not in {"succeeded", "failed", "blocked", "cancelled"}:
                    await asyncio.sleep(0.05)
                    task = call("GET", f"/v1/tasks/{task['task_id']}")
                turn["broker_ms"] = round((time.monotonic() - t) * 1000)
                reply = (task.get("result") or {}).get("text", "")
                turn.update(status=task["status"], provider=(task.get("result") or {}).get("provider"), reply=reply)
                turn["answer_ok"] = any(a in reply.lower() for a in accept)
                speech = out_dir / f"reply{index}-ultron.wav"
                t = time.monotonic()
                await voice.worker("render", text=reply or "No reply.", path=str(speech), **ULTRON)
                turn["tts_render_ms"] = round((time.monotonic() - t) * 1000)
                turn["tts"] = audio_stats(speech)
                turn["voice_to_audio_ms"] = turn["stt_ms"] + turn["broker_ms"] + turn["tts_render_ms"]
                report["turns"].append(turn)
                print(json.dumps(turn))
            # Playback cancel (barge-in path): silent playback, stop mid-utterance.
            job = asyncio.create_task(voice.worker("speak", text="This sentence is long enough to be interrupted halfway through by the cancel path.", voice="ljspeech", volume=0.0))
            t = time.monotonic()
            while voice.tts_state != "speaking" and time.monotonic() - t < 20 and not job.done():
                await asyncio.sleep(0.02)
            await asyncio.sleep(0.3)
            t_cancel = time.monotonic()
            job.cancel()
            try:
                await job
            except (asyncio.CancelledError, Exception):
                pass
            await voice.stop_worker()
            report["playback_cancel_ms"] = round((time.monotonic() - t_cancel) * 1000)
            report["worker_after_cancel"] = None if voice.process is None else voice.process.returncode
            try:
                await voice.worker("speak", text="Device test.", voice="ljspeech", output_device=999, volume=0.0)
                report["unavailable_output_rejected"] = False
            except Exception:
                report["unavailable_output_rejected"] = True
        finally:
            await voice.stop_worker()
            await voice._stop_infernal()
            store.db.close()
            server.should_exit = True
            thread.join(timeout=20)
    t = report["turns"]
    report["summary"] = {"answers_ok": sum(x["answer_ok"] for x in t), "turns": len(t),
                         "max_wer": max(x["wer"] for x in t), "max_peak_dbfs": max(x["tts"]["peak_dbfs"] for x in t),
                         "median_voice_to_audio_ms": sorted(x["voice_to_audio_ms"] for x in t)[len(t) // 2]}
    (out_dir / "voice-e2e.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report["summary"]), report.get("playback_cancel_ms"), report.get("unavailable_output_rejected"))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
