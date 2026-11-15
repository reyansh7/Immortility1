# IMMORTILITY — RESUME DEVELOPMENT AND COMPLETE THE REMAINING AGENTIC AI SYSTEM

## CRITICAL: CONTINUE EXISTING WORK — DO NOT RESTART

You are continuing the development of **IMMORTILITY**, my production-grade personal AI operating system.

The previous Codex session stopped during implementation of the master engineering directive.

**THIS IS A CONTINUATION AND IMPLEMENTATION TASK. NOT A NEW RESEARCH TASK.**

Do not repeat the complete GitHub ecosystem audit, rewrite the architecture from scratch, reinstall working dependencies, or discard previously implemented changes.

Your objective is to examine exactly where development stopped, complete unfinished work, and continue through all remaining eligible milestones until Immortility has a fully integrated, extensively tested agentic AI backend.

### AUTHORITATIVE REFERENCE DOCUMENTS

Read these existing files where present:

- `docs/implementation/IMMORTILITY_BOSS_LEVEL_CODEX_MASTER_PROMPT.md`
- `docs/research/ECOSYSTEM_ARCHITECTURE_AUDIT_2026-11-14.md`
- `docs/research/ECOSYSTEM_CANDIDATE_MATRIX_2026-11-14.md`
- `docs/research/ECOSYSTEM_IMPLEMENTATION_ROADMAP_2026-11-14.md`
- `docs/research/ECOSYSTEM_VERIFICATION_2026-11-14.md`
- `docs/research/IMMORTILITY_GITHUB_ECOSYSTEM.md`
- Existing implementation, verification, benchmark, security and rollback reports

The master directive remains authoritative for project scope and acceptance requirements. This continuation prompt clarifies execution priorities.

If documentation conflicts with actual code, inspect the implementation and tests, identify the discrepancy, and document the resolution.

---

# PART 1 — RECOVER THE EXACT DEVELOPMENT STATE

The previous Codex session was working on M0 repairs and standards-compliant MCP integration.

Its reported accomplishments include:

1. Windows protected-path and alias hardening.
2. CRLF-safe workspace operations.
3. Persistent memory recall exclusion.
4. Task-scoped approval ownership and revocation.
5. Inference reservations and usage-ledger changes.
6. Native Windows credential dialog.
7. Owned worker processes and cancellation cleanup.
8. Real Hermes offline smoke-test recovery.
9. Standard MCP integration using the official Python SDK.
10. A separate `.venv-mcp` environment.
11. Independent MCP interoperability testing.
12. A fixed arithmetic MCP capability.
13. MCP execution traces and capability manifests.
14. Early performance benchmarks.
15. Security and licensing inventory generation.

The last reported MCP benchmark showed approximately 1.29 ms warm p95 for arithmetic calls and approximately 1.9-second cold broker calls.

However, an initial discovery request timed out, the MCP capability remained disabled by default, and the final milestone verification was not recorded in the supplied progress log.

**Do not assume those findings are still current or that the milestone is complete.**

### First actions

1. Inspect `git status`, `git diff`, recent commits, untracked files, and implementation reports.
2. Identify every change introduced during the interrupted session.
3. Preserve all pre-existing user changes and current working files.
4. Determine whether another Codex process, test process, or implementation task is still running.
5. Never run two conflicting agents against the same working tree.
6. Inspect the current MCP runtime, capability manifest, security restrictions, tests, and feature flags.
7. Reproduce the relevant verification checks before modifying more code.
8. Identify unfinished operations, partial writes, inconsistent generated manifests, and uncommitted migration changes.
9. Check whether the native credential dialog and Stop behavior have received appropriate native verification.
10. Create a precise remaining-work inventory.

Do not revert, reset, clean, overwrite, or discard working-tree changes merely to obtain a clean Git status.

Create:

`docs/implementation/CONTINUATION_STATUS.md`

Record each capability as:

- VERIFIED WORKING
- IMPLEMENTED BUT UNVERIFIED
- PARTIALLY IMPLEMENTED
- BLOCKED
- NOT STARTED

Never label a feature COMPLETE simply because code or documentation exists.

---

# PART 2 — COMPLETE THE FOUNDATION

Before expanding Immortility's privileges, finish the outstanding M0/M1 work.

