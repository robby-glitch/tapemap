// THE ONE HOLD POLLER. Every OPEN trade (and the one closed trade a view asks to follow) is read every
// 15 s; the Validate tab and the floating window both render from here, so they can never print
// different words, and a second open trade is never silent (REVIEW P0-7, P1-20). It reads, it never
// decides: the server's hold.py is the rule.
import { useSyncExternalStore } from 'react'
import type { Now, Reading, Trade, Word } from './HoldWindow'
import type { Run } from './parts'

export type Held = Reading & { runs?: Run[] | null; src_data?: Record<string, string>; note?: string }
export type Flip = { t: string; from: Word; to: Word; rows: string[] }
type State = { trades: Trade[]; lots: Record<string, number | null>; reads: Record<string, Held>; flips: Record<string, Flip>
               err: string | null; loaded: boolean }

const POLL_MS = 15000, TIMEOUT_MS = 8000
const RANK: Record<string, number> = { FOLD: 0, 'PATA NAHI': 1, WATCH: 2, HOLD: 3 }
export const rank = (w?: string) => RANK[w ?? 'HOLD'] ?? 3

let s: State = { trades: [], lots: {}, reads: {}, flips: {}, err: null, loaded: false }
const subs = new Set<() => void>(), folds = new Set<(id: string) => void>()
let follow: string | null = null, busy = false, timer: number | undefined
const put = (p: Partial<State>) => { s = { ...s, ...p }; subs.forEach(f => f()) }

/** fetch with an 8 s abort: a slow server never stacks polls or hangs a button (REVIEW P1-18). */
export async function j<T>(url: string, body?: unknown, raw?: string): Promise<T> {
  const ac = new AbortController(), t = setTimeout(() => ac.abort(), TIMEOUT_MS)
  try {
    const r = await fetch(url, {
      signal: ac.signal, ...(body === undefined && raw === undefined ? {} : {
        method: 'POST', headers: { 'Content-Type': raw !== undefined ? 'text/csv' : 'application/json' },
        body: raw !== undefined ? raw : JSON.stringify(body) }) })
    return await r.json()
  } finally { clearTimeout(t) }
}
export const why = (e: unknown) => `could not check — no answer from the server (${(e as Error).name === 'AbortError' ? 'timed out after 8 s' : (e as Error).message})`

// which row changed when the word changed: "PAYERS for → against" (REVIEW §5, a diff instead of a paragraph)
const ROWS: [string, (n: Now) => string][] = [
  ['LINE', n => n.line.blind ? 'blind' : n.line.broken_at ? 'broken' : 'intact'], ['PAYERS', n => n.payers.state],
  ['HOLDERS', n => n.holders.state], ['FLOW', n => n.flow.state], ['TREND', n => n.trend.state]]
function flip(a: Now, b: Now): Flip {
  return { t: b.t, from: a.verdict, to: b.verdict,
           rows: ROWS.filter(([, f]) => f(a) !== f(b)).map(([nm, f]) => `${nm} ${f(a)} → ${f(b)}`) }
}

async function poll() {
  if (busy) return                       // never two polls in flight
  busy = true
  try {
    const r = await j<{ ok: boolean; trades: Trade[]; lots?: Record<string, number | null>; why?: string }>('/api/hold/trades')
    if (!r.ok) { put({ err: r.why || 'could not check — the trades could not be read', loaded: true }); return }
    const ids = r.trades.filter(t => !t.exit_t || t.id === follow).map(t => t.id)
    const reads = { ...s.reads }, flips = { ...s.flips }
    let err: string | null = null
    await Promise.all(ids.map(async id => {
      try {
        const h = await j<Held>(`/api/hold?id=${encodeURIComponent(id)}&rows=brief`)
        const was = reads[id]?.now
        if (was && h.now && was.verdict !== h.now.verdict) {
          flips[id] = flip(was, h.now)
          if (h.now.verdict === 'FOLD') folds.forEach(f => f(id))
        }
        reads[id] = h
      } catch (e) { err = why(e) }           // keep the last good read; the age chip shows it growing old
    }))
    put({ trades: r.trades, lots: r.lots || s.lots, reads, flips, err, loaded: true })
  } catch (e) { put({ err: why(e), loaded: true }) }
  finally { busy = false }
}

function subscribe(f: () => void) {
  subs.add(f)
  if (subs.size === 1) { poll(); timer = window.setInterval(poll, POLL_MS) }
  return () => { subs.delete(f); if (!subs.size) window.clearInterval(timer) }
}
export const useHold = () => useSyncExternalStore(subscribe, () => s)
export const refresh = () => poll()
/** a view reviewing a closed trade asks for it to be read too */
export const followTrade = (id: string | null) => { if (id !== follow) { follow = id; poll() } }
export const onFold = (f: (id: string) => void) => { folds.add(f); return () => { folds.delete(f) } }

/** the trade doors: mark · exit (with its time) · reopen (the 10 s undo). Nothing reaches a broker. */
export async function tradeOp(body: Record<string, unknown>): Promise<{ ok: boolean; why?: string; trades?: Trade[] }> {
  try {
    const r = await j<{ ok: boolean; why?: string; trades?: Trade[] }>('/api/hold/trades', body)
    if (r.ok && r.trades) put({ trades: r.trades })
    poll()
    return r
  } catch (e) { return { ok: false, why: why(e) } }
}

// one tone on a transition into FOLD, default ON (REVIEW P1-13); one AudioContext, unlocked by her first click
let ctx: AudioContext | null = null
if (typeof window !== 'undefined') window.addEventListener('pointerdown', () => { try { ctx ??= new AudioContext(); ctx.resume() } catch { /* no audio */ } }, { once: true })
export function tone() {
  try {
    ctx ??= new AudioContext()
    const o = ctx.createOscillator(), g = ctx.createGain()
    o.frequency.value = 520; g.gain.value = 0.08
    o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + 0.45)
  } catch { /* no audio: the red header still says it */ }
}

/** seconds since the read minute FINISHED (a minute HH:MM is complete at HH:MM+1) */
export function ageSec(asof?: string): number | null {
  if (!asof) return null
  const [h, m] = asof.split(':').map(Number), d = new Date()
  d.setHours(h, m + 1, 0, 0)
  return Math.round((Date.now() - d.getTime()) / 1000)
}
