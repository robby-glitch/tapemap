/**
 * Canvas chart engine: single high-DPI canvas, bar-index based time scale,
 * stacked panes (price + one sub-pane per 'pane' indicator), shared time axis,
 * drawings, crosshair and pan/zoom interactions.
 */
import type { Candle, Theme } from '../core/types'
import type { Converters, DrawEnv, Drawing, DrawingPoint, DrawingToolId } from '../drawings/types'
import {
  renderDrawing,
  hitTestDrawing,
  hitTestHandle,
  translateDrawing,
  movePoint,
  pointsNeeded,
  toolImpl,
  defaultDrawing,
} from '../drawings'
import type {
  ChartEngineOptions,
  ChartType,
  IChartEngine,
  IndicatorRenderData,
  ProjectionBand,
  ProjectionLine,
} from './types'
import { isRebinnedChartType } from './types'
import {
  toHeikinAshi,
  toRenko,
  toLineBreak,
  toKagi,
  toPointAndFigure,
  toRangeBars,
  autoRenkoBoxSize,
  autoPnfBoxSize,
  autoRangeSize,
  type KagiPoint,
} from './chartTransforms'
import type { Alert, ChartSettings } from '../alerts/types'
import { THEMES, FONT } from './themes'
import type { ChartColors } from './themes'
import type { ViewState } from './scales'
import {
  TimeScale,
  PriceScale,
  computeTimeTicks,
  formatTimeTickLabel,
  formatFullTime,
  formatPrice,
  formatCompact,
  decimalsForStep,
  niceStep,
} from './scales'
import * as R from './renderers'
import { attachInteractions } from './interactions'

const PRICE_AXIS_W = 64
const TIME_AXIS_H = 26
const SUB_PANE_H = 110
const SEPARATOR_H = 1
const MIN_VISIBLE_BARS = 3
const DEFAULT_VISIBLE_BARS = 160
const RIGHT_OFFSET_BARS = 5
const HISTORY_TRIGGER_BARS = 10
const MAGNET_SNAP_PX = 50
/** Side length of the square "A" (auto/manual) toggle button at the top of the price axis. */
const AXIS_TOGGLE_SIZE = 18
/** Inset of the toggle button from the right axis' top-left corner. */
const AXIS_TOGGLE_MARGIN = 4
/**
 * Pixels of vertical drag mapped to one e-fold of the manual price range when
 * scaling via the axis: range *= exp(dyPx / AXIS_SCALE_PX). Larger = gentler.
 */
const AXIS_SCALE_PX = 180
const FREEHAND_MIN_DIST_PX = 3
const FREEHAND_MAX_POINTS = 400
/** Vertical pixel tolerance for grabbing an alert line to drag it. */
const ALERT_HIT_PX = 5

interface PaneLayout {
  kind: 'main' | 'indicator'
  top: number
  height: number
  indicator?: IndicatorRenderData
}

interface Layout {
  width: number
  height: number
  plotWidth: number
  timeAxisTop: number
  panes: PaneLayout[]
}

type DragState =
  /**
   * Body drag. Horizontal time pan via `lastX` (always). In 'manual' price-scale
   * mode it is also a vertical price pan via `lastY`, making body-drag 2D.
   */
  | { mode: 'pan'; lastX: number; lastY: number }
  | { mode: 'move-drawing'; id: string; original: Drawing; startTime: number; startPrice: number; moved: boolean }
  | { mode: 'move-handle'; id: string; original: Drawing; handleIndex: number; moved: boolean }
  /** In-progress freehand (brush) capture; the drawing is committed on pointerup. */
  | { mode: 'freehand'; drawing: Drawing; lastPx: number; lastPy: number }
  /** Dragging a price-alert line vertically; onAlertMove fires on pointerup. */
  | { mode: 'move-alert'; id: string; price: number; moved: boolean }
  /**
   * Dragging the right price-axis strip to SCALE the main pane's price range
   * about the price under the drag-start Y. Switches the main scale to 'manual'.
   * `startMin`/`startMax` snapshot the range at gesture start; `anchorPrice` is
   * the price held fixed; `startY` is the pixel origin of the drag.
   */
  | { mode: 'scale-axis'; startMin: number; startMax: number; anchorPrice: number; startY: number }

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(Math.max(v, lo), hi)
}

/** Format milliseconds-remaining as a candle-close countdown (e.g. "04:31", "1:04:31", "6d 23:04"). */
function formatCountdown(ms: number): string {
  let s = Math.floor(ms / 1000)
  const days = Math.floor(s / 86400)
  s -= days * 86400
  const h = Math.floor(s / 3600)
  s -= h * 3600
  const m = Math.floor(s / 60)
  const sec = s - m * 60
  const pad = (n: number): string => String(n).padStart(2, '0')
  if (days > 0) return `${days}d ${pad(h)}:${pad(m)}`
  if (h > 0) return `${h}:${pad(m)}:${pad(sec)}`
  return `${pad(m)}:${pad(sec)}`
}

function isEditableTarget(t: EventTarget | null): boolean {
  if (!(t instanceof HTMLElement)) return false
  const tag = t.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || t.isContentEditable
}

