import { Fragment, useMemo } from 'react'
import type { ReactNode } from 'react'
import { palette, useMode } from '../theme'
import type { Palette } from '../theme'
import { liveMachine, machineWord, MACHINE_WORDS, lockNote } from '../machine'
import { useFlow } from '../trade/flow'
import { crl } from '../trade/ZoneRead'
import { useChainWire, flipReason } from './wire'
import {
  GlassCard, Absent, FrameBadge, labelInk, useGlassOrder, useGlassDrag,
  Hero, Chip, Receipts, Rail, Meter, wash, hair, inkOf,
} from './glass'
import type { RailMark, RailZone, MeterTick, Lean } from './glass'
import type { Chain, IndexKey, RunState, TapeBar, FlowRow } from '../data'
import { SCORED_INTERVAL } from '../data'
import type { Tab } from '../App'

/**
 * THESIS — A glance-board of glass instruments, each one a launcher into its
 * own evidence. It refuses the category default: a wall of equal-weight charts
 * that all demand reading at once. Here one thing is the hero and the rest are
 * dials you tap.
 *
 * OWN-WORLD — Apple liquid glass floating on an ambient field. Brass stays
 * structure, green and red stay direction, and the glass itself is neither.
 *
 * STORY — The operator glances, reads the machine first, and taps whichever
 * dial disagrees with it to interrogate it on the tab that owns the evidence.
 *
 * FIRST VIEWPORT — MACHINE as a two-column hero, then seven instruments in a
 * movable grid. Nothing needs a scroll to be seen.
 *
 * FINISH — Unreviewed and undocumented is unfinished.
 */

/* ── What this board refuses to do ───────────────────────────────────────────
 * The setup fires once or twice a week. WAITING is the majority state, so the
 * calm state is the DESIGNED state — no pulsing, no red, no urgency furniture
 * that would have to be ignored six days out of seven.
 *
 * Every figure below is read, never derived. Where a field is null the pane
 * prints which KIND of absence it is and the reason the backend published,
 * because "balanced" and "we could not look" are not the same sentence.
 */

interface Props {
  index: IndexKey
  chain: Chain
  bars: TapeBar[]
  runState: RunState[] | null
  runStateWhy: string
  runStateSell: RunState[] | null
  /** The interval, in minutes, the backend says these bars ARE. The MACHINE
   *  pane reads the same `run_state` the Trade tab does, so it must not imply
   *  a scored setup on candles §5c was never measured on. null reads as
   *  unknown, and unknown is not the scored interval. */
  publishedInterval: number | null
  /** No live tape for this index, or the backend is down. */
  stale: boolean
  loading: boolean
  chainStale: boolean
  setActiveTab: (t: Tab) => void
}

const f1 = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(1))
const f0 = (n: number | null | undefined) =>
  n == null ? '—' : Math.round(n).toLocaleString('en-IN')
const signed = (n: number | null | undefined, d = 1) =>
  n == null ? '—' : `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(d)}`

/** Dealer-signed gamma. Large and unitless, so it is shown compactly and
 *  always signed — the SIGN is the whole read (positive dampens, negative
 *  amplifies) and must never be the thing that gets rounded away. */
const gexFmt = (n: number | null | undefined): string => {
  if (n == null || !Number.isFinite(n)) return '—'
  const s = n < 0 ? '−' : '+'
  const a = Math.abs(n)
  if (a >= 1e6) return `${s}${(a / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${s}${(a / 1e3).toFixed(0)}k`
  return `${s}${a.toFixed(0)}`
}

/** ABSOLUTE open interest in Indian units. Deliberately NOT `crl`, which is
 *  the day-CHANGE formatter and always prints a sign: "+2.3Cr" of standing OI
 *  would read as a delta that never happened. `crl` is still used verbatim for
 *  the Trending-OI row, which really is a day change. */
