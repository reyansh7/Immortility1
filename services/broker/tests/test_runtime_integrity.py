import subprocess

import pytest

from immortility_broker import hermes
from immortility_broker.config import Settings


@pytest.fixture
def source(tmp_path, monkeypatch):
    (tmp_path / "venv/Scripts").mkdir(parents=True)
    (tmp_path / "venv/Scripts/python.exe").touch()
    (tmp_path / "tui_gateway").mkdir()
    (tmp_path / "tui_gateway/entry.py").touch()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="0.21.1"\n')
    (tmp_path / "toolsets.py").write_text("TOOLSETS = {'bot_room': []}\n")

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(tmp_path), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()

    git("init", "-q")
    git("add", "pyproject.toml", "toolsets.py", "tui_gateway/entry.py")
    git(
        "-c",
        "user.name=Runtime Test",
        "-c",
        "user.email=runtime@example.invalid",
        "commit",
        "-qm",
        "test fixture",
    )
    revision = git("rev-parse", "HEAD")
    monkeypatch.setattr(hermes, "REVIEWED_REVISION", revision)
    return tmp_path, Settings(_env_file=None, hermes_source=tmp_path, hermes_revision=revision)


def test_clean_reviewed_runtime_is_available(source):
    path, settings = source
    assert hermes.runtime_check(settings)["status"] == "available"


def test_same_commit_with_modified_tracked_source_is_rejected(source):
    path, settings = source
    (path / "tui_gateway/entry.py").write_text("raise RuntimeError('unreviewed change')")
    assert hermes.runtime_check(settings)["status"] == "incompatible"


def test_declared_version_and_reviewed_pin_must_agree(source):
    path, settings = source
    (path / "pyproject.toml").write_text('[project]\nversion="99.0.0"\n')
    assert hermes.runtime_check(settings)["status"] == "incompatible"


def test_unknown_pin_is_rejected(source):
    _, settings = source
    settings.hermes_revision = "12345678"
    assert hermes.runtime_check(settings)["status"] == "incompatible"
