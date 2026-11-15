"""Explicit official current-key response for deterministic transport fixtures."""

import httpx


def free_account_response(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert str(request.url) == "https://openrouter.ai/api/v1/key"
    assert request.headers.get("authorization", "").startswith("Bearer ")
    return httpx.Response(
        200,
        json={
            "data": {
                "free_model_daily_requests": {
                    "limit": 50,
                    "used": 0,
                    "remaining": 50,
                }
            }
        },
    )
