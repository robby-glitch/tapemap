// ── Live data layer ────────────────────────────────────────────────────────────
// Fetches the real TapeMap Python backend (proxied at /api) and maps its JSON
// into the exact shapes the App.tsx components already consume. On mount and
// every 5s it pulls /api/data and /api/chain for all three indices in parallel,
// tolerating a failing index (keeps last-good / mock fallback per index).
import { useEffect, useRef, useState } from 'react'

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
  type?: 'callwall' | 'putwall' | 'atm'
}
export interface Chain {
  pcr: string
  maxPain: number
  gex: string
  squeeze: string
  strikes: StrikeRow[]
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

// Market Heat Grid — one row per index, one cell per signal column.
export const HEAT_COLS = ['MOM', 'TIME', 'BIAS', 'GAMMA', 'SQZ', 'FLOW'] as const
export type HeatCol = (typeof HEAT_COLS)[number]
export type HeatTone = 'bull' | 'bear' | 'neutral'
export interface HeatCell {
  label: string
  tone: HeatTone
  intensity: 0 | 1 | 2 | 3
}

// Intraday Pressure Tape — one cell per bar, val in [-1, 1] (buy pressure +, sell −).
export interface PressCell {
  t: string
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
  chart: ChartPoint[]
  heat: HeatCell[]
  pressure: PressCell[]
  map: MapData
}

// ── Mapping helpers ─────────────────────────────────────────────────────────────
const VERDICT_SCORE: Record<string, number> = {
  GO: 3, READY: 2, WAIT: 0, CAUTION: 0, 'STAND ASIDE': -1, SPENT: -1,
}

// Heat-grid lookups for the TIME (verdict) and GAMMA (regime) columns.
const TIME_HEAT: Record<string, { tone: HeatTone; intensity: 0 | 1 | 2 | 3 }> = {
  GO: { tone: 'bull', intensity: 3 },
  READY: { tone: 'bull', intensity: 2 },
  WAIT: { tone: 'neutral', intensity: 1 },
  CAUTION: { tone: 'bear', intensity: 0 },
  'STAND ASIDE': { tone: 'neutral', intensity: 0 },
  SPENT: { tone: 'bear', intensity: 0 },
}
const GAMMA_HEAT: Record<string, { tone: HeatTone; intensity: 0 | 1 | 2 | 3 }> = {
  'AMPLIFIED-UP': { tone: 'bull', intensity: 3 },
  'AMPLIFIED-DOWN': { tone: 'bear', intensity: 3 },
  FLOOR: { tone: 'bull', intensity: 1 },
  CEILING: { tone: 'bear', intensity: 1 },
  PINNED: { tone: 'neutral', intensity: 2 },
  BALANCE: { tone: 'neutral', intensity: 0 },
  NEUTRAL: { tone: 'neutral', intensity: 0 },
}
const clampI = (n: number): 0 | 1 | 2 | 3 => Math.max(0, Math.min(3, Math.round(n))) as 0 | 1 | 2 | 3
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))

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

function eventDir(e: any): 'bull' | 'bear' | 'neutral' {
  const side = e?.data?.side
  const msg = String(e?.msg ?? '').toUpperCase()
  const hasBear = /BEAR|\bDOWN\b/.test(msg)
  if (side === 'BULL' || (/BULL|\bUP\b/.test(msg) && !hasBear)) return 'bull'
  if (side === 'BEAR' || hasBear) return 'bear'
  return 'neutral'
}

// De-dup near-equal level values (within `tol` pts), keeping the first seen.
function dedupLevels(levels: Level[], tol = 2): Level[] {
  const out: Level[] = []
  for (const lvl of levels) {
    if (out.some((k) => Math.abs(k.value - lvl.value) <= tol)) continue
    out.push(lvl)
  }
  return out
}

