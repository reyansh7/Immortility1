import { describe, expect, it } from "vitest";
import { followRuntimeStatus, type RuntimeStatus } from "./runtimeStatus";

const snapshot = {
  revision: 0,
  health: {
    ready: false,
    hermes: { status: "missing" },
    providers: {},
    free_only: true,
    active_task: null,
  },
  voice_state: "IDLE",
} satisfies RuntimeStatus;
describe("read-only runtime subscription", () => {
  it("tracks revisions and resets correctly when a broker restarts", async () => {
    const controller = new AbortController();
    const paths: string[] = [];
    const seen: number[] = [];
    const revisions = [9, 10, 0];
    await followRuntimeStatus(
      controller.signal,
      (value) => {
        seen.push(value.revision);
        if (seen.length === 3) controller.abort();
      },
      () => {
        throw new Error("unexpected failure");
      },
      async (path) => {
        paths.push(path);
        return { ...snapshot, revision: revisions[paths.length - 1] };
      },
    );
    expect(paths).toEqual([
      "/v1/runtime/status",
      "/v1/runtime/status?after=9",
      "/v1/runtime/status?after=10",
    ]);
    expect(seen).toEqual([9, 10, 0]);
  });
  it("never publishes a late response after teardown", async () => {
    const controller = new AbortController();
    let calls = 0;
    await followRuntimeStatus(
      controller.signal,
      () => calls++,
      () => calls++,
      async () => {
        controller.abort();
        return snapshot;
      },
    );
    expect(calls).toBe(0);
  });
});
