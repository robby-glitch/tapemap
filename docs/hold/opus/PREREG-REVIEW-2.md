# Second review: `docs/hold/PREREG-merged.md` rev 2 (Opus)

Written 2026-09-25 01:31 IST, read from the clock.

## How I checked

- I re-ran my literal probe (`scratch/xreview/prereg_probe.js rev2`) on the rev 2
  text: latch first, a writer's "payers adding" counted in rules 4 and 6, thin
  prints blind, and both-sides-leaving minutes counted by the clock.
- I replicated the §10 side read on my own frozen facts.
- The probe checks the text. It is not evidence about the market.
- The design choices she has already made are not re-opened here: the merged
  window, the quiet clock as FOLD, writers registered together, and the
  side-only read.

## Verdict: NOT YET, with five small must-fixes

All five are wording or log-schema changes. None touches a rule she chose.

Where each piece stands:
- **M1, M2 and M5 are resolved.**
- **M3 is resolved as a stated decision, and the decision is principled.**
- **M4 is resolved in its units, but not in computability.**
  - the trend-day definition classifies no trend day in the record;
  - the forward log cannot compute the day definitions or the side falsifier;
  - the log's horizon is undefined, which censors the stamps by her own exits.
- **§10 is clear and it speaks**, but one of its four counted facts is a
  logical copy of the other two.

## 1. M1 to M5

| | status | probe / check |
|---|---|---|
| **M1** latch before PATA NAHI | **resolved** | Rule 1 is the latch, and it "survives blind minutes". On these days no candle is missing after a FOLD, so the fix is tested by the text only. No new defect. |
| **M2** writers' OI | **resolved** | "Payers adding" counts in rules 4 and 6 but is not a WATCH by itself. **Short ATM PE against the trend (09-24 09:44):** FOLD at entry, "two families" (0.0 pts); W2 now holds on its own example. **With-trend short ATM CE (10:29):** FOLD at 10:43, "positioning flipped" (−3.5), during a bounce toward her strike, which the squeeze clause allows; the call expired at 0.15. **One gap:** the squeeze clause reads `grounds`' `dpx`, which does not exist before 4 closed ladder bars or when the ladder is blind. The text does not say what the own-side row reads then (S-a below). |
| **M3** readable minutes | **resolved, as a decision** | OI rows must read, and both-leaving minutes count as unpaid. The probe reproduces the stated consequence exactly: the six 09-24 puts fold at 14:08–14:10 (+204.9 / +129.2 / +112.6 / +88.8 / +40.3 / −11.3). §2 below covers whether it is principled. |
| **M4** falsifier | **partly** | Resolved: stamps as units, unlatched state, a kill clause for her clock, the 30-session bound, DRAFT until passed. Not resolved: N1, N2, N3 and N5 below. |
| **M5** the entry-check example | **resolved** | Verified at NIFTY 09-23 09:46: CE 23,400 BUILDING, held 09:44–09:46 (payers against, 3 minutes); CVD −529 since 09:30, rank 0.67; prints 2 sell / 0 buy (strict flow against). Trend rows all RANGE, so it is exactly two families, as the example says. |

## 2. The M3 decision: is it principled, and is its kill clause computable?

**Principled: yes.**
- "Both sides leaving" is a positive OI read: both nearer fronts are
  UNWINDING. It is not a failure to read.
- For a buyer it means the forced-covering signal is ambiguous. The side that
  should pay her and the side that should hold for her are both covering.
  Ambiguity is not payment, and her own wording is "nothing is paying".
- It is also the one mechanism in the map that can see §9.1's "the payers
  went quiet".

**The cost is stated.** Every expiry afternoon unwinds both sides (49 minutes on
09-24 SENSEX, all after 13:30). So the clock will fold buyers about 15 readable
minutes into that unwind whatever the direction. Clause 5 is the exit for this.

