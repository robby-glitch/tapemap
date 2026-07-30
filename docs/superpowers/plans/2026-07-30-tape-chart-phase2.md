# Tape Chart Phase 2 — Narration on the Chart (+ light theme)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** The Kite-style hover callout carrying each candle's narration, the ribbon beneath the chart, and a **light** reading surface — because the operator reads charts in Kite on the light theme and reported the dark build as unreadable and cramped.

**Design source of truth:** the approved mockup *"Contract Tape — narration on the chart"* (artifact `53ed3308`, published 2026-07-29). Its light palette and callout structure are copied verbatim below — do not invent alternatives.

**Architecture:** Narration is **presentation only** (spec §6 Phase 2: *"Narration content comes from the existing event stream; this phase is presentation, not analytics"*). A new `trade/narration.ts` joins the payload's existing events to bars on `t` and assigns a tier; nothing is computed about the market. The callout is plain React positioned over the chart; hover comes from the engine's `xToTime` converter. Phase 3+ (zones, translated levels, position lines) stays out.

## Global Constraints

- Branch `feature/dashboard-v2`. Never touch `ui/` (separate v1 frontend) or any `.py` file. `ui-v2/src/vendor/candl/` is PRISTINE.
- `pnpm` is not on PATH — always `corepack pnpm`.
- Gates each commit: `corepack pnpm --dir ui-v2 exec tsc --noEmit` · `corepack pnpm --dir ui-v2 build` · `python -m pytest -q` (43).
- **Honesty rules still bind.** Narration text is quoted from the event stream, never paraphrased into a stronger claim. A bar with no event says so plainly ("no event on this bar") rather than inventing a story. Every evidence line names real numbers from the payload.
- **UI renders, engine decides.** `narration.ts` may group, tier and format. It must not compute a rank, an average, or any market analytic.

## Light palette — copied verbatim from the approved mockup

```
ink #141A22 · dim #5C6675 · faint #98A2B0
bg #F7F8FA · panel #FFFFFF · panel2 #FBFCFD · line #E3E7ED · line2 #D2D9E2
brass #A9762A · brass-dim #B98F45     (darkened for legibility on white)
up #1B8A38 · down #C42B30              (darkened for legibility on white)
grid rgba(0,0,0,.05) · tip bg #FFFFFF · tip shadow 0 8px 26px rgba(20,26,34,.16)
```

Note the mockup deliberately darkens brass/up/down for the light surface. Do not reuse the dark palette's `#E0A852` / `#2EC27E` / `#FF5F6B` on white — they fail against it.

---

### Task 1: `theme.ts` — a second palette and a mode hook

**Files:** modify `ui-v2/src/theme.ts`.

- Keep the existing `T` export exactly as it is (the dark palette; the rest of the app reads it and must not change).
- Add `export const TL = { … }` with the light values above, same key names as `T` so components can hold either.
- Add `export type Mode = 'light' | 'dark'` and `export function palette(m: Mode) { return m === 'light' ? TL : T }`.
- Add `export const CHART_UP = { light: '#1B8A38', dark: '#2EC27E' }` and `CHART_DOWN = { light: '#C42B30', dark: '#FF5F6B' }` for the engine's `setSettings`.
- Add a tiny persisted-mode hook so the toggle survives a refresh, defaulting to **light**:

```ts
export function useMode(): [Mode, (m: Mode) => void] {
  const [mode, setMode] = useState<Mode>(() =>
    (localStorage.getItem('tape.mode') as Mode) || 'light')
  const set = (m: Mode) => { localStorage.setItem('tape.mode', m); setMode(m) }
  return [mode, set]
}
```

(import `useState` from react in this file).

---

### Task 2: `trade/narration.ts` — join the existing events to bars

**Files:** create `ui-v2/src/trade/narration.ts`.

**Produces:** `export type Tier = 0 | 1 | 2 | 3`, `export interface Narration { kind: string; head: string; ev: string; tone: 'bull' | 'bear' | 'neutral' | 'structure'; tier: Tier }`, and `export function buildNarration(bars: TapeBar[], events: EventItem[]): (Narration | null)[]` — one entry per bar, aligned 1:1, `null` when that minute carried no event.

Rules:
- Join on `t` — `EventItem.time` against `TapeBar.t`. Several events can share a minute; keep the highest-tier one and append `+N more` to its `ev`.
- Tier by the event's own kind, most consequential first: `3` = TRAP-SPRUNG, SPRING, SQUEEZE-RELEASE, ABSORPTION, IGNITION · `2` = DIVERGENCE, BREAK, BAND-REVERSAL, WALL-MIGRATION, ROLE-FLIP · `1` = STATE, CHOP, everything else · `0` = no event.
- `tone` from the event's existing `dir` (`bull`/`bear`/`neutral`); use `'structure'` for wall/role/level kinds so they render brass, not green/red — colour keeps one meaning.
- `kind` is the event's own tag, title-cased for display. `head` is the event's own message, first sentence. `ev` is the remainder plus the bar's own numbers formatted from the payload (`Vol`, `OI` and its change vs the previous bar). **Do not rewrite the message into a stronger claim.**
- A bar with no event returns `null`; the callout renders "no event on this bar — OHLC only" for it. Never fabricate a narrative.

---

### Task 3: `trade/Callout.tsx` — the hover box, to the mockup

**Files:** create `ui-v2/src/trade/Callout.tsx`.

**Props:** `{ mode: Mode; bar: TapeBar; prevBar: TapeBar | null; day: string; narr: Narration | null; x: number; y: number; boxW: number; boxH: number }` where `x`/`y` are cursor position inside the chart frame and `boxW`/`boxH` the frame size for edge-flipping.

