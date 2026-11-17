"""Broker-owned route policy on the existing Hermes-compatible proxy transport.

No native provider credentials enter Hermes. Provider-hosted tools, arbitrary
endpoints, local-model startup and same-task inference replay are not exposed.
"""

import hashlib
import json
import asyncio
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from types import MappingProxyType
from typing import Any, Callable, Literal

import httpx
from pydantic import Field, model_validator

from .capabilities import StrictModel
from .config import Settings
from .contracts import BrokerError
from .policy import MODEL

ProviderId = Literal["groq", "gemini", "nvidia", "openrouter"]
ModelMode = Literal["auto_cloud", "manual_cloud", "local_qwen", "local_heretic"]
TaskClass = Literal[
    "FAST_CHAT",
    "STRUCTURED_EXTRACTION",
    "DEEP_REASONING",
    "CODING",
    "RESEARCH",
    "DOCUMENT_WRITING",
    "TOOL_EXECUTION",
    "MULTIMODAL",
]


@dataclass(frozen=True)
class Provider:
    id: ProviderId
    base_url: str
    credential_field: str
    docs: str


PROVIDERS = MappingProxyType(
    {
        "groq": Provider(
            "groq",
            "https://api.groq.com/openai/v1",
            "groq_api_key",
            "https://console.groq.com/docs/openai",
        ),
        "gemini": Provider(
            "gemini",
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "gemini_api_key",
            "https://ai.google.dev/gemini-api/docs/openai",
        ),
        "nvidia": Provider(
            "nvidia",
            "https://integrate.api.nvidia.com/v1",
            "nvidia_api_key",
            "https://docs.api.nvidia.com/nim/reference/llm-apis",
        ),
        "openrouter": Provider(
            "openrouter",
            "https://openrouter.ai/api/v1",
            "openrouter_api_key",
            "https://openrouter.ai/docs/guides/features/tool-calling",
        ),
    }
)


class ModelSelection(StrictModel):
    mode: ModelMode = "auto_cloud"
    route_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:/-]{1,160}$")

    @model_validator(mode="after")
    def manual_identity(self) -> "ModelSelection":
        if (self.mode == "manual_cloud") != (self.route_id is not None):
            raise ValueError("Only manual cloud mode requires a route identity")
        return self


class ModelOffer(StrictModel):
    route_id: str = Field(pattern=r"^[A-Za-z0-9._:/-]{1,160}$")
    provider: ProviderId
    model_id: str = Field(pattern=r"^[A-Za-z0-9._:/-]{1,128}$")
    revision: str | None = Field(default=None, max_length=128)
    context_tokens: int = Field(ge=1024, le=2000000)
    modalities: tuple[Literal["text", "vision"], ...] = ("text",)
    tools_qualified: bool = False
    structured_qualified: bool = False
    qualification: Literal["offline", "live", "unverified"] = "unverified"
    # These proofs are internal verified evidence, never fields accepted from UI.
    zero_price_until: float = Field(default=0, ge=0, allow_inf_nan=False)
    account_until: float = Field(default=0, ge=0, allow_inf_nan=False)
    credential_identity: str = ""
    privacy: tuple[Literal["public", "personal"], ...] = ("public",)
    quota_remaining: int | None = Field(default=None, ge=0)
    quota_checked_at: float | None = None
    available: bool = False
    context_overhead: int = Field(default=0, ge=0, le=32000)

    @model_validator(mode="after")
    def canonical_route(self) -> "ModelOffer":
        expected = (
            MODEL
            if self.provider == "openrouter" and self.model_id == MODEL
            else self.provider + "/" + self.model_id
        )
        if self.route_id != expected:
            raise ValueError("Route identity must match its provider and model")
        return self


@dataclass(frozen=True)
class Requirements:
    task_class: TaskClass = "FAST_CHAT"
    tools: bool = False
    structured: bool = False
    modality: str = "text"
    privacy: str = "personal"
    context_tokens: int = 0
    remaining_calls: int = 1
    remaining_tokens: int = 4000
    deadline: float = float("inf")


