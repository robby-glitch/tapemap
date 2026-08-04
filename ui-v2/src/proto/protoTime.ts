// Time for the /proto spike. THROWAWAY — see context/HANDOFF.md §6b.
//
// lightweight-charts has no timezone support: it formats every timestamp with
// Date's UTC getters. Our clock is IST and carries no epoch at all — live.py
// converts the Dhan epoch to IST and keeps only "HH:MM" (live.py:291) — while
// indicators.ts's dayBase() returns a LOCAL-midnight epoch. So handing LWC
// `dayBase(day)/1000` renders the axis 5:30 off on this machine, and off by a
// DIFFERENT amount on a laptop set to UTC.
//
// The fix is to never hand it a true epoch. We hand it the epoch whose UTC
// clock IS the IST wall clock the payload already carries. dayBase() keeps
// ownership of every date format we accept (ISO / "Aug 04 LIVE" / "Jul 15");
// this file only re-anchors its calendar day to UTC midnight.
//
// Deliberately NO lightweight-charts import: this is date arithmetic, not
// charting. The UTCTimestamp cast belongs at the chart call site, which keeps
// the whole file — and its verification — usable before the dependency lands.

import { dayBase } from '../trade/indicators'
import type { TapeBar } from '../data'

/** UTC-midnight epoch (ms) for the session date dayBase() parsed. Reading
 *  dayBase's value back through LOCAL getters round-trips exactly, because
 *  dayBase built it from local Y/M/D in the first place — no offset term
 *  survives, so the result is identical on any machine timezone. */
export function utcBase(day: string): number {
  const d = new Date(dayBase(day))
  return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())
}

/** One epoch-SECONDS stamp per bar, aligned 1:1 with `bars`. Seconds, not
 *  milliseconds — lightweight-charts' UTCTimestamp is seconds, and candl's
 *  Candle.time is ms, which is exactly the kind of silent factor-of-1000 this
 *  comment exists to stop. */
export function toUtcTimes(day: string, bars: TapeBar[]): number[] {
  const base = utcBase(day)
  return bars.map((b) => {
    const [hh, mm] = b.t.split(':').map(Number)
    return (base + (hh * 60 + mm) * 60_000) / 1000
  })
}

/** '' when the stamps are finite and strictly ascending, otherwise a sentence
 *  naming the two bars that disagree.
 *
 *  Two separate hazards, one guard. LWC's setData THROWS on a duplicate or
 *  out-of-order time, and a NaN from an unparseable "HH:MM" slips past a naive
 *  `<=` because every comparison against NaN is false. The page discloses
 *  either one rather than dying on it (honesty rule: an absence gets a
 *  reason). */
export function ascentWhy(times: number[], bars: TapeBar[]): string {
  if (times.length !== bars.length) {
    return `${times.length} stamps for ${bars.length} bars — cannot line them up 1:1`
  }
  for (let i = 0; i < times.length; i++) {
    if (!Number.isFinite(times[i])) {
      return `bar ${i} has an unreadable clock ("${bars[i].t}") — cannot plot`
    }
    if (i > 0 && times[i] <= times[i - 1]) {
      return `bar ${i} ("${bars[i].t}") is not after bar ${i - 1} ("${bars[i - 1].t}") — cannot plot`
    }
  }
  return ''
}

/** The first stamp rendered as an ISO instant. This is the axis proof: for a
 *  09:15 first bar it MUST read "…T09:15:00.000Z". Printed in the header so
 *  the check sits on screen next to the payload's own clock, rather than in a
 *  console nobody opens during a live session. */
export function firstStampIso(times: number[]): string {
  const t = times[0]
  return Number.isFinite(t) ? new Date(t * 1000).toISOString() : '—'
}
