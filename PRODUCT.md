# TapeMap — product truth

Written 2026-08-05 for v3's design work. Sources are the repo's own record, not
inference: `context/HANDOFF.md`, `context/research-findings.md`, the operator's
v3 state-machine spec, and the `operator-trading-style` memory. Where something
was genuinely unanswered it is marked **OPEN** rather than guessed.

## What this is

A single-operator intraday trading instrument for Indian index futures and
options (NIFTY, BANKNIFTY, SENSEX). It is not a broker terminal and it places no
orders. It watches one setup and tells the operator where that setup stands.

## The unique mechanism, in one sentence

It runs the operator's own scored entry rule live, on their own tape, and holds
a position in a five-state machine — so the screen answers "am I in a trade, and
what is the next thing that has to happen" instead of showing a wall of
indicators.

## The one user

One person. Not a team, not a customer base. They are:

- An ICT/SMC discretionary trader who reads structure off the chart themselves.
- Running LuxAlgo SMC + fadi ICT on NIFTY 1-min; charts read in Kite, light
  theme, VWAP σ bands + OI pane.
- Trading **premium-matched option legs** — ATM when its premium is > ₹100,
  otherwise strikes > ₹100 on both sides, the two legs within ±₹25 of each
  other — going deep ITM when the near strike gets cheap.
- Technical enough to read a payload and argue with a number.

They do not need to be taught what VWAP is. They need to not miss the fire, and
to not be lied to.

## The scene

A weekday, 09:15 to 15:30 IST, at a desk, on a real monitor, alongside Kite and
TradingView. The tool is one window among several and is glanced at, not stared
at. **The setup fires 1–2 times a week** — so the honest majority state of this
screen is "nothing is happening", and that state has to be designed, not
tolerated.

## The state machine — the product

| state | what is true | what the screen owes |
|---|---|---|
| WAITING | d3 not touched | ±1σ interior context. **Context, not signal.** |
| ARMED | a candle's low touched d3; that candle is the reference | the reference candle live, a 10-candle countdown, and `ref_high` — the line that has to break |
| TRIGGERED | a candle closed above `ref_high` | entry at that close; stop at d3 − 20 |
| IN TRADE | position open | VWAP is the first milestone, then band-to-band trail |
| OUT | **the re-fire lock cleared** — price hit the stop or reached VWAP | that the next setup may arm again, and which of the two freed it |

**CORRECTED 2026-08-13 — the OUT row above used to read "stop / VWAP-trail exit
/ 15:15 flat · what happened, and why".** That is a claim the tool cannot make.
`run_states` emits `exit_why` and its own docstring defines it as *the bar the
re-fire lock cleared* (§5c point 7): after an entry the next setup may arm
immediately if stopped out, otherwise not until VWAP is touched. **The operator
manages the trade themselves and TRAILS. The tool records the entry and the stop
and nothing after.** Rendering that field as "exited at VWAP" states an exit
nobody observed — it was corrected in SETUP CHECK on 2026-08-12 and **fully
landed 2026-08-13 in `654d17c`**. All three screens now word it correctly.
Two of them share one definition: `machine.ts` exports `lockNote`, used by
`App.tsx` and `GlassBoard.tsx`. `SetupCheck.tsx` renders from its own
`lockWhy` prop instead — correct, but not covered by that shared guarantee.

Full rule and its score: `research-findings.md §5c`. Measured on 65 NIFTY
sessions: 19 trades, 68.4% hit at +30m against a 49.5% control, stopped out half
as often as the old rule. **+6m is negative** — the trade goes against you first
and then works, which is why the stop is not moved early. **That number belongs
to 3-minute bars and to no other interval** (`band_rotation.SCORED_INTERVAL`);
the live tape only started publishing them on 2026-08-12.

**The LIVE record is 20 rows and none of it is scored** (counted 2026-08-14):
9 entries and 11 arms across 2026-08-10 and 2026-08-13, every one carrying
`unscored` because `data/backtest/` ends 2026-07-31. NIFTY's first-ever §5c
entry landed 2026-08-13 12:09. **Do not present any live hit rate** — the
scorer itself refuses one below n=15 (research-findings §5e), and the forward
test is nowhere near it. `eod_capture.py` now preserves each session so the
count can start moving.

## Non-negotiable product rules

These are load-bearing and predate this design work.

1. **Three different sentences.** "We checked and found nothing", "we could not
   check", and "we are not showing you" must never collapse into one rendering.
   Every panel follows this.
2. **Never invent a level, a greek, or a pivot.** An absence gets a reason.
3. **Frame discipline.** Anything DRAWN on the chart is futures-frame; any
   DISTANCE to a strike is index-frame; `basis` is published, and a level whose
   frame is unknown is **not drawn at all**.
4. **No advice deflection.** Asked a trading question, answer it straight.
5. The backend is fixed. v3 is a new frontend on the same payload; if v3 changes
   the backend it is not v3.

## What the backend already publishes and the screen has never shown

`basis_why`, `t_floored`, `w_bars_ce` / `w_bars_pe`, `gex_spot_band`. All true,
all unread. HANDOFF §6b: "The backend tells the truth; the screen is still
silent. v3's job."

## Hard constraints

- **Charting engine is settled: `candl`.** 61 drawing tools with a full
  lifecycle API (`setActiveTool` / `setDrawings` / `onDrawingsChange` /
  `setMagnet`), of which ui-v2 wires **zero**. The operator has never been able
  to draw on their own chart. `ui-v2/src/vendor/candl/` is PRISTINE — never
  edited.
- **The layout trap.** The chart column must keep a definite pixel height; a
  percentage against an auto-height flex parent collapses the chart to zero.
  Anything added under the chart goes in the section BELOW the column. This has
  cost two bad edits and collapsed the chart twice. Toolbar goes ABOVE.
- React + Vite + TypeScript. Gates: `tsc --noEmit`, `vite build`, `pytest`.
- Desktop only in practice. No mobile usage scene exists for this tool.

## What v2 got wrong — evidence, not authority

Dual review scored it 5/10. A UI audit scored 7/20 and left seven open: zero
`@media` queries, no focus indicators, no `prefers-reduced-motion`,
`transition: width`, four competing side-tab accent borders, Inter/Roboto (a
terminal needs tabular figures), ~30 hard-coded colours outside `theme.ts`.
Seven fossil tabs the operator never opens. The verdict that matters:
**"weeks of backend-only work landed with nothing on their screen, and the chart
they finally saw was unreadable."**

## OPEN — not to be guessed by the designer

Recorded in HANDOFF §8, still owed by the operator: compression as context vs
co-condition, the expiry-day rule, a seller's stop and decay target, Setup B's
expression, and whether the ±1σ interior is no-trade with the edges as the
working zones. Three more are in `DEFERRED.md §0`.

**CORRECTED 2026-08-13.** This list also carried the **09:25 trigger gate** and
**re-fire suppression on the same level** as open. Both were settled on
2026-08-05 in `research-findings.md §5c` (the rule text, and point 7) and both
are implemented — `band_rotation.ANCHOR_MINUTE` gates the arm in `run_states`,
and the re-fire lock is `run_states`' own `lock`, cleared by stop or VWAP. A
designer reading them as unanswered was reading a list eight days stale.

## Brand commitments

None recorded. There is no logo, no brand palette, no marketing surface. The
tool has never been shown to anyone but its operator.
