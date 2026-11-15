"""Security regressions use synthetic scratch data only."""

import os

import pytest

from immortility_broker.contracts import BrokerError, TaskRequest
from immortility_broker.memory import prior_task_notes
from immortility_broker.store import Store
from immortility_broker.workspace import apply_proposed, fingerprint, locate, read_source


@pytest.mark.parametrize(
    "name",
    [
        "CREDENTIALS.JSON",
        ".GIT/config.json",
        ".ENV",
        ".env.local",
        "credentials.json.",
        "credentials.json ",
        "ＣＲＥＤＥＮＴＩＡＬＳ.json",
        "CON.txt",
        "lpt1.py",
        "file.py:stream",
        "//server/share.py",
        "dir/../file.py",
        "dir//file.py",
        "file~1.py",
    ],
)
def test_windows_path_aliases_are_denied(tmp_path, name):
    with pytest.raises(BrokerError, match="tool_denied"):
        locate(tmp_path, name)


def test_crlf_byte_identity_and_safe_temporary_file(tmp_path):
    path = tmp_path / "example.py"
    original = b"first = 1\r\nsecond = 2\r\n"
    path.write_bytes(original)
    legacy_temp = tmp_path / "example.py.immortility-tmp"
    legacy_temp.write_bytes(b"unrelated existing file")
    text = read_source(tmp_path, "example.py")
    assert text.encode() == original
    apply_proposed(tmp_path, "example.py", "first = 3\r\n", fingerprint(text))
    assert path.read_bytes() == b"first = 3\r\n"
    assert legacy_temp.read_bytes() == b"unrelated existing file"
    assert not list(tmp_path.glob(".immortility-*.tmp"))


def test_hard_link_cannot_read_or_modify_another_file(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("protected\n")
    root = tmp_path / "workspace"
    root.mkdir()
    os.link(outside, root / "alias.py")
    with pytest.raises(BrokerError, match="tool_denied"):
        read_source(root, "alias.py")
    assert outside.read_text() == "protected\n"


def test_forget_is_persistent_and_applies_to_every_automatic_recall(tmp_path):
    path = tmp_path / "db"
    store = Store(path)
    session = store.session()["id"]
    task, _ = store.create(
        TaskRequest(
            session_id=session, request_id="fact", content="citrus project", cloud_consent=True
        )
    )
    task_id = task["task_id"]
    for state in ("queued", "running", "verifying"):
        store.state(task_id, state)
    store.state(task_id, "succeeded", result={"text": "citrus preference"})
    store.remember(session, task_id, "citrus preference")
    assert store.forget(session, task_id) == 1
    store.remember(session, task_id, "citrus late write")
    store.db.close()
    store = Store(path)
    try:
        assert store.recall(session, "citrus") == []
        assert store.history(session) == []
        assert prior_task_notes(store.tasks(session), "citrus", "next") == ""
        assert store.get(task_id)["result"]["text"] == "citrus preference"
        assert store.get(task_id)["recall_excluded"]
        other = store.session()["id"]
        with pytest.raises(BrokerError, match="not_found"):
            store.forget(other, task_id)
    finally:
        store.db.close()


def test_database_upgrade_makes_consistent_backup_and_blocks_downgrade(tmp_path):
    import sqlite3

    path = tmp_path / "db"
    store = Store(path)
    session = store.session()["id"]
    store.db.execute("PRAGMA user_version=1")
    store.db.close()
    store = Store(path)
    try:
        assert store.db.execute("PRAGMA user_version").fetchone()[0] == 4
        copies = list(tmp_path.glob("db.pre-m0-*.sqlite"))
        assert len(copies) == 1
        with sqlite3.connect(copies[0]) as backup:
            assert backup.execute("PRAGMA user_version").fetchone()[0] == 1
            assert backup.execute("SELECT id FROM sessions").fetchone()[0] == session
    finally:
        store.db.close()
    store = Store(path)
    store.db.close()
    assert len(list(tmp_path.glob("db.pre-m0-*.sqlite"))) == 1


def test_approval_hash_does_not_confuse_missing_and_empty_files(tmp_path):
    path = tmp_path / "new.py"
    path.write_bytes(b"")
    with pytest.raises(BrokerError, match="stale_workspace"):
        apply_proposed(tmp_path, "new.py", "new = 1", fingerprint(""), expected_exists=False)
    assert path.read_bytes() == b""
