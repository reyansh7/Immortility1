"""Milestone 1.7: confirmed stops, run-event replay, approvals and correlation ids.

Everything here is offline. The fake gateway is a FastAPI app on an in-memory transport,
and the model is the simulated fixture. No provider is called.
"""

import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError, TaskRequest
from immortility_broker.hermes_gateway import GatewayRuntime, WarmGateway, run_phase
from immortility_broker.policy import MODEL

KEY = "local-test-key"


def frame(seq, event):
    return f"id: {seq}\ndata: {json.dumps({**event, 'seq': seq})}\n\n"


class FakeHermes:
    """Just enough of Hermes 0.23.2's /v1/runs surface for lifecycle tests."""

    def __init__(self):
        self.app = FastAPI()
        self.statuses = {}
        self.stops = []
        self.approvals = []
        self.connections = []
        self.script = {}
        self.stop_polls_before_cancel = 2
        self.never_confirm = False
        self.polls = {}
        app = self.app

        @app.get("/health")
        def health():
            return {"status": "ok"}

        @app.post("/v1/runs")
        def start(body: dict):
            run_id = "run_" + str(len(self.statuses) + 1)
            self.statuses[run_id] = "running"
            return JSONResponse({"run_id": run_id, "status": "queued"}, status_code=202)

        @app.get("/v1/runs/{run_id}/events")
        def events(run_id: str, request: Request):
            last = request.headers.get("last-event-id")
            self.connections.append(last)
            attempt = len([c for c in self.connections])
            frames = self.script[run_id](attempt, last)
            body = iter(frames) if isinstance(frames, list) else frames
            return StreamingResponse(body, media_type="text/event-stream")

        @app.get("/v1/runs/{run_id}")
        def status(run_id: str):
            self.polls[run_id] = self.polls.get(run_id, 0) + 1
            current = self.statuses[run_id]
            if (
                current == "stopping"
                and not self.never_confirm
                and self.polls[run_id] > self.stop_polls_before_cancel
            ):
                self.statuses[run_id] = current = "cancelled"
            return {"run_id": run_id, "status": current}

        @app.post("/v1/runs/{run_id}/stop")
        def stop(run_id: str):
            self.stops.append(run_id)
            if self.statuses[run_id] not in {"completed", "failed", "cancelled"}:
                self.statuses[run_id] = "stopping"
            return {"run_id": run_id, "status": "stopping"}

        @app.post("/v1/runs/{run_id}/approval")
        def approval(run_id: str, body: dict):
            self.approvals.append((run_id, body))
            return {"resolved": 1}


def client_for(fake):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=fake.app), base_url="http://hermes")


def test_run_phase_never_treats_a_stop_request_as_cancelled():
    assert run_phase("stopping") == "stopping"
    assert run_phase("waiting_for_approval") == "awaiting_approval"
    assert run_phase("queued") == "running"
    assert run_phase("interrupted") == "recovery_required"
    assert run_phase("made-up") == "recovery_required"
    assert run_phase("cancelled") == "cancelled"


async def test_reconnect_replays_from_last_event_id_and_drops_duplicates():
    fake = FakeHermes()

    def script(attempt, last):
        if attempt == 1:
            # The connection drops after two deltas with no terminal event.
            return [
                frame(0, {"event": "message.delta", "delta": "a"}),
                frame(1, {"event": "message.delta", "delta": "b"}),
            ]
        assert last == "1"
        # Hermes replays from the cursor; seq 1 arrives a second time.
        return [
            frame(1, {"event": "message.delta", "delta": "b"}),
            frame(2, {"event": "message.delta", "delta": "c"}),
            frame(3, {"event": "run.completed"}),
        ]

    fake.script["run_1"] = script
    async with client_for(fake) as client:
        gateway = WarmGateway("http://hermes", KEY, client)
        text = "".join([piece async for piece in gateway.run("hi", [])])
    assert text == "abc"
    assert gateway.duplicates_dropped == 1 and gateway.reconnects == 1
    assert fake.connections == [None, "1"]


