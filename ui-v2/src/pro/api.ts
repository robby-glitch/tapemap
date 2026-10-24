// THE PRO SCREEN'S ONE POLLER (docs/pro-tool/API-v3.md). Every 10 s: /api/hold/trades, then /api/fold?id= for each open
// trade, or /api/fold/flat (+ /api/fold/ifin for the four legs at her strike, IF YOU WERE IN) when flat, /api/chain for the
// strike picker, and /api/story (the decoder: sentence, count, highlights) for the open trade's index, else the picked one.
// It reads and renders; fold.py decides. An endpoint that is missing or down is "could not check — the engine is not
// answering (hh:mm:ss)", never a fixture (the fixture viewer is ?fixture=1, bannered, and never polls).
import { useSyncExternalStore } from 'react'
import { j, tone } from '../hold/store'
import type { Trade, Voice } from '../hold/HoldWindow'
export type { Trade }

// she trades all three (2026-10-03): the DESK reads the index she picks; a trade's own index rides its record
export const INDICES = ['NIFTY', 'BANKNIFTY', 'SENSEX'] as const
export type Idx = typeof INDICES[number]
const IDX0: Idx = (() => { try { const v = localStorage.getItem('pro.idx'); return INDICES.find(i => i === v) ?? 'NIFTY' } catch { return 'NIFTY' } })()
export const FIXTURE = new URLSearchParams(location.search).get('fixture') === '1'
const POLL_MS = 10000

// in a trade (and IF YOU WERE IN) the chips are her side's; flat has no "you", so fold.flat names the side
export type Chip = 'WITH' | 'AGAINST' | 'BUYERS' | 'SELLERS' | 'QUIET' | "CAN'T CHECK"
export type Row = { chip: Chip | null; sentence: string | null; machine?: string | null }
export type Rows = { zone: Row; flow: Row; oi: Row; vpin: Row }
export type Tag = { M: string[]; I: string[] }
export type Prem = { now: number | null; pct: number | null; peak: number | null; peak_pct?: number | null; peak_t: string | null
                     given_back: number | null; at_G: number | null; at_G_why?: string | null; at_A: number | null; at_A_why?: string | null
                     chain_age_s?: number; intrinsic: number | null; time: number | null; expiry_day: boolean; tag?: Tag }
export type Level = { px: number; why?: string; set_t?: string; locked?: boolean; touched?: boolean }
export type Wall = { k: number; side: 'CE' | 'PE'; oi: number | null; peak: number | null; peak_t: string | null; state?: string; px?: number; pts?: number }
export type Ev = { seq: number; ts: string; kind: string; text: string }
// headline is null with a `why` before the mark seeds; after her exit the view is frozen (premium at her exit)
export type View = { ts: string; headline: string | null; why?: string; clause: string; line2: string; mode?: string; expiry_pm?: boolean
                     fut?: number | null; F?: number | null; E?: number | null; G: Level | null; W: Wall | null; A: Wall | null
                     prem: Prem; rows: Rows; holes: unknown[]; sound_id: string | number | null; tag?: Tag; events?: Ev[]
                     frozen?: boolean; exit_t?: string }
export type Word = { t: string; headline: string; clause: string; prem?: number | null; pct?: number | null; after_exit?: boolean }
// HOLD v2 (hold2.py, research-findings §1m): the push-trail line beside the word, DISPLAY ONLY -- it never changes the word
export type Hold2 = { ok: boolean; why?: string; text?: string | null; note?: string; line_fut?: number; line_spot?: number | null
                      why_short?: string; pts?: number | null; front?: { side: string; k: number; state: string } | null; tag?: string }
// (A52: the three HOLD v3 shadow lines ride no in-trade reply any more; they are logged, then shown on the receipt)
export type FoldRead = { ok: boolean; why?: string; id?: string; trade?: Trade; view?: View; words?: Word[]; asof?: string; feed?: Feed; hold2?: Hold2 | null
                         voice?: Voice }   // A52 THE ONE VOICE + the TRADE MAP (server._in_trade), the floating window's face
