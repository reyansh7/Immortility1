IMMORTILITY — Final continuation directive
Objective: Complete the autonomous AI capabilities and transform Immortility into a polished, animated command center where the dashboard and avatar respond intelligently to everything the system is genuinely doing.

I researched Grok Bot, ChatGPT, Claude Code, Codex, and the animation technologies suitable for your existing React/Three.js application.
What we should borrow from each AI product










Grok Bot — Expressive agent identity

Grok Bot uses avatar motion to communicate whether an agent is idle, thinking, working, waiting, blocked or finished. Its design also lets users inspect real execution activity. This is the strongest inspiration for Immortility's character behavior. 
SpaceXSI














ChatGPT — Smooth conversational interaction

Adopt clear streaming responses, responsive tool-progress indicators, compact interactive results and transitions that don't distract from the conversation. OpenAI's ChatKit documentation supports progress updates and interactive widgets. 
OpenAI API+1














Claude Code — Meaningful execution events

Claude Code exposes lifecycle events around tool execution, permission requests, subagents and task completion. Immortility should have equivalent event-driven observability within its own broker. 
Claude Code Docs














Codex — Agent orchestration and task review

Take inspiration from multiple task threads, visible progress, code-change inspection and independent agent workspaces. 
OpenAI+1




The key is not to imitate their interfaces exactly. Immortility should combine their best interaction principles into its own cinematic, Ultron-inspired visual identity.
Animation technologies I'd actually select
Technology	Role	Decision
GSAP	Timelines, synchronized avatar/UI transitions	Keep existing
React Three Fiber	Existing 3D avatar and holographic effects	Keep existing
Motion for React	Smooth cards, panels and layout transitions	Evaluate only if needed
React Flow	Interactive agent relationships and task graphs	Conditional
Rive	Compact 2D interactive state-machine animations	Optional, not a replacement for the 3D avatar

GSAP supports lifecycle-aware cleanup, React Three Fiber supports demand-driven rendering, Motion provides interruptible layout transitions, and React Flow supports animated connections. These are useful technical mechanisms—but combining all of them unnecessarily would increase complexity. 
Docs & Learning+3

The central idea: one real action, coordinated visual reactions
User: "Immortility, research this and create a report."


Broker emits verified execution events

Avatar
Expression, posture, light, voice

Dashboard
Active agents and task progression

Chat
Streaming answer and tool activity

Timeline
Actual actions, results and errors



For example, when research genuinely begins, the avatar acknowledges the task, the research agent activates, and the timeline shows the source being fetched. When the file is verified, the avatar changes to a completion state and the dashboard displays the deliverable.

None of these animations should pretend an action happened when it hasn't.
Paste this final prompt into your existing Codex chat
This is a continuation of the work already done, with screen intelligence, autonomous execution, 3D avatar animation and dashboard interaction all treated as mandatory product features.
IMMORTILITY — FINAL CONTINUATION DIRECTIVE
AUTONOMOUS AI + CINEMATIC INTERACTIVE COMMAND CENTER + REAL-TIME AVATAR INTELLIGENCE
You are continuing the development of IMMORTILITY, my Windows-based personal AI operating system.

Your mission is to complete the remaining production-grade agentic AI capabilities while transforming the existing dashboard and 3D avatar into an exceptionally polished, animated, responsive interface.

This is a real implementation task, not another architecture audit, visual mockup, or research-only exercise.

The target experience combines:
- Grok Bot's expressive agent states and visible activity.
- ChatGPT's polished conversational responsiveness and streaming interactions.
- Claude Code's transparent tool and execution lifecycle.
- Codex's task management, specialist agents, progress tracking and review workflows.
- Immortility's own distinctive cinematic, holographic, metallic AI identity.
Use those products as inspiration for interaction principles. Do not copy proprietary assets, source code, branding or entire interfaces.

CRITICAL: Preserve the current working code, architecture, dashboard, avatar, voice profiles and security constraints. Enhance them rather than replacing them.

