"use client";

import { useEffect, useRef } from "react";

type Point = {
  x: number;
  y: number;
  z: number;
  phase: number;
  hue: number;
};

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;
const smoothstep = (from: number, to: number, value: number) => {
  const progress = clamp((value - from) / (to - from));
  return progress * progress * (3 - 2 * progress);
};

/**
 * A lightweight Canvas 2D alternative to a WebGL hero. It is intentionally
 * procedural, uses no third-party assets, pauses when the page is hidden, and
 * respects reduced-motion preferences.
 */
export default function VoiceCoreCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const stage = document.getElementById("hero-stage");
    const context = canvas?.getContext("2d");

    if (!canvas || !stage || !context) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pointCount = Math.min(window.innerWidth < 640 ? 76 : 126, reducedMotion ? 72 : 126);
    const points: Point[] = Array.from({ length: pointCount }, (_, index) => {
      const offset = 2 / pointCount;
      const y = index * offset - 1 + offset / 2;
      const radius = Math.sqrt(1 - y * y);
      const theta = index * Math.PI * (3 - Math.sqrt(5));

      return {
        x: Math.cos(theta) * radius,
        y,
        z: Math.sin(theta) * radius,
        phase: (index * 17.73) % (Math.PI * 2),
        hue: index % 5 === 0 ? 322 : index % 3 === 0 ? 186 : 270,
      };
    });

    let width = 0;
    let height = 0;
    let ratio = 1;
    let animationFrame = 0;
    let active = true;
    let pageVisible = !document.hidden;
    let pointerX = 0.5;
    let pointerY = 0.5;
    let targetPointerX = 0.5;
    let targetPointerY = 0.5;
    let progress = 0;

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      width = Math.max(bounds.width, 1);
      height = Math.max(bounds.height, 1);
      ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const getProgress = () => {
      const bounds = stage.getBoundingClientRect();
      return clamp(-bounds.top / Math.max(bounds.height - window.innerHeight, 1));
    };

    const drawGrid = (fade: number) => {
      if (fade <= 0.005) return;

      const horizon = height * 0.68;
      const vanishingX = width * 0.5;
      context.save();
      context.lineWidth = 1;
      context.strokeStyle = `rgba(77, 245, 219, ${0.1 * fade})`;

      for (let step = -7; step <= 7; step += 1) {
        context.beginPath();
        context.moveTo(vanishingX, horizon);
        context.lineTo(vanishingX + step * width * 0.18, height);
        context.stroke();
      }

      for (let row = 0; row < 8; row += 1) {
        const curve = row / 8;
        const y = lerp(horizon, height + 60, curve * curve);
        context.globalAlpha = fade * (0.8 - curve * 0.5);
        context.beginPath();
        context.moveTo(0, y);
        context.lineTo(width, y);
        context.stroke();
      }
      context.restore();
    };

    const draw = (time: number) => {
      progress = getProgress();
      pointerX = lerp(pointerX, targetPointerX, 0.045);
      pointerY = lerp(pointerY, targetPointerY, 0.045);

      context.clearRect(0, 0, width, height);

      const morph = smoothstep(0.34, 0.92, progress);
      const zoom = 1 + smoothstep(0.02, 0.62, progress) * 0.62;
      const centerX = width * (0.57 + (pointerX - 0.5) * 0.035);
      const centerY = height * (0.49 + (pointerY - 0.5) * 0.035);
      const scale = Math.min(width, height) * (width < 640 ? 0.31 : 0.275) * zoom;
      const turn = time * 0.00016 + progress * 1.36;
      const positions: Array<{ x: number; y: number; depth: number; hue: number }> = [];

      const aura = context.createRadialGradient(centerX, centerY, 0, centerX, centerY, scale * 1.8);
      aura.addColorStop(0, `rgba(255, 45, 120, ${0.16 - morph * 0.04})`);
      aura.addColorStop(0.35, `rgba(78, 214, 221, ${0.075 + morph * 0.025})`);
      aura.addColorStop(1, "rgba(5, 5, 8, 0)");
      context.fillStyle = aura;
      context.fillRect(0, 0, width, height);

      drawGrid(smoothstep(0.38, 0.88, progress));

      points.forEach((point, index) => {
        const spinX = point.x * Math.cos(turn) - point.z * Math.sin(turn);
        const spinZ = point.x * Math.sin(turn) + point.z * Math.cos(turn);
        const wave = Math.sin(time * 0.0011 + point.phase) * 0.035 * (1 - morph);
        const depth = (spinZ + 1.8) / 3.5;
        const perspective = 0.62 + depth * 0.62;
        const sphereX = centerX + spinX * scale * perspective;
        const sphereY = centerY + (point.y + wave) * scale * perspective;

        const column = index % 9;
        const orbit = index * 1.618 + time * 0.00014;
        const networkX = width * (0.18 + column * 0.08) + Math.cos(orbit) * 22 + (index % 2 ? 0 : 18);
        const networkY = height * (0.22 + ((index * 7) % 11) * 0.052) + Math.sin(orbit * 1.7) * 18;

        positions.push({
          x: lerp(sphereX, networkX, morph),
          y: lerp(sphereY, networkY, morph),
          depth,
          hue: point.hue,
        });
      });

      context.save();
      for (let left = 0; left < positions.length; left += 1) {
        for (let right = left + 1; right < positions.length; right += 1) {
          const a = positions[left];
          const b = positions[right];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          const maximum = lerp(scale * 0.47, width * 0.12, morph);
          if (distance < maximum && (right - left < 10 || (left + right) % 11 === 0)) {
            const alpha = (1 - distance / maximum) * (0.18 + morph * 0.16);
            context.strokeStyle = `hsla(${a.hue}, 94%, 70%, ${alpha})`;
            context.lineWidth = morph > 0.65 ? 0.75 : 0.55;
            context.beginPath();
            context.moveTo(a.x, a.y);
            context.lineTo(b.x, b.y);
            context.stroke();
          }
        }
      }
      context.restore();

      positions.forEach((point, index) => {
        const size = lerp(1.2, 2.35, point.depth) + (index % 7 === 0 ? 0.65 : 0);
        context.beginPath();
        context.fillStyle = `hsla(${point.hue}, 100%, ${lerp(67, 76, point.depth)}%, ${lerp(0.42, 0.96, point.depth)})`;
        context.shadowBlur = index % 4 === 0 ? 16 : 7;
        context.shadowColor = `hsla(${point.hue}, 100%, 66%, 0.75)`;
        context.arc(point.x, point.y, size, 0, Math.PI * 2);
        context.fill();
      });
      context.shadowBlur = 0;

      const coreRadius = scale * (0.12 - morph * 0.08);
      if (coreRadius > 3) {
        const core = context.createRadialGradient(centerX, centerY, 0, centerX, centerY, coreRadius * 3.5);
        core.addColorStop(0, "rgba(255, 255, 255, 0.98)");
        core.addColorStop(0.09, "rgba(255, 45, 120, 0.92)");
        core.addColorStop(0.38, "rgba(73, 224, 213, 0.3)");
        core.addColorStop(1, "rgba(5, 5, 8, 0)");
        context.fillStyle = core;
        context.beginPath();
        context.arc(centerX, centerY, coreRadius * 3.5, 0, Math.PI * 2);
        context.fill();
      }

      if (!reducedMotion && active && pageVisible) {
        animationFrame = window.requestAnimationFrame(draw);
      }
    };

    const updatePointer = (event: PointerEvent) => {
      targetPointerX = event.clientX / Math.max(window.innerWidth, 1);
      targetPointerY = event.clientY / Math.max(window.innerHeight, 1);
    };

    const onVisibilityChange = () => {
      pageVisible = !document.hidden;
      if (!pageVisible) {
        window.cancelAnimationFrame(animationFrame);
      } else if (!reducedMotion) {
        animationFrame = window.requestAnimationFrame(draw);
      } else {
        draw(performance.now());
      }
    };

    const onScroll = () => {
      if (reducedMotion) draw(performance.now());
    };

    resize();
    draw(performance.now());
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", updatePointer, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      active = false;
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", updatePointer);
      window.removeEventListener("scroll", onScroll);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" className="absolute inset-0 h-full w-full pointer-events-none" />;
}
