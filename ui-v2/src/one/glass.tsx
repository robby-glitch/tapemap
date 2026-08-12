import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode, PointerEvent as ReactPointerEvent } from 'react'
import type { Palette } from '../theme'

/* ── The glass instrument ────────────────────────────────────────────────────
 * The pane itself is CSS (index.css, `.glass-card`) because the material is
 * the same on every widget and a material that lives in inline styles is a
 * material that drifts. What lives here is everything the material is NOT:
 * the honesty renderings, the frame badges, and the reordering.
 */

/** Label colour that survives the glass in BOTH modes.
 *
 *  Measured against the effective surface — the fill composited over the
 *  blurred ambient field, not the raw page. In light that lands near #F9FAFC,
 *  where `textMuted` (#636C7A) is 5.0:1 and passes. In dark it lands near
 *  #191F2D, where the same token is 2.8:1 and does NOT, so dark steps up to
 *  `textSecondary` (6.5:1). One function, so no widget has to remember. */
/** Label colour that survives the glass in BOTH modes.
 *
 *  Measured against the effective surface — the fill composited over the
 *  blurred ambient field, not the raw page — and against the field's DARKEST
 *  region, which is where the warm form sits and where the floor is actually
 *  set. Both modes now step up from `textMuted` for the same reason: on light
 *  glass over the brass form #636C7A measures 4.29:1 and #5C6675 measures
 *  4.95:1; on dark glass #5D6B84 measures 3.2:1 and #9AA7BD measures 6.0:1.
 *  One function, so no widget has to remember. */
export const labelInk = (pal: Palette, _dark: boolean) => pal.textSecondary

/* ── Brass and amber, as TEXT, in light mode ─────────────────────────────────
 * The palette's `accent` (#A9762A) and `caution` (#B45309) are tuned to be
 * MARKS — a wall tick, a band rule, a stale badge's border. Against the
 * effective light-glass surface they read 3.6:1 and 4.1:1: both clear the 3:1
 * a graphical object owes the reader, and both miss the 4.5:1 that text does.
 *
 * This board turned brass into headline figures and rail labels, so it needs
 * the same two hues darker. Measured on the worst surface the board produces
 * (glass over the field's warm form): #7E5A16 is 5.1:1 and #8F4206 is 5.8:1.
 *
 * Dark mode keeps both tokens untouched — on dark glass they are already
 * 6.9:1 and 8.9:1, and darkening them there would be a straight regression.
 */
export const STRUCTURE_INK_LIGHT = '#7E5A16'
export const CAUTION_INK_LIGHT = '#8F4206'

/** The text-safe form of any tone. Only `accent` and `caution` are remapped,
 *  and only in light: everything else in the palette already clears 4.5:1 on
 *  the glass. Call this for LETTERS; pass the raw tone to whatever draws the
 *  line, so a brass rule stays brass. */
export const inkOf = (tone: string, pal: Palette, dark: boolean) => {
  if (dark) return tone
  if (tone === pal.accent) return STRUCTURE_INK_LIGHT
  if (tone === pal.caution) return CAUTION_INK_LIGHT
  return tone
}

/* ── Honesty ─────────────────────────────────────────────────────────────────
 * Three renderings, never one. A blank is not allowed to stand for any of
 * them, and none of them is allowed to look like a number.
 *
 *   'none'     we looked and there is nothing there. A finding.
 *   'blind'    we could not look. A failure, and the operator may be able to
 *              act on it, so it is the loud one (caution).
 *   'withheld' we are not showing you. A choice this screen made.
 */
export type AbsenceKind = 'none' | 'blind' | 'withheld'

const ABSENCE_WORD: Record<AbsenceKind, string> = {
  none: 'NOTHING THERE',
  blind: 'COULD NOT CHECK',
  withheld: 'NOT SHOWN HERE',
}

/** The one muted sentence that stands where the instrument would have been.
 *  Distinct per kind, because the whole point of three kinds is that they are
 *  three different situations. */
