"""Tool-free chat goes straight to the admitted provider. Hermes stays the tool runtime."""

import json
from typing import Any, AsyncIterator

import httpx

from .config import Settings
from .contracts import BrokerError
from .dialogue import chat_system
from .ledger import fit_prompt
from .providers import ModelOffer, compatible_request


class DirectChat:
    def __init__(self, settings: Settings, offer: ModelOffer):
        self.settings = settings
        self.offer = offer
        self.usage: dict[str, Any] | None = None
        self.stopped = False
        self.spawn_ms = 0.0
        self.ready_ms = 0.0

    async def stop(self) -> None:
        self.stopped = True

    async def run(
        self, content: str, history: list[dict[str, str]], role: str | None = None
    ) -> AsyncIterator[str]:
        del role
        messages = fit_prompt(
            [
                {
                    "role": "system",
                    "content": chat_system(self.offer.provider, self.offer.model_id),
                },
                *history,
                {"role": "user", "content": content},
            ],
            [],
            12000,
        )
        payload = {
            "messages": messages,
            "stream": True,
            "max_tokens": 500,
            "stream_options": {"include_usage": True},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, read=40.0)) as client:
            request = compatible_request(client, self.settings, self.offer, payload)
            response = await client.send(request, stream=True)
            try:
                if response.status_code != 200:
                    code = "quota_exhausted" if response.status_code == 429 else "provider_rejected"
                    message = (
                        "Free quota exhausted. Retry later; no paid fallback attempted."
                        if response.status_code == 429
                        else "Provider rejected the request. No paid fallback attempted."
                    )
                    raise BrokerError(code, message, 503)
                async for line in response.aiter_lines():
                    if self.stopped:
                        break
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    usage = chunk.get("usage")
                    if isinstance(usage, dict):
                        self.usage = usage
                    if chunk.get("error"):
                        raise BrokerError(
                            "provider_stream_failed",
                            "Provider interrupted the response. No fallback attempted.",
                            503,
                        )
                    for choice in chunk.get("choices") or []:
                        if not isinstance(choice, dict):
                            continue
                        delta = choice.get("delta") or {}
                        text = delta.get("content")
                        if isinstance(text, str) and text:
                            yield text
            finally:
                await response.aclose()
