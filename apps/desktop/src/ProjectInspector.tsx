import { useEffect, useRef, useState } from "react";
import { api, stream } from "./transport";
import { followTask } from "./chat";
import { terminal, type Task } from "./state";

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
}

export function projectRequest(
  session: string,
  scopeId: string,
  action: "search" | "read",
  value: string,
  requestId: string,
  startLine = 1,
) {
  return {
    session_id: session,
    request_id: requestId,
    label: action === "search" ? "Local project search" : "Local project file read",
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
            : { scope_id: scopeId, path: value, start_line: startLine, lines: 40 },
      },
    ],
  };
}

export function ProjectResults({
  result,
  disabled,
  onRead,
}: {
  result: ProjectResult;
  disabled: boolean;
  onRead: (path: string, line: number) => void;
}) {
  return (
    <div aria-label="Verified local project read">
      <p className="hint">Local file evidence · project text remains untrusted data.</p>
      {result.hits ? (
        <>
          <p role="status">
            {result.hits.length} matches · {result.files_scanned} files checked
            {result.skipped_files ? ` · ${result.skipped_files} files skipped` : ""}
          </p>
          {result.hits.map((hit) => (
            <div key={`${hit.path}:${hit.line}`}>
              <button type="button" disabled={disabled} onClick={() => onRead(hit.path, Math.max(1, hit.line - 5))}>
                {hit.path}:{hit.line}
              </button>
              <pre>{hit.text}</pre>
            </div>
          ))}
        </>
      ) : (
        <>
          <p>{result.path} · lines {result.start_line}–{result.end_line}</p>
          <pre>{result.text}</pre>
          <p className="hint">File SHA-256: {result.sha256}</p>
        </>
      )}
      {result.truncated && <p role="status">Read limit reached. Narrow the search or request another file page.</p>}
    </div>
  );
}

export function ProjectInspector({ session, connected, busy }: { session: string; connected: boolean; busy: boolean }) {
  const [scope, setScope] = useState<ProjectScope>({ available: false, scope_id: null, folder_name: null });
  const [folder, setFolder] = useState("");
  const [query, setQuery] = useState("");
  const [path, setPath] = useState("");
  const [consent, setConsent] = useState(false);
  const [pending, setPending] = useState(false);
  const [task, setTask] = useState<Task | null>(null);
  const [result, setResult] = useState<ProjectResult | null>(null);
  const [issue, setIssue] = useState("");
  const locked = useRef(false);
  const mounted = useRef(true);
  const watch = useRef<AbortController | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; watch.current?.abort(); };
  }, []);
  useEffect(() => {
    let current = true;
    if (connected) void api<ProjectScope>("/v1/projects/scope")
      .then((fresh) => { if (current) setScope(fresh); })
      .catch(() => { if (current) setIssue("Project permission status is unavailable."); });
    else setConsent(false);
    return () => { current = false; };
  }, [connected]);
  const disabled = !connected || busy || pending || !consent;

  async function choose(enabled: boolean) {
    if (locked.current || disabled) return;
    locked.current = true; setPending(true); setIssue("");
    try {
      const fresh = await api<ProjectScope>("/v1/settings/project", { enabled, ...(enabled ? { root: folder } : {}), local_read_consent: true });
      if (mounted.current) { setScope(fresh); setResult(null); setTask(null); }
    } catch (error) { if (mounted.current) setIssue(error instanceof Error ? error.message : "Project permission failed."); }
    finally { locked.current = false; if (mounted.current) setPending(false); }
  }

  async function inspect(action: "search" | "read", value: string, start = 1) {
    if (locked.current || disabled || !scope.scope_id || !value.trim()) return;
    locked.current = true; setPending(true); setIssue(""); setResult(null);
    const controller = new AbortController(); watch.current = controller;
    try {
      const created = await api<Task>("/v1/workflows", projectRequest(session, scope.scope_id, action, value, crypto.randomUUID(), start));
      if (!mounted.current) return;
      setTask(created);
      let final = created;
      await followTask(created, { stream: (after, onEvent, signal) => stream(created.task_id, after, onEvent, signal), task: () => api<Task>(`/v1/tasks/${created.task_id}`) }, () => {}, (fresh) => { final = fresh; if (mounted.current) setTask(fresh); }, controller.signal);
      if (!mounted.current || controller.signal.aborted) return;
      if (final.status !== "succeeded") throw new Error(final.error?.message ?? `Project task ${final.status}.`);
      const receipt = final.result as (Task["result"] & { steps?: { inspect?: ProjectResult } });
      const output = receipt?.steps?.inspect;
      if (!output || output.scope_id !== scope.scope_id || output.source_trust !== "untrusted-data") throw new Error("Project receipt does not match this folder permission.");
      setResult(output);
    } catch (error) { if (mounted.current) setIssue(error instanceof Error ? error.message : "Project read failed."); }
    finally { locked.current = false; if (mounted.current) setPending(false); }
  }

  return (
    <section aria-label="Local project inspection" className="workspace">
      <h3>Inspect project · local</h3>
      <p className="hint">Search and read selected project text without a cloud model, file edits or command execution.</p>
      <label><input type="checkbox" checked={consent} disabled={!connected || pending} onChange={(event) => setConsent(event.target.checked)} />Allow local reads for this project view</label>
      <fieldset disabled={disabled}>
        <label>Project folder<input value={folder} onChange={(event) => setFolder(event.target.value)} spellCheck={false} /></label>
        <button type="button" disabled={!folder.trim()} onClick={() => void choose(true)}>Select read-only project</button>
        {scope.available && <button type="button" onClick={() => void choose(false)}>Revoke project reads</button>}
        <p role="status">{scope.available ? `Selected: ${scope.folder_name}` : "No project read permission"}</p>
        <label>Search project text<input value={query} onChange={(event) => setQuery(event.target.value)} maxLength={120} /></label>
        <button type="button" disabled={!scope.available || !query.trim()} onClick={() => void inspect("search", query)}>Search locally</button>
        <label>Relative file path<input value={path} onChange={(event) => setPath(event.target.value)} maxLength={240} spellCheck={false} /></label>
        <button type="button" disabled={!scope.available || !path.trim()} onClick={() => void inspect("read", path)}>Read local file</button>
      </fieldset>
      {task && <p role="status">Local task · {task.status} · no cloud</p>}
      {task && !terminal.has(task.status) && <button type="button" disabled={!connected} onClick={() => void api(`/v1/tasks/${task.task_id}/cancel`, {}).catch((error: unknown) => setIssue(error instanceof Error ? error.message : "Cancellation failed."))}>Cancel project task</button>}
      {issue && <p role="alert">{issue}</p>}
      {result && <ProjectResults result={result} disabled={disabled} onRead={(file, line) => void inspect("read", file, line)} />}
    </section>
  );
}
