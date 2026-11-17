"""Offline provider protocols and deterministic routing; no billing/account claims."""

import json
import sqlite3
from dataclasses import replace

import httpx
import pytest
from pydantic import SecretStr

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError, TaskRequest
from immortility_broker.ledger import Ledger
from immortility_broker.policy import MODEL
from immortility_broker.providers import (
    PROVIDERS,
    ModelOffer,
    ModelRegistry,
    ModelSelection,
    Requirements,
    compatible_request,
    credential_identity,
    decide_route,
    route_class,
    task_class,
    verify_dispatch,
)
from immortility_broker.store import Store
from test_workspace import AUTH, TOKEN


@pytest.fixture
def registry(tmp_path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        openrouter_fallback_enabled=True,
        openrouter_api_key=SecretStr("fixture-openrouter"),
        groq_api_key=SecretStr("fixture-groq"),
        gemini_api_key=SecretStr("fixture-gemini"),
        nvidia_api_key=SecretStr("fixture-nvidia"),
    )
    store = Store(tmp_path / "state.sqlite3")
    value = ModelRegistry(store.db, settings, clock=lambda: 1000.0)
    yield value, store
    store.db.close()


def offer(registry, provider, **overrides):
    values = dict(
        route_id=provider + "/fixture-model",
        provider=provider,
        model_id="fixture-model",
        context_tokens=32768,
        tools_qualified=True,
        structured_qualified=True,
        qualification="offline",
        privacy=("public", "personal"),
        available=True,
        zero_price_until=2000.0,
        account_until=2000.0,
        credential_identity=credential_identity(registry.settings, provider),
    )
    values.update(overrides)
    return ModelOffer(**values)


