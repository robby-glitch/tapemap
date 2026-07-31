import { useEffect, useRef, useState } from 'react'
import { createChartEngine } from '../vendor/candl/chart/engine'
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { TapeBar, MapLevel, IndexKey, RotationSignal, Structure } from '../data'
import type { Mode } from '../theme'
import { CHART_UP, CHART_DOWN } from '../theme'
import { toCandles, buildIndicators } from './indicators'
import { startLevelsOverlay } from './LevelsOverlay'
import type { Narration } from './narration'
import type { Zone } from './zones'
import Callout from './Callout'

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  cursor: number | null // replay bar index; null = live
  mode: Mode
  hover: number | null
  onHover: (i: number | null) => void
  narrs: (Narration | null)[]
  /** Market-condition runs for the overlay's zone bands. Optional so a caller
   *  that has no ctx to group yet renders exactly as before — an absent prop
   *  means "no bands", never an invented verdict. */
  zones?: Zone[]
  /** The backend's SMC structure layer, or null when it is unavailable (no
   *  such backend, or bar indices that cannot be trusted — see data.ts's skip
   *  guard). Null draws nothing; TradeTab prints the reason. */
  structures?: Structure[] | null
  /** The SMC toggle. False = the operator hid the layer, which is a different
   *  fact from the layer being unavailable, and is not disclosed as one. */
  smc?: boolean
  /** The backend's index band-rotation signals, 1:1 with `bars`, or null when
   *  they cannot be lined up honestly (data.ts's guard). Null draws nothing;
   *  TradeTab prints the reason. */
  rotation?: (RotationSignal | null)[] | null
  /** The unscored event layers drawn over price — zone/condition bands and
   *  story balloons. Defaults TRUE so this component renders as it always did
   *  when the prop is omitted; TradeTab passes the operator's toggle, which
   *  defaults off. `narrs` still reaches the hover Callout either way — an
   *  on-demand read is not clutter, and hiding it would remove information the
   *  operator asked for rather than noise they did not. */
  story?: boolean
}

// A shared empty default, so an omitted `zones` prop does not hand the overlay
// a fresh array identity on every render.
const NO_ZONES: Zone[] = []

