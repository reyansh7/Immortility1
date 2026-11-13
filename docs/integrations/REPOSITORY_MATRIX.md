# Repository and dependency audit — 2026-11-13

Versions below distinguish installed integrations from audited candidates. Full
source hashes and repository metadata are in `infra/security/upstream-audit.json`.
An audited source revision is not an adopted runtime pin. No candidate was installed
or activated during P0; selected public source/docs were cached outside app source.

| Repository | Purpose | Installed / audited version | License | Interface and compatibility | Cost/resources | Status/evidence |
|---|---|---|---|---|---|---|
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Primary intelligence | Installed 0.21.1, full pin `04b88a4c0a7fe05ebe3bf053a103a39fe6638f11`; upstream release metadata 0.23.1 | MIT | Existing TUI JSON-RPC retained; ACP/HTTP, memory, cron, skills, delegation and MCP exist in installed source | Software local; inference only through free guard | INTEGRATION VERIFIED; real gateway adversarial denial/cancellation; no upgrade |
| [milind-soni/OpenMausBot](https://github.com/milind-soni/OpenMausBot) | Specialist teams; first CUA/browser candidate | Not installed; source `d76d0248`, package 0.1.155; MCP server 1.1.0 | Apache-2.0 core; separate enterprise license and third-party notices | stdio MCP; Windows embedded runtime documented; source requires Node >=24, unlike current Node 22 | Full app/team/CUA resource use unknown; protocol-only median 54.8 MB WS | Source catalogue INTEGRATION VERIFIED, actual app/team/Windows/browser BLOCKED; see OPENMAUSBOT.md |
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local STT | Installed 1.2.1; base-model pin in `voice_models.py` | MIT; model provenance separately reviewed | Existing adapter, CPU int8/two threads; optional checked CUDA; PyAV 18 pin preserved | Local; measured historical CPU 2.0–5.2 s including startup | INTEGRATION VERIFIED on synthetic audio; physical mic/noise/device tests remain |
| [snakers4/silero-vad](https://github.com/snakers4/silero-vad) | Speech activity detection | Bundled ONNX through faster-whisper; audited source `066409f3`, release metadata 6.2.3 | MIT | Reuse bundled VAD; do not install a duplicate capture/PyTorch VAD stack | Local ONNX CPU | Existing pipeline integrated; silence/noise acceptance still partial |
| [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) | Default local speech | Installed 1.8.0; LJ/Joe model revision `2f358b6a560e3a913ebf509b2f3344f20b367f94` | Package GPL-3.0-or-later; model cards separately reviewed | Existing worker/queued PCM playback retained | Local CPU; cold first audio historically 4.8–9.2 s | INTEGRATION VERIFIED synthesis/playback/Stop; latency goal not met |
| [cjpais/Handy](https://github.com/cjpais/Handy) | Alternative speech frontend | Not adopted; source `bd4b0271`, release 0.10.0 | MIT | Windows desktop; beta toggle/cancel CLI exists. Audited surface does not establish a broker-owned transcript/result contract | Duplicate mic/frontend/model residency unless justified; not measured | Deferred; retain existing faster-whisper rather than hotkey/capture duplication |
| [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | Authorized cloned voice | Existing qwen-tts 0.1.1; model `5d83992436eae1d760afd27aff78a71d676296fc` | Apache-2.0 code/model metadata; reference speaker consent separate | Isolated Python 3.13/CUDA worker retained; pinned Transformers 4.57.3/Accelerate 1.12.0 conflict with clean security upgrade path | Historical synthesis peak 2.74 GB VRAM; not real-time | IMPLEMENTED, experimental default OFF; 52 advisory entries in four isolated-env packages; no profile deleted |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | Browser alternative only after a measured gap | Not installed; source `48d9fe00`, package 1.0.3 | MIT | Current source includes its own Pydantic-AI agent loop and pins Pydantic 2.14.3, conflicting with broker 2.11.4 | Local Chrome optional, cloud/provider features may bill; no benchmark | Deferred; do not install into broker or duplicate Hermes/OMB by default |
| [microsoft/UFO](https://github.com/microsoft/UFO) | Windows controller alternative | Not installed; source `eae3c0a8`, release 3.0.10 (current README calls it UFO³) | MIT | Windows UIA/controller stack; README Python 3.10/3.11 differs from broker 3.13 | Model/provider cost and resources require measurement | Deferred; no second active controller; original UFO² references are historical |
| [docling-project/docling](https://github.com/docling-project/docling) | Document parsing | Not installed; source `b9bf356f`, release 2.150.0 | MIT code; model licenses separate | Python SDK/CLI, modular slim/extra packages and Windows classifiers | OCR/layout/model dependencies can be heavy; no benchmark | P6 candidate; no duplicate converter stack installed |
| [microsoft/markitdown](https://github.com/microsoft/markitdown) | Lightweight content conversion | Not installed; source `ed178952`, release 0.1.9 | MIT; optional converters retain own licenses | Python/CLI, optional format extras | Format-dependent; not measured | P6 candidate; choose per required fidelity, not alongside every parser |
| [pymupdf/PyMuPDF](https://github.com/pymupdf/PyMuPDF) | PDF-specific candidate | Not installed; audited source `67fe1152`; no runtime version claimed | AGPL-3.0 repository; distribution review required | Python PDF API; not interchangeable with a permissive renderer without review | Local; no benchmark | Deferred pending actual PDF need/license review |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | Local image backend | Not adopted; source `dc9ffe6a`, release 0.45.0 | GPL-3.0 code; each weight/workflow has separate terms | On-demand external process/API, not broker-venv import | GPU/model-dependent; 8 GB compatibility unmeasured | P6 candidate; no service or weights installed |

Cursor CLI and external Canva/Figma/GitHub/Google/MCP account integrations require
their own supported interface, explicit connection/permissions and cost checks.
An assistant-side connector's availability does not automatically connect that
service to Immortility. No external account access was activated in this audit.

Existing dependencies remain pinned in `uv.lock`, `pnpm-lock.yaml` and Cargo.lock.
Broker/npm advisory scans were clean on the audit date. The separate Qwen graph
is not covered by that clean result; see `infra/security/qwen-advisory-summary.json`.
The legacy Qwen installer now requires an explicit experimental switch and pins
the installed Torch/torchaudio versions, but its full transitive graph is not a
security-cleared reproducible release environment. No automatic upgrade was applied.
