// Proof 1 for the /proto spike: the σ envelope as a lightweight-charts series
// primitive. THROWAWAY.
//
// THE TEST. `drawRibbon` below is copied byte-for-byte out of
// LevelsOverlay.ts:227-271. The ONLY permitted difference is the TYPE of its
// `conv` parameter — the vendored `Converters` import becomes a local
// structural type. If the body ever needs editing, Proof 1 has failed: it would
// mean the drawing code was coupled to candl after all, and the rubric says
// keep candl.
//
// The constants below are likewise verbatim (LevelsOverlay.ts:48-56). They are
// EYEBALLED from the operator's own Kite band legend, so a hex may be off by a
// shade — LevelsOverlay is the place to correct it, not here.

import type {
  AutoscaleInfo,
  IChartApi,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  Logical,
  SeriesAttachedParameter,
  Time,
} from 'lightweight-charts'
import type { Mode } from '../theme'
import type { TapeBar } from '../data'

/** Structurally identical to candl's `Converters` as far as drawRibbon is
 *  concerned — it only ever calls these two of the four. Declaring it locally,
 *  and having the copied body still compile against it, is precisely what
 *  proves the drawing code was never candl-coupled. */
type Conv = { timeToX(t: number): number; priceToY(p: number): number }

/** A band key on `TapeBar` — any of the six σ deviations. Both edges of a
 *  ribbon take the same union so an ANNULUS (e.g. `u3`→`u2`, or `d1`→`d2`) is
 *  expressible, not only a symmetric ±nσ pair. */
type BandKey = 'u1' | 'u2' | 'u3' | 'd1' | 'd2' | 'd3'

const BAND_RGB = {
  core: '139,26,26',   // ±1σ  — Kite's dark red
  mid: '143,188,143',  // 1→2σ — Kite's sage green
  outer: '0,168,232',  // 2→3σ — Kite's azure
} as const
const BAND_FILL_ALPHA: Record<Mode, number> = { light: 0.10, dark: 0.13 }
const BAND_EDGE_ALPHA: Record<Mode, number> = { light: 0.55, dark: 0.45 }

/* ─── VERBATIM FROM LevelsOverlay.ts:227-271 — DO NOT EDIT THE BODY ─────────
   Only the `conv` parameter's type differs (Converters -> Conv). Any other
   change here invalidates Proof 1. */

/** One σ ribbon: a filled polygon between the `uKey`/`dKey` per-bar values
 *  across bars `[0, lastIdx]`, optionally with its two edges stroked. Walks the
 *  upper edge left→right then the lower edge right→left and closes — one path
 *  per CONTIGUOUS run of finite values, so a non-finite bar (the payload can
 *  carry nulls) ends the current run and starts a new one rather than being
 *  bridged over: a hole stays a hole. */
