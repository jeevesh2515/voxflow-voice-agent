# VoxFlow Heaviness Pass — Prompt 2 of 2 (Separate budget, run later)

Do not run this in the same session as the cosmic journey build. Ship and stabilize
that first; this is a distinct pass once the hero work is live.

---

## Paste this to Claude Code as the opening message

```
Repo: github.com/jeevesh2515/voxflow-voice-agent (Next.js 14)
Live site: https://voxflow-voice-agent.vercel.app/

This page is performance-heavy. Before changing anything, profile it: run a
Lighthouse/PageSpeed audit and report total JS execution time, long tasks, and
main-thread blocking time. Then identify every independent animation loop or timer
currently running on the page — I believe these exist and want them enumerated:

- The Live Operations Console counters (active calls, handled, orders)
- The streaming call-log / "Voxflow — Call Log syncing" feed
- The multi-depot switchboard (six simultaneous live states: LDN/BHM/MAN/BRS/LDS/GLA)
- The Voice X-Ray telemetry timeline (layer-by-layer hop trace)
- The ROI calculator (live-computed on slider input)
- The new cosmic-journey canvas frame-scrub from the hero (if shipped by this point)

For each one, tell me whether it's using its own setInterval/requestAnimationFrame
loop or a shared one, and whether it's still running when scrolled off-screen.
```

## What to actually fix, roughly in priority order

1. **Consolidate animation loops.** Multiple independent `setInterval`/`requestAnimationFrame`
   calls fighting for the main thread is a classic cause of jank that has nothing to
   do with image weight. Get these onto a single shared rAF loop where possible.

2. **Gate below-the-fold widgets with IntersectionObserver.** The multi-depot switchboard,
   telemetry timeline, and call-log feed almost certainly don't need to be animating
   before the user has scrolled to them. Mount their animation logic only when they
   enter the viewport, and pause/unmount it when they leave.

3. **Stop the cosmic-journey canvas loop once its section is scrolled past.** This is
   the most likely candidate for silently running forever if it's not explicitly
   torn down — check this first if it was shipped in the prior pass.

4. **Audit image and video formats.** Confirm WebP/AVIF is used throughout, check
   the LIDAR/radar images and any background imagery are appropriately sized (not
   serving a 4K source for a 400px display box), and lazy-load anything below the
   first viewport.

5. **Bundle analysis.** Run `next build` with the bundle analyzer, look for anything
   unexpectedly large (an unused chart library, a duplicated dependency, moment.js
   instead of a lighter date library, etc.).

6. **Respect `prefers-reduced-motion` everywhere,** not just on the hero — the
   telemetry and switchboard panels are strong candidates for a reduced-motion
   fallback too.

## Deliverable format to ask for

Ask Claude Code to produce a short before/after report: Lighthouse score, total
JS execution time, and largest contentful paint, measured before changes and again
after. Don't accept "should be faster now" without the numbers — that's the only
way to know the pass actually worked.

## Budget discipline

- This is diagnostic-then-fix work, which is naturally more iterative than the
  hero build. Expect more round-trips here, not fewer.
- Front-load the profiling step and get the numbers before asking for any fixes —
  don't let Claude Code guess at the bottleneck and start refactoring blind.
- Fix in the priority order above and re-measure after each major change, not just
  at the very end, so you can attribute the improvement to a specific fix.
