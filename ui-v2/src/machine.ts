import type { RunState } from './data'

/* ── The five-state machine, read once ───────────────────────────────────────
   Lifted VERBATIM out of App.tsx (2026-08-11) when the Glass board needed the
   same read the machine strip already does. Nothing here is new logic.

   It lives in its own module rather than being exported from App.tsx for one
   reason: App.tsx imports the board, and the board needs this — so exporting
   it from App would make the two files import each other. A shared helper that
   depends on nothing but a type has no business being the thing that creates a
   cycle.

   It READS `run_state`; it does not run a second copy of the machine. Side
   pick is SetupCheck's rule verbatim: the side with something happening wins,
   BUY (the scored side) wins ties, and a shown SELL is named so it can never
   borrow the buy rule's measured hit rate.                                   */

/** Last bar's machine state and which side is being shown. One definition,
 *  used by the strip, the title mirror and the Glass board's MACHINE widget,
 *  so all three can never disagree. */
export function liveMachine(runState: RunState[] | null, runStateSell: RunState[] | null) {
  const buy = runState?.length ? runState[runState.length - 1] : null
  const sell = runStateSell?.length ? runStateSell[runStateSell.length - 1] : null
  const buyLive = !!buy && (buy.state !== 'WAITING' || buy.exit_why != null)
  const sellLive = !!sell && (sell.state !== 'WAITING' || sell.exit_why != null)
  const showSell = sellLive && !buyLive
  return { st: showSell ? sell : buy, showSell, bothLive: buyLive && sellLive }
}

export const MACHINE_WORDS = ['WAITING', 'ARMED', 'TRIGGERED', 'TRADE MEIN', 'BAAHAR'] as const

/** What `exit_why` MEANS, written once because three screens render it.
 *
 *  It is the RE-FIRE LOCK clearing -- §5c point 7: after an entry the next
 *  setup may not arm until VWAP is touched, or immediately if stopped out.
 *  It is NOT the operator's exit. They manage the trade and TRAIL their own
 *  stop ("my stop is never vwap i like to trail", 2026-08-13), and nothing in
 *  this app knows when they actually got out.
 *
 *  Every caller said "nikal gaye" / "par nikle" / "the run is closed" until
 *  2026-08-13, which claimed an exit the tool cannot see. One sentence here
 *  so a fourth screen cannot invent a fifth wording. */
export function lockNote(st: RunState): string {
  return st.exit_why === 'stop' ? 'stop chhua' : 'VWAP chhua'
}

export type MachineWord = (typeof MACHINE_WORDS)[number]

/** SetupCheck's own state word for a bar — exit_why wins, IN_TRADE reads as
 *  the operator says it. */
export function machineWord(st: RunState): MachineWord {
  return st.exit_why ? 'BAAHAR' : st.state === 'IN_TRADE' ? 'TRADE MEIN' : st.state
}
