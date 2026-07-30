// Levels the engine already knows, drawn over the chart. The ONLY file that
// touches CandL's coordinate system: converters are live objects and must be
// re-queried every frame (their docs say so — zoom/pan invalidates them).
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { Converters } from '../vendor/candl/drawings/types'
import type { MapLevel, TapeBar } from '../data'
import { palette } from '../theme'
import type { Mode } from '../theme'

/** What the σ ribbons need, re-read every frame like every other getter here:
 *  the bars carry each sigma level per-bar, `times` is the candle time axis
 *  (ContractChart already builds this for hover mapping — reused, not
 *  recomputed), and `cursor` is the replay index so the ribbons stop exactly
 *  where the candles do. */
export interface RibbonData {
  bars: TapeBar[]
  times: number[]
  cursor: number | null
}

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

export function startLevelsOverlay(
  canvas: HTMLCanvasElement,
  host: HTMLElement,
  engine: IChartEngine,
  getLevels: () => MapLevel[],
  getMode: () => Mode,
  getRibbon: () => RibbonData,
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
    const ribbon = getRibbon()
    const rBars = ribbon.bars
    const rTimes = ribbon.times
    // Causality clamp: the ribbons' last drawn bar is the replay cursor, same
    // as the candles — never the newest bar the cursor is hiding.
    const rLastIdx = rBars.length
      ? (ribbon.cursor != null ? Math.max(0, Math.min(ribbon.cursor, rBars.length - 1)) : rBars.length - 1)
      : -1
    const rFirst = rBars[0]
    const rLast = rLastIdx >= 0 ? rBars[rLastIdx] : undefined
    // Signature additions for the ribbons: bar count and cursor catch any
    // append/replay-scrub, and the first+last VISIBLE bar's u1/d1 catch a
    // sigma value changing in place (e.g. a live VWAP/σ recompute on the same
    // bar count) — cheap because it reads 2 bars, never all ~375 every frame.
    const sig = `${mode}|${bw}x${bh}|${pane.x},${pane.y},${pane.width},${pane.height}` +
      `|${conv.priceToY(0)},${conv.priceToY(1000)}` +
      `|${levels.map((l) => `${l.kind}:${l.value}:${l.label}`).join(';')}` +
      `|${rBars.length},${ribbon.cursor}` +
      `|${rFirst?.u1},${rFirst?.d1},${rLast?.u1},${rLast?.d1}`
    if (sig === lastSig) return
    lastSig = sig

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    // σ ribbons: filled zones between the deviations, drawn UNDER the level
    // lines/chips below but over the chart canvas underneath this one. Widest
    // (±3σ) first so the narrower, slightly stronger ±1σ layers on top.
    if (rLastIdx >= 0) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      const brass = pal.accent
      drawRibbon(ctx, conv, rBars, rTimes, rLastIdx, 'u3', 'd3', withAlpha(brass, RIBBON_ALPHA.u3d3))
      drawRibbon(ctx, conv, rBars, rTimes, rLastIdx, 'u2', 'd2', withAlpha(brass, RIBBON_ALPHA.u2d2))
      drawRibbon(ctx, conv, rBars, rTimes, rLastIdx, 'u1', 'd1', withAlpha(brass, RIBBON_ALPHA.u1d1))
      ctx.restore()
    }

    ctx.font = '10px ui-monospace, SFMono-Regular, Menlo, monospace'
    ctx.textBaseline = 'bottom'

    const structColor = withAlpha(pal.accent, 0.85)
    const trapColor = withAlpha(pal.bear, 0.85)

    // Copy before sorting — getLevels() may return the live MAP.levels array,
    // and mutating it would corrupt whatever else reads it (e.g. Task 6's rail).
    const visible = levels
      .filter((lvl) => lvl.kind !== 'now') // the tape itself is the price
      .map((lvl) => ({ lvl, y: conv.priceToY(lvl.value) }))
      .filter(({ y }) => y >= pane.y + 4 && y <= pane.y + pane.height - 4)
      .sort((a, b) => a.y - b.y)

    let lastLabelY = -Infinity // last *drawn label's* y, not the last level's y
    for (const { lvl, y } of visible) {
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

      // Draw the label only if it clears the last *drawn* label by the min gap
      // AND clears the engine's own OHLC legend in the top-left of the pane.
      if (y - lastLabelY >= LABEL_GAP && y >= pane.y + LEGEND_BAND_PX) {
        ctx.fillText(`${lvl.label} ${lvl.value.toFixed(1)}`, pane.x + 6, y - 2)
        lastLabelY = y
      }
    }
  }

  raf = requestAnimationFrame(draw)
  return () => cancelAnimationFrame(raf)
}
