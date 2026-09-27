import { useState, useEffect, useMemo, useRef, useCallback, createContext, useContext } from 'react'
import { useLiveData, HEAT_COLS, chainAgeS, CHAIN_STALE_S } from './data'
import type { IndexKey, IndexInfo, Dataset, HeatTone, Chain, MapLevelKind, FlowRow, RunState, TapeBar, Interval, GroundedCall } from './data'
import { usePalette, rgbOf } from './theme'
import type { Palette } from './theme'
import TradeTab from './trade/TradeTab'
import GlassBoard from './one/GlassBoard'
import SignalsTab from './signals/SignalsTab'
import FlowTab from './flow/FlowTab'
// BOARD rev 3 (docs/mockups/board-chess-rev3-2026-09-24-notes.md).
import BoardRev3, { useBoardGlance } from './board/BoardRev3'
import type { GlanceRead } from './board/BoardRev3'
import VpinTab from './vpin/VpinTab'
import WarTab from './war/WarTab'
// THE HOLD / FOLD WINDOW (docs/hold/PREREG-merged.md rev 4): mounted once, below, so it floats on every tab.
import HoldWindow from './hold/HoldWindow'
import HoldTab from './hold/HoldTab'
// The five-state machine read, shared with the Glass board's MACHINE widget.
// It moved out of this file so the board could import it without App.tsx and
// the board importing each other — see machine.ts.
import { liveMachine, machineWord, MACHINE_WORDS, lockNote } from './machine'
// Same Hinglish layer the Trade tab's balloons and callout use — one source of
// captions, so a kind cannot read one way on the chart and another in the feed.
import { glossOf, pillText, dirText } from './trade/hinglish'

// ── Tokens ───────────────────────────────────────────────────────────────────
// Colour carries exactly one meaning each. Before this, hue did two jobs at
// once — purple meant "spring", cyan meant "gamma", while green and red ALSO
// meant up and down — so it resolved to neither. Now brass is structure
// (levels, walls, pins, dealer regime) and green/red are direction only.

// ── Types ─────────────────────────────────────────────────────────────────────
// IndexKey now comes from ./data (single source of truth for the live layer).
// 'Glass' is the glance BOARD (src/one/GlassBoard.tsx): the machine and seven
// instruments as movable panes of glass, each one a launcher into the tab that
// owns its evidence. It replaces the one-screen chart trial that used to sit
// here — that trial answered "what has to happen next" with a bigger chart,
// which is the thing the operator already has in Kite.
//
// It is listed FIRST and is NOT the default tab — the operator judges it
// against the nine that already exist, and a board that seizes the landing
// screen would be judging itself.
//
// Exported because GlassBoard takes `setActiveTab` and must name the tab each
// pane opens. A type-only import is erased at compile time, so this does not
// make the two modules cyclic at runtime.
// 'Signals' is the accumulating live RECORD — every row trigger_log.py has
// written, served by /api/signals. It is a log, not a read: it shows what
// fired and the context it fired in, and deliberately computes nothing from
// them, because no row has an outcome until `python trigger_log.py score`
// fills one. See src/signals/SignalsTab.tsx.
// 'Flow' draws the day's ORDER FLOW on a time axis — the tape events at their
// own time and price, from /api/day/record. It sits beside Tape because it
// answers the same question from the other end: Tape is what is happening now,
// Flow is the shape of what already happened. Its axis is the SESSION
// (09:15–15:30), not the record's first row: the extension replays the chart's
// loaded footprint, so events reach back before the server started.
// See src/flow/FlowTab.tsx.
// 'War' is the OI battlefield drawn over TIME — every strike a band at its own
// price, thick with what the writers added since the open, from /api/oihist. It
// sits beside OI Flow because it answers the question a ladder cannot: WHEN a
// wall was built, and whether it is still held. A front that peaked at 11.5M
// and holds 1.1M reads as a ruin here and as an ordinary small wall everywhere
// else in this app. See src/war/WarTab.tsx.
export type Tab = 'Board' | 'Glass' | 'Heat' | 'Trade' | 'Tape' | 'Flow' | 'VPIN' | 'Chain' | 'OI Flow' | 'War' | 'Events' | 'Validate' | 'Map' | 'Signals'

// ── Empty dataset (first paint, and any index never read this session) ──────
// Nothing in it is invented: a live read replaces it within one poll. Until
// then every consumer renders "not shown" — never a zero standing in for a
// price, never a placeholder read or signal (CLAUDE.md rule 6).
const NOT_SHOWN = 'not shown — no live read from the backend yet'
const EMPTY_CHAIN: Chain = {
  pcr: '—', maxPain: 0, gex: '—', squeeze: '—', strikes: [],
  mpDist: 0, gexSpot: 0, bookZone: null, inBookZone: true,
  spot: 0, expiry: '', atmStraddle: 0, aligned: true, flipPx: null, ts: '', builtAt: null,
}
const perIndex = <V,>(make: () => V): Record<IndexKey, V> =>
  ({ NIFTY: make(), BANKNIFTY: make(), SENSEX: make() })
const EMPTY: Dataset = {
  INDICES: perIndex(() => ({ price: 0, change: 0, pct: 0, state: 'not shown', arrow: '' })),
  READS: perIndex(() => ({ headline: NOT_SHOWN, timing: '', direction: '', sub: '' })),
  KEY_LEVELS: perIndex(() => []),
  ORDER_FLOW: perIndex(() => ({ main: '', mm: '', stats: [] })),
  CHAIN_DATA: perIndex(() => ({ ...EMPTY_CHAIN })),
  EVENTS_BY_IDX: perIndex(() => []),
  FOCUS_BY_IDX: perIndex(() => []),
  CHART_DATA: perIndex(() => []),
  HEAT: perIndex(() => []),
  PRESSURE: perIndex(() => []),
  MAP: perIndex(() => ({ now: 0, zoneLo: 0, zoneHi: 0, levels: [] })),
}

/** Has this index been read at all? A live price is the futures close, which
 *  is never 0 — only the empty dataset carries 0. */
const hasRead = (i: IndexInfo) => i.price > 0

/** The empty dataset's rendering for a whole tab: "not shown", which is not
 *  "checked and found nothing" and not "could not check". */
function NotShown({ what }: { what: string }) {
  const pal = usePalette()
  return (
    <div style={{ padding: 24 }}>
      <div style={{
        background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
        padding: 20, fontSize: 13, color: pal.textMuted,
      }}>{what}: {NOT_SHOWN}.</div>
    </div>
  )
}

