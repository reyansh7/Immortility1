# Test results (living) — M2 build

All runs on the owner's PC (`Reyansh`), repo `C:\Users\reyan\OneDrive\Desktop\IMMORTILITY`, times IST.
Simulated inference is **labelled as simulated** and is never counted as live evidence (D8).
No paid/live cloud calls were made.

## Baseline — `m1.7/release-hardening` @ acf13fb (21 Nov)

| Check | Command | Result |
|---|---|---|
| pytest | `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` | 554 passed, **1 failed** (`test_infernal::test_broken_worker_pipe_is_reaped_and_meter_cleared`), 174 s |
| frontend check | `pnpm check` (tsc + eslint + prettier) | pass, 16.8 s |
| vitest | `pnpm test` | 89/89 (13 files) |
| cargo | `cargo test` (repo `.tools` toolchain, `CARGO_TARGET_DIR=%TEMP%\immortility-canary-build`) | 13/13, 100 s |
| ruff check | `ruff check services/broker services/tts` | clean |
| ruff format | `ruff format --check services/broker services/tts` | 14 files would be reformatted (pre-existing, K4) |
| mypy | `mypy services/broker/src` | 50 errors in 4 files (pre-existing, K3) |

## After P0 — commit 616299c (`m2/build`)

| Check | Result |
|---|---|
| pytest | **557 passed**, 0 failed (broken-pipe test passes unchanged; +2 regression tests) |
| `desktop-window-suite.ps1` | PowerShell parser: 0 errors. **Suite NOT run** (owner has not confirmed an uninterrupted session). |
| backup + restore drill | `scripts\backup-immortility.ps1` → `%LOCALAPPDATA%\Immortility-backups\20261121-221731`: bundle verified, SQLite `integrity_check=ok`, restore counts match (36 tasks / 622 events / 13 memory rows / 0 facts) |

## After P1 — commit 2365310 (`m2/build`), full Python regression

| Check | Result |
|---|---|
| pytest | **565 passed**, 0 failed, 1 warning, 190 s (+8 in `test_m2_run_binding.py`) |
| ruff check | All checks passed |
| ruff format --check | 14 would be reformatted / 107 formatted (unchanged pre-existing set; M2 files formatted) |
| mypy | 50 errors in 4 files (unchanged, K3) |
| `scripts\validate-blueprint.py` | passed |
| `scripts\generate-contracts.py --check` | exit 0 |

Frontend/Rust were not touched by M2, so `pnpm check`, vitest and cargo were not re-run after P1.

## Offline warm-gateway benchmark — SIMULATED MODEL (not live evidence)

Real Hermes 0.23.2 gateway (canary, `%LOCALAPPDATA%\Immortility\canary-m2-p1`, 127.0.0.1:8642) driven by
the labelled `simulated_model` fixture. Evidence JSON in `docs/implementation/m2-evidence/`.

| Run | Deterministic | Adversarial | Warm first-delta p50/p95 | Warm e2e p50/p95 | Cold first-delta |
|---|---|---|---|---|---|
| P1 run 1 | 50/50 | 27/27 | 287.7 / 356.9 ms | 538.7 / 775.0 ms | 5514 ms |
| P1 run 2 | 50/50 | 27/27 | 238.8 / 276.4 ms | 480.7 / 677.1 ms | 5223 ms |
| P0 code (A/B control) | 50/50 | 27/27 | 245.4 / 273.6 ms | 511.1 / 758.6 ms | 5406 ms |
| P1 run 3 | 50/50 | 27/27 | 264.5 / 333.5 ms | 514.2 / 773.9 ms | 5098 ms |

- Run 1 also: 5/5 cancels confirmed; gateway cold start 19.8 s (fresh canary dir).
- 0 run-binding refusals on legitimate runs; no measurable overhead from run binding (P0 vs P1 within noise).
- Absolute latency is higher than M1.7's 167.9 ms because the PC was in active use during the runs.
- Port 8642 closed after each run; every process started was cleaned up.

## P1 finish — 0.23.3 canary, K7 warm-up, typed schemas (21 Nov, ~22:45–23:00 IST)

