# BETTER TRADE — the rules (Fable)

**Written 2026-09-25, after the HOLD/FOLD round and BEFORE this read was run
at any minute of any day.** The file's modification time is the authoritative
timestamp. Nothing below is a result.

**Contamination, declared:** through the HOLD/FOLD work I have seen the four
days' trend rows, fronts, folds and CVD at her trade minutes, and I know that
09-24 trended down and 09-23 ranged. I have **not** computed the board's
REGIME, `oi_read` or `aggression` at any minute, on any index, and no
threshold below was chosen by looking at a day. Every threshold is
`trendbox`'s, `board`'s or `grounds`'.

## 0. What she asked for, in her words

*"tell me if i have entered into the wrong trade already. second best trade
suggestion from both and which index and why … a engine trade is gonna be
good call or which side looks better whether call or put or the day like to
be selling or buying option."*

So, five answers, in plain words, all three indices, every finished minute:
**day** (buying or selling options), **side** (CE or PE), **index** (which is
cleanest), **the engine's trade** (a good call or not, grounded), and the
**second-best** trade. When she is in a trade the panel sits next to the
window and says whether her trade agrees with the read; when she is flat it
stands alone.

Advisory. No order, no size, no probability, no hit rate. A count of
agreeing facts is allowed and is labelled a count.

## 1. The facts, per index, at finished minute `t` (all existing reads)

| fact | source, unchanged | tag |
|---|---|---|
| price half of REGIME: TREND UP / TREND DOWN / CHOP / MIXED / FORMING, from the 5m · 15m · 1h rows | `trendbox.regime` | [I] |
| OI half of REGIME: PIN / TREND UP / TREND DOWN / BOTH LEAVING / NOT READ, from the **nearer** of each side's §1d top 2 | `board.oi_read` | [M] |
| REGIME: TREND UP / TREND DOWN when both halves say so; PIN / CHOP when price CHOP and OI PIN; else NOT AGREED (both halves printed); None while forming | `trendbox.regime` | [I] |
| aggression: pressing / leaning / none, with direction — CVD strong (rank ≥ 0.50) AND prints dominant the same way | `board.aggression` on `grounds.facts` | [I] |
| the nearer front per side: strike, state, build today | `fronts.read` + `board.nearer` | [M] |
| folds in the last 15 minutes, per side | `fronts.folds` | [M] |
| the engine's calls with their grounding: BACKED / THIN / CONTRADICTED / PATA NAHI and the OI · CVD · FLOW facts | `/api/calls` (the day's `data/calls` log) | [I] |
| the zone machine's setup (side, ARMED / fired, level) from the frame record, on days without a calls log | `data/frame` | [I] |
| blind: fronts forming (< 15 marks) · grid stale (> 3 min) · fewer than 4 ladder bars · rows forming | fronts / grounds / trendbox | — |

## 2. DAY — buying or selling options, per index

- **BUYING** when REGIME is TREND UP or TREND DOWN. *Why, in the window's
  words:* "one side's writers have stopped and the price rows agree — a move
  is being paid for; a bought option is paid by the move."
- **SELLING** when REGIME is PIN / CHOP. *Why:* "both sides are writing and
  the rows read range — the writers are being paid by time."
- **UNDECIDED** when REGIME is NOT AGREED. Both halves are printed: "price
  says CHOP, OI says TREND DOWN". No side is named.
- **FORMING** / **could not check** while a middle row is forming or OI is
  blind, with the reason.

The word is a per-minute read and it is shown with "since HH:MM" — how long
it has stood. There is no smoothing (a smoothing window would be a tunable).

## 3. SIDE — CE or PE, per index

**On a BUYING day:** the trend's side — UP → CE, DOWN → PE. Four confirming
facts are counted, each named:
1. the payers' nearer front (CE writers for up, PE writers for down) is
   UNWINDING, or a payers'-side fold is live (≤ 15 min) [M];
2. the holders' nearer front is BUILDING [M];
3. aggression is with the direction (pressing or leaning) [I];
4. all three rows 5m · 15m · 1h read the direction [I].
Printed as "PE · 3 of 4 facts agree" with the four listed as ● / ○ / ?.

