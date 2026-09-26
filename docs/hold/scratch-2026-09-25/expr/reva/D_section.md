## D. DISCLOSURE (rev a) — written 2026-09-26 01:40 IST by the clock, after rev a's fingerprinted run

**In-sample hindsight** on four frozen days and one live day. These are counts and rows, never a rate. **None of it counts
toward §E**, and no word is scored against an outcome on the grid. Every figure here is a construction property, or one of
her own entries' rows.

### D.0 Method, fingerprints, limits, and one incident

**Fingerprints** (`sha256sum` of this file):
- rev 0 `eca1afe0…2b6c` (00:21);
- rev 0a `5ddc16d1…a654` (00:33);
- **rev a** `79d7daa68fd9cc5bc3bd56396fafe184f65e7c7e99d13ca033bb061b5db1162d` (01:28, `rules_reva_before_run.md`);
- after the two smoke-test fixes (§G 01:31), **rev a as run**
  `cd210306eba4f668856f91985fd1071074c5b7a2ee7247f8f9e7391b36dfddf5` (01:32, `rules_reva_asrun.md`);
- the draft as the review read it, `d7c4a4de…4015`, kept as `draft_as_reviewed_d7c4a4de.md`.

**Scratch** (the session scratchpad `expr/`):
- `expr_a.py` implements rev a once, reusing rev 0a's helpers in `expr.py`;
- `run_a.py` does the run.

Its outputs are in `expr/reva/`:
- `stability.json` and `silence_detail.json` (both cadences, per index-day);
- `facts_3m.json`;
- `entries.json` and `tables_a.md`;
- `seller_0924.json`;
- `grid.json` and `grid_sell_hold.json`.

`expr/rev0a/silence_detail.json` is rev 0a's own detail, regenerated from its code.

**The incident** (it also answers review M5c):
- **What happened:** `expr.py` changes its working directory into the repo (`os.chdir`). So two outputs written from inline
  scratch scripts with relative paths landed in the repo root:
  - `tapemap/silence_detail.json` (00:40), which is rev 0a's `silence_detail.json` that the review found "missing";
  - `tapemap/rev0a/silence_detail.json` (01:37).
- **When and how it was fixed:** both were found at 01:38 by `git status` and moved into `expr/rev0a/`. The first is now
  `silence_detail_0040_from_the_inline_run.json`, and it matches rev 0a's §D.1 exactly.
- **What else was touched:** no other repo file. `data/` was never opened. The server was not touched, and nothing was
  POSTed.

**The inputs** are as rev 0a's §D.0:
- the frozen facts;
- the 09-24 frozen OI grids, ranked by the open plus the running high [I];
- **nearer-only fronts on 09-22 and 09-23** [I];
- Black-76 greeks [I], not the broker's;
- [I] candles on NIFTY and BANKNIFTY 09-24;
- 09-21 not frozen;
- 09-25 without premiums.

**S of "her option's expiry":** on every frozen day, the fixture's chain was the expiry of the options it priced. So the
straddle read is that expiry's.

### D.1 Words and silence at the registered cadence, the 3-minute close

There are 125 closes per index-day and direction, 2,250 in all.