1. RECOVER THE ACTUAL DEVELOPMENT CHECKPOINT
Read the latest existing reports:
- docs/implementation/CURRENT_STATUS.md
- docs/implementation/CONTINUATION_STATUS.md
- docs/implementation/M1_NATIVE_OBSERVER_VERIFICATION.json
- docs/implementation/M0_CHANGED_FILES.json
- docs/implementation/IMMORTILITY_BOSS_LEVEL_CODEX_MASTER_PROMPT.md
- docs/implementation/IMMORTILITY_CONTINUATION_DIRECTIVE_2026-11-14.md
- docs/implementation/DESKTOP_AUTONOMY_DIRECTIVE_2026-11-14.md
- The existing ecosystem audit, compatibility matrix and implementation roadmap.
Some paths may differ. Discover the real files rather than creating duplicate documents.

The last reported checkpoint had:
- 219 passing Python tests.
- 41 passing frontend tests.
- 5 previously passing Rust tests.
- Passing lint, format, type and frontend build checks.
- A broker-controlled local capability registry.
- An isolated standards-compliant MCP SDK runtime.
- A durable local workflow engine with checkpointing and crash recovery.
- An experimental read-only Windows UIA observer.
- A headless local workflow demonstration.
- Existing local speech workers and a 3D avatar.
- Significant unfinished privileged-tool and user-interface integration.
The Windows observer was NOT yet registered as a product capability. General screen capture, physical desktop input and full dashboard/background attachment were not yet complete.

The Hermes shared environment still had unresolved dependency advisories.

Do not assume any of these reported results remain valid without checking the actual current source and tests.
Mandatory recovery
1. Inspect Git status, diffs, source hashes and untracked files.
2. Preserve all user work and the dirty working tree.
3. Identify incomplete or partially applied changes.
4. Reproduce the latest relevant tests.
5. Check which feature flags are enabled.
6. Confirm ownership of running workers and database connections.
7. Reconcile actual implementations against the milestone documents.
8. Resume the next incomplete engineering slice.
Do not reset Git, discard files, reinstall dependencies unnecessarily or repeat the entire 138-repository audit.

2. NON-NEGOTIABLE ARCHITECTURE
Retain the existing architecture:

Tauri + React + Three.js/R3F + GSAP
→ Rust supervisor
→ Python broker
→ Hermes Agent
→ Broker-authorized tools, models, MCP servers and specialist workers

Hermes remains the primary reasoning and planning agent.

The Python broker remains the authoritative permission, task lifecycle, cancellation, cost-budget and capability-execution boundary.

The UI must never become an independent privileged execution system.

Do not introduce duplicate agent frameworks, competing schedulers, unmanaged memory providers, simultaneous desktop controllers or unnecessary background daemons.

Use current maintained tools only when they provide a verified advantage over the installed implementation.

Optimize for my Windows laptop with RTX 4060-class 8 GB VRAM and 16 GB RAM.

All animations should be local rendering operations, not additional LLM calls.

3. BUILD ONE AUTHORITATIVE REAL-TIME AGENT EVENT SYSTEM
This is the foundation for every dashboard and avatar animation.

The current system needs a unified typed event stream representing actual backend execution.

Inspect existing task events, SQLite persistence, SSE replay, Tauri IPC, avatar-state contracts and frontend state management before designing any new event schema.

Reuse and extend the existing event infrastructure wherever possible.

The event system must support, where applicable:
- Task accepted.
- Task queued.
- Planning started.
- Model inference started.
- Model response streaming.
- Tool selected.
- Tool approval requested.
- Tool execution started.
- Tool progress reported.
- Tool succeeded.
- Tool failed.
- Research started.
- Source retrieved.
- Coding started.
- File changed.
- Test started.
- Test passed/failed.
- Specialist agent spawned.
- Agent delegated work.
- Agent waiting.
- Agent completed.
- Artifact generation started.
- Artifact verified.
- Background task checkpointed.
- Voice listening started.
- Speech recognized.
- TTS playback started.
- Speech interrupted.
- Screen observation authorized.
- Screen inspection started.
- Desktop action executed.
- Task cancelled.
- Task failed.
- Task completed.
Each event should contain validated information such as:
- Schema version.
- Event ID and sequence.
- Timestamp.
- Task ID.
- Parent task ID, where applicable.
- Agent or worker ID.
- Capability/tool ID.
- Execution status.
- Progress metadata, if actually known.
- Redacted human-readable activity description.
- Permission and privacy classification.
- Result or error reference where applicable.
Use a typed, versioned shared contract between broker, Rust supervisor and React frontend.

