"""Offline SDK-vs-independent-peer probe. Prints only fixed test results."""
import asyncio
import os
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-I", str(Path(__file__).with_name("wire_fixture.py"))], env=dict(os.environ))
    async with Client(stdio_client(params), read_timeout_seconds=3, mode="legacy", cache=None) as client:
        tools = await client.list_tools()
        assert [tool.name for tool in tools.tools] == ["add"]
        result = await client.call_tool("add", {"a": 7, "b": 8})
        assert not result.is_error and result.content[0].text == "15"
        error = await client.session.call_tool("forbidden", {"a": 1, "b": 2})
        assert error.is_error
    print("Independent NDJSON initialize/list/call/error: PASS", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