const oiAbs = (n: number | null | undefined): string => {
  if (n == null || !Number.isFinite(n)) return '—'
  const a = Math.abs(n)
  if (a >= 1e7) return `${(a / 1e7).toFixed(2)}Cr`
  if (a >= 1e5) return `${(a / 1e5).toFixed(1)}L`
  return a.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

/* ── Small parts ─────────────────────────────────────────────────────────── */

function Note({ children, pal, dark }: { children: ReactNode; pal: Palette; dark: boolean }) {
  return (
    <span style={{ fontSize: 11, lineHeight: 1.45, color: labelInk(pal, dark) }}>
      {children}
    </span>
  )
}

/** A padded domain around a set of levels. Every rail on this board is drawn to
 *  scale, which needs a window, and a window derived per-pane by hand is a
 *  window that ends up different on each of them. */
function domain(vals: Array<number | null | undefined>, padFrac = 0.16): [number, number] | null {
  const v = vals.filter((x): x is number => x != null && Number.isFinite(x))
  if (v.length < 2) return null
  const lo = Math.min(...v)
  const hi = Math.max(...v)
  const pad = Math.max((hi - lo) * padFrac, 1)
  return [lo - pad, hi + pad]
}

/* ── Where each pane's lean comes from ───────────────────────────────────────
 * A tint is an opinion, so none of these functions is allowed to form one.
 * Every branch below copies a direction the app ALREADY publishes or already
 * paints somewhere else, and cites where. Five of the eight panes come back
 * null, and that is the honest answer for them rather than a gap to fill.
 *
 * REFUSED, with the reason each was refused:
 *
 *   ATM open interest — the pane knows which side's book is heavier, and the
 *     app nowhere turns that into a direction. data.ts's heat tiles DO give
 *     CE/PE rows a `dir`, but from `prem_d` and `oi_slope` (premium moving,
 *     book building), never from which leg holds more standing OI. Inventing
 *     "PE-heavy = bullish" here would be this board's own new opinion.
 *
 *   Dealer gamma — POSITIVE/NEGATIVE is a statement about how dealer hedging
 *     BEHAVES (dampens, amplifies), not about which way price goes. data.ts
 *     only assigns gamma a direction through the engine's GAMMA-PIN regime
 *     string (FLOOR → bull, CEILING → bear) and pointedly returns 0 for
 *     PINNED because "dampens BOTH ways" is not a side. That regime string is
 *     not on /api/chain, so this pane has nothing to read.
 *
 *   Walls — data.ts files walls with `dir: 'up'/'down'`, then overwrites it
 *     (KEY_LEVELS) with the level's POSITION relative to price. It is where a
 *     level sits, not which way anything is going.
 *
 *   Σ bands — the app does state price-versus-VWAP as a trend, but only as the
 *     narration engine's TREND-UP / TREND-DOWN kind (hinglish.ts: "Bhaav
 *     lagatar VWAP ke upar chal raha hai"). That is a backend verdict over a
 *     run of bars, not `c > vwap` on one bar, and this pane receives the bar,
 *     not the verdict.
 *
 *   Basis — a carry to expiry. Nothing in the app calls it directional.
 */

/** MACHINE — the live side, and only once a side is actually live.
 *
 *  `liveMachine` already decides this: a side is live when it has left WAITING
 *  or has an exit, and BUY wins ties. BUY is the long — SetupCheck renders it
 *  as "Todna hai > X" with "Stop < X", a break upward with the stop beneath —
 *  and SELL is its mirror, "Todna hai < X" with "Stop > X". The app states the
 *  side; the side's direction is written into the app's own inequalities.
 *
 *  WAITING is neutral, which is the majority state and exactly right: nothing
 *  has happened yet, so the glass has nothing to lean about. */
const machineLean = (st: RunState | null, showSell: boolean, stale: boolean): Lean => {
  if (stale || !st) return null
  const live = st.state !== 'WAITING' || st.exit_why != null
  if (!live) return null
  return showSell ? 'bear' : 'bull'
}

/** TRENDING OI — the backend's own `sentiment` on the latest mark.
 *
 *  Verbatim from the OI Flow tab's rule (App.tsx), including its baseline
 *  guard and the comment it carries: NEUTRAL once fell to the bear branch
 *  there, so "the one row that means no signal was the one shouting bearish".
 *  A baseline row is the session's zero point by construction, not a reading,
 *  and gets no tint for the same reason it gets no colour there. */
const flowLean = (last: FlowRow | null): Lean => {
  if (!last || last.baseline) return null
  return last.sentiment === 'BULLISH' ? 'bull'
    : last.sentiment === 'BEARISH' ? 'bear' : null
}

/** PIN & PRESSURE — the squeeze side.
 *
 *  data.ts already paints this exact field green or red on the Heat tab:
 *  `dir: sqz.side === 'UP' ? 'bull' : sqz.side === 'DOWN' ? 'bear' : 'neutral'`.
 *  The backend is careful with it — `side` is null when no book qualifies and
 *  always null inside the expiry squaring window, "where chain-wide OI decay
 *  carries no direction" — so a null side is a deliberate silence and lands
 *  here as no tint. The pin distance itself stays directionless: max pain is
 *  structure, and above-or-below spot is a position, not a call. */
const pinLean = (side: string | null): Lean =>
  side === 'UP' ? 'bull' : side === 'DOWN' ? 'bear' : null

/** Ink that reads on a saturated direction bar in EITHER mode. White survives
 *  light-mode bear (#C42B30, 7.4:1) and bull (#1B8A38, 5.3:1); on the dark
 *  palette's much lighter #FF5F6B / #2EC27E it collapses to ~2:1, so dark flips
 *  to the page ink instead (8:1 and 9.5:1). One constant, both modes. */
const onBarInk = (dark: boolean) => (dark ? '#0B0E14' : '#FFFFFF')

/* ── Widgets ─────────────────────────────────────────────────────────────── */

type WireOf = ReturnType<typeof useChainWire>

function MachinePane({ pal, dark, stale, st, showSell, bothLive, why, lastBar,
                      publishedInterval }: {
  pal: Palette; dark: boolean; stale: boolean
  st: RunState | null; showSell: boolean; bothLive: boolean
  why: string; lastBar: TapeBar | null; publishedInterval: number | null
}) {
  const current = st ? machineWord(st) : null

  // The same two sentences the machine strip uses, verbatim. One condition
  // must not get two different explanations on two surfaces.
  if (stale) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why="koi live tape nahi — machine padh nahi sakte" />
  }
  if (!st) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why={`Setup ki haalat nahi aa rahi${why ? ` — ${why}` : ''}`} />
  }

  const idx = current ? MACHINE_WORDS.indexOf(current) : -1

  /* The hero: ONE advancing number per state, and the sentence it answers.
     WAITING — the majority state, six days in seven — is the gap to the edge,
     which is also the one thing the meter below can draw to scale. */
  let heroV = '—'
  let heroUnit = ''
  let heroCap = ''
  let heroTone: string | undefined
  if (current === 'BAAHAR') {
    // The lock, not the trade — see machine.ts's lockNote. This pane used to
    // hero "VWAP / par nikle / the run is closed", which told the operator
    // they were out at a price the tool never knew they took.
    heroV = 'LOCK'
    heroUnit = 'khula'
    heroCap = `${lockNote(st)} — agla setup arm ho sakta hai; trade tum khud chalate ho`
    heroTone = pal.accent
  } else if (current === 'WAITING') {
    heroV = lastBar ? signed(lastBar.c - lastBar.d3) : '—'
    heroUnit = 'pt to d3'
    heroCap = lastBar ? `price ${f1(lastBar.c)} · d3 ${f1(lastBar.d3)}` : 'koi bar nahi'
  } else if (current === 'ARMED') {
    heroV = f1(showSell ? st.ref_low : st.ref_high)
    heroUnit = showSell ? 'todna niche' : 'todna upar'
    heroCap = st.candles_left != null
      ? `${st.candles_left} candle baaki is window mein`
      : 'window — no candle count published'
    heroTone = pal.accent
  } else if (current === 'TRIGGERED') {
    heroV = f1(st.stop)
    heroUnit = 'stop'
    heroCap = 'entry ho gayi — ab stop hi sawaal hai'
    heroTone = pal.accent
  } else {
    heroV = f1(lastBar?.vwap)
    heroUnit = 'VWAP'
    heroCap = `pehla milestone · stop ${f1(st.stop)}`
    heroTone = pal.accent
  }

  /* The gap, drawn. d3 anchors the left edge; the nearest band ABOVE price
     anchors the right, so the meter's scale is the structure price is actually
     travelling between rather than an arbitrary window. Above u3 there is no
     next band, so the window opens a little past price and says so. */
  let meter: ReactNode = null
  if (lastBar) {
    const b = lastBar
    const up: Array<[string, number]> = [
      ['d2', b.d2], ['d1', b.d1], ['VWAP', b.vwap], ['u1', b.u1], ['u2', b.u2], ['u3', b.u3],
    ]
    const nextUp = up.find(([, v]) => v > b.c)
    const hi = nextUp ? nextUp[1] : b.c + Math.max(4, (b.u3 - b.d3) * 0.07)
    const lo = Math.min(b.d3, b.c) - Math.max(2, (hi - b.d3) * 0.08)
    const ticks: MeterTick[] = [
      { at: b.d3, label: `d3 ${f1(b.d3)}`, tone: pal.accent, strong: true },
    ]
    if (nextUp) ticks.push({ at: nextUp[1], label: `${nextUp[0]} ${f1(nextUp[1])}`, tone: pal.accent })
    meter = (
      <Meter
        lo={lo} hi={hi} ticks={ticks}
        marker={b.c} markerLabel={f1(b.c)}
        span={[b.d3, b.c]} spanTone={pal.accent}
        pal={pal} dark={dark} height={42}
      />
    )
  }

  return (
    <>
      {/* The rail. Five states, drawn at a size that makes the lit one a place
          the eye lands rather than a word in a sentence. Brass, never green or
          red: a machine state is structure, not a directional call, and
          WAITING lights quietly because it is context, not an event. */}
      <div style={{ display: 'flex', alignItems: 'stretch', minWidth: 0 }}>
        {MACHINE_WORDS.map((w, i) => {
          const lit = w === current
          const done = idx > i
          const quiet = lit && w === 'WAITING'
          return (
            <Fragment key={w}>
              {i > 0 && (
                <span aria-hidden="true" style={{
                  flex: '0 0 12px', alignSelf: 'center', height: 1,
                  background: done ? wash(pal.accent, 0.55) : hair(dark, 0.16),
                }} />
              )}
              <span style={{
                flex: 1, minWidth: 0, textAlign: 'center', whiteSpace: 'nowrap',
                overflow: 'hidden', textOverflow: 'ellipsis',
                fontSize: lit ? 12 : 11, fontWeight: lit ? 800 : 600,
                letterSpacing: '0.07em', padding: '7px 3px', borderRadius: 9,
                color: lit ? (quiet ? pal.textPrimary : inkOf(pal.accent, pal, dark)) : labelInk(pal, dark),
                border: `1px solid ${lit ? (quiet ? hair(dark, 0.32) : wash(pal.accent, 0.8)) : hair(dark, 0.10)}`,
                background: lit ? (quiet ? hair(dark, 0.08) : wash(pal.accent, 0.18)) : 'transparent',
                boxShadow: lit && !quiet ? `0 0 0 3px ${wash(pal.accent, 0.13)}` : undefined,
                opacity: lit ? 1 : done ? 0.7 : 0.55,
              }}>{w}</span>
            </Fragment>
          )
        })}
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 18, minWidth: 0, flexWrap: 'wrap' }}>
        <div style={{ flex: '0 0 auto', minWidth: 0 }}>
          <Hero v={heroV} unit={heroUnit} caption={heroCap} tone={heroTone}
            pal={pal} dark={dark} size={34} />
        </div>
        <div style={{ flex: '1 1 240px', minWidth: 200 }}>{meter}</div>
      </div>

      <Receipts>
        <Chip pal={pal} dark={dark} strong>{showSell ? 'SELL · u3' : 'BUY · d3'}</Chip>
        <FrameBadge frame="FUT" pal={pal} dark={dark} />
        <Note pal={pal} dark={dark}>
          {showSell
            ? 'SELL mirror — the data rejected this side; it does not carry the buy rule’s measured hit rate.'
            // "the scored side" is a claim about the SIDE, and it stays true.
            // What the interval changes is whether the scored NUMBER describes
            // these candles — one short qualifier, and the Trade tab's SETUP
            // CHECK owns the full sentence.
            : publishedInterval === SCORED_INTERVAL
              ? 'the scored side.'
              : `the scored side — but these are ${publishedInterval ? `${publishedInterval}-minute` : 'unstated'}`
                + ` candles, not the ${SCORED_INTERVAL}-minute ones it was measured on.`}
          {bothLive && ' Both sides are live — the Trade tab shows the other.'}
          {st.readable === false && ' Is bar ka read nahi mila.'}
        </Note>
      </Receipts>
    </>
  )
}