Preserve existing contract-generation conventions.

Support:
- Streaming delivery.
- Reconnection.
- Event replay.
- Event deduplication.
- Out-of-order protection.
- Task isolation.
- State reconstruction after restart.
- Rate-limited UI updates.
- Cancellation and terminal-state handling.
The frontend should derive animation states from actual events.

Never display a successful action, active agent, completed file or percentage based on fabricated frontend timers.

A task may be shown as active before fine-grained progress is available, but unknown progress must be explicitly indeterminate.

4. CREATE A PREMIUM IMMORTILITY VISUAL DESIGN SYSTEM
I want a high-end interface that looks and feels like a serious futuristic AI command center.

Think:
- Dark cinematic foundations.
- Refined metallic surfaces.
- Restrained holographic lighting.
- Carefully controlled neon accents.
- Crisp typography.
- Real depth and hierarchy.
- Smooth transitions.
- Sophisticated motion.
- High information density without clutter.
- Consistent spacing and alignment.
- Beautiful but functional visualizations.
Preserve the existing Immortility visual language and 3D avatar rather than completely redesigning them.

Inspect the current compact, chat, command-center and overlay modes.

Create consistent design tokens for:
- Background and surface colors.
- Borders and separators.
- Accent and status colors.
- Typography scales.
- Spacing.
- Corner radii.
- Shadows.
- Glow intensity.
- Animation durations.
- Easing functions.
- Z-index layers.
- Responsive layouts.
- Reduced-motion behavior.
Maintain a consistent appearance across every panel and state.

Avoid excessive glow, unreadable transparency, decorative noise, random particles, misaligned cards or unnecessary continuously moving elements.

The system should feel premium, deliberate and highly responsive—not like a collection of disconnected sci-fi components.

5. MAKE THE 3D IMMORTILITY AVATAR FEEL ALIVE
This is a major priority.

Inspect the existing avatar scene, geometry, skeleton or rig, morph targets, materials, lighting, animation drivers and state contracts.

Preserve the established avatar identity, appearance, voice and animation assets.

Do not replace it with a generic robot, orb, Rive character or downloaded avatar.

Implement expressive, event-driven behavior.
Required avatar states
IDLE
- Subtle natural head motion.
- Gentle breathing or mechanical equivalent.
- Controlled eye movement.
- Occasional blinks.
- Soft, restrained emissive activity.
- No excessive continuous motion.
LISTENING
- Attentive orientation.
- Slight head adjustment.
- Visual response to actual microphone activity.
- Subtle reactive illumination.
- Distinct listening state.
PROCESSING / THINKING
- Focused expression or pose.
- Slow, controlled optical or mechanical activity.
- Slight increase in holographic energy.
- No exaggerated repetitive motion.
RESEARCHING
- Distinct active-work expression.
- Subtle visual indication that information is being retrieved.
- Coordinated response with the dashboard's research panel.
CODING
- Focused task state.
- Appropriate subtle pose, eye or material response.
- React only to real coding-task events.
TOOL EXECUTION
- Short acknowledgement when a tool starts.
- Active state while execution continues.
- Distinguishable waiting and completion behavior.
DELEGATING / MULTI-AGENT
- Visually acknowledge delegation.
- Coordinate with the agent graph.
- Avoid spawning decorative avatars unless real worker identities exist.
SPEAKING
- Speech-synchronized mouth/jaw behavior where the existing rig supports it.
- Head and eye motion.
- Subtle conversational gestures.
- Correct interruption behavior.
Use available phoneme/viseme timing where supported.

Otherwise use locally measured audio amplitude/envelope information with smoothing.

