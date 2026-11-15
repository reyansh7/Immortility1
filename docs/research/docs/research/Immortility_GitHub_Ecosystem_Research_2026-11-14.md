# Immortility: GitHub Capability & Integration Research

**Research snapshot:** 14 November 2026  
**Scope:** Windows personal AI with Hermes Agent, Python security/task broker, holographic Tauri/React/3D UI, optional specialist workers, local-first voice and memory, and strict cloud-token budgets.  
**Inventory:** 138 distinct GitHub repository candidates across 13 categories.

> **Evidence standard:** “Docs reviewed” indicates relevant publicly available GitHub documentation was checked while researching; it **does not** mean the code was installed, tested, audited or proven secure. “Candidate” means discovery-level shortlist only: its URL, recent maintenance, license, runtime and integration still require verification. Repository descriptions and licenses can change. **Do not bulk-install this inventory.**

## Executive decision

Keep **Hermes** as the only primary planner. Keep Immortility's **Python broker** as the one permission/task/cancellation boundary. Treat **OpenMausBot** as an optional specialist-runtime experiment, not a native Hermes dependency until interface tests pass. Select one memory owner, one active browser controller per task, one computer-control controller per task, one scheduler, and one trace collector. Run GPU-heavy modules only on demand.

### Recommended first wave (in order)

1. Audit Hermes built-in skills, memory, subagents, scheduler and plugin catalog. Install no duplicate frameworks.
2. Add **Serena** for narrow code retrieval/editing, then compare real prompt-token counts against baseline.
3. Prototype **Cua Driver** for Windows UIA in an interactive user session, broker-proxied and approval-controlled.
4. Use **Crawl4AI/trafilatura** for local web cleaning, **Playwright** for complex workflows; experiment with **Obscura** as a small-footprint backend with automatic fallback.
5. Consolidate speech: **Handy/whisper.cpp** or **sherpa-onnx**, **Silero VAD**, and one TTS engine such as **Kokoro**.
6. Implement a **single memory solution**: Hermes native first, GBrain only if measured retrieval and correction quality improve; SQLite/sqlite-vec optional.
7. Enable per-provider, per-task cloud-token ceilings; route simple work to a small local model or deterministic function first.
8. Use official Hermes plugin **Langfuse** *only if* cost audit needs outweigh telemetry-infrastructure overhead; a SQLite per-call ledger may be enough.

## Approved high-level target topology

```text
Tauri Windows desktop / React / React Three Fiber
   ↕ event stream and broker API
Python broker (AUTHORITY: approvals, allowlists, cancellation, secrets, budgets, audit)
   ↕
Hermes Agent (PRIMARY PLANNER, native skills and official plugins)
   ├─ model choices: cloud BYOK / local Ollama or llama.cpp
   ├─ memory owner: Hermes native OR GBrain (not both authoritative)
   ├─ code: Serena -> relevant symbols -> tests, optional coding specialist
   ├─ web: Crawl4AI/trafilatura -> Obscura OR Playwright, one session/task
   ├─ Windows: Cua Driver / UI Automation (interactive desktop, gated)
   ├─ voice: local STT, VAD, one TTS, ducking + cancellation
   └─ optional OpenMausBot specialist adapter ONLY after compatibility tests

Shared event log (SQLite WAL), bounded retries, explicit feature flags, strict egress.
```

## Viral GitHub recommendations: detailed assessment

| Source | Verdict | Important qualification |
|---|---|---|
| GBrain | Evaluate | Local memory is possible; concurrent memory writes and Hermes provider compatibility need measurement. |
| Skills Hub | Already native | Search official / GitHub skill sources from Hermes; skills load progressively. |
| Agent Reach | Evaluate | Social services may need cookies/account auth; be careful about platform policies and secrets. |
| Open Design | Optional | Apache-2.0 local-first design app with Hermes CLI support; not a memory or agent framework. |
| Hermes Studio | Reference/optional | Admin/control-center capabilities overlap with Immortility's custom interface. |
| Obscura | Evaluate | MCP and CDP support; rendering not yet fully Chromium compatible; retain Playwright fallback. |
| Open Generative AI | Optional | MuAPI-backed models need keys AND credits; local media generation needs sizeable model downloads/GPU. |
| Cua Driver | High-priority | Documented Windows+Hermes support but must run inside interactive session and must respect broker approvals. |

## Full repository inventory