async def test_identical_text_in_distinct_events_is_kept_but_a_replay_is_not():
    """Dedupe is by Hermes event seq, never by comparing text."""
    fake = FakeHermes()
    same = "Simulated duplicate."

    def script(attempt, last):
        if attempt == 1:
            return [
                frame(0, {"event": "message.delta", "delta": same}),
                frame(1, {"event": "message.delta", "delta": same}),
            ]
        return [
            frame(1, {"event": "message.delta", "delta": same}),
            frame(2, {"event": "run.completed"}),
        ]

    fake.script["run_1"] = script
    async with client_for(fake) as client:
        gateway = WarmGateway("http://hermes", KEY, client)
        text = "".join([piece async for piece in gateway.run("hi", [])])
    assert text == same + same
    assert gateway.duplicates_dropped == 1


def test_fixture_uses_the_tasks_own_tag_not_text_added_around_it():
    from immortility_broker.simulated import scripted_pieces, turn_diagnostics

    messages = [
        {"role": "user", "content": "SIM:steps earlier turn"},
        {"role": "assistant", "content": "Simulated steps finished. 8892."},
        # Notes before and recalled context after the request both carry other tags.
        {
            "role": "user",
            "content": "Local notes: SIM:steps\n\nSIM:approve what time is it\n"
            "<recalled>SIM:steps 8892</recalled>",
        },
    ]
    pieces = scripted_pieces(messages, "SIM:approve what time is it")
    assert b"sim-approve" in pieces[0][1]
    after_tool = messages + [
        {"role": "assistant", "content": ""},
        {"role": "tool", "content": "{}"},
    ]
    assert b"Simulated approved clock." in scripted_pieces(after_tool, "SIM:approve x")[0][1]
    seen = turn_diagnostics(messages, "SIM:approve what time is it")
    assert seen["task_tags"] == ["SIM:approve"] and seen["last_user_index"] == 2
    # The fixture's repeated text is legitimate model output: two separate deltas.
    dup = scripted_pieces([{"role": "user", "content": "SIM:dup"}], "SIM:dup")
    assert sum(b"Simulated duplicate." in block for _, block in dup) == 2


async def test_lost_replay_and_endless_disconnects_fail_closed():
    fake = FakeHermes()
    fake.script["run_1"] = lambda attempt, last: [
        frame(5, {"event": "replay.truncated", "oldest_retained_seq": 5})
    ]
    async with client_for(fake) as client:
        gateway = WarmGateway("http://hermes", KEY, client)
        with pytest.raises(BrokerError) as lost:
            "".join([piece async for piece in gateway.run("hi", [])])
        assert lost.value.code == "hermes_lost"
        fake.script["run_2"] = lambda attempt, last: [
            frame(0, {"event": "message.delta", "delta": "x"})
        ]
        with pytest.raises(BrokerError) as dropped:
            "".join([piece async for piece in gateway.run("hi", [])])
        assert dropped.value.code == "hermes_lost"
        assert gateway.reconnects == 4


async def test_an_unrequested_hermes_cancel_is_not_a_success():
    fake = FakeHermes()
    fake.script["run_1"] = lambda attempt, last: [
        frame(0, {"event": "message.delta", "delta": "partial"}),
        frame(1, {"event": "run.cancelled"}),
    ]
    async with client_for(fake) as client:
        gateway = WarmGateway("http://hermes", KEY, client)
        with pytest.raises(BrokerError) as caught:
            [piece async for piece in gateway.run("hi", [])]
    assert caught.value.code == "hermes_lost"


async def test_native_hermes_approval_is_denied_by_exact_request_id():
    fake = FakeHermes()
    fake.script["run_1"] = lambda attempt, last: [
        frame(0, {"event": "approval.request", "request_id": "req-7", "command": "rm -rf x"}),
        frame(1, {"event": "message.delta", "delta": "done"}),
        frame(2, {"event": "run.completed"}),
    ]
    async with client_for(fake) as client:
        gateway = WarmGateway("http://hermes", KEY, client)
        text = "".join([piece async for piece in gateway.run("hi", [])])
    assert text == "done"
    assert fake.approvals == [("run_1", {"choice": "deny", "request_id": "req-7"})]
    assert gateway.native_approvals_denied == 1


