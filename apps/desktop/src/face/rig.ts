import type { FaceState } from "./faceState";

/**
 * Expression targets per face state. Angles are radians in head space
 * (+X pitches the chin down, +Y turns to the face's left), glow values are
 * emissive multipliers and `hue` tints the stage lights and HUD.
 */
export interface Expression {
  pitch: number;
  yaw: number;
  roll: number;
  /** Brow lift: + raises (attentive), − lowers (focused/angry). */
  brow: number;
  /** Inner-brow furrow toward the nose bridge (0..1). */
  furrow: number;
  /** Resting eyelid closure (0 open .. 1 closed). */
  lid: number;
  eye: number;
  lines: number;
  mouth: number;
  /** Eye scanning amplitude for busy states. */
  scan: number;
  /** HUD ring rotation speed multiplier. */
  spin: number;
  hue: string;
  /** How strongly the head follows the cursor (0..1). */
  follow: number;
}

// Resting look: a slightly lowered, furrowed brow and narrowed lids give the
// face its controlled, predatory focus. Hues stay inside the crimson palette;
// only "disconnected" leaves it (titanium grey = no signal).
const base: Expression = {
  pitch: 0,
  yaw: 0,
  roll: 0,
  brow: -0.15,
  furrow: 0.35,
  lid: 0.22,
  eye: 0.8,
  lines: 0.8,
  mouth: 0,
  scan: 0,
  spin: 0.35,
  hue: "#d3172f",
  follow: 1,
};

export const EXPRESSIONS: Record<FaceState, Expression> = {
  idle: { ...base },
  listening: {
    ...base,
    pitch: -0.03,
    brow: 0.1,
    furrow: 0.15,
    lid: 0.12,
    eye: 1.1,
    lines: 1,
    spin: 0.55,
    hue: "#ff2b47",
    follow: 0.35,
  },
  thinking: {
    ...base,
    pitch: -0.06,
    yaw: 0.1,
    roll: 0.05,
    furrow: 0.55,
    lid: 0.3,
    eye: 0.95,
    lines: 1.05,
    scan: 0.18,
    spin: 0.9,
    follow: 0.25,
  },
  planning: {
    ...base,
    pitch: -0.03,
    furrow: 0.5,
    lid: 0.26,
    eye: 1.05,
    lines: 1.15,
    scan: 0.3,
    spin: 1.8,
    hue: "#ff2b47",
    follow: 0.2,
  },
  delegating: {
    ...base,
    furrow: 0.3,
    eye: 1.15,
    lines: 1.15,
    scan: 0.1,
    spin: 1.2,
    hue: "#ff2b47",
    follow: 0,
  },
  executing: {
    ...base,
    pitch: 0.03,
    furrow: 0.6,
    lid: 0.3,
    eye: 1.1,
    lines: 1.2,
    scan: 0.2,
    spin: 0.7,
    hue: "#ff5a5f",
    follow: 0.15,
  },
  awaiting: {
    ...base,
    brow: 0.05,
    furrow: 0.25,
    lid: 0.15,
    eye: 0.95,
    lines: 0.9,
    spin: 0,
    hue: "#ff5a5f",
    follow: 0,
  },
  responding: {
    ...base,
    brow: 0,
    furrow: 0.25,
    lid: 0.16,
    eye: 1.05,
    lines: 1,
    mouth: 0.03,
    spin: 0.8,
    hue: "#ff2b47",
  },
  speaking: {
    ...base,
    brow: 0.02,
    furrow: 0.25,
    lid: 0.16,
    eye: 1.15,
    lines: 1.05,
    spin: 0.6,
    hue: "#ff2b47",
    follow: 0.6,
  },
  error: {
    ...base,
    pitch: 0.06,
    brow: -0.6,
    furrow: 0.9,
    lid: 0.35,
    eye: 0.7,
    lines: 0.5,
    spin: 0.1,
    hue: "#a60f25",
    follow: 0.2,
  },
  disconnected: {
    ...base,
    pitch: 0.18,
    brow: -0.4,
    lid: 0.6,
    eye: 0.1,
    lines: 0.05,
    spin: 0,
    hue: "#7e8492",
    follow: 0,
  },
};

