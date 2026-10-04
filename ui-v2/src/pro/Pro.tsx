// THE DESK, the before-and-after face (orderflow-desk docs/PANEL-DESIGN-2026-10-04/DESIGN.md §1, her "build it" 2026-10-04):
// PEHLE = IF YOU WERE IN, the four ATM legs at her strike, with the strike picker and MARK; BAAD = RECORD. In a trade the
// engine's word is on the GoCharting panel and in the Float (?float=<id> is the Float's body), never here as well. During the
// session PEHLE comes first, after the close BAAD. ?fixture=1 is the dev viewer, bannered, never live.
import { useEffect, useState } from 'react'
import { FIXTURE, INDICES, hms, isDown, legKey, setIdx, setIfin, tradeOp, useStore, type Pick, type Trade } from './api'
import { Abs, Block, FloatBody, IfinCards, clockOf, f2, storyStale, tradeLabel } from './Desk'
import FeedBand from './FeedBand'
import { Slip } from './Mark'
import Record from './Record'
import { applyFixture, loadFixture, moments, pickMoment, type Fx, type FxState } from './fixture'

const q = new URLSearchParams(location.search)
const hhmm = () => new Date().toTimeString().slice(0, 5)

export default function Pro() {
  const st = useStore()
  const [sel, setSel] = useState<string | null>(null)
  const [pick, setPick] = useState<Pick | null>(null)
  const [minute, setMinute] = useState(hhmm())
  useEffect(() => { const t = window.setInterval(() => setMinute(hhmm()), 30000); return () => window.clearInterval(t) }, [])

  // the fixture viewer: ?fixture=1[&state=in|ifin][&at=HH:MM]
  const [fx, setFx] = useState<Fx | null>(null)
  const [fxAt, setFxAt] = useState<{ at: string; state: FxState }>({ at: q.get('at') ?? '', state: q.get('state') === 'in' || q.get('float') ? 'in' : 'ifin' })
  useEffect(() => { if (FIXTURE) loadFixture().then(setFx) }, [])
  useEffect(() => { if (fx) applyFixture(fx, fxAt.at, fxAt.state) }, [fx, fxAt])

  const open = st.trades.filter(t => !t.exit_t)
  const cur: Trade | null = open.find(t => t.id === sel) ?? open[open.length - 1] ?? null
  const fid = q.get('float')
  useEffect(() => { setIfin(!fid && !cur && pick ? pick.k : null) }, [fid, cur, pick?.k])   // flat: the four legs at her strike
  useEffect(() => { setPick(null) }, [st.idx])                                               // another index: its own strikes, from its ATM
  const asof = (cur && st.fold[cur.id]?.asof) ?? st.flat?.asof ?? st.chain?.ts ?? null
  const engine = FIXTURE ? 'fixture' : !st.loaded ? 'checking' : isDown(st.engineWhy) ? 'down' : st.engineWhy ? 'cant' : 'ok'
  const why = st.engineWhy ?? st.tradesWhy

  // ?float=<id>: the floating window's body (Float.tsx) -- the panel's top three lines for that trade, no chrome
  if (fid != null) {
    const t = st.trades.find(x => x.id === fid) ?? cur
    return <div className="pro float"><FeedBand feed={st.feed} compact />
      {t ? <FloatBody t={t} r={st.fold[t.id]} story={st.story} feed={st.feed} why={why} va={st.validate?.trade_id == null || st.validate.trade_id === t.id ? st.validate : null}
          onAck={(lamp, from, to) => { void tradeOp({ op: 'ack', id: t.id, lamp, from, to, t: hms() }) }} />
         : <p className="tradeline"><Abs text={st.loaded ? 'not shown — no open marked trade (the window closes when you are out)' : 'checking…'} /></p>}</div>
  }

  const after = q.get('tab') === 'record' || (!FIXTURE && (minute >= '15:30' || minute < '09:15'))   // ?tab=record: BAAD first
  const fxWhy = FIXTURE && pick && st.chain?.atm != null && pick.k !== st.chain.atm ? `could not check — the fixture holds ${st.chain.atm} only` : null
  const pehle = <section className="pehle" key="pehle">
    <h2 className="sec"><b>PEHLE · IF YOU WERE IN</b>{pick && <> · <span className="num">{st.idx} {pick.k}</span>{st.chain?.atm === pick.k ? ' (ATM)' : ''}</>}
      {st.chain?.ts && <span className="muted num"> · chain {st.chain.ts}{st.chain.spot != null ? ` · spot ${st.chain.spot}` : ''}</span>}
      <span className="muted"> · both legs, both ways · the engine's read for a mark made now · no size, no odds</span></h2>
    {cur ? <p className="intrade"><b>In a trade: {cur.idx} {tradeLabel(cur)} @{f2(cur.p0)} · {cur.t0.slice(0, 5)}</b> — the engine's word is on the GoCharting
      panel, and in the floating window when the chart is hidden. <Abs text="not shown here — IF YOU WERE IN reads again when you are flat" /></p> : <>
      {why && <p className="cant-banner"><Abs text={why} /></p>}
      <Abhi />
      <div className="pgrid">
        <IfinCards legs={fxWhy ? null : st.ifin} k={pick?.k ?? null} story={st.story} pick={pick} why={fxWhy}
          onPick={(ty, side) => pick && setPick({ ...pick, ty, side })} />
        <aside className="side"><Slip idx={st.idx} chain={st.chain} open={open} cur={cur} onSelect={setSel} pick={pick} setPick={setPick}
          leg={pick && !fxWhy ? st.ifin?.[legKey(pick.ty, pick.side)]?.view ?? null : null} lot={st.lot[st.idx] ?? null} /></aside>
      </div></>}
    {cur && <div className="pgrid one"><aside className="side"><Slip idx={st.idx} chain={st.chain} open={open} cur={cur} onSelect={setSel} pick={pick} setPick={setPick} /></aside></div>}
  </section>
  const day0 = q.get('day') ?? (fx ? fx[fxAt.state === 'in' ? 'float' : 'ifin'].day : undefined)   // ?day= opens RECORD on that day
  const baad = <Record key={`baad${day0 ?? ''}`} day0={day0} />

  return <div className="pro">
    {FIXTURE && <div className="fxbar"><span>FIXTURE — not live · real rows: {fxAt.state === 'in' ? 'her 30 Sep 22750 CE (the Float: open ?float=…)' : 'NIFTY 1 Oct, four ATM legs'}</span>
      {fx && moments(fx, fxAt.state).map(m => <button key={m} className={pickMoment(moments(fx, fxAt.state), fxAt.at) === m ? 'on' : ''} onClick={() => setFxAt(f => ({ ...f, at: m }))}>{m}</button>)}
      <span className="gap" />
      {(['ifin', 'in'] as const).map(s => <button key={s} className={fxAt.state === s ? 'on' : ''} onClick={() => setFxAt({ at: '', state: s })}>{s === 'in' ? 'IN A TRADE' : 'IF YOU WERE IN'}</button>)}
    </div>}
    <header className="top">
      <div className="brand">TapeMap <b>DESK</b> <span className="sub">pehle aur baad</span></div>
      <div className="mid">{cur ? <span>{cur.idx}</span>
          : <div className="seg idx" role="group" aria-label="index">{INDICES.map(i => <button key={i} className={st.idx === i ? 'on' : ''} onClick={() => setIdx(i)}>{i}</button>)}</div>}
        <span className="dot">·</span><span className="num">{asof ?? '—'}</span><span className="dot">·</span>
        <span className={`eng ${engine}`}>{engine === 'ok' ? 'engine answering' : engine === 'down' ? 'engine not answering' : engine === 'cant' ? 'engine answering · cannot read yet' : engine === 'fixture' ? 'fixture, not live' : 'checking…'}</span>
        {minute >= '14:45' && minute < '15:30' && <span className="amber">flat by 15:00 · your practice</span>}</div>
      <span className="muted small">in-trade read: GoCharting panel · floating window</span>
    </header>
    <FeedBand feed={st.feed} />
    <main className="desk">{after ? [baad, pehle] : [pehle, baad]}</main>
    <Footer />
  </div>
}

