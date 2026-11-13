import type { VoiceController } from "./useVoice";
export function VoiceControls({
  voice,
  settings = false,
}: {
  voice: VoiceController;
  settings?: boolean;
}) {
  const { status, options, setOptions } = voice;
  const active = !["IDLE", "ERROR", "CANCELLED"].includes(status.state);
  return (
    <section className="voice-controls" aria-label="Local voice">
      <div className="voice-status" aria-live="polite">
        <span className={status.state === "LISTENING" ? "capture-dot" : ""} />
        {status.cloned_voice
          ? "speaking · cloned voice"
          : status.tts_state === "loading"
            ? "loading voice engine"
            : status.state === "LISTENING"
              ? "MICROPHONE ON · local capture"
              : status.state.toLowerCase()}{" "}
        · audio stays local
      </div>
      {(voice.error || status.error || status.tts_error) && (
        <p role="alert" className="error">
          {voice.error || status.error || status.tts_error}
        </p>
      )}
      {settings && (
        <>
          {!status.experimental_qwen_enabled && (
            <p className="hint">
              Experimental Qwen speech is gated off pending security and native
              verification. LJ and Joe use local Piper.
            </p>
          )}
          <p>
            Local speech stays on this PC. Default voices use Piper. Custom
            Friend Voice uses Qwen3-TTS and a saved clone of the authorized
            reference recording. Wake word and continuous listening are off.
          </p>
          <button
            onClick={() => void voice.refreshDevices()}
            disabled={active || status.preparing}
          >
            Refresh audio devices
          </button>
          <label>
            Microphone
            <select
              value={options.input_device ?? ""}
              onChange={(e) =>
                setOptions({
                  ...options,
                  input_device:
                    e.target.value === "" ? null : Number(e.target.value),
                })
              }
            >
              <option value="">System default</option>
              {voice.devices
                .filter((d) => d.input)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} · {d.host}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Speaker
            <select
              value={options.output_device ?? ""}
              onChange={(e) =>
                setOptions({
                  ...options,
                  output_device:
                    e.target.value === "" ? null : Number(e.target.value),
                })
              }
            >
              <option value="">System default</option>
              {voice.devices
                .filter((d) => d.output)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} · {d.host}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Language
            <select
              value={options.language}
              onChange={(e) =>
                setOptions({ ...options, language: e.target.value })
              }
            >
              {[
                ["en", "English"],
                ["hi", "Hindi"],
                ["es", "Spanish"],
                ["fr", "French"],
                ["de", "German"],
                ["ja", "Japanese"],
                ["auto", "Detect language"],
              ].map(([value, name]) => (
                <option key={value} value={value}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Voice output
            <input
              type="checkbox"
              checked={options.voice_output}
              onChange={(e) =>
                setOptions({ ...options, voice_output: e.target.checked })
              }
            />
            Speak assistant replies
          </label>
          <label>
            <input
              type="checkbox"
              checked={options.clone_consent}
              onChange={(e) =>
                setOptions({
                  ...options,
                  clone_consent: e.target.checked,
                  voice: e.target.checked ? options.voice : "ljspeech",
                })
              }
            />
            I have my friend's permission to use this cloned voice locally
          </label>
          <label>
            Voice
            <select
              value={options.voice}
              onChange={(e) => {
                const friend = e.target.value === "friend";
                if (friend && !options.clone_consent) return;
                setOptions({
                  ...options,
                  voice: e.target.value as typeof options.voice,
                });
              }}
            >
              <option value="ljspeech">LJ · Piper</option>
              <option value="joe">Joe · Piper male</option>
              <option value="infernal" disabled={!status.infernal_enabled}>
                IMMORTILITY — INFERNAL · optional
              </option>
              <option
                value="friend"
                disabled={
                  !options.clone_consent || !status.experimental_qwen_enabled
                }
              >
                Custom friend voice
              </option>
            </select>
          </label>
          {options.voice === "infernal" && (
            <fieldset>
              <legend>Original robotic baritone</legend>
              <label>
                Voice source
                <select
                  value={options.infernal_base}
                  disabled={active}
                  onChange={(e) =>
                    setOptions({
                      ...options,
                      infernal_base: e.target
                        .value as typeof options.infernal_base,
                    })
                  }
                >
                  <option value="piper_northern">
                    Piper · Northern British male
                  </option>
                  <option value="kokoro_george">Kokoro · British George</option>
                  <option value="kokoro_fable">Kokoro · British Fable</option>
                  <option value="kokoro_onyx">Kokoro · American Onyx</option>
                  <option value="kokoro_fenrir">
                    Kokoro · American Fenrir
                  </option>
                </select>
              </label>
              <label>
                Character
                <select
                  value={options.voice_preset}
                  disabled={active}
                  onChange={(e) => {
                    const preset = e.target
                      .value as typeof options.voice_preset;
                    setOptions({
                      ...options,
                      ...status.infernal_presets?.[preset],
                      voice_preset: preset,
                    });
                  }}
                >
                  <option value="natural">Natural</option>
                  <option value="cinematic">Cinematic</option>
                  <option value="infernal">Infernal</option>
                  <option value="cinematic_v2">
                    Cinematic · natural baritone
                  </option>
                  <option value="ultron_inspired">
                    Ultron-inspired · original baritone
                  </option>
                  <option value="ultron_conversational">
                    INFERNAL · conversational Onyx (A)
                  </option>
                </select>
              </label>
              <label>
                Pitch · {options.pitch_semitones.toFixed(1)} semitones
                <input
                  type="range"
                  min="-6"
                  max="2"
                  step="0.1"
                  disabled={active}
                  value={options.pitch_semitones}
                  onChange={(e) =>
                    setOptions({
                      ...options,
                      pitch_semitones: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Robotic intensity ·{" "}
                {Math.round(options.robotic_intensity * 100)}%
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  disabled={active}
                  value={options.robotic_intensity}
                  onChange={(e) =>
                    setOptions({
                      ...options,
                      robotic_intensity: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Effects strength · {Math.round(options.effects_strength * 100)}%
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  disabled={active}
                  value={options.effects_strength}
                  onChange={(e) =>
                    setOptions({
                      ...options,
                      effects_strength: Number(e.target.value),
                    })
                  }
                />
              </label>
              <p className="hint">
                Stock licensed TTS voices with original effects. New baritone
                presets keep natural pitch and use deliberate phrase timing. No
                actor imitation or voice cloning. Test voice previews the
                current settings; stop before retuning.
              </p>
            </fieldset>
          )}
          {options.voice === "friend" && (
            <p className="hint">
              Speaking with the cloned voice from the local reference recording,
              played at 1.3×. This is synthetic speech, not a live person.
            </p>
          )}
          {options.voice !== "friend" && (
            <label>
              Speech speed
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={options.speed}
                onChange={(e) =>
                  setOptions({ ...options, speed: Number(e.target.value) })
                }
              />
              {options.speed}×
            </label>
          )}
          <label>
            Volume
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={options.volume}
              onChange={(e) =>
                setOptions({ ...options, volume: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Response length
            <select
              value={options.response_length}
              onChange={(e) =>
                setOptions({
                  ...options,
                  response_length: e.target.value as
                    "brief" | "normal" | "detailed",
                })
              }
            >
              <option value="brief">Brief conversation</option>
              <option value="normal">Normal</option>
              <option value="detailed">Detailed</option>
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={options.auto_speak}
              onChange={(e) =>
                setOptions({ ...options, auto_speak: e.target.checked })
              }
            />
            Speak voice replies
          </label>
          <label>
            <input
              type="checkbox"
              checked={options.stt_device === "auto"}
              onChange={(e) =>
                setOptions({
                  ...options,
                  stt_device: e.target.checked ? "auto" : "cpu",
                })
              }
            />
            Try compatible GPU; otherwise CPU
          </label>
          <p className="hint">
            Piper code is GPL-3.0. LJ Speech is public domain; Joe’s dataset is
            CC0. Qwen3-TTS weights are Apache-2.0 and stay on this computer. The
            reference recording and voice profile are never uploaded.
          </p>
          <button
            type="button"
            onClick={() => void voice.preview()}
            disabled={active}
          >
            Test voice
          </button>
          <button
            type="button"
            onClick={() => void voice.deleteProfile()}
            disabled={active || !status.profile_ready}
          >
            Delete custom voice
          </button>
        </>
      )}
      {!status.models_ready && (
        <button
          onClick={() => void voice.prepare()}
          disabled={status.preparing || active}
        >
          {status.preparing
            ? "Downloading local models…"
            : "Download local voice models"}
        </button>
      )}
      <label className="mic-consent">
        <input
          type="checkbox"
          checked={voice.micConsent}
          onChange={(e) => {
            voice.setMicConsent(e.target.checked);
            if (!e.target.checked) void voice.cancel();
          }}
        />
        Allow microphone while holding push-to-talk
      </label>
      <div className="voice-actions">
        <button
          type="button"
          disabled={
            !voice.micConsent ||
            !status.models_ready ||
            status.preparing ||
            ["TRANSCRIBING", "THINKING"].includes(status.state)
          }
          onPointerDown={(e) => {
            e.preventDefault();
            e.currentTarget.setPointerCapture(e.pointerId);
            void voice.start();
          }}
          onPointerUp={() => void voice.finish()}
          onPointerCancel={() => void voice.cancel()}
          onKeyDown={(e) => {
            if (e.code === "Space" && !e.repeat) {
              e.preventDefault();
              void voice.start();
            }
          }}
          onKeyUp={(e) => {
            if (e.code === "Space") {
              e.preventDefault();
              void voice.finish();
            }
          }}
        >
          Hold to talk
        </button>
        <button
          type="button"
          onClick={() => void voice.preview()}
          disabled={active}
        >
          Test voice
        </button>
        <button
          type="button"
          onClick={() => void voice.cancel()}
          disabled={!active && !status.preparing && status.state !== "SPEAKING"}
        >
          Stop speaking
        </button>
      </div>
      <p className="hint">
        Hold Space on the button or press and hold. Releases after 30 seconds
        maximum. Without cloud-text consent, transcription fills the composer
        for review.
      </p>
    </section>
  );
}
