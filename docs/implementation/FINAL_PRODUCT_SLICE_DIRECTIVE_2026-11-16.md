# IMMORTILITY — FINAL CODEX SESSION
## COMPLETE THE CURRENT PRODUCT SLICE, VERIFY EVERYTHING & PRESERVE A STABLE CHECKPOINT

You are the sole implementation engineer for IMMORTILITY, my Windows-native, JARVIS-inspired personal AI assistant.

**IMPORTANT: This is my final available Codex session for now. Optimize for finished, tested, reliable functionality rather than the maximum number of code changes.**

You have already implemented substantial infrastructure and begun the first genuinely useful local-first product capability: scoped project inspection.

Your immediate responsibility is to finish that capability properly, verify its integration, preserve the existing security architecture, and leave the project in a fully documented, resumable state.

**Do not start over. Do not rebuild Hermes, the broker, Engine/Store, or the dashboard.**

Do not spend this session on another extensive audit or architecture proposal.

Implement, test, fix, verify and close the current development slice.

---

# 1. RECOVER THE EXACT CURRENT STATE

Read:

- `AGENTS.md`
- `README.md`
- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/PRODUCT_BUILD_CHECKPOINT_2026-11-16.md`
- `docs/implementation/M3_FINAL_INTEGRATION_WORKLOG.md`
- `docs/implementation/M3_VERIFICATION.json`
- `docs/implementation/ARCHITECTURE_UPDATE_2026-11-15.md`
- `docs/implementation/MAIN_PRODUCT_BUILD_DIRECTIVE_2026-11-16.md`

Inspect the current working tree and recent source changes.

Preserve existing uncommitted changes and unrelated work.

Do not reset, clean, checkout, commit or push.

The latest complete regression checkpoint was:

- **425 Python tests passed.**
- **68 frontend tests passed.**
- **12 Rust tests passed.**
- Contracts, lint, formatting, types, builds and configured-key isolation passed.

These results predate the latest project-inspection additions.

**Do not present 425/68/12 as the current full-regression result until the newest source has been retested.**

Create a short recovery record immediately identifying the existing modified files, implementation scope and current blockers. This should be lightweight, not another architecture report.

---

# 2. EXACT CURRENT DEVELOPMENT STATUS

## A. Scoped project inspection — partially complete

The following components are already implemented:

### Backend

`services/broker/src/immortility_broker/project_inspection.py`

- Authorized project-root selection.
- Bounded literal source search.
- Bounded file-page reading.
- Root identity binding.
- Windows path/reparse/hardlink protection.
- Protected-file and secret filtering.
- File hashes and provenance.
- Cancellation.
- No automatic cloud recall.

### Broker

`services/broker/src/immortility_broker/app.py`

Existing registered capabilities:

- `project.search.v1`
- `project.read.v1`

They operate through the existing capability gateway and Engine/Store workflows.

Project-read permission must never imply permission to edit files, execute arbitrary shell commands or use unrelated tools.

### Frontend

`ProjectInspector.tsx`

Integrated into Settings with:

- Project folder selection.
- Explicit read consent.
- Literal search.
- File-page viewing.
- Task receipts.
- Cancellation.

The existing task-following infrastructure handles replay/reconciliation.

### Existing verification

- 14 new backend tests passed.
- 68 existing frontend tests passed.
- Frontend static checks passed.
- Mypy passed for 50 sources before later metadata changes.

**Remaining: dedicated frontend tests, Rust/native verification, real application interaction acceptance and a complete regression run.**

This is the primary task to finish.

## B. Warm Hermes MCP reuse — confirmed blocked

The latest warm-MCP experiment revealed an actual security problem:

- First profile's broker-controlled MCP clock call succeeded.
- Second profile's MCP request reused the first profile's revoked task credential.
- The broker rejected the request with HTTP 401.

This demonstrates credential crossing between warm MCP profiles.

The security boundary worked correctly.

**DO NOT ENABLE PRODUCTION WARM HERMES REUSE.**

Do not bypass the 401, share credentials across profiles or relax permission checks.

Do not attempt to solve this by introducing a second agent runtime.

Treat warm reuse as a separately blocked engineering milestone.

Preserve the existing per-task Hermes process path, which remains the safe production behavior.

Do not spend this final session repeatedly probing the same confirmed failure unless a small, independently verified upstream-compatible correction is immediately available and all primary work has already passed.

## C. Groq direct-provider metadata

One separately authorized credential-backed metadata GET was completed.

The result established that:

`openai/gpt-oss-120b`

was listed and active, with a reported 131,072-token context window.

Eight metadata tests passed.

This does NOT establish:

- Account billing tier.
- Free-plan entitlement.
- Remaining quota.
- Actual zero-cost eligibility.
- Tool-stream compatibility.
- Production readiness.

Do not repeat the consumed metadata authorization.

Do not make another protected account request or inference call without fresh authorization.

Do not activate this model based only on its listing.

## D. Computer Use

The last attempted browser interaction stopped because the automation runtime could not confidently establish the current Chrome URL.

Respect that restriction.

Do not bypass the policy using alternative browser-control techniques.

Native project-inspector verification should use the supported test harness and authorized native interface where available.

If native interaction cannot safely run, complete all feasible deterministic tests and mark native acceptance explicitly blocked.

---

# 3. PRECISE EXECUTION ORDER — FOLLOW STRICTLY

## STEP 1 — Finish project-inspection frontend behavior

Inspect the existing `ProjectInspector.tsx`, transport integration, Settings insertion and native operations.

Do not redesign the interface.

Correct actual implementation defects.

Verify:

1. Project selection is persisted correctly.
2. Folder changes invalidate old consent and edit authority.
3. Search requires explicit project-read consent.
4. File-page reads are scoped to the selected root.
5. Search results and file contents are presented accurately.
6. Secret/protected-file denials are visible and understandable.
7. No sensitive content reaches unintended logs or model context.
8. Duplicate clicks cannot create duplicate unauthorized operations.
9. Task cancellation stops the correct operation.
10. Disconnection disables unsafe controls.
11. Reconnection correctly reconciles task status.
12. Task receipts match the authorized project/root identity.
13. Errors are displayed without exposing sensitive paths or secrets.
14. Long-running reads remain bounded.
15. No cloud inference occurs.

Preserve existing backend permission enforcement.

Do not rely on frontend validation as the security boundary.

## STEP 2 — Add dedicated frontend and transport tests

Create focused tests for the new UI.

Test:

- Initial state.
- No consent.
- Consent granted.
- Root selection.
- Search success.
- Empty search.
- File-page success.
- Protected-file refusal.
- Network failure.
- Broker disconnection.
- Cancellation.
- Duplicate action prevention.
- Root change.
- Stale result rejection.
- Task receipt presentation.

Use deterministic fixtures.

Do not use real personal project files as test data.

Run focused tests immediately.

Fix failures before proceeding.

## STEP 3 — Complete backend and security acceptance

Recheck the entire project-inspection capability against realistic adversarial inputs.

Include:

- Path traversal.
- Symlink/reparse escape.
- Hardlink behavior.
- Root replacement.
- Directory identity mismatch.
- Secret-file detection.
- Protected paths.
- Binary data.
- Oversized files.
- Unsupported extensions.
- Unexpected encoding.
- Cancellation during scanning.
- Revoked permission.
- Changed project root during an active task.
- Duplicate requests.
- Error/retry handling.
- No unauthorized network or model calls.

Preserve exact root/digest validation and the existing broker capability permissions.

Add only regression tests that materially improve coverage.

Do not unnecessarily rewrite already passing security code.

## STEP 4 — Native Rust and application integration

Run Rust tests and the existing offline native build.

Verify the fixed native operations used by Project Inspector.

Where supported, test the actual Tauri application using a temporary synthetic project.

Demonstrate:

- Select project.
- Grant read consent.
- Search source files.
- Read an authorized file page.
- Reject a protected file.
- Cancel an active operation.
- Change project root and invalidate stale access.
- Recover from broker disconnection.
- Display a verified task receipt.

No real cloud inference.

No personal file upload.

No external account access.

If native automation is unavailable or blocked by security policy, do not bypass it. Record NATIVE BLOCKED and preserve a functioning offline-verified path.

## STEP 5 — Run the complete current regression suite

Once project inspection is stable, run the actual complete checks:

```powershell
& ./scripts/check.ps1

