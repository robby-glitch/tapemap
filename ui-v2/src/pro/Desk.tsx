// The DESK faces (6-blueprint.md §4.7, §4.8, §5, §6, §7.2): in a trade, IF YOU WERE IN, flat. Presentation only: every
// word and number here is the engine's; the screen computes nothing. Styles: ./pro.css.
import { cc, type Fight, type Flat, type FoldRead, type Ifin, type Pick, type Rows, type Trade, type View, type Word } from './api'

export const f2 = (x: number | null | undefined) => x == null ? '—' : x.toFixed(2)
export const f1 = (x: number | null | undefined) => x == null ? '—' : x.toFixed(1)
export const pct = (x: number | null | undefined) => x == null ? '' : `${x > 0 ? '+' : ''}${x}%`
export const L = (oi: number | null | undefined) => oi == null ? '—' : `${(oi / 1e5).toFixed(1)}L`
export const tradeLabel = (t: Trade) => `${t.role === 'long' ? 'long' : 'short'} ${t.k} ${t.side}`

/** a sentence's trailing [M] / [I] becomes the row's tag: one tag per row, not per number */
function splitTag(s?: string | null): [string | null, 'M' | 'I' | null] {
  if (!s) return [null, null]
  const m = s.match(/\s*\[(M|I)\]\s*$/)
  return m ? [s.slice(0, m.index), m[1] as 'M' | 'I'] : [s, null]
}
/** the three absences never collapse: checked-and-nothing (ink, a QUIET chip) · could not check, with its reason (grey italic) ·
 *  not showing you (grey). A missing read is 'none', never a zero. */
export function absence(text?: string | null, chip?: string | null): 'read' | 'cant' | 'notshown' | 'none' {
  if (!text) return 'none'
  const t = text.toLowerCase()
  if (chip === "CAN'T CHECK" || t.startsWith('could not check')) return 'cant'
  if (t.startsWith('not showing you') || t.startsWith('not shown')) return 'notshown'
  return 'read'
}
export const Abs = ({ text }: { text: string }) => <span className={`abs ${absence(text)}`}>{text}</span>
/** inline [M] / [I] inside an engine sentence (THE DAY) rendered as small tags */
export const Sentence = ({ s }: { s: string }) =>
  <>{s.split(/(\[[MI]\])/).map((p, i) => /^\[[MI]\]$/.test(p) ? <span key={i} className="tag">{p[1]}</span> : p)}</>

const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"] as const
const CLS: Record<string, string> = { HOLD: 'hold', 'PAST GIVE-UP': 'past', FOLD: 'fold', "CAN'T CHECK": 'cant' }
export function Headline({ h }: { h: string }) {
  const word = WORDS.find(w => h.toUpperCase().startsWith(w)) ?? h
  const rest = h.slice(word.length).replace(/^\s*·\s*/, '')
  return <h1 className={`headline ${CLS[word] ?? 'hold'}`}><span className="word">{word}</span>{rest && <span className="rest">{rest}</span>}</h1>
}
export const Cant = ({ why }: { why: string }) => why === 'checking…'
  ? <p className="clause muted">checking…</p>
  : <><h1 className="headline cant"><span className="word">CAN'T CHECK</span></h1><p className="clause"><Abs text={why} /></p></>

const ORDER: [keyof Rows, string][] = [['zone', 'ZONE'], ['flow', 'FLOW'], ['oi', 'OI'], ['vpin', 'VPIN']]
export function FourRows({ rows }: { rows?: Rows | null }) {
  return <div className="rows" role="table" aria-label="The four rows">
    {ORDER.map(([k, label]) => {
      const r = rows?.[k], [text, tag] = splitTag(r?.sentence), kind = absence(text, r?.chip)
      return <div className="row" role="row" key={k} data-chip={r?.chip ?? 'NONE'}>
        <span className="lbl">{label}</span>
        <span className="chip"><i className="mark" />{r?.chip ?? 'no read'}</span>
        <span className={`txt ${kind}`}>{text ?? 'not read yet'}{r?.machine && <span className="machine"> · {r.machine}</span>}</span>
        <span className="tag" title={tag === 'M' ? 'measured' : 'inferred'}>{tag ?? 'I'}</span>
      </div>
    })}
  </div>
}

/** her give-up and the wall ahead, in numbers */
export function Levels({ v }: { v: View }) {
  const G = v.G, A = v.A
  return <div className="levels">
    <div><span className="k">give-up</span>
      {G ? <><b className="num" title={G.why}>{G.px}</b><span className="muted">set {G.set_t}{v.mode ? ` · ${v.mode}` : ''}</span></> : <Abs text="could not check — no give-up yet" />}
      <span className="tag">M</span></div>
    <div><span className="k">wall ahead</span>
      {A ? <><b className="num">{A.k} {A.side}</b><span className="muted">{A.pts != null ? `${A.pts} pts · ` : ''}{L(A.oi)}{A.peak_t ? `, peak ${L(A.peak)} ${A.peak_t}` : ''}</span></> : <Abs text="could not check — no wall ahead read" />}
      <span className="tag">M</span></div>
  </div>
}

