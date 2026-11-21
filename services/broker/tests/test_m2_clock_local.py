"""K23 regression: the clock tool answers in local time with an explicit offset."""

from datetime import datetime, timedelta, timezone

import pytest

from immortility_broker import local_tools
from immortility_broker.capabilities import ClockOutput

IST = timezone(timedelta(hours=5, minutes=30), "India Standard Time")


class FixedAware(datetime):
    """astimezone() without an argument converts to IST, like the owner's PC."""

    def astimezone(self, tz=None):
        return super().astimezone(tz or IST)


def reading(utc_hour, minute=8):
    moment = FixedAware(2026, 11, 21, utc_hour, minute, 30, tzinfo=timezone.utc)
    return local_tools.clock_reading(moment)


def test_utc_evening_is_next_morning_in_ist():
    # The K23 failure: 22:18 UTC was reported as "10:08 PM IST"; it is 03:48 IST next day.
    r = reading(22, 18)
    assert r["timestamp"] == "2026-11-22T03:48:30+05:30"
    assert r["utc"] == "2026-11-21T22:18:30+00:00"
    assert r["local"] == "3:48 AM on Sunday 22 November 2026 (IST, UTC+05:30)"


def test_label_is_ist_initials_and_noon_midnight():
    assert "(IST, UTC+05:30)" in reading(22, 18)["local"]
    assert reading(18, 30)["local"].startswith("12:00 AM on Sunday 22 November")
    assert reading(6, 30)["local"].startswith("12:00 PM on Saturday 21 November")


def test_output_contract_accepts_reading_and_old_shape():
    ClockOutput.model_validate(reading(22))
    ClockOutput.model_validate({"timestamp": "2026-11-14T00:00:00+00:00"})
    with pytest.raises(ValueError):
        ClockOutput.model_validate({"timestamp": "2026-11-22T03:48:30"})  # naive refused
    with pytest.raises(ValueError):
        ClockOutput.model_validate({**reading(22), "extra": "x"})


def test_zone_label_fallbacks():
    plain_utc = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert local_tools._zone_label(plain_utc) == "UTC+00:00"
    pst = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=-8), "Pacific Standard Time"))
    assert local_tools._zone_label(pst) == "PST, UTC-08:00"


def test_broker_answers_what_time_in_local_time(tmp_path):
    import time

    from fastapi.testclient import TestClient

    from immortility_broker.app import create_app
    from immortility_broker.config import Settings

    token = "test-session-credential-" + "x" * 32
    auth = {"Authorization": f"Bearer {token}"}
    (tmp_path / "local-tools.json").write_text('{"enabled": true}', encoding="utf-8")
    settings = Settings(_env_file=None, data_dir=tmp_path, openrouter_api_key="")

    class Never:
        async def run(self, content, history):
            raise AssertionError("the clock answer must not need a model")
            yield ""

        async def stop(self):
            pass

    with TestClient(create_app(settings, token, factory=lambda: Never())) as client:
        session = client.post("/v1/sessions", headers=auth).json()["id"]
        body = {
            "session_id": session,
            "request_id": "k23",
            "content": "what time is it",
            "cloud_consent": True,
        }
        task_id = client.post("/v1/tasks", headers=auth, json=body).json()["task_id"]
        for _ in range(300):
            task = client.get(f"/v1/tasks/{task_id}", headers=auth).json()
            if task["status"] in {"succeeded", "failed", "blocked"}:
                break
            time.sleep(0.01)
    assert task["status"] == "succeeded", task
    text = task["result"]["text"]
    assert text.startswith("Local time: ") and "(" in text and "UTC" in text
