# The operator's exit rules for a SHORT

**Date:** 2026-08-08, dictated by the operator in answer to four questions,
plus one rule they added unprompted.
**Status:** specification. Nothing built yet.
**Why it exists:** `CHECKLIST` H has recorded *"a seller's stop and decay
target"* as owed by the operator since 2026-07-31, and the 2026-07-31 setup
spec says outright *"Do not invent them."* The u3 SELL mirror shipped on
2026-08-08 borrowing the BUY side's exits, and the first real session run
showed exactly why that borrow is wrong. This document closes the gap.

Quotes are the operator's, kept verbatim where the wording carries meaning.

---

## What forced this

The mirror was run over the operator's own Kite export of NIFTY AUG FUT for
**Friday 2026-08-07** (3-minute bars, their own VWAP and σ columns — so our
band pipeline was not part of the question).

    09:54  ARMED       high 24707 tagged u3 24704.62
    10:03  TRIGGERED   close 24685 < the reference candle's low 24690
    10:09  EXIT        VWAP

Entry 24685 with **VWAP at 24680.5** — 4.5 points away. The trade closed two
bars later for about four points. Price went on to 24601 by 14:15.

The cause is structural, not a bug: **the two-candle confirmation eats most of
the u3→VWAP distance before it ever triggers.** By the time price closes below
the reference candle's low it has already travelled most of the way back to the
mean. A VWAP-first exit, which was measured on the BUY side (`trail_score`:
*"hold the stop until VWAP, never breakeven"*), therefore fires almost
immediately on a short. The buy side does not have this problem because its
exits were designed against its own entries.

## The rules

### 1. What CLOSES the trade

> *"i like stay in a trade till the time market didnt show me 2 green candle
> in the chart"*

**Two CONSECUTIVE green candles**, and the operator chose the strict reading of
green: `close > open` **AND** `close > previous close`. A red candle in between
resets the count. A small green candle closing below the prior close does not
count.

Chosen over the looser readings deliberately. On the Friday session "any two
green candles" would have closed the 10:03 short almost immediately — 10:06 and
10:12 were both green, inside a move that ran another 80 points.

Plus the two conditions that already exist or were added here:

- **The stop**, `level + OPERATOR_STOP_PTS` (20) — above the band it armed on.
  Unchanged, and never hit on Friday (session high 24707 vs stop 24724.6).
- **An opposite-side entry.** The operator, unprompted: *"or my buy signal gets
  genrated the other side lets say that can be a rule as well"*. Both machines
  already run per bar, so this costs nothing to know.
  **OPEN below:** whether a merely ARMED buy closes the short, or only a
  TRIGGERED one.

### 2. How FAR the trade is aiming — the target ladder

> *"if oi is heavy like on ce side like they want to sell or try to hold it
> till -3 std vwap"*

- **Ordinary case:** band to band — **u2, then u1, then VWAP**.
- **CE-heavy case:** the target extends to **d3**, the far side.

### 3. The two never fight

The operator's own choice, and it is the whole design: **OI decides HOW FAR,
candles decide WHEN TO LEAVE.** A CE-heavy book raises the target; it does
**not** license ignoring the two green candles. So a short can be aiming at d3
and still close at u1 because the candles said so.

The rejected alternative was letting a heavy CE book overrule the candle exit.
Rejected because it puts an *unscored OI reading* above the thing the operator
is actually watching, and leaves no way out when that reading is wrong.

### 4. What measures "CE side heavy"

`oi_flow`'s **CALL-heavy %** — the same figure the OI strip under the chart and
the SETUP CHECK panel already display (*"CALL-heavy 62%"*). Chosen over the
engine's `w_ce` writer score and over PCR for one reason: **the rule must read
the number the operator reads.** A rule keyed to a figure that appears nowhere
on screen cannot be checked by eye, and two definitions of "heavy" drift apart
the way the 09:25 gate did.

**This is NOT C11's rejected veto.** C11 measured OI strength ≥40% as an ENTRY
filter and found it removed 10 of 12 signals including 9 winners. This is a
TARGET extension on an already-open trade — a different use of the same number,
and C11 says nothing about it either way.

---

## Plumbing this needs — and the honest failure mode

`run_states` sees **index/FUT bars only**. Those carry `oi`, but not the chain's
CE/PE split, which lives in `chain_metrics` / `oi_flow`. So the CE-heavy
condition needs a per-bar chain series passed into the detector, the same way
`index_series` is passed for the compression read.

**When that series is absent the condition is UNKNOWN and the target stays on
the ordinary ladder.** It must never fall back to a guess — the discipline
`band_rotation._trap` already follows (*"Without that series the compression
verdict is UNKNOWN and never falls back to premium"*).

The exit itself belongs in `run_states`' lock branch, beside the stop and VWAP
tests it replaces. One loop, both sides — the constraint the entry mirror was
built under.

---

## OPEN — must be answered before this is built

1. **The CALL-heavy threshold.** No percentage was given. 40% is the only
   number anywhere in the record and it appears as a *rejected entry filter*,
   so borrowing it here would be borrowing a number from a question it was
   never asked. **Do not pick one.**
2. **Does an ARMED buy close a short, or only a TRIGGERED one?** ARMED exits
   sooner and more often; TRIGGERED is the actual signal. Not stated.
3. **Position sizing is still undefined**, so "band to band" here specifies a
   TARGET LADDER, not partial exits. If the operator means scaling out at u2
   and u1, that is a different rule and needs sizes.
4. **The BUY side is untouched by this document.** Its exits are scored
   (`trail_score`); nothing here may be applied to it.

## How this gets validated

It does not, yet — and that is deliberate. `research-findings.md` §5's stop
rule is in force: seven consecutive negative or falsified tests outside NIFTY
d3, and any new hypothesis must be pre-registered before the run. The SELL side
already exists over a REJECTED verdict at the operator's explicit instruction
(CHECKLIST C12), so these exits ship as **rules the operator follows**, not as
measured edges, and no surface may present them as scored.

`trigger_log.py` is the route to real evidence: it records every fire live, and
needs a server restart to activate.
