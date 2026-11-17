# Product build checkpoint — 2026-11-16

## Groq qualification gap — 2026-11-16 later session

No source, test, or route change. The 456 Python / 86 frontend results remain the latest code regression and were not re-run. Rust remains the earlier 13-test result. The consumed Groq model-list GET was not repeated. No inference was sent.

Public Groq pages read this session: model card, models catalog, rate limits, billing FAQs, billing plans, tool use, and deprecations. The model card lists `openai/gpt-oss-120b` at **$0.15 input and $0.60 output per million tokens**. The models catalog labels **250K TPM / 1K RPM** as Developer-plan limits. The rate-limits table lists **30 RPM / 1K RPD / 8K TPM / 200K TPD** and also says that table is a Developer-plan summary, while exact organization limits are on the account Limits page. Those public tables disagree and are not this account. The plans page names Free as $0 and Developer as pay per token. No documented Groq API field returns the organization plan or a $0 entitlement. Tool-use docs say this model supports local function calling, does not support parallel tool calls, and that one local tool round trip is two API calls. Groq-hosted browser search, code execution, and remote MCP stay out of scope.

Evidence: [GROQ_QUALIFICATION_GAP_2026-11-16.json](GROQ_QUALIFICATION_GAP_2026-11-16.json). The historical closure below is unchanged.

## Confirmed memory — later same day

No Groq console tab was open, so the Billing plan and `openai/gpt-oss-120b` limits were not observed. No model-list GET and no chat completion were sent. Phase B remains unauthorized.

The existing store now keeps user-confirmed facts beside task notes. A fact is saved only with an explicit confirmation flag, is rejected when it contains a configured secret, and is retrieved through the existing SQLite FTS index. Correction marks the previous row superseded. Revocation removes it from search. User facts are available in every project context; project facts require that project's scope id. Restart uses the same database file. Chat injection, when a non-public task runs, adds at most 400 characters labeled as data rather than instructions. Model answers are not written into this table.

Settings exposes save, find, and correct for a user preference. Native window acceptance was not run. Live model use of the retrieved text was not run.

## Direct routing preferences — same day

`decide_route` names one preferred model and admits none unless a test supplies eligibility. Production eligibility is empty, so Groq, Gemini, and NVIDIA stay blocked and no completion is sent. Deep and complex tool tasks name `nvidia/nemotron-3-ultra-550b-a55b`. Its public serverless price is $0.60 / $2.40 per million tokens. Fast tasks name `openai/gpt-oss-120b`. General reasoning names `gemini-3.8-flash` from the public Gemini price page; this account is not qualified. The Heretic local model remains uninstalled. Provider routing tests: 37 passed. The live Groq clock task is still not authorized.



## FINAL CLOSURE — authoritative latest result

**Primary Project Inspector slice CLOSED. Current full gate PASSED: 455 Python / 85 frontend / 13 Rust. Overall M3 release is NOT claimed.** HEAD **edafc64abca0e7340f46a4068dad4b2a33fdd6f2**, dirty tree and pre-existing changes preserved. No optional feature was started after the gate. No account access, inference, installs, models, system settings, live database migration or Git history/index mutation in this final session.

`./scripts/check.ps1`: **455 Python passed in 110.02 s; 85 frontend passed in 2.47 s**; contracts, lint/format (103 files), mypy (51 sources), TypeScript/ESLint/Prettier and production build (2.98 s) passed. Offline Rust **13 passed in 0.91 s** (compilation 29.56 s); offline native build passed (19.43 s). Focused UI/presenter/transport 22 passed; project/workspace/workflows 40 passed; fixture scope 2 passed. Configured-key isolation, whitespace and engineering script compilation passed. No grant/deadline or secret assertion was weakened.

Native Tauri acceptance used two real synthetic folders with no credentials: folder selection, view consent, actual search/read/hash receipt, protected-file refusal, persisted scope after restart, root switch and consent/result clearing, queued-task cancellation, replacement-root recovery, broker restart with consent clearing, and revocation. The transient disconnected header was not sampled; control-lock logic has deterministic coverage. Native cancellation paused the queue before I/O; actual scanner-thread cancellation is backend coverage. The initial tool-delay case expired at the unchanged five-second limit and is retained. All owned native/broker/preview processes were reaped.

User-visible fixes include cleared consent on folder changes, revocation independent of checked consent, exact receipt/root/path matching, protected error presentation, duplicate-action guards, idempotent explicit retry, live tool/task status, no-resubmission reconnect, bounded page navigation and truthful clipped line ranges. Legacy workspace-root changes now revoke project-read availability, and active tasks block workspace changes. Source handling remains read-only, root/digest bound, cancellation-aware and excluded from cloud recall.

The original full gate **454 passed / 1 failed, 111.41 s** is preserved in `final-check.log`. Its only failure was a stale provider-health message fixture from before the provider-neutral policy. Both Gemini and NVIDIA expectations were aligned to the current contract, retaining key non-disclosure and adding explicit readiness-false checks. Focused recheck passed; then the complete gate passed. EBUSY dependency access and an interrupted sandboxed invocation were environmental observations; no dependency/system changes were made.