async def test_turn_stop_waits_for_hermes_to_confirm_the_run_ended():
    fake = FakeHermes()
    started = asyncio.Event()

    def script(attempt, last):
        async def slow():
            yield frame(0, {"event": "message.delta", "delta": "x"})
            started.set()
            await asyncio.sleep(30)

        return slow()

    fake.script["run_1"] = script
    async with client_for(fake) as client:
        runtime = GatewayRuntime(WarmGateway("http://hermes", KEY, client))

        async def consume():
            return [piece async for piece in runtime.run("SIM:slow", [])]

        worker = asyncio.create_task(consume())
        await asyncio.wait_for(started.wait(), 5)
        worker.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker
        await runtime.stop()
    assert runtime.run_id == "run_1" and fake.stops == ["run_1"]
    assert runtime.stop_phase == "cancelled"
    assert fake.polls["run_1"] > fake.stop_polls_before_cancel


async def test_a_run_that_never_confirms_is_reported_unconfirmed():
    fake = FakeHermes()
    fake.never_confirm = True
    fake.statuses["run_9"] = "running"
    async with client_for(fake) as client:
        gateway = WarmGateway("http://hermes", KEY, client)
        phase = await gateway.stop_and_confirm("run_9", timeout=0.3)
    assert phase == "stopping"


async def test_a_completed_turn_does_not_send_a_stop():
    fake = FakeHermes()
    fake.script["run_1"] = lambda attempt, last: [
        frame(0, {"event": "message.delta", "delta": "ok"}),
        frame(1, {"event": "run.completed"}),
    ]
    async with client_for(fake) as client:
        runtime = GatewayRuntime(WarmGateway("http://hermes", KEY, client))
        assert "".join([p async for p in runtime.run("hi", [])]) == "ok"
        await runtime.stop()
    assert fake.stops == [] and runtime.stop_phase == "completed"


class SlowRuntime:
    """Stands in for a gateway turn: it streams forever until stopped."""

    accepts_broker_schemas = True

    def __init__(self, phase):
        self.broker_schemas = []
        self.response_length = "normal"
        self.idempotency_key = ""
        self.phase = phase
        self.stop_phase = None
        self.run_id = "run_fixture"
        self.on_run = None

    async def run(self, content, history, role=None):
        if self.on_run:
            self.on_run(self.run_id)
        yield "partial "
        await asyncio.sleep(60)

    async def stop(self):
        self.stop_phase = self.phase


async def _cancel_through_engine(tmp_path, phase):
    runtime = SlowRuntime(phase)
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, factory=lambda: runtime)
    store = app.state.store
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            headers = {"Authorization": "Bearer " + "x" * 40}
            sid = (await client.post("/v1/sessions", headers=headers)).json()["id"]
            created = await client.post(
                "/v1/tasks",
                headers=headers,
                json={
                    "session_id": sid,
                    "request_id": "m17-stop",
                    "content": "slow turn",
                    "cloud_consent": True,
                },
            )
            tid = created.json()["task_id"]
            for _ in range(200):
                if any(e["type"] == "message.delta" for e in store.events(tid)):
                    break
                await asyncio.sleep(0.01)
            response = await client.post(f"/v1/tasks/{tid}/cancel", headers=headers, json={})
            assert response.status_code == 200
            states = [e["data"]["status"] for e in store.events(tid) if e["type"] == "task.state"]
            notices = [e["data"] for e in store.events(tid) if e["type"] == "audit.notice"]
            return store.get(tid), states, notices
    finally:
        store.db.close()


