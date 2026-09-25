import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { IndexKey } from '../data'

/* ── BOARD rev 3 ─────────────────────────────────────────────────────────────
   The chess-board main page, docs/mockups/board-chess-rev3-2026-09-24.html,
   wired to the live server. Its notes (…-notes.md) are the spec: §2 reading
   order, §6 definitions, §7 what is NOT wired, §11 element → source.

     /api/board    headline, fronts (carried in / built today), defender,
                   folds, FIRST, agreement, trend box, PCR, squares, mirror,
                   not_shown — ONE read per index per finished minute, cached
                   on the server; ?ce=&pe= moves only the mirror
     /api/oihist   the per-strike minute grid: OI at the open, the session
                   high, OI now (open + change) — the book and the OI clock
     /api/warmap   PDH/PDC/PDL/PWH/PWL/OPEN — level tags on the strike rows
     /api/frame    NIFTY's d2/u2 pockets (futures prices, placed by basis)

   Nothing is decided here: every read is the server's, in its own words. What
   this file computes is geometry (bar lengths, the ΔOI per 5 min sum) off [M]
   numbers. Her rules: LIGHT only; NO price or premium chart (OI bars are
   fine); hue = side only (coral CE, teal PE), state = geometry; a count is
   never odds; three absences, never one; after 15:30 the last snapshot.

   1536 × 577, never scaled: the shell hides the answer band, the MACHINE
   strip and the tape's replay bar on this tab so it fits under GlanceBar
   (72) + tabs (46) in a maximized 1536 × 695 window.
─────────────────────────────────────────────────────────────────────────── */

type Side = 'CE' | 'PE'
type Tag = 'M' | 'I'
type Vote = 1 | 0 | -1 | null
type State = 'BUILDING' | 'STALLED' | 'UNWINDING'

type BFront = {
  k: number; side: Side; oi: number | null; chg: number; peak: number; peak_at: string
  state: State; tag: Tag; open: number | null; now_oi: number | null; share: number | null
  built: 'today' | 'carried' | 'never' | null; itm: [string, number]; peak_spot: number | null
  unwind_at: string | null; nearer: boolean; rank: number; words: string; built_label: string | null
}
type Fold = { k: number; side: Side; t: string; high: number; high_at: string; spot_high: number; spot_fold?: number; off?: number; tag: Tag; src?: string }
type Def = { k: number; side: Side; flags: string[]; tag: Tag; fades: string } | null
type Fam = { k: string; v: Vote; fact: string; tag: Tag; doubt: string | null }
type TRow = { v: Vote; word: string; z?: number; sw?: string; r?: number; n: number }
type Piv = { name: string; px: number; dist: number }
type MLeg = {
  strike: number | null; t?: string; c?: number; vwap?: number | null; z?: number | null; band?: string | null
  why?: string; tag: Tag; pivots?: { above: Piv | null; above_why: string | null; below: Piv | null; below_why: string | null; day?: string | null } | null
  pivots_why?: string | null
}
type Square = { px: number; labels: string[]; dist: number }
type Dir = {
  sq: Square[]; who: { text: string; k: number | null; side: Side; tag: Tag }
  paying: { yn: string; text: string; tag: Tag }; refused: string; press: { yn: string; text: string; tag: Tag }
}
type Board = {
  ok: boolean; why?: string; idx?: string; day?: string; asof?: string | null; spot?: number; step?: number
  headline?: { text: string; tag: Tag; fold: { k: number; side: Side; t: string } | null }
  fronts?: BFront[] | null; fronts_why?: string | null
  defender?: { buy: Def; sell: Def; note: string }
  folds?: Fold[] | null; folds_why?: string | null
  first?: Fold | null; first_why?: string | null
  agreement?: { head: { dir: number; n: number; of: number; against: number; read: number; text: string }; fam: Fam[] }
  trend?: {
    rows: Record<string, TRow> | null; why?: string; at?: string
    strong: { word: string | null; n: number[]; why?: string }
    regime: { word: string | null; price?: [string, string]; oi?: [string, string]; why?: string }
  }
  pcr?: { v: number | null; text: string; tag: Tag }
  squares?: { up: Dir | null; up_why?: string; dn: Dir | null; dn_why?: string; levels_why: string | null }
  grid?: { from: string | null; to: string | null; marks: number; holes: string[]; whole: boolean }
  mirror?: {
    ok: boolean; why?: string; expiry?: string; legs?: { CE: MLeg; PE: MLeg }
    vs_futures?: { word: string | null; why?: string | null; text?: string }
    strikes?: { CE: number; PE: number }; atm?: number; span?: number
  }
  not_shown?: Record<string, string>
  built_at?: number
}
type OiHist = {
  ok: boolean; why?: string | null
  minutes?: Record<string, { spot?: number | null; k?: Record<string, unknown> } | null>
  peak?: { k: number; side: string; oi: number }[]; open?: { k: number; side: string; oi: number }[]; open_why?: string | null
}
type GridRow = { t: string; m: number; spot: number | null; k: Map<number, [number | null, number | null]> }
type Grid = {
  rows: GridRow[]; ks: number[]; chgNow: (k: number, i: 0 | 1) => number | null
  open: Map<string, number>; peak: Map<string, number>
  hi: { px: number; t: string } | null; lo: { px: number; t: string } | null
}
type Level = { kind: string; px: number; label?: string }
type WarMap = { ok: boolean; why?: string | null; indices?: Record<string, { levels?: Level[] | null; daily_why?: string | null }> }
type Frame = { ok: boolean; where?: { px?: number | null; buy_zone?: [number, number] | null; sell_zone?: [number, number] | null } | null }

const IDX: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']
const CC = 'could not check — '
const OPEN_M = 9 * 60 + 15, LAST_M = 15 * 60 + 29
const TF = ['1m', '3m', '5m', '15m', '1h', '4h', 'D']
const TAG_KINDS = new Set(['PDH', 'PDC', 'PDL', 'PWH', 'PWL', 'OPEN'])
const NS_LABEL: Record<string, string> = {
  level_under_attack: 'level under attack', flush: 'flush?', deep_otm: 'deep OTM', forced: 'forced / released', engine: 'engine words',
}

const ok = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x)
const mm = (t: string) => +t.slice(0, 2) * 60 + +t.slice(3, 5)
const hh = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
const f0 = (x: number) => Math.round(x).toLocaleString('en-IN')
const f1 = (x: number) => x.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const f2 = (x: number) => x.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const sgn = (x: number) => (x > 0 ? '+' : x < 0 ? '−' : '')
const sg1 = (x: number) => sgn(x) + Math.abs(x).toFixed(1)
const sL = (x: number) => sgn(x) + (Math.abs(x) / 1e5).toFixed(1) + 'L'
const uL = (x: number) => (Math.abs(x) / 1e5).toFixed(1) + 'L'
const pct = (x: number) => Math.round(x * 100) + '%'
const VOTE = (v: Vote) => (v === 1 ? '▲' : v === -1 ? '▼' : v === 0 ? '·' : '?')
const hue = (s: Side) => (s === 'CE' ? 'ce' : 'pe')
const noCC = (s: string | null | undefined) => String(s ?? '').replace(/^could not check — /, '')
const noNS = (s: string) => s.replace(/^not shown — /, '')
/** §1d's nine: the grid strikes nearest spot, a tie to the lower one (fronts.nine). */
const nine = (ks: number[], s: number) => [...ks].sort((a, b) => Math.abs(a - s) - Math.abs(b - s) || a - b).slice(0, 9)
const pair = (v: unknown): [number | null, number | null] =>
  Array.isArray(v) ? [ok(v[0]) ? v[0] : null, ok(v[1]) ? v[1] : null] : [null, null]

function usePoll<T>(url: string | null, ms: number): { data: T | null; why: string | null } {
  const [st, setSt] = useState<{ data: T | null; why: string | null }>({ data: null, why: 'reading…' })
  useEffect(() => {
    if (!url) return
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
        if (alive) {
          setSt((p) => ({ data: p.data, why: `the backend did not answer (${String(e)})` }))
          retry = window.setTimeout(load, 3000)
        }
      }
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, ms)
    return () => { alive = false; window.clearInterval(id); window.clearTimeout(retry) }
  }, [url, ms])
  return st
}

/* ── the GlanceBar's per-index read (the shell, Board tab only) ─────────── */
export type GlanceRead = { line: string; title: string }

