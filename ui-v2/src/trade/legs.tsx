// THE LEGS PANEL (SHADOW): the leg engine's record for this index, from GET /api/reader (reader_live.py, reader.py;
// docs/reader/8-shadow-build.md). Shadow and unsigned: it decides nothing and says so in its header. LIGHT. This file
// computes nothing that reads the market: every word and number is the server's; it only formats times and lays out.
import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import type { IndexKey } from '../data'
import { MONO, palette } from '../theme'

type Pal = ReturnType<typeof palette>

interface Tape { state: 'ok' | 'thin' | 'cant' | 'none' | 'short_leg'; d?: number; share?: number; lam?: number
  rank?: [number, number] | null; warming?: string; why?: string }
interface Oi { state: 'ok' | 'pub' | 'cant'; d?: number; moved?: number; why?: string; floor?: number }
export interface ReaderLeg {
  id: string; t0: number; t1: number; dir: 1 | -1; px0: number; px1: number; pts: number; mins: number
  ux: Tape; gc: Tape; oi: Oi
  who: { class: string; absorbed: boolean; thin: boolean; split: boolean; expiring: boolean; en?: string; chip?: string }
  en: string; chip: string; confirmed_at?: number; state?: string; back?: number
}
export interface ReaderReply {
  ok: boolean; why: string | null; idx: string; day?: string; shadow: true; signed?: false; asof?: string
  ruler?: number; ruler_note?: string; expiry?: string | null; expiring?: boolean; sessions_left?: number | null
  auction?: { state: string | null; d: number; band: number[] | null }
  legs?: ReaderLeg[]; forming?: ReaderLeg | null
  story?: { t: string; kind: string; en: string; chip: string }[]
  counts?: { legs: number; auction_changes: number }
  tag_note?: string
}

/** 15 s: legs confirm at most once a minute; the reader thread itself passes every 15 s. The poll dies with the panel. */
export function useReader(index: IndexKey) {
  const [reply, setReply] = useState<ReaderReply | null>(null)
  const [why, setWhy] = useState<string | null>('loading')
  useEffect(() => {
    let dead = false
    const pull = () => fetch(`/api/reader?idx=${index}`)
      .then((r) => r.json())
      .then((j: ReaderReply) => { if (!dead) { setReply(j); setWhy(null) } })
      .catch((e) => { if (!dead) setWhy(`could not check — /api/reader: ${e}`) })
    pull()
    const iv = setInterval(pull, 15000)
    return () => { dead = true; clearInterval(iv) }
  }, [index])
  return { reply, why }
}

// THE CROSS-INDEX READ (SHADOW): GET /api/xindex (xindex_live.py; docs/reader/10-xindex-build.md). The server's words
// only; the old LOOK HERE chip in the glance bar is untouched until she signs.
interface XLine { vote: 1 | -1 | 0 | null; why: string }
interface XRow { ok: boolean; why: string | null; D: number; word: string; chip: string; n_for: number; n_check: number
  n_against: number; lines: Record<string, XLine>; thin: boolean }
interface XOut { t: string; idx: Record<string, XRow>; look: { idx: string | null; D: number; line: string }
  sync: { chip: string }; walls: { chip: string }; extremes: { high: { chip: string } | null; low: { chip: string } | null } }
interface XReply { ok: boolean; why?: string | null; shadow: true; signed: false; note?: string; out?: XOut | null
  looks?: { t: string; idx: string | null; line: string }[] }

function useXindex() {
  const [x, setX] = useState<XReply | null>(null)
  useEffect(() => {
    let dead = false
    const pull = () => fetch('/api/xindex').then((r) => r.json())
      .then((j: XReply) => { if (!dead) setX(j) })
      .catch((e) => { if (!dead) setX({ ok: false, why: `could not check — /api/xindex: ${e}`, shadow: true, signed: false }) })
    pull()
    const iv = setInterval(pull, 15000)
    return () => { dead = true; clearInterval(iv) }
  }, [])
  return x
}

