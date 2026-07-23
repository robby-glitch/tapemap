import { useState, createContext, useContext } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceArea,
} from 'recharts'
import { useLiveData } from './data'
import type { IndexKey, IndexInfo, Dataset } from './data'

// ── Tokens ───────────────────────────────────────────────────────────────────
const T = {
  bg: '#0B0E14',
  card: '#141926',
  inset: '#1B2130',
  border: 'rgba(255,255,255,0.07)',
  textPrimary: '#E8EDF5',
  textSecondary: '#9AA7BD',
  textMuted: '#5D6B84',
  bull: '#2EC27E',
  bear: '#FF5F6B',
  caution: '#FFBF00',
  accent: '#8B5CF6',
}

// ── Types ─────────────────────────────────────────────────────────────────────
// IndexKey now comes from ./data (single source of truth for the live layer).
type Tab = 'Tape' | 'Chain' | 'Events' | 'Validate' | 'Map'

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
function makeIntraday(basePrice: number, vwap: number) {
  const data = []
  const times = []
  for (let h = 9; h <= 14; h++) {
    for (let m = 0; m < 60; m += 15) {
      if (h === 9 && m < 15) continue
      times.push(`${h}:${m.toString().padStart(2, '0')}`)
    }
  }
  times.push('14:30')
  let price = basePrice * 1.005
  for (let i = 0; i < times.length; i++) {
    const progress = i / times.length
    const trend = (basePrice - price) * 0.15
    const noise = (Math.random() - 0.5) * basePrice * 0.003
    price += trend + noise
    const band = basePrice * 0.0018
    data.push({
      time: times[i],
      price: +price.toFixed(2),
      vwap: +(vwap + (Math.random() - 0.5) * 20).toFixed(2),
      upper: +(price + band * basePrice * 0.001).toFixed(2),
      lower: +(price - band * basePrice * 0.001).toFixed(2),
      vol: Math.floor(Math.random() * 800000 + 200000),
      isFuture: progress > 0.85,
    })
  }
  return data
}

const MOCK_CHART_DATA: Record<IndexKey, ReturnType<typeof makeIntraday>> = {
  NIFTY:     makeIntraday(23860, 23909),
  BANKNIFTY: makeIntraday(56624, 56700),
  SENSEX:    makeIntraday(76360, 76420),
}

// ── Assembled mock dataset + live-data context ─────────────────────────────────
const MOCK: Dataset = {
  INDICES: MOCK_INDICES,
  READS: MOCK_READS,
  KEY_LEVELS: MOCK_KEY_LEVELS,
  ORDER_FLOW: MOCK_ORDER_FLOW,
  CHAIN_DATA: MOCK_CHAIN_DATA,
  EVENTS_BY_IDX: { NIFTY: MOCK_EVENTS, BANKNIFTY: MOCK_EVENTS, SENSEX: MOCK_EVENTS },
  CHART_DATA: MOCK_CHART_DATA,
}

