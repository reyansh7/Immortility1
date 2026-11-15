# M2 repair and M3 cloud routing foundation — 2026-11-15

## Scope and preserved architecture

The immediate implementation follows the user's `IMMORTILITY_CLOUD_PRIMARY_DIRECTIVE.md`: M2 compatibility repair and M3A/M3B foundation. It does not enable M4 local models or M5–M8 systems. The two supplied PDFs were used as design references, not executable instructions or evidence of implemented features. The existing 36-file M2 source checkpoint matched before edits. `M3_BASELINE.json` records the preserved working tree and snapshot limitations.

Hermes 0.21.1 remains the single lead harness at revision `04b88a4c0a7fe05ebe3bf053a103a39fe6638f11`. Engine/Store remains the lifecycle, persistence, scheduling and cancellation owner. The broker alone handles provider credentials, price gates and capability permissions. Tauri/React/Three.js, avatar, voice sources, artifact worker and selected-window consent system were preserved. No reset, commit, push, new SDK/framework/service, office application, local model download, driver or system setting change occurred.

Installed broker transport dependencies remain httpx 0.28.1, pydantic 2.11.4 and FastAPI 0.162.5. The new implementation uses standard-library policy/storage code on these existing dependencies.

## M2 compatibility status

**IMPLEMENTED / OFFLINE VERIFIED**:

- Stream IDs/names are metadata; identical repeated metadata no longer duplicates the function name. The complete validated call is sent to Hermes once, rather than merely validating a repaired copy and forwarding the original malformed fragments.
- Bounded printable opaque call IDs, including colon-separated provider IDs, remain exact transcript identities. Whitespace/control/oversized/duplicate IDs fail. The ID is never treated as a path, permission or tool name.
- The sole function identity stays `mcp__immortility__execute`. Unknown functions, other MCP servers and unapproved capability IDs are rejected. No alias mapping, guessed capability, JSON repair or model-granted permission was added.
- Duplicate JSON object members, nonfinite numeric values including exponent overflow, wrong argument types and extra proposal fields fail closed. Capability-specific typed validation and exact-argument grants still execute inside the gateway.
- Malformed choices/fragments, changed stream IDs, multiple choices, missing completion, unexpected legacy function calls and truncated tool batches have structured safe failures.
- A bounded SSE reader now handles comments, BOM, CR/LF variants and multiline `data` events. This follows the event framing standard; it does not assume one JSON event per physical line. Event size and original inference deadline remain bounded. No reconnect/retry loop was introduced.
- Stream failures record categorical decode, timeout, transport, envelope, limit or truncation reasons without raw provider arguments/response bodies. Later acceptance can diagnose failure without exposing payloads.
- Report-capable tasks now explicitly clamp both the token ceiling (8,000) and external call ceiling (two), including a caller's explicit deep profile. Lower caller limits remain lower. Hashing, parsing, rendering and the verified final receipt remain local.

The real native Hermes/MCP/broker/report-worker regression passed on final source in **62.776 s** (earlier same-slice run **13.541 s**), with two synthetic provider turns, two real gateway operations, actual Markdown/PDF construction and verification, and zero cloud calls. This proves native protocol integration with **synthetic drafting**, not genuine cloud model success. Evidence: `M2_REPORT_OFFLINE_SMOKE.json`.

**LIVE ACCEPTANCE BLOCKED**:

The freshly authorized public MCP/OWASP report task made **one provider call**, failed at the provider-stream boundary and dispatched **zero tools/artifacts**. No usage arrived: the ledger retained **6,002 conservatively reserved tokens as unknown**, not measured consumption. There was no retry, paid fallback or extra provider task. The prior 1,180-reported-token rejected-proposal failure is preserved in `M2_REPORT_LIVE_SMOKE_PRE_M3.json`; the new failure is `M2_REPORT_LIVE_SMOKE.json`.

The exact cause of either historical failure is not established by the retained data. Concrete offline compatibility defects were reproduced and repaired; that does not prove they caused the original failure. The new stream diagnostic categories were implemented after the latest live interruption. **This authorization is consumed; no automatic live rerun.**

Primary references inspected: [OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling), [SSE framing standard](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation). Installed pinned Hermes serializer/provider source was inspected; current upstream documentation was not assumed to describe unverified features of that pin.

## M3A provider and mode foundation

