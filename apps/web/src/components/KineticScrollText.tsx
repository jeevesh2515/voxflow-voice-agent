"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/**
 * Scroll-scrubbed per-letter kinetic headline.
 *
 * Each glyph's reveal is a pure function of scroll progress, so scrolling back
 * up plays the exact inverse: letters retract in the same order they arrived,
 * with no stuck state and no replay-on-reverse. That symmetry is the whole
 * point of the effect and it is why this is not an IntersectionObserver
 * one-shot animation.
 *
 * Per-glyph accent: letters land on an accent hue and settle to their resting
 * colour as they finish, so the line "writes" itself in colour and drains back
 * out on reverse.
 */

type Props = {
  /** Lines of copy. Split by line so each can stagger independently. */
  lines: string[];
  /** Section that owns the scrub window. */
  className?: string;
  /** Accent ramp applied per-glyph while it is resolving. */
  accents?: string[];
  /** Resting colour once a glyph is fully revealed. */
  restColor?: string;
  /** Fraction of the section's scroll used for the reveal (rest is dwell). */
  revealWindow?: number;
};

const DEFAULT_ACCENTS = ["#00ffcc", "#c6ff00", "#ff2d78", "#ffe04a", "#c084fc"];

export default function KineticScrollText({
  lines,
  className = "",
  accents = DEFAULT_ACCENTS,
  restColor = "#f8fafc",
  revealWindow = 0.55,
}: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [reduced, setReduced] = useState(false);

  // Flatten to a stable glyph list once. Index drives both stagger and hue so
  // the mapping is deterministic across renders. Indices are derived from the
  // running character offset per line (no mutated closure variable), which
  // keeps the stagger ramp identical to an imperative counter.
  const glyphs = useMemo(
    () =>
      lines.map((line, lineIndex) => {
        const words = line.split(" ");
        const lineOffset = lines.slice(0, lineIndex).reduce((n, value) => n + value.length, 0);
        // Character offset at the start of each word (words + 1 space each).
        const offsets = words.reduce<number[]>((acc, w, i) => {
          acc.push(i === 0 ? 0 : acc[i - 1] + w.length + 1);
          return acc;
        }, []);
        return words.map((word, wi) =>
          Array.from(word).map((ch, ci) => ({ ch, i: lineOffset + offsets[wi] + ci }))
        );
      }),
    [lines]
  );

  const total = useMemo(
    () => lines.reduce((n, l) => n + l.length, 0) || 1,
    [lines]
  );

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      setReduced(true);
      return;
    }

    const chars = Array.from(
      host.querySelectorAll<HTMLElement>("[data-glyph]")
    );

    let frame = 0;

    const apply = () => {
      frame = 0;
      const rect = host.getBoundingClientRect();
      const vh = window.innerHeight;

      // Progress across the element's travel through the viewport. Pure
      // function of position, therefore identical in both directions.
      const raw = (vh * 0.88 - rect.top) / (rect.height + vh * 0.55);
      const p = Math.min(1, Math.max(0, raw));

      for (const el of chars) {
        const idx = Number(el.dataset.glyph);
        // Each glyph gets its own slice of the reveal window, ordered by index.
        const startAt = (idx / total) * revealWindow;
        const local = Math.min(
          1,
          Math.max(0, (p - startAt) / Math.max(revealWindow / total * 6, 0.045))
        );

        el.style.opacity = String(0.04 + local * 0.96);
        el.style.transform = `translate3d(0,${(1 - local) * 0.62}em,0) scale(${0.86 + local * 0.14})`;
        el.style.filter = local < 0.98 ? `blur(${(1 - local) * 7}px)` : "none";
        // Accent while resolving, resting colour once settled.
        el.style.color =
          local >= 0.995
            ? restColor
            : accents[idx % accents.length];
      }
    };

    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(apply);
    };

    apply();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);

    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [total, revealWindow, accents, restColor]);

  return (
    <div ref={hostRef} className={className}>
      {glyphs.map((words, li) => (
        <span key={li} className="block">
          {words.map((word, wi) => (
            <span key={wi} className="inline-block whitespace-nowrap">
              {word.map(({ ch, i }) => (
                <span
                  key={i}
                  data-glyph={i}
                  className="inline-block will-change-[transform,opacity,filter]"
                  style={
                    reduced
                      ? { opacity: 1, color: restColor }
                      : { opacity: 0.04, color: restColor }
                  }
                >
                  {ch}
                </span>
              ))}
              {wi < words.length - 1 ? <span className="inline-block">&nbsp;</span> : null}
            </span>
          ))}
        </span>
      ))}
    </div>
  );
}
