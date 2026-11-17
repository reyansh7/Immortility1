import asyncio
import json

import httpx
import pytest

from immortility_broker.contracts import BrokerError
from immortility_broker.direct_metadata import GROQ_CANDIDATE, groq_model_metadata


async def test_one_official_metadata_get_does_not_imply_account_eligibility():
    requests = []

    def respond(request):
        requests.append(request)
        assert (
            str(request.url) == "https://api.groq.com/openai/v1/models" and request.method == "GET"
        )
        assert request.headers["authorization"] == "Bearer PRIVATE_KEY_CANARY"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": GROQ_CANDIDATE,
                        "active": True,
                        "context_window": 131072,
                        "private_account": "PRIVATE_RESPONSE_CANARY",
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await groq_model_metadata(client, "PRIVATE_KEY_CANARY")
    assert len(requests) == 1 and result["reported_context_tokens"] == 131072
    assert (
        not result["billing_verified"]
        and not result["quota_verified"]
        and not result["production_enabled"]
    )
    assert "CANARY" not in json.dumps(result)


@pytest.mark.parametrize(
    "status,body",
    [
        (401, b"PRIVATE_RESPONSE_CANARY"),
        (302, b""),
        (200, b"\xff"),
        (200, b"{" + b" " * 65536),
        (200, b'{"data":[],"data":[]}'),
    ],
)
async def test_metadata_errors_are_bounded_redacted_and_never_follow_redirects(status, body):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            status, content=body, headers={"location": "https://untrusted.invalid"}
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), follow_redirects=True
    ) as client:
        with pytest.raises(BrokerError, match="metadata_unavailable") as captured:
            await groq_model_metadata(client, "PRIVATE_KEY_CANARY")
    assert len(requests) == 1 and "CANARY" not in captured.value.message


async def test_metadata_missing_key_and_missing_model_fail_without_dispatch():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"data": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(BrokerError, match="missing_credential"):
            await groq_model_metadata(client, "")
        assert not requests
        with pytest.raises(BrokerError, match="model_unavailable"):
            await groq_model_metadata(client, "fixture")
    assert len(requests) == 1


async def test_metadata_cancellation_is_not_converted_to_eligibility():
    async def respond(_):
        raise asyncio.CancelledError

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(asyncio.CancelledError):
            await groq_model_metadata(client, "fixture")
