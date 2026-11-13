"""Original, restrained robotic coloration. Only used by the opt-in INFERNAL voice."""

import math
from dataclasses import dataclass
from typing import Any

PRESETS: dict[str, dict[str, float | str]] = {
    "natural": {
        "voice_preset": "natural",
        "pitch_semitones": 0.0,
        "robotic_intensity": 0.0,
        "effects_strength": 0.0,
        "speed": 1.0,
        "resonance_style": "classic",
        "delivery": "steady",
    },
    "cinematic": {
        "voice_preset": "cinematic",
        "pitch_semitones": -1.4,
        "robotic_intensity": 0.18,
        "effects_strength": 0.35,
        "speed": 0.94,
        "resonance_style": "classic",
        "delivery": "steady",
    },
    "infernal": {
        "voice_preset": "infernal",
        "pitch_semitones": -2.4,
        "robotic_intensity": 0.45,
        "effects_strength": 0.6,
        "speed": 0.94,
        "resonance_style": "classic",
        "delivery": "steady",
    },
    "cinematic_v2": {
        "voice_preset": "cinematic_v2",
        "infernal_base": "kokoro_onyx",
        "pitch_semitones": 0.0,
        "robotic_intensity": 0.12,
        "effects_strength": 0.30,
        "speed": 0.97,
        "resonance_style": "baritone",
        "delivery": "deliberate",
    },
    "ultron_inspired": {
        "voice_preset": "ultron_inspired",
        "infernal_base": "kokoro_onyx",
        "pitch_semitones": 0.0,
        "robotic_intensity": 0.30,
        "effects_strength": 0.45,
        "speed": 0.96,
        "resonance_style": "baritone",
        "delivery": "deliberate",
    },
    "ultron_conversational": {
        "voice_preset": "ultron_conversational",
        "infernal_base": "kokoro_onyx",
        "pitch_semitones": 0.0,
        "robotic_intensity": 0.36,
        "effects_strength": 0.45,
        "speed": 1.0,
        "resonance_style": "clear_baritone",
        "delivery": "conversational",
    },
}


def delivery_plan(
    text: str, speed: float, deliberate: bool, conversational: bool = False
) -> list[tuple[str, float, float, float]]:
    """Same spoken words, bounded clause timing/gain; Kokoro has no emotion-tag API."""
    if not deliberate and not conversational:
        return [(text, speed, 0.0, 1.0)]
    from .speech_text import ready_sentences

    sentences, _ = ready_sentences(text, 0, True)
    rates = (0.96, 1.04, 1.0, 0.96)
    pauses = (0.20, 0.27, 0.18, 0.24)
    gains = (1.0, 0.98, 1.06, 1.03)
    if conversational:
        rates = (0.99, 1.015, 1.0, 0.985)
        # Keep Kokoro's residual natural cadence after edge trimming. Stacking
        # synthetic silence here produced 0.76-0.98 s gaps in the first audition.
        pauses = (0.0, 0.0, 0.0, 0.0)
        gains = (1.0, 0.99, 1.035, 1.02)
    return [
        (
            sentence,
            max(0.5, min(2.0, speed * rates[i % 4])),
            pauses[i % 4] if i < len(sentences) - 1 else 0.0,
            gains[i % 4],
        )
        for i, sentence in enumerate(sentences)
    ]


@dataclass(frozen=True)
class Coloration:
    pitch_semitones: float = -2.4
    robotic_intensity: float = 0.45
    effects_strength: float = 0.6
    resonance_style: str = "classic"

    def __post_init__(self) -> None:
        if self.resonance_style not in {"classic", "baritone", "clear_baritone"}:
            raise ValueError("unknown_resonance_style")
        for value, low, high in (
            (self.pitch_semitones, -6, 2),
            (self.robotic_intensity, 0, 1),
            (self.effects_strength, 0, 1),
        ):
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError("infernal_parameter_out_of_range")


