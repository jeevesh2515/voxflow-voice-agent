"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

type SceneObject = {
  object: THREE.Object3D;
  material?: THREE.Material | THREE.Material[];
  baseScale?: THREE.Vector3;
  basePosition?: THREE.Vector3;
};

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const smoothstep = (from: number, to: number, value: number) => {
  const progress = clamp((value - from) / (to - from));
  return progress * progress * (3 - 2 * progress);
};

const cyan = 0x00ffcc;
const magenta = 0xff2d78;
const lime = 0xc6ff00;

function materialFor(color: number, opacity = 1) {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    wireframe: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
}

function buildSpeaker(color: number): THREE.Group {
  const speaker = new THREE.Group();
  const shellMaterial = materialFor(color, 0.5);
  const coneMaterial = materialFor(color, 0.8);
  const shell = new THREE.Mesh(new THREE.BoxGeometry(0.85, 1.2, 0.38), shellMaterial);
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.12, 0.08, 24), coneMaterial);
  cone.rotation.x = Math.PI / 2;
  cone.position.z = 0.22;
  speaker.add(shell, cone);
  return speaker;
}

function buildWarehouse(): THREE.Group {
  const warehouse = new THREE.Group();
  const material = materialFor(cyan, 0.3);
  const base = new THREE.Mesh(new THREE.BoxGeometry(5.8, 1.7, 2.7), material);
  base.position.y = 0.85;
  warehouse.add(base);

  for (let index = 0; index < 5; index += 1) {
    const bay = new THREE.Mesh(new THREE.BoxGeometry(0.72, 1.05, 0.05), material);
    bay.position.set(-1.9 + index * 0.95, 0.78, 1.38);
    warehouse.add(bay);
  }

  for (let index = 0; index < 6; index += 1) {
    const mast = new THREE.Mesh(new THREE.BoxGeometry(0.04, 2.3, 0.04), material);
    mast.position.set(-2.6 + index * 1.04, 1.9, -1.2);
    warehouse.add(mast);
  }

  return warehouse;
}

function buildRouteLines(nodes: THREE.Vector3[], color: number) {
  const geometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0), nodes[0],
    new THREE.Vector3(0, 0, 0), nodes[1],
    new THREE.Vector3(0, 0, 0), nodes[2],
    new THREE.Vector3(0, 0, 0), nodes[3],
    nodes[0], nodes[1],
    nodes[1], nodes[2],
    nodes[2], nodes[3],
  ]);
  return new THREE.LineSegments(
    geometry,
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.38, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
}

