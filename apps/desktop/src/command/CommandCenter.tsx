import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type CSSProperties,
  type ReactNode,
  type RefObject,
} from "react";
import { Approval } from "../Conversation";
import {
  faceLabel,
  presenceLabel,
  openTool,
  ROLES,
  type AgentStatus,
  type FaceState,
  type Role,
} from "../face/faceState";
import { FACE_IMAGE, FlatFace } from "../face/FlatFace";
import { EXPRESSIONS } from "../face/rig";
import type { Health, InterfacePrefs } from "../SettingsPanel";
import { terminal, type Task, type Transcript } from "../state";
import { windowAction } from "../transport";
import {
  Backdrop,
  Counter,
  gsap,
  Sparkline,
  useGSAP,
  useHistory,
  useMagnetic,
  useReducedMotion,
  useTilt,
} from "../ui/motion";
import { Icon, type IconName } from "../ui/Icon";
import { publishStats, useNow, useSceneStats } from "../ui/sceneStats";
import { greeting, summarize } from "./stats";
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
const views: [View, string, IconName][] = [
  ["home", "Home", "home"],
  ["chat", "Chat", "chat"],
  ["agents", "Agents", "agents"],
  ["tasks", "Tasks", "tasks"],
  ["timeline", "Timeline", "timeline"],
  ["memory", "Memory", "memory"],
  ["tools", "Tools", "tools"],
  ["settings", "Settings", "settings"],
];

