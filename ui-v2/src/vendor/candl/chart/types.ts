import type { Candle, Theme } from '../core/types'
import type { IndicatorOutput, IndicatorPlacement } from '../indicators/types'
import type { Converters, Drawing, DrawingToolId } from '../drawings/types'
import type { Alert, ChartSettings } from '../alerts/types'

export type ChartType =
  | 'candles'
  | 'volcandles'
  | 'hollow'
  | 'heikin'
  | 'bars'
  | 'hlcbars'
  | 'hlcarea'
  | 'line'
  | 'linemarkers'
  | 'step'
  | 'area'
  | 'baseline'
  | 'columns'
  | 'highlow'
  | 'renko'
  | 'kagi'
  | 'linebreak'
  | 'pnf'
  | 'range'

/**
 * Canonical list of every valid ChartType id. Single source of truth for
 * runtime validation (e.g. the cloud-sync defensive validator) so the allowed
 * set can never drift from the union above.
 */
export const CHART_TYPES: readonly ChartType[] = [
  'candles',
  'volcandles',
  'hollow',
  'heikin',
  'bars',
  'hlcbars',
  'hlcarea',
  'line',
  'linemarkers',
  'step',
  'area',
  'baseline',
  'columns',
  'highlow',
  'renko',
  'kagi',
  'linebreak',
  'pnf',
  'range',
]

/**
 * Chart types whose series is RE-BINNED off the time axis (Renko, Kagi, Line
 * Break). For these the engine renders a synthetic series on the bar-index
 * axis and — because overlay/pane indicators are computed on the ORIGINAL
 * candles and no longer align bar-for-bar — SKIPS drawing indicators and
 * volume. Crosshair, last-price and drawings still work on the synthetic axis.
 */
export const REBINNED_CHART_TYPES: ReadonlySet<ChartType> = new Set<ChartType>([
  'renko',
  'kagi',
  'linebreak',
  'pnf',
  'range',
])

export function isRebinnedChartType(type: ChartType): boolean {
  return REBINNED_CHART_TYPES.has(type)
}

/** One active indicator instance, fully computed, ready to render. */
export interface IndicatorRenderData {
  instanceId: string
  label: string // e.g. "RSI 14"
  placement: IndicatorPlacement
  outputs: IndicatorOutput[] // values aligned 1:1 with the candles passed to setData
  range?: [number, number] // fixed y-range for pane indicators
}

/**
 * A ghost polyline anchored at the LAST candle: each point is placed at
 * x = (last bar index + barOffset), so projections sprout rightward from "now"
 * into empty future space. Rendered only on the main price pane.
 */
export interface ProjectionLine {
  id: string
  color: string
  opacity: number // 0..1
  width: number
  dashed?: boolean
  points: { barOffset: number; price: number }[] // barOffset >= 0; 0 = at the last bar
}

/** A translucent fill between two future price paths (e.g. echo quartile band). */
export interface ProjectionBand {
  color: string
  opacity: number // fill opacity, 0..1
  upper: { barOffset: number; price: number }[]
  lower: { barOffset: number; price: number }[]
}

export interface ChartEngineOptions {
  theme: Theme
  pricePrecision: number
  chartType: ChartType
  /**
   * Fired (at most once per setData) when the user pans near the oldest
   * loaded candle — host should fetch older history and call setData with
   * the prepended array.
   */
  onRequestHistory?: () => void
  /** Fired whenever drawings are added / moved / deleted inside the engine. */
  onDrawingsChange?: (drawings: Drawing[]) => void
  /** Fired when the engine finishes/cancels a drawing tool (so UI can un-highlight it). */
  onActiveToolChange?: (tool: DrawingToolId | null) => void
  /** Fired when the selected drawing changes (select, deselect, delete, commit). */
  onSelectionChange?: (drawing: Drawing | null) => void
  /**
   * Right-click on the chart: the host shows a context menu at (x, y) — client
   * px relative to the container — with `price`/`time` at the cursor (for an
   * "add alert here" action). The engine has already called preventDefault.
   */
  onContextMenu?: (info: { x: number; y: number; price: number; time: number }) => void
  /** User clicked an alert line's delete/bell affordance — host removes the alert. */
  onAlertRemove?: (id: string) => void
  /** User dragged an alert line to a new price — host updates the alert. */
  onAlertMove?: (id: string, price: number) => void
}

