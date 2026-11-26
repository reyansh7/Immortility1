import { useEffect, useRef, useState } from "react";
import { api } from "../transport";
import type { Task } from "../state";
import {
  explainAvailable,
  explainRequest,
  pickExplainText,
  type ScreenRead,
} from "./explain";

type Phase =
  | { kind: "idle" }
  | { kind: "countdown"; left: number }
  | { kind: "reading" }
  | { kind: "preview"; text: string; from: string }
  | { kind: "sending" }
  | { kind: "message"; text: string };

const COUNTDOWN = 3;

export function ExplainThis({
  connected,
  mode,
  session,
  busy,
  onTask,
}: {
  connected: boolean;
  mode?: string;
  session: string;
  busy: boolean;
  onTask: (task: Task) => void;
}) {
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const timer = useRef<number | null>(null);
  const available = explainAvailable(connected, mode);

  const clear = () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = null;
  };
  useEffect(() => clear, []);

  useEffect(() => {
    if (phase.kind !== "countdown") return;
    if (phase.left > 0) {
      timer.current = window.setTimeout(
        () => setPhase({ kind: "countdown", left: phase.left - 1 }),
        1000,
      );
      return clear;
    }
    setPhase({ kind: "reading" });
    void (async () => {
      try {
        const read = await api<ScreenRead>("/v1/screen/target", {
          unit: "line",
          selection: true,
          ocr_fallback: true,
        });
        const picked = pickExplainText(read);
        setPhase(
          picked.ok
            ? { kind: "preview", text: picked.text, from: picked.from }
            : { kind: "message", text: picked.message },
        );
      } catch (issue) {
        setPhase({
          kind: "message",
          text:
            issue instanceof Error
              ? issue.message
              : "Screen reading failed; nothing was kept.",
        });
      }
    })();
  }, [phase]);

  const cancel = () => {
    clear();
    setPhase({ kind: "idle" });
  };

  async function explain(text: string) {
    setPhase({ kind: "sending" });
    try {
      const task = await api<Task>("/v1/tasks", explainRequest(session, text));
      onTask(task);
      setPhase({ kind: "idle" });
    } catch (issue) {
      setPhase({
        kind: "message",
        text:
          issue instanceof Error ? issue.message : "Could not ask the model.",
      });
    }
  }

  return (
    <div
      className={`explain explain-${phase.kind}`}
      onKeyDown={(event) => {
        if (event.key === "Escape" && phase.kind !== "idle") {
          event.stopPropagation();
          cancel();
        }
      }}
    >
      {phase.kind === "idle" && (
        <button
          type="button"
          className="explain-start"
          disabled={!available.ok || busy || !session}
          title={
            available.ok
              ? "Point at any text on screen; Immortility reads it once and explains it on this PC."
              : available.reason
          }
          onClick={() => setPhase({ kind: "countdown", left: COUNTDOWN })}
        >
          Explain this
        </button>
      )}
      {phase.kind === "countdown" && (
        <p className="explain-status" role="status">
          Point at the text… reading in {phase.left}
          <button type="button" onClick={cancel}>
            Cancel
          </button>
        </p>
      )}
      {(phase.kind === "reading" || phase.kind === "sending") && (
        <p className="explain-status" role="status">
          {phase.kind === "reading"
            ? "Reading the text under the pointer…"
            : "Asking the local model…"}
        </p>
      )}
      {phase.kind === "preview" && (
        <div
          className="explain-preview"
          role="dialog"
          aria-label="Explain this text?"
        >
          <p className="explain-label">
            Read from your screen ({phase.from}) · stays on this PC
          </p>
          <blockquote>{phase.text}</blockquote>
          <div className="explain-actions">
            <button
              type="button"
              className="primary"
              onClick={() => void explain(phase.text)}
            >
              Explain
            </button>
            <button type="button" onClick={cancel}>
              Discard
            </button>
          </div>
        </div>
      )}
      {phase.kind === "message" && (
        <p className="explain-status" role="status">
          {phase.text}
          <button type="button" onClick={cancel}>
            OK
          </button>
        </p>
      )}
      {phase.kind === "idle" && !available.ok && connected && (
        <span className="explain-hint">{available.reason}</span>
      )}
    </div>
  );
}