function glanceLine(b: Board | null): GlanceRead {
  if (!b) return { line: CC + 'the backend did not answer', title: '' }
  if (!b.ok || !ok(b.spot)) return { line: CC + noCC(b.why ?? 'no board read yet'), title: b.why ?? '' }
  const f = b.headline?.fold
  return {
    line: `idx ${f0(b.spot)} · ${f ? `fold ${f.side} ${f0(f.k)} ${f.t}` : 'no fold near spot'}`,
    title: `${b.idx} at ${b.asof} (the last finished minute) [I]: ${b.headline?.text ?? ''}`,
  }
}

/** One gentle poll of /api/board for all three indices, only while the Board
 *  tab is showing. The same URL the board itself reads, so the server answers
 *  it from its per-minute cache. */
export function useBoardGlance(on: boolean): Partial<Record<IndexKey, GlanceRead>> {
  const [reads, setReads] = useState<Partial<Record<IndexKey, GlanceRead>>>({})
  useEffect(() => {
    if (!on) return
    let alive = true, retry = 0
    const load = async () => {
      // one after another, not a burst: the dev proxy drops the odd request
      // when several land at once (a 502 with an empty body, measured 23:20)
      let failed = false
      for (const k of IDX) {
        let r: GlanceRead, bad = false
        try {
          const res = await fetch(`/api/board?idx=${k}`)
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          r = glanceLine((await res.json()) as Board)
        } catch { r = glanceLine(null); bad = failed = true }
        if (!alive) return
        // a failed poll keeps the last good line for that index, and retries soon
        setReads((p) => (bad && p[k] ? p : { ...p, [k]: r }))
      }
      if (failed && alive) retry = window.setTimeout(load, 5000)
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 60000)
    return () => { alive = false; window.clearInterval(id); window.clearTimeout(retry) }
  }, [on])
  return reads
}

/* ── styles: scoped under .b3, the mockup's own tokens ───────────────────── */
const CSS = `
.b3 { --card:#FFFFFF; --inset:#F0F2F5; --line:#E3E7ED; --line2:#C9D0DA; --text:#141A22; --text2:#4D5766; --muted:#636C7A;
  --ink:#141A22; --coral:#C4452C; --teal:#0B8277; --brass:#A9762A; --caution:#B45309;
  height:577px; display:grid; padding:6px 10px 4px; column-gap:8px; row-gap:5px; position:relative; overflow:hidden;
  grid-template-columns:440px 268px minmax(0,1fr) 322px; grid-template-rows:112px minmax(0,1fr) 104px 14px;
  color:var(--text); font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif; font-size:14px; line-height:19px; }
.b3 * { box-sizing:border-box; }
.b3 .num { font-family:"JetBrains Mono","Cascadia Mono",Consolas,ui-monospace,monospace; font-variant-numeric:tabular-nums; }
.b3 .muted { color:var(--muted); } .b3 .t2 { color:var(--text2); } .b3 .amber { color:var(--caution); }
.b3 .ce { color:var(--coral); } .b3 .pe { color:var(--teal); } .b3 .brass { color:var(--brass); }
.b3 .tag { font-size:11px; color:var(--muted); font-family:"JetBrains Mono",Consolas,monospace; font-weight:400; }
.b3 .cap { font-size:11px; letter-spacing:.07em; color:var(--muted); font-weight:700; }
.b3 .s11 { font-size:11px; line-height:14px; }
.b3 .one { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
.b3 button { font:inherit; }
.b3 .btn { border:1px solid var(--line); background:var(--card); color:var(--text2); border-radius:6px; padding:0 7px; cursor:pointer; font-size:11px; line-height:16px; white-space:nowrap; }
.b3 .btn:hover { border-color:var(--line2); color:var(--text); }
.b3 .panel { background:var(--card); border:1px solid var(--line); border-radius:8px; min-width:0; min-height:0; overflow:hidden; position:relative; }
.b3 .answer { grid-column:1 / -1; padding:4px 12px 3px; display:flex; flex-direction:column; gap:2px; }
.b3 .answer > * { flex-shrink:0; }
.b3 .head { display:flex; align-items:baseline; gap:8px; font-size:22px; line-height:28px; font-weight:650; }
.b3 .head .txt { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
.b3 .agree { display:grid; grid-template-columns:206px repeat(5, minmax(0,1fr)); column-gap:12px; height:34px; }
.b3 .agree .hd { border-right:1px solid var(--line); padding-right:8px; white-space:nowrap; overflow:hidden; }
.b3 .fam { display:grid; grid-template-columns:62px 1fr; column-gap:4px; min-width:0; }
.b3 .fam .k { font-size:11px; font-weight:700; letter-spacing:.06em; color:var(--muted); line-height:19px; white-space:nowrap; display:flex; align-items:center; gap:4px; }
.b3 .lamp { display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px; border:1.5px solid var(--ink); border-radius:3px; color:var(--ink); font-size:10px; line-height:1; }
.b3 .lamp.nv { border-style:dashed; border-color:var(--line2); color:var(--muted); }
.b3 .lamp.cc { border-style:dashed; border-color:var(--caution); color:var(--caution); }
.b3 .story { font-size:11px; line-height:14px; color:var(--text2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 .story b { color:var(--text); font-weight:650; }
.b3 .chip { font-size:10px; line-height:13px; font-weight:700; border:1.5px solid var(--ink); border-radius:4px; padding:0 3px; white-space:nowrap; }
.b3 .chip.lt { border-color:var(--line2); color:var(--text2); font-weight:600; }
.b3 .chip.inv { border:0; background:var(--ink); color:var(--card); letter-spacing:.04em; }
.b3 .ph { flex-shrink:0; padding:3px 10px 0; font-size:11px; line-height:13px; color:var(--text2); overflow:hidden; white-space:nowrap; }
.b3 .col { display:flex; flex-direction:column; }
/* the book */
.b3 .ladder { grid-column:1; grid-row:2; }
.b3 .lbody { flex:1; min-height:0; position:relative; display:grid; padding:2px 0 3px; }
.b3 .lrow { display:grid; grid-template-columns:82px minmax(0,1fr) 100px minmax(0,1fr) 82px; align-items:center; min-height:0; }
.b3 .edge { font-size:9.5px; line-height:12px; white-space:nowrap; overflow:hidden; padding:0 3px; letter-spacing:-.02em; }
.b3 .edge .x { font-size:8px; opacity:.85; }
.b3 .bars { position:relative; height:100%; }
.b3 .bar { position:absolute; top:50%; height:10px; margin-top:-5px; }
.b3 .hi { position:absolute; top:50%; height:14px; margin-top:-7px; width:1.5px; background:var(--ink); }
.b3 .box { position:absolute; top:50%; height:16px; margin-top:-8px; border:1.2px solid var(--ink); }
.b3 .rk { position:absolute; top:50%; margin-top:-7px; font-size:11px; line-height:14px; font-weight:700; }
.b3 .miss { position:absolute; top:50%; height:10px; margin-top:-5px; width:18px; border:1px dashed var(--caution); }
.b3 .mid { display:grid; grid-template-columns:50px minmax(0,1fr); align-items:center; height:100%; padding:0 3px; }
.b3 .mid.near { background:rgba(20,26,34,.06); }
.b3 .kchip { font-size:11px; line-height:15px; padding:0 3px; border-radius:3px; border:1px solid transparent; background:transparent; cursor:pointer; text-align:center; color:var(--muted); }
.b3 .kchip.on { color:var(--text2); } .b3 .kchip.fr { color:var(--text); font-weight:650; } .b3 .kchip.atm { color:var(--brass); font-weight:700; }
.b3 .kchip.off { opacity:.55; }
.b3 .kchip.pick { background:rgba(169,118,42,.12); border-color:rgba(169,118,42,.45); }
.b3 .kchip:hover { border-color:var(--line2); }
.b3 .ltag { font-size:9.5px; line-height:11px; font-weight:700; color:var(--brass); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-left:2px; }
.b3 .spot { position:absolute; left:78px; right:78px; height:0; border-top:1.2px dashed var(--brass); pointer-events:none; }
/* the pieces */
.b3 .rail { grid-column:2; grid-row:2; display:flex; flex-direction:column; gap:5px; min-height:0; }
.b3 .card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:4px 8px 3px; flex:1; min-height:0; display:flex; flex-direction:column; gap:1px; overflow:hidden; }
.b3 .card.first { border-color:var(--text2); }
.b3 .card .hd { display:flex; align-items:center; gap:4px; white-space:nowrap; }
.b3 .card .hd .rkn { margin-left:auto; }
.b3 .card .ln { font-size:11px; line-height:14px; color:var(--text2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 .slot { border:1px dashed var(--line2); border-radius:4px; padding:0 5px; color:var(--muted); font-size:11px; line-height:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 .glyph { display:inline-block; width:10px; height:10px; flex-shrink:0; }
/* what can happen */
.b3 .squares { grid-column:3; grid-row:2; padding:5px 9px 5px; display:flex; flex-direction:column; gap:5px; }
.b3 .sqh { display:flex; justify-content:space-between; align-items:baseline; height:14px; line-height:14px; white-space:nowrap; gap:6px; }
.b3 .dir { border:1px solid var(--line); border-left-width:3px; border-radius:6px; padding:2px 7px 3px; display:grid; grid-template-columns:88px minmax(0,1fr); column-gap:6px; }
.b3 .dir.up { border-left-color:var(--coral); } .b3 .dir.dn { border-left-color:var(--teal); }
.b3 .dir .l { font-size:10.5px; line-height:17px; letter-spacing:.06em; color:var(--muted); font-weight:700; white-space:nowrap; }
.b3 .dir .v { font-size:13px; line-height:17px; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 .yn { font-weight:700; }
.b3 .yn.yes { color:var(--text); } .b3 .yn.no { color:var(--muted); } .b3 .yn.notyet { color:var(--text2); } .b3 .yn.cc { color:var(--caution); }
/* the mirror + trend */
.b3 .right { grid-column:4; grid-row:2; display:flex; flex-direction:column; gap:5px; min-height:0; }
.b3 .mirror { flex:1; padding:4px 9px 4px; display:flex; flex-direction:column; gap:1px; }
.b3 .mirror .ml { font-size:11px; line-height:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:var(--text2); }
.b3 .mirror .mh { font-size:13px; line-height:17px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 .mirror .ml.two { white-space:normal; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
.b3 .mchips { display:flex; gap:3px; align-items:center; }
.b3 .mchips .lab { font-size:10px; font-weight:700; width:18px; }
.b3 .mchips button { font-size:10.5px; line-height:14px; padding:0 5px; border-radius:3px; border:1px solid var(--line); background:transparent; color:var(--muted); cursor:pointer; }
.b3 .mchips button.on { border-color:rgba(169,118,42,.45); background:rgba(169,118,42,.12); color:var(--brass); font-weight:700; }
.b3 .tslot { height:158px; flex-shrink:0; border:1px dashed var(--line2); border-radius:8px; font-size:11px; color:var(--muted); display:flex; align-items:center; justify-content:center; text-align:center; padding:8px; }
.b3 .trend { position:absolute; z-index:15; width:322px; background:var(--card); border:1px solid var(--line2); border-radius:8px;
  box-shadow:0 6px 20px rgba(20,26,34,.14); font-size:11px; line-height:13px; user-select:none; }
.b3 .trend .th { display:flex; align-items:center; gap:6px; padding:2px 6px 1px 8px; cursor:move; border-bottom:1px solid var(--line); white-space:nowrap; }
.b3 .trend .th .cap { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; }
.b3 .trend .tb { padding:3px 8px 4px; }
.b3 .trend .tr { display:grid; grid-template-columns:30px 74px 58px 70px 1fr; column-gap:4px; height:12px; line-height:12px; white-space:nowrap; }
.b3 .trend .tr .w { font-weight:700; color:var(--ink); }
.b3 .trend .tr.none .w { color:var(--muted); font-weight:600; }
.b3 .trend .ft { border-top:1px solid var(--line); margin-top:3px; padding-top:3px; }
.b3 .trend .ft div { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 .trend.min { width:auto; max-width:600px; } .b3 .trend.min .tb { display:none; }
/* bottom */
.b3 .clockp { grid-column:1 / 3; grid-row:3; }
.b3 .moves { grid-column:3 / -1; grid-row:3; padding:3px 10px 2px; }
.b3 .mvh { display:flex; justify-content:space-between; align-items:center; height:17px; }
.b3 .mv { display:grid; grid-template-columns:42px 16px minmax(0,1fr); column-gap:4px; padding:0 4px; border-radius:4px; line-height:18px; height:18px; overflow:hidden; }
.b3 .mv .x { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 .log { position:absolute; inset:0; z-index:20; background:var(--card); border:1px solid var(--line2); border-radius:8px; box-shadow:0 8px 28px rgba(20,26,34,.18);
  padding:6px 8px 8px; display:flex; flex-direction:column; grid-column:3 / -1; grid-row:2 / 4; }
.b3 .log .body { overflow-y:auto; flex:1; min-height:0; }
.b3 .log .mv { height:auto; } .b3 .log .mv .x { white-space:normal; }
.b3 .foot { grid-column:1 / -1; grid-row:4; font-size:11px; line-height:14px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.b3 svg text { font-family:Inter,"Segoe UI",system-ui,sans-serif; font-size:11px; fill:var(--text2); }
`

