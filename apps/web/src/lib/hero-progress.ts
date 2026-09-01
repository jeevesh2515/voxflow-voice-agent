/**
 * Single source of truth for the hero aperture scroll progress (0 → 1).
 *
 * Written once per scroll tick by HeroChoreography (GSAP ScrollTrigger scrub),
 * read every frame by AcousticBlackHoleCanvas.
 *
 * Deliberately a mutable ref object rather than React state or a CSS-var
 * read-back: the canvas samples this inside requestAnimationFrame, so it must
 * be an O(1) property access. Reading the CSS variable via getComputedStyle
 * each frame would force a style recalculation and cost us the 60fps budget.
 */
export const heroProgress = { value: 0 };
