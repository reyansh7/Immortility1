import { describe, expect, it } from "vitest";
import { sameStatus, type VoiceStatus } from "./useVoice";

const base = {
  state: "SPEAKING",
  level: 0.2,
  error: null,
  transcript: "",
  utterance_id: "u1",
  task_id: "t1",
  models_ready: true,
  preparing: false,
  latency_ms: {},
  profile_ready: false,
  tts_state: "speaking",
  tts_error: null,
  cloned_voice: false,
} as unknown as VoiceStatus;

describe("voice poll de-duplication", () => {
  it("ignores level-only changes so the app does not re-render", () => {
    expect(sameStatus(base, { ...base, level: 0.9 })).toBe(true);
  });
  it("still reports real state changes", () => {
    expect(sameStatus(base, { ...base, state: "IDLE" })).toBe(false);
    expect(sameStatus(base, { ...base, error: "boom" })).toBe(false);
  });
});
