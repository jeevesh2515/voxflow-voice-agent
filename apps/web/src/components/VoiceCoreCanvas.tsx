"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { heroProgress } from "@/lib/hero-progress";

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));

const cyan = 0x00ffcc;
const magenta = 0xff2d78;
const lime = 0xc6ff00;

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
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.35,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  return new THREE.LineSegments(geometry, material);
}

/**
 * High-performance 3D WebGL Voice Telematics Core & Acoustic LiDAR Scene.
 * Framed continuously around the Live Operations Console with audio-reactive pulses.
 */
export default function VoiceCoreCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 0.2, 12.5);

    // Directional and ambient lighting for metallic & neon highlights
    scene.add(new THREE.AmbientLight(0x3a4260, 1.5));
    const keyLight = new THREE.DirectionalLight(cyan, 2.5);
    keyLight.position.set(5, 5, 7);
    const rimLight = new THREE.DirectionalLight(magenta, 2.2);
    rimLight.position.set(-6, -3, 5);
    const topLight = new THREE.DirectionalLight(0x9cb8ff, 1.2);
    topLight.position.set(0, 6, 8);
    scene.add(keyLight, rimLight, topLight);

    const world = new THREE.Group();
    scene.add(world);

    // 1. Faceted Neon-Glass Core.
    // MeshPhysicalMaterial (not Standard) so the Higgsfield-generated equirectangular
    // studio map below can drive real specular reflections + clearcoat sheen.
    const coreGeometry = new THREE.IcosahedronGeometry(1.85, 3);
    const solidMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x161e30,
      metalness: 0.62,
      roughness: 0.18,
      emissive: 0x0c1222,
      emissiveIntensity: 0.3,
      clearcoat: 0.85,
      clearcoatRoughness: 0.22,
      envMapIntensity: 0.0, // ramped to full once the texture resolves, avoids a lighting pop
      flatShading: true,
      transparent: true,
      opacity: 0.88,
    });
    const solidCore = new THREE.Mesh(coreGeometry, solidMaterial);
    world.add(solidCore);

    // Neon studio reflection environment. Loaded async and non-blocking: if the
    // request fails the scene keeps rendering on its three directional lights alone.
    const pmrem = new THREE.PMREMGenerator(renderer);
    pmrem.compileEquirectangularShader();
    let envRenderTarget: THREE.WebGLRenderTarget | null = null;
    let envTexture: THREE.Texture | null = null;
    let envRamp = 0; // 0 → 1 fade-in, applied in paint()

    const envLoader = new THREE.TextureLoader();
    envLoader.load(
      "/voice-core-env.jpg",
      (texture) => {
        texture.mapping = THREE.EquirectangularReflectionMapping;
        texture.colorSpace = THREE.SRGBColorSpace;
        envRenderTarget = pmrem.fromEquirectangular(texture);
        solidMaterial.envMap = envRenderTarget.texture;
        solidMaterial.needsUpdate = true;
        envTexture = texture;
      },
      undefined,
      () => {
        // Texture missing or blocked — directional lights already cover the look.
      }
    );

    // 2. Glowing Cyan Wireframe Twin
    const wireMaterial = wireMaterialFor(cyan, 0.65);
    const wireCore = new THREE.Mesh(coreGeometry, wireMaterial);
    wireCore.scale.setScalar(1.003);
    world.add(wireCore);

    // 3. Magenta Point-Cloud LiDAR Scan
    const cloudMaterial = new THREE.PointsMaterial({
      color: magenta,
      size: 0.05,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });
    const pointCloud = new THREE.Points(coreGeometry, cloudMaterial);
    pointCloud.scale.setScalar(1.005);
    world.add(pointCloud);

    // 4. Inner High-Energy Pulse Core
    const innerMaterial = wireMaterialFor(lime, 0.45);
    const innerCore = new THREE.Mesh(new THREE.IcosahedronGeometry(0.9, 2), innerMaterial);
    world.add(innerCore);

    // 5. 4 Concentric Acoustic Soundwave Rings
    const rings: { mesh: THREE.Mesh; material: THREE.MeshBasicMaterial; baseRotation: THREE.Euler }[] = [];
    for (let index = 0; index < 4; index += 1) {
      const ringMaterial = new THREE.MeshBasicMaterial({
        color: index % 2 === 0 ? cyan : magenta,
        transparent: true,
        opacity: 0.45 - index * 0.08,
        wireframe: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(2.1 + index * 0.35, 0.012 + index * 0.005, 8, 80),
        ringMaterial
      );
      const baseRotation = new THREE.Euler(index * 0.55 + 0.2, index * 0.72 + 0.3, index * 0.4);
      ring.rotation.copy(baseRotation);
      world.add(ring);
      rings.push({ mesh: ring, material: ringMaterial, baseRotation });
    }

    // 6. Ambient Particle Dust (500 luminous drifting particles)
    const particleCount = 500;
    const particlePositions = new Float32Array(particleCount * 3);
    for (let index = 0; index < particleCount; index += 1) {
      const radius = 3.2 + Math.random() * 5.5;
      const theta = Math.random() * Math.PI * 2;
      const y = (Math.random() - 0.5) * 5.5;
      particlePositions[index * 3] = Math.cos(theta) * radius;
      particlePositions[index * 3 + 1] = y;
      particlePositions[index * 3 + 2] = Math.sin(theta) * radius;
    }
    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particleMaterial = new THREE.PointsMaterial({
      color: 0xe0d4fc,
      size: 0.035,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const particles = new THREE.Points(particleGeometry, particleMaterial);
    world.add(particles);

    // 7. Ground Grid & Logistics Routing Lines
    const routeNodes = [
      new THREE.Vector3(-0.8, 2.2, 0.5),
      new THREE.Vector3(1.2, -2.4, 0),
      new THREE.Vector3(3.2, 1.8, -0.8),
      new THREE.Vector3(4.8, -1.2, 0.2),
    ];
    const routes = buildRouteLines(routeNodes, cyan);
    routes.scale.setScalar(0.4);
    world.add(routes);

    const ground = new THREE.GridHelper(16, 16, cyan, cyan);
    ground.position.set(0, -3.2, -0.8);
    (ground.material as THREE.Material).transparent = true;
    (ground.material as THREE.Material).opacity = 0.12;
    world.add(ground);

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
      voicePulse = 1.0;
    };

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      width = Math.max(bounds.width, 1);
      height = Math.max(bounds.height, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };

    const paint = (time: number) => {
      // Shared with the CSS choreography (see lib/hero-progress.ts) so the mesh
      // and the DOM reveal are driven by one identical value.
      const scrollProgress = clamp(heroProgress.value);
      const idle = reducedMotion ? 0 : time;

      // Stage C docking ramp. Stays at 0 through Stages A and B, which is what
      // keeps the core dead-centre for the pure-aperture opening frame.
      const dockProgress = clamp((scrollProgress - 0.5) / 0.42);

      voicePulse *= 0.955;
      pointerX += (targetPointerX - pointerX) * 0.05;
      pointerY += (targetPointerY - pointerY) * 0.05;

      // Fade the neon studio reflections in once the env map has resolved, so the
      // core gains its glass character without a single-frame lighting jump.
      if (solidMaterial.envMap && envRamp < 1) {
        envRamp = Math.min(1, envRamp + 0.02);
        solidMaterial.envMapIntensity = envRamp * 1.35;
      }

      const isDesktop = width > 1024;
      // Centred during the aperture stage, then slides across to frame the console.
      const dockOffset = isDesktop ? dockProgress * 2.5 : 0;
      world.position.x = dockOffset;
      world.position.y = -scrollProgress * 0.45;
      world.rotation.y = idle * 0.00025 + scrollProgress * 0.95;

      // Smooth camera parallax + scroll zoom
      camera.position.x = pointerX * 0.45;
      camera.position.y = 0.2 - pointerY * 0.35;
      camera.position.z = 12.5 - scrollProgress * 2.0;
      camera.lookAt(dockOffset * 0.88, 0, 0);

      // Core rotation & audio-reactive scaling
      const pulseScale = (1 + voicePulse * 0.18 + Math.sin(idle * 0.002) * 0.015) * (1 + scrollProgress * 0.08);
      solidCore.scale.setScalar(pulseScale);
      wireCore.scale.setScalar(pulseScale * 1.003);
      pointCloud.scale.setScalar(pulseScale * 1.005);
      innerCore.scale.setScalar(1 + voicePulse * 0.35 + Math.sin(idle * 0.004) * 0.04);

      solidCore.rotation.y = idle * 0.00025 + scrollProgress * 0.5;
      solidCore.rotation.x = pointerY * 0.05;
      wireCore.rotation.y = solidCore.rotation.y;
      wireCore.rotation.x = solidCore.rotation.x;
      pointCloud.rotation.y = -idle * 0.0003 - scrollProgress * 0.4;
      innerCore.rotation.y = -idle * 0.0005;

      // Scroll-driven blueprint morphing (solid fades down slightly, wireframe and point-cloud intensify)
      solidMaterial.opacity = Math.max(0.35, 0.88 - scrollProgress * 0.5);
      solidMaterial.emissiveIntensity = 0.25 + voicePulse * 0.6;
      wireMaterial.opacity = Math.min(1.0, 0.55 + scrollProgress * 0.45 + voicePulse * 0.35);
      cloudMaterial.opacity = Math.min(1.0, 0.65 + scrollProgress * 0.35 + voicePulse * 0.3);

      // Acoustic wave rings expand with scroll depth and audio pulse
      rings.forEach(({ mesh, material, baseRotation }, index) => {
        const ringExpansion = (1 + Math.sin(idle * 0.002 + index) * 0.04 + voicePulse * (0.2 + index * 0.08)) * (1 + scrollProgress * (0.3 + index * 0.15));
        mesh.scale.setScalar(ringExpansion);
        mesh.rotation.x = baseRotation.x + idle * 0.00015 * (index + 1);
        mesh.rotation.z = baseRotation.z + idle * 0.0001 * (index + 1);
        material.opacity = (0.35 + Math.abs(Math.sin(idle * 0.0018 + index)) * 0.15 + voicePulse * 0.3) * (1 + scrollProgress * 0.3);
      });

      routes.scale.setScalar(0.4 + scrollProgress * 0.25);
      particles.rotation.y = -idle * 0.00006 - scrollProgress * 0.2;

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
      if (visible && pageVisible && !reducedMotion) {
        window.cancelAnimationFrame(raf);
        raf = window.requestAnimationFrame(paint);
      }
    }, { threshold: 0.05 });

    observer.observe(canvas);
    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", pointerMove, { passive: true });
    window.addEventListener("voxflow:voice-play", onVoicePlay);
    document.addEventListener("visibilitychange", onVisibilityChange);

    paint(performance.now());

    return () => {
      window.cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", pointerMove);
      window.removeEventListener("voxflow:voice-play", onVoicePlay);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      renderer.dispose();
      pmrem.dispose();
      envRenderTarget?.dispose();
      envTexture?.dispose();
      coreGeometry.dispose();
      solidMaterial.dispose();
      wireMaterial.dispose();
      cloudMaterial.dispose();
      innerMaterial.dispose();
      particleGeometry.dispose();
      particleMaterial.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="absolute inset-0 w-full h-full pointer-events-none z-0"
    />
  );
}
