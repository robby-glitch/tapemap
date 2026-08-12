import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { MONO } from '../theme'
import type { palette } from '../theme'
// The OI strip below the chart formats these same figures with `crl`. Measured
// live 2026-08-07: `chg_dir` is a raw OI delta (6,545,045 that afternoon), so a
// plain toFixed(2) printed "+6545045.00" — unreadable, and a DIFFERENT
// rendering of a number the strip was already showing as +65.45L. One
// formatter, so the two surfaces can never disagree about one figure.
import { crl } from './ZoneRead'
import type { TapeBar, RotationSignal, RunState, FlowRow } from '../data'
import { SCORED_INTERVAL } from '../data'

type Pal = ReturnType<typeof palette>

/**
 * SETUP CHECK — the panel in the rail beside the chart.
 *
 * The operator's ask, 2026-08-07: *"isme apni checklist or setup rules likh
 * sakte with a check box as more things checks more confidence in the trade"*.
 * Design confirmed off `ui-v2/comps/trade-setup-check.html`, variant B.
 *
 * ── The one thing this panel must not become ───────────────────────────────
 * A scoring widget. Only §5c's trigger is scored (68.4% at +30m, n=19).
 * CHECKLIST C7 measured compression-as-a-filter as HARMFUL across three
 * datasets; C11 measured a 40% OI-strength entry veto as removing 10 of 12
 * signals INCLUDING 9 WINNERS. One blended "confidence" number would render
 * both findings as UI and quietly argue against the trades the data says to
 * keep. So there are TWO tallies and they are never added together: the
 * trigger either stands or it does not, and everything else is colour.
 *
 * ── Nothing here re-derives a rule ─────────────────────────────────────────
 * Every AUTO row reads ONE published field. The 09:25 gate and the
 * first-of-run fold are NOT re-checked here — they live inside
 * `band_rotation.run_states`, and the last time a rule of this setup existed
 * in two languages the chart and the scorer disagreed for weeks. This panel
 * displays the state machine; it does not run a second copy of it.
 *
 * ── Three tick marks, not two ──────────────────────────────────────────────
 * Brass = the tool measured it. Ink = the operator's own hand. Dashed amber =
 * could not be checked. That is A1's three sentences as three marks, and it
 * costs nothing to honour because `trap` and `confirm` ALREADY arrive as
 * three-state fields with the backend's own sentence attached. Never green:
 * theme.ts reserves green and red for direction.
 *
 * ── The stop ───────────────────────────────────────────────────────────────
 * Shown since 2026-08-09, and only because the BACKEND now publishes it
 * (`run_state.stop`, from `band_rotation._stop_px`). It is settled at 20
 * points (D6) and defined once, as `band_rotation.OPERATOR_STOP_PTS`.
 * This panel must never compute it: `level` minus 20 in TypeScript would put
 * one rule in two languages, which is exactly how the 09:25 gate drifted for
 * weeks. A payload without the field therefore shows NO stop line at all —
 * absence is the correct rendering of "the server did not say", and the
 * operator has their own settled stop to fall back on.
 */

/** What a row's box shows. `auto-*` is the tool's reading, `man-*` the
 *  operator's. `auto-unknown` is the third sentence and must never be
 *  collapsed into `auto-off` — "we could not check" is not "it is false". */
type TickState = 'auto-on' | 'auto-off' | 'auto-unknown' | 'man-on' | 'man-off'

interface Row {
  /** Stable across sessions — it is the localStorage key for a manual tick. */
  id: string
  text: string
  state: TickState
  /** The backend's own words or its own numbers. Never a rephrasing. */
  receipt?: string
  /** True when the receipt is a disclosure rather than a measurement. */
  warn?: boolean
  /** Custom rows the operator wrote, which they can also delete. */
  custom?: boolean
}

/** One line of the session list: an entry the record published, plus the one
 *  fact about what came after it that this codebase actually holds.
 *
 *  There is no P&L field, no exit price and no outcome here, and that is not
 *  an omission to be filled in later — nothing in the payload knows any of
 *  them. The operator manages and TRAILS the trade themselves ("my stop is
 *  never vwap i like to trail"), so the tool has no idea where they left. */
interface SessionRow {
  /** Bar index into the day's bars — the sort key, and unique per side. */
  i: number
  t: string
  side: 'BUY' | 'SELL'
  band: string
  level: number | null
  /** The line that broke, under the NAME band_rotation published it as. A low
   *  carried as `ref_high` is a lie a reader cannot catch, so the two names
   *  travel all the way to the screen. */
  brkName: 'ref_high' | 'ref_low'
  brk: number | null
  stop: number | null
  /** `exit_why`, and the bar it landed on. run_states: "the bar the re-fire
   *  lock cleared". §5c point 7's lock — after an entry the NEXT setup may not
   *  arm until VWAP is touched (or at once if stopped). It says nothing about
   *  where this trade ended, and must never be worded as though it does. */
  lockT: string | null
  lockWhy: 'stop' | 'vwap' | null
  /** The states array was there and no bar cleared the lock. */
  lockOpen: boolean
  /** No states array reached us, so the lock line stays silent rather than
   *  reading as "never cleared" — the third sentence again. */
  lockKnown: boolean
}

