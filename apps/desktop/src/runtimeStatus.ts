import { api } from "./transport";
import type { Health } from "./SettingsPanel";
import type { VoiceState } from "./useVoice";

export interface ScreenAccess {
  active: boolean;
  kind: string;
  reads: number;
  last_ms: number | null;
  last_source: string;
  cloud: false;
}

export interface RuntimeStatus {
  revision: number;
  health: Health;
  voice_state: VoiceState;
  screen_access?: ScreenAccess;
}

/** Privacy indicator text while the broker is reading the screen (local only), else null. */
export function screenIndicator(value: RuntimeStatus): string | null {
  const access = value.screen_access;
  if (!access?.active) return null;
  return access.kind === "hover_target"
    ? "● Reading text under cursor (on this PC)"
    : "● Reading screen (on this PC)";
}

function pause(signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", done);
      resolve();
    };
    const timer = setTimeout(done, 1000);
    if (signal.aborted) done();
    else signal.addEventListener("abort", done, { once: true });
  });
}

/** One read-only long poll; revisions wake immediately, quiet peers heartbeat. */
export async function followRuntimeStatus(
  signal: AbortSignal,
  onStatus: (value: RuntimeStatus) => void,
  onUnavailable: () => void,
  request: (path: string) => Promise<RuntimeStatus> = api,
): Promise<void> {
  let revision: number | undefined;
  while (!signal.aborted) {
    try {
      const value = await request(
        `/v1/runtime/status${revision === undefined ? "" : `?after=${revision}`}`,
      );
      if (signal.aborted) return;
      if (!Number.isSafeInteger(value.revision) || value.revision < 0)
        throw new Error("Invalid runtime revision.");
      revision = value.revision;
      onStatus(value);
    } catch {
      if (signal.aborted) return;
      revision = undefined;
      onUnavailable();
      await pause(signal);
    }
  }
}