def test_model_hub_explains_provider_specific_missing_evidence_without_exposing_credentials(
    registry,
):
    value, _ = registry
    view = value.view()
    statuses = {provider["id"]: provider["status"] for provider in view["providers"]}
    assert "free-tier allowlist openai/gpt-oss-120b" in statuses["groq"]
    assert "free-tier allowlist gemini-3.5-flash" in statuses["gemini"]
    assert "free prototype allowlist nvidia/nemotron-3-ultra-550b-a55b" in statuses["nvidia"]
    assert "fresh preflight" in statuses["openrouter"]
    routed = {item["task_class"]: item for item in view["routing"]}
    assert routed["DEEP_REASONING"]["model_id"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert routed["DEEP_REASONING"]["admitted"] is False
    assert routed["FAST_CHAT"]["provider"] == "groq"
    assert all("fixture-" + provider not in json.dumps(view) for provider in PROVIDERS)


@pytest.mark.parametrize("provider", ["groq", "gemini", "nvidia", "openrouter"])
async def test_one_compatible_adapter_uses_only_its_bound_credential_and_endpoint(
    registry, provider
):
    registry, _ = registry
    route = offer(registry, provider)
    captured = []

    def upstream(request):
        captured.append(request)
        assert str(request.url) == PROVIDERS[provider].base_url + "/chat/completions"
        assert request.headers["Authorization"] == "Bearer fixture-" + provider
        body = json.loads(request.content)
        assert body["model"] == "fixture-model" and body["n"] == 1
        assert "private_option" not in body and "plugins" not in body and "api_key" not in body
        assert ("provider" in body) == (provider == "openrouter")
        return httpx.Response(
            200,
            text='data: {"choices":[{"delta":{"content":"fixture"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n',
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
        request = compatible_request(
            client,
            registry.settings,
            route,
            {
                "messages": [{"role": "user", "content": "Public fixture"}],
                "max_tokens": 128,
                "stream": True,
                "plugins": [{"id": "web"}],
                "private_option": "blocked",
            },
        )
        response = await client.send(request)
        assert response.status_code == 200
    assert len(captured) == 1
    assert "fixture-" not in json.dumps(registry.view())


@pytest.mark.parametrize("provider", ["groq", "gemini", "nvidia"])
async def test_advertisement_or_key_cannot_prove_free_account_dispatch(registry, provider):
    registry, _ = registry

    def never(_):
        pytest.fail("No provider request permitted without an account billing verifier")

    async with httpx.AsyncClient(transport=httpx.MockTransport(never)) as client:
        with pytest.raises(BrokerError, match="price_unverified"):
            await verify_dispatch(client, offer(registry, provider))


async def test_allowlisted_free_models_skip_zero_price_proof_and_paid_models_stay_closed(registry):
    registry, _ = registry

    def never(_):
        pytest.fail("A free-tier allowlist check must not call a provider")

    async with httpx.AsyncClient(transport=httpx.MockTransport(never)) as client:
        for provider, model in (
            ("groq", "openai/gpt-oss-120b"),
            ("gemini", "gemini-3.5-flash"),
            ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b"),
        ):
            route = registry.models[provider + "/" + model]
            assert registry.rejection(route, Requirements()) is None
            assert await verify_dispatch(client, route, key="fixture-" + provider) is None
        paid = offer(
            registry,
            "nvidia",
            route_id="nvidia/partner-priced-model",
            model_id="partner-priced-model",
        )
        with pytest.raises(BrokerError, match="price_unverified"):
            await verify_dispatch(client, paid, key="fixture-nvidia")


def test_pace_selects_groq_or_gemini_without_a_classifier_call():
    assert route_class("hello", []) == "FAST_CHAT"
    assert route_class("hello", [], budget_mode="deep") == "DEEP_REASONING"
    assert route_class("prove this theorem", [], budget_mode="fast") == "FAST_CHAT"
    assert route_class("x" * 4000, []) == "RESEARCH"
    assert route_class("what time is it", ["clock.now.v1"], budget_mode="fast") == "TOOL_EXECUTION"


def test_free_tier_routes_by_task_and_falls_back_after_a_rate_limit(registry):
    registry, _ = registry
    assert (
        registry.choose(ModelSelection(), Requirements(task_class="FAST_CHAT")).model_id
        == "openai/gpt-oss-120b"
    )
    assert (
        registry.choose(ModelSelection(), Requirements(task_class="DEEP_REASONING")).model_id
        == "nvidia/nemotron-3-ultra-550b-a55b"
    )
    assert (
        registry.choose(
            ModelSelection(), Requirements(task_class="TOOL_EXECUTION", tools=True)
        ).provider
        == "groq"
    )
    registry.failure(registry.models["groq/openai/gpt-oss-120b"], 429, "30")
    fallback = registry.choose(ModelSelection(), Requirements(task_class="FAST_CHAT"))
    assert fallback.provider == "gemini" and fallback.model_id == "gemini-3.5-flash"
    registry.failure(registry.models["nvidia/nvidia/nemotron-3-ultra-550b-a55b"], 429, "30")
    deep_fallback = registry.choose(ModelSelection(), Requirements(task_class="DEEP_REASONING"))
    assert deep_fallback.provider == "gemini" and deep_fallback.model_id == "gemini-3.5-flash"


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"available": False}, "model_unverified"),
        ({"qualification": "unverified"}, "model_unverified"),
        ({"zero_price_until": 999.0}, "price_or_account_unverified"),
        ({"account_until": 999.0}, "price_or_account_unverified"),
        ({"credential_identity": "foreign"}, "price_or_account_unverified"),
        ({"privacy": ("public",)}, "privacy_ineligible"),
        ({"tools_qualified": False}, "capability_ineligible"),
        ({"context_tokens": 1024}, "context_ineligible"),
        ({"quota_remaining": 0}, "quota_exhausted"),
    ],
)
def test_hard_eligibility_filters_precede_ranking(registry, change, reason):
    registry, _ = registry
    route = offer(registry, "groq", **change)
    assert registry.rejection(route, Requirements(tools=True, context_tokens=2000)) == reason


def test_quality_then_p95_ranking_manual_stickiness_and_circuit_fallback(registry):
    registry, store = registry
    slow, fast = offer(registry, "groq"), offer(registry, "gemini")
    registry.models = {slow.route_id: slow, fast.route_id: fast}
    sid = store.session()["id"]
    for route, outcomes, latency in [(slow, [True] * 3, 800), (fast, [True, False, False], 10)]:
        for index, success in enumerate(outcomes):
            task = store.create(
                TaskRequest(
                    session_id=sid,
                    request_id=route.provider + str(index),
                    content="fixture",
                    cloud_consent=True,
                )
            )[0]
            registry.observe(route, task["task_id"], "TOOL_EXECUTION", success, True, latency, 100)
    need = Requirements(task_class="TOOL_EXECUTION", tools=True)
    assert registry.choose(ModelSelection(), need) == slow
    assert (
        registry.choose(ModelSelection(mode="manual_cloud", route_id=fast.route_id), need) == fast
    )
    registry.failure(slow, 429, "120")
    assert registry.choose(ModelSelection(), need) == fast  # next selection, no inference replay
    with pytest.raises(BrokerError, match="route_unavailable"):
        registry.choose(ModelSelection(mode="manual_cloud", route_id=slow.route_id), need)
    assert registry.health(slow)[1] == 1120.0
    assert registry.rejection(fast, replace(need, deadline=999)) == "budget_or_deadline"


