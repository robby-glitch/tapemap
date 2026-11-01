import { useEffect, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { usePalette, MONO } from '../theme'

/* ── ALGO — the algo panel (Mary, 1 Nov 2026). Draws GET /api/algo verbatim: `live` (algo-lab/live_algo.py, today so
   far, rewritten every minute in market hours by its own process) and `panel` (algo-lab/shadow.py, the evening paper
   replay of every new session, with the kill rules and the 25 research days). Three lines each: the demo selling, the
   demo buying, and the quant's v2. Nothing is computed here. LIGHT; counts, never a rate; green/red stay
   direction-only, so P&L is ink; display only — I read, I don't place. */

type Cell = { line: string; idx: string; setup: string; n: number; w: number; R: number; R_wo_best: number; pts: number | null; rs_lot: number }
type Kill = { id: string; what: string; n: number; need: number; hit: boolean }
type Row = { line: string; idx: string; setup: string; side: string; legs: string; entry_t: string; exit_t: string; prem_pts: number; R: number; exit: string }
type Panel = {
  ok: boolean; why?: string; built_at?: string; sessions?: number; first?: string | null; last?: string | null; why_empty?: string | null
  forward?: Cell[]; kills?: Kill[]; research?: Cell[]; research_days?: string
  latest?: { day: string; idx: string[]; rows: Row[]; no_trade: string[] } | null
}
type LRow = { idx: string; setup: string; side: string; legs: string; entry_t: string; exit_t: string; entry: number; now: number; prem_pts: number; R: number | null; stop: number | null; lots: number; exit: string }
type LLine = { open: LRow[]; closed: LRow[]; skipped: { idx: string; t: string; setup: string; why: string }[] }
type Live = { ok: boolean; why?: string; day?: string; written?: string; stale_why?: string | null; idx?: Record<string, { asof: string | null; why: string | null }>; lines?: Record<string, LLine> }
type Doc = { panel: Panel; live: Live }

const POLL_MS = 20000
const LINES = ['demo_sell', 'demo_buy', 'v2']
const LINE: Record<string, [string, string]> = { demo_sell: ['DEMO · SELL', 'bech'], demo_buy: ['DEMO · BUY', 'kharid'], v2: ['V2 · ENGINE', 'khud chunta'] }
const SETUP: Record<string, string> = { A: 'pehla ghanta', B: 'dopahar leg', C: 'zone fade', R: 'rotation fly', all: 'sab' }
const signed = (x: number, d: number) => (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })
const exitChip = (e: string) => e.startsWith('STOP') ? 'line toot gayi' : e.startsWith('TIME') ? 'teen baje' : e.startsWith('PALAT') ? 'palat'
  : e.startsWith('ZONE') ? 'zone' : e.startsWith('TREND') ? 'trend aaya' : ''
const istNow = () => new Date(Date.now() + 330 * 60000)
const hms = (s: string) => { const [h, m, x] = s.split(':').map(Number); return h * 3600 + m * 60 + (x || 0) }