const ABSENCE_LEAD: Record<AbsenceKind, string> = {
  none: 'looked here, and there is nothing to draw.',
  blind: 'this could not be read.',
  withheld: 'this is not the surface that shows it.',
}

/* ── The quiet form ──────────────────────────────────────────────────────────
 * After hours three panes are absent at once, and the previous rendering gave
 * each of them a caution-coloured heading over caution-coloured body text —
 * an evening review that opened on a wall of amber warnings about a market
 * that was simply closed.
 *
 * The discipline is unchanged: the KIND, a sentence, and the backend's own
 * reason — never a blank, never a zero. What changed is the volume. The pane
 * stays glass and stays quiet; the caution colour survives only as a 6px dot,
 * which is enough to separate "we could not look" from "we looked and found
 * nothing" at a glance and not enough to shout across a still board.
 */
export function Absent({ kind, why, pal, dark }: {
  kind: AbsenceKind
  /** The reason, in the backend's own words wherever it publishes one.
   *  Never invented: an empty reason renders as an admitted empty reason. */
  why: string
  pal: Palette
  dark: boolean
}) {
  const ink = labelInk(pal, dark)
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 7,
      flex: 1, justifyContent: 'center', paddingBottom: 6, minWidth: 0,
    }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
        <span aria-hidden="true" style={{
          width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
          background: kind === 'blind' ? pal.caution : ink,
          opacity: kind === 'blind' ? 1 : 0.5,
        }} />
        <span style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.11em',
          color: ink, whiteSpace: 'nowrap',
        }}>{ABSENCE_WORD[kind]}</span>
      </span>

      <span style={{
        fontSize: 13, lineHeight: 1.4, color: ink,
        fontStyle: kind === 'withheld' ? 'italic' : 'normal',
      }}>{ABSENCE_LEAD[kind]}</span>

      <span style={{ fontSize: 11, lineHeight: 1.5, color: ink, opacity: 0.86 }}>
        {why || 'no reason was published with this absence — treat it as unknown, not as zero'}
      </span>
    </div>
  )
}

/* ── Frame ───────────────────────────────────────────────────────────────────
 * FUT and IDX are different scales separated by the basis (53.4 points on
 * NIFTY as this was written). A board that shows both without saying which is
 * which invites the exact misread data.ts's own comment records: "MAX PAIN
 * 24500 · -34" below price, while the backend's mp_dist said +26 above it.
 */
export type Frame = 'FUT' | 'IDX'

export function FrameBadge({ frame, pal, dark }: { frame: Frame; pal: Palette; dark: boolean }) {
  return (
    <span
      title={frame === 'FUT'
        ? 'FUTURES frame — the tape the chart is drawn on'
        : 'INDEX frame — the chain quotes strikes and spot against the index'}
      style={{
        fontSize: 11, fontWeight: 800, letterSpacing: '0.07em',
        padding: '0 5px', borderRadius: 4, whiteSpace: 'nowrap',
        color: labelInk(pal, dark),
        border: `1px solid ${dark ? 'rgba(255,255,255,0.16)' : 'rgba(20,26,34,0.14)'}`,
      }}
    >{frame}</span>
  )
}

/** A big tabular figure. Every price on this board goes through here, so none
 *  of them can jitter as the tape ticks. */
export function Figure({ v, pal, size = 21, tone }: {
  v: string; pal: Palette; size?: number; tone?: string
}) {
  return (
    <span className="mono" style={{
      fontSize: size, fontWeight: 700, letterSpacing: '-0.01em',
      color: tone ?? pal.textPrimary, lineHeight: 1.15,
    }}>{v}</span>
  )
}

/* ── Instruments ─────────────────────────────────────────────────────────────
 * Every pane on this board answers exactly one question, so every pane gets
 * exactly one hero reading, one drawn graphic, and a short receipt strip. What
 * follows is the vocabulary those three parts are built from. It lives here
 * rather than in each widget because eight panes drawing eight subtly
 * different ladders is how a board stops reading as one instrument.
 */

