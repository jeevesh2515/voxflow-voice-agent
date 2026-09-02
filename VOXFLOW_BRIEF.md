# Voxflow site bible — do not contradict

Product: Voxflow (spelling: Voxflow). Voice OS for UK freight / dispatch /
warehouse / customer / ERP-Sheets. EN + Hindi/Hinglish. eu-west-2.
Not a generic chatbot. Wedge: "Terminal sees the yard. Voxflow hears the line."

Live site to improve: <https://voxflow-voice-agent.vercel.app/>
Visual north star (motion/system, NOT logistics copy): <https://terminal-industries.com/>

Stack: keep the existing app. Vite/Next + React + TS + Tailwind.
Add: Lenis, GSAP + ScrollTrigger, SplitText/SplitType on ONE hero H1,
Three.js or one fullscreen GLSL black hole.

Look: #030308 void, ONE accent (voice-cyan #5EEAD4), white type.
Huge display type, short copy. Dent/inlay cards. No Material icon ligatures.
No rainbow. No scroll-jacked full-page snaps. Native scroll + Lenis.

Latency: ONE public number — "~200ms glass-to-glass turn, UK edge."
Hop math (84/112/196) ONLY inside the Voice X-ray widget.
Do not claim SOC 2 Type II unless a report URL is in this file (none yet — omit).
Do not claim 10x ROI without the calculator. Fake testimonials forbidden.

Section order (once, numbered 01–08):
01 Hero (hole + letter-stagger + Hear it live / Fix one workflow)
02 Problem (conversation black hole / IVR = clipboard)
03 Dual path (one line vs depot network)
04 Voice X-ray (keep, promote — unique widget)
05 Four zones: Dispatch / Warehouse / Support / ERP-Sheets
06 ROI calculator + samples (EN/US/Hindi/Hinglish)
07 Proof (named quote only, or none) + pricing teaser
08 FAQ + contact + footer

Motion: hole reacts to scroll; one pinned scene (x-ray OR 3 hops, not both);
prefers-reduced-motion = static hole, no SplitText.
Mobile = different choreography, not squashed desktop.

Conversion: /sign-up must render a form, not Loading…
Hero must have CTAs. Homepage pricing shows starting £ + 500 free min.

# VoxFlow Read-Only Research Package

**Scope:** Live homepage research only. No repository files were edited.

**Sources reviewed:** [VoxFlow live homepage][1], [Terminal Industries live homepage][2], and the live `/sign-up` route linked from VoxFlow.

## 1. VoxFlow homepage: complete top-to-bottom outline

The current VoxFlow homepage is best understood as a long-form voice-operations story. The sequence below records the visible structure in order, including the hero prelude, proof blocks, product demonstrations, conversion modules, and footer.

