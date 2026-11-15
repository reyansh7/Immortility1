# IMMORTILITY — MASTER ARCHITECTURE IMPLEMENTATION DIRECTIVE
## Cloud-Primary Intelligence · Intelligent Multi-Provider Routing · Hermes Orchestration · Persistent Memory · Extreme Performance Optimization

You are the principal AI systems architect, senior agentic-AI engineer, Windows systems engineer and performance engineer responsible for continuing **IMMORTILITY**.

IMMORTILITY is my personal Windows-native AI assistant, combining a powerful cloud-primary intelligence system, optional locally hosted models, advanced agent orchestration, persistent memory, voice interaction, MCP/tool integrations and a futuristic 3D command center.

**This is an implementation directive for an EXISTING working repository. It is NOT permission to rebuild the project.**

Your mission is to evolve the current application into a genuinely capable, fast, resource-efficient, multi-model agentic AI system.

The target is not to accumulate the most AI frameworks.

The target is:

**Maximum verified intelligence + minimum unnecessary latency + minimum wasted cloud tokens + reliable tool execution + persistent context + efficient orchestration.**

---

# 1. READ THE EXISTING PROJECT BEFORE CHANGING ANYTHING

Start by inspecting:

- `AGENTS.md`
- `README.md`
- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/M2_REPORT_ENGINE_CHECKPOINT.md`
- `docs/implementation/M2_REPORT_VERIFICATION.json`
- `docs/implementation/M2_REPORT_LIVE_SMOKE.json`
- `docs/implementation/M2_REPORT_DASHBOARD_SMOKE.json`
- `docs/implementation/M2A_PROGRESS.md`
- `docs/implementation/M2PLUS_MASTER_DIRECTIVE.md`
- Existing provider configuration and Hermes integration
- Broker, capability gateway, Engine/Store and memory code
- Existing dashboard, avatar and voice integration
- The supplied `Immortility_Research_Backed_Final_Architecture.pdf` and editable architecture specification, if available in the workspace

If a referenced document is unavailable, locate its actual equivalent before proceeding. Do not invent its contents.

The earlier research was informed by:

- ReAct
- RouteLLM
- FrugalGPT
- LLMCompiler
- MemGPT
- Lost in the Middle
- Berkeley Function Calling Leaderboard
- tau-bench

Use these as design evidence, not proof that any specific cloud model is superior.

Verify current documentation for the installed versions of Hermes, OpenMausBot and other relevant dependencies before deciding whether additional infrastructure is needed.

## Existing checkpoint

The latest recorded M2 checkpoint reported:

- 285 Python tests passing
- 57 frontend tests passing
- 8 Rust tests passing
- Native Hermes integration operational
- Broker-controlled tool access implemented
- Locally verified Markdown/PDF generation
- Public-source retrieval verified with synthetic drafting
- Native dashboard artifact exports verified
- Genuine real-model report execution blocked by a rejected tool proposal
- DOCX publication blocked pending rendering verification
- Existing native dashboard, Ultron avatar and voice features preserved

These results are historical. Reverify the actual working tree.

**Never restart the project, reset Git, discard untracked work, overwrite concurrent edits or introduce unnecessary replacements.**

Preserve the existing dirty checkout.

Do not commit, push, install applications, download model weights, change system settings or make paid API calls without explicit authorization.

---

# 2. FINAL ARCHITECTURE — NON-NEGOTIABLE

IMMORTILITY must use the following architecture:

```text
USER INPUT
  |
  |-- Text / Files / Images
  |
  |-- Voice -> Local STT
  |
  v
TAURI + REACT COMMAND CENTER
  |
  v
IMMORTILITY BROKER
  |
  |-- Request admission
  |-- Privacy and permission policies
  |-- Context preparation
  |-- Token / cost budgets
  |-- Model eligibility
  |-- Task lifecycle
  |
  v
HERMES AGENT
  |
  |-- Intelligent provider/model router
  |     |
  |     |-- Groq
  |     |-- Gemini
  |     |-- NVIDIA NIM
  |     |-- OpenRouter
  |     |
  |     |-- Manual Local Qwen3.5-9B
  |     |
  |     |-- Manual Local DeepSeek Heretic
  |
  |-- Main reasoning agent
  |-- Tool planning
  |-- Specialist-agent delegation
  |-- Context-aware execution
  |
  v