function GexPane({ pal, dark, w }: { pal: Palette; dark: boolean; w: WireOf }) {
  if (!w.ok) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why={w.why || 'the option chain has not answered yet'} />
  }

  const reg = w.gexRegime
  const regWord = reg === 'POSITIVE' ? 'POSITIVE' : reg === 'NEGATIVE' ? 'NEGATIVE' : null
  const regGloss = reg === 'POSITIVE' ? 'dealers dampen — moves fade back'
    : reg === 'NEGATIVE' ? 'dealers amplify — moves extend' : ''
  // Was a gamma profile built at all? NO_IV and ONE_STRIKE mean it was not,
  // and every number downstream of it is an empty sum rather than a reading.
  const profiled = w.flipStatus === 'FOUND' || w.flipStatus === 'NO_CROSSING'

  if (!regWord && reg !== 'OUT-OF-ZONE' && w.flipPx == null) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why={flipReason(w.flipStatus)
        || 'the chain published no gamma regime and no reason for its absence'} />
  }

  /* ── The ladder ────────────────────────────────────────────────────────────
   * The flip level IS the axis: above it dealer hedging leans against the move,
   * below it the same hedging pushes with it. That is a statement about a
   * REGION, and until now this pane made it in a sentence and a number — the
   * one shape the operator asked to see drawn. Positive sits above in brass
   * (structure), negative below in neutral ink. Neither is green or red: which
   * way dealers lean is not which way the tape goes.
   */
  const band = w.gexSpotBand
  const nearLo = w.spot != null && band != null ? w.spot - band : null
  const nearHi = w.spot != null && band != null ? w.spot + band : null
  const dom = domain([
    w.flipPx, w.spot, nearLo, nearHi,
    w.bookZone?.[0], w.bookZone?.[1], w.wallUp, w.wallDn,
  ])

  let rail: ReactNode = null
  if (dom && w.flipPx != null) {
    const [lo, hi] = dom
    const zones: RailZone[] = [
      { from: w.flipPx, to: hi, fill: wash(pal.accent, 0.16), label: 'dealers dampen', labelTone: pal.accent },
      { from: lo, to: w.flipPx, fill: hair(dark, dark ? 0.09 : 0.07), label: 'dealers amplify' },
    ]
    if (w.bookZone) {
      zones.push({ from: w.bookZone[0], to: w.bookZone[1], fill: wash(pal.strike, 0.13) })
    }
    if (nearLo != null && nearHi != null) {
      zones.push({ from: nearLo, to: nearHi, fill: hair(dark, dark ? 0.10 : 0.06) })
    }
    const marks: RailMark[] = [{ at: w.flipPx, label: 'flip', value: f0(w.flipPx), tone: pal.accent, strong: true }]
    if (nearHi != null) marks.push({ at: nearHi, label: `±${f0(band)}`, tone: labelInk(pal, dark), dashed: true })
    rail = (
      <Rail lo={lo} hi={hi} zones={zones} marks={marks}
        spot={w.spot} spotLabel={f0(w.spot)} pal={pal} dark={dark} height={126} />
    )
  }

  /* gex_spot_band: published by chain_metrics.py since D5 and never drawn
     until now. A near-money GEX is meaningless without it.

     When no strike had a solvable IV there is nothing to sum, and `sum()` over
     an empty set is 0.0 — a zero that means "we could not look", not "gamma
     here is zero". Printing it as a reading would be the same `?? 0` lie the
     ATM-IV row was fixed for. The WINDOW is still real (it comes from strike
     spacing), so it is shown and the sum is not. */
  const heroV = profiled && w.gexSpot != null ? gexFmt(w.gexSpot)
    : w.flipPx != null ? f0(w.flipPx) : '—'
  const heroUnit = profiled && w.gexSpot != null
    ? (band != null ? `GEX ±${f0(band)}pt` : 'near-money GEX')
    : 'flip level'

  return (
    <>
      <Hero v={heroV} unit={heroUnit} pal={pal} dark={dark} size={30}
        caption={regWord ? regGloss : undefined} tone={pal.accent} />

      {reg === 'OUT-OF-ZONE' && (
        // Not "neutral". The book has gamma; price has simply walked out of
        // it, and the total says nothing about where price actually is.
        <Note pal={pal} dark={dark}>
          <b style={{ color: inkOf(pal.caution, pal, dark) }}>OUT OF ZONE</b> — spot has walked outside the heavy
          books, so the chain-wide total says nothing about here.
        </Note>
      )}

      {rail ?? (
        <Note pal={pal} dark={dark}>
          <b style={{ color: labelInk(pal, dark) }}>no flip level to draw against</b> —{' '}
          {flipReason(w.flipStatus) || 'no reason published'}
        </Note>
      )}

      {!profiled && (
        <Note pal={pal} dark={dark}>
          nothing was summed in the near-money window this snapshot — the window is real, the sum is not.
        </Note>
      )}

      <Receipts>
        {regWord && <Chip pal={pal} dark={dark} tone={pal.accent} strong>{regWord}</Chip>}
        {w.bookZone ? (
          <Chip pal={pal} dark={dark} tone={w.inBookZone === false ? pal.caution : undefined}>
            {w.inBookZone === false ? 'outside ' : 'book '}{f0(w.bookZone[0])}–{f0(w.bookZone[1])}
          </Chip>
        ) : (
          <Note pal={pal} dark={dark}>no heavy-book zone — no strike carried a dominant share of OI</Note>
        )}
        <FrameBadge frame="IDX" pal={pal} dark={dark} />
      </Receipts>
    </>
  )
}

