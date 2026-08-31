"use client";

import { useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { heroProgress } from "@/lib/hero-progress";

/**
 * Drives the staged hero aperture choreography.
 *
 * Publishes a single normalised scroll value (0 → 1) across the hero section to
 * two consumers:
 *   1. the `--hero-progress` CSS custom property (copy/console/HUD reveal)
 *   2. the `heroProgress` ref object (read per-frame by VoiceCoreCanvas)
 *
 * Uses ScrollTrigger `scrub` rather than toggle/callback actions on purpose.
 * Scrub maps progress as a pure function of scroll offset, so scrolling back up
 * retraces the exact same values — no stuck classes, no one-way state, no
 * reverse-scroll jumpiness.
 */
export default function HeroChoreography() {
  useEffect(() => {
    const stage = document.getElementById("hero-stage");
    if (!stage) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Marks the stage as JS-driven, which is what activates the sticky pin and
    // the progress-driven reveals in CSS. Without it the hero degrades to a
    // plain single-viewport section with all copy visible.
    stage.classList.add("hero-stage-ready");

    if (reducedMotion) {
      // Honour the preference: land directly in the fully-resolved end state.
      heroProgress.value = 1;
      stage.style.setProperty("--hero-progress", "1");
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    // Seed the variable explicitly. ScrollTrigger's onUpdate does not fire while
    // progress is still 0, so without this the property stays absent on first
    // paint and the reveal silently depends on the CSS fallback matching.
    stage.style.setProperty("--hero-progress", "0");

    let frame = 0;
    const trigger = ScrollTrigger.create({
      trigger: stage,
      start: "top top",
      end: "bottom bottom",
      scrub: true,
      onUpdate: (self) => {
        const progress = self.progress;
        heroProgress.value = progress;

        // Batch the CSS var write into a frame to avoid style thrash when
        // Lenis emits several scroll events inside one paint.
        if (frame) return;
        frame = window.requestAnimationFrame(() => {
          frame = 0;
          stage.style.setProperty("--hero-progress", progress.toFixed(4));
        });
      },
    });

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      trigger.kill();
      stage.classList.remove("hero-stage-ready");
      stage.style.removeProperty("--hero-progress");
    };
  }, []);

  return null;
}
