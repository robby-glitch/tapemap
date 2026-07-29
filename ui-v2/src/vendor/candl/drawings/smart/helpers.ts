// Shared helpers for the smart (data-aware) drawing tools.
// Canvas-only: no DOM access. All time values are epoch ms; candles ascending.

import type { Candle } from '../../core/types'
import type { Drawing } from '../types'

/** Pixel tolerance for hit-testing strokes/edges. */
export const HIT_TOL = 6

/** Pixel half-extent for handle hit-testing. */
export const HANDLE_TOL = 8

/** Visual side length (px) of square anchor handles. */
export const HANDLE_SIZE = 7

/** Label typography for smart-tool chips. */
export const FONT_CHIP = '500 11px -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

/** Chip metrics: height / horizontal padding / corner radius. */
export const CHIP_H = 17
export const CHIP_PAD_X = 5
export const CHIP_RADIUS = 3

/** Neutral dark chip background (info chips that aren't tied to a semantic color). */
export const CHIP_NEUTRAL_BG = 'rgba(24, 28, 38, 0.92)'

// ---------------------------------------------------------------------------
// Canvas utilities
// ---------------------------------------------------------------------------

/**
 * Logical (CSS-pixel) size of the drawing surface. The engine pre-scales the
 * context by devicePixelRatio, so divide the backing-store size by the
 * context's current scale instead of trusting canvas.width raw.
 */
export function logicalSize(ctx: CanvasRenderingContext2D): { w: number; h: number } {
  const t = ctx.getTransform()
  const sx = t.a !== 0 ? Math.abs(t.a) : 1
  const sy = t.d !== 0 ? Math.abs(t.d) : 1
  return { w: ctx.canvas.width / sx, h: ctx.canvas.height / sy }
}

interface RGBA {
  r: number
  g: number
  b: number
  a: number
}

// Cache parsed colors — render runs every frame.
const colorCache = new Map<string, RGBA>()

/**
 * Parse any CSS color without touching the DOM: assigning to ctx.fillStyle
 * normalizes the value to "#rrggbb" (opaque) or "rgba(r, g, b, a)".
 */
function parseColor(ctx: CanvasRenderingContext2D, color: string): RGBA {
  const cached = colorCache.get(color)
  if (cached) return cached

  const prev = ctx.fillStyle
  ctx.fillStyle = color
  const norm = ctx.fillStyle
  ctx.fillStyle = prev

  let out: RGBA = { r: 0, g: 0, b: 0, a: 1 }
  if (typeof norm === 'string') {
    if (norm.charAt(0) === '#' && norm.length >= 7) {
      out = {
        r: parseInt(norm.slice(1, 3), 16),
        g: parseInt(norm.slice(3, 5), 16),
        b: parseInt(norm.slice(5, 7), 16),
        a: 1,
      }
    } else {
      const m = /rgba?\(([^)]+)\)/.exec(norm)
      if (m && m[1]) {
        const parts = m[1].split(',').map((s) => parseFloat(s))
        out = { r: parts[0] ?? 0, g: parts[1] ?? 0, b: parts[2] ?? 0, a: parts[3] ?? 1 }
      }
    }
  }
  if (colorCache.size > 256) colorCache.clear() // hard cap; colors are few in practice
  colorCache.set(color, out)
  return out
}

/** CSS color string = `color` with its alpha multiplied by `alpha`. */
export function withAlpha(ctx: CanvasRenderingContext2D, color: string, alpha: number): string {
  const c = parseColor(ctx, color)
  return `rgba(${c.r}, ${c.g}, ${c.b}, ${(c.a * alpha).toFixed(3)})`
}

/** Black or white, whichever reads best on top of `bg` (per luminance). */
export function contrastText(ctx: CanvasRenderingContext2D, bg: string): string {
  const c = parseColor(ctx, bg)
  const lum = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b
  return lum > 145 ? '#0f0f0f' : '#ffffff'
}

/** Manual rounded-rect path (avoids relying on CanvasPath.roundRect lib types). */
export function roundRectPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

/** Offset that keeps odd-width horizontal/vertical strokes pixel-crisp. */
export function crisp(v: number, lineWidth: number): number {
  return Math.round(lineWidth) % 2 === 1 ? Math.round(v) + 0.5 : Math.round(v)
}

export function strokeLine(
  ctx: CanvasRenderingContext2D,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
): void {
  ctx.beginPath()
  ctx.moveTo(x0, y0)
  ctx.lineTo(x1, y1)
  ctx.stroke()
}

export type ChipAlign = 'left' | 'center' | 'right'

/**
 * Draw a small rounded label chip. `y` is the chip's vertical center;
 * `x` is its left edge ('left'), center ('center') or right edge ('right').
 * Text color is black/white chosen by background luminance.
 * Returns the chip's pixel rect (useful for stacking labels).
 */
