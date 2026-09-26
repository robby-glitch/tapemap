## D. DISCLOSURE (rev b) — written 2026-09-26 01:53 IST by the clock, after rev b's fingerprinted run

**In-sample hindsight** on four frozen days and one live day. These are counts and rows, never a rate. **None of it counts
toward §E**, and no word is scored against an outcome on the grid.

**What rev b changed.** Rev b changes no fact, refusal, strike or line: those are rev a's. Only two things moved: the word's
grading, and rule 3s's buffer. So §D.3 is rev a's, unchanged, and every other table is rev b's.

### D.0 Method, fingerprints, limits, and the repo

**Fingerprints** (`sha256sum` of this file, each before its run):
- rev 0 `eca1afe0…2b6c` (00:21);
- rev 0a `5ddc16d1…a654` (00:33);
- rev a `79d7daa6…162d` (01:28);
- rev a as run `cd210306…dfddf5` (01:32);
- **rev b `d7d9ab3859c1e689591f5bd627ba63be4188b6dc755e3c8d135fd43e67c0e6cd` (01:48, `rules_revb_before_run.md`).**
- The rules text did not move after rev b's run. §D, §G's closing line and §H were written after it.

**Scratch** (the session scratchpad `expr/`):
- `expr_b.py` implements rev b once. It grades rev a's expression and adds the buffered 3s.
- `run_b.py` does the run.
- The outputs are in `expr/revb/`: `stability.json`, `silence_detail.json`, `entries.json`, `seller_0924.json`, `grid.json`,
  `tables_b.md`, `perday_b.md` and `rtable.md`.

