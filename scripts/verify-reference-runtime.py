"""Real broker -> RTX voice -> Windows speaker test. Fixed local text, no cloud or microphone."""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))


async def main() -> None:
    from immortility_broker.config import Settings
    from immortility_broker.store import Store
    from immortility_broker.voice import VoiceOptions, VoiceService

    with tempfile.TemporaryDirectory(prefix="runtime-", dir=ROOT / ".cache/reference-tts") as work:
        folder = Path(work)
        os.environ["IMMORTILITY_VOICE_DIR"] = str(folder / "unused-friend-profile")
        store = Store(folder / "state.db")
        voice = VoiceService(
            Settings(_env_file=None, data_dir=folder, reference_voice_enabled=True),
            store,
            AsyncMock(),
            AsyncMock(),
        )
        report = {"playbacks": [], "cloud_calls": 0, "microphone": False, "qwen": False}
        voice.reference.diagnostic_path = ROOT / ".cache/reference-tts/runtime-public-test.log"
        try:
            started = time.perf_counter()
            voice.apply_options(VoiceOptions(voice="reference", voice_output=True, volume=0.24))
            assert voice.reference_warm
            await asyncio.wait_for(voice.reference_warm, 120)
            if not voice.reference.ready:
                raise RuntimeError(voice.tts_error or "warmup failed")
            report["warmup_seconds"] = time.perf_counter() - started
            report["ready_metrics"] = dict(voice.reference.metrics)
            pid = voice.reference.process.pid
            for index in range(2):
                started = time.perf_counter()
                voice.note_assistant_text(
                    "local-fixed-test-" + str(index),
                    "Hi there. Tell me what I have to do, and I will do it for you.",
                    True,
                )
                first = None
                levels = []
                async with asyncio.timeout(60):
                    while voice.job and not voice.job.done():
                        if voice.level > 0:
                            levels.append(voice.level)
                            if first is None:
                                first = time.perf_counter() - started
                        await asyncio.sleep(0.005)
                    await voice.job
                assert levels and voice.level == 0 and voice.state == "IDLE", voice.tts_error
                assert voice.reference.process.pid == pid
                report["playbacks"].append(
                    {
                        "request_to_first_meter_ms": first * 1000,
                        "total_seconds": time.perf_counter() - started,
                        "peak_meter": max(levels),
                        "same_worker": True,
                    }
                )
            voice.note_assistant_text(
                "local-stop-test",
                "Stay calm. I have seen the problem, and I know how to solve it.",
                True,
            )
            async with asyncio.timeout(30):
                while voice.level <= 0:
                    if voice.job.done():
                        raise RuntimeError(voice.tts_error or "no audio")
                    await asyncio.sleep(0.005)
            process = voice.reference.process
            started = time.perf_counter()
            await voice.cancel()
            report["stop_ms"] = (time.perf_counter() - started) * 1000
            await asyncio.sleep(0.15)
            assert (
                voice.reference.process is None
                and process.returncode is not None
                and voice.level == 0
            )
            assert voice.reference_paused and voice.tts_state == "cold"
            report["worker_reaped"] = True
            report["meter_zero"] = True
            (ROOT / "data/audits/reference-tts-broker-runtime.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            print(json.dumps(report), flush=True)
        finally:
            await voice.cancel()
            store.db.close()


if __name__ == "__main__":
    asyncio.run(main())
