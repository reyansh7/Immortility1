"""Fixed reviewed MCP server: no native OS tools, provider keys or arbitrary URLs."""

import json
import os
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from mcp.server import MCPServer

server = MCPServer("immortility-broker")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Redirect denied")


@server.tool()
def execute(capability: str, arguments: dict) -> str:
    """Submit a proposed operation to the broker; this tool grants no permission."""
    from urllib.parse import urlsplit

    base = os.environ["IMMORTILITY_BROKER_URL"]
    parsed = urlsplit(base)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or not parsed.port
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Local endpoint denied")
    data = json.dumps({"capability": capability, "arguments": arguments}, allow_nan=False).encode()
    if len(data) > 16000:
        raise ValueError("Proposal exceeds limit")
    request = Request(
        base.rstrip("/") + "/inference/v1/capabilities/call",
        data=data,
        headers={
            "Authorization": "Bearer " + os.environ["IMMORTILITY_TASK_TOKEN"],
            "Content-Type": "application/json",
        },
    )
    try:
        timeout = 35 if capability in {"public.research.v1", "report.create.v1"} else 15
        with build_opener(ProxyHandler({}), NoRedirect()).open(
            request, timeout=timeout
        ) as response:
            body = response.read(64001)
            if len(body) > 64000:
                raise ValueError("Output limit")
            # Text-only avoids duplicating the same result in structuredContent.
            return json.dumps(json.loads(body), separators=(",", ":"))
    except Exception:
        # No exception/response body (which could contain credentials) is forwarded.
        raise ValueError("Broker denied or could not complete this operation") from None


if __name__ == "__main__":
    server.run(transport="stdio")
