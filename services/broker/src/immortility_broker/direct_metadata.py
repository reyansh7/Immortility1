"""One explicit read-only model-access check; never grants billing eligibility."""

import asyncio
import hashlib
import json
from typing import Any

import httpx

from .contracts import BrokerError

GROQ_CANDIDATE = "openai/gpt-oss-120b"


async def groq_model_metadata(client: httpx.AsyncClient, credential: str) -> dict[str, Any]:
    if not credential or len(credential) > 2500 or "\n" in credential or "\r" in credential:
        raise BrokerError("missing_credential", "A protected Groq credential is required.", 403)

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Ambiguous metadata")
            result[key] = value
        return result

    try:
        async with (
            asyncio.timeout(10),
            client.stream(
                "GET",
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": "Bearer " + credential, "Accept": "application/json"},
                follow_redirects=False,
                timeout=8,
            ) as response,
        ):
            response.raise_for_status()
            data = bytearray()
            async for part in response.aiter_bytes():
                if len(data) + len(part) > 65536:
                    raise ValueError("Metadata limit")
                data.extend(part)
        rows = json.loads(data.decode("utf-8"), object_pairs_hook=unique)["data"]
        if not isinstance(rows, list) or len(rows) > 256:
            raise ValueError("Invalid model listing")
        matches = [row for row in rows if isinstance(row, dict) and row.get("id") == GROQ_CANDIDATE]
        if len(matches) != 1:
            raise BrokerError(
                "model_unavailable",
                "The candidate was not uniquely listed for this credential.",
                403,
            )
        row = matches[0]
        active = row.get("active")
        context = row.get("context_window")
        return {
            "provider": "groq",
            "model": GROQ_CANDIDATE,
            "listed_for_credential": True,
            "reported_active": active if type(active) is bool else None,
            "reported_context_tokens": context
            if type(context) is int and 1024 <= context <= 2000000
            else None,
            "credential_identity": hashlib.sha256(credential.encode()).hexdigest(),
            "billing_verified": False,
            "quota_verified": False,
            "production_enabled": False,
            "status": "BLOCKED: account-plan, current limits and live tool qualification still required",
            "authenticated_metadata_requests": 1,
            "model_requests": 0,
        }
    except BrokerError:
        raise
    except (TimeoutError, httpx.HTTPError, ValueError, TypeError, KeyError, RecursionError):
        raise BrokerError(
            "metadata_unavailable",
            "Groq model metadata could not be verified; no inference sent.",
            503,
        ) from None
