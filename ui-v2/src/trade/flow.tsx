import { useEffect, useState } from 'react'
import type { FlowRow, IndexKey } from '../data'


/**
 * The latest Trending-OI mark, fetched and rendered.
 *
 * Lifted VERBATIM out of TradeTab (2026-08-11) when the One tab needed the
 * same line. Two copies of this fetch would drift in cadence, and two copies
 * of the line would eventually render one mark two ways — the exact failure
 * `crl` exists to prevent one layer down. So it lives once, here, and both
 * tabs mount it.
 */

/**
 * Trending OI for whoever needs the latest mark. Tab-local and on the OI Flow
 * tab's own 15s cadence — /api/oiflow aggregates from the chain poller's
 * in-memory minute grid, so this costs no broker request.
 *
 * interval=5 matches the OI Flow tab's default. Callers have no selector, so
 * the operator cannot re-cut it: pinned at 15 it showed a mark up to fifteen
 * minutes stale, and for the first hour of the session it had one usable row,
 * the 09:15 baseline being zero by construction. Whatever bucket the tab
 * defaults to, this must not be coarser.
 */
export function useFlow(index: IndexKey): { last: FlowRow | null; rows: FlowRow[] | null; why: string } {
  const [rows, setRows] = useState<FlowRow[] | null>(null)
  const [err, setErr] = useState<string>('')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/oiflow?idx=${index}&interval=5`)
        const j = await r.json()
        if (!alive) return
        if (!j.ok) { setErr(j.error || 'flow unavailable'); setRows(null); return }
        setErr('')
        setRows(j.rows || [])
      } catch { if (alive) { setErr('backend unreachable'); setRows(null) } }
    }
    load()
    const id = setInterval(load, 15000)
    return () => { alive = false; clearInterval(id) }
  }, [index])
  const last = rows && rows.length ? rows[rows.length - 1] : null
  const why = err || (rows && !rows.length
    ? 'no flow marks yet — the chain poller has not recorded a clock mark this session'
    : last ? '' : 'no flow rows yet')
  // `rows` is additive (2026-08-11): the Glass board draws the last few
  // buckets as history, not just the latest mark. Returning the array the
  // hook already holds is what keeps that from becoming the second copy of
  // this fetch the header above forbids. Existing callers destructure `last`
  // and are untouched.
  return { last, rows, why }
}
