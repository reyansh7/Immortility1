import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Composer, Messages } from "./Conversation";
import type { Task } from "./state";

describe("rendered chat regressions", () => {
  it("requires separate report permission and hides it in local background mode", () => {
    const props = {
      input: "MCP report",
      setInput: () => {},
      consent: true,
      setConsent: () => {},
      running: false,
      canSend: true,
      onSend: () => {},
      onStop: () => {},
      toolsAvailable: true,
      artifactsAvailable: true,
      setToolConsent: () => {},
      setArtifactConsent: () => {},
    };
    const disabled = renderToStaticMarkup(
      <Composer {...props} toolConsent={false} />,
    );
    expect(disabled).toContain("Create an editable Markdown report and PDF");
    expect(disabled).toMatch(/type="checkbox" disabled=""/);
    const permissionInputs = disabled.match(/<input[^>]*>/g) ?? [];
    expect(permissionInputs.slice(0, 2).join("")).not.toContain('checked=""');
    const local = renderToStaticMarkup(<Composer {...props} localOnly />);
    expect(local).not.toContain("Create an editable Markdown report and PDF");
  });

  it("shows links only for verified published deliverables", () => {
    const task: Task = {
      task_id: "fixture",
      session_id: "s",
      request_id: "r",
      status: "succeeded",
      input: { content: "MCP report" },
      result: {
        text: "Created and verified.",
        provider: "openrouter",
        model: "openrouter/free",
        artifacts: [
          {
            artifact_id: "report.md",
            size: 1024,
            sha256: "0".repeat(64),
            verification: "reopened",
          },
          {
            artifact_id: "report.pdf",
            size: 2048,
            sha256: "1".repeat(64),
            verification: "reopened-and-rendered",
          },
        ],
      },
    };
    const html = renderToStaticMarkup(
      <Messages
        tasks={[task]}
        transcripts={{}}
        ready
        reduced
        onError={() => {}}
        onSpeak={() => {}}
      />,
    );
    expect(html).toContain("Open editable report");
    expect(html).toContain("Open PDF");
    expect(html).not.toContain("DOCX");
  });
  it("renders a visible failure body when a task has no answer or live transcript", () => {
    const task: Task = {
      task_id: "fixture",
      session_id: "s",
      request_id: "r",
      status: "failed",
      input: { content: "Hello" },
      error: {
        code: "hermes_failed",
        message: "Hermes could not complete this request.",
      },
    };
    const html = renderToStaticMarkup(
      <Messages
        tasks={[task]}
        transcripts={{}}
        ready
        reduced
        onError={() => {}}
        onSpeak={() => {}}
      />,
    );
    expect(html).toContain("Hermes could not complete this request.");
    expect(html).not.toContain("Waiting for Hermes");
    expect(html).not.toContain("Read aloud");
  });
  it("keeps local background results readable without unavailable voice or cloud controls", () => {
    const task: Task = {
      task_id: "fixture",
      session_id: "s",
      request_id: "r",
      status: "succeeded",
      input: { content: "Local check", no_cloud: true },
      result: {
        text: "Eight steps verified.",
        provider: "local",
        model: "workflow.local.v1",
      },
    };
    const html = renderToStaticMarkup(
      <Messages
        tasks={[task]}
        transcripts={{}}
        ready={false}
        localOnly
        reduced
        onError={() => {}}
        onSpeak={() => {}}
      />,
    );
    expect(html).toContain("Eight steps verified.");
    expect(html).not.toContain("Read aloud");
    const composer = renderToStaticMarkup(
      <Composer
        input=""
        setInput={() => {}}
        consent={false}
        setConsent={() => {}}
        running={false}
        canSend={false}
        onSend={() => {}}
        onStop={() => {}}
        localOnly
      />,
    );
    expect(composer).toContain("accepts local tasks only");
    expect(composer).not.toContain(
      "Send this conversation to the free cloud model",
    );
  });
});
