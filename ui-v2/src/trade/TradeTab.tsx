import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import ContractChart from './ContractChart'
import Ribbon from './Ribbon'
import { buildNarration } from './narration'
import { dayPrecision } from './indicators'
import { buildZones } from './zones'
import { palette, MONO, useMode } from '../theme'
import type { TapeBar, MapLevel, IndexKey, EventItem, Structure } from '../data'

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  events: EventItem[]
  cursor: number | null
  stale: boolean
  loading: boolean
  /** True when the active index's option chain snapshot is past
   *  CHAIN_STALE_S (data.ts). MAX PAIN and GEX FLIP in `levels` are
   *  chain-derived, so they still draw — hiding real structure would be its
   *  own lie — but must be labelled as not-current. */
  chainStale: boolean
  /** The chain snapshot's own IST clock ("HH:MM:SS"), for the stale-chain
   *  disclosure line below. Empty when unknown. */
  chainTs: string
  /** FOCUS mode (App.tsx-owned, persisted under `tape.focus`): while on and
   *  this tab is active, App hides the glance bar + ANSWER band so the chart
   *  gets that height. The index switcher normally lives in the glance bar,
   *  so this tab surfaces a small substitute while it's hidden. */
  focus: boolean
  onFocusToggle: () => void
  onIndexChange: (k: IndexKey) => void
  /** The backend's SMC structure layer for this day, or null when it cannot be
   *  drawn honestly. Null is DISCLOSED below, never silently absent. */
  structures: Structure[] | null
  /** Why `structures` is null, in data.ts's own words. Empty when it isn't. */
  structuresWhy: string
}

const INDEX_KEYS: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']

function Stat({ pal, label, value, color, title }: {
  pal: ReturnType<typeof palette>; label: string; value: string; color?: string; title?: string
}) {
  return (
    <div title={title} style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
      <span style={{
        fontSize: 9.5, letterSpacing: '0.07em', textTransform: 'uppercase',
        color: pal.textMuted, whiteSpace: 'nowrap',
      }}>{label}</span>
      <span style={{
        fontFamily: MONO, fontSize: 13, fontWeight: 600,
        color: color ?? pal.textPrimary, whiteSpace: 'nowrap',
      }}>{value}</span>
    </div>
  )
}

// Mirrors zones.ts's own VERDICT_CLS (Task 1 mapping) — kept as a local copy
// rather than importing, since this panel colours a single bar's live
// `ctx.verdict` directly and has no zone/run to borrow a `cls` from. Never
// used to alter what's displayed, only which palette family paints it.
const VERDICT_CLS: Record<string, 'stand' | 'watch' | 'go'> = {
  GO: 'go', READY: 'watch', WAIT: 'watch', CAUTION: 'watch',
  'STAND ASIDE': 'stand', SPENT: 'stand',
}

function verdictColor(pal: ReturnType<typeof palette>, verdict: string): string {
  const cls = VERDICT_CLS[verdict]
  if (cls === 'go') return pal.bull
  if (cls === 'stand') return pal.bear
  if (cls === 'watch') return pal.caution
  return pal.textPrimary // an unrecognised verdict string: neutral, not a guessed direction
}

// SETUP's status chip: LOADING is still forming (outline, caution), ARMED is
// live (filled, the setup's own direction colour), EXPIRED/INVALIDATED are
// dead (struck through, faint). Any other status string still renders —
// plain outline, no colour claim — rather than being silently dropped.
function StatusChip({ pal, status, dirColor }: {
  pal: ReturnType<typeof palette>; status: string; dirColor: string
}) {
  const dead = status === 'EXPIRED' || status === 'INVALIDATED'
  const armed = status === 'ARMED'
  const loading = status === 'LOADING'
  return (
    <span style={{
      fontSize: 9.5, fontWeight: 700, letterSpacing: '0.05em', padding: '1px 6px',
      borderRadius: 3, fontFamily: MONO,
      textDecoration: dead ? 'line-through' : 'none',
      color: armed ? pal.card : dead ? pal.textMuted : loading ? pal.caution : pal.textSecondary,
      backgroundColor: armed ? dirColor : 'transparent',
      border: armed ? 'none' : `1px solid ${dead ? pal.border : loading ? pal.caution : pal.border}`,
    }}>{status}</span>
  )
}

/**
 * The ENGINE READ panel — the operator's requested "suggested trade" slot,
 * built the only honest way it can be: it surfaces the ENGINE's own existing
 * read with its receipts, quoted verbatim, and never invents or strengthens
 * a recommendation of its own. Reads `bar` — always `bars[at]`, the same
 * cursor-clamped bar the stat strip above uses — and nothing else, so a bar
 * with no ctx never borrows a neighbour's read.
 */
