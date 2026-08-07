// ── Live data layer ────────────────────────────────────────────────────────────
// Fetches the real TapeMap Python backend (proxied at /api) and maps its JSON
// into the exact shapes the App.tsx components already consume. On mount and
// every 5s it pulls /api/data and /api/chain for all three indices in parallel,
// tolerating a failing index (keeps last-good / mock fallback per index).
import { useCallback, useEffect, useRef, useState } from 'react'

// ── Target types (what the components read) ─────────────────────────────────────
export type IndexKey = 'NIFTY' | 'BANKNIFTY' | 'SENSEX'

export interface IndexInfo {
  price: number
  change: number
  pct: number
  state: string
  arrow: string
  highlight?: boolean
}
export interface Read {
  headline: string
  timing: string
  direction: string
  sub: string
}
export interface Level {
  label: string
  value: number
  note: string
  dist: number
  dir: 'up' | 'down' | 'here'
}
export interface OrderFlow {
  main: string
  mm: string
  stats: Array<{ label: string; value: string }>
}
export interface StrikeRow {
  strike: number
  ceOI: number
  peOI: number
  gex: number
  ceW: number
  peW: number
  /** Session-high OI per book; drives the "% off peak" defenders read. */
  cePk: number
  pePk: number
  /** Traded premium and fitted IV per leg. The feed returns delta/gamma as
   *  null, so anything greek-shaped must be computed, never read. */
  ceLtp: number
  peLtp: number
  ceIv: number
  peIv: number
  ceSpread: number
  peSpread: number
  type?: 'callwall' | 'putwall' | 'atm'
}
export interface Chain {
  pcr: string
  maxPain: number
  gex: string
  squeeze: string
  strikes: StrikeRow[]
  /** Signed distance from spot to max pain (+ = pin sits above). */
  mpDist: number
  /** Gamma concentrated at the strikes either side of spot, not chain-wide. */
  gexSpot: number
  /** [lo, hi] of the strikes carrying the heavy books, or null. */
  bookZone: [number, number] | null
  /**
   * False when price has walked outside the heavy books. Critical nuance:
   * gex_total collapses BOTH when dampening genuinely dies and when price
   * simply leaves the gamma — opposite meanings. On 2026-07-28 it read 120k
   * at the 15:01 low (outside the zone) and 1.56M twenty minutes later back
   * at 24,000; reading the first as "dampening over" cost a bad call.
   */
  inBookZone: boolean
  /** Spot at the chain snapshot, and the ATM straddle (CE+PE premium) — the
   *  market's own price for a move, which is what any bought option competes
   *  against. Expiry as "YYYY-MM-DD". */
  spot: number
  expiry: string
  atmStraddle: number
  /**
   * True when the strike ladder belongs to the bar being shown. False while
   * scrubbing: the chain arrives as a live snapshot with no per-strike
   * history, so the ladder cannot be replayed and must say so.
   */
  aligned: boolean
  /** Dealer gamma flip price from the chain GEX profile, or null when the
   *  chain could not compute one. Never guessed. */
  flipPx: number | null
  /** The poller's own IST clock ("HH:MM:SS") at the moment it built this
   *  snapshot. Honest even when the payload is stale — it is the label for
   *  `builtAt`, not a claim about now. */
  ts: string
  /**
   * Epoch seconds when the poller published this chain snapshot (`built_at`
   * on the wire), captured at publish time and deliberately NOT refreshed by
   * `_tag_error` — a tagged-but-stale payload keeps looking stale. `null`
   * when an older backend didn't supply the field, in which case staleness
   * is unknown and must never be reported as fresh.
   */
  builtAt: number | null
}
export interface EventItem {
  time: string
  text: string
  tag: string
  dir: 'bull' | 'bear' | 'neutral'
}
export interface ChartPoint {
  time: string
  price: number
  vwap: number
  upper: number
  lower: number
  vol: number
  isFuture: boolean
}

// Per-bar engine decisions — the same ctx/gamma/setup blocks `mapIndex` below
// already reads off the live bar (as `any`), now named so the Tape Chart can
// read them too. Field spellings copied verbatim from engine.py's ctx_track
// (~1091), gamma.track (~260) and setup_track (~891) — the engine owns the
// vocabulary; this file only names it, never rewords or re-derives it.
export interface BarCtx {
  verdict: string; vwhy: string; breadth: string; line: string
  flips: string[]; age: number
  rng30: number; rng_r: number; vol30: number; inside1: number
  z: number; bw_r: number
  pin: { k: number; dist: number; regime: string } | null
  plays: string[]
  floor: [string, number] | null
  cap: [string, number] | null
  episode?: unknown; loc?: string
}
export interface BarGamma { regime: string; w_ce: number; w_pe: number; proxy: number }

/** One option leg of a tape bar — the engine's tracked ATM strike, verbatim
 *  from the payload's `ce`/`pe` blocks (engine.py session_json). The premium's
 *  OWN session VWAP and σ bands, computed server-side; the UI renders them and
 *  derives nothing. NOTE this series is rolling-ATM: the sticky strike
 *  migrates with spot, so a premium step at a hop is a strike change, not a
 *  trade — every consumer must disclose that. */
export interface BarLeg {
  o: number; h: number; l: number; c: number
  vwap: number
  u1: number; d1: number; u2: number; d2: number; u3: number; d3: number
  oi: number | null; v: number
  /** Extra engine fields ride along untyped (z, vol_r, oi_slope, oi_r,
   *  prem_d, bw_r) — the block is passed through whole, never rebuilt. */
  [extra: string]: unknown
}

/** Floor pivots of ONE option leg's own prior session (`opt_pivots.ce/pe` on
 *  the wire) — computed server-side by live._floor_pivots from the contract's
 *  own H/L/C, which ride along as receipts. Rendered verbatim, never derived
 *  here. */
export interface OptPivotLeg {
  P: number; R1: number; S1: number; R2: number; S2: number; R3: number; S3: number
  H: number; L: number; C: number
}
export interface OptPivots {
  strike: number
  prev_day: string
  expiry: string
  ce: OptPivotLeg | null
  pe: OptPivotLeg | null
  /** Per-leg reason when that leg is null (no prior session / fetch failed).
   *  "No pivots exist" and "we could not get them" stay different sentences. */
  why: { ce: string | null; pe: string | null }
}

/* One row of /api/oiflow — Trending OI, aggregated server-side from the chain
   poller's minute grid (chain_metrics.ChainState.oi_flow). `call`/`put` are
   cumulative day OI CHANGE summed over the selected strikes, not outstanding
   OI; each row is the chain AS AT its clock mark. Shared by the OI Flow tab
   and the Trade tab's OI strip + zone read. */
export interface FlowRow {
  time: string; ltp: number | null; call: number; put: number; diff: number
  strength: number; pcr: number | null; chg_dir: number | null
  chg_dir_pct: number | null; sentiment: string
  brk: string | null; brk_px: number | null
}
export interface BarSetup {
  status: string; dir: 'UP' | 'DOWN'; t0: string; kind: string
  level_name: string; level_px: number; ref: number
  intensity: number; conflict: boolean; comp: number
  died?: string; fired?: string
}

// Tape Chart — one FUT bar, verbatim from the payload. The engine computed
// every field server-side (invariant: UI renders, engine decides); this type
// only names what arrives. Times are "HH:MM".
export interface TapeBar {
  t: string
  o: number; h: number; l: number; c: number
  v: number; oi: number
  vwap: number
  u1: number; d1: number; u2: number; d2: number; u3: number; d3: number
  /** Additive blocks only some backends/bars carry — early bars may predate
   *  the ctx block, older backends may lack it entirely. `null` (never a
   *  default) whenever the payload didn't carry the block for this bar, so a
   *  bar with no verdict can never be mistaken for one that inherited its
   *  neighbour's. */
  ctx?: BarCtx | null
  gamma?: BarGamma | null
  setup?: BarSetup | null
  /** The tracked ATM strike's option legs, verbatim from the payload. `null`
   *  when that leg did not print this minute — a missing leg minute stays a
   *  hole (session_json history: intersecting FUT with leg availability
   *  silently dropped whole bars once; never again). Rolling-ATM series —
   *  see BarLeg. */
  ce?: BarLeg | null
  pe?: BarLeg | null
}

// ── SMC / ICT structure layer (Phase 3.5) ──────────────────────────────────────
// Computed server-side by structure.py and attached to each day of /api/data as
// a sibling of `bars` (commits b616e9d / b2856c9). This file only NAMES the
// wire shape — no structure is derived, filtered or re-confirmed here.
export type StructureKind =
  | 'FVG' | 'OB' | 'BOS' | 'CHOCH' | 'EQH' | 'EQL' | 'SWING_H' | 'SWING_L'
  // Prior-session levels, inverted from the payload's own floor pivots and
  // cross-checked before publication (structure.py's prior_day_hlc), plus the
  // working range's 50% split. PD* carry `born: 0` — they are known before the
  // session opens. PREMIUM/DISCOUNT are re-cut whenever the range moves, so
  // several are published per session and the chart draws only the current one.
  | 'PDH' | 'PDL' | 'PDC' | 'PREMIUM' | 'DISCOUNT'

/**
 * Three distinct claims, which must never collapse into one rendering:
 *   CONFIRMED   — flow was checked and it agrees.
 *   UNCONFIRMED — flow was checked and it does NOT agree.
 *   UNKNOWN     — flow could not be checked at all (structure.py's OB and
 *                 BOS/CHOCH cases: /api/data carries no per-strike chain).
 * "We checked and found nothing" is a different statement from "we could not
 * check", and both differ again from "we are not showing you".
 */
export type StructureConfirm = 'CONFIRMED' | 'UNCONFIRMED' | 'UNKNOWN'

