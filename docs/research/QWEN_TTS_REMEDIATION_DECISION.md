# Qwen TTS remediation decision — 2026-11-13

**Final recommendation: BLOCKED for activation.** The separately named headless
candidate passes its CPU research gates. It is not a verified replacement runtime
and has not been selected by Immortility. `EXPERIMENTAL_QWEN_TTS=false` remains in
effect. No pretrained model weights were loaded, no CUDA model was initialized,
and no synthesis, playback, audio decoding, re-cloning or voice-data upload was
performed by the research candidate.

## Scope, plan and preservation

This work builds on [the previous remediation](../security/QWEN_REMEDIATION.md) and
[the original 52-entry register](../security/QWEN_ADVISORY_REGISTER.md). It did not
re-fetch or repeat that entire investigation. New work was limited to:

1. Check current official release metadata and concrete compatibility patches.
2. Review and materialize a pinned, separately named headless derivative.
3. Resolve and reproduce its real metadata/dependency graph in fresh environments.
4. Validate artifact identity, restricted profile loading and CPU contracts.
5. Scan the selected packages and retain source findings that scanners missed.
6. Check current broker/frontend regressions and document native approval gates.

Main risks were unmerged compatibility code, inherited dependency pins, false
confidence from version ranges, model/config substitution, unsafe deserialization,
Windows reparse points, mutable-cache races, and unmeasured CUDA behavior.

The production `.venv-tts`, broker `.venv`, private profiles, consent, source audio
and native settings were not modified by this research. All 13 previously recorded
private voice assets passed SHA-256 preservation checks before/after testing.
The public model cache was read for verification and was not rewritten. No private
audio or profile was copied into the candidate. The existing tensor profile was
read on CPU without re-serialization. Hermes/OpenMausBot were not changed by this
work, and Computer Use was not restarted.

Other working-tree changes appeared during validation (the broker test count
increased). They were preserved, including runtime files whose formatting currently
blocks the combined check. Their functionality is not attributed to this work.

## Investigated options and decisions

