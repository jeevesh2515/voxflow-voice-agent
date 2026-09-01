"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { heroProgress } from "@/lib/hero-progress";

/**
 * Physically-motivated Schwarzschild black hole, rendered as a single
 * full-screen fragment shader.
 *
 * WHY A RAY MARCHER AND NOT A GENERATED IMAGE
 * The feature that makes a black hole read as real is gravitational lensing:
 * light from behind is bent around the hole, so you see the FAR side of the
 * accretion disk arcing above and below the shadow, and the background
 * starfield smeared into an Einstein ring. That is a light-path effect. It
 * cannot be baked into a texture, because a texture has no notion of the rays
 * that formed it. So the starfield is the only generated asset here, and the
 * shader bends it.
 *
 * INTEGRATION
 * Null geodesics in Schwarzschild geometry, Cartesian form, Rs = 1:
 *
 *     d²x/dλ² = -3/2 · h² · x / r⁵      where h = x × dx/dλ  (angular momentum)
 *
 * h² is conserved along a ray, so it is computed once per pixel and the
 * integration is a cheap Verlet-style step. This is the standard formulation
 * and is accurate enough for a convincing photon ring at ~80 steps.
 */

const VERT = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

const FRAG = /* glsl */ `
  precision highp float;

  varying vec2 vUv;

  uniform vec2  uResolution;
  uniform float uTime;
  uniform float uScroll;      // hero progress 0 -> 1
  uniform float uVoicePulse;  // 0 -> 1, spikes on voice playback
  uniform float uFade;        // master opacity, driven by stage crossfade
  uniform sampler2D uStars;
  uniform float uHasStars;

  #define PI 3.14159265359

  // Disk geometry in Schwarzschild radii. Inner edge sits at the ISCO (3Rs),
  // which is where a real thin accretion disk truncates.
  const float DISK_INNER = 3.0;
  const float DISK_OUTER = 10.5;

  // Equirectangular lookup for a bent ray direction.
  vec2 dirToEquirect(vec3 d) {
    return vec2(
      atan(d.z, d.x) / (2.0 * PI) + 0.5,
      asin(clamp(d.y, -1.0, 1.0)) / PI + 0.5
    );
  }

  vec3 sampleStars(vec3 dir) {
    if (uHasStars < 0.5) {
      // Procedural fallback so a missing texture degrades to plausible sky
      // rather than a flat void.
      float h = fract(sin(dot(floor(dir * 420.0), vec3(12.9898, 78.233, 45.164))) * 43758.5453);
      float star = smoothstep(0.9985, 1.0, h);
      return vec3(star) * vec3(0.9, 0.95, 1.0);
    }
    return texture2D(uStars, dirToEquirect(dir)).rgb;
  }

  // Accretion disk, tuned to the Gargantua look from Interstellar: a razor-thin
  // blackbody disk running from near-white at the ISCO out to deep amber at the
  // rim. The voice signal modulates BRIGHTNESS rather than hue, so the disk
  // stays photoreal while still reacting to playback.
  vec3 diskEmission(vec3 hitPos, float beaming) {
    float r = length(hitPos.xz);
    float norm = clamp((r - DISK_INNER) / (DISK_OUTER - DISK_INNER), 0.0, 1.0);
    float angle = atan(hitPos.z, hitPos.x);

    // Keplerian shear: inner annuli orbit faster.
    float orbit = uTime * 0.5 / pow(max(r, 0.8), 1.5);

    // Turbulent banding. Kept low-contrast so it reads as gas structure
    // rather than a decorative pattern.
    float band = 0.82
      + 0.10 * sin(r * 7.0 - uTime * 1.1 + angle * 2.0)
      + 0.06 * sin(r * 15.0 + orbit * 6.0 - angle * 4.0);

    // Acoustic response: a radial pulse travelling outward on voice playback.
    float pulse = uVoicePulse * (0.6 + 0.4 * sin(r * 4.0 - uTime * 7.0));

    // Blackbody-ish temperature ramp. Hot core is nearly white with a faint
    // blue lift; the body is golden; the rim cools to deep orange.
    vec3 core = vec3(1.000, 0.980, 0.930);
    vec3 mid  = vec3(1.000, 0.760, 0.400);
    vec3 rim  = vec3(0.920, 0.480, 0.170);
    vec3 col = mix(core, mid, smoothstep(0.0, 0.34, norm));
    col = mix(col, rim, smoothstep(0.32, 1.0, norm));

    // A whisper of the brand teal in the coolest outer gas only — enough to
    // sit with the palette, far too little to break the photoreal read.
    col = mix(col, vec3(0.35, 0.85, 0.78), smoothstep(0.80, 1.0, norm) * 0.16);

    // Radial intensity: fierce inner edge, steep physical falloff (thin-disk
    // emission drops fast with r). The steep curve is what keeps the inner
    // annulus from clipping to a flat white sheet across the whole disk.
    float falloff = (1.0 / (0.55 + norm * 6.5));
    float edgeIn = smoothstep(0.0, 0.045, norm);
    float edgeOut = 1.0 - smoothstep(0.72, 1.0, norm);

    return col * band * falloff * edgeIn * edgeOut * beaming * (1.0 + pulse * 1.6);
  }

  void main() {
    vec2 frag = (vUv - 0.5) * vec2(uResolution.x / uResolution.y, 1.0);

    // Camera pulls back through the aperture stages. Rebased far enough out
    // that the whole disk + shadow sit inside the frame — closer framing read
    // as flying through gas rather than observing the hole.
    float camDist = mix(12.5, 17.5, smoothstep(0.0, 0.55, uScroll));
    // Near edge-on inclination is what makes the lensed far side of the disk
    // arc up over the shadow and back under it — the defining Gargantua
    // silhouette. FIXED: no pointer parallax. The hero gate requires the hole
    // to sit 100% still in space, so there is deliberately no camera wobble.
    float yaw   = uScroll * 0.5;
    float pitch = 0.105 + uScroll * 0.06;

    vec3 camPos = vec3(
      sin(yaw) * cos(pitch) * camDist,
      sin(pitch) * camDist,
      cos(yaw) * cos(pitch) * camDist
    );

    // Basis pointing back at the singularity.
    vec3 fwd   = normalize(-camPos);
    vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), fwd));
    vec3 up    = cross(fwd, right);

    // ~50deg vertical FOV.
    vec3 dir = normalize(fwd + right * frag.x * 1.05 + up * frag.y * 1.05);

    vec3 pos = camPos;
    vec3 vel = dir;

    // Conserved angular momentum for this ray.
    vec3 hVec = cross(pos, vel);
    float h2 = dot(hVec, hVec);

    vec3 colour = vec3(0.0);
    bool captured = false;

    // Step size grows with distance: fine detail near the photon sphere where
    // the bending is violent, coarse strides out in flat space.
    for (int i = 0; i < 160; i++) {
      if (i >= STEP_COUNT) break;

      float r = length(pos);
      if (r < 1.0) { captured = true; break; }   // crossed the horizon
      if (r > 42.0) break;                        // escaped to the sky

      float dt = clamp(r * 0.052, 0.018, 0.85);

      vec3 prevPos = pos;

      // Geodesic step.
      vec3 acc = -1.5 * h2 * pos / pow(dot(pos, pos), 2.5);
      vel += acc * dt;
      pos += vel * dt;

      // Equatorial disk crossing, detected by a sign change in y.
      if (prevPos.y * pos.y < 0.0) {
        float t = prevPos.y / (prevPos.y - pos.y);
        vec3 hit = mix(prevPos, pos, t);
        float hr = length(hit.xz);

        if (hr > DISK_INNER && hr < DISK_OUTER) {
          // Relativistic beaming: the limb rotating toward the viewer is
          // brighter. This asymmetry is a large part of why the image reads
          // as a real black hole rather than a symmetrical halo.
          // Doppler beaming deliberately subdued. Interstellar's effects team
          // found the physically accurate one-sided brightness read as
          // confusing on screen and muted it; kept here as a gentle asymmetry
          // rather than removed outright.
          vec3 orbitDir = normalize(vec3(-hit.z, 0.0, hit.x));
          float toward = dot(orbitDir, normalize(vel));
          float speed = 0.5 / sqrt(max(hr, 1.2));
          float beaming = pow(clamp(1.0 + toward * speed * 1.15, 0.4, 2.0), 1.35);

          colour += diskEmission(hit, beaming);
        }
      }
    }

    if (!captured) {
      // The ray survived, so its final (bent) direction samples the sky.
      // This is where the Einstein ring comes from.
      vec3 sky = sampleStars(normalize(vel));
      colour += sky * (0.55 + uScroll * 0.12);
    }

    // Photon-ring bloom hugging the shadow edge. NOTE: length(cross) / |camPos|
    // is sin of the ray's angle from the centre line, so the target must be
    // expressed in the same normalised units — the earlier version compared
    // against an absolute radius and the term never fired at all.
    float impact = length(cross(camPos, dir)) / max(length(camPos), 0.001);
    float grazing = 2.6 / camDist; // straight-line impact parameter for grazing rays
    float ring = exp(-pow((impact - grazing) * 34.0, 2.0));
    colour += ring * vec3(0.55, 0.44, 0.30) * (0.5 + uVoicePulse * 1.1);

    // Slight exposure lift, filmic-ish tonemap, then a mild gamma so the warm
    // disk keeps its glow without clipping to flat white.
    colour *= 1.12;
    colour = colour / (colour + vec3(0.78));
    colour = pow(colour, vec3(0.92));

    gl_FragColor = vec4(colour * uFade, uFade);
  }
`;

