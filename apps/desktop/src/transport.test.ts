import { it, expect } from "vitest";
import { operation } from "./transport";
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
  expect(operation("/v1/settings/provider-key", true).operation).toBe(
    "save_provider_key",
  );
  for (const [path, post] of [
    ["/v1/voice/status", true],
    ["/v1/voice/record", false],
    ["/v1/voice/speak/../../anything", true],
    ["/v1/voice/raw_capture", true],
  ] as const)
    expect(() => operation(path, post)).toThrow();
});
