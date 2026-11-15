"""Offline warm arithmetic benchmark; no provider, files, network, or user data."""
import asyncio
import importlib.metadata
import json
import os
import statistics
import sys
import time
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    times = []
    start = time.perf_counter()
    parameters = StdioServerParameters(command=sys.executable, args=["-I", str(Path(__file__).with_name("arithmetic.py"))], env=dict(os.environ))
    async with Client(stdio_client(parameters), read_timeout_seconds=3, mode="legacy", cache=None) as client:
        await client.list_tools()
        cold_ms = (time.perf_counter() - start) * 1000
        for index in range(100):
            started = time.perf_counter()
            result = await client.call_tool("add", {"a": index, "b": 1})
            assert result.structured_content == {"result": index + 1} and not result.is_error
            times.append((time.perf_counter() - started) * 1000)
    print(json.dumps({"mode": "real local SDK stdio, no model", "sdk_version": importlib.metadata.version("mcp"), "n": 100, "success": 100, "initialize_and_list_ms": round(cold_ms, 2), "warm_p50_ms": round(statistics.median(times), 2), "warm_p95_ms": round(sorted(times)[94], 2), "model_calls": 0, "cloud_tokens": 0, "additional_ram_mib": None, "additional_vram_mib": None}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
