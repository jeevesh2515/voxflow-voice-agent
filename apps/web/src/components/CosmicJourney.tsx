import React from "react";

/**
 * CosmicJourney: Pure CSS 5-keyframe hero backdrop stack.
 * Driven entirely by the --hero-progress custom property published on #hero-stage
 * by HeroChoreography. Zero JavaScript animation loops, zero IntersectionObserver.
 */
export default function CosmicJourney() {
  return (
    <div className="journey-stack pointer-events-none" aria-hidden="true">
      <div className="journey-kf journey-kf-2" />
      <div className="journey-kf journey-kf-3" />
      <div className="journey-kf journey-kf-4" />
      <div className="journey-streaks" />
      <div className="journey-kf journey-kf-5" />
      <div className="journey-scrim" />
    </div>
  );
}
