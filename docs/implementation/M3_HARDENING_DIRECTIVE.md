# IMMORTILITY — M3 HARDENING, RECOVERY & PRODUCTION READINESS

## Engineering Directive — Continue the Existing Implementation

You are the principal AI systems engineer, Windows systems architect, agentic-AI infrastructure engineer and performance specialist continuing development of **IMMORTILITY**.

This directive follows the completed M2 compatibility and M3A/M3B implementation slice.

**Do not start over. Do not rebuild Hermes, the broker, the model router or the dashboard.**

Your immediate objective is to convert the currently offline-verified M3 foundation into a reliable, performant, securely validated system.

The priority is:

**Repair the remaining regressions → establish repeatable performance → verify native UI → complete provider eligibility integration → prepare bounded live acceptance.**

Do not prematurely implement M4–M8.

---

## 1. Mandatory checkpoint recovery

Read the existing project instructions and current evidence:

- `AGENTS.md`
- `README.md`
- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/M3_CLOUD_ROUTING_CHECKPOINT.md`
- `docs/implementation/M3_VERIFICATION.json`
- `docs/implementation/M3_FULL_RUN_SLOW_FAILURE.json`
- `docs/implementation/M3_MCP_STARTUP_DIAGNOSTIC.json`
- `docs/implementation/M3_ROUTER_BENCHMARK.json`
- `docs/implementation/M2_REPORT_LIVE_SMOKE.json`
- `docs/implementation/M2_REPORT_OFFLINE_SMOKE.json`
- `docs/implementation/IMMORTILITY_CLOUD_PRIMARY_DIRECTIVE.md`

If a document has a different location, find its actual repository path before proceeding.

Inspect the working tree and preserve every unrelated or pre-existing change.

The latest recorded status is:

| Area | Verified checkpoint |
|---|---|
| M2 stream compatibility | Implemented and offline verified |
| M3 provider registry/router | Implemented and offline verified |
| Focused Python tests | 94 passed |
| Frontend tests | 62 passed |
| Rust tests | 9 passed |
| Latest whole-suite result | 348 passed, 8 failed |
| SDK regression | Four unresolved paths |
| SDK diagnostic | 10.684 seconds against 10-second deadline |
| Warm router p95 | 0.081 ms, synthetic |
| Native research/report smoke | 62.776 seconds, synthetic drafting |
| Real-model research/report | Failed at provider-stream boundary |
| Groq/Gemini/NVIDIA production dispatch | Disabled |
| Native Model Hub | Not interactively verified |
| Local models | Not installed or activated |

Four previously failing authentication test fixtures were corrected and passed focused rechecks.

**A complete clean regression run has not yet passed.**

Do not confuse focused acceptance with release acceptance.

The existing Hermes version, Engine/Store ownership, broker security boundary, Tauri dashboard, avatar and voice implementation must remain intact.

No Git reset, blanket checkout, clean, commit or push.

---

# 2. PRIORITY ZERO — FIX THE FOUR REMAINING SDK FAILURES

The full regression suite is currently blocked.

This is the highest-priority issue.

Investigate these unresolved areas individually:

1. Fixed-SDK discovery and startup.
2. Local SDK arithmetic execution.
3. Workflow execution behavior.
4. First-attempt/retry timing and result expectations.

Do not assume all four failures have one root cause.

## Required investigation

Instrument the existing local MCP/SDK initialization path with bounded, non-sensitive timing diagnostics.

Measure independently:

- Python import time
- Dependency initialization
- Manifest validation
- Process spawning
- SDK client construction
- MCP handshake
- Server readiness
- Capability discovery
- First tool invocation
- Result delivery
- Worker cleanup

Use monotonic timing and separate cold-start from warmed execution.

The previous diagnostic reported:

- Client import/input: 5.144 seconds
- Ready: 9.830 seconds
- Response: 10.258 seconds
- Total including exit: 10.684 seconds

The original production deadline is 10 seconds.

Investigate whether unnecessary work occurs on the critical execution path.

Potential optimization candidates include:

- Repeated imports
- Redundant manifest validation
- Repeated SDK initialization
- Unnecessary process spawning
- Duplicate discovery requests
- Blocking initialization
- Redundant startup serialization
- Excessive synchronous filesystem operations
- Avoidable protocol round trips

These are hypotheses, not established causes.

## Optimization requirements

Prefer fixing unnecessary work over increasing timeouts.

Evaluate whether validated metadata can be cached safely using hash-bound, version-bound evidence.

If an existing worker can be safely reused, benchmark that option, including memory cost, cancellation, process ownership, credential isolation and lifecycle effects.

Do not introduce a persistent worker merely to make one test faster.

Do not bypass security validation, disable SDK discovery or remove required startup checks.

Do not silently increase the 10-second production deadline.

If the deadline genuinely cannot be met with the existing dependency stack, document the measured limitation and present the narrowest alternatives without automatically changing policy.

## Acceptance

Require:

- All previously failing SDK tests pass.
- No relaxation of security checks.
- Normal workflow/retry semantics remain correct.
- Original deadlines and cancellation behavior are preserved.
- A complete regression run passes.
- Cold and warm startup measurements are recorded over multiple samples.

Do not claim a release-ready result based on one favorable timing sample.

---

# 3. PRIORITY ONE — INVESTIGATE THE END-TO-END LATENCY REGRESSION

The latest Hermes research/report smoke took **62.776 seconds**.

An earlier run in the same implementation slice took **13.541 seconds**.

This difference requires investigation, but is not yet proof of a repeatable regression.

## Required measurements

Break total time into:

1. Broker initialization
2. Hermes runtime initialization
3. Provider fixture initialization
4. MCP startup/discovery
5. Tool planning and dispatch
6. Gateway execution
7. Synthetic provider response generation
8. Report construction
9. PDF rendering and readback
10. Completion verification
11. Process cleanup

Run a controlled cold/warm benchmark series.

Record at least:

- Sample count
- Individual phase durations
- End-to-end p50/p95 where sample size supports them
- CPU usage
- Peak RAM
- Child process count
- Cleanup duration
- Repeated initialization
- Cache behavior

Distinguish operating-system scheduling contention from code-level work where possible.

Do not terminate unrelated host processes or alter global antivirus, security or operating-system configuration.

## Performance objective

Restore predictable, efficient execution without weakening correctness.

Investigate opportunities such as:

- Lazy initialization
- Avoiding repeated heavy imports
- Eliminating unnecessary subprocess startup
- Reusing safe verified metadata
- Faster bounded local document operations
- Avoiding duplicate schema serialization
- Efficient cancellation
- Selective context construction

The broker must remain authoritative.

Do not optimize away verification, permissions, source provenance or process cleanup.

Report real before/after numbers.

---

# 4. PRIORITY TWO — VERIFY THE NATIVE MODEL HUB

The Model Hub passes frontend component tests, TypeScript validation and Rust unit tests.

However, actual interactive acceptance in the Windows-native application is still pending.

Test the existing Tauri interface without redesigning it.

## Required scenarios

### Auto Cloud Primary

Verify:

- The default mode is selected correctly.
- Only eligible cloud routes appear available.
- Blocked routes clearly explain their status.
- Provider selection matches broker metadata.
- The UI does not invent account quotas.

### Manual Cloud

Verify:

- A user can select a registered concrete model.
- Selection persists after restart.
- A failed/unavailable route does not silently switch providers.
- `openrouter/free` clearly warns that its underlying model may vary.
- Credentials never reach frontend state or logs.

### Local Qwen and Local Heretic

Until M4 is implemented:

- Show both modes as unavailable.
- Allow only the intended safe selection behavior already defined by the current contract.
- Block cloud inference if a local-only mode is selected.
- Do not automatically start or download a local model.
- Do not falsely advertise local agent functionality.

### Consent and lifecycle

Verify:

- Switching modes invalidates applicable cloud/tool/artifact consent.
- Active tasks block model changes.
- Active voice turns block model changes.
- Duplicate clicks do not create duplicate operations.
- Restart restores the correct stored preference.
- Disconnected broker states are represented accurately.
- Failures are visible and recoverable.

Use the actual native application where supported.

If native GUI automation cannot establish acceptance, document the exact missing interaction rather than claiming success based on component tests.

Preserve the existing 3D command center, Ultron avatar, audio and rendering pipeline.

---

# 5. PRIORITY THREE — MAKE THE CLOUD PROVIDER REGISTRY PRODUCTION-READY

The four compatible transport foundations already exist:

- OpenRouter
- Groq
- Gemini
- NVIDIA NIM

**Do not rewrite these adapters.**

The remaining problem is trustworthy provider/model/account eligibility.

Current production availability:

- OpenRouter: existing gated `openrouter/free` route.
- Groq: blocked.
- Gemini: blocked.
- NVIDIA: blocked.

## Required work

Investigate current official provider documentation and the existing account/price-verification architecture.

Determine, for each provider:

1. What model metadata can be obtained without authentication?
2. What requires a protected account credential?
3. What pricing evidence is publicly available?
4. What account-specific free-tier evidence is obtainable?
5. What quota metadata is available through supported APIs?
6. Whether zero-cost eligibility can actually be established before dispatch.
7. How quickly the verification evidence becomes stale.
8. How credential rotation invalidates prior eligibility.
9. How account/provider billing rules affect permitted requests.
10. What happens when entitlement cannot be verified.

Do not equate an API key with free access.

Do not equate promotional credits with unconditional zero-cost execution.

Do not assume every model listed by a provider is available to the user.

## Feasible eligibility strategy

Implement a documented, fail-closed eligibility interface.

Allow independently verified evidence from supported official APIs and trusted provider documentation.

Where an official API cannot provide account-level proof, identify whether a separately authorized, user-reviewed account-console attestation is feasible.

Do not invent entitlement data or silently replace proof with assumptions.

If zero-dollar eligibility cannot be established under the current policy, leave that route blocked.

Provide a precise explanation in Model Hub:

- Which condition is missing
- Which provider/model is affected
- What evidence is required
- Whether the limitation is technical or account-specific

Avoid building a verification mechanism that can never succeed because its required evidence does not exist.

Document those cases as product decisions needing approval rather than silently weakening the free-only requirement.

## Provider activation

Only activate a new production route when:

- Its model capability is verified.
- Its price/account eligibility passes.
- Broker credential binding passes.
- Provider streaming and tool-call compatibility pass.
- Existing budgets and privacy restrictions pass.
- Its route is visible accurately in the UI.
- Appropriate live acceptance is separately authorized.

Do not run credential-backed tests without approval.

---

# 6. PRIORITY FOUR — HARDEN STREAMING AND LIVE ACCEPTANCE DIAGNOSTICS

The previous authorized live report attempt failed with:

`provider_stream_failed`

It made one model request.

No tools or artifacts were produced.

The provider did not return usage accounting.

The broker conservatively charged 6,002 tokens as unknown usage.

The exact cause was not established.

The latest safe stream diagnostics were added after that failure.

## Required offline investigation

Expand deterministic provider-stream fixtures to cover:

- Event framing
- Fragmented JSON
- Repeated tool metadata
- Call-ID continuity
- Empty content chunks
- Interleaved content and tool fragments
- Transport interruption
- Connection close before completion
- Provider timeout
- Malformed UTF-8
- Nonstandard but documented provider events
- Context-size rejection
- Missing usage
- Multiple tool proposals
- Unexpected finalization
- Truncated output
- Cancellation during streaming

Maintain existing strict schemas and capability grants.

Never silently repair arbitrary invalid model arguments.

Add bounded diagnostics for:

- HTTP status category
- Stream termination category
- Event count
- Bounded byte count
- Elapsed time
- Completion status
- Usage reported/unreported
- Tool proposals accepted/rejected

Do not log raw private tool arguments, credentials, provider response bodies or user documents.

## Live acceptance rule

The previous authorization is consumed.

Do not retry automatically.

After offline verification and a clean regression gate, request permission for one narrowly scoped, public-only real-model acceptance.

State:

- Provider and model
- Exact task
- Maximum external calls
- Maximum token exposure
- Public source scope
- Whether any file will be published
- No paid fallback
- No private data transmission
- No automatic retries

Preserve the existing research/report maximum of two model calls and 8,000 tokens.

If live testing remains unauthorized, mark live acceptance BLOCKED and continue independent work.

---

# 7. PRIORITY FIVE — AUDIT TOKEN ACCOUNTING AND PROVIDER ROUTING

The M3 routing policy is already implemented.

Do not replace it with another routing framework.

## Validate the existing implementation

Test:

- Deterministic classification
- Quality-aware ranking
- Privacy eligibility
- Provider/model capabilities
- Quota handling
- Sticky manual selection
- Credential rotation
- Circuit breaker recovery
- Deadline preservation
- Unknown token reservations
- Concurrent task budget consumption
- Crash and restart recovery
- Idempotent task submission
- Provider route evidence in execution traces

Current application-side ceilings are:

- 50 dispatch reservations per provider per UTC day
- 100,000 charged/reserved tokens per provider per UTC day

These are local policy ceilings, not actual provider allowances.

Ensure Model Hub never presents them as provider-granted quotas.

## Token optimization

Audit actual prompt construction.

Identify wasted tokens from:

- Repeated system instructions
- Duplicate tool descriptions
- Oversized tool schemas
- Irrelevant conversation history
- Repeated retrieved source text
- Duplicate agent handoffs
- Unnecessary planning requests
- Repeated result summaries

Reduce duplication only when source provenance, tool validity and task correctness remain intact.

Do not weaken the 8,000-token report task ceiling.

Do not add model-based routing classification unless a benchmark demonstrates sufficient value.

Do not invoke multiple models for routine requests.

The existing warm router benchmark is already below 0.2 ms p95 in synthetic tests.

**Optimize real end-to-end time and task completion, not only microsecond routing overhead.**

---

# 8. SQLITE V4 MIGRATION AND RECOVERY ACCEPTANCE

The new M3 state uses SQLite schema version 4.

Existing evidence covers isolated migration fixtures but not a real production user database upgrade.

Before any production migration:

- Verify the active schema.
- Verify there is no competing database owner.
- Inspect the migration and backup logic.
- Test migration on a controlled copy.
- Verify stored tasks and settings survive.
- Verify rollback/downgrade refusal behavior.
- Verify crash consistency.
- Verify credential rotation and route-state ownership.
- Verify no duplicate tasks after restart.

Do not migrate or replace live user data without appropriate authorization.

Preserve previous checkpoint evidence.

Do not treat a database backup as interchangeable with the live database while the broker owns it.

---

# 9. SECURITY AND ARCHITECTURE PRESERVATION

Non-negotiable:

**Hermes**

Remains the primary intelligence and planning harness.

**Immortility Broker**

Remains the only authoritative permission, credential, provider admission and capability gateway.

**Engine/Store**

Remains the only durable task/workflow owner.

**OpenMausBot**

Remains optional. Do not install another orchestrator.

**Dashboard**

Remains the existing Tauri/React/Three.js application.

Preserve:

- Typed contracts
- Exact tool identities
- Expiring permissions
- Scope checks
- Broker-owned paths
- Provider price checks
- Secret isolation
- Token reservations
- Cancellation
- Verified task receipts
- Durable task evidence
- Native consent
- Existing artifact checks

Do not enable general desktop control, unrestricted shell execution, private cloud uploads, arbitrary MCP servers or unapproved account actions.

Do not install or download dependencies/models without explicit permission.

Do not commit or push.

Do not remove or modify unrelated untracked files, including the unexpected `%SystemDrive%/` path noted in the checkpoint.

---

# 10. REQUIRED VALIDATION

After focused fixes, run the applicable complete checks:

```powershell
& .venv/Scripts/python.exe -m pytest -q services/broker/tests/test_providers.py services/broker/tests/test_provider_stream.py services/broker/tests/test_tool_streams.py

