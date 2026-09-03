/**
 * The 5-keyframe cosmic journey backdrop for the hero stage.
 *
 * Keyframe 1 (black hole) is NOT rendered here — it is the existing
 * AcousticBlackHoleCanvas, which stays mounted as the opening frame. This
 * component supplies keyframes 2 through 5 as still-image layers that crossfade
 * across the pinned hero scroll:
 *
 *   KF2  starfield / nebula      "Out here, signals go quiet."
 *   KF3  solar system panorama   "A signal, still moving."
 *   KF4  telescope + satellite   "Someone's listening now."   (+ streak overlay)
 *   KF5  Earth arrival           no copy — hands off to the docked headline
 *
 * Deliberately has no "use client" and no JavaScript at all. Every crossfade,
 * depth push and streak sweep is a `calc()` on `--hero-progress`, the single
 * scroll value HeroChoreography already publishes on `#hero-stage`. Reusing that
 * bus (rather than adding IntersectionObserver) keeps the journey bidirectional:
 * scrolling back up retraces the identical values, because opacity is a pure
 * function of scroll offset rather than a latched observer callback.
 *
 * Each layer declares a gradient *underneath* its image URL in the same
 * `background-image` stack, so a missing or not-yet-generated still degrades to
 * a colour field of the right mood instead of a black hole in the sequence.
 */
export default function CosmicJourney() {
  return (
    <div className="journey-stack" aria-hidden="true">
      <div className="journey-kf journey-kf-2" />
      <div className="journey-kf journey-kf-3" />
      <div className="journey-kf journey-kf-4" />
      {/* Keyframe 4 is the one beat where motion exceeds a crossfade: a CSS
          starfield-streak sweep, scoped to the telescope band. */}
      <div className="journey-streaks" />
      <div className="journey-kf journey-kf-5" />
      {/* Holds the docked headline and console legible over the Earth plate. */}
      <div className="journey-scrim" />
    </div>
  );
}
