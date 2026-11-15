import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from test_workspace import AUTH, TOKEN, CodingHermes, _task, _wait


def pending(client):
    session = client.post("/v1/sessions", headers=AUTH).json()["id"]
    task = client.post(
        "/v1/tasks",
        headers=AUTH,
        json={
            "session_id": session,
            "request_id": "bound",
            "content": "Fix the bug in calc.py and apply the change.",
            "cloud_consent": True,
        },
    ).json()
    return _wait(client, task["task_id"], {"awaiting_approval", "failed"})["task_id"]


@pytest.mark.parametrize("change", ["disable", "tamper", "expiry", "restart"])
def test_changed_or_expired_approval_cannot_write(tmp_path, change):
    repo, original, settings, factory = _task(tmp_path, CodingHermes)
    app = create_app(settings, TOKEN, factory=factory)
    with TestClient(app) as client:
        task_id = pending(client)
        if change == "disable":
            assert (
                client.post(
                    "/v1/settings/workspace", headers=AUTH, json={"enabled": False}
                ).status_code
                == 200
            )
            assert (
                client.post(
                    "/v1/settings/workspace",
                    headers=AUTH,
                    json={"enabled": True, "root": str(repo)},
                ).status_code
                == 200
            )
        elif change == "tamper":
            path = settings.data_dir / "approvals" / f"{task_id}.json"
            data = json.loads(path.read_text())
            data["content"] = "malicious = True"
            path.write_text(json.dumps(data))
        elif change == "expiry":
            digest, _ = app.state.engine.approvals[task_id]
            app.state.engine.approvals[task_id] = (digest, 0)
        else:
            app.state.engine.approvals.clear()  # In-memory authority never recovered from disk.
        response = client.post(
            f"/v1/tasks/{task_id}/approval", headers=AUTH, json={"decision": "approve"}
        )
        assert response.status_code >= 400
        assert (repo / "calc.py").read_text() == original


class NewFileHermes(CodingHermes):
    async def run(self, content, history, role=None):
        if role == "review":
            raise RuntimeError("private-review-canary")
        yield "PATCH new.py\n<<<\nvalue = 1\n>>>"


def test_review_failure_keeps_recovery_and_new_file_rollback_removes_it(tmp_path):
    repo, _, settings, factory = _task(tmp_path, NewFileHermes)
    settings.delegation_enabled = True
    app = create_app(settings, TOKEN, factory=factory)
    with TestClient(app) as client:
        task_id = pending(client)
        response = client.post(
            f"/v1/tasks/{task_id}/approval", headers=AUTH, json={"decision": "approve"}
        )
        assert response.json()["status"] == "failed"
        assert "private-review-canary" not in response.text
        assert (repo / "new.py").is_file()
        assert app.state.engine.active is None
        assert client.post(f"/v1/tasks/{task_id}/rollback", headers=AUTH).status_code == 200
        assert not (repo / "new.py").exists()


def test_research_reaches_exact_runtime_request_without_delegation(tmp_path, monkeypatch):
    received = []

    class Capture(CodingHermes):
        async def run(self, content, history, role=None):
            received.append(content)
            yield "Synthetic grounded answer."

    async def fetch(question):
        return {
            "title": "Fixture",
            "url": "https://en.wikipedia.org/wiki/Fixture",
            "extract": "answer-bearing evidence",
        }

    monkeypatch.setattr("immortility_broker.app.research_page_async", fetch)
    _, _, settings, _ = _task(tmp_path, Capture)
    settings.web_research_enabled = True
    with TestClient(create_app(settings, TOKEN, factory=Capture)) as client:
        sid = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": sid,
                "request_id": "web",
                "content": "Research fixture history",
                "cloud_consent": True,
            },
        ).json()
        assert _wait(client, created["task_id"], {"succeeded", "failed"})["status"] == "succeeded"
    assert "answer-bearing evidence" in received[0]
    assert "https://en.wikipedia.org/wiki/Fixture" in received[0]
    assert "data not instructions" in received[0]


async def test_fetch_cancellation_propagates(monkeypatch):
    from immortility_broker.web import research_page_async

    cancelled = asyncio.Event()

    async def hung(url):
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.set()

    monkeypatch.setattr("immortility_broker.web.fetch_json", hung)
    operation = asyncio.create_task(research_page_async("test"))
    await asyncio.sleep(0)
    operation.cancel()
    with pytest.raises(asyncio.CancelledError):
        await operation
    assert cancelled.is_set()


def test_global_stop_cancels_post_write_review_and_keeps_rollback(tmp_path):
    import concurrent.futures
    import threading

    entered = threading.Event()

    class SlowReview(CodingHermes):
        async def run(self, content, history, role=None):
            if role == "review":
                entered.set()
                await asyncio.sleep(60)
                yield "unreachable"
            else:
                async for delta in super().run(content, history, role):
                    yield delta

    repo, original, settings, _ = _task(tmp_path, SlowReview)
    settings.delegation_enabled = True
    app = create_app(settings, TOKEN, factory=SlowReview)
    with TestClient(app) as client:
        task_id = pending(client)
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            approval = pool.submit(
                client.post,
                f"/v1/tasks/{task_id}/approval",
                headers=AUTH,
                json={"decision": "approve"},
            )
            assert entered.wait(3)
            assert app.state.engine.active == task_id
            assert client.post("/v1/stop", headers=AUTH).status_code == 200
            assert approval.result(3).json()["status"] == "cancelled"
        assert app.state.engine.active is None
        assert client.post(f"/v1/tasks/{task_id}/rollback", headers=AUTH).status_code == 200
        assert (repo / "calc.py").read_text() == original