IMMORTILITY CAPABILITY GATEWAY
  |
  |-- Research
  |-- Coding
  |-- Browser
  |-- Desktop
  |-- MCP / external apps
  |-- Documents
  |-- Scheduling
  |
  v
VERIFIED TOOL EXECUTION
  |
  v
ENGINE / STORE
  |
  |-- Task state and checkpoints
  |-- Persistent memory
  |-- Execution evidence
  |-- Recovery and cancellation
  |-- Resource / token accounting
  |
  v
DASHBOARD + VERIFIED RESULTS + VOICE
```

## Architectural ownership

**Hermes Agent**

The only primary intelligence, planning and agent execution harness.

**Immortility Python Broker**

The authoritative security boundary for provider eligibility, budgets, permissions, capability access, cancellation, credentials and execution accounting.

**Engine/Store**

The authoritative system for durable task state, workflow checkpoints, recovery, scheduling ownership and persisted memory facts.

**Tauri / React / Three.js**

The native user interface, command center, avatar, voice controls and observability.

**OpenMausBot**

An optional specialist integration only when a verified capability gap justifies it.

Do not create a competing orchestrator, scheduler, memory authority or unrestricted tool executor.

---

# 3. PRIORITY ZERO — REPAIR THE REAL HERMES TOOL BRIDGE

Before adding new provider routing complexity, repair the existing genuine model-to-tool execution failure.

The previous live report attempt consumed:

- One authorized provider call
- 1,180 reported tokens
- Zero dispatched tools
- Zero published artifacts

The broker rejected the model's proposed tool invocation.

The exact rejected field was not retained.

## Tasks

Audit:

1. Hermes model tool-call formatting.
2. Provider-specific tool-call envelopes.
3. Streamed tool-call fragments.
4. Argument serialization and validation.
5. Tool identifiers and schema compatibility.
6. Agent bridge normalization.
7. Capability scope validation.
8. Token/context-budget effects.

Reproduce failures using deterministic offline fixtures.

Implement only the compatibility changes justified by evidence.

Maintain strict rejection of malformed or unauthorized actions.

Do not accept arbitrary tool names, relaxed argument schemas or provider-generated permissions.

Add regression tests for valid calls, invalid calls, unavailable tools, malformed streaming chunks, cancellation and provider-specific response shapes.

**Live acceptance requires a newly authorized real-model task.**

The previous authorization has been consumed.

Do not initiate additional cloud inference without fresh consent.

Preserve the existing report-task ceiling of two external calls and 8,000 tokens unless a separate approved change is made.

A genuine end-to-end test must prove:

Real model -> authorized tool proposal -> broker validation -> actual execution -> verified artifact -> durable result.

Only then mark this milestone LIVE VERIFIED.

---

# 4. PRIORITY ONE — INTELLIGENT MULTI-PROVIDER MODEL SYSTEM

Implement a **cloud-primary, capability-aware, cost-aware inference router**.

The default model mode must be:

**AUTO — CLOUD PRIMARY**

The system must use Groq, Gemini, NVIDIA and OpenRouter intelligently according to workload type, model capability, response time, rate limits and verified free-tier availability.

Do not send every request to every provider.

Do not use an additional cloud-model call to classify every request.

## Provider A — GROQ

Credential reference: `GROQ_API_KEY`

Preferred initial responsibilities:

- Fast conversational responses
- Lightweight reasoning
- Text classification
- Structured data extraction
- Low-latency tool rounds
- Time-sensitive interactions

Groq is the high-speed inference candidate.

However, do not blindly route all quick tasks to Groq.

Check actual model availability, supported tool-calling formats, rate limits, quota and success metrics.

Distinguish Groq from xAI Grok.

## Provider B — GOOGLE GEMINI

Credential reference: `GEMINI_API_KEY`

Preferred initial responsibilities:

- Complex planning
- Deep reasoning
- Long-context analysis
- Multimodal understanding
- Large document analysis
- Repository comprehension
- Advanced research and coding tasks

Select an appropriate Gemini model dynamically.

Do not default to the most expensive or largest model for ordinary questions.

Respect account/project-level quotas, privacy terms and free-tier eligibility.

## Provider C — NVIDIA NIM / BUILD

Credential reference: `NVIDIA_API_KEY`

Preferred initial responsibilities:

- Hosted open-weight reasoning models
- Coding-model experimentation
- Specialized instruction-following
- Alternative reasoning routes
- Independent verification when justified

Discover supported models from the actual available provider catalog.

Benchmark them before assigning a permanent responsibility.

NVIDIA-hosted development access must not be treated as unlimited or production-guaranteed.

## Provider D — OPENROUTER

Credential reference: `OPENROUTER_API_KEY`

Preferred initial responsibilities:

- Access to additional eligible AI models
- Model diversity
- Specialized reasoning/coding routes
- Controlled fallback
- Independent benchmarks

Support approved free model variants where actually available.

Never confuse a `$0` model price with unlimited requests.

Respect account limits, upstream routing behavior, model compatibility and provider privacy conditions.

Avoid hidden retries causing unnecessary quota consumption.

## Optional future providers

Support adding additional providers such as xAI without changing the fundamental router architecture.

New providers must not be automatically activated, given credentials, or trusted with private data.

---

# 5. PROVIDER REGISTRY AND MODEL ROUTER

First audit Hermes's native provider support.

Reuse supported adapters wherever possible.

Do not implement four new HTTP clients if Hermes already supports those providers.

Build a broker-owned provider registry that records:

```text
Provider ID
Model ID
Model revision
Credential reference
Supported modalities
Tool-call capability
Structured-output capability
Context window
Provider price / free eligibility
Account quota metadata
Observed rate limits
Request latency
Time to first token
Output throughput
Tool-call correctness
Task success rate
Error rate
Circuit breaker state
Privacy eligibility
Last verification timestamp
```

Do not trust these fields merely because a model advertisement claims them.

Verify the relevant properties through provider documentation, available account metadata and local benchmarks.

## Routing algorithm

Use a deterministic, low-overhead routing algorithm initially.

### Step 1: Hard eligibility filtering

Reject providers/models that fail any required condition:

- Requested model mode
- User privacy restrictions
- Free-only policy
- Account/model availability
- Required tool support
- Required context size
- Required modality
- Remaining budget
- Provider health
- Task deadline
- Broker permission policy

### Step 2: Capability classification

Determine task class using local rules and existing request metadata wherever practical.

Classes may include:

```text
FAST_CHAT
STRUCTURED_EXTRACTION
DEEP_REASONING
CODING
RESEARCH
MULTIMODAL
DOCUMENT_WRITING
TOOL_EXECUTION
PRIVATE_LOCAL
```

Avoid sending the entire user prompt to a cloud classifier simply to select a provider.

### Step 3: Quality-aware route ranking

Among qualified routes, prefer:

1. Sufficient measured task success.
2. Correct tool-call behavior.
3. Lower expected latency.
4. Lower unnecessary token overhead.
5. Adequate rate-limit/quota headroom.
6. Verified zero-cost eligibility.

A fast but unreliable route should not outrank a slightly slower model that reliably completes the task.

### Step 4: Failure handling

Implement:

- Provider health checks
- Rate-limit recognition
- Bounded circuit breakers
- Account-quota tracking
- Safe retry eligibility
- Explicit fallback policies
- Provider-specific error categories

Never silently switch to a paid model.

Never automatically replay side-effecting tool operations after switching providers.

Manual model selection must remain sticky.

Provider credentials must be protected using the existing native secret-storage design.

Never expose keys through frontend bundles, prompts, traces, embeddings, telemetry or generated reports.

---

# 6. MANUAL CLOUD AND LOCAL MODEL MODES

Implement these explicit user-selectable modes:

### MODE 1 — AUTO CLOUD PRIMARY

Default.

The broker selects the most suitable eligible cloud route dynamically.

Local inference is not automatically activated unless explicitly allowed by a separately defined policy.

### MODE 2 — MANUAL CLOUD

User selects a specific provider and model.

The system honors that selection.

Do not silently switch providers because another model is faster.

### MODE 3 — LOCAL QWEN

Model:

`Qwen/Qwen3.5-9B`

Run locally using a reviewed, compatible inference backend and quantization.

### MODE 4 — LOCAL DEEPSEEK HERETIC

Exact requested source model:

`xtools-at/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic`

This is the community-modified Qwen3.5-9B-derived model, not a full DeepSeek V4 deployment.

Evaluate a compatible 4-bit GGUF conversion.

## Local inference rules

Hardware target:

- RTX 4060 laptop GPU
- Approximately 8 GB VRAM
- 16 GB system RAM
- Existing 3D dashboard and voice runtime

Prefer a verified Hermes-managed local-model integration if available and compatible.

Otherwise evaluate llama.cpp with an OpenAI-compatible loopback endpoint.

Run only one local language model at a time.

Lazy-load on selection and unload when appropriate.

Never silently download multiple gigabytes of model weights.

Never replace GPU drivers or globally change CUDA/runtime dependencies without approval.

Local-only mode must guarantee:

- No cloud inference
- No automatic cloud fallback
- No remote model telemetry
- No remote provider tools
- No private content sent to cloud services

Use actual network-isolation tests, not UI labels alone.

## Local capability tiers

Maintain two different acceptance levels:

**Local Chat**

Bounded context, offline Q&A, summarization and local inference.

**Local Agent**

Hermes integration with actual tool-calling, sufficient context capacity and full broker-controlled execution.

Validate Hermes's documented context requirements against the pinned installed version.

Do not claim a 9B local model can reliably run the full Hermes agent workflow merely because a small-context chat test succeeds.

Benchmark local RAM, VRAM, throughput, load time and dashboard responsiveness.

---

# 7. ADVANCED HERMES AGENT ORCHESTRATION

Hermes remains the lead agent.

Reuse verified native delegation capabilities.

Do not build a second agent framework.

## Logical agent roles

Support bounded task-specific roles:

- Lead / planner
- Research
- Coding
- Reviewer
- Document generation
- Browser
- Computer use
- Local assistant

Roles do not mean always-on agent processes.

## Execution strategies

### FAST PATH

For simple tasks:

One suitable model request.

No delegation.

No unnecessary tool initialization.

### TOOL PATH

For a task requiring actions:

One Hermes lead agent using only authorized broker tools.

### TEAM PATH

For a complex divisible task:

Hermes creates a small dependency-aware plan.

Independent work can execute concurrently.

Dependent work waits for required verified results.

### RECOVERY PATH

Engine/Store persists task state and original deadlines.

Reconnect or restart retrieves evidence instead of blindly repeating model calls.

## Agent contract

Each delegated task must specify:

```text
Task ID
Parent task ID
Agent role
Goal
Input context references
Output contract
Approved tools
Permission scope
Provider/model profile
Maximum model calls
Token budget
Deadline
Cancellation state
Verification requirements
```

Subagents should receive the minimum required context.

They should return short, verified results instead of entire conversation transcripts.

Prevent concurrent conflicting file writes.

Use separate worktrees or another tested isolation approach for independent coding agents.

Do not launch additional agents unless expected quality or speed improvements justify the overhead.

## OpenMausBot

Audit the installed OpenMausBot version and current capabilities.

Use it only for verified specialist workflows or computer-use capabilities that Hermes plus the broker cannot already provide adequately.

Never allow OpenMausBot to create a separate permission authority, scheduler or unrestricted controller.

---

# 8. UNIFIED LONG-TERM MEMORY SYSTEM

Design one coherent memory architecture shared across authorized cloud and local inference modes.

A user must not lose relevant task context merely because they switch from Gemini to Groq or to a local model.

**Engine/Store remains the authoritative durable memory owner.**

Hermes native memory should provide a compact projection of relevant information, not an independently contradictory memory database.

## Required memory classes

**Working memory**

Recent session turns, active plan and current evidence.

**Semantic memory**

Stable preferences, confirmed facts and corrections.

**Project memory**

Repository state, decisions, milestones and project-specific context.

**Episodic memory**

Task histories, previous results, failures and successful fixes.

**Procedural memory**

Verified skills, approved workflows and reusable instructions.

## Storage strategy

Prefer:

- Existing SQLite storage
- WAL mode
- FTS5 search
- Structured fact records
- Provenance and timestamps
- Project/scope isolation
- Corrections and supersession
- Configurable retention

Do not automatically introduce a vector database.

Benchmark lexical retrieval first.

Add local embeddings or vector similarity only if measured recall improvements justify the complexity.

## Context engineering

Before inference:

1. Identify the current task.
2. Retrieve relevant verified task state.
3. Retrieve the smallest useful memory packet.
4. Include only necessary tool schemas.
5. Include directly relevant source excerpts.
6. Preserve source identities and provenance.
7. Deduplicate repeated information.
8. Reserve completion and tool-result token headroom.
9. Enforce privacy restrictions.

Never send entire past conversations automatically.

Never send unrelated personal history into research or coding tasks.

Do not store guessed model outputs as confirmed facts.

Memory must support user correction, inspection and deletion.

---

# 9. EXTREME TOKEN OPTIMIZATION

Immortility must minimize unnecessary cloud consumption without making difficult tasks less capable.

Implement:

- Deterministic request triage
- Task-specific context construction
- Selective tool schema exposure
- Stable prompt prefixes where caching is supported
- Provider-aware token counting
- Cached source retrieval
- Evidence references instead of duplicate large payloads
- Compact agent handoffs
- Bounded agent loops
- Adaptive task budgets
- Bounded retries
- Shared quotas across tasks
- Rate-limit-aware concurrency
- No cloud calls for hashing, rendering, parsing or other deterministic processing
- No unnecessary reviewer agent
- No repeated inference after reconnect
- No paid fallback

Do not call a separate model simply to route every task.

Do not default to running three models and voting.

Do not automatically use smaller models if their failure/retry rate increases total cost and latency.

Track:

```text
Prompt tokens
Completion tokens
Cached tokens
Provider requests
Provider/model selected
External model calls per task
Subagent calls
Tool round trips
Time to first token
End-to-end latency
Provider errors
Quota remaining
Verified task completion
Estimated and confirmed cost
```

Distinguish provider-reported usage, locally estimated usage and synthetic fixture accounting.

Never claim an exact cost or token saving without measurements.

---

# 10. MEMORY, TOOL AND EXECUTION SECURITY

Maintain the existing Immortility capability gateway.

All model-proposed actions must pass:

```text
Exact tool identity
Typed schema
Argument validation
Task scope
Credential scope
User permissions
Expiry and cancellation state
Privacy policy
Execution limits
```

Never treat retrieved web content or tool output as authoritative instructions.

Do not expose arbitrary unrestricted shell, browser, file access or MCP capabilities by default.

Provider-hosted tools must remain disabled unless explicitly reviewed because they can bypass local broker enforcement.

Enforce sensitive-operation approval for:

- Email or message sending
- External account changes
- Git pushes and deployment
- Purchases
- Deletion
- Software installation
- Security setting changes
- Private file uploads
- Privileged computer control

Retain safe diagnostics without logging private provider arguments or secrets.

Do not weaken rejection rules to accommodate unreliable models.

---

# 11. RELIABLE BACKGROUND TASKS AND SCHEDULING

Reuse Engine/Store.

Do not create another scheduler.

Implement and verify:

- Task persistence
- Dependency checkpoints
- Original deadlines
- Cancellation
- Worker crash recovery
- Reconnection without duplicate inference
- Idempotent tool-result handling
- Side-effect reconciliation
- Approval expiration
- Provider rate-limit waiting
- Accurate completion receipts

A task must not be marked successful merely because a model says it completed.

External actions and generated files require independent verification.

Unattended cloud execution requires separate authorization and explicit budgets.

---

# 12. VOICE AND 3D DASHBOARD INTEGRATION

Preserve the current Tauri/React/Three.js command center and Ultron avatar.

Do not redesign, replace or remove existing visual assets.

## Voice

Target pipeline:

```text
Microphone
  -> VAD / local STT
  -> Transcript
  -> Immortility Broker
  -> Hermes
  -> Verified result
  -> Local TTS
  -> Ultron avatar
