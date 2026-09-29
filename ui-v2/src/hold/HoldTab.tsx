// THE VALIDATE TAB — the hold window's permanent home (the floating window stays for every other tab
// and for popping out over the broker). Layout: docs/mockups/validate-2026-09-25/validate-design.html;
// fixes: docs/hold/REVIEW-2026-09-25.md.
//
// BEFORE: the slip on the left (index, strike, CE/PE, BUY/SELL, lots, VALIDATE; keys C/P B/S ↑↓ Enter
// I O). The answer: one big word — GO / WAIT / NO (docs/hold/VALIDATE-PREREG.md, signed, DRAFT until
// her forward checks judge it) — the five facts as marks, each fact in plain words, what would have to
// change, and the numbers she acts on. Every press is logged. A count, never a percentage; never a
// size. IN: "I'm in" marks the trade; the tab then reads it exactly as the window does (one store).
// LIGHT only; no chart; nothing is sent to any broker.
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { Chain, IndexKey } from '../data'
import type { Reading, Trade } from './HoldWindow'
import { Abs, AbsentList, Age, Cutoff, Err, Fired, Guard, Ico, Live, Mark, Marks, N, PlanList, Qual, Quiet, Rows, SideList, Sigma, StopBlock, T, WallBlock, WatchList,
         cap, inr, nowHMS, roomText, rs, span, strip, twoLegs, vcls } from './parts'
import { ageSec, followTrade, j, tradeOp, useHold } from './store'
import MarketNow from './MarketNow'
import type { Held } from './store'

type Absence = 'none' | 'blind' | 'hidden' | null
type Fact = { name: string; state: 'for' | 'against' | 'neither'; text: string; absence?: Absence }
type Verdict = { word: 'GO' | 'WAIT' | 'NO' | null; count: string; rev?: string; line?: number | null; noise?: number | null; not_shown?: string[]; n_for: number; n_against: number; n_neither: number; sentence: string
                 needs: string[]; facts: Fact[]; draft: string; tag?: string; writer_note?: string | null; printed?: string[] }
type ZoneEv = { t: string; seen: string; ago: number; kind?: string; side: string; band: string; px: number | null; legal: boolean | null; why: string | null; agrees: string; tag?: string }
// THE EXPRESSION (docs/hold/EXPRESSION-PREREG.md rev e §A, §B, §F.1): the last 3-min close's word for her direction
type XFact = { name: string; state: 'buy' | 'sell' | 'neither'; absence: Absence; text: string; tag: string }
type XCard = { side: 'CE' | 'PE'; role: 'long' | 'short'; k: number; atm: string; expiry?: string | null; px: number | null; px_t: string; px_tag: string
               delta: number | null; gamma: number | null; greeks_tag: string; greeks_why: string | null; entry: string | null; validate: Verdict | null
               named: boolean; refused: string[]; wall?: { k: number; state: string } | null; s4?: string | null; line_vs_strike?: string | null }
type Expr = { ok: boolean; why?: string; d: number; dir: 'UP' | 'DOWN'; draft: string; not_shown: string[]; setup_line?: string | null; read_at?: string
              word?: string; base?: string; leg?: string | null; leans?: boolean; named_by?: 'count' | 'refusal'; lead?: number | null; refused?: string[]
              since?: string; was?: { word: string; until: string } | null; since_gap?: string | null; nb?: number; ns?: number; nn?: number; count?: string
              facts?: XFact[]; buy?: XCard; sell?: XCard; zero_dte?: boolean
              printed?: { drag: { text?: string; why?: string; tag: string }; expiry: string; regime: { word: string | null; price?: string[]; oi?: string[]; why?: string } } }
type Check = Reading & {
  idx?: string; lot?: number | null; qty_src?: string; p0_src?: string | null; validate?: Verdict; note?: string; expr?: Expr
  zone?: { trigger: ZoneEv | null; arm: ZoneEv | null; why: string | null }
  greeks?: { delta?: number; gamma?: number; why?: string; tag?: string }
}
const IDX: IndexKey[] = ['NIFTY', 'SENSEX', 'BANKNIFTY'] as IndexKey[]
const NAMES = ['Your setup', 'Right now', 'Room', 'Paying']          // VALIDATE-PREREG rev 2 §1
const OLD_S = 60                     // an answer older than a minute is dimmed: the market has moved a bar

function ls(k: string, v?: string): string | null {
  try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v) } catch { /* the tab still works */ }
  return null
}
const lotsText = (n: number) => `${n} lot${n > 1 ? 's' : ''}`
const typing = (e: KeyboardEvent) => e.ctrlKey || e.metaKey || e.altKey || !!(e.target as HTMLElement)?.closest?.('input,select,textarea')

export default function HoldTab(p: { index: IndexKey; chain: Chain; onIndex: (i: IndexKey) => void }) {
  return <Guard name="Validate tab"><Tab {...p} /></Guard>
}

