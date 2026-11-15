/** Task presentation and read-only stream recovery. Never resubmits inference. */
import { terminal, type Task, type TaskEvent, type Transcript } from "./state";

export function taskStatus(task: Task, live?: Transcript) {
  return terminal.has(task.status)
    ? task.status
    : (live?.status ?? task.status);
}

export function reconcileTask(live: Transcript, task: Task): Transcript {
  if (live.task_id && live.task_id !== task.task_id) return live;
  return {
    ...live,
    task_id: task.task_id,
    status: task.status,
    text: task.result ? task.result.text : live.text,
    error: task.error?.message ?? live.error,
  };
}

export function taskOutcome(task: Task, live?: Transcript) {
  const status = taskStatus(task, live);
  const text = task.result ? task.result.text : (live?.text ?? "");
  const error = task.error?.message ?? live?.error;
  const fallback =
    error ??
    (
      {
        failed:
          "The request failed before a usable answer was completed. You can reconnect for details or retry it.",
        blocked:
          "This request needs permission or an available capability. Check its execution details.",
        rate_limited:
          "The free provider is currently rate-limited. No paid fallback was used.",
        disconnected:
          "The agent connection ended before this request completed. Reconnect to check its outcome.",
        cancelled: text.trim()
          ? "Request cancelled. The partial response is retained."
          : "Request cancelled before an answer was produced.",
        succeeded:
          "The task completed without a displayable answer. This is not a verified chat response; retry or inspect its execution details.",
      } as Record<string, string>
    )[status];
  return {
    status,
    text,
    notice: status === "succeeded" && text.trim() ? undefined : fallback,
  };
}

interface FollowTransport {
  stream: (
    after: number,
    onEvent: (event: TaskEvent) => void,
    signal: AbortSignal,
  ) => Promise<void>;
  task: () => Promise<Task>;
}

function pause(signal: AbortSignal, ms: number): Promise<void> {
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", finish);
      resolve();
    };
    const timer = setTimeout(finish, ms);
    if (signal.aborted) finish();
    else signal.addEventListener("abort", finish, { once: true });
  });
}

export async function followTask(
  original: Task,
  transport: FollowTransport,
  onEvent: (event: TaskEvent) => void,
  onTask: (task: Task) => void,
  signal: AbortSignal,
): Promise<void> {
  let cursor = 0;
  for (let attempt = 0; attempt < 3 && !signal.aborted; attempt++) {
    try {
      await transport.stream(
        cursor,
        (event) => {
          if (
            signal.aborted ||
            event.task_id !== original.task_id ||
            !Number.isSafeInteger(event.sequence) ||
            event.sequence <= cursor
          )
            return;
          cursor = event.sequence;
          onEvent(event);
        },
        signal,
      );
    } catch {
      /* Final metadata remains authoritative even when SSE is lost. */
    }
    if (signal.aborted) return;
    try {
      const task = await transport.task();
      if (signal.aborted) return;
      if (
        task.task_id !== original.task_id ||
        task.session_id !== original.session_id
      )
        throw new Error("Foreign task metadata rejected.");
      onTask(task);
      if (terminal.has(task.status)) return;
    } catch {
      /* Retry only GET/stream; no new model turn is submitted. */
    }
    if (attempt < 2) await pause(signal, attempt === 0 ? 250 : 750);
  }
  if (!signal.aborted)
    throw new Error(
      "The response connection was interrupted. Reconnect to retrieve the stored outcome; the request was not resubmitted.",
    );
}
