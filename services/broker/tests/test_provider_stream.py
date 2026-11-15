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


async def test_deadline_never_cancels_downstream_consumer_while_generator_is_suspended():
    import asyncio

    source = sse_data(httpx.Response(200, text="data: one\n\ndata: two\n\n"), time.time() + 0.02)
    try:
        assert await anext(source) == "one"
        # The old timeout spanning yield cancelled this unrelated consumer await.
        await asyncio.sleep(0.04)
        with pytest.raises(TimeoutError):
            await anext(source)
    finally:
        await source.aclose()


async def test_fragmented_multilingual_utf8_and_crlf_are_reassembled_exactly():
    class Bytes(httpx.AsyncByteStream):
        async def __aiter__(self):
            for byte in 'data: {"text":"日本語 λ"}\r\n\r\ndata: [DONE]\r\n\r\n'.encode():
                yield bytes([byte])

    frames = [
        value async for value in sse_data(httpx.Response(200, stream=Bytes()), time.time() + 2)
    ]
    assert json.loads(frames[0]) == {"text": "日本語 λ"}
    assert frames[-1] == "[DONE]"


async def test_invalid_utf8_is_rejected_instead_of_silently_replaced():
    with pytest.raises(BrokerError) as issue:
        _ = [
            value
            async for value in sse_data(
                httpx.Response(200, content=b'data: {"text":"\xff"}\n\n'), time.time() + 2
            )
        ]
    assert issue.value.diagnostic == "invalid_utf8"
    assert "text" not in issue.value.message
