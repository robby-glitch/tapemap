// MARKET NOW — the market's conditions at the top of the Validate tab, read off the Board's own reads
// (/api/board) and the VPIN gauge (/api/vpin). Display only: "conditions, not a vote". Nothing here
// feeds the GO / WAIT / NO word or the HOLD / FOLD window (their registrations name their inputs);
// VPIN is a SHADOW gauge and is labelled so. Her ask, 2026-09-25: "seller is strong or buyers ... who
// build the wall ... call heavy or put heavy how heavy one sided or balance expecting pin/chop or trending".
import { useEffect, useState } from 'react'
import type { IndexKey } from '../data'
import { Abs, Age, N, T, inr } from './parts'
import { j, why } from './store'

type Fam = { k: string; v: number | null; fact: string; tag: string; doubt?: string }
type Front = { k: number; side: 'CE' | 'PE'; state: string; built?: string; words?: string; nearer?: boolean; rank?: number; tag: string }
type Leg = { strike: number; c: number; vwap: number; z: number | null; band?: string; tag: string
             pivots?: { above?: { name: string; px: number; dist: number } | null; below?: { name: string; px: number; dist: number } | null } }
type Board = {
  ok: boolean; why?: string; asof?: string; headline?: { text: string; tag: string }
  agreement?: { head: { dir: number; n: number; of: number; text: string }; fam: Fam[] }
  trend?: { regime: { word: string; price: [string, string]; oi: [string, string] }; strong?: { word: string }; tag: string }
  pcr?: { v: number | null; text: string; tag: string }
  fronts?: Front[] | null; fronts_why?: string | null
  mirror?: { ok: boolean; why?: string; legs?: Partial<Record<'CE' | 'PE', Leg>> } | null
}
type Gauge = { vpin: number; pct: number | null; buckets: number }
type Vpin = { ok: boolean; why?: string; inst?: string; state?: Record<string, Gauge> }
type Failed = { ok: false; why: string }

const ARROW = (v: number | null) => v == null ? '?' : v > 0 ? '▲' : v < 0 ? '▼' : '–'
const POLL = 30000

function usePoll<X>(url: string | null): X | Failed | null {
  const [d, setD] = useState<X | Failed | null>(null)
  useEffect(() => {
    if (!url) { setD(null); return }
    let live = true
    const go = async () => { try { const r = await j<X>(url); if (live) setD(r) } catch (e) { if (live) setD({ ok: false, why: why(e) }) } }
    go()
    const t = setInterval(go, POLL)
    return () => { live = false; clearInterval(t) }
  }, [url])
  return d
}

/** `busy`: an answer or a trade is on screen -- the strip folds to one line so I'M IN stays above the fold;
 *  her click overrides until the screen changes state again. */
