"""Bounded SSE event framing shared by compatible providers, without retries."""

import asyncio
import time
from collections.abc import AsyncIterator

import httpx

from .contracts import BrokerError


async def sse_data(response: httpx.Response, deadline: float) -> AsyncIterator[str]:
    parts: list[str] = []
    size = 0
    first = True
    async with asyncio.timeout(max(0, deadline - time.time())):
        async for line in response.aiter_lines():
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