Actual native receipt event deltas for four successful tiny reads: 28.009–33.369 ms (UTC event times, not a monotonic/UI-latency benchmark). No CPU/RAM/GPU or large-project soak claim. Existing source/output/deadline caps remain enforced.

Important session files: `ProjectInspector.tsx`, new `projectInspection.ts` (ephemeral UI presenter), new `ProjectInspector.test.tsx`, `transport.test.ts`, native `main.rs` route test, backend `project_inspection.py`, `app.py` workspace guard, `workspace.py` permission reset, `test_project_inspection.py`, `test_broker.py` stale fixture correction, `test_native_event_fixture.py`, `native_project_fixture.py` and the two existing debug-native harness scripts. `SettingsPanel.tsx`, `transport.ts` and direct-metadata files included pre-session changes and were preserved. The complete observed dirty inventory and SHA-256 hashes are in the fresh evidence and `M3_VERIFICATION.json`.

Evidence: `.cache/verification/project-inspector-final-verification-fdacc1cd-7be7-452d-b28e-3e4ba32cef58.json`; native `.cache/verification/project-inspector-native-close-1459f04a-9d4b-4751-a2fd-09512122b8a3.json`. Original status/verification, starting inventory, failed gate and passing gate are under `.cache/verification/project-close-91210ab3-624b-4fca-91d6-d02e5ca3ad06/`.

**Known remaining gates:** direct-provider free entitlement/quota and real tool-stream qualification; separately authorized real-model execution; warm MCP credential crossing (reuse OFF); large-project/idle performance. The earlier metadata authorization is consumed. Qwen remains uninstalled; DOCX publication stays disabled. No current Project Inspector regression is known after these checks, within the stated native acceptance limits.

**Single next slice:** qualify the direct Groq account/model's zero-cost eligibility and prepare one separately authorized public-only Hermes tool task, at most two model calls/8,000 tokens with no paid fallback, private uploads or automatic retry. No excluded-provider or warm-runtime work is part of that slice.

## Historical development record — preserved below

## Final-session recovery and closure in progress

Recovered HEAD **edafc64abca0e7340f46a4068dad4b2a33fdd6f2**, dirty tree preserved. Starting modified-file inventory and preceding verification are saved under `.cache/verification/project-close-91210ab3-624b-4fca-91d6-d02e5ca3ad06/`. No Git mutation was performed. Scope is limited to finishing Project Inspector; no optional feature, account request, live inference or warm-reuse experiment.

**Frontend fixes IMPLEMENTED / focused OFFLINE VERIFIED:** an ephemeral UI presenter now owns duplicate-click guards, consent invalidation, receipt matching and read-only task following; durable ownership remains in Engine/Store. Folder changes clear view consent/results, revocation is independent of checked consent, real task/tool events update progress, cancellation targets the correct task once, disconnect clears consent and rejects late events, reconnect reads existing task state without another POST. Explicit retry after an interrupted submission retains its idempotency key. Raw unexpected path/token errors are not displayed. **22 focused component/presenter/transport tests passed (0.920 s)** and TypeScript/ESLint/Prettier passed. One initial lint attempt encountered an EBUSY dependency-file lock; a later unmodified dependency read passed. Dedicated fixture type/lint issues were corrected without production-policy relaxation.

Backend edge-case verification, Rust/native integration and final complete regression are pending at this point. The older results below remain historical until superseded by a completed closure gate.

**Native acceptance completed before the final gate:** actual Tauri/WebView with a keyless scratch broker and two synthetic source folders. Observed folder selection, explicit view consent, search result `answer = 42`, file page with line range/SHA-256, visible `.env` refusal, saved scope restored after restart, root switch clearing consent/results, queued-project cancellation, subsequent `answer = 99` from the replacement root, broker restart/recovery with cleared consent, and revocation while consent was unchecked. The transient disconnected header was not sampled during the brief restart; disconnection locks are deterministic presenter coverage. Scanner-thread interruption is real backend coverage; native cancellation used an explicit queue pause before tool dispatch. A separate delayed-tool fixture reached the original five-second deadline and failed as expected; that record is preserved. No production deadline was increased. Native/broker/preview processes were reaped.

**Pre-gate checks:** 40 project/workspace/workflow tests passed (24.39 s); 2 native-fixture scope tests passed (1.79 s); 13 offline Rust tests passed (0.91 s; compilation 29.56 s); offline native build passed (19.43 s); frontend production build passed (3.32 s). Current Python lint/typing passed (51 sources), frontend focused tests 22 passed and static checks passed. Full regression starts next; feature scope is frozen and no optional feature will be started.

The latest user directive is preserved in `MAIN_PRODUCT_BUILD_DIRECTIVE_2026-11-16.md`. This slice transitions to usable local-first features while direct-provider release gates remain independent. No fresh audit, new framework, install, model, commit or push.

