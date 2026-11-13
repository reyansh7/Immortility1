import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import {
  Component,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import {
  ROLES,
  playbackEnergy,
  type AgentStatus,
  type FaceState,
  type Role,
} from "./faceState";

export const HEAD_URL = "/models/immortility-head.glb";
export const HEAD_IMAGE = "/models/immortility-head-2d.png";
export type Quality = "high" | "balanced" | "performance" | "2d";

export interface SceneStats {
  fps: number;
  frameMs: number;
  maxFrameMs: number;
  loadMs: number;
  calls: number;
  triangles: number;
  renderer: string;
}

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

interface Pose {
  pitch: number;
  eye: number;
  core: number;
  crest: number;
  mouth: number;
  squint: number;
}
const poses: Record<FaceState, Pose> = {
  idle: { pitch: 0, eye: 2.2, core: 0.35, crest: 1.1, mouth: 0.12, squint: 1 },
  listening: {
    pitch: -0.05,
    eye: 3.2,
    core: 0.5,
    crest: 1.6,
    mouth: 0.2,
    squint: 1,
  },
  thinking: {
    pitch: 0.13,
    eye: 1.6,
    core: 0.7,
    crest: 2.2,
    mouth: 0.12,
    squint: 0.82,
  },
  planning: {
    pitch: 0.06,
    eye: 2.4,
    core: 0.8,
    crest: 2.4,
    mouth: 0.12,
    squint: 0.9,
  },
  delegating: {
    pitch: 0.03,
    eye: 2.8,
    core: 0.7,
    crest: 2,
    mouth: 0.12,
    squint: 0.9,
  },
  executing: {
    pitch: 0.06,
    eye: 3,
    core: 0.6,
    crest: 1.8,
    mouth: 0.12,
    squint: 0.6,
  },
  awaiting: {
    pitch: 0,
    eye: 2.6,
    core: 0.4,
    crest: 1.4,
    mouth: 0.12,
    squint: 1,
  },
  responding: {
    pitch: -0.02,
    eye: 2.6,
    core: 0.5,
    crest: 1.6,
    mouth: 0.4,
    squint: 1,
  },
  speaking: {
    pitch: -0.02,
    eye: 2.8,
    core: 0.5,
    crest: 1.6,
    mouth: 0.4,
    squint: 1,
  },
  error: {
    pitch: 0.1,
    eye: 0.9,
    core: 0.2,
    crest: 0.5,
    mouth: 0.08,
    squint: 0.8,
  },
  disconnected: {
    pitch: 0.15,
    eye: 0.15,
    core: 0.04,
    crest: 0.08,
    mouth: 0,
    squint: 0.7,
  },
};
const busy = new Set<FaceState>([
  "listening",
  "thinking",
  "planning",
  "delegating",
  "executing",
  "responding",
  "speaking",
]);

export const NODE_POSITIONS: Record<Role, [number, number, number]> = {
  research: [-2.9, 0.35, -0.4],
  coding: [2.9, 0.35, -0.4],
  review: [0, -1.5, 0.7],
};
const yawToward: Record<Role, [number, number]> = {
  research: [-0.32, 0.02],
  coding: [0.32, 0.02],
  review: [0, 0.2],
};

let brushed: THREE.DataTexture | null = null;
function brushedTexture(): THREE.DataTexture {
  if (brushed) return brushed;
  const size = 256;
  const data = new Uint8Array(size * size * 4);
  let seed = 7;
  const random = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let y = 0; y < size; y += 1) {
    const row = 205 + random() * 40;
    for (let x = 0; x < size; x += 1) {
      const value = Math.min(255, row + (random() - 0.5) * 18);
      const i = (y * size + x) * 4;
      data[i] = data[i + 1] = data[i + 2] = value;
      data[i + 3] = 255;
    }
  }
  brushed = new THREE.DataTexture(data, size, size);
  brushed.wrapS = brushed.wrapT = THREE.RepeatWrapping;
  brushed.repeat.set(5, 5);
  brushed.needsUpdate = true;
  return brushed;
}

let glow: THREE.CanvasTexture | null = null;
function glowTexture(): THREE.CanvasTexture {
  if (glow) return glow;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const context = canvas.getContext("2d")!;
  const gradient = context.createRadialGradient(64, 64, 0, 64, 64, 64);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.25, "rgba(255,255,255,0.45)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 128, 128);
  glow = new THREE.CanvasTexture(canvas);
  return glow;
}

