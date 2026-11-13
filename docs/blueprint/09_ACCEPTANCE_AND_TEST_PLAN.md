# 09 — Testing, validation and objective definition of done

## Automated layers
1. Static: `ruff`, `pyright`/`mypy`, `eslint`, `tsc --noEmit`, `cargo clippy`.
2. Unit: model policy decisions, path traversal rejection, task transitions, event sequence monotonicity, approval digest verification, quotas and retries.
3. Contract: JSON Schemas validate Python output and TS client fixtures, backwards compatibility tests.
4. Integration: mock Hermes gateway, provider 429/failure, local SQLite migrations, Cursor output parser, fake browser/document/media workers.
5. Security: prompt injection and untrusted PDF test corpus, forbidden filesystem path, URL SSRF, secret redaction, CORS/origin, approval replay, unauthenticated requests.
6. End-to-end Windows: Tauri launch, tray, overlay drag and restore, real Hermes chat smoke (opt-in), stop, restart, DPI/dual monitor.
7. Reliability: worker kill, reconnect after crash, long-running job cancellation, backpressure, 429, disk full, microphone unavailable.
8. Performance: idle 10-min soak, GPU idle/active, visual animation FPS, memory leaks, task latency budgets.
9. Artifact quality: DOCX opens; PPTX editable and rendered; PDF page count/layout; XLSX formulas preserved; generated MP4 probed by ffprobe.

## Each phase exit report must include
- changed files and why;
- exact run/test commands and machine details;
- tests passed/failed;
- visual evidence (optional, no secret data);
- what is real vs mocked vs disabled;
- reproducible known issues and next steps.

## P0 test minimum
- Blank install diagnostic handles missing tools without crash.
- `.env` ignored; sample config checked in.
- Unknown price and paid model forbidden; free-route 429 does not invoke paid fallback.
- All schema JSON files parse and validate fixture events/tasks.
- Broker only binds loopback and rejects unauthorized origins.
- Hermes in Phase 1 must not have direct host file-writing, terminal, browser automation, computer control or plugin-install capability, even if prompted adversarially.

## P1 test minimum
- User can launch orb; drag, collapse, expand, and close.
- With key/provider configured and Hermes running, real question returns streamed answer and provider label.
- Without Hermes or keys, honest disconnected / setup UI, no fake success.
- Simulated 429 and network drop show recovery/blocked status.
- Stop cancels active request where supported; task shows actual terminal status.
- No OS, screen, microphone or file modifications before explicit feature enablement.
- Windows multi-monitor, 125%/150% DPI manual smoke.

## P8 release gate
No critical permission bypass; documented install/uninstall/update and data retention; 24-hour idle soak; crash/restart correctness; security scans; acceptable performance budgets; independent Windows-user install test.
