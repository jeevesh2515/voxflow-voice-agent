# VoxFlow Cosmic Journey — Prompt 1 of 2 (Full Journey, Still-Image Build)

Budget reality check: you have 10 Higgsfield credits and ~$25 of Claude usage.
Cinematic video generation (Kling 3.0 ~6 credits/video, Sora2/Veo3.1 40-70
credits/video, with a typical 3-5x iteration rate to get a usable clip) does not
fit that budget for a multi-beat journey. This spec uses 5 AI-generated STILL
images (~2 credits each on a Nano-Banana-Pro-tier model) and builds all motion,
scroll-sync, and the "middle" effect with CSS/JS in code — that costs Claude
usage, not Higgsfield credits.

Do not deviate from this budget split mid-build: images from Higgsfield, motion
from code. If you start generating video clips to "just see how it looks," you
will burn the 10 credits before you have a usable asset.

---

## Paste this to Claude Code as the opening message

```
Repo: github.com/jeevesh2515/voxflow-voice-agent (Next.js 14)
Live site: https://voxflow-voice-agent.vercel.app/

I'm building a 5-keyframe scroll journey for the hero section: black hole → starfield
transition → solar system panorama → telescope/satellite close-up → Earth arrival.
Each keyframe is a STATIC AI-generated image (I'll provide them), not video. The
"motion" is entirely CSS/JS: cross-fading between keyframes, parallax depth on
foreground/background layers within each image (if I provide layered exports),
and scroll-triggered text reveals in the style of pinned storytelling sections
(fade + slight upward translate as each section enters viewport, using
IntersectionObserver — this is the same pattern Terminal Industries' site uses
for its stat/FAQ reveals, not a full video-scrub technique).

Once the journey reaches Earth (keyframe 5), that image freezes and becomes a
STICKY background behind the existing hero headline ("We closed the black hole
on the dispatch line") and the Live Operations Console panel — replacing the
black hole image currently there. It does NOT persist behind sections further
down the page (multi-depot switchboard, telemetry, ROI calculator, pricing —
none of that changes).

No Three.js/WebGL. No video-frame-sequence canvas scrubbing — that technique is
for continuous motion, and this build is 5 discrete images with crossfades, which
is simpler and cheaper to get right.
```

## The 5 keyframes and what happens at each

1. **Black hole** — already provided, clean, at
   `public/images/journey/01-black-hole.webp`. Watermark already removed on
   your end — use as-is, no further editing needed.
2. **Starfield / nebula transition** — brief scroll distance, mostly a visual
   bridge. First scroll-reveal text line appears here.
3. **Solar system panorama** — planets in correct order (Mercury → Neptune),
   ONE combined image, not one image per planet. Second text line appears here.
4. **Telescope + satellite close-up** — the "communication" beat. This is where
   the mid-journey scroll effect lives: a CSS-driven starfield-streak/zoom overlay
   plays as this section is entered, giving a sense of speed/motion without being
   a rendered video. Third text line appears here.
5. **Earth arrival** — blue marble, clouds, partial zoom (Apple-wallpaper style).
   This is the LAST keyframe. It freezes and becomes the sticky background for
   the existing hero headline/console handoff. No new tagline here — the existing
   "We closed the black hole on the dispatch line" copy takes over directly.

## Scroll-reveal text (Terminal-Industries style)

Fade + slight upward translate on scroll-into-view, gone before the next
keyframe fully takes over. Use these lines as-is — don't have Claude Code
brainstorm alternatives, that's the bigger token cost you were right to worry
about:

- **Keyframe 2 (starfield/nebula):** "Out here, signals go quiet."
- **Keyframe 3 (solar system panorama):** "A signal, still moving."
- **Keyframe 4 (telescope/satellite):** "Someone's listening now."
- **Keyframe 5 (Earth arrival):** none — hard cut into the existing "We closed
  the black hole on the dispatch line" headline, no overlap.

The arc: silence → a signal traveling → someone receiving it → "we closed the
black hole." The existing headline is the payoff the whole journey sets up,
so the last beat before it needs to stay empty, not compete with it.

## Higgsfield prompts — 5 stills, budget: 2 credits each, 10 total

Use a still-image model (Nano-Banana-Pro tier or equivalent), not a video model.

1. *(provided asset at `public/images/journey/01-black-hole.webp` — no
   generation needed, no credits spent)*
2. **Starfield/nebula**: deep space, dense star field transitioning into soft
   nebula color (dark blue/violet), no planets or objects in frame, cinematic,
   high detail, dark background suitable for text overlay
3. **Solar system panorama**: wide view of the solar system from an oblique
   angle, Sun at one edge, all 8 planets in correct order and relative spacing
   (compressed for composition, not to scientific scale), dark space background,
   photorealistic, no text/UI
4. **Telescope + satellite**: a space telescope (Hubble-style) and a
   communications satellite in the same frame, Earth visible small in the
   background, realistic materials and lighting, dark space background
5. **Earth arrival**: Earth from orbit, blue marble, visible cloud cover,
   sunlit, partial zoom (Earth fills roughly 40-60% of frame, curvature visible,
   not a tight close-up), no text/UI, matches classic Apple Earth-wallpaper style

Generate ONE take per image, not 2-3 candidates — at 10 credits total you don't
have room for taste-testing multiple versions of each. If a generation comes back
unusable, that's the one you're allowed to re-roll; budget for at most one retry
across the whole set, not one per image.

## Scroll mechanics

- Each keyframe transition: crossfade, not hard cut, over a short scroll distance.
- Keyframe 4's "middle scroll effect" is the one place motion goes beyond a
  crossfade — a CSS particle/streak overlay, cheap to build, no additional
  Higgsfield spend.
- Total scroll distance for the full 5-keyframe journey: keep it under 3x
  viewport height. Longer than that and you risk the visitor giving up before
  reaching your actual product content.
- `prefers-reduced-motion`: fall back to keyframe 5 (Earth) as a static hero
  image with no crossfade sequence at all.

## Budget discipline

- Generate all 5 images in one Higgsfield session before starting the Claude
  Code build — don't go back and forth generating one image at a time while
  code is waiting on it.
- Give Claude Code the full spec above plus the 5 final image files in one
  message.
- Batch feedback into one round rather than one issue per message.
- If it's not converging by round 3, cut keyframe 4 (telescope/satellite) before
  cutting the solar system panorama or the Earth handoff — those two carry more
  of the "black hole to Earth" through-line than the telescope beat does.

## Explicitly out of scope for this pass

- No individually rendered planet-by-planet close-ups.
- No video generation of any kind — stills only.
- No sticky background behind sections below the hero.
- No performance/heaviness work — separate prompt, separate budget, run later.
