# 12 — GitHub-first integration registry

These are **candidates/approved directions**, not proof that an adapter is built or that a specific model license is approved. Revalidate docs, commit/release, license, Windows compatibility and security before integration.

| Capability | Upstream | Integration / notes |
|---|---|---|
| Agent runtime | https://github.com/NousResearch/hermes-agent | Primary runtime; official gateway, API and MCP support. Native Windows docs available. |
| Desktop | https://github.com/tauri-apps/tauri | Tauri 2 window shell, secure capabilities. |
| UI | https://github.com/facebook/react | Reactive chat, orb and dashboards. |
| 3D | https://github.com/pmndrs/react-three-fiber | Optional expanded 3D; load on demand. |
| Coding | https://docs.cursor.com/en/cli/reference/output-format | Official Cursor CLI, do not automate private editor protocols. |
| Windows OS agent | https://github.com/microsoft/UFO | UFO² optional; separate adapter, Windows UIA + COM. |
| Browser agent | https://github.com/browser-use/browser-use | Local browser mode; do not accidentally use paid cloud. |
| Dictation | https://github.com/cjpais/Handy | App for dictation; no presumption of public streaming API. |
| STT | https://github.com/SYSTRAN/faster-whisper | Local transcription integration. |
| Wake word | https://github.com/dscripka/openWakeWord | On-demand hotword; default disabled. |
| TTS | https://github.com/rhasspy/piper | Evaluate maintenance / licensed voices before shipping. |
| Local inference | https://github.com/ollama/ollama | Optional local models. |
| Image / video generation | https://github.com/Comfy-Org/ComfyUI | Workflow execution over local HTTP/WS API. |
| Video editing | https://github.com/FFmpeg/FFmpeg | Frame decode, mux, encode, trim, subtitles. |
| Document parsing | https://github.com/docling-project/docling | PDF, DOCX, PPTX etc; resource-bounded worker. |
| Document conversion | https://github.com/microsoft/markitdown | Lightweight text extraction; not perfect layout preservation. |
| PDF | https://github.com/pymupdf/PyMuPDF | Read/render/edit; review license implications if distributing. |
| Word | https://github.com/python-openxml/python-docx | Editable DOCX. |
| PowerPoint | https://github.com/scanny/python-pptx | Editable PPTX. |
| Spreadsheet | https://github.com/openpyxl/openpyxl | Spreadsheet read/write. |
| Office conversion | https://github.com/LibreOffice/core | Headless conversion; optional, use isolated runtime. |
| Optional model proxy | https://github.com/BerriAI/litellm | Not included by default; add only to solve a concrete gap. |

## Upstream docs verified 2026-11-13
- Hermes protocols: https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration
- Hermes Windows: https://hermes-agent.nousresearch.com/docs/user-guide/windows-native
- Cursor stream-JSON: https://docs.cursor.com/en/cli/reference/output-format
- Tauri permissions: https://v2.tauri.app/security/capabilities/
- Browser Use modes: https://github.com/browser-use/browser-use
- UFO² quickstart: https://github.com/microsoft/UFO/blob/main/documents/docs/getting_started/quick_start_ufo2.md
- ComfyUI server routes: https://github.com/Comfy-Org/docs/blob/main/development/comfyui-server/comms_routes.mdx
- Docling formats: https://docling-project.github.io/docling/usage/supported_formats/
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Groq limits: https://console.groq.com/docs/rate-limits
- OpenRouter free model notes: https://openrouter.ai/collections/free-models

## Licensing gate
Do not assume all components are permissively licensed. Evaluate GPL/LGPL/AGPL/commercial and model-weight licenses for each shipping strategy. Linking to a repository does not confer redistribution rights. Especially audit PDF engines, video codecs, voice packs, generated-image models and avatar assets.
