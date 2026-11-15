import { api } from "./transport";
import type { Health } from "./SettingsPanel";
import type { VoiceState } from "./useVoice";

export interface RuntimeStatus {
  revision: number;
  health: Health;
  voice_state: VoiceState;
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
