# IMMORTILITY — AUTONOMOUS DESKTOP INTELLIGENCE, LIVE SCREEN UNDERSTANDING & UNATTENDED EXECUTION

## CRITICAL ADDITION TO THE EXISTING MASTER DIRECTIVE

Immortility must become a genuinely useful, screen-aware, voice-interactive personal AI capable of carrying out complex, long-running tasks on my Windows laptop while I am not actively supervising it.

This functionality is mandatory for the intended product.

Preserve the existing implementation and continue from the current development state. Do not restart the project or redesign the 3D dashboard.

## 1. REAL SCREEN AWARENESS

Implement a permission-controlled screen-understanding system.

Immortility must be able to:

- Capture the currently authorized monitor, application or window.
- Understand visible text, code, diagrams, charts, menus and interfaces.
- Identify UI elements using Windows UI Automation and accessibility trees.
- Use OCR or vision-language models when structured information is insufficient.
- Understand my references such as "this", "that button", "the error on the right" and "the graph at the bottom".
- Track authorized interface changes while performing a task.
- Recognize when a window moves, resizes, closes or loses focus.
- Understand multiple monitors and DPI scaling.
- Use application-native APIs or structured content instead of screenshots whenever more reliable.
- Automatically refresh stale visual context before interacting.

Screen capture must be task-scoped, permission-controlled and clearly indicated.

Use event-triggered captures or low-frequency sampling where possible. Do not continuously record or upload my entire screen unnecessarily.

Keep screen contents local by default. Any cloud vision request involving screen content requires appropriate authorization.

## 2. VISUAL POINTER AND VOICE-GUIDED EXPLANATIONS

I want to say:

"Immortility, explain this code and show me where the issue is."

Or:

"Explain this diagram and move your cursor to each component while explaining it."

Immortility must:

1. Understand the current authorized screen.
2. Identify the relevant elements.
3. Produce an explanation.
4. Highlight each element at the appropriate moment.
5. Synchronize highlights with spoken explanations.
6. Move a virtual pointer smoothly between relevant regions.
7. Optionally control the physical cursor when permitted.
8. Correctly handle scrolling and multi-monitor coordinates.
9. Pause or stop pointing when I interrupt or take manual control.
10. Avoid accidentally clicking when the task requires explanation only.

Implement a nonintrusive visual overlay for arrows, outlines, highlights and pointer indicators.

A virtual overlay should be the default for explanation mode because it avoids hijacking my physical mouse.

Use real cursor control only for actual authorized UI actions or when explicitly requested.

Integrate with the existing STT/TTS system.

Speech should support interruption, and visual highlighting must stop when speech is cancelled.

Test this with real code editors, documents, diagrams and browser pages.

## 3. AUTONOMOUS UNATTENDED TASK EXECUTION

This is a mandatory feature.

I should be able to give Immortility a substantial goal and leave my laptop while it completes the work.

Example:

"Immortility, research this subject and produce a professional 40-page report. Include citations, diagrams, tables and a bibliography. Generate both DOCX and PDF, validate them, and save them in my Reports folder. Complete the authorized work while I'm away."

The system must independently:

1. Understand the task and expected deliverables.
2. Determine whether sufficient instructions have been provided.
3. Create a task plan with verifiable milestones.
4. Identify available tools and required resources.
5. Obtain required task-scoped permissions before unattended execution.
6. Schedule independent subtasks efficiently.
7. Delegate specialist work only when worthwhile.
8. Execute research and artifact creation.
9. Check output quality and correctness.
10. Retry recoverable failures within budgets.
11. Save progress and checkpoints.
12. Produce real deliverable files.
13. Reopen, parse and render generated artifacts for verification.
14. Verify the requested page count, citations, formatting and output locations.
15. Produce a completion report with actual evidence.

For a 40-page report, verify the rendered PDF page count. Do not mistake 40 pages of generated text for an actual 40-page document.

Never invent research citations to fill pages.

The task must remain operational without the chat UI or dashboard being open, provided the authorized background runtime is available.

## 4. PERSISTENT BACKGROUND TASK ENGINE

Implement a robust background execution service integrated with the existing broker.

Required capabilities:

- Persistent task queue.
- Long-running tasks.
- Scheduled tasks.
- Task dependency graphs.
- Checkpointing.
- Crash recovery.
- Restart recovery.
- Bounded retries and exponential backoff.
- Progress monitoring.
- Cancellation propagation.
- Process cleanup.
- Failure isolation.
- Resource reservation.
- Automatic completion verification.
- Notifications.
- Detailed execution history.

Do not create a second conflicting task-lifecycle owner.

The Python broker remains authoritative for task admission, permissions, budget reservations, cancellation and execution state.

When the GUI closes, a previously authorized background task may continue through an explicitly installed and configured background supervisor.

A task must not depend on an open chat window.

If a Windows interactive session is locked or unavailable, background operations that do not require a desktop may continue, but UI automation must pause safely until an authorized interactive session is available.

Never bypass the Windows lock screen, UAC or protected-desktop boundaries.

Support resuming paused UI automation only after validating that the previous window, target and permission context are still correct.

## 5. AUTONOMOUS APPLICATION WORKFLOWS

Immortility must be capable of executing authorized workflows across applications.

Examples:

- Open a development project.
- Inspect code.
- Modify permitted files.
- Run approved tests.
- Diagnose failures.
- Create documentation.
- Generate an Excel spreadsheet.
- Produce an editable PowerPoint.
- Save and verify outputs.
- Prepare a Git commit or pull request.
- Inspect a Vercel deployment.
- Automate permitted repetitive desktop operations.

