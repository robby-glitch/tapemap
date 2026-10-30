import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import type { IndexKey } from '../data'
import { usePalette, rgbOf, MONO } from '../theme'
import { read, leanOf, resultOf, lakh, mm, W, HOLD, MOVE, FLOW, ACCEL } from './speed'
import type { Accel, Cell, Minutes, Side } from './speed'

/* ── RAFTAAR — the OI speed tab (Mary, 27 Oct 2026). The engine, its words and its [M]/[I] tags live in speed.ts;
   this file only draws them. One poll of /api/oihist (the grid the Board and War read), so the stamps here and the
   Board's "ruka" sit on the same minutes. LIGHT; no price chart; hue = side only (the Board's coral / teal), state is
   words + geometry; every glyph carries its Hinglish chip; display only. */

type Doc = { ok: boolean; why?: string | null; minutes?: Minutes; fronts?: { k: number; side: Side }[] | null }

const CE_HUE = '#C4452C', PE_HUE = '#0B8277'   // Board.tsx's side hues
const POLL_MS = 15000
const hue = (s: Side) => (s === 'CE' ? CE_HUE : PE_HUE)
const who = (s: Side) => (s === 'CE' ? 'CALL' : 'PUT')
const wash = (hex: string, a: number) => `rgba(${rgbOf(hex)},${a})`
const f0 = (x: number) => Math.round(x).toLocaleString('en-IN')
const f1 = (x: number) => x.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const pts = (x: number | null) => (x == null ? '—' : (x > 0 ? '+' : x < 0 ? '−' : '') + f1(Math.abs(x)))
const perMin = (x: number | null) => (x == null ? '—' : lakh(x, true) + '/m')
const istNow = () => Math.floor((Date.now() / 60000 + 330) % 1440)