function mapIndex(D: any, C: any): PerIndex {
  const day = D.days[D.days.length - 1]
  const bars = day.bars
  const b = bars[bars.length - 1]
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

  // KEY_LEVELS
  const wallUp = m.wall_up
  const wallDn = m.wall_dn
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
      { label: 'ATM IV', value: `${((g?.iv_ce ?? 0) * 100).toFixed(1)}/${((g?.iv_pe ?? 0) * 100).toFixed(1)}%` },
    ],
  }

  // CHAIN_DATA
  const gexR = m.gex_regime
  const sqScore = m.squeeze?.score ?? 0
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
      type: (s.k === atm ? 'atm' : s.k === wallUp ? 'callwall' : s.k === wallDn ? 'putwall' : undefined) as StrikeRow['type'],
    }))
    .reverse() // highest strike on top, matching the design ladder
  const chain: Chain = {
    pcr: (m.pcr_oi ?? 0).toFixed(2),
    maxPain: m.max_pain ?? 0,
    gex: gexR === 'POSITIVE' ? 'Positive' : gexR === 'NEGATIVE' ? 'Negative' : 'Neutral',
    squeeze: sqScore > 0.3 ? 'High' : sqScore > 0.1 ? 'Medium' : 'Low',
    strikes,
  }

  // EVENTS
  const evs: any[] = day.events ?? []
  const events: EventItem[] = evs
    .slice(-10)
    .reverse()
    .map((e) => ({
      time: e.t,
      text: (EVENT_PREFIX[e.kind] || '') + trimMsg(e.msg),
      tag: e.kind,
      dir: eventDir(e),
    }))

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

  // HEAT — one cell per signal column (HEAT_COLS order).
  const z = f.z ?? 0
  const momInt: 0 | 1 | 2 | 3 = episode.includes('MOVE RUNNING') ? 3 : clampI(Math.abs(z))
  const timeH = TIME_HEAT[verdict] ?? { tone: 'neutral' as HeatTone, intensity: 0 as const }
  const gammaH = GAMMA_HEAT[regime] ?? { tone: 'neutral' as HeatTone, intensity: 0 as const }
  const sq = m.squeeze ?? { side: 'DOWN', score: 0 }
  const sqInt: 0 | 1 | 2 | 3 = sq.score > 0.3 ? 3 : sq.score > 0.15 ? 2 : sq.score > 0.05 ? 1 : 0
  const flowTone: HeatTone = phrase1 === 'Fresh shorts building'
    ? 'bear'
    : phrase1 === 'Longs adding into the move'
    ? 'bull'
    : 'neutral'
  const flowLabel = phrase1 === 'Fresh shorts building'
    ? 'shorts'
    : phrase1 === 'Longs adding into the move'
    ? 'longs'
    : phrase1 === 'Positions covering'
    ? 'covering'
    : 'flat'
  const heat: HeatCell[] = [
    { label: `z ${z >= 0 ? '+' : ''}${z.toFixed(1)}`, tone: z > 0.5 ? 'bull' : z < -0.5 ? 'bear' : 'neutral', intensity: momInt },
    { label: verdict || 'WAIT', tone: timeH.tone, intensity: timeH.intensity },
    { label: breadth || 'MIXED', tone: breadth.includes('BULL') ? 'bull' : breadth.includes('BEAR') ? 'bear' : 'neutral', intensity: breadth.includes('STRONG') ? 3 : breadth.includes('LEAN') ? 2 : 0 },
    { label: regime || 'BALANCE', tone: gammaH.tone, intensity: gammaH.intensity },
    { label: `${sq.side} ${(sq.score ?? 0).toFixed(2)}`, tone: sq.side === 'UP' ? 'bull' : 'bear', intensity: sqInt },
    { label: flowLabel, tone: flowTone, intensity: flow.main.includes('decelerating') ? 1 : 2 },
  ]

  // PRESSURE — one cell per bar (skip the first 3, which have no 3-bar lookback).
  const pressure: PressCell[] = bars.slice(3).map((bar: any, j: number) => {
    const i = j + 3
    const oiUp = bar.fut.oi_slope > 0
    const pDir = Math.sign(bar.fut.c - bars[i - 3].fut.c)
    const mag = bar.fut.oi_r ?? 0.3
    const val = clamp((oiUp ? 1 : -0.3) * pDir * mag, -1, 1)
    return {
      t: bar.t,
      val,
      price: bar.fut.c,
      note: `${bar.t} · ${Math.round(bar.fut.c)} · ${val > 0.05 ? 'buying' : val < -0.05 ? 'selling' : 'flat'} (oiR ${(bar.fut.oi_r ?? 0).toFixed(2)})`,
    }
  })

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
  if (ctx.pin?.k != null) addLvl(ctx.pin.k, 'PIN', 'pin', `dealer magnet (${ctx.pin.regime})`, 2)
  const piv = day.pivots || {}
  for (const key of ['R3', 'R2', 'R1', 'P', 'S1', 'S2', 'S3']) addLvl(piv[key], key, 'pivot', 'pivot', 3)
  addLvl(f.vwap, 'VWAP', 'vwap', 'fair value', 4)
  if (ctx.floor) addLvl(ctx.floor[1], 'FLR', 'floor', String(ctx.floor[0]), 5)
  if (ctx.cap) addLvl(ctx.cap[1], 'CAP', 'cap', String(ctx.cap[0]), 5)
  addLvl(f.u1, '+1σ', 'band', 'volatility band', 6)
  addLvl(f.d1, '−1σ', 'band', 'volatility band', 6)
  addLvl(day.strike, 'STK', 'strike', 'ATM strike', 7)
  addLvl(sesHi, 'HI', 'session', 'session high', 8)
  addLvl(sesLo, 'LO', 'session', 'session low', 8)
  // Traps: resolve each trap event's price by its bar's close, dedupe by price, keep latest, max 3.
  const tClose: Record<string, number> = {}
  for (const bar of bars) tClose[bar.t] = bar.fut.c
  const trapKinds = new Set(['TRAP-SPRUNG', 'TRAP-SETTING', 'SPRING-FAIL'])
  const trapEvs = (day.events ?? []).filter((e: any) => trapKinds.has(e.kind)).slice(-6)
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

  return { index, score, read, levels, flow, chain, events, chart, heat, pressure, map }
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
    ds.CHART_DATA[k] = p.chart
    ds.HEAT[k] = p.heat
    ds.PRESSURE[k] = p.pressure
    ds.MAP[k] = p.map
  }
  return ds
}

