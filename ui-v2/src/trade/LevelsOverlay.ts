// Levels the engine already knows, drawn over the chart. The ONLY file that
// touches CandL's coordinate system: converters are live objects and must be
// re-queried every frame (their docs say so — zoom/pan invalidates them).
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { Converters } from '../vendor/candl/drawings/types'
import type { MapLevel, RotationSignal, Structure, TapeBar } from '../data'
import { palette } from '../theme'
import type { Mode } from '../theme'
import type { Narration } from './narration'
import { pillText } from './hinglish'
import type { Zone } from './zones'

/** What the per-bar passes (σ ribbons, story balloons) need, re-read every
 *  frame like every other getter here: the bars carry each sigma level
 *  per-bar, `times` is the candle time axis (ContractChart already builds this
 *  for hover mapping — reused, not recomputed), `narrs` is the same 1:1
 *  narration array the Callout and the Ribbon already read, and `cursor` is
 *  the replay index so ribbons and balloons stop exactly where the candles do. */
export interface OverlayData {
  bars: TapeBar[]
  times: number[]
  narrs: (Narration | null)[]
  cursor: number | null
  /** The backend's index band-rotation signals, 1:1 with `bars`, or null when
   *  they cannot be aligned honestly (data.ts's skip/length guard) — in which
   *  case NOTHING is drawn and TradeTab prints the reason. */
  rotation: (RotationSignal | null)[] | null
}

/** The pane geometry the engine hands out, in CSS px. */
type PaneRect = { x: number; y: number; width: number; height: number }

/** The active palette object — either `TL` or `T`; both carry these keys. */
type Palette = ReturnType<typeof palette>

// σ band palette — matched to the operator's own Kite VWAP-band study
// (screenshot, 2026-07-30): the ±1σ core reads pink/red, the 1→2σ shoulder
// green, the 2→3σ outer blue, each with a stronger edge line. Deliberately NOT
// brass: the operator reads this nested distance scale by hue in Kite all day,
// and matching it was an explicit request. Drawn as ANNULI (u3→u2, u2→u1,
// u1→d1, d1→d2, d2→d3) rather than three stacked full-width fills, so each
// ring keeps its own hue instead of muddying into the sum of all three.
// Read off the operator's own Kite band legend (screenshot, 2026-07-30):
// 1σ dark red · 2σ sage green · 3σ azure. These are EYEBALLED from that legend
// image, not sampled out of Kite's config — if a hex is off it is off by a
// shade, and this is the one place to correct it. VWAP's own bright red lives
// in indicators.ts, which owns that line.
const BAND_RGB = {
  core: '139,26,26',   // ±1σ  — Kite's dark red
  mid: '143,188,143',  // 1→2σ — Kite's sage green
  outer: '0,168,232',  // 2→3σ — Kite's azure
} as const
const BAND_FILL_ALPHA: Record<Mode, number> = { light: 0.10, dark: 0.13 }
// 0 since 2026-08-11, by the operator's instruction: the boundary lines (VWAP
// and ±1σ named specifically) were clutter next to the level chips on the
// right — "not required at all". The hued WASHES stay: they are the Kite-band
// context the operator asked for on 2026-07-30; only the strokes go. Kept as
// an alpha rather than deleting the edge path so turning a boundary back on
// is a one-number change.
const BAND_EDGE_ALPHA: Record<Mode, number> = { light: 0, dark: 0 }

// Minimum vertical gap between two drawn labels, for a 10px font.
const LABEL_GAP = 11

// The chart engine draws its own OHLC legend across the top-left of the main
// pane. A label landing in that band would overprint it and both become
// illegible, so labels start below it — the level's LINE is still drawn.
const LEGEND_BAND_PX = 26

// Right-axis price chip geometry (Task 5: "the mockup's right-axis price
// chip") — a filled rect just inside the pane's right edge, price in
// panel-coloured mono, so a level reads at the axis too, not only via the
// (collision-limited) left label.
const CHIP_H = 13
const CHIP_PAD = 4
const CHIP_MARGIN = 2

// The font stack every text pass in this file shares. Kept local (rather than
// theme.ts's MONO, which also lists Consolas) so the already-verified label
// and chip metrics do not shift under an added family.
const MONO_STACK = 'ui-monospace, SFMono-Regular, Menlo, monospace'

// Zone bands (Phase 3): one vertical wash per market-condition run. One hue
// per class, one alpha per mode — dark needs the higher alpha for the same
// apparent tint against #0B0E14. `go` and `none` are never drawn: a green
// light needs no warning wash, and a bar with no ctx must never be painted as
// though it had a verdict.
const ZONE_HUE: Record<'stand' | 'watch', string> = {
  stand: '196,43,48',
  watch: '255,191,0',
}
const ZONE_ALPHA: Record<Mode, Record<'stand' | 'watch', number>> = {
  light: { stand: 0.30, watch: 0.34 },
  dark: { stand: 0.36, watch: 0.40 },
}
// The condition track's height, and the alpha of the hairline dropped from it
// at each run's start. Higher alphas than a full-height wash could carry —
// a 9px strip can be read at a glance without tinting the price area.
const ZONE_STRIP_PX = 11
const ZONE_EDGE_ALPHA: Record<Mode, number> = { light: 0.16, dark: 0.20 }
// Small enough to sit just under the engine's legend band without competing
// with the 10px level labels that share the same corner.
const ZONE_LABEL_PX = 8.5

// SMC structure layer (Phase 3.5). Brass, because theme.ts's rule is that
// brass IS structure — an order block is not a direction claim, so it must not
// borrow green/red even though it carries a `dir`. Dark needs the higher alpha
// for the same apparent tint against #0B0E14, exactly as the zone bands do.
//
// OB is the only BOXED kind left. FVG held the other half of this table until
// 2026-08-07, when the operator dropped it — see drawStructures' header.
const STRUCT_ALPHA: Record<Mode, number> = {
  light: 0.050,
  dark: 0.085,
}
// Lowered from 0.25 with the fills: ~85 boxes overlap on a real session, and
// each border added a visible brass rule, so the compounded haze read as a
// stain over the candles rather than as structure.
const STRUCT_BORDER_ALPHA = 0.16
// UNCONFIRMED and UNKNOWN are DIFFERENT claims and their labels say so
// ("unconfirmed" vs "unchecked"), so the shape now carries the distinction
// too, not just the label text: UNCONFIRMED (flow checked, disagreed) draws
// noticeably faint with the normal solid 1px border; UNKNOWN (flow could not
// be checked) draws fainter still, with a DASHED border, so a de-cluttered
// label (or a screenshot with the label cropped) still reads which claim it is.
const STRUCT_FAINT_UNCONFIRMED = 0.55
const STRUCT_FAINT_UNKNOWN = 0.35
const STRUCT_LABEL_PX = 8.5
const STRUCT_LABEL_GAP = 3       // px between a tick/line end and its label
const STRUCT_POOL_DASH: [number, number] = [3, 3]
/** Half-length of a SWING_H/SWING_L tick, centred on x(born). Short on
 *  purpose: there are ~51 a session and each one is already the endpoint of an
 *  OB or an EQH/EQL pool, so this marks the pivot without competing with the
 *  structure that carries the claim. */
const STRUCT_SWING_PX = 5
/** How many OB zones are drawn, newest first. Zones are ranked by `born`, so
 *  the ones kept are the most recent — the ones price is still trading
 *  against. The count dropped is DISCLOSED in the chart's legend line (see
 *  TradeTab), because "we found nothing here" and "we are not showing you what
 *  we found" are different claims. Pools are never capped: there are only ~40
 *  of them and they draw as thin lines, not fills.
 *
 *  This capped FVG as well until 2026-08-07. FVG was ~85 of the ~90 boxes a
 *  session — with it gone the cap rarely binds, and it is kept rather than
 *  raised because the disclosure it feeds is what makes a thinned chart
 *  readable as thinned rather than as empty. */
export const STRUCT_ZONE_LIMIT = 12

// Story balloon geometry. A tier-≥2 narration gets a persistent pill so the
// day's story stays on the chart to refer back to, instead of living only in
// the hover callout.
const PILL_H = 14
const PILL_PAD_X = 5
const PILL_R = 7
const PILL_STEM = 6              // gap between the candle extreme and lane 0
const PILL_LANES = 3             // outward lanes before de-cluttering starts
const PILL_LANE_STEP = PILL_H + 2
const PILL_GUTTER = 2            // horizontal breathing room between two pills

// Band-rotation markers (band_rotation.detect_index). A DIFFERENT CLAIM from
// an event balloon — the operator's own setup, not something the engine
// observed — so it must not be mistakable for one at a glance. It IS a
// direction claim (BUY/SELL), so theme.ts's rule puts it on bull/bear and the
// distinction has to be carried by SHAPE, not by hue:
//
//   * a SQUARE-cornered pill (radius 2) against the balloons' rounded 7,
//   * a 1.5px border where a tier-2 balloon has 1,
//   * a filled TRIANGLE sitting on the σ band the bar actually pierced,
//     with a hairline from that band to the pill — a balloon anchors on the
//     candle extreme and has no band mark at all.
//
// The triangle is the load-bearing difference: it is the only mark on this
// chart drawn AT a σ level rather than at a candle.
const ROT_PILL_R = 2
const ROT_BORDER_PX = 1.5
const ROT_TRI_PX = 5             // half-width of the band marker's triangle
const ROT_STEM = 4               // gap between the band mark and lane 0
// Faded for a signal whose pre-move compression read came back SUSPECT (the
// index band was not squeezing, or was already releasing). Never hidden: that
// is the backend's context on the setup, not a veto of it. UNKNOWN — "we could
// not check" — sits between the two, and the dashed border says which is which.
const ROT_SUSPECT_ALPHA = 0.55
const ROT_UNKNOWN_ALPHA = 0.75
const ROT_DASH: [number, number] = [3, 2]