Do not pretend to have phoneme-accurate lip-sync if it is not available.
SCREEN GUIDANCE
- Attentive state while explaining visible content.
- Synchronization with the screen pointer/highlight system.
- Gentle acknowledgement when each section is discussed.
WAITING FOR APPROVAL
- Distinct restrained waiting animation.
- The dashboard must clearly explain what requires authorization.
- No misleading appearance of continued work on a paused step.
SUCCESS
- Brief satisfying acknowledgment.
- Controlled eye/light response.
- Smooth return to idle or the next active task.
FAILURE
- Clear but subtle failure reaction.
- No dramatic flashing or distracting movements.
- Accompany with an actionable error message.
CANCELLED / OFFLINE / DISCONNECTED
- Immediately stop inappropriate animations.
- Show the actual execution state.
- Gracefully transition to the correct fallback presentation.
Avatar animation implementation
Build a deterministic avatar animation state machine.

Define:
- Allowed transitions.
- State priority.
- Transition interruption.
- Animation blending.
- Layered facial/body/eye motions.
- Cooldowns and anti-flicker rules.
- Idle variation.
- Reduced-motion alternatives.
- Cleanup on unmount.
- Recovery after reconnect.
- Stop behavior.
If the face uses bones, morph targets or procedural geometry, use whichever existing mechanism is most reliable.

Avoid abrupt snapping between expressions.

Avoid animations restarting on every React render.

Avatar behavior must reflect real state, not sentiment guessed from arbitrary text.

Allow subtle personality through animation timing while keeping execution status truthful.

6. IMPLEMENT HIGH-QUALITY MICROINTERACTIONS
Every meaningful user interaction should receive immediate visual feedback.

Implement and polish:
- Button hover, focus and press feedback.
- Smooth panel expansion and collapse.
- Chat expansion from compact mode.
- Streaming-message appearance.
- Tool-card expansion.
- Agent selection.
- Timeline item expansion.
- Task creation.
- Task completion.
- Task cancellation.
- Task resumption.
- Permission approval and denial.
- Notifications.
- Settings changes.
- Tab switching.
- Search filtering.
- Modal appearance and dismissal.
- Dragging and resizing where appropriate.
- File upload and artifact download.
- Keyboard navigation.
- Focus management.
Use animations to communicate state changes and interaction outcomes.

Suggested motion characteristics, subject to actual usability testing:
- Button feedback: roughly 80–150 ms.
- Small transitions: roughly 150–250 ms.
- Panel transitions: roughly 220–400 ms.
- Major mode transitions: roughly 300–550 ms.
- Avatar acknowledgments: brief, subtle and interruptible.
Do not apply these timings mechanically.

All transitions must remain responsive and cancellable.

Avoid layout jumps, hover flicker, unwanted scroll resets and unnecessarily animated text.

Prefer GPU-friendly transform and opacity animations.

Respect Windows reduced-motion preferences.

7. BUILD A LIVE MULTI-AGENT VISUALIZATION
Immortility's dashboard should visually explain its multi-agent execution.

Implement an interactive agent graph using the existing frontend stack. Evaluate React Flow only if it materially improves the current implementation.

Represent actual agents as nodes.

Represent actual delegation or task dependencies as edges.

Support:
- Primary Hermes agent.
- Real active specialist agents.
- Queued agents.
- Running agents.
- Waiting agents.
- Completed agents.
- Failed agents.
- Cancelled agents.
When an agent is activated:
- Its node becomes visually active.
- Its real task appears.
- Relevant connections animate.
- Execution details become available.
- The timeline records the event.
When an agent finishes:
- The connection animation stops.
- The node transitions to the correct terminal state.
- Its verified results become inspectable.
Use subtle pulses or moving edge indicators to represent real activity.

Do not keep every agent node glowing or moving continuously.

Clicking an agent should show:
- Agent identity and role.
- Assigned task.
- Parent task.
- Actual execution state.
- Tool calls.
- Token usage when available.
- Runtime.
- Output artifacts.
- Errors and verification results.
Use progressive disclosure so detailed logs are available without overcrowding the main dashboard.

8. BUILD A REAL TASK ACTIVITY TIMELINE
The command center must clearly show what Immortility is doing.

