import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { api, windowAction } from "./transport";
import type { Task } from "./state";

export function BackgroundConnection({
  attached,
  session,
  sdk,
  onChanged,
  onTask,
  onError,
}: {
  attached: boolean;
  session: string;
  sdk: boolean;
  onChanged: (attached: boolean) => Promise<void>;
  onTask: (task: Task) => void;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function change(action: "attach_background" | "detach_background") {
    setBusy(true);
    try {
      await invoke(action);
      await onChanged(action === "attach_background");
    } catch (error) {
      onError(
        typeof error === "string" ? error : "Background connection failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function verify() {
    setBusy(true);
    try {
      const count = sdk ? 8 : 2;
      const steps = Array.from({ length: count }, (_, i) => ({
        id: `step${i}`,
        capability: sdk ? "arithmetic.add.v1" : "clock.now.v1",
        arguments: sdk ? { a: i, b: 1 } : {},
        depends_on: i ? [`step${i - 1}`] : [],
      }));
      onTask(
        await api<Task>("/v1/workflows", {
          session_id: session,
          request_id: crypto.randomUUID(),
          label: "Local background verification",
          steps,
          deadline_seconds: 120,
          max_retries: 0,
          resume_on_restart: false,
          local_read_consent: true,
          no_cloud: true,
        }),
      );
    } catch (error) {
      onError(
        error instanceof Error ? error.message : "Local workflow failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="screen-inspection" aria-label="Background connection">
      <div className="screen-inspection-actions">
        <button
          type="button"
          disabled={busy}
          onClick={() => void change("attach_background")}
        >
          Attach local background
        </button>
        {attached && (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => void change("detach_background")}
            >
              Detach dashboard
            </button>
            <button
              type="button"
              disabled={busy || !session}
              onClick={() => void verify()}
            >
              Run background verification
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void windowAction("quit")}
            >
              Close dashboard · keep tasks running
            </button>
          </>
        )}
      </div>
      <p className="hint">
        {attached
          ? `Attached to a local-only runtime. Verification runs ${sdk ? "8 SDK additions" : "2 clock reads"}; no model calls. Closing this dashboard leaves the runtime running. Stop cancels tasks.`
          : "Optional: attach a separately started local-only runtime. No startup service is installed. The desktop broker must be closed before that runtime can own the same data."}
      </p>
    </section>
  );
}
