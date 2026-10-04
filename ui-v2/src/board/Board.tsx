import { useEffect, useMemo, useState } from 'react'
import type { IndexKey } from '../data'
import { usePalette, rgbOf } from '../theme'
import type { Palette } from '../theme'

/* ── THE BOARD — overhaul 2026-10-03 (docs/board/BOARD-OVERHAUL-2026-10-03.md) ──
   ONE JOB, in one look: which side's near-money writers stopped first and are
   giving OI back (her §1d rule: that side is forced, that is the fuel), and the
   next reaction point each way. Her chess board: each piece's day (what has
   happened), its state now (what is happening), the next level and who stands
   between price and it (what can happen).

     /api/board    the four §1d fronts with the server's [M] extras (open, peak
                   time, first UNWINDING mark, spot at the peak, ITM/OTM, built
                   today vs carried) and the day's first leaver
     /api/oihist   the per-strike minute grid: each front's OI since the open
     /api/warmap   PDH/PDL/PWH/PWL and the major round numbers
     /api/sides    TEENO and the sides grid (round 4, rev sides-2): sides.py's read
                   of the call side and the put side on her nine strikes against the
                   index move, per closed 5-min slot, for all three indices, and the
                   two lines (Fable §6). RENDER ONLY: every word, flag and count arrives
                   from the server; no rule is copied here
     /api/trap     the trap layer, SHADOW (round 5, rev trap-1): trap.py's three lines
                   (TRAP / CHHOOTA / AGLA) for this index, collapsed by default; render
                   only, it changes no verdict, word or count on this screen

   The verdict is display [I] on §1d's own states, nothing new: `fronts.broke`
   restricted to fronts that built today (board.py's 0j.2 rule). It gates
   nothing. Her rules: LIGHT; no price chart (OI sparklines only); every glyph
   carries a Hinglish chip with its number; a count, never odds; never the word
   FOLD for writers leaving; three absences, never one. */

type Side = 'CE' | 'PE'
type State = 'BUILDING' | 'STALLED' | 'UNWINDING'
type Front = {
  k: number; side: Side; chg: number; peak: number; peak_at: string; state: State
  open: number | null; now_oi: number | null; share: number | null
  built: 'today' | 'carried' | 'never' | null; itm: [string, number]
  peak_spot: number | null; unwind_at: string | null
}
type First = { k: number; side: Side; t: string; high_at: string; spot_high?: number }
type BoardDoc = {
  ok: boolean; why?: string; idx?: string; asof?: string | null; spot?: number; step?: number
  headline?: { text?: string }
  fronts?: Front[] | null; fronts_why?: string | null
  first?: First | null; first_why?: string | null
  grid?: { from: string | null; to: string | null; marks: number; holes: string[]; whole: boolean }
  not_shown?: Record<string, string>
}
type OiHist = { ok: boolean; why?: string | null; minutes?: Record<string, { spot?: number | null; k?: Record<string, unknown> } | null> }
type Level = { kind: string; px: number; major?: boolean }
type WarMap = {
  ok: boolean; why?: string | null
  indices?: Record<string, { ok?: boolean; why?: string | null; levels?: Level[] | null; daily_why?: string | null }>
}
type Poll<T> = { data: T | null; why: string | null }
type SideCell = {
  st: 'ADD' | 'COV' | 'FLAT' | null; x: number | null; x_why: string | null; power: boolean; d: number
  top2: number[]; agree: number; n: number; of: number; run: number
}
type Slot = {
  t: string; from: string; src: 'live' | 'backfill'; ce: SideCell | null; pe: SideCell | null
  move: { st: string | null; d: number | null } | null; word: string | null; dir: number | null
  power: boolean; pdir: number | null; first: boolean; why: string[]; M_basis?: string
  fuel_top2_underwater?: number | null; fuel_dIV_med?: number | null; forced_why?: string | null
}
type SidesIdx = {
  ok: boolean; why?: string | null; day?: string; expiry?: string | null; dte?: number | null; expiry_day?: boolean
  chain_ok?: boolean; chain_why?: string | null; kal?: { day?: string } | null; kal_why?: string | null; slots?: Slot[]
}
type Three = {
  t: string | null; line1: string; line1_weekly: string | null; line2: string | null; line2_weekly: string | null
  dir: number | null; dir_three: number | null; dir_weekly: number | null
  n_power?: number; n_weekly_power?: number; missing: Record<string, string>; tags: string[]
}
type Sides = { ok: boolean; why?: string; now?: string; indices?: Record<string, SidesIdx>; three?: Three | null }
type TrapIdx = {
  ok: boolean; why?: string | null; lines?: { trap: string; chhoota: string | null; agla: string | null; t?: string }
  stamps_why?: string | null; who_why?: string | null; xindex_why?: string | null; tape_why?: string | null; oi_prev_why?: string | null
}
type Trap = { ok: boolean; why?: string; rev?: string; fixed_at?: string; indices?: Record<string, TrapIdx | undefined> }
type Row = { t: string; m: number; spot: number | null; k: Map<number, [number | null, number | null]> }
type Lv = { px: number; name: string }

// The Board's side hues, coral calls / teal puts (UI review 2026-10-03 §7). Hue = side only;
// green/red stay direction (theme.ts), state is words + geometry.
const CE_HUE = '#C4452C', PE_HUE = '#0B8277'
const OPEN_M = 9 * 60 + 15, SPAN = 375                 // 09:15 → 15:30
const CC = 'could not check — '
const SLOPE_MARKS = 15     // fronts.SLOPE_MARKS: the sequence needs this many one-minute marks
const UNDER = 0.05         // board.paying: BUILDING but ≥ 5 % under its own peak is "adding again", never "still adding"
const MERGE = 4, CLEAR = 3 // board.SQ_MERGE / SQ_CLEAR: levels this close are one; a level must clear spot by this
const STATIC = new Set(['PDH', 'PDL', 'PWH', 'PWL'])   // her reaction points; OPEN/PDC are not on her list
const IDX: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']
const SHOW = 6             // slots drawn per index (30 min): display length only, it decides nothing
// Which count TEENO shows. Mary's decision, 2026-10-04: the weekly books NIFTY + SENSEX (0/1/2), with
// BANKNIFTY a tagged witness, shown and never counted. sides.py sends both models; this is the one switch.
const COUNT_MODEL = 'weekly' as 'three' | 'weekly'

const ok = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x)
const mm = (t: string) => +t.slice(0, 2) * 60 + +t.slice(3, 5)
const f0 = (x: number) => Math.round(x).toLocaleString('en-IN')
const f1 = (x: number) => x.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
/** OI in lakh, one unit everywhere (2 decimals under a lakh, for BANKNIFTY), signed when asked. */
const oiL = (x: number, signed = false) => {
  if (x === 0) return '0'
  const a = Math.abs(x), s = x < 0 ? '−' : signed && x > 0 ? '+' : ''
  return s + (a / 1e5).toFixed(a >= 1e7 ? 0 : a >= 1e5 ? 1 : 2) + 'L'
}
const hue = (s: Side) => (s === 'CE' ? CE_HUE : PE_HUE)
const who = (s: Side) => (s === 'CE' ? 'CALL' : 'PUT')
const noCC = (s?: string | null) => String(s ?? '').replace(/^could not check — /, '')
const wash = (hex: string, a: number) => `rgba(${rgbOf(hex)},${a})`
const pair = (v: unknown): [number | null, number | null] =>
  Array.isArray(v) ? [ok(v[0]) ? v[0] : null, ok(v[1]) ? v[1] : null] : [null, null]
