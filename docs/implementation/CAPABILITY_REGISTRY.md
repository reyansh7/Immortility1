# Implemented capability contracts

The single broker registry contains two reviewed local reads: arithmetic and clock. It is not a universal plugin loader. Runtime registrations in application code are authoritative; JSON manifests are review inventories. Legacy arithmetic remains separate and disabled by default.

## `arithmetic.add.v1` â€” EXPERIMENTAL, default off

Reviewed schema inventory: [manifest and input/output](../../config/capabilities/arithmetic.add.v1.json). Implementation: `services/broker/src/immortility_broker/capabilities.py`, `standard_mcp.py`; reviewed scripts: `integrations/mcp-standard/`. Dependency lock: [29 pinned packages](../../config/mcp-requirements.lock); integrity manifest: [runtime pins](../../config/mcp-standard-runtime.json).

| Property | Contract |
|---|---|
| Input | Strict object `{ "a": 7, "b": 8 }`; integers each within Â±1,000,000,000; no extra fields |
| Output | Strict `{ "result": 15 }`; bounded integer; no executable content |
| Side effects | None to user files/accounts; ephemeral local process/config/temp directory only |
| Network / paid inference | None; no model credentials in environment; zero model calls |
| Scope | Current running broker task + session + real ledger attempt |
| Grant | Broker-created opaque token, monotonic expiry, 1â€“4 dispatches; consumed before await; Stop revokes/cancels |
| Concurrency | One gateway execution lease |
| Limits | 10-second operation deadline; bounded control input/output; SDK protocol timeout; owned tree reap â‰¤3 seconds target |
| Feature gate | `STANDARD_MCP_ENABLED=false` by default, independent of legacy `MCP_ENABLED` |
| Agent exposure | Only exact deterministic `add <integer> and <integer>` intent; no Hermes native tool enabled and no bulk schema injection |
| Validation | Real SDK initialize/list/call, exact expected inventory, typed local output, independent NDJSON-peer test |

Example in an isolated test broker: construct `Settings(_env_file=None, data_dir=scratch, standard_mcp_enabled=True)` and submit `add 7 and 8` through the existing task API. This is demonstrated by `test_real_broker_local_arithmetic_uses_no_hermes_or_cloud`. Existing task admission still requires the `cloud_consent` field for API compatibility; this exact local route sends no cloud request.

Paired cold startup now passes10/10; complete B1 hostile-server/transport acceptance is still required before promoting general servers. The SDK worker accepts only fixed `discover`/`add`; it cannot receive a server command, package install request, endpoint URL, token, account, shell argument or file path from the model.

## Existing capabilities retained

- Conversational tasks: pinned tool-free Hermes through broker; current free provider only. `budget_mode` supports explicit `fast`/`standard`/`deep`; auto does not silently select Deep.
- Scoped text patch proposal: exact trusted approval, root and byte snapshot; task-owned post-write review; code execution disabled. Model `VERDICT` text is not independent verification.
- Wikipedia: opt-in public-only async source fetch with bounded extraction and actual prompt wiring. General search/multi-site browsing is not implemented.
- Task memory search: SQLite FTS, current session; durable recall exclusion after Forget. Evidence/history is a separate retained surface.
- Existing local voice: selected settings/profiles retained; owned processes hardened; no cloud audio added.
- Legacy `/v1/mcp/tools` and `/v1/mcp/call`: **Content-Length arithmetic demonstration**, not standard MCP interoperability. No external servers.
- Read-only `/v1/tasks/{id}/usage`: attempt/call metadata, reservations/reports/unknowns, no prompt text or credential. Fixed native IPC is `task_usage`.

## Required before another capability

Add a reviewed versioned manifest, strict input/output, data provenance and egress policy, idempotency semantics, action digest, minimum scope, task deadline and cancellation, secret-free diagnostics, controller/resource ownership, negative fixtures and a real reversible demonstration. Server descriptions cannot authorize tools. Remote MCP/Streamable HTTP, OAuth, browser submission, Windows input, arbitrary execution, account connectors, sends/deletes and scheduled effects remain unregistered/disabled.


## `clock.now.v1` and durable workflows

The existing opt-in local clock now uses the same registry/grant/dispatch path: strict empty input, timezone-bearing ISO timestamp output, `LOCAL_TOOLS_ENABLED=false` by default. [Inventory](../../config/capabilities/clock.now.v1.json). Time output varies; the classification means a deterministic local adapter without model reasoning, not an immutable clock value. It never introduces another planner or scheduler. Both local adapters work without Hermes/provider credentials; unknown tools are denied.

`DURABLE_WORKFLOWS_ENABLED=false` by default. POST `/v1/workflows` accepts <=16 typed steps/dependencies, explicit `local_read_consent:true`, `no_cloud:true`, original <=1-hour expiry, <=2 retries and optional explicit restart consent. Only the two enabled reviewed local reads are admitted. Existing Engine/SQLite own admission, dispatch, checkpoint/retry/Stop and recovery; no extra runtime. Completed steps are digest-verified and not replayed, unfinished reads may resume within original expiry/attempt bounds. Results have no-cloud/no-recall provenance and a real zero-call ledger attempt. One database owner is enforced; SQLite v3 backs up v1/v2 before migration.

Fixed native operations: `ListCapabilities`, `CreateWorkflow`, `GetWorkflow`, `TaskUsage`; no generic capability-call/command tunnel. GET `/v1/capabilities` supplies scoped metadata only. Headless local-only mode skips vault/provider loading and denies model, settings and voice writes. Its actual process smoke is `scripts/smoke-headless-workflows.py`; no service/autorun or dashboard attachment is installed by that demonstration.

The Windows UIA worker is intentionally **not registered**. Its stdin consent flag is not an authenticated grant and must not be exposed to models or a generic HTTP route. Native picker/indicator, broker lease and the B4 corpus precede promotion. [Exact status](WINDOWS_OBSERVATION_STATUS.md).
