# Tape Chart Phase 1 — Index Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new `Trade` tab in `ui-v2/` that renders the index FUT tape — candles, VWAP + six σ bands, an OI pane, and every level TapeMap already knows — on the vendored CandL charting engine, with causal replay. No new backend.

**Architecture:** The CandL library (`rahulsangam7/Candl`, Apache-2.0) is vendored from source at a pinned commit into `ui-v2/src/vendor/candl/` and kept pristine; all our code lives in `ui-v2/src/trade/`. Data comes verbatim from `/api/data` (per-bar `fut` leg: `o h l c v oi vwap u1 d1 u2 d2 u3 d3`) via a new `tapeBars()` selector on `useLiveData` — full-day, non-truncated — while replay is driven by CandL's `setReplayCursor(index)`, which clips every series-derived layer causally. Levels reuse the already-honest `Dataset.MAP` (pivots, walls, PIN, floor/cap, VWAP, ±1σ, session hi/lo, traps), drawn on an overlay canvas via `getMainConverters()`. The browser computes nothing: every number on the chart comes from the payload; the frontend only reshapes.

**Tech Stack:** React 19 + Vite 8 + TS 5.7 (existing `ui-v2/`), vendored CandL charts (canvas, zero runtime deps, React ≥17 peer — satisfied).

**Prerequisite (already landed):** `session_json()` on `main` (`c91c9d5`, merged into this branch) now emits every FUT bar; a missing option leg is `null`, never a dropped row. The FUT series is complete.

## Global Constraints