const DataCtx = createContext<Dataset>(EMPTY)
function useData(): Dataset {
  return useContext(DataCtx)
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (n: number) => n.toLocaleString('en-IN')
/** `rgba()` from a palette token — the only route by which a colour in this
 *  file acquires an alpha channel. */
const wash = (token: string, alpha: number | string) => `rgba(${rgbOf(token)},${alpha})`
// Real OI is large (millions of units). Show in lakhs (L), or thousands (K) below 1L.
const formatOI = (n: number) => n >= 1e5 ? `${(n / 1e5).toFixed(1)}L` : `${(n / 1e3).toFixed(1)}K`

// Heat-tile hue per tone, as the `r,g,b` triplet the alpha ramp needs.
const heatRgb = (pal: Palette): Record<HeatTone, string> => ({
  bull: rgbOf(pal.bull), bear: rgbOf(pal.bear), neutral: rgbOf(pal.textMuted),
})
// Spike-radar cell background: hue by direction, alpha ramps with intensity (0..1).
const heatColor = (pal: Palette, dir: HeatTone, intensity: number) =>
  `rgba(${heatRgb(pal)[dir]}, ${(0.08 + 0.55 * Math.max(0, Math.min(1, intensity))).toFixed(3)})`
// Levels-map per-kind styling (wall color resolves to CALL=bear / PUT=bull at render).
const kindStyle = (pal: Palette): Record<MapLevelKind, { color: string; dot: number; marker?: string }> => ({
  now:     { color: pal.accent, dot: 9 },
  wall:    { color: pal.textSecondary, dot: 8 },
  pin:     { color: pal.accent, dot: 8, marker: '◎' },
  pivot:   { color: pal.textMuted, dot: 5 },
  vwap:    { color: pal.caution, dot: 6 },
  band:    { color: `rgba(${rgbOf(pal.accent)},0.6)`, dot: 4 },
  floor:   { color: pal.bull, dot: 6 },
  cap:     { color: pal.bear, dot: 6 },
  strike:  { color: pal.strike, dot: 6 },
  session: { color: pal.textMuted, dot: 4 },
  trap:    { color: pal.caution, dot: 6, marker: '⚑' },
})

// ── Sub-components ────────────────────────────────────────────────────────────

function TimingChip({ value }: { value: string }) {
  // Palette tokens, never literals: on white these are TL's darkened
  // variants, not the neon pair that vanishes there.
  const pal = usePalette()
  const colors: Record<string, [string, string]> = {
    WAIT:  [wash(pal.caution, 0.12), pal.caution],
    READY: [wash(pal.accent, 0.15), pal.accent],
    GO:    [wash(pal.bull, 0.15), pal.bull],
    CAUTION: [wash(pal.bear, 0.12), pal.bear],
  }
  const [bg, fg] = colors[value] ?? [wash(pal.textMuted, 0.15), pal.textMuted]
  return (
    <span className="chip" style={{ backgroundColor: bg, color: fg }}>
      {value === 'WAIT' && '⏸ '}{value === 'READY' && '⚡ '}{value === 'GO' && '▶ '}
      {value}
    </span>
  )
}

/** The headline call's evidence (grounds.py): OI, CVD and order flow, each FOR /
 *  AGAINST / FLAT / BLIND with the fact behind it. A status, never a score. */
function Grounds({ g }: { g?: GroundedCall | null }) {
  const pal = usePalette()
  if (!g) return (
    <div style={{ fontSize: 11.5, color: pal.textMuted, marginTop: 4 }}>
      UNGROUNDED — this call was not checked against OI, CVD or order flow (server predates /api/calls, or a replay position)
    </div>)
  const col = g.status === 'BACKED' ? pal.textPrimary : g.status === 'CONTRADICTED' ? pal.caution : pal.textMuted
  const sym: Record<string, string> = { for: '✓', against: '✗', flat: '–', blind: '?' }
  return (
    <div style={{ fontSize: 11.5, marginTop: 4, lineHeight: 1.5 }}>
      <b style={{ color: col, letterSpacing: '0.04em' }}>{g.status}</b>
      {(['oi', 'cvd', 'flow'] as const).map((k) => (
        <div key={k} style={{ color: g[k].state === 'against' ? pal.caution : pal.textSecondary }}>
          <span className="mono">{sym[g[k].state] ?? '?'} {k.toUpperCase()}</span> {g[k].fact?.replace(/^CVD /, '')}
        </div>))}
    </div>)
}

function DirectionChip({ value }: { value: string }) {
  const pal = usePalette()
  const colors: Record<string, [string, string]> = {
    BEARISH: [wash(pal.bear, 0.12), pal.bear],
    BULLISH: [wash(pal.bull, 0.12), pal.bull],
    NEUTRAL: [wash(pal.textMuted, 0.12), pal.textSecondary],
  }
  const [bg, fg] = colors[value] ?? [wash(pal.textMuted, 0.12), pal.textSecondary]
  return (
    <span className="chip" style={{ backgroundColor: bg, color: fg }}>
      {value === 'BEARISH' && '▼ '}{value === 'BULLISH' && '▲ '}{value === 'NEUTRAL' && '〰 '}
      {value}
    </span>
  )
}

function IndexCell({ idx, data, active, onClick, read }: {
  idx: IndexKey
  data: IndexInfo
  active: boolean
  onClick: () => void
  /** The Board tab's one-line read of this index (/api/board), Board tab only. */
  read?: GlanceRead
}) {
  const pal = usePalette()
  const isUp = data.pct >= 0
  const color = Math.abs(data.pct) < 0.1 ? pal.textSecondary : isUp ? pal.bull : pal.bear

  return (
    <button
      onClick={onClick}
      className={data.highlight ? 'trending-glow' : ''}
      style={{
        // #1B2130 / #141926 were the dark palette's inset and card, inlined.
        backgroundColor: active ? pal.inset : pal.card,
        border: data.highlight
          ? `1px solid ${pal.accent}`
          : active
          ? `1px solid ${wash(pal.ink, 0.12)}`
          : `1px solid ${pal.border}`,
        borderRadius: 10,
        padding: '8px 14px',
        cursor: 'pointer',
        minWidth: 180,
        textAlign: 'left',
        position: 'relative',
        transition: 'border-color 150ms, background 150ms',
      }}
    >
      {data.highlight && (
        <span style={{
          position: 'absolute',
          top: -7,
          right: 10,
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: '0.1em',
          backgroundColor: pal.accent,
          // On light brass, ink (#141A22) measures 4.4:1 — just under the
          // line. The darker page-black is 4.9:1.
          color: '#0B0E14',
          padding: '1px 7px',
          borderRadius: 4,
        }}>
          LOOK HERE
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: pal.textPrimary }}>{idx}</span>
        <span style={{ fontSize: 10, color: pal.textMuted }}>{data.state}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span className="mono" style={{ fontSize: 15, fontWeight: 600, color: pal.textPrimary }}>
          {hasRead(data) ? fmt(data.price) : '—'}
        </span>
        {hasRead(data) && (
          <span className="mono" style={{ fontSize: 11, color, fontWeight: 600 }}>
            {data.arrow} {data.pct > 0 ? '+' : ''}{data.pct.toFixed(2)}%
          </span>
        )}
      </div>
      {read && (
        <div className="mono" title={read.title} style={{
          fontSize: 10.5, lineHeight: '13px', color: read.line.startsWith('could not check') ? pal.caution : pal.textSecondary,
          maxWidth: 230, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{read.line}</div>
      )}
    </button>
  )
}

/* ── Dhan token capture ────────────────────────────────────────────────────
   Without this, an expired token means the tape stops and the only recovery
   is a terminal. Clipboard first, password field as fallback.

   The token is never logged, never echoed back, and never put in the DOM as
   text: the input is type=password, its value is cleared immediately after
   posting, and the only thing displayed is the server's own validity message.
   server.py validates it, writes .dhan_token and hot-reloads the poller.   */
const JWT_RE = /^eyJ[\w-]+\.[\w-]+\.[\w-]+$/    // client sanity; server re-validates

function TokenCapture({ tone = 'quiet' }: { tone?: 'quiet' | 'loud' }) {
  const pal = usePalette()
  const [mode, setMode] = useState<'idle' | 'busy' | 'paste'>('idle')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const post = async (tok: string) => {
    setMode('busy')
    try {
      const r = await fetch('/api/token', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: tok }),
      })
      const j = await r.json()
      setMsg({ ok: !!j.ok, text: j.ok ? `accepted — ${j.msg}` : `rejected — ${j.msg}` })
    } catch {
      setMsg({ ok: false, text: 'could not reach the server — is it running on 8765?' })
    }
    setMode('idle')
  }

  const capture = async () => {
    let raw = ''
    try { raw = (await navigator.clipboard.readText()).trim() } catch { raw = '' }
    if (JWT_RE.test(raw)) { await post(raw); raw = ''; return }
    setMsg(null)
    setMode('paste')
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  const submitPaste = async () => {
    const el = inputRef.current
    if (!el) return
    const v = el.value.trim()
    el.value = ''                    // clear before any await
    if (!v) return
    setMode('idle')
    await post(v)
  }

  const btnStyle = {
    fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', padding: '4px 10px',
    borderRadius: 3, cursor: 'pointer', background: 'transparent',
    border: `1px solid ${tone === 'loud' ? pal.caution : pal.border}`,
    color: tone === 'loud' ? pal.caution : pal.textMuted,
  } as const

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      {mode === 'paste' ? (
        <>
          <input
            ref={inputRef} type="password" autoComplete="off" spellCheck={false}
            placeholder="paste Dhan token"
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); submitPaste() } }}
            style={{
              background: pal.inset, border: `1px solid ${pal.border}`, borderRadius: 3,
              padding: '4px 8px', color: pal.textPrimary, fontSize: 11.5, width: 190,
              outline: 'none', fontFamily: 'inherit',
            }}
          />
          <button onClick={submitPaste} style={{ ...btnStyle, borderColor: pal.accent, color: pal.accent }}>SAVE</button>
          <button onClick={() => setMode('idle')} style={btnStyle}>CANCEL</button>
        </>
      ) : (
        <button onClick={capture} disabled={mode === 'busy'} style={btnStyle}
          title="Copy the token to your clipboard and click. If the browser blocks clipboard access you get a paste field instead.">
          {mode === 'busy' ? '⟳ SAVING…' : '⟳ TOKEN'}
        </button>
      )}
      {msg && (
        <span style={{ fontSize: 11, color: msg.ok ? pal.bull : pal.bear, maxWidth: 340 }}>
          {msg.text}
        </span>
      )}
    </span>
  )
}

function GlanceBar({ active, setActive, lastUpdated, error, reads }: {
  active: IndexKey
  setActive: (k: IndexKey) => void
  lastUpdated: Date | null
  error: string | null
  /** Board tab only: each index's one-line read, under its cell. */
  reads?: Partial<Record<IndexKey, GlanceRead>>
}) {
  const { INDICES } = useData()
  const pal = usePalette()
  return (
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backgroundColor: pal.card,
      borderBottom: `1px solid ${pal.border}`,
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 24,
      minHeight: 72,
      flexWrap: 'wrap',
    }}>
      {/* Brand. flexShrink 0 so the wordmark never compresses; the scanner
          beside it is the thing that gives way. */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.12em', color: pal.textPrimary }}>
          TAPEMAP
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: pal.bull }}>
          <span className="live-dot" style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: pal.bull, display: 'inline-block' }} />
          LIVE
        </span>
        {lastUpdated && (
          <span className="mono" style={{ fontSize: 10, color: pal.textMuted }}>
            updated {lastUpdated.toLocaleTimeString('en-GB')}
          </span>
        )}
        {error && (
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.06em',
            color: pal.caution,
            backgroundColor: wash(pal.caution, 0.1),
            border: `1px solid ${wash(pal.caution, 0.2)}`,
            borderRadius: 4,
            padding: '1px 6px',
          }}>
            reconnecting…
          </span>
        )}
      </div>

      {/* Index scanner.
          DEFECT FIX — this group had no `flex`/`min-width`, so its min-content
          was the full 556px of three 180px-min cards and it could not give a
          pixel. The bar's own `flexWrap:'wrap'` therefore broke the LINE first:
          below ~850px CSS the whole scanner dropped to a second row at x=24,
          i.e. the price and change block landed directly under the TAPEMAP
          wordmark. `flex: 1 1 auto` + `minWidth: 0` lets the group shrink so
          its OWN inner wrap re-flows the three cards instead — the bar grows a
          row of cards rather than dumping them beneath the logo.

          The basis is 200px, not `auto`: flexbox chooses LINE BREAKS from each
          item's hypothetical main size, and with `auto` that is still the
          group's 556px max-content — so the bar kept wrapping at ~810px no
          matter how shrinkable the group was afterwards. A 200px basis holds
          the first line down to ~610px, below which a stacked bar is the right
          answer anyway. */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flex: '1 1 200px', minWidth: 0 }}>
        {(Object.entries(INDICES) as [IndexKey, typeof INDICES[IndexKey]][]).map(([k, d]) => (
          <IndexCell key={k} idx={k} data={d} active={active === k} onClick={() => setActive(k)}
            read={reads ? reads[k] ?? { line: 'reading the board…', title: '' } : undefined} />
        ))}
      </div>

      <div style={{ marginLeft: 'auto' }}>
        <TokenCapture />
      </div>

      {/* THE READ used to be repeated here. It now lives once, in the ANSWER
          band directly below, at a scale that actually ranks it. Saying the
          same thing in four places is what made the old screen unreadable. */}
    </div>
  )
}

