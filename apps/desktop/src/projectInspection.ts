/** Ephemeral UI presentation only. The broker owns all permissions and tasks. */
import { followTask } from "./chat";
import { terminal, type Task, type TaskEvent } from "./state";
import { statuses } from "./contracts.generated";

export interface ProjectScope {
  available: boolean;
  scope_id: string | null;
  folder_name: string | null;
}
export interface ProjectHit {
  path: string;
  line: number;
  text: string;
  sha256: string;
}
export interface ProjectResult {
  scope_id: string;
  source_trust: "untrusted-data";
  truncated: boolean;
  hits?: ProjectHit[];
  files_scanned?: number;
  skipped_files?: number;
  path?: string;
  text?: string;
  sha256?: string;
  start_line?: number;
  end_line?: number;
  languages?: { suffix: string; files: number }[];
  manifests?: { path: string; kind: string }[];
  folders?: string[];
  files_seen?: number;
}
type Action = "search" | "read" | "outline";
interface Transport {
  request: <T>(path: string, body?: unknown) => Promise<T>;
  stream: (
    id: string,
    after: number,
    event: (value: TaskEvent) => void,
    signal: AbortSignal,
  ) => Promise<void>;
  requestId: () => string;
}
interface State {
  connected: boolean;
  scope: ProjectScope;
  consent: boolean;
  pending: boolean;
  cancelling: boolean;
  task: Task | null;
  result: ProjectResult | null;
  issue: string;
  activity: string;
}
const emptyScope: ProjectScope = {
  available: false,
  scope_id: null,
  folder_name: null,
};
const genericError =
  "Local project request failed. Reconnect or inspect the stored task status.";
function safeIssue(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (
    [
      "That path is protected or ambiguous.",
      "That path is not in the workspace.",
      "Only supported project text files can be read.",
      "Links are not followed.",
      "Hard-linked files are not allowed.",
      "Credential-like content must be redacted before task execution or inference.",
    ].includes(message)
  )
    return "File refused: protected, secret-bearing or outside the permitted project scope.";
  if (message === "Project read permission changed; choose the folder again.")
    return message;
  if (message === "Requested page is beyond the end of this file.")
    return message;
  return genericError;
}

export function projectRequest(
  session: string,
  scopeId: string,
  action: Action,
  value: string,
  requestId: string,
  startLine = 1,
) {
  return {
    session_id: session,
    request_id: requestId,
    label:
      action === "search"
        ? "Local project search"
        : action === "outline"
          ? "Local project map"
          : "Local project file read",
    local_read_consent: true,
    no_cloud: true,
    resume_on_restart: false,
    max_retries: 0,
    deadline_seconds: 15,
    steps: [
      {
        id: "inspect",
        capability: `project.${action}.v1`,
        arguments:
          action === "search"
            ? { scope_id: scopeId, query: value }
            : action === "outline"
              ? { scope_id: scopeId }
              : {
                  scope_id: scopeId,
                  path: value,
                  start_line: startLine,
                  lines: 40,
                },
      },
    ],
  };
}

