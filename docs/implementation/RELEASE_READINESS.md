# Release readiness (living)

As of 21 Nov 2026 (IST), branch `m2/build`. **Not release-ready. Production unchanged.**

## Production state (verified, untouched)
- Installed exe `apps\desktop\src-tauri\target\release\immortility-desktop.exe` SHA-256
  `7A131F97887EE9C39EA3805E774BCF804A2E3082575F9B831C37B489186663C1` (16 Nov 2026 19:17) — same before and after all M2 work.
- Production Hermes: **0.21.1 @04b88a4c** (stdio), no `hermes-gateway.json`, no `simulated-inference.json`
  in `%LOCALAPPDATA%\Immortility`.
- Production DB: 36 tasks / 622 events / 13 memory rows / 0 confirmed facts (read from a copy only).
- Note (K5): the exe runs the broker from the repo working tree; M2 broker changes are inert in
  production (warm-gateway path is flag-off), but `git switch m1.7/release-hardening` pins it exactly.

## Gates
| Gate | Status | Evidence / owner action |
|---|---|---|
| Python tests | PASS | 557 passed at P0 (616299c); P1 rerun in `TEST_RESULTS.md` |
| Vitest / tsc / ESLint / Prettier | PASS | 89/89; `pnpm check` clean |
| cargo test | PASS | 13/13 |
| Offline gateway benchmark (simulated) | PASS | 50/50 deterministic, 27/27 adversarial, 5/5 cancels, 8642 closed (4 runs) |
| ruff check | PASS | clean |
| ruff format / mypy | FAIL (pre-existing) | K3, K4 — typing/format debt, not hidden |
| Window suite 18/18 | **BLOCKED (owner)** | ~10 min uninterrupted desktop; `WINDOW_SUITE_PROCEDURE.md` |
| Live provider pilot | **BLOCKED (owner)** | `PROVIDER_READINESS_M2.md` §3 answers + written budget |
| ≥90% live tool success | BLOCKED | needs live pilot |
| Backup + restore drill | PASS | `%LOCALAPPDATA%\Immortility-backups\20261121-221731` |
| Push / merge | NOT REQUESTED | after 18/18 |

## Rollback
- Code: `git switch m1.7/release-hardening` (acf13fb) or `checkpoint/m1-2026-11-17` (133df63).
- Full repo restore: `git clone <backup>\repo.bundle` (all refs).
- Data: stop the app, rename current `state.sqlite3*` aside (never delete), copy `data\state.sqlite3` from the backup.
- Gateway: remove `hermes-gateway.json` (production never had it).
