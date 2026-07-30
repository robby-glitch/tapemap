// Tape Chart Phase 2 — narration joined from the existing event stream.
// Presentation only (spec §6 Phase 2): this module groups, tiers and formats
// events the engine already produced. It never computes a rank, an average,
// or a threshold — "UI renders, engine decides" holds here exactly as
// everywhere else in ui-v2.
import type { EventItem, TapeBar } from '../data'

export type Tier = 0 | 1 | 2 | 3

export interface Narration {
  kind: string
  head: string
  ev: string
  tone: 'bull' | 'bear' | 'neutral' | 'structure'
  tier: Tier
}

// Tier by the event's own kind, most consequential first. This only orders
// kinds the engine already assigned — nothing here is computed from bars.
const TIER3 = new Set(['TRAP-SPRUNG', 'SPRING', 'SQUEEZE-RELEASE', 'ABSORPTION', 'IGNITION'])
const TIER2 = new Set(['DIVERGENCE', 'BREAK', 'BAND-REVERSAL', 'WALL-MIGRATION', 'ROLE-FLIP'])
// STATE, CHOP, everything else → tier 1.

function tierOf(kind: string): Tier {
  if (TIER3.has(kind)) return 3
  if (TIER2.has(kind)) return 2
  return 1
}

// Kinds that describe price structure (a wall, a role at a wall, a level
// broken or reversed) rather than a directional call. theme.ts's own rule is
// that colour carries exactly one meaning — brass is STRUCTURE, green/red is
// DIRECTION — so these always render brass regardless of the event's own
// `dir`, matching how WALL-MIGRATION / ROLE-FLIP already read in the Events
// tab (data.ts's evDir still gives them a side, but that side is "which way
// the structure moved", not a market call).
const STRUCTURE_KINDS = new Set(['WALL-MIGRATION', 'ROLE-FLIP', 'BREAK', 'BAND-REVERSAL'])

function toneOf(e: EventItem): Narration['tone'] {
  return STRUCTURE_KINDS.has(e.tag) ? 'structure' : e.dir
}

/** TRAP-SPRUNG → Trap-Sprung. Formatting only — the tag's own words, cased
 *  for display, nothing added or reworded. */
function titleCase(s: string): string {
  return s
    .toLowerCase()
    .split(/([\s-]+)/)
    .map((part) => (/^[\s-]+$/.test(part) ? part : part.charAt(0).toUpperCase() + part.slice(1)))
    .join('')
}

/** Split off the first sentence verbatim; the remainder is returned
 *  untouched (no paraphrase, no summarizing) for use as evidence. */
function firstSentence(msg: string): { head: string; rest: string } {
  const m = /^(.+?[.!?])(\s+|$)/.exec(msg)
  if (!m) return { head: msg, rest: '' }
  return { head: m[1], rest: msg.slice(m[0].length) }
}

/** Format the bar's own volume, matching the convention already used in
 *  TradeTab's stat strip (`b.v.toLocaleString('en-IN')`). */
function fmtVol(v: number): string {
  return `Vol ${v.toLocaleString('en-IN')}`
}

/** Format the bar's own OI and its change vs the previous bar. Base uses the
 *  app's existing millions convention (TradeTab: `(b.oi/1e6).toFixed(2)}M`);
 *  the change is small relative to the base so it reads in thousands
 *  ("+80k" style), matching the mockup's OI row. Both numbers are read
 *  straight off the payload — this is a difference of two given values, not
 *  a derived market claim. */
function fmtOi(oi: number, prevOi: number | null): string {
  const base = `${(oi / 1e6).toFixed(2)}M`
  if (prevOi == null) return `OI ${base}`
  const d = oi - prevOi
  if (d === 0) return `OI ${base} (flat)`
  const sign = d > 0 ? '+' : '−'
  return `OI ${base} (${sign}${Math.round(Math.abs(d) / 1000)}k)`
}

/**
 * Join the payload's own event stream to bars on their "HH:MM" key (`t` on
 * TapeBar, `time` on EventItem) and tier each hit by kind. One entry per bar,
 * aligned 1:1 — `null` when that minute carried no event, so the UI can say
 * "no event on this bar" rather than invent one.
 *
 * The only arithmetic in this function formats the bar's own `v`/`oi` (and
 * their change vs the previous bar) and counts how many events shared a
 * minute — no rank, average, or threshold about the market is computed.
 */
export function buildNarration(bars: TapeBar[], events: EventItem[]): (Narration | null)[] {
  const byTime = new Map<string, EventItem[]>()
  for (const e of events) {
    const list = byTime.get(e.time)
    if (list) list.push(e)
    else byTime.set(e.time, [e])
  }

  return bars.map((bar, i) => {
    const hits = byTime.get(bar.t)
    if (!hits || !hits.length) return null

    // Several events can share a minute — keep the highest-tier one; ties
    // keep whichever came first in the payload's own order.
    let best = hits[0]
    let bestTier = tierOf(best.tag)
    for (const e of hits.slice(1)) {
      const t = tierOf(e.tag)
      if (t > bestTier) {
        best = e
        bestTier = t
      }
    }

    const { head, rest } = firstSentence(best.text)
    const prevBar = i > 0 ? bars[i - 1] : null
    const evidence = [rest.trim(), fmtVol(bar.v), fmtOi(bar.oi, prevBar ? prevBar.oi : null)]
      .filter((s) => s.length > 0)
      .join(' · ')
    const more = hits.length > 1 ? ` +${hits.length - 1} more` : ''

    return {
      kind: titleCase(best.tag),
      head,
      ev: evidence + more,
      tone: toneOf(best),
      tier: bestTier,
    }
  })
}