**Computable: not yet.** Clause 5 needs to know which rule produced each FOLD
stamp. The §8 row has `verdict`, `since` and `clock`, but no `fold_rule` field.
The precedence can be re-derived only by re-running the map. That breaks the
"answered from these rows and nowhere else" promise (N5).

It also needs the 30 minutes after each stamp, and the log's horizon is
undefined (N3).

## 3. The falsifier (M4)

### N1 (must fix): the trend-day definition classifies no trend day

"5m, 15m and 1h read the same direction on at least half of the session's
readable minutes" gives these shares (all three rows the same direction):

| index-day | share | a trend day by rev 2? |
|---|---|---|
| **SENSEX 09-24** | **46 %** | no |
| **NIFTY 09-24** | **35 %** | no |
| SENSEX 09-23 | 20 % | no |
| BANKNIFTY 09-24 | 6 % | no |
| every other index-day | 0–8 % | no |

So clause 3, B1, B5 and S-P1 can never bind on a day like 09-24, the reference
trend day. The pinned-day rule (two RANGE on at least half) does classify:
NIFTY 09-23 (61 %) and BANKNIFTY 09-23 (67 %). It also classifies NIFTY 09-22
(54 %), an expiry day that fell 105 points.

**Minimal fix, with no new number:** define both days by §10's own vote.
- A **trend day** is one where the same side (CALLS or PUTS) is named on
  **more than** half of the readable minutes.
  - SENSEX 09-24: PUTS 94 %. NIFTY 09-24: PUTS 88 %.
- A **pinned day** is one where "no side" stands on more than half.
  - NIFTY 09-23: 62 %. SENSEX 09-23: 55 %.
- Use "more than half", not "at least half", so a day cannot be both.

That this definition matches the house's labels for the reference days is a
check that it works, and it should be disclosed as one.

Two edge cases, disclosed:
- **BANKNIFTY 09-24 sits on the edge.** PUTS is 48 % on my [I] candles (no
  side 52 %, so "pinned") and 55 % on Fable's (so "trend"). A borderline day
  reads borderline.
- **NIFTY 09-22 reads pinned under both definitions** (no side 65 %), though
  the day fell 105 points in 30 minutes. A short leg inside a range day is
  still a range day.

### N2 (must fix): the log cannot compute the day definitions or the side falsifier

§8 writes rows **per trade** (marked or imported). Two things need **every
minute of every index**, whether or not she is in a trade:
- classifying a trend or pinned day;
- §10.6's side stamps.

On a day she trades only in the afternoon, the morning is missing.

**Fix:** a per-index session row, one per finished minute:
`data/hold/side_<day>.jsonl` with `{t, idx, 5m, 15m, 1h, side, facts, blind}`.
It is written live, and completed by the close-time import. Anytime-start makes
it exact.

### N3 (must fix): the log's horizon is undefined, so her own exits censor the stamps

Rows are "one per finished minute per marked trade", but the text never says
until when.
- If the rows stop at her exit, every FOLD that comes after her exit is never
  logged. Every noise stamp after it is lost too, along with the 30-minute
  excursion after any late stamp.
- Her exits are early by her own account (failure (a)). So clause 1, the core
  test, would be judged on a population filtered by the very failure the window
  exists to fix.

**Fix:** log each trade from its entry to 15:29, or to its first FOLD + 30
minutes if that is sooner, **regardless of her exit**. The import does this
exactly.

### N5 (must fix, small): three undefined words

- **`fold_rule`**: add it to the row (3 line / 4 flipped / 5 quiet / 6 two).
  Without it, clause 5 can only be recovered by re-running the map.
- **"collapses"** (§7.4, §10.6): say "clause 1's comparison reverses".
- **"a reversal of the index within 15 minutes"** (§10.6): undefined, since no
  size is given. Say "the side read names the other side, or no side, within 15
  minutes". That is computable and adds no number.

### Should fix

