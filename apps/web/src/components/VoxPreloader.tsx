/**
 * VoxFlow logo preloader.
 *
 * On first mount a glowing teal waveform mark sits dead-centre over the event
 * horizon, pulses for 1.2s, then dissolves (fade + slight expansion) to reveal
 * the black hole beneath. Pure CSS animation; it remains inert and fully
 * transparent afterwards, avoiding hydration timers and screenshot races.
 *
 * Reduced-motion clients skip it entirely — no point animating a reveal for
 * someone who asked not to see motion.
 */
export default function VoxPreloader() {
  return (
    <div className="vox-preloader" aria-hidden="true">
      <div className="vox-preloader-mark">
        <span className="material-symbols-outlined">graphic_eq</span>
      </div>
    </div>
  );
}