export interface Structure {
  kind: StructureKind
  /** Span the structure was read from. Indices into the day's UNFILTERED
   *  `bars` array — see `tapeBars`'s skip guard for why that matters. */
  i0: number
  i1: number
  /** The bar that COMPLETED the structure; `born >= i1`. Every field of a
   *  structure is a function of bars[0..born] only, so causal replay is
   *  truncation (`born <= cursor`), never recomputation. */
  born: number
  /** For area structures (FVG, OB, EQH, EQL) these bound the box. For point
   *  structures (BOS, CHOCH, SWING_H, SWING_L) `hi === lo` — the single price
   *  the structure is about (verified against a real 329-bar NIFTY session:
   *  every BOS/CHOCH row came back with hi === lo === the broken level). */
  hi: number
  lo: number
  /** +1 for anything bullish / high-side, −1 for its mirror. */
  dir: 1 | -1
  confirm: StructureConfirm
  /** The backend's own sentence for the verdict, quoted verbatim. */
  confirm_why: string
}

// ── Band-rotation signals on the INDEX (band_rotation.detect_index) ────────────
// The operator's OWN setup — a band extreme with a same-bar reversal — run
// server-side on the index's own bars and attached to each day of /api/data as
// a sibling of `bars`, one slot per bar, null where nothing fired. This file
// only NAMES the wire shape; no signal is derived, filtered or re-judged here.

/** Which σ band the bar pierced. The backend's asymmetry (buy the −2/−3σ
 *  extreme, sell only the +3σ one) is the operator's own, so there is no
 *  'u2' — a +2σ reversal is deliberately not a sell. */
export type RotationBand = 'd2' | 'd3' | 'u3'

/**
 * `confirm` is ALWAYS 'UNKNOWN' on an index signal, and that is structural,
 * not a data gap: confirmation asks whether the OPPOSITE option leg is
 * rotating and whether OI is decelerating on both books, and a single index
 * series has neither. `confirm_why` carries the backend's own sentence saying
 * so. It must never be rendered as, or rounded to, a confirmation.
 */
export interface RotationSignal {
  /** Index into the day's UNFILTERED `bars` — the same caveat `Structure`
   *  carries, and guarded the same way in `tapeBars`. */
  i: number
  /** The bar's own "HH:MM" label, or null when the bar carried none. */
  t: string | null
  side: 'BUY' | 'SELL'
  /** 'index' for these. Never 'CE'/'PE' — an index signal must not be
   *  bucketed with an option-leg one. */
  leg: string
  band: RotationBand
  /** The backend's own receipt for the trigger, quoted verbatim. */
  trigger: string
  /** Hits that lost a per-bar tie-break. Always null on the index path —
   *  there is no other leg that could have lost one. */
  also: string[] | null
  confirm: StructureConfirm
  confirm_why: string
  /** What the index's own VWAP band was doing BEFORE the move. */
  trap: 'CLEAR' | 'SUSPECT' | 'UNKNOWN'
  trap_why: string
  /** Index bars the band held that width, or null where never measured. */
  trap_dwell: number | null
  /** Only on `rotationRun` records — the bar whose low armed the setup, the
   *  high that had to break, and how many bars the trigger waited for it.
   *  Absent on `rotation` records, which have no reference candle at all. */
  ref_i?: number
  ref_high?: number
  level?: number
  waited?: number
}

/** Where the operator's two-candle setup stands on ONE bar (`run_state`).
 *
 *  `rotationRun` answers "where did it fire"; this answers "where does it
 *  stand right now", which is what a state display reads. Both come out of one
 *  loop in `band_rotation.run_states` — see there for why a second
 *  implementation of this machine is not allowed to exist.
 */
export interface RunState {
  i: number
  t: string | null
  state: 'WAITING' | 'ARMED' | 'TRIGGERED' | 'IN_TRADE'
  /** The live reference candle: the bar whose low touched d3. */
  ref_i: number | null
  /** The high that has to break for this to trigger. BUY side only. */
  ref_high?: number | null
  /** The SELL mirror's line: the low that has to break. Named for what it IS
   *  -- a low carried under `ref_high` would be a lie a reader cannot catch. */
  ref_low?: number | null
  /** The band the reference tagged — the stop is `level` minus 20. */
  level: number | null
  /** Bars left of the window before the reference expires. */
  candles_left: number | null
  /** Non-null only on a TRIGGERED bar; identical to `rotationRun[i]`. */
  entry: RotationSignal | null
  /** Set on the bar the re-fire lock cleared. OUT is not a state because a
   *  bar can clear the lock AND arm the next setup — see `run_states`. */
  exit_why: 'stop' | 'vwap' | null
  /** False when the bar carried no usable read. The state is then the one it
   *  is still IN, not WAITING: a missing read is not evidence the setup went
   *  away, and WAITING would blink a live reference off the screen. */
  readable: boolean
}

/**
 * What the Tape Chart reads per index: the day's FUT bars plus the structure
 * layer and the band-rotation signals that index them.
 *
 * `structures` / `rotation` are null whenever those indices cannot be trusted,
 * and the matching `*Why` then says why in the backend's/our own words. A null
 * is a disclosure, not a silent absence — TradeTab prints it.
 */
export interface TapeView {
  day: string
  bars: TapeBar[]
  /** The engine's tracked ATM strike for this session (`day.strike` on the
   *  wire) — the strike the bars' ce/pe legs belong to as of the newest bar.
   *  Sticky but ROLLING: it migrates with spot, so it names where the leg
   *  series currently lives, not where every bar of it was. null when the
   *  payload doesn't carry it. */
  strike: number | null
  /** Prior-session floor pivots per option leg (`opt_pivots` on the wire), or
   *  null when the backend doesn't publish them. */
  optPivots: OptPivots | null
  /** Which expiry the ce/pe legs, their pivots and t_days belong to
   *  (`opt_expiry`) — the NEAREST expiry, the one the operator trades. */
  optExpiry: string | null
  structures: Structure[] | null
  /** Empty string when `structures` is non-null. */
  structuresWhy: string
  /** One slot per bar, 1:1 with `bars`; null inside the array where nothing
   *  fired, and the WHOLE array null when it cannot be aligned honestly. */
  rotation: (RotationSignal | null)[] | null
  /** Empty string when `rotation` is non-null. */
  rotationWhy: string
  /** §5c's TWO-CANDLE entries — the rule the operator actually trades. Same
   *  slot-per-bar contract as `rotation`, and the same record shape, but a
   *  DIFFERENT bar: `rotation` marks the d3 touch, this marks the close that
   *  breaks the touching bar's high. Null on a backend too old to publish it,
   *  which is a thing to say out loud rather than fall back from. */
  rotationRun: (RotationSignal | null)[] | null
  /** Empty string when `rotationRun` is non-null. */
  rotationRunWhy: string
  /** §5c's SELL mirror -- u3 tag, then a close BELOW the reference candle's
   *  low. Published under its own key and never merged into `rotationRun`:
   *  merging would change what that array has always meant for every existing
   *  reader. Built 2026-08-08 on the operator's explicit instruction, over a
   *  REJECTED verdict (CHECKLIST C3) -- so it may be drawn, and must never be
   *  presented as carrying the buy rule's measured hit rate. */
  rotationRunSell: (RotationSignal | null)[] | null
  rotationRunSellWhy: string
  /** The same machine read per bar rather than per entry. One slot per bar. */
  runState: RunState[] | null
  /** Empty string when `runState` is non-null. */
  runStateWhy: string
}

// Live Spike Radar — one row per index, one cell per activity/spike column.
export const HEAT_COLS = ['FUT VOL', 'FUT OI', 'CE VOL', 'CE OI', 'PE VOL', 'PE OI', 'GAMMA', 'SQZ'] as const
export type HeatCol = (typeof HEAT_COLS)[number]
export type HeatTone = 'bull' | 'bear' | 'neutral'
export interface HeatCell {
  label: string
  intensity: number // 0..1
  dir: HeatTone
  spike: boolean
}

// Intraday Pressure Tape — bucketed net order-flow, val in [-1, 1] (buy +, sell −).
export interface PressCell {
  t: string
  tEnd: string
  val: number
  price: number
  note: string
}

// Levels Map — real action-zone price levels.
export type MapLevelKind =
  | 'now' | 'pivot' | 'wall' | 'vwap' | 'band' | 'pin' | 'floor' | 'cap' | 'strike' | 'trap' | 'session'
export interface MapLevel {
  label: string
  value: number
  kind: MapLevelKind
  note: string
}
export interface MapData {
  now: number
  zoneLo: number
  zoneHi: number
  levels: MapLevel[]
}

export interface Dataset {
  INDICES: Record<IndexKey, IndexInfo>
  READS: Record<IndexKey, Read>
  KEY_LEVELS: Record<IndexKey, Level[]>
  ORDER_FLOW: Record<IndexKey, OrderFlow>
  CHAIN_DATA: Record<IndexKey, Chain>
  EVENTS_BY_IDX: Record<IndexKey, EventItem[]>
  /** Same narrative with the repetition removed; see buildFocusFeed. */
  FOCUS_BY_IDX: Record<IndexKey, EventItem[]>
  CHART_DATA: Record<IndexKey, ChartPoint[]>
  HEAT: Record<IndexKey, HeatCell[]>
  PRESSURE: Record<IndexKey, PressCell[]>
  MAP: Record<IndexKey, MapData>
}

const KEYS: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']

// ── Per-index bundle (pre-highlight) ────────────────────────────────────────────
interface PerIndex {
  index: IndexInfo
  score: number
  read: Read
  levels: Level[]
  flow: OrderFlow
  chain: Chain
  events: EventItem[]
  focus: EventItem[]
  chart: ChartPoint[]
  heat: HeatCell[]
  pressure: PressCell[]
  map: MapData
}