/** THE reading of a pane. One per pane, and nothing else on the board may
 *  approach its size — the hierarchy IS the design. Tabular by construction so
 *  a ticking figure never reflows the pane under it. */
export function Hero({ v, unit, caption, pal, dark, size = 32, tone, strike }: {
  v: string; pal: Palette; dark: boolean
  unit?: string; caption?: string; size?: number; tone?: string
  /** A figure that must not be trusted, drawn as one. */
  strike?: boolean
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, minWidth: 0 }}>
        <span className="mono" style={{
          fontSize: size, fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1.02,
          color: tone ? inkOf(tone, pal, dark) : pal.textPrimary,
          textDecoration: strike ? 'line-through' : undefined,
        }}>{v}</span>
        {unit && (
          <span style={{
            fontSize: 11, fontWeight: 600, letterSpacing: '0.05em',
            color: labelInk(pal, dark), whiteSpace: 'nowrap',
          }}>{unit}</span>
        )}
      </div>
      {caption && (
        <span style={{ fontSize: 11, lineHeight: 1.4, color: labelInk(pal, dark) }}>{caption}</span>
      )}
    </div>
  )
}

/** A small stated fact. Chips replace the key/value ROWS the panes used to
 *  stack: three rows of label-dots-number is a table, and a table is what an
 *  instrument is supposed to save the operator from reading. */
export function Chip({ children, pal, dark, tone, strong }: {
  children: ReactNode; pal: Palette; dark: boolean; tone?: string; strong?: boolean
}) {
  // The LETTERS take the text-safe ink; the rim and wash keep the raw tone, so
  // a brass chip still reads brass without spending the contrast on its label.
  const ink = tone ? inkOf(tone, pal, dark) : labelInk(pal, dark)
  return (
    <span className="mono" style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, fontWeight: strong ? 700 : 600, letterSpacing: '0.03em',
      padding: '2px 7px', borderRadius: 5, whiteSpace: 'nowrap',
      color: ink,
      border: `1px solid ${tone ? wash(tone, 0.42) : hair(dark, 0.16)}`,
      background: tone ? wash(tone, 0.09) : 'transparent',
    }}>{children}</span>
  )
}

/** The receipt strip: the small print a hero reading is accountable to. Always
 *  last in a pane, always pushed to its floor. */
export function Receipts({ children }: { children: ReactNode }) {
  return (
    <div style={{
      marginTop: 'auto', display: 'flex', alignItems: 'center',
      gap: 6, flexWrap: 'wrap', minWidth: 0, paddingTop: 2,
    }}>{children}</div>
  )
}

/** An rgba wash mixed from any colour a caller already holds. Accepts the
 *  #RRGGBB the palette ships; anything else is returned untouched so a caller
 *  that already passed rgba() does not get mangled. */
export function wash(hex: string, a: number): string {
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return hex
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
}

/** The neutral hairline ink for the active mode. */
export const hair = (dark: boolean, a: number) =>
  `rgba(${dark ? '255,255,255' : '20,26,34'},${a})`

/** Clamp a value into a 0–100 position on a domain. A level outside the drawn
 *  window pins to the edge rather than escaping the graphic — the number
 *  beside it still says where it really is. */
export const pos = (v: number, lo: number, hi: number) =>
  hi > lo ? Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100)) : 50

export interface RailZone {
  from: number; to: number; fill: string
  /** Drawn inside the band when it is tall enough to hold it. */
  label?: string; labelTone?: string
}

export interface RailMark {
  at: number
  label: string
  /** The figure itself, printed at the right edge of the rail. */
  value?: string
  tone?: string
  /** The one mark the pane is about. */
  strong?: boolean
  dashed?: boolean
}

/* ── The vertical rail ───────────────────────────────────────────────────────
 * A price axis drawn to scale, top = high. Dealer gamma and Walls both answer
 * "where is spot relative to these levels", which is a question about DISTANCE,
 * and distance is the one thing a stack of text rows cannot show. Zones shade
 * regions; marks are the levels; the spot marker is the only bright thing.
 */
