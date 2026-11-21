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

**D9 · 21 Nov · Hermes 0.23.3 canary layout.** Source `%LOCALAPPDATA%\Immortility\canary-0233-src` (official tag v0.23.3, commit caafe538, verified), HERMES_HOME files in `%LOCALAPPDATA%\Immortility\canary-0233-home`, broker data in `canary-0233-m2`. Installed with Hermes' own `python -m pm.cli install --without chromium --without cua-driver` using the existing isolated Python 3.14.9, with HERMES_HOME/USERPROFILE/LOCALAPPDATA/APPDATA all pointed inside the canary home (production `%LOCALAPPDATA%\hermes` last written 17 Nov — untouched). The deepest workspace file is ≈215 chars below HERMES_HOME, so HERMES_HOME is the short directory junction `%LOCALAPPDATA%\h0233` (same reason `h0232` exists). The pin is `canary_only` in `hermes_gateway.GATEWAY_PINS`: `apply_gateway_flag` ignores it and `GatewaySupervisor` refuses it unless the data dir is `canary-*`.

**D10 · 21 Nov · K7 warm-up is a real Hermes run answered by the broker.** Hermes already pre-builds tool schemas at boot, but the first `/v1/runs` still spent ≈4–9 s before its first model request. The broker now issues one warm-up run after readiness with a fresh binding (not a task binding). The inference endpoint answers that binding locally with a fixed `ready` (model `immortility/local-warmup`, 0 tokens, ≤2 calls) and only while the warm-up is in flight; the warm key is otherwise accepted only with an active task grant, as before. No provider, fixture, ledger row, task or approval is involved. Opt-out: `"warmup": false` in the canary flag file.

**D11 · 21 Nov · Typed tool schemas default on the gateway path only.** `typed_tool_schemas_enabled` becomes true when the gateway flag is applied (opt-out `"typed_tool_schemas": false`). The global default stays false so the 0.21.1 desktop default, which the production exe runs from this working tree (K5), is unchanged.

**D12 · 21 Nov · Memory v1 is lexical-hybrid; vector embeddings deferred.** Researched sqlite-vec: v0.1.9 (31 Mar 2026; 0.1.10 only alpha), MIT/Apache-2.0, ~0.9 MB wheels incl. win_amd64, pre-v1 with breaking changes expected, 253 open issues. It is acceptable on licence and size, but it only stores vectors: it also needs a local embedding model and runtime (e.g. a static model2vec or ONNX MiniLM, 30–90 MB plus numpy/tokenizers), which counts as installing a model, and it needs `enable_load_extension` on the broker's Python. v1 therefore uses FTS5 (porter, bm25) fused with token overlap, recency, confidence, category weight and project match, and indexes each statement's slot subject ("name", "home location") so slot questions match without shared words. Benchmark: 40/40 functional cases; paraphrases with no shared words found 1/4 (the measured gap). Revisit embeddings when the owner approves a small local embedding model; the `memory_items` schema needs no change for that (side table keyed by id).

**D13 · 21 Nov · Memory deletion is content deletion plus recall exclusion.** Deleting a memory blanks body/subject/provenance (tombstone keeps id, category, timestamps), removes it from FTS, deletes every other memory item derived from the same task, and marks that task `recall_excluded` so task notes, `memory_fts` and conversation history cannot resurface it. Not secure erasure of WAL/backups (same limit as the existing `forget`).


**D14 · 21 Nov · P4 screen target is a user-initiated, broker-run, read-only local read.** `POST /v1/screen/target` (desktop session token only; not a model capability, not in the tool list) runs the hash-pinned worker `integrations/windows-observer/screen_target.py` under `.venv-observer` (`-I`, temp profile, job memory cap, no window): `WindowFromPoint`→root window is checked first (sensitive processes such as password managers/UAC/lock screen and titles containing password/sign in/credential/OTP are refused with the title withheld), then UIA `ElementFromPoint` → `TextPattern.RangeFromPoint` → `ExpandToEnclosingUnit(word|line)`, accepted only if the range's bounding rectangles contain the point; else the element Name. Any element with `IsPassword` or an `ES_PASSWORD` edit is refused *before* text is read, and the OCR fallback is never run after a refusal. Selection is read from the hovered document, or from the focused element only when it is inside the same top-level window. OCR fallback (`ocr_crop.ps1`): Windows.Media.Ocr over a ≤420×96 in-memory crop around the point, nothing written to disk; the word under/nearest (≤12 px) the point is chosen. Results are returned to the caller only — not stored, not audited with content, never sent to a provider by this module. While a read runs, `/v1/runtime/status.screen_access.active` is true and the desktop shows "● Reading text under cursor (on this PC)" (held ≥1.5 s). Wiring the result into chat/voice ("explain this") is a later step and will reuse the existing data-not-instructions labelling.
