import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { Approval } from "../Conversation";
import {
  faceLabel,
  ROLES,
  type AgentStatus,
  type FaceState,
  type Role,
} from "../face/faceState";
import { FlatFace, type SceneStats } from "../face/HeadScene";
import type { Health, InterfacePrefs } from "../SettingsPanel";
import { terminal, type Task, type Transcript } from "../state";
import { windowAction } from "../transport";
import { Timeline } from "./Timeline";

const HeadCanvas = lazy(() => import("../face/HeadScene"));

export type View =
  | "home"
  | "chat"
  | "agents"
  | "tasks"
  | "timeline"
  | "memory"
  | "tools"
  | "settings";
const views: [View, string, string][] = [
  ["home", "Home", "⌂"],
  ["chat", "Chat", "✉"],
  ["agents", "Agents", "◈"],
  ["tasks", "Tasks", "☰"],
  ["timeline", "Timeline", "⧗"],
  ["memory", "Memory", "◎"],
  ["tools", "Tools", "⚒"],
  ["settings", "Settings", "⚙"],
];

const roleText: Record<Role, string> = {
  research: "Gathers and summarizes facts for Hermes. No tools.",
  coding: "Drafts code and technical answers for Hermes. No tools.",
  review: "Checks the other agents' drafts before Hermes replies. No tools.",
};

interface Session {
  id: string;
  created: string;
}

export interface CommandCenterProps {
  face: FaceState;
  agent?: Role;
  level: RefObject<number>;
  prefs: InterfacePrefs;
  health?: Health;
  connected: boolean;
  consent: boolean;
  micLive: boolean;
  tasks: Task[];
  transcripts: Record<string, Transcript>;
  focus?: Task;
  agents: Record<Role, AgentStatus>;
  sessions: Session[];
  session: string;
  view: View;
  setView: (view: View) => void;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onStop: () => void;
  onError: (message: string) => void;
  onCompanion: () => void;
  onQuickChat: () => void;
  chat: ReactNode;
  composer: ReactNode;
  settings: ReactNode;
  memory: ReactNode;
  voice: ReactNode;
  error: ReactNode;
}

function duration(from?: string, to?: string): string {
  if (!from) return "—";
  const ms = (to ? Date.parse(to) : Date.now()) - Date.parse(from);
  if (!Number.isFinite(ms) || ms < 0) return "—";
  return ms < 60e3
    ? `${(ms / 1000).toFixed(1)} s`
    : `${Math.round(ms / 60e3)} min`;
}

function useTick(active: boolean) {
  const [, setNow] = useState(0);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);
}

function AgentDetail({
  agent,
  task,
  transcript,
  onTimeline,
  onStop,
  onClose,
}: {
  agent: AgentStatus;
  task?: Task;
  transcript?: Transcript;
  onTimeline: () => void;
  onStop: () => void;
  onClose: () => void;
}) {
  const running = agent.status === "started";
  return (
    <aside className="agent-detail" aria-label={`${agent.role} agent details`}>
      <header>
        <h3>{agent.role} agent</h3>
        <button
          type="button"
          aria-label="Close agent details"
          onClick={onClose}
        >
          ×
        </button>
      </header>
      <dl>
        <dt>Role</dt>
        <dd>{roleText[agent.role]}</dd>
        <dt>Status</dt>
        <dd className={`status ${agent.status}`}>
          {agent.status === "off"
            ? "Off — enable specialist agents in Settings"
            : agent.status === "available"
              ? "Available, not used by this task"
              : agent.status === "started"
                ? "Running"
                : agent.status}
        </dd>
        <dt>Task</dt>
        <dd>{task ? task.input.content.slice(0, 140) : "None"}</dd>
        <dt>Route</dt>
        <dd>
          {transcript?.metrics
            ? `${transcript.metrics.route_mode} · openrouter/free via Hermes`
            : "openrouter/free via Hermes"}
        </dd>
        <dt>Duration</dt>
        <dd>{duration(agent.startedAt, agent.endedAt)}</dd>
        <dt>Tool calls</dt>
        <dd>None. Specialist agents run with every tool disabled.</dd>
        <dt>Output</dt>
        <dd>
          The broker does not report per-agent output; Hermes’ combined answer
          is in Chat.
        </dd>
        {agent.status === "failed" && (
          <>
            <dt>Error</dt>
            <dd className="error">
              Agent reported failure.{" "}
              {transcript?.error ?? task?.error?.message ?? ""}
            </dd>
          </>
        )}
      </dl>
      <div className="row">
        <button type="button" onClick={onTimeline}>
          Show in timeline
        </button>
        {running && (
          <button type="button" className="danger" onClick={onStop}>
            Stop task
          </button>
        )}
      </div>
    </aside>
  );
}

