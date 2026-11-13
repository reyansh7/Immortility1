import { describe, it, expect } from "vitest";
import { reduceEvent, orbState, type Transcript } from "./state";
describe("durable event presentation", () => {
  it("does not duplicate replayed deltas", () => {
    const initial: Transcript = {
      text: "",
      sequence: 0,
      status: "created",
      events: [],
    };
    const event = {
      schema_version: "1.0" as const,
      task_id: "t",
      sequence: 1,
      type: "message.delta",
      data: { text: "hello" },
    };
    const once = reduceEvent(initial, event);
    expect(reduceEvent(once, event).text).toBe("hello");
  });
  it("keeps partial output when cancelled", () => {
    const state: Transcript = {
      text: "partial",
      sequence: 1,
      status: "running",
      events: [],
    };
    const next = reduceEvent(state, {
      schema_version: "1.0",
      task_id: "t",
      sequence: 2,
      type: "task.state",
      data: { status: "cancelled" },
    });
    expect(next.status).toBe("cancelled");
    expect(next.text).toBe("partial");
  });
  it("records specialist status only from agent events", () => {
    const initial: Transcript = {
      text: "",
      sequence: 0,
      status: "created",
      events: [],
    };
    const next = reduceEvent(initial, {
      schema_version: "1.0",
      task_id: "t",
      sequence: 1,
      type: "agent.started",
      data: { role: "research", status: "started" },
    });
    expect(next.events).toEqual(["research started"]);
  });
  it("shows disconnects and errors without invented activity", () => {
    expect(orbState(undefined, false)).toBe("disconnected");
    expect(orbState("blocked", true)).toBe("error");
    expect(orbState("running", true)).toBe("thinking");
    expect(orbState("succeeded", true)).toBe("idle");
  });
});