def task_class(content: str, capabilities: list[str], artifacts: str = "none") -> TaskClass:
    if artifacts != "none":
        return "DOCUMENT_WRITING"
    if capabilities:
        return "TOOL_EXECUTION"
    text = content.lower()
    if re.search(r"\b(code|coding|repository|pytest|refactor|debug|traceback)\b", text):
        return "CODING"
    if re.search(r"\b(research|sources|citations|documentation)\b", text):
        return "RESEARCH"
    if re.search(r"\b(json|extract|classify|structured)\b", text):
        return "STRUCTURED_EXTRACTION"
    if re.search(r"\b(prove|reason|reasoning|analyze|analyse|planning)\b", text):
        return "DEEP_REASONING"
    return "FAST_CHAT"


def route_class(
    content: str,
    capabilities: list[str],
    artifacts: str = "none",
    budget_mode: str = "auto",
    context_tokens: int = 0,
) -> TaskClass:
    """Pick a route class without a model call. NVIDIA stays out until it is free-tier qualified."""
    kind = task_class(content, capabilities, artifacts)
    if budget_mode == "deep":
        return "DEEP_REASONING"
    if budget_mode == "fast" and not capabilities and artifacts == "none":
        return "FAST_CHAT"
    if kind == "FAST_CHAT" and (context_tokens >= 6000 or len(content) >= 4000):
        return "RESEARCH"
    return kind


@dataclass(frozen=True)
class RouteCandidate:
    provider: str
    model_id: str
    reason: str


GROQ_FAST = RouteCandidate(
    "groq",
    "openai/gpt-oss-120b",
    "Free plan and organization caps were attested, but remaining quota is unverified and zero-price dispatch stays closed.",
)
GEMINI_REASONING = RouteCandidate(
    "gemini",
    "gemini-3.8-flash",
    "The public price page lists a free tier for this model. This account is not qualified.",
)
NVIDIA_DEEP = RouteCandidate(
    "nvidia",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "NVIDIA Build lists this model on its free prototype endpoint. Partner prices are a different route. Account quota is not read.",
)
LOCAL_HERETIC = RouteCandidate(
    "local",
    "xtools-at/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic",
    "The local model is not installed. Download requires separate approval.",
)
# Explicit free-tier allowlist. A published paid price does not remove a model
# that the provider serves on its free plan. Models absent from this map stay closed.
FREE_TIER: dict[tuple[str, str], dict[str, int | bool]] = {
    ("groq", "openai/gpt-oss-120b"): {"context": 131072, "tools": True},
    ("gemini", "gemini-3.5-flash"): {"context": 1048576, "tools": True},
    ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b"): {"context": 1048576, "tools": True},
}
CANDIDATES = (GROQ_FAST, GEMINI_REASONING, NVIDIA_DEEP, LOCAL_HERETIC)


def free_tier(provider: str, model_id: str) -> bool:
    return (provider, model_id) in FREE_TIER


def preference_order(kind: TaskClass, content: str, tools: bool) -> tuple[RouteCandidate, ...]:
    advanced = bool(
        re.search(r"\b(architecture|debug|refactor|agentic|planning)\b", content.lower())
    )
    if tools:
        return (NVIDIA_DEEP if advanced else GROQ_FAST,)
    if (
        kind == "DEEP_REASONING"
        or (kind == "CODING" and advanced)
        or (kind == "RESEARCH" and advanced)
    ):
        return (NVIDIA_DEEP, GEMINI_REASONING)
    if kind in {"RESEARCH", "DOCUMENT_WRITING", "MULTIMODAL", "STRUCTURED_EXTRACTION"}:
        return (GEMINI_REASONING, GROQ_FAST)
    return (GROQ_FAST, GEMINI_REASONING)


