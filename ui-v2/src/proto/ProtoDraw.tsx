// Does candl's drawing layer actually work? THROWAWAY.
//
// This is NOT part of the three proofs — it answers a question the rubric never
// asked and that turns out to matter more: can the operator draw on the chart.
//
// The finding that prompted it: candl ships 61 drawing tools with a full
// lifecycle API (setActiveTool / setDrawings / onDrawingsChange /
// onSelectionChange), lightweight-charts ships ZERO, and ui-v2 currently turns
// NONE of candl's on — the only app-side reference to the whole module is
// LevelsOverlay importing the `Converters` type. So the capability has been
// sitting one toolbar away this entire time.
//
// Deliberately mounted inside /proto, never in TradeTab: that tab is the live
// trading surface and carries the layout trap documented at
// TradeTab.tsx:519-528, where adding a row under the chart collapsed it to zero
// twice. Nothing here can reach it.
//
// src/vendor/candl/ is READ-ONLY (VENDOR.md: "never edit a file under candl/").

import { useEffect, useRef, useState } from 'react'
import { createChartEngine } from '../vendor/candl/chart/engine'
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { Drawing, DrawingToolId } from '../vendor/candl/drawings/types'
import { CHART_DOWN, CHART_UP, type Mode, MONO, palette } from '../theme'
import { buildIndicators, toCandles } from '../trade/indicators'
import type { TapeBar } from '../data'

const PANE_H = 460
const STORE = 'proto.drawings'

/** A deliberately small slice of the 61 — the ones an ICT/SMC read actually
 *  leans on. If these behave, the rest are the same machinery. */
const TOOLS: { id: DrawingToolId; label: string }[] = [
  { id: 'trendline', label: 'trend' },
  { id: 'ray', label: 'ray' },
  { id: 'hline', label: 'H-line' },
  { id: 'vline', label: 'V-line' },
  { id: 'rect', label: 'box' },
  { id: 'channel', label: 'channel' },
  { id: 'fib', label: 'fib' },
  { id: 'fibext', label: 'fib ext' },
  { id: 'longpos', label: 'long pos' },
  { id: 'brush', label: 'brush' },
  { id: 'note', label: 'note' },
]

interface Props {
  day: string
  bars: TapeBar[]
  mode: Mode
}

export default function ProtoDraw({ day, bars, mode }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const engineRef = useRef<IChartEngine | null>(null)
  const prevRef = useRef({ day: '', n: 0 })
  const [tool, setTool] = useState<DrawingToolId | null>(null)
  const [magnet, setMagnet] = useState(false)
  const [count, setCount] = useState(0)
  const [selected, setSelected] = useState<string>('none')
  const pal = palette(mode)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    const engine = createChartEngine(host, {
      theme: mode, pricePrecision: 2, chartType: 'candles',
      // The three callbacks that make a toolbar possible. Without
      // onActiveToolChange the button stays lit after the tool finishes.
      onDrawingsChange: (ds) => {
        setCount(ds.length)
        // Round-trips the whole list through storage, which is the real test:
        // a drawing that cannot be persisted is a drawing lost on refresh.
        try { localStorage.setItem(STORE, JSON.stringify(ds)) } catch { /* quota — not this test's problem */ }
      },
      onActiveToolChange: (t) => setTool(t),
      onSelectionChange: (d) => setSelected(d ? `${d.tool} #${String(d.id).slice(0, 6)}` : 'none'),
    })
    engineRef.current = engine
    prevRef.current = { day: '', n: 0 }
    engine.setSettings({
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      gridVisible: true, crosshairVisible: true,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })

    // Restore whatever the last session drew. setDrawings deliberately does
    // NOT fire onDrawingsChange, so the count is set by hand here.
    try {
      const raw = localStorage.getItem(STORE)
      if (raw) {
        const ds = JSON.parse(raw) as Drawing[]
        if (Array.isArray(ds)) { engine.setDrawings(ds); setCount(ds.length) }
      }
    } catch { /* a corrupt store must not take the page down */ }

    const ro = new ResizeObserver(() => engine.resize())
    ro.observe(host)
    return () => { ro.disconnect(); engine.destroy(); engineRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const engine = engineRef.current
    if (!engine || !bars.length) return
    const candles = toCandles(day, bars)
    const prev = prevRef.current
    const same = prev.day === day
    const grew = candles.length - prev.n
    if (same && grew === 0) engine.updateLast(candles[candles.length - 1])
    else if (same && grew === 1 && candles.length >= 2) {
      engine.updateLast(candles[candles.length - 2])
      engine.updateLast(candles[candles.length - 1])
    } else engine.setData(candles)
    engine.setIndicators(buildIndicators(bars))
    prevRef.current = { day, n: candles.length }
  }, [day, bars])

  useEffect(() => { engineRef.current?.setTheme(mode) }, [mode])

  const arm = (id: DrawingToolId) => {
    const next = tool === id ? null : id
    setTool(next)
    engineRef.current?.setActiveTool(next)
  }

  const btn = (active: boolean) => ({
    fontFamily: MONO, fontSize: 11, cursor: 'pointer', padding: '3px 7px',
    borderRadius: 3, border: `1px solid ${active ? pal.accent : pal.border}`,
    background: active ? pal.inset : 'transparent',
    color: active ? pal.accent : pal.textSecondary,
  })

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginBottom: 8 }}>
        {TOOLS.map((t) => (
          <button key={t.id} onClick={() => arm(t.id)} style={btn(tool === t.id)}>{t.label}</button>
        ))}
        <span style={{ width: 12 }} />
        <button onClick={() => { const m = !magnet; setMagnet(m); engineRef.current?.setMagnet(m) }}
                style={btn(magnet)}>magnet</button>
        <button onClick={() => { engineRef.current?.clearDrawings(); setCount(0); setSelected('none') }}
                style={btn(false)}>clear</button>
        <span style={{ fontFamily: MONO, fontSize: 11, color: pal.textMuted, marginLeft: 8 }}>
          armed: {tool ?? '—'} · drawings: {count} · selected: {selected}
        </span>
      </div>
      <div ref={hostRef} style={{ width: '100%', height: PANE_H }} />
    </div>
  )
}
