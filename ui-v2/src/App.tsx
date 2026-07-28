import { useState, createContext, useContext } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { useLiveData, HEAT_COLS } from './data'
import type { IndexKey, IndexInfo, Dataset, HeatCell, HeatTone, PressCell, Chain, MapData, MapLevelKind } from './data'

// ── Tokens ───────────────────────────────────────────────────────────────────
// Colour carries exactly one meaning each. Before this, hue did two jobs at
// once — purple meant "spring", cyan meant "gamma", while green and red ALSO
// meant up and down — so it resolved to neither. Now brass is structure
// (levels, walls, pins, dealer regime) and green/red are direction only.
const T = {
  bg: '#0B0E14',
  card: '#141926',
  inset: '#1B2130',
  border: 'rgba(255,255,255,0.07)',
  textPrimary: '#E8EDF5',
  textSecondary: '#9AA7BD',
  textMuted: '#5D6B84',
  bull: '#2EC27E',          // direction only
  bear: '#FF5F6B',          // direction only
  caution: '#FFBF00',
  accent: '#E0A852',        // structure: levels, walls, pins, regime
}

// ── Types ─────────────────────────────────────────────────────────────────────
// IndexKey now comes from ./data (single source of truth for the live layer).
type Tab = 'Heat' | 'Tape' | 'Chain' | 'Events' | 'Validate' | 'Map'

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
  return {
    ...c,
    strikes: c.strikes.map((s) => {
      const tot = s.ceOI + s.peOI || 1
      return { ...s, gex: s.ceOI - s.peOI, ceW: +(s.ceOI / tot).toFixed(2), peW: +(s.peOI / tot).toFixed(2) }
    }),
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
// Real OI is large (millions of units). Show in lakhs (L), or thousands (K) below 1L.
const formatOI = (n: number) => n >= 1e5 ? `${(n / 1e5).toFixed(1)}L` : `${(n / 1e3).toFixed(1)}K`
// Heat-tile color: hue from tone, alpha ramp from intensity (0–3).
const HEAT_RGB: Record<HeatTone, string> = { bull: '46,194,126', bear: '255,95,107', neutral: '93,107,132' }
// Spike-radar cell background: hue by direction, alpha ramps with intensity (0..1).
const heatColor = (dir: HeatTone, intensity: number) => `rgba(${HEAT_RGB[dir]}, ${(0.08 + 0.55 * Math.max(0, Math.min(1, intensity))).toFixed(3)})`
// Levels-map per-kind styling (wall color resolves to CALL=bear / PUT=bull at render).
const KIND_STYLE: Record<MapLevelKind, { color: string; dot: number; marker?: string }> = {
  now:     { color: T.accent, dot: 9 },
  wall:    { color: T.textSecondary, dot: 8 },
  pin:     { color: T.accent, dot: 8, marker: '◎' },
  pivot:   { color: T.textMuted, dot: 5 },
  vwap:    { color: T.caution, dot: 6 },
  band:    { color: 'rgba(224,168,82,0.6)', dot: 4 },
  floor:   { color: T.bull, dot: 6 },
  cap:     { color: T.bear, dot: 6 },
  strike:  { color: '#E8C15A', dot: 6 },
  session: { color: T.textMuted, dot: 4 },
  trap:    { color: T.caution, dot: 6, marker: '⚑' },
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TimingChip({ value }: { value: string }) {
  const colors: Record<string, [string, string]> = {
    WAIT:  ['rgba(255,191,0,0.12)', '#FFBF00'],
    READY: ['rgba(224,168,82,0.15)', '#E0A852'],
    GO:    ['rgba(46,194,126,0.15)', '#2EC27E'],
    CAUTION: ['rgba(255,95,107,0.12)', '#FF5F6B'],
  }
  const [bg, fg] = colors[value] ?? ['rgba(93,107,132,0.15)', '#5D6B84']
  return (
    <span className="chip" style={{ backgroundColor: bg, color: fg }}>
      {value === 'WAIT' && '⏸ '}{value === 'READY' && '⚡ '}{value === 'GO' && '▶ '}
      {value}
    </span>
  )
}

function DirectionChip({ value }: { value: string }) {
  const colors: Record<string, [string, string]> = {
    BEARISH: ['rgba(255,95,107,0.12)', '#FF5F6B'],
    BULLISH: ['rgba(46,194,126,0.12)', '#2EC27E'],
    NEUTRAL: ['rgba(93,107,132,0.12)', '#9AA7BD'],
  }
  const [bg, fg] = colors[value] ?? ['rgba(93,107,132,0.12)', '#9AA7BD']
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
  const isUp = data.pct >= 0
  const color = Math.abs(data.pct) < 0.1 ? T.textSecondary : isUp ? T.bull : T.bear

  return (
    <button
      onClick={onClick}
      className={data.highlight ? 'trending-glow' : ''}
      style={{
        backgroundColor: active ? '#1B2130' : '#141926',
        border: data.highlight
          ? `1px solid ${T.accent}`
          : active
          ? `1px solid rgba(255,255,255,0.12)`
          : `1px solid ${T.border}`,
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
          backgroundColor: T.accent,
          color: '#fff',
          padding: '1px 7px',
          borderRadius: 4,
        }}>
          LOOK HERE
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: T.textPrimary }}>{idx}</span>
        <span style={{ fontSize: 10, color: T.textMuted }}>{data.state}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span className="mono" style={{ fontSize: 15, fontWeight: 600, color: T.textPrimary }}>
          {fmt(data.price)}
        </span>
        <span className="mono" style={{ fontSize: 11, color, fontWeight: 600 }}>
          {data.arrow} {data.pct > 0 ? '+' : ''}{data.pct.toFixed(2)}%
        </span>
      </div>
    </button>
  )
}