// ── Mapping helpers ─────────────────────────────────────────────────────────────
const VERDICT_SCORE: Record<string, number> = {
  GO: 3, READY: 2, WAIT: 0, CAUTION: 0, 'STAND ASIDE': -1, SPENT: -1,
}

// Spike-radar gamma intensity by dealer regime.
const GAMMA_INT: Record<string, number> = {
  'AMPLIFIED-UP': 1, 'AMPLIFIED-DOWN': 1, PINNED: 0.6, CEILING: 0.5, FLOOR: 0.5, BALANCE: 0.2,
}
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))
const clamp01 = (n: number) => clamp(n ?? 0, 0, 1)

const MM_TEXT: Record<string, string> = {
  FLOOR: 'Dealers defend dips — put wall below.',
  CEILING: 'Dealers cap rallies — call wall above.',
  PINNED: 'Dealers pin price to the strike — mean-reverting.',
  'AMPLIFIED-UP': 'Negative gamma up — dealers chase rallies (moves accelerate).',
  'AMPLIFIED-DOWN': 'Negative gamma down — dealers amplify declines.',
  BALANCE: 'Neutral hedging — no strong dealer flow.',
  NEUTRAL: 'Neutral hedging — no strong dealer flow.',
}

const EVENT_PREFIX: Record<string, string> = {
  'TRAP-SPRUNG': 'Fake move sprung — late traders trapped: ',
  'SQUEEZE-RISK': 'Squeeze risk building: ',
  DIVERGENCE: 'Move not confirmed by options: ',
  'GAMMA-PIN': 'Dealers pinning price: ',
  CAMPAIGN: 'Writers pressing: ',
  PRESS: 'Positioning rotating: ',
  BREAK: 'Level broken: ',
  'OI-PEAK-LAG': 'Late conviction unwinding: ',
}

function trimMsg(s: string, n = 150): string {
  if (!s) return ''
  return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s
}

/**
 * Direction of an event, per kind. A keyword scan cannot do this: "BULL TRAP
 * SPRUNG" contains BULL but is bearish, and "PE writers add" is bullish while
 * naming the put side. Ported from ui/app.js evDir, which is the authority.
 */
function evDir(e: any): -1 | 0 | 1 {
  const k = e?.kind
  const m = String(e?.msg ?? '').toUpperCase()
  const s = e?.data?.side
  if (k === 'BAND-REVERSAL') return m.includes('+2') ? -1 : m.includes('-2') ? 1 : 0
  if (k === 'TRAP-SPRUNG' || k === 'TRAP-SETTING')
    return m.includes('BULL') ? -1 : m.includes('BEAR') ? 1 : 0
  if (k === 'PRESS' || k === 'CAMPAIGN' || k === 'BUYER-BUILD')
    return m.includes('BULLISH') ? 1 : m.includes('BEARISH') ? -1 : 0
  if (k === 'OI-PEAK-LAG') return m.includes('UPWARD') ? 1 : m.includes('DOWNWARD') ? -1 : 0
  if (k === 'SQUEEZE-RISK') return m.includes('UPSIDE') ? 1 : m.includes('DOWNSIDE') ? -1 : 0
  if (k === 'DIVERGENCE') return m.includes('HIGH') ? -1 : m.includes('LOW') ? 1 : 0
  // ABSORPTION names the side whose effort produced NO result: engine.py sets
  // `side = "sellers" if C < O else "buyers"` and prints "<side> hitting a
  // wall". Sellers hitting a wall is a down-bar that could not make range —
  // the wall held, so it reads UP; buyers hitting a wall is its mirror. This
  // is the engine's own filing rather than an interpretation: the same branch
  // writes trap_ev["UP"] for buyers and trap_ev["DN"] for sellers, i.e. the
  // side that failed is the side that gets trapped.
  if (k === 'ABSORPTION')
    return m.includes('SELLERS HITTING') ? 1 : m.includes('BUYERS HITTING') ? -1 : 0
  // GAMMA-PIN opens with its regime. FLOOR is "put wall below — dips into the
  // strike get absorbed; upside is NOT capped"; CEILING is the mirror. PINNED
  // says "dampens BOTH ways", which is not a direction and stays 0 — the whole
  // point of that regime is that neither side is favoured.
  if (k === 'GAMMA-PIN')
    return m.startsWith('FLOOR') ? 1 : m.startsWith('CEILING') ? -1 : 0
  if (k === 'IGNITION') return m.startsWith('UP') || m.includes('UP:') ? 1 : -1
  if (k === 'ARMED' || k === 'SPRING') return s === 'UP' ? 1 : s === 'DN' ? -1 : 0
  if (k === 'WALL-MIGRATION' || k === 'ROLE-FLIP') return s === 'UP' ? 1 : s === 'DN' ? -1 : 0
  return 0
}

function eventDir(e: any): 'bull' | 'bear' | 'neutral' {
  const d = evDir(e)
  return d > 0 ? 'bull' : d < 0 ? 'bear' : 'neutral'
}

/** Kinds loud enough to speak even when the log just said the same thing. */
const LOUD = new Set([
  'ARMED', 'SPRING', 'IGNITION', 'CLIMAX', 'TRAP', 'CARRY', 'SQUEEZE-RELEASE',
  'TRAP-SPRUNG', 'SPRING-FAIL', 'OI-PEAK-LAG', 'BAND-REVERSAL', 'BAND-BREAK',
  'WALL-MIGRATION', 'ROLE-FLIP',
])

/**
 * FOCUS: the same narrative with the repetition taken out. Ported from
 * ui/app.js buildFocusFeed, where it cut a live expiry day's log by ~40%.
 *
 * Four rules, in order: drop pure state churn and low-grade band tags; a
 * kind+direction may not repeat inside 10 minutes; a QUIET kind repeating the
 * direction the log just gave (within 8 min) is the same story, not new
 * evidence; and a single minute holding both bull and bear evidence collapses
 * to one CONFLICT line rather than printing a contradiction as two facts.
 */
function buildFocusFeed(events: any[]): any[] {
  const tmin = (t: string) => +t.slice(0, 2) * 60 + +t.slice(3, 5)
  const lastShown: Record<string, number> = {}   // kind|dir -> minute emitted
  const lastDir: Record<string, number> = {}     // dir -> minute a line showed
  const out: any[] = []
  const byT = new Map<string, any[]>()
  for (const e of events) {
    if (e.kind === 'STATE' || e.kind === 'TRAP-SETTING') continue
    if (e.kind === 'BAND-REVERSAL' && String(e.msg ?? '').includes('[LOW]')) continue
    if (!byT.has(e.t)) byT.set(e.t, [])
    byT.get(e.t)!.push(e)
  }
  for (const [t, group] of byT) {
    const bulls = group.filter((e) => evDir(e) > 0)
    const bears = group.filter((e) => evDir(e) < 0)
    const rest = group.filter((e) => evDir(e) === 0)
    const emit = (e: any) => {
      const d = evDir(e)
      const key = e.kind + '|' + d
      if (lastShown[key] !== undefined && tmin(t) - lastShown[key] <= 10) return
      if (d && !LOUD.has(e.kind)
          && lastDir[d] !== undefined && tmin(t) - lastDir[d] <= 8) return
      lastShown[key] = tmin(t)
      if (d) lastDir[d] = tmin(t)
      out.push(e)
    }
    if (bulls.length && bears.length) {
      rest.forEach(emit)
      emit({
        t, kind: 'CONFLICT',
        msg: `mixed evidence this minute — bull: ${bulls.map((e) => e.kind).join('+')} `
          + `vs bear: ${bears.map((e) => e.kind).join('+')} — no clean read, stand aside`,
      })
    } else {
      rest.forEach(emit)
      for (const side of [bulls, bears]) {
        if (!side.length) continue
        if (side.length === 1) { emit(side[0]); continue }
        const lead = side[0]
        side.slice(1).forEach((e) => { lastShown[e.kind + '|' + evDir(e)] = tmin(t) })
        emit({ ...lead, agree: side.slice(1).map((e) => e.kind) })
      }
    }
  }
  return out
}

// The poller round-robins all three indices roughly every 15s, so 90s of
// silence means several missed cycles, not one slow tick. This matches the
// existing TAPE STALE threshold, so the two banners agree on what "stale"
// means to the operator.
export const CHAIN_STALE_S = 90

/**
 * Seconds since the chain snapshot was published, or null when that is
 * unknowable (no chain yet, or an older backend that never sent `builtAt`).
 * Callers must treat null as "unknown", never as "fresh" — a missing
 * timestamp is not evidence of a live payload.
 */
export function chainAgeS(c: Chain | undefined, nowMs = Date.now()): number | null {
  if (c?.builtAt == null) return null
  return (nowMs / 1000) - c.builtAt
}

// De-dup near-equal level values (within `tol` pts), keeping the first seen.
/** Round to one decimal, preserving null — a level we could not place stays
 *  absent rather than becoming 0. */
function round1(v: number | null): number | null {
  return v == null ? null : Math.round(v * 10) / 10
}

/** An implied vol as a percent, or an em-dash when the solver had no answer. */
function ivPct(v: number | null | undefined): string {
  return typeof v === 'number' && v > 0 ? `${(v * 100).toFixed(1)}%` : '—'
}

function dedupLevels(levels: Level[], tol = 2): Level[] {
  const out: Level[] = []
  for (const lvl of levels) {
    if (out.some((k) => Math.abs(k.value - lvl.value) <= tol)) continue
    out.push(lvl)
  }
  return out
}

/**
 * Map one index's payloads into display shapes.
 *
 * `at` is a bar index for replay. Everything bar-derived is truncated to that
 * bar so the screen shows what was knowable THEN — no reading ahead. The
 * option chain is the exception and is handled separately: it arrives as a
 * live snapshot with no per-strike history, so scrubbing borrows the closest
 * `series` sample at or before the bar and flags the ladder as live-only.
 */
