"""Real Windows playback/cancel check, fixed public text, isolated settings and no microphone."""

import asyncio
import argparse
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
    from immortility_broker.voice import VoiceService, VoiceOptions
    from immortility_broker.infernal import PRESETS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refinement", action="store_true")
    parser.add_argument("--ab", action="store_true")
    args = parser.parse_args()
    bases = ("piper_northern", "kokoro_george", "kokoro_fable")
    jobs = [
        VoiceOptions(voice="infernal", infernal_base=base, volume=0.24, speed=0.94)
        for base in bases
    ]
    if args.refinement:
        jobs = [
            VoiceOptions(voice="infernal", volume=0.24, **PRESETS[preset])
            for preset in ("cinematic_v2", "ultron_inspired", "ultron_inspired")
        ]
    if args.ab:
        candidates = json.loads((ROOT / "config/infernal-refinement.json").read_text())[
            "candidates"
        ]
        jobs = [
            VoiceOptions(voice="infernal", volume=0.24, **candidate)
            for candidate in candidates.values()
        ]

    with tempfile.TemporaryDirectory(prefix="playback-", dir=ROOT / ".cache/infernal") as work:
        folder = Path(work)
        os.environ["IMMORTILITY_VOICE_DIR"] = str(folder / "private-unused")
        store = Store(folder / "state.db")
        admit, cancel_task = AsyncMock(), AsyncMock()
        voice = VoiceService(
            Settings(_env_file=None, data_dir=folder, infernal_voice_enabled=True),
            store,
            admit,
            cancel_task,
        )
        voice.models = Path.home() / "AppData/Local/Immortility/models"
        report = {
            "playbacks": [],
            "cancel_checks": [],
            "cloud_calls": 0,
            "microphone_opened": False,
        }
        try:
            original_pid = None
            for options in jobs:
                base = options.infernal_base
                started = time.perf_counter()
                voice.preview(options)
                levels = []
                first_audio = None
                async with asyncio.timeout(120):
                    while voice.job and not voice.job.done():
                        if voice.level > 0:
                            levels.append(voice.level)
                            if first_audio is None:
                                first_audio = time.perf_counter() - started
                        await asyncio.sleep(0.01)
                    if voice.job:
                        await voice.job
                if voice.error or voice.tts_error or not levels:
                    raise RuntimeError(
                        "Real playback did not report nonzero audio energy: "
                        + str(voice.error or voice.tts_error)
                    )
                assert voice.infernal_process is not None
                pid = voice.infernal_process.pid
                if original_pid is not None:
                    assert pid == original_pid
                original_pid = pid
                assert voice.level == 0 and voice.state == "IDLE"
                report["playbacks"].append(
                    {
                        "base": base,
                        "preset": options.voice_preset,
                        "robotic_intensity": options.robotic_intensity,
                        "delivery": options.delivery,
                        "first_audio_ms": round((first_audio or 0) * 1000, 2),
                        "total_ms": round((time.perf_counter() - started) * 1000, 2),
                        "meter_frames_observed": len(levels),
                        "peak_meter": max(levels),
                        "output_buffer_ms": voice.latency.get("audio_output_buffer"),
                        "same_warm_worker": True,
                    }
                )
                print("Completed real Windows playback:", base, flush=True)
            # Interrupt the tested voice while truly playing, then during a fresh load.
            voice.preview(jobs[-1])
            async with asyncio.timeout(30):
                while voice.level <= 0:
                    if voice.job and voice.job.done():
                        raise RuntimeError("Preview ended without playback")
                    await asyncio.sleep(0.01)
            playing = voice.infernal_process
            started = time.perf_counter()
            await voice.cancel()
            assert playing is not None and playing.returncode is not None
            assert voice.infernal_process is None and voice.level == 0 and voice.tts_state == "cold"
            report["cancel_checks"].append(
                {
                    "phase": "actual_playback",
                    "stop_ms": round((time.perf_counter() - started) * 1000, 3),
                    "process_reaped": True,
                    "meter_zero": True,
                }
            )
            # Stop a fresh owned process before first audio: no model-load delay should block Stop.
            voice.preview(jobs[-1])
            async with asyncio.timeout(10):
                while voice.infernal_process is None:
                    await asyncio.sleep(0.005)
            loading = voice.infernal_process
            started = time.perf_counter()
            await voice.cancel()
            assert loading is not None and loading.returncode is not None and voice.level == 0
            report["cancel_checks"].append(
                {
                    "phase": "fresh_worker_loading",
                    "stop_ms": round((time.perf_counter() - started) * 1000, 3),
                    "process_reaped": True,
                    "meter_zero": True,
                }
            )
            admit.assert_not_called()
            cancel_task.assert_not_called()
            name = (
                "infernal-refinement-windows.json"
                if args.refinement
                else "infernal-windows-playback.json"
            )
            if args.ab:
                name = "infernal-refinement-v3-windows.json"
            (ROOT / "data/audits" / name).write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report), flush=True)
        finally:
            await voice.cancel()
            store.db.close()


if __name__ == "__main__":
    asyncio.run(main())
