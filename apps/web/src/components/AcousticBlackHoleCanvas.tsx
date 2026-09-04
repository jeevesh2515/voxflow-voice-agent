"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * Geodesic-traced Schwarzschild black hole with on-scroll spatial waves.
 * Ported from Eric Bruneton / Ghostty Black Hole (github.com/s0xDk/ghostty-blackhole).
 *
 * Implements numerical integration of null geodesics:
 *   a = -(3/2) * h² * x / r⁵   where h = |x × v|
 *
 * Computes:
 * - Pure Schwarzschild shadow sphere at b_crit = (3√3/2) r_s (centered via vUv)
 * - Gravitational lensing & photon sphere winding
 * - Shakura-Sunyaev Keplerian accretion disk with edge-on inclination (arcs over & under)
 * - Relativistic Doppler boosting & gravitational redshift
 * - Tanner-Helland blackbody temperature radiance (5500K -> 2400K)
 * - On-scroll spatial acoustic shockwaves and camera recession into deep cosmos
 * - Audio-reactive pulse modulation during voice persona playback
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
  uniform float uScrollProgress; // 0 -> 1 through hero scroll
  uniform float uVoicePulse;     // 0 -> 1 on voice playback
  uniform float uFade;
  uniform sampler2D uStars;
  uniform float uHasStars;
  uniform vec2  uMouse;          // Normalized aspect-corrected mouse position
  uniform float uMouseActive;    // 0 -> 1 on hover interaction

  #define PI 3.14159265359
  #define N_STEPS 52

  // Tunables calibrated to the Gargantua / Interstellar astrophysical look
  const float LENS_DEPTH    = 14.0;
  const float DISK_INNER    = 2.0;    // Inner edge (ISCO)
  const float DISK_OUTER    = 8.2;    // Outer edge
  const float DISK_INCL     = 1.52;   // Edge-on tilt in radians (87°) -> arcs over and under
  const float DISK_ROLL     = 0.05;   // Screen roll
  const float DISK_TEMP     = 5500.0; // Peak temperature in Kelvin
  const float DISK_GAIN     = 2.4;    // Emission brightness
  const float DISK_OPACITY  = 0.92;   // Near disk opacity
  const float DOPPLER_MIX   = 0.65;   // Relativistic asymmetry
  const float DISK_BEAM     = 2.6;    // Beaming exponent g^N
  const float DISK_SPEED    = 4.8;    // Orbit streak speed
  const float DISK_WIND     = 6.5;    // Spiral tightness
  const float DISK_CONTRAST = 1.4;    // Gas filament contrast
  const float EXPOSURE      = 1.45;   // HDR tonemap exposure
  const float B_CRIT        = 2.598076; // (3√3 / 2) critical impact parameter
  const float Z0            = 14.5;   // Fixed base camera distance in space

  // Rotation in 2D
  vec2 rot(vec2 p, float a) {
    float c = cos(a), s = sin(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
  }

  // Hash / value noise for gas streaks
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

  // Tanner Helland blackbody color fit (Kelvin -> normalized RGB)
  vec3 blackbody(float T) {
    float t = clamp(T, 1500.0, 40000.0) / 100.0;
    float r = t <= 66.0 ? 1.0 : clamp(1.292936 * pow(t - 60.0, -0.1332047), 0.0, 1.0);
    float g = t <= 66.0 ? clamp(0.3900816 * log(t) - 0.6318414, 0.0, 1.0)
                        : clamp(1.1298909 * pow(t - 60.0, -0.0755148), 0.0, 1.0);
    float b = t >= 66.0 ? 1.0 : (t <= 19.0 ? 0.0 : clamp(0.5432068 * log(t - 10.0) - 1.1962540, 0.0, 1.0));
    return vec3(r, g, b);
  }

  // Procedural lensed background starfield
  vec3 stars(vec3 d) {
    vec2 sph = vec2(atan(d.x, -d.z), asin(clamp(d.y, -1.0, 1.0)));
    vec2 g   = sph * 45.0;
    vec2 id  = floor(g);
    float h  = hash21(id);
    if (h < 0.93) return vec3(0.0);
    vec2 f   = fract(g) - 0.5;
    vec2 off = (vec2(hash21(id + 17.3), hash21(id + 31.7)) - 0.5) * 0.7;
    float spark = smoothstep(0.12, 0.0, length(f - off));
    float tw    = 0.7 + 0.3 * sin(uTime * (0.8 + 2.0 * hash21(id + 5.1)) + 40.0 * h);
    vec3 tint   = mix(vec3(1.0, 0.85, 0.65), vec3(0.70, 0.90, 1.0), hash21(id + 2.9));
    return tint * spark * tw * ((h - 0.93) / 0.07) * 0.85;
  }

  void main() {
    float aspect = uResolution.x / max(uResolution.y, 1.0);

    // Guaranteed mathematically dead-centered coordinates using varying vUv
    vec2 p = (vUv - vec2(0.5, 0.5)) * vec2(aspect, 1.0);
    float plen = length(p);

    // Interactive mouse gravitational curvature & ring bending
    vec2 mDelta = p - uMouse;
    float mDist = length(mDelta);
    float progress = clamp(uScrollProgress, 0.0, 1.0);
    
    // Smooth influence falloff near the accretion ring structure
    float mouseEffect = smoothstep(1.35, 0.04, mDist) * uMouseActive * (1.0 - progress * 0.88);
    
    // Spacetime curvature deflection: bends photon ray trajectories toward cursor
    vec2 lensWarp = (mDist > 0.001) ? normalize(mDelta) * (mouseEffect * 0.16 / (mDist * 2.1 + 0.32)) : vec2(0.0);
    vec2 warpedP = p - lensWarp;

    // On-scroll camera recession: black hole smoothly recedes into deep space
    float camZ = Z0 + progress * 16.0;
    float rh = mix(0.24, 0.11, progress); // Normalized shadow radius on screen
    float W = B_CRIT / max(rh, 1e-4);
    
    // Dynamic roll & inclination bend under cursor gravitational shift
    float dynamicRoll = DISK_ROLL + (uMouse.x * 0.14) * mouseEffect;
    vec2 pr = rot(warpedP, dynamicRoll) * W;
    float b = length(pr);

    float rin = max(DISK_INNER, 1.6);
    float rout = max(DISK_OUTER, rin + 0.5);

    // Ray origin with receding distance & conserved angular momentum h²
    vec3 x = vec3(pr, camZ);
    vec3 v = vec3(0.0, 0.0, -1.0);
    float h2 = dot(pr, pr);

    // Disk coordinate frame with interactive pitch/tilt bending
    float dynamicIncl = DISK_INCL + (-uMouse.y * 0.24) * mouseEffect;
    float ci = cos(dynamicIncl), si = sin(dynamicIncl);
    vec3 n = vec3(0.0, si, ci);
    vec3 e2 = vec3(0.0, ci, -si);

    vec3 emitc = vec3(0.0);
    float trans = 1.0;
    bool captured = false;
    float sPrev = dot(x, n);
    vec3 xPrev = x;

    // Leapfrog geodesic integration
    for (int i = 0; i < N_STEPS; i++) {
      float r2 = dot(x, x);
      if (r2 < 1.0) { captured = true; break; }
      if (x.z < -camZ && v.z < 0.0) break;
      if (r2 > 4.0 * camZ * camZ) break;

      float r = sqrt(r2);
      float dt = clamp(0.15 * r, 0.03, 1.4);

      // Kick-drift-kick leapfrog
      vec3 a = -1.5 * h2 * x / (r2 * r2 * r);
      v += a * (0.5 * dt);
      x += v * dt;
      r2 = dot(x, x);
      r = sqrt(r2);
      a = -1.5 * h2 * x / (r2 * r2 * r);
      v += a * (0.5 * dt);

      // Check thin-disk plane crossing
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
          float swirl = rc * DISK_WIND * 0.12 - uTime * kep * DISK_SPEED * gloc * 0.12;

          float streaks = vnoiseWrapY(vec2(rc * 2.8, turns * 19.0 + swirl * 3.0), 19.0) * 0.65 +
                          vnoiseWrapY(vec2(rc * 1.0, turns * 9.0  + swirl * 1.5 + 7.0), 9.0) * 0.35;
          streaks = 0.35 + DISK_CONTRAST * streaks * streaks;

          // Relativistic Doppler boosting
          vec3 gasdir = normalize(cross(n, xc));
          float beta = clamp(inversesqrt(max(2.0 * (rc - 1.0), 0.2)), 0.0, 0.99);
          float g = gloc / max(1.0 + beta * dot(gasdir, normalize(v)), 0.05);
          g = mix(1.0, g, DOPPLER_MIX);

          // Shakura-Sunyaev temperature profile
          float xpr = max(1.0 - sqrt(rin / rc), 0.0);
          float tprof = pow(rin / rc, 0.75) * pow(xpr, 0.25) / 0.488;
          vec3 cbb = blackbody(DISK_TEMP * tprof * g);
          float boost = pow(g, DISK_BEAM);

          // Voice audio reactivity pulse
          float voiceMod = 1.0 + uVoicePulse * 0.8 * sin(rc * 5.0 - uTime * 6.0);

          // Interactive energetic photon excitation around accretion ring near cursor
          float diskMouseDist = length(xc.xy - uMouse * 8.5);
          float mouseSpark = exp(-diskMouseDist * 0.35) * mouseEffect;

          float density = band * streaks;
          emitc += trans * cbb * (DISK_GAIN * 2.2 * density * tprof * tprof * boost * voiceMod);
          emitc += trans * vec3(0.25, 0.92, 1.0) * (mouseSpark * 1.8 * boost);
          trans *= 1.0 - clamp(DISK_OPACITY * density, 0.0, 1.0);
        }
      }
      sPrev = s;
      xPrev = x;
    }

    if (!captured && dot(x, x) < 3.2) captured = true;

    // Background sky & photon ring
    vec3 bg = vec3(0.0);
    if (!captured) {
      vec3 d = normalize(v);
      bg = stars(d);
      if (uHasStars > 0.5) {
        vec2 eqUv = vec2(atan(d.z, d.x) / (2.0 * PI) + 0.5, asin(clamp(d.y, -1.0, 1.0)) / PI + 0.5);
        bg += texture2D(uStars, eqUv).rgb * 0.55;
      }
    }

    // Continuous on-scroll spatial acoustic shockwaves radiating from event horizon
    vec3 waveGlow = vec3(0.0);
    if (progress > 0.02) {
      float waveDist = plen;
      // Resonant harmonic waves (16Hz / 32Hz audio analogy)
      float waveFreq1 = 18.0;
      float waveFreq2 = 36.0;
      float wavePhase1 = waveDist * waveFreq1 - progress * 22.0 - uTime * 1.8;
      float wavePhase2 = waveDist * waveFreq2 - progress * 34.0 - uTime * 2.4;
      
      float waveRipples1 = sin(wavePhase1);
      float waveRipples2 = cos(wavePhase2);
      
      float waveMask = smoothstep(0.04, 0.45, progress) * (1.0 - smoothstep(0.80, 0.98, progress));
      float waveSharp1 = pow(clamp(waveRipples1, 0.0, 1.0), 3.2);
      float waveSharp2 = pow(clamp(waveRipples2, 0.0, 1.0), 4.0);
      float distFalloff = exp(-waveDist * 1.85);

      // Cyan-teal primary voice wave + magenta secondary harmonic wave
      waveGlow += vec3(0.0, 1.0, 0.85) * (waveSharp1 * waveMask * distFalloff * 0.55);
      waveGlow += vec3(1.0, 0.18, 0.48) * (waveSharp2 * waveMask * distFalloff * 0.35);
      
      // Voice audio reactivity surge
      if (uVoicePulse > 0.05) {
        waveGlow += vec3(0.0, 1.0, 0.85) * (uVoicePulse * sin(waveDist * 28.0 - uTime * 8.0) * distFalloff * 0.4);
      }
    }

    // HDR exposure tonemap — natural Schwarzschild shadow and Keplerian accretion disk with zero artificial rings
    vec3 col = bg * trans + (vec3(1.0) - exp(-emitc * EXPOSURE)) + waveGlow;

    // Seamless radial vignette falloff into deep cosmic space (zero rectangular boundaries)
    float edgeBlend = smoothstep(1.45, 0.65, plen);
    col *= edgeBlend;

    gl_FragColor = vec4(col * uFade, 1.0);
  }