/**
 * Which band-rotation records are drawn as a SETUP MARKER. Only `d3`.
 *
 * Not a density tweak — a truth one. `band_rotation.detect_index` emits three
 * bands, and two of them carry scored verdicts AGAINST them in
 * `context/research-findings.md` §2:
 *
 *   d2  "noise everywhere — 180 NIFTY signals ≈ coin flip"          REJECTED
 *   u3  selling any upper band, "REJECTED on 5 independent datasets,
 *       every depth"                                                REJECTED
 *
 * Drawing a rejected band in the SAME shape as the one surviving edge states
 * that they are the same kind of claim. They are not — and a session prints
 * enough of them to bury the d3 marks this tab exists for, which is the
 * identical failure STRUCT_ZONE_LIMIT was added for and the reason the
 * operator said they could not see anything.
 *
 * Withheld, never silently: `rotWithheld` counts what this drops so the legend
 * can say so. "We found nothing" and "we are not showing you" are different
 * statements (HANDOFF §9). Nothing is deleted — the backend still sends every
 * band, and the hover callout still carries each one's own sentence.
 */
/** 09:25 — `band_rotation.ANCHOR_MINUTE`, as minutes past midnight. */
const ROT_ANCHOR_MINUTE = 9 * 60 + 25

/** Minutes past midnight from a bar's own "HH:MM" label, or null. Read off the
 *  LABEL rather than counted in bars so the gate lands on 09:25 at any
 *  interval — the same thing `band_rotation._minute` does. */
function rotMinute(t: string | null | undefined): number | null {
  const m = /^(\d{1,2}):(\d{2})/.exec(t ?? '')
  if (!m) return null
  return Number(m[1]) * 60 + Number(m[2])
}

export interface RotDrawPlan {
  /** True at index i when the overlay puts a marker there. */
  drawn: boolean[]
  drawnCount: number
  /** Records the backend sent that §5c's detector cannot legally emit.
   *  Expected to be 0 forever; a non-zero one is a BACKEND disagreement, not
   *  a filter, and is withheld and named rather than quietly drawn. */
  unexpected: number
  unexpectedWhy: string
}

/**
 * Which records this chart draws as a SETUP MARKER.
 *
 * **This used to filter. It now verifies, and the difference matters.**
 *
 * It was written against `rotation` — §1's one-candle rule — and applied three
 * filters by hand (d3 BUY only, post-09:25, first-of-run) because the chart
 * was drawing a population no published number described, while the scorer
 * applied all three. Duplicating a rule in two languages is exactly how that
 * gap opened in the first place, so the filters did not stay here: they went
 * where the rule lives. `band_rotation.run_states` gates arming at 09:25 off
 * the bar's own clock label, only ever emits `d3`/`BUY` (`RUN_BAND`), and
 * folds a falling run into one reference by construction.
 *
 * So this is fed `rotationRun` and draws every record in it. What it still
 * does is CHECK: anything that is not d3 BUY after 09:25 cannot have come out
 * of that detector, so it is withheld and counted as a disagreement rather
 * than drawn. That count should be 0 forever. If it is not, the backend and
 * this chart disagree about what the rule is, and the operator is told so
 * instead of being shown an unscored marker (`HANDOFF` §9 / `CHECKLIST` A1).
 *
 * Nothing is deleted: the backend still sends `rotation` too, and a caller
 * that wants the touch rather than the entry can still ask for it.
 */
export function runDrawPlan(
  rotation: (RotationSignal | null)[] | null,
  lastIdx: number,
): RotDrawPlan {
  const plan: RotDrawPlan = {
    drawn: [], drawnCount: 0, unexpected: 0, unexpectedWhy: '',
  }
  if (!rotation) return plan
  const n = Math.min(lastIdx, rotation.length - 1)
  const odd: string[] = []
  for (let i = 0; i <= n; i++) {
    plan.drawn[i] = false
    const s = rotation[i]
    if (!s) continue
    const min = rotMinute(s.t)
    if (s.band !== 'd3' || s.side !== 'BUY') {
      plan.unexpected++
      if (odd.length < 3) odd.push(`${s.t ?? `bar ${i}`} is ${s.side} ${s.band}`)
      continue
    }
    if (min == null || min < ROT_ANCHOR_MINUTE) {
      plan.unexpected++
      if (odd.length < 3) odd.push(`${s.t ?? `bar ${i}`} is before 09:25`)
      continue
    }
    plan.drawn[i] = true
    plan.drawnCount++
  }
  if (plan.unexpected) {
    plan.unexpectedWhy = odd.join(', ')
      + (plan.unexpected > odd.length ? `, +${plan.unexpected - odd.length} more` : '')
  }
  return plan
}

/** Add an alpha channel to a `palette(mode)` colour. The overlay's dashed
 *  lines and chips need translucency the palette itself does not carry; this
 *  is the one place that derives it, always from a palette value passed in —
 *  never a colour invented here. */
