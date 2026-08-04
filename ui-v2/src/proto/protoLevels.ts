// Horizontal levels (pivots, walls, PIN, STK, floor/cap …) for the /proto
// spike. THROWAWAY.
//
// FRAME — the one thing to get right here, because getting it wrong cost a
// whole day on 2026-08-04 (HANDOFF §6b). This file does NO frame arithmetic at
// all. It draws `MapLevel.value` verbatim, because data.ts has already decided
// each level's frame at the point it was built:
//
//   - floor pivots (R3..S3) come from `day.pivots`, computed server-side off
//     the FUTURES bars, and are added WITHOUT toTape (data.ts:920-921)
//   - chain-derived levels (PIN, STK, MAX PAIN, GEX FLIP, walls) get
//     `toTape(v) = v + basis` at build time (data.ts:655-658, 763-764, 919-927)
//
// So the array handed in is uniformly futures-frame and is the SAME array
// ContractChart/LevelsOverlay already draws. Adding a `+ basis` here would
// double-count it. If a level's frame is ever unknown, data.ts drops it —
// this file never has to decide.

import type {
  IChartApi,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
} from 'lightweight-charts'
import { type Mode, palette } from '../theme'
import type { MapLevel } from '../data'

type DrawTarget = Parameters<IPrimitivePaneRenderer['draw']>[0]

/** Minimum vertical gap between two drawn LABELS, for a 10px font — the same
 *  11px LevelsOverlay uses. A label suppressed by collision still gets its
 *  LINE drawn: the level is real, only its name had nowhere to go. */
const LABEL_GAP = 11
const FONT = '10px ui-monospace, SFMono-Regular, Menlo, monospace'

export interface LevelsState {
  levels: MapLevel[]
  mode: Mode
}

/** Drawn by the series themselves, so skipped here rather than doubled. */
const SKIP: ReadonlySet<string> = new Set(['now', 'vwap', 'band'])

export class LevelsPrimitive implements ISeriesPrimitive<Time> {
  private chart: IChartApi | null = null
  private series: ISeriesApi<'Candlestick'> | null = null

  constructor(private readonly get: () => LevelsState) {}

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
    // Over the σ wash, under the rotation pills — the same stacking
    // LevelsOverlay uses, so a level never hides a signal.
    zOrder: () => 'normal',
    renderer: (): IPrimitivePaneRenderer => this.renderer,
  }

  private readonly renderer: IPrimitivePaneRenderer = {
    draw: (target: DrawTarget) => {
      const series = this.series
      if (!series) return
      const { levels, mode } = this.get()
      if (!levels.length) return
      const pal = palette(mode)

      target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
        ctx.font = FONT
        ctx.textBaseline = 'middle'
        ctx.textAlign = 'left'

        // Resolve to pixels first, then sort by y — label de-collision needs
        // screen order, which is not price order once the scale is inverted.
        const drawn: { y: number; l: MapLevel }[] = []
        for (const l of levels) {
          if (SKIP.has(l.kind)) continue
          if (!Number.isFinite(l.value)) continue
          const y = series.priceToCoordinate(l.value)
          if (y == null || y < 0 || y > mediaSize.height) continue
          drawn.push({ y, l })
        }
        drawn.sort((a, b) => a.y - b.y)

        let lastLabelY = -Infinity
        for (const { y, l } of drawn) {
          // One meaning per colour, matching theme.ts: brass is STRUCTURE.
          const tone = l.kind === 'pivot' ? pal.accent
            : l.kind === 'strike' ? pal.strike
            : l.kind === 'pin' ? pal.caution
            : pal.textSecondary

          ctx.strokeStyle = tone
          ctx.lineWidth = 1
          ctx.setLineDash(l.kind === 'pivot' ? [4, 3] : [2, 3])
          ctx.beginPath()
          ctx.moveTo(0, Math.round(y) + 0.5)
          ctx.lineTo(mediaSize.width, Math.round(y) + 0.5)
          ctx.stroke()
          ctx.setLineDash([])

          // The LINE is unconditional; only the label yields to collision, so
          // a crowded area loses names but never loses levels.
          if (y - lastLabelY < LABEL_GAP) continue
          lastLabelY = y
          const text = l.label
          const w = ctx.measureText(text).width
          ctx.fillStyle = pal.bg
          ctx.fillRect(2, y - 6, w + 6, 12)
          ctx.fillStyle = tone
          ctx.fillText(text, 5, y)
        }
      })
    },
  }
}