export default function AcousticBlackHoleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Reduced-motion and no-WebGL clients both fall through to the generated
    // Gargantua-style poster (<img> rendered beneath this canvas in the hero),
    // so a real black-hole image is always present even when the shader is not.
    if (reducedMotion) return;

    // Integration depth is the entire cost of this shader, so it is the knob
    // that gets turned down on weaker hardware rather than dropping the effect.
    const isSmall = window.innerWidth < 768;
    const stepCount = isSmall ? 52 : 96;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: false, // full-screen shader; MSAA buys nothing here
        powerPreference: "high-performance",
      });
    } catch {
      return; // No WebGL: the poster image beneath carries the visual.
    }

    // Ray marching is fragment-bound, so pixel count matters more than DPR
    // fidelity. Capped harder on small screens.
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isSmall ? 1.25 : 1.75));
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const uniforms: Record<string, THREE.IUniform> = {
      uResolution: { value: new THREE.Vector2(1, 1) },
      uTime: { value: 0 },
      uScroll: { value: 0 },
      uVoicePulse: { value: 0 },
      uFade: { value: 1 },
      uStars: { value: null },
      uHasStars: { value: 0 },
    };

    const material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms,
      transparent: true,
      depthWrite: false,
      defines: { STEP_COUNT: stepCount },
    });

    const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
    quad.frustumCulled = false;
    scene.add(quad);

    // Starfield that gets lensed. Async and optional.
    let starTexture: THREE.Texture | null = null;
    new THREE.TextureLoader().load(
      "/space-starfield.jpg",
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.wrapS = THREE.RepeatWrapping; // seam continuity around the panorama
        tex.wrapT = THREE.ClampToEdgeWrapping;
        tex.minFilter = THREE.LinearFilter;
        tex.generateMipmaps = false;
        uniforms.uStars.value = tex;
        uniforms.uHasStars.value = 1;
        starTexture = tex;
      },
      undefined,
      () => {
        /* keep the procedural fallback */
      }
    );

    let raf = 0;
    let visible = true;
    let pageVisible = !document.hidden;
    let voicePulse = 0;
    const start = performance.now();

    const resize = () => {
      const b = canvas.getBoundingClientRect();
      const w = Math.max(b.width, 1);
      const h = Math.max(b.height, 1);
      renderer.setSize(w, h, false);
      (uniforms.uResolution.value as THREE.Vector2).set(w, h);
    };

    const frame = () => {
      const progress = Math.min(1, Math.max(0, heroProgress.value));

      // The hole no longer fades out — it RECEDES (CSS layer opacity/scale
      // handles that in Stage C) so it stays as a clean deep-space backdrop
      // behind the hero copy and console.
      voicePulse *= 0.95;

      uniforms.uTime.value = (performance.now() - start) / 1000;
      uniforms.uScroll.value = progress;
      uniforms.uVoicePulse.value = voicePulse;
      uniforms.uFade.value = 1;

      renderer.render(scene, camera);

      if (visible && pageVisible) raf = requestAnimationFrame(frame);
    };

    const onVoice = () => {
      voicePulse = 1;
    };
    const onVisibility = () => {
      pageVisible = !document.hidden;
      cancelAnimationFrame(raf);
      if (pageVisible && visible) raf = requestAnimationFrame(frame);
    };

    const observer = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        cancelAnimationFrame(raf);
        if (visible && pageVisible) raf = requestAnimationFrame(frame);
      },
      { threshold: 0.01 }
    );

    observer.observe(canvas);
    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("voxflow:voice-play", onVoice);
    document.addEventListener("visibilitychange", onVisibility);

    frame();

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("voxflow:voice-play", onVoice);
      document.removeEventListener("visibilitychange", onVisibility);
      quad.geometry.dispose();
      material.dispose();
      starTexture?.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <>
      {/* Static fallback: always rendered. The live shader canvas above paints
          opaque over it when WebGL is available, so this only becomes visible
          for reduced-motion or no-WebGL clients. Either way the opening frame
          is a real Gargantua-style black hole, never a blank viewport. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/blackhole-poster.jpg"
        alt=""
        aria-hidden="true"
        className="absolute inset-0 h-full w-full object-cover pointer-events-none"
      />
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="absolute inset-0 h-full w-full pointer-events-none z-0"
      />
    </>
  );
}
