"""M2/P4 screen target: broker-side contract (no real screen is read in these tests)."""

import json

import pytest
from fastapi.testclient import TestClient

from immortility_broker import screen_target
from immortility_broker.app import create_app
from immortility_broker.config import ROOT, Settings
from immortility_broker.contracts import BrokerError

TOKEN = "test-session-credential-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class Idle:
    async def run(self, content, history):
        yield "ok"

    async def stop(self):
        pass


def _ocr(words):
    return {
        "ok": True,
        "lines": [
            {
                "text": " ".join(w[0] for w in words),
                "words": [{"t": t, "x": x, "y": 100, "w": 50, "h": 20} for t, x in words],
            }
        ],
    }


def test_ocr_pick_prefers_word_under_point_then_nearest_within_12px():
    ocr = _ocr([("alpha", 100), ("beta", 160), ("gamma", 220)])
    assert screen_target.pick_ocr_word(ocr, 170, 110, "word") == {
        "target": "beta",
        "line": "alpha beta gamma",
        "exact": True,
    }
    near = screen_target.pick_ocr_word(ocr, 157, 110, "word")  # between words: nearest wins
    assert near["target"] == "beta" and near["exact"] is False
    assert (
        screen_target.pick_ocr_word(ocr, 280, 110, "word")["exact"] is False
    )  # 10 px right of gamma
    assert screen_target.pick_ocr_word(ocr, 400, 110, "word") is None
    assert screen_target.pick_ocr_word(ocr, 170, 110, "line")["target"] == "alpha beta gamma"


def test_request_is_strict():
    with pytest.raises(ValueError):
        screen_target.TargetRequest(x=1, y=2, unit="paragraph")
    with pytest.raises(ValueError):
        screen_target.TargetRequest(x=1, y=2, extra=True)


def test_new_workers_are_hash_pinned():
    manifest = json.loads((ROOT / "config/observer-runtime.json").read_text())
    for name in (
        "integrations/windows-observer/screen_target.py",
        "integrations/windows-observer/ocr_crop.ps1",
    ):
        assert name in manifest["files"]


def test_worker_never_reads_password_or_sensitive_targets():
    source = (ROOT / "integrations/windows-observer/screen_target.py").read_text()
    assert "CurrentIsPassword" in source and "ES_PASSWORD" in source
    # selection never comes from another top-level window
    assert 'root_handle(focused, iuia, walker) == window["hwnd"]' in source
    for forbidden in (
        "SendInput",
        "keybd_event",
        "mouse_event",
        "ShellExecute",
        "urlopen",
        "requests",
    ):
        assert forbidden not in source
    ocr = (ROOT / "integrations/windows-observer/ocr_crop.ps1").read_text()
    for forbidden in ("Invoke-WebRequest", "Invoke-RestMethod", "Out-File", "Set-Content"):
        assert forbidden not in ocr
    import re

    assert re.findall(r"\.Save\(([^,]+),", ocr) == ["$memory"]  # in-memory PNG only


def test_endpoint_needs_session_token_and_reports_indicator(tmp_path, monkeypatch):
    calls = []

    async def fake_read(request, access, notify=None):
        access.active, access.kind = True, "hover_target"
        notify and notify()
        calls.append(request)
        access.active, access.kind, access.reads = False, "", access.reads + 1
        notify and notify()
        return {"source": "uia_text", "target": "word", "cloud": False}

    monkeypatch.setattr(screen_target, "read_target", fake_read)
    settings = Settings(_env_file=None, data_dir=tmp_path, openrouter_api_key="")
    with TestClient(create_app(settings, TOKEN, factory=lambda: Idle())) as client:
        assert client.post("/v1/screen/target", json={"x": 1, "y": 2}).status_code == 401
        before = client.get("/v1/runtime/status", headers=AUTH).json()
        assert before["screen_access"] == {
            "active": False,
            "kind": "",
            "reads": 0,
            "last_ms": None,
            "last_source": "",
            "cloud": False,
        }
        response = client.post("/v1/screen/target", headers=AUTH, json={"x": 1, "y": 2})
        assert response.status_code == 200 and response.json()["target"] == "word"
        after = client.get("/v1/runtime/status", headers=AUTH).json()
        assert after["revision"] > before["revision"] and after["screen_access"]["reads"] == 1
        bad = client.post("/v1/screen/target", headers=AUTH, json={"x": 1, "y": 2, "unit": "page"})
        assert bad.status_code == 422
    assert len(calls) == 1


def test_not_a_model_capability():
    from immortility_broker import agent_bridge

    with pytest.raises(Exception):
        agent_bridge.capability_input("screen_target")


def test_off_windows_it_refuses(monkeypatch):
    import asyncio

    monkeypatch.setattr(screen_target.os, "name", "posix")
    request = screen_target.TargetRequest(x=1, y=1)
    with pytest.raises(BrokerError):
        asyncio.run(screen_target.read_target(request, screen_target.ScreenAccess()))


def test_embedded_object_placeholder_is_not_text():
    # Real-window finding (Edge canvas): UIA returned U+FFFC with a matching rectangle.
    source = (ROOT / "integrations/windows-observer/screen_target.py").read_text()
    assert 'text.replace("\\ufffc", "").strip() and exact' in source