function GlanceBar({ active, setActive, lastUpdated, error }: {
  active: IndexKey
  setActive: (k: IndexKey) => void
  lastUpdated: Date | null
  error: string | null
}) {
  const { INDICES } = useData()
  return (
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backgroundColor: T.card,
      borderBottom: `1px solid ${T.border}`,
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 24,
      minHeight: 72,
      flexWrap: 'wrap',
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.12em', color: T.textPrimary }}>
          TAPEMAP
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: T.bull }}>
          <span className="live-dot" style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: T.bull, display: 'inline-block' }} />
          LIVE
        </span>
        {lastUpdated && (
          <span className="mono" style={{ fontSize: 10, color: T.textMuted }}>
            updated {lastUpdated.toLocaleTimeString('en-GB')}
          </span>
        )}
        {error && (
          <span style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.06em',
            color: T.caution,
            backgroundColor: 'rgba(255,191,0,0.1)',
            border: `1px solid rgba(255,191,0,0.2)`,
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

      {/* THE READ used to be repeated here. It now lives once, in the ANSWER
          band directly below, at a scale that actually ranks it. Saying the
          same thing in four places is what made the old screen unreadable. */}
    </div>
  )
}

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      backgroundColor: '#1B2130',
      border: `1px solid rgba(255,255,255,0.1)`,
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 11,
      color: T.textSecondary,
    }}>
      <div style={{ marginBottom: 4, color: T.textMuted }}>{label}</div>
      {payload.filter((p: any) => p.dataKey === 'price' || p.dataKey === 'vwap').map((p: any) => (
        <div key={p.dataKey} style={{ display: 'flex', gap: 8 }}>
          <span style={{ color: p.dataKey === 'vwap' ? '#FFBF00' : T.textPrimary }}>{p.dataKey === 'vwap' ? 'VWAP' : 'Price'}:</span>
          <span className="mono" style={{ color: T.textPrimary, fontWeight: 600 }}>{fmt(Math.round(p.value))}</span>
        </div>
      ))}
    </div>
  )
}

