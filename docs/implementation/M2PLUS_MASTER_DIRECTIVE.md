# IMMORTILITY — PHASE M2+ MASTER CONTINUATION
## FROM VERIFIED FOUNDATION TO A FULLY CAPABLE AUTONOMOUS AI SYSTEM

You are continuing development of **IMMORTILITY**, my Windows-based, Hermes-powered personal AI platform.

This is the next implementation phase after the completed critical-repairs checkpoint.

**Your mission is to transform Immortility from a working conversational assistant with a limited capability gateway into a genuinely useful, production-quality AI system that can research, use authorized tools, create files, understand projects, coordinate agents, interact with approved desktop applications, and complete long-running work.**

This is NOT another research-only task.

Do not start a new project, redesign the architecture, repeat the 138-repository audit, or discard existing work.

## 0. AUTHORITATIVE CURRENT CHECKPOINT

Read the actual repository and existing documentation, particularly:

- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/CONTINUATION_STATUS.md`
- `docs/implementation/CRITICAL_REPAIRS_CHECKPOINT.md`
- `docs/implementation/CRITICAL_REPAIRS_VERIFICATION.json`
- `docs/implementation/M0_CHANGED_FILES.json`
- The original boss-level master directive
- The autonomous-desktop directive
- The ecosystem implementation roadmap
- The relevant capability, security and architecture specifications

Discover actual filenames when necessary.

### Latest reported verification

The previous implementation session reported:

- 263 passing Python tests.
- 55 passing frontend tests.
- 6 passing Rust tests.
- Successful TypeScript, lint, formatting, contract and build checks.
- Two authorized live free-provider questions through Hermes.
- Correct Immortility identity and current-capability descriptions.
- Chat failure messages and stream-recovery improvements.
- Local Piper multisentence WAV repair.
- CPU Whisper transcription on an actual synthetic audio fixture.
- A mocked CUDA-to-CPU recovery test.
- Native dashboard attachment to a background local broker.
- DPAPI-protected credentials and real result replay.
- Existing broker-controlled MCP arithmetic execution.
- A native read-only Windows observation consent test.

These are historical verified checkpoints, not automatic evidence that all current files still pass.

### Known outstanding work

- Physical microphone and speaker acceptance.
- True general-purpose agent tool use.
- Loaded MCP cold-start reliability.
- Public multi-source research.
- Dynamic browser automation.
- General application screen understanding.
- Virtual pointer/voice-guided explanation.
- Safe desktop actions.
- Coding execution and verification.
- Durable memory improvements.
- Artifact creation.
- General multi-agent execution.
- Scheduling and external connectors.
- Long-running production acceptance.
- Shared Hermes dependency advisory review.

Do not repeat completed work unless checking compatibility or fixing a demonstrated regression.

### Working-tree protection

Inspect Git status and ongoing editor activity before modifying files.

Previous development involved concurrent avatar/GPU editing.

Never overwrite another editor's active work.

Use separate worktrees when simultaneous tasks require overlapping source changes.

Never reset Git or delete untracked user data to simplify the checkout.

---

# 1. MOST IMPORTANT PRIORITY — MAKE HERMES ACTUALLY USE AUTHORIZED TOOLS

This is the central missing capability.

Currently, real Hermes can answer questions, and the broker can execute some local operations, but broad model-directed tool execution is not yet available.

**Bridge the intelligence layer and the capability gateway.**

## Requirements

Hermes must be able to:

1. Understand a user goal.
2. Determine whether it needs tools.
3. Identify permitted tools.
4. Propose a structured tool operation.
5. Submit that operation through the broker.
6. Have the broker independently authorize it.
7. Execute the tool with bounded resources.
8. Receive the validated result.
9. Continue reasoning if necessary.
10. Verify the actual outcome.
11. Return a meaningful final answer or artifact.

### Crucial architecture restriction

Do not simply enable Hermes's unrestricted native shell, filesystem, browser or MCP toolsets.

Inspect the installed Hermes interfaces to determine the safest supported way to expose broker-mediated capabilities.

The existing free-provider gateway may disallow provider-native tool/function calls. Verify the actual transport and provider contracts before changing them.

If native function calling is unavailable or unsuitable, evaluate a tightly constrained structured-action protocol handled by the broker.

Such a protocol must have:

- Exact schemas.
- Independent broker-side validation.
- Explicit tool allowlists.
- Task-scoped grants.
- Permission checks.
- Argument validation.
- Output limits.
- Expiry and revocation.
- Bounded iterative execution.
- Prompt-injection protection.
- Safe failure behavior.

Never interpret arbitrary model-generated prose as an executable command.

Never execute a model's proposal simply because it appears valid JSON.

The broker must independently determine whether the requested operation is authorized.

### Efficient capability discovery

Do not inject every available MCP/tool schema into every model prompt.

Implement progressive capability exposure:

- Determine the relevant capability family locally where possible.
- Retrieve only applicable manifests.
- Supply compact schemas.
- Cache stable capability metadata.
- Avoid repeated tool discovery within one task.
- Use deterministic operations without model inference whenever appropriate.

### Initial end-to-end tests

Demonstrate:

**A.** Ask Immortility to calculate a result and receive a verified response from an approved local capability.

**B.** Ask it to inspect a user-approved scratch file and explain its contents.

**C.** Ask it to use a denied capability and verify that the broker refuses.

**D.** Cancel during tool execution and verify that the action stops.

**E.** Restart after an interrupted task and verify that state is recovered without duplicating side effects.

**F.** Check the model, tool, task and UI traces to prove the complete execution path.

At least one test must demonstrate genuine model-driven tool selection rather than a hardcoded mapping from a specific phrase to a tool.

**Exit condition: Immortility can genuinely choose and use approved tools, while the broker remains the sole execution authority.**

---

# 2. FINISH MCP RELIABILITY AND UNIVERSAL TOOL REGISTRATION

Preserve the existing isolated official MCP SDK runtime.

Investigate the observed MCP deadline failures during concurrent compilation or high system load.

Do not automatically increase timeouts to conceal an initialization defect.

Instrument the stages:

- Process creation.
- Dependency import.
- Server initialization.
- Capability negotiation.
- Tool discovery.
- Request dispatch.
- Result delivery.
- Cancellation.
- Process shutdown.

Compare cold-start isolation against a carefully controlled reusable-session design.

Any reuse must preserve per-task permission isolation and avoid sharing secrets or unrestricted state between unrelated tasks.

Test under controlled CPU and disk contention.

Implement registration for multiple reviewed capabilities without granting universal access to arbitrary discovered MCP tools.

Keep unknown or privileged external MCP servers default-off until their individual security gates pass.

### Verification

Test standard SDK interoperability, schema changes, malformed messages, oversized responses, forbidden tools, process crashes, task revocation and concurrent requests.

Report cold and warm latency separately, including failures.

---

# 3. BUILD REAL PUBLIC WEB RESEARCH

This is the first major productivity capability to deliver after the tool bridge.

I want Immortility to handle requests such as:

"Research the best open-source agent frameworks and explain which ones would work with my project."

"Read these three websites and compare their claims."

"Research a technical subject and prepare a properly cited report."

## Required implementation

Build a broker-controlled research pipeline with:

- Search-provider abstraction.
- Public web search when a configured provider is available.
- URL validation.
- Secure public HTTP fetching.
- HTML extraction.
- Source metadata.
- Source timestamps.
- Citation tracking.
- Content hashing.
- Bounded caching.
- Query refinement.
- Multi-source comparison.
- Contradiction identification.
- Source relevance ranking.
- Bounded response synthesis.

Evaluate the previously selected lightweight extraction tools such as Trafilatura.

Use deterministic HTML extraction before a full browser where appropriate.

For dynamic pages, evaluate Playwright as the compatibility baseline and Obscura only if measurable benefits justify it.

Do not start multiple browser controllers for the same task.

### Security

Block inappropriate local, loopback, link-local and private network targets for public fetch operations.

Protect against DNS rebinding, redirects into restricted addresses, decompression bombs and oversized responses.

Treat retrieved text as untrusted data.

Never obey instructions embedded inside pages or documents.

Do not silently upload private project information to a cloud model.

### Acceptance

Run genuine public-source research tasks, verify that actual excerpts reach Hermes, and ensure the answer uses traceable evidence.

Provide citations and clearly distinguish missing or contradictory information.

No fabricated sources.

---

# 4. IMPLEMENT A COMPLETE ARTIFACT AND DOCUMENT ENGINE

After the universal tool bridge and safe file policies work, begin producing real files.

This is a major product priority.

## Required formats

### DOCX

- Professional document layouts.
- Headings and sections.
- Tables.
- Images.
- Page numbers.
- Headers and footers.
- Citations and bibliography.
- Editable output.

### PDF

- Proper rendered pages.
- Embedded fonts where appropriate.
- Valid document structure.
- Correct page count.
- No clipping or overflowing content.
- Verification by reopening/rendering.

### PPTX

- Fully editable slides.
- Consistent themes.
- Charts and diagrams.
- Images and tables.
- Speaker notes when supported.
- Slide rendering.
- Visual overflow detection.

### XLSX

- Worksheets.
- Formulas.
- Formatting.
- Data validation.
- Charts.
- Financial and analytical models.
- Workbook integrity checks.

### Other artifacts

- Markdown.
- HTML.
- CSV.
- JSON.
- SVG.
- Architecture diagrams.
- Technical reports.
- Generated project documentation.

Use established format-specific libraries.

Do not use MarkItDown as a substitute for actual DOCX/PPTX/XLSX creation; it is primarily an ingestion/conversion component.

### Production artifact pipeline

User request
→ Requirements extraction
→ Plan
→ Source gathering
→ Content generation
→ File construction
→ Reopen/parse validation
→ Render inspection
→ Corrections
→ Verified deliverable

Every artifact must have a real authorized output path, file metadata, verification status and accessible user-facing result.

### Critical 40-page report test

Build a meaningful acceptance workflow for:

"Research a subject and create a properly formatted 40-page report with sources, figures and tables. Generate DOCX and PDF."

The system must:

1. Plan an appropriate report structure.
2. Gather sufficient evidence.
3. Produce substantive content.
4. Create editable DOCX.
5. Render PDF.
6. Verify the rendered PDF has exactly 40 pages when that is a hard requested constraint.
7. Check headings, tables, figures and citations.
8. Correct layout problems.
9. Preserve source provenance.
10. Save both actual files.

Do not fill pages with fabricated research, repeated paragraphs or meaningless padding.

If source material is insufficient, report the problem rather than inventing evidence.

Use synthetic, clearly labeled fixtures for automated testing. Separate those from an actual research report created for the user.

---

# 5. BUILD AUTONOMOUS RESEARCH-TO-DELIVERABLE WORKFLOWS

Connect the new capabilities to the already implemented durable workflow engine.

I want to give one task and let Immortility perform authorized work while I leave the computer.

Example:

"Research network security and prepare a detailed presentation and report. Save the finished files to my project folder."

Required behavior:

- Create a real task.
- Establish deliverables and constraints.
- Obtain necessary permissions.
- Break the work into stages.
- Execute approved research.
- Generate document content.
- Create actual files.
- Check results.
- Recover from interruptions.
- Notify the user.
- Display real progress after dashboard reconnection.

Use the existing broker-owned queue, checkpoints and background attachment.

Do not create a second workflow engine.

Do not turn existing synthetic SDK workflows into a false claim that arbitrary research or coding tasks can already run unattended.

### Background behavior

Headless tasks may continue after dashboard detachment through the explicitly configured background runtime.

The computer must remain powered and the runtime must remain available.

Desktop-dependent operations should pause safely when Windows is locked or the interactive session is unavailable.

No silent service installation.

No automatic authorization of sensitive external actions.

---

# 6. ENABLE SAFE PROJECT UNDERSTANDING AND CODING

Once tool mediation and workspace isolation are reliable, make Immortility useful for real development work.

Build:

- Approved repository discovery.
- Project structure understanding.
- File and symbol search.
- Relevant context retrieval.
- Dependency understanding.
- Error analysis.
- Change planning.
- Patch proposals.
- Diff review.
- Approved file modifications.
- Safe Git inspection.
- Build and test verification.
- Regression reporting.
- Rollback.

Evaluate Serena for symbol-level read-only retrieval if it improves prompt-token efficiency over the current bounded file search.

Do not enable unrestricted coding-agent shell execution.

If test execution is added, implement a genuine restricted execution boundary with explicit paths, commands, environment restrictions, deadlines and resource budgets.

Windows process ownership alone is not an adequate security sandbox for arbitrary untrusted code.

Test against controlled sample repositories before granting wider workspace access.

### Acceptance

Given an approved test repository with a seeded bug, Immortility should:

1. Locate the cause.
2. Propose the fix.
3. Apply it within the authorized scope.
4. Run approved tests.
5. Verify the outcome.
6. Display the diff and evidence.
7. Explain any remaining failures.

It must never call a patch complete merely because the model says it looks correct.

---

# 7. COMPLETE SCREEN UNDERSTANDING AND VOICE-GUIDED EXPLANATIONS

Preserve the now-verified synthetic-window consent workflow.

Extend it cautiously.

I want to say:

"Immortility, explain what is on my screen."

"Explain this code and point to the relevant functions."

"Show me where the problem is."

## First capability: read-only guided explanation

Implement:

- Explicit user-selected windows.
- Fresh native window identity verification.
- Task-scoped observation grants.
- UI Automation text and structure retrieval.
- Sensitive field exclusion.
- Optional screenshot capture with separate permission.
- OCR or visual-model fallback when justified.
- Region and coordinate mapping.
- Virtual pointer overlays.
- Element highlighting.
- Voice-synchronized explanations.
- Stop and permission revocation.

Do not move the actual mouse merely to point at something.

Use a virtual overlay for explanations.

Actual clicking, scrolling and typing require a separate privileged action capability and successful native safety acceptance.

Screen content must remain local unless the user explicitly authorizes sending the relevant content to a cloud provider.

Do not infer broad capture permission from the previous scratch-window test.

## Native voice acceptance

The previous session successfully fixed Piper WAV synthesis and verified CPU Whisper against a synthetic fixture.

Do not repeat that work unnecessarily.

However, physical audio remains unverified.

Request specific native permission when microphone or speaker testing is required.

Verify:

- Physical microphone capture.
- Accurate transcription.
- CPU fallback.
- Transcript insertion.
- Chat submission.
- Response playback.
- Stop speaking.
- Device disconnect/recovery.

Do not treat the synthetic audio fixture as proof that a physical microphone or speaker works.

---

# 8. IMPLEMENT REAL MULTI-AGENT COORDINATION

Hermes remains the primary planner.

Inspect native Hermes delegation and existing broker specialists before adding another orchestration framework.

Enable only the minimum orchestration functionality required for verified tasks.

Support:

- Parent task ownership.
- Specialist roles.
- Task decomposition.
- Sequential execution.
- Parallel independent work.
- Structured agent outputs.
- Agent handoffs.
- Context isolation.
- Token-budget propagation.
- Permission inheritance with no privilege escalation.
- Cancellation propagation.
- Checkpoints.
- Result verification.
- Failure reporting.

Do not spawn three agents when one agent and deterministic tools would be cheaper and equally effective.

Use a genuine research → writing → verification workflow as an acceptance test.

Each specialist's activity should be visible through actual dashboard events.

Avoid decorative agent nodes implying that unavailable agents are running.

---

# 9. COMPLETE MEMORY AND CONTROLLED SELF-IMPROVEMENT

Build upon the existing broker memory and durable forgetting behavior.

Required capabilities:

- Project-scoped memory.
- Approved user facts.
- Task history.
- Provenance.
- Corrections.
- Retrieval ranking.
- Bounded context insertion.
- Durable recall exclusion.
- Export and retention controls.
- Optional local semantic retrieval.

Do not install multiple authoritative memory frameworks.

Evaluate Hermes-native memory first.

Compare sqlite-vec, FastEmbed or GBrain only against measured retrieval failures.

### Controlled self-improvement

After a successful task, Immortility may propose retaining reusable lessons, workflows or skills.

After a failed task, it may record a verified failure cause.

Improvements must be evaluated before promotion.

No autonomous rewriting of security policy, permission grants, billing rules or critical runtime components.

Self-improvement must not silently generate extra paid model calls.

---

# 10. FINISH CONNECTORS, SCHEDULING AND MULTIMODAL CAPABILITIES

Continue the established roadmap after the core tool bridge and first real end-to-end tasks work.

Support approved connections to services such as GitHub, email/calendar, cloud storage, Vercel, databases and Canva only through their actually available APIs, MCP interfaces or other supported adapters.

Implement secure authentication and credential storage where appropriate.

Use one authoritative scheduler, preferring a compatible Hermes-native feature where justified.

Support authorized reminders, recurring jobs and conditional workflows.

Optional media generation should be lazy-loaded, resource-bounded and subject to verified model and license constraints.

No automatic account connection, private-data upload, purchase, deployment or paid inference.

---

# 11. KEEP THE DASHBOARD AND AVATAR ALIVE WITH REAL EVENTS

The visual system must advance alongside the backend.

Do not redesign the dashboard from scratch.

Connect genuine execution events to:

- Agent status.
- Task cards.
- Timeline.
- Tool activity.
- Real token usage.
- Approval requests.
- Artifact previews.
- Background-task progress.
- Avatar states.
- Voice activity.
- Completion/failure notifications.

The avatar should behave appropriately when listening, thinking, researching, coding, waiting, speaking, succeeding or failing.

All behavior must be driven by actual backend or audio events.

Do not fabricate task progress percentages.

Preserve existing visual assets and the other editor's GPU/avatar improvements.

Use GSAP/R3F efficiently.

Keep hidden dashboard rendering paused and avoid unnecessary continuous GPU activity.

Ensure the floating companion remains readable and interactive at narrow sizes.

---

# 12. EXTREME TOKEN, LATENCY AND HARDWARE OPTIMIZATION

Optimize **cost per successfully completed task**, not merely tokens per request.

Implement or refine:

- Exact task-wide token accounting.
- Parent/child agent budgets.
- No unauthorized paid fallback.
- Capability-first deterministic routing.
- Selective tool schemas.
- Source-context extraction.
- Prompt caching when supported.
- Retrieval caching.
- Context compaction when beneficial.
- Bounded tool-result sizes.
- Safe retries.
- Local processing for simple operations.
- One heavyweight GPU job at a time unless benchmarked otherwise.
- Lazy model and worker loading.
- Worker cleanup and idle expiry.
- Actual CPU/RAM/VRAM measurement.

The RTX 4060 should accelerate appropriate local inference and 3D rendering, not become required for microphone capture or basic agent logic.

Keep free-provider policies and explicit cloud-content consent.

Do not repeatedly run live provider tests without authorization.

Track total model calls and tokens consumed by all agent branches, retries and verification steps.

---

# 13. HANDLE REMAINING SECURITY DEBT

The previous audits identified unresolved advisories in the shared Hermes environment.

Do not ignore this, but do not blindly upgrade the installed Hermes runtime.

Prepare an isolated comparison against an appropriate reviewed version, using exact version pins and dependency evidence.

Identify reachable vulnerabilities relevant to the application's actual enabled paths.

Compare:

- API compatibility.
- Tool isolation.
- Delegation behavior.
- Memory behavior.
- Permission mediation.
- Startup latency.
- Token usage.
- Windows stability.
- Existing tests.

Promote only a compatible and verified upgrade.

Keep vulnerable or unsupported experimental voice and tool runtimes disabled.

Use secret scans, dependency scans and explicit permissions for every new integration.

---

# 14. PRODUCTION-GRADE ACCEPTANCE MATRIX

Create real end-to-end demonstrations, not merely isolated unit tests.

| Test | Required proof |
|---|---|
| Model-to-tool execution | Hermes chooses an approved capability and the broker executes it |
| Tool refusal | Unauthorized tool is blocked with no side effect |
| Web research | Real public sources retrieved, attributed and summarized |
| Artifact creation | Actual DOCX/PDF/PPTX/XLSX files reopen successfully |
| 40-page report | Rendered page count and meaningful content verified |
| Coding | Approved patch, tests and diff evidence |
| Background work | Task survives UI detachment and reattachment |
| Screen explanation | Authorized UI content explained with accurate highlighting |
| Voice | Real mic-to-STT-to-response-to-TTS path with Stop |
| Multi-agent work | Actual delegation and verified combined result |
| Memory | Correct recall, correction, exclusion and restart behavior |
| Scheduling | Authorized trigger executes once and survives restart safely |
| Security | Unauthorized paths, tools and data egress denied |
| Efficiency | Measured end-to-end latency, resource use and model tokens |

Every result must be classified as:

- VERIFIED REAL OPERATION
- VERIFIED LOCAL INTEGRATION
- MOCK-TESTED ONLY
- IMPLEMENTED BUT DISABLED
- BLOCKED
- NOT IMPLEMENTED

The real product must not display unavailable capabilities as if they were working.

---

# 15. IMPLEMENTATION STRATEGY — VERTICAL SLICES, NOT ENDLESS INFRASTRUCTURE

Follow this order, adjusting only for verified dependencies:

## M2A — Model-to-capability bridge

First deliver real Hermes-selected broker-authorized tool usage.

Do not expand to arbitrary external tools until its safety and cancellation tests pass.

## M2B — Real web research

Deliver multi-source, citation-bearing public research.

## M2C — Real artifact pipeline

Deliver actual DOCX/PDF/PPTX/XLSX files with verification.

## M2D — Autonomous research-to-report workflow

Connect planning, research, file generation, verification and background recovery into one demonstrated task.

## M3 — Safe coding and browser capabilities

Implement scoped repository intelligence, controlled editing and dynamic browser use.

## M4 — Screen explanation and supervised computer use

Expand native observation with separate permissions for visuals and actions.

## M5 — Multi-agent, memory and scheduling

Enable advanced orchestration and durable knowledge only after their compatibility and measurable value are established.

## M6 — Connected applications and production hardening

Expand provider integrations, monitoring, recovery, security and packaging.

Do not neglect voice and UI regressions while developing these capabilities.

### For every slice

1. Inspect existing code and available native features.
2. Identify the smallest missing behavior.
3. Implement working code.
4. Add appropriate tests.
5. Run real local integration tests.
6. Fix failures.
7. Test through the actual product interface where feasible.
8. Measure latency, tokens and resources.
9. Review permissions and privacy.
10. Update the checkpoint and continue.

Do not spend a full engineering session producing another broad architecture report instead of a working feature.

Do not mistake installation, source compilation, a fake fixture or a UI card for end-to-end capability.

When external credentials or live service permissions are missing, complete safe local components, record the blocker and continue independent work.

---

# 16. PERSISTENT PROGRESS AND FUTURE CONTINUATION

Maintain:

`docs/implementation/CURRENT_STATUS.md`

Record:

- Current milestone and exact subtask.
- Changed files.
- Verified functionality.
- Tests run.
- Exact benchmark results.
- Features still disabled.
- Security blockers.
- Concurrent source ownership.
- User approvals required.
- Next implementation action.

Add concise evidence reports for significant milestones.

Do not overwrite or silently reinterpret earlier benchmark evidence.

Do not promise future background work by Codex after the active session ends.

---

# FINAL PRODUCT EXPECTATION

I want Immortility to become a highly capable personal AI assistant that can perform actual work.

When I say:

**"Research this topic."**

It should find permitted sources, evaluate their relevance, and return a grounded response.

**"Prepare a 40-page report while I'm away."**

It should execute an authorized long-running workflow, create genuine deliverables, validate them and save them.

**"Open my project and fix the errors."**

It should understand the project, propose or apply authorized edits, run controlled tests and return evidence.

**"Explain what is on my screen."**

It should inspect an explicitly approved window, understand the visible content and guide me with speech and virtual highlighting.

**"Ask your agents to build this."**

It should coordinate real specialist work, respect budgets, verify outputs and report progress.

**"Remember this approach for next time."**

It should store approved reusable information and retrieve it when relevant.

The interface, avatar, chat, task graph, tools and background workflows must reflect real shared execution state.

The system must be:

- Highly capable.
- Secure.
- Fast.
- Low-cost.
- Token-efficient.
- Resource-conscious.
- Reliable under failure.
- Useful in real applications.
- Honest about limitations.
- Extensible without duplicate frameworks.

**The goal is not to claim Immortility can do everything. The goal is to make it capable of completing a very broad range of authorized tasks with real evidence of success.**

## START NOW

Recover the actual latest checkpoint.

Verify the critical repairs still hold.

**Begin with M2A: connect Hermes to the existing broker-mediated capability gateway.**

Then continue through each eligible vertical slice in dependency order.

Preserve all working features, files, selected voices, GPU improvements and dashboard components.

Do not restart the audit.

Do not stop at a demonstration or documentation-only result.

Implement, verify, benchmark and checkpoint genuine working capabilities.