# Prioritized implementation roadmap and acceptance benchmarks

**14 November 2026 — proposals only.** This audit enabled nothing. Follow the existing P0–P8 roadmap and [consolidation rules](../architecture/CONSOLIDATION.md); complete the current preview's acceptance gates before later-phase capabilities. Preserve working chat, local voices, profiles, history, settings, face and UI controls. The [architecture audit](ECOSYSTEM_ARCHITECTURE_AUDIT_2026-11-14.md) contains evidence and current defects; the [138-row matrix](ECOSYSTEM_CANDIDATE_MATRIX_2026-11-14.md) is the complete disposition register.

## Ranked shortlist

Rank reflects expected capability/efficiency gain after security prerequisites, not GitHub popularity. Effort is an unmeasured engineering estimate in focused developer-days, excluding approvals, hardware variability and upstream fixes. Every change is a small vertical slice with rollback and feature flags.

| Rank | Action / repository | Decision and phase | Why this comes first | Dependencies / effort estimate | Acceptance |
|---|---|---|---|---|---|
| 0 | Fix existing filename, approval, CRLF, Stop and forget defects | Existing-code repair, P0/P1/P2 | New tools would inherit these failures | No new runtime; 3–6 days across separate fixes | B0, regression probes, 100 repeated Stop cycles |
| 1 | Correct task/attempt token ledger in existing SQLite | Existing-code repair, P0/P1 | Needed to prove budgets or token savings | Fix task ownership/grants; 1–3 days | B0, B12 |
| 2 | modelcontextprotocol/python-sdk | INTEGRATE, supporting P0 contracts then P3 tools | Fixes demonstrated interoperability gap with maintained protocol lifecycle | Pin compatible release; isolate if broker pins conflict; 1–3 days | B1 |
| 3 | gitleaks/gitleaks and google/osv-scanner | INTEGRATE, P0 development/CI only | Cover source secrets, multiple lockfiles, native/integration dependency gaps | Existing audits retained; verified Windows binary or supported CI worker; 1–2 days | B9; zero runtime footprint |
| 4 | oraios/serena read-only retrieval | EXPERIMENT, P5 coding; earlier isolated evaluation only | Highest plausible coding-context improvement over first-20-files dump | B0+B1; isolated pins, exact tool inventory and GPL review; 2–4 days | B2, no writes/REPL/shell/memory |
| 5 | adbar/trafilatura | INTEGRATE, P3 research | Small deterministic content extraction; avoids browser/model use on static pages | Repair current web prompt wiring; bounded broker fetch; 1–2 days | B3 |
| 6 | trycua/cua driver versus pywinauto | EXPERIMENT, P3 | Adds missing native Windows awareness/control without second planner | B0+B1, interactive session, controller lease, consent; 3–6 days | B4; read-only inspection before any input |
| 7 | Hermes-native memory baseline; optional sqlite-vec + FastEmbed | KEEP owner / EXPERIMENT, P4 | Better recall only if current lexical retrieval demonstrably misses relevant facts | Forget/provenance/consent first; one derived index; 2–5 days | B5 |
| 8 | Current faster-whisper/Piper/Kokoro lifecycle; sherpa-onnx or whisper.cpp comparison if needed | KEEP / EXPERIMENT, P2 | Existing local speech is substantial; extra capture systems add little | Resolve Stop failures, cold/warm and physical mic benchmark; 2–4 days | B6 |
| 9 | One Ollama OR llama.cpp small-model route | EXPERIMENT, later capability/cost slice | Can avoid cloud for private simple tasks if quality is adequate | New local route contract, model digest/license, GPU reservation; 2–4 days | B7, B12 |
| 10 | microsoft/markitdown minimal local worker | INTEGRATE, P6 | Deterministic document preparation before cloud reasoning | Approved files, per-artifact egress consent, parser containment; 2–3 days | B8 |
| 11 | modelcontextprotocol/inspector | INTEGRATE, development tool with B1 | Independent MCP checks, no application service | Patched supported Node line first; isolated dev install; 0.5–1 day | B1, credentials in memory for tests |
| 12 | Optional OpenMausBot text-only adapter | EXPERIMENT, P5 | Useful only if it beats existing native Hermes specialists without widening privilege | Reconcile source/license identity, supported Node >=24, per-action control; 3–8 days | B11; no account pairing/dispatch until gated |

