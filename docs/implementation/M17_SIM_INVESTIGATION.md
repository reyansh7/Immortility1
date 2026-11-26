# M1.7 SIM investigation (canary only, simulated inference)

Every number here comes from the isolated canary
`%LOCALAPPDATA%\Immortility\canary-0232-m15` and the local `simulated_model` fixture.
No provider was contacted, so none of this is live-model evidence. The production DB was
read only from a copy (`%TEMP%\imm17\prodcopy`, opened with `mode=ro`).

## 0. Where the SIM tasks live
- Production `state.sqlite3` (copy): **36 tasks, 0 SIM tasks**. The newest task was created 2026-11-16 22:11 IST.
- Canary DB: 96 tasks, 94 of them SIM.
- Window suite scenario 18 compared mtime and size before and after the run for production `state.sqlite3`, `-wal`, `broker.log`, `hermes-gateway.json` (absent) and the Hermes 0.21.1 dir. All were identical.
- No production rows were deleted or changed. Nothing needs cleanup in production. If SIM text showed up in a chat history, it came from a canary window.

## 1. Why SIM:steps was blocked earlier and succeeded later
The steps tasks were traced in the canary DB.

Blocked or failed runs:
- `120786bd` (14:11 IST): **blocked `missing_key`**. It was blocked before queueing, and no route notice was written. Inferred cause: simulated routing was not active for that broker start, so routing asked for a real provider key. This was a configuration issue, not a permission issue.
- `ae3d560c` and `33c4abb5`: **failed `runtime_error`**. Both tools ran and were verified, but the run was on the *fast* budget (call_limit 2). The fixture's third model turn, which writes the answer, was refused. The run ended with no final answer. The cause is inferred from the identical failure reproduced in benchmark run 2, where steps on the fast budget failed 10/10 and passed 10/10 on standard.
- `d7d29818` and `169c3393` (window-suite run 1, text "SIM:steps w17-03_multistep-…"): **blocked `tool_denied`, reason `no_tools_granted`**.
  - Desktop admission derived capabilities from the task text. Once the suite token was appended, nothing matched, so the task got only `chat.respond`.
  - The earlier canary script had passed explicit capabilities. That is why it succeeded.

Successful runs:
- `16a3b67d` and `57076331`: **succeeded**, with explicit capabilities `clock.now.v1` + `arithmetic.multiply.v1` and enough budget.

Fix (9da60ea): canary-only admission gives SIM:steps exactly `["clock.now.v1","arithmetic.multiply.v1"]`. It applies only when all of these hold: simulated inference on, local tools on, text request, and no explicit capabilities. Production admission is unchanged, and nothing is widened for real providers. The offline benchmark runs steps on the standard budget.

Verified:
- Window run 3, task `d1e5316c-9714-413e-9d5f-35f4154c6557`: both tools allowed and verified (receipts 7b2513a3…, 5a95653d…), succeeded.
- Benchmark: steps 10/10.

## 2. SIM:dup
- The fixture's `repeat=2` emits two **distinct** delta events with the same text: seq 8 and 9, with different event ids. The UI correctly shows both.
- Dedupe is keyed on event identity and sequence (Last-Event-ID / seq). Identical text is never collapsed.
- Tests:
  - Python `test_m17_lifecycle.py`: identical text kept twice; a replay of the same seq is dropped.
  - Vitest `state.test.ts`: "keeps identical text from distinct events".
- Window run 3, task `c0e310e1-ef03-43ce-b0aa-f85a89314f4f`: succeeded, and `window_text_matches_store: true`.
- Benchmark: duplicate 8/8.

