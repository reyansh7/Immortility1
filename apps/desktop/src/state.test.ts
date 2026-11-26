import { describe, it, expect } from "vitest";
import { reduceEvent, orbState, type Transcript } from "./state";
describe("durable event presentation", () => {
  it("isolates task streams and rejects invalid state or sequence updates", () => {
    const initial: Transcript = {
      task_id: "task-a",
      text: "local",
      sequence: 2,
      status: "running",
      events: [],
    };
    for (const event of [
      {
        task_id: "task-b",
        sequence: 99,
        type: "task.state",
        data: { status: "succeeded" },
      },
      {
        task_id: "task-a",
        sequence: NaN,
        type: "task.state",
        data: { status: "succeeded" },
      },
      {
        task_id: "task-a",
        sequence: 3,
        type: "task.state",
        data: { status: "invented" },
      },
    ])
      expect(reduceEvent(initial, { schema_version: "1.0", ...event })).toBe(
        initial,
      );
  });
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
  it("keeps identical text from distinct events and drops a replay", () => {
    const initial: Transcript = {
      text: "",
      sequence: 0,
      status: "running",
      events: [],
    };
    const delta = (sequence: number) => ({
      schema_version: "1.0" as const,
      task_id: "t",
      sequence,
      type: "message.delta",
      data: { text: "Simulated duplicate." },
    });
    const twice = reduceEvent(reduceEvent(initial, delta(1)), delta(2));
    expect(twice.text).toBe("Simulated duplicate.Simulated duplicate.");
    expect(reduceEvent(twice, delta(2)).text).toBe(twice.text);
    expect(reduceEvent(twice, delta(1)).text).toBe(twice.text);
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
  it("keeps a requested stop active until the broker confirms it", () => {
    expect(orbState("stopping", true)).toBe("thinking");
    expect(orbState("cancelled", true)).toBe("idle");
  });
});
