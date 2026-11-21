/**
 * Always-visible status strip: what Immortility is doing and which senses or
 * controls are live. Every indicator carries a text label (never colour only) and
 * the strip is a polite live region, so screen readers hear changes.
 */
export type HudLevel = "off" | "on" | "live" | "warn";

export interface HudInput {
  presence: string;
  connected: boolean;
  voiceState?: string;
  screenReading?: string | null;
  pointer?: "moving" | "idle";
  route?: string;
}

export interface HudItem {
  key: "system" | "mic" | "screen" | "cursor" | "model";
  label: string;
  value: string;
  level: HudLevel;
}

const listening = new Set(["LISTENING", "RECORDING"]);
const voiceBusy = new Set(["TRANSCRIBING", "THINKING", "SPEAKING"]);

export function hudItems(input: HudInput): HudItem[] {
  const voice = (input.voiceState ?? "IDLE").toUpperCase();
  const route = input.route ?? "auto_cloud";
  const local = route.startsWith("local");
  return [
    {
      key: "system",
      label: "System",
      value: input.presence,
      level: !input.connected
        ? "warn"
        : input.presence === "Ready"
          ? "on"
          : "live",
    },
    {
      key: "mic",
      label: "Mic",
      value: listening.has(voice)
        ? "Listening"
        : voiceBusy.has(voice)
          ? voice.charAt(0) + voice.slice(1).toLowerCase()
          : voice === "ERROR"
            ? "Error"
            : "Off",
      level: listening.has(voice)
        ? "live"
        : voice === "ERROR"
          ? "warn"
          : voiceBusy.has(voice)
            ? "on"
            : "off",
    },
    {
      key: "screen",
      label: "Screen",
      value: input.screenReading ? "Reading" : "Off",
      level: input.screenReading ? "live" : "off",
    },
    {
      key: "cursor",
      label: "Cursor",
      value: input.pointer === "moving" ? "Moving" : "Yours",
      level: input.pointer === "moving" ? "live" : "off",
    },
    {
      key: "model",
      label: "Model",
      value: local
        ? "Local"
        : route === "auto_cloud"
          ? "Auto"
          : route === "manual_cloud"
            ? "Cloud"
            : route,
      level: local ? "on" : "off",
    },
  ];
}

export function StatusHud(props: HudInput & { compact?: boolean }) {
  const items = hudItems(props);
  const summary = items
    .filter((item) => item.level === "live" || item.level === "warn")
    .map((item) => `${item.label} ${item.value}`)
    .join(", ");
  return (
    <div
      className={`status-hud ${props.compact ? "compact" : ""}`}
      role="status"
      aria-live="polite"
      aria-label={summary ? `Live: ${summary}` : "Nothing live"}
    >
      {items.map((item) => (
        <span
          key={item.key}
          className={`hud-chip hud-${item.key} level-${item.level}`}
          title={`${item.label}: ${item.value}`}
        >
          <span className="hud-dot" aria-hidden="true" />
          <span className="hud-label">{item.label}</span>
          <span className="hud-value">{item.value}</span>
        </span>
      ))}
    </div>
  );
}
