"""Real broker relay regression: transport envelopes are not model output."""

from provider_fixtures import free_account_response

import json

import httpx
from pydantic import SecretStr
import pytest

from immortility_broker.agent_bridge import TOOL_NAME
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import TaskRequest
from immortility_broker.policy import MODEL


def provider_chunks(count):
    chunks = []
    for _ in range(count):
        chunks.append(
            {
                "id": "provider-envelope-" * 5,
                "model": "fixture-model",
                "system_fingerprint": "repeated-transport-metadata-" * 5,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "x", "reasoning": "PRIVATE_REASONING_CANARY" * 4},
                        "finish_reason": None,
                    }
                ],
            }
        )
    chunks.append(
        {
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "fixture-call",
                                "type": "function",
                                "function": {
                                    "name": TOOL_NAME,
                                    "arguments": json.dumps(
                                        {"capability": "clock.now.v1", "arguments": {}}
                                    ),
                                },
                            }
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
    )
    chunks.append({"choices": [], "usage": {"prompt_tokens": 15, "completion_tokens": 20}})
    return chunks


@pytest.mark.parametrize(
    "count,echo_key", [(1, False), (100, False), (600, False), (2048, False), (1, True)]
)
async def test_many_valid_small_chunks_reach_hermes_without_envelope_overflow(
    tmp_path, count, echo_key
):
    chunks = provider_chunks(count)
    if echo_key:
        chunks[0]["model"] = "synthetic-offline-credential"
    wire = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"
    if count >= 600:
        assert len(wire.encode()) > 128000

    def provider(request):
        if request.url.path == "/api/v1/key":
            return free_account_response(request)
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": MODEL, "pricing": {"prompt": "0", "completion": "0"}}]}
            )
        return httpx.Response(200, text=wire, headers={"content-type": "text/event-stream"})

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        openrouter_fallback_enabled=True,
        openrouter_api_key=SecretStr("synthetic-offline-credential"),
    )
    app = create_app(settings, "x" * 40, client=upstream)
    store, engine = app.state.store, app.state.engine
    sid = store.session()["id"]
    task, _ = store.create(
        TaskRequest(
            session_id=sid,
            request_id="many-chunks",
            content="Synthetic clock request",
            cloud_consent=True,
            allowed_capabilities=["clock.now.v1"],
        )
    )
    tid = task["task_id"]
    engine.open_grant(tid, "fast", 90)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + engine.inference_key},
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": "Synthetic public clock task"}],
                },
            )
            assert response.status_code == 200
            assert engine.provider_error is None, getattr(engine.provider_error, "diagnostic", None)
            assert "PRIVATE_REASONING_CANARY" not in response.text
            assert "synthetic-offline-credential" not in response.text
            assert TOOL_NAME in response.text
            assert response.text.endswith("data: [DONE]\n\n")
            assert store.ledger.summary(tid)["charged_tokens"] == 35
            notices = [
                json.loads(row[0])["data"]
                for row in store.db.execute("SELECT body FROM events WHERE task_id=?", (tid,))
            ]
            diagnostic = next(
                value for value in notices if value.get("name") == "provider_call_diagnostics"
            )
            assert (
                diagnostic["termination"] == "completed" and diagnostic["accepted_proposals"] == 1
            )
            assert diagnostic["reasoning_events_discarded"] == count
            assert diagnostic["semantic_bytes"] < count + 200
            assert diagnostic["usage_status"] == "reported"
            assert "PRIVATE_REASONING_CANARY" not in json.dumps(notices)
            assert "synthetic-offline-credential" not in json.dumps(notices)
            assert diagnostic["served_model"] == (None if echo_key else "fixture-model")
    finally:
        await upstream.aclose()
        store.db.close()


@pytest.mark.parametrize("field,size", [("content", 128001), ("arguments", 16001)])
def test_actual_semantic_limits_remain_enforced(field, size):
    from immortility_broker.semantic_stream import SemanticToolStream
    from immortility_broker.contracts import BrokerError

    stream = SemanticToolStream()
    delta = (
        {"content": "x" * size}
        if field == "content"
        else {"tool_calls": [{"index": 0, "function": {"arguments": "x" * size}}]}
    )
    with pytest.raises(BrokerError) as issue:
        stream.add({"choices": [{"delta": delta}]})
    assert issue.value.diagnostic == "bridge_output_limit"


def test_fragment_order_and_distinct_call_ids_are_preserved_and_changed_ids_denied():
    from immortility_broker.semantic_stream import SemanticToolStream
    from immortility_broker.contracts import BrokerError

    stream = SemanticToolStream()
    body = json.dumps({"capability": "clock.now.v1", "arguments": {}})
    for fragment_index in range(len(body)):
        stream.add(
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "index": i,
                                    "id": f"call:{i}",
                                    "type": "function",
                                    "function": {
                                        "name": TOOL_NAME,
                                        "arguments": body[fragment_index],
                                    },
                                }
                                for i in range(2)
                            ],
                        },
                    }
                ]
            }
        )
    stream.add({"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]})
    normalized = stream.normalized(["clock.now.v1"], None)
    calls = normalized[-1]["choices"][0]["delta"]["tool_calls"]
    assert [c["id"] for c in calls] == ["call:0", "call:1"]
    assert all(json.loads(c["function"]["arguments"]) == json.loads(body) for c in calls)
    invalid = SemanticToolStream()
    invalid.add({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "first"}]}}]})
    with pytest.raises(BrokerError):
        invalid.add({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "changed"}]}}]})


async def test_infeasible_report_headroom_blocks_before_catalog_or_model_request(tmp_path):
    requests = []

    def forbidden(request):
        requests.append(request)
        pytest.fail("An infeasible report must not contact a provider, even for preflight")

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(forbidden))
    app = create_app(
        Settings(
            _env_file=None,
            data_dir=tmp_path,
            openrouter_fallback_enabled=True,
            openrouter_api_key=SecretStr("synthetic-offline-credential"),
        ),
        "x" * 40,
        client=upstream,
    )
    store, engine = app.state.store, app.state.engine
    sid = store.session()["id"]
    task, _ = store.create(
        TaskRequest(
            session_id=sid,
            request_id="infeasible-report",
            content="Synthetic report",
            cloud_consent=True,
            allowed_capabilities=["report.create.v1"],
        )
    )
    engine.open_grant(task["task_id"], "standard", 90)
    engine.token_cap = 1000
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + engine.inference_key},
                json={"model": MODEL, "messages": [{"role": "user", "content": "Report"}]},
            )
        assert (
            response.status_code == 403
            and response.json()["error"]["code"] == "report_budget_infeasible"
        )
        assert not requests and engine.calls == 0
        assert store.ledger.summary(task["task_id"])["calls"] == 0
    finally:
        await upstream.aclose()
        store.db.close()