def test_auth_rejection_is_credential_scoped_and_rotation_invalidates_proof(registry):
    registry, _ = registry
    route = offer(registry, "groq")
    registry.failure(route, 401)
    assert registry.rejection(route, Requirements()) == "credential_rejected"
    registry.settings.groq_api_key = SecretStr("rotated-fixture")
    assert registry.rejection(route, Requirements()) == "price_or_account_unverified"
    refreshed = offer(registry, "groq")
    assert registry.rejection(refreshed, Requirements()) is None


def test_late_old_credential_failure_cannot_poison_rotated_account(registry):
    registry, _ = registry
    route = offer(registry, "groq")
    original = credential_identity(registry.settings, "groq")
    registry.settings.groq_api_key = SecretStr("rotated-offline-fixture")
    registry.failure(route, 401, credential=original)
    assert not registry.health(route)[2]


async def test_busy_task_or_voice_turn_prevents_mode_switch(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            app.state.engine.active = "active-fixture"
            response = await client.post(
                "/v1/settings/model-mode", headers=AUTH, json={"mode": "local_qwen"}
            )
            assert response.status_code == 409
            app.state.engine.active = None
            app.state.voice.state = "TRANSCRIBING"
            response = await client.post(
                "/v1/settings/model-mode", headers=AUTH, json={"mode": "local_qwen"}
            )
            assert response.status_code == 409
            assert app.state.engine.registry.selection().mode == "auto_cloud"
            app.state.voice.state = "IDLE"
    finally:
        app.state.store.db.close()


@pytest.mark.parametrize("mode", ["local_qwen", "local_heretic"])
async def test_local_mode_is_sticky_across_restart_and_blocks_all_cloud_io(tmp_path, mode):
    requests = []

    def never(request):
        requests.append(request)
        pytest.fail("Local mode must not call any cloud catalog or inference endpoint")

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(never))
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        openrouter_api_key=SecretStr("offline-provider-credential-not-in-the-prompt"),
    )
    app = create_app(settings, TOKEN, client=upstream)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            assert (
                await client.post("/v1/settings/model-mode", headers=AUTH, json={"mode": mode})
            ).status_code == 200
            sid = (await client.post("/v1/sessions", headers=AUTH)).json()["id"]
            body = {
                "session_id": sid,
                "request_id": "local",
                "content": "Explain this public fixture",
                "cloud_consent": True,
            }
            response = await client.post("/v1/tasks", headers=AUTH, json=body)
            assert response.json()["status"] == "blocked"
            assert response.json()["error"]["code"] == "local_model_unavailable"
            assert not (await client.get("/health/ready", headers=AUTH)).json()["ready"]
            assert (await client.post("/v1/tasks", headers=AUTH, json=body)).json()[
                "task_id"
            ] == response.json()["task_id"]
        app.state.store.db.close()
        reopened = Store(tmp_path / "state.sqlite3")
        try:
            assert ModelRegistry(reopened.db, settings).selection().mode == mode
        finally:
            reopened.db.close()
        assert not requests
    finally:
        await upstream.aclose()
        app.state.store.db.close()


