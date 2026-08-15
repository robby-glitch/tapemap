# Deferred — decided to do later, not forgotten

Opened 2026-08-07 at the operator's request: *"isko baad m krte h ek file m ye
sb rkhna jo baad m krna h"*.

**What belongs here.** Work that was found, measured, and consciously postponed.
Not a wishlist — every entry carries the measurement that found it, so the next
session can act without re-deriving anything. An entry with no evidence does not
belong in this file.

**What does NOT belong here.** The rules register is `CHECKLIST.md`; strategy
verdicts are `research-findings.md`; the styling backlog is `ui-audit.md`;
finished work is `progress-tracker.md`. This file links to those rather than
restating them.

---

## Reconciled 2026-08-14 — what has since shipped

Checked against `git log`, the source and `data/trigger_log.jsonl`, not memory.

- **Test count is now 569** (`pytest -q`, 2026-08-15) — the ponytail cleanup
  removed 20 tests along with the code they covered (the dead research
  scorers' `test_continuation.py` / `test_measure.py`, `oi_series`'s two, and
  the four weekend-broken contract tests were rewritten, not removed), after
  589 on 2026-08-14 16:00: one added that
  afternoon pinning the `carry_verdict` empty-book guard in
  `test_option_frame.py`. The earlier reconciliation, still accurate as
  history: **588** — 576, plus nine in
  `test_eod_capture.py` and three in `test_docs_claims.py`. The §1 figure and
  the 2026-08-13 note below are both superseded. **This number is now pinned by
  a test**: `test_stated_test_count_matches_reality` compares every stated
  count against what pytest actually collected, so it cannot go stale quietly.
- **The session tape is now preserved.** `eod_capture.py` + `eod_capture.bat`
  (`2499a12`), scheduled Mon–Fri 15:35 IST. The gap it closes is described in
  §0d below, which is what made it necessary.
- **`exit_why`'s half-landed correction is CLOSED** (`654d17c`): `machine.ts`
  exports `lockNote` and all three screens render the re-fire lock through it.

## 0d · THE TAPE EVAPORATES AT MIDNIGHT — closed forward, five rows lost

**Evidence, 2026-08-13/14.** Signals are logged forward correctly, but the bars
they are scored against arrived only through `backfill.py` → `dhan_fetch`, and
**the Dhan data API lapsed 2026-08-05**. So `data/backtest/` ends 2026-07-31,
every one of the 20 live §5c rows carries `unscored`, and a running session is
scoreable only between the close and the server's midnight roll.

On 2026-08-13 that window passed mid-conversation. **Five SENSEX entries —
09:36, 11:09, 12:09, 12:48, 14:03 — are permanently unmeasurable.** Verified
against every surviving source: the API had rolled (`days: []`), the cache had
nothing, and `data/chain/chain_SENSEX_2026-08-13.jsonl` (2047 rows) holds only
`spot` and per-strike OI — **no futures OHLC and no volume**, so the VWAP-banded
bars the rule runs on cannot be rebuilt from it. Two rows from that session were
scored in time and are recorded in HANDOFF's 2026-08-14 entry.

**Closed forward, not backward.** `eod_capture.py` preserves every session from
2026-08-14 on. It does **not** recover 2026-08-13.

**Still open, and both are cheap:**

1. **Recovering 2026-08-13 (and 2026-08-10).** Kite MCP exposes
   `get_historical_data`, which could supply SENSEX 3-minute futures for those
   days and materialise the missing `fut_<day>.json`. It needs an interactive
   OAuth login that a non-interactive session cannot perform. **Operator action,
   not code.** Note this does NOT cross §5's stop rule: filling outcomes on rows
   logged FORWARD is the route `trigger_log._session_bars`' own docstring names
   as allowed; what is forbidden is searching a new hypothesis out of the cache.
2. **`backfill.py` has no working data source.** It still imports `dhan_fetch`.
   Re-pointing it at Upstox historical (daily OAuth token — see the
   `upstox-data-source` memory) or at Kite would restore bulk backfill. Until
   then it is dead code for any date after 2026-08-05.

## 0f · ~~THE σ BANDS ARE WIDER THAN THE OPERATOR'S~~ · **CAUSE FOUND, NOT FIXED — the operator's decision (2026-08-15)**

