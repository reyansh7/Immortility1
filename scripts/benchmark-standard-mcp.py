"""Reproducible keyless MCP benchmark. No accounts or user content are contacted."""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))

from immortility_broker.process_owner import reap, spawn_owned
from immortility_broker.standard_mcp import reviewed_runtime, sdk_request


async def main():
    python = reviewed_runtime()
    env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}}
    process, owner = await spawn_owned(str(python), "-I", str(ROOT / "integrations/mcp-standard/benchmark.py"), env=env, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 15)
        if process.returncode != 0:
            raise RuntimeError("Synthetic benchmark failed; no performance claim recorded")
        result = json.loads(output)
    finally:
        await reap(process, owner)
    cold = []
    for _ in range(3):
        start = time.perf_counter()
        assert await sdk_request("add", 7, 8, enabled=True) == {"result": {"result": 15}}
        cold.append(round((time.perf_counter()-start)*1000, 2))
    result["broker_cold_call_ms_n3"] = cold
    result["scope"] = "Arithmetic only; not the full B1 task corpus or a quality comparison"
    destination = ROOT / "docs/implementation/MCP_BENCHMARK.json"
    destination.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
