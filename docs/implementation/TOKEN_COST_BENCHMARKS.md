# Current critical-repair evidence

The latest scoped measurements are in [CRITICAL_REPAIRS_CHECKPOINT.md](CRITICAL_REPAIRS_CHECKPOINT.md) and CRITICAL_REPAIRS_VERIFICATION.json. Exactly two authorized real free-route prompts used 1,509 reported tokens total (737 / 772), one provider call each, 16.005 / 7.620 seconds. No private history/files/audio/screen were sent; no paid fallback. This supersedes earlier statements below that no live test had occurred.

Whole-job Stop includes quiescence of all owned launcher descendants: n=30, p50 1.519 ms, p95 1.851 ms, max 1.876 ms; observed 5 OS processes per synthetic parent/child tree; maximum peak job commit 17,526,784 bytes. This is not model cancellation or idle RSS. The initial benchmark's exactly-two-process assertion was corrected to include real venv launchers.

Final real background workflow: 8 cold SDK steps, 23.787 seconds end to end, zero cloud calls/tokens. Prior standalone 29.468 seconds and optional 300-second hold remain checkpoint history. Existing 10-second capability deadlines are unchanged; loaded cold-start failures remain open. Installed Piper/CPU Whisper fixture: 5.317-second audio, 4,621.7 ms render, 6,237.6 ms recognition, WER 0.0625. No capture/playback. Combined idle CPU/RAM/VRAM and general token savings remain unmeasured.

# Earlier resource and token evidence

Measured on this Windows 11 / Python 3.13.11 checkout. RTX 4060 Laptop reports 8,188 MiB VRAM. These tests do not establish performance on Windows 10 or with loaded speech/GPU models.

| Operation | Observed result | Scope |
|---|---|---|
| Worker-ready Stop | n=100; p50 1.63 ms, p95 2.17 ms before the later suspended-start refinement | Real scratch Python workers. Separate descendant test inspects Windows exit state. Not microphone/GPU/audio-buffer latency; rerun after lifecycle changes. |
| Standard MCP 2.2.0 warm arithmetic | n=100, 100 correct; p50 0.93 ms, p95 1.29 ms | One established local stdio session; no model. [Raw record](MCP_BENCHMARK.json). |
| SDK initialize + list | 821.53 ms, n=1 | Excludes outer worker launch; not a p95. |
| Cold broker MCP calculation | 1,953.92 / 1,919.81 / 1,906.48 ms, n=3 | Includes process launch and teardown; experimental initialization failures are separately recorded, not excluded from reliability claims. |
| Isolated MCP disk | 47,599,170 bytes observed after install | 29 pinned packages; no models; subsequent caches can change disk use. |
| Local arithmetic cloud cost | 0 model calls, 0 cloud tokens, $0 inference for tested arithmetic | Broker test asserts Hermes factory is never called. Does not imply zero installation bandwidth or disk. |
| Real Hermes smoke | One normal fake-provider request succeeds; adversarial output blocked; Stop case sends no completion | Real pinned Hermes, offline fake HTTP provider. No live quality/TTFT/cost benchmark. |

RAM/VRAM/CPU measurements for the combined broker, SDK, UI and real speech pipelines are **unmeasured**. Disabled MCP launches no SDK process; this is code-path/test evidence, not an idle resource soak. Working-set estimates from the earlier [candidate matrix](../research/ECOSYSTEM_CANDIDATE_MATRIX_2026-11-14.md) remain planning estimates. No local LLM was downloaded or benchmarked.

## Enforced budgets

FAST: ≤4,000 reserved input+output tokens and ≤2 model calls. STANDARD: ≤8,000 / ≤4. Explicit DEEP: ≤16,000 / ≤6. Ledger aggregation includes all attempts of the same task, including repeated review/retry calls through the guard. Unsent price-check failures refund tokens but retain a call record. Dispatch errors/Stop/missing reports remain conservatively charged, never silently zero.

Known prompt/completion usage is persisted; provider cache/reasoning details are retained without double-counting. A report exceeding its reservation is persisted and blocks later reservations. Known reports can refund unused tokens once. Current tests include concurrent reservation contention, restart, invalid usage, overrun, multiple attempts, foreign task isolation and stale grant preflight.

The free router can change tokenizer/model. The current input reservation uses a conservative UTF-8-byte envelope, not a measured exact tokenizer. This may refuse a task that a particular tokenizer could fit. Hermes' renderer-marked irrelevant runtime OS/shell block is removed only in this tool-free route; the initial real smoke exposed why default context had exceeded FAST. Identity, user content, source labels and safety instructions are retained. No other document is silently truncated to fit a cloud budget; context overflow is explicit.

Complete real child-attempt attribution, live final-usage reconciliation, equal-quality token saving comparisons, caching/routing evaluations and B12 corpus remain open. No paid fallback, live provider key test, private upload or purchase was used to obtain these numbers.

Reproduce: `.venv/Scripts/python.exe scripts/benchmark-standard-mcp.py`; `.venv/Scripts/python.exe -m pytest -q -s services/broker/tests/test_tts_lifecycle.py`.


Latest refresh: Stop n=100 p50 **1.40 ms**, p95 **1.89 ms** after suspended-start refinement. MCP 2.2.0 warm n=100 p50 **0.86 ms**, p95 **1.26 ms**, initialize/list **1,021.56 ms** (n=1), cold broker **2,769.34 / 2,290.98 / 5,032.03 ms** (n=3). RAM/VRAM remain unmeasured. These replace earlier timing samples for current comparisons; earlier failures and the paired cold-start probe remain in acceptance history.


Current local workflow smoke uses zero model calls/cloud tokens and completes in5.695 s including controlled crash/restart. Normal UIA scratch observation:540.52 ms (n=1),31,154,176 bytes whole-job peak commit under256 MiB ceiling; wide:669.94 ms (n=1),31,498,240 bytes. Observer disk21,172,764 bytes at inventory. Commit is not RSS; CPU/RSS/VRAM and real-app rates remain unmeasured. Full constraints: [observer status](WINDOWS_OBSERVATION_STATUS.md). No broad token/quality saving claim is inferred from these deterministic local tools.