def test_shared_local_budget_spans_tasks_and_does_not_reset_on_key_rotation(tmp_path):
    db = sqlite3.connect(tmp_path / "ledger.sqlite")
    db.row_factory = sqlite3.Row
    ledger = Ledger(db)
    try:
        for index in range(50):
            attempt = ledger.begin(str(index), 4000, 2, MODEL)
            ledger.bind_route(attempt, "groq", "fixture", "single-broker-account", "groq/fixture")
            ledger.reserve(attempt, 10, 10)
        extra = ledger.begin("new-task", 4000, 2, MODEL)
        ledger.bind_route(extra, "groq", "fixture", "single-broker-account", "groq/fixture")
        with pytest.raises(BrokerError, match="shared_budget_exhausted"):
            ledger.reserve(extra, 10, 10)
        # A new provider has its own explicitly bounded local pool.
        other = ledger.begin("other", 4000, 2, MODEL)
        ledger.bind_route(other, "gemini", "fixture", "single-broker-account", "gemini/fixture")
        ledger.reserve(other, 10, 10)
        with pytest.raises(BrokerError, match="route_changed"):
            ledger.bind_route(other, "nvidia", "fixture", "single-broker-account", "nvidia/fixture")
    finally:
        db.close()


def test_v3_migration_preserves_data_and_creates_consistent_backup(tmp_path):
    path = tmp_path / "state.sqlite3"
    first = Store(path)
    sid = first.session()["id"]
    first.db.execute("PRAGMA user_version=3")
    first.db.close()
    second = Store(path)
    try:
        assert second.sessions()[0]["id"] == sid
        assert second.db.execute("PRAGMA user_version").fetchone()[0] == 4
        backups = list(tmp_path.glob("state.sqlite3.pre-v3-*.sqlite"))
        assert len(backups) == 1
        with sqlite3.connect(backups[0]) as backup:
            assert backup.execute("PRAGMA user_version").fetchone()[0] == 3
            assert backup.execute("SELECT id FROM sessions").fetchone()[0] == sid
    finally:
        second.db.close()


@pytest.mark.parametrize(
    "content,caps,artifact,expected",
    [
        ("Hello", [], "none", "FAST_CHAT"),
        ("Extract JSON", [], "none", "STRUCTURED_EXTRACTION"),
        ("Analyze the proof", [], "none", "DEEP_REASONING"),
        ("Debug repository code", [], "none", "CODING"),
        ("Research MCP sources", [], "none", "RESEARCH"),
        (
            "Make a report",
            ["public.research.v1", "report.create.v1"],
            "markdown-and-pdf",
            "DOCUMENT_WRITING",
        ),
        ("Verify time", ["clock.now.v1"], "none", "TOOL_EXECUTION"),
    ],
)
def test_classification_spends_no_cloud_call(content, caps, artifact, expected):
    assert task_class(content, caps, artifact) == expected