**The repo** (rev a's incident, fixed in rev b):
- `expr.py` no longer changes its working directory.
- Every rev b script writes to absolute paths inside `expr/`.
- After the run, `git status` showed nothing new in the repo except this draft and the review.

**The inputs** are as rev a's §D.0:
- nearer-only fronts on 09-22 and 09-23 [I];
- Black-76 greeks [I];
- [I] candles on NIFTY and BANKNIFTY 09-24;
- 09-21 not frozen;
- 09-25 without premiums.

**B_k** is `hold.noise` at each sale's entry read: the same function rev 5 B's line uses, with its fallback.

### D.1 Words and silence at the 3-minute close (rev b's words)

The counts are per index-day and direction, of 125 closes.
- "count · ref" splits a word named on the count from one named because the other leg was refused.
- STAND ASIDE is split into both refused · led · tie.

@@PERDAY@@

**At the 3-minute close (2,250 reads):**

| word | closes |
|---|---|
| BUY | 293 (209 on the count · 84 by refusal) |
| LEANS BUY | 347 (246 · 101) |
| EITHER | 275 |
| LEANS SELL | 324 (323 · 1) |
| SELL | 255 (253 · 2) |
| **STAND ASIDE** | **756** (360 both refused · 226 led · 170 tie) |

**Silence at the 3-minute close: 756 of 2,250 closes.** That is up from rev a's 586.
- The 170 new STAND ASIDE · tie closes are exactly the tie with a refused leg that rev a named as the open leg.
- **Of the 1,219 directional words, 672 are LEANS.** Those are named by a single fact.
- The strong words (BUY and SELL) are 548.

**Every minute, for comparison** (6,750 reads):
- BUY 871;
- LEANS BUY 1,052;
- EITHER 774;
- LEANS SELL 1,025;
- SELL 762;
- STAND ASIDE 2,236 (1,069 · 688 · 479);
- could not check 30.

### D.2 Stability under rev b's words, both cadences

| | read every minute | **read at the 3-minute close (registered)** | rev a at the 3-minute close (four words, for comparison) |
|---|---|---|---|
| reads | 6,750 | 2,250 | 2,250 |
| word changes, of transitions | 1,936 of 6,732 | **987 of 2,232** | 752 of 2,232 |
| median life of a word | 2 minutes | **3 minutes** (one bar) | 6 minutes |
| runs that last a single read | 885 of 1,954 | **564 of 1,005** | 355 of 770 |
| **direct BUY ↔ SELL flips** (strong to strong) | 8 | **11** | 185 (all BUY ↔ SELL were "strong" then) |
| buy-side ↔ sell-side flips (any of BUY, LEANS BUY to any of SELL, LEANS SELL) | 319 | **153** | 185 |
| directional words named by one fact (now LEANS) | 2,077 of 3,954 | **672 of 1,219** | 671 of 1,389 |

**Plainly:**
- **The strength in the word makes the word change more often.** Every one-fact change of margin (3–1 to 3–2) is now a word
  change. So the median word lives one bar, and more than half the runs last a single bar.
- **What it removes is the misleading flip.** A strong BUY now almost never turns straight into a strong SELL: 11 times at
  the close, against rev a's 185. Almost every flip of side now passes through LEANS or EITHER.
- **The word is still close to a coin flip at its margin, and it now says so in its own letters.** Just over half its
  directional words are LEANS.

### D.3 Facts, refusals, co-occurrence and the sell strike — rev a's, unchanged in rev b

@@D3@@

### D.4 At her 29 entries, the word on the screen at her entry (rev b)

This is the last 3-minute close at or before her read minute.
- The lead is the named leg's count minus the other's.
- The last column is the sold leg's first FOLD, in seller points at the fold:
  - rev 5 option B as built;
  - rev a's zero-buffer rule 3s;
  - **rev b's buffered rule 3s** (§C, YES answer), with B_k.

@@T_ENT@@

**The words at her 29 entries:**

| word | entries |
|---|---|
| BUY | 7 |
| LEANS BUY | 9 |
| SELL | 3 |
| LEANS SELL | 4 |
| EITHER | 2 |
| STAND ASIDE | 3 |
| could not check | 1 |

Silent at 4 of 29. Every directional word was named on the count.
- **Rev a's words became:**
  - of rev a's 16 BUYs, 7 stay BUY and 9 become LEANS BUY;
  - of rev a's 7 SELLs, 3 stay SELL and 4 become LEANS SELL.
- **Rev b's buffer moved four sold legs:**
  - **#14:** the PE 23,400 is no longer folded at 10:35 on a close through its strike. It folds at 13:32 by rule 3, at
    +11.65 instead of −2.15.
  - **#27, #28, #29** (CE 73,700, placed at K₀) are no longer folded at 14:02 / 14:02 / 14:35. They fold at 14:38, when that
    close was more than one candle through 73,700: +11.2, −10.5 and −35.15 instead of +4.15, −17.55 and −14.7.

**The legs afterwards, in R-multiples on the shared line** (rev a's figures). The legs, strikes and line are unchanged in rev
b, so these still stand.

@@T_R@@

### D.5 Her 09-25 NIFTY entries (rev b)

These are read at the read minute [I proxy]. The 3-minute-close facts before each entry were not frozen, and no premium was
frozen, so **R4 refuses SELL at all three**. That is the frozen record's gap, not the market's.

| entry (read) | dir | the word (rev b) | lead · b–s | what moved |
|---|---|---|---|---|
| 09:36 PE (her words; the saved 09:35 check) | DOWN | **STAND ASIDE · led:** "the facts favour selling, 3 to 0, but selling is refused: R4 — could not check" | −3 · 0–3 | as rev a |
| 12:01:21 CE (marked) | UP | **STAND ASIDE · tie:** "the facts tie 1–1, and selling is refused: nothing leads to buying" | 0 · 1–1 | rev a said BUY CE · selling refused (the tie reading) |
| 12:05:28 PE (marked) | DOWN | **LEANS BUY PE · selling refused (R4)** | 1 · 2–1 | rev a said BUY PE · selling refused |

### D.6 The seller on 09-24 under rev b's buffered rule 3s (the strike-rule disclosure)

These are her 13 put entries read as sales of the call at the same strike (the handoff's replay).
- B_k is rev 5 B's candle, read at each entry: 12.21 to 39.11 pts [M].

| sold call (entries) | B_k at entry | rev 5 B (as built) | rev a (3s, no buffer) | **rev b, §C YES** | **rev b, §C NO** | at 15:29 |
|---|---|---|---|---|---|---|
| 74,200 (09:41, 10:18) | 26.37 · 22.64 | 10:43 rule 4, 138.2 | the same | the same | the same | 0.15 |
| 74,100 (12:31) | 17.45 | 14:38 rule 3, 47.55 | held, then 14:45 rule 4, 42.45 | **held 14:38 (P_max 53.25), 14:45 rule 4, 42.45** | 14:38 rule 3, 47.55 | 0.15 |
| **74,000 (12:34, 12:43)** | 18.97 · 18.08 | 14:38 rule 3, 67.75 | 13:05 rule 3s, 191.65 | **13:05 rule 3s, 191.65** | **the same** | 0.2 |
| 74,000 (13:25) | 12.21 | 14:38 rule 3, 67.75 | the same | the same | the same | 0.2 |
| 73,900 (13:40, 13:42, 13:43) | 24.68 · 24.44 · 24.44 | 14:38 rule 3, 95.9 | the same | the same | the same | 0.1 |
| 73,800 (13:44, 13:53, 13:56, 14:22) | 24.44 · 28.77 · 39.11 · 25.56 | 14:38 rule 3, 133.1 | the same | the same | the same | 0.1 |

**The two 74,000 sales still fold at 13:05, at 191.65, under rev b.**
- **Why:** the 13:03–13:05 bar closed **25.4 pts** through 74,000, and one frozen candle at their entries was **18.97** and
  **18.08** pts. That is more than one candle through, so under the rule she signed for her line it was not noise.
- **The cost, in hindsight:** rev 5 held them to 14:38 at 67.75, and they expired at 0.2.
- **The buffer does not undo this row.** It is disclosed as it is, and not tuned.

**The 165 sold legs on the grid** (§E.2's units, §C with YES):

| | rev a (3s, zero buffer) | **rev b (3s + B_k)** |
|---|---|---|
| first FOLD by rule 3s | 13 | **13** |
| … before rev 5 B's own fold | 8 | **4** |
| … at a lower premium than rev 5's fold (better for her) | 7 | **3** |
| … at a higher premium | 1 | **1** |
| … at the same close as rev 5's line fold | 5 | **9** |
| first FOLD by rule 3 / 6 / 4 / none | 64 / 48 / 27 / 13 | 64 / 48 / 27 / 13 |

**The four rev b 3s folds that come before rev 5's fold:**

| sold leg | 3s fold | rev 5's fold | at 15:29 |
|---|---|---|---|
| SENSEX 09-22 PE 75,000 | 10:20 at 291.55 | 10:31 rule 4 at 342.05 | 448.8 |
| SENSEX 09-23 CE 74,700, two units | 10:17 at 243.35 | 10:20 rule 3 at 264.95 | 276.75 |
| BANKNIFTY 09-24 PE 55,500 | 15:14 at 329.45, the one higher | 15:20 rule 6 at 320.0 | 304.2 |

The other nine 3s folds land on the same close as rev 5's line fold. They are labelled 3s because §C.2 reads the strike first.

**The four rev a 3s folds that the buffer moved to the line's close** were all closes through the strike by less than one
candle, earlier in the bar sequence:
- NIFTY 09-22 PE 23,450 ×2, now 10:26;
- SENSEX 09-24 PE 74,000, now 13:26;
- SENSEX 09-24 CE 73,700, now 14:38.

**Plainly, the strike rule with rev 5 B's buffer:**
- it no longer folds on a poke inside one candle;
- it still folds a close more than one candle through (09-24 74,000 at 13:05);
- on the grid it rarely acts before the line itself (4 of 165).

**Held breaks** (W-R's unit) are unchanged from rev a:
- SENSEX 09-24 14:38 CE (74,100 / 74,200 / 74,300), with P_b → P_x (P_max):
  - 47.55 → 42.45 (53.25);
  - 33.3 → 28.9 (37.05);
  - 23.5 → 19.9 (26.4).
- SENSEX 09-24 15:29 PE 73,500.

### D.7 The grid in rev b: the words at the units, and what did not change

**The 216 units read:**

| word | units |
|---|---|
| BUY | 26 (17 on the count · 9 by refusal) |
| LEANS BUY | 37 (24 · 13) |
| EITHER | 35 |
| LEANS SELL | 41 |
| SELL | 14 |
| STAND ASIDE | 63 (35 both · 14 led · 14 tie) |

**Unchanged from rev a**, because they read no word:
- G is scored at 160 of 216 units;
- the writer population (ii): 165 legs, of which 57 resolved at 30 minutes;
- the held breaks.

**The forward counts by word are now spread over more populations,** since LEANS is never pooled. §E.2's 15-per-word bar will
take longer to reach, and that is disclosed, not tuned.
