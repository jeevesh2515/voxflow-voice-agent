# Voxflow Voice OS — Read-only QA findings

Target: https://journals-forbes-las-reported.trycloudflare.com/

## Homepage inventory

The deployed homepage exposes a minimal global header with VOXFLOW, PRODUCT, PRICING, HEAR IT, CONTACT, and a “Fix one workflow” CTA. The hero contains the proof chip “UK EDGE · ~200MS · EN + HINDI”, the requested headline “We closed the black hole on the dispatch line.”, subhead “Voice agents check stock, move docks, write sheets — on the call.”, and “Hear it live” / “Fix one workflow” CTAs.

Section 02 is “PROBLEM // THE CONVERSATION BLACK HOLE” with heading “Traditional IVR is a clipboard with a phone wire.” and three artifact cards: HOLD TIME 4:18 / M4 Corridor, MANUAL ERP LOOKUP / SKU-7729, and LANGUAGE BARRIER / EN / Hinglish. The payoff reads “The driver is still on the line. The sheet is already updated.”

Section 03 is “ARCHITECTURE // DUAL DEPLOYMENT PATH” with 01 // FAST START and 02 // CONTROL TOWER cards. The expected setup, telephony, state sync, multi-depot mesh, unified memory, and ~200ms turn labels are present.

Section 04 is “TELEMETRY // VOICE X-RAY ENGINE” with the requested heading, demo tag, SLA string, four layer labels, 84ms/112ms/196ms milestones, replay button, and keyboard hint. Section 05 is “OPERATIONS // FOUR OPERATING ZONES” with four tab labels. Sections 06, 07, and 08 are present as wrappers with the requested labels.

## Direct interaction observations

The hero “Hear it live” CTA navigated to `#section-04` and landed on the Voice X-ray widget. The rendered live DOM exposed a `div[role="slider"]`, an actual `input[type="range"]`, and buttons “84ms STT”, “112ms Intent”, “196ms Write”, and “Replay 196ms Turn”.

The 84ms STT and 196ms Write milestone clicks were executed from the live browser. The post-click extracted state remained at `112 ms / 196ms total turn` with Layer 03 selected, so milestone state transition was not confirmed and should be treated as a likely FAIL pending a clean rerun.

The live DOM exposed the following slider semantics on the div: role=slider, aria-label “Voice X-ray millisecond scrubber (use Left and Right arrow keys to scrub)”, aria-valuemin=0, aria-valuemax=196, aria-valuenow=112, tabindex=0. The actual range input exposed min=0, max=196, value=112. The keyboard test was not conclusively completed because focus moved between the wrapper and range input during browser interaction.

## Sign-up

The deployed `/sign-up` route rendered immediately with name, work email, company/workspace, password, primary language selector, Launch My Workspace button, and Sign In link. No loading spinner or redirect loop was observed.

## Pricing

The deployed `/pricing` route displayed £49 Starter, £149 Growth, and £399 Enterprise tiers, plus £ GBP, $ USD, and Annual –20% controls and five FAQ questions. Clicking the `$ USD` and `Annual –20%` controls did not produce a visible pricing or label change in the browser state; this is a likely FAIL for functional toggles. The page text remained in GBP with monthly billing wording after both clicks.

## Global visual evidence

The desktop screenshot showed a black/void canvas with a cyan/teal accent, glassy pill controls, green browser interaction outlines, and a fixed top navigation. No `.material-symbols-outlined`, `.material-icons`, or related Material icon ligature text was found in the saved HTML parser output. The expected dark industrial visual system is present. A full-screen WebGL black-hole canvas, smooth-scroll scaling/spin, mobile viewport, reduced-motion mode, and 60fps replay timing were not independently measured in this session.

## Further interaction results

The live Section 05 route `#section-05` lands correctly and exposes four semantic tab buttons with ids `tab-dispatch`, `tab-warehouse`, `tab-support`, and `tab-erp`. The desktop view shows the expected active Dispatch module and radar/wireframe inset. Clicking the Warehouse, Customer Support, and ERP & Sheets tab controls did not produce an observable active-state or content change; the view remained `ZONE 01 / SIP, POD, DOCK / AT DISPATCH`. Treat the four-tab switching requirement as FAIL pending a clean reproduction in a non-overlay browser session.

On `/pricing`, the £49/£149/£399 tiers and GBP/USD/Annual controls are present in the DOM. Clicking `$ USD` and `Annual –20%` did not visibly change the page: prices remained GBP/monthly. Treat currency and annual billing toggles as FAIL for functional behavior, while static pricing content passes.
