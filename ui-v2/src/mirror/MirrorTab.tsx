// MIRROR — the futures chart with the option charts under it, the way the
// operator reads GoCharting: "along with futures chart i look at the mirror
// chart of options as well ... it has same vwap steup +-3 std deviation
// pivots". FUT on top (/api/data), CE and PE side by side (/api/contract, one
// FIXED contract per pane), one 09:15->15:30 time axis, one crosshair.
//
// Why a small SVG chart and not ContractChart/LegChart: the vendored candl
// engine is bar-index based with its own pan/zoom, so it cannot pin a shared
// 09:15->15:30 axis or take a crosshair from another pane. Same palette, same
// candle pair (CHART_UP/DOWN), same band colours (LEG_BAND_LINES) instead.
//
// Nothing is derived here but `z` on the option legs, which /api/contract
// does not send: (close - VWAP) / (u1 - VWAP), the engine's own formula
// (engine.py), off that contract's measured close and bands.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { IndexKey } from '../data'
import { TL, CHART_UP, CHART_DOWN, MONO, rgbOf } from '../theme'
import { LEG_BAND_LINES, OI_LINE, PIV_LINE, lakh } from '../trade/indicators'

// LIGHT only: the operator does not read dark screens.
const pal = TL
const wash = (hex: string, a: number) => `rgba(${rgbOf(hex)},${a})`

const S0 = 9 * 60 + 15                 // 09:15, the session's first minute
const S1 = 15 * 60 + 30                // 15:30, the close
const END = '15:30'                    // bars stamped here or later are not session
const TICKS = [S0, 600, 660, 720, 780, 840, 900, S1]
const GUT = 62, OI_H = 26, AX_H = 14, TOP = 16
const PIV_KEYS = ['R3', 'R2', 'R1', 'P', 'S1', 'S2', 'S3'] as const
const POLL_MS = 15000
const IV_KEY = 'tape.mirror.interval'

type Piv = Record<(typeof PIV_KEYS)[number], number>
type BandKey = 'vwap' | 'u1' | 'd1' | 'u2' | 'd2' | 'u3' | 'd3'
interface MBar {
  t: string; m: number; o: number; h: number; l: number; c: number
  oi: number | null; z: number | null
  b: Record<BandKey, number | null>
}
interface Hover { m: number; id: string; y: number }
type Side = 'CE' | 'PE'
type Iv = 3 | 5

// ── small helpers ─────────────────────────────────────────────────────────
const num = (x: unknown): number | null =>
  typeof x === 'number' && Number.isFinite(x) ? x : null
const toMin = (t: string) => { const [h, m] = t.split(':').map(Number); return h * 60 + m }
const hhmm = (m: number) =>
  `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(Math.floor(m % 60)).padStart(2, '0')}`
