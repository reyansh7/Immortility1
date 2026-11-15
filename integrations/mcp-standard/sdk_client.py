"""Fixed SDK 2.2 bridge; its JSON control pipe is NOT the MCP transport.

The SDK speaks standard NDJSON to the fixed sibling arithmetic server.
Run only under the broker-owned, environment-filtered, pinned process.
"""
import asyncio
import importlib.metadata
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path


async def main():
    def phase(value):
        print("IMMORTILITY_MCP_STAGE " + value, file=sys.stderr, flush=True)
    def timing(value, start):
        print("IMMORTILITY_MCP_TIMING " + json.dumps({"phase": value, "milliseconds": round((time.perf_counter()-start)*1000, 3)}), file=sys.stderr, flush=True)
    phase("import")
    start = time.perf_counter()
    if importlib.metadata.version("mcp") != "2.2.0":
        raise RuntimeError("Unreviewed SDK version")
    timing("dependency_metadata", start)
    start = time.perf_counter()
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters, stdio_client
    timing("client_import", start)
    phase("input")

    request = json.loads(sys.stdin.buffer.readline(4097))
    if request.get("operation") not in {"discover", "add"}:
        raise ValueError("Forbidden operation")
    parameters = StdioServerParameters(command=sys.executable, args=["-I", str(Path(__file__).with_name("arithmetic.py"))], cwd=os.getcwd(), env=dict(os.environ))
    @asynccontextmanager
    async def measured_stdio():
        started = time.perf_counter()
        async with stdio_client(parameters) as streams:
            timing("server_spawn", started)
            try:
                yield streams
            finally:
                started = time.perf_counter()
        timing("stdio_cleanup", started)
    phase("initialize")
    # Initialization includes a second cold Python/SDK import. Paired cold-start
    # probes exhausted the old inner 3s timer while the broker still allowed a
    # 10s operation. Use that existing deadline envelope; no retry or extension
    # of the broker deadline is permitted, and warm latency is measured separately.
    start = time.perf_counter()
    connection = Client(measured_stdio(), read_timeout_seconds=8, cache=None, mode="legacy")
    timing("client_construct", start)
    start = time.perf_counter()
    async with connection as client:
        timing("handshake", start)
        phase("ready")
        start = time.perf_counter()
        tools = await client.list_tools()
        timing("discovery", start)
        phase("listed")
        if [tool.name for tool in tools.tools] != ["add"]:
            raise ValueError("Unexpected server inventory")
        if request["operation"] == "discover":
            result = {"tools": [tool.model_dump(mode="json") for tool in tools.tools]}
        else:
            a, b = request.get("a"), request.get("b")
            if type(a) is not int or type(b) is not int or abs(a) > 10**9 or abs(b) > 10**9:
                raise ValueError("Invalid input")
            start = time.perf_counter()
            response = await client.call_tool("add", {"a": a, "b": b})
            timing("first_invocation", start)
            if response.is_error:
                raise RuntimeError("Server rejected call")
            result = {"result": response.structured_content}
        phase("closing")
        start = time.perf_counter()
    timing("client_cleanup", start)
    phase("completed")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        if os.environ.get("IMMORTILITY_MCP_DIAGNOSTICS") == "synthetic-only":
            import traceback
            traceback.print_exception(error, file=sys.stderr)
        print('{"error":"mcp_failed"}', flush=True)
        sys.exit(1)
