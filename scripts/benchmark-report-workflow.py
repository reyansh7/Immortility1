"""Serial native Hermes report corpus; synthetic sources/drafts, no keys or uploads."""
import argparse
import asyncio
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"services/broker/src"))
from immortility_broker import hermes as hermes_module

spec = importlib.util.spec_from_file_location("report_smoke", ROOT/"scripts/smoke-research-report.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


async def sample():
    started, cpu = time.perf_counter(), time.process_time()
    phases, jobs = [], []
    def mark(name):
        phases.append({"phase": name, "elapsed_ms": round((time.perf_counter()-started)*1000,3)})

    original_create, original_send = smoke.create_app, hermes_module.Hermes.send
    original_frames, original_reap = hermes_module.Hermes.frames, hermes_module.reap
    original_transport = smoke.httpx.MockTransport

    def create(*args, **kwargs):
        mark("broker_initialization_begin")
        app = original_create(*args, **kwargs)
        mark("broker_initialization_end")
        registry = app.state.engine.gateway.registrations
        for name in ("public.research.v1", "report.create.v1"):
            entry = registry[name]
            async def measured(arguments, entry=entry, name=name):
                mark(name+"_begin")
                try:
                    return await entry.execute(arguments)
                finally:
                    mark(name+"_end")
            registry[name] = replace(entry, execute=measured)
        return app

    async def send(instance, method, params):
        if method in {"session.create", "prompt.submit"}:
            mark(method)
        return await original_send(instance, method, params)

    async def frames(instance):
        async for frame in original_frames(instance):
            envelope = frame.get("params", {})
            if envelope.get("type") == "session.info" and not envelope.get("payload", {}).get("lazy"):
                mark("hermes_and_MCP_ready")
            yield frame

    async def reap(process, owner):
        mark("hermes_cleanup_begin")
        if owner is not None:
            try:
                stats = owner.statistics()
                if stats:
                    jobs.append(stats)
            except OSError:
                pass
        try:
            return await original_reap(process, owner)
        finally:
            mark("hermes_cleanup_end")

    class Transport(original_transport):
        async def handle_async_request(self, request):
            mark("fixture_"+request.method+"_begin")
            try:
                return await super().handle_async_request(request)
            finally:
                mark("fixture_"+request.method+"_end")

    smoke.create_app = create
    hermes_module.Hermes.send, hermes_module.Hermes.frames = send, frames
    hermes_module.reap, smoke.httpx.MockTransport = reap, Transport
    try:
        await smoke.main(public_sources=False, live=False)
        result = json.loads((ROOT/"docs/implementation/M2_REPORT_OFFLINE_SMOKE.json").read_text())
        path = Path(result["directory"]).resolve()
        assert path.is_relative_to((ROOT/".cache/report-workflows").resolve())
        receipt = json.loads((path/"receipt.json").read_text())
        mark("completion_verified")
        return {"status":result["status"], "total_ms":round((time.perf_counter()-started)*1000,3),
                "legacy_smoke_seconds":result["seconds"], "broker_cpu_seconds":round(time.process_time()-cpu,6),
                "phases":phases, "hermes_job_resources":jobs,
                "report_worker_phases_ms":receipt.get("worker_phases_ms",{}),
                "report_worker_resources":receipt.get("worker_resources",{}), "cloud_calls":0}
    finally:
        smoke.create_app = original_create
        hermes_module.Hermes.send, hermes_module.Hermes.frames = original_send, original_frames
        hermes_module.reap, smoke.httpx.MockTransport = original_reap, original_transport


async def main(samples):
    out=ROOT/"docs/implementation"
    before=out/"M3_HARDENING_REPORT_BEFORE.json"
    if not before.exists():
        shutil.copyfile(out/"M2_REPORT_OFFLINE_SMOKE.json",before)
    rows=[]
    for _ in range(samples):
        rows.append(await sample())
    ordered=sorted(r["total_ms"] for r in rows)
    record={"classification":"Serial native Hermes/MCP/broker/report integration; synthetic sources and drafting",
        "samples":rows, "n":len(rows), "p50_ms":ordered[len(rows)//2],
        "p95_nearest_rank_ms":ordered[-1],
        "percentile_limit":"n=5..10; descriptive sample statistic, not a population latency guarantee",
        "cold_warm":"Fresh Hermes/MCP/report workers per task; shared warm broker imports after first sample; OS caches uncontrolled",
        "resource_units":"Owned Windows job CPU seconds and peak private commit bytes, not physical RSS/VRAM",
        "cloud_calls":0,"source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['scripts/smoke-research-report.py','integrations/artifacts/report_worker.py']}}
    (out/"M3_REPORT_PHASE_BENCHMARK.json").write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({"samples":len(rows),"successes":sum(r["status"]=="passed" for r in rows),"p50_ms":record["p50_ms"],"p95_nearest_rank_ms":record["p95_nearest_rank_ms"],"cloud_calls":0}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples',type=int,choices=range(5,11),default=5)
    asyncio.run(main(parser.parse_args().samples))