function mapIndex(D: any, C: any, at?: number): PerIndex {
  const day = D.days[D.days.length - 1]
  const allBars: any[] = day.bars ?? []
  const at_ = at == null ? allBars.length - 1
    : Math.max(0, Math.min(at, allBars.length - 1))
  const bars = at == null ? allBars : allBars.slice(0, at_ + 1)
  const b = bars[bars.length - 1]
  /** Nothing timestamped after this bar may appear anywhere on the screen. */
  const cutoff: string = b?.t ?? '23:59'
  const f = b.fut
  const ctx = b.ctx
  const g = b.gamma
  const o = bars[0].fut.o
  const m = C?.metrics ?? {}

  // INDICES
  const change = f.c - o
  const pct = o ? (change / o) * 100 : 0
  const arrow = pct > 0.1 ? '▲' : pct < -0.1 ? '▼' : '〰'
  const episode: string = ctx.episode || ''
  const verdict: string = ctx.verdict || ''
  const breadth: string = ctx.breadth || ''
  const state = (episode
    ? episode.split('—')[0].trim()
    : verdict
  ).toLowerCase()

  const regime: string = g?.regime || ''
  const score =
    (episode.includes('MOVE RUNNING') || state.includes('trend') || regime.startsWith('AMPLIFIED') ? 3 : 0) +
    (VERDICT_SCORE[verdict] ?? 0) +
    (breadth.includes('STRONG') ? 2 : breadth.includes('LEAN') ? 1 : 0) +
    ((ctx.rng_r ?? 0) >= 0.3 ? 1 : 0)

  const index: IndexInfo = { price: f.c, change, pct, state, arrow }

  // READS
  const direction = breadth.includes('BULL') ? 'BULLISH' : breadth.includes('BEAR') ? 'BEARISH' : 'NEUTRAL'
  const read: Read = {
    headline: ctx.episode || ctx.vwhy || '—',
    timing: verdict || 'WAIT',
    direction,
    sub: ctx.plays?.[0] || `Reclaim VWAP ${Math.round(f.vwap)} to confirm a turn.`,
  }

  // KEY_LEVELS. The chain quotes its walls against the INDEX; every level
  // here is drawn against the FUTURES tape. That gap was 72 points on
  // 2026-08-04 — more than a full strike step — so an unconverted wall lands
  // on the wrong side of price. `basis` is measured server-side once per
  // refresh (live.build_payload) and is null whenever the chain could not be
  // read; in that case we show no wall at all rather than one we know is
  // displaced. A missing level is a smaller lie than a misplaced one.
  const basis: number | null = typeof D.basis === 'number' ? D.basis : null
  const toTape = (v: number | null | undefined): number | null =>
    v == null || basis == null ? null : v + basis
  const wallUp = toTape(m.wall_up)
  const wallDn = toTape(m.wall_dn)
  const capV = ctx.cap ? ctx.cap[1] : undefined
  const floorV = ctx.floor ? ctx.floor[1] : undefined
  const raw: Level[] = []
  if (ctx.cap) raw.push({ label: 'CAP', value: ctx.cap[1], note: ctx.cap[0], dist: 0, dir: 'up' })
  raw.push({ label: 'VWAP', value: f.vwap, note: 'reclaim = turn', dist: 0, dir: 'up' })
  if (wallUp != null && (capV == null || Math.abs(wallUp - capV) > 2) && (floorV == null || Math.abs(wallUp - floorV) > 2))
    raw.push({ label: 'RES', value: wallUp, note: 'call wall', dist: 0, dir: 'up' })
  if (wallDn != null && (capV == null || Math.abs(wallDn - capV) > 2) && (floorV == null || Math.abs(wallDn - floorV) > 2))
    raw.push({ label: 'SUP', value: wallDn, note: 'put wall', dist: 0, dir: 'down' })
  raw.push({ label: 'NOW', value: f.c, note: 'last price', dist: 0, dir: 'here' })
  if (ctx.floor) raw.push({ label: 'FLR', value: ctx.floor[1], note: ctx.floor[0], dist: 0, dir: 'down' })

  const levels: Level[] = dedupLevels(raw)
    .map((lvl) => {
      if (lvl.label === 'NOW') return { ...lvl, dist: 0, dir: 'here' as const }
      const dist = Math.round(lvl.value - f.c)
      return { ...lvl, dist, dir: (lvl.value > f.c ? 'up' : lvl.value < f.c ? 'down' : 'here') as Level['dir'] }
    })
    .sort((a, b2) => b2.value - a.value)
    .slice(0, 6)

  // ORDER_FLOW
  const n = bars.length
  const prev6 = bars[Math.max(0, n - 6)].fut
  const priceDir = Math.sign(f.c - prev6.c)
  const futOiUp = f.oi_slope > 0
  const phrase1 = futOiUp && priceDir < 0
    ? 'Fresh shorts building'
    : futOiUp && priceDir > 0
    ? 'Longs adding into the move'
    : f.oi_slope < 0
    ? 'Positions covering'
    : 'Flat positioning'
  const premRecovering = f.prem_d > prev6.prem_d
  const phrase2 = premRecovering
    ? 'futures discount refilling (selling easing)'
    : 'discount widening (sellers pressing)'
  const priorVols: number[] = bars.slice(Math.max(0, n - 6), n - 1).map((x: any) => x.fut.v)
  const avgVol = priorVols.length ? priorVols.reduce((s, v) => s + v, 0) / priorVols.length : f.v
  const volFalling = f.v < avgVol * 0.7
  const phrase3 = volFalling ? 'volume drying up — move decelerating' : 'volume steady'
  const flow: OrderFlow = {
    main: `${phrase1}. ${phrase2}. ${phrase3}.`,
    mm: MM_TEXT[regime] || MM_TEXT.NEUTRAL,
    stats: [
      { label: 'Realized σ', value: `${(f.z ?? 0).toFixed(2)}σ` },
      { label: '30m Range', value: `${Math.round(ctx.rng30 ?? 0)} pts · p${Math.round((ctx.rng_r ?? 0) * 100)}` },
      // A null IV means the solver could not price that leg — it is NOT zero
      // volatility. `?? 0` rendered "unsolvable" as a confident "0.0%" all
      // through 2026-08-04, which is the one thing this app is not allowed
      // to do: invent a number where it has none.
      { label: 'ATM IV', value: `${ivPct(g?.iv_ce)} / ${ivPct(g?.iv_pe)}` },
    ],
  }

  // CHAIN_DATA. In replay, borrow the nearest `series` sample at or before
  // this bar instead of showing the live chain against a past bar — that
  // lookahead is exactly what made v1's scrubbed reads non-causal.
  const ser: any[] = C?.series ?? []
  let hist: any = null
  if (at != null) {
    for (const p of ser) {
      if (String(p.ts ?? '').slice(0, 5) <= cutoff) hist = p
      else break
    }
  }
  const gexR = hist?.greg ?? m.gex_regime
  const sqScore = hist?.sq ?? m.squeeze?.score ?? 0
  const atm = C?.atm
  const cstrikes: any[] = C?.strikes ?? []
  let ai = cstrikes.findIndex((s) => s.k === atm)
  if (ai < 0) ai = Math.floor(cstrikes.length / 2)
  const slice = cstrikes.slice(Math.max(0, ai - 6), ai + 7)
  const strikes: StrikeRow[] = slice
    .map((s) => ({
      strike: s.k,
      ceOI: s.ce?.oi ?? 0,
      peOI: s.pe?.oi ?? 0,
      gex: s.gex ?? 0,
      ceW: s.ce_w ?? 0,
      peW: s.pe_w ?? 0,
      cePk: s.ce_pk ?? s.ce?.oi ?? 0,
      pePk: s.pe_pk ?? s.pe?.oi ?? 0,
      ceLtp: s.ce?.ltp ?? 0,
      peLtp: s.pe?.ltp ?? 0,
      ceIv: s.ce?.iv ?? 0,
      peIv: s.pe?.iv ?? 0,
      ceSpread: Math.max(0, (s.ce?.ask ?? 0) - (s.ce?.bid ?? 0)),
      peSpread: Math.max(0, (s.pe?.ask ?? 0) - (s.pe?.bid ?? 0)),
      type: (s.k === atm ? 'atm' : s.k === wallUp ? 'callwall' : s.k === wallDn ? 'putwall' : undefined) as StrikeRow['type'],
    }))
    .reverse() // highest strike on top, matching the design ladder
  const chain: Chain = {
    pcr: (hist?.pcr ?? m.pcr_oi ?? 0).toFixed(2),
    // Max pain and the gamma flip are chain numbers, quoted against the
    // INDEX. Converted here, at the one place they enter the app, so the
    // header chip, the chart level (App.tsx) and `mpDist` below cannot
    // disagree: on 2026-08-04 the chip read "MAX PAIN 24500 · -34" — below
    // price — while the backend's own mp_dist said +26 above it. Same
    // number, two frames, one screen. 0/null when basis is unknown; every
    // consumer already guards on `> 0` / null rather than drawing it.
    // Rounded because converting a strike leaves the basis's decimals on a
    // number that reads as a level ("24571.05" is false precision on a
    // 50-point grid); one point is nothing on a 24,500 level.
    maxPain: Math.round(toTape(hist?.mp ?? m.max_pain) ?? 0),
    flipPx: Number.isFinite(m.flip_px) ? round1(toTape(m.flip_px)) : null,
    ts: C?.ts ?? '',
    // null = an older backend that didn't publish built_at — staleness is
    // UNKNOWN, not fresh, so this must never be treated as "just now".
    builtAt: Number.isFinite(C?.built_at) ? C.built_at : null,
    spot: C?.spot ?? b?.fut?.c ?? 0,
    expiry: C?.expiry ?? '',
    atmStraddle: (() => {
      const a = cstrikes.find((s: any) => s.k === atm)
      return (a?.ce?.ltp ?? 0) + (a?.pe?.ltp ?? 0)
    })(),
    // false = the strike ladder below is the LIVE snapshot, not this bar's.
    // There is no per-strike history in the payload, so it cannot be replayed.
    aligned: at == null,
    gex: gexR === 'POSITIVE' ? 'Positive' : gexR === 'NEGATIVE' ? 'Negative' : 'Neutral',
    squeeze: sqScore > 0.3 ? 'High' : sqScore > 0.1 ? 'Medium' : 'Low',
    strikes,
    mpDist: m.mp_dist ?? ((m.max_pain ?? 0) - (C?.spot ?? 0)),
    gexSpot: m.gex_spot ?? 0,
    bookZone: Array.isArray(m.book_zone) && m.book_zone.length === 2
      ? [m.book_zone[0], m.book_zone[1]] : null,
    // default TRUE: an older backend that omits the field should not make the
    // UI cry "outside the books" on every tick
    inBookZone: m.in_book_zone !== false,
  }

  // EVENTS — engine narrative PLUS the chain's structural events. The engine
  // only watches books at one ATM strike, so a wall changing hands is
  // invisible to it: on 2026-07-28 the 24,000 strike flipped ceiling->floor in
  // the morning and back in the afternoon, each the decisive move of its half
  // of the session, and neither produced a single line of narrative.
  const wallLog: any[] = (C?.metrics?.wall_log ?? [])
    .filter((e: any) => String(e.ts ?? '').slice(0, 5) <= cutoff)
  const wallEvents: EventItem[] = wallLog.map((e) => ({
    time: String(e.ts ?? '').slice(0, 5),
    text: trimMsg(e.msg ?? ''),
    tag: e.kind ?? 'WALL',
    dir: e.side === 'UP' ? 'bull' : e.side === 'DN' ? 'bear' : 'neutral',
  }))
  const evs: any[] = (day.events ?? []).filter((e: any) => (e.t ?? '') <= cutoff)
  const toItem = (e: any): EventItem => ({
    time: e.t,
    // the "+N agreeing" tail is appended AFTER trimming so a merged chorus
    // never loses the very thing that makes it a chorus
    text: (EVENT_PREFIX[e.kind] || '') + trimMsg(e.msg)
      + (e.agree?.length ? ` · +${e.agree.length} agreeing: ${e.agree.join(', ')}` : ''),
    tag: e.kind,
    dir: eventDir(e),
  })
  const byTime = (a: EventItem, b2: EventItem) =>
    a.time < b2.time ? -1 : a.time > b2.time ? 1 : 0
  // A wall changing hands is the headline of a session, so it must not be
  // croppable by however many ordinary events happened to fire after it.
  // Keep the last 10 overall PLUS the last 3 structural ones regardless.
  // A narrative log is only useful if you can read back through the session,
  // and FOCUS only demonstrates anything against a list long enough to have
  // repetition in it. The Events tab scrolls, so keep the day, not a window.
  const compose = (list: EventItem[]): EventItem[] => {
    const tail = [...list, ...wallEvents].sort(byTime).slice(-200)
    return Array.from(new Set([...tail, ...wallEvents.slice(-3)]))
      .sort(byTime).reverse()
  }
  const events = compose(evs.map(toItem))
  const focus = compose(buildFocusFeed(evs).map(toItem))

  // CHART_DATA
  const chart: ChartPoint[] = bars.map((bar: any) => ({
    time: bar.t,
    price: bar.fut.c,
    vwap: bar.fut.vwap,
    upper: bar.fut.u2,
    lower: bar.fut.d2,
    vol: bar.fut.v,
    isFuture: false,
  }))

  // HEAT — live spike radar: volume/OI ranks across futures + both option legs,
  // plus gamma regime (flip = spike) and squeeze. 8 cells in HEAT_COLS order.
  const ce = b.ce ?? {}
  const pe = b.pe ?? {}
  const prev4 = bars[Math.max(0, bars.length - 4)].fut
  const pDir4 = Math.sign(f.c - prev4.c)
  const pctLbl = (r: number) => `${Math.round((r ?? 0) * 100)}%`
  const gRegime: string = g?.regime || 'BALANCE'
  const gInt = GAMMA_INT[gRegime] ?? 0.3
  const gDir: HeatTone = /UP|FLOOR/.test(gRegime) ? 'bull' : /DOWN|CEILING/.test(gRegime) ? 'bear' : 'neutral'
  const prevRegime: string | undefined = bars[Math.max(0, bars.length - 15)]?.gamma?.regime
  const gammaFlip = prevRegime != null && prevRegime !== gRegime
  // squeeze.side is deliberately null when no book qualifies — and always null
  // inside the expiry squaring window, where chain-wide OI decay carries no
  // direction. Rendering that as "null 0.00" is worse than saying nothing.
  const sqz = { side: (m.squeeze?.side as string | null) ?? null, score: m.squeeze?.score ?? 0 }
  const heat: HeatCell[] = [
    { label: pctLbl(f.vol_r), intensity: clamp01(f.vol_r), dir: pDir4 > 0 ? 'bull' : pDir4 < 0 ? 'bear' : 'neutral', spike: (f.vol_r ?? 0) >= 0.8 },
    { label: pctLbl(f.oi_r), intensity: clamp01(f.oi_r), dir: f.oi_slope > 0 ? (pDir4 > 0 ? 'bull' : 'bear') : 'neutral', spike: (f.oi_r ?? 0) >= 0.8 },
    { label: pctLbl(ce.vol_r), intensity: clamp01(ce.vol_r), dir: ce.prem_d > 0 ? 'bull' : ce.prem_d < 0 ? 'bear' : 'neutral', spike: (ce.vol_r ?? 0) >= 0.8 },
    { label: pctLbl(ce.oi_r), intensity: clamp01(ce.oi_r), dir: ce.oi_slope > 0 ? (ce.prem_d < 0 ? 'bear' : 'bull') : 'neutral', spike: (ce.oi_r ?? 0) >= 0.8 },
    { label: pctLbl(pe.vol_r), intensity: clamp01(pe.vol_r), dir: pe.prem_d > 0 ? 'bear' : pe.prem_d < 0 ? 'bull' : 'neutral', spike: (pe.vol_r ?? 0) >= 0.8 },
    { label: pctLbl(pe.oi_r), intensity: clamp01(pe.oi_r), dir: pe.oi_slope > 0 ? (pe.prem_d < 0 ? 'bull' : 'bear') : 'neutral', spike: (pe.oi_r ?? 0) >= 0.8 },
    { label: gRegime, intensity: gInt, dir: gDir, spike: gammaFlip || gInt >= 0.9 },
    { label: sqz.side ? `${sqz.side} ${sqScore.toFixed(2)}` : 'NONE',
      intensity: sqz.side ? Math.min(1, sqScore / 0.4) : 0,
      dir: sqz.side === 'UP' ? 'bull' : sqz.side === 'DOWN' ? 'bear' : 'neutral',
      spike: !!sqz.side && sqScore >= 0.3 },
  ]

  // PRESSURE — bucketed net order-flow (≤ ~60 buckets) so it reads as a histogram,
  // not a per-minute barcode. Per-bar signed pressure, then averaged per bucket.
  const perBar = bars.map((bar: any, i: number) => {
    const oiUp = bar.fut.oi_slope > 0
    const pDir = i >= 3 ? Math.sign(bar.fut.c - bars[i - 3].fut.c) : 0
    const mag = bar.fut.oi_r ?? 0.3
    return clamp((oiUp ? 1 : -0.3) * pDir * mag, -1, 1)
  })
  const pStep = Math.max(3, Math.ceil(bars.length / 60))
  const pressure: PressCell[] = []
  for (let s = 0; s < bars.length; s += pStep) {
    const members = bars.slice(s, s + pStep)
    if (!members.length) continue
    const vals = perBar.slice(s, s + pStep)
    const val = vals.reduce((a: number, v: number) => a + v, 0) / vals.length
    const first = members[0]
    const last = members[members.length - 1]
    const dir = val > 0.03 ? 'buying' : val < -0.03 ? 'selling' : 'balanced'
    pressure.push({
      t: first.t,
      tEnd: last.t,
      val,
      price: last.fut.c,
      note: `${first.t}–${last.t} · net ${dir} ${Math.round(Math.abs(val) * 100)}%`,
    })
  }

  // MAP — real action-zone level map (parity with production ui/app.js renderMap).
  const now = f.c
  const eps = now * 0.0003
  const trapEps = now * 0.0004
  const rec = bars.slice(-120)
  const sesHi = Math.max(...rec.map((x: any) => x.fut.h))
  const sesLo = Math.min(...rec.map((x: any) => x.fut.l))

  const mapRaw: Array<{ level: MapLevel; prio: number }> = []
  const addLvl = (value: any, label: string, kind: MapLevelKind, note: string, prio: number) => {
    if (value == null || !isFinite(value)) return
    mapRaw.push({ level: { label, value: +value, kind, note }, prio })
  }
  addLvl(now, 'NOW', 'now', 'last price', 0)
  addLvl(wallUp, 'CALL', 'wall', 'call wall — resistance', 1)
  addLvl(wallDn, 'PUT', 'wall', 'put wall — support', 1)
  // PIN and STK below are STRIKES — index-frame numbers — while this axis is
  // the futures tape. Unconverted on 2026-08-04 the dealer magnet drew ~60
  // points low and on the WRONG SIDE of price, sitting below NOW while the
  // CALL wall on the very same strike (already converted) sat correctly
  // above it. Two levels naming the same strike, 60 points apart.
  if (ctx.pin?.k != null)
    addLvl(toTape(ctx.pin.k), 'PIN', 'pin', `dealer magnet (${ctx.pin.regime})`, 2)
  const piv = day.pivots || {}
  for (const key of ['R3', 'R2', 'R1', 'P', 'S1', 'S2', 'S3']) addLvl(piv[key], key, 'pivot', 'pivot', 3)
  addLvl(f.vwap, 'VWAP', 'vwap', 'fair value', 4)
  if (ctx.floor) addLvl(ctx.floor[1], 'FLR', 'floor', String(ctx.floor[0]), 5)
  if (ctx.cap) addLvl(ctx.cap[1], 'CAP', 'cap', String(ctx.cap[0]), 5)
  addLvl(f.u1, '+1σ', 'band', 'volatility band', 6)
  addLvl(f.d1, '−1σ', 'band', 'volatility band', 6)
  addLvl(toTape(day.strike), 'STK', 'strike', 'ATM strike', 7)
  addLvl(sesHi, 'HI', 'session', 'session high', 8)
  addLvl(sesLo, 'LO', 'session', 'session low', 8)
  // Traps: resolve each trap event's price by its bar's close, dedupe by price, keep latest, max 3.
  const tClose: Record<string, number> = {}
  for (const bar of bars) tClose[bar.t] = bar.fut.c
  const trapKinds = new Set(['TRAP-SPRUNG', 'TRAP-SETTING', 'SPRING-FAIL'])
  // `evs`, not day.events — the latter ignores the replay cutoff, and since
  // slice(-6) would then be filled by traps that have not happened yet (whose
  // bars resolve to null and get dropped), the map quietly lost its REAL
  // traps while scrubbed.
  const trapEvs = evs.filter((e: any) => trapKinds.has(e.kind)).slice(-6)
  const traps: Array<{ p: number; t: string; kind: string }> = []
  for (const e of [...trapEvs].reverse()) {
    const p = tClose[e.t]
    if (p == null) continue
    if (traps.length < 3 && !traps.some((x) => Math.abs(x.p - p) < trapEps)) traps.push({ p, t: e.t, kind: e.kind })
  }
  for (const tr of traps) addLvl(tr.p, 'TRAP', 'trap', `${tr.kind} ${tr.t}`, 9)

  // De-dupe near-equal values, keeping the higher-priority (lower prio number) one.
  mapRaw.sort((a, b) => a.prio - b.prio)
  const kept: MapLevel[] = []
  for (const { level } of mapRaw) {
    if (kept.some((k) => Math.abs(k.value - level.value) <= eps)) continue
    kept.push(level)
  }

  // Action zone: the near-price cluster (never let a far spike crush the scale).
  const zonePts = [now, f.vwap, f.u1, f.d1, sesLo, sesHi]
  if (ctx.floor) zonePts.push(ctx.floor[1])
  if (ctx.cap) zonePts.push(ctx.cap[1])
  if (wallUp != null && Math.abs(wallUp - now) < now * 0.02) zonePts.push(wallUp)
  if (wallDn != null && Math.abs(wallDn - now) < now * 0.02) zonePts.push(wallDn)
  const valid = zonePts.filter((v) => v != null && isFinite(v))
  let zLo = Math.min(...valid)
  let zHi = Math.max(...valid)
  const zpad = (zHi - zLo) * 0.12 || now * 0.001
  zLo -= zpad
  zHi += zpad

  const map: MapData = { now, zoneLo: zLo, zoneHi: zHi, levels: kept.sort((a, b) => b.value - a.value) }

  return { index, score, read, levels, flow, chain, events, focus, chart, heat, pressure, map }
}