const xPct = (m: number) => `${(Math.max(0, Math.min(SPAN, m - OPEN_M)) / SPAN) * 100}%`
const atPeak = (f: Front) => f.state === 'BUILDING' && f.peak - f.chg < UNDER * f.peak
/** Points price moved AGAINST (+) or FOR (−) this front's writers since its peak [M]. */
const against = (f: Front, spot: number) => (f.peak_spot == null ? null : f.side === 'CE' ? spot - f.peak_spot : f.peak_spot - spot)

function usePoll<T>(url: string, ms: number): { data: T | null; why: string | null } {
  const [st, setSt] = useState<{ data: T | null; why: string | null }>({ data: null, why: 'reading…' })
  useEffect(() => {
    let alive = true, retry = 0
    const load = async () => {
      window.clearTimeout(retry)
      try {
        const r = await fetch(url)
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const j = (await r.json()) as T
        if (alive) setSt({ data: j, why: null })
      } catch (e) {
        // keep the last read on screen, SAY it is the last read, and try again soon
        if (alive) { setSt((p) => ({ data: p.data, why: `the backend did not answer (${String(e)})` })); retry = window.setTimeout(load, 3000) }
      }
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, ms)
    return () => { alive = false; window.clearInterval(id); window.clearTimeout(retry) }
  }, [url, ms])
  return st
}

/* ── the words ─────────────────────────────────────────────────────────────── */
/** A front's state now: Hinglish word, the English time phrase, and the short plural for the count. */
function stateOf(f: Front): { hi: string; en: string; one: string; many: string } {
  if (f.peak <= 0) return { hi: 'AAJ NAHI BANA', en: 'carried in only', one: 'aaj nahi bana', many: 'aaj nahi bane' }
  if (f.state === 'BUILDING') return atPeak(f)
    ? { hi: 'LIKH RAHE', en: 'at its high', one: 'likh raha', many: 'likh rahe' }
    : { hi: 'PHIR LIKH RAHE', en: `${oiL(f.peak - f.chg)} under its ${f.peak_at} high`, one: 'phir likh raha', many: 'phir likh rahe' }
  if (f.state === 'STALLED') return { hi: 'RUK GAYE', en: `stopped at ${f.peak_at}`, one: 'ruka', many: 'ruke' }
  return { hi: 'CHHOD RAHE', en: `since ${f.unwind_at ?? f.peak_at}`, one: 'chhod raha', many: 'chhod rahe' }
}

function countOf(fr: Front[], side: Side): string {
  const n = new Map<string, { c: number; many: string }>()
  for (const f of fr.filter((x) => x.side === side)) {
    const s = stateOf(f), x = n.get(s.one)
    n.set(s.one, { c: (x?.c ?? 0) + 1, many: s.many })
  }
  return [...n].map(([one, { c, many }]) => `${c} ${c > 1 ? many : one}`).join(' · ') || 'no front read'
}

type Read = { word: string; chip: { text: string; dir: 1 | -1 | 0 } | null; lead: Front | null; then: Front | null }
/** `fronts.broke` over the fronts that BUILT today: the earliest-peaked UNWINDING one, else the
 *  earliest-peaked STALLED one. Her rule: the side that stops first and then gives back is forced.
 *  When BOTH sides are at the same step, the chip names both stamps in order and no direction:
 *  that is the end of a leg (1 Oct 15:29: puts broke 10:41, then calls were squeezed from 13:58),
 *  and a one-way fuel arrow there would point at the spent side. Whether the newer side should
 *  lead is her call (docs/board note, open question 2). */
function readOf(fr: Front[]): Read {
  const built = fr.filter((f) => f.peak > 0)
  if (!built.length) return { word: 'AAJ KOI FRONT NAHI BANA', chip: null, lead: null, then: null }
  const early = (a: Front, z: Front) => (a.peak_at < z.peak_at ? -1 : a.peak_at > z.peak_at ? 1 : 0)
  const unw = built.filter((f) => f.state === 'UNWINDING').sort(early)
  const stl = built.filter((f) => f.state === 'STALLED').sort(early)
  const lead = unw[0] ?? stl[0]
  if (!lead) return { word: 'DONO TARAF LIKH RAHE HAIN', chip: { text: 'koi nahi toota', dir: 0 }, lead: null, then: null }
  const way = lead.side === 'PE' ? 'neeche' : 'upar'
  const step = lead.state === 'UNWINDING' ? unw : stl
  const then = step.find((f) => f.side !== lead.side) ?? null
  const both = then ? { text: `pehle ${who(lead.side)} ${lead.peak_at} · phir ${who(then.side)} ${then.peak_at}`, dir: 0 as const } : null
  if (lead.state === 'UNWINDING') return {
    word: then ? 'DONO TARAF CHHOD RAHE' : `${who(lead.side)} WRITERS CHHOD RAHE HAIN`,
    chip: both ?? { text: `${lead.side === 'PE' ? '▼' : '▲'} fuel ${way} · ${lead.peak_at}`, dir: lead.side === 'PE' ? -1 : 1 }, lead, then,
  }
  return {
    word: then ? 'DONO TARAF RUK GAYE' : `${who(lead.side)} WRITERS RUK GAYE`,
    chip: both ?? { text: `dekho · wapas dein to fuel ${way}`, dir: 0 }, lead, then,
  }
}

/** One side's step, short, for the both-sides line. */
function stepOf(f: Front, spot: number): string {
  const a = against(f, spot)
  return `${f.side} ${f0(f.k)} stopped ${f.peak_at}` + (f.state === 'UNWINDING' ? `, giving back since ${f.unwind_at ?? f.peak_at}` : '')
    + (a == null ? '' : `, price ${f0(Math.abs(a))} ${a >= 0 ? 'against' : 'in their favour'}`)
}

function factOf(f: Front, spot: number): string {
  const a = against(f, spot)
  return `${f.side} ${f0(f.k)} stopped adding at ${f.peak_at}`
    + (f.state === 'UNWINDING' ? `, giving back since ${f.unwind_at ?? f.peak_at}` : ', not giving back yet')
    + ` · ${oiL(f.peak, true)} → ${oiL(f.chg, true)}`
    + (a == null ? ' · price since: could not check' : ` · price ${f0(Math.abs(a))} pts ${a >= 0 ? 'against them' : 'in their favour'} since then`)
}

