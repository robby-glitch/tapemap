// Proof 3 for the /proto spike: a rotation pill anchored to its own candle.
// THROWAWAY.
//
// THE TEST is anchor stability, nothing else. The lane ledger from
// LevelsOverlay (pickLane/takeLane, 3 lanes a side) is deliberately NOT ported:
// it is pure Canvas2D collision math with zero engine coupling, so porting it
// would prove nothing about lightweight-charts. What has to hold is that the
// triangle stays welded to its candle and its σ level through pan, zoom,
// resize, theme toggle and setData.
//
// The level is READ OFF THE BAR (`bars[sig.i][sig.band]`), never recomputed —
// RotationSignal carries no numeric level, only the band name, and inventing
// one would be exactly the kind of drawn falsehood the project forbids.

import type {
  IChartApi,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  Logical,
  SeriesAttachedParameter,
  Time,
} from 'lightweight-charts'
import { type Mode, palette } from '../theme'
import type { RotationSignal, TapeBar } from '../data'

type DrawTarget = Parameters<IPrimitivePaneRenderer['draw']>[0]

const TRI = 5        // half-width of the triangle sitting ON the band
const STEM = 26      // band -> pill, in px
const PILL_H = 15
const PILL_PAD = 5
const FONT = '10px ui-monospace, SFMono-Regular, Menlo, monospace'

export interface RotationState {
  bars: TapeBar[]
  rotation: (RotationSignal | null)[] | null
  mode: Mode
}

export class RotationPrimitive implements ISeriesPrimitive<Time> {
  private chart: IChartApi | null = null
  private series: ISeriesApi<'Candlestick'> | null = null

  constructor(private readonly get: () => RotationState) {}

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

  private readonly view: IPrimitivePaneView = {
    zOrder: () => 'top',
    renderer: (): IPrimitivePaneRenderer => this.renderer,
  }

  private readonly renderer: IPrimitivePaneRenderer = {
    draw: (target: DrawTarget) => {
      const chart = this.chart
      const series = this.series
      if (!chart || !series) return
      const { bars, rotation, mode } = this.get()
      // A withheld rotation layer draws NOTHING. data.ts nulls the whole array
      // rather than let indices drift, and a pill one bar off would claim the
      // operator's setup fired on a minute it did not.
      if (!rotation || !bars.length) return

      const pal = palette(mode)
      const ts = chart.timeScale()

      target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
        ctx.font = FONT
        ctx.textBaseline = 'middle'

        for (let i = 0; i < rotation.length; i++) {
          const sig = rotation[i]
          if (!sig) continue
          // Guard a shrunken bar array (replay, an index switch mid-poll):
          // the signal survives its bar only in a race, and a stale index must
          // not read off the end.
          const bar = bars[sig.i]
          if (!bar) continue

          const level = bar[sig.band]
          if (!Number.isFinite(level)) continue

          const x = ts.logicalToCoordinate(sig.i as Logical)
          const bandY = series.priceToCoordinate(level)
          const buy = sig.side === 'BUY'
          const extremeY = series.priceToCoordinate(buy ? bar.l : bar.h)
          if (x == null || bandY == null || extremeY == null) continue
          if (x < -40 || x > mediaSize.width + 40) continue

          // Whichever is further OUT — the same rule as drawRotation
          // (LevelsOverlay.ts:721-733), so the pill never sits inside the wick.
          const anchorY = buy ? Math.max(bandY, extremeY) : Math.min(bandY, extremeY)
          const dir = buy ? 1 : -1 // screen-down for a buy
          const tone = buy ? pal.bull : pal.bear
          const label = `${buy ? '▲' : '▼'} ${sig.side} ${sig.band}`

          // The triangle sits ON the σ band — the only mark drawn at a σ level.
          ctx.fillStyle = tone
          ctx.beginPath()
          ctx.moveTo(x, bandY)
          ctx.lineTo(x - TRI, bandY + dir * TRI * 1.6)
          ctx.lineTo(x + TRI, bandY + dir * TRI * 1.6)
          ctx.closePath()
          ctx.fill()

          const w = ctx.measureText(label).width + PILL_PAD * 2
          let cy = anchorY + dir * (STEM + PILL_H / 2)
          // Clamp INTO the pane rather than drop the pill — a signal must not
          // vanish just because it fired near an edge.
          const half = PILL_H / 2
          cy = Math.min(mediaSize.height - half - 1, Math.max(half + 1, cy))

          ctx.strokeStyle = tone
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(x, bandY)
          ctx.lineTo(x, cy - dir * half)
          ctx.stroke()

          // Square corners, matching the Trade tab's pills.
          const px = Math.round(x - w / 2)
          const py = Math.round(cy - half)
          ctx.fillStyle = pal.bg
          ctx.fillRect(px, py, w, PILL_H)
          ctx.lineWidth = 1.5
          ctx.strokeRect(px + 0.5, py + 0.5, w - 1, PILL_H - 1)
          ctx.fillStyle = tone
          ctx.textAlign = 'center'
          ctx.fillText(label, px + w / 2, py + PILL_H / 2)
        }
      })
    },
  }
}
