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

## Not run (by rule)

- 18/18 desktop window suite: waiting for an owner-scheduled ~10 min uninterrupted session (`WINDOW_SUITE_PROCEDURE.md`).
- Any live provider inference (Groq/Gemini/NVIDIA): locked until owner approval + budget (`PROVIDER_READINESS_M2.md`).
