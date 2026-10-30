/* ── OI SPEED (RAFTAAR) — Mary, 27 Oct 2026 ──────────────────────────────────
   "the rate of change or speed of oi writing and covering once they stop like we mark on board tab ... one glance one
   can see if this accelerating or staying steady or declining". The Board stamps when a front STOPPED (§1d); this reads
   what each near-money strike-side did after that, minute by minute, off the same /api/oihist grid:

     speed    OI change over the last W minutes, per minute [M]; "pehle" is the W minutes before that [M]
     flow     W likh rahe / R ruke / C chhod rahe: speed against §1d's own stall RATE of the strike's scale [I]
     stamp    a new flow is stamped once it HOLDS for HOLD one-minute marks, at its first mark: "ruk gaye 09:27",
              "chhodne lage 09:31", "phir likhne lage 10:21" [I]
     accel    now vs pehle: tez / barabar / dheema / palta (turned) / shuru (from stopped) [I]
     result   effort vs result: the spot move over the same W minutes, in the writers' frame [M], and its word [I]

   DISPLAY ONLY: it gates nothing, feeds no setup, no log, no Telegram. W and HOLD were chosen on 27 Oct's NIFTY grid to
   make the stamps legible; they are not §1d's and must not be mistaken for it. Causal: a mark reads only marks at or
   before it, so the stamps are the same whenever the screen is opened (the anytime-start rule; /api/oihist rebuilds
   the day from the record). Pure, no I/O. Check: node --experimental-strip-types src/speed/speed.check.ts */

export const W = 5               // the speed window, minutes [I]
export const HOLD = 3            // a new flow must hold 3 one-minute marks (her canonical 3-min bar) to be stamped [I]
export const RATE = 0.05 / 15    // §1d's stall rate, fronts.STALL_FRAC over SLOPE_MARKS: 5 % of the scale per 15 min
export const FAST = 1.5          // now >= 1.5x pehle is tez, <= 1/1.5 is dheema [I]
export const MOVE = 0.2          // a spot move under 0.2 strike step over W minutes is "price ruka" [I]
export const NEAR = 9            // fronts.NEAR: her nine strikes nearest spot

export type Side = 'CE' | 'PE'
export type Flow = 'W' | 'R' | 'C'
export type Accel = 'tez' | 'barabar' | 'dheema' | 'palta' | 'shuru' | null
export type Cell = {
  k: number; side: Side; chg: number; spd: number | null; before: number | null; floor: number
  flow: Flow | null; since: string | null; accel: Accel; vs: number | null   // vs: spot pts AGAINST this side's writers (+)
}
export type Stamp = { t: string; k: number; side: Side; flow: Flow; word: string; spot: number | null }
export type Net = { spd: number | null; before: number | null; floor: number; accel: Accel }
export type SpeedRead = {
  asof: string; spot: number | null; d5: number | null; d15: number | null; step: number; atm: number
  nine: number[]; cells: Cell[]; stamps: Stamp[]; net: Record<Side, Net>
}
export type Minutes = Record<string, { spot?: number | null; k?: Record<string, unknown> } | null>
/** The words, shared by the Speed tab and War so the two screens say one thing. */
export const FLOW: Record<Flow, string> = { W: 'LIKH RAHE', R: 'RUKE', C: 'CHHOD RAHE' }
export const ACCEL: Record<Exclude<Accel, null>, string> = { tez: '▲▲ tez', barabar: '▶ barabar', dheema: '▼ dheema', palta: '⇄ palta', shuru: '● shuru' }

const ok = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x)
export const mm = (t: string) => +t.slice(0, 2) * 60 + +t.slice(3, 5)
/** OI in lakh, the Board's unit (2 decimals under a lakh, for BANKNIFTY), signed when asked. */
export const lakh = (x: number, signed = false) => {
  if (Math.abs(x) < 500) return '0'                                   // rounds to 0.00L: never a "−0.00L"
  const a = Math.abs(x), s = x < 0 ? '−' : signed && x > 0 ? '+' : ''
  return s + (a / 1e5).toFixed(a >= 1e7 ? 0 : a >= 1e5 ? 1 : 2) + 'L'
}

export const flowOf = (spd: number, floor: number): Flow => (spd > floor ? 'W' : spd < -floor ? 'C' : 'R')

export function accelOf(now: number | null, before: number | null, floor: number): Accel {
  if (now == null || before == null) return null
  const a = Math.abs(now), b = Math.abs(before)
  if (a <= floor) return b <= floor ? null : 'dheema'
  if (b <= floor) return 'shuru'
  if (Math.sign(now) !== Math.sign(before)) return 'palta'
  return a >= FAST * b ? 'tez' : a * FAST <= b ? 'dheema' : 'barabar'
}

/** Effort vs result for one side's flow: did price go with the writers or against them over the same minutes? */
export function resultOf(flow: Flow | null, vs: number | null, step: number): string | null {
  if (flow == null || flow === 'R' || vs == null) return null
  if (Math.abs(vs) < MOVE * step) return 'price ruka'
  if (flow === 'W') return vs > 0 ? 'ulta likh rahe' : 'saath'        // writing into a move against them: absorbing, or trapped
  return vs > 0 ? 'bhaag rahe' : 'booking'                             // covering into pain is forced (fuel); into profit, booking
}