**Do not reopen this as a bug.** The cause is proven and the operator chose to
live with it: *"thats not required the difference is small we can manage with
out it."*

**Cause: granularity.** Bands are computed on the 1-minute series and only
SAMPLED into the display bucket (`contract_bars.py:218`, deliberate); Kite
computes SDVWAP on the 3-minute series. Recomputing on 3-minute bars matches
Kite to 0.1–0.3% after 13:45 and reproduces its σ = 0 first bar exactly. The
seeding theory was WRONG, and the variance recurrence is NOT at fault — full
experiment and table in `research-findings.md` §1c.

**Standing consequence, quote it wherever counts appear:** the bands stay wider
than the operator's chart, the error is **false-negative-only**, and therefore
**every TapeMap signal count is a FLOOR, not a total.** A touch that fires on
their screen and not in the tool is expected, not a new bug.

**Two residuals still genuinely unexplained** (small, nobody is waiting on
them): the 3-minute rebuild is 8.6% off at 10:30 though near-exact after 13:45,
and VWAP is 1.83 out even on 3-minute bars — granularity cannot explain that,
suspect volume.

The rest of this entry is kept as the measurement record.

**The measurement** (full detail: `research-findings.md` §1c). Against the
operator's own Kite CSV export of `NIFTY AUG FUT`, 3-min, 2026-08-14:
TapeMap σ / Kite σ ran **1.023 at 10:30 → 1.084 at 13:45 → 1.048 at 14:06**,
with the VWAP itself off by up to **1.70**. Wider σ = every band further from
price = **false negatives only**. Two confirmed misses that day: the **14:00**
u3 tag-and-reject the operator circled on their chart (high 24477.00 cleared
Kite's u3 24476.88 and closed back below; TapeMap's u3 was 24482.10, so the
high fell 5.10 short) and an **11:36** d2 entry missed by 0.25.

**The lead, explicitly NOT the answer yet.** On the 09:15 bar Kite has σ = 0
(all bands = VWAP 24416.67); TapeMap already has σ = 8.75. A seeding
difference is the obvious suspect but does not explain the ratio *rising* to
1.084 and then falling back. **Do not "fix" the seed and declare victory** —
measure the whole curve before and after.

**Everything needed is already on disk**, so this needs no live session:
- `data/backtest/fut_2026-08-14.json` — 379 RAW 1-minute bars, captured 15:35
- the operator's Kite CSV (`VWAP`, `SDVWAP1±`, `SDVWAP2±`, `SDVWAP3±` columns)
- `vwap_bands` in the engine is the code under suspicion

**When it is fixed**, HANDOFF §6's σ-bands row goes back to ✅ *with the new
ratio stated*, and §1b's 2026-08-14 signal counts must be re-derived — they
are currently a floor, not a total.

## 0e · CANDIDATE QUESTION — the target side never printed (observed 2026-08-13)

**Not a finding. One session, two scored rows.** Both showed the OPPOSITE side's
`d1`/`d2`/`d3` **untouched**, best excursions −0.38σ and −0.88σ — price never
crossed VWAP on either. The operator's exit plan trails toward −2σ/−3σ when OI
is heavy that side, so a session where that target never prints is worth
counting.

**Do not act on this yet, and do not go looking for it in `data/backtest/`** —
§5's stop rule forbids exactly that search. The legitimate route is the one
already running: `bands` is recorded on every scored row, so after n rows the
question answers itself from forward data. **If it is to be tested, pre-register
it in `research-findings.md` §5e first**, with the bar stated before the count
is read.

## Reconciled 2026-08-13 — what has since shipped

Checked against `git log` and the source, not against memory.

- **§4, the published stop — actually shipped 2026-08-12, not 2026-08-09.** The
  heading below carried the wrong date for three days. `_stop_px` and the
  per-bar `stop` field first exist in `8760d15` (`git log -S'"stop": _stop_px'`
  returns that commit and no other); on 2026-08-09 the entry was a
  specification, not a shipped field. Date corrected in place below.