// FEED HEALTH (P3, feed_health.py): is the GoCharting tape alive, read by the server from the data; rides every /api/fold* reply
export type FeedState = 'LIVE' | 'SLOW' | 'STALLED' | 'DEAD' | 'NOT OPEN TODAY' | 'AFTER CLOSE'
export type Feed = { idx?: string; state: FeedState | null; since?: string | null; age_s?: number | null; why?: string | null; chip?: string | null
                     do?: string | null; last_post?: string | null; last_bar?: string | null; alarm?: boolean; sound?: boolean
                     short_bar?: { t: string; gc: number; ux: number } | null; depends_on_gc?: string[]; upstox_only?: string[] }
export type Fight = { px: number | null; what: string; confirm: string | null }
export type GaveUp = { text: string; t: string; px: number; k: number; side: string; oi: string; unproven: string }
export type Reentry = { text: string; unproven: boolean; t?: string; px?: number; prem?: number | null; exit_prem?: number | null; falsifier?: string }
export type Flat = { ok: boolean; why?: string; next_fight?: { above: Fight | null; below: Fight | null } | null; at?: { px: number; what: string } | null
                     rows?: Rows; day?: string | null; asof?: string; date?: string; F?: number; gave_up?: GaveUp | null; reentry?: Reentry | null; tag?: Tag
                     feed?: Feed }
export type Ifin = { ok: boolean; why?: string; view?: View }
export type Strike = { k: number; ce: number | null; pe: number | null }
export type ChainLite = { ok: boolean; why?: string; ts?: string; spot?: number; atm?: number; expiry?: string; strikes: Strike[] }
export type RecTrade = { id: string; trade: Trade; words: Word[]; why?: string | null; exit: unknown; best: unknown; peak_before_exit: unknown; given_back: unknown }
export type Rec = { ok: boolean; why?: string; trades?: RecTrade[] }
export type Ty = 'CE' | 'PE'
export type Side = 'BUY' | 'SELL'
export type Pick = { k: number; ty: Ty; side: Side }
/** IF YOU WERE IN: the four at-the-money legs, a buyer's and a writer's of each, in a fixed order (CE row, PE row) */
export const LEGS = [['CE', 'BUY'], ['CE', 'SELL'], ['PE', 'BUY'], ['PE', 'SELL']] as const
export const legKey = (ty: string, side: string) => `${ty}:${side}`

// THE DECODER (story.py over the events the GoCharting extension posted; /api/story). Display only: it never enters a hold /
// fold read. Everything past `asof` is the panel round's (story.compose_all) and may be absent on an older server.
export type Tier = 'red' | 'amber' | 'blue'
export type Hi = { tier: Tier; kind: string; what: string; t_ms: number; time: string; id?: string; block?: string }
export type TradeRead = { against: number; behind: number; d: number; since?: string; word?: string | null; word_t?: string | null; word_why?: string | null
                          items?: { side: number; chip: string; time: string; kind: string }[]; note?: string }
export type Chapter = { start: string; end: string; current: boolean; name: string; sentence: string; chips: string[]; side: number; asar: number | null }
export type Story = { ok: boolean; sentence: string | null; sentence_why?: string | null; chips?: string[]; asof?: string | null
                      idx?: string; day?: string; ts?: string | null; now_ms?: number; open_prints?: number; event?: { kind: string; side?: number; state?: string; p?: number } | null
                      trade_read?: TradeRead | null; trade_read_why?: string | null; highlights?: Hi[]
                      chapters?: { items: Chapter[]; items_why?: string | null; trap_why?: string | null } }
export type S = { idx: Idx; loaded: boolean; trades: Trade[]; tradesWhy: string | null; fold: Record<string, FoldRead>; flat: Flat | null
                  engineWhy: string | null; ifin: Record<string, Ifin> | null; chain: ChainLite | null
                  /** the GoCharting tape's health off the last fold/flat reply; null = not read (the engine banner then speaks) */
                  feed: Feed | null; story: Story | null
                  /** the live in-trade read (GET /api/validate?idx=, the GoCharting round's validate_live); null when flat */
                  validate: Validate | null
                  /** contract size per index, off /api/hold/trades `lots` (the slip's lots -> qty) */
                  lot: Record<string, number> }

