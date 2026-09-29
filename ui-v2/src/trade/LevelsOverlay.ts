// Everything drawn over the Trade tab's futures chart. The ONLY file that touches CandL's coordinate system:
// converters are live objects and are re-queried every frame (zoom/pan invalidates them).
//
// What is drawn, and nothing else (docs/trade-tab/1-inventory-and-plan.md §C):
//   her zone      the d2→d3 and u2→u3 pockets of the 3-minute machine, with a thin d2 / u2 edge
//   zone entries  the machine's own entries, a triangle on the band and a square pill
//   her marks     P / A / E / C, the extension's own glyphs
// Every item is placed by its own clock and price. The replay cursor cuts every layer at the cursor bar's end.
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { Converters } from '../vendor/candl/drawings/types'
import type { RotationSignal, TapeBar } from '../data'
import { palette } from '../theme'
import type { Mode } from '../theme'
import type { FootEvent } from './footprint'
import type { EngMark } from './engine'
import { BUY_C, SELL_C, engChip, footChip, paintSide, sideColor } from './chips'

/** One bar of her zone's bands (the 3-minute machine's own bars, whatever the chart interval). `t` = epoch ms. */
export interface PocketBar { t: number; d2: number; d3: number; u2: number; u3: number }

/** One entry of her zone machine, placed on the chart bar `i` that contains its own time. `known` (chart ms) is when
 *  the machine could know it: the end of its 3-minute bar. The replay cut reads this, never the chart bar's start. */
export interface ZoneEntry { i: number; sig: RotationSignal; label: string; known: number }

/** The engine's layers, already placed on the chart's own clock (`t` = chart ms). `flat` is null when the flat
 *  levels are not shown: in a trade, while replaying, or with no live read. */
export interface EngineLayer {
  marks: EngMark[]
  flat: { above: number | null; below: number | null; at: number | null
          gaveUp: { t: number; px: number; text: string } | null } | null
  /** The current named walls are hidden while a trade is open (W and A replace them). */
  walls: boolean
}

export interface OverlayData {
  bars: TapeBar[]
  /** The chart's candle times (epoch ms), 1:1 with `bars`. */
  times: number[]
  cursor: number | null
  /** The interval the chart's bars ARE, in minutes; null = unknown (then no cut past the cursor bar's start). */
  interval: number | null
  pockets: PocketBar[] | null
  entries: ZoneEntry[]
  marks: FootEvent[] | null
  engine: EngineLayer | null
  trade: TradeLayer | null
  /** Floor pivots (the Pivots toggle), or null when off. */
  pivots: { label: string; value: number }[] | null
  /** The Value layer, or null when off. */
  value: ValueLayer | null
  /** The CHIPS toggle: Hinglish chips on the lines and the point marks (off: plain numbers on the lines). */
  chipsOn: boolean
  /** The hovered bar (the chart's index), whose point marks show their chips. */
  hover: number | null
  /** Bumped by ContractChart whenever any input changes: the frame-skip signature reads this, not the data. */
  rev: number
}

type PaneRect = { x: number; y: number; width: number; height: number }
type Palette = ReturnType<typeof palette>

// Kite's azure (her own VWAP-band study's ±3σ hue), the only band colour left on this chart
const ZONE_RGB = '0,132,184'
const ZONE_FILL = 0.08
const ZONE_EDGE = 0.55

const LEGEND_BAND_PX = 26          // the engine's OHLC legend owns the pane's top strip
const PILL_H = 14
const PILL_PAD_X = 5
const PILL_LANES = 3
const PILL_LANE_STEP = PILL_H + 2
const PILL_GUTTER = 2
const ROT_TRI_PX = 5
const ROT_STEM = 4
const ROT_SUSPECT_ALPHA = 0.55
const ROT_UNKNOWN_ALPHA = 0.75
const ROT_DASH: [number, number] = [3, 2]
const MONO_STACK = 'ui-monospace, SFMono-Regular, Menlo, monospace'

/** 09:25, `band_rotation.ANCHOR_MINUTE`. */
const ROT_ANCHOR_MINUTE = 9 * 60 + 25
function rotMinute(t: string | null | undefined): number | null {
  const m = /^(\d{1,2}):(\d{2})/.exec(t ?? '')
  return m ? Number(m[1]) * 60 + Number(m[2]) : null
}

/** Checks what the zone machine sent rather than filtering it: anything that is not BUY d2/d3 or SELL u2/u3 at or
 *  after 09:25 cannot come out of `band_rotation.run_states`, so it is withheld and COUNTED (a backend disagreement,
 *  expected 0 forever), never drawn and never silently dropped. */
export function entryPlan(entries: ZoneEntry[]): { ok: ZoneEntry[]; unexpected: number; why: string } {
  const ok: ZoneEntry[] = []
  const odd: string[] = []
  for (const e of entries) {
    const s = e.sig, band = String(s.band)       // the wire carries u2 too; data.ts's RotationBand predates the zone
    const legal = (s.side === 'BUY' && (band === 'd2' || band === 'd3'))
      || (s.side === 'SELL' && (band === 'u2' || band === 'u3'))
    const min = rotMinute(s.t)
    if (!legal || min == null || min < ROT_ANCHOR_MINUTE) { odd.push(`${s.t ?? '?'} ${s.side} ${s.band}`); continue }
    ok.push(e)
  }
  return { ok, unexpected: odd.length, why: odd.slice(0, 3).join(', ') + (odd.length > 3 ? `, +${odd.length - 3} more` : '') }
}

