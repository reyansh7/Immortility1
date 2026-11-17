import { useState, type ReactNode } from "react";
import type { OverlayPolicy } from "./face/faceState";
import type { Quality } from "./face/FlatFace";
import { api, windowAction } from "./transport";
import type { VoiceController } from "./useVoice";
import { VoiceControls } from "./VoiceControls";
import { invoke } from "@tauri-apps/api/core";
import { ModelHub, type ActiveModel } from "./ModelHub";
import { ProjectInspector } from "./ProjectInspector";
import type { ModelSelection } from "./contracts.generated";

export interface Health {
  credential_source?: string;
  ready: boolean;
  hermes: { status: string; version?: string; message?: string };
  providers: Record<string, string>;
  free_only: boolean;
  active_task: string | null;
  voice_state?: string;
  model_selection?: ModelSelection;
  delegation_enabled?: boolean;
  local_tools_enabled?: boolean;
  workspace_tools_enabled?: boolean;
  web_research_enabled?: boolean;
  mcp_enabled?: boolean;
  code_execution_enabled?: boolean;
  observation_available?: boolean;
  runtime_mode?: "desktop" | "local-background";
  standard_mcp_enabled?: boolean;
  artifact_tools_enabled?: boolean;
  active_model?: ActiveModel | null;
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
  const [notes, setNotes] = useState<Record<string, string>>({});
  async function save(provider: string) {
    try {
      const saved = await invoke<boolean>("configure_provider", { provider });
      setNotes((current) => ({
        ...current,
        [provider]: saved
          ? "Saved in Windows Credential Manager."
          : "Key entry canceled.",
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
        window. Chat uses only routes that pass broker price and permission
        checks.
      </p>
      {providers.map(([provider, label]) => (
        <div className="key-form" key={provider}>
          <p>
            <b>{label}</b> · {health?.providers?.[provider] ?? "missing key"}
          </p>
          <button type="button" onClick={() => void save(provider)}>
            Enter {label} key in Windows
          </button>
          {notes[provider] && <p className="hint">{notes[provider]}</p>}
        </div>
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
  const [fact, setFact] = useState("");
  const [correction, setCorrection] = useState("");
  const [selectedFact, setSelectedFact] = useState("");
  const [facts, setFacts] = useState<
    { id: string; body: string; trust: string; status: string }[]
  >([]);
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
        Confirmed preference
        <input
          value={fact}
          maxLength={500}
          onChange={(event) => setFact(event.target.value)}
        />
      </label>
      <button
        type="button"
        disabled={!fact.trim()}
        onClick={() =>
          void api("/v1/memory/facts", {
            kind: "preference",
            scope: "user",
            text: fact,
            confirmed: true,
          })
            .then(() => setResult("Preference saved on this computer."))
            .catch((issue: unknown) =>
              onError(message(issue, "Could not save that preference.")),
            )
        }
      >
        Save confirmed preference
      </button>
      <button
        type="button"
        disabled={!fact.trim()}
        onClick={() =>
          void api<{
            matches: {
              id: string;
              body: string;
              trust: string;
              status: string;
            }[];
          }>("/v1/memory/facts/search", { query: fact })
            .then((body) => {
              setFacts(body.matches);
              setSelectedFact(body.matches[0]?.id ?? "");
            })
            .catch((issue: unknown) =>
              onError(message(issue, "Confirmed memory search failed.")),
            )
        }
      >
        Find confirmed memory
      </button>
      {facts.map((item) => (
        <p key={item.id}>
          <button type="button" onClick={() => setSelectedFact(item.id)}>
            {item.trust}: {item.body}
          </button>
        </p>
      ))}
      <label>
        Correction
        <input
          value={correction}
          maxLength={500}
          onChange={(event) => setCorrection(event.target.value)}
        />
      </label>
      <button
        type="button"
        disabled={!selectedFact || !correction.trim()}
        onClick={() =>
          void api("/v1/memory/facts/correct", {
            id: selectedFact,
            text: correction,
            confirmed: true,
          })
            .then(() =>
              setResult("Preference corrected. The old value is inactive."),
            )
            .catch((issue: unknown) =>
              onError(message(issue, "Could not correct that preference.")),
            )
        }
      >
        Correct selected preference
      </button>
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
  cloudChat?: boolean;
  pace?: "auto" | "fast" | "deep";
}

export function SettingsPanel({
  health,
  connected = true,
  taskBusy = false,
  session,
  voice,
  prefs,
  setPrefs,
  onRefresh,
  onError,
  onPreviewOverlay,
  localCapabilities,
  onModelChange,
  onCloudChat,
}: {
  health: Health | undefined;
  connected?: boolean;
  taskBusy?: boolean;
  session: string;
  voice: VoiceController;
  prefs: InterfacePrefs;
  setPrefs: (next: Partial<InterfacePrefs>) => void;
  onRefresh: () => void;
  onError: (message: string) => void;
  onPreviewOverlay: () => void;
  localCapabilities?: ReactNode;
  onModelChange?: () => void;
  onCloudChat?: (value: boolean) => void;
}) {
  const localOnly = health?.runtime_mode === "local-background";
  const toggle = (path: string, label: string, key: keyof Health) => (
    <label>
      <input
        type="checkbox"
        disabled={localOnly}
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
      <h3>Chat</h3>
      {!localOnly && (
        <>
          <label>
            <input
              type="checkbox"
              checked={prefs.cloudChat === true}
              onChange={(event) => onCloudChat?.(event.target.checked)}
            />
            Cloud chat
          </label>
          <p className="hint">
            Messages go to a qualified free model. This does not approve file
            changes, computer control, private uploads, or paid inference.
          </p>
        </>
      )}
      {!localOnly && connected && health?.ready !== true && (
        <>
          <p>
            Chat needs a qualified free model. Save a provider key here.
            Immortility uses it only after the broker admits a free route.
          </p>
          <ProviderKeys health={health} onSaved={onRefresh} />
        </>
      )}
      <label>
        <input
          type="checkbox"
          checked={prefs.reduced}
          onChange={(event) => setPrefs({ reduced: event.target.checked })}
        />
        Reduce motion
      </label>
      <details className="advanced">
        <summary>Advanced</summary>
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
            <option value="2d">Minimal (2D, no WebGL)</option>
          </select>
        </label>
        <p className="hint">
          The launch command chooses the graphics chip for this run. Battery
          lowers the frame rate and resolution before it changes materials.
          Performance keeps the higher frame rate while the face is active.
        </p>
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
          Screen control (Computer Use) is disabled, so the overlay never opens
          on its own today. File reads and research never trigger it.
        </p>
        <button type="button" onClick={onPreviewOverlay}>
          Preview work overlay — no screen access
        </button>
        <h3>Runtime</h3>
        {localOnly ? (
          <p>
            Local background runtime attached. Tasks continue when this
            dashboard closes.
          </p>
        ) : (
          <p>
            Hermes {health?.hermes.version ?? ""} ·{" "}
            {health?.hermes.status ?? "unavailable"}
            {health?.hermes.message ? ` · ${health.hermes.message}` : ""}
          </p>
        )}
        <p>
          Paid inference: blocked · Code execution: disabled · Active task:{" "}
          {health?.active_task ?? "none"}
        </p>
        <button type="button" onClick={onRefresh}>
          Check connection
        </button>
        <h3>Capabilities</h3>
        {localCapabilities}
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
          "Public Wikipedia context and task-approved MCP security source retrieval. Pages are untrusted data; general web search is unavailable.",
          "web_research_enabled",
        )}
        {toggle(
          "/v1/settings/mcp",
          "Local arithmetic MCP server. External servers stay off.",
          "mcp_enabled",
        )}
        {toggle(
          "/v1/settings/standard-mcp",
          "Reviewed SDK arithmetic. Hermes needs separate permission for each task.",
          "standard_mcp_enabled",
        )}
        {toggle(
          "/v1/settings/artifacts",
          "Report files (Markdown and PDF). Each task needs separate creation permission.",
          "artifact_tools_enabled",
        )}
        {!localOnly && (
          <>
            <WorkspaceFolder
              enabled={health?.workspace_tools_enabled === true}
              onSaved={onRefresh}
            />
            <ProjectInspector
              session={session}
              connected={connected}
              busy={
                taskBusy ||
                !!health?.active_task ||
                !["IDLE", "ERROR", "CANCELLED"].includes(
                  health?.voice_state ?? "IDLE",
                )
              }
            />
            <LocalTools
              session={session}
              mcp={health?.mcp_enabled === true}
              clock={health?.local_tools_enabled === true}
              onError={onError}
            />
          </>
        )}
        <h3>Voice</h3>
        {localOnly ? (
          <p className="hint">
            Voice and model chat are unavailable in this local-only runtime.
          </p>
        ) : (
          <VoiceControls voice={voice} settings />
        )}
        {!localOnly && (
          <>
            <h3>Providers</h3>
            <ModelHub
              connected={connected}
              activeModel={health?.active_model}
              active={
                taskBusy ||
                health?.active_task != null ||
                !["IDLE", "ERROR", "CANCELLED"].includes(
                  health?.voice_state ?? "IDLE",
                ) ||
                !["IDLE", "ERROR", "CANCELLED"].includes(voice.status.state)
              }
              localOnly={localOnly}
              onError={onError}
              onChanged={() => {
                onModelChange?.();
                onRefresh();
              }}
            />
            <p>
              Credential storage:{" "}
              {health?.credential_source ?? "local environment"}
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
          </>
        )}
        <p className="hint">
          Ctrl+Shift+Space opens chat. Ctrl+Shift+Escape stops the active task.
        </p>
      </details>
    </section>
  );
}