- **§0b's "still open" stop item is CLOSED** by the same commit — the 20-point
  stop is published beside `level` on every `run_state` bar and on the entry
  record. The **68.4% vs 63.2%** reconciliation is **still open**, though not
  currently visible: `grep -rn "63.2" ui-v2/src` returns nothing, so no screen
  shows two hit rates for one rule today. The written reconciliation naming
  which exit each assumes is still owed.
- **§0's three operator decisions are all still owed** — nothing in the log
  answers them.
- **Not from this file, but it corrects it:** the tape published 1-minute bars
  until 2026-08-12 while §5c was scored on 3-minute
  (`band_rotation.SCORED_INTERVAL = 3`). Any measurement in this file taken off
  a LIVE payload before that date was taken at the wrong interval. The
  backtest-derived numbers here are unaffected — the scorer always used 3.
- Test count in §1 was 432; it is **576** as of 2026-08-13 (`pytest -q`).

## 0 · THREE DECISIONS OWED BY THE OPERATOR — nothing waits on code

These block real work and must not be guessed. Two of them were guessed once
already today and both guesses were wrong (CHECKLIST C13).

1. **The CALL-heavy threshold** for the short's target extension. No percentage
   given. 40% is the only number in the record and it sits there as a REJECTED
   entry filter (C11) — borrowing it would borrow a number from a question it
   was never asked. Best answered by watching the live CALL-heavy % for a
   session or two rather than picking in the abstract.
2. **Does an ARMED buy close a short, or only a TRIGGERED one?** ARMED exits
   sooner and more often; TRIGGERED is the actual signal.
3. **What "pass" means for the live forward test** (§5e) — per-trade points,
   hit rate, or a ratio against the 20-point stop. §5f's evidence argues for
   **median and hit rate, not mean**: at n≈19 the mean is hostage to one or two
   trades on BOTH sides.

Once 1 and 2 land, the short-exit rules in
`docs/superpowers/specs/2026-08-08-operator-short-exit.md` can be built.

## 0b · Callout v3 — five findings from the 2026-08-09 design review

Found by adversarial review of the callout redesign plan and **verified against
source**. None is a bug today; each is a trap the redesign would have walked
into. Plan: `~/.claude/plans/elegant-frolicking-pebble.md`.

1. **SQUEEZE-RELEASE is filed inconsistently.** It sits in `narration.ts:20`'s
   TIER3 (top billing on the chart) but is absent from `hinglish.ts`'s CLAIM
   table — so `claimOf` returns the `lean` default — and absent from `evDir`
   (`data.ts:517-548`), so its tone is neutral. A pill can therefore shout
   while its direction chip says "direction saaf nahi". Whether it should gain
   a CLAIM entry is a **vocabulary** decision needing its own reasoned commit;
   it is not the card's call. **Operator decision owed.**
2. **`ceW`/`peW` is the live chain ladder** — no per-strike history,
   `aligned=false` while scrubbing. Any per-bar surface must use
   `BarGamma.w_ce`/`w_pe` (`data.ts:137`) instead. The callout plan originally
   named the wrong field, which would have attributed live positioning to a
   past bar.
3. **CONFLICT is unreachable.** `buildNarration` returns `titleCase(best.tag)`
   and never synthesises it; CONFLICT exists only inside `buildFocusFeed`,
   which TradeTab does not consume (it passes the raw stream). Two costed
   options: repoint narration at the focus feed (also changes pills and
   ribbon), or detect it in the UI (violates "UI renders, engine decides").
   Neither taken.
4. **`hinglish.ts` holds 31 glosses, not 25.** HANDOFF's count is stale. The
   eight with no callout state were TRAP, TRAP-SETTING, BREAK, FLIP-TEST,
   OI-PEAK-LAG, CARRY, CHOP, STATE — and the "unknown kind" fallback does not
   catch them, because they *have* glosses. CARRY fires every session at 15:29.
   Also unfiled in CLAIM: BREAK and FLIP-TEST, which default to `lean` though
   BREAK is tier-2 and reads like a call.
5. **Per-kind hit rates must not be rendered.** `signal_review.py` prints them,
   but per-kind n runs 1–5 on one session; "100% · 2/2" reads as a measurement
   at any type size. The `--json` export therefore emits **claim buckets only**
   (n≈16–18) plus the control, and `test_signal_snapshot.py` pins that
   exclusion. Per-kind waits on multi-session live logging — the stop-rule on
   backtest slicing means re-slicing will not supply it.