### Security and reliability

Verify and complete:

- Windows path and reparse-point restrictions.
- Atomic file modifications and rollback.
- Task-scoped, revocable approvals.
- Secret isolation and redacted logs.
- Durable memory recall-exclusion semantics.
- Bounded process-tree cancellation.
- Stop propagation through child workers.
- Native credential-entry verification.
- Accurate provider accounting.
- Per-task and aggregate token budgets.
- Failure handling after partial provider transmission.
- Task trace integrity.
- Clean shutdown and restart recovery.

### MCP integration

Finish the isolated standard MCP implementation.

Use the independently tested, pinned SDK runtime rather than silently modifying Hermes's shared environment.

Investigate the earlier cold-start timeout.

Verify:

- Standard protocol initialization and negotiation.
- Tool discovery.
- Input/output JSON Schema validation.
- Tool invocation.
- Transport errors and timeouts.
- Process ownership and cancellation.
- Malformed/oversized messages.
- Concurrent requests.
- Tool authorization.
- Secret and private-data isolation.
- Restart and reconnection behavior.
- Feature-flag rollback.

A successful arithmetic example is the first interoperability milestone, not proof that arbitrary MCP servers are secure.

Keep unapproved servers disabled.

Review the reported shared-Hermes dependency advisories separately. Do not upgrade the working Hermes environment in place without an isolated compatibility and rollback test.

**Exit condition:** The foundation's required tests and security gates pass, with documented limitations and actual reproducible evidence.

---

# PART 3 — BUILD THE UNIVERSAL CAPABILITY GATEWAY

This is one of the most important missing systems.

Immortility must have one broker-mediated capability interface that allows it to safely discover and use multiple categories of tools.

Support capability adapters for:

- Standard MCP servers.
- REST APIs.
- Authenticated external connectors.
- Local Python tools.
- Fixed native Windows operations.
- Browser automation.
- File and document operations.
- Code intelligence.
- Approved command execution.
- Scheduled workflows.
- Specialist-agent execution.
- Media and artifact generation.

Every capability must define:

1. Unique identifier and version.
2. Input and output schemas.
3. Permissions and side effects.
4. Required secrets and scopes.
5. Resource limits.
6. Timeout and cancellation behavior.
7. Error classifications.
8. Audit and trace metadata.
9. Approval requirements.
10. Feature-flag and rollback behavior.

Build efficient capability discovery so Hermes does not receive hundreds of unnecessary tool descriptions.

Use progressive discovery, tool filtering, schema caching, and task-relevant capability exposure.

Do not create a second unrestricted tool execution channel.

**The Python broker remains the authoritative permission and task-lifecycle boundary.**

---

# PART 4 — COMPLETE REAL WEB RESEARCH AND BROWSER INTELLIGENCE

Implement a capable, grounded research pipeline.

### Required capabilities

- Web search through configured providers.
- Public webpage fetching.
- Deterministic HTML extraction.
- Source attribution and citations.
- Document and PDF ingestion.
- Structured data extraction.
- Research across multiple sources.
- Source comparison and contradiction detection.
- Research result caching.
- URL and domain validation.
- Bounded crawling where specifically required.
- JavaScript-rendered page handling.
- Website navigation.
- Form inspection and drafting.
- Authorized downloads.
- Browser-session isolation.
- Cancellation and timeout handling.

Use the audited lightweight extraction candidate, such as Trafilatura, when appropriate.

Evaluate Playwright as the compatibility baseline and Obscura as an optional alternative.

Use an LLM-driven browser controller only when deterministic automation cannot fulfill the request.

Do not launch several competing browser controllers.

Never bypass authentication, site restrictions or access controls.

Treat website text as untrusted data, not instructions.

### Verification

Test Immortility against genuine public websites, local synthetic websites, dynamic pages, structured documentation and pages containing adversarial instructions.

Verify that retrieved source content actually reaches Hermes and that answers are grounded in that evidence.

**Success means Immortility can conduct useful real research and accurately report its sources, not merely demonstrate an HTTP request.**

---

# PART 5 — COMPLETE WINDOWS COMPUTER CONTROL

Build a properly supervised Windows computer-use system.

Evaluate the audited Cua Driver and pywinauto candidates.