| Order | Section | What is present | Audit note |
| ---: | --- | --- | --- |
| 1 | Floating global navigation | VoxFlow mark, Platform, Intelligence, Economics, Pricing, Systems Live, Sign in, Get started, and mobile menu control | The nav is persistent and visually strong, but the brand link exposes the `graphic_eq` ligature in extracted text. |
| 2 | Hero visual prelude | Scroll-to-explore cue, “Signal Lock,” “16KHZ PCM,” “Latency Target <100MS,” and two numbered pre-headline statements | This reads like a cinematic intro layer rather than a fully separate section. It currently introduces numbering before the main hero. |
| 3 | Hero: Automate High-Volume Voice Operations | Multilingual voice-agent proposition, four trust badges, four voice-test buttons, trial CTA, simulator CTA, and legal/friction note | Core positioning is clear, but latency language should be normalized before launch. |
| 4 | Live Operations Console | Active calls, handled calls, orders, live agent stream, sample caller dialogue, STT/LLM/turn latency, and four proof metrics | High-value visual proof. The console is the homepage’s main product artifact. |
| 5 | Scroll-led signal narrative | “Autonomous Conversation Layer,” a large staged statement about turning chaotic phone traffic into one connected voice operating system | The current extracted text once appeared without spaces in the word reveal, so this section needs a regression check across browsers and reduced-motion mode. |
| 6 | Enterprise architecture / Three Pillars | Dual-engine multilingual voice; live CRM and Sheets sync; enterprise GDPR and eu-west-2 | The three pillars are useful, but the local `01`, `02`, `03` numbering competes with other numbered systems on the page. |
| 7 | Voice X-ray / Live Inspection | Draggable 0–196ms timeline; raw PCM; Whisper STT tokens; Llama intent matrix; live tool mutation; selected layer and confidence readout | Strong differentiator. Treat this as an interactive product proof, not a decorative animation. |
| 8 | At Dispatch | Driver check-ins, POD capture, dock reassignment, radar-node data, active trucks, pallet-bay status, intent confidence, ETA, and commit log | This is the freight-specific operational use-case layer. It should remain the anchor for the brand. |
| 9 | Real-time Telemetry | Caller POV in English and Hindi, agent responses, engine POV, PCM/STT/LLM/language-detection/Sheets commit trace, and 84ms/112ms/196ms bars | Best section for proving English–Hindi code-switching and system visibility. |
| 10 | Architecture: Four Hops | Amazon Connect; Whisper STT + Llama 3 70B; Tenant PostgreSQL + Sheets; Edge TTS + Audit Logging | Clear technical spine. The displayed “total pipeline turn” must reconcile with the latency figures elsewhere. |
| 11 | Two-way live sync | Transcript-to-tool-call examples and a frosted VoxFlow call-log / Google Sheets mirror | Useful proof of action, not just conversation. The sync status should be clearly labelled as simulated or live. |
| 12 | Multi-depot switchboard | Six hubs: London Central, Birmingham Hub, Manchester Express, Bristol Fleet, Leeds Gateway, Glasgow Freight; click/focus/hover states; caller, intent, and route-log telemetry | Strongest expression of VoxFlow as a dispatch/warehouse voice OS. |
| 13 | Outcomes / enterprise impact | Two case cards: UK dispatch operations and return velocity, each with a metric, quotation, role, and generic organization descriptor | Testimonials have roles and organization categories but no named individuals. This weakens trust. |
| 14 | ROI calculator | Daily inbound calls, average call duration, model assumptions, dynamic payback, annual savings, hours saved per month, and FTE equivalent | Conversion-relevant and interactive. Claims need a visible methodology link or a proof note. |
| 15 | Connected ecosystem | Amazon Connect, Google Sheets, Twilio SMS, PostgreSQL DB, Stripe Billing, Salesforce CRM, Slack & Teams, REST & Webhooks | The integration grid is useful; icon labels must not leak as visible text. |
| 16 | Pricing | Monthly/annual toggle; Starter, Growth, Enterprise; plan features; sign-up links; pricing comparison link | CTAs exist, but the page should make demo/contact escalation easier for enterprise visitors. |
| 17 | Testimonial block | Quote about scaling from 50 to 2,500 daily driver calls; Director of Logistics; UK Beverage & Freight Network | Strong operational specificity, but still unnamed. Verify permission and provenance before publication. |
| 18 | FAQ | UK numbers, Google Sheets sync, GDPR/data residency, and trial questions | The questions are relevant; test keyboard disclosure, focus visibility, and URL/deep-link behavior. |
| 19 | Final CTA | “Go live this week,” 14-day unlimited trial, no setup fees, trial CTA, simulator CTA | Present, but the page needs a clearer high-intent “Book a freight operations demo” path alongside self-serve sign-up. |
| 20 | Footer | Product, Company, Compliance groupings; GitHub link; Platform, Integrations, Pricing, About Us, Careers; footer contact phone; copyright | A footer is present on the live page. It is not missing, but it is light on direct enterprise conversion and support links. |

### Defect and risk flags

