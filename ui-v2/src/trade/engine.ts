// The rev 6 engine's reads for the Trade tab (docs/pro-tool/API-v3.md). Nothing here decides anything: fold.py owns
// every read, the tab draws it. In-trade words come from the DESK's own shared poller (`useStore`, imported, never
// edited), so this tab, the floating window and the DESK show one word from one poll. The flat read is polled here
// per index, because the DESK's poller is fixed to NIFTY.
import { useEffect, useState } from 'react'
import { j } from '../hold/store'
import { useStore, notAnswering } from '../pro/api'
import type { Flat, FoldRead, View } from '../pro/api'

export { useStore }

/** One chart mark from the engine, frozen at birth (fold.py `_mark` / the wall namings). `t` is epoch ms. */
export interface EngMark {
  kind: string            // wall · won · absorbed · trapped · released
  t: number
  ts: string
  px: number              // for a wall: the strike at K + basis, already placed by the engine
  side: number            // who the mark is about: +1 buyers, -1 sellers
  by?: string             // book · price (won by price is [I]) · oi
  lots?: number | null
  k?: number
  ty?: string
  disputed?: boolean
  text: string
}
export type FlatRead = Flat & { marks?: EngMark[]; basis?: number | null }

/** The in-trade view with the fields API-v3's type does not list. `A.state`, `W.px` and `G_steps` arrive with the
 *  server's D.14 fields; the face works without them. */
export type TradeView = View & {
  units?: { basis?: number | null; w?: number | null }
  oi_event?: { t: string; pct: number; k?: number; side?: string } | null
  G_steps?: { t: string; px: number; why?: string; refused?: boolean }[] | null
}

const POLL_MS = 10_000

/** `/api/fold/flat?idx=` every 10 s. The last good read is kept; `why` says when the engine stopped answering (the
 *  read under it is then shown as it last was) or why it could not read at all. */
export function useFlat(index: string): { flat: FlatRead | null; why: string | null } {
  const [flat, setFlat] = useState<FlatRead | null>(null)
  const [why, setWhy] = useState<string | null>('checking…')
  useEffect(() => {
    let alive = true
    setFlat(null)
    setWhy('checking…')
    const load = async () => {
      try {
        const r = await j<FlatRead>(`/api/fold/flat?idx=${index}`)
        if (!alive) return
        if (r.ok) { setFlat(r); setWhy(null) } else { setFlat(null); setWhy(r.why || 'could not check — the engine gave no reason') }
      } catch {
        if (alive) setWhy((w) => (w && w !== 'checking…' ? w : notAnswering()))
      }
    }
    load()
    const id = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])
  return { flat, why }
}

/** `?tradeview=<id>`: a GET-only review of one marked trade's view (frozen at her exit when she has left). It never
 *  writes to her record. Null id = not asked for. */
export function useTradeView(id: string | null): FoldRead | null {
  const [r, setR] = useState<FoldRead | null>(null)
  useEffect(() => {
    if (!id) { setR(null); return }
    let alive = true
    const load = async () => {
      try { const x = await j<FoldRead>(`/api/fold?id=${encodeURIComponent(id)}`); if (alive) setR(x) }
      catch { if (alive) setR({ ok: false, why: notAnswering() }) }
    }
    load()
    const t = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(t) }
  }, [id])
  return r
}

export const TRADEVIEW = new URLSearchParams(location.search).get('tradeview')