export function Rail({ lo, hi, zones = [], marks, spot, spotLabel, pal, dark, height = 116 }: {
  lo: number; hi: number
  zones?: RailZone[]
  marks: RailMark[]
  spot?: number | null
  spotLabel?: string
  pal: Palette; dark: boolean; height?: number
}) {
  return (
    <div style={{ position: 'relative', height, minWidth: 0, margin: '2px 0' }}>
      {/* the axis itself */}
      <div aria-hidden="true" style={{
        position: 'absolute', left: 0, right: 0, top: 0, bottom: 0,
        borderRadius: 7, border: `1px solid ${hair(dark, 0.12)}`, overflow: 'hidden',
      }}>
        {zones.map((z, i) => {
          const a = pos(z.from, lo, hi)
          const b = pos(z.to, lo, hi)
          const bottom = Math.min(a, b)
          const h = Math.abs(b - a)
          return (
            <div key={i} style={{
              position: 'absolute', left: 0, right: 0,
              bottom: `${bottom}%`, height: `${h}%`, background: z.fill,
            }} />
          )
        })}
      </div>

      {zones.map((z, i) => {
        if (!z.label) return null
        const mid = (pos(z.from, lo, hi) + pos(z.to, lo, hi)) / 2
        const h = Math.abs(pos(z.to, lo, hi) - pos(z.from, lo, hi))
        if (h < 22) return null
        return (
          <span key={`zl-${i}`} style={{
            position: 'absolute', left: 8, bottom: `${mid}%`, transform: 'translateY(50%)',
            fontSize: 11, fontWeight: 600, letterSpacing: '0.03em',
            color: z.labelTone ? inkOf(z.labelTone, pal, dark) : labelInk(pal, dark),
            whiteSpace: 'nowrap', pointerEvents: 'none',
          }}>{z.label}</span>
        )
      })}

      {marks.map((m) => {
        const p = pos(m.at, lo, hi)
        const tone = m.tone ?? pal.accent
        return (
          <div key={`${m.label}-${m.at}`} title={`${m.label} ${m.value ?? m.at}`} style={{
            position: 'absolute', left: 0, right: 0, bottom: `${p}%`,
            display: 'flex', alignItems: 'center', gap: 6, transform: 'translateY(50%)',
          }}>
            <span style={{
              flex: 1, height: m.strong ? 2 : 1, minWidth: 0,
              background: m.dashed
                ? `repeating-linear-gradient(90deg, ${tone} 0 4px, transparent 4px 8px)`
                : tone,
              opacity: m.strong ? 0.95 : 0.5,
            }} />
            <span className="mono" style={{
              fontSize: 11, fontWeight: m.strong ? 700 : 600,
              color: inkOf(tone, pal, dark), whiteSpace: 'nowrap', paddingRight: 2,
            }}>{m.label}{m.value ? ` ${m.value}` : ''}</span>
          </div>
        )
      })}

      {spot != null && (
        <div title={spotLabel ?? `spot ${spot}`} style={{
          position: 'absolute', left: 0, right: 0, bottom: `${pos(spot, lo, hi)}%`,
          display: 'flex', alignItems: 'center', gap: 5, transform: 'translateY(50%)',
        }}>
          <span style={{
            width: 9, height: 9, borderRadius: '50%', flexShrink: 0, marginLeft: -4,
            background: pal.textPrimary,
            boxShadow: `0 0 0 3px ${wash(pal.ink === '#FFFFFF' ? '#000000' : '#FFFFFF', 0.35)}`,
          }} />
          <span style={{ flex: 1, height: 2, background: pal.textPrimary, opacity: 0.85, minWidth: 0 }} />
          <span className="mono" style={{
            fontSize: 11, fontWeight: 700, color: pal.textPrimary, whiteSpace: 'nowrap', paddingRight: 2,
          }}>{spotLabel ?? 'spot'}</span>
        </div>
      )}
    </div>
  )
}

export interface MeterTick { at: number; label?: string; tone?: string; strong?: boolean }

