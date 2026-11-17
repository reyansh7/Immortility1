"""Small broker tool gateway. No orchestration loop or model-selected executable."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
from dataclasses import dataclass
import re
import time
from datetime import datetime
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .contracts import BrokerError, uid

if TYPE_CHECKING:
    from .store import Store


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Capability(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(default="arithmetic.add.v1", pattern=r"^[a-z][a-z0-9_.]{2,63}$")
    provider: Literal[
        "reviewed-local-mcp",
        "local-python",
        "reviewed-windows-uia",
        "reviewed-public-https",
        "reviewed-report-worker",
    ] = "reviewed-local-mcp"
    classification: Literal[
        "deterministic-read", "window-read", "public-read", "artifact-write"
    ] = "deterministic-read"
    network: bool = False
    irreversible: Literal[False] = False
    max_payload_bytes: int = Field(default=1024, ge=1, le=16000)
    max_output_bytes: int = Field(default=1024, ge=1, le=64000)
    deadline_ms: int = Field(default=10000, ge=1, le=30000)
    concurrency: Literal[1] = 1
    approval: Literal["task-scoped-local-opt-in"] = "task-scoped-local-opt-in"

    @model_validator(mode="after")
    def reviewed_network_contract(self) -> "Capability":
        if self.network != (self.classification == "public-read") or (
            self.classification == "public-read"
        ) != (self.provider == "reviewed-public-https"):
            raise ValueError("Network access requires the reviewed public-read provider contract")
        return self


class AddInput(StrictModel):
    a: int = Field(ge=-(10**9), le=10**9)
    b: int = Field(ge=-(10**9), le=10**9)


class AddOutput(StrictModel):
    result: int = Field(ge=-(2 * 10**9), le=2 * 10**9)


class MultiplyOutput(StrictModel):
    result: int = Field(ge=-(10**18), le=10**18)


def verified_product(left: int, right: int) -> int:
    """Integer product checked by division, so a bad result cannot pass as success."""
    if type(left) is not int or type(right) is not int:
        raise BrokerError("invalid_request", "Bounded integer arguments required.", 400)
    product = left * right
    if right == 0:
        if product != 0:
            raise BrokerError(
                "verification_failed", "Arithmetic result failed independent validation.", 503
            )
    elif product // right != left:
        raise BrokerError(
            "verification_failed", "Arithmetic result failed independent validation.", 503
        )
    return product


def parse_add(content: str) -> AddInput | None:
    match = re.fullmatch(
        r"\s*add\s+(-?\d{1,10})\s+and\s+(-?\d{1,10})\s*[.?]?\s*", content, re.IGNORECASE
    )
    if match is None:
        return None
    try:
        return AddInput(a=int(match[1]), b=int(match[2]))
    except ValueError:
        raise BrokerError(
            "invalid_request", "Arithmetic operands exceed the permitted bounds.", 400
        ) from None


class Grant(StrictModel):
    task_id: str
    session_id: str
    attempt_id: str
    capability: str = "arithmetic.add.v1"
    action_digest: str = ""
    expires: float = Field(ge=0, allow_inf_nan=False)
    calls: int = Field(default=1, ge=1, le=4)


class EmptyInput(StrictModel):
    pass


class ClockOutput(StrictModel):
    timestamp: str = Field(min_length=20, max_length=40)

    @field_validator("timestamp")
    @classmethod
    def valid_timestamp(cls, value: str) -> str:
        if datetime.fromisoformat(value).tzinfo is None:
            raise ValueError("A timezone is required")
        return value


@dataclass(frozen=True)
class Registration:
    manifest: Capability
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    execute: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
    enabled: Callable[[], bool]


def digest(name: str, arguments: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            {"capability": name, "arguments": arguments},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


class Gateway:
    """One registry, authorization point and task-owned dispatcher for local reads.

    Registrations come from reviewed application code, never server descriptions.
    No write/network/command adapter can be represented by the current manifest.
    """

    def __init__(self, store: Store):
        self.store = store
        self.registrations: dict[str, Registration] = {}
        self.grants: dict[str, Grant] = {}
        self.lock = asyncio.Lock()
        self.pending: dict[str, asyncio.Task[Any]] = {}
        self.schemas: dict[str, dict[str, Any]] = {}

    def register(self, registration: Registration) -> None:
        name = registration.manifest.name
        if name in self.registrations:
            raise ValueError("Capability identifiers must be unique")
        self.registrations[name] = registration
        self.schemas[name] = {
            "manifest": registration.manifest.model_dump(mode="json"),
            "input_schema": registration.input_model.model_json_schema(),
            "output_schema": registration.output_model.model_json_schema(),
        }

    def discover(self, names: tuple[str, ...], maximum: int = 4) -> list[dict[str, Any]]:
        # The broker selects relevant identifiers; external descriptions cannot
        # select permissions or register additional code. Return independent data.
        chosen = [
            name
            for name in names
            if name in self.registrations and self.registrations[name].enabled()
        ][: max(0, min(maximum, 4))]
        return [json.loads(json.dumps(self.schemas[name])) for name in chosen]

    def _registration(self, name: str) -> Registration:
        entry = self.registrations.get(name)
        if entry is None or not entry.enabled():
            raise BrokerError("tool_denied", "Capability is unregistered or disabled.", 403)
        return entry

    def _arguments(self, entry: Registration, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if (
                len(json.dumps(arguments, allow_nan=False).encode())
                > entry.manifest.max_payload_bytes
            ):
                raise BrokerError(
                    "input_limit", "Capability input exceeds its manifest limit.", 413
                )
            return dict(entry.input_model.model_validate(arguments).model_dump(mode="json"))
        except (ValueError, TypeError):
            raise BrokerError(
                "invalid_request", "Capability arguments do not match the approved schema.", 400
            ) from None

    def issue(self, grant: Grant, arguments: dict[str, Any], *, enabled: bool = False) -> str:
        entry = self._registration(grant.capability)
        task = self.store.get(grant.task_id)
        if (
            not enabled
            or task["session_id"] != grant.session_id
            or task["status"] != "running"
            or grant.expires <= time.monotonic()
            or not self.store.ledger.owns_attempt(grant.attempt_id, grant.task_id)
        ):
            raise BrokerError("tool_denied", "No matching live local capability scope.", 403)
        clean = self._arguments(entry, arguments)
        token = uid()
        self.grants[token] = grant.model_copy(
            update={
                "action_digest": digest(grant.capability, clean),
                "expires": min(grant.expires, time.monotonic() + entry.manifest.deadline_ms / 1000),
            }
        )
        return token

    async def revoke(self, task_id: str) -> None:
        self.grants = {key: grant for key, grant in self.grants.items() if grant.task_id != task_id}
        pending = self.pending.get(task_id)
        if pending is not None:
            pending.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pending

    async def invoke(
        self, token: str, name: str, arguments: dict[str, Any], *, enabled: bool = False
    ) -> dict[str, Any]:
        grant = self.grants.get(token)
        if grant is None:
            raise BrokerError("tool_denied", "Capability grant was revoked or consumed.", 403)
        try:
            async with asyncio.timeout_at(grant.expires):
                return await self._invoke(token, name, arguments, enabled=enabled)
        except TimeoutError:
            raise BrokerError("timeout", "Capability grant deadline expired.", 503) from None

    async def _invoke(
        self, token: str, name: str, arguments: dict[str, Any], *, enabled: bool = False
    ) -> dict[str, Any]:
        async with self.lock:
            grant = self.grants.get(token)
            entry = self._registration(name)
            clean = self._arguments(entry, arguments)
            if (
                grant is None
                or not enabled
                or grant.capability != name
                or grant.expires <= time.monotonic()
                or self.store.get(grant.task_id)["status"] != "running"
                or digest(name, clean) != grant.action_digest
            ):
                raise BrokerError(
                    "tool_denied", "Capability arguments, scope or lifetime changed.", 403
                )
            if grant.calls == 1:
                self.grants.pop(token)
            else:
                self.grants[token] = grant.model_copy(update={"calls": grant.calls - 1})
            self.store.event(
                grant.task_id, "tool.started", {"name": name, "attempt_id": grant.attempt_id}
            )

            async def dispatch() -> dict[str, Any]:
                # Recheck immediately before dispatch after any controller wait.
                self._registration(name)
                return await entry.execute(clean)

            operation = asyncio.create_task(dispatch())
            self.pending[grant.task_id] = operation
            status, code = "error", "tool_failed"
            try:
                async with asyncio.timeout(entry.manifest.deadline_ms / 1000):
                    try:
                        result = entry.output_model.model_validate(await operation)
                    except (ValueError, TypeError):
                        raise BrokerError(
                            "tool_output_invalid",
                            "Capability output failed schema validation.",
                            503,
                        ) from None
                    if len(result.model_dump_json().encode()) > entry.manifest.max_output_bytes:
                        raise BrokerError(
                            "output_limit", "Capability output exceeds its manifest limit.", 413
                        )
                status, code = "ok", "ok"
                return dict(result.model_dump(mode="json"))
            except asyncio.CancelledError:
                code = "cancelled"
                raise
            except TimeoutError:
                code = "timeout"
                raise BrokerError("timeout", "Capability deadline expired.", 503) from None
            except BrokerError as error:
                code = error.code
                raise
            except Exception:
                raise BrokerError(
                    "tool_failed", "Capability failed; details were redacted.", 503
                ) from None
            finally:
                self.pending.pop(grant.task_id, None)
                self.store.event(
                    grant.task_id,
                    "tool.completed",
                    {"name": name, "status": status, "code": code, "attempt_id": grant.attempt_id},
                )
