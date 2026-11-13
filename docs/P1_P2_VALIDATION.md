# P1 hardening and P2 local voice — 2026-11-13

This report covers the work from this chat: root relocation, Credential Manager,
Whisper/Piper voice, shared Hermes orchestration, orb states and execution traces.
The user explicitly excluded newer Qwen voice-cloning additions from this validation.
Those files were preserved. This is an integrated developer preview, not completed
P2 acceptance or a production release.

## What is implemented

| Capability | Status | Evidence / limits |
|---|---|---|
| Flattened project root | Verified | 35 top-level entries moved; 158 first-party hashes checked; hidden files included; outer documents preserved; old wrapper removed |
| Root-relative development | Verified | uv entry points and pnpm links regenerated; Python/UI/native builds run from `C:\Users\reyan\OneDrive\Desktop\IMMORTILITY` |
| Current-user Credential Manager | Verified | Real dummy write/read/delete test; actual OpenRouter key migrated with read-back before atomic `.env` removal; no secret returned to webview |
| Local English STT | Verified on synthetic fixture | faster-whisper 1.2.1, base model, CPU int8, Silero VAD; one word error in the 16-word sample |
| Local Piper TTS | Verified | piper-tts 1.8.0; LJ and Joe output streams opened, wrote PCM and completed; Stop reaped the speaking process |
| PTT capture and live indicator | Integrated; physical capture unverified | Literal consent required at HTTP and worker boundaries; held pointer/Space controls; max 30 seconds; explicit meter and capture status |
| Devices and languages | Partly verified | Native device selector populated real Windows endpoints; unavailable output rejected; English fixture tested; other languages/mic unplug remain unverified |
| Voice state machine | Verified deterministically | Explicit IDLE/LISTENING/TRANSCRIBING/THINKING/SPEAKING/CANCELLED/ERROR transitions; cancellation and early PTT release covered |
| One voice/chat conversation | Verified deterministically | Voice text enters the same task admission and Hermes adapter; typed-to-voice follow-up history and persistence tested |
| Real Hermes free inference | Verified | v0.21.1, revision `04b88a4c`; repeated fixed-prompt live test succeeded with two deltas after vault migration |
| Orb / future avatar contract | Integrated | Lightweight CSS states, RMS-driven listening/speaking scale, reduced-motion behavior; versioned avatar state JSON Schema; no 3D scene |
| Execution traces | Verified | Stable attempt ID, route, transitions, duration, outcome, failure code, disabled tools and explicit empty verification evidence; schema rejects extra content and local artifact paths |
| Self-learning / autonomous tool use | Planned; not implemented | Traces are instrumentation only. No independent outcome verifier, training or skill promotion ran |

The standalone speech smoke generates a public synthetic test WAV, never records
ambient audio and makes no cloud calls. Ordinary orchestration tests explicitly
use fake audio/Hermes adapters. They establish lifecycle/security behavior, not
physical microphone quality. The real Hermes offline smoke mocks only inference.
No fake provider is silently enabled in the desktop application.

## Executed checks and failures

- **51 scoped Python tests passed**, including the original 30, strict boolean
  consent denial, worker denial before sounddevice import, state transitions,
  record/transcribe/playback cancellation, silent input, sanitized device errors,
  temporary audio cleanup, restart cleanup, shared-session follow-up and active
  voice-thinking Stop. Current-user Credential Manager dummy tests passed.
- Five Vitest tests passed. Generated contract freshness and blueprint/schema
  parsing passed. Strict mypy passed on the current imported source graph.
- Before the later Qwen changes, the complete `scripts/check.ps1`, Ruff, TypeScript,
  ESLint, Prettier and Vite build passed. Two native security tests and Clippy with
  warnings denied passed. Tauri debug `--no-bundle` builds succeeded at the new root.
- The later shared-checkout check passed TypeScript and ESLint, but **Prettier
  reported `VoiceControls.tsx` and `style.css`** after newer edits. Those additions
  are outside this validation scope; this report does not claim the current whole
  checkout has a passing full check.
- Real Hermes + live free router: succeeded, two deltas; fixed public test prompt,
  empty test history, vault key never printed. Real Hermes + offline cancellation:
  cancelled, subprocess reaped, zero guarded provider calls. An earlier adversarial
  fake provider was blocked from issuing a terminal call to real Hermes.
- Python and pnpm advisory scans reported zero known vulnerabilities for this
  chat's resolved dependency graphs. This does not cover the separate Qwen venv,
  RustSec, future advisories, or a complete transitive license/SBOM audit.
- One upstream AnyIO/Starlette TestClient deprecation warning remains.
- Real fixture testing initially failed because Whisper vocabulary was absent;
  model preparation/readiness now includes it. PyAV 19 also broke faster-whisper's
  decoder API; explicitly pinning compatible PyAV 18.0.0 fixed the real test.

Native computer-use checks observed saved chat history, Hermes connected status,
Credential Manager as the key source, actual audio-device choices, speaking state
after Read aloud, and cancelled state after Stop voice. No microphone checkbox or
OS privacy permission was enabled by automation. Drag attempts did not demonstrate
movement; no successful drag/snap or tray test is claimed.

## Measured performance

These are observations on this Windows laptop, not general guarantees. Later
tests ran alongside development activity and show substantial workload variation.