export default function SpeedTab({ index }: { index: IndexKey }) {
  const pal = usePalette()
  const [doc, setDoc] = useState<Doc | null>(null)
  const [why, setWhy] = useState<string | null>('reading…')
  const [all, setAll] = useState(false)
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const res = await fetch(`/api/oihist?idx=${index}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const j = (await res.json()) as Doc
        if (alive) { setDoc(j); setWhy(j.ok ? null : j.why || 'the OI grid is not ready') }
      } catch (e) {
        if (alive) setWhy(`the backend did not answer (${String(e)}) — the last read stays on screen`)
      }
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])

  const r = useMemo(() => (doc?.ok ? read(doc.minutes) : null), [doc])
  const star = useMemo(() => new Set((doc?.fronts ?? []).map((f) => f.side + f.k)), [doc])
  const box: CSSProperties = { background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 6, padding: '10px 12px' }
  const lab: CSSProperties = { fontSize: 10.5, letterSpacing: 0.4, color: pal.textMuted, textTransform: 'uppercase' }

  if (!r) return (
    <div style={{ ...box, margin: 12, color: pal.textSecondary, fontSize: 13 }}>
      RAFTAAR · {index} — {why ?? (doc?.ok ? 'the grid has no minute with a spot yet' : 'reading…')}
    </div>)

  const now = istNow(), late = now - mm(r.asof)
  const stale = now >= 555 && now <= 930 && late > 3 ? `grid purana — last minute ${r.asof}, ${late} min ago` : now > 930 ? `market band · last read ${r.asof}` : null
  const lean = leanOf(r.net, r.d5, r.step)
  const cell = (k: number, s: Side) => r.cells.find((c) => c.k === k && c.side === s)!
  const max = Math.max(...r.cells.map((c) => Math.abs(c.spd ?? 0)), 1)
  const rows = [...r.nine].reverse()          // highest strike on top, as on her chain
  const marks = r.stamps.filter((s) => all || star.has(s.side + s.k)).slice(0, 40)

  const accelChip = (a: Accel) => a == null ? <span style={{ color: pal.textMuted }}>—</span> : (
    <span style={{ fontWeight: a === 'tez' || a === 'palta' ? 700 : 500, color: a === 'dheema' ? pal.textSecondary : pal.textPrimary }}>{ACCEL[a]}</span>)

  const flowPill = (c: Cell) => {
    const h = hue(c.side), f = c.flow
    const st: CSSProperties = { display: 'inline-block', minWidth: 84, textAlign: 'center', padding: '2px 6px', borderRadius: 4, fontSize: 11, fontWeight: 700,
      color: f === 'R' || f == null ? pal.textSecondary : h, background: f === 'W' ? wash(h, 0.14) : f === 'C' ? pal.card : pal.inset,
      border: f === 'C' ? `1px dashed ${h}` : `1px solid ${f === 'W' ? wash(h, 0.4) : pal.border}` }
    return <span style={st}>{f ? FLOW[f] : 'PATA NAHI'}</span>
  }

  const bar = (c: Cell) => {
    const w = c.spd == null ? 0 : Math.round((Math.abs(c.spd) / max) * 64), h = hue(c.side), cover = (c.spd ?? 0) < 0
    return (
      <div style={{ width: 66, display: 'flex', justifyContent: c.side === 'CE' ? 'flex-end' : 'flex-start' }}>
        <div title={`${who(c.side)} ${f0(c.k)}: ${perMin(c.spd)} [M]`} style={{ width: w, height: 10, borderRadius: 2,
          background: cover ? 'transparent' : h, border: cover ? `1.5px solid ${h}` : 'none', boxSizing: 'border-box' }} />
      </div>)
  }

  const side = (c: Cell) => {
    const res = resultOf(c.flow, c.vs, r.step)
    const loud = res === 'ulta likh rahe' || res === 'bhaag rahe'
    const parts = [
      <td key="f" style={{ padding: '4px 6px' }}>{flowPill(c)}</td>,
      <td key="b" style={{ padding: '4px 2px' }}>{bar(c)}</td>,
      <td key="n" style={{ padding: '4px 6px', fontFamily: MONO, fontWeight: 700, textAlign: 'right' }}>{perMin(c.spd)}</td>,
      <td key="p" style={{ padding: '4px 6px', fontFamily: MONO, color: pal.textSecondary, textAlign: 'right' }}>{perMin(c.before)}</td>,
      <td key="a" style={{ padding: '4px 6px', whiteSpace: 'nowrap' }}>{accelChip(c.accel)}</td>,
      <td key="r" style={{ padding: '4px 6px', whiteSpace: 'nowrap', color: loud ? pal.caution : pal.textSecondary, fontWeight: loud ? 700 : 400 }}>{res ?? '—'}</td>,
      <td key="s" style={{ padding: '4px 6px', fontFamily: MONO, color: pal.textMuted, whiteSpace: 'nowrap' }}>{c.since ? `se ${c.since}` : '—'}</td>,
    ]
    return c.side === 'CE' ? parts.reverse() : parts
  }

  const head = (s: Side) => {
    const n = r.net[s]
    return (
      <div style={box}>
        <div style={{ ...lab, color: hue(s) }}>{who(s)} writers · nine strikes</div>
        <div style={{ fontFamily: MONO, fontSize: 22, fontWeight: 700, color: pal.textPrimary }}>{perMin(n.spd)}</div>
        <div style={{ fontSize: 12, color: pal.textSecondary }}>pehle {perMin(n.before)} · {accelChip(n.accel)}</div>
      </div>)
  }

  const th: CSSProperties = { ...lab, padding: '4px 6px', fontWeight: 600, textAlign: 'left', whiteSpace: 'nowrap' }
  const sideHead = ['flow', '', `ab ${W}m`, 'pehle', 'chaal', 'price', 'kab se']
  return (
    <div style={{ padding: 12, display: 'grid', gap: 10, background: pal.bg, color: pal.textPrimary, fontSize: 12.5 }}>
      <div style={{ display: 'flex', gap: 14, alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 800, letterSpacing: 0.6 }}>RAFTAAR · {index}</span>
        <span style={{ fontFamily: MONO }}>{r.asof}</span>
        <span style={{ fontFamily: MONO }}>spot {f1(r.spot!)}s</span>
        <span style={{ fontFamily: MONO, color: pal.textSecondary }}>5m {pts(r.d5)} · 15m {pts(r.d15)} pts</span>
        {stale && <span style={{ color: pal.caution, fontWeight: 700 }}>{stale}</span>}
        {why && <span style={{ color: pal.caution }}>{why}</span>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
        {head('CE')}
        {head('PE')}
        <div style={box}>
          <div style={lab}>zor vs result · {W} min</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: lean?.dir === 1 ? pal.bull : lean?.dir === -1 ? pal.bear : pal.textSecondary }}>
            {lean ? `${lean.dir === 1 ? '▲ ' : lean.dir === -1 ? '▼ ' : ''}${lean.word}` : 'could not check — no 10-min history yet'}
          </div>
          <div style={{ fontSize: 12, color: lean?.result?.startsWith('price ulta') ? pal.caution : pal.textSecondary, fontWeight: lean?.result?.startsWith('price ulta') ? 700 : 400 }}>
            {lean?.result ?? '—'} · spot {pts(r.d5)}
          </div>
        </div>
      </div>

      <div style={{ ...box, padding: 0, overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${pal.border}` }}>
              {[...sideHead].reverse().map((x) => <th key={'c' + x} style={{ ...th, color: CE_HUE }}>{x}</th>)}
              <th style={{ ...th, textAlign: 'center' }}>strike</th>
              {sideHead.map((x) => <th key={'p' + x} style={{ ...th, color: PE_HUE }}>{x}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((k) => (
              <tr key={k} style={{ borderBottom: `1px solid ${pal.border}`, background: k === r.atm ? pal.inset : undefined }}>
                {side(cell(k, 'CE'))}
                <td style={{ padding: '4px 10px', textAlign: 'center', fontFamily: MONO, fontWeight: k === r.atm ? 800 : 600, whiteSpace: 'nowrap',
                  borderLeft: `1px solid ${pal.border}`, borderRight: `1px solid ${pal.border}` }}>
                  {star.has('CE' + k) && <span title="a §1d front (Board)" style={{ color: CE_HUE }}>★ </span>}
                  {f0(k)}{k === r.atm && <span style={{ color: pal.textMuted, fontWeight: 400 }}> ATM</span>}
                  {star.has('PE' + k) && <span title="a §1d front (Board)" style={{ color: PE_HUE }}> ★</span>}
                </td>
                {side(cell(k, 'PE'))}
              </tr>))}
          </tbody>
        </table>
      </div>

      <div style={box}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
          <span style={lab}>KRAM · kab kya badla · newest first</span>
          <button onClick={() => setAll((v) => !v)} style={{ fontSize: 11, padding: '2px 8px', border: `1px solid ${pal.border}`, borderRadius: 4,
            background: pal.inset, color: pal.textSecondary, cursor: 'pointer' }}>{all ? 'sirf ★ fronts' : 'sab nau strikes'}</button>
        </div>
        {!marks.length && <div style={{ color: pal.textSecondary }}>{all ? `no change has held for ${HOLD} minutes yet` : 'the ★ fronts have not changed flow yet — try sab nau strikes'}</div>}
        <div style={{ display: 'grid', gridTemplateColumns: 'auto auto auto auto 1fr', columnGap: 14, rowGap: 3, fontSize: 12.5 }}>
          {marks.map((s, i) => {
            const moved = s.spot == null ? null : r.spot! - s.spot
            const vs = moved == null || Math.abs(moved) < MOVE * r.step ? 0 : s.side === 'CE' ? moved : -moved   // + is against its writers
            return [
              <span key={i + 't'} style={{ fontFamily: MONO, fontWeight: 700 }}>{s.t}</span>,
              <span key={i + 'k'} style={{ fontFamily: MONO, color: hue(s.side), fontWeight: 700 }}>{s.side} {f0(s.k)}</span>,
              <span key={i + 'w'} style={{ fontWeight: s.flow === 'W' ? 700 : 500 }}>{s.word}</span>,
              <span key={i + 's'} style={{ fontFamily: MONO, color: pal.textSecondary }}>{s.spot == null ? 'spot —' : `@ ${f1(s.spot)}s`}</span>,
              <span key={i + 'v'} style={{ color: vs != null && vs > 0 ? pal.caution : pal.textSecondary }}>
                {moved == null ? '' : `tab se price ${pts(moved)} · ${vs > 0 ? 'unke khilaaf' : vs < 0 ? 'unke haq mein' : 'wahi'}`}</span>,
            ]
          })}
        </div>
      </div>

      <div style={{ fontSize: 11, color: pal.textMuted, lineHeight: 1.5 }}>
        raftaar = OI change per minute over the last {W} min [M] · pehle = the {W} min before that [M] · RUKE = under §1d's stall rate
        (5 % of the strike's own size per 15 min) [I] · a change is stamped when it holds {HOLD} min, at its first minute [I] · price = spot over
        the same {W} min, against (+) or with the writers [M] · ★ = the Board's §1d fronts · display only, it gates nothing.
      </div>
    </div>)
}
