import type { LogEntry, Status } from "../state";

export type FaceState =
  | "idle"
  | "listening"
  | "thinking"
  | "planning"
  | "delegating"
  | "executing"
  | "awaiting"
  | "responding"
  | "speaking"
  | "error"
  | "disconnected";

export const ROLES = ["research", "coding", "review"] as const;
export type Role = (typeof ROLES)[number];

export interface AgentStatus {
  role: Role;
  status: "off" | "available" | "started" | "succeeded" | "failed";
  startedAt?: string;
  endedAt?: string;
}

export interface FaceInputs {
  connected: boolean;
  status?: Status;
  log: LogEntry[];
  text: string;
  voiceState: string;
  ttsState: string;
}

const running = new Set<Status>(["created", "queued", "running", "verifying"]);

export function playbackEnergy(level: number, speaking: boolean): number {
  return speaking && Number.isFinite(level)
    ? Math.max(0, Math.min(1, level * 4))
    : 0;
}

export function agentStatuses(
  log: LogEntry[],
  delegationEnabled: boolean,
): Record<Role, AgentStatus> {
  const agents = Object.fromEntries(
    ROLES.map((role) => [
      role,
      { role, status: delegationEnabled ? "available" : "off" },
    ]),
  ) as Record<Role, AgentStatus>;
  for (const entry of log) {
    if (!entry.type.startsWith("agent.")) continue;
    const role = entry.data.role;
    if (
      typeof role !== "string" ||
      !(ROLES as readonly string[]).includes(role)
    )
      continue;
    const agent = agents[role as Role];
    if (entry.type === "agent.started") {
      agent.status = "started";
      agent.startedAt = entry.at;
      agent.endedAt = undefined;
    } else {
      agent.status = entry.data.status === "succeeded" ? "succeeded" : "failed";
      agent.endedAt = entry.at;
    }
  }
  return agents;
}

export function openTool(log: LogEntry[]): string | undefined {
  const open = new Map<string, number>();
  for (const entry of log) {
    const name = entry.data.name;
    if (typeof name !== "string") continue;
    if (entry.type === "tool.started") open.set(name, entry.sequence);
    if (entry.type === "tool.completed") open.delete(name);
  }
  return [...open.keys()].at(-1);
}

export function deriveFace(input: FaceInputs): {
  state: FaceState;
  agent?: Role;
} {
  if (input.ttsState === "speaking") return { state: "speaking" };
  if (input.voiceState === "LISTENING") return { state: "listening" };
  if (!input.connected || input.status === "disconnected")
    return { state: "disconnected" };
  const status = input.status;
  if (status === "failed" || status === "blocked" || status === "rate_limited")
    return { state: "error" };
  if (status === "awaiting_approval") return { state: "awaiting" };
  if (input.voiceState === "TRANSCRIBING" || input.voiceState === "THINKING")
    return { state: "thinking" };
  if (!status || !running.has(status)) return { state: "idle" };
  const agents = agentStatuses(input.log, true);
  const active = ROLES.find((role) => agents[role].status === "started");
  if (active) return { state: "delegating", agent: active };
  if (openTool(input.log)) return { state: "executing" };
  if (input.text.length > 0) return { state: "responding" };
  const plan = [...input.log]
    .reverse()
    .find((entry) => typeof entry.data.route_mode === "string");
  if (plan && plan.data.route_mode !== "fast") return { state: "planning" };
  return { state: "thinking" };
}

export function presenceLabel(input: {
  connected: boolean;
  ready: boolean;
  starting: boolean;
  localOnly: boolean;
  reconnecting?: boolean;
  hermes?: string;
}): string {
  if (!input.connected)
    return input.starting || input.reconnecting ? "Starting" : "Offline";
  if (input.reconnecting) return "Reconnecting";
  if (input.localOnly) return "Local";
  if (input.hermes === "checking") return "Starting";
  if (input.hermes && input.hermes !== "available")
    return "Hermes is not ready";
  return input.ready ? "Ready" : "Needs a qualified model";
}

export const faceLabel: Record<FaceState, string> = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Thinking",
  planning: "Planning",
  delegating: "Delegating",
  executing: "Running a tool",
  awaiting: "Waiting for your approval",
  responding: "Responding",
  speaking: "Speaking",
  error: "Error",
  disconnected: "Disconnected",
};

export type OverlayPolicy = "never" | "screen-control";
const screenTools = new Set(["computer_use", "screen_control"]);

export function wantsOverlay(log: LogEntry[], policy: OverlayPolicy): boolean {
  if (policy === "never") return false;
  const tool = openTool(log);
  return tool !== undefined && screenTools.has(tool);
}
