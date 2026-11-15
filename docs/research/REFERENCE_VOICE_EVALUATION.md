# Reference-conditioned mechanical voice — 14 November 2026

The user approved `Reference-Mechanical-Metal.wav` as the final voice direction.
This is **real local reference-conditioned XTTS synthesis**, not Onyx with a pitch
filter and not a replay of the uploaded recording. Default installation flags
remain off. The broker integration adds an explicitly enabled voice choice;
Piper, Kokoro and the saved friend profile remain available and unchanged. Qwen
remains disabled. Hermes and OpenMausBot were not modified.

## Runtime decision and source review

| Option | Verified capabilities and constraints | Decision |
|---|---|---|
| Kokoro 0.9.4 | Stock speaker packs; our integration has no reference speaker encoder. DSP cannot change this into reference cloning. | Preserve as fallback. |
| F5-TTS 1.1.22 | Official reference audio/text conditioning, safetensors and local vocoder paths; streaming helper emits chunks after generating each batch. MIT code, CC-BY-NC-4.0 weights. Published base metadata includes UI/training dependencies and Accelerate 1.15, whose source issue is documented in the previous Qwen audit. | Not installed; a lean, reviewed packaging path would be needed. No F5 quality comparison is claimed. |
| Chatterbox 0.1.7 | Actual reference conditioning in official source; MIT project. Published Python 3.12 metadata pins Torch/TorchAudio 2.6 and Transformers 5.2, conflicting with our patched stack. | Not installed or benchmarked; no metadata bypass or forced downgrade. |
| Maintained idiap Coqui 0.28.0 / XTTS-v2 | Reference conditioning and genuine incremental generation; configurable local checkpoint paths. MPL-2.0 code; **CPML non-commercial model and outputs**. | Selected viable candidate; real Windows GPU synthesis and cancellation verified. Not claimed globally best among untested engines. |

