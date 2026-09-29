import { useEffect, useMemo, useRef, useState } from 'react'
import { createChartEngine } from '../vendor/candl/chart/engine'
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { TapeBar, IndexKey } from '../data'
import type { Mode } from '../theme'
import { CHART_UP, CHART_DOWN } from '../theme'
import { toCandles, buildIndicators } from './indicators'
import { startLevelsOverlay } from './LevelsOverlay'
import type { EngineLayer, OverlayData, PocketBar, TradeLayer, ValueLayer, ZoneEntry } from './LevelsOverlay'
import type { FootEvent } from './footprint'
import type { TapeReply } from './tape'
import Callout from './Callout'

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  cursor: number | null // replay bar index; null = live
  mode: Mode
  hover: number | null
  onHover: (i: number | null) => void
  /** The interval the backend says these bars ARE (minutes), or null. */
  interval: number | null
  /** Her zone's bands, from the 3-minute machine's bars (whatever this chart's interval is). */
  pockets: PocketBar[] | null
  /** Her zone machine's entries, each on the chart bar containing its own time. */
  entries: ZoneEntry[]
  /** Her footprint marks (P / A / E / C). Null = the record could not be read; TradeTab says why. */
  marks: FootEvent[] | null
  /** The ladder record (`/api/tape`), for the Flow pane. Null = could not be read. */
  prints: TapeReply | null
  /** The Flow pane toggle (default on; it draws only at 5 and 15 minutes). */
  flowPane: boolean
  /** The engine's layers (fights, held, trapped, walls, NEXT FIGHT), on the chart's own clock. Null = no read. */
  engine: EngineLayer | null
  /** Her marked trade (entry, give-up, walls behind and ahead), on the chart's own clock. Null = none. */
  trade: TradeLayer | null
  /** Floor pivots (Pivots toggle on), else null. */
  pivots: { label: string; value: number }[] | null
  /** The Value layer (Value toggle on), else null. */
  value: ValueLayer | null
  /** The CHIPS toggle. */
  chipsOn: boolean
}

/** Nearest index in a sorted-ascending time array to `t` (binary search). */
function nearestIndex(times: number[], t: number): number {
  if (!times.length) return 0
  let lo = 0
  let hi = times.length - 1
  if (t <= times[0]) return 0
  if (t >= times[hi]) return hi
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (times[mid] === t) return mid
    if (times[mid] < t) lo = mid + 1
    else hi = mid
  }
  if (lo > 0 && Math.abs(times[lo - 1] - t) <= Math.abs(times[lo] - t)) return lo - 1
  return lo
}