| Flag | Live finding | Severity | Recommendation |
| --- | --- | ---: | --- |
| Material icon words in text | Extracted page text exposes `graphic_eq`, `play_arrow`, `arrow_forward`, `arrow_outward`, `support_agent`, `record_voice_over`, `table_chart`, `shield`, `format_quote`, `call`, `table`, `sms`, `database`, `credit_card`, `sync`, `notifications`, and `api`. | High | Ensure decorative Material Symbols are `aria-hidden`, icon text is not the accessible name, and every icon-only control has an explicit accessible label. Replace visible ligature leakage in SSR/fallback output. |
| Duplicate “01” | “01 // Autonomous Voice Engine,” “01 — Autonomous Conversation Layer,” “01 / At Dispatch,” pillar “01,” and local route labels all appear. | Medium | Keep numbering local only when it is visibly scoped; otherwise use one global spine such as `01 / 08` and reserve product stage numbers for the actual narrative. |
| Conflicting latency | The page currently presents `<100ms` target, “Sub-200ms,” a 98ms console figure, 84ms STT, 112ms LLM, 196ms turn, and a separate 38ms pipeline figure in the rendered/parsed surface. `<50ms` was not found in the current homepage extract, but should be searched in shared components and future variants. | High | Publish one canonical SLA definition: for example, “196ms glass-to-glass turn, with 84ms STT and 112ms reasoning components.” Label targets, component timings, and end-to-end measurements separately. Remove or explain 98ms and 38ms. |
| Unnamed testimonials | The current proof uses role labels such as Head of Fleet Operations, Chief Financial Officer, and Director of Logistics plus generic organization descriptions. | High | Use a permissioned person name, exact company, role, and date—or change the UI to an explicitly labelled “operator outcome” without quotation marks. Do not imply a named customer endorsement when none is supplied. |
| `/sign-up` loading/route failure | Opening `https://voxflow-voice-agent.vercel.app/sign-up` redirected to `/dashboard` and showed “Loading workspaces…”, “No authorized workspace,” and “Loading dashboard…”. | Critical | Keep unauthenticated users on a real sign-up screen. Test direct navigation, refresh, expired session, and plan query strings (`?plan=starter`, etc.). Never route a new visitor into an indefinite dashboard loading state. |
| Footer and CTAs | Neither is absent in the current live homepage: footer exists, and CTAs appear in the hero, pricing cards, and final CTA. | Medium | Treat this as an incomplete conversion system rather than a missing-element bug. Add a named enterprise demo CTA, a clear contact route, and a footer-level “Book an operations review” link. |
| Copy extraction / reveal spacing | The live extracted text showed `Yourcallerhearsacalm...` in the staged narrative, while later visual QA showed the intended spaced version. | Medium | Validate the final DOM and screen reader output, not only the visual frame. Provide a non-animated readable sentence in the accessibility tree. |

## 2. Reusable system extracted from Terminal Industries

The items below describe only the reusable **interaction and visual system** from [Terminal Industries][2]. They intentionally exclude its logistics messaging, yard terminology, proof points, and brand copy.

| System element | Reusable pattern for VoxFlow | Guardrail |
| --- | --- | --- |
| Dark field | Use a near-black, spacious canvas with quiet texture, restrained noise, large negative space, and a clear focal object. | Preserve VoxFlow’s dispatch/warehouse voice-OS identity; do not imitate Terminal’s exact art direction or copy. |
| One accent | Choose one dominant signal color for the active state, CTA, timeline cursor, and key metric; keep secondary colors rare and semantic. | Use VoxFlow’s selected accent consistently rather than a multi-colour neon rainbow. A cyan or magenta system can work; do not let both compete equally everywhere. |
| Modular 01/02 paths | Present visitor intent as a small set of numbered paths with distinct outcomes and a short action label. | Make the paths about VoxFlow jobs: dispatch coverage, warehouse call handling, or ERP action—not Terminal’s yard scenarios. |
| Calculator | Let visitors enter a few operational variables, calculate a visible outcome, and offer a next-step consultation. | Show assumptions, units, range limits, and methodology. Do not present an unqualified savings number. |
| Numbered spine | Give the page a persistent progression cue so the user knows where they are in the story. | Use a single coherent sequence and ensure it remains legible on mobile. Avoid repeated “01” labels from unrelated components. |
| Scroll-follow | Use smooth, inertial movement and elements that follow scroll progress with layered parallax or pinned moments. | Scroll must remain native and reversible. No wheel hijacking, trapped sections, scroll-jacking, or inaccessible horizontal-only interaction. |
| Dent cards | Use cards with a machined indentation/dent treatment: inset shadow, border recess, clipped corner, or controlled inner bevel. | Keep content contrast high and the card surface functional; do not make the dent a substitute for information hierarchy. |
| Glow | Apply a localized glow to the current node, active route, focus state, and conversion action. | Glow must have a non-colour equivalent such as border, icon, text, or state label for low-vision and colour-blind users. |

## 3. Final headline set: freight voice OS, UK English + Hindi

These are written for VoxFlow as a dispatch/warehouse voice operating system, not as a generic AI phone product. Hindi is intentionally natural and operational rather than a word-for-word translation.

