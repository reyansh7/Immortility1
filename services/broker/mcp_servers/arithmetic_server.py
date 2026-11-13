"""Local MCP stdio server. It can add two integers. It exposes shell and refuses it."""

import json
import sys


def read_message() -> dict | None:
    header = b""
    while b"\r\n\r\n" not in header:
        byte = sys.stdin.buffer.read(1)
        if not byte:
            return None
        header += byte
        if len(header) > 8192:
            return None
    length = 0
    for line in header.decode("ascii", "replace").split("\r\n"):
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
    if length <= 0 or length > 65536:
        return None
    return json.loads(sys.stdin.buffer.read(length))


def write_message(payload: dict) -> None:
    body = json.dumps(payload).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    sys.stdout.buffer.flush()


def main() -> None:
    while True:
        message = read_message()
        if message is None:
            return
        method = message.get("method")
        identifier = message.get("id")
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "immortility-arithmetic", "version": "0.1.0"},
                    },
                }
            )
        elif method == "tools/list":
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "result": {
                        "tools": [
                            {
                                "name": "add",
                                "description": "Add two integers.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "a": {"type": "integer"},
                                        "b": {"type": "integer"},
                                    },
                                    "required": ["a", "b"],
                                },
                            },
                            {
                                "name": "shell",
                                "description": "Not authorized.",
                                "inputSchema": {"type": "object"},
                            },
                        ]
                    },
                }
            )
        elif method == "tools/call":
            params = message.get("params") or {}
            if params.get("name") != "add":
                write_message(
                    {
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "error": {"code": -32601, "message": "denied"},
                    }
                )
                continue
            arguments = params.get("arguments") or {}
            total = int(arguments["a"]) + int(arguments["b"])
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "result": {
                        "content": [{"type": "text", "text": str(total)}],
                        "isError": False,
                    },
                }
            )
        elif identifier is not None:
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "error": {"code": -32601, "message": "unknown"},
                }
            )


if __name__ == "__main__":
    main()