. ./scripts/dev-env.ps1
cargo test --offline --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo build --offline --manifest-path apps/desktop/src-tauri/Cargo.toml

& .venv/Scripts/python.exe scripts/check-secret-isolation.py

git diff --check
```

Use the current repository's documented environment setup if a command differs.

Do not run overlapping heavy test suites.

Record:

- Python tests passed/failed.
- Frontend tests passed/failed.
- Rust tests passed/failed.
- Type checks.
- Lint/format.
- Production builds.
- Secret isolation.
- Project-inspection integration.
- Known environment limitations.

If a test fails, determine whether it is a new regression, a flaky test or an environment problem.

Fix actual regressions without weakening security or test assertions.

**Do not proceed to new features while the full regression is failing.**

## STEP 6 — Close and stabilize the project-inspection feature

After testing, ensure the product is in a coherent state.

Requirements:

- No experimental implementation enabled without verified prerequisites.
- No exposed secrets.
- No authorization bypass.
- No stale UI states.
- No unfinished placeholder code presented as functional.
- No broken imports.
- No unused temporary fixture accidentally enabled.
- No unowned worker processes.
- No incomplete schema changes.
- No unintended cloud calls.
- No regression in the existing dashboard, avatar or voice.

If the feature is fully offline verified but native interaction remains blocked, report that distinction honestly.

Do not disable working project inspection merely because unavailable native automation prevents an optional interaction test.

At this point, the primary implementation objective is complete.

---

# 4. OPTIONAL FOLLOW-ON WORK — ONLY AFTER THE PRIMARY FEATURE IS CLOSED

If the complete project-inspection feature is stable, the full regression passes, and sufficient session capacity clearly remains, select **one** small independent product improvement.

Prefer one of:

- Better project-inspection search relevance, within existing bounded local tooling.
- Clearer source-file and evidence provenance in the UI.
- Improved project-context retrieval without sending private files to cloud models.
- An isolated, testable internal Instant/Deep/Execute/Bots task classification contract, without activating unqualified providers.

Choose whichever has the highest immediate user value and smallest verification burden.

Before starting it, verify that focused tests, integration checks and documentation can also be completed.

**Do not begin another large subsystem.**

Specifically, do not begin:

- A complete memory-system rewrite.
- Advanced multi-agent orchestration.
- Broad computer-use implementation.
- A new browser automation framework.
- Full coding-agent file modification.
- New document engines.
- Local Qwen model installation.
- Production warm Hermes reuse.
- Unverified cloud-provider activation.
- A major dashboard redesign.

These remain future milestones.

The remaining final-session capacity must prioritize stability, not feature count.

---

# 5. STRICT ARCHITECTURE AND SAFETY RULES

Maintain the following architecture:

**Hermes Agent**

Primary intelligence, planning and native delegation harness.

**Immortility Python Broker**

Sole authority for credentials, permissions, capability grants, provider admission and budgets.

**Engine/Store**

Sole durable task, workflow, checkpoint and shared-context owner.

**Tauri / React / Three.js**

Existing native frontend, 3D dashboard and Ultron-inspired interface.

### Provider policy

Forward providers:

- Gemini.
- Groq.
- NVIDIA NIM.

OpenRouter and OmniRoute are excluded from forward development.

Do not add them back.

Do not remove historical compatibility code destructively unless separately authorized and safely verified.

Do not classify an API key or model-list response as proof of free inference.

### Security rules

Do not:

- Reset, clean, checkout, commit or push the project.
- Modify unrelated personal files.
- Upload private project contents.
- Print API credentials.
- Install dependencies or download models without approval.
- Alter Windows security settings or system services.
- Migrate live databases.
- Make cloud inference calls without fresh explicit authorization.
- Repeat consumed protected metadata requests.
- Activate a model with unverified billing status.
- Enable warm Hermes reuse with unresolved credential crossing.
- Weaken grants, deadlines or path restrictions.
- Bypass browser/computer-use policy.
- Replace working frameworks.
- Modify unrelated avatar, voice or rendering assets.

Routine authorized code changes and offline tests may proceed without repeated confirmation.

If external approval is required, record the blocker and continue safe independent work.

---

# 6. HARD STOPPING CONDITION — MANDATORY

**This section overrides any general instruction to keep adding features.**

You must stop starting new development work when ANY of these conditions is true:

### Condition A — Primary feature completed

The project-inspection implementation is finished, dedicated tests pass, the applicable native/build checks have been run, and the complete regression is green.

At this point, stop unless there is clearly sufficient capacity to implement, verify and document one small optional feature.

### Condition B — Full regression begins

Once you begin the final complete regression gate, **do not start another unrelated feature**.

Only correct regressions found by those checks.

After the gate completes, proceed to checkpoint and final reporting.

### Condition C — Remaining session capacity is uncertain

If you cannot confidently finish and verify another feature before the session or usage limit, stop adding code.

Immediately perform the highest-value remaining focused tests, source hygiene and checkpoint documentation.

Do not wait for a usage-limit warning.

### Condition D — A security or authorization blocker appears

If a feature requires new permissions, protected account access, paid inference, unsafe warm credentials or restricted computer control, do not attempt workarounds.

Mark the operation BLOCKED and continue only independent authorized tests or documentation.

### Condition E — Tests cannot be made green safely

If a regression cannot be resolved without weakening security, making unapproved external changes or creating an unbounded implementation, stop expansion.

Preserve the last verified working behavior, disable only the new unverified path if necessary, and document the exact failure.

Do not blindly undo unrelated dirty changes.

---

# 7. CLOSURE MUST HAPPEN BEFORE THE SESSION ENDS

Maintain a small, continuously updated implementation checkpoint during the work.

Do not postpone every documentation update until the very end.

Once the primary functionality and verification are complete, update:

- `docs/implementation/CURRENT_STATUS.md`
- `docs/implementation/PRODUCT_BUILD_CHECKPOINT_2026-11-16.md`
- `docs/implementation/M3_VERIFICATION.json`, if the current machine evidence schema requires updating.

Create a fresh, uniquely named evidence file if appropriate.

Preserve historical verification records.

The checkpoint must contain:

1. Current Git HEAD and dirty-state marker.
2. Exact files changed.
3. Features completed.
4. Features partially implemented.
5. Tests run and exact results.
6. Security checks.
7. Native acceptance status.
8. Known defects.
9. Remaining blocked operations.
10. Exact next development step.

If full regression cannot complete, clearly record that it did not complete.

Never claim the old 425/68/12 result is current-source acceptance without a new complete run.

---

# 8. FINAL RESPONSE REQUIRED

Provide a concise but detailed engineering handoff.

Use this exact structure:

## IMPLEMENTED

What functionality is now actually available?

## VERIFIED

Exact tests, builds and integration results.

## NATIVE ACCEPTANCE

What was demonstrated in the real Windows application, and what remains unverified?

## SECURITY

Confirm project-root protection, consent, credentials, cancellation and warm-Hermes restrictions.

## UNFINISHED OR BLOCKED

List every remaining issue and why it is unresolved.

## FILES CHANGED

Identify the important modifications.

## NEXT STEP

Provide the single next highest-value implementation slice for the next Codex session.

## CHECKPOINT

Identify where the verified state has been saved.

Do not claim release readiness without actual evidence.

---

# 9. FINAL OBJECTIVE

IMMORTILITY is ultimately intended to become an intelligent, natural-speaking, highly capable Windows AI assistant.

Its final features include:

- Instant conversations.
- Deep reasoning.
- Real tool execution.
- Web research.
- Coding.
- File and document manipulation.
- Persistent memory.
- Multi-agent delegation.
- Authorized computer use.
- Voice interaction.
- A responsive 3D command center.

But completing those features requires multiple verified development slices.

**This session's responsibility is to finish and stabilize the current product slice without leaving unnecessary unfinished implementation.**

Do not prioritize feature count over actual reliability.

Do not repeatedly perform architecture research already completed.

Do not waste the final available session on experiments that cannot be safely completed.

**EXECUTION ORDER:**

1. Recover latest state.
2. Complete Project Inspector UI.
3. Add dedicated frontend tests.
4. Verify backend security and cancellation.
5. Run Rust/native integration.
6. Run complete regression.
7. Fix any regressions.
8. Stabilize the feature.
9. Optionally complete one tiny independent improvement only if sufficient capacity remains.
10. Write the verified final checkpoint and engineering handoff.

**SUCCESS CRITERION: A stable, tested, genuinely useful Project Inspector capability, with no security regression, no unverified production activation and an exact continuation point.**

START IMPLEMENTING NOW.