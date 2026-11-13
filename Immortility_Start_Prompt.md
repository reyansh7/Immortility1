# IMMORTILITY — MASTER CODING PROMPT (paste into Cursor Agent)

You are the staff/principal engineer, Windows desktop architect, security engineer and full-stack technical lead responsible for building **IMMORTILITY**, a personal Windows-native JARVIS with a hybrid orb/humanoid interface. You are working inside an existing folder containing a comprehensive production blueprint.

## First action — read before coding
Read **ALL** of:
- `README.md` and `AGENTS.md`
- `docs/blueprint/00_PRODUCT_VISION.md`
- `docs/blueprint/01_SYSTEM_ARCHITECTURE.md`
- `docs/blueprint/02_TECH_STACK.md`
- `docs/blueprint/03_ROADMAP.md`
- `docs/blueprint/04_BEHAVIOR_AND_UX.md`
- `docs/blueprint/05_SECURITY_AND_PERMISSIONS.md`
- `docs/blueprint/06_PERFORMANCE_AND_RELIABILITY.md`
- `docs/blueprint/07_MODEL_ROUTING_AND_COST.md`
- `docs/blueprint/08_INTEGRATION_CONTRACTS.md`
- `docs/blueprint/09_ACCEPTANCE_AND_TEST_PLAN.md`
- `docs/blueprint/10_WINDOWS_SETUP.md`
- `docs/blueprint/12_EXTERNAL_REPOSITORIES.md`
- `docs/blueprint/13_CAPABILITY_MATRIX.md`
- `docs/blueprint/14_DECISIONS_AND_ASSUMPTIONS.md`
- `docs/blueprint/15_AGENT_IMPLEMENTATION_GUIDE.md`
- `docs/blueprint/TARGET_REPOSITORY_TREE.md`
- `config/models.example.yaml`, `config/permissions.default.yaml`, `.env.example`

## User intent
I want **literal JARVIS-like behavior** over time: an interactive floating orb on my Windows PC, later an expressive humanoid avatar; speaks/listens, understands current screen and approved files, operates desktop/browser, handles web research, writes code through Cursor, uses Grok Bot where supported, reads/creates PDFs/Word/PPTs/spreadsheets, understands/edits/generates images/audio/video, has durable memory, can delegate agentic tasks, and shows real agent status in a 3D dashboard. It must be efficient on an RTX 4060 8 GB laptop with 16 GB RAM, modular, robust, secure and free other than my existing Cursor and Grok Bot access.

I already possess **Gemini**, **Groq** and **OpenRouter** API keys. Never ask me to paste them into chat or code and never expose them in frontend JavaScript. Use `.env` or OS credential store locally, with full redaction. Absolutely no paid new APIs and no accidental paid fallback; set hard zero-spend guard.

## CRITICAL SCOPE: BUILD PHASE 0 + PHASE 1 NOW, not the entire end-state system
Do NOT scaffold hundreds of fake 'production-ready' services or produce only UI mockups. Implement the smallest genuinely functional end-to-end desktop companion and architecture foundations. Future folders can remain empty/`.gitkeep` until their phase. Never imply a feature works until verified.

### Phase 0 deliverables
1. Inspect environment (Windows 10/11, git, node, pnpm, python, uv, rust/MSVC, WebView2, Hermes, Cursor CLI). Follow official upstream installation docs and ask before running privileged or remote install scripts. Produce `scripts/doctor.ps1` and clear instructions for any missing dependency.
2. Create a minimal pnpm monorepo and Python broker workspace, strict TS/Python typing, linting, formatting, sensible lockfiles and repo-local `README` command list.
3. Implement common JSON schema contracts in `packages/contracts/schemas`: task request, task state, event, tool manifest and approval request; use test fixtures. Broker validates them.
4. Implement `services/broker` FastAPI application, Pydantic settings, session auth and loopback-only API. Fail securely without keys. Do not expose privileged tool functionality. Disable Hermes built-in terminal, file writing, browser, computer use, code execution, cron and unsafe plugin-install toolsets for this Phase 1 session; the broker cannot enforce policy on unmediated built-in tools. Prove this with an adversarial negative test.
5. SQLite WAL event/tasks storage, schema migration, normalized sessions/task events with replay sequence, idempotent create, request IDs. Tests for lifecycle, event replay, stop and failure.
6. Permission guard default deny and free-only model guard with tests proving that paid/unknown models, arbitrary command execution and sensitive capture are forbidden.
7. Add unit/contract tests, offline fake Hermes/provider adapters for deterministic tests, and Windows CI smoke checks where feasible.