`;

export default function AcousticBlackHoleCanvas() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: false,
        alpha: false,
        powerPreference: "high-performance",
        stencil: false,
        depth: false,
      });
    } catch {
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.domElement.className = "acoustic-blackhole-webgl absolute inset-0 h-full w-full pointer-events-none";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const geometry = new THREE.PlaneGeometry(2, 2);

    const uniforms: Record<string, THREE.IUniform> = {
      uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      uTime: { value: 0 },
      uScrollProgress: { value: 0 },
      uVoicePulse: { value: 0 },
      uFade: { value: 1 },
      uStars: { value: null },
      uHasStars: { value: 0 },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uMouseActive: { value: 0 },
    };

    const textureLoader = new THREE.TextureLoader();
    textureLoader.load(
      "/space-starfield.webp",
      (tex) => {
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.ClampToEdgeWrapping;
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        uniforms.uStars.value = tex;
        uniforms.uHasStars.value = 1;
      },
      undefined,
      () => {
        uniforms.uHasStars.value = 0;
      }
    );

    const material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms,
      depthTest: false,
      depthWrite: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    let voicePulse = 0;
    const onVoice = () => {
      voicePulse = 1.0;
    };
    window.addEventListener("voxflow:voice-active", onVoice);

    const onResize = () => {
      if (!renderer) return;
      const w = window.innerWidth;
      const h = window.innerHeight;
      renderer.setSize(w, h);
      uniforms.uResolution.value.set(w, h);
    };
    window.addEventListener("resize", onResize);

    // Interactive pointer gravity tracking with smooth easing
    let targetMouseX = 0;
    let targetMouseY = 0;
    let currentMouseX = 0;
    let currentMouseY = 0;
    let targetMouseActive = 0;
    let currentMouseActive = 0;

    const onPointerMove = (e: PointerEvent) => {
      const aspect = window.innerWidth / Math.max(window.innerHeight, 1);
      targetMouseX = (e.clientX / window.innerWidth - 0.5) * aspect;
      targetMouseY = -(e.clientY / window.innerHeight - 0.5); // WebGL Y is inverted
      targetMouseActive = 1.0;
    };

    const onPointerLeave = () => {
      targetMouseActive = 0.0;
    };

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerleave", onPointerLeave);

    const start = performance.now();
    let animId = 0;
    let inView = true;
    let pageVisible = typeof document === "undefined" ? true : !document.hidden;

    // Idle-cost gate: the fullscreen geodesic pass renders only while the hero
    // is on screen and the tab is visible. Scrolling back resumes seamlessly
    // because every uniform is re-derived per frame — no state to restore.
    const maybeStart = () => {
      if (animId === 0 && inView && pageVisible) frame();
    };

    const frame = () => {
      animId = 0;
      voicePulse *= 0.95;
      uniforms.uTime.value = (performance.now() - start) / 1000;
      uniforms.uVoicePulse.value = voicePulse;

      // Smooth mouse coordinates interpolation
      currentMouseX += (targetMouseX - currentMouseX) * 0.08;
      currentMouseY += (targetMouseY - currentMouseY) * 0.08;
      currentMouseActive += (targetMouseActive - currentMouseActive) * 0.06;
      uniforms.uMouse.value.set(currentMouseX, currentMouseY);
      uniforms.uMouseActive.value = currentMouseActive;

      // Track hero scroll progress custom property
      const rawProgress = parseFloat(
        document.documentElement.style.getPropertyValue("--hero-progress") || "0"
      );
      uniforms.uScrollProgress.value = Math.max(0, Math.min(1, isNaN(rawProgress) ? 0 : rawProgress));

      if (renderer) renderer.render(scene, camera);
      if (inView && pageVisible) animId = requestAnimationFrame(frame);
    };
    frame();

    const observer = new IntersectionObserver(
      ([entry]) => {
        inView = entry.isIntersecting;
        if (inView) maybeStart();
        else if (animId) {
          cancelAnimationFrame(animId);
          animId = 0;
        }
      },
      { threshold: 0 }
    );
    observer.observe(container);

    const onPageVisibility = () => {
      pageVisible = !document.hidden;
      if (pageVisible) maybeStart();
      else if (animId) {
        cancelAnimationFrame(animId);
        animId = 0;
      }
    };
    document.addEventListener("visibilitychange", onPageVisibility);

    return () => {
      cancelAnimationFrame(animId);
      animId = 0;
      observer.disconnect();
      document.removeEventListener("visibilitychange", onPageVisibility);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerleave", onPointerLeave);
      window.removeEventListener("voxflow:voice-active", onVoice);
      window.removeEventListener("resize", onResize);
      if (renderer && renderer.domElement && renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement);
        renderer.dispose();
      }
      geometry.dispose();
      material.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 h-full w-full overflow-hidden pointer-events-none bg-transparent"
      aria-hidden="true"
    />
  );
}
