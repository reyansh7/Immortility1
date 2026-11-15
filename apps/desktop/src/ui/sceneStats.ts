import { useEffect, useState, useSyncExternalStore } from "react";
import type { SceneStats } from "../face/FlatFace";

/*
 * Renderer statistics arrive once per second. Keeping them in a tiny external
 * store means only the panels that show them re-render — not the whole
 * command center (chat, composer and timeline included).
 */
let current: SceneStats | null = null;
const listeners = new Set<() => void>();

export function publishStats(stats: SceneStats | null): void {
  current = stats;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useSceneStats(): SceneStats | null {
  return useSyncExternalStore(
    subscribe,
    () => current,
    () => null,
  );
}

/** Re-renders only its caller once per second while `active`. */
export function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);
  return now;
}