Select one primary controller after testing.

Implement:

- Window discovery.
- Window inspection.
- UI Automation accessibility trees.
- Application identification.
- Semantic UI element selection.
- Authorized clicking and typing.
- File Explorer interaction.
- Controlled application launching.
- Window focus verification.
- Multi-monitor and DPI handling.
- Screenshot-based fallback when necessary.
- Action-result verification.
- Safe interruption.
- Task-scoped permission grants.

All interactions must be mediated through the broker.

Use an interactive Windows user session.

Never silently interact with password dialogs, secure desktops, elevated applications or unrelated windows.

Avoid arbitrary coordinate clicking when structured accessibility information exists.

Do not introduce unrestricted shell execution as a shortcut.

Begin with reversible tasks in scratch applications before allowing sensitive interactions.

**Success means Immortility can perform and verify actual approved desktop tasks on this Windows machine.**

---

# PART 6 — BUILD A REAL AUTONOMOUS SOFTWARE ENGINEERING SYSTEM

Immortility should become a capable coding assistant that can understand existing software and produce working changes.

Implement:

- Repository discovery and structure analysis.
- Language-aware code search.
- Symbol and reference retrieval.
- Dependency inspection.
- Error and stack-trace analysis.
- Change planning.
- Targeted source editing.
- Patch generation.
- Diff inspection.
- Safe Git operations.
- Test generation.
- Controlled test execution.
- Static analysis.
- Linting and type checking.
- Build verification.
- Debugging loops.
- Regression detection.
- Documentation generation.
- Deployment preparation.

Evaluate Serena for read-only code intelligence and token-efficient symbol retrieval.

Do not enable unnecessary Serena shell, REPL, memory or direct-edit capabilities.

Provide isolated execution for project commands and tests with explicit directory, command and resource controls.

Preserve the existing review/approve/rollback workflow.

Model-generated code must not automatically execute with unrestricted Windows user privileges.

A successful coding task must include actual files changed, meaningful test evidence, and any unresolved failures.

---

# PART 7 — IMPLEMENT RELIABLE MULTI-AGENT ORCHESTRATION

Hermes remains Immortility's primary planner.

First evaluate the installed Hermes native subagent/delegation mechanisms against the existing bounded specialist implementation.

Do not blindly integrate CrewAI, LangGraph, AutoGen or another universal agent runtime.

Build or adapt the minimal orchestration capabilities genuinely missing.

Support:

- Supervisor-worker execution.
- Specialist profiles.
- Task decomposition.
- Dependency-aware execution graphs.
- Sequential workflows.
- Parallel independent work.
- Agent handoffs.
- Shared task context.
- Isolated specialist context.
- Structured outputs.
- Result aggregation.
- Independent verification.
- Checkpointing and restart recovery.
- Bounded retries.
- Cancellation propagation.
- Resource scheduling.
- Token and cost limits.
- Agent progress tracking.

Potential roles include:

- Research
- Coding
- Architecture
- Testing
- Data analysis
- Documentation
- Design
- Review

These are reusable roles, not mandatory always-running processes.

Spawn specialist agents only when a task benefits from them.

Evaluate OpenMausBot in a separate compatibility experiment only if it provides measurable advantages over Hermes-native delegation.

Do not grant specialist agents direct permission to bypass the broker.

**Success means a multi-agent task produces verified, useful combined work—not merely several independent model responses.**

---

# PART 8 — IMPLEMENT ADVANCED MEMORY AND CONTROLLED SELF-IMPROVEMENT

Immortility must become more useful through experience without requiring uncontrolled model retraining.

Implement or verify:

### Memory

- Conversation memory.
- Project memory.
- User-approved long-term facts.
- Episodic task history.
- Semantic retrieval.
- Lexical retrieval.
- Hybrid search where justified.
- Provenance and timestamps.
- Memory corrections.
- Deduplication.
- Contradiction handling.
- Retrieval ranking.
- Context compression.
- Forgetting and recall exclusion.
- Export and deletion controls.
- Permission-aware retrieval.

Compare Hermes-native memory with the current broker store before adding GBrain or another memory authority.

Use only one authoritative durable-fact owner.

Add local embeddings and sqlite-vec only if measured retrieval improvement justifies them.