There are **six INTEGRATE candidates**: Python MCP SDK, Inspector, trafilatura, MarkItDown, Gitleaks and OSV-Scanner. This is a staged shortlist, not six immediate installs. Twenty candidates are conditional experiments; alternatives in the same family compete, rather than all being installed. Sixty-six are deferred, 28 rejected as runtime additions, 18 retained in existing roles.

## Ownership and dependency contract

| Capability | Single authority | Optional dependency role | Prohibited duplication |
|---|---|---|---|
| Planning and model reasoning | Hermes | Native skills/delegation after exact version and policy tests | LangGraph/CrewAI/PydanticAI as second universal planner |
| Permissions/lifecycle/cancellation | Broker | SDK client, approved worker proxies, task-scoped grants | Runtime/plugin decides its own elevated approval or runs hidden side effects |
| History/events | Broker SQLite WAL | Derived recall index, backup snapshot | Two writers mutating the same database or independent conflicting task states |
| Approved durable facts | One selected owner after P4 comparison | Hermes provider OR chosen alternative; derived indices rebuildable | Automatic simultaneous Hermes/GBrain/Mem0 fact extraction |
| Schedules | Hermes cron candidate, broker admits each execution | Persisted trigger identity, revoke/reapprove policy | APScheduler, OMB routines and n8n all firing the same job |
| Browser | One task-bound controller session | Playwright baseline/Obscura alternative after Windows gate | Two controllers click the same profile; silent replay after fallback |
| Windows control | One broker-issued controller lease per task | Cua driver OR pywinauto behind policy | Parallel input stacks, direct Hermes/OMB bypass |
| Voice capture | Current broker voice lifecycle | Selected ASR/TTS backend under one request/Stop contract | Handy plus broker both capturing, unrelated wake-word listeners |
| GPU allocation | Broker resource arbiter | One active heavyweight LLM/TTS/vision/media worker | Warm GPU models whose combined VRAM leaves no 3D/OS headroom |
| Telemetry | Local metadata and usage ledger | Optional OTel export later | Multiple external trace services capturing user content |

## Ordered implementation slices

### Slice 0 — P0/P1/P2 closure (do next after audit approval)

Repair A1–A10 as individually reviewable changes, starting protected filenames and owned cancellation. Add regression tests for casing/CRLF/forget/approval revocation and cross-task grant isolation. Correct aggregate accounting and task-budget metadata; reset per-task state. Resolve existing formatting failures. Preserve disabled code execution and all Hermes native side-effect tools. Reproduce existing real-Hermes offline demonstrations and current Windows native smoke; only an explicitly consented live-provider smoke can prove cloud eligibility.

Exit: complete existing agreed check script is green; all new negative cases pass; 100 fixed-child Stop cycles leave no owned descendants; history/voice assets preserved. No upstream runtime upgrade is bundled with these repairs. Risk: taskkill behavior may vary under job objects and loaded systems; use owned process handles rather than broad process-name termination.

### Slice 1 — P0 supporting MCP contract and security checks

Introduce a reviewed SDK adapter alongside the labeled arithmetic demo; prove independent standard stdio interoperability before moving the demo to it. Do not enable arbitrary external servers or Hermes native MCP tools. Add fixed launch manifests, schema/output byte limits, request deadlines and cancellation. Inspector remains dev-only, after its Node requirement is met. Add redacted secret and dependency scans covering **all** lockfiles/environments; archive SBOM/license reports without secrets. Pin exact commits/digests for tools and CI actions.

