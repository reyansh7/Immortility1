import { describe, expect, it } from "vitest";
import { hudItems } from "./StatusHud";

const base = { presence: "Ready", connected: true };
const pick = (items: ReturnType<typeof hudItems>, key: string) =>
  items.find((item) => item.key === key)!;

describe("status HUD", () => {
  it("is calm when nothing is live", () => {
    const items = hudItems(base);
    expect(items.map((item) => item.level)).toEqual([
      "on",
      "off",
      "off",
      "off",
      "off",
    ]);
    expect(pick(items, "cursor").value).toBe("Yours");
  });

  it("shows the microphone only while it is really listening", () => {
    expect(
      pick(hudItems({ ...base, voiceState: "LISTENING" }), "mic"),
    ).toMatchObject({
      value: "Listening",
      level: "live",
    });
    expect(
      pick(hudItems({ ...base, voiceState: "SPEAKING" }), "mic").level,
    ).toBe("on");
  });

  it("flags screen reading, pointer control and local model", () => {
    const items = hudItems({
      ...base,
      screenReading: "Reading window text",
      pointer: "moving",
      route: "local_qwen",
    });
    expect(pick(items, "screen").level).toBe("live");
    expect(pick(items, "cursor")).toMatchObject({
      value: "Moving",
      level: "live",
    });
    expect(pick(items, "model")).toMatchObject({ value: "Local", level: "on" });
  });

  it("warns when disconnected", () => {
    expect(
      pick(hudItems({ presence: "Offline", connected: false }), "system").level,
    ).toBe("warn");
  });
});