Prefer direct APIs, file libraries and deterministic tools over mouse clicking.

Use Windows UI Automation when native integration is unavailable.

Use screenshot-based interaction only when necessary.

Every action should be verified against the expected application state.

Never assume an action succeeded merely because the click command returned successfully.

## 6. INTELLIGENT PERMISSION AND AUTONOMY SYSTEM

Build configurable autonomy modes:

### OBSERVE

Read-only screen inspection and explanation.

### ASSIST

Suggest actions and request approval before making changes.

### AUTONOMOUS SCOPED TASK

Execute a predefined task within approved files, apps, domains, resource limits and permissions without repeatedly asking for approval.

### SCHEDULED AUTONOMATION

Execute previously configured workflows when their triggers occur, under persistent but revocable scoped permissions.

The system must distinguish ordinary reversible work from sensitive actions.

Examples of actions requiring stronger or fresh authorization include:

- Deleting important files.
- Sending external messages.
- Installing software.
- Publishing or deploying changes.
- Making purchases.
- Accessing sensitive credentials.
- Modifying security settings.
- Changing permissions.

When additional authorization is required and I am absent, pause only the affected step. Continue independent authorized work where possible.

Never treat a broad instruction such as "do anything" as unlimited permission.

## 7. SCREEN-AWARE MULTIMODAL AGENT LOOP

Implement the following execution pattern:

User voice/text instruction
→ Task planner
→ Permission and budget validation
→ Screen/app-state observation
→ Context retrieval
→ Model/tool selection
→ Authorized action
→ Result observation
→ Independent verification
→ Progress checkpoint
→ Next action or completion

Use adaptive observation.

Do not invoke a vision model after every deterministic action if the resulting state can be verified through structured APIs or accessibility information.

Use cached observations only while the relevant application state remains valid.

Treat displayed webpage/document text as untrusted information.

Ensure downloaded documents and third-party MCP tools cannot override the system's instruction hierarchy or permissions.

## 8. OPTIMIZE FOR THE ACTUAL LAPTOP

Target the existing Windows laptop with RTX 4060-class 8 GB VRAM and 16 GB RAM.

Optimize for:

- Low idle RAM consumption.
- Low idle CPU consumption.
- Minimal unnecessary screenshots.
- Minimal cloud vision calls.
- Minimal LLM tool-call overhead.
- Selective context retrieval.
- Local deterministic processing.
- Lazy model loading.
- GPU contention avoidance.
- Background worker cleanup.
- Intelligent model routing.
- Low latency for interactive explanation.
- Efficient execution for long-running tasks.

Do not keep large models, browser instances or GUI automation workers running unnecessarily.

A background task should not require the 3D dashboard to continuously render.

Measure performance with real workloads rather than assuming optimization succeeded.

## 9. REQUIRED END-TO-END TESTS

Implement real acceptance tests covering:

### Test 1: Explain visible code

Open a test project, request an explanation, identify the correct code region and provide a spoken explanation.

### Test 2: Cursor-guided explanation

Open a test diagram, identify multiple elements, highlight each in sequence, and synchronize the explanation with speech.

### Test 3: Autonomous 40-page report

Provide a report brief, authorize a scratch output folder, leave the UI unattended, and verify that a genuine formatted DOCX and exactly 40-page rendered PDF are produced with valid citations.

### Test 4: Cross-application task

Use approved tools to inspect files, perform a reversible application action and generate a verified artifact.

### Test 5: Long-running background job

Start a task, close the dashboard, confirm the authorized worker continues, and inspect the completed result after reopening the dashboard.

### Test 6: Interruption and recovery

Cancel a running task and verify child processes stop without orphaned workers.

Restart an interrupted job from a valid checkpoint without repeating irreversible actions.

### Test 7: Locked desktop

Verify that headless tasks can continue where supported, while GUI interaction pauses without attempting to bypass Windows session protections.

### Test 8: Permission revocation

Revoke access during an active task and confirm further restricted actions are blocked.

### Test 9: Efficiency

Measure cloud tokens, screenshot frequency, CPU, RAM, VRAM, elapsed time and cost for representative workflows.

Use mocked tests for development, but do not call a capability verified until appropriate real runtime and native Windows tests pass.

## 10. IMPLEMENTATION PRIORITY

Integrate this work into the current master roadmap.

Screen understanding, guided pointing and unattended background execution are first-class product capabilities.

Do not defer them merely because the dashboard or chat interface already works.

Complete prerequisite security, MCP, process-lifecycle and task-accounting repairs first.

Then implement:

1. Durable background task execution.
2. Read-only screen awareness.
3. Pointer overlays and voice synchronization.
4. Broker-controlled Windows actions.
5. Cross-application workflow execution.
6. Fully unattended document and coding tasks.
7. Recovery, permission and performance verification.

Continue implementing other independent milestones from the original master directive where safe.

## FINAL REQUIREMENT

I want Immortility to feel like a genuinely capable personal digital assistant.

I should be able to say:

"Immortility, look at my screen and explain this."

"Show me where the error is."

"Point to that button and explain what it does."

"Open my project, fix the errors and run the tests."

"Prepare a complete 40-page report while I'm away."

"Create a PowerPoint, Excel workbook and PDF from this research."

And Immortility should carry out the authorized work through actual tools, applications and files, with independent verification.

Preserve all existing work, security restrictions, voice profiles and dashboard contracts.

Do not stop at simulated demonstrations or incomplete adapters.

Report which capabilities pass real tests, which are experimental, and which remain blocked.

**Build a reliable autonomous desktop AI that understands my computer, explains what it sees, performs long tasks, and completes genuine work without requiring constant supervision.**