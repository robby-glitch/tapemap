// DEV ONLY: pro.html?fixture=1[&state=in|ifin][&at=HH:MM]. Real data, pushed into the store in place of the poller, bannered
// FIXTURE on screen; the live page never reads it. Built read-only from data/ (2026-10-04):
//  in:   her 30 Sep 22,750 CE long -- the engine's own logged rows (data/fold, src marked) at four moments, and /api/story at
//        each moment: story.compose_all over the extension's decoder.js run on the recorded bars (orderflow-desk/test).
//  ifin: NIFTY 1 Oct 12:08 / 12:11 / 12:17 -- fold.ifin on the day's rows for the four ATM legs (the prior sessions pooled as
//        fold_live pools them), and /api/story flat at each moment, the same way.
//  in also carries /api/validate at each moment: validate_live.read over the same rows (the GoCharting round's module).
//  receipts: her Sep 21-24 tradebook imported into a TEMP COPY of data/day_state (never the live folder), receipts.build
//        over that copy with the real chain files, and RECORD for 24 Sep off the copy. Her broker trade / order ids and
//        per-fill rows are stripped; the trips keep their entry / exit times and prices (as the 30 Sep / 1 Oct rows do).
import { put, type ChainLite, type FoldRead, type Ifin, type Rec, type Receipts, type Story, type Trade, type Validate, type View } from './api'

type FxFloat = { day: string; trade: Trade; moments: Record<string, { view: View; story: Story; validate: Validate }> }
type FxIfin = { day: string; idx: string; moments: Record<string, { k: number; spot: number; chain_ts: string
                                                                  strikes: ChainLite['strikes']; legs: Record<string, Ifin>; story: Story }> }
export type Fx = { float: FxFloat; ifin: FxIfin; receipts: { day: string; receipts: Receipts; record: Rec } }
export type FxState = 'in' | 'ifin'
export const loadFixture = async (): Promise<Fx> => (await import('./fixture.json')).default as unknown as Fx
export const moments = (fx: Fx, s: FxState) => Object.keys(s === 'in' ? fx.float.moments : fx.ifin.moments)
export const pickMoment = (ms: string[], at: string) => ms.find(k => k.startsWith(at)) ?? ms[ms.length - 1]

export function applyFixture(fx: Fx, at: string, s: FxState) {
  const key = pickMoment(moments(fx, s), at)
  if (s === 'in') {
    const m = fx.float.moments[key], t = fx.float.trade
    const read: FoldRead = { ok: true, id: t.id, trade: t, view: m.view, asof: m.view.ts }
    put({ loaded: true, trades: [t], fold: { [t.id]: read }, flat: null, ifin: null, chain: null, story: m.story, validate: m.validate, feed: null, engineWhy: null, tradesWhy: null })
  } else {
    const m = fx.ifin.moments[key]
    const chain: ChainLite = { ok: true, ts: m.chain_ts, spot: m.spot, atm: m.k, strikes: m.strikes }
    put({ loaded: true, trades: [], fold: {}, flat: null, ifin: m.legs, chain, story: m.story, validate: null, feed: null, engineWhy: null, tradesWhy: null,
          lot: { NIFTY: 65, BANKNIFTY: 30, SENSEX: 20 } })
  }
}