export default function ContractChart({
  index, day, bars, cursor, mode, hover, onHover, interval, pockets, entries, marks, prints, flowPane, engine, trade, pivots, value, chipsOn,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const hostRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<IChartEngine | null>(null)
  const modeRef = useRef<Mode>(mode)
  modeRef.current = mode
  const prevRef = useRef<{ index: string; day: string; n: number }>({ index: '', day: '', n: 0 })
  // the candle time axis (epoch ms), rebuilt with the data effect below
  const timesRef = useRef<number[]>([])
  const barsRef = useRef<TapeBar[]>(bars)
  barsRef.current = bars
  const cursorRef = useRef<number | null>(cursor)
  cursorRef.current = cursor
  const onHoverRef = useRef(onHover)
  onHoverRef.current = onHover
  // One ref the rAF overlay reads every frame. `rev` moves whenever an input moves, so the overlay repaints on a
  // data change and otherwise stays idle.
  const revRef = useRef(0)
  const rev = useMemo(() => ++revRef.current, [bars, cursor, interval, pockets, entries, marks, engine, trade, pivots, value, chipsOn, hover])
  const dataRef = useRef<Omit<OverlayData, 'times'>>({ bars, cursor, interval, pockets, entries, marks, engine, trade, pivots, value, chipsOn, hover, rev })
  dataRef.current = { bars, cursor, interval, pockets, entries, marks, engine, trade, pivots, value, chipsOn, hover, rev }
  const internalHoverRef = useRef<number | null>(null)
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number; w: number; h: number } | null>(null)

  useEffect(() => {
    const host = hostRef.current!
    const engine = createChartEngine(host, { theme: mode, pricePrecision: 2, chartType: 'candles' })
    engineRef.current = engine
    // a new engine holds no series: the next data effect must take the setData path (StrictMode remounts)
    prevRef.current = { index: '', day: '', n: 0 }
    engine.setSettings({
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      gridVisible: true, crosshairVisible: true,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })
    // not redundant with the engine's own observer: without it the host's growth leaves a stale layout
    const ro = new ResizeObserver(() => engine.resize())
    ro.observe(host)
    const stopOverlay = startLevelsOverlay(
      overlayRef.current!, host, engine,
      () => modeRef.current,
      () => ({ ...dataRef.current, times: timesRef.current }),
    )
    const onMove = (e: MouseEvent) => {
      const eng = engineRef.current
      const container = containerRef.current
      const times = timesRef.current
      if (!eng || !container || !times.length) return
      const conv = eng.getMainConverters()
      if (!conv) return
      const rect = container.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      const maxIdx = barsRef.current.length - 1
      let idx = Math.max(0, Math.min(nearestIndex(times, conv.xToTime(x)), maxIdx))
      // causality: hovering never reveals a bar the replay cursor is hiding
      const cur = cursorRef.current
      if (cur != null) idx = Math.min(idx, Math.max(0, Math.min(cur, maxIdx)))
      internalHoverRef.current = idx
      setHoverPos({ x, y, w: rect.width, h: rect.height })
      onHoverRef.current(idx)
    }
    const onLeave = () => {
      internalHoverRef.current = null
      setHoverPos(null)
      onHoverRef.current(null)
    }
    const container = containerRef.current!
    container.addEventListener('mousemove', onMove)
    container.addEventListener('mouseleave', onLeave)
    return () => {
      container.removeEventListener('mousemove', onMove)
      container.removeEventListener('mouseleave', onLeave)
      stopOverlay()
      ro.disconnect()
      engine.destroy()
      engineRef.current = null
    }
  }, [])

  useEffect(() => {
    const engine = engineRef.current
    if (!engine || !bars.length) return
    const candles = toCandles(day, bars)
    const prev = prevRef.current
    const grew = bars.length - prev.n
    const n = candles.length
    const same = index === prev.index && day === prev.day
    if (same && grew === 0) {
      engine.updateLast(candles[n - 1])
    } else if (same && grew === 1 && n >= 2) {
      // the minute rolled: finalise the forming candle, then append
      engine.updateLast(candles[n - 2])
      engine.updateLast(candles[n - 1])
    } else {
      engine.setData(candles)
    }
    engine.setIndicators(buildIndicators(bars, prints, interval, flowPane))
    timesRef.current = candles.map((c) => c.time)
    prevRef.current = { index, day, n: bars.length }
  }, [index, day, bars, prints, interval, flowPane])

  useEffect(() => {
    engineRef.current?.setReplayCursor(cursor)
  }, [cursor])

  // keep the Callout placed when `hover` arrived from outside this component's own mousemove
  useEffect(() => {
    if (hover == null) { setHoverPos(null); return }
    if (hover === internalHoverRef.current) return
    const engine = engineRef.current
    const container = containerRef.current
    const conv = engine?.getMainConverters()
    const t = timesRef.current[hover]
    const bar = barsRef.current[hover]
    if (!conv || !container || t == null || !bar) return
    const rect = container.getBoundingClientRect()
    setHoverPos({ x: conv.timeToX(t), y: conv.priceToY(bar.c), w: rect.width, h: rect.height })
  }, [hover, bars, day])

  const hoverBar = hover != null ? bars[hover] : null
  const entryHere = hover != null ? (entries.find((e) => e.i === hover) ?? null) : null
  // what the chart marked inside the hovered bar, each by its own clock
  const ofdHere = marks && hoverBar
    ? marks.filter((e) => ['trap', 'absorption', 'exhaustion', 'climax'].includes(e.kind)
        && e.t >= hoverBar.t && (hover != null && bars[hover + 1] ? e.t < bars[hover + 1].t : true)) : []
  const t0 = hover != null ? timesRef.current[hover] : undefined
  const t1 = hover != null ? (timesRef.current[hover + 1] ?? (t0 != null ? t0 + (interval ?? 5) * 60_000 : undefined)) : undefined
  const fightsHere = engine && t0 != null && t1 != null
    ? engine.marks.filter((m) => m.kind !== 'wall' && m.t >= t0 && m.t < t1) : []

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={hostRef} style={{ position: 'absolute', inset: 0 }} />
      <canvas ref={overlayRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />
      {hover != null && hoverPos && hoverBar && (
        <Callout
          mode={mode}
          bar={hoverBar}
          day={day}
          entry={entryHere?.sig ?? null}
          ofd={ofdHere}
          fights={fightsHere}
          x={hoverPos.x}
          y={hoverPos.y}
          boxW={hoverPos.w}
          boxH={hoverPos.h}
        />
      )}
    </div>
  )
}
