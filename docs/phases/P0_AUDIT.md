# P0 rebaseline and architecture audit — 2026-11-13

Phase status: **INTEGRATION VERIFIED** for the rebaseline, source audit, regression
checks and same-machine clean-source reproduction. **FAILED** performance/security
acceptance gates and **BLOCKED** optional integrations remain explicitly listed.
This does not declare P1/P2 or the full product complete.

## Plan, preservation and scope

1. Preserve current source and inspect the actual app, broker, contracts, workers,
   tests, locks and setup/check scripts.
2. Audit installed Hermes and OpenMausBot availability against pinned official
   source/docs; preserve existing subsystem ownership.
3. Establish current tests, source/dependency integrity and idle resource baseline.
4. Fix demonstrated formatting, worker lifecycle/privacy, runtime pin and Stop
   defects; add meaningful negative and real-process tests.
5. Rebuild and exercise safe native P1 controls. Keep later integrations inactive.

No Git repository existed at entry. A local `audit/p0-consolidation` branch was
initialized without staging, committing, pushing or deleting user files. A selected
118-file source/configuration snapshot and hashes were preserved in ignored
`.cache/p0-rebaseline/original`; credentials, user data, environments, model caches
and recordings were excluded. The working folder remains the original root.
Unchanged external memory/jobs and the installed legacy Grok application were not
read, migrated or reconfigured. No user recordings/profiles were deleted or re-cloned.

Primary risks: unmediated native agent tools; competing stores/controllers;
experimental Qwen dependencies; blocking GPU cancellation; opaque audio logs;
working-set/startup measurement validity; physical microphone and Windows manual
acceptance. The master consolidation rules govern these decisions.

## Actual inventory and ownership

The architecture is Tauri/React → enumerated Rust IPC → authenticated loopback
FastAPI broker → isolated Hermes stdio gateway → broker inference guard → verified
OpenRouter free route. Broker SQLite owns sessions/tasks/events. Existing Whisper/
Piper workers and the isolated optional Qwen runtime handle audio. No application
memory service, scheduler, browser service, computer controller, MCP manager or
specialist team was activated. Empty future folders are not implementations.

[CONSOLIDATION.md](../architecture/CONSOLIDATION.md) contains the current diagram,
component ownership, security boundaries, reuse decisions and adoption contract.
[REPOSITORY_MATRIX.md](../integrations/REPOSITORY_MATRIX.md) audits 13 repositories.
[OPENMAUSBOT.md](../integrations/OPENMAUSBOT.md) contains the concrete migration plan.

Installed Hermes: **0.21.1**, full revision
`04b88a4c0a7fe05ebe3bf053a103a39fe6638f11`, tracked source clean. The audit found
upstream release metadata 0.23.1 but did not upgrade. Native memory, cron, skills,
delegation, browser/computer, ACP and MCP code already exists; it is not permission
to activate it. Immortility still disables all 59 toolsets, memory, hooks, plugins,
MCP and lazy installs and checks the realized tool inventory before prompting.

OpenMausBot was not found in the checked installation locations/PATH. Audited
0.1.155 source requires Node >=24; the host remains Node 22.13.1. A network-disabled
source MCP catalogue test passed, but no installed team, browser or CUA workflow
ran. No pairing/account/model configuration was performed.

## Code changes

- Corrected the combined checkout's demonstrated Python/React formatting failures;
  `scripts/check.ps1` now also checks isolated TTS source with Ruff.
- Hermes startup verification now checks the exact full reviewed commit, declared
  package version and modified tracked source, rather than trusting an eight-digit
  HEAD alone. Version/dirty-source mismatch tests use disposable repositories.
- Serialized Qwen startup and requests so simultaneous first requests cannot spawn
  duplicate models. Timeout and cancellation reap the owned process; the previous
  queued JSON cancel could not interrupt synchronous GPU work.
- Worker cleanup uses only broker-owned expected WAV paths. Malicious reported
  paths cannot delete unrelated files. Real harmless subprocess tests verify
  timeout, Stop, restart, serialization, path rejection and process cleanup.