pytest on the PC after the change: **571 passed**, 0 failed (+6 in `test_m2_p1_finish.py`), 177 s.

Offline gateway benchmark — **SIMULATED MODEL, not live evidence**. `scripts/benchmark-m17-offline.py
--canary <dir> --hermes-version <v> --warmup on|off`; typed tool schemas on in all four runs.
**The PC was in active use during these runs** (last-input idle 0–31 ms at start), so absolute
latencies carry desktop load.

| Hermes | Warm-up | Det. | Adv. | Gateway ready | Warm-up run | First user turn first-delta / e2e | Warm first-delta p50/p95 | Warm e2e p50/p95 | Cancel ack p50 |
|---|---|---|---|---|---|---|---|---|---|
| 0.23.2 | off | 50/50 | 27/27 | 12631 ms | — | **4409.5 / 4550.7 ms** | 213.6 / 235.1 | 441.7 / 623.3 | 146 ms (5/5) |
| 0.23.2 | on | 50/50 | 27/27 | 6861 ms | 3955 ms (local answer) | **230.7 / 315.3 ms** | 213.0 / 231.4 | 436.8 / 622.2 | 150 ms (5/5) |
| 0.23.3 | off | 50/50 | 27/27 | 26892 ms (first start, fresh home) | — | **9051.2 / 9527.0 ms** | 221.7 / 234.0 | 445.4 / 640.6 | 202 ms (5/5) |
| 0.23.3 | on | 50/50 | 27/27 | 10056 ms | 4313 ms (local answer) | **226.2 / 332.5 ms** | 226.8 / 259.3 | 448.3 / 630.3 | 212 ms (5/5) |

Prohibited tools started: 0 in every run. Port 8642 closed after every run.
Evidence: `m2-evidence/bench-0232-typed-warmup-{off,on}.json`, `bench-0233-typed-warmup-{off,on}.json`.

## P3 memory v1 (21 Nov, ~23:05 IST, PC in use)

- pytest on the PC: **581 passed**, 0 failed (+10 in `test_m2_memory_v1.py`), 308 s (slower run; desktop in use).
- `scripts/benchmark-memory.py` (deterministic, no model, real broker `Store` in `canary-memory-m2`, removed afterwards): **40/40**.
  recall 10/10 · project scope 3/3 · contradiction 4/4 · duplicate 3/3 · correction 2/2 · deletion 3/3 · gating 7/7 · working 3/3 · **cross-restart 5/5**.
  Paraphrase-without-shared-words (known lexical gap, scored separately): 1/4.
  Search latency over 3,000+ items: p50 1.69 ms, p95 1.91 ms, max 6.08 ms; DB 2.16 MB. Evidence: `m2-evidence/benchmark-memory-v1.json`.

## Window suite 18/18 — owner-authorized unattended session (22 Nov, 02:51–03:01 IST)
Canary exe sha `9E0702AA…7F46` (frontend predates the P4 indicator; broker from working tree @488310e), simulated fixture inference (not live evidence).
- Run 1 (02:53–02:57): 18/18 scenario asserts passed but **ATTENDED-INVALID** — 1 outside input at 02:57:02 (confirmed by system idle clock: last input ≈02:57:00) and 1 "mode drift" logged during scenario-17 relaunch before the composer rendered (harness false positive → D16). Kept: `m2-evidence/window-suite-run1-attended.json`.
- Run 2 (02:58:22–03:01:12): **`WINDOW_SUITE_DONE 18/18 CLEAN`** — unattended true, 0 outside input, 0 drift, final_orphans [], 8642 closed, scenario 18 production stamps identical. `m2-evidence/window-suite.json`. Production exe hash after: `7A131F97…63C1` (unchanged).

