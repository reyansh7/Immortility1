# Immortility — current engineering checkpoint (2026-11-15)

**M3 offline regression PASSED. Native fixture acceptance advanced. M3 release NOT PASSED / BLOCKED.** Real direct-provider model/tool acceptance and account/model qualification remain unavailable. No live inference was performed.

## Current architecture

Latest user direction excludes **OpenRouter and OmniRoute** from the forward architecture. No further integration, qualification, benchmarking or activation is planned. Historical adapters, fixtures and evidence remain; the legacy fallback defaults off. Default cloud dispatch is blocked because no direct production model is qualified yet. Stored credentials do not change that status.

Use Hermes native routing/fallback and delegation, direct Gemini/Groq/NVIDIA adapters, the existing broker for permissions/credentials/budgets and Engine/Store for durable task/shared-context ownership. No replacement gateway, duplicate scheduler or orchestrator. Qwen3.5-9B remains optional/on-demand and **not installed**. See [architecture supersession](ARCHITECTURE_UPDATE_2026-11-15.md).

Instant/Deep/Execute/Bots are logical product behaviors, not four additional runtimes. Their complete manual-override UX is not implemented in this slice. Existing dashboard, Ultron/avatar assets and speech assets remain intact.

## Verified checks

| Gate | Actual result |
| --- | --- |
| `./scripts/check.ps1` | **425 Python passed, 97.74 s; 68 frontend passed, 2.30 s; exit 0** |
| Contracts/lint/format/types | Passed; 99 Python files, mypy 49 sources, TypeScript/ESLint/Prettier |
| Frontend build | Passed, 3.02 s; existing large avatar chunk warning retained |
| Offline Rust | **12 passed, 0.91 s**; native warm build 1.58 s |
| Final policy/rotation focused check | **22 passed, 2.46 s**, after the final type-narrowing/status-copy edits |
| Security | Configured keys absent from frontend/bundle/docs/config; whitespace and engineering-script syntax checks passed |

All four historical SDK cases passed in the complete suite. Original SDK/task/cancellation deadlines and retry/security expectations were not relaxed. The older 348/8-failure, 393/63/11 and interim 409/68/12 records remain historical evidence. Own earlier SDK startup series was 7/10 within its unchanged ten-second bound; auditor 40/40 scratch series is separate. No OneDrive causality or blanket startup reliability claim.

Complete gate log: `.cache/verification/m3-optional-provider-check-20261115.log` (name predates exclusion). Machine evidence/source hashes: [M3_VERIFICATION.json](M3_VERIFICATION.json). A type-narrowing assertion and provider-neutral copy were finalized during that gate; final focused tests passed afterwards. The standalone warm probe has separate current-source executable evidence.

## Implemented and demonstrated

**Runtime notifications — IMPLEMENTED / OFFLINE VERIFIED / NATIVE VERIFIED in keyless fixture.** One authenticated read-only revision long-poll replaces 15-second frontend health polling. Actual task/voice state changes lock model selection; disconnection disables last-known controls; reconnect refetches metadata. Observed preference changes clear applicable consent. No additional durable state owner or polling worker.

**Model Hub recovery — NATIVE VERIFIED in keyless fixture.** A confirmed hidden-error defect is repaired: selection failure appears inside Settings, retains the saved choice and recovers on explicit retry. A delayed selection produced one POST. Task/voice busy inputs were synthetic. Explicit scratch broker crash displayed Broker disconnected, disabled controls and recovered persisted Manual selection through the existing supervisor. No real model/audio acceptance is implied.

**Long native task transport — NATIVE VERIFIED with synthetic events.** Real Tauri/Store/auth transport completed **180.009 s**, 36 ordered unique ticks and one completion after a planned disconnect/replay. A separate 95-second silence recovered at **90.286 s**, replayed partial text and accepted one explicitly clicked cancellation with no false completion. The earlier 36-second interrupted run is retained and is not timeout acceptance. Safe cancellation notices identify normalized route, task UUID, reason and whitelisted source tag; tags never confer authority. All owned native/broker/preview processes were reaped.

**Typed tools/report budget — IMPLEMENTED / OFFLINE VERIFIED, experimental flag OFF.** Exact capability schemas, phase-specific research/report exposure, strict argument validation, retained paired history, bounded evidence and content-free byte accounting. Full source provenance stays local. The pinned MCP JSON-string envelope is compacted while retaining its complete untrusted-data warning. Two budget failures were preserved before repair. The default legacy minimum remains 826 conservative units; typed mode requires 1,200. Two calls/8,000 tokens unchanged; no argument repair, invented tokenizer ratio or third drafting call.

