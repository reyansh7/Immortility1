# Implementation and verification — 2026-11-13

Latest continuation: [critical repairs checkpoint](implementation/CRITICAL_REPAIRS_CHECKPOINT.md), [measured verification and changed-source manifest](implementation/CRITICAL_REPAIRS_VERIFICATION.json). **263 Python / 55 frontend / 6 Rust passed**; native background attachment, stored-result replay, visible chat outcomes and CPU speech repairs have scoped acceptance evidence. General autonomous desktop/coding/artifact capabilities remain incomplete. The older audit below is historical.

## Current P0 consolidation audit

The latest authoritative record is [P0_AUDIT.md](phases/P0_AUDIT.md), with
[ownership decisions](architecture/CONSOLIDATION.md),
[repository matrix](integrations/REPOSITORY_MATRIX.md) and
[performance baselines](performance/BASELINES.md). The complete current checkout
and a credential-free frozen-lock source reproduction both passed **78 Python +
5 frontend tests**, lint/types/contracts/build. Three native tests passed, and
updated native builds launched successfully. Keyboard movement, compact anchor
restore, restart restore, single instance and the global open shortcut were exercised.

The 10-minute idle baseline completed with verified process cleanup; UI CPU
averaged 0.0368%, UI working set 284.93 MB (target still missed). OpenMausBot source
MCP discovery passed a network-disabled probe; the application is absent and no
team/controller/browser integration was activated. No user memory/jobs/controller
was replaced. The planned Grok Bot bridge is superseded by OpenMausBot; historical
notes and unrelated installation/configuration were preserved.

The isolated Qwen environment has **52 advisory entries across four packages**.
It is now explicitly gated off by default; the clone profile and recording remain
preserved. The user heard Piper during a voice test and requested the friend clone;
metadata showed LJ selected. Native Qwen end-to-end remains unverified, and UI
automation stopped immediately when the user's physical Escape key stopped Computer Use.

The subsequent [Qwen security investigation](security/QWEN_REMEDIATION.md) enumerates
all 52 entries and conditional exposure. An independent candidate with setuptools
81.0.0 passed seven CPU-only profile regressions, but retains 51 direct findings
plus an additional upstream-base Torch advisory. It was not promoted or enabled.
All 13 recorded private voice assets remain checksum-identical.

Older scoped reports below are historical and do not override this audit.

## P1 hardening and P2 local voice update

The project root is now `C:\Users\reyan\OneDrive\Desktop\IMMORTILITY`; the extra
`Immortility` directory was removed after verified relocation. See
[ROOT_RELOCATION.md](ROOT_RELOCATION.md).

This chat implemented and tested current-user Windows Credential Manager migration,
Whisper CPU transcription with Silero VAD, Piper LJ/Joe synthesis/playback,
interruptible audio workers, explicit push-to-talk consent, one shared Hermes task
history, responsive orb states and versioned content-free execution traces.
51 scoped Python tests pass. Native read-aloud, Stop voice and device enumeration
were exercised. The detailed test/performance report and remaining manual gates
are in [P1_P2_VALIDATION.md](P1_P2_VALIDATION.md).

This is **integrated, partially verified P2**, not completed P2 acceptance or a
production-ready release. Physical microphone capture, manual drag/snap, tray,
multi-monitor/DPI, active live-inference native Stop and performance targets still
need the evidence listed in that report. Newer Qwen cloning work was preserved and
excluded from this chat's validation at the user's request.

## Original P0/P1 verification record

This is a working developer preview, not a production release or a claim that all
P1 release gates have passed. No P2–P8 capability is implemented by an empty folder.

## Verified working

- Built and launched an actual Tauri 2 Windows executable with transparent floating
  CSS orb, expandable chat and native always-on-top window configuration.
- Native chat → restricted Rust IPC → authenticated loopback broker → real Hermes
  v0.21.1 stdio gateway → guarded OpenRouter `openrouter/free` → native streaming
  channel → visible chat answer. The native test persisted **three message deltas**
  and a succeeded task. No provider response was simulated in this test.
