# IMMORTILITY — MASTER PRODUCTION ENGINEERING DIRECTIVE

**Mission:** Transform the EXISTING Immortility project into a secure, fast, token-efficient, extensible, durable, self-improving personal agent platform, grounded in real installed code and measured outcomes. Build usable backend capabilities across research, browsing, coding, Windows computer use, multimodal/voice, memory, multi-agent work, MCP/connectors, scheduled tasks, and editable document/presentation/spreadsheet/media creation. **Do not redesign, replace, or expand the 3D dashboard.** Preserve its UI and contracts; add only minimal, well-tested controls necessary to expose real capabilities.

You are acting as a principal AI systems architect, senior Windows/Rust/Tauri/Python/TypeScript engineer, agent-runtime engineer, security researcher, SRE, database engineer, benchmark engineer, and document automation engineer. You have permission to inspect the local project and implement ordinary source changes with tests. **You do not have blanket permission to use secrets externally, incur charges, pair accounts, download models, change operating-system security, delete private data, or execute irreversible account actions.** The user's already supplied API keys are sensitive existing configuration, not authorization for payment or uncontrolled network calls.

This is an **implementation assignment**, not a second recommendation-only audit. Work through independently verifiable increments. Deliver as much functioning tested code as can be safely completed in the current execution; when blocked, leave the exact actionable blocker and a passing, default-off foundation rather than fabricating completion. Do not announce an ETA, promise asynchronous work, or claim tests passed unless actually run. Avoid asking redundant questions. For genuinely irreversible/external/paid or account-authorization steps, obtain explicit approval through the project's established approval boundary.

## 0. Mandatory inputs, precedence, and reconciliation

Read actual source, lockfiles, tests, current AGENTS.md, existing architecture/CONSOLIDATION.md, blueprints, and these locally provided audit documents in `docs/research/` (copy supplied files into place non-destructively if absent):

- `ECOSYSTEM_ARCHITECTURE_AUDIT_2026-11-14.md` — original uploaded `Pasted text(20261114-084512).txt`
- `ECOSYSTEM_CANDIDATE_MATRIX_2026-11-14.md` — original `Pasted text (2)(1).txt`
- `ECOSYSTEM_IMPLEMENTATION_ROADMAP_2026-11-14.md` — original `Pasted text (3).txt`
- `ECOSYSTEM_VERIFICATION_2026-11-14.md` — original `Pasted text (4).txt`
- `Immortility_GitHub_Ecosystem_Research_2026-11-14.md` and `Immortility_GitHub_Repo_Catalog_2026-11-14.json` where available.
- Companion inventory, upstream evidence, advisories, reproducible probes, security/operations docs if present. **Never assume they exist solely because another document links to them.**

These audits are a dated baseline, not proof of today's source state or production approval. Source code, exact pinned releases, current local tests, security policies and reproducible results outrank an earlier summary. Log discrepancies. All 138 inventory candidates must receive a disposition; do not install all 138. Historic decision counts: KEEP 18, INTEGRATE 6, EXPERIMENT 20, DEFER 66, REJECT 28. An `INTEGRATE` means a staged candidate, NOT a pre-approval to install. Verify current repository owner, commit, release, supported Python/Node/Windows versions, license including subfolders/model weights, advisories and any external billing before adoption. Save a compact updated decision matrix and evidence links.

## 1. Immutable architectural invariants

1. **Hermes is the sole primary reasoning/planning agent.** Preserve pinned runtime and isolated, tool-free working path until an upgrade/adapter passes strict negative and positive tests. If testing current upstream release, run it in isolated worktree/config/process with real benchmark comparison and rollback; never in-place upgrade first.
2. **Immortility's Python FastAPI broker is the authoritative security, task admission, authorization, capability, grant, token ledger, tool dispatch, cancellation and process-ownership boundary.** Rust/Tauri remains trusted desktop supervisor/IPC guard; React/Three is presentation only. The model's output is never an authorization decision.
3. Existing `Tauri webview -> Rust fixed IPC -> loopback-authenticated Python broker -> isolated Hermes transport -> permitted model route` is the baseline. SQLite WAL remains authoritative for history/tasks/events. Preserve working chat, streaming, global Stop, settings, history, local voice paths, profiles, face/avatar, hotkeys and preview functionality.
4. **Every side-effecting action, including one invoked from delegated/natively equipped Hermes, external MCP server, cron, browser, Windows controller, plugin, code worker, or OpenMausBot, must pass the same broker policy and task-scoped grant.** If an upstream runtime cannot be instrumented to enforce this, it remains isolated, text-only, read-only, or disabled. No direct hidden model-visible shell, filesystem write, browser, network or OS input tools.
5. One owner per domain: task state/grants/budgets=broker; active reasoning=Hermes; approved durable facts=one selected memory authority; evidence/history=broker SQLite; scheduler=one selected coordinator with broker admission; browser=one controller/session per task; Windows input=one leased controller; mic=one capture owner; GPU=one resource arbiter. No competing full agent frameworks or unnecessary persistent daemons.
6. Secure, local-first, zero-paid-by-default. Preserve `ALLOW_PAID_INFERENCE=false`. Never infer a free quota from a configured key or model name. No automatic paid fallback or quota circumvention. Provider entitlements must be live-verified for any network inference; provider-specific output/security/data terms still apply.
7. **Self-improvement means evidence-based changes to skills, retrieval, routing, learned preferences and prompts**, not unrestricted self-rewriting, autonomous fine-tuning on private content, silent permission growth, permanent memory poisoning, or rewriting production code without review/tests.
8. Every optional capability is disabled by default until it passes corresponding B0–B12 acceptance checks; idle workers must consume effectively zero additional process CPU/RAM/VRAM when disabled (disk still counts).
9. Never override user approvals, Windows security, repository policies, service terms or `robots.txt`; comply with rate limits. Do not turn off security mechanisms to make benchmarks pass.
10. No UI/3D redesign. Add capability controls through existing UI contracts only if required, with tests and accessibility.