interface Rig {
  root: THREE.Object3D;
  head: THREE.Object3D;
  jaw: THREE.Object3D;
  eyes: THREE.Mesh[];
  eyeMaterial: THREE.MeshStandardMaterial;
  coreMaterial: THREE.MeshStandardMaterial;
  crestMaterial: THREE.MeshStandardMaterial;
  mouthMaterial: THREE.MeshStandardMaterial;
  halos: THREE.Sprite[];
  dispose: () => void;
}

function prepare(source: THREE.Object3D): Rig {
  const root = source.clone(true);
  const texture = brushedTexture();
  const armor = new THREE.MeshPhysicalMaterial({
    color: "#262a32",
    metalness: 1,
    roughness: 0.34,
    roughnessMap: texture,
    clearcoat: 0.4,
    clearcoatRoughness: 0.28,
  });
  const titanium = new THREE.MeshPhysicalMaterial({
    color: "#8d939e",
    metalness: 1,
    roughness: 0.24,
    roughnessMap: texture,
    clearcoat: 0.2,
  });
  const inner = new THREE.MeshStandardMaterial({
    color: "#0b0c0f",
    metalness: 0.6,
    roughness: 0.55,
  });
  const glowMaterial = (intensity: number) =>
    new THREE.MeshStandardMaterial({
      color: "#2a0308",
      emissive: "#ff304a",
      emissiveIntensity: intensity,
      toneMapped: false,
    });
  const coreMaterial = new THREE.MeshStandardMaterial({
    color: "#0c0103",
    emissive: "#d21f35",
    emissiveIntensity: 0.35,
    roughness: 0.6,
  });
  const eyeMaterial = glowMaterial(2.2);
  const crestMaterial = glowMaterial(1.1);
  const mouthMaterial = glowMaterial(0.12);
  const created: THREE.Material[] = [
    armor,
    titanium,
    inner,
    coreMaterial,
    eyeMaterial,
    crestMaterial,
    mouthMaterial,
  ];
  const eyes: THREE.Mesh[] = [];
  root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;
    const named = (object.material as THREE.Material).name;
    const owner = object.name.startsWith("Eye")
      ? "Eye"
      : object.parent?.name.startsWith("Eye")
        ? "Eye"
        : object.name;
    if (owner === "Eye" || named === "Eye") {
      object.material = eyeMaterial;
      eyes.push(object);
    } else if (object.name.startsWith("CrestGlow"))
      object.material = crestMaterial;
    else if (object.name.startsWith("MouthGlow"))
      object.material = mouthMaterial;
    else if (named === "Armor") object.material = armor;
    else if (named === "Titanium") object.material = titanium;
    else if (named === "Inner") object.material = inner;
    else if (named === "Core") object.material = coreMaterial;
  });
  const head = root.getObjectByName("Head") ?? root;
  const jaw = root.getObjectByName("JawPivot") ?? new THREE.Object3D();
  const halos = eyes.map((eye) => {
    eye.geometry.computeBoundingBox();
    const center = new THREE.Vector3();
    eye.geometry.boundingBox!.getCenter(center);
    const halo = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: glowTexture(),
        color: "#ff304a",
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        transparent: true,
        opacity: 0.5,
      }),
    );
    created.push(halo.material);
    halo.position.copy(center).add(new THREE.Vector3(0, 0, 0.08));
    halo.scale.set(0.62, 0.3, 1);
    eye.add(halo);
    return halo;
  });
  return {
    root,
    head,
    jaw,
    eyes,
    eyeMaterial,
    coreMaterial,
    crestMaterial,
    mouthMaterial,
    halos,
    dispose: () => created.forEach((material) => material.dispose()),
  };
}