// THE LIVE IN-TRADE READ (validate_live.read; validate-tab-spec adapted 2026-10-05). The engine's word stays the decision;
// lamps, prompt and shadow are reads beside it. Every missing piece arrives with its `_why`.
export type LampState = 'G' | 'A' | 'R' | 'X'
export type Lamp = { state: LampState; text?: string | null; since?: string | null; from?: LampState | null; acked?: boolean }
export type Validate = { ok: boolean; why?: string; in_trade?: boolean; trade_id?: string; asof?: string
  word?: string | null; word_why?: string | null; prompt?: string | null; prompt_why?: string | null; prompt_because?: string | null
  lamps?: Record<string, Lamp> | null
  level?: { t1: number | null; t2: number | null; inval: number | null; to_t1: number | null; to_t2: number | null; to_inval: number | null
            t1_why?: string | null; t2_why?: string | null; inval_why?: string | null; units?: string; t1_hit?: boolean; t2_hit?: boolean; state?: LampState } | null
  reversal?: { met: number; of: number; unknown?: number; items?: { key: string; met: boolean | null; text: string }[] } | null
  /** the engine's clause (word_why stays null while there is a word: the why-pair rule) */
  clause?: string | null
  noise_floor?: number | null; trail_unlock?: unknown; timer?: { in_trade_s?: number; green_since?: string | null; typical_s?: number; fear_zone?: boolean } | null
  cooldown?: Timer | null; flip?: Timer | null; shadow?: { word?: string | null } | null }
/** a WARNING, never a block (no order path): 10 min after a STOPPED / RED exit; 60 s after any exit (a FLIP) */
export type Timer = { until: number; left_s: number; why: string; from_d?: number }

export const hms = () => new Date().toTimeString().slice(0, 8)
export const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
/** "could not check — <why>", once: the engine's reasons already carry the prefix, and a doubled one read as noise */
export const cc = (w?: string | null, dflt = 'no reason given') => !w ? `could not check — ${dflt}` : w.startsWith('could not check') ? w : `could not check — ${w}`
export const notAnswering = (t = hms()) => `could not check — the engine is not answering (${t})`
/** the engine did not answer at all (down, or slower than the 8 s timeout) -- not the same as answering with a reason */
export const isDown = (w: string | null) => !!w && w.includes('the engine is not answering')

let s: S = { idx: IDX0, loaded: false, trades: [], tradesWhy: null, fold: {}, flat: null, engineWhy: null, ifin: null, chain: null, feed: null, story: null, validate: null, lot: {} }
const subs = new Set<() => void>()
let busy = false, again = false, timer: number | undefined, ifinK: number | null = null

/** render only on change: a read identical to the last one never notifies a subscriber */
export function put(p: Partial<S>) {
  const n = { ...s, ...p }
  if (JSON.stringify(n) === JSON.stringify(s)) return
  s = n; subs.forEach(f => f())
}

// one short tone when a trade's sound_id changes; ids are kept across reloads, so a reload is silent. Storage first:
// the floating window, its face and the DESK tab each poll, and the first page to hear a FOLD speaks for all of them.
const heard = new Map<string, string>()
function chime(id: string, sid: unknown) {
  if (sid == null) return
  const k = `pro.sound.${id}`, v = String(sid)
  let was: string | null = null
  try { was = localStorage.getItem(k) } catch { /* no storage: the in-memory map still keeps it to once per load */ }
  was ??= heard.get(k) ?? null
  if (was === v) return
  heard.set(k, v)
  try { localStorage.setItem(k, v) } catch { /* same */ }
  tone()
}

