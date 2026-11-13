"""Real CPU DSP contracts. Does not play audio or open any capture device."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))


class DSPTests(unittest.TestCase):
    def test_pitch_shift_matches_requested_frequency_without_speed_change(self):
        import numpy as np
        from immortility_broker.infernal import Coloration, InfernalDSP

        rate = 24000
        source = (0.2 * np.sin(2 * np.pi * 200 * np.arange(rate * 2) / rate)).astype(np.float32)
        output = InfernalDSP(Coloration(-2.4, 0, 0)).process(source, rate)
        self.assertEqual(len(output), len(source))
        middle = output[rate // 2 : rate * 3 // 2]
        spectrum = np.abs(np.fft.rfft(middle * np.hanning(len(middle))))
        dominant = np.fft.rfftfreq(len(middle), 1 / rate)[np.argmax(spectrum)]
        self.assertAlmostEqual(dominant, 200 * 2 ** (-2.4 / 12), delta=3)

    def test_silence_is_silent_and_output_is_bounded(self):
        import numpy as np
        from immortility_broker.infernal import Coloration, InfernalDSP

        dsp = InfernalDSP(Coloration())
        self.assertTrue(np.all(dsp.process(np.zeros(24000, dtype=np.float32), 24000) == 0))
        noisy = np.random.default_rng(4).normal(0, 2, 24000).astype(np.float32)
        output = dsp.process(noisy, 24000)
        self.assertTrue(np.isfinite(output).all())
        self.assertLessEqual(float(np.max(np.abs(output))), 0.92001)

    def test_invalid_samples_are_rejected(self):
        import numpy as np
        from immortility_broker.infernal import Coloration, InfernalDSP

        with self.assertRaises(ValueError):
            InfernalDSP(Coloration()).process(np.array([float("nan")]), 24000)

    def test_baritone_preserves_pitch_and_duration_without_pitch_shifter(self):
        import numpy as np
        from immortility_broker.infernal import Coloration, InfernalDSP

        rate = 24000
        source = (0.2 * np.sin(2 * np.pi * 160 * np.arange(rate) / rate)).astype(np.float32)
        for style in ("baritone", "clear_baritone"):
            with patch(
                "pedalboard.time_stretch", side_effect=AssertionError("unexpected pitch shift")
            ):
                output = InfernalDSP(Coloration(0, 0.3, 0.45, style)).process(source, rate)
            self.assertEqual(len(output), len(source))
            spectrum = np.abs(np.fft.rfft(output * np.hanning(len(output))))
            dominant = np.fft.rfftfreq(len(output), 1 / rate)[np.argmax(spectrum)]
            self.assertAlmostEqual(dominant, 160, delta=1)
            silence = InfernalDSP(Coloration(0, 0.3, 0.45, style)).process(
                np.zeros(rate, dtype=np.float32), rate
            )
            self.assertTrue(np.all(silence == 0))

    def test_boundary_trimming_retains_quiet_consonant_and_internal_pause(self):
        import numpy as np
        from immortility_broker.infernal_tts import conversational_edges

        rate = 24000
        consonant = np.random.default_rng(2).normal(0, 0.004, 2400).astype(np.float32)
        vowel = (0.2 * np.sin(2 * np.pi * 160 * np.arange(4800) / rate)).astype(np.float32)
        speech = np.concatenate([consonant, vowel, np.zeros(3600), vowel])
        padded = np.concatenate([np.zeros(12000), speech, np.zeros(16800)])
        output = conversational_edges(padded, rate)
        expected = np.concatenate([np.zeros(960), speech, np.zeros(1440)])
        np.testing.assert_array_equal(output, expected.astype(np.float32))


if __name__ == "__main__":
    unittest.main(verbosity=2)
