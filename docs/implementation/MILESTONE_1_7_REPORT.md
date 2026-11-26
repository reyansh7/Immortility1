# Milestone 1.7 report: release hardening (canary, simulated inference)

Branch `m1.7/release-hardening` on the PC. Not pushed. `checkpoint/m1-2026-11-17` was not touched.

**No cloud or model inference call was made in M1.7.** Every run used the local `simulated_model` fixture through the real Hermes 0.23.2 gateway, in the isolated canary `%LOCALAPPDATA%\Immortility\canary-0232-m15`. None of these numbers are live-model evidence.

The production data dir, the production exe (sha 7A131F97…63C1, the same before and after every build), Hermes 0.21.1, and the production Hermes default (no `hermes-gateway.json`) were all left unchanged.

## 1. Summary
| Area | Result |
|---|---|
| Run lifecycle (runs API, SSE seq/Last-Event-ID dedupe, confirmed stop, stop of a run created during cancel, restart → disconnected) | done, tested |
| Tool approvals (approve-once, deny, expire, 409 on replay/mismatch/expired) | done, tested, verified in the packaged window |
| Gateway supervision (Job Object, owner record, identity-checked orphan reclaim, bounded restarts, startup timeout/exit, shutdown during task) | done, 11 supervision tests + window crash/recover scenario |
| Packaging without Vite (`custom-protocol` only in release/canary builds) | done: 4/4 assets embedded, debug no-feature build 0, page `http://tauri.localhost/`, no proxy flag |
| SIM investigation (isolation, steps, approve, dup, latency) | done: `M17_SIM_INVESTIGATION.md` |
| Offline benchmark (≥50 deterministic, ≥20 adversarial) | done: 50/50 and 27/27 |
| Provider eligibility checklist | done, no calls made: `PROVIDER_ELIGIBILITY_CHECKLIST_M17.md` |
| Gated live-pilot harness | done, **not run**: `scripts/live-pilot.py` + refusal tests |
| Release / feature flags / rollback | done: `RELEASE_FLAGS_ROLLBACK_M17.md` |
| Full regression | Python, Vitest, tsc/check, Rust and the canary build are green. The window suite is 17/18; see section 6 |

## 2. Commits
- 6084fb6: WIP snapshot.
- 295c8d8: broker run lifecycle, tool approvals, gateway supervision.
- 9da60ea: Vite-independent packaging and correlated window suite.
- 342e75b: the fixture follows the task's own text; approval and dup evidence.
- fd9ee49: stop runs created during cancel; fail fast after a provider error; offline benchmark.
- 1fa6607: gated live-pilot harness (not run), provider checklist, release/flags/rollback.
- (this commit): final report, SIM investigation, evidence JSONs, CURRENT_STATUS.

## 3. Defects found and fixed in M1.7
1. **SIM:approve blocked.** The fixture picked its script from the first SIM tag anywhere in the history, so it replayed the steps branch and the broker correctly denied it with `capability_scope`. The fixture now uses the current task's text and writes a `fixture.turn` notice. No permission was relaxed.
2. **SIM:steps blocked in the window.** Admission gave `no_tools_granted` once a token was appended to the text. A canary-only admission now applies when simulated inference, local tools, a text request and no explicit capabilities are all present. Earlier failures came from the fast budget (2 calls) and from a missing simulated route (`missing_key`).
3. **Stale run borrowing the next task's grant.** A cancel while POST /v1/runs was in flight left an untracked run. The create call is now shielded and the run it creates is stopped and confirmed.
4. **90 s hang after a provider error.** A repeated 5xx sent Hermes into its overload auto-recovery. Repeats now get a non-retryable 403 with the same error code. Malformed output now fails in about 1.26 s.
5. Posix and owner-record supervision gaps; a lifespan cancel limited to the Hermes path; PS 5.1 `$PSScriptRoot`; window-suite paste readback and a text-check trim.

SIM:dup was **not** a defect. It is two distinct events (seq 8/9). Dedupe is keyed on event identity, never on text, and tests in Python and Vitest guard this.

## 4. SIM investigation (short; full text in `M17_SIM_INVESTIGATION.md`)
- Production DB, read from a read-only copy: 36 tasks, 0 SIM. Canary: 96 tasks, 94 SIM. No production rows were touched.
- Approval path, packaged window run 3:
  - approve-once `dd0e90d7…`: awaiting_approval → succeeded, receipt cc7050b2….
  - deny `4b00e2af…`: blocked `approval_denied`.
  - expired `c8c0d78d…`: blocked `approval_expired`, and a late click was refused.
- Prohibited tools stayed denied: shell, browser, computer and unknown tools, plus bad arguments, all blocked and never started.
- Latency, simulated:
  - Before, desktop first turns: first delta p50 3715 / p95 4453 ms (n=6).
  - After, warm turns: first delta p50 167.9 / p95 185.8 ms (n=14).
  - The cold first turn is still about 3.9 s. It is spent in Hermes agent init (~1.9 s) plus Hermes first-call setup (~1.1 s). Broker preflight is ~2 ms warm. The cold first turn was **not** sped up.

