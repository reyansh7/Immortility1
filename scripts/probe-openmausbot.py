"""Opt-in P0 source-protocol audit only. Never connects to a desktop, dispatches or pairs."""

import argparse
import asyncio
import hashlib
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


async def probe(source: Path, runs: int) -> dict:
    lock = json.loads((ROOT / "infra/security/upstream-audit.json").read_text())
    for relative, expected in lock["openmausbot_protocol_files"].items():
        actual = hashlib.sha256((source / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(
                "Audited source checksum mismatch; inspect the source before running it."
            )
    guard = ROOT / ".cache/p0-rebaseline/deny-network.mjs"
    guard.parent.mkdir(parents=True, exist_ok=True)
    guard.write_text(
        "globalThis.fetch = async () => { throw new Error('Network disabled during protocol-only audit'); };\n"
    )
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper()
        in {
            "SYSTEMROOT",
            "WINDIR",
            "PATH",
            "TEMP",
            "TMP",
            "COMSPEC",
            "PATHEXT",
            "USERPROFILE",
            "LOCALAPPDATA",
            "APPDATA",
        }
    }
    env["OPENMAUSBOT_URL"] = "http://127.0.0.1:1"
    measurements = []
    tools = []
    for _ in range(runs):
        started = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            "node",
            "--import",
            guard.as_uri(),
            "--experimental-strip-types",
            str(source / "scripts/mcp-server.ts"),
            env=env,
            cwd=source,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=512000,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert process.stdin and process.stdout

        async def request(identifier: int, method: str, params: dict) -> dict:
            process.stdin.write(
                (
                    json.dumps(
                        {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}
                    )
                    + "\n"
                ).encode()
            )
            await process.stdin.drain()
            line = await asyncio.wait_for(process.stdout.readline(), 10)
            if not line:
                raise RuntimeError(
                    "Source MCP exited before returning a protocol frame; check runtime compatibility."
                )
            response = json.loads(line)
            assert response["id"] == identifier
            return response

        try:
            initialized = await request(
                1,
                "initialize",
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "Immortility protocol-only audit", "version": "0.1.0"},
                },
            )
            init_ms = (time.perf_counter() - started) * 1000
            started = time.perf_counter()
            catalogue = await request(2, "tools/list", {})
            catalogue_ms = (time.perf_counter() - started) * 1000
            tools = catalogue["result"]["tools"]
            assert tools and all("inputSchema" in tool for tool in tools)
            assert (await request(3, "immortility/unknown", {}))["error"]["code"] == -32601
            # One fixed process-metadata command. No tokens, command lines or account content.
            memory_process = await asyncio.create_subprocess_exec(
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-Process -Id {process.pid} | Select-Object WorkingSet64,PrivateMemorySize64,CPU | ConvertTo-Json -Compress",
                stdout=asyncio.subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output, _ = await asyncio.wait_for(memory_process.communicate(), 10)
            memory = json.loads(output)
            measurements.append(
                {
                    "initialize_ms": init_ms,
                    "tools_list_ms": catalogue_ms,
                    "working_set_mb": memory["WorkingSet64"] / 1024**2,
                    "private_mb": memory["PrivateMemorySize64"] / 1024**2,
                    "process_cpu_seconds": memory["CPU"],
                }
            )
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()
                raise
        assert process.returncode == 0
    return {
        "schema_version": "1.0",
        "scope": "Official source MCP initialize/catalogue only; NOT installed desktop or team execution",
        "source_revision": lock["openmausbot_revision"],
        "runs": runs,
        "host_node_version": subprocess.check_output(
            ["node", "--version"], text=True, creationflags=subprocess.CREATE_NO_WINDOW
        ).strip(),
        "upstream_required_node": ">=24; this source-only compatibility probe does not override it",
        "server_info": initialized["result"]["serverInfo"],
        "initialize_median_ms": statistics.median(m["initialize_ms"] for m in measurements),
        "tools_list_median_ms": statistics.median(m["tools_list_ms"] for m in measurements),
        "working_set_median_mb": statistics.median(m["working_set_mb"] for m in measurements),
        "tools": [
            {
                "name": tool["name"],
                "read_only_hint": tool.get("annotations", {}).get("readOnlyHint", False),
            }
            for tool in tools
        ],
        "measurements": measurements,
        "http_calls": 0,
        "dispatches": 0,
        "provider_calls": 0,
        "credentials_loaded": False,
        "all_processes_reaped": True,
        "desktop_windows_cua_browser_reliability": "BLOCKED: application absent; policy interception not established",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-audit",
        type=Path,
        default=ROOT / ".cache/p0-rebaseline/upstream/milind-soni--OpenMausBot",
    )
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.runs <= 10:
        parser.error("Choose 1–10 protocol-only samples.")
    result = asyncio.run(probe(args.source_audit.resolve(), args.runs))
    output = ROOT / "data/audits/openmausbot-protocol.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
