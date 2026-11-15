from immortility_broker.gpu_budget import (
    HEAVY_MIB,
    RESERVE_MIB,
    allow_heavy_gpu,
    allow_light_gpu,
)


def test_light_speech_stays_on_cpu_until_the_display_reserve_fits():
    assert allow_light_gpu(None) is False
    assert allow_light_gpu(RESERVE_MIB) is False
    assert allow_light_gpu(RESERVE_MIB + 700) is True


def test_only_one_heavy_job_runs_and_cloud_is_not_a_fallback():
    denied, reason = allow_heavy_gpu(RESERVE_MIB + HEAVY_MIB, 1)
    assert denied is False
    assert "already running" in reason
    unknown, message = allow_heavy_gpu(None, 0)
    assert unknown is False
    assert "could not be measured" in message
    allowed, _ = allow_heavy_gpu(RESERVE_MIB + HEAVY_MIB, 0)
    assert allowed is True
