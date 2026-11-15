# Critical repairs and usable local background tasks

This is a continuation of the existing M0/M1 work. It does not mark the general autonomous agent roadmap complete. The current directive is [preserved here](CRITICAL_BUG_FIXES_DIRECTIVE_2026-11-14.md). The three referenced screenshots were absent from the supplied attachment folder; native screenshots of the actual running scratch instance were inspected instead.

## Scope and ownership

The small implementation sequence was: recover the dirty checkout and evidence; diagnose empty chat/identity; repair local voice; finish native attachment and readable chat; run independent offline, native and authorized live acceptance. Main risks were stale cross-session updates, duplicate inference, GPU failures after lazy model initialization, retained Windows descendants, privacy consent, and concurrent avatar work.

No reset, blanket staging, commit, dependency upgrade, model download, driver/PATH change, account connection, service installation or dashboard redesign occurred. The avatar/GPU editor's work was retained. HeadScene.tsx, rig.ts, rig.test.ts and gpu_budget.py were not edited by this increment. The user subsequently confirmed voice.py and voice_worker.py could be edited here. Shared files must be reviewed by hunk; neither the old baseline nor the new manifest authorizes restoring whole files over another editor's work.

## Verified changes

| Area | Actual change | Status and evidence |
| --- | --- | --- |
| Chat outcomes | Meaningful failure/blocked/rate-limit/disconnected/cancelled/empty-success body; persisted terminal state wins over replayed running events; final stored answer reconciles the transcript | **Verified** deterministic task and rendered-component tests. The private runtime's recent failed empty turn was `hermes_failed`; its exact original provider/runtime cause was not established. No private conversation text was copied into these reports. |
| Stream recovery | At most three read-only stream/GET attempts with sequence cursor and task/session isolation; final metadata fetched even when SSE fails; cancellation suppresses stale updates | **Verified** interruption, deduplication, foreign-scope and abort regressions. Never resubmits inference. |
| Submission | Synchronous in-flight guard, session-scoped acknowledgements/errors, preserve newly typed content, IME composition guard, visible unavailable reason | **Integrated**, type/lint checks pass. Native live rapid-submission corpus remains separate acceptance. |
| Identity and capability claims | Supported Hermes system overlay identifies Immortility, separates provider identity, and adds a bounded settings snapshot; all direct Hermes tools stay disabled | **Verified** actual real-Hermes outgoing request with fake provider, plus exactly two authorized real free-provider turns. No response replacement or hardcoded answer. |
| Provider failures | Malformed/error stream classified safely; late rejection from an old task cannot poison a newer grant; no raw upstream error body | **Verified** synthetic stream/error and cross-task regression tests. |
| Cost policy | Optional `MODEL_CALL_CAP` from 1 to 6 can lower each route's existing ceiling; durable ledger and request guard enforce it | **Verified** lower-ceiling regression. Defaults retain FAST 2 / STANDARD 4 / DEEP 6 calls and existing token caps. Live smoke used cap 1 and FAST 4,000. |
| Speech | CPU remains default; auto GPU failures during model loading or lazy segment iteration retry once on CPU int8; partial GPU output discarded | **Integrated**; CPU path **verified** with installed real models. GPU failure recovery is **mocked** deterministic acceptance, not a successful real GPU inference claim. |
| Multisentence WAV | Set channels/rate once, validate all later chunks before writing | **Verified** regression and real Piper-to-CPU-Whisper fixture. The initial actual failure occurred during WAV synthesis, before STT/microphone; it is not proof of the user's original microphone CUDA cause. |
| Voice diagnostics | Safe operation/stage/device/error category/timing/cleanup/exit metadata; stage-specific capture/STT/synthesis/playback errors; ordinary local inference offline; control-pipe setup shares timeout and guaranteed cleanup | **Verified** pipe failure/cancellation regressions. No raw audio, transcript, key or exception body in diagnostics. Physical microphone and speaker operation were not exercised. |
| Background boundary | Explicit local-only broker publication, current-user DPAPI, strict loopback/PID/creation/executable/root verification, native-private bearer; no token in React or publication stdout | **Verified** Python native DPAPI cases, Rust contracts, actual local broker/SDK smoke and dashboard attachment. Production still requires explicit separate startup. |
| UI lifetime | Attach/detach, close attached dashboard without killing runtime, reopen/reattach and retrieve real stored results; separate task Stop and explicit runtime shutdown | **Verified** synthetic native dashboard check and HTTP replay smoke. Native UI displayed two succeeded workflows, eight SDK steps each; no cloud. Backend smoke independently closed a client after real dispatch and replayed the remaining events. |
| Process ownership | Reap waits for the entire exact owned Windows Job to quiesce under the original total deadline, including launcher descendants | **Verified** real descendant file-handle release regression. Stop timing is in PROCESS_STOP_BENCHMARK.json; older 1.89 ms p95 does not describe this stronger cleanup. |
| Readability | Opaque chat/message surfaces, no whole-chat opacity entrance, local inspection/background controls in Settings, correct local-only status and unavailable controls hidden | **Verified** native compact/quick-chat/settings inspection and replayed result display, plus rendered-component regressions. Existing dashboard/3D design preserved. Full DPI/multimonitor matrix is pending. |

