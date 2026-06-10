"use client";

import { useEffect, useMemo, useRef } from "react";
import { Float, MeshDistortMaterial, PointMaterial, Points } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import type { Group } from "three";

/** Normalized pointer (-1..1), tracked on window since the canvas ignores events. */
function useWindowPointer() {
  const pointer = useRef({ x: 0, y: 0 });
  useEffect(() => {
    const move = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => window.removeEventListener("pointermove", move);
  }, []);
  return pointer;
}

/** Deterministic PRNG so the particle field is stable across renders. */
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function ParticleField({ count = 900 }: { count?: number }) {
  const positions = useMemo(() => {
    const rand = mulberry32(42);
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      // Random points in a shell between r=3.2 and r=6 — a halo around the scene.
      const r = 3.2 + rand() * 2.8;
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, [count]);

  const ref = useRef<Group>(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.02;
  });

  return (
    <group ref={ref}>
      <Points positions={positions} stride={3} frustumCulled>
        <PointMaterial transparent color="#34d399" size={0.025} sizeAttenuation depthWrite={false} opacity={0.6} />
      </Points>
    </group>
  );
}

function Scene() {
  const group = useRef<Group>(null);
  const pointer = useWindowPointer();

  // Gentle pointer parallax on the whole composition.
  useFrame(() => {
    if (!group.current) return;
    const { x, y } = pointer.current;
    group.current.rotation.y += (x * 0.25 - group.current.rotation.y) * 0.04;
    group.current.rotation.x += (-y * 0.15 - group.current.rotation.x) * 0.04;
  });

  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[4, 5, 6]} intensity={1.6} />
      <pointLight position={[-6, -3, -4]} intensity={0.6} color="#34d399" />

      <group ref={group}>
        {/* Core: a slowly breathing, distorted sphere — the "sentinel". */}
        <Float speed={1.4} rotationIntensity={0.6} floatIntensity={1.1}>
          <mesh position={[1.9, 0.1, 0]}>
            <icosahedronGeometry args={[1.25, 24]} />
            <MeshDistortMaterial
              color="#10b981"
              roughness={0.25}
              metalness={0.35}
              distort={0.32}
              speed={1.6}
            />
          </mesh>
        </Float>

        {/* Orbiters: wireframe geometry circling the core. */}
        <Float speed={2} rotationIntensity={1.4} floatIntensity={1.6} position={[-2.4, 0.9, -1]}>
          <mesh>
            <torusKnotGeometry args={[0.55, 0.16, 110, 14]} />
            <meshStandardMaterial color="#a7f3d0" wireframe transparent opacity={0.5} />
          </mesh>
        </Float>
        <Float speed={1.7} rotationIntensity={1.1} floatIntensity={1.3} position={[-0.6, -1.4, -0.5]}>
          <mesh>
            <octahedronGeometry args={[0.5, 0]} />
            <meshStandardMaterial color="#6ee7b7" wireframe transparent opacity={0.55} />
          </mesh>
        </Float>
        <Float speed={2.4} rotationIntensity={1.6} floatIntensity={1.8} position={[3.4, 1.6, -1.6]}>
          <mesh>
            <icosahedronGeometry args={[0.34, 1]} />
            <meshStandardMaterial color="#34d399" wireframe transparent opacity={0.45} />
          </mesh>
        </Float>

        <ParticleField />
      </group>
    </>
  );
}

/**
 * The landing hero scene: a distorted emerald core, wireframe orbiters, and a
 * rotating particle halo, all with pointer parallax. Client-only (loaded via
 * next/dynamic with ssr:false) and wrapped in SafeBoundary by the caller, so a
 * machine without WebGL simply doesn't render it. Decorative: aria-hidden,
 * pointer events off.
 */
export default function Hero3D() {
  return (
    <div aria-hidden="true" className="absolute inset-0" style={{ pointerEvents: "none" }}>
      <Canvas camera={{ position: [0, 0, 5.2], fov: 50 }} dpr={[1, 1.8]}>
        <Scene />
      </Canvas>
    </div>
  );
}
