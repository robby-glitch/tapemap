// The panel beside the chart, in the DESK's language (docs/pro-tool/6-blueprint.md §4.7, §4.8, §6). Every word and
// number is the engine's, verbatim; this panel computes nothing. Its own styles (the DESK's pro.css styles html/body
// globally and is never imported here). The chips copy the DESK's colours, because the floating DESK window sits
// beside this panel and shows the same rows.
import type { CSSProperties, ReactNode } from 'react'
import type { palette } from '../theme'
import { MONO } from '../theme'
import type { FlatRead, TradeView } from './engine'
import type { FoldRead, Rows, Trade } from '../pro/api'
import { GLOSSARY } from './chips'

type Pal = ReturnType<typeof palette>

const BLUE = '#1D4ED8', RED = '#C42B30', GREY = '#8A93A1', AMBER = '#B45309'
const CHIP_C: Record<string, string> = { WITH: BLUE, BUYERS: BLUE, AGAINST: RED, SELLERS: RED }
const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"]
const WORD_C: Record<string, string> = { HOLD: '#141A22', 'PAST GIVE-UP': AMBER, FOLD: RED, "CAN'T CHECK": GREY }
const L = (oi: number | null | undefined) => (oi == null ? '—' : `${(oi / 1e5).toFixed(1)}L`)

/** A trailing [M] / [I] becomes the row's tag. */
function splitTag(s?: string | null): [string | null, string | null] {
  if (!s) return [null, null]
  const m = s.match(/\s*\[(M|I)\]\s*$/)
  return m ? [s.slice(0, m.index), m[1]] : [s, null]
}
/** Could-not-check (grey italic) vs a read (ink): the three absences never collapse. */
const cant = (t?: string | null) => !!t && t.toLowerCase().startsWith('could not check')

function Tag({ pal, t }: { pal: Pal; t: string }) {
  return <span title={t === 'M' ? 'measured' : 'inferred'} style={{
    fontSize: 8.5, fontWeight: 700, color: pal.textMuted, border: `1px solid ${pal.border}`, borderRadius: 2,
    padding: '0 3px', marginLeft: 4, fontFamily: MONO,
  }}>{t}</span>
}

/** An engine sentence with its inline [M]/[I] rendered as small tags. */
function Sentence({ pal, s }: { pal: Pal; s: string }) {
  return <>{s.split(/(\[[MI]\])/).map((p, i) => /^\[[MI]\]$/.test(p) ? <Tag key={i} pal={pal} t={p[1]} /> : p)}</>
}

function Head({ pal, children }: { pal: Pal; children: ReactNode }) {
  return <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.09em', color: pal.textMuted,
                       textTransform: 'uppercase', marginTop: 12, marginBottom: 4 }}>{children}</div>
}

function FourRows({ pal, rows }: { pal: Pal; rows?: Rows | null }) {
  const order: [keyof Rows, string][] = [['zone', 'ZONE'], ['flow', 'FLOW'], ['oi', 'OI'], ['vpin', 'VPIN']]
  return <div>{order.map(([k, name]) => {
    const r = rows?.[k], [text, tag] = splitTag(r?.sentence), chip = r?.chip ?? null
    const c = chip ? CHIP_C[chip] ?? GREY : GREY
    return <div key={k} style={{ display: 'grid', gridTemplateColumns: '34px 64px 1fr', gap: 4, alignItems: 'baseline',
                                 borderTop: `1px solid ${pal.border}`, padding: '3px 0', fontSize: 11 }}>
      <b style={{ fontSize: 9.5, letterSpacing: '0.06em' }}>{name}</b>
      <span style={{ fontSize: 9, fontWeight: 700, color: c, border: `1px solid ${c}`, borderRadius: 3, padding: '0 3px',
                     justifySelf: 'start', whiteSpace: 'nowrap' }}>{chip ?? 'no read'}</span>
      <span style={{ color: cant(text) || !text ? pal.textMuted : pal.textPrimary, fontStyle: cant(text) || !text ? 'italic' : 'normal', lineHeight: 1.35 }}>
        {text ?? 'not read yet'}{r?.machine ? <span style={{ color: pal.textMuted }}> · {r.machine}</span> : null}
        {tag && <Tag pal={pal} t={tag} />}
      </span>
    </div>
  })}</div>
}