& .venv/Scripts/python.exe scripts/smoke-research-report.py

& .venv/Scripts/python.exe scripts/benchmark-model-router.py

& ./scripts/check.ps1

. ./scripts/dev-env.ps1
cargo test --offline --manifest-path apps/desktop/src-tauri/Cargo.toml

& .venv/Scripts/python.exe scripts/check-secret-isolation.py
```

Add targeted reproduction commands for the existing SDK failures.

Do not use a live-consent flag without new authorization.

Run resource benchmarks in a controlled way. Avoid unnecessary overlapping heavy test runs when assessing startup latency.

Record:

- Exact tests passed/failed
- Test revision and environment
- Reproduction commands
- CPU/RAM/GPU where measured
- Cold and warm latency
- Provider requests
- Reported vs reserved tokens
- Child process cleanup
- Files changed
- Remaining gates

Do not manipulate test expectations merely to make regression results green.

---

# 11. REQUIRED IMPLEMENTATION ORDER

## Stage A — Recovery

Inspect the current working tree and checkpoint.

Verify that previous M2/M3 changes remain intact.

Produce a concise failure map.

## Stage B — SDK reliability

Reproduce and resolve the four remaining SDK regression failures.

Investigate startup time.

Preserve original security, expiry and cancellation semantics.

## Stage C — Performance

Benchmark and optimize the slow synthetic Hermes report workflow.

Identify the actual critical path.

Record honest measurements.

## Stage D — Native UI

Verify real Model Hub mode selection, persistence, consent behavior and error presentation.

## Stage E — Provider readiness

Build or complete feasible account/model eligibility verification.

Keep unverified production dispatch blocked.

## Stage F — Streaming and accounting

Complete provider-stream diagnostics, ledger reconciliation and crash/recovery coverage.

## Stage G — Full regression

Run all existing complete validation gates and save fresh evidence.

## Stage H — Authorized live acceptance

Only if separately approved, perform one strictly bounded cloud-model acceptance.

If approval is absent, stop at the gate without misreporting the task as successful.

---

# 12. WHAT MUST NOT BE IMPLEMENTED IN THIS SLICE

Do not:

- Download Qwen3.5-9B.
- Download DeepSeek Heretic.
- Install another inference framework.
- Build a new vector database.
- Implement a second scheduler.
- Add another orchestration harness.
- Redesign the dashboard.
- Replace the Ultron avatar.
- Change voice assets or character rendering.
- Enable unrestricted computer control.
- Activate paid cloud models.
- Begin broad M4–M8 implementation.
- Rewrite the existing report engine merely because DOCX remains gated.

Local models, unified memory, advanced multi-agent orchestration and broader autonomy remain subsequent milestones.

You may prepare architecture interfaces for those later capabilities only when necessary to complete the current verified feature.

---

# 13. DELIVERABLES AND DOCUMENTATION

Update:

- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/M3_CLOUD_ROUTING_CHECKPOINT.md`
- `docs/implementation/M3_VERIFICATION.json`