function Glyph({ side, state }: { side: Side; state: State }) {
  const h = side === 'CE' ? 'var(--coral)' : 'var(--teal)'
  const style = state === 'BUILDING' ? { background: h }
    : state === 'STALLED' ? { background: side === 'CE' ? 'rgba(196,69,44,.3)' : 'rgba(11,130,119,.3)', border: `1px solid ${h}` }
      : { background: `repeating-linear-gradient(45deg, ${h} 0 1.5px, transparent 1.5px 4px)`, border: `1px solid ${h}` }
  return <span className="glyph" style={style} title={state} />
}

const Tg = ({ t }: { t: string }) => <span className="tag">[{t}]</span>

/* ── the component ────────────────────────────────────────────────────────── */
type TrendUi = { pos: { x: number; y: number } | null; min: boolean }
const TREND_KEY = 'tapemap.board3.trend'
function loadTrendUi(): TrendUi {
  try {
    const v = JSON.parse(localStorage.getItem(TREND_KEY) || 'null')
    if (v && typeof v === 'object') return { pos: v.pos && ok(v.pos.x) && ok(v.pos.y) ? v.pos : null, min: !!v.min }
  } catch { /* storage blocked or corrupt: docked, expanded */ }
  return { pos: null, min: false }
}

export default function BoardRev3({ index }: { index: IndexKey }) {
  const [sel, setSel] = useState<Set<number> | null>(null)        // null = her nine
  const [mk, setMk] = useState<{ CE: number | null; PE: number | null }>({ CE: null, PE: null })   // null = ATM
  const [log, setLog] = useState(false)
  const [tui, setTui] = useState<TrendUi>(loadTrendUi)
  useEffect(() => { try { localStorage.setItem(TREND_KEY, JSON.stringify(tui)) } catch { /* per-viewer convenience only */ } }, [tui])
  useEffect(() => { setSel(null); setMk({ CE: null, PE: null }); setLog(false) }, [index])
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setLog(false) }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [])

  const q = (mk.CE != null ? `&ce=${mk.CE}` : '') + (mk.PE != null ? `&pe=${mk.PE}` : '')
  const bd = usePoll<Board>(`/api/board?idx=${index}${q}`, 20000)
  const oh = usePoll<OiHist>(`/api/oihist?idx=${index}`, 30000)
  const wm = usePoll<WarMap>(`/api/warmap?idx=${index}`, 60000)
  const fm = usePoll<Frame>(index === 'NIFTY' ? `/api/frame?idx=${index}` : null, 60000)
  const b = bd.data && bd.data.idx === index ? bd.data : null

  /* the minute grid, cut to the board's own minute, so book and board agree */
  const grid = useMemo((): Grid | null => {
    const d = oh.data
    if (!d || !d.ok || !d.minutes) return null
    const asof = b?.asof ?? null
    const rows = Object.entries(d.minutes)
      .filter(([t, r]) => /^\d\d:\d\d$/.test(t) && r && r.k && mm(t) >= OPEN_M && mm(t) <= LAST_M && (!asof || t <= asof))
      .sort(([a], [z]) => (a < z ? -1 : 1))
      .map(([t, r]) => {
        const k = new Map<number, [number | null, number | null]>()
        for (const [ks, v] of Object.entries(r!.k!)) { const n = Number(ks); if (ok(n)) k.set(n, pair(v)) }
        return { t, m: mm(t), spot: ok(r!.spot) ? r!.spot : null, k }
      })
    if (!rows.length) return null
    const ks = [...rows[rows.length - 1].k.keys()].sort((a, z) => a - z)
    const chgNow = (k: number, i: 0 | 1): number | null => {
      for (let j = rows.length - 1; j >= 0; j--) { const v = rows[j].k.get(k)?.[i]; if (v != null) return v }
      return null
    }
    const open = new Map<string, number>(), peak = new Map<string, number>()
    for (const r of d.open ?? []) if (ok(r.oi)) open.set(`${Number(r.k)}${r.side.toUpperCase()}`, r.oi)
    for (const r of d.peak ?? []) if (ok(r.oi)) peak.set(`${Number(r.k)}${r.side.toUpperCase()}`, r.oi)
    let hi: { px: number; t: string } | null = null, lo: { px: number; t: string } | null = null
    for (const r of rows) if (r.spot != null) {
      if (!hi || r.spot > hi.px) hi = { px: r.spot, t: r.t }
      if (!lo || r.spot < lo.px) lo = { px: r.spot, t: r.t }
    }
    return { rows, ks, chgNow, open, peak, hi, lo }
  }, [oh.data, b?.asof])

  const step = b?.step && b.step > 0 ? b.step : null
  const spot = b?.spot ?? null
  const near = useMemo(() => new Set(grid && spot != null ? nine(grid.ks, spot) : []), [grid, spot])
  const follow = sel ?? near

  /* level tags on the strike rows [M]; the pockets are futures prices placed by the basis [I] */
  const levels = useMemo(() => {
    const out: { kind: string; px: number; title: string }[] = []
    const w = wm.data?.indices?.[index]
    for (const l of w?.levels ?? []) if (TAG_KINDS.has(l.kind) && ok(l.px)) out.push({ kind: l.kind, px: l.px, title: `${l.label ?? l.kind} [M]` })
    if (grid?.hi) out.push({ kind: 'H', px: grid.hi.px, title: `the day's high ${f1(grid.hi.px)} at ${grid.hi.t}, on the grid's minute marks [M]` })
    if (grid?.lo) out.push({ kind: 'L', px: grid.lo.px, title: `the day's low ${f1(grid.lo.px)} at ${grid.lo.t}, on the grid's minute marks [M]` })
    const wh = index === 'NIFTY' ? fm.data?.where : null
    if (wh && ok(wh.px) && spot != null) {
      const basis = wh.px - spot
      if (wh.buy_zone && ok(wh.buy_zone[1])) out.push({ kind: 'd2', px: wh.buy_zone[1] - basis, title: `d2 ${f1(wh.buy_zone[1])} fut, ≈ ${f0(wh.buy_zone[1] - basis)} index at a basis of ${f1(basis)} [I]` })
      if (wh.sell_zone && ok(wh.sell_zone[0])) out.push({ kind: 'u2', px: wh.sell_zone[0] - basis, title: `u2 ${f1(wh.sell_zone[0])} fut, ≈ ${f0(wh.sell_zone[0] - basis)} index at a basis of ${f1(basis)} [I]` })
    }
    return { out, why: wm.data && !w ? CC + (wm.data.why ?? `the war map has no ${index} board yet`) : w?.daily_why ? CC + w.daily_why : wm.why && !wm.data ? CC + wm.why : null }
  }, [wm.data, wm.why, fm.data, grid, spot, index])

  // the trend box: docked into its slot unless she has moved it
  const root = useRef<HTMLDivElement>(null), slot = useRef<HTMLDivElement>(null), tbox = useRef<HTMLDivElement>(null)
  const [dock, setDock] = useState({ x: 0, y: 0 })
  const [, setTick] = useState(0)
  useEffect(() => {
    const f = () => setTick((t) => t + 1)          // the slot moves with the window width
    window.addEventListener('resize', f)
    return () => window.removeEventListener('resize', f)
  }, [])
  useLayoutEffect(() => {
    if (!root.current || !slot.current) return
    const a = root.current.getBoundingClientRect(), s = slot.current.getBoundingClientRect()
    if (!a.width) return
    if (Math.abs(s.left - a.left - dock.x) > 0.5 || Math.abs(s.top - a.top - dock.y) > 0.5) setDock({ x: s.left - a.left, y: s.top - a.top })
    // a position saved on a wider screen is pulled back onto this board
    const p = tui.pos
    if (p && (p.x > a.width - 60 || p.y > a.height - 22)) setTui((t) => ({ ...t, pos: { x: Math.min(p.x, a.width - 60), y: Math.min(p.y, a.height - 22) } }))
  })
  const drag = (e: React.PointerEvent) => {
    if ((e.target as HTMLElement).closest('button') || !root.current || !tbox.current) return
    const a = root.current.getBoundingClientRect(), bx = tbox.current.getBoundingClientRect()
    const sx = e.clientX, sy = e.clientY, ox = bx.left - a.left, oy = bx.top - a.top
    const mv = (ev: PointerEvent) => setTui((t) => ({ ...t, pos: {
      x: Math.max(0, Math.min(ox + ev.clientX - sx, a.width - 60)),
      y: Math.max(0, Math.min(oy + ev.clientY - sy, a.height - 22)) } }))
    const up = () => { window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up) }
    window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up)
  }

  const toggle = (k: number) => {
    const base = new Set(sel ?? near)
    if (base.has(k)) base.delete(k); else base.add(k)
    setSel(base.size ? base : null)
  }

  const asofNote = b?.asof ? (() => {
    const n = new Date(), m = n.getHours() * 60 + n.getMinutes()
    return m >= 15 * 60 + 30 || m < OPEN_M || b.day !== localDay(n)
      ? `as of ${b.asof}, the session's last snapshot — it reads the same whenever it is opened`
      : `as of ${b.asof}, the last finished minute`
  })() : null

  return (
    <div className="b3" ref={root}>
      <style>{CSS}</style>
      <Answer b={b} why={bd.why} />
      <Book b={b} grid={grid} step={step} spot={spot} near={near} follow={follow} picked={!!sel}
        onToggle={toggle} onReset={() => setSel(null)} levels={levels.out} levelsWhy={levels.why} oihWhy={oh.data && !oh.data.ok ? oh.data.why ?? 'no grid' : oh.why} />
      <Rail b={b} />
      <Squares b={b} />
      <div className="right">
        <Mirror b={b} mk={mk} setMk={setMk} />
        <div className="tslot" ref={slot} style={{ visibility: tui.pos ? 'visible' : 'hidden' }}>
          the trend box floats: drag it by its title bar · – collapses it · double-click the title to dock it here
        </div>
      </div>
      <Trend b={b} ui={tui} at={tui.pos ?? dock} boxRef={tbox} onDrag={drag}
        onMin={() => setTui((t) => ({ ...t, min: !t.min }))} onDock={() => setTui((t) => ({ ...t, pos: null }))} />
      <OiClock b={b} grid={grid} follow={sel} />
      <Moves b={b} onLog={() => setLog(true)} />
      {log && <FullLog b={b} onClose={() => setLog(false)} />}
      <div className="foot" title={b?.day ? `${index} ${b.day}` : ''}>
        {index} · {b?.day ?? '—'} · {asofNote ?? (bd.why ? CC + bd.why : 'reading…')}
        {b?.grid && <> · grid {b.grid.from}–{b.grid.to}, {b.grid.marks} marks{b.grid.holes.length ? `, holes ${b.grid.holes.join(', ')}` : ''} <Tg t="M" /></>}
        {bd.why && b ? <span className="amber"> · could not refresh — {bd.why}; this is the read of {b.asof}</span> : null}
        {' '}· every number [M] measured or [I] inferred · display only, nothing here gates anything
      </div>
    </div>
  )
}