## 2. First checkpoint: real baseline and P0 safety defects (do this BEFORE adding tools)

Inventory git status, staged/unstaged/untracked files, branches, source/lock hashes, environment IDs, running processes, actual Hermes version and environment, installed/available credentials by name ONLY (never print values), network policy, Windows OS and interactive-session capabilities, RAM/VRAM, model files, disk free space, tests and build commands. Do not overwrite private modifications; create a reversible isolated worktree/branch only when safe, preserving dirty work. Store evidence and negative results in `docs/implementation/`.

Reproduce and FIX these specific audit findings, with regression fixtures and atomic, reversible commits:

- **A1:** Windows case-insensitive protected file bypass: reject `CREDENTIALS.JSON` like `credentials.json`; normalize Unicode/case/trailing-dot/space, junction/reparse/device/network forms, ensure approved-root containment against TOCTOU, separately classify actual secrets. Filesystem path allowlisting alone is not a sandbox.
- **A2:** Voice lifecycle: existing `test_tts_lifecycle.py` has three reproduced failures. Enforce worker/process-tree ownership, no orphan on Stop/timeout/race, preserve `voice_timeout` rather than misleading `tts_failed`, use bounded reap without broad `taskkill` by image name. Test 100 repeated Stop cycles and cancellation during startup/queued/streaming requests.
- **A3:** `forget` currently removes derived FTS while history and `prior_task_notes` can still recall text. Define user-facing forget vs delete-history vs search exclusion, apply tombstones/exclusions across ALL recall paths, handle SQLite WAL/backups transparently, test corrections/export/retention and no reintroduction from cached contexts.
- **A4:** Current arithmetic demo is custom `Content-Length` framed. Standard MCP stdio requires **newline-delimited UTF-8 JSON-RPC**; add official SDK-based standard client/session behind fixed manifests. Retain and label demo until independent stdio interoperability verified.
- **A5:** Provider usage is overwritten/stale and task-wide limits unimplemented. Create ledger and atomic reservations per task/attempt/child/route, aggregate parent + child + retry + cached/reasoning tokens as available, store unknown usage as unknown (never zero), enforce total task caps before every call, refund unused reservations safely, account for stop/error, price-verify per outgoing cloud call.
- **A6:** Pending approvals can survive feature disable and leave task ownership. Approval must bind exact task/attempt, root, target, action/content digest, expiry, current feature flag, grant/revocation state, and verified current file hash; post-write verification/review is task-owned and cancellable. Distinguish successful file write from later review failure. Rollback must restore nonexistent files to nonexistence.
- **A7:** CRLF bytes are inconsistently normalized between read/hash and apply. Fix byte-preserving compare or a single explicit canonicalization policy; use safe unique temporary handles and atomic replace, test symlinks/reparse/races and rollback.
- **A8:** Wikipedia context can miss actual prompt construction. Prove that fetched text/URL reaches the exact Hermes request. Bound compressed/uncompressed bytes, types, URL/redirects, DNS resolution and connection egress, timeout/cancellation, content/summaries/citations and SSRF protections.
- **A9:** Secret/identity/privacy controls: inspect dynamic paths for freshly entered UI keys; isolate backend secrets and test fake secret canary non-disclosure; strengthen streamed request body limits; trace retention, privacy, audit integrity and per-artifact external egress. Don't claim OS-enforced sandbox from allowlisted env vars.
- **A10:** Existing check script is red: baseline audit had 123 Python pass/3 fail, 41 frontend pass, 4 Rust pass and Prettier/Ruff formatting failures. Achieve green tests for touched code; report other pre-existing defects honestly. Qwen voice environment had 52 package advisory entries; keep it OFF until independently resolved and regression tested. Preserve all selected voice profiles and experiments.