function EngineReadPanel({ pal, bar }: { pal: ReturnType<typeof palette>; bar: TapeBar }) {
  const ctx = bar.ctx
  const setup = bar.setup
  const label: CSSProperties = {
    fontSize: 9.5, letterSpacing: '0.07em', textTransform: 'uppercase',
    color: pal.textMuted, fontWeight: 700,
  }
  return (
    <div style={{
      padding: '12px 16px', borderRadius: 6, backgroundColor: pal.card,
      border: `1px solid ${pal.border}`, display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={label}>ENGINE READ</div>

      {!ctx ? (
        <div style={{ fontSize: 11, color: pal.textMuted }}>
          engine context unavailable for this bar
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          {/* VERDICT */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 190, flex: '1 1 190px' }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: verdictColor(pal, ctx.verdict) }}>
              {ctx.verdict}
            </span>
            <span style={{ fontSize: 11, color: pal.textSecondary }}>{ctx.vwhy}</span>
            <span style={{ fontFamily: MONO, fontSize: 10.5, color: pal.textMuted }}>{ctx.line}</span>
            <span style={{ fontSize: 10.5, color: pal.textMuted }}>{ctx.breadth}</span>
            {ctx.flips.length > 0 && (
              <div style={{ display: 'flex', gap: 6, fontSize: 10, color: pal.textMuted, marginTop: 2 }}>
                <span style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>Δ15m</span>
                <span style={{ fontFamily: MONO }}>{ctx.flips.join(' · ')}</span>
              </div>
            )}
          </div>

          {/* SETUP */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 190, flex: '1 1 190px' }}>
            <span style={label}>SETUP</span>
            {setup ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <span style={{
                    fontSize: 12, fontWeight: 700,
                    color: setup.dir === 'UP' ? pal.bull : pal.bear,
                  }}>
                    {setup.dir === 'UP' ? '▲' : '▼'} {setup.kind}
                  </span>
                  <StatusChip pal={pal} status={setup.status}
                              dirColor={setup.dir === 'UP' ? pal.bull : pal.bear} />
                </div>
                <span style={{ fontSize: 11, color: pal.textSecondary }}>
                  {setup.level_name} @ {setup.level_px.toFixed(1)}
                </span>
                <span style={{ fontSize: 11, color: pal.textMuted }}>
                  invalid past {setup.ref.toFixed(1)}
                </span>
                <span style={{ fontFamily: MONO, fontSize: 10.5, color: pal.textMuted }}>
                  intensity {setup.intensity.toFixed(2)} · comp {setup.comp.toFixed(2)}
                </span>
              </>
            ) : (
              <span style={{ fontSize: 11, color: pal.textMuted }}>
                no setup armed — engine has nothing loaded here
              </span>
            )}
          </div>

          {/* PLAYS */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 220, flex: '2 1 220px' }}>
            <span style={label}>PLAYS</span>
            {ctx.plays.length ? ctx.plays.map((p, i) => (
              <div key={i} style={{
                fontFamily: MONO, fontSize: 11, color: pal.textPrimary,
                display: 'flex', gap: 7, lineHeight: 1.4,
              }}>
                <span style={{ color: pal.accent }}>▪</span><span>{p}</span>
              </div>
            )) : (
              <span style={{ fontSize: 11, color: pal.textMuted }}>
                no conditional plays on this bar
              </span>
            )}
          </div>

          {/* FLOOR / CAP — omitted entirely when both null */}
          {(ctx.floor || ctx.cap) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 130 }}>
              <span style={label}>FLOOR / CAP</span>
              {ctx.floor && (
                <span style={{
                  fontFamily: MONO, fontSize: 11, fontWeight: 600, color: pal.accent,
                  border: `1px solid ${pal.accent}`, borderRadius: 3, padding: '1px 7px', width: 'fit-content',
                }}>FLOOR {ctx.floor[0]} {ctx.floor[1].toFixed(1)}</span>
              )}
              {ctx.cap && (
                <span style={{
                  fontFamily: MONO, fontSize: 11, fontWeight: 600, color: pal.accent,
                  border: `1px solid ${pal.accent}`, borderRadius: 3, padding: '1px 7px', width: 'fit-content',
                }}>CAP {ctx.cap[0]} {ctx.cap[1].toFixed(1)}</span>
              )}
            </div>
          )}
        </div>
      )}

      <div style={{ fontSize: 10, color: pal.textMuted, borderTop: `1px solid ${pal.border}`, paddingTop: 8 }}>
        the engine's own read, quoted with its receipts — descriptive, not advice · signals only, orders never
      </div>
    </div>
  )
}