const f2 = (v: number | null) => (v == null ? '—' : v.toFixed(2))
const sgn = (v: number | null) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}`)

function readPiv(p: unknown): Piv | null {
  if (!p || typeof p !== 'object') return null
  const o = p as Record<string, unknown>
  return PIV_KEYS.every((k) => num(o[k]) != null) ? (o as unknown as Piv) : null
}

function mbar(t: string, x: Record<string, unknown>, band: Record<string, unknown>,
              z: number | null | 'calc'): MBar | null {
  const o = num(x.o), h = num(x.h), l = num(x.l), c = num(x.c)
  if (o == null || h == null || l == null || c == null) return null
  const b = {} as Record<BandKey, number | null>
  for (const [k] of LEG_BAND_LINES) b[k as BandKey] = num(band[k as string])
  const span = b.u1 != null && b.vwap != null ? b.u1 - b.vwap : null
  const zz = z === 'calc' ? (span != null && span > 1e-9 ? (c - (b.vwap as number)) / span : null) : z
  return { t, m: toMin(t), o, h, l, c, oi: num(x.oi), z: zz, b }
}

/** One reply, or the reason there is none. Never throws. */
async function get(url: string): Promise<{ j: any; why: null } | { j: null; why: string }> {
  try {
    const r = await fetch(url)
    return { j: await r.json(), why: null }
  } catch (e) {
    return { j: null, why: `backend unreachable (${e instanceof Error ? e.message : 'fetch failed'})` }
  }
}

function istNow() {
  const d = new Date(Date.now() + 5.5 * 3600000)
  return { hm: d.getUTCHours() * 60 + d.getUTCMinutes(), wd: d.getUTCDay() }
}

// ── data ──────────────────────────────────────────────────────────────────
interface FutState {
  why: string | null; bars: MBar[]; hidden: number; pivots: Piv | null
  label: string; engineStrike: number | null
}
function readFut(r: Awaited<ReturnType<typeof get>>): FutState {
  const empty = { bars: [], hidden: 0, pivots: null, label: '', engineStrike: null }
  if (r.why) return { ...empty, why: r.why }
  const j = r.j
  const day = Array.isArray(j?.days) ? j.days[j.days.length - 1] : null
  if (!day) return { ...empty, why: j?.live_error || j?.error || 'the backend has no session for this index yet' }
  const bars: MBar[] = []
  let hidden = 0
  for (const row of day.bars ?? []) {
    if (!row?.fut || typeof row.t !== 'string') continue
    if (row.t >= END) { hidden++; continue }
    const b = mbar(row.t, row.fut, row.fut, num(row.fut.z))
    if (b) bars.push(b)
  }
  return { why: null, bars, hidden, pivots: readPiv(day.pivots), label: String(day.day ?? ''),
           engineStrike: num(j.strike) ?? num(day.strike) }
}

interface ChainState {
  why: string | null; atm: number | null; spot: number | null; ts: string
  strikes: number[]; step: number | null; since: { ts: string; prev: number | null; atStart: boolean } | null
}
function readChain(r: Awaited<ReturnType<typeof get>>): ChainState {
  const none = { atm: null, spot: null, ts: '', strikes: [], step: null, since: null }
  if (r.why) return { ...none, why: r.why }
  const j = r.j
  if (!j?.ok || num(j.atm) == null) return { ...none, why: j?.error || 'the chain has no ATM yet' }
  const strikes = (j.strikes ?? []).map((s: any) => num(s?.k)).filter((k: number | null): k is number => k != null)
    .sort((a: number, b: number) => a - b)
  let step: number | null = null
  for (let i = 1; i < strikes.length; i++) {
    const d = strikes[i] - strikes[i - 1]
    if (d > 0 && (step == null || d < step)) step = d
  }
  const atm = j.atm as number
  // Since when has index spot been nearest this strike? Walked back through
  // the chain's own spot record [M]; a gap in the record stops the walk.
  let since: ChainState['since'] = null
  const ser: any[] = Array.isArray(j.series) ? j.series : []
  if (step && ser.length) {
    const near = (s: number) => Math.round(s / step!) * step!
    let i = ser.length - 1
    while (i >= 0 && num(ser[i]?.spot) != null && near(ser[i].spot) === atm) i--
    if (i < ser.length - 1) {
      const prevSpot = i >= 0 ? num(ser[i]?.spot) : null
      since = { ts: String(ser[i + 1].ts ?? '').slice(0, 5), prev: prevSpot != null ? near(prevSpot) : null,
                atStart: prevSpot == null }
    }
  }
  return { why: null, atm, spot: num(j.spot), ts: String(j.ts ?? ''), strikes, step, since }
}

interface LegState {
  strike: number; why: string | null; nothing: string | null
  bars: MBar[]; hidden: number; expiry: string; session: string
  pivots: Piv | null; pivotsWhy: string | null; pivotsDay: string; pivotsSent: boolean
}
function readLeg(r: Awaited<ReturnType<typeof get>>, side: Side, strike: number): LegState {
  const base: LegState = { strike, why: null, nothing: null, bars: [], hidden: 0, expiry: '', session: '',
                           pivots: null, pivotsWhy: null, pivotsDay: '', pivotsSent: false }
  if (r.why) return { ...base, why: r.why }
  const j = r.j
  if (!j?.ok) return { ...base, why: j?.live_error || 'the contract route answered without data' }
  const leg = j.legs?.[side]
  if (!leg) return { ...base, why: `the reply carried no ${side} leg` }
  const out: LegState = { ...base, expiry: String(j.expiry ?? ''), session: String(j.sessions?.slice(-1)[0] ?? ''),
                          pivotsSent: 'pivots' in leg, pivots: readPiv(leg.pivots),
                          pivotsWhy: leg.pivots_why ?? null, pivotsDay: String(leg.pivots_day ?? '') }
  ;(leg.bars ?? []).forEach((b: any, i: number) => {
    if (!b || typeof b.t !== 'string') return
    if (b.t >= END) { out.hidden++; return }
    const x = mbar(b.t, b, leg.vwap?.[i] ?? {}, 'calc')
    if (x) out.bars.push(x)
  })
  if (!out.bars.length) {
    const said = Object.values(leg.gap_reasons ?? {}).join('; ')
    out.nothing = `${side} ${strike} has no session bars for ${out.session || 'this session'}${said ? ` — ${said}` : ''}`
  }
  return out
}

/** One side's contract, polled. A strike change drops the old series at
 *  once, so the pane never shows one strike's bars under another's name. */
function useLeg(index: IndexKey, iv: Iv, side: Side, strike: number | null): LegState | null {
  const [st, setSt] = useState<LegState | null>(null)
  useEffect(() => {
    setSt(null)
    if (strike == null) return
    let alive = true
    const load = async () => {
      const r = await get(`/api/contract?idx=${index}&interval=${iv}&side=${side}&strike=${strike}`)
      if (alive) setSt(readLeg(r, side, strike))
    }
    load()
    const id = setInterval(load, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [index, iv, side, strike])
  return st
}

function useSize<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [s, set] = useState({ w: 0, h: 0 })
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(() => set({ w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, s] as const
}

// ── one pane ──────────────────────────────────────────────────────────────
function niceStep(raw: number) {
  const p = 10 ** Math.floor(Math.log10(raw))
  const f = raw / p
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p
}

interface PaneProps {
  id: string
  bars: MBar[]
  iv: Iv
  pivots: Piv | null
  hover: Hover | null
  onHover: (h: Hover | null) => void
  title: React.ReactNode
  notes: React.ReactNode
  /** Shown instead of the chart when there are no bars — already one of the
   *  three sentences. */
  empty: React.ReactNode | null
  zWhy: string
}

function Pane({ id, bars, iv, pivots, hover, onHover, title, notes, empty, zWhy }: PaneProps) {
  const [box, { w, h }] = useSize<HTMLDivElement>()
  const plotW = Math.max(10, w - GUT)
  const priceH = Math.max(60, h - OI_H - AX_H)
  const x = (m: number) => ((m - S0) / (S1 - S0)) * plotW

  const scale = useMemo(() => {
    let lo = Infinity, hi = -Infinity
    for (const b of bars) {
      lo = Math.min(lo, b.l, b.b.d3 ?? b.l)
      hi = Math.max(hi, b.h, b.b.u3 ?? b.h)
    }
    if (!Number.isFinite(lo)) return null
    const pad = (hi - lo) * 0.04 || 1
    return { lo: lo - pad, hi: hi + pad }
  }, [bars])
  const y = (v: number) => scale ? TOP + ((scale.hi - v) / (scale.hi - scale.lo)) * (priceH - TOP - 4) : 0

  // Everything that does not move with the mouse, built once per data/size.
  const stat = useMemo(() => {
    if (!scale || !w || !h) return { svg: null, off: [] as string[] }
    const px = plotW / (S1 - S0)
    const bw = Math.max(1, iv * px * 0.7)
    const cx = (b: MBar) => x(b.m + iv / 2)
    const gap = (i: number) => i > 0 && bars[i].m - bars[i - 1].m > iv   // a hole stays a hole
    const line = (k: BandKey) => {
      let d = '', pen = false
      bars.forEach((b, i) => {
        const v = b.b[k]
        if (v == null || gap(i)) { pen = false; if (v == null) return }
        d += `${pen ? 'L' : 'M'}${cx(b).toFixed(1)} ${y(v).toFixed(1)}`
        pen = true
      })
      return d
    }
    // The 2σ->3σ zone, washed like the Trade chart's outer ribbon.
    const zone = (a: BandKey, b2: BandKey) => {
      const runs: MBar[][] = []
      bars.forEach((b, i) => {
        if (b.b[a] == null || b.b[b2] == null) return
        if (!runs.length || gap(i) || runs[runs.length - 1].slice(-1)[0] !== bars[i - 1]) runs.push([])
        runs[runs.length - 1].push(b)
      })
      return runs.map((r) => 'M' + r.map((b) => `${cx(b).toFixed(1)} ${y(b.b[a]!).toFixed(1)}`).join('L')
        + 'L' + [...r].reverse().map((b) => `${cx(b).toFixed(1)} ${y(b.b[b2]!).toFixed(1)}`).join('L') + 'Z').join('')
    }
    const step = niceStep((scale.hi - scale.lo) / 5)
    const ticks: number[] = []
    for (let v = Math.ceil(scale.lo / step) * step; v <= scale.hi; v += step) ticks.push(v)
    const oiv = bars.map((b) => b.oi).filter((v): v is number => v != null)
    const oLo = Math.min(...oiv), oHi = Math.max(...oiv)
    const yo = (v: number) => priceH + 3 + (oHi > oLo ? (oHi - v) / (oHi - oLo) : 0.5) * (OI_H - 6)
    let oiPath = '', pen = false
    bars.forEach((b, i) => {
      if (b.oi == null || gap(i)) { pen = false; if (b.oi == null) return }
      oiPath += `${pen ? 'L' : 'M'}${cx(b).toFixed(1)} ${yo(b.oi).toFixed(1)}`
      pen = true
    })
    const off: string[] = []
    // Lines closer than a label's height share ONE label ("R1 26.0 · P 20.1")
    // rather than printing over each other; every level keeps its own line.
    const on = pivots ? PIV_KEYS.filter((k) => {
      const v = pivots[k]
      if (v >= scale.lo && v <= scale.hi) return true
      off.push(`${k} ${v.toFixed(2)}`)
      return false
    }) : []
    const labels: { y: number; text: string }[] = []
    for (const k of on) {                          // PIV_KEYS runs top to bottom
      const yy = y(pivots![k]), ly = yy < TOP + 12 ? yy + 10 : yy - 2   // under the line at the top edge
      const last = labels[labels.length - 1]
      const text = `${k} ${pivots![k].toFixed(1)}`
      if (last && ly - last.y < 10) last.text += ` · ${text}`
      else labels.push({ y: ly, text })
    }
    const pivEls = pivots ? (
      <g>
        {on.map((k) => <line key={k} x1={0} x2={plotW} y1={y(pivots[k])} y2={y(pivots[k])}
                              stroke={PIV_LINE} strokeWidth={1} strokeDasharray="5 4" />)}
        {labels.map((l) => (
          <text key={l.text} x={4} y={l.y} fontSize={9.5}
                fill={pal.textMuted} fontFamily={MONO} stroke="#fff" strokeWidth={3} paintOrder="stroke">{l.text}</text>
        ))}
      </g>
    ) : null
    const outer = LEG_BAND_LINES.find(([k]) => k === 'u3')![1]
    const svg = (
      <g>
        {TICKS.map((m) => <line key={m} x1={x(m)} x2={x(m)} y1={0} y2={priceH + OI_H} stroke={wash(pal.ink, 0.05)} />)}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={0} x2={plotW} y1={y(v)} y2={y(v)} stroke={wash(pal.ink, 0.05)} />
            <text x={plotW + 5} y={y(v) + 3} fontSize={9.5} fill={pal.textMuted} fontFamily={MONO}>{v.toFixed(step < 1 ? 2 : step < 10 ? 1 : 0)}</text>
          </g>
        ))}
        <path d={zone('u3', 'u2') + zone('d2', 'd3')} fill={wash(outer, 0.08)} stroke="none" />
        {pivEls}
        {LEG_BAND_LINES.map(([k, color]) => (
          <path key={k as string} d={line(k as BandKey)} fill="none" stroke={color}
                strokeWidth={k === 'vwap' ? 1.5 : 1} opacity={k === 'vwap' ? 1 : 0.85} />
        ))}
        {bars.map((b) => {
          const up = b.c >= b.o
          const col = up ? CHART_UP.light : CHART_DOWN.light
          const top = y(Math.max(b.o, b.c)), bot = y(Math.min(b.o, b.c))
          return (
            <g key={b.t}>
              <line x1={cx(b)} x2={cx(b)} y1={y(b.h)} y2={y(b.l)} stroke={col} strokeWidth={1} />
              <rect x={cx(b) - bw / 2} y={top} width={bw} height={Math.max(1, bot - top)} fill={col} />
            </g>
          )
        })}
        <line x1={0} x2={plotW} y1={priceH} y2={priceH} stroke={pal.border} />
        {oiPath && <path d={oiPath} fill="none" stroke={OI_LINE} strokeWidth={1.2} />}
        <text x={plotW + 5} y={priceH + 16} fontSize={9.5} fill={pal.textMuted} fontFamily={MONO}>OI [M]</text>
        <line x1={0} x2={plotW} y1={priceH + OI_H} y2={priceH + OI_H} stroke={pal.border} />
        {TICKS.map((m, i) => (
          <text key={m} x={x(m)} y={priceH + OI_H + 11} fontSize={9.5} fill={pal.textMuted} fontFamily={MONO}
                textAnchor={i === 0 ? 'start' : i === TICKS.length - 1 ? 'end' : 'middle'}>{hhmm(m)}</text>
        ))}
        <line x1={plotW} x2={plotW} y1={0} y2={priceH + OI_H} stroke={pal.border} />
      </g>
    )
    return { svg, off }
  }, [bars, w, h, pivots, iv, scale])

  const at = (m: number) => bars.find((b) => b.m <= m && m < b.m + iv) ?? null
  const hb = hover ? at(hover.m) : null
  const shown = hover ? hb : bars[bars.length - 1] ?? null
  const xl = hover ? (hb ? x(hb.m + iv / 2) : x(hover.m)) : null
  const mine = hover && hover.id === id && scale && hover.y >= TOP && hover.y <= priceH
  const yVal = mine && scale ? scale.hi - ((hover!.y - TOP) / (priceH - TOP - 4)) * (scale.hi - scale.lo) : null

  const move = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const px = Math.max(0, Math.min(plotW - 0.01, e.clientX - r.left))
    onHover({ m: S0 + (px / plotW) * (S1 - S0), id, y: e.clientY - r.top })
  }

  const grid = hover ? S0 + Math.floor((hover.m - S0) / iv) * iv : null
  const readout = !shown
    ? (hover ? `[M] ${hhmm(grid!)} — checked: this contract printed no bar in this bucket` : '')
    : `[M] ${hover ? '' : 'last bar '}${shown.t}  O ${f2(shown.o)} H ${f2(shown.h)} L ${f2(shown.l)} C ${f2(shown.c)}`
      + `  VWAP ${f2(shown.b.vwap)}  z ${sgn(shown.z)}  OI ${shown.oi == null ? '—' : lakh(shown.oi)}`

  return (
    <div style={{
      height: '100%', display: 'flex', flexDirection: 'column', minWidth: 0,
      border: `1px solid ${pal.border}`, borderRadius: 6, background: pal.card, overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '2px 10px', padding: '4px 8px 2px', fontSize: 10.5, color: pal.textMuted }}>
        <span style={{ fontWeight: 700, letterSpacing: '0.04em', color: pal.textPrimary, whiteSpace: 'nowrap' }}>{title}</span>
        {notes}
        {stat.off.length > 0 && <span>not showing you: {stat.off.join(', ')} — off this chart's price scale</span>}
      </div>
      <div ref={box} style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        {empty ? (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        padding: 12, fontSize: 11.5, color: pal.textMuted, textAlign: 'center' }}>{empty}</div>
        ) : (
          <>
            <svg width={w} height={h} style={{ display: 'block', cursor: 'crosshair' }}
                 onMouseMove={move} onMouseLeave={() => onHover(null)}>
              {stat.svg}
              {xl != null && <line x1={xl} x2={xl} y1={0} y2={priceH + OI_H} stroke={pal.textSecondary} strokeDasharray="3 3" />}
              {mine && yVal != null && (
                <g>
                  <line x1={0} x2={plotW} y1={hover!.y} y2={hover!.y} stroke={pal.textSecondary} strokeDasharray="3 3" />
                  <rect x={plotW + 1} y={hover!.y - 7} width={GUT - 2} height={14} fill={pal.textPrimary} />
                  <text x={plotW + 5} y={hover!.y + 3} fontSize={9.5} fill="#fff" fontFamily={MONO}>{yVal.toFixed(2)}</text>
                </g>
              )}
              {hb && scale && <circle cx={x(hb.m + iv / 2)} cy={y(hb.c)} r={2.5} fill={pal.textPrimary} />}
            </svg>
            <div title={zWhy} style={{
              position: 'absolute', top: 1, left: 6, right: GUT, fontSize: 10.5, fontFamily: MONO,
              color: pal.textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              pointerEvents: 'none', textShadow: '0 0 3px #fff, 0 0 3px #fff',
            }}>{readout}</div>
          </>
        )}
      </div>
    </div>
  )
}

// ── the tab ───────────────────────────────────────────────────────────────
function readIv(): Iv {
  try { return localStorage.getItem(IV_KEY) === '3' ? 3 : 5 } catch { return 5 }
}

const couldNot = (why: string) => <span style={{ color: pal.caution }}>could not check — {why}</span>

function pivNote(l: LegState): React.ReactNode {
  if (!l.pivotsSent) return couldNot('this server build sends no per-leg pivots (it needs the restart that ships them)')
  if (l.pivots) return <span>pivots [M] this contract's own prior session {l.pivotsDay}</span>
  if (l.pivotsWhy?.startsWith('no prior session'))
    return <span>pivots: checked — {l.pivotsWhy}</span>
  return couldNot(`pivots: ${l.pivotsWhy ?? 'no reason given'}`)
}

export default function MirrorTab({ index }: { index: IndexKey }) {
  // 5, not the engine's 3: this screen is read next to her GoCharting futures
  // chart, which is 5-minute, so the two must print the same candles. 3 is one
  // click away and remembered.
  const [iv, setIvState] = useState<Iv>(readIv)
  const setIv = (n: Iv) => { try { localStorage.setItem(IV_KEY, String(n)) } catch { /* private mode */ } setIvState(n) }
  const [pins, setPins] = useState<Record<Side, number | null>>({ CE: null, PE: null })
  const [fut, setFut] = useState<FutState | null>(null)
  const [chain, setChain] = useState<ChainState | null>(null)
  const [hover, setHover] = useState<Hover | null>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      const [d, c] = await Promise.all([get(`/api/data?idx=${index}&interval=${iv}`), get(`/api/chain?idx=${index}`)])
      if (!alive) return
      setFut(readFut(d))
      setChain(readChain(c))
    }
    load()
    const id = setInterval(load, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [index, iv])

  // ATM · following = the chain's ATM (index spot's nearest strike). With no
  // chain, the engine's own tracked strike, said so on screen.
  const atm = chain?.atm ?? null
  const follow = atm ?? fut?.engineStrike ?? null
  const want: Record<Side, number | null> = { CE: pins.CE ?? follow, PE: pins.PE ?? follow }
  const legs: Record<Side, LegState | null> = {
    CE: useLeg(index, iv, 'CE', want.CE),
    PE: useLeg(index, iv, 'PE', want.PE),
  }

  // The tab fills the screen below the app's chrome; the page scrolls if tiny.
  const outer = useRef<HTMLDivElement>(null)
  const [H, setH] = useState(580)
  useLayoutEffect(() => {
    const fit = () => {
      const el = outer.current
      if (!el) return
      const top = el.getBoundingClientRect().top + window.scrollY
      setH(Math.max(540, Math.min(1000, window.innerHeight - top - 4)))
    }
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [fut])

  // ±8 strikes around ATM on the chain's own strike step. The chain's list is
  // centred where the poller last re-centred, so it can run 4 below ATM and
  // 12 above; the step is what it reliably tells us. A strike the exchange
  // does not list answers "could not check" from /api/contract, in its words.
  // A pinned strike stays offered after ATM walks away from it.
  const chips = useMemo(() => {
    const st = chain?.step
    const win = atm != null && st ? Array.from({ length: 17 }, (_, j) => atm + (j - 8) * st) : []
    const extra = [pins.CE, pins.PE, follow].filter((k): k is number => k != null && !win.includes(k))
    return [...win, ...extra].sort((a, b) => a - b)
  }, [chain, atm, pins, follow])

  const now = istNow()
  const closed = now.wd === 0 || now.wd === 6 || now.hm >= S1 || now.hm < S0

  const chip = (on: boolean, dashed = false): React.CSSProperties => ({
    fontSize: 10.5, padding: '2px 7px', borderRadius: 3, cursor: 'pointer', fontFamily: MONO,
    background: on && !dashed ? wash(pal.accent, 0.12) : 'transparent',
    border: `1px ${dashed ? 'dashed' : 'solid'} ${on ? wash(pal.accent, 0.6) : pal.border}`,
    color: on ? pal.accent : pal.textMuted,
  })

  const row = (side: Side) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
      <span style={{ width: 22, fontSize: 10.5, fontWeight: 700, color: pal.textSecondary }}>{side}</span>
      <button onClick={() => setPins((p) => ({ ...p, [side]: null }))} style={chip(pins[side] == null)}
              title="Follow the ATM strike: the pane switches contract when the ATM moves">ATM · following</button>
      {chips.map((k) => {
        const pinned = pins[side] === k
        const followed = pins[side] == null && want[side] === k
        return (
          <button key={k} onClick={() => setPins((p) => ({ ...p, [side]: p[side] === k ? null : k }))}
                  style={{ ...chip(pinned || followed, followed), fontWeight: k === atm ? 700 : 400 }}
                  title={pinned ? 'pinned — click again to follow ATM' : k === atm ? 'the ATM strike now' : `pin ${side} ${k}`}>
            {k}{k === atm ? ' ·ATM' : ''}
          </button>
        )
      })}
    </div>
  )

  const since = chain?.since
  const atmLine = !chain || chain.why || atm == null
    ? couldNot(`the chain ATM (${chain?.why ?? 'no reply yet'})${fut?.engineStrike != null
        ? `; following the engine's tracked strike ${fut.engineStrike} instead` : ''}`)
    : <span>
        ATM <b style={{ color: pal.textPrimary }}>{atm}</b> [M] · index {f2(chain.spot)} at {chain.ts}
        {since ? (since.atStart
          ? ` · nearest strike since at least ${since.ts} (the chain's spot record starts there)`
          : ` · nearest strike since ${since.ts}${since.prev != null ? ` (was ${since.prev})` : ''}`) : ''}
      </span>

  const legPane = (side: Side) => {
    const l = legs[side]
    const k = want[side]
    const pinned = pins[side] != null
    const title = l ? `${side} ${l.strike}${l.expiry ? ` · exp ${l.expiry}` : ''}` : `${side} ${k ?? '—'}`
    const mode = pinned ? 'pinned' : `ATM · following${since && k === atm && !since.atStart ? ` since ${since.ts}` : ''}`
    const empty = k == null ? couldNot('no strike to chart: neither the chain ATM nor the engine strike is known yet')
      : !l ? <span>loading {side} {k}…</span>
      : l.why ? couldNot(l.why)
      : l.nothing ? <span>checked — {l.nothing}</span> : null
    return (
      <Pane id={side} bars={l?.bars ?? []} iv={iv} pivots={l?.pivots ?? null} hover={hover} onHover={setHover}
            empty={empty}
            zWhy="z [M] = (close − VWAP) / (u1 − VWAP): the engine's formula, from this contract's own measured close and bands"
            title={<>{title} <span style={{ fontWeight: 500, color: pinned ? pal.accent : pal.textSecondary }}>· {mode}</span></>}
            notes={l && !l.why && !l.nothing ? <>
              <span>own series from {l.bars[0]?.t ?? '—'}, never joined to another strike</span>
              {pivNote(l)}
              {l.hidden > 0 && <span>not showing you: {l.hidden} bar{l.hidden === 1 ? '' : 's'} stamped 15:30+ (after the close)</span>}
            </> : null} />
    )
  }

  return (
    <div ref={outer} style={{ height: H, display: 'flex', flexDirection: 'column', gap: 5, padding: '6px 16px 4px', background: pal.bg }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', fontSize: 11, color: pal.textMuted }}>
        <span className="micro-label" style={{ color: pal.textSecondary }}>Mirror — {index}</span>
        <span style={{ display: 'inline-flex', gap: 3 }}>
          {([3, 5] as Iv[]).map((n) => (
            <button key={n} onClick={() => setIv(n)} style={chip(iv === n)}>{n} min</button>
          ))}
        </span>
        <button onClick={() => setPins({ CE: null, PE: null })} disabled={pins.CE == null && pins.PE == null}
                style={{ ...chip(false), fontWeight: 700, letterSpacing: '0.08em', fontFamily: 'inherit',
                         opacity: pins.CE == null && pins.PE == null ? 0.45 : 1 }}>FOLLOW ATM</button>
        {atmLine}
        {closed && <span>· market closed — the session's last snapshot</span>}
      </div>
      {row('CE')}
      {row('PE')}
      <div style={{ flex: '0.42 1 0', minHeight: 0 }}>
        <Pane id="FUT" bars={fut?.bars ?? []} iv={iv} pivots={fut?.pivots ?? null} hover={hover} onHover={setHover}
              zWhy="z [M] is the engine's own per-bar value for the future"
              empty={!fut ? <span>loading FUT…</span> : fut.why ? couldNot(fut.why)
                : !fut.bars.length ? <span>checked — the engine has no futures bars for this session yet</span> : null}
              title={`FUT · ${index}${fut?.label ? ` · ${fut.label}` : ''}`}
              notes={fut && !fut.why ? <>
                {fut.pivots ? <span>pivots [M] prior session floor pivots</span>
                  : couldNot('the server published no FUT pivots for this session')}
                {fut.hidden > 0 && <span>not showing you: {fut.hidden} bar{fut.hidden === 1 ? '' : 's'} stamped 15:30+ (after the close)</span>}
              </> : null} />
      </div>
      <div style={{ flex: '0.58 1 0', minHeight: 0, display: 'flex', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>{legPane('CE')}</div>
        <div style={{ flex: 1, minWidth: 0 }}>{legPane('PE')}</div>
      </div>
    </div>
  )
}
