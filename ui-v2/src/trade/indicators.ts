// Pure reshaping: payload arrays -> CandL render structures. No indicator is
// ever computed here (invariant #6) — the engine's IndicatorRenderData takes
// already-computed values aligned 1:1 with the candles.
import type { Candle } from '../vendor/candl/core/types'
import type { IndicatorRenderData } from '../vendor/candl/chart/types'
import type { TapeBar, BarLeg, OptPivotLeg } from '../data'

// One-meaning colour (App.tsx `T`): brass is structure. The σ deviations
// themselves are filled ribbons drawn on the overlay canvas (LevelsOverlay),
// not lines here — so this file no longer needs a per-band line colour.
// VWAP is bright red, matching the operator's own Kite band study (legend
// screenshot, 2026-07-30) — the σ bands' dark-red/sage/azure shading lives in
// LevelsOverlay's BAND_RGB. Eyeballed from that legend, so a shade may be off;
// these two sites are the only places to correct it.
const VWAP_LINE = '#FF1A1A'
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

/* ── ATM option-leg panes ─────────────────────────────────────────────────
   The leg charts are small and carry no LevelsOverlay, so their σ bands are
   plain indicator LINES on the engine (the pattern this file used for the
   FUT chart before the ribbons). Colours echo the overlay's BAND_RGB family
   (±1σ dark red / ±2σ sage / ±3σ azure) so the two charts read as one
   system; VWAP is the same bright red as the FUT chart. */
const LEG_BAND_LINES: [keyof BarLeg, string][] = [
  ['vwap', VWAP_LINE],
  ['u1', '#8B1A1A'], ['d1', '#8B1A1A'],
  ['u2', '#5F9C5F'], ['d2', '#5F9C5F'],
  ['u3', '#0084B8'], ['d3', '#0084B8'],
]

export interface LegRender {
  candles: Candle[]
  indicators: IndicatorRenderData[]
  /** leg-local candle index -> source index into `bars`. Needed to clamp the
   *  replay cursor: the leg skips bars where it didn't print, so bar index N
   *  is NOT candle index N. */
  map: number[]
  /** Bars whose FUT printed but this leg did not — disclosed, never bridged. */
  missing: number
}

// Prior-day pivot lines on the leg panes: horizontal constants, one muted
// colour for all seven — they are structure, not direction, and the pane is
// small enough that seven coloured lines would fight the bands.
const PIV_LINE = '#8A93A0'
const PIV_KEYS: (keyof OptPivotLeg)[] = ['P', 'R1', 'S1', 'R2', 'S2', 'R3', 'S3']

/** One option leg -> candles + band lines + OI pane (+ prior-day pivot lines
 *  when the backend published them for this leg), built together so the
 *  indicator values stay aligned 1:1 with the candles even though null-leg
 *  bars are skipped. Purely a reshape of engine-computed fields. */
export function legRender(day: string, bars: TapeBar[], leg: 'ce' | 'pe',
                          piv?: OptPivotLeg | null): LegRender {
  const base = dayBase(day)
  const candles: Candle[] = []
  const map: number[] = []
  const values: Record<string, (number | null)[]> = {}
  for (const [k] of LEG_BAND_LINES) values[k as string] = []
  const oi: (number | null)[] = []
  let missing = 0
  for (let i = 0; i < bars.length; i++) {
    const L = bars[i][leg]
    if (!L) { missing++; continue }
    const [hh, mm] = bars[i].t.split(':').map(Number)
    candles.push({
      time: base + (hh * 60 + mm) * 60_000,
      open: L.o, high: L.h, low: L.l, close: L.c, volume: L.v,
    })
    map.push(i)
    for (const [k] of LEG_BAND_LINES) {
      const v = L[k]
      values[k as string].push(typeof v === 'number' && Number.isFinite(v) ? v : null)
    }
    oi.push(typeof L.oi === 'number' && Number.isFinite(L.oi) ? L.oi : null)
  }
  const indicators: IndicatorRenderData[] = [
    {
      instanceId: `${leg}-bands`, label: 'VWAP ±σ', placement: 'overlay',
      outputs: LEG_BAND_LINES.map(([k, color]) => ({
        name: k as string, values: values[k as string], color,
      })),
    },
    {
      instanceId: `${leg}-oi`, label: 'OI', placement: 'pane',
      outputs: [{ name: 'oi', values: oi, color: OI_LINE }],
    },
  ]
  if (piv) {
    // Constant per bar — the pivot IS a horizontal level. Values come from
    // the backend block verbatim; nothing is computed here (invariant #6).
    indicators.push({
      instanceId: `${leg}-pivots`, label: 'PIVOTS (prior session)', placement: 'overlay',
      outputs: PIV_KEYS.map((k) => ({
        name: k as string,
        values: candles.map(() => (Number.isFinite(piv[k]) ? piv[k] : null)),
        color: PIV_LINE,
      })),
    })
  }
  return { candles, indicators, map, missing }
}

export function buildIndicators(bars: TapeBar[]): IndicatorRenderData[] {
  return [
    {
      // The σ deviations themselves are no longer drawn as lines here — they
      // are filled ribbons on the overlay canvas (see LevelsOverlay's
      // startLevelsOverlay), which is why this instance now emits only VWAP.
      instanceId: 'vwap-bands', label: 'VWAP ±σ', placement: 'overlay',
      outputs: [
        { name: 'vwap', values: series(bars, (b) => b.vwap), color: VWAP_LINE },
      ],
    },
    {
      instanceId: 'oi', label: 'OI', placement: 'pane',
      outputs: [{ name: 'oi', values: series(bars, (b) => b.oi), color: OI_LINE }],
    },
  ]
}
