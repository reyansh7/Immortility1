Immortility — Independent System Audit (a2fbdbe)
What works, what only appears to work, and what blocks the Stage 4 critical chain, with every finding traced to file and line in commit a2fbdbe. Full reports and the Codex handoff are in /workspace/immortility/audit/.
On this page
Headline
Stage 4 critical chain
Live-run store inspection
Architecture as implemented
Implemented vs target
Integration matrix
Defect register
Where the time goes
Security posture
Roadmap
Codex handoff (Report K)
Verdict (Report L)
Show all 16
Headline
1
Critical findings
F-02 Hermes cold start (F-01 now High)
8
High findings
363 / 363
Native pytest (scratch copy)
plus Rust 9/9
1
Dispatchable model route
openrouter/free only
0
Live end-to-end report successes
provider_stream_failed, 6,002 charged
Takeaway.
The security design is strong. Execution is not yet reliable: cold process spawns set a 7–10 s floor per turn, the report budget is arithmetically infeasible, and stream failures can end with no diagnostic. Fix K-01 to K-06 before any fresh live retry.
Evidence classes are kept separate: SYN (synthetic), LOCAL-NATIVE (repo evidence from native runs), NATIVE WINDOWS (my approved runs in a TEMP scratch copy, 15 Nov 2026 around 14:53–15:15 IST), BOX (my Linux sandbox runs, not native Windows), PROVIDER (recorded cloud results). I made no cloud calls and no repo writes. The PDFs could not be cross-checked because they are not on the box. No overall completion percentage is given.
Stage 4 critical chain

| #   | Link                        | Diagnosis                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Status                                |
| --- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| 1   | Model / tool execution      | Provider sees one untyped execute(capability, arguments: object); schemas only in prose (agent_bridge.py L45-63; hermes.py L155-204). Consistent with the pre-M3 tool_denied result.                                                                                                                                                                                                                                                                                                                                          | Design confirmed, impact suspected    |
| 2   | Token accounting            | Bytes counted as tokens (4.11x over-estimate). With the 8,000 / 2-call report clamp, the drafting call gets 313 tokens or is blocked. A length finish is rejected as stream_shape.                                                                                                                                                                                                                                                                                                                                            | Confirmed arithmetic                  |
| 3   | SSE boundary / evidence gap | Correction: the recorded message comes from the caught-exception branch (app.py L2344-2373), so the asyncio.timeout hazard (F-04) did not cause it. reason_categories is empty because the smoke collects only provider_tool_contract events (F-33). The approved inspection found no stored reason at all; that run used uncommitted code (F-39). Leading explanation: the tool-mode 128 KB raw-chunk buffer overflows after about 280–410 tokens, which reproduces the exact message, unknown usage and full charge (F-38). | F-38 leading hypothesis               |
| 4   | 6,002 charge                | Input bound 3,954 + max_tokens 2,048, kept in full because usage was unknown. Fail-closed and correct, but it blocks any retry within the task.                                                                                                                                                                                                                                                                                                                                                                               | Confirmed                             |
| 5   | MCP 10.684 s vs 10 s        | Fresh client + server interpreters per call; the 10 s grant covers spawn plus an inner 10 s timer. In the native scratch copy all 40 starts took 2.3–3.0 s, so the miss did not reproduce (environment hypothesis: OneDrive location).                                                                                                                                                                                                                                                                                        | Design confirmed, miss not reproduced |
| 6   | Broker authorization        | Sound (task-bound grants, per-task key, digest). The only gap is a wall-clock grant spanning cold spawns.                                                                                                                                                                                                                                                                                                                                                                                                                     | Confirmed                             |
| 7   | Routing                     | One candidate route, so routing neither causes nor fixes the failure.                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Confirmed                             |
| 8   | Task recovery               | Only local workflows resume; agent tasks become disconnected (store.py L124-152).                                                                                                                                                                                                                                                                                                                                                                                                                                             | Confirmed                             |
| 9   | 4 SDK failures              | All route through per-call cold start under a 10 s grant. Natively they passed in the full suite (363/363) and in 5 of 5 focused reruns.                                                                                                                                                                                                                                                                                                                                                                                      | Not reproduced natively               |

Ranked by likely contribution to the failed live report task
Live-run store inspection