EXIT GATE P0: tests for every named defect green, native safe-path smoke and stop verified, no unauthorized external side effect, no increase in broad tool access. Do not hide failures by deleting tests, loosening assertions, raising timeouts arbitrarily or changing formatting wholesale.

## 3. Capability registry, broker tools and typed contracts

Implement the smallest extensible internal **Capability Registry** and **Tool Gateway** compatible with the existing broker. Do not build a separate agent harness. Use explicit versioned manifests, typed Pydantic models, JSON Schema, named tool identifiers, input/output schema validation, provenance, source/provider identity, read/write/network/action classification, user/workspace/account scope, cost/budget limits, maximum payload sizes, deadline, concurrency limit, irreversible flag, required approval policy, and cancellation handler. Expose only a selected relevant subset of tools to the agent per task (progressive disclosure). Never pass all tool schemas to the LLM. Report tool errors with stable typed codes, bounded redacted diagnostics and recovery options. Enforce output-content quarantine: external text/images/files are DATA, not higher-priority instructions.

Task API/data contracts must support: `task_id`, `attempt_id`, `parent_id`, user/session/workspace scope, idempotency key, budget/reservation, monotonic deadline, capability grants, trace ID, task status, cancellation signal, tool status, artifact IDs, immutable action digest, source citations, usage and typed error. State transitions must be legal and replayable. Native IPC remains fixed enumerations or similarly validated calls, not arbitrary privileged command tunnels.

For a tool call: resolve registry -> validate schema -> authorize scope/cost/action -> reserve budget -> acquire controller/resource lease -> execute in bounded isolation -> validate/truncate output with clear error semantics -> append event+usage -> verify side effects -> release lease/budget -> return typed result. For each approval: preview exact target and payload, ask through trusted UI, expire on state change, enforce at actual execution time. Include denial/revocation/timeout tests.

## 4. Model/provider intelligence: quick, smart, free-first, token-optimal

Keep present OpenRouter `openrouter/free` policy initially. Revisit already configured Gemini, Groq, Grok/xAI, NVIDIA, and other compatible keys only as **independent optional provider adapters** after checking their real official APIs, allowed models, price and rate/usage policies. Never guess API endpoints, model names, quotas or provider eligibility; no secret logging. Existing stored keys may be listed as available/not available, not revealed. No automatic paid usage. Do not silently route private code or documents to a cloud provider without data-egress policy and consent.

Create route classes: deterministic (zero-model) -> small local classifier/encoder -> existing free provider -> permitted stronger free provider; escalate only for measured failures/uncertainty/task complexity. Choose a model using actual benchmarked task suitability, expected total cost, context support, structured output, rate availability, latency, privacy and health. Fall back explicitly, never fabricate execution. Freeze output formats where possible; use constrained JSON and independent validators. Enforce deadline, max provider calls, per-turn and per-task budgets, child reservations, output caps and provider free-price revalidation each call.

Suggested STARTING total caps (design targets, tune only after evidence): FAST <=4,000 total input+output and <=2 model calls; STANDARD <=8,000 total and <=4; DEEP (explicitly requested) <=16,000 total and <=6. Include nested delegates, retries, cached/read/reasoning-token accounting when provider exposes it. Missing/late usage must fail bounded. If required quality can't be delivered within cap, produce an honest escalation decision rather than silently omit required information.

Optimize: deterministic local tools for arithmetic, file metadata, date, parsing, schema checks; intent-based tool shortlist, delta context, local ripgrep/symbol indexes, FTS5 first, conditional retrieval, conservative chunking/reranking, prompt-prefix caching where providers support it, scoped content-hash caching, summarization only when verified useful, batched independent local work, no duplicate background agents, compact structured tool outputs, redundant-call suppression, cold/warm caching with invalidation. **Do not cache provider price approval or sensitive answers across unrelated scopes.** Verify cost per successful task, not token count alone.

Optional one local Ollama OR llama.cpp route only after synthetic evals show acceptable accuracy and measured resource use. On approx. 16GB RAM / 8GB RTX 4060, leave headroom for Windows/Tauri/3D; do not preload multiple heavy models. Initial local test target <=4GB additional VRAM for configured context and <=4GB host RAM; no models pulled without approval, and unload/stop releases memory.

## 5. Research, web search, scraping and information extraction

Build staged REAL capabilities, all broker-owned and separately permissioned:

