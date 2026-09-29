// The hover card: the bar's own OHLC and volume, then what the chart marked inside this bar, each in its source's
// own words (the zone machine's trigger sentence, the engine's mark text, her footprint mark with its side and level).
// Presentation only: nothing here is derived as a market claim.
import { palette } from '../theme'
import type { Mode } from '../theme'
import { MONO } from '../theme'
import { dayBase } from './indicators'
import type { RotationSignal, TapeBar } from '../data'
import type { FootEvent } from './footprint'
import type { EngMark } from './engine'
import { BUY_C, SELL_C, engChip, footChip, sideColor } from './chips'

interface Props {
  mode: Mode
  bar: TapeBar
  day: string
  /** Her zone machine's entry on this bar (3-minute machine), or null. */
  entry: RotationSignal | null
  /** Her footprint marks stamped inside this bar. */
  ofd: FootEvent[]
  /** The engine's marks stamped inside this bar. */
  fights: EngMark[]
  x: number
  y: number
  boxW: number
  boxH: number
}

const W = 280, H = 190, EDGE = 6, GAP = 20
const KIND: Record<string, string> = { trap: 'P · trap', absorption: 'A · absorption', exhaustion: 'E · exhaustion', climax: 'C · climax' }

function place(x: number, y: number, fw: number, fh: number) {
  let left = x + GAP
  if (left + W > fw - EDGE) left = x - W - GAP
  left = Math.max(EDGE, Math.min(left, fw - W - EDGE))
  const top = Math.max(EDGE, Math.min(y - H / 2, fh - H - EDGE))
  return { left, top }
}

function dateTime(day: string, t: string): string {
  const [hh, mm] = t.split(':').map(Number)
  const d = new Date(dayBase(day) + (hh * 60 + mm) * 60_000)
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()} ${t}`
}

export default function Callout({ mode, bar, day, entry, ofd, fights, x, y, boxW, boxH }: Props) {
  const pal = palette(mode)
  const { left, top } = place(x, y, boxW, boxH)
  const row = { fontSize: 11, lineHeight: 1.4, color: pal.textSecondary } as const
  return (
    <div style={{
      position: 'absolute', left, top, minWidth: 240, maxWidth: 320, borderRadius: 8, border: `1px solid ${pal.border}`,
      backgroundColor: pal.card, boxShadow: '0 8px 26px rgba(20,26,34,.16)', pointerEvents: 'none', overflow: 'hidden', zIndex: 50,
    }}>
      <div style={{ padding: '9px 11px 8px', fontFamily: MONO }}>
        <div style={{ fontSize: 11, color: pal.textMuted }}>{dateTime(day, bar.t)}</div>
        <div style={{ fontSize: 19, fontWeight: 650, color: pal.textPrimary, margin: '2px 0 5px' }}>{bar.c.toFixed(1)}</div>
        <div style={{ fontSize: 11.5, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1px 12px' }}>
          <span><span style={{ color: pal.textMuted }}>O </span>{bar.o.toFixed(1)}</span>
          <span><span style={{ color: pal.textMuted }}>H </span>{bar.h.toFixed(1)}</span>
          <span><span style={{ color: pal.textMuted }}>C </span>{bar.c.toFixed(1)}</span>
          <span><span style={{ color: pal.textMuted }}>L </span>{bar.l.toFixed(1)}</span>
        </div>
        <div style={{ fontSize: 11.5, marginTop: 3 }}><span style={{ color: pal.textMuted }}>VOL </span>{bar.v.toLocaleString('en-IN')}</div>
      </div>
      {entry && (
        <div style={{ padding: '8px 11px', borderTop: `1px solid ${pal.border}`, borderLeft: `3px solid ${entry.side === 'BUY' ? BUY_C : SELL_C}` }}>
          <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.06em', color: entry.side === 'BUY' ? BUY_C : SELL_C }}>
            {entry.side === 'BUY' ? '▲' : '▼'} {entry.side} {entry.band} · your zone (3-minute machine)
          </div>
          <div style={{ ...row, color: pal.textPrimary, marginTop: 3 }}>{entry.trigger}</div>
        </div>
      )}
      {(fights.length > 0 || ofd.length > 0) && (
        <div style={{ padding: '7px 11px 9px', borderTop: `1px solid ${pal.border}` }}>
          {fights.map((m, i) => {
            const c = engChip(m)
            return (
              <div key={`f${i}`} style={row}>
                <b style={{ color: c?.color ?? sideColor(m.side) }}>
                  {m.kind === 'won' ? (m.side > 0 ? '▲' : '▼') : m.kind === 'absorbed' ? '▬' : '═'} {c?.text ?? m.text}
                </b>
                {c?.text !== m.text && <div style={{ color: pal.textMuted, fontSize: 10.5 }}>engine: {m.text}{m.by === 'price' ? ' [I]' : ' [M]'}</div>}
              </div>
            )
          })}
          {ofd.map((e, i) => {
            const c = footChip(e)
            return (
              <div key={`o${i}`} style={row}>
                <b style={{ color: c?.color ?? sideColor(e.side) }}>{c?.text ?? KIND[e.kind] ?? e.kind}</b>
                <div style={{ color: pal.textMuted, fontSize: 10.5 }}>
                  footprint, aapka · {KIND[e.kind] ?? e.kind}{e.p != null ? ` @ ${e.p}` : ''}{e.at ? ` · ${e.at}` : ' · named level par nahi'} [I]
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