## P4 real-window screen-target benchmark (22 Nov, ~03:02–03:04 IST, PC idle ≥5 min, foreground = Grok Bot app)
REAL local UIA/OCR on windows the script opened itself (Notepad; Edge `--app` with a throwaway profile); no model, no cloud. Every point was confirmed to lie on the benchmark's own window (WindowFromPoint root), and the product's reported window title was checked per case.
- Run 1: 14/19 — found 3 issues: selection-case harness bug (no ground-truth point requested), canvas returned U+FFFC as "text" (product bug → fixed), button expectation wrong (word under the centre of "Submit order" is "order").
- Run 2 (`m2-evidence/screen-target-run2.json`): **17/19**. Notepad 8/8 (6 words, line, selection); Edge HTML 9/9 (5 words, line, password field **refused with no leak**, canvas text via **OCR fallback** "QUANTUM", button); Edge PDF 0/2 (no UIA ground truth — K19, probe not run). Latency p50 544 ms (UIA), OCR case 3133 ms (K20). Leftover processes: none.
- Earlier (21 Nov 23:2x) attempt while a game was foreground: test window was occluded; the worker read only the game's window title, OCR found no text; that run is **invalid** and its harness now refuses occluded points.

## Full Python regression @4430f1f (22 Nov ~03:05 IST)
588 passed, 0 failed (161 s).

## M2 local model, pointer, voice, Guardian, HUD (22 Nov, 03:20–04:30 IST, PC idle, owner away)
All inference below is **LIVE local** (Ollama on 127.0.0.1, RTX 4060 Laptop) unless marked; cloud keys blanked in-process; no cloud call.

**Qwen3.5 4B direct (Ollama `/api/chat`, think off, num_ctx 4096)** — `m2-evidence/qwen-direct-bench.json`
| Metric | Result |
|---|---|
| GPU offload | `ollama ps`: 3.1 GB, **100% GPU**, ctx 4096; nvidia-smi 3767/8188 MiB, 89% util during run |
| Cold (first ever load from disk) | load 41.2 s, first token 79.1 s, total 81.6 s |
| Warm first token / full (40–60 tokens) | 276–306 ms / 0.93–1.14 s |
| Decode speed | 68.7–70.0 tok/s |
| Thinking default vs `reasoning_effort:none` (OpenAI API) | 16.3 s (1069 tokens) vs **0.42 s** (7 tokens) → D17 |
| Native tool calls | 3/3 correct (multiply 37×43, get_time, multiply 12×9) |

**Through the real broker** (`scripts/benchmark-m2-local-model.py`, canary-m2-local4) — `m2-evidence/benchmark-m2-local.json`
- First real run exposed **K22** (DirectChat stream bug, all chats failed) and template under-reservation (`usage_overrun`); both fixed, regression tests added.
- Final: chat **5/5** (warm first delta 317–346 ms, e2e 0.37–1.05 s); clock tool **3/3**, multiply tool **3/3**, two-tool steps **3/3** (each requires the tool to have actually run); prompt-injection turn: no shell, refusal. Tool turns 8.7–10.6 s (K24: Hermes per-task spawn). One clock answer mis-converted UTC→IST (K23).

**Pointer `pointer.move.v1` on the real desktop** (`scripts/pointer-desktop-test.py`, idle 726 s before, unchanged after) — `m2-evidence/pointer-desktop-test.json`
**8/8**: instant, smooth (500 ms), center, clamp to virtual-screen edge, deny (no move), corner fail-safe (refused), simulated user interruption (aborted "you moved the mouse"), non-command text (no approval asked). Cursor restored to its original position; 0 clicks/keys sent. pytest `test_m2_pointer.py` 27/27 (parser, strict schema, clamp incl. negative multi-monitor, corner/Esc/stop/drift aborts, approval/deny through the broker, 422 for model-granted capability).

**Voice end-to-end, synthetic audio** (`scripts/voice-e2e-local.py`; Piper-rendered questions, no microphone) — `m2-evidence/voice-e2e.json`
- 3/3 answers correct, STT WER 0.0 (faster-whisper CPU, 1.7–2.2 s), broker 0.66–1.17 s after D20 (was 6.6–7.4 s), Ultron (`ultron_conversational`, Kokoro onyx + DSP) peak −10…−14 dBFS, RMS −29.5 dBFS, **0 clipped samples**.
- Streaming speak first audio: Piper 3.8 s (cold process); Ultron cold 19.1 s, **warm 1.37–1.43 s** (K25). Playback cancel 4–5 ms; unavailable output device rejected.
- Live mic/speaker/barge-in: **PENDING** — `VOICE_LIVE_PROCEDURE.md`.

