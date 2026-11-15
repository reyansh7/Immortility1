import json
import time

import httpx
import pytest

from immortility_broker.contracts import BrokerError
from immortility_broker.provider_stream import sse_data


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
async def test_sse_frames_join_data_lines_and_ignore_comments_and_metadata(newline):
    text = newline.join(
        [
            "\ufeff: heartbeat",
            "event: message",
            'data: {"choices":',
            "data: []}",
            "",
            ": keepalive",
            "data:",
            "",
            "data: [DONE]",
            "",
            "",
        ]
    )
    response = httpx.Response(200, text=text)
    frames = [data async for data in sse_data(response, time.time() + 2)]
    assert json.loads(frames[0]) == {"choices": []}
    assert frames[1] == "[DONE]" and len(frames) == 2


@pytest.mark.parametrize(
    "body,category",
    [("data: {}", "truncated_sse"), ("data: " + "x" * 128001 + "\n\n", "sse_limit")],
)
async def test_partial_and_oversized_frames_fail_closed(body, category):
    with pytest.raises(BrokerError) as captured:
        _ = [data async for data in sse_data(httpx.Response(200, text=body), time.time() + 2)]
    assert captured.value.diagnostic == category


async def test_expired_stream_deadline_does_not_wait_for_network():
    class Waiting(httpx.AsyncByteStream):
        async def __aiter__(self):
            import asyncio

            await asyncio.sleep(60)
            yield b"data: never\n\n"

    with pytest.raises(TimeoutError):
        _ = [
            data async for data in sse_data(httpx.Response(200, stream=Waiting()), time.time() - 1)
        ]
