"""Opt-in native tool boundary; default chat remains tool-free."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from immortility_broker.agent_bridge import (
    TOOL_NAME,
    bridge_messages,
    tool_spec,
    validate_calls,
    validate_stream,
)
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError, TaskRequest
from immortility_broker.hermes import stream_matches
from immortility_broker.policy import MODEL, inference_payload
from test_workspace import AUTH, TOKEN


def call(capability="clock.now.v1", name=TOOL_NAME):
    return {
        "id": "fixture",
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps({"capability": capability, "arguments": {}}),
        },
    }


@pytest.mark.parametrize(
    "capability,name",
    [
        ("terminal", TOOL_NAME),
        ("window.inspect.v1", TOOL_NAME),
        ("clock.now.v1", "terminal"),
        ("clock.now.v1", "mcp__other__execute"),
    ],
)
def test_unknown_or_sensitive_tools_never_cross_provider_boundary(capability, name):
    with pytest.raises(BrokerError, match="tool_denied"):
        validate_calls([call(capability, name)], ["clock.now.v1"])


def test_opt_in_payload_uses_broker_schema_and_requires_matching_results():
    raw = {
        "model": MODEL,
        "tools": [tool_spec(["clock.now.v1"])],
        "messages": [{"role": "user", "content": "Public fixture"}],
    }
    with pytest.raises(BrokerError):
        inference_payload(raw)
    raw["tools"][0]["function"]["parameters"] = {"secret": "malicious schema"}
    result = inference_payload(raw, approved_capabilities=["clock.now.v1"])
    assert result["tools"] == [tool_spec(["clock.now.v1"], provider=True)]
    assert result["tools"][0]["function"]["name"] == "execute"
    assert "malicious" not in json.dumps(result)
    exchange = [
        *raw["messages"],
        {"role": "assistant", "content": None, "tool_calls": [call()]},
        {"role": "tool", "tool_call_id": "fixture", "content": '{"timestamp":"public fixture"}'},
    ]
    assert bridge_messages(exchange, ["clock.now.v1"])[-1]["tool_call_id"] == "fixture"
    for invalid in [
        exchange[:-1],
        [exchange[-1]],
        [*exchange[:-1], {**exchange[-1], "tool_call_id": "foreign"}],
    ]:
        with pytest.raises(BrokerError):
            bridge_messages(invalid, ["clock.now.v1"])


def test_native_stream_checks_all_fragments_before_release():
    chunks = [
        {"choices": [{"delta": {"tool_calls": [{"index": 0, **call()}]}}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
    ]
    validate_stream(chunks, ["clock.now.v1"])
    with pytest.raises(BrokerError):
        validate_stream(chunks[:-1], ["clock.now.v1"])
    chunks[0]["choices"][0]["delta"]["tool_calls"][0]["function"]["name"] = "terminal"
    with pytest.raises(BrokerError):
        validate_stream(chunks, ["clock.now.v1"])


def test_task_scope_is_strict_and_does_not_enable_other_capabilities():
    body = {"session_id": "s", "request_id": "r", "content": "fixture", "cloud_consent": True}
    assert not TaskRequest(**body).allowed_capabilities
    for allowed in [["terminal"], ["clock.now.v1", "clock.now.v1"], ["window.inspect.v1"]]:
        with pytest.raises(ValidationError):
            TaskRequest(**body, allowed_capabilities=allowed)


def test_rejected_provider_calls_keep_only_safe_diagnostic_categories():
    invalid = call(name="private-raw-proposal-canary")
    with pytest.raises(BrokerError) as captured:
        validate_calls([invalid], ["clock.now.v1"])
    assert captured.value.diagnostic == "tool_name"
    assert "private-raw-proposal-canary" not in captured.value.message
    invalid = call()
    invalid["id"] = "unsafe identity canary"
    with pytest.raises(BrokerError) as captured:
        validate_calls([invalid], ["clock.now.v1"])
    assert captured.value.diagnostic == "call_identity"


def test_renderer_separator_acceptance_is_scoped_and_exact():
    assert stream_matches("\n\nFinal", "Final", broker_tools=True)
    assert stream_matches("Checking.\n\nFinal", "Final", broker_tools=True)
    assert not stream_matches("\n\nFinal", "Final")
    assert not stream_matches("Different Final", "Final", broker_tools=True)
    assert not stream_matches("Final", "Different", broker_tools=True)


async def test_gateway_requires_current_private_grant_and_cancels_inflight_tool(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path, local_tools_enabled=True), TOKEN)
    engine, store = app.state.engine, app.state.store
    entered = asyncio.Event()
    stopped = asyncio.Event()

    async def slow(_):
        entered.set()
        try:
            await asyncio.sleep(60)
        finally:
            stopped.set()

    try:
        sid = store.session()["id"]
        task, _ = store.create(
            TaskRequest(
                session_id=sid,
                request_id="scope",
                content="fixture",
                cloud_consent=True,
                allowed_capabilities=["clock.now.v1"],
            )
        )
        tid = task["task_id"]
        store.state(tid, "queued")
        store.state(tid, "running")
        engine.open_grant(tid, "standard", 90)
        key = engine.inference_key
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            path = "/inference/v1/capabilities/call"
            body = {"capability": "clock.now.v1", "arguments": {}}
            assert (await client.post(path, headers=AUTH, json=body)).status_code == 401
            auth = {"Authorization": "Bearer " + key}
            assert (
                await client.post(
                    path, headers=auth, json={**body, "capability": "arithmetic.add.v1"}
                )
            ).status_code == 403
            assert (
                await client.post(
                    path, headers=auth, json={**body, "arguments": {"command": "forbidden"}}
                )
            ).status_code == 400
            engine.gateway.registrations["clock.now.v1"] = replace(
                engine.gateway.registrations["clock.now.v1"], execute=slow
            )
            operation = asyncio.create_task(client.post(path, headers=auth, json=body))
            await asyncio.wait_for(entered.wait(), 2)
            await engine.cancel(tid)
            response = await operation
            assert response.status_code == 409
            assert response.json()["error"]["code"] == "tool_cancelled"
            assert stopped.is_set() and not engine.gateway.pending and not engine.gateway.grants
            engine.inference_key = "rotated"
            assert (await client.post(path, headers=auth, json=body)).status_code == 401
    finally:
        store.db.close()


def test_disabled_capability_is_rejected_before_task_storage(tmp_path):
    from fastapi.testclient import TestClient

    app = create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN)
    with TestClient(app) as client:
        sid = client.post("/v1/sessions", headers=AUTH).json()["id"]
        response = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": sid,
                "request_id": "denied",
                "content": "fixture",
                "cloud_consent": True,
                "allowed_capabilities": ["clock.now.v1"],
            },
        )
        assert response.status_code == 403
        assert not app.state.store.tasks(sid)
