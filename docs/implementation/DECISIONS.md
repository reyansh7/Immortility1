# Technical decision record (living, M2 onward)

Format: ID · date (IST) · decision · why · alternatives rejected · reversibility.

**D1 · 21 Nov · Work on `m2/build`, branched from `m1.7/release-hardening` @ acf13fb.**
m1.7 stays untouched as the rollback point; `checkpoint/m1-2026-11-17` untouched. Nothing pushed or merged.

**D2 · 21 Nov · Hermes versions.** Verified against official GitHub tags/releases (21 Nov 2026):
v0.23.3 is the latest **stable** (tag commit `caafe538`, published 20 Nov 2026 06:04 IST);
latest canary `v0.23.3+canary.20261120T064609Z` (`32dbc1dc`). The research claim of 0.23.3
was correct; the owner's note (0.23.2 latest) predates it. Production stays **0.21.1 @04b88a4c**
(stdio). Canary stays **0.23.2 @ae2a81cc** (= official v0.23.2 commit) until 0.23.3 passes the
regression in a separate `canary-0233-*` dir. Reason: 1,657 commits since 0.23.2.

**D3 · 21 Nov · Broken-pipe test: fix the product, not the test.** The test encoded the right
contract (kill + wait + clear meter + propagate the original error). `reap()` now always kills
the owned child; cleanup cannot mask the original exception.

**D4 · 21 Nov · Window-suite hardening via the test harness, not the product.**
`EnableWindow(FALSE)` on the suite's own window during the expiry wait + `GetLastInputInfo`
detection + compact-mode drift recording. Rejected: `BlockInput` (needs elevation), disabling
approvals or Escape handling in the app (changes production), longer waits (doesn't fix input).

**D5 · 21 Nov · Run-scoped authorization for the warm gateway = per-task HMAC binding in Hermes
ephemeral `instructions` + relayed-proposal binding for tool calls.**
Why: Hermes 0.23.x outbound chat requests carry no run/session id we can trust, but its
runs API accepts `instructions`, which Hermes appends to the system prompt on every model call
of that run and never persists. Binding is `HMAC(secret_per_broker_process, task_id)`:
stable within a task (keeps Hermes `Idempotency-Key` replay valid), different across tasks,
invalidated by broker restart. The broker strips it before any provider/fixture sees it.
Tool calls over the warm key must match a proposal the broker relayed and authorized in this
task's stream; an unrelayed call never consumes an approve-once grant.
Rejected: per-run API key (Hermes has one provider key per process), restarting the gateway
per task (defeats warm runtime), trusting `X-Hermes-Session-*` headers (not sent upstream).
Reversible: remove the `instructions` field and the two checks.

**D6 · 21 Nov · Proposed (needs owner OK): move build caches off OneDrive.**
Exclude or relocate `.venv*`, `.cache`, `node_modules`, `apps/desktop/src-tauri/target`,
`.tools` (≈ several GB of churn). Option A (no layout change): mark them "Always keep on this
device" / exclude from sync. Option B: move repo to `C:\dev\IMMORTILITY` and update the
production shortcut. Not done: it changes where production runs from.

**D7 · 21 Nov · Backups live outside OneDrive in `%LOCALAPPDATA%\Immortility-backups\<stamp>`**
(git bundle of all refs + consistent SQLite snapshot taken from a scratch copy + manifest +
restore drill). Keys are not exported (they live in Windows Credential Manager).

**D8 · 21 Nov · Tests that need live inference are not substituted by simulations.** Simulated
results are labelled "simulated fixture" everywhere and are never counted toward the ≥90% gate.