type Ev = { t: string; side: Side; k: number; hi: string; en: string; first?: boolean }
/** KRAM: the four pieces' stamps, newest first, plus the day's first leaver (stamped once). */
function kramOf(fr: Front[], first: First | null | undefined): Ev[] {
  const out: Ev[] = []
  for (const f of fr) {
    if (f.peak <= 0 || atPeak(f)) continue
    out.push({ t: f.peak_at, side: f.side, k: f.k, hi: 'ruka', en: `stopped adding: its high, ${oiL(f.peak, true)} since the open [M]` })
    if (f.unwind_at) out.push({ t: f.unwind_at, side: f.side, k: f.k, hi: 'chhodne lage', en: 'began giving back (§1d UNWINDING) [M]' })
  }
  if (first) {
    const en = `the day's first top-2 front to give back, stamped once; its high was at ${first.high_at}${ok(first.spot_high) ? ` @ ${f1(first.spot_high)}` : ''} [M]`
    const dup = out.find((e) => e.t === first.t && e.side === first.side && e.k === first.k)
    if (dup) Object.assign(dup, { hi: 'aaj sabse pehle chhoda', en, first: true })
    else out.push({ t: first.t, side: first.side, k: first.k, hi: 'aaj sabse pehle chhoda', en, first: true })
  }
  return out.sort((a, z) => (a.t < z.t ? 1 : a.t > z.t ? -1 : 0))
}

