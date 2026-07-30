// Pure grouping over already-decided bars — no analytic is computed here
// (invariant #6, same as indicators.ts): a zone is just a maximal run of
// consecutive bars sharing one `ctx.verdict`, reported with the engine's own
// words. No rank, no average, no threshold is calculated in this file.
import type { TapeBar } from '../data'

export type ZoneCls = 'stand' | 'watch' | 'go' | 'none'

export interface Zone {
  i0: number
  i1: number
  verdict: string
  cls: ZoneCls
  label: string
  why: string
}

// The engine's own verdict vocabulary, observed verbatim in engine.py
// ~1028-1042 (context()) and cross-checked against data.ts's own
// VERDICT_SCORE table (~line 202-204):
//   GO           — "one-sided tape / dealer hedging amplifies"
//   READY        — "spring loaded — trigger defined" (armed, waiting on a
//                   trigger — not itself a green light)
//   WAIT         — "energy storing — prepare, don't chase" (COILING), or
//                   "trend stalled — range p.. , compression not continuation"
//   CAUTION      — "no edge defined right now"
//   STAND ASIDE  — "pin/chop — edges only, no chasing"
//   SPENT        — "leg released and given back — don't chase"
// Never rename these for display; `label`/`why` always carry the engine's
// own string. This map only buckets them for the zone fill colour.
const VERDICT_CLS: Record<string, ZoneCls> = {
  GO: 'go',
  READY: 'watch',
  WAIT: 'watch',
  CAUTION: 'watch',
  'STAND ASIDE': 'stand',
  SPENT: 'stand',
}

/**
 * Group consecutive bars into runs of one same `ctx.verdict`. Bars with no
 * ctx (predate the block, or an older backend) form their own `cls: 'none'`
 * runs — rendered as nothing, but the run still exists so a hover over that
 * stretch can say "unavailable" instead of silently skipping it.
 *
 * Pure over its input: callers wanting causal (no-look-ahead) zones must
 * slice `bars` down to the cursor themselves, or discard zones whose
 * `i0 > cursor` — this function does not know about any cursor.
 */
export function buildZones(bars: TapeBar[]): Zone[] {
  const zones: Zone[] = []
  const verdictAt = (i: number) => bars[i]?.ctx?.verdict ?? null
  let i0 = 0
  for (let i = 1; i <= bars.length; i++) {
    // A run ends at the array boundary, or wherever the verdict changes
    // (including a change to/from "no ctx", which is its own null run).
    const runEnds = i === bars.length || verdictAt(i) !== verdictAt(i - 1)
    if (!runEnds) continue
    const last = bars[i - 1]
    const verdict = last?.ctx?.verdict ?? ''
    const cls: ZoneCls = last?.ctx ? VERDICT_CLS[verdict] ?? 'none' : 'none'
    zones.push({
      i0,
      i1: i - 1,
      verdict,
      cls,
      label: last?.ctx ? `${verdict} · ${i - i0}m` : '',
      why: last?.ctx?.vwhy ?? '',
    })
    i0 = i
  }
  return zones
}