Exit: B1+B9 pass and rollback restores prior demo behavior. Risk: SDK/Inspector major versions and transitive Pydantic/Starlette/Node requirements can conflict; choose a supported release or isolate, never force the resolver.

### Slice 2 — P3 grounded public research

Repair Wikipedia data-to-prompt wiring first. Then fetch bounded public HTML through the broker and hand bytes to trafilatura. Return relevant sections with URL, title, extraction version, content hash and retrieval timestamp; treat all page text as data. Cache public extraction, not indefinitely cached price approval. Add a single browser backend only when static extraction cannot fulfill a test task, with explicit Windows 10/11 support decisions and no credential-profile reuse by default.

Exit: B3 passes; citation-bearing answers use actual supplied evidence, no unauthorized domain/local-IP access, and cancellation is bounded. Risk: extraction can omit tables/caveats; quality gates outrank token reduction. Obscura fallback must terminate the original session and revalidate navigation/action state, not blindly replay form actions.

### Slice 3 — P3 Windows awareness, then scoped actions

Honor prior consolidation by checking OpenMausBot's broker-policy contract as a comparator, without assuming its download page establishes host-control safety. If missing/blocked, document that reason and evaluate Cua's read-only window/UIA inspection in a disposable interactive test session. Compare pywinauto on the same apps. Pick one owner only after B4; capture is task-scoped with a live indicator. Then allow a small action enum with exact argument previews, target identity/freshness and per-action approval. Keep OS shell/code tools disabled.

Exit: inspection and a small reversible app workflow pass both Windows versions; no input on focus/target mismatch; Stop/revocation halts further actions. Risk: UAC/secure desktop/elevated apps and background delivery vary; fail closed rather than elevate or fall back to coordinates silently.

### Slice 4 — P4 memory and P5 coding intelligence

Implement recall exclusion, durable-fact consent, provenance and correction before adding embeddings. Benchmark Hermes-native memory/provider behavior with isolated nonpersonal fixtures against current FTS. If semantic misses justify it, add a **derived** sqlite-vec index and small CPU FastEmbed encoder without creating a fact owner. Test GBrain separately only if native semantics still fail; one writer, opt-in capture, no remote synthesis/relay by default, migration/export and rollback proof required.

For P5 coding, compare bounded filename/content search first, then read-only Serena symbols. Return only relevant TS/TSX/Python/Rust context; route proposals through existing approval/diff path. A language server can execute workspace plugins; tool-name filtering alone is not an OS boundary. Use reviewed server configuration, sanitized evaluation workspaces and an appropriate restricted execution boundary before untrusted projects. Keep arbitrary test execution off until Windows isolation is actually established. Cursor's official CLI is a later specialist adapter, with subscription/timeout/worktree and diff/test evidence; do not treat its login as a provider key.

Exit: B2+B5; no unexplained recall regression, no cross-workspace leak, no direct Serena edits/shell/memory. Risk: GPL distribution, native provider hooks and LSP project execution require release-specific review.

### Slice 5 — P2 performance continuation and optional local inference

Keep current speech choices; unify worker request IDs, cancellation, process ownership, temp-audio cleanup, cold/warm status and unload policy. Measure real push-to-talk only with explicit consent. Compare sherpa-onnx or whisper.cpp one at a time if accuracy/cold latency is inadequate. Do not promote Qwen from the historical vulnerable environment or reference XTTS without new security/license/native tests.

Evaluate one pinned local 1–4B quantized model using Ollama OR llama.cpp only after accurate accounting. Tiny classification/arithmetic/date conversion remains deterministic; no LLM needed. Keep cloud inference free-only and refuse unsupported local tasks rather than fabricate quality. Disable any cloud model pull/execution defaults and prevent local API exposure to LAN/untrusted web origins.

Exit: B6+B7+B12, at most one heavyweight GPU reservation; all original voice profiles preserved. Risk: a “small” model's weights exclude KV cache and 3D overhead; quantized model quality may be inadequate.

### Slice 6 — P6 artifacts/media; P7 scheduling; P8 release

