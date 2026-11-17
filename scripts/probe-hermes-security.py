"""Unauthorized access against the real Hermes 0.23.2 gateway. No model call."""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from immortility_broker.config import Settings
from immortility_broker.hermes_gateway import GatewaySupervisor


async def main() -> int:
    data = Path(os.environ["LOCALAPPDATA"]) / "Immortility" / "hermes-0232" / "security-probe"
    data.mkdir(parents=True, exist_ok=True)
    try:
        httpx.get("http://127.0.0.1:8642/health", timeout=2)
    except httpx.HTTPError:
        pass
    else:
        print(json.dumps({"blocked": "port 8642 is already in use"}), flush=True)
        return 2
    supervisor = GatewaySupervisor(
        Settings(_env_file=None, data_dir=data), "http://127.0.0.1:9"
    )
    await supervisor.start()
    results = []
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
            for method, path in (
                ("GET", "/health"),
                ("GET", "/v1/capabilities"),
                ("POST", "/v1/runs"),
            ):
                response = await client.request(method, supervisor.url + path)
                results.append({"method": method, "path": path, "status": response.status_code})
    finally:
        await supervisor.stop()
    protected = [item for item in results if item["path"] != "/health"]
    ok = all(item["status"] in {401, 403} for item in protected)
    print(
        json.dumps(
            {
                "gateway_state": supervisor.state,
                "cold_start_ms": supervisor.cold_start_ms,
                "results": results,
                "unauthorized_blocked": ok,
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if ok and supervisor.state == "stopped" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
