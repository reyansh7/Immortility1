"""M2 local model route (Ollama on loopback): opt-in, $0, private, same broker authority."""

import json

import httpx
import pytest

from immortility_broker.app import apply_local_model_flag
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.providers import (
    PROVIDERS,
    ModelRegistry,
    ModelSelection,
    Requirements,
    compatible_request,
    free_tier,
)
from immortility_broker.store import Store


def registry(tmp_path, enabled=True, **keys):
    if enabled:
        (tmp_path / "local-model.json").write_text(
            json.dumps({"enabled": True, "model": "immortility-qwen3.5-4b"}), encoding="utf-8"
        )
    settings = Settings(_env_file=None, data_dir=tmp_path, openrouter_api_key="", **keys)
    apply_local_model_flag(settings)
    store = Store(tmp_path / "state.sqlite3")
    return ModelRegistry(store.db, settings), settings


def test_absent_flag_leaves_local_mode_closed(tmp_path):
    reg, settings = registry(tmp_path, enabled=False)
    assert not settings.local_model_enabled
    with pytest.raises(BrokerError, match="local_model_unavailable"):
        reg.choose(ModelSelection(mode="local_qwen"), Requirements())


def test_local_route_is_loopback_free_and_private(tmp_path):
    reg, settings = registry(tmp_path)
    offer = reg.choose(ModelSelection(mode="local_qwen"), Requirements(tools=True))
    assert offer.provider == "local" and offer.model_id == "immortility-qwen3.5-4b"
    assert free_tier("local", offer.model_id)
    assert PROVIDERS["local"].base_url.startswith("http://127.0.0.1:")
    assert "personal" in offer.privacy
    request = compatible_request(httpx.AsyncClient(), settings, offer, {"messages": [], "x": 1})
    assert request.url.host == "127.0.0.1" and request.url.port == 11434
    body = json.loads(request.content)
    assert "x" not in body and body["model"] == "immortility-qwen3.5-4b"
    assert body["reasoning_effort"] == "none"


def test_personal_tasks_prefer_local_even_when_cloud_keys_exist(tmp_path):
    reg, _ = registry(tmp_path, groq_api_key="fixture-groq", gemini_api_key="fixture-gemini")
    assert reg.choose(ModelSelection(), Requirements(task_class="FAST_CHAT")).provider == "local"
    public = reg.choose(ModelSelection(), Requirements(task_class="FAST_CHAT", privacy="public"))
    assert public.provider == "groq"


def test_local_context_limit_is_enforced(tmp_path):
    reg, _ = registry(tmp_path)
    with pytest.raises(BrokerError, match="local_model_unavailable"):
        reg.choose(ModelSelection(mode="local_qwen"), Requirements(context_tokens=9000))


def test_model_name_from_flag_is_validated(tmp_path):
    (tmp_path / "local-model.json").write_text(
        json.dumps({"enabled": True, "model": "http://evil.example/model"}), encoding="utf-8"
    )
    settings = Settings(_env_file=None, data_dir=tmp_path, openrouter_api_key="")
    apply_local_model_flag(settings)
    assert not settings.local_model_enabled


def test_direct_chat_streams_over_a_real_loopback_socket(tmp_path, monkeypatch):
    """K22: DirectChat used `async with client.send(...)`, which fails on real httpx."""
    import asyncio
    import socket
    import threading
    import time
    import types

    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse

    import immortility_broker.providers as providers
    from immortility_broker.direct_chat import DirectChat

    seen: list[dict] = []
    fake = FastAPI()

    @fake.post("/v1/chat/completions")
    async def completions(body: dict):
        seen.append(body)

        def stream():
            yield "data: " + json.dumps({"choices": [{"delta": {"content": "Hi "}}]}) + "\n\n"
            yield "data: " + json.dumps({"choices": [{"delta": {"content": "there."}}]}) + "\n\n"
            usage = {"prompt_tokens": 40, "completion_tokens": 3}
            yield "data: " + json.dumps({"choices": [], "usage": usage}) + "\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(fake, log_level="critical"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    try:
        while not server.started:
            time.sleep(0.02)
        local = providers.Provider("local", f"http://127.0.0.1:{port}/v1", "local_model_key", "")
        monkeypatch.setattr(
            providers, "PROVIDERS", types.MappingProxyType({**providers.PROVIDERS, "local": local})
        )
        reg, settings = registry(tmp_path)
        offer = reg.choose(ModelSelection(mode="local_qwen"), Requirements())
        chat = DirectChat(settings, offer)

        async def collect() -> str:
            return "".join([part async for part in chat.run("hello", [])])

        assert asyncio.run(collect()) == "Hi there."
        assert chat.usage == {"prompt_tokens": 40, "completion_tokens": 3}
        assert seen[0]["reasoning_effort"] == "none" and seen[0]["max_tokens"] == 500
    finally:
        server.should_exit = True
        thread.join(timeout=10)
