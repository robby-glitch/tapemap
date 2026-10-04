// DEV ONLY: pro.html?fixture=1[&state=in|ifin][&at=HH:MM]. Real data, pushed into the store in place of the poller, bannered
// FIXTURE on screen; the live page never reads it. Built read-only from data/ (2026-10-04):
//  in:   her 30 Sep 22,750 CE long -- the engine's own logged rows (data/fold, src marked) at four moments, and /api/story at
//        each moment: story.compose_all over the extension's decoder.js run on the recorded bars (orderflow-desk/test).
//  ifin: NIFTY 1 Oct 12:08 / 12:11 / 12:17 -- fold.ifin on the day's rows for the four ATM legs (the prior sessions pooled as
//        fold_live pools them), and /api/story flat at each moment, the same way.
import { put, type ChainLite, type FoldRead, type Ifin, type Story, type Trade, type View } from './api'

type FxFloat = { day: string; trade: Trade; moments: Record<string, { view: View; story: Story }> }
type FxIfin = { day: string; idx: string; moments: Record<string, { k: number; spot: number; chain_ts: string
                                                                  strikes: ChainLite['strikes']; legs: Record<string, Ifin>; story: Story }> }
export type Fx = { float: FxFloat; ifin: FxIfin }
export type FxState = 'in' | 'ifin'
export const loadFixture = async (): Promise<Fx> => (await import('./fixture.json')).default as unknown as Fx
export const moments = (fx: Fx, s: FxState) => Object.keys(s === 'in' ? fx.float.moments : fx.ifin.moments)
export const pickMoment = (ms: string[], at: string) => ms.find(k => k.startsWith(at)) ?? ms[ms.length - 1]

export function applyFixture(fx: Fx, at: string, s: FxState) {
  const key = pickMoment(moments(fx, s), at)
  if (s === 'in') {
    const m = fx.float.moments[key], t = fx.float.trade
    const read: FoldRead = { ok: true, id: t.id, trade: t, view: m.view, asof: m.view.ts }
    put({ loaded: true, trades: [t], fold: { [t.id]: read }, flat: null, ifin: null, chain: null, story: m.story, feed: null, engineWhy: null, tradesWhy: null })
  } else {
    const m = fx.ifin.moments[key]
    const chain: ChainLite = { ok: true, ts: m.chain_ts, spot: m.spot, atm: m.k, strikes: m.strikes }
    put({ loaded: true, trades: [], fold: {}, flat: null, ifin: m.legs, chain, story: m.story, feed: null, engineWhy: null, tradesWhy: null })
  }
}
