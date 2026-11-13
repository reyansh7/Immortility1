# Qwen dependency remediation — 2026-11-13

Status: **security acceptance FAILED; playback remains disabled**. No experimental
playback, synthesis, model load, audio decoding, re-cloning or audio upload was run.
The original `.venv-tts` was not changed or selected for use. The app still uses
the original environment path with `EXPERIMENTAL_QWEN_TTS=false` by default.

## Original findings and applicability

The fresh original-environment scan reproduced **52 advisory entries across four
packages**. Their published severity breakdown is **5 Critical, 30 High,
16 Moderate and 1 Low**. Every original entry, aliases, severity source and
conditional reachability assessment is in
[QWEN_ADVISORY_REGISTER.md](QWEN_ADVISORY_REGISTER.md). Machine-readable CVSS vectors,
including disagreements between sources, are retained in
[`qwen-advisories-reviewed.json`](../../infra/security/qwen-advisories-reviewed.json).
The X-CLIP finding uses the original [ZDI advisory's High / CVSS 7.8](https://www.zerodayinitiative.com/advisories/ZDI-25-1144/).

| Package | Original version | Entries | Current exposure and prerequisites if enabled |
|---|---|---:|---|
| Accelerate | 1.12.0 | 1 | Sharded-checkpoint path traversal/DoS requires malicious weight-map entries. The inspected fixed Qwen snapshot contains one main and one speech-tokenizer safetensors file, no shard indexes. The worker exposes no checkpoint/repository selection. This constrains the input; it does not fix the package or authenticate locally tampered cache files. |
| Pillow | 12.3.0 | 42 | Reviewed speech path accepts text and a tensor profile, with no image/PDF/font/Arrow operations or image upload route. PIL may be imported transitively. The Windows WMF/EMF finding matches this OS, but its renderer is not called. Future image processing or arbitrary Python execution would change this assessment. |
| setuptools | 78.1.0 | 3 | Package downloads, sdist building or legacy wheel installation are required. Speech does none. One issue is macOS Unicode-filesystem specific; the namespace-path issue is Windows specific but requires `Wheel.install_as_egg`. These are package vulnerabilities even though the reviewed speech path does not invoke them. |
| Transformers | 4.57.3 | 6 | X-CLIP conversion, LightGlue initialization and `save_pretrained` are not called. Trainer RNG loading is unused and additionally requires Torch <2.6, unlike installed 2.11. Model/generation initialization **is used**: config/kernel and pre-consent generation-code download findings require further remediation. Fixed revision/SDPA narrow input, but do not establish cache integrity or OS network isolation. |

With the broker activation gate off, there is no authorized Qwen execution path.
The conditional assessments are source/call-path analysis, **not penetration tests,
proof of exploitability or blanket declarations that vulnerable packages are safe**.
No published exploit payload was executed. Trust flags alone are insufficient for
the model-loading findings, whose advisories describe trust-check bypasses.

## Patched versions and actual compatibility checks

Official [Qwen source](https://github.com/QwenLM/Qwen3-TTS/blob/main/pyproject.toml)
and PyPI still publish 0.1.1 with exact `transformers==4.57.3` and
`accelerate==1.12.0` requirements. Installed package metadata agrees. Both the
original and candidate graphs pass `uv pip check`.

| Dependency | Patch situation checked | Actual compatibility result |
|---|---|---|
| setuptools | 78.1.1 fixes PYSEC-2025-49. Later fixes require 83.0.0 / 84.1.0; latest inspected is 84.2.1. | Installed Torch 2.11.0+cu128 requires **setuptools<82**. 81.0.0 is the highest non-yanked stable allowed release; installed only in the candidate. Two entries remain. |
| Pillow | [13.0.0](https://github.com/python-pillow/Pillow/releases/tag/13.0.0) is the reported fix for all 42 entries. | Gradio 6.17.3 requires Pillow<13. Gradio 6.18–6.31 releases still require Pillow<13. Gradio 6.32 permits Pillow<14, but requires Hub>=1.16, conflicting with Transformers 4.57.3's Hub<1.0. Resolver rejected the candidate; nothing was forced or installed. |
| Transformers | Original scan lists fixes at 5.0/5.3/5.10 for various findings; latest inspected is 5.22.2. Some records only specify a last-affected version. | Any 5.x violates Qwen's exact 4.57.3 requirement. No unverified `--no-deps` override or compatibility shim was applied. |
| Accelerate | Original scan lists no fixed release; OSV records last affected 1.14.0. Latest inspected is 1.15.0. | 1.15.0 violates Qwen's exact 1.12.0 requirement. Resolver explicitly rejected it. A newer version number outside the advisory range is not independently verified security clearance. |

The current upstream Torch release inspected is 2.15.0 and no longer specifies
the setuptools<82 cap. Migrating the paired CUDA Torch/torchaudio stack is a separate
compatibility task requiring native model/generation regression evidence; it was
not silently substituted to bypass current constraints. It would still leave
Qwen's core Transformers/Accelerate pins and the Gradio/Hub conflict unresolved.

## Isolated change and regression results

Candidate: `.cache/qwen-remediation/candidate`, Python 3.13.11, no system-site
packages. Its package files were copied into independent files from `.venv-tts`
(no hard links or shared source files), then only **setuptools 78.1.0 → 81.0.0**
was installed from the official PyPI wheel. No original environment, native
configuration or private voice asset was changed. A cached full reinstall lacked
packages; a wheel-only full reinstall encountered SoX's source-only distribution,
so neither was used to bypass source-build review.

- Dependency consistency: **89 packages compatible**, original and candidate.
- CPU-only candidate regressions: **7 passed**, including real existing profile
  loading with `weights_only=True`, tensor-contract roundtrip, checksum rejection
  before deserialization, revision rejection, missing-embedding rejection, exact
  environment/package identity and no CUDA/model initialization.
- Socket connection methods were blocked during those regressions. HF/Transformers
  offline flags were also set. These are test-process controls, **not a claim that
  production Qwen has an OS network sandbox**.
- Existing private profile and JSON checksums matched before/after the read-only
  load. All **13 recorded source/reference/profile/consent/transcript/sample/log
  assets** passed local SHA-256 preservation checks. Public model/compile caches
  and transient playback files are excluded from that asset manifest and were not
  modified by this work. The ignored fingerprint manifest contains local paths,
  never audio contents.
- Main project regression checkpoint: **78 Python + 5 frontend tests**, lint,
  typing, schemas and frontend build passed. A frozen, credential-free source
  reproduction also passed 78 + 5 at the worker-lifecycle checkpoint.
- Candidate import emitted the existing missing SoX and FlashAttention warnings.
  Neither was installed. No synthesis quality, voice identity, GPU compatibility,
  latency or playback acceptance is inferred from CPU profile tests.

## Rescan and additional coverage gap

| Installed graph | Direct scan findings |
|---|---:|
| Unchanged original | **52** across four packages |
| Candidate with setuptools 81.0.0 | **51** across four packages |
| Removed | PYSEC-2025-49 / CVE-2025-47273 |
| Newly introduced in direct scan | **0** |

The remaining original-family severities in the candidate are **5 Critical,
29 High, 16 Moderate, 1 Low**. No finding was suppressed or ignored.

Both direct scans skipped the `+cu128` Torch/torchaudio versions because those
exact versions are not on PyPI. A separate **OSV upstream-base-version** query for
2.11.0 found an additional Torch advisory:
[GHSA-rrmf-rvhw-rf47 / CVE-2025-3000](https://github.com/advisories/GHSA-rrmf-rvhw-rf47),
published **Low**, with reported fix 2.13.0. It concerns `torch.jit.script` memory
corruption. This is **additional to the original 52**; the description's historical
"critical" wording differs from the reviewed publisher's severity. The worker does
not expose arbitrary JIT source, but this is not an exhaustive transitive JIT
call-graph proof. Treat it as a further unresolved upstream-code risk for the CUDA
build pending validation. The base torchaudio query returned zero known findings;
that is not an independent CUDA-binary/driver audit.

Reports under ignored `data/audits/`:

- `qwen-original-rescan.json`
- `qwen-candidate-advisories.json`
- `qwen-cuda-base-advisories.json`
- `qwen-enriched.json`
- `voice-preservation.json` (local paths/hashes only; keep private)

## Decision and next security milestone

**Do not promote or enable the candidate.** There is no verified fully patched,
dependency-consistent Qwen 0.1.1 graph in this investigation. Required next work is
a reviewed upstream-compatible core dependency release/backport, a headless
dependency contract from upstream that removes the unused Gradio constraint, and
a separately validated CUDA pair where necessary. Do not remove mandatory package
metadata, rebuild another agent runtime or switch the user's stored voice to hide
these failures.

For later Qwen execution, also require pinned local model/processor/tokenizer
artifact integrity, verified offline model loading and no untrusted config/code
selection. Re-run full package and source checks, CPU profile-contract tests, then
native generation/cancellation and speaker-identity acceptance. Existing profiles
must remain checksum-identical; a runtime change is not permission to re-clone.

The user requested keeping Qwen disabled. If unresolved vulnerabilities remain,
obtain their explicit scoped approval **before** any experimental playback. No such
approval is currently granted. Computer Use remains stopped by the user.

## Reproduce the completed read-only checks

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
.\.venv\Scripts\python.exe .\scripts\audit-qwen-security.py
.\.venv\Scripts\python.exe -m pip_audit --path .cache/qwen-remediation/candidate/Lib/site-packages --progress-spinner off --format json --output data/audits/qwen-candidate-advisories.json
.\.cache\qwen-remediation\candidate\Scripts\python.exe .\scripts\verify-qwen-candidate.py
.\.venv\Scripts\python.exe .\scripts\check-voice-preservation.py
```

`pip-audit` exits 1 when it finds vulnerabilities; that is the expected failing
security gate, not a successful scan with zero findings. Public package/advisory
queries send identifiers/versions only. Candidate checks require its preserved
local environment and profile and never activate the desktop's voice runtime.
