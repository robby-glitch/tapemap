// THE HOLD / FOLD WINDOW — docs/hold/PREREG-merged.md rev 4, served by /api/hold.
// Layout: docs/mockups/validate-2026-09-25/validate-design.html; fixes: docs/hold/REVIEW-2026-09-25.md.
//
// Mounted ONCE at the App root; it exists only while she is IN a trade. Every open trade is watched
// (the header carries the worst word); a FOLD keeps I'M OUT in the header and its live read under the
// word, and the ✕ still closes the window (closing is not exiting); the qualifier (NOISE / STRUCTURE
// ONLY / NOTHING PAYING), the quiet clock and the read's age are on the one line. "Pop out" moves the same tree into a Chrome Document Picture-in-Picture window over the
// broker. It reads, it never decides; LIGHT only, no chart, never P&L on the collapsed line, no order path.
import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import { Abs, Age, Cutoff, Err, Fired, Guard, Ico, Live, Mark, N, Qual, Quiet, Rows, SideList, Sigma, WALL, WatchList, cap, inr, levelNote, nowHMS, roomText, rs, span, strip, twoLegs, vcls } from './parts'
import { onFold, rank, tone, tradeOp, useHold } from './store'
import type { Held } from './store'

export type Word = 'HOLD' | 'WATCH' | 'FOLD' | 'PATA NAHI'
type Row = { state: string; fact?: string; rows?: string; why?: string | null; tag: string; label?: string; fold?: string | null }
export type Trade = { id: string; idx: string; k: number; side: 'CE' | 'PE'; role: 'long' | 'short'; t0: string; p0: number | null; qty: number
                      exit_t: string | null; exit_t_broker?: string | null }
export type SideRead = { side: string; since: string; text: string; facts: { k: string; state: string; fact: string; tag: string }[]; oi_half: string[]; expiry: { text: string }; agrees?: string }
export type Now = {
  t: string; verdict: Word; tag: string | null; sentence: string; since: string; fold_rule: number | null
  unlatched: Word; healed_since?: string | null     // the read NOW with the latch removed (hold.py §7); shown under a latched FOLD
  line: { L?: number; src?: string; room?: number | null; px?: number; broken_at?: string | null; blind?: string | null; tag: string
          level?: number | null; B?: number | null; print?: string | null; to_level?: number | null; next_close?: string | null; clamped?: boolean }
  payers: Row; holders: Row; flow: Row; trend: Row; count: string; n_for: number; n_against: number; against?: string | null
  clock: { paid_last?: string | null; quiet?: number; of?: number; text: string }
  watch: string | null; watch_items?: string[] | null
  prem: { c?: number; pnl?: number; pct?: number; why?: string; tag?: string }; blind: string[]
}
export type Reading = {
  ok: boolean; why?: string; draft?: string; asof?: string; trade?: Trade; now?: Now
  fold?: { t: string; rule: number; why?: string; L?: number | null; px?: number | null; by?: number | null; level?: number | null; by_level?: number | null } | null
  entry?: { t: string; verdict: string; text: string; head: boolean }; side?: SideRead; after_exit?: boolean
  sigma?: { z?: number | null; vwap?: number; why?: string } | null
  absent?: { checked_none: string; could_not_check: string[]; not_shown: string[] }
  plan?: PlanRow & { entry: PlanRow; draft: string; not_shown: string[] }
}
export type PlanRow = {
  t: string
  stop: { L?: number; room?: number | null; risk?: number | null; risk_why?: string | null; text?: string | null; level?: number | null
          level_text?: string | null; after_fold?: { L: number; text: string; detail?: string | null } | null }
  rung: null | { src: 'wall' | 'session' | 'none'; side: string; k: number | null; room: number | null; word: string | null
                 favour?: string; state?: string; fold_t?: string | null; label?: string }
  room: null | { rung: number | null; stop: number | null; text: string; note: string | null }
  touch: null | { k?: number; side?: string; word?: string; favour?: string; session?: boolean; text?: string }
  exits: { line: string; window: string }
}

const W = 400, COLW = 600

function ls(k: string, v?: string): string | null {
  try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v) } catch { /* private window: the window still works */ }
  return null
}
const contract = (t: Trade) => `${t.idx} ${t.k} ${t.side}`

export default function HoldWindow(p: { hidden?: boolean }) {
  return <Guard name="hold window"><Win {...p} /></Guard>
}