// Reverse a fallback Dataset into per-index bundles (score 0) for last-good seeding.
function perFromFallback(fb: Dataset): Record<IndexKey, PerIndex> {
  const out = {} as Record<IndexKey, PerIndex>
  for (const k of KEYS) {
    const { highlight, ...rest } = fb.INDICES[k]
    void highlight
    out[k] = {
      index: rest,
      score: 0,
      read: fb.READS[k],
      levels: fb.KEY_LEVELS[k],
      flow: fb.ORDER_FLOW[k],
      chain: fb.CHAIN_DATA[k],
      events: fb.EVENTS_BY_IDX[k],
      focus: fb.FOCUS_BY_IDX[k],
      chart: fb.CHART_DATA[k],
      heat: fb.HEAT[k],
      pressure: fb.PRESSURE[k],
      map: fb.MAP[k],
    }
  }
  return out
}

function assemble(per: Record<IndexKey, PerIndex>): Dataset {
  // Highlight = single index with the max tradeability score; ties → keep first.
  let maxK: IndexKey = KEYS[0]
  for (const k of KEYS) if (per[k].score > per[maxK].score) maxK = k

  const ds: Dataset = {
    INDICES: {} as Record<IndexKey, IndexInfo>,
    READS: {} as Record<IndexKey, Read>,
    KEY_LEVELS: {} as Record<IndexKey, Level[]>,
    ORDER_FLOW: {} as Record<IndexKey, OrderFlow>,
    CHAIN_DATA: {} as Record<IndexKey, Chain>,
    EVENTS_BY_IDX: {} as Record<IndexKey, EventItem[]>,
    FOCUS_BY_IDX: {} as Record<IndexKey, EventItem[]>,
    CHART_DATA: {} as Record<IndexKey, ChartPoint[]>,
    HEAT: {} as Record<IndexKey, HeatCell[]>,
    PRESSURE: {} as Record<IndexKey, PressCell[]>,
    MAP: {} as Record<IndexKey, MapData>,
  }
  for (const k of KEYS) {
    const p = per[k]
    ds.INDICES[k] = { ...p.index, highlight: k === maxK }
    ds.READS[k] = p.read
    ds.KEY_LEVELS[k] = p.levels
    ds.ORDER_FLOW[k] = p.flow
    ds.CHAIN_DATA[k] = p.chain
    ds.EVENTS_BY_IDX[k] = p.events
    ds.FOCUS_BY_IDX[k] = p.focus
    ds.CHART_DATA[k] = p.chart
    ds.HEAT[k] = p.heat
    ds.PRESSURE[k] = p.pressure
    ds.MAP[k] = p.map
  }
  return ds
}

