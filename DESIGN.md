# VoxFlow — Design System

**Status:** Documents the design system already implemented in
`apps/web/tailwind.config.ts` and `globals.css` — this file exists so
future changes stay consistent, not to propose a new direction.

---

## 1. Visual Identity

VoxFlow's dashboard uses a **dark-mode-first, neon/cyberpunk-adjacent**
aesthetic — appropriate for a "live voice ops center" feel (glowing
borders, scanline overlay, glassmorphism panels). A light mode variant
exists as a secondary, more conventional theme.

## 2. Color Palette

### Dark mode (default)

| Token | Hex | Usage |
|---|---|---|
| `primary` | `#ff2d78` | Magenta/pink — primary accent, active states, glow effects |
| `secondary` | `#00ffcc` | Cyan — secondary accent, success/live indicators |
| `tertiary` | `#ffe04a` | Yellow — warnings, highlights |
| `background` | `#0a0a12` | Page background |
| `surface` | `#0f0f1a` | Card/panel background |
| `surface-container` | `#141422` | Nested containers |
| `surface-container-high` / `-highest` | `#28283e` | Elevated surfaces |
| `surface-variant` | `#1e1e30` | Muted backgrounds |
| `surface-bright` | `#1a1a2e` | Slightly lifted surface |
| `surface-dim` | `#0f0f1a` | Dimmed surface |
| `outline` | `#5a5068` | Borders (default) |
| `outline-variant` | `#302840` | Subtle borders |
| `on-surface` | `#e8e0f0` | Primary text on dark surfaces |
| `on-surface-variant` | `#a098b0` | Secondary/muted text |
| `on-primary` | `#1a0010` | Text on primary-colored elements |
| `on-tertiary` | `#1a1000` | Text on tertiary-colored elements |
| `on-error-container` | `#ffa0a0` | Text on error containers |
| `error` | `#ff4444` | Error states |
| `success.500` | `#00ffcc` | Success states (aliases secondary) |
| `warn.500` | `#ffe04a` | Warning states (aliases tertiary) |
| `danger.500` | `#ff4444` | Danger states (aliases error) |

### Light mode

| Token | Hex | Usage |
|---|---|---|
| Background | `#f8fafc` | Page background |
| Text | `#0f172a` | Primary text |
| Accent | `#e11d48` | Rose — replaces neon primary in light mode |
| Glass panel border | `#e2e8f0` | Card borders |
| Glass panel background | `rgba(255,255,255,0.9)` | Card background with blur |

**Rule:** any new UI component must pull colors from these existing
Tailwind tokens (`bg-primary`, `text-on-surface`, etc.) — never hardcode a
new hex value without adding it to `tailwind.config.ts` and this table
first.

## 3. Typography

| Role | Font | Tailwind class | Usage |
|---|---|---|---|
| Headline / Display | Sora | `font-headline`, `font-display` | Page titles, hero text, dashboard section headers |
| Body | Inter | `font-body`, `font-sans` (default) | Paragraph text, general UI copy |
| Label / Monospace | Space Grotesk | `font-label`, `font-mono` | Data labels, call transcripts, technical/numeric values (SKUs, order IDs, timestamps) — fits the "ops console" feel |

**Rule:** transcripts, SKU codes, phone numbers, and order/shipment IDs
should use the monospace label font (`font-label`) to reinforce the
technical/data nature of that content, distinct from conversational
agent-reply text which can stay in body font.

## 4. Visual Effects (already implemented, reuse don't reinvent)

- **`.neon-text` / `.neon-text-sm`** — text-shadow glow using
  `currentColor`, for emphasis text (e.g. live call status, key metrics)
- **`.neon-border` / `.neon-border-card`** — glowing border with hover
  intensification, used for interactive cards
- **`.glass` / `.glass-strong`** — backdrop-blur translucent panels, for
  overlays and elevated cards
- **`.grid-bg`** — subtle grid + radial gradient background texture
- **`.noise`** — SVG fractal noise texture overlay for subtle grain
- **Scanline overlay** — dark-mode-only `body::after` repeating gradient,
  reinforces the "monitoring console" feel — do not apply in light mode
- **`boxShadow.glow`** — `0 0 20px rgba(255,45,120,0.4), inset 0 0 12px
  rgba(255,45,120,0.1)` — for primary CTA buttons or the "live call"
  indicator

## 5. Border Radius

Intentionally small/sharp, not the typical rounded-SaaS look:

| Token | Value |
|---|---|
| default | `0.125rem` |
| `lg` | `0.25rem` |
| `xl` | `0.5rem` |
| `2xl` | `1rem` |
| `3xl` | `1.5rem` |

This reinforces the technical/console aesthetic over a soft consumer-app
feel — keep new components consistent with this (avoid `rounded-full` or
large rounded corners unless there's a specific reason, e.g. avatars).

## 6. Live/Real-Time Indicators

Since VoxFlow's core value is real-time call handling, live-state UI
deserves particular consistency:

- **Active call:** use `secondary` (`#00ffcc`) with a pulse/glow animation
- **Escalated call:** use `error`/`danger.500` (`#ff4444`)
- **Pending/in-progress:** use `tertiary`/`warn.500` (`#ffe04a`)
- **Resolved/completed:** use muted `on-surface-variant` gray

Keep this mapping consistent across `/dashboard/calls`, the simulator, and
any future real-time status components — a color meaning "escalated" in
one view and something else in another undermines the ops-console trust
the design is going for.

## 7. Open Items (not yet decided — flag before implementing)

- No documented icon set/library confirmed in use — check
  `apps/web/package.json` before introducing a new one
- No documented spacing scale beyond Tailwind defaults — if a custom
  scale is needed, add it to `tailwind.config.ts` and this file together
