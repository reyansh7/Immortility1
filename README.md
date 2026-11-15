# IMMORTILITY — Production Architecture Blueprint (v1.0)

**Personal, Windows-first, voice-first, multimodal, agentic desktop companion.** Hybrid holographic orb at the edge of the screen; expandable humanoid avatar and 3D command center.

> Status: **P0/P1 developer preview with integrated P2 local voice**, not production-ready. Hermes text streaming, history, cancellation, Windows Credential Manager, local Whisper/Piper and content-free traces are implemented. Real microphone and remaining Windows interaction/performance gates are tracked in `docs/P1_P2_VALIDATION.md`. P3–P8 remain planned. No runtime mock mode is silently enabled.

The current master prompt's consolidation rules are recorded in
[`docs/architecture/CONSOLIDATION.md`](docs/architecture/CONSOLIDATION.md).
Hermes stays primary; the broker stays authoritative for permissions and task
lifecycle. OpenMausBot replaces the **planned** Grok Bot bridge after verification,
but is not installed or enabled. Existing memory, scheduling and computer-control
infrastructure was not migrated. See [`docs/phases/P0_AUDIT.md`](docs/phases/P0_AUDIT.md)
for the new combined-checkout baseline and measured results.

## Run on Windows PowerShell

From the project root containing this README:

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap-dev.ps1
# Edit .env locally if no key is configured. Never paste keys into chat or source files.
notepad .env
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-command.ps1
```

After that install, open a new Command Prompt or PowerShell window:

| Command | Behavior |
|---|---|
| `immortility` | On AC power, render on the high-performance GPU. On battery, use the power-saving GPU. |
| `immortility -performance` | High-performance GPU and a 60 fps interaction cap. `-gpu` is the same choice. |
| `immortility -balanced` | Power-saving GPU and a lower idle frame rate. |
| `immortility -battery` | Power-saving GPU, lower resolution, and the lowest idle frame rate. |
| `immortility -headless` | Local background runtime only. No 3D window and no cloud model calls. |

The graphics choice is applied to Immortility's own executable and to the WebView2
process it starts. It does not change the GPU preference of other applications.
An adapter change applies at the next cold start; an already open window is only
brought forward. Leave the desktop launch window open; closing it stops that app.

`ExecutionPolicy Bypass` applies only to that PowerShell process; it does not change
the machine execution policy. `bootstrap-dev.ps1` installs locked packages locally,
creates `.env` only if absent, and never installs system tools. `dev-env.ps1` detects
MSVC and the optional repo-local Rust toolchain. A Windows 10/11 SDK and WebView2
are required. The native shell starts its own loopback broker and isolated Hermes
gateway; **do not separately start your normal Hermes gateway**.

Specialists stay off until Settings enables them. A short question still uses one Hermes
call. A bugfix uses the coding specialist only when that checkbox is on. Workspace
edits stay off until you choose a folder. Immortility can then read that folder, propose
one file replacement, and write it only after you approve. Approved Python tests are
not run: no Windows isolation boundary is verified, so untrusted code execution stays
disabled. A completed edit can be restored from the saved previous text. Wikipedia
research and the local arithmetic MCP server stay off until their Settings checkboxes
are enabled. Qwen speech and computer use stay off.

The first launch is a floating orb. Click to expand; use the move handle to drag;
Escape collapses; Ctrl+Shift+Space opens chat; Ctrl+Shift+Escape or the tray's Stop
action cancels work. Allow cloud text in the chat before sending. Settings shows
provider gates, audio devices and local voice controls. Screen capture and agent tools
remain disabled. Microphone consent starts off; hold push-to-talk to record, release
to transcribe. Without cloud-text consent, the transcript fills the composer for
review. Raw audio is never uploaded by this implementation. Stop voice, the tray
Stop action and Ctrl+Shift+Escape interrupt local audio as well as the agent turn.

The optional voice dependencies are installed by bootstrap. Download the pinned
public speech models once (no API key or microphone access):

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare-voice.py
```