```

Reuse the existing working voice foundation and evaluate Handy integration where appropriate.

The voice system and text system must share the same task pathway.

Ensure speech cancellation, task cancellation and avatar state do not become inconsistent.

## Dashboard

Add or enhance the following views without clutter or regression:

**Model Hub**

- Auto Cloud Primary
- Manual Cloud
- Local Qwen
- Local Heretic
- Current model
- Provider availability
- Quota/usage
- Mode switching

**Agent Network**

- Active lead agent
- Specialist agents
- Task dependencies
- Execution status
- Tool activity

**Memory Center**

- Project knowledge
- Stored preferences
- Memory search
- Corrections and privacy controls

**Usage Monitor**

- Provider/model
- Tokens
- Calls
- Latency
- Limits
- Errors
- CPU/RAM/GPU use

**Workflow Center**

- Running tasks
- Queued work
- Blocked approvals
- Restart/recovery state
- Stop controls

Preserve the current artifact library and verified report export system.

Keep 3D rendering isolated from model inference and heavy workers.

Under local model GPU pressure, reduce nonessential visual workload without degrading the core interaction experience.

---

# 13. PERFORMANCE ENGINEERING

All major decisions must be benchmarked.

These are proposed targets, not claims of achieved performance:

- Warm broker admission: under 50 ms p95 where no external I/O is required
- Cached route decision: under 10 ms p95
- Local UI acknowledgement: under 150 ms p95
- Fast eligible cloud response: optimize first-token latency toward 1.5 s p50 where feasible
- Zero unauthorized paid model calls
- Zero unauthorized cloud requests in Local Only mode
- Zero duplicate side effects across the tested crash/retry corpus
- Zero leaked provider keys in frontend bundles and traces
- No unnecessary persistent GPU model processes

Measure:

- Cold and warm startup
- Model selection overhead
- Full request duration
- Tool round-trip latency
- Token overhead
- CPU/RAM usage
- GPU VRAM
- Provider failover behavior
- Cancellation latency
- Memory retrieval time
- Dashboard frame stability
- Resource cleanup

Never report configured resource ceilings as measured usage.

Do not add Docker, Redis, Kubernetes, a vector server or another service simply because it is common in agentic-AI stacks.

Every new dependency needs a demonstrated benefit.

---

# 14. BENCHMARK SUITE

Build a representative test corpus before optimizing routing weights.

Suggested coverage:

- 30 short chat/extraction tasks
- 20 tool-call contract scenarios
- 15 coding tasks
- 10 research tasks
- 10 memory/recall tasks
- 10 security and prompt-injection scenarios
- 10 crash/cancel/restart scenarios

Use deterministic offline fixtures wherever possible.

When real provider benchmarks are authorized, use the same representative workload and evaluate:

- Actual success
- Tool-call correctness
- Structured output validity
- Latency
- Tokens consumed
- Rate-limit failures
- Cost eligibility
- Recovery behavior

Keep held-out tasks for evaluating routing improvements.

Do not train an additional model router until evidence demonstrates that deterministic routing is insufficient.

---

# 15. MANDATORY IMPLEMENTATION ORDER

Do not attempt to implement the full architecture in one uncontrolled change.

## M2 — COMPLETE THE EXISTING TOOL BRIDGE

Repair the real-model tool proposal incompatibility.

Finish offline contract verification.

Preserve Markdown/PDF report generation.

Investigate DOCX rendering independently, without installing software or enabling unverified publication.

Request fresh authorization before genuine cloud acceptance.

## M3A — MULTI-PROVIDER REGISTRY

Implement:

- Groq
- Gemini
- NVIDIA
- OpenRouter
- Protected credential references
- Provider/model capability metadata
- Manual Cloud mode
- Auto Cloud Primary mode
- Free-price/permission enforcement
- Account-quota and failure-state handling

Use existing Hermes provider functionality wherever verified.

Create deterministic offline provider adapters/fixtures for tests.

## M3B — INTELLIGENT ROUTER

Implement:

- Deterministic request classification
- Capability-aware model selection
- Provider eligibility filtering
- Benchmark-based ranking
- Circuit breakers
- Token accounting
- Safe fallback
- Dashboard route visibility

Do not use live model calls without approval.

## M4 — MANUAL LOCAL AI

Integrate:

- Qwen3.5-9B
- DeepSeek-V4-Pro-Qwen3.5-9B Heretic
- Compatible local inference server
- Manual-only mode switching
- One-model-at-a-time loading
- VRAM management
- Cloud-isolation tests

Model downloading and installation require explicit authorization.

## M5 — CONTEXT AND MEMORY

Complete:

- Unified durable memory authority
- Scope-aware retrieval
- Project knowledge
- Episodic summaries
- Corrections
- Context token budgets
- Provider-switch continuity

## M6 — HERMES MULTI-AGENT DELEGATION

Implement:

- Role-specific agent contracts
- Provider selection per agent
- Bounded subagent budgets
- Dependency-aware execution
- Parallel independent work
- Safe concurrent code editing
- Compact verified result handoffs

## M7 — ADVANCED TOOLS

Expand independently verified research, browser, coding, MCP, document and desktop capabilities.

Do not enable unrestricted computer control.

## M8 — SYSTEM POLISH

Complete:

- Voice acceptance
- Dashboard observability
- Task-state synchronization
- Scheduling/recovery UX
- GPU/CPU optimization
- End-to-end reliability benchmarks

---

# 16. IMPORTANT EXECUTION RULES

### Preserve current work

Do not modify unrelated UI, avatar, voice or GPU code.

Do not discard another agent's concurrent edits.

### Build incrementally

After each feature, run its focused regression tests.

Update the engineering checkpoint.

### Maintain authorization

Local, reversible development and offline tests may proceed.

Ask before real inference, private uploads, downloads/installations, paid requests, external account actions, deployments or Git pushes.

### Be honest about status

Use these labels:

- IMPLEMENTED
- OFFLINE VERIFIED
- NATIVE VERIFIED
- LIVE VERIFIED
- BLOCKED

Do not call a synthetic provider smoke test a genuine cloud-model acceptance.

### Never chase test counts

Do not delete tests or weaken security checks to make the build pass.

### Preserve existing budgets

The M2 report task currently has a two-call/8,000-token ceiling.

Do not silently relax it when introducing broader task profiles.

### Use official documentation

Verify the installed framework versions and relevant provider documentation before relying on optional features.

### No unnecessary frameworks

Reuse Hermes, Engine/Store, the capability gateway and existing voice/dashboard infrastructure.

---

# 17. WHAT I EXPECT FROM THIS EXECUTION

Begin by:

1. Reading the current checkpoint and Git status.
2. Mapping the existing Hermes/provider architecture.
3. Identifying which planned features already exist.
4. Inspecting the rejected M2 tool-call path.
5. Producing a concise implementation plan with specific file-level changes.
6. Completing safe offline bridge repairs and tests.
7. Building the M3A provider registry and manual/automatic model-mode foundation where independent of blocked live acceptance.
8. Implementing offline route selection, accounting, error handling and tests.
9. Verifying security, performance and frontend integration.
10. Updating the relevant checkpoint documents.

Do not get stuck repeating audits already completed.

If the live M2 acceptance is blocked by authorization, continue independent M3 offline work without pretending the M2 gate has passed.

**The immediate deliverable is M2 repair plus the verified M3 provider-routing foundation.**

Do not silently expand into downloading local models, building a new memory framework, replacing the dashboard or activating unrestricted agents in the same implementation slice.

Implement later milestones incrementally only after their prerequisites are satisfied.

## Final engineering report

Report:

- Exact code changes and file paths
- Existing capabilities reused
- Providers integrated and their tested modes
- Routing behavior
- Token/budget accounting
- Unit and integration test results
- Benchmarked performance
- Credential and privacy verification
- UI changes
- Remaining blockers
- What is implemented versus actually verified
- Next engineering milestone

Update `docs/implementation/CURRENT_STATUS.md` and create or update the relevant M3 checkpoint and machine-readable verification evidence.

---

# FINAL OBJECTIVE

Build IMMORTILITY into an exceptionally capable **cloud-primary, local-capable, fast, secure and token-efficient personal AI system**.

I should be able to speak or type naturally, have Hermes understand and plan the task, automatically select the best eligible cloud model from Groq, Gemini, NVIDIA or OpenRouter, delegate only when beneficial, execute authorized tools, remember relevant information, verify actual results and communicate through my existing 3D command center.

I must also be able to switch manually to either Qwen3.5-9B or my exact DeepSeek Heretic model and operate privately without cloud inference.

**One lead intelligence harness. One broker. One workflow authority. One coherent memory architecture. Multiple intelligently selected AI models. Minimal unnecessary token expenditure. Maximum verified capability.**

Begin with the existing codebase, not a new implementation.