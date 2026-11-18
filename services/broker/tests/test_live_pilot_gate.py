"""The live pilot harness must refuse unless every explicit gate is satisfied.

These tests never pass every gate, so no provider can be contacted.
"""

import importlib.util
import json
import socket
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "live-pilot.py"


@pytest.fixture()
def pilot(monkeypatch):
    spec = importlib.util.spec_from_file_location("live_pilot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def no_network(*args, **kwargs):
        raise AssertionError("the pilot opened a network connection")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(module, "execute", lambda args: pytest.fail("execute reached"))
    return module


def run(pilot, tmp_path, capsys, *extra, env=None, monkeypatch=None):
    if monkeypatch is not None:
        if env:
            monkeypatch.setenv("IMMORTILITY_LIVE_PILOT", env)
        else:
            monkeypatch.delenv("IMMORTILITY_LIVE_PILOT", raising=False)
    code = pilot.main(["--pilot-dir", str(tmp_path / "canary-live-pilot"), *extra])
    return code, json.loads(capsys.readouterr().out)


def test_default_is_a_plan_with_reservations_and_no_calls(pilot, tmp_path, capsys, monkeypatch):
    code, out = run(pilot, tmp_path, capsys, monkeypatch=monkeypatch)
    assert code == 2 and out["status"] == "blocked" and out["calls_made"] == 0
    assert out["plan"]["reservation"] == {
        "requests": 5,
        "tokens": 6000,
        "tokens_per_request_cap": 1200,
        "retries": 0,
        "paid_usd": 0,
    }
    assert out["plan"]["inference_category"] == "live_model"
    assert not (tmp_path / "canary-live-pilot").exists()


@pytest.mark.parametrize(
    "extra, env, reason",
    [
        (["--execute"], "authorized", "--approval does not match"),
        (
            ["--execute", "--approval", "I-APPROVE-LIVE-PILOT-groq-2000-01-01"],
            "authorized",
            "--approval does not match",
        ),
        (
            ["--execute", "--approval", "{phrase}"],
            None,
            "IMMORTILITY_LIVE_PILOT=authorized is not set",
        ),
        (["--execute", "--approval", "{phrase}", "--tasks", "6"], "authorized", "tasks must be"),
        (
            ["--execute", "--approval", "{phrase}", "--max-requests", "11"],
            "authorized",
            "max requests must be",
        ),
        (
            ["--execute", "--approval", "{phrase}", "--max-tokens", "20001"],
            "authorized",
            "max tokens must be",
        ),
        (["--approval", "{phrase}"], "authorized", "--execute was not given"),
    ],
)
def test_every_missing_gate_blocks(pilot, tmp_path, capsys, monkeypatch, extra, env, reason):
    phrase = pilot.approval_phrase("groq", date.today())
    extra = [phrase if item == "{phrase}" else item for item in extra]
    code, out = run(pilot, tmp_path, capsys, *extra, env=env, monkeypatch=monkeypatch)
    assert code == 2 and out["calls_made"] == 0
    assert any(reason in item for item in out["blocked_by"])


def test_open_reservation_and_production_dir_block(pilot, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("IMMORTILITY_LIVE_PILOT", "authorized")
    phrase = pilot.approval_phrase("groq", date.today())
    ledger_dir = tmp_path / "canary-live-pilot"
    ledger_dir.mkdir()
    (ledger_dir / "live-pilot-reservations.json").write_text(json.dumps([{"open": True}]))
    code, out = run(pilot, tmp_path, capsys, "--execute", "--approval", phrase)
    assert code == 2 and any("still open" in item for item in out["blocked_by"])
    code = pilot.main(
        ["--pilot-dir", str(tmp_path / "Immortility"), "--execute", "--approval", phrase]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and any("canary-live-pilot" in item for item in out["blocked_by"])
