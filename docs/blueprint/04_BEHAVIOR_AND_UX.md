# 04 — Behavior, personality, UX and interaction specification

## Hybrid appearance state machine
`hidden -> idle_orb -> listening -> thinking -> executing -> speaking -> idle_orb`, with `awaiting_approval`, `error` and `disconnected` overlay states. `expanded_chat` and `humanoid_view` are presentation modes sharing the same agent state. The avatar must never imply capabilities that aren't connected.

## Compact orb
- Pin near right side but user-draggable; snap-to-edge; remember location per monitor/DPI; survive display disconnect.
- Width target 72–120 physical-equivalent dp when collapsed, user adjustable; low-opacity inactive, high contrast on hover; never sit invisibly above unrelated click targets.
- Right click opens tray menu: expand, mute, pause, see permissions, quit. Hotkeys configurable and conflict-aware.
- Idle: subtle breathing glow capped low FPS; Listening: explicit mic ring; Thinking: pulse; Acting: agent indicator; Speaking: waveform; Approval: visible warning dot; Offline: honest icon.
- User can set no animation, reduced motion and no always-on-top.

## Expanded surfaces
- Chat timeline includes messages, sources, tool calls, subtasks, exact status, permissions, token/cost budget and recoverable errors.
- Human avatar view animates eyes, posture and mouth from actual speech events, not fake transcripts; avoid uncanny low-quality facial animation.
- 3D command center shows real agent instances, task dependencies, timestamps and confidence/verification signals; a 2D task list always available.
- Use skeleton / calm animations while waiting, never deceptive progress percentages.

## Voice-first contract
- Push-to-talk defaults ON, wake word defaults OFF. No hidden ambient transcription.
- Status cues: microphone activated, model processing, actionable response, interruption and completion.
- Allow barge-in during TTS, stop speech instantly on explicit stop, cancellable agent task separately.
- Recognize pronouns like “this window” only with foreground-window context; request permission to capture before using visuals.
- Avoid sending speech recordings to cloud without explicit permission; local transcription first.

## Conversational demeanor
- Warm, concise, competent, non-flattering. Natural conversational pacing; no cinematic roleplay when taking consequential actions.
- Clarify dangerous/ambiguous intent once, not for ordinary safe analysis.
- Summarize actions, what was verified, what is uncertain, what remains to do.
- For requests requiring unavailable tool or exceeded quota, state blocker and offer approved local alternative; never invent success.
- Learn preferences from explicit feedback; allow review and deletion of memories.

## Activity patterns
- “What are you doing?” -> honest list of active tasks, tools, budget, ETA only if measured, stop button.
- “Stop” -> immediately stop TTS; request cancellation of active task; notify if non-reversible action already committed.
- “Undo” -> undo manifest for reversible actions and review; Git worktree rollback after verification.
- “Look at screen” -> temporary indicator, explicit screenshot permission, show a screenshot preview if desired, no always-on capture.
- “Keep working” -> only allowed scheduled/long-running operation while application process is active; persistent tasks resume with user consent on relaunch.
