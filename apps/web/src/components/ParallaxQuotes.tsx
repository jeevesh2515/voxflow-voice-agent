/**
 * Deep fixed-background parallax viewport.
 *
 * The Gargantua poster locks in place (sticky, not fixed — so it un-pins
 * naturally at the section boundary with no trap in either scroll direction)
 * while oversized typography glides over it under a heavy radial scrim.
 *
 * Pure CSS sticky + transform on the foreground. There is no scroll listener
 * here at all, which is exactly why reverse scrolling over it costs nothing.
 */
export default function ParallaxQuotes() {
  return (
    <section className="relative min-h-[140vh]" aria-label="Customer outcomes">
      {/* Locked background layer. */}
      <div className="sticky top-0 h-screen overflow-hidden" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/blackhole-poster.jpg"
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-45"
        />
        {/* Readability scrim — heavier at the centre where the text lands. */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(5,5,10,0.82)_0%,rgba(5,5,10,0.55)_48%,rgba(5,5,10,0.85)_100%)]" />
      </div>

      {/* Scrolling foreground. Negative top margin pulls it back over the bg. */}
      <div className="relative z-10 mx-auto -mt-[100vh] max-w-5xl space-y-48 px-6 py-[42vh]">
        <figure>
          <blockquote className="font-headline text-3xl font-extrabold leading-[1.15] tracking-tight text-white sm:text-5xl lg:text-6xl">
            &ldquo;We replaced 14 manual dispatcher queues with one autonomous
            voice signal.&rdquo;
          </blockquote>
          <figcaption className="mt-6 font-label text-xs uppercase tracking-[0.22em] text-[#a098b0]">
            — Fleet Operations, UK Logistics
          </figcaption>
        </figure>

        <figure>
          <blockquote className="font-headline text-3xl font-extrabold leading-[1.15] tracking-tight text-white sm:text-5xl lg:text-6xl">
            &ldquo;Measurable payback in 14 days, without a capital
            infrastructure project.&rdquo;
          </blockquote>
          <figcaption className="mt-6 font-label text-xs uppercase tracking-[0.22em] text-[#a098b0]">
            — CFO, National Distribution Group
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