Structure, matching the mockup exactly (two sections divided by a `line` border, `min-width: 252px`, `max-width: 312px`, radius 8, the mockup's shadow):

1. **OHLC block** — `padding: 9px 11px 8px`:
   - date + time, `11px`, `faint`, mono — `dd/mm/yyyy HH:MM`
   - the close, `20px`, weight 660, mono, letter-spacing -.02em
   - a 2×2 mono grid (`gap: 1px 14px`, `11.5px`): `OPEN` `HIGH` / `CLOSE` `LOW`, labels `faint`, values weight 560
   - `VOLUME` row and `OPEN INTEREST` row, `11.5px`, label left / value right (`justify-content: space-between`); OI shows the value **and its change vs the previous bar** (`+80k` style), `null`-safe when `prevBar` is null.
2. **Narration block** — `padding: 9px 11px 10px`:
   - `kind` — `10px`, letter-spacing .11em, uppercase, weight 700
   - `head` — `13px`, weight 580, line-height 1.35
   - `ev` — `11px`, `dim`, line-height 1.45
   - Border and `kind` colour follow `tone`: bull → up, bear → down, structure → brass, neutral → default line colour.

Positioning: `left = x + 20`, `top = y - boxH/2`, flipped to `x - w - 20` when it would overflow the right edge, clamped ≥6px on every side. `pointer-events: none`.

---

### Task 4: `trade/Ribbon.tsx` — the day's shape at a glance

**Files:** create `ui-v2/src/trade/Ribbon.tsx`.

Spec §6: *"the ribbon beneath the chart (one tick per candle, height by tier) so the day's shape reads at a glance."*

**Props:** `{ mode: Mode; narrs: (Narration | null)[]; cursor: number | null; hover: number | null; onHover: (i: number | null) => void; onScrub?: (i: number) => void }`

- A flex row of one thin tick per bar, height by tier: `0` → 3px, `1` → 6px, `2` → 11px, `3` → 16px, in a fixed 20px track so the row never reflows.
- Tick colour from `tone` (bull/bear/structure/neutral), tier-0 ticks in `faint` at low opacity — quiet minutes stay visible but recede.
- The bar under the cursor (replay) gets a 1px brass outline; the hovered bar brightens. Hovering a tick calls `onHover(i)` so the chart's callout follows the ribbon too.
- Bars after the replay cursor render at 25% opacity — the ribbon must be causal like everything else.

---

### Task 5: light-mode chart + hover + right-axis level tags

**Files:** modify `ui-v2/src/trade/ContractChart.tsx`, `ui-v2/src/trade/LevelsOverlay.ts`.

`ContractChart`:
- New props `mode: Mode`, `hover: number | null`, `onHover: (i: number | null) => void`, `narrs: (Narration | null)[]`.
- Pass `theme: mode` into `createChartEngine`, and call `engine.setTheme(mode)` in an effect on `mode`. Feed `setSettings` from `CHART_UP[mode]` / `CHART_DOWN[mode]`.
- Hover: a `mousemove`/`mouseleave` listener on the container. Map `clientX` → container-relative x → `conv.xToTime(x)` → nearest bar index by `t`, clamped to `[0, bars.length-1]` and to the replay cursor when scrubbing (never reveal a hidden future bar). Call `onHover(i)`; render `<Callout>` when `hover != null`.
- Keep everything already verified: the `index`/`day`/`n` identity guard, the two-call rollover, `setReplayCursor`, the ResizeObserver (load-bearing — see its comment), and the overlay lifecycle.

`LevelsOverlay`:
- Take a `mode` argument (or a `getMode()` getter, consistent with `getLevels()`), and pick brass/red from the light or dark palette accordingly. Include `mode` in the redraw signature.
- Add the mockup's **right-axis price chip**: a filled brass rect just inside the right edge of the pane with the level's price in `panel`-coloured mono, so a level is readable at the axis as well as by its left label. Keep the legend-band suppression and the 11px collision rule for the left labels.

---

### Task 6: `TradeTab` — light surface, toggle, legend, breathing room

**Files:** modify `ui-v2/src/trade/TradeTab.tsx`.

- Call `useMode()`; hold `hover` state; build `narrs` once with `useMemo`.
- Paint the tab on the mode's `bg`, the stat strip and chart frame on `panel` with `line` borders. Every colour comes from `palette(mode)` — no literal hex.
- A **Light / Dark** toggle in the stat strip's right end, beside the LIVE/REPLAY/STALE pill.
- **Breathing room** (the operator's complaint):
  - the stat strip becomes one compact row, `11px` labels, `13px` values;
  - the chart frame gets the remaining height, minimum 420px;
  - `<Ribbon>` sits directly beneath the chart frame, then a one-line legend (VWAP & σ bands · levels · OI) in `dim` at `11px`.
- Keep the date-precision disclosure, the STALE line, the loading state and the no-tape notice — all re-coloured for the mode.

---

### Task 7: verify in the browser, then document

- Light is the default on a fresh load; the toggle flips both the React chrome and the engine, and survives a refresh.
- Hovering the chart shows the callout with the payload's real OHLC/volume/OI, and narration text that appears verbatim in `/api/data`'s event stream for that minute.
- A minute with no event says "no event on this bar", never invents one.
- The ribbon shows one tick per bar, taller on event minutes, dimmed past the replay cursor.
- Paint stays healthy (≥100 rAF/s) with the callout following the cursor.
- Then update `context/ui-v2-dashboard.md` (Tabs entry, build history, open items) and record that Phase 2 is presentation-only.
