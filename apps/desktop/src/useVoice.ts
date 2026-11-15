import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { api } from "./transport";
import type { Task } from "./state";

export type VoiceState =
  | "IDLE"
  | "LISTENING"
  | "TRANSCRIBING"
  | "THINKING"
  | "SPEAKING"
  | "CANCELLED"
  | "ERROR";
export interface VoiceStatus {
  infernal_enabled?: boolean;
  reference_enabled?: boolean;
  reference_ready?: boolean;
  infernal_presets?: Record<string, Partial<VoiceOptions>>;
  experimental_qwen_enabled?: boolean;
  state: VoiceState;
  level: number;
  error: string | null;
  transcript: string;
  utterance_id: string | null;
  task_id: string | null;
  models_ready: boolean;
  preparing: boolean;
  latency_ms: Record<string, number>;
  diagnostic?: {
    operation?: string;
    stage?: string;
    device?: string;
    code?: string;
    elapsed_ms?: number;
    exit_code?: number;
  };
  profile_ready: boolean;
  tts_state: "cold" | "loading" | "ready" | "speaking" | "error";
  tts_error: string | null;
  cloned_voice: boolean;
  options?: VoiceOptions;
}
interface Device {
  id: number;
  name: string;
  host: string;
  input: boolean;
  output: boolean;
}
export interface VoiceOptions {
  input_device: number | null;
  output_device: number | null;
  language: string;
  stt_device: "cpu" | "auto";
  voice: "ljspeech" | "joe" | "friend" | "infernal" | "reference";
  infernal_base:
    | "piper_northern"
    | "kokoro_george"
    | "kokoro_fable"
    | "kokoro_onyx"
    | "kokoro_fenrir";
  voice_preset:
    | "natural"
    | "cinematic"
    | "infernal"
    | "cinematic_v2"
    | "ultron_inspired"
    | "ultron_conversational";
  resonance_style: "classic" | "baritone" | "clear_baritone";
  delivery: "steady" | "deliberate" | "conversational";
  pitch_semitones: number;
  robotic_intensity: number;
  effects_strength: number;
  speed: number;
  volume: number;
  response_length: "brief" | "normal" | "detailed";
  auto_speak: boolean;
  voice_output: boolean;
  clone_consent: boolean;
}
const defaults: VoiceOptions = {
  input_device: null,
  output_device: null,
  language: "en",
  stt_device: "cpu",
  voice: "ljspeech",
  infernal_base: "kokoro_george",
  voice_preset: "infernal",
  resonance_style: "classic",
  delivery: "steady",
  pitch_semitones: -2.4,
  robotic_intensity: 0.45,
  effects_strength: 0.6,
  speed: 1,
  volume: 0.7,
  response_length: "brief",
  auto_speak: true,
  voice_output: false,
  clone_consent: false,
};
/**
 * True when two polls differ only in playback level. The level is consumed by
 * the face through a ref, so these polls (every 80 ms while speaking) no
 * longer re-render the whole app.
 */
export function sameStatus(a: VoiceStatus, b: VoiceStatus): boolean {
  return (
    JSON.stringify({ ...a, level: 0 }) === JSON.stringify({ ...b, level: 0 })
  );
}