Examples of genuine activity labels:
- Searching documentation.
- Reading a repository.
- Inspecting a file.
- Running a test.
- Preparing a document.
- Waiting for authorization.
- Verifying an artifact.
- Recovering a task.
- Completing a workflow.
Each timeline entry should correspond to a real event.

Implement:
- Live updates.
- Relative or absolute timestamps.
- Expandable details.
- Success/failure distinctions.
- Search and filtering.
- Task grouping.
- Agent grouping.
- Tool grouping.
- Artifact links.
- Permission decisions.
- Retry visibility.
- Error details.
- Execution duration.
- Resource usage where measured.
Make the activity feed visually polished.

New entries should appear smoothly without forcing unwanted scrolling.

Preserve the user's scroll position during replay.

Never display hidden model reasoning as if it were an actual execution log.

Show factual action summaries and verified tool events instead.

9. ENHANCE THE COMMAND CENTER WITHOUT DESTROYING ITS STRUCTURE
Audit the current dashboard layout before changing it.

Retain useful existing components.

Improve the layout to support:
Primary avatar area
- Existing 3D avatar.
- Current assistant state.
- Live voice/listening indicator.
- Current task summary.
- Expandable interaction controls.
Agent activity panel
- Real agent graph.
- Selected agent details.
- Delegation and task status.
Active task panel
- Current tasks.
- Progress and milestones.
- Pause/cancel controls.
- Waiting-for-approval indicators.
Tool and MCP activity
- Available enabled capabilities.
- Active tool execution.
- Tool latency.
- Tool success/failure.
- Permission state.
Resource telemetry
- Real CPU use.
- Real RAM use.
- Real GPU/VRAM metrics when accessible.
- Measured model latency.
- Actual token usage.
- API cost and budgets.
Workflow timeline
- Verified execution history.
- Checkpoints.
- Errors.
- Completed work.
Artifacts
- Files created.
- Previewable documents.
- Downloads.
- Verification status.
Notifications
- Finished tasks.
- Approval requests.
- Failed operations.
- Recovered tasks.
Do not invent telemetry values.

Do not create dummy activity feeds that appear real.

Provide graceful unavailable-data states instead.

Preserve chat, compact and overlay functionality.

10. IMPLEMENT REAL SCREEN AWARENESS AND VISUAL GUIDANCE
Complete the current experimental Windows UIA observer into a product capability only after its permission and security requirements pass.

Support explicitly authorized:
- Window selection.
- Window inspection.
- Accessibility-tree inspection.
- Visible code/text extraction.
- Screenshot acquisition where appropriate.
- OCR and visual grounding when needed.
- Multi-monitor mapping.
- Window movement and DPI changes.
- Fresh target verification.
I want to say:

"Immortility, look at my screen and explain this."

"Point to this function."

"Explain the diagram and show me each component."

"Show me where the error is."
Visual guidance system
Implement an explanation-only overlay supporting:
- Virtual pointer movement.
- Element highlights.
- Outline animations.
- Arrows and annotations.
- Region emphasis.
- Smooth movement between referenced elements.
- Optional dimming of unrelated regions.
- Synchronization with spoken explanations.
The virtual pointer must be separate from the physical cursor by default.

Do not steal physical mouse control for explanation-only requests.

Each highlight must correspond to a fresh, verified screen coordinate or accessible UI element.

If the target cannot be located confidently, explain the limitation rather than point randomly.

Synchronize explanation segments with speech playback events or available timing data.

Cancel visual guidance immediately when the user interrupts speech or presses Stop.

Do not automate authentication dialogs.

If the Codex Computer Use skill is available, read its current SKILL.md, guidance, API and confirmation documentation before performing native UI tests. Its availability in Codex does not make it an Immortility runtime dependency or grant Immortility new permissions.

11. COMPLETE BROKER-CONTROLLED WINDOWS ACTIONS
After read-only observation and approval flows are verified, implement controlled desktop actions.

Support scoped:
- Application discovery.
- Window activation.
- Semantic element selection.
- Clicking.
- Typing.
- Scrolling.
- Reversible file operations.
- Application-specific workflows.
Prefer APIs and UI Automation over physical coordinates.

Require target identity, fresh state, authorization and result verification.