export function createChartEngine(container: HTMLElement, options: ChartEngineOptions): IChartEngine {
  // ----- canvas setup ------------------------------------------------------
  const canvas = document.createElement('canvas')
  canvas.style.display = 'block'
  // Touch gestures on the chart drive pan / pinch-zoom — never the browser's
  // page scroll/zoom. (The interaction layer also preventDefaults touch events.)
  canvas.style.touchAction = 'none'
  const maybeCtx = canvas.getContext('2d')
  if (!maybeCtx) throw new Error('CandL chart: 2d canvas context unavailable')
  const ctx = maybeCtx
  container.appendChild(canvas)

  // ----- state -------------------------------------------------------------
  let theme: Theme = options.theme
  let precision = options.pricePrecision
  let chartType: ChartType = options.chartType
  let candles: Candle[] = []
  /**
   * The series actually drawn on the bar-index axis + driving the price scale,
   * derived from `candles` + chartType:
   *  - 1:1 types (candles/hollow/bars/line/area/...): identical times to
   *    `candles` (heikin transforms OHLC but keeps the count), so index↔candle
   *    mapping is unchanged from the original 4-type behavior.
   *  - re-binned types (renko/linebreak/kagi): a SYNTHETIC array whose times
   *    approximate each element's source-candle time. `ts` is built from THESE
   *    times, so the index axis, crosshair and last-price track the synthetic
   *    series. Volume + indicators are skipped for re-binned types (they're
   *    computed on the original candles and no longer align).
   */
  let renderSeries: Candle[] = []
  /** Kagi vertices when chartType === 'kagi' (else null). Drawn as a polyline. */
  let kagiPoints: KagiPoint[] | null = null
  /**
   * Box height (in price) of the active Point & Figure series, so the renderer
   * can stack the right number of X/O glyphs per column. 0 when chartType isn't
   * 'pnf'. Set in rebuildSeries alongside renderSeries.
   */
  let pnfBoxSize = 0
  let indicators: IndicatorRenderData[] = []
  /**
   * Replay cursor in render-series index space, or null when replay is OFF.
   * When set, the engine clips every series-derived layer to bars [0..cursor]
   * (the bars after it are the hidden "future"); see effectiveLength(). Always
   * kept within [0, renderSeries.length-1] by clampReplayCursor(), re-applied
   * after setData/updateLast in case the series shrank.
   */
  let replayCursor: number | null = null
  /**
   * Whether replay playback is actively running (host-pushed via
   * setReplayPlaying). Zoom gestures consult this: while playing, the view
   * must keep the cursor on screen or the next tick's auto-scroll snaps the
   * view away mid-gesture; while paused there is no tick, so pointer-anchored
   * zoom is free to move the playhead off screen (inspecting history).
   */
  let replayPlaying = false
  let projLines: ProjectionLine[] = []
  let projBand: ProjectionBand | null = null
  let drawings: Drawing[] = []
  let alerts: Alert[] = []
  /**
   * Appearance settings. Null until the host calls setSettings; while null the
   * engine falls back to the active theme's up/down colors with grid + crosshair
   * shown (matching the contract's "default before first setSettings").
   */
  let settings: ChartSettings | null = null
  /**
   * Tag rectangles (CSS px) of the alert affordances drawn this frame, by id —
   * rebuilt every render so click hit-testing always matches what's on screen.
   */
  let alertTagRects: { id: string; x: number; y: number; width: number; height: number }[] = []
  let selectedId: string | null = null
  let activeTool: DrawingToolId | null = null
  let pendingPoints: DrawingPoint[] = []
  let magnet = false
  let barMs = 60_000 // median candle spacing; recomputed on setData
  /**
   * Main price-pane scale mode. In 'auto' (default) computeMainScale auto-fits
   * the visible data, the original behavior. In 'manual' it uses the stored
   * `manualScale` { min, max } verbatim (no auto-fit, no margin re-application),
   * so the user's drag-set range survives setData/updateLast until reset. Only
   * the MAIN pane has a manual mode; indicator sub-panes always auto-fit.
   */
  let priceScaleMode: 'auto' | 'manual' = 'auto'
  /** The fixed main-pane price range while `priceScaleMode === 'manual'`. */
  let manualScale: { min: number; max: number } | null = null
  /** Logarithmic main price axis (the "L" toggle); independent of auto/manual. */
  let priceScaleLog = false
  /**
   * The "A" toggle button rect (CSS px) drawn this frame at the top of the price
   * axis, or null when there's no axis to draw on. Rebuilt every render so click
   * hit-testing always matches what's on screen.
   */
  let axisToggleRect: { x: number; y: number; width: number; height: number } | null = null
  /** The "L" log-scale toggle button rect (CSS px) drawn this frame, or null. */
  let logToggleRect: { x: number; y: number; width: number; height: number } | null = null
  let drag: DragState | null = null
  let hover: { x: number; y: number } | null = null
  let historyArmed = true
  let destroyed = false
  let rafId = 0
  let currentDpr = 1
  const size = { width: 0, height: 0 }

  const ts = new TimeScale()

  // ----- sizing / render loop ----------------------------------------------
  function applySize(): void {
    const w = container.clientWidth
    const h = container.clientHeight
    currentDpr = Math.max(1, window.devicePixelRatio || 1)
    size.width = w
    size.height = h
    canvas.width = Math.max(1, Math.round(w * currentDpr))
    canvas.height = Math.max(1, Math.round(h * currentDpr))
    canvas.style.width = `${w}px`
    canvas.style.height = `${h}px`
    ctx.setTransform(currentDpr, 0, 0, currentDpr, 0, 0)
  }

  /** Schedule a render on the next animation frame (coalesces repeated calls). */
  function invalidate(): void {
    if (destroyed || rafId !== 0) return
    rafId = requestAnimationFrame(() => {
      rafId = 0
      render()
    })
  }

  // Re-render once a second so the live candle's close-countdown keeps ticking
  // even when no price update arrives. invalidate() coalesces to one frame.
  const countdownTimer = setInterval(invalidate, 1000)

  // ----- layout & scales ----------------------------------------------------
  function computeLayout(): Layout {
    const width = size.width
    const height = size.height
    const plotWidth = Math.max(0, width - PRICE_AXIS_W)
    const paneInds = indicators.filter((i) => i.placement === 'pane')
    const np = paneInds.length
    const timeAxisTop = Math.max(0, height - TIME_AXIS_H)
    const available = Math.max(0, timeAxisTop - np * SEPARATOR_H)
    let subH = np > 0 ? SUB_PANE_H : 0
    let mainH = available - np * subH
    if (np > 0 && mainH < 120) {
      // Not enough room for full-size sub-panes: shrink them, keep main usable.
      subH = Math.max(40, Math.floor((available - 120) / np))
      mainH = Math.max(0, available - np * subH)
    }
    const panes: PaneLayout[] = [{ kind: 'main', top: 0, height: mainH }]
    let top = mainH
    for (const ind of paneInds) {
      top += SEPARATOR_H
      panes.push({ kind: 'indicator', top, height: subH, indicator: ind })
      top += subH
    }
    ts.plotWidth = plotWidth
    return { width, height, plotWidth, timeAxisTop, panes }
  }

  function paneIndexAt(y: number, layout: Layout): number {
    for (let i = 0; i < layout.panes.length; i++) {
      const p = layout.panes[i]
      if (y >= p.top && y < p.top + p.height) return i
    }
    return -1
  }

  /**
   * Main-pane price scale. In 'manual' mode it uses the user's fixed
   * { min, max } verbatim (the drag-set range, no auto-fit / no margin), so the
   * scale stays put across setData/updateLast. In 'auto' mode (default) it
   * auto-fits the visible series + visible overlay values with 8% margins.
   */
  function computeMainScale(pane: PaneLayout): PriceScale {
    if (priceScaleMode === 'manual' && manualScale !== null) {
      return new PriceScale(
        pane.top,
        pane.height,
        manualScale.min,
        manualScale.max,
        priceScaleLog && manualScale.min > 0,
      )
    }
    const range = ts.visibleRange()
    const from = range.from
    // Replay clips data at the cursor; the auto-fit (series + overlay values +
    // projections) must ignore the hidden "future" so it never includes bars
    // past the cursor. effectiveLength()-1 is the last visible bar.
    const to = Math.min(range.to, effectiveLength() - 1)
    let min = Infinity
    let max = -Infinity
    if (renderSeries.length > 0 && from <= to) {
      // Close-only fitting for the pure-line / close-anchored types; the rest
      // (candles/bars/heikin/renko/etc.) fit to the full high-low range.
      const closeOnly =
        chartType === 'line' ||
        chartType === 'area' ||
        chartType === 'linemarkers' ||
        chartType === 'step' ||
        chartType === 'baseline' ||
        chartType === 'columns' ||
        chartType === 'kagi'
      for (let i = from; i <= to; i++) {
        const c = renderSeries[i]
        if (closeOnly) {
          if (c.close < min) min = c.close
          if (c.close > max) max = c.close
        } else {
          if (c.low < min) min = c.low
          if (c.high > max) max = c.high
        }
      }
      // Re-binned series' indicators are computed on the original candles and no
      // longer align bar-for-bar, so they're skipped (here and at draw time).
      if (!isRebinnedChartType(chartType)) {
        for (const ind of indicators) {
          if (ind.placement !== 'overlay') continue
          for (const out of ind.outputs) {
            const last = Math.min(to, out.values.length - 1)
            for (let i = from; i <= last; i++) {
              const v = out.values[i]
              if (v == null || !isFinite(v)) continue
              if (v < min) min = v
              if (v > max) max = v
            }
          }
        }
      }
    }
    // Projections: include only points whose bar offsets are (about) on screen,
    // so visible ghosts never render off-scale but far-future points don't
    // distort the fit when the user is zoomed elsewhere. One bar of margin on
    // each side mirrors how line series extend past the viewport edges.
    if (renderSeries.length > 0 && (projLines.length > 0 || projBand !== null)) {
      const lastIdx = renderSeries.length - 1
      const includeProjectionPoints = (pts: { barOffset: number; price: number }[]): void => {
        for (const p of pts) {
          const center = lastIdx + p.barOffset + 0.5 // center-x bar index of the point
          if (center < ts.view.start - 1 || center > ts.view.end + 1) continue
          if (!isFinite(p.price)) continue
          if (p.price < min) min = p.price
          if (p.price > max) max = p.price
        }
      }
      for (const line of projLines) includeProjectionPoints(line.points)
      if (projBand) {
        includeProjectionPoints(projBand.upper)
        includeProjectionPoints(projBand.lower)
      }
    }
    if (!isFinite(min) || !isFinite(max)) {
      min = 0
      max = 1
    }
    if (min === max) {
      const p = Math.abs(min) * 0.01 || 1
      min -= p
      max += p
    }
    // Log axis (only with a strictly positive range): pad in log space so the
    // 8% margins look even, and never let the padded min cross zero.
    if (priceScaleLog && min > 0) {
      const lmin = Math.log(min)
      const lmax = Math.log(max)
      const lpad = (lmax - lmin) * 0.08
      return new PriceScale(pane.top, pane.height, Math.exp(lmin - lpad), Math.exp(lmax + lpad), true)
    }
    const pad = (max - min) * 0.08
    return new PriceScale(pane.top, pane.height, min - pad, max + pad)
  }

  /** Scale for an indicator sub-pane: fixed range if declared, else auto-fit. */
  function computePaneScale(pane: PaneLayout): PriceScale {
    const ind = pane.indicator as IndicatorRenderData
    if (ind.range) {
      return new PriceScale(pane.top, pane.height, ind.range[0], ind.range[1])
    }
    const range = ts.visibleRange()
    const from = range.from
    // Replay clips data at the cursor: the pane auto-fit must ignore indicator
    // values past it so the sub-pane scale matches the clipped plot.
    const to = Math.min(range.to, effectiveLength() - 1)
    let min = Infinity
    let max = -Infinity
    let hasHistogram = false
    for (const out of ind.outputs) {
      if ((out.style ?? 'line') === 'histogram') hasHistogram = true
      const last = Math.min(to, out.values.length - 1)
      for (let i = Math.max(0, from); i <= last; i++) {
        const v = out.values[i]
        if (v == null || !isFinite(v)) continue
        if (v < min) min = v
        if (v > max) max = v
      }
    }
    if (hasHistogram) {
      // Histograms grow from zero; keep the baseline inside the pane.
      if (min > 0) min = 0
      if (max < 0) max = 0
    }
    if (!isFinite(min) || !isFinite(max)) {
      min = 0
      max = 1
    }
    if (min === max) {
      const p = Math.abs(min) * 0.01 || 1
      min -= p
      max += p
    }
    const pad = (max - min) * 0.08
    return new PriceScale(pane.top, pane.height, min - pad, max + pad)
  }

  /** Converters for the main pane (the contract object handed to the drawings module). */
  function makeConverters(mainScale: PriceScale): Converters {
    return {
      timeToX: (time) => ts.timeToX(time),
      xToTime: (x) => ts.xToTime(x),
      priceToY: (price) => mainScale.priceToY(price),
      yToPrice: (y) => mainScale.yToPrice(y),
    }
  }

  /**
   * Memo for the main-pane scale behind getMainConverters. computeMainScale is
   * O(visible bars) and overlay consumers (e.g. the Oracle storm) call
   * priceToY/yToPrice thousands of times per frame, so we recompute only when
   * an input actually changed. The cache is keyed by VALUE on every input of
   * computeMainScale (viewport, size, render-series identity/length + last OHLC,
   * indicators/projections refs, chart type), so pan/zoom, resize, setData,
   * updateLast, setIndicators, setProjections and setChartType all miss it
   * naturally — no explicit invalidation hooks, hence no staleness pitfalls.
   * `renderSeries` gets a fresh array reference on every rebuildSeries(), so it
   * is a complete change signal for both 1:1 and re-binned chart types.
   */
  let liveScaleCache: {
    scale: PriceScale
    viewStart: number
    viewEnd: number
    width: number
    height: number
    seriesRef: Candle[]
    seriesCount: number
    lastHigh: number
    lastLow: number
    lastClose: number
    indicatorsRef: IndicatorRenderData[]
    projLinesRef: ProjectionLine[]
    projBandRef: ProjectionBand | null
    type: ChartType
    mode: 'auto' | 'manual'
    manualMin: number
    manualMax: number
    log: boolean
  } | null = null

  function liveMainScale(): PriceScale {
    const n = renderSeries.length
    const last = n > 0 ? renderSeries[n - 1] : null
    const c = liveScaleCache
    if (
      c !== null &&
      c.mode === priceScaleMode &&
      c.log === priceScaleLog &&
      c.manualMin === (manualScale !== null ? manualScale.min : NaN) &&
      c.manualMax === (manualScale !== null ? manualScale.max : NaN) &&
      c.viewStart === ts.view.start &&
      c.viewEnd === ts.view.end &&
      c.width === size.width &&
      c.height === size.height &&
      c.seriesRef === renderSeries &&
      c.seriesCount === n &&
      c.indicatorsRef === indicators &&
      c.projLinesRef === projLines &&
      c.projBandRef === projBand &&
      c.type === chartType &&
      (last === null || (c.lastHigh === last.high && c.lastLow === last.low && c.lastClose === last.close))
    ) {
      return c.scale
    }
    // computeLayout() also refreshes ts.plotWidth, keeping timeToX consistent
    // even if no render pass has happened since the last size change.
    const scale = computeMainScale(computeLayout().panes[0])
    liveScaleCache = {
      scale,
      viewStart: ts.view.start,
      viewEnd: ts.view.end,
      width: size.width,
      height: size.height,
      seriesRef: renderSeries,
      seriesCount: n,
      lastHigh: last !== null ? last.high : NaN,
      lastLow: last !== null ? last.low : NaN,
      lastClose: last !== null ? last.close : NaN,
      indicatorsRef: indicators,
      projLinesRef: projLines,
      projBandRef: projBand,
      type: chartType,
      mode: priceScaleMode,
      log: priceScaleLog,
      manualMin: manualScale !== null ? manualScale.min : NaN,
      manualMax: manualScale !== null ? manualScale.max : NaN,
    }
    return scale
  }

  /**
   * Stable wrapper handed out by getMainConverters: every method reads the
   * engine's CURRENT scales at call time (never a snapshot), so results track
   * pan/zoom/resize/data updates automatically. Same math as makeConverters.
   */
  const liveConverters: Converters = {
    timeToX: (time) => ts.timeToX(time),
    xToTime: (x) => ts.xToTime(x),
    priceToY: (price) => liveMainScale().priceToY(price),
    yToPrice: (y) => liveMainScale().yToPrice(y),
  }

  /** Median candle spacing in ms; cached (recomputed on setData). */
  function computeBarMs(): void {
    const n = candles.length
    if (n < 2) {
      barMs = ts.intervalMs || 60_000
      return
    }
    const deltas: number[] = []
    for (let i = 1; i < n; i++) {
      const d = candles[i].time - candles[i - 1].time
      if (d > 0) deltas.push(d)
    }
    if (deltas.length === 0) {
      barMs = ts.intervalMs || 60_000
      return
    }
    deltas.sort((a, b) => a - b)
    barMs = deltas[deltas.length >> 1]
  }

  /**
   * Recompute `renderSeries` / `kagiPoints` for the active chart type and point
   * `ts` at the series' times. O(n) — safe to call on every setData/updateLast/
   * setChartType. For 1:1 types the result mirrors `candles` (heikin remaps
   * OHLC but keeps the same times), preserving the original index↔candle axis.
   * For re-binned types it builds the synthetic array and rebuilds the time
   * axis from the synthetic elements' (approximate) source times.
   */
  function rebuildSeries(): void {
    // PnF box size only carries meaning for the 'pnf' type; reset it for the
    // rest so a switch away from PnF doesn't leave a stale value behind.
    pnfBoxSize = 0
    switch (chartType) {
      case 'heikin':
        renderSeries = toHeikinAshi(candles)
        kagiPoints = null
        break
      case 'renko':
        renderSeries = toRenko(candles, autoRenkoBoxSize(candles))
        kagiPoints = null
        break
      case 'linebreak':
        renderSeries = toLineBreak(candles, 3)
        kagiPoints = null
        break
      case 'pnf': {
        const box = autoPnfBoxSize(candles)
        pnfBoxSize = box
        renderSeries = toPointAndFigure(candles, box, 3)
        kagiPoints = null
        break
      }
      case 'range':
        renderSeries = toRangeBars(candles, autoRangeSize(candles))
        kagiPoints = null
        break
      case 'kagi': {
        const pts = toKagi(candles, 0.04)
        kagiPoints = pts
        // A 1-element synthetic candle array per Kagi vertex anchors the index
        // axis (close = vertex price) so the price scale auto-fits the line and
        // the crosshair/last-price work the same as the block series.
        renderSeries = pts.map((p) => ({
          time: p.time,
          open: p.price,
          high: p.price,
          low: p.price,
          close: p.price,
          volume: 0,
        }))
        break
      }
      default:
        // 1:1 with the loaded candles (candles/hollow/bars/hlcbars/line/
        // linemarkers/step/area/baseline/columns/highlow).
        renderSeries = candles
        kagiPoints = null
        break
    }
    ts.setTimes(renderSeries.map((c) => c.time))
  }

  /**
   * Effective number of render-series bars that are VISIBLE as data. Normally
   * the whole series; during replay it's clipped to cursor+1 so bars after the
   * cursor are hidden ("future"). Every series-derived layer (drawn series,
   * volume, indicator plots/legend, last-price, auto-fit, crosshair) clamps its
   * upper bound to effectiveLength()-1. With replayCursor === null this is
   * exactly renderSeries.length, so non-replay rendering is byte-identical.
   */
  function effectiveLength(): number {
    const n = renderSeries.length
    if (replayCursor === null) return n
    return Math.min(replayCursor + 1, n)
  }

  /** Re-clamp the replay cursor into the current series bounds (after data changes). */
  function clampReplayCursor(): void {
    if (replayCursor === null) return
    const n = renderSeries.length
    if (n === 0) {
      replayCursor = null
      return
    }
    replayCursor = clamp(replayCursor, 0, n - 1)
  }

  /** One DrawEnv per render/interaction pass (fields are cheap references). */
  function makeEnv(): DrawEnv {
    return { candles, pricePrecision: precision, barMs }
  }

  /**
   * The active up/down colors: settings override the theme's when present.
   * (Used for candle bodies/wicks, bars, volume, the last-price tag, the
   * change-% legend coloring and alert lines.)
   */
  function upColor(colors: ChartColors): string {
    return settings ? settings.upColor : colors.up
  }
  function downColor(colors: ChartColors): string {
    return settings ? settings.downColor : colors.down
  }

  /**
   * Theme palette with the up/down/accent colors swapped to the settings'
   * up/down (line + area series draw with `accent`, which the contract maps to
   * the up color). Background/text/grid base colors stay theme-governed. Cheap
   * shallow spread; built once per render and passed to the series renderers.
   */
  function effectiveColors(colors: ChartColors): ChartColors {
    if (!settings) return colors
    return { ...colors, up: settings.upColor, down: settings.downColor, accent: settings.upColor }
  }

  function gridVisible(): boolean {
    return settings ? settings.gridVisible : true
  }
  function crosshairVisible(): boolean {
    return settings ? settings.crosshairVisible : true
  }

  /**
   * Candidate drawing point at (x, y). With magnet on, the PRICE snaps to the
   * nearest of {open,high,low,close} of the candle under the cursor's bar when
   * that value is within MAGNET_SNAP_PX vertically. Time is never snapped.
   */
  function magnetSnap(x: number, y: number, conv: Converters): { time: number; price: number; snapped: boolean } {
    const time = conv.xToTime(x)
    const price = conv.yToPrice(y)
    if (!magnet || candles.length === 0) return { time, price, snapped: false }
    const idx = Math.floor(ts.xToIndex(x)) // bar i occupies [i, i+1)
    if (idx < 0 || idx >= candles.length) return { time, price, snapped: false }
    const c = candles[idx]
    let best = price
    let bestDy = Infinity
    for (const v of [c.open, c.high, c.low, c.close]) {
      const dy = Math.abs(conv.priceToY(v) - y)
      if (dy < bestDy) {
        bestDy = dy
        best = v
      }
    }
    if (bestDy <= MAGNET_SNAP_PX) return { time, price: best, snapped: true }
    return { time, price, snapped: false }
  }

  // ----- view manipulation ---------------------------------------------------
  // View-bound math uses effectiveLength(), not ts.count: during replay the
  // bars past the cursor are hidden, so zoom-out limits and edge clamps must
  // treat the revealed prefix as the whole dataset or the viewport can end up
  // on (mostly) blank "future" space. Outside replay the two are identical.
  function maxVisibleBars(): number {
    return Math.max(60, Math.round(effectiveLength() * 1.2) + RIGHT_OFFSET_BARS * 2)
  }

  /** Keep at least a couple of bars on screen so the user can't get lost. */
  function clampView(): void {
    const n = effectiveLength()
    if (n === 0) return
    let { start, end } = ts.view
    const range = end - start
    const minEnd = Math.min(n, 2)
    if (end < minEnd) {
      end = minEnd
      start = end - range
    }
    const maxStart = n - 2
    if (start > maxStart) {
      start = maxStart
      end = start + range
    }
    ts.view = { start, end }
  }

  /**
   * Right-edge margin (blank bars) used when pinning the replay cursor. The
   * full RIGHT_OFFSET_BARS on normal zooms, but proportional on tight zooms:
   * with a fixed 5-bar margin and a view narrower than ~7 bars, the pinned
   * viewport would contain only hidden-future bars and the chart would render
   * blank on every playback tick.
   */
  function replayPinMargin(width: number): number {
    return Math.min(RIGHT_OFFSET_BARS, Math.max(0, Math.floor(width / 3)))
  }

  /**
   * After a wheel/pinch zoom while replay is PLAYING, shift the zoomed view
   * just enough to keep an on-screen playhead on screen (same inequalities as
   * the setReplayCursor pin). Without this, pointer-anchored zoom pushes the
   * cursor out of the followed zone, the next playback tick snaps the view
   * back, and the chart ping-pongs for the rest of the gesture. Paused replay
   * is left alone: no tick will snap, and zooming the playhead off screen to
   * inspect revealed history is legitimate.
   */
  function keepReplayCursorVisible(prev: ViewState): void {
    if (replayCursor === null || !replayPlaying) return
    const wasVisible =
      replayCursor >= prev.start && replayCursor <= prev.end - replayPinMargin(prev.end - prev.start)
    if (!wasVisible) return
    let { start, end } = ts.view
    const width = end - start
    const margin = replayPinMargin(width)
    if (replayCursor >= start && replayCursor <= end - margin) return
    if (replayCursor < start) {
      start = replayCursor // slipped off the left edge: hold it there
      end = start + width
    } else {
      end = replayCursor + 1 + margin // off the right: same pin as the tick
      start = end - width
    }
    ts.view = { start, end }
  }

  function checkHistory(): void {
    if (historyArmed && ts.count > 0 && ts.view.start <= HISTORY_TRIGGER_BARS) {
      historyArmed = false // re-armed by the next setData
      options.onRequestHistory?.()
    }
  }

  function shiftView(deltaBars: number): void {
    ts.view = { start: ts.view.start + deltaBars, end: ts.view.end + deltaBars }
    clampView()
    checkHistory()
    invalidate()
  }

  function resetViewInternal(): void {
    // A full view reset also drops any manual price scale back to auto-fit.
    // effectiveLength keeps the reset off the hidden future during replay.
    exitManualScale()
    const n = effectiveLength()
    if (n === 0) {
      ts.view = { start: -DEFAULT_VISIBLE_BARS / 2, end: DEFAULT_VISIBLE_BARS / 2 }
      return
    }
    const end = n + RIGHT_OFFSET_BARS
    const visible = Math.min(DEFAULT_VISIBLE_BARS, Math.max(MIN_VISIBLE_BARS, n) + RIGHT_OFFSET_BARS)
    ts.view = { start: end - visible, end }
  }

  // ----- manual price-scale helpers ------------------------------------------
  /** The current main-pane price scale (honors auto vs manual mode). */
  function currentMainScale(): PriceScale {
    return computeMainScale(computeLayout().panes[0])
  }

  /**
   * Switch the main pane to MANUAL price scale, seeding the fixed range from
   * whatever is on screen right now (the auto-fit range when coming from 'auto',
   * else the existing manual range). No-op-safe to call when already manual.
   */
  function enterManualScale(): void {
    const s = currentMainScale()
    manualScale = { min: s.min, max: s.max }
    priceScaleMode = 'manual'
  }

  /** Restore the main pane to AUTO price scale (re-fit to visible data). */
  function exitManualScale(): void {
    priceScaleMode = 'auto'
    manualScale = null
  }

  // ----- drawings helpers -----------------------------------------------------
  function emitDrawings(): void {
    options.onDrawingsChange?.(drawings.slice())
  }

  function replaceDrawing(id: string, updated: Drawing): void {
    const idx = drawings.findIndex((d) => d.id === id)
    if (idx >= 0) drawings[idx] = updated
  }

  /** Change the selection, firing onSelectionChange only when the id actually changes. */
  function setSelection(id: string | null): void {
    if (selectedId === id) return
    selectedId = id
    const d = id !== null ? (drawings.find((x) => x.id === id) ?? null) : null
    options.onSelectionChange?.(d)
  }

  /** Re-announce the selected drawing (post-drag: same object reference onDrawingsChange sees). */
  function emitSelectionCurrent(): void {
    const d = selectedId !== null ? (drawings.find((x) => x.id === selectedId) ?? null) : null
    options.onSelectionChange?.(d)
  }

  function cancelTool(): void {
    pendingPoints = []
    if (activeTool !== null) {
      activeTool = null
      options.onActiveToolChange?.(null)
    }
    invalidate()
  }

  /** Shared post-placement flow: add, auto-select, disarm, notify host. */
  function commitDrawing(d: Drawing): void {
    drawings.push(d)
    selectedId = d.id
    pendingPoints = []
    activeTool = null
    emitDrawings()
    options.onActiveToolChange?.(null)
    options.onSelectionChange?.(d)
  }

  /** One placement click of an armed n-point tool (n >= 1; freehand is drag-driven). */
  function placeToolPoint(x: number, y: number, layout: Layout): void {
    const tool = activeTool
    if (!tool) return
    const need = pointsNeeded(tool)
    if (need < 1) return
    const scale = computeMainScale(layout.panes[0])
    const conv = makeConverters(scale)
    const snap = magnetSnap(x, y, conv)
    pendingPoints.push({ time: snap.time, price: snap.price })
    if (pendingPoints.length >= need) {
      const env = makeEnv()
      let drawing = defaultDrawing(tool, pendingPoints[0])
      drawing.points = pendingPoints.slice(0, need)
      const impl = toolImpl(tool)
      if (impl.expandOnCommit) drawing = impl.expandOnCommit(drawing, env)
      commitDrawing(drawing)
    }
    invalidate()
  }

  /** Start freehand (brush) capture: the drawing grows on pointermove, commits on pointerup. */
  function startFreehand(x: number, y: number, layout: Layout): void {
    const tool = activeTool
    if (!tool) return
    const conv = makeConverters(computeMainScale(layout.panes[0]))
    const drawing = defaultDrawing(tool, { time: conv.xToTime(x), price: conv.yToPrice(y) })
    drag = { mode: 'freehand', drawing, lastPx: x, lastPy: y }
    invalidate()
  }

  /**
   * Live preview of the armed tool: placed points + the cursor as the
   * provisional next point. Tool impls tolerate partial point lists.
   */
  function buildPreview(conv: Converters, mainPane: PaneLayout): Drawing | null {
    const tool = activeTool
    if (!tool) return null
    const need = pointsNeeded(tool)
    if (need < 1) return null // freehand previews via the drag state instead
    const inMain =
      hover !== null &&
      hover.x >= 0 &&
      hover.x <= ts.plotWidth &&
      hover.y >= mainPane.top &&
      hover.y < mainPane.top + mainPane.height
    const pts = pendingPoints.slice()
    if (inMain && hover && pts.length < need) {
      const snap = magnetSnap(hover.x, hover.y, conv)
      pts.push({ time: snap.time, price: snap.price })
    }
    if (pts.length === 0) return null
    const preview = defaultDrawing(tool, pts[0])
    preview.id = '__preview__'
    preview.points = pts
    return preview
  }

  // ----- alert hit-testing ------------------------------------------------------
  /** The alert whose right-axis tag/bell is under (x, y), or null. */
  function alertTagAt(x: number, y: number): Alert | null {
    for (const r of alertTagRects) {
      if (x >= r.x && x <= r.x + r.width && y >= r.y && y <= r.y + r.height) {
        return alerts.find((a) => a.id === r.id) ?? null
      }
    }
    return null
  }

  /**
   * The alert whose dashed line is within ALERT_HIT_PX of (x, y) inside the plot
   * area (not the axis). Returns the nearest match when several overlap.
   */
  function alertLineAt(x: number, y: number, layout: Layout, mainScale: PriceScale): Alert | null {
    if (x < 0 || x > layout.plotWidth) return null
    let best: Alert | null = null
    let bestDy = ALERT_HIT_PX + 1
    for (const a of alerts) {
      const ay = mainScale.priceToY(a.price)
      if (ay < mainScale.top || ay > mainScale.bottom) continue
      const dy = Math.abs(ay - y)
      if (dy <= ALERT_HIT_PX && dy < bestDy) {
        best = a
        bestDy = dy
      }
    }
    return best
  }

  // ----- price-axis region hit-testing ----------------------------------------
  /**
   * True when (x, y) is inside the MAIN pane's right price-axis strip
   * (x > plotWidth, within the main pane's vertical span). This is the band the
   * user drags to scale the price range / double-clicks to reset to auto.
   */
  function inMainAxisStrip(x: number, y: number, layout: Layout): boolean {
    const mainPane = layout.panes[0]
    return (
      x > layout.plotWidth &&
      x <= layout.width &&
      y >= mainPane.top &&
      y < mainPane.top + mainPane.height
    )
  }

  /** True when (x, y) is inside the "A" auto/manual toggle button drawn this frame. */
  function inAxisToggle(x: number, y: number): boolean {
    const r = axisToggleRect
    return r !== null && x >= r.x && x <= r.x + r.width && y >= r.y && y <= r.y + r.height
  }

  /** True when (x, y) is inside the "L" log-scale toggle button drawn this frame. */
  function inLogToggle(x: number, y: number): boolean {
    const r = logToggleRect
    return r !== null && x >= r.x && x <= r.x + r.width && y >= r.y && y <= r.y + r.height
  }

  // ----- interactions ----------------------------------------------------------
  function updateCursor(x: number, y: number): void {
    if (drag) return
    const layout = computeLayout()
    // Right price-axis affordances (no tool armed): the "A" toggle button and
    // the draggable scale strip. Checked before the plot test since both live
    // at x > plotWidth. Alert tags (also in this column) win via their own
    // hit-test below — but only inside the plot, so they never overlap here.
    if (!activeTool) {
      if (inAxisToggle(x, y) || inLogToggle(x, y)) {
        canvas.style.cursor = 'pointer'
        return
      }
      if (inMainAxisStrip(x, y, layout) && alertTagAt(x, y) === null) {
        canvas.style.cursor = 'ns-resize'
        return
      }
    }
    const inPlot = x >= 0 && x <= layout.plotWidth && y >= 0 && y < layout.timeAxisTop
    if (!inPlot) {
      canvas.style.cursor = 'default'
      return
    }
    if (activeTool) {
      canvas.style.cursor = 'crosshair'
      return
    }
    const mainPane = layout.panes[0]
    if (drawings.length > 0 && y >= mainPane.top && y < mainPane.top + mainPane.height) {
      const conv = makeConverters(computeMainScale(mainPane))
      const env = makeEnv()
      const sel = selectedId ? drawings.find((d) => d.id === selectedId) : undefined
      if (sel && hitTestHandle(sel, x, y, conv, env) >= 0) {
        canvas.style.cursor = 'pointer'
        return
      }
      for (let i = drawings.length - 1; i >= 0; i--) {
        if (hitTestDrawing(drawings[i], x, y, conv, env)) {
          canvas.style.cursor = 'pointer'
          return
        }
      }
    }
    // Alerts (only when no drawing/handle is under the cursor — checked above).
    if (alerts.length > 0) {
      if (alertTagAt(x, y) !== null) {
        canvas.style.cursor = 'pointer' // bell/tag removes on click
        return
      }
      const mainScale = computeMainScale(mainPane)
      if (alertLineAt(x, y, layout, mainScale) !== null) {
        canvas.style.cursor = 'grab' // line drags vertically
        return
      }
    }
    canvas.style.cursor = 'crosshair'
  }

  function handlePointerDown(x: number, y: number, ev: MouseEvent): void {
    if (ev.button !== 0) return
    const layout = computeLayout()
    const mainPane = layout.panes[0]
    const inMain =
      x >= 0 && x <= layout.plotWidth && y >= mainPane.top && y < mainPane.top + mainPane.height

    if (activeTool) {
      // While a tool is armed, drags never pan the chart. Alerts + axis are inert.
      if (inMain) {
        if (pointsNeeded(activeTool) === -1) startFreehand(x, y, layout)
        else placeToolPoint(x, y, layout)
      }
      return
    }

    // Price-axis "A" toggle button: flip auto<->manual. Checked before the axis
    // strip so a click on the button toggles rather than starting a scale drag.
    if (inAxisToggle(x, y)) {
      if (priceScaleMode === 'manual') exitManualScale()
      else enterManualScale() // seeds the manual range from the current visible min/max
      invalidate()
      return
    }

    // Price-axis "L" toggle: flip linear<->log. The cache keys on priceScaleLog,
    // so the next scale read recomputes under the new mode.
    if (inLogToggle(x, y)) {
      priceScaleLog = !priceScaleLog
      invalidate()
      return
    }

    // Right price-axis strip: drag vertically to SCALE the price range about the
    // price under the cursor. This switches the main scale to 'manual'. Alert
    // price tags also live in this column; defer to them (matching updateCursor)
    // so clicking a tag removes its alert instead of starting a scale drag.
    if (inMainAxisStrip(x, y, layout) && alertTagAt(x, y) === null) {
      const s = computeMainScale(mainPane)
      const anchorPrice = s.yToPrice(clamp(y, s.top, s.bottom))
      drag = { mode: 'scale-axis', startMin: s.min, startMax: s.max, anchorPrice, startY: y }
      // The gesture always ends in manual mode; seed it now so the first move
      // (and the toggle button's state) reflect the manual range immediately.
      manualScale = { min: s.min, max: s.max }
      priceScaleMode = 'manual'
      canvas.style.cursor = 'ns-resize'
      invalidate()
      return
    }

    // Alert affordance: clicking the bell/price tag removes the alert. Checked
    // before drawings since the tag sits in the right-axis column (x > plotWidth)
    // where no drawing can be hit.
    if (alerts.length > 0) {
      const tagAlert = alertTagAt(x, y)
      if (tagAlert) {
        options.onAlertRemove?.(tagAlert.id)
        return
      }
    }

    if (inMain && drawings.length > 0) {
      const conv = makeConverters(computeMainScale(mainPane))
      const env = makeEnv()
      const sel = selectedId ? drawings.find((d) => d.id === selectedId) : undefined
      if (sel) {
        const handleIndex = hitTestHandle(sel, x, y, conv, env)
        if (handleIndex >= 0) {
          drag = { mode: 'move-handle', id: sel.id, original: sel, handleIndex, moved: false }
          invalidate()
          return
        }
      }
      for (let i = drawings.length - 1; i >= 0; i--) {
        const d = drawings[i]
        if (hitTestDrawing(d, x, y, conv, env)) {
          setSelection(d.id)
          drag = {
            mode: 'move-drawing',
            id: d.id,
            original: d,
            startTime: conv.xToTime(x),
            startPrice: conv.yToPrice(y),
            moved: false,
          }
          invalidate()
          return
        }
      }
    }

    // Alert line: pressing within ALERT_HIT_PX (and not on a drawing/handle,
    // checked above) starts a vertical drag to move the alert. Never deselects
    // a drawing, and takes priority over panning.
    if (inMain && alerts.length > 0) {
      const mainScale = computeMainScale(mainPane)
      const lineAlert = alertLineAt(x, y, layout, mainScale)
      if (lineAlert) {
        drag = { mode: 'move-alert', id: lineAlert.id, price: lineAlert.price, moved: false }
        canvas.style.cursor = 'grabbing'
        invalidate()
        return
      }
    }

    // Empty click in the main pane deselects the current drawing.
    if (inMain && drawings.length > 0 && selectedId) {
      setSelection(null)
      invalidate()
    }

    drag = { mode: 'pan', lastX: x, lastY: y }
    canvas.style.cursor = 'grabbing'
  }

  function handlePointerMove(x: number, y: number, _ev: MouseEvent): void {
    hover = { x, y }
    if (drag) {
      if (drag.mode === 'pan') {
        const spacing = ts.barSpacing()
        if (spacing > 0) {
          const dBars = (x - drag.lastX) / spacing
          drag.lastX = x
          if (dBars !== 0) shiftView(-dBars)
        }
        // Manual mode: body-drag is 2D — also pan the price range vertically by
        // the drag's price delta. (Auto mode leaves the vertical to auto-fit.)
        if (priceScaleMode === 'manual' && manualScale !== null) {
          const dyPx = y - drag.lastY
          if (dyPx !== 0) {
            const mainPane = computeLayout().panes[0]
            const span = manualScale.max - manualScale.min
            // Convert pixel travel to a price delta; dragging DOWN moves the
            // viewport down (prices shift up), matching a grab-and-drag feel.
            const dPrice = (dyPx / Math.max(1, mainPane.height)) * span
            manualScale = { min: manualScale.min + dPrice, max: manualScale.max + dPrice }
          }
        }
        drag.lastY = y
      } else if (drag.mode === 'scale-axis') {
        // Dragging the price axis scales the range about the anchor price. Up =
        // smaller range (zoom in), down = larger range (zoom out), exponential
        // in the pixel delta. startMin/startMax keep the gesture stable.
        const dyPx = y - drag.startY
        const factor = Math.exp(dyPx / AXIS_SCALE_PX)
        const newMin = drag.anchorPrice - (drag.anchorPrice - drag.startMin) * factor
        const newMax = drag.anchorPrice + (drag.startMax - drag.anchorPrice) * factor
        // Guard against a degenerate / inverted range from extreme drags.
        if (newMax - newMin > 1e-12 && isFinite(newMin) && isFinite(newMax)) {
          manualScale = { min: newMin, max: newMax }
        }
      } else {
        const layout = computeLayout()
        const mainScale = computeMainScale(layout.panes[0])
        const conv = makeConverters(mainScale)
        if (drag.mode === 'freehand') {
          // Thin to >= FREEHAND_MIN_DIST_PX of screen travel, cap the point count.
          const dx = x - drag.lastPx
          const dy = y - drag.lastPy
          if (
            drag.drawing.points.length < FREEHAND_MAX_POINTS &&
            dx * dx + dy * dy >= FREEHAND_MIN_DIST_PX * FREEHAND_MIN_DIST_PX
          ) {
            drag.drawing.points.push({ time: conv.xToTime(x), price: conv.yToPrice(y) })
            drag.lastPx = x
            drag.lastPy = y
          }
        } else if (drag.mode === 'move-drawing') {
          // Whole-drawing translate never magnet-snaps.
          const t = conv.xToTime(x)
          const p = conv.yToPrice(y)
          replaceDrawing(drag.id, translateDrawing(drag.original, t - drag.startTime, p - drag.startPrice))
          drag.moved = true
        } else if (drag.mode === 'move-alert') {
          // Vertical drag: track the cursor's price (clamped to the main pane).
          // drawAlerts renders the grabbed line here; committed on pointerup.
          const cy = clamp(y, mainScale.top, mainScale.bottom)
          drag.price = mainScale.yToPrice(cy)
          drag.moved = true
          canvas.style.cursor = 'grabbing'
        } else {
          const snap = magnetSnap(x, y, conv)
          replaceDrawing(
            drag.id,
            movePoint(drag.original, drag.handleIndex, { time: snap.time, price: snap.price }, makeEnv()),
          )
          drag.moved = true
        }
      }
    } else {
      updateCursor(x, y)
    }
    invalidate()
  }

  function handlePointerUp(_x: number, _y: number, _ev: MouseEvent): void {
    if (drag) {
      if (drag.mode === 'freehand') {
        // A click without any drag travel leaves a single point — an invisible
        // sliver that could never be hit-tested again. Discard it and keep the
        // brush armed so the user can simply try again.
        if (drag.drawing.points.length >= 2) commitDrawing(drag.drawing)
      } else if (drag.mode === 'move-alert') {
        // Hand the new price to the host (which re-runs setAlerts). The local
        // preview already moved the line; a no-travel click is a no-op.
        if (drag.moved) options.onAlertMove?.(drag.id, drag.price)
      } else if ((drag.mode === 'move-drawing' || drag.mode === 'move-handle') && drag.moved) {
        emitDrawings()
        emitSelectionCurrent() // same object reference that onDrawingsChange just saw
      }
      // 'pan' and 'scale-axis' need no commit step — their effects (view / manual
      // scale) are applied live during the drag.
    }
    drag = null
    if (hover) updateCursor(hover.x, hover.y)
    invalidate()
  }

  function handlePointerLeave(): void {
    hover = null
    invalidate()
  }

  function handleWheel(x: number, _y: number, ev: WheelEvent): void {
    const layout = computeLayout()
    if (layout.plotWidth <= 0) return
    // Trackpad 2-finger horizontal swipe (deltaX dominant, not a pinch) pans
    // through time instead of zooming. Pinch (ctrlKey) and vertical wheel zoom.
    if (Math.abs(ev.deltaX) > Math.abs(ev.deltaY) && !ev.ctrlKey) {
      const barsPerPx = ts.range / layout.plotWidth
      const shift = ev.deltaX * barsPerPx
      ts.view = { start: ts.view.start + shift, end: ts.view.end + shift }
      clampView()
      checkHistory()
      invalidate()
      return
    }
    const range = ts.range
    const factor = Math.exp(-ev.deltaY * 0.0012)
    const newRange = clamp(range / factor, MIN_VISIBLE_BARS, maxVisibleBars())
    if (newRange === range) return
    const cx = clamp(x, 0, layout.plotWidth)
    const anchor = ts.xToIndex(cx) // bar index under the cursor stays put
    const ratio = cx / layout.plotWidth
    const start = anchor - ratio * newRange
    const prev = ts.view
    ts.view = { start, end: start + newRange }
    keepReplayCursorVisible(prev)
    clampView()
    checkHistory()
    invalidate()
  }

  /** Two-finger pinch: zoom the time range around centerX by `scale` (>1 = in). */
  function handlePinch(centerX: number, scale: number): void {
    const layout = computeLayout()
    if (layout.plotWidth <= 0 || !(scale > 0)) return
    const range = ts.range
    const newRange = clamp(range / scale, MIN_VISIBLE_BARS, maxVisibleBars())
    if (newRange === range) return
    const cx = clamp(centerX, 0, layout.plotWidth)
    const anchor = ts.xToIndex(cx) // bar index under the pinch center stays put
    const ratio = cx / layout.plotWidth
    const start = anchor - ratio * newRange
    const prev = ts.view
    ts.view = { start, end: start + newRange }
    keepReplayCursorVisible(prev)
    clampView()
    checkHistory()
    invalidate()
  }

  function handleDoubleClick(x: number, y: number, _ev: MouseEvent): void {
    const layout = computeLayout()
    // Double-click on the price axis (strip or the "A" toggle) resets ONLY the
    // main price scale to auto-fit — the time view is left as-is. Double-click
    // on the chart body still resets the whole view (which also drops to auto).
    if (!activeTool && (inAxisToggle(x, y) || inMainAxisStrip(x, y, layout))) {
      exitManualScale()
      invalidate()
      return
    }
    resetViewInternal()
    invalidate()
  }

  /**
   * Right-click: suppress the native menu and hand the host the cursor's
   * (x, y) in container CSS px plus the main-pane price/time under it (for an
   * "add alert here" action). No-op without an onContextMenu handler — still
   * preventDefault so a stale browser menu never shows over the chart.
   */
  function handleContextMenu(x: number, y: number, ev: MouseEvent): void {
    ev.preventDefault()
    if (!options.onContextMenu) return
    const layout = computeLayout()
    const mainScale = computeMainScale(layout.panes[0])
    const price = mainScale.yToPrice(y)
    const time = ts.xToTime(x)
    options.onContextMenu({ x, y, price, time })
  }

  function handleKeyDown(ev: KeyboardEvent): void {
    if (isEditableTarget(ev.target)) return
    if (ev.key === 'Escape') {
      if (drag !== null && drag.mode === 'freehand') {
        drag = null // discard the partial freehand capture
        cancelTool()
      } else if (activeTool !== null || pendingPoints.length > 0) {
        cancelTool() // discard partial placement
      } else if (selectedId) {
        setSelection(null)
        invalidate()
      }
    } else if ((ev.key === 'Delete' || ev.key === 'Backspace') && selectedId) {
      drawings = drawings.filter((d) => d.id !== selectedId)
      setSelection(null)
      emitDrawings()
      invalidate()
      ev.preventDefault()
    }
  }

  const disposeInteractions = attachInteractions(canvas, {
    pointerDown: handlePointerDown,
    pointerMove: handlePointerMove,
    pointerUp: handlePointerUp,
    pointerLeave: handlePointerLeave,
    wheel: handleWheel,
    pinch: handlePinch,
    doubleClick: handleDoubleClick,
    contextMenu: handleContextMenu,
    keyDown: handleKeyDown,
  })

  const resizeObserver = new ResizeObserver(() => {
    applySize()
    invalidate()
  })
  resizeObserver.observe(container)

  // ----- formatting helpers ------------------------------------------------
  function formatIndicatorValue(v: number): string {
    const decimals = Math.abs(v) >= 1 ? 2 : 4
    return v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  function paneTickLabels(scale: PriceScale, ticks: number[]): { y: number; label: string }[] {
    const step = ticks.length >= 2 ? ticks[1] - ticks[0] : niceStep((scale.max - scale.min) / 8 || 1)
    const dec = decimalsForStep(step)
    return ticks.map((v) => ({
      y: Math.round(scale.priceToY(v)),
      label: v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }),
    }))
  }

  function formatPaneCrosshairValue(v: number, scale: PriceScale): string {
    const dec = decimalsForStep(niceStep((scale.max - scale.min) / 8 || 1))
    return v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec })
  }

  // ----- rendering -----------------------------------------------------------
  function clipPane(pane: PaneLayout, layout: Layout): void {
    ctx.beginPath()
    ctx.rect(0, pane.top, layout.plotWidth, pane.height)
    ctx.clip()
  }

  function drawSeriesByType(scale: PriceScale, colors: ChartColors, from: number, to: number): void {
    // All series draw from `renderSeries` (heikin = remapped OHLC; renko/
    // linebreak = synthetic blocks; kagi via kagiPoints). For the original 4
    // types renderSeries === candles, so output is byte-for-byte unchanged.
    const s = renderSeries
    switch (chartType) {
      case 'candles':
        R.drawCandles(ctx, s, from, to, ts, scale, colors)
        break
      case 'volcandles':
        R.drawVolumeCandles(ctx, s, from, to, ts, scale, colors)
        break
      case 'hlcarea':
        R.drawHlcAreaSeries(ctx, s, from, to, ts, scale, colors)
        break
      case 'hollow':
        R.drawHollowCandles(ctx, s, from, to, ts, scale, colors)
        break
      case 'heikin':
        R.drawCandles(ctx, s, from, to, ts, scale, colors)
        break
      case 'bars':
        R.drawBars(ctx, s, from, to, ts, scale, colors)
        break
      case 'hlcbars':
        R.drawHlcBars(ctx, s, from, to, ts, scale, colors)
        break
      case 'line':
        R.drawLineSeries(ctx, s, from, to, ts, scale, colors)
        break
      case 'linemarkers':
        R.drawLineMarkers(ctx, s, from, to, ts, scale, colors)
        break
      case 'step':
        R.drawStepSeries(ctx, s, from, to, ts, scale, colors)
        break
      case 'area':
        R.drawAreaSeries(ctx, s, from, to, ts, scale, colors)
        break
      case 'baseline': {
        // Split at the first VISIBLE candle's close.
        const baseline = s[from].close
        R.drawBaselineSeries(ctx, s, from, to, ts, scale, colors, baseline)
        break
      }
      case 'columns':
        R.drawColumnsSeries(ctx, s, from, to, ts, scale, colors)
        break
      case 'highlow':
        R.drawHighLowSeries(ctx, s, from, to, ts, scale, colors)
        break
      case 'renko':
      case 'linebreak':
        R.drawBlockSeries(ctx, s, from, to, ts, scale, colors)
        break
      case 'range':
        // Range bars are full synthetic OHLC bars on the index axis.
        R.drawCandles(ctx, s, from, to, ts, scale, colors)
        break
      case 'pnf':
        R.drawPointAndFigure(ctx, s, from, to, ts, scale, colors, pnfBoxSize)
        break
      case 'kagi':
        if (kagiPoints) {
          // Each Kagi vertex maps 1:1 to a renderSeries bar, so during replay
          // `to` is the clipped last-visible index: draw only vertices [0..to]
          // (slicing is a no-op when replay is off, since to === len-1).
          const pts = to >= kagiPoints.length - 1 ? kagiPoints : kagiPoints.slice(0, to + 1)
          R.drawKagiSeries(ctx, pts, ts, scale, colors)
        }
        break
    }
  }

  function drawLastPrice(layout: Layout, mainScale: PriceScale, colors: ChartColors): void {
    // Track the series on screen (synthetic for re-binned types) so the
    // last-price line/tag matches what's drawn. During replay the "current"
    // bar is the one AT the cursor (effectiveLength()-1), so the line/tag show
    // the replay bar's close, not the hidden future's.
    const n = effectiveLength()
    if (n === 0) return
    const last = renderSeries[n - 1]
    const prevClose = n > 1 ? renderSeries[n - 2].close : last.open
    const color = last.close >= prevClose ? upColor(colors) : downColor(colors)
    const y = mainScale.priceToY(last.close)
    if (y >= mainScale.top && y <= mainScale.bottom) {
      R.drawLastPriceLine(ctx, color, Math.round(y) + 0.5, layout.plotWidth)
    }
    const tagY = clamp(y, mainScale.top + 9, mainScale.bottom - 9)
    R.drawPriceTag(
      ctx,
      formatPrice(last.close, precision),
      tagY,
      layout.plotWidth,
      layout.width - layout.plotWidth,
      color,
      '#ffffff',
    )

    // Countdown to the live candle's close, just under the price tag. Only for
    // real-time, time-based charts: re-binned types aren't time-aligned, and
    // during replay the "current" bar is historical (no live close).
    if (replayCursor === null && !isRebinnedChartType(chartType) && candles.length > 0 && ts.intervalMs > 0) {
      const remaining = candles[candles.length - 1].time + ts.intervalMs - Date.now()
      if (remaining > 0 && remaining <= ts.intervalMs + 60_000) {
        let cdY = tagY + 9 + 8 // below the 18px price tag
        if (cdY + 8 > mainScale.bottom) cdY = tagY - 9 - 8 // flip above near the pane floor
        R.drawCloseCountdown(
          ctx,
          formatCountdown(remaining),
          cdY,
          layout.plotWidth,
          layout.width - layout.plotWidth,
          colors,
        )
      }
    }
  }

  /**
   * Draw the current-symbol price alerts on the main pane and rebuild the
   * tag-rect table used for click hit-testing. Lines spanning the plot width;
   * bell + price tag near the right axis. Triggered alerts render muted.
   */
  function drawAlerts(layout: Layout, mainScale: PriceScale, colors: ChartColors): void {
    alertTagRects = []
    if (alerts.length === 0) return
    const axisWidth = layout.width - layout.plotWidth
    const dragAlert = drag !== null && drag.mode === 'move-alert' ? drag : null
    for (const alert of alerts) {
      // While dragging, render the grabbed alert at the live cursor price
      // without mutating the host-owned alert object.
      const price = dragAlert !== null && dragAlert.id === alert.id ? dragAlert.price : alert.price
      const y = mainScale.priceToY(price)
      // Clamp the tag (and thus the bell/click target) inside the main pane so
      // off-screen alerts still expose an affordance at the pane edge.
      const tagY = clamp(y, mainScale.top + 9, mainScale.bottom - 9)
      const color = alert.condition === 'above' ? upColor(colors) : downColor(colors)
      // Only draw the dashed line when it falls inside the main pane.
      const lineVisible = y >= mainScale.top && y <= mainScale.bottom
      const rect = R.drawAlertLine(
        ctx,
        color,
        alert.triggered,
        formatPrice(price, precision),
        y,
        tagY,
        lineVisible,
        layout.plotWidth,
        axisWidth,
      )
      alertTagRects.push({ id: alert.id, x: rect.x, y: rect.y, width: rect.width, height: rect.height })
    }
  }

  function drawLegends(layout: Layout, colors: ChartColors, hoverIdx: number | null): void {
    // Legend reflects the rendered series (synthetic for re-binned types).
    // During replay the resting (non-hover) row shows the bar AT the cursor,
    // and the hovered index is pre-clamped to [0..effectiveLength()-1] by the
    // caller, so indicator values never read into the hidden future.
    const n = effectiveLength()
    if (n === 0) return
    const i = hoverIdx ?? n - 1
    const c = renderSeries[i]
    const x0 = 10
    const lineH = 16
    let y = layout.panes[0].top + 12
    const dirColor = c.close >= c.open ? upColor(colors) : downColor(colors)
    const prevClose = i > 0 ? renderSeries[i - 1].close : c.open
    const chg = prevClose !== 0 ? ((c.close - prevClose) / prevClose) * 100 : 0
    const chgColor = chg >= 0 ? upColor(colors) : downColor(colors)
    const fp = (v: number): string => formatPrice(v, precision)
    R.drawLegendLine(
      ctx,
      [
        { text: 'O', color: colors.mutedText },
        { text: fp(c.open), color: dirColor },
        { text: 'H', color: colors.mutedText },
        { text: fp(c.high), color: dirColor },
        { text: 'L', color: colors.mutedText },
        { text: fp(c.low), color: dirColor },
        { text: 'C', color: colors.mutedText },
        { text: fp(c.close), color: dirColor },
        { text: `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`, color: chgColor },
        { text: 'Vol', color: colors.mutedText },
        { text: formatCompact(c.volume), color: dirColor },
      ],
      x0,
      y,
    )
    y += lineH
    // Re-binned series (renko/kagi/linebreak) don't align bar-for-bar with the
    // candle-indexed indicators, so their legend values would be meaningless —
    // skip them (matching the skipped plots). The hovered `i` here is a
    // synthetic-bar index, not a candle index.
    if (!isRebinnedChartType(chartType)) {
      // Overlay indicators, listed under the OHLC row.
      for (const ind of indicators) {
        if (ind.placement !== 'overlay') continue
        const segs: R.LegendSegment[] = [{ text: ind.label, color: colors.mutedText }]
        for (const out of ind.outputs) {
          const v = i < out.values.length ? out.values[i] : null
          segs.push({ text: v == null || !isFinite(v) ? '—' : fp(v), color: out.color })
        }
        R.drawLegendLine(ctx, segs, x0, y)
        y += lineH
      }
      // Pane indicators, each in its own pane's top-left corner.
      for (let pi = 1; pi < layout.panes.length; pi++) {
        const pane = layout.panes[pi]
        const ind = pane.indicator as IndicatorRenderData
        const segs: R.LegendSegment[] = [{ text: ind.label, color: colors.mutedText }]
        for (const out of ind.outputs) {
          const v = i < out.values.length ? out.values[i] : null
          segs.push({ text: v == null || !isFinite(v) ? '—' : formatIndicatorValue(v), color: out.color })
        }
        R.drawLegendLine(ctx, segs, x0, pane.top + 12)
      }
    }
  }

  function drawCrosshair(layout: Layout, scales: PriceScale[], colors: ChartColors): void {
    if (!hover) return
    const { x, y } = hover
    if (x < 0 || x > layout.plotWidth || y < 0 || y >= layout.timeAxisTop) return
    const idx = Math.floor(ts.xToIndex(x))
    const snappedX = Math.round(ts.centerX(idx)) + 0.5
    R.drawCrosshairVertical(ctx, colors, snappedX, layout.timeAxisTop)
    if (ts.count > 0) {
      R.drawTimeTag(
        ctx,
        colors,
        formatFullTime(ts.indexToTime(idx), ts.intervalMs),
        Math.round(ts.centerX(idx)),
        layout.plotWidth,
        layout.timeAxisTop,
        TIME_AXIS_H,
      )
    }
    const pi = paneIndexAt(y, layout)
    if (pi >= 0 && pi < scales.length) {
      R.drawCrosshairHorizontal(ctx, colors, Math.round(y) + 0.5, layout.plotWidth)
      const scale = scales[pi]
      const price = scale.yToPrice(y)
      const label = pi === 0 ? formatPrice(price, precision) : formatPaneCrosshairValue(price, scale)
      R.drawPriceTag(
        ctx,
        label,
        y,
        layout.plotWidth,
        layout.width - layout.plotWidth,
        colors.crosshairTagBg,
        colors.crosshairTagText,
      )
    }
  }

  function render(): void {
    if (destroyed) return
    if ((window.devicePixelRatio || 1) !== currentDpr) applySize()
    if (size.width <= 0 || size.height <= 0) return
    const colors = THEMES[theme]
    // Effective palette: settings' up/down/accent override the theme's (series,
    // volume, magnet ring). Base bg/text/grid/axis colors stay theme-governed.
    const eColors = effectiveColors(colors)
    const showGrid = gridVisible()
    const layout = computeLayout()
    ctx.save()
    ctx.font = FONT
    ctx.fillStyle = colors.bg
    ctx.fillRect(0, 0, layout.width, layout.height)

    const timeTicks = computeTimeTicks(ts)
    if (showGrid) R.drawVerticalGrid(ctx, colors, timeTicks, layout.timeAxisTop)

    const { from, to } = ts.visibleRange()
    // Replay-clipped upper draw index: bars after the cursor are the hidden
    // "future", so every series-derived layer (volume, the drawn series, all
    // indicator plots, projections' anchor) iterates [from..drawTo] instead of
    // [from..to]. With replay OFF, effectiveLength() === renderSeries.length so
    // drawTo === to and the render is byte-identical to before. `from` and the
    // time ticks are untouched, so the x-axis never resizes at the cursor.
    const drawTo = Math.min(to, effectiveLength() - 1)
    const hasData = effectiveLength() > 0 && from <= drawTo
    // Re-binned types (renko/kagi/linebreak) draw a synthetic series on the
    // index axis; volume + indicators (computed on the original candles) no
    // longer align, so they're suppressed to avoid meaningless / garbled plots.
    const rebinned = isRebinnedChartType(chartType)
    const mainPane = layout.panes[0]
    const mainScale = computeMainScale(mainPane)
    const scales: PriceScale[] = [mainScale]

    // --- main pane ---
    const mainTicks = mainScale.ticks(Math.pow(10, -precision))
    if (showGrid) R.drawHorizontalGrid(ctx, colors, layout.plotWidth, mainScale, mainTicks)
    if (hasData && mainPane.height > 0 && layout.plotWidth > 0) {
      ctx.save()
      clipPane(mainPane, layout)
      // Volume is no longer drawn built-in on the main pane (it's now an opt-in
      // 'volume' indicator rendered in its own sub-pane via the normal pipeline),
      // so the main pane is full-height price. R.drawVolume remains exported for
      // that indicator's histogram to reuse.
      drawSeriesByType(mainScale, eColors, from, drawTo)
      if (!rebinned) {
        for (const ind of indicators) {
          if (ind.placement !== 'overlay') continue
          for (const out of ind.outputs) {
            R.drawIndicatorOutput(ctx, out, from, drawTo, ts, mainScale)
          }
        }
      }
      // Ghost projections: above candles/overlays, beneath drawings/crosshair.
      // Anchored at the last VISIBLE bar so during replay they sprout from the
      // cursor bar, not the hidden future's last bar.
      if (projLines.length > 0 || projBand !== null) {
        R.drawProjections(ctx, projLines, projBand, effectiveLength() - 1, ts, mainScale)
      }
      ctx.restore()
    }

    // --- indicator sub-panes ---
    for (let pi = 1; pi < layout.panes.length; pi++) {
      const pane = layout.panes[pi]
      const scale = computePaneScale(pane)
      scales.push(scale)
      const ticks = scale.ticks()
      if (showGrid) R.drawHorizontalGrid(ctx, colors, layout.plotWidth, scale, ticks)
      const ind = pane.indicator as IndicatorRenderData
      if (ind.range && ind.range[0] === 0 && ind.range[1] === 100) {
        R.drawGuideLines(ctx, colors, layout.plotWidth, scale, [30, 70])
      }
      // Pane indicator plots are also suppressed for re-binned types (they'd be
      // plotted against a synthetic x-axis they weren't computed on). The pane
      // chrome (grid/guides/separator) stays so the layout doesn't jump.
      if (!rebinned && pane.height > 0 && layout.plotWidth > 0) {
        ctx.save()
        clipPane(pane, layout)
        for (const out of ind.outputs) {
          R.drawIndicatorOutput(ctx, out, from, drawTo, ts, scale)
        }
        ctx.restore()
      }
      R.drawSeparator(ctx, colors, pane.top - SEPARATOR_H, layout.width)
    }

    // --- axes ---
    R.drawAxisLines(ctx, colors, layout.plotWidth, layout.timeAxisTop, layout.width, layout.height)
    R.drawPriceAxisLabels(
      ctx,
      colors,
      layout.plotWidth,
      mainTicks.map((v) => ({ y: Math.round(mainScale.priceToY(v)), label: formatPrice(v, precision) })),
    )
    for (let pi = 1; pi < layout.panes.length; pi++) {
      R.drawPriceAxisLabels(ctx, colors, layout.plotWidth, paneTickLabels(scales[pi], scales[pi].ticks()))
    }

    // --- price-scale auto/manual "A" toggle (top of the right price axis) ---
    // Drawn only when there is both an axis column and a main pane with height.
    const axisW = layout.width - layout.plotWidth
    if (axisW > AXIS_TOGGLE_SIZE + AXIS_TOGGLE_MARGIN && mainPane.height > AXIS_TOGGLE_SIZE) {
      const bx = layout.plotWidth + AXIS_TOGGLE_MARGIN + 1
      const by = mainPane.top + AXIS_TOGGLE_MARGIN
      R.drawAxisToggleButton(ctx, colors, bx, by, AXIS_TOGGLE_SIZE, priceScaleMode === 'auto')
      axisToggleRect = { x: bx, y: by, width: AXIS_TOGGLE_SIZE, height: AXIS_TOGGLE_SIZE }
      // Log-scale "L" toggle directly below "A" (filled when log is on), when the
      // main pane is tall enough for a second button.
      const ly = by + AXIS_TOGGLE_SIZE + 4
      if (mainPane.top + mainPane.height > ly + AXIS_TOGGLE_SIZE) {
        R.drawAxisToggleButton(ctx, colors, bx, ly, AXIS_TOGGLE_SIZE, priceScaleLog, 'L')
        logToggleRect = { x: bx, y: ly, width: AXIS_TOGGLE_SIZE, height: AXIS_TOGGLE_SIZE }
      } else {
        logToggleRect = null
      }
    } else {
      axisToggleRect = null
      logToggleRect = null
    }
    const timeLabels: { x: number; label: string }[] = []
    for (let i = 0; i < timeTicks.length; i++) {
      timeLabels.push({
        x: timeTicks[i].x,
        label: formatTimeTickLabel(timeTicks[i].time, i > 0 ? timeTicks[i - 1].time : null, ts.intervalMs),
      })
    }
    R.drawTimeAxisLabels(ctx, colors, timeLabels, layout.timeAxisTop + TIME_AXIS_H / 2 + 1)

    // --- last price ---
    if (hasData) drawLastPrice(layout, mainScale, colors)

    // --- price alerts (main pane; beneath drawings so drawings win clicks) ---
    drawAlerts(layout, mainScale, colors)

    // --- drawings (main pane only, clipped) ---
    if (mainPane.height > 0 && layout.plotWidth > 0) {
      const conv = makeConverters(mainScale)
      const env = makeEnv()
      ctx.save()
      clipPane(mainPane, layout)
      for (const d of drawings) {
        renderDrawing(ctx, d, conv, d.id === selectedId, env)
      }
      const preview = buildPreview(conv, mainPane)
      if (preview) renderDrawing(ctx, preview, conv, false, env)
      if (drag !== null && drag.mode === 'freehand') {
        renderDrawing(ctx, drag.drawing, conv, false, env)
      }
      // Magnet feedback: ring on the snapped candidate point while placing / handle-dragging.
      if (magnet && hover) {
        const placing = activeTool !== null && pointsNeeded(activeTool) >= 1
        const handleDragging = drag !== null && drag.mode === 'move-handle'
        const inMain =
          hover.x >= 0 &&
          hover.x <= layout.plotWidth &&
          hover.y >= mainPane.top &&
          hover.y < mainPane.top + mainPane.height
        if ((placing && inMain) || handleDragging) {
          const snap = magnetSnap(hover.x, hover.y, conv)
          if (snap.snapped) R.drawMagnetRing(ctx, hover.x, conv.priceToY(snap.price), eColors.accent)
        }
      }
      ctx.restore()
    }

    // --- crosshair + legend ---
    // Clamp the hovered legend index to the last VISIBLE bar so that, during
    // replay, hovering over the hidden future still reads the cursor bar's
    // values (and the legend never surfaces future OHLC / indicator values).
    const hoverIdx =
      hover && hasData && hover.x >= 0 && hover.x <= layout.plotWidth && hover.y < layout.timeAxisTop
        ? clamp(Math.floor(ts.xToIndex(hover.x)), 0, effectiveLength() - 1)
        : null
    if (crosshairVisible()) drawCrosshair(layout, scales, colors)
    drawLegends(layout, colors, hoverIdx)

    ctx.restore()
  }

  // ----- public API -----------------------------------------------------------
  const engine: IChartEngine = {
    setData(newCandles: Candle[]): void {
      // View stability is reasoned in RENDER-SERIES index space (what's on the
      // index axis), so re-binned types stay visually stable too: the synthetic
      // bar count, not the candle count, drives the shift. For the 1:1 types
      // renderSeries mirrors candles, so this matches the original behavior.
      const prevSeries = renderSeries
      const prevCount = prevSeries.length
      const prevView = { ...ts.view }
      candles = newCandles.slice()
      computeBarMs()
      rebuildSeries() // recompute transforms + point ts at the new series' times
      const newCount = renderSeries.length
      if (prevCount === 0 || newCount === 0) {
        resetViewInternal()
      } else {
        const sameLast = renderSeries[newCount - 1].time === prevSeries[prevCount - 1].time
        const shift = newCount - prevCount
        if (sameLast) {
          // Same series; history was prepended (or trimmed) at the front:
          // shift indices so the viewport stays visually stable.
          ts.view = { start: prevView.start + shift, end: prevView.end + shift }
        } else if (renderSeries[0].time === prevSeries[0].time) {
          // Same series with newer candles appended: keep the viewport.
          ts.view = prevView
        } else {
          // Different series (symbol/interval switch): start fresh.
          resetViewInternal()
        }
      }
      historyArmed = true // re-arm the onRequestHistory trigger
      clampReplayCursor() // re-pin into the (possibly resized) series bounds
      invalidate()
    },

    updateLast(candle: Candle): void {
      const n = candles.length
      if (n === 0) {
        engine.setData([candle])
        return
      }
      // Capture the right-edge-following state against the CURRENT render-series
      // index space BEFORE mutating candles (for 1:1 types renderSeries aliases
      // candles, so the mutation below would otherwise change this count).
      const prevSeriesCount = renderSeries.length
      const atRightEdge = ts.view.end >= prevSeriesCount - 0.5
      const last = candles[n - 1]
      if (candle.time === last.time) {
        candles[n - 1] = candle
      } else if (candle.time > last.time) {
        candles.push(candle)
      } else {
        return // out-of-order update; ignore
      }
      // Re-binned types: re-transform the whole loaded array (O(n)) since one
      // new candle can add, remove or leave the synthetic bar count unchanged.
      // For 1:1 types this is a cheap pass that just remaps OHLC (heikin) or
      // returns the same array. Auto-scroll keeps the right edge in view when
      // the series grew and the viewport was already following it — matching
      // the original append behavior for the 4 base types (grew === 1).
      rebuildSeries()
      const grew = renderSeries.length - prevSeriesCount
      if (atRightEdge && grew > 0) {
        ts.view = { start: ts.view.start + grew, end: ts.view.end + grew }
      }
      clampReplayCursor() // re-pin if a re-binned transform shrank the series
      invalidate()
    },

    setIndicators(list: IndicatorRenderData[]): void {
      indicators = list.slice()
      invalidate()
    },

    setChartType(type: ChartType): void {
      if (type === chartType) {
        invalidate()
        return
      }
      const prevCount = renderSeries.length
      const axisChanged = isRebinnedChartType(type) !== isRebinnedChartType(chartType)
      chartType = type
      rebuildSeries()
      // Refit the viewport when the index axis changes meaning: switching into
      // or out of a re-binned type (different bar count AND different x-axis
      // semantics), or any length change. The 1:1 types all share the candle
      // index axis and keep the same count, so their viewport is preserved.
      if (axisChanged || renderSeries.length !== prevCount) {
        resetViewInternal()
      } else {
        clampView()
      }
      invalidate()
    },

    setTheme(t: Theme): void {
      theme = t
      invalidate()
    },

    setPricePrecision(p: number): void {
      precision = p
      invalidate()
    },

    setActiveTool(tool: DrawingToolId | null): void {
      activeTool = tool
      pendingPoints = []
      if (drag !== null && drag.mode === 'freehand') drag = null // discard mid-stroke capture
      if (tool !== null) setSelection(null)
      invalidate()
    },

    setDrawings(ds: Drawing[]): void {
      drawings = ds.slice()
      if (selectedId && !drawings.some((d) => d.id === selectedId)) setSelection(null)
      invalidate()
    },

    updateDrawing(d: Drawing): void {
      const idx = drawings.findIndex((x) => x.id === d.id)
      if (idx < 0) return // unknown id: no-op
      drawings[idx] = d // selection (by id) is untouched, so it stays selected
      emitDrawings() // deliberately NOT onSelectionChange — the inspector is the caller
      invalidate()
    },

    setMagnet(on: boolean): void {
      magnet = on
      invalidate()
    },

    setAlerts(list: Alert[]): void {
      // If the host replaces the set mid-drag (e.g. its own poll), cancel any
      // in-progress alert drag whose target just disappeared so we don't keep a
      // dangling reference or fire onAlertMove for a gone alert.
      if (drag !== null && drag.mode === 'move-alert') {
        const draggedId = drag.id
        if (!list.some((a) => a.id === draggedId)) drag = null
      }
      alerts = list.slice()
      invalidate()
    },

    setSettings(next: ChartSettings): void {
      settings = { ...next }
      invalidate()
    },

    clearDrawings(): void {
      if (drawings.length === 0) return
      drawings = []
      setSelection(null)
      emitDrawings()
      invalidate()
    },

    resetView(): void {
      resetViewInternal()
      invalidate()
    },

    resize(): void {
      applySize()
      invalidate()
    },

    destroy(): void {
      if (destroyed) return
      destroyed = true
      clearInterval(countdownTimer)
      if (rafId !== 0) cancelAnimationFrame(rafId)
      rafId = 0
      disposeInteractions()
      resizeObserver.disconnect()
      canvas.remove()
    },

    setProjections(lines: ProjectionLine[], band?: ProjectionBand | null): void {
      projLines = lines.slice()
      projBand = band ?? null
      // If the viewport is following the right edge (same criterion as the
      // updateLast auto-scroll), expand the right-edge offset once so the
      // longest projection plus 3 bars of breathing room is on screen. Zoom
      // width is preserved; we never shrink an offset the user already has,
      // and panning away afterwards is respected (no re-expansion until the
      // next setProjections call).
      const n = ts.count
      if (projLines.length > 0 && n > 0 && ts.view.end >= n - 0.5) {
        let maxOffset = 0
        for (const line of projLines) {
          for (const p of line.points) if (p.barOffset > maxOffset) maxOffset = p.barOffset
        }
        if (projBand) {
          for (const p of projBand.upper) if (p.barOffset > maxOffset) maxOffset = p.barOffset
          for (const p of projBand.lower) if (p.barOffset > maxOffset) maxOffset = p.barOffset
        }
        const desiredEnd = n + maxOffset + 3
        if (ts.view.end < desiredEnd) {
          const range = ts.range
          ts.view = { start: desiredEnd - range, end: desiredEnd }
          clampView() // keep at least a couple of candles on screen when zoomed far in
        }
      }
      invalidate()
    },

    scrollToTime(time: number): void {
      // `ts` is keyed to the render series (synthetic for re-binned types), so
      // clamp to its length, not the candle count.
      const n = renderSeries.length
      if (n === 0) return
      // timeToIndex binary-searches the loaded range (and extrapolates outside
      // it); rounding + clamping yields the nearest (synthetic) bar index.
      const idx = clamp(Math.round(ts.timeToIndex(time)), 0, n - 1)
      const range = ts.range
      const center = idx + 0.5 // bar centers live at index + 0.5
      ts.view = { start: center - range / 2, end: center + range / 2 }
      clampView()
      checkHistory()
      invalidate()
    },

    setReplayCursor(index: number | null): void {
      if (index === null) {
        if (replayCursor === null) return // already off — no repaint needed
        replayCursor = null
        invalidate()
        return
      }
      const n = renderSeries.length
      // No series yet: arm at 0 once data arrives. clampReplayCursor() runs on
      // every setData/updateLast, so storing 0 here is re-clamped (or cleared)
      // when the series materializes; storing the raw value would risk an
      // out-of-range cursor until the next data change.
      const next = n === 0 ? 0 : clamp(Math.round(index), 0, n - 1)
      const entering = replayCursor === null
      if (!entering && next === replayCursor) return
      replayCursor = next
      // Bring the cursor into view: on entry, or when it walks off-screen
      // (during play / scrub). Pin it near the right edge, preserving zoom
      // width, so the revealed history sits on the left and the "now" bar is at
      // the right. Without this, entering replay leaves the viewport on the
      // (now-hidden) future bars and the chart looks empty.
      if (n > 0) {
        const width = ts.view.end - ts.view.start
        const margin = replayPinMargin(width)
        const visible = next >= ts.view.start && next <= ts.view.end - margin
        if (entering || !visible) {
          const end = next + 1 + margin
          ts.view = { start: end - width, end }
          clampView()
          checkHistory()
        }
      }
      invalidate()
    },

    setReplayPlaying(playing: boolean): void {
      // Only consulted by future zoom gestures — no repaint needed.
      replayPlaying = playing
    },

    getMainConverters(): Converters | null {
      if (size.width <= 0 || size.height <= 0) return null
      return liveConverters
    },

    getMainPaneRect(): { x: number; y: number; width: number; height: number } | null {
      if (size.width <= 0 || size.height <= 0) return null
      const pane = computeLayout().panes[0]
      return { x: 0, y: pane.top, width: ts.plotWidth, height: pane.height }
    },
  }

  // Initial sizing + first paint.
  applySize()
  rebuildSeries() // empty until setData, but keeps renderSeries/ts consistent
  resetViewInternal()
  invalidate()

  return engine
}