- **Excursion units.** "Premium points" pools NIFTY and SENSEX, which differ
  about 3× in scale, so SENSEX stamps would dominate the comparison. Compare
  within an index, or use % of the stamp-minute premium.
- **A minimum number of sessions.** At her pace (about 10 round trips a day),
  15 FOLD stamps and 15 noise stamps arrive in 2 or 3 sessions. The falsifier
  would then run on one or two regimes. Add "and at least 10 sessions", §1d's
  own horizon.
- **B1's second half is vacuous.** Any WATCH count exceeds zero. Drop it.

**Would it kill a wrong buyer window within 30 sessions?** Yes, once N1, N2,
N3 and N5 are fixed. Her trade frequency supplies the stamps; clause 2 and
clause 3 (with N1) stop it from passing by folding everything; clause 4 stops
one day from carrying it.

**For writers it will be inconclusive at 30 sessions**, which clause 6 states
honestly.

## 4. The §10 side read

1. **The rule is clear, and it speaks.**
   - "≥ 2 of 5m · 15m · 1h one way, none the other way" gives CALLS or PUTS;
     anything else is "no side".
   - Replicated on my facts to the minute: SENSEX 09-24 PUTS 354 / no side 21;
     NIFTY 09-23 CALLS 141 / no side 233; SENSEX 09-23 CALLS 168 / no side 205.
     NIFTY 09-24 gives 330 against their 338, because my candles there are [I].
2. **N4 (must fix): the counted facts double-count.**
   - Fact 1 (the OI half, `board.oi_read`) is, by construction, "holders
     BUILDING and payers not BUILDING". On every minute it read "for" (463
     minutes over 9 index-days), fact 3 was also "for". On every minute it read
     "against" (392 minutes), fact 2 was also "against".
   - So "3 for · 0 against" is two independent facts plus one copy.
   - **Fix:** print the OI half as the summary line of facts 2 and 3, and do
     not count it. This is the same caution the board's own agreement note
     gives.
3. **The lag is honestly described in 10.5** ("tens of minutes"; old side, then
   no side, then the new side). But **S-P3's "15–45 minutes" is a new number,
   and their own replay already contradicts it:**
   - SENSEX 09-24 still read PUTS 60 minutes after the 14:24 low;
   - NIFTY 09-22 never named PUTS during the 10:20 fall, and named it at 12:11.
   - Restate S-P3 as the shape without the numbers, or measure the lag forward.
4. **Its falsifier is not computable from the log as specified.** N2 (no
   per-index minute log) and N5 ("reversal" undefined) apply here.
5. **It matches her simplification.**
   - CALLS / PUTS / no side, per index;
   - "your side vs the read: agrees / against / no side" beside the entry check;
   - never an exit instruction, and no alert.
   - **A small anytime-start slip:** the expiry line reads
     `upstox_instruments.option_expiry`, from the live dump. At the close-time
     import on an expiry day, that weekly has already left the dump. Take the
     expiry from the day's chain record, or from the tradebook's `expiry_date`,
     as their own replay did.

## 5. Other should-fixes (not blocking)

- **S-a.** Say what a writer's own-side row reads when `dpx` is blind (first ~20
  minutes, or no ladder): "could not check — no ladder window yet", with rule 4
  unavailable for her until then.
- **S-b.** "Too thin to read … on SENSEX that is most of the day" is true on
  09-23 (331 of 375 minutes) but not on 09-24 (100 of 375). State the measured
  share, or drop "most".

## The minimal list to reach SIGNABLE

1. **N1:** trend and pinned days defined by §10's side vote, "more than half".
2. **N2:** a per-index, per-minute session log (`side_<day>.jsonl`), live and
   completed by the import.
3. **N3:** each trade logged from entry to 15:29 (or first FOLD + 30 min),
   whatever her exit.
4. **N4:** the OI half printed but not counted in §10.2.
5. **N5:** `fold_rule` in the row; "collapses" and "reversal" defined as above.

With those five, I would sign it.
