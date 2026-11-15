"""Keyless Windows owned-tree Stop timing after both synthetic workers are ready."""

import asyncio
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.process_owner import reap, spawn_owned


async def main():
    samples, peaks, process_counts = [], [], []
    child = "import time;print('ready',flush=True);time.sleep(60)"
    parent = "import subprocess,sys,time;p=subprocess.Popen([sys.executable,'-u','-c',sys.argv[1]],stdout=subprocess.PIPE);assert p.stdout.readline().strip()==b'ready';print('ready',flush=True);time.sleep(60)"
    for _ in range(30):
        process, owner = await spawn_owned(sys.executable, "-u", "-c", parent, child, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            assert (await asyncio.wait_for(process.stdout.readline(), 5)).strip() == b"ready"
            count = owner.active_processes()
            # A Windows venv can retain launcher processes for both workers.
            assert count >= 2
            process_counts.append(count)
            peaks.append(owner.peak_committed_bytes())
            started = time.perf_counter()
            await reap(process, owner)
            samples.append(1000 * (time.perf_counter() - started))
            assert process.returncode is not None
        finally:
            await reap(process, owner)
    report = {"scope": "native Windows Job with ready synthetic parent and child, including venv launchers; Stop includes whole-job quiescence; not a UI or SDK latency measurement", "n": len(samples), "observed_process_counts": sorted(set(process_counts)), "p50_ms": round(statistics.median(samples), 3), "p95_ms": round(sorted(samples)[math.ceil(len(samples)*.95)-1], 3), "max_ms": round(max(samples), 3), "max_peak_job_commit_bytes": max(peaks), "cloud_calls": 0, "cloud_tokens": 0, "idle_cpu": None, "idle_ram": None}
    (ROOT / "docs/implementation/PROCESS_STOP_BENCHMARK.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