function withAlpha(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r},${g},${b},${alpha})`
}

/** Trace a rounded rect into the current path. Hand-rolled rather than
 *  `ctx.roundRect`, which is newer than this project's browser floor — a
 *  missing method would THROW inside the rAF loop and take every later pass
 *  (levels included) down with it, instead of degrading one pill. */
function roundedRectPath(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
) {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

/** Half the on-screen distance between two adjacent candles, measured off the
 *  live axis rather than assumed. Zone bands pad by this at both ends so
 *  consecutive runs tile edge-to-edge: `timeToX` returns a candle's CENTRE, so
 *  an unpadded band would leave a bar-wide gap between one run's last candle
 *  and the next run's first. 0 when the axis is degenerate (one bar, or a
 *  non-finite step) — never a guessed pixel width. */
function halfBarPx(conv: Converters, times: number[]): number {
  if (times.length < 2) return 0
  const step = conv.timeToX(times[1]) - conv.timeToX(times[0])
  return Number.isFinite(step) && step > 0 ? step / 2 : 0
}

/** A band key on `TapeBar` — any of the six σ deviations. Both edges of a
 *  ribbon take the same union so an ANNULUS (e.g. `u3`→`u2`, or `d1`→`d2`) is
 *  expressible, not only a symmetric ±nσ pair. */
type BandKey = 'u1' | 'u2' | 'u3' | 'd1' | 'd2' | 'd3'

/** One σ ribbon: a filled polygon between the `uKey`/`dKey` per-bar values
 *  across bars `[0, lastIdx]`, optionally with its two edges stroked. Walks the
 *  upper edge left→right then the lower edge right→left and closes — one path
 *  per CONTIGUOUS run of finite values, so a non-finite bar (the payload can
 *  carry nulls) ends the current run and starts a new one rather than being
 *  bridged over: a hole stays a hole. */
function drawRibbon(
  ctx: CanvasRenderingContext2D,
  conv: Converters,
  bars: TapeBar[],
  times: number[],
  lastIdx: number,
  uKey: BandKey,
  dKey: BandKey,
  fillStyle: string,
  edgeStyle?: string,
) {
  ctx.fillStyle = fillStyle
  let i = 0
  while (i <= lastIdx) {
    const finite = (k: number) =>
      times[k] != null && Number.isFinite(bars[k][uKey]) && Number.isFinite(bars[k][dKey])
    if (!finite(i)) { i++; continue }
    let j = i
    while (j + 1 <= lastIdx && finite(j + 1)) j++
    if (j > i) {
      ctx.beginPath()
      ctx.moveTo(conv.timeToX(times[i]), conv.priceToY(bars[i][uKey]))
      for (let k = i + 1; k <= j; k++) ctx.lineTo(conv.timeToX(times[k]), conv.priceToY(bars[k][uKey]))
      for (let k = j; k >= i; k--) ctx.lineTo(conv.timeToX(times[k]), conv.priceToY(bars[k][dKey]))
      ctx.closePath()
      ctx.fill()
      if (edgeStyle) {
        // Stroke each edge as its own open path — closing the polygon instead
        // would draw two vertical joins across the band, which Kite's study
        // does not have.
        ctx.strokeStyle = edgeStyle
        ctx.lineWidth = 1
        for (const key of [uKey, dKey]) {
          ctx.beginPath()
          ctx.moveTo(conv.timeToX(times[i]), conv.priceToY(bars[i][key]))
          for (let k = i + 1; k <= j; k++) {
            ctx.lineTo(conv.timeToX(times[k]), conv.priceToY(bars[k][key]))
          }
          ctx.stroke()
        }
      }
    }
    i = j + 1
  }
}

/**
 * Market-condition zone bands: a vertical wash spanning the pane height for
 * every run of bars sharing one engine verdict. Drawn FIRST, so the σ ribbons,
 * the level lines/chips and the story balloons all read on top of it.
 *
 * `lastIdx` is the cursor-clamped last visible bar, shared with the ribbons —
 * a band is cut off there, never drawn past the candles it describes.
 */
function drawZones(
  ctx: CanvasRenderingContext2D,
  conv: Converters,
  pane: PaneRect,
  times: number[],
  zones: Zone[],
  lastIdx: number,
  mode: Mode,
) {
  // Clamp rather than bail when `times` is one append behind `bars` (a render
  // between the data effect's two writes can see exactly that): the bands then
  // stop one bar short for a frame, the same way the ribbons and the balloons
  // do, instead of the whole wash blinking out.
  const cut = Math.min(lastIdx, times.length - 1)
  if (cut < 0) return
  const half = halfBarPx(conv, times)
  const cutX = conv.timeToX(times[cut]) + half
  if (!Number.isFinite(cutX)) return
  ctx.font = `${ZONE_LABEL_PX}px ${MONO_STACK}`
  ctx.textBaseline = 'top'
  for (const z of zones) {
    // 'go' needs no warning wash and 'none' has no verdict to show; both draw
    // nothing, so a bar the backend said nothing about stays unpainted.
    if (z.cls !== 'stand' && z.cls !== 'watch') continue
    const t0 = times[z.i0]
    const t1 = times[Math.min(z.i1, times.length - 1)]
    if (t0 == null || t1 == null) continue
    const x0 = conv.timeToX(t0) - half
    // Causality: while scrubbing, the band stops exactly where the candles do.
    // It must never advertise a verdict from a bar the cursor is hiding.
    const x1 = Math.min(conv.timeToX(t1) + half, cutX)
    if (!Number.isFinite(x0) || !Number.isFinite(x1) || x1 <= x0) continue
    const hue = ZONE_HUE[z.cls]
    // A CONDITION TRACK along the top of the pane, not a full-height wash.
    // Washing the whole price area was legible in isolation but unreadable
    // stacked under the σ bands and the structure boxes — the operator's own
    // words on the full-height version were "everything cramped up". The strip
    // keeps every verdict on screen, in the engine's own colour and words,
    // while the price area stays as clean as their Kite chart.
    // Sits just BELOW the engine's own OHLC legend band, which owns the top
    // LEGEND_BAND_PX of the pane — starting at pane.y would print the track
    // straight through "O 24363.80 H 24364.00 …".
    const stripTop = pane.y + LEGEND_BAND_PX
    ctx.fillStyle = `rgba(${hue},${ZONE_ALPHA[mode][z.cls]})`
    ctx.fillRect(x0, stripTop, x1 - x0, ZONE_STRIP_PX)
    // A hairline dropped from the strip marks where the run starts, so a
    // condition change is still locatable against the candles.
    ctx.fillStyle = `rgba(${hue},${ZONE_EDGE_ALPHA[mode]})`
    ctx.fillRect(x0, stripTop, 1, pane.height - LEGEND_BAND_PX)
    // The label is the engine's own words, upper-cased for display only. It is
    // skipped rather than truncated when the band is narrower than the text —
    // a clipped half-word reads as a different verdict.
    if (!z.label) continue
    const label = z.label.toUpperCase()
    if (ctx.measureText(label).width > x1 - x0 - 4) continue
    ctx.fillStyle = `rgb(${hue})`
    ctx.fillText(label, x0 + 2, stripTop + 1)
  }
}

/** An axis-aligned box already occupied by a drawn label. */
type LabelBox = { x0: number; y0: number; x1: number; y1: number }

/**
 * The SMC / ICT structure layer (Phase 3.5), drawn between the zone bands and
 * the σ ribbons. Every shape here is the BACKEND's — structure.py found it,
 * named it and confirmed it; this function only positions it.
 *
 *   OB         translucent brass box over [lo, hi], from the structure's own
 *              first bar and extended right to the last visible bar (or the
 *              replay cursor while scrubbing).
 *   EQH / EQL  a dashed line across the pool, from x(i0) to x(born).
 *   SWING_H/L  a short unlabelled tick at the pivot.
 *   PD*        prior-session levels across the whole pane, always labelled.
 *   PREMIUM /  the current range's two halves, named at the right edge.
 *   DISCOUNT
 *
 * THREE KINDS ARE PUBLISHED AND DELIBERATELY NOT DRAWN — FVG, BOS and CHOCH.
 * The operator dropped them on 2026-08-07 (*"i dont like smc… ob or eqh eql
 * swing h and l bhi rakh le"*). They are still typed in data.ts and still
 * arrive in the payload: this function stops rendering them, and structure.py
 * is untouched. Because that is "we are not showing you" rather than "we found
 * nothing", TradeTab's `Hidden:` line reports how many were withheld (A1/A5).
 *
 * SWING_H/SWING_L are drawn as of the same day. They had been suppressed since
 * Phase 3.5 because ~51 pivot marks a session buried the structures that carry
 * a claim — with FVG's ~85 boxes and BOS/CHoCH's ~40 ticks gone, that budget
 * exists. They stay UNLABELLED and shortest: each is already the endpoint of an
 * OB or a pool, so the tick locates the pivot without renaming it.
 *
 * Confirmation shows as opacity plus border style plus a label suffix:
 * CONFIRMED at full alpha, solid border, no suffix; UNCONFIRMED at 0.55×
 * alpha, solid border, "unconfirmed" (flow was checked and disagreed);
 * UNKNOWN at 0.35× alpha, DASHED border, "unchecked" (flow could not be
 * checked at all) — the shape alone tells the two apart once a label is
 * de-cluttered. A structure is NEVER dropped for being unconfirmed: "we
 * found nothing" and "we are not showing you" are different statements.
 *
 * `taken` arrives pre-seeded with the level labels' boxes, so a structure
 * label never overprints a price level's. It is mutated as labels are placed.
 */
function drawStructures(
  ctx: CanvasRenderingContext2D,
  conv: Converters,
  pane: PaneRect,
  pal: Palette,
  times: number[],
  structures: Structure[],
  lastIdx: number,
  mode: Mode,
  taken: LabelBox[],
) {
  // Same clamp the zone bands use: `times` can be one append behind `bars` for
  // a frame, and stopping one bar short beats blinking the whole layer out.
  const cut = Math.min(lastIdx, times.length - 1)
  if (cut < 0) return
  const half = halfBarPx(conv, times)
  const cutX = conv.timeToX(times[cut]) + half
  if (!Number.isFinite(cutX)) return
  const brass = pal.accent

  /** CONFIRMED draws at the configured alpha. UNCONFIRMED and UNKNOWN each
   *  get their own fraction of it (never zero, and never a different hue —
   *  brass is structure) so the two claims stay visually distinct even once
   *  a label is de-cluttered; the border dash (below) carries the rest. */
  const scale = (s: Structure) =>
    s.confirm === 'CONFIRMED' ? 1
      : s.confirm === 'UNCONFIRMED' ? STRUCT_FAINT_UNCONFIRMED
        : STRUCT_FAINT_UNKNOWN
  const suffix = (s: Structure) =>
    s.confirm === 'UNCONFIRMED' ? ' unconfirmed'
      : s.confirm === 'UNKNOWN' ? ' unchecked' : ''
  /** The single price a point/pool structure is about. `hi === lo` for
   *  BOS/CHOCH (verified against a live payload), so this reads correctly
   *  whether the backend sends a point or a span. */
  const levelOf = (s: Structure) => (s.dir > 0 ? s.hi : s.lo)

  // Causality, and the whole of it: structure.py guarantees every field of a
  // structure — including its confirmation — is a function of bars[0..born],
  // so this filter IS the replay truncation. Nothing is recomputed here.
  const live: Structure[] = []
  for (const s of structures) if (s.born >= 0 && s.born <= cut) live.push(s)

  // The newest STRUCT_ZONE_LIMIT zones, by birth. structure.py already sorts by
  // `born`, but this does not lean on that: it takes the largest `born` values
  // explicitly, so a change in the backend's ordering cannot silently start
  // showing the OLDEST zones instead of the newest.
  // The CURRENT premium/discount cut: the newest range that exists at this
  // bar. -Infinity when the layer publishes none, which draws nothing.
  const eqBorn = live.reduce(
    (m, s) => ((s.kind === 'PREMIUM' || s.kind === 'DISCOUNT') && s.born > m ? s.born : m),
    -Infinity,
  )

  const zoneCut = (() => {
    const borns = live.filter((s) => s.kind === 'OB').map((s) => s.born)
    if (borns.length <= STRUCT_ZONE_LIMIT) return -Infinity
    borns.sort((a, b) => b - a)
    return borns[STRUCT_ZONE_LIMIT - 1]
  })()

  // Boxes first, so a translucent fill never washes over a tick, a pool line
  // or a label drawn below.
  for (const s of live) {
    if (s.kind !== 'OB') continue
    if (s.born < zoneCut) continue
    const t0 = times[s.i0]
    if (t0 == null) continue
    const x0 = conv.timeToX(t0) - half
    const yHi = conv.priceToY(s.hi)
    const yLo = conv.priceToY(s.lo)
    if (!Number.isFinite(x0) || !Number.isFinite(yHi) || !Number.isFinite(yLo)) continue
    // Right edge is the last VISIBLE bar, i.e. the replay cursor when one is
    // set. Whether a gap has since been filled is a later-bar question, so
    // extending past the cursor would answer it with data the operator has
    // scrubbed away from.
    if (cutX <= x0) continue
    const top = Math.min(yHi, yLo)
    const h = Math.abs(yLo - yHi)
    const sc = scale(s)
    ctx.fillStyle = withAlpha(brass, STRUCT_ALPHA[mode] * sc)
    ctx.fillRect(x0, top, cutX - x0, h)
    ctx.lineWidth = 1
    ctx.strokeStyle = withAlpha(brass, STRUCT_BORDER_ALPHA * sc)
    // UNKNOWN gets a dashed border — "could not be checked" reads differently
    // from UNCONFIRMED's solid one even with the label gone.
    if (s.confirm === 'UNKNOWN') ctx.setLineDash(STRUCT_POOL_DASH)
    ctx.strokeRect(x0, top, cutX - x0, h)
    if (s.confirm === 'UNKNOWN') ctx.setLineDash([]) // never let dash state leak into the next stroke/fill
  }

  ctx.font = `${STRUCT_LABEL_PX}px ${MONO_STACK}`
  ctx.textBaseline = 'middle'
  ctx.lineWidth = 1

  /** Draw `text` at (x, y) unless it would leave the pane, overprint the
   *  engine's OHLC legend, or collide with a label already placed. Only the
   *  TEXT de-clutters — the structure's own box/tick/line is already drawn,
   *  the same bargain the level labels below make (line always, label when it
   *  clears). */
  const placeLabel = (text: string, x: number, y: number, color: string) => {
    if (!text) return // unconfirmed/unchecked structures draw their shape only
    const w = ctx.measureText(text).width
    const box: LabelBox = {
      x0: x, y0: y - STRUCT_LABEL_PX / 2 - 1,
      x1: x + w, y1: y + STRUCT_LABEL_PX / 2 + 1,
    }
    if (box.x0 < pane.x || box.x1 > pane.x + pane.width - 2) return
    if (box.y0 < pane.y + LEGEND_BAND_PX || box.y1 > pane.y + pane.height - 2) return
    for (const t of taken) {
      if (box.x0 < t.x1 && box.x1 > t.x0 && box.y0 < t.y1 && box.y1 > t.y0) return
    }
    taken.push(box)
    ctx.fillStyle = color
    ctx.fillText(text, x, y)
  }

  for (const s of live) {
    const sc = scale(s)
    const color = withAlpha(brass, 0.85 * sc)
    // Text is for the FLOW-CONFIRMED few only. A real session carries ~180
    // structures of which ~90% are UNCONFIRMED or UNKNOWN, and labelling them
    // all buried the candles under "OB unchecked / EQH unconfirmed" — the exact
    // 479-label noise problem spec §7 exists to avoid. The unlabelled ones are
    // NOT hidden: every shape still draws, and its opacity + dashed-vs-solid
    // border still distinguish unconfirmed from unchecked (see the constants).
    const label = s.confirm === 'CONFIRMED' ? s.kind + suffix(s) : ''

    if (s.kind === 'OB') {
      if (s.born < zoneCut) continue // same newest-N cap the fills above use
      const t0 = times[s.i0]
      if (t0 == null) continue
      const x0 = conv.timeToX(t0) - half
      const yHi = conv.priceToY(s.hi)
      const yLo = conv.priceToY(s.lo)
      if (!Number.isFinite(x0) || !Number.isFinite(yHi) || !Number.isFinite(yLo)) continue
      const top = Math.min(yHi, yLo)
      const h = Math.abs(yLo - yHi)
      // Inside the box when it can hold the text; just above it otherwise. An
      // 8.5px label crammed into a 3px gap reads as a different structure.
      // Clamped to the pane's left edge rather than the box's own: at the
      // default 160-bar view most boxes start left of the viewport, and an
      // unclamped x there is exactly what made placeLabel's own edge bail
      // drop the label instead of sliding it onto the visible box.
      placeLabel(label, Math.max(x0 + 2, pane.x + 2),
        h >= STRUCT_LABEL_PX + 2 ? top + h / 2 : top - STRUCT_LABEL_PX / 2 - 1, color)
      continue
    }

    // Prior-session levels: drawn across the WHOLE pane and always labelled.
    // There are exactly three of them, they are known before the session opens,
    // and they are reference levels rather than events — the label-suppression
    // rule above (confirmed-only) exists to thin ~180 intraday marks and would
    // be actively wrong here. Their `confirm` is UNKNOWN by construction (a
    // prior session's level has no flow in this payload), so the suffix is
    // dropped: "PDH unchecked" would imply a flow question that was never asked.
    if (s.kind === 'PDH' || s.kind === 'PDL' || s.kind === 'PDC') {
      const y = conv.priceToY(s.hi)
      if (!Number.isFinite(y)) continue
      if (y < pane.y + LEGEND_BAND_PX || y > pane.y + pane.height - 2) continue
      ctx.strokeStyle = withAlpha(brass, 0.7)
      ctx.setLineDash([7, 5])
      ctx.beginPath()
      ctx.moveTo(pane.x, y)
      ctx.lineTo(pane.x + pane.width, y)
      ctx.stroke()
      ctx.setLineDash([])
      placeLabel(`${s.kind} ${s.hi.toFixed(1)}`, pane.x + 3, y - STRUCT_LABEL_PX,
        withAlpha(brass, 0.95))
      continue
    }

    // PREMIUM / DISCOUNT: only the CURRENT pair is drawn (see `eqBorn` above).
    // The backend re-cuts the range ~45 times a session; every cut is published
    // so replay can show the range as it stood at any bar, but painting all of
    // them at once would be 90 overlapping bands describing one moving line.
    if (s.kind === 'PREMIUM' || s.kind === 'DISCOUNT') {
      if (s.born !== eqBorn) continue
      const yMid = conv.priceToY(s.kind === 'PREMIUM' ? s.lo : s.hi) // the shared 50% edge
      const yEnd = conv.priceToY(s.kind === 'PREMIUM' ? s.hi : s.lo) // the range's own end
      if (!Number.isFinite(yMid) || !Number.isFinite(yEnd)) continue
      // The equilibrium line itself, drawn once (PREMIUM's lo === DISCOUNT's hi).
      if (s.kind === 'PREMIUM' && yMid > pane.y + LEGEND_BAND_PX && yMid < pane.y + pane.height - 2) {
        ctx.strokeStyle = withAlpha(brass, 0.6)
        ctx.setLineDash([2, 3])
        ctx.beginPath()
        ctx.moveTo(pane.x, yMid)
        ctx.lineTo(pane.x + pane.width, yMid)
        ctx.stroke()
        ctx.setLineDash([])
        placeLabel(`EQ ${s.lo.toFixed(1)}`, pane.x + 3, yMid - STRUCT_LABEL_PX,
          withAlpha(brass, 0.9))
      }
      // The half's own name, at the far right against its outer edge, so the
      // two halves are named without tinting the price area the operator just
      // asked to keep clean.
      const yLab = (yMid + yEnd) / 2
      if (yLab > pane.y + LEGEND_BAND_PX && yLab < pane.y + pane.height - 2) {
        const w = ctx.measureText(s.kind).width
        placeLabel(s.kind, pane.x + pane.width - w - CHIP_MARGIN - 52, yLab,
          withAlpha(brass, 0.75))
      }
      continue
    }

    // SWING_H / SWING_L: a short tick CENTRED on the pivot bar, never
    // labelled. Suppressed entirely until 2026-08-07 — the note that used to
    // sit at the bottom of this loop said each is already the endpoint of an
    // OB or an EQH/EQL pool and that 51 of them a session bury the structures
    // that carry a claim. Both halves of that are still true, which is exactly
    // why this draws the pivot and does NOT name it: adding "SWING_H" beside
    // an OB's own label would print two names for one price. The budget for
    // the marks themselves came from dropping FVG and BOS/CHoCH.
    //
    // `levelOf` is wrong here. It picks hi for a bullish structure, and a
    // SWING_L's `dir` is -1 while the price that matters is its low — the two
    // agree by luck on a point structure where hi === lo, and this does not
    // rely on that.
    if (s.kind === 'SWING_H' || s.kind === 'SWING_L') {
      const tb = times[s.born]
      if (tb == null) continue
      const xb = Math.min(conv.timeToX(tb), cutX)
      const y = conv.priceToY(s.kind === 'SWING_H' ? s.hi : s.lo)
      if (!Number.isFinite(xb) || !Number.isFinite(y)) continue
      if (y < pane.y + 1 || y > pane.y + pane.height - 1) continue
      // Faintest mark in the layer. A pivot is a location, not a claim, so it
      // sits below every shape that asserts something about flow.
      ctx.strokeStyle = withAlpha(brass, 0.45 * sc)
      ctx.beginPath()
      ctx.moveTo(Math.max(pane.x, xb - STRUCT_SWING_PX), y)
      ctx.lineTo(Math.min(pane.x + pane.width, xb + STRUCT_SWING_PX), y)
      ctx.stroke()
      continue
    }

    if (s.kind === 'EQH' || s.kind === 'EQL') {
      const t0 = times[s.i0]
      const tb = times[s.born]
      if (t0 == null || tb == null) continue
      const x0 = conv.timeToX(t0)
      const x1 = Math.min(conv.timeToX(tb), cutX)
      const y = conv.priceToY(levelOf(s))
      if (!Number.isFinite(x0) || !Number.isFinite(x1) || !Number.isFinite(y)) continue
      if (x1 <= x0 || y < pane.y + 1 || y > pane.y + pane.height - 1) continue
      ctx.strokeStyle = color
      ctx.setLineDash(STRUCT_POOL_DASH)
      ctx.beginPath()
      ctx.moveTo(x0, y)
      ctx.lineTo(x1, y)
      ctx.stroke()
      ctx.setLineDash([]) // never let dash state leak into the next stroke/fill
      // Same right-edge fallback as BOS/CHoCH above: the pool's `born` end is
      // the same ~5-bar right margin the newest break lands in.
      {
        const w = ctx.measureText(label).width
        const rightX = x1 + STRUCT_LABEL_GAP
        const lx = rightX + w > pane.x + pane.width - 2 ? x1 - STRUCT_LABEL_GAP - w : rightX
        placeLabel(label, lx, y, color)
      }
      continue
    }

    // Anything reaching here is a kind this layer does not draw — FVG, BOS and
    // CHOCH as of 2026-08-07, plus any kind structure.py adds later. Falling
    // through silently is correct for a RENDERER (an unknown shape must never
    // be guessed at), and it is not silent to the operator: TradeTab counts
    // exactly this set and says so in the `Hidden:` line.
  }
}

/** Rightmost drawn edge per side (0 = above the high, 1 = below the low) per
 *  lane. One array is shared by the rotation pass and the balloon pass, which
 *  is what keeps a setup marker and an event pill off each other. */
type LaneRight = [number[], number[]]

/** A fresh lane ledger — `PILL_LANES` empty lanes on each side. */
function newLanes(): LaneRight {
  return [
    Array(PILL_LANES).fill(-Infinity),  // lanes above the high
    Array(PILL_LANES).fill(-Infinity),  // lanes below the low
  ]
}

/**
 * Which lane a pill starting at `px` on `side` can use — the first whose
 * occupant it clears. `keep` decides what happens when every lane is taken:
 * true returns the least-occupied one anyway (nothing is ever dropped), false
 * returns −1 so the caller can de-clutter instead.
 *
 * Does NOT mutate: a pill can still bail on the pane bounds after choosing a
 * lane, and one that never draws must not reserve space. `takeLane` is the
 * commit, called only once the pill is certain to paint.
 */
function pickLane(lanes: LaneRight, side: 0 | 1, px: number, keep: boolean): number {
  const row = lanes[side]
  for (let l = 0; l < PILL_LANES; l++) {
    if (px >= row[l]) return l
  }
  if (!keep) return -1
  let best = 0
  for (let l = 1; l < PILL_LANES; l++) if (row[l] < row[best]) best = l
  return best
}

/** Commit a placed pill's footprint to its lane. */
function takeLane(lanes: LaneRight, side: 0 | 1, lane: number, px: number, pillW: number) {
  lanes[side][lane] = px + pillW + PILL_GUTTER
}

/**
 * Band-rotation markers: the operator's OWN setup, drawn where it fired.
 *
 * Every one of these is the BACKEND's — band_rotation.detect_index found the
 * tag and the same-bar reversal on the index's own bars; this function only
 * positions it. It is a different claim from an event balloon (that is
 * something the engine observed; this is the operator's setup printing), so it
 * is deliberately a different SHAPE: a triangle on the σ band the bar actually
 * pierced, a stem, and a square-cornered pill naming the direction and the
 * band ("▲ BUY d2").
 *
 * A BUY marker hangs below the bar's low, a SELL above its high — the side the
 * reversal came from, so the mark sits where the operator's eye already is.
 *
 * The compression read rides as opacity + border style, never as suppression:
 * CLEAR full and solid; SUSPECT faded and solid (checked, the index was not
 * squeezing); UNKNOWN in between and DASHED (could not be checked). A signal
 * is NEVER dropped for its trap verdict — "we found nothing" and "we are not
 * showing you" are different statements.
 *
 * `confirm` is not drawn at all: on an index series it is UNKNOWN by
 * construction (there is no opposite leg), so a per-marker "unchecked" badge
 * would imply a question that varies between signals when it never does. The
 * hover callout carries the backend's sentence in full.
 */
function drawRotation(
  ctx: CanvasRenderingContext2D,
  conv: Converters,
  pane: PaneRect,
  pal: Palette,
  bars: TapeBar[],
  times: number[],
  rotation: (RotationSignal | null)[],
  lastIdx: number,
  lanes: LaneRight,
) {
  if (lastIdx < 0) return
  ctx.font = `bold 10px ${MONO_STACK}`
  ctx.textBaseline = 'middle'
  // Causality plus the arrays' own bounds — rotation/times are built 1:1 with
  // bars, but a mid-poll render can see them one append apart.
  const n = Math.min(lastIdx, rotation.length - 1, bars.length - 1, times.length - 1)
  // ONE plan decides what is drawn, and the legend reports the same object —
  // so the number the operator reads can never drift from what is on screen.
  // Built over `n`, not `lastIdx`, because a marker past the shorter array is
  // not drawable and must not be counted as drawn either.
  const plan = runDrawPlan(rotation, n)
  for (let i = 0; i <= n; i++) {
    const sig = rotation[i]
    if (!sig) continue
    if (!plan.drawn[i]) continue
    const buy = sig.side === 'BUY'
    // Direction, so theme.ts puts it on bull/bear. The SHAPE is what tells it
    // apart from an event balloon; the hue is what tells the operator which
    // way it leans, and borrowing brass here would say "structure" instead.
    const tone = buy ? pal.bull : pal.bear
    const alpha = sig.trap === 'CLEAR' ? 1
      : sig.trap === 'UNKNOWN' ? ROT_UNKNOWN_ALPHA : ROT_SUSPECT_ALPHA
    const stroke = withAlpha(tone, alpha)

    const x = conv.timeToX(times[i])
    if (!Number.isFinite(x)) continue
    if (x < pane.x - 2 || x > pane.x + pane.width + 2) continue // panned out
    // The σ level the bar actually pierced, read off the bar itself — the same
    // per-bar band the ribbons above are drawn from, never re-derived here.
    const level = bars[i][sig.band]
    const bandY = conv.priceToY(level)
    const extremeY = conv.priceToY(buy ? bars[i].l : bars[i].h)
    if (!Number.isFinite(bandY) || !Number.isFinite(extremeY)) continue
    // Hang off whichever is further out — the band or the candle's own
    // extreme. The wick pierced the band, so which one that is depends on how
    // far past it price went, and anchoring on the band alone would put the
    // pill inside the candle on a deep piercing bar.
    const anchorY = buy ? Math.max(bandY, extremeY) : Math.min(bandY, extremeY)

    const text = `${buy ? '▲' : '▼'} ${sig.side} ${sig.band}`
    const pillW = ctx.measureText(text).width + PILL_PAD_X * 2
    if (pillW + 4 > pane.width) continue // pane cannot hold this pill at all
    const px = Math.max(pane.x + 2, Math.min(x - pillW / 2, pane.x + pane.width - 2 - pillW))
    const side: 0 | 1 = buy ? 1 : 0
    // `keep` is true: the operator's own setup is never de-cluttered away.
    const lane = pickLane(lanes, side, px, true)
    const off = ROT_STEM + lane * PILL_LANE_STEP
    // CLAMPED into the pane, not dropped. A story balloon that will not fit
    // simply bails — it is one of many, and the ribbon and the callout still
    // carry it. A setup marker has no such second home, and the +3σ case makes
    // this concrete: a SELL hangs off a band sitting near the top of the pane,
    // so the outward placement lands over the engine's OHLC legend and the
    // whole signal would silently vanish (measured: 2 of 15 on the live
    // 2026-07-31 NIFTY session). Moving the pill is safe because the STEM is
    // still drawn from the true band y and the triangle still sits ON the
    // band, so nothing about WHERE the signal fired is altered — only where
    // its label is parked, exactly as `px` already slides horizontally.
    const topLimit = pane.y + LEGEND_BAND_PX
    const botLimit = pane.y + pane.height - 2 - PILL_H
    if (botLimit < topLimit) continue          // pane too short to hold a pill
    const pillTop = Math.max(topLimit,
      Math.min(buy ? anchorY + off : anchorY - off - PILL_H, botLimit))
    takeLane(lanes, side, lane, px, pillW)

    // The band mark: a filled triangle sitting ON the pierced σ level,
    // pointing the way the bar reversed. Nothing else on this chart is drawn
    // at a σ level, which is what makes a setup marker unmistakable.
    ctx.fillStyle = stroke
    ctx.beginPath()
    if (buy) {
      ctx.moveTo(x, bandY - ROT_TRI_PX)
      ctx.lineTo(x - ROT_TRI_PX, bandY + ROT_TRI_PX)
      ctx.lineTo(x + ROT_TRI_PX, bandY + ROT_TRI_PX)
    } else {
      ctx.moveTo(x, bandY + ROT_TRI_PX)
      ctx.lineTo(x - ROT_TRI_PX, bandY - ROT_TRI_PX)
      ctx.lineTo(x + ROT_TRI_PX, bandY - ROT_TRI_PX)
    }
    ctx.closePath()
    ctx.fill()

    // Stem from the band mark to the pill, through the candle's extreme.
    ctx.strokeStyle = withAlpha(tone, alpha * 0.5)
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(x, bandY)
    ctx.lineTo(x, buy ? pillTop : pillTop + PILL_H)
    ctx.stroke()

    // The pill: square corners and a heavier border, so it does not read as
    // one of the rounded story balloons even in a screenshot.
    roundedRectPath(ctx, px, pillTop, pillW, PILL_H, ROT_PILL_R)
    ctx.fillStyle = withAlpha(pal.card, 0.92)
    ctx.fill()
    ctx.lineWidth = ROT_BORDER_PX
    ctx.strokeStyle = stroke
    // UNKNOWN compression gets a dashed border — "could not be checked" reads
    // differently from SUSPECT's solid one even with the colour washed out.
    if (sig.trap === 'UNKNOWN') ctx.setLineDash(ROT_DASH)
    ctx.stroke()
    ctx.setLineDash([]) // never let dash state leak into the next stroke/fill
    ctx.lineWidth = 1
    ctx.fillStyle = stroke
    ctx.fillText(text, px + PILL_PAD_X, pillTop + PILL_H / 2)
  }
}

/**
 * Story balloons: a persistent pill for every tier-≥2 narration, so the day's
 * events stay legible after the mouse has moved on — the hover callout alone
 * cannot be "referred to later".
 *
 * Placement: bear tone above the candle's high, bull tone below its low,
 * structure/neutral above the high. Laid out left→right; a pill that would
 * collide with the one already in its lane steps one lane further out, up to
 * `PILL_LANES`. Past that, tier 2 is dropped (the ribbon and the callout still
 * carry it — this only de-clutters) and tier 3 is kept in whichever lane it
 * overlaps least, because a sprung trap must never silently vanish.
 */
function drawBalloons(
  ctx: CanvasRenderingContext2D,
  conv: Converters,
  pane: PaneRect,
  pal: Palette,
  bars: TapeBar[],
  times: number[],
  narrs: (Narration | null)[],
  lastIdx: number,
  /** Rightmost drawn edge per side per lane, SHARED with the rotation pass
   *  (which runs first and takes the inner lanes) so the two layers cannot
   *  overprint each other. Mutated as pills are placed. */
  laneRight: LaneRight,
) {
  if (lastIdx < 0) return
  ctx.font = `10px ${MONO_STACK}`
  ctx.textBaseline = 'middle'
  ctx.lineWidth = 1
  // Causality plus the arrays' own bounds — narrs/times are built 1:1 with
  // bars, but a mid-poll render can see them one append apart.
  const n = Math.min(lastIdx, narrs.length - 1, bars.length - 1, times.length - 1)
  for (let i = 0; i <= n; i++) {
    const nr = narrs[i]
    if (!nr || nr.tier < 2) continue
    const below = nr.tone === 'bull'
    // theme.ts's rule: green/red is DIRECTION, brass is STRUCTURE. A toneless
    // (neutral) event gets the muted text colour rather than borrowing either.
    const tone = nr.tone === 'bull' ? pal.bull
      : nr.tone === 'bear' ? pal.bear
        : nr.tone === 'structure' ? pal.accent
          : pal.textSecondary
    const x = conv.timeToX(times[i])
    const anchorY = conv.priceToY(below ? bars[i].l : bars[i].h)
    if (!Number.isFinite(x) || !Number.isFinite(anchorY)) continue
    if (x < pane.x - 2 || x > pane.x + pane.width + 2) continue // panned out of the pane
    // Hinglish caption, so a balloon says what happened rather than naming a
    // category. An unglossed kind falls back to the engine's own string.
    const text = pillText(nr.kind).toUpperCase()
    const pillW = ctx.measureText(text).width + PILL_PAD_X * 2
    if (pillW + 4 > pane.width) continue // pane cannot hold this pill at all
    // Centred on the bar, then nudged to stay inside the pane. The STEM below
    // still uses the bar's true x, so a nudged pill never mislabels a bar.
    const px = Math.max(pane.x + 2, Math.min(x - pillW / 2, pane.x + pane.width - 2 - pillW))
    const side: 0 | 1 = below ? 1 : 0
    // De-clutter: tier 2 yields when every lane is taken, tier 3 never does.
    const lane = pickLane(laneRight, side, px, nr.tier >= 3)
    if (lane < 0) continue
    const off = PILL_STEM + lane * PILL_LANE_STEP
    const pillTop = below ? anchorY + off : anchorY - off - PILL_H
    // Never outside the pane rect, and never over the engine's OHLC legend.
    if (pillTop < pane.y + LEGEND_BAND_PX) continue
    if (pillTop + PILL_H > pane.y + pane.height - 2) continue
    takeLane(laneRight, side, lane, px, pillW)

    ctx.strokeStyle = withAlpha(tone, 0.5)
    ctx.beginPath()
    ctx.moveTo(x, anchorY)
    ctx.lineTo(x, below ? pillTop : pillTop + PILL_H)
    ctx.stroke()

    roundedRectPath(ctx, px, pillTop, pillW, PILL_H, PILL_R)
    if (nr.tier >= 3) {
      // Tier 3 is the loud one: solid tone, panel-coloured text.
      ctx.fillStyle = tone
      ctx.fill()
      ctx.fillStyle = pal.card
    } else {
      ctx.fillStyle = withAlpha(pal.card, 0.85)
      ctx.fill()
      ctx.strokeStyle = tone
      ctx.stroke()
      ctx.fillStyle = tone
    }
    ctx.fillText(text, px + PILL_PAD_X, pillTop + PILL_H / 2)
  }
}

export function startLevelsOverlay(
  canvas: HTMLCanvasElement,
  host: HTMLElement,
  engine: IChartEngine,
  getLevels: () => MapLevel[],
  getMode: () => Mode,
  getData: () => OverlayData,
  getZones: () => Zone[],
  /** The backend's structure layer, or null when its bar indices cannot be
   *  trusted (data.ts's skip guard) — in which case NOTHING is drawn and
   *  TradeTab prints the reason instead. Misaligned boxes would be a lie. */
  getStructures: () => Structure[] | null,
  /** The SMC toggle. Off means the operator asked for the layer to be hidden,
   *  which is not the same as the layer being unavailable. */
  getSmc: () => boolean,
  /** The event-derived layers drawn OVER the price area — the zone/condition
   *  bands and the story balloons. Default off, because neither was ever
   *  scored: signal_review.py measured the engine's own directional events at
   *  -0.1 pts (`risk`) and -6.2 pts (`lean`) at +30m against a +4.1 control,
   *  and the tab draws ~83 of them a session at equal visual weight. Unproven
   *  is not the same as wrong, so nothing is deleted — it is opt-in, and
   *  TradeTab's legend reports how many are being withheld. */
  getStory: () => boolean,
): () => void {
  const ctx = canvas.getContext('2d')!
  let raf = 0
  let lastSig = ''

  const draw = () => {
    raf = requestAnimationFrame(draw)
    const dpr = Math.max(1, window.devicePixelRatio || 1)
    const w = host.clientWidth, h = host.clientHeight
    const bw = Math.round(w * dpr), bh = Math.round(h * dpr)
    if (canvas.width !== bw || canvas.height !== bh) {
      canvas.width = bw
      canvas.height = bh
      // A canvas is a REPLACED element: with position:absolute and inset:0 it
      // takes its intrinsic size from these width/height attributes instead of
      // stretching to the parent, so the CSS size must be set explicitly or the
      // overlay renders dpr× too large and every level line misaligns.
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
    }

    const conv = engine.getMainConverters()
    const pane = engine.getMainPaneRect()
    if (!conv || !pane) return // engine not laid out yet — draw nothing, never guess

    const mode = getMode()
    const pal = palette(mode)

    // Cheap per-frame guard: if nothing the drawing depends on has moved since
    // the last frame, skip the clear + redraw entirely. Not touching the canvas
    // means no repaint is queued, so the compositor stays idle between the
    // ~once-per-5s level updates and the rare pan/zoom/resize/mode switch.
    // `mode` is part of the signature so a theme toggle repaints immediately.
    const levels = getLevels()
    const data = getData()
    const zones = getZones()
    const smc = getSmc()
    const story = getStory()
    const structures = getStructures()
    // Drawn only when the operator asked for it AND the indices are
    // trustworthy. `structs.length === 0` and `structures === null` both draw
    // nothing, but they are different facts, and the signature below keeps
    // them apart so the disclosure in TradeTab and this layer never disagree.
    const structs = smc && structures ? structures : []
    const dBars = data.bars
    const dTimes = data.times
    const dNarrs = data.narrs
    // Null (cannot be aligned) and an all-null array (aligned, nothing fired)
    // are different facts. Both draw nothing; the signature below keeps them
    // apart so this layer and TradeTab's disclosure never disagree.
    const dRot = data.rotation
    // Causality clamp: the last drawn bar for EVERY per-bar pass (ribbons,
    // zone bands, balloons) is the replay cursor, same as the candles — never
    // the newest bar the cursor is hiding.
    const lastIdx = dBars.length
      ? (data.cursor != null ? Math.max(0, Math.min(data.cursor, dBars.length - 1)) : dBars.length - 1)
      : -1
    const dFirst = dBars[0]
    const dLast = lastIdx >= 0 ? dBars[lastIdx] : undefined
    // What the balloon pass actually depends on, in one no-allocation pass:
    //  - lastNarr:  `narrs.length` alone cannot see a `null` slot BECOMING a
    //    Narration on a bar that already existed (the poll that appends bar N
    //    also fills bar N-1's event), so without this a fresh event would
    //    never repaint.
    //  - tierSum:   nor can either of those see a narration's TIER change in
    //    place — buildNarration keeps the highest-tier event of a minute, so a
    //    TRAP-SPRUNG arriving into a minute that already held a STATE takes it
    //    1 → 3 and a balloon must appear. Index-weighted, so a single bar's
    //    tier moving always moves the sum.
    //  - nBalloons: the count actually drawn, which pins a 2 → 3 restyle too.
    // ~375 iterations of three integer ops, no allocation — and every value is
    // constant between frames, so the skip still holds and paint does not
    // collapse back to the ~3fps this guard was added to fix.
    let lastNarr = -1
    let tierSum = 0
    let nBalloons = 0
    for (let i = 0; i < dNarrs.length; i++) {
      const nr = dNarrs[i]
      if (!nr) continue
      lastNarr = i
      tierSum += (i + 1) * nr.tier
      if (nr.tier >= 2) nBalloons++
    }
    // What the rotation pass depends on, in the same no-allocation style as
    // the narration scan above:
    //  - nRot / lastRot: a new signal appears (count moves, last index moves).
    //  - lastSig*:       the NEWEST signal can still change in place. The
    //    forming bar's trap verdict resolves as the run-up grows, and its
    //    band can deepen from d2 to d3 within the same minute if the low
    //    extends — both restyle a marker that is already drawn, at an
    //    unchanged count. Everything older is settled and constant between
    //    frames, so the skip guard still holds.
    let nRot = 0
    let lastRot = -1
    let lastRotBand = ''
    let lastRotTrap = ''
    let lastRotSide = ''
    if (dRot) {
      for (let i = 0; i < dRot.length; i++) {
        const r = dRot[i]
        if (!r) continue
        nRot++
        lastRot = i
        lastRotBand = r.band
        lastRotTrap = r.trap
        lastRotSide = r.side
      }
    }
    const z0 = zones[0]
    const zN = zones[zones.length - 1]
    // Signature additions for the ribbons: bar count and cursor catch any
    // append/replay-scrub, and the first+last VISIBLE bar's u1/d1 catch a
    // sigma value changing in place (e.g. a live VWAP/σ recompute on the same
    // bar count) — cheap because it reads 2 bars, never all ~375 every frame.
    // Then the four narration fields computed above (balloons), and the zone
    // count + first/last run bounds and class (bands): closed bars never
    // change verdict, so the only run that moves is the last one — whose i1
    // grows each minute — and a new verdict starts a new run, changing the
    // count. A verdict rewritten inside an already-closed middle run would be
    // missed, which the backend does not do.
    const sig = `${mode}|${bw}x${bh}|${pane.x},${pane.y},${pane.width},${pane.height}` +
      `|${conv.priceToY(0)},${conv.priceToY(1000)}` +
      // Two TIME probes as well as the two price probes. `timeToX` is a pure
      // linear map off view.start/range/plotWidth with no clamping (scales.ts
      // indexToX), so these two numbers pin the horizontal transform exactly.
      // The price probes alone only catch a pan indirectly — via the autoscale
      // recompute — and would miss one across a flat stretch, leaving the zone
      // bands and the balloons frozen at the old x while the candles moved.
      // Constant between frames unless the view actually moves, so the skip
      // still holds.
      `|${conv.timeToX(0)},${conv.timeToX(60000)}` +
      `|${levels.map((l) => `${l.kind}:${l.value}:${l.label}`).join(';')}` +
      // `times` is written by the data effect, `bars` during render, so the two
      // can be one append apart for a frame. Its length is in the signature so
      // the frame where they resync repaints — otherwise every per-bar pass
      // would stay one bar short until the next poll.
      `|${dBars.length},${dTimes.length},${data.cursor}` +
      `|${dFirst?.u1},${dFirst?.d1},${dLast?.u1},${dLast?.d1}` +
      `|${dNarrs.length},${lastNarr},${tierSum},${nBalloons}` +
      // Rotation markers: availability (null vs an aligned array — two
      // different facts), the array length, how many fired, and the newest
      // signal's index/side/band/trap for the in-place changes above.
      `|${dRot ? dRot.length : 'x'},${nRot},${lastRot},` +
      `${lastRotSide}${lastRotBand}${lastRotTrap}` +
      // `label` rather than `cls`: a verdict RENAME within the same cls (e.g.
      // one CAUTION sentence replacing another) changes neither the class nor
      // the run bounds, but it is drawn text — `cls` alone would miss it and
      // leave the old sentence painted.
      `|${zones.length},${z0?.i0}:${z0?.i1}:${z0?.label},${zN?.i0}:${zN?.i1}:${zN?.label}` +
      // Structures: the toggle, the availability (null vs an empty list — two
      // different facts), the count, and the first/last `born`. A new
      // structure moves the count; the newest one moves the last born.
      // Everything already-born and fully settled stays constant — EXCEPT the
      // most recent structure while it is still forming: structure.py can
      // still tighten its box (hi/lo) or resolve its confirm from
      // UNKNOWN/UNCONFIRMED once later flow data arrives, same `born`. The
      // last structure's confirm + rounded hi/lo (rounded to match this
      // file's own price-text style, e.g. the level chips above) are added so
      // that in-place shift repaints too, without keying anything per-frame.
      // `story` belongs here for the same reason `smc` does: the frame-skip
      // guard would otherwise hold the last painted frame after a toggle, and
      // the layer would appear stuck on until something else moved.
      `|${story ? 1 : 0},${zones.length}` +
      `|${smc ? 1 : 0}${structures ? '' : 'x'},${structs.length},` +
      `${structs[0]?.born},${structs[structs.length - 1]?.born},` +
      `${structs[structs.length - 1]?.confirm},` +
      `${structs[structs.length - 1]?.hi?.toFixed(1)},${structs[structs.length - 1]?.lo?.toFixed(1)}`
    if (sig === lastSig) return
    lastSig = sig

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    // Zone bands FIRST — the market-condition wash is the backdrop everything
    // else reads against, so it must sit under the σ ribbons, not over them.
    if (lastIdx >= 0 && zones.length && story) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      drawZones(ctx, conv, pane, dTimes, zones, lastIdx, mode)
      ctx.restore()
    }

    // The level labels are DECIDED here, before anything else draws, though
    // they are PAINTED further down in layer order. Two readers need one
    // answer: the structure pass (which must not overprint a price level's
    // label) and the level pass itself. Deciding twice would risk them
    // disagreeing about which labels exist.
    ctx.font = `10px ${MONO_STACK}`
    // Copy before sorting — getLevels() may return the live MAP.levels array,
    // and mutating it would corrupt whatever else reads it.
    const visible = levels
      .filter((lvl) => lvl.kind !== 'now') // the tape itself is the price
      .map((lvl) => ({ lvl, y: conv.priceToY(lvl.value) }))
      .filter(({ y }) => y >= pane.y + 4 && y <= pane.y + pane.height - 4)
      .sort((a, b) => a.y - b.y)
    // A label is drawn only if it clears the last DRAWN label by the min gap
    // AND clears the engine's own OHLC legend in the top-left of the pane.
    const takenLabels: LabelBox[] = []
    const labelled: boolean[] = []
    {
      let lastLabelY = -Infinity // last *drawn label's* y, not the last level's y
      for (const { lvl, y } of visible) {
        const ok = y - lastLabelY >= LABEL_GAP && y >= pane.y + LEGEND_BAND_PX
        labelled.push(ok)
        if (ok) {
          lastLabelY = y
          const w = ctx.measureText(`${lvl.label} ${lvl.value.toFixed(1)}`).width
          // Baseline 'bottom' at y-2 for a 10px font, padded by 1px each way.
          takenLabels.push({ x0: pane.x + 6, y0: y - 13, x1: pane.x + 6 + w, y1: y - 1 })
        }
        // Every visible level also gets a right-axis price chip, painted much
        // further down (~46px wide, 13px tall) regardless of whether its left
        // label cleared the collision check above. Seeded here, in the same
        // hoisted block, so the structure pass below never puts a label under
        // a chip that hasn't been painted yet.
        const chipW = ctx.measureText(lvl.value.toFixed(1)).width + CHIP_PAD * 2
        const chipX = pane.x + pane.width - chipW - CHIP_MARGIN
        takenLabels.push({ x0: chipX, y0: y - CHIP_H / 2, x1: chipX + chipW, y1: y + CHIP_H / 2 })
      }
    }

    // Structure layer SECOND — above the market-condition wash, below the σ
    // ribbons and the level lines. It describes the same price geometry the
    // levels do, so it must not sit on top of them and win the contrast.
    if (lastIdx >= 0 && structs.length) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      drawStructures(ctx, conv, pane, pal, dTimes, structs, lastIdx, mode, takenLabels)
      ctx.restore()
    }

    // σ bands, Kite-style: five ANNULI rather than three stacked full-width
    // fills, so the blue outer / green shoulder / pink core each keep their own
    // hue (stacking three washes would render the core as the sum of all
    // three). Drawn UNDER the level lines/chips below, over the chart canvas
    // underneath this one.
    if (lastIdx >= 0) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      const fa = BAND_FILL_ALPHA[mode]
      const ea = BAND_EDGE_ALPHA[mode]
      const ring = (u: BandKey, d: BandKey, rgb: string) => drawRibbon(
        ctx, conv, dBars, dTimes, lastIdx, u, d,
        `rgba(${rgb},${fa})`, `rgba(${rgb},${ea})`,
      )
      ring('u3', 'u2', BAND_RGB.outer)
      ring('d2', 'd3', BAND_RGB.outer)
      ring('u2', 'u1', BAND_RGB.mid)
      ring('d1', 'd2', BAND_RGB.mid)
      ring('u1', 'd1', BAND_RGB.core)
      ctx.restore()
    }

    ctx.font = '10px ui-monospace, SFMono-Regular, Menlo, monospace'
    ctx.textBaseline = 'bottom'

    /* ── Proximity emphasis ────────────────────────────────────────────────
       The operator, 2026-08-07, looking at ~20 levels at once: *"lines sahi se
       nhi dikh rhi kaffi patli h same colors ki koi differenhe nhi h"* — every
       level drew at one weight and one hue, so none stood out and the eye had
       nothing to follow. Their fix, in their words: light a line up as price
       approaches it, and otherwise leave it as it was.

       WHAT THE BRIGHTNESS MEANS, and the whole of it: DISTANCE. It says "price
       is here", never "this level will hold". Which levels hold has never been
       scored, and a line that flares as price arrives is one small step from
       reading as a call. So proximity drives weight and hue only — no level is
       added, removed, re-ordered, re-labelled or withheld by it.

       Distance is measured in σ, not points, so it self-scales: NIFTY's 1σ and
       BANKNIFTY's are different numbers for the same thing, and a hard-coded
       point threshold would have become three constants that drift apart. */
    /* Both widened 2026-08-07 after the first cut did visibly nothing.
       Operator: *"jb price unko approach kr to line waise he golden kuch change
       nhi ho rha h"*. Two separate mistakes, both measured on the live tape
       (px 24651.2, 1σ 21.96):
         - FADE was 1σ. Levels routinely sit 1-3σ apart, so on most bars NO
           level was inside the ramp at all and nothing ever lit.
         - the alpha range was 0.85→1.00, a 15% change. That is invisible. */
    const NEAR_FULL = 0.35   // within a third of a σ: fully lit
    const NEAR_FADE = 3.00   // beyond three σ: resting weight
    const lastBar = lastIdx >= 0 ? dBars[lastIdx] : null
    const px = lastBar ? Number(lastBar.c) : NaN
    // One σ from the band pair the chart already draws. Degrades to NaN — and
    // every consumer below falls back to the resting look — rather than
    // guessing a width, which would light the WRONG lines with full confidence.
    const sigma1: number = lastBar
      && Number.isFinite(Number(lastBar.u1)) && Number.isFinite(Number(lastBar.d1))
      ? (Number(lastBar.u1) - Number(lastBar.d1)) / 2
      : NaN
    const usable = Number.isFinite(px) && Number.isFinite(sigma1) && sigma1 > 0
    /** 0 at NEAR_FADE σ away, 1 within NEAR_FULL σ. */
    const nearness = (v: number) => {
      if (!usable) return 0
      const d = Math.abs(v - px) / sigma1
      if (d <= NEAR_FULL) return 1
      if (d >= NEAR_FADE) return 0
      return (NEAR_FADE - d) / (NEAR_FADE - NEAR_FULL)
    }
    // The ONE level price is moving toward — nearest above on an up bar,
    // nearest below on a down bar. Only this one takes a directional hue, so
    // green/red stay rare enough to keep meaning direction (theme.ts's rule:
    // green/red are DIRECTION, brass is STRUCTURE). Tinting every level above
    // and below would make the hue ambient and it would mean nothing again —
    // the exact failure that rule was written after.
    const up = lastBar ? Number(lastBar.c) >= Number(lastBar.o) : true
    let targetIdx = -1
    if (usable) {
      let best = Infinity
      visible.forEach(({ lvl }, i) => {
        if (up ? lvl.value <= px : lvl.value >= px) return
        // A trap level is ALREADY red, and that red means "trap", not "down".
        // Letting one become the directional target would paint it green on an
        // up bar — a trap level announcing "up", which is precisely the
        // collision theme.ts's one-meaning-per-hue rule exists to prevent. It
        // still thickens with proximity; it just never changes hue.
        if (lvl.kind === 'trap') return
        const d = Math.abs(lvl.value - px)
        if (d < best) { best = d; targetIdx = i }
      })
      // The target is NOT distance-gated. It was, and that was the bug: a
      // "within 1σ or nothing" rule meant the tint almost never appeared, which
      // is exactly what the operator reported. Which level is next is worth
      // knowing at any distance; HOW CLOSE it is, is what the ramp says.
    }

    visible.forEach(({ lvl, y }, li) => {
      const near = nearness(lvl.value)
      const isTarget = li === targetIdx
      // Resting weight is what it always was — the operator asked for the rest
      // to stay put. Emphasis is bought by the near level GAINING, never by the
      // far ones losing, because "too faint" was the other half of the
      // complaint and dimming them would have made that worse.
      const hue = isTarget ? (up ? pal.bull : pal.bear)
        : lvl.kind === 'trap' ? pal.bear : pal.accent
      const color = withAlpha(hue, 0.7 + 0.3 * near)
      ctx.strokeStyle = color
      ctx.fillStyle = color

      // Always draw the line — suppressing it would hide a real price level.
      ctx.lineWidth = 1 + 1.6 * near + (isTarget ? 0.8 : 0)
      // The target draws SOLID where every other level is dashed. Hue alone is
      // a weak signal on a chart already carrying brass, red and green, and it
      // is the one signal a colour-blind reader loses entirely; the dash
      // pattern carries the same fact through a second channel.
      if (isTarget) ctx.setLineDash([])
      else ctx.setLineDash(lvl.kind === 'band' ? [2, 4] : [6, 4])
      ctx.beginPath()
      ctx.moveTo(pane.x, y)
      ctx.lineTo(pane.x + pane.width, y)
      ctx.stroke()
      ctx.setLineDash([]) // reset so dash state never leaks into the next stroke/fill
      ctx.lineWidth = 1   // and neither does width

      // Right-axis price chip: filled brass/red rect with panel-coloured text,
      // so the level reads at the axis even when its left label loses the
      // 11px collision check below.
      const priceText = lvl.value.toFixed(1)
      const chipW = ctx.measureText(priceText).width + CHIP_PAD * 2
      const chipX = pane.x + pane.width - chipW - CHIP_MARGIN
      const chipY = y - CHIP_H / 2
      ctx.fillStyle = color
      ctx.fillRect(chipX, chipY, chipW, CHIP_H)
      ctx.fillStyle = pal.card
      ctx.textBaseline = 'middle'
      ctx.fillText(priceText, chipX + CHIP_PAD, y + 0.5)
      ctx.textBaseline = 'bottom' // restore before the left label below
      ctx.fillStyle = color

      // The gap/legend decision was made above (`labelled`), before the
      // structure pass read it — same answer, one place.
      if (labelled[li]) {
        ctx.fillText(`${lvl.label} ${lvl.value.toFixed(1)}`, pane.x + 6, y - 2)
      }
    })

    // Markers LAST — the persistent pills sit above the bands, the ribbons and
    // the level lines, since they are the thing being read. The two passes
    // share ONE lane ledger, so a setup marker and an event balloon can never
    // land on top of each other; rotation runs first and takes the inner
    // lanes, because the operator's own setup is what the tab is for.
    if (lastIdx >= 0 && (dRot || (story && dNarrs.length))) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      const lanes = newLanes()
      // Rotation is NOT gated by `story`. It is the operator's own setup —
      // the only analytic here derived from their edge rather than someone
      // else's vocabulary, and the only one measured, found wrong and
      // corrected twice. The event balloons are the unscored layer.
      if (dRot) drawRotation(ctx, conv, pane, pal, dBars, dTimes, dRot, lastIdx, lanes)
      if (story && dNarrs.length) {
        drawBalloons(ctx, conv, pane, pal, dBars, dTimes, dNarrs, lastIdx, lanes)
      }
      ctx.restore()
    }
  }

  raf = requestAnimationFrame(draw)
  return () => cancelAnimationFrame(raf)
}