function FlowPane({ pal, dark, last, rows, why }: {
  pal: Palette; dark: boolean; last: FlowRow | null; rows: FlowRow[] | null; why: string
}) {
  if (!last) return <Absent kind="blind" pal={pal} dark={dark} why={why} />

  // Last few marks, oldest → newest. `baseline` rows are the session's zero
  // point by construction, not a reading, so they are drawn hollow.
  const tail = (rows ?? []).slice(-9)
  const peak = Math.max(1, ...tail.map((r) => Math.max(Math.abs(r.call), Math.abs(r.put))))
  const H = 78

  return (
    <>
      <Hero v={crl(last.diff)} unit={`${last.diff >= 0 ? 'PUT' : 'CALL'}-heavy`}
        caption={`cumulative day OI change · ${last.time} mark`} pal={pal} dark={dark} size={31} />

      {/* CALL above the zero axis, PUT below it, both on ONE shared scale so
          the two legs are comparable by length. Red above is call-side OI,
          green below is put-side — the bars carry direction, the numbers do
          not. The newest bucket is the read; everything left of it is the
          run-up to it and is drawn as such. */}
      <div style={{ position: 'relative', height: H, marginTop: 2, minWidth: 0 }}>
        <div aria-hidden="true" style={{
          position: 'absolute', left: 0, right: 0, top: H / 2, height: 1,
          background: hair(dark, 0.22),
        }} />
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 3, height: '100%' }}>
          {tail.map((r, i) => {
            const latest = i === tail.length - 1
            const op = r.baseline ? 0.28 : latest ? 1 : 0.55
            return (
              <div key={`${r.time}-${i}`} title={`${r.time} · CALL ${crl(r.call)} · PUT ${crl(r.put)}`}
                style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end' }}>
                  <div style={{
                    width: '100%', height: `${Math.max(3, (Math.abs(r.call) / peak) * 100)}%`,
                    background: pal.bear, borderRadius: '3px 3px 0 0', opacity: op,
                  }} />
                </div>
                <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start' }}>
                  <div style={{
                    width: '100%', height: `${Math.max(3, (Math.abs(r.put) / peak) * 100)}%`,
                    background: pal.bull, borderRadius: '0 0 3px 3px', opacity: op,
                  }} />
                </div>
              </div>
            )
          })}
        </div>
        {/* the newest bucket, named */}
        <span aria-hidden="true" style={{
          position: 'absolute', right: 0, top: -1, bottom: -1,
          width: `calc(${100 / Math.max(1, tail.length)}% - 1px)`,
          border: `1px solid ${wash(pal.accent, 0.5)}`, borderRadius: 5, pointerEvents: 'none',
        }} />
      </div>

      <Receipts>
        <Chip pal={pal} dark={dark}>CALL {crl(last.call)}</Chip>
        <Chip pal={pal} dark={dark}>PUT {crl(last.put)}</Chip>
        {last.pcr != null && <Chip pal={pal} dark={dark}>PCR {last.pcr.toFixed(2)}</Chip>}
        <Note pal={pal} dark={dark}>5-minute marks · {tail.length} shown</Note>
      </Receipts>
    </>
  )
}

