"""Admission for local GPU work. Cloud calls are not a fallback and are not counted here.

The RTX 4060 Laptop GPU on this machine reports 8188 MiB. One heavy job may run,
and only when free memory still covers Windows plus the visible dashboard.
"""

from __future__ import annotations

import subprocess

RESERVE_MIB = 1536
LIGHT_MIB = 700
HEAVY_MIB = 2800
MAX_HEAVY_JOBS = 1


def allow_light_gpu(free_mib: int | None) -> bool:
    """Speech-to-text may use CUDA only when the reserve and its own footprint fit."""
    return free_mib is not None and free_mib >= RESERVE_MIB + LIGHT_MIB


def allow_heavy_gpu(free_mib: int | None, heavy_running: int) -> tuple[bool, str]:
    if heavy_running >= MAX_HEAVY_JOBS:
        return False, "A heavy local GPU job is already running."
    if heavy_running < 0:
        return False, "Invalid GPU job count."
    if free_mib is None:
        return False, "Free GPU memory could not be measured, so the heavy job stays unloaded."
    if free_mib < RESERVE_MIB + HEAVY_MIB:
        return (
            False,
            "Free GPU memory is below the dashboard reserve plus one heavy model.",
        )
    return True, "One heavy local GPU job fits."


def free_vram_mib() -> int | None:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    line = completed.stdout.strip().splitlines()
    if not line:
        return None
    try:
        return int(float(line[0].split(",")[0].strip()))
    except ValueError:
        return None
