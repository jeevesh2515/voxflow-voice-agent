"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const smoothstep = (from: number, to: number, value: number) => {
  const progress = clamp((value - from) / (to - from));
  return progress * progress * (3 - 2 * progress);
};
const easeInOutQuart = (t: number) => (t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2);

// VoxFlow signal palette: dominant cyan, restrained magenta secondary
const cyan = 0x5eead4;
const magenta = 0xff2d78;
const cyanDim = 0x2dd4bf;

function wireMaterialFor(color: number, opacity = 1) {
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
  const shell = new THREE.Mesh(new THREE.BoxGeometry(0.85, 1.2, 0.38), wireMaterialFor(color, 0.5));
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.12, 0.08, 24), wireMaterialFor(color, 0.8));
  cone.rotation.x = Math.PI / 2;
  cone.position.z = 0.22;
  speaker.add(shell, cone);
  return speaker;
}

function buildWarehouse(): { group: THREE.Group; material: THREE.Material } {
  const warehouse = new THREE.Group();
  const material = wireMaterialFor(cyan, 0.32);
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

  return { group: warehouse, material };
}

function buildRouteLines(nodes: THREE.Vector3[], color: number) {
  const geometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0),
    nodes[0],
    new THREE.Vector3(0, 0, 0),
    nodes[1],
    new THREE.Vector3(0, 0, 0),
    nodes[2],
    new THREE.Vector3(0, 0, 0),
    nodes[3],
    nodes[0],
    nodes[1],
    nodes[1],
    nodes[2],
    nodes[2],
    nodes[3],
  ]);
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.38,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  return { lines: new THREE.LineSegments(geometry, material), material };
}

/**
 * Three-stage cinematic hero — freight voice OS.
 *  A (0.00–0.15): centered solid metallic Voice Core.
 *  B (0.15–0.55): quartic camera orbit + zoom, solid dissolves into cyan wireframe blueprint, acoustic rings expand.
 *  C (0.55–1.00): blueprint shifts right, signal routes beam into warehouse grid, blueprint vanishes.
 * Audio-reactive pulse on voxflow:voice-play. Reduced-motion safe, GPU-cleanup, no scroll hijack.
 */