- Branch: `feature/dashboard-v2`. Never edit `ui/` from this branch.
- The vendored tree `ui-v2/src/vendor/candl/` stays **pristine** — any change we need goes in a sibling file under `ui-v2/src/trade/`, never inline (spec §3).
- UI renders, engine decides (invariant #6): the browser never computes VWAP, a band, or any indicator value — `trade/indicators.ts` is pure reshaping of server arrays.
- Honesty rules (context/ui-v2-dashboard.md): a fallback must never look like live data; a dead index says so at full width; guard NaN at the source; replay must be causal.
- Colour carries one meaning: **brass `#E0A852` is structure** (levels, bands, VWAP); green/red are direction only (App.tsx `T` tokens).
- `pnpm` is not on PATH — always `corepack pnpm`.
- Gates before every commit: `corepack pnpm --dir ui-v2 exec tsc --noEmit` · `corepack pnpm --dir ui-v2 build` · `python -m pytest -q` from repo root (43 tests).
- Upstream pin: `https://github.com/rahulsangam7/Candl` @ `538938105834d9231860d639e4b03956e5f3dd67` (verified 2026-07-30: `@candllabs/charts` 0.1.0, Apache-2.0, `files: [dist,…]` — not installable from npm or git URL, hence vendoring from source).
- Verified engine API (from that commit): `createChartEngine(container: HTMLElement, options: ChartEngineOptions): IChartEngine`; `setData(candles: Candle[])`, `updateLast(candle)` (replaces last if same open time, else appends; auto-scrolls at right edge), `setIndicators(IndicatorRenderData[])`, `setReplayCursor(index: number | null)`, `getMainConverters(): Converters | null`, `getMainPaneRect(): {x,y,width,height} | null`, `scrollToTime(ms)`, `resize()`, `destroy()`. `Candle = { time /*epoch ms*/, open, high, low, close, volume }`. `IndicatorRenderData = { instanceId, label, placement: 'overlay'|'pane', outputs: IndicatorOutput[], range? }`, `IndicatorOutput = { name, values: (number|null)[] /*1:1 with candles*/, color, style? }`. `ChartType` includes `'candles'`. `Theme = 'dark' | 'light'`.

---

### Task 1: Vendor the CandL engine

**Files:**
- Create: `ui-v2/src/vendor/candl/**` (upstream `src/` copied verbatim — 55 files)
- Create: `ui-v2/src/vendor/candl/LICENSE`, `ui-v2/src/vendor/candl/NOTICE` (Apache-2.0 attribution)
- Create: `ui-v2/src/vendor/VENDOR.md`
- Modify: `ui-v2/.gitignore` (currently `node_modules` + `dist`)
- Modify (contingency only): `ui-v2/tsconfig.json`

**Interfaces:**
- Consumes: nothing from this repo.
- Produces: importable modules `../vendor/candl/chart/engine` (`createChartEngine`), `../vendor/candl/chart/types` (`IChartEngine`, `IndicatorRenderData`, `ChartEngineOptions`), `../vendor/candl/core/types` (`Candle`, `Theme`), `../vendor/candl/drawings/types` (`Converters`) — used by Tasks 3–5.

- [ ] **Step 1: Clone upstream at the pinned commit**

```bash
cd "$SCRATCH"   # any scratch dir OUTSIDE the repo
git clone https://github.com/rahulsangam7/Candl candl-upstream
cd candl-upstream
git -c advice.detachedHead=false checkout 538938105834d9231860d639e4b03956e5f3dd67
git rev-parse HEAD
```

Expected: `538938105834d9231860d639e4b03956e5f3dd67`. If the checkout fails because history moved, stop and report — do not vendor an unpinned tree.

- [ ] **Step 2: Copy `src/`, LICENSE and NOTICE into the vendor tree**

```bash
cd "/c/Users/kaam/Desktop/new tool nifty"
mkdir -p ui-v2/src/vendor/candl
cp -r "$SCRATCH/candl-upstream/src/." ui-v2/src/vendor/candl/
cp "$SCRATCH/candl-upstream/LICENSE" "$SCRATCH/candl-upstream/NOTICE" ui-v2/src/vendor/candl/
ls ui-v2/src/vendor/candl   # expect: alerts chart components core data drawings index.ts indicators lab LICENSE NOTICE
```

Do **not** copy `examples/`, `package.json`, or config files — only `src/` contents plus the two licence files.

- [ ] **Step 3: Write `ui-v2/src/vendor/VENDOR.md`**

```markdown
# Vendored libraries

## candl/ — CandL Charts

- Upstream: https://github.com/rahulsangam7/Candl (`@candllabs/charts`)
- Commit: 538938105834d9231860d639e4b03956e5f3dd67 (vendored 2026-07-30)
- License: Apache-2.0 — LICENSE and NOTICE are inside `candl/` as the licence requires.
- Why from source: the package is not on npm (`@candllabs/charts` 404s) and its
  `files` field ships only `dist`, so a git-URL install would depend on their
  build running. Vite compiles the source with our app instead.

**This tree is pristine.** Never edit a file under `candl/`. Any change we need
goes in a sibling file under `ui-v2/src/trade/`, so we can still diff against
upstream when it releases. To re-vendor: clone upstream, check out the new
commit, re-copy `src/` + LICENSE + NOTICE, update this file.
```

- [ ] **Step 4: Add `.vite/` to `ui-v2/.gitignore`**

```
node_modules
dist
.vite
```

(The untracked `ui-v2/.vite/` dir in `git status` is Vite's dep cache — it must never be committed.)

- [ ] **Step 5: Run the type gate**

Run: `corepack pnpm --dir ui-v2 exec tsc --noEmit`

Expected: clean, **or** unused-variable errors coming only from `src/vendor/candl/**`. Upstream compiles with `noUnusedLocals: false, noUnusedParameters: false` (verified in their tsconfig); ours has both `true`.

- [ ] **Step 6 (only if Step 5 shows vendor-only unused errors): relax the two flags**

In `ui-v2/tsconfig.json` set:

```json
    "noUnusedLocals": false,
    "noUnusedParameters": false,
```

with this comment above them: `// vendored candl compiles with these off (see src/vendor/VENDOR.md); vendor files must not be edited`. Any **other** class of error (type errors, missing modules): stop and report — do not patch vendor files.

Re-run: `corepack pnpm --dir ui-v2 exec tsc --noEmit` — expected clean.

- [ ] **Step 7: Run the build + python gates**

```bash
corepack pnpm --dir ui-v2 build          # expected: built without errors
python -m pytest -q                      # expected: 43 passed
```

- [ ] **Step 8: Commit**

```bash
git add ui-v2/src/vendor ui-v2/.gitignore ui-v2/tsconfig.json
git commit -m "feat(ui-v2): vendor CandL charting engine @5389381 (Apache-2.0, source-compiled)"
```

---

### Task 2: `tapeBars()` — the full-day FUT series out of the data layer

**Files:**
- Modify: `ui-v2/src/data.ts` (add `TapeBar` after `ChartPoint` ~line 104; add selector inside `useLiveData` ~line 970; extend its return ~line 975)

**Interfaces:**
- Consumes: the retained raw payload `raw[k].D` (shape: `{ days: [{ day, bars: [{ t, fut: { o,h,l,c,v,oi,vwap,u1,d1,u2,d2,u3,d3, … } | null, ce, pe }], … }] }`).
- Produces: `export interface TapeBar { t: string; o: number; h: number; l: number; c: number; v: number; oi: number; vwap: number; u1: number; d1: number; u2: number; d2: number; u3: number; d3: number }` and `tapeBars(k: IndexKey): { day: string; bars: TapeBar[] }` on the `useLiveData` return — **full day, never truncated by replay** (CandL's replay cursor does the clipping; that is what keeps the time axis fixed). Tasks 3, 6, 7 rely on these exact names.

- [ ] **Step 1: Add the `TapeBar` type** (after the `ChartPoint` interface)

```ts
// Tape Chart — one FUT bar, verbatim from the payload. The engine computed
// every field server-side (invariant: UI renders, engine decides); this type
// only names what arrives. Times are "HH:MM".
export interface TapeBar {
  t: string
  o: number; h: number; l: number; c: number
  v: number; oi: number
  vwap: number
  u1: number; d1: number; u2: number; d2: number; u3: number; d3: number
}
```

- [ ] **Step 2: Add the selector inside `useLiveData`** (next to the existing `at`/`barCount` callbacks; ensure `useCallback` is in the react import)

```ts
  // Tape Chart: the newest day's FUT bars, verbatim and FULL — replay is done
  // by the chart engine's cursor (causal truncation), not by re-slicing here.
  const tapeBars = useCallback((k: IndexKey): { day: string; bars: TapeBar[] } => {
    const D = raw[k]?.D
    const day = D?.days?.[D.days.length - 1]
    if (!day) return { day: '', bars: [] }
    const bars: TapeBar[] = []
    for (const b of day.bars ?? []) {
      const f = b.fut
      if (!f) continue // engine ≥ c91c9d5 always emits fut; guard for older backends
      bars.push({
        t: b.t, o: f.o, h: f.h, l: f.l, c: f.c, v: f.v, oi: f.oi,
        vwap: f.vwap, u1: f.u1, d1: f.d1, u2: f.u2, d2: f.d2, u3: f.u3, d3: f.d3,
      })
    }
    return { day: day.day ?? '', bars }
  }, [raw])
```

- [ ] **Step 3: Extend the return**

```ts
  return { data, loading, error, lastUpdated, barCount, at, dead, tapeBars }
```

- [ ] **Step 3b: Surface `flip_px` — the chain computes it, data.ts drops it**

The spec's Phase 1 level list includes the gamma flip. `/api/chain` already carries it (`chain_metrics.py:319`, key `flip_px`), but the `Chain` mapping never reads it. Add to the `Chain` interface (data.ts:57):

```ts
  /** Dealer gamma flip price from the chain GEX profile, or null when the
   *  chain could not compute one. Never guessed. */
  flipPx: number | null
```

and in the chain-mapping object where `maxPain: hist?.mp ?? m.max_pain ?? 0` is built (data.ts:462), add:

```ts
    flipPx: Number.isFinite(m.flip_px) ? m.flip_px : null,
```

The field stays **required**, so the compiler forces every construction site to
decide about it. That means one more site: `mockChain()` in `App.tsx` (~:209)
also builds a `Chain`, so add it there beside the other explicit fallback
fields (`mpDist: 0`, `spot: 0`, `expiry: ''`, …):

```ts
    flipPx: null,        // fallback has no gamma flip — null, never a fabricated level
```

Not optional (`flipPx?:`): optional lets a future construction site forget the
field, and `undefined` would then read as "no flip" indistinguishably from a
genuine absence. This is the only App.tsx line that belongs to Task 2 rather
than Task 7 — without it `tsc --noEmit` fails, and a task must leave the tree
compiling. (Found during execution: the plan originally missed this site.)

- [ ] **Step 4: Gate**

Run: `corepack pnpm --dir ui-v2 exec tsc --noEmit` — expected clean (nothing consumes it yet).

- [ ] **Step 5: Commit**

```bash
git add ui-v2/src/data.ts
git commit -m "feat(ui-v2): tapeBars() — full-day FUT series for the Tape Chart"
```

---

### Task 3: `trade/indicators.ts` — reshape server arrays for the engine

**Files:**
- Create: `ui-v2/src/trade/indicators.ts`

**Interfaces:**
- Consumes: `TapeBar` from `../data`; `Candle` from `../vendor/candl/core/types`; `IndicatorRenderData` from `../vendor/candl/chart/types`.
- Produces: `toCandles(day: string, bars: TapeBar[]): Candle[]` and `buildIndicators(bars: TapeBar[]): IndicatorRenderData[]` — used by Task 5. **It computes nothing** — every value is a payload field or `null`.

- [ ] **Step 1: Write the module**

```ts
// Pure reshaping: payload arrays -> CandL render structures. No indicator is
// ever computed here (invariant #6) — the engine's IndicatorRenderData takes
// already-computed values aligned 1:1 with the candles.
import type { Candle } from '../vendor/candl/core/types'
import type { IndicatorRenderData } from '../vendor/candl/chart/types'
import type { TapeBar } from '../data'

// One-meaning colour (App.tsx `T`): brass is structure. Bands fade outward.
const BRASS = '#E0A852'
const BAND = ['rgba(224,168,82,0.70)', 'rgba(224,168,82,0.45)', 'rgba(224,168,82,0.28)']
const OI_LINE = '#7F8EA3' // neutral — OI is a series here, not a direction call

// Local-midnight epoch for the session date. Live payloads carry ISO dates;
// replay CSV days ("Tue 15") don't parse — fall back to a fixed base so the
// intraday HH:MM clock (which IS real data) still renders correctly.
export function dayBase(day: string): number {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(day)
  if (m) return new Date(+m[1], +m[2] - 1, +m[3]).getTime()
  return new Date(2026, 0, 1).getTime()
}

export function toCandles(day: string, bars: TapeBar[]): Candle[] {
  const base = dayBase(day)
  return bars.map((b) => {
    const [hh, mm] = b.t.split(':').map(Number)
    return { time: base + (hh * 60 + mm) * 60_000, open: b.o, high: b.h, low: b.l, close: b.c, volume: b.v }
  })
}

// NaN is guarded at the source (honesty rule 5): a non-finite payload value
// becomes a null gap in the plot, never a drawn falsehood.
const series = (bars: TapeBar[], f: (b: TapeBar) => number) =>
  bars.map((b) => { const v = f(b); return Number.isFinite(v) ? v : null })

export function buildIndicators(bars: TapeBar[]): IndicatorRenderData[] {
  return [
    {
      instanceId: 'vwap-bands', label: 'VWAP ±σ', placement: 'overlay',
      outputs: [
        { name: 'vwap', values: series(bars, (b) => b.vwap), color: BRASS },
        { name: '+1σ', values: series(bars, (b) => b.u1), color: BAND[0] },
        { name: '-1σ', values: series(bars, (b) => b.d1), color: BAND[0] },
        { name: '+2σ', values: series(bars, (b) => b.u2), color: BAND[1] },
        { name: '-2σ', values: series(bars, (b) => b.d2), color: BAND[1] },
        { name: '+3σ', values: series(bars, (b) => b.u3), color: BAND[2] },
        { name: '-3σ', values: series(bars, (b) => b.d3), color: BAND[2] },
      ],
    },
    {
      instanceId: 'oi', label: 'OI', placement: 'pane',
      outputs: [{ name: 'oi', values: series(bars, (b) => b.oi), color: OI_LINE }],
    },
  ]
}
```

- [ ] **Step 2: Gate**

Run: `corepack pnpm --dir ui-v2 exec tsc --noEmit` — expected clean.

- [ ] **Step 3: Commit**

```bash
git add ui-v2/src/trade/indicators.ts
git commit -m "feat(ui-v2): trade/indicators — reshape payload series into CandL render data"
```

---

### Task 4: `trade/LevelsOverlay.ts` — TapeMap's levels drawn on the chart

**Files:**
- Create: `ui-v2/src/trade/LevelsOverlay.ts`

**Interfaces:**
- Consumes: `IChartEngine` from `../vendor/candl/chart/types`; `MapLevel` from `../data` (`{ label, value, kind: 'now'|'pivot'|'wall'|'vwap'|'band'|'pin'|'floor'|'cap'|'strike'|'trap'|'session', note }`).
- Produces: `startLevelsOverlay(canvas: HTMLCanvasElement, host: HTMLElement, engine: IChartEngine, getLevels: () => MapLevel[]): () => void` (returns a stop function) — used by Task 5. **This is the only file that touches CandL's coordinate system**, and it re-queries the converters every frame, as the engine docs require.

**Added during execution — label collision handling.** The code below draws every
label unconditionally. In practice `MAP.levels` carries 15+ entries (seven
pivots, both OI walls, VWAP, ±1σ, PIN, floor, cap, session hi/lo, plus MAX PAIN
and GEX FLIP), many within a few pixels of each other on a ~500px pane, and the
labels pile into an illegible stack. Required behaviour: **always draw every
line** (suppressing a line would hide a real level), but draw a label only when
it clears the last drawn label vertically; sort by `y` first so the decision is
deterministic. A level whose label is suppressed still shows its line, so
nothing is silently dropped — and the Task 6 header/rail remains the place the
full list is readable.

- [ ] **Step 1: Write the module**

```ts
// Levels the engine already knows, drawn over the chart. The ONLY file that
// touches CandL's coordinate system: converters are live objects and must be
// re-queried every frame (their docs say so — zoom/pan invalidates them).
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { MapLevel } from '../data'

// One-meaning colour: brass = structure; red is reserved for trap risk.
const STRUCT = 'rgba(224,168,82,0.85)'
const TRAP = 'rgba(255,95,107,0.85)'

export function startLevelsOverlay(
  canvas: HTMLCanvasElement,
  host: HTMLElement,
  engine: IChartEngine,
  getLevels: () => MapLevel[],
): () => void {
  const ctx = canvas.getContext('2d')!
  let raf = 0

  const draw = () => {
    raf = requestAnimationFrame(draw)
    const dpr = window.devicePixelRatio || 1
    const w = host.clientWidth, h = host.clientHeight
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr
      canvas.height = h * dpr
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    const conv = engine.getMainConverters()
    const pane = engine.getMainPaneRect()
    if (!conv || !pane) return // engine not laid out yet — draw nothing, never guess

    ctx.font = '10px ui-monospace, SFMono-Regular, Menlo, monospace'
    ctx.textBaseline = 'bottom'
    for (const lvl of getLevels()) {
      if (lvl.kind === 'now') continue // the tape itself is the price
      const y = conv.priceToY(lvl.value)
      if (y < pane.y + 4 || y > pane.y + pane.height - 4) continue
      const color = lvl.kind === 'trap' ? TRAP : STRUCT
      ctx.strokeStyle = color
      ctx.fillStyle = color
      ctx.setLineDash(lvl.kind === 'band' ? [2, 4] : [6, 4])
      ctx.beginPath()
      ctx.moveTo(pane.x, y)
      ctx.lineTo(pane.x + pane.width, y)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.fillText(`${lvl.label} ${lvl.value.toFixed(1)}`, pane.x + 6, y - 2)
    }
  }

  raf = requestAnimationFrame(draw)
  return () => cancelAnimationFrame(raf)
}
```

- [ ] **Step 2: Gate**

Run: `corepack pnpm --dir ui-v2 exec tsc --noEmit` — expected clean.

- [ ] **Step 3: Commit**

```bash
git add ui-v2/src/trade/LevelsOverlay.ts
git commit -m "feat(ui-v2): trade/LevelsOverlay — MAP levels drawn via engine converters"
```

---

### Task 5: `trade/ContractChart.tsx` — mount the engine, feed it, own the overlay

**Files:**
- Create: `ui-v2/src/trade/ContractChart.tsx`

**Interfaces:**
- Consumes: `createChartEngine` from `../vendor/candl/chart/engine`; `IChartEngine` from `../vendor/candl/chart/types`; `TapeBar`, `MapLevel` from `../data`; `toCandles`, `buildIndicators` from `./indicators`; `startLevelsOverlay` from `./LevelsOverlay`.
- Produces: `default ContractChart({ day, bars, levels, cursor }: { day: string; bars: TapeBar[]; levels: MapLevel[]; cursor: number | null })` — used by Task 6. `cursor` is the replay bar index (`null` = live); it drives `setReplayCursor` directly.

- [ ] **Step 1: Write the component**

```tsx
import { useEffect, useRef } from 'react'
import { createChartEngine } from '../vendor/candl/chart/engine'
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { TapeBar, MapLevel } from '../data'
import { toCandles, buildIndicators } from './indicators'
import { startLevelsOverlay } from './LevelsOverlay'

interface Props {
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  cursor: number | null // replay bar index; null = live
}

export default function ContractChart({ day, bars, levels, cursor }: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<IChartEngine | null>(null)
  const levelsRef = useRef<MapLevel[]>(levels)
  const prevRef = useRef<{ day: string; n: number }>({ day: '', n: 0 })
  levelsRef.current = levels

  useEffect(() => {
    const host = hostRef.current!
    const engine = createChartEngine(host, { theme: 'dark', pricePrecision: 2, chartType: 'candles' })
    engineRef.current = engine
    // The vendored theme's own candles are teal/red (#26a69a/#ef5350) — foreign
    // to this app's palette. setSettings is the library's sanctioned styling
    // hook, so the colours align here rather than by editing the pristine
    // vendor theme. Green/red carry direction, matching T.bull / T.bear.
    engine.setSettings({
      upColor: '#2EC27E', downColor: '#FF5F6B',
      gridVisible: true, crosshairVisible: true,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })
    const ro = new ResizeObserver(() => engine.resize())
    ro.observe(host)
    const stopOverlay = startLevelsOverlay(overlayRef.current!, host, engine, () => levelsRef.current)
    return () => {
      stopOverlay()
      ro.disconnect()
      engine.destroy()
      engineRef.current = null
    }
  }, [])

  useEffect(() => {
    const engine = engineRef.current
    if (!engine || !bars.length) return
    const candles = toCandles(day, bars)
    const prev = prevRef.current
    const grew = bars.length - prev.n
    const n = candles.length
    if (day === prev.day && grew === 0) {
      engine.updateLast(candles[n - 1])   // same forming minute, refreshed
    } else if (day === prev.day && grew === 1 && n >= 2) {
      // The minute rolled over. The bar we last pushed was still forming, so
      // its final OHLC must be written before the new one is appended —
      // otherwise the closed candle keeps the mid-formation values it had at
      // the last poll. updateLast replaces on equal open time and appends
      // otherwise (engine contract), so these two calls do exactly that.
      engine.updateLast(candles[n - 2])
      engine.updateLast(candles[n - 1])
    } else {
      engine.setData(candles) // first load, day change, or any gap — resync
    }
    engine.setIndicators(buildIndicators(bars))
    prevRef.current = { day, n: bars.length }
  }, [day, bars])

  useEffect(() => {
    engineRef.current?.setReplayCursor(cursor)
  }, [cursor])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={hostRef} style={{ position: 'absolute', inset: 0 }} />
      <canvas ref={overlayRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />
    </div>
  )
}
```

- [ ] **Step 2: Gate**

Run: `corepack pnpm --dir ui-v2 exec tsc --noEmit` — expected clean.

- [ ] **Step 3: Commit**

```bash
git add ui-v2/src/trade/ContractChart.tsx
git commit -m "feat(ui-v2): trade/ContractChart — CandL mount, live updates, replay cursor"
```

---

### Task 6: `trade/TradeTab.tsx` — composition + the honest empty state

**Files:**
- Create: `ui-v2/src/theme.ts` (extract the design tokens so `trade/` can share them)
- Modify: `ui-v2/src/App.tsx:15` (import `T` instead of declaring it — all 236 existing `T.*` uses are untouched)
- Create: `ui-v2/src/trade/TradeTab.tsx`

**Interfaces:**
- Consumes: `ContractChart` from `./ContractChart`; `TapeBar`, `MapLevel`, `IndexKey` from `../data`; `dayPrecision` from `./indicators` (added by the Task 3 review fix: returns `'exact'` for an ISO session date, `'no-year'` for a CSV replay key like `Jul 15` whose month and day are real but whose year is inferred, `'none'` when nothing parsed). The header must **disclose** anything other than `'exact'` — the intraday clock is always real, but an inferred calendar date must never read as fact.
- Produces: `default TradeTab({ index, day, bars, levels, cursor }: { index: IndexKey; day: string; bars: TapeBar[]; levels: MapLevel[]; cursor: number | null })` — used by Task 7.

- [ ] **Step 1: Extract the design tokens into `ui-v2/src/theme.ts`**

`T` is currently a module-local `const` in `App.tsx:15` and is used 236 times
there. The `trade/` components need the same tokens, and importing them from
`App.tsx` would be circular (`App.tsx` imports `TradeTab`). So move the
declaration — do not duplicate the values, and do not change any of them:

```ts
// Design tokens. Colour carries exactly one meaning each: brass is STRUCTURE
// (levels, walls, pins, σ-bands, ATM, positive GEX), green/red are DIRECTION
// only. Before that rule, purple meant "spring" while green/red also meant
// up/down, so hue resolved to neither.
export const T = {
  bg: '#0B0E14',
  card: '#141926',
  inset: '#1B2130',
  border: 'rgba(255,255,255,0.07)',
  textPrimary: '#E8EDF5',
  textSecondary: '#9AA7BD',
  textMuted: '#5D6B84',
  bull: '#2EC27E',          // direction only
  bear: '#FF5F6B',          // direction only
  caution: '#FFBF00',
  accent: '#E0A852',        // structure: levels, walls, pins, regime
} as const

/** Tabular monospace, so digits do not jitter as prices tick. */
export const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
```

Then in `App.tsx` delete the `const T = {...}` block (keeping its comment with
the tokens, as above) and add to the imports at the top:

```ts
import { T } from './theme'
```

Every existing `T.*` reference in `App.tsx` keeps working unchanged. Verify with
`corepack pnpm --dir ui-v2 exec tsc --noEmit` before continuing — this step must
be type-clean on its own.

- [ ] **Step 2: Write the component**

The header is a stat strip, not a row of loose spans: each cell is a muted
label above a tabular-mono value, so the eye lands on the number. It reads the
**shown** bar under replay, never the newest, and it discloses an inferred
session date rather than letting one read as fact.

```tsx
import ContractChart from './ContractChart'
import { dayPrecision } from './indicators'
import { T, MONO } from '../theme'
import type { TapeBar, MapLevel, IndexKey } from '../data'

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  cursor: number | null
}

function Stat({ label, value, color, title }: {
  label: string; value: string; color?: string; title?: string
}) {
  return (
    <div title={title} style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
      <span style={{
        fontSize: 9.5, letterSpacing: '0.07em', textTransform: 'uppercase',
        color: T.textMuted, whiteSpace: 'nowrap',
      }}>{label}</span>
      <span style={{
        fontFamily: MONO, fontSize: 13, fontWeight: 600,
        color: color ?? T.textPrimary, whiteSpace: 'nowrap',
      }}>{value}</span>
    </div>
  )
}

export default function TradeTab({ index, day, bars, levels, cursor }: Props) {
  // Honesty rule 1: no tape = say so at full width, and chart nothing. A
  // fallback must never occupy the space where live data goes.
  if (!bars.length) {
    return (
      <div style={{ padding: 16 }}>
        <div style={{
          padding: '14px 18px', borderRadius: 6,
          backgroundColor: 'rgba(255,191,0,0.10)',
          border: `1px solid ${T.caution}`, color: T.caution,
          fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
        }}>
          NO {index} TAPE — the backend has no session for this index, so there is
          nothing to chart. No candles are drawn rather than placeholder ones.
        </div>
      </div>
    )
  }

  // Clamp both ends: a negative cursor would index bars[-1] === undefined and
  // throw on the first field read.
  const at = cursor == null
    ? bars.length - 1
    : Math.max(0, Math.min(cursor, bars.length - 1))
  const b = bars[at]                       // causal: the shown bar, not the newest
  const live = cursor == null
  const prec = dayPrecision(day)
  const dir = b.c >= b.o ? T.bull : T.bear // the bar's own direction, same as its candle

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: 'clamp(420px, calc(100vh - 300px), 1200px)', padding: 16, gap: 10,
    }}>
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 22, flexWrap: 'wrap',
        padding: '10px 14px', backgroundColor: T.card,
        border: `1px solid ${T.border}`, borderRadius: 6,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 9.5, letterSpacing: '0.07em', color: T.textMuted }}>
            CONTRACT
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: T.textPrimary, letterSpacing: '0.02em' }}>
            {index} FUT
          </span>
        </div>
        <Stat label="Session" value={day || '—'}
              color={prec === 'exact' ? T.textPrimary : T.caution}
              title={prec === 'exact' ? undefined
                : prec === 'no-year'
                  ? 'This session key carries no year, so the chart’s date axis infers the current one. The month, day and intraday clock are real.'
                  : 'This session key carries no parseable date, so the chart’s date axis is synthetic. The intraday clock is real.'} />
        <Stat label="Bar" value={b.t} />
        <Stat label="Close" value={b.c.toFixed(1)} color={dir} />
        <Stat label="Open interest" value={`${(b.oi / 1e6).toFixed(2)}M`} />
        <Stat label="Volume" value={b.v.toLocaleString('en-IN')} />
        <Stat label="Bars" value={`${at + 1} / ${bars.length}`} />
        {/* Amber for REPLAY, matching the no-tape banner and the date
            disclosure: in this tab amber means "not the data you'd assume".
            Brass is reserved for structure, so it must not mean "mode". */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 7 }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            backgroundColor: live ? T.bull : T.caution,
          }} />
          <span style={{
            fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em',
            color: live ? T.bull : T.caution,
          }}>{live ? 'LIVE' : 'REPLAY'}</span>
        </div>
      </div>

      {prec !== 'exact' && (
        <div style={{ fontSize: 11, color: T.textMuted, paddingLeft: 2 }}>
          {prec === 'no-year'
            ? 'Session key carries no year — the date axis infers the current one; month, day and intraday times are real.'
            : 'Session key carries no parseable date — the date axis is synthetic; intraday times are real.'}
        </div>
      )}

      <div style={{
        flex: 1, minHeight: 0, borderRadius: 6, overflow: 'hidden',
        border: `1px solid ${T.border}`,
      }}>
        <ContractChart day={day} bars={bars} levels={levels} cursor={cursor} />
      </div>
    </div>
  )
}
```

The chart sits inside a bordered, rounded, `overflow: hidden` frame: the
vendored engine paints its own `#0e1117` background (`engine.ts:1699`) which
cannot be overridden through its API, and framing it this way makes that
slightly-lighter panel read as a deliberate inset rather than a mismatch.

- [ ] **Step 2: Gate**

Run: `corepack pnpm --dir ui-v2 exec tsc --noEmit` — expected clean.

- [ ] **Step 3: Commit**

```bash
git add ui-v2/src/trade/TradeTab.tsx
git commit -m "feat(ui-v2): TradeTab — chart composition with honest no-tape state"
```

---

### Task 7: Wire the tab into `App.tsx`

**Files:**
- Modify: `ui-v2/src/App.tsx` — five edits. Line numbers as of the start of this
  task (they shifted when Task 6 extracted the tokens, so locate by content, not
  by number): the `Tab` union `:19`, the `tabs` array `:1809`, the `useLiveData`
  destructure `:1810`, the `data` memo `:1818` (insert after it), and the tab
  render block starting `:1967`.

**Interfaces:**
- Consumes: `TradeTab` (Task 6), `tapeBars` (Task 2), existing `scrub` state and `data` (the replay-truncated `Dataset` — its `MAP` is already causal under replay, which is exactly what the overlay must show).
- Produces: the user-visible `Trade` tab.

- [ ] **Step 1: Extend the Tab union and tabs array** (the `type Tab` line and the `const tabs: Tab[]` line)

```ts
type Tab = 'Heat' | 'Trade' | 'Tape' | 'Chain' | 'OI Flow' | 'Events' | 'Validate' | 'Map'
```

```ts
  const tabs: Tab[] = ['Heat', 'Trade', 'Tape', 'Chain', 'OI Flow', 'Events', 'Validate', 'Map']
```

- [ ] **Step 2: Import and destructure** (top of file, beside the existing `import { T } from './theme'`; then the `useLiveData(MOCK)` line)

```ts
import TradeTab from './trade/TradeTab'
```

```ts
  const { data: liveData, error, lastUpdated, barCount, at, dead, tapeBars } = useLiveData(MOCK)
```

- [ ] **Step 3: Select the active index's tape and levels once per render** (insert immediately after the existing `const data = useMemo(() => at(scrub), [scrub, liveData])` line)

```ts
  const tape = useMemo(() => tapeBars(activeIndex), [tapeBars, activeIndex, liveData])
  // MAP levels are bar-derived and causal under replay. MAX PAIN and GEX FLIP
  // come from the chain, which is a live snapshot with no per-strike history
  // (the same reason Chain.aligned goes false while scrubbing) — so they are
  // drawn only when live, never during replay (honesty rule 6).
  const tradeLevels = useMemo(() => {
    const lv = [...(data.MAP[activeIndex]?.levels ?? [])]
    if (scrub == null) {
      const ch = data.CHAIN_DATA[activeIndex]
      if (ch && Number.isFinite(ch.maxPain) && ch.maxPain > 0)
        lv.push({ label: 'MAX PAIN', value: ch.maxPain, kind: 'strike', note: 'chain snapshot' })
      if (ch?.flipPx != null)
        lv.push({ label: 'GEX FLIP', value: ch.flipPx, kind: 'strike', note: 'chain snapshot' })
    }
    return lv
  }, [data, activeIndex, scrub])
```

- [ ] **Step 4: Render the tab** (in the tab render block, immediately after the `activeTab === 'Heat'` line)

```tsx
        {activeTab === 'Trade'    && <TradeTab index={activeIndex} day={tape.day} bars={tape.bars}
                                              levels={tradeLevels} cursor={scrub} />}
```

- [ ] **Step 5: Gates**

```bash
corepack pnpm --dir ui-v2 exec tsc --noEmit   # expected clean
corepack pnpm --dir ui-v2 build               # expected: built without errors
python -m pytest -q                           # expected: 43 passed
```

- [ ] **Step 6: Commit**

```bash
git add ui-v2/src/App.tsx
git commit -m "feat(ui-v2): Trade tab — index tape on the CandL engine"
```

---

### Task 8: Browser verification against the mock backend, then docs

**Files:**
- Modify: `context/ui-v2-dashboard.md` (tabs list + build history + open items)

**Interfaces:**
- Consumes: the finished Trade tab; launch configs `tapemap-mock-8765` (backend, works offline, serves only NIFTY) and `tapemap-v2` (Vite on 5173) from `.claude/launch.json` on this branch.
- Produces: verified feature + updated context doc.

- [ ] **Step 1: Start backend + Vite, open a fresh tab** (React hook-order warnings after an edit are HMR artifacts — always judge from a clean load)

Start `tapemap-mock-8765`, then `tapemap-v2`, open `http://localhost:5173`, click **Trade**.

- [ ] **Step 2: Verify the chart against the payload**

- Candles render for NIFTY with VWAP + six brass bands and the OI pane below.
- Bar count in the header equals `days[last].bars.length` from `curl "http://127.0.0.1:8765/api/data?idx=NIFTY"`.
- Levels overlay shows pivots/walls/VWAP/session levels with labels; no `NOW` line.
- MAX PAIN and GEX FLIP appear while live (mock chain serves NIFTY) and **disappear during replay** — they are chain snapshots and cannot be replayed.
- Console: zero errors.

- [ ] **Step 3: Verify replay causality**

Enter replay, scrub to an early bar: the chart clips to bars `[0..cursor]` with the time axis NOT resizing (that is `setReplayCursor` working); the header shows the scrubbed bar's `t`/`C`/`OI`; levels update with the scrub (MAP is causal). RETURN TO LIVE restores the full series.

- [ ] **Step 4: Verify the honest empty state**

Switch the header index to BANKNIFTY: the mock serves only NIFTY, so the tab must show the full-width "NO BANKNIFTY TAPE" note and **no chart**. That is the fix working, not a bug.

- [ ] **Step 5: Verify the live update path** (the mock replays forward)

Stay on NIFTY ~30s: the forming candle updates in place via `updateLast` without the viewport jumping (unless at the right edge, where auto-scroll is correct).

- [ ] **Step 6: Update `context/ui-v2-dashboard.md`**

Add `Trade` to the Tabs section: "**Trade** — the Tape Chart (Phase 1): index FUT candles, VWAP ±1/2/3σ bands, OI pane and the MAP levels drawn on the vendored CandL engine (`ui-v2/src/vendor/candl/`, pristine — see `ui-v2/src/vendor/VENDOR.md`); replay drives `setReplayCursor`, so it is causal at the engine layer." Append the build-history line with the actual commit hashes, and add an open item: "Trade tab verified against the mock fixture only — verify on a live session; then Phase 2 (callout + ribbon)."

- [ ] **Step 7: Final gates + commit**

```bash
corepack pnpm --dir ui-v2 exec tsc --noEmit && corepack pnpm --dir ui-v2 build && python -m pytest -q
git add context/ui-v2-dashboard.md
git commit -m "docs: record Tape Chart Phase 1 (Trade tab) in the v2 context doc"
```

---

## Out of scope for Phase 1 (by the spec's phasing)

Narration callout + ribbon (Phase 2), zones (Phase 3), SMC/ICT structure layer (Phase 3.5), position layer (Phase 4), `/api/contract` + `contract_tape.py` + the four states (Phase 5), Echoes (Phase 6). No interval selector (the payload is 1-minute; server-side aggregation arrives with `/api/contract` in Phase 5). No `python` changes at all — Phase 1 adds zero analytics, so the pytest surface is unchanged at 43.
