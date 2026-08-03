import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import ContractChart from './ContractChart'
import Ribbon from './Ribbon'
import LegChart from './LegChart'
import ZoneRead, { crl } from './ZoneRead'
import { buildNarration } from './narration'
import { dayPrecision } from './indicators'
import { buildZones } from './zones'
// The overlay owns the cap; the legend below only reports it, so the number the
// operator reads can never drift from the number actually drawn.
import { STRUCT_ZONE_LIMIT } from './LevelsOverlay'
import { palette, MONO, useMode } from '../theme'
import type { TapeBar, MapLevel, IndexKey, EventItem, RotationSignal, Structure, Chain, FlowRow, OptPivots } from '../data'

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  events: EventItem[]
  cursor: number | null
  /** The live chain snapshot for this index — feeds the ZONE READ's books and
   *  GEX groups. Live-only (no per-strike history), so during replay the
   *  panel labels those groups as not cursor-aligned rather than hiding them. */
  chain: Chain
  /** The engine's tracked ATM strike (TapeView.strike) — names which strike
   *  the ce/pe leg panes belong to. Rolling; the panes disclose that. */
  strike: number | null
  /** Prior-session floor pivots per leg + the legs' expiry (nearest — the
   *  contract the operator trades). Null when the backend predates them. */
  optPivots: OptPivots | null
  optExpiry: string | null
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
  /** The backend's index band-rotation signals for this day, 1:1 with `bars`,
   *  or null when they cannot be drawn honestly. Null is DISCLOSED below. */
  rotation: (RotationSignal | null)[] | null
  /** Why `rotation` is null, in data.ts's own words. Empty when it isn't. */
  rotationWhy: string
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
      <div style={label}>WHAT THE ENGINE SAYS TO WATCH</div>

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
                    // Engine invariant (engine.py:440-442): a conflicted spring's
                    // `dir` must never be treated as a directional vote, so the
                    // arrow (the vote) is dropped and the kind goes neutral —
                    // only an unconflicted setup borrows bull/bear.
                    color: setup.conflict ? pal.textSecondary : (setup.dir === 'UP' ? pal.bull : pal.bear),
                  }}>
                    {setup.conflict ? '' : `${setup.dir === 'UP' ? '▲' : '▼'} `}{setup.kind}
                  </span>
                  <StatusChip pal={pal} status={setup.status}
                              dirColor={setup.conflict ? pal.textSecondary
                                : (setup.dir === 'UP' ? pal.bull : pal.bear)} />
                  {/* Age: t0 is the setup's birth time, verbatim. Without this a
                      40-minute-old LOADING setup and one born this bar look
                      identical. */}
                  <span style={{ fontFamily: MONO, fontSize: 9.5, color: pal.textMuted }}>
                    since {setup.t0}
                  </span>
                </div>
                {setup.conflict && (
                  <span style={{ fontSize: 11, color: pal.caution }}>
                    direction unresolved — books rotate against this spring
                  </span>
                )}
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
            <span style={label}>LOOK FOR — THE ENGINE'S CONDITIONAL PLAYS</span>
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
  index, day, bars, levels, events, cursor, chain, strike, optPivots, optExpiry,
  stale, loading, chainStale, chainTs,
  focus, onFocusToggle, onIndexChange, structures, structuresWhy,
  rotation, rotationWhy,
}: Props) {
  // Persisted per Task 1: defaults to light — the operator reads charts in
  // Kite on the light theme and reported the dark build unreadable.
  const [mode, setMode] = useMode()
  const pal = palette(mode)

  // SMC structure layer, now default OFF — reversed 2026-07-31 on measurement,
  // not taste. On the operator's own 2026-07-30 session structure.py printed 9
  // EQH and 7 EQL where their LuxAlgo printed 2 and 2 (4x over-firing); ~2/3 of
  // all structures are UNKNOWN by construction because the payload carries no
  // per-strike chain OI to confirm them; and the FVG/OB boxes never close, so a
  // filled gap keeps drawing. ~180 shapes a session buried the candles, which
  // is the exact noise the spec exists to avoid.
  //
  // The gate flipped with the default: `=== 'on'` now, so an absent or corrupt
  // value fails towards the QUIET chart. That inverts the old convention here
  // deliberately — with an unscored layer, failing "open" means failing towards
  // clutter the measurements do not support.
  const [smc, setSmc] = useState<boolean>(() => localStorage.getItem('tape.smc') === 'on')
  const toggleSmc = () => {
    const next = !smc
    localStorage.setItem('tape.smc', next ? 'on' : 'off')
    setSmc(next)
  }

  // STORY — the zone/condition bands and the event balloons, the two layers
  // drawn OVER the price area from the engine's event stream. Default OFF for
  // the same reason: signal_review.py scored the engine's own directional
  // events at -0.1 pts (`risk`, n=16) and -6.2 pts (`lean`, n=16) at +30m
  // against a +4.1 control — two of three claim-strength buckets did worse than
  // doing nothing — and the tab renders ~83 events a session at equal weight.
  //
  // Nothing is deleted. Unproven is not the same as disproven, the operator can
  // switch it back on in one click, and the legend below reports how many
  // events are being withheld so "hidden" never reads as "none found".
  const [story, setStory] = useState<boolean>(() => localStorage.getItem('tape.story') === 'on')
  const toggleStory = () => {
    const next = !story
    localStorage.setItem('tape.story', next ? 'on' : 'off')
    setStory(next)
  }

  // Leg-pane layout. Default SPLIT (side by side) because the operator's setup
  // is a PAIR read — one leg washed out at its floor while the other unwinds
  // from stretched — and that comparison wants both legs on screen at once.
  // STACK gives each pane the full width instead, which buys horizontal
  // resolution for reading individual candles. Both are tall (LegChart's
  // PANE_H); the page scrolls, so height costs nothing.
  const [legStack, setLegStack] = useState<boolean>(() => localStorage.getItem('tape.legstack') === 'on')
  const toggleLegStack = () => {
    const next = !legStack
    localStorage.setItem('tape.legstack', next ? 'on' : 'off')
    setLegStack(next)
  }

  // Trending OI for the strip + the ZONE READ's flow group. Tab-local and on
  // the OI Flow tab's own 15s cadence — /api/oiflow aggregates from the chain
  // poller's in-memory minute grid, so this costs no Dhan request. One fetch,
  // two consumers.
  const [flowRows, setFlowRows] = useState<FlowRow[] | null>(null)
  const [flowErr, setFlowErr] = useState<string>('')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/oiflow?idx=${index}&interval=15`)
        const j = await r.json()
        if (!alive) return
        if (!j.ok) { setFlowErr(j.error || 'flow unavailable'); setFlowRows(null); return }
        setFlowErr('')
        setFlowRows(j.rows || [])
      } catch { if (alive) { setFlowErr('backend unreachable'); setFlowRows(null) } }
    }
    load()
    const id = setInterval(load, 15000)
    return () => { alive = false; clearInterval(id) }
  }, [index])
  const lastFlow = flowRows && flowRows.length ? flowRows[flowRows.length - 1] : null
  const flowWhy = flowErr || (flowRows && !flowRows.length
    ? 'no flow marks yet — the chain poller has not recorded a clock mark this session'
    : lastFlow ? '' : 'no flow rows yet')

  // Clamp both ends: a negative cursor would index bars[-1] === undefined and
  // throw on the first field read. Computed here (rather than only after the
  // no-tape bail below) so structCounts, which needs the same clamp, never
  // has to duplicate it — bars.length === 0 just yields at === -1, which is
  // never read until the bail has already returned.
  const at = cursor == null
    ? bars.length - 1
    : Math.max(0, Math.min(cursor, bars.length - 1))

  // What the SMC toggle's tooltip reports: SWING_H/SWING_L are never drawn
  // (LevelsOverlay.ts's drawStructures says why — each is already the
  // endpoint of a BOS, an EQH/EQL pool or an OB), so counting them alongside
  // the drawn kinds would tell the operator "N structures" when only a
  // fraction of N puts anything on the chart. Split into what's actually
  // rendered and what's tracked but not shown.
  //
  // Causality: while the replay cursor is set, a structure born past `at` has
  // not happened yet as far as the chart is showing — LevelsOverlay's own
  // drawStructures filter is `s.born <= cut`, and this tooltip must count the
  // same set it draws, not the whole day's structures. Live (cursor === null)
  // counts everything, matching the overlay's unclamped draw there too.
  const structCounts = useMemo(() => {
    if (!structures) return null
    let drawn = 0, swings = 0, zones = 0
    for (const s of structures) {
      if (cursor != null && s.born > at) continue
      if (s.kind === 'SWING_H' || s.kind === 'SWING_L') swings++
      else {
        drawn++
        // FVG/OB are the only capped kinds (STRUCT_ZONE_LIMIT); counted apart
        // so the legend can disclose how many of them the chart is holding back.
        if (s.kind === 'FVG' || s.kind === 'OB') zones++
      }
    }
    return { drawn, swings, zones }
  }, [structures, cursor, at])

  // How many band-rotation signals the chart is actually showing. Causality:
  // one born past the cursor has not happened yet as far as the chart is
  // concerned, and the overlay's own draw clamps to the same bar — this count
  // must describe the same set, never the whole day's.
  const rotCount = useMemo(() => {
    if (!rotation) return null
    let fired = 0
    for (let i = 0; i < rotation.length; i++) {
      if (cursor != null && i > at) break
      if (rotation[i]) fired++
    }
    return fired
  }, [rotation, cursor, at])

  // Presentation only (spec §6 Phase 2): joins the payload's own event stream
  // to bars, tiers and formats — nothing computed about the market.
  const narrs = useMemo(() => buildNarration(bars, events), [bars, events])

  // How many events the STORY layer is holding back. Same causal clamp as
  // rotCount: an event past the cursor has not happened yet as far as the
  // chart is concerned, so it must not be counted into a disclosure that
  // describes what is being withheld from the CURRENT view.
  const eventCount = useMemo(() => {
    let n = 0
    for (let i = 0; i < narrs.length; i++) {
      if (cursor != null && i > at) break
      if (narrs[i]) n++
    }
    return n
  }, [narrs, cursor, at])

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
      // The CHART column fills the viewport exactly. The engine's read is a
      // sibling BELOW it (see the render), deliberately outside this budget:
      // the operator asked for a bigger chart plus "the page scrollable a
      // little bit" with the suggestion at the bottom of it, and that is
      // precisely a full-height chart followed by one panel's worth of scroll.
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

  const b = bars[at]                       // causal: the shown bar, not the newest
  const live = cursor == null
  const prec = dayPrecision(day)
  const dir = b.c >= b.o ? pal.bull : pal.bear // the bar's own direction, same as its candle
  const modeLabel = stale ? 'STALE' : live ? 'LIVE' : 'REPLAY'
  const modeColor = stale || !live ? pal.caution : pal.bull

  return (
    <>
    <div ref={rootRef} style={{
      display: 'flex', flexDirection: 'column',
      // minHeight, NOT height: the chart child is `flex:1` with minHeight 420,
      // so it cannot shrink to absorb overflow. With a fixed height the rows
      // added below it (OI strip, legend, the Hidden disclosure) spilled out
      // of the box and painted over the option-leg panes — the operator saw
      // the Hidden line floating across the CE chart. As a minimum it still
      // fills the viewport when content is short (flex:1 expands the chart),
      // and simply grows when it is not. Safe for the measurement loop: the
      // column's own `top` is set by what is ABOVE it, so growing downward
      // cannot move it, and the ResizeObserver watches the parent, not self.
      minHeight: availH ?? 420, padding: '16px 16px 0', gap: 8,
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

          {/* STORY: the event-derived layers over price (condition bands +
              balloons). Same styling family. Off by default — see the state
              above for the measurements. The title names the count so the
              operator knows what turning it on would add. */}
          <button
            onClick={toggleStory}
            title={narrs.length
              ? `Show the engine's event layers over price — ${eventCount} event${eventCount === 1 ? '' : 's'} and ${zones.length} condition band${zones.length === 1 ? '' : 's'} on this session. Off by default: these were never scored, and the ones that were measured did worse than doing nothing.`
              : 'Show the engine\'s event layers over price — no events on this session'}
            style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
              padding: '3px 9px', cursor: 'pointer',
              border: `1px solid ${pal.border}`, borderRadius: 4,
              backgroundColor: story ? pal.accent : 'transparent',
              color: story ? pal.card : pal.textMuted,
            }}
          >STORY</button>

          {/* LEGS: how the CE/PE premium panes are laid out. Same styling
              family; the label names the state you would switch TO is wrong —
              it names the CURRENT one, like LIGHT/DARK, so the button reads as
              a state not a command. */}
          <button
            onClick={toggleLegStack}
            title={legStack
              ? 'CE and PE panes stacked full-width — more horizontal resolution per pane. Click for side by side.'
              : 'CE and PE panes side by side — both legs visible at once, which is what the pair rotation read needs. Click to stack them full-width.'}
            style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
              padding: '3px 9px', cursor: 'pointer',
              border: `1px solid ${pal.border}`, borderRadius: 4,
              backgroundColor: 'transparent', color: pal.textMuted,
            }}
          >{legStack ? 'LEGS STACKED' : 'LEGS SPLIT'}</button>

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

      {/* The band-rotation layer is missing, so say so — an unmarked chart
          must not read as "your setup never printed today". Gated on `day` for
          the same reason the structure line above is: an empty day is the
          tab's own initial-load state, already covered by the bail. */}
      {day && !rotation && (
        <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
          Band-rotation signals unavailable{rotationWhy ? ` — ${rotationWhy}` : ''}. No setup
          markers are drawn rather than markers that might sit on the wrong bars.
        </div>
      )}

      <div style={{
        flex: 1, minHeight: 420, borderRadius: 6, overflow: 'hidden',
        border: `1px solid ${pal.border}`, backgroundColor: pal.card,
      }}>
        <ContractChart
          index={index} day={day} bars={bars} levels={levels} cursor={cursor}
          mode={mode} hover={hover} onHover={handleHover} narrs={narrs} zones={zones}
          structures={structures} smc={smc} rotation={rotation} story={story}
        />
      </div>

      {/* The last Trending-OI read, directly on the chart — the operator's
          explicit ask. The mark time is always shown (the row is the chain AS
          AT that clock mark, not now), and while replaying the strip dims and
          says it is live rather than pretending it scrubbed. */}
      <div style={{
        fontFamily: MONO, fontSize: 11, paddingLeft: 2,
        color: pal.textSecondary, opacity: cursor != null ? 0.55 : 1,
      }}>
        {lastFlow ? (
          <>
            <span style={{ fontWeight: 700, color: pal.textMuted }}>OI {lastFlow.time}</span>
            {' · CALL '}{crl(lastFlow.call)}
            {' · PUT '}{crl(lastFlow.put)}
            {' · DIFF '}{crl(lastFlow.diff)} {lastFlow.diff >= 0 ? 'PUT' : 'CALL'}-heavy{' '}
            {Math.abs(lastFlow.strength * 100).toFixed(0)}%
            {lastFlow.pcr != null && <>{' · PCR '}{lastFlow.pcr.toFixed(2)}</>}
            {lastFlow.chg_dir != null && (
              <>{' · Δ '}{lastFlow.chg_dir >= 0 ? '▲' : '▼'}{crl(Math.abs(lastFlow.chg_dir)).slice(1)}</>
            )}
            {lastFlow.brk && (
              <span style={{ color: pal.accent, fontWeight: 700 }}>
                {' · '}{lastFlow.brk} {lastFlow.brk_px != null ? lastFlow.brk_px.toFixed(1) : ''}
              </span>
            )}
            {cursor != null && (
              <span style={{ fontStyle: 'italic', color: pal.textMuted }}>
                {' · live flow — not aligned to the replay cursor'}
              </span>
            )}
          </>
        ) : (
          <span style={{ fontStyle: 'italic', color: pal.textMuted }}>
            Trending OI unavailable — {flowWhy}
          </span>
        )}
      </div>

      {/* The day's shape at a glance, dimmed past the replay cursor. */}
      <Ribbon mode={mode} narrs={narrs} cursor={cursor} hover={hover} onHover={handleHover} />

      <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
        VWAP red · σ bands ±1σ dark red / ±2σ green / ±3σ blue · levels · OI
        {rotCount != null
          ? ` · ${rotCount} band-rotation setup${rotCount === 1 ? '' : 's'} (triangle on the σ band`
            + ` it tagged, square pill; faded = the index was not squeezing into it,`
            + ` dashed = that could not be checked)`
          : ''}
        {smc && structures && structures.length
          ? ` · SMC structure (brass; solid = flow-confirmed and labelled, faint = unconfirmed,`
            + ` faint dashed = unchecked)${structCounts && structCounts.zones > STRUCT_ZONE_LIMIT
              ? ` · newest ${STRUCT_ZONE_LIMIT} of ${structCounts.zones} FVG/OB zones drawn`
              : ''}`
          : ''}
      </div>

      {/* What the chart is NOT drawing, and how much of it there is.
          Honesty rule: "we are not showing you" must never be indistinguishable
          from "we checked and found nothing". A layer that is merely switched
          off has to say so, with its count, or a quiet chart reads as a quiet
          market. Only rendered once the session has loaded (`day`), so an empty
          first paint never claims anything is being withheld. */}
      {day && (!story || !smc) && (
        <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2, opacity: 0.85 }}>
          Hidden:
          {!story && ` STORY — ${eventCount} event${eventCount === 1 ? '' : 's'}`
            + ` and ${zones.length} condition band${zones.length === 1 ? '' : 's'} not drawn`}
          {!story && !smc && ' ·'}
          {!smc && (structures
            ? ` SMC — ${structCounts ? structCounts.drawn : 0} structure${structCounts && structCounts.drawn === 1 ? '' : 's'} not drawn`
            : ' SMC — unavailable for this session, not merely hidden')}
          {'. '}
          Both are off by default because they were never scored against what
          price did next; the buttons above turn them back on. Hover still reads
          every event on its own bar.
        </div>
      )}

    </div>

    {/* Below the full-height chart column, in the operator's reading order:
        the ATM option legs (where the ±3σ trigger actually lives), then the
        ZONE READ (what sits at this price), then the engine's own read. All
        three read the SAME cursor-clamped bar `b` / cursor, so replay scrubs
        them causally together. */}
    <div style={{
      padding: '8px 16px 16px', backgroundColor: pal.bg,
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
        <LegChart day={day} bars={bars} leg="ce" strike={strike} cursor={cursor} mode={mode}
                  pivots={optPivots?.ce ?? null} pivotsWhy={optPivots?.why?.ce ?? null}
                  expiry={optExpiry} wide={legStack} />
        <LegChart day={day} bars={bars} leg="pe" strike={strike} cursor={cursor} mode={mode}
                  pivots={optPivots?.pe ?? null} pivotsWhy={optPivots?.why?.pe ?? null}
                  expiry={optExpiry} wide={legStack} />
      </div>
      <ZoneRead
        pal={pal} bar={b} chain={chain} levels={levels}
        rot={rotation?.[at] ?? null}
        structures={structures} structuresWhy={structuresWhy}
        flow={lastFlow} flowWhy={flowWhy}
        replaying={cursor != null}
      />
      <EngineReadPanel pal={pal} bar={b} />
    </div>
    </>
  )
}
