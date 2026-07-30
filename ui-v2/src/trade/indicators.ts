// Pure reshaping: payload arrays -> CandL render structures. No indicator is
// ever computed here (invariant #6) — the engine's IndicatorRenderData takes
// already-computed values aligned 1:1 with the candles.
import type { Candle } from '../vendor/candl/core/types'
import type { IndicatorRenderData } from '../vendor/candl/chart/types'
import type { TapeBar } from '../data'

// One-meaning colour (App.tsx `T`): brass is structure. The σ deviations
// themselves are filled ribbons drawn on the overlay canvas (LevelsOverlay),
// not lines here — so this file no longer needs a per-band line colour.
const BRASS = '#E0A852'
const OI_LINE = '#7F8EA3' // neutral — OI is a series here, not a direction call

const MONTHS: Record<string, number> = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
  jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
}
const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})/
const MON_DAY = /^([A-Za-z]{3})\s+(\d{1,2})\b/

// How much of the session's calendar date the payload actually told us. The
// live backend emits ISO "YYYY-MM-DD" (exact); the live poller also emits
// "Jul 30 LIVE" (real month/day plus a trailing " LIVE" suffix — live.py:225);
// CSV replay emits "Jul 15" — real month and day, but the string carries no
// year. Anything else tells us nothing. The intraday HH:MM clock is real in
// all three cases; only the calendar part varies, and the UI discloses
// anything short of 'exact' rather than letting an inferred date read as fact.
export type DayPrecision = 'exact' | 'no-year' | 'none'

export function dayPrecision(day: string): DayPrecision {
  if (ISO_DAY.test(day)) return 'exact'
  const md = MON_DAY.exec(day.trim())
  if (md && MONTHS[md[1].toLowerCase()] !== undefined) return 'no-year'
  return 'none'
}

// Local-midnight epoch for the session date — the anchor the chart's time axis
// is built on. Parses as much of the real date as the payload carries; when it
// carries no year we assume the current one, and when it carries nothing
// parseable we use a fixed anchor so bars still order correctly within the
// session. dayPrecision() reports which case applied.
export function dayBase(day: string): number {
  const iso = ISO_DAY.exec(day)
  if (iso) return new Date(+iso[1], +iso[2] - 1, +iso[3]).getTime()
  const md = MON_DAY.exec(day.trim())
  if (md) {
    const mo = MONTHS[md[1].toLowerCase()]
    if (mo !== undefined) return new Date(new Date().getFullYear(), mo, +md[2]).getTime()
  }
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
      // The σ deviations themselves are no longer drawn as lines here — they
      // are filled ribbons on the overlay canvas (see LevelsOverlay's
      // startLevelsOverlay), which is why this instance now emits only VWAP.
      instanceId: 'vwap-bands', label: 'VWAP ±σ', placement: 'overlay',
      outputs: [
        { name: 'vwap', values: series(bars, (b) => b.vwap), color: BRASS },
      ],
    },
    {
      instanceId: 'oi', label: 'OI', placement: 'pane',
      outputs: [{ name: 'oi', values: series(bars, (b) => b.oi), color: OI_LINE }],
    },
  ]
}