| index-day | dir | BUY (count · by refusal) | SELL (count · by refusal) | EITHER | STAND ASIDE (both · led) | changes · direct BUY↔SELL | median run | BUY/SELL named by one fact |
|---|---|---|---|---|---|---|---|---|
| NIFTY 09-22 (0DTE) | UP | 31 (9 · 22) | 42 (42 · 0) | 4 | 48 (31 · 17) | 34 · 6 | 6 min | 37 of 73 |
| | DOWN | 27 (17 · 10) | 46 (46 · 0) | 27 | 25 (20 · 5) | 34 · 5 | 6 min | 33 of 73 |
| SENSEX 09-22 | UP | 42 (16 · 26) | 44 (43 · 1) | 11 | 28 (16 · 12) | 51 · 19 | 6 min | 41 of 86 |
| | DOWN | 42 (19 · 23) | 45 (45 · 0) | 10 | 28 (16 · 12) | 35 · 10 | 6 min | 41 of 87 |
| BANKNIFTY 09-22 | UP | 42 (8 · 34) | 13 (13 · 0) | 3 | 67 (47 · 20) | 31 · 8 | 6 min | 23 of 55 |
| | DOWN | 44 (10 · 34) | 47 (46 · 1) | 4 | 30 (16 · 14) | 34 · 8 | 3 min | 34 of 91 |
| NIFTY 09-23 (range) | UP | 43 (38 · 5) | 36 (36 · 0) | 25 | 21 (3 · 18) | 62 · 25 | 3 min | 46 of 79 |
| | DOWN | 46 (5 · 41) | 19 (19 · 0) | 12 | 48 (26 · 22) | 46 · 8 | 3 min | 18 of 65 |
| SENSEX 09-23 | UP | 32 (30 · 2) | 53 (53 · 0) | 23 | 17 (1 · 16) | 47 · 16 | 6 min | 50 of 85 |
| | DOWN | 30 (10 · 20) | 39 (39 · 0) | 16 | 40 (16 · 24) | 45 · 2 | 3 min | 29 of 69 |
| BANKNIFTY 09-23 | UP | 40 (35 · 5) | 40 (40 · 0) | 15 | 30 (17 · 13) | 53 · 14 | 4.5 min | 42 of 80 |
| | DOWN | 52 (5 · 47) | 18 (17 · 1) | 10 | 45 (27 · 18) | 33 · 6 | 6 min | 19 of 70 |
| NIFTY 09-24 (trend down) [I candles] | UP | 29 (23 · 6) | 10 (10 · 0) | 20 | 66 (62 · 4) | 36 · 2 | 6 min | 20 of 39 |
| | DOWN | 74 (71 · 3) | 23 (23 · 0) | 19 | 9 (3 · 6) | 44 · 12 | 6 min | 55 of 97 |
| SENSEX 09-24 (0DTE, trend down) | UP | 52 (14 · 38) | 8 (8 · 0) | 30 | 35 (26 · 9) | 42 · 2 | 3 min | 22 of 60 |
| | DOWN | 69 (68 · 1) | 27 (26 · 1) | 13 | 16 (6 · 10) | 47 · 15 | 6 min | 57 of 96 |
| BANKNIFTY 09-24 [I candles] | UP | 52 (24 · 28) | 34 (34 · 0) | 15 | 24 (19 · 5) | 38 · 11 | 6 min | 44 of 86 |
| | DOWN | 62 (53 · 9) | 36 (36 · 0) | 18 | 9 (8 · 1) | 40 · 16 | 6 min | 60 of 98 |
| **total, of 2,250** | | **809 (455 · 354)** | **580 (576 · 4)** | **275** | **586 (360 · 226)** | **752 · 185** | 6 min | **671 of 1,389** |

**Silence at the 3-minute close: 586 of 2,250 closes, all STAND ASIDE.**
- 360 of those are both legs refused. In all of them the long leg's entry check folds, so they gather on the counter-trend
  direction.
- None is "could not check": the 30 minutes with no index candle all fell between closes.

**Every minute, for comparison** (6,750 reads):
- BUY 2,395 (1,366 on the count · 1,029 by refusal);
- SELL 1,794 (1,779 · 15);
- EITHER 774;
- STAND ASIDE 1,757 (1,069 both · 688 led);
- could not check 30.
- **Silent on 1,787.**

**Refusal-named words are not rare.** 354 of the 809 BUYs at the close were named because SELL was refused. They are kept
apart everywhere (§A.4, §E.2).

### D.2 Stability under both cadences (review M3)

