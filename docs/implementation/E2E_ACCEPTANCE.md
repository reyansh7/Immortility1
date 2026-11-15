# Executed acceptance and open gates

Use repository root in PowerShell. `. ./scripts/dev-env.ps1` selects the existing repo Rust/Visual Studio toolchain. No model/account credentials are needed for the following tests.

## Executed evidence

| Command | Observed result |
|---|---|
| Initial `.venv/Scripts/python.exe -m pytest -q` | 127 passed, 22.15 s, before repairs; historical 3 lifecycle failures not reproduced |
| `./scripts/check.ps1` during implementation | A complete run passed 185 Python, 41 frontend, lint/format/types/contracts and Vite build. Later edits require the final rerun below; isolated MCP initialization failures were also reproduced and remain recorded. |
| `cargo test --offline --locked --manifest-path apps/desktop/src-tauri/Cargo.toml` | 5 passed; native credential code compiles; webview `save_provider_key` operation denied; identifier escape denied |
| `python docs/research/ecosystem_audit_probes.py --expect-fixed` using `.venv` | Upper/lower credentials names denied; CRLF applies; FTS/history/prior-task recall excluded after Forget |
| `python scripts/smoke-hermes.py --offline` using `.venv` | Real pinned Hermes; fake provider only; succeeded; one guarded completion |
| Same `--offline --adversarial` | Blocked unsafe tool response before Hermes; zero streamed chunks |
| Same `--offline --cancel` | Cancelled; Hermes process reaped; no completion request |
| `pytest test_usage_ledger.py test_public_io.py` | 20 passed; concurrent reservations, unknowns, bounded bytes/compression/redirects/DNS/chunked-body canary |
| `pytest test_inference_grants.py test_approval_ownership.py` | 13 passed at that checkpoint; stale preflight cannot poison next task; secret-like source content blocked; Stop during post-write review leaves rollback |
| `pytest test_process_owner.py test_tts_lifecycle.py -s` | 12 passed before suspended-start refinement; native descendants and spawn cancellation; n=100 worker-ready Stop cycles |
| `python scripts/check-secret-isolation.py` | Configured keys absent from frontend source/bundle/docs/config; values never printed |
| `pip-audit --path .venv-mcp/Lib/site-packages` | 29 packages, no known advisories; [report](MCP_ISOLATED_RUNTIME_AUDIT.json) |
| Shared Hermes environment `pip-audit --path .../venv/Lib/site-packages` | **103 advisory entries / 15 packages**, including old MCP; [report](MCP_SHARED_RUNTIME_AUDIT.json). Not cleared by the isolated MCP environment. |

Exact latest aggregate results will be recorded in `M0_FINAL_VERIFICATION.json`. A prior passing run is not a substitute for the current source checks.

## Regression fixtures added

`test_m0_repairs.py`: alias/case/Unicode/device/UNC/ADS/path traversal, hardlinks, CRLF, unrelated old temp preservation, persistent Forget, SQLite v1 backup/v2 downgrade protection, missing vs empty-file conflict.

`test_approval_ownership.py`: disable/re-enable, expiry, payload tampering, restart revocation, failed review recovery, newly created-file removal on rollback, actual research prompt/URL with delegation off, async fetch cancellation, Stop during post-write review.

`test_usage_ledger.py` / `test_inference_grants.py`: contention across attempts, unknown/restart, single settlement/refund, cache/reasoning fields, invalid reports/overrun, scoped grants, stale preflight, transport unknowns, no content in usage endpoint, configured-key/recognizable-secret denial.

`test_standard_mcp.py`: real official SDK/server; independent stdlib NDJSON peer; fixed inventory; disabled/forbidden dispatch, scope/single use/revoke; real broker arithmetic with no Hermes/cloud. This is **not complete B1 acceptance** for hostile third-party servers.

## Failures preserved and gates still open

1. Initial full check failed an old frontend test expecting webview key submission; the assertion was deliberately changed to require denial after native credential entry replaced that path. No key-saving assertion was weakened into permissive behavior.
2. Original SDK 2.0.0 reused from Hermes was rejected after advisory scan. Separate official SDK 2.2.0 environment was installed from hashed wheels; Hermes was not modified.
3. SDK initialization intermittently failed, including under paired cold starts. Lifecycle phase diagnostics contain fixed phase names only. Root cause was the inner 3 s initialization timer including a second cold Python/SDK import. It is now 8 s inside the unchanged 10 s overall deadline; paired cold probe passes 10/10. Complete B1 remains open; earlier failures are retained.
4. Initial FAST real-Hermes smoke failed before sending inference due to mandatory startup context. Supported prompt hints and removal of irrelevant renderer-owned shell context restored the tool-free real protocol smoke without changing the 4,000-token cap.
5. Unique dummy native vault roundtrip passes; interactive credential entry/cancel is not yet demonstrated. Rust unit/compile results alone do not prove the desktop interaction.
6. No live free-provider quality/usage run, real microphone/STT/TTS/GPU soak, UI screenshot comparison, general web/browser/Windows input, scheduling, real artifact rendering/editability or authorized external connector action has been accepted here.

## Required next acceptance

Finish M0/B0 with audited Hermes dependency reachability and an isolated upgrade comparison (never in-place first), native credential-canary acceptance and parent/descendant Stop soak. Finish B1 with independent protocol errors/cancel/hung/noise/oversize/concurrency and Streamable HTTP policies before registering any external server. Complete B12 live usage/child accounting before enabling native delegation with effects. Keep every later privileged capability disabled meanwhile.


## Validated checkpoint update

The current isolated full run passed **190 Python tests in 44.57 s, 41 frontend tests, all contracts/lint/format/types and the frontend build**. The targeted native lifecycle/MCP run passed 19 tests; final 100 worker-ready Stop cycles measured p50 1.40 ms/p95 1.89 ms. Paired cold MCP startup passed 10/10 within the unchanged 10 s operation deadline after aligning the SDK inner initialization timer to 8 s; the former 3 s timer included a second cold Python/SDK import. Suspended-start ownership hardening addresses a separate launcher race. Earlier failed runs remain historical evidence. See [source-hashed verification](M0_FINAL_VERIFICATION.json).

Registry and durable local read queue are now verified; UIA scratch-only worker has its own evidence. Trusted source selection, normal dashboard/headless attachment, virtual pointing and artifacts remain unaccepted. Current results follow; historical checkpoints above remain valid for their recorded source.


## Current continuation verification

Latest full `scripts/check.ps1`: **219 Python in55.26 s /41 frontend in2.03 s**, lint/format/types/contracts/build pass, mypy38 sources. Configured-key isolation scan passes. Unchanged Rust was previously5 passed. See [source hashes](M1_NATIVE_OBSERVER_VERIFICATION.json).

Actual headless broker smoke: EOF survival, owned crash, checkpoint/restart, no replay, original expiry and zero-cloud ledger;5.695 s. Registry tests cover exact arguments, scope, expiry, disabled policy, redaction and real clock/SDK routes. Native process tests additionally prove allocation refusal under an optional job commit limit.

UIA normal/wide native fixture smokes pass: code text, protected-field canary,13 denials and64-node truncation. This is not a registered product tool or completed B4 corpus. [Details](WINDOWS_OBSERVATION_STATUS.md). First tests exposed Windows output encoding, missing TextPattern and an invalid peak-counter assumption; all were corrected and rerun. No user window observed, input performed or screenshot uploaded.
