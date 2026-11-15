"""Serial, keyless SDK phase/resource measurements; no persistent product worker."""
import argparse
import asyncio
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))
from immortility_broker.contracts import BrokerError
from immortility_broker.process_owner import reap, spawn_owned
from immortility_broker.standard_mcp import SdkProbe, reviewed_runtime, sdk_request


def distribution(values):
    ordered = sorted(values)
    return {
        "n": len(values),
        "p50_ms": round(statistics.median(values), 3),
        "p95_nearest_rank_ms": round(ordered[math.ceil(len(ordered)*0.95)-1], 3),
        "max_ms": round(max(values), 3),
        "p95_note": "Descriptive nearest-rank statistic; small sample, not a service guarantee.",
    }


async def main(samples):
    rows = []
    for index in range(samples):
        probe = SdkProbe()
        broker_cpu = time.process_time()
        operation = "discover" if index % 2 else "add"
        try:
            result = await sdk_request(operation, 7, 8, enabled=True, probe=probe)
            assert result == {"result": {"result": 15}} if operation == "add" else [t["name"] for t in result["tools"]] == ["add"]
        except BrokerError as error:
            probe.status = "failed"
            probe.mark("failure_delivered")
            # Never retain arbitrary exception strings or worker stderr.
            failure = error.code
        else:
            failure = None
        row = asdict(probe)
        row.pop("started")
        row.update(sample=index+1, operation=operation, error_code=failure,
                   broker_cpu_seconds=round(time.process_time()-broker_cpu, 6))
        rows.append(row)
        print(json.dumps({"sample": index+1, "status": probe.status, "total_ms": probe.phases_ms.get("cleanup_finished")}), flush=True)

    # Same reviewed SDK/server, one transient connection. Never retained after benchmark.
    python = reviewed_runtime()
    env = {k:v for k,v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}}
    began = time.perf_counter()
    process, owner = await spawn_owned(str(python), "-I", str(ROOT/"integrations/mcp-standard/benchmark.py"), env=env,
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 15)
        if process.returncode != 0:
            raise RuntimeError("Warm SDK benchmark failed; no warm performance claim")
        warm = json.loads(output)
        warm["owned_job"] = owner.statistics()
        warm["whole_worker_ms"] = round((time.perf_counter()-began)*1000,3)
    finally:
        await reap(process, owner)

    record = {
        "classification": "Local fixed SDK only; serial samples; no cloud calls or credentials",
        "production_deadline_seconds": 10,
        "cold_definition": "Fresh client/server process pair per sample; first sample separately identified; OS filesystem caches not flushed or controlled",
        "warm_definition": "100 arithmetic invocations in one transient SDK connection; not process startup",
        "samples": rows,
        "fresh_pair_total": distribution([r["phases_ms"]["cleanup_finished"] for r in rows]),
        "successes": sum(r["status"] == "passed" for r in rows),
        "warm": warm,
        "resource_units": {"cpu_seconds":"Cumulative Windows owned-job CPU, includes exited children", "peak_job_commit_bytes":"Peak private committed job memory; not RSS or VRAM"},
        "persistent_worker_enabled": False,
        "metadata_cache_enabled": False,
        "cloud_calls": 0,
    }
    path = ROOT/"docs/implementation/M3_SDK_PHASE_BENCHMARK.json"
    path.write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"evidence":str(path.relative_to(ROOT)),"successes":record["successes"],"samples":samples,"fresh_pair_total":record["fresh_pair_total"]}))
    return 0 if record["successes"] == samples else 1


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, choices=range(5,21), default=10)
    raise SystemExit(asyncio.run(main(parser.parse_args().samples)))
