import asyncio

import httpx
import pytest

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.runtime_status import RuntimeChanges


async def test_notifications_broadcast_without_losing_changes_and_cancel_cleanly():
    changes = RuntimeChanges()
    first = asyncio.create_task(changes.wait(0))
    second = asyncio.create_task(changes.wait(0))
    await asyncio.sleep(0)
    changes.notify()
    await asyncio.wait_for(asyncio.gather(first, second), 0.5)
    assert changes.revision == 1
    await asyncio.wait_for(changes.wait(0), 0.5)
    pending = asyncio.create_task(changes.wait(1))
    await asyncio.sleep(0)
    assert not pending.done()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    await changes.wait(1, timeout=0.01)
    assert changes.revision == 1


@pytest.mark.parametrize("local_only", [False, True])
async def test_task_and_voice_changes_wake_authenticated_status_without_model_calls(
    tmp_path, local_only
):
    app = create_app(
        Settings(_env_file=None, data_dir=tmp_path, local_only_mode=local_only), "x" * 40
    )
    engine = app.state.engine
    headers = {"Authorization": "Bearer " + "x" * 40}
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            assert (await client.get("/v1/runtime/status")).status_code == 401
            first = (await client.get("/v1/runtime/status", headers=headers)).json()
            pending = asyncio.create_task(
                client.get("/v1/runtime/status?after=" + str(first["revision"]), headers=headers)
            )
            await asyncio.sleep(0.02)
            engine.active = "synthetic-task"
            value = (await asyncio.wait_for(pending, 0.5)).json()
            assert value["health"]["active_task"] == "synthetic-task"
            assert value["revision"] > first["revision"]
            pending = asyncio.create_task(
                client.get("/v1/runtime/status?after=" + str(value["revision"]), headers=headers)
            )
            await asyncio.sleep(0.02)
            app.state.voice.state = "TRANSCRIBING"
            value = (await asyncio.wait_for(pending, 0.5)).json()
            assert value["voice_state"] == "TRANSCRIBING"
            for query in ["-1", "9007199254740992", "NaN"]:
                assert (
                    await client.get("/v1/runtime/status?after=" + query, headers=headers)
                ).status_code in {400, 422}
            assert engine.calls == 0 and engine.worker is None
    finally:
        app.state.store.db.close()
