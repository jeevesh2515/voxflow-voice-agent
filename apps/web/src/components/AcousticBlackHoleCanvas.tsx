"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * Fullscreen WebGL Schwarzschild Black Hole & Sparse Starfield.
 * - Scroll-linked scale and spin
 * - Simpler shader and reduced steps on mobile / small screens
 * - Pauses RAF loop when document.hidden or off-screen
 * - Renders a single static frame when prefers-reduced-motion is active
 * - Background void token: #030308, Accent: #5EEAD4
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
  uniform float uScrollProgress; // 0 -> 1 normalized scroll
  uniform float uScrollSpin;     // cumulative spin radians
  uniform float uVoicePulse;     // 0 -> 1 on audio events
  uniform float uIsMobile;       // 1.0 if mobile, 0.0 if desktop

  #define PI 3.14159265359

  // Gravitational & accretion disk parameters
  const float DISK_INNER    = 2.0;    // ISCO
  const float DISK_OUTER    = 7.8;    // Outer accretion disk boundary
  const float DISK_INCL     = 1.50;   // ~86° edge-on inclination
  const float DISK_TEMP     = 5600.0; // Blackbody Kelvin
  const float DISK_GAIN     = 2.3;
  const float DISK_OPACITY  = 0.90;
  const float DOPPLER_MIX   = 0.65;
  const float DISK_BEAM     = 2.5;
  const float DISK_SPEED    = 4.2;
  const float DISK_WIND     = 6.0;
  const float B_CRIT        = 2.598076;
  const float Z0            = 14.0;

  vec2 rot(vec2 p, float a) {
    float c = cos(a), s = sin(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
  }

  float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }

  float vnoiseWrapY(vec2 p, float periodY) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float iY1 = mod(i.y, periodY);
    float iY2 = mod(i.y + 1.0, periodY);
    float a = hash21(vec2(i.x, iY1));
    float b = hash21(vec2(i.x + 1.0, iY1));
    float c = hash21(vec2(i.x, iY2));
    float d = hash21(vec2(i.x + 1.0, iY2));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }

  vec3 blackbody(float T) {
    float t = clamp(T, 1500.0, 40000.0) / 100.0;
    float r = t <= 66.0 ? 1.0 : clamp(1.292936 * pow(t - 60.0, -0.1332047), 0.0, 1.0);
    float g = t <= 66.0 ? clamp(0.3900816 * log(t) - 0.6318414, 0.0, 1.0)
                        : clamp(1.1298909 * pow(t - 60.0, -0.0755148), 0.0, 1.0);
    float b = t >= 66.0 ? 1.0 : (t <= 19.0 ? 0.0 : clamp(0.5432068 * log(t - 10.0) - 1.1962540, 0.0, 1.0));
    return vec3(r, g, b);
  }

  // Sparse cosmic starfield in deep void
  vec3 sparseStars(vec3 d) {
    vec2 sph = vec2(atan(d.x, -d.z), asin(clamp(d.y, -1.0, 1.0)));
    vec2 g   = sph * 42.0;
    vec2 id  = floor(g);
    float h  = hash21(id);
    if (h < 0.94) return vec3(0.0);
    vec2 f   = fract(g) - 0.5;
    vec2 off = (vec2(hash21(id + 17.3), hash21(id + 31.7)) - 0.5) * 0.7;
    float spark = smoothstep(0.11, 0.0, length(f - off));
    float tw    = 0.65 + 0.35 * sin(uTime * (0.8 + 2.0 * hash21(id + 5.1)) + 40.0 * h);
    vec3 tint   = mix(vec3(0.9, 0.95, 1.0), vec3(0.37, 0.92, 0.83), hash21(id + 2.9)); // #5EEAD4 accent tint
    return tint * spark * tw * ((h - 0.94) / 0.06) * 0.75;
  }

  void main() {
    float aspect = uResolution.x / max(uResolution.y, 1.0);
    vec2 p = (vUv - vec2(0.5, 0.5)) * vec2(aspect, 1.0);
    float plen = length(p);

    // Scroll-linked scale & spin
    float progress = clamp(uScrollProgress, 0.0, 1.0);
    float camZ = Z0 + progress * 14.0;
    float rh = mix(0.23, 0.12, progress);
    float W = B_CRIT / max(rh, 1e-4);

    // Apply scroll-linked rotation angle
    float currentRoll = 0.05 + uScrollSpin * 0.6 + progress * 0.4;
    vec2 pr = rot(p, currentRoll) * W;

    float rin = max(DISK_INNER, 1.6);
    float rout = max(DISK_OUTER, rin + 0.5);

    vec3 x = vec3(pr, camZ);
    vec3 v = vec3(0.0, 0.0, -1.0);
    float h2 = dot(pr, pr);

    float ci = cos(DISK_INCL), si = sin(DISK_INCL);
    vec3 n = vec3(0.0, si, ci);
    vec3 e2 = vec3(0.0, ci, -si);

    vec3 emitc = vec3(0.0);
    float trans = 1.0;
    bool captured = false;
    float sPrev = dot(x, n);
    vec3 xPrev = x;

    // Raymarching steps: 24 on mobile, 48 on desktop
    int maxSteps = uIsMobile > 0.5 ? 24 : 48;

    for (int i = 0; i < 48; i++) {
      if (i >= maxSteps) break;

      float r2 = dot(x, x);
      if (r2 < 1.0) { captured = true; break; }
      if (x.z < -camZ && v.z < 0.0) break;
      if (r2 > 4.0 * camZ * camZ) break;

      float r = sqrt(r2);
      float dt = clamp((uIsMobile > 0.5 ? 0.22 : 0.15) * r, 0.04, 1.6);

      vec3 a = -1.5 * h2 * x / (r2 * r2 * r);
      v += a * (0.5 * dt);
      x += v * dt;
      r2 = dot(x, x);
      r = sqrt(r2);
      a = -1.5 * h2 * x / (r2 * r2 * r);
      v += a * (0.5 * dt);

      // Check thin accretion disk intersection
      float s = dot(x, n);
      if (s * sPrev < 0.0 && trans > 0.02) {
        float tc = sPrev / (sPrev - s);
        vec3 xc = mix(xPrev, x, tc);
        float rc = length(xc);

        if (rc > rin && rc < rout) {
          float band = smoothstep(rin, rin * 1.25, rc) * (1.0 - smoothstep(rout * 0.72, rout, rc));
          float phi = atan(dot(xc, e2), xc.x);
          float turns = phi / (2.0 * PI);
          float kep = pow(rin / rc, 1.5);
          float gloc = sqrt(max(1.0 - 1.5 / rc, 0.02));
          float swirl = rc * DISK_WIND * 0.12 - (uTime * 0.8 + uScrollSpin * 0.4) * kep * DISK_SPEED * gloc * 0.12;

          float streaks = 0.5;
          if (uIsMobile > 0.5) {
            streaks = vnoiseWrapY(vec2(rc * 2.2, turns * 12.0 + swirl * 2.5), 12.0);
          } else {
            streaks = vnoiseWrapY(vec2(rc * 2.8, turns * 18.0 + swirl * 3.0), 18.0) * 0.65 +
                      vnoiseWrapY(vec2(rc * 1.0, turns * 8.0  + swirl * 1.5 + 7.0), 8.0) * 0.35;
          }
          streaks = 0.35 + 1.3 * streaks * streaks;

          vec3 gasdir = normalize(cross(n, xc));
          float beta = clamp(inversesqrt(max(2.0 * (rc - 1.0), 0.2)), 0.0, 0.99);
          float g = gloc / max(1.0 + beta * dot(gasdir, normalize(v)), 0.05);
          g = mix(1.0, g, DOPPLER_MIX);

          float xpr = max(1.0 - sqrt(rin / rc), 0.0);
          float tprof = pow(rin / rc, 0.75) * pow(xpr, 0.25) / 0.488;
          vec3 cbb = blackbody(DISK_TEMP * tprof * g);
          float boost = pow(g, DISK_BEAM);

          float density = band * streaks;
          emitc += trans * cbb * (DISK_GAIN * 2.1 * density * tprof * tprof * boost);
          trans *= 1.0 - clamp(DISK_OPACITY * density, 0.0, 1.0);
        }
      }
      sPrev = s;
      xPrev = x;
    }

    if (!captured && dot(x, x) < 3.2) captured = true;

    // Void background (#030308) + sparse stars
    vec3 voidColor = vec3(0.01176, 0.01176, 0.03137); // #030308
    vec3 bg = voidColor;
    if (!captured) {
      vec3 d = normalize(v);
      bg += sparseStars(d);
    }

    // Scroll-linked acoustic teal/cyan wave harmonics
    vec3 waveGlow = vec3(0.0);
    if (progress > 0.01) {
      float waveDist = plen;
      float wavePhase = waveDist * 16.0 - progress * 18.0 - uTime * 1.5;
      float waveRipples = sin(wavePhase);
      float waveMask = smoothstep(0.03, 0.35, progress) * (1.0 - smoothstep(0.80, 0.99, progress));
      float waveSharp = pow(clamp(waveRipples, 0.0, 1.0), 3.0);
      float distFalloff = exp(-waveDist * 1.8);

      // Accent #5EEAD4 (RGB: 0.368, 0.917, 0.831)
      waveGlow += vec3(0.368, 0.917, 0.831) * (waveSharp * waveMask * distFalloff * 0.45);
    }

    // Exposure tonemapping onto void background
    vec3 col = bg * trans + (vec3(1.0) - exp(-emitc * 1.4)) + waveGlow;

    // Radial vignette into deep void #030308
    float edgeBlend = smoothstep(1.4, 0.55, plen);
    col = mix(voidColor, col, edgeBlend);

    gl_FragColor = vec4(col, 1.0);
  }
