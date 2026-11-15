import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.workspace import locate, real_root

TOKEN = "test-session-credential-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_workspace_rejects_escape_and_protected_paths(tmp_path):
    (tmp_path / "calc.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    assert locate(tmp_path, "calc.py").name == "calc.py"
    with pytest.raises(BrokerError):
        locate(tmp_path, "../outside.py")
    with pytest.raises(BrokerError):
        locate(tmp_path, ".env")
    with pytest.raises(BrokerError):
        real_root(Path(tmp_path.anchor))


def test_link_is_not_followed(tmp_path):
    target = tmp_path / "inside"
    target.mkdir()
    link = tmp_path / "jump"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if created.returncode != 0:
            pytest.skip("This Windows account cannot create a link.")
    with pytest.raises(BrokerError):
        locate(tmp_path, "jump/secret.py")


class CodingHermes:
    async def run(self, content, history, role=None):
        if role == "review":
            assert "Code execution is disabled" in content
            yield "The patch is present. Tests were not run.\nVERDICT: pass"
            return
        assert "return a - b" in content
        yield ("The function subtracts.\nPATCH calc.py\n<<<\ndef add(a, b):\n    return a + b\n>>>")

    async def stop(self):
        return None


def _wait(client, task_id, allowed):
    for _ in range(200):
        task = client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()
        if task["status"] in allowed:
            return task
        time.sleep(0.01)
    pytest.fail("Task did not reach " + ",".join(allowed))


def test_approved_patch_is_applied_and_tested(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "calc.py").write_text(
        "def add(a, b):\n    return a - b\n", encoding="utf-8", newline="\n"
    )
    (repo / "test_calc.py").write_text(
        "import unittest\nfrom calc import add\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(1, 2), 3)\n",
        encoding="utf-8",
        newline="\n",
    )
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "state",
        delegation_enabled=True,
        workspace_tools_enabled=True,
        workspace_root=repo,
        openrouter_api_key="",
    )
    with TestClient(create_app(settings, TOKEN, factory=CodingHermes)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "bug-1",
                "content": "Fix the bug in calc.py and apply the change.",
                "cloud_consent": True,
            },
        )
        waiting = _wait(client, created.json()["task_id"], {"awaiting_approval", "failed"})
        assert waiting["status"] == "awaiting_approval"
        assert "return a - b" in (repo / "calc.py").read_text(encoding="utf-8")
        approved = client.post(
            f"/v1/tasks/{waiting['task_id']}/approval",
            headers=AUTH,
            json={"decision": "approve"},
        )
        assert approved.status_code == 200
        body = approved.json()
    assert "return a + b" in (repo / "calc.py").read_text(encoding="utf-8")
    assert body["status"] == "succeeded"
    assert "Code execution is disabled" in body["result"]["text"]
    assert "VERDICT: pass" in body["result"]["text"]
    with TestClient(create_app(settings, TOKEN, factory=CodingHermes)) as client:
        restored = client.post(f"/v1/tasks/{waiting['task_id']}/rollback", headers=AUTH)
        trace = client.get(f"/v1/tasks/{waiting['task_id']}/trace", headers=AUTH).json()
    assert restored.status_code == 200
    assert "return a - b" in (repo / "calc.py").read_text(encoding="utf-8")
    names = [call["name"] for call in trace["tools"]["calls"]]
    assert trace["tools"]["status"] == "authorized"
    assert "patch" in names and "unittest" not in names


def test_denied_approval_does_not_write(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    original = "def add(a, b):\n    return a - b\n"
    (repo / "calc.py").write_text(original, encoding="utf-8", newline="\n")
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "state",
        workspace_tools_enabled=True,
        workspace_root=repo,
        openrouter_api_key="",
    )
    with TestClient(create_app(settings, TOKEN, factory=CodingHermes)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "bug-2",
                "content": "Fix the bug in calc.py and apply the change.",
                "cloud_consent": True,
            },
        )
        waiting = _wait(client, created.json()["task_id"], {"awaiting_approval", "failed"})
        denied = client.post(
            f"/v1/tasks/{waiting['task_id']}/approval",
            headers=AUTH,
            json={"decision": "deny"},
        )
    assert denied.json()["status"] == "blocked"
    assert (repo / "calc.py").read_text(encoding="utf-8") == original


class EscapeHermes:
    async def run(self, content, history, role=None):
        yield "PATCH ../outside.py\n<<<\nprint('escaped')\n>>>"

    async def stop(self):
        return None


def _task(tmp_path, factory):
    repo = tmp_path / "repo"
    repo.mkdir()
    original = "def add(a, b):\n    return a - b\n"
    (repo / "calc.py").write_text(original, encoding="utf-8", newline="\n")
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "state",
        workspace_tools_enabled=True,
        workspace_root=repo,
        openrouter_api_key="",
    )
    return repo, original, settings, factory


def test_malicious_patch_never_leaves_the_workspace(tmp_path):
    repo, original, settings, factory = _task(tmp_path, EscapeHermes)
    with TestClient(create_app(settings, TOKEN, factory=factory)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "bug-escape",
                "content": "Fix the bug in calc.py and apply the change.",
                "cloud_consent": True,
            },
        )
        finished = _wait(client, created.json()["task_id"], {"blocked", "awaiting_approval"})
    assert finished["status"] == "blocked"
    assert finished["error"]["code"] == "tool_denied"
    assert (repo / "calc.py").read_text(encoding="utf-8") == original
    assert not (tmp_path / "outside.py").exists()


def test_changed_file_conflicts_instead_of_being_overwritten(tmp_path):
    repo, original, settings, factory = _task(tmp_path, CodingHermes)
    with TestClient(create_app(settings, TOKEN, factory=factory)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "bug-conflict",
                "content": "Fix the bug in calc.py and apply the change.",
                "cloud_consent": True,
            },
        )
        waiting = _wait(client, created.json()["task_id"], {"awaiting_approval", "failed"})
        (repo / "calc.py").write_text(
            "def add(a, b):\n    return a\n", encoding="utf-8", newline="\n"
        )
        conflict = client.post(
            f"/v1/tasks/{waiting['task_id']}/approval",
            headers=AUTH,
            json={"decision": "approve"},
        )
    assert conflict.status_code == 200
    assert conflict.json()["status"] == "failed"
    assert conflict.json()["error"]["code"] == "stale_workspace"
    assert (repo / "calc.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a\n"


def test_cancel_during_approval_does_not_write(tmp_path):
    repo, original, settings, factory = _task(tmp_path, CodingHermes)
    with TestClient(create_app(settings, TOKEN, factory=factory)) as client:
        session = client.post("/v1/sessions", headers=AUTH).json()["id"]
        created = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session,
                "request_id": "bug-cancel",
                "content": "Fix the bug in calc.py and apply the change.",
                "cloud_consent": True,
            },
        )
        pending = _wait(client, created.json()["task_id"], {"awaiting_approval", "failed"})
        cancelled = client.post(f"/v1/tasks/{pending['task_id']}/cancel", headers=AUTH)
    assert cancelled.json()["status"] == "cancelled"
    assert (repo / "calc.py").read_text(encoding="utf-8") == original