function XindexLine({ pal }: { pal: Pal }) {
  const x = useXindex()
  const head: CSSProperties = { fontSize: 9.5, letterSpacing: '0.07em', color: pal.textMuted, fontWeight: 600 }
  const o = x?.out
  const arrow = (d: number) => d > 0 ? '▲' : d < 0 ? '▼' : ''
  const side = (d: number) => d > 0 ? pal.bull : d < 0 ? pal.bear : pal.textMuted
  return (
    <div style={{ marginBottom: 8, paddingBottom: 6, borderBottom: `1px solid ${pal.border}` }}>
      <div style={{ display: 'flex', gap: 14, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 4 }}>
        <span style={{ ...head, color: pal.textPrimary }}>LOOK HERE · SHADOW</span>
        <span style={head}>unsigned · {x?.note ?? 'counts of lines, never a %'}{o ? ` · as of ${o.t}` : ''}</span>
      </div>
      {!x?.ok || !o ? <div style={{ color: pal.textMuted }}>{x?.why ?? 'loading'}</div> : (<>
        <div style={{ color: o.look.idx ? pal.textPrimary : pal.textMuted }}>
          {o.look.idx && <span style={{ color: side(o.look.D), fontWeight: 600 }}>{arrow(o.look.D)} </span>}{o.look.line}
        </div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 4, fontSize: 11 }}>
          {Object.entries(o.idx).map(([k, r]) => (
            <span key={k} title={Object.entries(r.lines).map(([n, l]) => `${n}: ${l.vote === null ? 'check nahi' : l.vote > 0 ? '+' : l.vote < 0 ? '−' : '·'} ${l.why}`).join('\n')}>
              <b>{k}</b> <span style={{ color: side(r.D) }}>{arrow(r.D)}</span> {r.chip}
              {r.ok ? ` · ${r.n_for}/${r.n_check}${r.n_against ? ` (${r.n_against} against)` : ''}` : ''}{r.thin ? ' · patla' : ''}
            </span>))}
        </div>
        <div style={{ marginTop: 3, color: pal.textMuted, fontSize: 11 }}>
          {[o.sync.chip, o.extremes.high?.chip, o.extremes.low?.chip, o.walls.chip].filter(Boolean).join(' · ')}
        </div>
        {(x.looks ?? []).length > 1 && (
          <div style={{ marginTop: 3, color: pal.textMuted, fontSize: 10.5 }} title={(x.looks ?? []).map((l) => `${l.t} ${l.line}`).join('\n')}>
            today: {(x.looks ?? []).map((l) => `${l.t} ${l.idx ?? '—'}`).join(' · ')}
          </div>)}
      </>)}
    </div>
  )
}

const ist = (ms: number) => new Date(ms + 19_800_000).toISOString().slice(11, 16)
const num = (x: number | undefined | null, sign = true) =>
  x == null ? '—' : `${sign && x > 0 ? '+' : ''}${Math.round(x).toLocaleString('en-IN')}`.replace('-', '−')

function tapeCell(t: Tape): { text: string; title: string } {
  if (t.state === 'ok') {
    const eff = t.lam != null ? ` · ${Math.round(t.lam)}/1k ${t.rank ? `(${t.rank[0]} of ${t.rank[1]}, 1 = least)` : '(garam)'}` : ''
    return { text: `Δ${num(t.d)} (${num((t.share ?? 0) * 100)}%)${eff}`, title: 'Δ [I]: side inferred. pts/1k = points per 1,000 lots of net Δ; rank 1 = the LEAST progress per lot of today' }
  }
  if (t.state === 'thin') return { text: `Δ${num(t.d)} patla`, title: t.why ?? '' }
  if (t.state === 'none') return { text: '—', title: t.why ?? 'no tape for this index' }
  return { text: 'check nahi', title: t.why ?? '' }
}

function oiCell(o: Oi): { text: string; title: string } {
  if (o.state === 'ok') return { text: `${num(o.d)} ${o.moved ? '' : '· flat'}`, title: `OI [M], lots; read with a one-update tolerance against ±${o.floor ?? '?'}` }
  if (o.state === 'pub') return { text: `${num(o.d)} · batch`, title: o.why ?? '' }
  return { text: 'check nahi', title: o.why ?? '' }
}

