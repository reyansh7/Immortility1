import os
from uuid import uuid4

import pytest

from immortility_broker.secrets import CredentialError, CredentialManager, migrate_env


class MemoryVault(CredentialManager):
    def __init__(self, fail=False):
        self.value = None
        self.fail = fail

    def read(self):
        return self.value

    def write(self, value):
        if self.fail:
            raise CredentialError("Storage unavailable")
        self.value = value


def test_migration_preserves_other_settings_and_is_idempotent(tmp_path):
    path = tmp_path / ".env"
    path.write_text('# local\nexport OPENROUTER_API_KEY = "dummy-not-a-key"\nOTHER=value\n')
    vault = MemoryVault()
    migrate_env(path, vault)
    assert vault.read() == "dummy-not-a-key"
    assert path.read_text() == "# local\nOTHER=value\n"
    migrate_env(path, vault)
    assert not list(tmp_path.glob(".env-migrate-*"))


def test_migration_moves_gemini_and_groq_without_leaving_plaintext(tmp_path, monkeypatch):
    stored = {}

    class Capture(CredentialManager):
        def __init__(self, namespace="Immortility", provider="openrouter"):
            self.provider = provider

        def write(self, value):
            stored[self.provider] = value

        def read(self):
            return stored.get(self.provider)

    monkeypatch.setattr("immortility_broker.secrets.CredentialManager", Capture)
    path = tmp_path / ".env"
    path.write_text(
        "OPENROUTER_API_KEY=dummy-open\n"
        "GEMINI_API_KEY=dummy-gemini-value\n"
        "GROQ_API_KEY=dummy-groq-value\n"
        "KEEP=1\n"
    )
    vault = MemoryVault()
    migrate_env(path, vault)
    text = path.read_text()
    assert vault.read() == "dummy-open"
    assert stored["gemini"] == "dummy-gemini-value"
    assert stored["groq"] == "dummy-groq-value"
    assert "dummy-" not in text
    assert "KEEP=1\n" in text


def test_failed_storage_never_removes_source(tmp_path):
    path = tmp_path / ".env"
    original = "OPENROUTER_API_KEY=dummy-not-a-key\n"
    path.write_text(original)
    with pytest.raises(CredentialError):
        migrate_env(path, MemoryVault(fail=True))
    assert path.read_text() == original


@pytest.mark.skipif(os.name != "nt", reason="Windows Credential Manager integration")
def test_real_current_user_vault_dummy_roundtrip():
    # Unique test-only target; never reads or changes the user's actual provider key.
    vault = CredentialManager("Immortility-Test-" + str(uuid4()))
    try:
        assert vault.read() is None
        vault.write("dummy-credential-not-an-api-key")
        assert vault.read() == "dummy-credential-not-an-api-key"
    finally:
        vault.delete()
    assert vault.read() is None
