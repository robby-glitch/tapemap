// The lightweight-charts chart for the /proto spike. THROWAWAY.
//
// Step 2 scope, deliberately narrow: candles + VWAP + a correct time axis, and
// nothing else. The OI pane (Proof 2), the σ envelope (Proof 1) and the
// rotation pill (Proof 3) each land in their own step so a failure can be
// attributed to one thing.
//
// Nothing here may be trusted until the header's ISO stamp matches the
// payload's own clock — see protoTime.ts for why that is the whole ballgame.

import { useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  LineSeries,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
  type WhitespaceData,
} from 'lightweight-charts'
import { CHART_DOWN, CHART_UP, type Mode, palette, rgbOf } from '../theme'
import { LevelsPrimitive } from './protoLevels'
import { RibbonPrimitive } from './protoRibbon'
import { RotationPrimitive } from './protoRotation'
import type { MapLevel, RotationSignal, TapeBar } from '../data'

/** The chart's own box. ContractChart's root is height:100% and collapses to
 *  zero inside an auto-height flex parent (TradeTab.tsx:519-528, two bad edits
 *  paid for that). The spike sidesteps the whole trap with a definite pixel
 *  height, the same way LegChart does. */
export const PROTO_H = 560

interface Props {
  bars: TapeBar[]
  /** Epoch SECONDS, 1:1 with `bars`, already IST-as-UTC. Passed in rather than
   *  recomputed so the chart and the header can never disagree about what they
   *  are showing. */
  times: number[]
  /** Index-aligned 1:1 with `bars`, or null when the layer is withheld. Null
   *  draws no pills at all — never a partial or shifted set. */
  rotation: (RotationSignal | null)[] | null
  /** Pivots, walls, PIN, STK, floor/cap — the SAME array TradeTab hands
   *  ContractChart, so every value is already in the futures frame. See
   *  protoLevels.ts; nothing here adds basis. */
  levels: MapLevel[]
  mode: Mode
  /** Verification plumbing, not a feature. `i` is the bar index under the
   *  crosshair; `lwcTime` is the timestamp lightweight-charts itself holds for
   *  that point — the very value it formats onto the axis.
   *
   *  Both are needed, and neither alone is enough: `i` comes from
   *  param.logical, which is index-based and would look correct even if every
   *  stamp were in the wrong timezone, while `lwcTime` is the frame itself. */
  onHover?: (i: number | null, lwcTime: number | null) => void
}