- Keyless environment allowlisting and fixed error codes replace inherited
  miscellaneous environment variables and opaque persistent audio exception logs.
  Old logs were left intact; no new `engine.log` is created by the client.
- Speech failure becomes a visible voice error while preserving text chat.
- `EXPERIMENTAL_QWEN_TTS=false` by default; the existing private clone is preserved.
  Explicit opt-in is required while advisory/native gates are unresolved. The
  installer refuses accidental execution without `-AllowExperimental` and pins
  installed Torch/torchaudio versions; no packages were upgraded during the audit.
- Global Stop attempts Hermes cancellation even when audio cleanup fails and
  reports a safe incomplete-audio error instead of silently leaving the agent active.
- Native edge snapping waits for mouse release rather than treating a held pause
  as completed dragging. Fixed Up/Down keyboard move controls use the existing own-
  window IPC boundary and persist the compact anchor; no generic desktop controller
  or arbitrary coordinate API was introduced.
- Added reproducible read-only runtime/source-protocol audits, a clean-source
  reproduction harness, and an owned native idle benchmark with validated CPU
  counters, explicit incomplete reports and descendant-cleanup evidence.

## Current verification evidence

| Check | Actual result |
|---|---|
| Initial current-checkout Python suite | 61 passed; full check stopped on three Python formatting failures |
| Final `scripts/check.ps1` | **78 Python tests**, **5 Vitest tests**, Ruff for broker/TTS, strict broker mypy, generated contracts, schemas, TypeScript, ESLint, Prettier and frontend build passed |
| `scripts/reproduce-check.ps1` | Fresh credential-free source copy (`run-20261113-191401`); frozen offline uv/pnpm installation; **78 Python + 5 frontend tests** and all checks/build passed with Hermes deliberately unavailable |
| Native `cargo test --locked` | Three tests passed, including held-drag snap regression |
| Native Clippy | Passed with warnings denied at the drag-release checkpoint; subsequent fixed keyboard controls also built/tested |
| Native Tauri debug build | Passed at the actual project root; updated executable launched |
| Real Hermes + adversarial fake provider | Tool request blocked, zero tool execution; provider is explicitly mocked |
| Real Hermes + offline cancellation | Cancelled, real process reaped, zero provider calls |
| Windows Credential Manager | Existing real dummy roundtrip tests passed; actual provider-key isolation check passed |
| OpenMausBot source MCP | Three initialize/catalogue/unknown-method/EOF probes passed; no HTTP, dispatch, provider call or credentials |
| Current physical/native observations | Keyboard move changed the compact position, collapse restored the anchor, restart restored it again; second launch left one instance and opened chat; global open shortcut and historical chat restoration worked |

The clean-source harness excludes credentials, models, profiles and recordings and
does not install Qwen. It proves same-machine source/dependency reproducibility,
not a clean Windows account/installer, an empty offline package cache, a Git clone
with a committed history, or a portable native binary. The first manual copy
omitted `.env.example` and the JavaScript lint config; the reusable harness includes
both and passed. One upstream AnyIO/Starlette deprecation warning remains.

A status-only real TTS worker test runs under the lightweight broker interpreter,
loads no model and confirms keyless environment/log suppression. It is not a real
Qwen synthesis benchmark. Real blocking/echo subprocesses separately verify
bounded lifecycle behavior without GPU/model access.

Native mouse-drag automation did not demonstrate successful movement; the release
logic is unit verified, but physical dragging is still a manual acceptance gate.
No multi-monitor, changed-DPI, tray, sleep/resume or active live-cloud native Stop
success is claimed by this audit.

## Physical voice handoff and selected voice

The user ran the requested voice test and reported hearing a different voice from
the desired friend clone. Metadata confirmed an intact clone profile, recorded
speaker consent and available reference source. The selected voice was **ljspeech**,
with automatic typed-response speech off and the current clone-consent setting off.
The two most recent inspected task records were text-source tasks (succeeded and
cancelled); these do not independently establish the full microphone → Hermes
voice-source path. No prompt/response/recording was printed during that inspection.

