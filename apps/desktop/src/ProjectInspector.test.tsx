import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ProjectInspector, ProjectResults } from "./ProjectInspector";
import {
  ProjectInspection,
  projectRequest,
  type ProjectResult,
} from "./projectInspection";
import type { Task, TaskEvent } from "./state";

const scope = {
  available: true,
  scope_id: "a".repeat(64),
  folder_name: "Synthetic project",
};
const other = {
  ...scope,
  scope_id: "b".repeat(64),
  folder_name: "Other fixture",
};
const read: ProjectResult = {
  scope_id: scope.scope_id,
  source_trust: "untrusted-data",
  truncated: false,
  path: "src/app.tsx",
  text: "<script>never executed</script>",
  sha256: "c".repeat(64),
  start_line: 1,
  end_line: 1,
};
const search: ProjectResult = {
  scope_id: scope.scope_id,
  source_trust: "untrusted-data",
  truncated: false,
  hits: [
    {
      path: "src/app.tsx",
      line: 8,
      text: "export const answer = 42;",
      sha256: "c".repeat(64),
    },
  ],
  files_scanned: 2,
  skipped_files: 1,
};
const task: Task = {
  task_id: "a0000000-0000-0000-0000-000000000000",
  session_id: "session",
  request_id: "fixture",
  status: "running",
  input: { content: "Local project inspection", no_cloud: true },
};
function finished(output = search): Task {
  return {
    ...task,
    status: "succeeded",
    result: {
      text: "Validated local read",
      provider: "local",
      model: "workflow.local.v1",
      steps: { inspect: output },
    } as Task["result"],
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}
function fixture() {
  const calls: { path: string; body?: unknown }[] = [];
  let currentScope = scope,
    finalTask = finished(),
    serial = 0;
  let handler: ((path: string, body?: unknown) => Promise<unknown>) | undefined;
  const streaming = vi.fn<
    (
      id: string,
      after: number,
      event: (event: TaskEvent) => void,
      signal: AbortSignal,
    ) => Promise<void>
  >(async () => {});
  const model = new ProjectInspection("session", {
    request: async <T,>(path: string, body?: unknown): Promise<T> => {
      calls.push({ path, body });
      if (handler) return (await handler(path, body)) as T;
      if (path === "/v1/projects/scope") return currentScope as T;
      if (path === "/v1/settings/project")
        return (
          (body as { enabled: boolean }).enabled
            ? currentScope
            : { available: false, scope_id: null, folder_name: null }
        ) as T;
      if (path === "/v1/workflows") return task as T;
      if (path.endsWith("/cancel"))
        return { ...task, status: "cancelled" } as T;
      return finalTask as T;
    },
    stream: streaming,
    requestId: () => `request-${++serial}`,
  });
  return {
    model,
    calls,
    streaming,
    setScope: (value: typeof scope) => {
      currentScope = value;
    },
    setFinal: (value: Task) => {
      finalTask = value;
    },
    setHandler: (value: typeof handler) => {
      handler = value;
    },
    posts: () => calls.filter((c) => c.path === "/v1/workflows"),
  };
}

describe("Project Inspector behavior against broker contracts", () => {
  it("starts without consent/content and blocks disconnected operations", async () => {
    const f = fixture();
    await f.model.select(true, "fixture");
    await f.model.inspect("search", "answer");
    expect(f.calls).toHaveLength(0);
    const html = renderToStaticMarkup(
      <ProjectInspector session="session" connected={false} busy={false} />,
    );
    expect(html).toContain("No project read permission");
    expect(html).toContain("disabled");
    expect(html).not.toContain('checked=""');
  });
  it("requires view consent and creates an exact local-only search", async () => {
    const f = fixture();
    await f.model.connect(true);
    await f.model.inspect("search", "answer");
    expect(f.posts()).toHaveLength(0);
    f.model.consent(true);
    await f.model.inspect("search", "answer");
    expect(f.model.getSnapshot().result).toEqual(search);
    expect(f.posts()[0].body).toMatchObject({
      no_cloud: true,
      local_read_consent: true,
      max_retries: 0,
      resume_on_restart: false,
      steps: [
        {
          id: "inspect",
          capability: "project.search.v1",
          arguments: { scope_id: scope.scope_id, query: "answer" },
        },
      ],
    });
  });
  it("root changes invalidate consent, content and task references", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    await f.model.inspect("search", "answer");
    f.setScope(other);
    await f.model.select(true, "other-fixture");
    expect(f.model.getSnapshot()).toMatchObject({
      scope: other,
      consent: false,
      result: null,
      task: null,
    });
    await f.model.inspect("search", "answer");
    expect(f.posts()).toHaveLength(1);
  });
  it("allows revocation with unchecked view consent", async () => {
    const f = fixture();
    await f.model.connect(true);
    await f.model.select(false);
    expect(f.model.getSnapshot().scope.available).toBe(false);
    expect(f.calls.at(-1)).toMatchObject({
      path: "/v1/settings/project",
      body: { enabled: false },
    });
  });
  it("rejects empty search and respects active-work locks", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    await f.model.inspect("search", "  ");
    f.model.setBusy(true);
    await f.model.inspect("search", "answer");
    await f.model.select(true, "fixture");
    expect(f.posts()).toHaveLength(0);
    expect(f.calls).toHaveLength(1);
  });
  it("accepts file pages only for the requested path", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    f.setFinal(finished(read));
    await f.model.inspect("read", "src/app.tsx");
    expect(f.model.getSnapshot().result).toEqual(read);
    f.setFinal(finished({ ...read, path: "other.ts" }));
    await f.model.inspect("read", "src/app.tsx");
    expect(f.model.getSnapshot().result).toBeNull();
    expect(f.model.getSnapshot().issue).toContain("receipt does not match");
  });
  it("presents empty search accurately", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    f.setFinal(finished({ ...search, hits: [] }));
    await f.model.inspect("search", "absent");
    const html = renderToStaticMarkup(
      <ProjectResults
        result={f.model.getSnapshot().result!}
        disabled={false}
        onRead={() => {}}
      />,
    );
    expect(html).toContain("0 matches");
    expect(html).not.toContain("export const");
  });
  it("maps a project from names without showing file text", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    const mapped: ProjectResult = {
      scope_id: scope.scope_id,
      source_trust: "untrusted-data",
      truncated: false,
      languages: [{ suffix: ".py", files: 2 }],
      manifests: [{ path: "pyproject.toml", kind: "python" }],
      folders: ["src"],
      files_seen: 2,
    };
    f.setFinal(finished(mapped));
    await f.model.inspect("outline", "map");
    const posted = f.posts().at(-1)?.body as ReturnType<typeof projectRequest>;
    expect(posted.steps[0].capability).toBe("project.outline.v1");
    expect(posted.steps[0].arguments).toEqual({ scope_id: scope.scope_id });
    const html = renderToStaticMarkup(
      <ProjectResults
        result={f.model.getSnapshot().result!}
        disabled={false}
        onRead={() => {}}
      />,
    );
    expect(html).toContain(".py 2");
    expect(html).toContain("pyproject.toml (python)");
    expect(html).not.toContain("File SHA-256");
  });
  it("displays protected-file refusal and never displays raw private errors", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    f.setFinal({
      ...task,
      status: "failed",
      error: {
        code: "tool_denied",
        message: "That path is protected or ambiguous.",
      },
    });
    await f.model.inspect("read", ".env");
    expect(f.model.getSnapshot().issue).toContain("File refused");
    f.setHandler(async () => {
      throw new Error("C:\\PRIVATE_PATH_CANARY\\PRIVATE_KEY_CANARY");
    });
    await f.model.inspect("read", "src/app.tsx");
    expect(f.model.getSnapshot().issue).not.toContain("CANARY");
    expect(f.model.getSnapshot().result).toBeNull();
  });
  it("does not retry POSTs automatically and reuses the idempotency key on explicit retry", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    f.setHandler(async () => {
      throw new Error("network");
    });
    await f.model.inspect("search", "answer");
    expect(f.posts()).toHaveLength(1);
    f.setHandler(undefined);
    await f.model.inspect("search", "answer");
    expect(
      (f.posts()[0].body as ReturnType<typeof projectRequest>).request_id,
    ).toBe((f.posts()[1].body as ReturnType<typeof projectRequest>).request_id);
  });
  it("prevents duplicate root-selection clicks before acknowledgement", async () => {
    const f = fixture();
    await f.model.connect(true);
    const waiting = deferred<typeof scope>();
    f.setHandler(async () => waiting.promise);
    const first = f.model.select(true, "fixture");
    await f.model.select(true, "fixture");
    expect(
      f.calls.filter((c) => c.path === "/v1/settings/project"),
    ).toHaveLength(1);
    waiting.resolve(scope);
    await first;
  });
  it("prevents duplicate search clicks and shows real task/tool events", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    const waiting = deferred<void>();
    f.streaming.mockImplementation(async (id, _after, onEvent) => {
      onEvent({
        schema_version: "1.0",
        task_id: id,
        sequence: 1,
        type: "task.state",
        data: { status: "verifying" },
      });
      onEvent({
        schema_version: "1.0",
        task_id: id,
        sequence: 2,
        type: "tool.started",
        data: { name: "project.search.v1" },
      });
      await waiting.promise;
    });
    const first = f.model.inspect("search", "answer");
    await Promise.resolve();
    await f.model.inspect("search", "answer");
    expect(f.posts()).toHaveLength(1);
    expect(f.model.getSnapshot().activity).toContain("running");
    expect(f.model.getSnapshot().task?.status).toBe("verifying");
    waiting.resolve();
    await first;
    expect(f.model.getSnapshot().task?.status).toBe("succeeded");
  });
  it("cancels only the current task and coalesces duplicate Stop clicks", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    const streaming = deferred<void>();
    f.streaming.mockImplementation(async () => streaming.promise);
    const work = f.model.inspect("search", "answer");
    await Promise.resolve();
    const cancelling = deferred<Task>();
    f.setHandler(async (path) => {
      expect(path).toBe(`/v1/tasks/${task.task_id}/cancel`);
      return cancelling.promise;
    });
    const stop = f.model.cancel();
    await f.model.cancel();
    expect(f.calls.filter((c) => c.path.endsWith("/cancel"))).toHaveLength(1);
    cancelling.resolve({ ...task, status: "cancelled" });
    await stop;
    streaming.resolve();
    await work;
    expect(f.model.getSnapshot()).toMatchObject({
      pending: false,
      result: null,
      issue: "Project task cancelled.",
    });
  });
  it("disconnects safely, ignores late events and reconciles with GET only", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    const waiting = deferred<void>();
    f.streaming.mockImplementationOnce(async () => waiting.promise);
    const work = f.model.inspect("search", "answer");
    await Promise.resolve();
    await f.model.connect(false);
    expect(f.model.getSnapshot()).toMatchObject({
      connected: false,
      consent: false,
      result: null,
    });
    await f.model.inspect("search", "other");
    waiting.resolve();
    await work;
    await f.model.connect(true);
    expect(f.posts()).toHaveLength(1);
    expect(f.model.getSnapshot().task?.status).toBe("succeeded");
    expect(f.model.getSnapshot().result).toBeNull();
    f.model.consent(true);
    expect(f.model.getSnapshot().result).toEqual(search);
  });
  it("rejects stale root receipts", async () => {
    const f = fixture();
    await f.model.connect(true);
    f.model.consent(true);
    f.setFinal(finished({ ...search, scope_id: other.scope_id }));
    await f.model.inspect("search", "answer");
    expect(f.model.getSnapshot().result).toBeNull();
    expect(f.model.getSnapshot().issue).toContain("receipt does not match");
  });
  it("recovers status errors through read-only refresh and ignores disposed views", async () => {
    const f = fixture();
    f.setHandler(async () => {
      throw new Error("network");
    });
    await f.model.connect(true);
    expect(f.model.getSnapshot().issue).toContain("unavailable");
    f.setHandler(undefined);
    await f.model.connect(true);
    expect(f.model.getSnapshot().scope).toEqual(scope);
    expect(f.posts()).toHaveLength(0);
    const waiting = deferred<typeof scope>();
    f.setHandler(async () => waiting.promise);
    const work = f.model.connect(true);
    f.model.dispose();
    waiting.resolve(other);
    await work;
    expect(f.model.getSnapshot().scope).toEqual(scope);
  });
  it("renders receipt source as escaped data with file provenance", () => {
    const html = renderToStaticMarkup(
      <ProjectResults result={read} disabled={false} onRead={() => {}} />,
    );
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
    expect(html).toContain(read.sha256);
    expect(html).toContain("untrusted data");
  });
});
