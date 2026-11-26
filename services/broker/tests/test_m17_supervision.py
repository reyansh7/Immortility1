"""Milestone 1.7 gateway supervision with a real child process and a fake Hermes.

The fake gateway is a tiny local HTTP server started exactly like Hermes
(`python -m hermes_cli.main gateway run`, cwd = HERMES_HOME). It also implements Hermes'
planned-stop marker so the graceful path is exercised. No model or network is used.
"""

import asyncio
import json
import os
import socket
import sys
import textwrap
from pathlib import Path

import httpx
import pytest

from immortility_broker import hermes_gateway, process_owner
from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.hermes_gateway import GATEWAY_REVISION, GatewaySupervisor

FAKE_MAIN = textwrap.dedent(
    """
    import os, pathlib, sys, threading, time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    home = pathlib.Path(os.environ["HERMES_HOME"])
    (home / "gateway.pid").write_text(str(os.getpid()))
    mode_file = home / "fake-mode.txt"
    mode = mode_file.read_text().strip() if mode_file.exists() else "serve"
    if mode == "exit":
        sys.exit(3)
    if mode == "hang":
        time.sleep(60)
        sys.exit(0)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path == "/health" else 404)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 8642), Handler)

    def watch():
        marker = home / "stop-marker"
        while True:
            if marker.exists():
                marker.unlink()
                (home / "graceful-exit").write_text("1")
                server.shutdown()
                return
            time.sleep(0.05)

    threading.Thread(target=watch, daemon=True).start()
    server.serve_forever()
    server.server_close()
    """
)

FAKE_STATUS = textwrap.dedent(
    """
    import os, pathlib
    home = pathlib.Path(os.environ["HERMES_HOME"])

    def get_running_pid():
        return int((home / "gateway.pid").read_text())

    def write_planned_stop_marker(pid):
        (home / "stop-marker").write_text(str(pid))
    """
)


def port_open() -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", 8642)) == 0


@pytest.fixture
def supervisor(tmp_path, monkeypatch):
    if port_open():
        pytest.skip("Port 8642 is in use outside this test.")
    home = tmp_path / "home"
    (home / "hermes_cli").mkdir(parents=True)
    (home / "hermes_cli" / "__init__.py").write_text("")
    (home / "hermes_cli" / "main.py").write_text(FAKE_MAIN)
    (home / "gateway").mkdir()
    (home / "gateway" / "__init__.py").write_text("")
    (home / "gateway" / "status.py").write_text(FAKE_STATUS)
    source = tmp_path / "source"
    (source / ".git").mkdir(parents=True)
    (source / ".git" / "HEAD").write_text(GATEWAY_REVISION + "\n")
    data = tmp_path / "data"
    data.mkdir()
    made = GatewaySupervisor(Settings(_env_file=None, data_dir=data), "http://127.0.0.1:9")
    made.home, made.source = home, source
    made.graceful_timeout = 5.0
    monkeypatch.setattr(made, "_python", lambda: Path(sys.executable))
    monkeypatch.setattr(made, "_write_config", lambda: None)
    yield made
    if made.process is not None and made.process.returncode is None:
        made.process.kill()


def alive(pid: int) -> bool:
    if os.name == "nt":
        return process_owner.process_identity(pid) is not None
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


async def wait_closed(seconds=5.0):
    for _ in range(int(seconds / 0.05)):
        if not port_open():
            return True
        await asyncio.sleep(0.05)
    return False


async def test_rapid_restart_cycles_stop_gracefully_and_leave_nothing(supervisor):
    pids = []
    for _ in range(3):
        await supervisor.start()
        assert supervisor.state == "ready" and port_open()
        assert json.loads(supervisor._owner_record().read_text())["pid"] == supervisor.process.pid
        child = int((supervisor.home / "gateway.pid").read_text())
        pids.append((supervisor.process.pid, child))
        await supervisor.stop()
        assert supervisor.last_stop["graceful"] is True
        assert supervisor.state == "stopped" and await wait_closed()
        assert not supervisor._owner_record().exists()
    for launcher, child in pids:
        assert not alive(launcher) and not alive(child)


async def test_forced_stop_when_graceful_stop_is_unavailable(supervisor):
    (supervisor.home / "gateway" / "status.py").unlink()
    await supervisor.start()
    launcher = supervisor.process.pid
    child = int((supervisor.home / "gateway.pid").read_text())
    await supervisor.stop()
    assert supervisor.last_stop["graceful"] is False and supervisor.last_stop["forced"] is True
    assert await wait_closed() and not alive(launcher) and not alive(child)


async def test_startup_timeout_reaps_the_child(supervisor):
    (supervisor.home / "fake-mode.txt").write_text("hang")
    supervisor.ready_timeout = 1.0
    with pytest.raises(BrokerError) as caught:
        await supervisor.start()
    assert caught.value.code == "hermes_unavailable"
    child = int((supervisor.home / "gateway.pid").read_text())
    await asyncio.sleep(0.2)
    assert not alive(child) and supervisor.process is None and supervisor.state == "stopped"


async def test_exit_during_startup_is_reported(supervisor):
    (supervisor.home / "fake-mode.txt").write_text("exit")
    with pytest.raises(BrokerError) as caught:
        await supervisor.start()
    assert "exited during startup" in caught.value.message
    assert supervisor.runtime_ready is False