Begin P6 with minimal MarkItDown local extraction and source anchors. Add authoring/render verification separately; extracting text is not editable document creation. Add PDF OCR or ComfyUI only for actual tasks with parser containment, frozen custom nodes, output-root grants and model licenses. Keep existing Blender build pipeline; no agent plugin needed for ordinary chat.

P7 evaluates Hermes cron and native delegation under broker admission/reservation contracts, with restart requiring renewed approval for irreversible steps. No competing scheduler. OMB remains optional unless B11 demonstrates a material win. P8 adds signed packaging/updater, reversible migrations, consent/data removal, native long-soak and accessibility/resource testing. Current face/dashboard visuals do not satisfy these release gates by themselves.

## Benchmark protocol common to every proposed integration (B0)

Use a fixed, versioned corpus and task IDs with expected outcomes, input hashes, permitted outputs/domains, exact runtime/commit/model/license identifiers and feature flags. Compare baseline and candidate on the same host, power plan, concurrency, corpus and model route. Record cold and warm distributions separately, other GPU processes, CPU/RAM/VRAM, disk before/after and time to first usable result. Use 10 realistic task types × at least 3 repetitions for functional screening; **>=100 timed operations** for meaningful p50/p95 comparisons, report n and failures. Three historical source-protocol runs do not establish p95.

Record total parent+child+retry prompt/completion/tool tokens, cached/read/reasoning fields when available, actual model identity where provider reports it, wall time, artifact correctness and stop/recovery results. Missing usage is unknown, not zero. All mandatory safety fixtures and existing tests must pass: do not accept a nominal “<=1% regression” if it hides a failing critical test or one test in a small suite. For capability tasks, candidate success must be no lower than baseline; savings/latency gains cannot come from dropping requirements.

Common security tests: tool off, unregistered tool, mutated schema, output injection, denied path/domain, loopback/private IP, secret canary, stale approval/target, revoked grant, over-budget call, process crash, network outage, malformed/oversized output, Stop before first response and during an active action. Zero unauthorized reads/writes/capture/egress; no automatic paid fallback. Capture consent must be visible and task scoped. No live secrets in fixtures or exported reports.

Common rollback: default-off flag, prior lockfile retained, versioned configuration/database migration, export/backup before owner changes, no cleanup of private profiles or historic evidence. Set one concurrent optional model job initially; unload on expiry. Targets below are **proposed**, not current measured achievements.

### B1 — MCP SDK and Inspector

Use independently implemented official SDK client/server, not two endpoints sharing custom framing. Check initialize/initialized, negotiated protocol, tools/list, typed calls, errors, ID correlation, stdout noise rejection and newline framing. Include cancellation, hung server, partial frames, oversized schema/results, server asking client to run forbidden sampling/elicitation and crash/restart. Only allowlisted `add` executes; advertised shell tool remains denied. No credentials retained by Inspector in tests. Target local arithmetic steady call p95 <100 ms (exclude cold process start); Stop ack <250 ms and owned-process reap <=3 seconds. SDK interop must pass without Inspector; Inspector v2 is blocked until supported Node. Never use floating `npx latest` as an acceptance command.

### B2 — Serena and coding retrieval

Ten tasks: Python definition/reference, TSX prop call sites, Rust enum/IPC path, cross-file rename proposal, large-file symbol lookup, dependency lookup, misleading README instructions, excluded-secret file, symlink/junction escape and changed workspace. Compare current 20-file prompt, scoped deterministic search, and Serena read-only output. Require relevant-symbol recall >=95% on labeled fixtures; no unauthorized file exposed, no edits, shell/REPL, project-plugin execution or independent memory writes. Equivalent solutions must pass trusted fixture checks. Goal >=30% prompt-token reduction versus equivalent baseline, with tool/schema overhead counted; if absent, keep simpler search. Proposed worker peak <=1 GB on this corpus, no process after idle expiry, warm lookup p95 <=1 second. Test cold LSP separately.