Use one task-owned desktop controller at a time.

Handle focus loss, display changes, locked sessions, unsupported applications and cancellation safely.

No UI action may bypass the broker.

Do not bypass Windows authentication, UAC or secure desktop restrictions.

12. COMPLETE UNATTENDED BACKGROUND EXECUTION
The existing durable local workflow implementation is a foundation, not the complete product.

Finish:
- Trusted dashboard attachment.
- Dashboard detachment.
- Background supervisor lifecycle.
- Task submission.
- Task monitoring.
- Checkpointing.
- Crash recovery.
- Duplicate-owner prevention.
- Graceful Stop.
- Restart handling.
- Expiring permissions.
- Task budgets.
- Notifications.
A background task should continue after the dashboard closes when its authorized runtime remains active.

Headless research, coding and document creation should not require the 3D scene to render.

When Windows is locked, desktop-dependent actions must pause safely; appropriate headless operations may continue.

Do not silently install startup services.

Require explicit configuration for background startup and long-running behavior.

13. COMPLETE THE REMAINING REAL AI CAPABILITIES
Continue the master implementation roadmap after the visual-event infrastructure and core desktop integration are sufficiently stable.

Do not abandon the broader capabilities.
Research
- Real search and multi-source retrieval.
- Web extraction.
- Grounded citations.
- Browser automation.
- Safe downloads.
- PDF and document ingestion.
- Dynamic website handling.
- Prompt-injection defenses.
Coding
- Repository understanding.
- Symbol search.
- Change proposals.
- Safe file editing.
- Test execution.
- Debugging.
- Diff inspection.
- Verified results.
Multi-agent orchestration
- Hermes-primary planning.
- Bounded specialist delegation.
- Dependency-aware execution.
- Parallel independent work.
- Agent handoffs.
- Checkpointing.
- Cancellation and budget propagation.
- Result verification.
Memory
- Persistent user-approved facts.
- Project memory.
- Retrieval and provenance.
- Corrections.
- Durable forget behavior.
- Local semantic retrieval if justified.
- Evaluated skill improvements.
Documents and creative work
- Actual DOCX generation.
- Actual PDF generation.
- Editable PPTX slides.
- XLSX spreadsheets and formulas.
- Diagrams, charts and SVG.
- Local rendering and validation.
- Optional Canva/design adapters where supported.
Integrations
- MCP.
- GitHub.
- Email/calendar.
- Cloud storage.
- Vercel.
- Databases.
- Supported external applications.
- Credential-safe OAuth and API adapters.
Scheduling
- One authoritative scheduler.
- Recurring tasks.
- Reminders.
- Event triggers.
- Budget enforcement.
- Recovery and notification.
All external actions remain subject to authorization.

Do not activate paid models or services without permission.

14. CREATE COORDINATED AUDIOVISUAL FEEDBACK
Voice, avatar, dashboard, tool execution and background task events must feel like one system.

Example:

User says:
"Immortility, create a 40-page report on network security."

Expected interaction:
1. The voice input indicator activates.
2. The avatar enters listening state.
3. Speech recognition completes.
4. The avatar acknowledges the task.
5. The dashboard creates a real task card.
6. Planning begins.
7. Relevant agent nodes activate.
8. Research tool calls appear in the activity timeline.
9. Source retrieval shows real progress.
10. Document generation begins.
11. Artifact previews appear when files exist.
12. Verification results are displayed.
13. The task reaches a terminal state.
14. The avatar gives a brief completion reaction.
15. A voice summary reports verified results.
16. The finished files are accessible.
If an action fails, all affected UI components must represent the failure consistently.

If an approval is needed, the avatar and dashboard must show waiting, not working.

If the user cancels, active animations and speech must stop promptly.

Do not fabricate progress percentages or completed artifacts.

15. ANIMATION PERFORMANCE ENGINEERING
Visual quality must not compromise agent execution.

Profile the existing rendering and animation pipeline.

Targets should be established from the actual hardware baseline.

