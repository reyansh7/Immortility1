"""CPU-only research contracts. Never load model weights, audio, CUDA or generate speech."""

import importlib.metadata as metadata
import json
import os
import pickle
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / ".cache/qwen-remediation-v2"
if not Path(sys.prefix).resolve().is_relative_to(RESEARCH.resolve()):
    raise SystemExit("Use only the separately materialized headless candidate interpreter")
sys.path.insert(0, str(ROOT / "services/tts/src"))
os.environ.update(
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
    HF_HUB_DISABLE_TELEMETRY="1",
    TOKENIZERS_PARALLELISM="false",
)
METRICS = {}


def forbidden(*_args, **_kwargs):
    raise AssertionError(
        "This research pass forbids network, model weights, CUDA and audio operations"
    )


class UntrustedProfile:
    """Harmless non-tensor object used to prove restricted deserialization rejects it."""


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        started = time.perf_counter()
        import torch

        cls.torch = torch
        cls.cuda_guard = patch.object(torch.cuda, "_lazy_init", forbidden)
        cls.cuda_guard.start()
        import qwen_tts
        from transformers import PreTrainedModel
        import qwen_tts._immortility_security as security

        cls.security = security
        cls.qwen = qwen_tts
        cls.model_guard = patch.object(PreTrainedModel, "from_pretrained", forbidden)
        cls.model_guard.start()
        METRICS["import_seconds"] = round(time.perf_counter() - started, 3)

    @classmethod
    def tearDownClass(cls):
        cls.model_guard.stop()
        cls.cuda_guard.stop()
        if cls.torch.cuda.is_initialized():
            raise AssertionError("CUDA was initialized")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qwen-headless-contract-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_01_isolated_distribution_and_real_dependencies(self):
        expected = {
            "immortility-qwen-tts-headless": "0.1.1.post1+immortility.2",
            "torch": "2.15.0",
            "transformers": "5.15.1",
            "setuptools": "84.2.1",
        }
        for name, version in expected.items():
            self.assertEqual(metadata.version(name), version)
            self.assertTrue(
                Path(metadata.distribution(name).locate_file(""))
                .resolve()
                .is_relative_to(Path(sys.prefix).resolve())
            )
        names = {d.metadata["Name"].lower() for d in metadata.distributions()}
        self.assertFalse(
            names
            & {
                "qwen-tts",
                "qwen-tts-hf",
                "gradio",
                "pillow",
                "sox",
                "onnxruntime",
                "torchaudio",
                "accelerate",
            }
        )
        METRICS["torch_cuda_build"] = self.torch.version.cuda

    def test_02_real_existing_model_artifacts_match_upstream(self):
        start = time.perf_counter()
        root = (
            Path.home()
            / "AppData/Local/Immortility/voice/hf-cache/hub/models--Qwen--Qwen3-TTS-12Hz-0.6B-Base/snapshots"
            / self.security.REVISION
        )
        self.assertEqual(self.security.verify_snapshot(root), root.resolve())
        METRICS["artifact_verification_seconds"] = round(time.perf_counter() - start, 3)
        METRICS["verified_artifacts"] = 11

    def test_03_pinned_config_parses_without_loading_models(self):
        from qwen_tts.core.models.configuration_qwen3_tts import Qwen3TTSConfig
        from qwen_tts.core.tokenizer_12hz.configuration_qwen3_tts_tokenizer_v2 import (
            Qwen3TTSTokenizerV2Config,
        )

        public = RESEARCH / "public/model"
        model = Qwen3TTSConfig.from_dict(json.loads((public / "config.json").read_text()))
        codec = Qwen3TTSTokenizerV2Config.from_dict(
            json.loads((public / "speech_tokenizer/config.json").read_text())
        )
        self.assertEqual(model.model_type, "qwen3_tts")
        self.assertEqual(codec.model_type, "qwen3_tts_tokenizer_12hz")
        # Mimi legitimately normalized rope_theta into rope_parameters in this release.
        # Exercise its actual CPU-only frequency initializer, rather than assuming a field layout.
        from transformers.models.mimi.modeling_mimi import MimiRotaryEmbedding

        rotary = MimiRotaryEmbedding(codec.encoder_config)
        reference, scaling = MimiRotaryEmbedding.compute_default_rope_parameters(
            codec.encoder_config
        )
        self.torch.testing.assert_close(rotary.inv_freq, reference)
        self.assertEqual(rotary.attention_scaling, scaling)
        self.assertTrue(self.torch.isfinite(rotary.inv_freq).all())

    def test_03b_optional_accelerate_is_not_needed_for_default_cpu_dispatch(self):
        from transformers.integrations.accelerate import check_and_set_device_map
        from transformers.utils import is_accelerate_available

        self.assertFalse(is_accelerate_available())
        self.assertIsNone(check_and_set_device_map(None))
        with self.assertRaisesRegex(ValueError, "requires.*accelerate"):
            check_and_set_device_map("cuda:0")

    def test_04_real_text_tokenizer_roundtrip_is_local(self):
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            str(RESEARCH / "public/model"),
            local_files_only=True,
            trust_remote_code=False,
            fix_mistral_regex=True,
        )
        phrase = "Immortility contract test."
        self.assertEqual(tokenizer.decode(tokenizer.encode(phrase)), phrase)

    def test_05_rope_compatibility_buffers_are_restored(self):
        from qwen_tts._transformers_compat import restore_rope_buffers, _default_rope_parameters

        torch = self.torch

        class Rope(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.config = SimpleNamespace(
                    rope_theta=10000, hidden_size=8, num_attention_heads=2
                )
                self.register_buffer("inv_freq", torch.zeros(2), persistent=False)
                self.rope_init_fn = _default_rope_parameters

        model = Rope()
        restore_rope_buffers(model)
        torch.testing.assert_close(model.inv_freq, torch.tensor([1.0, 0.01]))
        self.assertIs(model.original_inv_freq, model.inv_freq)
        self.assertEqual(model.attention_scaling, 1.0)

    def test_06_mimi_compatibility_retains_full_context(self):
        from qwen_tts._transformers_compat import restore_mimi_full_attention

        class Mimi(self.torch.nn.Module):
            __module__ = "transformers.models.mimi.modeling_mimi"

            def __init__(self):
                super().__init__()
                self.config = SimpleNamespace(max_position_embeddings=8000, sliding_window=250)
                self.sliding_window = 250

        model = Mimi()
        restore_mimi_full_attention(model)
        self.assertEqual(model.config.sliding_window, 8000)
        self.assertEqual(model.sliding_window, 8000)

    def test_07_existing_private_profile_contract_survives(self):
        from qwen_tts._immortility_profile import load_preserved_profile

        folder = Path.home() / "AppData/Local/Immortility/voice"
        profile, meta = folder / "friend_voice.pt", folder / "friend_voice.json"
        hashes = json.loads((ROOT / "data/audits/voice-preservation.json").read_text())
        items = load_preserved_profile(
            profile,
            meta,
            profile_sha256=hashes[str(profile)]["sha256"],
            metadata_sha256=hashes[str(meta)]["sha256"],
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].ref_spk_embedding.device.type, "cpu")
        self.assertEqual(items[0].ref_code.device.type, "cpu")
        self.assertEqual(self.security.sha256(profile), hashes[str(profile)]["sha256"])
        self.assertEqual(self.security.sha256(meta), hashes[str(meta)]["sha256"])

    def test_08_remote_model_and_tokenizer_inputs_are_denied(self):
        for value in (
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "https://example.invalid/model",
            "../model",
            "\\\\server\\share",
        ):
            with self.subTest(value=value), self.assertRaises((ValueError, OSError)):
                self.qwen.Qwen3TTSModel.from_pretrained(value)
        with self.assertRaises(ValueError):
            self.qwen.Qwen3TTSTokenizer.from_pretrained("https://example.invalid/speech_tokenizer")

    def test_09_unsafe_loading_arguments_are_rejected(self):
        for options in (
            {"trust_remote_code": True},
            {"local_files_only": False},
            {"use_safetensors": False},
            {"weights_only": False},
            {"revision": "main"},
            {"attn_implementation": "attacker/repo"},
            {"config": {}},
            {"token": "not-a-real-token"},
            {"device_map": "cuda:1"},
        ):
            with (
                self.subTest(options=tuple(options)),
                patch.object(self.security, "verify_snapshot", return_value=self.folder),
            ):
                with self.assertRaises(ValueError):
                    self.security.local_options(self.folder, options)

    def test_10_model_and_processor_keep_same_verified_path_and_flags(self):
        import qwen_tts.inference.qwen3_tts_model as module

        fake = SimpleNamespace(device=self.torch.device("cpu"), generate_config={})
        with (
            patch.object(self.security, "verify_snapshot", return_value=self.folder),
            patch.object(module.AutoConfig, "register"),
            patch.object(module.AutoModel, "register"),
            patch.object(module.AutoProcessor, "register"),
            patch.object(module, "Qwen3TTSForConditionalGeneration", SimpleNamespace),
            patch.object(module.AutoModel, "from_pretrained", return_value=fake) as model,
            patch.object(
                module.AutoProcessor, "from_pretrained", return_value=object()
            ) as processor,
        ):
            self.qwen.Qwen3TTSModel.from_pretrained(str(self.folder))
        for call in (model.call_args, processor.call_args):
            self.assertEqual(call.args[0], str(self.folder))
            self.assertIs(call.kwargs["local_files_only"], True)
            self.assertIs(call.kwargs["trust_remote_code"], False)
        self.assertIs(model.call_args.kwargs["use_safetensors"], True)
        self.assertIs(model.call_args.kwargs["weights_only"], True)

    def test_11_remote_audio_branches_fail_before_any_decoder(self):
        model = object.__new__(self.qwen.Qwen3TTSModel)
        codec = self.qwen.Qwen3TTSTokenizer()
        with self.assertRaisesRegex(ValueError, "remote_audio_disabled"):
            model._load_audio_to_np("https://example.invalid/audio.wav")
        with self.assertRaisesRegex(ValueError, "remote_audio_disabled"):
            codec.load_audio("https://example.invalid/audio.wav", 24000)

    def fixture(self, blob):
        profile, meta = self.folder / "fixture.pt", self.folder / "fixture.json"
        self.torch.save(blob, profile)
        payload = {
            "format_version": 1,
            "model_id": self.security.MODEL,
            "model_revision": self.security.REVISION,
            "profile_sha256": self.security.sha256(profile),
            "x_vector_only_mode": False,
            "icl_mode": True,
            "ref_text": "Public tensor fixture.",
        }
        meta.write_text(json.dumps(payload))
        return (
            profile,
            meta,
            {
                "profile_sha256": self.security.sha256(profile),
                "metadata_sha256": self.security.sha256(meta),
            },
        )

    def test_12_non_tensor_pickle_is_rejected(self):
        from qwen_tts._immortility_profile import load_preserved_profile

        profile, meta, hashes = self.fixture(UntrustedProfile())
        with self.assertRaises(pickle.UnpicklingError):
            load_preserved_profile(profile, meta, **hashes)

    def test_13_metadata_tampering_is_rejected_before_deserialization(self):
        from qwen_tts._immortility_profile import load_preserved_profile

        profile, meta, hashes = self.fixture({})
        meta.write_text("{}")
        with (
            patch.object(self.torch, "load", side_effect=forbidden),
            self.assertRaisesRegex(ValueError, "untrusted"),
        ):
            load_preserved_profile(profile, meta, **hashes)

    def test_14_invalid_tensor_structure_is_rejected(self):
        from qwen_tts._immortility_profile import load_preserved_profile

        bad = {
            "ref_code": self.torch.zeros((2, 16), dtype=self.torch.int64),
            "ref_spk_embedding": self.torch.tensor([float("nan")]),
        }
        profile, meta, hashes = self.fixture(bad)
        with self.assertRaisesRegex(ValueError, "embedding"):
            load_preserved_profile(profile, meta, **hashes)

    def test_15_snapshot_tampering_and_unlisted_code_are_denied(self):
        root = self.folder / self.security.REVISION
        root.mkdir()
        expected = json.loads((ROOT / "integrations/qwen-headless/artifacts.json").read_text())
        # Missing artifacts must fail before model loading; no fake weight file is deserialized.
        with self.assertRaisesRegex(ValueError, "artifact"):
            self.security.verify_snapshot(root)
        for name in expected["files"]:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"corrupt public fixture")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.security.verify_snapshot(root)
        (root / "model.py").write_text("raise AssertionError('must never execute')")
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            self.security.verify_snapshot(root)

    def test_16_reparse_attribute_is_denied(self):
        with patch.object(
            Path, "lstat", return_value=SimpleNamespace(st_mode=0, st_file_attributes=0x400)
        ):
            with self.assertRaisesRegex(ValueError, "reparse"):
                self.security._regular(self.folder)

    @unittest.skipUnless(os.name == "nt", "Windows junction contract")
    def test_17_real_windows_junction_is_rejected_before_traversal(self):
        root = self.folder / self.security.REVISION
        root.mkdir()
        outside = self.folder / "outside"
        outside.mkdir()
        junction = root / "speech_tokenizer"

        def quote(p):
            return "'" + str(p).replace("'", "''") + "'"

        command = (
            "New-Item -ItemType Junction -Path "
            + quote(junction)
            + " -Target "
            + quote(outside)
            + " -ErrorAction Stop | Out-Null"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
            env={
                k: v
                for k, v in os.environ.items()
                if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
            },
        )
        if result.returncode:
            self.skipTest("Local junction creation unavailable; native gate remains open")
        try:
            self.assertTrue(junction.is_junction())
            with self.assertRaisesRegex(ValueError, "reparse"):
                self.security.verify_snapshot(root)
        finally:
            # Non-recursive removal of only this owned junction, never its target.
            assert junction.parent == root and root.parent == self.folder
            os.rmdir(junction)
        self.assertTrue(outside.is_dir())

    def test_18_nested_tokenizer_loaders_remain_local_and_restricted(self):
        import qwen_tts.inference.qwen3_tts_tokenizer as module

        fake = SimpleNamespace(
            device=self.torch.device("cpu"), config=SimpleNamespace(), modules=lambda: []
        )
        with (
            patch.object(self.security, "verify_snapshot", return_value=self.folder),
            patch.object(module.AutoConfig, "register"),
            patch.object(module.AutoModel, "register"),
            patch.object(
                module.AutoFeatureExtractor, "from_pretrained", return_value=object()
            ) as features,
            patch.object(module.AutoModel, "from_pretrained", return_value=fake) as model,
        ):
            self.qwen.Qwen3TTSTokenizer.from_pretrained(str(self.folder / "speech_tokenizer"))
        for call in (features.call_args, model.call_args):
            self.assertEqual(call.args[0], str(self.folder / "speech_tokenizer"))
            self.assertIs(call.kwargs["local_files_only"], True)
            self.assertIs(call.kwargs["trust_remote_code"], False)
        self.assertIs(model.call_args.kwargs["use_safetensors"], True)
        self.assertIs(model.call_args.kwargs["weights_only"], True)


if __name__ == "__main__":
    with (
        patch.object(socket.socket, "connect", forbidden),
        patch.object(socket.socket, "connect_ex", forbidden),
        patch.object(socket, "create_connection", forbidden),
    ):
        result = unittest.main(verbosity=2, exit=False).result
    METRICS.update(
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        no_model_weights_loaded=True,
        no_cuda_initialized=True,
        no_audio_decoded_or_generated=True,
    )
    (ROOT / "data/audits/qwen-headless-contracts.json").write_text(
        json.dumps(METRICS, indent=2) + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
