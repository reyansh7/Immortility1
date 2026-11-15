# IMMORTILITY — CRITICAL BUG FIXES, UI REFINEMENT & CONTINUED PRODUCTION IMPLEMENTATION

## MANDATORY CONTINUATION DIRECTIVE

Continue developing my existing Windows AI assistant, **IMMORTILITY**, from its latest engineering checkpoint.

This is NOT a new project, another GitHub audit, or a request to recreate the application.

**Your immediate priority is to fix actual problems I am experiencing in the running application, finish the interrupted background-attachment implementation, and then continue building the remaining agentic AI capabilities.**

I have attached three screenshots showing the current desktop dashboard, chat page and floating companion.

Treat those screenshots as concrete visual regression evidence.

Do not claim that functionality works merely because a unit test passes.

---

# 1. RECOVER THE ACTUAL CURRENT STATE

Read the existing project documentation, including:

- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/CONTINUATION_STATUS.md`
- `docs/implementation/M1_NATIVE_OBSERVER_VERIFICATION.json`
- `docs/implementation/M0_CHANGED_FILES.json`
- The original master engineering directive
- The desktop-autonomy directive
- The latest GPU/performance directive
- The latest relevant implementation, benchmark and verification reports

Discover actual paths rather than assuming all files have the same names.

The latest reported state includes:

- 233 passing Python tests.
- 45 passing frontend tests.
- Five passing Rust tests.
- An experimental Windows observation capability with a manually verified scratch-window consent flow.
- A broker-owned local workflow engine.
- A standards-compliant MCP integration.
- A partially implemented background-attachment mechanism.
- DPAPI-protected local background credentials.
- Process ownership and cleanup improvements.
- Ongoing unrelated avatar and GPU optimization work.

These are **previously reported results**, not proof that the current checkout still passes.

The previous Codex session stopped while working on:

- Background broker attachment.
- Reconnection behavior.
- Windows process-tree cleanup.
- An MCP deadline failure during concurrent build load.
- A background smoke test using `scripts/smoke-background-attachment.py`.
- Rust build verification.

It reported approximately 31 modified files during that increment.

## Important: concurrent editor protection

Another Codex chat was simultaneously modifying:

- `HeadScene.tsx`
- `rig.ts`
- `rig.test.ts`
- `gpu_budget.py`

And potentially additional avatar/GPU files.

Before editing:

1. Inspect Git status and recent file modification times.
2. Identify all currently running development processes.
3. Determine whether another editor or agent is still writing to the same checkout.
4. Preserve all modified and untracked files.
5. Do not reset, clean, overwrite or discard user changes.
6. Avoid modifying avatar/GPU source currently owned by another active session.
7. If parallel development is necessary, use separate worktrees/branches with explicit file ownership and integration review.
8. Never run two concurrent writers against the same SQLite database or shared source files.

If the other editor is still active, complete independent broker/chat/voice work first and defer conflicting changes until ownership is clear.

## Baseline

Reproduce the currently supported checks and record actual results.

Do not repeatedly run full builds during active concurrent modifications.

Create a concise current-state and ownership checkpoint before implementing new changes.

---

# 2. CRITICAL BUG: IMMORTILITY SOMETIMES RETURNS TO IDLE WITHOUT RESPONDING

This is a top-priority user-visible defect.

I asked Immortility a question, but it did not display an answer. The interface simply returned to **Idle**.

In other cases, a chat response is successfully generated.

Investigate the entire request lifecycle.

## Examine

- Chat input submission.
- Send button and Enter handling.
- Local/cloud consent state.
- Selected conversation/session.
- Task admission.
- Model-route selection.
- Hermes startup and session creation.
- Provider connectivity.
- OpenRouter free-model eligibility.
- Request timeouts.
- Model response streaming.
- Empty provider responses.
- Tool-call-only responses.
- Refused or malformed responses.
- SSE connection and event replay.
- Stream finalization.
- Message persistence.
- Frontend conversation state.
- UI rendering.
- Cancellation races.
- Retry and error handling.
- Task terminal-state transitions.

Inspect the actual logs and traces associated with failed requests.

Do not assume the problem is caused by the LLM, the network, consent or the frontend without evidence.

## Required behavior

Every submitted chat request must reach a clear visible terminal result:

- A genuine assistant response.
- A meaningful error.
- A visible permission requirement.
- A cancellation message.
- A timeout message.
- A provider-unavailable result.

**Never silently return to Idle after accepting a question without presenting the outcome.**

If a provider returns no usable output, distinguish that condition from success.

A task may not be marked successfully answered solely because the model request finished.

Ensure final response persistence and UI acknowledgment are handled correctly across stream disconnection or reconnection, without duplicating messages.

Use bounded, safe retry policies for genuinely retryable failures.

Do not automatically make repeated paid or unauthorized cloud requests.

## Debug and acceptance tests

Test:

1. "Hi."
2. "Who are you?"
3. "What can you actually do right now?"
4. "Explain Python decorators."
5. A multiline technical question.
6. Multiple consecutive questions.
7. Two quick submissions.
8. Provider timeout.
9. Empty provider output.
10. Provider rejection.
11. SSE interruption and reconnection.
12. Cancellation during streaming.
13. Closing and reopening the conversation.

Verify that the actual displayed response corresponds to the correct task and conversation.

Test both actual local broker operation and explicitly authorized live provider inference.

Use fake providers for deterministic regression testing, but do not claim the real cloud route works without a real authorized smoke test.

### Fix assistant identity and capability descriptions

One screenshot shows the assistant responding that it is "Particle-1, a language model created by Particle AI."

Immortility should consistently present itself as **Immortility, my personal Windows AI companion**.

Preserve truthful provider/model metadata separately.

Do not fabricate the underlying provider, model identity, model capabilities, or tool access.

When asked what it can do, the assistant should describe the capabilities genuinely enabled in the current application—not all planned future features.

Inspect the system instructions, provider-adapter configuration and capability metadata.

Do not solve this merely by hiding or hardcoding the generated answer.

---

# 3. CRITICAL BUG: MICROPHONE AND CUDA FAILURES

I am experiencing CUDA-related problems while using the microphone/voice functionality.

Investigate the complete local voice pipeline.

**Important: Microphone audio capture itself should not require CUDA.**

Determine whether the failure actually occurs during:

1. Windows microphone permission.
2. Device selection.
3. Audio stream initialization.
4. Audio recording.
5. Voice activity detection.
6. Speech-to-text model initialization.
7. Speech recognition inference.
8. GPU library initialization.
9. Text-to-speech synthesis.
10. Audio playback.
11. Worker cleanup.
12. Switching between voice models.

Do not diagnose a CUDA problem from the word "microphone" alone.

## Inspect actual environments

Audit the existing isolated environments for:

- faster-whisper
- CTranslate2
- Piper
- Kokoro
- Qwen TTS
- Reference TTS
- PyTorch
- ONNX Runtime
- CUDA runtime dependencies
- cuDNN dependencies
- NVIDIA driver compatibility
- Model precision and compute types

Inspect relevant package versions, device-detection results, worker stderr, exception chains and process exit codes.

Do not print or leak credentials.

Do not globally reinstall CUDA, change graphics drivers, modify PATH indiscriminately, or upgrade every speech environment in place.

Do not automatically enable the Qwen runtime while its security gate remains unresolved.

## Mandatory CPU fallback

Voice input must remain usable even when CUDA is unavailable.

Implement a predictable processing policy:

- Capture audio through the appropriate Windows device.
- Use local CPU VAD.
- Prefer the existing reliable local CPU STT backend as the baseline.
- Use GPU STT only when explicitly supported and demonstrated to be beneficial.
- On a recoverable GPU initialization failure, use an approved CPU fallback without requiring a complete app restart.
- Clearly display which speech backend is active.
- Do not repeatedly attempt a known-broken GPU path.
- Keep voice capture local unless cloud consent is explicitly granted.

Evaluate whether GPU voice inference is worth the startup time, resource pressure and compatibility risk on this laptop.

## Voice lifecycle

Verify:

- Push-to-talk.
- Microphone selection.
- Recording permission.
- Audio device changes.
- Maximum recording duration.
- Silence handling.
- Transcription accuracy on controlled fixtures.
- Transcript insertion into chat.
- Voice command submission.
- TTS playback.
- Stop speaking.
- Worker cancellation.
- Worker restart after errors.
- Recovery from unavailable audio devices.
- No orphaned processes.

Show meaningful errors such as:

"Microphone unavailable."

"Speech recognition failed; CPU fallback activated."

"Voice model unavailable."

Do not show a generic CUDA exception to the user without an actionable explanation.

## Resource management

The RTX 4060 must not become a permanent requirement for basic voice interaction.

Avoid running multiple heavyweight TTS/STT models simultaneously.

Do not create extra GPU contention with the 3D avatar.

**Acceptance: I can hold the talk button, speak a question, receive a transcription, obtain an actual assistant response, hear the reply, and interrupt playback without crashing or losing the session.**

Perform native microphone tests only with my explicit permission.

---

# 4. FIX THE ACTUAL DASHBOARD AND CHAT UI

Use the three screenshots as the baseline for visual corrections.

Do not merely change random CSS values.

## Screenshot 1 — Main dashboard

The existing red-and-black command-center aesthetic is a useful foundation and must be preserved.

However, improve:

- Layout balance.
- Empty-space utilization.
- Alignment.
- Typography hierarchy.
- Agent-node presentation.
- Task/status readability.
- Panel spacing.
- Responsive behavior.
- Avatar composition.
- Status indicator clarity.
- Tool activity visualization.
- Resource metrics.
- Conversation input placement.

The current central avatar dominates the screen, while some informational regions feel underutilized.

Keep the avatar prominent, but make the surrounding interface feel like a genuinely useful command center.

Agent nodes currently show Research, Coding and Review as disabled.

Those disabled states must remain accurate, but the UI should explain availability and requirements instead of leaving the impression of broken decorative buttons.

Do not fabricate active agents.

## Screenshot 2 — Chat page

The conversation layout has excessive unused vertical space and prominent engineering controls above the actual conversation.

The controls labeled:

- Attach local background
- Inspect one window · local

currently appear in the main chat view.

Evaluate moving development or specialized operation controls into a clearly organized Tools, Settings, or Capabilities panel.

Keep important actions discoverable.

Improve:

- Conversation message layout.
- Message spacing.
- Streaming feedback.
- Loading indicators.
- Submission state.
- Error banners.
- Execution trace expansion.
- Tool-call visibility.
- Cloud-consent clarity.
- Voice controls.
- Input composer responsiveness.
- Long message scrolling.
- Status synchronization.

The distinction between a connected model, permission to send text to a cloud provider, and availability of tools must be clear.

Do not require users to infer these states from an unexplained checkbox.

## Screenshot 3 — Floating companion

This is a high-priority visual defect.

The floating companion is too cluttered and shows background application content through the interface, reducing readability.

Fix:

- Excessive transparency.
- Text/background contrast.
- Content layering.
- Z-index stacking.
- Window clipping.
- Header alignment.
- Vertical space distribution.
- Chat scrolling.
- Voice-control overflow.
- Input composer positioning.
- Floating action placement.
- Small-window responsive layout.
- Panel separation.
- Scrollbar visibility.
- Footer behavior.
- Hit targets.
- Focus and keyboard interactions.

The compact companion should be intentionally designed for a narrow window, not simply the desktop chat page compressed vertically.

Use solid or sufficiently opaque conversation surfaces.

The page underneath must not visually interfere with chat content.

Keep the input accessible while the message history scrolls.

Ensure the companion cannot accidentally display overlapping, cropped or unreadable controls.

## Required viewport tests

Test against the actual screenshot dimensions and representative configurations:

- 1817 × 942.
- 1841 × 980.
- 532 × 920.
- Smaller compact companion sizes.
- Common 1080p desktop layouts.
- Windows display scaling at 100%, 125% and 150% where testable.

Check actual screenshots and native application behavior.

Do not approve the visual changes based only on static component tests.

---

# 5. PRESERVE AND IMPROVE AVATAR ANIMATION

The avatar is a major part of Immortility's identity.

Do not replace its current model or visual design.

However, coordinate with the other development session that is modifying avatar/GPU files.

Once safe to work on them, verify that the avatar accurately responds to real execution events.

Required states:

- Idle.
- Listening.
- Thinking.
- Streaming.
- Researching.
- Coding.
- Running tools.
- Waiting for approval.
- Speaking.
- Screen guidance.
- Success.
- Failure.
- Cancellation.
- Disconnected.

Transitions should be smooth, interruptible and driven by genuine broker state.

The avatar should not keep playing a thinking animation after the model has failed or returned to Idle.

Voice speaking animations must use real playback state.

Use the existing GSAP/R3F infrastructure.

Avoid unnecessary GPU use while the app is idle.

Respect reduced-motion and power-saving modes.

---

# 6. FINISH THE INTERRUPTED BACKGROUND ATTACHMENT

The previous session was implementing an explicit attachment to a separately running local-only broker.

Continue from the actual code.

Inspect:

- DPAPI credential protection.
- Broker process identity validation.
- Ownership and duplicate-instance prevention.
- Connection authorization.
- Rust supervisor integration.
- Desktop IPC contracts.
- Dashboard attachment and detachment.
- Reconnection.
- SSE event replay.
- Task lifecycle.
- Stop propagation.
- Shared SQLite ownership.
- Background runtime shutdown.
- Log cleanup and owned descendant reaping.

The previous session encountered:

- A smoke-test status mismatch (`completed` versus `succeeded`) that was reportedly corrected.
- A Windows cleanup race involving descendant process log handles.
- An MCP request deadline during heavy concurrent compilation.
- An interrupted 300-second background-attachment smoke.
- An unfinished Rust build/verification sequence.

Reproduce and resolve these issues without hiding failures through arbitrary timeout increases.

Check for leftover processes from the interrupted tests, but only terminate processes that can be positively identified as belonging to the test.

Do not kill unrelated Python, Rust, WebView2 or user processes.

## Required actual behavior

A user should be able to:

1. Start an authorized background task.
2. Close or detach the dashboard.
3. Allow eligible headless work to continue.
4. Reopen Immortility.
5. Reconnect securely to the same running broker.
6. Observe the current task and its real progress.
7. Stop the task.
8. Confirm all owned task workers have stopped.

If background mode is not configured, clearly explain that it is unavailable.

Do not silently install an autorun service or permanently running daemon.

Windows GUI automation must pause when the interactive session is unavailable.

Verify that app shutdown, dashboard detachment, background process shutdown and task cancellation are distinct operations.

---

# 7. IMPROVE GPU/CPU OPTIMIZATION WITHOUT BREAKING VOICE

My machine uses an NVIDIA RTX 4060 Laptop GPU and AMD integrated graphics.

Another development session may already be modifying GPU handling.

Reconcile those changes only after preventing concurrent file conflicts.

Implement adaptive performance where supported.

- Use the RTX when it materially improves active 3D rendering or approved local inference.
- Avoid unnecessary GPU use for basic audio capture and ordinary broker operations.
- Use CPU execution for lightweight deterministic operations.
- Avoid keeping large voice or AI models loaded without need.
- Pause or throttle rendering when hidden.
- Prevent competing heavyweight local AI tasks from exhausting VRAM.
- Clearly distinguish rendering GPU selection from CUDA inference-device selection.
- Do not assume switching the graphics adapter automatically changes the device used by speech models.

Measure actual CPU, GPU, RAM, VRAM and rendering performance.

A dashboard animation improvement must not make microphone transcription or local TTS less reliable.

---

# 8. COMPLETE SCREEN UNDERSTANDING AND GUIDED EXPLANATIONS

After the existing native security gates are satisfied, continue integrating Windows observation.

I want to say:

"Immortility, look at my screen."

"Explain this code."

"Point to the error."

"Move your pointer around this diagram while explaining it."

Implement:

- Authorized window selection.
- Trustworthy foreground window identity.
- Scoped observation leases.
- UI Automation inspection.
- Optional screenshot capture with explicit permission.
- OCR and vision-language fallback where justified.
- Fresh coordinate mapping.
- Explanation-only virtual pointer.
- Visual highlights and overlays.
- Synchronization with spoken explanations.
- Immediate Stop and permission revocation.
- No accidental physical clicks during explanation.

Use the current experimental UIA observer as a starting point.

Do not expose arbitrary screen capture or desktop input before its independent permission checks and native tests pass.

If the Codex Computer Use skill is available, read its actual skill and bundled safety documentation before using it to test Windows UI.

Do not treat Codex's own automation permissions as permissions automatically granted to Immortility.

---

# 9. CONTINUE BUILDING THE FULL AGENTIC AI PLATFORM

Once the immediate reliability and integration problems are contained, continue through the remaining master directive.

Do not stop after polishing the UI.

Complete the eligible parts of:

## Research

- Real multi-source search.
- Web extraction.
- Grounded citations.
- Browser navigation.
- Controlled crawling.
- Document ingestion.
- Source comparison.

## Coding

- Repository analysis.
- Symbol-level retrieval.
- Safe file editing.
- Build and test execution.
- Error correction.
- Verified patches.

## Multi-agent orchestration

- Hermes-primary planning.
- Specialist delegation.
- Task graphs.
- Parallel independent workers.
- Shared progress.
- Checkpointing.
- Budget and cancellation propagation.

## Memory

- Durable facts.
- Project context.
- Provenance.
- Corrections.
- Safe recall.
- Verified improvements to reusable procedures.

## Artifact creation

- DOCX.
- PDF.
- PPTX.
- XLSX.
- Charts.
- Diagrams.
- SVG.
- Actual rendered document verification.

## External integrations

- Standard MCP.
- APIs.
- Approved OAuth connectors.
- GitHub.
- Vercel.
- Email/calendar.
- Cloud storage.
- Other supported tools.

## Automation

- Scheduled tasks.
- Durable background work.
- Notifications.
- Task recovery.
- Safe unattended execution.

Use existing maintained dependencies and Hermes capabilities wherever possible.

Do not install several competing agent frameworks just to increase the feature count.

Keep cloud tokens and resource consumption tightly controlled.

---

# 10. REQUIRED END-TO-END TESTS BEFORE REPORTING SUCCESS

At minimum, complete the following demonstrations.

### A — Real chat response

Ask "Who are you?" and "What can you do?"

Verify actual text appears, correct conversation ownership and visible terminal state.

### B — No-response regression

Simulate empty provider output, slow inference, cancellation and reconnect.

Confirm the UI never silently reports success without displaying the outcome.

### C — Local microphone

Record an authorized voice command, transcribe it, and recover gracefully if the GPU backend is unavailable.

### D — Full voice conversation

Input → transcription → actual assistant response → TTS → user interruption.

### E — Compact companion

Show the companion at narrow dimensions with readable content and no overlapping controls or intrusive background bleed-through.

### F — Dashboard

Verify genuine events drive agent status, avatar state, task cards, timeline and resource displays.

### G — Background attachment

Start, detach, continue, reattach, inspect and Stop an actual local workflow.

### H — Windows observation

Inspect a scratch app through the permitted native flow; verify password controls and disallowed targets remain protected.

### I — Screen explanation

Explain a permitted scratch document using visual highlights without taking control of the physical cursor.

### J — Reliability and security

Run the full existing test suite, contracts, type checks, lint, formatting and native tests as appropriate.

Verify no secret exposure, permission bypass or orphaned subprocesses.

### K — Performance

Benchmark chat latency, startup, idle RAM, active GPU use, TTS/STT execution and dashboard FPS on the actual machine.

### L — Broader capabilities

Continue implementing and validating document creation, research, coding, agents and tool integration under the original acceptance gates.

Separate results into:

- Verified real operation.
- Verified local integration.
- Mock-tested only.
- Experimental and disabled.
- Blocked.
- Not implemented.

Do not mark mock-tested capabilities as production-ready.

---

# 11. IMPLEMENTATION ORDER

Execute in this priority order.

**Phase 0 — Recovery and ownership**

Verify the checkout, concurrent editor status, current tests and interrupted processes.

**Phase 1 — Critical chat reliability**

Fix the no-response/Idle bug and assistant identity/capability presentation.

**Phase 2 — Microphone and CUDA**

Identify the exact failing component, repair the speech pipeline, add reliable CPU fallback and test voice end to end.

**Phase 3 — Dashboard and companion corrections**

Fix layout, overlays, readability, responsive design, interaction states and visual regressions.

Avoid conflicting with the other active avatar/GPU editor.

**Phase 4 — Background attachment**

Complete DPAPI-protected attachment, lifecycle management, reconnect, crash recovery and Stop.

**Phase 5 — Screen intelligence and visualization**

Integrate trusted observation, spoken explanation, highlights, pointer behavior and real activity-driven avatar states.

**Phase 6 — Production capability expansion**

Continue the master roadmap for research, coding, multi-agent orchestration, memory, documents, external tools and scheduling.

**Phase 7 — Full production validation**

Perform actual end-to-end tests, resource benchmarks, security reviews, native Windows verification and regression checks.

Respect dependencies and work on independent tasks when another slice is blocked.

---

# 12. EXECUTION RULES

- This is an implementation task, not a research-only task.
- Preserve all existing working functionality.
- Do not reset Git or delete untracked files.
- Never overwrite concurrent user edits.
- Do not secretly alter Windows security settings.
- Do not automate login or authentication dialogs.
- Do not spend money or trigger paid inference.
- Do not upload private files, screenshots or recordings without permission.
- Do not introduce an unrestricted desktop-control channel.
- Do not fabricate tool execution or progress.
- Do not use hardcoded chatbot replies to conceal backend defects.
- Do not weaken tests to make them pass.
- Keep expensive models and workers lazy-loaded.
- Validate new features on the real runtime whenever feasible.
- Report limitations accurately.
- Update the existing implementation checkpoint after each validated work slice.

When visual screenshots or microphone tests require native consent, request that specific approval and continue independent work where possible.

Do not promise that unexecuted tests or future steps have already been completed.

---

# 13. FINAL EXPECTED EXPERIENCE

I should be able to launch Immortility and have a polished, readable interface.

When I type:

"Who are you?"

I should receive a real, correctly displayed response—not an unexplained transition back to Idle.

When I hold the microphone button:

Immortility should capture my voice locally, recognize speech through a working backend, reply, speak naturally and allow interruption.

If GPU speech inference fails, the supported CPU path should remain functional.

When I expand the command center:

The dashboard should look refined, aligned and responsive, with smooth animations and genuine agent activity.

When I open the floating companion:

It should be compact, readable, correctly layered and comfortable to use over other applications.

When I say:

"Explain what's on my screen."

Immortility should inspect a permitted window, identify relevant content and explain it through voice with synchronized highlighting.

When I say:

"Create a 40-page report while I'm away."

It should execute the authorized headless workflow, create actual DOCX/PDF deliverables, verify page count and formatting, and preserve task state across dashboard detachment.

When I assign a complex project:

It should choose appropriate tools, use specialist agents when beneficial, execute real tasks and provide verified results.

**The standard of completion is reliable, observable, actual user-facing functionality—not test counts alone.**

## START NOW

Recover the actual current checkpoint and finish the interrupted work safely.

Prioritize the chat no-response problem, microphone/CUDA failure, companion layout and background attachment.

Continue through the remaining eligible implementation milestones.

Preserve all existing user work, avatar assets and selected voice profiles.

Keep the system optimized for speed, low cloud-token consumption, low idle resource usage, reliability and security.

Implement the work, test it, and document the actual evidence.