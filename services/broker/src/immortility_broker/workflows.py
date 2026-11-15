"""Typed, bounded read-only workflow journal in the broker's authoritative SQLite.

There is no scheduler, agent loop, command executor or separate lifecycle owner.
The existing Engine admits, dispatches, cancels and recovers these tasks.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import Field, JsonValue, field_validator, model_validator

from .capabilities import Gateway, StrictModel
from .contracts import BrokerError

if TYPE_CHECKING:
    from .store import Store


class OutputReference(StrictModel):
    step_id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,31}$")
    field: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")


class WorkflowStep(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,31}$")
    capability: str = Field(min_length=3, max_length=64)
    arguments: dict[str, JsonValue] = Field(default_factory=dict, max_length=16)
    depends_on: list[str] = Field(default_factory=list, max_length=16)
    bindings: dict[str, OutputReference] = Field(default_factory=dict, max_length=16)


class WorkflowRequest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    session_id: str = Field(min_length=1, max_length=64)
    request_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=160)
    steps: list[WorkflowStep] = Field(min_length=1, max_length=16)
    deadline_seconds: int = Field(default=60, ge=1, le=3600)
    max_retries: int = Field(default=0, ge=0, le=2)
    resume_on_restart: bool = False
    local_read_consent: Literal[True]
    no_cloud: Literal[True] = True

    @field_validator("local_read_consent", "no_cloud", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit local-only authorization required")
        return value

    @model_validator(mode="after")
    def valid_graph(self) -> Self:
        names = {step.id for step in self.steps}
        if len(names) != len(self.steps):
            raise ValueError("Step identifiers must be unique")
        for step in self.steps:
            if not set(step.depends_on) <= names or step.id in step.depends_on:
                raise ValueError("Unknown or self dependency")
            if set(step.arguments) & set(step.bindings):
                raise ValueError("A bound argument cannot also be literal")
            if any(
                reference.step_id not in step.depends_on for reference in step.bindings.values()
            ):
                raise ValueError("Every reference must be an explicit dependency")
        self.ordered_steps()
        return self

    def ordered_steps(self) -> list[WorkflowStep]:
        done: set[str] = set()
        ordered: list[WorkflowStep] = []
        while len(ordered) != len(self.steps):
            ready = [
                step for step in self.steps if step.id not in done and set(step.depends_on) <= done
            ]
            if not ready:
                raise ValueError("Workflow dependency cycle")
            ordered.extend(ready)
            done.update(step.id for step in ready)
        return ordered


def checksum(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def workflow_identity(session_id: str, request_id: str) -> str:
    return "workflow-" + hashlib.sha256((session_id + "\0" + request_id).encode()).hexdigest()[:40]


class WorkflowJournal:
    def __init__(self, store: Store):
        self.store = store

    def existing(self, request: WorkflowRequest) -> dict[str, Any] | None:
        row = self.store.db.execute(
            "SELECT request,body FROM tasks WHERE request_id=?",
            (workflow_identity(request.session_id, request.request_id),),
        ).fetchone()
        if row is None:
            return None
        try:
            if (
                WorkflowRequest.model_validate_json(row["request"]).model_dump()
                != request.model_dump()
            ):
                raise ValueError
            return dict(json.loads(row["body"]))
        except ValueError:
            raise BrokerError(
                "idempotency_conflict", "Workflow request ID already has different content.", 409
            ) from None

    def validate(self, request: WorkflowRequest, gateway: Gateway) -> dict[str, str]:
        selected: dict[str, str] = {}
        by_id = {step.id: step for step in request.steps}
        for step in request.ordered_steps():
            descriptors = gateway.discover((step.capability,))
            if not descriptors:
                raise BrokerError(
                    "tool_denied", "Workflow capability is unavailable or disabled.", 403
                )
            descriptor = descriptors[0]
            # Current registry cannot represent network/write/irreversible tools.
            if (
                descriptor["manifest"]["network"]
                or descriptor["manifest"]["irreversible"]
                or descriptor["manifest"]["classification"] != "deterministic-read"
            ):
                raise BrokerError(
                    "tool_denied", "Only registered local read operations may resume.", 403
                )
            arguments: dict[str, Any] = dict(step.arguments)
            for target, reference in step.bindings.items():
                source = (
                    gateway.schemas[by_id[reference.step_id].capability]["output_schema"]
                    .get("properties", {})
                    .get(reference.field)
                )
                destination = descriptor["input_schema"].get("properties", {}).get(target)
                if (
                    not source
                    or not destination
                    or source.get("type") not in {"integer", "string"}
                    or source.get("type") != destination.get("type")
                ):
                    raise BrokerError(
                        "invalid_request", "Workflow binding schemas are incompatible.", 400
                    )
                arguments[target] = {"integer": 0, "string": "2026-01-01T00:00:00+00:00"}.get(
                    source.get("type")
                )
            try:
                gateway.registrations[step.capability].input_model.model_validate(arguments)
            except ValueError:
                raise BrokerError(
                    "invalid_request", "Workflow arguments fail capability validation.", 400
                ) from None
            selected[step.capability] = checksum(descriptor)
        return selected

    def insert(self, task_id: str, request: WorkflowRequest, manifests: dict[str, str]) -> None:
        # Called inside Store's atomic task-create transaction.
        body = {
            "request": request.model_dump(mode="json"),
            "expires_at": time.time() + request.deadline_seconds,
            "manifests": manifests,
        }
        self.store.db.execute(
            "INSERT INTO workflows VALUES(?,?,?,?)",
            (task_id, "queued", json.dumps(body), checksum(body)),
        )
        self.store.db.executemany(
            "INSERT INTO workflow_steps(task_id,step_id,status,attempts) VALUES(?,?,?,0)",
            [(task_id, step.id, "pending") for step in request.steps],
        )

    def load(self, task_id: str) -> tuple[WorkflowRequest, dict[str, Any]]:
        row = self.store.db.execute(
            "SELECT body,digest FROM workflows WHERE task_id=?", (task_id,)
        ).fetchone()
        if row is None:
            raise BrokerError("not_found", "Workflow not found.", 404)
        try:
            body = json.loads(row["body"])
            if checksum(body) != row["digest"]:
                raise ValueError
            request = WorkflowRequest.model_validate(body["request"])
            expires = body["expires_at"]
            if type(expires) not in {int, float} or not 0 < expires < float("inf"):
                raise ValueError
            return request, dict(body)
        except (ValueError, KeyError, TypeError):
            raise BrokerError(
                "checkpoint_corrupt", "Workflow definition failed integrity validation.", 409
            ) from None

    def exists(self, task_id: str) -> bool:
        return (
            self.store.db.execute("SELECT 1 FROM workflows WHERE task_id=?", (task_id,)).fetchone()
            is not None
        )

    def next_task(self) -> str | None:
        rows = self.store.db.execute(
            "SELECT w.task_id,t.body FROM workflows w JOIN tasks t ON t.id=w.task_id WHERE w.status='queued' ORDER BY w.rowid"
        ).fetchall()
        return next(
            (str(row["task_id"]) for row in rows if json.loads(row["body"])["status"] == "queued"),
            None,
        )

    def completed(
        self, task_id: str, gateway: Gateway, request: WorkflowRequest
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        steps = {step.id: step for step in request.steps}
        for row in self.store.db.execute(
            "SELECT * FROM workflow_steps WHERE task_id=? AND status='completed'", (task_id,)
        ):
            try:
                data = json.loads(row["result"])
                if checksum(data) != row["digest"]:
                    raise ValueError
                output = gateway.registrations[
                    steps[row["step_id"]].capability
                ].output_model.model_validate(data)
                result[row["step_id"]] = dict(output.model_dump(mode="json"))
            except (ValueError, KeyError, TypeError):
                raise BrokerError(
                    "checkpoint_corrupt", "Workflow result checkpoint failed validation.", 409
                ) from None
        return result

    def begin_step(self, task_id: str, step_id: str, maximum: int) -> None:
        with self.store.db:
            changed = self.store.db.execute(
                "UPDATE workflow_steps SET status='running',attempts=attempts+1 WHERE task_id=? AND step_id=? AND attempts<? AND status!='completed'",
                (task_id, step_id, maximum),
            ).rowcount
            if changed != 1:
                raise BrokerError(
                    "retry_exhausted", "Workflow step retry allowance exhausted.", 409
                )

    def checkpoint(self, task_id: str, step_id: str, output: dict[str, Any]) -> None:
        with self.store.db:
            self.store.db.execute(
                "UPDATE workflow_steps SET status='completed',result=?,digest=?,error_code=NULL WHERE task_id=? AND step_id=?",
                (json.dumps(output), checksum(output), task_id, step_id),
            )

    def step_error(self, task_id: str, step_id: str, code: str) -> int:
        with self.store.db:
            self.store.db.execute(
                "UPDATE workflow_steps SET status='pending',error_code=? WHERE task_id=? AND step_id=?",
                (code, task_id, step_id),
            )
        return int(
            self.store.db.execute(
                "SELECT attempts FROM workflow_steps WHERE task_id=? AND step_id=?",
                (task_id, step_id),
            ).fetchone()[0]
        )

    def status(self, task_id: str, status: str) -> None:
        with self.store.db:
            self.store.db.execute(
                "UPDATE workflows SET status=? WHERE task_id=?", (status, task_id)
            )

    def view(self, task_id: str) -> dict[str, Any]:
        request, body = self.load(task_id)
        rows = [
            dict(row)
            for row in self.store.db.execute(
                "SELECT step_id,status,attempts,error_code FROM workflow_steps WHERE task_id=?",
                (task_id,),
            )
        ]
        return {
            "schema_version": "1.0",
            "task": self.store.get(task_id),
            "definition": request.model_dump(mode="json"),
            "expires_at": body["expires_at"],
            "steps": rows,
        }
