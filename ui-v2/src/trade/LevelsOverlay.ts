// Levels the engine already knows, drawn over the chart. The ONLY file that
// touches CandL's coordinate system: converters are live objects and must be
// re-queried every frame (their docs say so — zoom/pan invalidates them).
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { Converters } from '../vendor/candl/drawings/types'
import type { MapLevel, Structure, TapeBar } from '../data'
import { palette } from '../theme'
import type { Mode } from '../theme'
import type { Narration } from './narration'
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
}

/** The pane geometry the engine hands out, in CSS px. */
type PaneRect = { x: number; y: number; width: number; height: number }

/** The active palette object — either `TL` or `T`; both carry these keys. */
type Palette = ReturnType<typeof palette>

// Ribbon fill alphas — the approved mockup's own ceiling (±1σ 0.075, ±2σ
// 0.055), extended with a slightly dimmer ±3σ. Widest drawn first so the
// narrower, slightly stronger ones layer on top without darkening past this.
const RIBBON_ALPHA: Record<'u1d1' | 'u2d2' | 'u3d3', number> = {
  u3d3: 0.040,
  u2d2: 0.055,
  u1d1: 0.075,
}

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
  light: { stand: 0.05, watch: 0.07 },
  dark: { stand: 0.08, watch: 0.10 },
}
// Small enough to sit just under the engine's legend band without competing
// with the 10px level labels that share the same corner.
const ZONE_LABEL_PX = 8.5

// SMC structure layer (Phase 3.5). Brass, because theme.ts's rule is that
// brass IS structure — an FVG is not a direction claim, so it must not borrow
// green/red even though it carries a `dir`. Dark needs the higher alpha for the
// same apparent tint against #0B0E14, exactly as the zone bands do; OB reads a
// touch stronger than FVG because a block is a level, a gap is a void.
const STRUCT_ALPHA: Record<Mode, Record<'FVG' | 'OB', number>> = {
  light: { FVG: 0.045, OB: 0.07 },
  dark: { FVG: 0.07, OB: 0.10 },
}
const STRUCT_BORDER_ALPHA = 0.25
// UNCONFIRMED and UNKNOWN both draw at this fraction of the above. They are
// DIFFERENT claims and their labels say so ("unconfirmed" vs "unchecked"); the
// shared dimming only says "not confirmed", which is true of both.
const STRUCT_FAINT = 0.45
const STRUCT_TICK_PX = 24        // BOS/CHoCH tick length, ending at x(born)
const STRUCT_LABEL_PX = 8.5
const STRUCT_LABEL_GAP = 3       // px between a tick/line end and its label
const STRUCT_POOL_DASH: [number, number] = [3, 3]

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

/** One σ ribbon: a filled polygon between the `uKey`/`dKey` per-bar values
 *  across bars `[0, lastIdx]`. Walks the upper edge left→right then the lower
 *  edge right→left and closes — one path per CONTIGUOUS run of finite values,
 *  so a non-finite bar (the payload can carry nulls) ends the current run and
 *  starts a new one rather than being bridged over: a hole stays a hole. */
function drawRibbon(
  ctx: CanvasRenderingContext2D,
  conv: Converters,
  bars: TapeBar[],
  times: number[],
  lastIdx: number,
  uKey: 'u1' | 'u2' | 'u3',
  dKey: 'd1' | 'd2' | 'd3',
  fillStyle: string,
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
    ctx.fillStyle = `rgba(${hue},${ZONE_ALPHA[mode][z.cls]})`
    ctx.fillRect(x0, pane.y, x1 - x0, pane.height)
    // The label is the engine's own words, upper-cased for display only. It is
    // skipped rather than truncated when the band is narrower than the text —
    // a clipped half-word reads as a different verdict.
    if (!z.label) continue
    const label = z.label.toUpperCase()
    if (ctx.measureText(label).width > x1 - x0 - 4) continue
    ctx.fillStyle = `rgb(${hue})`
    ctx.fillText(label, x0 + 2, pane.y + LEGEND_BAND_PX)
  }
}

/** An axis-aligned box already occupied by a drawn label. */
type LabelBox = { x0: number; y0: number; x1: number; y1: number }