function Tab({ index, chain, onIndex }: { index: IndexKey; chain: Chain; onIndex: (i: IndexKey) => void }) {
  const st = useHold()
  const ladder = [...(chain?.strikes || [])].sort((a, b) => a.strike - b.strike)
  const atm = ladder.length ? ladder.reduce((b, s) => Math.abs(s.strike - chain.spot) < Math.abs(b.strike - chain.spot) ? s : b, ladder[0]).strike : 0
  const [strike, setStrike] = useState<number>(atm)
  const [side, setSideS] = useState<'CE' | 'PE'>(() => ls('hold.side') === 'CE' ? 'CE' : 'PE')     // her last choice survives an index switch
  const [role, setRoleS] = useState<'long' | 'short'>(() => ls('hold.role') === 'short' ? 'short' : 'long')
  const setSide = (v: 'CE' | 'PE') => { ls('hold.side', v); setSideS(v) }
  const setRole = (v: 'long' | 'short') => { ls('hold.role', v); setRoleS(v) }
  const [lots, setLots] = useState(1)
  const [ck, setCk] = useState<Check | null>(null)
  const [asked, setAsked] = useState<{ at: string; key: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(true)
  const [fill, setFill] = useState({ t: '', p: '' })
  const [marking, setMarking] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [sel, setSelS] = useState<string | null>(() => ls('hold.sel') || null)
  const [mode, setMode] = useState<'check' | 'in'>('check')
  const [undo, setUndo] = useState<{ id: string; label: string } | null>(null)
  const [exitT, setExitT] = useState('')
  const decided = useRef(false)
  const lot = st.lots[index] ?? (ck?.ok ? ck.lot : null) ?? null        // preloaded at mount (REVIEW P1-7)
  const key = `${index}|${strike}|${side}|${role}`                       // lots change the size, not the answer
  const select = (id: string | null) => { ls('hold.sel', id ?? ''); setSelS(id) }

  useEffect(() => { if (atm && !ladder.some(s => s.strike === strike)) setStrike(atm) }, [index, atm])
  const current = st.trades.find(t => t.id === sel) || null
  useEffect(() => { followTrade(mode === 'in' && current?.exit_t ? current.id : null); return () => followTrade(null) }, [mode, current?.id, current?.exit_t])
  // opening the tab while a marked trade is still open: show that trade first
  useEffect(() => {
    if (decided.current || !st.loaded) return
    decided.current = true
    const openT = st.trades.filter(t => !t.exit_t)
    const t = openT.find(t => t.id === sel) || openT[openT.length - 1]
    if (t) { select(t.id); setMode('in') }
  }, [st.loaded])

  const validateNow = async () => {
    if (!strike || busy) return
    setBusy(true); setMsg(null)
    const qty = lot ? `&qty=${lots * lot}` : ''
    try {
      const r = await j<Check>(`/api/hold/check?idx=${index}&k=${strike}&side=${side}&role=${role}${qty}&log=1`)
      setCk(r); setAsked({ at: nowHMS(), key })
      setFill({ t: '', p: r.ok && r.trade?.p0 != null ? String(r.trade.p0) : '' })
      if (r.ok) setEditing(false)
    } catch (e) { setCk({ ok: false, why: `could not check — no answer from the server (${(e as Error).message})` }) }
    setBusy(false)
  }
  const stale = !!asked && asked.key !== key
  const ready = !!ck?.ok && !stale && !marking

  const imIn = async () => {
    if (!ready || !ck?.ok) return
    setMarking(true)
    const r = await tradeOp({ op: 'mark', idx: index, k: strike, side, role, t0: fill.t || nowHMS(),
                              p0: fill.p || String(ck.trade?.p0 ?? ''), qty: lot ? lots * lot : ck.trade?.qty })
    setMarking(false)
    if (!r.ok) { setMsg(r.why || 'the mark did not land'); return }
    setMsg(null)
    const t = [...(r.trades || [])].reverse().find(t => t.idx === index && t.k === strike && t.side === side && t.role === role && !t.exit_t)
    if (t) { select(t.id); setMode('in') }
  }
  // §F.1: each expression card keeps its own I'M IN -- it marks that leg (the ATM strike, now, the card's premium)
  const imInCard = async (c: XCard) => {
    if (!ck?.ok || stale || marking) return
    setMarking(true)
    const r = await tradeOp({ op: 'mark', idx: ck.trade?.idx ?? index, k: c.k, side: c.side, role: c.role, t0: nowHMS(),
                              p0: c.px != null ? String(c.px) : '', qty: lot ? lots * lot : ck.trade?.qty })
    setMarking(false)
    if (!r.ok) { setMsg(r.why || 'the mark did not land'); return }
    setMsg(null)
    const t = [...(r.trades || [])].reverse().find(t => t.k === c.k && t.side === c.side && t.role === c.role && !t.exit_t)
    if (t) { select(t.id); setMode('in') }
  }
  // §F.1: "setup: BUY d2 armed, 11:42 bar — the expression for UP is ready" -- display only, it pre-fills nothing
  const [setupLine, setSetupLine] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    const go = () => j<{ ok: boolean; setup_line?: string | null }>(`/api/hold/expr?idx=${index}`)
      .then(r => { if (live) setSetupLine(r.ok ? r.setup_line ?? null : null) }).catch(() => { if (live) setSetupLine(null) })
    go()
    const t = setInterval(go, 30000)
    return () => { live = false; clearInterval(t) }
  }, [index])
  const imOut = async (t: Trade) => {
    const r = await tradeOp({ op: 'exit', id: t.id, exit_t: exitT || nowHMS() })
    if (!r.ok) { setMsg(r.why || 'the exit did not land'); return }
    setExitT(''); setMode('check'); select(null)
    setUndo({ id: t.id, label: `${t.idx} ${t.k} ${t.side}` })
    setTimeout(() => setUndo(u => u?.id === t.id ? null : u), 10000)
  }
  const reopen = async () => {
    if (!undo) return
    const r = await tradeOp({ op: 'reopen', id: undo.id })
    if (!r.ok) setMsg(r.why || 'the undo did not land')
    else { select(undo.id); setMode('in') }
    setUndo(null)
  }
  const open = (t: Trade) => { select(t.id); setMode('in') }

  // keys, as on a broker ticket: C/P · B/S · ↑↓ strike · Enter validate · I in · O out (REVIEW §5)
  const keys = useRef<(e: KeyboardEvent) => void>(() => {})
  keys.current = (e: KeyboardEvent) => {
    if (typing(e)) return
    const k = e.key.toLowerCase(), i = ladder.findIndex(s => s.strike === strike)
    const inView = mode === 'in' && current
    if (!inView && k === 'c') setSide('CE')
    else if (!inView && k === 'p') setSide('PE')
    else if (!inView && k === 'b') setRole('long')
    else if (!inView && k === 's') setRole('short')
    else if (!inView && (e.key === 'ArrowUp' || e.key === 'ArrowDown') && i >= 0) {
      const n = ladder[i + (e.key === 'ArrowUp' ? 1 : -1)]
      if (n) setStrike(n.strike)
    } else if (!inView && e.key === 'Enter') validateNow()
    else if (!inView && k === 'i') imIn()
    else if (inView && k === 'o' && !current.exit_t) imOut(current)
    else return
    e.preventDefault()
  }
  useEffect(() => { const f = (e: KeyboardEvent) => keys.current(e); window.addEventListener('keydown', f); return () => window.removeEventListener('keydown', f) }, [])

  // after the close: the tradebook completes the day's hold log
  const [imp, setImp] = useState<string | null>(null)
  const afterClose = nowHMS().slice(0, 5) >= '15:30'
  const importCsv = async (file: File | null) => {
    try {
      const text = file ? await file.text() : ''
      const r = await j<{ ok: boolean; why?: string; imported?: string[]; matched_marked?: number; rows_written?: Record<string, number> }>('/api/hold/import', undefined, text)
      setImp(r.ok ? `day completed — ${r.imported?.length ?? 0} imported, ${r.matched_marked ?? 0} already marked, `
                    + `${Object.values(r.rows_written || {}).reduce((a, b) => a + b, 0)} rows written` : (r.why || 'the import did not land'))
    } catch (e) { setImp(`the import did not land (${(e as Error).message})`) }
  }

  const inView = mode === 'in' && current
  const rd = current ? st.reads[current.id] : undefined
  const row = ladder.find(s => s.strike === strike)
  const prem = row ? (side === 'CE' ? row.ceLtp : row.peLtp) : null
  const money = (k: number) => k === atm ? 'ATM' : (side === 'CE' ? k < chain.spot : k > chain.spot) ? 'ITM' : 'OTM'
  const step = (d: number) => { const i = ladder.findIndex(s => s.strike === strike); const n = ladder[i + d]; if (n) setStrike(n.strike) }
  const riskScale = ck?.ok && lot && ck.trade?.qty ? (lots * lot) / ck.trade.qty : 1

  return (
    <div className="hv validate">
      <div className="mkt-row"><MarketNow index={index} busy={!!inView || !!ck?.ok || busy} /></div>
      <aside className="slip" aria-label="Your contract">
        {inView ? <TradeCard t={current} rd={rd} exitT={exitT} setExitT={setExitT} onOut={() => imOut(current)} onBack={() => setMode('check')} /> : (
          <form onSubmit={e => { e.preventDefault(); validateNow() }} autoComplete="off" className="slip-form">
            {!editing && ck?.ok ? (
              <div className="echo-card">
                <span className="label">You are checking</span>
                <div className="c">{index} {strike} {side}</div>
                <div className="s">{role === 'long' ? 'BUY · long' : 'SELL · short'} · {lotsText(lots)}{lot ? ` (${lots * lot})` : ''}
                  {' '}<button type="button" className="link" onClick={() => setEditing(true)}>change</button></div>
              </div>
            ) : <>
              <fieldset className="field"><legend className="label">Index</legend>
                <Seg opts={IDX} v={index} on={i => onIndex(i as IndexKey)} /></fieldset>
              <div className="field"><span className="label">Strike</span>
                <div className="strike">
                  <button type="button" aria-label="One strike lower" onClick={() => step(-1)}><Ico n="Minus" /></button>
                  <select value={strike} onChange={e => setStrike(+e.target.value)} aria-label="Strike">
                    {ladder.map(s => <option key={s.strike} value={s.strike}>{s.strike}  ·  {money(s.strike)}</option>)}
                  </select>
                  <button type="button" aria-label="One strike higher" onClick={() => step(1)}><Ico n="Plus" /></button>
                </div>
                <span className="hint">{chain?.spot ? <>{index} <N t="M">{inr(chain.spot, 1, 2)}</N> · ATM {atm}</> : 'the ladder has not loaded yet'}
                  {prem != null && <> · {side} now <N t="I">{inr(prem, 2)}</N></>}</span>
              </div>
              <div className="pair">
                <fieldset className="field"><legend className="label">Option</legend>
                  <Seg opts={['CE', 'PE']} v={side} on={x => setSide(x as 'CE' | 'PE')} /></fieldset>
                <fieldset className="field"><legend className="label">You</legend>
                  <Seg opts={['long', 'short']} v={role} on={x => setRole(x as 'long' | 'short')}
                       labels={{ long: <>BUY <small>long</small></>, short: <>SELL <small>short</small></> }} /></fieldset>
              </div>
              <div className="field"><span className="label">Qty</span>
                <div className="stepper" role="group" aria-label="Lots">
                  <button type="button" aria-label="One lot less" disabled={lots <= 1} onClick={() => setLots(Math.max(1, lots - 1))}><Ico n="Minus" /></button>
                  <output>{lotsText(lots)}</output>
                  <button type="button" aria-label="One lot more" onClick={() => setLots(lots + 1)}><Ico n="Plus" /></button>
                </div>
                <span className="hint">{lot ? <>= <span className="num">{inr(lots * lot)}</span> qty · lot {lot}</> : <Abs text="could not check — the lot size is not loaded; the check reads per unit" />}</span>
              </div>
            </>}
            <button type="submit" className="btn btn-validate" disabled={busy || !strike}>{busy ? 'CHECKING…' : ck?.ok && !editing ? 'VALIDATE AGAIN' : 'VALIDATE'}</button>
            <p className="fine">Each press is logged. Keys: C/P · B/S · ↑↓ strike · Enter · I = I'm in</p>
            {setupLine && <p className="fine xp-setup">{setupLine}</p>}
            <Cutoff />

            <div className="took">
              <span className="label">Took it?</span>
              <div className="pair">
                <label className="field"><span className="hint">Fill time</span>
                  <input className="inp" value={fill.t} placeholder="now" disabled={!ck?.ok || stale} onChange={e => setFill({ ...fill, t: e.target.value })} /></label>
                <label className="field"><span className="hint">Fill price ₹</span>
                  <input className="inp" type="number" step="any" min="0" inputMode="decimal" value={fill.p} disabled={!ck?.ok || stale}
                         onChange={e => setFill({ ...fill, p: e.target.value })} /></label>
              </div>
              <span className="hint">{ck?.ok && !stale
                ? <>Price from {ck.p0_src === 'you' ? 'you' : (ck.p0_src || '').replace(' [I]', '')}<T t="I" />; time empty = when you press. Use your broker's fill.</>
                : 'After an answer.'}</span>
              <button type="button" className="btn btn-in" disabled={!ready} onClick={imIn}>{marking ? 'MARKING…' : "I'M IN — WATCH IT FOR ME"}</button>
              <Err>{msg}</Err>
            </div>
          </form>
        )}
        {undo && <div className="undo">{undo.label} marked out <button type="button" className="link" onClick={reopen}>Undo</button></div>}
        {st.trades.length > 0 && (
          <div className="today">
            <span className="label">Today's trades</span>
            {st.trades.map(t => {
              const w = st.reads[t.id]?.now?.verdict
              return (
                <button type="button" key={t.id} aria-pressed={!!inView && t.id === sel} onClick={() => open(t)}>
                  <span>{!t.exit_t && w && <b className={`word ${vcls(w)}`}>{w} </b>}{t.idx} {t.k} {t.side} · {t.role}</span>
                  <span className="num">{t.t0.slice(0, 5)}{t.exit_t ? `–${t.exit_t.slice(0, 5)}` : ' · open'}</span>
                </button>
              )
            })}
          </div>
        )}
        {afterClose && (
          <div className="took">
            <span className="label">After the close</span>
            <label className="link" style={{ cursor: 'pointer', alignSelf: 'flex-start' }}>import tradebook CSV
              <input type="file" accept=".csv,text/csv" hidden onChange={e => importCsv(e.target.files?.[0] || null)} /></label>
            <button type="button" className="link" style={{ alignSelf: 'flex-start' }} onClick={() => importCsv(null)}>complete today's log without a CSV</button>
            {imp && <span className="hint">{imp}</span>}
          </div>
        )}
      </aside>

      <section className={`answer${!inView && stale ? ' stale' : ''}`} aria-live="polite">
        {inView ? <InView t={current} rd={rd} open={st.trades.filter(t => !t.exit_t)} flip={st.flips[current.id]} err={st.err} />
          : busy ? <Loading label={`${index} ${strike} ${side}`} role={role} lots={lots} />
          : !ck ? <Empty />
          : !ck.ok ? <div className="empty fresh"><span className="label">No answer</span><h2>Nothing to read for that contract right now.</h2><div className="abs-list"><Abs text={ck.why} /></div></div>
          : !ck.validate ? <div className="empty fresh"><div className="abs-list"><Abs text="could not check — the server needs a restart to give the word" /></div></div>
          : <CheckView ck={ck} v={ck.validate} at={asked?.at} stale={stale} riskScale={riskScale} onAgain={validateNow}
                       onIn={imInCard} busy={marking} />}
      </section>
    </div>
  )
}

