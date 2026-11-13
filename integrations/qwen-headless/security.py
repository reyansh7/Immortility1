"""Candidate-only artifact/argument checks. This is NOT an OS sandbox or authorization grant."""

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

REVISION = "5d83992436eae1d760afd27aff78a71d676296fc"
MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path) -> None:
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("model_reparse_point_forbidden")


def verify_snapshot(value: str | Path) -> Path:
    text = str(value)
    path = Path(value)
    if not path.is_absolute() or text.startswith(("\\\\", "//")) or "://" in text:
        raise ValueError("only_absolute_local_snapshot_allowed")
    _regular(path)
    root = path.resolve(strict=True)
    if root.name != REVISION or not root.is_dir():
        raise ValueError("unreviewed_model_revision")
    manifest = json.loads(Path(__file__).with_name("artifacts.json").read_text(encoding="utf-8"))
    if manifest["model_id"] != MODEL or manifest["revision"] != REVISION:
        raise ValueError("invalid_trusted_manifest")
    expected = manifest["files"]
    # Check each directory before descending: rglob can otherwise enumerate a Windows junction.
    actual = set()
    pending = [root]
    allowed_dirs = {str(Path(name).parent).replace("\\", "/") for name in expected} - {"."}
    while pending:
        directory = pending.pop()
        _regular(directory)
        with os.scandir(directory) as entries:
            for entry in entries:
                resource = Path(entry.path)
                _regular(resource)
                relative = resource.relative_to(root).as_posix()
                if entry.is_dir(follow_symlinks=False):
                    if relative not in allowed_dirs:
                        raise ValueError("unreviewed_model_directory")
                    pending.append(resource)
                elif entry.is_file(follow_symlinks=False):
                    actual.add(relative)
                    if relative not in expected:
                        raise ValueError("unreviewed_model_artifact")
                else:
                    raise ValueError("non_regular_model_artifact")
    if actual != set(expected):
        raise ValueError("unreviewed_or_missing_model_artifact")
    for name, item in expected.items():
        resource = root / name
        _regular(resource)
        if resource.stat().st_size != item["bytes"] or sha256(resource) != item["sha256"]:
            raise ValueError("model_artifact_integrity_failed")
    types = {"config.json": "qwen3_tts", "speech_tokenizer/config.json": "qwen3_tts_tokenizer_12hz"}
    for name, model_type in types.items():
        config = json.loads((root / name).read_text(encoding="utf-8"))
        if config.get("model_type") != model_type:
            raise ValueError("unauthorized_model_architecture")
    return root


def local_options(value: str | Path, options: dict[str, Any], *, tokenizer: bool = False):
    path = Path(value)
    if tokenizer:
        if path.name != "speech_tokenizer":
            raise ValueError("unauthorized_tokenizer")
        root = verify_snapshot(path.parent) / "speech_tokenizer"
    else:
        root = verify_snapshot(path)
    required = {
        "local_files_only": True,
        "trust_remote_code": False,
        "use_safetensors": True,
        "weights_only": True,
        "attn_implementation": "sdpa",
    }
    # Device dispatch/offload would require Accelerate. It is deliberately absent.
    # A future broker-approved GPU stage must move the fully loaded CPU model explicitly.
    allowed = set(required) | {"revision", "dtype"}
    if set(options) - allowed:
        raise ValueError("unauthorized_model_loading_option")
    for key, wanted in required.items():
        if key in options and (type(options[key]) is not type(wanted) or options[key] != wanted):
            raise ValueError("unsafe_model_loading_option")
    if options.get("revision", REVISION) != REVISION:
        raise ValueError("unreviewed_model_revision")
    if "dtype" in options and str(options["dtype"]) != "torch.bfloat16":
        raise ValueError("unauthorized_model_dtype")
    result = {**options, **required}
    result.pop("revision", None)  # Absolute verified snapshot pins every nested loader too.
    return str(root), result
