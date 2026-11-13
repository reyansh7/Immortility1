import { describe as suite, expect, it } from "vitest";
import { parseBlocks } from "../Markdown";
import { redact, type Task, type Transcript } from "../state";
import { category, collect, describe } from "./Timeline";

const entry = (type: string, data: Record<string, string | number>) => ({
  sequence: 1,
  type,
  at: "2026-11-13T10:00:00Z",
  data,
});

suite("timeline", () => {
  it("names real broker events without inventing detail", () => {
    expect(describe(entry("agent.started", { role: "research" }))).toBe(
      "research agent started",
    );
    expect(
      describe(
        entry("tool.completed", { name: "read", status: "ok", path: "a.py" }),
      ),
    ).toBe("Tool read ok · a.py");
    expect(
      describe(
        entry("audit.notice", {
          route_mode: "fast",
          calls: 1,
          latency_ms: 900,
        }),
      ),
    ).toBe("Route fast · 1 calls · 900 ms");
    expect(
      describe(
        entry("audit.notice", {
          route_mode: "fast",
          model: "openrouter/free",
        }),
      ),
    ).toBe("Route plan fast · openrouter/free");
    expect(category("task.error")).toBe("error");
    expect(category("approval.requested")).toBe("approval");
    expect(category("artifact.created")).toBe("other");
  });

  it("merges task logs in time order and tags each entry with its task", () => {
    const tasks = [{ task_id: "b" }, { task_id: "a" }] as Task[];
    const log = (at: string, sequence: number) => ({
      sequence,
      type: "task.state",
      at,
      data: { status: "running" },
    });
    const transcripts = {
      a: { log: [log("2026-11-13T10:00:01Z", 2)] },
      b: {
        log: [log("2026-11-13T10:00:02Z", 1), log("2026-11-13T10:00:00Z", 3)],
      },
    } as unknown as Record<string, Transcript>;
    expect(collect(tasks, transcripts).map((row) => row.task_id)).toEqual([
      "b",
      "a",
      "b",
    ]);
  });

  it("drops unknown keys and secrets before display", () => {
    expect(
      redact({ message: "bad key sk-abcdefghijklmnop", hidden: "x", calls: 2 }),
    ).toEqual({ message: "bad key [redacted]", calls: 2 });
  });
});

suite("markdown", () => {
  it("parses fences, headings, lists and paragraphs", () => {
    const blocks = parseBlocks(
      "# Title\nSome *text*\n\n- one\n- two\n\n```ts\nconst a = 1;\n```\n> quoted",
    );
    expect(blocks.map((block) => block.kind)).toEqual([
      "heading",
      "paragraph",
      "list",
      "code",
      "quote",
    ]);
    expect(blocks[3]).toEqual({
      kind: "code",
      lang: "ts",
      text: "const a = 1;",
    });
  });

  it("keeps an unterminated fence as code instead of dropping text", () => {
    expect(parseBlocks("```\nstreaming")).toEqual([
      { kind: "code", lang: "", text: "streaming" },
    ]);
  });
});
