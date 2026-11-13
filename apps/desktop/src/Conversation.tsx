import { useEffect, useRef, useState } from "react";
import { Markdown } from "./Markdown";
import { terminal, type Task, type Transcript } from "./state";
import { api } from "./transport";

interface ExecutionTrace {
  outcome: string;
  duration_ms: number;
  transitions: { state: string; timestamp: string }[];
  delegations?: { role: string; status: string }[];
  tools: { status: string; calls: unknown[] };
  agent: { runtime: string; route: string };
  completion_evidence: { streamed_chunks: number };
}

const message = (issue: unknown, fallback: string) =>
  issue instanceof Error ? issue.message : fallback;

function TaskTrace({ taskId }: { taskId: string }) {
  const [trace, setTrace] = useState<ExecutionTrace | null>(null);
  const [error, setError] = useState("");
  function load(open: boolean) {
    if (!open || trace || error) return;
    void api<ExecutionTrace>(`/v1/tasks/${taskId}/trace`)
      .then(setTrace)
      .catch((issue: unknown) =>
        setError(message(issue, "Trace unavailable.")),
      );
  }
  return (
    <details onToggle={(event) => load(event.currentTarget.open)}>
      <summary>Execution trace</summary>
      {error && <p className="error">{error}</p>}
      {trace && (
        <div className="trace">
          <p>
            {trace.agent.runtime} · {trace.agent.route} · {trace.outcome} ·{" "}
            {Math.round(trace.duration_ms)} ms · tools {trace.tools.status} ·{" "}
            {trace.completion_evidence.streamed_chunks} streamed parts
          </p>
          {(trace.delegations ?? []).length > 0 && (
            <ol>
              {(trace.delegations ?? []).map((step, index) => (
                <li key={`${step.role}-${step.status}-${index}`}>
                  {step.role} {step.status}
                </li>
              ))}
            </ol>
          )}
          <ol>
            {trace.transitions.map((step, index) => (
              <li key={`${step.state}-${index}`}>{step.state}</li>
            ))}
          </ol>
        </div>
      )}
    </details>
  );
}

export function Approval({
  taskId,
  onError,
}: {
  taskId: string;
  onError: (message: string) => void;
}) {
  const decide = (decision: "approve" | "deny") =>
    void api(`/v1/tasks/${taskId}/approval`, { decision }).catch(
      (issue: unknown) =>
        onError(
          message(
            issue,
            decision === "approve"
              ? "Approval failed."
              : "Could not deny the change.",
          ),
        ),
    );
  return (
    <div className="approval">
      <button
        type="button"
        className="primary"
        onClick={() => decide("approve")}
      >
        Approve change
      </button>
      <button type="button" onClick={() => decide("deny")}>
        Deny change
      </button>
    </div>
  );
}