export default function LegsPanel({ pal, index }: { pal: Pal; index: IndexKey }) {
  const { reply, why } = useReader(index)
  const head: CSSProperties = { fontSize: 9.5, letterSpacing: '0.07em', color: pal.textMuted, fontWeight: 600 }
  const cell: CSSProperties = { padding: '3px 8px', borderBottom: `1px solid ${pal.border}`, whiteSpace: 'nowrap' }
  const r = reply
  const rows: ReaderLeg[] = r?.ok ? [...(r.legs ?? []), ...(r.forming ? [{ ...r.forming, state: 'forming' }] : [])] : []
  return (
    <div style={{
      flexShrink: 0, maxHeight: '38%', overflow: 'auto', borderRadius: 6, border: `1px solid ${pal.border}`,
      backgroundColor: pal.card, padding: '8px 12px', fontSize: 11.5, color: pal.textPrimary,
    }}>
      <XindexLine pal={pal} />
      <div style={{ display: 'flex', gap: 14, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 6 }}>
        <span style={{ ...head, color: pal.textPrimary }}>LEGS · SHADOW</span>
        <span style={head}>unsigned thresholds · describes the tape, decides nothing</span>
        {r?.ok && <span style={{ ...head, fontWeight: 400 }} title={r.ruler_note}>ruler {r.ruler} pts · {r.auction?.state ?? '—'}
          {r.auction?.band ? ` ${r.auction.band[0]}–${r.auction.band[1]}` : ''}{r.expiring ? ` · ${r.idx} expiring (${r.sessions_left} session left)` : ''}
          {' · '}as of {r.asof}</span>}
        <span style={{ ...head, fontWeight: 400 }}>{r?.tag_note ?? ''}</span>
      </div>
      {!r?.ok && <div style={{ color: pal.textMuted }}>{why ?? r?.why ?? 'could not check'}</div>}
      {r?.ok && !rows.length && <div style={{ color: pal.textMuted }}>checked: no leg confirmed yet today</div>}
      {r?.ok && rows.length > 0 && (
        <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: MONO, fontSize: 11 }}>
          <thead>
            <tr>{['#', 'time', '', 'pts [M]', 'min', 'UX', 'GC', 'OI [M]', 'who'].map((h) =>
              <th key={h} style={{ ...cell, ...head, textAlign: h === 'who' ? 'left' : 'right' }}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((L, i) => {
              const ux = tapeCell(L.ux), gc = tapeCell(L.gc), oi = oiCell(L.oi)
              const forming = L.state === 'forming'
              return (
                <tr key={L.id} title={L.en} style={{ color: forming ? pal.textMuted : pal.textPrimary }}>
                  <td style={{ ...cell, textAlign: 'right' }}>{forming ? 'abhi' : i + 1}</td>
                  <td style={{ ...cell, textAlign: 'right' }}>{ist(L.t0)}→{ist(L.t1)}</td>
                  <td style={{ ...cell, textAlign: 'center', color: L.dir > 0 ? pal.bull : pal.bear }}>{L.dir > 0 ? '▲' : '▼'}</td>
                  <td style={{ ...cell, textAlign: 'right' }}>{num(L.pts)}</td>
                  <td style={{ ...cell, textAlign: 'right' }}>{L.mins}</td>
                  <td style={{ ...cell, textAlign: 'right' }} title={ux.title}>{ux.text}</td>
                  <td style={{ ...cell, textAlign: 'right' }} title={gc.title}>{gc.text}</td>
                  <td style={{ ...cell, textAlign: 'right' }} title={oi.title}>{oi.text}</td>
                  <td style={{ ...cell, fontFamily: 'inherit' }} title={L.who.en}>{L.who.chip ?? L.who.class}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
      {r?.ok && (r.story ?? []).filter((s) => s.kind === 'auction' || s.kind === 'ruler').length > 0 && (
        <div style={{ marginTop: 6, color: pal.textMuted, fontSize: 11 }}>
          {(r.story ?? []).filter((s) => s.kind === 'auction' || s.kind === 'ruler').map((s, i) =>
            <span key={i} title={s.en} style={{ marginRight: 12 }}>{s.t} {s.chip}</span>)}
        </div>
      )}
    </div>
  )
}