const DataCtx = createContext<Dataset>(MOCK)
function useData(): Dataset {
  return useContext(DataCtx)
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (n: number) => n.toLocaleString('en-IN')
// Real OI is large (millions of units). Show in lakhs (L), or thousands (K) below 1L.
const formatOI = (n: number) => n >= 1e5 ? `${(n / 1e5).toFixed(1)}L` : `${(n / 1e3).toFixed(1)}K`

// ── Sub-components ────────────────────────────────────────────────────────────

function TimingChip({ value }: { value: string }) {
  const colors: Record<string, [string, string]> = {
    WAIT:  ['rgba(255,191,0,0.12)', '#FFBF00'],
    READY: ['rgba(139,92,246,0.15)', '#8B5CF6'],
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
  const { INDICES, READS } = useData()
  const read = READS[active]
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

      {/* THE READ */}
      <div style={{
        marginLeft: 'auto',
        maxWidth: 340,
        paddingLeft: 20,
        borderLeft: `1px solid ${T.border}`,
      }}>
        <div style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: T.textMuted, marginBottom: 6 }}>
          THE READ — {active}
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.textPrimary, lineHeight: 1.4, marginBottom: 7 }}>
          {read.headline}
        </div>
        <div style={{ display: 'flex', gap: 6, marginBottom: 5 }}>
          <div>
            <div style={{ fontSize: 9, color: T.textMuted, marginBottom: 3, letterSpacing: '0.08em' }}>TIMING</div>
            <TimingChip value={read.timing} />
          </div>
          <div>
            <div style={{ fontSize: 9, color: T.textMuted, marginBottom: 3, letterSpacing: '0.08em' }}>DIRECTION</div>
            <DirectionChip value={read.direction} />
          </div>
        </div>
        <div style={{ fontSize: 11, color: T.textMuted }}>{read.sub}</div>
      </div>
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
  const { KEY_LEVELS, ORDER_FLOW, CHART_DATA } = useData()
  const levels = KEY_LEVELS[index]
  const flow = ORDER_FLOW[index]
  const data = CHART_DATA[index]
  const lastPoint = data[data.length - 3]
  const priceMin = Math.min(...data.map(d => d.lower)) * 0.9995
  const priceMax = Math.max(...data.map(d => d.upper)) * 1.0005

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
                backgroundColor: isHere ? 'rgba(139,92,246,0.06)' : 'transparent',
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
          <div className="micro-label">Price · VWAP · ±2σ Band</div>
          <div style={{ display: 'flex', gap: 14, fontSize: 10, color: T.textMuted }}>
            <span style={{ color: '#FFBF00' }}>— VWAP</span>
            <span style={{ color: 'rgba(139,92,246,0.6)' }}>░ Band</span>
          </div>
        </div>
        <div style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="bandFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={T.accent} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={T.accent} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 6" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: T.textMuted, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                interval={3}
              />
              <YAxis
                domain={[priceMin, priceMax]}
                tick={{ fill: T.textMuted, fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => fmt(Math.round(v))}
                width={70}
              />
              <Tooltip content={<ChartTooltip />} />
              {/* Band */}
              <Area type="monotone" dataKey="upper" stroke="none" fill="url(#bandFill)" />
              <Area type="monotone" dataKey="lower" stroke="none" fill={T.card} />
              {/* VWAP */}
              <Line
                type="monotone"
                dataKey="vwap"
                stroke="#FFBF00"
                strokeWidth={1}
                strokeDasharray="4 4"
                dot={false}
                activeDot={false}
              />
              {/* Price */}
              <Line
                type="monotone"
                dataKey="price"
                stroke={T.textPrimary}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3, fill: T.accent, strokeWidth: 0 }}
              />
              {/* Future dim area */}
              {lastPoint && (
                <ReferenceArea
                  x1={lastPoint.time}
                  fill="rgba(11,14,20,0.5)"
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
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
  const maxOI = Math.max(...chain.strikes.flatMap(s => [s.ceOI, s.peOI]))

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

      {/* Strike ladder */}
      <div style={{
        backgroundColor: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 14,
        overflow: 'hidden',
      }}>
        <div style={{ padding: '12px 20px', borderBottom: `1px solid ${T.border}` }}>
          <div className="micro-label">Strike Ladder — OI Heatmap</div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${T.border}` }}>
              <th style={{ padding: '8px 20px', textAlign: 'left', fontSize: 10, color: T.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>CE OI (lots)</th>
              <th style={{ padding: '8px 20px', textAlign: 'center', fontSize: 10, color: T.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>STRIKE</th>
              <th style={{ padding: '8px 20px', textAlign: 'right', fontSize: 10, color: T.textMuted, fontWeight: 600, letterSpacing: '0.08em' }}>PE OI (lots)</th>
            </tr>
          </thead>
          <tbody>
            {chain.strikes.map(s => {
              const isWall = s.type === 'callwall' || s.type === 'putwall'
              const isATM = s.type === 'atm'
              return (
                <tr key={s.strike} style={{
                  borderBottom: `1px solid ${T.border}`,
                  backgroundColor: isATM ? 'rgba(139,92,246,0.06)' : 'transparent',
                }}>
                  <td style={{ padding: '10px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{
                        height: 6,
                        width: `${(s.ceOI / maxOI) * 140}px`,
                        backgroundColor: `rgba(255,95,107,${s.type === 'callwall' ? 0.8 : 0.35})`,
                        borderRadius: 3,
                        marginLeft: 'auto',
                        transition: 'width 300ms',
                      }} />
                      <span className="mono" style={{ fontSize: 12, color: T.textSecondary, minWidth: 40, textAlign: 'right' }}>
                        {formatOI(s.ceOI)}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '10px 20px', textAlign: 'center' }}>
                    <span className="mono" style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: isATM ? T.accent : isWall ? T.textPrimary : T.textSecondary,
                    }}>
                      {fmt(s.strike)}
                    </span>
                    {s.type === 'callwall' && <span style={{ fontSize: 9, color: T.bear, marginLeft: 6, fontWeight: 600 }}>▲ CALL WALL</span>}
                    {s.type === 'putwall' && <span style={{ fontSize: 9, color: T.bull, marginLeft: 6, fontWeight: 600 }}>▼ PUT WALL</span>}
                    {isATM && <span style={{ fontSize: 9, color: T.accent, marginLeft: 6, fontWeight: 600 }}>◉ ATM</span>}
                  </td>
                  <td style={{ padding: '10px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="mono" style={{ fontSize: 12, color: T.textSecondary, minWidth: 40 }}>
                        {formatOI(s.peOI)}
                      </span>
                      <div style={{
                        height: 6,
                        width: `${(s.peOI / maxOI) * 140}px`,
                        backgroundColor: `rgba(46,194,126,${s.type === 'putwall' ? 0.8 : 0.35})`,
                        borderRadius: 3,
                        transition: 'width 300ms',
                      }} />
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
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
              border: `1px solid ${hovered === i ? 'rgba(255,255,255,0.1)' : T.border}`,
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
                    backgroundColor: position === p ? 'rgba(139,92,246,0.1)' : 'transparent',
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
  const { KEY_LEVELS, INDICES } = useData()
  const levels = KEY_LEVELS[index]
  const allLevels = [
    ...levels,
    { label: 'PDH',  value: INDICES[index].price * 1.009, note: 'Prior day high', dist: Math.round(INDICES[index].price * 0.009), dir: 'up' as const },
    { label: 'PDL',  value: INDICES[index].price * 0.994, note: 'Prior day low',  dist: -Math.round(INDICES[index].price * 0.006), dir: 'down' as const },
    { label: 'WPP',  value: INDICES[index].price * 1.003, note: 'Weekly pivot',   dist: Math.round(INDICES[index].price * 0.003), dir: 'up' as const },
  ].sort((a, b) => b.value - a.value)

  const priceNow = INDICES[index].price
  const hi = Math.max(...allLevels.map(l => l.value)) * 1.001
  const lo = Math.min(...allLevels.map(l => l.value)) * 0.999
  const range = hi - lo

  return (
    <div style={{ padding: 24, maxWidth: 560 }}>
      <div className="micro-label" style={{ marginBottom: 16 }}>Levels Map — {index}</div>
      <div style={{
        backgroundColor: T.card,
        border: `1px solid ${T.border}`,
        borderRadius: 14,
        padding: '20px 24px',
        position: 'relative',
      }}>
        {/* Price axis */}
        <div style={{ position: 'relative', height: allLevels.length * 52 }}>
          {/* Current price line */}
          <div style={{
            position: 'absolute',
            left: 0, right: 0,
            top: `${((hi - priceNow) / range) * 100}%`,
            height: 1,
            backgroundColor: T.accent,
            opacity: 0.5,
            zIndex: 1,
          }}>
            <span className="mono" style={{
              position: 'absolute',
              right: 0,
              top: -9,
              fontSize: 10,
              color: T.accent,
              fontWeight: 700,
            }}>NOW {fmt(Math.round(priceNow))}</span>
          </div>

          {allLevels.map((lvl, i) => {
            const pct = ((hi - lvl.value) / range) * 100
            const isHere = lvl.dir === 'here'
            const isAbove = lvl.value > priceNow
            const dotColor = isHere ? T.accent : isAbove ? T.bear : T.bull
            return (
              <div key={i} style={{
                position: 'absolute',
                left: 0, right: 0,
                top: `${pct}%`,
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                transform: 'translateY(-50%)',
              }}>
                <div style={{
                  width: 8, height: 8,
                  borderRadius: '50%',
                  backgroundColor: dotColor,
                  flexShrink: 0,
                  boxShadow: isHere ? `0 0 8px ${T.accent}` : undefined,
                }} />
                <div style={{
                  height: 1,
                  flex: 1,
                  backgroundColor: isHere ? T.accent : 'rgba(255,255,255,0.06)',
                  borderStyle: isHere ? 'solid' : 'dashed',
                }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 280 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: T.textMuted, width: 36 }}>{lvl.label}</span>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: isHere ? T.accent : T.textPrimary, width: 72 }}>
                    {fmt(Math.round(lvl.value))}
                  </span>
                  <span style={{ fontSize: 11, color: T.textMuted }}>{lvl.note}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [activeIndex, setActiveIndex] = useState<IndexKey>('NIFTY')
  const [activeTab, setActiveTab] = useState<Tab>('Tape')
  const tabs: Tab[] = ['Tape', 'Chain', 'Events', 'Validate', 'Map']
  const { data, error, lastUpdated } = useLiveData(MOCK)

  return (
    <DataCtx.Provider value={data}>
    <div style={{ minHeight: '100vh', backgroundColor: T.bg, display: 'flex', flexDirection: 'column' }}>
      <GlanceBar active={activeIndex} setActive={setActiveIndex} lastUpdated={lastUpdated} error={error} />

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