function localDay(n: Date) {
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`
}

/* ── 1–3: the headline, the count, FIRST FOLD, the staircase, what is not shown ── */
function Answer({ b, why }: { b: Board | null; why: string | null }) {
  if (!b || !b.ok) {
    return (
      <div className="panel answer">
        <div className="head amber"><span className="txt">{b ? CC + noCC(b.why) : why ? CC + why : 'reading the board…'}</span></div>
        {b?.not_shown && <NotShown ns={b.not_shown} />}
      </div>
    )
  }
  const a = b.agreement, h = a?.head
  const fs = b.folds ?? []
  const stair = (side: Side) => {
    const x = fs.filter((f) => f.side === side).slice(-3)
    return x.length ? x.map((f) => `${f0(f.k)} ${f.t}`).join(' → ') : b.folds_why ? noCC(b.folds_why) : 'none yet — checked, none'
  }
  const fst = b.first
  return (
    <div className="panel answer">
      <div className="head" title={b.headline?.text}>
        <span className="txt">{b.headline?.text ?? CC + 'no headline in the payload'}</span>
        <span className="tag" style={{ flexShrink: 0 }}>[{b.headline?.tag ?? 'I'}]</span>
      </div>
      {a && h ? (
        <div className="agree">
          <div className="hd">
            <div><b>{h.dir > 0 ? `▲ UP · ${h.n} of ${h.of} agree` : h.dir < 0 ? `▼ DOWN · ${h.n} of ${h.of} agree` : `NO SIDE · ${h.n} up · ${h.against} down`}</b> <Tg t="I" /></div>
            <div className="s11 muted">{h.dir !== 0 ? `${h.against} against · ` : ''}{h.of - h.read} not read · a count, not odds</div>
          </div>
          {a.fam.map((f) => (
            <div className="fam" key={f.k}>
              <div className="k"><span className={`lamp ${f.v == null ? 'cc' : f.v === 0 ? 'nv' : ''}`}>{VOTE(f.v)}</span>{f.k}</div>
              <div style={{ minWidth: 0 }}>
                <div className="one" title={f.fact}>{f.v == null ? noCC(f.fact) : f.fact} <Tg t={f.tag} /></div>
                <div className={`one s11 ${f.v == null ? 'amber' : 'muted'}`} title={f.doubt ?? f.fact}>{f.v == null ? 'could not check' : f.doubt}</div>
              </div>
            </div>
          ))}
        </div>
      ) : <div className="s11 amber" style={{ height: 34 }}>agreement: could not check — not in the payload</div>}
      <div className="story" title={`FIRST FOLD ${fst ? `${fst.side} ${fst.k} ${fst.t} — ${fst.src ?? ''}` : b.first_why ?? ''}`}>
        {fst
          ? <><span className="chip inv">1ST FOLD</span> <b className={hue(fst.side)}>{fst.side} {f0(fst.k)}</b> folded <b>{fst.t}</b>, high {sL(fst.high)} at {fst.high_at} @ {f1(fst.spot_high)} <span className="tag">[{fst.tag}] stamped once</span></>
          : <><b>FIRST FOLD</b> <span className={b.first_why?.startsWith('could') ? 'amber' : 'muted'}>{b.first_why ?? 'none yet'}</span></>}
        {' · '}<b>FOLDS</b> <span className="pe">puts</span> {stair('PE')} · <span className="ce">calls</span> {stair('CE')} <Tg t="M" />
        {' · '}{b.pcr ? <>{b.pcr.text} <Tg t={b.pcr.tag} /></> : <span className="amber">PCR: could not check</span>}
      </div>
      {b.not_shown && <NotShown ns={b.not_shown} />}
    </div>
  )
}

function NotShown({ ns }: { ns: Record<string, string> }) {
  const txt = Object.entries(ns).map(([k, v]) => `${NS_LABEL[k] ?? k}: ${noNS(v)}`).join(' · ')
  return <div className="story muted" title={txt}><b className="muted" style={{ letterSpacing: '.06em' }}>NOT SHOWN</b> — {txt}</div>
}

/* ── 4–5: the book, CE | strike | PE, and the strike chips ─────────────────── */

function Book({ b, grid, step, spot, near, follow, picked, onToggle, onReset, levels, levelsWhy, oihWhy }: {
  b: Board | null; grid: Grid | null; step: number | null; spot: number | null; near: Set<number>; follow: Set<number>; picked: boolean
  onToggle: (k: number) => void; onReset: () => void; levels: { kind: string; px: number; title: string }[]; levelsWhy: string | null; oihWhy: string | null
}) {
  if (!b?.ok || step == null || spot == null) return <div className="panel ladder col"><div className="ph"><span className="cap">THE BOOK</span> · <span className="amber">{CC + (b?.why ? noCC(b.why) : 'no board read yet')}</span></div></div>
  const atm = Math.round(spot / step) * step
  const rows: number[] = []
  for (let n = 7; n >= -7; n--) rows.push(Math.round(atm + n * step))
  const hiK = rows[0], loK = rows[rows.length - 1]
  const inGrid = new Set(grid?.ks ?? [])
  const F = new Map<string, BFront>((b.fronts ?? []).map((f) => [`${Math.round(f.k)}${f.side}`, f]))
  const val = (k: number, side: Side) => {
    const i = side === 'CE' ? 0 : 1
    if (!grid || !inGrid.has(k)) return null
    const op = grid.open.get(`${k}${side}`), ch = grid.chgNow(k, i)
    if (op == null || ch == null) return null
    return { open: op, now: op + ch, peak: grid.peak.get(`${k}${side}`) ?? null }
  }
  let amax = 1
  for (const k of rows) for (const s of ['CE', 'PE'] as Side[]) { const v = val(k, s); if (v) amax = Math.max(amax, v.now, v.peak ?? 0) }
  // 80% of the lane at the longest bar: the top-2 rank prints just outside its box
  const len = (x: number) => Math.max(0, Math.min(80, (x / amax) * 80))
  const tags = new Map<number, typeof levels>(), up: string[] = [], dn: string[] = []
  for (const l of levels) {
    const k = Math.round(Math.round(l.px / step) * step)
    if (k > hiK) up.push(`${l.kind} ${f0(l.px)}`)
    else if (k < loK) dn.push(`${l.kind} ${f0(l.px)}`)
    else tags.set(k, [...(tags.get(k) ?? []), l])
  }
  const lastFold = (k: number, side: Side) => (b.folds ?? []).filter((x) => Math.round(x.k) === k && x.side === side)
  const hf = b.headline?.fold
  const sy = ((hiK - spot) / step + 0.5) / rows.length          // the spot line, as a fraction of the body
  return (
    <div className="panel ladder col">
      <div className="ph" style={{ height: 44 }}>
        <div className="one"><span className="cap">THE BOOK</span> · OI now <Tg t="M" /> · bar = {uL(amax)} · <span className="brass">- - spot {f1(spot)}</span> · follow:{' '}
          {picked ? <><b>{follow.size} chosen</b> <button className="btn" onClick={onReset} title="back to her rule: the nine strikes nearest spot" style={{ lineHeight: '12px', fontSize: 10, padding: '0 4px' }}>nine ⟲</button></>
            : <b title="her rule: the nine grid strikes nearest spot, moving with it — click a strike to choose your own">her nine</b>}</div>
        <div className="one"><b className="ce">◄ CE</b> <span className="muted">▮ built today ▯ carried in · │ high · □ top 2 · edges: latest fold high→unwind</span> <b className="pe">PE ►</b></div>
        <div className="one muted" title={levels.map((l) => l.title).join(' · ')}>
          {levelsWhy ? <span className="amber">levels: {levelsWhy} · </span> : null}
          {oihWhy ? <span className="amber">grid: {CC + noCC(oihWhy)} · </span> : null}
          <span className="brass">off the board</span> ↑ {up.length ? up.join(' · ') : 'checked, none'} · ↓ {dn.length ? dn.join(' · ') : 'checked, none'}
        </div>
      </div>
      <div className="lbody" style={{ gridTemplateRows: `repeat(${rows.length}, minmax(0,1fr))` }}>
        {rows.map((k) => {
          const on = follow.has(k)
          const isF = F.has(`${k}CE`) || F.has(`${k}PE`)
          const cls = `kchip num ${k === atm ? 'atm' : isF ? 'fr' : on ? 'on' : ''} ${on ? '' : 'off'} ${picked && on ? 'pick' : ''}`
          const tg = tags.get(k)
          const side = (s: Side) => {
            const v = val(k, s), f = F.get(`${k}${s}`), a = on ? 1 : 0.35, pe = s === 'PE'
            const at = (w: number) => (pe ? { left: `${w}%` } : { right: `${w}%` })
            const rgb = s === 'CE' ? '196,69,44' : '11,130,119'
            if (!v) return <div className="bars"><span className="miss" style={pe ? { left: 0 } : { right: 0 }} title={`${s} ${f0(k)}: ${inGrid.has(k) ? 'no open or no change for this strike' : "outside the server's ±8 grid"} — could not check`} /></div>
            const wn = len(v.now), wo = len(v.open), wp = v.peak != null ? len(v.peak) : null
            const light = { background: `rgba(${rgb},${0.18 * a})`, boxShadow: `inset 0 0 0 0.8px rgba(${rgb},${0.35 * a})` }
            const title = `${s} ${f0(k)}: open ${uL(v.open)} (carried in) → now ${uL(v.now)} (${sL(v.now - v.open)} today)${v.peak != null ? ` · session high ${uL(v.peak)}` : ''} [M]`
            return (
              <div className="bars" title={title}>
                {v.now > v.open ? <>
                  <span className="bar" style={{ ...at(0), width: `${wo}%`, ...light }} />
                  <span className="bar" style={{ ...at(wo), width: `${wn - wo}%`, background: `rgba(${rgb},${0.62 * a})` }} />
                </> : <>
                  <span className="bar" style={{ ...at(0), width: `${wn}%`, ...light }} />
                  <span className="bar" style={{ ...at(wo), width: 0, borderLeft: `1px dashed rgba(${rgb},${a})` }} />
                </>}
                {wp != null && <span className="hi" style={{ ...at(wp), opacity: on ? 1 : 0.4 }} />}
                {f && <>
                  <span className="box" style={{ ...at(0), width: `calc(${Math.max(wn, wp ?? 0)}% + 3px)` }} />
                  <span className={`rk num ${hue(s)}`} style={pe ? { left: `calc(${Math.max(wn, wp ?? 0)}% + 5px)` } : { right: `calc(${Math.max(wn, wp ?? 0)}% + 5px)` }}>{f.rank}</span>
                </>}
              </div>
            )
          }
          const edge = (s: Side) => {
            const fl = on ? lastFold(k, s) : []
            if (!fl.length) return <div className="edge" />
            const x = fl[fl.length - 1], live = hf && Math.round(hf.k) === k && hf.side === s && hf.t === x.t
            return <div className={`edge num ${hue(s)}`} style={{ textAlign: s === 'PE' ? 'right' : 'left', fontWeight: live ? 800 : 400 }}
              title={`${s} ${f0(k)} folded ${fl.length > 1 ? `${fl.length} times today; latest: ` : ''}high ${sL(x.high)} at ${x.high_at} @ ${f1(x.spot_high)} · §1d unwinding ${x.t}${ok(x.spot_fold) ? ` @ ${f1(x.spot_fold)}` : ''} [M]`}>
              {fl.length > 1 && <span className="x">×{fl.length} </span>}{x.high_at}→{x.t}</div>
          }
          return (
            <div className="lrow" key={k}>
              {edge('CE')}{side('CE')}
              <div className={`mid ${near.has(k) ? 'near' : ''}`}>
                <button className={cls} aria-pressed={on} onClick={() => onToggle(k)}
                  title={`${f0(k)}${k === atm ? ' — at the money' : ''}${near.has(k) ? ' · one of her nine' : ''} · click to ${on ? 'hide' : 'follow'} it`}>{f0(k)}</button>
                <span className="ltag" title={tg?.map((x) => x.title).join(' · ')}>{tg?.map((x) => x.kind).join('·') ?? ''}</span>
              </div>
              {side('PE')}{edge('PE')}
            </div>
          )
        })}
        <div className="spot" style={{ top: `calc(2px + (100% - 5px) * ${sy})` }} />
      </div>
    </div>
  )
}

/* ── 6: the four fronts, the defender said honestly ────────────────────────── */
function Rail({ b }: { b: Board | null }) {
  if (!b?.ok) return <div className="rail" />
  if (!b.fronts?.length) return <div className="rail"><div className="card"><div className="ln amber">{b.fronts_why ?? CC + 'no fronts in the payload'}</div></div></div>
  const fst = b.first
  return (
    <div className="rail">
      {b.fronts.map((f) => {
        const isFirst = !!fst && Math.round(fst.k) === Math.round(f.k) && fst.side === f.side
        const [m, dd] = f.itm
        const g = f.rank === 1 ? b.defender?.[f.side === 'PE' ? 'buy' : 'sell'] : null
        const hiAbs = f.open != null ? f.open + Math.max(0, f.peak) : null
        return (
          <div className={`card ${isFirst ? 'first' : ''}`} key={`${f.side}${f.k}`}>
            <div className="hd">
              <Glyph side={f.side} state={f.state} />
              <b className={hue(f.side)} style={{ fontSize: 13.5 }}>{f.side} {f0(f.k)}</b>
              <span className={`chip num ${m === 'OTM' ? 'lt' : ''}`}>{m} {f0(dd)}</span>
              {f.nearer && <span className="tag" title="the nearer to spot of this side's two">nearer</span>}
              {isFirst && <span className="chip inv" title={`the first §1d top-2 front today to fold — stamped once at ${fst!.t}`}>1ST FOLD</span>}
              <span className="rkn tag" title="rank by session-high absolute OI (§1d, unchanged)">#{f.rank}</span>
            </div>
            <div className="ln" title={f.words}><b className={hue(f.side)}>{f.state}</b> · {f.words}</div>
            <div className="ln" title={`open = OI at the open (carried in); high = open + the day's largest build${f.peak_spot != null ? `, spot ${f0(f.peak_spot)} then` : ''}; now = open + change [M]`}>
              {f.built_label ? <span className={`chip ${f.built === 'today' ? '' : 'lt'}`}>{f.built_label}</span> : <span className="amber">built today: could not check — no open</span>}
              {' '}open {f.open != null ? uL(f.open) : '(could not check)'} → high {hiAbs != null ? uL(hiAbs) : '(could not check)'}{f.peak > 0 ? ` ${f.peak_at}` : ''} → now {f.now_oi != null ? uL(f.now_oi) : '(could not check)'} <Tg t="M" />
            </div>
            {g ? (
              g.flags.length
                ? <div className="ln amber" title={`the §1d gate leans on this front for ${g.fades} fades: ${g.flags.join('; ')} — ${b.defender?.note ?? ''}`}>⚑ GATE DEFENDER ({g.fades}) · {g.flags.join(' · ')} <Tg t={g.tag} /></div>
                : <div className="ln" title={b.defender?.note}>⚑ GATE DEFENDER ({g.fades}) · the nearer wall, built today <Tg t={g.tag} /></div>
            ) : <div className="slot" title={b.not_shown?.forced ?? ''}>forced / released — not shown, pending her §1d addendum</div>}
          </div>
        )
      })}
    </div>
  )
}

