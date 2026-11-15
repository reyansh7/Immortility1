# IMMORTILITY — MASTER ENGINEERING DIRECTIVE
## Build a Fast, Capable, Reliable Personal AI — Without Overengineering

You are the principal AI systems architect, senior systems engineer, performance engineer, and implementation agent responsible for developing **IMMORTILITY**.

Immortility is intended to become a deeply capable Windows personal AI assistant inspired by the experience of JARVIS and Ultron.

This is not simply a chatbot with an attractive interface.

It must become a practical AI system capable of understanding natural-language instructions, reasoning, using tools, controlling authorized applications, performing coding and research tasks, managing files and workflows, and maintaining useful context across conversations and models.

**The objective is maximum practical intelligence, capability, responsiveness, reliability, and usage endurance with minimum unnecessary complexity.**

Do not interpret this ambition as permission to introduce dozens of agents, frameworks, services, databases, or custom infrastructure.

Our guiding engineering principle:

**Maximum capability. Minimum moving parts. Near-instant interaction. Verified execution. Zero unintended expenditure.**

---

# 1. FIRST: CONTINUE THE EXISTING M3 WORK

You were interrupted while implementing and validating the M3 integration.

Do not abandon, restart, overwrite, or prematurely mark that work complete.

Current reported checkpoint:

- The 180-second synthetic native event-stream test previously succeeded, including reconnect and event replay.
- That fixture did not execute a real model or tool.
- The frontend build passed after the earlier approval interruption.
- Runtime status notifications received task-busy and voice-busy state changes.
- Model Hub correctly blocked mode changes during busy and pending states.
- A delayed-selection test recorded exactly one broker mode-change request.
- A failure-recovery test revealed that the model-selection error banner was hidden while Settings was open.
- A UI fix for that error was subsequently edited.
- The intended 95-second silent-stream test was cancelled around 36 seconds, before the 90-second read-idle timeout.
- That timeout acceptance case therefore remains unpassed.
- The latest interruption occurred after additional edits to approximately nine files, without a final verified acceptance report.

These are reported observations, not proof that the current working tree is complete.

## Your immediate actions

1. Read `AGENTS.md`, the current implementation status, M3 integration worklog, relevant architecture directives, and affected source files.
2. Inspect Git status, uncommitted changes, and actual test results.
3. Preserve the existing dashboard, Ultron avatar, audio/voice development, and any concurrent work.
4. Review the latest Model Hub failure-banner fix.
5. Complete the interrupted native acceptance tests.
6. Instrument the silent-stream cancellation path so the originating HTTP route, action category, task ID, and reason can be identified without exposing secrets.
7. Verify the actual timeout behavior instead of counting an early cancellation as success.
8. Confirm reconnect, replay, cancellation, cleanup, and exactly-once completion behavior.
9. Re-run relevant Python, Rust, TypeScript, frontend, and native checks.
10. Update documentation using only actual evidence.

Do not bypass approval reviews, weaken security checks, or silently switch to less protected execution paths.

If a validation remains blocked, document the exact blocker and preserve the last working state.

**Finish M3 correctly before implementing additional architecture.**

---

# 2. FINAL TARGET ARCHITECTURE

Keep the production architecture intentionally small.

The preferred runtime is:

```text
                    IMMORTILITY
             Tauri + React + Three.js
          Dashboard | Voice | Bots | Tasks
                         |
                         v
                 PYTHON BROKER
       Security | Task Lifecycle | Budgets
          Shared Context | Checkpoints
                         |
                         v
                 WARM HERMES AGENT
          Reasoning | Planning | Tools
              Native Delegation
                         |
                         v
              MODEL ACCESS LAYER
          Hermes Native Providers
                         OR
              Optional OmniRoute
                         |
             +-----------+-----------+
             |           |           |
           Gemini       Groq        NVIDIA
             |           |           |
             +------ OpenRouter -----+
                         |
                 Local Qwen3.5-9B
                   (On Demand)
```

This diagram represents logical responsibilities, not a requirement to create a separate service for each box.

The broker's shared durable context and task state must remain accessible to Hermes and authorized specialist agents.

## Authoritative responsibility ownership

**Tauri / React**
- User interaction
- 3D dashboard and avatar
- Voice controls
- Task visibility
- Bots workspace
- Streaming output
- Settings and model status

