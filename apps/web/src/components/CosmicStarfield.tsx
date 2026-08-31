"use client";

import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  size: number;
  alpha: number;
  alphaSpeed: number;
  color: string;
  vx: number;
  vy: number;
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

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const colors = [
      "rgba(255, 45, 120, ",  // Cyber Magenta
      "rgba(192, 132, 252, ", // Cosmic Violet
      "rgba(56, 189, 248, ",  // Ice Cyan
      "rgba(255, 255, 255, ", // Star White
    ];

    // Elegant, subtle particles (not distracting clutter)
    const count = Math.min(Math.floor((width * height) / 18000), 70);
    const particles: Particle[] = [];

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 2.0 + 0.6,
        alpha: Math.random() * 0.5 + 0.2,
        alphaSpeed: (Math.random() * 0.01 + 0.004) * (Math.random() > 0.5 ? 1 : -1),
        color: colors[Math.floor(Math.random() * colors.length)],
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
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
      } else if (!isRunning && !prefersReducedMotion) {
        isRunning = true;
        render();
      }
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibilityChange);

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Deep, pitch background
      ctx.fillStyle = "#07070f";
      ctx.fillRect(0, 0, width, height);

      // Smooth mouse-follow nebula glow
      mouseX += (targetMouseX - mouseX) * 0.04;
      mouseY += (targetMouseY - mouseY) * 0.04;

      // Soft ambient glowing nebula clouds
      const g1 = ctx.createRadialGradient(
        width * 0.2,
        height * 0.25,
        0,
        width * 0.2,
        height * 0.25,
        Math.max(width * 0.45, 400)
      );
      g1.addColorStop(0, "rgba(255, 45, 120, 0.06)");
      g1.addColorStop(0.6, "rgba(192, 132, 252, 0.02)");
      g1.addColorStop(1, "transparent");
      ctx.fillStyle = g1;
      ctx.fillRect(0, 0, width, height);

      const g2 = ctx.createRadialGradient(
        width * 0.82,
        height * 0.35,
        0,
        width * 0.82,
        height * 0.35,
        Math.max(width * 0.4, 380)
      );
      g2.addColorStop(0, "rgba(192, 132, 252, 0.05)");
      g2.addColorStop(0.6, "rgba(56, 189, 248, 0.015)");
      g2.addColorStop(1, "transparent");
      ctx.fillStyle = g2;
      ctx.fillRect(0, 0, width, height);

      // Subtle mouse spotlight
      const gMouse = ctx.createRadialGradient(
        mouseX,
        mouseY,
        0,
        mouseX,
        mouseY,
        Math.max(width * 0.3, 300)
      );
      gMouse.addColorStop(0, "rgba(255, 45, 120, 0.04)");
      gMouse.addColorStop(1, "transparent");
      ctx.fillStyle = gMouse;
      ctx.fillRect(0, 0, width, height);

      // Render gentle floating stardust particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        if (!prefersReducedMotion) {
          p.alpha += p.alphaSpeed;
          if (p.alpha > 0.7 || p.alpha < 0.15) {
            p.alphaSpeed = -p.alphaSpeed;
          }
          p.x += p.vx;
          p.y += p.vy;

          if (p.x < 0) p.x = width;
          if (p.x > width) p.x = 0;
          if (p.y < 0) p.y = height;
          if (p.y > height) p.y = 0;
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `${p.color}${Math.max(0.1, Math.min(0.8, p.alpha))})`;
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