`;

export default function AcousticBlackHoleCanvas() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof window === "undefined") return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isMobile =
      window.innerWidth < 768 ||
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: false,
        alpha: false,
        powerPreference: isMobile ? "default" : "high-performance",
        stencil: false,
        depth: false,
      });
    } catch {
      return;
    }

    const dpr = isMobile ? 1.0 : Math.min(window.devicePixelRatio || 1, 1.5);
    renderer.setPixelRatio(dpr);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.domElement.className = "w-full h-full pointer-events-none";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const geometry = new THREE.PlaneGeometry(2, 2);

    const uniforms: Record<string, THREE.IUniform> = {
      uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      uTime: { value: 0 },
      uScrollProgress: { value: 0 },
      uScrollSpin: { value: 0 },
      uVoicePulse: { value: 0 },
      uIsMobile: { value: isMobile ? 1.0 : 0.0 },
    };

    const material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms,
      depthTest: false,
      depthWrite: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    let animId = 0;
    let isRunning = true;
    let lastScrollY = window.scrollY;
    let targetSpin = 0;
    let currentSpin = 0;

    const onScroll = () => {
      const scrollY = window.scrollY;
      const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.min(1, Math.max(0, scrollY / maxScroll));
      uniforms.uScrollProgress.value = progress;

      const deltaY = scrollY - lastScrollY;
      lastScrollY = scrollY;
      targetSpin += deltaY * 0.0015;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    const onResize = () => {
      if (!renderer) return;
      const w = window.innerWidth;
      const h = window.innerHeight;
      renderer.setSize(w, h);
      uniforms.uResolution.value.set(w, h);
    };
    window.addEventListener("resize", onResize);

    const onVisibilityChange = () => {
      if (document.hidden) {
        isRunning = false;
        cancelAnimationFrame(animId);
      } else if (!isRunning && !prefersReducedMotion) {
        isRunning = true;
        renderLoop();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    const start = performance.now();

    const renderLoop = () => {
      if (!renderer) return;

      currentSpin += (targetSpin - currentSpin) * 0.08;
      uniforms.uTime.value = (performance.now() - start) / 1000;
      uniforms.uScrollSpin.value = currentSpin;

      renderer.render(scene, camera);

      if (isRunning && !prefersReducedMotion) {
        animId = requestAnimationFrame(renderLoop);
      }
    };

    if (prefersReducedMotion) {
      // Render static single frame for reduced motion preference
      uniforms.uTime.value = 1.0;
      uniforms.uScrollProgress.value = 0.0;
      uniforms.uScrollSpin.value = 0.0;
      renderer.render(scene, camera);
    } else {
      renderLoop();
    }

    return () => {
      isRunning = false;
      cancelAnimationFrame(animId);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      if (renderer) {
        if (renderer.domElement && renderer.domElement.parentNode) {
          renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
        renderer.dispose();
      }
      geometry.dispose();
      material.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 pointer-events-none -z-10 w-full h-full overflow-hidden bg-[#030308]"
      aria-hidden="true"
    />
  );
}
