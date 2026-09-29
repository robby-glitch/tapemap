// The pro screen's shell: header, DESK (the face + the slip) and RECORD. ?fixture=1 is the dev viewer, bannered, never live.
import { useEffect, useState } from 'react'
import { FIXTURE, IDX, setIfin, useStore, type Pick, type Trade } from './api'
import { FlatFace, IfinFace, InTrade, Premium, Words } from './Desk'
import FeedBand from './FeedBand'
import { Slip } from './Mark'
import Record from './Record'
import { applyFixture, loadFixture, moments, pickMoment, type Views } from './fixture'

const q = new URLSearchParams(location.search)
const hhmm = () => new Date().toTimeString().slice(0, 5)
type FxState = 'in' | 'flat' | 'ifin'

export default function Pro() {
  const st = useStore()
  const [tab, setTab] = useState<'DESK' | 'RECORD'>(q.get('tab') === 'record' ? 'RECORD' : 'DESK')
  const [sel, setSel] = useState<string | null>(null)
  const [pick, setPick] = useState<Pick | null>(null)
  const [ifinOn, setIfinOn] = useState(q.get('state') === 'ifin')
  const [minute, setMinute] = useState(hhmm())
  useEffect(() => { const t = window.setInterval(() => setMinute(hhmm()), 30000); return () => window.clearInterval(t) }, [])

  // the fixture viewer: ?fixture=1[&at=11:16][&state=in|flat|ifin]
  const [views, setViews] = useState<Views | null>(null)
  const [fx, setFx] = useState<{ at: string; state: FxState }>({ at: q.get('at') ?? '', state: (['flat', 'ifin'].includes(q.get('state') ?? '') ? q.get('state') : 'in') as FxState })
  useEffect(() => { if (FIXTURE) loadFixture().then(setViews) }, [])
  useEffect(() => { if (views) applyFixture(views, fx.at, fx.state === 'in' ? 'in' : 'flat') }, [views, fx])

  const open = st.trades.filter(t => !t.exit_t)
  const cur: Trade | null = open.find(t => t.id === sel) ?? open[open.length - 1] ?? null
  const read = cur ? st.fold[cur.id] : undefined
  useEffect(() => { setIfin(!cur && ifinOn && pick ? pick : null) }, [cur, ifinOn, pick])   // flat: the slip's strike is what IF YOU WERE IN reads
  const asof = read?.asof ?? read?.view?.ts ?? st.flat?.asof ?? null
  const engine = FIXTURE ? 'fixture' : !st.loaded ? 'checking' : st.engineWhy ? 'down' : 'ok'
  const why = st.engineWhy ?? st.tradesWhy
  const ifinView = !cur && ifinOn && st.ifin?.ok && st.ifin.view?.headline != null && pick ? st.ifin.view : null

  // ?float=<id>: the floating window's body (Float.tsx) -- the same face and premium for that trade, compact, no chrome
  const fid = q.get('float')
  if (fid != null) {
    const t = st.trades.find(x => x.id === fid) ?? cur, r = t ? st.fold[t.id] : undefined
    return <div className="pro float"><FeedBand feed={st.feed} compact />{t ? <><InTrade t={t} r={r} why={why} />
      {r?.ok && r.view?.headline != null && <Premium v={r.view} ty={t.side} />}</> : <FlatFace f={st.flat} why={why} />}</div>
  }

  return <div className="pro">
    {FIXTURE && <div className="fxbar"><span>FIXTURE — not live · her put, 2026-09-28</span>
      {views && moments(views).map(m => <button key={m} className={pickMoment(views, fx.at) === m ? 'on' : ''} onClick={() => setFx(f => ({ ...f, at: m }))}>{m}</button>)}
      <span className="gap" />
      {(['in', 'flat', 'ifin'] as const).map(s => <button key={s} className={fx.state === s ? 'on' : ''} onClick={() => { setFx(f => ({ ...f, state: s })); setIfinOn(s === 'ifin') }}>
        {s === 'in' ? 'IN A TRADE' : s === 'flat' ? 'FLAT' : 'IF YOU WERE IN'}</button>)}
    </div>}
    <header className="top">
      <div className="brand">TapeMap <b>DESK</b></div>
      <div className="mid"><span>{IDX}</span><span className="dot">·</span><span className="num">{asof ?? '—'}</span><span className="dot">·</span>
        <span className={`eng ${engine}`}>{engine === 'ok' ? 'engine answering' : engine === 'down' ? 'engine not answering' : engine === 'fixture' ? 'fixture, not live' : 'checking…'}</span>
        {minute >= '14:45' && minute < '15:30' && <span className="amber">flat by 15:00 · your practice</span>}</div>
      <nav>{(['DESK', 'RECORD'] as const).map(t => <button key={t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{t}</button>)}</nav>
    </header>
    <FeedBand feed={st.feed} />
    {tab === 'RECORD' ? <Record /> : <main className="desk">
      <section className="face">
        {cur ? <InTrade t={cur} r={read} why={why}
          /> : ifinOn && pick ? <IfinFace r={st.ifin} pick={pick} why={why} /> : <FlatFace f={st.flat} why={why} />}
      </section>
      <aside className="side">
        <Slip chain={st.chain} open={open} cur={cur} onSelect={setSel} pick={pick} setPick={setPick} />
        {!cur && <button className={`toggle ${ifinOn ? 'on' : ''}`} onClick={() => setIfinOn(v => !v)}>{ifinOn ? '◂ back to FLAT' : 'IF YOU WERE IN ▸'}</button>}
        {cur && read?.ok && read.view?.headline != null && <Premium v={read.view} ty={cur.side} />}
        {ifinView && pick && <Premium v={ifinView} ty={pick.ty} />}
        {cur && <Words w={read?.words} />}
      </aside>
    </main>}
  </div>
}
