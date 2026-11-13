# 08 — Contracts, events, orchestration and adapters

The files `packages/contracts/schemas/*.json` are normative schema drafts. Keep TypeScript types and Pydantic models generated from, or tested against, these contracts; no hand-edited divergence.

## Task lifecycle
`created -> queued -> running -> awaiting_approval -> running -> verifying -> succeeded` with terminal `failed | cancelled | blocked`. Tasks can also pause with `rate_limited` or `disconnected`, not silently succeed.

## Required task fields
`task_id`, `session_id`, `request_id`, `created_at` (ISO UTC), `input` (type/content/resource refs), `workspace_id`, `privacy_class`, `capabilities`, `deadline_ms`, `status`, `parent_task_id?`, `budget`, `result?`, `error?`.

## Event stream
`event_id`, `task_id`, `sequence`, `timestamp`, `type`, `actor`, `data` with typed event types: `message.delta`, `task.state`, `tool.started`, `tool.progress`, `tool.completed`, `approval.requested`, `approval.resolved`, `artifact.created`, `audit.notice`, `task.error`.

## Tool manifests
For each adapter, declare input/output schema, risk tier, required scopes, secrets required, local/remote egress, OS support, timeout, cancel mechanism, idempotency and verification method. No dynamic arbitrary command string tools exposed to LLM by default.

## Broker API target (Phase 1 minimal)
- `GET /health/live` — liveness only; no secret data.
- `GET /health/ready` — authenticated readiness with dependency statuses.
- `POST /v1/sessions` — creates session; requires local authenticated caller.
- `POST /v1/tasks` — enqueues conversational task with idempotency key.
- `GET /v1/tasks/{id}` — current state.
- `GET /v1/tasks/{id}/events` — authenticated SSE replay with last-event-id.
- `POST /v1/tasks/{id}/cancel` — cancellation and worker signal.
- `POST /v1/approvals/{id}/decision` — future phase, binds exact action digest.
No broker tool execution endpoints until permissions policy and tests exist.

## Hermes compatibility strategy
Use documented interface, not internal imports by default:
- Prefer **TUI gateway JSON-RPC** when requiring stream, approvals, slash commands and session controls.
- For Phase 1 basic conversation, the **API server** may be simpler: `/v1/runs`, `/v1/runs/{id}/events` and stop endpoint.
- Probe supported Hermes version and capabilities; do not invent API methods.
- Explicitly disable unmediated Hermes terminal/file/browser/computer-use/code-execution/cron and tool/plugin installation in P1. In later phases re-enable only independently sandboxed or broker-mediated capabilities; require a negative tool-call test.
- Keep Hermes process under supervisor/health model; don't expose server beyond loopback.

## Cursor adapter (P5)
Spawn official CLI in verified worktree and parse NDJSON `--output-format stream-json`; handle malformed chunks, final success/failure, timeouts and process cancellation. No blanket `--force`. Prefer `--worktree` if compatible with installed version; compare changed files and test evidence before reporting success.

## OpenMausBot adapter (P5; not activated)
Use the audited stdio MCP control plane only after installed Windows paths, pairing,
free-model route, idempotency, waits and interruption are verified. Sends may trigger
tools: every privileged action must pass Immortility's broker, not merely an upstream
approval card. Keep native execution disabled until a broker-mediated seam exists.
See [OPENMAUSBOT.md](../integrations/OPENMAUSBOT.md). No cookie scraping, account
inheritance, duplicate memory/scheduler/controller or recursive Hermes delegation.

## Compatibility and versioning
All contracts use `schema_version` with semantic evolution, idempotent retries, forward-compatible unknown event types handled as opaque, and migration tests.