function withAlpha(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`
}

/** A rounded rect path, hand-rolled (`ctx.roundRect` is newer than this project's browser floor). */
function roundedRectPath(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

/** Half the on-screen distance between two adjacent candles, off the live axis; 0 when degenerate. */
function halfBarPx(conv: Converters, times: number[]): number {
  if (times.length < 2) return 0
  const step = conv.timeToX(times[1]) - conv.timeToX(times[0])
  return Number.isFinite(step) && step > 0 ? step / 2 : 0
}

/** The end of the cursor bar in epoch ms: every layer is cut here while replaying. Infinity live. */
function cutMs(d: OverlayData): number {
  if (d.cursor == null || !d.times.length) return Infinity
  const i = Math.max(0, Math.min(d.cursor, d.times.length - 1))
  return d.times[i] + (d.interval ?? 0) * 60_000
}

/** Her zone: the two pockets as one band each, walked per contiguous run of finite values (a hole stays a hole), and
 *  the arming edge (d2 / u2) stroked thin. Pocket bars are the 3-minute machine's; a bar is shown once it has closed
 *  inside the visible chart (t + 3 min ≤ cut). */
function drawZone(ctx: CanvasRenderingContext2D, conv: Converters, pk: PocketBar[], cut: number) {
  const vis = pk.filter((b) => b.t + 3 * 60_000 <= cut)
  for (const [edge, far] of [['d2', 'd3'], ['u2', 'u3']] as const) {
    let i = 0
    while (i < vis.length) {
      const ok = (k: number) => Number.isFinite(vis[k][edge]) && Number.isFinite(vis[k][far])
      if (!ok(i)) { i++; continue }
      let j = i
      while (j + 1 < vis.length && ok(j + 1)) j++
      if (j > i) {
        ctx.beginPath()
        for (let k = i; k <= j; k++) ctx.lineTo(conv.timeToX(vis[k].t), conv.priceToY(vis[k][edge]))
        for (let k = j; k >= i; k--) ctx.lineTo(conv.timeToX(vis[k].t), conv.priceToY(vis[k][far]))
        ctx.closePath()
        ctx.fillStyle = `rgba(${ZONE_RGB},${ZONE_FILL})`
        ctx.fill()
        ctx.beginPath()
        for (let k = i; k <= j; k++) ctx.lineTo(conv.timeToX(vis[k].t), conv.priceToY(vis[k][edge]))
        ctx.strokeStyle = `rgba(${ZONE_RGB},${ZONE_EDGE})`
        ctx.lineWidth = 1
        ctx.setLineDash([])
        ctx.stroke()
      }
      i = j + 1
    }
  }
}

type LaneRight = [number[], number[]]
const newLanes = (): LaneRight => [Array(PILL_LANES).fill(-Infinity), Array(PILL_LANES).fill(-Infinity)]
function pickLane(lanes: LaneRight, side: 0 | 1, px: number): number {
  const row = lanes[side]
  for (let l = 0; l < PILL_LANES; l++) if (px >= row[l]) return l
  let best = 0
  for (let l = 1; l < PILL_LANES; l++) if (row[l] < row[best]) best = l
  return best
}

/** Her zone machine's entries: a filled triangle ON the band it armed on (the one mark drawn at a σ level), a stem,
 *  and a square pill under a BUY's low / over a SELL's high. The compression read rides as opacity and a dashed
 *  border, never as suppression. Never de-cluttered away; clamped into the pane rather than dropped. */
function drawEntries(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, d: OverlayData, cut: number, taken: { x0: number; y0: number; x1: number; y1: number }[]) {
  const { ok } = entryPlan(d.entries)
  const lanes = newLanes()
  ctx.font = `bold 10px ${MONO_STACK}`
  ctx.textBaseline = 'middle'
  for (const e of ok) {
    const bar = d.bars[e.i], t = d.times[e.i]
    if (!bar || t == null || e.known > cut) continue
    const sig = e.sig, buy = sig.side === 'BUY'
    const tone = buy ? BUY_C : SELL_C
    const alpha = sig.trap === 'CLEAR' ? 1 : sig.trap === 'UNKNOWN' ? ROT_UNKNOWN_ALPHA : ROT_SUSPECT_ALPHA
    const stroke = withAlpha(tone, alpha)
    const x = conv.timeToX(t)
    if (!Number.isFinite(x) || x < pane.x - 2 || x > pane.x + pane.width + 2) continue
    const level = sig.level ?? (bar as unknown as Record<string, number>)[sig.band]
    const bandY = conv.priceToY(level)
    const extremeY = conv.priceToY(buy ? bar.l : bar.h)
    if (!Number.isFinite(bandY) || !Number.isFinite(extremeY)) continue
    const anchorY = buy ? Math.max(bandY, extremeY) : Math.min(bandY, extremeY)
    const text = `${buy ? '▲' : '▼'} ${e.label}`
    const pillW = ctx.measureText(text).width + PILL_PAD_X * 2
    if (pillW + 4 > pane.width) continue
    const px = Math.max(pane.x + 2, Math.min(x - pillW / 2, pane.x + pane.width - 2 - pillW))
    const side: 0 | 1 = buy ? 1 : 0
    const lane = pickLane(lanes, side, px)
    const off = ROT_STEM + lane * PILL_LANE_STEP
    const topLimit = pane.y + LEGEND_BAND_PX
    const botLimit = pane.y + pane.height - 2 - PILL_H
    if (botLimit < topLimit) continue
    const pillTop = Math.max(topLimit, Math.min(buy ? anchorY + off : anchorY - off - PILL_H, botLimit))
    lanes[side][lane] = px + pillW + PILL_GUTTER
    taken.push({ x0: px, y0: pillTop, x1: px + pillW, y1: pillTop + PILL_H })
    ctx.fillStyle = stroke
    ctx.beginPath()
    if (buy) { ctx.moveTo(x, bandY - ROT_TRI_PX); ctx.lineTo(x - ROT_TRI_PX, bandY + ROT_TRI_PX); ctx.lineTo(x + ROT_TRI_PX, bandY + ROT_TRI_PX) }
    else { ctx.moveTo(x, bandY + ROT_TRI_PX); ctx.lineTo(x - ROT_TRI_PX, bandY - ROT_TRI_PX); ctx.lineTo(x + ROT_TRI_PX, bandY - ROT_TRI_PX) }
    ctx.closePath()
    ctx.fill()
    ctx.strokeStyle = withAlpha(tone, alpha * 0.5)
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(x, bandY)
    ctx.lineTo(x, buy ? pillTop : pillTop + PILL_H)
    ctx.stroke()
    roundedRectPath(ctx, px, pillTop, pillW, PILL_H, 2)
    ctx.fillStyle = 'rgba(255,255,255,0.92)'
    ctx.fill()
    ctx.lineWidth = 1.5
    ctx.strokeStyle = stroke
    if (sig.trap === 'UNKNOWN') ctx.setLineDash(ROT_DASH)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.lineWidth = 1
    ctx.fillStyle = stroke
    ctx.fillText(text, px + PILL_PAD_X, pillTop + PILL_H / 2)
  }
}

/* ── Her footprint marks: the extension's own glyph family, painted as GoCharting paints them ─────────────────
   trap a FILLED DISC carrying P · climax a DIAMOND carrying C · absorption a SHELF · exhaustion a CHEVRON.
   Placed by its own clock and its own price, never snapped to a candle (the record is 5-minute).
   The extension's two rules (orderflow-desk overlay.js): a mark wears its SIDE's colour (`sideC`), and an absorption
   or an exhaustion that is NOT at a named level is not drawn at all (`if (!m.at && …) continue`). Heavy = at a level. */
const MARK_PRIO: Record<string, number> = { trap: 0, absorption: 1, exhaustion: 2, climax: 3 }
const MARK_LETTER: Record<string, string> = { trap: 'P', climax: 'C', absorption: 'A', exhaustion: 'E' }
const MARK_FONT = 'ui-sans-serif, system-ui, sans-serif'
const MARK_U_MIN = 4
const MARK_U_MAX = 14
const MARK_U_OF_PITCH = 0.75
const MARK_LETTERS_AT = 5.2

function hhmmMins(t: string): number {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(t))
  return m ? +m[1] * 60 + +m[2] : NaN
}

function barContaining(times: number[], t: number, hi: number): number {
  if (hi < 0 || t < times[0]) return -1
  let lo = 0
  let h = hi
  while (h - lo > 1) {
    const mid = (lo + h) >> 1
    if (times[mid] <= t) lo = mid
    else h = mid
  }
  return times[h] <= t ? h : lo
}

/** The marks this layer draws, and how many are heavy / have no glyph: counted by the draw's own rule. */
export function markCounts(marks: FootEvent[] | null): { drawn: number; heavy: number; skipped: number; offLevel: number } {
  let drawn = 0, heavy = 0, skipped = 0, offLevel = 0
  for (const e of marks || []) {
    if (MARK_PRIO[e.kind] === undefined) { skipped++; continue }
    if (e.p == null || !Number.isFinite(e.p) || !Number.isFinite(hhmmMins(e.t))) continue
    if (offLevelAE(e)) { offLevel++; continue }
    drawn++
    if (e.at) heavy++
  }
  return { drawn, heavy, skipped, offLevel }
}

/** The extension's rule: an absorption or an exhaustion away from a named level is not one of her marks. */
const offLevelAE = (e: FootEvent) => !e.at && (e.kind === 'absorption' || e.kind === 'exhaustion')

function drawMarks(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, pal: Palette,
                   d: OverlayData, marks: FootEvent[], cut: number, now: number, pts: Point[]) {
  const { bars, times } = d
  if (!times.length || !bars.length) return
  const firstMins = hhmmMins(bars[0].t)
  if (!Number.isFinite(firstMins)) return
  const base = times[0] - firstMins * 60_000
  const lastIdx = times.length - 1
  const pitch = halfBarPx(conv, times) * 2
  const u = Math.max(MARK_U_MIN, Math.min(MARK_U_MAX, MARK_U_OF_PITCH * pitch))
  const letters = u >= MARK_LETTERS_AT
  const LS = Math.max(8, Math.min(13, 1.4 * u))
  const groups = new Map<string, FootEvent[]>()
  for (const e of marks) {
    if (MARK_PRIO[e.kind] === undefined || offLevelAE(e)) continue
    if (e.p == null || !Number.isFinite(e.p)) continue
    const mins = hhmmMins(e.t)
    if (!Number.isFinite(mins) || base + mins * 60_000 >= cut) continue
    const g = groups.get(e.t)
    if (g) g.push(e)
    else groups.set(e.t, [e])
  }
  type Draw = { e: FootEvent; x: number; y: number; away: number; t: number }
  const draws: Draw[] = []
  for (const [t, g] of groups) {
    g.sort((a, b) => ((b.at ? 1 : 0) - (a.at ? 1 : 0)) || (MARK_PRIO[a.kind] - MARK_PRIO[b.kind]))
    const tms = base + hhmmMins(t) * 60_000
    const x = conv.timeToX(tms)
    if (!Number.isFinite(x)) continue
    const bi = barContaining(times, tms, lastIdx)
    const b = bi >= 0 ? bars[bi] : null
    const mid = b ? (Number(b.h) + Number(b.l)) / 2 : (g[0].p as number)
    const away = (g[0].p as number) <= mid ? 1 : -1
    let prevY: number | null = null
    let prevExt = 0
    for (const e of g) {
      const ext = e.kind === 'absorption' ? Math.max(2, 0.35 * u) / 2 + 1 : e.kind === 'exhaustion' ? u * 0.7 : u
      const y0 = conv.priceToY(e.p as number)
      if (!Number.isFinite(y0)) continue
      const y: number = prevY != null && Math.abs(y0 - prevY) < 2 * u ? prevY + away * (prevExt + ext + 1) : y0
      prevY = y
      prevExt = ext
      draws.push({ e, x, y, away, t: tms })
    }
  }
  ctx.save()
  ctx.setLineDash([])
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'
  const glow = withAlpha(pal.card, 0.9)
  const halo = (trace: () => void, color: string, lw: number) => {
    ctx.strokeStyle = glow; ctx.lineWidth = lw + 2.5; trace(); ctx.stroke()
    ctx.strokeStyle = color; ctx.lineWidth = lw; trace(); ctx.stroke()
  }
  const letter = (s: string, x: number, y: number, color: string, ring: string, align: CanvasTextAlign) => {
    ctx.font = `800 ${LS}px ${MARK_FONT}`
    ctx.textAlign = align
    ctx.textBaseline = 'middle'
    ctx.lineWidth = 3
    ctx.strokeStyle = ring
    ctx.strokeText(s, x, y)
    ctx.fillStyle = color
    ctx.fillText(s, x, y)
  }
  for (const dr of draws.sort((a, b) => (a.e.at ? 1 : 0) - (b.e.at ? 1 : 0))) {
    const { e, x, y, away } = dr
    if (y < pane.y + 2 || y > pane.y + pane.height - 2) continue
    if (x < pane.x - 20 || x > pane.x + pane.width + 20) continue
    const a = fade(dr.t, now)
    ctx.globalAlpha = a
    const chip = footChip(e)
    if (chip) pts.push({ t: dr.t, x, y, text: chip.text, color: chip.color, alpha: a, at: !!e.at })
    const heavy = !!e.at
    const lw = heavy ? 2.5 : 1.5
    const cc = withAlpha(sideColor(paintSide(e)), heavy ? 1 : 0.8)   // P flipped as GoCharting paints it (main.js:169)
    const R = u
    if (e.kind === 'trap') {
      halo(() => { ctx.beginPath(); ctx.arc(x, y, R, 0, Math.PI * 2) }, cc, lw)
      ctx.fillStyle = cc
      ctx.fill()
      if (letters) letter(MARK_LETTER.trap, x, y + 0.5, pal.card, cc, 'center')
    } else if (e.kind === 'climax') {
      halo(() => { ctx.beginPath(); ctx.moveTo(x, y - R); ctx.lineTo(x + R, y); ctx.lineTo(x, y + R); ctx.lineTo(x - R, y); ctx.closePath() }, cc, lw)
      if (letters) letter(MARK_LETTER.climax, x, y + 0.5, cc, glow, 'center')
    } else if (e.kind === 'absorption') {
      const w = Math.max(10, 1.8 * pitch) / 2
      const h = Math.max(2, 0.35 * u)
      halo(() => roundedRectPath(ctx, x - w, y - h / 2, 2 * w, h, h / 2), cc, lw)
      ctx.fillStyle = cc
      ctx.fill()
      if (letters) letter(MARK_LETTER.absorption, x - w - 3, y + 0.5, cc, glow, 'right')
    } else if (e.kind === 'exhaustion') {
      const w = R
      const h = u * 0.5 * away
      halo(() => { ctx.beginPath(); ctx.moveTo(x - w, y - h); ctx.lineTo(x, y + h * 0.4); ctx.lineTo(x + w, y - h) }, cc, lw)
      if (letters) letter(MARK_LETTER.exhaustion, x, y + h * 0.4 + away * u * 0.8, cc, glow, 'center')
    }
    ctx.globalAlpha = 1
  }
  ctx.restore()
}

/* ── The engine's layers, her trade, the reference lines, and the CHIPS ─────────────────────────────────────────────
   Her ask (docs/trade-tab/2-hinglish-chips.md): every symbol readable without the key. A LINE carries a chip at the
   right edge, never a label mid-chart. A POINT mark (▲▼ ▬ P A E C) carries a chip beside its glyph when it is among
   the newest 6, sits at a named level, or is under the mouse. Chips stack; one that still collides is dropped and its
   glyph stays. Point glyphs and their chips fade with age. CHIPS off: the lines carry plain numbers, no point chips.
   Every mark is fold.py's or the extension's, frozen at birth, at its own (t, px); this only positions it. */
const INK = '#141A22'
const MUTED = '#5C6675'
const CHIP_FONT = '600 10px ui-sans-serif, system-ui, "Segoe UI", sans-serif'
const CHIP_H = 14
const NEWEST_N = 6

type Box = { x0: number; y0: number; x1: number; y1: number }
const hits = (a: Box, taken: Box[]) => taken.some((b) => a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0)

/** A line's chip at the right edge. `num` is the CHIPS-off text. Rank: hers and the engine's levels first, then the
 *  walls and shelves, then the quiet reference chips. */
type Chip = { y: number; text: string; num?: string; color: string; filled: boolean; small?: boolean }

function chipBox(ctx: CanvasRenderingContext2D, x: number, y: number, text: string, color: string, filled: boolean,
                 alpha = 1, small = false) {
  ctx.save()
  ctx.globalAlpha = alpha
  ctx.font = small ? `9px ${MONO_STACK}` : CHIP_FONT
  ctx.textBaseline = 'middle'
  const w = ctx.measureText(text).width + 8
  roundedRectPath(ctx, x, y, w, CHIP_H, 3)
  ctx.fillStyle = filled ? color : 'rgba(255,255,255,0.94)'
  ctx.fill()
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.setLineDash([])
  ctx.stroke()
  ctx.fillStyle = filled ? '#FFFFFF' : color
  ctx.fillText(text, x + 4, y + CHIP_H / 2 + 0.5)
  ctx.restore()
}

function chipWidth(ctx: CanvasRenderingContext2D, text: string, small = false) {
  ctx.font = small ? `9px ${MONO_STACK}` : CHIP_FONT
  return ctx.measureText(text).width + 8
}

function drawChips(ctx: CanvasRenderingContext2D, pane: PaneRect, chips: Chip[], on: boolean, taken: Box[]): number {
  let n = 0
  const rank = (c: Chip) => (c.filled ? 0 : c.small ? 2 : 1)
  for (const c of chips.sort((a, b) => rank(a) - rank(b))) {
    if (!Number.isFinite(c.y)) continue
    const text = on || c.num == null ? c.text : c.num
    const w = chipWidth(ctx, text, c.small)
    const x = pane.x + pane.width - w - 2
    // stack: on its own line first, then one chip-height above or below with a short leader; else drop the chip
    for (const dy of [0, -(CHIP_H + 1), CHIP_H + 1]) {
      const y = c.y - CHIP_H / 2 + dy
      const box = { x0: x, y0: y, x1: x + w, y1: y + CHIP_H }
      if (y < pane.y + LEGEND_BAND_PX || y + CHIP_H > pane.y + pane.height - 2 || hits(box, taken)) continue
      taken.push(box)
      if (dy) {
        ctx.strokeStyle = withAlpha(c.color, 0.6)
        ctx.lineWidth = 1
        ctx.beginPath(); ctx.moveTo(x - 4, c.y); ctx.lineTo(x, y + CHIP_H / 2); ctx.stroke()
      }
      chipBox(ctx, x, y, text, c.color, c.filled, 1, c.small)
      n++
      break
    }
  }
  return n
}

/** A point mark that may carry a chip: where its glyph sits, what its chip says, and why it would show. */
type Point = { t: number; x: number; y: number; text: string; color: string; alpha: number; at: boolean; always?: boolean }

/** Beside the glyph: right, above-right, below-right, then left; the first place that clears everything else. */
function drawPointChips(ctx: CanvasRenderingContext2D, pane: PaneRect, pts: Point[], hoverSpan: [number, number] | null, taken: Box[]): number {
  let n = 0
  const marks = pts.filter((p) => !p.always)
  const newest = new Set([...marks].sort((a, b) => b.t - a.t).slice(0, NEWEST_N))
  const hovered = (p: Point) => !!hoverSpan && p.t >= hoverSpan[0] && p.t < hoverSpan[1]
  const shown = pts.filter((p) => p.always || hovered(p) || newest.has(p) || p.at)
  const prio = (p: Point) => (p.always ? 0 : hovered(p) ? 1 : newest.has(p) ? 2 : 3)
  for (const p of shown.sort((a, b) => prio(a) - prio(b) || b.t - a.t)) {
    const w = chipWidth(ctx, p.text)
    const tries = [[p.x + 9, p.y - CHIP_H / 2], [p.x + 9, p.y - CHIP_H - 8], [p.x + 9, p.y + 8], [p.x - 9 - w, p.y - CHIP_H / 2]]
    for (const [x, y] of tries) {
      const box = { x0: x, y0: y, x1: x + w, y1: y + CHIP_H }
      if (x < pane.x + 2 || x + w > pane.x + pane.width - 2) continue
      if (y < pane.y + LEGEND_BAND_PX || y + CHIP_H > pane.y + pane.height - 2 || hits(box, taken)) continue
      taken.push(box)
      chipBox(ctx, x, y, p.text, p.color, false, hovered(p) || p.always ? 1 : p.alpha)
      n++
      break
    }
  }
  return n
}

/** Age fade, the same for a glyph and its chip: full when new, down to 0.4 after four hours. */
function fade(t: number, now: number) {
  return Math.max(0.4, 1 - 0.6 * Math.max(0, now - t) / (240 * 60_000))
}

function hline(ctx: CanvasRenderingContext2D, pane: PaneRect, y: number, color: string, width: number, dash: number[], x0 = pane.x) {
  if (!Number.isFinite(y) || y < pane.y + 2 || y > pane.y + pane.height - 2) return false
  ctx.strokeStyle = color
  ctx.lineWidth = width
  ctx.setLineDash(dash)
  ctx.beginPath()
  ctx.moveTo(Math.max(pane.x, x0), y)
  ctx.lineTo(pane.x + pane.width, y)
  ctx.stroke()
  ctx.setLineDash([])
  return true
}

/** Fights won (▲ buyers / ▼ sellers; a white dot = won by price [I]; hollow = disputed) and held (a short square
 *  bar, no letter: the engine's book detector, never to be read as her footprint A). Held is coloured by the HOLDER,
 *  so the glyph, its chip ("Buyers ne roka") and the engine's own "N lots of buyers held" agree. */
function drawFights(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, marks: EngMark[], cut: number,
                    now: number, pts: Point[]) {
  ctx.save()
  ctx.lineJoin = 'round'
  for (const m of marks) {
    if (m.t >= cut || (m.kind !== 'won' && m.kind !== 'absorbed')) continue
    const x = conv.timeToX(m.t), y = conv.priceToY(m.px)
    if (!Number.isFinite(x) || !Number.isFinite(y) || y < pane.y + 2 || y > pane.y + pane.height - 2) continue
    if (x < pane.x - 6 || x > pane.x + pane.width + 6) continue
    const chip = engChip(m)
    const c = chip?.color ?? sideColor(m.side)
    const a = fade(m.t, now)
    ctx.globalAlpha = a
    ctx.beginPath()
    if (m.kind === 'won') {
      const s = 5
      if (m.side > 0) { ctx.moveTo(x, y - s); ctx.lineTo(x - s * 0.9, y + s * 0.6); ctx.lineTo(x + s * 0.9, y + s * 0.6) }
      else { ctx.moveTo(x, y + s); ctx.lineTo(x - s * 0.9, y - s * 0.6); ctx.lineTo(x + s * 0.9, y - s * 0.6) }
      ctx.closePath()
    } else {
      ctx.rect(x - 5, y - 2.5, 10, 5)
    }
    ctx.lineWidth = 3
    ctx.strokeStyle = 'rgba(255,255,255,0.95)'
    ctx.stroke()
    if (m.disputed) { ctx.lineWidth = 1.5; ctx.strokeStyle = c; ctx.stroke() }
    else { ctx.fillStyle = c; ctx.fill() }
    if (m.kind === 'won' && m.by === 'price') {
      ctx.beginPath()
      ctx.arc(x, y + (m.side > 0 ? 1 : -1), 1.3, 0, Math.PI * 2)
      ctx.fillStyle = '#FFFFFF'
      ctx.fill()
    }
    ctx.globalAlpha = 1
    if (chip) pts.push({ t: m.t, x, y, text: chip.text, color: c, alpha: a, at: false })
  }
  ctx.restore()
}

/** Trapped inventory not released by the cut: a thick translucent line from the trap to the right edge, its chip
 *  there ("Buyers phase · 429 lots"). A release is the engine's `released` mark on the same run (price and side). */
function drawShelves(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, marks: EngMark[], cut: number, chips: Chip[]) {
  const released = new Set<string>()
  for (const m of marks) if (m.kind === 'released' && m.t < cut) released.add(`${m.px}|${m.side}`)
  for (const m of marks) {
    if (m.kind !== 'trapped' || m.t >= cut || released.has(`${m.px}|${m.side}`)) continue
    const y = conv.priceToY(m.px), x0 = conv.timeToX(m.t)
    const chip = engChip(m)
    const c = chip?.color ?? sideColor(m.side)
    if (!hline(ctx, pane, y, withAlpha(c, 0.45), 3, [], x0)) continue
    chips.push({ y, text: chip?.text ?? m.text, num: `phase ${m.lots ?? ''}`.trim(), color: c, filled: false })
  }
}

/** The newest wall each side at the cut, at K + basis (the engine placed it), dotted, chipped at the right edge. */
function wallChips(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, marks: EngMark[], cut: number, chips: Chip[]) {
  const last = new Map<string, EngMark>()
  for (const m of marks) if (m.kind === 'wall' && m.t < cut && m.ty) last.set(m.ty, m)
  for (const m of last.values()) {
    const y = conv.priceToY(m.px)
    if (hline(ctx, pane, y, withAlpha(MUTED, 0.85), 1.2, [1.5, 3])) {
      chips.push({ y, text: engChip(m)?.text ?? `${m.k} ${m.ty}`, num: `${m.k} ${m.ty}`, color: MUTED, filled: false })
    }
  }
}

/** NEXT FIGHT above and below (or AT one level): solid ink, chipped at the right edge. Live only. */
function drawNextFight(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, f: NonNullable<EngineLayer['flat']>,
                       chips: Chip[], pts: Point[]) {
  const one = (px: number | null, name: string) => {
    if (px == null) return
    const y = conv.priceToY(px)
    if (hline(ctx, pane, y, INK, 1.3, [])) chips.push({ y, text: `${name} · ${px}`, num: String(px), color: INK, filled: true })
  }
  if (f.at != null) one(f.at, 'Ladai yahin')
  one(f.above, 'Agli ladai upar')
  one(f.below, 'Agli ladai neeche')
  if (f.gaveUp) {
    const x = conv.timeToX(f.gaveUp.t), y = conv.priceToY(f.gaveUp.px)
    if (Number.isFinite(x) && Number.isFinite(y)) {
      ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2)
      ctx.fillStyle = INK; ctx.fill()
      pts.push({ t: f.gaveUp.t, x, y, text: f.gaveUp.text, color: INK, alpha: 1, at: false, always: true })
    }
  }
}

/* ── Her trade ─────────────────────────────────────────────────────────────────────────────────────────────────────
   Entry ▸ at the future's price when she marked, with a faint line to the right edge for its chip; G, her give-up,
   dashed from the minute it was set, its colour the engine's word and nothing else (ink HOLD · amber PAST GIVE-UP ·
   red FOLD · grey CAN'T CHECK); older G steps at 55%; W behind her and A ahead, dotted at K + basis; the OI event on
   W; FOLD ■. `chip` is the Hinglish chip, `num` the CHIPS-off text. */
export interface TradeLayer {
  entry: { t: number; px: number; chip: string; num: string } | null
  G: { px: number; from: number; color: string; chip: string; num: string } | null
  steps: { px: number; from: number; to: number }[]
  W: { px: number; chip: string; num: string } | null
  A: { px: number; chip: string; num: string } | null
  oiEvent: { t: number; px: number; chip: string } | null
  fold: { t: number; px: number; chip: string } | null
  /** Today's other marked trades on this index: entry / exit hairlines only. */
  ticks: { t: number; text: string }[]
}

function drawTrade(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, tr: TradeLayer, cut: number, live: boolean,
                   chips: Chip[], pts: Point[], taken: Box[]) {
  ctx.save()
  for (const k of tr.ticks) {
    if (k.t >= cut) continue
    const x = conv.timeToX(k.t)
    if (!Number.isFinite(x) || x < pane.x || x > pane.x + pane.width) continue
    ctx.strokeStyle = withAlpha(MUTED, 0.35)
    ctx.lineWidth = 1
    ctx.setLineDash([])
    ctx.beginPath(); ctx.moveTo(x, pane.y + LEGEND_BAND_PX); ctx.lineTo(x, pane.y + pane.height); ctx.stroke()
    const w = chipWidth(ctx, k.text)
    const box = { x0: x + 3, y0: pane.y + LEGEND_BAND_PX + 2, x1: x + 3 + w, y1: pane.y + LEGEND_BAND_PX + 2 + CHIP_H }
    if (box.x1 < pane.x + pane.width && !hits(box, taken)) { taken.push(box); chipBox(ctx, box.x0, box.y0, k.text, MUTED, false, 0.9) }
  }
  if (live) {
    for (const s of tr.steps) {
      if (!tr.G) break
      const y = conv.priceToY(s.px), x0 = conv.timeToX(s.from), x1 = conv.timeToX(s.to)
      if (!Number.isFinite(y) || !Number.isFinite(x0) || !Number.isFinite(x1)) continue
      ctx.strokeStyle = withAlpha(tr.G.color, 0.55)
      ctx.lineWidth = 1.4
      ctx.setLineDash([6, 4])
      ctx.beginPath(); ctx.moveTo(Math.max(pane.x, x0), y); ctx.lineTo(Math.min(pane.x + pane.width, x1), y); ctx.stroke()
      ctx.setLineDash([])
    }
    if (tr.W) {
      const y = conv.priceToY(tr.W.px)
      if (hline(ctx, pane, y, withAlpha(MUTED, 0.9), 1.5, [1.5, 3])) chips.push({ y, text: tr.W.chip, num: tr.W.num, color: MUTED, filled: false })
    }
    if (tr.A) {
      const y = conv.priceToY(tr.A.px)
      if (hline(ctx, pane, y, withAlpha(INK, 0.8), 1.6, [1.5, 3])) chips.push({ y, text: tr.A.chip, num: tr.A.num, color: INK, filled: false })
    }
    if (tr.oiEvent && tr.oiEvent.t < cut) {
      const x = conv.timeToX(tr.oiEvent.t), y = conv.priceToY(tr.oiEvent.px)
      if (Number.isFinite(x) && Number.isFinite(y)) {
        ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2)
        ctx.fillStyle = '#FFFFFF'; ctx.fill()
        ctx.strokeStyle = INK; ctx.lineWidth = 1.5; ctx.stroke()
        pts.push({ t: tr.oiEvent.t, x, y, text: tr.oiEvent.chip, color: INK, alpha: 1, at: false, always: true })
      }
    }
    if (tr.G) {
      const y = conv.priceToY(tr.G.px)
      if (hline(ctx, pane, y, tr.G.color, 1.8, [6, 4], conv.timeToX(tr.G.from))) {
        chips.push({ y, text: tr.G.chip, num: tr.G.num, color: tr.G.color, filled: true })
      }
    }
    if (tr.fold && tr.fold.t < cut) {
      const x = conv.timeToX(tr.fold.t), y = conv.priceToY(tr.fold.px)
      if (Number.isFinite(x) && Number.isFinite(y)) {
        ctx.fillStyle = '#C42B30'
        ctx.strokeStyle = '#FFFFFF'
        ctx.lineWidth = 2
        ctx.strokeRect(x - 5, y - 5, 10, 10)
        ctx.fillRect(x - 5, y - 5, 10, 10)
        pts.push({ t: tr.fold.t, x, y, text: tr.fold.chip, color: '#C42B30', alpha: 1, at: false, always: true })
      }
    }
  }
  if (tr.entry && tr.entry.t < cut) {
    const x = conv.timeToX(tr.entry.t), y = conv.priceToY(tr.entry.px)
    if (Number.isFinite(x) && Number.isFinite(y)) {
      if (live && hline(ctx, pane, y, withAlpha(INK, 0.35), 1, [2, 3], x)) {
        chips.push({ y, text: tr.entry.chip, num: tr.entry.num, color: INK, filled: false })
      }
      ctx.beginPath()
      ctx.moveTo(x - 7, y - 6); ctx.lineTo(x + 3, y); ctx.lineTo(x - 7, y + 6); ctx.closePath()
      ctx.lineWidth = 3; ctx.strokeStyle = '#FFFFFF'; ctx.stroke()
      ctx.fillStyle = INK; ctx.fill()
    }
  }
  ctx.restore()
}

/* ── Reference layers ──────────────────────────────────────────────────────────────────────────────────────────────
   Pivots: her reference lines, "they work some days they dont", so they never decide anything here: grey hairlines,
   no glow, no colour, a small number chip at the right edge (reference, not a read). On by default.
   Value (off by default): ONE family, the Upstox ux ladder's session value area and high-volume nodes, tagged [I], plus
   the ladder record's prior days and naked POCs when the contract has them. */
export interface ValueLayer {
  poc: number | null; vah: number | null; val: number | null
  hvn: number[]
  prior: { day: string; poc: number }[]
  naked: { day: string; poc: number; to: number | null }[]
}
const REF = '#8A93A1'

function drawPivots(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, pivots: { label: string; value: number }[], chips: Chip[]) {
  for (const p of pivots) {
    const y = conv.priceToY(p.value)
    if (hline(ctx, pane, y, withAlpha(REF, 0.55), 1, [])) chips.push({ y, text: `${p.label} ${p.value.toFixed(1)}`, color: REF, filled: false, small: true })
  }
}

function drawValue(ctx: CanvasRenderingContext2D, conv: Converters, pane: PaneRect, v: ValueLayer, cut: number, chips: Chip[]) {
  for (const p of v.hvn) {
    const yt = conv.priceToY(p + 2.5), yb = conv.priceToY(p - 2.5)
    if (!Number.isFinite(yt) || !Number.isFinite(yb)) continue
    ctx.fillStyle = 'rgba(20,26,34,0.06)'
    ctx.fillRect(pane.x, yt, pane.width, yb - yt)
  }
  if (v.vah != null && v.val != null) {
    const yh = conv.priceToY(v.vah), yl = conv.priceToY(v.val)
    if (Number.isFinite(yh) && Number.isFinite(yl)) {
      ctx.fillStyle = 'rgba(138,147,161,0.07)'
      ctx.fillRect(pane.x, yh, pane.width, yl - yh)
      if (hline(ctx, pane, yh, withAlpha(REF, 0.6), 1, [2, 3])) chips.push({ y: yh, text: `VAH ${v.vah} [I]`, color: REF, filled: false, small: true })
      if (hline(ctx, pane, yl, withAlpha(REF, 0.6), 1, [2, 3])) chips.push({ y: yl, text: `VAL ${v.val} [I]`, color: REF, filled: false, small: true })
    }
  }
  if (v.poc != null) {
    const y = conv.priceToY(v.poc)
    if (hline(ctx, pane, y, withAlpha(MUTED, 0.9), 1.2, [5, 3])) chips.push({ y, text: `POC ${v.poc} [I]`, color: MUTED, filled: false, small: true })
  }
  for (const p of v.prior) {
    const y = conv.priceToY(p.poc)
    if (hline(ctx, pane, y, withAlpha(REF, 0.45), 1, [1, 4])) chips.push({ y, text: `POC ${p.day.slice(5)}`, color: REF, filled: false, small: true })
  }
  for (const n of v.naked) {
    const y = conv.priceToY(n.poc)
    const x1 = n.to != null && n.to < cut ? conv.timeToX(n.to) : pane.x + pane.width
    if (!Number.isFinite(y) || y < pane.y + 2 || y > pane.y + pane.height - 2) continue
    ctx.strokeStyle = withAlpha(MUTED, 0.7)
    ctx.lineWidth = 1
    ctx.setLineDash([])
    ctx.beginPath(); ctx.moveTo(pane.x, y); ctx.lineTo(Math.max(pane.x, x1), y); ctx.stroke()
    chips.push({ y, text: `NPOC ${n.day.slice(5)}`, color: MUTED, filled: false, small: true })
  }
}

export function startLevelsOverlay(
  canvas: HTMLCanvasElement,
  host: HTMLElement,
  engine: IChartEngine,
  getMode: () => Mode,
  getData: () => OverlayData,
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
      // a canvas is a replaced element: its CSS size must be set or it renders dpr× too large
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
    }
    const conv = engine.getMainConverters()
    const pane = engine.getMainPaneRect()
    if (!conv || !pane) return
    const mode = getMode()
    const d = getData()
    // Skip the redraw when nothing moved: the inputs (rev), the size, the pane, and the view transform (two price and
    // two time probes pin it exactly).
    const sig = `${mode}|${bw}x${bh}|${pane.x},${pane.y},${pane.width},${pane.height}`
      + `|${conv.priceToY(0)},${conv.priceToY(1000)}|${conv.timeToX(0)},${conv.timeToX(60000)}|${d.rev}`
      + `|${d.times.length},${d.times[d.times.length - 1]}`
    if (sig === lastSig) return
    lastSig = sig
    const pal = palette(mode)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)
    if (!d.bars.length || !d.times.length) return
    const cut = cutMs(d)
    const lastT = d.times[d.times.length - 1] + (d.interval ?? 0) * 60_000
    const now = Math.min(cut, lastT)
    const hi = d.hover
    const hoverSpan: [number, number] | null = hi != null && d.times[hi] != null
      ? [d.times[hi], d.times[hi + 1] ?? d.times[hi] + (d.interval ?? 5) * 60_000] : null
    ctx.save()
    ctx.beginPath()
    ctx.rect(pane.x, pane.y, pane.width, pane.height)
    ctx.clip()
    const chips: Chip[] = []
    const pts: Point[] = []
    const taken: Box[] = []
    if (d.value) drawValue(ctx, conv, pane, d.value, cut, chips)
    if (d.pivots) drawPivots(ctx, conv, pane, d.pivots, chips)
    if (d.pockets) drawZone(ctx, conv, d.pockets, cut)
    const eng = d.engine
    if (eng) {
      if (eng.walls) wallChips(ctx, conv, pane, eng.marks, cut, chips)
      drawShelves(ctx, conv, pane, eng.marks, cut, chips)
      if (eng.flat) drawNextFight(ctx, conv, pane, eng.flat, chips, pts)
    }
    if (d.trade) drawTrade(ctx, conv, pane, d.trade, cut, d.cursor == null, chips, pts, taken)
    drawEntries(ctx, conv, pane, d, cut, taken)
    if (d.marks && d.marks.length) drawMarks(ctx, conv, pane, pal, d, d.marks, cut, now, pts)
    if (eng) drawFights(ctx, conv, pane, eng.marks, cut, now, pts)
    const nLine = drawChips(ctx, pane, chips, d.chipsOn, taken)
    const nPoint = d.chipsOn ? drawPointChips(ctx, pane, pts, hoverSpan, taken) : 0
    // what was drawn, readable off the element: how the chip rule is checked (docs/trade-tab/2-hinglish-chips.md)
    canvas.dataset.chips = `lines ${nLine} · points ${nPoint} of ${pts.length} · entries ${d.entries.length}`
    ctx.restore()
  }
  raf = requestAnimationFrame(draw)
  return () => cancelAnimationFrame(raf)
}
