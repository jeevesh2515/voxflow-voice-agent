"use client";

import { useEffect, useRef } from "react";

export default function HeroCursorFollower() {
  const badgeRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const badge = badgeRef.current;
    const stage = document.getElementById("hero-stage");
    if (!badge || !stage) return;

    const hasFinePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!hasFinePointer.matches || reducedMotion.matches) return;

    let targetX = window.innerWidth * 0.5;
    let targetY = window.innerHeight * 0.5;
    let currentX = targetX;
    let currentY = targetY;
    let frame = 0;
    let active = false;

    const render = () => {
      currentX += (targetX - currentX) * 0.19;
      currentY += (targetY - currentY) * 0.19;
      badge.style.setProperty("--cursor-x", `${currentX}px`);
      badge.style.setProperty("--cursor-y", `${currentY}px`);

      if (active) frame = window.requestAnimationFrame(render);
      else frame = 0;
    };

    const begin = (event: PointerEvent) => {
      targetX = currentX = event.clientX;
      targetY = currentY = event.clientY;
      active = true;
      badge.dataset.active = "true";
      if (!frame) frame = window.requestAnimationFrame(render);
    };

    const move = (event: PointerEvent) => {
      targetX = event.clientX;
      targetY = event.clientY;
    };

    const end = () => {
      active = false;
      badge.dataset.active = "false";
    };

    stage.addEventListener("pointerenter", begin);
    stage.addEventListener("pointermove", move);
    stage.addEventListener("pointerleave", end);

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      stage.removeEventListener("pointerenter", begin);
      stage.removeEventListener("pointermove", move);
      stage.removeEventListener("pointerleave", end);
    };
  }, []);

  return (
    <div ref={badgeRef} className="hero-cursor-badge" data-active="false" aria-hidden="true">
      <span>[ SCROLL TO EXPLORE ↓ ]</span>
    </div>
  );
}