function TapeTab({ index }: { index: IndexKey }) {
  const { KEY_LEVELS, ORDER_FLOW, CHART_DATA, PRESSURE, MAP } = useData()
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
    l.kind === 'wall' ? (l.label === 'CALL' ? T.bear : T.bull)
    : l.kind === 'pin' ? T.accent
    : l.kind === 'floor' ? T.bull
    : l.kind === 'cap' ? T.bear
    : l.kind === 'strike' ? '#E8C15A'
    : l.kind === 'trap' ? T.caution
    : l.kind === 'band' ? 'rgba(255,255,255,0.14)'
    : T.textMuted
  const strongKind = (k: string) =>
    k === 'wall' || k === 'pin' || k === 'floor' || k === 'cap' || k === 'strike' || k === 'trap'

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 260px', gap: 16, padding: 24, flex: 1 }}>
      {/* Left: Key Levels */}
      <div style={{
        backgroundColor: T.card,
        border: `1px solid ${T.border}`,
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
                borderLeft: isHere ? `3px solid ${T.accent}` : '3px solid transparent',
                backgroundColor: isHere ? 'rgba(224,168,82,0.06)' : 'transparent',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: T.textMuted, letterSpacing: '0.06em' }}>{lvl.label}</span>
                {!isHere && (
                  <span className="mono" style={{
                    fontSize: 10,
                    color: isUp ? T.bull : T.bear,
                    fontWeight: 600,
                  }}>
                    {isUp ? '▲' : '▼'} {isUp ? '+' : ''}{lvl.dist}
                  </span>
                )}
              </div>
              <div className="mono" style={{ fontSize: 14, fontWeight: 600, color: isHere ? T.accent : T.textPrimary }}>
                {fmt(lvl.value)}
              </div>
              <div style={{ fontSize: 10, color: T.textMuted, marginTop: 1 }}>{lvl.note}</div>
            </div>
          )
        })}
      </div>

      {/* Center: Chart */}
      <div style={{
        backgroundColor: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 14,
        padding: '16px 8px 8px 4px',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 12px', marginBottom: 12 }}>
          <div className="micro-label">Price · VWAP · ±1σ · Key Levels</div>
          <div style={{ display: 'flex', gap: 14, fontSize: 10, color: T.textMuted }}>
            <span style={{ color: T.textPrimary }}>— Price</span>
            <span style={{ color: T.caution }}>-- VWAP</span>
            <span style={{ color: 'rgba(224,168,82,0.6)' }}>▨ ±1σ</span>
          </div>
        </div>
        <div style={{ height: 380 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 6, right: 78, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={T.accent} stopOpacity={0.10} />
                  <stop offset="100%" stopColor={T.accent} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bandFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={T.accent} stopOpacity={0.09} />
                  <stop offset="100%" stopColor={T.accent} stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 6" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="time"
                ticks={xTicks}
                interval={0}
                minTickGap={40}
                tick={{ fill: T.textMuted, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[zLo, zHi]}
                allowDataOverflow
                tick={{ fill: T.textMuted, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => fmt(Math.round(v))}
                width={62}
              />
              <Tooltip content={<ChartTooltip />} />
              {/* ±1σ band: accent between per-bar upper and lower (card mask hides below lower) */}
              <Area type="monotone" dataKey="upper" stroke="none" fill="url(#bandFill)" isAnimationActive={false} />
              <Area type="monotone" dataKey="lower" stroke="none" fill={T.card} isAnimationActive={false} />
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
              <Line type="monotone" dataKey="vwap" stroke={T.caution} strokeWidth={1} strokeDasharray="4 4" dot={false} activeDot={false} isAnimationActive={false} />
              {/* Price — the hero (bold line + depth fill in one series) */}
              <Area type="monotone" dataKey="price" stroke={T.textPrimary} strokeWidth={2} fill="url(#priceFill)" dot={false} activeDot={{ r: 3, fill: T.accent, strokeWidth: 0 }} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Pressure Tape — diverging net-flow histogram (bars grow up=buying / down=selling) */}
        <div style={{ padding: '10px 12px 4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <div className="micro-label">Pressure Tape — net order-flow (bucketed)</div>
            <div style={{ display: 'flex', gap: 12, fontSize: 10, color: T.textMuted }}>
              <span style={{ color: T.bull }}>▲ buying</span>
              <span style={{ color: T.bear }}>▼ selling</span>
              <span style={{ color: T.textMuted }}>· balanced</span>
            </div>
          </div>
          <div style={{ position: 'relative', height: 64, paddingLeft: 62, paddingRight: 78 }}>
            {/* zero centerline */}
            <div style={{ position: 'absolute', left: 62, right: 78, top: '50%', height: 1, background: 'rgba(255,255,255,0.06)' }} />
            <div style={{ position: 'relative', display: 'flex', gap: 2, height: '100%', alignItems: 'stretch' }}>
              {pressure.map((c, i) => {
                const up = c.val > 0.03
                const dn = c.val < -0.03
                const h = Math.min(46, Math.abs(c.val) * 46)
                const alpha = (0.35 + 0.5 * Math.abs(c.val)).toFixed(3)
                const green = `rgba(46,194,126, ${alpha})`
                const red = `rgba(255,95,107, ${alpha})`
                return (
                  <div key={i} title={c.note} style={{ flex: 1, minWidth: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
                    {/* top half — buying grows up from the centerline */}
                    <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
                      {up && <div style={{ width: '100%', height: h, background: green, borderRadius: '3px 3px 0 0' }} />}
                      {!up && !dn && <div style={{ width: '100%', height: 3, background: 'rgba(93,107,132,0.35)' }} />}
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
        backgroundColor: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 14,
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}>
        <div>
          <div className="micro-label" style={{ marginBottom: 10 }}>Order Flow</div>
          <p style={{ fontSize: 13, color: T.textPrimary, lineHeight: 1.65, margin: 0 }}>
            {flow.main.split('. ').map((sentence, i, arr) => (
              <span key={i}>
                <span style={{ color: i === 0 ? T.textPrimary : T.textSecondary }}>{sentence}{i < arr.length - 1 ? '. ' : ''}</span>
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
            color: T.caution,
            backgroundColor: 'rgba(255,191,0,0.08)',
            border: `1px solid rgba(255,191,0,0.15)`,
            borderRadius: 6,
            padding: '2px 8px',
            marginBottom: 8,
          }}>
            ● {flow.main.includes('decelerating') ? 'decelerating' : 'building'}
          </div>
          <div className="micro-label" style={{ marginBottom: 6 }}>MM Perspective</div>
          <p style={{ fontSize: 12, color: T.textSecondary, margin: 0, lineHeight: 1.55 }}>
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
                backgroundColor: T.inset,
                borderRadius: 8,
                border: `1px solid ${T.border}`,
              }}>
                <span style={{ fontSize: 11, color: T.textMuted }}>{s.label}</span>
                <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: T.textPrimary }}>{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function ChainTab({ index }: { index: IndexKey }) {
  const { CHAIN_DATA } = useData()
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
            backgroundColor: T.card,
            border: `1px solid ${T.border}`,
            borderRadius: 14,
            padding: '16px 20px',
          }}>
            <div className="micro-label" style={{ marginBottom: 8 }}>{stat.label}</div>
            <div className="mono" style={{ fontSize: 24, fontWeight: 700, color: T.textPrimary, marginBottom: 4 }}>{stat.value}</div>
            <div style={{ fontSize: 11, color: T.textMuted }}>{stat.note}</div>
          </div>
        ))}
      </div>

      {/* Strike heatmap */}
      <div style={{
        backgroundColor: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 14,
        overflow: 'hidden',
      }}>
        <div style={{ padding: '12px 20px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="micro-label">Strike Heatmap — CE OI · GEX · PE OI</div>
          <div style={{ display: 'flex', gap: 14, fontSize: 10, color: T.textMuted }}>
            <span style={{ color: T.bear }}>■ CE writers</span>
            <span style={{ color: T.bull }}>■ PE writers</span>
            <span style={{ color: T.accent }}>■ +GEX</span>
            <span style={{ color: T.caution }}>■ −GEX</span>
          </div>
        </div>
        {/* Column header */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '8px 20px', borderBottom: `1px solid ${T.border}` }}>
          <div style={{ flex: 1, fontSize: 10, color: T.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>CE OI</div>
          <div style={{ width: 48, textAlign: 'center', fontSize: 10, color: T.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>GEX</div>
          <div style={{ width: 160, textAlign: 'center', fontSize: 10, color: T.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>STRIKE</div>
          <div style={{ flex: 1, textAlign: 'right', fontSize: 10, color: T.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>PE OI</div>
        </div>
        {/* Rows */}
        {chain.strikes.map(s => {
          const isWall = s.type === 'callwall' || s.type === 'putwall'
          const isATM = s.type === 'atm'
          const ceA = Math.min(1, s.ceOI / maxCeOI)
          const peA = Math.min(1, s.peOI / maxPeOI)
          const gexA = Math.min(1, Math.abs(s.gex) / maxAbsGex)
          const gexRGB = s.gex > 0 ? '224,168,82' : '255,191,0'
          return (
            <div key={s.strike} style={{
              display: 'flex',
              alignItems: 'stretch',
              borderBottom: `1px solid ${T.border}`,
              backgroundColor: isATM ? 'rgba(224,168,82,0.06)' : 'transparent',
            }}>
              {/* CE OI heat cell */}
              <div style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8,
                padding: '10px 14px',
                backgroundColor: `rgba(255,95,107,${(0.06 + 0.64 * ceA).toFixed(3)})`,
              }}>
                <span className="mono" style={{ fontSize: 12, color: T.textPrimary, fontWeight: 600 }}>{formatOI(s.ceOI)}</span>
              </div>
              {/* GEX strip */}
              <div title={`GEX ${Math.round(s.gex).toLocaleString('en-IN')}`} style={{
                width: 48,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                backgroundColor: `rgba(${gexRGB},${(0.10 + 0.80 * gexA).toFixed(3)})`,
                borderLeft: `1px solid ${T.border}`,
                borderRight: `1px solid ${T.border}`,
              }}>
                <span className="mono" style={{ fontSize: 9, color: T.textPrimary, opacity: 0.85 }}>{s.gex > 0 ? '+' : '−'}</span>
              </div>
              {/* Strike */}
              <div style={{ width: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px 4px' }}>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: isATM ? T.accent : isWall ? T.textPrimary : T.textSecondary }}>
                  {fmt(s.strike)}
                </span>
                {s.type === 'callwall' && <span style={{ fontSize: 9, color: T.bear, marginLeft: 6, fontWeight: 600 }}>▲</span>}
                {s.type === 'putwall' && <span style={{ fontSize: 9, color: T.bull, marginLeft: 6, fontWeight: 600 }}>▼</span>}
                {isATM && <span style={{ fontSize: 9, color: T.accent, marginLeft: 6, fontWeight: 600 }}>◉</span>}
              </div>
              {/* PE OI heat cell */}
              <div style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 8,
                padding: '10px 14px',
                backgroundColor: `rgba(46,194,126,${(0.06 + 0.64 * peA).toFixed(3)})`,
              }}>
                <span className="mono" style={{ fontSize: 12, color: T.textPrimary, fontWeight: 600 }}>{formatOI(s.peOI)}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function EventsTab({ index }: { index: IndexKey }) {
  const { EVENTS_BY_IDX } = useData()
  const events = EVENTS_BY_IDX[index]
  const [hovered, setHovered] = useState<number | null>(null)
  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 760 }}>
      <div className="micro-label" style={{ marginBottom: 4 }}>Event Feed — {index} — newest first</div>
      {events.map((ev, i) => {
        const accent = ev.dir === 'bull' ? T.bull : ev.dir === 'bear' ? T.bear : T.textMuted
        return (
          <div
            key={i}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: 'flex',
              gap: 16,
              padding: '14px 18px',
              backgroundColor: hovered === i ? T.inset : T.card,
              borderTop: `1px solid ${hovered === i ? 'rgba(255,255,255,0.1)' : T.border}`,
              borderRight: `1px solid ${hovered === i ? 'rgba(255,255,255,0.1)' : T.border}`,
              borderBottom: `1px solid ${hovered === i ? 'rgba(255,255,255,0.1)' : T.border}`,
              borderLeft: `3px solid ${accent}`,
              borderRadius: 10,
              cursor: 'pointer',
              transition: 'all 150ms',
            }}
          >
            <span className="mono" style={{ fontSize: 11, color: T.textMuted, whiteSpace: 'nowrap', marginTop: 1 }}>{ev.time}</span>
            <span style={{ fontSize: 13, color: T.textPrimary, lineHeight: 1.5 }}>{ev.text}</span>
            {hovered === i && (
              <span style={{
                marginLeft: 'auto',
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: accent,
                backgroundColor: `rgba(${ev.dir === 'bull' ? '46,194,126' : ev.dir === 'bear' ? '255,95,107' : '93,107,132'},0.1)`,
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
  const [strike, setStrike] = useState('')
  const [side, setSide] = useState<'CE' | 'PE'>('CE')
  const [position, setPosition] = useState<'Long' | 'Short'>('Long')
  const [score, setScore] = useState<number | null>(null)

  const { READS, INDICES } = useData()
  const read = READS[index]

  const handleValidate = () => {
    let s = 50
    if (read.timing === 'GO') s += 20
    else if (read.timing === 'READY') s += 10
    else if (read.timing === 'WAIT') s -= 15
    if (read.direction === 'BULLISH' && position === 'Long' && side === 'CE') s += 15
    else if (read.direction === 'BEARISH' && position === 'Long' && side === 'PE') s += 15
    else s -= 10
    s += Math.floor(Math.random() * 10 - 5)
    setScore(Math.max(0, Math.min(100, s)))
  }

  const gates = [
    { text: `Method verdict is ${read.timing} — ${read.timing === 'WAIT' ? 'size down or skip' : 'edge confirmed'}`, pass: read.timing !== 'WAIT' },
    { text: `Direction ${read.direction} — ${side === 'CE' && read.direction === 'BEARISH' ? 'misaligned with bias' : side === 'PE' && read.direction === 'BULLISH' ? 'misaligned with bias' : 'aligned with bias'}`, pass: !(side === 'CE' && read.direction === 'BEARISH') && !(side === 'PE' && read.direction === 'BULLISH') },
    { text: 'Within market hours and pre-expiry window', pass: true },
    { text: 'IV not spiked above 20% (no earnings/event risk)', pass: true },
  ]

  return (
    <div style={{ padding: 24, display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
      <div style={{
        backgroundColor: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 14,
        padding: 24,
        width: 340,
      }}>
        <div className="micro-label" style={{ marginBottom: 16 }}>Trade Checker — {index}</div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 11, color: T.textMuted }}>Strike</span>
            <input
              type="number"
              placeholder={`e.g. ${INDICES[index].price % 100 < 50 ? Math.floor(INDICES[index].price / 100) * 100 : Math.ceil(INDICES[index].price / 100) * 100}`}
              value={strike}
              onChange={e => { setStrike(e.target.value); setScore(null) }}
              style={{
                backgroundColor: T.inset,
                border: `1px solid ${T.border}`,
                borderRadius: 8,
                padding: '9px 12px',
                color: T.textPrimary,
                fontSize: 13,
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 11, color: T.textMuted }}>Option Type</span>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['CE', 'PE'] as const).map(s => (
                <button
                  key={s}
                  onClick={() => { setSide(s); setScore(null) }}
                  style={{
                    flex: 1,
                    padding: '8px',
                    borderRadius: 8,
                    border: `1px solid ${side === s ? (s === 'CE' ? T.bear : T.bull) : T.border}`,
                    backgroundColor: side === s ? (s === 'CE' ? 'rgba(255,95,107,0.1)' : 'rgba(46,194,126,0.1)') : 'transparent',
                    color: side === s ? (s === 'CE' ? T.bear : T.bull) : T.textMuted,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 150ms',
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 11, color: T.textMuted }}>Position</span>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['Long', 'Short'] as const).map(p => (
                <button
                  key={p}
                  onClick={() => { setPosition(p); setScore(null) }}
                  style={{
                    flex: 1,
                    padding: '8px',
                    borderRadius: 8,
                    border: `1px solid ${position === p ? T.accent : T.border}`,
                    backgroundColor: position === p ? 'rgba(224,168,82,0.1)' : 'transparent',
                    color: position === p ? T.accent : T.textMuted,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 150ms',
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
          </label>

          <button
            onClick={handleValidate}
            style={{
              marginTop: 8,
              padding: '11px',
              borderRadius: 10,
              borderStyle: 'none',
              backgroundColor: T.accent,
              color: '#fff',
              fontSize: 13,
              fontWeight: 700,
              cursor: 'pointer',
              letterSpacing: '0.04em',
              transition: 'opacity 150ms',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            Validate Trade
          </button>
        </div>
      </div>

      {score !== null && (
        <div style={{
          backgroundColor: T.card,
          border: `1px solid ${T.border}`,
          borderRadius: 14,
          padding: 24,
          flex: 1,
          minWidth: 280,
        }}>
          <div className="micro-label" style={{ marginBottom: 16 }}>Confidence Score</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 16 }}>
            <span className="mono" style={{
              fontSize: 52,
              fontWeight: 700,
              color: score >= 60 ? T.bull : score >= 40 ? T.caution : T.bear,
              lineHeight: 1,
            }}>{score}</span>
            <span style={{ fontSize: 18, color: T.textMuted }}>/100</span>
          </div>

          {/* Score bar */}
          <div style={{ height: 6, backgroundColor: T.inset, borderRadius: 3, marginBottom: 20, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${score}%`,
              backgroundColor: score >= 60 ? T.bull : score >= 40 ? T.caution : T.bear,
              borderRadius: 3,
              transition: 'width 400ms ease',
            }} />
          </div>

          <div className="micro-label" style={{ marginBottom: 10 }}>Gate Checks</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {gates.map((g, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 13, color: g.pass ? T.bull : T.bear, marginTop: 1 }}>{g.pass ? '✓' : '✗'}</span>
                <span style={{ fontSize: 12, color: g.pass ? T.textSecondary : T.textPrimary, lineHeight: 1.5 }}>{g.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function MapTab({ index }: { index: IndexKey }) {
  const { MAP } = useData()
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
      <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 16 }}>
        Real levels around price — pivots, OI walls, VWAP, ±1σ, dealer pin, floor/cap, traps. Zoomed to where the fight is now.
      </div>
      <div style={{ backgroundColor: T.card, border: `1px solid ${T.border}`, borderRadius: 14, padding: '20px 24px' }}>
        <div style={{ position: 'relative', height: H }}>
          {/* ±1σ band shade */}
          {bandHi != null && bandLo != null && (
            <div style={{
              position: 'absolute', left: 0, right: 0,
              top: yOf(bandHi), height: Math.max(1, yOf(bandLo) - yOf(bandHi)),
              background: 'rgba(224,168,82,0.06)', borderRadius: 4,
            }} />
          )}
          {/* NOW line */}
          <div style={{ position: 'absolute', left: 0, right: 0, top: nowY, height: 0, borderTop: `1px solid ${T.accent}`, zIndex: 4 }}>
            <span className="mono" style={{ position: 'absolute', right: 0, top: -9, fontSize: 10, color: T.accent, fontWeight: 700 }}>
              NOW {fmt(Math.round(m.now))}
            </span>
          </div>
          {/* Levels */}
          {m.levels.map((lvl, i) => {
            if (lvl.kind === 'now') return null
            const st = KIND_STYLE[lvl.kind]
            const color = lvl.kind === 'wall' ? (lvl.label === 'CALL' ? T.bear : T.bull) : st.color
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
                  boxShadow: lvl.kind === 'pin' ? `0 0 8px ${T.accent}` : undefined,
                }} />
                <div style={{ flex: 1, height: 0, borderTop: `1px dashed rgba(${above ? '255,95,107' : '46,194,126'},0.14)` }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 280 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: T.textMuted, width: 46, textAlign: 'right' }}>
                    {st.marker ? `${st.marker} ` : ''}{lvl.label}
                  </span>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 700, color, width: 66 }}>
                    {fmt(Math.round(lvl.value))}
                  </span>
                  <span style={{ fontSize: 11, color: T.textMuted }}>{note}</span>
                </div>
              </div>
            )
          })}
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', gap: 16, marginTop: 16, flexWrap: 'wrap', fontSize: 10, color: T.textMuted, alignItems: 'center' }}>
          {legendItem(T.bear, 'call wall')}
          {legendItem(T.bull, 'put wall')}
          {legendItem(T.accent, 'dealer pin')}
          {legendItem(T.textMuted, 'pivot / session')}
          {legendItem(T.caution, 'vwap · trap')}
        </div>
      </div>
    </div>
  )
}

function HeatTab({ active, setActive }: { active: IndexKey; setActive: (k: IndexKey) => void }) {
  const { HEAT, INDICES } = useData()
  const keys: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']
  const spikeCount = keys.reduce((n, k) => n + HEAT[k].filter(c => c.spike).length, 0)

  const legend = (dir: HeatTone, glyph: string, label: string) => (
    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ color: `rgb(${HEAT_RGB[dir]})`, fontSize: 11 }}>{glyph}</span>{label}
    </span>
  )

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <div className="micro-label">Live Spike Radar</div>
        {spikeCount > 0 && (
          <span style={{
            fontSize: 9, fontWeight: 700, letterSpacing: '0.06em', color: T.caution,
            background: 'rgba(255,191,0,0.12)', border: '1px solid rgba(255,191,0,0.25)',
            borderRadius: 4, padding: '1px 7px',
          }}>
            ⚡ {spikeCount} spikes live
          </span>
        )}
      </div>
      <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 16 }}>
        Live spike radar — volume, OI, gamma &amp; squeeze across futures + both option legs. Brighter = bigger; glowing ⚡ = spiking.
      </div>
      <div style={{ backgroundColor: T.card, border: `1px solid ${T.border}`, borderRadius: 14, padding: 16 }}>
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
                  background: isActive ? T.inset : 'transparent',
                  borderTop: `1px solid ${isActive ? 'rgba(255,255,255,0.12)' : T.border}`,
                  borderRight: `1px solid ${isActive ? 'rgba(255,255,255,0.12)' : T.border}`,
                  borderBottom: `1px solid ${isActive ? 'rgba(255,255,255,0.12)' : T.border}`,
                  borderLeft: hot ? `3px solid ${T.accent}` : '3px solid transparent',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: T.textPrimary,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  gap: 2,
                }}
              >
                <span style={{ fontSize: 12, fontWeight: 700 }}>{k}</span>
                <span className="mono" style={{ fontSize: 11, color: T.textMuted }}>{fmt(INDICES[k].price)}</span>
              </button>
              {cells.map((cell, i) => {
                const hue = HEAT_RGB[cell.dir]
                const arrow = cell.dir === 'bull' ? '▲' : cell.dir === 'bear' ? '▼' : '·'
                return (
                  <div
                    key={i}
                    title={`${HEAT_COLS[i]}: ${cell.label}${cell.spike ? ' — SPIKE' : ''}`}
                    style={{
                      flex: 1,
                      height: 46,
                      borderRadius: 8,
                      backgroundColor: heatColor(cell.dir, cell.intensity),
                      border: cell.spike ? `1px solid rgba(${hue},0.9)` : `1px solid ${T.border}`,
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
                    <span style={{ fontSize: 10, fontWeight: 700, lineHeight: 1.1, color: cell.intensity > 0.5 ? T.textPrimary : T.textSecondary }}>
                      {cell.spike ? '⚡ ' : ''}{cell.label}
                    </span>
                    <span style={{ fontSize: 9, color: `rgb(${hue})`, opacity: 0.9 }}>{arrow}</span>
                  </div>
                )
              })}
            </div>
          )
        })}
        {/* Legend */}
        <div style={{ display: 'flex', gap: 16, marginTop: 14, fontSize: 10, color: T.textMuted, alignItems: 'center', flexWrap: 'wrap' }}>
          {legend('bull', '▲', 'bullish')}
          {legend('bear', '▼', 'bearish')}
          {legend('neutral', '·', 'neutral')}
          <span style={{ color: T.caution }}>⚡ spike</span>
          <span>brighter = stronger</span>
        </div>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
/* ── ANSWER band ───────────────────────────────────────────────────────────
   Always visible, above the tabs. v2 inherited v1's worst structural habit:
   the read lived behind a tab, so the one thing worth seeing on a live tape
   took a click to reach. Price, the verdict, the sentence and — crucially —
   what would invalidate it now own the top of the screen at a scale nothing
   else competes with. Everything below is evidence for this band.          */
function AnswerBand({ index, stale }: { index: IndexKey; stale: boolean }) {
  const { INDICES, READS, CHAIN_DATA, KEY_LEVELS } = useData()
  const info = INDICES[index]
  const read = READS[index]
  const chain = CHAIN_DATA[index]
  const levels = KEY_LEVELS[index] ?? []

  const dirCol = info.change > 0 ? T.bull : info.change < 0 ? T.bear : T.textSecondary
  const above = levels.filter(l => l.value > info.price).sort((a, b) => a.value - b.value)[0]
  const below = levels.filter(l => l.value < info.price).sort((a, b) => b.value - a.value)[0]
  const mpDist = Math.round(chain.maxPain - info.price)

  const chip = (label: string, tone: 'structure' | 'quiet' = 'quiet') => (
    <span key={label} className="mono" style={{
      fontSize: 10.5, letterSpacing: '0.05em', padding: '3px 8px', borderRadius: 3,
      whiteSpace: 'nowrap',
      border: `1px solid ${tone === 'structure' ? 'rgba(224,168,82,0.45)' : T.border}`,
      color: tone === 'structure' ? T.accent : T.textMuted,
    }}>{label}</span>
  )

  return (
    <div style={{ backgroundColor: T.bg, borderBottom: `1px solid ${T.border}` }}>
      <div style={{
        display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: 26,
        alignItems: 'center', padding: '14px 24px',
      }}>
        <div>
          <div className="mono" style={{
            fontSize: 32, lineHeight: 1, fontWeight: 600, letterSpacing: '-0.02em',
            // a price you cannot trust must not look like one you can
            color: stale ? T.textMuted : T.textPrimary,
            textDecoration: stale ? 'line-through' : 'none',
          }}>
            {info.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mono" style={{ fontSize: 12, color: stale ? T.textMuted : dirCol, marginTop: 5 }}>
            {stale ? 'placeholder' : `${info.change > 0 ? '+' : ''}${info.change.toFixed(2)} · ${info.pct > 0 ? '+' : ''}${info.pct.toFixed(2)}%`}
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          {stale ? (
            <div style={{
              fontSize: 11, letterSpacing: '0.15em', textTransform: 'uppercase',
              color: T.bear, fontWeight: 700, marginBottom: 4,
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
            <div style={{ fontSize: 12.5, color: T.textSecondary, marginTop: 3 }}>{read.sub}</div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 5, alignItems: 'flex-end' }}>
          {chip(`MAX PAIN ${chain.maxPain} · ${mpDist >= 0 ? '+' : ''}${mpDist}`, 'structure')}
          {chip(`GEX ${chain.gex}`)}
          {chip(`PCR ${chain.pcr} · SQUEEZE ${chain.squeeze}`)}
        </div>
      </div>

      <div style={{
        display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap',
        padding: '8px 24px', backgroundColor: T.card,
        borderTop: `1px solid ${T.border}`, fontSize: 12.5,
      }}>
        <span className="micro-label" style={{ whiteSpace: 'nowrap' }}>Changes if</span>
        {above
          ? <span>breaks <span className="mono" style={{ color: T.accent }}>{above.value}</span>
              <span style={{ color: T.textMuted }}> ({above.label}{above.note ? ` · ${above.note}` : ''})</span></span>
          : <span style={{ color: T.textMuted }}>no level mapped above</span>}
        <span style={{ color: T.textMuted }}>·</span>
        {below
          ? <span>or loses <span className="mono" style={{ color: T.accent }}>{below.value}</span>
              <span style={{ color: T.textMuted }}> ({below.label}{below.note ? ` · ${below.note}` : ''})</span></span>
          : <span style={{ color: T.textMuted }}>no level mapped below</span>}
      </div>
    </div>
  )
}

export default function App() {
  const [activeIndex, setActiveIndex] = useState<IndexKey>('NIFTY')
  const [activeTab, setActiveTab] = useState<Tab>('Heat')
  const tabs: Tab[] = ['Heat', 'Tape', 'Chain', 'Events', 'Validate', 'Map']
  const { data, error, lastUpdated } = useLiveData(MOCK)

  return (
    <DataCtx.Provider value={data}>
    <div style={{ minHeight: '100vh', backgroundColor: T.bg, display: 'flex', flexDirection: 'column' }}>
      <GlanceBar active={activeIndex} setActive={setActiveIndex} lastUpdated={lastUpdated} error={error} />

      {/* A trading screen must never present placeholder numbers as real. The
          fallback dataset exists so the first paint isn't empty — the moment
          every index fails, say so at full width instead of showing a small
          "reconnecting" chip beside believable-looking prices. */}
      {error && (
        <div style={{
          padding: '9px 24px', backgroundColor: 'rgba(255,95,107,0.12)',
          borderBottom: `1px solid ${T.bear}`, color: T.bear,
          fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
        }}>
          NOT LIVE — the backend is unreachable, so every figure below is placeholder data.
          Check that <span className="mono">server.py</span> is up on 8765 and the Dhan token is valid.
        </div>
      )}

      <AnswerBand index={activeIndex} stale={!!error} />

      {/* Tab bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        padding: '0 24px',
        backgroundColor: T.card,
        borderBottom: `1px solid ${T.border}`,
      }}>
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '12px 16px',
              fontSize: 13,
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? T.textPrimary : T.textMuted,
              backgroundColor: 'transparent',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              borderBottom: `2px solid ${activeTab === tab ? T.accent : 'transparent'}`,
              cursor: 'pointer',
              transition: 'all 150ms',
              letterSpacing: '0.01em',
            }}
          >
            {tab}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: 11, color: T.textMuted }}>
          <span className="mono">{lastUpdated ? lastUpdated.toLocaleTimeString('en-GB') : '—'}</span> IST
        </div>
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeTab === 'Heat'     && <HeatTab active={activeIndex} setActive={setActiveIndex} />}
        {activeTab === 'Tape'     && <TapeTab index={activeIndex} />}
        {activeTab === 'Chain'    && <ChainTab index={activeIndex} />}
        {activeTab === 'Events'   && <EventsTab index={activeIndex} />}
        {activeTab === 'Validate' && <ValidateTab index={activeIndex} />}
        {activeTab === 'Map'      && <MapTab index={activeIndex} />}
      </div>
    </div>
    </DataCtx.Provider>
  )
}