/* ── WHAT CAN HAPPEN: the next square each way, and what it takes ─────────── */
function Squares({ b }: { b: Board | null }) {
  const ynCls: Record<string, string> = { yes: 'yes', no: 'no', 'not yet': 'notyet', 'could not check': 'cc' }
  const sq = b?.ok ? b.squares : undefined
  const card = (name: 'up' | 'dn') => {
    const p = sq?.[name], upd = name === 'up'
    if (!p) return <div className={`dir ${name}`}><div className="l">{upd ? '▲ UP TO' : '▼ DOWN TO'}</div><div className="v muted">{sq?.[`${name}_why`] ?? 'checked, none'}</div></div>
    const [a, nx] = p.sq
    return (
      <div className={`dir ${name}`}>
        <div className="l">{upd ? '▲ UP TO' : '▼ DOWN TO'}</div>
        <div className="v" title={p.sq.map((x) => `${f1(x.px)} (${sg1(x.dist)}): ${x.labels.join(', ')}`).join(' · then ')}>
          <b className={`num ${upd ? 'ce' : 'pe'}`}>{f0(a.px)}</b> <span className="num t2">{sg1(a.dist)}</span> · {a.labels.join(' · ')}{nx && <span className="s11 t2"> · then {f0(nx.px)}</span>} <Tg t="M" /></div>
        <div className="l">WHO PAYS</div><div className="v" title={p.who.text}>{p.who.text} <Tg t={p.who.tag} /></div>
        <div className="l">PAYING NOW?</div><div className="v" title={p.paying.text}><span className={`yn ${ynCls[p.paying.yn] ?? ''}`}>{p.paying.yn}</span> — {p.paying.text} <Tg t={p.paying.tag} /></div>
        <div className="l">PRESSING?</div><div className="v" title={p.press.text}><span className={`yn ${ynCls[p.press.yn] ?? ''}`}>{p.press.yn}</span> — {p.press.text} <Tg t={p.press.tag} /></div>
        <div className="l">AT THE LEVEL</div><div className="v muted s11" style={{ lineHeight: '17px' }} title={b?.not_shown?.level_under_attack}>not shown — the level-under-attack read is a draft, pending her pre-registration</div>
        <div className="l">REFUSED IF</div><div className="v t2" title={p.refused}>{p.refused} <Tg t="I" /></div>
      </div>
    )
  }
  return (
    <div className="panel squares">
      <div className="sqh"><span className="cap one">WHAT CAN HAPPEN · the next square each way and what it takes, never odds</span><Tg t="I" /></div>
      {!b?.ok ? <div className="s11 amber">{CC + noCC(b?.why ?? 'no board read yet')}</div>
        : !sq ? <div className="s11 muted">not shown — WHAT CAN HAPPEN is not wired on this server yet (it needs the server restarted onto board.squares)</div>
          : <>{card('up')}{card('dn')}{sq.levels_why && <div className="s11 amber one" title={sq.levels_why}>{sq.levels_why}</div>}</>}
    </div>
  )
}