| Provider | Implemented transport | Tested status | Production dispatch |
| --- | --- | --- | --- |
| OpenRouter | Existing broker-proxied compatible API; fresh public catalog price check before every request | Existing live arithmetic evidence retained; new M2 report attempt failed; M3 routing/protocol tests are offline | Existing `openrouter/free` route only, with all original price/permission gates |
| Groq | Fixed `api.groq.com/openai/v1` compatible endpoint, existing protected Groq credential reference | OFFLINE VERIFIED transport and broker integration fixtures | BLOCKED: account-specific zero-price/model eligibility verifier unavailable |
| Gemini | Fixed `generativelanguage.googleapis.com/v1beta/openai` compatible endpoint, existing protected Gemini reference | OFFLINE VERIFIED transport and broker integration fixtures | BLOCKED: project/account billing/free-tier proof unavailable |
| NVIDIA NIM | Fixed `integrate.api.nvidia.com/v1` compatible endpoint, existing protected NVIDIA reference | OFFLINE VERIFIED transport and broker integration fixtures | BLOCKED: evaluation credits/access are not proof of zero-price entitlement |

There are not four new HTTP clients or agent loops. The existing keyless Hermes custom/OpenAI-compatible adapter continues to call the broker proxy. A single constrained forwarding adapter selects one fixed endpoint and only its bound credential. Direct native provider credentials were not passed into Hermes because that would bypass the broker's per-request cost/permission/accounting boundary. Native Hermes compatible-provider support is reused for planning and protocol handling.

