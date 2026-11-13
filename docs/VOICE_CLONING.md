# Local cloned voice

P0 audit update: the existing isolated environment has unresolved package advisories.
The broker gate `EXPERIMENTAL_QWEN_TTS` defaults to false, and the installer requires
an explicit `-AllowExperimental` switch after review. Do not treat the historical
measurements below as security clearance or native end-to-end acceptance. Piper
LJ/Joe remain available, and the private source/profile have not been removed.
See [P0_AUDIT.md](phases/P0_AUDIT.md).

The user subsequently requested keeping Qwen disabled during dependency remediation.
See [QWEN_REMEDIATION.md](security/QWEN_REMEDIATION.md) for the full advisory register,
compatible candidate update, CPU-only profile checks and remaining failures. Do not
run the historical build/playback commands below as part of that security review.

Custom Friend Voice is an opt-in local clone. Hermes still writes the answer. Qwen3-TTS only speaks the user-facing text.

## What runs where

- Default voices stay on Piper inside the existing voice worker.
- The clone uses `Qwen/Qwen3-TTS-12Hz-0.6B-Base` revision `5d83992436eae1d760afd27aff78a71d676296fc` (Apache-2.0).
- Weights and inference live in `.venv-tts`, separate from the Hermes `.venv`.
- The desktop starts one worker process and reuses it. It is not started once per sentence.
- CUDA BF16 and PyTorch SDPA are required. If CUDA is missing, speech fails with a visible error and text chat continues. There is no silent CPU fallback.
- The model does not stream audio tokens. Completed sentences are synthesized in order, then played one at a time.

## Privacy

Reference audio, the transcript, `friend_voice.pt`, and consent live only in `%LOCALAPPDATA%\Immortility\voice`. Playback WAVs are deleted after they finish. Generated speech is not stored in chat history. Nothing is uploaded to Hugging Face or any voice API. The original `audio1.ogg` stays in `immortility's_voice` and that folder is gitignored.

`friend_voice.pt` is a dictionary of CPU tensors. It is loaded with `torch.load(..., weights_only=True)`. JSON metadata stores the model id, revision, package version, reference fingerprint, creation time, language, and format version. A checksum mismatch is treated as a corrupt profile.

The cloned voice stays off until you check **I have my friend's permission to use this cloned voice locally** and turn on **Speak assistant replies**. Delete custom voice removes the profile, the converted reference, the transcript, and that consent. It does not delete the original OGG.

The interface says when speech is using the cloned voice. The orb scales slightly with playback level and returns to idle when playback stops.

## Windows setup

From the repository root:

```powershell
# Experimental only, after dependency/security and speaker-authorization review:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-qwen-tts.ps1 -AllowExperimental
.\.venv-tts\Scripts\python.exe .\scripts\build-friend-voice.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Then open Settings, confirm permission, choose **Custom friend voice**, enable **Speak assistant replies**, and ask Hermes a question. **Test voice** speaks a fixed greeting. **Stop speaking** cancels playback and drops sentences that have not played. In-flight GPU work may finish, but its audio is discarded.

The first model load downloads the public weights into the local voice cache and can take several minutes. Later launches reuse `friend_voice.pt`.

## Transcript check

The supplied transcript is used. A local faster-whisper base pass on the 16 kb/s Opus file matched it except the last clause, which Whisper heard as "once the better time" instead of "one step at a time". That disagreement is stored in the profile metadata. Listening samples are not claimed to be a perfect match of the speaker.

## Measured on this RTX 4060 Laptop, 8 GB

These numbers are from the local run on 2026-11-13. They are not listening scores.

| Step | Result |
|---|---|
| Cold load, including the weight download | 196 s |
| Warm load from the local cache | 10.0 s |
| Saved profile load | 0.019 s |
| Greeting synthesis, 11 words, 6.6 s of audio | 23.5 s |
| Profile-build peak VRAM | 2.42 GB |
| Synthesis peak VRAM | 2.74 GB |
| VRAM still held while the model stays loaded | 2.18 GB |

The reference WAV is 19.54 s, 24 kHz, mono, peak 0.946, not clipped. The source OGG is 16 kb/s Opus, so the clone cannot recover detail that was never in the recording.

A local Whisper base pass on the three samples repeated the requested words. It heard the name Immortility as "immortality". That check does not prove the speaker matches your friend. Listen to the files in `%LOCALAPPDATA%\Immortility\voice\samples`.

## What was not verified in the desktop session

The worker, profile reload, broker tests, and desktop unit tests passed. The greeting WAV was played through the local speakers with the same playback function the broker uses: 133 blocks, peak level 0.146, and the level returned to zero. A full open-the-app, ask-Hermes, hear-it-in-the-window pass was not run in this session. In-flight GPU work is not cut off mid-forward; Stop speaking drops audio that has not started and any audio still being generated. SoX is not installed; reference conversion uses FFmpeg and the model reads WAV through soundfile. FlashAttention is not installed; inference uses PyTorch SDPA.
