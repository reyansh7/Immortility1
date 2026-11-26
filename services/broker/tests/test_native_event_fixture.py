"""Accelerated contracts for the explicit keyless native stream test source."""

import asyncio
import importlib.util

import httpx

from immortility_broker.app import create_app
from immortility_broker.config import ROOT, Settings


def test_project_native_fixture_cannot_admit_personal_roots_or_other_tools(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "native_project_fixture", ROOT / "scripts/native_project_fixture.py"
    )
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.prepare(tmp_path)
    assert "answer = 42" in (tmp_path / "project-one/example.ts").read_text()
    assert fixture.allowed(
        "/v1/settings/project", {"enabled": True, "root": str(tmp_path / "project-one")}, tmp_path
    )
    for root in [
        str(tmp_path.parent),
        str(tmp_path / "project-one/../outside"),
        "\\\\server\\share",
    ]:
        assert not fixture.allowed(
            "/v1/settings/project", {"enabled": True, "root": root}, tmp_path
        )
    assert fixture.allowed(
        "/v1/workflows", {"steps": [{"capability": "project.read.v1"}]}, tmp_path
    )
    for capability in ["terminal", "arithmetic.add.v1", "public.research.v1"]:
        assert not fixture.allowed(
            "/v1/workflows", {"steps": [{"capability": capability}]}, tmp_path
        )
    assert not fixture.allowed("/v1/tasks", {"cloud_consent": True}, tmp_path)


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
