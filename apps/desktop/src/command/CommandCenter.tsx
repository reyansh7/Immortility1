import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import type { Group, Mesh } from "three";

const plates: [number, number, number, number, number, number][] = [
  [0, 0.18, 0, 1.05, 0.92, 0.62],
  [-0.46, -0.02, 0.16, 0.24, 0.48, 0.36],
  [0.46, -0.02, 0.16, 0.24, 0.48, 0.36],
  [0, 0.58, 0.04, 0.78, 0.16, 0.48],
  [0, 0.08, 0.28, 0.34, 0.16, 0.12],
];

function RobotFace({
  active,
  speaking,
  reduced,
}: {
  active: boolean;
  speaking: boolean;
  reduced: boolean;
}) {
  const head = useRef<Group>(null);
  const jaw = useRef<Mesh>(null);
  const { invalidate } = useThree();
  useEffect(() => {
    invalidate();
    if (reduced || !active) return;
    const timer = window.setInterval(() => invalidate(), 120);
    return () => window.clearInterval(timer);
  }, [active, invalidate, reduced, speaking]);
  useFrame(({ clock }) => {
    if (!head.current || reduced) return;
    head.current.rotation.y = active
      ? Math.sin(clock.elapsedTime * 2) * 0.04
      : 0;
    if (jaw.current) {
      jaw.current.position.y = speaking
        ? -0.42 + Math.abs(Math.sin(clock.elapsedTime * 8)) * 0.05
        : -0.42;
    }
  });
  const glow = active ? 1.5 : 0.35;
  return (
    <group ref={head}>
      {plates.map((plate) => (
        <mesh key={plate.join()} position={[plate[0], plate[1], plate[2]]}>
          <boxGeometry args={[plate[3], plate[4], plate[5]]} />
          <meshStandardMaterial
            color="#1a1e22"
            metalness={0.88}
            roughness={0.28}
          />
        </mesh>
      ))}
      <mesh position={[-0.24, 0.16, 0.36]}>
        <boxGeometry args={[0.2, 0.06, 0.05]} />
        <meshStandardMaterial
          color="#8d1a1a"
          emissive="#ff2a2a"
          emissiveIntensity={glow}
        />
      </mesh>
      <mesh position={[0.24, 0.16, 0.36]}>
        <boxGeometry args={[0.2, 0.06, 0.05]} />
        <meshStandardMaterial
          color="#8d1a1a"
          emissive="#ff2a2a"
          emissiveIntensity={glow}
        />
      </mesh>
      <mesh ref={jaw} position={[0, -0.42, 0.22]}>
        <boxGeometry args={[0.42, 0.05, 0.06]} />
        <meshStandardMaterial
          color="#ff2a2a"
          emissive="#ff2a2a"
          emissiveIntensity={speaking ? 1.2 : 0.2}
          metalness={0.4}
          roughness={0.45}
        />
      </mesh>
    </group>
  );
}

export default function CommandCenter({
  active,
  speaking,
  reduced,
  flat,
  events,
}: {
  active: boolean;
  speaking: boolean;
  reduced: boolean;
  flat: boolean;
  events: string[];
}) {
  return (
    <section className="command-center" aria-label="Agent command center">
      {flat ? (
        <div className="robot-flat" aria-hidden="true">
          <span />
          <span />
        </div>
      ) : (
        <Canvas
          frameloop="demand"
          dpr={[1, 1.25]}
          camera={{ position: [0, 0, 3.2], fov: 35 }}
          gl={{ antialias: true, powerPreference: "high-performance" }}
        >
          <color attach="background" args={["#07080a"]} />
          <ambientLight intensity={0.22} />
          <directionalLight position={[2, 2.4, 3]} intensity={1.2} />
          <RobotFace active={active} speaking={speaking} reduced={reduced} />
        </Canvas>
      )}
      <ol>
        {events.length === 0 ? <li>No specialist is running.</li> : null}
        {events.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ol>
    </section>
  );
}
