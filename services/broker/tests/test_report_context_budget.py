"""Bounded evidence and content-free reservation accounting; no network or model."""

from copy import deepcopy
import json

import pytest

from immortility_broker.contracts import BrokerError
from immortility_broker.ledger import input_upper_bound, prompt_byte_components
from immortility_broker.research import SOURCES, model_evidence


def test_bounded_evidence_keeps_sources_and_local_provenance_unchanged():
    original = {
        "sources": [
            {
                "source_id": ident,
                "title": title,
                "url": url,
                "sha256": "a" * 64,
                "retrieved_at": "2026-11-15T00:00:00Z",
                "excerpt": ("Public permissions evidence — scoped authorization. " * 12)[:650],
                "cache_hit": False,
            }
            for ident, (title, url) in SOURCES.items()
        ],
        "unavailable": [],
        "search_mode": "reviewed-source-catalog",
        "source_trust": "untrusted-data",
    }
    snapshot = deepcopy(original)
    full = model_evidence(original)
    context = model_evidence(original, max_bytes=1600)
    assert len(json.dumps(context, separators=(",", ":")).encode()) <= 1600
    assert context["context_bounded"] is True
    assert [source["source_id"] for source in context["sources"]] == list(SOURCES)
    for source, retained in zip(full["sources"], context["sources"], strict=True):
        assert source["excerpt"].startswith(retained["excerpt"])
        assert len(retained["excerpt"]) >= 80
    assert context["source_trust"] == "untrusted-data"
    assert original == snapshot
    with pytest.raises(BrokerError, match="report_budget_infeasible"):
        model_evidence(original, max_bytes=100)
    assert original == snapshot


def test_prompt_components_match_reservation_without_emitting_content():
    messages = [
        {"role": "system", "content": "PRIVATE_CANARY —"},
        {"role": "user", "content": "question"},
    ]
    plain = prompt_byte_components({"messages": messages})
    assert sum(plain.values()) == input_upper_bound(messages)
    calls = [{"id": "stable:1", "function": {"arguments": "ARGUMENT_CANARY"}}]
    payload = {
        "messages": messages
        + [
            {"role": "assistant", "content": None, "tool_calls": calls},
            {"role": "tool", "content": "RESULT_CANARY"},
        ],
        "tools": [{"SCHEMA_CANARY": "bound"}],
    }
    components = prompt_byte_components(payload)
    expected = (
        64
        + 32 * len(payload["messages"])
        + sum(len((m.get("content") or "").encode()) for m in payload["messages"])
    )
    expected += len(json.dumps(payload["tools"]).encode()) + sum(
        len(json.dumps(m.get("tool_calls", [])).encode()) for m in payload["messages"]
    )
    assert sum(components.values()) == expected
    assert all(type(value) is int and value >= 0 for value in components.values())
    assert "CANARY" not in json.dumps(components)
