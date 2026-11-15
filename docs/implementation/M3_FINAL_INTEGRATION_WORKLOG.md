# M3 final integration — active worklog

**Latest architecture supersession:** [ARCHITECTURE_UPDATE_2026-11-15.md](ARCHITECTURE_UPDATE_2026-11-15.md) excludes OpenRouter and OmniRoute from further development/adoption. Legacy evidence and already implemented compatibility code are retained; default fallback is off. Direct Gemini/Groq/NVIDIA and on-demand Qwen are the forward targets. No local model is installed and no direct production route is qualified. Historical preparation below is not permission or a plan to activate a legacy provider.

Task order: native long-stream/race acceptance; exact approved tool schemas and measured context; concrete model/context/provider qualification; isolated warm Hermes experiment; complete regression and checkpoint. Follow-on memory work requires the preceding critical gates. No new live inference authorization exists.

Risks: native stream/replay/cleanup regressions; schema overhead starving the two-call/8,000-token report policy; warm process cross-task leakage; unknown account entitlements. Preserve the current dirty checkout, provider gates, task/grant deadlines, existing UI/avatar/voice and Engine/Store ownership. No installs, live database migration, project Git changes or account operations.

Recovered source hashes matched the prior checkpoint. Initial native work uses only an explicit debug fixture, empty provider credentials, scratch Store/profile and fixed synthetic events. Synthetic drafting remains separate from real-provider acceptance.

## Verified work in this integration slice

- **IMPLEMENTED / OFFLINE VERIFIED:** authenticated read-only runtime revision notifications replace the frontend's 15-second health interval. Engine/Store remains authoritative. Active-task, voice-state and acknowledged preference changes wake the single long-poll; disconnected controls are disabled and reconnect refetches model metadata.
- **NATIVE VERIFIED, keyless fixture:** 180.009-second native task stream survived the planned connection break, replayed 36 ordered ticks once and completed once. The separate 95-second silent case reconnected at 90.286 seconds, replayed partial results and accepted one explicitly clicked cancellation. A prior early-cancelled 36-second attempt is retained as an unpassed case.
- **IMPLEMENTED / NATIVE VERIFIED:** the hidden Model Hub selection error is now visible inside Settings. Injected failure retained Auto; explicit retry stored Manual and cleared the alert. Delayed selection produced one model-mode POST; synthetic task/voice busy notifications locked controls. These are native interactions with synthetic workloads, not physical voice or real AI acceptance.
- **IMPLEMENTED / OFFLINE and NATIVE VERIFIED:** bounded cancellation notices identify normalized route, task UUID, reason and a whitelisted source category. Source tags are diagnostic labels, never authorization evidence. The explicit native cancellation had one Store transition and one audit notice.
- **NATIVE VERIFIED:** scratch-only broker crash showed Broker disconnected and disabled last-known controls, followed by supervisor recovery and persisted Manual selection. No task or provider call was created; owned processes were reaped. Evidence: `.cache/verification/native-broker-crash-recovery-fe62b900-d98a-4f26-96f2-e58c43361bef.json`.
- **IMPLEMENTED / OFFLINE VERIFIED, experimental flag OFF:** exact capability input schemas, phase-specific research/report exposure, strict broker argument validation, bounded model evidence and content-free prompt byte components. Schema reference siblings retain both constraints. Historical research call/result pairs stay valid while only the report schema is advertised. No alias translation or invalid-argument repair.

## Confirmed budget problem and bounded repair

The first typed-schema smoke exposed both schemas, adding 1,147 bytes over the generic schema, and failed before drafting. A second version still could not reserve the new 1,200-unit experimental output floor. Both failures remain in unique evidence files:

- `.cache/verification/research-report-smoke-713e719a-83ce-480d-b2f5-00bc57178727.json`
- `.cache/verification/research-report-smoke-ee5e3d87-3787-4079-bca8-27f5e6b5dd6c.json`

Phase-specific schemas, concise trusted instructions and removal of the pinned MCP JSON-string envelope now pass. The complete untrusted-result warning, source IDs, paired call IDs and full local provenance remain. Success `.cache/verification/research-report-smoke-8d01540d-ff47-46ec-b937-0019a8c9144f.json`: real local Hermes/MCP/broker, two actual gateway operations, real Markdown/PDF verification, 20.542 seconds, zero cloud calls. Second-call reservation 5,988 input units leaves 1,262 output units after synthetic reported first-call usage. The 62-unit margin over the experimental floor is narrow. The fixture's 1,500 reported tokens are synthetic and cannot calibrate real tokenization. No speedup is established against the earlier 14.394-second functional sample.

Report policy stays two provider calls / 8,000 tokens. Unknown usage remains conservatively charged; it may prevent the second call. Legacy default keeps its existing 826-unit minimum; typed mode requires 1,200 and stays off pending real model qualification and authorized acceptance.

## Resource observation

Five compact-idle samples over 20.939 seconds, 11 owned native/broker/WebView processes: about 6.044% of one logical core (~0.378% of this 16-logical-core machine), peak summed working sets 808,640,512 bytes and summed private memory 490,008,576 bytes. Shared pages may be double-counted. Owned-PID Windows GPU dedicated-memory counter: 23,339,008 bytes; not GPU utilization or NVIDIA-only VRAM. This predates the final runtime-notification bundle and is not a before/after comparison, a ten-minute soak or proof of a 250 MB UI-only target. Evidence: `.cache/verification/native-idle-summary-29758bfb.json`.

## Current blockers and next bounded slice

