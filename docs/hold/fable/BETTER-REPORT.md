# BETTER TRADE — the report (Fable)

Written 2026-09-25, after the replay. `BETTER-RULES.md` was written first and
is unchanged above its §10. Data: `data.js` (rebuilt for all three indices ×
09-21 → 09-24; 12 index-days, 21.8 MB), engine `better.js`, replay
`scratch/better_report.js` → `scratch/better_out.txt` (registered) and
`scratch/better_out_variant.txt` (variant B). The panel is in `index.html`,
left of the HOLD/FOLD window, with a **flat** toggle (no trade to compare) and
a **variant B** toggle (post-data, unregistered, off by default).

**Provenance of the index candles**, because REST served no 09-24 candles
after midnight: SENSEX 09-24 re-read from the record frozen from REST the
same night [M]; NIFTY and BANKNIFTY 09-24 reconstructed from the chain's
per-minute spot [I] (highs and lows are closes, so their trend rows are
weaker on that day); every other index-day from REST [M]. The footer of the
panel prints this for the day it is reading.

## 1. The read, in ten lines

1. Every finished minute, per index, from the board's own reads: REGIME
   (`trendbox.regime` on the 5m · 15m · 1h rows and `board.oi_read` on the
   nearer §1d fronts), `board.aggression`, the nearer fronts, folds, the
   calls log, the zone setup.
