"""Bounded SSE event framing shared by compatible providers, without retries."""

import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import cast

import httpx

from .contracts import BrokerError


def provider_error_category(error: object) -> str:
    code = error.get("code") if isinstance(error, dict) else None
    return (
        code
        if isinstance(code, str)
        and code
        in {
            "context_length_exceeded",
            "invalid_request_error",
            "rate_limit_exceeded",
            "insufficient_quota",
            "model_not_found",
            "server_error",
            "content_filter",
        }
        else "provider_error"
    )


@dataclass
class StreamCounters:
    started: float = field(default_factory=time.perf_counter)
    raw_bytes: int = 0
    read_chunks: int = 0
    events: int = 0


async def _bounded_lines(
    response: httpx.Response, deadline: float, counters: StreamCounters
) -> AsyncGenerator[str, None]:
    """No cancellation scope spans a yield into downstream code (PEP 789)."""
    expires = asyncio.get_running_loop().time() + max(0, deadline - time.time())
    # HTTPX implements aiter_bytes as an async generator with aclose().
    source = cast(AsyncGenerator[bytes, None], response.aiter_bytes(chunk_size=4096))
    line = bytearray()
    skip_lf = False
    try:
        while True:
            try:
                async with asyncio.timeout_at(expires):
                    block = await anext(source)
            except StopAsyncIteration:
                break
            counters.read_chunks += 1
            counters.raw_bytes += len(block)
            if counters.raw_bytes > 8000000:
                raise BrokerError(
                    "provider_stream_failed",
                    "Provider transport exceeds its bound.",
                    503,
                    diagnostic="sse_limit",
                )
            for byte in block:
                if skip_lf and byte == 10:
                    skip_lf = False
                    continue
                skip_lf = False
                if byte in {10, 13}:
                    if asyncio.get_running_loop().time() >= expires:
                        raise TimeoutError
                    yield line.decode("utf-8", errors="strict")
                    line.clear()
                    skip_lf = byte == 13
                else:
                    line.append(byte)
                    if len(line) > 128000:
                        raise BrokerError(
                            "provider_stream_failed",
                            "Provider event exceeds its bound.",
                            503,
                            diagnostic="sse_limit",
                        )
        if line:
            yield line.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise BrokerError(
            "provider_stream_failed",
            "Provider stream has invalid UTF-8.",
            503,
            diagnostic="invalid_utf8",
        ) from None
    finally:
        await source.aclose()


async def sse_data(
    response: httpx.Response, deadline: float, counters: StreamCounters | None = None
) -> AsyncGenerator[str, None]:
    parts: list[str] = []
    size = 0
    first = True
    lines = _bounded_lines(
        response, deadline, counters if counters is not None else StreamCounters()
    )
    try:
        async for line in lines:
            if first:
                line, first = line.removeprefix("\ufeff"), False
            if len(line.encode()) > 128000:
                raise BrokerError(
                    "provider_stream_failed",
                    "Provider event exceeds its limit.",
                    503,
                    diagnostic="sse_limit",
                )
            if not line:
                if parts:
                    data = "\n".join(parts)
                    parts, size = [], 0
                    if data.strip():
                        if counters is not None:
                            counters.events += 1
                        yield data.strip()
                continue
            if line.startswith(":"):
                continue
            field, _, value = line.partition(":")
            if field == "data":
                value = value.removeprefix(" ")
                size += len(value.encode()) + 1
                if size > 128000:
                    raise BrokerError(
                        "provider_stream_failed",
                        "Provider event exceeds its limit.",
                        503,
                        diagnostic="sse_limit",
                    )
                parts.append(value)
        if parts:
            raise BrokerError(
                "provider_stream_failed",
                "Provider event was interrupted.",
                503,
                diagnostic="truncated_sse",
            )
    finally:
        await lines.aclose()
