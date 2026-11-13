# INFERNAL voice refinement — 14 November 2026

Status: **integrated, opt-in; local synthesis/playback/cancellation verified**.
User listening selection: **A — subtler metallic presence**, after comparing Onyx
and Fenrir and rejecting the first overly slow Onyx pair. **Default promotion is
not approved or performed.** `INFERNAL_VOICE_ENABLED=false` and
`EXPERIMENTAL_QWEN_TTS=false` were confirmed in the local application settings.
No Hermes, OpenMausBot, private cloned voice, source recording or consent record
was modified. Computer Use was not restarted.

## Reference interpretation and listening evidence

The target is an original intelligent American baritone, with a human performance
under a restrained mechanical texture. No actor embedding, actor recording,
film audio, conversion model or film dialogue was used. This is a style brief,
not a measured acoustic match to James Spader.

[Whedon's casting comments reported by ComingSoon](https://www.comingsoon.net/movies/news/108813-joss-whedon-talks-casting-james-spader-as-ultron)
describe a compelling, calmly unsettling voice with human humor and range. That
supports prioritizing performance rather than an extreme pitch/distortion filter.
The technical controls below follow the user's more specific listening feedback;
the interview is not evidence of any particular EQ curve or frequency target.

The preserved `data/previews/infernal/kokoro_george-infernal.wav` uses British
George, legacy -2.4 semitone processing and a steady rendering. Its autocorrelation
median voiced F0 was approximately 124 Hz. The American auditions used natural
pitch: Onyx approximately 89 Hz and Fenrir approximately 144 Hz. These estimates
are indicative and do not score richness, intelligibility, character or accent.
The user selected **Onyx as the leading foundation by listening**, then selected
the subtler revised A sample. Both American raw samples transcribed with zero word
errors in the fixed local test. Selection was not made by pitch or a cold-vs-warm
latency comparison.

Kokoro's [official voice inventory](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)
identifies `am_onyx`, `am_fenrir` and `bm_george`. Its
[pipeline source](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py)
supports speed and phoneme/text handling, not a reliable acting/emotion-tag API.
Phrase rate variation and modest gain emphasis are implemented. Sarcasm, menace,
word-level emotional emphasis and spontaneous human acting remain **limited,
not verified capabilities**. The system does not insert sarcastic words into an
assistant response or send new prompts to a cloud model to render this voice.

Follow-up web research requested by the user located:

1. [Marvel Entertainment: How James Spader Crafted Ultron](https://www.youtube.com/watch?v=sbe7-zit_x0),
   official performance featurette published 27 August 2015.
2. [SoundWorks Collection: The Sound of Avengers: Age of Ultron](https://vimeo.com/126456478),
   Michael Coleman's production interview with Christopher Boyes. The published
   description verifies its subject; no detailed DSP recipe was exposed by the
   available text. [Skywalker Sound's own credits](https://www.skysound.com/projects/averengers-age-of-ultron/)
   independently confirm Boyes and David Acord's sound-design roles.
3. [The Credits / Motion Picture Association](https://www.motionpictures.org/2015/04/from-spader-to-scarlett-5-great-voice-performances-in-sci-fi-films/),
   a firsthand film review describing articulated baritone, digital enhancement,
   wit and emotional variation. This corroborates a performance-first brief;
   it does not prescribe a particular filter implementation.

The web tool returned indexed video descriptions and article text, not perceptually
accessible streamed audio. **No claim of watching/hearing these videos, phonetic
accent measurement or reverse-engineering the film's effect chain is made.** The
American-English pronunciation target follows the user's brief and chosen Onyx
stock voice. A precise regional or Mid-Atlantic classification of the film voice
has not been verified. British George should not be substituted merely because
it sounds formal. No video was downloaded, converted, uploaded to another model
or used as a cloning/training reference. Further reference listening should focus
on diction, intra-sentence timing and emotional contrast; no new default was
changed based on inaccessible audio or a search snippet.

### User-provided local reference inspection

The user subsequently supplied `C:\Users\reyan\Downloads\now_im_free.mp3` for
inspection. It was decoded in memory with the existing PyAV stack and transcribed
with local CPU Whisper; no upload, synthesis, cloning or reference conversion file
was produced. The original SHA-256 remained
`d161839fe97adf85ded67ce74fbbe413f996bd4a11049276c5bbee5852ddff71`.

Decoded duration: 9.327 s, original 44.1 kHz stereo MP3. ASR estimated two speech
regions, 0.30–2.46 s and 4.26–8.54 s, approximately 1.8 s apart. The whole mix
continues through that speech gap. Approximately 58.72% of the measured spectral
power in active analysis frames is below 65 Hz, versus 0.77% for A, using the same
mono 16 kHz analysis and -20 dBFS normalization. This substantial low-frequency
content belongs to the complete recording; it cannot be attributed exclusively
to the vocal fundamental, acting or a particular effect. Ordinary silent-gap
metrics are misleading on this mixed reference. The pitch proxy was explicitly
rejected: only four resolved frames remained after rejecting boundary maxima.
No reliable vocal pitch, accent classification, perceptual similarity score or
film DSP recipe was inferred. These are local signal/transcription observations,
not a claim of auditory perception by the text tools.

The result supports treating the dramatic spacing and soundtrack separately from
the everyday assistant voice. It does not justify lowering Onyx further or adding
the recording's sub-bass to every spoken reply. Source file, preset defaults,
private voice assets and feature gates were not modified. The numerical report
is retained locally at `data/audits/ultron-reference-analysis.json`.

## Selected A design and integration

The optional `ultron_conversational` preset is labelled
**INFERNAL · conversational Onyx (A)** in voice settings. The default voice remains
LJ and existing saved preferences remain unchanged. The original natural,
cinematic, infernal and first Onyx presets remain available. B remains an audition,
not an automatically selected fallback.

- Stock Onyx, American pronunciation pipeline, natural pitch: **0 semitones**.
- Conversational rate near 1.0 with small clause variations; slight gain emphasis.
- Conservative generated-silence trimming, with quiet-consonant guards. No added
  silent delay on top of Kokoro's remaining normal sentence cadence.
- High-pass 65 Hz, a small 145 Hz support band, reduced 370 Hz congestion, presence
  at 2.8 kHz and a gentle positive shelf at 6 kHz. The earlier high-frequency
  darkening and larger bass boost are not used by the new clear baritone mode.
- Mild compression and low parallel saturation; dry speech stays dominant.
- Quiet 4.5 ms variable doubling plus 2.3/3.7/5.1 ms short comb coloration. A uses
  intensity 0.36, B 0.52, with effects strength 0.45. No long echoes/reverb, bit
  crushing, vocoder or actor cloning. No pitch shifting in either A/B candidate.
- All speech and DSP run locally on CPU. The persistent keyless audio worker is
  broker-owned, reused while warm, and released after idle polling observes 60 s
  inactivity. Explicit Stop immediately terminates that owned worker and clears
  the meter. No agent tool or independent planning loop was introduced.
- Actual processed PCM RMS drives the existing face jaw through the voice status
  meter; silent blocks and cancellation set energy to zero. Busy status polling
  is 80 ms, with the existing frame smoothing. This is amplitude animation,
  **not phoneme alignment**. Code/unit and real output-meter paths are verified;
  physical visual/audio synchronization in the native face view remains a manual
  acceptance gate. No native UI automation was restarted.

## Auditions, preservation and timing

All files below use the same public text: “All systems are online. I am ready to
assist. Give me a task, and I will handle it with precision. Your instructions
remain in control.” No model provider call is needed.

| Artifact | Duration | Internal measured sentence gaps | Local ASR word errors | Clipping |
|---|---:|---|---:|---:|
| `infernal-refinement/Current.wav` (byte copy of original George) | 10.075 s | reference retained | 0 | 0 |
| `infernal-refinement/Cinematic.wav` | 12.850 s | 1.08–1.21 s | 0 | 0 |
| `infernal-refinement/Ultron-Inspired.wav` | 12.925 s | 1.08–1.23 s | 0 | 0 |
| `infernal-refinement-v2/A-Subtle.wav`, B equivalent | 11.155 s | 0.76–0.98 s | 0 | 0 |
| **`infernal-refinement-v3/A-Subtle.wav`** | **10.075 s** | **0.42, 0.44, 0.58 s** | **0** | **0** |
| `infernal-refinement-v3/B-Colder.wav` | 10.075 s | 0.42, 0.44, 0.58 s | 0 | 0 |

The first timing correction failed the requested gap target; it is retained as
v2 evidence. V3 removes the extra inserted silence. Gap detection uses 10 ms RMS
frames below 0.003 (-50.5 dBFS), excluding outer silence. It is a repeatable quiet
gap proxy, not forced phonetic alignment or a guarantee for every future sentence.
Local Whisper CPU ASR is a clarity regression proxy, not proof of naturalness or
absence of audible processing artifacts. Human listening remains authoritative.

Final A/B use **one shared synthesized PCM performance**, identical words and
matched -20.00 dBFS RMS. Only metallic intensity differs. Peak levels are -1.74
and -1.71 dBFS, below the output ceiling. Original and intermediate files are
preserved; the generator refuses to overwrite a nonempty audition directory.

`scripts/check-voice-preservation.py` checked all **13** recorded private voice
assets: **0 missing/changed**. No private audio was decoded for these auditions.
Clone consent is no longer rewritten by unrelated public voice settings.

## Actual performance evidence

Machine-readable results remain local under `data/audits/` (ignored by Git):
`infernal-refinement-v3.json`, `infernal-refinement-v3-analysis.json` and
`infernal-refinement-v3-windows.json`. Historical Piper/George/Fable reports and
the earlier refinement reports remain available.

| Check | Observed |
|---|---|
| V3 synthesis, one shared performance | 20.376 s cold after Torch import; first chunk 16.005 s; CPU 24.391 core-seconds |
| Peak sampled working set, shared render | 1341.4 MiB; not a whole-system memory measurement |
| A DSP / B DSP | 14.599 ms / 12.045 ms for 10.075 s of PCM |
| Real Windows cold first audio, A | 16,877 ms |
| Real Windows warm first audio, B | 1519 ms |
| Real output driver buffer | 93.333 ms |
| Stop during actual V3 playback | 4.762 ms to owned process reaped + meter zero |
| Stop during fresh worker loading | 2.075 ms to owned process reaped + meter zero |
| Inference device | Explicit CPU; GPU utilization not instrumented |

Timing is not a p95 study. Hardware acoustic tail/loopback was not measured; the
driver's buffer and UI meter polling contribute delay beyond process cleanup.
Cold startup remains too slow for an everyday instant assistant. Keep the worker
warm only while opted in and active; a future separately benchmarked optimization
may examine lighter inference backends. Do not install a new GPU or conversion
stack merely to add repositories. Existing Piper is substantially lighter and
remains available. No automatic engine replacement occurred.

## Dependency, provenance and license review

Dedicated Python **3.12.14**, `.venv-infernal`, locked separately at
`integrations/infernal/uv.lock`. No production Python dependency update or Qwen
environment modification was required.

| Component | Installed version | Review |
|---|---|---|
| Kokoro / Misaki | 0.9.4 / 0.9.4 | Apache-2.0; official source examined for local loading and pronunciation setup |
| Pedalboard | 0.9.26 | GPLv3; native processing plus bundled third-party obligations |
| Piper | 1.8.0 | GPL-3.0-or-later; original LJ/Joe preserved |
| Torch | 2.15.0 Windows CPU wheel | Locked wheel SHA; no CUDA loading; weights-only deserialization in reviewed Kokoro loader |
| Transformers | 5.15.1 | Resolved and real Kokoro CPU inference exercised |
| NumPy / sounddevice | 2.5.4 / 0.5.6 | Locked numerical/audio stack; real Windows playback exercised |
| spaCy English model | en-core-web-sm 3.8.0 | MIT, official GitHub wheel locked by SHA; blocks Misaki runtime model auto-install |

`uv pip check` passed **101 distributions**. A frozen offline dry-run reports
**no changes**. `data/audits/infernal-packages.json` reports no known advisories
for the **100 indexed distributions**, and explicitly skips the GitHub-delivered
spaCy model because it is not indexed on PyPI. That skip is not represented as a
security pass. A dependency scan is not a source audit or an OS sandbox.

Public Kokoro model revision:
`f3ff3571791e39611d31c381e3a41a3af07b4987`. Public Piper revision:
`2f358b6a560e3a913ebf509b2f3344f20b367f94`. `config/infernal-models.json` pins
eight public artifacts (configuration, weights and stock voices), sizes and SHA-256.
Loading is local/offline with explicit CPU placement and restricted Torch loading.
No arbitrary remote model code is enabled. Worker environment forwards only the
small OS/runtime allowlist, no provider credentials or unrelated secrets.

Offline environment flags do not enforce Windows network isolation. The worker
has current-user filesystem permissions, and first-load hash checks do not solve
same-user artifact mutation/check-to-use races. OS sandboxing/read-only deployment
staging remains unimplemented; no stronger claim is made.

[Piper](https://github.com/OHF-Voice/piper1-gpl) and
[Pedalboard](https://github.com/spotify/pedalboard/blob/master/LICENSE) carry GPL
obligations. Pedalboard's bundled JUCE/Rubber Band/FFTW notices must accompany a
redistribution review. Northern English male's model card lists OpenSLR83,
CC-BY-SA-4.0, and Lessac fine-tuning provenance. Kokoro's
[model card](https://huggingface.co/hexgrad/Kokoro-82M) licenses weights under
Apache-2.0 and describes training/attribution; this is upstream provenance, not an
independent rights audit. Piper Alan was rejected because its linked dataset
license was not sufficiently permissive for this use. eSpeak NG is GPLv3; the
`espeakng-loader` wheel does not declare a license in its metadata, an unresolved
packaging/redistribution provenance gap. No public installer is being shipped.

[w-okada/voice-changer](https://github.com/w-okada/voice-changer) was not installed:
conversion adds a model/processing stage and reference/provenance complexity,
without a demonstrated advantage over stock Onyx plus local DSP for this task.

## Regression checks and remaining gates

- Focused voice/clone-boundary/refinement regressions: **40 passed**; no Qwen
  inference. Real CPU DSP contracts: **5 passed**, including retained quiet
  consonants/internal pauses, natural pitch, duration, finite/limited audio and
  silence. Strict mypy: **26 files passed**. New/changed voice Python Ruff passed.
- Frontend: **20 tests passed**, TypeScript/ESLint passed, production Vite build
  passed. Voice files' Prettier passed. Existing combined-tree formatting failures
  remain in other concurrently changed files; they were not mass-reformatted.
- Full broker checkpoint before the final preset registration: **112 passed,
  2 failed**. The same two failures reproduced serially: existing
  `test_tts_lifecycle` blocking-worker cancel/racing tests time out in Windows
  `taskkill /T`. Root worker fallback kills it but correctly reports that tree
  cleanup was not confirmed. These are not Qwen model tests and are not waived.
  The separate INFERNAL owned-process Stop tests pass. Qwen remains disabled.
- Final full broker checkpoint after optional A registration: **114 passed,
  1 failed** (`test_timeout_reaps_real_worker_and_releases_turn`). The same existing
  Windows cleanup failure returned `tts_failed` rather than the expected
  `voice_timeout`; the other two lifecycle tests happened to pass on this run.
  This variability does not clear the cleanup gate. No timeout was relaxed and
  no failure was skipped. Final frontend rerun: **20 passed**, production build
  passed with the previously recorded bundle warnings; final mypy **26 passed**.
- Existing Vite warnings: head scene both static/dynamic imported and main bundle
  over 500 kB. Not hidden by raising warning limits. Native face visual sync,
  driver loopback stop timing, multi-device testing and statistical performance
  testing remain open. No fresh native Tauri UI validation is claimed.

## Exact Windows commands

The current environment is already prepared. For another checkout, optional setup
downloads only the locked public runtime/models, without changing system Python,
PATH, registry, defaults or feature flags:

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-infernal.ps1
```

Validate without microphone or cloud requests:

```powershell
.\.venv-infernal\Scripts\python.exe .\scripts\verify-infernal-dsp.py
.\.venv\Scripts\python.exe .\scripts\analyze-infernal.py --ab
.\.venv\Scripts\python.exe .\scripts\check-voice-preservation.py
# Audible fixed public preview and real Stop; temporary settings, not promotion:
.\.venv\Scripts\python.exe .\scripts\verify-infernal-windows.py --ab
```

To opt in for one app launch after reviewing A (these commands have **not** been
run to change your live app):

```powershell
$env:INFERNAL_VOICE_ENABLED = 'true'
$env:EXPERIMENTAL_QWEN_TTS = 'false'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

In Settings, select **IMMORTILITY — INFERNAL**, then character **INFERNAL ·
conversational Onyx (A)**, then Test voice. Use Stop speaking/global Stop. No
microphone or cloud consent is needed for that fixed local preview. Close the app
and remove the shell opt-in to restore the gate:
`Remove-Item Env:INFERNAL_VOICE_ENABLED`.

The next acceptance step is the user's native in-app A playback/face/Stop check,
then explicit approval before any default promotion. Future expressive work must
be judged on ordinary assistant sentences, questions, lists and restrained dry
humor, without claiming unsupported emotion control or introducing a paid API.
