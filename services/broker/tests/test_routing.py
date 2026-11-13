import time

from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.routing import classify

TOKEN = "test-session-credential-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_trivial_question_stays_on_the_direct_path():
    plan = classify("What is two plus two?")
    assert plan.mode == "fast" and plan.roles == () and plan.call_limit == 2


def test_a_bugfix_does_not_start_research():
    plan = classify("Fix the bug in calc.py")
    assert plan.mode == "standard" and plan.roles == ("coding",)


def test_apply_and_review_request_both_roles():
    plan = classify("Fix the bug in calc.py and apply the change.")
    assert plan.mode == "workflow"
    assert plan.roles == ("coding", "review")


class Once:
    def __init__(self):
        self.calls = 0

    async def run(self, content, history, role=None):
        self.calls += 1
        assert role is None
        yield "Four."

    async def stop(self):
        return None


def test_enabled_specialists_still_skip_a_trivial_question(tmp_path):
    runtime = Once()
    settings = Settings(
        _env_file=None, data_dir=tmp_path, delegation_enabled=True, openrouter_api_key=""
    )
    with TestClient(create_app(settings, TOKEN, factory=lambda: runtime)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "fast-1",
                "content": "What is two plus two?",
                "cloud_consent": True,
            },
        )
        task_id = created.json()["task_id"]
        for _ in range(200):
            task = client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()
            if task["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.01)
        body = client.get(f"/v1/tasks/{task_id}/events", headers=AUTH).text
    assert task["status"] == "succeeded"
    assert runtime.calls == 1
    assert "agent.started" not in body
    assert '"route_mode": "fast"' in body or '"route_mode":"fast"' in body
