"""Usage is reported, unknown, or not applicable. A missing report is not zero spend."""

import sqlite3

import httpx

from immortility_broker.app import apply_gateway_flag
from immortility_broker.config import Settings
from immortility_broker.hermes_gateway import GatewaySupervisor, WarmGateway, run_phase
from immortility_broker.ledger import Ledger, billing_view, local_billing, quota_headers
from immortility_broker.permission_policy import govern


def test_provider_usage_is_unverified_and_reasoning_is_not_added_twice():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    ledger = Ledger(db)
    attempt = ledger.begin("task", 100000, 6, "groq/openai/gpt-oss-120b")
    ledger.bind_route(
        attempt, "groq", "openai/gpt-oss-120b", "single-broker-account", "groq/openai/gpt-oss-120b"
    )
    call = ledger.reserve(attempt, 1000, 500)
    ledger.settle(
        call,
        {
            "prompt_tokens": 100,
            "completion_tokens": 40,
            "completion_tokens_details": {"reasoning_tokens": 15},
            "prompt_tokens_details": {"cached_tokens": 8},
        },
    )
    view = billing_view(ledger.summary("task"))
    assert view["billing_status"] == "reported_unverified"
    assert view["verified_billed_usd"] is None
    assert view["prompt_tokens"] == 100
    assert view["completion_tokens"] == 40
    assert view["charged_tokens"] == 140
    reported = ledger.details("task")["calls"][0]["reported"]
    assert reported["reasoning_tokens"] == 15
    assert reported["reasoning_included_in_completion"] is True
    assert reported["cached_tokens"] == 8
    missing = ledger.reserve(attempt, 64, 32)
    ledger.settle(missing, None)
    unknown = billing_view(ledger.summary("task"))
    assert unknown["billing_status"] == "unknown"
    assert unknown["verified_billed_usd"] is None
    assert local_billing()["billing_status"] == "not_applicable"


def test_quota_headers_drop_credentials_and_a_stop_is_not_completion():
    class Headers(dict):
        pass

    headers = Headers(
        {
            "x-ratelimit-remaining-requests": "12",
            "authorization": "Bearer secret",
            "retry-after": "3",
        }
    )
    assert quota_headers(headers) == {
        "x-ratelimit-remaining-requests": "12",
        "retry-after": "3",
    }
    assert run_phase("stopping") == "stopping"
    assert run_phase("cancelled") == "cancelled"
    assert run_phase("stopping") != "completed"


def test_gateway_reuse_does_not_invent_a_zero_startup(tmp_path):
    supervisor = GatewaySupervisor(
        Settings(_env_file=None, data_dir=tmp_path), "http://127.0.0.1:9"
    )
    supervisor.gateway = WarmGateway("http://127.0.0.1:9", "k" * 32, httpx.AsyncClient())
    supervisor.state = "ready"
    supervisor.cold_start_ms = 12.5
    first = supervisor.session()
    second = supervisor.session()
    assert first.spawn_ms == 12.5
    assert first.reused is False
    assert second.spawn_ms is None
    assert second.reused is True


def test_gateway_flag_stays_off_until_the_local_file_opts_in(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path)
    apply_gateway_flag(settings)
    assert settings.hermes_0232_gateway is False
    (tmp_path / "hermes-gateway.json").write_text('{"enabled": true}\n', encoding="utf-8")
    apply_gateway_flag(settings)
    assert settings.hermes_0232_gateway is True


def test_live_boundary_denies_ungoverned_tools_without_a_model():
    allowed = ("clock.now.v1", "arithmetic.multiply.v1", "project.outline.v1")
    denied = (
        "shell.exec",
        "browser.navigate",
        "computer_use.click",
        "yolo",
        "mcp.install",
        "unknown.tool",
    )
    assert all(govern(name, "assisted") == "allow" for name in allowed)
    assert all(govern(name, "assisted") == "deny" for name in denied)