function AtmPane({ pal, dark, chain, atm }: {
  pal: Palette; dark: boolean; chain: Chain; atm: number | null
}) {
  const row = chain.strikes.find((s) => s.type === 'atm')
    ?? (atm != null ? chain.strikes.find((s) => s.strike === atm) : undefined)

  if (!row) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why="the chain ladder carries no ATM row — the snapshot did not name an at-the-money strike" />
  }

  const heavier = row.ceOI === row.peOI ? null : row.ceOI > row.peOI ? 'CE' : 'PE'
  const tot = row.ceOI + row.peOI
  const cePct = tot > 0 ? (row.ceOI / tot) * 100 : 50
  const ink = onBarInk(dark)

  return (
    <>
      <Hero v={f0(row.strike)} unit="ATM strike" tone={pal.accent} pal={pal} dark={dark} size={31}
        caption={heavier
          ? `${heavier} side holds ${Math.round(Math.max(cePct, 100 - cePct))}% of this strike’s book`
          : 'both books are the same size — neither side owns it'} />

      {/* The split, at a weight you can actually read. This was a 4px sliver;
          a 26px bar with the shares written INSIDE it turns the pane's whole
          question into one glance. The bar carries direction (green/red); the
          ink on it is chosen per mode so both segments clear 4.5:1. */}
      <div style={{
        display: 'flex', height: 26, borderRadius: 7, overflow: 'hidden', minWidth: 0,
        border: `1px solid ${hair(dark, 0.12)}`,
      }}>
        <div style={{
          width: `${cePct}%`, background: pal.bear, display: 'flex',
          alignItems: 'center', justifyContent: 'center', minWidth: 0,
        }}>
          <span className="mono" style={{
            fontSize: 11, fontWeight: 800, color: ink, letterSpacing: '0.03em', whiteSpace: 'nowrap',
          }}>{cePct >= 22 ? `CE ${Math.round(cePct)}%` : ''}</span>
        </div>
        <div style={{
          width: `${100 - cePct}%`, background: pal.bull, display: 'flex',
          alignItems: 'center', justifyContent: 'center', minWidth: 0,
        }}>
          <span className="mono" style={{
            fontSize: 11, fontWeight: 800, color: ink, letterSpacing: '0.03em', whiteSpace: 'nowrap',
          }}>{100 - cePct >= 22 ? `PE ${Math.round(100 - cePct)}%` : ''}</span>
        </div>
      </div>

      <Receipts>
        <Chip pal={pal} dark={dark}>CE {oiAbs(row.ceOI)}</Chip>
        <Chip pal={pal} dark={dark}>PE {oiAbs(row.peOI)}</Chip>
        <FrameBadge frame="IDX" pal={pal} dark={dark} />
        {heavier && (
          <Note pal={pal} dark={dark}>
            {heavier === 'CE' ? 'call writers hold this strike.' : 'put writers hold this strike.'}
          </Note>
        )}
      </Receipts>
    </>
  )
}