// ── Hook ────────────────────────────────────────────────────────────────────────
export function useLiveData(fallback: Dataset) {
  const [data, setData] = useState<Dataset>(fallback)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const lastGood = useRef<Record<IndexKey, PerIndex>>(perFromFallback(fallback))

  useEffect(() => {
    let alive = true

    async function fetchIdx(k: IndexKey): Promise<PerIndex | null> {
      try {
        const [dr, cr] = await Promise.all([
          fetch('/api/data?idx=' + k),
          fetch('/api/chain?idx=' + k),
        ])
        if (!dr.ok || !cr.ok) throw new Error('http ' + dr.status + '/' + cr.status)
        const [D, C] = await Promise.all([dr.json(), cr.json()])
        return mapIndex(D, C)
      } catch {
        return null
      }
    }

    async function tick() {
      const results = await Promise.all(KEYS.map(fetchIdx))
      if (!alive) return
      const per = {} as Record<IndexKey, PerIndex>
      let failures = 0
      KEYS.forEach((k, i) => {
        const r = results[i]
        if (r) per[k] = r
        else {
          per[k] = lastGood.current[k]
          failures++
        }
      })
      lastGood.current = per
      setData(assemble(per))
      setLoading(false)
      setLastUpdated(new Date())
      setError(failures === KEYS.length ? 'reconnecting' : null)
    }

    tick()
    const id = setInterval(tick, 5000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  return { data, loading, error, lastUpdated }
}