| Metric | First completed local speech run | Repeated run |
|---|---:|---:|
| Synthetic English fixture length | 5.10 s | 5.29 s |
| CPU STT, including worker/model startup | 2.02 s | 5.17 s |
| Word error rate, ignoring punctuation/case | 6.25% | 6.25% |
| Piper first-audio readiness, including cold startup | 4.83 s | 9.16 s |
| Speaking worker Stop and reap | 213 ms | 285 ms |
| Joe complete short playback | 5.79 s | 6.78 s |

The 2.5-second STT goal is not consistently met. Cold TTS startup is too slow for
natural turn-taking. The speech test measures device opening/writes and process
cleanup; it does not measure acoustic quality or an electrical loopback timestamp.
Fixture files and latest metrics are `tests/fixtures/voice-english.wav` and ignored
`data/benchmarks/voice-local.json`. A single synthetic sample is not a robust STT
accuracy/noise benchmark.

The completed **600-second P1 compact-idle** baseline had 70 samples after warmup:
UI group working set averaged **391.2 MB**, maximum **399.9 MB**; private memory
averaged **156.0 MB**. GPU engine-sum utilization averaged **0.907%**. Engine sum is
a sum of per-engine Windows counters, not a percentage of overall GPU capacity.
Broker working set was recorded separately. The UI working-set target of <250 MB
was missed. All CPU samples reported zero in that first script; that counter result
has not been accepted as evidence of zero CPU use.

The benchmark now uses validated CIM kernel/user CPU counters and refuses missing
timings. The repeat P2 idle run **failed because the native app exited before
completion**, so no completed P2 CPU/idle baseline is claimed. Do not confuse the
old P1 JSON with a new successful P2 run. Repeat on an uninterrupted instance before
promotion. Original data remains in ignored `data/benchmarks/p1-baseline.json`.

## Security and privacy

- Provider credentials remain backend-only. The actual migrated key was checked
  absent from frontend source/bundle, docs and config. A key previously pasted into
  chat should be rotated locally; migration does not revoke it.
- OpenRouter's `openrouter/free` route is the only enabled inference path, with
  live zero-price verification and no paid fallback. Gemini/Groq remain blocked
  pending verified account eligibility. No new subscription or privileged audio/
  CUDA installation was introduced.
- Hermes built-in tools, plugins, hooks and MCP stay disabled. Voice never grants
  terminal, file, screen or browser access. Fixed native operations cannot name an
  arbitrary HTTP endpoint; provider and broker secrets never enter the webview.
- No cloud audio endpoint exists. Mic capture starts only for an explicit PTT
  request and is bounded. Without text consent, transcription stays for local
  review. Captured WAVs are ephemeral and removed; the public fixture is retained
  intentionally for reproducible tests. Windows/process crash during capture is
  covered by marked-directory cleanup on the next start.
- Conversation text remains plaintext SQLite. Content-free traces contain no
  prompts, response text, audio, screenshots, credentials or local file paths.
- Piper is GPL-3.0-or-later. Dataset/model provenance is documented in
  `infra/security/DEPENDENCIES.md`; redistribution legal review is still required.

## Exact Windows commands

For this already configured PC:

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Or launch the existing debug build without the Vite developer server:

```powershell
Start-Process .\apps\desktop\src-tauri\target\debug\immortility-desktop.exe
```

Select LJ or Joe for this chat's verified Piper path. In Settings, refresh devices,
choose an input/output, and enable microphone consent yourself. Hold to talk,
release to transcribe. Leave cloud-text consent off to review the transcript first.
Use Read aloud for completed text; Stop voice/tray Stop/Ctrl+Shift+Escape cancel.

Dependency/model setup if needed (the existing installations are already present):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap-dev.ps1
.\.venv\Scripts\python.exe .\scripts\prepare-voice.py
```

Scoped reproduction, excluding the newer cloning tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q services/broker/tests/test_broker.py services/broker/tests/test_firewall.py services/broker/tests/test_secrets.py services/broker/tests/test_voice.py
.\.venv\Scripts\python.exe .\scripts\verify-voice.py --play
.\.venv\Scripts\python.exe .\scripts\smoke-hermes.py --offline --cancel
.\.venv\Scripts\python.exe .\scripts\smoke-hermes.py --offline --adversarial
.\.venv\Scripts\python.exe .\scripts\check-secret-isolation.py
pnpm.cmd test
powershell -NoProfile -ExecutionPolicy Bypass -Command ". .\scripts\dev-env.ps1; pnpm.cmd --filter @immortility/desktop tauri build --debug --no-bundle"
```

`verify-voice.py --play` audibly plays synthetic speech at 30% volume. Omitting
`--play` performs synthesis/transcription/device enumeration without playback.
The opt-in live `smoke-hermes.py` without `--offline` uploads only its fixed public
prompt through the guarded free route. It never uploads a fixture or microphone audio.

For the complete checkout, `scripts/check.ps1` also includes newer tests; its final
status belongs to the combined work and is outside this chat's requested scope.

## Remaining gates and next milestone

Before P2 acceptance: physical Windows mic allow/deny, PTT release and Stop during
capture, noise/no-speech fixture expansion, mic unplug/default-device changes,
GPU STT compatibility/fallback, multi-monitor and 125%/150% DPI, manual drag/snap/
pin/tray/placement, native Stop during live inference, reconnect after interruption,
and an uninterrupted 10-minute P2 idle CPU/GPU/memory run. Preserve single-instance
and Job Object shutdown behavior while doing these checks.

Next milestone: close these P1/P2 gates, reduce idle UI memory and cold speech
latency, and run a complete physical voice → Hermes → spoken reply test. Only then
begin P3 scoped screen/file awareness. P3–P8, independent verification and
self-learning remain unimplemented in this chat.
