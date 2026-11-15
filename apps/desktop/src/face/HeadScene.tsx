import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import {
  Component,
  memo,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { playbackEnergy, type FaceState, type Role } from "./faceState";
import { FACE_URL, FlatFace, type Quality, type SceneStats } from "./FlatFace";
import {
  BUSY_STATES,
  EXPRESSIONS,
  blinkAmount,
  envelope,
  effectivePower,
  frameBudget,
  graphicsHint,
  jawOpen,
  nextBlink,
  pixelRatioCap,
  speechEnergy,
  syllable,
  type PowerProfile,
} from "./rig";
import { BoneDriver } from "./boneDriver";

export type { Quality, SceneStats } from "./FlatFace";

/*
 * Lighting language shared with the CSS theme: obsidian surroundings, a dim
 * neutral key from above, crimson rim light and controlled emissive seams.
 * Everything renders on demand (frameloop="demand") through the Pacer below.
 */
const ENERGY = new THREE.Color("#ff2b47");
const TITANIUM = "#2a2d34";
const GUNMETAL = "#1b1d22";

function rendererName(gl: THREE.WebGLRenderer): string {
  const context = gl.getContext();
  const info = context.getExtension("WEBGL_debug_renderer_info");
  const name = info
    ? context.getParameter(info.UNMASKED_RENDERER_WEBGL)
    : context.getParameter(context.RENDERER);
  return String(name)
    .replace(/^ANGLE \(/, "")
    .replace(/\)$/, "")
    .slice(0, 90);
}

/** Live values the face writes each frame and the chamber/lights read. */
interface Signal {
  hue: THREE.Color;
  spin: number;
  energy: number;
  busy: number;
  eye: number;
}

interface Pointer {
  x: number;
  y: number;
  seen: boolean;
  moved: number;
}

/** Cursor position relative to the canvas centre, tracked across the whole window. */
function usePointer(host: RefObject<HTMLDivElement | null>) {
  const pointer = useRef<Pointer>({ x: 0, y: 0, seen: false, moved: 0 });
  useEffect(() => {
    let box: DOMRect | null = null;
    const measure = () => (box = host.current?.getBoundingClientRect() ?? null);
    const move = (event: PointerEvent) => {
      if (!box) measure();
      if (!box) return;
      const x = (event.clientX - (box.left + box.width / 2)) / (box.width / 2);
      const y =
        -(event.clientY - (box.top + box.height / 2)) / (box.height / 2);
      const p = pointer.current;
      p.x = Math.max(-1.6, Math.min(1.6, x));
      p.y = Math.max(-1.6, Math.min(1.6, y));
      p.seen = true;
      p.moved = performance.now();
    };
    const reset = () => (box = null);
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("resize", reset);
    window.addEventListener("scroll", reset, true);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("resize", reset);
      window.removeEventListener("scroll", reset, true);
    };
  }, [host]);
  return pointer;
}

/** False while the window is hidden/minimized or the canvas is scrolled away. */
function useVisible(host: RefObject<HTMLDivElement | null>): boolean {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const node = host.current;
    let inView = true;
    const update = () =>
      setVisible(inView && document.visibilityState === "visible");
    const observer =
      node && typeof IntersectionObserver !== "undefined"
        ? new IntersectionObserver(([entry]) => {
            inView = entry.isIntersecting;
            update();
          })
        : null;
    if (node) observer?.observe(node);
    document.addEventListener("visibilitychange", update);
    return () => {
      observer?.disconnect();
      document.removeEventListener("visibilitychange", update);
    };
  }, [host]);
  return visible;
}

let glow: THREE.CanvasTexture | null = null;
function glowTexture(): THREE.CanvasTexture {
  if (glow) return glow;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const context = canvas.getContext("2d")!;
  const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.25, "rgba(255,255,255,0.45)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 64, 64);
  glow = new THREE.CanvasTexture(canvas);
  return glow;
}

const BONES = [
  "Head",
  "Jaw",
  "LipLowerL",
  "LipLowerR",
  "LipUpperL",
  "LipUpperR",
  "MouthCornerL",
  "MouthCornerR",
  "EyeL",
  "EyeR",
  "LidUpperL",
  "LidUpperR",
  "LidLowerL",
  "LidLowerR",
  "BrowInnerL",
  "BrowInnerR",
  "BrowOuterL",
  "BrowOuterR",
] as const;
type BoneName = (typeof BONES)[number];

