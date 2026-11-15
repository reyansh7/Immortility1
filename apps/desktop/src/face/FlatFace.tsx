import type { FaceState } from "./faceState";

/** Shared, render-free face types live here so the 3D scene stays lazy-loaded. */
export const FACE_URL = "/models/immortility-face.glb";
export const FACE_IMAGE = "/models/immortility-face-2d.png";
export type Quality = "high" | "balanced" | "performance" | "2d";

export interface SceneStats {
  fps: number;
  frameMs: number;
  maxFrameMs: number;
  p95FrameMs: number;
  loadMs: number;
  /** Draw calls and triangles of one whole frame, post-processing included. */
  calls: number;
  triangles: number;
  textures: number;
  geometries: number;
  programs: number;
  /** Full-screen post-processing passes (0 = direct render). */
  passes: number;
  /** Frames the pacer currently allows per second (0 = render on change only). */
  budget: number;
  renderer: string;
}

/** 2D portrait used while the 3D scene loads, in Minimal (2D) quality, or after a lost GPU context. */
export function FlatFace({
  face,
  compact,
}: {
  face: FaceState;
  compact?: boolean;
}) {
  return (
    <div
      className={`flat-face ${face} ${compact ? "small" : ""}`}
      aria-hidden="true"
    >
      <span className="flat-glow" />
      <img src={FACE_IMAGE} alt="" draggable={false} />
    </div>
  );
}
