# HOLD or FOLD: the rules, written before any replay

**Written 2026-09-24 23:45 IST, before the window was run at any minute of any
trade.** Status: **DRAFT. Nothing below has been registered.** The window
shows these verdicts marked DRAFT until Mary registers them (see section 8).

**What I had already seen when I wrote this, stated so nobody has to guess:**
the coordinator's summary of 2026-09-24 (the trend rows read DOWN at her
exits, the engine's SPENT/WAIT headlines, put folds at 09:46 / 10:23 / 12:27 /
13:27 / 13:46, call folds CE 74200 at 13:39 and CE 74000 at 14:12, the low at
14:24); one `/api/board?idx=SENSEX` payload as of 15:29 (47 folds, first fold
PE 74000 at 09:46); and the coordinator's list of her 09-21 to 09-23 trades
with their signs. I have not computed any fact, state or verdict at any
minute. No threshold below was chosen by looking at a trade.

---

## 1. What the window is for

Her words: direction is never her problem. Management is. Two failures:

- **(a) folding a good trade on noise**, such as one red candle or a pullback;
- **(b) holding a bad trade on hope** after its reason has gone, and the chop
  version of the same thing: re-entering again and again when nothing is paying.

So the window answers one question at every finished minute: **is the reason
for this trade still standing?** It answers from positioning and order flow.
**It never answers from the premium's own candles.** The premium is shown as
context and never gets a vote. That is the whole mechanism against failure (a):
a red candle cannot move the verdict, because no candle is an input.

## 2. The trade reduces to a direction and a role

| trade    | direction `d` she needs     | role   |
|----------|-----------------------------|--------|
| long CE  | up (+1)                     | buyer  |
| long PE  | down (−1)                   | buyer  |
| short PE | not down (+1)               | writer |
| short CE | not up (−1)                 | writer |
| spread   | a debit spread reads as its long leg, a credit spread as its short leg | |

From `d`, two sides of the near-ATM book:

- **Q, the side that PAYS for the move.** These are the writers who are forced
  if price travels `d`: CE writers for up, PE writers for down. When they
  cover, the move gets its fuel (the operator thesis: trapped inventory is the fuel).
- **R, the side that HOLDS the thesis.** These are the writers whose staying
  put protects it: PE writers (the floor) for up, CE writers (the ceiling) for
  down. **For a writer, R is her own crowd.**

A long PE and a short CE have the same Q and R, and they break on the same
facts. The one difference between a buyer and a writer is rule 5.4, below:
a buyer needs someone to be paying her, and a writer is paid by time.

## 3. The facts, all from what TapeMap already computes (nothing new is measured)

Read at finished minute `t`, with every input cut to `t` (a grid cut at `t`, a
running session peak up to `t`, ladder bars closed by `t`, runs begun by `t`).
The same inputs always give the same answer, and a restart reads a past minute
exactly as it read live.

| fact | source (existing code, unchanged) | tag |
|---|---|---|
| **Q state**, **R state**: BUILDING / STALLED / UNWINDING of the **nearer to spot of that side's §1d top 2** | `fronts.read` + `board.nearer` (§1d: nine strikes, top 2 by session-peak OI, 15 % unwind, ±5 % stall, 15-mark slope) | [M] |
| **folds**: a sized strike-side inside the nine, first read UNWINDING after a new high | `fronts.folds` (FOLD_SIZE 0.15), `board.still_folded` | [M] |
| **CVD**: 15-min change over 3 closed 5-min ladder bars, ranked against today's own; top/bottom divergence | `grounds.facts` (W 3, STRONG 0.50) | [I] |
| **FLOW**: fill runs + stacked imbalances, buy vs sell, in the same 15 min | `grounds.facts` (dominance = at least 2 prints and 2× the other side) | [I] |
| context only (never a vote): premium vs entry, premium vs its own session VWAP ±σ, trend rows 5m / 15m, next wall on the Q side, GoCharting footprint (NIFTY) | `/api/contract`, `trendbox.rows`, `board.headline` | [M]/[I] |

The engine's own words (SPENT, WAIT, CAUTION, GO) are **not inputs**. On
09-24 they were marked CONTRADICTED or THIN by the tool's own grounding again
and again, and a HOLD/FOLD window that repeated them would carry the same fault.

## 4. How each fact reads for this trade

