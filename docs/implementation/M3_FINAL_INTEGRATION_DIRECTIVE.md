# IMMORTILITY — M3 FINAL INTEGRATION, REAL-MODEL READINESS & PERFORMANCE OPTIMIZATION

## CONTINUE THE EXISTING IMPLEMENTATION — DO NOT START OVER

You are continuing the Immortility project as its sole implementation agent.

The previous engineering session successfully implemented substantial M3 repairs and completed the full offline regression.

**Your next objective is to finish the remaining native integration and model-qualification gates, make the system significantly more responsive, and prepare its first genuinely successful real-model-to-tool-to-artifact workflow.**

Continue developing useful capabilities when their prerequisites pass.

Do not stop after producing another architecture review or planning document.

---

## 1. RECOVER THE VERIFIED CHECKPOINT

Before coding, read:

- `AGENTS.md`
- `README.md`
- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/M3_CLOUD_ROUTING_CHECKPOINT.md`
- `docs/implementation/M3_VERIFICATION.json`
- `docs/implementation/M3_GROKBOT_RECONCILIATION_2026-11-15.md`
- `docs/implementation/M3_PROVIDER_READINESS_2026-11-15.md`
- The latest relevant native and stream-repair verification evidence.

Examine the current Git working tree.

Preserve all previous changes, including uncommitted work.

Do not reset, clean, checkout, commit or push.

### Last verified state

- 393 Python tests passed.
- 63 frontend tests passed.
- 11 Rust tests passed.
- Full Python/TypeScript linting and formatting passed.
- Frontend and offline native builds passed.
- Configured-key isolation passed.
- K-32 semantic stream-buffer repair implemented.
- K-24 diagnostics and evidence provenance implemented.
- K-13 Hermes readiness ordering repaired.
- K-12 desktop HTTP event-lifetime issue repaired.
- Stream timeout scopes repaired.
- Report feasibility admission implemented.
- Native Model Hub partially accepted.
- Real Hermes → MCP → broker executed two tool operations and generated verified Markdown/PDF artifacts in 14.394 seconds using synthetic drafting.
- Zero cloud calls.
- SQLite v4 retained.
- No new dependencies or models installed.

**Do not repeat these repairs unless the current source or tests show an actual regression.**

The historical failed cloud report remains unresolved as a live acceptance result, even though the tool-buffer overflow mechanism was reproduced and repaired offline.

The M3 release gate is still blocked.

---

# STAGE A — COMPLETE NATIVE WINDOWS ACCEPTANCE

This is the first implementation priority.

The existing Model Hub has passed partial native acceptance against an isolated keyless fixture.

Finish the missing cases.

## A1. Long-running native event streams

The old Tauri client imposed a 100-second total HTTP timeout.

The repaired implementation uses:

- Five-second connection timeout.
- Ninety-second read-idle timeout.
- Broker-owned overall task deadline.

Verify the actual native application with controlled local streams lasting beyond 100 seconds, including a 150–180-second case and, where practical, a case approaching 300 seconds.

Use synthetic local event sources.

No cloud inference.

Test:

- Continuous event delivery.
- Heartbeats.
- Temporary network interruptions.
- Broker reconnect.
- Event replay after reconnect.
- No duplicate results.
- Cancellation during streaming.
- Stalled-peer timeout.
- Correct completion state.
- Child-process cleanup.

Do not run several expensive long-duration tests unnecessarily.

A few carefully designed representative cases with deterministic fixtures are preferable to repeated uninformative waiting.

## A2. Model Hub race conditions

Verify:

- Rapid overlapping distinct model selections.
- Duplicate requests.
- Restart persistence.
- Cloud/tool/artifact consent clearing.
- Busy-task restrictions.
- Busy-voice restrictions.
- Broker-disconnected state.
- Hermes-runtime-unavailable state.
- Accurate eligibility messages.
- Recovery after failures.

The existing 15-second frontend health polling may delay visible busy-state changes.

Investigate whether task/voice state notifications can update the interface immediately without excessive polling.

Preserve broker-side guards.

The dashboard must not show incorrect active-state information while the broker already knows a task is running.

## A3. Native resource assessment

Measure:

- Idle CPU.
- Idle RAM.
- GPU/VRAM where supported.
- Rendering responsiveness.
- Application startup.
- UI interaction latency.
- Process cleanup.

Do not alter the visual design or avatar assets.

Produce an updated native acceptance record distinguishing observed, simulated and still-unverified behavior.

---

# STAGE B — REAL MODEL TOOL-CALLING QUALITY

The next major obstacle is making a genuinely intelligent model reliably call real tools.

## B1. Typed capability schemas

Investigate the GrokBot K-07 finding.

The provider-visible interface currently uses one generic `execute` tool with capability arguments.

Determine whether exact provider-facing JSON schemas can improve reliable tool selection and argument construction.

Implement the smallest compatible improvement.

Requirements:

- Only approved capabilities appear.
- Each capability has the correct typed argument schema.
- Hermes continues to recognize its registered MCP tool.
- Broker capability identities remain exact.
- Provider-facing names translate safely to the registered Hermes interface, where required.
- No unauthorized tool is exposed.
- Invalid arguments fail closed.
- Tool call IDs remain stable.
- No arbitrary JSON repair.
- No duplicate tool descriptions unnecessarily inflate prompts.

Use deterministic offline tool-call fixtures.

Test single tools, multiple proposals, fragmented calls, malicious tool names, malformed arguments and cancellation.

Do not assume the proposed translation is compatible until verified against pinned Hermes.

## B2. Prompt and context efficiency

Instrument actual prompt construction.

Measure token and byte contributions from:

- System instructions.
- Hermes instructions.
- Tool definitions.
- Tool schemas.
- Project context.
- Conversation history.
- Retrieved sources.
- Memory.
- Output reservations.

Identify redundant content.

Minimize unnecessary prompt overhead without removing safety instructions or required tool contracts.

Do not rely only on raw UTF-8 byte counts as real provider token usage.

## B3. Report feasibility

The current report admission floor is 826 conservative output reservation units.

This proves only minimal schema feasibility, not the ability to produce a useful report.

Evaluate realistic short-report drafting requirements.

Ensure the system can accommodate:

- A genuine explanatory report.
- Citations.
- Required report structure.
- Tool proposal syntax.
- Final completion.
- Reasonable output headroom.

Preserve the existing two-call/8,000-token report policy unless a separate product decision changes it.

If a task is infeasible under the limit, reject it clearly before spending a model call.

Do not silently compress every report into an unusably short artifact merely to satisfy the ledger.

---

# STAGE C — QUALIFY A GENUINELY USABLE CLOUD MODEL

The current production path still has only the existing gated OpenRouter free alias.

Groq, Gemini and NVIDIA have offline transport foundations but are not yet production-admitted.

Do not rewrite those integrations.

## C1. Verify concrete model eligibility

Research current official provider documentation where network research is allowed.

Determine for each candidate:

- Exact model identifier.
- Tool-calling support.
- Context window.
- Structured output support.
- Streaming compatibility.
- Model availability.
- Actual price rules.
- Account/project entitlement evidence.
- Rate limits.
- Token limits.
- Whether zero-cost usage can be established.
- Whether the model is compatible with pinned Hermes.

Do not assume an API key means free inference.

Do not treat promotional credits as unconditional zero-cost eligibility.

Do not treat application-local budgets as actual provider quotas.

## C2. Context and tokenizer qualification

The independent audit identified a possible mismatch between Hermes' documented context needs and the existing free alias's configured 16K ceiling.

Inspect the exact pinned Hermes implementation and documentation.

Determine the actual operating requirements for:

- Plain chat.
- Tool-enabled tasks.
- Research/report workflows.
- Multi-turn agent execution.

Distinguish minimum supported context from recommended context.

Implement truthful context admission and output-headroom validation.

Use model-specific tokenizers where practical and verified.

When exact tokenization is unavailable, use a defensible conservative estimator and clearly classify the uncertainty.

Do not invent model context capacities.

## C3. Provider compatibility

Create distinct provider-specific streaming fixtures for:

- OpenRouter.
- Groq.
- Gemini.
- NVIDIA NIM.

Verify documented tool-call differences, including possible missing call-index metadata.

Reject ambiguous streams.

Test malformed events, premature finalization, provider interruptions, quota errors and unknown usage.

Record compatibility results as OFFLINE VERIFIED only.

## C4. Production route readiness

Register genuinely qualified routes only after eligibility evidence exists.

Until then, leave them non-dispatchable.

Provide actionable Model Hub explanations for every blocked model.

Do not quietly fall back to paid routes.

If the free-only policy cannot be satisfied with the available official account evidence, document the exact product decision that needs approval.

Do not implement a verifier that requires evidence the provider cannot supply.

---

# STAGE D — LOW-LATENCY HERMES AND MCP OPTIMIZATION

Immortility should feel responsive and natural, not spend most of every request starting processes.

Previous measurements indicated:

- Hermes/MCP readiness consumed approximately 61–67% of synthetic report execution.
- SDK cold start varied substantially between environments.
- Warm MCP calls were approximately 1 ms.
- Router-selection overhead was already below 0.1 ms p95 in synthetic benchmarks.

**Prioritize meaningful end-to-end latency improvements.**

## D1. Hermes runtime reuse

Investigate whether Hermes 0.21.1 safely supports multiple sequential sessions within a reusable process.

Develop a feature-flagged experimental implementation if supported.

Requirements:

- One authoritative broker.
- Per-task credential isolation.
- No cross-task session leakage.
- Correct model selection.
- Valid grants and expiry.
- Cancellation propagation.
- Crash recovery.
- Predictable process ownership.
- Proper shutdown.
- No unnecessary idle GPU consumption.

Benchmark both cold and reused sessions.

Do not activate persistent Hermes as the default without successful isolation and stability tests.

## D2. MCP SDK startup

Investigate:

- Repeated client/server interpreter launches.
- The measured approximately 977 ms handshake phase.
- Expensive imports.
- Manifest hashing.
- Duplicate initialization.
- Safe SDK-session reuse.
- Possible environment-dependent filesystem overhead.

Compare controlled runs in the project directory and a temporary local copy.

Do not assume OneDrive is the cause until measured.

Do not raise the original task/grant deadlines simply to make tests pass.

## D3. User-perceived latency

Measure:

- Time to first visible response.
- Time to first real model call where available.
- Time to first tool result.
- End-to-end workflow duration.
- Per-task process count.
- Peak RAM.
- CPU.
- Idle resource overhead.
- Cancellation time.

Benchmark real startup paths rather than repeatedly optimizing the already fast router microbenchmark.

The goal is a fast, secure core that eventually supports a natural voice interface.

---

# STAGE E — COMPLETE M3 ACCEPTANCE PREPARATION

After the relevant offline and native gates pass, prepare a genuine model-to-tool-to-report acceptance.

Target workflow:

1. User submits a bounded public research task.
2. Hermes plans.
3. A qualified cloud model constructs valid tool proposals.
4. Broker independently validates capability grants.
5. Actual research tools execute.
6. Verified public source evidence is returned.
7. A real model drafts a report.
8. Report worker creates Markdown/PDF artifacts.
9. Generated files are reopened and validated.
10. A durable completion receipt reaches the native UI.

No synthetic drafting for the final live acceptance.

However, **do not execute any new cloud inference without fresh explicit authorization.**

The previous live authorization is consumed.

Prepare an authorization request detailing:

- Provider/model.
- Exact public task.
- Maximum model calls.
- Maximum reserved tokens.
- Source scope.
- File destinations.
- Data sent externally.
- Zero-cost eligibility.
- No automatic retries or paid fallback.

If permission is unavailable, mark LIVE ACCEPTANCE BLOCKED and continue independent offline work.

Do not claim M3 is fully released without genuinely satisfying the relevant gate.

---

# STAGE F — CONTINUE PRODUCT DEVELOPMENT

Once the current critical correctness gates are stable, continue useful engineering.

Do not spend the entire session producing plans.

Prioritize one small, independently verifiable follow-on feature at a time.

Preferred next track:

**Memory provenance and context efficiency.**

The audit identified the risk of model-generated answers being stored and recalled as facts.

Implement a safe foundation using the existing Engine/Store:

- User-supplied facts distinguished from model responses.
- Tool evidence distinguished from guesses.
- Source provenance.
- Corrections and supersession.
- Relevant retrieval.
- Duplicate-context reduction.
- Trust boundaries.
- Privacy-scoped recall.
- Prompt-injection resistance.

Use the existing SQLite storage where practical.

Do not add a vector database or competing memory owner without demonstrated need.

Once this foundation is verified, prepare the next appropriate slices for:

- Hermes-native tool-using delegation.
- General web research.
- Expanded coding tools.
- Authorized browser/computer interaction.
- Document formats.
- Voice responsiveness.
- Local inference.

Do not install frameworks, enable broad computer control or download Qwen/Heretic model weights automatically.

Later milestones must remain feature-gated until their own security, performance and permission requirements pass.

---

# STAGE G — VALIDATION

Run focused tests after each repair.

Run the complete regression before closing the milestone.

Validate:

- Python tests.
- Frontend tests.
- Rust tests.
- Contracts.
- Type checking.
- Formatting and linting.
- Native application build.
- Credential isolation.
- Tool permissions.
- Provider-stream correctness.
- Cancellation.
- Workflow recovery.
- Native Model Hub behavior.
- Real local Hermes/MCP execution.

Preserve historical evidence.

Write new benchmark output to unique, untracked scratch paths.

Do not overwrite old failure logs.

Do not declare success solely because synthetic tests pass.

## Security and implementation boundaries

Preserve:

- Hermes as primary agent harness.
- Immortility Broker as sole credentials/permissions/provider boundary.
- Engine/Store as authoritative workflow owner.
- Existing Tauri/React/Three.js dashboard.
- Existing avatar and voice assets.
- Strict cloud-free eligibility.
- Cancellation and task expiry.
- No unauthorized system actions.

Do not:

- Reset or clean Git.
- Commit or push without approval.
- Modify unrelated personal files.
- Install new dependencies/models without permission.
- Change Windows security or system settings.
- Migrate live user databases without authorization.
- Execute authenticated cloud inference without approval.
- Automatically activate unverified providers.
- Replace working architecture with new frameworks.

Make routine authorized code changes autonomously.

---

# FINAL ENGINEERING DELIVERABLE

Update:

- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/M3_CLOUD_ROUTING_CHECKPOINT.md`
- `docs/implementation/M3_VERIFICATION.json`

Add fresh evidence where appropriate.

Report:

1. Actual native acceptance completed.
2. Typed tool-schema compatibility and measured prompt overhead.
3. Concrete provider/model qualification.
4. Tokenizer and output-headroom findings.
5. Hermes/MCP performance before and after.
6. Complete regression results.
7. Security and process-isolation acceptance.
8. Features newly implemented.
9. Remaining blocked external approvals.
10. Whether M3 has passed its release gate.
11. The next approved engineering milestone.

**Continue coding and verifying until the authorized work is complete or a genuine blocker prevents further progress.**

Do not stop after another plan.

Do not claim that synthetic model drafting is real cloud task completion.

Do not repeat already completed K-32, K-24, K-12 or K-13 repairs unless current evidence demonstrates a regression.

**FINAL GOAL: Transform Immortility into an exceptionally responsive, intelligent, reliable, secure and naturally interactive JARVIS-inspired personal AI assistant.**

Start with the current verified checkpoint. Implement the remaining native and model-readiness work, optimize the Hermes runtime, and continue advancing the system through verified incremental features.