function drawRibbon(
  ctx: CanvasRenderingContext2D,
  conv: Conv,
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

/* ─── END VERBATIM ────────────────────────────────────────────────────────── */

/** The draw target's type, inferred rather than imported. It is
 *  `CanvasRenderingTarget2D` from `fancy-canvas`, which lightweight-charts
 *  depends on but does NOT re-export, and which pnpm does not hoist — so a
 *  direct import would not resolve. Inferring costs nothing and keeps a
 *  throwaway from adding a dependency. */
type DrawTarget = Parameters<IPrimitivePaneRenderer['draw']>[0]

export interface RibbonState {
  bars: TapeBar[]
  mode: Mode
}

export class RibbonPrimitive implements ISeriesPrimitive<Time> {
  private chart: IChartApi | null = null
  private series: ISeriesApi<'Candlestick'> | null = null
  /** Bar INDICES, not timestamps — see the adapter note in `draw`. Cached
   *  because it is handed to drawRibbon on every frame. */
  private idx: number[] = []

  constructor(private readonly get: () => RibbonState) {}

  attached(p: SeriesAttachedParameter<Time>): void {
    this.chart = p.chart
    this.series = p.series as ISeriesApi<'Candlestick'>
  }

  detached(): void {
    this.chart = null
    this.series = null
  }

  updateAllViews(): void {}

  paneViews(): readonly IPrimitivePaneView[] {
    return [this.view]
  }

  /** Without this the price scale knows only about the candles, so the moment
   *  price rides ±3σ the outer edge is clipped off the pane — precisely on the
   *  bars the operator's setup fires on. Verified present in v5.2.0's typings
   *  before any of this was written (it was the plan's risk R1). */
  autoscaleInfo(start: Logical, end: Logical): AutoscaleInfo | null {
    const { bars } = this.get()
    if (!bars.length) return null
    const lo = Math.max(0, Math.floor(start))
    const hi = Math.min(bars.length - 1, Math.ceil(end))
    let min = Infinity
    let max = -Infinity
    for (let i = lo; i <= hi; i++) {
      const b = bars[i]
      if (!b) continue
      if (Number.isFinite(b.d3) && b.d3 < min) min = b.d3
      if (Number.isFinite(b.u3) && b.u3 > max) max = b.u3
    }
    // No finite σ in view is a real absence, not a zero range — say nothing
    // rather than pin the scale to garbage.
    if (!Number.isFinite(min) || !Number.isFinite(max)) return null
    return { priceRange: { minValue: min, maxValue: max } }
  }

  private readonly view: IPrimitivePaneView = {
    // Under the candles. candl's overlay canvas is a sibling ABOVE the chart,
    // so its wash tints the candle bodies; this reads cleaner. One word to
    // change if the operator prefers candl's look.
    zOrder: () => 'bottom',
    renderer: (): IPrimitivePaneRenderer => this.renderer,
  }

  private readonly renderer: IPrimitivePaneRenderer = {
    draw: (target: DrawTarget) => {
      const chart = this.chart
      const series = this.series
      if (!chart || !series) return
      const { bars, mode } = this.get()
      const lastIdx = bars.length - 1
      if (lastIdx < 0) return
      if (this.idx.length !== bars.length) this.idx = bars.map((_, i) => i)

      // Media space = CSS pixels, 1 unit = 1 px — the exact space
      // LevelsOverlay already draws in, which is why the copied body needs no
      // scaling changes.
      target.useMediaCoordinateSpace(({ context: ctx }) => {
        const ts = chart.timeScale()
        // THE ADAPTER — the only new code the ribbon needs. `logicalToCoordinate`
        // rather than `timeToCoordinate` on purpose: the latter returns null for
        // bars scrolled outside the visible range, and drawRibbon treats a
        // non-finite value as a RUN BREAK, so the envelope would fragment under
        // pan. logicalToCoordinate is a pure affine map over bar index and never
        // returns null. The adapter changed; the drawing code did not.
        const conv: Conv = {
          timeToX: (i) => ts.logicalToCoordinate(i as Logical) ?? NaN,
          priceToY: (p) => series.priceToCoordinate(p) ?? NaN,
        }
        // Not laid out yet — draw nothing rather than guess, the same bargain
        // LevelsOverlay makes when the engine has no converters.
        if (!Number.isFinite(conv.priceToY(bars[lastIdx].c))) return

        const fa = BAND_FILL_ALPHA[mode]
        const ea = BAND_EDGE_ALPHA[mode]
        const ring = (u: BandKey, d: BandKey, rgb: string) => drawRibbon(
          ctx, conv, bars, this.idx, lastIdx, u, d,
          `rgba(${rgb},${fa})`, `rgba(${rgb},${ea})`,
        )
        // Verbatim from LevelsOverlay.ts:1169-1173.
        ring('u3', 'u2', BAND_RGB.outer)
        ring('d2', 'd3', BAND_RGB.outer)
        ring('u2', 'u1', BAND_RGB.mid)
        ring('d1', 'd2', BAND_RGB.mid)
        ring('u1', 'd1', BAND_RGB.core)
      })
    },
  }
}