**Existing Python Broker**
- Permission enforcement
- Task lifecycle
- Cancellation and recovery
- Context and persistence coordination
- Budget enforcement
- Provider policy
- Security boundaries
- Audit logging

**Hermes**
- Main intelligence
- Planning and reasoning
- Registered tool invocation
- Native subagent delegation
- Model interaction
- Existing agent capabilities

**Optional OmniRoute**
- Provider/model selection
- Quota-aware routing
- Provider failover
- Inference telemetry

**Existing persistent storage**
- Conversation history
- Relevant memory
- Task checkpoints
- Agent outcomes
- Provider transitions
- Tool execution state

Keep one authoritative owner for each function.

Do not introduce a new always-running process when a module within an existing process is sufficient.

---

# 3. TOP PRIORITY: MAKE HERMES WARM AND RESPONSIVE

The most important near-term improvement is removing avoidable latency from starting and interacting with Hermes.

Audit the current lifecycle before changing it.

Determine whether Hermes is started separately for each task, whether its dependencies are repeatedly initialized, and which parts can safely remain warm.

Where beneficial, implement a supervised warm execution mechanism.

Requirements:

- No unnecessary full Hermes startup for each conversation turn.
- Reuse initialized model clients, compatible connections, and safe tool registrations where possible.
- Do not share mutable task-specific state unsafely.
- Support concurrent task admission with explicit concurrency limits.
- Preserve cancellation, restart recovery, and process cleanup.
- Detect dead or unhealthy workers.
- Recover without silently duplicating tool side effects.
- Avoid retaining large unused model contexts in memory.
- Avoid constant background CPU activity.

Benchmark cold and warm execution.

Do not implement a large custom worker framework if Hermes already provides suitable persistent execution facilities.

## Interaction responsiveness

The interface must acknowledge the user's action without waiting for a cloud model response.

For example:

User: "Immortility, research this architecture and build a prototype."

Expected experience:

1. The request is immediately accepted into a real task lifecycle.
2. Immortility displays or speaks a short acknowledgement once acceptance is confirmed.
3. The assistant plans using the appropriate model.
4. Authorized tools and agents execute.
5. Task progress streams into the dashboard.
6. The user can interrupt, inspect, pause where supported, or cancel.
7. The assistant reports verified results and any incomplete work.

Do not fabricate progress.

Never announce that a task has started before the broker has actually accepted or scheduled it.

For long-running tasks, return control to the interface immediately while the supervised task executes. Do not block the UI waiting for completion.

---

# 4. REAL MODEL-TO-TOOL EXECUTION

This is more important than adding another AI framework.

Immortility must go beyond generating text that describes what it would do.

It must reliably perform authorized actions through real tools.

Examples:

- Read and edit files.
- Search project directories.
- Run controlled terminal commands.
- Execute tests.
- Debug applications.
- Research the web using actual sources.
- Generate documents and reports.
- Interact with browsers.
- Control approved desktop applications.
- Use available MCP integrations.
- Create and manage permitted scheduled workflows.

Use Hermes' verified native tool interfaces first.

Keep the Python broker authoritative for permissions and task execution policy.

Preserve registered tool names, typed schemas, authorization checks, and audit trails.

Implement a genuine end-to-end acceptance test:

```text
User request
   -> Hermes model interprets request
   -> Model selects registered tool
   -> Broker authorizes invocation
   -> Real tool executes
   -> Result returns to model
   -> Model responds using actual result
   -> UI displays verified completion
```

Test successful execution, authorization denial, timeout, cancellation, malformed model output, interrupted connections, and partial failure.

Do not count synthetic fixture events as evidence of real tool-use success.

Use safe, deterministic, non-destructive test operations for initial acceptance.

Require explicit authorization for destructive or sensitive operations.

The ambition is broad capability within clear permissions—not unrestricted execution.

---

# 5. MODEL ORCHESTRATION — BALANCED STRATEGY

Available intended inference sources:

1. Google Gemini API
2. Groq Cloud API
3. NVIDIA-hosted model APIs
4. OpenRouter
5. Local Qwen3.5-9B

Use strong cloud models for difficult reasoning and coding, fast cloud models for routine interactions, and local inference when appropriate.