function WallsPane({ pal, dark, w }: { pal: Palette; dark: boolean; w: WireOf }) {
  if (!w.ok) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why={w.why || 'the option chain has not answered yet'} />
  }
  if (w.wallUp == null && w.wallDn == null) {
    // Both walls come out of the same gamma profile as the flip, so they fail
    // for the same reason and it must be the SAME reason, not a vaguer one.
    return w.flipStatus === 'NO_IV' || w.flipStatus === 'ONE_STRIKE'
      ? <Absent kind="blind" pal={pal} dark={dark} why={flipReason(w.flipStatus)} />
      : <Absent kind="none" pal={pal} dark={dark}
          why="looked, and found none — no strike either side of spot carried non-zero dealer gamma" />
  }

  const dUp = w.wallUp != null && w.spot != null ? w.wallUp - w.spot : null
  const dDn = w.wallDn != null && w.spot != null ? w.wallDn - w.spot : null

  // The hero is the wall price is actually closest to — the one that decides
  // the next few points. Ties go up, so the number never flickers between two.
  const nearer = dUp != null && dDn != null
    ? (Math.abs(dUp) <= Math.abs(dDn) ? 'call' : 'put')
    : dUp != null ? 'call' : dDn != null ? 'put' : null
  const nearD = nearer === 'call' ? dUp : dDn

  /* Both walls, spot between them, drawn to the SAME scale — so "the call wall
     is close and the put wall is far" is a shape, not two numbers the operator
     has to subtract in their head. */
  const dom = domain([w.wallUp, w.wallDn, w.spot], 0.14)
  const marks: RailMark[] = []
  if (w.wallUp != null) marks.push({ at: w.wallUp, label: 'call', value: f0(w.wallUp), tone: pal.accent, strong: true })
  if (w.wallDn != null) marks.push({ at: w.wallDn, label: 'put', value: f0(w.wallDn), tone: pal.accent, strong: true })

  return (
    <>
      <Hero
        v={nearD != null ? signed(nearD, 0) : '—'}
        unit={nearer ? `pt to ${nearer} wall` : 'no wall'}
        caption={dUp != null && dDn != null
          ? `call ${signed(dUp, 0)} · put ${signed(dDn, 0)} · spot ${f0(w.spot)}`
          : `spot ${f0(w.spot)}`}
        pal={pal} dark={dark} size={31} />

      {dom ? (
        <Rail lo={dom[0]} hi={dom[1]} marks={marks} spot={w.spot} spotLabel={f0(w.spot)}
          pal={pal} dark={dark} height={104} />
      ) : (
        <Note pal={pal} dark={dark}>
          only one side of the book carried dealer gamma, so there is no span to draw between.
        </Note>
      )}

      <Receipts>
        {w.wallUp == null && (
          <Note pal={pal} dark={dark}>
            <b style={{ color: labelInk(pal, dark) }}>no call wall</b> — no strike above spot carried dealer gamma
          </Note>
        )}
        {w.wallDn == null && (
          <Note pal={pal} dark={dark}>
            <b style={{ color: labelInk(pal, dark) }}>no put wall</b> — no strike below spot carried dealer gamma
          </Note>
        )}
        <FrameBadge frame="IDX" pal={pal} dark={dark} />
        <Note pal={pal} dark={dark}>distances measured against index spot</Note>
      </Receipts>
    </>
  )
}

function PinPane({ pal, dark, w }: { pal: Palette; dark: boolean; w: WireOf }) {
  if (!w.ok) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why={w.why || 'the option chain has not answered yet'} />
  }

  const sq = w.squeezeScore
  const sqWord = sq == null ? null : sq > 0.3 ? 'HIGH' : sq > 0.1 ? 'MEDIUM' : 'LOW'

  if (w.maxPain == null) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why="the chain computed no max-pain strike this snapshot" />
  }

  /* Spot at the CENTRE, the pin offset drawn from it. A pin distance is a
     signed thing and the only honest way to draw one is symmetrically — a
     meter that started at spot would make +20 and −20 look like different
     magnitudes. The window is at least ±30pt so a tiny offset does not fill
     the whole rail and read as a large one. */
  const R = Math.max(30, Math.abs(w.mpDist ?? 0) * 1.6)
  const centre = w.spot ?? w.maxPain
  const ticks: MeterTick[] = [
    { at: w.maxPain, label: `PIN ${f0(w.maxPain)}`, tone: pal.accent, strong: true },
  ]

  return (
    <>
      <Hero
        v={w.mpDist != null ? signed(w.mpDist, 0) : '—'}
        unit="pt to pin"
        caption={w.mpDist != null
          ? `max pain ${f0(w.maxPain)} sits ${w.mpDist >= 0 ? 'above' : 'below'} spot ${f0(w.spot)}`
          : `max pain ${f0(w.maxPain)} · no signed distance published`}
        pal={pal} dark={dark} size={31} />

      <Meter lo={centre - R} hi={centre + R} ticks={ticks}
        marker={centre} markerLabel="spot"
        span={w.spot != null ? [w.spot, w.maxPain] : undefined} spanTone={pal.accent}
        pal={pal} dark={dark} height={42} />

      <Receipts>
        <Chip pal={pal} dark={dark}>PCR oi {w.pcrOi != null ? w.pcrOi.toFixed(2) : '—'}</Chip>
        <Chip pal={pal} dark={dark}>PCR vol {w.pcrVol != null ? w.pcrVol.toFixed(2) : '—'}</Chip>
        {sqWord ? (
          <Chip pal={pal} dark={dark} strong
            tone={sqWord === 'HIGH' ? pal.caution : undefined}>
            SQZ {w.squeezeSide ? `${sqWord} ${w.squeezeSide}` : sqWord}
          </Chip>
        ) : (
          <Note pal={pal} dark={dark}>no squeeze score published this snapshot</Note>
        )}
        <FrameBadge frame="IDX" pal={pal} dark={dark} />
        {w.squeezeVerdict && <Note pal={pal} dark={dark}>{w.squeezeVerdict}</Note>}
      </Receipts>
    </>
  )
}