Select LJ or Joe in Settings for the Piper implementation verified in this chat.
Use Read aloud on a completed response. Speech speed, volume, language, device and
voice-response length are configurable. Continuous listening and wake words stay off.

An optional local **INFERNAL** voice now supports Kokoro American Onyx, restrained
metallic processing and conversational timing. The user selected the subtler A
audition; defaults remain unchanged and `INFERNAL_VOICE_ENABLED=false`. See the
[voice refinement evidence and opt-in commands](docs/research/INFERNAL_VOICE_REFINEMENT.md)
for preserved A/B previews, real Windows playback/Stop results, licenses and
remaining acceptance gates. Qwen remains disabled.

The user-approved **Mechanical reference** voice now uses an isolated local XTTS
runtime through the broker, with background prewarming, sentence prefetch and
actual playback-energy face animation. On this PC the reference feature is
enabled; choose **IMMORTILITY · Mechanical reference** in Settings and enable
**Speak assistant replies** after restarting the updated app. It is English-only
in this slice and its model/output license is non-commercial. See
[reference voice evaluation and measured runtime](docs/research/REFERENCE_VOICE_EVALUATION.md).

The current real route is **Hermes → local inference guard → OpenRouter
`openrouter/free`**. Each outgoing request verifies the live catalog price and
forces a zero-price route. Gemini and Groq are displayed but blocked because this
implementation cannot establish account-level free eligibility. Paid inference,
agent tools, model training, screen capture and OS automation remain blocked. Local
Whisper/Piper inference requires no cloud speech subscription.

## Face and dashboard

The animated robotic face (`apps/desktop/public/models/immortility-face.glb`), its Blender
pipeline, animation controls and the GSAP dashboard are documented in
[`docs/visual/FACE_AND_DASHBOARD.md`](docs/visual/FACE_AND_DASHBOARD.md).

