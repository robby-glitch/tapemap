import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { usePalette, rgbOf } from '../theme'
import type { IndexKey } from '../data'
import { useTape } from '../trade/tape'
import type { TapeBarRow } from '../trade/tape'

/* ── BOARD ────────────────────────────────────────────────────────────────────
   The whole chess board on one screen, the mockup of 2026-09-22
   (docs/mockups/board-2026-09-22.html) fed by what the server ALREADY serves:

     /api/frame    head.gate · where (px, vwap, σ, z, zones) · trapped (writers,
                   window, pace, fut_oi, gear) · walls.rows · tape.events ·
                   setup (state, confirm, tells) · breadth (written/unwound)
     /api/tape     5-min bars with delta + cvd · ux (λ, runs, agreement)
     /api/vpin     toxicity gauge
     /api/drag     the buyer's tax
     /api/signals  the zone/5c rows and the engine context stamped on them
                   (gamma regime, IV, IVR, OI totals, 30m range)

   Nothing here is computed on the server's behalf. The PLAYS panel lights the
   conditions the board can READ off those fields and says how many of N are
   lit; below N it says REFUSE. That count is a description of the fields, not
   a signal, and no hit rate, win rate or expectancy is reachable from here.
   Every hole is a grey PATA NAHI with the server's own reason — the P0 of the
   last desk was a gate that said GO while its inputs were holes.

   ponytail: one file, inline styles like the other tabs, 30 s polls that die
   with the tab. The per-bar READ line is factual (delta, volume vs the day's
   median, events at that bar, fires) and never a verdict.
─────────────────────────────────────────────────────────────────────────────── */

type Gate = { level?: string | null; reason?: string | null; would_be?: string | null; tag?: string }
type Frame = {
  ok: boolean; ts?: string; day?: string; error?: string; why?: string | null
  head?: { symbol?: string | null; expiry?: string | null; expiry_why?: string | null; dte?: number | null; started?: string | null; gate?: Gate }
  where?: {
    px?: number | null; vwap?: number | null; sigma?: number | null; z?: number | null; warm?: boolean; warm_at?: string
    buy_zone?: [number, number] | null; sell_zone?: [number, number] | null; edge?: unknown; zone_why?: string | null
    open?: number | null; high?: Extreme | null; low?: Extreme | null; bars_why?: string | null
  }
  trapped?: {
    writers?: { side: string; worst: { k: number; pain: number; conf: unknown } | null; ce_chg: number; pe_chg: number } | null; writers_why?: string | null
    window?: { t0: string; t1: string; minutes: number; ce: number; pe: number } | null; window_why?: string | null
    pace?: { ce: number; pe: number } | null; pace_why?: string | null
    fut_oi?: { d_oi: number; d_px: number } | null; fut_oi_why?: string | null
    gear?: string | null; gear_why?: string | null
  }
  walls?: { rows?: WallRow[]; oi_why?: string | null }
  tape?: { events?: Ev[]; aggressor?: { side?: string | null; rank?: number | null } | null; aggressor_why?: string | null }
  events?: Ev[]
  setup?: { state?: string; state_why?: string | null; side?: string; confirm?: { value?: string; why?: string | null }; tells?: { name: string; predicate: string }[]; gate?: FadeGate | null }
  breadth?: {
    written_ce?: number | null; unwound_ce?: number | null; written_pe?: number | null; unwound_pe?: number | null; counts_why?: string | null
    advancing?: number | null; retreating?: number | null; regime?: string | null; pinned?: boolean | null; regime_why?: string | null
  }
  coverage?: { book?: { why?: string | null; drain_why?: string | null; failed?: number } }
}
type WallRow = { kind: string; p: number; d?: number | null; oi?: number | null; chg?: number | null; state?: string | null; tests?: number | null; since?: string | null; strike?: number | null; last_outcome?: string | null }
type Extreme = { p: number; t: string }
/** `at` is an OBJECT on the wire — {kind, label} — not a string. Rendering it
 *  raw printed "[object Object]" on the first live day (2026-09-22). */
type Ev = { t: string; kind: string; p: number | null; at?: { kind: string; label: string } | null; side?: number | null }
type Vpin = { ok: boolean; state?: Record<string, { vpin: number | null; pct: number | null; buckets: number; fill: number }>; backfill?: { why?: string } }
type Drag = { ok: boolean; indices?: Record<string, { frac?: number | null; drag?: number | null; owed?: number | null; paid?: number | null; strike?: number | null; right_side?: string | null; anchor_why?: string | null }> }
type SigRow = {
  day?: string | null; t?: string | null; side?: string | null; band?: string | null; rule?: string | null; kind?: 'arm' | null; px?: number | null; trigger?: string | null
  /** §1d's fade gate AS AT the row's own bar (trigger_log._gate_at). Drawn, never used to drop a row. */
  gate?: { legal?: boolean | null; why?: string | null; veto?: boolean | null } | null
  oi_call?: number | null; oi_put?: number | null; oi_why?: string | null
  gamma?: { regime?: string | null; iv_ce?: number | null; iv_pe?: number | null } | null
  ctx?: { verdict?: string | null; line?: string | null; breadth?: string | null; ivr_ce?: number | null; ivr_pe?: number | null; rng30?: number | null; inside1?: number | null; pin?: { k?: number | null; dist?: number | null } | null; flips?: string[] | null } | null
}
type Signals = { ok: boolean; error?: string; rows?: SigRow[]; five_c?: { rows?: SigRow[] }; legacy?: { rows?: SigRow[] } }
/** `/api/oihist`. THE FRONTS ARE COMPUTED ON THE SERVER (`fronts.py`,
 *  research-findings §1d) and only read here — the rule must not exist twice,
 *  in two languages, the way the gear once did. That route is served straight
 *  out of the chain poller and never touches the extension, so this read
 *  survives a dead GoCharting tab. */
type OiHist = {
  ok: boolean; why?: string | null
  fronts?: Front[] | null; fronts_why?: string | null; broke?: Front | null
}

/** One front: a strike/side the operator would actually be short. */
type Front = {
  k: number; side: 'CE' | 'PE'; oi: number | null
  chg: number; peak: number; peak_at: string; from_peak: number; slope: number
  state: 'BUILDING' | 'STALLED' | 'UNWINDING'; tag?: string
}

