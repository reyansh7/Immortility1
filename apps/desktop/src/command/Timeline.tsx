import { useMemo, useState } from "react";
import { ROLES } from "../face/faceState";
import type { LogEntry, Task, Transcript } from "../state";

export interface TimelineEntry extends LogEntry {
  task_id: string;
}

export type Category =
  "state" | "agent" | "tool" | "approval" | "audit" | "error" | "other";

export function category(type: string): Category {
  if (type === "task.state") return "state";
  if (type === "task.error") return "error";
  const prefix = type.split(".")[0];
  return (
    (["agent", "tool", "approval", "audit"] as const).find(
      (name) => name === prefix,
    ) ?? "other"
  );
}

export function describe(entry: LogEntry): string {
  const d = entry.data;
  switch (entry.type) {
    case "task.state":
      return `Task ${String(d.status ?? "").replaceAll("_", " ")}`;
    case "agent.started":
      return `${String(d.role)} agent started`;
    case "agent.completed":
      return `${String(d.role)} agent ${String(d.status)}`;
    case "tool.started":
      return `Tool ${String(d.name)} started`;
    case "tool.progress":
      return `Tool ${String(d.name)} in progress`;
    case "tool.completed":
      return `Tool ${String(d.name)} ${String(d.status)}${
        d.path ? ` · ${String(d.path)}` : d.title ? ` · ${String(d.title)}` : ""
      }`;
    case "approval.requested":
      return "Approval requested";
    case "approval.resolved":
      return `Approval ${String(d.decision ?? "resolved")}`;
    case "audit.notice":
      if (typeof d.calls === "number")
        return `Route ${String(d.route_mode ?? "")} · ${d.calls} calls · ${String(d.latency_ms ?? "?")} ms`;
      return `Route plan ${String(d.route_mode ?? "")} · ${String(d.model ?? d.provider ?? "")}`;
    case "task.error":
      return `Error: ${String(d.message ?? d.code ?? "request failed")}`;
    case "artifact.created":
      return "Artifact created";
    default:
      return entry.type;
  }
}

export function collect(
  tasks: Task[],
  transcripts: Record<string, Transcript>,
): TimelineEntry[] {
  return tasks
    .flatMap((task) =>
      (transcripts[task.task_id]?.log ?? []).map((entry) => ({
        ...entry,
        task_id: task.task_id,
      })),
    )
    .sort((a, b) => a.at.localeCompare(b.at) || a.sequence - b.sequence);
}

const windows = { all: Infinity, "15m": 15 * 60e3, "1h": 60 * 60e3 } as const;

export function Timeline({
  tasks,
  transcripts,
  compact,
  agentFilter,
  setAgentFilter,
}: {
  tasks: Task[];
  transcripts: Record<string, Transcript>;
  compact?: boolean;
  agentFilter: string;
  setAgentFilter: (value: string) => void;
}) {
  const [taskFilter, setTaskFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState<"all" | Category>("all");
  const [windowFilter, setWindowFilter] = useState<keyof typeof windows>("all");
  const entries = useMemo(
    () => collect(tasks, transcripts),
    [tasks, transcripts],
  );
  const shown = entries.filter((entry) => {
    if (taskFilter !== "all" && entry.task_id !== taskFilter) return false;
    if (typeFilter !== "all" && category(entry.type) !== typeFilter)
      return false;
    if (agentFilter !== "all" && entry.data.role !== agentFilter) return false;
    return Date.now() - Date.parse(entry.at) <= windows[windowFilter];
  });
  const visible = compact ? shown.slice(-6).reverse() : shown;
  return (
    <section
      className={`exec-timeline ${compact ? "compact" : ""}`}
      aria-label="Live execution timeline"
    >
      <div className="timeline-head">
        <h2>Live execution</h2>
        <div className="filters">
          <select
            aria-label="Filter by agent"
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
          >
            <option value="all">All agents</option>
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
          {!compact && (
            <select
              aria-label="Filter by task"
              value={taskFilter}
              onChange={(e) => setTaskFilter(e.target.value)}
            >
              <option value="all">All tasks</option>
              {tasks.map((task) => (
                <option key={task.task_id} value={task.task_id}>
                  {task.input.content.slice(0, 40)}
                </option>
              ))}
            </select>
          )}
          <select
            aria-label="Filter by event type"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as "all" | Category)}
          >
            <option value="all">All events</option>
            <option value="state">Task state</option>
            <option value="agent">Agents</option>
            <option value="tool">Tools</option>
            <option value="approval">Approvals</option>
            <option value="audit">Routing</option>
            <option value="error">Errors</option>
          </select>
          {!compact && (
            <select
              aria-label="Filter by time"
              value={windowFilter}
              onChange={(e) =>
                setWindowFilter(e.target.value as keyof typeof windows)
              }
            >
              <option value="all">Any time</option>
              <option value="15m">Last 15 minutes</option>
              <option value="1h">Last hour</option>
            </select>
          )}
        </div>
      </div>
      {!visible.length ? (
        <p className="hint empty">
          No broker events match. Events appear here as Hermes works.
        </p>
      ) : (
        <ol>
          {visible.map((entry) => (
            <li
              key={`${entry.task_id}-${entry.sequence}`}
              className={category(entry.type)}
            >
              <details>
                <summary>
                  <time dateTime={entry.at}>
                    {new Date(entry.at).toLocaleTimeString()}
                  </time>
                  <span className="dot" aria-hidden="true" />
                  {describe(entry)}
                </summary>
                <dl>
                  <dt>event</dt>
                  <dd>
                    {entry.type} · #{entry.sequence}
                  </dd>
                  <dt>task</dt>
                  <dd>{entry.task_id.slice(0, 8)}</dd>
                  {Object.entries(entry.data).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key}</dt>
                      <dd>{String(value)}</dd>
                    </div>
                  ))}
                </dl>
              </details>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