def decide_route(
    *,
    kind: TaskClass,
    content: str = "",
    tools: bool = False,
    privacy: str = "public",
    mode: ModelMode = "auto_cloud",
    manual_model: str | None = None,
    eligible: frozenset[str] = frozenset(),
    local_ready: bool = False,
) -> dict[str, Any]:
    """Choose one preferred model. An empty eligibility set admits nothing and sends nothing."""
    if mode == "local_qwen":
        return {
            "task_class": kind,
            "provider": "local",
            "model_id": "Qwen/Qwen3.5-9B",
            "admitted": False,
            "fallback_used": False,
            "reason": "The selected local model is the Heretic build, and standard Qwen is not installed.",
            "paid_fallback": False,
        }
    if mode == "local_heretic" or privacy == "personal":
        order: tuple[RouteCandidate, ...] = (LOCAL_HERETIC,)
    elif mode == "manual_cloud":
        chosen = next((item for item in CANDIDATES if item.model_id == manual_model), None)
        order = (chosen,) if chosen is not None else ()
    else:
        order = preference_order(kind, content, tools)
    if tools or mode == "manual_cloud":
        order = order[:1]
    preferred: RouteCandidate | None = None
    for index, candidate in enumerate(order):
        if candidate.provider == "local":
            admitted = local_ready
        else:
            admitted = candidate.model_id in eligible
        if admitted:
            return {
                "task_class": kind,
                "provider": candidate.provider,
                "model_id": candidate.model_id,
                "admitted": True,
                "fallback_used": index > 0,
                "reason": "eligible",
                "paid_fallback": False,
            }
        if preferred is None:
            preferred = candidate
    if preferred is None:
        return {
            "task_class": kind,
            "provider": None,
            "model_id": None,
            "admitted": False,
            "fallback_used": False,
            "reason": "No eligible direct model is admitted. No request was sent.",
            "paid_fallback": False,
        }
    return {
        "task_class": kind,
        "provider": preferred.provider,
        "model_id": preferred.model_id,
        "admitted": False,
        "fallback_used": False,
        "reason": preferred.reason,
        "paid_fallback": False,
    }


def credential_identity(settings: Settings, provider: ProviderId) -> str:
    secret = getattr(settings, PROVIDERS[provider].credential_field).get_secret_value()
    return hashlib.sha256(secret.encode()).hexdigest() if secret else ""