class InfernalDSP:
    def __init__(self, settings: Coloration):
        from pedalboard import (
            Compressor,
            HighpassFilter,
            HighShelfFilter,
            PeakFilter,
            Pedalboard,
        )

        self.settings = settings
        strength = settings.effects_strength
        clear = settings.resonance_style == "clear_baritone"
        plugins = []
        if strength:
            plugins.extend(
                [
                    HighpassFilter(cutoff_frequency_hz=65),
                    PeakFilter(
                        cutoff_frequency_hz=145, gain_db=(0.8 if clear else 2.8) * strength, q=0.8
                    ),
                    PeakFilter(cutoff_frequency_hz=370, gain_db=-2.3 * strength, q=0.9),
                    PeakFilter(
                        cutoff_frequency_hz=2800 if clear else 2400,
                        gain_db=(3.0 if clear else 2.2) * strength,
                        q=0.7,
                    ),
                    HighShelfFilter(
                        cutoff_frequency_hz=6000 if clear else 7400,
                        gain_db=(1.2 if clear else -1.5) * strength,
                    ),
                    Compressor(
                        threshold_db=-20, ratio=1 + 1.8 * strength, attack_ms=12, release_ms=85
                    ),
                ]
            )
        self.board = Pedalboard(plugins)

    def process(self, samples: Any, sample_rate: int) -> Any:
        import numpy as np

        source = np.asarray(samples, dtype=np.float32).reshape(-1)
        if sample_rate not in range(8000, 96001) or len(source) > sample_rate * 120:
            raise ValueError("infernal_audio_bounds")
        if not np.isfinite(source).all():
            raise ValueError("nonfinite_audio")
        if not len(source):
            return source.copy()
        if abs(self.settings.pitch_semitones) > 0.01:
            from pedalboard import time_stretch

            source = time_stretch(
                source,
                sample_rate,
                stretch_factor=1.0,
                pitch_shift_in_semitones=self.settings.pitch_semitones,
                high_quality=True,
                preserve_formants=True,
            ).reshape(-1)
        out = self.board(source.reshape(1, -1), sample_rate, buffer_size=512, reset=True).reshape(
            -1
        )
        strength, robot = self.settings.effects_strength, self.settings.robotic_intensity
        clear = self.settings.resonance_style == "clear_baritone"
        if self.settings.resonance_style in {"baritone", "clear_baritone"}:
            # Natural performance dominates. Quiet, phase-varied doubling adds a body,
            # rather than low-frequency ring modulation that can resemble a demon filter.
            dry = out.copy()
            positions = np.arange(len(out), dtype=np.float32)
            if robot * strength:
                modulated_delay = sample_rate * (
                    (0.0045 if clear else 0.007)
                    + (0.00006 if clear else 0.00018)
                    * np.sin(2 * np.pi * 0.21 * positions / sample_rate)
                )
                doubled = np.interp(positions - modulated_delay, positions, dry, left=0, right=0)
                out = out + doubled * ((0.18 if clear else 0.12) * robot * strength)
                reflections = (
                    ((2.3, 0.14), (3.7, -0.085), (5.1, 0.055))
                    if clear
                    else ((3.1, 0.08), (5.3, -0.04))
                )
                for milliseconds, gain in reflections:
                    offset = round(sample_rate * milliseconds / 1000)
                    if len(out) > offset:
                        out[offset:] += dry[:-offset] * gain * robot * strength
            out = out * (1 - 0.06 * strength) + np.tanh(out * 1.5) / 1.5 * (0.06 * strength)
            for milliseconds, gain in () if clear else ((19, 0.018), (41, 0.009)):
                offset = round(sample_rate * milliseconds / 1000)
                if len(out) > offset:
                    out[offset:] += dry[:-offset] * gain * strength
            peak = float(np.max(np.abs(out)))
            if peak > 0.92:
                out *= 0.92 / peak
            return np.ascontiguousarray(out, dtype=np.float32)
        if strength:
            # Parallel saturation preserves the dry consonants; no bit crushing or vocoder.
            wet = 0.16 * strength
            out = (1 - wet) * out + wet * np.tanh(out * 1.8) / 1.8
            phase = np.arange(len(out), dtype=np.float32) / sample_rate
            metal = np.sin(2 * np.pi * 37 * phase) + 0.35 * np.sin(2 * np.pi * 61 * phase)
            out = out * (1 + 0.075 * robot * strength * metal)
            # Two very quiet early reflections, never a long reverb tail masking words.
            dry = out.copy()
            for milliseconds, gain in ((11, 0.035), (23, 0.018)):
                delay = round(sample_rate * milliseconds / 1000)
                if len(out) > delay:
                    out[delay:] += dry[:-delay] * gain * strength
        peak = float(np.max(np.abs(out)))
        if peak > 0.92:
            out *= 0.92 / peak
        return np.ascontiguousarray(out, dtype=np.float32)


def jaw_level(rms: float) -> float:
    """Content-free playback meter; silence is exactly zero."""
    return 0.0 if not math.isfinite(rms) else max(0.0, min(1.0, rms))