async def test_cancel_is_stopping_until_the_run_confirms(tmp_path):
    task, states, notices = await _cancel_through_engine(tmp_path, "cancelled")
    assert task["status"] == "cancelled"
    assert states[-2:] == ["stopping", "cancelled"]
    confirmed = next(n for n in notices if n.get("name") == "cancellation.confirmed")
    assert confirmed["run_phase"] == "cancelled" and confirmed["run_id"] == "run_fixture"
    assert any(n.get("name") == "hermes.run.started" for n in notices)
    assert task["result"]["partial"] is True and task["result"]["text"].startswith("partial")


async def test_an_unconfirmed_stop_needs_recovery_instead_of_claiming_cancelled(tmp_path):
    task, states, notices = await _cancel_through_engine(tmp_path, "stopping")
    assert task["status"] == "disconnected"
    assert task["error"]["code"] == "stop_unconfirmed"
    assert "cancelled" not in states and states[-2:] == ["stopping", "disconnected"]
    assert any(n.get("name") == "cancellation.unconfirmed" for n in notices)


def test_stopping_cannot_jump_to_success(tmp_path):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40)
    store = app.state.store
    try:
        task, _ = store.create(
            TaskRequest(
                session_id=store.session()["id"], request_id="t", content="x", cloud_consent=True
            )
        )
        tid = task["task_id"]
        store.state(tid, "queued")
        store.state(tid, "running")
        store.state(tid, "stopping")
        for forbidden in ("succeeded", "running", "verifying", "blocked"):
            with pytest.raises(BrokerError):
                store.state(tid, forbidden)
        store.state(tid, "cancelled")
    finally:
        store.db.close()


async def _approval_fixture(tmp_path, ttl=5.0):
    settings = Settings(_env_file=None, data_dir=tmp_path, local_tools_enabled=True)
    settings.simulated_inference = True
    app = create_app(settings, "x" * 40)
    store, engine = app.state.store, app.state.engine
    engine.approval_ttl = ttl
    task, _ = store.create(
        TaskRequest(
            session_id=store.session()["id"],
            request_id="approve",
            content="SIM:approve",
            cloud_consent=True,
            allowed_capabilities=["clock.now.v1"],
        )
    )
    tid = task["task_id"]
    store.state(tid, "queued")
    store.state(tid, "running")
    engine.open_grant(tid, "fast", 90)
    engine.require_tool_approval.add(tid)
    return app, store, engine, tid


async def _infer(client, engine):
    return await client.post(
        "/inference/v1/chat/completions",
        headers={"Authorization": "Bearer " + engine.inference_key},
        json={"model": MODEL, "messages": [{"role": "user", "content": "SIM:approve"}]},
    )


async def _wait_pending(engine, tid):
    for _ in range(300):
        if tid in engine.tool_approvals:
            return engine.tool_approvals[tid]["request_id"]
        await asyncio.sleep(0.01)
    raise AssertionError("no approval was requested")


async def test_tool_approval_is_one_shot_and_replay_is_rejected(tmp_path):
    app, store, engine, tid = await _approval_fixture(tmp_path)
    headers = {"Authorization": "Bearer " + "x" * 40}
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            inference = asyncio.create_task(_infer(client, engine))
            request_id = await _wait_pending(engine, tid)
            assert store.get(tid)["status"] == "awaiting_approval"
            approved = await client.post(
                f"/v1/tasks/{tid}/approval",
                headers=headers,
                json={"decision": "approve", "request_id": request_id},
            )
            assert approved.status_code == 200
            response = await inference
            assert response.status_code == 200 and "clock.now.v1" in response.text
            assert store.get(tid)["status"] == "running"
            call = {"capability": "clock.now.v1", "arguments": {}}
            auth = {"Authorization": "Bearer " + engine.inference_key}
            first = await client.post("/inference/v1/capabilities/call", headers=auth, json=call)
            again = await client.post("/inference/v1/capabilities/call", headers=auth, json=call)
            assert first.status_code == 200 and again.status_code == 403
            replay = await client.post(
                f"/v1/tasks/{tid}/approval",
                headers=headers,
                json={"decision": "approve", "request_id": request_id},
            )
            assert replay.status_code == 409
            assert replay.json()["error"]["code"] == "approval_replayed"
        events = store.events(tid)
        requested = next(e["data"] for e in events if e["type"] == "approval.requested")
        resolved = next(e["data"] for e in events if e["type"] == "approval.resolved")
        completed = next(
            e["data"]
            for e in events
            if e["type"] == "tool.completed" and "tool_call_id" in e["data"]
        )
        assert requested["tool_call_id"] == "sim-approve" == resolved["tool_call_id"]
        assert resolved["decision"] == "approve" and resolved["request_id"] == request_id
        assert completed["tool_call_id"] == "sim-approve" and completed["verified"] is True
        assert len(completed["receipt"]) == 16
    finally:
        store.db.close()


