# 06 — Performance, reliability and capacity targets

These are **engineering targets to benchmark**, not guarantees. Measure on a Windows laptop with RTX 4060 8 GB VRAM / 16 GB RAM, in idle/light and saturated conditions. Free cloud API latency and quotas are external variables.

## UX budgets
| Metric | Initial target | Measurement |
|---|---|---|
| Window interactive after launch | <= 3 s warm, <= 6 s cold | Windows boot-to-render benchmark |
| Idle compact orb CPU | < 2% average after settling | 10-min Windows PerfMon sample |
| Idle UI RAM | < 250 MB UI process group (target) | Task Manager / process profiler |
| Collapsed orb update | 5–15 FPS / event-driven | R3F/RAF profiler |
| Expanded 3D | 30 FPS typical, fallback when low | Real GPU frame measurement |
| Click-to-status response | < 150 ms local p95 | UI event timestamps |
| Text streaming | progress visible as soon as Hermes streams | SSE/WS trace |
| Local STT | Optimize for < 2.5 s endpoint-to-text | Measured on target mic/hardware |
| Mic disabled | zero active capture calls | negative integration test |
| Cancellation acknowledgement | < 250 ms UI; kill worker bounded | event + process test |
| User data on crash | no lost committed task/audit events | crash/restart test |

## GPU budget
- No 3D command center render when collapsed. Use a CSS/SVG orb as low-power fallback.
- Avoid keeping two heavyweight GPU models loaded simultaneously. GPU queue serializes ComfyUI / vision / local STT when competing for memory.
- Quantized local 4B models are optional; prefer cloud reasoning within validated free quotas.
- Free-system resources after each media job; cap process VRAM and provide cancellation.
- Background processes dormant when unavailable/unneeded; use on-demand workers with health checks.

## Resilience
- Bound retries with exponential backoff and provider `Retry-After`; no retry storms or loops between providers.
- Event persistence before side effects; idempotency token for action-replayable workflows.
- Supervisor health checks and auto-restart limits with circuit breaker.
- Do not repeat non-idempotent browser clicks or payment submissions automatically.
- Timeouts: distinct connect, first-token, overall job and tool-call budgets.
- UI remains usable offline; displays 'unavailable' accurately, no phantom task progress.
- Diagnostics bundle excludes content, secrets and user files unless explicitly exported.

## Release gates
Track target values against baselines. Any serious regression in idle CPU/GPU, memory, microphone privacy, cancellation or permission enforcement blocks promotion to the next phase.