**Still open from the same plan:** reconcile SetupCheck's **68.4%** against
`trail_score`'s **63.2%** for the same rule, naming which exit each assumes. Two
"measured" hit rates for one rule on one screen is an A1 failure. *(The other
item here — publish the 20-point stop beside `level` in `run_state` — SHIPPED
2026-08-12, `8760d15`; see the reconciliation section at the top.)*

## 1 · Premium / discount is measured on the wrong range · BACKEND

**Status:** operator has seen the numbers and deferred the fix. The three
options below were put to them; none chosen yet.

`structure.py:482` takes the working range from `prev_sh` / `prev_sl` — the
previous confirmed swing high/low pair. Those are 1-minute fractal pivots, so
two consecutive swings sit 8–16 points apart on NIFTY.

Measured live, 2026-08-07 (NIFTY, 385 bars):

| | |
|---|---|
| session range | 24601 → 24707 (106 pts), equilibrium **24654** |
| published PREMIUM | 24655 → 24663 |
| published DISCOUNT | 24647 → 24655 |
| so the range used | **16 points** |
| PD pairs per session | **56** |

So it publishes the premium/discount of the last 1-minute micro-swing, not of
the leg being traded. ICT's premium/discount is a **dealing range** read.

**This is not a crash and must not be smuggled in as a "bug fix".**
`structure.py`'s own comment records the box counts (44/43/57 per day) as
measured, so the current behaviour is deliberate. Changing it is a change of
DEFINITION, which is the operator's call, and a backend change, which CHECKLIST
F2 says must be separate and explicitly agreed.

Options as put to the operator:
1. **Swing pair with a minimum size** (e.g. range ≥ 1σ, ~22 pts today) — the
   ICT dealing range. Recommended. Collapses 56 pairs to a handful.
2. **Session high → low** — one stable pair all day; goes wide by the close and
   on a trending day the "discount" half marks where price was this morning.
3. **Leave it** — then the 16-point band keeps claiming to be a premium/discount
   zone, which is the thing that looked wrong.

Needs: the change, tests (**576** as of 2026-08-13; the 432 here was stale), and
a note in `CHECKLIST.md`.

## 2 · Structure lines carry no text · FRONTEND

**Status:** operator deferred — *"isko rehnde filhall"*.

`LevelsOverlay.drawStructures` labels only `confirm === 'CONFIRMED'`.

**Measured on the live 2026-08-07 payload: that yields ZERO.** Not "few" —
nothing in the session is CONFIRMED, so the rule deletes 100% of the labels.
Of ~93 marks actually drawn (12 OB boxes, 58 swing ticks, 18 EQH/EQL pools,
3 PD lines, 2 range bands) only the 3 prior-day lines carry text, because those
have their own always-label branch.

The rule was written to thin 479 labels off ~180 structures. That pressure is
gone: FVG (~85 boxes) and BOS/CHOCH were dropped on 2026-08-07, so a label
budget now exists.

Direction proposed, not yet chosen: label by KIND, not by `confirm` — OB /
EQH / EQL / PD always named (~35 labels), swings left unlabelled (58 is the
noise problem), and let confirmation keep doing what it already does through
opacity and the dashed border.

## 2b · ~~The SETUP CHECK panel is BUY-only~~ · **DONE 2026-08-08**

The panel now reads both machines and NAMES the side it is showing (a
`BUY · d3` / `SELL · u3` badge beside the state word). A side that is not
WAITING wins; with both live the BUY side shows and a caution line says the
sell side is armed too, because picking silently would hide half the machine
and preferring the scored side is the only defensible tie-break.

The 68.4% / n=19 note is swapped out on a sell for the sentence saying that
side has no score. A number belonging to one rule must not ride along beside
another.

## 3 · Left-edge level labels · FRONTEND

**Status:** open in `ui-audit.md` under Readability as **FAILING**; the operator
circled it on 2026-08-07 and then redirected to the line weights instead.

Three faults in one place:
- the price is drawn **twice** — in the left label and again in the right-axis
  chip;
- on collision the left label is **dropped**, so a level can end up with no name
  anywhere;
- 8.5–11px against the σ ribbon fills is under-contrast.

