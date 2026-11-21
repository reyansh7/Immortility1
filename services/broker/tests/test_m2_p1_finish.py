"""M2/P1 finish: reviewed gateway pins (0.23.3 canary-only), K7 warm-up, typed schemas.

Offline only. The warm-up is answered by the broker itself; nothing here contacts a
provider or the simulated fixture, so none of it is live-model evidence.
"""

import json
from pathlib import Path

import httpx
import pytest

from immortility_broker import run_binding
from immortility_broker.app import apply_gateway_flag, create_app, warm_gateway
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.hermes_gateway import GATEWAY_PINS, GatewaySupervisor, gateway_pin
from immortility_broker.policy import MODEL

WARM = "w" * 43
CLIENT_TOKEN = "x" * 40


def _flag(directory: Path, body: dict) -> Settings:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "hermes-gateway.json").write_text(json.dumps(body), encoding="utf-8")
    settings = Settings(_env_file=None, data_dir=directory)
    apply_gateway_flag(settings)
    return settings


def test_candidate_pin_is_refused_outside_a_canary(tmp_path):
    assert GATEWAY_PINS["0.23.3"]["revision"].startswith("caafe538")
    assert GATEWAY_PINS["0.23.2"]["revision"].startswith("ae2a81c")
    with pytest.raises(BrokerError):
        gateway_pin("0.23.3", tmp_path / "prod")
    with pytest.raises(BrokerError):
        gateway_pin("9.9.9", tmp_path / "canary-x")
    assert gateway_pin("0.23.3", tmp_path / "canary-0233-m2")["home"] == "h0233"
    assert gateway_pin("0.23.2", tmp_path / "prod")["home"] == "h0232"


def test_flag_file_selects_a_candidate_only_inside_a_canary(tmp_path):
    outside = _flag(tmp_path / "dev", {"enabled": True, "version": "0.23.3"})
    assert outside.hermes_0232_gateway is False  # default runtime stays in place
    assert outside.typed_tool_schemas_enabled is False
    unknown = _flag(tmp_path / "canary-u", {"enabled": True, "version": "latest"})
    assert unknown.hermes_0232_gateway is False
    inside = _flag(tmp_path / "canary-0233-m2", {"enabled": True, "version": "0.23.3"})
    assert inside.hermes_0232_gateway is True
    assert inside.hermes_gateway_version == "0.23.3"
    supervisor = GatewaySupervisor(inside, "http://127.0.0.1:9")
    assert supervisor.home.name == "h0233" and supervisor.source.name == "canary-0233-src"
    assert supervisor.revision == GATEWAY_PINS["0.23.3"]["revision"]


def test_gateway_path_defaults_to_typed_schemas_and_warmup(tmp_path):
    plain = _flag(tmp_path / "canary-a", {"enabled": True})
    assert plain.hermes_gateway_version == "0.23.2"
    assert plain.typed_tool_schemas_enabled is True
    assert plain.gateway_warmup_enabled is True
    off = _flag(
        tmp_path / "canary-b", {"enabled": True, "typed_tool_schemas": False, "warmup": False}
    )
    assert off.typed_tool_schemas_enabled is False
    assert off.gateway_warmup_enabled is False
    # No flag file: the desktop default (0.21.1 stdio) and its settings are untouched.
    none = Settings(_env_file=None, data_dir=tmp_path / "prod")
    apply_gateway_flag(none)
    assert none.hermes_0232_gateway is False and none.typed_tool_schemas_enabled is False


def test_typed_gateway_config_uses_the_strict_broker_models(tmp_path, monkeypatch):
    settings = _flag(tmp_path / "canary-t", {"enabled": True})
    supervisor = GatewaySupervisor(settings, "http://127.0.0.1:9")
    supervisor.home = tmp_path / "home"
    seen = {}

    def fake_config(source, base_url, token, **kwargs):
        seen.update(kwargs)
        return {"agent": {}}

    monkeypatch.setattr("immortility_broker.hermes.isolated_config", fake_config)
    supervisor._write_config()
    assert seen["typed_tools"] is True
    multiply = next(
        s for s in seen["broker_schemas"] if s["manifest"]["name"] == "arithmetic.multiply.v1"
    )
    assert set(multiply["input_schema"]["required"]) == {"a", "b"}
    assert multiply["input_schema"]["properties"]["a"].get("type") == "integer"


def _warm_app(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    app = create_app(settings, CLIENT_TOKEN)
    app.state.engine.warm_inference_key = WARM
    return app, app.state.engine


def _post(client, binding):
    system = "You are Jarvis." + ("\n\n" + run_binding.marker(binding) if binding else "")
    return client.post(
        "/inference/v1/chat/completions",
        headers={"Authorization": "Bearer " + WARM},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": "warm"},
            ],
        },
    )


class _FakeHermes:
    """Stands in for the gateway: one run makes one model request back to the broker."""

    def __init__(self, client):
        self.client = client
        self.responses = []

    async def run(self, content, history, idempotency_key=None, on_run=None, instructions=None):
        binding = instructions[len(run_binding.MARKER_PREFIX) : -1]
        response = await _post(self.client, binding)
        self.responses.append(response)
        yield response.text


async def test_warmup_is_answered_locally_and_only_while_in_flight(tmp_path):
    app, engine = _warm_app(tmp_path)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://127.0.0.1"
        ) as client:
            hermes = _FakeHermes(client)

            class Supervisor:
                gateway = hermes

            await warm_gateway(engine, Supervisor())
            assert engine.warmup_state == "done" and engine.warmup_calls == 1
            first = hermes.responses[0]
            assert first.status_code == 200 and "ready" in first.text
            assert "immortility/local-warmup" in first.text
            assert engine.warmup_binding is None
            # Replaying the old warm-up binding after the warm-up is refused (no active task).
            stale = run_binding.new_binding()
            replay = await _post(client, stale)
            assert replay.status_code in {401, 403}
            # With no warm-up in flight and no task, a bare warm-key request is refused too.
            bare = await _post(client, None)
            assert bare.status_code in {401, 403}
        assert engine.store.ledger.summary("none")["charged_tokens"] == 0
    finally:
        engine.store.db.close()


async def test_warmup_binding_cannot_serve_a_task_and_failure_is_contained(tmp_path):
    app, engine = _warm_app(tmp_path)
    try:

        class Broken:
            async def run(self, *args, **kwargs):
                raise RuntimeError("gateway down")
                yield ""  # pragma: no cover

        class Supervisor:
            gateway = Broken()

        await warm_gateway(engine, Supervisor())
        assert engine.warmup_state == "failed" and engine.warmup_binding is None

        class NoGateway:
            gateway = None

        await warm_gateway(engine, NoGateway())
        assert engine.warmup_state == "skipped"
    finally:
        engine.store.db.close()