function Seg({ opts, v, on, labels }: { opts: string[]; v: string; on: (v: string) => void; labels?: Record<string, ReactNode> }) {
  return (
    <div className="seg" role="group">
      {opts.map(o => <button type="button" key={o} aria-pressed={v === o} onClick={() => on(o)}>{labels?.[o] ?? o}</button>)}
    </div>
  )
}

function Empty() {
  return (
    <div className="empty fresh">
      <span className="label">Before you take it</span>
      <h2>Pick the contract, then press VALIDATE.</h2>
      <p>The answer is one word, and four marks: which of four facts line up with your trade. A count, not odds. Nothing is sent to your broker.</p>
      <div className="legend">
        <span className="word v-GO">GO</span><p>Right now reads HOLD, nothing is against you, and at most one fact is not there yet.</p>
        <span className="word v-WAIT">WAIT</span><p>In between. It names what would have to change.</p>
        <span className="word v-NO">NO</span><p>You would be entering a FOLD — the window's own rule, read at entry.</p>
      </div>
      <div className="five"><span className="label">The four</span><ol>{NAMES.map(n => <li key={n}>{n}</li>)}</ol></div>
    </div>
  )
}

function Loading({ label, role, lots }: { label: string; role: string; lots: number }) {
  const sk = (w: number, h: number) => <span className="sk" style={{ width: w, height: h }} />
  return (
    <>
      <div className="echo"><span className="label">Checking</span><span className="c">{label}</span>
        <span className="dot">·</span><span>{role === 'long' ? 'BUY · long' : 'SELL · short'}</span><span className="dot">·</span><span>{lotsText(lots)}</span></div>
      <div className="band">
        <div className="w">{sk(176, 80)}</div>
        <div className="cnt">{sk(120, 40)}<span style={{ height: 8 }} />{sk(96, 12)}</div>
        <div className="say">{sk(420, 16)}{sk(300, 16)}<span className="fine">Reading your setup, the side and the walls…</span></div>
      </div>
      <div className="body">
        <div><div className="sec-h"><span className="label">The facts</span><span className="note">reading</span></div>
          {NAMES.map(n => <div className="fact" key={n}><span /><span className="nm">{n}</span><span className="st muted">…</span>{sk(360, 14)}<span /></div>)}</div>
        <div className="nums">{['Stop', 'Next wall', 'Premium · Delta'].map(l => <div className="nb" key={l}><span className="label">{l}</span><div className="nb-top">{sk(150, 28)}{sk(56, 20)}</div></div>)}</div>
      </div>
    </>
  )
}