/** Nearest index in a sorted-ascending time array to `t` — the inverse of
 *  toCandles's own `dayBase(day) + minutes*60000` construction. Binary search
 *  since the axis is monotonic (one entry per bar, in bar order). */
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
  index, day, bars, levels, cursor, mode, hover, onHover, narrs, zones = NO_ZONES,
  structures = null, smc = true, rotation = null, story = true,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const hostRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<IChartEngine | null>(null)
  const levelsRef = useRef<MapLevel[]>(levels)
  const modeRef = useRef<Mode>(mode)
  const prevRef = useRef<{ index: string; day: string; n: number }>({ index: '', day: '', n: 0 })
  levelsRef.current = levels
  modeRef.current = mode

  // Refs so the single long-lived mousemove listener (attached once, at engine
  // creation) always reads current data without needing to be re-attached
  // whenever bars/cursor/onHover change identity.
  const barsRef = useRef<TapeBar[]>(bars)
  barsRef.current = bars
  const cursorRef = useRef<number | null>(cursor)
  cursorRef.current = cursor
  const onHoverRef = useRef(onHover)
  onHoverRef.current = onHover
  // Same pattern for the overlay's two new inputs: the rAF loop in
  // LevelsOverlay is started ONCE (in the []-deps effect below) and reads its
  // data through getters, so narrations and zones must reach it via refs — a
  // captured prop would freeze at the values of the first render.
  const narrsRef = useRef<(Narration | null)[]>(narrs)
  narrsRef.current = narrs
  const zonesRef = useRef<Zone[]>(zones)
  zonesRef.current = zones
  const structuresRef = useRef<Structure[] | null>(structures)
  structuresRef.current = structures
  const smcRef = useRef<boolean>(smc)
  smcRef.current = smc
  // Same ref pattern again: the rAF loop reads its data through getters, so a
  // captured prop would freeze at the first render's value.
  const rotationRef = useRef<(RotationSignal | null)[] | null>(rotation)
  rotationRef.current = rotation
  const storyRef = useRef<boolean>(story)
  storyRef.current = story
  // The candle time axis (epoch ms), rebuilt once per data change (the same
  // [index, day, bars] effect that feeds the engine) — never recomputed
  // inside the mousemove handler itself.
  const timesRef = useRef<number[]>([])
  // The last index this component itself set via mousemove, so the
  // hover-position effect below can tell "the chart's own cursor moved" apart
  // from "hover arrived from elsewhere (e.g. the ribbon)".
  const internalHoverRef = useRef<number | null>(null)

  // Where to anchor the Callout: literal mouse position while hovering the
  // chart itself; recomputed from the engine's own converters when `hover`
  // arrives from outside (Ribbon), since there is no mouse position to read
  // in that case. `w`/`h` are the frame size at the moment of the read, used
  // for the Callout's own edge-flip math.
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number; w: number; h: number } | null>(null)

  useEffect(() => {
    const host = hostRef.current!
    const engine = createChartEngine(host, { theme: mode, pricePrecision: 2, chartType: 'candles' })
    engineRef.current = engine
    // A newly created engine holds no series, so the next data effect MUST take
    // the setData path. prevRef survives an effect remount (React StrictMode
    // re-runs effects in dev), and without this reset the data effect would see
    // grew === 0 and call updateLast on an empty engine — leaving the chart with
    // a single candle instead of the whole session.
    prevRef.current = { index: '', day: '', n: 0 }
    // setSettings is the library's sanctioned styling hook, so candle colour is
    // set here rather than by editing the pristine vendor theme. Green/red carry
    // direction only. In LIGHT mode CHART_UP/DOWN are deliberately the
    // Kite/TradingView default pair (#26a69a/#ef5350) so these candles match the
    // ones the operator reads in Kite; dark stays on palette(mode).bull/bear.
    engine.setSettings({
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      gridVisible: true, crosshairVisible: true,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })
    // The engine installs its own ResizeObserver, but ours is NOT redundant —
    // removing it was tried and measurably broke the chart: the host grows once
    // TradeTab measures its available height, and without this the engine keeps
    // a stale internal layout and draws the session into ~57% of the canvas
    // (14 candle clusters instead of 156). Keep it.
    const ro = new ResizeObserver(() => engine.resize())
    ro.observe(host)
    const stopOverlay = startLevelsOverlay(
      overlayRef.current!, host, engine,
      () => levelsRef.current, () => modeRef.current,
      () => ({
        bars: barsRef.current, times: timesRef.current,
        narrs: narrsRef.current, cursor: cursorRef.current,
        rotation: rotationRef.current,
      }),
      () => zonesRef.current,
      () => structuresRef.current,
      () => smcRef.current,
      () => storyRef.current,
    )

    // Hover mapping: clientX -> container-relative x -> engine's own xToTime
    // -> nearest bar index. The overlay canvas is pointer-events:none, so the
    // container itself receives these. Converters are re-queried on every
    // move (never cached — they go stale under pan/zoom).
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
      const t = conv.xToTime(x)
      const maxIdx = barsRef.current.length - 1
      let idx = Math.max(0, Math.min(nearestIndex(times, t), maxIdx))
      // The causality rule: hovering must never reveal a bar the replay
      // cursor is hiding. Not optional.
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
      engine.updateLast(candles[n - 1])   // same forming minute, refreshed
    } else if (same && grew === 1 && n >= 2) {
      // The minute rolled over. The bar we last pushed was still forming, so
      // its final OHLC must be written before the new one is appended —
      // otherwise the closed candle keeps the mid-formation values it had at
      // the last poll. updateLast replaces on equal open time and appends
      // otherwise (engine contract), so these two calls do exactly that.
      engine.updateLast(candles[n - 2])
      engine.updateLast(candles[n - 1])
    } else {
      engine.setData(candles) // first load, index/day change, or any gap — resync
    }
    engine.setIndicators(buildIndicators(bars))
    timesRef.current = candles.map((c) => c.time)
    prevRef.current = { index, day, n: bars.length }
  }, [index, day, bars])

  useEffect(() => {
    engineRef.current?.setReplayCursor(cursor)
  }, [cursor])

  // Mode: repaint the engine's own theme and candle colours whenever it
  // changes (the toggle in TradeTab), independent of the data effect above.
  useEffect(() => {
    const engine = engineRef.current
    if (!engine) return
    engine.setTheme(mode)
    engine.setSettings({
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      gridVisible: true, crosshairVisible: true,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })
  }, [mode])

  // Keep the Callout positioned when `hover` arrived from outside (the
  // ribbon) rather than from this component's own mousemove — derive its
  // screen position from the engine's own converters at the hovered bar's
  // own time/price rather than guessing.
  useEffect(() => {
    if (hover == null) {
      setHoverPos(null)
      return
    }
    if (hover === internalHoverRef.current) return // mousemove already positioned it
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

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={hostRef} style={{ position: 'absolute', inset: 0 }} />
      <canvas ref={overlayRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />
      {hover != null && hoverPos && hoverBar && (
        <Callout
          mode={mode}
          bar={hoverBar}
          prevBar={hover > 0 ? bars[hover - 1] : null}
          day={day}
          narr={narrs[hover] ?? null}
          rot={rotation?.[hover] ?? null}
          x={hoverPos.x}
          y={hoverPos.y}
          boxW={hoverPos.w}
          boxH={hoverPos.h}
        />
      )}
    </div>
  )
}
