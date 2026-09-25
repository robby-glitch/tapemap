# HOLD / FOLD — the rules (Fable)

**Written 2026-09-24 23:40 IST, after the close, BEFORE any replay was run.**
Nothing below is a result. Every threshold is fixed here with its reason.
If a rule changes after data is seen, the original text stays and the change
is appended under §10 with the reason.

---

## 0. What the window is for

Direction is not her problem. Two failures are:

- **(a)** leaving a good trade on noise — one red candle, a small pullback, a
  red P&L number;
- **(b)** staying in a bad trade after its reason is gone — hope, FOMO.

So the window answers exactly one question, every minute, from facts:
**is the reason you entered still true?** It never answers "is this trade
profitable". P&L is shown small and grey and feeds nothing.

It is advisory. It never places, modifies, sizes or suggests an order.

## 1. The trade, in the tool's words

A trade is (index, strike, CE/PE, long/short, entry minute, entry price, qty).
From it:

| trade | role | **want** (index direction the thesis needs) | **payers** (writers who pay if it goes `want`) | **wall** (writers holding the other way shut) |
|---|---|---|---|---|
| long CE | buyer | UP | CE writers | PE writers |
| long PE | buyer | DOWN | PE writers | CE writers |
| short CE | writer | DOWN ("not up") | — | CE writers, me among them |
| short PE | writer | UP ("not down") | — | PE writers, me among them |

A **buyer** is a bet that the move in `want` is being paid for.
A **writer** is a bet that the move the other way (**danger** = −want) is
absent or exhausted. That one sentence is the whole writer mapping: a writer
uses grounds.py's *exhaust* reads on the danger direction, a buyer uses its
*move* reads on the want direction. Nothing new is invented for writers.

A spread is read on its net direction: a debit spread as its long leg, a
credit spread as its short leg. The second leg enters P&L only.

## 2. The four reads

Each read answers **FOR / AGAINST / FLAT / BLIND** — grounds.py's four words,
unchanged. BLIND always prints its reason ("could not check — …").
Three of the four are the tool's existing, already-registered reads with the
trade's direction substituted for the engine's call. One (STRUCTURE) is new.

### 2.1 STRUCTURE [M] — the hard read (new)

The **invalidation level L** is a price on the index.

- **Set at entry.** Bearish trade (want DOWN): L = the most recent 5-minute
  swing high of TODAY (a pivot: its high above the 2 bars either side —
  trendbox's PIV = 2, on trendbox's 09:15-aligned 5-min bars, closed bars only)
  that sits **above** the index's 1-min close at the entry minute. If there is
  none, L = the session high so far. Bullish trade: mirrored with swing lows /
  session low.
- **Trails, one way.** When a new 5-min pivot confirms (i.e. 2 bars after it
  close) that is nearer to price than L and still on the far side of price,
  L moves to it. L never moves away from price.
- **BROKEN** when a **1-minute index CLOSE** lands beyond L (bearish: close > L;
  bullish: close < L). Buffer **0**. A wick beyond L is not a break.
- **Latched.** Once broken, broken for this trade. Re-picking the trade (a new
  entry minute) starts a new trade with a new L. That is honest: after a
  structure break she is in a different trade.

*Why 5-min pivots:* 1-min swings are noise; 15-min swings are too far for an
intraday option. PIV = 2 on 5-min is what trendbox already uses for its swing
rows — one definition of "a swing" in the tool, not two.
*Why the 1-min close:* one red candle that does not close the index beyond a
25-minute structure is noise **by construction**, not by opinion.

### 2.2 FUEL [M] — the OI read (grounds._oi, unchanged)

Fronts = `fronts.read` over the nine strikes nearest spot, top 2 per side by
session-peak OI **as of that minute** (the running peak — causal; the
end-of-day peak must never rank a minute earlier in the day). The read uses the
#1 front on each side, exactly as grounds does.

- **Buyer:** `_oi("move", want)`.
  FOR — the payers' front is UNWINDING (covering is paying the move), or the
  wall is BUILDING while the payers are not (the other side is holding).
  AGAINST — the payers' front is BUILDING and the wall is not (a defender
  standing in the way). FLAT — otherwise, including both sides unwinding
  ("writers leaving both sides, no direction").
- **Writer:** `_oi("exhaust", danger)`.
  FOR — my side's front is BUILDING or STALLED (the writers are holding, the
  danger move's fuel is off). AGAINST — my side's front is UNWINDING (the
  writers are covering: the squeeze is being paid for). FLAT — otherwise.