/* ── The horizontal meter ────────────────────────────────────────────────────
 * The same idea laid flat, for the two panes whose question is "how far, and
 * which way": the machine's price→d3 gap, and the pin's spot→max-pain offset.
 * The TRAVEL between the marker and the target is drawn as a filled span, so
 * "18 points away" has a length and not just a value.
 */
export function Meter({ lo, hi, ticks, marker, markerLabel, span, spanTone, pal, dark, height = 40 }: {
  lo: number; hi: number
  ticks: MeterTick[]
  marker: number
  markerLabel?: string
  /** The distance being measured, drawn as a bar between two values. */
  span?: [number, number]
  spanTone?: string
  pal: Palette; dark: boolean; height?: number
}) {
  const mp = pos(marker, lo, hi)
  return (
    <div style={{ position: 'relative', height, minWidth: 0, marginTop: 2 }}>
      {/* the track */}
      <div aria-hidden="true" style={{
        position: 'absolute', left: 0, right: 0, top: height / 2 - 5, height: 10,
        borderRadius: 5, background: hair(dark, dark ? 0.10 : 0.07),
        border: `1px solid ${hair(dark, 0.10)}`, overflow: 'hidden',
      }}>
        {span && (
          <div style={{
            position: 'absolute', top: 0, bottom: 0,
            left: `${Math.min(pos(span[0], lo, hi), pos(span[1], lo, hi))}%`,
            width: `${Math.abs(pos(span[1], lo, hi) - pos(span[0], lo, hi))}%`,
            background: wash(spanTone ?? pal.accent, 0.34),
          }} />
        )}
      </div>

      {ticks.map((t) => {
        const p = pos(t.at, lo, hi)
        const tone = t.tone ?? pal.accent
        return (
          <span key={`${t.label}-${t.at}`} title={t.label} style={{
            position: 'absolute', left: `${p}%`, top: height / 2 - 9,
            width: t.strong ? 2 : 1, height: 18, marginLeft: -0.5,
            background: tone, opacity: t.strong ? 0.95 : 0.45,
          }} />
        )
      })}

      {ticks.filter((t) => t.label).map((t) => {
        const p = pos(t.at, lo, hi)
        return (
          <span key={`lbl-${t.label}-${t.at}`} style={{
            position: 'absolute', left: `${p}%`, bottom: 0,
            transform: p > 88 ? 'translateX(-100%)' : p < 12 ? 'none' : 'translateX(-50%)',
            fontSize: 11, fontWeight: t.strong ? 700 : 500, whiteSpace: 'nowrap',
            color: t.strong ? inkOf(t.tone ?? pal.accent, pal, dark) : labelInk(pal, dark),
          }}>{t.label}</span>
        )
      })}

      {/* the marker — the only bright thing on the meter */}
      <span title={markerLabel} style={{
        position: 'absolute', left: `${mp}%`, top: height / 2 - 11,
        width: 3, height: 22, marginLeft: -1.5, borderRadius: 2,
        background: pal.textPrimary,
      }} />
      {markerLabel && (
        <span className="mono" style={{
          position: 'absolute', left: `${mp}%`, top: 0,
          transform: mp > 84 ? 'translateX(-100%)' : mp < 16 ? 'none' : 'translateX(-50%)',
          fontSize: 11, fontWeight: 700, color: pal.textPrimary, whiteSpace: 'nowrap',
        }}>{markerLabel}</span>
      )}
    </div>
  )
}

/* ── The pane ───────────────────────────────────────────────────────────── */

/* ── Lean ────────────────────────────────────────────────────────────────────
 * The direction a pane's own data point is leaning, as a tint on the glass.
 *
 * THE RULE, and it is the whole rule: a lean may only ever be READ from a
 * direction this app already states somewhere — a backend field, or a mapping
 * that already exists in data.ts and paints green/red on another surface. No
 * pane is allowed to acquire a direction here that it did not have before,
 * because a tint is an opinion and this board does not get to have new ones.
 * Panes with no such source stay null, and null is not a verdict: it is the
 * ordinary glass this board was already made of.
 *
 * `null` is also what an ABSENT or STALE pane gets. "We could not check" must
 * never come out tinted — not even the deliberate neutral-white reading, which
 * would be the board claiming balance it never measured. See GlassCard, which
 * drops the tint whenever a stale note is present.
 */
