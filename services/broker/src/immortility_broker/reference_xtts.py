"""Reviewed read-only XTTS loader adapter; no upstream files or framework globals patched.

Upstream 0.28.0 Xtts._load_checkpoint rewrites legacy checkpoints after converting
the config object. We only need its tensor state, so preserve the pinned artifact.
"""

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any


def read_only_state(path: Path, legacy_scope: AbstractContextManager[Any]) -> dict[str, Any]:
    import torch

    with legacy_scope:
        checkpoint = torch.load(str(path), map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("model"), dict):
        raise ValueError("invalid_checkpoint_state")
    state = checkpoint["model"]
    if not state or not all(isinstance(value, torch.Tensor) for value in state.values()):
        raise ValueError("non_tensor_model_state")
    return dict(state)


def create_model(config: Any) -> Any:
    from TTS.tts.models.xtts import Xtts, _legacy_safe_globals

    class ReadOnlyXtts(Xtts):  # type: ignore[misc]
        def _load_checkpoint(self, model_path: Path) -> dict[str, Any]:
            return read_only_state(model_path, _legacy_safe_globals())

    return ReadOnlyXtts(config)