function Head({
  face,
  agent,
  level,
  reduced,
  hovered,
  follow,
}: {
  face: FaceState;
  agent?: Role;
  level: RefObject<number>;
  reduced: boolean;
  hovered: boolean;
  follow: boolean;
}) {
  const gltf = useLoader(GLTFLoader, HEAD_URL);
  const rig = useMemo(() => prepare(gltf.scene), [gltf]);
  useEffect(() => () => rig.dispose(), [rig]);
  const changed = useRef({ state: face, at: 0 });
  const motion = useRef({ yaw: 0, pitch: 0, jaw: 0, bob: 0 });
  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    const dt = Math.min(delta, 0.1);
    if (changed.current.state !== face)
      changed.current = { state: face, at: t };
    const since = t - changed.current.at;
    const pose = poses[face];
    const live = !reduced;
    let yaw = 0;
    let pitch = pose.pitch;
    let eyeL = pose.eye;
    let eyeR = pose.eye;
    let crest = pose.crest;
    let core = pose.core;
    let mouth = pose.mouth;
    if (live) {
      if (face === "idle")
        yaw = 0.06 * Math.sin(t * 0.23) + 0.03 * Math.sin(t * 0.61);
      if (face === "thinking") crest *= 1 + 0.35 * Math.sin(t * 2.2);
      if (face === "planning") {
        eyeL *= 1 + 0.3 * Math.sin(t * 5);
        eyeR *= 1 + 0.3 * Math.sin(t * 5 + Math.PI);
        yaw = 0.08 * Math.sin(t * 1.3) * Math.exp(-since * 0.4);
      }
      if (face === "executing") core *= 1 + 0.12 * Math.sin(t * 13);
      if (face === "responding") mouth *= 0.7 + 0.3 * Math.sin(t * 6);
      if (face === "error")
        eyeL = eyeR = pose.eye + 1.2 * Math.exp(-since * 1.5);
      const tracked = new Set<FaceState>([
        "idle",
        "listening",
        "responding",
        "speaking",
      ]);
      if (follow && tracked.has(face)) {
        yaw += state.pointer.x * 0.22;
        pitch -= state.pointer.y * 0.1;
      }
    }
    if (face === "delegating" && agent) {
      yaw = yawToward[agent][0];
      pitch = yawToward[agent][1];
    }
    const hover = hovered ? 1.15 : 1;
    // Playback RMS for speech sits around 0.05-0.25; scale it into the jaw's range.
    const speech = playbackEnergy(level.current ?? 0, face === "speaking");
    if (face === "speaking") mouth = 0.3 + speech * 2.6;
    const m = motion.current;
    m.yaw = THREE.MathUtils.damp(m.yaw, yaw, 4, dt);
    m.pitch = THREE.MathUtils.damp(m.pitch, pitch, 4, dt);
    m.jaw = THREE.MathUtils.damp(m.jaw, speech * 0.3, 18, dt);
    m.bob = live ? 0.035 * Math.sin(t * 0.9) : 0;
    rig.head.rotation.y = m.yaw;
    rig.head.rotation.x = m.pitch;
    rig.jaw.rotation.x = m.jaw;
    rig.root.position.y = 0.25 + m.bob;
    const damp = (from: number, to: number) =>
      THREE.MathUtils.damp(from, to, 6, dt);
    rig.eyeMaterial.emissiveIntensity = damp(
      rig.eyeMaterial.emissiveIntensity,
      ((eyeL + eyeR) / 2) * hover,
    );
    rig.halos.forEach((halo, index) => {
      const value = (index === 0 ? eyeL : eyeR) * hover;
      halo.material.opacity = damp(
        halo.material.opacity,
        Math.min(0.85, value / 4),
      );
    });
    rig.eyes.forEach((eye) => {
      eye.scale.y = damp(eye.scale.y, pose.squint);
    });
    rig.crestMaterial.emissiveIntensity = damp(
      rig.crestMaterial.emissiveIntensity,
      crest,
    );
    rig.coreMaterial.emissiveIntensity = damp(
      rig.coreMaterial.emissiveIntensity,
      core,
    );
    rig.mouthMaterial.emissiveIntensity = THREE.MathUtils.damp(
      rig.mouthMaterial.emissiveIntensity,
      mouth,
      14,
      dt,
    );
  });
  return <primitive object={rig.root} />;
}