export type Lean = 'bull' | 'bear' | null

export interface GlassCardProps {
  id: string
  /** What the widget is. */
  label: string
  /** Direction this pane's data point leans, or null for none. Read only —
   *  see the Lean note above for where each pane's source lives. */
  lean?: Lean
  /** Which tab clicking it opens. Shown, so the launcher is not a guess. */
  goesTo: string
  onOpen: () => void
  /** Grid columns this pane occupies. */
  span?: number
  minHeight?: number
  /** Quietly marks a pane whose numbers came from a stale chain snapshot. */
  staleNote?: string
  lifted: boolean
  over: boolean
  onGripDown: (e: ReactPointerEvent) => void
  /** Alt+←/→ while the pane has focus. */
  onNudge: (delta: number) => void
  pal: Palette
  dark: boolean
  children: ReactNode
}

export function GlassCard({
  id, label, goesTo, onOpen, span = 1, minHeight = 146, staleNote, lean = null,
  lifted, over, onGripDown, onNudge, pal, dark, children,
}: GlassCardProps) {
  // A stale snapshot cannot carry a lean. The figures are from a moment that
  // has passed, and tinting them would let a 208-minute-old chain state a
  // direction about now — which is exactly the misread the STALE badge exists
  // to prevent, restated in colour where it is harder to argue with.
  const tint = staleNote ? null : lean
  const cls = 'glass-card'
    + (tint ? ` lean-${tint}` : '')
    + (lifted ? ' is-lift' : '') + (over ? ' is-over' : '')
  return (
    <div
      data-glass-id={id}
      className={cls}
      role="button"
      tabIndex={0}
      // The tint is a glance aid, never the only carrier of the fact: a hue
      // nobody can see is a fact nobody gets. Screen readers hear it, and the
      // pane's own copy still states the side in words.
      aria-label={`${label}${tint ? `, leaning ${tint === 'bull' ? 'bullish' : 'bearish'}` : ''}`
        + ` — open the ${goesTo} tab. Alt with left or right arrow moves this panel.`}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
          e.preventDefault()
          onNudge(e.key === 'ArrowLeft' ? -1 : 1)
          return
        }
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen() }
      }}
      style={{
        gridColumn: `span ${span}`,
        minHeight,
        padding: '13px 15px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 9,
        cursor: 'pointer',
        // Above .glass-field, which sits at z-index 0 and is what the blur
        // actually bends. Without a stacking order the field paints over the
        // panes and the whole board goes flat.
        zIndex: 1,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, minHeight: 17 }}>
        <span style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.07em',
          textTransform: 'uppercase', color: labelInk(pal, dark), whiteSpace: 'nowrap',
        }}>{label}</span>

        {/* Letters take the text-safe amber, the rim keeps the raw token — so
            the badge still reads as the same caution colour it does everywhere
            else in the app without spending its contrast on the letters. */}
        {staleNote && (
          <span title={staleNote} style={{
            fontSize: 11, fontWeight: 800, letterSpacing: '0.05em',
            padding: '0 5px', borderRadius: 4, color: inkOf(pal.caution, pal, dark),
            border: `1px solid ${wash(pal.caution, 0.55)}`, whiteSpace: 'nowrap',
          }}>STALE</span>
        )}

        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontSize: 11, fontWeight: 600,
            color: labelInk(pal, dark), opacity: 0.8, whiteSpace: 'nowrap',
          }}>{goesTo} →</span>
          {/* Pointer-only, and aria-hidden: the keyboard route to the same
              action is Alt+arrow on the pane itself, which is already in the
              pane's own label. A second tab stop that only works with a mouse
              would be a promise the keyboard cannot keep. */}
          <span
            className="glass-grip"
            aria-hidden="true"
            title="Drag to rearrange"
            onPointerDown={onGripDown}
            onClick={(e) => e.stopPropagation()}
            style={{ fontSize: 15, color: labelInk(pal, dark), letterSpacing: '-1px' }}
          >⠿</span>
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, flex: 1, minWidth: 0 }}>
        {children}
      </div>
    </div>
  )
}

