// ui-v2/src/trade/tape.ts
import { useEffect, useState } from 'react'
import type { IndexKey } from '../data'

/**
 * `/api/tape` — the ladder record and what the server reads off it (spec
 * 2026-09-19-orderflow-levels §D). One fetch, one cadence, any number of
 * mounts — the `./footprint` shape. This file computes NOTHING: levels, flags
 * and marks arrive computed and tagged; the overlay draws them.
 *
 * 30 s, not faster: levels move once per 5-minute bar, and 30 s is the cadence
 * this endpoint family already settled on (footprint.ts). The poll dies with
 * the tab.
 */
export interface TapeLadderRow { p: number; b: number; s: number; bt: number; st: number }
export interface TapeStack { side: 'buy' | 'sell'; low: number; high: number; run: number }
export interface TapeBarRow {
  t: number; o: number; h: number; l: number; c: number
  vol: number; buy: number; sell: number; delta: number; cvd: number
  oi: number | null; fromTicks: boolean
  ladder: TapeLadderRow[] | null
  stacks: TapeStack[] | null; unfinished_high: boolean | null; unfinished_low: boolean | null; poc: number | null
}
export interface TapeNode { p: number; vol: number; kind: 'HVN' | 'LVN' }
export interface TapeLevels {
  session: { poc: number; vah: number; val: number } | null
  prior: { day: string; poc: number; vah: number; val: number }[]
  prior_why: string | null
  naked: { day: string; poc: number; touched_t: number | null }[]
  nodes: TapeNode[]
  tag: 'M'
  why: string | null
}
export interface TapeMark {
  t: number; kind: string; side: -1 | 0 | 1 | null; p: number | null; size: number | null
  src: 'ofd' | 'tm'; why?: string; tag?: 'I'
}
export interface TapeReply {
  ok: true; idx: string; day: string; interval: 5; src: 'live' | 'file'; tag: 'M'
  rowSize: number | null; rowAnchor: number; lot: number | null
  bars: TapeBarRow[]
  forming: TapeBarRow | null; forming_why: string | null
  ladder_why: string | null
  levels: TapeLevels
  marks: { ofd: TapeMark[]; tm: TapeMark[]; tm_why: string | null }
  why: null
}

export function useTape(index: IndexKey): { reply: TapeReply | null; why: string } {
  const [reply, setReply] = useState<TapeReply | null>(null)
  const [why, setWhy] = useState<string>('prints record abhi padha ja raha hai')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/tape?idx=${index}`)
        const j = await r.json()
        if (!alive) return
        if (!j.ok) {
          setWhy(`prints record padha nahi ja saka — ${j.why || 'server ne wajah nahi batayi'}`)
          setReply(null); return
        }
        setReply(j as TapeReply)
        setWhy('')
      } catch (e) {
        // the backend not answering is "could not check", not "no prints today"
        if (alive) { setWhy(`prints record padha nahi ja saka — backend ne jawab nahi diya (${String(e)})`); setReply(null) }
      }
    }
    // the first read ALWAYS happens; the hidden-tab guard is on the repeat only (footprint.ts measured why)
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 30000)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])
  return { reply, why }
}