/* ── the component ─────────────────────────────────────────────────────────── */
export default function Board({ index }: { index: IndexKey }) {
  const pal = usePalette()
  const bd = usePoll<BoardDoc>(`/api/board?idx=${index}`, 20000)
  const sd = usePoll<Sides>('/api/sides', 20000)          // all three indices and their count, one request
  const [sidesFull, setSidesFull] = useState<boolean>(loadSidesFull)
  const toggleSides = () => setSidesFull((v) => { saveSidesFull(!v); return !v })
  const readCols = { gridTemplateColumns: sidesFull ? 'minmax(0,1fr) 494px' : 'minmax(0,1fr) auto' }
  const tp = usePoll<Trap>(`/api/trap?idx=${index}`, 20000)
  const [trapOpen, setTrapOpen] = useState<boolean>(loadTrapOpen)
  const toggleTrap = () => setTrapOpen((v) => { saveTrapOpen(!v); return !v })
  const oh =usePoll<OiHist>(`/api/oihist?idx=${index}`, 30000)
  const wm = usePoll<WarMap>(`/api/warmap?idx=${index}`, 60000)
  const b = bd.data && bd.data.idx === index ? bd.data : null
  const spot = b?.ok && ok(b.spot) ? b.spot : null
  const fr = b?.ok ? b.fronts ?? [] : []

  /* the minute grid, cut to the board's own minute so the lines and the words agree */
  const grid = useMemo((): Row[] | null => {
    const d = oh.data
    if (!d?.ok || !d.minutes) return null
    const asof = b?.asof ?? null
    const rows: Row[] = []
    for (const [t, r] of Object.entries(d.minutes)) {
      if (!/^\d\d:\d\d$/.test(t) || !r?.k || mm(t) < OPEN_M || mm(t) >= OPEN_M + SPAN || (asof && t > asof)) continue
      const k = new Map<number, [number | null, number | null]>()
      for (const [ks, v] of Object.entries(r.k)) { const n = Number(ks); if (ok(n)) k.set(n, pair(v)) }
      rows.push({ t, m: mm(t), spot: ok(r.spot) ? r.spot : null, k })
    }
    rows.sort((a, z) => a.m - z.m)
    return rows.length ? rows : null
  }, [oh.data, b?.asof])

  /* the next reaction points: her levels + major rounds + the day's high / low */
  const lv = useMemo((): { up: Lv[]; dn: Lv[]; why: string | null; note: string | null } => {
    if (spot == null) return { up: [], dn: [], why: null, note: null }
    const w = wm.data, x = w?.indices?.[index]
    const cand: Lv[] = []
    let why: string | null = null, note: string | null = null
    if (!w) why = CC + (wm.why ?? 'no war map read yet')
    else if (!x || x.ok === false) why = CC + (x?.why ?? w.why ?? `the war map has no ${index} board yet`)
    else {
      for (const l of x.levels ?? []) {
        if (!ok(l.px)) continue
        if (STATIC.has(l.kind)) cand.push({ px: l.px, name: l.kind })
        else if (l.kind === 'ROUND' && l.major) cand.push({ px: l.px, name: 'round' })
      }
      if (x.daily_why) note = `PDH/PDL/PWH/PWL: ${CC}${x.daily_why}`
    }
    if (grid) {
      let hi: Row | null = null, lo: Row | null = null
      for (const r of grid) if (r.spot != null) {
        if (!hi || r.spot > hi.spot!) hi = r
        if (!lo || r.spot < lo.spot!) lo = r
      }
      if (hi) cand.push({ px: hi.spot!, name: `din ka high ${hi.t}` })
      if (lo) cand.push({ px: lo.spot!, name: `din ka low ${lo.t}` })
    }
    const merged: Lv[] = []
    for (const c of cand.sort((a, z) => a.px - z.px)) {
      const last = merged[merged.length - 1]
      if (last && c.px - last.px <= MERGE) { if (!last.name.includes(c.name)) last.name += ' · ' + c.name }
      else merged.push({ ...c })
    }
    return {
      up: merged.filter((l) => l.px > spot + CLEAR).slice(0, 2),
      dn: merged.filter((l) => l.px < spot - CLEAR).reverse().slice(0, 2),
      why, note,
    }
  }, [wm.data, wm.why, grid, spot, index])

  const css = CSS(pal)
  if (!b || !b.ok || spot == null) {
    return (
      <div className="nb"><style>{css}</style>
        <div className="card read" style={{ display: 'block' }}>
          <div className="verdict" style={{ color: pal.caution }}>BOARD PADHA NAHI JA SAKA</div>
          <div className="fact" style={{ color: pal.caution }}>
            {b ? (b.why?.startsWith('could not') ? b.why : CC + (b.why ?? 'no board read')) : bd.why ? CC + noCC(bd.why) : 'reading the board…'}
          </div>
          <div className="fact">
            Ye shaant market nahi hai — padhne ko data hi nahi hai.{' '}
            {b ? 'Jab grid par session ka pehla poora minute aayega, board wahi se padhega.' : 'Backend se jawab nahi aaya; board har kuch second mein dobara pooch raha hai.'}
          </div>
        </div>
        <div className="card read" style={readCols}><div><TeenoLine sd={sd} pal={pal} vdir={0} /><TrapBlock tp={tp} index={index} pal={pal} open={trapOpen} onToggle={toggleTrap} /></div><SidesGrid sd={sd} pal={pal} full={sidesFull} onToggle={toggleSides} /></div>
        <Foot b={b} index={index} why={bd.why} pal={pal} />
      </div>
    )
  }

  const forming = (b.grid?.marks ?? 0) < SLOPE_MARKS
  const rd = readOf(fr)
  const chipTone = (d: 1 | -1 | 0) => (d > 0 ? pal.bull : d < 0 ? pal.bear : pal.textSecondary)

  /* the board's rows, in price order: levels, the four pieces, the spot line */
  type Item = { px: number; o: number; kind: 'lv' | 'f' | 'spot'; lv?: Lv; f?: Front; tag?: string }
  const items: Item[] = [
    ...lv.up.map((l, i) => ({ px: l.px, o: 0, kind: 'lv' as const, lv: l, tag: i === 0 ? 'Agli ladai upar' : 'phir' })),
    ...lv.dn.map((l, i) => ({ px: l.px, o: 0, kind: 'lv' as const, lv: l, tag: i === 0 ? 'Agli ladai neeche' : 'phir' })),
    ...fr.map((f) => ({ px: f.k, o: f.side === 'CE' ? 1 : 2, kind: 'f' as const, f })),
    { px: spot, o: 3, kind: 'spot' as const },
  ].sort((a, z) => z.px - a.px || a.o - z.o)

  /* one shared OI scale across the four lines, so sizes compare */
  const series = (f: Front) => (grid ?? []).map((r) => ({ m: r.m, v: r.k.get(f.k)?.[f.side === 'CE' ? 0 : 1] ?? null }))
  let top = 0, bot = 0
  for (const f of fr) for (const p of series(f)) if (p.v != null) { top = Math.max(top, p.v); bot = Math.min(bot, p.v) }
  const asofM = b.asof ? mm(b.asof) : null
  const kram = kramOf(fr, b.first)

  const lvChip = (l: Lv | undefined, up: boolean) => {
    const name = up ? 'Agli ladai upar' : 'Agli ladai neeche'
    if (lv.why) return <div className="lvchip" style={{ color: pal.caution, borderColor: wash(pal.caution, 0.4) }} title={lv.why}>{up ? '▲' : '▼'} {name} · {CC}levels</div>
    if (!l) return <div className="lvchip muted">{up ? '▲' : '▼'} {name} · checked, none within the war map's window</div>
    const d = l.px - spot
    return (
      <div className="lvchip" title={`${l.name} ${f1(l.px)}, ${d > 0 ? '+' : '−'}${f1(Math.abs(d))} from the index [M]`}>
        <span style={{ color: up ? pal.bull : pal.bear }}>{up ? '▲' : '▼'}</span> {name} · <b className="mono">{f0(l.px)}</b> {l.name} · <span className="mono">{d > 0 ? '+' : '−'}{f0(Math.abs(d))}</span>
      </div>
    )
  }

  return (
    <div className="nb"><style>{css}</style>
      {/* 1–4 · THE READ */}
      <div className="card read" style={readCols}>
        <div style={{ minWidth: 0 }}>
          {forming ? <>
            <div className="verdict">FRONTS BAN RAHE HAIN <span className="cp">{b.grid?.marks ?? 0} of {SLOPE_MARKS} minute</span></div>
            <div className="fact">{b.headline?.text ?? `the build → stall → unwind sequence needs ${SLOPE_MARKS} one-minute marks`} <span className="tag">[M]</span></div>
          </> : !b.fronts?.length ? <>
            <div className="verdict" style={{ color: pal.caution }}>FRONTS PADHE NAHI JA SAKE</div>
            <div className="fact" style={{ color: pal.caution }}>{CC + noCC(b.fronts_why ?? 'no fronts in the payload')}</div>
          </> : <>
            <div className="verdict">
              <span>{rd.word}</span>
              {rd.chip && <span className="cp big" style={{ color: chipTone(rd.chip.dir), borderColor: wash(chipTone(rd.chip.dir), 0.45), background: wash(chipTone(rd.chip.dir), 0.07) }}>{rd.chip.text}</span>}
              <span className="tag">[I]</span>
            </div>
            <div className="fact">
              {rd.lead ? <>{rd.then ? `pehle ${who(rd.lead.side)}: ${stepOf(rd.lead, spot)} · phir ${who(rd.then.side)}: ${stepOf(rd.then, spot)}` : factOf(rd.lead, spot)} <span className="tag">[M]</span></>
                : rd.word.startsWith('DONO TARAF LIKH') ? 'All four fronts are still adding — nobody has stopped yet, so no side is being forced. ' : 'None of the four built today — only carried-in OI. '}
            </div>
            <div className="count">
              <b className="pe">PUT</b> {countOf(fr, 'PE')} <span className="sep">·</span> <b className="ce">CALL</b> {countOf(fr, 'CE')}
              <span className="muted"> — a count of the 4 pieces, not odds</span>
            </div>
          </>}
          <div className="ladai">{lvChip(lv.up[0], true)}{lvChip(lv.dn[0], false)}</div>
          <TeenoLine sd={sd} pal={pal} vdir={!forming && rd.chip ? rd.chip.dir : 0} />
          <TrapBlock tp={tp} index={index} pal={pal} open={trapOpen} onToggle={toggleTrap} />
        </div>
        <SidesGrid sd={sd} pal={pal} full={sidesFull} onToggle={toggleSides} />
      </div>

      <div className="body">
        {/* 5 · THE BOARD — the pieces in price order, each with its day */}
        <div className="card board">
          <div className="bhead">
            <span className="cap">THE BOARD</span> · 9 strikes nearest spot, top 2 by OI per side · line = OI aaj likha,
            {' '}<span className="mono">- - -</span> = subah ka OI · halka = wapas diya
            {grid && <> · <span className="mono">{oiL(top, true)}{bot < 0 ? ` / ${oiL(bot, true)}` : ''}</span></>}
            {!grid && <span style={{ color: pal.caution }}> · OI lines: {CC}{noCC(oh.data && !oh.data.ok ? oh.data.why ?? 'no minute grid' : oh.why ?? 'no minute grid yet')}</span>}
          </div>
          {items.map((it, i) => it.kind === 'spot' ? (
            <div className="row spot" key="spot">
              <div className="mono" style={{ color: pal.accent, fontWeight: 700 }}>bhav {f1(spot)}</div>
              <div className="spotline" />
              <div className="muted s12">index · {b.asof}</div>
            </div>
          ) : it.kind === 'lv' ? (
            <div className="row lv" key={`lv${i}`}>
              <div className="mono" style={{ color: pal.accent, fontWeight: 700 }}>{f0(it.lv!.px)}</div>
              <div className="lvline"><span className="s12 one">{it.lv!.name}</span></div>
              <div className="s12 one"><span style={{ color: pal.accent, fontWeight: 700 }}>{it.tag}</span> <span className="mono t2">{it.lv!.px > spot ? '+' : '−'}{f0(Math.abs(it.lv!.px - spot))}</span></div>
            </div>
          ) : (
            <Piece key={`${it.f!.side}${it.f!.k}`} f={it.f!} spot={spot} pts={series(it.f!)} top={top} bot={bot} asofM={asofM} hasGrid={!!grid} pal={pal} />
          ))}
          {lv.note && <div className="s12" style={{ color: pal.caution, paddingLeft: 4 }}>{lv.note}</div>}
          <div className="row axis">
            <div />
            <div style={{ position: 'relative', height: 14 }}>
              {['09:15', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'].map((t, i) => (
                <span key={t} className="mono tick" style={{ left: xPct(mm(t)), transform: i === 0 ? 'none' : 'translateX(-50%)' }}>{t}</span>
              ))}
            </div>
            <div />
          </div>
        </div>

        {/* 6 · KRAM — plain, in time order, one word per row */}
        <div className="card kram">
          <div className="bhead"><span className="cap">KRAM</span> · kab kya hua, naya upar</div>
          {kram.length ? kram.map((e, i) => (
            <div className="ev" key={i} title={e.en}>
              <span className="mono t2">{e.t}</span>
              <b className="mono" style={{ color: hue(e.side) }}>{e.side} {f0(e.k)}</b>
              <span style={e.first ? { fontWeight: 700 } : undefined}>{e.hi}</span>
            </div>
          )) : <div className="s12 muted">checked, none — no piece has stopped adding yet today{b.first_why && !b.first_why.startsWith('checked') ? ` · ${b.first_why}` : ''}</div>}
        </div>
      </div>

      <Foot b={b} index={index} why={bd.why} pal={pal} />
    </div>
  )
}

