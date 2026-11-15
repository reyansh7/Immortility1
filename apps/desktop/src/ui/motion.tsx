import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  type ReactNode,
  type RefObject,
} from "react";

gsap.registerPlugin(useGSAP);
// Entrance/page tweens must finish even after a long frame (cold start, GPU
// stall); lag smoothing would otherwise leave panels half-faded.
gsap.ticker.lagSmoothing(0);
export { gsap, useGSAP };

/** Mirrors the "Reduce motion" interface preference for every animated widget. */
const ReducedMotion = createContext(false);
export function MotionProvider({
  reduced,
  children,
}: {
  reduced: boolean;
  children: ReactNode;
}) {
  useEffect(() => {
    gsap.globalTimeline.timeScale(reduced ? 1000 : 1);
  }, [reduced]);
  return (
    <ReducedMotion.Provider value={reduced}>{children}</ReducedMotion.Provider>
  );
}
export const useReducedMotion = () => useContext(ReducedMotion);

const finePointer = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(hover: hover) and (pointer: fine)").matches;

/** Subtle 3D tilt toward the cursor with a moving specular sheen. */
export function useTilt<T extends HTMLElement>(max = 6): RefObject<T | null> {
  const ref = useRef<T>(null);
  const reduced = useReducedMotion();
  useEffect(() => {
    const node = ref.current;
    if (!node || reduced || !finePointer() || max <= 0) return;
    const rx = gsap.quickTo(node, "rotationX", {
      duration: 0.5,
      ease: "power3",
    });
    const ry = gsap.quickTo(node, "rotationY", {
      duration: 0.5,
      ease: "power3",
    });
    gsap.set(node, {
      transformPerspective: 900,
      transformStyle: "preserve-3d",
    });
    const move = (event: PointerEvent) => {
      const box = node.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width;
      const y = (event.clientY - box.top) / box.height;
      rx((0.5 - y) * max);
      ry((x - 0.5) * max);
      node.style.setProperty("--mx", `${x * 100}%`);
      node.style.setProperty("--my", `${y * 100}%`);
    };
    const leave = () => {
      rx(0);
      ry(0);
    };
    node.addEventListener("pointermove", move);
    node.addEventListener("pointerleave", leave);
    return () => {
      node.removeEventListener("pointermove", move);
      node.removeEventListener("pointerleave", leave);
      gsap.set(node, { clearProps: "transform" });
    };
  }, [max, reduced]);
  return ref;
}

/** Buttons that lean toward the cursor while hovered. */
export function useMagnetic<T extends HTMLElement>(
  strength = 0.3,
): RefObject<T | null> {
  const ref = useRef<T>(null);
  const reduced = useReducedMotion();
  useEffect(() => {
    const node = ref.current;
    if (!node || reduced || !finePointer()) return;
    const x = gsap.quickTo(node, "x", { duration: 0.4, ease: "power3" });
    const y = gsap.quickTo(node, "y", { duration: 0.4, ease: "power3" });
    const move = (event: PointerEvent) => {
      const box = node.getBoundingClientRect();
      x((event.clientX - (box.left + box.width / 2)) * strength);
      y((event.clientY - (box.top + box.height / 2)) * strength);
    };
    const leave = () => {
      gsap.to(node, { x: 0, y: 0, duration: 0.7, ease: "elastic.out(1, 0.4)" });
    };
    node.addEventListener("pointermove", move);
    node.addEventListener("pointerleave", leave);
    return () => {
      node.removeEventListener("pointermove", move);
      node.removeEventListener("pointerleave", leave);
      gsap.set(node, { clearProps: "transform" });
    };
  }, [strength, reduced]);
  return ref;
}

/** Number that rolls to its new value. */
export function Counter({
  value,
  decimals = 0,
  suffix = "",
}: {
  value: number;
  decimals?: number;
  suffix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const shown = useRef({ v: 0 });
  const reduced = useReducedMotion();
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const paint = () =>
      (node.textContent = `${shown.current.v.toFixed(decimals)}${suffix}`);
    if (reduced) {
      shown.current.v = value;
      paint();
      return;
    }
    const tween = gsap.to(shown.current, {
      v: value,
      duration: 1.1,
      ease: "power3.out",
      onUpdate: paint,
    });
    return () => {
      tween.kill();
    };
  }, [value, decimals, suffix, reduced]);
  return (
    <span ref={ref} className="counter">
      {`0${suffix}`}
    </span>
  );
}

/** Smoothed SVG sparkline with a gradient fill that draws itself in. */
export function Sparkline({
  values,
  color = "var(--accent)",
  height = 34,
  label,
}: {
  values: number[];
  color?: string;
  height?: number;
  label: string;
}) {
  const path = useRef<SVGPathElement>(null);
  const id = useRef(`spark-${Math.random().toString(36).slice(2, 8)}`);
  const reduced = useReducedMotion();
  const width = 120;
  const points = values.length > 1 ? values : [0, 0];
  const max = Math.max(...points, 1e-6);
  const min = Math.min(...points, 0);
  const span = max - min || 1;
  const xy = points.map((v, i) => [
    (i / (points.length - 1)) * width,
    height - 3 - ((v - min) / span) * (height - 8),
  ]);
  let d = `M${xy[0][0].toFixed(1)},${xy[0][1].toFixed(1)}`;
  for (let i = 1; i < xy.length; i += 1) {
    const [x0, y0] = xy[i - 1];
    const [x1, y1] = xy[i];
    const cx = (x0 + x1) / 2;
    d += ` C${cx.toFixed(1)},${y0.toFixed(1)} ${cx.toFixed(1)},${y1.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`;
  }
  const area = `${d} L${width},${height} L0,${height} Z`;
  useGSAP(
    () => {
      const node = path.current;
      if (!node || reduced) return;
      const length = node.getTotalLength();
      gsap.fromTo(
        node,
        { strokeDasharray: length, strokeDashoffset: length },
        { strokeDashoffset: 0, duration: 1.4, ease: "power2.out" },
      );
    },
    { dependencies: [reduced] },
  );
  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      <defs>
        <linearGradient id={id.current} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.45" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id.current})`} />
      <path
        ref={path}
        d={d}
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/** Keeps the last `size` samples of a changing value. */
export function useHistory(value: number | undefined, size = 24): number[] {
  const history = useRef<number[]>([]);
  const last = useRef<number | undefined>(undefined);
  if (value !== undefined && value !== last.current) {
    last.current = value;
    history.current = [...history.current, value].slice(-size);
  }
  return history.current;
}

/**
 * Static backdrop: obsidian base, a low crimson horizon and a vignette, all
 * plain gradients painted once. (The earlier animated aurora, grid and 2D
 * particle canvas repainted the whole window up to 30 times a second.)
 */
export function Backdrop() {
  return (
    <div className="backdrop" aria-hidden="true">
      <div className="horizon" />
      <div className="vignette" />
    </div>
  );
}
