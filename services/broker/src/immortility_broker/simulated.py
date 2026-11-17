"""Test-only model fixture. It never calls a provider and is not a live model."""

import json
import re
from typing import Any

SIMULATED_MODEL = "immortility-fixture"
SIMULATED_PROVIDER = "simulated"


class SimulatedRoute:
    provider = SIMULATED_PROVIDER
    model_id = SIMULATED_MODEL
    route_id = "simulated/immortility-fixture"
    qualification = "offline"


class SimulatedUpstream:
    """Enough of an HTTP response for the existing provider stream parser."""

    def __init__(self, pieces: list[tuple[float, bytes]]) -> None:
        self.status_code = 200
        self.headers: dict[str, str] = {}
        self.pieces = pieces
        self._closed = False

    async def aiter_bytes(self, chunk_size: int = 4096):
        del chunk_size
        for delay, block in self.pieces:
            if self._closed:
                break
            if delay:
                import asyncio

                await asyncio.sleep(delay)
            yield block

    async def aclose(self) -> None:
        self._closed = True


def _current_turn(messages: list[dict[str, Any]]) -> tuple[str, int]:
    """Use the latest SIM tag, and count only tool results after that request."""
    start = 0
    tag = "SIM:chat"
    for index, message in enumerate(messages):
        content = message.get("content")
        if not isinstance(content, str):
            continue
        found = re.findall(r"SIM:[a-z]+", content)
        if found:
            start = index
            tag = found[-1]
    done = sum(message.get("role") == "tool" for message in messages[start:])
    return tag, done


def _chunk(
    delta: dict[str, Any], finish: str | None = None, *, usage: dict[str, int] | None = None
) -> bytes:
    body: dict[str, Any] = {
        "id": "sim",
        "object": "chat.completion.chunk",
        "model": SIMULATED_MODEL,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    if usage is not None:
        body["usage"] = usage
    return ("data: " + json.dumps(body) + "\n\n").encode()


def _tool(capability: str, arguments: dict[str, Any], ident: str) -> list[tuple[float, bytes]]:
    payload = json.dumps({"capability": capability, "arguments": arguments}, separators=(",", ":"))
    usage = {"prompt_tokens": 24, "completion_tokens": 12, "total_tokens": 36}
    return [
        (
            0,
            _chunk(
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": ident,
                            "type": "function",
                            "function": {"name": "execute", "arguments": payload},
                        }
                    ]
                }
            ),
        ),
        (0, _chunk({}, "tool_calls", usage=usage)),
        (0, b"data: [DONE]\n\n"),
    ]


def _text(text: str, *, repeat: int = 1, delay: float = 0) -> list[tuple[float, bytes]]:
    usage = {"prompt_tokens": 16, "completion_tokens": 8, "total_tokens": 24}
    pieces = [(delay if index == 0 else 0, _chunk({"content": text})) for index in range(repeat)]
    pieces.append((0, _chunk({}, "stop", usage=usage)))
    pieces.append((0, b"data: [DONE]\n\n"))
    return pieces


def _latest_user(messages: list[dict[str, Any]]) -> str:
    text = ""
    for message in messages:
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            text = message["content"]
    return text


def _milestone(text: str) -> bool:
    folded = text.casefold()
    return "247" in folded and "36" in folded and "time" in folded and "project" in folded


def scripted_pieces(messages: list[dict[str, Any]]) -> list[tuple[float, bytes]]:
    """Choose a fixture from the latest SIM tag. Older transcript text cannot redirect it."""
    latest = _latest_user(messages)
    if _milestone(latest):
        start = 0
        for index, message in enumerate(messages):
            if message.get("role") == "user" and message.get("content") == latest:
                start = index
        done = sum(item.get("role") == "tool" for item in messages[start:])
        if done == 0:
            return _tool("clock.now.v1", {}, "sim-clock")
        if done == 1:
            return _tool("arithmetic.multiply.v1", {"a": 247, "b": 36}, "sim-multiply")
        if done == 2:
            return _tool("project.outline.v1", {}, "sim-outline")
        return _text("Verified. 247 × 36 = 8892. The clock and project inspection ran.")
    tag, done = _current_turn(messages)
    if tag == "SIM:malformed" and done == 0:
        payload = {"error": {"code": "server_error", "message": "simulated malformed output"}}
        return [(0, ("data: " + json.dumps(payload) + "\n\n").encode())]
    if tag == "SIM:shell" and done == 0:
        return _tool("shell.exec", {"command": "denied-canary"}, "sim-shell")
    if tag == "SIM:browser" and done == 0:
        return _tool("browser.navigate", {"url": "http://127.0.0.1/denied"}, "sim-browser")
    if tag == "SIM:computer" and done == 0:
        return _tool("computer_use.click", {"x": 0, "y": 0}, "sim-computer")
    if tag == "SIM:yolo" and done == 0:
        return _tool("yolo", {}, "sim-yolo")
    if tag == "SIM:mcp" and done == 0:
        return _tool("mcp.install", {"name": "denied"}, "sim-mcp")
    if tag == "SIM:unknown" and done == 0:
        return _tool("not.a.tool", {}, "sim-unknown")
    if tag == "SIM:bad" and done == 0:
        return _tool("arithmetic.multiply.v1", {}, "sim-bad")
    if tag == "SIM:path" and done == 0:
        return _tool(
            "project.read.v1",
            {"path": "../outside", "start_line": 1, "lines": 1},
            "sim-path",
        )
    if tag == "SIM:slow" and done == 0:
        return _text("Simulated slow reply.", delay=20)
    if tag == "SIM:approve":
        if done == 0:
            return _tool("clock.now.v1", {}, "sim-approve")
        return _text("Simulated approved clock.")
    if tag in {"SIM:clock", "SIM:steps", "SIM:inject"}:
        if done == 0:
            return _tool("clock.now.v1", {}, "sim-clock")
        if tag == "SIM:steps" and done == 1:
            return _tool("arithmetic.multiply.v1", {"a": 247, "b": 36}, "sim-multiply")
        if tag == "SIM:inject":
            return _text("Simulated safe reply.")
        if tag == "SIM:steps":
            return _text("Simulated steps finished. 8892.")
        return _text("Simulated clock checked.")
    if tag == "SIM:dup":
        return _text("Simulated duplicate.", repeat=2)
    return _text("Simulated reply. This is not a cloud model.")
