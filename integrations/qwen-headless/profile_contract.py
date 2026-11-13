"""Read-only profile boundary for a future broker-authorized candidate execution."""

import json
from pathlib import Path

from ._immortility_security import MODEL, REVISION, _regular, sha256


def load_preserved_profile(
    profile: Path, metadata: Path, *, profile_sha256: str, metadata_sha256: str
):
    """Expected hashes must come from trusted broker state, never model/user tool arguments."""
    for path, expected, limit in (
        (profile, profile_sha256, 64 * 1024 * 1024),
        (metadata, metadata_sha256, 64 * 1024),
    ):
        _regular(path)
        if not path.is_file() or path.stat().st_size > limit or sha256(path) != expected:
            raise ValueError("untrusted_or_oversized_profile")
    meta = json.loads(metadata.read_text(encoding="utf-8"))
    if (
        meta.get("model_id") != MODEL
        or meta.get("model_revision") != REVISION
        or meta.get("format_version") != 1
        or meta.get("profile_sha256") != profile_sha256
        or meta.get("x_vector_only_mode") is not False
        or meta.get("icl_mode") is not True
    ):
        raise ValueError("unauthorized_profile_contract")
    import torch
    from .inference.qwen3_tts_model import VoiceClonePromptItem

    blob = torch.load(profile, map_location="cpu", weights_only=True)
    if type(blob) is not dict or set(blob) != {"ref_code", "ref_spk_embedding"}:
        raise ValueError("invalid_profile_tensor_dictionary")
    embedding, code = blob["ref_spk_embedding"], blob["ref_code"]
    if (
        type(embedding) is not torch.Tensor
        or embedding.layout != torch.strided
        or embedding.device.type != "cpu"
        or embedding.ndim != 1
        or not 1 <= embedding.numel() <= 8192
        or not embedding.is_floating_point()
        or not torch.isfinite(embedding).all()
    ):
        raise ValueError("invalid_profile_embedding")
    if code is not None and (
        type(code) is not torch.Tensor
        or code.layout != torch.strided
        or code.device.type != "cpu"
        or code.dtype != torch.int64
        or code.ndim != 2
        or code.numel() > 2_000_000
    ):
        raise ValueError("invalid_profile_reference_codes")
    transcript = meta.get("ref_text")
    if not isinstance(transcript, str) or not 1 <= len(transcript) <= 16_384:
        raise ValueError("invalid_profile_transcript")
    return [
        VoiceClonePromptItem(
            ref_code=code,
            ref_spk_embedding=embedding,
            x_vector_only_mode=False,
            icl_mode=True,
            ref_text=transcript,
        )
    ]
