# UI audit — v2 dashboard, 2026-08-06

**Score: 10/20 — Acceptable, significant work needed.** The 2026-08-04 audit
scored 7/20; these are the same seven items re-measured, plus what the live
measurement added.

**Nothing here has been fixed.** The operator's decision, 2026-08-06: *"changes
live market mein karenge"* — every fix below waits for a live session, because a
trading screen is the wrong thing to re-style against a closed market and a tape
serving placeholder data.

Measured live on `localhost:5173` against a real backend, plus `detect.mjs` over
all of `ui-v2/src`. Contrast is alpha-composited through every ancestor
background — the first pass did not blend `wash()`'s rgba and produced three
false 1.00 ratios, which are excluded here.

| # | dimension | score | key finding |
|---|---|---|---|
| 1 | Accessibility | 1/4 | 1 ARIA attribute in the whole app; no focus indicator on 22 buttons |
| 2 | Performance | 3/4 | `transition: all` x3 and `transition: width 350ms` |
| 3 | Responsive | 1/4 | zero `@media`; measured overflow (669px content, 520px viewport) |
| 4 | Theming | 2/4 | real token system, but 22 hard-coded hex values bypass it |
| 5 | Implementation integrity | 3/4 | 7 detector findings, all isolated |

## Implementation integrity — PASS

Not interchangeable with any other product. Every non-trivial comment cites a
measured date and its consequence; the honesty rules are enforced in code rather
than described in docs (`rotDrawPlan` counts withheld signals under three
separate reasons; `STRUCT_ZONE_LIMIT` is disclosed in the legend). No false
positives in the detector run.

## Findings

### P1 · Contrast — 4 verified WCAG AA failures (1.4.3)

| text | size | ratio | needs |
|---|---|---|---|
| `MAX PAIN 24000 · +140` | 10.5px | **3.72** | 4.5 |
| `⟳ TOKEN` | 10.5px/700 | **3.93** | 4.5 |
| `23900` (CHANGES IF) | 12.5px | **3.95** | 4.5 |
| `23808` (CHANGES IF) | 12.5px | **3.95** | 4.5 |

Brass `rgb(169,118,42)`, caution `rgb(180,83,9)`. Ten more strings sit at
4.38–4.45 — under, but borderline.

**Why it matters more than a ratio.** `23900` and `23808` are the two numbers in
the CHANGES IF band that say when the thesis breaks. The least readable colour on
the screen is carrying the thing that has to be read first. Fix: darken brass to
about `#8A5F1F` (≈4.6:1), or raise the 10.5px chips to 12px+. → `/impeccable colorize`

### P1 · No focus indicator
22 `<button>` in `ui-v2/src`, 3 focus/outline declarations total. WCAG 2.4.7.
Keyboard navigation gives no sign of position. → `/impeccable harden`

### P1 · One ARIA attribute, app-wide
26 `onClick` vs 22 `<button>` (≈4 clickable non-buttons); 1 `aria-*`/`role`.
No `role="tablist"` on the tab bar, no `aria-live` on the price region — a
screen reader is not told when the NOT LIVE banner changes. WCAG 4.1.2.
→ `/impeccable harden`

### P2 · No `prefers-reduced-motion` alternative
0 occurrences against 5 live `transition` declarations. WCAG 2.3.3.
→ `/impeccable animate`

### P2 · Layout-property animation
`App.tsx:1322` `transition: 'width 350ms ease'`; `App.tsx` 1151, 1232, 2059
`transition: 'all 150ms'`. `all` will silently pick up any layout property added
later. Fix: `width` → `transform: scaleX()`; `all` → an explicit list.
→ `/impeccable optimize`

### P2 · 22 hard-coded hex values bypass the token system
`App.tsx` · `proto/ProtoChart.tsx` · `trade/ContractChart.tsx` ·
`trade/indicators.ts` · `trade/LevelsOverlay.ts`. `theme.ts` + `usePalette()` is
a real system and is widely used; these 22 sit outside it, mostly in chart and
overlay code where the hook was not in scope. They will not follow a theme
change. (2026-08-04 counted ~30, so this is moving.) → `/impeccable extract`

### P2 · Zero `@media`, and a measured horizontal overflow
Content 669px in a 520px viewport. **This is not straightforwardly a defect:**
PRODUCT.md states *"Desktop only in practice. No mobile usage scene exists for
this tool."* Two facts point the other way — `vite.config.ts` sets
`host: '0.0.0.0'` deliberately, and on 2026-08-06 the operator was viewing the
dashboard at `192.168.29.165:5173`, i.e. from another machine.

**Owed decision:** if off-machine viewing is a real use case this is P1; if it is
not, `host` should become `localhost` so the intent is stated in the code.
→ `/impeccable adapt`

### P2 · Numbers are not tabular
`index.css:29` Inter, `:53` Roboto; `tabular`/`font-variant-numeric` appears
twice in the entire app. Not cosmetic: with proportional digits `23,860` and
`23,808` are different widths, so ticking numbers jitter and columns do not
align. PRODUCT.md already says *"a terminal needs tabular figures"*.
`font-variant-numeric: tabular-nums` fixes it without changing the face.
→ `/impeccable typeset`

### P3 · Four side-tab accent borders
`App.tsx` 1148, 1306 · `trade/Callout.tsx` 177, 223 — all `borderLeft: 3px solid`.
→ `/impeccable polish`

### P3 · 999 kB single chunk (302 kB gzip)
Localhost tool, loaded once a day. Effectively no user impact.

## Patterns

1. **Accessibility never got a pass at all** — focus, ARIA and reduced-motion are
   all near zero. One missing pass, not three separate bugs.
2. **The token system was built, then chart code went around it.** Most of the 22
   hex values are in chart/overlay files where `usePalette()` was not available.
3. **The lowest-contrast colour carries the highest-stakes numbers.** Brass was
   treated as secondary; it is holding the invalidation levels.

## What is working

- Honesty rules enforced as architecture: `rotDrawPlan`'s three withheld-reason
  counts; the 2026-08-06 split of reachable-vs-no-data in the NOT LIVE banner.
- A real token system — `theme.ts`, `usePalette()`, `wash()` — used broadly.
- Placeholder data never impersonates live: struck-through price, `placeholder`
  label, `DO NOT TRADE FROM THIS SCREEN`.
- Zero `will-change` abuse; `useMemo` used where it earns its keep.

## Not measured — stated rather than implied

- **Viewport above 520px.** The browser pane could not be widened, so whether the
  overflow persists at 1280px is unverified.
- **OS dark mode.** With `prefers-color-scheme: dark` the body stayed light
  (`rgb(247,248,250)`), so the OS setting is ignored and the mode is a manual
  persisted toggle. That may well be deliberate, so it is not filed as a finding.

## Order to work in

1. P1 `/impeccable harden` — focus indicators, ARIA (tablist, `aria-live`)
2. P1 `/impeccable colorize` — brass and caution to AA
3. P2 `/impeccable typeset` — `tabular-nums` on every numeric surface
4. P2 `/impeccable optimize` — the four transitions
5. P2 `/impeccable extract` — 22 hex values into `theme.ts`
6. P2 `/impeccable adapt` — after the `0.0.0.0` decision
7. P3 `/impeccable polish` — the side-tab borders, final pass
