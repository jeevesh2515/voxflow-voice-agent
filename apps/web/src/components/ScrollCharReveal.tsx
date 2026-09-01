"use client";

import { useEffect, useRef } from "react";
import { heroProgress } from "@/lib/hero-progress";

interface ScrollCharRevealProps {
  text: string;
  startProgress: number;
  endProgress: number;
  highlightColor?: string;
  className?: string;
  as?: "h1" | "h2" | "h3" | "p" | "span" | "div";
}

/**
 * Character-by-character illuminated scroll text reveal (Terminal Industries pattern).
 *
 * Progressively lights up each glyph as --hero-progress advances through the
 * component's defined scroll window:
 *   1. Inactive: dimmed subtle translucent slate (rgba(255, 255, 255, 0.22))
 *   2. Active reveal front: hot vibrant neon highlightColor with radiant glow
 *   3. Fully revealed: crisp pristine white (#ffffff)
 */
export default function ScrollCharReveal({
  text,
  startProgress,
  endProgress,
  highlightColor = "#00ffcc",
  className = "",
  as: Component = "h2",
}: ScrollCharRevealProps) {
  const containerRef = useRef<HTMLElement | null>(null);

  // Split text into words, and words into characters with preserved spacing
  const words = text.split(" ");
  let globalCharIndex = 0;
  const wordTokens = words.map((word) => {
    const chars = word.split("").map((char) => ({
      char,
      index: globalCharIndex++,
    }));
    globalCharIndex++; // Count space as a progression step
    return chars;
  });

  const totalChars = Math.max(globalCharIndex - 1, 1);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const charEls = container.querySelectorAll<HTMLSpanElement>(".scroll-char");
    if (!charEls.length) return;

    let animId = 0;
    let prevProgress = -1;

    const update = () => {
      const p = heroProgress.value;
      if (Math.abs(p - prevProgress) > 0.0004) {
        prevProgress = p;

        // Progress normalised across this punchline's active window [0, 1]
        const localProgress = Math.max(
          0,
          Math.min(1, (p - startProgress) / Math.max(endProgress - startProgress, 0.001))
        );

        const currentActiveIndex = localProgress * (totalChars + 1.5);

        charEls.forEach((el, i) => {
          const charDist = i - currentActiveIndex;

          if (charDist > 0.8) {
            // Inactive / unrevealed
            el.style.color = "rgba(255, 255, 255, 0.22)";
            el.style.textShadow = "none";
            el.style.opacity = "0.7";
            el.style.transform = "none";
          } else if (charDist >= -1.2 && charDist <= 0.8) {
            // Active illuminating front with hot color transition & glow
            el.style.color = highlightColor;
            el.style.textShadow = `0 0 18px ${highlightColor}, 0 0 36px ${highlightColor}88`;
            el.style.opacity = "1";
            el.style.transform = "translate3d(0, -1px, 0)";
          } else {
            // Settled / fully illuminated
            el.style.color = "#ffffff";
            el.style.textShadow = "0 4px 24px rgba(0, 0, 0, 0.95)";
            el.style.opacity = "1";
            el.style.transform = "none";
          }
        });
      }
      animId = requestAnimationFrame(update);
    };

    update();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [startProgress, endProgress, highlightColor, totalChars]);

  return (
    <Component
      ref={containerRef as any}
      className={`scroll-char-reveal ${className}`}
      aria-label={text}
    >
      {wordTokens.map((chars, wordIdx) => (
        <span key={wordIdx} className="inline-block whitespace-nowrap mr-[0.28em]">
          {chars.map(({ char, index }) => (
            <span
              key={index}
              className="scroll-char inline-block transition-all duration-150"
              style={{
                color: "rgba(255, 255, 255, 0.22)",
                opacity: 0.7,
              }}
              aria-hidden="true"
            >
              {char}
            </span>
          ))}
        </span>
      ))}
    </Component>
  );
}