export default function VoiceCoreCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const stage = document.getElementById("hero-stage");
    if (!canvas || !stage) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: !reducedMotion, powerPreference: "high-performance" });
    } catch {
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, reducedMotion ? 1 : 1.5));
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);

    // Stage A lighting: metallic shading + glowing core emission + horizon fill
    scene.add(new THREE.AmbientLight(0x3a4260, 1.4));
    const keyLight = new THREE.DirectionalLight(cyan, 2.2);
    keyLight.position.set(5, 5, 7);
    const rimLight = new THREE.DirectionalLight(magenta, 1.6);
    rimLight.position.set(-6, -3, 5);
    const horizonLight = new THREE.DirectionalLight(0x9cb8ff, 1.2);
    horizonLight.position.set(0, 6, 8);
    scene.add(keyLight, rimLight, horizonLight);

    // Blueprint group: solid core + wireframe twin + point cloud + acoustic rings
    const blueprint = new THREE.Group();
    scene.add(blueprint);

    const coreGeometry = new THREE.IcosahedronGeometry(2, 3);
    const ringGeometryA = new THREE.TorusGeometry(2.35, 0.014, 8, 90);
    const ringGeometryB = new THREE.TorusGeometry(2.35, 0.019, 8, 90);
    const ringGeometryC = new THREE.TorusGeometry(2.35, 0.024, 8, 90);
    const solidMaterial = new THREE.MeshStandardMaterial({
      color: 0x1e273d,
      metalness: 0.82,
      roughness: 0.28,
      emissive: 0x0c1220,
      emissiveIntensity: 0.35,
      flatShading: true,
      transparent: true,
      opacity: 1,
    });
    const solidCore = new THREE.Mesh(coreGeometry, solidMaterial);
    blueprint.add(solidCore);

    const wireBlueprintMaterial = wireMaterialFor(cyan, 0);
    const wireBlueprint = new THREE.Mesh(coreGeometry, wireBlueprintMaterial);
    wireBlueprint.scale.setScalar(1.002);
    blueprint.add(wireBlueprint);

    const cloudMaterial = new THREE.PointsMaterial({
      color: magenta,
      size: 0.045,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });
    const pointCloud = new THREE.Points(coreGeometry, cloudMaterial);
    pointCloud.scale.setScalar(1.002);
    blueprint.add(pointCloud);

    const emissionCore = new THREE.Mesh(new THREE.IcosahedronGeometry(0.9, 3), wireMaterialFor(cyanDim, 0.55));
    blueprint.add(emissionCore);

    // Concentric acoustic wave rings, expanding outward with scroll depth.
    const ringGeometries = [ringGeometryA, ringGeometryB, ringGeometryC];
    const rings: { mesh: THREE.Mesh; material: THREE.MeshBasicMaterial; baseRotation: THREE.Euler }[] = [];
    for (let index = 0; index < 3; index += 1) {
      const ringMaterial = new THREE.MeshBasicMaterial({
        color: index === 1 ? magenta : cyan,
        transparent: true,
        opacity: 0,
        wireframe: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const ring = new THREE.Mesh(ringGeometries[index], ringMaterial);
      const baseRotation = new THREE.Euler(Math.PI / 2 + index * 0.16, index * 0.24, index * 0.4);
      ring.rotation.copy(baseRotation);
      blueprint.add(ring);
      rings.push({ mesh: ring, material: ringMaterial, baseRotation });
    }

    // Infra group: UK dispatch routes + warehouse grid, revealed in stage C
    const infra = new THREE.Group();
    scene.add(infra);
    const infraMaterials: { material: THREE.Material; base: number }[] = [];
    const trackInfra = (material: THREE.Material, base: number) => {
      (material as unknown as { opacity: number }).opacity = 0;
      infraMaterials.push({ material, base });
    };

    const routeNodes = [
      new THREE.Vector3(-0.5, 2.2, 0.5),
      new THREE.Vector3(1.2, -2.4, 0),
      new THREE.Vector3(3.2, 1.8, -0.8),
      new THREE.Vector3(4.8, -1.2, 0.2),
    ];
    const { lines: routes, material: routesMaterial } = buildRouteLines(routeNodes, cyan);
    routes.position.y = 0.1;
    infra.add(routes);
    trackInfra(routesMaterial, 0.38);

    const nodeObjects: { object: THREE.Mesh; material: THREE.Material; basePosition: THREE.Vector3 }[] = routeNodes.map((position, index) => {
      const node = new THREE.Mesh(new THREE.IcosahedronGeometry(0.18, 1), wireMaterialFor(index % 2 === 0 ? cyan : cyanDim, 0.9));
      node.position.copy(position);
      infra.add(node);
      trackInfra(node.material as THREE.Material, 0.9);
      return { object: node, material: node.material as THREE.Material, basePosition: position.clone() };
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
    speakerGroup.traverse((child) => {
      if (child instanceof THREE.Mesh) trackInfra(child.material as THREE.Material, (child.material as THREE.Material & { opacity: number }).opacity);
    });
    infra.add(speakerGroup);

    const { group: warehouse, material: warehouseMaterial } = buildWarehouse();
    warehouse.position.set(0, -3.3, -1.4);
    infra.add(warehouse);
    trackInfra(warehouseMaterial, 0.3);

    const ground = new THREE.GridHelper(18, 18, cyan, cyan);
    ground.position.set(0, -3.2, -0.8);
    const groundMaterial = ground.material as THREE.Material & { transparent: boolean };
    groundMaterial.transparent = true;
    infra.add(ground);
    trackInfra(groundMaterial as unknown as THREE.Material, 0.15);

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
      renderer!.setSize(width, height, false);
    };

    const scrollProgress = () => {
      const bounds = stage.getBoundingClientRect();
      return clamp(-bounds.top / Math.max(bounds.height - window.innerHeight, 1));
    };

    const paint = (time: number) => {
      const progress = scrollProgress();
      const morph = easeInOutQuart(clamp((progress - 0.15) / 0.4));
      const reveal = smoothstep(0.55, 0.75, progress);
      const vanish = smoothstep(0.84, 0.97, progress);
      const blueprintFade = 1 - vanish;
      const idle = reducedMotion ? 0 : time;

      voicePulse *= 0.965;
      pointerX += (targetPointerX - pointerX) * 0.04;
      pointerY += (targetPointerY - pointerY) * 0.04;

      const isDesktop = width > 1024;
      const blueprintX = isDesktop ? reveal * 3.6 : 0;

      // Camera: quartic orbit around the core while zooming in, then eases to frame the console.
      const orbitAngle = morph * Math.PI * 0.85 + pointerX * 0.06;
      const orbitDistance = 12.5 - morph * 4 - reveal * 0.8;
      camera.position.x = Math.sin(orbitAngle) * orbitDistance + blueprintX * reveal * 0.55;
      camera.position.z = Math.cos(orbitAngle) * orbitDistance;
      camera.position.y = 0.3 + morph * 0.9 - reveal * 0.35 - pointerY * 0.38;
      camera.lookAt(blueprintX * reveal, 0, 0);

      blueprint.position.x = blueprintX;
      blueprint.position.y = reveal * 0.3;
      blueprint.rotation.y = idle * 0.00016 + morph * 0.6;
      blueprint.rotation.x = pointerY * 0.05;
      blueprint.scale.setScalar(1 + morph * 0.12 - reveal * 0.08);

      // Solid dissolves into wireframe + point cloud.
      solidMaterial.opacity = (1 - morph) * blueprintFade;
      solidMaterial.emissiveIntensity = 0.32 + voicePulse * 0.5;
      wireBlueprintMaterial.opacity = morph * 0.92 * blueprintFade;
      cloudMaterial.opacity = morph * 0.45 * blueprintFade;
      const emissionMaterial = emissionCore.material as THREE.Material & { opacity: number };
      emissionMaterial.opacity = (0.55 + voicePulse * 0.35) * blueprintFade;
      emissionCore.scale.setScalar(1 + voicePulse * 0.28 + (1 - morph) * 0.06);
      solidCore.rotation.x = idle * 0.00021;
      solidCore.rotation.z = idle * 0.00013;
      pointCloud.rotation.y = -idle * 0.0003;

      // Acoustic rings expand outward in sync with scroll depth.
      rings.forEach(({ mesh, material, baseRotation }, index) => {
        const expansion = 1 + morph * (1.1 + index * 0.85) + voicePulse * 0.2;
        mesh.scale.setScalar(expansion);
        mesh.rotation.x = baseRotation.x + idle * 0.00012 * (index + 1);
        mesh.rotation.z = baseRotation.z + idle * 0.00009 * (index + 1);
        material.opacity = morph * (0.5 - index * 0.11) * (0.7 + Math.abs(Math.sin(idle * 0.0016 + index * 1.3)) * 0.3 + voicePulse * 0.3) * blueprintFade;
      });

      // Stage C: signal vectors beam down into the warehouse grid.
      infra.position.x = isDesktop ? reveal * 1.1 : 0;
      infraMaterials.forEach(({ material, base }) => {
        (material as unknown as { opacity: number }).opacity = base * reveal;
      });
      nodeObjects.forEach(({ object, material, basePosition }, index) => {
        const pulse = 1 + Math.sin(idle * 0.003 + index) * 0.22;
        object.scale.setScalar((0.35 + reveal * 0.9) * pulse);
        object.position.lerp(basePosition.clone().multiplyScalar(0.72 + reveal * 0.28), 0.08);
        (material as unknown as { opacity: number }).opacity = (0.22 + reveal * 0.78) * 0.9;
      });
      warehouse.scale.setScalar(0.2 + reveal * 0.8);
      speakerGroup.scale.setScalar(0.66 + reveal * 0.34);
      routes.scale.setScalar(0.35 + reveal * 0.65);

      renderer!.render(scene, camera);
      if (!reducedMotion && visible && pageVisible) raf = window.requestAnimationFrame(paint);
    };

    const pointerMove = (event: PointerEvent) => {
      targetPointerX = (event.clientX / Math.max(window.innerWidth, 1) - 0.5) * 2;
      targetPointerY = (event.clientY / Math.max(window.innerHeight, 1) - 0.5) * 2;
    };

    let staticTicking = false;
    const staticRepaint = () => {
      if (reducedMotion && !staticTicking) {
        staticTicking = true;
        window.requestAnimationFrame((time) => {
          staticTicking = false;
          paint(time);
        });
      }
    };

    const onVisibilityChange = () => {
      pageVisible = !document.hidden;
      if (!pageVisible) window.cancelAnimationFrame(raf);
      else if (!reducedMotion) raf = window.requestAnimationFrame(paint);
      else paint(performance.now());
    };

    const observer = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        if (!reducedMotion && visible && pageVisible && !raf) raf = window.requestAnimationFrame(paint);
        if (!visible) window.cancelAnimationFrame(raf);
      },
      { threshold: 0 }
    );

    resize();
    paint(performance.now());
    window.addEventListener("voxflow:voice-play", onVoicePlay as EventListener);

    observer.observe(stage);
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("resize", staticRepaint, { passive: true });
    window.addEventListener("scroll", staticRepaint, { passive: true });
    window.addEventListener("pointermove", pointerMove, { passive: true });
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("resize", staticRepaint);
      window.removeEventListener("scroll", staticRepaint);
      window.removeEventListener("pointermove", pointerMove);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("voxflow:voice-play", onVoicePlay as EventListener);
      coreGeometry.dispose();
      ringGeometryA.dispose();
      ringGeometryB.dispose();
      ringGeometryC.dispose();
      solidMaterial.dispose();
      wireBlueprintMaterial.dispose();
      cloudMaterial.dispose();
      rings.forEach(({ material }) => material.dispose());
      nodeObjects.forEach(({ object }) => object.geometry.dispose());
      warehouse.traverse((child) => {
        if (child instanceof THREE.Mesh) child.geometry.dispose();
      });
      ground.geometry.dispose();
      routes.geometry.dispose();
      (routes.material as THREE.Material).dispose();
      (ground.material as THREE.Material).dispose();
      (warehouseMaterial as THREE.Material).dispose();
      renderer!.dispose();
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" className="absolute inset-0 h-full w-full pointer-events-none" />;
}