/** §1d's answer for one bar: may this band be faded at all? Distinct from the
 *  `Gate` above, which is the seller's TRADE/HALF SIZE/NO NEW RISK gate on the
 *  frame's head — two different questions that must not share a name. */
type FadeGate = {
  legal: boolean | null; why: string | null; side?: string | null
  defender?: 'CE' | 'PE' | null; front?: Front | null; veto?: boolean | null; tag?: string
}

function useJson<T>(url: string, everyMs: number): { data: T | null; why: string | null } {
  const [data, setData] = useState<T | null>(null)
  const [why, setWhy] = useState<string | null>('abhi padha ja raha hai')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(url); const j = await r.json()
        if (!alive) return
        setData(j as T); setWhy(null)
      } catch (e) { if (alive) { setData(null); setWhy(`backend ne jawab nahi diya (${String(e)})`) } }
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, everyMs)
    return () => { alive = false; window.clearInterval(id) }
  }, [url, everyMs])
  return { data, why }
}

const OPEN = 9 * 60 + 15, CLOSE = 15 * 60 + 30
const mins = (t: string | null | undefined) => { const m = /^(\d{1,2}):(\d{2})/.exec(t ?? ''); return m ? +m[1] * 60 + +m[2] : null }
const hhmm = (v: number) => `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`
const tHM = (ms: number) => { const s = (Math.floor(ms / 1000) + 19800) % 86400; return hhmm(Math.floor(s / 60)) }
const n0 = (v: number | null | undefined, d = 0) => (v == null || !Number.isFinite(v) ? null : v.toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d }))
const lakh = (v: number | null | undefined) => (v == null ? null : `${(v / 1e5).toFixed(1)}L`)
/** Signed lakhs — an OI change is only readable with its sign on it. */
const signL = (v: number | null | undefined) => (v == null ? '—' : `${v > 0 ? '+' : ''}${(v / 1e5).toFixed(1)}L`)
const pct = (v: number | null | undefined) => (v == null ? null : `${Math.round(v * 100)}%`)

type Lamp = { name: string; on: boolean | null; why?: string }

