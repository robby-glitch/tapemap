# Tape Chart Phase 3 — zones, story balloons, the engine's read, SMC structure

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal (operator's words, 2026-07-30):** the hover box "is not letting me know
anything… I want this box to be telling the market story — suppose a move
started from bottom, if there is important levels it should drop a balloon with
info so we know and refer later"; "I want the colors same like I have in Kite
Zerodha charts"; "I want the charts to have zones as per market condition";
plus the spec's Phase 3 (zones), Phase 3.5 (SMC structure), and the trade
panel that surfaces the ENGINE's read with receipts.

**The controlling discovery (verified against `engine.py` 2026-07-30):**
`/api/data` bars ALREADY carry, per bar `t`:

- `bars[i].ctx` — `{verdict, vwhy, breadth, line, flips[], age, rng30, rng_r,
  vol30, inside1, z, bw_r, iv_ce, iv_pe, ivr_ce, ivr_pe,
  pin: {k, dist, regime}|null, t_exp, episode, loc, plays[],
  floor: [name, px]|null, cap: [name, px]|null}` (engine.py `ctx_track`, ~1091).
- `bars[i].gamma` — `{regime, w_ce, w_pe, proxy, iv_ce, iv_pe}` where regime ∈
  PINNED · FLOOR · CEILING · AMPLIFIED-UP · AMPLIFIED-DOWN · NEUTRAL (~260).
- `bars[i].setup` — the engine's momentum-setup lifecycle when one exists:
  `{status: LOADING|ARMED|EXPIRED|INVALIDATED, dir: UP|DOWN, t0, kind,
  level_name, level_px, ref, intensity, conflict, comp, died?, fired?}` (~891).

So **zones and the trade panel are pure presentation of per-bar engine
decisions** — Tasks 1–4 need NO backend change and work against the live
server that is already running. Only Phase 3.5 (`structure.py`) is backend.

## Global Constraints

- Branch `feature/dashboard-v2`. Tasks 1–4 never touch `ui/` or any `.py`
  file; Task 5 touches ONLY new `structure.py` + `test_structure.py` + the
  payload-assembly seam it identifies (additive key, v1 must ignore it).
  `ui-v2/src/vendor/candl/` is PRISTINE — never edit it.
- `pnpm` is not on PATH — always `corepack pnpm --dir ui-v2 ...`.
- Gates each commit: `corepack pnpm --dir ui-v2 exec tsc --noEmit` ·
  `corepack pnpm --dir ui-v2 build` · `python -m pytest -q` (48 now).
- **HONESTY RULES bind** (context/ui-v2-dashboard.md): quote the engine's own
  wording verbatim — never paraphrase into a stronger claim; a bar with no
  `ctx` says "engine context unavailable", it does not inherit a neighbour's;
  nothing is drawn for a value that is null/absent; replay is causal — no
  zone, balloon, structure or panel content may reveal a bar past the replay
  cursor.
- **UI renders, engine decides.** `trade/*.ts` may group contiguous identical
  per-bar verdicts into runs, tier, and format. It must not compute a rank,
  average, threshold, or any market analytic. (Precedent: `narration.ts`.)
- Colour discipline: brass = structure, green/red = direction only, amber
  `#FFBF00`/`T.caution` = "not the data you'd assume".
- Known chart gotchas (do not relearn): converters re-queried every frame;
  `LevelsOverlay` redraw-skip signature must include every new input; canvas
  CSS size set explicitly (replaced element); `Math.round`ed DPR; the
  ContractChart ResizeObserver is load-bearing; prevRef resets on engine
  creation; `LEGEND_BAND_PX` keeps the top band clear.

---

### Task 1: data layer — ctx/gamma/setup on TapeBar + zone runs

**Files:** modify `ui-v2/src/data.ts`; create `ui-v2/src/trade/zones.ts`.

1. In `data.ts`, add types mapped VERBATIM from the payload (all optional and
   null-safe — early bars may predate the ctx block, old backends may lack it):

```ts
export interface BarCtx {
  verdict: string; vwhy: string; breadth: string; line: string
  flips: string[]; age: number
  rng30: number; rng_r: number; vol30: number; inside1: number
  z: number; bw_r: number
  pin: { k: number; dist: number; regime: string } | null
  plays: string[]
  floor: [string, number] | null
  cap: [string, number] | null
  episode?: unknown; loc?: string
}
export interface BarGamma { regime: string; w_ce: number; w_pe: number; proxy: number }
export interface BarSetup {
  status: string; dir: 'UP' | 'DOWN'; t0: string; kind: string
  level_name: string; level_px: number; ref: number
  intensity: number; conflict: boolean; comp: number
  died?: string; fired?: string
}
```

   Extend `TapeBar` with `ctx?: BarCtx | null; gamma?: BarGamma | null;
   setup?: BarSetup | null` and map them in `tapeBars()` from `b.ctx`,
   `b.gamma`, `b.setup` (pass through `?? null`; NEVER default a missing
   verdict to anything). **First read `engine.py` lines 905–1110** and copy
   the exact `vwhy`/`verdict` field spellings — if a field named here does
   not match the engine, the engine is the authority and this plan is wrong.

2. `trade/zones.ts` — pure grouping, no analytics:

```ts
export interface Zone { i0: number; i1: number; verdict: string; cls: ZoneCls
                        label: string; why: string }
export type ZoneCls = 'stand' | 'watch' | 'go' | 'none'
export function buildZones(bars: TapeBar[]): Zone[]
```

   - A zone is a maximal run of consecutive bars with the SAME
     `ctx.verdict`. Bars with no ctx form `cls:'none'` runs (rendered as
     nothing, but the run must exist so hover can say "unavailable").
   - `cls` maps from the engine's OWN verdict vocabulary. **Read
     `engine.py` ~936–1058 first** to learn the real verdict strings, then
     map: stand-aside/no-trade family → `'stand'`, caution/selective family
     → `'watch'`, tradeable/go family → `'go'`. Record the actual observed
     strings in a comment. Never rename a verdict for display — `label` is
     the verdict verbatim plus the run length ("STAND ASIDE · 47m" style,
     using the engine's string, not this example's).
   - `why` is the LAST bar-of-run's `vwhy` verbatim (the engine's own
     receipt), never a synthesis across bars.
   - Causality note for consumers: callers clip by slicing `bars` before
     calling, or by ignoring zones with `i0 > cursor`; buildZones itself is
     pure over its input.