@pytest.mark.parametrize("outcome", ["deny", "expired"])
async def test_denied_or_expired_approval_never_reaches_hermes(tmp_path, outcome):
    app, store, engine, tid = await _approval_fixture(
        tmp_path, ttl=0.4 if outcome == "expired" else 5
    )
    headers = {"Authorization": "Bearer " + "x" * 40}
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            inference = asyncio.create_task(_infer(client, engine))
            request_id = await _wait_pending(engine, tid)
            if outcome == "deny":
                await client.post(
                    f"/v1/tasks/{tid}/approval",
                    headers=headers,
                    json={"decision": "deny", "request_id": request_id},
                )
            response = await inference
            assert "clock.now.v1" not in response.text
            assert engine.provider_error is not None
            assert engine.provider_error.code == (
                "approval_denied" if outcome == "deny" else "approval_expired"
            )
            late = await client.post(
                f"/v1/tasks/{tid}/approval",
                headers=headers,
                json={"decision": "approve", "request_id": request_id},
            )
            assert late.status_code == 409
            call = await client.post(
                "/inference/v1/capabilities/call",
                headers={"Authorization": "Bearer " + engine.inference_key},
                json={"capability": "clock.now.v1", "arguments": {}},
            )
            assert call.status_code == 403
        resolved = next(e["data"] for e in store.events(tid) if e["type"] == "approval.resolved")
        assert resolved["decision"] == outcome
    finally:
        store.db.close()


async def test_every_proposed_tool_call_gets_an_authorization_record(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path, local_tools_enabled=True)
    settings.simulated_inference = True
    app = create_app(settings, "x" * 40)
    store, engine = app.state.store, app.state.engine
    try:
        task, _ = store.create(
            TaskRequest(
                session_id=store.session()["id"],
                request_id="c",
                content="SIM:clock",
                cloud_consent=True,
                allowed_capabilities=["clock.now.v1"],
            )
        )
        tid = task["task_id"]
        store.state(tid, "queued")
        store.state(tid, "running")
        engine.open_grant(tid, "fast", 90)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post(
                "/inference/v1/chat/completions",
                headers={"Authorization": "Bearer " + engine.inference_key},
                json={"model": MODEL, "messages": [{"role": "user", "content": "SIM:clock"}]},
            )
            assert response.status_code == 200
            call = await client.post(
                "/inference/v1/capabilities/call",
                headers={"Authorization": "Bearer " + engine.inference_key},
                json={"capability": "clock.now.v1", "arguments": {}},
            )
            assert call.status_code == 200
        notices = [e["data"] for e in store.events(tid) if e["type"] == "audit.notice"]
        decision = next(n for n in notices if n.get("name") == "tool.authorization")
        assert decision == {
            "name": "tool.authorization",
            "decision": "allow",
            "capability": "clock.now.v1",
            "tool_call_id": "sim-clock",
        }
        started = next(
            e["data"]
            for e in store.events(tid)
            if e["type"] == "tool.started" and "tool_call_id" in e["data"]
        )
        assert started["tool_call_id"] == "sim-clock"
    finally:
        store.db.close()