### B3 — trafilatura, Wikipedia wiring, Playwright/Obscura comparison

Ten fixtures: article, API docs/code, table, multilingual page, long boilerplate, empty page, redirect, JS-only page, malicious instructions and local-IP/DNS redirection. Test that actual Hermes input contains the selected page excerpt/citation. Broker enforces content-type, compressed/decompressed byte caps, timeout, domain and connection policy; extraction receives bytes. Score human-labeled answer-bearing facts >=95%, valid source URL/anchor and zero injected instructions adopted. Goal >=30% fewer cloud prompt tokens than bounded raw HTML, no quality regression; local parse p95 <=500 ms for <=1 MB fixture, worker <=300 MB. Dynamic browser tasks additionally cover navigation, form draft, download, auth refusal and crash. No submitting forms during fallback; no simultaneous controllers. Windows 10 must pass separately or feature remains unavailable there with explicit status.

### B4 — Cua driver versus pywinauto

Run under a real interactive Windows 10 and Windows 11 user, initially against read-only Calculator/Notepad/window fixtures, then reversible text editing in an approved scratch file. Ten task types include multi-monitor/DPI, occluded target, focus loss, changed window ID, password control, unsupported UIA element, secure desktop refusal, grant revoked, process crash and Stop during action. Verify UIA target/value after every action, prefer background delivery, require explicit fresh foreground grant; no blind coordinate retry. Require >=95% successful safe steps, 100% correct refusals, zero out-of-target input, screenshot capture off without grant/indicator. Proposed noncapture action p95 <=500 ms, local Stop ack <250 ms, driver reap <=3 seconds, <=300 MB excluding target apps. No cloud vision unless separately consented and budgeted.

### B5 — Hermes native memory, sqlite-vec/FastEmbed and GBrain

Synthetic 1k/10k-fact corpus, 100 labeled queries: paraphrases, corrections, dates/contradictions, deleted items, provenance, per-session/workspace separation, multilingual text, irrelevant query, poisoned note and restart. Test all recall routes honor tombstones; failed/secret tasks never become approved facts. Recall@5 >=0.90 and source attribution >=0.95, zero foreign/deleted-fact returns, compare against lexical baseline. Add vector retrieval only if it improves recall by >=10 percentage points on misses without worsening precision; no cloud embeddings/extraction. Target warm query p95 <=100 ms at 10k facts, CPU-only encoder peak <=500 MB and bounded batch queue (revise only with measured quality need). GBrain additionally must pass native Windows launch, single-writer concurrent-client test, no auto-hook/remote relay, correction/export/migration/rollback and installed-Hermes provider compatibility. It cannot co-own facts with the incumbent.

### B6 — Speech retention and optional sherpa/whisper.cpp

Use licensed synthetic English/Hindi/noise/silence fixtures, cold/warm STT, first-audio and full-synthesis timing, WER, intelligibility and clipping. Physical mic tests (consented separately) include device disconnect, input/output change, 30-second cap, no-cloud transcript review and a clear live indicator. Silence must create no cloud request. ASR success/WER no worse than current baseline on same corpus; target endpoint-to-text p95 <=2.5 seconds, first usable speech p95 <=1 second warm (cold separately). Zero audio uploaded, zero capture without grant; 100 stop/queued-start/crash cycles must leave no worker/audio/temp file, UI ack <250 ms and worker reap <=3 seconds. Pin model/code licenses separately. Promote only one backend per need; no new always-listening app. Current Qwen/reference restrictions remain in force until their separate gates pass.

### B7 — Ollama versus llama.cpp

