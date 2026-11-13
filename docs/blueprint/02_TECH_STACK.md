# 02 — TECH STACK (authoritative target)

| Layer | Choice | Rationale / deployment |
|---|---|---|
| OS / packaging | Windows 10/11, **Tauri 2**, Rust shell | Lightweight desktop, tray, overlay, safe native window APIs |
| UI | React, TypeScript strict, Vite, Tailwind CSS | Mature typed desktop UI |
| 3D UI | three.js + React Three Fiber + Drei; GSAP sparingly | Hybrid orb + humanoid + interactive agent visualization |
| Accessibility | ARIA, keyboard navigation, reduced-motion support | 2D alternatives to every 3D operation |
| Backend broker | Python 3.11+ validated, FastAPI, Pydantic v2, Uvicorn, httpx | Tool adapters, auth, policy, streaming, local orchestrator glue |
| Agent runtime | **Nous Research Hermes Agent** | Existing agent lifecycle, memory, skills, MCP, subagents; official programmatic gateway |
| Model routing | Hermes provider integration first; custom zero-spend preflight policy | Avoid two competing orchestrators; LiteLLM only after a proved need |
| Cloud providers | Gemini API, GroqCloud, OpenRouter :free; NVIDIA key stored only | User already has keys; free tier varies, must verify. NVIDIA is not a chat route |
| Local inference | Ollama optional with Qwen-class small models | Offline fallback; do not preload on 8 GB VRAM |
| Coding execution | Cursor Agent CLI in sandboxed Git worktree | Use existing paid Cursor entitlement when supported |
| Cloud collaborator | Grok Bot optional shared MCP/task bridge | Not assumed to expose direct remote job API |
| Browser | Browser Use local library + Chromium CDP | Explicit approved browsing; local browser to avoid hosted bill |
| Windows OS | Windows UI Automation + pywin32/Win32; UFO² optional specialist | Focused API actions first; GUI fallback only when needed |
| Speech-to-text | Handy initially for dictation; faster-whisper integration later | Handy is an app, not a guaranteed stream API |
| Wake word / VAD | openWakeWord; Silero VAD or WebRTC VAD | Optional wake word, interrupt handling, privacy |
| Text-to-speech | Piper for the default local voices; Qwen3-TTS 12Hz 0.6B Base for an opt-in cloned voice | Fully local. The clone runs in its own environment on CUDA BF16 with SDPA. No paid voice API. |
| Documents input | Docling, MarkItDown, PyMuPDF | Structured PDF/DOCX/PPTX extraction |
| Documents output | python-docx, python-pptx, openpyxl, ReportLab | Editable DOCX/PPTX/XLSX and PDFs; render validation |
| Rendering | LibreOffice headless for supported office conversions | Optional dependency; isolation and fidelity checks |
| Image generation/edit | ComfyUI API + VRAM-appropriate workflows | On-demand GPU worker; per-workflow licensing check |
| Video understanding | FFmpeg frame sampling + vision API | Avoid uploading full video unnecessarily |
| Video generation | ComfyUI-compatible low-VRAM workflow, optional later | Experimental locally, not Phase 1 |
| Video editing | FFmpeg, ffprobe | Deterministic and free |
| Storage | SQLite WAL; optional SQLite FTS5 | Reliable local state without service costs |
| Retrieval | SQLite FTS first, local embeddings optional; vector DB only when needed | Cost and dependency control |
| Secrets | Windows Credential Manager / DPAPI via Rust backend | Keys never delivered to webview |
| Processes | Rust supervisor or Python subprocess with job objects | Stop/cancel/restart workers, limits and lifetime |
| Telemetry | OpenTelemetry-compatible traces, structlog, optional Prometheus | Local opt-in observability, redacted logs |
| Contracts | JSON Schema + Pydantic / TypeScript types | Durable typed event, task, tool manifests |
| Test | pytest, Vitest, React Testing Library, Playwright, cargo test | Unit, contract, integration, Windows E2E |
| Lint/security | ruff, pyright/mypy, ESLint, Prettier, cargo clippy, pip-audit, npm audit | Enforced CI quality |
| Package management | pnpm, uv or pip-tools, Cargo lockfiles | Pinned reproducible builds |
| CI | GitHub Actions Windows runner plus optional Linux tests | Installation, formatting, unit/E2E, build artifact checks |

## No extra subscription policy
- `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`: allowed only for **account-confirmed free eligible models**.
- `NVIDIA_API_KEY`: stored locally. It is not sent to Hermes and is not a chat route until a model ID and a live $0 price are verified.
- `XAI_API_KEY`: **not required** for Grok Bot and is disabled to avoid unexpected pay-as-you-go spend.
- Cursor CLI login uses existing subscription; availability and quota must be checked.
- Self-hosted ComfyUI/Docling/FFmpeg/Piper have no required cloud API key; compute and third-party content terms still apply.
- No paid TTS/video/image subscriptions required; if unsupported by local hardware, explain limitation and don't fake success.

## API lifecycle
Before coding each adapter, verify official upstream version, license, API, environment requirements and transitive dependency risk. Pin to a tested release/commit; do not copy-paste unreviewed install scripts into automation.

## Primary references
Hermes: https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration
Tauri v2: https://v2.tauri.app/security/capabilities/
Cursor CLI: https://docs.cursor.com/en/cli/reference/output-format
Groq limits: https://console.groq.com/docs/rate-limits
OpenRouter free: https://openrouter.ai/collections/free-models
Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