/* ── Order ───────────────────────────────────────────────────────────────────
 * Persisted in localStorage. A corrupt value must never throw and must never
 * leave the board empty: anything unreadable falls back to the default order,
 * and a stored order that is missing panes (a new widget shipped) or naming
 * panes that no longer exist (one was cut) is reconciled rather than rejected
 * — otherwise the first release after this one silently resets everyone.
 */
const KEY = 'tape.glass.order'

function readStored(): string[] | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const v: unknown = JSON.parse(raw)
    if (!Array.isArray(v)) return null
    const out = v.filter((x): x is string => typeof x === 'string')
    return out.length ? out : null
  } catch {
    return null
  }
}

function reconcile(stored: string[] | null, defaults: string[]): string[] {
  if (!stored) return defaults
  const seen = new Set<string>()
  const kept: string[] = []
  for (const id of stored) {
    if (defaults.includes(id) && !seen.has(id)) { seen.add(id); kept.push(id) }
  }
  for (const id of defaults) if (!seen.has(id)) kept.push(id)
  return kept
}

export function useGlassOrder(defaults: string[]) {
  const [order, setOrder] = useState<string[]>(() => reconcile(readStored(), defaults))

  const persist = useCallback((next: string[]) => {
    setOrder(next)
    try { localStorage.setItem(KEY, JSON.stringify(next)) } catch { /* private mode — the board still works, it just won't remember */ }
  }, [])

  /** Move `id` into `target`'s slot, shifting the rest. */
  const move = useCallback((id: string, target: string) => {
    setOrder((prev) => {
      const from = prev.indexOf(id)
      const to = prev.indexOf(target)
      if (from < 0 || to < 0 || from === to) return prev
      const next = prev.slice()
      next.splice(from, 1)
      next.splice(to, 0, id)
      try { localStorage.setItem(KEY, JSON.stringify(next)) } catch { /* see persist */ }
      return next
    })
  }, [])

  const nudge = useCallback((id: string, delta: number) => {
    setOrder((prev) => {
      const from = prev.indexOf(id)
      const to = from + delta
      if (from < 0 || to < 0 || to >= prev.length) return prev
      const next = prev.slice()
      next.splice(from, 1)
      next.splice(to, 0, id)
      try { localStorage.setItem(KEY, JSON.stringify(next)) } catch { /* see persist */ }
      return next
    })
  }, [])

  return { order, move, nudge, persist }
}

/** Pointer drag, started from a grip and resolved by whatever pane the pointer
 *  is over on release. Grip-only on purpose: the whole pane is a launcher, so
 *  "drag anywhere" would have every rearrange start as a mis-click. */
export function useGlassDrag(move: (id: string, target: string) => void) {
  const [drag, setDrag] = useState<{ id: string; over: string | null } | null>(null)
  const moveRef = useRef(move)
  moveRef.current = move

  const start = useCallback((id: string) => (e: ReactPointerEvent) => {
    // Left button / touch / pen only, and never let the press become a text
    // selection or a click on the pane underneath.
    if (e.button !== 0) return
    e.preventDefault()
    e.stopPropagation()
    setDrag({ id, over: null })
  }, [])

  useEffect(() => {
    if (!drag) return
    const onMove = (e: PointerEvent) => {
      const el = document.elementFromPoint(e.clientX, e.clientY)
      const card = el ? (el.closest('[data-glass-id]') as HTMLElement | null) : null
      const over = card?.dataset.glassId ?? null
      setDrag((d) => (!d || d.over === over ? d : { ...d, over }))
    }
    const onUp = () => {
      setDrag((d) => {
        if (d && d.over && d.over !== d.id) moveRef.current(d.id, d.over)
        return null
      })
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointercancel', onUp)
    }
  }, [drag?.id])

  return { drag, start }
}