export default function AlgoTab() {
  const pal = usePalette()
  const [doc, setDoc] = useState<Doc | null>(null)
  const [why, setWhy] = useState<string | null>('reading…')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const res = await fetch('/api/algo')
        if (!res.ok) throw new Error(res.status === 404 ? 'the server has no /api/algo yet — restart TapeMap after the close to load it' : `HTTP ${res.status}`)
        const j = (await res.json()) as Doc
        if (alive) { setDoc(j); setWhy(null) }
      } catch (e) {
        if (alive) setWhy(`could not check — ${e instanceof Error ? e.message : String(e)}`)
      }
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [])

  const box: CSSProperties = { background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 6, padding: '10px 12px', marginBottom: 10 }
  const lab: CSSProperties = { fontSize: 10.5, letterSpacing: 0.4, color: pal.textMuted, textTransform: 'uppercase', marginBottom: 6 }
  const th: CSSProperties = { textAlign: 'left', fontWeight: 600, color: pal.textMuted, fontSize: 10.5, padding: '3px 8px', borderBottom: `1px solid ${pal.border}`, whiteSpace: 'nowrap' }
  const td: CSSProperties = { padding: '3px 8px', borderBottom: `1px solid ${pal.border}`, whiteSpace: 'nowrap', fontFamily: MONO, fontSize: 12 }
  const num: CSSProperties = { ...td, textAlign: 'right' }
  const chip = (t: string) => t ? <span style={{ marginLeft: 6, padding: '0 6px', borderRadius: 8, background: pal.inset, border: `1px solid ${pal.border}`, color: pal.textSecondary, fontSize: 10.5, fontFamily: 'inherit' }}>{t}</span> : null
  const pill = (t: string, warn: boolean, strong = false) => <span style={{ padding: '1px 7px', borderRadius: 4, fontSize: 10.5, fontWeight: 700, color: warn ? pal.caution : strong ? pal.textPrimary : pal.textSecondary, border: `1px solid ${warn ? pal.caution : strong ? pal.textPrimary : pal.border}`, background: warn ? pal.inset : pal.card }}>{t}</span>
  const line = (l: string) => <>{(LINE[l] ?? [l])[0]}{chip((LINE[l] ?? [l, ''])[1])}</>
  const table = (head: string[], body: ReactNode) => (
    <div style={{ overflowX: 'auto' }}><table style={{ borderCollapse: 'collapse', width: '100%' }}>
      <thead><tr>{head.map((h, i) => <th key={h + i} style={i > 2 ? { ...th, textAlign: 'right' } : th}>{h}</th>)}</tr></thead>
      <tbody>{body}</tbody></table></div>)
  const cells = (cs: Cell[]) => table(['line', 'idx', 'setup', 'n', 'W / L', 'R', 'R w/o best', 'prem pts', '₹ / lot', ''],
    cs.map((c) => (
      <tr key={c.line + c.idx + c.setup} style={c.idx === 'all' ? { background: pal.inset, fontWeight: 600 } : undefined}>
        <td style={td}>{line(c.line)}</td><td style={td}>{c.idx}</td><td style={td}>{c.setup}{chip(SETUP[c.setup] ?? '')}</td>
        <td style={num}>{c.n}</td><td style={num}>{c.w} / {c.n - c.w}</td><td style={num}>{signed(c.R, 2)}</td>
        <td style={num}>{signed(c.R_wo_best, 2)}</td><td style={num}>{c.pts == null ? '—' : signed(c.pts, 1)}</td>
        <td style={num}>{signed(c.rs_lot, 0)}</td>
        <td style={num}>{c.n < 15 ? pill('KAM DATA · n<15', false) : pill('n ≥ 15', false)}</td>
      </tr>)))

  if (!doc) return <div style={{ ...box, margin: 12, color: pal.textSecondary, fontSize: 13 }}>ALGO — {why ?? 'reading…'}</div>

  const { panel, live } = doc
  const now = istNow(), today = now.toISOString().slice(0, 10), nowMin = now.getUTCHours() * 60 + now.getUTCMinutes()
  const market = now.getUTCDay() > 0 && now.getUTCDay() < 6 && nowMin >= 556 && nowMin <= 945
  const lag = live.ok && live.written ? (now.getUTCHours() * 3600 + now.getUTCMinutes() * 60 + now.getUTCSeconds()) - hms(live.written) : null
  const liveNote = !live.ok ? null : live.day !== today ? `last session ${live.day} · its final read`
    : live.stale_why ? live.stale_why : market && lag != null && lag > 150 ? `purana — written ${live.written}, ${Math.round(lag / 60)} min ago (is live_algo.py running?)`
    : market ? null : `market band · the day's last read ${live.written}`
  const lrows: ReactNode[] = []
  if (live.ok) for (const ln of LINES) {
    const L = live.lines?.[ln]
    if (!L) continue
    const show = (r: LRow, open: boolean) => lrows.push(
      <tr key={ln + r.idx + r.entry_t}>
        <td style={td}>{line(ln)}</td><td style={td}>{r.idx}</td>
        <td style={td}>{open ? pill('TRADE MEIN', false, true) : pill('BAND', false)}</td>
        <td style={num}>{r.setup}{chip(SETUP[r.setup] ?? '')}</td>
        <td style={num}>{r.legs}{chip(r.side === 'SELL' ? 'bech' : 'kharid')} × {r.lots}</td>
        <td style={num}>{r.entry_t}{open ? '' : ` → ${r.exit_t}`}</td>
        <td style={num}>{r.entry.toFixed(2)} → {r.now.toFixed(2)}</td>
        <td style={num}>{signed(r.prem_pts, 1)}</td><td style={num}>{r.R == null ? '—' : signed(r.R, 2)}</td>
        <td style={num}>{open ? (r.stop == null ? 'stop — none' : <>stop {r.stop.toLocaleString('en-IN')}f{chip('line')}</>) : <>{r.exit}{chip(exitChip(r.exit))}</>}</td>
      </tr>)
    L.open.forEach((r) => show(r, true))
    L.closed.forEach((r) => show(r, false))
    if (!L.open.length && !L.closed.length) {
      const s = L.skipped[L.skipped.length - 1]
      lrows.push(<tr key={ln + 'none'}><td style={td}>{line(ln)}</td><td style={td}>—</td><td style={td}>{pill('KHALI', false)}</td>
        <td style={{ ...td, color: pal.textMuted, whiteSpace: 'normal' }} colSpan={7}>{s ? `no trade · last refusal ${s.idx} ${s.setup} ${s.t}: ${s.why}` : 'no trade · no signal yet'}</td></tr>)
    }
  }
  const hits = (panel.kills ?? []).filter((k) => k.hit).length
  return (
    <div style={{ padding: 12, color: pal.textPrimary, fontSize: 13 }}>
      <div style={box}>
        <div style={{ ...lab, display: 'flex', gap: 14, flexWrap: 'wrap' }}>
          <b style={{ color: pal.textPrimary, letterSpacing: 0.5 }}>LIVE · PAPER</b>
          {live.ok && Object.entries(live.idx ?? {}).map(([k, v]) => <span key={k}>{k} {v.asof ?? v.why}</span>)}
          {live.ok && <span>written {live.written}</span>}
          <span>[M] the algo's call on the record so far · no orders</span>
        </div>
        {!live.ok && <div style={{ color: pal.textSecondary }}>{live.why}</div>}
        {liveNote && <div style={{ color: market ? pal.caution : pal.textSecondary, marginBottom: 6 }}>{liveNote}</div>}
        {live.ok && table(['line', 'idx', 'state', 'setup', 'legs × lots', 'time', 'entry → now', 'prem pts', 'R', 'stop / exit'], lrows)}
      </div>

      <div style={{ ...box, display: 'flex', gap: 18, flexWrap: 'wrap', alignItems: 'baseline' }}>
        <b style={{ letterSpacing: 0.5 }}>EVENING SHADOW</b>
        {panel.ok ? <>
          <span>forward sessions <b style={{ fontFamily: MONO }}>{panel.sessions}</b>{panel.first ? ` · ${panel.first} → ${panel.last}` : ''}</span>
          <span>kill rules {pill(hits ? `${hits} RUKO` : 'sab dekh rahe', hits > 0)}</span>
          <span style={{ color: pal.textMuted }}>[M] replay after the close · written {panel.built_at} · next 16:10</span>
        </> : <span style={{ color: pal.textSecondary }}>{panel.why}</span>}
      </div>
      {panel.ok && panel.why_empty && <div style={{ ...box, color: pal.textSecondary }}>{panel.why_empty}</div>}

      {panel.ok && panel.latest && <div style={box}>
        <div style={lab}>latest scored session · {panel.latest.day} · recorded {panel.latest.idx.join(' + ') || 'none'}</div>
        {table(['line', 'idx', 'setup', 'legs', 'entry → exit', 'prem pts', 'R', 'exit'], <>
          {panel.latest.rows.map((r, i) => (
            <tr key={i}>
              <td style={td}>{line(r.line)}</td><td style={td}>{r.idx}</td><td style={td}>{r.setup}{chip(SETUP[r.setup] ?? '')}</td>
              <td style={num}>{r.legs}{chip(r.side === 'SELL' ? 'bech' : 'kharid')}</td><td style={num}>{r.entry_t} → {r.exit_t}</td>
              <td style={num}>{signed(r.prem_pts, 1)}</td><td style={num}>{signed(r.R, 2)}</td>
              <td style={num}>{r.exit}{chip(exitChip(r.exit))}</td>
            </tr>))}
          {panel.latest.no_trade.map((l) => <tr key={l}><td style={td}>{line(l)}</td><td style={{ ...td, color: pal.textMuted }} colSpan={7}>no trade — every refusal is in the replay's skipped log</td></tr>)}
        </>)}
      </div>}

      {panel.ok && <div style={box}>
        <div style={lab}>forward record · R on each line's own risk, so compare R within a line</div>
        {(panel.forward ?? []).some((c) => c.n > 0) ? cells(panel.forward ?? []) : <div style={{ color: pal.textMuted }}>no forward trade yet</div>}
      </div>}

      {panel.ok && <div style={box}>
        <div style={lab}>kill rules · from both studies' RESULTS §8</div>
        {table(['rule', 'what', '', 'progress', 'state'], (panel.kills ?? []).map((k, i) => (
          <tr key={i}>
            <td style={td}>{k.id}</td><td style={{ ...td, fontFamily: 'inherit', whiteSpace: 'normal' }} colSpan={2}>{k.what}</td>
            <td style={num}>{k.n} of {k.need}</td><td style={num}>{k.hit ? pill('RUKO · TRIGGERED', true) : pill('dekh rahe', false)}</td>
          </tr>)))}
        <div style={{ color: pal.textMuted, fontSize: 11.5, marginTop: 6 }}>K8 / F-K8 (live reads vs this replay) and K10 / F-K9 (blind minutes) need the live CARD: check by hand.</div>
      </div>}

      {panel.ok && <div style={box}>
        <div style={lab}>research record · {panel.research_days} · seen days, not proof</div>
        {cells(panel.research ?? [])}
      </div>}
    </div>)
}
