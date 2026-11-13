"""Pinned public local models; inference never downloads or uploads audio."""

from pathlib import Path
from typing import Any

WHISPER_REPO = "Systran/faster-whisper-base"
WHISPER_REV = "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"
PIPER_REPO = "rhasspy/piper-voices"
PIPER_REV = "2f358b6a560e3a913ebf509b2f3344f20b367f94"
VOICES = {"ljspeech": "en_US-ljspeech-medium", "joe": "en_US-joe-medium"}


def voice_path(root: Path, voice: str) -> Path:
    return root / (VOICES[voice] + ".onnx")


def ready(root: Path) -> bool:
    return (
        (root / "whisper/model.bin").is_file()
        and (root / "whisper/vocabulary.txt").is_file()
        and all(
            voice_path(root, voice).is_file()
            and Path(str(voice_path(root, voice)) + ".json").is_file()
            for voice in VOICES
        )
    )


def prepare(root: Path) -> dict[str, Any]:
    from huggingface_hub import hf_hub_download, snapshot_download

    root.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        WHISPER_REPO,
        revision=WHISPER_REV,
        token=False,
        local_dir=root / "whisper",
        allow_patterns=["*.json", "*.txt", "model.bin"],
    )
    for voice in VOICES.values():
        name = voice.split("-")[1]
        prefix = f"en/en_US/{name}/medium/"
        for file in [voice + ".onnx", voice + ".onnx.json", "MODEL_CARD"]:
            path = Path(hf_hub_download(PIPER_REPO, prefix + file, revision=PIPER_REV, token=False))
            import shutil

            shutil.copyfile(
                path, root / (voice + "-MODEL_CARD.md" if file == "MODEL_CARD" else file)
            )
    return {"ready": ready(root), "stt_revision": WHISPER_REV, "tts_revision": PIPER_REV}