const roleText: Record<Role, string> = {
  research: "Gathers and summarizes facts for Hermes. No tools.",
  coding: "Drafts code and technical answers for Hermes. No tools.",
  review: "Checks the other agents' drafts before Hermes replies. No tools.",
};
// Specialists differ by glyph and position, not by rainbow colour.
const roleColor: Record<Role, string> = {
  research: "#ff5a5f",
  coding: "#ff2b47",
  review: "#d3172f",
};
const roleIcon: Record<Role, IconName> = {
  research: "globe",
  coding: "code",
  review: "shield",
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
  starting?: boolean;
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

/** Live duration that re-renders itself, not the whole command center. */
function Elapsed({ from, to }: { from?: string; to?: string }) {
  useNow(!!from && !to);
  return <>{duration(from, to)}</>;
}

type Spot = "lt" | "lb" | "rt" | "rb";
const roleSpot: Record<Role, Spot> = {
  research: "lt",
  review: "lb",
  coding: "rt",
};
const anchor: Record<Spot, [number, number]> = {
  lt: [16, 33],
  lb: [16, 63],
  rt: [84, 33],
  rb: [84, 63],
};
const core: [number, number] = [50, 46];
function beam([x, y]: [number, number]): string {
  const [cx, cy] = core;
  const mx = (x + cx) / 2;
  return `M${cx},${cy} C${mx},${cy} ${mx},${y} ${x},${y}`;
}
const nodeStatus: Record<AgentStatus["status"], string> = {
  off: "Disabled",
  available: "Standby",
  started: "Running",
  succeeded: "Returned",
  failed: "Failed",
};

/**
 * Specialist network around the face chamber. Every state shown comes from
 * broker agent.* events (agentStatuses); nothing animates without one.
 */
function AgentNetwork({
  agents,
  selected,
  active,
  route,
  onSelect,
}: {
  agents: Record<Role, AgentStatus>;
  selected: Role | null;
  active?: Role;
  route: string;
  onSelect: (role: Role) => void;
}) {
  return (
    <>
      <svg
        className="network"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {ROLES.map((role) => (
          <path
            key={role}
            d={beam(anchor[roleSpot[role]])}
            className={`beam ${agents[role].status} ${active === role ? "live" : ""}`}
            vectorEffect="non-scaling-stroke"
          />
        ))}
        <path
          d={beam(anchor.rb)}
          className="beam route"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      {ROLES.map((role) => {
        const agent = agents[role];
        return (
          <button
            key={role}
            type="button"
            className={`node spot-${roleSpot[role]} ${agent.status} ${active === role ? "live" : ""} ${selected === role ? "selected" : ""}`}
            aria-pressed={selected === role}
            aria-label={`${role} specialist: ${nodeStatus[agent.status]}`}
            onClick={() => onSelect(role)}
          >
            <span className="node-core">
              <Icon name={roleIcon[role]} />
            </span>
            <span className="node-text">
              <strong>{role}</strong>
              <small>
                <i className="node-light" />
                {nodeStatus[agent.status]}
                {agent.startedAt && (
                  <>
                    {" · "}
                    <Elapsed from={agent.startedAt} to={agent.endedAt} />
                  </>
                )}
              </small>
            </span>
          </button>
        );
      })}
      <div className="node spot-rb route" aria-label={`Hermes route: ${route}`}>
        <span className="node-core">
          <Icon name="chip" />
        </span>
        <span className="node-text">
          <strong>Hermes</strong>
          <small>
            <i className="node-light" />
            {route}
          </small>
        </span>
      </div>
    </>
  );
}

/** Glass card with cursor tilt and a moving sheen. */
function Card({
  className = "",
  label,
  children,
  tilt = 0,
}: {
  className?: string;
  label: string;
  children: ReactNode;
  tilt?: number;
}) {
  const ref = useTilt<HTMLElement>(tilt);
  return (
    <section ref={ref} className={`card ${className}`} aria-label={label}>
      <span className="sheen" aria-hidden="true" />
      {children}
    </section>
  );
}

function MagneticButton({
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  const ref = useMagnetic<HTMLButtonElement>(0.25);
  return (
    <button ref={ref} type="button" className={className} {...rest}>
      {children}
    </button>
  );
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
    <aside
      className="agent-detail"
      aria-label={`${agent.role} agent details`}
      style={{ "--role": roleColor[agent.role] } as CSSProperties}
    >
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
        <dd>
          <Elapsed from={agent.startedAt} to={agent.endedAt} />
        </dd>
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
  transcript,
  connected,
}: {
  transcript?: Transcript;
  connected: boolean;
}) {
  const stats = useSceneStats();
  const memory = (
    performance as Performance & {
      memory?: { usedJSHeapSize: number };
    }
  ).memory;
  const fpsHistory = useHistory(stats?.fps, 30);
  const rows: [string, string][] = [
    ["Broker", connected ? "connected" : "disconnected"],
    ["Frame interval", stats ? `${stats.frameMs} ms avg` : "—"],
    ["Frame p95", stats ? `${stats.p95FrameMs} ms` : "—"],
    ["Longest gap", stats ? `${stats.maxFrameMs} ms` : "—"],
    ["Head load", stats?.loadMs ? `${stats.loadMs} ms` : "—"],
    ["GPU", stats?.renderer || "—"],
    [
      "Draw calls",
      stats
        ? `${stats.calls} · ${(stats.triangles / 1000).toFixed(1)}k tris`
        : "—",
    ],
    [
      "GPU resources",
      stats
        ? `${stats.textures} tex · ${stats.geometries} geo · ${stats.programs} prog`
        : "—",
    ],
    [
      "Post passes",
      stats ? (stats.passes ? `${stats.passes} (bloom)` : "none") : "—",
    ],
    [
      "Idle budget",
      stats ? (stats.budget ? `${stats.budget} fps cap` : "on change") : "—",
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
    <Card label="System metrics" className="system">
      <h2>
        <Icon name="pulse" /> System
      </h2>
      <div className="fps-row">
        <div>
          <strong className="big">
            {stats ? <Counter value={stats.fps} /> : "—"}
          </strong>
          <small>{stats ? "fps · render rate" : "3D stage hidden"}</small>
        </div>
        <Sparkline
          values={fpsHistory}
          color="var(--energy)"
          label="Render rate history"
        />
      </div>
      <dl className="metrics">
        {rows.map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd title={value}>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="hint">
        Measured in this window. CPU and GPU usage are measured outside the app.
      </p>
    </Card>
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
    ["Cloud model", consent, consent ? "allowed" : "off"],
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
    <Card label="Permissions" className="perm-card">
      <h2>
        <Icon name="shield" /> Permissions
      </h2>
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
    </Card>
  );
}

function Tools({ health }: { health?: Health }) {
  const tools: [string, boolean, string, IconName][] = [
    [
      "Local clock",
      health?.local_tools_enabled === true,
      "Reads the PC clock.",
      "clock",
    ],
    [
      "Wikipedia research",
      health?.web_research_enabled === true,
      "One public page per request, treated as untrusted data.",
      "globe",
    ],
    [
      "Local MCP (arithmetic)",
      health?.mcp_enabled === true,
      "Local stdio server with an allowlist.",
      "chip",
    ],
    [
      "Workspace read and patch",
      health?.workspace_tools_enabled === true,
      "Reads one folder; each change needs your approval and can be rolled back.",
      "folder",
    ],
    ["Code execution", false, "Disabled until isolation is verified.", "code"],
    [
      "Terminal, browser, Computer Use",
      false,
      "Disabled in Hermes and the broker.",
      "lock",
    ],
  ];
  return (
    <div className="tool-grid">
      {tools.map(([name, on, note, icon]) => (
        <Card key={name} label={name} className={`tool ${on ? "on" : "off"}`}>
          <span className="tool-icon">
            <Icon name={icon} />
          </span>
          <h3>{name}</h3>
          <p>{note}</p>
          <small>{on ? "Enabled" : "Off"}</small>
        </Card>
      ))}
      <p className="hint">Change these in Settings · Capabilities.</p>
    </div>
  );
}

function PulseTiles({
  tasks,
  transcripts,
}: {
  tasks: Task[];
  transcripts: Record<string, Transcript>;
}) {
  const stats = useSceneStats();
  const pulse = useMemo(
    () => summarize(tasks, transcripts),
    [tasks, transcripts],
  );
  const fps = useHistory(stats?.fps, 30);
  const tiles: {
    key: string;
    label: string;
    value?: number;
    suffix?: string;
    note: string;
    series: number[];
    color: string;
  }[] = [
    {
      key: "tasks",
      label: "Tasks",
      value: pulse.total,
      note: pulse.running ? `${pulse.running} running` : "this conversation",
      series: pulse.latencies.map((_, i) => i + 1),
      color: "var(--energy)",
    },
    {
      key: "success",
      label: "Success",
      value: pulse.successRate,
      suffix: "%",
      note: `${pulse.succeeded}/${pulse.finished} finished`,
      series: pulse.latencies.map(() => pulse.successRate ?? 0),
      color: "var(--infernal)",
    },
    {
      key: "latency",
      label: "Avg route",
      value: pulse.avgLatency,
      suffix: " ms",
      note: pulse.tokens ? `${pulse.tokens} tokens` : "no routed calls yet",
      series: pulse.latencies,
      color: "var(--ember)",
    },
    {
      key: "fps",
      label: "Render",
      value: stats?.fps,
      suffix: " fps",
      note: stats ? `${stats.frameMs} ms frame` : "warming up",
      series: fps,
      color: "var(--titanium-text)",
    },
  ];
  return (
    <div className="pulse-row" aria-label="Session pulse">
      {tiles.map((tile) => (
        <Card
          key={tile.key}
          label={tile.label}
          className={`pulse pulse-${tile.key}`}
          tilt={4}
        >
          <small>{tile.label}</small>
          <strong>
            {tile.value === undefined ? (
              "—"
            ) : (
              <Counter value={tile.value} suffix={tile.suffix} />
            )}
          </strong>
          <span className="note">{tile.note}</span>
          <Sparkline
            values={tile.series}
            color={tile.color}
            height={28}
            label={`${tile.label} trend`}
          />
        </Card>
      ))}
    </div>
  );
}

function AgentCards({
  agents,
  selected,
  onSelect,
}: {
  agents: Record<Role, AgentStatus>;
  selected: Role | null;
  onSelect: (role: Role) => void;
}) {
  return (
    <div className="agent-cards">
      {ROLES.map((role) => {
        const agent = agents[role];
        return (
          <Card
            key={role}
            label={`${role} agent`}
            className={`agent-card ${agent.status} ${selected === role ? "selected" : ""}`}
            tilt={4}
          >
            <span
              className="agent-orb"
              style={{ "--role": roleColor[role] } as CSSProperties}
            >
              <Icon name={roleIcon[role]} />
            </span>
            <h3>{role}</h3>
            <p>{roleText[role]}</p>
            <div className="row">
              <span className={`chip ${agent.status}`}>
                {agent.status === "started" ? "running" : agent.status}
              </span>
              <button type="button" onClick={() => onSelect(role)}>
                Details
              </button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

const greetingNow = () => greeting(new Date().getHours());

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
  const [agentFilter, setAgentFilter] = useState("all");
  const root = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const indicator = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();
  const live = focus ? transcripts[focus.task_id] : undefined;
  const staged = view === "home" || view === "agents";
  useEffect(() => {
    if (!staged) publishStats(null);
  }, [staged]);
  const status = live?.status ?? focus?.status;
  const running = !!status && !terminal.has(status);
  const startedAt = live?.log?.[0]?.at;
  const hue = EXPRESSIONS[face].hue;
  const ready = props.connected && !!health?.ready;

  // Entrance choreography.
  useGSAP(
    () => {
      if (reduced) return;
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.from(".cc-top > *", {
        y: -18,
        opacity: 0,
        stagger: 0.04,
        duration: 0.6,
      })
        .from(
          ".cc-nav .nav-item",
          { x: -22, opacity: 0, stagger: 0.05, duration: 0.5 },
          0.1,
        )
        .from(
          ".cc-side > .card",
          { x: 28, opacity: 0, stagger: 0.07, duration: 0.6 },
          0.15,
        )
        .from(".cc-bottom", { y: 24, opacity: 0, duration: 0.6 }, 0.25);
    },
    { scope: root },
  );
  // Page transition on every view change.
  useGSAP(
    () => {
      if (reduced || !frame.current) return;
      gsap.fromTo(
        frame.current.children,
        { opacity: 0, y: 12 },
        {
          opacity: 1,
          y: 0,
          duration: 0.45,
          stagger: 0.06,
          ease: "power3.out",
          clearProps: "transform",
        },
      );
    },
    { dependencies: [view], scope: root },
  );
  // Sliding nav indicator.
  useGSAP(
    () => {
      const current = root.current?.querySelector<HTMLElement>(
        ".cc-nav .nav-item.current",
      );
      if (!current || !indicator.current) return;
      gsap.to(indicator.current, {
        y: current.offsetTop,
        height: current.offsetHeight,
        opacity: 1,
        duration: reduced ? 0 : 0.5,
        ease: "power3.out",
      });
    },
    { dependencies: [view, reduced], scope: root },
  );

  const tool = live?.log ? openTool(live.log) : undefined;
  const plan = live?.log
    ? [...live.log]
        .reverse()
        .find((entry) => entry.type === "audit.notice" && entry.data.model)
    : undefined;
  const route = plan
    ? `${String(plan.data.route_mode ?? "route")} · ${String(plan.data.model)}`
    : live?.metrics?.route_mode
      ? `${live.metrics.route_mode} · openrouter/free`
      : ready
        ? "Auto"
        : "Needs a qualified model";
  const activity =
    status === "awaiting_approval"
      ? "Paused. Approve or reject the pending change."
      : running && props.agent
        ? `Delegated to the ${props.agent} specialist.`
        : running && tool
          ? `Running ${tool}.`
          : running && focus
            ? focus.input.content.slice(0, 90)
            : face === "speaking"
              ? "Speaking the last answer aloud."
              : face === "error"
                ? (live?.error ??
                  focus?.error?.message ??
                  "The last request failed.")
                : face === "disconnected"
                  ? "Waiting for the local broker."
                  : `${greetingNow()}. Ask, plan, research or build.`;
  const stage = (
    <div
      className={`stage ${running ? "working" : ""}`}
      aria-label={`Immortility face: ${faceLabel[face]}`}
    >
      <div className="chamber-atmos" aria-hidden="true" />
      <AgentNetwork
        agents={agents}
        selected={selected}
        active={face === "delegating" ? props.agent : undefined}
        route={route}
        onSelect={(role) => setSelected(selected === role ? null : role)}
      />
      <Suspense fallback={<FlatFace face={face} />}>
        <HeadCanvas
          face={face}
          agent={props.agent}
          level={props.level}
          quality={prefs.quality}
          reduced={prefs.reduced}
          onStats={publishStats}
        />
      </Suspense>
      <div className="stage-status">
        <span className="eyebrow">
          <span className={`live-dot ${ready ? "on" : ""}`} />
          {ready ? "Core online" : "Core offline"}
        </span>
        <h1>{faceLabel[face]}</h1>
        <p>{activity}</p>
      </div>
      {props.micLive && (
        <div className="stage-caption">
          <span className="live-indicator">● Microphone live</span>
        </div>
      )}
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
      center = <div className="chat-view glass">{props.chat}</div>;
      break;
    case "timeline":
      center = <div className="pane glass">{timeline(false)}</div>;
      break;
    case "tasks":
      center = (
        <div className="tasks-view glass">
          <div className="row">
            <h2 className="pane-title">
              <Icon name="tasks" /> Tasks
            </h2>
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
              className="primary"
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
      center = (
        <div className="pane glass">
          <h2 className="pane-title">
            <Icon name="memory" /> Memory
          </h2>
          {props.memory}
        </div>
      );
      break;
    case "tools":
      center = <Tools health={health} />;
      break;
    case "settings":
      center = <div className="pane glass">{props.settings}</div>;
      break;
    case "agents":
      center = (
        <>
          {stage}
          <AgentCards
            agents={agents}
            selected={selected}
            onSelect={(role) => setSelected(selected === role ? null : role)}
          />
        </>
      );
      break;
    default:
      center = (
        <>
          {stage}
          <div className="home-lower">
            {timeline(true)}
            <PulseTiles tasks={tasks} transcripts={transcripts} />
          </div>
        </>
      );
  }
  return (
    <div
      ref={root}
      className={`command face-${face} q-${prefs.quality}`}
      style={{ "--state": hue } as CSSProperties}
    >
      <Backdrop />
      <header
        className="cc-top"
        onPointerDown={(event) => {
          if (
            event.button === 0 &&
            (event.target === event.currentTarget ||
              (event.target as HTMLElement).classList.contains("drag-zone"))
          )
            void windowAction("drag_free");
        }}
        onDoubleClick={(event) => {
          if (
            event.target === event.currentTarget ||
            (event.target as HTMLElement).classList.contains("drag-zone")
          )
            void windowAction("maximize");
        }}
      >
        <div className="brand">
          <span className="brand-mark">
            <img src={FACE_IMAGE} alt="" />
          </span>
          <div>
            <strong>IMMORTILITY</strong>
            <small>Your eternal AI companion</small>
          </div>
        </div>
        <span className={`state-pill ${face}`}>
          <i /> {faceLabel[face]}
        </span>
        <span className="model">
          <span className={`dot ${ready ? "online" : ""}`} />
          {presenceLabel({
            connected: props.connected,
            ready: !!health?.ready,
            starting: props.starting === true,
            localOnly: health?.runtime_mode === "local-background",
            hermes: health?.hermes.status,
          })}
        </span>
        <span className="badge">Free</span>
        <span className="drag-zone" aria-hidden="true" />
        <div className="window-buttons">
          <MagneticButton
            className="glow-btn"
            onClick={props.onQuickChat}
            title="Quick chat"
          >
            <Icon name="chat" /> Quick chat
          </MagneticButton>
          <MagneticButton
            className="glow-btn alt"
            onClick={props.onCompanion}
            title="Return to the floating face"
          >
            <Icon name="face" /> Companion
          </MagneticButton>
          <button
            type="button"
            className="icon-btn"
            onClick={() => setView("settings")}
            aria-label="Settings"
          >
            <Icon name="settings" />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={() => void windowAction("minimize")}
            aria-label="Minimize"
          >
            <Icon name="minimize" />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={() => void windowAction("maximize")}
            aria-label="Maximize or restore"
          >
            <Icon name="maximize" />
          </button>
          <button
            type="button"
            className="icon-btn close"
            onClick={props.onCompanion}
            aria-label="Close command center"
          >
            <Icon name="close" />
          </button>
        </div>
      </header>
      <nav className="cc-nav" aria-label="Command center">
        <div className="nav-list">
          <span ref={indicator} className="nav-indicator" aria-hidden="true" />
          {views.map(([id, label, icon]) => (
            <button
              key={id}
              type="button"
              aria-current={view === id ? "page" : undefined}
              className={`nav-item ${view === id ? "current" : ""}`}
              onClick={() => setView(id)}
              title={label}
            >
              <Icon name={icon} />
              <span className="nav-label">{label}</span>
            </button>
          ))}
        </div>
        <div className="nav-core" aria-hidden="true">
          <span className="core-ring" />
          <span className="nav-label">Core {ready ? "stable" : "offline"}</span>
        </div>
        <p className="hint nav-label">
          Workflows and Projects are not implemented yet.
        </p>
      </nav>
      <main className={`cc-main view-${view}`}>
        <div ref={frame} className="view-frame">
          {center}
        </div>
      </main>
      <aside className="cc-side" aria-label="Status">
        <Card
          className={`active-task ${running ? "running" : ""}`}
          label="Active task"
        >
          <h2>
            <Icon name="bolt" /> {running ? "Active task" : "Latest task"}
          </h2>
          {focus ? (
            <>
              <p className="task-title">{focus.input.content.slice(0, 120)}</p>
              <p className={`status ${status}`}>
                {status?.replaceAll("_", " ")} · {faceLabel[face]}
                {running && startedAt && (
                  <>
                    {" · "}
                    <Elapsed from={startedAt} />
                  </>
                )}
              </p>
              {running && <div className="progress" aria-hidden="true" />}
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
        </Card>
        <Card label="Agents">
          <h2>
            <Icon name="agents" /> Agents
          </h2>
          <ul className="agents">
            {ROLES.map((role) => (
              <li key={role}>
                <button
                  type="button"
                  className={agents[role].status}
                  style={{ "--role": roleColor[role] } as CSSProperties}
                  onClick={() => {
                    setSelected(role);
                    if (!staged) setView("home");
                  }}
                >
                  <span>
                    <i className="role-dot" /> {role}
                  </span>
                  <small>
                    {agents[role].status === "started"
                      ? "running"
                      : agents[role].status}
                    {agents[role].startedAt && (
                      <>
                        {" · "}
                        <Elapsed
                          from={agents[role].startedAt}
                          to={agents[role].endedAt}
                        />
                      </>
                    )}
                  </small>
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="voice-card" label="Voice">
          <h2>
            <Icon name="mic" /> Voice
          </h2>
          {props.voice}
        </Card>
        <Metrics transcript={live} connected={props.connected} />
        <Permissions
          health={health}
          consent={props.consent}
          micLive={props.micLive}
        />
      </aside>
      <footer className="cc-bottom">
        {props.error}
        {props.composer}
      </footer>
    </div>
  );
}