Primary sources: [F5 source](https://github.com/SWivid/F5-TTS),
[F5 weights](https://huggingface.co/SWivid/F5-TTS),
[Chatterbox metadata](https://github.com/resemble-ai/chatterbox/blob/master/pyproject.toml),
[maintained Coqui](https://github.com/idiap/coqui-ai-TTS),
[XTTS APIs](https://coqui-tts.readthedocs.io/en/latest/models/xtts.html),
[CPML terms](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt).
The local preview is for private, non-commercial use; commercial distribution is
not cleared by this evaluation. The license text accompanies the matched previews.

The source audit pinned Coqui commit `ed4ec35c2282bf61a6b4297f066892d33ae71fc0`,
F5 `600e5fdfbf319f84735557aca80a7aaf60d487e6`, and Chatterbox
`ab55923c27757c90cfcc407baa57dc25a7d25217`. Public source/metadata audit cache is
`.cache/reference-tts/upstream`; no full upstream repository was copied into the
application.

## Reference and identity limitations

Original `now_im_free.mp3` SHA-256:
`d161839fe97adf85ded67ce74fbbe413f996bd4a11049276c5bbee5852ddff71`.
The source was not changed or uploaded. It is about 9.3 seconds of a finished
cinematic mix, with two short speech regions and approximately 1.8 seconds between
them. Approximately 58.7% of the measured active-frame spectral power was below
65 Hz. That is mix energy, not a measured vocal fundamental.

Separate speech crops retain 6.92 seconds with conservative margins. A 65 Hz
high-pass reduces rumble. **This does not isolate a dry actor recording or remove
overlapping effects/music.** The original and both derived versions are preserved.
Their fingerprints are in ignored `data/reference-tts/reference/reference.json`.
Zero-shot conditioning is kept in worker memory; existing private clone profiles,
consent records and source audio are not repurposed or overwritten.

Reliable regional-accent classification, isolated vocal formants, breathiness,
roughness and exact cinematic effect decomposition cannot be established from
this short mixed reference. No such measurements or listening-based judgments are
invented. English conditioning is implemented; sarcasm, menace and naturalness
remain human listening judgments, not guaranteed emotion controls. More clean,
varied speech would improve the evidence for identity and pronunciation; the
current sample is adequate for a trial, not proof of an exact match.

## Actual comparison results

Five fixed, original dialogues cover normal conversation, a question, dry humor,
quiet authority and dramatic wording. Every variant receives identical text from
`config/reference-tts-evaluation.json`. Generated categories are test scripts, not
proof that the engine can independently direct each emotion.

The three matched main previews are under `data/previews/reference-matched`:
`Original-Onyx.wav`, `Reference-Dry.wav`, `Reference-Metal.wav`. “Dry” means **no
added DSP**, not that the conditioning recording was free of processing. Subsequent
user-directed revisions preserve every previous file. The approved final effect
is `Reference-Mechanical-Metal.wav`: -1.8 semitones with formants preserved,
stronger short resonances, 24% parallel ring modulation at 90/133 Hz, bounded
levels and no long echo. This deliberate pitch adjustment followed the user's
later requests for more depth; identity still comes from XTTS conditioning.

| Check | Observed result |
|---|---|
| Same XTTS internal speaker encoder cosine, five-case mean | Onyx 0.165; reference-conditioned 0.550; subtle added DSP 0.555 |
| Normal sentence encoder cosine | Onyx 0.093; reference-conditioned 0.529 |
| Warm incremental generation first chunk | 0.313–0.332 s in the initial full evaluation |
| Full 3.5–4.6 s utterance synthesis | Approximately 1.55–2.15 s in that evaluation |
| GPU tensor allocation peak | Approximately 1.86–1.89 GiB; allocator reservation about 2.14 GiB |
| Initial CPU-first loading | 17–19 s model load; 25–28 s end-to-first-chunk cold |
| Initial sampled worker RAM | 4.76 GiB peak, about 2.2 GiB after loading |
| Cancel during actual incremental generation | 36.2 ms to owned worker reaped |
| Cancel during weight initialization | 3.5 ms to owned worker reaped |
| Clipping in matched output files | 0 samples |

Cosines are **not match percentages**, not independent biometric validation, and
not calibrated speaker-identification acceptance scores. The encoder is part of
XTTS itself. They support a comparison with stock Onyx, not an exact-match claim.

Local Whisper recovered all words in question, quiet and dramatic cloned tests.
For the normal sentence it omitted “and” (6.25% word-error proxy); the dry humor
test had article/contraction differences. Onyx also produced an ASR contraction
difference in its quiet test. These are transcription/clarity flags, not proof
of what a listener heard. The final stronger mechanical preview retained the
same normal-sentence transcription flag. Intelligibility is not declared perfect.

Reports: `data/audits/reference-tts-full-benchmark.json`,
`reference-tts-intelligibility.json`, individual run reports and mechanical FX
reports. The external child-process RAM sampler returned implausible 4 MiB values;
it was rejected, and the RAM figure above was measured inside the worker instead.
This is a small benchmark, not p95/soak validation.

## Supply-chain and loader checks

Isolated `.venv-reference-tts`, Python 3.12.14, and a frozen separate lock. Current
pins include Coqui 0.28.0, Torch 2.15.0+cu132, TorchAudio 2.11.1, TorchCodec 0.17.0,
Transformers 5.15.1, setuptools 84.2.1, Six 1.17.0 and Pedalboard 0.9.26.
TorchAudio's [documented stable ABI](https://docs.pytorch.org/audio/stable/installation.html)
supports Torch 2.11 and later. Actual inference was tested on RTX 4060 Laptop,
8188 MiB VRAM, driver 621.01. No driver or system Python was changed.

`uv pip check` passes 104 installed distributions. The final installed audit has
zero known findings for 103 indexed distributions and explicitly skips the CUDA
Torch local version, which is not indexed on PyPI. Its published base version
2.15.0 was separately audited in the resolved graph, and the official CUDA wheel
is hash-pinned in `uv.lock`; this does not turn the skip into a complete binary
security audit. No advisory was suppressed. License metadata is retained locally.

The original XTTS loader rewrote its legacy checkpoint during the first test.
The integrity gate detected it; the altered file was not accepted as a new hash.
The official model was restored. `reference_xtts.py` subclasses only the reader,
using weights-only mmap loading, four reviewed legacy config classes and a
tensor-only state check, without rewriting the artifact or patching packages or
framework globals. CPU fixtures verify unchanged hashes and rejection of unknown
pickle classes/non-tensor state. See `integrations/reference-tts/COMPATIBILITY.md`.

All model/config/vocabulary/license assets are revision/size/SHA-256 pinned.
Reference assets are also hashed. Runtime network connections are denied by a
Python audit hook, and the worker receives a keyless OS-variable allowlist with
separate caches and offline settings. These controls are **not OS sandboxing**;
same-user filesystem mutation/check-to-use races are not claimed solved.

## Broker integration and quick responses

The new `reference` voice is gated by `REFERENCE_VOICE_ENABLED`. Settings exposes
**IMMORTILITY · Mechanical reference**. English, speech speed, volume, speaker
selection, Read aloud, streamed assistant speech and global Stop use the broker's
existing voice lifecycle. Actual processed playback RMS drives the existing face;
there is no transcript-based fake mouth movement.

Prewarming begins when this voice is selected with Speak assistant replies on.
The worker and reference conditioning stay warm while that voice mode is enabled.
Turning it off, switching voice, global Stop or shutdown releases the worker.
Stop pauses automatic prewarming until a new user action; it does not immediately
reload the model. A failed warm-up does not retry endlessly.

The broker renders completed sentences as Hermes streams text and prefetches the
next sentence during playback through a bounded queue. Approved formant-preserving
FX are applied to complete phrases, avoiding discontinuities from resetting an
offline pitch processor on tiny chunks. The runtime therefore does **not** claim
0.31 s end-to-speaker latency from the incremental benchmark. Real broker/speaker
timings are recorded by `scripts/verify-reference-runtime.py`.

Full model hashes are checked on each process load. Warm requests remain bound to
that loaded manifest digest and recheck the small reference manifests/assets;
they do not reread 1.9 GB of already-loaded weights for every sentence. A GPU-first
constructor plus mmap loading removes the duplicate CPU parameter allocation;
legacy explicit CPU buffers are moved and all tensor placement is checked before
conditioning. Validation results and remaining gates are recorded below.

## Windows commands

The environment and reference are already prepared on this PC. To reproduce setup:

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-reference-tts.ps1
.\.venv-infernal\Scripts\python.exe .\scripts\prepare-reference-audio.py
.\.venv-reference-tts\Scripts\python.exe .\scripts\verify-reference-contracts.py
# Audible fixed local text, real GPU and broker Stop; no microphone/cloud:
.\.venv\Scripts\python.exe .\scripts\verify-reference-runtime.py
```

To use it in a fresh app process:

```powershell
$env:REFERENCE_VOICE_ENABLED = 'true'
$env:EXPERIMENTAL_QWEN_TTS = 'false'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Choose **IMMORTILITY · Mechanical reference**, keep language English, and turn on
**Speak assistant replies**. Wait for the warm-ready indication before timing a
reply. Close an older running app before launching the updated process. No live
GUI restart or native visual verification is performed by Computer Use.

## Final integration verification

The approved mechanical profile is now **integrated and verified through the
broker voice service and Windows audio output**. The local ignored `.env` enables
only `REFERENCE_VOICE_ENABLED=true`; examples/default installations remain off.
Qwen was verified false. App voice selection and device/consent preferences are
not silently rewritten: select the new voice once in Settings after a fresh app
launch. Keep Speak assistant replies on to keep the model warm. No physical GUI
or visual face-sync completion is claimed without the user's in-app check.

`data/audits/reference-tts-broker-runtime.json` records the final fixed-public-text
test, without a microphone or cloud call:

| Integrated measurement | Observed |
|---|---:|
| Fresh worker preparation, warm file cache | 15.54 s |
| Weight load within preparation | 7.51 s |
| First reply to nonzero playback meter | 2.26 s |
| Next reply to nonzero playback meter, same worker | 1.41 s |
| Stop to reaped worker / meter zero | 70.45 ms |
| Ready worker resident working set | 1765 MiB |
| GPU allocated / reserved after priming | 1839 / 3520 MiB |

These are local text-to-audio timings after a complete sentence is available;
they exclude Hermes/provider response latency and do not measure physical speaker
loopback or p95 behavior. Preparation primes lazy kernels once with silent fixed
text; no audio is played or uploaded and no model weights are trained. CPU-first
and GPU-first timings were recorded in differing cache/resource conditions, so
the entire timing difference is not attributed to one change. GPU-first loading
needed a final `.to('cuda')` for legacy FloatTensor-created buffers; every
registered parameter/buffer is now checked before conditioning. Failures were
retained and fixed rather than relaxed or hidden.

Regression evidence: the baseline broker suite passed 115 tests before this
integration; the reference evaluation checkpoint passed 123. Final full-suite
run: **124 passed, 3 failed**, all in the known unchanged Qwen worker's Windows
taskkill/cleanup tests. Serial lifecycle rerun: **8 passed, 1 failed** (timeout
reported cleanup failure instead of voice_timeout). The new reference voice's
actual Stop test passes and Qwen stays disabled. These failures are not waived;
the repository-wide release gate is not declared green. Strict mypy covered
31 broker files successfully; Ruff passed. Frontend checks, **41 tests**, and
production Vite build passed, with the existing large 3D-chunk warning retained.
CPU restricted-loader contracts: **3 passed**. The new offline integration tests
verify prefetch overlap, default deny, sequential chat speech/replay handling and
that Stop does not auto-restart prewarming.

Final focused voice/reference/clone-boundary regression: **42 passed**. The runtime
mechanical FX was applied to the preserved dry sample and compared against the
user-approved preview: **PCM bytes matched exactly**. This verifies that the live
style uses the accepted DSP settings rather than a newly approximated filter.

All 13 recorded private friend-voice assets remained unchanged; the supplied MP3
and pinned model hashes also remain unchanged. Optional diagnostic logs are used
only by the fixed-public-text verification script; ordinary app worker stderr is
suppressed. Existing Piper/Kokoro, Hermes and user frontend work were preserved.

Remaining work: user confirmation of the actual native face/audio experience,
broader device/long-response/soak testing, more clean reference material if higher
similarity is needed, reducing the lazy cold-load cost and GPU allocator reserve,
and the independent disabled-Qwen lifecycle failure. This is a working local
developer integration, not a portable production installer or an exact-identity
certification.