/**
 * Public API of the canvas chart engine.
 * Created via `createChartEngine(container, options)` from src/chart/engine.ts.
 *
 * setData semantics: full replace. If the new array shares the previous
 * last-candle time but has extra candles prepended (history pagination),
 * the viewport must stay visually stable (shift indices by the prepend count).
 */
export interface IChartEngine {
  setData(candles: Candle[]): void
  /** Live update: replace last candle if same open time, else append. Auto-scrolls if viewport is at the right edge. */
  updateLast(candle: Candle): void
  setIndicators(indicators: IndicatorRenderData[]): void
  setChartType(type: ChartType): void
  setTheme(theme: Theme): void
  setPricePrecision(precision: number): void
  /** Arm a drawing tool (clicks then place its points), or null to disarm. */
  setActiveTool(tool: DrawingToolId | null): void
  /** Replace all drawings (e.g. restored from localStorage). Does NOT fire onDrawingsChange. */
  setDrawings(drawings: Drawing[]): void
  /**
   * Replace one drawing by id (inspector edits: color/width/text/props/points).
   * Keeps selection on it, repaints, fires onDrawingsChange (but not onSelectionChange).
   */
  updateDrawing(drawing: Drawing): void
  /** Magnet mode: placement clicks and handle drags snap to the nearest OHLC value when close. */
  setMagnet(on: boolean): void
  /**
   * Render price-alert lines on the main pane: a dashed horizontal line at each
   * alert price with a bell glyph + price tag near the right axis. Clicking the
   * bell fires onAlertRemove; dragging the line fires onAlertMove. Triggered
   * alerts render muted. Pass [] to clear. (Only alerts for the current symbol.)
   */
  setAlerts(alerts: Alert[]): void
  /** Apply appearance settings: candle up/down colors, grid + crosshair visibility. */
  setSettings(settings: ChartSettings): void
  clearDrawings(): void
  resetView(): void
  resize(): void
  destroy(): void
  /**
   * Render ghost paths sprouting rightward from the last candle (pass [] / null
   * to clear). If the viewport is following the right edge when called, the
   * right-edge offset expands once so the longest projection is visible.
   * Projections must survive setData/updateLast until explicitly cleared.
   */
  setProjections(lines: ProjectionLine[], band?: ProjectionBand | null): void
  /** Center the viewport on the candle nearest the given time (epoch ms). */
  scrollToTime(time: number): void
  /**
   * Replay mode: when `index` is a number the engine treats the visible data as
   * `renderSeries.slice(0, index + 1)` — every series-derived layer (drawn
   * series + re-binned blocks, volume histogram, overlay + pane indicator plots
   * and their legend values, the last-price line/tag, the price auto-fit and
   * the crosshair/legend) is clipped to bars `[0..index]`; bars after `index`
   * are the hidden "future". The time axis and bar-index positions are
   * untouched, so the chart never resizes horizontally — only data drawing is
   * cut off at the cursor. `index` is clamped to `[0, renderSeries.length - 1]`.
   * Pass `null` to leave replay (render everything as normal). setData/updateLast
   * remain safe during replay and re-clamp the cursor if the series shrank.
   */
  setReplayCursor(index: number | null): void
  /**
   * Whether replay playback is running. While true, zoom gestures keep the
   * replay cursor on screen (so the per-tick auto-scroll never snaps the view
   * away mid-gesture); while false (paused / replay off) zoom is purely
   * pointer-anchored. Rendering is unaffected.
   */
  setReplayPlaying(playing: boolean): void
  /**
   * Current main-pane coordinate converters (CSS px, time extrapolates past
   * the data edge), for overlays that draw in sync with the chart — e.g. the
   * Oracle storm canvas. Returns null before the first layout. The object is
   * a live view: results reflect the viewport at call time, so overlays
   * should re-query every animation frame rather than caching results.
   */
  getMainConverters(): Converters | null
  /** Geometry of the main price pane in CSS px (for clipping overlays). Null before first layout. */
  getMainPaneRect(): { x: number; y: number; width: number; height: number } | null
}
