"""Real local model/fixture and optional speaker interruption check. Never captures audio."""

import argparse
import asyncio
import json
import sys
import tempfile
import time
import wave
from contextlib import ExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.config import Settings
from immortility_broker.store import Store
from immortility_broker.voice import VoiceOptions, VoiceService
from immortility_broker.voice_models import ready

PHRASE = "The local voice system is ready. Please open the blue folder and read the morning report."


async def main(play: bool) -> None:
    models = Path.home() / "AppData/Local/Immortility/models"
    if not ready(models):
        raise SystemExit("Prepare local voice models first: python scripts/prepare-voice.py")
    report = {"schema_version": "1.0", "microphone_opened": False, "cloud_calls": 0}

    async def forbidden(*args):
        raise AssertionError("This check must never invoke an agent or cloud API")

    with tempfile.TemporaryDirectory(prefix="immortility-voice-check-") as directory, ExitStack() as cleanup:
        settings = Settings(_env_file=None, data_dir=Path(directory))
        store = Store(settings.data_dir / "db")
        cleanup.callback(store.db.close)
        voice = VoiceService(settings, store, forbidden, forbidden)
        voice.models = models
        fixture = ROOT / "tests/fixtures/voice-english.wav"
        fixture.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        await voice.worker("render", text=PHRASE, voice="ljspeech", path=str(fixture))
        report["fixture_render_ms"] = round((time.monotonic() - started) * 1000, 1)
        with wave.open(str(fixture), "rb") as audio:
            report["fixture_seconds"] = audio.getnframes() / audio.getframerate()
        started = time.monotonic()
        result = await voice.worker("transcribe", path=str(fixture), language="en", stt_device="cpu")
        report["stt_cpu_ms"] = round((time.monotonic() - started) * 1000, 1)
        expected = PHRASE.lower().replace(".", "").split()
        actual = str(result["text"]).lower().replace(".", "").replace(",", "").split()
        # Levenshtein word error rate, rather than an exact punctuation assertion.
        row = list(range(len(actual) + 1))
        for i, word in enumerate(expected, 1):
            nxt = [i]
            for j, other in enumerate(actual, 1):
                nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (word != other)))
            row = nxt
        report["fixture_word_error_rate"] = row[-1] / len(expected)
        assert report["fixture_word_error_rate"] <= 0.2, "Fixture transcription exceeded 20% WER"
        devices = await voice.devices()
        report["input_device_count"] = sum(d["input"] for d in devices["devices"])
        report["output_device_count"] = sum(d["output"] for d in devices["devices"])
        # Actual unavailable-device path: output only, never touches a microphone.
        try:
            await voice.worker("speak", text="Device test.", output_device=999)
        except Exception:
            report["unavailable_output_rejected"] = True
        else:
            raise AssertionError("Invalid output device was accepted")
        if play:
            session = store.session()["id"]
            from immortility_broker.contracts import TaskRequest
            task, _ = store.create(TaskRequest(session_id=session,request_id="voice-check",content="Synthetic speaker test",cloud_consent=True))
            for state in ["queued", "running", "verifying"]:
                store.state(task["task_id"], state)
            store.state(task["task_id"], "succeeded", result={"text": PHRASE * 5})
            voice.speak_task(task["task_id"], VoiceOptions(volume=0.3))
            deadline = time.monotonic() + 40
            while "tts_first_audio" not in voice.latency and time.monotonic() < deadline:
                if voice.job.done():
                    raise AssertionError("Playback failed before opening speaker")
                await asyncio.sleep(0.05)
            assert "tts_first_audio" in voice.latency, "No audio output opened"
            await asyncio.sleep(0.5)
            report["tts_first_audio_ms"] = round(voice.latency["tts_first_audio"], 1)
            started = time.monotonic()
            await voice.cancel()
            report["speaker_stop_ms"] = round((time.monotonic() - started) * 1000, 1)
            assert voice.process is None and voice.state == "CANCELLED"
            report["speaker_interruption"] = "verified process reaped"
            # A complete second voice utterance exercises draining/normal cleanup.
            started = time.monotonic()
            await voice.worker("speak", text="Local speech playback is complete.", voice="joe", volume=0.3)
            report["joe_playback_ms"] = round((time.monotonic() - started) * 1000, 1)
        store.db.close()
    output = ROOT / "data/benchmarks/voice-local.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--play", action="store_true", help="Play synthetic speech at 30% volume and verify immediate Stop")
    asyncio.run(main(parser.parse_args().play))