/** States in which the scene renders at its "active" frame rate. */
export const BUSY_STATES: ReadonlySet<FaceState> = new Set<FaceState>([
  "listening",
  "thinking",
  "planning",
  "delegating",
  "executing",
  "responding",
  "speaking",
]);

/**
 * Frame-rate budget. The scene renders on demand: these are caps for the
 * invalidation pacer, 0 = render only when something changes.
 */
export type PowerProfile = "auto" | "performance" | "balanced" | "battery";

export function effectivePower(
  profile: PowerProfile = "balanced",
  onBattery = false,
): Exclude<PowerProfile, "auto"> {
  if (profile === "auto") return onBattery ? "battery" : "performance";
  return profile;
}

export function frameBudget(options: {
  quality: "high" | "balanced" | "performance" | "2d";
  compact: boolean;
  active: boolean;
  reduced: boolean;
  visible: boolean;
  /** Launch profile. Omitted keeps the original fixed table. */
  power?: PowerProfile;
  onBattery?: boolean;
}): number {
  const { quality, compact, active, reduced, visible } = options;
  if (!visible || quality === "2d") return 0;
  if (reduced) return active ? 12 : 0;
  if (options.power) {
    const power = effectivePower(options.power, options.onBattery);
    if (power === "battery")
      return compact ? (active ? 20 : 6) : active ? 30 : 8;
    if (power === "balanced") {
      if (compact) return active ? 30 : 8;
      return active ? (quality === "performance" ? 30 : 45) : 8;
    }
    if (compact) return active ? 30 : 12;
    return active ? (quality === "performance" ? 30 : 60) : 12;
  }
  if (compact) return active ? 30 : 12;
  const table = { high: [60, 30], balanced: [60, 24], performance: [30, 15] };
  return table[quality][active ? 0 : 1];
}

/** Device-pixel-ratio ceiling. Battery cuts resolution before it cuts materials. */
export function pixelRatioCap(options: {
  quality: "high" | "balanced" | "performance" | "2d";
  compact: boolean;
  power?: PowerProfile;
  onBattery?: boolean;
}): number {
  const power = options.power
    ? effectivePower(options.power, options.onBattery)
    : "balanced";
  if (options.compact) return power === "battery" ? 1 : 1.25;
  if (power === "battery" || options.quality === "performance") return 1;
  if (power === "balanced") return 1.25;
  return options.quality === "high" ? 1.75 : 1.25;
}

export function graphicsHint(
  power: PowerProfile = "balanced",
  onBattery = false,
): "high-performance" | "low-power" {
  return effectivePower(power, onBattery) === "performance"
    ? "high-performance"
    : "low-power";
}

/**
 * Jaw opening from the reported playback level only. No level means no
 * movement: the mouth never "chatters" on a guess.
 */
export function jawOpen(energy: number, rhythm: number): number {
  return energy * (0.35 + 0.65 * rhythm) * 0.8;
}

/** Fast-attack, slow-release follower for the sparse (≈12 Hz) playback level. */
export function envelope(previous: number, target: number, dt: number): number {
  const rate = target > previous ? 22 : 7;
  return previous + (target - previous) * (1 - Math.exp(-rate * dt));
}

/**
 * Syllable-like jaw motion: the broker reports playback RMS a few times per
 * second, so the mouth opens on a quasi-random 4-6 Hz rhythm scaled by it.
 */
export function syllable(t: number): number {
  const a = Math.sin(t * 10.7 + Math.sin(t * 2.3) * 1.9);
  const b = Math.sin(t * 6.1 + 1.3);
  return Math.min(1, Math.max(0, 0.55 + 0.35 * a + 0.2 * b));
}

/** Playback RMS sits around 0.05–0.25; map it to a 0..1 speech energy. */
export function speechEnergy(level: number): number {
  return Number.isFinite(level) ? Math.max(0, Math.min(1, level * 4)) : 0;
}

/** Seconds until the next blink; occasional quick double blinks. */
export function nextBlink(random: () => number = Math.random): number {
  const r = random();
  return r < 0.14 ? 0.22 : 2.2 + random() * 4;
}

/** Lid closure for a blink that started `since` seconds ago (0..1). */
export function blinkAmount(since: number, length = 0.17): number {
  if (since < 0 || since > length) return 0;
  const x = since / length;
  return x < 0.4 ? x / 0.4 : 1 - (x - 0.4) / 0.6;
}