Computer Use was stopped by the user's physical Escape key. UI control stopped;
the voice selection and experimental flag were not changed. Clone identity,
physical mic/noise/device behavior and a complete Qwen native workflow remain
unverified. A scoped explicit experimental clone test requires addressing or
acknowledging the advisory gate; do not rebuild or upload the preserved profile.

## Security and dependency findings

Broker and npm scans: **zero known advisories** in the scanned graphs on this date.
The isolated Qwen environment: **52 advisory entries across four packages**:

| Installed package | Advisory entries | Reported fixed-version situation |
|---|---:|---|
| Accelerate 1.12.0 | 1 | No fixed version listed in the scan |
| Pillow 12.3.0 | 42 | Scan lists 13.0.0 |
| setuptools 78.1.0 | 3 | Scan includes 78.1.1, 83.0.0, 84.1.0, depending on advisory |
| Transformers 4.57.3 | 6 | Fixes listed in 5.x, conflicting with Qwen 0.1.1's exact pin |

Counts are advisory entries, not an independently deduplicated exploit count. No
exploitability claim or silent incompatible upgrade was made. The native clone
runtime stays off by default; its original environment/profile remain. Summary:
`infra/security/qwen-advisory-summary.json`. Full private-environment package audit
data is ignored under `data/audits`, containing package metadata, not voice data.

Follow-up requested by the user: [QWEN_REMEDIATION.md](../security/QWEN_REMEDIATION.md)
lists all 52 entries, severity and conditional reachability, incompatible patch
constraints, an isolated setuptools update, seven CPU-only regressions and the
remaining **51 direct candidate findings**. A supplemental upstream-base Torch
scan found one additional advisory not covered by the exact CUDA-wheel scan.
Original packages and 13 private voice assets remain unchanged; playback stays off.

Piper GPL/model distribution review, OpenMausBot enterprise/third-party notices,
RustSec, full SBOM/license audit and signing/installer gates remain open. Upstream
account/subscription/paid cloud examples were not activated. No provider key,
pairing token, private voice or user memory/job data was uploaded by this audit.

## Performance and remaining gates

See [BASELINES.md](../performance/BASELINES.md). The completed 600-second compact
idle run passed measurement/lifecycle validity, but missed the <250 MB UI working-
set target. Cold/warm interactive startup, warm speech, VRAM under real clone load,
real team dispatch, browser actions and 3D FPS are not inferred from protocol tests.

Priority backlog:

1. Resolve the cloned-voice experimental/advisory gate with a compatible reviewed
   dependency path or explicitly scoped developer opt-in; verify the preserved
   friend profile in the actual native workflow, without re-cloning/uploading it.
2. Complete physical PTT → STT → Hermes → Piper/Qwen and interruption/restart tests.
3. Complete mouse drag/snap, tray/pin, monitor removal and DPI/sleep/resume testing.
4. Profile UI working set and cold speech startup; require controlled before/after
   measurements. Do not trim working sets artificially to claim lower memory use.
5. Only after P1/P2 gates, prepare a concrete approved OpenMausBot installation,
   dedicated restricted team and broker-mediated per-action execution proof.
6. Preserve existing memory/schedules/controllers until a measured alternative
   demonstrably improves required behavior. Browser Use remains a conditional gap
   filler, not a default additional framework.

## Commands

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\reproduce-check.ps1
.\.venv\Scripts\python.exe .\scripts\audit-runtime.py
.\.venv\Scripts\python.exe .\scripts\probe-openmausbot.py
.\.venv\Scripts\python.exe .\scripts\benchmark-desktop.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

The source-protocol probe needs the exact inspected public source in the ignored
audit cache and verifies tracked hashes; it does not install OpenMausBot. Close the
normal app before the owned benchmark. Cached reproduction needs approved packages
already populated by bootstrap. Real Hermes/live-provider smokes stay separate and
opt-in; no cloud call is hidden inside the ordinary test suite.