| Run                                          | Timeline (IST)                                                        | Ledger                                                    | Outcome                                  |
| -------------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------- |
| Pre-M3 live, task 032ec364 (deep)            | 02:25:18 running; call at +21.7 s; blocked +5.8 s later               | 1,180 charged (961 prompt + 219 completion, 90 reasoning) | tool_denied; invalid field not stored    |
| Authorized M2 live, task 305d230c (standard) | 11:39:31 running; call at +8.7 s; failed +14.5 s later (23.2 s total) | 6,002 reserved and charged; usage unknown; no deltas      | provider_stream_failed; no reason stored |

Approved read-only inspection (card t0s18), about 15:30–15:35 IST. 19 retained stores under .cache\\report-workflows were opened with sqlite mode=ro&immutable=1 (the one WAL store was read from a TEMP copy). Output was redacted, nothing was written, and file count and bytes were identical before and after

| Candidate cause                                                    | Status             | Basis                                                                                                                         |
| ------------------------------------------------------------------ | ------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| Non-200 HTTP (429 etc.)                                            | Excluded*          | Would give the quota or rejected message; so HTTP 200 is inferred                                                             |
| Send-time transport error                                          | Excluded*          | Would give 'Provider transport failed'                                                                                        |
| Mid-stream provider error chunk                                    | Excluded*          | Would give 'Provider interrupted the response'                                                                                |
| Deadline or timeout                                                | Unlikely           | 23 s into a 150 s plan deadline; 14.5 s vs a 70 s read timeout                                                                |
| Tool-mode 128 KB buffer overflow (F-38)                            | Leading hypothesis | SYN N=600 gives the exact message, unknown usage and full charge; earlier successful live tool turns were 219 tokens or fewer |
| Missing [DONE], bad JSON, oversize event, disconnect, null choices | Not excluded       | Same message, no stored diagnostic                                                                                            |

Root cause is still a hypothesis.
The reason, provider error code and HTTP status were never persisted, because the live run used uncommitted code without the stream audit event. Excluded* assumes that code's relay branches matched a2fbdbe. To confirm: land K-32 and K-24, then run either one freshly authorized live attempt that records the diagnostic and the streamed chunk and byte counts, or an offline 600-chunk tool-mode smoke.
Architecture as implemented
Tauri 2 + React 19
stream_task: 100 s total timeout
FastAPI broker
token + origin check; one global
Engine
SQLite WAL
commit per delta; 150 ms polling
Hermes 0.21.1
new process + temp HOME per turn
MCP agent bridge
one opaque execute tool
Capability gateway
global lock during execution
MCP SDK arithmetic
client + server spawned per call
Research / report / window
read
3 fixed sources; report worker
Inference proxy
byte bound; catalog fetch every call
openrouter/free
HTTP + SSE
stdio JSON-RPC
POST /v1/agent/tool
chat/completions
SSE
Dashed edges are spawned fresh per turn or per call
Implemented vs target

| Layer         | Target                                        | As implemented                                         | Finding          |
| ------------- | --------------------------------------------- | ------------------------------------------------------ | ---------------- |
| Agent runtime | Long-lived agent with sessions, tools, memory | Cold start per turn; memory and toolsets stripped      | F-02, F-10       |
| Tools         | Typed, warm, parallel-safe                    | Opaque meta-tool; SDK cold spawn per call; global lock | F-01, F-24, F-32 |
| Routing       | Multi-provider, measured                      | One route; keyword classes                             | F-06             |
| Streaming     | Incremental, diagnosable                      | Buffered in tool mode; deadline inside generator       | F-04, F-14, F-25 |
| Budget        | Accurate, usage-calibrated                    | Byte-count bound starves reports                       | F-03             |
| Memory        | Cross-session, ranked, curated                | Session FTS; recalls model answers                     | F-10             |
| Delegation    | Tool-using sub-agents                         | Text-only specialists, new process each                | F-09             |
| Local models  | Ollama / llama.cpp on the RTX 4060            | Fail-closed placeholders                               | F-26             |
| Voice         | Wake word, streaming STT                      | Push-to-talk, batch STT, interrupt                     | F-27             |
| Computer use  | Observe and act with confirmation             | Window UIA read-only                                   | —                |

Integration matrix