Do not prioritize local models automatically merely because they are local.

## Preferred routing behavior

**Complex reasoning / architecture**
- Strongest suitable available cloud model.

**Complex coding**
- Best verified coding-capable cloud model.

**Routine conversation**
- Fast, reliable, quota-available model.

**Classification / summarization / simple extraction**
- Lightweight cloud model or local Qwen.

**Background operations**
- Cheapest suitable inference route, or deterministic tools where possible.

**Cloud quota exhaustion**
- Compatible fallback model.
- Local inference where capability permits.
- Otherwise pause or queue the task transparently.

Verify exact available model IDs, capabilities, free-tier eligibility, and provider quotas before configuring them.

## OmniRoute adoption policy

OmniRoute is a candidate, not a mandatory dependency.

First audit Hermes' installed provider routing, fallback, configuration, and quota capabilities.

Then evaluate OmniRoute in isolation.

Compare the same model and workload through:

- Hermes direct provider access.
- Hermes through OmniRoute.

Benchmark:

- Request routing overhead
- Time to first streamed token
- End-to-end latency
- Tool-calling compatibility
- Structured output reliability
- Cancellation
- Fallback behavior
- Memory continuity
- CPU and RAM usage
- Credential security
- Configuration and maintenance complexity

Use at least 30 representative paired requests for latency analysis where permitted by quotas and budgets. Use mocked providers for exhaustive error-path testing.

**Enable OmniRoute in production only if its routing benefits justify its complexity and measured overhead.**

If Hermes native capabilities provide sufficiently good routing with less overhead, retain them instead.

Do not install LiteLLM or another competing model gateway.

Do not route every request through an extra LLM-based classifier.

Use deterministic routing rules, verified capability metadata, quota state, and lightweight heuristics wherever possible.

---

# 6. MAXIMUM USAGE WITH STRICT ZERO SPEND

The user intends to interact with Immortility heavily throughout the day.

We need the greatest sustainable usage possible within legitimate provider limits.

This does NOT mean unlimited free cloud inference is guaranteed.

Implement a strict default zero-spend policy:

- No paid-model fallback without explicit user authorization.
- No automatic credit purchases or service upgrades.
- No use of an endpoint merely because it appears cheap.
- Every selectable cloud model must have verified free eligibility or an explicitly authorized spending policy.
- Unknown pricing or quota status must fail closed.
- Track provider/model request counts and known token usage.
- Respect RPM, TPM, daily quotas, cooldowns, and provider retry instructions.
- Use bounded retries with exponential backoff and jitter.
- Apply circuit breakers to failing endpoints.
- Never circumvent provider rate limits or terms of service.

If all suitable providers are unavailable, explain the condition and continue using appropriate local tools or local inference rather than silently switching to a paid endpoint.

## Token efficiency

Avoid:

- Replaying complete histories on every request.
- Calling a model to classify obviously deterministic commands.
- Spawning agents for trivial tasks.
- Repeatedly analyzing unchanged files.
- Sending identical tool results multiple times.
- Unnecessary agent debates.
- Repeated model calls when cached data is still valid.

Implement selective context retrieval, prompt-prefix caching where supported, tool-result caching when safe, bounded output, and compact agent handoffs.

Preserve correctness over token savings.

Measure requests and tokens per completed task, not merely individual API latency.

---

# 7. MEMORY — CONTEXT MUST SURVIVE MODEL CHANGES

Immortility must own its durable context independently of any provider.

A task might start with Gemini and later continue using NVIDIA or Groq.

It should retain:

- User-visible conversation history.
- Project decisions and relevant facts.
- Current task objective.
- Completed steps.
- Authorized tool execution results.
- File and artifact references.
- Failed attempts and retry state.
- Relevant checkpoints.
- Outstanding dependencies.

Use existing Hermes memory facilities wherever appropriate.

Do not introduce a second independent personal-memory authority.

Use the existing broker storage architecture and SQLite where suitable, after inspecting the current implementation.

Separate:

1. **Conversation history:** Durable record of exchanges.
2. **Long-term memory:** Important retrievable knowledge.
3. **Task execution state:** Operational checkpoints and tool outcomes.

These can use one underlying database while maintaining clear logical separation.

## Critical requirement