interface Props {
  pal: Pal
  /** The session key. Ticks are stored against it, so a new day starts empty
   *  on its own and yesterday's ticks can never be shown as today's. */
  day: string
  /** The cursor-clamped bar — the same one the strip above reads. */
  bar: TapeBar
  /** Where the two-candle setup stands on THIS bar. Null when the backend
   *  does not publish it, which is stated rather than faked as WAITING. */
  runState: RunState | null
  /** Why `runState` is null, in data.ts's own words. Empty when it isn't. */
  runStateWhy: string
  /** The SELL mirror's state on this bar. The panel shows whichever side is
   *  live and NAMES which one — sitting on WAITING while the other side is
   *  armed would misreport the machine outright. */
  runStateSell: RunState | null
  /** The SELL mirror's entry record on this bar, for the context receipts. */
  entrySell: RotationSignal | null
  /** §5c's entry record for this bar, when one exists. `trap` and `confirm`
   *  live here, so before a trigger they are honestly unavailable. */
  entry: RotationSignal | null
  /** The latest Trending-OI mark. Null when the poller has none. */
  flow: FlowRow | null
  flowWhy: string
  /** The interval, in minutes, the backend says these bars ARE. §5c's 68.4%
   *  was measured at SCORED_INTERVAL and nowhere else, so anything but that —
   *  including `null`, a backend that will not say — makes the trigger group's
   *  number inapplicable, and the group says so. */
  publishedInterval?: number | null
  /** ── The day's §5c record ──────────────────────────────────────────────
   *  Everything above reads the CURSOR'S BAR, so a completed setup leaves the
   *  panel entirely: the operator had a full SELL sequence 09:25→09:38 and at
   *  10:12 this panel showed `WAITING · BUY · d3` and nothing else. These four
   *  arrays are the whole DAY, so an entry stays on screen whatever the
   *  machine is doing now.
   *
   *  `sessionRun` / `sessionRunSell` are the ENTRIES (TradeTab's `rotationRun`
   *  pair). `sessionStates` / `sessionStatesSell` are read for exactly ONE
   *  field — `exit_why`, which run_states' own docstring defines as "the bar
   *  the re-fire lock cleared". It is NOT a trade exit and is never rendered
   *  as one.
   *
   *  All optional: absent, the list does not render at all and OneTab's panel
   *  is byte-for-byte what it was. */
  sessionRun?: (RotationSignal | null)[] | null
  /** Why `sessionRun` is null, in data.ts's own words. Empty when it isn't. */
  sessionRunWhy?: string
  sessionRunSell?: (RotationSignal | null)[] | null
  /** Why `sessionRunSell` is null. Kept SEPARATE from the buy side's: one side
   *  can arrive while the other cannot, and "checked, nothing fired" must not
   *  be printed over a side that was never checked. */
  sessionRunSellWhy?: string
  sessionStates?: RunState[] | null
  sessionStatesSell?: RunState[] | null
  /** ONE-SCREEN rendering (src/one/OneTab.tsx). The state block and the
   *  TRIGGER group render exactly as they always have; the unscored groups —
   *  "Saath de raha hai", "Mera read", Reset and the two tallies — move behind
   *  a closed disclosure. Nothing is dropped: the disclosure's own summary
   *  carries the agree tally, so a collapsed group can never read as an empty
   *  one, and one click restores the full panel.
   *
   *  ABSENT (the Trade tab) the render is unchanged, byte for byte. */
  compact?: boolean
}

const LS_RULES = 'tape.check.rules'
const LS_TICKS = 'tape.check.ticks'

/** The operator's own rules. A corrupt value reads as "none" rather than
 *  throwing — an unusable list must not take the whole tab down. */
function loadRules(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(LS_RULES) || '[]')
    return Array.isArray(v) ? v.filter((s) => typeof s === 'string' && s.trim()) : []
  } catch { return [] }
}

/** Ticks, stored WITH the day they were made on. Reading them back for a
 *  different day returns nothing, which IS the daily reset — no clock, no
 *  scheduled job, and no way for a stale tick to survive into a new session. */
function loadTicks(day: string): Set<string> {
  try {
    const v = JSON.parse(localStorage.getItem(LS_TICKS) || 'null')
    if (!v || v.day !== day || !Array.isArray(v.ids)) return new Set()
    return new Set(v.ids.filter((s: unknown) => typeof s === 'string') as string[])
  } catch { return new Set() }
}

const CHECK_D = 'M2.5 6.4l2.4 2.4 4.6-5.2'

function Tick({ pal, state }: { pal: Pal; state: TickState }) {
  const on = state === 'auto-on' || state === 'man-on'
  const unknown = state === 'auto-unknown'
  // Brass for the tool's own reading, ink for the operator's. The hue carries
  // WHO CHECKED, which is the distinction this panel exists to keep.
  const fill = state === 'auto-on' ? pal.accent : pal.textPrimary
  return (
    <span aria-hidden="true" style={{
      width: 14, height: 14, flexShrink: 0, marginTop: 1, borderRadius: 3,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      backgroundColor: on ? fill : 'transparent',
      border: `1px ${unknown ? 'dashed' : 'solid'} `
        + `${on ? fill : unknown ? pal.caution : pal.border}`,
    }}>
      {on && (
        <svg viewBox="0 0 12 12" width="10" height="10" fill="none" stroke={pal.card}
             strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d={CHECK_D} />
        </svg>
      )}
      {unknown && (
        <svg viewBox="0 0 12 12" width="10" height="10" fill="none" stroke={pal.caution}
             strokeWidth="2.4" strokeLinecap="round">
          <path d="M6 2.6v4.2" /><path d="M6 9.3v.1" />
        </svg>
      )}
    </span>
  )
}

