// BAAD · RECORD (orderflow-desk docs/PANEL-DESIGN-2026-10-04/DESIGN.md §1): her trades on any day (/api/fold/record: her
// marks, or the tradebook imported after the day), the engine's word during the trade and at her exit, and what the engine
// and the premium did after. A row carries the grammar's mark where a RED (FOLD / PAST GIVE-UP) or an AMBER (a read going
// to CAN'T CHECK) happened while she was in. Rows and counts, never a rate. Click a row for every word.
// THE SCOREBOARD on top (receipts.py, validate-tab-spec §7.1): the KPI -- avg hold of WINNERS vs LOSERS -- big, for today, this
// week and all time; fear exits and their points left, re-entry tax, amber exits, adds dumped. Each row carries its receipt:
// hold, points, left on the table, the premium +10/+20/+30 min after, the exit's tags and the lamps at the exit. The
// tradebook import: file -> preview -> confirm; the server backs every touched day file up first. Premium points, never rupees.
import { Fragment, useEffect, useState } from 'react'
import { cc, FIXTURE, importBook, receiptsGet, record, today, useStore, type Board, type ImportOut, type Rec, type RecTrade, type Receipt, type Receipts, type Word } from './api'
import { Abs, f2, pct, tradeLabel, wordOf } from './Desk'
import { loadFixture } from './fixture'