class ModelRegistry:
    def __init__(
        self, db: sqlite3.Connection, settings: Settings, clock: Callable[[], float] = time.time
    ):
        self.db, self.settings, self.clock = db, settings, clock
        # Existing virtual free route only. Other models enter through a reviewed
        # verifier, not advertisements, a key's presence or frontend price claims.
        self.models: dict[str, ModelOffer] = {
            MODEL: ModelOffer(
                route_id=MODEL,
                provider="openrouter",
                model_id=MODEL,
                context_tokens=16384,
                tools_qualified=True,
                structured_qualified=True,
                qualification="offline",
                privacy=("public", "personal"),
                available=True,
            )
        }
        self.refresh_free_routes()

    def refresh_free_routes(self) -> None:
        """Admit allowlisted free models when their credential is present. Paid models are never added."""
        for (provider, model_id), spec in FREE_TIER.items():
            route_id = provider + "/" + model_id
            if not credential_identity(self.settings, provider):  # type: ignore[arg-type]
                self.models.pop(route_id, None)
                continue
            self.models[route_id] = ModelOffer(
                route_id=route_id,
                provider=provider,  # type: ignore[arg-type]
                model_id=model_id,
                context_tokens=int(spec["context"]),
                tools_qualified=bool(spec["tools"]),
                structured_qualified=True,
                qualification="live",
                privacy=("public", "personal"),
                available=True,
            )

    def selection(self) -> ModelSelection:
        row = self.db.execute("SELECT body FROM model_preferences WHERE id=1").fetchone()
        return ModelSelection.model_validate_json(row[0]) if row else ModelSelection()

    def set_selection(self, value: ModelSelection) -> None:
        if value.mode == "manual_cloud" and value.route_id not in self.models:
            raise BrokerError(
                "route_unavailable", "The selected cloud route is not registered.", 403
            )
        with self.db:
            self.db.execute(
                "INSERT INTO model_preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                (value.model_dump_json(),),
            )

    def ready(self) -> bool:
        try:
            self.choose(self.selection(), Requirements(privacy="public"))
            return True
        except BrokerError:
            return False

    def health(self, offer: ModelOffer, credential: str | None = None) -> tuple[int, float, bool]:
        identity = (
            offer.route_id
            + ":"
            + (
                credential
                if credential is not None
                else credential_identity(self.settings, offer.provider)
            )
        )
        row = self.db.execute(
            "SELECT failures,cooldown,auth_blocked FROM provider_health WHERE route_id=?",
            (identity,),
        ).fetchone()
        return (int(row[0]), float(row[1]), bool(row[2])) if row else (0, 0.0, False)

    def rejection(self, offer: ModelOffer, need: Requirements) -> str | None:
        now = self.clock()
        if self.settings.local_only_mode:
            return "local_only"
        if offer.provider == "openrouter" and not self.settings.openrouter_fallback_enabled:
            return "optional_fallback_disabled"
        identity = credential_identity(self.settings, offer.provider)
        if not identity:
            return "missing_credential"
        if not offer.available or offer.qualification == "unverified":
            return "model_unverified"
        # Legacy virtual router is a candidate pending its mandatory fresh public
        # catalog preflight. That exception never authorizes a provider POST.
        legacy = (
            offer.route_id == MODEL and offer.provider == "openrouter" and offer.model_id == MODEL
        )
        if not legacy and not free_tier(offer.provider, offer.model_id) and (
            offer.zero_price_until <= now
            or offer.account_until <= now
            or offer.credential_identity != identity
        ):
            return "price_or_account_unverified"
        if need.privacy not in offer.privacy:
            return "privacy_ineligible"
        if (
            need.modality not in offer.modalities
            or need.tools
            and not offer.tools_qualified
            or need.structured
            and not offer.structured_qualified
        ):
            return "capability_ineligible"
        if offer.context_tokens < need.context_tokens:
            return "context_ineligible"
        if need.deadline <= now or need.remaining_calls <= 0 or need.remaining_tokens < 128:
            return "budget_or_deadline"
        count, _, latency = self.statistics(offer, need.task_class)
        if count >= 3 and now + latency / 1000 >= need.deadline:
            return "deadline_ineligible"
        if offer.quota_remaining == 0:
            return "quota_exhausted"
        failures, cooldown, auth_blocked = self.health(offer)
        if auth_blocked:
            return "credential_rejected"
        if cooldown > now:
            return "circuit_open"
        return None

    def statistics(self, offer: ModelOffer, kind: TaskClass) -> tuple[int, float, float]:
        rows = self.db.execute(
            "SELECT verified_success,latency_ms FROM route_observations WHERE route_id=? AND task_class=? AND verified_success IS NOT NULL ORDER BY rowid DESC LIMIT 100",
            (offer.route_id, kind),
        ).fetchall()
        if not rows:
            return 0, 0.0, 0.0
        latencies = sorted(float(row[1]) for row in rows)
        return (
            len(rows),
            sum(int(row[0]) for row in rows) / len(rows),
            latencies[math.ceil(0.95 * len(rows)) - 1],
        )

    def choose(self, selection: ModelSelection, need: Requirements) -> ModelOffer:
        if selection.mode.startswith("local_") or self.settings.local_only_mode:
            raise BrokerError(
                "local_model_unavailable",
                "Local language-model mode is selected; no cloud request is permitted. The M4 runtime is not installed.",
                403,
            )
        candidates = list(self.models.values())
        if selection.mode == "manual_cloud":
            candidates = [offer for offer in candidates if offer.route_id == selection.route_id]
        candidates = [offer for offer in candidates if self.rejection(offer, need) is None]
        if not candidates:
            raise BrokerError(
                "route_unavailable",
                "No route meets model, privacy, price/account, capability, quota and health requirements. No fallback was sent.",
                503,
            )

        def ranking(offer: ModelOffer) -> tuple[Any, ...]:
            count, success, latency = self.statistics(offer, need.task_class)
            measured = count >= 3
            if need.task_class in {"DEEP_REASONING", "CODING"} and not need.tools:
                preferred_provider = "nvidia"
            elif need.task_class in {"FAST_CHAT", "TOOL_EXECUTION"} or need.tools:
                preferred_provider = "groq"
            else:
                preferred_provider = "gemini"
            preferred = offer.provider == preferred_provider
            return (
                not preferred,
                offer.provider == "openrouter",
                not measured,
                -success if measured else 0,
                latency if measured else math.inf,
                offer.context_overhead,
                -(offer.quota_remaining or 0),
                offer.route_id,
            )

        return min(candidates, key=ranking)

    def failure(
        self,
        offer: ModelOffer,
        status: int,
        retry_after: str | None = None,
        *,
        credential: str | None = None,
    ) -> None:
        failures, cooldown, auth = self.health(offer, credential)
        failures += 1
        wait = 60.0 if status == 429 or failures >= 3 else 0.0
        if retry_after and len(retry_after) <= 128:
            try:
                wait = max(wait, float(retry_after))
            except ValueError:
                try:
                    wait = max(wait, parsedate_to_datetime(retry_after).timestamp() - self.clock())
                except (ValueError, TypeError, OverflowError):
                    pass
        if not math.isfinite(wait):
            wait = 3600
        cooldown = max(cooldown, self.clock() + min(max(wait, 0), 3600))
        with self.db:
            self.db.execute(
                "INSERT INTO provider_health VALUES(?,?,?,?) ON CONFLICT(route_id) DO UPDATE SET failures=excluded.failures,cooldown=excluded.cooldown,auth_blocked=excluded.auth_blocked",
                (
                    offer.route_id
                    + ":"
                    + (
                        credential
                        if credential is not None
                        else credential_identity(self.settings, offer.provider)
                    ),
                    failures,
                    cooldown,
                    int(auth or status in {401, 403}),
                ),
            )

    def observe(
        self,
        offer: ModelOffer,
        tid: str,
        kind: TaskClass,
        success: bool,
        verified: bool,
        latency_ms: float,
        tokens: int,
    ) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO route_observations VALUES(?,?,?,?,?,?,?)",
                (
                    tid,
                    offer.route_id,
                    kind,
                    int(success),
                    int(success) if verified else None,
                    max(latency_ms, 0),
                    max(tokens, 0),
                ),
            )

    def view(self) -> dict[str, Any]:
        samples: tuple[tuple[TaskClass, str, bool], ...] = (
            ("FAST_CHAT", "hello", False),
            ("DEEP_REASONING", "plan the architecture", False),
            ("TOOL_EXECUTION", "what time is it", True),
            ("CODING", "debug this refactor", False),
        )
        rows = []
        for offer in self.models.values():
            rows.append(
                {
                    "route_id": offer.route_id,
                    "provider": offer.provider,
                    "model": offer.model_id,
                    "revision": offer.revision,
                    "context_tokens": offer.context_tokens,
                    "modalities": list(offer.modalities),
                    "tools_qualification": offer.qualification
                    if offer.tools_qualified
                    else "unverified",
                    "blocked_reason": self.rejection(offer, Requirements(privacy="public")),
                    "price_check": "fresh catalog required before each request"
                    if offer.route_id == MODEL
                    else "free-tier allowlist; provider quota is not read"
                    if free_tier(offer.provider, offer.model_id)
                    else "paid or unverified models stay closed",
                    "quota_remaining": offer.quota_remaining,
                    "quota_checked_at": offer.quota_checked_at,
                    "cooldown_until": self.health(offer)[1],
                }
            )
        return {
            "selection": self.selection().model_dump(),
            "providers": [
                {
                    "id": provider.id,
                    "credential_present": bool(credential_identity(self.settings, provider.id)),
                    "transport": "Hermes OpenAI-compatible broker proxy",
                    "status": (
                        "optional fallback enabled; fresh preflight requires zero price and official account quota"
                        if self.settings.openrouter_fallback_enabled
                        else "optional fallback disabled; explicit broker configuration opt-in required"
                    )
                    if provider.id == "openrouter"
                    else {
                        "groq": "free-tier allowlist openai/gpt-oss-120b; provider quota is not read",
                        "gemini": "free-tier allowlist gemini-3.5-flash; provider quota is not read",
                        "nvidia": "free prototype allowlist nvidia/nemotron-3-ultra-550b-a55b; account quota is not read",
                    }[provider.id],
                    "docs": provider.docs,
                }
                for provider in PROVIDERS.values()
            ],
            "models": rows,
            "local_models": [
                {"mode": "local_qwen", "model": "Qwen/Qwen3.5-9B", "available": False},
                {
                    "mode": "local_heretic",
                    "model": "xtools-at/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic",
                    "available": False,
                },
            ],
            "automatic_local_fallback": False,
            "paid_fallback": False,
            "routing": [
                decide_route(kind=kind, content=sample, tools=tools)
                for kind, sample, tools in samples
            ],
        }