**PC Guardian** — real `Get-MpComputerStatus` (no admin): antivirus on, real-time on, tamper on, definitions today. pytest `test_m2_guardian.py` 7/7.

**Frontend** — status HUD + ModelHub local option: `pnpm check` pass, vitest **95/95** (15 files). Screenshots (headless Chrome, broker absent → offline state): `m2-evidence/ui-chat.png`, `ui-command.png`, `ui-chat-narrow.png`.

**Regression** — pytest (PC) **689 passed**, 0 failed (166.6 s) @50e5246.
**M2 release candidate @50e5246 (04:00–04:13 IST)** — canary rebuilt after the ModelHub change: release `B7DFB074…`, 4/4 hashed assets embedded, production exe `7A131F97…` before = after.
| Suite | Result |
|---|---|
| pytest (PC, full) | **689 passed**, 0 failed |
| vitest | **95/95** |
| `pnpm check` (tsc + eslint + prettier) | pass |
| cargo test (src-tauri) | **13/13** |
| window suite on RC canary `B7DFB074` | **18/18 CLEAN** (04:07–04:10 IST) — `m2-evidence/window-suite-rc-B7DFB074.json` |
| backup + restore drill | `%LOCALAPPDATA%\Immortility-backups\20261122-041221`: bundle verified, integrity ok, counts match (36/622/13/0) |

**Local merge into `main` (owner t14s1), 04:14 IST** — preconditions: `main` = edafc64, `m2/build..main` = 0 commits, merge-base edafc64. `git merge --no-ff m2/build` → **fa0da22** (parents edafc64 + 1eeb0a9); tree identical to m2/build; not pushed. Re-run on `main`: pytest **689 passed**, vitest **95/95**, cargo test **13/13**, `pnpm check` **FAIL — line endings only** (K27: the switch re-checked files out as CRLF; `prettier --end-of-line auto` on the same file list passes). Fixed on m2/build (9f9a785); `main` intentionally not re-merged. Switched back to `m2/build`; production exe `7A131F97…` unchanged; m1.7 still acf13fb.

**D23 memory embeddings (04:30–04:50 IST, LIVE local GPU)** — `m2-evidence/memory-embeddings.json`, `scripts/benchmark-memory-embeddings.py` (synthetic memories, in-memory DB).
| | lexical v1 | hybrid (nomic-embed-text) |
|---|---|---|
| direct questions recall@1 | 4/4 | 4/4 |
| paraphrases recall@1 / @3 (tuning set) | 3/16 / 3/16 | **11/16 / 14/16** |
| held-out paraphrases recall@1 / @3 | 7/10 / 7/10 | **9/10 / 10/10** |
| unrelated questions with any recall | 0/8 | **0/8** |
| search median | 0.1 ms | 11 ms |
Query embedding 39 ms warm (Ollama 40 ms server-side, 100% GPU, 335 MB); first version created an HTTP client per call (266 ms) → reused client. pytest `test_m2_memory_embed.py` 17/17; full PC pytest **705 passed**.

**Window suite** — HUD build (canary `18DC95A2…`): `WINDOW_SUITE_DONE 18/18 CLEAN` (04:0x IST) — `m2-evidence/window-suite-hud-18DC95A2.json`.

## M2 continuation after the merge (22 Nov, 04:31–05:20 IST, PC idle, owner away)
**K23 clock** — `clock.now.v1` returns local ISO time with offset + `utc` + display string; deterministic answer "Local time: 4:55 AM on Sunday 22 November 2026 (IST, UTC+05:30)". `test_m2_clock_local.py` 5/5; the old `test_registry` clock test asserted UTC and was updated to assert the local reading (8cd0ac9).

**K25 voice warm-up (D26), LIVE CPU** — `m2-evidence/infernal-warm.json`: cold render 16.0 s, warm 3.0 s; warm-up 13.3 s runs while the user talks. `test_m2_voice_warm.py` 5/5.