function useTick(ms: number) {
  const [, t] = useState(0)
  useEffect(() => { const i = setInterval(() => t(x => x + 1), ms); return () => clearInterval(i) }, [ms])
}

function CheckView({ ck, v, at, stale, riskScale, onAgain, onIn, busy }: { ck: Check; v: Verdict; at?: string; stale: boolean; riskScale: number; onAgain: () => void
                                                                        onIn: (c: XCard) => void; busy: boolean }) {
  const [open, setOpen] = useState<Record<string, boolean>>({})
  useTick(5000)
  const tr = ck.trade!, n = ck.now!, g = ck.greeks
  const age = ageSec(ck.asof) ?? 0, old = !stale && age > OLD_S
  return (
    <div className={`fresh${old ? ' aged' : ''}`}>
      {stale && <div className="stale-note"><Ico n="Undo" /><span>You changed the contract. This answer is for the one you checked. Press VALIDATE again.</span></div>}
      {old && <div className="stale-note"><Ico n="Undo" /><span>This answer is {Math.floor(age / 60)} min old — the market has moved a bar.</span>
        <button type="button" className="btn btn-sm" onClick={onAgain}>VALIDATE AGAIN</button></div>}
      {ck.expr ? <Expression x={ck.expr} idx={tr.idx} onIn={onIn} busy={busy || stale} />
        : <div className="xp"><Abs text="not shown — the expression needs the server restarted on the new code" kind="hidden" /></div>}
      <div className="echo">
        <span className="label">Answer for</span><span className="c">{tr.idx} {tr.k} {tr.side}</span>
        <span className="dot">·</span><span>{tr.role === 'long' ? 'BUY · long' : 'SELL · short'}</span>
        <span className="dot">·</span><Age asof={ck.asof} stale={OLD_S} />{at && <span className="fine">pressed {at}</span>}
        <span className="right"><span className="fine">nothing is sent to your broker</span><span className="draft" title={v.draft}>DRAFT</span></span>
      </div>
      <div className={`band${v.word === 'NO' ? ' red' : ''}${ck.expr?.ok ? ' mine' : ''}`}>
        <h2 className="w"><span className={`word ${vcls(v.word || 'PATA NAHI')}`}>{v.word || '—'}</span></h2>
        <div className="cnt">
          <Marks facts={v.facts} />
          <div className="sub">{v.count}<T t={v.tag || 'I'} /></div>
        </div>
        <div className="say">
          <p className="clamp3" title={v.sentence}>{v.sentence}</p>
          {v.word === 'WAIT' && v.needs.length > 0 && (
            <div className="needs"><span className="label">{v.n_against ? 'What would have to change' : 'Not there yet'}</span>
              <ul>{v.needs.map(x => { const f = v.facts.find(f => f.name === x); return <li key={x}><Ico n="ArrowRight" /><span><b>{x}</b>{f && !f.absence ? ` — ${f.text}` : ''}</span></li> })}</ul></div>
          )}
          {v.writer_note && <Abs text={v.writer_note} kind="hidden" />}
          {v.printed && v.printed.length > 0 && <p className="fine">Printed, not counted: {v.printed.join(' · ')}</p>}
        </div>
      </div>
      <div className="body">
        <div>
          <div className="sec-h"><span className="label">The facts</span><span className="note">in the order of the marks</span></div>
          {v.facts.map(f => {
            const can = f.text.length > 110 && !f.absence
            const flip = () => can && setOpen({ ...open, [f.name]: !open[f.name] })
            return (
              <div key={f.name} className={`fact${can ? ' can' : ''}${open[f.name] ? ' open' : ''}`} data-st={f.state}
                   role={can ? 'button' : undefined} tabIndex={can ? 0 : undefined} aria-expanded={can ? !!open[f.name] : undefined}
                   onClick={flip} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); flip() } }}>
                <Mark st={f.state} /><span className="nm">{f.name}</span><span className="st">{f.absence ? '—' : f.state}</span>
                <span className="tx">{f.absence ? <Abs text={f.text} kind={f.absence} /> : f.text}</span><Ico n="ChevronDown" c="chev" />
              </div>
            )
          })}
        </div>
        <div className="nums">
          <StopBlock p={ck.plan} n={n} idx={tr.idx} riskScale={riskScale} noise={v.noise ?? null} />
          <WallBlock p={ck.plan} />
          <div className="nb nb2">
            <div><span className="label">Premium</span>
              {n.prem.c != null ? <><div className="mid"><N t={n.prem.tag || 'I'}>{rs(n.prem.c, 2)}</N></div><div className="sub">last trade at {ck.asof}</div></>
                : <div><Abs text={n.prem.why || 'could not check — no premium for this contract on the chain'} /></div>}</div>
            <div><span className="label">Delta</span>
              {g?.delta != null ? <><div className="mid"><N t={g.tag || 'M'}>{(g.delta < 0 ? '−' : '+') + Math.abs(g.delta).toFixed(2)}</N></div>
                {g.gamma != null && <div className="sub">gamma <N t={g.tag || 'M'}>{g.gamma}</N></div>}</>
                : <div><Abs text={g?.why || 'could not check — no greeks for this contract'} /></div>}</div>
          </div>
        </div>
      </div>
      <details className="deep">
        <summary><Ico n="ChevronDown" />Deeper detail <span className="muted">— if you enter now, the plan, the zone, the side read, what is absent</span></summary>
        <div className="deep-grid">
          <section><h4 className="label">If you enter now</h4>{ck.entry && <p className="sm">{ck.entry.text}</p>}<Rows n={n} /></section>
          <section>{ck.plan && <PlanList p={ck.plan} qty={tr.qty} />}<Zone z={ck.zone} /></section>
          <section>{ck.side && <SideList s={ck.side} />}<AbsentList a={ck.absent} extra={v.not_shown || []} />
            <h4 className="label">Draft</h4><p className="fine">{v.draft}</p>{ck.note && <p className="fine">{ck.note}</p>}</section>
        </div>
      </details>
    </div>
  )
}