def compatible_request(
    client: httpx.AsyncClient, settings: Settings, offer: ModelOffer, payload: dict[str, Any]
) -> httpx.Request:
    """One reviewed transport adapter; no arbitrary body options or hosted tools."""
    body = {
        key: value
        for key, value in payload.items()
        if key
        in {"messages", "stream", "stream_options", "max_tokens", "tools", "parallel_tool_calls"}
    }
    body.update(model=offer.model_id, n=1)
    if offer.provider == "openrouter":
        body["provider"] = {"max_price": {"prompt": 0, "completion": 0}, "allow_fallbacks": False}
    key = getattr(settings, PROVIDERS[offer.provider].credential_field).get_secret_value()
    if not key:
        raise BrokerError("missing_key", "Selected provider credential is unavailable.", 403)
    return client.build_request(
        "POST",
        PROVIDERS[offer.provider].base_url + "/chat/completions",
        json=body,
        headers={"Authorization": "Bearer " + key},
    )


async def verify_free_quota(
    client: httpx.AsyncClient, key: str, *, minimum_requests: int = 1
) -> int:
    """Fresh official account metadata, never a price/entitlement substitute.

    No cache survives credential rotation or restart. Only an integer count
    escapes this function; labels, account IDs, balances and response bodies do not.
    A remote concurrent consumer can still exhaust quota after this observation;
    the provider must reject that request and no fallback is authorized here.
    """
    if not key or type(minimum_requests) is not int or minimum_requests < 1:
        raise BrokerError("quota_unverified", "Free-model account quota is unverified.", 403)

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise ValueError("Ambiguous metadata")
            result[name] = value
        return result

    try:
        async with (
            asyncio.timeout(10),
            client.stream(
                "GET",
                "https://openrouter.ai/api/v1/key",
                headers={"Authorization": "Bearer " + key, "Accept": "application/json"},
                timeout=10,
                follow_redirects=False,
            ) as response,
        ):
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                if len(body) + len(chunk) > 32768:
                    raise ValueError("Metadata exceeds bound")
                body.extend(chunk)
        quota = json.loads(body.decode("utf-8"), object_pairs_hook=unique)["data"][
            "free_model_daily_requests"
        ]
        limit, used, remaining = (quota[name] for name in ("limit", "used", "remaining"))
        if (
            any(type(value) is not int or value < 0 for value in (limit, used, remaining))
            or used + remaining != limit
        ):
            raise ValueError("Inconsistent quota")
    except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError, RecursionError):
        raise BrokerError(
            "quota_unverified",
            "Cannot verify current account free-model quota. No inference sent.",
            403,
        ) from None
    if remaining < minimum_requests:
        raise BrokerError(
            "quota_exhausted", "Insufficient account free-model requests. No inference sent.", 403
        )
    assert isinstance(remaining, int)
    return remaining


async def verify_dispatch(
    client: httpx.AsyncClient,
    offer: ModelOffer,
    *,
    key: str = "",
    minimum_requests: int = 1,
    still_authorized: Callable[[], bool] | None = None,
) -> int | None:
    # Allowlisted free-tier models do not have an account quota document.
    # Returning None means "not read", never an invented remaining count.
    # Every other direct model, including priced NVIDIA routes, stays closed.
    if free_tier(offer.provider, offer.model_id):
        if not key:
            raise BrokerError("missing_key", "Selected provider credential is unavailable.", 403)
        if still_authorized is not None and not still_authorized():
            raise BrokerError("inference_closed", "Inference grant changed during preflight.", 403)
        return None
    if offer.provider != "openrouter" or offer.model_id != MODEL:
        raise BrokerError(
            "price_unverified",
            "This model is not on the free-tier allowlist. Paid and unverified routes stay closed.",
            403,
        )
    from .policy import verify_catalog

    await verify_catalog(client)
    if still_authorized is not None and not still_authorized():
        raise BrokerError("inference_closed", "Inference grant changed during preflight.", 403)
    return await verify_free_quota(client, key, minimum_requests=minimum_requests)
