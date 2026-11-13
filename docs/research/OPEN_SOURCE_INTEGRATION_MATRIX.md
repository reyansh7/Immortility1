# Open-source integration decisions — 2026-11-13

The installed and previously audited set is in
[REPOSITORY_MATRIX.md](../integrations/REPOSITORY_MATRIX.md). This file records
the candidates named for a multi-agent and 3D command center. None of the new
candidates were installed.

| Candidate | Audited pin | License | Windows | Decision |
|---|---|---|---|---|
| NousResearch/hermes-agent | Installed 0.21.1, `04b88a4c0a7fe05ebe3bf053a103a39fe6638f11` | MIT | Yes, current integration | Keep. Do not upgrade in this pass. Upstream metadata 0.23.1 was seen earlier and not adopted |
| milind-soni/OpenMausBot | Not installed. Source `d76d0248`, package 0.1.155 | Apache-2.0 core, separate enterprise terms | Documented, but source wants Node >= 24 and this machine is Node 22.13.1 | Reject for now. A source MCP probe passed with the network disabled. No team or computer-use run |
| cjpais/Handy | Not adopted. Source `bd4b0271`, release 0.10.0 | MIT | Desktop app exists | Reject. faster-whisper already owns speech-to-text |
| vercel-labs/agent-browser | Not installed in this pass | Not adopted | Not measured here | Reject. No browser controller is authorized, and OpenMausBot was already the first candidate |
| pmndrs/react-three-fiber and drei | Not installed | MIT | Browser/WebView | Reject for this pass. There is one Hermes agent. A 3D scene of specialist agents would not reflect backend state |
| xyflow/xyflow | Not installed | MIT | WebView | Reject for this pass. Task order is a short state list. A graph library would not add a real dependency |
| mem0ai/mem0 | Not installed | Apache-2.0 | Python possible | Reject. Hermes memory exists upstream and is disabled. SQLite already stores turns. A second memory engine is not justified |

Browser Use, UFO, Docling, MarkItDown, PyMuPDF, and ComfyUI stay deferred for
the reasons already recorded in the repository matrix. Qwen3-TTS stays
experimental and off.
