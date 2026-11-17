"""Read-only storage classification and bounded reveal. No deletion and no cloud."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from immortility_broker.app import create_app
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
import os
import subprocess

from immortility_broker.storage_audit import (
    allowed_target,
    authorize,
    classify,
    intent,
    render,
    resource_summary,
    save_report,
    scan,
)


def test_scan_classifies_rebuildable_cache_and_does_not_delete(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    modules = downloads / "node_modules"
    modules.mkdir(parents=True)
    (modules / "left.txt").write_text("keep", encoding="utf-8")
    documents = tmp_path / "Documents"
    documents.mkdir()
    (documents / "taxes.txt").write_text("personal", encoding="utf-8")
    before = (modules / "left.txt").read_text(encoding="utf-8")

    report = scan(tmp_path, seconds=2, max_entries=100)
    assert report["deleted"] is False
    assert (modules / "left.txt").read_text(encoding="utf-8") == before
    classes = {item["name"]: item["class"] for item in report["items"]}
    assert classes["node_modules"] == "rebuildable-candidate"
    assert classes["taxes.txt"] == "user-data"
    text = render(report)
    assert "No files were opened or deleted" in text
    assert "node_modules" in text


def test_reveal_accepts_downloads_and_refuses_a_foreign_path(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    opened: list[list[str]] = []
    assert intent("Open File Explorer and show me my Downloads folder") == (
        "desktop.reveal.v1",
        {"target": "downloads"},
    )
    assert intent("What is the weather") is None
    path, selecting = allowed_target(tmp_path, "downloads", tmp_path)
    assert selecting is False
    assert path == downloads.resolve()
    from immortility_broker.storage_audit import reveal

    text = reveal(tmp_path, "downloads", tmp_path, launcher=opened.append)
    assert opened == [["explorer.exe", str(downloads.resolve())]]
    assert "File Explorer" in text
    outside = tmp_path.parent / "outside-folder"
    outside.mkdir(exist_ok=True)
    save_report(
        tmp_path,
        {
            "items": [
                {
                    "path": str(outside),
                    "name": "outside",
                    "class": "rebuildable-candidate",
                    "bytes": 1,
                }
            ]
        },
    )
    with pytest.raises(BrokerError) as caught:
        allowed_target(tmp_path, "largest-rebuildable", tmp_path)
    assert caught.value.code == "tool_denied"
    assert caught.value.message == "Refusing to open a path outside the user profile."


TOKEN = "test-session-credential-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_storage_question_stays_local_and_does_not_call_a_model(tmp_path: Path, monkeypatch):
    modules = tmp_path / "Downloads" / "node_modules"
    modules.mkdir(parents=True)
    (modules / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("immortility_broker.app.Path.home", lambda: tmp_path)
    called: list[str] = []

    class UnusedModel:
        async def run(self, content, history):
            del history
            called.append(content)
            yield "unused"

        async def stop(self):
            return None

    settings = Settings(
        _env_file=None, data_dir=tmp_path / "data", laptop_tools_enabled=True
    )
    with TestClient(create_app(settings, TOKEN, factory=lambda: UnusedModel())) as client:
        session_id = client.post("/v1/sessions", headers=AUTH).json()["id"]
        response = client.post(
            "/v1/tasks",
            headers=AUTH,
            json={
                "session_id": session_id,
                "request_id": "storage-1",
                "content": "Immortility, analyze my laptop and tell me what is taking up space.",
                "cloud_consent": True,
            },
        )
        task_id = response.json()["task_id"]
        for _ in range(200):
            task = client.get(f"/v1/tasks/{task_id}", headers=AUTH).json()
            if task["status"] in {"succeeded", "failed", "blocked", "cancelled"}:
                break
            time.sleep(0.01)
        else:
            pytest.fail("storage task did not settle")
    assert task["status"] == "succeeded"
    assert task["result"]["provider"] == "local"
    assert task["result"]["billing_status"] == "not_applicable"
    assert task["result"]["verified_billed_usd"] is None
    assert "node_modules" in task["result"]["text"]
    assert "rebuildable-candidate" in task["result"]["text"]
    assert called == []


def test_junction_and_protected_paths_are_refused(tmp_path: Path, monkeypatch):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    outside = tmp_path.parent / "junction-target"
    outside.mkdir(exist_ok=True)
    link = downloads / "escape"
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    save_report(
        tmp_path,
        {
            "items": [
                {
                    "path": str(link),
                    "name": "escape",
                    "class": "rebuildable-candidate",
                    "bytes": 1,
                }
            ]
        },
    )
    with pytest.raises(BrokerError) as caught:
        allowed_target(tmp_path, "largest-rebuildable", tmp_path)
    assert caught.value.message == "Refusing to follow a symlink or junction."
    protected = tmp_path / "Windows"
    protected.mkdir()
    monkeypatch.setenv("SystemRoot", str(protected))
    save_report(
        tmp_path,
        {
            "items": [
                {
                    "path": str(protected),
                    "name": "Windows",
                    "class": "rebuildable-candidate",
                    "bytes": 1,
                }
            ]
        },
    )
    with pytest.raises(BrokerError) as protected_error:
        allowed_target(tmp_path, "largest-rebuildable", tmp_path)
    assert protected_error.value.message == "Refusing to open a protected Windows folder."
    with pytest.raises(BrokerError) as network:
        authorize(tmp_path, Path(r"\\server\share"))
    assert network.value.message == "Refusing to open a network path."


def test_reveal_selects_only_a_real_file_in_downloads(tmp_path: Path, monkeypatch):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    target = downloads / "notes.txt"
    target.write_text("local", encoding="utf-8")
    selected: list[Path] = []
    assert intent("Show notes.txt in my Downloads") == (
        "desktop.reveal.v1",
        {"target": "downloads-file", "name": "notes.txt"},
    )
    from immortility_broker.storage_audit import reveal

    text = reveal(
        tmp_path,
        "downloads-file",
        tmp_path,
        name="notes.txt",
        select_item=selected.append,
    )
    assert selected == [Path(os.path.realpath(target))]
    assert "selected" in text
    with pytest.raises(BrokerError) as escaped:
        allowed_target(tmp_path, "downloads-file", tmp_path, name=r"..\secret.txt")
    assert escaped.value.message == "That file name is not allowed."
    class Linked:
        name = "linked.txt"
        path = str(downloads / "linked.txt")

        def is_symlink(self) -> bool:
            return True

        def is_junction(self) -> bool:
            return False

        def is_file(self, follow_symlinks: bool = True) -> bool:
            del follow_symlinks
            return True

    class Listing:
        def __enter__(self) -> object:
            return iter([Linked()])

        def __exit__(self, *args: object) -> bool:
            del args
            return False

    monkeypatch.setattr("immortility_broker.storage_audit.os.scandir", lambda folder: Listing())
    with pytest.raises(BrokerError) as missing:
        allowed_target(tmp_path, "downloads-file", tmp_path, name="linked.txt")
    assert missing.value.message == "That file is not in the authorized folder."


def test_cancelled_scan_does_not_delete(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    kept = downloads / "keep.txt"
    kept.write_text("stay", encoding="utf-8")
    report = scan(tmp_path, cancelled=lambda: True)
    assert report["cancelled"] is True
    assert report["deleted"] is False
    assert report["uploaded"] is False
    assert kept.read_text(encoding="utf-8") == "stay"
    assert "cancelled" in render(report)


def test_resource_summary_uses_the_supplied_sample():
    text = resource_summary(lambda: [("explorer", 50 * 1024 * 1024), ("other", 1024)])
    assert "Highest working set: explorer" in text
    assert "50.0 MB" in text
    assert intent("Which application is consuming the most RAM") == ("laptop.resources.v1", {})


def test_classify_keeps_documents_as_user_data():
    assert classify("notes", "Documents") == "user-data"
    assert classify("node_modules", "Downloads") == "rebuildable-candidate"
    assert classify("setup.exe", "Downloads") == "installer-candidate"
    assert classify("clip.mp4", "Downloads") == "user-media"


def test_one_large_download_folder_does_not_hide_documents(tmp_path: Path):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    for index in range(20):
        (downloads / f"file-{index}.txt").write_text("x", encoding="utf-8")
    documents = tmp_path / "Documents" / "notes"
    documents.mkdir(parents=True)
    (documents / "kept.txt").write_text("personal", encoding="utf-8")
    report = scan(tmp_path, seconds=2, max_entries=10)
    names = {item["name"] for item in report["items"]}
    assert "notes" in names
    assert next(item for item in report["items"] if item["name"] == "notes")["class"] == "user-data"
