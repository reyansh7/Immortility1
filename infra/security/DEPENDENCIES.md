# Dependency review, developer preview

Registry versions resolved on 2026-11-13; JavaScript, Python and Rust transitive
versions are captured in pnpm-lock.yaml, uv.lock and Cargo.lock respectively.
No upstream framework source or model weights are redistributed.

| Dependency | License | Use |
|---|---|---|
| Tauri and plugins | MIT / Apache-2.0 | Native shell, tray, shortcuts |
| reqwest, futures-util | MIT / Apache-2.0 | Restricted native loopback HTTP/SSE bridge |
| React, React DOM, Vite, TypeScript | MIT | UI and build |
| FastAPI, Pydantic, httpx, jsonschema | MIT | Broker, validation, HTTP |
| Starlette, uvicorn | BSD-3-Clause | ASGI transport |
| Hermes Agent v0.21.1 | MIT | External installed runtime; not copied |
| SQLite | public domain | Python standard-library storage |

Test/build dependencies carry their upstream licenses. Check the resolved full
inventory before redistribution. This table is a direct-dependency review, not
a full legal audit or SBOM. Rust advisory scanning and signed binary distribution
remain release gates; npm and Python vulnerability scans are run locally and in CI.

The first scan found advisories in Starlette, pytest, Vitest and tinypool. Pins were
updated to fixed compatible versions, and subsequent npm/Python scans report zero
known advisories. This is a dated scan result, not a guarantee of future safety.

ESLint 10.14.0 still resolves minimatch 10.2.6 with a glob amplification advisory.
A dependency override scoped only to `eslint>minimatch` pins the fixed 11.0.1
release; TypeScript lint is rerun against that graph. No runtime dependency uses
this override. Supported ESLint 10 replaces the deprecated ESLint 9 line.

Official references:
- https://v2.tauri.app/start/prerequisites/
- https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration
- https://github.com/NousResearch/hermes-agent/blob/main/LICENSE
- https://fastapi.tiangolo.com/advanced/events/
- https://www.python-httpx.org/async/
- https://openrouter.ai/docs/guides/routing/model-variants/free

Vite 6.4.6 and TypeScript 5.9.3 are intentionally kept on compatible pinned versions;
the project does not require the newest major release. No npm lifecycle scripts
are blanket-approved. The esbuild platform binary from its optional package works
without enabling an install script.

## P2 local speech review — 2026-11-13

| Pinned integration | License / scope | Actual use |
|---|---|---|
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) 1.2.1 | MIT | CPU int8 STT; two threads, local files only |
| CTranslate2 4.9.0 | MIT | Whisper execution; optional CUDA only after DLL/compute checks |
| [Silero VAD](https://github.com/snakers4/silero-vad) ONNX bundled by faster-whisper | MIT | `vad_filter=True`; no extra PyTorch runtime required |
| [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) / piper-tts 1.8.0 | GPL-3.0-or-later | Local LJ/Joe speech synthesis |
| [sounddevice](https://python-sounddevice.readthedocs.io/en/0.5.6/api/raw-streams.html) 0.5.6 | MIT; review bundled PortAudio notices for redistribution | Device enumeration, bounded raw input/output streams |
| PyAV 18.0.0 | BSD-3-Clause Python binding; bundled FFmpeg components require their own license review | Audio decoding/resampling |
| ONNX Runtime 1.31.1 | MIT | VAD/Piper inference |
| NumPy 2.5.4 on Python >=3.12 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (wheel metadata) | PCM metering |

Whisper model: `Systran/faster-whisper-base`, pinned revision
`ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`. Piper models come from
`rhasspy/piper-voices`, pinned revision `2f358b6a560e3a913ebf509b2f3344f20b367f94`.
`en_US-ljspeech-medium` was trained from scratch on public-domain LJ Speech.
`en_US-joe-medium` identifies its dataset and rdh base as CC0. Model cards are
downloaded alongside both voices. Dataset provenance is not a substitute for a
complete model/distribution license review. Weights are downloaded locally, never
copied into the source tree or bundled into a release. Piper's GPL obligations and
all wheel/FFmpeg notices must be resolved before distributing an application bundle.

PyAV 19 removed `av.open(metadata_errors=...)`, which faster-whisper 1.2.1 still
uses. A real fixture test exposed this incompatibility; PyAV 18.0.0 is explicitly
pinned instead of patching upstream code. See the
[official PyAV changelog](https://pyav.basswood.io/docs/stable/development/changelog.html).
The initial Whisper model download also omitted `vocabulary.txt`; preparation and
readiness checks now include it. No privileged audio/GPU driver installation was
performed. CPU is the verified STT path; CUDA execution remains unverified.

This review covers this chat's Piper/Whisper additions. Newer Qwen dependencies
are outside this validation scope. See `docs/VOICE_CLONING.md` for their separate work.