M3 release is still **BLOCKED**: no new authorized real-model acceptance, no qualified concrete model/tokenizer/context, no account-specific quota/eligibility fetch, and no live Groq/Gemini/NVIDIA stream qualification. DOCX publication remains disabled. No installation, account connection, live migration, paid request, private upload or Git history/index mutation occurred.

The user's Instant/Deep/Execute/Bots policy describes logical behaviors within this same stack. Existing deterministic classification and task/tool contracts can support that direction; four product modes and manual overrides are not yet implemented or advertised. Prioritize genuine model-selected tool execution before memory/framework expansion.

Installed Hermes exposes multi-session/profile APIs, but current Immortility launches bind a task-specific loopback credential and MCP profile. Keeping that process alive without proving profile/MCP/credential/cancellation isolation is unsafe. The keyless sequential text-profile probe below passed; production warm reuse remains disabled pending tool/cancellation/recovery qualification.

OpenRouter's official current-key endpoint documents account-specific free-model request counts. Public documentation was read; the protected endpoint was not called. Quota counts would supplement, not replace, the current price gate or establish concrete-model compatibility. Unverifiable providers stay blocked. Sources: [current-key API](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key), [provider parameter enforcement](https://openrouter.ai/docs/guides/routing/provider-selection#requiring-providers-to-support-all-parameters).

Fresh complete results/source hashes are recorded in `M3_VERIFICATION.json`: **425 Python / 68 frontend / 12 Rust passed**. Earlier 393/63/11 and interim 409/68/12 results are preserved historical checkpoints.

## Final provider-policy reconciliation

Before the final exclusion instruction, fresh bounded official account-quota parsing and not-sent ledger settlement were implemented and tested offline. Missing/ambiguous/inconsistent quota, credits-only data, redirect, 401, malformed UTF-8, duplicate JSON fields and oversized bodies fail closed; cancellation propagates. Account metadata never goes to Hermes/frontend/logs; only a request count can enter an audit notice. Credential rotation and revoked grants block protected preflight continuation. That legacy work is now frozen and default-disabled; no protected endpoint or model call was executed.

Direct-provider transports already dispatch to their official API endpoints in the existing adapter. Tests exercise exact endpoint/model/credential binding with synthetic qualification, not real account eligibility. Automatic ranking now prefers eligible direct routes, preserves explicit manual pins and never replays an active task to another provider. Production direct routes remain blocked rather than treating stored keys or credits as free access.

The updated ready/setup copy is provider-neutral. No new model framework, proxy, optional routing package or service was added. Broker security, budgets, Store ownership and existing memory are unchanged.

## Warm canonical Hermes experiment

`scripts/probe-hermes-session-reuse.py` uses only the installed reviewed canonical stdio gateway, existing spawn/cleanup ownership and isolated temporary profiles. No alternate agent loop, production service or real provider request. Two sequential named profiles receive separate loopback fixture credentials and synthetic history canaries. Readiness in either create/info order requires an empty tool inventory; each session completes and receives an explicit close acknowledgement. Returned requests confirm matching credentials, own history and absence of the other profile's canary.

Two positive exploratory pairs passed: first readiness **9.8519 / 6.7309 s**, subsequent readiness **0.7390 / 1.2618 s**. Final source is SHA-bound in `.cache/verification/hermes-session-reuse-probe-efcab0c5-8991-43e0-afe7-fea07bc35089.json`. No p95, sustained performance or production speedup claim follows from these pairs. Zero tools/cloud calls. The final-source negative `--fault-after-first-close` intentionally exited 1 and produced a failed record; independent assertions verified the requested fault, one closed session/call, expected RuntimeError and cleanup. Failed evidence is preserved at `.cache/verification/hermes-session-reuse-probe-e45813c6-eca6-4428-b8d7-7a316d56241b.json`.

This proves feasibility for sequential text-profile reuse only. MCP/tool context, cancellation, crash/restart, credential lifecycle, concurrent sessions and idle memory remain unverified. The production Hermes adapter still uses the original per-task process/profile.

## Files and final checks

Current-slice source changes: `runtime_status.py`, Engine/runtime-status and cancellation routes in `app.py`, state-change callback in `voice.py`; `runtimeStatus.ts`, `main.tsx`, Model Hub/Settings/Conversation/transport components and Rust fixed-operation transport; exact schema/history handling in `agent_bridge.py`, report evidence/accounting in `research.py`/`ledger.py`, trusted schema construction in `policy.py`, experimental prompt/config export in `hermes.py`/`config.py`; direct-first/default-disabled legacy policy in `providers.py`; debug-only native fixture scripts and the isolated warm probe. New/updated tests cover those contracts. Earlier dirty stream/artifact/benchmark repairs are preserved and distinguished by checkpoint history. No voice/avatar asset changes.

Full check: `./scripts/check.ps1` — 425 Python (97.74 s), 68 frontend (2.30 s), contracts/static/build passed; 99 formatted Python files, mypy 49 sources, frontend build 3.02 s. Offline Rust 12 passed (0.91 s), warm build 1.58 s. After final assertion/status-copy edits, provider-policy/rotation focus 22 passed (2.46 s). Secret isolation, script syntax, warm-probe lint and whitespace passed. Existing Starlette deprecation and large avatar bundle warnings remain; no dependencies were upgraded to suppress them.

**M3 release gate NOT PASSED.** Direct model/account/live-tool qualification is still missing. Production warm reuse is OFF. Next eligible engineering slice is keyless MCP/profile/cancellation isolation using this same canonical gateway, then direct-provider eligibility and separately authorized public real-model execution. No excluded-provider work, model install or broad memory/agent framework expansion.