## Current verification

- Python: **263 passed, 63.65 seconds** after the final pipe-setup cleanup repair. One existing Starlette/AnyIO deprecation warning.
- Frontend: **55 passed, 3.06 seconds**; TypeScript, ESLint, Prettier and production build passed. Vite retained the existing large avatar chunk warning (928.42 kB uncompressed); it was not suppressed or used to justify changing concurrent avatar code.
- Rust: **6 passed**, fresh offline run; compile 60 seconds, test execution below reported 0.01-second precision. Repo-local toolchain is `.tools/cargo`, `.tools/rustup`; ordinary shell PATH lacks Cargo.
- Ruff lint/format: passed (74 Python files). Mypy: passed (41 source files). Blueprint and generated contracts: passed.
- Configured-provider-key scan: frontend source, production bundle, docs and config passed. No key values printed.
- Real pinned Hermes + local fake provider: succeeded, one request; actual system prompt identity and disabled-capability snapshot asserted.
- [Authorized live evidence](CHAT_IDENTITY_LIVE_SMOKE.json): two separate empty scratch sessions, exactly two public prompts and two provider calls; no existing history/notes/files/audio/screen sent. Both succeeded. Identity response identified Immortility and stated the routed underlying model was unverified. Capability response described conversation/text reasoning and separate user-controlled window reads without claiming direct tools.
- [Native positive observation consent](NATIVE_WINDOW_CONSENT_SMOKE.json) remains the human's prior accepted synthetic-window test, not an approval for other windows or ongoing observation.
- [Background smoke](BACKGROUND_ATTACHMENT_SMOKE.json) uses the real local broker, DPAPI and isolated official SDK. The native GUI additionally attached, dispatched, detached, closed and reopened; it showed the same stored synthetic results. UI helper initially timed out awaiting app approval; after user authorization it worked. Focus/geometry recovery was needed on reopening, and activation resolved it.

## Measured costs and limits

| Measurement | Result | Scope |
| --- | --- | --- |
| Live identity | 16.005 s; 677 prompt + 60 completion = 737 tokens | One real free-route turn, n=1 |
| Live capability answer | 7.620 s; 666 + 106 = 772 tokens | Separate real free-route turn, n=1 |
| Live total | 1,509 reported tokens, 2 calls | Zero-price catalog enforced before each dispatch; no fallback/retry |
| Synthetic speech | Piper render 4,621.7 ms; WAV 5.317 s; CPU STT 6,237.6 ms; WER 0.0625 | One local fixture; no capture/playback; installed models only |
| Background SDK workflow | First standalone smoke 29.468 s, 8 steps | Full cold process/broker/cleanup path, no cloud; not warm tool latency |
| Whole-job Stop | n=30; p50 1.519 ms; p95 1.851 ms; max 1.876 ms; max peak job commit 17,526,784 bytes | Includes 5 observed OS processes per ready synthetic tree and whole-job quiescence, not model interrupt latency or idle RSS |
| Idle CPU/RAM, combined VRAM, sustained load and battery | **Unmeasured** | No fabricated idle-resource or percentage-saving claim |

