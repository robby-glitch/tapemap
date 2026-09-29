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
export interface TapeStack { side: 'buy' | 'sell'; low: number; high: number; run: number }
export interface TapeBarRow {
  t: number; o: number; h: number; l: number; c: number
  vol: number; buy: number; sell: number; delta: number; cvd: number
  oi: number | null; fromTicks: boolean
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
  src: 'ofd' | 'tm' | 'ux'; why?: string; tag?: 'I'
}
export interface TapeReply {
  ok: true; idx: string; day: string; interval: 5; src: 'live' | 'file'; tag: 'M'
  rowSize: number | null; rowAnchor: number; lot: number | null
  bars: TapeBarRow[]
  forming: TapeBarRow | null; forming_why: string | null
  ladder_why: string | null
  levels: TapeLevels
  marks: { ofd: TapeMark[]; ofd_why: string | null; tm: TapeMark[]; tm_why: string | null }
  ux: TapeUx
  why: null
}

export interface UxBarRow extends TapeBarRow {
  unknown: number
  unpriced: number
  exact: number | null; reconstructed: number | null; hidden: number | null
  partial: boolean | null; partial_why: string | null
}
export interface UxRun {
  t: number; kind: 'run'; side: -1 | 1; n: number; qty: number; thr: number; p: number | null
  from_t: number; to_t: number; src: 'ux'; tag: 'I'; why: string; unit?: 'lots' | 'units'
}
export interface UxAgree {
  tag: 'M'
  bars_joined: number; bars_ofd_only: number; bars_ux_only: number
  poc_rows_median: number | null; poc_rows_median_why: string | null
  poc_within_1: number | null; poc_within_1_why: string | null
  delta_sign_agree: number | null; delta_sign_agree_why: string | null
  vol_ratio_median: number | null; vol_ratio_median_why: string | null
  va_overlap: number | null; va_overlap_why: string | null
  hvn_jaccard: number | null; hvn_jaccard_why: string | null
  lvn_jaccard: number | null; lvn_jaccard_why: string | null
  exact_frac: number | null; exact_frac_why: string | null
  hidden_frac: number | null; hidden_frac_why: string | null
  unknown_frac: number | null; unknown_frac_why: string | null
  unpriced_frac: number | null; unpriced_frac_why: string | null
}
export interface UxImpact { lambda: number | null; lots_per_tick: number | null; pct: number | null; n: number; why: string | null; tag: 'I' }
export interface TapeUx {
  src: 'ux'; tag: 'I'
  bars: UxBarRow[]; forming: UxBarRow | null
  levels: { session: { poc: number; vah: number; val: number } | null; nodes: TapeNode[]; why: string | null }
  marks: { runs: UxRun[]; runs_why: string | null }
  impact: UxImpact | null
  agree: UxAgree | null; agree_why: string | null
  book_from: string | null; frames_per_s: number | null; lot: number | null; lot_src: string | null
  lot_why: string | null
  rebuild_why: string | null
  why: string | null
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