// ── Hook ────────────────────────────────────────────────────────────────────────
// ── Trade validator ────────────────────────────────────────────────────────
// Replaces a mock that added Math.random() to its own confidence score and
// hardcoded two of its four gates to pass. Every check below is computed from
// the live chain or it is not shown.

export interface Gate {
  label: string
  detail: string
  verdict: 'pass' | 'warn' | 'fail'
}
export interface TradeCheck {
  ok: boolean
  premium: number
  breakeven: number
  moveNeeded: number      // points spot must travel to break even
  expectedMove: number    // what the market is pricing for the rest of session
  emRatio: number         // moveNeeded / expectedMove; > 1 = needs more than priced
  delta: number
  spreadPct: number
  intrinsic: number
  timeValue: number
  wall: { strike: number; oi: number } | null
  gates: Gate[]
  score: number           // 0-100, deterministic
  verdict: 'TAKE' | 'SMALL' | 'AVOID'
  headline: string
}

/** Standard normal CDF (Abramowitz & Stegun 7.1.26) — for delta, since the
 *  feed sends null greeks. */
function ncdf(x: number): number {
  const t = 1 / (1 + 0.2316419 * Math.abs(x))
  const d = 0.3989422804014327 * Math.exp(-x * x / 2)
  const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
    + t * (-1.821255978 + t * 1.330274429))))
  return x >= 0 ? 1 - p : p
}

const MIN_T = 1 / (365 * 24 * 6)        // ten minutes, in years

/** Years to expiry, always finite. The chain publishes expiry as "MOCK" in
 *  fixture mode and can omit it entirely, and an Invalid Date silently turns
 *  every downstream greek into NaN — which then renders as "delta NaN" and
 *  falls through to the wrong branch of the contract-fit gate. */
function yearsToExpiry(expiry: string, now = new Date()): number {
  const end = /^\d{4}-\d{2}-\d{2}$/.test(expiry)
    ? new Date(expiry + 'T15:30:00+05:30').getTime() : NaN
  if (!Number.isFinite(end)) return 1 / 365       // assume ~a day
  const t = (end - now.getTime()) / (365 * 24 * 3600 * 1000)
  return Number.isFinite(t) ? Math.max(t, MIN_T) : 1 / 365
}

/** Fraction of the trading session still to run (09:15–15:30 IST). */
function sessionLeft(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  if (!Number.isFinite(h)) return 0.5
  return clamp01((930 - (h * 60 + m)) / 375)
}