export function useVoice(
  session: string,
  cloudConsent: boolean,
  onTask: (task: Task) => void,
  onTranscript: (text: string) => void,
) {
  const level = useRef(0);
  const [status, setRawStatus] = useState<VoiceStatus>({
    state: "IDLE",
    level: 0,
    error: null,
    transcript: "",
    utterance_id: null,
    task_id: null,
    models_ready: false,
    preparing: false,
    latency_ms: {},
    profile_ready: false,
    tts_state: "cold",
    tts_error: null,
    cloned_voice: false,
  });
  const setStatus = useCallback(
    (next: VoiceStatus | ((previous: VoiceStatus) => VoiceStatus)) => {
      setRawStatus((previous) => {
        const fresh = typeof next === "function" ? next(previous) : next;
        // The face reads the level through this ref; idempotent, so safe
        // under StrictMode's double-invoked updaters.
        level.current = fresh.level;
        return sameStatus(previous, fresh) ? previous : fresh;
      });
    },
    [],
  );
  const [options, setOptions] = useState(defaults),
    [devices, setDevices] = useState<Device[]>([]),
    [micConsent, setMicConsent] = useState(false),
    [error, setError] = useState("");
  const callbacks = useRef({ onTask, onTranscript, session });
  callbacks.current = { onTask, onTranscript, session };
  const current = useRef(status);
  current.current = status;
  const taskSeen = useRef(""),
    transcriptSeen = useRef("");
  const pending = useRef<Promise<VoiceStatus> | null>(null);
  const hydrated = useRef(false);
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const fresh = await api<VoiceStatus>("/v1/voice/status");
        if (stopped) return;
        setStatus(fresh);
        if (!hydrated.current && fresh.options) {
          hydrated.current = true;
          setOptions(fresh.options);
        }
        if (fresh.task_id && fresh.task_id !== taskSeen.current) {
          taskSeen.current = fresh.task_id;
          const task = await api<Task>(`/v1/tasks/${fresh.task_id}`);
          if (!stopped && task.session_id === callbacks.current.session)
            callbacks.current.onTask(task);
        }
        if (
          fresh.state === "IDLE" &&
          !fresh.task_id &&
          fresh.transcript &&
          fresh.utterance_id !== transcriptSeen.current
        ) {
          transcriptSeen.current = fresh.utterance_id ?? "";
          callbacks.current.onTranscript(fresh.transcript);
        }
      } catch {
        /* Main connection status owns broker failures; recording is never retried. */
      }
      if (!stopped)
        timer = setTimeout(
          () => void poll(),
          ["IDLE", "ERROR", "CANCELLED"].includes(current.current.state) &&
            !current.current.preparing &&
            !["loading", "speaking"].includes(current.current.tts_state)
            ? 3000
            : 80,
        );
    }
    void poll();
    const listener = listen("global-stop", () => {
      setMicConsent(false);
      void api<VoiceStatus>("/v1/voice/cancel", {})
        .then(setStatus)
        .catch(() => {});
    });
    return () => {
      stopped = true;
      clearTimeout(timer);
      void listener.then((unlisten) => unlisten());
    };
  }, []);
  async function start() {
    if (!micConsent || !session || pending.current) return;
    setError("");
    const operation = api<VoiceStatus>("/v1/voice/record", {
      ...options,
      session_id: session,
      microphone_consent: true,
      cloud_consent: cloudConsent,
    });
    pending.current = operation;
    try {
      setStatus(await operation);
    } catch (issue) {
      setError(
        issue instanceof Error ? issue.message : "Unable to start microphone.",
      );
    } finally {
      pending.current = null;
    }
  }
  async function finish() {
    try {
      if (pending.current) await pending.current;
      setStatus(await api<VoiceStatus>("/v1/voice/finish", {}));
    } catch {
      /* start displays the error */
    }
  }
  async function cancel() {
    setMicConsent(false);
    setStatus((previous) => ({
      ...previous,
      state: "CANCELLED",
      tts_state: "cold",
      level: 0,
    }));
    try {
      setStatus(await api<VoiceStatus>("/v1/voice/cancel", {}));
    } catch {
      setError(
        "Voice stop could not reach the broker. Use the tray Stop action.",
      );
    }
  }
  async function prepare() {
    setError("");
    try {
      setStatus(await api<VoiceStatus>("/v1/voice/prepare", {}));
    } catch (issue) {
      setError(String(issue));
    }
  }
  async function refreshDevices() {
    try {
      setDevices(
        (await api<{ devices: Device[] }>("/v1/voice/devices")).devices,
      );
    } catch (issue) {
      setError(String(issue));
    }
  }
  async function updateOptions(next: VoiceOptions) {
    setOptions(next);
    try {
      const fresh = await api<VoiceStatus>("/v1/voice/options", next);
      setStatus(fresh);
    } catch (issue) {
      setError(
        issue instanceof Error
          ? issue.message
          : "Voice settings were rejected.",
      );
    }
  }
  async function preview() {
    setError("");
    try {
      setStatus(await api<VoiceStatus>("/v1/voice/preview", options));
    } catch (issue) {
      setError(
        issue instanceof Error ? issue.message : "Voice preview failed.",
      );
    }
  }
  async function deleteProfile() {
    setError("");
    try {
      const fresh = await api<VoiceStatus>("/v1/voice/profile/delete", {});
      setStatus(fresh);
      if (fresh.options) setOptions(fresh.options);
    } catch (issue) {
      setError(
        issue instanceof Error
          ? issue.message
          : "Could not delete the voice profile.",
      );
    }
  }
  async function speak(taskId: string) {
    try {
      setStatus(await api<VoiceStatus>(`/v1/voice/speak/${taskId}`, options));
    } catch (issue) {
      setError(String(issue));
    }
  }
  return {
    status,
    /** Latest playback/mic level, updated without re-rendering. */
    level,
    options,
    setOptions: updateOptions,
    preview,
    deleteProfile,
    devices,
    micConsent,
    setMicConsent,
    error,
    start,
    finish,
    cancel,
    prepare,
    refreshDevices,
    speak,
  };
}
export type VoiceController = ReturnType<typeof useVoice>;
