"""CPU-only candidate regressions. No model load, synthesis, playback or audio decoding."""

import importlib.metadata
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / ".cache/qwen-remediation/candidate"
if Path(sys.prefix).resolve() != CANDIDATE.resolve():
    raise SystemExit("Run only with the separate .cache/qwen-remediation/candidate interpreter")
sys.path.insert(0, str(ROOT / "services/tts/src"))
os.environ.update(
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    HF_HUB_DISABLE_TELEMETRY="1",
    HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
    TOKENIZERS_PARALLELISM="false",
    PYTHONDONTWRITEBYTECODE="1",
)


def denied(*_args, **_kwargs):
    raise AssertionError("Network is forbidden in candidate regressions")


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from qwen_tts.inference.qwen3_tts_model import VoiceClonePromptItem

        cls.torch = torch
        cls.prompt_type = VoiceClonePromptItem

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qwen-profile-contract-")
        self.folder = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def fixture(self):
        from immortility_tts.profile import write_profile

        profile = self.folder / "fixture.pt"
        meta = self.folder / "fixture.json"
        reference = self.folder / "opaque-fixture.bin"
        reference.write_bytes(b"not audio; tensor-serialization contract only")
        item = self.prompt_type(
            ref_code=self.torch.zeros((2, 16), dtype=self.torch.int64),
            ref_spk_embedding=self.torch.zeros(1024),
            x_vector_only_mode=False,
            icl_mode=True,
            ref_text="Synthetic tensor contract.",
        )
        write_profile(item, profile, meta, reference, item.ref_text, "0.1.1", {})
        return profile, meta

    def test_candidate_identity_and_pinned_versions(self):
        expected = {
            "setuptools": "81.0.0",
            "qwen-tts": "0.1.1",
            "transformers": "4.57.3",
            "accelerate": "1.12.0",
            "torch": "2.11.0+cu128",
            "torchaudio": "2.11.0+cu128",
        }
        for name, version in expected.items():
            self.assertEqual(importlib.metadata.version(name), version)
            distribution = importlib.metadata.distribution(name)
            self.assertTrue(Path(distribution.locate_file("")).resolve().is_relative_to(CANDIDATE))

    def test_tensor_profile_roundtrip_without_model(self):
        from immortility_tts.profile import load_profile

        profile, meta = self.fixture()
        items = load_profile(profile, meta)
        self.assertEqual(len(items), 1)
        self.assertEqual(tuple(items[0].ref_spk_embedding.shape), (1024,))
        self.assertEqual(items[0].ref_spk_embedding.device.type, "cpu")
        self.assertEqual(items[0].ref_code.device.type, "cpu")

    def test_checksum_rejected_before_tensor_deserialization(self):
        from immortility_tts.profile import load_profile

        profile, meta = self.fixture()
        profile.write_bytes(b"corrupt fixture")
        with patch.object(self.torch, "load", side_effect=AssertionError("must not deserialize")):
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_profile(profile, meta)

    def test_revision_mismatch_rejected(self):
        from immortility_tts.profile import load_profile

        profile, meta = self.fixture()
        payload = json.loads(meta.read_text(encoding="utf-8"))
        payload["model_revision"] = "unreviewed"
        meta.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "revision"):
            load_profile(profile, meta)

    def test_missing_embedding_rejected(self):
        from immortility_tts.profile import load_profile, sha256

        profile, meta = self.fixture()
        self.torch.save({"ref_code": self.torch.zeros(1)}, profile)
        payload = json.loads(meta.read_text(encoding="utf-8"))
        payload["profile_sha256"] = sha256(profile)
        meta.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "speaker embedding"):
            load_profile(profile, meta)

    def test_preserved_private_profile_loads_on_cpu(self):
        from immortility_tts.profile import load_profile, sha256

        folder = Path.home() / "AppData/Local/Immortility/voice"
        profile, meta = folder / "friend_voice.pt", folder / "friend_voice.json"
        before = sha256(profile), sha256(meta)
        items = load_profile(profile, meta)
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], self.prompt_type)
        self.assertEqual(items[0].ref_spk_embedding.device.type, "cpu")
        self.assertEqual(before, (sha256(profile), sha256(meta)))

    def test_no_gpu_model_or_network_was_initialized(self):
        from immortility_tts.worker import ENGINE

        self.assertFalse(self.torch.cuda.is_initialized())
        self.assertFalse(ENGINE)
        self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")


if __name__ == "__main__":
    # Block actual socket connects even if an imported package ignores HF's offline flag.
    with (
        patch.object(socket.socket, "connect", denied),
        patch.object(socket.socket, "connect_ex", denied),
        patch.object(socket, "create_connection", denied),
    ):
        unittest.main(verbosity=2)