- The model answered “Immortality is connected.”, changing the spelling in the
  fixed test prompt. The UI displayed that actual output without correction.
- Relaunch restored that answer and session. An earlier forcibly interrupted turn
  correctly returned as disconnected with an explicit restart message.
- Ctrl+Shift+Space opened chat. A second application launch exited and activated
  the first instance; only one native instance remained.
- Force-stopping the owned test instance removed both broker launcher/interpreter
  processes through the Windows Job Object. Real-Hermes offline cancellation also
  reaped its process and persisted cancelled, without invoking a cloud provider.
- Default-deny tool policy, paid/unknown pricing rejection, separate inference
  credential, source pin check, session auth, origin/Host checks, SSE auth/replay,
  idempotency conflicts, bounded concurrency, missing-key handling, 402/429/offline
  errors, SQLite WAL history, future-version database rejection and restart recovery.
- An adversarial fake provider attempted a terminal tool call while driving **real
  Hermes**. It was blocked before Hermes saw the call; no tool executed.
- The actual configured provider key is absent from UI source, built UI assets,
  docs and checked-in example configuration. Native IPC exposes no credentials.

## Implemented but not fully verified manually

Tray controls, global stop wiring, pin/unpin, reduced-motion checkbox, position
restore by monitor, drag and edge snapping. Drag attempts through the computer-use
helper were constrained by window bounds and did not establish successful movement.
Independent manual drag/snap, tray interactions, multi-monitor disconnect and
125%/150% DPI checks remain required. Compact placement is stored independently
of the tall expanded panel so opening chat does not replace the orb anchor.

Cancellation has deterministic HTTP integration tests and a real-Hermes offline
process test. The live native UI showed its Stop button during inference; an active
live-cloud cancellation through that button was not separately exercised.

## Executed checks

| Check | Observed result |
|---|---|
| `scripts/check.ps1` | 30 Python tests, 4 Vitest tests, schema/type freshness, Ruff, strict mypy, TypeScript, ESLint, Prettier, Vite build pass |
| `cargo test --locked` | 2 native security tests pass |
| `cargo clippy --locked -- -D warnings` | Pass |
| Tauri debug build, no bundle | Pass; real executable launched |
| Real Hermes + offline fake inference | Succeeded; protocol integration verified |
| Real Hermes + adversarial fake inference | Blocked; no tool execution |
| Real Hermes + offline cancellation | Cancelled; process reaped; zero provider calls |
| Real Hermes + live verified free model | Succeeded; separate broker smoke and native UI test |
| `pip-audit`, `pnpm audit` | Zero known advisories in final scanned graphs |

Two third-party TestClient deprecation warnings remain (httpx compatibility and
AnyIO portal alias). They do not fail tests. A forced Windows socket close emitted
a Proactor reset warning in an earlier smoke run; bounded graceful gateway shutdown
with process-tree kill fallback was added, and the repeated cancellation test passed.

The GitHub Windows workflow is supplied but has not been run remotely. RustSec/SBOM,
full transitive license audit and signed release/installer gates remain open.

## Machine and toolchain

Windows 11 Home Single Language, build 10.0.26300; approximately 16 GB RAM; NVIDIA
RTX 4060 Laptop GPU plus AMD integrated graphics. Node 22.13.1, pnpm 10.27.0,
Python 3.13.11 for the broker, Hermes' existing Python 3.11.16 runtime, repo-local
Rust 1.100.0, Visual Studio 2022 MSVC and WebView2. The missing Windows SDK was
installed with explicit approval through Microsoft's signed Visual Studio Installer;
the elevated install exited 0. Rust was installed only in ignored `.tools`, without
modifying the user's PATH. Cursor CLI remains absent and is not needed until P5.

Initial native compilation failed for missing Rust/SDK libraries; these failures
were resolved. Native health and task admission then exposed synchronous Git probing
inside active Windows request paths. Compatibility checks now run once at broker
startup, before the native handshake. No synchronous Git probe runs in a turn.

## Cost and privacy boundaries