/** the decoder's line for the market now (/api/story): its sentence verbatim, the current chapter, and the market's own
 *  out-of-the-ordinary changes (a new BADA PRINT, a trap state, POWER, an OI step, a new chapter) */
function Abhi() {
  const st = useStore(), s = st.story, now = clockOf(s), stale = storyStale(s, now)
  const hs = !stale ? (s?.highlights ?? []).filter(h => h.block !== 'trade' && h.block !== 'feed') : []
  const [gone, setGone] = useState<string[]>([])
  const live = hs.filter(h => now - h.t_ms <= 180000 && !gone.includes(h.what + h.time))
  const ch = !stale ? s?.chapters?.items?.filter(c => c.current).pop() : undefined
  const text = !s ? 'checking…' : stale ? `could not check — the decoder last posted ${new Date(s.now_ms!).toTimeString().slice(0, 5)} (the GoCharting extension is not posting)`
    : s.sentence ?? `could not check — ${s.sentence_why ?? 'no decoder sentence'}`
  return <Block hs={live} clear={() => setGone(g => [...g, ...live.map(h => h.what + h.time)])} className="abhi">
    <p><b className="k">DECODER · ABHI</b>{s?.asof && !stale && <span className="num muted">{s.asof} · </span>}<Abs text={text} />
      {(s?.chips ?? []).length > 0 && !stale && <span className="chips">{s!.chips!.map(c => <span key={c} className="chip">{c}</span>)}</span>}</p>
    {ch && <p className="muted">abhi ka chapter <b className="num">{ch.start}</b> · {ch.name}{ch.asar != null ? ` · asar ${ch.asar > 0 ? '+' : ''}${ch.asar} so far` : ''}</p>}
  </Block>
}

/** the three absences, always three, never collapsed */
function Footer() {
  const st = useStore(), s = st.story
  const checked = [s?.ok && s.open_prints === 0 && `koi khula BADA PRINT nahi${s.asof ? ` (decoder, ${s.asof})` : ''}`,
                   st.loaded && !st.trades.length && 'aaj koi trade mark nahi'].filter(Boolean) as string[]
  const cant = [st.chain && !st.chain.ok && `the strike picker: ${st.chain.why ?? 'the chain has not loaded'}`,
                s && !s.ok && `the decoder: ${s.sentence_why ?? 'no sentence'}`,
                'a decoder count per leg for IF YOU WERE IN — /api/story counts only an open trade (trade_read); no flat count by side'].filter(Boolean) as string[]
  return <footer className="foot">
    <p><b>checked, nothing</b> · {checked.length ? checked.join(' · ') : 'nothing empty to report — every read above has a value or its reason'}</p>
    <p className="cantl"><b>could not check</b> · {cant.join(' · ')}</p>
    <p className="nsl"><b>not shown</b> · HOLD / FOLD while you are in (the GoCharting panel and the floating window carry it) · NEXT FIGHT and the zone machine (the panel) · the decoder-informed read (P1–P7, unsigned)</p>
  </footer>
}
