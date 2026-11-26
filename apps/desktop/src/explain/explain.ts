/**
 * "Explain this" (D24): one user-initiated read of the text under the cursor,
 * previewed before anything is sent, explained by the local model only.
 */
export interface ScreenRead {
  source?: string;
  target?: string;
  line?: string;
  selection?: string;
  denied?: string | null;
  window?: { title?: string; process?: string } | Record<string, unknown>;
}

export type Pick =
  | { ok: true; text: string; from: "selection" | "line" | "word" }
  | { ok: false; message: string };

export const MAX_EXPLAIN_CHARS = 1200;

export function pickExplainText(read: ScreenRead): Pick {
  if (read.denied)
    return {
      ok: false,
      message:
        "That window is protected (password or sign-in), so nothing was read.",
    };
  const clean = (value?: string) => (value ?? "").replace(/\s+/g, " ").trim();
  const selection = clean(read.selection);
  const line = clean(read.line);
  const word = clean(read.target);
  const [text, from] = selection
    ? [selection, "selection" as const]
    : line
      ? [line, "line" as const]
      : [word, "word" as const];
  if (text.length < 2)
    return {
      ok: false,
      message:
        "No readable text under the pointer. Point at text and try again.",
    };
  return { ok: true, text: text.slice(0, MAX_EXPLAIN_CHARS), from };
}

/** Only the local model may see screen text; the broker enforces this too. */
export function explainAvailable(
  connected: boolean,
  mode: string | undefined,
): { ok: boolean; reason: string } {
  if (!connected) return { ok: false, reason: "The local broker is offline." };
  if (mode !== "local_qwen")
    return {
      ok: false,
      reason:
        "Explain this runs only on the local model. Choose Local Qwen in the Model hub.",
    };
  return { ok: true, reason: "" };
}

export function explainRequest(session: string, text: string) {
  return {
    session_id: session,
    request_id: crypto.randomUUID(),
    content: text,
    cloud_consent: true as const,
    privacy_class: "personal" as const,
    origin: "screen" as const,
    response_length: "brief" as const,
  };
}
