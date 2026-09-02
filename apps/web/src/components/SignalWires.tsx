"use client";

/**
 * Flowing signal wires.
 *
 * Animated via stroke-dashoffset on a vector path rather than a canvas loop:
 * the browser compositor handles it, there is no per-frame JS, and it stays
 * razor sharp at any DPR. Each wire carries a travelling luminous dash to read
 * as live traffic moving between depots.
 *
 * Purely decorative, so it is aria-hidden and disabled under reduced-motion
 * (the static paths remain, only the travel stops).
 */

type Wire = {
  d: string;
  color: string;
  /** Seconds for one traversal. Varied so wires never pulse in lockstep. */
  dur: number;
  delay: number;
  width: number;
  opacity: number;
};

const WIRES: Wire[] = [
  { d: "M -40 180 C 220 120, 420 300, 700 210 S 1080 90, 1480 200", color: "#00ffcc", dur: 5.4, delay: 0, width: 1.15, opacity: 0.5 },
  { d: "M -40 320 C 260 400, 520 200, 780 330 S 1120 430, 1480 300", color: "#ff2d78", dur: 7.1, delay: 0.9, width: 1, opacity: 0.4 },
  { d: "M -40 90 C 300 60, 560 250, 900 120 S 1200 40, 1480 130", color: "#c6ff00", dur: 8.6, delay: 1.8, width: 0.85, opacity: 0.3 },
  { d: "M -40 430 C 240 470, 480 350, 820 440 S 1160 500, 1480 410", color: "#c084fc", dur: 6.3, delay: 2.6, width: 0.9, opacity: 0.34 },
];

export default function SignalWires({ className = "" }: { className?: string }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      <svg
        className="h-full w-full"
        viewBox="0 0 1440 520"
        preserveAspectRatio="xMidYMid slice"
        fill="none"
      >
        <defs>
          {WIRES.map((w, i) => (
            <linearGradient key={i} id={`wire-grad-${i}`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={w.color} stopOpacity="0" />
              <stop offset="50%" stopColor={w.color} stopOpacity="1" />
              <stop offset="100%" stopColor={w.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>

        {WIRES.map((w, i) => (
          <g key={i}>
            {/* Static conduit. */}
            <path
              d={w.d}
              stroke={w.color}
              strokeWidth={w.width * 0.6}
              strokeOpacity={w.opacity * 0.28}
              strokeLinecap="round"
            />
            {/* Travelling packet. */}
            <path
              className="signal-wire-flow"
              d={w.d}
              stroke={`url(#wire-grad-${i})`}
              strokeWidth={w.width * 2.1}
              strokeOpacity={w.opacity}
              strokeLinecap="round"
              strokeDasharray="120 900"
              style={{
                animationDuration: `${w.dur}s`,
                animationDelay: `${w.delay}s`,
              }}
            />
          </g>
        ))}
      </svg>
    </div>
  );
}
