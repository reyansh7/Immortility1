import { it, expect, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { connect, operation } from "./transport";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn(), Channel: class {} }));
it("allows only bounded read-only runtime revision requests", () => {
  expect(operation("/v1/runtime/status", false)).toEqual({
    operation: "runtime_status",
  });
  expect(operation("/v1/runtime/status?after=12", false)).toEqual({
    operation: "runtime_status",
    id: "12",
  });
  for (const path of [
    "/v1/runtime/status?after=-1",
    "/v1/runtime/status?after=9007199254740992",
    "/v1/runtime/status?after=../inference",
  ])
    expect(() => operation(path, false)).toThrow();
  expect(() => operation("/v1/runtime/status", true)).toThrow();
});

it("preserves safe native startup failures as visible recoverable errors", async () => {
  vi.mocked(invoke).mockRejectedValueOnce("Synthetic native startup failure.");
  await expect(connect()).rejects.toThrow("Synthetic native startup failure.");
  vi.mocked(invoke).mockRejectedValueOnce({ unexpected: "PRIVATE_CANARY" });
  await expect(connect()).rejects.toThrow("Unable to start local service.");
});
it("only admits enumerated local operations, never inference or arbitrary URLs", () => {
  expect(operation("/health/ready", false)).toEqual({ operation: "health" });
  for (const path of [
    "/inference/v1/chat/completions",
    "https://evil.test",
    "/v1/tasks/../../inference",
    "/v1/tools/terminal",
  ]) {
    expect(() => operation(path, true)).toThrow();
  }
});
it("restricts voice methods and validates scoped identifiers", () => {
  expect(operation("/v1/voice/status", false).operation).toBe("voice_status");
  expect(operation("/v1/voice/record", true).operation).toBe("voice_record");
  expect(() => operation("/v1/settings/provider-key", true)).toThrow();
  expect(
    operation("/v1/tasks/f0153ff9-a672-41b1-b490-0cea79542195/usage", false)
      .operation,
  ).toBe("task_usage");
  for (const [path, post] of [
    ["/v1/voice/status", true],
    ["/v1/voice/record", false],
    ["/v1/voice/speak/../../anything", true],
    ["/v1/voice/raw_capture", true],
  ] as const)
    expect(() => operation(path, post)).toThrow();
});
it("exposes only the typed model catalog and mode-setting operations", () => {
  expect(operation("/v1/models", false)).toEqual({
    operation: "model_catalog",
  });
  expect(operation("/v1/settings/model-mode", true)).toEqual({
    operation: "set_model_mode",
  });
  for (const [path, post] of [
    ["/v1/models", true],
    ["/v1/settings/model-mode", false],
    ["/v1/providers/credentials", false],
    ["https://api.groq.com/openai/v1", true],
  ] as const)
    expect(() => operation(path, post)).toThrow();
});
