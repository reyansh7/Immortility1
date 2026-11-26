import { describe, expect, it } from "vitest";
import {
  MAX_EXPLAIN_CHARS,
  explainAvailable,
  explainRequest,
  pickExplainText,
} from "./explain";

describe("explain this", () => {
  it("prefers selection, then line, then word", () => {
    expect(
      pickExplainText({
        selection: " picked  text ",
        line: "a line",
        target: "w",
      }),
    ).toEqual({ ok: true, text: "picked text", from: "selection" });
    expect(pickExplainText({ line: "a line", target: "w" })).toMatchObject({
      text: "a line",
      from: "line",
    });
    expect(pickExplainText({ target: "word" })).toMatchObject({ from: "word" });
  });

  it("refuses protected windows and empty reads", () => {
    expect(pickExplainText({ denied: "password", line: "secret" }).ok).toBe(
      false,
    );
    expect(pickExplainText({ line: " " }).ok).toBe(false);
  });

  it("bounds the text", () => {
    const picked = pickExplainText({ line: "x".repeat(5000) });
    expect(picked.ok && picked.text.length).toBe(MAX_EXPLAIN_CHARS);
  });

  it("is local-only", () => {
    expect(explainAvailable(true, "local_qwen").ok).toBe(true);
    expect(explainAvailable(true, "auto_cloud").ok).toBe(false);
    expect(explainAvailable(false, "local_qwen").ok).toBe(false);
  });

  it("marks the task as screen-origin and personal", () => {
    const request = explainRequest("s1", "text");
    expect(request).toMatchObject({
      origin: "screen",
      privacy_class: "personal",
      cloud_consent: true,
      content: "text",
    });
    expect(request).not.toHaveProperty("allowed_capabilities");
  });
});