| # | English headline | Hindi headline |
| ---: | --- | --- |
| 1 | **Every freight call becomes an action.** | **हर फ्रेट कॉल सीधे कार्रवाई में बदलती है।** |
| 2 | **The voice OS for dispatch teams under pressure.** | **दबाव में काम कर रही डिस्पैच टीमों के लिए वॉइस OS।** |
| 3 | **Keep the dock moving. Let VoxFlow handle the line.** | **डॉक की रफ्तार बनाए रखें। कॉल VoxFlow संभाले।** |
| 4 | **From driver check-in to ERP commit, in one voice turn.** | **ड्राइवर चेक-इन से ERP अपडेट तक, एक ही वॉइस टर्न में।** |
| 5 | **Your warehouse hears the request. Your systems execute it.** | **वेयरहाउस अनुरोध सुनता है। आपके सिस्टम उसे पूरा करते हैं।** |
| 6 | **One operating layer for every inbound freight conversation.** | **हर इनबाउंड फ्रेट बातचीत के लिए एक ऑपरेटिंग लेयर।** |
| 7 | **Answer in English. Act in Hindi. Update the operation live.** | **अंग्रेज़ी में जवाब दें। हिंदी में कार्रवाई करें। ऑपरेशन को लाइव अपडेट करें।** |
| 8 | **Turn missed calls into confirmed loads, slots, and handoffs.** | **छूटी हुई कॉल को पक्के लोड, स्लॉट और हैंडऑफ में बदलें।** |
| 9 | **The calm voice between your driver and your control tower.** | **ड्राइवर और कंट्रोल टावर के बीच भरोसेमंद, शांत आवाज़।** |
| 10 | **Dispatch intelligence that speaks the language of the floor.** | **डिस्पैच इंटेलिजेंस जो ऑपरेशन फ्लोर की भाषा बोलती है।** |
| 11 | **Every intent routed. Every update written back.** | **हर इंटेंट सही जगह रूट। हर अपडेट सिस्टम में दर्ज।** |
| 12 | **Make high-volume voice traffic operational.** | **हाई-वॉल्यूम वॉइस ट्रैफिक को ऑपरेशनल बनाइए।** |

## 4. Dark still image shot list

The stills should be used as sparse narrative anchors, not as generic hero decoration. Each should be composed for a dark field, minimal copy overlay, and one dominant signal accent.

| # | Still concept | Composition and motion cue | Accent / production direction |
| ---: | --- | --- | --- |
| 1 | **Acoustic dispatch sphere** | Black studio void; a faceted translucent sphere made from concentric voice-wave rings and route vectors; no people, no logos, no text. | Electric cyan only. Slow 3/4 camera view; leave left-side negative space for a headline. |
| 2 | **Warehouse voice corridor** | Night warehouse aisle with dock doors fading into darkness; a single luminous waveform travels from phone handset to dock light. | Magenta only. Low camera, long exposure feel, subtle haze, realistic industrial materials. |
| 3 | **Driver check-in waveform** | Close-up of a rugged hands-free radio / phone near a loading bay; waveform geometry reflects across wet concrete. | High-voltage lime only. Editorial still, shallow depth of field, no readable UI text. |
| 4 | **ERP commit lattice** | Dark overhead plan of pallet lanes and warehouse grid; thin luminous nodes connect a call event to inventory, route, and confirmation endpoints. | Cyan only. Top-down diagrammatic composition, controlled bloom, no generic dashboard. |
| 5 | **Bilingual signal bridge** | Abstract split field: English phoneme marks on one side, Devanagari-inspired sound shapes on the other, joined by one continuous audio ribbon. | Soft violet only. Treat language forms as abstract graphic marks, not fake readable copy. |
| 6 | **Control tower through glass** | Dim operations room seen through reflective glass; one operator silhouette, a single active route line, and distant dock lights. | Warm amber only. Premium documentary tone; preserve anonymity and avoid stock-photo smiles. |

**Negative prompt for all six:** generic humanoid robot, blue-purple AI brain, smiling call-centre headset stock photo, floating random code, fake brand logos, illegible UI text, excessive lens flare, busy gradient background, truck hero cliché.

## 5. Future-section QA checklist

Use this matrix as a release gate for every new section. “Pass” means tested at desktop and mobile widths, with motion enabled and `prefers-reduced-motion: reduce` enabled.