async function poll() {
  if (busy) { again = true; return }
  busy = true
  const at = hms(), n: Partial<S> = { loaded: true }
  try {
    const r = await j<{ ok: boolean; trades: Trade[]; why?: string; lots?: Record<string, number> }>('/api/hold/trades')
    if (r.ok) { n.trades = r.trades; n.tradesWhy = null; n.lot = r.lots ?? s.lot } else n.tradesWhy = cc(r.why, 'the trades could not be read')
  } catch { n.tradesWhy = s.tradesWhy ?? notAnswering(at) }
  const trades = n.trades ?? s.trades, open = trades.filter(t => !t.exit_t), k = ifinK, idx = s.idx
  let why: string | null = null
  const fail = () => { why ??= s.engineWhy ?? notAnswering(at) }          // the first failure's time stays: no churn
  const refused = (w?: string) => { why ??= cc(w, 'the engine gave no reason') }
  const fold: Record<string, FoldRead> = {}
  let feed: Feed | null = null                                             // the feed band rides whichever read answered
  const jobs: Promise<unknown>[] = open.map(async t => {
    try {
      const r = await j<FoldRead>(`/api/fold?id=${encodeURIComponent(t.id)}`)
      fold[t.id] = r
      if (r.feed) feed = r.feed
      if (r.ok) chime(t.id, r.view?.sound_id); else refused(r.why)
    } catch { fail(); if (s.fold[t.id]) fold[t.id] = s.fold[t.id] }     // keep the last read; the banner says it is old
  })
  if (!open.length) {
    jobs.push((async () => {
      try { const r = await j<Flat>(`/api/fold/flat?idx=${idx}`); n.flat = r; if (r.feed) feed = r.feed; if (!r.ok) refused(r.why) }
      catch { fail(); n.flat = s.flat }
    })())
    const legs: Record<string, Ifin> = {}
    if (k != null) {
      n.ifin = legs
      for (const [ty, side] of LEGS) jobs.push((async () => {
        const lk = legKey(ty, side)
        try { legs[lk] = await j<Ifin>(`/api/fold/ifin?idx=${idx}&k=${k}&ty=${ty}&side=${side}`) }
        catch { legs[lk] = { ok: false, why: s.ifin?.[lk]?.why ?? notAnswering(at) } }
      })())
    } else n.ifin = null
  } else { n.flat = null; n.ifin = null }
  jobs.push((async () => {
    try {
      const c = await j<{ ok: boolean; why?: string; error?: string; ts?: string; spot?: number; atm?: number; expiry?: string
                          strikes?: { k: number; ce?: { ltp?: number | null }; pe?: { ltp?: number | null } }[] }>(`/api/chain?idx=${idx}`)
      n.chain = { ok: c.ok, why: c.why ?? c.error, ts: c.ts, spot: c.spot, atm: c.atm, expiry: c.expiry,     // /api/chain refuses in `error`
                  strikes: (c.strikes || []).map(x => ({ k: x.k, ce: x.ce?.ltp ?? null, pe: x.pe?.ltp ?? null })) }
    } catch { n.chain = s.chain ?? { ok: false, why: notAnswering(at), strikes: [] } }
  })())
  jobs.push((async () => {                     // the live in-trade read (flat: the cooldown / flip timers); /api/fold stays the fallback
    try { n.validate = await j<Validate>(`/api/validate?idx=${open[0]?.idx ?? idx}`) }
    catch { n.validate = { ok: false, why: `could not check — the server did not answer /api/validate (${at})` } }
  })())
  jobs.push((async () => {                                               // the decoder: never a hold / fold input
    try { n.story = await j<Story>(`/api/story?idx=${open[0]?.idx ?? idx}`) }
    catch { n.story = { ok: false, sentence: null, sentence_why: `the server did not answer /api/story (${at})` } }
  })())
  await Promise.all(jobs)
  if (idx !== s.idx) { busy = false; again = false; poll(); return }        // she switched index mid-poll: this read is the old one's
  n.fold = fold; n.engineWhy = why; n.feed = feed                       // no reply, no feed: the engine banner speaks, not a stale band
  put(n)
  busy = false
  if (again) { again = false; poll() }
}

function subscribe(f: () => void) {
  subs.add(f)
  if (subs.size === 1 && !FIXTURE) { poll(); timer = window.setInterval(poll, POLL_MS) }
  return () => { subs.delete(f); if (!subs.size) window.clearInterval(timer) }
}
export const useStore = () => useSyncExternalStore(subscribe, () => s)