@pytest.mark.parametrize("provider", ["groq", "gemini", "nvidia", "openrouter"])
async def test_broker_task_uses_selected_route_and_shared_accounting(
    tmp_path, monkeypatch, provider
):
    import time
    import immortility_broker.app as app_module
    from immortility_broker.policy import MODEL

    sent, verified = [], []
    app = None

    async def fixture_preflight(client, route, *, key, minimum_requests, still_authorized):
        assert key == "fixture-" + route.provider
        assert minimum_requests == 1 and still_authorized()
        verified.append(route.provider)
        return 50

    monkeypatch.setattr(app_module, "verify_dispatch", fixture_preflight)

    def upstream(request):
        sent.append(request)
        assert request.headers["Authorization"] == "Bearer fixture-" + provider
        assert str(request.url) == PROVIDERS[provider].base_url + "/chat/completions"
        assert json.loads(request.content)["model"] == "fixture-model"
        chunks = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Synthetic provider fixture response"},
                        "finish_reason": None,
                    }
                ]
            },
            {
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20},
            },
        ]
        return httpx.Response(
            200,
            text="".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
            + "data: [DONE]\n\n",
            headers={"content-type": "text/event-stream"},
        )

    class FixtureHermesIngress:
        """Mock Hermes ingress for HTTP routing integration, not a product loop."""

        async def run(self, content, history, role=None):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
            ) as client:
                response = await client.post(
                    "/inference/v1/chat/completions",
                    headers={"Authorization": "Bearer " + app.state.engine.inference_key},
                    json={"model": MODEL, "messages": [{"role": "user", "content": content}]},
                )
                response.raise_for_status()
                health_response = await client.get("/health/ready", headers=AUTH)
                assert health_response.status_code == 200
                health = health_response.json()
                assert health["active_model"] == {
                    "provider": provider,
                    "model": "fixture-model",
                    "route_id": provider + "/fixture-model",
                }
                assert "fixture-" + provider not in json.dumps(health)
                assert "credential_identity" not in json.dumps(health)
                for line in response.text.splitlines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        for choice in json.loads(line[6:]).get("choices", []):
                            if choice["delta"].get("content"):
                                yield choice["delta"]["content"]

        async def stop(self):
            pass

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        openrouter_fallback_enabled=True,
        **{PROVIDERS[provider].credential_field: SecretStr("fixture-" + provider)},
    )
    transport = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_app(settings, TOKEN, client=transport, factory=FixtureHermesIngress)
    route = offer(
        app.state.engine.registry,
        provider,
        zero_price_until=time.time() + 300,
        account_until=time.time() + 300,
    )
    app.state.engine.registry.models[route.route_id] = route
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            assert (
                await client.post(
                    "/v1/settings/model-mode",
                    headers=AUTH,
                    json={"mode": "manual_cloud", "route_id": route.route_id},
                )
            ).status_code == 200
            sid = (await client.post("/v1/sessions", headers=AUTH)).json()["id"]
            response = await client.post(
                "/v1/tasks",
                headers=AUTH,
                json={
                    "session_id": sid,
                    "request_id": "manual",
                    "content": "Hello public example",
                    "cloud_consent": True,
                },
            )
            tid = response.json()["task_id"]
            await app.state.engine.worker
            task = (await client.get(f"/v1/tasks/{tid}", headers=AUTH)).json()
            assert task["status"] == "succeeded", task.get("error")
            assert (
                task["result"]["provider"] == provider
                and task["result"]["model"] == "fixture-model"
            )
            trace = (await client.get(f"/v1/tasks/{tid}/trace", headers=AUTH)).json()
            assert trace["agent"]["route"] == route.route_id
            usage = (await client.get(f"/v1/tasks/{tid}/usage", headers=AUTH)).json()
            assert usage["summary"]["calls"] == 1 and usage["summary"]["charged_tokens"] == 70
            assert usage["routes"][-1]["provider"] == provider
            assert "fixture-" + provider not in json.dumps([task, trace, usage])
        assert len(sent) == 1 and verified == [provider]
    finally:
        await transport.aclose()
        app.state.store.db.close()


def test_direct_routes_prefer_specialists_and_admit_nothing_by_default():
    fast = decide_route(kind="FAST_CHAT", content="hello")
    deep = decide_route(kind="DEEP_REASONING", content="plan the architecture")
    coding = decide_route(kind="CODING", content="debug this refactor")
    clock = decide_route(kind="TOOL_EXECUTION", content="what time is it", tools=True)
    assert fast["model_id"] == "openai/gpt-oss-120b" and fast["admitted"] is False
    assert "remaining quota is unverified" in fast["reason"]
    assert deep["model_id"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert "free prototype" in deep["reason"] and "not read" in deep["reason"]
    assert coding["provider"] == "nvidia" and coding["fallback_used"] is False
    assert clock["provider"] == "groq" and clock["paid_fallback"] is False
    eligible = frozenset({"gemini-3.8-flash"})
    fallback = decide_route(kind="FAST_CHAT", content="hello", eligible=eligible)
    assert fallback["model_id"] == "gemini-3.8-flash" and fallback["fallback_used"] is True
    pinned = decide_route(
        kind="FAST_CHAT",
        mode="manual_cloud",
        manual_model="openai/gpt-oss-120b",
        eligible=eligible,
    )
    assert pinned["model_id"] == "openai/gpt-oss-120b" and pinned["admitted"] is False
    tool = decide_route(
        kind="TOOL_EXECUTION",
        content="debug the agentic tool",
        tools=True,
        eligible=eligible,
    )
    assert tool["model_id"] == "nvidia/nemotron-3-ultra-550b-a55b" and tool["admitted"] is False
    private = decide_route(kind="FAST_CHAT", privacy="personal", eligible=eligible)
    assert private["provider"] == "local" and private["admitted"] is False
    offline = decide_route(kind="DEEP_REASONING", mode="local_heretic", local_ready=True)
    assert offline["admitted"] is True and offline["model_id"].endswith("heretic")
    assert "openrouter" not in json.dumps(
        [fast, deep, coding, clock, fallback, pinned, tool, private, offline]
    )
