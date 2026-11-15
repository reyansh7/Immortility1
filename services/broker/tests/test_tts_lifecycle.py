"""Real keyless subprocess lifecycle tests; no GPU, models or microphone needed."""

import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from immortility_broker.contracts import BrokerError
from immortility_broker.tts_client import QwenWorker
from immortility_broker.voice import VoiceOptions
from immortility_broker.process_owner import spawn_owned


class LocalWorker(QwenWorker):
    def __init__(self, program):
        super().__init__(enabled=True)
        self.program = program
        self.starts = 0

    async def _start(self):
        if self.process and self.process.returncode is None:
            return
        self.starts += 1
        self.process, self.owner = await spawn_owned(
            sys.executable,
            "-u",
            "-c",
            self.program,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.reader = asyncio.create_task(self._read())


HANG = "import sys,time; sys.stdin.readline(); time.sleep(60)"
ECHO = "import sys,json;\nfor line in sys.stdin:\n m=json.loads(line); print(json.dumps({'id':m['id'],'kind':'ok'}),flush=True)"


async def test_experimental_runtime_is_off_by_default():
    worker = QwenWorker()
    with pytest.raises(BrokerError, match="experimental_qwen_disabled"):
        await worker.start()
    assert worker.process is None


async def test_worker_status_is_keyless_and_does_not_create_content_logs(tmp_path, monkeypatch):
    import immortility_broker.tts_client as client

    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path))
    monkeypatch.setenv("AWS_SESSION_TOKEN", "dummy-must-not-reach-worker")
    monkeypatch.setattr(client, "tts_python", lambda: Path(sys.executable))
    original_spawn = asyncio.create_subprocess_exec

    async def spawn(*args, **kwargs):
        assert "AWS_SESSION_TOKEN" not in kwargs["env"]
        assert kwargs["stderr"] == asyncio.subprocess.DEVNULL
        return await original_spawn(*args, **kwargs)

    monkeypatch.setattr(client.asyncio, "create_subprocess_exec", spawn)
    worker = QwenWorker(enabled=True)
    try:
        result = await worker.request({"op": "status", "id": "status-only"}, 3)
        assert result["kind"] == "ok" and result["loaded"] is False
        assert not (tmp_path / "engine.log").exists()
    finally:
        await worker.shutdown()


async def test_timeout_reaps_real_worker_and_releases_turn():
    worker = LocalWorker(HANG)
    with pytest.raises(BrokerError, match="voice_timeout"):
        await worker.request({"op": "status", "id": "one"}, 0.1)
    assert worker.process is None and not worker.turn.locked() and not worker.pending
    worker.program = ECHO
    assert (await worker.request({"op": "status", "id": "two"}, 3))["kind"] == "ok"
    await worker.shutdown()


async def test_stop_reaps_real_blocking_child_without_waiting_for_json_cancel():
    worker = LocalWorker(HANG)
    operation = asyncio.create_task(worker.request({"op": "status", "id": "one"}, 60))
    while worker.process is None or not worker.pending:
        await asyncio.sleep(0.01)
    child = worker.process
    await asyncio.wait_for(worker.cancel(), 4)
    with pytest.raises(BrokerError):
        await asyncio.wait_for(operation, 1)
    assert child.returncode is not None and worker.process is None


async def test_concurrent_start_only_spawns_one_process():
    worker = LocalWorker(ECHO)
    results = await asyncio.gather(
        *[worker.request({"op": "status", "id": str(index)}, 3) for index in range(3)]
    )
    assert all(result["kind"] == "ok" for result in results) and worker.starts == 1
    await worker.shutdown()


async def test_one_hundred_real_stop_cycles_are_bounded_and_leave_no_worker(tmp_path):
    import time

    timings = []
    for index in range(100):
        ready = tmp_path / str(index)
        program = (
            "from pathlib import Path; import sys,time; Path("
            + repr(str(ready))
            + ").write_text('ready'); sys.stdin.readline(); time.sleep(60)"
        )
        worker = LocalWorker(program)
        operation = asyncio.create_task(worker.request({"op": "status", "id": str(index)}, 60))
        while worker.process is None or not worker.pending or not ready.exists():
            await asyncio.sleep(0.001)
        process = worker.process
        start = time.perf_counter()
        await asyncio.wait_for(worker.cancel(), 3)
        timings.append(time.perf_counter() - start)
        with pytest.raises(BrokerError):
            await asyncio.wait_for(operation, 1)
        assert process.returncode is not None and worker.owner is None and not worker.pending
    print(
        f"Stop cycles n=100 p50_ms={sorted(timings)[49] * 1000:.2f} p95_ms={sorted(timings)[94] * 1000:.2f}"
    )


async def test_stop_racing_a_queued_request_does_not_orphan_the_restarted_worker():
    worker = LocalWorker(HANG)
    first = asyncio.create_task(worker.request({"op": "status", "id": "first"}, 60))
    while worker.process is None or not worker.pending:
        await asyncio.sleep(0.01)
    original = worker.process
    worker.program = ECHO
    second = asyncio.create_task(worker.request({"op": "status", "id": "second"}, 3))
    await worker.cancel()
    with pytest.raises(BrokerError):
        await first
    assert (await second)["kind"] == "ok"
    assert original.returncode is not None and worker.process is not None
    restarted = worker.process
    await worker.shutdown()
    assert restarted.returncode is not None and worker.process is None


async def test_hostile_worker_path_cannot_delete_unrelated_file(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "private"))
    private = tmp_path / "keep.wav"
    private.write_bytes(b"user audio must be preserved")
    program = (
        "import sys,json; m=json.loads(sys.stdin.readline()); "
        + "print(json.dumps({'id':m['id'],'kind':'ok','path':"
        + repr(str(private))
        + "}),flush=True)"
    )
    worker = LocalWorker(program)
    worker.stop.set()
    result = await worker.request({"op": "status", "id": "one"}, 3)
    assert result["kind"] == "error" and private.exists()
    await worker.shutdown()


async def test_output_escape_rejected_before_process_start(tmp_path):
    worker = LocalWorker(ECHO)
    with pytest.raises(BrokerError):
        await worker.request(
            {"op": "synthesize", "id": "one", "out": str(tmp_path / "escape.wav")}, 1
        )
    assert worker.starts == 0


async def test_speech_failure_is_visible_and_does_not_break_text(tmp_path, monkeypatch):
    from immortility_broker.config import Settings
    from immortility_broker.store import Store
    from immortility_broker.voice import VoiceService

    store = Store(tmp_path / "db")
    try:
        voice = VoiceService(
            Settings(_env_file=None, data_dir=tmp_path), store, AsyncMock(), AsyncMock()
        )
        voice.options = VoiceOptions(voice_output=True)
        monkeypatch.setattr("immortility_broker.voice.ready", lambda _: True)
        voice.worker = AsyncMock(side_effect=OSError("private engine detail"))
        voice.note_assistant_text("task", "Readable answer.", True)
        await voice.job
        assert voice.state == "ERROR" and voice.tts_state == "error"
        assert "private" not in voice.error and voice.level == 0
    finally:
        store.db.close()
