// Pure reshaping: payload arrays -> CandL render structures. No indicator is
// ever computed here (invariant #6) — the engine's IndicatorRenderData takes
// already-computed values aligned 1:1 with the candles.
import type { Candle } from '../vendor/candl/core/types'
import type { IndicatorRenderData } from '../vendor/candl/chart/types'
import type { TapeBar } from '../data'

// One-meaning colour (App.tsx `T`): brass is structure. Bands fade outward.
const BRASS = '#E0A852'
const BAND = ['rgba(224,168,82,0.70)', 'rgba(224,168,82,0.45)', 'rgba(224,168,82,0.28)']
const OI_LINE = '#7F8EA3' // neutral — OI is a series here, not a direction call

// Local-midnight epoch for the session date. Live payloads carry ISO dates;
// replay CSV days ("Tue 15") don't parse — fall back to a fixed base so the
// intraday HH:MM clock (which IS real data) still renders correctly.
export function dayBase(day: string): number {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(day)
  if (m) return new Date(+m[1], +m[2] - 1, +m[3]).getTime()
  return new Date(2026, 0, 1).getTime()
}

export function toCandles(day: string, bars: TapeBar[]): Candle[] {
  const base = dayBase(day)
  return bars.map((b) => {
    const [hh, mm] = b.t.split(':').map(Number)
    return { time: base + (hh * 60 + mm) * 60_000, open: b.o, high: b.h, low: b.l, close: b.c, volume: b.v }
  })
}

// NaN is guarded at the source (honesty rule 5): a non-finite payload value
// becomes a null gap in the plot, never a drawn falsehood.
const series = (bars: TapeBar[], f: (b: TapeBar) => number) =>
  bars.map((b) => { const v = f(b); return Number.isFinite(v) ? v : null })

export function buildIndicators(bars: TapeBar[]): IndicatorRenderData[] {
  return [
    {
      instanceId: 'vwap-bands', label: 'VWAP ±σ', placement: 'overlay',
      outputs: [
        { name: 'vwap', values: series(bars, (b) => b.vwap), color: BRASS },
        { name: '+1σ', values: series(bars, (b) => b.u1), color: BAND[0] },
        { name: '-1σ', values: series(bars, (b) => b.d1), color: BAND[0] },
        { name: '+2σ', values: series(bars, (b) => b.u2), color: BAND[1] },
        { name: '-2σ', values: series(bars, (b) => b.d2), color: BAND[1] },
        { name: '+3σ', values: series(bars, (b) => b.u3), color: BAND[2] },
        { name: '-3σ', values: series(bars, (b) => b.d3), color: BAND[2] },
      ],
    },
    {
      instanceId: 'oi', label: 'OI', placement: 'pane',
      outputs: [{ name: 'oi', values: series(bars, (b) => b.oi), color: OI_LINE }],
    },
  ]
}