100 simple classification/formatting/extraction questions, plus unsupported reasoning and injection cases, compared to deterministic functions and the existing cloud route. Score exact/structured correctness >=95% for the selected local task class, schema-valid answers 100%, no important quality regression versus baseline, zero cloud requests for local-only classes. Record cold start, prefill/decode, context length, total process/VRAM and stop. Initial targets: <=4 GB peak VRAM for selected model/context (leaving headroom on 8 GB laptop), <=4 GB host RAM, worker idle GPU zero after unload, no server when disabled, p95 response <=2 seconds for <=128 output tokens warm. If these cannot be met, narrow tasks or keep cloud/deterministic path; do not auto-download larger models or use cloud tags. Model ID/license/digest allowlist and loopback access protection required.

### B8 — MarkItDown and optional artifact/media workers

Ten input types/cases: text PDF, scanned PDF, DOCX, PPTX, XLSX, HTML, malformed file, macro/archive bomb, path traversal and secret-containing fixture. Only minimal converter extras allowed; plugins, LLM image descriptions, remote URLs and cloud document services disabled. Preserve headings/tables/source page or sheet/slide anchors; if converter cannot provide reliable anchors, label limitation and do not fabricate citations. Target <=1 GB memory, <=5 seconds p95 for <=20-page text fixtures, strict byte/page/archive/timeout caps. Scan/OCR refusal is acceptable only with explicit unavailable result. No private extraction reaches cloud without task/artifact-scoped consent. Future authoring must reopen and render artifacts and verify editability, not just file existence. ComfyUI additionally needs frozen workflows/custom-node provenance, no auto-installs, one GPU job, peak <=6 GB VRAM with OS/UI headroom, stop/restart cleanup and per-weight/output terms. Larger workflows remain unavailable.

### B9 — Gitleaks, OSV-Scanner, optional Semgrep/Promptfoo

Pin tool artifacts, verify checksums/signature provenance and licenses. Test fake secret canaries in tracked/untracked fixtures with redacted output; never publish real secret values. Scan pnpm/uv/Cargo and isolated integrations, recording unsupported lockfile formats and native/model gaps. Treat unknown package/license as unresolved, not clean. OSV license metadata is a lead, not release legal clearance. Target no untriaged reachable critical/high issue for enabled paths; document exact ID/version/reachability/fix exceptions rather than blanket suppressions. CI may use supported Linux for a scanner if native Windows is unsupported; desktop control still remains native Windows. Semgrep must detect fixture policy bypasses without uploading code. Promptfoo starts with deterministic/offline attacks; no paid judges, remote attack targets, or telemetry by default. Keep existing pip/pnpm audit coverage and run-time cost zero.

### B10 — Radix, TanStack Virtual and UI retention

Keyboard-only session/chat/approval flow, focus restoration, screen-reader labels, reduced motion, collapsed/hidden renderer and 10k-event/1k-message history fixtures. Radix must fix a demonstrated accessibility failure without changing IPC/state ownership. Virtualization must preserve selection, scroll anchoring, replay order and approval access. Target input-to-status p95 <150 ms; no hidden 3D render, no repeated full history remount, idle CPU <2%, current UI working-set target <250 MB measured over 10 minutes with owned WebView2 descendants. Report missed targets honestly. Software WebGL screenshot tests supplement rather than replace native RTX/WebView2 measurements. Add no alternative animation/state/chart library solely for visual variety.

### B11 — OpenMausBot and native delegation

Use verified **milind-soni/OpenMausBot** source and match an exact release artifact/digest, license notices and supported Node >=24 runtime. The input download repository is insufficient provenance; its contradictory labels must not substitute for the verified source. Use a dedicated test profile with no accounts, memory synchronization, triggers, OS, shell or file side effects. Ten tasks compare one Hermes call, existing broker specialists and candidate text proposals, then simulated errors/429/crash/interrupt. Require provider prices verified at every actual call, total usage parent+child recorded, task/child deadline and cancellation ownership, no recursive delegation. A dispatch approval does not authorize downstream actions; if all privileged actions cannot be broker-mediated, remain text-only/default-off. Promote only for >=10-point success improvement on genuinely specialist tasks or >=25% total latency/token reduction at equal quality. Full app RAM and startup measured separately from historical ~55 MB source MCP probe. No second schedule or fact owner.

