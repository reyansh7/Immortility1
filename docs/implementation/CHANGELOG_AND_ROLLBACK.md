# Changes and reversible recovery

Latest continuation: [critical repairs checkpoint](CRITICAL_REPAIRS_CHECKPOINT.md), CRITICAL_REPAIRS_VERIFICATION.json. This adds chat outcome/recovery and identity, CPU voice/lazy CUDA fallback and WAV fixes, native-private background attachment and whole-job cleanup, plus scoped Settings/readability changes. The new report records exact source hashes and changes since OBSERVATION_BASELINE.json. M0_CHANGED_FILES.json below remains the earlier historical register.

Do not restore shared main.tsx, native main.rs, Cargo.toml or voice files wholesale from a prior checkpoint. Review the current hunks and concurrent editor changes first. Native observation and SDK tools remain separately gated; turning off their entry points or detaching the UI is reversible. Explicitly stop a published test runtime through its authenticated shutdown before removing its owned temporary credentials. No production database migration or service installation was added by the critical-repair slice.

The checkout already contained extensive tracked/untracked user work. No blanket staging, reset, branch switch, commit or source deletion was performed. The review unit is the [exact change register](M0_CHANGED_FILES.json), compared against the [before snapshot](M0_BASELINE.json) and `.cache/engineering-m0/before/` source copies.

## Behavioral changes

- Hardened Windows path/byte/temp-file handling and bounded traversal; scope checks remain a file adapter, not a code sandbox.
- Task-bound expiring approval authority and revocation; journal before write; readback; cancellable review; recover failed/cancelled approved writes; new-file rollback restores nonexistence.
- Persistent recall exclusion across all automatic task recall paths; no history/evidence erasure claim.
- Durable task/attempt/call ledger, conservative unknown reservations, total caps and rotated grant keys; fixed read-only native usage operation.
- Native Windows credential dialog replaces React key input; old generic key IPC operation is rejected. Secret-like input is blocked before task persistence/research and again at inference; arbitrary upstream error text is suppressed.
- Async bounded Wikipedia transport and exact runtime prompt wiring; streamed incoming-body limit.
- Shared cancellation-safe Windows process ownership, including suspended startup; existing speech preferences/models/profile files preserved. Production Qwen and untrusted code execution cannot be enabled by environment.
- Default-off fixed arithmetic gateway using separately installed official MCP SDK 2.2.0. Legacy Content-Length demo kept separate. No external server/browser/scheduler/framework was installed.
- Explicit direct pin to already-installed `httpcore==1.0.9`; broker lock refreshed offline. Formatter-only changes are identified in the source register.

## Data migration

New SQLite user version is **3**. Opening v1 creates a consistent online SQLite backup beside the database (`<database-name>.pre-m0-<unique>.sqlite`) before schema changes. Main/WAL content is included by SQLite's backup API. Existing backups are never overwritten. The previous broker refuses a database with newer `user_version`, preventing silent downgrade.

The v2 migration adds usage tables; v3 adds durable workflow definitions/checkpoints. Opening v2 creates a `.pre-v2-<unique>.sqlite` backup before migrating. Recall exclusion is stored in each affected task JSON. Tests cover preservation and one backup on upgrade, not repeated backup every startup. Backups and rollback records contain user history/source; retain privately and manage deletion through a separately reviewed retention policy. No live personal database was opened by these tests; test/smoke brokers use temporary roots.

## Rollback procedure

1. Stop the application and verify its owned processes have exited. Preserve current source and data before rollback; do not run `git reset --hard` in this dirty checkout.
2. Review `M0_CHANGED_FILES.json`. Restore only selected task-authored changes from `.cache/engineering-m0/before/<relative-path>` after comparing against later user edits. New task-authored files are explicitly listed; do not delete pre-existing untracked files based on Git status.
3. For a v3 database, restore its matching v2/v1 SQLite backup **as a complete stopped database**, using a new recovery directory first. Do not mix an older main DB with newer `-wal`/`-shm` files. Keep current data until recovery is verified. Never blindly decrement `user_version`.
4. The MCP runtime is isolated in `.venv-mcp`; disabling `STANDARD_MCP_ENABLED` stops new launches. Removing that task-owned environment is optional after confirming no live worker; it does not change Hermes, broker or any speech environment. Do not repin an unreviewed runtime merely to make integrity verification pass.
5. Re-run the agreed checks and offline Hermes normal/adversarial/Stop smoke. No external credential/account mutation is required.

## Recreate the isolated MCP environment

PowerShell from repository root, after reviewing the lock and audit:

```powershell
. ./scripts/dev-env.ps1
uv venv .venv-mcp --python .venv/Scripts/python.exe --no-managed-python
uv pip sync --python .venv-mcp/Scripts/python.exe config/mcp-requirements.lock --require-hashes --only-binary :all:
.venv/Scripts/python.exe -m pytest -q services/broker/tests/test_standard_mcp.py
.venv/Scripts/python.exe scripts/benchmark-standard-mcp.py
```

No model, user token, private upload, OAuth connection or paid action is involved. Integrity pins were recorded for the reviewed Windows/Python build; a changed executable/dependency requires a fresh reviewed compatibility/security check, not an automatic runtime upgrade.

Future sends, deletes, purchases, deployment, pushes, account pairing, private cloud uploads and model downloads still require their specific established authorization. The user authorized engineering implementation, not those external effects.


## Durable workflow and native observer increment

Existing Engine/Store now own the optional local read-only queue/DAG/checkpoints and explicit headless mode. Database version3 also enforces a single live owner with an OS file lock; an existing `.owner.lock` file alone does not prove an owner is running. Do not remove locks to bypass a live broker. Choose a matching versioned broker when restoring a v1/v2 backup; do not decrement the current version or mix WAL generations. Tests and real crash/restart smoke use temporary databases, not personal history.

The follow-up admission guard rejects credential-like input before persistence/research, and Windows jobs can enforce an optional whole-job commit ceiling. Existing workers retain their previous default resource configuration.

Observer source is an isolated scratch-only experiment: `integrations/windows-observer/`, `scripts/smoke-windows-observer.py`, `scripts/verify-observer-runtime.py`, and `config/observer-*`. It registers no product tool and installs no autorun/service. The four-package `.venv-observer` can be retained without an idle worker. Any removal requires confirming its exact resolved workspace path and that owned evaluations have ended; no deletion was performed here. Do not re-record runtime pins merely to suppress a failed integrity check. [Acceptance and promotion gates](WINDOWS_OBSERVATION_STATUS.md).

The current source/config rollback register covers30 modified baseline files and37 new task-authored files. New docs/evidence are separate; the pasted directives are preserved user inputs. Preserve all other pre-existing untracked work and compare against later user edits before selective restoration.