| | read every minute | **read at the 3-minute close (registered)** |
|---|---|---|
| reads | 6,750 | 2,250 |
| word changes, of transitions | 1,398 of 6,732 | **752 of 2,232** |
| changes per index, per direction, per session | about 78 | **about 42** |
| median life of a word | 2 minutes | **6 minutes** (two bars) |
| runs that last a single read | 530 of 1,416 | **355 of 770** |
| direct BUY ↔ SELL flips | 369 | **185** |
| BUY / SELL words named by one fact | 2,077 of 4,189 | **671 of 1,389** |
| of those, on the count | 1,767 of 3,145 | **569 of 1,031** |

The review's count for rev 0a, every minute, was: 1,340 changes, median 2 minutes, 498 of 1,358 runs of one minute, 365
direct flips, and 2,077 of 4,198 BUY/SELL minutes by one fact.

**Plainly.** The 3-minute close halves the changes per session and triples the median life of the word. **It does not make the
word stable.**
- It still changes at about one close in three (752 of 2,232).
- Nearly half its runs last a single bar (355 of 770).
- 185 of its changes are a **direct BUY ↔ SELL flip**, about one bar transition in twelve.
- About half its BUY / SELL words stand on a single fact (671 of 1,389).

At the 3-minute close the word is still close to a coin flip at its margin. That is why the since-clock and the count are
printed, and it is §H.2's open item.

### D.3 Facts, refusals, co-occurrence and the sell strike, at the 2,250 closes