export default function SetupCheck({
  pal, day, bar, runState, runStateWhy, runStateSell, entry, entrySell,
  flow, flowWhy, publishedInterval = null, compact = false,
  sessionRun, sessionRunWhy = '', sessionRunSell, sessionRunSellWhy = '',
  sessionStates, sessionStatesSell,
}: Props) {
  // The scored interval is a fact about §5c, so it is read from the one place
  // that owns it rather than typed as a 3 here. At anything else the trigger
  // group's measured number does not describe what is on screen.
  const offScore = publishedInterval !== SCORED_INTERVAL
  /* Which side the panel is reading.
     A state that is not WAITING wins, because that is the side with something
     happening. If BOTH are live the BUY side wins and the header says the sell
     side is also armed -- picking silently would hide half the machine, and
     preferring the SCORED side is the only defensible tie-break.
     This is a display choice over two published arrays; it decides nothing
     about the market and computes no rule. */
  const buyLive = !!runState && runState.state !== 'WAITING'
  const sellLive = !!runStateSell && runStateSell.state !== 'WAITING'
  const showSell = sellLive && !buyLive
  const st = showSell ? runStateSell : runState
  const sig = showSell ? entrySell : entry
  const bothLive = buyLive && sellLive
  const [rules, setRules] = useState<string[]>(loadRules)
  const [ticks, setTicks] = useState<Set<string>>(() => loadTicks(day))
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState('')

  // Re-read on a day change rather than clearing: the operator may scrub back
  // to an earlier session, and that session's ticks are still ITS ticks.
  useEffect(() => { setTicks(loadTicks(day)) }, [day])

  const toggle = (id: string) => {
    setTicks((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      localStorage.setItem(LS_TICKS, JSON.stringify({ day, ids: [...next] }))
      return next
    })
  }
  const reset = () => {
    setTicks(new Set())
    localStorage.setItem(LS_TICKS, JSON.stringify({ day, ids: [] }))
  }
  const saveRules = (next: string[]) => {
    setRules(next)
    localStorage.setItem(LS_RULES, JSON.stringify(next))
  }

  const f1 = (n: number | null | undefined) =>
    typeof n === 'number' && Number.isFinite(n) ? n.toFixed(1) : null

  // TWO decimals, only in the session list, and only because that list is a
  // RECORD of what was published. NIFTY ticks at 0.05, so f1 turns a genuine
  // 24551.25 into 24551.3 — fine for a live read the operator is watching move,
  // wrong for a row they may check against the log tomorrow.
  const f2 = (n: number | null | undefined) =>
    typeof n === 'number' && Number.isFinite(n) ? n.toFixed(2) : null

  // ── TRIGGER: three reads of `run_state`, no rule re-implemented ──────────
  const trigger: Row[] = useMemo(() => {
    if (!st) return []
    // A buy's line to beat is a HIGH, a sell's is a LOW. They arrive under
    // different names precisely so this cannot be got wrong silently.
    const brk = showSell ? st.ref_low : st.ref_high
    const ref = st.ref_i != null && brk != null
    const fired = st.state === 'TRIGGERED' || st.state === 'IN_TRADE'
    return [
      {
        id: 't.ref',
        text: `${showSell ? 'u3' : 'd3'} chhua, reference candle bani`,
        state: ref ? 'auto-on' : 'auto-off',
        receipt: ref
          ? `${showSell ? 'u3' : 'd3'} ${f1(st.level) ?? '—'}${st.t ? ` · ${st.t}` : ''}`
          : `abhi kisi candle ne ${showSell ? 'u3' : 'd3'} nahi chhua`,
      },
      {
        id: 't.win', text: 'Window abhi khula hai',
        state: st.candles_left != null && st.candles_left > 0 ? 'auto-on'
          : ref ? 'auto-off' : 'auto-unknown',
        receipt: st.candles_left != null
          ? `${st.candles_left} candle baaki`
          : 'koi live reference nahi, toh ginne ko window bhi nahi',
        warn: st.candles_left == null && !ref,
      },
      {
        id: 't.brk',
        text: `Close ne reference ${showSell ? 'low' : 'high'} toda`,
        state: fired ? 'auto-on' : 'auto-off',
        receipt: brk != null
          ? `todna hai ${showSell ? '<' : '>'} ${f1(brk)}`
          : `reference ${showSell ? 'low' : 'high'} abhi nahi bana`,
      },
    ]
  }, [st, showSell])

  // ── CONTEXT: unscored. Two kinds of row, and the difference is deliberate.
  // AUTO rows read a published three-state field. RECEIPT+MANUAL rows print the
  // number the payload actually carries and let the OPERATOR decide — because
  // an auto tick on OI strength would encode the very veto C11 disproved, and
  // OI *deceleration* is a second derivative nothing publishes.
  const context: Row[] = useMemo(() => {
    const out: Row[] = []
    const g = bar.gamma
    // The operator's own reading, 2026-08-07: positive gamma damps the move so
    // a mean-reversion entry is favoured; negative gamma amplifies it. Their
    // #17, which research-findings §4 records as mechanically sound and NOT YET
    // SCORED — there is no per-trigger gamma history in the cache. Said plainly
    // in the group note rather than dressed up as a measured edge.
    //
    // ONLY PINNED earns a sentence. The first cut of this row read
    // `Gamma ${regime} — ek-tarfa chaal ka mahaul` for everything else, and on
    // the live 2026-08-07 tape that rendered "Gamma NEUTRAL — ek-tarfa chaal ka
    // mahaul", which is an invented claim (A2): NEUTRAL is not negative gamma,
    // and FLOOR/CEILING describe which side dealers defend, not whether the
    // move is amplified. The payload publishes a regime LABEL, not a gamma
    // sign, so any other label is stated and left uncharacterised.
    out.push(g ? {
      id: 'c.gamma',
      text: g.regime === 'PINNED' ? 'Gamma PINNED — reversion ke haq mein'
        : `Gamma ${g.regime}`,
      state: g.regime === 'PINNED' ? 'auto-on' : 'auto-off',
      receipt: `${g.regime} · proxy ${g.proxy.toFixed(2)}`
        + ` · CE ${g.w_ce.toFixed(2)} / PE ${g.w_pe.toFixed(2)}`
        + (g.regime === 'PINNED' ? '' : ' — pin ke alawa is rule ka kuch kehna nahi'),
    } : {
      id: 'c.gamma', text: 'Gamma regime',
      state: 'auto-unknown',
      receipt: 'is bar ka gamma block nahi aaya — padha hi nahi ja saka', warn: true,
    })

    // trap / confirm arrive on the ENTRY record, so before a trigger they are
    // genuinely unavailable — not false. That is the whole reason
    // `auto-unknown` exists as its own mark.
    out.push(sig ? {
      id: 'c.trap',
      text: sig.trap === 'CLEAR' ? 'Index pehle sikud raha tha'
        : sig.trap === 'SUSPECT' ? 'Index pehle se faila hua tha — trap ka shaq'
          : 'Compression check nahi ho paaya',
      state: sig.trap === 'CLEAR' ? 'auto-on'
        : sig.trap === 'SUSPECT' ? 'auto-off' : 'auto-unknown',
      receipt: sig.trap_why, warn: sig.trap === 'UNKNOWN',
    } : {
      id: 'c.trap', text: 'Index pehle sikud raha tha',
      state: 'auto-unknown',
      receipt: 'entry record abhi nahi bana, toh compression verdict bhi nahi', warn: true,
    })

    out.push(sig ? {
      id: 'c.conf',
      text: sig.confirm === 'CONFIRMED' ? 'Doosri leg ne confirm kiya'
        : sig.confirm === 'UNCONFIRMED' ? 'Doosri leg ne confirm NAHI kiya'
          : 'Doosri leg check nahi ho payi',
      state: sig.confirm === 'CONFIRMED' ? 'auto-on'
        : sig.confirm === 'UNCONFIRMED' ? 'auto-off' : 'auto-unknown',
      receipt: sig.confirm_why, warn: sig.confirm === 'UNKNOWN',
    } : {
      id: 'c.conf', text: 'Doosri leg ne confirm kiya',
      state: 'auto-unknown',
      receipt: 'entry record abhi nahi bana', warn: true,
    })

    // RECEIPT + MANUAL. C11: a 40% OI-strength veto would have removed 10 of 12
    // signals including 9 winners — at a d3 low the flow is structurally
    // CALL-heavy and the put-heaviness arrives AFTER the turn. So the tool
    // states the reading and the operator decides what it is worth.
    out.push({
      id: 'c.oi',
      text: 'OI ka jhukaav mere haq mein',
      state: ticks.has('c.oi') ? 'man-on' : 'man-off',
      receipt: flow
        ? `${flow.diff >= 0 ? 'PUT' : 'CALL'}-heavy ${Math.abs(flow.strength * 100).toFixed(0)}%`
          + ` · ${flow.time}${flow.pcr != null ? ` · PCR ${flow.pcr.toFixed(2)}` : ''}`
        : `Trending OI nahi aayi — ${flowWhy}`,
      warn: !flow,
    })
    out.push({
      id: 'c.oidecel',
      text: 'OI banne ki raftaar dheemi pad rahi',
      state: ticks.has('c.oidecel') ? 'man-on' : 'man-off',
      // Deliberately not auto: the rule is the SLOPE OF `oi_slope` (their own
      // words — "oi is lagging so we need to prempt by the change"), and
      // nothing in the payload publishes that second derivative. Computing it
      // here would make the UI derive a market quantity, which this codebase
      // does not do. So: the reading it DOES have, and the gap said out loud.
      receipt: flow?.chg_dir != null
        ? `Δ ${crl(flow.chg_dir)} — raftaar khud kahin publish nahi hoti, dekh kar tick karo`
        : 'raftaar kahin publish nahi hoti — khud dekh kar tick karo',
    })
    out.push({
      id: 'c.pair',
      text: 'Doosri leg apne +2σ se ghoom rahi hai',
      state: ticks.has('c.pair') ? 'man-on' : 'man-off',
      receipt: 'premium-matched jodi, dono ≥ ₹100 — ye chart is payload mein nahi hai',
    })
    return out
  }, [bar.gamma, sig, flow, flowWhy, ticks])

  // ── THE DAY'S ENTRIES ────────────────────────────────────────────────────
  // One pass per side over the published arrays. Nothing is re-derived: every
  // field below is copied off a record, and where a record has no field the
  // row carries null and the render says so.
  const sessionRows: SessionRow[] = useMemo(() => {
    const out: SessionRow[] = []
    const collect = (
      entries: (RotationSignal | null)[] | null | undefined,
      states: RunState[] | null | undefined,
    ) => {
      if (!entries) return
      entries.forEach((e, i) => {
        if (!e) return
        const sell = e.side === 'SELL'
        // `ref_low` rides on the SELL record only (band_rotation emits
        // `"ref_low" if sell else "ref_high"`). data.ts is pristine and types
        // the BUY name, so the sell name is read through a local narrowing
        // rather than by widening the shared interface.
        const brk = sell
          ? (e as { ref_low?: number | null }).ref_low ?? null
          : e.ref_high ?? null
        // The first bar AFTER the entry that cleared the lock. The lock is
        // always cleared before the same side can arm again, so the first hit
        // is this entry's and cannot belong to a later one.
        let lockT: string | null = null
        let lockWhy: 'stop' | 'vwap' | null = null
        if (states) {
          for (let j = i + 1; j < states.length; j++) {
            const s = states[j]
            if (s && s.exit_why) { lockT = s.t; lockWhy = s.exit_why; break }
          }
        }
        out.push({
          i, t: e.t || '—', side: sell ? 'SELL' : 'BUY',
          band: e.band, level: e.level ?? null,
          brkName: sell ? 'ref_low' : 'ref_high', brk,
          stop: e.stop ?? null,
          lockT, lockWhy, lockOpen: !!states && !lockWhy, lockKnown: !!states,
        })
      })
    }
    collect(sessionRun, sessionStates)
    collect(sessionRunSell, sessionStatesSell)
    // Newest first. Sorted on the BAR INDEX, not the "HH:MM" label: both
    // arrays are aligned 1:1 with the same `bars`, so the index orders the two
    // sides against each other exactly, and a bar that carried no label still
    // lands in its true place.
    return out.sort((a, b) => b.i - a.i)
  }, [sessionRun, sessionRunSell, sessionStates, sessionStatesSell])

  const mine: Row[] = rules.map((text, i) => ({
    id: `m.${i}`, text, custom: true,
    state: ticks.has(`m.${i}`) ? 'man-on' : 'man-off',
  }))

  // One pass over the rows themselves, so the number the operator reads can
  // never drift from the rows on screen — the same contract the chart legend
  // keeps by counting through the overlay's own predicate (A5).
  const onOf = (rs: Row[]) => rs.filter((r) => r.state === 'auto-on' || r.state === 'man-on').length
  const agree = [...context, ...mine]

  const label: CSSProperties = {
    fontSize: 9.5, fontWeight: 700, letterSpacing: '0.1em',
    textTransform: 'uppercase', color: pal.textSecondary,
  }
  const rowBtn: CSSProperties = {
    display: 'flex', gap: 8, alignItems: 'flex-start', width: 'calc(100% + 10px)',
    margin: '0 -5px', padding: '4px 5px', textAlign: 'left', font: 'inherit',
    color: 'inherit', background: 'none', border: 0, borderRadius: 4, cursor: 'pointer',
  }

  const RowBody = ({ r }: { r: Row }) => (
    <>
      <Tick pal={pal} state={r.state} />
      <span style={{ minWidth: 0, flex: 1 }}>
        <span style={{
          fontSize: 11.5, lineHeight: 1.35, display: 'block',
          color: r.state === 'auto-on' || r.state === 'man-on' ? pal.textPrimary : pal.textSecondary,
        }}>{r.text}</span>
        {r.receipt && (
          <span style={{
            fontSize: 10, lineHeight: 1.35, display: 'block', marginTop: 1,
            fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
            color: r.warn ? pal.caution : pal.textMuted,
          }}>{r.receipt}</span>
        )}
      </span>
      {r.custom && (
        <span
          role="button" tabIndex={0} title="Ye rule hata do"
          aria-label={`Rule hatao: ${r.text}`}
          onClick={(e) => {
            e.stopPropagation()
            saveRules(rules.filter((_, i) => `m.${i}` !== r.id))
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              e.stopPropagation()
              saveRules(rules.filter((_, i) => `m.${i}` !== r.id))
            }
          }}
          style={{ fontSize: 13, lineHeight: 1, color: pal.textMuted, padding: '0 2px', cursor: 'pointer' }}
        >×</span>
      )}
    </>
  )

  const Group = ({ name, count, note, rows }: {
    name: string; count: string; note?: string; rows: Row[]
  }) => (
    <div style={{ marginTop: 14 }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 6,
        paddingBottom: 5, borderBottom: `1px solid ${pal.border}`, marginBottom: 7,
      }}>
        <span style={label}>{name}</span>
        <span style={{
          fontFamily: MONO, fontSize: 10, fontWeight: 700, color: pal.textMuted,
          fontVariantNumeric: 'tabular-nums',
        }}>{count}</span>
      </div>
      {note && (
        <div style={{ fontSize: 10, color: pal.textMuted, lineHeight: 1.45, margin: '-2px 0 8px' }}>
          {note}
        </div>
      )}
      {rows.map((r) => {
        // An AUTO row is not clickable ON PURPOSE: if the operator can overrule
        // the tool's reading, the row is a MANUAL row. A half-owned tick is a
        // lie about who checked.
        const manual = r.state === 'man-on' || r.state === 'man-off'
        return manual ? (
          <button key={r.id} onClick={() => toggle(r.id)} aria-pressed={r.state === 'man-on'}
                  style={rowBtn}><RowBody r={r} /></button>
        ) : (
          <div key={r.id} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '4px 0' }}>
            <RowBody r={r} />
          </div>
        )
      })}
    </div>
  )

  const stateWord = st
    ? (st.exit_why ? 'BAAHAR' : st.state === 'IN_TRADE' ? 'TRADE MEIN' : st.state)
    : null

  /* The three blocks below were inline in the return until 2026-08-11. They
     are named now ONLY so the compact rendering can re-parent them without a
     second copy — the JSX is unchanged, so the Trade tab's tree is identical.
     A forked "compact version" of these rows is exactly how one reading of the
     machine becomes two. */
  const resetBtn = (
    <button
      onClick={reset}
      title="Aaj ke saare manual tick hata do. Har naye din ye apne aap saaf ho jaate hain."
      style={{
        fontSize: 9.5, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
        padding: '3px 7px', borderRadius: 4, cursor: 'pointer',
        border: `1px solid ${pal.border}`, background: 'transparent', color: pal.textMuted,
      }}
    >Reset</button>
  )

  /* ── AAJ KE SIGNAL ─────────────────────────────────────────────────────
     The day's entries, which stay put when the machine returns to WAITING.
     Rendered only when the arrays were PASSED — `undefined` on both means the
     caller (OneTab) never offered them, and an absent list is not the same
     claim as an empty one.

     Deliberately NOT inside `compact`'s disclosure: the whole complaint was a
     signal disappearing, and a fold is a slower way of disappearing. */
  const sessionOffered = sessionRun !== undefined || sessionRunSell !== undefined
  const buyGone = !sessionRun
  const sellGone = !sessionRunSell
  const sessionWhy = sessionRunWhy || sessionRunSellWhy
  const anySell = sessionRows.some((r) => r.side === 'SELL')

  const sessionBlock = sessionOffered && (
    <div style={{ marginTop: 14 }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 6,
        paddingBottom: 5, borderBottom: `1px solid ${pal.border}`, marginBottom: 7,
      }}>
        <span style={label}>Aaj ke signal</span>
        <span style={{
          fontFamily: MONO, fontSize: 10, fontWeight: 700, color: pal.textMuted,
          fontVariantNumeric: 'tabular-nums',
        }}>
          {publishedInterval ? `${publishedInterval}m · ` : ''}{sessionRows.length}
        </span>
      </div>

      {/* A2: which candles this list IS. Read off the published interval, never
          the requested one. It says only that the list is per-interval — the
          scored-number question is the TRIGGER group's and is not repeated. */}
      <div style={{ fontSize: 10, color: pal.textMuted, lineHeight: 1.45, margin: '-2px 0 8px' }}>
        {publishedInterval
          ? `Ye list ${publishedInterval}-minute candles ki hai. Upar timeframe`
            + ' badloge toh list bhi badlegi — har interval par apne alag signal bante hain.'
          : 'Backend ne interval nahi bataya, toh ye list kis candle ki hai wo pakka'
            + ' nahi. Timeframe badalne par list badal jaati hai.'}
      </div>

      {sessionRows.length === 0 ? (
        // A1's three sentences, and they are three different claims. Collapsing
        // "dekha, kuch nahi mila" into "dekha hi nahi ja saka" is the failure
        // this panel exists to avoid.
        <div style={{
          fontSize: 10.5, lineHeight: 1.5,
          color: buyGone || sellGone ? pal.caution : pal.textMuted,
        }}>
          {buyGone && sellGone
            ? `Aaj ke signal check hi nahi kar paye${sessionWhy ? ` — ${sessionWhy}` : ''}.`
              + ' Ye "koi signal nahi bana" NAHI hai — ye "dekha hi nahi ja saka" hai.'
            : buyGone
              ? 'SELL side dekhi — is timeframe par ek bhi entry nahi bani. BUY side'
                + ` check nahi ho payi${sessionRunWhy ? ` — ${sessionRunWhy}` : ''}.`
              : sellGone
                ? 'BUY side dekhi — is timeframe par ek bhi entry nahi bani. SELL side'
                  + ` check nahi ho payi${sessionRunSellWhy ? ` — ${sessionRunSellWhy}` : ''}.`
                : 'Aaj is timeframe par ek bhi entry nahi bani — dono taraf dekha gaya,'
                  + ' record khaali hai.'}
        </div>
      ) : (
        <>
          {(buyGone || sellGone) && (
            <div style={{ fontSize: 10, color: pal.caution, lineHeight: 1.45, marginBottom: 7 }}>
              {buyGone ? 'BUY' : 'SELL'} side ki entries nahi aayin
              {(buyGone ? sessionRunWhy : sessionRunSellWhy)
                ? ` — ${buyGone ? sessionRunWhy : sessionRunSellWhy}` : ''}
              , toh neeche wali list adhoori ho sakti hai.
            </div>
          )}
          {sessionRows.map((r) => {
            const sell = r.side === 'SELL'
            return (
              <div key={`${r.side}.${r.i}`} style={{
                padding: '6px 0', borderTop: `1px solid ${pal.border}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                  <span style={{
                    fontSize: 11.5, fontWeight: 700, color: pal.textPrimary,
                    fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
                  }}>{r.t}</span>
                  {/* theme.ts reserves these two hues for DIRECTION, and a side
                      is exactly that — the one place a colour here is honest. */}
                  <span style={{
                    fontSize: 9, fontWeight: 700, letterSpacing: '0.09em',
                    fontFamily: MONO, color: sell ? pal.bear : pal.bull,
                  }}>{r.side} · {r.band}</span>
                  {/* The sell side's standing disclosure, in one word per row.
                      Spelled out ONCE below — the measured number belongs to
                      the TRIGGER group and is not restated a second time. */}
                  {sell && (
                    <span style={{
                      fontSize: 8.5, fontWeight: 700, letterSpacing: '0.08em',
                      marginLeft: 'auto', padding: '1px 4px', borderRadius: 3,
                      fontFamily: MONO, color: pal.caution,
                      border: `1px solid ${pal.caution}`,
                    }}>SCORE NAHI</span>
                  )}
                </div>
                <div style={{
                  fontSize: 10.5, lineHeight: 1.45, marginTop: 2, color: pal.textSecondary,
                  fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
                }}>
                  {r.band} {f2(r.level) ?? '—'} · {r.brkName} {f2(r.brk) ?? '—'}
                </div>
                {/* Muted like the state block's: a stop is not a bearish call.
                    Absent when the payload carried none — never level ∓ 20. */}
                {r.stop != null && (
                  <div style={{
                    fontSize: 10.5, lineHeight: 1.45, color: pal.textMuted,
                    fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
                  }}>stop {f2(r.stop)}</div>
                )}
                {r.lockKnown && (
                  <div style={{ fontSize: 10, lineHeight: 1.45, marginTop: 2, color: pal.textMuted }}>
                    {r.lockWhy
                      ? `re-fire lock ${r.lockT ?? '—'} par khula — `
                        + `${r.lockWhy === 'stop' ? 'stop chhua' : 'VWAP chhua'}`
                      : r.lockOpen ? 're-fire lock ab tak laga hua hai' : ''}
                  </div>
                )}
              </div>
            )
          })}
          <div style={{
            fontSize: 9.5, color: pal.textMuted, lineHeight: 1.5,
            marginTop: 8, paddingTop: 7, borderTop: `1px solid ${pal.border}`,
          }}>
            "re-fire lock" wali line lock ki hai, trade ki NAHI: uske baad agla setup
            arm ho sakta tha, bas itna. Tum kab nikle ye yahan kahin darj nahi hai —
            stop tum khud trail karte ho.
            {anySell && ' SCORE NAHI ka matlab: upper band pe bechna paanch datasets'
              + ' pe naapa aur reject hua tha; ye tumhare kehne par banaya gaya hai.'}
          </div>
        </>
      )}
    </div>
  )

  const contextGroup = (
    <Group name="Saath de raha hai" count={`${onOf(context)} / ${context.length}`}
           note="Bina score wala hissa. Trade ko rang deta hai — rok kabhi nahi sakta."
           rows={context} />
  )

  const mineBlock = (
    <div style={{ marginTop: 14 }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 6,
        paddingBottom: 5, borderBottom: `1px solid ${pal.border}`, marginBottom: 7,
      }}>
        <span style={label}>Mera read</span>
        <span style={{
          fontFamily: MONO, fontSize: 10, fontWeight: 700, color: pal.textMuted,
          fontVariantNumeric: 'tabular-nums',
        }}>{onOf(mine)} / {mine.length}</span>
      </div>
      {mine.length === 0 && !adding && (
        <div style={{ fontSize: 10, color: pal.textMuted, lineHeight: 1.5, marginBottom: 6 }}>
          Yahan apne rules likho. Ye tumhare hain — tool inhe kabhi khud tick nahi
          karega, aur maine yahan koi rule apne se nahi bhara.
        </div>
      )}
      {mine.map((r) => (
        <button key={r.id} onClick={() => toggle(r.id)} aria-pressed={r.state === 'man-on'}
                style={rowBtn}><RowBody r={r} /></button>
      ))}
      {adding ? (
        <input
          autoFocus value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => { setAdding(false); setDraft('') }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && draft.trim()) {
              saveRules([...rules, draft.trim()]); setDraft(''); setAdding(false)
            }
            if (e.key === 'Escape') { setAdding(false); setDraft('') }
          }}
          placeholder="Apna rule likho, Enter dabao"
          style={{
            width: '100%', marginTop: 6, padding: '5px 7px', borderRadius: 4,
            border: `1px solid ${pal.accent}`, backgroundColor: pal.inset,
            color: pal.textPrimary, font: 'inherit', fontSize: 11,
          }}
        />
      ) : (
        <button
          onClick={() => setAdding(true)}
          style={{
            width: '100%', marginTop: 6, padding: '5px 0', borderRadius: 4,
            border: `1px dashed ${pal.border}`, background: 'transparent',
            color: pal.textMuted, font: 'inherit', fontSize: 10, fontWeight: 600,
            letterSpacing: '0.06em', cursor: 'pointer',
          }}
        >+ Rule jodo</button>
      )}
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 }}>
        <div>
          <div style={{ ...label, color: pal.textMuted, letterSpacing: '0.08em' }}>Setup check</div>
          <div style={{
            fontSize: 10.5, color: pal.textMuted, marginTop: 2,
            fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
          }}>{day || '—'}</div>
        </div>
        {/* In compact this sits with the manual rows it clears, inside the
            disclosure — a Reset whose targets are all hidden is a button that
            reads as clearing the trigger. */}
        {!compact && resetBtn}
      </div>

      {/* The state block. This IS the product — PRODUCT.md's five-state machine
          — so it sits above the list rather than being one row inside it. */}
      {st ? (
        <div style={{
          border: `1px solid ${pal.border}`, borderRadius: 5, backgroundColor: pal.inset,
          padding: '9px 10px', marginTop: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 7 }}>
            <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: '0.1em',
                           color: pal.accent }}>{stateWord}</span>
            {/* Which side this is. Never implied by colour alone: a reader who
                misses the badge would read a SELL state as the scored BUY. */}
            <span style={{
              fontSize: 9, fontWeight: 700, letterSpacing: '0.09em',
              padding: '1px 5px', borderRadius: 3, fontFamily: MONO,
              color: pal.textMuted, border: `1px solid ${pal.border}`,
            }}>{showSell ? 'SELL · u3' : 'BUY · d3'}</span>
          </div>
          {bothLive && (
            <div style={{ fontSize: 10, color: pal.caution, marginTop: 3, lineHeight: 1.45 }}>
              Doosri taraf bhi armed hai. Yahan BUY dikhaya ja raha hai kyunki
              score sirf usi ka hai — sell ke markers chart par hain.
            </div>
          )}
          {!st.readable && (
            <div style={{ fontSize: 10, color: pal.caution, marginTop: 3, lineHeight: 1.45 }}>
              Is bar ka read nahi mila — upar wali haalat wahi hai jismein setup abhi
              hai, WAITING nahi. Read na milna iska saboot nahi ki setup khatam ho gaya.
            </div>
          )}
          <div style={{ fontSize: 10.5, color: pal.textSecondary, marginTop: 3, lineHeight: 1.5 }}>
            {st.ref_i != null && st.level != null
              ? `Reference candle ne ${showSell ? 'u3' : 'd3'} ${f1(st.level)} chhua`
                + (st.candles_left != null ? ` · ${st.candles_left} candle baaki` : '')
              : `Abhi koi reference candle nahi — ${showSell ? 'u3' : 'd3'} chhua hi nahi gaya.`}
          </div>
          {/* The two prices that bound the trade, in one block because they
              are one thought: the line that has to break, and the line that
              says you were wrong. Tabular-nums so they align digit for digit.
              Either may be absent on its own — a TRIGGERED bar has cleared its
              reference but still has a stop — so the block renders if EITHER
              exists rather than hanging both off the first. */}
          {((showSell ? st.ref_low : st.ref_high) != null || st.stop != null) && (
            <div style={{
              marginTop: 5, paddingTop: 5, borderTop: `1px solid ${pal.border}`,
              fontSize: 10.5, fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
            }}>
              {(showSell ? st.ref_low : st.ref_high) != null && (
                <div style={{ color: pal.textPrimary }}>
                  Todna hai {showSell ? '<' : '>'} {f1(showSell ? st.ref_low : st.ref_high)}
                </div>
              )}
              {/* Muted, not red: theme.ts reserves red for DIRECTION, and a
                  stop is not a bearish call. Read verbatim off the payload —
                  never `level` minus 20, which is the rule stated twice. */}
              {st.stop != null && (
                <div style={{ color: pal.textMuted, marginTop: 2 }}>
                  Stop {showSell ? '>' : '<'} {f1(st.stop)}
                </div>
              )}
            </div>
          )}
          {/* NOT "nikal gaye", which this read as until 2026-08-12. `exit_why`
              is the bar the RE-FIRE LOCK cleared (run_states' own docstring),
              not a trade exit: the operator trails their own stop and the tool
              has no idea where they left. Worded here as the lock and nothing
              more; what the lock IS is explained once, in the session list. */}
          {st.exit_why && (
            <div style={{ fontSize: 10.5, color: pal.textSecondary, marginTop: 4 }}>
              Re-fire lock khula — {st.exit_why === 'stop' ? 'stop chhua' : 'VWAP chhua'}
            </div>
          )}
        </div>
      ) : (
        <div style={{ fontSize: 10.5, color: pal.textMuted, marginTop: 10, lineHeight: 1.5 }}>
          Setup ki haalat nahi aa rahi{runStateWhy ? ` — ${runStateWhy}` : ''}. Koi
          haalat dikhayi nahi ja rahi, kyunki galat bar ki haalat dikhane se behtar
          hai kuch na dikhana.
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', margin: '0 -12px', padding: '0 12px' }}>
        {trigger.length > 0 && (
          <Group name="Trigger" count={`${onOf(trigger)} / ${trigger.length}`}
                 note={showSell
                   // The sell note already says the number does not apply to
                   // this side at all, so the interval line is not appended
                   // here: it would be a third statement of one fact.
                   ? 'u3 ka ulta aaina. ISKA KOI SCORE NAHI — upper band pe bechna'
                     + ' paanch datasets pe naapa aur reject hua tha; ye tumhare'
                     + ' kehne par banaya gaya hai. 68.4% ise haasil nahi hai.'
                   // ONE extra line, and only off the scored interval. §5c was
                   // measured on 3-minute candles; on any other candle this is
                   // a different setup carrying no measured number.
                   : offScore
                     ? `Ye chart ${publishedInterval ? `${publishedInterval}-minute` : 'anjaan'}`
                       + ` candles ka hai, ${SCORED_INTERVAL}-minute wala nahi — 68.4% (n=19)`
                       + ' sirf 3m par naapa gaya tha, is timeframe par laagu nahi hoti.'
                     : '§5c — sirf isi hisse ka score nikla hai: 68.4% hit at +30m, n=19.'}
                 rows={trigger} />
        )}
        {/* Above the unscored half and outside compact's fold, because it is
            the §5c record and belongs with §5c's trigger. */}
        {sessionBlock}
        {compact ? (
          /* The unscored half, closed by default. The summary carries its own
             tally, so "collapsed" can never be misread as "nothing found" —
             A1's distinction, kept at the one place the rows are hidden. */
          <details style={{ marginTop: 14 }}>
            {/* NOT `display:flex` on the summary itself — that suppresses the
                native disclosure triangle in Chrome, and a fold with no
                affordance is a fold nobody opens. The row is a child instead,
                so the marker keeps its own box. */}
            <summary style={{
              // fontSize sizes the native marker too. Left at the inherited
              // 16px the triangle plus a calc(100% - 16px) row overflowed the
              // rail and wrapped onto a second line box, which is where 20px
              // of dead space above the label came from.
              cursor: 'pointer', paddingBottom: 5, lineHeight: 1.2, fontSize: 11,
              borderBottom: `1px solid ${pal.border}`,
            }}>
              <span style={{
                display: 'inline-flex', width: 'calc(100% - 20px)',
                alignItems: 'baseline', justifyContent: 'space-between', gap: 6,
                verticalAlign: 'middle',
              }}>
                <span style={label}>Rang, rok nahi</span>
                <span style={{
                  fontFamily: MONO, fontSize: 10, fontWeight: 700, color: pal.textMuted,
                  fontVariantNumeric: 'tabular-nums',
                }}>{onOf(agree)} / {agree.length}</span>
              </span>
            </summary>
            {contextGroup}
            {mineBlock}
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
              {resetBtn}
            </div>
            <div style={{ fontSize: 9.5, color: pal.textMuted, marginTop: 8, lineHeight: 1.5 }}>
              Jaan-bujh kar alag rakhe hain. Trigger ya to bana hai ya nahi; baaki sirf rang
              hai. Dono jod dene se ek bina-score wali line ek scored line ke barabar ho jaati.
            </div>
          </details>
        ) : (
          <>
            {contextGroup}
            {mineBlock}
          </>
        )}
      </div>

      {/* TWO tallies, never one. See the header comment for the measurements
          that make adding them a mistake rather than a simplification.
          In compact the trigger tally is the TRIGGER GROUP's own count and the
          agree tally is the disclosure's — same two numbers, never summed. */}
      {!compact && (
      <div style={{ borderTop: `1px solid ${pal.border}`, marginTop: 12, paddingTop: 10 }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <div style={{ ...label, fontSize: 9, color: pal.textMuted }}>Trigger</div>
            <div style={{
              fontSize: 15, fontWeight: 700, marginTop: 1, color: pal.textPrimary,
              fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
            }}>{trigger.length ? `${onOf(trigger)} / ${trigger.length}` : '—'}</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ ...label, fontSize: 9, color: pal.textMuted }}>Saath</div>
            <div style={{
              fontSize: 15, fontWeight: 700, marginTop: 1, color: pal.accent,
              fontFamily: MONO, fontVariantNumeric: 'tabular-nums',
            }}>{onOf(agree)} / {agree.length}</div>
          </div>
        </div>
        <div style={{ fontSize: 9.5, color: pal.textMuted, marginTop: 7, lineHeight: 1.5 }}>
          Jaan-bujh kar alag rakhe hain. Trigger ya to bana hai ya nahi; baaki sirf rang
          hai. Dono jod dene se ek bina-score wali line ek scored line ke barabar ho jaati.
        </div>
      </div>
      )}
    </div>
  )
}