// ---------------------------------------------------------------- THE EXPRESSION (EXPRESSION-PREREG.md rev e §F.1)
const XCOL: [XFact['state'], string][] = [['buy', 'For buy'], ['sell', 'For sell'], ['neither', 'Neither']]
const fmtD = (x: number) => (x < 0 ? '−' : '+') + Math.abs(x).toFixed(2)

function Expression({ x, idx, onIn, busy }: { x: Expr; idx: string; onIn: (c: XCard) => void; busy: boolean }) {
  const [sig, setSig] = useState<Record<string, { z?: number | null; why?: string; tag?: string }>>({})
  useEffect(() => {                                   // σ vs its own VWAP, printed: fetched after the answer (a REST read)
    let live = true
    for (const c of [x.buy, x.sell]) if (c) j<{ z?: number | null; why?: string; tag?: string }>(`/api/hold/sigma?idx=${idx}&k=${c.k}&side=${c.side}`)
      .then(r => { if (live) setSig(s => ({ ...s, [c.side]: r })) }).catch(e => { if (live) setSig(s => ({ ...s, [c.side]: { why: `could not check — ${(e as Error).message}` } })) })
    return () => { live = false }
  }, [x.buy?.k, x.buy?.side, idx])
  if (!x.ok) return (
    <section className="xp"><div className="xp-h"><span className="label">The expression · {x.dir} · {idx}</span><span className="draft" title={x.draft}>DRAFT</span></div>
      <div className="xp-absent"><Abs text={x.why || 'could not check — the expression'} /></div>
      {x.setup_line && <p className="fine">{x.setup_line}</p>}</section>)
  // the word's second line is the server's own refusal sentences (§F.1 item 1), in the caution ink; the count is its `count`
  const note = x.refused?.length ? x.refused.join('; ') : null, aside = x.base === 'STAND ASIDE', pr = x.printed
  const head = x.base === 'EITHER' || aside ? x.base : `${x.base!.replace('LEANS ', '')} ${x.leg}`
  return (
    <section className="xp" aria-label="The expression — buy the option, or sell the other side">
      <div className="xp-h"><span className="label">The expression · {x.dir} · {idx}</span>
        <span className="fine">which leg expresses your direction — not a second VALIDATE</span><span className="draft" title={x.draft}>DRAFT</span></div>
      <div className="xp-band">
        <div className="xp-w">
          {x.leans && <span className="word xp-leans">LEANS</span>}
          <h2 className={`word xp-word${aside ? ' v-WAIT' : ''}`}>{head}</h2>
          {note && <p className="xp-note">{note}</p>}
        </div>
        <div className="xp-meta">
          <p>since <span className="num">{x.since}</span>{x.was && <> · was {x.was.word} until <span className="num">{x.was.until}</span></>} · read at the <span className="num">{x.read_at}</span> close</p>
          {x.since_gap && <Abs text={x.since_gap} />}
          <p className="xp-count">{x.count}<T t="I" /></p>
        </div>
      </div>
      <div className="xp-cards">{[x.buy!, x.sell!].map(c => <XCardView key={c.side} c={c} sig={sig[c.side]} onIn={onIn} busy={busy} />)}</div>
      <div className="xp-facts" role="table" aria-label="The five facts">
        <div className="xp-fr xp-fh" role="row"><span role="columnheader" className="label">Fact</span>
          {XCOL.map(([, l]) => <span key={l} role="columnheader" className="label">{l}</span>)}</div>
        {(x.facts || []).map(f => (
          <div key={f.name} className="xp-fr" role="row" data-st={f.state}>
            <span className="nm" role="cell">{f.name}</span>
            {XCOL.map(([s]) => <span key={s} role="cell" className="xp-m">{f.state === s && <Ico n={s === 'neither' ? 'Minus' : 'Check'} c="xp-mk" />}</span>)}
            <span className="xp-tx" role="cell">{f.absence ? <Abs text={f.text} kind={f.absence} /> : <>{f.state === 'neither' && <b className="muted">a read — </b>}{f.text}</>}<T t={f.tag} /></span>
          </div>))}
      </div>
      <div className="xp-print"><span className="label">Printed, not counted</span>
        <p>{pr?.drag.text ?? <Abs text={pr?.drag.why} />}</p>
        <p>{pr?.expiry ? <>{pr.expiry}<T t="M" /></> : <Abs text="could not check — the expiry is not in the day's record" />}</p>
        <p>{pr?.regime.word !== undefined && pr.regime.price ? <>the board's REGIME: <b>{pr.regime.word ?? '—'}</b> · price {pr.regime.price[0]} · OI {pr.regime.oi?.[0]}<T t="I" /></>
          : <Abs text={pr?.regime.why || 'could not check — the board regime'} />}</p>
        {[x.buy!, x.sell!].map(c => { const s = sig[c.side]; return <p key={c.side}>{c.side} {inr(c.k)}: {s == null ? <span className="muted">reading…</span>
          : s.z != null ? <>premium <N t={s.tag || 'M'}>{`${s.z > 0 ? '+' : ''}${s.z}σ`}</N> vs its own VWAP</> : <Abs text={s.why} />}</p> })}
      </div>
      <div className="abs-list xp-not">{x.not_shown.map(t => <Abs key={t} text={t} />)}</div>
    </section>
  )
}

