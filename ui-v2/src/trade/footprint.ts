import { useEffect, useState } from 'react'
import type { IndexKey, RunState } from '../data'

/**
 * The day's FOOTPRINT record, for the one question SETUP CHECK cannot answer
 * from the chain and the candle: **is anything absorbing under the live
 * reference candle?**
 *
 * `/api/day/record` (record_read.py, streamed off `data/frame/frame_<day>.jsonl`)
 * is the only payload on this stack that carries tape events with a price and,
 * sometimes, a named level. Nothing under `src/trade/` has ever read it.
 *
 * ── Why the fetch lives here and not in the panel ──────────────────────────
 * Modelled on `./flow`, which exists for exactly this reason: one fetch, one
 * cadence, and any number of mounts. Two copies of this poll would drift and
 * the same record would be reported two ways.
 *
 * ── What this must never do ───────────────────────────────────────────────
 * The record is written on 5-MINUTE frames; this tab draws 3-minute bars. An
 * event's OWN t and p cross that boundary intact — they are a clock reading and
 * a price, not a bar index — so the chart overlay does draw them, each at its
 * own time and its own price and never snapped to a candle (LevelsOverlay's
 * `drawMarks`). What must NEVER reach the chart is anything DERIVED: the
 * extension's sigma is GoCharting's and runs 1.02–1.08 wider than this stack's,
 * so its bands, zones and distances stay text on this tab and nothing else.
 * `side` is not in this payload at all, which is why the marks are neutral.
 *
 * No direction verdict, no hit rate, no strength percentage. The row states
 * what the record holds and the operator decides what it is worth.
 */

/** One tape event as `/api/day/record` publishes it. */
export interface FootEvent {
  /** "HH:MM", the event's own stamp — replayed events predate the first frame. */
  t: string
  kind: string
  p: number | null
  /** The named level it landed on, in the backend's own words ("at S 56525"),
   *  or null. 22 of 40 carried one on 2026-09-18. */
  at: string | null
  /** Set by record_read.py from `signals.CONFIRMS`. ABSENT on a backend that
   *  predates that line — which is "could not check", never "found nothing". */
  confirm?: boolean
}

export interface Footprint {
  /** null when the record could not be read at all. Empty when this INDEX has
   *  no events in it — two different sentences, kept apart by `lookUnder`. */
  events: FootEvent[] | null
  /** The reason, as a whole sentence when `events` is null (the row prints it
   *  verbatim), and the backend's own `events_why` otherwise. */
  why: string
}

/**
 * The day's record for one index, on a tab-local 30s cadence.
 *
 * WHY 30s AND NOT 15s. record_read caches by (mtime, size, idx), and the
 * extension appends a frame every ~11s during the session — so in market hours
 * very nearly every poll is a COLD read of the whole day file. Measured
 * 2026-09-18 against the live server: 1.83s for the cold pass over 56 MB, 12-75
 * ms warm. That is one blocked second-and-a-half on a single-threaded server
 * that is also serving the 5s tape poll, and the Trade tab is the one the
 * operator sits on all day. 30s is the cadence FlowTab already settled on for
 * this same endpoint; the row is slow context, not a bell.
 *
 * The poll dies with the tab: App mounts TradeTab only while Trade is active.
 */