Display only, not in the verdict: the last fold on each side (from
`fronts.folds`), when, and its distance from spot. On the wall side, a fold
within 2 strike-steps of spot is worded "winners cashing in" — the exhaustion
pattern from her doctrine (build → stall → unwind; the side that stops first).
It stays a printed fact until registered separately (§8).

### 2.3 FLOW [I] — the ladder read (grounds._cvd + grounds._flow, unchanged)

Buyer: `_cvd("move", want)` and `_flow("move", want)`.
Writer: `_cvd("exhaust", danger)` and `_flow("exhaust", danger)`.
Window = the last 3 closed 5-min ladder bars (15 min), grounds' `W`; "strong"
and "one-sided" are grounds' STRONG = 0.5 / ONE_SIDED = 0.8 ranks against the
day's own 15-min changes; a side "dominates" the prints with ≥ 2 and ≥ 2× the
other. Merged into one word: AGAINST if either is AGAINST; FOR if either is
FOR and neither AGAINST; FLAT if both flat; BLIND if both blind (with both
reasons). It updates only when a 5-min ladder bar closes, so it cannot react to
one 1-min candle.

GoCharting's footprint marks are NIFTY-only; they are printed, never counted,
so the three indices read by one rule.

### 2.4 TREND [I] — trendbox's 5m / 15m / 1h rows, unchanged

The three middle rows (the ones REGIME reads), each UP / DOWN / RANGE / forming.

- **Buyer:** FOR — ≥ 2 of 3 read `want` and none reads against; AGAINST — ≥ 2
  read against; FLAT — otherwise (including forming rows).