| Integration                  | Status                                                          | Evidence                                               |
| ---------------------------- | --------------------------------------------------------------- | ------------------------------------------------------ |
| Hermes Agent 0.21.1 (pinned) | Native verified (synthetic)                                     | hermes.py L22-82; report benchmark 5/5                 |
| OpenRouter openrouter/free   | Live failed                                                     | M2_REPORT_LIVE_SMOKE.json                              |
| Groq / Gemini / NVIDIA       | Offline tests pass natively, generic fixtures; dispatch blocked | providers.py L444-455; test_providers.py L321-360      |
| xAI                          | Not implemented                                                 | providers.py L25                                       |
| MCP SDK (arithmetic)         | Native verified, 40/40 (scratch copy)                           | Repo record was 7/10; evidence/native/sdk_bench_*.json |
| MCP agent bridge             | Native verified (synthetic)                                     | integrations/mcp-standard/agent_bridge.py              |
| Legacy MCP bridge            | Duplicate                                                       | mcp_bridge.py L40-62                                   |
| Public research              | 3 fixed sources + Wikipedia                                     | research.py L19-33                                     |
| Report artifacts             | Native verified (synthetic)                                     | benchmark 10/10; offline smoke 5/5                     |
| DOCX / PPTX / XLSX           | Disabled / not implemented                                      | config.py                                              |
| Coding (proposal only)       | Implemented, narrow                                             | workspace.py L130, L201-228                            |
| Windows observer             | Read-only UIA                                                   | .venv-observer (pywinauto 0.6.9)                       |
| Voice STT / TTS              | Implemented, push-to-talk                                       | voice_worker.py L36-117                                |
| Handy                        | Not installed                                                   | PC inventory                                           |
| llama.cpp                    | Not implemented                                                 | PC inventory                                           |
| Ollama                       | Installed, unused                                               | AppData/Local/Programs/Ollama                          |
| Local Qwen / Heretic         | Not implemented (fail closed)                                   | providers.py L407-413                                  |
| OpenMausBot                  | Not installed; do not integrate                                 | needs Node 24+; PC has 22.13.1                         |
| Wake word                    | Not implemented                                                 | voice.py L200                                          |
| Credential Manager           | Implemented                                                     | secrets.py; app.py L1618-1636                          |

Defect register
All33
Critical1
High8
Medium16
Low8

