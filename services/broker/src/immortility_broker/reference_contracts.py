"""Typed, broker-mediated reference voice contracts. No arbitrary models, tools or output paths."""

import hashlib
import json
import stat
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[4]


class ReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evaluation_authorized: Literal[True]
    run_id: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")
    case: Literal["normal", "question", "sarcasm", "quiet", "dramatic"] = "normal"
    operation: Literal["evaluate", "prepare", "speak"] = "evaluate"
    text: str = Field(default="", max_length=500)
    speed: float = Field(default=1.0, ge=0.5, le=2.0, allow_inf_nan=False)
    reference: Literal["conditioned", "speech-crop"] = "conditioned"
    model_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reference_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("evaluation_authorized", mode="before")
    @classmethod
    def explicit_authorization(cls, value: object) -> object:
        if value is not True:
            raise ValueError("explicit_evaluation_authorization_required")
        return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_junction(path: Path) -> bool:
    """Mount-point reparse check also works in the supported Python 3.11 broker."""
    try:
        return getattr(path.lstat(), "st_reparse_tag", 0) == getattr(
            stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003
        )
    except OSError:
        return False


def verified_file(root: Path, name: str, size: int, digest: str) -> Path:
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("unauthorized_asset_name")
    path = root / name
    if (
        root.is_symlink()
        or is_junction(root)
        or not path.is_file()
        or path.is_symlink()
        or path.resolve().parent != root.resolve()
        or path.stat().st_size != size
        or sha256(path) != digest
    ):
        raise ValueError("asset_integrity_failed")
    return path


def approved_paths(request: ReferenceRequest, *, loaded_model: bool = False) -> tuple[Path, Path]:
    manifest_path = ROOT / "config/reference-tts-models.json"
    reference_path = ROOT / "data/reference-tts/reference/reference.json"
    if sha256(manifest_path) != request.model_manifest_sha256:
        raise ValueError("model_manifest_substitution")
    if sha256(reference_path) != request.reference_manifest_sha256:
        raise ValueError("reference_manifest_substitution")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["model"] != "coqui/XTTS-v2":
        raise ValueError("unauthorized_model")
    root = Path.home() / "AppData/Local/Immortility/models/reference-tts" / manifest["revision"]
    if not loaded_model:
        for name, item in manifest["files"].items():
            verified_file(root, name, item["bytes"], item["sha256"])
    reference = json.loads(reference_path.read_text(encoding="utf-8"))["files"][request.reference]
    path = verified_file(
        reference_path.parent, reference["name"], reference["bytes"], reference["sha256"]
    )
    return root, path