## Actual implementation and verification

- `project_inspection.py`: opt-in project-root identity, bounded literal source search and file-page reads. Uses existing Windows path/reparse/hardlink protections. Protected files, recognized secrets, configured keys, binary data and unsupported types are withheld. Every result carries file hashes and untrusted-data provenance.
- `app.py`: registers `project.search.v1` / `project.read.v1` in the existing gateway. Existing Engine/Store workflows execute them locally with explicit local read consent. Project permission alone admits only project reads, not unrelated workflow tools. Results stay excluded from cloud conversation recall. No shell, file mutation or AI inference.
- Project selection persists in the existing workspace settings. It does not enable approved writes; changing folders disables pre-existing edit authority. Directory identity is bound into arguments and checked during read/delivery. Cancellation stops the bounded scanner thread and revokes pending grants.
- Backend tests: **14 passed in 4.20 s**. Earlier combined project/workflow run: 25 passed, one new fixture asserted the wrong HTTP status for existing secret protection; corrected to require **403 / secret_egress_denied**, with no production relaxation. Ruff passed after formatting; mypy **50 sources passed** before the additional metadata module was added.
- `ProjectInspector.tsx`, Settings insertion and two fixed native operations are implemented. Existing `followTask` handles read-only replay/reconciliation without resubmission. TypeScript/lint/format passed; **68 existing frontend tests passed in 2.76 s**. Dedicated new UI tests, further interaction review, Rust/build and full regression remain pending. This is not a completed/native-verified product feature.

## Warm MCP investigation completed to a blocking result

Actual first-profile clock execution traversed canonical Hermes → reviewed MCP bridge → real broker gateway. The second profile's model credential/history were separate, but its MCP request still used the first profile's task credential. Safe categorization recorded `expected_profile=second`, `credential_profile=first`, `credential_matches_active=false`, `client_category=mcp-bridge`, HTTP **401**. The broker prevented the action. Production per-task Hermes is unchanged and reuse remains OFF.

Evidence: `.cache/verification/hermes-mcp-reuse-probe-7ebc02ee-567c-41ec-b6e7-7120309cc36a.json`. Cleanup passed. Cancellation/recovery phases in this warm probe were not reached. Failed/interrupted fixture iterations are retained; none is live-inference evidence. No installed Hermes files were modified. A future fix needs a verified upstream profile-aware MCP lifecycle, not a global client with retained task credentials.

## First direct-provider candidate

**Candidate for account qualification: Groq `openai/gpt-oss-120b`.** Official documentation lists tool use, JSON Schema mode, a 131,072-token context and 65,536 maximum completion tokens. These advertised capabilities do not qualify the combined Hermes streaming/tool path. Provider-reported speed is not an Immortility benchmark. [Official model documentation](https://console.groq.com/docs/model/openai/gpt-oss-120b).

Groq distinguishes Free and billable Developer tiers; account upgrade changes billing. Organization limits must be checked in the account and can be project-specific. The stored key and a public model page cannot establish those conditions. [Billing FAQs](https://console.groq.com/docs/billing-faqs), [rate limits](https://console.groq.com/docs/rate-limits).

`direct_metadata.py` / `check-direct-model.py` implement one bounded, fixed-host, read-only model-list request with no redirect, retry, model call or production activation. Eight deterministic tests passed in **0.80 s**, covering malformed/oversized/duplicate/unauthorized/redirect responses, missing credential/model, cancellation and non-disclosure of key/response canaries.

The user separately authorized one metadata GET and read-only inspection of already signed-in Billing/Limits pages. The **single GET completed** and returned the candidate listed/active with context **131,072**. Evidence `.cache/verification/groq-model-metadata-2cb3e864-4a90-4bda-96fb-317c6420886b.json`. Raw response/account identifiers and credentials were not printed or forwarded. Billing and quota remain unverified; **zero inference calls** and no retry.

Gemini remains an independent direct-provider candidate; do not block the first useful route on qualifying all providers. NVIDIA's public guidance distinguishes prototyping/evaluation from production entitlement, which needs separate review; a trial or developer key is not production proof. [NVIDIA FAQ](https://docs.api.nvidia.com/nim/docs/product). OpenRouter/OmniRoute remain excluded from forward work.

## UI-control blocker and next work

Computer Use stopped while attempting a new Chrome tab because it could not establish the current browser URL with sufficient confidence to enforce policy. The runtime instructed ending UI work for the turn. No alternate automation path was attempted. The new-tab outcome, account Billing/Limits and native project feature are unverified.

Resume with remaining project UI review, dedicated component/transport tests, current Rust/full regression and scratch-project native demonstration when available. Check folder revocation, duplicate clicks, disconnection, task-state/tool feedback and receipt scope matching. Keep legacy evidence and all dirty work intact. No live model test is authorized. Any future live request must identify a qualified direct route and remain public-only, at most two calls/8,000 tokens, no paid fallback, private uploads, publication or automatic retry.
