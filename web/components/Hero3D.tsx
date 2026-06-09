"use client";

import { Float, Icosahedron } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";

/**
 * A subtle WebGL backdrop for the landing hero: a slowly floating, rotating
 * wireframe icosahedron in the brand colour. Purely decorative — pointer events
 * are disabled so it never interferes with the buttons above it.
 */
export default function Hero3D() {
  return (
    <Canvas
      className="!absolute inset-0 -z-10"
      style={{ pointerEvents: "none" }}
      camera={{ position: [0, 0, 4], fov: 50 }}
      dpr={[1, 2]}
    >
      <ambientLight intensity={0.5} />
      <directionalLight position={[3, 3, 4]} intensity={1.4} />
      <Float speed={1.6} rotationIntensity={1.3} floatIntensity={1.8}>
        <Icosahedron args={[1.4, 1]}>
          <meshStandardMaterial color="#10b981" wireframe transparent opacity={0.55} />
        </Icosahedron>
      </Float>
      <Float speed={2.2} rotationIntensity={1} floatIntensity={1.2} position={[2.2, -1.1, -1]}>
        <Icosahedron args={[0.5, 0]}>
          <meshStandardMaterial color="#34d399" wireframe transparent opacity={0.4} />
        </Icosahedron>
      </Float>
    </Canvas>
  );
}