/* ── TEENO and the sides grid (round 4, rev sides-2): render only, every word from sides.py ── */
const SIDES_MISSING = CC + 'server not restarted with the sides read yet'
// The SIDES grid opens collapsed: the latest slot plus any POWER / PUSHTI column of the last SHOW. The full grid is
// one click away; the choice is a per-viewer convenience in localStorage, so a blocked store just means collapsed.
const SIDES_FULL_KEY = 'tapemap.board.sidesFull'
function loadSidesFull(): boolean {
  try { return localStorage.getItem(SIDES_FULL_KEY) === '1' } catch { return false }
}
function saveSidesFull(v: boolean) {
  try { localStorage.setItem(SIDES_FULL_KEY, v ? '1' : '0') } catch { /* private window / blocked: stays per-session */ }
}
const SIDE_HI: Record<string, string> = { ADD: 'likh', COV: 'kaat', FLAT: 'flat' }

function sidesWhy(sd: Poll<Sides>): string | null {
  if (sd.data?.ok && sd.data.indices) return null
  if (sd.data && !sd.data.ok) return sd.data.why ?? CC + 'the sides read failed'
  if (sd.why && /HTTP 404/.test(sd.why)) return SIDES_MISSING          // an older server has no /api/sides route
  return sd.why === 'reading…' ? 'reading the sides…' : CC + noCC(sd.why ?? 'no sides read')
}

function TeenoLine({ sd, pal, vdir }: { sd: Poll<Sides>; pal: Palette; vdir: number }) {
  const w = sidesWhy(sd)
  if (w) return <div className="tline one"><span className="cap">TEENO</span> · <span style={{ color: w.startsWith('could') ? pal.caution : pal.textMuted }}>{w}</span></div>
  const t = sd.data!.three, ix = sd.data!.indices!
  if (!t || !t.t) return <div className="tline one"><span className="cap">TEENO</span> · <span style={{ color: pal.caution }}>{t?.line1 ?? CC + 'no closed slot yet'}</span></div>
  const wk = COUNT_MODEL === 'weekly'
  const line1 = (wk ? t.line1_weekly : null) ?? t.line1
  const line2 = wk ? t.line2_weekly : t.line2
  const dir = wk ? t.dir_weekly : t.dir_three
  const tone = dir === 1 ? pal.bull : dir === -1 ? pal.bear : pal.textPrimary
  const vs = dir && vdir ? (vdir === dir ? 'verdict ke saath' : 'verdict ke ulta') : null
  const noKal = IDX.filter((i) => ix[i]?.ok && !ix[i]?.kal)
  const tags = [...t.tags, ...(noKal.length ? [`subah ka scale — kal ka data nahi · ${noKal.join(', ')}`] : [])]
  return (<>
    <div className="tline" title={`sides.py at the ${t.t} slot — a count of indices, never odds [I]`}>
      <span className="cap">TEENO</span> <span className="mono muted">{t.t}</span> · <b style={{ color: tone }}>{line1}</b>
      {vs ? <span className="t2"> · {vs}</span> : null} <span className="tag">[I]</span>
    </div>
    <div className="tline2">
      {line2 ? <span className="cp pushti">{line2}</span> : <span className="cp lt">pushti: checked, none yet today</span>}
    </div>
    <div className="tags" title={[...tags, ...Object.entries(t.missing).map(([i, x]) => `${i}: ${x}`)].join(' · ')}>
      {Object.entries(t.missing).map(([i, x]) => <span key={i} className="cp lt" style={{ color: pal.caution }}>{i}: {noCC(x)}</span>)}
      {tags.map((x) => <span key={x} className="cp lt">{x}</span>)}
    </div>
  </>)
}

