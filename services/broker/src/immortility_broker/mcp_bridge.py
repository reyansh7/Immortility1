"""Broker-owned client for one local arithmetic MCP server.

The official MCP SDK is not imported. This client speaks Content-Length JSON-RPC
for initialize, tools/list, and tools/call, then the broker allowlist decides
what may run. The server path is fixed. External servers are not started.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .contracts import BrokerError

AUTHORIZED = frozenset({"add"})
SERVER = Path(__file__).resolve().parents[2] / "mcp_servers" / "arithmetic_server.py"


def _frame(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload).encode()
    return f"Content-Length: {len(body)}\r\n\r\n".encode() + body


def _read_frame(stream: bytes) -> tuple[dict[str, Any], bytes]:
    marker = stream.find(b"\r\n\r\n")
    if marker < 0:
        raise BrokerError("mcp_failed", "The local MCP server stopped.", 503)
    header = stream[:marker].decode("ascii", "replace")
    length = 0
    for line in header.split("\r\n"):
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
    start = marker + 4
    if length <= 0 or len(stream) < start + length:
        raise BrokerError("mcp_failed", "The local MCP server stopped.", 503)
    return json.loads(stream[start : start + length]), stream[start + length :]


def _run(messages: list[dict[str, Any]], timeout: float = 5) -> list[dict[str, Any]]:
    if not SERVER.is_file():
        raise BrokerError("mcp_unavailable", "The local MCP server is not installed.", 503)
    try:
        completed = subprocess.run(
            [sys.executable, str(SERVER)],
            input=b"".join(_frame(message) for message in messages),
            capture_output=True,
            timeout=timeout,
            shell=False,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as error:
        raise BrokerError("timeout", "The local MCP server timed out.") from error
    if completed.returncode not in {0, None} and not completed.stdout:
        raise BrokerError("mcp_failed", "The local MCP server stopped.", 503)
    rest = completed.stdout
    replies: list[dict[str, Any]] = []
    while rest.strip():
        message, rest = _read_frame(rest)
        replies.append(message)
    return replies


def discover(enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"tools": [], "external": False}
    replies = _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "immortility", "version": "0.1.0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
    )
    listed = next(item for item in replies if item.get("id") == 2)["result"]["tools"]
    return {
        "tools": [
            {"name": tool["name"], "authorized": tool["name"] in AUTHORIZED} for tool in listed
        ],
        "external": False,
    }


def call_add(enabled: bool, name: str, first: int, second: int) -> dict[str, str]:
    if not enabled or name not in AUTHORIZED:
        raise BrokerError("tool_denied", "That MCP tool is not authorized.", 403)
    replies = _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "immortility", "version": "0.1.0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "add", "arguments": {"a": first, "b": second}},
            },
        ]
    )
    result = next(item for item in replies if item.get("id") == 3)["result"]
    text = str(result["content"][0]["text"])
    return {"name": "add", "result": text}