- **Writer:** AGAINST — ≥ 2 read `danger`; FOR — none reads danger and none is
  forming (a range is a writer's friend); FLAT — otherwise.

## 3. The verdict

- **FOLD** — STRUCTURE is BROKEN; **or** at least **2 of the 3** soft reads
  (FUEL, FLOW, TREND) are AGAINST at the same minute. Latched: once FOLD, FOLD
  for this trade, printed with "since HH:MM".
- **WATCH** — exactly 1 soft read is AGAINST. Not latched; it clears when the
  read clears.
- **HOLD** — nothing is AGAINST.
- BLIND reads count as neither. If STRUCTURE is blind (no index candle at
  that minute) the verdict is **PATA NAHI**, never HOLD.

No probability, no score. "2 of 3 against" is a count and is allowed.

**At entry** the same rule runs on the entry minute and is printed as
"entered into: HOLD / WATCH / FOLD". A FOLD or WATCH at entry is the FOMO
guard: it says the reason was already thin when she pressed buy.

## 4. Noise versus break, in her words

**Noise** (the window does not move): one red candle; the premium off its
high; the premium under its own VWAP; the P&L line red; a 1-min wick beyond L;
the 1m / 3m trend rows flipping; a single fill run against you; a red 5-min
candle that does not close beyond L.

**Break** (the window says FOLD): a 1-min index close beyond a 25-minute
structure; or two of three independent families — OI, order flow, trend —
against the trade at the same time.

## 5. Calm by construction

The fastest input into the verdict is the 1-min index close, and it is judged
against a level at least 10 minutes old (a pivot needs two closed bars after
it). Everything else moves on 5-min ladder bars or 15-min OI slopes. The
premium's own candles feed nothing except the grey P&L line. The only colour
on the window is the verdict word.

## 6. Absence

Every read prints one of exactly three sentences: **"checked, none"** /
**"could not check — why"** / **"not showing you — why"**. A missing value is
never 0. A stale OI grid (> 3 min behind, fronts.STALE_MIN) makes FUEL blind
with that reason.

## 7. Anytime-start

Everything is recomputed from the day's record from 09:15: the index 1-min
candles (REST, exact), the OI minute grid, the ladder bars. L at entry depends
only on bars closed before the entry minute. Opened at 13:00 for a 10:19 entry,
the window reads what it would have read had it watched since 10:19, and says
so ("backfilled [M]").

## 8. What must be pre-registered before a live verdict

1. STRUCTURE (§2.1): the 5-min PIV = 2 pivot, the 1-min close, buffer 0, the
   one-way trail, the latch.
2. The verdict map (§3): hard structure; 2-of-3 soft; WATCH at 1; latch.
3. The writer mapping (§1): writer = exhaust-of-danger.
4. The trend-row vote (§2.4) — new use of trendbox's rows, which are display
   only today.
5. Candidate, NOT in the verdict until registered on its own: "wall fold
   within 2 steps of spot = exhaustion" (§2.2).
6. Candidate, NOT in the verdict: premium-vs-index divergence (the mirror's
   DIVERGES) as a buyer's "the option is not paying" read.

**Predictions, committed now, before replay:**
- P1. On a trend day, trades WITH the trend read HOLD on most of their
  in-trade minutes; FOLD fires on a minority of the day's minutes. If FOLD
  fires on most minutes of a trend day, the rule is reading noise.
- P2. On a range day, directional buys read WATCH or FOLD early — within the
  first two 5-min ladder bars after entry — more often than on a trend day.
- P3. Structure breaks are rare: a handful per direction per day.
- P4. Repeated re-entries in the same contract on a range day will each be
  met by the same WATCH/FOLD state, because the state comes from the tape,
  not from the trade.

**Falsifier (committed now):** over 30 forward sessions of logged trades,
compare the option's favourable excursion over the next 30 minutes after a
FOLD minute against a HOLD minute in the same trade type. If FOLD minutes are
not followed by worse excursions than HOLD minutes, **or** FOLD fires on the
majority of in-trade minutes on trend days (P1 fails), **or** the result
collapses when the single worst trade is removed, the verdict is noise and
the map is deleted rather than tuned. The reads stay (they are grounds' and
trendbox's, with their own kill conditions).

**Hazards, recorded now:** the latch keeps FOLD after a break that price
reverses within a minute; a 5-min pivot confirms ~10 min after the swing, so
early in a leg L is often the session extreme; grounds' side attribution is
[I]; ranking by running peak can switch the #1 front between two minutes and
flip FUEL — printed as it happens, not smoothed.

## 9. Parameters, fixed here

| parameter | value | from |
|---|---|---|
| swing bar | 5-min, 09:15-aligned, closed bars only | trendbox |
| PIV | 2 | trendbox |
| break | 1-min index close beyond L, buffer 0 | this file |
| latch | yes (FOLD) / no (WATCH) | this file |
| ladder window W | 3 closed 5-min bars | grounds |
| STRONG / ONE_SIDED | 0.5 / 0.8 | grounds |
| flow dominance | ≥ 2 and ≥ 2× | grounds |
| fronts NEAR / TOP / UNWIND / STALL / SLOPE | 9 / 2 / 0.15 / 0.05 / 15 marks | §1d |
| stale grid | > 3 min | fronts.STALE_MIN |
| trend rows | 5m, 15m, 1h; N = 20 | trendbox |
| soft-family FOLD | 2 of 3 | this file |

None of these is to be grid-searched. Changing one is a new registration.

## 10. Changes after seeing data

**2026-09-25 00:40 IST, after the replay of 31 trades (REPORT.md).** Nothing
above this line was edited. **No rule was changed and no parameter moved.**
What the data made me want to change is logged here as proposals, each
needing its own registration and falsifier before it touches a verdict.

**A. Proposed, NOT applied — the near-spot wall fold as a FUEL against (§8.5).**
On 09-24 the CE side folded at 74200 (13:39, spot 73,880) and 74000 (14:12,
spot 73,648) — the winners cashing in at spot, her build → stall → unwind
sequence on the side that was winning — and the low printed at 14:24. The
window's FUEL read stayed FLAT because grounds ranks the #1 front by
session-peak OI and that front (CE 74300) sat 700 points away, so both #1s
were "unwinding — no direction". The proposal: for a **buyer**, when the wall
side's nearest sized strike within 2 steps of spot has folded (`fronts.folds`)
inside the last 15 minutes and the payers' side has no fold nearer to spot
than that, FUEL = AGAINST, worded "wall folded at spot — winners cashing in".
**Why not applied tonight:** it is one day's pattern; applying it and re-running
the same day is how a rule gets fitted. It would have turned entries 11–13 on
09-24 from HOLD to WATCH. To be registered on its own with a falsifier and
judged on forward rows.

**B. Proposed, NOT applied — a PAY read for buyers (§8.6).** On 09-22 the
23500 PE gave back 222 → 134 between 14:00 and 14:14 inside an intact
structure (36 points of room; expiry day, in-the-money). The window said HOLD
and was right about the thesis and silent about the option. The proposal: the
mirror's DIVERGES (index new extreme in `want`, premium no new extreme in the
same window) as a fourth soft read for buyers only. **Why not applied:** it
changes what the window is — a thesis read — into a P&L read, and that is a
design decision for her, not a threshold for me.

**C. Recorded, not changed — buffer 0.** The 09-22 11:14 FOLD came on a
two-point close over a swing high (23,393 over 23,391). A buffer is a tunable;
the point of the rule is that there is none. If she wants one it is a new
registration, stated in points or in σ, before it is used.

**D. Recorded — the running-peak flip.** At 10:37 on 09-24 the PE #1 front
read BUILDING again for a few minutes after its 10:22 fold and FUEL flipped
to AGAINST; with the flow divergence that made a FOLD at 179.15 on a put that
closed at 620. §8's hazard list named this. Not smoothed; a smoothing window
would be a tunable.

**E. Recorded — sub-minute trades.** Twelve of the 31 lasted a minute or less.
The window has one reading for them, the entry read. That is the design, not a
gap: it can refuse a reason that is not there; it cannot manage ten seconds.

---

**2026-09-25, after reading the other designer's work (CRITIQUE.md). The
times "01:30" and "01:50" below were estimates, not clock reads — Opus's
review (S7) caught it; the system clock read 01:22 IST when the round-4
registration was written, so both entries were made before that. The file's
mtime is the time.**
Still nothing applied to the registered rule. Two more proposals, and A is now
visible in the prototype as a labelled **variant toggle, off by default**.

**F. Proposed, shown as a variant — FUEL is blind while the grid is forming.**
`fronts.read` on two marks returns a slope over two marks and my engine called
it "flat" at 09:17 on 09-23 (RULES §6 covered a *stale* grid, not a *forming*
one). The other window said PATA NAHI there ("the build → stall → unwind
sequence needs 15 one-minute marks, 2 so far"), which is house rule 6 read
correctly. Proposal: FUEL = could not check until `fronts.SLOPE_MARKS` (15)
marks exist. Not a threshold — a reuse of §1d's own number — but post-data, so
it rides with A on the toggle and waits for her word.

**A, restated as the toggle implements it (unchanged in substance):** for a
buyer, a wall-side fold within 2 strike-steps of spot inside the last 15
minutes, with no payers'-side fold nearer to spot, reads FUEL = AGAINST,
worded "wall folded at spot — winners cashing in". Unregistered.

**G. Proposed, NOT in the toggle — the writer's own-crowd unwind needs a
direction.** Both windows folded a with-trend short call (09-24, CE sold at
10:29–11:00, expired at 0.15) because the CE front near spot was UNWINDING and
both rules read that as "the writers are covering / the side holding your
trade is leaving". In a falling market, call writers at a lower strike buying
back are the winners cashing in, not a squeeze. Proposal: for a writer, an
own-side front UNWINDING reads AGAINST only while spot is moving **toward** her
strike over the same 15-minute window; moving **away**, it reads FOR
("winners cashing in — your strike is farther from spot than at your entry").
Not applied: it is a new clause and it was seen on one writer row on one day.

**H. Not proposed, recorded.** The other window's "R-fold + one confirmation
= FOLD" (their rule 3A) folded a with-trend put at 13:12 on 09-24 at 201.9 that
reached 448 by 14:35: on a trend day the ceiling moves down strike by strike,
and each move is a fold. My §8.5 candidate was kept out of the verdict for
that reason.

**A, result of switching the toggle on (2026-09-25 01:50), recorded so it is
not tuned.** On 09-24 for a put buyer, A fires on 119 minutes, the first at
10:14 (CE 74,000 folded 10:14, 134 pts from spot) — the same minute and fact
as their 3A's first FOLD — and it does not fire at 14:12–14:24: the folds the
brief called "near spot" (CE 74,200 at 13:39, CE 74,000 at 14:12) were 320 and
352 points from spot, beyond two steps. Distance does not separate a ceiling
stepping down from the winners cashing in; on this day the exhaustion fold
was the farther one. The parameter stays at 2, A stays off, and it is no
longer a candidate I would put forward: what differed at 14:12 was that the
payers' side had gone quiet (last PE fold 13:46, both fronts unwinding), which
is a clock on the payers, not a distance on the wall. F fired where it should
(09-23 09:17).
