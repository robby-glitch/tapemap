// MARK MY TRADE (6-blueprint.md §7.3; validate-tab-spec §2.2-§2.3, her "go" 2026-10-05): CE/PE → BUY/SELL → strike (◂ ▸,
// at the money first) → the entry premium prefilled from the live chain (she types her fill) → THE THESIS LOCK (inval =
// the engine's give-up, T1 = the wall ahead, T2 blank for the engine's next level; each editable, futures points; one
// optional line why) → LOTS BY ROLE (CORE 1, BANKER 0-1, ADD 0-3; CORE only is the default) → MARK. Posts the existing door,
// /api/hold/trades {op: mark, ..., thesis, roles}. A record of what she did on her broker; nothing reaches a broker.
import { useEffect, useState } from 'react'
import { cc, hms, tradeOp, useStore, type ChainLite, type Idx, type Pick, type Side, type Trade, type Ty, type View } from './api'
import { Abs, f2, tradeLabel } from './Desk'

type Th = { inval: string; t1: string; t2: string; why: string }
const num = (x: string) => { const v = parseFloat(x); return isFinite(v) && v > 0 ? v : null }

const ls = (k: string, v?: string) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v) } catch { /* the slip still works */ } return null }

export function Slip({ idx, chain, open, cur, onSelect, pick, setPick, leg = null, lot = null }: { idx: Idx; chain: ChainLite | null; open: Trade[]; cur: Trade | null
                                                                       onSelect: (id: string) => void; pick: Pick | null; setPick: (p: Pick) => void
                                                                       leg?: View | null; lot?: number | null }) {
  const ks = (chain?.strikes ?? []).map(s => s.k).sort((a, b) => a - b)
  const atm = chain?.atm ?? null
  const gaps = ks.slice(1).map((k, i) => k - ks[i]).filter(d => d > 0)
  const step = gaps.length ? Math.min(...gaps) : 50
  const loaded = ks.length > 0
  const [p0, setP0] = useState(''), [qty, setQty] = useState(''), [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null), [arm, setArm] = useState<string | null>(null)
  // the thesis: the engine's levels for the picked leg until she types her own; the field she typed is hers
  const eng: Th = { inval: leg?.G?.px != null ? String(leg.G.px) : '', t1: leg?.A?.px != null ? String(leg.A.px) : '', t2: '', why: '' }
  const [th, setTh] = useState<Th>({ inval: '', t1: '', t2: '', why: '' }), [mine, setMine] = useState<string[]>([])
  const val = (k: keyof Th) => mine.includes(k) ? th[k] : eng[k]
  const type = (k: keyof Th, v: string) => { setTh(x => ({ ...x, [k]: v })); setMine(m => m.includes(k) ? m : [...m, k]) }
  useEffect(() => { setMine(m => m.filter(k => k === 'why')) }, [pick?.k, pick?.ty, pick?.side])     // a new leg: the engine's levels again
  const [banker, setBanker] = useState(0), [adds, setAdds] = useState(0)
  const lots = 1 + banker + adds
  const va = useStore().validate
  const warn = [va?.flip && `FLIP — ${va.flip.why} · ${va.flip.left_s} s`,
                va?.cooldown && `COOLDOWN — ${va.cooldown.why} · ${Math.ceil(va.cooldown.left_s / 60)} min left`].filter(Boolean) as string[]
  // the first chain: her strike starts at the money; her last CE/PE and BUY/SELL survive a reload
  useEffect(() => { if (!pick && atm) setPick({ k: atm, ty: ls('pro.ty') === 'CE' ? 'CE' : 'PE', side: ls('pro.side') === 'SELL' ? 'SELL' : 'BUY' }) }, [pick, atm, setPick])
  const row = pick ? chain?.strikes.find(s => s.k === pick.k) : undefined
  const ltp = row && pick ? (pick.ty === 'CE' ? row.ce : row.pe) : null
  // frozen when the row opens: prefilled once per strike / type, never overwritten while she types
  useEffect(() => { setP0(ltp != null ? String(ltp) : '') }, [pick?.k, pick?.ty, loaded])  // eslint-disable-line react-hooks/exhaustive-deps
  const set = (p: Partial<Pick>) => { if (!pick) return; const n = { ...pick, ...p }; ls('pro.ty', n.ty); ls('pro.side', n.side); setPick(n) }
  const stepK = (d: number) => set({ k: (pick?.k ?? 0) + d * step })
  // keys as on a ticket: C/P · B/S · ↑↓ strike. Never Enter: a mark is a click.
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || (e.target as HTMLElement)?.closest?.('input,select,textarea') || !pick || cur) return
      const k = e.key.toUpperCase()
      if (k === 'C') set({ ty: 'CE' }); else if (k === 'P') set({ ty: 'PE' }); else if (k === 'B') set({ side: 'BUY' }); else if (k === 'S') set({ side: 'SELL' })
      else if (e.key === 'ArrowUp') { stepK(1); e.preventDefault() } else if (e.key === 'ArrowDown') { stepK(-1); e.preventDefault() }
    }
    window.addEventListener('keydown', on)
    return () => window.removeEventListener('keydown', on)
  })
  const money = pick && atm ? (pick.k === atm ? 'ATM' : `${(pick.ty === 'CE') === (pick.k < atm) ? 'ITM' : 'OTM'} ${Math.round(Math.abs(pick.k - atm) / step)}`) : null

  const mark = async () => {
    if (!pick || busy || !p0) return
    setBusy(true); setMsg(null)
    const thesis = { why: th.why.trim().slice(0, 120) || null, t1: num(val('t1')), t2: num(val('t2')), inval: num(val('inval')),
                     src: Object.fromEntries((['t1', 't2', 'inval'] as const).filter(k => num(val(k)) != null).map(k => [k, mine.includes(k) ? 'her' : 'engine'])) }
    const roles = [{ role: 'CORE', lots: 1 }, ...(banker ? [{ role: 'BANKER', lots: 1 }] : []), ...Array.from({ length: adds }, () => ({ role: 'ADD', lots: 1 }))]
    const q = qty || (lot ? String(lots * lot) : '')
    const r = await tradeOp({ op: 'mark', idx, k: pick.k, side: pick.ty, role: pick.side === 'BUY' ? 'long' : 'short', t0: hms(), p0, ...(q ? { qty: q } : {}), thesis, roles })
    setBusy(false)
    if (!r.ok) setMsg(r.why || 'the mark did not land')
  }
  // I'M OUT is two presses 5 s apart: the record is hers, a slip of the hand is not
  const out = async (t: Trade) => {
    if (arm !== t.id) { setArm(t.id); window.setTimeout(() => setArm(a => a === t.id ? null : a), 5000); return }
    setArm(null); setBusy(true); setMsg(null)
    const r = await tradeOp({ op: 'exit', id: t.id, exit_t: hms() })
    setBusy(false)
    if (!r.ok) setMsg(r.why || 'the exit did not land')
  }

  if (open.length) return <div className="card slip">
    <div className="k">YOUR TRADE{open.length > 1 ? `S · ${open.length}` : ''}</div>
    {open.map(t => <div key={t.id} className={`held ${cur?.id === t.id ? 'on' : ''}`} onClick={() => onSelect(t.id)}>
      <div><b>{t.idx} {tradeLabel(t)}</b>{open.length > 1 && <span className="muted"> · {t.t0.slice(0, 5)}</span>}</div>
      <button className={`btn out ${arm === t.id ? 'arm' : ''}`} disabled={busy} onClick={e => { e.stopPropagation(); out(t) }}>{arm === t.id ? 'CONFIRM OUT' : "I'M OUT"}</button>
    </div>)}
    {msg && <p className="msg">{msg}</p>}
  </div>

  return <div className="card slip">
    <div className="k">MARK MY TRADE · {idx}</div>
    <div className="line"><Seg opts={['CE', 'PE']} v={pick?.ty} on={x => set({ ty: x as Ty })} /><Seg opts={['BUY', 'SELL']} v={pick?.side} on={x => set({ side: x as Side })} /></div>
    <div className="strike">
      <button aria-label="strike down" onClick={() => stepK(-1)} disabled={!pick}>◂</button>
      <span className="num">{pick?.k ?? '—'}</span>
      <button aria-label="strike up" onClick={() => stepK(1)} disabled={!pick}>▸</button>
      <span className="money">{money ?? <Abs text={cc(chain?.why, 'the chain has not loaded')} />}</span>
      {pick && atm && pick.k !== atm && <button className="lnk" onClick={() => set({ k: atm })}>ATM {atm}</button>}
    </div>
    <div className="fields">
      <label className="field"><span>entry premium</span><input inputMode="decimal" value={p0} onChange={e => setP0(e.target.value)} placeholder="your fill" /></label>
      <label className="field"><span>qty</span><input inputMode="numeric" value={qty} onChange={e => setQty(e.target.value)} placeholder={lot ? String(lots * lot) : 'optional'} /></label>
    </div>
    <p className="fine">{ltp != null ? <>chain {f2(ltp)} at {chain?.ts ?? '—'} · type your fill</>
      : loaded ? <Abs text="could not check — no premium for this strike in the chain" /> : chain?.why ? 'type your fill' : <Abs text="could not check — the chain has not loaded" />}</p>
    <div className="thesis">
      <div className="k">THESIS LOCK · futures pts · locked at MARK</div>
      {(['inval', 't1', 't2'] as const).map(k => <label key={k} className="lvl">
        <span className="n">{k === 'inval' ? 'INVAL' : k.toUpperCase()}</span>
        <input inputMode="decimal" value={val(k)} onChange={e => type(k, e.target.value)} placeholder={k === 't2' ? 'engine: next level beyond T1' : 'not read yet'} />
        <span className={`src ${mine.includes(k) ? 'her' : ''}`}>{mine.includes(k) ? 'tumhara' : num(eng[k]) != null ? (k === 'inval' ? 'engine · give-up' : 'engine · wall ahead')
          : k === 't2' ? 'engine bharega' : <Abs text="could not check — no engine level yet" />}</span></label>)}
      <input className="why" maxLength={120} value={th.why} onChange={e => type('why', e.target.value)} placeholder="why — one line, optional (≤ 120)" />
    </div>
    <div className="lots">
      <div className="k">LOTS BY ROLE · {lots} lot{lots > 1 ? 's' : ''}{lot ? ` = ${lots * lot} qty` : ''}</div>
      <span className="lrole on" title="the last lot to leave: at T2, on RED or at the invalidation">CORE 1</span>
      <button className={`lrole ${banker ? 'on' : ''}`} onClick={() => setBanker(b => b ? 0 : 1)} title="books at T1, pays for the trade">BANKER {banker}</button>
      <span className="lrole add" title="up to 3; each cut first">ADD
        <button aria-label="one ADD fewer" disabled={!adds} onClick={() => setAdds(a => Math.max(0, a - 1))}>−</button>
        <b className="num">{adds}</b>
        <button aria-label="one ADD more" disabled={adds >= 3} onClick={() => setAdds(a => Math.min(3, a + 1))}>+</button></span>
    </div>
    {warn.map(w => <p key={w} className="warn">{w} <span className="muted">· a warning, tagged on the record — never a block</span></p>)}
    <button className="btn" disabled={!pick || !p0 || busy} onClick={mark}>MARK{pick ? ` · ${pick.side} ${pick.k} ${pick.ty}` : ''}</button>
    {msg && <p className="msg">{msg}</p>}
  </div>
}

function Seg({ opts, v, on }: { opts: string[]; v?: string; on: (x: string) => void }) {
  return <div className="seg" role="group">{opts.map(o => <button key={o} className={v === o ? 'on' : ''} onClick={() => on(o)}>{o}</button>)}</div>
}
