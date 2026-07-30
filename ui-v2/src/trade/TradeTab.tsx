import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import ContractChart from './ContractChart'
import Ribbon from './Ribbon'
import { buildNarration } from './narration'
import { dayPrecision } from './indicators'
import { palette, MONO, useMode } from '../theme'
import type { TapeBar, MapLevel, IndexKey, EventItem } from '../data'

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  events: EventItem[]
  cursor: number | null
  stale: boolean
  loading: boolean
}

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

export default function TradeTab({ index, day, bars, levels, events, cursor, stale, loading }: Props) {
  // Persisted per Task 1: defaults to light — the operator reads charts in
  // Kite on the light theme and reported the dark build unreadable.
  const [mode, setMode] = useMode()
  const pal = palette(mode)

  // Presentation only (spec §6 Phase 2): joins the payload's own event stream
  // to bars, tiers and formats — nothing computed about the market.
  const narrs = useMemo(() => buildNarration(bars, events), [bars, events])

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

      <div style={{
        flex: 1, minHeight: 420, borderRadius: 6, overflow: 'hidden',
        border: `1px solid ${pal.border}`, backgroundColor: pal.card,
      }}>
        <ContractChart
          index={index} day={day} bars={bars} levels={levels} cursor={cursor}
          mode={mode} hover={hover} onHover={handleHover} narrs={narrs}
        />
      </div>

      {/* The day's shape at a glance, dimmed past the replay cursor. */}
      <Ribbon mode={mode} narrs={narrs} cursor={cursor} hover={hover} onHover={handleHover} />

      <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
        VWAP & σ bands · levels · OI
      </div>
    </div>
  )
}
