"""Offline repair: a real failing unittest, an exact patch, approval, and a rerun."""

from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from test_workspace import AUTH, TOKEN


def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8", newline="\n")
    (root / "test_calc.py").write_text(
        "import unittest\nfrom calc import add\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(1, 2), 3)\n",
        encoding="utf-8",
        newline="\n",
    )
    return root


def settings(tmp_path, root):
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "state",
        hermes_source=tmp_path / "absent",
        workspace_root=root,
        workspace_tools_enabled=True,
        openrouter_api_key="",
        groq_api_key="",
        gemini_api_key="",
        nvidia_api_key="",
    )


def propose(client, session, content, request_id="fix-1"):
    return client.post(
        "/v1/repairs",
        headers=AUTH,
        json={
            "session_id": session,
            "request_id": request_id,
            "path": "calc.py",
            "test_path": "test_calc.py",
            "content": content,
            "write_consent": True,
        },
    )


def test_failing_unittest_is_patched_only_after_approval_and_then_passes(tmp_path):
    root = repo(tmp_path)

    def forbidden():
        raise AssertionError("A local repair must not start Hermes")

    fixed = "def add(a, b):\n    return a + b\n"
    with TestClient(create_app(settings(tmp_path, root), TOKEN, factory=forbidden)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = propose(client, session, fixed)
        assert created.status_code == 200, created.text
        task = created.json()
        assert task["status"] == "awaiting_approval"
        assert task["input"]["no_cloud"] is True
        assert "return a - b" in (root / "calc.py").read_text(encoding="utf-8")
        approved = client.post(
            f"/v1/tasks/{task['task_id']}/approval",
            headers=AUTH,
            json={"decision": "approve"},
        )
        assert approved.status_code == 200, approved.text
        done = approved.json()
    assert done["status"] == "succeeded"
    assert done["result"]["provider"] == "local"
    assert done["result"]["model"] == "project.repair.v1"
    assert "Allowlisted unittest passed" in done["result"]["text"]
    assert "return a + b" in (root / "calc.py").read_text(encoding="utf-8")
    remembered = client_memory(tmp_path, root, session, done["task_id"])
    assert any("unittest passed" in item["body"] for item in remembered)


def client_memory(tmp_path, root, session, task_id):
    with TestClient(create_app(settings(tmp_path, root), TOKEN)) as client:
        return client.post(
            "/v1/memory/search",
            headers=AUTH,
            json={"session_id": session, "query": "unittest passed"},
        ).json()["matches"]


def test_denied_or_incorrect_patch_does_not_keep_the_change(tmp_path):
    root = repo(tmp_path)
    wrong = "def add(a, b):\n    return a * b\n"
    with TestClient(create_app(settings(tmp_path, root), TOKEN)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        denied = propose(client, session, wrong, "fix-deny")
        assert denied.status_code == 200
        task_id = denied.json()["task_id"]
        refused = client.post(
            f"/v1/tasks/{task_id}/approval", headers=AUTH, json={"decision": "deny"}
        )
        assert refused.json()["status"] == "blocked"
        assert "return a - b" in (root / "calc.py").read_text(encoding="utf-8")
        proposed = propose(client, session, wrong, "fix-wrong")
        assert proposed.status_code == 200
        failed = client.post(
            f"/v1/tasks/{proposed.json()['task_id']}/approval",
            headers=AUTH,
            json={"decision": "approve"},
        )
        assert failed.json()["status"] == "failed"
    assert "return a - b" in (root / "calc.py").read_text(encoding="utf-8")


def test_cancelling_a_repair_leaves_the_file_unchanged(tmp_path):
    root = repo(tmp_path)
    fixed = "def add(a, b):\n    return a + b\n"
    with TestClient(create_app(settings(tmp_path, root), TOKEN)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = propose(client, session, fixed, "fix-cancel")
        assert created.status_code == 200
        task_id = created.json()["task_id"]
        cancelled = client.post(f"/v1/tasks/{task_id}/cancel", headers=AUTH)
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
    assert "return a - b" in (root / "calc.py").read_text(encoding="utf-8")


def test_repair_rejects_a_shell_shaped_test_path(tmp_path):
    root = repo(tmp_path)
    with TestClient(create_app(settings(tmp_path, root), TOKEN)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        rejected = client.post(
            "/v1/repairs",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "bad",
                "path": "calc.py",
                "test_path": "test_calc.py & calc",
                "content": "def add(a, b):\n    return a + b\n",
                "write_consent": True,
            },
        )
    assert rejected.status_code == 403
    assert "return a - b" in (root / "calc.py").read_text(encoding="utf-8")