interface Rig {
  root: THREE.Object3D;
  bones: Partial<Record<BoneName, BoneDriver>>;
  armor: THREE.MeshStandardMaterial;
  glow: THREE.MeshBasicMaterial;
  halos: THREE.Sprite[];
  dispose: () => void;
}

/**
 * One standard PBR material for the armour (albedo, ORM, normal, seam
 * emission from the GLB) and one unlit material for eyes and mouth: two
 * programs, two draw calls for the whole face.
 */
function prepare(source: THREE.Object3D, compact: boolean): Rig {
  const root = cloneSkinned(source);
  const created: THREE.Material[] = [];
  let armor: THREE.MeshStandardMaterial | null = null;
  const glowMaterial = new THREE.MeshBasicMaterial({ color: ENERGY });
  created.push(glowMaterial);
  root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;
    object.frustumCulled = false;
    const original = object.material as THREE.MeshStandardMaterial;
    if (object.name.startsWith("FaceGlow")) {
      object.material = glowMaterial;
      return;
    }
    armor = new THREE.MeshStandardMaterial({
      map: original.map,
      normalMap: original.normalMap,
      normalScale: new THREE.Vector2(1.15, 1.15),
      roughnessMap: original.roughnessMap,
      metalnessMap: original.metalnessMap,
      emissiveMap: original.emissiveMap,
      emissive: "#ffffff",
      emissiveIntensity: 0.9,
      metalness: 1,
      roughness: 1,
      envMapIntensity: compact ? 1.5 : 1.6,
      side: THREE.DoubleSide,
    });
    created.push(armor);
    object.material = armor;
  });
  if (!armor) throw new Error("Face shell missing from the model.");
  const bones: Rig["bones"] = {};
  for (const name of BONES) {
    const bone = root.getObjectByName(name);
    if (bone) bones[name] = new BoneDriver(bone, root);
  }
  // Two small additive sprites stand in for bloom around the eyes on tiers
  // without post-processing (and add a tight core on High).
  const halos: THREE.Sprite[] = [];
  const head = bones.Head?.bone;
  if (head) {
    root.updateMatrixWorld(true);
    for (const side of ["EyeL", "EyeR"] as const) {
      const eye = bones[side]?.bone;
      if (!eye) continue;
      const at = eye.getWorldPosition(new THREE.Vector3());
      at.z += 0.2;
      const halo = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: glowTexture(),
          color: ENERGY,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
          transparent: true,
          opacity: 0.3,
        }),
      );
      created.push(halo.material);
      head.worldToLocal(at);
      halo.position.copy(at);
      const s = 1 / (head.getWorldScale(new THREE.Vector3()).x || 1);
      halo.scale.set(0.5 * s, 0.17 * s, 1);
      head.add(halo);
      halos.push(halo);
    }
  }
  return {
    root,
    bones,
    armor,
    glow: glowMaterial,
    halos,
    dispose: () => created.forEach((material) => material.dispose()),
  };
}

/** Where the face looks (yaw, pitch) when it hands work to a specialist node. */
const AGENT_LOOK: Record<Role, [number, number]> = {
  research: [-0.48, 0.08],
  review: [-0.42, -0.14],
  coding: [0.48, 0.08],
};