function label(text: string): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 96;
  const context = canvas.getContext("2d")!;
  context.font = "600 34px 'Segoe UI', Inter, sans-serif";
  context.textAlign = "center";
  context.fillStyle = "#e8e9ed";
  context.fillText(text.toUpperCase(), 256, 44);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function AgentNode({
  agent,
  selected,
  onSelect,
}: {
  agent: AgentStatus;
  selected: boolean;
  onSelect: (role: Role) => void;
}) {
  const ring = useRef<THREE.Mesh>(null);
  const pulse = useRef<THREE.Mesh>(null);
  const position = NODE_POSITIONS[agent.role];
  const curve = useMemo(() => {
    const end = new THREE.Vector3(...position);
    const start = new THREE.Vector3(0, 0.25, 0.25);
    const middle = start
      .clone()
      .lerp(end, 0.5)
      .add(new THREE.Vector3(0, 0.45, 0.4));
    return new THREE.QuadraticBezierCurve3(start, middle, end);
  }, [position]);
  const tube = useMemo(
    () => new THREE.TubeGeometry(curve, 48, 0.009, 6),
    [curve],
  );
  useEffect(() => () => tube.dispose(), [tube]);
  const text = useMemo(
    () =>
      label(
        `${agent.role} · ${agent.status === "started" ? "running" : agent.status}`,
      ),
    [agent.role, agent.status],
  );
  useEffect(() => () => text.dispose(), [text]);
  const running = agent.status === "started";
  const emissive = {
    off: 0,
    available: 0.25,
    started: 2.4,
    succeeded: 0.8,
    failed: 0.4,
  }[agent.status];
  const opacity = {
    off: 0.06,
    available: 0.18,
    started: 0.75,
    succeeded: 0.35,
    failed: 0.25,
  }[agent.status];
  useFrame((state, delta) => {
    if (ring.current && running) ring.current.rotation.z += delta * 1.4;
    if (pulse.current) {
      pulse.current.visible = running;
      if (running)
        pulse.current.position.copy(
          curve.getPoint((state.clock.elapsedTime * 0.55) % 1),
        );
    }
  });
  return (
    <group>
      <mesh geometry={tube}>
        <meshBasicMaterial
          color="#d21f35"
          transparent
          opacity={opacity}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
      <mesh ref={pulse} visible={false}>
        <sphereGeometry args={[0.045, 12, 8]} />
        <meshBasicMaterial color="#ff304a" toneMapped={false} />
      </mesh>
      <group
        position={position}
        scale={selected ? 1.18 : 1}
        onClick={(event) => {
          event.stopPropagation();
          onSelect(agent.role);
        }}
        onPointerOver={() => (document.body.style.cursor = "pointer")}
        onPointerOut={() => (document.body.style.cursor = "")}
      >
        <mesh>
          <icosahedronGeometry args={[0.22, 1]} />
          <meshPhysicalMaterial
            color={agent.status === "off" ? "#30343c" : "#8d939e"}
            metalness={1}
            roughness={0.3}
            clearcoat={0.3}
            flatShading
          />
        </mesh>
        <mesh>
          <sphereGeometry args={[0.1, 16, 12]} />
          <meshStandardMaterial
            color="#1a0205"
            emissive={agent.status === "failed" ? "#7a2a2a" : "#ff304a"}
            emissiveIntensity={emissive}
            toneMapped={false}
          />
        </mesh>
        <mesh ref={ring} rotation={[Math.PI / 2.4, 0, 0]}>
          <torusGeometry args={[0.36, 0.016, 8, 48]} />
          <meshStandardMaterial
            color="#252931"
            metalness={1}
            roughness={0.3}
            emissive="#d21f35"
            emissiveIntensity={selected ? 1.2 : emissive * 0.4}
          />
        </mesh>
        <sprite
          position={agent.role === "review" ? [1.15, 0, 0] : [0, -0.55, 0]}
          scale={[1.5, 0.28, 1]}
        >
          <spriteMaterial
            map={text}
            transparent
            depthWrite={false}
            opacity={agent.status === "off" ? 0.45 : 0.95}
          />
        </sprite>
      </group>
    </group>
  );
}

function Environment() {
  const { gl, scene } = useThree();
  useEffect(() => {
    const generator = new THREE.PMREMGenerator(gl);
    const room = new RoomEnvironment();
    const map = generator.fromScene(room, 0.04).texture;
    scene.environment = map;
    scene.environmentIntensity = 0.55;
    return () => {
      scene.environment = null;
      map.dispose();
      generator.dispose();
      room.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          (object.material as THREE.Material).dispose();
        }
      });
    };
  }, [gl, scene]);
  return null;
}

function Pacer({ fps }: { fps: number }) {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    invalidate();
    if (fps <= 0) return;
    let frame = 0;
    let last = 0;
    const interval = 1000 / fps;
    const loop = (time: number) => {
      frame = requestAnimationFrame(loop);
      if (document.hidden) return;
      // At a 60 fps cap every display frame renders; gating it only adds jitter-driven drops.
      if (fps >= 58 || time - last >= interval - 4) {
        last = time;
        invalidate();
      }
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [fps, invalidate]);
  return null;
}

function Meter({
  onStats,
  started,
}: {
  onStats?: (stats: SceneStats) => void;
  started: number;
}) {
  const sample = useRef({
    frames: 0,
    time: 0,
    worst: 0,
    from: performance.now(),
  });
  const loaded = useRef(0);
  const renderer = useRef("");
  useFrame((state, delta) => {
    if (!loaded.current) loaded.current = performance.now() - started;
    if (!renderer.current) renderer.current = rendererName(state.gl);
    const s = sample.current;
    s.frames += 1;
    s.time += delta;
    s.worst = Math.max(s.worst, delta);
    const now = performance.now();
    if (now - s.from >= 1000 && onStats) {
      onStats({
        fps: Math.round((s.frames * 1000) / (now - s.from)),
        frameMs: Math.round((s.time / s.frames) * 10000) / 10,
        maxFrameMs: Math.round(s.worst * 10000) / 10,
        loadMs: Math.round(loaded.current),
        calls: state.gl.info.render.calls,
        triangles: state.gl.info.render.triangles,
        renderer: renderer.current,
      });
      sample.current = { frames: 0, time: 0, worst: 0, from: now };
    }
  });
  return null;
}