function SidesGrid({ sd, pal, full, onToggle }: { sd: Poll<Sides>; pal: Palette; full: boolean; onToggle: () => void }) {
  const w = sidesWhy(sd)
  if (w) return (
    <div className="sides"><div className="snone">
      <div style={{ color: w.startsWith('could') ? pal.caution : pal.textMuted }}>{w}</div>
      <div className="s12 muted">CALL / PUT writers per 5-min slot — likh, kaat, flat — for NIFTY, BANKNIFTY and SENSEX appear here once the server runs sides.py.</div>
    </div></div>)
  const ix = sd.data!.indices!, T = sd.data!.three?.t
  const all = new Set<string>()
  IDX.forEach((i) => ix[i]?.slots?.forEach((x) => all.add(x.t)))
  const last6 = [...all].filter((x) => !T || x <= T).sort().slice(-SHOW)
  // collapsed: the latest slot, and any slot of the last SHOW where an index was POWER (a PUSHTI is POWER too)
  const times = full ? last6 : last6.filter((t, k) => k === last6.length - 1 || IDX.some((i) => ix[i]?.slots?.find((q) => q.t === t)?.power))
  const cols = { gridTemplateColumns: `62px 26px repeat(${times.length}, ${full ? 'minmax(0,1fr)' : '76px'})` }
  if (!times.length) return <div className="sides"><div className="snone muted">{sd.data!.three?.line1 ?? 'checked, none yet — the first slot closes at 09:20'}</div></div>
  const hueOf = (side: 'ce' | 'pe') => (side === 'ce' ? CE_HUE : PE_HUE)
  const cell = (i: string, t: string, x: Slot | undefined, side: 'ce' | 'pe') => {
    if (!x) return <span key={t} className="sc muted" title="no slot at this mark">—</span>
    const c = x[side]
    const tip = `${i} ${x.from}–${x.t} ${side.toUpperCase()} (the nine nearest spot): ` + (c ? `${c.st ?? 'not read'}` +
      (c.x != null ? ` ×${c.x} of its ${x.M_basis === 'kal' ? 'kal ka' : "today's"} scale` : c.x_why ? ` (${c.x_why})` : '') +
      ` · top-2 by OI ${c.top2.map((k) => f0(k)).join(', ')}: ${c.agree}/2 the same way · ${c.n}/${c.of} of the nine · ΔOI ${oiL(c.d, true)}` +
      (c.power ? ' · POWER' : '') + (c.run > 1 ? ` · ${c.run} slots se` : '') : x.why.join(' · ')) +
      (x.src === 'backfill' ? ' · rebuilt after a restart (backfill)' : '') + ' [M] OI · [I] read'
    if (!c) return <span key={t} className="sc" style={{ color: pal.caution }} title={tip}>?</span>
    if (!c.st) return <span key={t} className="sc muted" title={x.why.join(' · ') || tip}>{x.why.some((q) => q.includes('kal ka data')) ? 'no kal' : 'warm'}</span>
    const first = c.power && x.first
    const txt = c.power ? `${SIDE_HI[c.st]}×${c.x != null ? Math.round(c.x) : '∞'} ${c.agree}/2` : SIDE_HI[c.st]
    return <span key={t} title={tip} className={`sc ${c.power ? 'pw' : ''} ${first ? 'first' : ''} ${x.src === 'backfill' ? 'bf' : ''} ${x.M_basis === 'kal' ? 'kal' : ''}`}
      style={{ color: first ? pal.card : c.st === 'FLAT' ? pal.textMuted : hueOf(side), fontWeight: c.st === 'COV' || c.power ? 700 : 400 }}>{txt}</span>
  }
  const readCell = (t: string, x: Slot | undefined) => {
    if (!x) return <span key={t} className="sc muted">—</span>
    if (!x.word) {
      const y = x.why.find((q) => q.startsWith('15:15')) ? '15:15' : x.why.some((q) => q.includes('kal ka data')) ? 'no kal' : x.ce && !x.ce.st ? 'warm' : '?'
      return <span key={t} className="sc muted" title={x.why.join(' · ')}>{y}</span>
    }
    // only a POWER slot's word is drawn in colour; a non-POWER word is context, drawn quiet
    const col = !x.power ? pal.textMuted : x.dir === 1 ? pal.bull : x.dir === -1 ? pal.bear : pal.textPrimary
    const forced = x.fuel_top2_underwater
    return <span key={t} className={`sc rw ${x.power ? 'pw' : ''} ${x.power && x.first ? 'first' : ''}`}
      style={{ color: x.power && x.first ? pal.card : col, fontWeight: x.power ? 700 : 500 }}
      title={`${x.word}${x.power ? (x.first ? ' · PUSHTI (first POWER slot this way since the last opposite one)' : ' · POWER, continuation (phir se)') : ' · not POWER'}`
        + ` · index ${x.move?.d != null ? (x.move.d > 0 ? '+' : '') + f1(x.move.d) : '?'} (${x.move?.st ?? '?'})`
        + (forced != null ? ` · forced ${forced}/2 (fuel side's top-2 writers underwater, ltp > day VWAP)` : x.forced_why ? ` · ${x.forced_why}` : '')
        + (x.fuel_dIV_med != null ? ` · IV ${x.fuel_dIV_med > 0 ? '+' : ''}${x.fuel_dIV_med} vol pts` : '') + ' [I]'}>{x.word}</span>
  }
  return (
    <div className="sides">
      <div className="srow shead" style={cols}>
        <button className="stog" onClick={onToggle} title={full ? 'show only the latest slot and the POWER slots' : `show all ${last6.length} slots of the last 30 min`}>
          SIDES {full ? '▾ chhota' : `▸ poora (${last6.length})`}</button>{times.map((t) => <span key={t} className="mono">{t}</span>)}</div>
      {IDX.map((i) => {
        const x = ix[i]
        if (!x || !x.ok) return (
          <div className="srow sblock" key={i} style={cols}><b className="mono">{i}</b><span />
            <span className="one" style={{ gridColumn: '3 / -1', color: pal.caution }}>{x?.why ?? CC + 'not in the reply'}</span></div>)
        const by = new Map((x.slots ?? []).map((q) => [q.t, q]))
        const note = x.expiry_day ? 'expiry din' : i === 'BANKNIFTY' ? (x.dte != null ? `${x.dte} DTE` : 'monthly') : x.chain_ok === false ? 'chain down' : ''
        return (
          <div className="sblock" key={i}>
            <div className="srow" style={cols}><b className="mono">{i}</b><span className="ce sd">CE</span>{times.map((t) => cell(i, t, by.get(t), 'ce'))}</div>
            <div className="srow" style={cols}><span className="muted s10" title={i === 'BANKNIFTY' ? 'the monthly book: a witness, shown and never counted (Mary, 2026-10-04)' : note}>{note}</span><span className="pe sd">PE</span>{times.map((t) => cell(i, t, by.get(t), 'pe'))}</div>
            <div className="srow" style={cols}><span /><span className="muted sd">read</span>{times.map((t) => readCell(t, by.get(t)))}</div>
          </div>)
      })}
    </div>)
}

/* ── the trap layer (round 5, rev trap-1, SHADOW): render only, every line from trap.py ── */
const TRAP_MISSING = CC + 'server not restarted with the trap read yet'
const TRAP_OPEN_KEY = 'tapemap.board.trapOpen'           // collapsed by default; a blocked store just means collapsed
function loadTrapOpen(): boolean {
  try { return localStorage.getItem(TRAP_OPEN_KEY) === '1' } catch { return false }
}
function saveTrapOpen(v: boolean) {
  try { localStorage.setItem(TRAP_OPEN_KEY, v ? '1' : '0') } catch { /* private window / blocked: stays per-session */ }
}

function TrapBlock({ tp, index, pal, open, onToggle }: { tp: Poll<Trap>; index: IndexKey; pal: Palette; open: boolean; onToggle: () => void }) {
  const d = tp.data, x = d?.ok ? d.indices?.[index] : undefined
  const w = d?.ok ? (!x ? 'reading the traps…' : x.ok ? null : x.why ?? CC + `no trap read for ${index}`)
    : d ? d.why ?? CC + 'the trap read failed'
      : tp.why && /HTTP 404/.test(tp.why) ? TRAP_MISSING                   // an older server has no /api/trap route
        : tp.why === 'reading…' ? 'reading the traps…' : CC + noCC(tp.why ?? 'no trap read')
  const L = x?.ok ? x.lines : undefined
  const head = (
    <div className="tline one">
      <button className="stog trapt" onClick={onToggle} title={open ? 'hide the trap lines' : `show ${index}'s three trap lines`}>
        TRAP · shadow {open ? '▾' : '▸'}</button>
      {L?.t ? <span className="mono muted"> {L.t}</span> : null}
      {w ? <span style={{ color: w.startsWith('could') ? pal.caution : pal.textMuted }}> · {w}</span> : null}
      <span className="tag"> [I] shadow — changes no verdict, word or count</span>
    </div>)
  if (!open || w || !L) return head
  const tone = L.chhoota?.startsWith('▲') ? pal.bull : L.chhoota?.startsWith('▼') ? pal.bear : pal.textSecondary
  const notes = [x!.stamps_why, x!.who_why, x!.xindex_why, x!.tape_why, x!.oi_prev_why].filter((q): q is string => !!q)
  return (<>
    {head}
    <div className="trap" title={`trap.py rev ${d!.rev ?? '?'}, fixed ${d!.fixed_at ?? '?'} — display and log only [I]`}>
      <div className="tl"><span className="cap">TRAP</span><span style={{ color: L.trap.startsWith('could') ? pal.caution : undefined }}>{L.trap}</span></div>
      <div className="tl"><span className="cap">CHHOOTA</span><span style={{ color: tone, fontWeight: L.chhoota?.startsWith('koi') ? 400 : 650 }}>{L.chhoota ?? '—'}</span></div>
      {L.agla ? <div className="tl"><span className="cap">AGLA</span><span>{L.agla}</span></div> : null}
      {notes.length ? <div className="tags">{notes.map((q) => <span key={q} className="cp lt" style={q.startsWith('could') ? { color: pal.caution } : undefined}>{q}</span>)}</div> : null}
    </div>
  </>)
}

