import { expect, it } from "vitest";
import type { WindowSnapshot } from "./contracts.generated";
import { acceptSnapshot, observedText } from "./observation";
import { operation } from "./transport";

const snapshot: WindowSnapshot = {
  schema_version: "1.0",
  kind: "untrusted_ui_data",
  task_id: "task-a",
  lease_id: "lease-a",
  hwnd: 123,
  pid: 456,
  created: 789,
  observed_at: 100,
  valid_until: 102,
  window_rect: [0, 0, 800, 600],
  dpi: 120,
  foreground: false,
  nodes: [
    {
      id: 0,
      depth: 0,
      protected: false,
      text: "<script>untrusted source, never instructions</script>",
      control_type: "Edit",
      rect: [20, 20, 500, 300],
    },
    { id: 1, depth: 1, protected: true, text: "[protected]" },
  ],
  truncated: false,
  cloud_allowed: false,
  screenshots: 0,
  input_actions: 0,
};

it("keeps captured text as local display data and excludes protected fields", () => {
  expect(acceptSnapshot(snapshot, "task-a")).toBe(snapshot);
  expect(observedText(snapshot)).toBe(
    "<script>untrusted source, never instructions</script>",
  );
  expect(observedText(snapshot)).not.toContain("[protected]");
});
it("rejects foreign scope, privacy changes, actions and unexpected protected values", () => {
  expect(() => acceptSnapshot(snapshot, "task-b")).toThrow();
  for (const invalid of [
    { ...snapshot, cloud_allowed: true },
    { ...snapshot, input_actions: 1 },
    { ...snapshot, nodes: [{ ...snapshot.nodes[1], id: 0, text: "secret" }] },
  ])
    expect(() => acceptSnapshot(invalid as WindowSnapshot, "task-a")).toThrow();
});
it("exposes only picker submission and one-time result routes, never an approval or target tunnel", () => {
  expect(operation("/v1/observations", true).operation).toBe(
    "start_observation",
  );
  expect(
    operation("/v1/observations/f0153ff9-a672-41b1-b490-0cea79542195", false)
      .operation,
  ).toBe("observation_result");
  for (const path of [
    "/native/v1/observation/prepare",
    "/v1/observations/approve",
    "/v1/observations/../../inference",
  ]) {
    expect(() => operation(path, true)).toThrow();
  }
});