/** the index the DESK reads while she is flat: the slip, the flat read and IF YOU WERE IN follow it */
export function setIdx(x: Idx) {
  if (x === s.idx) return
  try { localStorage.setItem('pro.idx', x) } catch { /* the pick still holds for this page */ }
  ifinK = null
  put({ idx: x, flat: null, ifin: null, chain: null, engineWhy: null })
  if (!FIXTURE) poll()
}

/** the strike she is looking at while flat: IF YOU WERE IN reads its four legs now and at every poll */
export function setIfin(k: number | null) {
  if (k === ifinK) return
  ifinK = k
  if (!FIXTURE) poll()
}

/** the existing door, unchanged: {op: mark | exit | reopen | unmark}. Nothing reaches a broker. */
export async function tradeOp(body: Record<string, unknown>): Promise<{ ok: boolean; why?: string; trades?: Trade[] }> {
  if (FIXTURE) return { ok: false, why: 'FIXTURE — nothing is marked from this viewer' }
  try {
    const r = await j<{ ok: boolean; why?: string; trades?: Trade[] }>('/api/hold/trades', body)
    if (r.ok && r.trades) put({ trades: r.trades })
    poll()
    return r
  } catch { return { ok: false, why: notAnswering() } }
}

// RECEIPTS (receipts.py; validate-tab-spec §7): every closed trade's receipt + the scoreboard; and the tradebook import
export type Receipt = { id: string; day: string; hold_s: number | null; pts: number | null; exit_px: number | null; exit_px_src: string
  result: 'win' | 'loss' | 'flat' | null; left_on_table_pts: number | null
  post: { p10?: number | null; p20?: number | null; p30?: number | null; max_fav?: number; max_fav_t?: string; complete?: boolean; why?: string | null }
  adds_dumped: { t: string; after_s: number }[]; engine_at_exit: string | null; reversal_at_exit: number | null
  lamps_at_exit: Record<string, string> | null; tags: string[]; fear: boolean; fear_clock_only: boolean; amber: boolean; amber_unverified: boolean; src: string }
export type Board = { n: number; n_win: number; n_loss: number; n_flat: number; n_unpriced: number; avg_hold_win_s: number | null; avg_hold_loss_s: number | null
  median_hold_win_s: number | null; fear_exits: number; fear_left_pts: number; fear_clock_only: number; fear_clock_only_left_pts: number
  reentries: number; reentry_tax_events: number; reentry_tax_pts: number; amber_exits: number; amber_unverified: number; adds_dumped: number; left_on_table_pts: number }
export type ReTax = { from: string; to: string; day: string; gap_s: number; same_leg: boolean; exit_px: number | null; reentry_px: number | null; tax: number | null; why: string | null }
export type Receipts = { ok: boolean; why?: string; today?: string; typical_s?: number; typical_src?: string; receipts?: Receipt[]; reentries?: ReTax[]
  scoreboard?: { today: Board; week: Board; all: Board } }
export type ImportOut = { ok: boolean; why?: string; confirm?: boolean; fills?: number; skipped?: string[]
  days?: Record<string, { new: { id: string; t0: string; exit_t: string | null; qty: number; p0: number | null; exit_px: number | null }[]; have: string[]; refused: string[] }>
  wrote?: Record<string, string[]>; backups?: string[] }
export async function receiptsGet(): Promise<Receipts> {
  try { return await j<Receipts>('/api/receipts') } catch { return { ok: false, why: notAnswering() } }
}
/** her tradebook: a preview unless confirm; the server backs every touched day file up before it writes. Never an order. */
export async function importBook(csv: string, confirm: boolean): Promise<ImportOut> {
  if (FIXTURE) return { ok: false, why: 'FIXTURE — nothing is imported from this viewer' }
  try { return await j<ImportOut>('/api/receipts/import', { csv, confirm }) } catch { return { ok: false, why: notAnswering() } }
}

export async function record(day: string): Promise<Rec> {
  try { return await j<Rec>(`/api/fold/record?day=${day}`) } catch { return { ok: false, why: notAnswering() } }
}
