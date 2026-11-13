import { useState, type FormEvent } from "react";
import type { OverlayPolicy } from "./face/faceState";
import type { Quality } from "./face/HeadScene";
import { api, windowAction } from "./transport";
import type { VoiceController } from "./useVoice";
import { VoiceControls } from "./VoiceControls";

export interface Health {
  credential_source?: string;
  ready: boolean;
  hermes: { status: string; version?: string; message?: string };
  providers: Record<string, string>;
  free_only: boolean;
  active_task: string | null;
  delegation_enabled?: boolean;
  local_tools_enabled?: boolean;
  workspace_tools_enabled?: boolean;
  web_research_enabled?: boolean;
  mcp_enabled?: boolean;
  code_execution_enabled?: boolean;
}

const providers = [
  ["openrouter", "OpenRouter"],
  ["gemini", "Gemini"],
  ["groq", "Groq"],
  ["nvidia", "NVIDIA"],
] as const;

const message = (issue: unknown, fallback: string) =>
  issue instanceof Error ? issue.message : fallback;

function ProviderKeys({
  health,
  onSaved,
}: {
  health: Health | undefined;
  onSaved: () => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  async function save(event: FormEvent, provider: string) {
    event.preventDefault();
    try {
      await api("/v1/settings/provider-key", {
        provider,
        api_key: drafts[provider] ?? "",
      });
      setDrafts((current) => ({ ...current, [provider]: "" }));
      setNotes((current) => ({
        ...current,
        [provider]: "Saved in Windows Credential Manager.",
      }));
      onSaved();
    } catch (issue) {
      setNotes((current) => ({
        ...current,
        [provider]: message(issue, "Could not save the key."),
      }));
    }
  }
  return (
    <>
      <p className="hint">
        Keys stay in Windows Credential Manager on this PC and never reach this
        window. Chat uses only the free OpenRouter route.
      </p>
      {providers.map(([provider, label]) => (
        <form
          className="key-form"
          key={provider}
          onSubmit={(event) => void save(event, provider)}
        >
          <p>
            <b>{label}</b> · {health?.providers?.[provider] ?? "missing key"}
          </p>
          <label>
            {label} API key
            <input
              type="password"
              name={`${provider}-api-key`}
              autoComplete="off"
              spellCheck={false}
              value={drafts[provider] ?? ""}
              onChange={(event) =>
                setDrafts((current) => ({
                  ...current,
                  [provider]: event.target.value,
                }))
              }
            />
          </label>
          <button
            type="submit"
            disabled={(drafts[provider] ?? "").trim().length < 16}
          >
            Save {label} key
          </button>
          {notes[provider] && <p className="hint">{notes[provider]}</p>}
        </form>
      ))}
    </>
  );
}

export function LocalTools({
  session,
  mcp,
  clock,
  onError,
}: {
  session: string;
  mcp: boolean;
  clock: boolean;
  onError: (message: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<{ task_id: string; body: string }[]>(
    [],
  );
  const [result, setResult] = useState("");
  return (
    <div className="workspace">
      <div className="row">
        {mcp && (
          <button
            type="button"
            onClick={() =>
              void api<{ result: string }>("/v1/mcp/call", {
                name: "add",
                a: 2,
                b: 2,
              })
                .then((body) => setResult(`Local MCP 2 + 2 = ${body.result}`))
                .catch((issue: unknown) =>
                  onError(message(issue, "MCP failed.")),
                )
            }
          >
            Ask local MCP for 2 + 2
          </button>
        )}
        {clock && (
          <button
            type="button"
            onClick={() =>
              void api<{ result: string }>("/v1/tools/call", {
                name: "clock",
              })
                .then((row) => setResult(`Local clock: ${row.result}`))
                .catch((issue: unknown) =>
                  onError(message(issue, "Clock failed.")),
                )
            }
          >
            Read local clock
          </button>
        )}
      </div>
      {result && <p>{result}</p>}
      <label>
        Search this conversation’s memory
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <button
        type="button"
        disabled={!query.trim()}
        onClick={() =>
          void api<{ matches: { task_id: string; body: string }[] }>(
            "/v1/memory/search",
            { session_id: session, query },
          )
            .then((body) => setMatches(body.matches))
            .catch((issue: unknown) =>
              onError(message(issue, "Memory search failed.")),
            )
        }
      >
        Search memory
      </button>
      {matches.map((item) => (
        <p key={item.task_id} className="memory-row">
          <span>{item.body}</span>
          <button
            type="button"
            onClick={() =>
              void api("/v1/memory/delete", {
                session_id: session,
                task_id: item.task_id,
              }).then(() =>
                setMatches((current) =>
                  current.filter((row) => row.task_id !== item.task_id),
                ),
              )
            }
          >
            Forget
          </button>
        </p>
      ))}
    </div>
  );
}

function WorkspaceFolder({
  enabled,
  onSaved,
}: {
  enabled: boolean;
  onSaved: () => void;
}) {
  const [root, setRoot] = useState("");
  const [problem, setProblem] = useState("");
  return (
    <div className="workspace">
      <label>
        Workspace folder
        <input
          value={root}
          spellCheck={false}
          onChange={(event) => setRoot(event.target.value)}
        />
      </label>
      <button
        type="button"
        onClick={() =>
          void api("/v1/settings/workspace", { enabled: true, root })
            .then(() => {
              setProblem("");
              onSaved();
            })
            .catch((issue: unknown) =>
              setProblem(message(issue, "Workspace was rejected.")),
            )
        }
      >
        Allow approved edits in this folder
      </button>
      {enabled && (
        <button
          type="button"
          onClick={() =>
            void api("/v1/settings/workspace", { enabled: false })
              .then(() => onSaved())
              .catch((issue: unknown) =>
                setProblem(message(issue, "Could not turn this off.")),
              )
          }
        >
          Turn workspace edits off
        </button>
      )}
      {problem && <p className="error">{problem}</p>}
    </div>
  );
}

export interface InterfacePrefs {
  quality: Quality;
  overlay: OverlayPolicy;
  reduced: boolean;
  pin: boolean;
}

export function SettingsPanel({
  health,
  session,
  voice,
  prefs,
  setPrefs,
  onRefresh,
  onError,
  onPreviewOverlay,
}: {
  health: Health | undefined;
  session: string;
  voice: VoiceController;
  prefs: InterfacePrefs;
  setPrefs: (next: Partial<InterfacePrefs>) => void;
  onRefresh: () => void;
  onError: (message: string) => void;
  onPreviewOverlay: () => void;
}) {
  const toggle = (path: string, label: string, key: keyof Health) => (
    <label>
      <input
        type="checkbox"
        checked={health?.[key] === true}
        onChange={(event) =>
          void api(path, { enabled: event.target.checked })
            .then(onRefresh)
            .catch((issue: unknown) =>
              onError(message(issue, "Setting failed.")),
            )
        }
      />
      {label}
    </label>
  );
  return (
    <section className="settings" aria-label="Settings">
      <h3>Interface</h3>
      <label>
        3D quality
        <select
          value={prefs.quality}
          onChange={(event) =>
            setPrefs({ quality: event.target.value as Quality })
          }
        >
          <option value="high">High</option>
          <option value="balanced">Balanced</option>
          <option value="performance">Performance</option>
          <option value="2d">2D fallback (no WebGL)</option>
        </select>
      </label>
      <label>
        <input
          type="checkbox"
          checked={prefs.reduced}
          onChange={(event) => setPrefs({ reduced: event.target.checked })}
        />
        Reduce motion
      </label>
      <label>
        <input
          type="checkbox"
          checked={prefs.pin}
          onChange={(event) => {
            setPrefs({ pin: event.target.checked });
            void windowAction(event.target.checked ? "pin" : "unpin");
          }}
        />
        Companion stays on top
      </label>
      <label>
        Work overlay
        <select
          value={prefs.overlay}
          onChange={(event) =>
            setPrefs({ overlay: event.target.value as OverlayPolicy })
          }
        >
          <option value="screen-control">
            Collapse to overlay during screen control
          </option>
          <option value="never">Never collapse automatically</option>
        </select>
      </label>
      <p className="hint">
        Screen control (Computer Use) is disabled, so the overlay never opens on
        its own today. File reads and research never trigger it.
      </p>
      <button type="button" onClick={onPreviewOverlay}>
        Preview work overlay — no screen access
      </button>
      <h3>Runtime</h3>
      <p>
        Hermes {health?.hermes.version ?? ""} ·{" "}
        {health?.hermes.status ?? "unavailable"}
        {health?.hermes.message ? ` · ${health.hermes.message}` : ""}
      </p>
      <p>
        Paid inference: blocked · Code execution: disabled · Active task:{" "}
        {health?.active_task ?? "none"}
      </p>
      <button type="button" onClick={onRefresh}>
        Check connection
      </button>
      <h3>Capabilities</h3>
      {toggle(
        "/v1/settings/delegation",
        "Specialist agents (research, coding, review). No tools.",
        "delegation_enabled",
      )}
      {toggle(
        "/v1/settings/local-tools",
        "Local clock tool. Terminal and files stay off.",
        "local_tools_enabled",
      )}
      {toggle(
        "/v1/settings/web-research",
        "Public Wikipedia research. Pages are untrusted data.",
        "web_research_enabled",
      )}
      {toggle(
        "/v1/settings/mcp",
        "Local arithmetic MCP server. External servers stay off.",
        "mcp_enabled",
      )}
      <WorkspaceFolder
        enabled={health?.workspace_tools_enabled === true}
        onSaved={onRefresh}
      />
      <LocalTools
        session={session}
        mcp={health?.mcp_enabled === true}
        clock={health?.local_tools_enabled === true}
        onError={onError}
      />
      <h3>Voice</h3>
      <VoiceControls voice={voice} settings />
      <h3>Providers</h3>
      <p>
        Credential storage: {health?.credential_source ?? "local environment"}
      </p>
      <button
        type="button"
        onClick={() =>
          void api("/v1/settings/migrate-credentials", {})
            .then(onRefresh)
            .catch((issue: unknown) =>
              onError(message(issue, "Migration failed.")),
            )
        }
      >
        Move .env keys to Windows Credential Manager
      </button>
      <ProviderKeys health={health} onSaved={onRefresh} />
      <p className="hint">
        Ctrl+Shift+Space opens chat. Ctrl+Shift+Escape stops the active task.
      </p>
    </section>
  );
}