function Metrics({
  stats,
  transcript,
  connected,
}: {
  stats: SceneStats | null;
  transcript?: Transcript;
  connected: boolean;
}) {
  const memory = (
    performance as Performance & {
      memory?: { usedJSHeapSize: number };
    }
  ).memory;
  const rows: [string, string][] = [
    ["Broker", connected ? "connected" : "disconnected"],
    ["Render rate", stats ? `${stats.fps} fps` : "3D stage hidden"],
    ["Frame interval", stats ? `${stats.frameMs} ms avg` : "—"],
    ["Longest gap", stats ? `${stats.maxFrameMs} ms` : "—"],
    ["Head load", stats?.loadMs ? `${stats.loadMs} ms` : "—"],
    ["GPU", stats?.renderer || "—"],
    [
      "Draw calls",
      stats
        ? `${stats.calls} · ${Math.round(stats.triangles / 1000)}k tris`
        : "—",
    ],
    [
      "JS heap",
      memory
        ? `${Math.round(memory.usedJSHeapSize / 1048576)} MB`
        : "not exposed",
    ],
    [
      "Last route",
      transcript?.metrics
        ? `${transcript.metrics.latency_ms} ms · first token ${transcript.metrics.first_token_ms ?? "—"} ms`
        : "—",
    ],
    [
      "Tokens",
      transcript?.metrics?.prompt_tokens !== undefined
        ? `${transcript.metrics.prompt_tokens} in · ${transcript.metrics.completion_tokens ?? 0} out`
        : "—",
    ],
  ];
  return (
    <section className="card" aria-label="System metrics">
      <h2>System</h2>
      <dl className="metrics">
        {rows.map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="hint">
        Measured in this window. CPU and GPU usage are measured outside the app.
      </p>
    </section>
  );
}

function Permissions({
  health,
  consent,
  micLive,
}: {
  health?: Health;
  consent: boolean;
  micLive: boolean;
}) {
  const rows: [string, boolean | "locked", string][] = [
    [
      "Cloud model",
      consent,
      consent ? "this conversation" : "ask each conversation",
    ],
    ["Microphone", micLive, micLive ? "live now" : "off"],
    ["Specialist agents", health?.delegation_enabled === true, "no tools"],
    ["Web research", health?.web_research_enabled === true, "Wikipedia only"],
    ["Local MCP", health?.mcp_enabled === true, "arithmetic only"],
    [
      "Workspace edits",
      health?.workspace_tools_enabled === true,
      "approval required",
    ],
    ["Code execution", "locked", "disabled"],
    ["Terminal", "locked", "disabled"],
    ["Screen control", "locked", "disabled"],
    ["Paid inference", "locked", "blocked"],
  ];
  return (
    <section className="card" aria-label="Permissions">
      <h2>Permissions</h2>
      <ul className="permissions">
        {rows.map(([name, on, note]) => (
          <li
            key={name}
            className={on === "locked" ? "locked" : on ? "on" : "off"}
          >
            <span>{name}</span>
            <small>{note}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Tools({ health }: { health?: Health }) {
  const tools: [string, boolean, string][] = [
    [
      "Local clock",
      health?.local_tools_enabled === true,
      "Reads the PC clock.",
    ],
    [
      "Wikipedia research",
      health?.web_research_enabled === true,
      "One public page per request, treated as untrusted data.",
    ],
    [
      "Local MCP (arithmetic)",
      health?.mcp_enabled === true,
      "Local stdio server with an allowlist.",
    ],
    [
      "Workspace read and patch",
      health?.workspace_tools_enabled === true,
      "Reads one folder; each change needs your approval and can be rolled back.",
    ],
    ["Code execution", false, "Disabled until isolation is verified."],
    [
      "Terminal, browser, Computer Use",
      false,
      "Disabled in Hermes and the broker.",
    ],
  ];
  return (
    <div className="tool-grid">
      {tools.map(([name, on, note]) => (
        <section key={name} className={`card tool ${on ? "on" : "off"}`}>
          <h3>{name}</h3>
          <p>{note}</p>
          <small>{on ? "Enabled" : "Off"}</small>
        </section>
      ))}
      <p className="hint">Change these in Settings · Capabilities.</p>
    </div>
  );
}

export default function CommandCenter(props: CommandCenterProps) {
  const {
    face,
    focus,
    transcripts,
    tasks,
    agents,
    view,
    setView,
    prefs,
    health,
  } = props;
  const [selected, setSelected] = useState<Role | null>(null);
  const [stats, setStats] = useState<SceneStats | null>(null);
  const [agentFilter, setAgentFilter] = useState("all");
  const reset = useRef<(() => void) | null>(null);
  const live = focus ? transcripts[focus.task_id] : undefined;
  const staged = view === "home" || view === "agents";
  useEffect(() => {
    if (!staged) setStats(null);
  }, [staged]);
  const status = live?.status ?? focus?.status;
  const running = !!status && !terminal.has(status);
  useTick(running);
  const startedAt = live?.log?.[0]?.at;
  const stage = (
    <div className="stage" aria-label={`Immortility face: ${faceLabel[face]}`}>
      <Suspense fallback={<FlatFace face={face} />}>
        <HeadCanvas
          face={face}
          agent={props.agent}
          level={props.level}
          quality={prefs.quality}
          reduced={prefs.reduced}
          agents={agents}
          selected={selected}
          onSelect={(role) => setSelected(selected === role ? null : role)}
          onStats={setStats}
          reset={reset}
        />
      </Suspense>
      <div className="stage-caption">
        <span className={`state-pill ${face}`}>{faceLabel[face]}</span>
        {props.micLive && (
          <span className="live-indicator">● Microphone live</span>
        )}
      </div>
      <div className="stage-tools">
        <button
          type="button"
          onClick={() => reset.current?.()}
          title="Reset the camera"
        >
          Reset view
        </button>
      </div>
      {selected && (
        <AgentDetail
          agent={agents[selected]}
          task={focus}
          transcript={live}
          onClose={() => setSelected(null)}
          onStop={props.onStop}
          onTimeline={() => {
            setAgentFilter(selected);
            setView("timeline");
          }}
        />
      )}
    </div>
  );
  const timeline = (compact: boolean) => (
    <Timeline
      tasks={tasks}
      transcripts={transcripts}
      compact={compact}
      agentFilter={agentFilter}
      setAgentFilter={setAgentFilter}
    />
  );
  let center: ReactNode;
  switch (view) {
    case "chat":
      center = <div className="chat-view">{props.chat}</div>;
      break;
    case "timeline":
      center = timeline(false);
      break;
    case "tasks":
      center = (
        <div className="tasks-view">
          <div className="row">
            <select
              aria-label="Conversation"
              value={props.session}
              onChange={(e) => props.onSelectSession(e.target.value)}
            >
              {props.sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {new Date(s.created).toLocaleString()} · {s.id.slice(0, 6)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={props.onNewSession}
              disabled={!props.connected}
            >
              New conversation
            </button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Request</th>
                <th>Status</th>
                <th>Route</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {[...tasks].reverse().map((task) => {
                const row = transcripts[task.task_id];
                return (
                  <tr key={task.task_id}>
                    <td>{task.input.content.slice(0, 90)}</td>
                    <td className={`status ${row?.status ?? task.status}`}>
                      {(row?.status ?? task.status).replaceAll("_", " ")}
                    </td>
                    <td>{row?.metrics?.route_mode ?? "—"}</td>
                    <td>
                      {row?.metrics ? `${row.metrics.latency_ms} ms` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!tasks.length && (
            <p className="hint">No tasks in this conversation yet.</p>
          )}
        </div>
      );
      break;
    case "memory":
      center = <div className="pane">{props.memory}</div>;
      break;
    case "tools":
      center = <Tools health={health} />;
      break;
    case "settings":
      center = <div className="pane">{props.settings}</div>;
      break;
    default:
      center = stage;
  }
  return (
    <div className="command">
      <header
        className="cc-top"
        onPointerDown={(event) => {
          if (event.button === 0 && event.target === event.currentTarget)
            void windowAction("drag_free");
        }}
        onDoubleClick={(event) => {
          if (event.target === event.currentTarget)
            void windowAction("maximize");
        }}
      >
        <div className="brand">
          <img src="/models/immortility-head-2d.png" alt="" />
          <strong>IMMORTILITY</strong>
        </div>
        <span className={`state-pill ${face}`}>{faceLabel[face]}</span>
        <span className="model">
          <span
            className={`dot ${props.connected && health?.ready ? "online" : ""}`}
          />
          {props.connected
            ? health?.ready
              ? `Hermes ${health.hermes.version ?? ""} · openrouter/free`
              : "Setup required"
            : "Broker disconnected"}
        </span>
        <span className="badge">$0 · free only</span>
        <div className="window-buttons">
          <button type="button" onClick={props.onQuickChat} title="Quick chat">
            Quick chat
          </button>
          <button
            type="button"
            onClick={props.onCompanion}
            title="Return to the floating face"
          >
            Companion
          </button>
          <button
            type="button"
            onClick={() => setView("settings")}
            aria-label="Settings"
          >
            ⚙
          </button>
          <button
            type="button"
            onClick={() => void windowAction("minimize")}
            aria-label="Minimize"
          >
            –
          </button>
          <button
            type="button"
            onClick={() => void windowAction("maximize")}
            aria-label="Maximize or restore"
          >
            ▢
          </button>
          <button
            type="button"
            onClick={props.onCompanion}
            aria-label="Close command center"
          >
            ×
          </button>
        </div>
      </header>
      <nav className="cc-nav" aria-label="Command center">
        {views.map(([id, label, icon]) => (
          <button
            key={id}
            type="button"
            aria-current={view === id ? "page" : undefined}
            className={view === id ? "current" : ""}
            onClick={() => setView(id)}
          >
            <span aria-hidden="true">{icon}</span>
            {label}
          </button>
        ))}
        <p className="hint">Workflows and Projects are not implemented yet.</p>
      </nav>
      <main className={`cc-main view-${view}`}>{center}</main>
      <aside className="cc-side" aria-label="Status">
        <section className="card active-task" aria-label="Active task">
          <h2>{running ? "Active task" : "Latest task"}</h2>
          {focus ? (
            <>
              <p className="task-title">{focus.input.content.slice(0, 120)}</p>
              <p className={`status ${status}`}>
                {status?.replaceAll("_", " ")} · {faceLabel[face]}
                {running && startedAt ? ` · ${duration(startedAt)}` : ""}
              </p>
              {status === "awaiting_approval" && (
                <>
                  {live?.preview && (
                    <pre className="diff-preview">{live.preview}</pre>
                  )}
                  <Approval taskId={focus.task_id} onError={props.onError} />
                </>
              )}
              {running && (
                <button type="button" className="danger" onClick={props.onStop}>
                  Stop
                </button>
              )}
            </>
          ) : (
            <p className="hint">Nothing yet. Send a message below.</p>
          )}
        </section>
        <section className="card" aria-label="Agents">
          <h2>Agents</h2>
          <ul className="agents">
            {ROLES.map((role) => (
              <li key={role}>
                <button
                  type="button"
                  className={agents[role].status}
                  onClick={() => {
                    setSelected(role);
                    setView("home");
                  }}
                >
                  <span>{role}</span>
                  <small>
                    {agents[role].status === "started"
                      ? "running"
                      : agents[role].status}
                    {agents[role].startedAt
                      ? ` · ${duration(agents[role].startedAt, agents[role].endedAt)}`
                      : ""}
                  </small>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="card voice-card" aria-label="Voice">
          <h2>Voice</h2>
          {props.voice}
        </section>
        <Metrics stats={stats} transcript={live} connected={props.connected} />
        <Permissions
          health={health}
          consent={props.consent}
          micLive={props.micLive}
        />
      </aside>
      <footer className="cc-bottom">
        {props.error}
        {view !== "timeline" && view !== "chat" && timeline(true)}
        {props.composer}
      </footer>
    </div>
  );
}