export function Premium({ v, ty }: { v: View; ty: string }) {
  const p = v.prem, up = (p.pct ?? 0) > 0, dn = (p.pct ?? 0) < 0
  const why = (w?: string | null) => w && !/^\[[MI]\]$/.test(w) ? w : 'could not check'
  return <div className="card prem">
    <div className="k">PREMIUM{v.frozen && v.exit_t ? ` · AT YOUR EXIT ${v.exit_t.slice(0, 5)}` : ''}</div>
    <div className="big"><span className="num now">{f2(p.now)}</span><span className={`pct ${up ? 'up' : dn ? 'dn' : ''}`}>{pct(p.pct)}</span><span className="ty">{ty}</span></div>
    <div className="grp">
      <div className="kv"><span>peak</span><span className="num">{f2(p.peak)}{p.peak_pct != null ? ` ${pct(p.peak_pct)}` : ''}{p.peak_t ? ` · ${p.peak_t}` : ''}</span></div>
      <div className="kv"><span>given back</span><span className="num">{f2(p.given_back)}</span></div>
      <span className="tag">M</span>
    </div>
    <div className="grp">
      <div className="kv"><span>at your give-up</span><span className="num">{p.at_G != null ? f2(p.at_G) : <Abs text={why(p.at_G_why)} />}</span></div>
      <div className="kv"><span>at the wall ahead</span><span className="num">{p.at_A != null ? f2(p.at_A) : <Abs text={why(p.at_A_why)} />}</span></div>
      <span className="tag">I</span>
    </div>
    {p.expiry_day && <div className="grp split"><span className="num">{ty} {f2(p.now)} = {f1(p.intrinsic)} in the money + {f1(p.time)} time</span><span className="tag">I</span></div>}
  </div>
}

function Face({ v, why }: { v: View; why: string | null }) {
  return <>
    {why && <p className="cant-banner">{why} · showing the read from {v.ts}</p>}
    <div className={why ? 'dim' : ''}>
      <Headline h={v.headline ?? ''} />
      <p className="clause">{v.clause}</p>
      <p className="line2">{v.line2}</p>
      <FourRows rows={v.rows} />
      <Levels v={v} />
    </div>
  </>
}

export function InTrade({ t, r, why }: { t: Trade; r?: FoldRead; why: string | null }) {
  const v = r?.ok ? r.view : undefined
  const line = <p className="tradeline"><b>{tradeLabel(t)}</b> · in at {f2(t.p0)} · {t.t0.slice(0, 5)}
    {v?.frozen && v.exit_t && <> · <b>out {v.exit_t.slice(0, 5)}</b> · frozen at your exit</>}</p>
  if (!v || v.headline == null) {
    const reason = why ?? (!r ? 'checking…' : r.ok ? cc(v?.why, 'no view yet') : cc(r.why, 'the engine gave no reason'))
    return <>{line}<Cant why={reason} /></>
  }
  return <>{line}<Face v={v} why={why} /></>
}

export function IfinFace({ r, pick, why }: { r: Ifin | null; pick: Pick; why: string | null }) {
  const head = `IF YOU WERE IN · ${pick.side === 'BUY' ? 'long' : 'short'} ${pick.k} ${pick.ty}`
  const v = r?.ok ? r.view : undefined
  if (!v || v.headline == null) {
    const reason = why ?? (!r ? 'checking…' : cc(r.why ?? v?.why, 'no read'))
    return <><p className="tradeline"><b>{head}</b></p><Cant why={reason} /></>
  }
  return <><p className="tradeline"><b>{head}</b> · at {f2(v.prem.now)} now</p><Face v={v} why={why} /></>
}

function FightBox({ label, f }: { label: 'above' | 'below'; f: Fight | null }) {
  return <div className={`fight ${label}`}>
    <div className="k">{label}{f?.px != null && <b className="num">{f.px}</b>}</div>
    {!f ? <p><Abs text={`could not check — no level ${label} yet`} /></p> : <>
      <p className={absence(f.what)}>{f.what}</p>
      <p className="confirm">{f.confirm ? <><b>confirms:</b> {f.confirm}</> : <Abs text="could not check — nothing to confirm yet" />}</p></>}
  </div>
}

export function FlatFace({ f, why }: { f: Flat | null; why: string | null }) {
  if (!f || !f.ok) return <Cant why={why ?? (f?.why ? cc(f.why) : 'checking…')} />
  const nf = f.next_fight
  return <>
    <p className="tradeline"><b>FLAT</b>{f.at && <> · at <b className="num">{f.at.px}</b> ({f.at.what})</>}</p>
    {why && <p className="cant-banner">{why} · showing the read from {f.asof}</p>}
    <div className={why ? 'dim' : ''}>
      <h1 className="headline flat"><span className="word">NEXT FIGHT</span>
        {nf ? <span className="rest"><b className="num">{nf.above?.px ?? '—'}</b> above <span className="sep">·</span> <b className="num">{nf.below?.px ?? '—'}</b> below</span>
            : <span className="rest"><Abs text={f.why ?? 'could not check — no levels yet'} /></span>}</h1>
      {nf && <div className="fights"><FightBox label="above" f={nf.above} /><FightBox label="below" f={nf.below} /></div>}
      {f.gave_up && <div className="gaveup"><b>{f.gave_up.text}</b><span><Sentence s={f.gave_up.oi} /></span><span className="muted">{f.gave_up.unproven}</span></div>}
      {f.reentry && <div className="reentry"><span className="k">RE-ENTRY · unproven</span><span>{f.reentry.text}</span></div>}
      <FourRows rows={f.rows} />
      <div className="day"><span className="k">THE DAY</span><p>{f.day ? <Sentence s={f.day} /> : <Abs text="could not check — no day sentence yet" />}</p></div>
    </div>
  </>
}

export function Words({ w }: { w?: Word[] | null }) {
  return <div className="card words"><div className="k">WORDS{w?.length ? ` · ${w.length}` : ''}</div>
    {!w?.length ? <Abs text="checked — no words logged yet" />
      : <ul>{w.slice(-8).reverse().map((x, i) => <li key={i}><span className="t num">{x.t.slice(0, 5)}</span><span><b>{x.headline}</b>{x.clause ? ` · ${x.clause}` : ''}</span></li>)}</ul>}
  </div>
}