/* ── 8: the mirror read, in words, with CE / PE strike chips ──────────────── */
function Mirror({ b, mk, setMk }: { b: Board | null; mk: { CE: number | null; PE: number | null }; setMk: (f: (m: { CE: number | null; PE: number | null }) => { CE: number | null; PE: number | null }) => void }) {
  const m = b?.ok ? b.mirror : undefined
  const step = b?.step ?? null, atm = m?.atm ?? (b?.spot != null && step ? Math.round(b.spot / step) * step : null)
  const chips = (side: Side) => {
    if (atm == null || !step) return null
    const ks = [-2, -1, 0, 1, 2].map((n) => Math.round(atm + n * step))
    const cur = mk[side]
    if (cur != null && !ks.includes(cur)) ks.push(cur)
    return (
      <div className="mchips">
        <span className={`lab ${hue(side)}`}>{side}</span>
        {ks.map((k) => (
          <button key={k} className={(cur ?? atm) === k ? 'on' : ''} title={k === atm ? 'the strike at the money (follows spot)' : 'pin this strike'}
            onClick={() => setMk((p) => ({ ...p, [side]: k === atm ? null : k }))}>{f0(k)}{k === atm ? ' ATM' : ''}</button>
        ))}
      </div>
    )
  }
  const leg = (side: Side) => {
    const L = m?.legs?.[side]
    const K = L?.strike ?? m?.strikes?.[side]
    const nm = <b className={hue(side)}>{side} {K != null ? f0(K) : ''}</b>
    if (!L) return [<>{nm} <span className="amber">could not check — no leg in the payload</span></>, null]
    if (L.why && !ok(L.c)) return [<>{nm} <span className={L.why.startsWith('could') ? 'amber' : 'muted'}>{L.why}</span></>, null]
    const z = L.z != null ? <>z <b className="num">{sg1(L.z)}</b> · {L.band}</> : <span className="amber">{L.why ?? 'z: could not check'}</span>
    const pv = L.pivots
    const p2 = pv ? <>pivots: above {pv.above ? `${pv.above.name} ${f2(pv.above.px)} (+${f2(pv.above.dist)})` : noCC(pv.above_why)} · below {pv.below ? `${pv.below.name} ${f2(pv.below.px)} (−${f2(pv.below.dist)})` : noCC(pv.below_why)} <Tg t="M" /></>
      : <span className="amber">pivots: {L.pivots_why ?? 'could not check'}</span>
    return [<>{nm} <span className="num">₹{f2(L.c!)}</span> · {z} <Tg t={L.tag} /> <span className="tag">{L.t} bar</span></>, p2]
  }
  if (!m) return <div className="panel mirror"><div className="ml"><span className="cap">THE MIRROR READ</span></div><div className="ml amber">{b?.ok ? 'could not check — no mirror in the payload' : ''}</div></div>
  const [c1, c2] = leg('CE'), [p1, p2] = leg('PE')
  const vf = m.vs_futures
  return (
    <div className="panel mirror">
      <div className="ml"><span className="cap">THE MIRROR READ</span> · premium vs its own session VWAP ±σ{m.expiry ? ` · ${m.expiry} expiry` : ''}</div>
      {chips('CE')}{chips('PE')}
      {m.ok === false ? <div className="ml two amber" title={m.why}>{m.why}</div> : <>
        <div className="mh">{c1}</div>{c2 && <div className="ml">{c2}</div>}
        <div className="mh">{p1}</div>{p2 && <div className="ml">{p2}</div>}
        <div className="ml two" style={{ marginTop: 2 }} title={vf?.text ?? vf?.why ?? ''}>
          <span className="cap">VS FUTURES</span> {vf?.word ? <>{vf.text}</> : <span className={(vf?.why ?? '').startsWith('could') ? 'amber' : 'muted'}>{vf?.why ?? 'could not check'}</span>} <Tg t="I" /> <span className="tag">draft</span></div>
      </>}
    </div>
  )
}