| Option | Evidence | Decision |
|---|---|---|
| Official `qwen-tts` | PyPI remains 0.1.1; official main `022e286b98fbec7e1e916cb940cdf532cd9f488e` still has exact Transformers 4.57.3 and Accelerate 1.12.0 pins. | Original environment preserved, inactive. It cannot resolve to patched core versions under its published metadata. |
| Upstream PR #360 | [Open, unmerged PR](https://github.com/QwenLM/Qwen3-TTS/pull/360), head `00969daa8064e23adc9e5f52cdf20cf247f94159`. Reviewed configuration, masking/cache, RoPE-buffer and Mimi-attention changes. | Used as an explicitly unofficial, pinned research source; not represented as an official release. |
| `qwen-tts-hf` 0.1.1.post1 | [Distribution notice](https://pypi.org/project/qwen-tts-hf/) identifies the same PR. It retains `accelerate==1.12.0`, Gradio and 25 Hz dependencies. Same `qwen_tts` namespace; cannot coexist with stock Qwen. | Not installed unchanged; it would retain known vulnerable dependencies. |
| Metadata override / global monkey patch | Would install a graph inconsistent with the published package or silently change framework globals in another runtime. | Rejected. No forced install, `--no-deps` install, advisory ignore list or hidden metadata deletion was used. |
| Headless derivative C1, Accelerate 1.15.0 | Normal resolver and scans passed, but actual source still joins unsanitized checkpoint-index filenames. A reader-mocked contract demonstrated an out-of-scope path. | Rejected despite a zero-finding scan. See the source finding below. |
| Headless derivative C2, no Accelerate | Qwen's selected 12 Hz code has no direct Accelerate imports. Transformers supports default CPU loading without it; device-map/offload requests require it. | Selected for CPU research only. Device-map input is explicitly rejected; future GPU movement needs its own validated implementation. |
| Newer Transformers 5.22.2 | Current PyPI metadata inspected. Compatibility was not assumed; the upstream patch's documented validation used 5.15.1, and a later-version Mimi issue is referenced from the PR. | Pin 5.15.1 for this candidate. It has no indexed findings in the performed scans. No claim of compatibility with every 5.x release. |
| Faster Qwen / GGML alternatives | [Faster Qwen](https://github.com/andimarafioti/faster-qwen3-tts) uses the compatibility distribution and introduces CUDA graphs / another generation implementation. A GGML/GGUF path does not establish an importer for this saved tensor-profile contract. | No alternative engine installed or substituted. Profile/generation parity and native behavior are unverified; changing engines would not close this acceptance gate. |

The PR author's GB10/DGX generation and quality results are upstream reports, not
Windows/RTX 4060 results reproduced here. No native claim is inherited from them.

## Candidate dependency matrix

Selected package: **`immortility-qwen-tts-headless==0.1.1.post1+immortility.2`**.
It provides the original `qwen_tts` namespace in an independent environment and is
never co-installed with stock Qwen. This is a local derivative, not a published
official package or a silent patch to the original environment.

| Component | Original | Prior isolated candidate | Selected C2 |
|---|---|---|---|
| Python | 3.13.11 | 3.13.11 | 3.13.11, Windows x64 |
| Qwen source | qwen-tts 0.1.1 | Same | PR360 exact commit, reviewed local patch |
| Transformers | 4.57.3 | 4.57.3 | **5.15.1** |
| Accelerate | 1.12.0 | 1.12.0 | **Absent**, dispatch/offload unsupported |
| Torch | 2.11.0+cu128 | Same | **2.15.0 CPU wheel**, `torch.version.cuda is None` |
| setuptools | 78.1.0 | 81.0.0 | **84.2.1** |
| Pillow / Gradio | 12.3.0 / 6.17.3 | Same | **Absent** |
| torchaudio / SoX / ONNX Runtime | Installed for unused 25 Hz imports | Same | **Absent**; selected model is 12 Hz |
| Hugging Face Hub | 0.36.2 | Same | **1.33.0**, resolved normally |
| Tokenizers | 0.22.2 | Same | **0.22.2**, within selected Transformers bounds |
| Other direct dependencies | Existing graph | Same | librosa 1.0.1, soundfile 0.14.0, einops 0.8.2, NumPy 2.5.4 |

The installed Windows C2 graph contains **62 distributions**. Its universal lock
also describes platform-specific dependencies not installed on this Windows host.
The original root `uv.lock`, `pnpm-lock.yaml` and original TTS environment were not
changed. The research lock lives at `integrations/qwen-headless/uv.lock`.

### Packaging and provenance

- The Apache-2.0 license was read and retained. Original copyright notices remain;
  modified source files carry change notices and the built package includes NOTICE.
- Only the selected Qwen namespace files are materialized, under ignored research
  cache paths. Gradio CLI/entry point and 25 Hz codec source are excluded, not merely
  left installed but unused. No agent framework was rebuilt.
- The source archive is pinned by commit and SHA-256
  `545855ad56ddbddc237b746922aed5c789ca21e901347e68d5ee0deecfd2bd58`.
- `integrations/qwen-headless/provenance.json` records original/candidate source
  fingerprints and local recipe/lock fingerprints. `reviewed-source.patch` records
  local source changes; the preparation script fails on changed patch context.
- The renamed package declares its real dependencies. Pinned setuptools 84.2.1
  and wheel 0.47.0 build it normally. Installation uses the normal resolver and
  frozen lock; no installed distribution metadata is edited afterward.
- C2 was built again in a fresh directory from the frozen lock with **offline**
  cached installation. `uv pip check` passed with 62 packages. This demonstrates
  same-machine reproduction, not an empty-cache/clean-Windows-machine proof.

The final research source/environment is
`.cache/qwen-remediation-v2/verified-source`, separate from `.venv-tts`.
The app's worker still selects `.venv-tts`; this candidate is not on its active path.

## Security comparison and source review

Every original ID, severity, alias and selected-candidate disposition is retained in
[`qwen-headless-residuals.json`](../../infra/security/qwen-headless-residuals.json).
No original finding is dropped or reclassified as fixed solely because its path
was conditionally unreachable.

| Original finding group | Entries | Selected candidate disposition |
|---|---:|---|
| Pillow native image/PDF/font/Arrow findings | 42 | Component absent from the installed graph and selected source dependencies. This removes that code from this candidate; it does not patch the original environment. |
| Accelerate index traversal/DoS | 1 | Component absent; device-map/offload arguments rejected. The newer-version source finding remains recorded, not called an upstream fix. |
| setuptools download traversal, macOS sdist normalization, Windows legacy namespace escape | 3 | Updated to 84.2.1, beyond all reported fix versions. Reviewed namespace resolver validates identifier components and destination containment. |
| Transformers X-CLIP, LightGlue, Trainer RNG, attention configuration, template saving and custom generation findings | 6 | Updated to 5.15.1, outside reported affected ranges; zero indexed findings in both queried services. Model/config restrictions below provide additional controls, not substitutes for dependency patches. |
| Additional original Torch JIT finding | Outside the 52 | CPU Torch 2.15.0 is beyond the reported 2.13.0 fix. No CUDA-binary test is inferred from that result. |

PyPI-backed scanning of the exact final reproduced graph reports **zero known
findings in 61 published packages**, with the local derivative explicitly skipped
as unindexed. OSV independently reported zero findings for the equivalent C2
dependency graph. Explicit OSV queries also covered the upstream names `qwen-tts`
0.1.1 and `qwen-tts-hf` 0.1.1.post1, returning zero indexed package records. Those
queries do not certify modified source or prove the absence of unknown defects.

### Important scanner limitation: Accelerate 1.15.0

The original advisory's affected range ended at 1.14.0. Nevertheless, inspected
1.15.0 source contains:

```python
checkpoint_files = sorted(list(set(index.values())))
checkpoint_files = [os.path.join(checkpoint_folder, f) for f in checkpoint_files]
```

A synthetic `../outside-do-not-read.safetensors` index entry reached a **mocked**
checkpoint reader outside the approved fixture folder. The reader raised before
any file read, tensor deserialization or pretrained model load. Evidence:
`data/audits/qwen-accelerate-path-contract.json`.

This is a demonstrated validation gap in a rejected option, despite clean scans.
It was addressed in C2 by removing the component **and its dispatch feature**.
No Accelerate source fork, relaxed advisory filter or arbitrary unsafe loader is
installed. Full model loading without Accelerate is still a native approval gate.

### Candidate hardening implemented and tested

1. **Same model and revision.** Main weights, text tokenizer/processor and nested
   speech tokenizer all use revision `5d83992436eae1d760afd27aff78a71d676296fc` of
   `Qwen/Qwen3-TTS-12Hz-0.6B-Base`. There is no model substitution.
2. **Trusted artifact manifest.** Eleven files have pinned sizes and SHA-256 hashes.
   Large-file hashes came from the upstream revision's LFS metadata. Pinned public
   small files were downloaded, checked against their Git blob IDs and SHA-256
   hashed. All eleven existing local files matched, including both safetensors.
3. **Local-only loader interface.** Reject remote IDs/URLs, UNC/relative paths,
   wrong revisions, missing/extra artifacts, unreviewed directories, reparse points
   and caller-supplied loading/configuration overrides. Check directories before
   descent; a real Windows junction test passed without traversing its target.
4. **Nested flags preserved.** Model, processor, speech tokenizer and feature
   extractor get verified local paths and explicit offline/trust restrictions.
   Model loads require safetensors and `weights_only=True`; remote download helpers
   and URL audio branches fail explicitly. Loader propagation tests use mocks;
   actual pretrained weight loading did not occur.
5. **Restricted profile reader.** Require trusted profile **and metadata** hashes,
   size/format/model/revision checks, then `torch.load(map_location='cpu',
   weights_only=True)`. Validate exact tensor keys, dense CPU tensors, dimensions,
   finite embedding values and transcript bounds. A harmless unallowlisted pickle
   class was rejected; metadata corruption failed before deserialization. There is
   no `safe_globals` expansion or profile migration.
6. **No activation grant.** None of these checks authorizes execution. The broker
   remains authoritative. Its experimental gate remains false, and the candidate
   has no registration, auto-selection or generic execution endpoint.

Python flags, socket mocks and path checks **are not an OS sandbox**. A future
broker integration must independently bind task/session, action, expiry, canonical
snapshot path, manifest digest and profile/metadata hashes to its authorization.
Model/profile check-to-use races require read-only staging and enforced filesystem
permissions. Windows restricted-token/ACL and egress controls have not been
implemented or claimed here. The model and profile must not be writable by an
untrusted process during future loading.

## Actual correctness and regression results

| Check | Observed result |
|---|---|
| Selected/reproduced dependency graph | 62 installed packages; `uv pip check` passed; frozen offline reproduction succeeded |
| Final CPU research contracts | See final machine report `data/audits/qwen-headless-contracts.json`; includes source identity, actual pinned configuration/text-tokenizer parsing, RoPE/Mimi helpers, existing profile reading, restricted deserialization, negative artifact/argument checks and real junction rejection |
| Artifact identity | All 11 files matched upstream; no weight deserialization |
| Private preservation | 13 recorded private assets, 0 missing/changed |
| Earlier C1 test | 15/16 passed; failed assertion assumed Mimi retained `rope_theta` as a direct field. Source showed its legitimate `rope_parameters` representation. The revised contract compares the actual initializer; no unnecessary shim was added. |
| Initial main regression run | 83 passed, 2 failed: Windows taskkill cleanup exceeded its deadline during competing imports |
| Focused lifecycle rerun | 9 passed, without changing code or relaxing timeouts |
| Serial broker checkpoint | **89 tests passed**, one existing AnyIO/Starlette deprecation warning |
| Frontend checkpoint | **6 tests passed**; TypeScript, ESLint, Prettier and production build passed |
| Strict broker mypy / new-file Ruff | Passed; broker check covered 20 source files |
| Secret isolation | Configured provider keys absent from frontend source/bundle/docs/config |
| Combined `scripts/check.ps1` | **Not green at observed checkpoint**: stopped on formatting in app.py, delegation.py, hermes.py, test_broker.py and test_delegation.py after the 89-test pass. These concurrent existing changes were preserved; Hermes was not reformatted. |

Warnings from bare text-tokenizer loading (generic model-type notice and a BPE
deprecation) are recorded, not suppressed. A tokenizer roundtrip is not full
processor/model/generation parity. The CPU tests initialize only small helper
buffers and configurations, never the pretrained model. The original broker test
suite uses its deterministic fixtures; no Qwen inference or hardware playback was
introduced into it.

## Performance and Windows CUDA plan

Current measurements are limited to CPU test import and artifact hashing, recorded
in `qwen-headless-contracts.json`. The eleven-file verification previously measured
about 2.1 seconds on this host. Import timing varies with cold DLL/cache/antivirus
state and is not a model-load or first-audio benchmark. RAM, VRAM, inference
latency, throughput, cancellation during a CUDA forward and speaker similarity are
**unmeasured for C2**. Historical original-runtime numbers were not reused.

The official PyTorch indexes were queried without downloading GPU wheels:

- No Torch 2.15.0 Windows cp313 wheel was listed in cu128 or cu130.
- cu132 lists `torch-2.15.0+cu132-cp313-cp313-win_amd64.whl`, SHA-256
  `7b54774dedca2a1147f1ae47451d9a8a7e88b80665fc505bf6a4f1f427d21e97`.
- This is an available future candidate, **not an installed or validated GPU
  runtime**. The current driver was not changed or probed by this CPU phase.

[TorchAudio's current documentation](https://docs.pytorch.org/audio/stable/installation.html)
states 2.11 uses the stable ABI and supports Torch 2.11 and later; older exact-pair
rules do not automatically apply to that release. C2 does not need torchaudio
because the selected 12 Hz code does not import it. Do not add it solely to create
a nominal pair. The original 2.11.0+cu128 installations remain untouched.

Before a native checkpoint:

1. Finish independent source/security review and the working-tree formatting gate.
   Stabilize Windows cleanup under realistic load; do not increase timeouts just
   to hide failures.
2. Prepare a concrete approval request for a separate GPU research environment and
   **model loading only**. Keep the app's experimental flag false. Confirm exact
   Windows driver requirements for the wheel against NVIDIA's release notes;
   [CUDA-family compatibility floors](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)
   alone do not guarantee all features/PTX behavior.
3. After approval, lock/hash the exact official GPU wheel and dependencies, rescan,
   then measure CPU loading without Accelerate followed by explicit `.to('cuda:0')`
   under broker authorization. Verify BF16/SDPA support, non-persistent RoPE buffers,
   peak CPU/private RAM, VRAM, cleanup and absence of network access. Do not assume
   `.to()` handles the separate codec wrapper or restores every buffer correctly.
4. Generation requires its own approved scope. Then compare fixed-seed ICL codec
   and text behavior, natural EOS, finite/non-silent output, speaker identity,
   sentence ordering, Stop during load/generation and restart. Preserve profile
   fingerprints. No re-cloning is authorized as a compatibility workaround.
5. Benchmark cold/warm load, artifact-check overhead, first-audio and whole-turn
   latency, CPU/RAM/VRAM and cancellation p50/p95 on the RTX 4060/8 GB laptop.
   Serialize heavyweight GPU work through the existing broker. Promotion needs
   those measured results and an explicit review; a successful installation is
   insufficient.

## Residual issues and recommendation

The machine register retains seven explicit residual gates: unindexed derivative
coverage, untested pretrained/native behavior, lack of OS isolation and immutable
staging, unverified manual GPU placement without Accelerate, observed taskkill
timing instability, the rejected Accelerate source flaw, and unvalidated GPU
wheel/driver behavior. The combined-check formatting failure is an additional
checkout acceptance issue.

**PASS:** isolated/frozen CPU research candidate, published dependency checks,
read-only profile compatibility, artifact identity, tested input restrictions and
preservation at the recorded checkpoints.

**BLOCKED:** full security/compatibility acceptance, native loading/generation and
activation. Official Qwen still has incompatible dependency pins; the reviewed
compatibility PR remains unmerged, and the candidate's narrower loading path is
not a native parity proof. Keep the production environment and selected voice
unchanged. No experimental playback approval has been granted in this phase.

## Windows reproduction commands — CPU research only

Existing final candidate checks:

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
.\.cache\qwen-remediation-v2\verified-source\.venv\Scripts\python.exe .\scripts\verify-qwen-headless.py
.\.venv\Scripts\python.exe .\scripts\check-voice-preservation.py
```

Fresh cached source/environment reproduction (use a new destination):

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv'
$researchCopy = '.cache/qwen-remediation-v2/reproduce-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
.\.venv\Scripts\python.exe .\scripts\prepare-qwen-headless.py --output $researchCopy
uv sync --project $researchCopy --frozen --offline --no-editable
uv pip check --python (Join-Path $researchCopy '.venv/Scripts/python.exe')
& (Join-Path $researchCopy '.venv/Scripts/python.exe') .\scripts\verify-qwen-headless.py
```

Source materialization verifies the pinned public archive and requires the reviewed
recipe/lock. Empty caches may require explicit public source/package downloads;
the offline command fails rather than choosing new versions. These commands never
change the app's worker path or enable Qwen. Do not run the historical clone-build
or synthesis scripts as part of this research checkpoint.