export function useFootprint(index: IndexKey): Footprint {
  const [events, setEvents] = useState<FootEvent[] | null>(null)
  // "Being read" is its own sentence: before the first response lands, saying
  // the record COULD NOT be read would be the wrong one of the three.
  const [why, setWhy] = useState<string>('footprint record abhi padha ja raha hai')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/day/record?idx=${index}`)
        const j = await r.json()
        if (!alive) return
        if (!j.ok) {
          setWhy(`footprint record padha nahi ja saka — ${j.error || 'server ne wajah nahi batayi'}`)
          setEvents(null); return
        }
        setEvents(j.events || [])
        setWhy(j.events_why || '')
      } catch (e) {
        // The backend not answering is "could not check", not "no flow today".
        if (alive) {
          setWhy(`footprint record padha nahi ja saka — backend ne jawab nahi diya (${String(e)})`)
          setEvents(null)
        }
      }
    }
    // The first read ALWAYS happens. The hidden-tab guard goes on the REPEAT
    // only: on the first load it hangs the row at "could not read" whenever the
    // page is painted while backgrounded, which FlowTab measured for real (a
    // preview pane reports document.hidden true the whole time).
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 30000)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])
  return { events, why }
}

/** The three sentences, as the three marks SETUP CHECK already draws. */
export interface Look {
  state: 'auto-on' | 'auto-off' | 'auto-unknown'
  /** Printed verbatim in the panel's receipt slot. */
  receipt: string
  warn: boolean
}

const f1 = (n: number) => n.toFixed(1)

/**
 * Did the footprint see anything confirming under the live reference candle?
 *
 * THE FILTER INTRODUCES NO NEW CONSTANT. Its bounds are two numbers
 * `band_rotation.run_states` already publishes: events stamped at or after the
 * reference bar's own time (`st.t`), priced between the arming band (`st.level`)
 * and the reference candle's own line (`ref_high` on the buy side, `ref_low` on
 * the sell mirror). A bar's own extent is not an invented threshold. Times are
 * compared as zero-padded "HH:MM" strings, which orders them exactly and parses
 * nothing.
 *
 * THREE ANSWERS, NEVER TWO (CLAUDE.md rule 6). Found it, looked and found
 * nothing, could not look. An index whose record holds no events reads COULD
 * NOT LOOK with the reason — the extension is on one index at a time, and
 * reporting its silence about BANKNIFTY as "nothing absorbed" is precisely the
 * lie this panel exists to prevent.
 */
export function lookUnder(fp: Footprint, st: RunState | null, sell: boolean): Look {
  if (!fp.events) return { state: 'auto-unknown', receipt: fp.why, warn: true }
  if (!fp.events.length) {
    return {
      state: 'auto-unknown', warn: true,
      receipt: `is index ka footprint record hi nahi hai — ${fp.why || 'extension kisi aur index par hai'}`,
    }
  }
  // A backend that predates record_read's `confirm` tag. Reading every event as
  // non-confirming would print "kuch nahi dikha" over a record nobody asked the
  // question of, so it is the third sentence instead.
  if (!fp.events.some((e) => 'confirm' in e)) {
    return {
      state: 'auto-unknown', warn: true,
      receipt: 'backend ne events par confirm tag nahi lagaya — server purana chal raha hai',
    }
  }
  const brk = sell ? st?.ref_low : st?.ref_high
  if (!st || st.t == null || st.level == null || brk == null) {
    return {
      state: 'auto-unknown', warn: true,
      receipt: 'koi live reference candle nahi — jiske neeche dekhna hai wahi nahi bana',
    }
  }
  const lo = Math.min(st.level, brk)
  const hi = Math.max(st.level, brk)
  const t0 = st.t
  const hits = fp.events.filter(
    (e) => e.confirm && e.t >= t0 && e.p != null && e.p >= lo && e.p <= hi,
  )
  if (!hits.length) {
    return {
      state: 'auto-off', warn: false,
      receipt: `reference ke ${sell ? 'oopar' : 'neeche'} footprint pe kuch nahi dikha`
        + ` — ${f1(lo)}–${f1(hi)}, ${t0} ke baad`,
    }
  }
  // The latest one, in the record's own words. `at` travels verbatim because a
  // named level is the strongest thing this payload can say, and `footprint` is
  // stamped on so this can never be read as the engine's own ABSORPTION — two
  // populations, one word (CLAUDE.md rule 5).
  const e = hits[hits.length - 1]
  const more = hits.length - 1
  return {
    state: 'auto-on', warn: false,
    receipt: `${e.t} ${e.kind}${e.at ? ` · ${e.at}` : ''} · footprint`
      + (more ? ` · +${more} aur` : ''),
  }
}
