import { useEffect, useRef } from 'react'
import { createChartEngine } from '../vendor/candl/chart/engine'
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { TapeBar, MapLevel } from '../data'
import { toCandles, buildIndicators } from './indicators'
import { startLevelsOverlay } from './LevelsOverlay'

interface Props {
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  cursor: number | null // replay bar index; null = live
}

export default function ContractChart({ day, bars, levels, cursor }: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<IChartEngine | null>(null)
  const levelsRef = useRef<MapLevel[]>(levels)
  const prevRef = useRef<{ day: string; n: number }>({ day: '', n: 0 })
  levelsRef.current = levels

  useEffect(() => {
    const host = hostRef.current!
    const engine = createChartEngine(host, { theme: 'dark', pricePrecision: 2, chartType: 'candles' })
    engineRef.current = engine
    // The vendored theme's own candles are teal/red (#26a69a/#ef5350) — foreign
    // to this app's palette. setSettings is the library's sanctioned styling
    // hook, so the colours align here rather than by editing the pristine
    // vendor theme. Green/red carry direction, matching T.bull / T.bear.
    engine.setSettings({
      upColor: '#2EC27E', downColor: '#FF5F6B',
      gridVisible: true, crosshairVisible: true,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })
    const ro = new ResizeObserver(() => engine.resize())
    ro.observe(host)
    const stopOverlay = startLevelsOverlay(overlayRef.current!, host, engine, () => levelsRef.current)
    return () => {
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
    if (day === prev.day && grew === 0) {
      engine.updateLast(candles[n - 1])   // same forming minute, refreshed
    } else if (day === prev.day && grew === 1 && n >= 2) {
      // The minute rolled over. The bar we last pushed was still forming, so
      // its final OHLC must be written before the new one is appended —
      // otherwise the closed candle keeps the mid-formation values it had at
      // the last poll. updateLast replaces on equal open time and appends
      // otherwise (engine contract), so these two calls do exactly that.
      engine.updateLast(candles[n - 2])
      engine.updateLast(candles[n - 1])
    } else {
      engine.setData(candles) // first load, day change, or any gap — resync
    }
    engine.setIndicators(buildIndicators(bars))
    prevRef.current = { day, n: bars.length }
  }, [day, bars])

  useEffect(() => {
    engineRef.current?.setReplayCursor(cursor)
  }, [cursor])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={hostRef} style={{ position: 'absolute', inset: 0 }} />
      <canvas ref={overlayRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />
    </div>
  )
}
