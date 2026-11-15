import { describe, expect, it } from "vitest";
import type { Task, Transcript } from "../state";
import { greeting, summarize } from "./stats";

const task = (id: string, status: Task["status"]): Task => ({
  task_id: id,
  session_id: "s",
  request_id: id,
  status,
  input: { content: id },
});
const transcript = (
  status: Transcript["status"],
  latency?: number,
): Transcript => ({
  text: "",
  sequence: 1,
  status,
  events: [],
  ...(latency
    ? {
        metrics: {
          route_mode: "fast",
          calls: 1,
          latency_ms: latency,
          prompt_tokens: 10,
          completion_tokens: 5,
        },
      }
    : {}),
});

describe("summarize", () => {
  it("is empty without tasks", () => {
    const pulse = summarize([], {});
    expect(pulse.total).toBe(0);
    expect(pulse.successRate).toBeUndefined();
    expect(pulse.avgLatency).toBeUndefined();
  });
  it("uses live transcript status over the stored task status", () => {
    const pulse = summarize(
      [task("a", "running"), task("b", "succeeded"), task("c", "failed")],
      {
        a: transcript("succeeded", 1000),
        b: transcript("succeeded", 3000),
        c: transcript("failed"),
      },
    );
    expect(pulse).toMatchObject({
      total: 3,
      finished: 3,
      succeeded: 2,
      running: 0,
      successRate: 67,
      avgLatency: 2000,
      latencies: [1000, 3000],
      tokens: 30,
    });
  });
  it("counts running tasks", () => {
    expect(summarize([task("a", "running")], {}).running).toBe(1);
  });
});

describe("greeting", () => {
  it("follows the time of day", () => {
    expect(greeting(3)).toBe("Working late");
    expect(greeting(9)).toBe("Good morning");
    expect(greeting(14)).toBe("Good afternoon");
    expect(greeting(20)).toBe("Good evening");
  });
});
