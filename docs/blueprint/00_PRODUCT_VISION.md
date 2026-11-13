# 00 — Product vision and finish line

## Identity
**Immortility** is a single-user Windows-first local desktop AI companion. It is presented as a compact holographic orb pinned near the right screen edge, expandable into a conversational humanoid avatar and an optional 3D command center. All visual surfaces share one task state and one permissions system.

## End-state promise
Ask naturally by voice or text. Immortility should interpret the request, clarify only when an action is impossible or ambiguous, plan when needed, call approved tools, use available models, delegate specialized work, monitor progress, verify each action, remember durable non-sensitive context and explain outcomes in concise spoken and written form. It should accept interruption, cancellation and correction at any time.

## Supported surfaces
- **Desktop companion:** compact always-on-top orb, click-to-expand, click-through only when explicitly configured, tray menu, hotkey, microphone status, task status and global pause.
- **Humanoid conversation:** an animated 3D avatar on demand with expressive lip sync / gesture states where practical; never at cost of usability or blocking screen access.
- **Command center:** 3D agent/task visualization backed by real events; fallback to accessible 2D list/timeline; no fake activity.
- **Remote/mobile (later):** separate authenticated, revocable client; never expose local agent services publicly by default.

## Capability coverage — long-term target
1. Voice: push-to-talk, low-latency STT/TTS, interruption, VAD, wake-word opt-in, languages and audio device selection.
2. Reasoning: planning, question answering, code reasoning, grounded web research, transparent uncertainty and citations.
3. OS: enumerate active windows, screen context on demand, permitted UIA/Win32 controls, mouse/keyboard actions with preview/approval.
4. Files: search, read, extract, classify, organize, rename, create, diff, version and recover files inside approved roots.
5. Coding: inspect workspace, plan, delegate Cursor CLI, track diff, run tests, summarize, stage changes; require review for destructive/deploy.
6. Internet: public search, navigate sites, extract structured data, connect explicitly authorized accounts; no automatic CAPTCHA bypass or access-control circumvention.
7. Documents: parse and author PDF, DOCX, PPTX, XLSX; preserve structure and validate rendered output.
8. Visuals: analyze images, generate/edit/upscale images, create diagrams, create/edit/transcribe/summarize videos.
9. Audio: TTS, transcription, subtitles, sound editing, conversion, optional music tools where lawful.
10. 3D/media: optional GLB scene generation/editing via Blender/Three.js tool adapters, post-MVP.
11. Memory: short-term context, project-specific summaries, editable durable preferences, evidence provenance, deletion and export.
12. Multi-agent: specialists for code/research/browser/desktop/documents/media; budgeted concurrency, cancellation and verification.
13. Automation: scheduled jobs, reminders, workflow graphs, task continuation, idempotency and retry with human approval boundaries.
14. Privacy/operations: audit trail, local encrypted credentials, cost dashboard, error recovery, explicit no-paid policy.

## Example success journeys
- “Look at this error” → consented active-window capture → vision/UIA → suggest fix → approved Cursor worktree → tests → show diff.
- “Summarize these PDFs and make a 12-slide deck” → approved folder → Docling parse → sources → PPTX generation → render check → final output.
- “Generate five sci-fi images and a short video” → plan/quality settings → ComfyUI or alternative compatible engine → FFmpeg encode → local preview and output.
- “Find academic papers” → browser/search → source validation → annotated notes → memory only after consent.
- “Organize Downloads” → *dry-run preview first* → approval → atomic moves → undo log.

## Explicit non-goals
- Literally knowing everything, bypassing website access controls, or guaranteeing no hallucinations.
- Unrestricted admin rights, silent continuous screen recording, password harvesting, covert monitoring, or remote access without authorization.
- Unlimited cloud inference: free tiers are rate-limited and model availability changes.
- Replacing each external vendor's legal/technical access rules (Cursor and Grok Bot remain subject to their official interfaces).
- Building a new agent runtime, OS automation framework, diffusion engine or media encoder from scratch.

## Product quality bar
A command is complete only after the user sees a correct outcome, a verification result, and an accurate report of any partial failures. The assistant must never say it completed an action based only on model text.
