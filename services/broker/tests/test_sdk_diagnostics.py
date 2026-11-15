import asyncio
import json

import pytest

from immortility_broker.standard_mcp import SdkProbe, sdk_request


def test_probe_never_retains_arbitrary_stderr_or_invalid_measurements():
    probe = SdkProbe()
    for value in [
        {"phase": "PRIVATE_CANARY", "milliseconds": 1},
        {"phase": "client_import", "milliseconds": True},
        {"phase": "client_import", "milliseconds": float("inf")},
        {"phase": "client_import", "milliseconds": -1},
        {"phase": "client_import", "milliseconds": 60001},
        {"phase": [], "milliseconds": 1},
        [],
    ]:
        probe.worker(json.dumps(value).encode())
    probe.worker(b"PRIVATE_CANARY\xff")
    assert not probe.worker_ms
    probe.worker(b'{"phase":"client_import","milliseconds":1.5,"body":"PRIVATE_CANARY"}')
    assert probe.worker_ms == {"client_import": 1.5}
    assert "PRIVATE_CANARY" not in repr(probe)


async def test_real_probe_reports_phases_and_owned_job_cleanup():
    probe = SdkProbe()
    assert await sdk_request("add", 7, 8, enabled=True, probe=probe) == {"result": {"result": 15}}
    assert probe.status == "passed"
    assert list(probe.phases_ms) == [
        "manifest_validated",
        "spawned",
        "request_sent",
        "result_delivered",
        "worker_exited",
        "cleanup_started",
        "cleanup_finished",
    ]
    assert list(probe.phases_ms.values()) == sorted(probe.phases_ms.values())
    assert {
        "client_import",
        "server_import",
        "server_spawn",
        "handshake",
        "discovery",
        "first_invocation",
        "client_cleanup",
    } <= probe.worker_ms.keys()
    assert probe.resources["cpu_seconds"] >= 0
    assert probe.resources["total_processes"] >= 2
    # A venv launcher/console descendant may still exist immediately before reap.
    assert 0 <= probe.resources["active_processes"] <= probe.resources["total_processes"]
    assert probe.resources["peak_job_commit_bytes"] > 0
    assert probe.cleanup_confirmed


@pytest.mark.parametrize("cancel", [True, False])
async def test_diagnostic_failure_or_cancellation_cannot_skip_owned_cleanup(monkeypatch, cancel):
    import immortility_broker.standard_mcp as module

    original = module.spawn_owned
    entered = asyncio.Event()
    children = []

    async def capture(*args, **kwargs):
        process, owner = await original(*args, **kwargs)
        children.append((process, owner))
        if not cancel:

            def broken():
                raise RuntimeError("synthetic counter failure")

            monkeypatch.setattr(owner, "statistics", broken)
        entered.set()
        return process, owner

    monkeypatch.setattr(module, "spawn_owned", capture)
    probe = SdkProbe()
    task = asyncio.create_task(sdk_request("discover", enabled=True, probe=probe))
    await asyncio.wait_for(entered.wait(), 5)
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else RuntimeError):
        await task
    assert children[0][0].returncode is not None
    assert children[0][1].handle is None
    assert "cleanup_finished" in probe.phases_ms
    assert probe.cleanup_confirmed
    if cancel:
        assert probe.status == "cancelled"