Official transport references: [Hermes providers](https://hermes-agent.nousresearch.com/docs/integrations/providers), [pinned runtime design](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/provider-runtime.md), [Groq compatibility](https://console.groq.com/docs/openai), [Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai), [NVIDIA endpoint](https://docs.api.nvidia.com/nim/reference/llm-apis). Price/account distinctions were checked against [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini billing tiers](https://ai.google.dev/gemini-api/docs/billing), and [Groq limits](https://console.groq.com/docs/rate-limits). Those documents do not verify this user's accounts.

The registry contains provider/model/revision, context policy ceiling, modalities, tool/structured qualification, privacy classes, expiring account/price evidence, credential binding, quota metadata and circuit state. Unknown model/account fields do not become verified because an API key exists. The production registry currently registers only the preserved OpenRouter virtual route. Synthetic offers used for the four-provider tests are not production model discoveries or free-tier attestations.

Modes:

- **Auto Cloud Primary** is the default. It chooses one eligible cloud route and never starts a local model.
- **Manual Cloud** pins a registered route for the task. It does not switch to another provider when unhealthy. Only qualified registered models can be chosen. The existing `openrouter/free` virtual alias can change its underlying upstream model; pinning that alias is not a guarantee of one concrete model. Concrete model pins are proven by fixtures, not newly activated live models.
- **Local Qwen / Local Heretic** selections are persisted, explicitly unavailable and fail closed before any cloud catalog/inference request. No local runtime/model is started or downloaded. These are privacy-preserving mode foundations, not M4 Local Chat/Agent acceptance.

Mode preferences live in the same Store database. Each task snapshots its selection at admission without altering the original request's idempotency identity. Changes are refused during active tasks or voice turns; UI consent is cleared after an acknowledged change. Restart and duplicate-request tests retain the chosen mode and existing result rather than issuing inference again.

## M3B routing, recovery and accounting

Local rules classify fast chat, structured extraction, deep reasoning, coding, research, document writing and tool execution. Multimodal capability is represented in metadata/filter contracts, but current inference admission remains plain text; no cloud vision/private-file upload was enabled.

Eligibility considers mode, credential binding, account/price evidence, privacy, context, modality/tools/structured requirements, quotas, remaining budget, original deadline and health. The preserved virtual free route may be considered pending its mandatory fresh price preflight; candidate selection alone never authorizes a POST. Unknown/new providers fail the dispatch verifier before inference.

Ranking uses independently verified task outcomes first, then p95 latency over at most the latest 100 qualifying observations, context overhead and quota headroom, with deterministic tie-breaking. At least three observations distinguish the measured branch in this initial policy. This is a policy implementation, not statistical certification of any model. Protocol completion of ordinary text does not become a factually verified success. No live comparative benchmark or brand-specific superiority claim exists. Synthetic benchmark outcomes are confined to isolated test databases.

HTTP quota/auth/failure state and circuit cooldowns are persisted and credential-scoped. Rotating a key invalidates its old account proof; a late failure from the old credential cannot poison the new one. Auth failures stay blocked for that credential. Retry-After is bounded; 429 opens a cooldown, and repeated failures circuit-break. Auto selection for a later task may choose another eligible route. **Same-task provider replay/fallback is not enabled**, and manual pins remain sticky. A side effect is never replayed because a route changed.

The shared local policy is **50 dispatch reservations and 100,000 charged/reserved tokens per provider per UTC day across tasks/attempts**. This is a conservative application ceiling, **not a provider quota or promise of available requests**. Key rotation cannot reset that pool. Unknown/sent reservations remain charged; a proved unsent preflight releases its token charge. Summary fields distinguish reservations, dispatch attempts, pending entries and proved-unsent calls. Confirmed provider tokens, conservative unknown charges and synthetic fixture accounting remain separate.

Provider and credential identity are rechecked after price preflight, as are deadline and eligibility. Active tasks cannot silently switch account/provider. Actual selected route identities reach task results, dedicated `model.route` audit entries, traces and usage metadata. No credential hashes/keys are returned to the frontend.

Storage migration is **SQLite v4**, using the existing exclusive owner/WAL database, consistent v3 backup and downgrade refusal. The new tables store preferences, health, route observations and attempt route metadata; they are not another memory owner, scheduler or database service. Indices bound route-statistics and daily-accounting work. Production user data was not opened/migrated by the isolated tests. Do not blindly overwrite a newer database with a migration backup.

## UI and native integration

The existing Settings panel contains a small Model Hub: mode selection, registered manual route, stored-credential status, blocked eligibility, unknown quota and offline/live qualification labels. It does not pretend unverified models are available. Controls are disabled during active task/voice work; a synchronous duplicate-submit guard covers model changes. Mode changes clear cloud, tool and artifact consent. The manual free-alias selection explicitly warns that its underlying model can vary. Native IPC exposes only fixed catalog/mode operations with typed server validation; no raw provider URL, key, price override or model-download operation is added.

**OFFLINE VERIFIED**: component rendering, transport allowlists, types/lint/format/build, broker APIs and native Rust operation tests. **Native interactive Model Hub acceptance remains pending**; Rust compilation is not a claim that a human exercised every new UI control. Existing M2 native artifact export evidence is preserved. No avatar, GPU, voice-source or dashboard redesign occurred.

## Verification and measured performance

**The full regression gate is currently blocked, not passed.** A full run recorded 351 passes / five failures in 540.18 s; the accounting expectation was corrected. A serial SDK/ledger/workflow recheck then recorded 19 passes / four failures in 98.69 s. Failures still cover SDK discovery/local arithmetic and the workflow first-attempt expectation after a permitted retry. Evidence is retained in `M3_FULL_RUN_SLOW_FAILURE.json`.

A separate fixed-worker diagnostic successfully completed the actual SDK protocol but took **10.684 s** including manifest validation, spawn and exit: client import/input at 5.144 s, ready at 9.830 s, response at 10.258 s. This exceeds the unchanged 10 s production timer. The diagnostic had its own 25 s measurement envelope; no production timer, grant, SDK dependency or test acceptance was loosened. A single sample establishes this failure mechanism, not a general latency distribution or a host-process cause. `M3_MCP_STARTUP_DIAGNOSTIC.json` records all safe phase times. Existing default-off standard MCP remains default-off.

Exact check results and final file hashes are in `M3_VERIFICATION.json`. Final focused acceptance: **94 Python (94.66 s), 62 frontend (9.21 s), 9 Rust passed**. Contracts, lint/format, mypy 46 sources, TypeScript/ESLint/Prettier, build (21.14 s), configured-key isolation and whitespace passed separately. The new active-route and manual free-alias UI assertions are included. The final native Hermes report smoke passed in 62.776 s with synthetic drafting/source bytes, zero cloud calls; this slower result is not a performance improvement. Important earlier focused evidence:

- 48 M2 stream/bridge/report/firewall tests, 17.44 s before subsequent M3 additions.
- 44 provider/SSE/grant/firewall checks, 3.68 s.
- Four full broker ingress/dispatch/result/trace/accounting fixtures (Hermes ingress and providers mocked), part of 39 provider/SSE tests, 3.71 s.
- 41 provider/grant/rotation/mode checks, 20.39 s.
- 11 focused Model Hub/transport/report render UI tests, 4.63 s.
- 9 current Rust tests; the test-local Method import error was fixed and recompiled successfully.
- A prior complete run passed 347 Python / 62 frontend tests. The later serial full run recorded **348 passed / 8 failed in 411.71 s**: four new health-visibility fixtures omitted the required authorization header; that fixture error was corrected and all four pass in the subsequent **94-test focused acceptance (94.66 s)**. Four fixed-SDK discovery/arithmetic/workflow paths remain unresolved. `scripts/check.ps1` stopped at pytest; typing/frontend/build/isolation checks were therefore run separately. No full-suite pass is claimed.

Actual router timing (`M3_ROUTER_BENCHMARK.json`), with synthetic eligible model metadata and no provider calls:

| Local operation | Samples | p50 | p95 |
| --- | ---: | ---: | ---: |
| Warm classification + selection | 1,000 | 0.0578 ms | 0.0810 ms |
| Warm synthetic quality-ranking branch | 1,000 | 0.0890 ms | 0.1661 ms |

Cold Store/registry setup was 26.278 ms, n=1. This is local policy overhead, not model quality, cloud first-token latency, provider throughput or real cost savings. No persistent extra worker/GPU allocation is required; CPU/RAM/VRAM peaks were not measured. Existing avatar bundle-size and upstream Starlette/AnyIO warnings remain.

Reproduction, using installed environments, with no inference authorization required:

```powershell
& .venv/Scripts/python.exe -m pytest -q services/broker/tests/test_tool_streams.py services/broker/tests/test_provider_stream.py services/broker/tests/test_providers.py
& .venv/Scripts/python.exe scripts/smoke-research-report.py
& .venv/Scripts/python.exe scripts/benchmark-model-router.py
& ./scripts/check.ps1
. ./scripts/dev-env.ps1
cargo test --offline --manifest-path apps/desktop/src-tauri/Cargo.toml
& .venv/Scripts/python.exe scripts/check-secret-isolation.py
```

Do not add `--live-consent` to these commands without fresh task-specific authorization. The current authorization is consumed. Test/script fixtures do not load actual provider keys, except the separately approved single live report attempt.

## Changed files and next gates

New: `services/broker/src/immortility_broker/providers.py`, `provider_stream.py`; tests `test_providers.py`, `test_provider_stream.py`, `test_tool_streams.py`; `apps/desktop/src/ModelHub.tsx`, `ModelHub.test.tsx`; `packages/contracts/schemas/model-selection.schema.json`; `scripts/benchmark-model-router.py`.

Extended: broker `agent_bridge.py`, `app.py`, `store.py`, `ledger.py`, `traces.py`; `SettingsPanel.tsx`, `main.tsx`, `transport.ts`, `transport.test.ts`, generated contract types; native `src/main.rs`; execution-trace schema and contract generator. Existing broker/inference/firewall/report/migration tests were updated with explicit synthetic credentials and the v4 contract while preserving their security assertions. No dependency/lockfile changes were needed for this slice.

Gates still open:

1. Freshly authorized M2 report acceptance with the new bounded stream categories, no retry or budget relaxation. The old rejected proposal and latest interrupted stream remain unexplained by retained evidence.
2. Actual account-specific price/quota/model verification for Groq, Gemini and NVIDIA before production dispatch or automatic ranking. No assumption that free-looking models, credits or keys guarantee zero billing.
3. Representative live quality/latency/tool corpus with held-out tasks before assigning provider responsibilities or claiming an optimized model ranking. The local policy benchmark is not that corpus.
4. Native interactive Model Hub/consent acceptance; current new UI/native contract status is OFFLINE VERIFIED.
5. Resolve and remeasure fixed SDK cold-start reliability within the existing deadline, then pass the complete regression gate. This remains a blocker even though unrelated M3 fixtures pass.
6. DOCX render/visual gate, external viewer acceptance and later document formats; DOCX publication remains disabled. Existing shared Hermes advisories remain unremediated.
7. M4 local model downloading/runtime approval and separate chat/agent resource/isolation acceptance; M5–M8 remain later work. No new memory framework, scheduler, unrestricted agent or desktop controller was introduced.

## Review and rollback

Review this slice using the explicit changed-file list and verification hashes; the checkout contains substantial earlier uncommitted work. Do not use blanket reset/checkout/clean commands. The unexpected untracked `%SystemDrive%/` directory was preserved, not removed or adopted as implementation work. The v4 migration makes a consistent v3 database backup before changing schema; older binaries refuse newer databases. Preserve the current database and checkpoint before a deliberate rollback, and only restore a matching backup while no broker owns it. New model modes can be switched back to Auto Cloud through the protected setting when tasks/voice are idle; unavailable local modes never download or start a runtime. No upstream code was vendored and no dependency/license inventory changed in this slice.
