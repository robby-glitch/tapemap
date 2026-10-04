// BAAD · RECORD (orderflow-desk docs/PANEL-DESIGN-2026-10-04/DESIGN.md §1): her trades on any day (/api/fold/record: her
// marks, or the tradebook imported after the day), the engine's word during the trade and at her exit, and what the engine
// and the premium did after. A row carries the grammar's mark where a RED (FOLD / PAST GIVE-UP) or an AMBER (a read going
// to CAN'T CHECK) happened while she was in. Rows and counts, never a rate. Click a row for every word.
import { Fragment, useEffect, useState } from 'react'
import { cc, record, today, useStore, type Rec, type RecTrade, type Word } from './api'
import { Abs, f2, pct, tradeLabel, wordOf } from './Desk'

const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"]
const SHORT: Record<string, string> = { HOLD: 'HOLD', 'PAST GIVE-UP': 'PGU', FOLD: 'FOLD', "CAN'T CHECK": "CAN'T" }
type Num = { t?: string | null; prem?: number | null; pct?: number | null; at?: string | null }
// after her exit the engine reads on: what holding would have done, never counted as her trade's words
const after = (x: Word, exit?: string | null) => x.after_exit ?? (!!exit && x.t > exit)
const at = (w?: Word) => w ? <><span className="num">{w.t.slice(0, 5)}</span>{w.prem != null && <span className="num"> @{f2(w.prem)}{w.pct != null ? ` (${pct(w.pct)})` : ''}</span>}</> : null

export default function Record({ day0 }: { day0?: string }) {
  const [day, setDay] = useState(day0 ?? today())     // any day: a past one reads off the files (fold log + her marks)
  const [r, setR] = useState<Rec | null>(null)
  useEffect(() => {
    let live = true
    setR(null)
    const go = () => record(day).then(x => { if (live) setR(x) })   // read-only, the fixture viewer too: the record is files
    go()
    const t = window.setInterval(go, 60000)
    return () => { live = false; window.clearInterval(t) }
  }, [day])
  const ts = r?.ok ? r.trades ?? [] : []
  const imp = ts.filter(t => t.trade.src === 'import').length
  return <section className="baad">
    <h2 className="sec"><b>BAAD · RECORD</b> <input type="date" value={day} max={today()} onChange={e => e.target.value && setDay(e.target.value)} aria-label="day" />
      {ts.length > 0 && <span> · {ts.length} trade{ts.length > 1 ? 's' : ''}{imp ? ` · ${imp === ts.length ? 'all' : imp} imported from the tradebook (replayed, not marked live)` : ''}</span>}
      <span className="muted"> · the engine's word during, at your exit and after · counts, never rates</span></h2>
    {!r ? <p className="muted">checking…</p>
      : !r.ok ? <p><Abs text={cc(r.why, 'the record could not be read')} /></p>
      : !ts.length ? <p><Abs text={`checked — no trades marked ${day === today() ? 'today' : `on ${day}`}`} /></p>
      : <table className="tbl">
        <thead><tr><th>#</th><th>trade</th><th>in → out</th><th>during your trade</th><th>engine at your exit</th><th>after your exit · the engine's own path</th></tr></thead>
        <tbody>{ts.map((t, i) => <Row key={t.id} n={i + 1} t={t} />)}</tbody>
      </table>}
    <Kahani day={day} />
    <p className="note"><b>not shown</b> · the decoder-informed read at exit (P1–P7, a proposal, unsigned) and the kill clocks — no server field yet ·
      <b> could not check</b> · the premium at +20 / +40 min after your exit — the record carries the engine's word changes, not a minute series</p>
  </section>
}

/** AAJ KI KAHANI after the close: the day's chapters as the decoder composed them (/api/story), for the day it carries */
function Kahani({ day }: { day: string }) {
  const s = useStore().story, items = s?.day === day ? s.chapters?.items ?? [] : []
  if (!items.length) return <p className="note"><Abs text={s?.day === day && s.chapters?.items_why ? cc(s.chapters.items_why)
    : `not shown — the day's chapters for ${day}: /api/story carries only the session the extension last posted`} /></p>
  return <><h3 className="sub">AAJ KI KAHANI · {day} · {items.length} chapters{s?.chapters?.trap_why ? <span className="muted"> · {s.chapters.trap_why}</span> : null}</h3>
    <table className="tbl kah"><tbody>{items.map(c => <tr key={c.start} className={c.current ? 'cur' : ''}>
      <td className="num">{c.start}–{c.end}</td><td><b>{c.name}</b></td><td>{c.sentence}</td>
      <td>{c.chips.map(x => <span key={x} className="chip">{x}</span>)}</td>
      <td className="num">{c.asar != null ? `asar ${c.asar > 0 ? '+' : ''}${c.asar}${c.current ? ' so far' : ''}` : <Abs text="could not check — no closed bar inside it" />}</td></tr>)}</tbody></table></>
}

