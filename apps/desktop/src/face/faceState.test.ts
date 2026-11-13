import { describe, expect, it } from "vitest";
import type { LogEntry } from "../state";
import {
  agentStatuses,
  deriveFace,
  wantsOverlay,
  playbackEnergy,
} from "./faceState";

describe("playback-driven jaw", () => {
  it("closes on silence, stop and invalid meters and follows played amplitude", () => {
    expect(playbackEnergy(0, true)).toBe(0);
    expect(playbackEnergy(0.12, true)).toBeCloseTo(0.48);
    expect(playbackEnergy(0.4, true)).toBe(1);
    expect(playbackEnergy(0.4, false)).toBe(0);
    expect(playbackEnergy(Number.NaN, true)).toBe(0);
    expect(playbackEnergy(Infinity, true)).toBe(0);
  });
});

let sequence = 0;
function entry(type: string, data: LogEntry["data"]): LogEntry {
  sequence += 1;
  return { sequence, type, at: `2026-11-13T15:00:0${sequence % 10}Z`, data };
}
const base = {
  connected: true,
  text: "",
  voiceState: "IDLE",
  ttsState: "ready",
};

describe("deriveFace", () => {
  it("stays idle without a running task", () => {
    expect(deriveFace({ ...base, log: [] }).state).toBe("idle");
  });
  it("plans on a non-fast route and thinks on the fast route", () => {
    const planned = [entry("audit.notice", { route_mode: "standard" })];
    const fast = [entry("audit.notice", { route_mode: "fast" })];
    expect(deriveFace({ ...base, status: "running", log: planned }).state).toBe(
      "planning",
    );
    expect(deriveFace({ ...base, status: "running", log: fast }).state).toBe(
      "thinking",
    );
  });
  it("delegates only while a real agent event is open", () => {
    const started = [
      entry("agent.started", { role: "coding", status: "started" }),
    ];
    expect(deriveFace({ ...base, status: "running", log: started })).toEqual({
      state: "delegating",
      agent: "coding",
    });
    const done = [
      ...started,
      entry("agent.completed", { role: "coding", status: "succeeded" }),
    ];
    expect(deriveFace({ ...base, status: "running", log: done }).state).toBe(
      "thinking",
    );
  });
  it("shows tool execution, approval, response and error states", () => {
    const tool = [entry("tool.started", { name: "list" })];
    expect(deriveFace({ ...base, status: "running", log: tool }).state).toBe(
      "executing",
    );
    expect(
      deriveFace({ ...base, status: "awaiting_approval", log: [] }).state,
    ).toBe("awaiting");
    expect(
      deriveFace({ ...base, status: "running", log: [], text: "Hi" }).state,
    ).toBe("responding");
    expect(deriveFace({ ...base, status: "failed", log: [] }).state).toBe(
      "error",
    );
  });
  it("speaks only when the authorized voice runtime reports speaking", () => {
    expect(
      deriveFace({ ...base, status: "running", log: [], text: "Hello" }).state,
    ).not.toBe("speaking");
    expect(deriveFace({ ...base, log: [], ttsState: "speaking" }).state).toBe(
      "speaking",
    );
  });
  it("reports disconnected before task state", () => {
    expect(
      deriveFace({ ...base, connected: false, status: "running", log: [] })
        .state,
    ).toBe("disconnected");
  });
});

describe("agentStatuses", () => {
  it("marks agents off when delegation is disabled and ignores unknown roles", () => {
    const log = [
      entry("agent.started", { role: "automation", status: "started" }),
    ];
    const agents = agentStatuses(log, false);
    expect(agents.coding.status).toBe("off");
    expect(Object.keys(agents)).toEqual(["research", "coding", "review"]);
  });
});

describe("wantsOverlay", () => {
  it("collapses only for an open screen-control tool when the policy allows it", () => {
    const screen = [entry("tool.started", { name: "computer_use" })];
    expect(wantsOverlay(screen, "screen-control")).toBe(true);
    expect(wantsOverlay(screen, "never")).toBe(false);
    expect(
      wantsOverlay([entry("tool.started", { name: "read" })], "screen-control"),
    ).toBe(false);
    expect(
      wantsOverlay(
        [
          ...screen,
          entry("tool.completed", { name: "computer_use", status: "ok" }),
        ],
        "screen-control",
      ),
    ).toBe(false);
  });
});
