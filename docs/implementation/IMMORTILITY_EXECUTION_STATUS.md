# Engineering checkpoint — 14 November 2026

Implementation is in progress. This is **not a production-ready release or an M0/M1 exit-gate approval**. No later milestone is represented as completed by a directory, manifest, mock, or package installation.

Authoritative directive: [master prompt](IMMORTILITY_BOSS_LEVEL_CODEX_MASTER_PROMPT.md). Before-state: [snapshot](M0_BASELINE.json). Exact source changes and hashes: [change register](M0_CHANGED_FILES.json). Commands, failures and acceptance limits: [acceptance record](E2E_ACCEPTANCE.md).

## M0 repairs

| Finding | Implemented behavior | Verification and remaining gate |
|---|---|---|
| A1 filesystem | Case/Unicode/device/UNC/ADS/8.3 aliases rejected; links/reparse/hardlinks denied; Windows ancestor handles held during read/write; bounded enumeration prunes private/runtime directories | Native Windows scratch fixtures pass. This is a scoped file adapter, not an OS sandbox or universal secret classifier. Same-user hostile concurrent mutation is not a supported isolation boundary. |
| A2 lifecycle | Shared owned process jobs; bounded reap; cancellation-safe spawn; suspended Windows startup before job assignment/resume; no taskkill helper in repaired worker paths | Real subprocess, queued request, timeout, spawn-cancel, descendant and 100 worker-ready Stop tests. Native GPU/microphone soak remains unverified. |
| A3 forget | Durable recall exclusion covers FTS, history injected into prompts, prior-task notes and late remember; forgetting cancels captured active context | Restart and foreign-session fixtures pass. History/evidence remain visible. This is search exclusion, not physical erasure; WAL/backups retain data. |
| A4 standard MCP | Official SDK stdio client and server, independent stdlib NDJSON peer, isolated SDK 2.2.0, fixed scripts/hashes, no model-selected executable | EXPERIMENTAL, default off. Interop and local broker calculation have passed; the inner initialization timeout was diagnosed and corrected; paired cold startup passes 10/10. Complete hostile-server/HTTP/OAuth B1 remains open. Legacy Content-Length demo remains explicitly separate. |
| A5 usage | Durable SQLite per-attempt/call reservations; task aggregate across attempts; atomic call/token caps; unknown usage conservatively charged; overrun blocks further calls; grant key rotated | Concurrent reservation, restart, refund, invalid usage, cross-task preflight and transport fixtures pass. No live provider usage validation or complete child/DAG attribution yet. |
| A6 approval | Digest binds task/session/attempt/root/content/hash/existence; live expiry; disable/Stop revokes; apply/review owned by task; journal precedes write | Tamper, expiry, disable/re-enable, restart, review failure, Stop during review and rollback fixtures. New-file rollback removes the created file. |
| A7 bytes | CRLF-preserving reads/hashes, bounded bytes, unique exclusively created temp, fsync and atomic replace, post-write readback | Scratch round trip and stale/existence conflict fixtures. No claim of atomic compare-and-swap against arbitrary hostile same-user writers. |
| A8 Wikipedia | Async bounded JSON fetch; validated public IP connection with original TLS hostname; compression/redirect/type/byte controls; source reaches actual runtime prompt even without delegation | Transport fixtures, DNS/mixed-address denial, exact prompt and cancellation tests. General search, HTML extraction and dynamic browser are not implemented by this repair. |
| A9 privacy | Native Windows credential entry replaces React password state; fixed IPC route cannot save a webview-supplied key; actual ASGI body bytes bounded; arbitrary Hermes error text suppressed; known-key/recognizable-secret egress guard | Rust compiles/tests; synthetic canaries and source/bundle key scan. Unique dummy native vault roundtrip passes; credential-dialog interaction/cancel remains manual. Not a universal DLP guarantee. |
| A10 checks | Formatter failures repaired without a UI redesign; Qwen production flag hard-disabled; existing profiles/voice experiments retained | See latest check evidence. An earlier 185-Python/41-frontend green run does not erase later MCP failure diagnostics. |

## Milestones and owners

