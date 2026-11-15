import asyncio
import json

import httpx
import pytest

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.workflows import WorkflowRequest, WorkflowStep


@pytest.mark.parametrize("global_stop", [False, True])
@pytest.mark.parametrize("source", ["native-ipc-cancel", "PRIVATE_HEADER_CANARY"])
async def test_cancellation_logs_only_bounded_route_task_reason_and_source(
    tmp_path, global_stop, source
):
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40)
    store, engine = app.state.store, app.state.engine
    task, _ = store.create_workflow(
        WorkflowRequest(
            session_id=store.session()["id"],
            request_id="diagnostic",
            label="Synthetic cancel",
            local_read_consent=True,
            steps=[WorkflowStep(id="read", capability="clock.now.v1")],
        ),
        {},
    )
    tid = task["task_id"]
    store.state(tid, "queued")
    store.state(tid, "running")
    engine.active = tid
    engine.worker = asyncio.create_task(asyncio.sleep(60))
    path = "/v1/stop" if global_stop else f"/v1/tasks/{tid}/cancel"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post(
                path,
                json={},
                headers={
                    "Authorization": "Bearer " + "x" * 40,
                    "X-Immortility-Action-Source": source,
                },
            )
        assert response.status_code == 200 and store.get(tid)["status"] == "cancelled"
        events = store.events(tid)
        notice = next(
            event["data"]
            for event in events
            if event["data"].get("name") == "cancellation.requested"
        )
        assert notice["task_id"] == tid
        assert notice["route"] == ("/v1/stop" if global_stop else "/v1/tasks/{task_id}/cancel")
        assert notice["reason"] == ("global_stop_request" if global_stop else "task_cancel_request")
        assert notice["source_tag"] == (
            source if source != "PRIVATE_HEADER_CANARY" else "authenticated-local-request"
        )
        assert "PRIVATE_HEADER_CANARY" not in json.dumps(events)
        assert engine.active is None and engine.calls == 0
    finally:
        engine.worker.cancel()
        store.db.close()