Gate: tsc + build + pytest. Commit.

---

### Task 2: chart layer — Kite candle colours, story balloons, zone bands

**Files:** modify `ui-v2/src/theme.ts`, `ui-v2/src/trade/ContractChart.tsx`,
`ui-v2/src/trade/LevelsOverlay.ts`.

1. **Kite colours.** In `theme.ts` set `CHART_UP.light = '#26a69a'` and
   `CHART_DOWN.light = '#ef5350'` — Zerodha Kite's default (TradingView
   classic) candle pair, per the operator's request to match their Kite
   charts. Dark values unchanged. Add a one-line comment naming the source
   ("Kite/TradingView default pair, operator request 2026-07-30").

2. **Story balloons** in `LevelsOverlay.ts` (it owns the rAF loop, converters
   and redraw signature): a NEW draw pass rendering persistent markers for
   every bar whose narration tier ≥ 2 — the market story stays on the chart
   to "refer later", instead of living only in the hover box.
   - Extend the existing data getter to also supply `narrs: (Narration|null)[]`
     (threaded from ContractChart exactly like `bars`/`times`, via a ref).
   - For bar i with `narrs[i]` and tier ≥ 2, and `i <= cursor` when the
     replay cursor is set: anchor at `x = timeToX(times[i])`; bear-tone
     balloons above the candle high, bull-tone below the low, structure/
     neutral above the high. A 1px stem from candle to balloon.
   - Balloon = rounded pill, 10px mono uppercase text = `narr.kind`
     (the engine's own tag, e.g. TRAP-SPRUNG). Tier 3: filled with the tone
     colour, panel-coloured text. Tier 2: 1px tone outline, tone text on a
     translucent panel fill. Tone colours from the mode palette
     (bull/bear/structure→brass/neutral).
   - Collision: lay out left→right; when a pill would overlap the previous
     one on the same side, push it one lane outward (up to 3 lanes of
     `pillH + 2` px). Beyond 3 lanes, drop TIER-2 pills first and keep tier
     3 — the ribbon and callout still carry everything, so nothing is lost,
     only de-cluttered. Never draw outside the pane rect; respect
     `LEGEND_BAND_PX`.
   - Include in the redraw signature: narration count + last non-null narr
     index + cursor (already present) so new events repaint exactly once.

3. **Zone bands** in `LevelsOverlay.ts`, drawn FIRST (behind everything):
   for each `Zone` (getter threaded like levels), skip `cls:'none'` and
   `'go'`; fill the vertical band `[timeToX(times[i0]), timeToX(times[i1])]`
   across the pane height. Light mode: `'stand'` → `rgba(196,43,48,0.05)`,
   `'watch'` → `rgba(255,191,0,0.07)`; dark mode: same hues at 0.08/0.10.
   At the band's top edge (below the legend band), an 8.5px uppercase label:
   the zone's `label`, in the band's colour at full opacity, clipped to the
   band width (skip the text when the band is narrower than the text).
   Clamp the band's right edge to the replay cursor's x when scrubbing.
   Include zone list (count + first/last i0/i1/cls) in the redraw signature.

4. `ContractChart.tsx`: thread `narrs` (already a prop) and a new
   `zones: Zone[]` prop into the overlay via refs, same pattern as
   `barsRef`. No other behavioural change; the identity guard, two-call
   rollover, ResizeObserver and prevRef reset are verified and MUST remain.

Gate: tsc + build + pytest. Commit.

---

### Task 3: TradeTab — the ENGINE READ panel + zone wiring

**Files:** modify `ui-v2/src/trade/TradeTab.tsx` (and `App.tsx` ONLY if a
prop must be threaded — check first; TradeTab already receives `bars`).

1. Build `zones` once per bars change with `useMemo(() => buildZones(bars))`.
   Pass to `ContractChart`.

2. **ENGINE READ panel**, full width, directly below the ribbon+legend,
   on the mode's `panel` with a `line` border — the "suggested trade" slot
   the operator asked for, built the only honest way: it surfaces the
   ENGINE's existing read with receipts, it never invents a recommendation.
   All content reads from `bars[at]` (the SAME cursor-clamped index the stat
   strip uses) so replay scrubs the panel causally. Sections, left→right:

   - **VERDICT** — `ctx.verdict` large (13px, weight 700; colour: `'stand'`
     family → bear, `'watch'` → caution, `'go'` → bull, from the Task 1
     mapping), then `ctx.vwhy` verbatim at 11px dim, then `ctx.line` at
     10.5px faint mono (the engine's own quantified receipt), then
     `ctx.breadth`.
   - **SETUP** — when `bars[at].setup` exists: `kind` + `dir` (arrow, green/
     red by dir), `status` chip (LOADING → caution outline, ARMED → filled
     dir colour, EXPIRED/INVALIDATED → struck-through faint), the engine's
     level `level_name @ level_px`, invalidation `ref` ("invalid past
     {ref}" — the engine's ref, not a suggestion), `intensity` and `comp`
     as small mono stats. When absent: "no setup armed — engine has nothing
     loaded here" in faint.
   - **PLAYS** — `ctx.plays` verbatim, one line each, mono 11px, bullet in
     brass (they are level-conditional structure statements). When empty:
     "no conditional plays on this bar".
   - **FLOOR / CAP** — `ctx.floor` and `ctx.cap` as `name px` chips in
     brass; omitted entirely when null.
   - When `bars[at].ctx` is missing: the whole panel body is one line —
     "engine context unavailable for this bar" (faint). Never show a
     neighbouring bar's read.
   - Footer, 10px faint, always: "the engine's own read, quoted with its
     receipts — descriptive, not advice · signals only, orders never".

3. `flips` (`ctx.flips`) render as a thin "Δ15m" row under VERDICT when
   non-empty — the delta radar is the "what changed" story feed.

4. Keep FOCUS, the toggle, the pills, disclosure lines untouched. The panel
   participates in the height measurement (chart minimum 420px still holds;
   panel may scroll the page — the chart must not shrink below minimum).

Gate: tsc + build + pytest. Commit.

---

### Task 4: browser verification + docs (controller does this)

Live server on 8765 is running (market hours). Vite via launch.json
`tapemap-v2`. Verify: Kite candle colours; balloons on real event bars,
persistent, causal under scrub; zone bands with engine-verbatim labels;
ENGINE READ panel matching `/api/data`'s ctx for the shown bar; ctx-less
early bars honest; 0 console errors; paint ≥ 100 rAF/s. Then update
`context/ui-v2-dashboard.md` + `.superpowers/sdd/progress.md`, commit docs.

---

### Task 5: `structure.py` — the SMC/ICT layer (Phase 3.5, backend)

**Files:** create `structure.py`, `test_structure.py`; modify the payload
assembly seam only (investigate: `live.py` builds the live payload per
cycle; `server.py` `analyze(...)` builds the replay payload — attach an
additive top-level key `structures` to each day dict; v1 ignores unknown
keys — verify that by reading `ui/app.js` `setDay`).

Follow spec §7 of `docs/superpowers/specs/2026-07-29-contract-tape-design.md`
EXACTLY — definitions, tolerances as fractions of session realised range or
percentile ranks (NEVER point values), the IP line (write from definitions,
no Pine source), and the four test families (geometry from hand-built bars,
causality/truncation equivalence, index independence at BANKNIFTY/SENSEX
scale, confirmation separability: absent flow inputs → every structure
`confirm: "UNKNOWN"`, never `"UNCONFIRMED"`).

Output shape (one list per day, aligned to bar indices, each structure
carries its birth so the UI can clip causally):

```json
{ "kind": "FVG|OB|BOS|CHOCH|EQH|EQL|SWING_H|SWING_L",
  "i0": 12, "i1": 15, "born": 15, "hi": 24310.0, "lo": 24296.5,
  "dir": 1, "confirm": "CONFIRMED|UNCONFIRMED|UNKNOWN",
  "confirm_why": "…names the actual fields/numbers, or what was missing…" }
```

`born` = the index of the bar that completed the structure (a swing needs
its confirming bars — it must not exist before them). Flow confirmation
sources per spec §7's table, reading fields that already exist; where a
source is unavailable in this payload path, `UNKNOWN` + why. Pure stdlib,
no I/O, never imported by `engine.py`. Module docstring records the
definitions used.

Gate: pytest (new tests + 48 existing) + tsc + build (unchanged but run).
Commit.

---

### Task 6: structure frontend + live restart (controller-verified)

**Files:** `ui-v2/src/data.ts` (map `structures`), `ui-v2/src/trade/`
(draw in `LevelsOverlay`), `TradeTab.tsx` (an `SMC` toggle, default ON,
persisted `tape.smc`).

- FVG/OB → translucent boxes from `i0..i1` extended right until filled/now,
  brass-tinted for structure; BOS/CHoCH → short horizontal tick at the broken
  level + 8.5px label at `born`; EQH/EQL → dashed line across the pool.
- `confirm: CONFIRMED` full opacity; `UNCONFIRMED` faint + "unconfirmed"
  suffix; `UNKNOWN` faint + "unchecked" suffix. Never silently dropped.
- Causal: draw only structures with `born <= cursor` when scrubbing.
- Redraw signature includes structure count + toggle.
- Then restart the live server (owed anyway — activates the CHAIN STALE
  `built_at` banner) and verify live: structures render, zones/balloons/
  panel live, banner plumbing correct. Update docs + ledger.
