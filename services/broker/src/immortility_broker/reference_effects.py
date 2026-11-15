"""Approved mechanical voice coloration, shared by preview and runtime. Identity comes from XTTS."""

from typing import Any

from .infernal import Coloration, InfernalDSP


def mechanical(samples: Any, rate: int) -> Any:
    import numpy as np
    from pedalboard import HighpassFilter, PeakFilter, Pedalboard

    output = InfernalDSP(Coloration(-1.8, 0.95, 0.75, "clear_baritone")).process(samples, rate)
    phase = np.arange(len(output), dtype=np.float32) / rate
    carrier = (np.sin(2 * np.pi * 90 * phase) + 0.3 * np.sin(2 * np.pi * 133 * phase)) / 1.3
    output = 0.76 * output + 0.24 * output * carrier
    dry = output.copy()
    for milliseconds, gain in ((1.3, 0.12), (2.1, -0.07), (3.7, 0.06)):
        delay = round(rate * milliseconds / 1000)
        if len(output) > delay:
            output[delay:] += dry[:-delay] * gain
    output = Pedalboard(
        [
            HighpassFilter(cutoff_frequency_hz=65),
            PeakFilter(cutoff_frequency_hz=780, gain_db=3.0, q=5.5),
            PeakFilter(cutoff_frequency_hz=1400, gain_db=2.5, q=5),
            PeakFilter(cutoff_frequency_hz=2600, gain_db=1.0, q=3),
        ]
    )(output.reshape(1, -1), rate).reshape(-1)
    output *= 0.1 / max(1e-9, float(np.sqrt(np.mean(output * output))))
    output *= min(1.0, 0.9 / max(1e-9, float(np.max(np.abs(output)))))
    return output
