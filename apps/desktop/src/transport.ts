import { Channel, invoke } from "@tauri-apps/api/core";
import type { TaskEvent } from "./state";

export async function connect(): Promise<void> {
  try {
    await invoke("connection");
  } catch (error) {
    throw new Error(
      typeof error === "string" ? error : "Unable to start local service.",
      { cause: error },
    );
  }
}

export function operation(
  path: string,
  post: boolean,
): { operation: string; id?: string } {
  if (path === "/health/ready" && !post) return { operation: "health" };
  if (path === "/v1/models" && !post) return { operation: "model_catalog" };
  if (path === "/v1/settings/model-mode" && post)
    return { operation: "set_model_mode" };
  if (path === "/v1/sessions")
    return { operation: post ? "create_session" : "sessions" };
  if (path === "/v1/tasks" && post) return { operation: "create_task" };
  if (path === "/v1/observations" && post)
    return { operation: "start_observation" };
  const observation = /^\/v1\/observations\/([a-f0-9-]{36})$/.exec(path);
  if (observation && !post)
    return { operation: "observation_result", id: observation[1] };
  if (path === "/v1/workflows" && post) return { operation: "create_workflow" };
  const workflow = /^\/v1\/workflows\/([a-f0-9-]{36})$/.exec(path);
  if (workflow && !post) return { operation: "get_workflow", id: workflow[1] };
  if (path === "/v1/stop" && post) return { operation: "stop" };
  if (path === "/v1/runtime/shutdown" && post)
    return { operation: "shutdown_background" };
  const voiceRoutes: Record<string, string> = {
    "/v1/voice/status": "voice_status",
    "/v1/voice/devices": "voice_devices",
    "/v1/voice/prepare": "voice_prepare",
    "/v1/voice/record": "voice_record",
    "/v1/voice/finish": "voice_finish",
    "/v1/voice/cancel": "voice_cancel",
    "/v1/voice/options": "voice_options",
    "/v1/voice/preview": "voice_preview",
    "/v1/voice/profile/delete": "voice_delete_profile",
    "/v1/settings/migrate-credentials": "migrate_credentials",
    "/v1/settings/delegation": "set_delegation",
    "/v1/settings/local-tools": "set_local_tools",
    "/v1/settings/web-research": "set_web_research",
    "/v1/settings/mcp": "set_mcp",
    "/v1/settings/standard-mcp": "set_standard_mcp",
    "/v1/settings/artifacts": "set_artifacts",
    "/v1/mcp/call": "call_mcp",
    "/v1/memory/search": "memory_search",
    "/v1/memory/delete": "memory_delete",
    "/v1/tools/call": "call_tool",
  };
  if (
    voiceRoutes[path] &&
    post !== (path.endsWith("/status") || path.endsWith("/devices"))
  )
    return { operation: voiceRoutes[path] };
  const speaking = /^\/v1\/voice\/speak\/([a-f0-9-]{36})$/.exec(path);
  if (speaking && post) return { operation: "voice_speak", id: speaking[1] };
  const session = /^\/v1\/sessions\/([a-f0-9-]{36})\/tasks$/.exec(path);
  const trace = /^\/v1\/tasks\/([a-f0-9-]{36})\/trace$/.exec(path);
  const usage = /^\/v1\/tasks\/([a-f0-9-]{36})\/usage$/.exec(path);
  if (usage && !post) return { operation: "task_usage", id: usage[1] };
  if (path === "/v1/tools" && !post) return { operation: "list_tools" };
  if (path === "/v1/capabilities" && !post)
    return { operation: "list_capabilities" };
  if (path === "/v1/mcp/tools" && !post) return { operation: "list_mcp" };
  if (path === "/v1/settings/workspace" && post)
    return { operation: "set_workspace" };
  const approval = /^\/v1\/tasks\/([a-f0-9-]{36})\/approval$/.exec(path);
  if (approval && post)
    return { operation: "resolve_approval", id: approval[1] };
  const rollback = /^\/v1\/tasks\/([a-f0-9-]{36})\/rollback$/.exec(path);
  if (rollback && post) return { operation: "rollback", id: rollback[1] };
  if (trace && !post) return { operation: "task_trace", id: trace[1] };
  if (session && !post) return { operation: "session_tasks", id: session[1] };
  const task = /^\/v1\/tasks\/([a-f0-9-]{36})(\/cancel)?$/.exec(path);
  if (task && ((post && task[2]) || (!post && !task[2])))
    return { operation: post ? "cancel" : "task", id: task[1] };
  throw new Error("Unsupported local request.");
}

export async function api<T>(path: string, body?: unknown): Promise<T> {
  try {
    const route = operation(path, body !== undefined);
    return await invoke<T>("broker_request", {
      ...route,
      payload: body ?? null,
      id: route.id ?? null,
    });
  } catch (error) {
    throw new Error(
      typeof error === "string" ? error : "Local broker request failed.",
      { cause: error },
    );
  }
}

export async function stream(
  taskId: string,
  after: number,
  onEvent: (event: TaskEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const channel = new Channel<TaskEvent>();
  channel.onmessage = (event) => {
    if (!signal.aborted && event.task_id === taskId) onEvent(event);
  };
  try {
    await invoke("stream_task", { taskId, after, channel });
  } catch (error) {
    if (!signal.aborted)
      throw new Error(
        typeof error === "string"
          ? error
          : "Stream disconnected; reconnect to replay.",
        { cause: error },
      );
  }
}

export async function windowAction(
  action:
    | "expand"
    | "collapse"
    | "drag"
    | "snap"
    | "pin"
    | "unpin"
    | "hide"
    | "quit"
    | "nudge_up"
    | "nudge_down"
    | "command"
    | "overlay"
    | "minimize"
    | "maximize"
    | "drag_free"
    | "context_menu",
): Promise<void> {
  await invoke("window_action", { action });
}
