# Phase completion — 2026-11-13

## Phase 0 — Audit

Already existed: P0 audit, consolidation ownership, repository matrix, idle
baseline, and Qwen advisory register.

This pass added the feature matrix in `IMMORTILITY_FULL_AUDIT.md` and the
candidate decisions in `OPEN_SOURCE_INTEGRATION_MATRIX.md`. No package was
installed. Hermes remains 0.21.1. OpenMausBot remains absent.

## Phase 1 — Task engine

Already existed and tested: SQLite task states, illegal transitions, sequenced
events, cancellation, idempotency, and restart without replaying side effects.

This pass added a regression that `created` cannot jump to `succeeded`, and
showed the existing content-free trace in chat when the user opens it.

## Phases 2 through 6 — not implemented

Multi-agent delegation, Mem0, MCP activation, a new scheduler, browser control,
computer use, and a 3D agent scene were not built. Each one would either invent
a second agent loop, draw agents that are not running, or enable a capability
the current security rules keep off. Qwen was not enabled and voice profiles
were not modified.

## How to see the trace

Start the app with `scripts/dev.ps1`. Send a consented message. Open
**Execution trace** on that turn. The states, duration, route, and
`tools disabled` come from `GET /v1/tasks/{id}/trace`.
