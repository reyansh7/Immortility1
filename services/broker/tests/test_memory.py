import time

from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.memory import (
    experience_record,
    format_facts,
    prior_task_notes,
    redact,
    retrieve,
    trim_history,
)
from immortility_broker.store import Store
from test_workspace import AUTH, TOKEN


def test_retrieve_keeps_the_matching_paragraph_only():
    text = "Alpha has nothing useful.\nThe broker stores task notes locally."
    selected = retrieve(text, "where are task notes stored")
    assert "task notes" in selected
    assert "Alpha" not in selected


def test_trim_history_keeps_the_newest_messages():
    history = [
        {"role": "user", "content": "old " * 20},
        {"role": "assistant", "content": "older"},
        {"role": "user", "content": "keep this"},
    ]
    trimmed = trim_history(history, 12)
    assert trimmed[-1]["content"] == "keep this"
    assert "old" not in "".join(item["content"] for item in trimmed)


def test_prior_notes_ignore_unrelated_tasks():
    tasks = [
        {
            "task_id": "1",
            "status": "succeeded",
            "input": {"content": "python length function"},
            "result": {"text": "Use len."},
        },
        {
            "task_id": "2",
            "status": "succeeded",
            "input": {"content": "bake a cake"},
            "result": {"text": "Use flour."},
        },
    ]
    notes = prior_task_notes(tasks, "python string length", "3")
    assert "len" in notes
    assert "flour" not in notes


def test_verified_experience_survives_restart_and_stays_in_its_session(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = Store(path)
    first = store.session()["id"]
    second = store.session()["id"]
    from immortility_broker.contracts import TaskRequest

    task, _ = store.create(
        TaskRequest(
            session_id=first,
            request_id="clock-experience",
            content="Check the UTC time with the clock tool",
            cloud_consent=True,
        )
    )
    record = experience_record(
        request="Check the UTC time with the clock tool. api_key=super-secret-value",
        provider="groq",
        model="openai/gpt-oss-120b",
        tools=["clock.now.v1"],
        outcome="ok",
    )
    assert "super-secret" not in record
    assert "clock.now.v1" in record
    assert "groq" in record
    store.remember(first, task["task_id"], record)
    store.db.close()

    opened = Store(path)
    found = opened.recall(first, "UTC clock time")
    assert any("clock.now.v1" in item["body"] for item in found)
    assert opened.recall(second, "UTC clock time") == []
    assert opened.recall(first, "unrelated baking") == []
    assert "abcdefghijklmnop" not in redact("bearer abcdefghijklmnop")
    opened.db.close()


def test_confirmed_facts_persist_correct_and_stay_in_project_scope(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = Store(path)
    project = "a" * 64
    other = "b" * 64
    preference = store.confirm_fact("user", "", "preference", "Prefer dark compact answers")
    duplicate = store.confirm_fact("user", "", "preference", "Prefer dark compact answers")
    decision = store.confirm_fact(
        "project", project, "decision", "Keep the broker as the permission boundary"
    )
    assert duplicate["id"] == preference["id"]
    store.db.close()

    opened = Store(path)
    restored = opened.recall_facts("dark compact answers", "")
    assert [item["id"] for item in restored] == [preference["id"]]
    assert restored[0]["trust"] == "user-confirmed"
    assert all(
        item["id"] != decision["id"] for item in opened.recall_facts("permission boundary", "")
    )
    assert all(
        item["id"] != decision["id"] for item in opened.recall_facts("permission boundary", other)
    )
    scoped = opened.recall_facts("permission boundary", project)
    assert [item["id"] for item in scoped] == [decision["id"]]
    assert any(
        item["id"] == preference["id"] for item in opened.recall_facts("compact answers", project)
    )

    corrected = opened.correct_fact(preference["id"], "Prefer short plain answers")
    assert corrected["supersedes"] == preference["id"]
    assert corrected["status"] == "active"
    visible = opened.recall_facts("answers", project)
    assert [item["body"] for item in visible if item["scope"] == "user"] == [
        "Prefer short plain answers"
    ]
    assert opened.recall_facts("dark compact", "") == []
    opened.revoke_fact(corrected["id"])
    assert opened.recall_facts("plain answers", "") == []
    started = time.perf_counter()
    bounded = opened.recall_facts("permission boundary", project)
    elapsed = time.perf_counter() - started
    assert elapsed < 0.1
    assert sum(len(item["body"]) for item in bounded) <= 800
    packed = format_facts(bounded)
    assert "permission boundary" in packed and len(packed) <= 400
    opened.db.close()

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "app",
        hermes_source=tmp_path / "absent",
        openrouter_api_key="",
        groq_api_key="PROJECT_SECRET_CANARY_123456789",
        gemini_api_key="",
        nvidia_api_key="",
    )
    with TestClient(create_app(settings, TOKEN)) as client:
        saved = client.post(
            "/v1/memory/facts",
            headers=AUTH,
            json={
                "kind": "preference",
                "scope": "user",
                "text": "Prefer short plain answers",
                "confirmed": True,
            },
        )
        assert saved.status_code == 200, saved.text
        denied = client.post(
            "/v1/memory/facts",
            headers=AUTH,
            json={
                "kind": "preference",
                "scope": "user",
                "text": "Remember PROJECT_SECRET_CANARY_123456789",
                "confirmed": True,
            },
        )
        assert denied.status_code == 403
        unconfirmed = client.post(
            "/v1/memory/facts",
            headers=AUTH,
            json={
                "kind": "preference",
                "scope": "user",
                "text": "Prefer short plain answers",
                "confirmed": False,
            },
        )
        assert unconfirmed.status_code == 422
