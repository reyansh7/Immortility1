import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { api, stream } from "./transport";
import { terminal } from "./state";
import { ProjectInspection, type ProjectResult } from "./projectInspection";
export { projectRequest } from "./projectInspection";
export type {
  ProjectScope,
  ProjectHit,
  ProjectResult,
} from "./projectInspection";

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
      <p className="hint">
        Local file evidence · project text remains untrusted data.
      </p>
      {result.languages ? (
        <>
          <p role="status">
            {result.files_seen ?? 0} source files named
            {result.truncated ? " · map stopped at its limit" : ""}
          </p>
          <p>
            Languages:{" "}
            {result.languages
              .map((item) => `${item.suffix} ${item.files}`)
              .join(", ") || "none recognized"}
          </p>
          <p>
            Manifests:{" "}
            {result.manifests
              ?.map((item) => `${item.path} (${item.kind})`)
              .join(", ") || "none at the top of the tree"}
          </p>
          <p>Top folders: {result.folders?.join(", ") || "none"}</p>
        </>
      ) : result.hits ? (
        <>
          <p role="status">
            {result.hits.length} matches · {result.files_scanned} files checked
            {result.skipped_files
              ? ` · ${result.skipped_files} files skipped`
              : ""}
          </p>
          {result.hits.map((hit) => (
            <div key={`${hit.path}:${hit.line}`}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onRead(hit.path, Math.max(1, hit.line - 5))}
              >
                {hit.path}:{hit.line}
              </button>
              <pre>{hit.text}</pre>
            </div>
          ))}
        </>
      ) : (
        <>
          <p>
            {result.path}
            {result.text
              ? ` · lines ${result.start_line}–${result.end_line}`
              : " · empty file"}
          </p>
          <pre>{result.text}</pre>
          <p className="hint">File SHA-256: {result.sha256}</p>
          {result.path &&
            result.start_line !== undefined &&
            result.start_line > 1 && (
              <button
                type="button"
                disabled={disabled}
                onClick={() =>
                  onRead(result.path!, Math.max(1, result.start_line! - 40))
                }
              >
                Previous file page
              </button>
            )}
          {result.path && result.truncated && result.end_line !== undefined && (
            <button
              type="button"
              disabled={disabled}
              onClick={() => onRead(result.path!, result.end_line! + 1)}
            >
              Next file page
            </button>
          )}
        </>
      )}
      {result.truncated && (
        <p role="status">
          Read limit reached. Narrow the search or request another file page.
        </p>
      )}
    </div>
  );
}

export function ProjectInspector({
  session,
  connected,
  busy,
}: {
  session: string;
  connected: boolean;
  busy: boolean;
}) {
  const model = useMemo(
    () =>
      new ProjectInspection(session, {
        request: api,
        stream,
        requestId: () => crypto.randomUUID(),
      }),
    [session],
  );
  const state = useSyncExternalStore(
    model.subscribe,
    model.getSnapshot,
    model.getSnapshot,
  );
  const [folder, setFolder] = useState("");
  const [query, setQuery] = useState("");
  const [path, setPath] = useState("");
  useEffect(() => {
    model.attach();
    void model.connect(connected);
    return () => model.dispose();
  }, [model, connected]);
  useEffect(() => {
    model.setBusy(busy);
  }, [model, busy]);
  const active = !!state.task && !terminal.has(state.task.status);
  const locked = !connected || busy || state.pending || active;
  const readDisabled = locked || !state.consent || !state.scope.available;
  return (
    <section aria-label="Local project inspection" className="workspace">
      <h3>Inspect project · local</h3>
      <p className="hint">
        Map, search and read selected project text without a cloud model, file
        edits or command execution.
      </p>
      <fieldset disabled={locked}>
        <label>
          Project folder
          <input
            value={folder}
            onChange={(event) => setFolder(event.target.value)}
            spellCheck={false}
            maxLength={1024}
          />
        </label>
        <button
          type="button"
          disabled={!folder.trim()}
          onClick={() => void model.select(true, folder)}
        >
          Select read-only project
        </button>
        {state.scope.available && (
          <button type="button" onClick={() => void model.select(false)}>
            Revoke project reads
          </button>
        )}
      </fieldset>
      <p role="status">
        {state.scope.available
          ? `Selected: ${state.scope.folder_name}`
          : "No project read permission"}
      </p>
      <button
        type="button"
        disabled={!connected || state.pending}
        onClick={() => void model.connect(true)}
      >
        Refresh project status
      </button>
      <label>
        <input
          type="checkbox"
          checked={state.consent}
          disabled={!connected || state.pending || !state.scope.available}
          onChange={(event) => model.consent(event.target.checked)}
        />
        Allow local reads for this project view
      </label>
      {state.scope.available && !state.consent && (
        <p className="hint">
          Confirm local reads for the selected folder. Selecting another folder
          clears this consent.
        </p>
      )}
      <fieldset disabled={readDisabled}>
        <button
          type="button"
          onClick={() => void model.inspect("outline", "map")}
        >
          Map this project
        </button>
        <label>
          Search project text
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={120}
          />
        </label>
        <button
          type="button"
          disabled={!query.trim()}
          onClick={() => void model.inspect("search", query)}
        >
          Search locally
        </button>
        <label>
          Relative file path
          <input
            value={path}
            onChange={(event) => setPath(event.target.value)}
            maxLength={240}
            spellCheck={false}
          />
        </label>
        <button
          type="button"
          disabled={!path.trim()}
          onClick={() => void model.inspect("read", path)}
        >
          Read local file
        </button>
      </fieldset>
      {state.task && (
        <p role="status">Local task · {state.task.status} · no cloud</p>
      )}
      {state.activity && <p role="status">{state.activity}</p>}
      {active && (
        <button
          type="button"
          disabled={!connected || state.cancelling}
          onClick={() => void model.cancel()}
        >
          Cancel project task
        </button>
      )}
      {state.issue && <p role="alert">{state.issue}</p>}
      {state.result && (
        <ProjectResults
          result={state.result}
          disabled={readDisabled}
          onRead={(file, line) => void model.inspect("read", file, line)}
        />
      )}
    </section>
  );
}
