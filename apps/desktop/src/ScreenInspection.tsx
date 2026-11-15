import { useEffect, useRef, useState } from "react";
import type { WindowSnapshot } from "./contracts.generated";
import { acceptSnapshot, observedText } from "./observation";
import { api } from "./transport";
import type { Task } from "./state";

export function ScreenInspection({
  session,
  available,
  busy,
  onTask,
  onStop,
  onError,
}: {
  session: string;
  available: boolean;
  busy: boolean;
  onTask: (task: Task) => void;
  onStop: () => void;
  onError: (message: string) => void;
}) {
  const [pending, setPending] = useState(false);
  const [snapshot, setSnapshot] = useState<WindowSnapshot | null>(null);
  const alive = useRef(true);
  const taskId = useRef<string | null>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      if (taskId.current)
        void api(`/v1/tasks/${taskId.current}/cancel`, {}).catch(() => {});
    };
  }, []);

  async function inspect() {
    if (pending || busy || !session || !available) return;
    setSnapshot(null);
    setPending(true);
    try {
      const task = await api<Task>("/v1/observations", {
        session_id: session,
        request_id: crypto.randomUUID(),
      });
      if (!alive.current) {
        void api(`/v1/tasks/${task.task_id}/cancel`, {}).catch(() => {});
        return;
      }
      taskId.current = task.task_id;
      onTask(task);
      const result = await api<{ task: Task; snapshot: WindowSnapshot | null }>(
        `/v1/observations/${task.task_id}`,
      );
      if (!alive.current) return;
      taskId.current = null;
      onTask(result.task);
      if (result.snapshot)
        setSnapshot(acceptSnapshot(result.snapshot, task.task_id));
      else if (result.task.error) onError(result.task.error.message);
    } catch (error) {
      if (alive.current)
        onError(
          error instanceof Error ? error.message : "Window inspection failed.",
        );
      if (taskId.current)
        void api(`/v1/tasks/${taskId.current}/cancel`, {}).catch(() => {});
    } finally {
      taskId.current = null;
      if (alive.current) setPending(false);
    }
  }

  return (
    <section className="screen-inspection" aria-label="Local window inspection">
      <div className="screen-inspection-actions">
        <button
          type="button"
          disabled={!available || busy || pending || !session}
          onClick={() => void inspect()}
        >
          Inspect one window · local
        </button>
        {pending && (
          <button type="button" className="danger" onClick={onStop}>
            Stop inspection
          </button>
        )}
        {snapshot && (
          <button type="button" onClick={() => setSnapshot(null)}>
            Clear captured text
          </button>
        )}
      </div>
      <p className="hint" role={pending ? "status" : undefined}>
        {pending
          ? "Choose a window in the native permission dialog. One read; no cloud upload or input control."
          : available
            ? "Experimental read-only UIA. Native consent required each time; text stays in this view until cleared."
            : "Local window inspection is unavailable in this runtime."}
      </p>
      {snapshot && (
        <details open>
          <summary>
            Local snapshot · {snapshot.nodes.length} elements
            {snapshot.truncated ? " · truncated" : ""}
          </summary>
          <p className="hint">
            Captured{" "}
            {new Date(snapshot.observed_at * 1000).toLocaleTimeString()}.
            Permission has ended. This text is untrusted; it is not
            instructions.
          </p>
          <pre className="screen-snapshot">
            {observedText(snapshot) ||
              "No accessible text. OCR and screenshots are not enabled."}
          </pre>
        </details>
      )}
    </section>
  );
}