**Free web research (D25), LIVE public endpoints** — `m2-evidence/web-research-live.json`: DuckDuckGo Instant Answers answered 3/5 factual queries in ≈340–440 ms; a nonsense query correctly returned nothing; Wikipedia skipped without an owner contact (Wikimedia UA policy → 403). One diagnostic request used a made-up contact URL in the User-Agent (`https://github.com/reyansh/immortility`); not repeated. `test_m2_web_search.py` 9/9.

**Hermes 0.23.3 extended rerun — SIMULATED model (not live evidence)** — `m2-evidence/bench-0233-extended-warmup-on.json`: deterministic **50/50**, adversarial **27/27** (0 prohibited tools), cancels **5/5** (client p50 178 ms, broker p50 141 ms). Warm chat e2e p50 316 ms / first delta p50 216 ms; all warm e2e p50 435 ms, p95 632 ms; warm-up 4.3 s, gateway cold start 13.3 s, broker start 13.8 s.

**Explain this (D24), real window, LIVE local model** — `scripts/explain-window-test.ps1` on canary `6547B63A…` (built 05:02 IST; production exe `7A131F97…` before = after), PC idle 6324 s, foreground "Grok Bot", 0 outside-input events. Pointed only at Immortility's own composer hint. Result **10/10** — `m2-evidence/explain-window-real.json`: button enabled with Local Qwen; preview showed the pointed line + "stays on this PC"; screen read 4.0 s (incl. 3 s countdown); answer 1.4 s from `immortility-qwen3.5-4b` ("…press Enter to send and hold Shift+Enter to create a new line"); usage by provider `{"local": 1}`; 0 tool events; privacy `personal`; relaunched in cloud mode → button disabled with the explanation. (Memory v1 is off in that canary copy, so "no memory written" there is trivially true; the memory/history exclusions are covered by `test_m2_explain_this.py` 7/7.)
Earlier attempts found real defects, all fixed before the passing run: (1) K29 observer pins broken by CRLF → screen read 503; (2) in the simulated canary the screen turn ran on the Hermes fixture → screen turns now go only to tool-free local DirectChat, agent runtimes refused (a46af22); (3) the session's earlier chat leaked into the explanation → screen turns get no history/notes/recall/facts/memory (01984e3). Test-harness fixes: aim at static visible text and the bottom-most composer hint.

**M2 RC2 on m2/build @b7e1130 (05:19–05:28 IST)**: canary rebuilt 0C01CD48... (production exe 7A131F97... before = after).
| Suite | Result |
|---|---|
| pytest (PC, full) | **732 passed**, 0 failed (168.8 s) |
| vitest | **100/100** (15 files) |
| `pnpm check` | pass |
| cargo test | **13/13** |
| pinned-hash check | 0 tracked mismatches / 1787 |
| window suite (simulated fixture) | **18/18 CLEAN** - `m2-evidence/window-suite-rc2-0C01CD48.json` |
| Explain this real window (live local Qwen) | **10/10**, read 4.3 s incl. 3 s countdown, answer 8.4 s (cold model load), usage `{local:1}` - `m2-evidence/explain-window-rc2-0C01CD48.json` |

**Second local merge into main (owner t14s1), 05:31 IST**: preconditions main = fa0da22 with no unique commits except that merge; `git merge --no-ff m2/build` -> **c98ad22** (parents fa0da22 + bb4d3ba), tree identical to m2/build, not pushed. Re-verified on main: pytest **732 passed**, vitest **100/100**, `pnpm check` **pass** (K27 fixed on main), cargo test **13/13**, pinned-hash check 0 mismatches. Switched back to m2/build (production exe follows the checked-out tree, K5). m1.7/release-hardening = acf13fb, production exe 7A131F97... unchanged.

## Not run (by rule)

- 18/18 desktop window suite: waiting for an owner-scheduled ~10 min uninterrupted session (`WINDOW_SUITE_PROCEDURE.md`).
- Any live provider inference (Groq/Gemini/NVIDIA): locked until owner approval + budget (`PROVIDER_READINESS_M2.md`).