function XCardView({ c, sig, onIn, busy }: { c: XCard; sig?: { z?: number | null; why?: string; tag?: string }; onIn: (c: XCard) => void; busy: boolean }) {
  const buy = c.role === 'long', v = c.validate
  return (
    <div className={`xp-card${c.named ? ' named' : ''}${c.refused.length ? ' refused' : ''}`}>
      <div className="xp-ch"><span className="word">{buy ? 'BUY' : 'SELL'} {c.side} {inr(c.k)}</span>
        <span className="fine">ATM · {c.expiry || 'expiry not in the day\'s record'}{!buy && c.delta != null && <> · Δ <N t={c.greeks_tag}>{fmtD(c.delta)}</N></>}</span></div>
      {c.refused.length > 0 && <p className="xp-note">{buy ? 'buying' : 'selling'} refused: {c.refused.join('; ')}</p>}
      <div className="xp-cb">
        <div><span className="label">{buy ? 'VALIDATE' : 'The writer\'s VALIDATE'}</span>
          <div className={`word xp-vw ${vcls(v?.word || 'PATA NAHI')}`}>{v?.word || '—'}</div>
          {v?.word ? <span className="fine">{v.count}</span> : <Abs text={v?.sentence || 'could not check — this leg\'s word'} />}</div>
        <dl className="kv">
          <dt>Premium</dt><dd>{c.px != null ? <><N t={c.px_tag}>{rs(c.px, 2)}</N> <span className="muted">at {c.px_t}</span></> : <Abs text={`could not check — no premium for ${c.side} ${c.k} at ${c.px_t}`} />}</dd>
          <dt>Δ</dt><dd>{c.delta != null ? <N t={c.greeks_tag}>{fmtD(c.delta)}</N> : <Abs text={c.greeks_why} />}</dd>
          <dt>Entry check</dt><dd>{c.entry ? <b className={`word ${vcls(c.entry)}`}>{c.entry}</b> : <Abs text="could not check — the entry check" />}</dd>
          {!buy && <><dt>Wall behind it</dt><dd>{c.wall ? <>{c.side} <N t="M">{inr(c.wall.k)}</N> · {c.wall.state.toLowerCase()}</>
            : <Abs text="checked, none — no wall behind the sale (R6)" />}</dd>
            {c.line_vs_strike && <><dt>Your line</dt><dd>{c.line_vs_strike}</dd></>}</>}
          <dt>σ</dt><dd>{sig == null ? <span className="muted">reading…</span> : sig.z != null ? <N t={sig.tag || 'M'}>{`${sig.z > 0 ? '+' : ''}${sig.z}σ`}</N> : <Abs text={sig.why} />}</dd>
        </dl>
        {c.s4 && <p className="fine">On 0DTE: {c.s4}</p>}
        <p className="fine">{c.atm}</p>
      </div>
      <button type="button" className="btn btn-in" disabled={busy} onClick={() => onIn(c)}>I'M IN — {buy ? 'BUY' : 'SELL'} {c.side} {inr(c.k)}</button>
    </div>
  )
}

