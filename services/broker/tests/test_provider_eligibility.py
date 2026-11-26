"""Fail-closed optional routing and official quota fixtures; no account access."""

import asyncio
import json

import httpx
import pytest

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError, TaskRequest
from immortility_broker.policy import MODEL
from immortility_broker.providers import (
    ModelRegistry,
    ModelSelection,
    Requirements,
    verify_free_quota,
)
from immortility_broker.store import Store
from test_inference_grants import grant
from test_providers import offer


@pytest.fixture
def registry(tmp_path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        openrouter_api_key="fixture-openrouter",
        groq_api_key="fixture-groq",
    )
    store = Store(tmp_path / "state.sqlite3")
    yield ModelRegistry(store.db, settings, clock=lambda: 1000.0), store
    store.db.close()


def test_stored_key_does_not_enable_optional_fallback(registry):
    value, _ = registry
    assert Settings(_env_file=None).openrouter_fallback_enabled is False
    value.settings.openrouter_fallback_enabled = False
    route = value.models[MODEL]
    assert value.rejection(route, Requirements()) == "optional_fallback_disabled"
    chosen = value.choose(ModelSelection(), Requirements())
    assert chosen.provider == "groq" and chosen.model_id == "openai/gpt-oss-120b"
    with pytest.raises(BrokerError, match="route_unavailable"):
        value.choose(ModelSelection(mode="manual_cloud", route_id=MODEL), Requirements())
    assert "optional fallback disabled" in next(
        p["status"] for p in value.view()["providers"] if p["id"] == "openrouter"
    )


def test_eligible_direct_routes_precede_opted_in_fallback_without_changing_manual_pin(registry):
    value, store = registry
    value.settings.openrouter_fallback_enabled = True
    # A qualified direct route is preferred even when the optional fallback has
    # favorable observations. This does not activate real production offers.
    direct = offer(value, "groq")
    value.models[direct.route_id] = direct
    for index in range(3):
        task, _ = store.create(
            TaskRequest(
                session_id=store.session()["id"],
                request_id="fallback-" + str(index),
                content="Public fixture",
                cloud_consent=True,
            )
        )
        value.observe(value.models[MODEL], task["task_id"], "FAST_CHAT", True, True, 1, 1)
    assert value.choose(ModelSelection(), Requirements()).provider == "groq"
    assert (
        value.choose(ModelSelection(mode="manual_cloud", route_id=MODEL), Requirements()).route_id
        == MODEL
    )


@pytest.mark.parametrize(
    "quota",
    [
        None,
        {},
        {"limit": 50, "used": 0, "remaining": True},
        {"limit": 50, "used": -1, "remaining": 51},
        {"limit": 50, "used": 0, "remaining": 50.0},
        {"limit": 50, "used": 0, "remaining": 40},
    ],
)
async def test_unknown_or_ambiguous_quota_is_not_free_access(quota):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "data": {
                        "free_model_daily_requests": quota,
                        "limit_remaining": 100,
                        "is_free_tier": True,
                        "label": "PRIVATE_ACCOUNT_CANARY",
                    }
                },
            )
        )
    ) as client:
        with pytest.raises(BrokerError, match="quota_unverified") as captured:
            await verify_free_quota(client, "FIXTURE_KEY_CANARY")
    assert "CANARY" not in captured.value.message


@pytest.mark.parametrize(
    "status,body",
    [
        (401, b"PRIVATE_ACCOUNT_CANARY"),
        (302, b""),
        (200, b"\xff"),
        (200, b"{" + b" " * 32768),
        (
            200,
            b'{"data":{},"data":{"free_model_daily_requests":{"limit":50,"used":0,"remaining":50}}}',
        ),
    ],
)
async def test_bad_account_response_never_leaks_or_redirects(status, body):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            status, content=body, headers={"location": "https://untrusted.invalid/"}
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), follow_redirects=True
    ) as client:
        with pytest.raises(BrokerError, match="quota_unverified") as captured:
            await verify_free_quota(client, "FIXTURE_KEY_CANARY")
    assert len(requests) == 1 and "CANARY" not in captured.value.message


async def test_quota_checked_fresh_and_credential_bound_without_cache():
    observed = []

    def respond(request):
        observed.append(request.headers["authorization"])
        return httpx.Response(
            200,
            json={"data": {"free_model_daily_requests": {"limit": 50, "used": 48, "remaining": 2}}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await verify_free_quota(client, "first", minimum_requests=2) == 2
        assert await verify_free_quota(client, "rotated") == 2
        with pytest.raises(BrokerError, match="quota_exhausted"):
            await verify_free_quota(client, "rotated", minimum_requests=3)
    assert observed == ["Bearer first", "Bearer rotated", "Bearer rotated"]


async def test_quota_cancellation_propagates():
    async def respond(_):
        raise asyncio.CancelledError

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(asyncio.CancelledError):
            await verify_free_quota(client, "fixture")


async def test_missing_account_proof_prevents_post_and_releases_reserved_tokens(tmp_path):
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path == "/api/v1/models":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        assert request.url.path == "/api/v1/key" and request.method == "GET"
        return httpx.Response(
            200, json={"data": {"label": "PRIVATE_ACCOUNT_CANARY", "limit_remaining": 100}}
        )

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, client=upstream)
    try:
        task_id, key = grant(app, "quota-missing")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + key},
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": "Public arithmetic"}],
                },
            )
        assert response.status_code == 403 and "CANARY" not in response.text
        assert [request.method for request in requests] == ["GET", "GET"]
        summary = app.state.store.ledger.summary(task_id)
        assert (
            summary["charged_tokens"]
            == summary["dispatch_attempts"]
            == summary["pending_reservations"]
            == 0
        )
        assert summary["not_sent_calls"] == 1
        assert "CANARY" not in json.dumps(app.state.store.events(task_id))
    finally:
        await upstream.aclose()
        app.state.store.db.close()