| Milestone | Status | Owner / next bounded action |
|---|---|---|
| M0 | INTEGRATED; exit gate pending | Broker/native supervisor. Finish native credential acceptance, independent filesystem race review, cold startup/Stop soak and Hermes advisory reachability/remediation comparison. |
| M1 arithmetic gateway | EXPERIMENTAL, default off | Broker owns typed grants, single controller lock, deadline, cancellation and schema validation. Two registered adapters: arithmetic and clock; cold probe passes 10/10. Complete B1 before external servers. |
| M1 general connectors | NOT STARTED | Streamable HTTP/OAuth/resource/prompt/session recovery/hostile-server memory bounds/Inspector acceptance are required before enabling external servers. |
| M2 grounded multi-source web/browser | BLOCKED by M0/M1 acceptance | Wikipedia repair is integrated. Next: safe public fixture corpus and static extraction; no unrestricted fetch or browser enabled. |
| M3 Windows/coding | EXPERIMENTAL read-only worker | Approved patches retained; code execution hard-disabled. Synthetic read-only UIA worker verified but not registered; no Windows input controller or Serena. |
| M4 memory/self-learning | NOT STARTED beyond A3 | Establish labelled retrieval/correction/retention corpus before embeddings or a new memory service. |
| M5 delegation/scheduling | VERIFIED local read workflow foundation; model/scheduling expansion pending | Existing Engine owns optional durable read-only DAG and explicit headless mode; no new scheduler, OMB runtime or background agent framework. |
| M6 artifacts/connectors | NOT STARTED | No claim of real DOCX/PPTX/XLSX/PDF creation. Editable/rendered acceptance and scoped account consent are prerequisites. |
| M7 voice/local models | NOT STARTED beyond lifecycle repair | Preserve reference/INFERNAL/Piper settings and assets. No model download or new GPU fleet. |
| M8 production hardening | NOT STARTED beyond additive DB backup/version gate | Packaging, signed release, complete supply-chain/reachability work, resource/soak and E2E gallery remain. |

## Reconciliation and risks

- Original audit: 123 Python passes and three lifecycle failures. Actual initial engineering baseline: **127 passes**, with those failures not reproduced. The regression repair is supported by additional native lifecycle tests, not that historical count.
- Actual Hermes stays **0.21.1**, revision `04b88a4c0a7fe05ebe3bf053a103a39fe6638f11`. No upstream checkout or environment was upgraded. Its isolated tool inventory remains empty.
- The shared Hermes environment scan found **103 advisory entries in 15 packages**, including MCP 2.0.0. The new MCP slice therefore uses a separate 29-package, hash-locked SDK **2.2.0** environment. Its pre-install and installed scans have zero known entries. This does not clear Hermes, model weights, native binaries or unpublished vulnerabilities.
- New SQLite schema version **3** refuses future-version downgrade. Upgrading v1/v2 makes a consistent SQLite backup before changing schema; backups contain private history and need retention management.
- No live inference, private document upload, account connection, purchase, send, deploy, git push, model download or OS security-policy change was performed. No commits or blanket Git reset/stage operations were made in this dirty checkout.
- The Tauri/React/Three dashboard and avatar were preserved; UI edits are restricted to credential entry and a fixed read-only usage route.

No approval is requested to conceal incomplete work. Later privileged capabilities remain disabled because their acceptance gates have not been satisfied.


## Validated checkpoint update

The current isolated full run passed **190 Python tests in 44.57 s, 41 frontend tests, all contracts/lint/format/types and the frontend build**. The targeted native lifecycle/MCP run passed 19 tests; final 100 worker-ready Stop cycles measured p50 1.40 ms/p95 1.89 ms. Paired cold MCP startup passed 10/10 within the unchanged 10 s operation deadline after aligning the SDK inner initialization timer to 8 s; the former 3 s timer included a second cold Python/SDK import. Suspended-start ownership hardening addresses a separate launcher race. Earlier failed runs remain historical evidence. See [source-hashed verification](M0_FINAL_VERIFICATION.json).

Current continuation: two-adapter registry and durable broker-owned local read-only queue are verified. UIA is a scratch-only experiment. Trusted native source permission, headless/dashboard attachment, virtual overlay, real artifacts and release acceptance remain. See CURRENT_STATUS.md and CONTINUATION_STATUS.md.


## Current continuation verification

Latest full `scripts/check.ps1`: **219 Python in55.26 s /41 frontend in2.03 s**, lint/format/types/contracts/build pass, mypy38 sources. Configured-key isolation scan passes. Unchanged Rust was previously5 passed. See [source hashes](M1_NATIVE_OBSERVER_VERIFICATION.json).

Actual headless broker smoke: EOF survival, owned crash, checkpoint/restart, no replay, original expiry and zero-cloud ledger;5.695 s. Registry tests cover exact arguments, scope, expiry, disabled policy, redaction and real clock/SDK routes. Native process tests additionally prove allocation refusal under an optional job commit limit.

UIA normal/wide native fixture smokes pass: code text, protected-field canary,13 denials and64-node truncation. This is not a registered product tool or completed B4 corpus. [Details](WINDOWS_OBSERVATION_STATUS.md). First tests exposed Windows output encoding, missing TextPattern and an invalid peak-counter assumption; all were corrected and rerun. No user window observed, input performed or screenshot uploaded.