export function validateTrade(
  chain: Chain, read: Read, strike: number,
  side: 'CE' | 'PE', position: 'Long' | 'Short', nowHHMM: string,
): TradeCheck | null {
  const row = chain.strikes.find((s) => s.strike === strike)
  if (!row) return null

  const spot = chain.spot
  const premium = side === 'CE' ? row.ceLtp : row.peLtp
  const iv = side === 'CE' ? row.ceIv : row.peIv
  const spread = side === 'CE' ? row.ceSpread : row.peSpread
  if (!premium) return null

  const intrinsic = side === 'CE' ? Math.max(0, spot - strike) : Math.max(0, strike - spot)
  const timeValue = Math.max(0, premium - intrinsic)
  const breakeven = side === 'CE' ? strike + premium : strike - premium
  const moveNeeded = Math.abs(breakeven - spot)
  // What the market itself is charging for the remaining session
  const expectedMove = chain.atmStraddle * Math.sqrt(Math.max(sessionLeft(nowHHMM), 0.02))
  const emRatio = expectedMove > 0 ? moveNeeded / expectedMove : 99

  const T = yearsToExpiry(chain.expiry)
  const sig = iv > 0 ? iv : 0.12
  const d1 = (Math.log(spot / strike) + (sig * sig / 2) * T) / (sig * Math.sqrt(T))
  const callDelta = ncdf(d1)
  const delta = side === 'CE' ? callDelta : callDelta - 1

  const long = position === 'Long'
  const bullish = (side === 'CE') === long          // long call / short put = bullish
  const readBull = read.direction.toUpperCase().includes('BULL')
  const readBear = read.direction.toUpperCase().includes('BEAR')
  const aligned = (bullish && readBull) || (!bullish && readBear)
  const noEdge = !readBull && !readBear

  // Structure standing between spot and the target
  const between = chain.strikes.filter((s) =>
    bullish ? s.strike > spot && s.strike <= breakeven
            : s.strike < spot && s.strike >= breakeven)
  const wallRow = between.sort((a, b) =>
    (bullish ? b.ceOI - a.ceOI : b.peOI - a.peOI))[0]
  const wall = wallRow
    ? { strike: wallRow.strike, oi: bullish ? wallRow.ceOI : wallRow.peOI }
    : null

  const spreadPct = premium > 0 ? spread / premium : 0
  const gates: Gate[] = []

  gates.push(noEdge
    ? { label: 'Method read', detail: `${read.direction} — the method has no side right now`, verdict: 'warn' }
    : aligned
      ? { label: 'Method read', detail: `${read.direction} · ${read.timing} — trade agrees with it`, verdict: 'pass' }
      : { label: 'Method read', detail: `${read.direction} — this is the opposite bet`, verdict: 'fail' })

  gates.push(emRatio <= 0.6
    ? { label: 'Move required', detail: `${moveNeeded.toFixed(0)} pts to break even, well inside the ${expectedMove.toFixed(0)} pts priced`, verdict: 'pass' }
    : emRatio <= 1
      ? { label: 'Move required', detail: `${moveNeeded.toFixed(0)} pts to break even vs ${expectedMove.toFixed(0)} pts priced — most of the session's budget`, verdict: 'warn' }
      : { label: 'Move required', detail: `${moveNeeded.toFixed(0)} pts to break even, more than the ${expectedMove.toFixed(0)} pts the market is pricing`, verdict: 'fail' })

  const dAbs = Math.abs(delta)
  gates.push(!Number.isFinite(dAbs)
    // never invent a greek: say the input was missing and move on
    ? { label: 'Contract fit', detail: `delta unavailable (no usable IV or expiry) — ${intrinsic.toFixed(0)} pts intrinsic, ${timeValue.toFixed(1)} pts time value`, verdict: 'warn' }
    : dAbs >= 0.35 && dAbs <= 0.65
      ? { label: 'Contract fit', detail: `delta ${delta.toFixed(2)} — responsive without paying for intrinsic`, verdict: 'pass' }
      : dAbs < 0.35
        ? { label: 'Contract fit', detail: `delta ${delta.toFixed(2)} — needs a big move just to matter`, verdict: 'warn' }
        : { label: 'Contract fit', detail: `delta ${delta.toFixed(2)} — ${intrinsic.toFixed(0)} of the ${premium.toFixed(0)} premium is intrinsic, you are largely buying the future`, verdict: 'warn' })

  gates.push(chain.gex === 'Positive' && chain.inBookZone
    ? { label: 'Dealer regime', detail: 'positive gamma inside the book zone — dealers damp moves, directional premium fights the pin', verdict: long ? 'warn' : 'pass' }
    : chain.gex === 'Negative'
      ? { label: 'Dealer regime', detail: 'negative gamma — hedging extends moves, which favours the buyer', verdict: long ? 'pass' : 'warn' }
      : { label: 'Dealer regime', detail: `${chain.gex} gamma${chain.inBookZone ? '' : ', price outside the book zone'}`, verdict: 'warn' })

  if (wall) {
    gates.push({
      label: 'Structure in the way',
      detail: `${(wall.oi / 1e6).toFixed(1)}M ${bullish ? 'calls' : 'puts'} at ${wall.strike} sit between spot and your breakeven`,
      verdict: wall.oi > 20e6 ? 'fail' : wall.oi > 8e6 ? 'warn' : 'pass',
    })
  } else {
    gates.push({ label: 'Structure in the way', detail: 'no heavy book between spot and breakeven', verdict: 'pass' })
  }

  gates.push(spreadPct <= 0.02
    ? { label: 'Liquidity', detail: `bid-ask ${spread.toFixed(2)} on ${premium.toFixed(2)} (${(spreadPct * 100).toFixed(1)}%)`, verdict: 'pass' }
    : spreadPct <= 0.06
      ? { label: 'Liquidity', detail: `bid-ask ${(spreadPct * 100).toFixed(1)}% of premium — costs you on entry and exit`, verdict: 'warn' }
      : { label: 'Liquidity', detail: `bid-ask ${(spreadPct * 100).toFixed(1)}% of premium — too wide to trade cleanly`, verdict: 'fail' })

  const fails = gates.filter((g) => g.verdict === 'fail').length
  const warns = gates.filter((g) => g.verdict === 'warn').length
  const score = Math.max(0, Math.min(100,
    Math.round(100 - fails * 30 - warns * 12)))
  const verdict: TradeCheck['verdict'] = fails > 0 ? 'AVOID' : warns >= 2 ? 'SMALL' : 'TAKE'
  const headline =
    fails > 0
      ? `${gates.find((g) => g.verdict === 'fail')!.label.toLowerCase()} rules this out`
      : warns >= 2
        ? 'workable, but it is not a clean setup — size accordingly'
        : `${moveNeeded.toFixed(0)} pts to break even against ${expectedMove.toFixed(0)} priced, with the read behind it`

  return {
    ok: true, premium, breakeven, moveNeeded, expectedMove, emRatio, delta,
    spreadPct, intrinsic, timeValue, wall, gates, score, verdict, headline,
  }
}

/** Why one index has no usable tape this tick.
 *
 * `reachable` is the distinction the old `null` return threw away. A backend
 * answering "no bars yet for 2026-08-06" and a backend that is not running at
 * all produced the identical banner, and only one of them is fixed by pasting
 * a token. HANDOFF section 9: "we checked and found nothing" and "we could not
 * check" must never collapse into one rendering. */
type IdxResult =
  | { ok: true; per: PerIndex }
  | { ok: false; reachable: boolean; why: string }

/** A per-bar layer, or null with the reason it could not be trusted.
 *
 *  Every layer indexed by bar takes the same guard, because the failure is the
 *  same one: a marker drawn one bar off claims the operator's setup fired on a
 *  minute it did not. A length mismatch is a real disagreement about the bar
 *  list, so it is disclosed rather than papered over by padding or truncating.
 */
function alignPerBar<T>(
  raw: unknown, nBars: number, skipped: number, what: string,
): [T[] | null, string] {
  if (!Array.isArray(raw)) return [null, `this backend publishes no ${what}`]
  if (skipped > 0)
    return [null, `${skipped} bar${skipped === 1 ? '' : 's'} lacked a FUT leg, so the `
      + `${what} bar indices no longer line up with the chart`]
  if (raw.length !== nBars)
    return [null, `the backend sent ${raw.length} ${what} slot`
      + `${raw.length === 1 ? '' : 's'} for ${nBars} bars, so they cannot be `
      + 'lined up 1:1']
  return [raw as T[], '']
}

export type LiveError = 'unreachable' | 'no-data'