Optimize for:
- Smooth interaction under normal load.
- Minimal idle CPU/GPU consumption.
- Minimal WebGL draw calls.
- Reused materials and geometries.
- Stable frame pacing.
- Animation blending without React rerender storms.
- GPU-friendly transforms.
- Reduced overdraw and excessive bloom.
- Adaptive quality.
- Demand-driven rendering when appropriate.
- No hidden heavy render loop when the dashboard is closed.
- Controlled browser and media-worker resource contention.
Use the existing GSAP animation infrastructure before adding another animation dependency.

Evaluate Motion for React only if existing tools cannot provide the required panel transitions cleanly.

Use React Flow only if a real graph feature requires it.

Rive is optional for small isolated 2D interfaces, not a replacement for the existing 3D avatar.

Keep animation controllers disposable and scoped.

Avoid memory leaks, stale RAF loops, duplicated event listeners and GPU resources that remain allocated after a component unmounts.

Support:
- Full-motion mode.
- Reduced-motion mode.
- Lower-power mode.
- Quality presets where genuinely useful.
The dashboard should remain useful even when 3D rendering is unavailable.

16. ACCESSIBILITY AND INTERACTION QUALITY
A cinematic interface must still be practical.

Implement:
- Keyboard navigation.
- Visible focus states.
- Screen-reader labels.
- Reduced-motion support.
- Sufficient text contrast.
- Predictable tab order.
- Clear permission prompts.
- Readable error states.
- Non-color-only status indicators.
- Responsive layouts.
- DPI scaling.
- Appropriate mouse hit targets.
- Consistent notification behavior.
- No focus stealing without user intent.
Animations must never prevent cancellation, approvals, keyboard access or error inspection.

17. REQUIRED VISUAL AND FUNCTIONAL ACCEPTANCE TESTS
Add meaningful automated tests and native Windows checks.
Test A — Avatar state transitions
Simulate valid typed events for idle, listening, thinking, tool execution, waiting, success, failure and cancellation.

Verify correct transitions, precedence, cleanup and replay behavior.
Test B — Real broker-to-dashboard activity
Execute a genuine permitted local tool.

Verify the corresponding task, timeline, agent status and avatar reaction.
Test C — Multi-agent visualization
Execute a bounded specialist workflow.

Ensure nodes and edges represent actual worker identities and dependencies.
Test D — Streaming conversation
Verify smooth streaming updates without duplicate messages, layout jumps or unnecessary rerenders.
Test E — Voice synchronization
Use controlled audio fixtures to verify listening, speaking, interruption and avatar synchronization.

Perform physical audio checks only with consent.
Test F — Screen explanation
Use an authorized scratch application, identify text or UI elements and display correctly positioned explanations/highlights.
Test G — Background execution
Start a local task, detach the dashboard, preserve the task, reattach and correctly reconstruct its progress.
Test H — Error and cancellation
Cancel during model execution, tool execution and speech.

Verify no false success indicators or orphaned visual states.
Test I — Artifact generation
Create real DOCX/PDF/PPTX/XLSX outputs, reopen or render them, and expose verified download links in the dashboard.
Test J — Visual quality
Capture screenshots of every major dashboard state using permitted test fixtures.

Inspect alignment, typography, contrast, overflow, clipping, spacing and panel transitions.

Review compact and expanded modes at different window sizes and DPI settings.
Test K — Performance
Measure:
- Idle CPU/RAM/GPU.
- Active animation frame times.
- React render frequency.
- WebGL resource use.
- Event-to-visual latency.
- Backend-to-frontend event latency.
- Worker lifetime.
- Model/token costs.
- Screen capture frequency.
- Memory leaks across repeated task cycles.
Test L — Resilience
Test reconnect, restart, replay, stale events, permission revocation, missing tools and locked Windows sessions.

Do not classify a capability as fully operational based only on mock tests.