export function Messages({
  tasks,
  transcripts,
  ready,
  reduced,
  onError,
  onSpeak,
}: {
  tasks: Task[];
  transcripts: Record<string, Transcript>;
  ready: boolean;
  reduced: boolean;
  onError: (message: string) => void;
  onSpeak: (taskId: string) => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  useEffect(() => {
    const node = scroller.current;
    if (node && pinned.current)
      node.scrollTo({
        top: node.scrollHeight,
        behavior: reduced ? "instant" : "smooth",
      });
  }, [transcripts, tasks, reduced]);
  return (
    <div
      ref={scroller}
      className="timeline"
      role="log"
      aria-label="Conversation history"
      aria-live="polite"
      aria-relevant="additions text"
      onScroll={(event) => {
        const node = event.currentTarget;
        pinned.current =
          node.scrollHeight - node.scrollTop - node.clientHeight < 48;
      }}
    >
      {!tasks.length && (
        <div className="welcome">
          <span className="eyebrow">IMMORTILITY · HERMES</span>
          <h1>What should we work on?</h1>
          <p>
            {ready
              ? "A conversation with Hermes on the free OpenRouter route. Tools stay off unless you enable them in Settings."
              : "Add an OpenRouter key in Settings, then check the connection. A verified Hermes installation is also required."}
          </p>
        </div>
      )}
      {tasks.map((task) => {
        const live = transcripts[task.task_id],
          status = live?.status ?? task.status,
          text = task.result?.text ?? live?.text;
        const model = task.result
          ? `${task.result.provider} · ${task.result.model}`
          : "Hermes · OpenRouter / free";
        return (
          <article key={task.task_id}>
            <div className="user-message">
              <small>YOU</small>
              <p>{task.input.content}</p>
            </div>
            <div className="assistant-message">
              <small>
                IMMORTILITY <span>{model}</span>
              </small>
              {text && <Markdown text={text} />}
              {!text && !terminal.has(status) && (
                <p className="waiting">Waiting for Hermes…</p>
              )}
              {live?.preview && (
                <pre className="diff-preview">{live.preview}</pre>
              )}
              {status === "awaiting_approval" && (
                <Approval taskId={task.task_id} onError={onError} />
              )}
              <div className={`task-status ${status}`}>
                {status.replaceAll("_", " ")}
                {status === "cancelled" ? " · partial response retained" : ""}
                {live?.metrics &&
                  ` · ${live.metrics.route_mode} · ${live.metrics.calls} model calls · ${live.metrics.latency_ms} ms`}
                {live?.metrics?.first_token_ms !== undefined &&
                  ` · first token ${live.metrics.first_token_ms} ms`}
                {live?.metrics?.prompt_tokens !== undefined &&
                  ` · ${live.metrics.prompt_tokens}/${live.metrics.completion_tokens ?? 0} tokens`}
              </div>
              {(task.error?.message ?? live?.error) && (
                <p className="error" role="alert">
                  {task.error?.message ?? live?.error}
                </p>
              )}
              <div className="message-actions">
                {!terminal.has(status) && (
                  <button
                    type="button"
                    onClick={() =>
                      void api(`/v1/tasks/${task.task_id}/cancel`, {}).catch(
                        (issue: unknown) =>
                          onError(message(issue, "Cancel failed.")),
                      )
                    }
                  >
                    Cancel task
                  </button>
                )}
                {status === "succeeded" && (
                  <button type="button" onClick={() => onSpeak(task.task_id)}>
                    Read aloud
                  </button>
                )}
                {status === "succeeded" && live?.preview && (
                  <button
                    type="button"
                    onClick={() =>
                      void api(`/v1/tasks/${task.task_id}/rollback`, {}).catch(
                        (issue: unknown) =>
                          onError(message(issue, "Rollback failed.")),
                      )
                    }
                  >
                    Restore previous file
                  </button>
                )}
              </div>
              <TaskTrace taskId={task.task_id} />
            </div>
          </article>
        );
      })}
    </div>
  );
}

export function Composer({
  input,
  setInput,
  consent,
  setConsent,
  running,
  canSend,
  onSend,
  onStop,
  quickActions,
}: {
  input: string;
  setInput: (value: string) => void;
  consent: boolean;
  setConsent: (value: boolean) => void;
  running: boolean;
  canSend: boolean;
  onSend: () => void;
  onStop: () => void;
  quickActions?: boolean;
}) {
  const actions = [
    ["Create", "Draft "],
    ["Analyze", "Analyze "],
    ["Plan", "Make a step-by-step plan for "],
    ["Learn", "Explain "],
  ] as const;
  return (
    <form
      className="composer-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSend();
      }}
    >
      <div className="composer">
        <textarea
          aria-label="Message Hermes"
          placeholder="Ask Immortility anything…"
          maxLength={16000}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
        />
        {running ? (
          <button className="send stop" type="button" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button
            className="send"
            type="submit"
            aria-label="Send message"
            disabled={!canSend || !input.trim()}
          >
            ↑
          </button>
        )}
      </div>
      <div className="composer-meta">
        <label className="consent">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          Send this conversation to the free cloud model
        </label>
        {quickActions && (
          <div className="quick-actions" aria-label="Prompt starters">
            {actions.map(([label, prefix]) => (
              <button
                key={label}
                type="button"
                onClick={() =>
                  setInput(input.startsWith(prefix) ? input : prefix + input)
                }
              >
                {label}
              </button>
            ))}
          </div>
        )}
        <span className="hint">Enter to send · Shift+Enter for a new line</span>
      </div>
    </form>
  );
}