/**
 * The SMC / ICT structure layer (Phase 3.5), drawn between the zone bands and
 * the σ ribbons. Every shape here is the BACKEND's — structure.py found it,
 * named it and confirmed it; this function only positions it.
 *
 *   FVG / OB   translucent brass box over [lo, hi], from the structure's own
 *              first bar and extended right to the last visible bar (or the
 *              replay cursor while scrubbing).
 *   BOS/CHoCH  a short tick at the broken level, ending at x(born), labelled.
 *   EQH / EQL  a dashed line across the pool, from x(i0) to x(born).
 *   SWING_H/L  deliberately not drawn — see the note at the bottom.
 *
 * Confirmation shows as opacity plus a label suffix: CONFIRMED at full alpha
 * and no suffix, UNCONFIRMED faint + "unconfirmed" (flow was checked and
 * disagreed), UNKNOWN faint + "unchecked" (flow could not be checked at all).
 * A structure is NEVER dropped for being unconfirmed: "we found nothing" and
 * "we are not showing you" are different statements.
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

  /** CONFIRMED draws at the configured alpha, the other two at a fraction of
   *  it. Never zero, and never a different hue — brass is structure. */
  const scale = (s: Structure) => (s.confirm === 'CONFIRMED' ? 1 : STRUCT_FAINT)
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

  // Boxes first, so a translucent fill never washes over a tick, a pool line
  // or a label drawn below.
  for (const s of live) {
    if (s.kind !== 'FVG' && s.kind !== 'OB') continue
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
    ctx.fillStyle = withAlpha(brass, STRUCT_ALPHA[mode][s.kind] * sc)
    ctx.fillRect(x0, top, cutX - x0, h)
    ctx.lineWidth = 1
    ctx.strokeStyle = withAlpha(brass, STRUCT_BORDER_ALPHA * sc)
    ctx.strokeRect(x0, top, cutX - x0, h)
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
    const label = s.kind + suffix(s)

    if (s.kind === 'FVG' || s.kind === 'OB') {
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
      placeLabel(label, x0 + 2,
        h >= STRUCT_LABEL_PX + 2 ? top + h / 2 : top - STRUCT_LABEL_PX / 2 - 1, color)
      continue
    }

    if (s.kind === 'BOS' || s.kind === 'CHOCH') {
      const tb = times[s.born]
      if (tb == null) continue
      const xb = Math.min(conv.timeToX(tb), cutX)
      const y = conv.priceToY(levelOf(s))
      if (!Number.isFinite(xb) || !Number.isFinite(y)) continue
      if (y < pane.y + 1 || y > pane.y + pane.height - 1) continue
      ctx.strokeStyle = color
      ctx.beginPath()
      ctx.moveTo(Math.max(pane.x, xb - STRUCT_TICK_PX), y)
      ctx.lineTo(xb, y)
      ctx.stroke()
      placeLabel(label, xb + STRUCT_LABEL_GAP, y, color)
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
      placeLabel(label, x1 + STRUCT_LABEL_GAP, y, color)
      continue
    }

    // SWING_H / SWING_L arrive in the payload and are typed in data.ts, but
    // are deliberately not drawn at this task's scope: each is already the
    // endpoint of a BOS, an EQH/EQL pool or an OB, and on the live 329-bar
    // NIFTY session there are 51 of them — enough pivot marks to bury the
    // structures that actually carry a claim.
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
) {
  if (lastIdx < 0) return
  ctx.font = `10px ${MONO_STACK}`
  ctx.textBaseline = 'middle'
  ctx.lineWidth = 1
  // Rightmost drawn edge per side per lane: a pill only steps outward when it
  // would actually collide with the pill already occupying that lane, so a
  // sparse morning does not push the afternoon's events into orbit.
  const laneRight: [number[], number[]] = [
    [-Infinity, -Infinity, -Infinity], // lanes above the high
    [-Infinity, -Infinity, -Infinity], // lanes below the low
  ]
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
    const text = nr.kind.toUpperCase()
    const pillW = ctx.measureText(text).width + PILL_PAD_X * 2
    if (pillW + 4 > pane.width) continue // pane cannot hold this pill at all
    // Centred on the bar, then nudged to stay inside the pane. The STEM below
    // still uses the bar's true x, so a nudged pill never mislabels a bar.
    const px = Math.max(pane.x + 2, Math.min(x - pillW / 2, pane.x + pane.width - 2 - pillW))
    const side = below ? 1 : 0
    const lanes = laneRight[side]
    let lane = -1
    for (let l = 0; l < PILL_LANES; l++) {
      if (px >= lanes[l]) { lane = l; break }
    }
    if (lane < 0) {
      if (nr.tier < 3) continue // de-clutter: tier 2 yields, tier 3 never does
      let best = 0
      for (let l = 1; l < PILL_LANES; l++) if (lanes[l] < lanes[best]) best = l
      lane = best
    }
    const off = PILL_STEM + lane * PILL_LANE_STEP
    const pillTop = below ? anchorY + off : anchorY - off - PILL_H
    // Never outside the pane rect, and never over the engine's OHLC legend.
    if (pillTop < pane.y + LEGEND_BAND_PX) continue
    if (pillTop + PILL_H > pane.y + pane.height - 2) continue
    lanes[lane] = px + pillW + PILL_GUTTER

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
    const structures = getStructures()
    // Drawn only when the operator asked for it AND the indices are
    // trustworthy. `structs.length === 0` and `structures === null` both draw
    // nothing, but they are different facts, and the signature below keeps
    // them apart so the disclosure in TradeTab and this layer never disagree.
    const structs = smc && structures ? structures : []
    const dBars = data.bars
    const dTimes = data.times
    const dNarrs = data.narrs
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
      `|${zones.length},${z0?.i0}:${z0?.i1}:${z0?.cls},${zN?.i0}:${zN?.i1}:${zN?.cls}` +
      // Structures: the toggle, the availability (null vs an empty list — two
      // different facts), the count, and the first/last `born`. A new
      // structure moves the count; the newest one moves the last born. An
      // already-born structure never changes, because structure.py defines
      // every field of one as a function of bars[0..born] only — so there is
      // nothing else here that can move, and nothing per-frame that would
      // collapse paint back to the ~3fps this guard exists to prevent.
      `|${smc ? 1 : 0}${structures ? '' : 'x'},${structs.length},` +
      `${structs[0]?.born},${structs[structs.length - 1]?.born}`
    if (sig === lastSig) return
    lastSig = sig

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    // Zone bands FIRST — the market-condition wash is the backdrop everything
    // else reads against, so it must sit under the σ ribbons, not over them.
    if (lastIdx >= 0 && zones.length) {
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
        if (!ok) continue
        lastLabelY = y
        const w = ctx.measureText(`${lvl.label} ${lvl.value.toFixed(1)}`).width
        // Baseline 'bottom' at y-2 for a 10px font, padded by 1px each way.
        takenLabels.push({ x0: pane.x + 6, y0: y - 13, x1: pane.x + 6 + w, y1: y - 1 })
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

    // σ ribbons: filled zones between the deviations, drawn UNDER the level
    // lines/chips below but over the chart canvas underneath this one. Widest
    // (±3σ) first so the narrower, slightly stronger ±1σ layers on top.
    if (lastIdx >= 0) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      const brass = pal.accent
      drawRibbon(ctx, conv, dBars, dTimes, lastIdx, 'u3', 'd3', withAlpha(brass, RIBBON_ALPHA.u3d3))
      drawRibbon(ctx, conv, dBars, dTimes, lastIdx, 'u2', 'd2', withAlpha(brass, RIBBON_ALPHA.u2d2))
      drawRibbon(ctx, conv, dBars, dTimes, lastIdx, 'u1', 'd1', withAlpha(brass, RIBBON_ALPHA.u1d1))
      ctx.restore()
    }

    ctx.font = '10px ui-monospace, SFMono-Regular, Menlo, monospace'
    ctx.textBaseline = 'bottom'

    const structColor = withAlpha(pal.accent, 0.85)
    const trapColor = withAlpha(pal.bear, 0.85)

    visible.forEach(({ lvl, y }, li) => {
      const color = lvl.kind === 'trap' ? trapColor : structColor
      ctx.strokeStyle = color
      ctx.fillStyle = color

      // Always draw the line — suppressing it would hide a real price level.
      ctx.setLineDash(lvl.kind === 'band' ? [2, 4] : [6, 4])
      ctx.beginPath()
      ctx.moveTo(pane.x, y)
      ctx.lineTo(pane.x + pane.width, y)
      ctx.stroke()
      ctx.setLineDash([]) // reset so dash state never leaks into the next stroke/fill

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

    // Story balloons LAST — the persistent event markers sit above the bands,
    // the ribbons and the level lines, since they are the thing being read.
    if (lastIdx >= 0 && dNarrs.length) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      drawBalloons(ctx, conv, pane, pal, dBars, dTimes, dNarrs, lastIdx)
      ctx.restore()
    }
  }

  raf = requestAnimationFrame(draw)
  return () => cancelAnimationFrame(raf)
}