/* ── one piece: label · its day · its state now ───────────────────────────── */
function Piece({ f, spot, pts, top, bot, asofM, hasGrid, pal }: {
  f: Front; spot: number; pts: { m: number; v: number | null }[]; top: number; bot: number
  asofM: number | null; hasGrid: boolean; pal: Palette
}) {
  const H = 32, pad = 3, h = hue(f.side)
  const y = (v: number) => pad + ((top - v) / (top - bot || 1)) * (H - 2 * pad)
  const x = (m: number) => m - OPEN_M
  const segs: { m: number; v: number }[][] = []
  let cur: { m: number; v: number }[] = []
  for (const p of pts) {
    if (p.v == null) { if (cur.length) segs.push(cur); cur = []; continue }
    cur.push({ m: p.m, v: p.v })
  }
  if (cur.length) segs.push(cur)
  const line = (s: { m: number; v: number }[]) => s.map((p, i) => `${i ? 'L' : 'M'}${x(p.m)} ${y(p.v).toFixed(2)}`).join('')
  const y0 = y(0)
  const pm = mm(f.peak_at)
  const after = pts.filter((p) => p.m >= pm && p.v != null) as { m: number; v: number }[]
  const showPeak = f.peak > 0 && !atPeak(f)
  const st = stateOf(f)
  const a = f.peak > 0 && !atPeak(f) ? against(f, spot) : null
  const [m, dd] = f.itm
  const built = f.built === 'today' && f.share != null ? `aaj bana ${Math.round(f.share * 100)}%`
    : f.built === 'carried' && f.share != null ? `pehle se ${Math.round((1 - f.share) * 100)}%`
      : f.built === 'never' ? 'aaj nahi bana' : 'built: could not check'
  const pxPeak = (x(pm) / SPAN) * 100
  return (
    <div className="row lane">
      <div style={{ minWidth: 0 }} title={`open ${f.open != null ? oiL(f.open) : '(could not check)'} → now ${f.now_oi != null ? oiL(f.now_oi) : '(could not check)'} OI [M]`}>
        <div className="mono" style={{ color: h, fontWeight: 750, fontSize: 15, lineHeight: '19px' }}>{f.side} {f0(f.k)}</div>
        <div className="s12 one"><span className="cp sm">{m} {f0(dd)}</span> <span className={`cp sm ${f.built === 'today' ? 'ink' : ''}`}>{built}</span></div>
      </div>
      <div style={{ position: 'relative', height: H }}>
        {hasGrid && segs.length ? <>
          <svg viewBox={`0 0 ${SPAN} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: H, display: 'block', overflow: 'visible' }}>
            <line x1={0} x2={SPAN} y1={y0} y2={y0} stroke={pal.textMuted} strokeOpacity={0.55} strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
            {segs.map((s, i) => (
              <path key={`a${i}`} d={`${line(s)}L${x(s[s.length - 1].m)} ${y0}L${x(s[0].m)} ${y0}Z`} fill={wash(h, 0.13)} stroke="none" />
            ))}
            {showPeak && after.length > 1 && (
              <path d={`M${x(after[0].m)} ${y(f.peak)}L${x(after[after.length - 1].m)} ${y(f.peak)}${[...after].reverse().map((p) => `L${x(p.m)} ${y(p.v).toFixed(2)}`).join('')}Z`}
                fill={wash(h, 0.3)} stroke="none" />
            )}
            {showPeak && after.length > 1 && (
              <line x1={x(after[0].m)} x2={x(after[after.length - 1].m)} y1={y(f.peak)} y2={y(f.peak)} stroke={h} strokeOpacity={0.6} strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
            )}
            {segs.map((s, i) => <path key={`l${i}`} d={line(s)} fill="none" stroke={h} strokeWidth={1.6} vectorEffect="non-scaling-stroke" />)}
            {asofM != null && <line x1={x(asofM)} x2={x(asofM)} y1={0} y2={H} stroke={pal.textMuted} strokeOpacity={0.5} vectorEffect="non-scaling-stroke" />}
          </svg>
          {showPeak && <>
            <span className="dot" style={{ left: `${pxPeak}%`, top: y(f.peak), background: h }} />
            <span className="plabel mono" style={{ top: Math.max(0, y(f.peak) - 15), ...(pxPeak > 72 ? { right: `${100 - pxPeak}%`, marginRight: 6 } : { left: `${pxPeak}%`, marginLeft: 6 }) }}>
              ruka {f.peak_at}
            </span>
          </>}
        </> : <div className="nogrid">{hasGrid ? `${f.side} ${f0(f.k)}: not on the minute grid — could not check` : ''}</div>}
      </div>
      <div style={{ minWidth: 0 }}>
        <div className="one"><span className="state">{st.hi}</span> <span className="s12 t2">{st.en}</span></div>
        <div className="s12 t2 one" title={a != null ? `price has moved ${f0(Math.abs(a))} pts ${a >= 0 ? 'against' : 'in favour of'} these writers since their ${f.peak_at} peak (${f.peak_spot != null ? f1(f.peak_spot) : '?'} → ${f1(spot)}) [M]` : undefined}>
          {f.peak <= 0 ? <>{oiL(f.chg, true)} vs the open</>
            : atPeak(f) ? <>{oiL(f.chg, true)} since the open</>
              : <><span className="mono">{oiL(f.peak, true)}</span> {f.peak_at} → <span className="mono">{oiL(f.chg, true)}</span> now</>}
          {a != null && <> · <b style={{ color: a >= 0 ? pal.textPrimary : pal.textMuted }}>{Math.round(Math.abs(a)) === 0 ? 'bhav wahi' : `bhav ${f0(Math.abs(a))} ${a >= 0 ? 'khilaaf' : 'haq mein'}`}</b></>}
        </div>
      </div>
    </div>
  )
}

/* ── the footer: as of, the grid, the rule, what is not shown ─────────────── */
function Foot({ b, index, why, pal }: { b: BoardDoc | null; index: IndexKey; why: string | null; pal: Palette }) {
  const n = new Date(), m = n.getHours() * 60 + n.getMinutes(), wd = n.getDay()
  const live = wd > 0 && wd < 6 && m >= OPEN_M && m < OPEN_M + SPAN + 1
  const g = b?.ok ? b.grid : undefined
  const forced = b?.not_shown?.forced
  return (
    <div className="foot">
      {index}
      {b?.ok && b.asof ? <> · as of {b.asof}, {live ? 'the last finished minute' : 'the last snapshot of the session this server holds'}</> : null}
      {g && <> · grid {g.from}–{g.to}{g.holes.length ? <span style={{ color: pal.caution }}>, holes {g.holes.join(', ')}</span> : ', whole'} [M]</>}
      {why && b?.ok ? <span style={{ color: pal.caution }}> · could not refresh — {noCC(why)}; this is the read of {b.asof}</span> : null}
      {b?.ok && <> · verdict [I] on §1d's states, gates nothing{forced ? <> · <i>{forced}</i></> : null}</>}
    </div>
  )
}

const CSS = (p: Palette) => `
.nb { padding:8px 12px 6px; display:flex; flex-direction:column; gap:8px; color:${p.textPrimary}; font-size:13px; line-height:18px; }
.nb * { box-sizing:border-box; }
.nb .card { background:${p.card}; border:1px solid ${p.border}; border-radius:10px; min-width:0; }
.nb .read { display:grid; grid-template-columns:minmax(0,1fr) 494px; column-gap:14px; padding:8px 14px 8px; }
.nb .ladai { display:flex; gap:8px; margin-top:5px; min-width:0; }
.nb .ladai .lvchip { font-size:12.5px; line-height:17px; padding:1px 8px; }
.nb .tline { font-size:13.5px; line-height:19px; margin-top:5px; }
.nb .tags { display:flex; gap:6px; margin-top:3px; overflow:hidden; white-space:nowrap; }
.nb .cp.lt { font-weight:600; color:${p.textSecondary}; font-size:11px; line-height:15px; padding:0 6px; }
.nb .tline2 { margin-top:3px; min-width:0; }
.nb .cp.pushti { background:${p.textPrimary}; color:${p.card}; border-color:${p.textPrimary}; font-size:11.5px; line-height:15px; padding:1px 7px; font-weight:600; white-space:normal; letter-spacing:0; }
.nb .sc.kal { text-decoration:underline dotted; }
.nb .sides { border-left:1px solid ${p.border}; padding-left:12px; min-width:0; display:flex; flex-direction:column; gap:2px; justify-content:center; }
.nb .srow { display:grid; grid-template-columns:62px 26px repeat(${SHOW}, minmax(0,1fr)); column-gap:3px; align-items:center; font-size:10.5px; line-height:14px; }
.nb .shead { color:${p.textMuted}; font-size:10px; }
.nb .shead .mono { text-align:center; }
.nb .sblock { display:flex; flex-direction:column; gap:1px; padding-top:2px; border-top:1px solid ${wash(p.textPrimary, 0.07)}; }
.nb .sd { font-size:10px; font-weight:700; }
.nb .s10 { font-size:9.5px; line-height:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.nb .sc { font-family:'Roboto Mono',monospace; white-space:nowrap; overflow:hidden; text-align:center; padding:0 1px; border:1px solid transparent; border-radius:3px; letter-spacing:-0.3px; }
.nb .sc.pw { border-color:${p.textPrimary}; }
.nb .sc.first { background:${p.textPrimary}; border-color:${p.textPrimary}; }
.nb .sc.bf { font-style:italic; }
.nb .sc.rw { font-family:Inter,'Segoe UI',system-ui,sans-serif; font-weight:700; font-size:10px; letter-spacing:0; }
.nb .snone { font-size:12.5px; line-height:18px; padding:6px 2px; }
.nb .stog { font-size:10px; font-weight:700; letter-spacing:.06em; color:${p.textSecondary}; background:transparent; border:1px solid ${p.border}; border-radius:4px; padding:0 4px; cursor:pointer; white-space:nowrap; grid-column:1 / 3; justify-self:start; }
.nb .stog:hover { border-color:${p.textMuted}; color:${p.textPrimary}; }
.nb .trapt { font-size:10.5px; padding:0 5px; }
.nb .trap { margin-top:3px; display:flex; flex-direction:column; gap:1px; padding:3px 8px; border:1px dashed ${p.border}; border-radius:6px; }
.nb .tl { display:grid; grid-template-columns:62px minmax(0,1fr); column-gap:6px; font-size:12.5px; line-height:17px; }
.nb .verdict { font-size:22px; line-height:28px; font-weight:750; letter-spacing:.01em; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.nb .fact { font-size:13.5px; line-height:19px; color:${p.textSecondary}; margin-top:2px; }
.nb .count { font-size:13px; line-height:19px; margin-top:2px; }
.nb .cps { display:flex; flex-direction:column; gap:5px; justify-content:center; align-items:stretch; }
.nb .asof { font-size:11px; color:${p.textMuted}; text-align:right; }
.nb .lvchip { border:1px solid ${p.border}; border-radius:8px; padding:3px 10px; font-size:13px; line-height:18px; white-space:nowrap; }
.nb .cp { display:inline-block; font-size:12px; line-height:16px; font-weight:700; border:1px solid ${p.border}; border-radius:5px; padding:1px 7px; white-space:nowrap; letter-spacing:.02em; }
.nb .cp.big { font-size:14px; line-height:20px; padding:2px 9px; }
.nb .cp.sm { font-size:11px; line-height:14px; padding:0 5px; font-weight:600; color:${p.textSecondary}; }
.nb .cp.sm.ink { color:${p.textPrimary}; border-color:${wash(p.textPrimary, 0.35)}; }
.nb .tag { font-size:11px; color:${p.textMuted}; font-weight:400; font-family:'Roboto Mono',monospace; }
.nb .muted { color:${p.textMuted}; } .nb .t2 { color:${p.textSecondary}; } .nb .s12 { font-size:12px; line-height:16px; }
.nb .ce { color:${CE_HUE}; } .nb .pe { color:${PE_HUE}; } .nb .sep { color:${p.textMuted}; margin:0 4px; }
.nb .one { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
.nb .body { display:grid; grid-template-columns:minmax(0,1fr) 236px; gap:8px; align-items:stretch; }
.nb .board { padding:5px 10px 3px; }
.nb .bhead { font-size:11.5px; line-height:15px; color:${p.textMuted}; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.nb .cap { font-size:11px; font-weight:700; letter-spacing:.08em; color:${p.textSecondary}; }
.nb .row { display:grid; grid-template-columns:160px minmax(0,1fr) 268px; column-gap:12px; align-items:center; }
.nb .lane { height:38px; border-top:1px solid ${wash(p.textPrimary, 0.06)}; }
.nb .lv { height:17px; }
.nb .lvline { border-top:1px dashed ${wash(p.accent, 0.6)}; height:0; position:relative; }
.nb .lvline > span { position:absolute; left:0; top:-9px; max-width:100%; padding-right:6px; background:${p.card}; color:${p.accent}; font-weight:600; }
.nb .spot { height:20px; }
.nb .spotline { border-top:2px solid ${p.accent}; height:0; }
.nb .axis { margin-top:1px; }
.nb .tick { position:absolute; top:0; font-size:10.5px; color:${p.textMuted}; }
.nb .dot { position:absolute; width:7px; height:7px; border-radius:50%; margin:-3.5px 0 0 -3.5px; box-shadow:0 0 0 1.5px ${p.card}; }
.nb .plabel { position:absolute; font-size:11px; line-height:13px; font-weight:700; color:${p.textPrimary}; background:${wash(p.card, 0.85)}; padding:0 2px; white-space:nowrap; }
.nb .nogrid { height:100%; border:1px dashed ${p.border}; border-radius:4px; font-size:11.5px; color:${p.caution}; padding:2px 6px; }
.nb .state { font-size:12.5px; font-weight:750; letter-spacing:.03em; }
.nb .kram { padding:5px 10px 4px; overflow:hidden; }
.nb .ev { display:grid; grid-template-columns:40px 78px minmax(0,1fr); column-gap:6px; font-size:12.5px; line-height:16px; padding:2px 0; border-top:1px solid ${wash(p.textPrimary, 0.05)}; }
.nb .foot { font-size:11px; line-height:15px; color:${p.textMuted}; padding:0 2px; }
`