function Row({ n, t }: { n: number; t: RecTrade }) {
  const [open, setOpen] = useState(false)
  const ex = t.trade.exit_t, inWs = t.words.filter(x => !after(x, ex)), outWs = t.words.filter(x => after(x, ex))
  const first = (ws: Word[], w: string) => ws.find(x => wordOf(x.headline) === w)
  const red = [first(inWs, 'PAST GIVE-UP'), first(inWs, 'FOLD')].filter(Boolean) as Word[]
  const amber = first(inWs, "CAN'T CHECK")
  const tier = red.length ? 'red' : amber ? 'amber' : ''
  const counts = WORDS.map(w => [w, inWs.filter(x => wordOf(x.headline) === w).length] as const).filter(([, c]) => c)
  const last = inWs[inWs.length - 1], exit = t.exit as Num | null
  const pgu = first(outWs, 'PAST GIVE-UP'), fold = first(outWs, 'FOLD')
  const priced = outWs.filter(x => x.pct != null)
  const best = priced.reduce<Word | undefined>((a, x) => !a || x.pct! > a.pct! ? x : a, undefined)
  const worst = priced.reduce<Word | undefined>((a, x) => !a || x.pct! < a.pct! ? x : a, undefined)
  return <Fragment>
    <tr className={`rr ${tier ? `hi-${tier}` : ''} ${open ? 'open' : ''}`} onClick={() => setOpen(o => !o)} title="click: every word, in and after">
      <td className="num">{n}</td>
      <td><b>{t.trade.idx} {t.trade.k} {t.trade.side}</b><br /><span className="muted">{tradeLabel(t.trade).split(' ')[0]} @{f2(t.trade.p0)}</span>
        {t.trade.src === 'import' && <span className="src">import</span>}</td>
      <td className="num">{t.trade.t0.slice(0, 8)} →<br />{ex ? ex.slice(0, 8) : <span className="muted">still marked</span>}</td>
      <td>{t.why ? <Abs text={cc(t.why)} /> : <>
        <span className="cts">{counts.map(([w, c]) => <span key={w}><b className="num">{c}</b> {SHORT[w]}</span>)}</span>
        {red.map(w => <p key={w.t + w.headline} className="kya red"><b>kya badla</b> · {at(w)} · {w.headline}</p>)}
        {amber && <p className="kya amber"><b>kya badla</b> · {at(amber)} · read went CAN'T CHECK</p>}</>}</td>
      <td>{last ? <><b>{wordOf(last.headline)}</b>{last.headline.length > wordOf(last.headline).length ? last.headline.slice(wordOf(last.headline).length) : ''}
        {last.clause ? <span> · {last.clause}</span> : null}</> : <Abs text="could not check — no word logged while you were in" />}
        {exit?.prem != null && <><br /><span className="muted num" title="the premium on the engine's last read before your exit (not your fill)">engine's last read{exit.at ? ` ${exit.at}` : ''} · {f2(exit.prem)}{exit.pct != null ? ` (${pct(exit.pct)})` : ''}</span></>}</td>
      <td>{!ex ? <span className="muted">—</span> : !outWs.length ? <Abs text="checked — the engine logged no word after your exit" /> : <>
        {pgu && <span className="pth">PGU {at(pgu)}</span>}{fold && <span className="pth">FOLD {at(fold)}</span>}
        {!pgu && !fold && <span className="pth">no PGU, no FOLD after</span>}
        {priced.length > 1 && <><br /><span className="muted">at the engine's word changes: best {at(best)} · worst {at(worst)}</span></>}</>}</td>
    </tr>
    {open && <tr className="ws"><td /><td colSpan={5}>
      <ul>{t.words.map((x, i) => <li key={i} className={after(x, ex) ? 'aft' : ''}><span className="num">{x.t.slice(0, 8)}</span>
        <span><b>{x.headline}</b>{x.clause ? ` · ${x.clause}` : ''}{x.prem != null && <span className="muted num"> · {f2(x.prem)}{x.pct != null ? ` (${pct(x.pct)})` : ''}</span>}
          {after(x, ex) && <span className="muted"> · after your exit, not counted</span>}</span></li>)}</ul></td></tr>}
  </Fragment>
}
