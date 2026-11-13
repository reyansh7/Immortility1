"""Versioned, content-free trajectory view over committed broker events."""

from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .contracts import validate
from .store import Store


def execution_trace(store: Store, task_id: str) -> dict[str, Any]:
    task = store.get(task_id)
    events = []
    cursor = 0
    while batch := store.events(task_id, cursor):
        events.extend(batch)
        cursor = batch[-1]["sequence"]
    transitions = [
        {"state": event["data"]["status"], "timestamp": event["timestamp"]}
        for event in events
        if event["type"] == "task.state"
    ]
    start = next(
        (entry["timestamp"] for entry in transitions if entry["state"] == "running"),
        task["created_at"],
    )
    last = transitions[-1]["timestamp"] if transitions else task["created_at"]
    duration = max(
        0.0, (datetime.fromisoformat(last) - datetime.fromisoformat(start)).total_seconds() * 1000
    )
    tool_calls = [
        {"name": str(event["data"].get("name", ""))[:32], "status": event["data"].get("status")}
        for event in events
        if event["type"] == "tool.completed"
        and event["data"].get("status") in {"ok", "denied", "error"}
        and isinstance(event["data"].get("name"), str)
        and event["data"].get("name")
    ][:16]
    trace = {
        "schema_version": "1.0",
        "task_id": task_id,
        "attempt_id": str(uuid5(NAMESPACE_URL, task_id + ":attempt:1")),
        "agent": {"runtime": "hermes", "route": "openrouter/free"},
        "modality": task["input"].get("source", "text"),
        "transitions": transitions,
        "duration_ms": duration,
        "outcome": task["status"],
        "failure_class": task.get("error", {}).get("code"),
        "delegations": [
            {"role": event["data"].get("role", ""), "status": event["data"].get("status", "")}
            for event in events
            if event["type"] in {"agent.started", "agent.completed"}
            and event["data"].get("role") in {"research", "coding", "review"}
        ],
        "tools": {"status": "authorized" if tool_calls else "disabled", "calls": tool_calls},
        "artifact_refs": [],
        "verification_evidence": [],
        "completion_evidence": {
            "streamed_chunks": sum(e["type"] == "message.delta" for e in events),
            "independent_verifier": False,
        },
    }
    validate("execution-trace", trace)
    return trace
