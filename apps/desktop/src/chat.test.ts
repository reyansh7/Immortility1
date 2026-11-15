import { describe, expect, it, vi } from "vitest";
import { followTask, reconcileTask, taskOutcome, taskStatus } from "./chat";
import {
  reduceEvent,
  type Task,
  type Transcript,
  type TaskEvent,
} from "./state";

const task: Task = {
  task_id: "a",
  session_id: "s",
  request_id: "r",
  status: "running",
  input: { content: "fixture" },
};
const blank: Transcript = {
  task_id: "a",
  text: "",
  sequence: 0,
  status: "running",
  events: [],
};
const event = (sequence: number, text: string): TaskEvent => ({
  schema_version: "1.0",
  task_id: "a",
  sequence,
  type: "message.delta",
  data: { text },
});

describe("chat outcomes and recovery", () => {
  it("shows a meaningful visible outcome for every empty terminal task", () => {
    for (const status of [
      "failed",
      "blocked",
      "rate_limited",
      "disconnected",
      "cancelled",
      "succeeded",
    ] as const) {
      const outcome = taskOutcome({ ...task, status }, blank);
      expect(outcome.status).toBe(status);
      expect(outcome.notice?.length).toBeGreaterThan(20);
      expect(outcome.text).toBe("");
    }
  });
  it("keeps a partial answer and a classified failure visible", () => {
    const outcome = taskOutcome(
      {
        ...task,
        status: "failed",
        error: { code: "timeout", message: "Provider timed out." },
      },
      { ...blank, text: "Partial" },
    );
    expect(outcome.text).toBe("Partial");
    expect(outcome.notice).toBe("Provider timed out.");
  });
  it("prefers the final stored answer and status over replayed running state", () => {
    const final: Task = {
      ...task,
      status: "succeeded",
      result: { text: "Stored", provider: "fixture", model: "fixture" },
    };
    expect(taskStatus(final, blank)).toBe("succeeded");
    expect(reconcileTask({ ...blank, text: "Part" }, final).text).toBe(
      "Stored",
    );
    expect(taskOutcome(final, blank).notice).toBeUndefined();
    expect(
      taskOutcome(
        { ...final, result: { ...final.result!, text: "" } },
        { ...blank, text: "Old" },
      ).notice,
    ).toContain("without a displayable answer");
    expect(reconcileTask(blank, { ...final, task_id: "foreign" })).toBe(blank);
  });
  it("retrieves a failed final task after SSE drops without resubmitting inference", async () => {
    const final: Task = {
      ...task,
      status: "failed",
      error: { code: "hermes_failed", message: "Hermes failed." },
    };
    const transport = {
      stream: vi.fn().mockRejectedValue(new Error("connection lost")),
      task: vi.fn().mockResolvedValue(final),
    };
    const onTask = vi.fn();
    await followTask(
      task,
      transport,
      vi.fn(),
      onTask,
      new AbortController().signal,
    );
    expect(transport.stream).toHaveBeenCalledTimes(1);
    expect(transport.task).toHaveBeenCalledTimes(1);
    expect(onTask).toHaveBeenCalledWith(final);
  });
  it("resumes at the last cursor and ignores duplicate and foreign events", async () => {
    let live = blank;
    const transport = {
      stream: vi
        .fn()
        .mockImplementationOnce(async (_after, onEvent) => {
          onEvent(event(1, "Hel"));
          throw new Error("lost");
        })
        .mockImplementationOnce(async (after, onEvent) => {
          expect(after).toBe(1);
          onEvent(event(1, "duplicate"));
          onEvent({ ...event(100, "foreign"), task_id: "other" });
          onEvent(event(2, "lo"));
        }),
      task: vi
        .fn()
        .mockResolvedValueOnce(task)
        .mockResolvedValueOnce({ ...task, status: "succeeded" }),
    };
    await followTask(
      task,
      transport,
      (e) => {
        live = reduceEvent(live, e);
      },
      vi.fn(),
      new AbortController().signal,
    );
    expect(live.text).toBe("Hello");
    expect(live.sequence).toBe(2);
  });
  it("bounds recovery and rejects mismatched session metadata", async () => {
    const onTask = vi.fn();
    const transport = {
      stream: vi.fn().mockRejectedValue(new Error("lost")),
      task: vi.fn().mockResolvedValue({
        ...task,
        status: "succeeded",
        session_id: "foreign",
      }),
    };
    await expect(
      followTask(
        task,
        transport,
        vi.fn(),
        onTask,
        new AbortController().signal,
      ),
    ).rejects.toThrow("not resubmitted");
    expect(transport.stream).toHaveBeenCalledTimes(3);
    expect(onTask).not.toHaveBeenCalled();
  });
  it("does not fetch or update a stale task after cancellation or session change", async () => {
    const controller = new AbortController();
    const transport = {
      stream: vi.fn().mockImplementation(async () => {
        controller.abort();
      }),
      task: vi.fn(),
    };
    const onTask = vi.fn();
    await followTask(task, transport, vi.fn(), onTask, controller.signal);
    expect(transport.task).not.toHaveBeenCalled();
    expect(onTask).not.toHaveBeenCalled();
  });
});