Memory continuity is not achieved by dumping an entire conversation into every prompt.

Implement selective context assembly.

Simple interactions should require little or no expensive retrieval.

Long-running tasks should receive concise, relevant checkpoints.

For model handoffs, preserve standardized messages and verified tool outcomes.

Do not assume proprietary hidden reasoning states or all provider-specific tool formats can be transferred perfectly.

Maintain explicit provenance and avoid treating unverified generated summaries as facts.

Support restart recovery without losing committed state.

Any data retention or indexing must honor user privacy and deletion controls.

---

# 8. AGENT ORCHESTRATION — ONE COORDINATOR, MINIMUM AGENTS

Do not build an unnecessarily complex agent swarm.

Hermes remains the sole primary reasoning coordinator.

Prefer native Hermes delegation over external frameworks.

Default policy:

- Normal conversation: zero subagents.
- Simple tool request: zero subagents.
- Research task: optionally one specialist.
- Complex independent subtasks: at most two concurrent specialists initially.
- Multi-step workflows: bounded delegation with a clear task graph.
- Background bots: on-demand rather than constantly active.

Avoid recursive, uncontrolled agent spawning.

Each delegated task should have:

- Explicit objective
- Required context
- Tool permissions
- Model capability requirements
- Time and token budgets
- Completion criteria
- Structured result
- Cancellation path

Agents should not repeatedly exchange unproductive messages.

The parent Hermes agent should consolidate results and perform necessary verification.

## Bots workspace

The existing idea of a Bots tab should remain.

Initially, use it to organize Hermes-backed specialist bots with separate sessions and permissions.

Do not install OpenMausBot merely to populate the tab.

Evaluate an external bot runtime only when a concrete missing capability—such as specialized computer-use isolation—has been demonstrated.

Keep a single authoritative task scheduler and avoid concurrent controllers manipulating the same desktop session.

---

# 9. LOCAL QWEN3.5-9B — ON-DEMAND ONLY

The development computer has approximately:

- NVIDIA RTX 4060 laptop GPU
- 8 GB VRAM
- 16 GB RAM

Do not force a 9B local model to remain loaded permanently.

Evaluate quantized inference appropriate to the available memory.

Use the local backend selectively for supported tasks and cloud-quota fallback.

Measure:

- Model load time
- Tokens per second
- RAM and VRAM usage
- Prompt processing latency
- Quality of tool calls
- Concurrent impact on the 3D dashboard
- Impact on voice responsiveness

Prefer lazy loading and controlled model unloading where practical.

Do not allow local inference to freeze the interface or destabilize Hermes.

Do not automatically load multiple large local models.

---

# 10. VOICE AND CONVERSATIONAL EXPERIENCE

Immortility is ultimately a conversational assistant.

The desired experience is natural, quick, and interactive.

Architect for:

- Low-latency speech recognition.
- Streaming text responses.
- Early spoken acknowledgement where appropriate.
- Interruptible TTS.
- User barge-in.
- Cancellation by voice.
- Natural turn-taking.
- Task-status announcements.
- Voice and text operating on the same task/session.
- Consistent context across modalities.

Do not block speech playback until an entire long response has been generated.

Do not make the system narrate every internal tool call.

Keep acknowledgements concise and task execution observable.

Preserve existing voice work and its selected voice identity.

Prioritize reliable turn-taking and actual task execution over cinematic voice effects.

Avoid running unnecessarily heavy STT, TTS, local inference, and 3D rendering simultaneously when resource pressure becomes excessive.

---

# 11. PERFORMANCE — ENGINEER FOR A FAST ASSISTANT

Treat latency as a primary architectural concern.

Instrument the complete path:

```text
User input
   -> UI acknowledgement
   -> Broker admission
   -> Hermes readiness
   -> Context assembly
   -> Model routing
   -> Provider first token
   -> Tool execution
   -> Streamed response
   -> Task completion
```

Record latency by stage.

Avoid measuring only overall response time.

## Initial engineering targets

These are targets to validate on the actual hardware, not guarantees.