function Controls({ reset }: { reset?: RefObject<(() => void) | null> }) {
  const { camera, gl, invalidate } = useThree();
  const controls = useMemo(
    () => new OrbitControls(camera, gl.domElement),
    [camera, gl],
  );
  useEffect(() => {
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 4.5;
    controls.maxDistance = 10;
    controls.minAzimuthAngle = -0.7;
    controls.maxAzimuthAngle = 0.7;
    controls.minPolarAngle = Math.PI / 2 - 0.45;
    controls.maxPolarAngle = Math.PI / 2 + 0.3;
    controls.panSpeed = 0.5;
    controls.saveState();
    const low = new THREE.Vector3(-2, -1.5, -1);
    const high = new THREE.Vector3(2, 1.5, 1);
    const change = () => {
      controls.target.clamp(low, high);
      invalidate();
    };
    controls.addEventListener("change", change);
    if (reset) reset.current = () => controls.reset();
    return () => {
      controls.removeEventListener("change", change);
      controls.dispose();
    };
  }, [controls, invalidate, reset]);
  useFrame(() => controls.update());
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
      <img src={HEAD_IMAGE} alt="" draggable={false} />
    </div>
  );
}

export interface HeadCanvasProps {
  face: FaceState;
  agent?: Role;
  level: RefObject<number>;
  quality: Quality;
  reduced: boolean;
  compact?: boolean;
  agents?: Record<Role, AgentStatus>;
  selected?: Role | null;
  onSelect?: (role: Role) => void;
  onStats?: (stats: SceneStats) => void;
  reset?: RefObject<(() => void) | null>;
}

export default function HeadCanvas(props: HeadCanvasProps) {
  const { face, quality, reduced, compact } = props;
  const [hovered, setHovered] = useState(false);
  const [lost, setLost] = useState(false);
  const started = useMemo(() => performance.now(), []);
  const fallback = <FlatFace face={face} compact={compact} />;
  if (quality === "2d" || lost) return fallback;
  const active = busy.has(face) || hovered;
  const fps = reduced
    ? 0
    : compact
      ? active
        ? 30
        : 12
      : {
          high: active ? 60 : 30,
          balanced: active ? 45 : 20,
          performance: active ? 30 : 10,
        }[quality];
  const dpr: [number, number] =
    quality === "high" ? [1, 2] : quality === "balanced" ? [1, 1.5] : [1, 1];
  return (
    <Boundary fallback={fallback}>
      <Canvas
        className="head-canvas"
        frameloop="demand"
        dpr={compact ? [1, 1.5] : dpr}
        camera={
          compact
            ? { position: [0, 0.1, 5.4], fov: 30 }
            : { position: [0, 0.1, 6.9], fov: 35 }
        }
        gl={{
          antialias: quality !== "performance",
          alpha: true,
          powerPreference: compact ? "low-power" : "high-performance",
        }}
        onCreated={({ gl }) => {
          gl.domElement.addEventListener("webglcontextlost", () =>
            setLost(true),
          );
        }}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <Pacer fps={fps} />
        <Meter onStats={props.onStats} started={started} />
        <ambientLight intensity={0.12} />
        <directionalLight
          position={[3, 4, 5]}
          intensity={2.3}
          color="#dfe6f0"
        />
        <directionalLight
          position={[-4, 2, 3]}
          intensity={0.35}
          color="#9ca3af"
        />
        <pointLight position={[-3, 1.4, -2.4]} intensity={22} color="#d21f35" />
        <pointLight position={[3.2, -1, -2]} intensity={8} color="#ff304a" />
        {quality !== "performance" && <Environment />}
        <Suspense fallback={null}>
          <Head
            face={face}
            agent={props.agent}
            level={props.level}
            reduced={reduced}
            hovered={hovered}
            follow={!compact || hovered}
          />
        </Suspense>
        {!compact &&
          props.agents &&
          ROLES.map((role) => (
            <AgentNode
              key={role}
              agent={props.agents![role]}
              selected={props.selected === role}
              onSelect={props.onSelect ?? (() => {})}
            />
          ))}
        {!compact && <Controls reset={props.reset} />}
      </Canvas>
    </Boundary>
  );
}