/* ── 9: the floating trend box, text only ──────────────────────────────────── */
const RULES = "On the INDEX's own candles, 20 closed bars per row (the forming bar is not used). POS: price now against the 20-bar mean, in that window's own σ; up at +1σ or more, down at −1σ or less. SWINGS: the last two pivot highs and lows (a pivot beats the 2 bars either side); HH·HL up, LH·LL down, anything else mixed. SLOPE: the least-squares line through the 20 closes, its rise across the window in σ; up at +1σ, down at −1σ. A row is UP when 2 of the 3 say up and none says down (DOWN mirrored), else RANGE. REGIME: TREND when the 5m, 15m and 1h rows all point one way AND OI agrees; PIN/CHOP when two of those rows read RANGE and both sides' nearer fronts are writing; otherwise NOT AGREED. STRONG: BULLS when 4 or more rows are UP and at most 1 is DOWN (BEARS mirrored), else NEITHER. Display only; not tuned; not odds."

function Trend({ b, ui, at, boxRef, onDrag, onMin, onDock }: {
  b: Board | null; ui: TrendUi; at: { x: number; y: number }; boxRef: React.RefObject<HTMLDivElement | null>
  onDrag: (e: React.PointerEvent) => void; onMin: () => void; onDock: () => void
}) {
  const tr = b?.ok ? b.trend : undefined
  const rows = tr?.rows ?? null
  const rg = tr?.regime, stg = tr?.strong
  const pill = rows ? TF.map((k) => `${k}${VOTE(rows[k]?.v ?? null)}`).join(' ') + ` · ${rg?.word ?? '—'} · ${stg?.word ?? '—'}` : 'could not check'
  let body: ReactNode
  if (!tr) body = <div className="tb amber">{b?.ok ? 'could not check — no trend in the payload' : 'reading…'}</div>
  else if (!rows) body = <div className="tb amber">{tr.why ?? 'could not check — no index candle yet'}</div>
  else body = (
    <div className="tb">
      {TF.map((k) => {
        const x = rows[k]
        if (!x || x.v == null) return <div className="tr none" key={k}><span className="num">{k}</span><span className="w">forming</span><span className="muted" style={{ gridColumn: '3 / -1' }}>{x ? `${x.n} of 20 bars — not a read yet` : 'could not check'}</span></div>
        return <div className={`tr ${x.v === 0 ? 'none' : ''}`} key={k}><span className="num">{k}</span><span className="w">{VOTE(x.v)} {x.word}</span>
          <span className="num">{ok(x.z) ? sg1(x.z) : ''}</span><span className="num">{!x.sw || x.sw === 'no swings' ? '—' : x.sw}</span><span className="num">{ok(x.r) ? sg1(x.r) : ''}</span></div>
      })}
      <div className="ft">
        <div title={`price: ${(rg?.price ?? []).join(': ')} · OI: ${(rg?.oi ?? []).join(': ')}`}><b>REGIME {rg?.word ?? '—'}</b> <Tg t="I" />{rg?.why ? <span className="amber"> {rg.why}</span> : null}</div>
        <div className="muted" title={`${(rg?.price ?? [])[1] ?? ''} · ${(rg?.oi ?? [])[1] ?? ''}`}>price: {rg?.price?.[0] ?? '—'} · OI: {rg?.oi?.[0] ?? '—'}</div>
        <div><b>STRONG: {stg?.word ?? '—'}</b> {stg?.n && <span className="muted">{stg.n[1]} down · {stg.n[0]} up · {stg.n[2]} range{stg.n[3] ? ` · ${stg.n[3]} forming` : ''}</span>}</div>
      </div>
    </div>
  )
  return (
    <div className={`trend ${ui.min ? 'min' : ''}`} ref={boxRef} style={{ left: at.x, top: at.y }}>
      <div className="th" title={RULES} onPointerDown={onDrag} onDoubleClick={onDock}>
        <span className="cap">TREND <Tg t="I" />{ui.min && <span className="num" style={{ fontWeight: 400, letterSpacing: 0, color: 'var(--text)', marginLeft: 6 }}>{pill}</span>}</span>
        {!ui.min && <><span className="tag" style={{ width: 58 }}>pos σ</span><span className="tag" style={{ width: 70 }}>swings</span><span className="tag" style={{ width: 46 }}>slope σ</span></>}
        <button className="btn" onClick={onMin} style={{ padding: '0 5px', lineHeight: '13px' }} title={ui.min ? 'expand' : 'collapse'} aria-label={ui.min ? 'expand the trend box' : 'collapse the trend box'}>{ui.min ? '▢' : '–'}</button>
      </div>
      {!ui.min && body}
    </div>
  )
}

