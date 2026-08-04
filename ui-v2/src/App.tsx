import { useState, useEffect, useMemo, useRef, createContext, useContext } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { useLiveData, HEAT_COLS, validateTrade, chainAgeS, CHAIN_STALE_S } from './data'
import type { IndexKey, IndexInfo, Dataset, HeatCell, HeatTone, PressCell, Chain, MapData, MapLevelKind, Gate, FlowRow } from './data'
import { usePalette, useMode, palette, rgbOf } from './theme'
import type { Palette } from './theme'
import TradeTab from './trade/TradeTab'
import ProtoTab from './proto/ProtoTab'
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
// 'Proto' is the throwaway lightweight-charts spike (src/proto/). It is not a
// feature: it exists to decide v3's charting foundation and gets deleted with
// its directory once the verdict is recorded. See context/HANDOFF.md §6b.
type Tab = 'Heat' | 'Trade' | 'Tape' | 'Chain' | 'OI Flow' | 'Events' | 'Validate' | 'Map' | 'Proto'

// ── Mock data (fallback shown on first paint / when an index fails to fetch) ────
const MOCK_INDICES: Record<IndexKey, { price: number; change: number; pct: number; state: string; arrow: string; highlight?: boolean }> = {
  BANKNIFTY: { price: 56624, change: -405,  pct: -0.71, state: 'recovering',   arrow: '▼', highlight: true },
  NIFTY:     { price: 23860, change: -60,   pct: -0.25, state: 'heavy, capped', arrow: '▼' },
  SENSEX:    { price: 76360, change: -30,   pct: -0.04, state: 'rolled over',   arrow: '〰' },
}

const MOCK_READS: Record<IndexKey, { headline: string; timing: string; direction: string; sub: string }> = {
  NIFTY: {
    headline: 'Down-leg exhausted — relief bounce under resistance',
    timing: 'WAIT',
    direction: 'BEARISH',
    sub: 'Reclaim VWAP 23,909 to confirm a turn.',
  },
  BANKNIFTY: {
    headline: 'Biggest mover — short squeeze in progress near 56,500',
    timing: 'READY',
    direction: 'BULLISH',
    sub: 'Hold above 56,500 CE wall to sustain. Watch 56,800 resistance.',
  },
  SENSEX: {
    headline: 'Sideways drift — insufficient momentum either way',
    timing: 'WAIT',
    direction: 'NEUTRAL',
    sub: 'No edge until break above 76,500 or below 76,100.',
  },
}

const MOCK_KEY_LEVELS: Record<IndexKey, Array<{ label: string; value: number; note: string; dist: number; dir: 'up' | 'down' | 'here' }>> = {
  NIFTY: [
    { label: 'CAP',  value: 23900, note: 'CE wall 7M', dist: +40, dir: 'up' },
    { label: 'VWAP', value: 23909, note: 'reclaim = turn', dist: +49, dir: 'up' },
    { label: 'NOW',  value: 23860, note: 'last price', dist: 0, dir: 'here' },
    { label: 'LOW',  value: 23808, note: 'session low', dist: -52, dir: 'down' },
    { label: 'SUP',  value: 23750, note: 'PE wall 5.2M', dist: -110, dir: 'down' },
  ],
  BANKNIFTY: [
    { label: 'RES',  value: 56800, note: 'call wall', dist: +176, dir: 'up' },
    { label: 'VWAP', value: 56700, note: 'reclaim watch', dist: +76, dir: 'up' },
    { label: 'NOW',  value: 56624, note: 'last price', dist: 0, dir: 'here' },
    { label: 'SUP',  value: 56500, note: 'CE wall / key', dist: -124, dir: 'down' },
    { label: 'LOW',  value: 56200, note: 'session low', dist: -424, dir: 'down' },
  ],
  SENSEX: [
    { label: 'RES',  value: 76500, note: 'call wall', dist: +140, dir: 'up' },
    { label: 'VWAP', value: 76420, note: 'flat VWAP', dist: +60, dir: 'up' },
    { label: 'NOW',  value: 76360, note: 'last price', dist: 0, dir: 'here' },
    { label: 'SUP',  value: 76100, note: 'PE wall', dist: -260, dir: 'down' },
    { label: 'LOW',  value: 75900, note: 'session low', dist: -460, dir: 'down' },
  ],
}

const MOCK_ORDER_FLOW: Record<IndexKey, { main: string; mm: string; stats: Array<{ label: string; value: string }> }> = {
  NIFTY: {
    main: 'Selling dried up. Futures discount refilled, call-writers covering (supportive). But NIFTY OI is rebuilding — shorts may re-press. Move: decelerating.',
    mm: 'Dealers still cap rallies (negative-gamma).',
    stats: [
      { label: 'Realized σ', value: '9.4%' },
      { label: '30m Range', value: '94 pts · 68th %ile' },
      { label: 'ATM IV', value: '13.2%' },
    ],
  },
  BANKNIFTY: {
    main: 'Short squeeze in early stages. PE writers rapidly covering — OI shedding at lows. Call-side building slowly but not yet a wall. Move: accelerating.',
    mm: 'Dealers long gamma locally — moves self-correct near 56,500.',
    stats: [
      { label: 'Realized σ', value: '12.8%' },
      { label: '30m Range', value: '224 pts · 82nd %ile' },
      { label: 'ATM IV', value: '15.6%' },
    ],
  },
  SENSEX: {
    main: 'Balanced flow, no conviction either way. Futures trading at fair value. Options market quiet — no large directional bets. Move: sideways drift.',
    mm: 'Dealers neutral gamma — no strong hedging flow.',
    stats: [
      { label: 'Realized σ', value: '7.1%' },
      { label: '30m Range', value: '82 pts · 34th %ile' },
      { label: 'ATM IV', value: '11.4%' },
    ],
  },
}