function Zone({ z }: { z?: Check['zone'] }) {
  const line = (e: ZoneEv | null) => e && (
    <div className="zr"><Mark st={e.agrees === 'agrees' ? 'for' : e.agrees === 'against' ? 'against' : 'neither'} />
      <div><b>{e.side} {e.band}</b> {e.kind ?? ''} <span className="num">{e.t}</span> <span className="muted">({e.ago} min ago)</span> · gate {e.legal ? 'legal' : e.legal === false ? 'not legal' : 'not read'}
        {e.px != null && <> · at <N t={e.tag || 'M'}>{inr(e.px, 1)}</N></>}
        <div className="muted">{e.why}{e.agrees ? ` — ${e.agrees}` : ''}</div></div></div>
  )
  return <><h4 className="label">Your setup — the zone machine</h4>{line(z?.trigger ?? null)}{line(z?.arm ?? null)}{z?.why && <Abs text={z.why} />}
    {!z?.trigger && !z?.arm && !z?.why && <Abs text="checked, none — no zone trigger on this index today" />}</>
}

function TradeCard({ t, rd, exitT, setExitT, onOut, onBack }: { t: Trade; rd?: Held; exitT: string; setExitT: (v: string) => void; onOut: () => Promise<void>; onBack: () => void }) {
  const [busy, setBusy] = useState(false)
  return (
    <div className="tcard">
      <span className="label">Your marked trade</span>
      <div><div className="c">{t.idx} {t.k} {t.side}</div><div className="s">{t.role === 'long' ? 'BUY · long' : 'SELL · short'} · qty {t.qty}</div></div>
      <dl className="kv">
        <dt>In at</dt><dd className="num">{t.t0}</dd>
        <dt>Fill</dt><dd>{t.p0 != null ? <><span className="num">{rs(t.p0, 2)}</span> <span className="muted">your fill</span></> : '—'}</dd>
        {t.exit_t && <><dt>Out at</dt><dd className="num">{t.exit_t}{t.exit_t_broker ? ` · broker ${t.exit_t_broker}` : ''}</dd></>}
      </dl>
      {t.exit_t ? <button type="button" className="btn" onClick={onBack}>BACK TO VALIDATE</button> : <>
        <label className="field"><span className="hint">Exit time</span>
          <input className="inp" value={exitT} placeholder="now" onChange={e => setExitT(e.target.value)} /></label>
        <button type="button" className="btn btn-in" disabled={busy} onClick={async () => { setBusy(true); await onOut(); setBusy(false) }}>I'M OUT — STOP WATCHING</button>
        <span className="hint">Key O. You get 10 s to undo.</span>
        <button type="button" className="link" style={{ alignSelf: 'flex-start' }} onClick={onBack}>check another trade (this one stays watched)</button>
      </>}
      {rd?.after_exit && <p className="fine">You are out; the read is still logged to 15:29.</p>}
      <div className="words">
        <span className="label">The four words</span>
        <span className="word v-HOLD">HOLD</span><p>The reason you entered still stands. "· NOISE" means the premium is red but nothing that holds it changed.</p>
        <span className="word v-WATCH">WATCH</span><p>Something moved against you. It lists what would make it FOLD.</p>
        <span className="word v-FOLD">FOLD</span><p>A fold rule matched. The header turns red, and only "I'm out" clears it.</p>
        <span className="word v-PATA">PATA NAHI</span><p>Don't know: a needed input is missing.</p>
      </div>
    </div>
  )
}

