# 14 — Architectural decision records, assumptions and open risks

## ADR-001: Local-first Windows app
Decision: Tauri 2 hybrid desktop shell, not a website masquerading as a companion. Why: window stacking, tray, OS access and low idle overhead. Tradeoff: Rust + MSVC toolchain.

## ADR-002: Hermes, not new agent loop
Decision: official Hermes programmatic protocol. Why: existing memory/skills/MCP/orchestration. Risk: feature/version shifts. Mitigation: version detection, compatible adapter and pinned tested release.

## ADR-003: Modular monolith, on-demand workers
Decision: one broker process in early stages plus named adapters; isolate resource-heavy and dangerous tools into separate workers when activated. Avoid speculative always-running microservices.

## ADR-004: Free-only inference by default
Decision: Gemini eligible free + Groq free + OpenRouter :free, strict free-price preflight. Consequence: outages and quota exhaustion produce visible unavailable status, not paid fallback.

## ADR-005: Cursor specialist
Decision: Cursor CLI executes coding in scoped Git worktrees; verify diff and tests. Tradeoff: consumes subscription usage; not API for arbitrary brain tasks.

## ADR-006: Grok Bot conditional integration
Decision: no claim of remote delegation until supported trigger/API confirmed. Shared MCP bridge can exchange task/result metadata if the bot supports and authenticates it; cloud is separate trust domain.

## ADR-007: Private data is local by default
Decision: screen/audio/docs withheld from cloud until consent and provider policy accepted; avoid storing raw screenshot blobs permanently.

## ADR-008: Rendering should never be the logic
Decision: orb/avatar/3D are client presentations of one task state; CSS fallback and accessible 2D control path required.

## Open questions to resolve during implementation
- Which Hermes programmatic protocol is most stable with the chosen release (full TUI gateway vs HTTP run API)?
- Which Gemini model IDs are *actually* free for this account on the day of setup?
- Whether OpenRouter's key $0 credit limit admits free requests, and how its 402 errors behave.
- Which Grok Bot triggers/webhooks are officially supported at the time of integration?
- Which Windows audio capture/TTS engine has acceptable quality on 8 GB VRAM and 16 GB RAM?
- Which specific local image/video model weights permit intended usage and meet VRAM constraints?
- Which PDF library licenses allow planned distribution mode without extra obligations?

## Risk register
R1 paid-model leakage (critical); R2 prompt injection causes tool misuse (critical); R3 key exposure in webview/logs (critical); R4 Windows process/origin authentication (high); R5 OS/UI automation brittleness (high); R6 cloud free quotas (high); R7 GPU contention (medium); R8 3D distraction/perf (medium); R9 vendor API drift (high).

## ADR-009: Reviewed stdio gateway for P1

Implementation selects the documented TUI gateway, launched with the installed
Hermes v0.21.1 checkout at local revision `04b88a4c`. No AIAgent internal imports,
runtime fork, gateway HTTP exposure or second reasoning loop. Every task starts
an owned process and isolated temporary HERMES_HOME, with successful prior turns
seeded via `session.create.messages`; broker SQLite owns durable chat history.
Provider credentials, user rules, auth pools, plugins, MCP and hooks are not inherited.

This release interprets an empty configured tool list as a default in one path.
Use explicit `HERMES_TUI_TOOLSETS=bot_room` (the reviewed empty built-in toolset),
disable all catalog toolsets in isolated config as defense in depth, and require
the built `session.info` inventory to be empty before `prompt.submit`. Never trust
the lazy create response's initially empty inventory. Fail closed on any tool,
approval, protocol mismatch or unexpected tool-call output. Windows stop kills the
owned process tree; the native supervisor adds a kill-on-close Job Object.

## ADR-010: Credentials stay in an inference guard

Hermes receives only a private loopback inference credential. A separate broker
endpoint validates every model request, strips non-allowlisted options, rejects
tools/multimodal content, caps output, checks live prices and forces only the free
router. The native shell retains the random per-launch broker credential and
exposes only enumerated IPC operations plus an SSE-to-Tauri-channel bridge. No
HTTP endpoint URL, broker token, inference credential or provider key reaches the
webview. The CSP permits IPC and disallows direct webview HTTP access. Compatibility
is checked at broker startup, so health requests do not spawn Git from a Windows
threadpool on every heartbeat; this was the observed connection stall.

The adapter uses Hermes' supported custom OpenAI-compatible provider setting.
There is no separate provider-side agent loop. At most two provider calls are
admitted per task (including Hermes' credential probe/retry), with no paid fallback.
Model errors expose safe codes, not raw upstream response bodies. Gemini/Groq
remain disabled until account-level free status can be established reliably.
Current-user Windows Credential Manager is now implemented. Ignored `.env` remains
a development fallback; verified migration writes the vault before removing the
plaintext entry. Neither store has a secret-returning frontend operation.

## ADR-011: Local speech around the existing Hermes engine

P2 uses faster-whisper 1.2.1 with its bundled Silero ONNX VAD for local STT,
Piper 1.8.0 for local speech and sounddevice 0.5.6 for raw device I/O. STT/TTS
provider protocols isolate engine choices. Heavy imports and inference run in
on-demand keyless subprocesses, with fixed JSON operations, timeouts and process-tree
cancellation. This bounds idle model memory but adds measurable cold-start latency.
No continuous microphone capture, wake-word loop or cloud audio route is enabled.

The typed voice FSM allows only declared transitions. PTT requires literal boolean
consent in both broker admission and the worker. Thirty-second capture limits and
a forty-second broker watchdog bound recording. Ephemeral marked WAV directories
are removed on completion, cancellation and next-start recovery. Releasing PTT
before the process starts still sends Stop. Playback uses a bounded three-chunk
queue, fifty-millisecond output writes, RMS animation and explicit completion drain.

Transcription without cloud-text consent returns to the composer for review.
Consented text enters the same authenticated task endpoint and Hermes gateway as
typed input; it inherits session history, free-only routing and tool denial.
Response length is a trusted Hermes personality setting, never a new agent loop.

## ADR-012: Metadata traces without learning claims

`execution-trace.schema.json` v1 defines task/attempt identity, runtime/route,
state timestamps, duration, outcome/failure code, disabled tool status, artifact
references and verification evidence. `GET /v1/tasks/{id}/trace` derives it from
committed local events; no migration or second task log is necessary. Prompts,
assistant text, raw audio, screenshots and credentials are excluded. The attempt
identifier refers to the single broker/Hermes attempt; provider probes are not
represented as independent agent attempts. The free router label is the configured
route, not a claim about a provider's undisclosed underlying model.

Empty verification evidence means no independent verifier ran. Stream completion
is transport evidence only. This groundwork implements no self-learning, model
training, skill promotion or autonomous behavior changes.

## ADR-011: Cloned speech is a local Qwen3-TTS worker

Decision: keep Piper as the default voice and add an opt-in friend-voice clone
with `Qwen/Qwen3-TTS-12Hz-0.6B-Base` revision `5d83992436eae1d760afd27aff78a71d676296fc`
(Apache-2.0). The model runs in `.venv-tts`, not the Hermes environment, and is
loaded once per desktop session. Reference audio and `friend_voice.pt` stay under
`%LOCALAPPDATA%\Immortility\voice`. The profile is a CPU tensor dict loaded with
`weights_only=True` plus JSON metadata. Speech is sentence-queued from the
user-facing assistant text only. CUDA BF16 and PyTorch SDPA are required; there
is no silent CPU fallback. FlashAttention is not required.