export default function TradeTab({
  index, day, bars, levels, events, cursor, stale, loading, chainStale, chainTs,
  focus, onFocusToggle, onIndexChange, structures, structuresWhy,
}: Props) {
  // Persisted per Task 1: defaults to light — the operator reads charts in
  // Kite on the light theme and reported the dark build unreadable.
  const [mode, setMode] = useMode()
  const pal = palette(mode)

  // SMC structure layer, default ON: the operator trades ICT/SMC, so the layer
  // is the point of the tab, not a garnish. Persisted like `tape.mode` and
  // `tape.focus`; only the literal string 'off' turns it off, so a corrupt or
  // absent value fails towards showing the operator more, never less.
  const [smc, setSmc] = useState<boolean>(() => localStorage.getItem('tape.smc') !== 'off')
  const toggleSmc = () => {
    const next = !smc
    localStorage.setItem('tape.smc', next ? 'on' : 'off')
    setSmc(next)
  }

  // What the SMC toggle's tooltip reports: SWING_H/SWING_L are never drawn
  // (LevelsOverlay.ts's drawStructures says why — each is already the
  // endpoint of a BOS, an EQH/EQL pool or an OB), so counting them alongside
  // the drawn kinds would tell the operator "N structures" when only a
  // fraction of N puts anything on the chart. Split into what's actually
  // rendered and what's tracked but not shown.
  const structCounts = useMemo(() => {
    if (!structures) return null
    let drawn = 0, swings = 0
    for (const s of structures) {
      if (s.kind === 'SWING_H' || s.kind === 'SWING_L') swings++
      else drawn++
    }
    return { drawn, swings }
  }, [structures])

  // Presentation only (spec §6 Phase 2): joins the payload's own event stream
  // to bars, tiers and formats — nothing computed about the market.
  const narrs = useMemo(() => buildNarration(bars, events), [bars, events])

  // Causality (binding, Task 2 review): a zone's label/why embed the run's
  // FULL length, so while the replay cursor is set, buildZones must never
  // see bars past it — otherwise a band would announce how long a regime
  // persists beyond where the operator has scrubbed to. Slice first, group
  // second; buildZones itself has no notion of a cursor.
  const zones = useMemo(() => {
    const sliced = cursor == null
      ? bars
      : bars.slice(0, Math.max(0, Math.min(cursor, bars.length - 1)) + 1)
    return buildZones(sliced)
  }, [bars, cursor])

  const [hover, setHover] = useState<number | null>(null)
  // Hovering must never reveal a bar the replay cursor is hiding — the
  // causality rule holds regardless of whether hover came from the chart's
  // own mousemove or from the ribbon underneath it.
  const handleHover = (i: number | null) => {
    if (i == null || !bars.length) { setHover(null); return }
    const maxIdx = bars.length - 1
    let idx = Math.max(0, Math.min(i, maxIdx))
    if (cursor != null) idx = Math.min(idx, Math.max(0, Math.min(cursor, maxIdx)))
    setHover(idx)
  }

  // The offset above this tab is content-dependent (the ANSWER band wraps
  // differently per index, and banners appear conditionally), so a fixed
  // calc(100vh - Npx) is wrong in some states and pushes the chart below the
  // fold. Measure the real distance to the viewport bottom instead.
  const rootRef = useRef<HTMLDivElement>(null)
  const [availH, setAvailH] = useState<number | null>(null)
  // Size the column to the space actually available. Strictly event-driven:
  // this effect MUST keep its dependency array, and the observer MUST watch
  // the parent rather than our own box. A dep-less layout effect that sets
  // state here does not converge, because our container is `flex:1` inside a
  // `min-height:100vh` column, so growing our height moves our own top and
  // the value oscillates. Layout effects run before paint, so that loop
  // freezes the page outright.
  useLayoutEffect(() => {
    const el = rootRef.current
    if (!el) return
    const measure = () => {
      const node = rootRef.current
      if (!node) return
      const next = Math.max(320, window.innerHeight - node.getBoundingClientRect().top - 12)
      setAvailH((prev) => (prev != null && Math.abs(prev - next) < 2 ? prev : next))
    }
    measure()
    window.addEventListener('resize', measure)
    const parent = el.parentElement
    const ro = parent ? new ResizeObserver(measure) : null
    if (parent && ro) ro.observe(parent)
    return () => {
      window.removeEventListener('resize', measure)
      ro?.disconnect()
    }
  }, [index, bars.length === 0])

  // Honesty rule 1: no tape = say so at full width, and chart nothing. A
  // fallback must never occupy the space where live data goes. But before the
  // first poll resolves, a healthy index also has zero bars — that transient
  // state must read as "loading", not "no session", or a fine index looks dead.
  if (!bars.length) {
    if (loading) {
      return (
        <div style={{ padding: 16, backgroundColor: pal.bg }}>
          <div style={{
            padding: '14px 18px', borderRadius: 6,
            backgroundColor: pal.card,
            border: `1px solid ${pal.border}`, color: pal.textMuted,
            fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
          }}>
            Loading {index} tape…
          </div>
        </div>
      )
    }
    return (
      <div style={{ padding: 16, backgroundColor: pal.bg }}>
        <div style={{
          padding: '14px 18px', borderRadius: 6,
          backgroundColor: pal.card,
          border: `1px solid ${pal.caution}`, color: pal.caution,
          fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
        }}>
          NO {index} TAPE — the backend has no session for this index, so there is
          nothing to chart. No candles are drawn rather than placeholder ones.
        </div>
      </div>
    )
  }

  // Clamp both ends: a negative cursor would index bars[-1] === undefined and
  // throw on the first field read.
  const at = cursor == null
    ? bars.length - 1
    : Math.max(0, Math.min(cursor, bars.length - 1))
  const b = bars[at]                       // causal: the shown bar, not the newest
  const live = cursor == null
  const prec = dayPrecision(day)
  const dir = b.c >= b.o ? pal.bull : pal.bear // the bar's own direction, same as its candle
  const modeLabel = stale ? 'STALE' : live ? 'LIVE' : 'REPLAY'
  const modeColor = stale || !live ? pal.caution : pal.bull

  return (
    <div ref={rootRef} style={{
      display: 'flex', flexDirection: 'column',
      height: availH ?? 420, padding: 16, gap: 8,
      backgroundColor: pal.bg,
    }}>
      {/* Stat strip — one compact row (Task 6's "breathing room"): 11px
          labels, 13px values, the Light/Dark toggle beside the mode pill. */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap',
        padding: '7px 14px', backgroundColor: pal.card,
        border: `1px solid ${pal.border}`, borderRadius: 6,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 9.5, letterSpacing: '0.07em', color: pal.textMuted }}>
            CONTRACT
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: pal.textPrimary, letterSpacing: '0.02em' }}>
            {index} FUT
          </span>
        </div>
        <Stat pal={pal} label="Session" value={day || '—'}
              color={prec === 'exact' ? pal.textPrimary : pal.caution}
              title={prec === 'exact' ? undefined
                : prec === 'no-year'
                  ? 'This session key carries no year, so the chart’s date axis infers the current one. The month, day and intraday clock are real.'
                  : 'This session key carries no parseable date, so the chart’s date axis is synthetic. The intraday clock is real.'} />
        <Stat pal={pal} label="Bar" value={b.t} />
        <Stat pal={pal} label="Close" value={b.c.toFixed(1)} color={dir} />
        <Stat pal={pal} label="Open interest" value={`${(b.oi / 1e6).toFixed(2)}M`} />
        <Stat pal={pal} label="Volume" value={b.v.toLocaleString('en-IN')} />
        <Stat pal={pal} label="Bars" value={`${at + 1} / ${bars.length}`} />

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', border: `1px solid ${pal.border}`, borderRadius: 4, overflow: 'hidden' }}>
            {(['light', 'dark'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                  padding: '3px 9px', cursor: 'pointer', border: 'none',
                  backgroundColor: mode === m ? pal.accent : 'transparent',
                  color: mode === m ? pal.card : pal.textMuted,
                }}
              >{m === 'light' ? 'LIGHT' : 'DARK'}</button>
            ))}
          </div>

          {/* FOCUS: hides the glance bar + ANSWER band (App.tsx-owned state)
              while this tab is active, so the chart reclaims that height.
              Styled like the LIGHT/DARK toggle, palette tokens only. */}
          <button
            onClick={onFocusToggle}
            title="Hide the glance bar and ANSWER band while on this tab, so the chart gets more height"
            style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
              padding: '3px 9px', cursor: 'pointer',
              border: `1px solid ${pal.border}`, borderRadius: 4,
              backgroundColor: focus ? pal.accent : 'transparent',
              color: focus ? pal.card : pal.textMuted,
            }}
          >FOCUS</button>

          {/* SMC: the structure layer (FVG / OB / BOS / CHoCH / EQH / EQL) on
              the chart. Same styling family as FOCUS and LIGHT/DARK. When the
              layer is unavailable the button still toggles — it is the
              operator's preference, not a status light; the disclosure line
              below is what reports availability. */}
          <button
            onClick={toggleSmc}
            title={structCounts
              ? `Show the backend's SMC structure layer (${structCounts.drawn} structures drawn · ${structCounts.swings} swings tracked)`
              : 'Show the SMC structure layer — unavailable for this session, see the note below'}
            style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
              padding: '3px 9px', cursor: 'pointer',
              border: `1px solid ${pal.border}`, borderRadius: 4,
              backgroundColor: smc ? pal.accent : 'transparent',
              color: smc ? pal.card : pal.textMuted,
            }}
          >SMC</button>

          {/* With the glance bar hidden, its index switcher goes with it —
              this is just that switcher, not a duplicate of the whole bar. */}
          {focus && (
            <div style={{ display: 'flex', gap: 4 }}>
              {INDEX_KEYS.map((k) => (
                <button
                  key={k}
                  onClick={() => onIndexChange(k)}
                  style={{
                    fontSize: 10, fontWeight: 700, letterSpacing: '0.04em',
                    padding: '3px 8px', cursor: 'pointer', borderRadius: 4,
                    border: `1px solid ${k === index ? pal.accent : pal.border}`,
                    backgroundColor: 'transparent',
                    color: k === index ? pal.accent : pal.textMuted,
                  }}
                >{k}</button>
              ))}
            </div>
          )}

          {/* Amber for REPLAY, matching the no-tape banner and the date
              disclosure: in this tab amber means "not the data you'd assume".
              Brass is reserved for structure, so it must not mean "mode".
              STALE is the same amber — a dead index's last-good tape is
              exactly as "not what you'd assume" as a replay frame. */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              backgroundColor: modeColor,
            }} />
            <span style={{
              fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em',
              color: modeColor,
            }}>{modeLabel}</span>
          </div>
        </div>
      </div>

      {stale && (
        <div style={{ fontSize: 11, color: pal.caution, paddingLeft: 2 }}>
          This index stopped updating — the chart below is the last tape received, not live. Its final bar is {b.t}.
        </div>
      )}

      {prec !== 'exact' && (
        <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
          {prec === 'no-year'
            ? 'Session key carries no year — the date axis infers the current one; month, day and intraday times are real.'
            : 'Session key carries no parseable date — the date axis is synthetic; intraday times are real.'}
        </div>
      )}

      {chainStale && (
        <div style={{ fontSize: 11, color: pal.caution, paddingLeft: 2 }}>
          Chain snapshot is stale — MAX PAIN and GEX FLIP below are from {chainTs || 'an earlier time'}, not now.
        </div>
      )}

      {/* The layer is missing, so say so rather than let an empty chart read
          as "no structure found". Faint, one line, and only when SMC is on —
          with the toggle off the operator already knows why nothing is drawn.
          Gated on `day` too: an empty day is the tab's own initial-load state
          (the bail above already covers it with a loading/no-tape message),
          not a real session whose structures came back absent or misaligned —
          those two must never share this disclosure line. */}
      {smc && day && !structures && (
        <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
          Structure layer unavailable{structuresWhy ? ` — ${structuresWhy}` : ''}. No boxes are drawn
          rather than boxes that might sit on the wrong bars.
        </div>
      )}

      <div style={{
        flex: 1, minHeight: 420, borderRadius: 6, overflow: 'hidden',
        border: `1px solid ${pal.border}`, backgroundColor: pal.card,
      }}>
        <ContractChart
          index={index} day={day} bars={bars} levels={levels} cursor={cursor}
          mode={mode} hover={hover} onHover={handleHover} narrs={narrs} zones={zones}
          structures={structures} smc={smc}
        />
      </div>

      {/* The day's shape at a glance, dimmed past the replay cursor. */}
      <Ribbon mode={mode} narrs={narrs} cursor={cursor} hover={hover} onHover={handleHover} />

      <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
        VWAP & σ bands · levels · OI{smc && structures ? ' · SMC structure (brass)' : ''}
      </div>

      {/* ENGINE READ — full width, directly below the ribbon+legend. Reads
          bars[at] only (the SAME cursor-clamped bar `b` the stat strip above
          uses), so replay scrubs it causally too. */}
      <EngineReadPanel pal={pal} bar={b} />
    </div>
  )
}
