"""Protocol ordering fixtures: no runtime, provider credentials or subprocesses."""

import asyncio
from types import SimpleNamespace

import pytest

from immortility_broker import hermes
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError


@pytest.mark.asyncio
@pytest.mark.parametrize("ready_first", [True, False])
@pytest.mark.parametrize("tools", [[], ["terminal"]])
async def test_verified_readiness_and_session_id_can_arrive_in_either_order(
    tmp_path, monkeypatch, ready_first, tools
):
    sent = []
    cleaned = []

    async def spawn(*args, **kwargs):
        return SimpleNamespace(returncode=0), None

    async def reap(process, owner):
        cleaned.append(process)

    monkeypatch.setattr(hermes, "spawn_owned", spawn)
    monkeypatch.setattr(hermes, "reap", reap)
    monkeypatch.setattr(hermes, "isolated_config", lambda *args: {})

    class Fixture(hermes.Hermes):
        async def send(self, method, params):
            sent.append((method, params))
            return len(sent)

        async def frames(self):
            created = {"id": 1, "result": {"session_id": "synthetic-session"}}
            ready = {
                "method": "event",
                "params": {"type": "session.info", "payload": {"tools": tools}},
            }
            yield {"method": "event", "params": {"type": "session.info", "payload": {"lazy": True}}}
            for frame in [ready, created] if ready_first else [created, ready]:
                yield frame
            assert [name for name, _ in sent] == ["session.create", "prompt.submit"]
            # A repeated readiness notice must never submit a second prompt.
            yield ready
            assert [name for name, _ in sent] == ["session.create", "prompt.submit"]
            yield {
                "method": "event",
                "params": {"type": "message.complete", "payload": {"text": "answer"}},
            }

    runtime = Fixture(Settings(_env_file=None, data_dir=tmp_path), "http://127.0.0.1", "fixture")
    if tools:
        with pytest.raises(BrokerError) as error:
            _ = [part async for part in runtime.run("public fixture", [])]
        assert error.value.code == "tools_enabled"
        assert [name for name, _ in sent] == ["session.create"]
    else:
        assert [part async for part in runtime.run("public fixture", [])] == ["answer"]
        assert sent[1][1] == {"session_id": "synthetic-session", "text": "public fixture"}
    assert len(cleaned) == 1
    assert runtime.process is None


@pytest.mark.asyncio
async def test_frame_read_timeout_is_structured_without_extending_the_deadline(monkeypatch):
    runtime = hermes.Hermes(Settings(_env_file=None), "http://127.0.0.1", "fixture")
    runtime.process = SimpleNamespace(stdout=asyncio.StreamReader())

    async def timeout(awaitable, seconds):
        assert seconds == 70
        awaitable.close()
        raise TimeoutError

    monkeypatch.setattr(hermes.asyncio, "wait_for", timeout)
    with pytest.raises(BrokerError) as error:
        await anext(runtime.frames())
    assert error.value.code == "hermes_timeout"
