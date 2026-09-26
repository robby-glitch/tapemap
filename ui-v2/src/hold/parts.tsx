// The pieces the Validate tab and the floating hold window share, so the two can never print
// different facts: the marks, the three absences, the [M]/[I] tags, the word with its qualifier, the
// quiet clock, the age of the read, the stop and wall blocks, the four rows, the plan, the side read.
// Presentation only -- the server's hold.py / plan.py / validate.py are the rules. Styles: ./hold.css.
import { Component, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { Now, PlanRow, Reading, SideRead } from './HoldWindow'
import { ageSec } from './store'
import './hold.css'

const PATHS = {   // Lucide (ISC), inlined: the app carries no icon package
  Check: '<path d="M20 6 9 17l-5-5"/>',
  X: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  Minus: '<path d="M5 12h14"/>',
  Plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  ChevronDown: '<path d="m6 9 6 6 6-6"/>',
  ChevronUp: '<path d="m18 15-6-6-6 6"/>',
  ArrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  EyeOff: '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><path d="m2 2 20 20"/>',
  SearchX: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="m13.5 8.5-5 5"/><path d="m8.5 8.5 5 5"/>',
  Ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  PiP: '<path d="M21 9V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10c0 1.1.9 2 2 2h4"/><rect width="10" height="7" x="12" y="13" rx="2"/>',
  Undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"/>',
}
export function Ico({ n, c = '' }: { n: keyof typeof PATHS; c?: string }) {
  return <svg className={`i ${c}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"
              strokeLinejoin="round" aria-hidden="true" dangerouslySetInnerHTML={{ __html: PATHS[n] }} />
}

export const inr = (x: number, min = 0, max = min) => x.toLocaleString('en-IN', { minimumFractionDigits: min, maximumFractionDigits: max })
export const rs = (x: number, dp = 0) => '₹' + inr(x, dp)
export const vcls = (w: string) => 'v-' + (w === 'PATA NAHI' ? 'PATA' : w)
export const strip = (s: string) => s.replace(/^(?:HOLD|WATCH|FOLD|PATA NAHI)\b[^—]*? — /, '')   // the word, its qualifier and "since" are shown apart
/** Points to the line: "past it" once the index has closed beyond it -- never a negative distance. */
export const roomText = (room: number) => room < 0 ? `${Math.abs(room)} pts past it` : `${room} pts`
export const cap = (s: string) => s ? s[0].toUpperCase() + s.slice(1) : s
export const nowHMS = () => new Date().toTimeString().slice(0, 8)

export function T({ t }: { t?: string | null }) {
  return t ? <span className="tag" title={t === 'M' ? 'measured' : 'inferred'}>[{t}]</span> : null
}
export function N({ children, t }: { children: ReactNode; t?: string | null }) {
  return <><span className="num">{children}</span><T t={t} /></>
}

const MARKS: Record<string, [keyof typeof PATHS, string]> = {
  for: ['Check', 'm-for'], against: ['X', 'm-against'], neither: ['Minus', 'm-neither'], flat: ['Minus', 'm-neither'], blind: ['EyeOff', 'm-blind'],
}
export function Mark({ st }: { st: string }) {
  const m = MARKS[st]
  return m ? <Ico n={m[0]} c={m[1]} /> : <span />
}
export const WALL: Record<string, string> = { 'GIVING WAY': 'for', DEFENDED: 'against', STALLED: 'neither' }
const ROW_WORD: Record<string, string> = { for: 'for', against: 'against', flat: 'flat', blind: 'could not check' }

/** The three absences, never one rendering (CLAUDE.md rule 6): solid = looked and found none,
 *  dashed = could not look, hatched = not shown to you. `kind` when the server says which. */
export function Abs({ text, kind }: { text?: string | null; kind?: 'none' | 'blind' | 'hidden' | null }) {
  if (!text) return null
  const s = String(text), i = s.indexOf(' — ')
  const k = kind || (s.startsWith('checked, none') ? 'none' : s.startsWith('could not check') ? 'blind' : 'hidden')
  const head = i > 0 ? s.slice(0, i) : s, rest = i > 0 ? s.slice(i + 3) : ''
  return (
    <span className={`abs abs-${k}`}>
      <Ico n={k === 'none' ? 'SearchX' : k === 'blind' ? 'EyeOff' : 'Ban'} />
      <span><b>{head}</b>{rest ? ` — ${rest}` : ''}</span>
    </span>
  )
}
/** A failure of the screen itself (a click that did not land) -- not one of the three market absences. */
export const Err = ({ children }: { children?: ReactNode }) => children ? <span className="err">{children}</span> : null

/** The word's qualifier, in the word slot -- "HOLD · NOISE" is the anti-panic word (REVIEW P0-5). */
const QUAL: Record<string, [string, string]> = {
  noise: ['NOISE', ''], 'structure only': ['STRUCTURE ONLY', 'q-unknown'], 'OI blind': ['OI BLIND', 'q-unknown'], 'nothing paying': ['NOTHING PAYING', 'q-caution'] }
export function Qual({ tag }: { tag?: string | null }) {
  const q = tag ? QUAL[tag] : null
  return q ? <span className={`qual ${q[1]}`}> · {q[0]}</span> : null
}

/** The buyer's quiet clock: her own rule-5 FOLD, "visible at all times" (§3.5; REVIEW P0-8). */
export function Quiet({ n }: { n?: Now }) {
  const c = n?.clock
  if (!c || c.quiet == null || !c.of) return null
  return <span className={`quiet${c.quiet >= 10 ? ' warm' : ''}`} title={c.text}>quiet <span className="num">{c.quiet}/{c.of}</span></span>
}

/** How old the read is: the minute it read finished at HH:MM+1 (REVIEW P1-10). Ticks every second. */
export function Age({ asof, stale = 90 }: { asof?: string; stale?: number }) {
  const [, tick] = useState(0)
  useEffect(() => { const t = setInterval(() => tick(x => x + 1), 1000); return () => clearInterval(t) }, [])
  const a = ageSec(asof)
  if (a == null) return null
  const txt = a < 0 ? 'now' : a < 60 ? `${a}s ago` : `${Math.floor(a / 60)}m ${a % 60}s ago`
  return <span className={`age${a > stale ? ' old' : ''}`} title="how long since the minute it read finished">read {asof} · {txt}</span>
}

/** Her PRACTICE since 2026-09-26, not a rule: nothing held or opened after 15:00, because the new CAS makes the close
 *  too volatile ("dont make any new rules"). A reminder from 14:45; it blocks nothing and feeds no word. */
export function Cutoff({ open = false }: { open?: boolean }) {
  const [, tick] = useState(0)
  useEffect(() => { const t = setInterval(() => tick(x => x + 1), 15000); return () => clearInterval(t) }, [])
  const d = new Date(), m = d.getHours() * 60 + d.getMinutes(), left = 15 * 60 - m
  if (m < 14 * 60 + 45 || m >= 15 * 60 + 30) return null
  return <span className="cutoff" title="your practice since 26 Sep (the new CAS), not a rule — nothing is blocked">
    {left > 0 ? `your 15:00 cutoff (CAS) — ${left} min` : open ? 'past your 15:00 cutoff (CAS) — this trade is still open' : 'past your 15:00 cutoff (CAS) — no new trades'}</span>
}

/** The count as five marks in fact order -- still a count, and it cannot be read as 20 % (REVIEW P1-1). */
export function Marks({ facts }: { facts: { state: string; name: string }[] }) {
  return <span className="marks" aria-label={facts.map(f => `${f.name} ${f.state}`).join(', ')}>
    {facts.map(f => <Mark key={f.name} st={f.state} />)}</span>
}

type Fold = { t: string; rule: number; why?: string; L?: number | null; px?: number | null; by?: number | null; level?: number | null; by_level?: number | null } | null | undefined

export function StopBlock({ p, n, idx, fold, riskScale = 1, noise }: { p?: PlanRow | null; n?: Now; idx?: string; fold?: Fold; riskScale?: number; noise?: number | null }) {
  const s = p?.stop
  if (fold?.rule === 3 && fold.L != null) return (              // after a FOLD the stop IS the line that broke (REVIEW P0-9)
    <div className="nb">
      <span className="label">Stop · the line that broke</span>
      <div className="nb-top"><span className="big"><N t="M">{inr(fold.L, 1)}</N></span>
        {fold.by != null && <span className="pts"><span className="num">{fold.by}</span><small>pts through</small><T t="M" /></span>}</div>
      <div className="risk">broke {fold.t}{fold.px != null && <> · {idx} closed <N t="M">{inr(fold.px, 1)}</N></>}</div>
      {fold.by_level != null && fold.level != null && <div className="sub"><N t="M">{`${fold.by_level} pts`}</N> past the break level {inr(fold.level, 1)}</div>}
      {s?.after_fold?.text && <div className="sub">{s.after_fold.text}</div>}
      {s?.L != null && s.L !== fold.L && <div className="sub">the line has since trailed to {inr(s.L, 1)} — a new trade would use it</div>}
    </div>
  )
  if (!s || s.L == null) return (
    <div className="nb"><span className="label">Stop · index level</span>
      <div><Abs text={n?.line.blind || s?.risk_why || 'could not check — the line'} /></div></div>
  )
  return (
    <div className="nb">
      <span className="label">Stop · index level</span>
      <div className="nb-top"><span className="big"><N t="M">{inr(s.L, 1)}</N></span>
        {s.room != null && <span className="pts"><span className="num">{Math.abs(s.room)}</span><small>{s.room < 0 ? 'pts past it' : 'pts'}</small><T t="M" /></span>}</div>
      {n?.line.broken_at ? <div className="risk">the line broke at <span className="num">{n.line.broken_at}</span></div>
        : s.room != null && s.room < 0 ? <div className="risk">the index is already past this line</div>
        : s.risk != null ? <div className="risk">≈ <N t="I">{rs(s.risk * riskScale)}</N> of premium between here and the line</div> : <Abs text={s.risk_why} />}
      {s.level_text && <div className="sub">{s.level_text.replace(/^line [\d,.]+ · /, '')}</div>}
      {noise != null && <div className="sub">one normal 1-min candle: <N t="M">{`${noise} pts`}</N>{s.room != null && s.room <= noise ? ' — your stop is inside it' : ''}</div>}
      {n?.line.px != null && <div className="sub">{idx} now <N t="M">{inr(n.line.px, 1, 2)}</N> · {n.line.src}</div>}
    </div>
  )
}

export function WallBlock({ p, fold }: { p?: PlanRow | null; fold?: Fold }) {
  const r = p?.rung
  return (
    <div className="nb">
      <span className="label">Next wall</span>
      {fold ? <div><Abs text="not shown — the plan ended at the FOLD" /></div>
        : !r ? <div><Abs text="not shown — a writer has no next wall: time is her target" /></div>
        : r.src === 'wall' && r.k != null ? <>
          <div className="nb-top"><span className="big"><span className="k">{r.side}</span><N t="M">{inr(r.k)}</N></span>
            {r.room != null && <span className="pts"><span className="num">{r.room}</span><small>pts</small><T t="M" /></span>}</div>
          <div className="ww"><Mark st={WALL[r.word || ''] || 'neither'} />{r.word}</div>
          <div className="sub">{r.favour}{r.state ? ` · ${r.state}${r.fold_t ? `, folded ${r.fold_t}` : ''}` : ''}</div>
        </>
        : r.src === 'session' && r.k != null ? <>
          <div className="nb-top"><span className="big"><N t="M">{inr(r.k, 1)}</N></span>
            {r.room != null && <span className="pts"><span className="num">{r.room}</span><small>pts</small><T t="M" /></span>}</div>
          <div className="sub">{r.label}</div>
        </>
        : <div><Abs text={r.label} /></div>}
    </div>
  )
}

/** Premium, with σ against its own session VWAP -- a registered footer item (§5; REVIEW P1-14). */
export function Sigma({ rd }: { rd?: Reading }) {
  const g = rd?.sigma
  if (!g) return null
  return g.z != null ? <span className="sub">premium <N t="M">{`${g.z > 0 ? '+' : ''}${g.z}σ`}</N> vs its own VWAP</span>
                     : <Abs text={g.why} />
}

/** What would turn this WATCH into FOLD, as a list (REVIEW copy 9); the server's items when it sends them. */
export function WatchList({ n }: { n: Now }) {
  if (n.verdict !== 'WATCH') return null
  const items = n.watch_items || (n.watch ? n.watch.replace(/^FOLD if (any one of: )?/, '').split(/ · |, or /) : [])
  if (!items.length) return null
  return <div className="needs"><span className="label">What would make it FOLD</span>
    <ul>{items.map(x => <li key={x}><Ico n="ArrowRight" /><span>{cap(x)}</span></li>)}</ul></div>
}

/** The four rows (plus the line) exactly as the window reads them. */
export function Rows({ n }: { n: Now }) {
  const L = n.line
  const rows: { nm: string; st: string; word?: string; tx: ReactNode }[] = [
    { nm: 'Line', st: L.blind ? 'blind' : L.broken_at ? 'against' : '', word: L.blind ? 'could not check' : L.broken_at ? `broken ${L.broken_at}` : 'not broken',
      tx: L.blind ? <Abs text={L.blind} /> : <>{L.print || <><N t="M">{inr(L.L ?? 0, 1)}</N> · <span className="num">{roomText(L.room ?? 0)}</span>{(L.room ?? 0) < 0 ? '' : ' of room'}</>} — {L.src}</> },
    { nm: 'Payers', st: n.payers.state, tx: <>{n.payers.fact}<T t={n.payers.tag} /></> },
    { nm: n.holders.label === 'YOUR SIDE' ? 'Your side' : 'Holders', st: n.holders.state,
      tx: <>{n.holders.fact}<T t={n.holders.tag} />{n.holders.fold && <div>{n.holders.fold}</div>}</> },
    { nm: 'Order flow', st: n.flow.state,
      tx: n.flow.state === 'blind' ? <><Abs text={n.flow.why} />{n.flow.fact && <div className="muted">seen: {n.flow.fact}<T t={n.flow.tag} /></div>}</>
        : <>{n.flow.fact}<T t={n.flow.tag} /></> },
    { nm: 'Trend', st: n.trend.state, tx: <>{n.trend.rows}<T t={n.trend.tag} /></> },
  ]
  return (
    <>
      {rows.map(r => (
        <div className="drow" key={r.nm}><Mark st={r.st} />
          <div><div className="rh"><span className="nm">{r.nm}</span><span className="st">{r.word || ROW_WORD[r.st] || r.st}</span></div>
            <div className="tx">{r.tx}</div></div></div>
      ))}
      <p className="sm">{n.count} · {n.clock.text}</p>
    </>
  )
}

export function PlanList({ p, qty }: { p: NonNullable<Reading['plan']>; qty?: number }) {
  const rg = p.rung
  return (
    <>
      <h4 className="label">The plan</h4>
      <dl className="kv">
        <dt>Stop</dt><dd>{p.stop.L != null ? <><N t="M">{inr(p.stop.L, 1)}</N> · {roomText(p.stop.room ?? 0)}{p.stop.risk != null && (p.stop.room ?? 0) >= 0 && <> · ≈ <N t="I">{rs(p.stop.risk)}</N> at risk{qty ? `, qty ${qty}` : ''}</>}</> : <Abs text={p.stop.risk_why} />}</dd>
        <dt>Rung</dt><dd>{!rg ? 'none — a writer' : rg.src === 'wall' ? <>{rg.side} <N t="M">{inr(rg.k ?? 0)}</N> · {rg.room} pts · <b>{rg.word?.toLowerCase()}</b> — {rg.favour}</> : rg.label}</dd>
        {p.room && <><dt>Room</dt><dd>{p.room.text}{p.room.note ? ` — ${p.room.note}` : ''}</dd></>}
        {p.touch && <><dt>Touched</dt><dd>{p.t}: {p.touch.session ? p.touch.text : `${p.touch.word} — ${p.touch.favour}`}</dd></>}
        <dt>Exits</dt><dd>{p.exits.line}<br />{p.exits.window} — both stand; you choose</dd>
        {p.entry?.room && <><dt>At entry</dt><dd>{p.entry.room.text} · {p.entry.exits.window}</dd></>}
      </dl>
      <div className="abs-list">{p.not_shown.map((t, i) => <Abs key={i} text={t} />)}</div>
    </>
  )
}

export function SideList({ s }: { s: SideRead }) {
  return (
    <>
      <h4 className="label">The side read</h4>
      <div className="side-w"><span className="word">{s.side}</span><span className="sm">since <span className="num">{s.since}</span><T t="I" /></span></div>
      <p className="sm">{s.text}</p>
      {s.agrees && <p className="sm">your trade vs the read: <b>{s.agrees}</b></p>}
      {s.facts.map(f => (
        <div className="drow" key={f.k}><Mark st={f.state} />
          <div><div className="rh"><span className="nm">{f.k}</span><span className="st">{ROW_WORD[f.state] || f.state}</span></div>
            <div className="tx">{f.state === 'blind' ? <Abs text={f.fact} /> : <>{f.fact}<T t={f.tag} /></>}</div></div></div>
      ))}
      {s.oi_half?.[1] && <p className="sm">OI, printed not counted: <b>{s.oi_half[0]}</b> — {s.oi_half[1]}</p>}
      {s.expiry?.text && <div className="abs-list"><Abs text={s.expiry.text} /></div>}
    </>
  )
}

export function AbsentList({ a, extra = [] }: { a?: Reading['absent']; extra?: (string | null | undefined)[] }) {
  const all = [a?.checked_none, ...(a?.could_not_check || []), ...(a?.not_shown || []), ...extra].filter(Boolean) as string[]
  return <><h4 className="label">What is absent, and why</h4><div className="abs-list">{all.map((t, i) => <Abs key={i} text={t} />)}</div></>
}

export type Run = { from: string; to: string; verdict: string; tag: string | null; sentence: string }
export const span = (r: Run) => r.from === r.to ? r.from : `${r.from}–${r.to}`

/** A long straddle has no direction; each leg is read as its own (REVIEW P1-22). */
export const twoLegs = (open: { idx: string; side: string; role: string }[]) =>
  open.some(a => open.some(b => a.idx === b.idx && a.role === b.role && a.side !== b.side))

/** One broken render must never take the app, or the other view, down with it (REVIEW P1-20). */
export class Guard extends Component<{ children: ReactNode; name: string }, { err: string | null }> {
  state = { err: null as string | null }
  static getDerivedStateFromError(e: Error) { return { err: e.message } }
  render() {
    return this.state.err
      ? <div className="hv"><span className="err">The {this.props.name} hit a screen error ({this.state.err}). Press F5; the server and your records are untouched.</span></div>
      : this.props.children
  }
}