export default function BoardTab({ index }: { index: IndexKey }) {
  const pal = usePalette()
  const wash = (token: string, a: number) => `rgba(${rgbOf(token)},${a})`
  const buy = '#3CC8A8', sell = '#E86A5A'
  const frame = useJson<Frame>(`/api/frame?idx=${index}`, 15000)
  const vpin = useJson<Vpin>(`/api/vpin?idx=${index}`, 30000)
  const drag = useJson<Drag>(`/api/drag?idx=${index}`, 30000)
  const sigs = useJson<Signals>(`/api/signals?rule=all&kind=all&idx=${index}`, 30000)
  const oih = useJson<OiHist>(`/api/oihist?idx=${index}`, 30000)
  const tape = useTape(index)

  // THE CLOCK IS THE MACHINE'S, NOT THE FRAME'S. Reading "now" off the last
  // posted frame is how a dead extension renders as a calm market: on
  // 2026-09-22 the extension posted once at 09:17, stamped with MONDAY's
  // session, and stopped — every panel below would have drawn that as live.
  const [nowMs, setNowMs] = useState(() => Date.now())
  useEffect(() => { const id = window.setInterval(() => setNowMs(Date.now()), 15000); return () => window.clearInterval(id) }, [])
  const nowM = Math.floor(((nowMs + 19800e3) % 86400e3) / 60000)
  const today = tape.reply?.day ?? new Date(nowMs + 19800e3).toISOString().slice(0, 10)

  // The frame is the EXTENSION's document. It counts as "now" only if it is
  // today's session and recent; otherwise it is named stale and every answer
  // built on it becomes a hole with that reason. (House rule: "we could not
  // check" must never render as "we checked and found nothing".)
  const fRaw = frame.data?.ok ? frame.data : null
  const frameAge = fRaw?.ts ? nowM - (mins(fRaw.ts) ?? nowM) : null
  const staleWhy = !fRaw
    ? (frame.data?.why ?? frame.why ?? 'extension ne abhi tak post nahi kiya')
    : fRaw.day !== today
      ? `extension ka aakhri frame ${fRaw.day} ${fRaw.ts} ka hai — aaj ka nahi (GoCharting tab F5 karo)`
      : frameAge != null && frameAge > 5
        ? `extension ka aakhri frame ${fRaw.ts} ka hai, ${frameAge}m purana (GoCharting tab F5 karo)`
        : null
  const f = staleWhy ? null : fRaw
  const staleShort = staleWhy ? (fRaw ? 'extension stale' : 'extension ne post nahi kiya') : null

  // GoCharting's ladder when it is posting, else the Upstox tape — which is a
  // SECOND source for the same bars (spec 2026-09-20), not a placeholder.
  const gcBars: TapeBarRow[] = tape.reply?.bars ?? []
  const ux = tape.reply?.ux ?? null
  const uxBars = (ux?.bars ?? []) as unknown as TapeBarRow[]
  const usingUx = gcBars.length === 0 && uxBars.length > 0
  const bars: TapeBarRow[] = usingUx ? uxBars : gcBars
  const forming = (usingUx ? (ux?.forming as unknown as TapeBarRow | null) : tape.reply?.forming) ?? null
  const barsSrc = usingUx ? 'Upstox tape (ux) [I] — GoCharting post nahi kar raha' : gcBars.length ? 'GoCharting ladder [M]' : null
  const barsWhy = bars.length ? null : (tape.why || tape.reply?.ladder_why || ux?.why || 'abhi koi bar nahi')

  // the day's signal rows, newest first; the newest carries the engine context
  const rows = useMemo(() => {
    const j = sigs.data
    const all = [...(j?.rows ?? []), ...(j?.five_c?.rows ?? []), ...(j?.legacy?.rows ?? [])]
    const seen = new Set<string>(); const out: SigRow[] = []
    for (const r of all) {
      if (!r || (today && r.day !== today) || r.t == null) continue
      const k = `${r.t}|${r.side}|${r.band}|${r.rule}|${r.kind ?? 'entry'}`
      if (seen.has(k)) continue; seen.add(k); out.push(r)
    }
    return out.sort((a, b) => (mins(b.t) ?? 0) - (mins(a.t) ?? 0))
  }, [sigs.data, today])
  const latest = rows[0] ?? null
  const ctx = latest?.ctx ?? null

  const events: Ev[] = (f?.tape?.events ?? f?.events ?? []).filter(e => e && e.t)
  // The frame publishes EVERY level it knows — 51 rows on 2026-09-22, out to
  // strikes 380 points away. A board shows the ones price can reach today:
  // nearest by the row's own distance `d`, and the far tail stays one click
  // away on the War tab rather than being dumped here.
  const WALLS_SHOWN = 14
  const allWalls: WallRow[] = f?.walls?.rows ?? []
  const wallPx = f?.where?.px ?? (forming ?? bars[bars.length - 1])?.c ?? null
  const walls: WallRow[] = [...allWalls]
    .sort((a, b) => Math.abs(a.d ?? (wallPx == null ? 0 : a.p - wallPx)) - Math.abs(b.d ?? (wallPx == null ? 0 : b.p - wallPx)))
    .slice(0, WALLS_SHOWN)
    .sort((a, b) => b.p - a.p)
  // ── THE FRONTS — the operator's own rule, stated 2026-09-22 ────────────────
  //
  //   "hamesha read nearest ATM pe rehni chahiye. 23700 PE writers are
  //    irrelevant, wahan pe hedging ke liye positions banate hain, chhote
  //    seller premium ke liye. Poora 1.5L kaun dega per lot. Hamesha check
  //    karo the strike with most of OI and second best on BOTH sides, and
  //    always check WHICH SIDE STOPS FIRST increasing their positions and
  //    then unwinding."
  //
  // `frame.trapped.writers` does not answer this: it takes max(pain) over
  // every leg and on this morning returned PE 23700 at conf "low" — a strike
  // nobody carries margin on — while the front that actually broke was PE
  // 23400, whose build peaked at 10:19, one minute before a 105-point drop.
  // So: nearest strikes to spot, top two by ABSOLUTE OI per side, and each
  // one's own build → stall → unwind read off its OI-change series.
  const SLOPE_MARKS = 15      // only to label the slope column; the rule lives in fronts.py
  const fronts: Front[] = oih.data?.fronts ?? []
  const frontsWhy = fronts.length ? null : (oih.data?.fronts_why ?? oih.why ?? 'oihist ne jawab nahi diya')
  const frontOf = (side: 'CE' | 'PE') => fronts.find(x => x.side === side) ?? null
  const sideState = (side: 'CE' | 'PE') => frontOf(side)?.state ?? null
  // WHO BROKE FIRST -- also the server's answer, not a second implementation.
  const broke: Front | null = oih.data?.broke ?? null
  // §1d's verdict for the setup on screen. The frame computes it with the same
  // function; a stale frame makes it a hole like every other frame-borne field.
  const fadeGate: FadeGate | null = f?.setup?.gate ?? null

  const tr = f?.trapped
  const br = f?.breadth
  const gate = f?.head?.gate
  const vs = vpin.data?.state ? Object.values(vpin.data.state)[0] : null
  const dg = drag.data?.indices?.[index] ?? null
  const lam = ux?.impact ?? null

  // ── the board's read of the plays: N lamps, lit / unlit / hole ─────────────
  const medVol = useMemo(() => { const v = bars.map(b => b.vol).filter(x => x > 0).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : null }, [bars])
  const last = bars[bars.length - 1] ?? null
  const recentEv = events.filter(e => { const m = mins(e.t); return m != null && nowM - m <= 15 })
  const absorbedAtEdge = recentEv.some(e => e.kind === 'absorption' && e.at)
  // BUILDING on BOTH near-ATM fronts — not the whole-chain written/unwound
  // counts, which include the far hedging strikes she rules out.
  const bothBuilding = fronts.length ? sideState('CE') === 'BUILDING' && sideState('PE') === 'BUILDING' : null
  // THE REGIME COMES FROM BREADTH, NOT FROM `trapped.gear`. `_book_for` passes
  // `senses: None` on purpose (server.py: the /api/senses reading is assembled
  // in that handler and must not be re-derived), so `trapped.gear` is a
  // STRUCTURAL hole — a lamp on it could never light. breadth.regime is the
  // per-index dealer regime the frame actually fills: FLOOR / CEILING /
  // AMPLIFIED-UP / AMPLIFIED-DOWN / PINNED / NEUTRAL, tagged [I].
  const regimeWord = br?.regime ?? null
  const pinned = br?.pinned ?? null
  const fuelSide = broke?.side ?? null
  const drainOk = fronts.length ? broke?.state === 'UNWINDING' : null
  // IGNITION MUST NOT WAIT FOR THE BAR TO CLOSE. Reading only the last CLOSED
  // bar made this lamp structurally one bar late: at 10:41 on 2026-09-22, mid
  // cascade, the last closed bar was 10:35 at 1.0x median while the bar then
  // forming did 1549 (2.5x). By the time it lit, minutes 1-5 were gone. So the
  // forming bar is projected to a full interval from the minutes it has run.
  const formingRate = useMemo(() => {
    if (!forming) return null
    const start = mins(tHM(forming.t)); if (start == null) return null
    const elapsed = Math.min(Math.max(nowM - start, 1), 5)
    return forming.vol * (5 / elapsed)
  }, [forming, nowM])
  const hotVol = Math.max(last?.vol ?? 0, formingRate ?? 0)
  const ignition = medVol ? hotVol >= 2 * medVol : null
  const zoneTouched = f?.setup?.state ? ['ARMED', 'TRIGGERED', 'IN_TRADE'].includes(f.setup.state) : null
  const setupSide = f?.setup?.side === 'sell' ? 'sell' : 'buy'

  const plays: { name: string; sub: string; lamps: Lamp[]; note: string }[] = [
    { name: 'S3 SELL premium', sub: 'wings on · 60–70% take', note: 'legal only in PIN with both books building',
      lamps: [
        { name: 'regime PINNED', on: pinned, why: br?.regime_why ?? staleShort ?? undefined },
        { name: `dono top fronts building${frontOf('CE') && frontOf('PE') ? ` (CE ${frontOf('CE')!.k} · PE ${frontOf('PE')!.k})` : ''}`, on: bothBuilding, why: fronts.length ? undefined : (oih.why ?? 'oihist nahi aayi') },
        { name: 'VPIN low', on: vs?.pct != null ? vs.pct < 0.5 : null, why: vs ? `${vs.buckets} buckets` : vpin.why ?? undefined },
        { name: 'gate TRADE', on: gate?.level ? gate.level === 'TRADE' : null, why: gate?.reason ?? staleShort ?? undefined },
        { name: 'edges absorbed', on: events.length ? absorbedAtEdge : null, why: f?.tape?.aggressor_why ?? staleShort ?? undefined },
      ] },
    { name: `S2 BUY cascade${fuelSide ? ` ${fuelSide === 'CE' ? 'CE' : 'PE'}` : ''}`, sub: 'min 1–5 · exit when the drain stops', note: 'fuel · ignition · drain — refuse at 2/3, fakes die here',
      lamps: [
        { name: broke ? `fuel: ${broke.side} ${broke.k} peaked ${broke.peak_at}` : 'fuel: a near-ATM front that stopped building', on: fronts.length ? !!broke : null, why: fronts.length ? undefined : (oih.why ?? 'oihist nahi aayi') },
        { name: `ignition: vol ${medVol ? (hotVol / medVol).toFixed(1) : '—'}× median${formingRate && formingRate > (last?.vol ?? 0) ? ' (banta hua bar)' : ''}`, on: ignition, why: barsWhy ?? undefined },
        { name: broke ? `drain: ${broke.side} ${broke.k} ${signL(broke.from_peak)} peak se` : 'drain: that side giving OI back', on: drainOk, why: fronts.length ? undefined : (oih.why ?? 'oihist nahi aayi') },
      ] },
    { name: `S1 FADE ${setupSide === 'sell' ? 'u2' : 'd2'}`, sub: 'stop past the sweep · target VWAP', note: 'zone touched · absorption at the edge · that side building · PIN',
      lamps: [
        // THE LAST TWO ARE §1d, THE PRE-REGISTERED FADE GATE, and they are the
        // server's answer, not a second opinion assembled here. "regime
        // PINNED" used to sit in this row; it was my own stand-in for her
        // unanswered "if market condition is right", and §1d replaces it with
        // the rule she actually stated. Keeping both would make the board
        // stricter than the rule being measured.
        { name: 'zone touched', on: zoneTouched, why: f?.setup?.state_why ?? f?.where?.zone_why ?? staleShort ?? undefined },
        { name: 'absorption at the edge', on: events.length ? absorbedAtEdge : null, why: f?.tape?.aggressor_why ?? staleShort ?? undefined },
        { name: fadeGate?.why ? `defender: ${fadeGate.why}` : 'defender still building', on: fadeGate ? (fadeGate.veto ? null : fadeGate.legal) : null, why: fadeGate ? undefined : (staleShort ?? frontsWhy ?? undefined) },
        { name: 'engine has not said NO FADE', on: fadeGate?.veto == null ? null : !fadeGate.veto, why: fadeGate?.veto == null ? (staleShort ?? 'engine plays not on the frame') : undefined },
      ] },
  ]
  const full = plays.filter(p => p.lamps.every(l => l.on === true))
  const playNow = full.length ? full.map(p => p.name).join(' · ') : 'SKIP'

  // ── who is trapped, one sentence, or the hole ───────────────────────────────
  const trappedLine = (() => {
    // Read off the FRONTS, not off frame.trapped — and off /api/oihist, which
    // the extension is not in the path of, so this answer survives a dead tab.
    if (!fronts.length) return { big: 'PATA NAHI', sub: oih.data?.why ?? oih.why ?? 'per-strike OI history nahi aayi' }
    const each = fronts.map(x => `${x.side} ${x.k} ${x.state.toLowerCase()} (${signL(x.chg)}, peak ${signL(x.peak)} @${x.peak_at})`).join(' · ')
    if (!broke) return { big: 'Dono taraf abhi likh rahe hain', sub: `koi front peak se nahi tuta [M] · ${each}` }
    const verb = broke.state === 'UNWINDING' ? 'unwind kar rahe hain' : 'build rok chuke hain'
    const other = fronts.find(x => x.side !== broke.side && x.state === 'BUILDING')
    return {
      big: `${broke.side} ${broke.k} writers ${verb} — pehle ruke ${broke.peak_at} pe`,
      sub: `peak ${signL(broke.peak)} @${broke.peak_at}, ab ${signL(broke.chg)} (${signL(broke.from_peak)} peak se, ${SLOPE_MARKS}m ka rukh ${signL(broke.slope)}) [M]`
        + (other ? ` · doosri taraf ${other.side} ${other.k} abhi bhi likh raha (${signL(other.slope)})` : '')
        + ` · ${each}`,
    }
  })()

  // ── read feed: one factual line per closed bar, newest first ───────────────
  const feed = useMemo(() => {
    const out: { t: string; line: string; tag: string }[] = []
    const byBar = (t: number) => { const a = tHM(t); const m = mins(a)!; return { a, ev: events.filter(e => { const x = mins(e.t); return x != null && x >= m && x < m + 5 }), sg: rows.filter(r => { const x = mins(r.t); return x != null && x >= m && x < m + 5 }) } }
    for (let i = bars.length - 1; i >= 0; i--) {
      const b = bars[i]; const { a, ev, sg } = byBar(b.t)
      const parts = [`Δ ${b.delta > 0 ? '+' : ''}${b.delta}`, `vol ${b.vol}${medVol ? ` (${(b.vol / medVol).toFixed(1)}×)` : ''}`, `${b.o} → ${b.c}`]
      if (b.stacks?.length) parts.push(`stack ${b.stacks.map(s => `${s.side} ${s.low}–${s.high}`).join(', ')}`)
      if (b.unfinished_high) parts.push('unfinished high'); if (b.unfinished_low) parts.push('unfinished low')
      for (const e of ev) parts.push(`${e.kind}${e.at?.label ? ` ${e.at.label}` : ''}${e.p != null ? ` @${e.p}` : ''}`)
      // §1d on the face: an illegal fade is a tap, not a trade -- it still prints, with the gate's reason
      for (const s of sg) {
        // a row written before the gate existed carries no field: not stamped, which is not "could not read"
        const g = s.gate?.legal, stamped = s.gate !== undefined
        const word = s.kind === 'arm' ? 'ARM' : g === false ? 'no trade ·' : 'FIRE'
        const gate = !stamped ? '' : g === true ? ' · legal' : g === false ? ` · NO FADE — ${s.gate?.why ?? 'defender not building'}` : ' · gate ?'
        parts.push(`${word} ${s.side} ${s.band} (${s.rule})${s.px != null ? ` @${s.px}` : ''}${gate}`)
      }
      out.push({ t: a, line: parts.join(' · '), tag: 'M' })
    }
    return out
  }, [bars, events, rows, medVol])

  // ── tape strip geometry ─────────────────────────────────────────────────────
  const W = 1000, H = 250, PL = 8, PR = 60, PT = 8, PH = 176, CH = 52
  const t1 = Math.min(Math.max(nowM + 60, 11 * 60 + 30), CLOSE)
  const X = (m: number) => PL + (m - OPEN) / (t1 - OPEN) * (W - PL - PR)
  const allBars = forming ? [...bars, forming] : bars
  const zoneVals = [f?.where?.buy_zone?.[0], f?.where?.buy_zone?.[1], f?.where?.sell_zone?.[0], f?.where?.sell_zone?.[1]].filter((x): x is number => x != null)
  const lo = allBars.length ? Math.min(...allBars.map(b => b.l), ...zoneVals) - 6 : 0
  const hi = allBars.length ? Math.max(...allBars.map(b => b.h), ...zoneVals) + 6 : 1
  const Y = (p: number) => PT + (hi - p) / (hi - lo) * PH
  const bw = Math.max((W - PL - PR) / ((t1 - OPEN) / 5) - 3, 2)
  const cvds = bars.map(b => b.cvd); const cmin = Math.min(...cvds, 0), cmax = Math.max(...cvds, 0)
  const c0 = PT + PH + 16; const CY = (v: number) => c0 + (cmax - v) / Math.max(cmax - cmin, 1) * (CH - 6) + 3
  const glyph: Record<string, string> = { absorption: '◆', initiative: '▲', vacuum: '○', trap: '✕', exhaustion: '▽', climax: '✦' }

  // ── styles ──────────────────────────────────────────────────────────────────
  const line = `1px solid ${pal.border}`
  const S: Record<string, CSSProperties> = {
    root: { display: 'grid', gridTemplateRows: 'auto auto 1fr', height: 'calc(100vh - 96px)', minHeight: 720, color: pal.textPrimary, fontSize: 13 },
    rail: { display: 'flex', alignItems: 'center', gap: 18, padding: '6px 14px', borderBottom: line, fontSize: 11, color: pal.textMuted },
    answer: { display: 'grid', gridTemplateColumns: '1.1fr 1.9fr 1fr', borderBottom: line },
    cell: { padding: '10px 14px', borderRight: line },
    lbl: { fontSize: 11, color: pal.textMuted, letterSpacing: '.06em', textTransform: 'uppercase' },
    big: { fontSize: 22, fontWeight: 600, margin: '2px 0 4px' },
    sub: { fontSize: 11, color: pal.textMuted },
    main: { display: 'grid', gridTemplateColumns: '1fr 560px', minHeight: 0 },
    panel: { padding: '8px 12px', minHeight: 0, borderBottom: line },
    ph: { display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4 },
    mtag: { fontSize: 10, color: pal.accent }, itag: { fontSize: 10, color: pal.textMuted, border: `1px dashed ${pal.textMuted}`, padding: '0 4px' },
    row: { display: 'grid', gridTemplateColumns: '44px 24px 1fr', gap: 8, padding: '5px 0', borderBottom: line, fontSize: 12, lineHeight: 1.35, fontVariantNumeric: 'tabular-nums' },
    hole: { color: pal.textMuted },
  }
  const holeSpan = (why: string | null | undefined) => <span style={S.hole}>PATA NAHI{why ? ` · ${why}` : ''}</span>
  const kv = (k: string, v: string | null, why?: string | null, tag: 'M' | 'I' = 'M') => (
    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: line, padding: '2px 0', fontSize: 11 }}>
      <span style={{ color: pal.textMuted }}>{k}</span>
      {v == null ? holeSpan(why) : <span style={tag === 'I' ? { fontStyle: 'italic', color: pal.textSecondary } : undefined}>{v} <span style={{ color: pal.textMuted, fontSize: 9 }}>[{tag}]</span></span>}
    </div>)

  const gearWord = regimeWord
  const regimeSub = [
    br?.advancing != null ? `fronts ${br.advancing} advancing / ${br.retreating} retreating [I]` : null,
    latest?.gamma?.regime ? `gamma ${latest.gamma.regime} @${latest.t}${ctx?.pin?.k ? ` · pin ${ctx.pin.k} (${ctx.pin.dist} away)` : ''} [M]` : null,
    f?.setup?.state ? `zone ${f.setup.state} ${f.setup.side}` : null,
  ].filter(Boolean).join(' · ')

  return (
    <div style={S.root}>
      <div style={S.rail}>
        <span style={{ fontSize: 15, color: pal.textPrimary, fontFamily: 'Roboto Mono, monospace' }}>{today} · {hhmm(nowM)}</span>
        <span style={{ fontFamily: 'Roboto Mono, monospace' }}>FUT <b style={{ color: pal.textPrimary }}>{n0(f?.where?.px ?? (forming ?? bars[bars.length - 1])?.c, 1) ?? '—'}</b> · day {n0(f?.where?.low?.p ?? (bars.length ? Math.min(...bars.map(b => b.l)) : null), 0) ?? '—'}{f?.where?.low?.t ? ` @${f.where.low.t}` : ''} – {n0(f?.where?.high?.p ?? (bars.length ? Math.max(...bars.map(b => b.h)) : null), 0) ?? '—'}{f?.where?.high?.t ? ` @${f.where.high.t}` : ''} · z {f?.where?.z ?? '—'} · σ {n0(f?.where?.sigma, 1) ?? '—'} {f?.where?.warm ? '[M]' : `(bands: ${staleWhy ?? f?.where?.zone_why ?? `warm at ${f?.where?.warm_at ?? '09:25'}`})`}</span>
        <span>exp {f?.head?.expiry ?? (f?.head?.expiry_why ? `PATA NAHI · ${f.head.expiry_why}` : '—')}{f?.head?.dte != null ? ` · DTE ${f.head.dte}` : ''}</span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 14 }}>
          <span>gate <b style={{ color: gate?.level === 'PATA NAHI' || !gate ? pal.textMuted : pal.textPrimary }}>{gate?.level ?? 'PATA NAHI'}</b>{gate?.reason ? ` · ${gate.reason}` : ''}</span>
          <span>Upstox tape <b style={{ color: pal.textPrimary }}>{ux?.why ? 'PATA NAHI' : `${uxBars.length} bars · ${ux?.frames_per_s ?? '—'} fr/s`}</b>{ux?.why ? ` · ${ux.why}` : ''}</span>
          <span>extension <b style={{ color: staleWhy ? pal.textMuted : pal.textPrimary }}>{fRaw ? `${fRaw.day} ${fRaw.ts}${frameAge != null && frameAge > 0 ? ` (${frameAge}m purana)` : ''}` : 'koi post nahi'}</b> · GoCharting {gcBars.length} bars</span>
          <span>flat by <b style={{ color: pal.textPrimary }}>15:15</b></span>
        </span>
      </div>

      <div style={S.answer}>
        <div style={S.cell}>
          <div style={S.lbl}>Regime · gear</div>
          <div style={{ ...S.big, ...(gearWord ? {} : S.hole) }}>{gearWord ?? 'PATA NAHI'}</div>
          <div style={S.sub}>{gearWord ? `${pinned ? 'pinned' : 'not pinned'} [I] · ${regimeSub || '—'}` : `${staleWhy ?? br?.regime_why ?? frame.why ?? 'breadth did not build'}${regimeSub ? ` · ${regimeSub}` : ''}`}</div>
        </div>
        <div style={S.cell}>
          <div style={S.lbl}>Who is trapped · now</div>
          <div style={{ ...S.big, ...(trappedLine.big === 'PATA NAHI' ? S.hole : {}) }}>{trappedLine.big}</div>
          <div style={S.sub}>{trappedLine.sub}
            {latest?.oi_call != null && latest?.oi_put != null ? ` · calls ${lakh(latest.oi_call)} vs puts ${lakh(latest.oi_put)} @${latest.t} [M]` : ''}
            {ctx?.ivr_ce != null ? ` · IVR CE ${ctx.ivr_ce} / PE ${ctx.ivr_pe} [M]` : ''}
            {f?.tape?.aggressor?.side ? ` · aggressing: ${f.tape.aggressor.side}${f.tape.aggressor.rank != null ? ` (p${Math.round(f.tape.aggressor.rank * 100)})` : ''} [M]` : (f?.tape?.aggressor_why ? ` · aggressor: ${f.tape.aggressor_why}` : '')}
          </div>
        </div>
        <div style={{ ...S.cell, borderRight: 0 }}>
          <div style={S.lbl}>Play · board's read [I]</div>
          <div style={S.big}>{playNow}</div>
          <div style={S.sub}>{full.length ? 'every lamp lit — the board reads, the trader decides' : plays.map(p => `${p.name.split(' ')[0]} ${p.lamps.filter(l => l.on === true).length}/${p.lamps.length}`).join(' · ') + ' · below full = refuse · S5 logged as a trade'}</div>
        </div>
      </div>

      <div style={S.main}>
        <div style={{ display: 'grid', gridTemplateRows: '262px 1fr', minHeight: 0, borderRight: line }}>
          <div style={S.panel}>
            <div style={S.ph}><span style={{ ...S.lbl, marginRight: 'auto' }}>Tape · 5-min · zones now · walls · events · fires · CVD</span><span style={usingUx ? S.itag : S.mtag}>{barsSrc ?? 'koi source nahi'}</span>{staleWhy ? <span style={S.itag}>zones/walls/events band — {staleWhy}</span> : null}</div>
            {bars.length === 0 ? <div style={{ ...S.hole, padding: 12 }}>{barsWhy}</div> : (
              <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={214} style={{ fontFamily: 'Roboto Mono, monospace', fontSize: 10 }}>
                {f?.where?.sell_zone && <rect x={PL} y={Y(f.where.sell_zone[1])} width={W - PL - PR} height={Math.max(Y(f.where.sell_zone[0]) - Y(f.where.sell_zone[1]), 1)} fill={wash(sell, 0.10)} />}
                {f?.where?.buy_zone && <rect x={PL} y={Y(f.where.buy_zone[1])} width={W - PL - PR} height={Math.max(Y(f.where.buy_zone[0]) - Y(f.where.buy_zone[1]), 1)} fill={wash(buy, 0.12)} />}
                {f?.where?.vwap != null && <line x1={PL} x2={W - PR} y1={Y(f.where.vwap)} y2={Y(f.where.vwap)} stroke={pal.accent} strokeWidth={1.2} />}
                {walls.filter(w => w.p >= lo && w.p <= hi).map((w, i) => (
                  <g key={i}><line x1={PL} x2={W - PR} y1={Y(w.p)} y2={Y(w.p)} stroke={w.kind === 'CE' || w.kind === 'S' ? sell : w.kind === 'PE' || w.kind === 'B' ? buy : pal.accent} strokeWidth={w.kind === 'CE' || w.kind === 'PE' ? 1.4 : 0.8} strokeDasharray={w.kind === 'CE' || w.kind === 'PE' ? undefined : '6 4'} />
                    <text x={W - PR + 4} y={Y(w.p) + 3} fill={pal.textSecondary} fontSize={9}>{w.kind} {n0(w.p, 0)}</text></g>))}
                {allBars.map((b, i) => { const m = mins(tHM(b.t))!; if (m < OPEN || m > t1) return null; const x = X(m); const isF = forming != null && i === allBars.length - 1; const up = b.c >= b.o
                  return <g key={b.t}><line x1={x} x2={x} y1={Y(b.h)} y2={Y(b.l)} stroke={pal.textSecondary} strokeWidth={1} />
                    <rect x={x - bw / 2} y={Y(Math.max(b.o, b.c))} width={bw} height={Math.max(Y(Math.min(b.o, b.c)) - Y(Math.max(b.o, b.c)), 1)} fill={isF ? 'none' : up ? pal.bg : pal.textSecondary} stroke={pal.textSecondary} strokeWidth={1} strokeDasharray={isF ? '2 2' : undefined} /></g> })}
                {events.map((e, i) => { const m = mins(e.t); if (m == null || e.p == null || m > t1) return null; return <text key={i} x={X(m) - 4} y={Y(e.p) - 6} fill={e.at ? pal.accent : pal.textSecondary} fontSize={11}>{glyph[e.kind] ?? '·'}</text> })}
                {rows.filter(r => !r.kind && r.px != null).map((r, i) => { const m = mins(r.t); if (m == null || m > t1) return null; const x = X(m), y = Y(r.px!); const s = r.side === 'SELL'; const off = s ? -10 : 10
                  // §1d: legal = the full mark; NOT legal = hollow grey "no fade"; gate unread = dashed with "?"
                  const stamped = r.gate !== undefined, g = stamped ? r.gate?.legal : true, col = g === false ? pal.textMuted : s ? sell : buy
                  return <g key={i}><title>{g === false ? `no fade — ${r.gate?.why ?? ''}` : g == null ? 'gate ? — not read' : 'fade gate legal'}</title>
                    <polygon points={`${x - 5},${y + off} ${x + 5},${y + off} ${x},${y}`} fill={g === false ? 'none' : col} stroke={col} strokeWidth={1.2} strokeDasharray={g == null ? '2 2' : undefined} />
                    <text x={x + 7} y={y + (s ? -8 : 12)} fill={col} fontSize={9}>{r.t} {g === false ? 'no fade' : `${r.side} ${r.band}`}{g == null ? ' ?' : ''}</text></g> })}
                <line x1={X(Math.min(nowM, t1))} x2={X(Math.min(nowM, t1))} y1={PT} y2={PT + PH + CH + 10} stroke={wash(pal.textPrimary, 0.35)} strokeDasharray="2 3" />
                {['09:15', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'].map(h => { const m = mins(h)!; return m <= t1 ? <text key={h} x={X(m)} y={PT + PH + 12} fill={pal.textMuted} fontSize={9} textAnchor="middle">{h}</text> : null })}
                <line x1={PL} x2={W - PR} y1={c0} y2={c0} stroke={wash(pal.textPrimary, 0.08)} />
                <polyline points={bars.map(b => `${X(mins(tHM(b.t))!)},${CY(b.cvd)}`).join(' ')} fill="none" stroke={buy} strokeWidth={1.3} />
                {bars.length > 0 && <text x={W - PR + 4} y={CY(bars[bars.length - 1].cvd) + 3} fill={pal.textSecondary} fontSize={9}>CVD {bars[bars.length - 1].cvd > 0 ? '+' : ''}{bars[bars.length - 1].cvd}</text>}
              </svg>)}
          </div>
          <div style={{ ...S.panel, overflow: 'auto', borderBottom: 0 }}>
            <div style={S.ph}><span style={{ ...S.lbl, marginRight: 'auto' }}>Read · one line per closed bar · latest first</span><span style={S.mtag}>[M] delta, volume vs the day's median, events, fires — facts, never a verdict</span></div>
            {feed.length === 0 ? <div style={S.hole}>{barsWhy ?? 'no closed bar yet'}</div> : feed.map(r => (
              <div key={r.t} style={S.row}><span style={{ color: pal.textMuted }}>{r.t}</span><span style={{ fontSize: 10, color: pal.accent }}>[{r.tag}]</span><span>{r.line}</span></div>))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', minHeight: 0 }}>
          <div style={S.panel}>
            <div style={S.ph}><span style={{ ...S.lbl, marginRight: 'auto' }}>Fronts · near-ATM · most OI and second best, dono taraf</span><span style={S.mtag}>[M] per-minute OI · build → stall → unwind</span></div>
            {fronts.length === 0 ? <div style={{ ...S.hole, marginBottom: 8 }}>PATA NAHI · {frontsWhy}</div> : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5, fontVariantNumeric: 'tabular-nums', marginBottom: 8 }}>
                <thead><tr>{['front', 'oi', 'ab', 'peak', 'peak se', `${SLOPE_MARKS}m`, 'state'].map(h => <th key={h} style={{ fontWeight: 500, color: pal.textMuted, fontSize: 10, textAlign: 'left', padding: '2px 6px' }}>{h}</th>)}</tr></thead>
                <tbody>{fronts.map(x => { const col = x.side === 'CE' ? sell : buy; const isBroke = broke != null && broke.k === x.k && broke.side === x.side
                  return <tr key={`${x.side}${x.k}`} style={{ borderTop: line, background: isBroke ? wash(pal.accent, 0.08) : undefined }}>
                    <td style={{ padding: '3px 6px', color: col, boxShadow: `inset 3px 0 0 ${col}` }}>{x.side} {x.k}</td>
                    <td style={{ padding: '3px 6px' }}>{lakh(x.oi) ?? '—'}</td>
                    <td style={{ padding: '3px 6px' }}>{signL(x.chg)}</td>
                    <td style={{ padding: '3px 6px', color: pal.textMuted }}>{signL(x.peak)} @{x.peak_at}</td>
                    <td style={{ padding: '3px 6px', color: x.from_peak < 0 ? col : pal.textMuted }}>{signL(x.from_peak)}</td>
                    <td style={{ padding: '3px 6px', color: x.slope < 0 ? col : pal.textMuted }}>{signL(x.slope)}</td>
                    <td style={{ padding: '3px 6px', fontWeight: x.state === 'BUILDING' ? 400 : 500, color: x.state === 'BUILDING' ? pal.textMuted : col }}>{x.state}</td>
                  </tr> })}</tbody>
              </table>)}
            <div style={S.ph}><span style={{ ...S.lbl, marginRight: 'auto' }}>Walls · breadth</span><span style={S.mtag}>{allWalls.length > walls.length ? `[M] nearest ${walls.length} of ${allWalls.length} — rest on War` : '[M] from the chain'}</span></div>
            {walls.length === 0 ? <div style={S.hole}>PATA NAHI · {staleWhy ?? f?.walls?.oi_why ?? frame.why ?? 'walls not answered'}</div> : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5, fontVariantNumeric: 'tabular-nums' }}>
                <thead><tr>{['side', 'price', 'oi', 'chg', 'state', 'tests', 'since', 'last'].map(h => <th key={h} style={{ fontWeight: 500, color: pal.textMuted, fontSize: 10, textAlign: 'left', padding: '2px 6px' }}>{h}</th>)}</tr></thead>
                <tbody>{walls.map((w, i) => { const isCe = w.kind === 'CE' || w.kind === 'S'; const col = isCe ? sell : w.kind === 'PE' || w.kind === 'B' ? buy : pal.accent; const cover = (w.chg ?? 0) < 0
                  return <tr key={i} style={{ borderTop: line, background: cover ? `repeating-linear-gradient(135deg, transparent 0 5px, ${wash(pal.textPrimary, 0.05)} 5px 7px)` : undefined }}>
                    <td style={{ padding: '3px 6px', color: col, boxShadow: `inset 3px 0 0 ${col}` }}>{w.kind}</td><td style={{ padding: '3px 6px' }}>{n0(w.p, 1)}</td><td style={{ padding: '3px 6px' }}>{lakh(w.oi) ?? '—'}</td>
                    <td style={{ padding: '3px 6px', color: cover ? col : pal.textMuted }}>{w.chg == null ? '—' : `${w.chg > 0 ? '▲ ' : cover ? '▼ ' : ''}${lakh(w.chg)}${cover ? ' COVER' : ''}`}</td>
                    <td style={{ padding: '3px 6px' }}>{w.state ?? '—'}</td><td style={{ padding: '3px 6px' }}>{w.tests ?? '—'}</td><td style={{ padding: '3px 6px' }}>{w.since ?? '—'}</td><td style={{ padding: '3px 6px', color: pal.textMuted }}>{w.last_outcome ?? '—'}</td></tr> })}</tbody>
              </table>)}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px 14px', marginTop: 8 }}>
              {kv('written CE / unwound', br?.written_ce != null ? `${br.written_ce} / ${br.unwound_ce}` : null, br?.counts_why)}
              {kv('written PE / unwound', br?.written_pe != null ? `${br.written_pe} / ${br.unwound_pe}` : null, br?.counts_why)}
              {kv('fronts adv / retreat', br?.advancing != null ? `${br.advancing} / ${br.retreating}` : null, br?.regime_why)}
              {kv('pace CE / PE (rank)', tr?.pace ? `${tr.pace.ce} / ${tr.pace.pe}` : null, tr?.pace_why, 'I')}
              {kv('VPIN', vs?.vpin != null ? `${vs.vpin.toFixed(2)}${vs.pct != null ? ` · p${Math.round(vs.pct * 100)}` : ''}` : null, vs ? `${vs.buckets} buckets · fill ${pct(vs.fill)}` : vpin.why, 'I')}
              {kv('λ pts/lot', lam?.lambda != null ? `${lam.lambda.toFixed(3)}${lam.pct != null ? ` · p${Math.round(lam.pct * 100)}` : ''}` : null, lam?.why ?? ux?.why ?? 'ux not answered', 'I')}
              {kv('drag (eaten)', dg?.frac != null ? `${pct(dg.frac)}${dg.right_side ? ` ${dg.right_side.toUpperCase()} ${dg.strike ?? ''}` : ''}` : null, dg?.anchor_why ?? (drag.data && !drag.data.ok ? 'drag board not up' : drag.why), 'M')}
              {kv('IV/RV', null, gate?.reason?.includes('IV vs RV') ? 'not measured' : 'not on the wire')}
              {kv('IV CE / PE', latest?.gamma?.iv_ce != null ? `${(latest.gamma.iv_ce * 100).toFixed(1)} / ${((latest.gamma.iv_pe ?? 0) * 100).toFixed(1)} @${latest.t}` : null, 'no signal row today')}
              {kv('IVR CE / PE', ctx?.ivr_ce != null ? `${ctx.ivr_ce} / ${ctx.ivr_pe} @${latest?.t}` : null, 'no signal row today')}
              {kv('30m range', ctx?.rng30 != null ? `${n0(ctx.rng30, 0)} pts @${latest?.t}` : null, 'no signal row today')}
              {kv('inside ±1σ', ctx?.inside1 != null ? `${pct(ctx.inside1)} @${latest?.t}` : null, 'no signal row today')}
            </div>
          </div>
          <div style={{ ...S.panel, borderBottom: 0, overflow: 'auto' }}>
            <div style={S.ph}><span style={{ ...S.lbl, marginRight: 'auto' }}>Plays · lamps the board can read · refuse below full</span><span style={S.itag}>[I] a read of the fields, not a signal</span></div>
            <div style={{ display: 'grid', gap: 6 }}>
              {plays.map(p => { const lit = p.lamps.filter(l => l.on === true).length; const isFull = lit === p.lamps.length; const holes = p.lamps.filter(l => l.on == null).length
                return <div key={p.name} style={{ display: 'grid', gridTemplateColumns: '150px 1fr 96px', gap: 10, padding: '7px 8px', border: `1px solid ${isFull ? pal.accent : pal.border}`, alignItems: 'center' }}>
                  <div style={{ fontWeight: 500 }}>{p.name}<small style={{ display: 'block', color: pal.textMuted, fontWeight: 400, fontSize: 10 }}>{p.sub}</small></div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 10px', fontSize: 11, color: pal.textMuted }}>
                    {p.lamps.map(l => <span key={l.name} title={l.why ?? ''} style={{ color: l.on === true ? pal.textPrimary : pal.textMuted }}>{l.on === true ? <span style={{ color: pal.accent }}>● </span> : l.on === false ? '○ ' : '◌ '}{l.name}{l.on == null && l.why ? ` (${l.why})` : ''}</span>)}
                  </div>
                  <div style={{ textAlign: 'right', fontWeight: 500 }}>{isFull ? 'FULL' : 'REFUSE'}<small style={{ display: 'block', color: pal.textMuted, fontWeight: 400, fontSize: 10 }}>{lit}/{p.lamps.length}{holes ? ` · ${holes} hole${holes > 1 ? 's' : ''}` : ''}</small></div>
                </div> })}
              <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr 96px', gap: 10, padding: '7px 8px', border: `1px solid ${full.length ? pal.border : pal.accent}`, alignItems: 'center' }}>
                <div style={{ fontWeight: 500 }}>S5 SKIP<small style={{ display: 'block', color: pal.textMuted, fontWeight: 400, fontSize: 10 }}>logged as an executed trade</small></div>
                <div style={{ fontSize: 11, color: pal.textMuted }}>{full.length ? 'a play is full — skip is off' : 'no play at full; pieces disagree or are holes'}</div>
                <div style={{ textAlign: 'right', fontWeight: 500 }}>{full.length ? 'off' : 'ACTIVE'}</div>
              </div>
            </div>
            {f?.setup?.tells?.length ? <div style={{ fontSize: 11, color: pal.textMuted, marginTop: 6 }}>What flips it: {f.setup.tells.map(t => <span key={t.name}><b style={{ color: pal.textPrimary, fontWeight: 500 }}>{t.name}</b> if {t.predicate} · </span>)}</div> : null}
            <div style={{ fontSize: 10, color: pal.textMuted, marginTop: 6 }}>hue = side only · hatched = covering · dashed = forming · grey = PATA NAHI with the server's reason · no hit rate, no verdict — the board reads, the trader decides</div>
          </div>
        </div>
      </div>
    </div>
  )
}
