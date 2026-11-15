"""Accelerated contracts for the explicit keyless native stream test source."""

import asyncio
import importlib.util

import httpx

from immortility_broker.app import create_app
from immortility_broker.config import ROOT, Settings


async def test_native_fixture_completes_a_real_store_task_without_inference(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "native_event_fixture", ROOT / "scripts/native_event_fixture.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def forbidden():
        raise AssertionError("Synthetic transport acceptance must never start Hermes")

    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, factory=forbidden)
    produce = module.install_stream_fixture(app, tmp_path, 0.03, drop_after=0)
    task = app.state.store.tasks(app.state.store.sessions()[0]["id"])[0]
    worker = asyncio.create_task(produce())
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            denied = await client.get(f"/v1/tasks/{task['task_id']}/events")
            assert denied.status_code == 401
            response = await client.get(
                f"/v1/tasks/{task['task_id']}/events",
                headers={"Authorization": "Bearer " + "x" * 40},
            )
        await worker
        assert "Native stream completed." in response.text
        final = app.state.store.get(task["task_id"])
        assert final["status"] == "succeeded" and final["input"]["no_cloud"] is True
        assert final["budget"]["max_calls"] == 0
        events = app.state.store.events(task["task_id"])
        assert len({event["sequence"] for event in events}) == len(events)
        assert app.state.engine.inference_allowed is False
    finally:
        worker.cancel()
        app.state.store.db.close()