export function drawChip(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  text: string,
  bg: string,
  align: ChipAlign = 'left',
): { x: number; y: number; w: number; h: number } {
  ctx.font = FONT_CHIP
  const w = Math.ceil(ctx.measureText(text).width) + CHIP_PAD_X * 2
  const left = align === 'left' ? x : align === 'right' ? x - w : x - w / 2
  const top = y - CHIP_H / 2
  roundRectPath(ctx, left, top, w, CHIP_H, CHIP_RADIUS)
  ctx.fillStyle = bg
  ctx.fill()
  ctx.fillStyle = contrastText(ctx, bg)
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, left + CHIP_PAD_X, y + 0.5)
  return { x: left, y: top, w, h: CHIP_H }
}

/** White square handle with an accent border, centered at (x, y). */
export function drawHandle(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  accent: string,
): void {
  const half = HANDLE_SIZE / 2
  ctx.lineWidth = 1
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(x - half, y - half, HANDLE_SIZE, HANDLE_SIZE)
  ctx.strokeStyle = accent
  ctx.strokeRect(x - half, y - half, HANDLE_SIZE, HANDLE_SIZE)
}

// ---------------------------------------------------------------------------
// Number formatting
// ---------------------------------------------------------------------------

/** Price with thousands separators at the symbol's precision, e.g. "64,210.00". */
export function fmtPrice(price: number, precision: number): string {
  if (!Number.isFinite(price)) return String(price)
  const dp = Math.max(0, Math.min(8, Math.round(precision)))
  const neg = price < 0
  const fixed = Math.abs(price).toFixed(dp)
  const dot = fixed.indexOf('.')
  const intPart = dot === -1 ? fixed : fixed.slice(0, dot)
  const frac = dot === -1 ? '' : fixed.slice(dot)
  let grouped = ''
  for (let i = 0; i < intPart.length; i++) {
    if (i > 0 && (intPart.length - i) % 3 === 0) grouped += ','
    grouped += intPart.charAt(i)
  }
  return (neg ? '-' : '') + grouped + frac
}

/** Compact magnitude: 950 → "950", 12_400 → "12.4K", 3_400_000 → "3.4M". */
export function fmtCompact(n: number): string {
  if (!Number.isFinite(n)) return String(n)
  const neg = n < 0 ? '-' : ''
  let a = Math.abs(n)
  const units = ['', 'K', 'M', 'B', 'T']
  let u = 0
  while (a >= 999.95 && u < units.length - 1) {
    a /= 1000
    u++
  }
  const s = a >= 99.95 ? a.toFixed(0) : a.toFixed(1).replace(/\.0$/, '')
  return neg + s + units[u]
}

/** Signed percent with two decimals: "+3.44%" / "-1.72%". */
export function fmtSignedPct(p: number): string {
  if (!Number.isFinite(p)) return '0.00%'
  return `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`
}

/** Dollar amount at a sensible precision for chip labels (no "$" prefix). */
export function fmtMoney(v: number): string {
  if (!Number.isFinite(v)) return '0'
  const a = Math.abs(v)
  if (a >= 1000) return fmtCompact(v)
  if (a >= 100) return v.toFixed(0)
  if (a >= 10) return v.toFixed(1)
  return v.toFixed(2)
}

/** Numeric prop with fallback (Drawing.props values are loosely typed). */
export function propNum(d: Drawing, key: string, fallback: number): number {
  const v = d.props ? d.props[key] : undefined
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback
}

// ---------------------------------------------------------------------------
// Candle math
// ---------------------------------------------------------------------------

/** Index of the first candle with time >= t (candles ascending). May be candles.length. */
export function lowerBound(candles: Candle[], t: number): number {
  let lo = 0
  let hi = candles.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (candles[mid].time < t) lo = mid + 1
    else hi = mid
  }
  return lo
}

/** Index of the candle whose open time is nearest t, or -1 when empty. */
export function nearestIndex(candles: Candle[], t: number): number {
  const n = candles.length
  if (n === 0) return -1
  const i = lowerBound(candles, t)
  if (i <= 0) return 0
  if (i >= n) return n - 1
  return t - candles[i - 1].time <= candles[i].time - t ? i - 1 : i
}

function trueRange(c: Candle, prev: Candle): number {
  return Math.max(c.high - c.low, Math.abs(c.high - prev.close), Math.abs(c.low - prev.close))
}

/**
 * Wilder-smoothed ATR over candles[0..endIndex] (inclusive).
 * Returns undefined when fewer than period+1 candles are available
 * (i.e. not enough data for `period` true ranges).
 */
export function wilderATR(candles: Candle[], endIndex: number, period = 14): number | undefined {
  const end = Math.min(endIndex, candles.length - 1)
  if (period < 1 || end < period) return undefined
  let atr = 0
  for (let i = 1; i <= period; i++) atr += trueRange(candles[i], candles[i - 1])
  atr /= period
  for (let i = period + 1; i <= end; i++) {
    atr = (atr * (period - 1) + trueRange(candles[i], candles[i - 1])) / period
  }
  return atr
}

/** Distance from (px,py) to segment (x0,y0)-(x1,y1). */
export function distToSegment(
  px: number,
  py: number,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
): number {
  const dx = x1 - x0
  const dy = y1 - y0
  const lenSq = dx * dx + dy * dy
  let t = lenSq === 0 ? 0 : ((px - x0) * dx + (py - y0) * dy) / lenSq
  t = Math.max(0, Math.min(1, t))
  return Math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))
}