Earlier loaded MCP cold starts failed the existing 10-second capability deadline. Several unloaded runs and the full suites pass; the precise loaded failure stage remains unresolved. The deadline was not increased. External privileged MCP tools remain disabled. A future adapter should record safe per-stage timings and evaluate task-scoped SDK reuse against cold process isolation before choosing either. Do not claim broad MCP reliability from the arithmetic fixture.

The optional hold smoke included 300 seconds of deliberate waiting; its elapsed total is not a latency benchmark. A first Stop benchmark attempt assumed exactly two OS processes and failed before measurement: Windows venv launchers added descendants. The corrected benchmark counts the real job members rather than excluding them.

## Reproduce and review

Run from the repository root in PowerShell:

```powershell
& .venv/Scripts/python.exe -m pytest -q
pnpm check
pnpm test
pnpm build
. ./scripts/dev-env.ps1
cargo test --offline --manifest-path apps/desktop/src-tauri/Cargo.toml
& .venv/Scripts/python.exe scripts/check-secret-isolation.py
& .venv/Scripts/python.exe scripts/smoke-hermes.py --offline
& .venv/Scripts/python.exe scripts/verify-voice.py
& .venv/Scripts/python.exe scripts/benchmark-process-stop.py
& .venv/Scripts/python.exe scripts/smoke-background-attachment.py
```

`verify-voice.py` now writes its synthetic fixture to a temporary directory, preserving existing recordings. It never opens a microphone. Do not add `--play` without separate speaker-test authorization. `smoke-chat-identity.py --live-consent` requires a new deliberate live-test decision; the two authorized turns have already run, and this report is not permission for recurring cloud tests.

For explicit optional background startup, first quit the normal desktop that owns its data. Set PYTHONPATH to services/broker/src and start `.venv/Scripts/python.exe -m immortility_broker --headless --local-workflows --standard-mcp --publish-attachment --data-dir <the selected runtime data directory>`. Then open the desktop and use **Settings → Attach local background**. Production default data is `%LOCALAPPDATA%/Immortility`; debug acceptance used a dedicated `.cache` root. Do not start a second owner on an active database. Nothing starts automatically, and attached brokers currently accept local read-only workflows only.

New evidence and owned source hashes are in CRITICAL_REPAIRS_VERIFICATION.json. OBSERVATION_BASELINE.json and `.cache/engineering-observation/before/` retain the earlier dirty snapshot; M0 reports remain historical. Review selected hunks before any rollback. Current-user DPAPI files are ephemeral credentials, not portable backups.

## Remaining ordered work

1. **Manual acceptance:** ordinary desktop chat after restart, rapid/multiline/consecutive sends, provider failure rendering, physical microphone capture and speaker Stop. No blanket microphone authorization was inferred from permission to fix voice code. Run exact DPI 100/125/150%, small/tall windows and multiple monitors. Native observation across real applications/secure desktop remains gated.
2. **MCP reliability:** safe stage timings under controlled CPU/disk contention, cancel during cold import/initialize/close, repeated attach/restart/expiry. Retain default-off external tools and original deadlines.
3. **Next eligible product slice:** local selected-window explanation with freshness checks, safe pointer overlay and voice cancellation synchronization. Requires its own acceptance corpus; current native read does not enable screenshots, physical input or unattended computer control.
4. **Later authorized milestones:** scoped supervised Windows actions, broader public research/browser, isolated coding, editable artifact engine, advanced memory/specialists/scheduling/connectors. These are planned, not installed or verified here; preserve Hermes and broker ownership.

Shared Hermes/speech advisory remediation remains open (previous installed audit: 103 advisory entries across 15 Hermes packages). No in-place upgrade was attempted. Qwen and arbitrary code execution remain hard-disabled. This checkpoint is bounded evidence, not a production-wide security certification.
