// Pure reshaping: payload arrays -> CandL render structures. No indicator is computed here (invariant #6): the
// engine's IndicatorRenderData takes already-computed values aligned 1:1 with the candles.
import type { Candle } from '../vendor/candl/core/types'
import type { IndicatorRenderData } from '../vendor/candl/chart/types'
import type { TapeBar } from '../data'
import type { TapeReply } from './tape'

const CVD_LINE = '#7F8EA3'
const DELTA_UP = '#26a69a'   // the candle pair, one meaning: the sign of the delta
const DELTA_DOWN = '#ef5350'

const MONTHS: Record<string, number> = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
}
const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})/
const MON_DAY = /^([A-Za-z]{3})\s+(\d{1,2})\b/

/** Local-midnight epoch for the session date, the anchor the chart's time axis is built on. The live key is
 *  "Sep 29 LIVE" (no year: the current year is assumed); CSV replay is "Jul 15"; an unreadable key falls back to a
 *  fixed anchor so bars still order. The intraday clock is real in every case. */
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

const IST_MS = 5.5 * 3600000
/** "HH:MM" IST for a tape-bar epoch, the label convention the chart's bars use. */
function hhmmOf(t: number): string {
  const d = new Date(t + IST_MS)
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
}

/** Delta and CVD aligned 1:1 with the chart's bars, or null when they cannot be: the record is 5-minute; 15 sums
 *  three record bars exactly; 3 and 1 do not divide it (spec §J.5). Alignment is by "HH:MM" label, never by index.
 *  `source` picks the family: the ladder record (`ofd`) or the Upstox ux ladder (`ux`, null-out when the reply
 *  carries a `why`). */
export function alignDelta(
  bars: TapeBar[], prints: TapeReply | null | undefined, interval: number | null | undefined,
  source: 'ofd' | 'ux' = 'ofd',
): { delta: (number | null)[]; cvd: (number | null)[] } | null {
  if (!prints || (interval !== 5 && interval !== 15)) return null
  const rows = source === 'ux' ? (prints.ux && !prints.ux.why ? prints.ux.bars : []) : prints.bars
  if (!rows.length) return null
  const per = new Map<string, number>()
  for (const b of rows) per.set(hhmmOf(b.t), b.delta)
  const delta: (number | null)[] = []
  const cvd: (number | null)[] = []
  let run: number | null = null
  for (const bar of bars) {
    let d: number | null = null
    if (interval === 5) {
      d = per.has(bar.t) ? per.get(bar.t)! : null
    } else {
      const [hh, mm] = bar.t.split(':').map(Number)
      const parts = [0, 5, 10].map((k) => per.get(`${String(hh).padStart(2, '0')}:${String(mm + k).padStart(2, '0')}`))
      d = parts.every((v) => v != null) ? parts.reduce((a, v) => a + (v as number), 0) : null
    }
    delta.push(d)
    if (d != null) run = (run ?? 0) + d
    cvd.push(d != null ? run : null)
  }
  return delta.some((v) => v != null) ? { delta, cvd } : null
}

/** The chart's sub-panes. The FUT OI pane is gone (in expiry week it reads the roll as positioning; her OI is read at
 *  levels). What is left is the Flow pane: delta per bar plus its running sum (CVD), from ONE family, the Upstox ux
 *  ladder, the book the engine's fights are built from. Tagged [I]: the side of a print is inferred. It draws only at
 *  5 and 15 minutes (the record is 5-minute and is never re-cut), and only while the Flow pane is on. The vendor
 *  gives a sub-pane a fixed 110 px, about 17% of the chart on a 1080p screen. */
export function buildIndicators(bars: TapeBar[], prints: TapeReply | null | undefined,
                                publishedInterval: number | null | undefined, flowPane: boolean): IndicatorRenderData[] {
  if (!flowPane) return []
  const du = alignDelta(bars, prints, publishedInterval, 'ux')
  if (!du) return []
  const last = [...du.delta].reverse().find((v) => v != null)
  const cvd = [...du.cvd].reverse().find((v) => v != null)
  const fmt = (v: number | null | undefined) => (v == null ? '—' : `${v > 0 ? '+' : ''}${Math.round(v)}`)
  return [{
    instanceId: 'flow', placement: 'pane',
    label: `FLOW [I] · ux Δ last ${fmt(last)} lots · CVD ${fmt(cvd)}`,
    outputs: [
      { name: 'delta', values: du.delta, color: (last ?? 0) >= 0 ? DELTA_UP : DELTA_DOWN, style: 'histogram' },
      { name: 'cvd', values: du.cvd, color: CVD_LINE },
    ],
  }]
}