async def test_crash_between_turns_restarts_with_a_bound(supervisor):
    await supervisor.start()
    supervisor.max_crash_restarts = 1
    try:
        first = supervisor.process
        first.kill()
        await first.wait()
        await supervisor.recover_if_crashed()
        assert supervisor.crash_restarts == 1 and supervisor.state == "ready"
        assert supervisor.process is not first and port_open()
        supervisor.process.kill()
        await supervisor.process.wait()
        with pytest.raises(BrokerError) as caught:
            await supervisor.recover_if_crashed()
        assert "keeps exiting" in caught.value.message
    finally:
        await supervisor.stop()
    assert await wait_closed()


@pytest.mark.skipif(os.name != "nt", reason="Process identity uses Windows creation times.")
async def test_orphan_from_a_crashed_broker_is_reclaimed_by_identity(supervisor, tmp_path):
    await supervisor.start()
    orphan = supervisor.process
    child = int((supervisor.home / "gateway.pid").read_text())
    # The broker "crashes": nothing stops the gateway, its record stays behind.
    successor = GatewaySupervisor(
        Settings(_env_file=None, data_dir=supervisor.data_dir), "http://127.0.0.1:9"
    )
    successor.home, successor.source = supervisor.home, supervisor.source
    successor._python = lambda: Path(sys.executable)
    successor._write_config = lambda: None
    try:
        await successor.start()
        assert successor.reclaimed_orphan is True and successor.state == "ready"
        await orphan.wait()
        assert not alive(child)
    finally:
        await successor.stop()
        if orphan.returncode is None:
            orphan.kill()
    assert await wait_closed()


async def test_unrelated_listener_is_left_alone_even_with_a_stale_record(supervisor):
    async def handler(reader, writer):
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 8642)
    # A record naming this test process with the wrong start time: it must not be killed.
    supervisor.home.mkdir(parents=True, exist_ok=True)
    supervisor._owner_record().write_text(
        json.dumps({"pid": os.getpid(), "created": 1, "image": sys.executable})
    )
    try:
        with pytest.raises(BrokerError) as caught:
            await supervisor.start()
        assert "left running" in caught.value.message
        assert port_open() and not supervisor._owner_record().exists()
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.skipif(os.name != "nt", reason="Process identity uses Windows creation times.")
async def test_recorded_tree_needs_matching_start_time_and_image():
    child = await asyncio.create_subprocess_exec(
        sys.executable, "-c", "import time; time.sleep(30)"
    )
    try:
        created, image = process_owner.process_identity(child.pid)
        prefix = os.path.dirname(image)
        assert process_owner.terminate_recorded_tree(child.pid, created + 1, prefix) is False
        assert process_owner.terminate_recorded_tree(child.pid, created, "C:\\not-here") is False
        assert alive(child.pid)
        assert process_owner.terminate_recorded_tree(child.pid, created, prefix) is True
        await asyncio.wait_for(child.wait(), 5)
    finally:
        if child.returncode is None:
            child.kill()


async def test_missing_runtime_and_bad_checkout_fail_closed(tmp_path):
    made = GatewaySupervisor(Settings(_env_file=None, data_dir=tmp_path), "http://127.0.0.1:9")
    made.home = tmp_path / "empty-home"
    made.source = tmp_path / "missing-source"
    with pytest.raises(BrokerError) as unreadable:
        made._verify_checkout()
    assert unreadable.value.code == "hermes_unavailable"
    (made.source / ".git").mkdir(parents=True)
    (made.source / ".git" / "HEAD").write_text("0" * 40)
    with pytest.raises(BrokerError) as different:
        made._verify_checkout()
    assert different.value.code == "hermes_incompatible"
    with pytest.raises(BrokerError) as missing:
        made._python()
    assert missing.value.code == "hermes_unavailable"


async def test_job_setup_failure_leaves_no_running_state(supervisor, monkeypatch):
    async def refused(*args, **kwargs):
        raise OSError("Cannot establish worker process ownership")

    monkeypatch.setattr(hermes_gateway, "_broker_already_in_job", lambda: False)
    monkeypatch.setattr(process_owner, "spawn_owned", refused)
    with pytest.raises(OSError):
        await supervisor.start()
    assert supervisor.process is None and supervisor.runtime_ready is False
    assert supervisor._log is None and not port_open()


async def test_shutdown_during_an_active_task_confirms_the_stop_first(tmp_path):
    from test_m17_lifecycle import SlowRuntime

    runtime = SlowRuntime("cancelled")
    app = create_app(Settings(_env_file=None, data_dir=tmp_path), "x" * 40, factory=lambda: runtime)
    store, engine = app.state.store, app.state.engine
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            headers = {"Authorization": "Bearer " + "x" * 40}
            sid = (await client.post("/v1/sessions", headers=headers)).json()["id"]
            tid = (
                await client.post(
                    "/v1/tasks",
                    headers=headers,
                    json={
                        "session_id": sid,
                        "request_id": "shutdown",
                        "content": "slow",
                        "cloud_consent": True,
                    },
                )
            ).json()["task_id"]
            for _ in range(200):
                if any(e["type"] == "message.delta" for e in store.events(tid)):
                    break
                await asyncio.sleep(0.01)
    task = json.loads(
        __import__("sqlite3")
        .connect(tmp_path / "state.sqlite3")
        .execute("SELECT body FROM tasks WHERE id=?", (tid,))
        .fetchone()[0]
    )
    assert task["status"] == "cancelled"
    assert engine.active is None
