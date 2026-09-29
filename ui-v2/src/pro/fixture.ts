// DEV ONLY: pro.html?fixture=1. Real engine output for her put on 2026-09-28 (docs/pro-tool/fixtures/fold_view_H2_slim.json
// with the nested event rows stripped), pushed into the store in place of the poller so the screen can be judged before the
// endpoints exist. Bannered FIXTURE on screen; the live page never reads it.
import { put, type ChainLite, type Flat, type FoldRead, type Rec, type Trade, type View, type Word } from './api'

export type Views = Record<string, View>
export const FX_TRADE: Trade = { id: 'NIFTY-23000PE-long-093027', idx: 'NIFTY', k: 23000, side: 'PE', role: 'long', t0: '09:30:27', p0: 120.4, qty: 0, exit_t: null }
export const loadFixture = async (): Promise<Views> => (await import('./fixture.json')).default as unknown as Views
export const moments = (v: Views) => Object.keys(v)
export const pickMoment = (v: Views, at: string) => moments(v).find(k => k.startsWith(at)) ?? moments(v)[moments(v).length - 1]
const L = (oi: number | null) => oi == null ? '—' : `${(oi / 1e5).toFixed(1)}L`
const words = (v: Views, upto: string): Word[] => moments(v).filter(k => k <= upto).map(k => ({ t: v[k].ts, headline: v[k].headline ?? '', clause: v[k].clause }))

export function applyFixture(views: Views, at: string, state: 'in' | 'flat') {
  const key = pickMoment(views, at), v = views[key]
  const atm = Math.round((v.F ?? 22900) / 50) * 50
  const chain: ChainLite = { ok: true, ts: v.ts, spot: v.fut ?? undefined, atm, expiry: '2026-09-29',
                             strikes: Array.from({ length: 13 }, (_, i) => ({ k: atm + (i - 6) * 50, ce: null, pe: null })) }
  // the fixture holds no flat read: NEXT FIGHT is this moment's give-up (above) and wall ahead (below) in fold.flat's wording;
  // THE DAY counts the fixture's own fights (09:29 S, 09:48 B, 11:04 S, 13:07 S, 14:37 S) and says what it cannot know
  const flat: Flat = {
    ok: true, asof: v.ts, rows: v.rows, F: v.F ?? undefined,
    next_fight: {
      above: v.G ? { px: v.G.px, what: v.G.why ?? '', confirm: `lifts at ${v.G.px}–${v.G.px + 5} followed by price and ${v.W?.k} ${v.W?.side} off its peak · VPIN turning buyers' way: calls` } : null,
      below: v.A?.px != null ? { px: v.A.px, what: `${v.A.k} ${v.A.side} writers (${L(v.A.oi)})`, confirm: `hits at ${v.A.px - 5}–${v.A.px} followed by price and ${v.A.k} ${v.A.side} off its peak · VPIN turning sellers' way: puts` } : null },
    day: "sellers' day (4 fights to 1) [M] · could not check: the fixture carries no volume profile",
  }
  if (state === 'in') {
    const read: FoldRead = { ok: true, id: FX_TRADE.id, trade: FX_TRADE, view: v, words: words(views, key), asof: v.ts }
    put({ loaded: true, trades: [FX_TRADE], fold: { [FX_TRADE.id]: read }, flat: null, ifin: null, chain, engineWhy: null, tradesWhy: null })
  } else {
    put({ loaded: true, trades: [], fold: {}, flat, ifin: { ok: true, view: v }, chain, engineWhy: null, tradesWhy: null })
  }
}

export function fixtureRecord(views: Views): Rec {
  const ks = moments(views), last = views[ks[ks.length - 1]]
  return { ok: true, trades: [{ id: FX_TRADE.id, trade: FX_TRADE, words: words(views, ks[ks.length - 1]), exit: null,
                                best: Math.max(...ks.map(k => views[k].prem.peak ?? 0)), peak_before_exit: last.prem.peak, given_back: last.prem.given_back }] }
}