### Self-improvement

Build a controlled feedback loop:

1. Record completed task outcomes.
2. Identify verified failures and user corrections.
3. Extract candidate reusable lessons.
4. Associate each lesson with evidence and confidence.
5. Propose improvements to skills, context selection, tool routing or procedures.
6. Evaluate proposed changes against regression tasks.
7. Promote improvements only when acceptance criteria pass.
8. Support rollback and deletion.

Never let the system silently weaken security, alter budgets or grant itself permissions.

Do not equate storing memories with learning new model weights.

**Success means measurable improvement on repeated task families without privacy or reliability regressions.**

---

# PART 9 — EXTREME MODEL AND TOKEN OPTIMIZATION

I want Immortility to be exceptionally efficient.

The priority is:

**Maximum verified task success per unit of time, cloud cost, memory and compute.**

Implement:

- Correct task-wide usage accounting.
- Parent and subagent budget aggregation.
- Model capability routing.
- Free-provider eligibility checks.
- Optional local model inference.
- No unauthorized paid fallback.
- Exact-match caching.
- Safe semantic caching where justified.
- Retrieval-result caching.
- Selective tool loading.
- Context compression.
- Bounded file and web context.
- Lazy worker initialization.
- Idle worker termination.
- Intelligent retry limits.
- Avoidance of duplicated agent reasoning.
- Small-model routing for appropriate tasks.
- Deterministic local processing whenever possible.
- GPU resource arbitration.

Inspect the actual available model providers and credentials securely without exposing their values.

Having an API key does not establish provider entitlement, quota or compatibility.

Evaluate newer Hermes releases separately and determine whether native routing or delegation improvements should replace custom logic.

Do not upgrade merely because a newer release exists.

On the RTX 4060 laptop, avoid keeping multiple heavyweight GPU workloads resident simultaneously.

Benchmark actual prompt/completion tokens, latency and task outcomes.

Never claim token savings without measurements.

**The primary efficiency metric is cost per successfully completed task, supported by latency and quality measurements.**

---

# PART 10 — COMPLETE VOICE AND MULTIMODAL INTELLIGENCE

Preserve the existing voice implementations and user-selected voice profiles.

Complete:

- Local speech-to-text.
- Voice activity detection.
- Microphone permission handling.
- Speech endpointing.
- Streaming transcription where useful.
- Natural text-to-speech.
- Playback interruption.
- Barge-in.
- Echo handling.
- Voice-worker cancellation.
- Device failure recovery.
- Optional wake-word detection.
- Speech/avatar state events.
- Local OCR and image analysis when needed.
- Consent-controlled multimodal model requests.

Avoid installing another complete speech framework when existing workers suffice.

Use real microphone and audio tests only with appropriate user consent.

Do not activate the previously flagged Qwen runtime until its dependency and execution gates pass.

The existing 3D dashboard and avatar design are outside the scope of this implementation, but required backend speech and state contracts should remain functional.

---

# PART 11 — BUILD THE COMPLETE DOCUMENT AND ARTIFACT ENGINE

Immortility must create actual deliverable files, not just generate text describing them.

Implement a reusable artifact pipeline with:

### Documents

- DOCX creation and editing.
- PDF generation.
- PDF text extraction.
- Formatting and layout.
- Tables, images and citations.
- Document verification.

### Presentations

- Editable PPTX creation.
- Slide layouts.
- Charts and tables.
- Theme and typography.
- Speaker notes where supported.
- Slide rendering and visual inspection.
- Overflow and alignment checks.

### Spreadsheets

- XLSX creation and editing.
- Formulas and references.
- Formatting.
- Data cleaning.
- Financial models.
- Charts.
- Workbook validation.

### Design

- SVG diagrams.
- Flowcharts.
- Architecture diagrams.
- Mermaid.
- Optional Canva integration through authorized supported APIs or tools.
- Local design alternatives where Canva functionality is unavailable.

### Additional artifacts

- CSV.
- JSON.
- Markdown.
- HTML.
- Technical documentation.
- Code repositories.
- Reports containing charts and research references.

Evaluate MarkItDown for ingestion rather than assuming it can generate all output formats.

Use established format-specific libraries and rendering/validation tools.