| fact | FOR BUY | FOR SELL | NEITHER |
|---|---|---|---|
| SPEED | 1,008 | — | 1,242 |
| ROOM (with S1's noise step) | 1,138 | 707 | 405 |
| SHIELD | — | 537 | 1,713 |
| REGIME | 567 | 1,116 | 567 |
| PREMIUM | 766 | 1,316 | 168 |

**Refusals, per close** (a close can carry several):

| refusal | closes |
|---|---|
| R1 | 355 |
| R2 | 311 |
| R3 | 98 |
| R4, both legs rose | 24 |
| **R4, could not check** | **138** |
| R5 | 372 |
| R6 | 440 (over-fired on 09-22 and 09-23: nearer-only fronts) |

**Co-occurrence** (review S5). The facts co-vote by regime, so the count is not independent evidence:

| pair (both votes) | together | if independent |
|---|---|---|
| SHIELD SELL · ROOM SELL (a pin) | 294 | 169 |
| SPEED BUY · REGIME BUY (a trend) | 331 | 254 |
| REGIME BUY · PREMIUM BUY | 217 | 193 |
| REGIME SELL · PREMIUM SELL | 686 | 653 |
| SPEED BUY · ROOM BUY | 470 | 510 |

**Where the sale was placed (Q3)**, at the 580 SELL words:

| placement | SELL words |
|---|---|
| at the wall | 478 |
| at K₀, because the wall sat at the money on the in-the-money side | 83 |
| at K₀, because the wall lay beyond one straddle | 19 |

The wall's distance in straddles at SELL words had quartiles of 0.09 / 0.19 / 0.34. The far case is rare, and it happened on
the expiry afternoon.

### D.4 At her 29 entries, the word on the screen at her entry (the last 3-minute close at or before her read minute)

Facts are marked B = FOR BUY, S = FOR SELL, · = NEITHER, in the order SPEED · ROOM · SHIELD · REGIME · PREMIUM. "Four facts" is the
same count with fact 5 dropped (review S7; shown, not used).

@@T1@@

**The words at her 29 entries:**

| word | entries |
|---|---|
| BUY | 16 |
| SELL | 7 |
| EITHER | 2 |
| STAND ASIDE | 3 |
| could not check | 1 |

**Silent at 4 of 29.**
- **Every BUY and SELL at her entries was named on the count;** none was named by refusal.
- **The 3-minute close changed four entries** against the every-minute read:
  - #3: EITHER → SELL CE;
  - #5 and #6: SELL CE → BUY PE, because the 10:41 close stands until 10:44. So the 10:41 / 10:42 flip rev 0a showed at her
    entries is gone;
  - #29: SELL CE → EITHER.
- **Against rev 0a:** the same four. No entry word moved by S1, R4 or Q3 alone.

**What each leg did afterwards, in R-multiples on their shared line** (M1). Each leg's P&L over the next 30 finished minutes,
from her read minute, is divided by its PLAN §2.1 premium at risk to L at that minute, on [I] greeks. G = the long R − the
short R. Then comes the sold leg under the window, and the writer's word (§B) on it. The folds are in seller points at the
fold.

@@T2@@

**In rows, not rates:**
- **When her direction was right** (the move went "with", 18 scored entries), the buy leg's R was the higher at 11, the lower
  at 5, and equal at 2 (#14, #28).
  - The five lower: #2, #5, #6, #12, #17 (G −0.35 / −0.28 / −0.11 / −0.04 / −0.06).
  - Her 09-24 afternoon puts: #22–#24 carried G +4.11 / +1.34 / +1.07, and #25–#28 carried G +0.5 to 0.0.
- **When it was wrong** ("against", 9 scored), the sell leg's R was the higher at 7 (#7, #10, #11, #18, #20, #21, #29).
  - At #8 the line sat 9.8 pts away. Both legs lost many R (−4.76 and −9.3), and the buy leg lost less.
  - At #16 (a 3.3-pt move) both made a little.
- **The 09-24 afternoon K₀ sales** (#26–#29, the wall beyond one straddle):
  - #27 and #28 (CE 73,700) were folded by rule 3s at 14:02, and #29 at 14:35, all before rev 5 B's 14:38 line fold. CE 73,700
    ended at 0.15.
  - #26 (CE 73,800) folded at 14:38 by rule 3.
- **The writer's word on the 27 sell legs** (#9 had no sale):
  - "line beyond strike" is flagged at 17 (§B.1). Near-ATM sales put the line beyond the strike.
  - At 30 minutes: target 2 (#8, #22), stop 1 (#10), neither 24.
  - To 15:29, shown: target 14, stop 3.

### D.5 Her 09-25 NIFTY entries (rev a)

The facts at the 3-minute close before each entry (09:33, 11:59 and 12:02) are **not in the frozen record**. The words below
are read at the read minute, from the same pieces rev 0a used [I proxy]. No 09-25 premium was frozen, so fact 5 cannot read,
and **R4 refuses SELL at all three**.
- That R4 is the frozen record's gap, not the market's. Live, fact 5 would read.

| entry (read) | dir | the word (rev a) | b–s | facts | what moved against rev 0a |
|---|---|---|---|---|---|
| 09:36 PE (her words; the saved 09:35 check) | DOWN | **STAND ASIDE · led:** "the facts favour selling, 3 to 0, but selling is refused: R4 — could not check: no premium frozen" | 0–3 | · S S S ? | M4: SELL CE → STAND ASIDE. This goes against the one in-sample row it touches: the index never came within 95 pts of CE 23,200. |
| 12:01:21 CE (marked) | UP | **BUY CE · selling refused (R4)** | 1–1 | B · · S ? | S1: ROOM went FOR BUY → NEITHER (the line 1.65 pts away, inside one candle of 4.9). M4 then names BUY by refusal at a tie. |
| 12:05:28 PE (marked) | DOWN | **BUY PE · selling refused (R4)** | 2–1 | B B · S ? | The word is unchanged; it is now named by refusal. |

### D.6 The seller on 09-24 under rev a's §C: signed R, rule 3s, both answers to §C.7

These are her 13 put entries read as sales of the call at the same strike (the handoff's replay).
- **At 14:38** the ATM straddle was 321.6 pts [M] and the index closed 73,764.02. Every sold call was out of the money, so
  signed R equals the old unsigned R.

| sold call (entries) | at entry | rev 5 B (as built) | **§C, YES** | **§C, NO** | at 15:29 |
|---|---|---|---|---|---|
| 74,200 (09:41, 10:18) | 174.7 · 138.6 | 10:43 rule 4, at 138.2 | the same | the same | 0.15 |
| 74,100 (12:31) | 138.0 | 14:38 rule 3, at 47.55 | **held at 14:38** (R +336 > S 321.6). **P_max 53.25 while held**, then 14:45 rule 4 at 42.45 | 14:38 rule 3, at 47.55 | 0.15 |
| **74,000 (12:34, 12:43)** | 171.7 · 178.1 | 14:38 rule 3, at 67.75 | **13:05 rule 3s, at 191.65**: the 13:03–13:05 bar closed 25.4 pts through 74,000 | **the same 3s fold** | 0.2 |
| 74,000 (13:25) | 157.05 | 14:38 rule 3, at 67.75 | the same (R 236 ≤ 321.6) | the same | 0.2 |
| 73,900 (13:40, 13:42, 13:43) | 157.65 · 154.25 · 140.4 | 14:38 rule 3, at 95.9 | the same (R 136) | the same | 0.1 |
| 73,800 (13:44, 13:53, 13:56, 14:22) | 176.0 · 145.05 · 127.65 · 107.45 | 14:38 rule 3, at 133.1 | the same (R 36) | the same | 0.1 |

**The result, stated against itself:**
- **The reach still does not rescue 09-24.** Under YES it holds one sale (74,100) for seven minutes, and its premium rose to
  53.25 above the break's 47.55 before rule 4 folded it at 42.45. Under NO it folds at 14:38 as today.
- **Rule 3s costs on the record.** It folds the two 74,000 sales at 13:05 at 191.65, where rev 5 held them to 14:38 at
  67.75, and both expired at 0.2. The fold came on a 25-pt close through the strike, which is the kind of one-candle poke rev
  5 B's buffer exists to ignore.
- **3s at every close is a zero-buffer stop at the strike.** On the grid and at her entries it also folds at-the-money sales
  on the first close past the strike (§D.7). This is disclosed, not tuned. Its scope is §H.3.

### D.7 The grid: scorability (M1), the writer population (M6), held breaks (M9) and 3s

- **Units:** 216 (nine index-days × two directions × twelve closes from 09:44).
  - **Words at the units:** SELL 55 · BUY 41 on the count and 36 by refusal · EITHER 35 · STAND ASIDE 49 (35 both · 14 led).
- **G (R-multiples) scored at 160 of 216.** Not scored: no sell strike 44, no premium 6, no greeks 6.
- **The writer population (ii),** at the 165 units with a sell strike:
  - **words:** GO 60 · WAIT 81 · NO 24; in the stratum 133;
  - **at 30 minutes:** target 24 · stop 33 · neither 82 · not scored 26;
  - **to 15:29 (shown):** target 49 · stop 48 · neither 42 · not scored 26.
  - **That is 57 resolved at 30 minutes over three sessions,** about 19 a session. P1-W's 15 GO and 15 WAIT inside the stratum
    are within reach in 10–30 sessions, which rev 0's her-presses-only population never was.
- **The window on those 165 sold legs (§C, YES)**, the first FOLD:

  | first FOLD | legs |
  |---|---|
  | rule 3 | 64 |
  | rule 6 | 48 |
  | rule 4 | 27 |
  | **rule 3s** | **13** |
  | none by 15:29 | 13 |

- **Rule 3s on the grid** fired at 13 legs. It fired before rev 5 B's fold at 8, and at the same minute at 5.
  - Of the 8, the premium at the 3s fold was lower than at rev 5's fold at 7 and higher at 1.
  - One SENSEX 09-24 ATM call (73,700) folded at 14:35 by 3s and expired at 0.15.
- **Held breaks, W-R's unit, keyed (index, bar, L, side):** two distinct on the grid, both SENSEX 09-24.
  - **14:38 CE:** the 74,200 and 74,300 legs, and the handoff's 74,100. Every leg folded at 14:45 by rule 4. P_b → P_x (P_max)
    per strike:
    - 74,100: 47.55 → 42.45 (53.25);
    - 74,200: 33.3 → 28.9 (37.05);
    - 74,300: 23.5 → 19.9 (26.4).
  - **15:29 PE 73,500:** held at the last close (R 80.5 > S 20.05), and it ended at 0.15.
  - **None counts toward W-R.**
