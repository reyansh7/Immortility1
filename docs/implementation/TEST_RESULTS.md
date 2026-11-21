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

## Not run (by rule)

- 18/18 desktop window suite: waiting for an owner-scheduled ~10 min uninterrupted session (`WINDOW_SUITE_PROCEDURE.md`).
- Any live provider inference (Groq/Gemini/NVIDIA): locked until owner approval + budget (`PROVIDER_READINESS_M2.md`).
