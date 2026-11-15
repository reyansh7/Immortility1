"""Reviewed local SDK server. No files, network, shell, sampling, or credentials."""
import json
import sys
import time

started = time.perf_counter()
from mcp.server import MCPServer
print("IMMORTILITY_MCP_TIMING " + json.dumps({"phase": "server_import", "milliseconds": round((time.perf_counter()-started)*1000, 3)}), file=sys.stderr, flush=True)

started = time.perf_counter()
server = MCPServer("immortility-arithmetic")


@server.tool()
def add(a: int, b: int) -> int:
    """Add two bounded integers."""
    if type(a) is not int or type(b) is not int or abs(a) > 10**9 or abs(b) > 10**9:
        raise ValueError("Integer out of bounds")
    return a + b


if __name__ == "__main__":
    print("IMMORTILITY_MCP_TIMING " + json.dumps({"phase": "server_construct", "milliseconds": round((time.perf_counter()-started)*1000, 3)}), file=sys.stderr, flush=True)
    server.run(transport="stdio")