export class ProjectInspection {
  private state: State = {
    connected: false,
    scope: emptyScope,
    consent: false,
    pending: false,
    cancelling: false,
    task: null,
    result: null,
    issue: "",
    activity: "",
  };
  private listeners = new Set<() => void>();
  private version = 0;
  private disposed = false;
  private locked = false;
  private busy = false;
  private watch: AbortController | null = null;
  private operation: {
    action: Action;
    value: string;
    start: number;
    scope: string;
  } | null = null;
  private retry: { signature: string; id: string } | null = null;
  constructor(
    private session: string,
    private transport: Transport,
  ) {}
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };
  attach() {
    this.disposed = false;
  }
  dispose() {
    this.disposed = true;
    this.version++;
    this.watch?.abort();
  }
  setBusy(value: boolean) {
    this.busy = value;
  }
  private patch(value: Partial<State>) {
    if (this.disposed) return;
    this.state = { ...this.state, ...value };
    for (const listener of this.listeners) listener();
  }
  private active() {
    return !!this.state.task && !terminal.has(this.state.task.status);
  }
  private current(version: number) {
    return !this.disposed && version === this.version;
  }
  private allowed() {
    return this.state.connected && !this.busy && !this.locked && !this.active();
  }
  consent(value: boolean) {
    this.patch({
      consent: value && this.state.connected && this.state.scope.available,
      result: null,
    });
    if (this.state.consent && this.state.task) this.receipt(this.state.task);
  }
  async connect(connected: boolean) {
    const version = ++this.version;
    this.watch?.abort();
    this.locked = false;
    this.patch({
      connected,
      consent: false,
      result: null,
      pending: false,
      cancelling: false,
    });
    if (!connected) return;
    try {
      const scope =
        await this.transport.request<ProjectScope>("/v1/projects/scope");
      if (!this.current(version)) return;
      if (
        scope.available &&
        (!scope.scope_id || !/^[a-f0-9]{64}$/.test(scope.scope_id))
      )
        throw new Error();
      const changed = scope.scope_id !== this.state.scope.scope_id;
      this.patch({
        scope,
        issue: "",
        ...(changed ? { task: null, activity: "" } : {}),
      });
      if (changed) {
        this.operation = null;
        this.retry = null;
      }
      if (this.state.task) await this.follow(this.state.task, version);
    } catch {
      if (this.current(version))
        this.patch({
          issue:
            "Project permission status is unavailable. Reconnect to retry.",
          scope: emptyScope,
        });
    }
  }
  async select(enabled: boolean, root = "") {
    if (!this.allowed() || (enabled && !root.trim())) return;
    this.locked = true;
    const version = ++this.version;
    this.patch({ pending: true, issue: "", consent: false, result: null });
    try {
      const scope = await this.transport.request<ProjectScope>(
        "/v1/settings/project",
        { enabled, ...(enabled ? { root } : {}), local_read_consent: true },
      );
      if (!this.current(version)) return;
      this.operation = null;
      this.retry = null;
      this.patch({
        scope,
        consent: false,
        result: null,
        task: null,
        activity: "",
      });
    } catch (error) {
      if (this.current(version)) this.patch({ issue: safeIssue(error) });
    } finally {
      if (this.current(version)) {
        this.locked = false;
        this.patch({ pending: false });
      }
    }
  }
  private receipt(task: Task) {
    if (!this.state.consent || task.status !== "succeeded" || !this.operation)
      return;
    const output = (
      task.result as Task["result"] & { steps?: { inspect?: ProjectResult } }
    )?.steps?.inspect;
    const operation = this.operation;
    if (
      !output ||
      output.scope_id !== this.state.scope.scope_id ||
      output.scope_id !== operation.scope ||
      output.source_trust !== "untrusted-data" ||
      (operation.action === "search"
        ? !Array.isArray(output.hits)
        : operation.action === "outline"
          ? !Array.isArray(output.languages)
          : output.path !== operation.value || typeof output.text !== "string")
    ) {
      this.patch({
        result: null,
        issue: "Project receipt does not match this folder permission.",
      });
      return;
    }
    this.patch({ result: output });
  }
  private accept(task: Task) {
    const current = this.state.task;
    if (
      !current ||
      task.task_id !== current.task_id ||
      task.session_id !== this.session
    )
      throw new Error();
    this.patch({ task });
    if (terminal.has(task.status)) {
      this.retry = null;
      if (task.status === "succeeded") this.receipt(task);
      else
        this.patch({
          result: null,
          issue:
            task.status === "cancelled"
              ? "Project task cancelled."
              : safeIssue(new Error(task.error?.message)),
        });
    }
  }
  private async follow(task: Task, version: number) {
    const controller = new AbortController();
    this.watch = controller;
    if (terminal.has(task.status)) {
      this.accept(task);
      return;
    }
    this.patch({ pending: true });
    try {
      await followTask(
        task,
        {
          stream: (after, event, signal) =>
            this.transport.stream(task.task_id, after, event, signal),
          task: () => this.transport.request<Task>(`/v1/tasks/${task.task_id}`),
        },
        (event) => {
          if (!this.current(version)) return;
          if (
            event.type === "task.state" &&
            statuses.includes(event.data.status as Task["status"])
          )
            this.patch({
              task: { ...task, status: event.data.status as Task["status"] },
            });
          if (
            ["tool.started", "tool.completed"].includes(event.type) &&
            [
              "project.search.v1",
              "project.read.v1",
              "project.outline.v1",
            ].includes(String(event.data.name))
          )
            this.patch({
              activity: `${String(event.data.name)} · ${event.type === "tool.started" ? "running" : "finished"}`,
            });
        },
        (fresh) => {
          if (this.current(version)) this.accept(fresh);
        },
        controller.signal,
      );
    } finally {
      if (this.current(version)) this.patch({ pending: false });
    }
  }
  async inspect(action: Action, value: string, start = 1) {
    const scope = this.state.scope.scope_id;
    if (
      !this.allowed() ||
      !this.state.consent ||
      !scope ||
      (action !== "outline" && !value.trim())
    )
      return;
    this.locked = true;
    const version = ++this.version;
    this.patch({
      pending: true,
      result: null,
      issue: "",
      activity: "",
      task: null,
    });
    this.operation = { action, value, start, scope };
    const signature = JSON.stringify(this.operation);
    if (this.retry?.signature !== signature)
      this.retry = { signature, id: this.transport.requestId() };
    try {
      const task = await this.transport.request<Task>(
        "/v1/workflows",
        projectRequest(
          this.session,
          scope,
          action,
          value,
          this.retry.id,
          start,
        ),
      );
      if (!this.current(version)) return;
      if (task.session_id !== this.session) throw new Error();
      this.patch({ task });
      await this.follow(task, version);
    } catch (error) {
      if (this.current(version)) this.patch({ issue: safeIssue(error) });
    } finally {
      if (this.current(version)) {
        this.locked = false;
        this.patch({ pending: false });
      }
    }
  }
  async cancel() {
    const task = this.state.task;
    if (
      !this.state.connected ||
      !task ||
      terminal.has(task.status) ||
      this.state.cancelling
    )
      return;
    this.patch({ cancelling: true });
    try {
      const fresh = await this.transport.request<Task>(
        `/v1/tasks/${task.task_id}/cancel`,
        {},
      );
      if (!this.state.connected || this.state.task?.task_id !== task.task_id)
        return;
      this.accept(fresh);
      if (terminal.has(fresh.status)) {
        this.version++;
        this.watch?.abort();
        this.locked = false;
        this.patch({ pending: false });
      }
    } catch (error) {
      this.patch({ issue: safeIssue(error) });
    } finally {
      this.patch({ cancelling: false });
    }
  }
}
