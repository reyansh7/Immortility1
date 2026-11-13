# 11 — Operational playbook and releases

## Process ownership
Desktop shell supervises broker and its child workers. Per-worker lifecycle: `absent -> starting -> healthy -> draining -> stopped` with crash/exhausted/restart states. UI remains useful if a worker is unavailable. Prevent duplicate background processes on repeated launches.

## Data ownership
- SQLite migrations are transactional and reversible when possible; back up DB before destructive migrations.
- Store task/event/audit metadata separate from content and user-supplied files.
- Autoclean temporary screenshots, transcriptions and media after documented TTL unless user opts to retain.
- Export/delete personal memories and logs with one user command.

## Secrets and updates
- Store credentials in OS secret store; redact shell command arguments and crash dumps.
- Open-source dependencies are pinned, SBOM generated, licenses noted, security advisories reviewed.
- Auto-update starts OFF until signed release/update validation is implemented. Display update description and consent.
- For third-party adapters: use compatibility matrix, checksum verification and safe rollback.

## Incident scenarios
- Paid call unexpectedly allowed -> disable cloud outbound requests, log incident metadata (not secrets), investigate policy path.
- Prompt injection succeeded -> revoke grants, quarantine affected MCP tool, inspect audit, rotate tokens.
- Machine resources exhausted -> terminate media worker, restore low-power orb and postpone tasks.
- Broker crash -> on restart reconcile task states; never replay irreversible actions automatically.

## Packaging
Initial deliverable is a local developer build; after P8 produce signed `.msi`/`.exe` if tooling and certificate available, plus uninstall handling. Avoid claiming signed binaries without a valid signing identity.

## Git strategy
`main` always bootstrappable; feature branches per phase; smaller reviewable PRs; conventional commits optional; staging builds with reproducible lockfiles; no vendored model weights.