**On a SELLING day:** the side to write is the one whose nearer front is
BUILDING **and** toward which price is not moving over the last 15 minutes
(grounds' `dpx` sign: up is toward the CE strike, down is toward the PE
strike). If both sides qualify, the one with the larger build today (change
since the open) [M]. If neither, **"no side — stand aside"** with the reason
(both leaving, or price pressing toward the only side that is writing).
Three confirming facts are counted: both nearer fronts BUILDING [M]; no
aggression either way [I]; at least two of the three rows RANGE [I].

**UNDECIDED / FORMING:** no side. The panel says what would decide it ("a
PIN from OI, or the 15m row turning").

## 4. INDEX — which is cleanest, across NIFTY · BANKNIFTY · SENSEX

Rank, in this order: (1) a decided DAY (BUYING or SELLING) over UNDECIDED,
over FORMING / blind; (2) the count of confirming facts (§3); (3) fewer blind
reads; (4) the index she is in, if any; (5) name order. The panel prints all
three rows: `NIFTY · BUYING PE · 3 of 4 · 0 blind`, etc. **Best** is rank 1;
**second-best** is rank 2 — a different index by construction. If only one
index is decided, "second: checked, none — the other two read UNDECIDED /
forming". Ranking is by counts of facts, never by a score.

## 5. THE ENGINE'S TRADE — a good call or not

- With a calls log (from 09-24): the latest `/api/calls` row for that index
  at or before `t`, the verdict-source call first: its text, its status —
  **BACKED** ("a good call: OI and flow agree, nothing contradicts"), **THIN**
  ("one family for, none against"), **CONTRADICTED** ("the tape says the
  opposite: <fact>"), **PATA NAHI** — and its three facts.
- Without one: the zone machine's setup from the frame record when ARMED or
  fired — a BUY arm at d2 / d3 is grounded as "the down move to <level> is
  done" (grounds' *exhaust* kind, direction down), a SELL arm as the mirror —
  through `grounds.ground` on the same facts, so the status words are the
  same. No setup → "checked, none — nothing armed". No frame record → "could
  not check — no frame record for <index> on <day>".
- The engine's own headline words are shown here only **with** their status;
  the HOLD/FOLD window keeps not showing them.

## 6. WRONG TRADE — when she is in one

Her trade (index, side, role) is held against the read on three points:
- **day**: buyer on a BUYING day ✓, writer on a SELLING day ✓, the reverse ✗,
  UNDECIDED ?;
- **side**: her side equals the read's side ✓, the other ✗, no side ?;
- **index**: hers is rank 1 ✓, rank 2 "second", rank 3 ✗.

Printed: "your trade agrees with n of 3 — day ✓ side ✗ index second". With
n ≤ 1 the first line reads **"WRONG TRADE for today's read — the read says
<index> <side> <buy/sell>"**, and the second-best follows. With UNDECIDED on
the day: "no read yet — the day has not decided; your trade is neither
confirmed nor refused". This is a comparison of words, not a verdict on her
P&L, and it never tells her to exit — that is the HOLD/FOLD window's job.

## 7. Absence

"checked, none" (no fold in 15 min; nothing armed) · "could not check — why"
(fronts forming; grid stale; fewer than 4 ladder bars; no calls log before
09-24; no frame record; no chain record for 09-21) · "not showing you — why"
(BANKNIFTY option premiums are not in this record, so BANKNIFTY reads on its
index and chain only; the engine's headline is not repeated outside §5).

## 8. Predictions, committed now

- P1. On 09-24 (trend day) SENSEX and NIFTY read **BUYING · PE** for most
  minutes after the first hour; on 09-23 (range day) they read **SELLING** or
  **UNDECIDED** for most minutes. If the two days read alike, the DAY read is
  noise.
- P2. Her 09-23 call entries read "wrong trade" or "no read yet" on most of
  the six; her 09-24 put entries read "agrees 3 of 3" or "2 of 3" on most of
  the thirteen.
- P3. UNDECIDED will be the most common word on at least one index each day
  — NOT AGREED is the board's most frequent regime — and the panel will be
  honest about that rather than forcing a side.
- P4. The engine's calls on 09-24 read CONTRADICTED or THIN at most of her
  entries (already known from the grounding); the panel will not call them
  good.

**Falsifier (before any forward row):** over 30 forward sessions, (i) the
median index range on days read BUYING at 10:30 must exceed the median on
days read SELLING at 10:30 — as two distributions, not a rate; (ii) on
BUYING days the named side's ATM option must have a larger favourable
excursion from 10:30 to the close than the other side's, as distributions;
(iii) the rank-1 index's named trade must not do worse than the rank-3
index's, as distributions; (iv) the result must survive removing the single
best day. Any one failing kills the read; it is not tuned.

**Hazards:** the DAY word can flip minute to minute (no smoothing, on
purpose); the engine's calls read CONTRADICTED often, so "good call" will be
rare; BANKNIFTY has no premium in this record; SENSEX prints are blind for
long stretches so its aggression read is mostly CVD alone (and says so).

## 9. Parameters, fixed here

None new. trendbox (rows, N = 20, regime), board (`oi_read`, `nearer`,
`aggression`), grounds (W = 3, STRONG 0.50, dominance ≥ 2 and ≥ 2×), fronts
(§1d, fold size 0.15, 15-minute recency, `STALE_MIN` 3, `SLOPE_MARKS` 15).
The counts "n of 4" / "n of 3" and the ranking order are this file's only
choices.

## 10. Changes after seeing data

**2026-09-25, after the replay (BETTER-REPORT.md).** Nothing above was
edited. No rule was changed and no parameter moved. The registered read
stays as written and is the panel's default.

**The result, stated first.** The DAY read as registered (§2: the board's
REGIME word) is honest and nearly mute: UNDECIDED on 328–355 of 375 minutes on
every index-day, BUYING on 26 minutes of SENSEX 09-24 and 31 of NIFTY 09-24,
SELLING on 32 minutes of NIFTY 09-23. At her 31 entries it said "no read yet"
or "could not check" 26 times. **P1 fails as written** — the trend day and the
range day read alike, both UNDECIDED — because the board's REGIME needs the
price half (5m, 15m and 1h all one way) AND the OI half (one nearer front
writing, the other not) to agree, and on a real trend day the winning side's
writers are cashing in, so the OI half reads BOTH LEAVING. P3 held
(UNDECIDED is the commonest word everywhere). P4 held (THIN ×8, CONTRADICTED
×5, BACKED ×0 at her 09-24 entries). P2 could not be tested by the registered
read because it did not speak.

**B. Proposed, shown as a labelled variant toggle ("variant B"), NOT
registered.** The DAY word comes from the **price half alone**: 5m · 15m · 1h
all one way = BUYING; CHOP (two of three RANGE) = SELLING; MIXED =
UNDECIDED; forming = could not check. The OI half is not dropped — it becomes
one of the **counted** facts in §3 ("OI half PIN / TREND … — n of 5" for a
buy, "n of 4" for a sell), so a BUYING word with the OI half against reads
"2 of 5". *Why:* it is the same two halves, with the gate turned into a
count, which is what the house does elsewhere ("n of 5 agree, a count, not
odds"). *What it did, stated so it is not tuned further:* SENSEX 09-24 read
BUYING · PE on 172 minutes and 09-23 read SELLING on 168 and BUYING · CE on
74 (the 11:00–12:30 rally); NIFTY 09-23 read SELLING on 214 minutes, 09-24
BUYING · PE on 121. At her 13 SENSEX put entries on 09-24 it read "agrees"
11 times and UNDECIDED twice (09:41, 13:25); at her six 09-23 call entries it
read WRONG TRADE three times (09:46, 09:59, 10:18), UNDECIDED twice, could
not check once. It also read WRONG TRADE at 09-22 13:47 — her best trade
(+₹1,410) — because the rows read CHOP and no side was writable; and
"agrees" at 09-24 14:22, two minutes before the low. Those are its costs.
**Not applied** to the registered read: it was chosen after seeing the days.
Hers to register or reject; the toggle shows both readings on every minute.

**C. Wording only, applied.** When the read names no trade ("checked, none")
the WRONG line said "the read says checked, none". It now says "a buyer on a
SELLING read; the read names no side yet (why)". No verdict moved.

**D. Recorded.** "SELLING · no side" is most of the variant's SELLING minutes
(NIFTY 09-23: 162 of 214): the write-side rule (§3) needs both nearer fronts
BUILDING and price not pressing toward the chosen strike, and on these days
that was rarely true. The panel says "stand aside" and why. Whether a
writer's day needs a softer side rule is hers to say; nothing here was moved.