export function useLiveData(fallback: Dataset) {
  const [data, setData] = useState<Dataset>(fallback)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<LiveError | null>(null)
  /** The backend's own sentence for the failure, carried out verbatim rather
   *  than replaced with a guess about the cause. */
  const [errorWhy, setErrorWhy] = useState<string | null>(null)
  /** Which broker the running server is on, from /api/health. `null` means a
   *  backend too old to answer — which must read as unknown, never as Dhan. */
  const [broker, setBroker] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const lastGood = useRef<Record<IndexKey, PerIndex>>(perFromFallback(fallback))
  // Raw payloads are kept so replay can re-map any bar without re-fetching.
  const [raw, setRaw] = useState<Partial<Record<IndexKey, { D: any; C: any }>>>({})
  /** Indices with no usable tape right now — shown as unavailable, not faked. */
  const [dead, setDead] = useState<IndexKey[]>([])

  useEffect(() => {
    let alive = true

    const rawSeen: Partial<Record<IndexKey, { D: any; C: any }>> = {}

    async function fetchIdx(k: IndexKey): Promise<IdxResult> {
      let dr: Response
      let cr: Response
      try {
        ;[dr, cr] = await Promise.all([
          fetch('/api/data?idx=' + k),
          fetch('/api/chain?idx=' + k),
        ])
      } catch {
        // fetch() rejects ONLY on a transport failure — nothing listening, or
        // the dev-server proxy has nothing to forward to. This is the one case
        // that means "unreachable". Every branch below got an answer.
        return { ok: false, reachable: false, why: 'no answer on 8765' }
      }
      // A dev-server proxy answers 502/503/504 ON BEHALF of an upstream it
      // could not reach, so fetch resolving is NOT proof the backend is there.
      // Measured 2026-08-06 09:46 with the backend stopped: Vite returned 502
      // and the banner read "the backend is up but has no session yet" -- the
      // same collapse this function was written to fix, one layer up.
      if (dr.status >= 502 && dr.status <= 504)
        return { ok: false, reachable: false, why: `no answer on 8765 (proxy ${dr.status})` }
      if (!dr.ok || !cr.ok)
        return { ok: false, reachable: true, why: `HTTP ${dr.status}/${cr.status}` }
      let D: any
      let C: any
      try {
        ;[D, C] = await Promise.all([dr.json(), cr.json()])
      } catch {
        return { ok: false, reachable: true, why: 'unreadable response' }
      }
      // An index can fail on its own — no tape in this server mode, a bad
      // instrument, a build error — while the others are perfectly live.
      // Treat that as a failure for THIS index rather than rendering
      // whatever happens to be in the fallback under its name. The backend's
      // own sentence is carried out rather than replaced: "no bars yet for
      // 2026-08-06" is a market that has not opened, and the banner used to
      // render exactly that as an unreachable backend with an expired token.
      if (D?.live_error || !D?.days?.length)
        return { ok: false, reachable: true, why: D?.live_error || 'no session yet' }
      rawSeen[k] = { D, C }
      return { ok: true, per: mapIndex(D, C) }
    }

    async function tick() {
      const [results, health] = await Promise.all([
        Promise.all(KEYS.map(fetchIdx)),
        // Cheap, and answers whatever the tape is doing. It is the only route
        // that can say WHICH broker is serving, which the banner needs so it
        // stops naming a Dhan token while the tool runs on Upstox.
        fetch('/api/health').then((r) => (r.ok ? r.json() : null)).catch(() => null),
      ])
      if (!alive) return
      setBroker(health?.broker ?? null)
      const per = {} as Record<IndexKey, PerIndex>
      const down: IndexKey[] = []
      const fails: Extract<IdxResult, { ok: false }>[] = []
      KEYS.forEach((k, i) => {
        const r = results[i]
        if (r.ok) per[k] = r.per
        else {
          per[k] = lastGood.current[k]
          down.push(k)
          fails.push(r)
        }
      })
      setDead(down)
      lastGood.current = per
      setData(assemble(per))
      if (Object.keys(rawSeen).length) setRaw((r) => ({ ...r, ...rawSeen }))
      setLoading(false)
      setLastUpdated(new Date())
      if (fails.length === KEYS.length) {
        // Reachability is not per-index: one answer from ANY index — or from
        // /api/health — proves the backend is up, so the failure is about data
        // and not about the connection.
        const reachable = fails.some((f) => f.reachable) || health != null
        setError(reachable ? 'no-data' : 'unreachable')
        setErrorWhy(fails[0]?.why ?? null)
      } else {
        setError(null)
        setErrorWhy(null)
      }
    }

    tick()
    const id = setInterval(tick, 5000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  /** Bars available for replay on the active index (0 when not yet loaded). */
  const barCount = (k: IndexKey) => {
    const D = raw[k]?.D
    const days = D?.days
    return days?.length ? (days[days.length - 1].bars?.length ?? 0) : 0
  }

  /** Re-map every index at bar `at`, or null for live. Never re-fetches. */
  const at = (idx: number | null): Dataset => {
    if (idx == null) return data
    const per = {} as Record<IndexKey, PerIndex>
    for (const k of KEYS) {
      const r = raw[k]
      per[k] = r ? mapIndex(r.D, r.C, idx) : lastGood.current[k]
    }
    return assemble(per)
  }

  // Tape Chart: the newest day's FUT bars, verbatim and FULL — replay is done
  // by the chart engine's cursor (causal truncation), not by re-slicing here.
  const tapeBars = useCallback((k: IndexKey): TapeView => {
    const D = raw[k]?.D
    const day = D?.days?.[D.days.length - 1]
    // No session at all yet — this is the tab's own loading/no-tape state,
    // not a structure-layer availability fact, so there is no "why" to give:
    // TradeTab reads the empty `day` string itself as the signal to suppress
    // its structure disclosure, rather than parsing this string's wording.
    if (!day) {
      return {
        day: '', bars: [], strike: null, optPivots: null, optExpiry: null,
        structures: null, structuresWhy: '', rotation: null, rotationWhy: '',
        rotationRun: null, rotationRunWhy: '',
        rotationRunSell: null, rotationRunSellWhy: '',
        runState: null, runStateWhy: '',
      }
    }
    const bars: TapeBar[] = []
    // structure.py's indices address the day's UNFILTERED bar list, so the
    // skip below silently shifts every one of them. In practice the engine
    // emits a FUT leg on every bar (verified: 329/329 on the live 2026-07-30
    // NIFTY session), but "in practice" is not a guarantee, and a structure
    // layer drawn one bar off is worse than no structure layer at all.
    let skipped = 0
    for (const b of day.bars ?? []) {
      const f = b.fut
      if (!f) { skipped++; continue } // engine ≥ c91c9d5 always emits fut; guard for older backends
      bars.push({
        t: b.t, o: f.o, h: f.h, l: f.l, c: f.c, v: f.v, oi: f.oi,
        vwap: f.vwap, u1: f.u1, d1: f.d1, u2: f.u2, d2: f.d2, u3: f.u3, d3: f.d3,
        // Pass the whole block through — never reconstruct field-by-field —
        // so an unrecognized extra field the engine adds later still rides
        // along, and a bar predating the block gets `null`, never inherits.
        ctx: b.ctx ?? null, gamma: b.gamma ?? null, setup: b.setup ?? null,
        // The tracked ATM strike's option legs — the series the operator's
        // ±3σ trigger actually lives on. Same pass-through rule; null when
        // the leg didn't print that minute.
        ce: b.ce ?? null, pe: b.pe ?? null,
      })
    }
    // Verbatim in the normal case: not filtered, not re-sorted, not
    // re-confirmed. Anything else and the layer is withheld WITH a reason.
    let structures: Structure[] | null = null
    let structuresWhy = ''
    if (!Array.isArray(day.structures)) {
      structuresWhy = 'this backend publishes no structure layer'
    } else if (skipped > 0) {
      structuresWhy = `${skipped} bar${skipped === 1 ? '' : 's'} lacked a FUT leg, `
        + 'so the layer’s bar indices no longer line up with the chart'
    } else {
      // Verbatim, but not blind: a row whose `confirm` is not one of the three
      // known values still gets shown (never dropped for a wire surprise) —
      // normalised to UNKNOWN, the honest reading of "not recognised", with
      // the surprising original value kept in `confirm_why` rather than
      // silently overwritten. One cheap map, no deep validation.
      structures = (day.structures as Structure[]).map((s) => {
        if (s.confirm === 'CONFIRMED' || s.confirm === 'UNCONFIRMED' || s.confirm === 'UNKNOWN') return s
        return {
          ...s,
          confirm: 'UNKNOWN' as const,
          confirm_why: `unrecognised confirm "${s.confirm}" — treated as unchecked; ${s.confirm_why ?? ''}`,
        }
      })
    }

    // Band-rotation signals ride the SAME unfiltered bar indices as the
    // structure layer, so they take the same skip guard: a signal drawn one
    // bar off would claim the operator's own setup fired on a minute it did
    // not. The backend emits one slot per bar including nulls, so a length
    // mismatch is a real disagreement about the bar list and is disclosed
    // rather than papered over by padding or truncating.
    let rotation: (RotationSignal | null)[] | null = null
    let rotationWhy = ''
    const rawRot = day.rotation
    if (!Array.isArray(rawRot)) {
      rotationWhy = 'this backend publishes no index band-rotation layer'
    } else if (skipped > 0) {
      rotationWhy = `${skipped} bar${skipped === 1 ? '' : 's'} lacked a FUT leg, `
        + 'so the signals’ bar indices no longer line up with the chart'
    } else if (rawRot.length !== bars.length) {
      rotationWhy = `the backend sent ${rawRot.length} signal slot${rawRot.length === 1 ? '' : 's'} `
        + `for ${bars.length} bars, so they cannot be lined up 1:1`
    } else {
      // Verbatim, but not blind — same bargain the structure layer makes: a
      // row whose `confirm` is not one of the three known values is still
      // shown, normalised to UNKNOWN (the honest reading of "not recognised")
      // with the surprising original kept in `confirm_why`, never dropped.
      rotation = (rawRot as (RotationSignal | null)[]).map((r) => {
        if (!r) return null
        if (r.confirm === 'CONFIRMED' || r.confirm === 'UNCONFIRMED' || r.confirm === 'UNKNOWN') return r
        return {
          ...r,
          confirm: 'UNKNOWN' as const,
          confirm_why: `unrecognised confirm "${r.confirm}" — treated as unchecked; ${r.confirm_why ?? ''}`,
        }
      })
    }
    // §5c's two-candle entries and the per-bar state of the same machine.
    // Same guard as `rotation` above, for the same reason. These are NOT a
    // fallback for each other: `rotation` marks the d3 touch and `rotationRun`
    // marks the entry, so quietly substituting one would move every marker on
    // the chart with nothing on screen saying it had happened.
    const [rotationRun, rotationRunWhy] =
      alignPerBar<RotationSignal | null>(day.rotation_run, bars.length, skipped,
                                         'two-candle entry')
    const [rotationRunSell, rotationRunSellWhy] =
      alignPerBar<RotationSignal | null>(day.rotation_run_sell, bars.length,
                                         skipped, 'two-candle sell entry')
    const [runState, runStateWhy] =
      alignPerBar<RunState>(day.run_state, bars.length, skipped, 'run-state')

    return {
      day: day.day ?? '', bars,
      strike: typeof day.strike === 'number' && Number.isFinite(day.strike) ? day.strike : null,
      // Whole-block pass-through, same rule as ctx/gamma/setup.
      optPivots: (day.opt_pivots as OptPivots | undefined) ?? null,
      optExpiry: typeof day.opt_expiry === 'string' ? day.opt_expiry : null,
      structures, structuresWhy, rotation, rotationWhy,
      rotationRun, rotationRunWhy, rotationRunSell, rotationRunSellWhy,
      runState, runStateWhy,
    }
  }, [raw])

  return { data, loading, error, errorWhy, broker, lastUpdated, barCount, at, dead, tapeBars }
}