/* ── the OI clock: ΔOI per 5 min over the followed strikes (OI only) ──────── */
function OiClock({ b, grid, follow }: { b: Board | null; grid: Grid | null; follow: Set<number> | null }) {
  const W = 714, H = 102, XL = 46, XR = W - 10
  const xOf = (m: number) => XL + ((XR - XL) * (m - OPEN_M)) / 375
  const A0 = 30, A1 = 80, mid = (A0 + A1) / 2
  const bars: { s0: number; dc: number; dp: number }[] = []
  if (grid) {
    const idxAt = (m: number) => { let j = -1; for (let i = 0; i < grid.rows.length && grid.rows[i].m <= m; i++) j = i; return j }
    const chg = (j: number, k: number, i: 0 | 1) => { for (let q = j; q >= 0; q--) { const v = grid.rows[q].k.get(k)?.[i]; if (v != null) return v } return null }
    const end = grid.rows[grid.rows.length - 1].m
    for (let s0 = OPEN_M; s0 <= LAST_M; s0 += 5) {
      const e = Math.min(s0 + 4, LAST_M)
      if (e > end) break
      const je = idxAt(e)
      if (je < 0 || grid.rows[je].m < s0) continue                    // a hole is a hole, never a zero bar
      const jp = s0 === OPEN_M ? -1 : idxAt(s0 - 1)
      const sp = grid.rows[je].spot
      const set = follow ?? new Set(sp != null ? nine(grid.ks, sp) : [])
      let dc = 0, dp = 0
      for (const k of set) {
        const c1 = chg(je, k, 0), p1 = chg(je, k, 1), c0 = jp < 0 ? 0 : chg(jp, k, 0), p0 = jp < 0 ? 0 : chg(jp, k, 1)
        if (c1 != null && c0 != null) dc += c1 - c0
        if (p1 != null && p0 != null) dp += p1 - p0
      }
      bars.push({ s0, dc, dp })
    }
  }
  // the 09:15 bar is the open against the carried book; it would flatten the rest, so it is clipped
  const bmax = Math.max(1, ...bars.filter((x) => x.s0 !== OPEN_M).map((x) => Math.max(Math.abs(x.dc), Math.abs(x.dp))))
  const bw = xOf(5) - xOf(0)
  const sc = (v: number) => Math.max(-1, Math.min(1, v / bmax)) * (mid - A0 - 1)
  return (
    <div className="panel clockp">
      <svg width={W} height={H} style={{ display: 'block' }}>
        <text x={10} y={12}><tspan style={{ fontWeight: 700, letterSpacing: '.07em', fill: 'var(--muted)' }}>THE OI CLOCK</tspan>
          <tspan> · ΔOI per 5 min over the {follow ? 'chosen' : "nine nearest spot at each bar"} strikes [M] · ±{uL(bmax)} · CE ▮ PE ▮ · light = given back</tspan></text>
        <text x={10} y={25} style={{ fill: 'var(--muted)', fontSize: 10.5 }}><title>{`deep OTM: ${b?.not_shown?.deep_otm ?? ''} · flush?: ${b?.not_shown?.flush ?? ''}`}</title>not shown — deep OTM beyond the ±8 grid: {noNS(b?.not_shown?.deep_otm ?? 'a later batch')} · flush?: {noNS(b?.not_shown?.flush ?? 'a draft')}</text>
        <text x={XL - 5} y={mid + 4} textAnchor="end">ΔOI</text>
        <line x1={XL} y1={mid} x2={XR} y2={mid} style={{ stroke: 'var(--line2)' }} />
        {!grid && <text x={XL + 6} y={A1 - 4} style={{ fill: 'var(--caution)' }}>could not check — no minute grid read yet</text>}
        {bars.map((x) => {
          const X = xOf(x.s0), w = Math.max(1, bw / 2 - 0.8)
          const clip = Math.abs(x.dc) > bmax || Math.abs(x.dp) > bmax
          return (
            <g key={x.s0}>
              <title>{`${hh(x.s0)}–${hh(Math.min(x.s0 + 4, LAST_M))}: CE ${sL(x.dc)} · PE ${sL(x.dp)} [M]${clip ? ' (clipped: the opening bar)' : ''}`}</title>
              <rect x={X + 0.5} y={x.dc >= 0 ? mid - sc(x.dc) : mid} width={w} height={Math.abs(sc(x.dc))} style={{ fill: 'var(--coral)', fillOpacity: x.dc >= 0 ? 0.7 : 0.3 }} />
              <rect x={X + bw / 2} y={x.dp >= 0 ? mid - sc(x.dp) : mid} width={w} height={Math.abs(sc(x.dp))} style={{ fill: 'var(--teal)', fillOpacity: x.dp >= 0 ? 0.7 : 0.3 }} />
              {clip && <text x={X + bw / 2} y={A0 + 6} textAnchor="middle" style={{ fontSize: 9, fill: 'var(--muted)' }}>↕</text>}
            </g>
          )
        })}
        {['09:15', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'].map((t) => {
          const x = xOf(mm(t))
          return <g key={t}><line x1={x} y1={A1 + 2} x2={x} y2={A1 + 5} style={{ stroke: 'var(--line2)' }} /><text x={x} y={H - 5} textAnchor="middle" style={{ fontSize: 9.5 }}>{t}</text></g>
        })}
        {b?.asof && <line x1={xOf(mm(b.asof) + 1)} y1={A0} x2={xOf(mm(b.asof) + 1)} y2={A1} style={{ stroke: 'var(--text2)', opacity: 0.4 }} />}
      </svg>
    </div>
  )
}

/* ── 7: the fold staircase as moves; the whole day behind a button ─────────── */
function moveRow(f: Fold, first: Fold | null | undefined) {
  const isFirst = !!first && first.k === f.k && first.side === f.side && first.t === f.t
  const txt = `${f.side} ${f0(f.k)} folded — high ${sL(f.high)} at ${f.high_at} @ ${f1(f.spot_high)} · §1d unwinding ${f.t}${ok(f.spot_fold) ? ` @ ${f1(f.spot_fold)}` : ''}${ok(f.off) ? `, ${pct(f.off)} off` : ''}${isFirst ? ' · FIRST FOLD, stamped once' : ''}`
  return (
    <div className="mv" key={`${f.side}${f.k}${f.t}`}>
      <span className="num t2">{f.t}</span>
      <span className={hue(f.side)} style={{ textAlign: 'center' }}>{isFirst ? '★' : '▨'}</span>
      <span className="x" title={txt}>{txt} <Tg t={f.tag} /></span>
    </div>
  )
}

function Moves({ b, onLog }: { b: Board | null; onLog: () => void }) {
  const fs = b?.ok ? b.folds ?? [] : []
  return (
    <div className="panel moves">
      <div className="mvh"><span className="cap">MOVES · the folds, the last 4 of {fs.length} so far</span>
        <button className="btn" onClick={onLog} disabled={!fs.length}>open the full log ▸</button></div>
      {!b?.ok ? null : fs.length ? fs.slice(-4).map((f) => moveRow(f, b.first))
        : <div className="s11 muted">{b.folds_why ?? 'no fold yet today — checked, none'}</div>}
    </div>
  )
}

function FullLog({ b, onClose }: { b: Board | null; onClose: () => void }) {
  const fs = b?.ok ? b.folds ?? [] : []
  return (
    <div className="log" role="dialog" aria-label="the full log of folds">
      <div className="mvh"><span className="cap">THE FULL LOG · {b?.idx} · {b?.day} · {fs.length} folds to {b?.asof}</span>
        <button className="btn" onClick={onClose}>close ✕</button></div>
      <div className="body">{fs.map((f) => moveRow(f, b?.first))}</div>
    </div>
  )
}
