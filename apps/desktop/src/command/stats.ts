import { terminal, type Task, type Transcript } from "../state";

export interface SessionPulse {
  total: number;
  finished: number;
  succeeded: number;
  running: number;
  /** Percentage of finished tasks that succeeded, or undefined when none finished. */
  successRate?: number;
  /** Mean route latency over tasks that reported metrics. */
  avgLatency?: number;
  /** Route latency per task, oldest first. */
  latencies: number[];
  tokens: number;
}

/** Aggregates real broker data for the Home pulse tiles; nothing is estimated. */
export function summarize(
  tasks: Task[],
  transcripts: Record<string, Transcript>,
): SessionPulse {
  let finished = 0;
  let succeeded = 0;
  let running = 0;
  let tokens = 0;
  const latencies: number[] = [];
  for (const task of tasks) {
    const live = transcripts[task.task_id];
    const status = live?.status ?? task.status;
    if (terminal.has(status)) finished += 1;
    else running += 1;
    if (status === "succeeded") succeeded += 1;
    const metrics = live?.metrics;
    if (metrics) {
      latencies.push(metrics.latency_ms);
      tokens += (metrics.prompt_tokens ?? 0) + (metrics.completion_tokens ?? 0);
    }
  }
  return {
    total: tasks.length,
    finished,
    succeeded,
    running,
    successRate: finished
      ? Math.round((succeeded / finished) * 100)
      : undefined,
    avgLatency: latencies.length
      ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)
      : undefined,
    latencies,
    tokens,
  };
}

/** Time-of-day greeting for the Home hero. */
export function greeting(hour: number): string {
  if (hour < 5) return "Working late";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