const MOCK_CHAIN_DATA: Record<IndexKey, { pcr: string; maxPain: number; gex: string; squeeze: string; strikes: Array<{ strike: number; ceOI: number; peOI: number; type?: 'callwall' | 'putwall' | 'atm' }> }> = {
  NIFTY: {
    pcr: '0.82', maxPain: 24000, gex: 'Negative', squeeze: 'Low',
    strikes: [
      { strike: 24200, ceOI: 8200, peOI: 1100, type: 'callwall' },
      { strike: 24100, ceOI: 5400, peOI: 1800 },
      { strike: 24000, ceOI: 7100, peOI: 2200 },
      { strike: 23900, ceOI: 7000, peOI: 2900, type: 'callwall' },
      { strike: 23800, ceOI: 2100, peOI: 4200, type: 'atm' },
      { strike: 23700, ceOI: 1200, peOI: 5800 },
      { strike: 23600, ceOI: 900,  peOI: 6100, type: 'putwall' },
      { strike: 23500, ceOI: 600,  peOI: 5200 },
    ],
  },
  BANKNIFTY: {
    pcr: '1.04', maxPain: 56500, gex: 'Positive', squeeze: 'High',
    strikes: [
      { strike: 57000, ceOI: 4200, peOI: 900 },
      { strike: 56800, ceOI: 5800, peOI: 1400, type: 'callwall' },
      { strike: 56700, ceOI: 3200, peOI: 2100 },
      { strike: 56600, ceOI: 2800, peOI: 2900, type: 'atm' },
      { strike: 56500, ceOI: 1900, peOI: 4400, type: 'putwall' },
      { strike: 56200, ceOI: 800,  peOI: 5100 },
      { strike: 56000, ceOI: 600,  peOI: 4800 },
      { strike: 55800, ceOI: 400,  peOI: 3200 },
    ],
  },
  SENSEX: {
    pcr: '0.91', maxPain: 76500, gex: 'Neutral', squeeze: 'Medium',
    strikes: [
      { strike: 77000, ceOI: 3100, peOI: 600 },
      { strike: 76800, ceOI: 4200, peOI: 900, type: 'callwall' },
      { strike: 76600, ceOI: 2800, peOI: 1400 },
      { strike: 76400, ceOI: 2100, peOI: 2200, type: 'atm' },
      { strike: 76200, ceOI: 1100, peOI: 3800 },
      { strike: 76000, ceOI: 800,  peOI: 4200, type: 'putwall' },
      { strike: 75800, ceOI: 500,  peOI: 3100 },
      { strike: 75600, ceOI: 300,  peOI: 2400 },
    ],
  },
}

const MOCK_EVENTS = [
  { time: '14:33', text: 'Fake low sprung — late shorts trapped, small bounce likely', tag: 'BEAR-TRAP SPRUNG', dir: 'bull' as const },
  { time: '14:09', text: 'New low but puts aren\'t confirming — selling not fully paid for', tag: 'UNCONFIRMED BREAKDOWN', dir: 'neutral' as const },
  { time: '13:53', text: 'Call-writers being squeezed — supportive of a bounce', tag: 'SQUEEZE SIGNAL', dir: 'bull' as const },
  { time: '13:22', text: 'VWAP lost — sellers have the edge, avoid longs', tag: 'VWAP LOSS', dir: 'bear' as const },
  { time: '12:47', text: 'OI building at 23,800 PE — that\'s the floor the market is defending', tag: 'SUPPORT IDENTIFIED', dir: 'bull' as const },
  { time: '12:18', text: 'Afternoon drift lower on light volume — no conviction', tag: 'LOW CONVICTION', dir: 'neutral' as const },
  { time: '11:54', text: 'Call wall at 23,900 absorbing every rally — capped', tag: 'CAPPED', dir: 'bear' as const },
  { time: '11:30', text: 'Morning range set: 23,808–23,942. Fair value near 23,870.', tag: 'RANGE SET', dir: 'neutral' as const },
]

