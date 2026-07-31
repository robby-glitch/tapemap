// Tape Chart Phase 2 — the hover callout, built to the approved mockup
// ("Contract Tape — narration on the chart", artifact 53ed3308, 2026-07-29).
// Presentation only: every number here is read straight off the bar the
// cursor is over (or its neighbour, for the OI delta) — nothing is derived
// as a market claim. `narr` already carries the engine's own tiering and
// tone (trade/narration.ts); this component only lays it out.
import { palette } from '../theme'
import type { Mode } from '../theme'
import { MONO } from '../theme'
import { dayBase } from './indicators'
import type { Narration } from './narration'
import { glossOf, pillText, dirText } from './hinglish'
import type { RotationSignal, TapeBar } from '../data'

interface Props {
  mode: Mode
  bar: TapeBar
  prevBar: TapeBar | null
  day: string
  narr: Narration | null
  /** The band-rotation signal on THIS bar, or null. Presentation only: every
   *  sentence below is the backend's own, quoted verbatim. */
  rot?: RotationSignal | null
  /** Cursor position inside the chart frame. */
  x: number
  y: number
  /** The chart frame's own size, for edge-flipping. */
  boxW: number
  boxH: number
}

// The mockup's box is fluid (`min-width: 252px`, `max-width: 312px`) — its
// exact rendered size depends on content the callout hasn't measured. These
// constants are the assumed size used purely for the position arithmetic
// below (a value inside the min/max band); they are not a layout constraint,
// so the CSS min/max-width still governs what actually paints.
const ASSUMED_W = 280
const ASSUMED_H = 210
// Roughly what the band-rotation block adds when a bar carries a signal:
// a header, the trigger receipt, the compression read and the confirmation
// note. Same standing as the constants above — position arithmetic only.
const ROT_BLOCK_H = 130
const EDGE_MARGIN = 6
const CURSOR_GAP = 20

// Verbatim from the mockup ("tip shadow 0 8px 26px rgba(20,26,34,.16)") — not
// a palette colour (no `shadow` key exists on either palette), so it is kept
// as its own constant rather than invented as a hex literal.
const TIP_SHADOW = '0 8px 26px rgba(20,26,34,.16)'

/**
 * The callout must never cover the candle it describes: it sits to the right
 * of the cursor, vertically centred on it, and flips to the left side when it
 * would overflow the right edge of the frame — then is clamped at least
 * `EDGE_MARGIN` inside every edge of the frame so it never fully leaves the
 * chart either.
 */
function computePosition(
  x: number, y: number, frameW: number, frameH: number,
  w = ASSUMED_W, h = ASSUMED_H,
): { left: number; top: number } {
  let left = x + CURSOR_GAP
  if (left + w > frameW - EDGE_MARGIN) left = x - w - CURSOR_GAP
  left = Math.max(EDGE_MARGIN, Math.min(left, frameW - w - EDGE_MARGIN))

  let top = y - h / 2
  top = Math.max(EDGE_MARGIN, Math.min(top, frameH - h - EDGE_MARGIN))

  return { left, top }
}

/** `dd/mm/yyyy HH:MM` — the date from the session's own anchor (dayBase,
 *  shared with the chart's own axis so the two never disagree), the clock
 *  taken verbatim from the bar's own `t` rather than re-derived. */
function formatDateTime(day: string, t: string): string {
  const [hh, mm] = t.split(':').map(Number)
  const d = new Date(dayBase(day) + (hh * 60 + mm) * 60_000)
  const dd = String(d.getDate()).padStart(2, '0')
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  return `${dd}/${mo}/${d.getFullYear()} ${t}`
}

/** OI plus its change vs the previous bar, "+80k" style. `null`-safe: with no
 *  previous bar there is nothing to difference, so only the level is shown —
 *  never a NaN from subtracting against a missing value. */
