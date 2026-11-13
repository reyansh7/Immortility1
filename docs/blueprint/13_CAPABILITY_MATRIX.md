# 13 — Complete capability matrix (target, not current implementation)

Legend: `P#` earliest planned phase, `Approval` if side effects/privacy sensitive, `Optional` if high compute / restricted.

| Domain | Feature | Phase | Policy |
|---|---|---|---|
| Desktop | Floating orb, always-on-top, tray, drag, snap, multi-monitor | P1 | Local |
| Desktop | Expand chat, task panel, status, offline banner | P1 | Local |
| Desktop | Humanoid 3D expression/lip-sync; 3D command center | P8 | Optional GPU |
| Conversation | Streaming chat with Hermes and real free models | P1 | Free-only |
| Conversation | Tools, memory, personalization, project context | P4 | Consent |
| Voice | Push-to-talk + local transcription and TTS | P2 | Mic permission |
| Voice | Wake word, VAD, interruption, multilingual profiles | P2+ | Opt-in |
| OS | Foreground window data, screen vision, UIA controls | P3 | Scoped permission |
| OS | Keyboard/mouse and app launch/control | P3 | Approval |
| Files | Read, search, extract, organize, rename and undo | P3 | Allowlisted roots |
| Browser | Search, browse, extract, form preview | P3 | Domain policy |
| Browser | Submit/send/download/upload, account-based actions | P3+ | Fresh approval |
| Coding | Cursor CLI task delegation and tests, Git diff review | P5 | Approved worktree |
| Research | Source evaluation, dedupe, citations, summaries | P3+ | Verify sources |
| Memory | Persistent summaries, retrieval and deletion | P4 | Inspect/edit/delete |
| Tools | MCP registry and per-tool risk manifests | P5 | Default deny |
| Grok Bot | Shared task/MCP bridge where documented | P5 | Conditional |
| Docs | PDF/DOCX/PPTX/XLSX ingest, OCR, citations | P6 | File consent |
| Docs | DOCX/PPTX/XLSX/PDF generation, editing, QA | P6 | Output validation |
| Images | Vision, diagram understanding, generation/editing/upscale | P6 | Privacy, compute |
| Video | Summarize, frame search, video/voice editing, subtitles | P6 | Privacy, compute |
| Video | Text/image-to-video local quantized models | P6+ | Optional/experimental |
| Audio | Sound conversion, captioning, voices | P2/P6 | Privacy/license |
| Automation | Multi-agent planning, scheduling, task DAGs, resumes | P7 | Budget + approval |
| Operations | Zero-spend guard, audit, cancellation, recovery | P0+ | Mandatory |
| Personal services | Mail/calendar/drives/cloud apps through supported MCP | P7+ | Explicit OAuth |
| Remote | Mobile/remote authenticated command center | P8+ | Separate security review |
| 3D content | Blender/GLB tools and scene analysis | P8+ | Optional |

**Do-everything means extensible legitimate capabilities, not unrestricted access or guaranteed success.** Unsupported work must be labeled honestly and presented with an integration path.