**Priority meaning:** Core = architecture baseline or particularly useful; Evaluate = prototype and benchmark first; Optional = only when feature required; Defer = overlapping or disproportionate complexity. The repository priority is **not** an instruction to install it immediately.

### Agent core and Hermes (10)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Primary assistant and skills ecosystem | Keep one reasoning and tool-execution authority; audit installed Hermes features before new dependencies | Docs reviewed |
| Core | [NousResearch/hermes-official-plugins](https://github.com/NousResearch/hermes-official-plugins) | Official reviewed Hermes extensions | Install only useful plugins; check profile/version compatibility and avoid cloning the whole catalog | Docs reviewed |
| Evaluate | [OpenMausBot/OpenMausBot](https://github.com/OpenMausBot/OpenMausBot) | Specialist crews and integrations | No documented native Hermes driver or general Windows host control guarantee; prove interop behind broker first | Docs reviewed |
| Evaluate | [JPeetz/Hermes-Studio](https://github.com/JPeetz/Hermes-Studio) | Hermes multi-agent admin studio | Reference for dashboard UX or temporary admin surface, not second permanent control center | Docs reviewed |
| Evaluate | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Checkpointed graph workflows | Only if native Hermes workflows cannot meet durable task-state needs; avoid a second agent brain | Candidate |
| Optional | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | Typed agent workflows | Use selected structured worker flows, not universal orchestration replacement | Candidate |
| Optional | [huggingface/smolagents](https://github.com/huggingface/smolagents) | Small agent examples and tool patterns | Research reference rather than production runtime | Candidate |
| Defer | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | Multi-agent crew framework | Overlaps Hermes and OpenMausBot; significant extra control surface | Candidate |
| Optional | [openinterpreter/openinterpreter](https://github.com/openinterpreter/openinterpreter) | Coding-agent harness for low-cost models | New project direction is coding-agent-focused; evaluate only as a specialist executor rather than core | Docs reviewed |
| Defer | [microsoft/agent-framework](https://github.com/microsoft/agent-framework) | Enterprise multi-agent coordination | Likely unnecessary for local desktop assistant; compare only after basic architecture is stable | Candidate |

### Memory and retrieval (12)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Evaluate | [garrytan/gbrain](https://github.com/garrytan/gbrain) | Facts, provenance and correctable long-term memory | Benchmark versus Hermes memory; local PGLite writer concurrency requires care | Docs reviewed |
| Evaluate | [veltri-23/hermes-gbrain-memory](https://github.com/veltri-23/hermes-gbrain-memory) | GBrain Hermes adapter | Check native memory-provider support/version before promising drop-in integration | Docs reviewed |
| Optional | [BrightCollage/hermes-gbrain-memory-plugin](https://github.com/BrightCollage/hermes-gbrain-memory-plugin) | Alternative GBrain MCP bridge | Compare with preceding adapter; do not install both | Docs reviewed |
| Evaluate | [asg017/sqlite-vec](https://github.com/asg017/sqlite-vec) | SQLite-backed vector similarity search | Excellent light single-process search path; pre-v1 API can change | Docs reviewed |
| Evaluate | [UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers) | Local text embeddings | Run small CPU encoder; avoid cloud embed calls and unnecessarily large models | Candidate |
| Evaluate | [qdrant/fastembed](https://github.com/qdrant/fastembed) | Lightweight embeddings and reranking | Check on-device size and batch throughput | Candidate |
| Optional | [mem0ai/mem0](https://github.com/mem0ai/mem0) | Agentic semantic long-term memory | Alternative to GBrain or Hermes native memory, not additional default memory owner | Docs reviewed |
| Optional | [getzep/graphiti](https://github.com/getzep/graphiti) | Temporal knowledge graph | Neo4j/FalkorDB and embeddings add infrastructure; use only if real temporal-graph queries justify it | Docs reviewed |
| Defer | [qdrant/qdrant](https://github.com/qdrant/qdrant) | Dedicated vector database | Usually unnecessary for a single-user Windows assistant with modest memory corpus | Docs reviewed |
| Defer | [chroma-core/chroma](https://github.com/chroma-core/chroma) | Embedding database | Choose only if sqlite-vec is insufficient; avoid two indexes for same facts | Candidate |
| Optional | [screenpipe/screenpipe](https://github.com/screenpipe/screenpipe) | Local screen/audio activity recall | Very sensitive continuous capture, source-available license, plan limits and large storage; opt-in only | Docs reviewed |
| Defer | [letta-ai/letta-code](https://github.com/letta-ai/letta-code) | Memory-centric coding agent | Full alternate agent runtime, not a drop-in Hermes memory store | Docs reviewed |

### Web research and browsing (12)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [microsoft/playwright](https://github.com/microsoft/playwright) | Reliable browser interaction and tests | Use for complex websites, auth workflows, and fallback when lightweight engines fail | Docs reviewed |
| Evaluate | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | MCP exposure for Playwright browser | Use one browser controller per task through broker | Candidate |
| Evaluate | [h4ckf0r0day/obscura](https://github.com/h4ckf0r0day/obscura) | Rust browser with MCP/CDP | Benchmark speed/compatibility; own documentation notes incomplete Chromium parity | Docs reviewed |
| Evaluate | [SGavrl/hermes-plugin-obscura](https://github.com/SGavrl/hermes-plugin-obscura) | Hermes Obscura integration | Test with target Hermes version; feature flag and fallback to Playwright | Docs reviewed |
| Evaluate | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | Web pages to structured markdown | Extract only relevant page sections before cloud reasoning | Docs reviewed |
| Evaluate | [adbar/trafilatura](https://github.com/adbar/trafilatura) | Local clean text extraction | Very cheap preprocessing for news, articles and documentation | Candidate |
| Evaluate | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | Social, video and platform discovery | Platform cookies, login and restrictions require scoped access | Docs reviewed |
| Optional | [thanhtantran/agent-reach-hermes](https://github.com/thanhtantran/agent-reach-hermes) | Hermes skill wrapper for Agent Reach | Use only if native tool integration is insufficient | Docs reviewed |
| Optional | [browser-use/browser-use](https://github.com/browser-use/browser-use) | LLM-driven browser automation | Useful for visual web tasks but can burn tokens; use deterministic browser actions first | Docs reviewed |
| Optional | [mendableai/firecrawl](https://github.com/mendableai/firecrawl) | Web crawling and extraction | Self-host dependencies and optional services, deploy only if Crawl4AI insufficient | Candidate |
| Optional | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | Extract public video metadata/media | Observe copyrights, site policies and authentication boundaries | Candidate |
| Optional | [scrapy/scrapy](https://github.com/scrapy/scrapy) | Batch web crawls | Only for dedicated larger crawling jobs | Candidate |

### Windows computer and OS (10)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [trycua/cua](https://github.com/trycua/cua) | Windows UI control, screenshots, accessibility and MCP | Run in interactive Windows session; broker approval for every sensitive action | Docs reviewed |
| Evaluate | [pywinauto/pywinauto](https://github.com/pywinauto/pywinauto) | Deterministic Windows Win32/UIA automation | Prefer accessible controls over coordinate clicking | Docs reviewed |
| Evaluate | [microsoft/OmniParser](https://github.com/microsoft/OmniParser) | Screenshot UI perception | Check model-license terms; only necessary for interfaces lacking accessibility APIs | Candidate |
| Optional | [microsoft/UFO](https://github.com/microsoft/UFO) | Windows UI agent research | Reference capabilities; may duplicate Cua and require extra model calls | Candidate |
| Optional | [asweigart/pyautogui](https://github.com/asweigart/pyautogui) | Mouse/keyboard automation fallback | Coordinate-based actions fragile; always verify target window and user approval | Candidate |
| Optional | [AutoHotkey/AutoHotkey](https://github.com/AutoHotkey/AutoHotkey) | Windows native keyboard macros | Simple deterministic triggers better than model calls | Candidate |
| Optional | [tauri-apps/global-hotkey](https://github.com/tauri-apps/global-hotkey) | Cross-platform global keyboard shortcut Rust crate | Tauri official plugin is normally easier; use native crate only if necessary | Docs reviewed |
| Defer | [bytedance/UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop) | Vision-driven GUI agent | Archived by owner Nov 9 2026; benchmark research only, not new long-term dependency | Docs reviewed |
| Optional | [microsoft/PowerToys](https://github.com/microsoft/PowerToys) | OS tooling, shortcuts and UX reference | Reuse behavior not complete application | Candidate |
| Optional | [giampaolo/psutil](https://github.com/giampaolo/psutil) | Local CPU/GPU process system observations | Expose narrow read-only telemetry to dashboard and agent | Candidate |

### Speech, voice and sound (13)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [cjpais/handy](https://github.com/cjpais/handy) | Local speech-to-text dictation | Reuse as Windows STT UX or inspect integration; avoid duplicate always-on capture | Docs reviewed |
| Evaluate | [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | Offline STT/TTS/VAD/keyword detection | Promising single speech stack; benchmark accuracy and the chosen voice | Docs reviewed |
| Evaluate | [snakers4/silero-vad](https://github.com/snakers4/silero-vad) | Voice activity detection | Stop silence from triggering repeated cloud calls | Docs reviewed |
| Evaluate | [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Local Whisper ASR | CPU-friendly baseline, GPU options depend on build | Docs reviewed |
| Evaluate | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Fast Python ASR | Windows CUDA/cuDNN version setup must match | Docs reviewed |
| Evaluate | [hexgrad/kokoro](https://github.com/hexgrad/kokoro) | Local TTS | Benchmark metallic post-processing separately; verify voice/model licensing | Docs reviewed |
| Optional | [dscripka/openWakeWord](https://github.com/dscripka/openWakeWord) | Wake-word listening | Bundled model license may differ from source; avoid constant microphone if unneeded | Docs reviewed |
| Optional | [myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice) | Timbre conversion and voice transfer | Potential cinematic character voices with consent; test speed/quality | Docs reviewed |
| Optional | [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) | Lightweight local TTS | Current project GPL-3.0 and voice model licenses vary; review distribution obligations | Docs reviewed |
| Optional | [Pipecat-AI/pipecat](https://github.com/Pipecat-AI/pipecat) | Real-time conversational voice pipelines | Heavy if only simple push-to-talk speech is needed | Candidate |
| Optional | [livekit/agents](https://github.com/livekit/agents) | Streaming and interruptible voice sessions | Best for distributed/networked real-time voice, not needed for purely local desktop | Candidate |
| Optional | [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) | Audio/video encoding and DSP | Use for metallic effects, clipping, pitch and audio output preprocessing | Candidate |
| Defer | [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) | Expressive TTS research | Upstream states it was retired August 2026; archive only | Docs reviewed |

### Models, routing and inference (8)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [ollama/ollama](https://github.com/ollama/ollama) | Easy local model runtime | Cheap local classification, summarization and private tasks when quality suffices | Docs reviewed |
| Evaluate | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | Efficient GGUF inference engine | Alternative to Ollama, benchmark before deploying second server | Candidate |
| Evaluate | [Portkey-AI/gateway](https://github.com/Portkey-AI/gateway) | Multi-provider proxy/routing and guardrails | Use only if Hermes native providers/routing do not suffice; separate hosted features | Docs reviewed |
| Evaluate | [microsoft/onnxruntime](https://github.com/microsoft/onnxruntime) | Optimized local inference runtime | Useful for speech, embedding and compact classifiers | Candidate |
| Optional | [BerriAI/litellm](https://github.com/BerriAI/litellm) | Broad provider gateway | Security-sensitive credential store; review advisories and package provenance, don't blindly pip install | Docs reviewed |
| Optional | [vllm-project/vllm](https://github.com/vllm-project/vllm) | GPU server inference | Great for larger Linux GPU servers, poor first fit on Windows laptop | Candidate |
| Optional | [sgl-project/sglang](https://github.com/sgl-project/sglang) | High-throughput serving | Same server-oriented caution as vLLM | Candidate |
| Defer | [nomic-ai/gpt4all](https://github.com/nomic-ai/gpt4all) | Local chat app | Redundant as Immortility already has its own UI and inference integration | Candidate |

### Coding and repository intelligence (12)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [oraios/serena](https://github.com/oraios/serena) | Language-server-powered symbolic code navigation and edits | Reduce token-heavy whole-file dumps, include only matching symbols | Docs reviewed |
| Evaluate | [yamadashy/repomix](https://github.com/yamadashy/repomix) | Pack selected repo context | Use scope filters and token reports; full repo prompts are expensive | Docs reviewed |
| Evaluate | [coderamp-labs/gitingest](https://github.com/coderamp-labs/gitingest) | Convert GitHub repos to text summaries | Useful first-pass research input; redact secrets and trim output | Docs reviewed |
| Evaluate | [Aider-AI/aider](https://github.com/Aider-AI/aider) | Git-aware coding agent | Consider as isolated specialist worker only, not simultaneous core brain | Candidate |
| Evaluate | [anomalyco/opencode](https://github.com/anomalyco/opencode) | Open-source coding agent/CLI | Evaluate as specialized executor with broker and spend limits | Candidate |
| Optional | [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | Software engineering agent environment | Heavy runtime, commonly uses sandboxes/containers; only if benchmark wins | Candidate |
| Optional | [cline/cline](https://github.com/cline/cline) | VS Code coding assistant | Useful user-facing coding reference, redundant to Hermes coding harness | Candidate |
| Optional | [block/goose](https://github.com/block/goose) | Local extensible coding assistant | Agent-runtime alternative for architecture comparisons | Candidate |
| Optional | [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) | Issue-to-patch agent research | May improve benchmark strategies, not necessary as live component | Candidate |
| Optional | [microsoft/markitdown](https://github.com/microsoft/markitdown) | Convert Office, PDF, HTML and more to text | Cheap deterministic document preparation; security-check input file types | Docs reviewed |
| Optional | [pymupdf/PyMuPDF](https://github.com/pymupdf/PyMuPDF) | Fast local PDF text and rendering | Add only if Hermes lacks suitable extraction path | Candidate |
| Optional | [ocrmypdf/OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | Searchable scanned PDFs | Enable only when scanned content requires OCR | Candidate |

### MCP, plugins and integrations (8)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | Build typed Python MCP adapters | Small, permission-aware wrappers for special OS and API tools | Candidate |
| Evaluate | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | Official MCP examples and integrations | Source of patterns, not a reason to install all servers | Candidate |
| Evaluate | [jlowin/fastmcp](https://github.com/jlowin/fastmcp) | Rapid MCP service implementation | Use only if SDK ergonomics justify another dependency | Candidate |
| Core | [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) | Test MCP tools, schemas, resources and OAuth | Use its CLI and TUI modes in CI; audit remote endpoints before access | Docs reviewed |
| Optional | [activepieces/activepieces](https://github.com/activepieces/activepieces) | Self-hostable integration/workflow catalog | MIT community core; enterprise features commercial; likely heavier than needed | Docs reviewed |
| Optional | [n8n-io/n8n](https://github.com/n8n-io/n8n) | Workflow automation builder | Source-available license restrictions; separate always-on stack | Candidate |
| Optional | [HomeAssistant/core](https://github.com/HomeAssistant/core) | Smart-home platform integration | Use Hermes official plugin if already have Home Assistant | Candidate |
| Optional | [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | Curated MCP server discovery | Index only; vet every third-party server before granting credentials | Candidate |

### 3D UI and frontend (19)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [tauri-apps/tauri](https://github.com/tauri-apps/tauri) | Lightweight Rust desktop shell | Keep the existing Windows UI rather than rewriting into Electron | Docs reviewed |
| Core | [pmndrs/react-three-fiber](https://github.com/pmndrs/react-three-fiber) | React Three.js canvas | Use for immersive holographic orb/avatar visualization | Docs reviewed |
| Core | [pmndrs/drei](https://github.com/pmndrs/drei) | 3D controls, environment, helpers | Prefer mature helpers instead of custom shader/scene glue | Docs reviewed |
| Core | [pmndrs/zustand](https://github.com/pmndrs/zustand) | Lightweight UI state management | Centralize live agent status with minimal React rerendering | Docs reviewed |
| Evaluate | [xyflow/xyflow](https://github.com/xyflow/xyflow) | Editable node graph for agents/workflows | Best foundation for multi-agent visual orchestration view | Docs reviewed |
| Evaluate | [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | Accessible high-quality UI primitives | Use for status panels, tool approval dialogs and settings | Docs reviewed |
| Evaluate | [pmndrs/react-postprocessing](https://github.com/pmndrs/react-postprocessing) | 3D bloom, outlines, shader effects | Use carefully; expensive post-processing should adapt to frame budget | Docs reviewed |
| Evaluate | [motiondivision/motion](https://github.com/motiondivision/motion) | Interface microanimations | Use tasteful deterministic UI transitions | Candidate |
| Evaluate | [pixiv/three-vrm](https://github.com/pixiv/three-vrm) | Anime/VRM avatar loading and animation | Only if character asset uses VRM rather than GLB rig | Candidate |
| Optional | [pmndrs/react-spring](https://github.com/pmndrs/react-spring) | Physics-based UI/3D animation | Great animation option; avoid stacking competing animation libraries | Docs reviewed |
| Evaluate | [assistant-ui/assistant-ui](https://github.com/assistant-ui/assistant-ui) | AI chat primitives, streaming, retries and tool-approval UI | Use inside existing React Tauri frontend via a custom backend runtime, not a new Next app | Docs reviewed |
| Evaluate | [tauri-apps/plugins-workspace](https://github.com/tauri-apps/plugins-workspace) | Official Tauri system integrations including shortcuts and notifications | Use capabilities/permissions to restrict plugins; inspect exact version compatibility | Docs reviewed |
| Optional | [pmndrs/leva](https://github.com/pmndrs/leva) | 3D controls/debug panel | Dev mode only; never ship raw dev toggles to end users | Candidate |
| Optional | [radix-ui/primitives](https://github.com/radix-ui/primitives) | Accessible control primitives | Potential base for approval and command palettes | Candidate |
| Optional | [lucide-icons/lucide](https://github.com/lucide-icons/lucide) | Icon system | Tiny visual affordances with consistent styling | Candidate |
| Optional | [recharts/recharts](https://github.com/recharts/recharts) | Cost/usage dashboard charts | Mount charts only when their tab is visible | Candidate |
| Optional | [tanstack/query](https://github.com/tanstack/query) | React query and caching | Keep session data cached, avoid polling too often | Candidate |
| Optional | [tanstack/virtual](https://github.com/tanstack/virtual) | Virtualized conversation and log streams | Render long agent traces without excessive DOM nodes | Candidate |
| Optional | [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid) | Workflow and architecture diagrams | Read-only flow view or documentation export | Candidate |

### Design and multimodal creation (11)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Optional | [nexu-io/open-design](https://github.com/nexu-io/open-design) | Local-first multi-agent design workspace | Works with Hermes CLI and BYOK; separate creative workflow only | Docs reviewed |
| Optional | [Anil-matcha/Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) | Local and keyed cloud media generation UI | MuAPI credit requirement for cloud models; local GPU weights can be multi-GB | Docs reviewed |
| Optional | [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | Local image and video workflow graphs | Start only when requested, GPU load conflicts with local LLM | Candidate |
| Optional | [nexu-io/html-video](https://github.com/nexu-io/html-video) | Local HTML-to-video rendering driven by agents | Promising for Immortility promo/exports; optional soundtrack API costs | Docs reviewed |
| Optional | [nexu-io/motion-anything](https://github.com/nexu-io/motion-anything) | Promptable motion recipes and export | Explore if building animated holographic assets | Docs reviewed |
| Optional | [blender/blender](https://github.com/blender/blender) | 3D asset creation | Invoke in supervised creative tasks via official Hermes Blender plugin | Candidate |
| Optional | [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe) | Face/hand/body tracking | Only if webcam gesture features wanted, with explicit camera consent | Candidate |
| Optional | [upscayl/upscayl](https://github.com/upscayl/upscayl) | Image upscaling utility | Useful asset prep outside always-on assistant runtime | Candidate |
| Optional | [danielgatis/rembg](https://github.com/danielgatis/rembg) | Local image background removal | Small utility for avatar thumbnails and UI art | Candidate |
| Optional | [xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Super-resolution for image assets | Optional, GPU intensive | Candidate |
| Optional | [KhronosGroup/glTF-Sample-Models](https://github.com/KhronosGroup/glTF-Sample-Models) | Sample 3D models | Dev visual test assets; check licenses per model | Candidate |

### Security, permissions and integrity (6)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks) | Detect accidentally committed secrets | Run before installing imported repos or publishing code | Candidate |
| Core | [google/osv-scanner](https://github.com/google/osv-scanner) | Vulnerability scan for dependencies | Gate integration on vulnerable dependency findings | Candidate |
| Evaluate | [semgrep/semgrep](https://github.com/semgrep/semgrep) | Static analysis and code scanning | Target custom broker and newly added plugin handlers | Candidate |
| Evaluate | [aquasecurity/trivy](https://github.com/aquasecurity/trivy) | Filesystem/image dependency scanner | Useful if you introduce containers or bundled binaries | Candidate |
| Evaluate | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | LLM regression and prompt-injection tests | Model + tool-approval safety benchmark for every release | Candidate |
| Optional | [restic/restic](https://github.com/restic/restic) | Encrypted backup of memory and config | Back up SQLite data and local state, never raw cloud keys | Candidate |

### Observability, testing and utilities (13)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Core | [astral-sh/uv](https://github.com/astral-sh/uv) | Fast Python environment/dependency manager | Isolate tools to avoid polluting system Python; clean caches thoughtfully | Candidate |
| Core | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) | Broker unit/integration test runner | Use cancellation, restart, tool approval and provider failover tests | Candidate |
| Evaluate | [langfuse/langfuse](https://github.com/langfuse/langfuse) | Traces and token/cost accounting | Official Hermes plugin available; full self-hosting adds services | Docs reviewed |
| Evaluate | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | LLM traces and evaluations | Alternative observability path; don't run multiple backends by default | Candidate |
| Evaluate | [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python) | Vendor-neutral traces and spans | Collect event and error metadata, scrub user content and secrets | Candidate |
| Evaluate | [agronholm/apscheduler](https://github.com/agronholm/apscheduler) | Python job scheduling | Choose only if Hermes has no satisfactory native scheduler; v4 currently prerelease | Docs reviewed |
| Evaluate | [astral-sh/ruff](https://github.com/astral-sh/ruff) | Python lint and formatting | Fast precommit quality gate | Candidate |
| Evaluate | [pre-commit/pre-commit](https://github.com/pre-commit/pre-commit) | Automated repository checks | Run secret scan and lint before commits | Candidate |
| Optional | [encode/httpx](https://github.com/encode/httpx) | Async HTTP client for API adapters | Use only through broker and with endpoint allowlists | Candidate |
| Optional | [fastapi/fastapi](https://github.com/fastapi/fastapi) | Local broker HTTP interface | Already likely present; do not add a second backend web server | Candidate |
| Optional | [samuelcolvin/watchfiles](https://github.com/samuelcolvin/watchfiles) | Fast file watcher for local skills/config | Hot reload in dev only, avoid constant production scans | Candidate |
| Optional | [Textualize/rich](https://github.com/Textualize/rich) | Developer CLI progress and logging | Keep diagnostics readable without cloud LLM tokens | Candidate |
| Optional | [rclone/rclone](https://github.com/rclone/rclone) | Optional storage sync | Use only with per-provider scoped credentials and encryption | Candidate |

### Discovery collections (4)

| Priority | Repository | What it adds | Integration note | Review |
|---|---|---|---|---|
| Optional | [awesome-selfhosted/awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) | Curated self-hosted tools index | Discovery source, never wholesale install | Candidate |
| Optional | [openai/skills](https://github.com/openai/skills) | Skill format and reusable patterns | Import selectively using Hermes skills hub review path | Candidate |
| Optional | [anthropics/skills](https://github.com/anthropics/skills) | Example skill bundles | Licenses and executable content vary across files | Candidate |
| Optional | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | Frontend engineering skills | Use selected source-audited skills; progressive disclosure | Candidate |

## Nonnegotiable adoption gates

For every proposed install or plugin: (1) exact GitHub owner/repo and release provenance; (2) current license and **model weights license** separately; (3) Windows support and Node/Python/Rust runtime compatibility; (4) permission surface, secrets and outbound endpoints; (5) idle RAM/CPU, active VRAM, cold-start delay; (6) success rate on ten realistic tasks and recovery on failure; (7) median and p95 latency; (8) model prompt/completion/tool tokens and cost; (9) cancellation and restart behavior; (10) security scan, code review, pinned release/commit and rollback path. **No dependency is admitted on GitHub stars alone.**

### Suggested acceptance thresholds (initial targets, tune against measured baseline)

- **Prompt tokens:** <= baseline for equivalent task quality; goal >= 30% less on common coding/research tasks with Serena and local preprocessing. This is a target, not a measured claim.
- **Idle performance:** heavy media models and extra browser engines consume zero active GPU time when feature is unused; prefer lazy starts.
- **Correctness:** <= 1% regression on maintained unit/E2E tests; zero unauthorized tool actions.
- **Resilience:** stable recovery after process crash and network outage; no duplicate writes on retries.
- **Human control:** confirmation before irreversible file/financial/account/network changes. A user can stop tasks and revoke tools.

## Security and cost watchlist

- **LiteLLM:** security advisories and reported supply-chain compromise incidents in 2026 make unpinned package installation especially sensitive. Prefer Hermes's built-in model support until a gateway's benefit is measured.
- **Piper:** the current OHF-Voice project is GPL-3.0; model licenses can have distinct obligations.
- **Chatterbox:** upstream states it was retired in August 2026; do not rely on future fixes.
- **GBrain:** avoid concurrent embedded PGLite writers; provider adapter and version dependencies are not automatic.
- **Obscura:** incomplete Chromium parity acknowledged; complex SSO, WebRTC or anti-bot heavy sites may require Playwright.
- **OpenGenerativeAI:** free source-code and free unlimited hosted image/video generation are NOT equivalent.
- **OpenMausBot:** documented Windows binary/installer does not prove all Windows host controls nor native Hermes driver support.
- **UI-TARS Desktop:** archived November 9, 2026; use as research, not new primary dependency.
- **Screenpipe:** continuous screen/audio collection is privacy- and disk-intensive, and current app is source-available with plan-dependent features; explicit opt-in only.
- **APScheduler:** repository describes v4 as prerelease; pin a suitable stable version if chosen.
- **Open Design:** local-first does not necessarily mean every telemetry path is disabled; review network/privacy behavior.

## Original evidence and audit trail

- [Hermes skill catalogs and progressive disclosure](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md)
- [Hermes official plugins and named install paths](https://github.com/NousResearch/hermes-official-plugins)
- [Hermes advanced delegation version and routing](https://github.com/NousResearch/hermes-official-plugins/blob/main/advanced-delegation/README.md)
- [OpenMausBot actual supported backends and Windows matrix](https://github.com/OpenMausBot/OpenMausBot)
- [Hermes Studio operator interface](https://github.com/JPeetz/Hermes-Studio)
- [GBrain local memory design](https://github.com/garrytan/gbrain)
- [GBrain Hermes compatibility adapter](https://github.com/veltri-23/hermes-gbrain-memory)
- [Agent Reach setup and auth requirements](https://github.com/Panniantong/Agent-Reach)
- [Open Design local-first and Hermes support](https://github.com/nexu-io/open-design)
- [Obscura browser caveats](https://github.com/h4ckf0r0day/obscura/releases)
- [Obscura MCP behavior](https://github.com/h4ckf0r0day/obscura/wiki/Use-the-MCP-server)
- [Cua Driver Windows documentation](https://github.com/trycua/cua/blob/main/libs/cua-driver/rust/Skills/cua-driver/WINDOWS.md)
- [Cua Driver Windows+Hermes official guide](https://github.com/trycua/cua/blob/main/blog/inside-windows-computer-use.md)
- [Open Generative AI local and cloud modes](https://github.com/Anil-matcha/Open-Generative-AI)
- [Maintainer on MuAPI key and paid API credits](https://github.com/anil-matcha/open-generative-ai/issues/203)
- [Serena LSP symbolic editing and tokens](https://github.com/oraios/serena)
- [sherpa-onnx Windows and local speech features](https://github.com/k2-fsa/sherpa-onnx)
- [Piper license terms](https://github.com/OHF-Voice/piper1-gpl)
- [Chatterbox maintenance retirement warning](https://github.com/resemble-ai/chatterbox)
- [LiteLLM security advisories](https://github.com/BerriAI/litellm/security/advisories)
- [APScheduler v4 prerelease warning](https://github.com/agronholm/apscheduler)
- [OpenDesign html-video current and planned engines](https://github.com/nexu-io/html-video)
- [MCP Inspector UI/CLI/TUI integration validation](https://github.com/modelcontextprotocol/inspector)
- [AI chat primitives and streaming interfaces](https://github.com/assistant-ui/assistant-ui)
- [UI-TARS Desktop archived November 9 2026](https://github.com/bytedance/UI-TARS-desktop)
- [Screenpipe source-available screen/audio recall warning](https://github.com/screenpipe/screenpipe)
- [Tauri Windows global shortcuts](https://tauri.app/plugin/global-shortcut/)

## Research limitations

This report is an extensive practical selection catalog, not proof of completeness across all of GitHub and not a source-code audit of every repository. All listings need compatibility testing on Immortility's exact Hermes and Windows releases before adoption. Social-post marketing claims and model-count/performance benchmarks were not treated as independently measured results. Some lower-priority discoveries are intentionally marked *Candidate* to distinguish them from documentation-reviewed projects.
