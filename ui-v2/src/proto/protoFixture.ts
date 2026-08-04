// Fixture loading for the /proto spike. THROWAWAY.
//
// The market is shut for most of the hours this prototype gets worked on, and
// the three proofs have to run against real bars — mock data would prove
// nothing about a σ ribbon or a rotation anchor. So the proto can also read a
// cached /api/data response. These are real captured payloads, not fixtures
// authored for the test:
//
//   data/backtest/WEEKLY_LEGS/NIFTY_2026-08-04_index_close.json  376 bars, 21 rotations
//   data/backtest/WEEKLY_LEGS/NIFTY_2026-08-04_index_1525.json   opposite basis sign
//   data/backtest/WEEKLY_LEGS/NIFTY_2026-08-04_partial.json      no basis key at all
//
// Loaded through an <input type="file">, not an import: ui-v2 carries its own
// pnpm-lock.yaml, so Vite's workspace root stops at ui-v2/ and importing
// ../../../data/... falls outside server.fs.allow. The file input also works
// under `vite preview` and swaps between the three without a rebuild.

import type { TapeBar, RotationSignal } from '../data'

/** The FUT leg's numeric block, exactly the fields TapeBar flattens. Declared
 *  locally rather than reusing BarLeg because BarLeg types `oi` as nullable
 *  while TapeBar does not — an incompatibility the live path never notices
 *  because it reshapes from an untyped payload. */
interface RawFut {
  o: number; h: number; l: number; c: number; v: number; oi: number
  vwap: number
  u1: number; d1: number; u2: number; d2: number; u3: number; d3: number
}

interface RawBar {
  t: string
  fut?: RawFut | null
  ctx?: TapeBar['ctx']
  gamma?: TapeBar['gamma']
  setup?: TapeBar['setup']
  ce?: TapeBar['ce']
  pe?: TapeBar['pe']
}

interface RawPayload {
  days?: { day?: string; bars?: RawBar[]; rotation?: unknown }[]
}

export interface FixtureView {
  day: string
  bars: TapeBar[]
  rotation: (RotationSignal | null)[] | null
  /** Why the rotation layer is withheld, when it is. '' = nothing withheld. */
  rotationWhy: string
}

/** Mirrors useLiveData's tapeBars (data.ts:1289-1390) — the same FUT mapping
 *  and, far more importantly, the same WITHHOLDING rules. A bar with no FUT
 *  leg is skipped, and any skip or length disagreement withholds the entire
 *  rotation array with a reason, because signals drawn one bar off would claim
 *  the operator's own setup fired on a minute it did not.
 *
 *  tapeBars is a useCallback closed over the live `raw` map and is not
 *  exported standalone, so this is a deliberate duplication — confined to the
 *  throwaway, and it dies with it. */
export function reshapeFixture(payload: unknown): FixtureView {
  const p = payload as RawPayload | null | undefined
  const day = p?.days?.[p.days.length - 1]
  if (!day) {
    return { day: '', bars: [], rotation: null, rotationWhy: 'no days[] in this payload' }
  }

  const bars: TapeBar[] = []
  let skipped = 0
  for (const b of day.bars ?? []) {
    const f = b.fut
    if (!f) { skipped++; continue }
    bars.push({
      t: b.t, o: f.o, h: f.h, l: f.l, c: f.c, v: f.v, oi: f.oi,
      vwap: f.vwap, u1: f.u1, d1: f.d1, u2: f.u2, d2: f.d2, u3: f.u3, d3: f.d3,
      // Whole-block pass-through, same rule as the live path: never rebuilt
      // field-by-field, so a field the engine adds later still rides along and
      // a bar predating the block gets null rather than inheriting.
      ctx: b.ctx ?? null, gamma: b.gamma ?? null, setup: b.setup ?? null,
      ce: b.ce ?? null, pe: b.pe ?? null,
    })
  }

  let rotation: (RotationSignal | null)[] | null = null
  let rotationWhy = ''
  const raw = day.rotation
  if (!Array.isArray(raw)) {
    rotationWhy = 'this payload carries no index band-rotation layer'
  } else if (skipped > 0) {
    rotationWhy = `${skipped} bar${skipped === 1 ? '' : 's'} lacked a FUT leg, `
      + 'so the signals’ bar indices no longer line up with the chart'
  } else if (raw.length !== bars.length) {
    rotationWhy = `the payload carries ${raw.length} signal slot${raw.length === 1 ? '' : 's'} `
      + `for ${bars.length} bars, so they cannot be lined up 1:1`
  } else {
    rotation = raw as (RotationSignal | null)[]
  }

  return { day: day.day ?? '', bars, rotation, rotationWhy }
}

/** Read a user-picked .json file. A parse failure comes back as a sentence in
 *  `rotationWhy`, never as a thrown SyntaxError — the page discloses, it does
 *  not die. */
export async function readFixture(file: File): Promise<FixtureView> {
  let parsed: unknown
  try {
    parsed = JSON.parse(await file.text())
  } catch (e) {
    return {
      day: '', bars: [], rotation: null,
      rotationWhy: `${file.name} is not valid JSON: ${(e as Error).message}`,
    }
  }
  return reshapeFixture(parsed)
}