function BandsPane({ pal, dark, bar, stale, loading }: {
  pal: Palette; dark: boolean; bar: TapeBar | null; stale: boolean; loading: boolean
}) {
  if (stale || !bar) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why={loading ? 'tape aa raha hai — no bar has landed yet'
        : 'no live tape for this index, so there are no σ bands to sit in'} />
  }

  const gap = bar.c - bar.d3
  // Which bracket price actually sits in, named from the ladder itself.
  const ladder: Array<[string, number]> = [
    ['u3', bar.u3], ['u2', bar.u2], ['u1', bar.u1],
    ['VWAP', bar.vwap], ['d1', bar.d1], ['d2', bar.d2], ['d3', bar.d3],
  ]
  let where = `above u3 ${f1(bar.u3)}`
  if (bar.c < bar.d3) where = `below d3 ${f1(bar.d3)}`
  else {
    for (let i = 0; i < ladder.length - 1; i++) {
      if (bar.c <= ladder[i][1] && bar.c > ladder[i + 1][1]) {
        where = `between ${ladder[i + 1][0]} and ${ladder[i][0]}`
        break
      }
    }
  }

  /* The ladder IS the pane now, at a size that can carry its own labels.
     Brass ticks are structure, VWAP takes the caution amber it has everywhere
     else, and d3 is drawn strong because it is the one edge the research
     actually scored. The price mark is the only bright thing. No green or red
     here — a band is not a direction. */
  const ticks: MeterTick[] = ladder.map(([name, v]) => ({
    at: v,
    label: `${name}`,
    tone: name === 'VWAP' ? pal.caution : pal.accent,
    strong: name === 'd3',
  }))

  return (
    <>
      <Hero v={signed(gap)} unit="pt to d3"
        tone={Math.abs(gap) < 15 ? pal.accent : undefined}
        caption={`${where} · price ${f1(bar.c)}`}
        pal={pal} dark={dark} size={31} />

      <Meter lo={bar.d3} hi={bar.u3} ticks={ticks}
        marker={bar.c} markerLabel={f1(bar.c)}
        span={[bar.d3, bar.c]} spanTone={pal.accent}
        pal={pal} dark={dark} height={48} />

      <Receipts>
        <Chip pal={pal} dark={dark} tone={pal.accent} strong>d3 {f1(bar.d3)}</Chip>
        <Chip pal={pal} dark={dark} tone={pal.caution}>VWAP {f1(bar.vwap)} ({signed(bar.c - bar.vwap)})</Chip>
        <FrameBadge frame="FUT" pal={pal} dark={dark} />
        <Note pal={pal} dark={dark}>d3 is the one scored edge</Note>
      </Receipts>
    </>
  )
}

function BasisPane({ pal, dark, w }: { pal: Palette; dark: boolean; w: WireOf }) {
  if (!w.basisRead) {
    return <Absent kind="blind" pal={pal} dark={dark}
      why="the basis has not been read yet — /api/data has not answered this index" />
  }
  if (w.basis == null) {
    // The backend refuses an implausible carry rather than shipping 0.0, and
    // ships the sentence with it. This is the one place that sentence lands.
    return <Absent kind="none" pal={pal} dark={dark}
      why={w.basisWhy || 'the backend published a null basis without a reason — treat every chain level as unplaced'} />
  }
  /* The two rails. This pane explains the FRAME every other pane is badged
     with, and it explained it in a sentence — so the one thing on the board
     that is genuinely a diagram was the one thing drawn as prose. Two tapes,
     the gap between them bracketed and named. Brass, because a frame offset is
     structure; nothing here is a direction. */
  const fut = w.spot != null ? w.spot + w.basis : null
  const up = w.basis >= 0

  return (
    <>
      <Hero v={signed(w.basis, 2)} unit="FUT − IDX" tone={pal.accent} pal={pal} dark={dark} size={31}
        caption="every IDX figure on this board sits this far from the same level on the FUT tape" />

      <div style={{ position: 'relative', height: 62, minWidth: 0, marginTop: 2 }} aria-hidden="true">
        {([['FUT', fut, 8], ['IDX', w.spot, 44]] as Array<[string, number | null, number]>).map(([name, v, top]) => (
          <div key={name} style={{
            position: 'absolute', left: 0, right: 0, top,
            display: 'flex', alignItems: 'center', gap: 7,
          }}>
            <span style={{
              fontSize: 11, fontWeight: 800, letterSpacing: '0.07em',
              color: labelInk(pal, dark), width: 28, flexShrink: 0,
            }}>{name}</span>
            <span style={{ flex: 1, height: 2, background: wash(pal.accent, 0.5), minWidth: 0 }} />
            <span className="mono" style={{
              fontSize: 11.5, fontWeight: 700, color: pal.textPrimary, whiteSpace: 'nowrap',
            }}>{v != null ? f1(v) : '—'}</span>
          </div>
        ))}
        {/* the bracket between them, and the number it measures */}
        <div style={{
          position: 'absolute', left: 44, top: 15, bottom: 15, width: 1,
          background: pal.accent, opacity: 0.75,
        }} />
        <span className="mono" style={{
          position: 'absolute', left: 52, top: 22,
          fontSize: 11.5, fontWeight: 700, color: inkOf(pal.accent, pal, dark), whiteSpace: 'nowrap',
        }}>{signed(w.basis, 2)} pt {up ? 'above' : 'below'}</span>
      </div>

      <Receipts>
        <Chip pal={pal} dark={dark}>index spot {f1(w.spot)}</Chip>
        <Note pal={pal} dark={dark}>
          checked and plausible — a carry the backend could not believe ships as null with a reason, never as 0.0
        </Note>
      </Receipts>
    </>
  )
}

/* ── The board ───────────────────────────────────────────────────────────── */