- UI interaction feedback: under 50 ms under normal load.
- Local task acknowledgement: preferably under 150 ms.
- Broker admission overhead: under 20 ms p95.
- Additional model-gateway overhead: target under 30 ms p95.
- Common local context lookups: under 50 ms p95.
- No full Hermes cold start for every message.
- Provider streams forwarded without unnecessary buffering.
- Responsive UI while long-running tasks execute.
- Minimal idle CPU/GPU consumption.
- No polling loops that can be replaced by existing event-driven notifications.

Measure p50, p95, and worst-case behavior where useful.

Use reproducible benchmarks.

Do not report success simply because a synthetic test meets a target.

## Optimization priorities

1. Eliminate unnecessary process startup.
2. Eliminate unnecessary model calls.
3. Reduce context assembly overhead.
4. Maintain persistent compatible connections.
5. Stream results immediately.
6. Reduce redundant UI rendering.
7. Eliminate duplicate agent orchestration.
8. Bound parallel workload.
9. Prevent GPU/RAM contention.
10. Profile before adding caching or complexity.

Keep routing decisions computationally cheap.

Do not introduce prompt-compression models, embedding pipelines, or rerankers into the interactive hot path unless benchmarks show a net benefit.

---

# 12. DESIGN FOR BROAD CAPABILITY, NOT ENDLESS FRAMEWORKS

Immortility should be extensible enough to support many legitimate tasks.

But broad capability should come from reliable tools, well-defined interfaces, permissions, and strong reasoning models—not hundreds of resident agents.

Use existing Hermes tools, approved MCP servers, and verified integrations.

Prefer adding capabilities as modular, lazy-loaded tools.

Examples of future capability domains:

- Software engineering
- Browser automation
- Desktop interaction
- Research and analysis
- Document and spreadsheet creation
- File management
- Personal workflows
- Connected applications
- Scheduling and notifications
- Multimedia processing

Each tool should have clear capability metadata, authorization requirements, timeout handling, errors, cancellation behavior, and test coverage.

Prefer reliable deterministic execution over having an LLM manually imitate an operation that a real tool can perform.

Do not build speculative integrations without a concrete use case.

---

# 13. PROTECT EXISTING DEVELOPMENT

This project already contains substantial implementation work.

Preserve:

- Current 3D dashboard.
- Avatar development.
- Floating assistant/orb experience.
- Existing chat behavior.
- Event streaming and reconnect logic.
- Model Hub.
- Voice system.
- Task cancellation.
- Security controls.
- Existing tests and documentation.

Do not overwrite concurrent avatar, dashboard, or audio changes.

Do not make broad refactors without measuring their necessity.

Do not silently commit, push, merge, or deploy.

Respect existing repository rules and feature flags.

Avoid new dependencies when existing libraries can satisfy the requirement.

Avoid creating parallel abstractions for capabilities that already exist.

---

# 14. IMPLEMENTATION PRIORITIES

Follow this order.

## M3 — Finish Current Integration

Complete native event-stream, notification, Model Hub, failure recovery, reconnect, cancellation, and cleanup acceptance.

Prove the outstanding idle-timeout case.

Do not proceed with major architecture additions until the checkpoint is correctly documented.

## M4 — Warm Hermes and Genuine Tools

Eliminate unnecessary cold starts.

Prove real model-to-tool execution through the broker.

Establish reliable end-to-end task completion.

This is the highest-value capability milestone.

## M5 — Persistent Context and Recovery

Make conversation and task context durable across model switching, process restarts, and interruptions.

Reuse existing infrastructure.

Keep retrieval lightweight.

## M6 — Efficient Multi-Provider Inference

Audit Hermes native model routing.

Integrate and benchmark Gemini, Groq, NVIDIA, OpenRouter, and local Qwen through approved endpoints.

Evaluate OmniRoute in isolation.

Adopt it only after passing performance, tool-compatibility, reliability, and zero-spend tests.

## M7 — Bounded Specialist Agents

Use Hermes native delegation.

Introduce specialist workflows only when they improve actual task completion.

Build the Bots UI without creating another orchestration framework.

## M8 — Full Conversational Experience

Integrate responsive speech recognition, streaming speech, interruption, avatar reactions, and task-status interaction.

Do not postpone all voice work if it can safely progress independently.

## M9 — Broad Capability and Optimization

Expand approved tool integrations.

Improve browser and coding workflows.

Profile real tasks, optimize latency and token usage, and eliminate unnecessary complexity.

