import { useEffect, useState } from 'react'
import type { IndexKey } from '../data'

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
  /** The side the extension paints the mark in (+1 buyers, -1 sellers, 0 neutral). The record does not carry it;
   *  `withSide` joins it from `/api/tape`'s ofd marks. Absent = not joined, drawn neutral, never guessed. */
  side?: number | null
  /** P only: whether it sits at the swing extreme of the chart's closed bars before it (TradeTab `marks`); null = no. */
  swing?: 'top' | 'bottom' | null
}

const IST_MS = 5.5 * 3600_000
const hhmmIST = (ms: number) => {
  const d = new Date(ms + IST_MS)
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
}

/** The record's events with the extension's own `side`, joined on (HH:MM, kind, price) from `/api/tape`'s ofd marks
 *  (33 of 33 matched on 2026-09-29). These are board.js's RAW sides (the tape posts `m.local.events`, main.js:220 → :269):
 *  a trap's side is the TRAPPED side. Only the P colour flips it, in chips.paintSide (main.js:169). A presentation
 *  join: nothing is inferred, and an unmatched event keeps no side. */
export function withSide(events: FootEvent[] | null,
                         ofd: { t: number; kind: string; p: number | null; side: number | null }[] | null | undefined): FootEvent[] | null {
  if (!events) return null
  if (!ofd || !ofd.length) return events
  const side = new Map<string, number | null>()
  for (const m of ofd) side.set(`${hhmmIST(m.t)}|${m.kind}|${m.p}`, m.side)
  return events.map((e) => {
    const k = `${e.t}|${e.kind}|${e.p}`
    return side.has(k) ? { ...e, side: side.get(k) } : e
  })
}

export interface Footprint {
  /** null when the record could not be read at all. Empty when this INDEX has
   *  no events in it — two different sentences. */
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
