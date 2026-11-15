"""Small CPU-only source/serialization contracts; never loads the pretrained voice model."""

import contextlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))


class Unsupported:
    pass


class Contracts(unittest.TestCase):
    def test_tensor_checkpoint_is_read_without_modifying_file(self):
        import torch
        from immortility_broker.reference_xtts import read_only_state
        from immortility_broker.reference_contracts import sha256

        with tempfile.TemporaryDirectory(dir=ROOT / ".cache/reference-tts") as work:
            path = Path(work) / "fixture.pth"
            torch.save({"model": {"weight": torch.arange(4)}, "config": {}}, path)
            before = sha256(path)
            state = read_only_state(path, contextlib.nullcontext())
            torch.testing.assert_close(state["weight"], torch.arange(4))
            self.assertEqual(sha256(path), before)

    def test_unapproved_pickle_class_is_rejected(self):
        import torch
        import pickle
        from immortility_broker.reference_xtts import read_only_state

        with tempfile.TemporaryDirectory(dir=ROOT / ".cache/reference-tts") as work:
            path = Path(work) / "unsupported.pth"
            torch.save({"model": {"weight": torch.arange(4)}, "config": Unsupported()}, path)
            with self.assertRaises(pickle.UnpicklingError):
                read_only_state(path, contextlib.nullcontext())

    def test_non_tensor_state_is_rejected(self):
        import torch
        from immortility_broker.reference_xtts import read_only_state

        with tempfile.TemporaryDirectory(dir=ROOT / ".cache/reference-tts") as work:
            path = Path(work) / "invalid.pth"
            torch.save({"model": {"weight": "not a tensor"}}, path)
            with self.assertRaises(ValueError):
                read_only_state(path, contextlib.nullcontext())


if __name__ == "__main__":
    unittest.main(verbosity=2)