/** The whole board's pressure: PUT writing and CALL cutting push up, CALL writing and PUT cutting push down. */
export function leanOf(net: Record<Side, Net>, d5: number | null, step: number): { dir: 1 | -1 | 0; word: string; result: string | null } | null {
  const c = net.CE.spd, p = net.PE.spd
  if (c == null || p == null) return null
  const lean = p - c
  if (Math.abs(lean) <= net.CE.floor + net.PE.floor) return { dir: 0, word: 'dono barabar', result: null }
  const dir = lean > 0 ? 1 : -1
  const result = d5 == null ? null : Math.abs(d5) < MOVE * step ? 'price ruka · absorb?' : Math.sign(d5) === dir ? 'price saath' : 'price ulta · zor bekaar'
  return { dir, word: dir > 0 ? 'zor upar ka' : 'zor neeche ka', result }
}

export function read(minutes: Minutes | null | undefined): SpeedRead | null {
  const rows = Object.entries(minutes ?? {})
    .filter(([t, r]) => /^\d\d:\d\d$/.test(t) && !!r && typeof r === 'object')
    .sort(([a], [z]) => (a < z ? -1 : a > z ? 1 : 0))
  if (!rows.length) return null
  const ms = rows.map(([t]) => mm(t))
  const at = new Map(ms.map((m, i) => [m, i]))
  const raw = rows.map(([, r]) => (ok(r?.spot) ? r!.spot! : null))
  const spotAt = (i: number): number | null => { for (let j = i; j >= 0; j--) if (raw[j] != null) return raw[j]; return null }
  const L = rows.length - 1, spot = spotAt(L)
  if (spot == null) return null
  const ago = (n: number) => { const b = at.get(ms[L] - n); const s = b == null ? null : spotAt(b); return s == null ? null : spot - s }

  const ks = Object.keys(rows[L][1]?.k ?? {}).map(Number).filter(ok).sort((a, z) => a - z)
  if (!ks.length) return null
  const step = Math.min(...ks.slice(1).map((k, i) => k - ks[i]).filter((d) => d > 0), Infinity)
  const nine = [...ks].sort((a, z) => Math.abs(a - spot) - Math.abs(z - spot) || a - z).slice(0, NEAR).sort((a, z) => a - z)
  const atm = nine.reduce((b, k) => (Math.abs(k - spot) < Math.abs(b - spot) ? k : b), nine[0])

  const cells: Cell[] = [], stamps: Stamp[] = []
  for (const k of nine) for (const [si, side] of [[0, 'CE'], [1, 'PE']] as const) {
    // an absent cell reads 0, as in fronts.read: the grid is written whole per minute
    const v = rows.map(([, r]) => { const c = (r?.k ?? {})[String(k)]; return Array.isArray(c) && ok(c[si]) ? c[si] : 0 })
    let hi = 0, lo = 0, run: Flow | null = null, n = 0, cur: Flow | null = null, since: string | null = null, wrote = false
    for (let i = 0; i <= L; i++) {
      hi = Math.max(hi, v[i]); lo = Math.min(lo, v[i])
      const b = at.get(ms[i] - W)
      if (b == null) { run = null; n = 0; continue }                    // a hole in the record: no speed, the run restarts
      const f = flowOf((v[i] - v[b]) / W, RATE * Math.max(hi, -lo, 1))
      n = f === run ? n + 1 : 1; run = f
      if (n !== HOLD || f === cur) continue
      const s = i - HOLD + 1
      stamps.push({ t: rows[s][0], k, side, flow: f, spot: spotAt(s),
        word: f === 'W' ? (wrote ? 'phir likhne lage' : 'likhne lage') : f === 'R' ? 'ruk gaye' : 'chhodne lage' })
      if (f === 'W') wrote = true
      cur = f; since = rows[s][0]
    }
    const b = at.get(ms[L] - W), b2 = at.get(ms[L] - 2 * W)
    const spd = b == null ? null : (v[L] - v[b]) / W
    const before = b == null || b2 == null ? null : (v[b] - v[b2]) / W
    const floor = RATE * Math.max(hi, -lo, 1)
    const was = b == null ? null : spotAt(b)
    cells.push({ k, side, chg: v[L], spd, before, floor, flow: cur, since, accel: accelOf(spd, before, floor),
      vs: was == null ? null : side === 'CE' ? spot - was : was - spot })
  }
  stamps.sort((a, z) => (a.t < z.t ? 1 : a.t > z.t ? -1 : a.side < z.side ? -1 : a.side > z.side ? 1 : a.k - z.k))

  const sum = (xs: (number | null)[]) => (xs.some((x) => x == null) ? null : xs.reduce((a: number, x) => a + x!, 0))
  const netOf = (side: Side): Net => {
    const cs = cells.filter((c) => c.side === side)
    const spd = sum(cs.map((c) => c.spd)), before = sum(cs.map((c) => c.before)), floor = cs.reduce((a, c) => a + c.floor, 0)
    return { spd, before, floor, accel: accelOf(spd, before, floor) }
  }
  return { asof: rows[L][0], spot, d5: ago(W), d15: ago(15), step: Number.isFinite(step) ? step : 50, atm, nine, cells, stamps,
    net: { CE: netOf('CE'), PE: netOf('PE') } }
}
