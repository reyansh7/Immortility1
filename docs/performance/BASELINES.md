# Measured baselines — 2026-11-13

These are observed values, not performance promises. The native app was compact,
idle and made no capture or inference requests. Other development applications
were running. CPU percentages are normalized across logical processors; GPU
engine sum is not a percentage of the entire GPU's capacity.

## Completed owned native idle run

Script: `scripts/benchmark-desktop.py` → `scripts/benchmark-idle.ps1`.
Requested interval: 600 seconds, warmup 30 seconds; observed elapsed 634.68 seconds,
70 samples. Report `Completed=true`; no owned processes remained after termination.

| Metric | Observed |
|---|---:|
| UI CPU average | 0.0368% |
| Whole owned tree CPU average | 0.0368% |
| UI working set average | 284.93 MB |
| UI working set maximum | 392.84 MB |
| UI private memory average | 197.20 MB |
| Broker Python group working set average | 45.44 MB |
| Whole owned tree working set average | 330.38 MB |
| Matching GPU engine utilization sum, average | 0.941% |
| CreateProcess duration | 923 ms — **not** time to interactive |

The <2% idle CPU target was checked and met in this run. The <250 MB average UI
working-set target was checked and **not met**. No interactive startup, GPU VRAM
or active-task performance claim follows from these numbers.

The older run averaged 391.2 MB UI working set and had invalid all-zero CPU
evidence. The new runner fixes counter validity and process ownership. The working-
set change is **not a controlled optimization result**: OS paging, other workload
and process residency differ, and private memory was higher in this run. No
artificial working-set trimming was added.

Raw ignored report: `data/benchmarks/p0-current-idle.json`. The sampler now preserves
`Completed=false`/failure information and partial samples on an early exit instead
of silently leaving an old successful report to be misread as the new run.

## OpenMausBot narrow source-protocol probe

Three runs, Node 22.13.1, inspected/hash-pinned source only. Upstream declares
Node >=24; passing this limited probe does not establish supported application
compatibility or adoption readiness.

| Metric | Observed median |
|---|---:|
| Process start through MCP initialize response | 151.1 ms |
| tools/list response | 0.58 ms |
| MCP process working set | 54.8 MB |

All three processes exited on stdin closure. `fetch` was disabled; zero HTTP,
provider, account or team-dispatch calls occurred. The probe also rejected an
unknown method. It measures neither the full Electron application nor Windows
CUA/browser behavior. Three samples are insufficient for useful p95 claims.
Raw report: ignored `data/audits/openmausbot-protocol.json`.

## Speech baseline retained

Historical synthetic Whisper/Piper runs from `P1_P2_VALIDATION.md`: 5.1–5.3 seconds
of English audio, 2.02–5.17 seconds CPU STT including worker/model startup, 6.25%
word error rate, 4.83–9.16 seconds cold Piper first-audio readiness, 213–285 ms
speaking-worker Stop/reap. The 2.5-second STT target was not consistently met.

Historical Qwen report: 23.5 seconds synthesis for an 11-word/6.6-second greeting,
2.74 GB synthesis peak VRAM and 2.18 GB retained while loaded. No claim of real-time
speech, speaker likeness or new native Qwen performance is made. Its runtime is
now gated off by default pending security/native verification.

Next measurements: actual time to interactive, controlled compact memory profile,
warm/cold speech distributions with content-free timing, physical microphone
latency/noise/disconnect, bounded real-model cancellation and resource recovery.
No future scheduler/memory/controller is adopted on the basis of these baselines.
