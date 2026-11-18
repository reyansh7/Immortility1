# M1.7 release, feature flags and rollback

## What ships in M1.7
- Broker run lifecycle:
  - POST /v1/runs is tracked per task, and SSE is deduped by seq / event id.
  - Stops are confirmed. A run created while the task was being cancelled is stopped.
  - After a provider error, a repeat fails fast with 403 instead of letting Hermes retry.
- Approve-once tool approvals:
  - States: awaiting_approval, then approve, deny or expired.
  - A replay, mismatch or expired approval returns 409.
- Gateway supervision:
  - Job Object ownership and an owner record.
  - Orphans are reclaimed only when their identity is verified.
  - Restarts mark non-terminal tasks `disconnected`.
- Packaging: `custom-protocol` is no longer a default Cargo feature. `tauri build` and `scripts/build-canary.ps1` turn it on, so release builds embed `dist` and no longer depend on Vite.
- Test tooling:
  - `scripts/desktop-window-suite.ps1`: 18 scenarios.
  - `scripts/benchmark-m17-offline.py`: 50 deterministic and 27 adversarial cases.
  - `scripts/live-pilot.py`: gated, not run.

## Feature flags (all default OFF; files in the broker data dir)
| Flag file | Effect when present and valid | Default |
|---|---|---|
| `hermes-gateway.json` `{"enabled": true}` | Use Hermes 0.23.2 runs API gateway | absent → **Hermes 0.21.1** (production unchanged) |
| `simulated-inference.json` `{"enabled": true, "category": "simulated_model"}` | Local fixture instead of any provider (canary only) | absent → off. An env var cannot enable it |
| `local-tools.json` `{"enabled": true}` | Enables broker local tools (clock; needed by the SIM:steps canary admission) | absent → off |
| `workspace.json` | Project read root for `project.*` tools | absent → none |
| `laptop.json` | Laptop storage audit | absent → off |
| `capability-flags.json` | web_research / mcp / standard_mcp toggles | absent → defaults |
| Cargo feature `custom-protocol` | Embed frontend in exe | off for `cargo build`, on for `tauri build` / build-canary |

Also gated:
- The SIM:steps canary admission applies only when simulated inference is on, local tools are on, the request is text, and no explicit capabilities were given.
- The production data dir `%LOCALAPPDATA%\Immortility` has no `hermes-gateway.json` or `simulated-inference.json`. This was verified before and after the window suite.

## Release procedure (not performed in M1.7)
1. Full regression is green: Python (except the known baseline `test_infernal::test_broken_worker_pipe_is_reaped_and_meter_cleared`), Vitest, tsc, cargo test, window suite and canary build.
2. Build with `pnpm tauri build`, or `scripts/build-canary.ps1` for a canary into `%TEMP%\immortility-canary-build`. Check the embedded asset count.
3. Keep the current production exe (`apps\desktop\src-tauri\target\release\immortility-desktop.exe`) and its SHA-256 as the rollback artifact before replacing anything. M1.7 did **not** replace it.
4. Enable the 0.23.2 gateway for a user only by writing `hermes-gateway.json`, and only after a live pilot is approved and passes.

## Rollback
- **Gateway**: delete or rename `hermes-gateway.json` and restart the app. The broker returns to Hermes 0.21.1, which was never modified.
- **Simulated fixture / local tools**: remove `simulated-inference.json` or `local-tools.json` in the canary dir. Production never had them.
- **Code**: everything is on branch `m1.7/release-hardening`:
  - 6084fb6: WIP
  - 295c8d8
  - 9da60ea
  - 342e75b
  - fd9ee49
  - later docs and test commits

  `checkpoint/m1-2026-11-17` and 133df63 are untouched. To roll back, check out that checkpoint or revert individual commits. Do not `reset --hard` over uncommitted work.
- **Database**: M1.7 added no schema migration. Task rows written by the canary live only in the canary DB.
- **Processes**: stop the app. The gateway lives in the desktop's Job Object and exits with it. If an orphan is left, the broker reclaims it on the next start, but only when the PID, creation time and image match its owner record.
