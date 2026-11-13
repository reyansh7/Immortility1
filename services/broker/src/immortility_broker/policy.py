from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from .contracts import BrokerError

MODEL = "openrouter/free"


def route_model(requested: str | None) -> str:
    """Only the verified free router is selectable. Stored Gemini, Groq and NVIDIA keys are not routes."""
    if requested not in {None, "", MODEL}:
        raise BrokerError("inference_denied", "Only the verified free router is enabled.", 403)
    return MODEL


def allow_tool(name: str, arguments: dict[str, Any]) -> None:
    # No filesystem, capture, subprocess, MCP, or other tool dispatcher exists in P1.
    raise BrokerError("tool_denied", "All agent tools are disabled in Phase 1.", 403)


def free_model(model: str, pricing: dict[str, Any]) -> None:
    if model != MODEL or not {"prompt", "completion"}.issubset(pricing):
        raise BrokerError("price_unverified", "Only the verified free router is enabled.")
    try:
        if any(not Decimal(str(p)).is_finite() or Decimal(str(p)) != 0 for p in pricing.values()):
            raise ValueError
    except (InvalidOperation, ValueError):
        raise BrokerError(
            "price_unverified", "Unknown or nonzero model price; request blocked."
        ) from None


async def verify_catalog(client: httpx.AsyncClient) -> None:
    try:
        response = await client.get("https://openrouter.ai/api/v1/models", timeout=10)
        response.raise_for_status()
        rows = response.json()["data"]
        row = next(r for r in rows if r["id"] == MODEL)
        free_model(row["id"], row["pricing"])
    except BrokerError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, StopIteration, TypeError):
        raise BrokerError(
            "catalog_unavailable", "Cannot verify live $0 pricing. No inference sent."
        ) from None


def inference_payload(body: dict[str, Any]) -> dict[str, Any]:
    # Rebuild an allowlisted request: no paid fallbacks, plugins, search, audio, images, or tools.
    if body.get("model") != MODEL or body.get("tools") or body.get("functions"):
        raise BrokerError(
            "inference_denied", "Model or tool selection violates Phase 1 policy.", 403
        )
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) > 64:
        raise BrokerError("inference_denied", "Invalid conversation.", 403)
    clean = []
    for message in messages:
        if (
            not isinstance(message, dict)
            or message.get("role") not in {"system", "user", "assistant"}
            or not isinstance(message.get("content"), str)
            or message.get("tool_calls")
        ):
            raise BrokerError("inference_denied", "Only plain text conversations are enabled.", 403)
        clean.append({"role": message["role"], "content": message["content"]})
    if sum(len(m["content"]) for m in clean) > 120000:
        raise BrokerError("context_limit", "Conversation is too long; start a new session.")
    return {
        "model": MODEL,
        "messages": clean,
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_tokens": 2048,
        "provider": {"max_price": {"prompt": 0, "completion": 0}},
    }