function Face({
  face,
  agent,
  level,
  reduced,
  hovered,
  follow,
  signal,
  compact,
}: {
  face: FaceState;
  agent?: Role;
  level: RefObject<number>;
  reduced: boolean;
  hovered: boolean;
  follow: RefObject<Pointer>;
  signal: RefObject<Signal>;
  compact: boolean;
}) {
  const gltf = useLoader(GLTFLoader, FACE_URL);
  const rig = useMemo(() => prepare(gltf.scene, compact), [gltf, compact]);
  useEffect(() => () => rig.dispose(), [rig]);
  const timeline = useRef({
    state: face,
    since: 0,
    blinkAt: 1.5,
    blinkStart: -10,
    poke: -10,
    energy: 0,
    pokeRequested: false,
  });
  const cur = useRef({
    ...EXPRESSIONS.idle,
    hue: new THREE.Color(EXPRESSIONS.idle.hue),
    px: 0,
    py: 0,
  });
  const target = useMemo(() => new THREE.Color(), []);
  const scratch = useMemo(() => new THREE.Vector3(), []);
  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    const dt = Math.min(delta, 0.1);
    const tl = timeline.current;
    if (tl.state !== face) {
      tl.state = face;
      tl.since = t;
    }
    const since = t - tl.since;
    if (tl.pokeRequested) {
      tl.pokeRequested = false;
      tl.poke = t;
      tl.blinkStart = t;
    }
    const e = EXPRESSIONS[face];
    const c = cur.current;
    const live = !reduced;
    const k = (rate: number) => 1 - Math.exp(-rate * dt);
    const ease = k(4);
    for (const key of [
      "pitch",
      "yaw",
      "roll",
      "brow",
      "furrow",
      "lid",
      "eye",
      "lines",
      "mouth",
      "scan",
      "spin",
      "follow",
    ] as const)
      c[key] += (e[key] - c[key]) * ease;
    target.set(e.hue);
    c.hue.lerp(target, k(3));

    // Speech energy comes only from the broker's reported playback level
    // (playbackEnergy: 0 on silence, stop or an invalid meter). When speech
    // stops or is cancelled the jaw closes quickly instead of easing out.
    const raw = level.current ?? 0;
    const speaking = face === "speaking";
    tl.energy = speaking
      ? envelope(tl.energy, playbackEnergy(raw, true), dt)
      : Math.max(0, tl.energy - dt * 6);
    const energy = tl.energy;
    const mic = face === "listening" ? speechEnergy(raw) : 0;

    const pointer = follow.current;
    const px = pointer.seen && live ? pointer.x : 0;
    const py = pointer.seen && live ? pointer.y : 0;
    c.px += (px - c.px) * k(5);
    c.py += (py - c.py) * k(5);

    if (live && t > tl.blinkAt) {
      tl.blinkStart = t;
      tl.blinkAt = t + nextBlink();
    }
    const blink = face === "disconnected" ? 0 : blinkAmount(t - tl.blinkStart);
    const closure = Math.min(1, Math.max(c.lid, blink));
    const poke = Math.exp(-(t - tl.poke) * 4);

    let yaw = c.yaw + c.px * 0.36 * c.follow;
    let pitch = c.pitch - c.py * 0.18 * c.follow;
    let roll = c.roll;
    let bob = 0;
    if (live) {
      // Slow hover plus tiny servo-like corrections.
      yaw += 0.035 * Math.sin(t * 0.21) + 0.012 * Math.sin(t * 0.83 + 1);
      pitch += 0.014 * Math.sin(t * 0.29) + 0.006 * Math.sin(t * 1.7);
      roll += 0.01 * Math.sin(t * 0.37 + 2);
      bob = 0.03 * Math.sin(t * 0.9);
      pitch += energy * 0.02 * Math.sin(t * 5.1);
      // Error: one controlled recoil, no shaking or flashing.
      if (face === "error") pitch += 0.06 * Math.exp(-since * 2.2);
      if (face === "thinking") roll += 0.025 * Math.sin(t * 0.6);
      pitch -= poke * 0.08;
    }
    if (face === "delegating" && agent) {
      const [lookYaw, lookPitch] = AGENT_LOOK[agent];
      yaw = lookYaw * Math.min(1, since * 1.5);
      pitch = lookPitch * Math.min(1, since * 1.5);
    }
    const b = rig.bones;
    b.Head?.set(pitch, yaw, roll);
    rig.root.position.y = bob + (hovered ? 0.03 : 0);

    // Jaw moves only with reported voice level; restrained amplitude.
    const open = c.mouth + (live ? jawOpen(energy, syllable(t)) : energy * 0.4);
    const wide = energy * (0.4 + 0.3 * Math.sin(t * 4.1));
    b.Jaw?.set(open * 0.21, 0, 0);
    b.LipLowerL?.set(open * 0.07, 0, 0, scratch.set(0, -open * 0.008, 0));
    b.LipLowerR?.set(open * 0.07, 0, 0, scratch.set(0, -open * 0.008, 0));
    b.LipUpperL?.set(0, 0, 0, scratch.set(0, open * 0.01, 0));
    b.LipUpperR?.set(0, 0, 0, scratch.set(0, open * 0.01, 0));
    b.MouthCornerL?.set(0, 0, 0, scratch.set(wide * 0.016, -open * 0.02, 0));
    b.MouthCornerR?.set(0, 0, 0, scratch.set(-wide * 0.016, -open * 0.02, 0));

    const scan = live ? c.scan * Math.sin(t * 1.9) * 0.3 : 0;
    const eyeYaw = c.px * 0.14 * c.follow + scan;
    const eyePitch = -c.py * 0.07 * c.follow;
    const squash = Math.max(0.06, 1 - closure * 0.94);
    b.EyeL?.set(eyePitch, eyeYaw, 0, undefined, squash);
    b.EyeR?.set(eyePitch, eyeYaw, 0, undefined, squash);
    b.LidUpperL?.set(closure * 0.45, 0, 0);
    b.LidUpperR?.set(closure * 0.45, 0, 0);
    b.LidLowerL?.set(-closure * 0.2, 0, 0);
    b.LidLowerR?.set(-closure * 0.2, 0, 0);

    const lift = c.brow * 0.028 + energy * 0.005;
    const furrow = c.furrow;
    b.BrowInnerL?.set(
      0,
      0,
      furrow * 0.12,
      scratch.set(-furrow * 0.012, lift - furrow * 0.014, 0),
    );
    b.BrowInnerR?.set(
      0,
      0,
      -furrow * 0.12,
      scratch.set(furrow * 0.012, lift - furrow * 0.014, 0),
    );
    b.BrowOuterL?.set(0, 0, 0, scratch.set(0, lift * 0.7, 0));
    b.BrowOuterR?.set(0, 0, 0, scratch.set(0, lift * 0.7, 0));

    // Glow: purposeful modulation per state, never strobing.
    let pulse = 0;
    if (live) {
      if (face === "listening") pulse = 0.1 * Math.sin(t * 2.2);
      else if (face === "thinking")
        pulse = 0.14 * Math.sin(t * 1.3) * Math.sin(t * 0.41 + 1);
      else if (BUSY_STATES.has(face)) pulse = 0.05 * Math.sin(t * 1.6);
    }
    // Kept near 1.0–1.6 in linear light: brighter values tone-map toward
    // pink/white, which is exactly the washed-out look to avoid.
    const eye =
      1.35 *
      c.eye *
      (1 +
        pulse +
        energy * 0.3 +
        mic * 0.35 +
        (hovered ? 0.12 : 0) +
        poke * 0.35) *
      (1 - closure * 0.45);
    rig.glow.color.copy(ENERGY).lerp(c.hue, 0.3).multiplyScalar(eye);
    rig.armor.emissiveIntensity =
      // Seams only: kept low so emission never floods the metal.
      0.22 *
      c.lines *
      (1 + energy * 0.5 + (live ? 0.08 * Math.sin(t * 1.1) : 0));
    for (const halo of rig.halos) {
      halo.material.opacity = Math.min(0.4, eye / 4.2);
      halo.material.color.copy(ENERGY).lerp(c.hue, 0.3);
    }

    const s = signal.current;
    s.hue.copy(c.hue);
    s.spin = c.spin;
    s.energy = Math.max(energy, mic);
    s.busy += ((BUSY_STATES.has(face) ? 1 : 0) - s.busy) * k(3);
    s.eye = eye;
  });
  return (
    <primitive
      object={rig.root}
      onClick={(event: { stopPropagation: () => void }) => {
        event.stopPropagation();
        timeline.current.pokeRequested = true;
      }}
    />
  );
}