type WidgetId = 'machine' | 'gex' | 'flow' | 'atmoi' | 'walls' | 'pin' | 'bands' | 'basis'

const DEFAULT_ORDER: WidgetId[] = ['machine', 'gex', 'flow', 'atmoi', 'walls', 'pin', 'bands', 'basis']

export default function GlassBoard({
  index, chain, bars, runState, runStateWhy, runStateSell,
  publishedInterval, stale, loading, chainStale, setActiveTab,
}: Props) {
  const [mode] = useMode()
  const pal = palette(mode)
  const dark = mode === 'dark'

  const w = useChainWire(index)
  const { last: lastFlow, rows: flowRows, why: flowWhy } = useFlow(index)

  const { order, move, nudge } = useGlassOrder(DEFAULT_ORDER)
  const { drag, start } = useGlassDrag(move)

  const lastBar = bars.length ? bars[bars.length - 1] : null
  const machine = useMemo(
    () => liveMachine(runState, runStateSell),
    [runState, runStateSell],
  )

  const staleNote = chainStale
    ? `chain snapshot ${w.ts || '--:--:--'} — these figures are from that moment, not now`
    : undefined

  const SPEC: Record<WidgetId, {
    label: string; goesTo: Tab; span: number; minHeight: number
    chainFed: boolean; body: ReactNode
    /** Read, never formed — see the lean sources at the top of this file.
     *  Omitted entirely on the five panes the app states no direction for. */
    lean?: Lean
  }> = {
    machine: {
      label: 'Machine', goesTo: 'Trade', span: 2, minHeight: 232, chainFed: false,
      lean: machineLean(machine.st, machine.showSell, stale),
      body: <MachinePane pal={pal} dark={dark} stale={stale} st={machine.st}
        showSell={machine.showSell} bothLive={machine.bothLive}
        why={runStateWhy} lastBar={lastBar}
        publishedInterval={publishedInterval} />,
    },
    gex: {
      label: 'Dealer gamma', goesTo: 'Chain', span: 1, minHeight: 288, chainFed: true,
      body: <GexPane pal={pal} dark={dark} w={w} />,
    },
    flow: {
      label: 'Trending OI', goesTo: 'OI Flow', span: 1, minHeight: 232, chainFed: false,
      lean: flowLean(lastFlow),
      body: <FlowPane pal={pal} dark={dark} last={lastFlow} rows={flowRows} why={flowWhy} />,
    },
    atmoi: {
      label: 'ATM open interest', goesTo: 'Chain', span: 1, minHeight: 196, chainFed: true,
      body: <AtmPane pal={pal} dark={dark} chain={chain} atm={w.atm} />,
    },
    walls: {
      label: 'Walls', goesTo: 'Chain', span: 1, minHeight: 264, chainFed: true,
      body: <WallsPane pal={pal} dark={dark} w={w} />,
    },
    pin: {
      label: 'Pin & pressure', goesTo: 'Chain', span: 1, minHeight: 212, chainFed: true,
      lean: w.ok && w.maxPain != null ? pinLean(w.squeezeSide) : null,
      body: <PinPane pal={pal} dark={dark} w={w} />,
    },
    bands: {
      label: 'σ bands', goesTo: 'Trade', span: 1, minHeight: 212, chainFed: false,
      body: <BandsPane pal={pal} dark={dark} bar={lastBar} stale={stale} loading={loading} />,
    },
    basis: {
      label: 'Basis', goesTo: 'Trade', span: 1, minHeight: 232, chainFed: false,
      body: <BasisPane pal={pal} dark={dark} w={w} />,
    },
  }

  return (
    <div style={{
      position: 'relative', minHeight: '100%', padding: '18px 22px 26px',
      // The pointer is dragging a pane, not selecting the numbers on it.
      userSelect: drag ? 'none' : undefined,
    }}>
      {/* What the glass refracts. Behind everything, and never a data surface. */}
      <div className="glass-field" aria-hidden="true" />

      <div style={{
        position: 'relative', zIndex: 1,
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 13,
      }}>
        <span style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.1em',
          color: labelInk(pal, dark), textTransform: 'uppercase',
        }}>{index} · glance board</span>
        <span style={{ fontSize: 11, color: labelInk(pal, dark) }}>
          tap a panel to open its evidence · drag ⠿ to rearrange (or Alt+←/→ on a focused panel)
        </span>
        {w.note && (
          <span className="mono" style={{ fontSize: 11, color: labelInk(pal, dark), marginLeft: 'auto' }}>
            chain {w.ts || '--:--:--'} · {w.note}
          </span>
        )}
      </div>

      <div style={{
        position: 'relative', zIndex: 1,
        display: 'grid',
        // 300px, not the 276 this started at: the panes now carry drawn
        // instruments with their own labels, and a rail that has to letterbox
        // is a rail that stops being to scale. At 1900 that resolves to five
        // ~360px columns — the hero spans two, so both rows fill.
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gridAutoRows: 'minmax(min-content, auto)',
        gap: 14,
        alignItems: 'stretch',
      }}>
        {order.map((id) => {
          const s = SPEC[id as WidgetId]
          if (!s) return null
          return (
            <GlassCard
              key={id}
              id={id}
              label={s.label}
              goesTo={s.goesTo}
              span={s.span}
              minHeight={s.minHeight}
              staleNote={s.chainFed ? staleNote : undefined}
              lean={s.lean ?? null}
              lifted={drag?.id === id}
              over={!!drag && drag.over === id && drag.id !== id}
              onGripDown={start(id)}
              onNudge={(d) => nudge(id, d)}
              onOpen={() => setActiveTab(s.goesTo)}
              pal={pal}
              dark={dark}
            >
              {s.body}
            </GlassCard>
          )
        })}
      </div>
    </div>
  )
}