export default function ProtoChart({ bars, times, rotation, levels, mode, onHover }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const vwapRef = useRef<ISeriesApi<'Line'> | null>(null)
  const oiRef = useRef<ISeriesApi<'Line'> | null>(null)
  // Mirrors of the latest props for callbacks that are registered once.
  const barsRef = useRef(bars)
  const hoverRef = useRef(onHover)
  barsRef.current = bars
  hoverRef.current = onHover
  // The primitives are constructed once and read this on every frame, so they
  // never hold a stale closure over props — the same getter pattern
  // startLevelsOverlay uses (LevelsOverlay.ts:895-918).
  const stateRef = useRef({ bars, rotation, levels, mode })
  stateRef.current = { bars, rotation, levels, mode }
  /** Last (session anchor, bar count) actually pushed. Reset on create because
   *  StrictMode mounts every effect twice in dev: without the reset the second
   *  mount takes the incremental path against a brand-new empty series and you
   *  get one candle instead of 385 — then blame the library. Same scar as
   *  ContractChart.tsx:130-135. */
  const prevRef = useRef({ base: -1, n: 0 })

  // ── create once ───────────────────────────────────────────────────────────
  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    const pal = palette(mode)
    const ink = rgbOf(pal.ink)
    const chart = createChart(host, {
      width: host.clientWidth,
      height: host.clientHeight,
      layout: {
        background: { color: pal.bg },
        textColor: pal.textSecondary,
        // Left at the library's default (shown). Hiding it is a LICENCE call —
        // lightweight-charts is Apache-2.0 *plus* a TradingView attribution
        // requirement — and that is the operator's to make, not this file's.
        // Keeping it visible also prices the decision honestly: this is the
        // chart real estate shipping it would cost.
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: `rgba(${ink},0.04)` },
        horzLines: { color: `rgba(${ink},0.04)` },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: pal.border,
        rightOffset: 3,
      },
      rightPriceScale: { borderColor: pal.border },
    })
    chartRef.current = chart
    prevRef.current = { base: -1, n: 0 }

    candleRef.current = chart.addSeries(CandlestickSeries, {
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      wickUpColor: CHART_UP[mode], wickDownColor: CHART_DOWN[mode],
      borderVisible: false,
      // NIFTY futures tick at 0.05. candl's bare pricePrecision:2 lets the axis
      // offer levels that cannot exist; minMove stops that.
      priceFormat: { type: 'price', precision: 2, minMove: 0.05 },
    })

    vwapRef.current = chart.addSeries(LineSeries, {
      color: '#FF1A1A', lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false,
      crosshairMarkerVisible: false,
    })

    // ── Proof 2: the OI pane. The whole thing is the trailing `1`. The pane
    //    does not exist until this call and is created by it; no layout code,
    //    no axis wiring, no crosshair bridging.
    oiRef.current = chart.addSeries(LineSeries, {
      color: '#7F8EA3', lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false,
      crosshairMarkerVisible: false,
    }, 1)
    // Height is asserted in the data effect, NOT here: at construction the
    // pane exists in the model but has not been laid out, and setHeight on a
    // zero-height pane silently does nothing (measured: panes() reported
    // [532, 0] with the OI series holding all 385 points).

    // ── Proofs 1 and 3, both series primitives on the candles. Order matters
    //    only for paint: the ribbon declares zOrder 'bottom' and the pills
    //    'top', so the wash sits under the candles and the signals over them.
    candleRef.current.attachPrimitive(new RibbonPrimitive(() => stateRef.current))
    candleRef.current.attachPrimitive(new LevelsPrimitive(() => stateRef.current))
    candleRef.current.attachPrimitive(new RotationPrimitive(() => stateRef.current))

    // Verification handle. THROWAWAY, like everything else here: the browser
    // pane this gets driven from does not always composite frames, and without
    // a handle the only way to check "did the OI pane get created" is to look
    // at pixels that were never painted. Asking the API is the honest check.
    ;(window as unknown as Record<string, unknown>).__proto = {
      chart, candle: candleRef.current, oi: oiRef.current,
    }

    // param.logical IS the bar index — no binary search, unlike candl which
    // hands back a time and makes ContractChart.tsx:52-66 hunt for the nearest
    // bar. Worth noting in the write-up: ~20 lines and an off-by-one class gone.
    chart.subscribeCrosshairMove((param) => {
      const cb = hoverRef.current
      if (!cb) return
      const l = param.logical
      cb(
        l != null && l >= 0 && l < barsRef.current.length ? Math.round(l) : null,
        typeof param.time === 'number' ? param.time : null,
      )
    })

    const ro = new ResizeObserver(() => {
      if (host.clientWidth > 0 && host.clientHeight > 0) {
        chart.resize(host.clientWidth, host.clientHeight)
      }
    })
    ro.observe(host)

    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
      candleRef.current = null
      vwapRef.current = null
    }
    // Created once. Theme changes are applied by the effect below rather than
    // by tearing the chart down, so a light/dark toggle never loses the zoom.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── data ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    const candle = candleRef.current
    const vwap = vwapRef.current
    const oi = oiRef.current
    if (!candle || !vwap || !oi) return
    const n = times.length
    if (n === 0) {
      candle.setData([])
      vwap.setData([])
      oi.setData([])
      prevRef.current = { base: -1, n: 0 }
      return
    }

    const cd: CandlestickData<UTCTimestamp>[] = bars.map((b, i) => ({
      time: times[i] as UTCTimestamp, open: b.o, high: b.h, low: b.l, close: b.c,
    }))
    // A non-finite VWAP becomes whitespace, never a bridged line — the same
    // rule indicators.ts's series() applies. A hole stays a hole.
    const vd: (LineData<UTCTimestamp> | WhitespaceData<UTCTimestamp>)[] = bars.map((b, i) =>
      Number.isFinite(b.vwap)
        ? { time: times[i] as UTCTimestamp, value: b.vwap }
        : { time: times[i] as UTCTimestamp })
    // bar.oi, NOT /api/oiflow — this is the series candl's own sub-pane plots
    // (indicators.ts:166-169), so the pane comparison stays like for like
    // instead of turning into a test of 15-minute resampling.
    const od: (LineData<UTCTimestamp> | WhitespaceData<UTCTimestamp>)[] = bars.map((b, i) =>
      Number.isFinite(b.oi)
        ? { time: times[i] as UTCTimestamp, value: b.oi }
        : { time: times[i] as UTCTimestamp })

    const prev = prevRef.current
    const same = prev.base === times[0]
    const grew = n - prev.n

    // The three-branch ladder from ContractChart.tsx:212-236, kept in shape on
    // purpose. The `else` is not a fallback for tidiness: LWC's update() THROWS
    // on a time older than the series' last point (candl's updateLast merely
    // shrugged), and every case that could produce that — first paint, a new
    // session, an index switch, bars shrinking — lands in it. Do not "simplify"
    // this into a single setData either: data.ts hands a fresh array identity
    // every 5s poll, and a blind setData would reset the operator's zoom on
    // every tick and make the library look broken.
    if (same && grew === 0) {
      candle.update(cd[n - 1]); vwap.update(vd[n - 1]); oi.update(od[n - 1])
    } else if (same && grew === 1 && n >= 2) {
      candle.update(cd[n - 2]); vwap.update(vd[n - 2]); oi.update(od[n - 2])
      candle.update(cd[n - 1]); vwap.update(vd[n - 1]); oi.update(od[n - 1])
    } else {
      candle.setData(cd); vwap.setData(vd); oi.setData(od)
      chartRef.current?.timeScale().fitContent()
    }
    // Assert the OI pane's height once it has data to be laid out around.
    // Re-checked rather than set blindly so a height the operator has dragged
    // themselves is not stamped back to 110 on every poll.
    const p1 = chartRef.current?.panes()[1]
    if (p1 && p1.getHeight() < 40) p1.setHeight(110)
    prevRef.current = { base: times[0], n }
  }, [bars, times])

  // ── theme ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    const chart = chartRef.current
    const candle = candleRef.current
    if (!chart || !candle) return
    const pal = palette(mode)
    const ink = rgbOf(pal.ink)
    chart.applyOptions({
      layout: { background: { color: pal.bg }, textColor: pal.textSecondary },
      grid: {
        vertLines: { color: `rgba(${ink},0.04)` },
        horzLines: { color: `rgba(${ink},0.04)` },
      },
      timeScale: { borderColor: pal.border },
      rightPriceScale: { borderColor: pal.border },
    })
    candle.applyOptions({
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      wickUpColor: CHART_UP[mode], wickDownColor: CHART_DOWN[mode],
    })
  }, [mode])

  return <div ref={hostRef} style={{ width: '100%', height: PROTO_H }} />
}