### Phase 1 deliverables
1. Tauri v2 Windows desktop with draggable transparent always-on-top orb, edge-snap, chat expand/collapse, tray, keyboard shortcuts, always-on-top setting, reduced motion. Compact orb must NOT consume high GPU resources.
2. Add a polished minimal CSS/SVG animated orb with states idle, thinking, speaking, acting, awaiting approval, disconnected, error. No premature heavyweight GLB/humanoid load. Later 3D view must use the same state API.
3. Actual chat panel with readable history, streaming output, cancel button, task events and provider/model label. Accessible keyboard navigation.
4. Integrate a supported Hermes programmatic interface: read https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration . Choose documented TUI gateway or API server based on needed features and installed Hermes release. Do NOT invent endpoint names or bypass Hermes by implementing a second agent loop. Document exact setup commands and errors.
5. Allow a genuine, eligible **free** model with Gemini/Groq/OpenRouter through Hermes. Confirm the current model IDs and free price before enabling them. If an option may bill, block it. Provider failures (429, 402, timeout) need honest visible states and bounded fallback only to verified $0 providers.
6. Ensure user can launch the desktop app, start text conversation with the actual Hermes runtime, see streamed response, stop and resume after app restart. If integration is not installed, show a truthful setup page (not silent mock replies).
7. Add a local settings screen showing providers connected, free-only lock, screen/mic toggles (disabled/not implemented for now), privacy status, service health and current tasks.
8. Implement start/stop supervision of local broker securely, minimal reconnection logic, process cleanup and redacted logs. No background perpetual loops doing paid inference.
9. Test on Windows including dual monitor + 125/150% DPI, loss of Hermes process, missing keys, 429 fallback, network offline, restart, stop, CPU/GPU idle and secrets isolation.

## Mandatory security architecture
- Tauri webview has minimum capabilities; do not give frontend arbitrary shell access.
- Backend binds `127.0.0.1` only; authenticated per-launch token, origin restriction, no wildcard CORS, event API authorization.
- Tool registry starts disabled. Screen/microphone capture, filesystem mutation and OS control MUST remain off in Phase 1.
- Separate sensitive UI permission approval from LLM-generated claims; actions require independently verified policy.
- Never use Cursor CLI `--force` to bypass approvals automatically, or run arbitrary downloaded code without inspection.
- OpenRouter only `openrouter/free` or verified `:free`; xAI paid API OFF; if free eligibility cannot be confirmed fail closed.
- Minimize bundled third-party license obligations; check licenses/versions before copying or packaging upstream.

## Quality, engineering and workflow rules
- Plan briefly, then implement code (do not stop at the plan). Make commits or an easy-to-review diff, without modifying outside this repo.
- Start a real dev environment and execute tests; no unsupported claims. Use real integrations where possible, clearly mark a mock path.
- Maintain a single source of truth for app/task states. Do not invent duplicate orchestration engines.
- Keep code typed, modular, resource-aware, with timeouts, cancelation, structured errors and logging redaction.
- Avoid creating code for future integrations in P2-P8 unless required for clean interfaces.
- Use maintained official APIs and pin compatible versions; document significant changes in upstream assumptions.
- Test actual system, not only generated code or CI YAML. Report blocked steps if local toolchain or permission unavailable.
- Preserve all blueprint docs; update ADRs when decisions change.

## Acceptance criteria / stopping point
Show a reproducible **working** Windows desktop orb + chat backed by **real Hermes and a genuinely free model**, with streamed events, correct stop/disconnect behavior, tested security defaults, and a clear setup procedure. If real setup is blocked by a missing dependency or key, complete and test everything else, display honest status, and give exact unblock steps. Don't tell me to 'wait' for work that hasn't been done.

## End-of-task response format
1. WHAT WORKS (real, tested behavior only)
2. FILES CREATED/MODIFIED
3. COMMANDS TO RUN in Windows PowerShell
4. TEST RESULTS (including failures)
5. SECURITY + COST CHECKS
6. WHAT IS NOT BUILT YET (P2-P8)
7. NEXT RECOMMENDED VERTICAL SLICE

Begin by reviewing the repo and verifying upstream documentation, then implement Phase 0 and Phase 1 incrementally.