function arcs(
  radius: number,
  tube: number,
  segments: [number, number][],
  radial = 6,
): THREE.BufferGeometry {
  const parts = segments.map(([start, length]) => {
    const g = new THREE.TorusGeometry(
      radius,
      tube,
      radial,
      Math.max(8, Math.round(length * 24)),
      length,
    );
    g.rotateZ(start);
    return g;
  });
  const merged = mergeGeometries(parts, false)!;
  parts.forEach((part) => part.dispose());
  return merged;
}

/** Static chamber geometry, built once and shared by every dashboard canvas. */
function buildChamber() {
  // Halo: three black-chrome arc segments with machined ticks, merged.
  const gap = 0.32;
  const third = (Math.PI * 2) / 3;
  const halo = arcs(1.56, 0.032, [
    [Math.PI / 2 + gap / 2, third - gap],
    [Math.PI / 2 + third + gap / 2, third - gap],
    [Math.PI / 2 + 2 * third + gap / 2, third - gap],
  ]);
  const ticks: THREE.BufferGeometry[] = [];
  for (let i = 0; i < 36; i += 1) {
    const a = (i / 36) * Math.PI * 2;
    const tick = new THREE.BoxGeometry(0.018, i % 3 === 0 ? 0.11 : 0.05, 0.02);
    tick.translate(0, 1.66, 0);
    tick.rotateZ(a);
    ticks.push(tick);
  }
  const chrome = mergeGeometries([halo, ...ticks], false)!;
  halo.dispose();
  ticks.forEach((tick) => tick.dispose());
  // Energy channel inside the arcs (emissive, thin).
  const channel = arcs(
    1.5,
    0.006,
    [0, 1, 2].map((i) => [Math.PI / 2 + i * third + 0.5, third - 1.0]),
    4,
  );
  const outer = new THREE.TorusGeometry(1.82, 0.0035, 3, 160);
  // Emitter pedestal: machined lathe profile under the chin.
  const profile = [
    [0, -0.5],
    [1.05, -0.5],
    [1.12, -0.44],
    [1.1, -0.38],
    [0.86, -0.32],
    [0.74, -0.16],
    [0.78, -0.1],
    [0.6, -0.04],
    [0.42, 0],
    [0, 0],
  ].map(([x, y]) => new THREE.Vector2(x, y));
  const pedestal = new THREE.LatheGeometry(profile, 72);
  const emitter = new THREE.TorusGeometry(0.66, 0.012, 6, 96);
  emitter.rotateX(Math.PI / 2);
  emitter.translate(0, -0.06, 0);
  const lip = new THREE.TorusGeometry(1.08, 0.008, 4, 120);
  lip.rotateX(Math.PI / 2);
  lip.translate(0, -0.42, 0);
  const emitters = mergeGeometries([emitter, lip], false)!;
  emitter.dispose();
  lip.dispose();
  return { chrome, channel, outer, pedestal, emitters };
}

