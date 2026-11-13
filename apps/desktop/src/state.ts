export const terminal = new Set([
  "succeeded",
  "failed",
  "cancelled",
  "blocked",
  "rate_limited",
  "disconnected",
]);
import type { Status, AvatarState } from "./contracts.generated";
export type { Status } from "./contracts.generated";
export type OrbState = AvatarState;
export interface Task {
  task_id: string;
  session_id: string;
  request_id: string;
  status: Status;
  input: { content: string };
  result?: { text: string; provider: string; model: string };
  error?: { code: string; message: string };
}
export interface TaskEvent {
  schema_version: "1.0";
  task_id: string;
  sequence: number;
  timestamp?: string;
  type: string;
  data: Record<string, unknown>;
}
export interface LogEntry {
  sequence: number;
  type: string;
  at: string;
  data: Record<string, string | number | boolean>;
}
const visibleKeys = [
  "status",
  "role",
  "name",
  "path",
  "url",
  "title",
  "route_mode",
  "calls",
  "latency_ms",
  "first_token_ms",
  "prompt_tokens",
  "completion_tokens",
  "decision",
  "code",
  "message",
  "provider",
  "model",
  "delegation",
  "tools_enabled",
] as const;
const secretLike = /(sk-[A-Za-z0-9_-]{8,}|bearer\s+\S+|api[_-]?key\S*)/gi;
export function redact(
  data: Record<string, unknown>,
): Record<string, string | number | boolean> {
  const kept: Record<string, string | number | boolean> = {};
  for (const key of visibleKeys) {
    const value = data[key];
    if (typeof value === "number" || typeof value === "boolean")
      kept[key] = value;
    else if (typeof value === "string")
      kept[key] = value.replace(secretLike, "[redacted]").slice(0, 240);
  }
  return kept;
}
export interface Transcript {
  text: string;
  sequence: number;
  status: Status;
  events: string[];
  log?: LogEntry[];
  error?: string;
  preview?: string;
  metrics?: {
    route_mode: string;
    calls: number;
    latency_ms: number;
    first_token_ms?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
  };
}
export function reduceEvent(state: Transcript, event: TaskEvent): Transcript {
  if (event.sequence <= state.sequence) return state;
  const next = { ...state, sequence: event.sequence };
  if (event.type === "message.delta" && typeof event.data.text === "string")
    next.text += event.data.text;
  if (event.type === "task.state") next.status = event.data.status as Status;
  if (event.type === "task.error")
    next.error = String(event.data.message ?? "Request failed.");
  if (
    event.type === "approval.requested" &&
    typeof event.data.preview === "string"
  )
    next.preview = event.data.preview;
  if (
    event.type === "audit.notice" &&
    typeof event.data.latency_ms === "number" &&
    typeof event.data.calls === "number" &&
    typeof event.data.route_mode === "string"
  )
    next.metrics = {
      route_mode: event.data.route_mode,
      calls: event.data.calls,
      latency_ms: event.data.latency_ms,
      ...(typeof event.data.first_token_ms === "number"
        ? { first_token_ms: event.data.first_token_ms }
        : {}),
      ...(typeof event.data.prompt_tokens === "number"
        ? { prompt_tokens: event.data.prompt_tokens }
        : {}),
      ...(typeof event.data.completion_tokens === "number"
        ? { completion_tokens: event.data.completion_tokens }
        : {}),
    };
  if (event.type !== "message.delta") {
    const role =
      event.type.startsWith("agent.") && typeof event.data.role === "string"
        ? `${event.data.role} ${String(event.data.status ?? "")}`
        : event.type === "task.state"
          ? String(event.data.status)
          : event.type;
    next.events = [...state.events.slice(-19), role];
    next.log = [
      ...(state.log ?? []).slice(-119),
      {
        sequence: event.sequence,
        type: event.type,
        at: event.timestamp ?? new Date().toISOString(),
        data: redact(event.data),
      },
    ];
  }
  return next;
}
export function orbState(
  status: Status | undefined,
  connected: boolean,
): OrbState {
  if (status === "failed" || status === "blocked" || status === "rate_limited")
    return "error";
  if (!connected || status === "disconnected") return "disconnected";
  if (status === "awaiting_approval") return "awaiting-approval";
  if (
    status === "running" ||
    status === "queued" ||
    status === "created" ||
    status === "verifying"
  )
    return "thinking";
  return "idle";
}
