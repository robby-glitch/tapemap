// HER ZONE, ALWAYS THE 3-MINUTE MACHINE (CLAUDE.md rule 3: 3-minute is canonical; `server._hold_machine` reads it at
// SCORED_INTERVAL). The backend re-runs `band_rotation.run_states` on whatever interval a chart asks for, so a 5m
// chart's own `zone_state` is a different machine (29 Sep: no BUY at 5m, the 3m machine's BUY d2 fired at 09:39).
// This hook hands every reader the 3-minute machine: from the chart's own payload when the chart IS 3m, otherwise from
// one extra read of `/api/data?interval=3` for the active index. A failed read is a sentence, never a 5m substitute.
import { useEffect, useMemo, useState } from 'react'
import type { Bands3, IndexKey, RunState, TapeBar, TapeView } from '../data'

export interface Zone3 {
  /** The 3-minute bars (their d2/d3/u2/u3 are her zone's bands). Empty when unread. */
  bars: TapeBar[]
  buy: RunState[] | null
  sell: RunState[] | null
  /** Why the machine is not available, in a sentence. Empty when it is. */
  why: string
  /** The session day of those bars. */
  day: string
  /** ZONE-3M (draft §1r): on a 3-minute chart from band_rotation.ZONE3_FROM (the payload's `zone3_on`), the bars on
   *  the bands computed on the 3-minute bars and the zone machine on those same bands -- one switch, read by the Trade
   *  tab's pockets and entry markers and by the machine strip and tab title (App.tsx `zm`), so nothing on her screen
   *  disagrees with the pockets. Absent or null otherwise, and every reader keeps bars / buy / sell above. */
  z3?: { bars: TapeBar[]; buy: RunState[]; sell: RunState[] } | null
}

const POLL_MS = 5000  // the main tape poll's cadence: this is her live ARMED signal
/** A bar whose 3-minute bands could not be computed: a hole (NaN, drawZone skips it), never the sampled value. */
const HOLE: Bands3 = { vwap: NaN, u1: NaN, d1: NaN, u2: NaN, d2: NaN, u3: NaN, d3: NaN }

/** One `/api/data` payload's newest day -> the machine's bars and per-bar states, with the tape's own guard: a bar
 *  without a FUT leg shifts every index, and a length mismatch is a disagreement, so both withhold with a reason. */
export function mapZone3(D: any): Zone3 {
  const day = D?.days?.[D.days.length - 1]
  if (!day) return { bars: [], buy: null, sell: null, why: D?.live_error || 'no 3-minute session yet', day: '' }
  const bars: TapeBar[] = []
  let skipped = 0
  for (const b of day.bars ?? []) {
    const f = b.fut
    if (!f) { skipped++; continue }
    bars.push({ t: b.t, o: f.o, h: f.h, l: f.l, c: f.c, v: f.v, oi: f.oi, vwap: f.vwap,
                u1: f.u1, d1: f.d1, u2: f.u2, d2: f.d2, u3: f.u3, d3: f.d3, ctx: null, gamma: null, setup: null })
  }
  const align = (raw: unknown, what: string): [RunState[] | null, string] => {
    if (!Array.isArray(raw)) return [null, `this backend publishes no ${what}`]
    if (skipped > 0) return [null, `${skipped} bar(s) lacked a FUT leg, so the ${what} no longer lines up`]
    if (raw.length !== bars.length) return [null, `the backend sent ${raw.length} ${what} slots for ${bars.length} bars`]
    return [raw as RunState[], '']
  }
  const [buy, wb] = align(day.zone_state, '3-minute zone state')
  const [sell, ws] = align(day.zone_state_sell, '3-minute sell-side zone state')
  return { bars, buy, sell, why: wb || ws, day: day.day ?? '' }
}

export function useZone3(index: IndexKey, interval: number, tape: TapeView): Zone3 {
  const own = interval === 3
  const [fetched, setFetched] = useState<Zone3 | null>(null)
  useEffect(() => {
    setFetched(null)
    if (own) return
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/data?idx=${index}&interval=3`)
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const z = mapZone3(await r.json())
        if (alive) setFetched(z)
      } catch (e) {
        if (alive) setFetched((prev) => ({ bars: prev?.bars ?? [], buy: null, sell: null, day: prev?.day ?? '',
          why: `the 3-minute machine could not be read (${e instanceof Error ? e.message : 'no answer'})` }))
      }
    }
    load()
    const id = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [index, own])
  const z3 = useMemo(() => {
    const { zone3On, bands3, zone3State, zone3StateSell } = tape
    if (!zone3On || !bands3 || !zone3State || !zone3StateSell) return null
    return { bars: tape.bars.map((b, i) => ({ ...b, ...(bands3[i] ?? HOLE) })), buy: zone3State, sell: zone3StateSell }
  }, [tape])
  if (own) return { bars: tape.bars, buy: tape.zoneState, sell: tape.zoneStateSell, why: tape.zoneStateWhy, day: tape.day, z3 }
  return fetched ?? { bars: [], buy: null, sell: null, why: 'reading the 3-minute machine…', day: '' }
}

/** The session's floor pivots (P, R1–R3, S1–S3), straight off the payload's `day.pivots`. The MAP levels dedupe them
 *  against legacy levels (29 Sep: S1 22697.2 vanished under PIN 22699), so they are read here once per index and day,
 *  from the smallest payload (15-minute). Reference only: they never decide anything. */
export function usePivots(index: IndexKey, day: string, on: boolean): { label: string; value: number }[] | null {
  const [piv, setPiv] = useState<{ label: string; value: number }[] | null>(null)
  useEffect(() => {
    setPiv(null)
    if (!on || !day) return
    let alive = true
    fetch(`/api/data?idx=${index}&interval=15`).then((r) => r.json()).then((D) => {
      const p = D?.days?.[D.days.length - 1]?.pivots ?? {}
      const out = ['R3', 'R2', 'R1', 'P', 'S1', 'S2', 'S3']
        .filter((k) => typeof p[k] === 'number' && Number.isFinite(p[k])).map((k) => ({ label: k, value: p[k] as number }))
      if (alive) setPiv(out)
    }).catch(() => { if (alive) setPiv([]) })
    return () => { alive = false }
  }, [index, day, on])
  return piv
}
