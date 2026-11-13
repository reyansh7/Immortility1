"""Private local paths for the cloned voice. Audio never leaves this machine."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
MODEL_REVISION = "5d83992436eae1d760afd27aff78a71d676296fc"
PROFILE_FORMAT = 1
REFERENCE_TRANSCRIPT = (
    "Hey, good morning! How are you doing today? I was just thinking about how quickly "
    "everything changes. Some days are exciting, and some are a little confusing. But that's "
    "okay. We can figure things out together, one step at a time."
)
# faster-whisper base, int8, on the 16 kb/s Opus source. The final clause disagrees.
# The operator-supplied transcript is kept; this disagreement is recorded, not hidden.
TRANSCRIPT_FLAG = (
    "Local faster-whisper base heard the final clause as 'once the better time' rather than "
    "'one step at a time'. The rest matches. The supplied transcript is used for cloning."
)
PREVIEW_PHRASE = "Hey! I'm Immortility. It's really nice to hear from you again."


def voice_root() -> Path:
    override = os.environ.get("IMMORTILITY_VOICE_DIR")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    return base / "Immortility" / "voice"


def source_recording() -> Path:
    override = os.environ.get("IMMORTILITY_VOICE_SOURCE")
    if override:
        return Path(override)
    return ROOT / "immortility's_voice" / "audio1.ogg"


def reference_wav() -> Path:
    return voice_root() / "reference.wav"


def profile_path() -> Path:
    return voice_root() / "friend_voice.pt"


def metadata_path() -> Path:
    return voice_root() / "friend_voice.json"


def consent_path() -> Path:
    return voice_root() / "consent.json"


def samples_dir() -> Path:
    return voice_root() / "samples"


def playback_dir() -> Path:
    return voice_root() / "playback"


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_source() -> Path:
    path = source_recording()
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(path.name)
    return path


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def consent_granted() -> bool:
    data = _read_json(consent_path())
    return bool(data and data.get("friend_authorized") is True)


def write_consent(authorized: bool) -> None:
    root = voice_root()
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "immortility.voice_consent.v1",
        "friend_authorized": authorized,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    consent_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def profile_metadata() -> dict[str, Any] | None:
    data = _read_json(metadata_path())
    if not data or data.get("format_version") != PROFILE_FORMAT:
        return None
    if data.get("model_id") != MODEL_ID or data.get("model_revision") != MODEL_REVISION:
        return None
    return data


def profile_ready() -> bool:
    meta = profile_metadata()
    path = profile_path()
    if meta is None or not path.is_file() or path.is_symlink():
        return False
    try:
        return fingerprint(path) == meta.get("profile_sha256")
    except OSError:
        return False


def settings_path(data_dir: Path) -> Path:
    return data_dir / "speech-settings.json"


def load_voice_settings(data_dir: Path) -> dict[str, Any] | None:
    return _read_json(settings_path(data_dir))


def save_voice_settings(data_dir: Path, payload: dict[str, Any]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    settings_path(data_dir).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def delete_clone() -> None:
    root = voice_root()
    if not root.exists():
        return
    for name in (
        "reference.wav",
        "transcript.txt",
        "friend_voice.pt",
        "friend_voice.json",
        "consent.json",
    ):
        file = root / name
        if file.is_file() and not file.is_symlink() and file.resolve().parent == root.resolve():
            file.unlink()
    for folder_name in ("samples", "playback"):
        folder = root / folder_name
        if (
            folder.is_dir()
            and not folder.is_symlink()
            and folder.resolve().parent == root.resolve()
        ):
            for child in folder.iterdir():
                if child.is_file() and not child.is_symlink():
                    child.unlink()
            folder.rmdir()