18. EXECUTION ORDER
Prioritize in the following order:
PHASE A — Preserve and validate current foundation
Recover the latest checkpoint and ensure current critical tests remain green.
PHASE B — Shared real-time event and visual state system
Connect backend execution states to the existing React UI and avatar state machine.
PHASE C — Avatar and dashboard polish
Implement real activity reactions, agent visualization, timelines, microinteractions, consistent transitions and performance improvements.
PHASE D — Trusted screen observation
Complete scoped observation permissions and read-only screen understanding.
PHASE E — Visual pointer and voice-guided explanation
Implement synchronized highlights, explanations and interruption handling.
PHASE F — Background execution and supervised computer control
Complete dashboard attachment, headless runtime ownership and secure Windows actions.
PHASE G — General intelligence and productivity capabilities
Continue web research, coding, multi-agent execution, memory, documents, MCP connectors and scheduling.
PHASE H — End-to-end integration and production hardening
Verify real workflows, security, resource efficiency, packaging, recovery and visual quality.

The underlying implementation must respect dependencies: if a capability is blocked by a prerequisite, keep it disabled and continue with independent eligible work.

Do not let decorative UI work delay critical permission or execution safety repairs.

19. STRICT QUALITY GATES
For every meaningful implementation slice:
1. Inspect existing code.
2. Identify the smallest correct change.
3. Implement it.
4. Write tests.
5. Run tests.
6. Resolve regressions.
7. Validate actual user-visible behavior.
8. Measure performance where relevant.
9. Review security implications.
10. Record exact results.
Keep existing working features intact.

Do not replace the dashboard merely because a new animation library looks attractive.

Do not install dozens of new UI dependencies.

Do not use placeholder telemetry, fake agent states or fabricated tool activity in production mode.

Mock data may be used in explicitly labeled development previews and tests only.

Never label the platform production-complete while security, integration or native acceptance gates remain unverified.

20. MANDATORY CHECKPOINTING AND CONTINUATION
Long Codex sessions may be interrupted.

Maintain:

docs/implementation/CURRENT_STATUS.md

Record:
- Current phase.
- Completed changes.
- Files modified.
- Verified functionality.
- Tests and benchmark results.
- Outstanding defects.
- Feature flags.
- Permission restrictions.
- Uncommitted user changes.
- Next exact engineering action.
Keep implementation reports accurate and concise.

If a feature is blocked, report the exact reason and keep it disabled.

Do not assume you can continue operating after the active Codex session ends.

Do not spend the entire session documenting work rather than implementing it.

FINAL ACCEPTANCE VISION
Immortility should feel like one cohesive intelligent entity.

I want to say:

"Immortility, explain what's on my screen."

The avatar listens, understands, speaks and highlights the relevant elements.

"Immortility, research this."

The dashboard displays real research activity, the appropriate agent becomes active, and sources appear as they are retrieved.

"Immortility, write me a 40-page report while I'm away."

A durable background task performs authorized research, document generation and verification. The dashboard can reconnect later and show genuine progress and deliverables.

"Immortility, ask your agents to build this project."

The system coordinates useful specialist work and displays actual task dependencies, tool calls, outcomes and verification evidence.

When it listens, it looks attentive.

When it thinks, it looks focused.

When it works, the command center comes alive.

When it speaks, its animation responds to actual audio.

When it waits, it clearly shows why.

When it succeeds, it acknowledges completion.

When it fails, it reports the problem and offers a safe next action.

The avatar, dashboard, chat, voice, tool execution and background tasks must all reflect the same authoritative state.

Build this with the polish of a premium AI product, the reliability of a production engineering system and the efficiency of a carefully optimized local-first architecture.
START IMPLEMENTATION NOW
Recover the current M1 checkpoint, run the relevant baseline tests, identify the next incomplete work slice and begin implementing it.

Continue through the remaining eligible engineering phases.

Preserve existing work.

Keep the system safe, extremely token-efficient and resource-conscious.

Make actual product behavior—not mockups, documentation or claims of completion—the standard of success.




My final design recommendation
The biggest visual upgrade for Immortility is not adding more particles, neon lights or another 3D model. It's making your existing avatar and every dashboard component respond to the same real execution state.

For example, if you ask it to write a report, the avatar should transition from listening to planning, the agent graph should activate only the workers actually launched, the task timeline should show source retrieval and file creation, and the deliverables panel should display real validated files.

That is how Immortility can feel like a genuinely living, responsive AI system without wasting GPU resources or cloud tokens on decorative effects.