function formatOi(oi: number, prevBar: TapeBar | null): string {
  const base = `${(oi / 1e6).toFixed(2)}M`
  if (prevBar == null) return base
  const d = oi - prevBar.oi
  if (d === 0) return `${base} (flat)`
  const sign = d > 0 ? '+' : '−'
  return `${base} (${sign}${Math.round(Math.abs(d) / 1000)}k)`
}

function toneColor(pal: ReturnType<typeof palette>, tone: Narration['tone']): string {
  switch (tone) {
    case 'bull': return pal.bull
    case 'bear': return pal.bear
    case 'structure': return pal.accent
    default: return pal.border
  }
}

export default function Callout({ mode, bar, prevBar, day, narr, rot = null, x, y, boxW, boxH }: Props) {
  const pal = palette(mode)
  // The box grows by the rotation block when there is one, so the
  // edge-flip/clamp arithmetic keeps the WHOLE callout on screen rather than
  // pushing its receipts off the bottom of the frame.
  const { left, top } = computePosition(x, y, boxW, boxH, ASSUMED_W,
    ASSUMED_H + (rot ? ROT_BLOCK_H : 0))
  const accent = narr ? toneColor(pal, narr.tone) : pal.border
  // A rotation signal IS a direction claim, so it takes bull/bear — the same
  // rule the chart marker follows, so the callout and the pill agree on hue.
  const rotTone = rot ? (rot.side === 'BUY' ? pal.bull : pal.bear) : pal.border

  return (
    <div style={{
      position: 'absolute', left, top,
      minWidth: 252, maxWidth: 312,
      borderRadius: 8,
      border: `1px solid ${pal.border}`,
      backgroundColor: pal.card,
      boxShadow: TIP_SHADOW,
      pointerEvents: 'none',
      overflow: 'hidden',
      zIndex: 50,
    }}>
      {/* OHLC block */}
      <div style={{ padding: '9px 11px 8px' }}>
        <div style={{ fontFamily: MONO, fontSize: 11, color: pal.textMuted }}>
          {formatDateTime(day, bar.t)}
        </div>
        <div style={{
          fontFamily: MONO, fontSize: 20, fontWeight: 660, letterSpacing: '-0.02em',
          color: pal.textPrimary, margin: '2px 0 6px',
        }}>
          {bar.c.toFixed(1)}
        </div>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1px 14px',
          fontFamily: MONO, fontSize: 11.5, marginBottom: 6,
        }}>
          <div>
            <span style={{ color: pal.textMuted }}>OPEN </span>
            <span style={{ fontWeight: 560, color: pal.textPrimary }}>{bar.o.toFixed(1)}</span>
          </div>
          <div>
            <span style={{ color: pal.textMuted }}>HIGH </span>
            <span style={{ fontWeight: 560, color: pal.textPrimary }}>{bar.h.toFixed(1)}</span>
          </div>
          <div>
            <span style={{ color: pal.textMuted }}>CLOSE </span>
            <span style={{ fontWeight: 560, color: pal.textPrimary }}>{bar.c.toFixed(1)}</span>
          </div>
          <div>
            <span style={{ color: pal.textMuted }}>LOW </span>
            <span style={{ fontWeight: 560, color: pal.textPrimary }}>{bar.l.toFixed(1)}</span>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: MONO, fontSize: 11.5 }}>
          <span style={{ color: pal.textMuted }}>VOLUME</span>
          <span style={{ color: pal.textPrimary, fontWeight: 560 }}>{bar.v.toLocaleString('en-IN')}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: MONO, fontSize: 11.5 }}>
          <span style={{ color: pal.textMuted }}>OPEN INTEREST</span>
          <span style={{ color: pal.textPrimary, fontWeight: 560 }}>{formatOi(bar.oi, prevBar)}</span>
        </div>
      </div>

      {/* Band-rotation block — the operator's OWN setup, above the engine's
          narration because it is the claim they came for. Every sentence is
          the backend's, quoted verbatim: this component computes nothing
          about the market, and in particular never upgrades an UNKNOWN. */}
      {rot && (
        <div style={{
          padding: '9px 11px 10px', borderTop: `1px solid ${pal.border}`,
          borderLeft: `3px solid ${rotTone}`,
        }}>
          <div style={{
            display: 'flex', alignItems: 'baseline', gap: 7, marginBottom: 4, flexWrap: 'wrap',
          }}>
            <span style={{
              fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase',
              fontWeight: 700, color: rotTone,
            }}>
              {rot.side === 'BUY' ? '▲' : '▼'} {rot.side} {rot.band}
            </span>
            <span style={{ fontSize: 10, color: pal.textMuted, fontWeight: 600 }}>
              band se palat — apna setup
            </span>
          </div>
          <div style={{ fontSize: 11.5, lineHeight: 1.45, color: pal.textPrimary, marginBottom: 5 }}>
            {rot.trigger}
          </div>
          <div style={{
            fontSize: 9.5, letterSpacing: '0.09em', textTransform: 'uppercase',
            color: pal.textMuted, marginBottom: 2,
          }}>
            squeeze pehle — {rot.trap}
            {rot.trap_dwell != null ? ` · dwell ${rot.trap_dwell}` : ''}
          </div>
          <div style={{ fontSize: 11, color: pal.textSecondary, lineHeight: 1.45, marginBottom: 5 }}>
            {rot.trap_why}
          </div>
          {/* The confirmation is UNKNOWN on every index signal and its reason
              says why. Shown, never hidden: a reader who sees the trigger and
              no confirmation line would fill the gap in themselves, and the
              guess that costs money is the optimistic one. */}
          <div style={{
            fontSize: 9.5, letterSpacing: '0.09em', textTransform: 'uppercase',
            color: pal.textMuted, marginBottom: 2,
          }}>
            confirm — {rot.confirm}
          </div>
          <div style={{ fontSize: 10.5, color: pal.textMuted, lineHeight: 1.4 }}>
            {rot.confirm_why}
          </div>
        </div>
      )}

      {/* Narration block — a bar with no event says so, never invents one. */}
      {narr ? (
        <div style={{ padding: '9px 11px 10px', borderTop: `1px solid ${pal.border}`, borderLeft: `3px solid ${accent}` }}>
          {/* Hinglish first, because it is what reads at a glance: the kind's
              own caption, then which way the engine already said this leans.
              The engine's English sentence and its numbers follow underneath,
              verbatim — the gloss translates the KIND, never the claim, so the
              receipt has to stay on screen right next to it. */}
          <div style={{
            display: 'flex', alignItems: 'baseline', gap: 7, marginBottom: 3, flexWrap: 'wrap',
          }}>
            <span style={{
              fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase',
              fontWeight: 700, color: accent,
            }}>
              {pillText(narr.kind)}
            </span>
            <span style={{ fontSize: 10, color: accent, fontWeight: 600 }}>
              {dirText(narr.tone, narr.kind).arrow} {dirText(narr.tone, narr.kind).text}
            </span>
          </div>
          {glossOf(narr.kind) && (
            <div style={{ fontSize: 12, lineHeight: 1.4, color: pal.textPrimary, marginBottom: 5 }}>
              {glossOf(narr.kind)!.line}
            </div>
          )}
          <div style={{
            fontSize: 9.5, letterSpacing: '0.09em', textTransform: 'uppercase',
            color: pal.textMuted, marginBottom: 2,
          }}>
            engine ke apne shabd — {narr.kind}
          </div>
          <div style={{ fontSize: 12, fontWeight: 560, lineHeight: 1.35, color: pal.textSecondary, marginBottom: 3 }}>
            {narr.head}
          </div>
          <div style={{ fontSize: 11, color: pal.textSecondary, lineHeight: 1.45 }}>
            {narr.ev}
          </div>
        </div>
      ) : (
        <div style={{ padding: '9px 11px 10px', borderTop: `1px solid ${pal.border}` }}>
          <div style={{ fontSize: 11, color: pal.textMuted }}>
            is bar par koi event nahi — sirf OHLC
          </div>
        </div>
      )}
    </div>
  )
}