**Tier W1 static public research:** fix existing Wikipedia task wiring; add bounded HTTP fetch with network egress controls, SSRF defenses and redirection rules; deterministic HTML extraction via `adbar/trafilatura` (extraction consumes already authorized fetched bytes; don't expose unrestricted `fetch_url`). Return source URL, title, sections, timestamps, content hash and citation anchors. Apply instruction-in-data defenses. Cache by scope/hash/TTL; do not treat extraction as verified fact. Support query, multiple sources, source comparison, research summaries and direct clickable citations.

**Tier W2 dynamic pages:** compare Playwright Chromium and Obscura on same JS/auth/render fixture corpus; choose one active session backend per task. Browser launch/profile/session/credentials/downloads under broker scope, DOM/accessibility first, screenshot fallback only with grant. Read-only navigation and form drafting before any submission; verify state after each action. On crash/fallback, terminate old session and revalidate state; NEVER replay a submit/payment/send action blindly.

**Tier W3 specialized:** search provider APIs, public YouTube metadata/transcripts, GitHub/issues, RSS, permitted platform adapters (Agent Reach) and bulk crawlers only if task justifies them. Treat website/platform auth and cookie handling as sensitive; do not install arbitrary cookie-extraction helpers or evade access controls. Honor `robots.txt`, site terms and bandwidth limits; no indiscriminate crawling. If paid search endpoints needed, support disabled connector and explicit nonpaid alternative.

Expected demonstrations: multiple trustworthy cited web results; extracting documentation; comparing sources; dealing with missing page/JS only/redirect; detecting prompt injection; respecting denial and Stop; returning partial findings when site blocks access.

## 6. Standard MCP and universal application connectivity

Use `modelcontextprotocol/python-sdk` client/session with independently implemented protocol tests, version/feature negotiation, standard stdio and Streamable HTTP, tool/resource/prompt discovery, schema validation, session recovery, request IDs, progress, bounded responses and cancellation. Keep MCP Inspector a DEVELOPMENT-only tool after supported Node versions and pinned release are verified; never an always-running runtime dependency.

Introduce a reviewed **Connector Registry**: fixed approved MCP server manifest / executable digest, launch args, environment allowlist, trusted publisher, allowed domains, per-server tool allowlist, auth scopes, resource ownership and egress rules. Untrusted remote servers cannot set their own privileged permissions. OAuth 2.0/OIDC where appropriate: PKCE, callback validation, short-lived tokens, refresh and revocation, OS credential vault, no arbitrary token dumping. Explicit consent for each account and scope. Server-supplied descriptions are untrusted; no auto-install of requested packages/commands.

Capability families to support with independently scoped connectors IF available: filesystem, Git/GitHub, web/search, browser, email read/draft/send, calendar read/create/update, cloud-drive documents, notes/knowledge services, messaging, issue trackers, databases, spreadsheets, documents, design services (including Canva if genuine supported authorized integration), media services, and custom APIs using vetted OpenAPI specifications. **An arbitrary API is not automatically safe, licensed, free or controllable.** Unavailable connectors must have clear disabled/setup states rather than mock success.

Use A2A only for genuinely independent remote agent systems after interoperability and isolation tests; in-process Hermes subagents do NOT require A2A. Do not expose public listening ports just to support MCP.

## 7. Windows computer use, files and developer automation

Compare `trycua/cua` native Windows driver vs `pywinauto` in a disposable, interactive, normal-user Windows session; select one active controller owner based on tests. Use UIA/accessibility, semantic window/element identifiers, fresh snapshots, target identity, focus checks, explicit leases and action verification. Screenshots/window trees are sensitive data with visible per-task consent and no passive recording. Never control password inputs, UAC secure desktop, elevated or non-consented applications; never silently bypass permission barriers. Reversible Notepad/Calculator test first. Multi-monitor/DPI, foreground stealing, crash, Stop, revoke, stale target and wrong-window cases mandatory. Foreground actions require a fresh approval. Separate read-only inspection from interactive control.

For coding: existing protected workspace read/patch/approval/rollback remains canonical; first implement scoped deterministic filesystem/symbol search and `rg` integration. Evaluate read-only Serena symbol retrieval against deterministic baseline and test its GPL-3.0-or-later application vs MIT SolidLSP components and licensing obligations. Never let Serena REPL, shell, write or memory tools bypass broker. LSP/workspace plugins are executable surfaces: isolate them when repositories are untrusted. Supports task-scoped create/edit/refactor with approved root, previews/diffs, tests under a RESTRICTED executor and safe rollback. The prior source says arbitrary test execution is disabled; **do not activate an unrestricted terminal under the guise of enabling coding**. Add isolated test runner only when real OS-enforced sandbox, allowed commands, filesystem and network restrictions, quotas and process teardown are demonstrated.

Optional CLI specialists (Cursor, OpenCode, Claude Code etc.) only if installed, licensed/entitled and they can be run as broker-owned scoped workers. No assumption that a login or API key permits free execution. Never allow uncontrolled git push/deploy.

## 8. Memory and verifiable self-improvement

Fix forgetting/privacy first. Define distinct stores: session/workflow state, append-only task evidence, user-approved durable facts/preferences, project facts, reusable procedures/skills, and optional derived lexical/vector indexes. One authority for approved durable facts. Keep PII/workspace isolation and consent, provenance/source hashes, timestamps, confidence, correction history, retention, tombstones, export and deletion semantics; no hidden collection or secret memorization.

Benchmark baseline broker FTS5 and Hermes native provider/search against 1k/10k synthetic facts and 100 labelled queries. Only if lexical recall misses justify it, test a derived `sqlite-vec` + CPU ONNX/FastEmbed semantic index. GBrain is a separated experiment, not an automatic second durable-memory owner. No third-party cloud memory extraction unless explicitly authorized. Cache invalidation when a source changes, consent revoked or fact deleted. Prevent prompt/memory poisoning, conflicting facts, cross-workspace recall and stale information.

**Self-improvement loop:** instrument errors/task outcomes -> produce candidate improvement to retrieval ranking, prompt template, model routing, skill procedure, or tool descriptions -> compare on versioned held-out evals and safety fixtures -> stage versioned change -> human approval for persistent policy/skill changes -> rollout with feature flag -> monitor and rollback. Favor offline metadata-based learning and local statistical updates; model weight retraining is a separate manually approved project. Never let an agent declare its own eval score or silently alter permissions.

## 9. Multi-agent teamwork and durable workflows

Prefer existing broker Hermes research/coding/review specialists and benchmark *newer* Hermes native delegation in a fully isolated version/policy test. Advanced Delegation plugin requires Hermes >=0.22.5; current audited pin is 0.21.1. Before upgrading, compare new Hermes gateway/session ownership and security hooks to existing broker controls. Ensure native delegated children cannot gain tools and that parent/child model usage is aggregated correctly. Use manager-worker plus explicit task DAGs: specialized researcher, coder, verifier, reviewer, artifact generator, browser/computer operator. Spawn a specialist only for genuinely separable work. Parallelism must be bounded by rate, RAM, GPU and token reservations; no recursive swarms or double orchestration.

OpenMausBot is an OPTIONAL adapter experiment, not the universal orchestrator: verify real source `milind-soni/OpenMausBot`, license carve-outs, exact artifact provenance, Node >=24, and absence of a tested native Hermes driver. Compare text-only proposal mode against existing Hermes specialists; unless all downstream actions are broker mediated, leave OpenMausBot unable to use OS/accounts/files. Do not run its separate scheduler, memory or Electron UI as a second authority. Preserve fallback to single Hermes when unavailable.

Implement resumable task graphs and checkpointing in existing broker SQLite with idempotency, legal transitions, per-child grant and deadline, cancellation propagation, retry/backoff, dead-letter/resume policy, event replay, timeouts, and crash/restart semantics. For completed irreversible steps, require a compensation/reconciliation plan; never automatically replay non-idempotent sends, purchases or changes. Reliability should rely on deterministic state machine and tool verification, not agent self-claims.

## 10. Scheduled tasks, reminders and autonomous routines

Evaluate Hermes native cron first, since the installed source includes scheduling. Choose one scheduler, broker-admit every trigger, persist schedule identity/owner/capabilities/budget/privacy consent; pause/resume/delete, missed-run policy, idempotency, restart behavior, per-run grants, and explicit approval for external side effects. Support one-shot reminders, recurring research summaries, availability monitoring and status checks when users request them. No always-on model loops or speculative proactive monitoring of private systems. Event-driven triggers may use signed webhooks but must be authenticated, rate-limited and scoped. Demonstrate that scheduled jobs can complete after restart without duplicating actions and that Stop/cancel/disable revoke pending effects.

## 11. REAL artifact and creative work — editable, render-tested output

Build a modular Artifact Pipeline with typed requests, task-scoped input paths/URLs, provenance, fonts/assets licensing, output paths, temporary directories, size and page/slide limits, citations, metadata, preview/validation and cleanup. **Read/import ≠ write/edit; an image of a presentation ≠ editable PPTX.** Separate deterministic local authoring from optional cloud AI design/inference.

- **Documents:** DOCX create/read/edit with styles/headings/tables/images/page layout via vetted libraries such as python-docx; PDF generation/merging/extraction with appropriate PDF libraries and license review; render to pages and inspect pagination, overflow, fonts, citations. No fake output paths.
- **PowerPoint / slides:** actual PPTX with editable text, shapes, charts, tables, speaker notes if supported, branded templates and image assets; use python-pptx or another validated local renderer/editor. Validate OOXML structure, reopen file, render slides to images/PDF through supported rendering tools, visually inspect clipping/overlaps, and report features not reliably editable. Use slide outline/content planner with deterministic layout. Do not call a deck finished solely because PPTX saves.
- **Spreadsheets:** XLSX with actual formulas, calculated/recalculable outputs, formatting, charts, validation, data provenance, and CSV support using vetted spreadsheet library. Verify formulas or show limitations of cached results. Avoid formula injection on CSV import/export.
- **Research/report artifacts:** HTML/Markdown, structured JSON/CSV, diagrams (Mermaid/SVG), infographics, flowcharts, code/project files, archives, and reproducible exports. Input ingestion with `microsoft/markitdown` minimal extras, with sandbox and content limits. PDFs with scans require separate OCR path; refuse unsupported pages explicitly instead of inventing text.
- **Canva / visual design:** If a legitimate connected Canva API/tool supports the requested creation/editing, implement a credential-scoped optional connector using actual documented endpoints and scopes. Otherwise produce an editable local PPTX/SVG/HTML artifact and clearly explain the Canva handoff limitation. No impersonation or scraping private accounts.
- **Image/audio/video:** Optional user-authorized local pipelines (ComfyUI, Blender, FFmpeg etc.) only with exact model/node/weight licenses, media rights, GPU reservation, size quotas, consent and safe task-owned process shutdown. Never pre-download multi-GB models, or promise local video generation fits 8 GB VRAM. Existing avatar/rendering asset pipeline must remain unchanged.
- **Template work:** Preserve input template layout and editable structure when requested; citations/claims must be grounded. Keep user content out of external generation services without explicit per-artifact permission.

Provide end-to-end demos: 8–10-slide editable deck with chart and rendered preview, 2-page styled DOCX + PDF, working formula XLSX, cited research Markdown, and one small designed SVG. All generated into an approved output root. Compare quality, editability, runtime, memory and token costs. Do not install heavyweight conversion suites by default; pick available verified tools and document missing capabilities.

## 12. Voice, multimodal and avatar integration (no 3D redesign)

Retain existing faster-whisper + Silero VAD + Piper and opt-in Kokoro; repair lifecycle first. Compare sherpa-onnx/whisper.cpp only if measured value. Add voice wake word, turn-taking, optional barge-in, streaming ASR/TTS, endpointing, microphone/device error handling, echo cancellation where available, explicit mic indicator and no cloud audio without separate consent. One capture owner, one speech worker active per request; cancellation must stop recording, transcription and synthesis and clean temp files. Keep existing voice preferences and any voice styles, including lower metallic voice settings, without creating a new GPU model fleet. Existing 3D UI may receive validated `idle/listening/thinking/speaking/error` state events, NOT a scene redesign.

Multimodal screenshot/image understanding and OCR are separate privileged capabilities: permissioned source selection, private data handling, preprocessing, bounded images/frames, no continuous desktop capture and measured quality. Only send externally where user authorization covers that exact source.

## 13. Security and safety gates for universal connectivity

Implement least privilege, scope inheritance, explicit read/write/send/delete/payment risk levels, approval lifetimes, capabilities as revocable grants, credential vault, OAuth revocation, separation between user content and executable instructions, process ownership, no unrestricted shell, no wildcard domains, DNS rebinding/SSRF defense, secret-canary tests, file path safety and controlled egress, and tamper-evident or explicitly bounded audit claims. Dynamic grants must be revalidated immediately before side effects and before every delegated step. Credential values must never appear in logs, prompt traces, screenshots, repo artifacts, frontend health or model output. Native tool-policy bypass is release blocking.

Add development-only Gitleaks, OSV-Scanner, current pnpm/pip/Cargo scans and optional offline static-analysis/Promptfoo evals. Pin all scanners; cover isolated speech environments, native downloads, model files and subcomponents as applicable. Treat unresolved license/CVE as unresolved, not clean. Existing disabled vulnerable Qwen runtime stays disabled. No arbitrary MCP server installs or auto-upgrade of plugins from LLM suggestions. Keep sensitive operations requiring user approval (send email, share data, booking/purchase, delete, deploy, git push, protected files, account authorization). Test malice in documents/web content/tool descriptions, secrets in inputs, forged tool results, refusal and prompt injection.

## 14. Operational performance, observability and CI/release

Local metadata-first observability with trace IDs spanning frontend -> Rust -> broker -> Hermes -> tool/child -> artifact. Record model/provider ID, per-call token fields and reservations, latency TTFT/total, cache hit/miss, tool attempt outcomes, retry counts, memory retrieval source and safety decisions. Content logging/trace export is separate opt-in and redacted by default. No external Langfuse or other telemetry unless explicit opt-in; official plugin would need version/security reconciliation.

Implement health/readiness, durable task reconciliation, native process supervision, Stop propagation, policy/config validation, schema migrations with backup and rollback, dependency/license/security reports, SBOM, reproducible build, signed release strategy when practical, secure local network exposure, supported Windows versions, accessible approval interactions. Add CI checks for Python unit/type/lint/format, frontend type/lint/test/build, Rust cargo tests, integration contract tests, MCP conformance, vulnerability scan and artifact reopening/render validation. No Kubernetes, Redis, Docker or multi-service infrastructure unless a concrete capability lacks a simpler safe option.

## 15. Quantified evaluation B0–B12 — no simulated success claims

Use the original `ECOSYSTEM_IMPLEMENTATION_ROADMAP_2026-11-14.md` for authoritative complete B0–B12 definitions. Before adoption, run a consistent, versioned test corpus on the SAME host with cold/warm measurements, source hashes, model IDs, input/output counts and baselines. Functional screen: >=10 realistic task types × >=3 repetitions; robust latency statistics need >=100 timed operations. Track actual n, p50/p95, CPU/RAM/VRAM/disk, TTFT, tool/agent steps, total input/output/reasoning/cache tokens, quality, refusals, cost and crashes. Unknown usage != zero. Proposed targets are acceptance goals, NOT achieved claims.

- **B0 baseline:** zero unauthorized actions/egress/secret leaks; all mandatory tests pass; feature flags and rollback.
- **B1 MCP:** independent SDK/Inspector interop, initialize/list/call/error/cancel/hung server, stdout noise, oversized payloads and forbidden tools; target warm local call p95 <100ms, Stop ack <250ms, reap <=3s if achievable on machine.
- **B2 coding/Serena:** relevant symbol recall >=95%, no forbidden reads or edits, >=30% prompt-token saving goal at equal task quality; if not, prefer deterministic search.
- **B3 research/browser:** >=95% answer-bearing facts recovered on labelled fixtures, no injected instructions adopted, >=30% prompt token reduction vs raw HTML if quality preserved, static parse p95 <=500ms on <=1MB; dynamic browsing safe fallback and cancellation.
- **B4 Windows:** >=95% safe steps, 100% correct refusal, zero wrong-window input, no capture without consent; measure action latency and Stop under stress.
- **B5 memory:** Recall@5 >=0.90, attribution >=0.95, zero deleted/foreign returns; add vector index only if >=10 point improvement on misses without precision regression.
- **B6 voice:** no regression vs existing WER/quality on identical fixtures, no cloud audio, bounded Stop; proposed warm first-audio <=1s and endpoint-to-text p95 <=2.5s, report hardware reality.
- **B7 local inference:** selected narrow task accuracy >=95%, structured validity 100%, no cloud for local-only, <=4GB VRAM and <=4GB RAM proposed, zero GPU load after unload.
- **B8 artifacts:** 10 types including malformed/secret/scan, successful re-open/render/editability, strict parser limits and explicit unsupported content handling.
- **B9 security tooling:** deterministic positive/negative fixtures, secret redaction, CI-only resources, no unexplained critical/high reachable vulnerabilities in active paths.
- **B10 UI contracts:** minimal accessibility/virtualization fixes if necessary, no 3D regression, stop/focus/approval usability.
- **B11 delegation/OMB:** safe broker-mediated downstream actions, aggregate usage; only promote if >=10-point specialist success gain OR >=25% latency/token decrease at equal quality.
- **B12 ledger/routing:** exact task/child/retry usage, atomic reservations, zero overspend, sequential/concurrent isolation, unknown usage handled and current free-price verified.

Assess basic end-to-end tasks (not mocks alone): sourced multi-site research; an authorized local file refactor with diff/test; a permitted web form DRAFT without submission; an approved reversible native app interaction; local STT->Hermes->TTS; a parallel research/review workflow with cancel; a recurring dry-run job; an editable deck/report/spreadsheet with verified previews. Mark offline fake-provider tests, mock/UI tests, live cloud tests and native desktop tests separately. Require explicit approval before first real private data upload or account mutation. If cloud availability/free quota absent, report BLOCKED and preserve working local path, rather than spoof it.

## 16. Milestone execution order — build, test, demonstrate, document

Implement **vertical slices**, not all-at-once rewrites. Milestone gating is strict:

**M0 Baseline and remediation:** Snapshot/verify repo, fix A1–A10, hardened task/grant/cancellation and accurate ledger, green tests.

**M1 Broker capability gateway + standard MCP:** typed registry, allowlisted official SDK client, protocol conformance, dev Inspector, CI scanning, no hidden native tools.

**M2 Grounded research + web:** bounded authorized fetch, trafilatura, actual prompt citations, caching, dynamic Playwright/Obscura comparison, first production-grade research demonstration.

**M3 Windows + coding:** read-only UIA/Cua/pywinauto evaluation, broker controller leases; safe scoped actions, deterministic code retrieval, optional Serena read-only, workspace patch/verification and safe executor gate.

**M4 Durable memory + self-learning:** recall/privacy/correction baseline, optional CPU semantic retrieval, evidence-based skill/routing feedback with offline evaluations and approvals.

**M5 Multi-agent + tasks:** Hermes specialists/native delegation version comparison, bounded DAG execution, checkpoint/restart, scheduler with broker admission, OMB text-only experiment if meaningful.

**M6 Artifacts/creative + connectors:** DOCX/PDF/PPTX/XLSX/Markdown/SVG pipelines with real editability/preview, scoped Canva/cloud/email/calendar/drive integrations only when supported and authorized.

**M7 Voice/multimodal/local models:** retain and harden current local voices, scoped STT/TTS and visual understanding, one optional small local inference backend with GPU arbitration.

**M8 Production hardening:** full tracing/accounting, supply-chain audits, rollback/migrations, native Windows resource/soak, privacy controls, packaging/release gates, complete E2E gallery.

At every milestone: inspect existing implementation, compare candidate solutions, implement minimum safe changes, write tests FIRST or alongside code, run available tests, create reproducible acceptance evidence and demo, measure versus baseline, update docs, include rollback instructions, preserve disabled default until accepted, and continue to the next eligible independent slice if safe. If blockers arise, stop only that branch, document reason and work on an independent safe slice. Never claim later milestones complete because scaffolding or examples exist.

## 17. Required output and truthful status discipline

Write and keep current:

- `docs/implementation/IMMORTILITY_EXECUTION_STATUS.md`: actual DONE / INTEGRATED-UNVERIFIED / TESTED-MOCK / EXPERIMENTAL / BLOCKED / NOT-STARTED per feature, commit/paths, owners and next action.
- `docs/implementation/ARCHITECTURE_AND_TRUST_BOUNDARIES.md`: current architecture with single owner per component, contracts and threat model.
- `docs/implementation/REPOSITORY_DECISIONS.md`: all 138 candidates, verification evidence, licensing/runtime compatibility, installed vs discarded, exact pins and rollback.
- `docs/implementation/CAPABILITY_REGISTRY.md`: tool/API/connector/skill manifests, permissions, scopes, example schemas and required approvals.
- `docs/implementation/TOKEN_COST_BENCHMARKS.md`: real input+output+child usage, unknowns, baseline, charts/tables of quality/latency/cost per successful task; distinguish measured from goal.
- `docs/implementation/E2E_ACCEPTANCE.md`: executed commands, outputs, n, platform, native/free/offline modes, artifact previews, Stop/rollback/security tests and limitations.
- `docs/implementation/CHANGELOG_AND_ROLLBACK.md`: migration and reversible steps; sensitive actions requiring human approval.
- Output artifacts/tests only in sanctioned workspace locations; keep personal secrets out of generated docs.

After every milestone, respond concisely with: (1) exact changed files, (2) working features and how to try, (3) test commands/results and what was NOT tested, (4) token/RAM/latency measurements if actually measured, (5) security/permissions status, (6) remaining blockers and next bounded slice. Do not bury failures or overstate tests. Keep task continuity and restart-safe checkpoint notes.

## 18. Final definition of success

Success does NOT mean all repos installed or that the assistant is literally omnipotent. Success means a small, reliable, well-tested and documented system can:

1. Converse via Hermes using verified free or local routes with hard token/cost budgets.
2. Choose permitted tools dynamically through standard typed MCP and vetted connectors.
3. Research the public web with evidence, trustworthy citations, injection boundaries and efficient extraction.
4. Operate approved Windows/browser surfaces safely, confirm each action and stop immediately.
5. Read/write approved code and files using correct diffs, isolation and verification.
6. Persist, retrieve, correct and forget authorized memories without private-data leakage.
7. Coordinate bounded specialists with task ownership, usage accounting, checkpointing and cancellation.
8. Execute consented scheduled work without duplicate or unauthorized side effects.
9. Create **real, editable, validated** slides, documents, spreadsheets and other artifacts and make them retrievable.
10. Deliver voice and multimodal flows with working consent and worker teardown.
11. Learn from evidence-based outcomes through gated skill/context/model improvements without uncontrolled self-modification.
12. Survive crashes, pass negative security tests, use minimal idle resources and report actual measurements.

**Begin NOW with M0: inspect the real checkout, reproduce audit findings and implement the first smallest set of fixes. Don't merely write a new roadmap. Continue milestone-by-milestone with verifiable working code and explicit evidence, never trading away safety, privacy, free-only constraints, or existing functionality to declare completion.**