function TapeTab({ index }: { index: IndexKey }) {
  const { INDICES, KEY_LEVELS, ORDER_FLOW, PRESSURE } = useData()
  const pal = usePalette()
  if (!hasRead(INDICES[index])) return <NotShown what={`${index} tape`} />
  const levels = KEY_LEVELS[index]
  const flow = ORDER_FLOW[index]
  const pressure = PRESSURE[index]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 260px', gap: 16, padding: 24, flex: 1 }}>
      {/* Left: Key Levels */}
      <div style={{
        backgroundColor: pal.card,
        border: `1px solid ${pal.border}`,
        borderRadius: 14,
        padding: '16px 0',
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
      }}>
        <div className="micro-label" style={{ padding: '0 16px', marginBottom: 12 }}>Key Levels</div>
        {levels.map((lvl) => {
          const isHere = lvl.dir === 'here'
          const isUp = lvl.dir === 'up'
          return (
            <div
              key={lvl.label}
              style={{
                padding: '10px 16px',
                borderLeft: isHere ? `3px solid ${pal.accent}` : '3px solid transparent',
                backgroundColor: isHere ? wash(pal.accent, 0.06) : 'transparent',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: pal.textMuted, letterSpacing: '0.06em' }}>{lvl.label}</span>
                {!isHere && (
                  <span className="mono" style={{
                    fontSize: 10,
                    color: isUp ? pal.bull : pal.bear,
                    fontWeight: 600,
                  }}>
                    {isUp ? '▲' : '▼'} {isUp ? '+' : ''}{lvl.dist}
                  </span>
                )}
              </div>
              <div className="mono" style={{ fontSize: 14, fontWeight: 600, color: isHere ? pal.accent : pal.textPrimary }}>
                {fmt(lvl.value)}
              </div>
              <div style={{ fontSize: 10, color: pal.textMuted, marginTop: 1 }}>{lvl.note}</div>
            </div>
          )
        })}
      </div>

      {/* Center: the Pressure Tape. The price/VWAP chart that sat above it is
          gone (no charts, reads only: she has the chart on her broker screen). */}
      <div style={{
        backgroundColor: pal.card,
        border: `1px solid ${pal.border}`,
        borderRadius: 14,
        padding: '16px 8px 8px 4px',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Pressure Tape — diverging net-flow histogram (bars grow up=buying / down=selling) */}
        <div style={{ padding: '10px 12px 4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <div className="micro-label">Pressure Tape — net order-flow (bucketed)</div>
            <div style={{ display: 'flex', gap: 12, fontSize: 10, color: pal.textMuted }}>
              <span style={{ color: pal.bull }}>▲ buying</span>
              <span style={{ color: pal.bear }}>▼ selling</span>
              <span style={{ color: pal.textMuted }}>· balanced</span>
            </div>
          </div>
          <div style={{ position: 'relative', height: 64, paddingLeft: 62, paddingRight: 78 }}>
            {/* zero centerline */}
            <div style={{ position: 'absolute', left: 62, right: 78, top: '50%', height: 1, background: wash(pal.ink, 0.06) }} />
            <div style={{ position: 'relative', display: 'flex', gap: 2, height: '100%', alignItems: 'stretch' }}>
              {pressure.map((c, i) => {
                const up = c.val > 0.03
                const dn = c.val < -0.03
                const h = Math.min(46, Math.abs(c.val) * 46)
                const alpha = (0.35 + 0.5 * Math.abs(c.val)).toFixed(3)
                const green = wash(pal.bull, alpha)
                const red = wash(pal.bear, alpha)
                return (
                  <div key={i} title={c.note} style={{ flex: 1, minWidth: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
                    {/* top half — buying grows up from the centerline */}
                    <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
                      {up && <div style={{ width: '100%', height: h, background: green, borderRadius: '3px 3px 0 0' }} />}
                      {!up && !dn && <div style={{ width: '100%', height: 3, background: wash(pal.textMuted, 0.35) }} />}
                    </div>
                    {/* bottom half — selling grows down from the centerline */}
                    <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
                      {dn && <div style={{ width: '100%', height: h, background: red, borderRadius: '0 0 3px 3px' }} />}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Right: Order Flow */}
      <div style={{
        backgroundColor: pal.card,
        border: `1px solid ${pal.border}`,
        borderRadius: 14,
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}>
        <div>
          <div className="micro-label" style={{ marginBottom: 10 }}>Order Flow</div>
          <p style={{ fontSize: 13, color: pal.textPrimary, lineHeight: 1.65, margin: 0 }}>
            {flow.main.split('. ').map((sentence, i, arr) => (
              <span key={i}>
                <span style={{ color: i === 0 ? pal.textPrimary : pal.textSecondary }}>{sentence}{i < arr.length - 1 ? '. ' : ''}</span>
              </span>
            ))}
          </p>
        </div>

        <div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 10,
            fontWeight: 600,
            color: pal.caution,
            backgroundColor: wash(pal.caution, 0.08),
            border: `1px solid ${wash(pal.caution, 0.15)}`,
            borderRadius: 6,
            padding: '2px 8px',
            marginBottom: 8,
          }}>
            ● {flow.main.includes('decelerating') ? 'decelerating' : 'building'}
          </div>
          <div className="micro-label" style={{ marginBottom: 6 }}>MM Perspective</div>
          <p style={{ fontSize: 12, color: pal.textSecondary, margin: 0, lineHeight: 1.55 }}>
            {flow.mm}
          </p>
        </div>

        <div style={{ marginTop: 'auto' }}>
          <div className="micro-label" style={{ marginBottom: 10 }}>Volatility</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {flow.stats.map(s => (
              <div key={s.label} style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 10px',
                backgroundColor: pal.inset,
                borderRadius: 8,
                border: `1px solid ${pal.border}`,
              }}>
                <span style={{ fontSize: 11, color: pal.textMuted }}>{s.label}</span>
                <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: pal.textPrimary }}>{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/* How far a book has fallen from its own session high. A wall at full strength
   and a wall that has quietly lost a third of its defenders look identical if
   you only print current OI — and that difference is the whole game. Shown
   only once it is worth reacting to. */
function OffPeak({ oi, pk }: { oi: number; pk: number }) {
  const pal = usePalette()
  if (!pk || pk <= 0) return null
  const off = 1 - oi / pk
  if (off < 0.08) return null
  return (
    <span className="mono" title={`session peak ${Math.round(pk).toLocaleString('en-IN')}`}
      style={{
        fontSize: 9.5, fontWeight: 700, letterSpacing: '0.02em',
        color: off >= 0.30 ? pal.caution : pal.textSecondary, opacity: 0.95,
      }}>
      −{Math.round(off * 100)}%
    </span>
  )
}

function ChainTab({ index }: { index: IndexKey }) {
  const { CHAIN_DATA, INDICES } = useData()
  const pal = usePalette()
  if (!hasRead(INDICES[index])) return <NotShown what={`${index} option chain`} />
  const chain = CHAIN_DATA[index]
  const maxCeOI = Math.max(1, ...chain.strikes.map(s => s.ceOI))
  const maxPeOI = Math.max(1, ...chain.strikes.map(s => s.peOI))
  const maxAbsGex = Math.max(1, ...chain.strikes.map(s => Math.abs(s.gex)))

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Put/Call Ratio', value: chain.pcr, note: Number(chain.pcr) < 1 ? 'Bearish lean' : 'Bullish lean' },
          { label: 'Max Pain', value: fmt(chain.maxPain), note: 'Expiry magnet' },
          { label: 'GEX', value: chain.gex, note: chain.gex === 'Negative' ? 'Amplifies moves' : chain.gex === 'Positive' ? 'Dampens moves' : 'Balanced' },
          { label: 'Squeeze Fuel', value: chain.squeeze, note: chain.squeeze === 'High' ? 'Large short base' : 'Limited short' },
        ].map(stat => (
          <div key={stat.label} style={{
            backgroundColor: pal.card,
            border: `1px solid ${pal.border}`,
            borderRadius: 14,
            padding: '16px 20px',
          }}>
            <div className="micro-label" style={{ marginBottom: 8 }}>{stat.label}</div>
            <div className="mono" style={{ fontSize: 24, fontWeight: 700, color: pal.textPrimary, marginBottom: 4 }}>{stat.value}</div>
            <div style={{ fontSize: 11, color: pal.textMuted }}>{stat.note}</div>
          </div>
        ))}
      </div>

      {/* Strike heatmap */}
      <div style={{
        backgroundColor: pal.card,
        border: `1px solid ${pal.border}`,
        borderRadius: 14,
        overflow: 'hidden',
      }}>
        <div style={{ padding: '12px 20px', borderBottom: `1px solid ${pal.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="micro-label">
            Strike Heatmap — CE OI · GEX · PE OI
            {!chain.aligned && (
              <span style={{ color: pal.caution, marginLeft: 10, letterSpacing: 0, textTransform: 'none' }}>
                live snapshot — the ladder has no per-strike history, so it is not replayed
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 14, fontSize: 10, color: pal.textMuted }}>
            <span style={{ color: pal.bear }}>■ CE writers</span>
            <span style={{ color: pal.bull }}>■ PE writers</span>
            <span style={{ color: pal.accent }}>■ +GEX</span>
            <span style={{ color: pal.caution }}>■ −GEX</span>
          </div>
        </div>
        {/* Column header */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '8px 20px', borderBottom: `1px solid ${pal.border}` }}>
          <div style={{ flex: 1, fontSize: 10, color: pal.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>CE OI</div>
          <div style={{ width: 48, textAlign: 'center', fontSize: 10, color: pal.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>GEX</div>
          <div style={{ width: 160, textAlign: 'center', fontSize: 10, color: pal.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>STRIKE</div>
          <div style={{ flex: 1, textAlign: 'right', fontSize: 10, color: pal.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>PE OI</div>
        </div>
        {/* Rows */}
        {chain.strikes.map(s => {
          const isWall = s.type === 'callwall' || s.type === 'putwall'
          const isATM = s.type === 'atm'
          const ceA = Math.min(1, s.ceOI / maxCeOI)
          const peA = Math.min(1, s.peOI / maxPeOI)
          const gexA = Math.min(1, Math.abs(s.gex) / maxAbsGex)
          const gexRGB = rgbOf(s.gex > 0 ? pal.accent : pal.caution)
          return (
            <div key={s.strike} style={{
              display: 'flex',
              alignItems: 'stretch',
              borderBottom: `1px solid ${pal.border}`,
              backgroundColor: isATM ? wash(pal.accent, 0.06) : 'transparent',
            }}>
              {/* CE OI heat cell */}
              <div style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8,
                padding: '10px 14px',
                backgroundColor: wash(pal.bear, (0.06 + 0.64 * ceA).toFixed(3)),
              }}>
                <OffPeak oi={s.ceOI} pk={s.cePk} />
                <span className="mono" style={{ fontSize: 12, color: pal.textPrimary, fontWeight: 600 }}>{formatOI(s.ceOI)}</span>
              </div>
              {/* GEX strip */}
              <div title={`GEX ${Math.round(s.gex).toLocaleString('en-IN')}`} style={{
                width: 48,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                backgroundColor: `rgba(${gexRGB},${(0.10 + 0.80 * gexA).toFixed(3)})`,
                borderLeft: `1px solid ${pal.border}`,
                borderRight: `1px solid ${pal.border}`,
              }}>
                <span className="mono" style={{ fontSize: 9, color: pal.textPrimary, opacity: 0.85 }}>{s.gex > 0 ? '+' : '−'}</span>
              </div>
              {/* Strike */}
              <div style={{ width: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px 4px' }}>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: isATM ? pal.accent : isWall ? pal.textPrimary : pal.textSecondary }}>
                  {fmt(s.strike)}
                </span>
                {s.type === 'callwall' && <span style={{ fontSize: 9, color: pal.bear, marginLeft: 6, fontWeight: 600 }}>▲</span>}
                {s.type === 'putwall' && <span style={{ fontSize: 9, color: pal.bull, marginLeft: 6, fontWeight: 600 }}>▼</span>}
                {isATM && <span style={{ fontSize: 9, color: pal.accent, marginLeft: 6, fontWeight: 600 }}>◉</span>}
              </div>
              {/* PE OI heat cell */}
              <div style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 8,
                padding: '10px 14px',
                backgroundColor: wash(pal.bull, (0.06 + 0.64 * peA).toFixed(3)),
              }}>
                <span className="mono" style={{ fontSize: 12, color: pal.textPrimary, fontWeight: 600 }}>{formatOI(s.peOI)}</span>
                <OffPeak oi={s.peOI} pk={s.pePk} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function EventsTab({ index }: { index: IndexKey }) {
  const { EVENTS_BY_IDX, FOCUS_BY_IDX, INDICES } = useData()
  const pal = usePalette()
  // FOCUS is the default: on a live expiry day the raw log repeats itself so
  // often that the signal is buried. Preference persists, as it does in v1.
  const [focus, setFocus] = useState(() => localStorage.getItem('focus') !== '0')
  const events = focus ? FOCUS_BY_IDX[index] : EVENTS_BY_IDX[index]
  const full = EVENTS_BY_IDX[index]
  const hidden = Math.max(0, full.length - events.length)
  const [hovered, setHovered] = useState<number | null>(null)
  if (!hasRead(INDICES[index])) return <NotShown what={`${index} events`} />
  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 760 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
        <span className="micro-label">Event Feed — {index} — newest first</span>
        <button
          onClick={() => { const n = !focus; setFocus(n); localStorage.setItem('focus', n ? '1' : '0') }}
          title="FOCUS drops state churn and low-grade band tags, silences a kind repeating itself inside 10 minutes or echoing the log's direction inside 8, and collapses a contradictory minute into one CONFLICT line. Panels always show everything."
          style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', padding: '3px 9px',
            borderRadius: 3, cursor: 'pointer', background: 'transparent',
            border: `1px solid ${focus ? pal.accent : pal.border}`,
            color: focus ? pal.accent : pal.textMuted,
          }}
        >FOCUS</button>
        {focus && hidden > 0 && (
          <span style={{ fontSize: 11, color: pal.textMuted }}>{hidden} repeat{hidden === 1 ? '' : 's'} hidden</span>
        )}
      </div>
      {events.map((ev, i) => {
        const accent = ev.dir === 'bull' ? pal.bull : ev.dir === 'bear' ? pal.bear : pal.textMuted
        return (
          <div
            key={i}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: 'flex',
              gap: 16,
              padding: '14px 18px',
              backgroundColor: hovered === i ? pal.inset : pal.card,
              borderTop: `1px solid ${hovered === i ? wash(pal.ink, 0.1) : pal.border}`,
              borderRight: `1px solid ${hovered === i ? wash(pal.ink, 0.1) : pal.border}`,
              borderBottom: `1px solid ${hovered === i ? wash(pal.ink, 0.1) : pal.border}`,
              borderLeft: `3px solid ${accent}`,
              borderRadius: 10,
              cursor: 'pointer',
              transition: 'all 150ms',
            }}
          >
            <span className="mono" style={{ fontSize: 11, color: pal.textMuted, whiteSpace: 'nowrap', marginTop: 1 }}>{ev.time}</span>
            {/* Hinglish caption + the direction the engine already decided
                (data.ts's evDir), then the engine's own sentence underneath,
                verbatim. The gloss names the KIND — it never restates the
                claim, so the original line has to stay visible beside it. An
                unglossed kind falls back to the engine's own tag. */}
            <span style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
              <span style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                <span style={{
                  fontSize: 12, fontWeight: 700, letterSpacing: '0.06em',
                  textTransform: 'uppercase', color: accent,
                }}>
                  {pillText(ev.tag)}
                </span>
                <span style={{ fontSize: 10, fontWeight: 600, color: accent }}>
                  {dirText(ev.dir, ev.tag).arrow} {dirText(ev.dir, ev.tag).text}
                </span>
              </span>
              {glossOf(ev.tag) && (
                <span style={{ fontSize: 12.5, color: pal.textPrimary, lineHeight: 1.45 }}>
                  {glossOf(ev.tag)!.line}
                </span>
              )}
              <span style={{ fontSize: 12, color: pal.textSecondary, lineHeight: 1.5 }}>{ev.text}</span>
            </span>
            {hovered === i && (
              <span style={{
                marginLeft: 'auto',
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: accent,
                backgroundColor: wash(accent, 0.1),
                padding: '2px 8px',
                borderRadius: 4,
                alignSelf: 'flex-start',
                whiteSpace: 'nowrap',
              }}>
                {ev.tag}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function MapTab({ index }: { index: IndexKey }) {
  const { MAP, INDICES } = useData()
  const pal = usePalette()
  if (!hasRead(INDICES[index])) return <NotShown what={`${index} levels map`} />
  const m = MAP[index]
  const H = 520
  const span = Math.max(1, m.zoneHi - m.zoneLo)
  const yOf = (v: number) => Math.max(0, Math.min(H, ((m.zoneHi - v) / span) * H))

  const bandHi = m.levels.find(l => l.label === '+1σ')?.value
  const bandLo = m.levels.find(l => l.label === '−1σ')?.value
  const nowY = yOf(m.now)

  const legendItem = (color: string, label: string) => (
    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ width: 9, height: 9, borderRadius: '50%', background: color }} />{label}
    </span>
  )

  return (
    <div style={{ padding: 24, maxWidth: 720 }}>
      <div className="micro-label" style={{ marginBottom: 4 }}>Levels Map — {index} · action zone</div>
      <div style={{ fontSize: 11, color: pal.textMuted, marginBottom: 16 }}>
        Real levels around price — pivots, OI walls, VWAP, ±1σ, dealer pin, floor/cap, traps. Zoomed to where the fight is now.
      </div>
      <div style={{ backgroundColor: pal.card, border: `1px solid ${pal.border}`, borderRadius: 14, padding: '20px 24px' }}>
        <div style={{ position: 'relative', height: H }}>
          {/* ±1σ band shade */}
          {bandHi != null && bandLo != null && (
            <div style={{
              position: 'absolute', left: 0, right: 0,
              top: yOf(bandHi), height: Math.max(1, yOf(bandLo) - yOf(bandHi)),
              background: wash(pal.accent, 0.06), borderRadius: 4,
            }} />
          )}
          {/* NOW line */}
          <div style={{ position: 'absolute', left: 0, right: 0, top: nowY, height: 0, borderTop: `1px solid ${pal.accent}`, zIndex: 4 }}>
            <span className="mono" style={{ position: 'absolute', right: 0, top: -9, fontSize: 10, color: pal.accent, fontWeight: 700 }}>
              NOW {fmt(Math.round(m.now))}
            </span>
          </div>
          {/* Levels */}
          {m.levels.map((lvl, i) => {
            if (lvl.kind === 'now') return null
            const st = kindStyle(pal)[lvl.kind]
            const color = lvl.kind === 'wall' ? (lvl.label === 'CALL' ? pal.bear : pal.bull) : st.color
            const off = lvl.value > m.zoneHi ? 'up' : lvl.value < m.zoneLo ? 'down' : null
            const y = yOf(lvl.value)
            const above = lvl.value >= m.now
            const note = lvl.note + (off === 'up' ? ' ↑ off-scale' : off === 'down' ? ' ↓ off-scale' : '')
            return (
              <div key={i} style={{
                position: 'absolute', left: 0, right: 0, top: y,
                display: 'flex', alignItems: 'center', gap: 10, transform: 'translateY(-50%)',
              }}>
                <div style={{
                  width: st.dot, height: st.dot, borderRadius: '50%', backgroundColor: color, flexShrink: 0,
                  boxShadow: lvl.kind === 'pin' ? `0 0 8px ${pal.accent}` : undefined,
                }} />
                <div style={{ flex: 1, height: 0, borderTop: `1px dashed ${wash(above ? pal.bear : pal.bull, 0.14)}` }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 280 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: pal.textMuted, width: 46, textAlign: 'right' }}>
                    {st.marker ? `${st.marker} ` : ''}{lvl.label}
                  </span>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 700, color, width: 66 }}>
                    {fmt(Math.round(lvl.value))}
                  </span>
                  <span style={{ fontSize: 11, color: pal.textMuted }}>{note}</span>
                </div>
              </div>
            )
          })}
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', gap: 16, marginTop: 16, flexWrap: 'wrap', fontSize: 10, color: pal.textMuted, alignItems: 'center' }}>
          {legendItem(pal.bear, 'call wall')}
          {legendItem(pal.bull, 'put wall')}
          {legendItem(pal.accent, 'dealer pin')}
          {legendItem(pal.textMuted, 'pivot / session')}
          {legendItem(pal.caution, 'vwap · trap')}
        </div>
      </div>
    </div>
  )
}

function HeatTab({ active, setActive, dead }: {
  active: IndexKey; setActive: (k: IndexKey) => void; dead: IndexKey[]
}) {
  const { HEAT, INDICES } = useData()
  const pal = usePalette()
  const keys: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']
  // This is the one view read across all three indices at once, so a dead one
  // must not sit here looking identical to a live one. Its row would otherwise
  // show its last good read and get counted in the spike badge as though it
  // were happening now.
  const isDead = (k: IndexKey) => dead.includes(k)
  const spikeCount = keys.reduce(
    (n, k) => n + (isDead(k) ? 0 : HEAT[k].filter(c => c.spike).length), 0)

  const legend = (dir: HeatTone, glyph: string, label: string) => (
    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ color: `rgb(${heatRgb(pal)[dir]})`, fontSize: 11 }}>{glyph}</span>{label}
    </span>
  )

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <div className="micro-label">Live Spike Radar</div>
        {spikeCount > 0 && (
          <span style={{
            fontSize: 9, fontWeight: 700, letterSpacing: '0.06em', color: pal.caution,
            background: wash(pal.caution, 0.12), border: `1px solid ${wash(pal.caution, 0.25)}`,
            borderRadius: 4, padding: '1px 7px',
          }}>
            ⚡ {spikeCount} spikes live
          </span>
        )}
      </div>
      <div style={{ fontSize: 11, color: pal.textMuted, marginBottom: 16 }}>
        Live spike radar — volume, OI, gamma &amp; squeeze across futures + both option legs. Brighter = bigger; glowing ⚡ = spiking.
      </div>
      <div style={{ backgroundColor: pal.card, border: `1px solid ${pal.border}`, borderRadius: 14, padding: 16 }}>
        {/* Header row */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
          <div style={{ width: 132 }} />
          {HEAT_COLS.map(c => (
            <div key={c} className="micro-label" style={{ flex: 1, textAlign: 'center' }}>{c}</div>
          ))}
        </div>
        {/* Index rows */}
        {keys.map(k => {
          const cells = HEAT[k]
          const hot = INDICES[k].highlight
          const isActive = active === k
          return (
            <div key={k} style={{ display: 'flex', gap: 6, alignItems: 'stretch', marginBottom: 8 }}>
              <button
                onClick={() => setActive(k)}
                className={hot ? 'trending-glow' : ''}
                style={{
                  width: 132,
                  textAlign: 'left',
                  cursor: 'pointer',
                  background: isActive ? pal.inset : 'transparent',
                  borderTop: `1px solid ${isActive ? wash(pal.ink, 0.12) : pal.border}`,
                  borderRight: `1px solid ${isActive ? wash(pal.ink, 0.12) : pal.border}`,
                  borderBottom: `1px solid ${isActive ? wash(pal.ink, 0.12) : pal.border}`,
                  borderLeft: hot ? `3px solid ${pal.accent}` : '3px solid transparent',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: pal.textPrimary,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  gap: 2,
                }}
              >
                <span style={{ fontSize: 12, fontWeight: 700, color: isDead(k) ? pal.textMuted : pal.textPrimary }}>{k}</span>
                <span className="mono" style={{
                  fontSize: 11, color: pal.textMuted,
                  textDecoration: isDead(k) ? 'line-through' : 'none',
                }}>{hasRead(INDICES[k]) ? fmt(INDICES[k].price) : '—'}</span>
              </button>
              {isDead(k) ? (
                <div style={{
                  flex: 1, display: 'flex', alignItems: 'center', gap: 8,
                  border: `1px dashed ${pal.border}`, borderRadius: 8, padding: '8px 14px',
                  fontSize: 11.5, color: pal.caution,
                }}>
                  no {k} tape — nothing to read here
                </div>
              ) : !hasRead(INDICES[k]) ? (
                <div style={{
                  flex: 1, display: 'flex', alignItems: 'center', gap: 8,
                  border: `1px dashed ${pal.border}`, borderRadius: 8, padding: '8px 14px',
                  fontSize: 11.5, color: pal.textMuted,
                }}>
                  {k}: {NOT_SHOWN}
                </div>
              ) : cells.map((cell, i) => {
                const hue = heatRgb(pal)[cell.dir]
                const arrow = cell.dir === 'bull' ? '▲' : cell.dir === 'bear' ? '▼' : '·'
                return (
                  <div
                    key={i}
                    title={`${HEAT_COLS[i]}: ${cell.label}${cell.spike ? ' — SPIKE' : ''}`}
                    style={{
                      flex: 1,
                      height: 46,
                      borderRadius: 8,
                      backgroundColor: heatColor(pal, cell.dir, cell.intensity),
                      border: cell.spike ? `1px solid rgba(${hue},0.9)` : `1px solid ${pal.border}`,
                      boxShadow: cell.spike ? `0 0 10px 1px rgba(${hue},0.55)` : undefined,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 1,
                      textAlign: 'center',
                      padding: '0 4px',
                    }}
                  >
                    <span style={{ fontSize: 10, fontWeight: 700, lineHeight: 1.1, color: cell.intensity > 0.5 ? pal.textPrimary : pal.textSecondary }}>
                      {cell.spike ? '⚡ ' : ''}{cell.label}
                    </span>
                    {/* Ink, not the tile's own hue: on white the wash goes
                        saturated and a same-hue glyph disappears into it
                        (measured 1.5–2.8:1). Direction is already carried by
                        the tile colour and the arrow's shape. */}
                    <span style={{ fontSize: 9, color: pal.textPrimary, opacity: 0.9 }}>{arrow}</span>
                  </div>
                )
              })}
            </div>
          )
        })}
        {/* Legend */}
        <div style={{ display: 'flex', gap: 16, marginTop: 14, fontSize: 10, color: pal.textMuted, alignItems: 'center', flexWrap: 'wrap' }}>
          {legend('bull', '▲', 'bullish')}
          {legend('bear', '▼', 'bearish')}
          {legend('neutral', '·', 'neutral')}
          <span style={{ color: pal.caution }}>⚡ spike</span>
          <span>brighter = stronger</span>
        </div>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
/* ── Trending OI ───────────────────────────────────────────────────────────
   One row per clock mark: how much call and put OI has been ADDED across the
   selected strikes since the day opened, and which way that is tilting.
   Aggregated server-side (/api/oiflow) — the minute grid behind it is a few
   hundred KB while the raw chain is ~180 MB a day. Row shape (`FlowRow`) is
   shared with the Trade tab's OI strip + zone read and lives in data.ts. */

const inr = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 0 })

function OiFlowTab({ index }: { index: IndexKey }) {
  const pal = usePalette()
  // 5, not 15: a bucket only exists once the session has run long enough to
  // produce it. Measured 2026-08-10 at 09:37 — a 15-minute grid was TWO rows,
  // and the first of those is the 09:15 baseline, which is zero by
  // construction (call/put are cumulative day OI CHANGE, so at the opening
  // bell nothing has changed yet). The table therefore read as empty for the
  // first hour of every session. Operator request; the selector still offers
  // 15/30/60 for anyone who wants the coarser read.
  const [mins, setMins] = useState(5)
  const [rows, setRows] = useState<FlowRow[]>([])
  const [avail, setAvail] = useState<number[]>([])
  const [sel, setSel] = useState<number[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  /** Why the CHAIN cannot be read, in the backend's own words. Null when it is
   *  healthy. Separate from `err`, which is this endpoint failing: the flow
   *  endpoint answers fine while the chain behind it is dead, and those are
   *  two different sentences. */
  const [chainWhy, setChainWhy] = useState<string | null>(null)

  useEffect(() => { setSel(null) }, [index])   // strike sets differ per index

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const q = `idx=${index}&interval=${mins}`
          + (sel?.length ? `&strikes=${sel.join(',')}` : '')
        const r = await fetch('/api/oiflow?' + q)
        const j = await r.json()
        if (!alive) return
        if (!j.ok) { setErr(j.error || 'unavailable'); setRows([]); return }
        setErr(null)
        // The chain's own health, published alongside the rows. An empty
        // `rows` with a DEAD chain is "we could not check", not "nothing
        // yet" — see the empty state below.
        setChainWhy(j.chain_ok === false ? (j.chain_why || 'the chain is unavailable') : null)
        setAvail(j.strikes || [])
        setRows(j.rows || [])
      } catch { if (alive) setErr('backend unreachable') }
    }
    load()
    const id = setInterval(load, 15000)
    return () => { alive = false; clearInterval(id) }
  }, [index, mins, sel])

  const toggle = (k: number) => {
    const base = sel ?? avail
    const next = base.includes(k) ? base.filter(x => x !== k) : [...base, k].sort((a, b) => a - b)
    setSel(next.length ? next : null)
  }

  const th: React.CSSProperties = {
    textAlign: 'right', padding: '7px 10px', fontSize: 10.5, fontWeight: 600,
    letterSpacing: '0.09em', textTransform: 'uppercase', color: pal.textMuted,
    borderBottom: `1px solid ${pal.border}`, whiteSpace: 'nowrap',
  }
  const td: React.CSSProperties = {
    textAlign: 'right', padding: '6px 10px', fontSize: 12,
    borderBottom: `1px solid ${wash(pal.ink, 0.035)}`, whiteSpace: 'nowrap',
  }

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <span className="micro-label">Trending OI — {index}</span>
        <select value={mins} onChange={e => setMins(+e.target.value)} style={{
          background: pal.inset, color: pal.textSecondary, fontSize: 11,
          border: `1px solid ${pal.border}`, borderRadius: 3, padding: '4px 7px',
        }}>
          {[5, 15, 30, 60].map(m => <option key={m} value={m}>{m} min</option>)}
        </select>
        <span style={{ fontSize: 11, color: pal.textMuted }}>
          {rows.length} mark{rows.length === 1 ? '' : 's'} · OI added since the open,
          summed over {(sel ?? avail).length || '—'} strikes
        </span>
        {sel && (
          <button onClick={() => setSel(null)} style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', padding: '3px 9px',
            borderRadius: 3, cursor: 'pointer', background: 'transparent',
            border: `1px solid ${pal.border}`, color: pal.textMuted,
          }}>ALL STRIKES</button>
        )}
      </div>

      {avail.length > 0 && (
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          {avail.map(k => {
            const on = (sel ?? avail).includes(k)
            return (
              <button key={k} onClick={() => toggle(k)} className="mono" style={{
                fontSize: 10.5, padding: '3px 8px', borderRadius: 3, cursor: 'pointer',
                background: on ? wash(pal.accent, 0.12) : 'transparent',
                border: `1px solid ${on ? wash(pal.accent, 0.45) : pal.border}`,
                color: on ? pal.accent : pal.textMuted,
              }}>{k}</button>
            )
          })}
        </div>
      )}

      {err ? (
        <div style={{
          background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
          padding: 20, fontSize: 13, color: pal.caution,
        }}>Trending OI unavailable — {err}. It needs the chain poller running.</div>
      ) : !rows.length && chainWhy ? (
        /* COULD NOT CHECK. The rows are empty because the chain feed behind
           them is down, so no mark is coming at the next boundary or any
           other. Saying "no marks yet" here is the lie this branch exists to
           prevent: on 2026-08-12 NIFTY's socket was dead from the open and
           this tab sent the operator away to wait for a 09:20 row that could
           never exist. The backend's own sentence is quoted, not paraphrased. */
        <div style={{
          background: pal.card, border: `1px solid ${pal.caution}`, borderRadius: 12,
          padding: 20, fontSize: 13, color: pal.caution,
        }}>
          Trending OI padha hi nahi ja saka — {index} ka chain feed neeche hai.
          <div style={{ marginTop: 6, color: pal.textSecondary, fontSize: 12.5 }}>
            {chainWhy}
          </div>
          <div style={{ marginTop: 6, color: pal.textMuted, fontSize: 12 }}>
            Ye "abhi tak koi mark nahi" nahi hai — jab tak feed wapas nahi aata,
            agle boundary par bhi koi row nahi banegi.
          </div>
        </div>
      ) : !rows.length ? (
        /* CHECKED, NOTHING YET. Only reachable with a HEALTHY chain, so the
           "wait for the boundary" promise is one this screen can keep. */
        <div style={{
          background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
          padding: 20, fontSize: 13, color: pal.textMuted,
        }}>No marks yet — the first row appears at the next {mins}-minute boundary.</div>
      ) : (
        <div style={{
          background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
          overflowX: 'auto',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ ...th, textAlign: 'left' }}>Time</th>
                {/* Frame discipline: this LTP is the index print the chain
                    poller logs, not the futures tape the glance bar shows —
                    the two can sit 70+ points apart, so the frame is named. */}
                <th style={th}>LTP · IDX</th>
                <th style={{ ...th, textAlign: 'center' }}>Break</th>
                <th style={th}>Call OI added</th>
                <th style={th}>Put OI added</th>
                <th style={th}>Diff</th>
                <th style={{ ...th, textAlign: 'center' }}>Strength</th>
                <th style={th}>Chg in dir</th>
                <th style={th}>Dir %</th>
                <th style={th}>PCR</th>
                <th style={{ ...th, textAlign: 'center' }}>Sentiment</th>
              </tr>
            </thead>
            <tbody>
              {[...rows].reverse().map(r => {
                const bull = r.sentiment === 'BULLISH'
                const bear = r.sentiment === 'BEARISH'
                // `baseline` is the ENGINE saying this mark is the session's
                // zero point rather than a reading (chain_metrics.oi_flow):
                // call/put are cumulative day OI change, so the first mark is
                // zero by construction. The UI must not infer that from 0/0 —
                // mid-session that is a real reading of "nothing was added".
                //
                // Muted, never green/red: theme.ts reserves those for
                // DIRECTION, and the absence of a reading has no direction.
                // That also fixes NEUTRAL, which fell to the bear branch and
                // so painted red on a red wash — the one row that means "no
                // signal" was the one shouting bearish.
                const sTone = r.baseline || !(bull || bear) ? pal.textMuted
                  : bull ? pal.bull : pal.bear
                const sCol = r.diff > 0 ? pal.bull : r.diff < 0 ? pal.bear : pal.textMuted
                const dCol = (r.chg_dir ?? 0) > 0 ? pal.bull : (r.chg_dir ?? 0) < 0 ? pal.bear : pal.textMuted
                return (
                  <tr key={r.time}>
                    <td className="mono" style={{ ...td, textAlign: 'left', color: pal.textSecondary }}>{r.time}</td>
                    <td className="mono" style={td}>{r.ltp?.toFixed(2) ?? '—'}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      {r.brk ? (
                        <span className="mono" style={{
                          fontSize: 9.5, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
                          color: r.brk === 'DHB' ? pal.bull : pal.bear,
                          background: r.brk === 'DHB' ? wash(pal.bull, 0.12) : wash(pal.bear, 0.12),
                        }}>{r.brk} {r.brk_px}</span>
                      ) : <span style={{ color: pal.textMuted }}>·</span>}
                    </td>
                    <td className="mono" style={td}>{inr(r.call)}</td>
                    <td className="mono" style={td}>{inr(r.put)}</td>
                    <td className="mono" style={{ ...td, color: sCol, fontWeight: 600 }}>{inr(r.diff)}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      <span className="mono" style={{
                        fontSize: 10.5, fontWeight: 700, padding: '2px 7px', borderRadius: 10,
                        color: sCol, border: `1px solid ${sCol}55`,
                      }}>{r.strength > 0 ? '+' : ''}{Math.round(r.strength * 100)}%</span>
                    </td>
                    <td className="mono" style={{ ...td, color: dCol }}>
                      {r.chg_dir == null ? '—' : (r.chg_dir > 0 ? '▲ ' : '▼ ') + inr(Math.abs(r.chg_dir))}
                    </td>
                    <td className="mono" style={{ ...td, color: dCol }}>
                      {r.chg_dir_pct == null ? '—' : `${(r.chg_dir_pct * 100).toFixed(1)}%`}
                    </td>
                    <td className="mono" style={td}>{r.pcr?.toFixed(2) ?? '—'}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      <span
                        title={r.baseline
                          ? 'The session’s zero point, not a reading — call and put '
                            + 'are cumulative OI change since the open, so the first mark '
                            + 'is zero by construction.'
                          : undefined}
                        style={{
                          fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                          padding: '2px 8px', borderRadius: 3,
                          color: sTone, background: wash(sTone, 0.12),
                        }}>{r.baseline ? 'BASELINE' : r.sentiment}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <div style={{ fontSize: 11, color: pal.textMuted, maxWidth: '78ch' }}>
        Each row is the chain <b>as at</b> that mark, not an average of the
        interval after it. Diff = put minus call; strength divides it by the
        larger leg; "chg in dir" is how far Diff moved since the previous mark.
      </div>
    </div>
  )
}

/* ── ANSWER band ───────────────────────────────────────────────────────────
   Always visible, above the tabs. v2 inherited v1's worst structural habit:
   the read lived behind a tab, so the one thing worth seeing on a live tape
   took a click to reach. Price, the verdict, the sentence and — crucially —
   what would invalidate it now own the top of the screen at a scale nothing
   else competes with. Everything below is evidence for this band.          */
function AnswerBand({ index, stale }: { index: IndexKey; stale: boolean }) {
  const { INDICES, READS, CHAIN_DATA, KEY_LEVELS } = useData()
  const pal = usePalette()
  const info = INDICES[index]
  const read = READS[index]
  const chain = CHAIN_DATA[index]
  const levels = KEY_LEVELS[index] ?? []
  const has = hasRead(info)

  const dirCol = info.change > 0 ? pal.bull : info.change < 0 ? pal.bear : pal.textSecondary
  const above = levels.filter(l => l.value > info.price).sort((a, b) => a.value - b.value)[0]
  const below = levels.filter(l => l.value < info.price).sort((a, b) => b.value - a.value)[0]
  const mpDist = Math.round(chain.maxPain - info.price)

  const chip = (label: string, tone: 'structure' | 'quiet' = 'quiet') => (
    <span key={label} className="mono" style={{
      fontSize: 10.5, letterSpacing: '0.05em', padding: '3px 8px', borderRadius: 3,
      whiteSpace: 'nowrap',
      border: `1px solid ${tone === 'structure' ? wash(pal.accent, 0.45) : pal.border}`,
      color: tone === 'structure' ? pal.accent : pal.textMuted,
    }}>{label}</span>
  )

  return (
    <div style={{ backgroundColor: pal.bg, borderBottom: `1px solid ${pal.border}`, flexShrink: 0 }}>
      {/* Grid lives in index.css (.answer-band) because it needs a breakpoint
          and an inline style cannot carry one — see the note there. */}
      <div className="answer-band">
        <div style={{ whiteSpace: 'nowrap' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <div className="mono" style={{
              fontSize: 32, lineHeight: 1, fontWeight: 600, letterSpacing: '-0.02em',
              // a price you cannot trust must not look like one you can
              color: stale ? pal.textMuted : pal.textPrimary,
              textDecoration: stale ? 'line-through' : 'none',
            }}>
              {has ? info.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
            </div>
            {/* Frame discipline: this is the futures tape, and OI Flow's LTP
                column is the index print — 70+ points apart some afternoons.
                Both carry their frame so neither reads as the other. */}
            <span title="Futures frame — the tape this app draws"
              style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: pal.textMuted }}>
              FUT
            </span>
          </div>
          <div className="mono" style={{ fontSize: 12, color: stale ? pal.textMuted : dirCol, marginTop: 5 }}>
            {!has ? 'not shown' : stale ? 'not live' : `${info.change > 0 ? '+' : ''}${info.change.toFixed(2)} · ${info.pct > 0 ? '+' : ''}${info.pct.toFixed(2)}%`}
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          {stale ? (
            <div style={{
              fontSize: 11, letterSpacing: '0.15em', textTransform: 'uppercase',
              color: pal.bear, fontWeight: 700, marginBottom: 4,
            }}>
              No live data — do not trade from this screen
            </div>
          ) : has && (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6 }}>
              <DirectionChip value={read.direction} />
              <TimingChip value={read.timing} />
            </div>
          )}
          <div style={{ fontSize: 14.5, lineHeight: 1.45, maxWidth: '62ch' }}>
            {read.headline}
          </div>
          {has && <Grounds g={read.ground} />}
          {read.sub && (
            <div style={{ fontSize: 12.5, color: pal.textSecondary, marginTop: 3 }}>{read.sub}</div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 5, alignItems: 'flex-end' }}>
          {has && <>
          {chip(`MAX PAIN ${chain.maxPain} · ${mpDist >= 0 ? '+' : ''}${mpDist}`, 'structure')}
          {/* A GEX reading without "where is price relative to the books" is
              the single most misleading number on the screen. */}
          {chain.inBookZone
            ? chip(`GEX ${chain.gex} · in book zone`)
            : chip(`GEX ${chain.gex} · OUTSIDE BOOKS — SNAP-BACK RISK`, 'structure')}
          {chip(`PCR ${chain.pcr} · SQUEEZE ${chain.squeeze}`)}
          </>}
        </div>
      </div>

      <div style={{
        display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap',
        padding: '8px 24px', backgroundColor: pal.card,
        borderTop: `1px solid ${pal.border}`, fontSize: 12.5,
      }}>
        <span className="micro-label" style={{ whiteSpace: 'nowrap' }}>Changes if</span>
        {!has ? <span style={{ color: pal.textMuted }}>{NOT_SHOWN}</span> : <>
        {above
          ? <span>breaks <span className="mono" style={{ color: pal.accent }}>{above.value}</span>
              <span style={{ color: pal.textMuted }}> ({above.label}{above.note ? ` · ${above.note}` : ''})</span></span>
          : <span style={{ color: pal.textMuted }}>no level mapped above</span>}
        <span style={{ color: pal.textMuted }}>·</span>
        {below
          ? <span>or loses <span className="mono" style={{ color: pal.accent }}>{below.value}</span>
              <span style={{ color: pal.textMuted }}> ({below.label}{below.note ? ` · ${below.note}` : ''})</span></span>
          : <span style={{ color: pal.textMuted }}>no level mapped below</span>}
        </>}
      </div>
    </div>
  )
}

/* ── Machine strip ──────────────────────────────────────────────────────────
   PRODUCT.md's five-state machine, surfaced at SHELL level. Until now the
   machine's current state lived only inside Trade → SetupCheck, so from any
   other tab — or any other window — an ARM changed nothing glanceable. This
   strip renders on every tab, under the ANSWER band, and document.title
   mirrors it (see App) so the browser tab itself announces ARMED.

   It READS `run_state`; it does not run a second copy of the machine — the
   same contract SetupCheck states at its top. Side pick is SetupCheck's rule
   verbatim: the side with something happening wins, BUY (the scored side)
   wins ties, and a shown SELL is named so it can never borrow the buy rule's
   measured hit rate. All prices here are futures-frame — the same frame as
   the chart these levels are drawn on. */

/* `liveMachine`, `MACHINE_WORDS` and `machineWord` moved to ./machine.ts —
   unchanged — so the Glass board's MACHINE widget can read the machine the
   same single way this strip does. */

function MachineStrip({ runState, runStateWhy, runStateSell, lastBar, stale, replaying }: {
  runState: RunState[] | null
  runStateWhy: string
  runStateSell: RunState[] | null
  lastBar: TapeBar | null
  stale: boolean
  replaying: boolean
}) {
  const pal = usePalette()
  const f1 = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(1))
  const { st, showSell, bothLive } = liveMachine(runState, runStateSell)
  const current = st ? machineWord(st) : null

  // The one advancing number per state. WAITING's is the number this screen
  // has never printed: how far price is from d3.
  let detail: string
  if (stale) {
    // Distinct sentence #2: could not check. Placeholder bars must not be
    // read as a machine state.
    detail = 'koi live tape nahi — machine padh nahi sakte'
  } else if (!st) {
    // SetupCheck's own words for the same absence — one sentence, two panels.
    detail = `Setup ki haalat nahi aa rahi${runStateWhy ? ` — ${runStateWhy}` : ''}`
  } else if (current === 'BAAHAR') {
    // The LOCK opened, not a trade. See machine.ts's lockNote.
    detail = `re-fire lock khula — ${lockNote(st)} · agla setup arm ho sakta hai`
  } else if (current === 'WAITING') {
    detail = lastBar
      ? `d2 ${f1(lastBar.d2)} · u2 ${f1(lastBar.u2)} · price ${f1(lastBar.c)}`
      : 'd2 — · koi bar nahi'
  } else if (current === 'ARMED') {
    detail = `todna ${showSell ? '<' : '>'} ${f1(showSell ? st.ref_low : st.ref_high)}`
      + ` · ${st.candles_left != null ? `${st.candles_left} candle baaki` : 'window —'}`
  } else if (current === 'TRIGGERED') {
    detail = `entry hui · stop ${f1(st.stop)}`
  } else {
    // TRADE MEIN — VWAP is the first milestone, then band-to-band.
    detail = `pehla milestone VWAP ${f1(lastBar?.vwap)} · stop ${f1(st.stop)}`
  }

  const unreadable = !stale && st != null && !st.readable

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      padding: '6px 24px', backgroundColor: pal.bg,
      borderBottom: `1px solid ${pal.border}`,
    }}>
      <span className="micro-label" style={{ whiteSpace: 'nowrap' }} title="THE ZONE machine: d2→d3 buy, u2→u3 sell (CLAUDE.md rule 3) — the setup VALIDATE reads">Zone machine</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }} aria-live="polite">
        {MACHINE_WORDS.map((w, i) => {
          const lit = !stale && w === current
          return (
            <span key={w} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {i > 0 && <span aria-hidden="true" style={{ color: pal.textMuted, opacity: 0.45, fontSize: 10 }}>→</span>}
              <span style={{
                fontSize: 11, fontWeight: lit ? 700 : 500, letterSpacing: '0.07em',
                padding: '2px 8px', borderRadius: 4, whiteSpace: 'nowrap',
                // Brass, not green/red: a machine state is structure, not a
                // directional call. WAITING lights quietly — context, not
                // signal.
                color: lit ? (w === 'WAITING' ? pal.textPrimary : pal.accent) : pal.textMuted,
                border: `1px solid ${lit ? (w === 'WAITING' ? wash(pal.ink, 0.18) : wash(pal.accent, 0.55)) : 'transparent'}`,
                backgroundColor: lit && w !== 'WAITING' ? wash(pal.accent, 0.10) : 'transparent',
                opacity: lit ? 1 : 0.75,
              }}>{w}</span>
            </span>
          )
        })}
      </div>
      {showSell && st && (
        <span title="zone SELL (u2→u3) — unscored, pre-registered; no rate of any kind belongs next to it" style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', padding: '1px 7px',
          borderRadius: 4, border: `1px solid ${pal.border}`, color: pal.textSecondary,
        }}>SELL · u2→u3</span>
      )}
      {bothLive && (
        <span style={{ fontSize: 10.5, color: pal.textSecondary }}>· SELL side bhi live hai — Trade tab dekho</span>
      )}
      <span className="mono" style={{
        fontSize: 11.5, whiteSpace: 'nowrap',
        color: stale ? pal.caution : !st ? pal.caution : current === 'WAITING' ? pal.textSecondary : pal.textPrimary,
      }}>{detail}</span>
      {unreadable && (
        <span style={{ fontSize: 10.5, color: pal.caution }}>· is bar ka read nahi mila</span>
      )}
      {replaying && (
        <span title="Replay chal raha hai — ye strip phir bhi LIVE tape padhti hai, scrub nahi" style={{
          marginLeft: 'auto', fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
          padding: '1px 7px', borderRadius: 4,
          border: `1px solid ${wash(pal.accent, 0.5)}`, color: pal.accent,
        }}>LIVE</span>
      )}
    </div>
  )
}

export default function App() {
  const pal = usePalette()
  const [activeIndex, setActiveIndex] = useState<IndexKey>('NIFTY')
  const [activeTab, setActiveTab] = useState<Tab>('Heat')
  // FOCUS: while on and the Trade tab is active, hide the glance bar + ANSWER
  // band so the chart reclaims that ~417px of chrome (Kite gives the chart
  // nearly the whole viewport; this dashboard didn't). Persisted in
  // localStorage — defaults OFF so nothing changes for anyone who hasn't
  // opted in.
  const [focus, setFocusState] = useState<boolean>(() => localStorage.getItem('tape.focus') === '1')
  const setFocus = (v: boolean) => { localStorage.setItem('tape.focus', v ? '1' : '0'); setFocusState(v) }
  const focusHidesChrome = focus && activeTab === 'Trade'
  // BOARD rev 3's shell (notes §8 step 1), the Board tab ONLY: the board is
  // its own answer, so the global ANSWER band, the MACHINE strip and the
  // tape's replay bar (the board never follows it) step aside for its
  // 1536 × 577, and the GlanceBar carries each index's one-line board read.
  // Every other tab keeps all three exactly as before.
  const onBoard = activeTab === 'Board'
  // The Validate tab is its own answer too: the hold window's check never shows the engine's
  // headline (docs/hold/PREREG-merged.md §5), so the ANSWER band and the replay bar step aside
  // there, as on the Board. The MACHINE strip stays: it is her setup.
  const onValidate = activeTab === 'Validate'
  const boardReads = useBoardGlance(onBoard)
  const tabs: Tab[] = ['Board', 'Glass', 'Heat', 'Trade', 'Tape', 'Flow', 'VPIN', 'Chain', 'OI Flow', 'War', 'Events', 'Validate', 'Map', 'Signals']
  const { data: liveData, loading, error, errorWhy, broker, lastUpdated, barCount, at, dead, tapeBars,
          interval, setInterval: setInterval_ } = useLiveData(EMPTY)
  const idxDead = dead.includes(activeIndex)

  // ── Replay. scrub === null means live. Re-maps stored payloads; no refetch.
  const [scrub, setScrub] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(8)
  const nBars = barCount(activeIndex)
  /** Switching interval rebuilds the tape with a different number of bars, so
   *  a scrub index from the old one names a different minute (bar 200 of 385
   *  is 12:35; of 129 it does not exist). Drop back to live rather than
   *  silently re-point it: a replay frame that moved without being asked to is
   *  the same lie as a marker drawn one bar off. */
  const changeInterval = useCallback((n: Interval) => {
    setScrub(null)
    setPlaying(false)
    setInterval_(n)
  }, [setInterval_])
  const data = useMemo(() => at(scrub), [scrub, liveData])
  const tape = useMemo(() => tapeBars(activeIndex), [tapeBars, activeIndex, liveData])
  // MAP levels are bar-derived and causal under replay. MAX PAIN and GEX FLIP
  // come from the chain, which is a live snapshot with no per-strike history
  // (the same reason Chain.aligned goes false while scrubbing) — so they are
  // drawn only when live, never during replay (honesty rule 6).
  // VWAP and the ±1σ bands are DROPPED from the chart's level list, by the
  // operator's instruction 2026-08-11 and again 2026-08-12: "there are lines
  // for vwap and +1 std deviation as well not required at all because i can
  // see there levels on the right side of chart". Those two arrive as MAP
  // LEVELS -- horizontal lines with a price chip -- built in data.ts
  // (`addLvl(f.vwap, 'VWAP', 'vwap' …)`, `addLvl(f.u1, '+1σ', 'band' …)`).
  // They are a SEPARATE layer from the VWAP polyline and the σ ribbon edges
  // that came off earlier; removing those left these standing, which is why
  // the chart still drew them after the first pass.
  //
  // Filtered HERE, at the chart's boundary, rather than in data.ts: the Map
  // tab reads the same array as a table, where a named level with its price
  // is the entire point and costs no chart ink. Pivots, MAX PAIN, PIN, walls,
  // CAP/FLR, HI/LO, STK and traps all stay -- the operator named those as
  // the ones to keep.
  const tradeLevels = useMemo(() => {
    const lv = [...(data.MAP[activeIndex]?.levels ?? [])]
      .filter((l) => l.kind !== 'vwap' && l.kind !== 'band')
    if (scrub == null) {
      const ch = data.CHAIN_DATA[activeIndex]
      if (ch && Number.isFinite(ch.maxPain) && ch.maxPain > 0)
        lv.push({ label: 'MAX PAIN', value: ch.maxPain, kind: 'strike', note: 'chain snapshot' })
      if (ch?.flipPx != null && ch.flipPx > 0)
        lv.push({ label: 'GEX FLIP', value: ch.flipPx, kind: 'strike', note: 'chain snapshot' })
    }
    return lv
  }, [data, activeIndex, scrub])
  const barTime = data.CHART_DATA[activeIndex]?.slice(-1)[0]?.time ?? '--:--'

  // A stale chain is a separate failure from a dead tape or an unreachable
  // backend: the futures tape can keep ticking normally while the option
  // poller is hung, and MAX PAIN/GEX/PCR quietly render minutes-old numbers
  // as if current. `builtAt` is the trustworthy signal for that — `null`
  // means an older backend never sent it, which must read as "unknown", not
  // "fresh", so the banner only fires once age is actually known and past
  // the threshold.
  const activeChain = data.CHAIN_DATA[activeIndex]
  const chainAge = chainAgeS(activeChain)
  const chainStale = chainAge != null && chainAge > CHAIN_STALE_S

  // Mirror the machine into the browser tab title, so ARMED is visible from
  // Kite or TradingView without TapeMap being the front window. Same state
  // pick as the strip (liveMachine — one definition). A dead tape or a dead
  // backend must NOT title-flash a placeholder machine, so those fall back to
  // the plain title.
  useEffect(() => {
    let title = 'TapeMap — Live'
    if (!error && !idxDead) {
      const { st } = liveMachine(tape.zoneState, tape.zoneStateSell)     // the zone: her setup (rule 3)
      if (st) {
        const w = machineWord(st)
        if (w === 'ARMED') title = `● ARMED · ${st.candles_left != null ? `${st.candles_left} baaki` : 'window —'} — TapeMap`
        else if (w === 'TRIGGERED') title = '●● TRIGGERED — TapeMap'
        else if (w === 'TRADE MEIN') title = '● TRADE MEIN — TapeMap'
        // Not "BAAHAR (vwap)" — from a browser tab that read as "you are out
        // at VWAP". The lock opening is the fact; the exit is the operator's.
        else if (w === 'BAAHAR') title = `LOCK OPEN · ${st.exit_why} — TapeMap`
      }
    }
    document.title = title
    return () => { document.title = 'TapeMap — Live' }
  }, [tape, error, idxDead])

  useEffect(() => {
    if (!playing || scrub == null) return
    const id = setInterval(() => {
      setScrub((s) => {
        if (s == null) return s
        if (s >= nBars - 1) { setPlaying(false); return s }
        return s + 1
      })
    }, Math.max(40, 1000 / speed))
    return () => clearInterval(id)
  }, [playing, speed, scrub == null, nBars])

  return (
    <DataCtx.Provider value={data}>
    <div style={{ minHeight: '100vh', backgroundColor: pal.bg, display: 'flex', flexDirection: 'column' }}>
      {/* FOCUS hides only the glance bar + ANSWER band, and only on the Trade
          tab — every safety banner below (NOT LIVE / NO {index} TAPE / CHAIN
          STALE) still renders unconditionally: buying chart pixels by hiding
          a staleness disclosure is the one trade this tool refuses to make. */}
      {!focusHidesChrome && (
        <GlanceBar active={activeIndex} setActive={setActiveIndex} lastUpdated={lastUpdated} error={error}
          reads={onBoard ? boardReads : undefined} />
      )}

      {/* A trading screen must never present stale numbers as live. The
          moment every index fails, say so at full width instead of showing a
          small "reconnecting" chip beside believable-looking prices. */}
      {error && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.bear, 0.12),
          borderBottom: `1px solid ${pal.bear}`, color: pal.bear,
          fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
          display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap',
        }}>
          <span style={{ marginRight: 12 }}>
            {error === 'unreachable'
              ? 'NOT LIVE — no answer from the backend on 8765, so nothing below is live '
                + '(the last good read, or not shown). Run stop.bat, then the TapeMap v2 shortcut again.'
              : `NOT LIVE — the backend is up${broker ? ` on ${broker}` : ''} but has no `
                + `session yet${errorWhy ? `: ${errorWhy}` : ''}. Nothing below is live `
                + '(the last good read, or not shown).'}
          </span>
          {/* The button only appears where it can actually change something.
              It cannot reach a backend that is not answering; and on Upstox
              server.py refuses the write outright, because the running tape
              and chain read .upstox_token and only `python upstox_auth.py`
              refreshes it. Offering it anyway is how a screen at 02:50 came
              to blame an expired Dhan token for a market that had not opened. */}
          {error === 'no-data' && broker !== 'upstox' && <TokenCapture tone="loud" />}
        </div>
      )}

      {/* One index can be down while the others are fine — say which. */}
      {!error && idxDead && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.caution, 0.12),
          borderBottom: `1px solid ${pal.caution}`, color: pal.caution,
          fontSize: 12.5, fontWeight: 600,
        }}>
          NO {activeIndex} TAPE — the backend has no session for this index, so the
          figures below are not live (the last good read, or not shown). {dead.length < 3 && 'The other indices are live.'}
        </div>
      )}

      {/* The tape can be perfectly live while the option-chain poller hangs —
          that gap is invisible unless it is called out on its own, separate
          from the "backend unreachable" banner above (which already covers
          this ground when it fires, so this stays silent then). */}
      {!error && chainStale && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.caution, 0.12),
          borderBottom: `1px solid ${pal.caution}`, color: pal.caution,
          fontSize: 12.5, fontWeight: 600,
        }}>
          CHAIN STALE — last option-chain snapshot {activeChain.ts || '--:--:--'} ({Math.floor((chainAge as number) / 60)}m old).
          Max pain, GEX, PCR and the chain-derived chart levels below are from that moment, not now.
          Candles, VWAP and the σ bands are unaffected.
        </div>
      )}

      {!focusHidesChrome && !onBoard && !onValidate && (
        <AnswerBand index={activeIndex} stale={!!error || idxDead} />
      )}

      {/* The machine strip renders on every tab, and even under FOCUS. It is
          the product's spine, and the one row that must never be traded away
          for chart pixels. The one exception is the Board tab, by her own
          spec (BOARD rev 3 §8 step 1); the browser-tab title still mirrors
          the machine there. */}
      {!onBoard && <MachineStrip
        runState={tape.zoneState}
        runStateWhy={tape.zoneStateWhy}
        runStateSell={tape.zoneStateSell}
        lastBar={tape.bars.length ? tape.bars[tape.bars.length - 1] : null}
        stale={!!error || idxDead}
        replaying={scrub != null}
      />}

      {/* Tab bar */}
      <div role="tablist" aria-label="TapeMap panels" style={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        padding: '0 24px',
        backgroundColor: pal.card,
        borderBottom: `1px solid ${pal.border}`,
      }}>
        {tabs.map(tab => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '12px 16px',
              fontSize: 13,
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? pal.textPrimary : pal.textMuted,
              backgroundColor: 'transparent',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              borderBottom: `2px solid ${activeTab === tab ? pal.accent : 'transparent'}`,
              cursor: 'pointer',
              transition: 'all 150ms',
              letterSpacing: '0.01em',
            }}
          >
            {tab}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: 11, color: pal.textMuted }}>
          <span className="mono">{lastUpdated ? lastUpdated.toLocaleTimeString('en-GB') : '—'}</span> IST
        </div>
      </div>

      {/* Replay transport. Hidden until there are bars to scrub. */}
      {nBars > 1 && !onBoard && !onValidate && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '8px 24px',
          borderBottom: `1px solid ${pal.border}`,
          backgroundColor: scrub == null ? pal.bg : wash(pal.accent, 0.07),
        }}>
          <button
            onClick={() => {
              if (scrub == null) { setScrub(Math.max(0, nBars - 60)); setPlaying(true) }
              else setPlaying(!playing)
            }}
            title={scrub == null ? 'Replay the last hour' : playing ? 'Pause' : 'Play'}
            style={{
              width: 30, height: 26, borderRadius: 3, cursor: 'pointer',
              background: 'transparent', border: `1px solid ${pal.border}`,
              color: pal.textPrimary, fontSize: 12,
            }}
          >{playing ? '❚❚' : '▶'}</button>

          <select value={speed} onChange={(e) => setSpeed(+e.target.value)}
            style={{
              background: pal.inset, color: pal.textSecondary, fontSize: 11,
              border: `1px solid ${pal.border}`, borderRadius: 3, padding: '4px 6px',
            }}>
            {[1, 3, 8, 25].map(s => <option key={s} value={s}>{s}×</option>)}
          </select>

          <span className="mono" style={{
            fontSize: 12, color: scrub == null ? pal.textMuted : pal.accent,
            minWidth: 46, fontWeight: 600,
          }}>{barTime}</span>

          <input
            type="range" min={0} max={Math.max(0, nBars - 1)}
            value={scrub == null ? nBars - 1 : scrub}
            onChange={(e) => { setScrub(+e.target.value); setPlaying(false) }}
            aria-label="Replay position"
            style={{ flex: 1, accentColor: pal.accent, cursor: 'pointer' }}
          />

          {scrub == null ? (
            <span className="mono" style={{ fontSize: 10.5, color: pal.textMuted, letterSpacing: '0.06em' }}>
              LIVE
            </span>
          ) : (
            <button
              onClick={() => { setScrub(null); setPlaying(false) }}
              style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
                padding: '4px 10px', borderRadius: 3, cursor: 'pointer',
                background: 'transparent', border: `1px solid ${pal.accent}`, color: pal.accent,
              }}
            >RETURN TO LIVE</button>
          )}
        </div>
      )}

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {/* key={activeIndex} for the same reason TradeTab carries one: the
            chart engine is rebuilt per contract rather than mutated across an
            index switch. Passed the SAME tape/chain/level props TradeTab gets,
            from the same memos — one payload, two presentations. */}
        {/* The board reads the glance-bar's active index all the way down —
            key={activeIndex} so a switch remounts it rather than letting a
            pane paint the previous index's figures for one frame. */}
        {activeTab === 'Glass'    && <GlassBoard key={activeIndex} index={activeIndex}
                                              chain={activeChain} bars={tape.bars}
                                              runState={tape.zoneState}
                                              runStateWhy={tape.zoneStateWhy}
                                              runStateSell={tape.zoneStateSell}
                                              publishedInterval={tape.interval}
                                              stale={idxDead || !!error} loading={loading}
                                              chainStale={chainStale}
                                              setActiveTab={setActiveTab} />}
        {activeTab === 'Heat'     && <HeatTab active={activeIndex} setActive={setActiveIndex} dead={dead} />}
        {activeTab === 'Trade'    && <TradeTab key={activeIndex} index={activeIndex} day={tape.day} bars={tape.bars}
                                              chain={activeChain} strike={tape.strike}
                                              optPivots={tape.optPivots} optExpiry={tape.optExpiry}
                                              levels={tradeLevels} events={data.EVENTS_BY_IDX[activeIndex]} cursor={scrub}
                                              stale={idxDead || !!error} loading={loading} chainStale={chainStale}
                                              chainTs={activeChain.ts}
                                              focus={focus} onFocusToggle={() => setFocus(!focus)}
                                              onIndexChange={setActiveIndex}
                                              interval={interval} publishedInterval={tape.interval}
                                              onIntervalChange={changeInterval}
                                              structures={tape.structures}
                                              structuresWhy={tape.structuresWhy}
                                              rotation={tape.rotation}
                                              rotationWhy={tape.rotationWhy}
                                              rotationRun={tape.rotationRun}
                                              rotationRunWhy={tape.rotationRunWhy}
                                              rotationRunSell={tape.rotationRunSell}
                                              rotationRunSellWhy={tape.rotationRunSellWhy}
                                              runState={tape.runState}
                                              runStateWhy={tape.runStateWhy}
                                              runStateSell={tape.runStateSell} />}
        {/* key={activeIndex}: the pins are per index, so a switch starts on ATM. */}
        {activeTab === 'Tape'     && <TapeTab index={activeIndex} />}
        {/* Mounted only while active, which is also what stops its 30s poll:
            the tab unmounts and the interval is cleared with it. */}
        {activeTab === 'Board'    && <BoardRev3 key={activeIndex} index={activeIndex} />}
        {activeTab === 'Flow'     && <FlowTab index={activeIndex} />}
        {activeTab === 'VPIN'     && <VpinTab key={activeIndex} index={activeIndex} />}
        {activeTab === 'Chain'    && <ChainTab index={activeIndex} />}
        {activeTab === 'OI Flow'  && <OiFlowTab index={activeIndex} />}
        {/* Mounted only while active, which is also what stops its 30s poll. */}
        {activeTab === 'War'      && <WarTab index={activeIndex} />}
        {activeTab === 'Events'   && <EventsTab index={activeIndex} />}
        {/* the hold window's permanent home: check before the trade, hold it after (docs/hold/) */}
        {activeTab === 'Validate' && <HoldTab key={activeIndex} index={activeIndex} chain={activeChain} onIndex={setActiveIndex} />}
        {activeTab === 'Map'      && <MapTab index={activeIndex} />}
        {/* No `index` prop, deliberately: the log spans all three indices and
            the operator tracks the strategy, not one tape. The tab carries its
            own index filter, which starts on ALL. */}
        {activeTab === 'Signals'  && <SignalsTab />}
      </div>
      <HoldWindow hidden={onValidate} />
    </div>
    </DataCtx.Provider>
  )
}
