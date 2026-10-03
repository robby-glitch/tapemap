// RECORD (6-blueprint.md §3, after 15:30): her trades' word history from /api/fold/record, as counts, never rates.
import { useEffect, useState } from 'react'
import { cc, FIXTURE, record, today, type Rec, type RecTrade, type Word } from './api'
import { Abs, f2, tradeLabel } from './Desk'
import { fixtureRecord, loadFixture } from './fixture'

const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"]
const word = (h: string) => WORDS.find(w => h.toUpperCase().startsWith(w)) ?? h
const fmt = (v: unknown): string => v == null ? '—' : typeof v === 'number' ? f2(v)
  : typeof v === 'object' ? Object.entries(v as Record<string, unknown>).map(([k, x]) => `${k} ${fmt(x)}`).join(' · ') : String(v)

export default function Record() {
  const [day, setDay] = useState(today())             // any day: a past one reads off the files (fold log + her marks)
  const [r, setR] = useState<Rec | null>(null)
  useEffect(() => {
    let live = true
    setR(null)
    if (FIXTURE) { loadFixture().then(v => { if (live) setR(fixtureRecord(v)) }); return () => { live = false } }
    const go = () => record(day).then(x => { if (live) setR(x) })
    go()
    const t = window.setInterval(go, 60000)
    return () => { live = false; window.clearInterval(t) }
  }, [day])
  return <main className="record">
    <p className="tradeline"><b>RECORD</b> · <input type="date" value={day} max={today()} onChange={e => e.target.value && setDay(e.target.value)} aria-label="day" /> · counts, never rates</p>
    {!r ? <p className="muted">checking…</p>
      : !r.ok ? <p><Abs text={cc(r.why, 'the record could not be read')} /></p>
      : !r.trades?.length ? <p><Abs text={`checked — no trades marked ${day === today() ? 'today' : `on ${day}`}`} /></p>
      : r.trades.map(t => <TradeRec key={t.id} t={t} />)}
  </main>
}

// after her exit the engine reads on: what holding would have done, never counted as her trade's words
const after = (x: Word, exit?: string | null) => x.after_exit ?? (!!exit && x.t > exit)
const Words = ({ ws }: { ws: Word[] }) => <ul className="words">{ws.map((x, i) => <li key={i}><span className="t num">{x.t.slice(0, 5)}</span><span><b>{x.headline}</b>{x.clause ? ` · ${x.clause}` : ''}{x.prem != null ? <span className="muted num"> · {f2(x.prem)}{x.pct != null ? ` (${x.pct > 0 ? '+' : ''}${x.pct} %)` : ''}</span> : null}</span></li>)}</ul>

function TradeRec({ t }: { t: RecTrade }) {
  const inWs = t.words.filter(x => !after(x, t.trade.exit_t)), outWs = t.words.filter(x => after(x, t.trade.exit_t))
  const counts = WORDS.map(w => [w, inWs.filter(x => word(x.headline) === w).length] as const)
  return <section className="rec">
    <h2><b>{t.trade.idx} {tradeLabel(t.trade)}</b>{t.trade.src === 'import' && <span className="amber"> · IMPORTED from the tradebook · not marked live · the engine's words replayed on the day's rows</span>}<span className="muted"> · in at {f2(t.trade.p0)} · {t.trade.t0.slice(0, 5)}{t.trade.exit_t ? ` → out ${t.trade.exit_t.slice(0, 5)}` : ' · still marked'}</span></h2>
    <div className="counts">{counts.map(([w, n]) => <span key={w} className={n ? '' : 'none'}><b className="num">{n}</b>{w}</span>)}</div>
    <div className="kvs">
      <div className="kv"><span>exit</span><span className="num">{fmt(t.exit)}</span></div>
      <div className="kv"><span>best</span><span className="num">{fmt(t.best)}</span></div>
      <div className="kv"><span>peak before exit</span><span className="num">{fmt(t.peak_before_exit)}</span></div>
      <div className="kv"><span>given back</span><span className="num">{fmt(t.given_back)}</span></div>
    </div>
    <Words ws={inWs} />
    {outWs.length ? <><p className="muted">AFTER YOUR EXIT · what holding would have done · not your trade, not counted</p><Words ws={outWs} /></> : null}
  </section>
}