const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"]
const SHORT: Record<string, string> = { HOLD: 'HOLD', 'PAST GIVE-UP': 'PGU', FOLD: 'FOLD', "CAN'T CHECK": "CAN'T" }
type Num = { t?: string | null; prem?: number | null; pct?: number | null; at?: string | null }
// after her exit the engine reads on: what holding would have done, never counted as her trade's words
const after = (x: Word, exit?: string | null) => x.after_exit ?? (!!exit && x.t > exit)
const at = (w?: Word) => w ? <><span className="num">{w.t.slice(0, 5)}</span>{w.prem != null && <span className="num"> @{f2(w.prem)}{w.pct != null ? ` (${pct(w.pct)})` : ''}</span>}</> : null
const mss = (s: number | null | undefined) => s == null ? '—' : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`
const sp = (x: number | null | undefined) => x == null ? '—' : `${x > 0 ? '+' : ''}${x.toFixed(1)}`

export default function Record({ day0 }: { day0?: string }) {
  const [day, setDay] = useState(day0 ?? today())     // any day: a past one reads off the files (fold log + her marks)
  const [r, setR] = useState<Rec | null>(null)
  const [rc, setRc] = useState<Receipts | null>(null)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let live = true
    setR(null)
    // read-only. The fixture viewer: her Sep 21-24 tradebook imported into a temp copy (fixture.ts), else the record's files
    const go = () => (FIXTURE ? loadFixture().then(f => f.receipts.day === day ? f.receipts.record : record(day)) : record(day)).then(x => { if (live) setR(x) })
    go()
    const t = window.setInterval(go, 60000)
    return () => { live = false; window.clearInterval(t) }
  }, [day, tick])
  useEffect(() => {
    let live = true
    const go = () => (FIXTURE ? loadFixture().then(f => f.receipts.receipts) : receiptsGet()).then(x => { if (live) setRc(x) })
    go()
    const t = window.setInterval(go, 60000)
    return () => { live = false; window.clearInterval(t) }
  }, [tick])
  const ts = r?.ok ? r.trades ?? [] : []
  const imp = ts.filter(t => t.trade.src === 'import').length
  const rcOf = (id: string) => rc?.receipts?.find(x => x.id === id && x.day === day)
  return <section className="baad">
    <h2 className="sec"><b>BAAD · RECORD</b> <input type="date" value={day} max={today()} onChange={e => e.target.value && setDay(e.target.value)} aria-label="day" />
      {ts.length > 0 && <span> · {ts.length} trade{ts.length > 1 ? 's' : ''}{imp ? ` · ${imp === ts.length ? 'all' : imp} imported from the tradebook` : ''}</span>}
      <span className="muted"> · counts, never rates</span>
      <Import done={() => setTick(x => x + 1)} /></h2>
    <Scoreboard rc={rc} />
    {!r ? <p className="muted">checking…</p>
      : !r.ok ? <p><Abs text={cc(r.why, 'the record could not be read')} /></p>
      : !ts.length ? <p><Abs text={`checked — no trades marked ${day === today() ? 'today' : `on ${day}`}`} /></p>
      : <table className="tbl">
        <thead><tr><th>#</th><th>trade</th><th>in → out</th><th>during your trade</th><th>engine at your exit</th><th>after · the engine's path</th><th>receipt</th></tr></thead>
        <tbody>{ts.map((t, i) => <Row key={t.id} n={i + 1} t={t} rc={rc?.ok ? rcOf(t.id) ?? null : undefined} />)}</tbody>
      </table>}
    <Kahani day={day} />
    <p className="note"><b>not shown</b> · the decoder-informed read at exit (P1–P7, a proposal, unsigned) and the kill clocks — no server field yet ·
      {rc?.typical_s != null && <> · typical time to target <b>{mss(rc.typical_s)}</b> ({rc.typical_src})</>}</p>
  </section>
}

/** THE SCOREBOARD (spec §7.1): today / this week / all time side by side; the KPI row first and big */
function Scoreboard({ rc }: { rc: Receipts | null }) {
  if (!rc) return <p className="muted">checking the receipts…</p>
  if (!rc.ok || !rc.scoreboard) return <p className="note"><Abs text={cc(rc.why, 'the receipts could not be read (GET /api/receipts)')} /></p>
  const cols: [string, Board][] = [['aaj', rc.scoreboard.today], ['is hafte', rc.scoreboard.week], ['sab', rc.scoreboard.all]]
  const cell = (b: Board, f: (b: Board) => React.ReactNode) => b.n ? f(b) : <Abs text="checked — no closed trade" />
  return <table className="score">
    <thead><tr><th>SCOREBOARD · her own rows, never a rate</th>{cols.map(([k, b]) => <th key={k}>{k} <span className="muted">· {b.n} trade{b.n === 1 ? '' : 's'}</span></th>)}</tr></thead>
    <tbody>
      <tr className="kpi"><td><b>avg hold</b> — winners vs losers<br /><span className="muted">THE KPI · the target is winners ≥ 10:00</span></td>{cols.map(([k, b]) => <td key={k}>{cell(b, b => <>
        <span className="w"><b className="num">{mss(b.avg_hold_win_s)}</b> jeet ({b.n_win})</span>
        <span className="l"><b className="num">{mss(b.avg_hold_loss_s)}</b> haar ({b.n_loss})</span>
        <span className="muted small num">median jeet {mss(b.median_hold_win_s)}{b.n_unpriced ? ` · ${b.n_unpriced} without an exit premium` : ''}</span></>)}</td>)}</tr>
      <tr><td><b>fear exits</b> · points left on the table</td>{cols.map(([k, b]) => <td key={k}>{cell(b, b => <>
        <b className="num">{b.fear_exits}</b> tagged · <span className="num">{sp(b.fear_left_pts)}</span> pts
        {b.fear_clock_only > 0 && <><br /><span className="muted small">+{b.fear_clock_only} by the clock only (no flow lamp recorded) · {sp(b.fear_clock_only_left_pts)} pts</span></>}</>)}</td>)}</tr>
      <tr><td><b>re-entry tax</b> · same direction within 15 min</td>{cols.map(([k, b]) => <td key={k}>{cell(b, b => <>
        <b className="num">{b.reentry_tax_events}</b> paid · <span className="num">{sp(b.reentry_tax_pts)}</span> premium pts<span className="muted small"> · {b.reentries} re-entries</span></>)}</td>)}</tr>
      <tr><td><b>amber exits</b> · out while the engine said HOLD, reversal &lt; 2</td>{cols.map(([k, b]) => <td key={k}>{cell(b, b => <>
        <b className="num">{b.amber_exits}</b>{b.amber_unverified > 0 && <span className="muted small"> · {b.amber_unverified} HOLD at exit, reversal not recorded</span>}</>)}</td>)}</tr>
      <tr><td><b>adds dumped</b> · sold within 2 bars</td>{cols.map(([k, b]) => <td key={k}>{cell(b, b => <b className="num">{b.adds_dumped}</b>)}</td>)}</tr>
    </tbody>
  </table>
}

/** her tradebook: file -> preview (what is new, what is already there, what the door refused) -> confirm */
function Import({ done }: { done: () => void }) {
  const [open, setOpen] = useState(false), [text, setText] = useState<string | null>(null), [name, setName] = useState('')
  const [pv, setPv] = useState<ImportOut | null>(null), [busy, setBusy] = useState(false)
  const pick = async (f?: File | null) => {
    if (!f) return
    const t = await f.text()
    setName(f.name); setText(t); setBusy(true); setPv(await importBook(t, false)); setBusy(false)
  }
  const confirm = async () => { if (!text) return; setBusy(true); const o = await importBook(text, true); setBusy(false); setPv(o); if (o.ok) done() }
  const n = pv?.days ? Object.values(pv.days).reduce((a, x) => a + x.new.length, 0) : 0
  if (!open) return <button className="lnkbtn" onClick={() => setOpen(true)}>IMPORT TRADEBOOK</button>
  return <div className="import">
    <label className="lnkbtn">tradebook CSV (Zerodha)<input type="file" accept=".csv,text/csv" onChange={e => pick(e.target.files?.[0])} /></label>
    {name && <span className="muted"> {name}</span>}
    {busy && <span className="muted"> · reading…</span>}
    {pv && !pv.ok && <p><Abs text={cc(pv.why, 'the import could not be read')} /></p>}
    {pv?.ok && <div className="pv">
      <p>{pv.fills} fills{pv.skipped?.length ? ` · ${pv.skipped.length} rows skipped (not an index option fill)` : ''} ·
        {Object.entries(pv.days ?? {}).map(([d, x]) => <span key={d}> {d}: <b>{x.new.length}</b> new, {x.have.length} already there{x.refused.length ? `, ${x.refused.length} refused` : ''} ·</span>)}</p>
      {pv.confirm ? <p><b>imported</b> · {Object.entries(pv.wrote ?? {}).map(([d, ids]) => `${d}: ${ids.length}`).join(' · ') || 'nothing new'} ·
          backups {(pv.backups ?? []).length} (day_*.json.bak-import-*)</p>
        : n ? <button className="btn sm" disabled={busy} onClick={confirm}>CONFIRM · import {n} round trip{n > 1 ? 's' : ''} (day files backed up first)</button>
        : <p><Abs text="checked — nothing new in this file (every round trip is already in the record)" /></p>}
    </div>}
    <button className="lnkbtn" onClick={() => { setOpen(false); setPv(null); setText(null); setName('') }}>close</button>
  </div>
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

/** the receipt cell: what the trade left behind (receipts.py), never rupees */
function ReceiptCell({ r }: { r: Receipt | null | undefined }) {
  if (r === undefined) return <Abs text="could not check — the receipts did not load" />
  if (r === null) return <Abs text="not shown — no receipt (still open, or not in the receipts' record yet)" />
  const lamps = r.lamps_at_exit ? Object.entries(r.lamps_at_exit).map(([k, v]) => `${k.toUpperCase()} ${v}`).join(' · ') : null
  return <>
    <span className="num">hold <b>{mss(r.hold_s)}</b> · <b className={(r.pts ?? 0) > 0 ? 'up' : (r.pts ?? 0) < 0 ? 'dn' : ''}>{sp(r.pts)}</b> pts</span>
    <span className="muted small"> ({r.exit_px_src})</span><br />
    {r.post.why ? <Abs text={r.post.why} /> : <span className="num">left <b>{sp(r.left_on_table_pts)}</b> (best {f2(r.post.max_fav)} {r.post.max_fav_t?.slice(0, 5)}) ·
      +10/+20/+30 {f2(r.post.p10)} / {f2(r.post.p20)} / {f2(r.post.p30)}</span>}
    <br />{r.tags.map(x => <span key={x} className="xtag">{x}</span>)}
    {r.fear_clock_only && <span className="xtag soft" title="green at exit before a third of the typical time; no flow lamp recorded to rule a reversal in or out">fear? clock only</span>}
    {r.adds_dumped.length > 0 && <span className="xtag">ADD DUMPED ×{r.adds_dumped.length}</span>}
    <span className="muted small">{lamps ? `lamps at exit ${lamps}` : 'lamps at exit: not recorded'}{r.reversal_at_exit != null ? ` · ${r.reversal_at_exit}/4 reversal` : ''}</span>
  </>
}

function Row({ n, t, rc }: { n: number; t: RecTrade; rc?: Receipt | null }) {
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
      <td className="rcpt"><ReceiptCell r={rc} /></td>
    </tr>
    {open && <tr className="ws"><td /><td colSpan={6}>
      <ul>{t.words.map((x, i) => <li key={i} className={after(x, ex) ? 'aft' : ''}><span className="num">{x.t.slice(0, 8)}</span>
        <span><b>{x.headline}</b>{x.clause ? ` · ${x.clause}` : ''}{x.prem != null && <span className="muted num"> · {f2(x.prem)}{x.pct != null ? ` (${pct(x.pct)})` : ''}</span>}
          {after(x, ex) && <span className="muted"> · after your exit, not counted</span>}</span></li>)}</ul></td></tr>}
  </Fragment>
}