Add bounded diagnostics or benchmark evidence as needed.

Preserve historical failures.

Use clear milestone labels:

**IMPLEMENTED**

Code exists.

**OFFLINE VERIFIED**

Deterministic fixtures and tests pass.

**NATIVE VERIFIED**

The real Windows application passes the required integration and interaction tests.

**LIVE VERIFIED**

A separately authorized real-provider operation passes.

**BLOCKED**

A required approval, entitlement, dependency or verification is unavailable.

## Final engineering report

Explain:

1. Exact problems discovered and their evidence.
2. Root causes confirmed versus hypotheses.
3. Code changes and files modified.
4. Startup/latency improvement, if measured.
5. Full regression results.
6. Native Model Hub acceptance.
7. Provider availability and eligibility.
8. Token and quota accounting.
9. Real cloud acceptance status.
10. Remaining limitations and next steps.

Explicitly state whether the M3 release gate passed.

A large number of passing tests does not compensate for unresolved required failures.

---

# FINAL OBJECTIVE

Complete the engineering foundation required for a production-ready IMMORTILITY intelligent model router.

IMMORTILITY must become a responsive, reliable cloud-primary AI assistant where Hermes selects a qualified model, the broker independently authorizes execution, Engine/Store preserves task state, the dashboard displays truthful status and unnecessary token consumption is minimized.

The intended providers remain:

- Groq — low-latency candidate
- Gemini — complex reasoning/long-context candidate
- NVIDIA NIM — specialized hosted open-weight candidate
- OpenRouter — multi-model access and eligible fallback

The intended manually selectable local models remain:

- Qwen3.5-9B
- DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic

However, no provider's superiority or local model compatibility is assumed without evidence.

**First fix reliability. Then prove performance. Then verify live model routing. Only afterward expand capability.**

Begin immediately with the existing dirty checkout. Do not start a fresh audit or rewrite working systems.