function InView({ t, rd, open, flip, err }: { t: Trade; rd?: Held; open: Trade[]; flip?: { t: string; rows: string[] }; err: string | null }) {
  if (!rd) return <div className="empty"><span className="label">Reading your trade…</span></div>
  if (!rd.ok || !rd.now) return <div className="empty fresh"><span className="label">No reading</span><div className="abs-list"><Abs text={rd.why || 'could not check — no reading yet'} /></div></div>
  const n = rd.now, runs = rd.runs || [], red = n.verdict === 'FOLD', fold = rd.fold
  const entryRoom = rd.plan?.entry?.stop?.room
  // under a latch the server's checked_none slot carries the latch rule -- a rule statement, printed plain (not an absence)
  const rule = fold ? rd.absent?.checked_none?.replace(/^checked, none — /, '') : null
  return (
    <div className="fresh">
      <div className="echo">
        <span className="label">Watching your trade</span><span className="c">{t.idx} {t.k} {t.side}</span>
        <span className="dot">·</span><span>{t.role === 'long' ? 'BUY · long' : 'SELL · short'} · qty <span className="num">{t.qty}</span></span>
        <span className="dot">·</span><span>in <span className="num">{t.t0}</span>{t.p0 != null && <> at <span className="num">{rs(t.p0, 2)}</span></>}</span>
        {t.exit_t && <><span className="dot">·</span><span>out <span className="num">{t.exit_t}</span></span></>}
        <span className="dot">·</span><Age asof={rd.asof} /><Cutoff open={!t.exit_t} />
        <span className="right"><span className="fine">nothing is sent to your broker</span><span className="draft" title={rd.draft}>DRAFT</span></span>
      </div>
      {err && <div className="stale-note"><Abs text={err} /></div>}
      <div className={`band${red ? ' red' : ''}`}>
        <h2 className="w"><span className={`word ${vcls(n.verdict)}`}>{n.verdict}<Qual tag={n.tag} /></span>
          <Live n={n} />
          <span className="since">since <span className="num">{n.since}</span>{t.role === 'long' && <> · <Quiet n={n} /></>}</span></h2>
        <div className="cnt">
          <div className="label">live read</div>
          <div className="n n28">{n.n_for}<span className="of"> for · </span>{n.n_against}<span className="of"> against</span></div>
          <div className="odds">a count, not odds</div>
        </div>
        <div className="say">
          {fold ? <Fired fold={fold} /> : <p>{cap(strip(n.sentence))}</p>}
          {rule && <p className="sm">{rule}</p>}
          <div className="band-rows"><Rows n={n} /></div>
          {flip && flip.rows.length > 0 && <p className="sm flip">changed {flip.t}: {flip.rows.join(' · ')}</p>}
          <WatchList n={n} />
          {rd.entry?.head && <p className="sm" style={{ fontWeight: 600 }}>{rd.entry.text}</p>}
          {!red && n.verdict === 'HOLD' && <Abs text={rd.absent?.checked_none} kind="none" />}
        </div>
      </div>
      <div className="body">
        <div className="runs">
          <div className="sec-h"><span className="label">What it said since you entered</span>
            {rd.entry && <span className="note">you entered at {rd.entry.t} into {rd.entry.verdict}{entryRoom != null ? `, ${roomText(entryRoom)} from your line` : ''}</span>}</div>
          {n.flow.state === 'blind' && <div style={{ padding: '8px 0' }}><Abs text="could not check — order flow is blind: two-family FOLDs read OI and trend only" /></div>}
          {twoLegs(open) && <div style={{ padding: '8px 0' }}><Abs text="not shown — a two-leg position is not registered; each leg is read as its own direction" /></div>}
          {runs.length ? runs.map((r, i) => (
            <div key={r.from} className={`run${i === runs.length - 1 ? ' now' : ''}`}>
              <span className="t">{span(r)}</span>
              <span className={`wd word ${vcls(r.verdict)}`}>{r.verdict}{r.tag && <small>{r.tag}</small>}</span>
              <span className="tx">{cap(strip(r.sentence))}</span>
            </div>
          )) : <div style={{ padding: 8 }}><Abs text="checked, none — no finished minute since your entry yet" /></div>}
        </div>
        <div className="nums">
          <StopBlock p={rd.plan} n={n} idx={t.idx} fold={fold} />
          <WallBlock p={rd.plan} />
          <div className="nb">
            <span className="label">Premium</span>
            {n.prem.c != null ? <>
              <div className="nb-top"><span className="big"><N t={n.prem.tag || 'I'}>{rs(n.prem.c, 2)}</N></span></div>
              {t.p0 != null && <div className="sub">in at <span className="num">{rs(t.p0, 2)}</span> <span className="muted">your fill</span></div>}
              <div><Sigma rd={rd} /></div>
              {n.prem.pnl != null && <div className="pnl">P&amp;L <N t={n.prem.tag || 'I'}>{(n.prem.pnl < 0 ? '−' : '+') + rs(Math.abs(n.prem.pnl))}</N></div>}
            </> : <div><Abs text={n.prem.why || 'could not check — no premium on the chain'} /></div>}
          </div>
        </div>
      </div>
      <details className="deep">
        <summary><Ico n="ChevronDown" />Deeper detail <span className="muted">— at entry, the plan, the side read, what is absent</span></summary>
        <div className="deep-grid">
          <section>{rd.entry && <><h4 className="label">At entry</h4><p className="sm">{rd.entry.text}</p></>}</section>
          <section>{rd.plan && <PlanList p={rd.plan} qty={t.qty} />}{rd.side && <SideList s={rd.side} />}</section>
          <section><AbsentList a={rd.absent} extra={[rd.sigma?.why]} latched={!!fold} />
            {rd.src_data && <><h4 className="label">Sources</h4><dl className="kv">{Object.entries(rd.src_data).flatMap(([k, v]) => [<dt key={k}>{k}</dt>, <dd key={`${k}.v`}>{v}</dd>])}</dl></>}
            <h4 className="label">Draft</h4><p className="fine">{rd.draft}</p>{rd.plan?.draft && <p className="fine">{rd.plan.draft}</p>}{rd.note && <p className="fine">{rd.note}</p>}</section>
        </div>
      </details>
    </div>
  )
}