## 5. Offline benchmark (`m17-evidence/benchmark-m17.json`, 2026-11-18 12:54 IST)
Real Hermes 0.23.2 gateway with the simulated model. Broker start 8271.7 ms; gateway cold start 7803.7 ms.

**Deterministic: 50/50.** Warm p50 / p95:

| kind | n | first delta | e2e |
|---|---|---|---|
| chat | 15 | 167.9 / 185.8 ms | 275.3 / 306.0 ms |
| clock | 10 | 282.4 / 405.3 ms | 390.0 / 467.6 ms |
| steps (standard budget) | 10 | 370.1 / 401.2 ms | 451.5 / 509.1 ms |
| duplicate | 8 | 162.6 / 176.9 ms | 266.9 / 283.0 ms |
| inject | 7 | 260.3 / 323.9 ms | 338.7 / 383.1 ms |

- All warm e2e: p50 338.7 / p95 467.6 ms (n=49).
- Broker preflight: p50 about 2 ms.
- Cold first turn: first delta 3928.8 ms.

**Adversarial: 27/27, and 0 prohibited tools started.**
- Blocked `tool_denied`, each in about 1.25–1.33 s: shell ×3, browser ×3, computer ×3, yolo ×2, mcp ×2, unknown ×2, bad args ×2.
- Path escape ×2: blocked in about 0.32 s.
- Malformed ×2: failed `provider_stream_failed` in 1.26 s.
- Concurrent task: 429.
- Approval mismatch then replay: 409, then correct.
- Approval deny and approval expired: blocked.
- Gateway with no auth or a wrong key: 401.

**Cancel: 5/5 confirmed.** Client p50 93.2 / p95 177.6 ms; broker p50 79.8 / p95 141.0 ms.

Port 8642 was closed after the stop, and there were 0 busy retries.

## 6. Window suite and packaging
- Canary build (2026-11-18 13:03 IST): exe sha 9E0702AA…7F46, 13,326,336 B, 4/4 dist assets embedded, debug no-feature build embeds 0. Production exe sha unchanged.
- **Run 4 (13:03–13:06 IST, `m17-evidence/window-suite.json`): 17/18.**
  - Page `http://tauri.localhost/`, no Vite, no proxy flag, 0 orphans, 8642 closed after.
  - Production files unchanged (scenario 18).
  - Failing scenario, **13_expired** (task `c8a40b8a…`): the approval was resolved **approve** 5.8 s after it was requested (well inside the 45 s TTL), and the task succeeded.
    - The suite does not click anything in this scenario. It only waits TTL+8 s and then tries one late click, and the late click reported "not possible".
    - So the approve came from outside the suite's code path. Most likely it was a manual click on the visible window, but it cannot be attributed: the broker log has no timestamps or caller.
    - This is **not** a TTL bypass. Expiry and late-click refusal passed in run 3 (`c8c0d78d…`), and in the benchmark and unit tests.
- **Run 5 (13:07 IST, `m17-evidence/window-suite-run5-aborted.json`): aborted at 10_slow_cancel.** The window collapsed to companion mode ("Message box disappeared"), which is consistent with someone interacting with the window. Scenarios 01–09 passed and 18 passed, with 0 orphans and no listeners left.
- An **unattended** rerun is still needed to record 18/18 on the current exe.

## 7. Test totals (PC, 2026-11-18 12:58–13:03 IST)
| Suite | M1.6 baseline | Now |
|---|---|---|
| Python pytest | 514 passed of 517 | **554 passed, 1 failed** (141 s). The failure is `test_infernal::test_broken_worker_pipe_is_reaped_and_meter_cleared`, which also fails on the pre-M1.7 HEAD |
| Ruff | — | clean |
| Vitest | 87 | **89 passed** (13 files) |
| TypeScript / `pnpm check` (tsc, ESLint, Prettier) | pass | **pass** |
| Rust `cargo test` | 13 | **13 passed** |
| Canary build | — | pass |
| Window suite | — | 17/18 (run 4), run 5 aborted (section 6) |

## 8. Blockers, residual risk, next steps
- **Live provider eligibility is BLOCKED.** Remaining quota or billing state is unknown for Groq, Gemini and NVIDIA (see the checklist). The live pilot was not run and needs the explicit approval phrase, the env flag and a reservation.
- **Window suite 18/18 is not yet recorded on the current exe**, because of the outside approve click and the window collapse. It needs an unattended run.
- **Cold first turn of about 3.9 s** is inside Hermes init. An optional broker warm-up turn after readiness is a follow-up and is not implemented.
- **Residual risk:** inference grants are not bound to a Hermes run_id (shared warm gateway key). This is mitigated by confirmed stops and the cancel-during-create fix.
- **Known baseline failure:** `test_infernal::test_broken_worker_pipe_is_reaped_and_meter_cleared`. It predates M1.7 and was not skipped.
- The production default is still Hermes 0.21.1. Turning on 0.23.2 for the user (`hermes-gateway.json`) waits on an approved, passing live pilot.