function Win({ hidden = false }: { hidden?: boolean }) {
  const st = useHold()
  const open = st.trades.filter(t => !t.exit_t).map(t => ({ t, rd: st.reads[t.id] as Held | undefined }))
    .sort((a, b) => rank(a.rd?.now?.verdict) - rank(b.rd?.now?.verdict) || b.t.t0.localeCompare(a.t.t0))
  const folded = open.filter(x => x.rd?.now?.verdict === 'FOLD')
  const [pick, setPick] = useState<string | null>(null)
  // a FOLD anywhere takes the head; otherwise her pick, else the worst word
  const cur = folded.length && !folded.some(x => x.t.id === pick) ? folded[0] : open.find(x => x.t.id === pick) || open[0]
  const [closed, setClosedS] = useState<string[]>(() => { try { return JSON.parse(ls('hold.closed3') || '[]') } catch { return [] } })
  // ✕ closes it for the trades open now, keyed on whether each is FOLD: a new trade, or a trade TURNING FOLD, brings
  // it back (REVIEW P0-6); closed under a FOLD it stays closed -- closing the window is not exiting the trade
  const ck = (x: { t: Trade; rd?: Held }) => x.t.id + (x.rd?.now?.verdict === 'FOLD' ? ':FOLD' : '')
  const show = open.length > 0 && open.some(x => !closed.includes(ck(x)))
  const [min, setMinS] = useState<boolean>(() => ls('hold.min') === '1')
  const [pos, setPos] = useState<{ x: number; y: number } | null>(() => { try { return JSON.parse(ls('hold.pos2') || 'null') } catch { return null } })
  const [beep, setBeepS] = useState<boolean>(() => ls('hold.tone') !== '0')        // default ON (REVIEW P1-13)
  const [pip, setPip] = useState<Window | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [undo, setUndo] = useState<{ id: string; label: string } | null>(null)

  const setMin = (v: boolean) => {
    ls('hold.min', v ? '1' : '0'); setMinS(v)
    try { pip?.resizeTo(pip.outerWidth, v ? 110 : 600) } catch { /* the OS keeps its size */ }
  }
  const setBeep = (v: boolean) => { ls('hold.tone', v ? '1' : '0'); setBeepS(v); if (v) tone() }

  useEffect(() => onFold(() => { if (beep) tone() }), [beep])       // one tone, on any trade turning FOLD
  useEffect(() => { if (!show && pip) pip.close() }, [show, pip])   // out of every trade: the pop-out goes too

  // the word in the browser tab title (and the PiP title), so the taskbar carries it behind the broker window;
  // under a latched FOLD the live read rides along: "[FOLD · live HOLD 23000PE]"
  const now = cur?.rd?.ok ? cur.rd.now : undefined
  const head = show && cur && now
    ? `[${now.verdict}${now.tag ? ` · ${now.tag}` : ''}${now.verdict === 'FOLD' ? ` · live ${now.unlatched}` : ''} ${cur.t.k}${cur.t.side}] ` : ''
  useEffect(() => {
    const put = () => { document.title = head + document.title.replace(/^\[[^\]]*\] /, '') }
    put()
    const t = setInterval(put, 2000)                                  // the app rewrites the title on each tape update
    return () => { clearInterval(t); document.title = document.title.replace(/^\[[^\]]*\] /, '') }
  }, [head])
  useEffect(() => { if (pip) pip.document.title = head || 'HOLD / FOLD' }, [pip, head])

  // drag by the header (the main-window float only; a PiP window is moved by the OS); double-click re-docks it
  const drag = useRef<{ dx: number; dy: number } | null>(null)
  const box = useRef<HTMLDivElement>(null)
  const onDown = (e: React.PointerEvent) => {
    if (pip || (e.target as HTMLElement).closest('button,select,input,label,details')) return
    const r = box.current!.getBoundingClientRect()
    drag.current = { dx: e.clientX - r.left, dy: e.clientY - r.top }
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }
  const onMove = (e: React.PointerEvent) => {
    if (!drag.current) return
    setPos({ x: Math.min(Math.max(0, e.clientX - drag.current.dx), window.innerWidth - 160),
             y: Math.min(Math.max(0, e.clientY - drag.current.dy), window.innerHeight - 48) })
  }
  const onUp = () => { if (drag.current) { drag.current = null; ls('hold.pos2', JSON.stringify(pos)) } }
  const grip = { onPointerDown: onDown, onPointerMove: onMove, onPointerUp: onUp, onDoubleClick: () => { setPos(null); ls('hold.pos2', 'null') } }

  const popOut = async () => {
    const dp = (window as unknown as { documentPictureInPicture?: { requestWindow: (o: object) => Promise<Window> } }).documentPictureInPicture
    if (!dp) { setMsg('This browser cannot pop out (it needs Chrome 116 or later) — the window stays in the tab.'); return }
    try {
      const w = await dp.requestWindow({ width: 380, height: min ? 110 : 600 })        // fits beside a 695-px broker chart
      w.document.body.style.margin = '0'
      w.document.body.style.background = '#fff'
      for (const ss of Array.from(document.styleSheets)) {        // the pop-out is a new document: carry the styles over
        try {
          const st = w.document.createElement('style')
          st.textContent = Array.from(ss.cssRules).map(r => r.cssText).join('\n')
          w.document.head.append(st)
        } catch {
          if (ss.href) { const l = w.document.createElement('link'); l.rel = 'stylesheet'; l.href = ss.href; w.document.head.append(l) }
        }
      }
      w.addEventListener('pagehide', () => setPip(null))
      setPip(w)
    } catch (e) { setMsg(`Could not pop out — ${(e as Error).message}`) }
  }

  const out = async (t: Trade) => {
    if (busy) return
    setBusy(true)
    const r = await tradeOp({ op: 'exit', id: t.id, exit_t: nowHMS() })
    setBusy(false)
    if (!r.ok) { setMsg(r.why || 'the exit did not land'); return }
    setUndo({ id: t.id, label: contract(t) })
    setTimeout(() => setUndo(u => u?.id === t.id ? null : u), 10000)
  }
  const reopen = async () => {
    if (!undo) return
    const r = await tradeOp({ op: 'reopen', id: undo.id })
    if (!r.ok) setMsg(r.why || 'the undo did not land')
    setUndo(null)
  }
  const closeIt = () => { const ids = open.map(ck); ls('hold.closed3', JSON.stringify(ids)); setClosedS(ids) }

  const toast = undo && createPortal(
    <div className="hv hv-toast">{undo.label} marked out at {nowHMS().slice(0, 5)} <button type="button" onClick={reopen}>Undo</button></div>, document.body)
  if (!show || !cur) return toast || null
  if (hidden && !pip) return toast || null        // on the Validate tab the full-size reading is the tab itself

  const rd = cur.rd, t = cur.t, fold = rd?.fold
  const red = now?.verdict === 'FOLD'
  const others = open.filter(x => x.t.id !== t.id)
  // I'M OUT under a FOLD, and the ✕ always: closing the window is not exiting the trade
  const act = <>
    {red && <button type="button" className="btn btn-sm btn-out" disabled={busy} onClick={() => out(t)}>I'M OUT</button>}
    <button type="button" className="icon-btn" title="Close the window — it comes back by itself for a new trade, or if an open trade turns FOLD; the trade stays watched" aria-label="Close" onClick={closeIt}><Ico n="X" /></button>
  </>
  const btns = (
    <span className="fl-btns">
      {!pip && <button type="button" className="icon-btn" title="Pop out on top of every window" aria-label="Pop out" onClick={popOut}><Ico n="PiP" /></button>}
      {pip && <button type="button" className="icon-btn" title="Back into the tab" aria-label="Back into the tab" onClick={() => pip.close()}><Ico n="Undo" /></button>}
      <button type="button" className="icon-btn" title={min ? 'Open' : 'Collapse to one line'} aria-label={min ? 'Open' : 'Collapse'} onClick={() => setMin(!min)}>
        <Ico n={min ? 'ChevronUp' : 'ChevronDown'} /></button>
      {act}
    </span>
  )
  const lineBit = !now ? null : fold?.rule === 3 && fold.L != null
    ? <span>line {inr(fold.L, 1)} broke {fold.t} by <N t="M">{`${fold.by} pts`}</N></span>
    : now.line.blind ? <Abs text={now.line.blind} />
    : now.line.to_level != null
      ? <span>line <N t="M">{inr(now.line.L ?? 0, 1)}</N> · <N t="M">{`${now.line.to_level} pts`}</N> to the break{now.line.next_close ? ` · close ${now.line.next_close}` : ''}</span>
      : <span>line <N t="M">{inr(now.line.L ?? 0, 1)}</N> · <N t="M">{roomText(now.line.room ?? 0)}</N></span>

  // ── collapsed: WORD · contract · line & room · quiet · the one against-fact · rung · since · age — NEVER the P&L (§5)
  const line = min ? (
    <div className="fl-line" {...grip}>
      {now ? <span className={`word fw ${vcls(now.verdict)}`}>{now.verdict}<Qual tag={now.tag} />
               {now.verdict === 'FOLD' && <span className="qual live-c"> · live {now.unlatched}</span>}</span>
           : <span className="word fw v-PATA">{rd && !rd.ok ? 'NO READ' : 'READING…'}</span>}
      <span className="mid">
        <span className="c">{contract(t)}</span>
        {now && <><span className="dot">·</span>{lineBit}</>}
        {now && t.role === 'long' && <><span className="dot">·</span><Quiet n={now} /></>}
        {now && <><span className="dot">·</span><Against n={now} fold={fold} /></>}
        {now && rd?.plan?.rung?.src === 'wall' && <><span className="dot">·</span><span>rung <N t="M">{`${rd.plan.rung.room} pts`}</N> {rd.plan.rung.word?.toLowerCase()}</span></>}
        {others.length > 0 && <><span className="dot">·</span><span>+{others.length} open{others.some(x => x.rd?.now?.verdict === 'FOLD') ? ' · one is FOLD' : ''}</span></>}
      </span>
      {now && <span className="since">since <span className="num">{now.since}</span></span>}
      <Age asof={rd?.asof} />
      <Cutoff open />
      <span className="draft" title={rd?.draft || 'pre-registered, untested'}>DRAFT</span>
      {btns}
    </div>
  ) : null

  const pl = rd?.plan
  const entryRoom = pl?.entry?.stop?.room
  const body = min ? null : (
    <>
      <div className="fl-head" {...grip}>
        <div>
          {now ? <div className={`word fw ${vcls(now.verdict)}`}>{now.verdict}</div> : <div className="none">{rd && !rd.ok ? 'NO READ' : 'READING…'}</div>}
          {now && <Live n={now} />}
          {now && <div className="since">since <span className="num">{now.since}</span></div>}
        </div>
        <div className="cnt" style={{ minWidth: 0 }}>
          {now && <div className="qline"><Qual tag={now.tag} />{t.role === 'long' && <Quiet n={now} />}</div>}
          {now && <div className="sub"><span className="label">live read</span> {now.count}</div>}
          <div className="c">{contract(t)}<span>{t.role} · qty {t.qty} · in {t.t0.slice(0, 5)}</span></div>
        </div>
        {btns}
      </div>

      {rd && !rd.ok && <div className="fl-sec"><Abs text={rd.why} /></div>}
      {st.err && <div className="fl-sec"><Abs text={st.err} /></div>}
      {now && rd && <>
        <div className="fl-sec">
          {fold ? <Fired fold={fold} /> : <p className="fl-say">{cap(strip(now.sentence))}</p>}
          {st.flips[t.id] && st.flips[t.id].rows.length > 0 && <p className="sm flip">changed {st.flips[t.id].t}: {st.flips[t.id].rows.join(' · ')}</p>}
          <WatchList n={now} />
          {rd.entry?.head && <p className="sm" style={{ fontWeight: 600 }}>{rd.entry.text}</p>}
          {entryRoom != null && <p className="sm">you entered <N t="M">{roomText(entryRoom)}</N> from your line</p>}
          {now.flow.state === 'blind' && <Abs text="could not check — order flow is blind: two-family FOLDs read OI and trend only" />}
          {twoLegs(open.map(x => x.t)) && <Abs text="not shown — a two-leg position is not registered; each leg is read as its own direction" />}
          {!red && now.verdict === 'HOLD' && <div><Abs text={rd.absent?.checked_none} /></div>}
        </div>
        <div className="fl-sec fl-nums">
          <div><span className="label">Stop</span>
            {fold?.rule === 3 && fold.L != null ? <><div className="big"><N t="M">{inr(fold.L, 1)}</N></div><div className="sub">broke {fold.t} by <N t="M">{`${fold.by} pts`}</N>{fold.by_level != null && <> · {fold.by_level} past the break</>}</div>
                {pl?.stop.after_fold?.text && <div className="sub">{pl.stop.after_fold.text}</div>}</>
              : pl?.stop.L != null ? <><div className="big"><N t="M">{inr(pl.stop.L, 1)}</N></div>
                <div className="sub"><N t="M">{pl.stop.room != null ? roomText(pl.stop.room) : '—'}</N>{pl.stop.risk != null && (pl.stop.room ?? 0) >= 0 && <> · ≈ <N t="I">{rs(pl.stop.risk)}</N></>}</div>
                {pl.stop.level_text && <div className="sub">{levelNote(pl.stop.level_text)}</div>}</>
              : <div className="sub"><Abs text={now.line.blind || pl?.stop.risk_why || 'could not check — the line'} /></div>}</div>
          <div><span className="label">Next wall</span>
            {pl?.rung?.src === 'wall' && pl.rung.k != null ? <><div className="big">{pl.rung.side} <N t="M">{inr(pl.rung.k)}</N></div>
                <div className="ww"><Mark st={WALL[pl.rung.word || ''] || 'neither'} />{pl.rung.word}</div><div className="sub"><N t="M">{`${pl.rung.room} pts`}</N></div></>
              : pl?.rung?.src === 'session' && pl.rung.k != null ? <><div className="big"><N t="M">{inr(pl.rung.k, 1)}</N></div><div className="sub">{pl.rung.label}</div></>
              : <div className="sub">{pl?.rung ? pl.rung.label : 'none — a writer: the stop alone'}</div>}</div>
          <div><span className="label">Premium</span>
            {now.prem.c != null ? <><div className="big"><N t={now.prem.tag || 'I'}>{rs(now.prem.c, 2)}</N></div>
              {t.p0 != null && <div className="sub">in <span className="num">{rs(t.p0, 2)}</span></div>}
              {now.prem.pnl != null && <div className="sub pnl-sm">P&amp;L <N t={now.prem.tag || 'I'}>{(now.prem.pnl < 0 ? '−' : '+') + rs(Math.abs(now.prem.pnl))}</N></div>}
              <Sigma rd={rd} /></>
              : <div className="sub"><Abs text={now.prem.why} /></div>}</div>
        </div>
        <details className="fl-sec fl-more">
          <summary className="label">The rows · since you entered · the side read</summary>
          <div className="fl-rows"><Rows n={now} /></div>
          {!!rd.runs?.length && <div className="fl-runs">
            {rd.runs.map(r => <div className="run" key={r.from}><span className="t num">{span(r)}</span><span className={`wd word ${vcls(r.verdict)}`}>{r.verdict}</span>
              <span className="tx" title={r.sentence}>{cap(strip(r.sentence))}</span></div>)}</div>}
          {rd.side && <SideList s={rd.side} />}
        </details>
      </>}
      {others.length > 0 && (
        <div className="fl-sec fl-trades"><span className="label">Also open</span>
          {others.map(x => (
            <div className="tr" key={x.t.id}>
              <span onClick={() => setPick(x.t.id)} title="show this trade">
                <b className={`word ${vcls(x.rd?.now?.verdict || 'PATA NAHI')}`}>{x.rd?.now?.verdict || '…'}</b> {contract(x.t)} · since {x.rd?.now?.since || '—'}</span>
              <button type="button" className="btn btn-sm" disabled={busy} onClick={() => out(x.t)}>I'm out</button>
            </div>
          ))}
        </div>
      )}
      <div className="fl-sec fl-tools">
        {!red && <button type="button" className="btn btn-sm" disabled={busy} onClick={() => out(t)}>I'm out of {contract(t)}</button>}
        <label style={{ marginLeft: 'auto' }}><input type="checkbox" checked={beep} onChange={e => setBeep(e.target.checked)} /> tone on FOLD</label>
        {msg && <Err>{msg} <button type="button" className="link" onClick={() => setMsg(null)}>dismiss</button></Err>}
      </div>
      <div className="fl-foot"><span className="draft" title={rd?.draft || 'pre-registered, untested'}>DRAFT</span><Age asof={rd?.asof} /><Cutoff open /><span>nothing is sent to your broker</span></div>
    </>
  )

  const cls = `hv float ${min ? 'col' : 'open'}${red ? ' red' : ''}${pip ? ' in-pip' : ''}`
  const style: CSSProperties | undefined = pip ? undefined
    : pos ? { left: Math.max(0, Math.min(pos.x, window.innerWidth - (min ? Math.min(COLW, window.innerWidth - 16) : W) - 8)), top: pos.y, right: 'auto', bottom: 'auto' }
    : undefined
  const win = <div ref={box} className={cls} style={style}>{line}{body}</div>
  if (pip) return <>{createPortal(win, pip.document.body)}{!hidden && <div className="hv-back">HOLD / FOLD is popped out on top <button type="button" onClick={() => pip.close()}>bring it back</button></div>}{toast}</>
  return <>{win}{toast}</>
}

function Against({ n, fold }: { n: Now; fold?: Reading['fold'] }) {
  // the server's own rule phrase heads its reason ("two families against you: …"); no copy of the rule names here
  if (n.verdict === 'FOLD' && fold) return <span className="ag"><Ico n="X" c="m-against" />{fold.why?.split(': ')[0] || `rule ${fold.rule}`}</span>
  if (n.against) return <span className="ag">{n.against.startsWith('nothing') ? null : <Ico n="X" c="m-against" />}{n.against}</span>
  const a = [n.payers, n.holders, n.flow, n.trend].find(r => r.state === 'against')
  return a ? <span className="ag"><Ico n="X" c="m-against" />{(a.fact || a.rows || '').split(' — ')[0]}</span>
           : <span className="ag">nothing against you</span>
}