| ID   | Severity | Subsystem              | Location                                                                                   | Finding                                                                                                                                                                                                                                                 | Status                                     |
| ---- | -------: | ---------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| F-01 |     High | MCP / tools            | standard_mcp.py L96-215; sdk_client.py L27-52; capabilities.py L45, L196-200, L219         | Per-call cold spawn of SDK client + server: native 2.34 s p50 (40/40 ok) vs ~1 ms warm. Was Critical; the repo-recorded failures did not reproduce natively                                                                                             | Confirmed (native)                         |
| F-02 | Critical | Agent runtime          | hermes.py L305-374; delegation.py L83-97                                                   | New Hermes + MCP bridge per turn: 7.3–9.9 s before the first model call; 46 processes per report                                                                                                                                                        | Confirmed                                  |
| F-03 |     High | Token budget           | ledger.py L252-255; app.py L729-735, L2143-2155; agent_bridge.py L236-239                  | Byte-as-token bound (4.11x) leaves 313 output tokens for report drafting, or blocks it                                                                                                                                                                  | Confirmed arithmetic                       |
| F-33 |     High | Evidence / diagnostics | smoke-research-report.py L298-302; app.py L2286-2292, L2344-2373                           | Live-smoke JSON collects only provider_tool_contract, so stream failure reasons are dropped and error-chunk codes are lost. The approved store inspection showed the live run never persisted any reason, so it cannot be recovered.                    | Confirmed                                  |
| F-38 |     High | Tool bridge stream     | app.py L2303-2306, L2344-2373                                                              | Tool-mode relay caps raw chunk-JSON bytes at 128,000, about 280–410 streamed tokens against max_tokens 2,048. Overflow yields the exact live error message, unknown usage and a full charge (SYN repro, N=600). Leading explanation of the live failure | Mechanism confirmed; live cause hypothesis |
| F-04 |   Medium | Provider stream        | provider_stream.py L12-54; app.py L2344-2374                                               | asyncio.timeout around yield is a latent hazard, but it did not produce the recorded live failure (was High; see F-33)                                                                                                                                  | Mechanism confirmed                        |
| F-32 |     High | Tool interface         | agent_bridge.py L45-63; hermes.py L155-204                                                 | One opaque execute(capability, arguments: object); real schemas only as prose in the prompt                                                                                                                                                             | Design confirmed                           |
| F-05 |     High | Provider compat        | agent_bridge.py L198-203; test_providers.py L321-360                                       | Gemini tool stream without index is rejected; provider fixtures are generic                                                                                                                                                                             | Confirmed (repro)                          |
| F-06 |     High | Routing                | providers.py L133-174, L444-455; routing.py L30-50                                         | Router has one dispatchable route; classes come from keywords                                                                                                                                                                                           | Confirmed                                  |
| F-08 |     High | Engine                 | app.py L165-334, L2117-2129                                                                | Single global active task; no concurrency                                                                                                                                                                                                               | Confirmed                                  |
| F-07 |   Medium | Provider policy        | policy.py L50-62; app.py L2207-2208                                                        | Full OpenRouter catalog downloaded before every model call                                                                                                                                                                                              | Confirmed                                  |
| F-09 |   Medium | Delegation             | delegation.py L1-8, L83-97, L117-182                                                       | Text-only specialists, each a new Hermes process                                                                                                                                                                                                        | Confirmed                                  |
| F-10 |   Medium | Memory                 | store.py L431-461; app.py L845-858, L955                                                   | Session-only FTS, unranked, recalls model answers as facts, duplicated context                                                                                                                                                                          | Confirmed                                  |
| F-11 |   Medium | Persistence            | store.py L370-391; app.py L1964-1991                                                       | Commit + schema validation per token delta; SSE polls SQLite every 150 ms                                                                                                                                                                               | Confirmed                                  |
| F-12 |   Medium | Event loop             | mcp_bridge.py L40-62; standard_mcp.py L66-81                                               | Sync subprocess and 135-file hashing on the event loop                                                                                                                                                                                                  | Confirmed                                  |
| F-14 |   Medium | Desktop                | main.rs L508-515, L600-643                                                                 | 100 s whole-request reqwest timeout vs task deadlines up to 300 s                                                                                                                                                                                       | Suspected                                  |
| F-15 |   Medium | Hermes protocol        | hermes.py L293-303, L402-421                                                               | Possible prompt-never-submitted ordering race; 70 s TimeoutError unmapped                                                                                                                                                                               | Hypothesis                                 |
| F-16 |   Medium | Coding                 | workspace.py L130, L201-228, L321-328                                                      | Proposal only; first 20 files; no .ts/.tsx/.rs; tests disabled                                                                                                                                                                                          | Confirmed                                  |
| F-17 |   Medium | Research               | research.py L19-47; web.py L17-113                                                         | 3 fixed unpinned main-branch sources + Wikipedia; dead sync path                                                                                                                                                                                        | Confirmed                                  |
| F-18 |   Medium | Supply chain           | evidence/pip_audit_pc_venvs.txt                                                            | Hermes venv: 105 advisories (incl. mcp 2.0.0); .venv-tts: 57; reachability low                                                                                                                                                                          | Confirmed                                  |
| F-39 |   Medium | Evidence provenance    | M2_REPORT_LIVE_SMOKE.json; smoke-research-report.py                                        | Committed live evidence came from uncommitted code (store schema matches neither 2b81cfe nor a2fbdbe); no commit, dirty flag or code digest recorded                                                                                                    | Confirmed                                  |
| F-34 |   Medium | Model route            | policy.py L9; providers.py L162-174; app.py L2163                                          | openrouter/free meta-router instead of a pinned :free model; registry claims 16,384 context vs Hermes' documented 64K minimum                                                                                                                           | Confirmed                                  |
| F-35 |   Medium | Routing                | routing.py L14-50; providers.py L133-147; policy.py L26-30                                 | Three overlapping routing layers; the Fast/Standard/Deep plans are an earlier-architecture remnant                                                                                                                                                      | Confirmed                                  |
| F-24 |   Medium | Gateway                | capabilities.py L227-293                                                                   | Global lock held across capability execution                                                                                                                                                                                                            | Confirmed                                  |
| F-25 |   Medium | Streaming UX           | app.py L2303-2326                                                                          | Tool-mode turns stream nothing until [DONE]                                                                                                                                                                                                             | Confirmed                                  |
| F-13 |      Low | MCP                    | mcp_bridge.py L40-62                                                                       | Duplicate legacy MCP with Content-Length framing                                                                                                                                                                                                        | Confirmed                                  |
| F-19 |      Low | Repo hygiene           | %SystemDrive%/ProgramData/.../Caches/*.db                                                  | Windows cache DBs tracked in git                                                                                                                                                                                                                        | Confirmed                                  |
| F-20 |      Low | Secrets                | providers.py L150-152                                                                      | Unsalted SHA-256 key fingerprint persisted                                                                                                                                                                                                              | Confirmed                                  |
| F-21 |      Low | Audit trail            | app.py L829-840, L962                                                                      | Audit event hard-codes provider openrouter                                                                                                                                                                                                              | Confirmed                                  |
| F-22 |      Low | Code health            | policy.py L33-35; scripts/; docs/research/docs/                                            | Dead code, 69 unlinted script errors, duplicated docs                                                                                                                                                                                                   | Confirmed                                  |
| F-23 |      Low | Persistence            | store.py L124-152, L481-491                                                                | Full task scans at startup and per request                                                                                                                                                                                                              | Confirmed                                  |
| F-36 |      Low | Docs / scaffolding     | Immortility_Tech_Stack.md L13, L19; services/*; apps/desktop/src/{app,components,features} | Earlier-architecture docs (Ollama, openWakeWord) and empty scaffold dirs; final architecture not in repo                                                                                                                                                | Confirmed                                  |
| F-27 |      Low | Voice / UI             | voice.py L200; BASELINES.md                                                                | Push-to-talk batch STT; UI 285 MB vs 250 MB target                                                                                                                                                                                                      | Confirmed                                  |

Full #28-format entries in IMMORTILITY_AUDIT_REPORT.md
Where the time goes
Hermes + MCP ready
6.68 s
Report worker
1.75 s
session.create
0.51 s
Everything else
1.56 s

| Metric                  | Native scratch copy       | Repo record                |
| ----------------------- | ------------------------- | -------------------------- |
| SDK cold pair p50 / p95 | 2,342 / 2,684 ms (40/40)  | 6,763 / 10,549 ms (7/10)   |
| SDK warm p50            | 0.78–1.11 ms              | 1.43 ms                    |
| Report task p50 / p95   | 10,490 / 14,819 ms (n=10) | 13,113 / 15,779 ms (n=5)   |
| Hermes + MCP ready      | 6.1–9.9 s (61–67%)        | 7.3–9.9 s                  |
| Offline smoke ×5        | mean 10.03 s, sd 0.14 s   | —                          |
| pytest                  | 363 pass / 0 fail         | 351/5 and 348/8            |
| UI working set          | not run                   | 284.93 MB vs 250 MB target |

Synthetic report task, native Windows scratch copy, n=10; median sample (10.49 s total)
Native Windows verification

| Check                                          | Result                                                                           | Status         |
| ---------------------------------------------- | -------------------------------------------------------------------------------- | -------------- |
| Full pytest --durations=30                     | 363 passed, 0 failed, 1 deselected (Credential Manager roundtrip), 92.3 s        | Pass           |
| 4 previously failing tests and their files, ×5 | 31/31 passed in each of 5 runs                                                   | Not reproduced |
| check.ps1 Python steps                         | blueprint, contracts --check, ruff, ruff format, mypy (46 files) all pass        | Pass           |
| check.ps1 pnpm steps                           | Skipped: node_modules excluded and installs forbidden; box run passes            | Skipped        |
| SDK startup 2×20                               | p50 2,342 ms, p95 2,684 ms; handshake fixed at about 977 ms (new task K-23)      | Pass           |
| cargo test --offline                           | 9 passed, 0 failed                                                               | Pass           |
| cargo tree -i, 5 advisory crates, windows-msvc | Nothing to print: not in the Windows build                                       | Not reachable  |
| benchmark-desktop.py                           | Skipped: launches the full GUI app for 10+ min and needs the excluded target exe | Skipped        |

Approved runs in %TEMP%\\immortility-audit, 15 Nov 2026 around 14:53–15:15 IST; scratch copy deleted afterwards and the real repo left untouched (HEAD a2fbdbe, 0 changes)
Severity changes.
F-01 goes from Critical to High: the failures did not reproduce in TEMP, but each call still costs 2.3 s cold against about 1 ms warm. F-03 is reinforced: even the native synthetic run sent the drafting call only 973 max tokens. New hypothesis: the repo's OneDrive-synced location slows imports (K-23).
PDF cross-check
18
Matches
20
Partial
11
Contradicted
5
Not implemented
Final architecture (research-backed blueprint v1.0, 14 pp) vs code at a2fbdbe plus native results. Full 55-row table in report §16. The attachment file names were swapped in the hand-off: 23535331… is the FINAL document, 2520a61e… the EARLIER one.
Counts are indicative claim tallies, not a completion score. The security model, fail-closed policy, local triage, verification and key isolation largely match the final architecture. Orchestration, memory semantics, routing breadth and the performance targets do not.

| Final-architecture claim                                                     | Code / evidence                                                                   | Verdict         |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | --------------- |
| A1: four benchmarked cloud routes                                            | One registered route (providers.py L162-174); others blocked (L444-455)           | Contradicted    |
| A3: reuse Hermes adapters, delegation, memory                                | provider custom (hermes.py L205-211); delegation and memory disabled (L215, L237) | Contradicted    |
| §3.4: exact tool schemas in context                                          | Prose schemas; execute(arguments: object) (hermes.py L155-204)                    | Contradicted    |
| §6: no second planner                                                        | delegation.py L117-182 reimplements orchestration                                 | Contradicted    |
| §4: pin an approved :free model                                              | openrouter/free meta-router (policy.py L9)                                        | Contradicted    |
| §7: never turn guesses into memories                                         | Final answer stored and recalled (app.py L955, L854-858)                          | Contradicted    |
| §7: count with the model tokenizer                                           | Bytes treated as tokens (ledger.py L252-255)                                      | Contradicted    |
| §11: route decision under 10 ms from cache                                   | Catalog fetched every call (app.py L2207-2208)                                    | Contradicted    |
| §11: first token under 1.5 s p50                                             | Hermes + MCP ready alone 6.1–9.9 s (native)                                       | Contradicted    |
| §13: M2 live gate before M3                                                  | M3 work landed; live M2 still fails (F-37)                                        | Contradicted    |
| §8: Hermes needs at least 64K                                                | Verified in Hermes docs; registry says 16,384 (providers.py L167)                 | Inconsistent    |
| §10: state machine incl. PLANNED / PAUSED / DELIVERED                        | store.py L393-419 lacks them                                                      | Partial         |
| §10: one authoritative scheduler                                             | workflows.py L3: there is no scheduler                                            | Not implemented |
| A2: local Qwen / Heretic, no cloud fallback                                  | Fail-closed placeholders (providers.py L275-280)                                  | Partial         |
| Keys never reach React or Hermes; no paid fallback; deny on unverified price | secrets.py; hermes.py L335-361; providers.py L420-441; policy.py L50-62           | Matches         |
| No shell or remote MCP; revoke on Stop; verify reports by hash               | capabilities.py; app.py L1002, L1140-1165; native smoke                           | Matches         |

| Earlier-architecture remnant                                                           | Where                                                                       |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Fast / Standard / Deep profiles, alongside the two-stage router and route_model (F-35) | routing.py L14-50; providers.py L133-147; policy.py L26-30                  |
| Role specialist table, as custom delegation (F-09)                                     | delegation.py L117-182; hermes.py L85-89                                    |
| Legacy MCP bridge on protocol 2024-11-05 (F-13)                                        | mcp_bridge.py                                                               |
| Ollama / LM Studio option and openWakeWord in docs (F-36)                              | Immortility_Tech_Stack.md L13, L19                                          |
| Services folder layout as empty scaffolds (F-36)                                       | services/{automation,browser,…}; apps/desktop/src/{app,components,features} |

| Citation check                                                                                    | Result                                                                                                            |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| R1–R8 papers (ReAct, RouteLLM, FrugalGPT, LLMCompiler, MemGPT, Lost in the Middle, BFCL, τ-bench) | All titles, venues and claims check out                                                                           |
| Groq org-level limits; Gemini per project not per key; NVIDIA prototyping; MCP 2026-07-28 changes | Verified                                                                                                          |
| Hermes 64K minimum and 4–8K schema overhead                                                       | Verified, but the PDF cites main; cite pinned 04b88a4c                                                            |
| OpenRouter 50/day and 20 RPM                                                                      | Only below 10 credits purchased; omits the 1,000/day tier                                                         |
| OpenRouter: failed attempts count toward the daily cap                                            | Not found in docs: unverified                                                                                     |
| Heretic Q4 GGUF                                                                                   | Upstream is safetensors only; GGUFs are third-party (provenance hop); base is a DeepSeek-V4-Pro distill fine-tune |

C1: keep keys and adapters in the broker · Challenge PDF
A3's 'reuse Hermes provider adapters' conflicts with the PDF's own key rule. The current broker-adapter design is safer; amend A3.
C2: pin the model · Fix code
Agree with the PDF: the meta-router makes tool behavior and context unknowable (K-26).
C3: 64K local agent on 8 GB VRAM · Challenge PDF
9B Q4 plus a 64K KV cache plus the 3D UI is unlikely to fit (estimate, unmeasured). Plan M4 as standalone local chat; the agent tier is a stretch goal (K-31).
C4: single Hermes brain vs 1.5 s first token · Decision needed
Not reachable with per-turn cold start. Decide between warm Hermes and broker-direct tool-less chat (K-29).
C5: honor the M2 gate · Process
Freeze M3+ scope until the live gate passes; diagnose first (K-24, K-25).
C6: Heretic provenance · Guardrail
Hash-pinned local conversion from upstream safetensors; same broker grants; chat-only first.
Security posture
Retain
Per-launch bearer token (HMAC compare) plus origin check
Per-task inference key; grants bound to task, digest and expiry
Hermes env allowlist, temporary HOME, toolsets disabled
Irreversible capabilities typed out; ledger fails closed
Credential Manager storage; key rotation invalidates the task
Job objects, strict CSP, Hermes pin check
Fix
Hermes venv: 105 advisories (mcp 2.0.0 among them); reachability low
Model output is stored and re-injected as memory notes (stored-injection channel)
Unsalted API-key SHA-256 persisted
Cargo: 5 advisories confirmed NOT in the Windows build (native cargo tree)
Windows cache DBs tracked in git
Roadmap

| Phase         | Goal                                    | Tasks                        | Exit criteria                                                                                |
| ------------- | --------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------- |
| M3-H1 (now)   | Critical chain diagnosable and feasible | K-01 to K-06                 | 4 SDK failures gone natively; report budget test passes; every stream failure has a category |
| M3-H2         | Tool reliability and provider breadth   | K-07, K-08, K-09, K-17, K-18 | Typed tools; catalog cached; Gemini fixture accepted; 2+ routes behind consent               |
| M3-H3         | Responsiveness                          | K-10 to K-13, K-19, K-20     | Native time-to-first-token measured and improved; no 100 s drops                             |
| M3-H4 (spike) | Warm agent runtime                      | K-16                         | Second-turn startup under 1.5 s (synthetic) with isolation tests                             |
| M3-H5         | Hygiene and memory                      | K-14, K-15, K-21, K-22       | Memory provenance; repo clean; lint scope widened                                            |
| M4            | Local model runtime                     | Design after H1–H4           | Ollama or llama.cpp route measured on the RTX 4060 with Hermes context                       |
| M5            | Voice presence                          | Design                       | Streaming STT (Handy-class) evaluated; wake word                                             |

Codex handoff (Report K)

| Task | Priority | Change                                                                                                                        | Size |
| ---- | -------: | ----------------------------------------------------------------------------------------------------------------------------- | ---: |
| K-01 |       P0 | Persistent broker-owned MCP SDK session                                                                                       |    M |
| K-02 |       P1 | Separate startup deadline from per-call grant (was P0)                                                                        |    S |
| K-03 |       P0 | Per-read deadlines instead of asyncio.timeout around yield                                                                    |    S |
| K-04 |       P0 | Category for every stream end; record max_tokens and finish_reason per call                                                   |    S |
| K-05 |       P0 | Calibrated input-token bound                                                                                                  |  S–M |
| K-06 |       P0 | Report feasibility check and output floor                                                                                     |    S |
| K-07 |       P1 | Typed per-capability tool schemas                                                                                             |    M |
| K-08 |       P1 | Catalog TTL cache                                                                                                             |    S |
| K-09 |       P1 | Provider stream normalizers and fixtures                                                                                      |    S |
| K-10 |       P1 | Coalesced delta events and push notifier                                                                                      |  S–M |
| K-11 |       P1 | Retire legacy MCP bridge                                                                                                      |    S |
| K-12 |       P1 | Tauri idle-read timeout                                                                                                       |    S |
| K-13 |       P1 | Hermes session-start state machine                                                                                            |    S |
| K-14 |       P2 | Memory provenance, ranking, escaping                                                                                          |  S–M |
| K-15 |       P2 | Untrack %SystemDrive% cache DBs                                                                                               |    S |
| K-16 |       P2 | Warm Hermes runtime spike (flagged)                                                                                           |    L |
| K-17 |       P2 | Router verified-observation semantics                                                                                         |    M |
| K-18 |       P2 | Audit provider field                                                                                                          |    S |
| K-19 |       P2 | Narrow the gateway lock                                                                                                       |    S |
| K-20 |       P2 | Incremental text in tool mode                                                                                                 |    M |
| K-21 |       P2 | Coding capability breadth                                                                                                     |    M |
| K-22 |       P2 | Dead code, lint scope, benchmark output paths                                                                                 |    S |
| K-23 |       P1 | Explain the 977 ms SDK handshake; A/B test OneDrive vs local path                                                             |    S |
| K-24 |       P0 | Capture every provider_* failure reason in smoke evidence; keep error-chunk codes (sanitized)                                 |    S |
| K-25 |       P0 | Read-only task-event inspector (mode=ro) for retained stores                                                                  |    S |
| K-26 |       P1 | Pin an approved :free model; require at least 64K context and tools; record the served model                                  |    M |
| K-27 |       P2 | Collapse the three routing layers into one                                                                                    |    M |
| K-28 |       P1 | Context window from the verified catalog; calibrated token estimates; output headroom                                         |    M |
| K-29 |       P2 | Spike: warm Hermes vs broker-direct chat against the 1.5 s first-token target                                                 |    M |
| K-30 |       P2 | Add the final architecture to the repo; mark earlier docs superseded; remove empty scaffolds                                  |    S |
| K-31 |       P2 | M4 local-tier gate spec (chat vs 64K agent tier, GGUF provenance); no downloads                                               |    S |
| K-32 |       P0 | Tool-mode buffer: bound semantic output rather than envelope bytes; drop reasoning; bridge_output_limit diagnostic (do first) |    S |

Full task cards with acceptance tests in CODEX_HANDOFF.md
Verdict (Report L)
Works · Retain
Security boundary, local workflows, synthetic report path (5/5), ledger fail-closed, credential rotation, frontend and on-demand 3D, push-to-talk voice
Only appears to work · Scaffold
Multi-provider routing (one route), offline provider verification (generic fixtures), delegation (text-only), research (3 sources), memory (recalls model output)
Broken · Fix first
Live report task (leading cause: tool-mode buffer overflow, F-38); failure reasons not captured (F-33); live evidence not tied to a commit (F-39); report budget. The MCP SDK startup failures did not reproduce natively, though cold cost is still 2.3 s per call
Missing · Roadmap
Local models, general web research, cross-session memory, concurrency, wake word and streaming STT, xAI, TS/Rust coding, computer actions
Overcomplicated · Simplify
46 processes per report; two MCP stacks; per-delta commits; keyword router over one route
Prevents JARVIS
7–10 s cold-start floor per turn, no reliable live tool execution, single-task engine, no real memory, no local fallback, push-to-talk only
Next after M3 hardening
K-01 to K-06, then K-07 and the K-16 spike, then one freshly authorized live retry with per-call evidence
Requires approval
Most of these were run on 15 Nov in a scratch copy (see Native Windows verification). Still open: pnpm steps, benchmark-desktop, a run in the original location for K-23, and the live retry, which needs fresh authorization
robocopy . $env:TEMP\immortility-audit /E /XD .git node_modules
& .venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --durations=30
.\scripts\check.ps1
& .venv\Scripts\python.exe -m pytest -q -p no:cacheprovider services/broker/tests/test_standard_mcp.py services/broker/tests/test_workflows.py services/broker/tests/test_usage_ledger.py
& .venv\Scripts\python.exe scripts\benchmark-sdk-startup.py --samples 20   # run twice for n=40 p50/p95
& .venv\Scripts\python.exe scripts\benchmark-report-workflow.py --samples 10
& .venv\Scripts\python.exe scripts\smoke-research-report.py
. .\scripts\dev-env.ps1; cargo test --offline --manifest-path apps\desktop\src-tauri\Cargo.toml
cargo tree --manifest-path apps\desktop\src-tauri\Cargo.toml --target x86_64-pc-windows-msvc -i glib
& .venv\Scripts\python.exe scripts\benchmark-desktop.py --seconds 600 --output $env:TEMP\p0-idle.json
# Live retry: only with fresh explicit authorization, after K-03/K-04/K-05
& .venv\Scripts\python.exe scripts\smoke-research-report.py --live-consent
# DONE 15 Nov (t0s18): read-only store inspection; no failure reason was ever stored (see Live-run store inspection)
Get-ChildItem .cache\report-workflows -Recurse -Filter state.sqlite3 | Sort-Object LastWriteTime | Select-Object -Last 5 FullName,LastWriteTime
# then open with sqlite URI mode=ro and select task_id, sequence, body from events where body like '%provider_stream%'
Copy
Research sources
RouteLLM: learned routers, over 2x cost reduction
arxiv.org
FrugalGPT: LLM cascades, up to 98% cost reduction
arxiv.org
τ-bench: agents under 50% of tasks; pass^8 under 25%
arxiv.org
CaMeL: 77% of tasks with provable security
arxiv.org
AgentDojo: 97 tasks, 629 injection cases
arxiv.org
MemGPT: tiered agent memory
arxiv.org
Lost in the Middle
arxiv.org
Hermes delegation docs
nousresearch.com
PEP 789: yield inside cancel scopes
peps.python.org
reqwest ClientBuilder::timeout semantics
docs.rs
Gemini OpenAI-compat tool streaming index issue
discuss.ai.google.dev
Handy local STT
github.com