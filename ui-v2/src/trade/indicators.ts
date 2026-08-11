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
// The LEVEL stays a plain neutral line: it is context, not a direction call.
// What the level cannot say — who moved and which way — is said in words by
// `oiLabel` below, which is the part of this pane that carries the meaning.
const OI_LINE = '#7F8EA3'

/** Indian market units: OI is spoken in lakh and crore, not millions. */
function lakh(n: number): string {
  const a = Math.abs(n)
  if (a >= 1e7) return `${(n / 1e7).toFixed(2)} Cr`
  if (a >= 1e5) return `${(n / 1e5).toFixed(2)} L`
  if (a >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return `${Math.round(n)}`
}

/** The four states, named AND said in plain language.
 *
 * `option` picks the vocabulary. On a futures series the two sides are longs
 * and shorts; on an OPTION series the short side is the WRITER — the word the
 * operator uses, and the one that says who is carrying the risk. Same four
 * states either way; only the noun changes.
 */
function oiState(dOi: number, dPx: number, option: boolean) {
  if (dOi > 0 && dPx > 0)
    return { name: 'LONG BUILDUP', said: option ? 'buyers added' : 'longs added' }
  if (dOi > 0 && dPx < 0)
    return { name: 'SHORT BUILDUP', said: option ? 'writers added' : 'shorts added' }
  if (dOi < 0 && dPx > 0)
    return { name: 'SHORT COVERING', said: option ? 'writers covered' : 'shorts covered' }
  return { name: 'LONG UNWINDING', said: option ? 'buyers exited' : 'longs exited' }
}

/** The pane's headline: what just happened to open interest on THIS contract.
 *
 * The pane used to read "OI 11,203,335.00" — a level, which answers "how
 * much", and nobody asks that mid-session. The operator's own rule does not
 * use it either: their dictated condition is explicitly NOT peak OI but the
 * rate of change — "oi is lagging so we need to prempt by the change".
 *
 * So the line reads the CHANGE, names the state, and says in words who moved:
 *
 *     PE 24600 · SHORT BUILDUP — writers added 2.41 L · 1.12 Cr open · +8.63 L today
 *
 * A bar with nothing to read says so instead of picking a state. Flat OI, a
 * flat close, and a missing leg are each real answers; guessing one of four
 * directions out of them would invent a read the tape never gave.
 */
function oiLabel(oi: (number | null)[], close: (number | null)[],
                 contract: string, option: boolean): string {
  const head = contract ? `${contract} · ` : ''
  let i = oi.length - 1
  while (i > 0 && oi[i] == null) i--
  const now = oi[i]
  if (now == null) return `${head}OI — not published for this contract`

  const open = oi.find((v) => v != null) ?? null
  const today = open == null
    ? '' : ` · ${now >= open ? '+' : ''}${lakh(now - open)} today`
  const level = `${lakh(now)} open${today}`

  const prev = i > 0 ? oi[i - 1] : null
  const pa = i > 0 ? close[i - 1] : null
  const pb = close[i]
  if (prev == null || pa == null || pb == null)
    return `${head}OI ${level} — no previous bar to compare`
  const dOi = now - prev
  const dPx = pb - pa
  if (dOi === 0) return `${head}OI unchanged this bar · ${level}`
  if (dPx === 0)
    return `${head}OI ${dOi > 0 ? '+' : ''}${lakh(dOi)} on a flat close — no read · ${level}`

  const s = oiState(dOi, dPx, option)
  return `${head}${s.name} — ${s.said} ${lakh(Math.abs(dOi))} · ${level}`
}

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
                          piv?: OptPivotLeg | null,
                          strike?: number | null): LegRender {
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
      instanceId: `${leg}-oi`, placement: 'pane',
      label: oiLabel(oi, candles.map((c) => c.close),
                     `${leg.toUpperCase()}${strike ? ` ${strike}` : ''}`, true),
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
    // The FUT chart no longer draws the VWAP polyline either. Operator,
    // 2026-08-11: the line is redundant next to the level chips on the right
    // and the VWAP figure the stat strip / Σ BANDS pane already print — one
    // more line over the tape bought nothing. The σ deviations went the same
    // way earlier (filled ribbons on the overlay canvas, edges now silent —
    // see LevelsOverlay). The LEG panes keep their own VWAP: the operator
    // named only "the chart". VWAP_LINE stays exported for them.
    {
      instanceId: 'oi', placement: 'pane',
      // The index pane charts the FUTURE, so the two sides are longs and
      // shorts rather than buyers and writers.
      label: oiLabel(series(bars, (b) => b.oi), series(bars, (b) => b.c),
                     'FUT', false),
      outputs: [{ name: 'oi', values: series(bars, (b) => b.oi), color: OI_LINE }],
    },
  ]
}