Direction proposed, not yet chosen: name on the left in a filled chip, price on
the right axis only, and de-collide by **nudging** rather than dropping.

**2026-08-13 — taken for TWO lines only, uncommitted.** `LevelsOverlay` now
draws `d3 · ARMS THE BUY` and `u3 · ARMS THE SELL` as left-edge **filled** chips
against solid 2.5px brass lines, deliberately unlike the 1px dashes every other
level uses. That is this entry's proposed treatment, applied to the two bands
§5c actually reads and to nothing else — the reason is the d2/d3 reading trap
(HANDOFF, 2026-08-13), not this entry. The three faults above still hold for
every other level.

## 4 · ~~The stop is not published~~ · **DONE 2026-08-12** (`8760d15`)

*Dated 2026-08-09 until 2026-08-13; that was the day it was specified. The field
did not exist until `8760d15`.*

Done exactly as specified: one field. `band_rotation._stop_px(level, stop_pts,
sell)` is now the single expression, called by BOTH the re-fire lock and the
published field — the file's own warning above `OPERATOR_STOP_PTS` says two
copies of a risk parameter drift silently, and a stop the chart draws differing
from the stop the lock enforces is that failure. It is emitted on every
`run_state` bar beside `level`, and on the entry record.

`RunState.stop` is **optional** in TypeScript on purpose: a server on older code
omits it, and the panel then shows NO stop line rather than computing `level`
minus 20. Absence is the correct rendering of "the server did not say".

SETUP CHECK now pairs it with the line to beat (`Todna hai > X` / `Stop < Y`),
muted rather than red — theme.ts reserves red for direction, and a stop is not
a bearish call.

Tests: `test_band_rotation_run.py` §7, six of them, including the BUY/SELL
mirror (a short's stop sits ABOVE the band) and the assertion that a moving
reference does NOT move the stop.

~~**Not yet seen on screen.** 2026-08-09 is a Sunday and the session carries no
bars, so no setup can arm and the line cannot render.~~ **2026-08-13:** the
field ships and two SENSEX setups armed on 2026-08-13 (`trigger_log.jsonl`,
09:33 and 11:06), so a `level` and its stop have existed live. Whether the
operator has *looked* at the rendered line is not recorded here and is not
claimed.

## 5 · MERA READ ships empty · needs the OPERATOR, not code

The panel's third group is the operator's own rules and starts empty. Asked
twice on 2026-08-07 what those rules are; not answered. Seeding it with three
invented lines is exactly what CHECKLIST A2 forbids, so it stays empty until
they say what goes in it.

## 6 · Hinglish stops at the Trade tab's chrome

Done: the SETUP CHECK panel, the stat strip, the toggles and their tooltips,
the disclosure lines, the legend, the `Chhupa hua:` line, EngineReadPanel's
labels, ZoneRead's `Kahan` group.

Still English: **ZoneRead's body sentences** ("no EQH pool above", "formed;
sweep not tracked"), the **leg panes** (`LegChart`), and **`App.tsx`'s CHAIN
STALE banner** plus the glance bar and ANSWER band.

Deliberately never translated, and this must survive any future pass: every
string the BACKEND authored and the UI quotes verbatim — `ctx.vwhy`, `ctx.line`,
`ctx.breadth`, `ctx.plays`, the setup fields, `trap_why`, `confirm_why`,
`structuresWhy`, `rotationRunWhy`, `flowWhy`. Translating a quote breaks
EngineReadPanel's stated promise that it shows the engine's own read.

## 7 · The session key reads oddly

`day` arrives as the literal string **`"Aug 07 LIVE"`** — no year, and with
`LIVE` inside the key. The UI renders it verbatim (A2), and `dayPrecision`
already discloses the missing year. Owed decision: fix the key at source, or
have the panel show only the date part.

## 8 · The styling backlog is elsewhere

`ui-audit.md` holds the P1/P2 items — contrast, focus indicators, ARIA,
`prefers-reduced-motion`, `transition: width`, the side-tab borders, 22
hard-coded hex values, `tabular-nums`. The operator's standing decision on
2026-08-06 is *"changes live market mein karenge"*. The SETUP CHECK panel meets
all of them from the start; the rest of the app does not.