- **Q (the payer):**
  - UNWINDING → **pays**;
  - a Q-side fold in the last 15 min → **pays**;
  - BUILDING, held for 3 finished minutes, with a build today (peak > 0) →
    **against**: "writers adding in its way";
  - STALLED, or never built today → **flat**.
- **R (the holder):**
  - BUILDING (peak > 0) → **holds**, which supports the trade but does not pay it;
  - UNWINDING, held for 3 finished minutes → **against**: "the side holding
    your trade is leaving";
  - otherwise → **flat**.
- **R-fold:** a fold on the R side stamped in the last 15 min and still folded
  at `t` (no new high, not BUILDING) is a **break candidate**. It counts
  whether it was stamped before or after entry. A trade entered 5 minutes after
  its ceiling folded was entered without a ceiling.
- **Both sides leaving:** when Q and R are both UNWINDING (her expiry
  afternoons, and `grounds`' 2026-09-23 rule), OI says nothing about which way
  price goes. Then every OI fact above, the folds included, reads **flat**, and
  order flow decides.
- **CVD:**
  - strong (rank ≥ 0.50) the trade's way → **pays**;
  - strong the other way → **against**;
  - for a **buyer** only, a divergence against `d` (price made a new extreme
    in `d` and CVD did not) → **against**: "the move is not being paid for";
  - otherwise → **flat**.
  - **Blind** when there are fewer than 4 closed ladder bars.
- **FLOW:**
  - dominant the trade's way → **pays**;
  - dominant the other way → **against**;
  - otherwise → **flat**.
  - **Blind** when neither fill runs nor stacks can be read (it says why,
    and never reads as "quiet").

**Why 3 minutes of persistence for state facts, and none for folds.** A fold
is already de-noised: 15 % off its own high with a falling 15-minute slope,
stamped once. A BUILDING/UNWINDING state is read fresh every minute, and on
2026-09-23 the §1d gate flickered minute to minute from 09:50 to 10:05. Three
minutes is §1d's own `STALE_MIN`, and it is the zone machine's bar, so no new
number is introduced. "Pays" facts need no persistence: a paying fact only
ever keeps a trade open. Asymmetric on purpose, because failure (a) is the
one she named first.

**Why 15 minutes for "recent".** It is the window every family already uses:
grounds' 3 closed 5-minute bars, and §1d's 15-mark slope. One number, reused.

## 5. The verdict, in order (the first rule that matches wins)

1. **Once FOLD has fired, it stays FOLD for that trade.** It shows the time it
   fired and the reason. If the break later heals, it says so ("the break has
   healed since 14:16; a re-entry is a new trade") but the verdict does not
   flip back. A broken thesis is a one-way door, and a window that flips
   FOLD→HOLD→FOLD is the panic machine she is trying to escape.
2. **PATA NAHI**: the near-ATM fronts could not be read, or the grid's newest
   mark is more than 3 min behind `t` (`fronts.stale`). A blind window says so
   and shows no verdict. A missing value is never a zero.
3. **FOLD, thesis broken**, on either of:
   - **A. the holder was forced out:** a live R-fold candidate, **plus one
     confirmation**: Q against (writers adding in its way), CVD against, or
     FLOW against;
   - **B. the positioning flipped:** Q against **and** R against, both held
     for 3 minutes. This is the board's own OI read turning to the opposite trend.
4. **FOLD, the reason is gone** (buyers only): **no "pays" fact at any finished
   minute in the last 15 minutes of the trade**, with the clock starting at
   entry. Nobody is being forced, nobody is pressing her way, and a long
   option is bleeding time. This is the rule for failure (b) and for the
   re-entry chop. Writers are exempt, because a writer is paid by time when
   nothing happens.
5. **WATCH**: any single against-fact short of FOLD. That means an R-fold with
   no confirmation, Q against, R against, or CVD and FLOW both against.
   **WATCH is not an exit.** It names the one thing to watch and what would
   turn it into FOLD. It is silent.
6. **HOLD**: everything else. If the premium is worse than her entry, or the
   last 1-minute premium candle went against her, the verdict reads **HOLD ·
   NOISE** and names the facts that did not change: "premium −9 % from entry,
   and this is noise: PE 73,700 still giving back and CE 74,000 still writing".

A buyer also always sees **"paid last at HH:MM (n min ago)"**. The countdown to
rule 4 is visible, so the reason-gone FOLD never arrives as a surprise.

## 6. Order flow's place, stated plainly

Order flow (CVD, FLOW) **confirms** a structural break (rule 3A) and **keeps a
buyer's trade alive** (rule 4). **On its own it can reach WATCH, never FOLD.**
The reason is that a counter-push of 5 to 10 minutes inside a trend is exactly
what a red candle looks like on the tape. If flow alone could fold a trade,
the window would reproduce failure (a) with better data. Positioning (OI) is
the point in this market (her thesis, `india-options-market-structure`).

## 7. What the window must never do

- It never places, modifies or sizes an order, and never names a target price
  or a stop price. It names the **facts** and the **wall** ahead.
- It never shows a hit rate, a probability or a confidence. The only numbers
  are facts, and "n for / n against" is a count.
- It never colours P&L red or green. P&L is shown in neutral ink. A red number
  is the panic trigger this window exists to remove.
- It never reads the engine's headline.

## 8. What must be pre-registered before this shows a verdict live

Following the §1d pattern: the rule, the fixed parameters, the predictions and
a falsifier, all committed before any live row.

**The rule:** sections 2 to 5 as written here.

**Parameters (fixed, never grid-searched):** everything §1d and `grounds`
already fix. There are three new numbers, all reused from the house:

- `PERSIST = 3` min for against-state facts (§1d's `STALE_MIN`);
- `RECENT = 15` min for fold recency (grounds' `W` × 5 min, §1d's slope);
- `REASON_GONE = 15` min without a pays fact (the same window).

**Predictions:**

1. Minutes stamped **HOLD · NOISE** are followed, over the next 30 min, by a
   larger favourable premium excursion than minutes stamped **FOLD**.
2. **FOLD** fires on a minority of trades within 5 min of entry. If it fires
   on most trades that early, it is a panic machine.
3. On a trending day, a trade entered with the trend gets its first FOLD late
   in the leg, near the other side's first fold. On a pinned day, buyers get
   **REASON GONE** within 15 to 20 min of entry.

**Falsifier:**

- Over ≥ 15 forward FOLD stamps and ≥ 15 HOLD · NOISE stamps (under 15 is
  inconclusive, house rule §5e), the 30-min favourable excursion after HOLD ·
  NOISE is **not** larger than after FOLD; **or**
- FOLD fires within 5 min of entry on more than half of all trades; **or**
- the result collapses once the single best day is removed (§5 lesson 2).

If it is falsified, it dies. It is not tuned.

**Logging:** every minute's verdict, with its facts, is written forward for
every trade she marks. The log is never edited. Just as in §1d, the window
suppresses nothing: she can always act against it, and that disagreement is
the evidence.

## 9. Changes after seeing data

**Correction, 2026-09-25 00:49 IST (read from the system clock).** The clock times I first
wrote on 9.1 to 9.6 ("00:05", "00:20", "00:55", "02:30") were estimates, not readings, and
the later ones were wrong: the files show the whole of 9.1 to 9.6 was written before
00:29. They are replaced below with what can be stated. The ORDER each entry claims
(before the replay, before the rule ran, after the replay, during the cross-review) is
unchanged and is what the session record shows. From here on every timestamp is read
from the clock.

(If a rule changes after a replay, the old text stays above, and the change is
added here with its date, its reason, and what it was seen on.)

**9.1 — written after 23:45 and before the first replay (the clock time was not recorded), a clarification made BEFORE any replay was run
(no fact, state or verdict had been computed yet).** Rule 5.2 (PATA NAHI)
gains one more blind case. **Before the grid holds 15 one-minute marks, the OI
facts are "forming", and the window says "could not check: the build → stall →
unwind sequence needs 15 one-minute marks, n so far".** This is the house's
own rule, not a new number: `board.headline` already says "Fronts forming"
below `fronts.SLOPE_MARKS`, and `fronts.folds` stamps nothing before it. It is
written here because her 2026-09-23 09:18 entry falls inside that stretch, and
the window must not pretend a 3-minute slope is a read. It came from reading
the trade list (the entry times), not from any outcome.

**9.2 — written after 9.1 and before the rule was first run (time not recorded), a clarification made BEFORE the rule was run.**
Rule 5.4's 15-minute clock counts **readable** minutes only. A minute the
window could not read (grid stale, fronts forming) is "could not check", and
"could not check" is not the same as "nothing paid". So REASON GONE needs 15
readable minutes since entry with no pays fact in them. Without this, a
09:18 entry would reach REASON GONE at 09:33 on three minutes of actual
reading. This is an interpretation of house rule 6 (a missing value is never
a zero), not a new number.

**9.3 — written after the first replay (time not recorded). A CHANGE MADE AFTER SEEING DATA. Label only; no
HOLD, WATCH or FOLD decision moves.** Seen on 2026-09-24, on a put held from
13:57. From 14:25 to 14:38, both sides' writers were leaving, so every OI
fact read flat; nothing was paying and nothing was against. The window printed
"HOLD · NOISE — nothing that holds this trade has changed: nothing against
you" while the premium fell 283 → 188. That sentence claims a reason is
standing when none is. **The new rule: the NOISE tag needs at least one "for"
fact at that minute, naming what is holding the trade. With none, the minute
reads "HOLD · nothing paying (n min)", and the REASON GONE clock stays
visible.** The verdict logic, the parameters and rule 5.4 are unchanged. The
old text of 5.6 stands above. This is a truthfulness fix to the words, not a
threshold, and it is in the report as a post-data change.

**Also found on the same data, and NOT changed; these are for her to register
or reject (REPORT.md §4).**

- (i) An R-fold on a trend day is often the ceiling **moving**, not
  vanishing. Candidate rule: an R-fold is a break only if no R-side build
  nearer to spot, in the trade's direction, is BUILDING.
- (ii) On expiry afternoons with both sides leaving, the window runs on a
  15-min CVD alone, and it lagged a 14:24 reversal by 16 min.
- (iii) For writers, "Q writers adding" produces a WATCH that does not
  threaten a writer's thesis.

None of these was applied, because each was seen on one day only.

**9.4 to 9.6 — written during the cross-review, before 00:29 on 2026-09-25 (the file's mtime) (I have now read
Fable's work). All three are PROPOSALS for her pre-registration. None is
applied.** The prototype shows each one as a labelled toggle, off by default,
and "off" is the draft exactly as written above. Each was judged on the same
four days it came from, so on these rows it carries no evidential weight.

- **9.4, a structure line (Fable's STRUCTURE, ported rule for rule from
  `docs/hold/fable/hold.js`):**
  - at entry, take the last confirmed 5-minute swing beyond the index
    (trendbox PIV = 2), or the session extreme if there is none;
  - it trails one way only;
  - a 1-minute index close beyond it, with buffer 0, is a hard FOLD, and it
    latches.
  - The line and its "points of room" are shown in the ledger.
  - Why: on 2026-09-24, both sides were unwinding on the expiry afternoon,
    so every OI fact read flat. The line broke at 14:35, 5 minutes before my
    OI FOLD at 14:40 (put from 13:57: −47.9 pts against −85.3). It is also
    the best anti-panic number either window shows.
- **9.5, moved ceiling** (candidate (i) of 9.3, in its simplest form): an
  R-fold is not a break while the nearer R front still reads BUILDING.
  - On these days it changed only 09-23 10:19 and 10:33 (FOLD at 11:37
    instead of 10:40).
  - It did **not** change the 09-24 counter-bounce folds at 10:14, 10:37 or
    13:12. So those folds are **not** explained by "the ceiling moved", and
    the hypothesis in 9.3 (i) is weaker than I thought.
- **9.6, merged:**
  - positioning alone (rules 3A or 3B) no longer folds. It needs CVD or
    prints against too, or the 9.4 line, which it implies.
  - Why: Fable's two-families-against map, with my OI read as the OI family.
  - On 09-24 it moved the 13:12 folds to 13:24, where they came as REASON
    GONE instead, right before the collapse at 13:25.
  - So the 15-minute reason-gone clock, not the OI break, is what hurts a
    trend-day consolidation. That is the finding. The fix is not proposed
    here.

**Data provenance disclosure (not a rule change).** I did not freeze the
09-24 **index** 1-minute candles on the night. After midnight Upstox served
neither `intraday` nor `historical` for that session. For SENSEX 09-24, the
trend rows (context only, never a vote) and the 9.4 line are therefore read
from Fable's frozen record (`docs/hold/fable/data.js`, Upstox REST [M]). On
NIFTY 09-22 and 09-23 their per-minute close equals mine exactly, and their
pivots equal mine 22 of 22 and 19 of 19. No draft verdict reads these
candles, and the baseline replay is byte-identical before and after. NIFTY
09-24 has no index candles: "could not check".