Each generated artifact must be saved to an authorized output directory and verified through an independent reopen, parse or render step.

A successful artifact request must produce an actual downloadable or accessible file.

---

# PART 12 — COMPLETE EXTERNAL APPLICATION CONNECTIVITY

Immortility should become an expandable, permission-controlled system for interacting with supported external applications.

Build provider-independent integration contracts for:

- GitHub.
- Git providers.
- Google services.
- Microsoft services.
- Calendar and email.
- Cloud storage.
- Notion.
- Slack and Discord.
- Canva.
- Vercel.
- Databases.
- Local developer tools.
- Other approved MCP/API services.

Do not invent provider operations.

Inspect each provider's actual supported API or MCP capabilities.

Implement OAuth or other supported authentication flows where required.

Tokens must be protected and scoped.

Support credential revocation, permission expiry and connection health checks.

Separate read-only actions from side-effecting operations.

Do not send messages, deploy software, delete information, or modify external accounts without appropriate authorization.

Where credentials or provider access are unavailable, complete testable adapters using local fixtures and clearly mark the live integration as blocked.

**Never claim an integration is operational based solely on a mock test.**

---

# PART 13 — IMPLEMENT SCHEDULING AND BACKGROUND AUTOMATION

Add a reliable scheduling layer for approved recurring or conditional tasks.

Evaluate Hermes's native scheduling capabilities first.

Implement:

- One-time schedules.
- Recurring jobs.
- Scheduled research.
- Deployment monitoring.
- Repository checks.
- Reminders.
- Retry and failure handling.
- Restart recovery.
- Task cancellation.
- Resource budgeting.
- Missed-run handling.
- Job history.
- Notifications.

Only one component should own authoritative schedule execution.

All scheduled tool calls must go through the same broker permission boundary as interactive tasks.

Do not silently authorize sensitive future actions because an initial schedule was accepted.

---

# PART 14 — PRODUCTION SECURITY, OBSERVABILITY AND RECOVERY

Ensure every major workflow is:

- Secure.
- Observable.
- Cancellable.
- Recoverable.
- Resource-bounded.
- Permission-controlled.
- Testable.
- Auditable.

Implement:

- Structured logging.
- End-to-end execution traces.
- Tool-call traces.
- Model usage records.
- Token and cost dashboards through existing APIs.
- Consistent error taxonomy.
- Dependency vulnerability scanning.
- Secret scanning.
- License inventory.
- Process health checks.
- Graceful shutdown.
- Backup and restore.
- Durable task-state recovery.
- Data retention controls.
- Safe database migrations.
- Feature-flag rollback.
- Continuous integration tests.

Keep private prompt content, user memories, credentials and sensitive tool outputs out of external telemetry by default.

Do not conflate a model's statement that an action succeeded with independent verification.

---

# PART 15 — COMPLETE END-TO-END CAPABILITY BENCHMARKS

Do not stop after unit tests.

Create a realistic evaluation suite covering these tasks:

**Task A — Autonomous coding**

Given an approved repository, diagnose a real defect, modify code, run authorized tests, and produce a verified patch.

**Task B — Research**

Research a current technical subject, retrieve multiple sources, compare evidence, and generate a cited report.

**Task C — Desktop automation**

Interact with a permitted Windows application, perform a reversible action, and verify the result.

**Task D — MCP connectivity**

Discover an approved MCP server, validate its tools, execute an authorized operation, and correctly reject forbidden operations.

**Task E — Multi-agent collaboration**

Coordinate research, implementation and testing roles to produce one verified artifact.

**Task F — Long-term memory**

Recall approved project context across restarts, apply corrections, and ensure forgotten information is excluded from recall.

**Task G — Document creation**

Generate and validate an actual formatted DOCX and PDF.

**Task H — Presentation creation**

Generate a real PPTX, render slides, and check visual layout.

**Task I — Spreadsheet creation**

Create a workbook with formulas, data and charts; reopen it and validate expected results.

**Task J — Scheduling**

Execute a permitted scheduled job, persist the result and demonstrate restart behavior.

**Task K — Voice**

Accept a consented voice command, process it, speak a response, and support Stop.

**Task L — Model optimization**

Compare different approved routes on identical tasks and measure token usage, success rate, latency and cost.

