# VoxFlow Voice X-ray QA Report

**Mode:** Read-only deployed-site QA. No repository files were edited.

**Target reviewed:** [VoxFlow deployed homepage](https://voxflow-voice-agent.vercel.app/), requested target `#section-04`, and the actual deployed anchor `#voice-xray`.

## Executive result

The deployed Voice X-ray experience is **visually present and reachable through `#voice-xray`**, but it does not match the supplied QA contract in several important ways. The requested `#section-04` anchor does not exist in the deployed DOM; the actual section ID is `voice-xray`. The desktop console renders the expected four visual layers and the selected-layer telemetry readout, but the live DOM/text surface exposes no scrubber slider, milestone buttons, replay button, or ARIA slider attributes. Consequently, the interaction and keyboard tests cannot pass against the current deployment.

The deployed `/sign-up` route does resolve to a real form, so the current unauthenticated form-load check passes.

## Test summary

| Test ID | Description | Status | Evidence |
|---|---|---|---|
| 1 | Section layout and visual telemetry | **PARTIAL PASS** | `#voice-xray` lands correctly. Four waveform layers are visible, including Raw PCM, Whisper STT, Llama Intent Matrix, and Live Tool Mutation. Selected Layer 03, `112ms`, `intent: stock_check`, `hop integrity 100%`, and `confidence 98.4%` are present. Required prompt-specific marker and demo tag are absent. |
| 2 | Scrubber, milestone, and replay interaction | **FAIL / NOT AVAILABLE** | Browser element map exposed no slider or milestone buttons. Deployed text contains no `Replay 196ms Turn`, `84ms STT`, `112ms Intent`, or `196ms Write` controls. |
| 3 | Keyboard accessibility | **FAIL / NOT AVAILABLE** | No `role="slider"`, `aria-valuemin`, `aria-valuemax`, or `aria-valuenow` attributes were found in the saved deployed HTML. Keyboard arrow/Home/End behavior could not be exercised because no slider control is exposed. |
| 4 | Desktop pinning and mobile layout | **DESKTOP PARTIAL PASS; MOBILE UNVERIFIED** | Desktop visual section is reachable and the pinned hero/scroll choreography is observable. Direct requested anchor is invalid. Mobile 390px behavior could not be emulated in this browser session. |
| 5 | Reduced-motion fallback | **UNVERIFIED** | No reduced-motion emulation was available in this browser session. The deployed HTML could not confirm a disabled replay control or reduced-motion-specific static last-frame behavior. |
| — | Sign-up boundary check | **PASS** | `/sign-up` shows a real form with name, work email, company/workspace, password, language select, launch button, and sign-in link. |

## Test 1 — Section layout and visual telemetry

### Observed

Navigating to `https://voxflow-voice-agent.vercel.app/#voice-xray` landed on the Voice X-ray section. The desktop visual frame showed the section marker `02 — VOICE X-RAY / LIVE INSPECTION`, the heading `Hear the signal. See every decision.`, a dark double-bezel telemetry console, four waveform rows, and the selected-layer card.

The deployed surface exposes these four layer labels:

| Layer | Observed deployed label |
|---:|---|
| 01 | RAW PCM / 16KHZ |
| 02 | WHISPER STT TOKENS |
| 03 | LLAMA INTENT MATRIX |
| 04 | LIVE TOOL MUTATION |

The telemetry readout exposes `SELECTED LAYER / 03`, `LLAMA INTENT MATRIX`, `112ms`, `intent: stock_check · confidence: 0.98`, `hop integrity 100%`, `LATENCY 112ms`, and `CONFIDENCE 98.4%`. The surrounding page also exposes 84ms STT, 112ms LLM, and 196ms turn values.

### Deviations from the supplied contract

The supplied QA prompt asks for `04 / 08 • Telemetry // Voice X-Ray Engine`, `DEMO REPLAY // CALL #8841 (M4 CORRIDOR)`, and `Glass-to-Glass Turn: < 200ms | PASS (196ms)`. Those exact strings were not present. The live marker is `02 — VOICE X-RAY / LIVE INSPECTION`, the call label is `CALL / #8841 / INBOUND`, and the live copy says the call moves in the same 196ms turn without the requested explicit PASS string.

The requested target URL `#section-04` is also mismatched. The deployed HTML contains `id="voice-xray"` and does not contain `id="section-04"`. The correct direct target is `https://voxflow-voice-agent.vercel.app/#voice-xray`.

## Test 2 — Scrubber, milestones, and replay

The visible desktop console presents waveform and telemetry content, but no interactive control was exposed in the browser’s interactive-element map at the relevant viewport. The deployed extracted text lists static timeline labels `0ms`, `64ms`, `128ms`, and `196ms`, but no functional labels for the milestone buttons or replay action.

The following expected controls were not found in the live DOM/text surface:

| Expected control | Result |
|---|---|
| Timeline slider from 0ms to 196ms | Not exposed; FAIL |
| `84ms STT` milestone | Not found; FAIL |
| `112ms Intent` milestone | Not found; FAIL |
| `196ms Write` milestone | Not found; FAIL |
| `Replay 196ms Turn` button | Not found; FAIL |
| Stable right-column height during scrub | Not exercisable; UNVERIFIED |

## Test 3 — Keyboard accessibility

The saved deployed HTML was searched for slider semantics and returned no matches for `role="slider"`, `aria-valuemin`, `aria-valuemax`, or `aria-valuenow`. Because no slider was exposed, the requested Right Arrow, Left Arrow, Home, and End tests could not be performed. This is a **functional accessibility failure**, not merely an unverified test.

## Test 4 — Desktop versus mobile

The desktop route is visually reachable through the actual `#voice-xray` anchor. The page uses an extended cinematic hero sequence, and multiple normal wheel operations remain within that sequence before downstream content appears. The supplied `#section-04` anchor does not land because it is not the deployed ID.

A 390px viewport could not be emulated in the current browser session. Mobile stacking, overflow, touch scrubbing, and disabled desktop pinning therefore remain **unverified**.

## Test 5 — Reduced-motion fallback

Reduced-motion emulation was not available in the current browser session. The following requirements remain unverified: static 196ms last frame, disabled replay button with `disabled` and `aria-disabled`, and bypassed GSAP pinning. These should be tested in a browser with the media preference explicitly set to `reduce`.

## Additional boundary check — sign-up

The deployed route `https://voxflow-voice-agent.vercel.app/sign-up` rendered a real onboarding form rather than an indefinite loading screen. It contained:

- Your name input.
- Work email input.
- Company/workspace name input.
- Password input.
- Primary agent language select with English (UK / Global) and Hindi.
- `Launch My Workspace →` submit button.
- `Already have a workspace? Sign In` link.

This is a **PASS** for initial form presence. A submit/error/authenticated-session test was not performed because it would require entering user data and submitting a live form.

## Recommended release fixes

First, align the QA target and production markup: either publish the requested `id="section-04"` or update the QA prompt to use `#voice-xray`. Second, ship a real accessible slider with `role="slider"`, `aria-valuemin="0"`, `aria-valuemax="196"`, and `aria-valuenow`, plus keyboard support. Third, add the three milestone controls and replay button with stable layout behavior. Fourth, decide whether the prompt-specific labels are canonical product copy; if so, add them exactly and make the SLA definition explicit. Fifth, run a true 390px viewport test and a `prefers-reduced-motion: reduce` test before calling Section 04 complete.

## References

[1]: https://voxflow-voice-agent.vercel.app/ "VoxFlow deployed homepage"

[2]: https://voxflow-voice-agent.vercel.app/#voice-xray "VoxFlow deployed Voice X-ray section"

[3]: https://voxflow-voice-agent.vercel.app/sign-up "VoxFlow deployed sign-up route"
