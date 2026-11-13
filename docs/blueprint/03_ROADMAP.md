# 03 — Detailed phased roadmap

**Rule: finish vertical slice and verify acceptance tests before starting the next stage.** Phases below define incremental integration, not promises that every module must be live immediately. `P0` and `P1` are the initial coding-agent assignment.

2026-11-13 consolidation: execute the current P0 rebaseline, then close P1/P2
acceptance. [CONSOLIDATION.md](../architecture/CONSOLIDATION.md) governs ownership
and supersedes older framework choices. No existing user memory/jobs/controllers
are replaced automatically; no later phase is enabled by installing a repository.

## P0 — Foundations, policy and deterministic tests
- Verify Windows toolchain and official API surfaces; decide Hermes HTTP vs TUI gateway. Document exact commands.
- Create pnpm workspace + Python workspace, local broker, typed shared JSON schemas and consistent event IDs.
- Implement strongly typed configuration with environment validation, strict local-only binding, redacted logging and error envelopes.
- Implement policy engine with default deny, zero-paid guard and mock providers; unit tests for all deny paths.
- Add scripts: doctor.ps1, bootstrap-dev.ps1; tests, linters, GitHub Actions smoke check.
**Exit:** fresh clone can run diagnostics and offline tests; no secret in Git; zero-paid policy unit tests pass.

## P1 — Working desktop orb and text conversation (MVP)
- Implement Tauri 2 transparent always-on-top floating companion (draggable; pinned right; tray; always on top toggled; no click interception outside widget; reduced-motion option).
- Render 2D/CSS orb first with states: idle, listening, thinking, speaking, executing, awaiting approval, error, disconnected. 3D enhancements later.
- Expanded 2D chat panel with streaming text, stop action, keyboard navigation, session list and connectivity indicator.
- Broker task/session/events endpoints with broker-issued per-launch auth and origin guard; persistence in SQLite.
- Hermes official programmatic integration with version detection, real streaming text response, cancellation and disconnect handling. Integration can be optional if runtime absent; mock-only is never considered completion.
- Wire one genuine free provider after verifying account model eligibility; fallback to simulated provider only with obvious MOCK label.
- UI shows per-request status and costs/free-tier restrictions; no filesystem or screen capture yet.
**Exit:** user starts Immortility locally, chats with a real Hermes-backed free model, sees status, stop works, restart preserves safe session history. Windows manual smoke test recorded.

## P2 — Voice, audio and personality
- Add push-to-talk STT (Handy app integration only if supported; else faster-whisper direct integration), microphone permission and visible capture indicator.
- Local Piper speech output, voice selection, interruptible playback and ducking, VAD, optional wake-word OFF by default.
- Configurable personality: concise natural responses, no invented emotions/experience, clarify ambiguity, speak status only when useful.
- Test recording denied, device unavailable, acoustic noise, cancellation, no network.
**Exit:** voice request -> text/agent -> spoken response, explicit mute + kill switch.

## P3 — Screen, files, browser and OS awareness
- Implement on-demand active-window screenshot (consent each task or expiring scoped grant), UIA tree, title/focus metadata.
- Scoped filesystem roots: path normalization, symlink/reparse point checks, dry-run/diff for writes, atomic moves, undo manifest.
- Benchmark OpenMausBot's Windows/browser capabilities first behind broker policy. Add Browser Use only for a specific measured gap, with isolated profile/domain scope; no payment/login auto-submission.
- Optional UFO² Windows automation behind separate worker and explicit approvals.
**Exit:** look at a screenshot, identify UI safely, summarize a permitted folder, preview and approve a reversible file action; audit shows everything.

## P4 — Durable memory and retrieval
- SQLite FTS, per-project namespaces, source provenance, retention TTL and opt-in durable memories.
- Retrieval policy separates transient prompt context from long-term facts; guard against poisoning by tool content.
- Memory inspect/edit/export/delete in dashboard; measure retrieval quality and stale facts.
**Exit:** learns user-approved project context across restarts and forgets on request.

## P5 — Coding agent and OpenMausBot specialist teams
- Official Cursor CLI adapter: availability check/login, safe `--print --output-format stream-json`, worktree checkout, timeout/cancel, diff + tests, human review before merge.
- Use OpenMausBot's verified MCP control plane for bounded specialist teams. Dedicated pairing/model/workspace, idempotent sends, parent/child ownership and interruption must pass broker-policy and zero-cost checks. Native privileged tools stay off unless every action crosses the broker.
- Introduce skill registry manifest/permissions, tool discovery and strict capability routing.
**Exit:** approved coding task produces real diff + test report; one genuine broker-mediated specialist workflow supports cancellation/recovery with verified artifacts. The older Grok Bot bridge is superseded; unrelated historical configuration stays intact.

## P6 — Multimodal content and artifacts
- Document ingestion (Docling/PyMuPDF/MarkItDown), page citations, output DOCX/PPTX/PDF/XLSX with format validation and rendered-layout QA.
- Image understanding via eligible vision provider with consented uploads; local image generation/edit through ComfyUI on demand.
- Video/audio editing (FFmpeg), subtitles, frame inspection; then experimental generative video after VRAM measurement.
- Never export images of slides as fake editable PPTX; verify artifact existence, format and visual output.
**Exit:** PDF -> cited summary -> editable slides -> rendered previews; image and video workflows each separately tested.

## P7 — Multi-agent orchestration and scheduling
- Skill/capability-based delegation using Hermes existing agent abilities; DAG tasks, concurrency caps, cancellation propagation, timeout/budget enforcement.
- Preserve task persistence/idempotency and choose one authoritative scheduler after auditing Hermes/OpenMausBot native features. Build only missing broker reliability/approval controls; do not introduce a competing scheduler or memory store without evidence.
- Grounded agent activity in expanded command center; respect free-tier model limits.
**Exit:** multi-stage job survives restart or fails cleanly; no duplicate side effects; quotas tested.

## P8 — Hybrid humanoid + command center; production hardening
- Custom 3D humanoid, animations, lip-sync, expressions, skinning and avatar asset license review; fallback CSS orb while inactive.
- 3D agent graph and workflows share live backend events; accessible 2D controls remain first class.
- Implement updater, sign builds when certificates available, reversible migrations, uninstall data choices, crash recovery, security audit, GPU/CPU profiles.
- Windows installer reproducibility, portable mode decision, telemetry opt-in, SBOM and vulnerability scanning.
**Exit:** real packaged desktop build stable over long-running soak, clean installation on a separate Windows account, clear recovery instructions.

## Release levels
- **Developer preview:** P0-P1, local only, all dangerous tools disabled.
- **Personal alpha:** P2-P4 with opt-in permissions.
- **Personal beta:** P5-P7 after end-to-end verification.
- **Production-ready target:** P8 including security, accessibility and recoverability gates.
