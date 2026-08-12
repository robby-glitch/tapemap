import { useEffect, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { usePalette, rgbOf } from '../theme'

/* ── SIGNALS ─────────────────────────────────────────────────────────────────
   The live trigger record (data/trigger_log.jsonl, written by trigger_log.py's
   `log_new` from server.py's per-index refresh threads), served by
   /api/signals. Until now it existed only on disk and only `python
   trigger_log.py` could see it.

   What this screen is FOR: the operator asked for "a place [where] all the
   signals it generated [live] so that we can track or backtest the strategy".
   So it shows the accumulating record — and nothing derived from it.

   Three rules this file exists to keep, each one a place where a prettier
   screen would lie:

   1. TWO RULES ARE IN THAT FILE. Rows with `rule: "5c"` are the operator's
      scored two-candle entry. Rows with no `rule` came from §1's ONE-CANDLE
      touch, which research-findings marks VOID — a different detector marking
      a different bar. The default view is §5c only; ALL shows the legacy rows
      under their own heading, labelled, and never inside a §5c count. The
      backend counts them separately for the same reason.

   2. NO RATE, AT ANY n. Outcomes are filled only by `python trigger_log.py
      score`, never at log time. When they are filled they appear PER ROW,
      exactly as published, and are never averaged: below the log's ~20-25
      target the sample is noise, and at or above it research-findings §5e
      records the pass criterion as owed by the operator and not to be
      invented. The refusal sentence comes from the backend (`no_rate_why`) so
      the threshold lives in one language, not two.

      The outcome answers the operator's own question (2026-08-12): the max
      move from the price, the max adverse move, whether their 20-point stop
      broke — which does NOT end the measurement — and how far the OPPOSITE
      ±1/±2/±3σ side was reached, read live. `f15`/`f30` are older and
      narrower and keep exactly the meaning they had; neither is folded into
      the other.

   3. ABSENCE HAS THREE MEANINGS and they are three different sentences:
      the log could not be read (nothing was checked), no §5c signal has ever
      been logged (checked, empty), and this filter matches nothing (checked,
      non-empty, filtered out). Collapsing them is this codebase's first
      non-negotiable.

   4. AN ARM IS NOT A SIGNAL (added 2026-08-12). The log now also records the
      setup ARMING — a 3-minute candle touching d3 or u3 — so it can be scored
      on forward live data. An arm is counted, filtered and displayed entirely
      apart from entries: the entry may never come, and folding arms into an
      entry total would inflate what this strategy has produced by every setup
      that expired unfired. Nothing here presents one as a trade.            */

// ── The row shape, exactly as trigger_log.log_new writes it ─────────────────
type Pin = { k?: number | null; dist?: number | null; regime?: string | null }

type Ctx = {
  verdict?: string | null
  vwhy?: string | null
  breadth?: string | null
  line?: string | null
  flips?: string[] | null
  age?: number | null
  rng30?: number | null
  vol30?: number | null
  inside1?: number | null
  z?: number | null
  pin?: Pin | null
  plays?: string[] | null
  floor?: [string, number] | null
  cap?: [string, number] | null
}

type Gamma = {
  regime?: string | null
  w_ce?: number | null
  w_pe?: number | null
  w_bars_ce?: number | null
  w_bars_pe?: number | null
  proxy?: number | null
  iv_ce?: number | null
  iv_pe?: number | null
}

export type SignalRow = {
  at?: number | null
  day?: string | null
  index?: string | null
  t?: string | null
  side?: string | null
  band?: string | null
  rule?: string | null
  /** ABSENT on an entry row — every row written before 2026-08-12 is one, and
   *  none was rewritten to say so. Absent IS "entry". */
  kind?: 'arm' | null
  px?: number | null
  trigger?: string | null
  // ── arm rows only (kind === 'arm'). An entry row carries none of these. ──
  /** The bar interval the arm was recorded at. Always the scored 3. */
  interval?: number | null
  /** The band value armed on. */
  level?: number | null
  /** The reference bar's line to beat, under its TRUE name: a BUY publishes
   *  `ref_high`, a SELL `ref_low`, and a low never arrives as a high. */
  ref_high?: number | null
  ref_low?: number | null
  /** The touch itself — the 3-minute bar's own low (BUY) / high (SELL). */
  extreme?: number | null
  /** TIMING ONLY: the 1-minute bar inside that 3-minute bucket which made the
   *  extreme. `null` plus `t_1m_why` when it could not be identified — never
   *  a guessed minute. */
  t_1m?: string | null
  extreme_1m?: number | null
  t_1m_why?: string | null
  /** A later candle printing a new lower low BECOMES the reference. Each
   *  distinct reference is its own row; `first_t` points at the arm that
   *  started the setup, so counting SETUPS is counting `rearm: false`. */
  rearm?: boolean | null
  first_t?: string | null
  gamma?: Gamma | null
  ctx?: Ctx | null
  oi_call?: number | null
  oi_put?: number | null
  oi_strength?: number | null
  closed_bar?: boolean | null
  f15?: number | null
  f30?: number | null

  // ── Outcome fields. Filled ONLY by `python trigger_log.py score`, never at
  //    log time, and under names of their own — `f15`/`f30` keep exactly the
  //    meaning they always had and are not folded into any of these. ────────
  /** WHICH PRICE every number below is in points from. `entry_close` on an
   *  entry (the close the rule fired on) and `arm_close` on an arm (the arm
   *  candle's own close — an arm entered nothing, so it has no entry price).
   *  Named on the row so a reader can never mistake one for the other. */
  anchor?: 'entry_close' | 'arm_close' | null
  anchor_px?: number | null
  anchor_t?: string | null
  scored_from?: string | null
  /** The operator's own flat-by time. Nothing after it is measured. */
  scored_to?: string | null
  /** Furthest FAVOURABLE / ADVERSE move in points, signed by side like f15,
   *  with the clock each was reached. Bar extremes, not closes. */
  mfe?: number | null
  mfe_t?: string | null
  mae?: number | null
  mae_t?: string | null
  /** The operator's 20-point stop. `stop_hit: null` means it could not be
   *  PLACED (no band price on the row) — that is "unknown", not "it held".
   *  A hit does NOT end the measurement: mfe/mae keep running to `scored_to`,
   *  because "stopped out" and "would have worked" are two separate facts. */
  stop_px?: number | null
  stop_hit?: boolean | null
  stop_t?: string | null
  stop_from?: string | null
  stop_why?: string | null
  /** How far the OPPOSITE side of the band was reached — the side the operator
   *  takes profit on. Read LIVE: each bar against ITS OWN bands, never the
   *  ones frozen at the anchor. `sigma` is how far the furthest excursion got
   *  in the band's own sigma units, which is what answers "and beyond". */
  bands?: {
    side?: 'u' | 'd' | null
    u1?: string | null; u2?: string | null; u3?: string | null
    d1?: string | null; d2?: string | null; d3?: string | null
    furthest?: string | null
    beyond?: boolean | null
    sigma?: number | null
    sigma_t?: string | null
    no_band?: number | null
  } | null
  /** ARM ROWS ONLY: did the setup go on to TRIGGER, and when. `null` means it
   *  was NOT RE-DERIVED — the cached session shows no arm on that bar — which
   *  is not the same claim as "it did not trigger". */
  triggered?: boolean | null
  trigger_t?: string | null
  trigger_why?: string | null
  /** Why this row carries no numbers, in words. Never a zero, never blank. */
  unscored?: string | null
}

type Payload = {
  ok: boolean
  path?: string
  error?: string
  rule?: string
  idx?: string | null
  kind?: string
  total?: number
  unparsed?: number
  five_c?: {
    n: number; buy: number; sell: number; scored: number
    /** Rows carrying the operator's outcome measures, and rows that were
     *  CHECKED and could not be measured. Two counts, because a hole in the
     *  cache and a trade that went nowhere are opposite facts.
     *
     *  OPTIONAL on purpose: a backend older than 2026-08-12 serves this object
     *  without them, and a long-running server is not restarted just because
     *  the UI reloaded. Read through `??` below — rendering `undefined of 3`
     *  is the kind of number this screen exists to not print. */
    outcome?: number; unscored?: number
  }
  legacy?: { n: number }
  /** Counted apart from `five_c` and never summed into it. `setups` collapses
   *  a run of falling lows into the one setup §5c says it is; `n` stays the
   *  lossless row count. No `scored`: an arm has no entry price, so it can
   *  never have an outcome. */
  arms?: {
    n: number; buy: number; sell: number
    setups: number; rearms: number
    interval: number[]; no_minute: number
    /** An arm still never gets f15/f30 — it entered nothing. It CAN carry the
     *  outcome measures, anchored on its own candle's close. `triggered`
     *  counts the setups that went on to fire; `not_rederived` counts those
     *  the cached session could not be replayed for, which is not a "no". */
    outcome?: number; unscored?: number
    triggered?: number; not_rederived?: number
  }
  /** The refusal to print a rate, in trigger_log's own words. Never restated
   *  here: one rule, one language. */
  no_rate_why?: string
  rows?: SignalRow[]
  matched?: number
}

const INDICES = ['NIFTY', 'BANKNIFTY', 'SENSEX'] as const
type Kind = 'all' | 'entry' | 'arm'

const wash = (token: string, alpha: number | string) => `rgba(${rgbOf(token)},${alpha})`

/** A price as the log published it. Never rounded to a prettier number: `px`
 *  IS the close the rule fired on, and 78657.25 rounded to 78657 is a
 *  different bar's close on a setup measured in points. */
const px = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const signed = (n: number | null | undefined, digits = 1) =>
  n == null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(digits)}`

const inr = (n: number | null | undefined) =>
  n == null ? '—' : Math.round(n).toLocaleString('en-IN')

/** The logger's own identity key (trigger_log._key) — day, index, time, side,
 *  band, rule. Two indices can log the same minute, so nothing shorter is
 *  unique. */
const keyOf = (r: SignalRow, i: number) =>
  `${r.day}|${r.index}|${r.t}|${r.side}|${r.band}|${r.rule ?? 'legacy'}|${r.kind ?? 'entry'}|${i}`

export default function SignalsTab() {
  const pal = usePalette()
  const [rule, setRule] = useState<'5c' | 'all'>('5c')
  const [kind, setKind] = useState<Kind>('all')
  const [idx, setIdx] = useState<string>('')          // '' = every index
  const [pay, setPay] = useState<Payload | null>(null)
  /** Why nothing could be read, in the source's own words. Distinct from an
   *  empty table: see the three branches at the bottom of this file. */
  const [why, setWhy] = useState<string | null>(null)
  const [open, setOpen] = useState<Record<string, boolean>>({})

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/signals?rule=${rule}&kind=${kind}${idx ? `&idx=${idx}` : ''}`)
        const j: Payload = await r.json()
        if (!alive) return
        if (!j.ok) { setWhy(j.error || 'the server did not say why'); setPay(null); return }
        setWhy(null)
        setPay(j)
      } catch (e) {
        // The backend not answering is ALSO "could not check" — it is not an
        // empty log. Same branch, different reason, and the reason is named.
        if (alive) { setWhy(`the backend did not answer (${String(e)})`); setPay(null) }
      }
    }
    load()
    // The refresh threads append to the file while this is open, so a signal
    // that fires while the operator is on this tab appears without a reload.
    const id = window.setInterval(load, 30000)
    return () => { alive = false; window.clearInterval(id) }
  }, [rule, kind, idx])

  // Every count is coalesced field by field, not just object by object: a
  // backend older than the outcome fields answers with a five_c/arms that is
  // PRESENT but short, and `?? {}` on the object alone would leave the new
  // keys undefined and print "undefined of 3 rows".
  const p5 = pay?.five_c
  const five = {
    n: p5?.n ?? 0, buy: p5?.buy ?? 0, sell: p5?.sell ?? 0,
    scored: p5?.scored ?? 0, outcome: p5?.outcome ?? 0, unscored: p5?.unscored ?? 0,
  }
  const pa = pay?.arms
  const arms = {
    n: pa?.n ?? 0, buy: pa?.buy ?? 0, sell: pa?.sell ?? 0,
    setups: pa?.setups ?? 0, rearms: pa?.rearms ?? 0,
    interval: pa?.interval ?? [], no_minute: pa?.no_minute ?? 0,
    outcome: pa?.outcome ?? 0, unscored: pa?.unscored ?? 0,
    triggered: pa?.triggered ?? 0, not_rederived: pa?.not_rederived ?? 0,
  }
  const legacyN = pay?.legacy?.n ?? 0
  const rows = pay?.rows ?? []
  // `kind !== 'arm'` and not `rule === '5c'`: an arm row IS §5c, so grouping on
  // the rule alone would file it under the entry heading — the one place this
  // screen is not allowed to put it.
  const fiveRows = rows.filter(r => r.kind !== 'arm' && r.rule === '5c')
  const legacyRows = rows.filter(r => r.kind !== 'arm' && r.rule !== '5c')
  const armRows = rows.filter(r => r.kind === 'arm')

  /** How many rows the WHOLE log holds for the population this view selects —
   *  the number that decides "checked, empty" from "checked, filtered out".
   *  Deliberately blind to the index filter, which is what the third branch
   *  is for. Entries and arms are added only here, to compare against zero;
   *  no sum of the two is ever shown as a count of anything. */
  const entriesN = rule === '5c' ? five.n : (pay?.total ?? 0) - arms.n
  const inLog = kind === 'arm' ? arms.n : kind === 'entry' ? entriesN : entriesN + arms.n

  const btn = (on: boolean): CSSProperties => ({
    fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', padding: '4px 10px',
    borderRadius: 3, cursor: 'pointer',
    background: on ? wash(pal.accent, 0.12) : 'transparent',
    border: `1px solid ${on ? wash(pal.accent, 0.45) : pal.border}`,
    color: on ? pal.accent : pal.textMuted,
  })

  const card: CSSProperties = {
    background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
  }

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>

      {/* ── Controls ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <span className="micro-label">Signals — live trigger record</span>
        <div style={{ display: 'flex', gap: 5 }}>
          <button onClick={() => setRule('5c')} style={btn(rule === '5c')}>§5C ONLY</button>
          <button onClick={() => setRule('all')} style={btn(rule === 'all')}>ALL ROWS</button>
        </div>
        {/* Entries and arms are two populations. The filter names them, and
            the summary below counts them, separately. */}
        <div style={{ display: 'flex', gap: 5 }}>
          <button onClick={() => setKind('all')} style={btn(kind === 'all')}>BOTH KINDS</button>
          <button onClick={() => setKind('entry')} style={btn(kind === 'entry')}>ENTRIES</button>
          <button onClick={() => setKind('arm')} style={btn(kind === 'arm')}>ARMS</button>
        </div>
        <div style={{ display: 'flex', gap: 5 }}>
          <button onClick={() => setIdx('')} style={btn(idx === '')}>ALL INDICES</button>
          {INDICES.map(k => (
            <button key={k} onClick={() => setIdx(k)} style={btn(idx === k)}>{k}</button>
          ))}
        </div>
      </div>

      {/* ── Summary. §5c ENTRIES only, whole-log, never filtered ──────────── */}
      <div style={{ ...card, padding: '14px 16px', display: 'flex', gap: 26, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <Stat label="§5c entries" value={five.n} tone={pal.textPrimary} />
        {/* Green/red here is a SIDE, which is the one thing hue is allowed to
            mean. It labels the count, not a quality. */}
        <Stat label="buy · d3" value={five.buy} tone={pal.bull} />
        <Stat label="sell · u3" value={five.sell} tone={pal.bear} />
        <Stat label="scored" value={five.scored} tone={five.scored ? pal.textPrimary : pal.textMuted} />
        <span style={{ fontSize: 11, color: pal.textMuted, maxWidth: 420, lineHeight: 1.5 }}>
          Entries only — a trade the rule actually took. Counts are the whole log,
          per rule. They do not move with the filters above
          {legacyN ? `, they never include the ${legacyN} legacy rows` : ''}, and they
          never include an arm.
        </span>
      </div>

      {/* ── Arms. A SEPARATE card, never a column of the one above. ───────── */}
      <div style={{ ...card, padding: '14px 16px', display: 'flex', gap: 26, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <Stat label="arms · setups" value={arms.setups} tone={pal.textPrimary} />
        <Stat label="re-arms" value={arms.rearms} tone={pal.textMuted} />
        <Stat label="arm rows" value={arms.n} tone={pal.textMuted} />
        <Stat label="buy · d3" value={arms.buy} tone={pal.bull} />
        <Stat label="sell · u3" value={arms.sell} tone={pal.bear} />
        {/* The question the arms were started to answer: does the trigger
            condition earn its keep, or filter out winners? A count only —
            never a share, and never with `not_rederived` folded in, which is
            "we could not replay it", not "it did not fire". */}
        <Stat label="went on to trigger" value={arms.triggered}
          tone={arms.triggered ? pal.textPrimary : pal.textMuted} />
        <span style={{ fontSize: 11, color: pal.textMuted, maxWidth: 460, lineHeight: 1.5 }}>
          <strong style={{ color: pal.textSecondary }}>An arm is the setup arming, not a trade
          signal.</strong>{' '}
          A candle touched the band; the entry may never come. These are counted
          apart from the entries above and are never added to them. A run of falling
          lows is one setup, so each re-arm keeps its own row and{' '}
          <span className="mono">setups</span> counts the distinct ones.
          {arms.outcome > 0 && <> {arms.outcome} carr{arms.outcome === 1 ? 'ies' : 'y'} an
            outcome, measured from the arm candle's own close — never from an entry price,
            because none exists.</>}
          {arms.not_rederived > 0 && <> {arms.not_rederived} could not be replayed on their
            cached session, so whether they triggered is <strong>unknown</strong>, not “no”.</>}
        </span>
      </div>

      {/* ── The unscored-outcomes notice. Rule 2, stated as a fact. ───────── */}
      <div style={{
        // `border`, not `borderColor` on top of `card`: React warns when a
        // shorthand and its longhand are both set on one element, and the
        // warning is right — which one wins is render-order dependent.
        ...card, border: `1px solid ${wash(pal.accent, 0.35)}`, padding: '12px 16px',
        fontSize: 12.5, color: pal.textSecondary, lineHeight: 1.6,
      }}>
        {five.outcome === 0 && five.scored === 0 ? (
          <>
            <strong style={{ color: pal.textPrimary }}>Outcomes are unfilled.</strong>{' '}
            {five.outcome} of {five.n} §5c row{five.n === 1 ? '' : 's'} carry an outcome
            (MFE/MAE, the stop, the opposite-side bands). Fill them with{' '}
            <span className="mono" style={{ color: pal.accent }}>python trigger_log.py score</span>.
          </>
        ) : (
          <>
            <strong style={{ color: pal.textPrimary }}>
              {five.outcome} of {five.n} §5c rows carry an outcome
            </strong>
            {five.scored !== five.outcome ? `, ${five.scored} carry an f15/f30` : ''}. Each appears on
            its own row exactly as published, measured from the price the row names — never averaged
            into a headline here.
          </>
        )}
        {five.unscored > 0 && (
          <div style={{ marginTop: 6, color: pal.caution }}>
            {five.unscored} §5c row{five.unscored === 1 ? ' was' : 's were'} checked and could{' '}
            <strong>not</strong> be measured — each carries its own reason. That is not a flat trade;
            it is an unmeasured one, and the two are never shown as the same thing.
          </div>
        )}
        {/* The refusal, in the backend's words. Restating the threshold in
            TypeScript would be the same rule in two languages. */}
        <div style={{ marginTop: 8, color: pal.textMuted }}>
          {pay?.no_rate_why
            ?? 'No hit rate, win rate or expectancy is shown on this screen.'}
        </div>
      </div>

      {/* ── The two notes that qualify what a row IS. Nothing more. ───────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11.5, color: pal.textMuted, lineHeight: 1.55 }}>
        <span>
          Recorded at the scored interval — a record visible only on another timeframe never
          reaches this log.
        </span>
        <span>
          Arms are recorded at the <strong style={{ color: pal.textSecondary }}>3-minute canonical
          interval</strong>
          {arms.interval.length > 0 && arms.interval.join('/') !== '3'
            ? ` (this log holds ${arms.interval.join(' and ')}-minute arms)` : ''}
          {' '}— the interval §5c was scored on. 1-minute supplies <strong style={{ color: pal.textSecondary }}>timing
          only</strong>: <span className="mono">t_1m</span> names which minute inside the candle made the
          extreme, and can never create an arm the 3-minute tape did not have.
          {arms.no_minute > 0
            ? ` ${arms.no_minute} of ${arms.n} arm${arms.n === 1 ? '' : 's'} could not be given a minute; each carries the reason on its own row instead of a guess.`
            : ''}
        </span>
        <span>
          <span style={{ color: pal.bear, fontWeight: 700 }}>SELL · u3</span> rows — entries and arms
          alike — are collected on the operator's 2026-08-08 instruction. Selling an upper band was measured across five datasets
          and rejected (CHECKLIST C3) — no measured edge attaches to them, and none of the buy rule's
          numbers do either.
        </span>
        {!!pay?.unparsed && (
          <span style={{ color: pal.caution }}>
            {pay.unparsed} line{pay.unparsed === 1 ? '' : 's'} in the log could not be parsed and
            {pay.unparsed === 1 ? ' is' : ' are'} not shown or counted anywhere above.
          </span>
        )}
      </div>

      {/* ── The three absences, and the record ────────────────────────────── */}
      {why ? (
        /* COULD NOT CHECK. Nothing was read, so nothing can be said about what
           the log holds — including that it is empty. */
        <div style={{ ...card, border: `1px solid ${pal.caution}`, padding: 20, fontSize: 13, color: pal.caution }}>
          The log could not be read — {why}.
          <div style={{ marginTop: 6, fontSize: 12, color: pal.textSecondary }}>
            This is not “no signals yet”: nothing was checked. The record is{' '}
            <span className="mono">data/trigger_log.jsonl</span>, written live by the server's refresh
            threads.
          </div>
        </div>
      ) : !pay ? (
        <div style={{ ...card, padding: 20, fontSize: 13, color: pal.textMuted }}>reading the log…</div>
      ) : inLog === 0 ? (
        /* CHECKED, EMPTY. The file was read; it holds no row of the kind and
           rule being shown. Reachable only with a healthy read, so the
           sentence is one this screen can keep. */
        <div style={{ ...card, padding: 20, fontSize: 13, color: pal.textMuted }}>
          {kind === 'arm'
            ? 'No arms logged yet — the log was read and holds no arm row.'
            : rule === '5c'
              ? `No §5c ${kind === 'entry' ? 'entries' : 'rows'} logged yet — the log was read and holds none.`
              : 'The log was read and holds no rows yet.'}
          <div style={{ marginTop: 6, fontSize: 12 }}>
            {kind === 'arm'
              ? 'A session can legitimately produce none: an arm needs a 3-minute candle to touch d3 or u3 after 09:25, and it is written the refresh after that candle closes. Arms have only been recorded since 2026-08-12, so earlier sessions hold none by construction.'
              : rule === '5c' && legacyN > 0
                ? `${pay.total} rows are on disk, every one of them from the superseded one-candle rule.`
                : 'The first row appears the refresh after the setup fires on a closed bar.'}
          </div>
        </div>
      ) : rows.length === 0 ? (
        /* CHECKED, NON-EMPTY, FILTERED OUT. The rows exist; this view asked
           for a slice that has none. */
        <div style={{ ...card, padding: 20, fontSize: 13, color: pal.textMuted }}>
          No rows match this filter — {kind === 'arm'
            ? `${arms.n} arm row${arms.n === 1 ? '' : 's'}`
            : rule === '5c'
              ? `${five.n} §5c entr${five.n === 1 ? 'y' : 'ies'}${kind === 'all' && arms.n ? ` and ${arms.n} arm row${arms.n === 1 ? '' : 's'}` : ''}`
              : `${pay.total} rows`}{' '}
          {idx ? `in the log, none from ${idx}.` : 'in the log.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* §5c — the rule the operator actually scored. */}
          {fiveRows.length > 0 && (
            <Section
              title={`§5c — two-candle entry · ${fiveRows.length} row${fiveRows.length === 1 ? '' : 's'} shown`}
              note="The rule this screen counts."
            >
              {fiveRows.map((r, i) => (
                <Row key={keyOf(r, i)} r={r} legacy={false}
                  open={!!open[keyOf(r, i)]}
                  onToggle={() => setOpen(o => ({ ...o, [keyOf(r, i)]: !o[keyOf(r, i)] }))} />
              ))}
            </Section>
          )}

          {/* Arms — their own section, so nothing here can read as an entry. */}
          {armRows.length > 0 && (
            <Section
              title={`Arms — the setup arming · ${armRows.length} row${armRows.length === 1 ? '' : 's'} shown`}
              note={'NOT trade signals. Each row is one 3-minute candle touching its band; the '
                + 'entry may or may not follow, and no row here is counted as one. A re-arm is '
                + 'the same setup taking a new reference — its own row, marked, pointing back at '
                + 'the arm that started the setup.'}
            >
              {armRows.map((r, i) => (
                <ArmRow key={keyOf(r, i)} r={r}
                  open={!!open[keyOf(r, i)]}
                  onToggle={() => setOpen(o => ({ ...o, [keyOf(r, i)]: !o[keyOf(r, i)] }))} />
              ))}
            </Section>
          )}

          {/* Legacy — shown only under ALL, and never inside a §5c number. */}
          {legacyRows.length > 0 && (
            <Section
              title={`Void — §1 one-candle rule · ${legacyRows.length} row${legacyRows.length === 1 ? '' : 's'} shown`}
              note={'A DIFFERENT detector: it marked the d3 touch, not the §5c entry, and '
                + 'research-findings marks it void. Kept for the record, counted separately, '
                + 'never part of a §5c total.'}
              tone={pal.caution}
            >
              {legacyRows.map((r, i) => (
                <Row key={keyOf(r, i)} r={r} legacy
                  open={!!open[keyOf(r, i)]}
                  onToggle={() => setOpen(o => ({ ...o, [keyOf(r, i)]: !o[keyOf(r, i)] }))} />
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  )
}

// ── Pieces ──────────────────────────────────────────────────────────────────

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  const pal = usePalette()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span className="micro-label" style={{ color: pal.textMuted }}>{label}</span>
      <span className="mono" style={{ fontSize: 22, fontWeight: 700, color: tone, lineHeight: 1 }}>
        {value}
      </span>
    </div>
  )
}

function Section({ title, note, tone, children }: {
  title: string
  note: string
  tone?: string
  children: ReactNode
}) {
  const pal = usePalette()
  return (
    <div style={{
      background: pal.card, border: `1px solid ${tone ? wash(tone, 0.4) : pal.border}`,
      borderRadius: 12, overflow: 'hidden',
    }}>
      <div style={{
        padding: '10px 16px', borderBottom: `1px solid ${pal.border}`,
        background: tone ? wash(tone, 0.07) : 'transparent',
      }}>
        <div className="micro-label" style={{ color: tone ?? pal.textSecondary }}>{title}</div>
        <div style={{ fontSize: 11, color: pal.textMuted, marginTop: 3, lineHeight: 1.5, maxWidth: 760 }}>
          {note}
        </div>
      </div>
      <div>{children}</div>
    </div>
  )
}

/** One logged record. Everything printed here is a field the row published —
 *  no rule constant, no stop, no window, nothing derived. */
function Row({ r, legacy, open, onToggle }: {
  r: SignalRow
  legacy: boolean
  open: boolean
  onToggle: () => void
}) {
  const pal = usePalette()
  const buy = r.side === 'BUY'
  // Direction, and only direction. A side badge is the one place this app lets
  // green and red carry meaning.
  const sideCol = buy ? pal.bull : pal.bear
  const g = r.gamma ?? null
  const c = r.ctx ?? null
  const scored = r.f15 != null || r.f30 != null

  return (
    <div style={{
      borderBottom: `1px solid ${wash(pal.ink, 0.05)}`,
      padding: '10px 16px',
      opacity: legacy ? 0.85 : 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <span className="mono" style={{ fontSize: 12, color: pal.textSecondary, minWidth: 128 }}>
          {r.day ?? '—'} {r.t ?? '--:--'}
        </span>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: pal.textPrimary, minWidth: 78 }}>
          {r.index ?? '—'}
        </span>
        <span className="chip" style={{
          background: wash(sideCol, 0.12), color: sideCol, fontSize: 11,
        }}>
          {r.side ?? '—'} · {r.band ?? '—'}
        </span>
        <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: pal.textPrimary }}>
          {px(r.px)}
        </span>
        {legacy && (
          <span className="chip" style={{
            background: wash(pal.caution, 0.1), color: pal.caution, fontSize: 11,
            border: `1px solid ${wash(pal.caution, 0.35)}`,
          }}>
            void · §1 one-candle
          </span>
        )}
        {/* Forward move, per row, exactly as `score` published it — or an
            em-dash that says it was never filled. Never aggregated. */}
        <span className="mono" title={scored
          ? 'forward move in points, signed by side, filled by python trigger_log.py score'
          : 'unfilled — python trigger_log.py score fills f15/f30'}
          style={{ fontSize: 11.5, color: scored ? pal.textSecondary : pal.textMuted, marginLeft: 'auto' }}>
          f15 {signed(r.f15)} · f30 {signed(r.f30)}
        </span>
        <button onClick={onToggle} style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', padding: '2px 8px',
          borderRadius: 3, cursor: 'pointer', background: 'transparent',
          border: `1px solid ${pal.border}`, color: pal.textMuted,
        }}>{open ? 'LESS' : 'MORE'}</button>
      </div>

      {/* The detector's own receipt, verbatim and unwrapped in meaning: it is
          the only line that says which bars fired the rule. */}
      <div style={{ fontSize: 12, color: pal.textSecondary, marginTop: 6, lineHeight: 1.55 }}>
        {r.trigger || <span style={{ color: pal.textMuted }}>no receipt sentence was logged for this row</span>}
      </div>

      <Outcome r={r} />

      {/* The three context reads checklist #17/#18 are about. Brass border =
          structure; none of these is a direction. */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 7 }}>
        <Tag label="MM" value={g?.regime ?? null} />
        <Tag label="verdict" value={c?.verdict ?? null}
          tone={c?.verdict === 'CAUTION' ? pal.caution : undefined} />
        <Tag label="OI strength" value={r.oi_strength == null ? null : signed(r.oi_strength, 4)} mono />
      </div>

      {open && (
        <div style={{
          marginTop: 10, padding: '10px 12px', borderRadius: 8,
          background: pal.inset, border: `1px solid ${pal.border}`,
          display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {c?.line && (
            <div style={{ fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5 }}>{c.line}</div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(158px, 1fr))', gap: '6px 14px' }}>
            <Field k="breadth" v={c?.breadth ?? null} />
            <Field k="why" v={c?.vwhy ?? null} />
            <Field k="age" v={c?.age == null ? null : `${c.age}m`} />
            <Field k="z" v={c?.z == null ? null : c.z.toFixed(2)} mono />
            <Field k="30m range" v={c?.rng30 == null ? null : c.rng30.toFixed(1)} mono />
            <Field k="vol 30m" v={c?.vol30 == null ? null : `${Math.round(c.vol30 * 100)}%`} mono />
            <Field k="inside ±1σ" v={c?.inside1 == null ? null : `${Math.round(c.inside1 * 100)}%`} mono />
            <Field k="pin" v={c?.pin?.k == null ? null : `${inr(c.pin.k)} · ${signed(c.pin.dist, 0)} · ${c.pin.regime ?? '—'}`} mono />
            <Field k="call OI chg" v={inr(r.oi_call)} mono />
            <Field k="put OI chg" v={inr(r.oi_put)} mono />
            <Field k="gamma w_ce / w_pe" v={g?.w_ce == null && g?.w_pe == null ? null : `${signed(g?.w_ce, 2)} / ${signed(g?.w_pe, 2)}`} mono />
            <Field k="IV ce / pe" v={g?.iv_ce == null && g?.iv_pe == null ? null : `${g?.iv_ce ?? '—'} / ${g?.iv_pe ?? '—'}`} mono />
            <Field k="closed bar" v={r.closed_bar === true ? 'yes' : r.closed_bar === false ? 'no' : null} />
            <Field k="logged at" v={r.at == null ? null : new Date(r.at * 1000).toLocaleTimeString('en-GB')} mono />
            <OutcomeFields r={r} />
          </div>
          {!!c?.flips?.length && (
            <div>
              <div className="micro-label" style={{ marginBottom: 3 }}>flips on this bar</div>
              {c.flips.map((f, i) => (
                <div key={i} style={{ fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5 }}>· {f}</div>
              ))}
            </div>
          )}
          {!!c?.plays?.length && (
            <div>
              <div className="micro-label" style={{ marginBottom: 3 }}>plays the engine published on this bar</div>
              {c.plays.map((p, i) => (
                <div key={i} style={{ fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5 }}>· {p}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** One logged ARM. A deliberately DIFFERENT component from `Row`, not a flag
 *  on it: an arm has no entry price, no receipt sentence and no outcome, and
 *  a shared renderer would have to leave those columns blank — which is how a
 *  reader starts seeing an arm as a trade that merely lost its numbers. */
function ArmRow({ r, open, onToggle }: {
  r: SignalRow
  open: boolean
  onToggle: () => void
}) {
  const pal = usePalette()
  const buy = r.side === 'BUY'
  const sideCol = buy ? pal.bull : pal.bear
  const g = r.gamma ?? null
  const c = r.ctx ?? null
  // The line to beat, under whichever true name this row published.
  const refPx = buy ? r.ref_high : r.ref_low
  const refName = buy ? 'ref_high' : 'ref_low'

  return (
    <div style={{ borderBottom: `1px solid ${wash(pal.ink, 0.05)}`, padding: '10px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <span className="mono" style={{ fontSize: 12, color: pal.textSecondary, minWidth: 128 }}>
          {r.day ?? '—'} {r.t ?? '--:--'}
        </span>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: pal.textPrimary, minWidth: 78 }}>
          {r.index ?? '—'}
        </span>
        <span className="chip" style={{ background: wash(sideCol, 0.12), color: sideCol, fontSize: 11 }}>
          {r.side ?? '—'} · {r.band ?? '—'}
        </span>
        {/* The word, on every row. It is the one thing this section must never
            let a glance get wrong. */}
        <span className="chip" title="the setup arming — not a trade signal"
          style={{
            background: 'transparent', color: pal.textMuted, fontSize: 11,
            border: `1px solid ${pal.border}`, letterSpacing: '0.06em',
          }}>
          arm{r.interval == null ? '' : ` · ${r.interval}m`}
        </span>
        {r.rearm === true && (
          <span className="chip" title={`the same setup taking a new reference; it armed first at ${r.first_t ?? 'an unrecorded time'}`}
            style={{
              background: wash(pal.accent, 0.1), color: pal.accent, fontSize: 11,
              border: `1px solid ${wash(pal.accent, 0.35)}`,
            }}>
            re-arm{r.first_t ? ` · from ${r.first_t}` : ''}
          </span>
        )}
        <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: pal.textPrimary }}>
          {px(r.level)}
        </span>
        {/* Timing, or the absence of it said out loud. */}
        <span className="mono"
          title={r.t_1m
            ? 'the 1-minute bar inside this 3-minute candle that made the extreme — timing only'
            : r.t_1m_why ?? 'no minute was identified and no reason was recorded'}
          style={{
            fontSize: 11.5, marginLeft: 'auto',
            color: r.t_1m ? pal.textSecondary : pal.textMuted,
          }}>
          {r.t_1m ? `1m ${r.t_1m} · ${px(r.extreme_1m)}` : '1m — not identified'}
        </span>
        <button onClick={onToggle} style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', padding: '2px 8px',
          borderRadius: 3, cursor: 'pointer', background: 'transparent',
          border: `1px solid ${pal.border}`, color: pal.textMuted,
        }}>{open ? 'LESS' : 'MORE'}</button>
      </div>

      {/* What actually happened, in the row's own published numbers. No rule
          constant, no window, no stop — nothing this row did not carry. */}
      <div style={{ fontSize: 12, color: pal.textSecondary, marginTop: 6, lineHeight: 1.55 }}>
        {r.extreme == null || r.level == null
          ? <span style={{ color: pal.textMuted }}>this row logged no level or extreme for the touch</span>
          : <>The candle's {buy ? 'low' : 'high'} {px(r.extreme)} {buy ? 'reached' : 'tagged'}{' '}
            {r.band ?? 'the band'} {px(r.level)}
            {refPx == null ? '' : `, and an entry needs a later candle to close ${buy ? 'above' : 'below'} this one's ${buy ? 'high' : 'low'} ${px(refPx)}`}.
            {' '}No entry is claimed here.</>}
      </div>

      <Outcome r={r} />

      {!r.t_1m && r.t_1m_why && (
        <div style={{ fontSize: 11.5, color: pal.textMuted, marginTop: 5, lineHeight: 1.5 }}>
          The minute was not identified — {r.t_1m_why}.
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 7 }}>
        <Tag label="MM" value={g?.regime ?? null} />
        <Tag label="verdict" value={c?.verdict ?? null}
          tone={c?.verdict === 'CAUTION' ? pal.caution : undefined} />
        <Tag label="OI strength" value={r.oi_strength == null ? null : signed(r.oi_strength, 4)} mono />
      </div>

      {open && (
        <div style={{
          marginTop: 10, padding: '10px 12px', borderRadius: 8,
          background: pal.inset, border: `1px solid ${pal.border}`,
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(158px, 1fr))', gap: '6px 14px',
        }}>
          <Field k="interval" v={r.interval == null ? null : `${r.interval}m`} mono />
          <Field k="bucket" v={r.t ?? null} mono />
          <Field k={refName} v={refPx == null ? null : px(refPx)} mono />
          <Field k="level" v={r.level == null ? null : px(r.level)} mono />
          <Field k={buy ? '3m low' : '3m high'} v={r.extreme == null ? null : px(r.extreme)} mono />
          <Field k="1m minute" v={r.t_1m ?? null} mono />
          <Field k={buy ? '1m low' : '1m high'} v={r.extreme_1m == null ? null : px(r.extreme_1m)} mono />
          <Field k="re-arm" v={r.rearm == null ? null : r.rearm ? 'yes' : 'no'} />
          <Field k="setup armed at" v={r.first_t ?? null} mono />
          <Field k="breadth" v={c?.breadth ?? null} />
          <Field k="z" v={c?.z == null ? null : c.z.toFixed(2)} mono />
          <Field k="call OI chg" v={inr(r.oi_call)} mono />
          <Field k="put OI chg" v={inr(r.oi_put)} mono />
          <Field k="closed bar" v={r.closed_bar === true ? 'yes' : r.closed_bar === false ? 'no' : null} />
          <Field k="logged at" v={r.at == null ? null : new Date(r.at * 1000).toLocaleTimeString('en-GB')} mono />
          <OutcomeFields r={r} />
        </div>
      )}
    </div>
  )
}

/** The outcome's own fields, for the expanded view. Every first-touch clock
 *  the band read found, so "reached u2 at 12:30" is checkable against the
 *  chart rather than only summarised. Nothing is rendered at all when the row
 *  was never measured — `Outcome` above has already said which absence it is. */
function OutcomeFields({ r }: { r: SignalRow }) {
  const b = r.bands
  if (r.mfe == null && r.mae == null) return null
  const names = b?.side === 'd' ? (['d1', 'd2', 'd3'] as const) : (['u1', 'u2', 'u3'] as const)
  return (
    <>
      <Field k="anchor" v={r.anchor ?? null} />
      <Field k="anchor px" v={r.anchor_px == null ? null : px(r.anchor_px)} mono />
      <Field k="window" v={r.scored_from ? `${r.scored_from} → ${r.scored_to ?? '—'}` : null} mono />
      <Field k="stop px" v={r.stop_px == null ? null : px(r.stop_px)} mono />
      {/* Where the band price that placed the stop came from. A number the
          detector logged and one lifted out of its receipt sentence are both
          usable and are not the same provenance. */}
      <Field k="stop level from" v={r.stop_from ?? null} />
      {names.map(n => (
        <Field key={n} k={`${n} first touch`} v={b?.[n] ?? null} mono />
      ))}
      <Field k="furthest σ" v={b?.sigma == null ? null : `${signed(b.sigma, 2)} @${b.sigma_t ?? '—'}`} mono />
      {/* Not a defect count — how many candles in the window carried no
          readable band, said out loud rather than shown as a non-touch. */}
      <Field k="candles with no band" v={b?.no_band == null ? null : String(b.no_band)} mono />
    </>
  )
}

/** The operator's outcome, on its own line under a row.
 *
 *  *"check that after it generates any signals what the max market moves from
 *  price and did it touch the other side +-2 std +-3 std and beyond. because i
 *  try to hold the trade if oi is heavy on that side."* (2026-08-12)
 *
 *  Three renderings, never two: the row was measured, the row was CHECKED and
 *  could not be measured (its reason, verbatim), or nothing has been run over
 *  it yet. An unmeasured row and a trade that went nowhere would otherwise
 *  look identical, and they are opposite facts.
 *
 *  The ANCHOR is printed first and by name because every number after it is in
 *  points from that price, and an entry's and an arm's are different prices.
 *  The STOP and the MFE are printed side by side deliberately: a stopped-out
 *  row that then ran is exactly what the operator asked to be able to see. */
function Outcome({ r }: { r: SignalRow }) {
  const pal = usePalette()
  if (r.mfe == null && r.mae == null) {
    return r.unscored
      ? (
        <div style={{ fontSize: 11.5, color: pal.caution, marginTop: 6, lineHeight: 1.5 }}>
          Not scored — {r.unscored}
        </div>
      )
      : (
        <div style={{ fontSize: 11.5, color: pal.textMuted, marginTop: 6 }}>
          No outcome filled — <span className="mono">python trigger_log.py score</span> fills it.
        </div>
      )
  }
  const b = r.bands ?? {}
  // The furthest band actually touched, and whether price carried PAST it.
  // Touching u3 IS +3σ, so the level alone cannot tell a tag from a run
  // through it — `sigma` is what answers "and beyond".
  const far = b.furthest
    ? `${b.beyond ? 'beyond ' : ''}${b.furthest}${b.sigma == null ? '' : ` · ${signed(b.sigma, 2)}σ`}${b.sigma_t ? ` @${b.sigma_t}` : ''}`
    : 'not reached'
  const stop = r.stop_hit == null
    ? { text: 'stop not placeable', tone: pal.caution, tip: r.stop_why ?? undefined }
    : r.stop_hit
      ? { text: `stop HIT ${r.stop_t ?? ''}`.trim(), tone: pal.bear,
          tip: 'the operator’s 20-point stop broke here — and the measurement did NOT end: MFE/MAE keep running to the flat-by time, so "stopped out" and "would have worked" stay two separate facts' }
      : { text: 'stop held', tone: pal.textSecondary,
          tip: r.stop_px == null ? undefined : `no candle in the window reached ${px(r.stop_px)}` }
  return (
    <div style={{
      marginTop: 7, padding: '6px 9px', borderRadius: 6,
      background: pal.inset, border: `1px solid ${pal.border}`,
      display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'baseline',
      fontSize: 11.5, color: pal.textSecondary, lineHeight: 1.5,
    }}>
      <span className="mono" title={r.anchor === 'arm_close'
        ? 'an arm entered nothing, so every number here is measured from the ARM CANDLE’S own close'
        : 'measured from the close the rule entered on'}
        style={{ color: pal.textMuted }}>
        from {r.anchor === 'arm_close' ? 'arm close' : 'entry close'} {px(r.anchor_px)}
        {r.scored_to ? ` → ${r.scored_to}` : ''}
      </span>
      <span className="mono" title="furthest FAVOURABLE move in points, signed by side">
        MFE <strong style={{ color: pal.bull }}>{signed(r.mfe)}</strong>
        {r.mfe_t ? ` @${r.mfe_t}` : ''}
      </span>
      <span className="mono" title="furthest ADVERSE move in points, signed by side">
        MAE <strong style={{ color: pal.bear }}>{signed(r.mae)}</strong>
        {r.mae_t ? ` @${r.mae_t}` : ''}
      </span>
      <span className="mono" title={stop.tip} style={{ color: stop.tone }}>{stop.text}</span>
      <span className="mono" title={'how far the OPPOSITE side of the band was reached — the side '
        + 'the operator targets. Read LIVE: each candle against its own bands, never the ones '
        + 'frozen at the anchor, because the VWAP drifts all day and they trail band to band.'}>
        other side {far}
      </span>
      {r.kind === 'arm' && (
        <span className="mono" title={r.triggered == null
          ? r.trigger_why ?? 'not re-derived'
          : r.triggered ? 'the setup went on to fire' : r.trigger_why ?? 'the setup never fired'}
          style={{ color: r.triggered == null ? pal.caution : pal.textSecondary }}>
          {r.triggered == null
            ? 'trigger NOT re-derived'
            : r.triggered ? `triggered ${r.trigger_t ?? ''}`.trim() : 'never triggered'}
        </span>
      )}
    </div>
  )
}

/** A context read as published. `null` prints as an em-dash and says so on
 *  hover — a missing read is not a neutral read. */
function Tag({ label, value, tone, mono }: {
  label: string
  value: string | null
  tone?: string
  mono?: boolean
}) {
  const pal = usePalette()
  const col = value == null ? pal.textMuted : tone ?? pal.textSecondary
  return (
    <span title={value == null ? 'this row logged no value for it' : undefined} style={{
      display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11,
      padding: '2px 8px', borderRadius: 4,
      border: `1px solid ${value == null ? pal.border : wash(pal.accent, 0.3)}`,
      color: col,
    }}>
      <span style={{ color: pal.textMuted, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{label}</span>
      <span className={mono ? 'mono' : undefined} style={{ fontWeight: 600 }}>{value ?? '—'}</span>
    </span>
  )
}

function Field({ k, v, mono }: { k: string; v: string | null; mono?: boolean }) {
  const pal = usePalette()
  return (
    <div style={{ display: 'flex', gap: 6, fontSize: 11, alignItems: 'baseline' }}>
      <span style={{ color: pal.textMuted, letterSpacing: '0.04em', textTransform: 'uppercase' }}>{k}</span>
      <span className={mono ? 'mono' : undefined}
        style={{ color: v == null ? pal.textMuted : pal.textSecondary, fontWeight: 600 }}>
        {v ?? '—'}
      </span>
    </div>
  )
}
