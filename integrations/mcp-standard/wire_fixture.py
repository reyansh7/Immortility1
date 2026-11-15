"""Independent stdlib NDJSON peer for SDK interoperability tests. Never a user tool."""
import json
import sys

SCHEMA = {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"], "additionalProperties": False}

for line in sys.stdin.buffer:
    if len(line) > 16000:
        sys.exit(2)
    request = json.loads(line)
    if "id" not in request:
        continue
    method = request.get("method")
    reply = {"jsonrpc": "2.0", "id": request["id"]}
    if method == "initialize":
        reply["result"] = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "independent-wire-fixture", "version": "1.0"}}
    elif method == "tools/list":
        reply["result"] = {"tools": [{"name": "add", "description": "Untrusted fixture description", "inputSchema": SCHEMA}]}
    elif method == "tools/call":
        parameters = request.get("params", {})
        arguments = parameters.get("arguments", {})
        valid = parameters.get("name") == "add" and set(arguments) == {"a", "b"} and all(type(v) is int for v in arguments.values())
        reply["result"] = {"content": [{"type": "text", "text": str(arguments["a"] + arguments["b"]) if valid else "Invalid tool or arguments"}], "isError": not valid}
    elif method == "ping":
        reply["result"] = {}
    else:
        reply["error"] = {"code": -32601, "message": "Unsupported method"}
    sys.stdout.write(json.dumps(reply) + "\n")
    sys.stdout.flush()