Every test must distinguish:

- Mocked
- Synthetic local integration
- Real local runtime
- Real external service
- Manual/native verification required

Do not manufacture green results.

Use the existing B0–B12 benchmark requirements from the roadmap, preserving their stricter gates where applicable.

---

# PART 16 — IMPLEMENTATION ORDER AND EXECUTION RULES

Proceed in dependency order.

### M0 — Recover and finish existing work
Complete partial security, lifecycle, ledger, credential and MCP repairs.

### M1 — Universal capability gateway
Implement standard tools, schemas, permissions, discovery and execution.

### M2 — Research and browser intelligence
Complete grounded web retrieval and browser automation.

### M3 — Windows computer use
Implement safe, authorized desktop interaction.

### M4 — Memory and self-improvement
Complete persistent recall, retrieval and controlled learning from experience.

### M5 — Coding and multi-agent execution
Complete repo intelligence, safe code operations and verified delegation.

### M6 — Artifact and document production
Complete DOCX, PDF, PPTX, XLSX, diagrams and optional design integrations.

### M7 — Scheduling and external integrations
Complete durable automation and supported connected services.

### M8 — Full production hardening
Complete end-to-end verification, performance optimization, security, packaging and recovery.

Follow existing roadmap dependencies where they are more specific than these groupings.

Within each milestone:

1. Inspect existing functionality.
2. Identify the smallest remaining vertical slice.
3. Implement it.
4. Add tests.
5. Run actual tests.
6. Fix regressions.
7. Measure performance.
8. Review security and permissions.
9. Record the result.
10. Continue to the next eligible slice.

Do not spend the session generating only documentation.

Do not stop after completing one easy demonstration if more independent engineering work can safely proceed.

If a task is blocked by credentials, platform restrictions or unsafe permissions, document the blocker, keep it disabled and continue with other independent work.

Never hide a failed test by weakening its assertions.

---

# PART 17 — PROGRESS PERSISTENCE AND FUTURE RESUMPTION

Long Codex sessions may end because of tool limits, context limits, execution interruption or session termination.

Design the implementation workflow so progress is never lost.

Maintain:

`docs/implementation/CURRENT_STATUS.md`

Include:

- Current milestone and subtask.
- Last verified working commit or source state.
- Files changed.
- Completed capabilities.
- Tests and exact results.
- Pending issues.
- Current blockers.
- Feature flags.
- Uncommitted changes.
- Next exact engineering action.

Update this file after each validated milestone and before ending a work session when possible.

On every resumed session, read this file and inspect the actual working tree before continuing.

Do not create placeholder implementation reports claiming that future work has already happened.

Do not require me to repeat the full 138-repository audit or master directive in every session.

Do not promise background continuation after the execution session ends.

---

# PART 18 — FINAL ACCEPTANCE CRITERIA

Immortility is not complete merely because all planned modules have files.

It must demonstrate that it can:

1. Accept a complex goal.
2. Plan appropriate steps.
3. Choose relevant tools and models.
4. Retrieve correct context.
5. Execute authorized actions.
6. Delegate independent work when beneficial.
7. Monitor tool and model outcomes.
8. Recover from reasonable failures.
9. Verify results.
10. Produce genuine deliverables.
11. Remember approved useful context.
12. Improve selected behavior through evaluated feedback.
13. Respect permissions, privacy and cost limits.
14. Stop safely on request.
15. Report honestly what succeeded and what did not.

The final report must provide a capability matrix identifying what is:

- Verified in real operation.
- Verified only in local integration tests.
- Implemented but awaiting external authorization.
- Experimental and disabled.
- Blocked.
- Not implemented.

**Never claim the system can do literally anything or access every platform. It must report actual supported capabilities and their limitations accurately.**

## START NOW

First recover the interrupted M0/MCP state from the actual repository, reproduce the latest checks, and close remaining foundation issues.

Then continue implementing the eligible milestones, prioritizing genuine working features over research and documentation.

Preserve the 3D dashboard and existing working behavior.

Optimize relentlessly for capability, correctness, responsiveness, security, minimal cloud tokens and low idle resource usage.

**My objective is a complete, highly capable personal agent platform that performs real work end to end—not another prototype that merely simulates intelligence.**

Proceed with implementation.