export default function MarketNow({ index, busy = false }: { index: IndexKey; busy?: boolean }) {
  const [manual, setManual] = useState<boolean | null>(null)
  useEffect(() => setManual(null), [busy])
  const open = manual ?? !busy
  const setOpen = (v: boolean) => setManual(v)
  const bd = usePoll<Board>(`/api/board?idx=${index}`) as Board | null
  const vp = usePoll<Vpin>(index === 'NIFTY' ? '/api/vpin' : null) as Vpin | null
  if (!bd) return <div className="mkt"><span className="label">Market now</span> <span className="muted">reading…</span></div>
  if (!bd.ok) return <div className="mkt"><span className="label">Market now</span> <Abs text={bd.why} /></div>

  const rg = bd.trend?.regime, ag = bd.agreement
  const wall = (side: 'CE' | 'PE') => (bd.fronts || []).filter(f => f.side === side).sort((a, b) => (a.rank ?? 9) - (b.rank ?? 9))[0]
  const walls = [wall('CE'), wall('PE')].filter(Boolean) as Front[]
  const pcr = bd.pcr?.v                       // the number [M] only: no put-heavy / call-heavy line of our own
  const slow = vp && vp.ok ? vp.state?.['NIFTY-FUT'] : undefined, fast = vp && vp.ok ? vp.state?.['NIFTY-FUT:fast'] : undefined
  const legs = (['CE', 'PE'] as const).map(s => [s, bd.mirror?.legs?.[s]] as const).filter(([, l]) => l)
  // VPIN, the shadow gauge: the same line in the open grid and under the folded header, so a trade never hides it
  const vpin = index !== 'NIFTY' ? <Abs text="not shown — VPIN runs on NIFTY futures only" />
    : !vp ? <span className="muted">reading…</span>
    : !vp.ok ? <Abs text={vp.why} />
    : slow || fast ? <>{slow && <span className="ms"><b>slow {slow.vpin.toFixed(2)}</b> · rank {slow.pct != null ? slow.pct.toFixed(2) : '—'} of its history<T t="I" /></span>}
        {fast && <span className="ms"><b>fast {fast.vpin.toFixed(2)}</b> · rank {fast.pct != null ? fast.pct.toFixed(2) : '—'}<T t="I" /></span>}</>
    : <Abs text="checked, none — no VPIN bucket yet today" />

  return (
    <div className="mkt" aria-label="Market now — conditions, not a vote">
      <button type="button" className="mkt-h" onClick={() => setOpen(!open)} aria-expanded={open} title={open ? 'fold to one line' : 'open'}>
        <span className="label">{open ? '▾' : '▸'} Market now · {index}</span><Age asof={bd.asof} stale={180} />
        {!open && <span className="ms">{rg ? (rg.word === 'AGREED' ? `${rg.price[0]} agreed` : 'regime not agreed') : ''}{ag ? ` · ${ag.head.dir > 0 ? 'buyers' : ag.head.dir < 0 ? 'sellers' : 'no side'} ${ag.head.n}/${ag.head.of}` : ''}{pcr != null ? ` · PCR ${pcr}` : ''}</span>}
        <span className="fine">conditions, not a vote — GO / WAIT / NO reads only its registered facts</span></button>
      {!open && <div className="mkt-vpin"><span className="label">VPIN</span>{vpin}<span className="fine">shadow gauge — not counted in any verdict</span></div>}
      {open && <>
      <div className="mkt-grid">
        <div className="mc"><span className="label">Trend or chop</span>
          {rg ? <><b className="mv">{rg.word === 'AGREED' ? `${rg.price[0]} · agreed` : 'NOT AGREED'}</b>
            <span className="ms">price {rg.price[0]} · OI {rg.oi[0]}{bd.trend?.strong ? ` · strong: ${bd.trend.strong.word}` : ''}<T t={bd.trend?.tag} /></span></>
            : <Abs text="could not check — no regime read" />}</div>
        <div className="mc"><span className="label">Who is pressing</span>
          {ag ? <><b className="mv">{ag.head.dir > 0 ? 'BUYERS' : ag.head.dir < 0 ? 'SELLERS' : 'NO SIDE'} · {ag.head.n} of {ag.head.of} agree</b>
            <span className="ms">{ag.fam.map(f => <span key={f.k} title={`${f.fact}${f.doubt ? ` — ${f.doubt}` : ''}`} className="fam">{f.k} {ARROW(f.v)}</span>)}</span></>
            : <Abs text="could not check — no agreement read" />}</div>
        <div className="mc"><span className="label">OI · PCR</span>
          {pcr != null ? <><b className="mv">PCR <N t={bd.pcr?.tag}>{pcr}</N></b>
            <span className="ms" title={bd.pcr?.text}>ΣPE / ΣCE open interest · drifts, no timing</span></>
            : <Abs text={bd.pcr?.text || 'could not check — no PCR'} />}</div>
        <div className="mc"><span className="label">The walls · who built them</span>
          {walls.length ? walls.map(f => <span key={f.side} className="ms"><b>{f.side} {inr(f.k)}</b> · {f.built === 'today' ? 'built today' : f.built || '—'} · {f.words || f.state.toLowerCase()}<T t={f.tag} /></span>)
            : <Abs text={bd.fronts_why || 'checked, none — no sized front inside the nine'} />}</div>
        <div className="mc"><span className="label">Mirror · premium vs its VWAP</span>
          {legs.length ? legs.map(([s, l]) => <span key={s} className="ms"><b>{s} {inr(l!.strike)}</b> <N t={l!.tag}>{inr(l!.c, 2)}</N> · {l!.z != null ? `${l!.z > 0 ? '+' : ''}${l!.z}σ` : '—'}{l!.band ? ` (${l!.band})` : ''}
              {l!.pivots?.above ? ` · ${l!.pivots.above.name} ${inr(l!.pivots.above.dist, 1)} above` : ''}{l!.pivots?.below ? ` · ${l!.pivots.below.name} ${inr(l!.pivots.below.dist, 1)} below` : ''}</span>)
            : <Abs text={bd.mirror?.why || 'could not check — no mirror read'} />}</div>
        <div className="mc"><span className="label">VPIN · order-flow toxicity</span>
          {vpin}<span className="ms muted">shadow gauge — not counted in any verdict</span></div>
      </div>
      {bd.headline?.text && <div className="mkt-now" title={bd.headline.text}><span className="label">Now</span> {bd.headline.text}<T t={bd.headline.tag} /></div>}
      </>}
    </div>
  )
}