/**
 * The chamber the face lives in: a slowly turning halo of machined arcs
 * behind the head and an emitter pedestal below it. Six draw calls, no
 * transparency except the emissive lines.
 */
const Chamber = memo(function Chamber({
  signal,
  reduced,
}: {
  signal: RefObject<Signal>;
  reduced: boolean;
}) {
  const geometry = useMemo(buildChamber, []);
  const materials = useMemo(
    () => ({
      chrome: new THREE.MeshStandardMaterial({
        color: GUNMETAL,
        metalness: 1,
        roughness: 0.24,
      }),
      titanium: new THREE.MeshStandardMaterial({
        color: TITANIUM,
        metalness: 1,
        roughness: 0.42,
      }),
      channel: new THREE.MeshBasicMaterial({ color: ENERGY }),
      outer: new THREE.MeshBasicMaterial({
        color: ENERGY,
        transparent: true,
        opacity: 0.35,
        depthWrite: false,
      }),
      emitter: new THREE.MeshBasicMaterial({ color: ENERGY }),
    }),
    [],
  );
  useEffect(
    () => () => {
      Object.values(geometry).forEach((g) => g.dispose());
      Object.values(materials).forEach((m) => m.dispose());
    },
    [geometry, materials],
  );
  const halo = useRef<THREE.Group>(null);
  const outer = useRef<THREE.Mesh>(null);
  const spin = useRef(0);
  useFrame((_, delta) => {
    const s = signal.current;
    const dt = Math.min(delta, 0.1);
    if (!reduced) spin.current += dt * s.spin * 0.22;
    if (halo.current) halo.current.rotation.z = spin.current;
    if (outer.current) outer.current.rotation.z = -spin.current * 0.6;
    const level = 0.55 + s.busy * 0.35 + s.energy * 0.8;
    materials.channel.color.copy(ENERGY).lerp(s.hue, 0.5).multiplyScalar(level);
    materials.emitter.color
      .copy(ENERGY)
      .lerp(s.hue, 0.4)
      .multiplyScalar(0.8 + s.busy * 0.5 + s.energy * 1.2);
    materials.outer.color.copy(s.hue);
    materials.outer.opacity = 0.18 + s.busy * 0.14;
  });
  return (
    <group>
      <group position={[0, 0.06, -0.62]}>
        <group ref={halo}>
          <mesh geometry={geometry.chrome} material={materials.chrome} />
          <mesh geometry={geometry.channel} material={materials.channel} />
        </group>
        <mesh
          ref={outer}
          geometry={geometry.outer}
          material={materials.outer}
        />
      </group>
      <group position={[0, -1.12, -0.1]}>
        <mesh geometry={geometry.pedestal} material={materials.titanium} />
        <mesh geometry={geometry.emitters} material={materials.emitter} />
      </group>
    </group>
  );
});

/**
 * Dark studio for reflections: obsidian room, a dim neutral softbox above
 * and in front, crimson strips behind left and right. Baked once to PMREM.
 */
