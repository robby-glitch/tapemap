import { useEffect, useState } from 'react'
import { MONO } from '../theme'
import type { palette } from '../theme'
// The strip and SetupCheck's OI receipt format the same figures with `crl`.
// One formatter, so two surfaces can never disagree about one number.
import { crl } from './ZoneRead'
import type { FlowRow, IndexKey } from '../data'

type Pal = ReturnType<typeof palette>

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

/**
 * The one-line rendering of that mark. The mark time is ALWAYS shown (the row
 * is the chain AS AT that clock mark, not now), and while replaying the line
 * dims and says it is live rather than pretending it scrubbed.
 *
 * Absence is a sentence, never a blank: "Trending OI nahi mili — {why}".
 */
export function FlowLine({ pal, flow, flowWhy, replaying }: {
  pal: Pal
  flow: FlowRow | null
  flowWhy: string
  /** True while the replay cursor is set. This line does not scrub — it says so. */
  replaying: boolean
}) {
  return (
    <div style={{
      fontFamily: MONO, fontSize: 11, paddingLeft: 2,
      color: pal.textSecondary, opacity: replaying ? 0.55 : 1,
    }}>
      {flow ? (
        <>
          <span style={{ fontWeight: 700, color: pal.textMuted }}>OI {flow.time}</span>
          {' · CALL '}{crl(flow.call)}
          {' · PUT '}{crl(flow.put)}
          {' · DIFF '}{crl(flow.diff)} {flow.diff >= 0 ? 'PUT' : 'CALL'}-heavy{' '}
          {Math.abs(flow.strength * 100).toFixed(0)}%
          {flow.pcr != null && <>{' · PCR '}{flow.pcr.toFixed(2)}</>}
          {flow.chg_dir != null && (
            <>{' · Δ '}{flow.chg_dir >= 0 ? '▲' : '▼'}{crl(Math.abs(flow.chg_dir)).slice(1)}</>
          )}
          {flow.brk && (
            <span style={{ color: pal.accent, fontWeight: 700 }}>
              {' · '}{flow.brk} {flow.brk_px != null ? flow.brk_px.toFixed(1) : ''}
            </span>
          )}
          {replaying && (
            <span style={{ fontStyle: 'italic', color: pal.textMuted }}>
              {' · live flow — replay cursor ke saath aligned nahi'}
            </span>
          )}
        </>
      ) : (
        <span style={{ fontStyle: 'italic', color: pal.textMuted }}>
          Trending OI nahi mili — {flowWhy}
        </span>
      )}
    </div>
  )
}
