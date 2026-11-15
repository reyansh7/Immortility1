"""Private local connection protection and identity; synthetic credentials only."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from immortility_broker.attachment import (
    ConnectionRecord,
    FILENAME,
    _dpapi,
    publish,
    read,
    unpublish,
)
from immortility_broker.app import create_app
from immortility_broker.config import ROOT, Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.store import Store
from test_workspace import AUTH, TOKEN

KEY = "synthetic-local-connection-" + "x" * 40


@pytest.mark.skipif(os.name != "nt", reason="Current-user Windows DPAPI")
def test_current_user_protected_record_roundtrip_and_tamper_denial(tmp_path):
    path, owned = publish(tmp_path, "http://127.0.0.1:12345", KEY, str(uuid4()))
    assert KEY.encode() not in path.read_bytes()
    record = read(tmp_path)
    assert record.token == KEY
    assert KEY not in repr(record)
    assert record.pid == os.getpid()
    corrupted = bytearray(owned)
    corrupted[-1] ^= 1
    path.write_bytes(corrupted)
    with pytest.raises(BrokerError, match="attachment_invalid"):
        read(tmp_path)
    unpublish(path, owned)
    assert path.exists()  # Never delete a changed/successor record.
    path.write_bytes(owned)
    unpublish(path, owned)
    assert not path.exists()


@pytest.mark.skipif(os.name != "nt", reason="Native process creation identity")
def test_changed_pid_creation_project_and_data_scope_are_denied(tmp_path):
    path, _ = publish(tmp_path, "http://127.0.0.1:12345", KEY, str(uuid4()))
    original = read(tmp_path)
    for change in [
        {"created": original.created + 1},
        {"project_root": str(tmp_path)},
        {"data_root": str(tmp_path / "foreign")},
        {"pid": 2**31},
    ]:
        path.write_bytes(_dpapi(original.model_copy(update=change).model_dump_json().encode()))
        with pytest.raises(BrokerError):
            read(tmp_path)


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:12345",
        "http://localhost:12345",
        "http://127.0.0.1:0",
        "http://127.0.0.1:123/a",
        "http://127.0.0.1:123?x=1",
        "http://127.0.0.1:123@evil.test",
        "http://127.0.0.1:00123",
        "http://[::1]:123",
    ],
)
def test_private_connection_endpoint_is_literal_loopback_only(url):
    with pytest.raises(ValidationError):
        ConnectionRecord(
            instance_id=str(uuid4()),
            url=url,
            token=KEY,
            pid=123,
            created=456,
            executable="C:/python.exe",
            project_root=str(ROOT),
            data_root=str(ROOT),
        )


def test_background_cleanup_runs_before_releasing_database_owner(tmp_path):
    checked = []

    def hook():
        with pytest.raises(BrokerError, match="broker_already_running"):
            Store(tmp_path / "state.sqlite3")
        checked.append(True)

    with TestClient(
        create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN, shutdown_hook=hook)
    ):
        pass
    assert checked == [True]
    store = Store(tmp_path / "state.sqlite3")
    store.db.close()


def test_shutdown_is_explicit_local_only_and_authenticated(tmp_path):
    stopped = []
    settings = Settings(_env_file=None, data_dir=tmp_path, local_only_mode=True)
    with TestClient(
        create_app(settings, TOKEN, stop_runtime=lambda: stopped.append(True))
    ) as client:
        assert client.post("/v1/runtime/shutdown", json={}).status_code == 401
        assert stopped == []
        assert client.post("/v1/runtime/shutdown", headers=AUTH, json={}).json() == {
            "shutdown_requested": True
        }
        assert stopped == [True]
        ready = client.get("/health/ready", headers=AUTH).json()
        assert ready["runtime_mode"] == "local-background"
        assert "token" not in ready
    with TestClient(create_app(Settings(_env_file=None, data_dir=tmp_path), TOKEN)) as client:
        assert client.post("/v1/runtime/shutdown", headers=AUTH, json={}).status_code == 403
    assert not (tmp_path / FILENAME).exists()
