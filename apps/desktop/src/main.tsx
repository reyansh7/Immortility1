import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { createRoot } from "react-dom/client";
import { listen } from "@tauri-apps/api/event";
import { api, connect, stream, windowAction } from "./transport";
import {
  orbState,
  reduceEvent,
  terminal,
  type Task,
  type Transcript,
} from "./state";
import "./style.css";
import { useVoice } from "./useVoice";
import { VoiceControls } from "./VoiceControls";

const CommandCenter = lazy(() => import("./command/CommandCenter"));

interface Health {
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
interface Session {
  id: string;
  created: string;
}
const providers = [
  ["openrouter", "OpenRouter"],
  ["gemini", "Gemini"],
  ["groq", "Groq"],
] as const;

function ProviderKeys({
  health,
  onSaved,
}: {
  health: Health | null | undefined;
  onSaved: () => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  async function save(event: FormEvent, provider: string) {
    event.preventDefault();
    const apiKey = drafts[provider] ?? "";
    try {
      await api("/v1/settings/provider-key", { provider, api_key: apiKey });
      setDrafts((current) => ({ ...current, [provider]: "" }));
      setNotes((current) => ({
        ...current,
        [provider]: "Saved in Windows Credential Manager.",
      }));
      onSaved();
    } catch (issue) {
      setNotes((current) => ({
        ...current,
        [provider]:
          issue instanceof Error ? issue.message : "Could not save the key.",
      }));
    }
  }
  return (
    <>
      <p className="hint">
        Keys stay in Windows Credential Manager on this PC. Chat still uses the
        free OpenRouter route.
      </p>
      {providers.map(([provider, label]) => (
        <form
          className="key-form"
          key={provider}
          onSubmit={(event) => void save(event, provider)}
        >
          <p>
            <b>{label}</b>
            <br />
            {health?.providers?.[provider] ?? "missing key"}
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

interface ExecutionTrace {
  outcome: string;
  duration_ms: number;
  transitions: { state: string; timestamp: string }[];
  delegations?: { role: string; status: string }[];
  tools: { status: string; calls: unknown[] };
  agent: { runtime: string; route: string };
  completion_evidence: { streamed_chunks: number };
}

function AgentBoard({
  events,
  running,
  onCancel,
}: {
  events: string[];
  running: boolean;
  onCancel: () => void;
}) {
  const latest = new Map<string, string>();
  for (const item of events) {
    const match = /^(research|coding|review) (\S+)/.exec(item);
    if (match) latest.set(match[1], match[2]);
  }
  if (latest.size === 0) return null;
  return (
    <div className="agent-board" aria-label="Live specialist agents">
      <div className="agent-hub">Immortility</div>
      <div className="agent-nodes">
        {["research", "coding", "review"]
          .filter((role) => latest.has(role))
          .map((role) => (
            <div key={role} className={`agent-node ${latest.get(role) ?? ""}`}>
              <b>{role}</b>
              <span>{latest.get(role)}</span>
            </div>
          ))}
      </div>
      {running && (
        <button type="button" onClick={onCancel}>
          Cancel task
        </button>
      )}
    </div>
  );
}

function LocalTools({
  session,
  mcp,
  onError,
}: {
  session: string;
  mcp: boolean;
  onError: (message: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<{ task_id: string; body: string }[]>(
    [],
  );
  const [sum, setSum] = useState("");
  return (
    <div className="workspace">
      {mcp && (
        <button
          type="button"
          onClick={() =>
            void api<{ result: string }>("/v1/mcp/call", {
              name: "add",
              a: 2,
              b: 2,
            })
              .then((body) => setSum(body.result))
              .catch((issue: unknown) =>
                onError(issue instanceof Error ? issue.message : "MCP failed."),
              )
          }
        >
          Ask local MCP for 2 + 2
        </button>
      )}
      {sum && <p>Local MCP result: {sum}</p>}
      <label>
        Search this conversation
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <button
        type="button"
        onClick={() =>
          void api<{ matches: { task_id: string; body: string }[] }>(
            "/v1/memory/search",
            { session_id: session, query },
          )
            .then((body) => setMatches(body.matches))
            .catch((issue: unknown) =>
              onError(
                issue instanceof Error
                  ? issue.message
                  : "Memory search failed.",
              ),
            )
        }
      >
        Search memory
      </button>
      {matches.map((item) => (
        <p key={item.task_id}>
          {item.body}
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
            Delete
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
              setProblem(
                issue instanceof Error
                  ? issue.message
                  : "Workspace was rejected.",
              ),
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
                setProblem(
                  issue instanceof Error
                    ? issue.message
                    : "Could not turn this off.",
                ),
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

function LocalClock({ enabled }: { enabled: boolean }) {
  const [result, setResult] = useState("");
  const [problem, setProblem] = useState("");
  if (!enabled) return null;
  return (
    <div>
      <button
        type="button"
        onClick={() =>
          void api<{ result: string }>("/v1/tools/call", {
            name: "clock",
          }).then(
            (row) => {
              setResult(row.result);
              setProblem("");
            },
            (issue: unknown) =>
              setProblem(
                issue instanceof Error ? issue.message : "Clock failed.",
              ),
          )
        }
      >
        Read local clock
      </button>
      {result && <p>Local clock: {result}</p>}
      {problem && <p className="error">{problem}</p>}
    </div>
  );
}

function TaskTrace({ taskId }: { taskId: string }) {
  const [trace, setTrace] = useState<ExecutionTrace | null>(null);
  const [error, setError] = useState("");
  function load(open: boolean) {
    if (!open || trace || error) return;
    void api<ExecutionTrace>(`/v1/tasks/${taskId}/trace`)
      .then(setTrace)
      .catch((issue: unknown) =>
        setError(issue instanceof Error ? issue.message : "Trace unavailable."),
      );
  }
  return (
    <details onToggle={(event) => load(event.currentTarget.open)}>
      <summary>Execution trace</summary>
      {error && <p className="error">{error}</p>}
      {trace && (
        <div className="trace">
          <p>
            {trace.agent.runtime} · {trace.agent.route} · {trace.outcome} ·{" "}
            {Math.round(trace.duration_ms)} ms · tools {trace.tools.status} ·{" "}
            {trace.completion_evidence.streamed_chunks} streamed parts
          </p>
          {(trace.delegations ?? []).length > 0 && (
            <ol>
              {(trace.delegations ?? []).map((step, index) => (
                <li key={`${step.role}-${step.status}-${index}`}>
                  {step.role} {step.status}
                </li>
              ))}
            </ol>
          )}
          <ol>
            {trace.transitions.map((step, index) => (
              <li key={`${step.state}-${index}`}>{step.state}</li>
            ))}
          </ol>
        </div>
      )}
    </details>
  );
}

const blank: Transcript = {
  text: "",
  sequence: 0,
  status: "created",
  events: [],
};
function App() {
  const [expanded, setExpanded] = useState(false),
    [settings, setSettings] = useState(false);
  const [health, setHealth] = useState<Health>(),
    [sessions, setSessions] = useState<Session[]>([]),
    [session, setSession] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]),
    [transcripts, setTranscripts] = useState<Record<string, Transcript>>({});
  const [input, setInput] = useState(""),
    [error, setError] = useState(""),
    [connected, setConnected] = useState(false),
    [sending, setSending] = useState(false),
    [command, setCommand] = useState(false);
  const [consent, setConsent] = useState(false),
    [pin, setPin] = useState(true),
    [reduced, setReduced] = useState(false);
  const streamAbort = useRef<AbortController | null>(null),
    sessionRef = useRef(""),
    lastRequest = useRef<{
      session_id: string;
      request_id: string;
      content: string;
      cloud_consent: true;
    } | null>(null);
  const tasksRef = useRef(tasks);
  tasksRef.current = tasks;
  const tail = useRef<HTMLDivElement>(null);
  function moveWithKeyboard(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    event.preventDefault();
    void windowAction(
      event.key === "ArrowUp" ? "nudge_up" : "nudge_down",
    ).catch(() => setError("Unable to move the companion window."));
  }
  const active = tasks.find(
    (t) => !terminal.has(transcripts[t.task_id]?.status ?? t.status),
  );
  const chatState = orbState(
    active
      ? (transcripts[active.task_id]?.status ?? active.status)
      : tasks.length
        ? (transcripts[tasks.at(-1)!.task_id]?.status ?? tasks.at(-1)!.status)
        : undefined,
    connected && !!health?.ready,
  );
  const changeWindow = useCallback(async (open: boolean) => {
    try {
      await windowAction(open ? "expand" : "collapse");
      setExpanded(open);
    } catch {
      setExpanded(true);
    }
  }, []);
  const watch = useCallback(async (task: Task) => {
    streamAbort.current?.abort();
    const controller = new AbortController();
    streamAbort.current = controller;
    // Replay from the beginning and deduplicate sequence numbers after reconnect.
    try {
      await stream(
        task.task_id,
        0,
        (event) => {
          setTranscripts((previous) => ({
            ...previous,
            [task.task_id]: reduceEvent(previous[task.task_id] ?? blank, event),
          }));
        },
        controller.signal,
      );
      const fresh = await api<Task>(`/v1/tasks/${task.task_id}`);
      setTasks((previous) =>
        previous.map((t) => (t.task_id === fresh.task_id ? fresh : t)),
      );
    } catch (issue) {
      if (!controller.signal.aborted)
        setError(
          issue instanceof Error ? issue.message : "Stream interrupted.",
        );
    }
  }, []);
  const onVoiceTask = useCallback(
    (task: Task) => {
      setTasks((previous) =>
        previous.some((t) => t.task_id === task.task_id)
          ? previous
          : [...previous, task],
      );
      if (!terminal.has(task.status)) void watch(task);
    },
    [watch],
  );
  const voice = useVoice(session, consent, onVoiceTask, setInput);
  const voiceStates = {
    LISTENING: "listening",
    TRANSCRIBING: "transcribing",
    THINKING: "thinking",
    SPEAKING: "speaking",
    CANCELLED: "cancelled",
    ERROR: "error",
  } as const;
  const state =
    voice.status.tts_state === "loading"
      ? "thinking"
      : voice.status.state in voiceStates
        ? voiceStates[voice.status.state as keyof typeof voiceStates]
        : chatState;
  const selectSession = useCallback(
    async (id: string) => {
      streamAbort.current?.abort();
      sessionRef.current = id;
      setSession(id);
      setError("");
      setConsent(false);
      try {
        const rows = await api<Task[]>(`/v1/sessions/${id}/tasks`);
        if (sessionRef.current !== id) return;
        setTasks(rows);
        const running = rows.find((t) => !terminal.has(t.status));
        if (running) void watch(running);
      } catch (issue) {
        setError(String(issue));
      }
    },
    [watch],
  );
  const refresh = useCallback(async () => {
    setError("");
    try {
      await connect();
      const [status, rows] = await Promise.all([
        api<Health>("/health/ready"),
        api<Session[]>("/v1/sessions"),
      ]);
      setHealth(status);
      setConnected(true);
      setSessions(rows);
      if (!sessionRef.current) {
        const chosen = rows[0] ?? (await api<Session>("/v1/sessions", {}));
        if (!rows.length) setSessions([chosen]);
        await selectSession(chosen.id);
      } else {
        const running = tasksRef.current.find((t) => !terminal.has(t.status));
        if (running) void watch(running);
      }
    } catch (issue) {
      setConnected(false);
      setError(
        issue instanceof Error
          ? issue.message
          : "Unable to start local service.",
      );
    }
  }, [selectSession, watch]);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      void api<Health>("/health/ready")
        .then((h) => {
          setHealth(h);
          setConnected(true);
        })
        .catch(() => setConnected(false));
    }, 15000);
    const listeners = [
      listen("toggle-chat", () => {
        void changeWindow(true);
      }),
      listen("global-stop", () => {
        void api("/v1/stop", {}).catch(() =>
          setError("Stop could not reach the broker."),
        );
      }),
    ];
    return () => {
      clearInterval(timer);
      streamAbort.current?.abort();
      for (const pending of listeners)
        void pending.then((unlisten) => unlisten()).catch(() => {});
    };
  }, [refresh, changeWindow]);
  useEffect(() => {
    tail.current?.scrollIntoView({ behavior: reduced ? "instant" : "smooth" });
  }, [transcripts, reduced]);
  async function send() {
    if (
      !input.trim() ||
      sending ||
      active ||
      !consent ||
      !["IDLE", "ERROR", "CANCELLED"].includes(voice.status.state)
    )
      return;
    setSending(true);
    setError("");
    const request =
      lastRequest.current?.content === input &&
      lastRequest.current.session_id === session
        ? lastRequest.current
        : {
            session_id: session,
            request_id: crypto.randomUUID(),
            content: input,
            cloud_consent: true as const,
          };
    lastRequest.current = request;
    try {
      const task = await api<Task>("/v1/tasks", request);
      setTasks((previous) =>
        previous.some((t) => t.task_id === task.task_id)
          ? previous
          : [...previous, task],
      );
      setInput("");
      lastRequest.current = null;
      if (!terminal.has(task.status)) void watch(task);
    } catch (issue) {
      setError(
        issue instanceof Error ? issue.message : "Message could not be sent.",
      );
    } finally {
      setSending(false);
    }
  }
  async function newSession() {
    try {
      const row = await api<Session>("/v1/sessions", {});
      setSessions((previous) => [row, ...previous]);
      await selectSession(row.id);
    } catch {
      setError("Could not create a conversation.");
    }
  }
  return (
    <main
      className={`${expanded ? "expanded" : "compact"} ${reduced ? "reduced" : ""}`}
      onKeyDown={(event) => {
        if (event.key === "Escape") void changeWindow(false);
      }}
    >
      {expanded && (
        <section className="panel" aria-label="Immortility companion">
          <header>
            <div className="identity">
              <span className="mark">I</span>
              <div>
                <strong>IMMORTILITY</strong>
                <small>Your local companion</small>
              </div>
            </div>
            <div className="header-actions">
              <button
                aria-label="Command center"
                onClick={() => setCommand(!command)}
              >
                Face
              </button>
              <button
                aria-label="Settings"
                onClick={() => setSettings(!settings)}
              >
                ⚙
              </button>
              <button
                aria-label="Collapse chat"
                onClick={() => void changeWindow(false)}
              >
                −
              </button>
            </div>
          </header>
          <div className="connection">
            <span
              className={`dot ${connected && health?.ready ? "online" : ""}`}
            />
            <span>
              {connected
                ? health?.ready
                  ? "Hermes connected"
                  : "Setup required"
                : "Broker disconnected"}
            </span>
            <span className="badge">$0 LOCKED</span>
          </div>
          {settings ? (
            <section className="settings" aria-label="Settings">
              <h2>Private by default.</h2>
              <p>
                Text is sent to the free cloud model only when you consent.
                Conversation history stays in local SQLite.
              </p>
              <h3>Runtime</h3>
              <p>
                Hermes {health?.hermes.version ?? ""} ·{" "}
                {health?.hermes.status ?? "unavailable"}
              </p>
              {health?.hermes.message && <p>{health.hermes.message}</p>}
              <h3>Providers</h3>
              <p>
                Credential storage:{" "}
                {health?.credential_source ?? "local environment"}
              </p>
              <button
                onClick={() =>
                  void api("/v1/settings/migrate-credentials", {})
                    .then(() => refresh())
                    .catch((issue) => setError(String(issue)))
                }
              >
                Move .env keys to Windows Credential Manager
              </button>
              <ProviderKeys health={health} onSaved={() => void refresh()} />
              <label>
                <input
                  type="checkbox"
                  checked={health?.delegation_enabled === true}
                  onChange={(event) =>
                    void api("/v1/settings/delegation", {
                      enabled: event.target.checked,
                    })
                      .then(() => refresh())
                      .catch((issue) => setError(String(issue)))
                  }
                />
                Specialist agents (research, coding, review). No tools.
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={health?.local_tools_enabled === true}
                  onChange={(event) =>
                    void api("/v1/settings/local-tools", {
                      enabled: event.target.checked,
                    })
                      .then(() => refresh())
                      .catch((issue) => setError(String(issue)))
                  }
                />
                Local clock tool. Terminal and files stay off.
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={health?.web_research_enabled === true}
                  onChange={(event) =>
                    void api("/v1/settings/web-research", {
                      enabled: event.target.checked,
                    })
                      .then(() => refresh())
                      .catch((issue) => setError(String(issue)))
                  }
                />
                Public Wikipedia research. Pages are untrusted data.
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={health?.mcp_enabled === true}
                  onChange={(event) =>
                    void api("/v1/settings/mcp", {
                      enabled: event.target.checked,
                    })
                      .then(() => refresh())
                      .catch((issue) => setError(String(issue)))
                  }
                />
                Local arithmetic MCP server. External servers stay off.
              </label>
              <LocalTools
                session={session}
                mcp={health?.mcp_enabled === true}
                onError={setError}
              />
              <LocalClock enabled={health?.local_tools_enabled === true} />
              <WorkspaceFolder
                enabled={health?.workspace_tools_enabled === true}
                onSaved={() => void refresh()}
              />
              <label>
                <input
                  type="checkbox"
                  checked={pin}
                  onChange={(e) => {
                    setPin(e.target.checked);
                    void windowAction(e.target.checked ? "pin" : "unpin");
                  }}
                />
                Always on top
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={reduced}
                  onChange={(e) => setReduced(e.target.checked)}
                />
                Reduce animation
              </label>
              <VoiceControls voice={voice} settings />
              <label>
                <input type="checkbox" disabled />
                Screen capture · planned in Phase 3
              </label>
              <p>
                Code execution: disabled. Paid inference: blocked. Active task:{" "}
                {health?.active_task ?? "none"}.
              </p>
              <button onClick={() => void refresh()}>Check connection</button>
              <p className="hint">
                Ctrl+Shift+Space opens chat. Ctrl+Shift+Escape stops the active
                task.
              </p>
            </section>
          ) : (
            <>
              <nav aria-label="Conversations">
                <select
                  aria-label="Conversation"
                  value={session}
                  onChange={(e) => void selectSession(e.target.value)}
                >
                  {sessions.map((s, index) => (
                    <option key={s.id} value={s.id}>
                      {index === 0
                        ? "Latest"
                        : new Date(s.created).toLocaleString()}{" "}
                      · {s.id.slice(0, 6)}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => void newSession()}
                  disabled={!connected}
                  aria-label="New conversation"
                >
                  ＋
                </button>
              </nav>
              <div
                className="timeline"
                role="log"
                aria-label="Conversation history"
                aria-live="polite"
                aria-relevant="additions text"
              >
                {!tasks.length && (
                  <div className="welcome">
                    <span className="eyebrow">A QUIET PLACE TO THINK</span>
                    <h1>
                      What’s on
                      <br />
                      your mind?
                    </h1>
                    <p>
                      {health?.ready
                        ? "A conversation with Hermes. No tools or screen access."
                        : "Set OPENROUTER_API_KEY in your local .env, then restart. A verified Hermes installation is also required."}
                    </p>
                    <p className="hint">
                      No simulated answers. Free availability is checked on
                      every request.
                    </p>
                  </div>
                )}
                {tasks.map((task) => {
                  const live = transcripts[task.task_id],
                    status = live?.status ?? task.status,
                    text = task.result?.text ?? live?.text;
                  return (
                    <article key={task.task_id}>
                      <div className="user-message">
                        <small>YOU</small>
                        <p>{task.input.content}</p>
                      </div>
                      <div className="assistant-message">
                        <small>
                          IMMORTILITY <span>Hermes · OpenRouter / free</span>
                        </small>
                        {text && <p>{text}</p>}
                        {!text && !terminal.has(status) && (
                          <p className="waiting">Waiting for Hermes…</p>
                        )}
                        {command && (
                          <Suspense fallback={<p>Loading command center…</p>}>
                            <CommandCenter
                              active={
                                status === "running" ||
                                status === "verifying" ||
                                status === "awaiting_approval"
                              }
                              speaking={voice.status.tts_state === "speaking"}
                              reduced={reduced}
                              flat={reduced}
                              events={live?.events ?? []}
                            />
                          </Suspense>
                        )}
                        {live?.preview && (
                          <pre className="diff-preview">{live.preview}</pre>
                        )}
                        {live?.metrics && (
                          <p className="hint">
                            {live.metrics.route_mode} · {live.metrics.calls}{" "}
                            model calls · {live.metrics.latency_ms} ms
                            {live.metrics.first_token_ms !== undefined
                              ? ` · first token ${live.metrics.first_token_ms} ms`
                              : ""}
                            {live.metrics.prompt_tokens !== undefined
                              ? ` · ${live.metrics.prompt_tokens} prompt tokens`
                              : ""}
                            {live.metrics.completion_tokens !== undefined
                              ? ` · ${live.metrics.completion_tokens} completion tokens`
                              : ""}
                          </p>
                        )}
                        {status === "awaiting_approval" && (
                          <div className="approval">
                            <button
                              type="button"
                              onClick={() =>
                                void api(`/v1/tasks/${task.task_id}/approval`, {
                                  decision: "approve",
                                }).catch((issue: unknown) =>
                                  setError(
                                    issue instanceof Error
                                      ? issue.message
                                      : "Approval failed.",
                                  ),
                                )
                              }
                            >
                              Approve change
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                void api(`/v1/tasks/${task.task_id}/approval`, {
                                  decision: "deny",
                                }).catch((issue: unknown) =>
                                  setError(
                                    issue instanceof Error
                                      ? issue.message
                                      : "Could not deny the change.",
                                  ),
                                )
                              }
                            >
                              Deny change
                            </button>
                          </div>
                        )}
                        <AgentBoard
                          events={live?.events ?? []}
                          running={!terminal.has(status)}
                          onCancel={() =>
                            void api(
                              `/v1/tasks/${task.task_id}/cancel`,
                              {},
                            ).catch((issue: unknown) =>
                              setError(
                                issue instanceof Error
                                  ? issue.message
                                  : "Cancel failed.",
                              ),
                            )
                          }
                        />
                        <div className="task-status">
                          {status.replaceAll("_", " ")}
                          {status === "cancelled"
                            ? " · partial response retained"
                            : ""}
                          {live?.events
                            .filter((item) =>
                              /^(research|coding|review) /.test(item),
                            )
                            .map((item) => ` · ${item}`)}
                        </div>
                        {(task.error?.message ?? live?.error) && (
                          <p className="error" role="alert">
                            {task.error?.message ?? live?.error}
                          </p>
                        )}
                        <TaskTrace taskId={task.task_id} />
                        {status === "succeeded" && (
                          <button
                            type="button"
                            onClick={() => void voice.speak(task.task_id)}
                          >
                            Read aloud
                          </button>
                        )}
                        {status === "succeeded" && live?.preview && (
                          <button
                            type="button"
                            onClick={() =>
                              void api(
                                `/v1/tasks/${task.task_id}/rollback`,
                                {},
                              ).catch((issue: unknown) =>
                                setError(
                                  issue instanceof Error
                                    ? issue.message
                                    : "Rollback failed.",
                                ),
                              )
                            }
                          >
                            Restore previous file
                          </button>
                        )}
                      </div>
                    </article>
                  );
                })}
                <div ref={tail} />
              </div>
              {error && (
                <div role="alert" className="error service-error">
                  {error}
                  <button onClick={() => void refresh()}>Reconnect</button>
                </div>
              )}
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void send();
                }}
              >
                <label className="consent">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => {
                      setConsent(e.target.checked);
                      if (!e.target.checked) {
                        void api("/v1/stop", {}).catch(() =>
                          setError("Stop could not reach the broker."),
                        );
                      }
                    }}
                  />
                  Allow this conversation’s text to the free cloud provider.
                </label>
                <div className="composer">
                  <textarea
                    aria-label="Message Hermes"
                    placeholder="Ask anything. Start here."
                    maxLength={16000}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        void send();
                      }
                    }}
                  />
                  {active ? (
                    <button
                      className="send stop"
                      type="button"
                      onClick={() =>
                        void api("/v1/stop", {})
                          .then(() => api<Task>(`/v1/tasks/${active.task_id}`))
                          .then((task) =>
                            setTasks((previous) =>
                              previous.map((t) =>
                                t.task_id === task.task_id ? task : t,
                              ),
                            ),
                          )
                          .catch(() =>
                            setError("Stop failed; use the tray stop action."),
                          )
                      }
                    >
                      Stop
                    </button>
                  ) : (
                    <button
                      className="send"
                      type="submit"
                      aria-label="Send message"
                      disabled={
                        !connected ||
                        !health?.ready ||
                        !consent ||
                        sending ||
                        !input.trim()
                      }
                    >
                      ↑
                    </button>
                  )}
                </div>
                <div className="footer-note">
                  <span>Local voice · tools off</span>
                  <span>Enter to send · Shift+Enter for a new line</span>
                </div>
              </form>
              <VoiceControls voice={voice} />
            </>
          )}
          <footer>
            <button
              onPointerDown={(e) => {
                if (e.button === 0) void windowAction("drag");
              }}
              aria-label="Drag companion"
              title="Drag to move, or focus and use Up/Down arrows"
              onKeyDown={moveWithKeyboard}
            >
              ⠿ Move
            </button>
            <span>LOCAL FIRST / PHASE 2</span>
          </footer>
        </section>
      )}
      <div className="orb-dock">
        <button
          className={`orb ${state}`}
          style={
            {
              "--audio-level": Math.max(0, Math.min(1, voice.status.level)),
            } as React.CSSProperties
          }
          aria-label={`${expanded ? "Collapse" : "Open"} Immortility — ${state}`}
          title={`Immortility · ${state}`}
          onClick={() => void changeWindow(!expanded)}
        >
          <span className="orb-ring" />
          <span className="orb-core" />
          <span className="orb-status" />
        </button>
        {!expanded && (
          <button
            className="drag-handle"
            aria-label="Drag orb"
            title="Drag to move, or focus and use Up/Down arrows"
            onKeyDown={moveWithKeyboard}
            onPointerDown={() => void windowAction("drag")}
          >
            ⠿
          </button>
        )}
      </div>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