Only OpenRouter `openrouter/free` is enabled. Every outgoing model call rechecks live
zero prices; its request is rebuilt with no tools, plugins or paid fallback, and
zero provider max prices. No automatic retry is sent after a provider rejection.
Gemini, Groq and NVIDIA keys can be stored in Windows Credential Manager. They are shown as stored, not as chat routes, because account-level free eligibility and NVIDIA NIM prices are unverified.
There is no paid xAI path, automatic top-up or extra subscription.

Hermes has an isolated temporary profile, explicit empty built-in toolset, disabled
toolsets, empty MCP/plugins/hooks and no inherited provider credentials. The broker
requires the built tool inventory to be empty before submitting text. Browser, files,
terminal, code execution, cron, installs, screen and microphone capabilities stay off.

The webview receives only typed data/events; Rust retains broker auth and permits
only enumerated local operations. CSP disallows direct HTTP access from the UI.
The inference credential and provider key stay backend-side. Prompt-free local
request metadata logs rotate at 1 MB with two backups; task events are persisted
separately. Raw upstream errors and Hermes logs are not forwarded to the UI.

The key has since been migrated to current-user Windows Credential Manager with
read-back verification, and its plaintext `.env` entry removed. A key pasted into
chat should still be rotated locally. Conversation text remains plaintext local
SQLite; history export/deletion UI remains unimplemented.

## Files and ownership

- Root manifests: `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`,
  `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`.
- `services/broker/src/immortility_broker/`: config, validated contracts, SQLite store,
  policy/inference guard, Hermes adapter, FastAPI endpoints and private parent handshake.
- `services/broker/tests/`: lifecycle/security/contracts/provider failure tests.
- `packages/contracts/schemas/task-request.schema.json`: admission contract;
  generated TS status union derives from the existing normative task schema.
- `apps/desktop/`: strict typed React client, native streaming transport, orb CSS,
  UI tests, lint config; `src-tauri/` contains the supervisor, Job Object, typed IPC,
  tray, window/placement controls, capabilities, config, icon and Cargo lockfile.
- `scripts/`: diagnostics, dependency setup, native dev environment, launch/check,
  generated contracts/icon, secret-boundary check and opt-in Hermes smoke tests.
- `.github/workflows/windows.yml`, `infra/security/DEPENDENCIES.md`: CI/review notes.
- Updated README/ADRs and `docs/research/EVOLUTION_DIRECTION.md`: handoff plus the
  analysis of all additional self-learning design notes.

No Git repository was present in the supplied directory, so no commit or PR was
created. The source files and lockfiles are the reviewable deliverable.

## Exact launch commands

Already built on this machine:

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
& '.\apps\desktop\src-tauri\target\debug\immortility-desktop.exe'
```

Development and offline tests:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-command.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

`install-command.ps1` puts `immortility` on the user PATH. With no flag it selects the
high-performance GPU on AC power and the power-saving GPU on battery.
`-performance`, `-balanced`, `-battery`, and `-headless` select the other modes.
`-gpu` is the same as `-performance`. The preference is written only for this
app's executable.

Run the test command in another terminal or after closing dev mode. See README
for clean dependency setup, native builds and explicitly invoked real/offline
Hermes smoke tests. The developer executable depends on this checkout, its `.venv`
and the reviewed Hermes install. It is not a portable or signed installer.

## Remaining work and next milestone

Close P1 with independent drag/tray/dual-monitor/DPI verification, a 10-minute idle
CPU/GPU/RAM benchmark, active native cancellation/reconnect matrix and Windows 10
testing. The <2% CPU / <250 MB UI and startup/stop latency targets are **not yet
measured or claimed achieved**. Remove remaining shipping blockers, add OS secret
storage and package reproducibility before calling it production-ready.

Then P2 is local push-to-talk and interruptible local speech, with visible capture
indicators and no cloud audio by default. P3–P8 OS/browser/files, durable memory,
Cursor/Grok integrations, documents/media, scheduling, avatar and command center
remain unimplemented. The Evolution Engine is analyzed design only: tracing and
independent verifiers come before Experience Graph retrieval, skill promotion and
learned routing. No self-learning improvement or benchmark gain is claimed.