function Word({ h }: { h: string }) {
  const w = WORDS.find((x) => h.toUpperCase().startsWith(x)) ?? h
  const rest = h.slice(w.length).replace(/^\s*·\s*/, '')
  return <div style={{ marginTop: 6 }}>
    <span style={{ fontSize: 20, fontWeight: 800, letterSpacing: '0.06em', color: WORD_C[w] ?? '#141A22' }}>{w}</span>
    {rest && <span style={{ fontSize: 12, fontWeight: 600, marginLeft: 6 }}>{rest}</span>}
  </div>
}

export interface SideProps {
  pal: Pal
  index: string
  /** The open marked trade on this index (or the `?tradeview=` review), with the engine's read of it. */
  trade: Trade | null
  fold: FoldRead | null
  review: boolean
  flat: FlatRead | null
  flatWhy: string | null
  replaying: boolean
  /** One line: what is not on the chart, and why. Only the entries that apply. */
  notShown: string[]
}

export default function Side({ pal, index, trade, fold, review, flat, flatWhy, replaying, notShown }: SideProps) {
  const small: CSSProperties = { fontSize: 11, lineHeight: 1.45, margin: '2px 0' }
  const muted: CSSProperties = { ...small, color: pal.textMuted }
  const v = fold?.ok ? (fold.view as TradeView | undefined) : undefined
  let now: ReactNode
  let rows: Rows | null | undefined = null
  if (trade) {
    const line = <p style={small}><b>{review ? 'REVIEW · ' : ''}{trade.role} {trade.k} {trade.side}</b> · in {trade.p0 ?? '—'} · {trade.t0.slice(0, 5)}
      {trade.exit_t && <> · out {trade.exit_t.slice(0, 5)}{v?.frozen ? ' · frozen at the exit' : ''}</>}</p>
    if (!v || v.headline == null) {
      const why = !fold ? 'checking…' : fold.ok ? `could not check — ${v?.why ?? 'no view yet'}` : `could not check — ${fold.why ?? 'the engine gave no reason'}`
      now = <>{line}<Word h="CAN'T CHECK" /><p style={{ ...muted, fontStyle: 'italic' }}>{why}</p></>
    } else {
      rows = v.rows
      const G = v.G, W = v.W, A = v.A as (typeof v.A & { state?: string | null }) | null
      now = <>
        {line}
        <Word h={v.headline} />
        <p style={{ ...small, fontWeight: 600 }}>{v.clause}</p>
        <p style={muted}>{v.line2}</p>
        <Head pal={pal}>Levels <Tag pal={pal} t="M" /></Head>
        <p style={{ ...small, fontFamily: MONO }}>give-up {G ? <b>{G.px}</b> : <i>could not check — no give-up yet</i>}{G?.set_t ? ` · set ${G.set_t}` : ''}{v.mode ? ` · ${v.mode}` : ''}</p>
        <p style={{ ...small, fontFamily: MONO }}>behind {W ? `${W.k} ${W.side} ${L(W.oi)}${W.state ? ` · ${W.state}` : ''}` : <i>could not check — no wall behind</i>}</p>
        <p style={{ ...small, fontFamily: MONO }}>ahead {A ? `${A.k} ${A.side}${A.pts != null ? ` · ${A.pts} pts` : ''} · ${L(A.oi)}${A.peak_t ? `, peak ${L(A.peak)} ${A.peak_t}` : ''}${A.state ? ` · ${A.state}` : ''}` : <i>could not check — no wall ahead</i>}</p>
      </>
    }
  } else if (flat?.ok) {
    rows = flat.rows
    const nf = flat.next_fight
    const box = (k: 'above' | 'below') => {
      const f = nf?.[k]
      return <div key={k} style={{ borderLeft: `2px solid ${pal.border}`, paddingLeft: 6, margin: '5px 0' }}>
        <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.08em', color: pal.textMuted }}>{k.toUpperCase()} {f?.px != null && <b style={{ color: pal.textPrimary, fontFamily: MONO }}>{f.px}</b>}</div>
        {!f ? <p style={{ ...muted, fontStyle: 'italic' }}>could not check — no level {k} yet</p> : <>
          <p style={cant(f.what) ? { ...muted, fontStyle: 'italic' } : small}>{f.what}</p>
          {f.confirm && <p style={muted}><b>confirms:</b> {f.confirm}</p>}</>}
      </div>
    }
    now = <>
      <p style={small}><b>FLAT</b> · {index}{flat.at ? <> · at <b>{flat.at.px}</b> ({flat.at.what})</> : null}{flat.asof ? <span style={{ color: pal.textMuted }}> · as of {flat.asof}</span> : null}</p>
      {flatWhy && <p style={{ ...muted, fontStyle: 'italic' }}>{flatWhy} · showing the last read</p>}
      <div style={{ fontSize: 17, fontWeight: 800, letterSpacing: '0.04em', marginTop: 4 }}>NEXT FIGHT</div>
      {nf ? <p style={{ ...small, fontFamily: MONO }}><b>{nf.above?.px ?? '—'}</b> above · <b>{nf.below?.px ?? '—'}</b> below</p>
          : <p style={{ ...muted, fontStyle: 'italic' }}>could not check — no levels yet</p>}
      {nf && <>{box('above')}{box('below')}</>}
      {flat.gave_up && <p style={{ ...small, fontWeight: 700 }}>{flat.gave_up.text} <span style={{ fontWeight: 400, color: pal.textMuted }}>· {flat.gave_up.unproven}</span></p>}
      {flat.reentry && <p style={muted}><b>RE-ENTRY · unproven</b> · {flat.reentry.text}</p>}
    </>
  } else {
    now = <><Word h="CAN'T CHECK" /><p style={{ ...muted, fontStyle: 'italic' }}>{flatWhy ?? 'checking…'}</p></>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, color: pal.textPrimary }}>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', margin: '0 -12px', padding: '0 12px' }}>
        {now}
        {replaying && <p style={{ ...muted, fontStyle: 'italic' }}>not shown: the engine's read is live, not at the replay cursor</p>}
        <Head pal={pal}>The four reads</Head>
        {rows ? <FourRows pal={pal} rows={rows} /> : <p style={{ ...muted, fontStyle: 'italic' }}>could not check — no read</p>}
        {!trade && flat?.ok && <>
          <Head pal={pal}>The day</Head>
          <p style={small}>{flat.day ? <Sentence pal={pal} s={flat.day} /> : <i>could not check — no day sentence yet</i>}</p>
        </>}
      </div>
      <div style={{ borderTop: `1px solid ${pal.border}`, marginTop: 8, paddingTop: 6, fontSize: 9.5, lineHeight: 1.5, color: pal.textMuted }}>
        <div style={{ fontWeight: 700, letterSpacing: '0.06em', color: pal.textSecondary }}>NISHAAN KA MATLAB</div>
        {GLOSSARY.map(([g, m]) => (
          <div key={g} style={{ display: 'grid', gridTemplateColumns: '26px 1fr', gap: 4 }}>
            <b style={{ color: pal.textPrimary, fontFamily: MONO }}>{g}</b><span>{m}</span>
          </div>
        ))}
        <div style={{ marginTop: 2 }}>P A E C ke chips extension ka read hain [I]; baaki engine ke.</div>
        {notShown.length > 0 && <div style={{ marginTop: 3 }}><b>Not on the chart:</b> {notShown.join(' · ')}</div>}
      </div>
    </div>
  )
}
