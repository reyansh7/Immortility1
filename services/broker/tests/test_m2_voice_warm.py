"""K25: silent INFERNAL warm-up while the user talks; longer keep-alive; no interleaving."""

import asyncio
import io
import json
from unittest.mock import AsyncMock, Mock

import pytest

from immortility_broker import voice as voice_module
from immortility_broker import voice_worker
from immortility_broker.config import Settings
from immortility_broker.store import Store
from immortility_broker.voice import VoiceOptions, VoiceService


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_VOICE_DIR", str(tmp_path / "private"))
    store = Store(tmp_path / "state.db")
    svc = VoiceService(
        Settings(_env_file=None, data_dir=tmp_path, infernal_voice_enabled=True),
        store,
        AsyncMock(),
        AsyncMock(),
    )
    yield svc
    store.db.close()


def infernal(svc, **extra):
    svc.options = VoiceOptions.model_validate({"voice": "infernal", "voice_output": True, **extra})


@pytest.mark.asyncio
async def test_prewarm_only_for_infernal_output(service):
    calls = []

    async def exchange(operation, options):
        calls.append(operation)
        return {"kind": "done"}

    service._infernal_exchange = exchange
    service.prewarm_infernal()  # default voice: nothing
    infernal(service, voice_output=False)
    service.prewarm_infernal()
    assert service.infernal_warm is None
    infernal(service)
    service.settings.infernal_voice_enabled = False
    service.prewarm_infernal()
    assert service.infernal_warm is None
    service.settings.infernal_voice_enabled = True
    service.prewarm_infernal()
    service.prewarm_infernal()  # already warming: not twice
    await service.infernal_warm
    assert calls == ["warm"] and "tts_warm" in service.latency
    service.infernal_process = Mock(returncode=None)
    service.prewarm_infernal()  # already warm process: nothing
    assert calls == ["warm"]


@pytest.mark.asyncio
async def test_speak_waits_for_warm_and_never_interleaves(service):
    infernal(service)
    gate, order = asyncio.Event(), []

    async def exchange(operation, options):
        order.append(operation + ":start")
        if operation == "warm":
            await gate.wait()
        order.append(operation + ":end")
        return {"kind": "done"}

    service._infernal_exchange = exchange
    service.prewarm_infernal()
    await asyncio.sleep(0)
    speak = asyncio.create_task(service.worker("speak", voice="infernal", text="hi"))
    await asyncio.sleep(0.01)
    assert order == ["warm:start"]
    gate.set()
    await speak
    assert order == ["warm:start", "warm:end", "speak:start", "speak:end"]


@pytest.mark.asyncio
async def test_warm_failure_is_silent_and_stop_cancels(service):
    infernal(service)

    async def broken(operation, options):
        raise RuntimeError("cold start failed")

    service._infernal_exchange = broken
    service.prewarm_infernal()
    await service.infernal_warm  # suppressed: chat and recording are unaffected
    blocker = asyncio.Event()

    async def slow(operation, options):
        await blocker.wait()

    service._infernal_exchange = slow
    service.prewarm_infernal()
    await asyncio.sleep(0)
    await service.stop_worker()
    assert service.infernal_warm.cancelled()


def test_keep_alive_is_ten_minutes():
    assert voice_module.INFERNAL_KEEP_SECONDS == 600


def frames(options, monkeypatch, produced):
    out = io.StringIO()
    monkeypatch.setattr(voice_worker, "PROTOCOL", out)
    import immortility_broker.infernal_tts as tts

    monkeypatch.setattr(
        tts, "chunks", lambda root, text, opts: produced.append(text) or iter([1, 2])
    )
    voice_worker.handle(options)
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_worker_warm_discards_audio_and_needs_authorization(monkeypatch):
    produced = []
    denied = frames(
        {"operation": "warm", "voice": "infernal", "models": "m"}, monkeypatch, produced
    )
    assert denied[-1]["kind"] == "error" and produced == []
    ok = frames(
        {"operation": "warm", "voice": "infernal", "models": "m", "infernal_authorized": True},
        monkeypatch,
        produced,
    )
    assert ok[-1] == {"kind": "done", "warmed": True} and produced == ["Ready."]
    other = frames({"operation": "warm", "voice": "ljspeech", "models": "m"}, monkeypatch, produced)
    assert other[-1]["code"] == "operation_denied"