2. **DAY** — BUYING when REGIME is TREND UP/DOWN ("one side's writers have
   stopped and the price rows agree — a move is being paid for"); SELLING
   when PIN / CHOP ("both sides writing, the rows read range — the writers
   are paid by time"); UNDECIDED when NOT AGREED, both halves printed; shown
   with "since HH:MM".
3. **SIDE** — on a BUYING day the trend's side, with 4 counted facts (payers
   unwinding or folded, holders building, aggression with it, all three rows
   with it); on a SELLING day the side whose nearer front is BUILDING and
   toward which price is not moving, with 3 counted facts; else "no side —
   stand aside" and why.
4. **INDEX** — the three ranked: decided day first, then the count of facts,
   then fewer blind reads, then the index she is in; best = rank 1,
   second-best = rank 2, or "checked, none" with the reason.
5. **ENGINE** — the latest `/api/calls` row (09-24) with its status: BACKED
   "a good call", THIN, CONTRADICTED "the tape says the opposite" and the
   facts; before the calls log, the zone machine's armed setup grounded the
   same way; "checked, none — nothing armed" when idle.
6. **YOUR TRADE** — day ✓/✗/?, side ✓/✗/?, index ✓/second/✗; "WRONG TRADE
   for today's read — the read says …" at 0–1 of 3; "no read yet — the day
   has not decided" on UNDECIDED. Never an exit instruction; that is the
   window's job.
7. Absence in three sentences; BANKNIFTY says "not showing you — no option
   premiums in this record".
8. No probability, no size, no order; counts are labelled counts; light; no
   chart; [M]/[I] on every row.
9. It sits left of the HOLD/FOLD window when she is in a trade and stands
   alone when flat (the **flat** toggle).
10. **Variant B** (post-data, unregistered): the DAY word from the price rows
    alone with the OI half as a counted fact — see §4 and RULES §10 B.

## 2. Did the two days read differently? (the "not tuned to one day" test)

Minutes per word, 375 per index-day:

| index-day | registered read | variant B |
|---|---|---|
| SENSEX 09-23 (range) | UNDECIDED 323 · SELLING 25 · BUYING 11 · blind 16 | SELLING 168 · BUYING CE 74 · UNDECIDED 117 |
| SENSEX 09-24 (trend) | UNDECIDED 333 · **BUYING PE 26** · blind 16 | **BUYING PE 172** · UNDECIDED 187 |
| NIFTY 09-23 (range) | UNDECIDED 328 · SELLING 32 | SELLING 214 · UNDECIDED 146 |
| NIFTY 09-24 (trend) | UNDECIDED 328 · BUYING PE 31 | BUYING PE 121 · UNDECIDED 219 · SELLING 19 |
| BANKNIFTY 09-23 / 09-24 | UNDECIDED 341 / 355 | SELLING 237 / SELLING 124 + BUYING PE 19 |
| 09-22 (all three) | UNDECIDED 333–344 | SELLING 194–203 (NIFTY, SENSEX), BUYING CE 21–30 |
| 09-21 (all three) | could not check (no chain record) | same |

**The registered read does not separate the days: both are UNDECIDED nine
minutes in ten.** P1 fails as written, and RULES §10 says why (the REGIME
gate needs the winning side's writers to keep writing, and on a trend day
they cash in). Variant B separates them: SENSEX BUYING · PE 172 minutes on
the trend day against SELLING 168 on the range day; NIFTY SELLING 214 on
09-23 against BUYING · PE 121 on 09-24. Two days is a description, not a
result.

## 3. What it said at her entries

Read minute = the last finished minute before the fill. "R" = the registered
read for her index; "V" = variant B. "took" is what she took.

| entry | trade | R: day · side · your trade | V: day · side · your trade | engine (09-24 only) | took ₹ |
|---|---|---|---|---|---|
| 09-21 14:00 | N 23300CE | could not check — no chain record | same | could not check | −754 |
| 09-22 09:42 | N 23300CE | UNDECIDED · no read yet | UNDECIDED | nothing armed | −471 |
| 09-22 10:32 | N 23550PE | UNDECIDED | UNDECIDED (since 10:30) | — | +601 |
| 09-22 10:42 / 10:43 / 10:44 | N 23550PE ×3 | UNDECIDED | SELLING · CE 2 of 4 · **WRONG** (buyer, wrong side) | — | +793 / −224 / +163 |
| 09-22 10:52 | N 23500PE | UNDECIDED | SELLING · CE 2 of 4 · **WRONG** | — | −855 |
| 09-22 13:48 | N 23500PE | UNDECIDED | SELLING · no side · **WRONG** (a buyer on a SELLING read) | — | **+1,410** |
| 09-23 09:18 | N 23450CE (1) | could not check — fronts forming, 2 of 15 marks | same | — | −65 |
| 09-23 09:47 | N 23450CE (2) | SELLING · PE sell 3 of 3 · **WRONG** | SELLING · PE 4 of 4 · **WRONG** | — | −497 |
| 09-23 09:49 | N 23400PE | SELLING · PE · agrees 2 of 3 (day ✗ side ✓ index ✓) | same | — | −52 |
| 09-23 10:00 | N 23450CE (3) | SELLING · PE sell 3 of 3 · **WRONG** | **WRONG** | — | −507 |
| 09-23 10:19 | N 23450CE (4) | UNDECIDED (since 10:17) | SELLING · no side; best SENSEX PE sell · **WRONG** | — | +205 |
| 09-23 10:33 | N 23450CE (5) | UNDECIDED | UNDECIDED | — | −29 |
| 09-23 11:07 | N 23450CE (6) | UNDECIDED | UNDECIDED | — | −367 |
| 09-23 11:32 | S 74900CE | BUYING · CE 2 of 4 · agrees 3 of 3 | BUYING · CE 3 of 5 · agrees | no frame record for SENSEX | −305 |
| 09-24 09:42 | S 74200PE #1 | UNDECIDED (since 09:31) | UNDECIDED | THIN: GO | +475 |
| 09-24 10:19 | #2 | UNDECIDED | BUYING · PE 2 of 5 · agrees 3 of 3 | CONTRADICTED: WAIT — trend stalled | +456 |
| 09-24 12:32 | #3 | UNDECIDED (since 12:23) | BUYING · PE · agrees 3 of 3 | CONTRADICTED: WAIT | +546 |
| 09-24 12:35 / 12:44 | #4 / #5 | UNDECIDED | BUYING · PE · agrees 3 of 3 | CONTRADICTED: SPENT | −752 / −159 |
| 09-24 13:26 | #6 | UNDECIDED | UNDECIDED (since 13:01) | THIN: WAIT | +716 |
| 09-24 13:41 / 13:43 / 13:44 | #7–#9 | UNDECIDED; ranking put **NIFTY BUYING PE 3 of 4** first, SENSEX second | BUYING · PE · agrees 2 of 3 (index second) | THIN: GO / SPENT | +177 / +30 / +143 |
| 09-24 13:45 | #10 | UNDECIDED | BUYING · PE · agrees 3 of 3 | THIN: SPENT | +240 |
| 09-24 13:54 | #11 | UNDECIDED, NIFTY first | BUYING · PE · agrees 2 of 3 | CONTRADICTED: GO | −243 |
| 09-24 13:57 | #12 | UNDECIDED, NIFTY first | BUYING · PE · agrees 2 of 3 | THIN: GO | +592 |
| 09-24 14:23 | #13 | UNDECIDED | BUYING · PE · agrees 3 of 3 | THIN: GO | +147 |
| 09-24 11:00 (writer) | S short 74500CE | UNDECIDED | UNDECIDED | THIN: STAND ASIDE — pin/chop | — |
| 09-23 10:30 (writer) | N short 23400CE | UNDECIDED | UNDECIDED | nothing armed | — |

In rows: the registered read **spoke at 5 of 31 entries** — three times
WRONG TRADE (09-23 09:47 and 10:00, both losers), once "agrees 2 of 3" on a
put buy on a SELLING read (−52), once "agrees 3 of 3" on the SENSEX call
(−305). It was silent at all 13 SENSEX put entries on the trend day; on
09-24 afternoon its ranking named **NIFTY BUYING · PE 3 of 4** as the best
trade while SENSEX stayed UNDECIDED — the NIFTY chain read TREND DOWN on
both halves while SENSEX's calls were cashing in.

Variant B spoke at 25 of 31: "agrees" at 11 of the 13 SENSEX put entries
(the two UNDECIDED were 09:41 and 13:25); WRONG at three of the six 09-23
call entries; WRONG at four 09-22 put scalps and at her best trade.

**The engine's trade** (09-24, the only day with a calls log): THIN eight
times, CONTRADICTED five, BACKED never — the panel never called the engine's
trade good on that day, as P4 predicted from the grounding.

## 4. Where it would have misled her

**The registered read, by silence.** "No read yet — the day has not decided"
at 26 of 31 entries is not wrong, but a trader who asked "is today a buying
day" at 12:31 on 09-24, with SENSEX 74,050 and every trend row DOWN, and got
"UNDECIDED — price says TREND DOWN, OI says BOTH LEAVING" would be right to
call it useless. The OI half is doing its job (both nearer fronts were
unwinding), and the gate is too strict for the question she asked.

**The registered read, when it spoke:** 09-23 11:31 "agrees 3 of 3" on the
SENSEX call (it went 215 → 252 by 12:06, then 166 — a right read for 35
minutes); 09-23 09:48 "agrees 2 of 3" on a put buy on a SELLING day, which
is a mixed message the wording should not smooth over.

**Variant B, when it spoke wrongly:** 09-22 13:47 WRONG on her +₹1,410 put
(the rows read CHOP at 13:47; the fall came in the next 13 minutes); 09-22
10:41–10:43 WRONG on +793 and +163 scalps (and right on −224 and −855 in the
same minutes — the read did not change between them, her exits did); 09-23
10:18 WRONG on +205; 09-23 11:31 agrees on −305; 09-24 12:34 / 12:43 agrees on
−752 / −159 (the thesis was right, her exits were not — the HOLD window's
job, not this panel's); 09-24 14:22 agrees, two minutes before the low. A
SELLING-day word does not say a put buy is wrong on a 100-point drop inside a
range (09-22 10:20–10:50): the read's grain is the 15-minute row, and it
should say so.

**Both:** BANKNIFTY never decided on the registered read and read "SELLING
no side" for most of variant B's minutes — with no premiums in the record
and its 09-24 candles reconstructed from chain spot [I], its rank is the
least trustworthy of the three and the panel says so. "SELLING · no side" is
most of the variant's SELLING minutes on every index (RULES §10 D).

**What neither read can do:** call the engine's trade good — on 09-24 the
grounding contradicted or thinned every call at her entries, so "is the
engine's trade a good call" was answered "no" or "thin" thirteen times; the
answer is honest and it is not help.

## 5. What must be pre-registered before this shows live

The registered read (§2–§6 of BETTER-RULES.md) as written; or variant B, if
she chooses it, as its own registration with the same falsifier (RULES §8):
BUYING-day median index range > SELLING-day median; the named side's ATM
option out-travels the other side's on BUYING days; rank 1 does not do worse
than rank 3; the result survives removing the best day — all as
distributions, never a rate, after 30 forward sessions. The write-side rule
(§3, "SELLING · no side") is hers to keep or soften before it is registered.

## 6. Wiring, smallest first

1. **`better.py` + `GET /api/better?idx=&strike=&side=&role=&entry=`** —
   a port of `better.js` over what `/api/board` already assembles per
   finished minute for each index (`_board_core`, `trendbox.regime`,
   `board.oi_read`, `board.aggression`) plus `/api/calls`'s latest row and
   the frame's setup. One request, three indices, one row of words.
2. **Its own forward log**, `data/hold/better_<day>.jsonl`, one row per
   finished minute per index: day word, since, side, the counted facts, the
   ranking, the engine status — write-once, the falsifier's only source.
3. **The panel** as a second Document-PiP window or a second block in the
   same one, from `index.html`'s `#bt`; it reads the marked trade from the
   same `data/day_state/` record the HOLD window uses, so "wrong trade" and
   "hold/fold" are about the same trade.
4. Nothing new is measured; nothing is ordered or sized.

---

## 7. THE SIDE READ (PREREG-merged.md §10) — described on the four days, not tuned

Added 2026-09-25 after the clock read 01:22 IST, after §10 of the
registration was written and before this replay was run. Engine:
`scratch/side_report.js` (the vote and the four facts exactly as §10.1–10.2
state them; expiry from the tradebook's `expiry_date` [M] for NIFTY 09-22 and
SENSEX 09-24, BANKNIFTY 09-24 as the month's last Thursday [I]); output
`scratch/side_out.txt`, rows `scratch/side_rows.json`. The prototype's panel
still shows the round-3 read (variant B is its price-led form); wiring the
side line into the panel is the next change and was not made in this round.

**It speaks.** Minutes per word, 375 per index-day:

| index-day | CALLS | PUTS | no side | could not check |
|---|---|---|---|---|
| SENSEX 09-24 (trend down) | — | **354** | 21 | — |
| NIFTY 09-24 | — | **338** | 35 | — |
| BANKNIFTY 09-24 [I candles] | — | 205 | 168 | — |
| SENSEX 09-23 (range) | 168 | — | **207** | — |
| NIFTY 09-23 | 141 | — | **234** | — |
| BANKNIFTY 09-23 | 122 | — | 253 | — |
| NIFTY 09-22 (expiry) | 59 | 71 | 245 | — |
| SENSEX 09-22 | 61 | 78 | 236 | — |
| NIFTY 09-21 | **351** | — | 24 | — |
| SENSEX 09-21 | 302 | — | 73 | — |

The trend day reads one side nine minutes in ten; the range day reads "no
side" more than half the time with CALLS on the 10:20–11:50 rally; the
expiry day 09-22 reads "no side" two minutes in three with short CALLS and
PUTS stretches. That is S-P1's shape on two days, which is a description.

**Where it lags at the turns [M, index closes at the change minutes]:**
- SENSEX 09-24: PUTS from 09:29 (74,283) to 15:24 (73,720) with one 2-minute
  gap at 11:18. The low printed at 14:24; the read stayed PUTS for **60
  minutes** after it. The counted facts moved first: "holders CE 74,200
  leaving" is printed as *against* from 13:40 (the ceiling cashing in), which
  is the fact §10.5 says to watch.
- NIFTY 09-23: the morning low was near 10:10 (≈ 23,350); CALLS came at
  **10:19** (23,393), 9 minutes and 40 points later; the high was ≈ 23,460 at
  11:30 and the read dropped to "no side" at **11:49** (23,435), 19 minutes
  later, then flickered CALLS / no side eleven times between 12:01 and 13:09.
- SENSEX 09-23: CALLS 10:24 (74,744) → no side 11:50 (74,858); the rally ran
  on to 74,900 at 12:30 while the read flickered.
- NIFTY 09-22: the 10:20 fall (23,475 → 23,370 by 10:50): the read held CALLS
  until **10:33**, 13 minutes into the fall, then "no side" until PUTS at
  12:11 — it never named PUTS during the fall itself; the 5m row went RANGE,
  the 15m and 1h stayed UP.
- BANKNIFTY 09-21 and 09-24 flicker between a side and "no side" on
  consecutive minutes (16 changes on 09-24) when one row sits at its
  threshold. There is no smoothing, by registration; the "since" clock
  resets on each flip. Recorded as the cost of speaking every minute; not
  tuned.

**At her entries** (read minute = the last finished minute before the fill;
"agrees" for a buyer means her option's side is the read's side):

| entry | trade | side read · for / against | your side vs the read | took ₹ |
|---|---|---|---|---|
| 09-21 14:00 | N CE | CALLS · 0 / 0 (OI, flow could not check — no chain, no ladder that day) | agrees | −754 |
| 09-22 09:42 | N CE | CALLS · 1 / 1 (payers CE 23,450 adding in its way) · 0DTE | agrees | −471 |
| 09-22 10:32 | N PE | CALLS · 1 / 2 (OI TREND DOWN, holders leaving — the rows lag the 10:20 fall) | **against** | +601 |
| 09-22 10:42 · 10:43 · 10:44 · 10:52 | N PE ×4 | no side (5m 15m 1h all RANGE) | no side | +793 −224 +163 −855 |
| 09-22 13:48 | N PE | no side (5m RANGE · 15m DOWN · 1h RANGE); BANKNIFTY PUTS | no side | **+1,410** |
| 09-23 09:18 · 09:47 · 09:49 · 10:00 | N CE, CE, PE, CE | no side (all rows RANGE) | no side | −65 −497 −52 −507 |
| 09-23 10:19 | N CE | no side (5m RANGE · 15m UP · 1h RANGE) — CALLS came at 10:19, one minute after this read | no side | +205 |
| 09-23 10:33 | N CE | CALLS · 3 / 0 (OI TREND UP, payers CE 23,400 unwinding · fold 10:26, holders PE 23,400 building) | agrees | −29 |
| 09-23 11:07 | N CE | CALLS · 3 / 0 | agrees | −367 |
| 09-23 11:32 | S CE | CALLS · 2 / 0 | agrees | −305 |
| 09-24 09:42 | S PE #1 | PUTS · 1 / 1 (payers PE 74,200 adding in its way — it folded at 09:46) · 0DTE | agrees | +475 |
| 09-24 10:19 · 12:32 · 12:35 · 12:44 | #2–#5 | PUTS · 1 / 0 (payers unwinding / fold 12:27) | agrees | +456 +546 −752 −159 |
| 09-24 13:26 | #6 | PUTS · 0 / 0 (5m DOWN · 15m RANGE · 1h DOWN; both nearer fronts stalled) | agrees | +716 |
| 09-24 13:41 – 13:57 | #7–#12 | PUTS · 1 / 0 or 1 / 1 ("holders CE 74,200 leaving" against from 13:40) | agrees | +177 +30 +143 +240 −243 +592 |
| 09-24 14:23 | #13 | PUTS · 1 / 1 (holders CE 74,200 leaving) | agrees | +147 |
| 09-24 11:00 writer | S short 74500 CE | PUTS · 0 / 3 | agrees (you wrote the other side) — the call expired 0.15 | — |
| 09-23 10:30 writer | N short 23400 CE | CALLS · 3 / 0 | **against** (you wrote the read's side) — she was writing into the rally | — |

In rows: 17 entries agreed with the read, 1 was against it, 9 had no side, 2
were the writer examples. The 13 SENSEX puts on the trend day all agreed
(10 winners, 3 losers by her exits). The four other "agrees" on buys (09-21,
09-22 09:41, 09-23 10:32 and 11:06, SENSEX 11:31) all lost — three of them
were calls bought inside the last 40 minutes of a CALLS stretch that ended
at 11:49–11:50. The one "against" (09-22 10:31, a put bought 11 minutes into
the 10:20 fall while the rows still read UP) made +601. Her best trade
(09-22 13:48, +1,410) was "no side". Counts on four days; not a rate.

**Where it would mislead her, plainly:** at a turn it is on the wrong side
for 10–60 minutes (the 09-22 10:31 put, the 09-24 14:24 low, the 09-23 late
calls); it names a side for a writer when she should be reading the other
line (a PUTS side told the 09-24 call writer "agrees", correctly, and a CALLS
side told the 09-23 call writer "against", correctly — but only because the
rally was real); on a flickering minute it can say CALLS and "no side" a
minute apart; and on SENSEX the aggression fact is "could not check — too
thin to read" most of the day, so its counts are three facts, not four.
None of this is tuned out; it is what §10.5 and §11 of the registration say.