These are dependency-ordered milestones, not instructions to rebuild completed work or abandon safe parallel development.

---

# 15. MANDATORY ACCEPTANCE SCENARIOS

The final architecture must eventually demonstrate:

**Scenario A — Fast Conversation**

User asks a simple question.

Hermes responds through one suitable model without spawning agents, performing unnecessary retrieval, or repeatedly starting processes.

**Scenario B — Genuine Tool Use**

User requests an authorized local action.

Hermes selects a real registered tool. The broker validates execution. The action completes and the assistant reports the observed result.

**Scenario C — Complex Coding**

User requests a feature change.

Hermes inspects the repository, develops a bounded plan, edits approved files, runs relevant tests, and reports actual results.

**Scenario D — Provider Failure**

A cloud endpoint reaches a simulated quota limit.

The application switches to a compatible, authorized alternative without losing durable task state, duplicating non-idempotent tool actions, or selecting paid inference.

**Scenario E — Restart Recovery**

A task is interrupted by an application restart.

Completed work and durable checkpoints are retained. The system reconciles execution state and safely resumes or requests appropriate action.

**Scenario F — Voice Interruption**

The user interrupts spoken output and gives another instruction.

Audio stops promptly, the new request is admitted correctly, and previous task state is handled according to cancellation and concurrency policy.

**Scenario G — UI Under Load**

The dashboard remains responsive while a permitted long-running task executes.

**Scenario H — Zero-Spend Exhaustion**

Every free cloud endpoint is unavailable.

The application avoids billable calls, tries an appropriate local capability if available, and otherwise clearly reports that the requested operation cannot continue.

Do not claim these scenarios pass until they have actually been tested.

---

# 16. ENGINEERING DELIVERABLES

For each milestone:

1. Audit existing implementation.
2. Identify reusable native capabilities.
3. State the smallest justified architecture change.
4. Implement behind feature flags where appropriate.
5. Add or update focused tests.
6. Perform real integration checks.
7. Measure latency and resource impact.
8. Document failures and limitations honestly.
9. Update implementation status.
10. Identify the next highest-value step.

Maintain an architecture decision record specifying:

- Capability owner
- Runtime components
- Memory ownership
- Model routing ownership
- Agent orchestration ownership
- Scheduler ownership
- Security boundaries
- Performance benchmarks
- Deferred components

Do not add a component without explaining what existing component cannot reasonably handle its responsibility.

## Required reporting format

At the end of each completed engineering slice, report:

- What was implemented.
- What was reused rather than rebuilt.
- What was tested.
- What actually passed or failed.
- Performance measurements, if collected.
- Any security or compatibility concerns.
- Remaining blockers.
- The next implementation step.

Keep the report concise and evidence-based.

Do not confuse edited files with working functionality.

---

# 17. FINAL NON-NEGOTIABLE DIRECTIVE

We are not developing a showcase of GitHub repositories.

We are developing **IMMORTILITY**, a highly capable personal AI assistant with the conversational experience of JARVIS and the technical capabilities of a reliable agentic system.

The user should be able to speak naturally, receive an immediate acknowledgement, and have the system perform real authorized work using whichever tools, models, and specialists are necessary.

But an assistant that uses five agents to accomplish what one Hermes instance could do is poorly engineered.

An assistant that starts five services before answering a simple question is poorly engineered.

An assistant that burns free API requests unnecessarily is poorly engineered.

An assistant that claims it completed actions without executing them is fundamentally broken.

**Intelligence should be powerful. Orchestration should be minimal. Execution should be real. Memory should be durable. Interaction should feel immediate.**

Do not sacrifice capability to save a few milliseconds, and do not sacrifice responsiveness by adding unnecessary architecture.

Optimize for the user's experience and verified outcomes.

## YOUR IMMEDIATE NEXT ACTION

Return to the current M3 working tree.

Inspect the latest uncommitted changes.

Finish the interrupted native Model Hub and runtime-notification acceptance, including the previously unverified idle-timeout test.

Then audit the installed Hermes runtime for warm execution and native tool-use capabilities.

Produce a brief implementation decision showing the smallest safe next step.

Proceed with the highest-priority eligible engineering slice, implement and test it, and preserve all existing functionality.

**Build the simplest system that delivers the most capable assistant.**
