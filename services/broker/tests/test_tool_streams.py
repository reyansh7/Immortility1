"""Provider protocol fixtures, never live inference or provider-generated permissions."""

import json

import pytest

from immortility_broker.agent_bridge import (
    PROVIDER_TOOL_NAME,
    TOOL_NAME,
    bridge_messages,
    validate_calls,
    validate_stream,
)
from immortility_broker.contracts import BrokerError


def stream(*fragments, finish="tool_calls"):
    return [
        *(
            {"choices": [{"index": 0, "delta": {"tool_calls": [fragment]}}]}
            for fragment in fragments
        ),
        {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
        {"choices": [], "usage": {"prompt_tokens": 15, "completion_tokens": 20}},
    ]


def fragment(arguments="", *, ident="call.provider:0", name=TOOL_NAME):
    return {
        "index": 0,
        "id": ident,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


@pytest.mark.parametrize("repeat_metadata", [False, True])
def test_standard_deltas_and_repeated_metadata_are_canonicalized_before_hermes(repeat_metadata):
    body = json.dumps({"capability": "clock.now.v1", "arguments": {}})
    first = fragment(body[:20])
    second = (
        fragment(body[20:])
        if repeat_metadata
        else {
            "index": 0,
            "id": None,
            "type": None,
            "function": {"name": None, "arguments": body[20:]},
        }
    )
    original = stream(first, second)
    normalized = validate_stream(original, ["clock.now.v1"])
    calls = normalized[-2]["choices"][0]["delta"]["tool_calls"]
    assert len(calls) == 1 and calls[0]["function"]["name"] == TOOL_NAME
    assert calls[0]["id"] == "call.provider:0"
    assert json.loads(calls[0]["function"]["arguments"]) == json.loads(body)
    assert "tool_calls" not in normalized[0]["choices"][0]["delta"]
    assert original[0]["choices"][0]["delta"]["tool_calls"]  # no mutation
    assert normalized[-1]["usage"] == original[-1]["usage"]
    exchange = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{key: value for key, value in calls[0].items() if key != "index"}],
        },
        {"role": "tool", "tool_call_id": "call.provider:0", "content": "bounded fixture"},
    ]
    assert bridge_messages(exchange, ["clock.now.v1"])[-1]["tool_call_id"] == "call.provider:0"


def test_short_provider_name_is_canonicalized_and_a_misspelling_is_denied():
    body = json.dumps({"capability": "clock.now.v1", "arguments": {}})
    normalized = validate_stream(
        stream(fragment(body, name=PROVIDER_TOOL_NAME)), ["clock.now.v1"]
    )
    call = normalized[-2]["choices"][0]["delta"]["tool_calls"][0]
    assert call["function"]["name"] == TOOL_NAME
    with pytest.raises(BrokerError, match="tool_denied"):
        validate_stream(
            stream(fragment(body, name="mcp__immortality__execute")), ["clock.now.v1"]
        )


@pytest.mark.parametrize(
    "arguments",
    [
        '{"capability":"clock.now.v1","capability":"terminal","arguments":{}}',
        '{"capability":"clock.now.v1","arguments":{"x":1,"x":2}}',
        '{"capability":"clock.now.v1","arguments":{"value":NaN}}',
        '{"capability":"clock.now.v1","arguments":{"value":1e999}}',
        '{"capability":"clock.now.v1","arguments":{},"permission":"all"}',
        '{"capability":"terminal","arguments":{}}',
        '{"capability":"clock.now.v1","arguments":[]}',
    ],
)
def test_ambiguous_or_unauthorized_proposals_are_not_repaired(arguments):
    with pytest.raises(BrokerError):
        validate_stream(stream(fragment(arguments)), ["clock.now.v1"])


@pytest.mark.parametrize(
    "chunks",
    [
        [{"choices": None}],
        [{"choices": [{}]}],
        [{"choices": [{"delta": []}]}],
        [{"choices": [{"index": False, "delta": {}}]}],
        [{"choices": [{"delta": {"tool_calls": {}}}]}],
        stream({"index": True, "function": {}}),
        stream({"index": 0, "function": {"arguments": {"capability": "clock.now.v1"}}}),
        stream(fragment("{}"), fragment("{}", ident="different")),
        stream(fragment("{}", name="terminal")),
        stream(fragment("{}"), finish="stop"),
        stream(fragment("{}"), finish="length"),
        stream(fragment("{}"))[:-2],
        [{"choices": [{"index": 0, "delta": {}}, {"index": 1, "delta": {}}]}],
    ],
)
def test_malformed_streams_fail_with_safe_structured_errors(chunks):
    with pytest.raises(BrokerError) as captured:
        validate_stream(chunks, ["clock.now.v1"])
    assert captured.value.code == "tool_denied"
    assert captured.value.diagnostic in {"stream_shape", "tool_name", "proposal_schema"}


def test_opaque_ids_remain_exact_bounded_noncontrol_data():
    body = json.dumps({"capability": "clock.now.v1", "arguments": {}})
    for ident in ["", "x" * 129, "line\nbreak", "space here", "\x1b[31m"]:
        with pytest.raises(BrokerError):
            validate_stream(stream(fragment(body, ident=ident)), ["clock.now.v1"])
    with pytest.raises(BrokerError):
        validate_calls(
            [
                {
                    "id": "valid",
                    "type": "function",
                    "function": {"name": "mcp__other__execute", "arguments": body},
                }
            ],
            ["clock.now.v1"],
        )
