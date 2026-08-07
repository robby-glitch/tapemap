// One compact ATM option-leg pane: the premium's own candles against the
// premium's OWN VWAP ±σ bands (engine-computed, rendered verbatim), plus its
// OI sub-pane. This is where the operator's trigger lives — "buy the touch of
// −3σ, sell +3σ" is read off THESE bands, not the index's — and until this
// component the app computed that series server-side, shipped it every 5s,
// and threw it away in the mapping.
//
// Deliberately slim: no LevelsOverlay, no narration, no callout, no
// structures. The pane answers one question — where is the premium relative
// to its own bands — and everything else already has a home.
import { useEffect, useMemo, useRef } from 'react'
import { createChartEngine } from '../vendor/candl/chart/engine'
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { TapeBar, OptPivotLeg } from '../data'
import type { Mode } from '../theme'
import { CHART_UP, CHART_DOWN, palette } from '../theme'
import { legRender } from './indicators'

interface Props {
  day: string
  bars: TapeBar[]
  leg: 'ce' | 'pe'
  /** The engine's tracked ATM strike (TapeView.strike) — rolling, disclosed. */
  strike: number | null
  cursor: number | null // replay bar index into `bars`; null = live
  mode: Mode
  /** Prior-session floor pivots for THIS contract, computed server-side, or
   *  null with `pivotsWhy` naming the reason. Drawn as muted constant lines. */
  pivots?: OptPivotLeg | null
  pivotsWhy?: string | null
  /** The expiry the leg belongs to (`opt_expiry`) — the NEAREST one, i.e. the
   *  contract the operator actually trades. Named in the header. */
  expiry?: string | null
  /** Full width (stacked, one leg per row) instead of sharing the row. */
  wide?: boolean
}

// Why this is not ~200px, which is what it was until the operator said the
// panes were "crammped up": the engine gives the OI sub-pane SUB_PANE_H=110
// plus a separator and the time axis, so a 200px host left mainH = 62 — under
// its own 120px floor, which then shrank the OI pane to 52 and pinned price at
// exactly 120px. Candles AND seven band lines in 120 pixels. At 460 the price
// pane gets ~320 and the OI pane its full 110. The page scrolls; height here
// is free, and reading the premium against its own bands is the whole job.
const PANE_H = 460

export default function LegChart({
  day, bars, leg, strike, cursor, mode,
  pivots = null, pivotsWhy = null, expiry = null, wide = false,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<IChartEngine | null>(null)
  const prevRef = useRef<{ day: string; n: number }>({ day: '', n: 0 })

  const render = useMemo(() => legRender(day, bars, leg, pivots, strike), [day, bars, leg, pivots, strike])
  const pal = palette(mode)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return // no-leg session: the host div is not mounted at all
    const engine = createChartEngine(host, { theme: mode, pricePrecision: 2, chartType: 'candles' })
    engineRef.current = engine
    // Same StrictMode rule as ContractChart: a remounted engine holds no
    // series, so the data effect below MUST take the setData path — reset the
    // identity ref or it would updateLast against an empty engine.
    prevRef.current = { day: '', n: 0 }
    engine.setSettings({
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      gridVisible: true, crosshairVisible: false,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })
    // The engine's own ResizeObserver is not sufficient here either — the
    // host grows when TradeTab measures its height (see ContractChart's
    // measured 57%-canvas failure). Keep ours.
    const ro = new ResizeObserver(() => engine.resize())
    ro.observe(host)
    return () => {
      ro.disconnect()
      engine.destroy()
      engineRef.current = null
    }
  }, [render.candles.length > 0])

  useEffect(() => {
    const engine = engineRef.current
    if (!engine || !render.candles.length) return
    const prev = prevRef.current
    const n = render.candles.length
    const grew = n - prev.n
    const same = day === prev.day
    if (same && grew === 0) {
      engine.updateLast(render.candles[n - 1])       // forming minute refreshed
    } else if (same && grew === 1 && n >= 2) {
      // Minute rollover: finalise the previously-forming candle, then append.
      engine.updateLast(render.candles[n - 2])
      engine.updateLast(render.candles[n - 1])
    } else {
      engine.setData(render.candles)
    }
    engine.setIndicators(render.indicators)
    prevRef.current = { day, n }
  }, [day, render])

  // Replay: the leg skips bars where it didn't print, so the bar-space cursor
  // must be mapped to leg-local candle space — the last candle whose source
  // bar index is <= cursor. -1 (cursor before the first printed candle) clips
  // everything, which is the honest render of "this leg hadn't printed yet".
  useEffect(() => {
    const engine = engineRef.current
    if (!engine) return
    if (cursor == null) { engine.setReplayCursor(null); return }
    let lo = -1
    for (let j = 0; j < render.map.length; j++) {
      if (render.map[j] <= cursor) lo = j
      else break
    }
    engine.setReplayCursor(lo)
  }, [cursor, render])

  useEffect(() => {
    const engine = engineRef.current
    if (!engine) return
    engine.setTheme(mode)
    engine.setSettings({
      upColor: CHART_UP[mode], downColor: CHART_DOWN[mode],
      gridVisible: true, crosshairVisible: false,
      alertSound: false, alertTune: 0, alertDuration: 1,
    })
  }, [mode])

  const name = leg.toUpperCase()
  return (
    <div style={{
      // `1 1 100%` forces one pane per row inside the same wrapping row, so
      // stacked mode needs no separate container.
      flex: wide ? '1 1 100%' : '1 1 380px',
      minWidth: 320, display: 'flex', flexDirection: 'column',
      border: `1px solid ${pal.border}`, borderRadius: 6, overflow: 'hidden',
      backgroundColor: pal.card,
    }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 8, padding: '6px 10px 4px',
        fontSize: 10.5, color: pal.textMuted,
      }}>
        <span style={{ fontWeight: 700, letterSpacing: '0.06em', color: pal.textSecondary, whiteSpace: 'nowrap' }}>
          ATM {strike != null ? strike.toFixed(0) : '—'} {name}
          {expiry ? ` · exp ${expiry}` : ''}
        </span>
        <span>
          rolling ATM — the tracked strike migrates with spot; a premium step
          at a hop is a strike change, not a trade
          {render.missing > 0 && ` · ${render.missing} minute${render.missing === 1 ? '' : 's'} this leg did not print`}
          {pivots
            ? ' · pivots: this contract’s own prior session'
            : pivotsWhy ? ` · pivots unavailable — ${pivotsWhy}` : ''}
        </span>
      </div>
      {render.candles.length ? (
        <div ref={hostRef} style={{ flex: 1, minHeight: PANE_H }} />
      ) : (
        // Honesty rule 1: an absent leg says so at full width; no placeholder
        // candles. The host div is not mounted at all, so zero canvases.
        <div style={{
          flex: 1, minHeight: PANE_H, display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: 11, color: pal.textMuted, padding: 12,
          textAlign: 'center',
        }}>
          no {name} leg on this session — the payload carried no {leg} bars, so
          nothing is charted
        </div>
      )}
    </div>
  )
}