## 3. SIM:approve
- Root cause: the fixture chose its script from the *first* SIM tag anywhere in the conversation history, not from the current task. In a session that had already run "SIM:steps", a later "SIM:approve" replayed the steps branch. It asked for `sim-clock` and then `sim-multiply` while only `clock.now.v1` was in scope. The broker correctly denied this with `capability_scope`, and the task ended `tool_denied` (canary task `f899560c`).
- Fix (342e75b): `scripted_pieces(messages, current)` takes the tag from the task's own input, and milestones start after the last user message. Each turn also writes a `fixture.turn` audit notice for diagnosis. **No permission rule was relaxed.**
- Verified in window run 3 (exe sha 958EEAA2…), all on run-scoped Hermes run ids:
  - **approve once**, `dd0e90d7-6ead-449e-ae64-d59341ccf597`: running → **awaiting_approval** → running → verifying → succeeded. clock.now.v1 started, completed ok, receipt cc7050b2…, run `run_3e89471b…`.
    - The suite marked this scenario failed only because the text check did not trim leading newlines ("\n\nSimulated approved clock."). The check now uses Trim(). The full regression rerun reports it.
  - **deny**, `4b00e2af-d203-4e86-9308-34427a724daa`: awaiting_approval → blocked `approval_denied`. The tool never started.
  - **expired**, `c8c0d78d-301f-4c44-b04d-9dcfa352a7e4`: awaiting_approval → blocked `approval_expired`, and a late click was not possible.
  - **prohibited tools stayed denied**: shell `5f138e63-1615-4b57-aca1-90c0b90634f4`, browser `90a7370d-7d21-4062-bcb3-8bfbe7dd8127`, computer `b5e063cc-0aea-498b-a362-d2ecd2b0c890` and unknown tool `382941fc-0971-440d-9ac3-dace6dec74d0` were all blocked `tool_denied` and never started. Bad arguments, `87180c7a-31e1-4ea9-8533-109834c6eec3`, were denied with `capability_arguments`.
- Offline benchmark (fd9ee49): approval_deny, approval_expired and approval_mismatch_then_replay passed. Mismatch and replay return 409, and the correct approval then succeeds. 0 prohibited tools started across 27 adversarial cases.
- A bug found here was fixed in fd9ee49. If a task was cancelled while POST /v1/runs was still in flight, the created run kept running and could use the *next* task's inference grant. The create call is now shielded, and the run it creates is stopped and confirmed. There is a test for this in `test_m17_lifecycle.py`.

## 4. First-token latency (simulated fixture)
**Before.** Desktop chat samples from the canary DB, measured from task creation, n=6. These were separate desktop launches, so each was a first turn:

| stage | p50 | p95 |
|---|---|---|
| state running | 6 ms | 24 ms |
| Hermes run started | 43 ms (n=3) | 65 ms |
| **first delta** | **3715 ms** | **4453 ms** |
| succeeded | 3857 ms | 4582 ms |

Per-stage breakdown of the first turn after a fresh gateway, from the `hermes_timing` and `model.route` notices:
- Hermes agent cold init: about 1.9 s.
- About 1.1 s of first-call setup inside Hermes before the request reaches the broker.
- Broker preflight: 21.9 ms cold, 1.7–2.4 ms warm. Now recorded as `preflight_ms`.
- Fixture stream to first delta: about 10–15 ms.

The broker was not the bottleneck.

**After.** Offline benchmark, fd9ee49, real Hermes 0.23.2 gateway, 2026-11-18 12:54 IST:

| measure | value |
|---|---|
| cold first turn (gateway already healthy) | first delta 3928.8 ms, preflight 9.9 ms, model route 3915.1 ms |
| warm chat first delta | p50 **167.9 ms**, p95 **185.8 ms** (n=14) |
| warm chat e2e | p50 275.3 ms, p95 306.0 ms |
| warm preflight | p50 1.9 ms, p95 2.4 ms |
| run started | p50 30.1 ms |
| all warm first deltas (chat + dup) | p50 164.0 ms, p95 185.8 ms (n=22) |
| all warm e2e | p50 338.7 ms, p95 467.6 ms (n=49) |
| gateway cold start | 7803.7 ms |
| broker start | 8271.7 ms |

Conclusion: the 3–4 s appears only on the **first turn after a gateway start**, and it is spent inside Hermes agent initialization. Warm turns reach the first token in about 0.17 s. The broker fixes in M1.7 were measurement (`preflight_ms`) and correctness, not speed. M1.7 changed nothing to speed up the cold first turn, because the Hermes runtime is off limits. A possible follow-up is a broker-issued warm-up turn after gateway readiness. It is not implemented.
