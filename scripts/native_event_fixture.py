"""Fixed synthetic SSE source, imported only by the explicit debug acceptance broker.

Uses the real Store contracts and broker auth. Never calls a runtime, provider,
tool, audio device or private database. No route or duration is frontend-controlled.
"""

import asyncio
import json
import time
from pathlib import Path

from fastapi import Request
from fastapi.responses import StreamingResponse

from immortility_broker.contracts import TERMINAL
from immortility_broker.workflows import WorkflowRequest, WorkflowStep


def install_stream_fixture(
    app, folder: Path, duration: float, drop_after: float = 45, stall_seconds: float = 0
):
    store, engine = app.state.store, app.state.engine
    task, _ = store.create_workflow(
        WorkflowRequest(
            session_id=store.session()["id"],
            request_id="native-local-stream",
            label="Synthetic local event acceptance; no model or tool execution",
            local_read_consent=True,
            deadline_seconds=max(1, int(duration)),
            steps=[WorkflowStep(id="synthetic", capability="clock.now.v1")],
        ),
        {},
    )
    tid = task["task_id"]
    store.state(
        tid,
        "queued",
        input={**task["input"], "no_cloud": True},
        budget={
            "max_paid_usd": 0,
            "max_tokens": 0,
            "max_calls": 0,
            "timeout_ms": int(duration * 1000) + 1000,
        },
    )
    store.state(tid, "running")
    engine.active = tid
    started = asyncio.Event()
    record = {
        "classification": "synthetic local events; actual native task transport",
        "task_id": tid,
        "duration_seconds": duration,
        "connections": [],
        "dropped_once": False,
        "heartbeats": 0,
        "cloud_calls": 0,
        "tool_calls": 0,
        "stalled_once": False,
    }

    def save():
        record["status"] = store.get(tid)["status"]
        (folder / "native-stream-evidence.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )

    save()

    # Replace only this debug fixture's task-event source; all broker security
    # middleware and fixed native IPC paths still apply.
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) != "/v1/tasks/{task_id}/events"
    ]

    @app.get("/v1/tasks/{task_id}/events")
    async def fixture_events(task_id: str, request: Request, after: int = 0):
        if task_id != tid:
            from immortility_broker.contracts import BrokerError

            raise BrokerError("not_found", "Synthetic stream task not found.", 404)
        if after < 0:
            from immortility_broker.contracts import BrokerError

            raise BrokerError("invalid_cursor", "Invalid replay cursor.", 400)
        record["connections"].append(
            {
                "after": after,
                "at_seconds": round(time.monotonic() - origin, 3) if started.is_set() else 0,
            }
        )
        started.set()
        save()

        async def chunks():
            cursor = after
            while not await request.is_disconnected():
                elapsed = time.monotonic() - origin
                if drop_after and elapsed >= drop_after and not record["dropped_once"]:
                    record["dropped_once"] = True
                    save()
                    raise OSError("Synthetic transport interruption")
                for event in store.events(tid, cursor):
                    cursor = event["sequence"]
                    yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"
                if store.get(tid)["status"] in TERMINAL:
                    save()
                    return
                if stall_seconds and not record["stalled_once"]:
                    record["stalled_once"] = True
                    save()
                    await asyncio.sleep(stall_seconds)
                record["heartbeats"] += 1
                yield ": synthetic heartbeat\n\n"
                await asyncio.sleep(0.25)

        return StreamingResponse(chunks(), media_type="text/event-stream")

    origin = time.monotonic()

    async def produce():
        nonlocal origin
        await started.wait()
        origin = time.monotonic()
        pieces = []
        tick = 0
        while time.monotonic() - origin < duration:
            if store.get(tid)["status"] in TERMINAL:
                break
            tick += 1
            piece = f"Local fixture tick {tick:03d}.\n"
            pieces.append(piece)
            store.event(tid, "message.delta", {"text": piece})
            await asyncio.sleep(min(5, max(0.01, duration - (time.monotonic() - origin))))
        if store.get(tid)["status"] not in TERMINAL:
            final = "Native stream completed.\n"
            pieces.append(final)
            store.event(tid, "message.delta", {"text": final})
            store.state(tid, "verifying")
            store.state(
                tid,
                "succeeded",
                result={
                    "text": "".join(pieces),
                    "provider": "local",
                    "model": "synthetic-native-events",
                },
            )
        engine.active = None
        record.update(
            status=store.get(tid)["status"],
            elapsed_seconds=round(time.monotonic() - origin, 3),
            text_sha256=__import__("hashlib").sha256("".join(pieces).encode()).hexdigest(),
            event_count=len(store.events(tid)),
        )
        save()

    return produce
