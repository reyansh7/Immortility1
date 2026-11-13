"""Current-user Windows Credential Manager. No secret-returning HTTP/IPC surface."""

import ctypes
import os
import tempfile
from ctypes import wintypes
from pathlib import Path
from typing import Any


class CredentialError(RuntimeError):
    pass


class Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


_TARGETS = {
    "openrouter": "OpenRouter",
    "gemini": "Gemini",
    "groq": "Groq",
}


class CredentialManager:
    def __init__(self, namespace: str = "Immortility", provider: str = "openrouter"):
        if provider not in _TARGETS:
            raise CredentialError("Unknown credential provider.")
        self.provider = provider
        self.target = namespace + "/" + _TARGETS[provider]

    def api(self) -> Any:
        if os.name != "nt":
            raise CredentialError("Windows Credential Manager is unavailable on this OS.")
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
        api.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(Credential)),
        ]
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        return api

    def read(self) -> str | None:
        api = self.api()
        pointer = ctypes.POINTER(Credential)()
        if not api.CredReadW(self.target, 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == 1168:
                return None
            raise CredentialError("Cannot access the current user's credential store.")
        try:
            try:
                return ctypes.string_at(
                    pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize
                ).decode("utf-8")
            except UnicodeDecodeError:
                raise CredentialError("The stored credential has an invalid encoding.") from None
        finally:
            api.CredFree(pointer)

    def write(self, value: str) -> None:
        if not value or "\n" in value or "\r" in value or len(value.encode()) > 2500:
            raise CredentialError("Invalid credential length.")
        blob = (ctypes.c_ubyte * len(value.encode())).from_buffer_copy(value.encode())
        credential = Credential(
            Type=1,
            TargetName=self.target,
            UserName="Immortility",
            CredentialBlobSize=len(blob),
            CredentialBlob=blob,
            Persist=2,
        )
        if not self.api().CredWriteW(ctypes.byref(credential), 0):
            raise CredentialError("Credential storage failed; the existing .env is unchanged.")
        if self.read() != value:
            raise CredentialError("Credential verification failed; the existing .env is unchanged.")

    def delete(self) -> None:
        if not self.api().CredDeleteW(self.target, 1, 0) and ctypes.get_last_error() != 1168:
            raise CredentialError("Credential removal failed.")


def _assignment_name(line: str) -> str:
    return line.strip().removeprefix("export ").split("=", 1)[0].strip()


def remove_env_assignments(path: Path, names: set[str]) -> None:
    if not path.is_file() or not names:
        return
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    content = "".join(line for line in lines if _assignment_name(line) not in names)
    if content == "".join(lines):
        return
    handle, temporary = tempfile.mkstemp(prefix=".env-migrate-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def migrate_env(path: Path, vault: CredentialManager) -> None:
    from dotenv import dotenv_values

    values = dotenv_values(path, interpolate=False)
    names: list[str] = []
    openrouter = values.get("OPENROUTER_API_KEY")
    extras = {
        "gemini": ("GEMINI_API_KEY", values.get("GEMINI_API_KEY")),
        "groq": ("GROQ_API_KEY", values.get("GROQ_API_KEY")),
    }
    if not openrouter and not vault.read() and not any(secret for _, secret in extras.values()):
        raise CredentialError("No OpenRouter credential is configured.")
    if openrouter:
        vault.write(openrouter)  # Read-back verification occurs before touching the source.
        names.append("OPENROUTER_API_KEY")
    for provider, (env_name, secret) in extras.items():
        if not secret:
            continue
        CredentialManager(provider=provider).write(secret)
        names.append(env_name)
    remove_env_assignments(path, set(names))