// ── Chart data gen ────────────────────────────────────────────────────────────
// Realistic intraday mock: a mean-reverting price walk 09:15→15:29 with a VWAP
// that tracks price and a tight ±1σ band — so the MOCK chart reads like a real one.
function makeIntraday(basePrice: number, vwapBase: number) {
  const data = []
  const sigma = basePrice * 0.0009
  const bound = basePrice * 0.0032
  let price = basePrice + basePrice * 0.0016
  let vwap = vwapBase
  const start = 9 * 60 + 15
  const end = 15 * 60 + 29
  const total = (end - start) / 3
  let i = 0
  for (let mins = start; mins <= end; mins += 3, i++) {
    const h = Math.floor(mins / 60), mm = mins % 60
    const time = `${String(h).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
    const revert = (basePrice - price) * 0.06
    const noise = (Math.random() - 0.5) * basePrice * 0.001
    price = Math.max(basePrice - bound, Math.min(basePrice + bound, price + revert + noise))
    vwap += (price - vwap) * 0.03 + (Math.random() - 0.5) * 1.5
    const s = sigma * (0.85 + Math.random() * 0.3)
    data.push({
      time,
      price: +price.toFixed(2),
      vwap: +vwap.toFixed(2),
      upper: +(price + s).toFixed(2),
      lower: +(price - s).toFixed(2),
      vol: Math.floor(Math.random() * 800000 + 200000),
      isFuture: i / total > 0.9,
    })
  }
  return data
}

const MOCK_CHART_DATA: Record<IndexKey, ReturnType<typeof makeIntraday>> = {
  NIFTY:     makeIntraday(23860, 23909),
  BANKNIFTY: makeIntraday(56624, 56700),
  SENSEX:    makeIntraday(76360, 76420),
}

// Augment the mock strike ladder with the heatmap fields the live shape now carries.
function mockChain(c: typeof MOCK_CHAIN_DATA[IndexKey]): Chain {
  const ks = c.strikes.map(s => s.strike)
  return {
    ...c,
    strikes: c.strikes.map((s) => {
      const tot = s.ceOI + s.peOI || 1
      return {
        ...s, gex: s.ceOI - s.peOI,
        ceW: +(s.ceOI / tot).toFixed(2), peW: +(s.peOI / tot).toFixed(2),
        cePk: s.ceOI, pePk: s.peOI,     // placeholder: "at peak", so 0% off
        // no quotes in the fallback: the validator returns null rather than
        // checking a trade against invented premiums
        ceLtp: 0, peLtp: 0, ceIv: 0, peIv: 0, ceSpread: 0, peSpread: 0,
      }
    }),
    mpDist: 0,
    gexSpot: 0,
    bookZone: ks.length ? [Math.min(...ks), Math.max(...ks)] : null,
    inBookZone: true,
    spot: 0,
    expiry: '',
    atmStraddle: 0,
    aligned: true,
    flipPx: null,        // fallback has no gamma flip — null, never a fabricated level
    ts: '',
    // fallback has no real snapshot time — null reads as "unknown", never as fresh.
    builtAt: null,
  }
}

// Mock Live Spike Radar — 8 cells per index in HEAT_COLS order
// (FUT VOL, FUT OI, CE VOL, CE OI, PE VOL, PE OI, GAMMA, SQZ), with a few real spikes.
const MOCK_HEAT: Record<IndexKey, HeatCell[]> = {
  // NIFTY — heavy, capped: futures shorts building + puts being written (bearish spikes).
  NIFTY: [
    { label: '42%', intensity: 0.42, dir: 'bear', spike: false },
    { label: '86%', intensity: 0.86, dir: 'bear', spike: true },
    { label: '50%', intensity: 0.50, dir: 'bear', spike: false },
    { label: '64%', intensity: 0.64, dir: 'bear', spike: false },
    { label: '38%', intensity: 0.38, dir: 'neutral', spike: false },
    { label: '85%', intensity: 0.85, dir: 'bear', spike: true },
    { label: 'AMPLIFIED-DOWN', intensity: 1, dir: 'bear', spike: true },
    { label: 'DOWN 0.04', intensity: 0.10, dir: 'bear', spike: false },
  ],
  // BANKNIFTY — the mover: futures volume + PE writing surge, gamma flipped up, squeeze on.
  BANKNIFTY: [
    { label: '90%', intensity: 0.90, dir: 'bull', spike: true },
    { label: '72%', intensity: 0.72, dir: 'bull', spike: false },
    { label: '55%', intensity: 0.55, dir: 'bear', spike: false },
    { label: '60%', intensity: 0.60, dir: 'bear', spike: false },
    { label: '68%', intensity: 0.68, dir: 'bull', spike: false },
    { label: '84%', intensity: 0.84, dir: 'bull', spike: true },
    { label: 'AMPLIFIED-UP', intensity: 1, dir: 'bull', spike: true },
    { label: 'UP 0.36', intensity: 0.90, dir: 'bull', spike: true },
  ],
  // SENSEX — quiet drift: nothing lit.
  SENSEX: [
    { label: '22%', intensity: 0.22, dir: 'neutral', spike: false },
    { label: '30%', intensity: 0.30, dir: 'neutral', spike: false },
    { label: '28%', intensity: 0.28, dir: 'neutral', spike: false },
    { label: '35%', intensity: 0.35, dir: 'neutral', spike: false },
    { label: '40%', intensity: 0.40, dir: 'bull', spike: false },
    { label: '33%', intensity: 0.33, dir: 'neutral', spike: false },
    { label: 'BALANCE', intensity: 0.20, dir: 'neutral', spike: false },
    { label: 'DOWN 0.10', intensity: 0.25, dir: 'bear', spike: false },
  ],
}

// Mock Pressure Tape — ~30 buckets with a believable session arc: morning selling,
// midday balance, afternoon buying push, with varied magnitude + occasional spikes.
function mockPressure(points: ReturnType<typeof makeIntraday>): PressCell[] {
  const N = 30
  const per = Math.max(1, Math.floor(points.length / N))
  const out: PressCell[] = []
  for (let b = 0; b < N; b++) {
    const phase = b / (N - 1) // 0 → 1 across the session
    // arc: strong selling early (−), cross to buying by the close (+)
    const arc = Math.sin((phase - 0.15) * Math.PI * 1.15) * 0.65
    const wobble = Math.sin(b * 1.7) * 0.18
    const spike = b % 7 === 3 ? -Math.sign(arc || 1) * 0.3 : 0 // occasional opposite spike
    const val = Math.max(-0.95, Math.min(0.95, arc + wobble + spike))
    const p = points[Math.min(points.length - 1, b * per)]
    const pEnd = points[Math.min(points.length - 1, (b + 1) * per - 1)]
    const dir = val > 0.03 ? 'buying' : val < -0.03 ? 'selling' : 'balanced'
    out.push({
      t: p?.time ?? '',
      tEnd: pEnd?.time ?? p?.time ?? '',
      val: +val.toFixed(2),
      price: pEnd?.price ?? p?.price ?? 0,
      note: `${p?.time ?? ''}–${pEnd?.time ?? ''} · net ${dir} ${Math.round(Math.abs(val) * 100)}%`,
    })
  }
  return out
}

// Mock Levels Map (plausible static levels; replaced by live action-zone map when data arrives).
function mockMap(now: number, vwap: number, callW: number, putW: number): MapData {
  const u1 = Math.round(now * 1.0015)
  const d1 = Math.round(now * 0.9985)
  const levels = [
    { label: 'NOW', value: now, kind: 'now' as const, note: 'last price' },
    { label: 'CALL', value: callW, kind: 'wall' as const, note: 'call wall — resistance' },
    { label: 'PUT', value: putW, kind: 'wall' as const, note: 'put wall — support' },
    { label: 'VWAP', value: vwap, kind: 'vwap' as const, note: 'fair value' },
    { label: '+1σ', value: u1, kind: 'band' as const, note: 'volatility band' },
    { label: '−1σ', value: d1, kind: 'band' as const, note: 'volatility band' },
    { label: 'PIN', value: Math.round(now / 50) * 50, kind: 'pin' as const, note: 'dealer magnet (mock)' },
    { label: 'HI', value: Math.round(now * 1.0027), kind: 'session' as const, note: 'session high' },
    { label: 'LO', value: Math.round(now * 0.9961), kind: 'session' as const, note: 'session low' },
  ].sort((a, b) => b.value - a.value)
  const vals = levels.map(l => l.value)
  const lo = Math.min(...vals), hi = Math.max(...vals)
  const pad = (hi - lo) * 0.12 || now * 0.001
  return { now, zoneLo: lo - pad, zoneHi: hi + pad, levels }
}

// ── Assembled mock dataset + live-data context ─────────────────────────────────
const MOCK: Dataset = {
  INDICES: MOCK_INDICES,
  READS: MOCK_READS,
  KEY_LEVELS: MOCK_KEY_LEVELS,
  ORDER_FLOW: MOCK_ORDER_FLOW,
  CHAIN_DATA: { NIFTY: mockChain(MOCK_CHAIN_DATA.NIFTY), BANKNIFTY: mockChain(MOCK_CHAIN_DATA.BANKNIFTY), SENSEX: mockChain(MOCK_CHAIN_DATA.SENSEX) },
  EVENTS_BY_IDX: { NIFTY: MOCK_EVENTS, BANKNIFTY: MOCK_EVENTS, SENSEX: MOCK_EVENTS },
  FOCUS_BY_IDX: { NIFTY: MOCK_EVENTS, BANKNIFTY: MOCK_EVENTS, SENSEX: MOCK_EVENTS },
  CHART_DATA: MOCK_CHART_DATA,
  HEAT: MOCK_HEAT,
  PRESSURE: { NIFTY: mockPressure(MOCK_CHART_DATA.NIFTY), BANKNIFTY: mockPressure(MOCK_CHART_DATA.BANKNIFTY), SENSEX: mockPressure(MOCK_CHART_DATA.SENSEX) },
  MAP: {
    NIFTY: mockMap(23860, 23909, 23900, 23750),
    BANKNIFTY: mockMap(56624, 56700, 56800, 56500),
    SENSEX: mockMap(76360, 76420, 76500, 76100),
  },
}

const DataCtx = createContext<Dataset>(MOCK)
function useData(): Dataset {
  return useContext(DataCtx)
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (n: number) => n.toLocaleString('en-IN')
/** `rgba()` from a palette token — the only route by which a colour in this
 *  file acquires an alpha channel. Every tint, hairline and glow below used to
 *  be a literal `rgba(255,255,255,…)` or `rgba(224,168,82,…)`, which is a
 *  dark-surface assumption baked past the palette: white at 7% is invisible on
 *  white. Alphas are unchanged, so dark still renders exactly as before. */
const wash = (token: string, alpha: number | string) => `rgba(${rgbOf(token)},${alpha})`
// Real OI is large (millions of units). Show in lakhs (L), or thousands (K) below 1L.
const formatOI = (n: number) => n >= 1e5 ? `${(n / 1e5).toFixed(1)}L` : `${(n / 1e3).toFixed(1)}K`
/* These three were module-level colour constants, which is exactly the shape a
   theme cannot reach: evaluated once at import, they would keep painting the
   dark palette forever while the rest of the page went white. Each now takes
   the active palette from its caller. The dark values are unchanged — every
   triplet below is `rgbOf()` of the same dark token the literal spelled out
   (bull #2EC27E → 46,194,126, bear #FF5F6B → 255,95,107, muted #5D6B84 →
   93,107,132), so dark renders byte-identically. */

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
  // The literals these entries used to hold were the dark palette spelled out
  // by hand — caution, accent, bull, bear, textMuted. Read from the palette
  // they now follow the mode, and on white they use TL's darkened variants
  // instead of the neon pair that vanishes there.
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

function IndexCell({ idx, data, active, onClick }: {
  idx: IndexKey
  data: IndexInfo
  active: boolean
  onClick: () => void
}) {
  const [mode] = useMode()
  const pal = palette(mode)
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
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.1em',
          backgroundColor: pal.accent,
          // White on light brass is 4.4:1 at 9px; ink on it is 6.4:1. Dark
          // keeps the white it has always had.
          color: mode === 'light' ? pal.textPrimary : '#fff',
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
          {fmt(data.price)}
        </span>
        <span className="mono" style={{ fontSize: 11, color, fontWeight: 600 }}>
          {data.arrow} {data.pct > 0 ? '+' : ''}{data.pct.toFixed(2)}%
        </span>
      </div>
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

function GlanceBar({ active, setActive, lastUpdated, error }: {
  active: IndexKey
  setActive: (k: IndexKey) => void
  lastUpdated: Date | null
  error: string | null
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
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 8 }}>
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
            fontSize: 9,
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

      {/* Index scanner */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {(Object.entries(INDICES) as [IndexKey, typeof INDICES[IndexKey]][]).map(([k, d]) => (
          <IndexCell key={k} idx={k} data={d} active={active === k} onClick={() => setActive(k)} />
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

/* Recharts renders this as a real element, so it may hold hooks. It has to:
   a tooltip that keeps its dark #1B2130 panel while the chart behind it turns
   white is the one component where getting the theme wrong is invisible until
   you hover — and its label was pal.textMuted on that dark panel, which on a
   white panel would be the same reading either way only by luck. */
const ChartTooltip = ({ active, payload, label }: any) => {
  const [mode] = useMode()
  const pal = palette(mode)
  if (!active || !payload?.length) return null
  return (
    <div style={{
      backgroundColor: pal.inset,
      border: `1px solid ${wash(pal.ink, 0.1)}`,
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 11,
      color: pal.textSecondary,
      // On white, an inset-coloured panel is nearly the card colour, so the
      // tooltip needs a shadow to read as floating rather than as a hole.
      // Light only: dark mode is meant to look exactly as it did before.
      boxShadow: mode === 'light' ? `0 4px 14px ${wash(pal.ink, 0.16)}` : undefined,
    }}>
      <div style={{ marginBottom: 4, color: pal.textMuted }}>{label}</div>
      {payload.filter((p: any) => p.dataKey === 'price' || p.dataKey === 'vwap').map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', gap: 8 }}>
          <span style={{ color: p.dataKey === 'vwap' ? pal.caution : pal.textPrimary }}>{p.dataKey === 'vwap' ? 'VWAP' : 'Price'}:</span>
          <span className="mono" style={{ color: pal.textPrimary, fontWeight: 600 }}>{fmt(Math.round(p.value))}</span>
        </div>
      ))}
    </div>
  )
}

function TapeTab({ index }: { index: IndexKey }) {
  const { KEY_LEVELS, ORDER_FLOW, CHART_DATA, PRESSURE, MAP } = useData()
  const [mode] = useMode()
  const pal = palette(mode)
  const levels = KEY_LEVELS[index]
  const flow = ORDER_FLOW[index]
  const data = CHART_DATA[index]
  const pressure = PRESSURE[index]
  const map = MAP[index]

  // Y domain = action zone (near price) so a far spike can't crush the chart.
  const zLo = map.zoneLo
  const zHi = map.zoneHi

  // Readable X-axis: only hour-boundary times that exist in the data, plus ends.
  const hourTicks = data.filter(d => d.time.endsWith(':00')).map(d => d.time)
  const xTicks = Array.from(
    new Set([data[0]?.time, ...hourTicks, data[data.length - 1]?.time].filter(Boolean)),
  ) as string[]

  // Key levels drawn ON the chart: in-zone, deduped, skip now (price line) + vwap (its own line).
  const dedupeEps = map.now * 0.0004
  const refLevels = map.levels
    .filter(l => l.kind !== 'now' && l.kind !== 'vwap' && l.value >= zLo && l.value <= zHi)
    .sort((a, b) => b.value - a.value)
    .reduce<typeof map.levels>((acc, l) => {
      if (!acc.some(k => Math.abs(k.value - l.value) <= dedupeEps)) acc.push(l)
      return acc
    }, [])
  const refColor = (l: typeof map.levels[number]) =>
    l.kind === 'wall' ? (l.label === 'CALL' ? pal.bear : pal.bull)
    : l.kind === 'pin' ? pal.accent
    : l.kind === 'floor' ? pal.bull
    : l.kind === 'cap' ? pal.bear
    : l.kind === 'strike' ? pal.strike
    : l.kind === 'trap' ? pal.caution
    : l.kind === 'band' ? wash(pal.ink, 0.14)
    : pal.textMuted
  const strongKind = (k: string) =>
    k === 'wall' || k === 'pin' || k === 'floor' || k === 'cap' || k === 'strike' || k === 'trap'

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

      {/* Center: Chart */}
      <div style={{
        backgroundColor: pal.card,
        border: `1px solid ${pal.border}`,
        borderRadius: 14,
        padding: '16px 8px 8px 4px',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 12px', marginBottom: 12 }}>
          <div className="micro-label">Price · VWAP · ±1σ · Key Levels</div>
          <div style={{ display: 'flex', gap: 14, fontSize: 10, color: pal.textMuted }}>
            <span style={{ color: pal.textPrimary }}>— Price</span>
            <span style={{ color: pal.caution }}>-- VWAP</span>
            {/* A legend swatch echoing the band's own translucency. At 0.6 on
                white that is 2.1:1 — and the band it labels is drawn at 0.09,
                so the swatch was never a literal sample anyway. Light mode
                takes it to full brass; dark keeps the value it had. */}
            <span style={{ color: mode === 'light' ? pal.accent : wash(pal.accent, 0.6) }}>▨ ±1σ</span>
          </div>
        </div>
        <div style={{ height: 380 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 6, right: 78, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={pal.accent} stopOpacity={0.10} />
                  <stop offset="100%" stopColor={pal.accent} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bandFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={pal.accent} stopOpacity={0.09} />
                  <stop offset="100%" stopColor={pal.accent} stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 6" stroke={wash(pal.ink, 0.04)} vertical={false} />
              <XAxis
                dataKey="time"
                ticks={xTicks}
                interval={0}
                minTickGap={40}
                tick={{ fill: pal.textMuted, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[zLo, zHi]}
                allowDataOverflow
                tick={{ fill: pal.textMuted, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => fmt(Math.round(v))}
                width={62}
              />
              <Tooltip content={<ChartTooltip />} />
              {/* ±1σ band: accent between per-bar upper and lower (card mask hides below lower) */}
              <Area type="monotone" dataKey="upper" stroke="none" fill="url(#bandFill)" isAnimationActive={false} />
              <Area type="monotone" dataKey="lower" stroke="none" fill={pal.card} isAnimationActive={false} />
              {/* Key levels ON the chart as horizontal reference lines */}
              {refLevels.map((l, i) => {
                const c = refColor(l)
                const strong = strongKind(l.kind)
                return (
                  <ReferenceLine
                    key={`ref-${l.kind}-${Math.round(l.value)}-${i}`}
                    y={l.value}
                    stroke={c}
                    strokeDasharray={strong ? '5 4' : '2 5'}
                    strokeOpacity={strong ? 0.85 : 0.5}
                    ifOverflow="hidden"
                    label={{
                      value: `${l.kind === 'trap' ? '⚑ ' : ''}${l.label} ${fmt(Math.round(l.value))}`,
                      position: 'right',
                      fill: c,
                      fontSize: 9,
                    }}
                  />
                )
              })}
              {/* VWAP */}
              <Line type="monotone" dataKey="vwap" stroke={pal.caution} strokeWidth={1} strokeDasharray="4 4" dot={false} activeDot={false} isAnimationActive={false} />
              {/* Price — the hero (bold line + depth fill in one series) */}
              <Area type="monotone" dataKey="price" stroke={pal.textPrimary} strokeWidth={2} fill="url(#priceFill)" dot={false} activeDot={{ r: 3, fill: pal.accent, strokeWidth: 0 }} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

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
  const { CHAIN_DATA } = useData()
  const pal = usePalette()
  const chain = CHAIN_DATA[index]
  const maxCeOI = Math.max(1, ...chain.strikes.map(s => s.ceOI))
  const maxPeOI = Math.max(1, ...chain.strikes.map(s => s.peOI))
  const maxAbsGex = Math.max(1, ...chain.strikes.map(s => Math.abs(s.gex)))

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Put/Call Ratio', value: chain.pcr, note: chain.pcr < '1' ? 'Bearish lean' : 'Bullish lean' },
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
  const { EVENTS_BY_IDX, FOCUS_BY_IDX } = useData()
  const pal = usePalette()
  // FOCUS is the default: on a live expiry day the raw log repeats itself so
  // often that the signal is buried. Preference persists, as it does in v1.
  const [focus, setFocus] = useState(() => localStorage.getItem('focus') !== '0')
  const events = focus ? FOCUS_BY_IDX[index] : EVENTS_BY_IDX[index]
  const full = EVENTS_BY_IDX[index]
  const hidden = Math.max(0, full.length - events.length)
  const [hovered, setHovered] = useState<number | null>(null)
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

function ValidateTab({ index }: { index: IndexKey }) {
  const { READS, CHAIN_DATA, CHART_DATA } = useData()
  const pal = usePalette()
  const read = READS[index]
  const chain = CHAIN_DATA[index]
  const nowHHMM = CHART_DATA[index]?.slice(-1)[0]?.time ?? '12:00'

  // Strikes come from the live ladder, so you cannot check a contract that
  // does not exist — the old free-text box happily accepted anything.
  const ladder = [...chain.strikes].sort((a, b) => a.strike - b.strike)
  const nearest = ladder.reduce((best, s) =>
    Math.abs(s.strike - chain.spot) < Math.abs(best.strike - chain.spot) ? s : best,
    ladder[0])
  const [strike, setStrike] = useState<number>(nearest?.strike ?? 0)
  const [side, setSide] = useState<'CE' | 'PE'>('CE')
  const [position, setPosition] = useState<'Long' | 'Short'>('Long')

  const check = validateTrade(chain, read, strike, side, position, nowHHMM)
  const vCol = check?.verdict === 'TAKE' ? pal.bull
    : check?.verdict === 'SMALL' ? pal.caution : pal.bear
  const gCol = (v: Gate['verdict']) => v === 'pass' ? pal.bull : v === 'warn' ? pal.caution : pal.bear
  const gMark = (v: Gate['verdict']) => v === 'pass' ? '✓' : v === 'warn' ? '!' : '✕'

  const seg = <K extends string>(
    opts: readonly K[], value: K, onPick: (k: K) => void, tone: (k: K) => string,
  ) => (
    <div style={{ display: 'flex', gap: 6 }}>
      {opts.map(o => (
        <button key={o} onClick={() => onPick(o)} style={{
          flex: 1, padding: '7px 8px', borderRadius: 6, fontSize: 12.5, fontWeight: 600,
          cursor: 'pointer', transition: 'all 150ms',
          border: `1px solid ${value === o ? tone(o) : pal.border}`,
          backgroundColor: value === o ? `${tone(o)}1A` : 'transparent',
          color: value === o ? tone(o) : pal.textMuted,
        }}>{o}</button>
      ))}
    </div>
  )

  return (
    <div style={{ padding: 24, display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-start' }}>
      {/* ── the contract ── */}
      <div style={{
        backgroundColor: pal.card, border: `1px solid ${pal.border}`,
        borderRadius: 12, padding: 20, width: 300,
      }}>
        <div className="micro-label" style={{ marginBottom: 14 }}>Contract — {index}</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 11, color: pal.textMuted }}>Strike</span>
            <select value={strike} onChange={e => setStrike(+e.target.value)} style={{
              backgroundColor: pal.inset, border: `1px solid ${pal.border}`, borderRadius: 6,
              padding: '8px 10px', color: pal.textPrimary, fontSize: 13,
              fontFamily: 'inherit', outline: 'none',
            }}>
              {ladder.map(s => (
                <option key={s.strike} value={s.strike}>
                  {s.strike}{s.strike === nearest?.strike ? '  · nearest spot' : ''}
                </option>
              ))}
            </select>
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 11, color: pal.textMuted }}>Option type</span>
            {seg(['CE', 'PE'] as const, side, setSide, k => k === 'CE' ? pal.bear : pal.bull)}
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 11, color: pal.textMuted }}>Position</span>
            {seg(['Long', 'Short'] as const, position, setPosition, () => pal.accent)}
          </label>

          {/* live premium, so the choice is never blind */}
          <div style={{
            borderTop: `1px solid ${pal.border}`, paddingTop: 12, display: 'grid',
            gridTemplateColumns: '1fr auto', rowGap: 7, fontSize: 12,
          }}>
            <span style={{ color: pal.textMuted }}>Premium</span>
            <span className="mono">{check ? `${check.premium.toFixed(2)}` : '—'}</span>
            <span style={{ color: pal.textMuted }}>Intrinsic / time</span>
            <span className="mono">{check ? `${check.intrinsic.toFixed(0)} / ${check.timeValue.toFixed(1)}` : '—'}</span>
            <span style={{ color: pal.textMuted }}>Breakeven</span>
            <span className="mono" style={{ color: pal.accent }}>{check ? check.breakeven.toFixed(0) : '—'}</span>
            <span style={{ color: pal.textMuted }}>Spot now</span>
            <span className="mono">{chain.spot.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* ── the answer ── */}
      <div style={{ flex: 1, minWidth: 340, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {!check ? (
          <div style={{
            backgroundColor: pal.card, border: `1px solid ${pal.border}`,
            borderRadius: 12, padding: 20, fontSize: 13, color: pal.textMuted,
          }}>
            No premium quoted for that contract right now — nothing to check against.
          </div>
        ) : (
          <>
            <div style={{
              backgroundColor: pal.card, border: `1px solid ${pal.border}`,
              borderRadius: 12, padding: '18px 20px',
              borderLeft: `3px solid ${vCol}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
                <span style={{
                  fontSize: 22, fontWeight: 800, letterSpacing: '0.04em', color: vCol,
                }}>{check.verdict}</span>
                <span className="mono" style={{ fontSize: 12, color: pal.textMuted }}>
                  {check.score}/100
                </span>
                <span style={{ fontSize: 13.5, color: pal.textSecondary, flex: 1, minWidth: 220 }}>
                  {check.headline}
                </span>
              </div>
              <div style={{ height: 4, backgroundColor: pal.inset, borderRadius: 2, marginTop: 14, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${check.score}%`, backgroundColor: vCol,
                  borderRadius: 2, transition: 'width 350ms ease',
                }} />
              </div>
            </div>

            {/* the one comparison that decides most option buys */}
            <div style={{
              backgroundColor: pal.card, border: `1px solid ${pal.border}`,
              borderRadius: 12, padding: '16px 20px',
            }}>
              <div className="micro-label" style={{ marginBottom: 12 }}>
                Move required vs move priced
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
                <span className="mono" style={{ fontSize: 26, fontWeight: 700, color: check.emRatio > 1 ? pal.bear : pal.textPrimary }}>
                  {check.moveNeeded.toFixed(0)}
                </span>
                <span style={{ fontSize: 12, color: pal.textMuted }}>pts needed</span>
                <span style={{ fontSize: 12, color: pal.textMuted }}>vs</span>
                <span className="mono" style={{ fontSize: 18, color: pal.accent }}>
                  {check.expectedMove.toFixed(0)}
                </span>
                <span style={{ fontSize: 12, color: pal.textMuted }}>priced for the rest of the session</span>
              </div>
              <div style={{ position: 'relative', height: 8, backgroundColor: pal.inset, borderRadius: 4, overflow: 'hidden' }}>
                <div style={{
                  position: 'absolute', top: 0, bottom: 0, left: 0,
                  width: `${Math.min(100, 100 / Math.max(check.emRatio, 0.01))}%`,
                  backgroundColor: wash(pal.accent, 0.35),
                }} />
                <div style={{
                  position: 'absolute', top: 0, bottom: 0, left: 0,
                  width: `${Math.min(100, (check.emRatio / Math.max(check.emRatio, 1)) * 100)}%`,
                  backgroundColor: check.emRatio > 1 ? pal.bear : pal.bull, opacity: 0.75,
                }} />
              </div>
              <div style={{ fontSize: 11.5, color: pal.textMuted, marginTop: 9 }}>
                Delta {Number.isFinite(check.delta) ? check.delta.toFixed(2) : 'n/a'} · bid-ask {(check.spreadPct * 100).toFixed(1)}% of premium
                {check.wall && ` · ${(check.wall.oi / 1e6).toFixed(1)}M at ${check.wall.strike} in the way`}
              </div>
            </div>

            <div style={{
              backgroundColor: pal.card, border: `1px solid ${pal.border}`,
              borderRadius: 12, padding: '16px 20px',
            }}>
              <div className="micro-label" style={{ marginBottom: 12 }}>What it clears, what it does not</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
                {check.gates.map((g, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '16px 118px 1fr', gap: 10, alignItems: 'baseline' }}>
                    <span style={{ color: gCol(g.verdict), fontSize: 12, fontWeight: 700 }}>{gMark(g.verdict)}</span>
                    <span style={{ fontSize: 11.5, color: pal.textMuted, letterSpacing: '0.02em' }}>{g.label}</span>
                    <span style={{ fontSize: 12.5, color: g.verdict === 'pass' ? pal.textSecondary : pal.textPrimary, lineHeight: 1.5 }}>
                      {g.detail}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function MapTab({ index }: { index: IndexKey }) {
  const { MAP } = useData()
  const pal = usePalette()
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
  const [mode] = useMode()
  const pal = palette(mode)
  const keys: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']
  // This is the one view read across all three indices at once, so a dead one
  // must not sit here looking identical to a live one. Its fallback row would
  // otherwise show invented signals — "AMPLIFIED-UP", "UP 0.36" — and get
  // counted in the spike badge as though it were happening.
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
                }}>{fmt(INDICES[k].price)}</span>
              </button>
              {isDead(k) ? (
                <div style={{
                  flex: 1, display: 'flex', alignItems: 'center', gap: 8,
                  border: `1px dashed ${pal.border}`, borderRadius: 8, padding: '8px 14px',
                  fontSize: 11.5, color: pal.caution,
                }}>
                  no {k} tape — nothing to read here
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
                    {/* The tile's own hue, on a tile washed in that same hue.
                        On a dark tile the bright token reads; on a white
                        surface the wash goes saturated and the glyph
                        disappears into it (measured 1.5–2.8:1). Direction is
                        already carried by the tile colour and the arrow's
                        shape, so light mode draws the glyph in ink. */}
                    <span style={{ fontSize: 9, color: mode === 'light' ? pal.textPrimary : `rgb(${hue})`, opacity: 0.9 }}>{arrow}</span>
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
  const [mins, setMins] = useState(15)
  const [rows, setRows] = useState<FlowRow[]>([])
  const [avail, setAvail] = useState<number[]>([])
  const [sel, setSel] = useState<number[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

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
    textAlign: 'right', padding: '7px 10px', fontSize: 9.5, fontWeight: 600,
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
      ) : !rows.length ? (
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
                <th style={th}>LTP</th>
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
                      <span style={{
                        fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                        padding: '2px 8px', borderRadius: 3,
                        color: bull ? pal.bull : pal.bear,
                        background: bull ? wash(pal.bull, 0.12) : wash(pal.bear, 0.12),
                      }}>{r.sentiment}</span>
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
    <div style={{ backgroundColor: pal.bg, borderBottom: `1px solid ${pal.border}` }}>
      <div style={{
        display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: 26,
        alignItems: 'center', padding: '14px 24px',
      }}>
        <div>
          <div className="mono" style={{
            fontSize: 32, lineHeight: 1, fontWeight: 600, letterSpacing: '-0.02em',
            // a price you cannot trust must not look like one you can
            color: stale ? pal.textMuted : pal.textPrimary,
            textDecoration: stale ? 'line-through' : 'none',
          }}>
            {info.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mono" style={{ fontSize: 12, color: stale ? pal.textMuted : dirCol, marginTop: 5 }}>
            {stale ? 'placeholder' : `${info.change > 0 ? '+' : ''}${info.change.toFixed(2)} · ${info.pct > 0 ? '+' : ''}${info.pct.toFixed(2)}%`}
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
          ) : (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6 }}>
              <DirectionChip value={read.direction} />
              <TimingChip value={read.timing} />
            </div>
          )}
          <div style={{ fontSize: 14.5, lineHeight: 1.45, maxWidth: '62ch' }}>
            {read.headline}
          </div>
          {read.sub && (
            <div style={{ fontSize: 12.5, color: pal.textSecondary, marginTop: 3 }}>{read.sub}</div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 5, alignItems: 'flex-end' }}>
          {chip(`MAX PAIN ${chain.maxPain} · ${mpDist >= 0 ? '+' : ''}${mpDist}`, 'structure')}
          {/* A GEX reading without "where is price relative to the books" is
              the single most misleading number on the screen. */}
          {chain.inBookZone
            ? chip(`GEX ${chain.gex} · in book zone`)
            : chip(`GEX ${chain.gex} · OUTSIDE BOOKS — SNAP-BACK RISK`, 'structure')}
          {chip(`PCR ${chain.pcr} · SQUEEZE ${chain.squeeze}`)}
        </div>
      </div>

      <div style={{
        display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap',
        padding: '8px 24px', backgroundColor: pal.card,
        borderTop: `1px solid ${pal.border}`, fontSize: 12.5,
      }}>
        <span className="micro-label" style={{ whiteSpace: 'nowrap' }}>Changes if</span>
        {above
          ? <span>breaks <span className="mono" style={{ color: pal.accent }}>{above.value}</span>
              <span style={{ color: pal.textMuted }}> ({above.label}{above.note ? ` · ${above.note}` : ''})</span></span>
          : <span style={{ color: pal.textMuted }}>no level mapped above</span>}
        <span style={{ color: pal.textMuted }}>·</span>
        {below
          ? <span>or loses <span className="mono" style={{ color: pal.accent }}>{below.value}</span>
              <span style={{ color: pal.textMuted }}> ({below.label}{below.note ? ` · ${below.note}` : ''})</span></span>
          : <span style={{ color: pal.textMuted }}>no level mapped below</span>}
      </div>
    </div>
  )
}

export default function App() {
  // The shell paints from the same mode the chart does — see theme.ts's
  // ModeProvider, mounted in main.tsx above this component.
  const pal = usePalette()
  const [activeIndex, setActiveIndex] = useState<IndexKey>('NIFTY')
  const [activeTab, setActiveTab] = useState<Tab>('Heat')
  // FOCUS: while on and the Trade tab is active, hide the glance bar + ANSWER
  // band so the chart reclaims that ~417px of chrome (Kite gives the chart
  // nearly the whole viewport; this dashboard didn't). Persisted the same way
  // useMode() persists its own toggle — defaults OFF so nothing changes for
  // anyone who hasn't opted in.
  const [focus, setFocusState] = useState<boolean>(() => localStorage.getItem('tape.focus') === '1')
  const setFocus = (v: boolean) => { localStorage.setItem('tape.focus', v ? '1' : '0'); setFocusState(v) }
  const focusHidesChrome = focus && activeTab === 'Trade'
  const tabs: Tab[] = ['Heat', 'Trade', 'Tape', 'Chain', 'OI Flow', 'Events', 'Validate', 'Map', 'Proto']
  const { data: liveData, loading, error, lastUpdated, barCount, at, dead, tapeBars } = useLiveData(MOCK)
  const idxDead = dead.includes(activeIndex)

  // ── Replay. scrub === null means live. Re-maps stored payloads; no refetch.
  const [scrub, setScrub] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(8)
  const nBars = barCount(activeIndex)
  const data = useMemo(() => at(scrub), [scrub, liveData])
  const tape = useMemo(() => tapeBars(activeIndex), [tapeBars, activeIndex, liveData])
  // MAP levels are bar-derived and causal under replay. MAX PAIN and GEX FLIP
  // come from the chain, which is a live snapshot with no per-strike history
  // (the same reason Chain.aligned goes false while scrubbing) — so they are
  // drawn only when live, never during replay (honesty rule 6).
  const tradeLevels = useMemo(() => {
    const lv = [...(data.MAP[activeIndex]?.levels ?? [])]
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
        <GlanceBar active={activeIndex} setActive={setActiveIndex} lastUpdated={lastUpdated} error={error} />
      )}

      {/* A trading screen must never present placeholder numbers as real. The
          fallback dataset exists so the first paint isn't empty — the moment
          every index fails, say so at full width instead of showing a small
          "reconnecting" chip beside believable-looking prices. */}
      {error && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.bear, 0.12),
          borderBottom: `1px solid ${pal.bear}`, color: pal.bear,
          fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
          display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap',
        }}>
          <span style={{ marginRight: 12 }}>
            NOT LIVE — the backend is unreachable, so every figure below is placeholder data.
            An expired Dhan token is the usual cause:
          </span>
          <TokenCapture tone="loud" />
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
          figures below are placeholder. {dead.length < 3 && 'The other indices are live.'}
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

      {!focusHidesChrome && (
        <AnswerBand index={activeIndex} stale={!!error || idxDead} />
      )}

      {/* Tab bar */}
      <div style={{
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
      {nBars > 1 && (
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
        {activeTab === 'Heat'     && <HeatTab active={activeIndex} setActive={setActiveIndex} dead={dead} />}
        {activeTab === 'Trade'    && <TradeTab key={activeIndex} index={activeIndex} day={tape.day} bars={tape.bars}
                                              chain={activeChain} strike={tape.strike}
                                              optPivots={tape.optPivots} optExpiry={tape.optExpiry}
                                              levels={tradeLevels} events={data.EVENTS_BY_IDX[activeIndex]} cursor={scrub}
                                              stale={idxDead || !!error} loading={loading} chainStale={chainStale}
                                              chainTs={activeChain.ts}
                                              focus={focus} onFocusToggle={() => setFocus(!focus)}
                                              onIndexChange={setActiveIndex}
                                              structures={tape.structures}
                                              structuresWhy={tape.structuresWhy}
                                              rotation={tape.rotation}
                                              rotationWhy={tape.rotationWhy} />}
        {activeTab === 'Tape'     && <TapeTab index={activeIndex} />}
        {activeTab === 'Chain'    && <ChainTab index={activeIndex} />}
        {activeTab === 'OI Flow'  && <OiFlowTab index={activeIndex} />}
        {activeTab === 'Events'   && <EventsTab index={activeIndex} />}
        {activeTab === 'Validate' && <ValidateTab index={activeIndex} />}
        {activeTab === 'Map'      && <MapTab index={activeIndex} />}
        {/* No key={activeIndex}: unlike TradeTab, the spike is deliberately
            exposed to an index switch without a remount, because surviving one
            is a real v3 requirement. */}
        {activeTab === 'Proto'    && <ProtoTab day={tape.day} bars={tape.bars}
                                              rotation={tape.rotation} rotationWhy={tape.rotationWhy}
                                              levels={tradeLevels} />}
      </div>
    </div>
    </DataCtx.Provider>
  )
}
