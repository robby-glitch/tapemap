// MARK MY TRADE (6-blueprint.md §7.3): CE/PE → BUY/SELL → MARK, the strike prefilled at the money with ◂ ▸ steps, the entry
// premium prefilled from the live chain and frozen when the row opens (she types her fill). Posts the existing door,
// /api/hold/trades {op: mark | exit}: one record with the old Validate tab. Nothing reaches a broker.
import { useEffect, useState } from 'react'
import { cc, hms, tradeOp, type ChainLite, type Idx, type Pick, type Side, type Trade, type Ty } from './api'
import { Abs, f2, tradeLabel } from './Desk'

const ls = (k: string, v?: string) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v) } catch { /* the slip still works */ } return null }

export function Slip({ idx, chain, open, cur, onSelect, pick, setPick }: { idx: Idx; chain: ChainLite | null; open: Trade[]; cur: Trade | null
                                                                       onSelect: (id: string) => void; pick: Pick | null; setPick: (p: Pick) => void }) {
  const ks = (chain?.strikes ?? []).map(s => s.k).sort((a, b) => a - b)
  const atm = chain?.atm ?? null
  const gaps = ks.slice(1).map((k, i) => k - ks[i]).filter(d => d > 0)
  const step = gaps.length ? Math.min(...gaps) : 50
  const loaded = ks.length > 0
  const [p0, setP0] = useState(''), [qty, setQty] = useState(''), [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null), [arm, setArm] = useState<string | null>(null)
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
    const r = await tradeOp({ op: 'mark', idx, k: pick.k, side: pick.ty, role: pick.side === 'BUY' ? 'long' : 'short', t0: hms(), p0, ...(qty ? { qty } : {}) })
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
      <label className="field"><span>qty</span><input inputMode="numeric" value={qty} onChange={e => setQty(e.target.value)} placeholder="optional" /></label>
    </div>
    <p className="fine">{ltp != null ? <>chain {f2(ltp)} at {chain?.ts ?? '—'} · type your fill</>
      : loaded ? <Abs text="could not check — no premium for this strike in the chain" /> : chain?.why ? 'type your fill' : <Abs text="could not check — the chain has not loaded" />}</p>
    <button className="btn" disabled={!pick || !p0 || busy} onClick={mark}>MARK{pick ? ` · ${pick.side} ${pick.k} ${pick.ty}` : ''}</button>
    {msg && <p className="msg">{msg}</p>}
  </div>
}

function Seg({ opts, v, on }: { opts: string[]; v?: string; on: (x: string) => void }) {
  return <div className="seg" role="group">{opts.map(o => <button key={o} className={v === o ? 'on' : ''} onClick={() => on(o)}>{o}</button>)}</div>
}