## Validate and build

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
.\.venv\Scripts\python.exe .\scripts\smoke-hermes.py --offline
.\.venv\Scripts\python.exe .\scripts\smoke-hermes.py --offline --adversarial
.\.venv\Scripts\python.exe .\scripts\smoke-hermes.py --offline --cancel
# Real local speech fixture + optional synthetic speaker playback (never microphone):
.\.venv\Scripts\python.exe .\scripts\verify-voice.py --play
# Opt-in cloud smoke: fixed prompt; key from Credential Manager or ignored .env.
.\.venv\Scripts\python.exe .\scripts\smoke-hermes.py
.\.venv\Scripts\python.exe .\scripts\check-secret-isolation.py
powershell -NoProfile -ExecutionPolicy Bypass -Command ". .\scripts\dev-env.ps1; pnpm.cmd desktop:build"
```

The offline smoke uses **real Hermes and a fake inference provider**, explicitly
labeled. The ordinary tests use deterministic fake Hermes/provider adapters and
do not access cloud APIs. The real smoke must be invoked separately. A browser-only
Vite preview cannot access the native supervisor and reports disconnected honestly.

The developer binary depends on this checkout, `.venv`, and the reviewed Hermes
source install. It is not a portable installer. Private native runtime state lives
under `%LOCALAPPDATA%\Immortility`; direct broker development uses ignored `data/dev`.
Conversation text is local plaintext SQLite; encryption and history export/deletion
UI are not yet implemented. Credentials load from current-user
Windows Credential Manager, with ignored `.env` as a development fallback. To migrate
an existing key safely, use Settings or run:

```powershell
.\.venv\Scripts\python.exe .\scripts\migrate-secrets.py
```

Migration writes and verifies the vault before atomically removing only the provider
key from `.env`. The frontend has no secret-reading endpoint. See
`docs/P1_P2_VALIDATION.md` for the scoped tests and remaining gates. Newer Qwen
voice-cloning code is now included in the P0 audit. Its isolated environment has
unresolved dependency advisories, so `EXPERIMENTAL_QWEN_TTS=false` by default.
Piper LJ/Joe and text chat remain available; profiles/recordings are preserved.

The follow-up [Qwen security report](docs/security/QWEN_REMEDIATION.md) records all
52 original advisories, applicability and patch conflicts. A separate candidate
update passed CPU profile tests but still fails security acceptance; it is not
enabled or promoted. No re-cloning or audio upload was performed.

See `docs/IMPLEMENTATION_STATUS.md` for evidence and remaining release gates, `docs/VOICE_CLONING.md` for the opt-in local cloned voice, and
`docs/research/EVOLUTION_DIRECTION.md` for the analyzed self-learning roadmap.

## Start here (in order)
1. `docs/blueprint/00_PRODUCT_VISION.md` — end-state, actual examples, scope and non-goals.
2. `docs/blueprint/01_SYSTEM_ARCHITECTURE.md` — Windows architecture and data flows.
3. `docs/blueprint/02_TECH_STACK.md` — selected and optional libraries, GitHub references.
4. `docs/blueprint/03_ROADMAP.md` — ordered milestones and acceptance criteria.
5. `docs/blueprint/04_BEHAVIOR_AND_UX.md` — orb, avatar, voice, workflow behaviors.
6. `docs/blueprint/05_SECURITY_AND_PERMISSIONS.md` — hard security boundaries.
7. `docs/blueprint/06_PERFORMANCE_AND_RELIABILITY.md` — measurable targets.
8. `docs/blueprint/07_MODEL_ROUTING_AND_COST.md` — Gemini/Groq/OpenRouter, Cursor, Grok Bot.
9. `docs/blueprint/08_INTEGRATION_CONTRACTS.md` — message, tool, task, approval contracts.
10. `docs/blueprint/09_ACCEPTANCE_AND_TEST_PLAN.md` — objective definition of done.
11. `docs/blueprint/10_WINDOWS_SETUP.md` — installation and development steps.
12. `docs/blueprint/11_OPERATIONS_AND_RELEASES.md` — upgrades, recovery and telemetry.
13. `docs/blueprint/12_EXTERNAL_REPOSITORIES.md` — projects to reuse and review.
14. `docs/blueprint/13_CAPABILITY_MATRIX.md` — comprehensive feature inventory.
15. `docs/blueprint/14_DECISIONS_AND_ASSUMPTIONS.md` — ADRs, known unknowns.
16. `docs/blueprint/TARGET_REPOSITORY_TREE.md` — complete end-state folder structure.

## Give to your coding agent
Paste **`prompts/START_CODING_WITH_CURSOR.md`** into Cursor (or another coding agent) *from the root of this repository*. The prompt explicitly asks for Phase 0 + Phase 1 only. Don't ask it to generate every future module simultaneously.

## Current credentials
You already have **Gemini API, Groq API, OpenRouter API, NVIDIA API** access, **Cursor Pro** and **Grok Bot** access. Place keys in an ignored local `.env` or native credential store. Never paste secrets in tickets, logs, prompts or screenshots. Chat uses only the verified free OpenRouter route; Gemini, Groq and NVIDIA keys stay stored and are not chat routes.

## Principles
- Windows-native initially; optional remote control later; offline-tolerant when appropriate.
- Use Hermes as primary agent runtime through an official protocol; do not fork it lightly.
- Use built-in provider routing first; add LiteLLM only if needed, to avoid redundant proxies.
- Let Cursor perform coding through its official CLI after explicit workspace approval.
- Use OpenMausBot for future specialist teams after the broker-mediated execution contract is verified; keep the older Grok Bot integration plan superseded without altering unrelated accounts.
- No autonomous destructive actions, screen recording or arbitrary script execution by default.
- No unverified paid API calls; hard budget ceiling of zero additional dollars.
- Don't confuse a visual demo with a functional agent. End-to-end tests determine readiness.

## Sources and provenance
`docs/blueprint/12_EXTERNAL_REPOSITORIES.md` includes upstream official documentation URLs. Library versions, licenses, provider quotas and API surfaces must be reverified and pinned during implementation.