/** Realtime WebGL voice-acoustic lidar: a procedural scene with no external assets. */
export default function VoiceCoreCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const stage = document.getElementById("hero-stage");
    if (!canvas || !stage) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 0.2, 12);

    const world = new THREE.Group();
    scene.add(world);

    const coreMaterial = materialFor(magenta, 0.86);
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(2, 4), coreMaterial);
    world.add(core);

    const innerCore = new THREE.Mesh(new THREE.IcosahedronGeometry(1.38, 3), materialFor(cyan, 0.28));
    world.add(innerCore);

    const waveMaterials: THREE.MeshBasicMaterial[] = [];
    for (let index = 0; index < 4; index += 1) {
      const ringMaterial = new THREE.MeshBasicMaterial({
        color: index % 2 === 0 ? cyan : magenta,
        transparent: true,
        opacity: 0.42,
        wireframe: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const ring = new THREE.Mesh(new THREE.TorusGeometry(2.2 + index * 0.28, 0.012 + index * 0.006, 8, 80), ringMaterial);
      ring.rotation.set(index * 0.55, index * 0.72, index * 0.4);
      world.add(ring);
      waveMaterials.push(ringMaterial);
    }

    const particleCount = window.innerWidth < 700 ? 480 : 900;
    const particlePositions = new Float32Array(particleCount * 3);
    const particlePhases = new Float32Array(particleCount);
    for (let index = 0; index < particleCount; index += 1) {
      const radius = 3.6 + Math.random() * 5.5;
      const theta = Math.random() * Math.PI * 2;
      const y = (Math.random() - 0.5) * 5.6;
      particlePositions[index * 3] = Math.cos(theta) * radius;
      particlePositions[index * 3 + 1] = y;
      particlePositions[index * 3 + 2] = Math.sin(theta) * radius;
      particlePhases[index] = Math.random() * Math.PI * 2;
    }
    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particleMaterial = new THREE.PointsMaterial({
      color: cyan,
      size: 0.028,
      transparent: true,
      opacity: 0.68,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });
    const particles = new THREE.Points(particleGeometry, particleMaterial);
    world.add(particles);

    const routeNodes = [
      new THREE.Vector3(-0.5, 2.2, 0.5),
      new THREE.Vector3(1.2, -2.4, 0),
      new THREE.Vector3(3.2, 1.8, -0.8),
      new THREE.Vector3(4.8, -1.2, 0.2),
    ];
    const routes = buildRouteLines(routeNodes, cyan);
    routes.scale.setScalar(0.35);
    routes.position.y = 0.1;
    world.add(routes);

    const nodeObjects: SceneObject[] = routeNodes.map((position, index) => {
      const node = new THREE.Mesh(new THREE.IcosahedronGeometry(0.18, 1), materialFor(index % 2 === 0 ? lime : cyan, 0.9));
      node.position.copy(position);
      world.add(node);
      return { object: node, material: node.material, basePosition: position.clone() };
    });

    const speakerGroup = new THREE.Group();
    const speakerPositions = [
      new THREE.Vector3(0.8, -2.4, 0.5),
      new THREE.Vector3(3.9, -2.2, 0.8),
      new THREE.Vector3(4.4, 2.2, -0.2),
    ];
    speakerPositions.forEach((position, index) => {
      const speaker = buildSpeaker(index === 1 ? magenta : cyan);
      speaker.position.copy(position);
      speaker.rotation.y = index * 0.7;
      speakerGroup.add(speaker);
    });
    world.add(speakerGroup);

    const warehouse = buildWarehouse();
    warehouse.position.set(0, -3.3, -1.4);
    warehouse.scale.setScalar(0.2);
    world.add(warehouse);

    const ground = new THREE.GridHelper(18, 18, cyan, cyan);
    ground.position.set(0, -3.2, -0.8);
    ground.material.transparent = true;
    ground.material.opacity = 0.12;
    world.add(ground);

    const sceneObjects: SceneObject[] = [
      { object: core, material: coreMaterial, baseScale: new THREE.Vector3(1, 1, 1) },
      { object: innerCore, material: innerCore.material, baseScale: new THREE.Vector3(1, 1, 1) },
      { object: routes, material: routes.material, baseScale: new THREE.Vector3(1, 1, 1) },
      { object: speakerGroup, baseScale: new THREE.Vector3(1, 1, 1) },
      { object: warehouse, baseScale: new THREE.Vector3(1, 1, 1) },
      { object: ground, material: ground.material as THREE.Material, baseScale: new THREE.Vector3(1, 1, 1) },
    ];

    let width = 1;
    let height = 1;
    let raf = 0;
    let visible = true;
    let pointerX = 0;
    let pointerY = 0;
    let targetPointerX = 0;
    let targetPointerY = 0;
    let pageVisible = !document.hidden;
    let voicePulse = 0;

    const onVoicePlay = () => {
      voicePulse = Math.min(1, voicePulse + 0.85);
    };

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      width = Math.max(bounds.width, 1);
      height = Math.max(bounds.height, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };

    const scrollProgress = () => {
      const bounds = stage.getBoundingClientRect();
      return clamp(-bounds.top / Math.max(bounds.height - window.innerHeight, 1));
    };

    const paint = (time: number) => {
      const progress = scrollProgress();
      const morph = smoothstep(0.12, 0.82, progress);
      const wave = Math.sin(time * 0.0022);
      voicePulse *= 0.965;
      pointerX += (targetPointerX - pointerX) * 0.04;
      pointerY += (targetPointerY - pointerY) * 0.04;

      const isDesktop = width > 1024;
      const baseZoom = 1 + morph * 0.52;
      world.rotation.y = time * 0.0001 + progress * 0.9 + pointerX * 0.07;
      world.rotation.x = pointerY * 0.045;
      world.position.x = isDesktop ? 2.6 * (1 - morph * 0.4) : 0;
      world.position.y = morph * 0.45;
      world.scale.setScalar(baseZoom);
      camera.position.x = pointerX * 0.45;
      camera.position.y = 0.2 - pointerY * 0.38;
      camera.position.z = isDesktop ? 13 - morph * 2.25 : 14.5 - morph * 2.25;
      camera.lookAt(isDesktop ? 2.2 * (1 - morph * 0.5) : 0, 0, 0);

      core.rotation.x = time * 0.00021;
      core.rotation.z = time * 0.00013;
      innerCore.rotation.y = -time * 0.00033;
      core.scale.setScalar(1 + wave * 0.018 + (1 - morph) * 0.08 + voicePulse * 0.1);
      innerCore.scale.setScalar(1 + (1 - morph) * 0.1);
      waveMaterials.forEach((material, index) => {
        material.opacity = 0.18 + (1 - morph) * 0.2 + Math.abs(Math.sin(time * 0.0018 + index)) * 0.12 + voicePulse * 0.24;
      });
      (particleGeometry.attributes.position as THREE.BufferAttribute).needsUpdate = false;
      particleMaterial.opacity = 0.44 + morph * 0.24;
      particles.rotation.y = -time * 0.00004;
      particles.rotation.z = morph * 0.25;

      sceneObjects.forEach(({ object, material }) => {
        const isInfrastructure = object === routes || object === warehouse || object === ground || object === speakerGroup;
        const targetOpacity = isInfrastructure ? 0.15 + morph * 0.85 : 1;
        if (material) {
          if (Array.isArray(material)) material.forEach((item) => { item.opacity = targetOpacity; });
          else material.opacity = targetOpacity * (object === innerCore ? 0.38 : 1);
        }
      });

      nodeObjects.forEach(({ object, material, basePosition }, index) => {
        const pulse = 1 + Math.sin(time * 0.003 + index) * 0.22;
        object.scale.setScalar((0.35 + morph * 0.9) * pulse);
        object.position.lerp(basePosition!.clone().multiplyScalar(0.72 + morph * 0.28), 0.08);
        (material as THREE.Material).opacity = 0.22 + morph * 0.78;
      });
      warehouse.scale.setScalar(0.2 + morph * 0.8);
      speakerGroup.scale.setScalar(0.66 + morph * 0.34);
      ground.material.opacity = 0.04 + morph * 0.15;
      routes.scale.setScalar(0.35 + morph * 0.65);

      renderer.render(scene, camera);
      if (!reducedMotion && visible && pageVisible) raf = window.requestAnimationFrame(paint);
    };

    const pointerMove = (event: PointerEvent) => {
      targetPointerX = (event.clientX / Math.max(window.innerWidth, 1) - 0.5) * 2;
      targetPointerY = (event.clientY / Math.max(window.innerHeight, 1) - 0.5) * 2;
    };

    const onVisibilityChange = () => {
      pageVisible = !document.hidden;
      if (!pageVisible) window.cancelAnimationFrame(raf);
      else if (!reducedMotion) raf = window.requestAnimationFrame(paint);
      else paint(performance.now());
    };

    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (!reducedMotion && visible && pageVisible && !raf) raf = window.requestAnimationFrame(paint);
      if (!visible) window.cancelAnimationFrame(raf);
    }, { threshold: 0 });

    resize();
    paint(performance.now());
    window.addEventListener("voxflow:voice-play", onVoicePlay);

    observer.observe(stage);
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", pointerMove, { passive: true });
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", pointerMove);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("voxflow:voice-play", onVoicePlay);
      particleGeometry.dispose();
      particleMaterial.dispose();
      renderer.dispose();
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" className="absolute inset-0 h-full w-full pointer-events-none" />;
}