**Local tool/report demonstration — OFFLINE VERIFIED, historical compatibility scope.** Pinned real Hermes→MCP→broker executed research and report tools, reopened editable Markdown and rendered/read back PDF. Final source sample **15.763 s**, two synthetic provider turns with 600 fragments each, two real gateway operations, zero cloud calls. Typed drafting headroom **1,262** conservative units versus its 1,200 floor is narrow and not calibrated model token usage or quality assurance. The demonstration predates final provider exclusion; it does not authorize or propose a legacy-provider activation. DOCX publication remains disabled.

**Direct transport/policy — OFFLINE VERIFIED only.** Existing Gemini/Groq/NVIDIA adapters target official endpoints; exact endpoint/model/credential bindings pass deterministic fixtures with synthetic qualification. Eligible direct routes rank ahead of the disabled legacy fallback; manual pins remain sticky. No direct model/account has production proof. Legacy quota/security work implemented before exclusion is frozen, default-disabled compatibility coverage; no protected account endpoint was called.

## Warm Hermes feasibility — production reuse OFF

One real canonical stdio gateway completed two sequential named scratch-profile text sessions with distinct local fixture credentials and histories. Correct credentials, no crossed history canary, empty tools, acknowledged closes and owned-process cleanup passed in **two exploratory pairs**. Current-source readiness: **6.7309 s first / 1.2618 s second**; preceding pair **9.8519 / 0.7390 s**. These samples do not establish p95, production speedup or sustained throughput.

A deliberately injected post-close exception produced a **failed** probe record as intended; separate assertions verified one call/session, expected RuntimeError and complete cleanup. This negative case is not a successful warm session. No permanent process, provider account, external model or tool was involved.

Reproduce: `.venv/Scripts/python.exe scripts/probe-hermes-session-reuse.py`. Negative cleanup: add `--fault-after-first-close` (expected exit 1). Production per-task Hermes remains unchanged. MCP/tool isolation, cancellation, crash recovery, credential lifecycle and idle-memory proof are still required before enabling reuse.

Evidence: `.cache/verification/hermes-session-reuse-probe-efcab0c5-8991-43e0-afe7-fea07bc35089.json`; negative `.cache/verification/hermes-session-reuse-probe-e45813c6-eca6-4428-b8d7-7a316d56241b.json`.

## Resource and live limits

Historical compact-idle observation, five samples over 20.939 s, 11 owned native/broker/WebView processes: **6.044% of one logical core** (~0.378% whole 16-core machine), summed peak working sets **808,640,512 bytes**, private memory **490,008,576 bytes**, Windows owned-PID GPU dedicated counter **23,339,008 bytes**. Shared RSS may be double-counted; this is neither UI-only RAM, GPU utilization, NVIDIA-only VRAM nor a before/after/ten-minute soak. It predates the final notification bundle.

No new inference/account calls, paid requests, private uploads, installs, models, system changes, live database migration, project commit/push/reset/clean or unrelated cleanup. Unknown sent usage remains conservatively charged. The historical failed live attempt's **6,002 unknown tokens** are not measured consumption; authorization is consumed and no retry was made. Local policy ceilings (50 requests/100,000 charged-reserved tokens per provider/day) are not provider quotas.

## Exact next gates

1. Prove warm canonical Hermes MCP/tool/profile isolation, cancellation/crash cleanup and idle resources before production reuse.
2. Qualify concrete direct Gemini/Groq/NVIDIA models, supported zero-cost/account evidence, context limits and tool-stream behavior. Keep unknown entitlements blocked; no brand superiority assumed.
3. Calibrate report budget/context with a qualified direct model, then request separate public-only live acceptance: at most two model calls/8,000 tokens, no private content, paid fallback, file publication or retry. No excluded-provider acceptance will be requested.
4. Preserve model-independent context in the existing Store and Hermes native specialist contracts; expand capability only after those gates. On-demand Qwen installation/resource checks require separate authorization.

Detailed changes, actual native evidence paths, root causes and reproduction commands: [worklog](M3_FINAL_INTEGRATION_WORKLOG.md), [checkpoint](M3_CLOUD_ROUTING_CHECKPOINT.md), [verification JSON](M3_VERIFICATION.json). Pre-consolidation text is preserved in `CURRENT_STATUS_HISTORY_M3_FINAL_INTEGRATION_2026-11-15.md`; earlier history and failed records remain intact.
