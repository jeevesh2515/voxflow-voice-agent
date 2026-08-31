"use client";

import { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  size: number;
  baseAlpha: number;
  alpha: number;
  alphaSpeed: number;
  color: string;
  vx: number;
  vy: number;
  isBright: boolean;
}

export default function CosmicStarfield() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId = 0;
    let isRunning = true;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Respect reduced motion preference for accessibility
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const colors = [
      "rgba(255, 45, 120, ",  // Cyber Magenta
      "rgba(192, 132, 252, ", // Cosmic Violet
      "rgba(56, 189, 248, ",  // Ice Cyan
      "rgba(255, 224, 74, ",  // Warm Gold
      "rgba(255, 255, 255, ", // Bright Star White
    ];

    const isMobile = width < 768;
    const starCount = Math.min(
      Math.floor((width * height) / (isMobile ? 12000 : 7500)),
      isMobile ? 65 : 170
    );
    const stars: Star[] = [];

    for (let i = 0; i < starCount; i++) {
      const baseAlpha = 0.35 + Math.random() * 0.65;
      const size = Math.random() * 2.4 + 0.8;
      stars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size,
        baseAlpha,
        alpha: baseAlpha,
        alphaSpeed: (Math.random() * 0.02 + 0.008) * (Math.random() > 0.5 ? 1 : -1),
        color: colors[Math.floor(Math.random() * colors.length)],
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        isBright: size > 2.0,
      });
    }

    let mouseX = width / 2;
    let mouseY = height / 2;
    let targetMouseX = mouseX;
    let targetMouseY = mouseY;

    const onMouseMove = (e: MouseEvent) => {
      targetMouseX = e.clientX;
      targetMouseY = e.clientY;
    };

    const onResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const onVisibilityChange = () => {
      if (document.hidden) {
        isRunning = false;
        cancelAnimationFrame(animationId);
      } else {
        if (!isRunning && !prefersReducedMotion) {
          isRunning = true;
          render();
        }
      }
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibilityChange);

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Deep space canvas background
      ctx.fillStyle = "#050508";
      ctx.fillRect(0, 0, width, height);

      // Smooth mouse interpolation for interactive glowing nebula
      mouseX += (targetMouseX - mouseX) * 0.05;
      mouseY += (targetMouseY - mouseY) * 0.05;

      // Ambient radial nebula glows
      const nebula1 = ctx.createRadialGradient(
        width * 0.25,
        height * 0.25,
        0,
        width * 0.25,
        height * 0.25,
        Math.max(width * 0.5, 500)
      );
      nebula1.addColorStop(0, "rgba(255, 45, 120, 0.08)");
      nebula1.addColorStop(0.6, "rgba(168, 85, 247, 0.03)");
      nebula1.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = nebula1;
      ctx.fillRect(0, 0, width, height);

      const nebula2 = ctx.createRadialGradient(
        width * 0.8,
        height * 0.7,
        0,
        width * 0.8,
        height * 0.7,
        Math.max(width * 0.45, 450)
      );
      nebula2.addColorStop(0, "rgba(192, 132, 252, 0.06)");
      nebula2.addColorStop(0.5, "rgba(56, 189, 248, 0.02)");
      nebula2.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = nebula2;
      ctx.fillRect(0, 0, width, height);

      // Mouse interactive spotlight
      const mouseGlow = ctx.createRadialGradient(
        mouseX,
        mouseY,
        0,
        mouseX,
        mouseY,
        Math.max(width * 0.35, 380)
      );
      mouseGlow.addColorStop(0, "rgba(255, 45, 120, 0.07)");
      mouseGlow.addColorStop(0.5, "rgba(168, 85, 247, 0.025)");
      mouseGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = mouseGlow;
      ctx.fillRect(0, 0, width, height);

      // 1. Draw connecting constellation lines (single batch)
      ctx.beginPath();
      for (let i = 0; i < stars.length; i++) {
        const s = stars[i];
        for (let j = i + 1; j < stars.length; j++) {
          const s2 = stars[j];
          const dx = s.x - s2.x;
          const dy = s.y - s2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < (isMobile ? 70 : 95)) {
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(s2.x, s2.y);
          }
        }
      }
      ctx.strokeStyle = "rgba(255, 45, 120, 0.12)";
      ctx.lineWidth = 0.5;
      ctx.stroke();

      // 2. Draw stars
      for (let i = 0; i < stars.length; i++) {
        const s = stars[i];

        if (!prefersReducedMotion) {
          // Twinkle
          s.alpha += s.alphaSpeed;
          if (s.alpha > 0.95 || s.alpha < 0.2) {
            s.alphaSpeed = -s.alphaSpeed;
          }

          // Float movement
          s.x += s.vx;
          s.y += s.vy;

          if (s.x < 0) s.x = width;
          if (s.x > width) s.x = 0;
          if (s.y < 0) s.y = height;
          if (s.y > height) s.y = 0;
        }

        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        ctx.fillStyle = `${s.color}${Math.max(0.2, Math.min(1, s.alpha))})`;

        // Optimize GPU fill by only blooming brightest prominent stars
        if (s.isBright && !isMobile) {
          ctx.shadowBlur = 8;
          ctx.shadowColor = s.color + "0.8)";
        } else {
          ctx.shadowBlur = 0;
        }

        ctx.fill();
      }

      if (!prefersReducedMotion && isRunning) {
        animationId = requestAnimationFrame(render);
      }
    };

    render();

    return () => {
      isRunning = false;
      cancelAnimationFrame(animationId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0 w-full h-full"
      aria-hidden="true"
    />
  );
}
