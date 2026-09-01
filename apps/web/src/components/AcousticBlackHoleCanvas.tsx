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

    // On-scroll camera recession: black hole smoothly recedes into deep space
    float progress = clamp(uScrollProgress, 0.0, 1.0);
    float camZ = Z0 + progress * 16.0;
    float rh = mix(0.24, 0.11, progress); // Normalized shadow radius on screen
    float W = B_CRIT / max(rh, 1e-4);
    vec2 pr = rot(p, DISK_ROLL) * W;
    float b = length(pr);

    float rin = max(DISK_INNER, 1.6);
    float rout = max(DISK_OUTER, rin + 0.5);

    // Ray origin with receding distance & conserved angular momentum h²
    vec3 x = vec3(pr, camZ);
    vec3 v = vec3(0.0, 0.0, -1.0);
    float h2 = dot(pr, pr);

    // Disk coordinate frame
    float ci = cos(DISK_INCL), si = sin(DISK_INCL);
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

          float density = band * streaks;
          emitc += trans * cbb * (DISK_GAIN * 2.2 * density * tprof * tprof * boost * voiceMod);
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

    // Einstein photon ring razor glow
    float impact = length(cross(vec3(pr, camZ), normalize(v))) / max(length(vec3(pr, camZ)), 0.001);
    float photonRing = 2.598 / camZ;
    float ring = exp(-pow((impact - photonRing) * camZ * 46.0, 2.0));
    vec3 ringColor = ring * vec3(1.0, 0.72, 0.32) * (0.8 + uVoicePulse * 0.6);

    // On-scroll spatial acoustic shockwaves radiating from event horizon
    vec3 waveGlow = vec3(0.0);
    if (progress > 0.04) {
      float waveDist = plen;
      float waveFreq = 22.0;
      float waveSpeed = 12.0;
      float wavePhase = waveDist * waveFreq - progress * 24.0 - uTime * 1.5;
      float waveRipples = sin(wavePhase);
      float waveMask = smoothstep(0.05, 0.5, progress) * (1.0 - smoothstep(0.85, 1.0, progress));
      float waveSharp = pow(clamp(waveRipples, 0.0, 1.0), 3.0);
      float distFalloff = exp(-waveDist * 2.2);
      waveGlow = vec3(0.0, 0.95, 0.85) * (waveSharp * waveMask * distFalloff * 0.42);
      waveGlow += vec3(1.0, 0.2, 0.5) * (pow(clamp(-waveRipples, 0.0, 1.0), 4.0) * waveMask * distFalloff * 0.25);
    }

    // HDR exposure tonemap
    vec3 col = bg * trans + (vec3(1.0) - exp(-emitc * EXPOSURE)) + ringColor + waveGlow;

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
    };

    const textureLoader = new THREE.TextureLoader();
    textureLoader.load(
      "/space-starfield.jpg",
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

    const start = performance.now();
    let animId = 0;

    const frame = () => {
      voicePulse *= 0.95;
      uniforms.uTime.value = (performance.now() - start) / 1000;
      uniforms.uVoicePulse.value = voicePulse;

      // Track hero scroll progress custom property
      const rawProgress = parseFloat(
        document.documentElement.style.getPropertyValue("--hero-progress") || "0"
      );
      uniforms.uScrollProgress.value = Math.max(0, Math.min(1, isNaN(rawProgress) ? 0 : rawProgress));

      if (renderer) renderer.render(scene, camera);
      animId = requestAnimationFrame(frame);
    };
    frame();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("voxflow:voice-active", onVoice);
      window.removeEventListener("resize", onResize);
      if (renderer && renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement.parentElement);
        renderer.dispose();
      }
      geometry.dispose();
      material.dispose();
    };
  }, []);

  return (
    <div ref={containerRef} className="absolute inset-0 h-full w-full overflow-hidden bg-[#000000]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/blackhole-poster.jpg"
        alt=""
        aria-hidden="true"
        className="acoustic-blackhole-fallback absolute inset-0 h-full w-full object-cover"
      />
    </div>
  );
}