| Future section | Motion QA | Mobile QA | Accessibility QA |
| --- | --- | --- | --- |
| Global nav / numbered spine | Scroll-follow never traps the page; reverse scroll returns cleanly; active marker changes within 0.6–1.2s. | Menu opens without layout shift; nav does not cover hero copy or controls; tap targets at least 44px. | Landmark navigation; visible focus; current section exposed to screen readers; decorative icon ligatures hidden. |
| Visual-first hero | WebGL pauses offscreen; pointer parallax has no dead zone; no camera rotation behind the scene; reduced motion shows a stable still. | Canvas keeps aspect ratio; no horizontal overflow; headline and CTAs remain above the fold; GPU load is reasonable on mid-range mobile. | Hero has one real H1; canvas is `aria-hidden`; all actions have text labels; contrast remains readable over the scene. |
| Voice persona controls | Click gives immediate state feedback; pulse/equalizer timing is deterministic; stop/replay behavior is clear. | Pills wrap without collisions; audio controls remain thumb-friendly; no autoplay. | Keyboard activation; `aria-pressed` or equivalent state; spoken language announced; audio permission/failure communicated. |
| Proof metrics / console | Numbers animate once and settle; no infinite high-cost animation when offscreen. | Console can stack without clipping; latency labels do not overlap. | Metrics have text labels and units; no meaning conveyed by colour alone; live region used sparingly. |
| Scroll narrative | Scroll-follow is progressive, reversible, and not wheel hijacking; word reveal has a non-animated fallback. | Copy does not become too large or cut off; pinned duration remains tolerable. | Full sentence available in DOM; screen reader order is logical; focus never moves unexpectedly. |
| Pillars / architecture | Staggered reveals are 0.6–1.2s and pause offscreen. | Cards become a readable single-column sequence; no hover-only information. | Heading hierarchy is unique and sequential; card controls are not fake buttons; icons have labels or are hidden. |
| Voice X-ray | Scrubber updates all four layers synchronously; keyboard arrows and pointer dragging work; no scrubber scroll lock. | Timeline is reachable and usable with touch; readout wraps; no tiny 10px-only controls. | Range has label, min/max/value; selected layer announced; confidence and latency exposed as text. |
| Dispatch telemetry | Simulated events do not imply real live data unless labelled; animation stops when inactive. | Logs horizontally scroll only inside a labelled region; vital status appears before detail. | Table headers and row relationships; intent/state text not colour-only; phone numbers masked. |
| Pipeline / Sheets mirror | Active hop follows scroll without desync; simulated commits have a clear cadence. | Four hops collapse vertically; spreadsheet remains legible at 320px. | Use semantic list/table markup; identify simulated/live state; do not expose fake status as an ARIA live stream. |
| Multi-depot switchboard | Hover, click, focus, and touch all select the same hub; focus state persists after pointer leaves. | Six hubs stack with no accidental activation; focused telemetry appears near selected hub. | Buttons have accessible names; active hub announced; route log is text; colour contrast checked for every state. |
| ROI calculator | Sliders update outputs without lag; calculations show stable rounding; no animated number deception. | Range controls are easy to drag; values and units stay visible; output cards do not reorder confusingly. | Labels are associated; keyboard range control works; assumptions, formula, and currency are disclosed; no financial guarantee language. |
| Pricing / testimonials | Billing toggle preserves focus and does not jump the page; CTA hover never hides label. | Cards become a comparison list; primary CTA stays visible; testimonial quote does not create overflow. | Plan buttons have unique names; quote attribution is truthful and permissioned; no unnamed endorsement presented as verified proof. |
| FAQ / final CTA / footer | Disclosure transition is reversible and respects reduced motion; final CTA enters once. | Accordion rows are easy to tap; footer columns collapse logically; contact route is visible. | Native disclosure semantics or equivalent; focus moves predictably; footer landmarks and link purpose are clear; sign-up error states are actionable. |
| `/sign-up` and auth boundary | Loading has a timeout/error state; direct URL and refresh are tested; no redirect loop. | Form fits narrow screens and preserves entered values after validation errors. | Unauthenticated visitors see a real sign-up route; errors are announced; loading is not the only content; plan query string is retained. |

## References

[1]: https://voxflow-voice-agent.vercel.app/ "VoxFlow Voice Agent live homepage"

[2]: https://terminal-industries.com/ "Terminal Industries live homepage"
