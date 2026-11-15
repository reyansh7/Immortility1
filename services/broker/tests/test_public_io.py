import asyncio
import json
import socket
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.public_fetch import MAX_BYTES, PublicBackend, fetch_json, validate_url
from immortility_broker.request_limits import BodyLimitMiddleware


class Pool:
    def __init__(self, chunks, status=200, encoding=b"identity", content_type=b"application/json"):
        self.status = status
        self.headers = [(b"content-type", content_type), (b"content-encoding", encoding)]
        self.chunks = chunks
        self.closed = False

    @asynccontextmanager
    async def stream(self, *args, **kwargs):
        try:
            yield self
        finally:
            self.closed = True

    async def aiter_stream(self):
        for chunk in self.chunks:
            yield chunk


@pytest.mark.parametrize(
    "url",
    [
        "http://en.wikipedia.org/x",
        "https://localhost/x",
        "https://127.0.0.1",
        "https://en.wikipedia.org:444/x",
        "https://user@en.wikipedia.org/x",
        "https://en.wikipedia.org/x#hidden",
    ],
)
def test_public_scope_is_exact(url):
    with pytest.raises(BrokerError, match="tool_denied"):
        validate_url(url)


@pytest.mark.parametrize(
    "pool,code",
    [
        (Pool([b"x" * MAX_BYTES, b"x"]), "output_limit"),
        (Pool([b"{}"], status=302), "source_unavailable"),
        (Pool([b"compressed"], encoding=b"gzip"), "source_unavailable"),
        (Pool([b"[]"], content_type=b"text/html"), "source_unavailable"),
        (Pool([b"not json"]), "source_unavailable"),
    ],
)
async def test_sources_are_bounded_and_closed(pool, code):
    with pytest.raises(BrokerError, match=code):
        await fetch_json("https://en.wikipedia.org/x", pool)
    assert pool.closed


async def test_dns_is_pinned_to_a_validated_public_ip(monkeypatch):
    backend = PublicBackend()
    connection = AsyncMock(return_value=object())
    backend.backend.connect_tcp = connection
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(
        loop, "getaddrinfo", AsyncMock(return_value=[(socket.AF_INET, 1, 6, "", ("1.1.1.1", 443))])
    )
    await backend.connect_tcp("en.wikipedia.org", 443)
    assert connection.call_args.args == ("1.1.1.1", 443)
    monkeypatch.setattr(
        loop,
        "getaddrinfo",
        AsyncMock(
            return_value=[
                (socket.AF_INET, 1, 6, "", ("127.0.0.1", 443)),
                (socket.AF_INET, 1, 6, "", ("1.1.1.1", 443)),
            ]
        ),
    )
    with pytest.raises(BrokerError, match="tool_denied"):
        await backend.connect_tcp("en.wikipedia.org", 443)
    assert connection.await_count == 1


async def test_chunked_body_limit_does_not_trust_content_length_or_echo_secrets():
    downstream = AsyncMock()
    receive = AsyncMock(
        side_effect=[
            {"type": "http.request", "body": b"FAKE_SECRET_CANARY", "more_body": True},
            {"type": "http.request", "body": b"X" * 20, "more_body": False},
        ]
    )
    send = AsyncMock()
    await BodyLimitMiddleware(downstream, maximum=24)(
        {"type": "http", "headers": [(b"content-length", b"1")]}, receive, send
    )
    downstream.assert_not_called()
    assert send.call_args_list[0].args[0]["status"] == 413
    body = send.call_args_list[1].args[0]["body"]
    assert json.loads(body)["error"]["code"] == "too_large"
    assert b"CANARY" not in body


@pytest.mark.parametrize(
    "provider,credential",
    [
        ("openrouter", "SYNTHETIC_ROUTER_CANARY_123456789"),
        ("gemini", "SYNTHETIC_GEMINI_CANARY_123456789"),
        ("groq", "SYNTHETIC_GROQ_CANARY_123456789"),
        ("nvidia", "SYNTHETIC_NVIDIA_CANARY_123456789"),
        (None, "sk-" + "SYNTHETIC_CANARY_" * 3),
        (None, "ghp_" + "SYNTHETICCANARY" * 3),
        (None, "AKIA" + "A" * 16),
        (None, "-----BEGIN OPENSSH PRIVATE KEY-----"),
    ],
)
def test_secret_input_never_reaches_task_research_or_model(
    tmp_path, monkeypatch, provider, credential
):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        web_research_enabled=True,
        **({provider + "_api_key": credential} if provider else {}),
    )
    fetch = AsyncMock(side_effect=AssertionError("Secret input reached research"))
    monkeypatch.setattr("immortility_broker.app.research_page_async", fetch)
    calls = []

    def factory(*args):
        calls.append(args)
        raise AssertionError("Secret input reached Hermes")

    token = "synthetic-broker-token-" + "x" * 32
    headers = {"Authorization": "Bearer " + token}
    with TestClient(create_app(settings, token, factory=factory)) as client:
        session = client.post("/v1/sessions", headers=headers).json()["id"]
        response = client.post(
            "/v1/tasks",
            headers=headers,
            json={
                "session_id": session,
                "request_id": "secret-input",
                "content": "Research this credential " + credential,
                "cloud_consent": True,
            },
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "secret_egress_denied"
        assert credential not in response.text
        assert client.get(f"/v1/sessions/{session}/tasks", headers=headers).json() == []
        assert calls == []
        fetch.assert_not_called()