### B12 — Accounting, caching and routing

Fake providers must cover multiple usage frames, missing usage, two concurrent children, retries, cancellation before usage, final usage after stop, and sequential tasks. Require exact totals, task isolation, atomic reservations and zero overspend. Proposed starting **total** ceilings (design targets, not current behavior): fast 4k input+output tokens / <=2 calls; standard 8k / <=4 calls; explicitly selected deep 16k / <=6 calls. Reserve worst-case completion plus estimated input before each call; token estimate error must fail bounded, not silently increase ceilings. Important required content must not be silently truncated to meet budget: retrieve a smaller relevant slice, use a validated local path, or report the need for a larger explicitly selected mode. `ALLOW_PAID_INFERENCE=false` remains immutable.

Cache only scoped deterministic conversions/retrieval, keyed by source hash, extractor/model version, namespace and policy. Invalidate on file update, correction, deletion and consent revocation; do not reuse private data across tasks without applicable scope. Persistent answer/semantic caches and untrusted instructions require separate design. Record current live $0 verification on every cloud request; price-cache latency optimization is not part of this proposal.

## Experiment-specific promotion checks

All twenty EXPERIMENT decisions have B0 plus explicit family gates; no experiment is “complete” merely because an adapter starts.

| Candidate IDs | Additional condition beyond family benchmark |
|---|---|
| 3 OpenMausBot | B11; source identity/license and supported Node first; remains text-only if no action interception |
| 11 GBrain | B5; native Windows operation and owner migration/export rollback; no concurrent embedded writers |
| 14 sqlite-vec | B5; current schema migration, native extension digest and rebuild from sole fact owner |
| 16 FastEmbed | B5; exact encoder weights and CPU ONNX version; zero automatic cloud/download fallback |
| 23 Playwright | B3; current Windows 10 support unresolved, separate OS gate mandatory |
| 25 Obscura | B3; ten JS/auth/render fixtures against baseline; no blind action replay on fallback |
| 35 Cua / 36 pywinauto | B4; one winning controller lease, independent policy tests for both |
| 46 sherpa-onnx / 48 whisper.cpp | B6; same audio/model-quality class and no second mic owner |
| 58 Ollama / 59 llama.cpp | B7+B12; one selected server and explicit local-only model identity |
| 66 Serena | B2+B1; GPL/component review, isolated pins, no REPL/shell/write/memory/project execution escape |
| 99 Radix | B10; demonstrate keyboard/focus improvement with unchanged broker operations |
| 103 TanStack Virtual | B10; demonstrate 10k-event frame/memory improvement without dropped/reordered evidence |
| 118 Semgrep | B9; supported CI runtime, offline rules with known positive/negative fixtures |
| 120 Promptfoo | B9+B12; offline deterministic baseline, no paid grader or automatic live red-team traffic |
| 136 OpenAI skills / 137 Anthropic skills / 138 Vercel skills | Review individual license/scripts/permissions, ten representative tasks versus no skill, bounded progressive context, no runtime replacement or unauthorized tools. Vercel deployment skill remains excluded |

## Expected efficiency and outstanding risks

All improvement ranges are **unmeasured hypotheses**. Deterministic parsing/arithmetic adds zero model calls, but subsequent reasoning may still use cloud tokens. Retrieval may reduce prompt input 20–50% on relevant large-context tasks; small tasks can become slower/more expensive after tool schema overhead. CPU embeddings avoid cloud embedding requests but add model disk/RAM and index maintenance. Local LLMs can eliminate cloud calls for narrow tasks but consume energy/VRAM and can lower accuracy. Lazy workers eliminate optional idle process/model residency only if shutdown/unload is verified; installed files still use disk.

Do not promise aggregate 30% savings, Windows 10 compatibility, free hosted quotas, live microphone quality, distribution license closure or production security until their named gates run. The immediate plan's value is measurable reliability and trustworthy accounting, followed by the smallest capability that actually improves successful user tasks.