function Environment({ intensity }: { intensity: number }) {
  const { gl, scene } = useThree();
  useEffect(() => {
    const room = new THREE.Scene();
    const created: { dispose: () => void }[] = [];
    const panel = (
      w: number,
      h: number,
      color: THREE.Color,
      position: [number, number, number],
    ) => {
      const geometry = new THREE.PlaneGeometry(w, h);
      const material = new THREE.MeshBasicMaterial({
        color,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(...position);
      mesh.lookAt(0, 0, 0);
      room.add(mesh);
      created.push(geometry, material);
    };
    const box = new THREE.BoxGeometry(20, 20, 20);
    const walls = new THREE.MeshBasicMaterial({
      // Faint neutral walls give the metal a body instead of pure black.
      color: new THREE.Color(0.03, 0.03, 0.034),
      side: THREE.BackSide,
    });
    room.add(new THREE.Mesh(box, walls));
    created.push(box, walls);
    const white = new THREE.Color(0.9, 0.92, 0.97);
    panel(7, 3, white.clone().multiplyScalar(5), [0, 6, 1.5]);
    panel(4, 3.5, white.clone().multiplyScalar(2.6), [3, 2, 6]);
    panel(12, 3, white.clone().multiplyScalar(0.55), [0, 4.5, 6]);
    panel(3, 3, white.clone().multiplyScalar(0.6), [-4, 1, 5]);
    panel(1.4, 8, ENERGY.clone().multiplyScalar(2.3), [-6, 0.5, -3]);
    panel(1.4, 8, ENERGY.clone().multiplyScalar(1.5), [6, 0, -2.5]);
    panel(8, 3, ENERGY.clone().multiplyScalar(0.18), [0, -6, 0]);
    const generator = new THREE.PMREMGenerator(gl);
    const map = generator.fromScene(room, 0.04).texture;
    scene.environment = map;
    scene.environmentIntensity = intensity;
    generator.dispose();
    created.forEach((item) => item.dispose());
    return () => {
      scene.environment = null;
      map.dispose();
    };
  }, [gl, scene, intensity]);
  return null;
}

/** Crimson rim lights and an emitter fill that follow the state hue. */
function StateLights({
  signal,
  chamber,
}: {
  signal: RefObject<Signal>;
  chamber: boolean;
}) {
  const a = useRef<THREE.PointLight>(null);
  const b = useRef<THREE.PointLight>(null);
  const under = useRef<THREE.PointLight>(null);
  useFrame(() => {
    const s = signal.current;
    if (a.current) {
      a.current.color.copy(ENERGY).lerp(s.hue, 0.5);
      a.current.intensity = 4 + s.energy * 2.5 + s.busy * 2;
    }
    if (b.current) b.current.color.copy(ENERGY).lerp(s.hue, 0.5);
    if (under.current) {
      under.current.color.copy(ENERGY).lerp(s.hue, 0.4);
      under.current.intensity = 0.9 + s.busy * 0.8 + s.energy * 1.5;
    }
  });
  return (
    <>
      <pointLight ref={a} position={[-2.8, 1.2, -1.6]} intensity={4} />
      <pointLight ref={b} position={[2.8, 0.5, -1.4]} intensity={3} />
      {chamber && (
        <pointLight ref={under} position={[0, -1.15, 0.9]} intensity={1.6} />
      )}
    </>
  );
}

/**
 * Guards the bloom chain: a single NaN/Inf texel from specular aliasing on
 * the skinned metal would otherwise be blurred across the whole head.
 */
const SanitizeShader = {
  name: "SanitizeShader",
  uniforms: { tDiffuse: { value: null } },
  vertexShader: `varying vec2 vUv;
void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `uniform sampler2D tDiffuse;
varying vec2 vUv;
void main() {
  vec4 c = texture2D(tDiffuse, vUv);
  bvec4 bad = bvec4(isnan(c.r) || isinf(c.r), isnan(c.g) || isinf(c.g), isnan(c.b) || isinf(c.b), isnan(c.a) || isinf(c.a));
  if (any(bad)) c = vec4(0.0);
  gl_FragColor = vec4(min(c.rgb, vec3(16.0)), clamp(c.a, 0.0, 1.0));
}`,
};

/** High tier only: emissive-only bloom (threshold above lit-metal luminance). */
function Bloom() {
  const { gl, scene, camera, size } = useThree();
  const composer = useMemo(() => {
    const target = new THREE.WebGLRenderTarget(1, 1, {
      type: THREE.HalfFloatType,
      format: THREE.RGBAFormat,
      samples: 4,
    });
    const effect = new EffectComposer(gl, target);
    const render = new RenderPass(scene, camera);
    render.clearAlpha = 0;
    effect.addPass(render);
    effect.addPass(new ShaderPass(SanitizeShader));
    effect.addPass(
      new UnrealBloomPass(new THREE.Vector2(256, 256), 0.5, 0.35, 1.05),
    );
    effect.addPass(new OutputPass());
    return effect;
  }, [gl, scene, camera]);
  useEffect(() => {
    composer.setPixelRatio(Math.min(gl.getPixelRatio(), 1.25));
    composer.setSize(size.width, size.height);
  }, [composer, gl, size]);
  useEffect(() => () => composer.dispose(), [composer]);
  useFrame(() => composer.render(), 1);
  return null;
}

/**
 * Invalidation pacer for frameloop="demand": renders at the active rate while
 * something is happening (busy state, hover, recent cursor motion) and drops
 * to the idle rate otherwise. Stops entirely while hidden.
 */
function Pacer({
  active,
  idle,
  pointer,
  wake,
}: {
  active: number;
  idle: number;
  pointer: RefObject<Pointer>;
  wake: unknown;
}) {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    invalidate();
  }, [invalidate, wake]);
  useEffect(() => {
    if (active <= 0 && idle <= 0) return;
    let raf = 0;
    let timer = 0;
    let stopped = false;
    const tick = () => {
      if (stopped) return;
      const moving = performance.now() - pointer.current.moved < 1200;
      const fps = moving ? Math.max(active, idle) : idle;
      if (fps <= 0) return;
      invalidate();
      if (fps >= 58) {
        raf = requestAnimationFrame(tick);
        return;
      }
      timer = window.setTimeout(
        () => {
          raf = requestAnimationFrame(tick);
        },
        Math.max(0, 1000 / fps - 4),
      );
    };
    raf = requestAnimationFrame(tick);
    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      window.clearTimeout(timer);
    };
  }, [active, idle, invalidate, pointer]);
  return null;
}

/** Whole-frame renderer statistics (post-processing included). */
function Meter({
  onStats,
  started,
  passes,
  budget,
}: {
  onStats?: (stats: SceneStats) => void;
  started: number;
  passes: number;
  budget: number;
}) {
  const gl = useThree((state) => state.gl);
  useEffect(() => {
    gl.info.autoReset = false;
    return () => {
      gl.info.autoReset = true;
    };
  }, [gl]);
  const sample = useRef({
    frames: 0,
    time: 0,
    worst: 0,
    gaps: [] as number[],
    from: performance.now(),
    calls: 0,
    triangles: 0,
  });
  const loaded = useRef(0);
  const renderer = useRef("");
  useFrame((state, delta) => {
    const info = state.gl.info;
    const s = sample.current;
    // Totals of the previous frame, then start counting this one.
    s.calls = info.render.calls;
    s.triangles = info.render.triangles;
    info.reset();
    if (!loaded.current) loaded.current = performance.now() - started;
    if (!renderer.current) renderer.current = rendererName(state.gl);
    s.frames += 1;
    s.time += delta;
    s.worst = Math.max(s.worst, delta);
    s.gaps.push(delta * 1000);
    if (s.gaps.length > 180) s.gaps.shift();
    const now = performance.now();
    if (now - s.from >= 1000) {
      const ordered = [...s.gaps].sort((a, b) => a - b);
      const index = Math.min(
        ordered.length - 1,
        Math.max(0, Math.ceil(ordered.length * 0.95) - 1),
      );
      const p95 = ordered[index] ?? 0;
      const stats: SceneStats = {
        fps: Math.round((s.frames * 1000) / (now - s.from)),
        frameMs: Math.round((s.time / s.frames) * 10000) / 10,
        maxFrameMs: Math.round(s.worst * 10000) / 10,
        p95FrameMs: Math.round(p95 * 10) / 10,
        loadMs: Math.round(loaded.current),
        calls: s.calls,
        triangles: s.triangles,
        textures: info.memory.textures,
        geometries: info.memory.geometries,
        programs: info.programs?.length ?? 0,
        passes,
        budget,
        renderer: renderer.current,
      };
      onStats?.(stats);
      if (import.meta.env.DEV) {
        const w = window as unknown as {
          __immortilityScene?: Record<string, SceneStats>;
        };
        w.__immortilityScene = {
          ...w.__immortilityScene,
          [state.size.width < 300 ? "compact" : "stage"]: stats,
        };
      }
      sample.current = {
        ...s,
        frames: 0,
        time: 0,
        worst: 0,
        gaps: [],
        from: now,
      };
    }
  });
  return null;
}

class Boundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function launchPower(): { profile: PowerProfile; onBattery: boolean } {
  const raw = import.meta.env.VITE_IMMORTILITY_PROFILE;
  const profile: PowerProfile =
    raw === "auto" ||
    raw === "performance" ||
    raw === "balanced" ||
    raw === "battery"
      ? raw
      : "balanced";
  return {
    profile,
    onBattery: import.meta.env.VITE_IMMORTILITY_ON_BATTERY === "1",
  };
}

export interface HeadCanvasProps {
  face: FaceState;
  agent?: Role;
  level: RefObject<number>;
  quality: Quality;
  reduced: boolean;
  /** Companion / quick-chat face: no chamber, no post-processing, low idle rate. */
  compact?: boolean;
  onStats?: (stats: SceneStats) => void;
}

export default function HeadCanvas(props: HeadCanvasProps) {
  const { face, quality, reduced, compact = false } = props;
  const [hovered, setHovered] = useState(false);
  const [lost, setLost] = useState(false);
  const launch = useMemo(launchPower, []);
  const [dprCap, setDprCap] = useState(() =>
    pixelRatioCap({
      quality,
      compact,
      power: launch.profile,
      onBattery: launch.onBattery,
    }),
  );
  const started = useMemo(() => performance.now(), []);
  const host = useRef<HTMLDivElement>(null);
  const pointer = usePointer(host);
  const visible = useVisible(host);
  const signal = useRef<Signal>({
    hue: new THREE.Color(EXPRESSIONS.idle.hue),
    spin: 0.35,
    energy: 0,
    busy: 0,
    eye: 1,
  });
  const fallback = <FlatFace face={face} compact={compact} />;
  if (quality === "2d" || lost) return fallback;
  const busy = BUSY_STATES.has(face) || hovered;
  const budget = {
    quality,
    compact,
    reduced,
    visible,
    power: launch.profile,
    onBattery: launch.onBattery,
  };
  const activeFps = frameBudget({ ...budget, active: true });
  const idleFps = frameBudget({ ...budget, active: busy });
  const rendering = effectivePower(launch.profile, launch.onBattery);
  const bloom = !compact && quality === "high" && rendering !== "battery";
  const dprCeiling = Math.min(
    dprCap,
    pixelRatioCap({
      quality,
      compact,
      power: launch.profile,
      onBattery: launch.onBattery,
    }),
  );
  const dpr: [number, number] = [Math.min(1, dprCeiling), dprCeiling];
  const noteStats = (stats: SceneStats) => {
    props.onStats?.(stats);
    if (stats.budget < 45 || stats.fps < 1 || dprCeiling <= 1) return;
    if (stats.fps >= stats.budget * 0.75) return;
    setDprCap((current) =>
      Math.max(1, Math.round((current - 0.25) * 100) / 100),
    );
  };
  return (
    <Boundary fallback={fallback}>
      <div ref={host} className="head-host">
        <Canvas
          className="head-canvas"
          frameloop="demand"
          dpr={dpr}
          camera={
            compact
              ? { position: [0, 0.02, 5.1], fov: 30 }
              : { position: [0, -0.18, 5.7], fov: 30 }
          }
          gl={{
            antialias: !bloom && quality !== "performance",
            alpha: true,
            premultipliedAlpha: true,
            powerPreference: graphicsHint(launch.profile, launch.onBattery),
            toneMapping: THREE.NeutralToneMapping,
            toneMappingExposure: 0.92,
          }}
          onCreated={({ gl }) => {
            gl.setClearColor(0x000000, 0);
            gl.domElement.addEventListener("webglcontextlost", () =>
              setLost(true),
            );
          }}
          onPointerEnter={() => setHovered(true)}
          onPointerLeave={() => setHovered(false)}
        >
          <Pacer
            active={activeFps}
            idle={idleFps}
            pointer={pointer}
            wake={`${face}${props.agent ?? ""}${visible}`}
          />
          <Meter
            onStats={noteStats}
            started={started}
            passes={bloom ? 4 : 0}
            budget={idleFps}
          />
          <directionalLight
            position={[2.4, 4.2, 5]}
            intensity={2.6}
            color="#e9ebf2"
          />
          <StateLights signal={signal} chamber={!compact} />
          <Environment intensity={compact ? 0.9 : 1} />
          <Suspense fallback={null}>
            <Face
              face={face}
              agent={props.agent}
              level={props.level}
              reduced={reduced}
              hovered={hovered}
              follow={pointer}
              signal={signal}
              compact={compact}
            />
          </Suspense>
          {!compact && <Chamber signal={signal} reduced={reduced} />}
          {bloom && <Bloom />}
        </Canvas>
      </div>
    </Boundary>
  );
}
