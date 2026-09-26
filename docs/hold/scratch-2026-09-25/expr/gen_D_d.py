# Writes rev d's §D into the draft (after rev d's run), from expr/revd/tables_d.md (gen_tables_d.py) and hand-written prose.
# §D.3's facts / refusals / co-occurrence tables and §D.5's rows are carried over verbatim from rev c's §D: rev d's run
# reproduces the same words and refusal counts at every close (revd/moved_from_revc.json is empty; revd/refusals.json).
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
P = r"C:\Users\kaam\Desktop\operator mode\tapemap\docs\hold\EXPRESSION-PREREG-DRAFT.md"
NOW = sys.argv[1]
s = open(P, encoding="utf-8").read()
tb = open(os.path.join(HERE, "revd", "tables_d.md"), encoding="utf-8").read()
J = lambda p: json.load(open(os.path.join(HERE, p), encoding="utf-8"))
RF, G, MV = J("revd/refusals.json"), J("revd/grid.json"), J("revd/moved_from_revc.json")
assert MV == {} and RF["refusals"] == {"R3": 98, "R4cnc": 138, "R5": 372, "R1": 355, "R2": 311, "R6": 440, "R4": 24}


def block(title, stop="\n###"):
    a = tb.index(title) + len(title)
    b = tb.find(stop, a)
    return tb[a:b if b > 0 else None].strip()


def table_only(txt):
    return "\n".join(l for l in txt.split("\n") if l.startswith("|"))


a = s.index("## D. DISCLOSURE (rev c)")
z = s.index("## E. PARAMETERS, FALSIFIERS, LOGS, CLOCKS")
old = s[a:z]
d3 = old[old.index("| fact | FOR BUY | FOR SELL | NEITHER |"):old.index("**Where the sale was placed (Q3)**")].rstrip()
d5 = old[old.index("| entry (read) | dir | the word (rev c)"):old.index("### D.6 ")].rstrip().replace("the word (rev c)", "the word (rev d)")
d1_rows = table_only(block("### D.1 table"))
d2 = table_only(block("### D.2 table"))
d4w = table_only(block("### D.4 words"))
d4r = table_only(block("### D.4 R-multiples and the writer word"))
d6 = table_only(block("### D.6 seller 09-24 (her strikes as CE sales), rev 5 B", "\ngrid legs"))
d6 = (d6.replace("(09:42, 10:19)", "(09:41, 10:18)").replace("(12:32)", "(12:31)")
        .replace("(12:35, 12:44, 13:26)", "(12:34, 12:43, 13:25)").replace("(13:41, 13:43, 13:44)", "(13:40, 13:42, 13:43)")
        .replace("(13:45, 13:54, 13:57, 14:23)", "(13:44, 13:53, 13:56, 14:22)"))
w, L = G["writer"], G["legs"]
assert (w["n"], w["words"], w["cnc_moved"], w["stratum"], w["stratum_beyond"], w["beyond"], w["resolved30"], w["resolved1529"], w["notscored"]) == \
    (216, {"GO": 72, "NO": 35, "WAIT": 109}, 0, {"GO": 72, "NO": 21, "WAIT": 77}, {"GO": 71, "NO": 19, "WAIT": 74}, 196, 78, 127, 38)
assert L == {"n": 216, "first_fold": {"3": 108, "4": 35, "6": 54, "none": 19}, "exp_today": 48, "after_1500_start": 18}
assert G["scored_G"] == 204 and G["notscored"] == {"no premium": 6, "no greeks": 6}
ts = G["tab_scored"]

D = f"""## D. DISCLOSURE (rev d) — written 2026-09-26 {NOW} IST by the clock, after rev d's fingerprinted run

**In-sample hindsight** on four frozen days and one live day. These are counts and rows, never a rate. **None of it counts
toward §E**, and no word is scored against an outcome on the grid.

**What rev d changed in what this reads:**
- **the sale's strike:** the ATM strike, the buy's (§A.5), where rev c placed it at the wall or K₀;
- **the writer's word (§B):** its wall is §A's wall behind the sale, and a could-not-check risk fact reads WAIT;
- **the window:** every sold leg is folded by rev 5 B as built (§C), with no reach and no 3s.

**No word moved at any of the 2,250 closes, and no refusal count moved** [M] (`revd/moved_from_revc.json` is empty;
`revd/refusals.json`).
- R1 and R2 read the window's fronts and flow for the short leg, and those do not depend on its strike.
- R4's straddle clause added a code only where SELL was already refused.

So §D.1–§D.3's words, stability and refusals are rev c's, reproduced by rev d's own run. What is new is §D.4's sold leg
and writer word, §D.6, §D.7's scoring and writer population, and §D.8.

### D.0 Method, fingerprints, limits, and the repo

**Fingerprints** (`sha256sum` of this file, each before its run):
- rev 0 `eca1afe0…2b6c` (00:21);
- rev 0a `5ddc16d1…a654` (00:33);
- rev a `79d7daa6…162d` (01:28);
- rev a as run `cd210306…dfddf5` (01:32);
- rev b `d7d9ab38…67c0e6cd` (01:48);
- rev c `64ad9d7f…2010` (14:38);
- **rev d `78b5f86c8994229fcc7c31f29c400f1c388c3094ba12201d0e5e6bb5cc97d260` (19:22, `rules_revd_before_run.md`).**
- The rules text did not move after rev d's run. §D and §G's post-run lines were written after it.

**Scratch** (`docs/hold/scratch-2026-09-25/expr/`):
- `expr_d.py` implements rev d once, over rev c's code. It carries self-checks of the new writer clause and the shared wall.
- `run_d.py` does the run, 19:25:54–19:27:58.
- The outputs are in `expr/revd/`: `stability.json`, `refusals.json`, `moved_from_revc.json`, `entries.json`,
  `seller_0924.json` and `grid.json`.
- `gen_tables_d.py` wrote the tables (`revd/tables_d.md`), and `gen_D_d.py` wrote this section from them. The prose was
  written by hand after the tables were read.

**The repo.** Rev d's scripts write only inside `expr/`, and run with `python -B` (no `__pycache__`). `git status` after the
run showed only rev d's scratch files, this draft, and the second review (`EXPRESSION-REVIEW-2.md`, the reviewer's file).

**The inputs** are as rev a's:
- nearer-only fronts on 09-22 and 09-23 [I];
- Black-76 greeks [I];
- [I] candles on NIFTY and BANKNIFTY 09-24;
- 09-21 not frozen;
- 09-25 without premiums.

**"Expiry day"** on the record is NIFTY 09-22 and SENSEX 09-24: the chain's resolved expiry was the session date. BANKNIFTY
had none.

### D.1 Words and silence at the 3-minute close (rev d's words, identical to rev c's)

The counts are per index-day and direction, of 125 closes.
- "count · ref" splits a word named on the count from one named because the other leg was refused.
- For LEANS BUY, the figure after the semicolon is the ties with selling refused (rev c's rule).
- STAND ASIDE is split into both refused · led.

{d1_rows}
| **total, of 2,250** | | **293 (209 · 84)** | **516 (246 · 270; 169)** | **275** | **325 (323 · 2)** | **255 (253 · 2)** | **586 (360 · 226)** | **1,010 · 11 · 185** | 3 min |

**At the 3-minute close (2,250 reads):**

| word | closes |
|---|---|
| BUY | 293 (209 on the count · 84 by refusal) |
| LEANS BUY | 516 (246 on the count · **270 by refusal**: 101 with a one-fact lead, **169 ties**) |
| EITHER | 275 |
| LEANS SELL | 325 (323 · 2 by refusal: 1 with a one-fact lead, 1 tie) |
| SELL | 255 (253 · 2) |
| **STAND ASIDE** | **586** (360 both refused · 226 led) |

**Silence at the 3-minute close: 586 of 2,250 closes.**
- **LEANS BUY is the most frequent directional word, and more than half of it is named by refusal:** 270 of 516. It is its
  own population, never pooled with the 246 on the count (§E.2).
- **Of the 1,389 directional words, 841 are LEANS.**

**What stands behind the words named by refusal** (review A-T5, A-T6) [M]:

| word named by refusal | closes | R6 among its refusals | R6 alone |
|---|---|---|---|
| BUY · selling refused | 84 | 60 | 39 |
| LEANS BUY · selling refused, a one-fact lead | 101 | 51 | 35 |
| LEANS BUY · selling refused, a tie (rev c) | 169 | **121** | **105** |
| STAND ASIDE · led | 226 | 112 | 96 |
| STAND ASIDE · both refused | 360 | 96 | 5 |
| SELL, LEANS SELL · buying refused (all four) | 4 | 0 | 0 |

- **Most of rev c's refused ties rest on R6,** "no wall behind the sale": 121 of 169, and R6 alone on 105. R6 over-fired on
  09-22 and 09-23, where only the nearer fronts were frozen (§D.3). So most of rev c's in-sample effect sits on a fixture
  gap, and the forward rows will say how often a real session reads it.
- **A word named because buying is refused almost never occurs:** 4 of 2,250 closes, and 0 of the 216 units (§D.7). Expect
  SELL and LEANS SELL · buying refused to end inconclusive and DRAFT [I].

**Every minute, for comparison** (6,750 reads):
- BUY 871;
- LEANS BUY 1,524 (746 · 778 by refusal, of which 472 ties);
- EITHER 774;
- LEANS SELL 1,032;
- SELL 762;
- STAND ASIDE 1,757 (1,069 · 688);
- could not check 30.

### D.2 Stability, both cadences (rev d's, identical to rev c's)

{d2}

**Plainly:**
- **The word changes often.** Its median life is one bar, and 562 of its 1,028 runs last a single read. The since-clock is what
  makes it usable: a word that has stood four bars and one that appeared this bar are different reads.
- **The word is still close to a coin flip at its margin, and it says so in its letters:** 841 of its 1,389 directional
  words are LEANS.
- Rev a's 185 direct BUY ↔ SELL flips, in rev c's history, are not comparable with these 11 (review A-T7). Rev a had no
  LEANS, so every directional word was "strong" there.

### D.3 Facts, refusals and co-occurrence — rev a's, unchanged in revs b, c and d

{d3}

**The sale's strike (rev d):** the ATM strike, the buy's, at every word. Rev c's placements (478 at the wall, 102 at K₀ at the
580 SELL words; the wall a median 0.19 straddles out) are on file in rev c's outputs (`reva/facts_3m.json`), and none is
registered.

### D.4 At her 29 entries, the word on the screen at her entry (rev d)

This is the last 3-minute close at or before her read minute.
- The lead is the named leg's count minus the other's.
- The last column is **the sold leg at the ATM strike**, named with rev c's strike where it differed. It shows that leg's first
  FOLD under rev 5 B, which is the window as built and as registered (§C), in seller points at the fold.

{d4w}

**The words at her 29 entries** (unchanged from rev c):

| word | entries |
|---|---|
| BUY | 7 |
| LEANS BUY | 9 |
| SELL | 3 |
| LEANS SELL | 4 |
| EITHER | 2 |
| STAND ASIDE | 3 (2 both refused · 1 led) |
| could not check | 1 |

- **No entry word moved in rev d** [M].
- **The sold leg moved to the ATM strike at 20 of her 28 frozen entries.** At #9 rev c named no sale, because S could not be
  read at 09:17 (R4). Rev d prices the ATM 23,400 PE there and still refuses it.
- **The window folds every sold leg as rev 5 B does,** because §C changes nothing.

**The legs afterwards, in R-multiples on the shared line, and the writer's word** (rev d: the sell leg at the ATM strike).
The sold leg's premium change is shown to 14:59, where her practice closes (§D.8), and to 15:29.

{d4r}

- **The writer's word at her entries** (§B, rev d): GO 7, WAIT 19, NO 2 [M]. Rev d's could-not-check clause moved none of
  them. These are rows, shown and not judged.
- **The line lies beyond the strike at 27 of 28,** as §B.1 says it must for a sale at the money. X is computed there and
  flagged.

### D.5 Her 09-25 NIFTY entries (rev d)

These are read at the read minute [I proxy]. The 3-minute-close facts before each entry were not frozen, and no premium was
frozen, so **R4 refuses SELL at all three**. That is the frozen record's gap, not the market's. Rev d moves nothing here.

{d5}

### D.6 The seller on 09-24, folded as today (her answers)

These are her 13 put entries read as sales of the call at the same strike (the handoff's replay). The window is rev 5 B,
unchanged, on every day (§C).

{d6}

- **The 11 sold calls folded at 14:38 by rule 3** (the bounce off the 14:24 low), and the two 74,200 calls at 10:43 by
  rule 4. **Every one ended at 0.1–0.2.** Her answers keep those folds. This is disclosed, not tuned (§C.3).
- **Against 14:59, where her practice would have closed them,** the 14:38 folds gave up 14.0 (74,100), 17.55 (74,000), 19.8
  (73,900) and 21.9 (73,800) points [M]. The 10:43 fold of 74,200 (138.2) stood 116.05 above its 14:59 premium.

**The 216 sold legs on the grid**, one per unit at the ATM strike, under rev 5 B [M]:

| first FOLD | legs |
|---|---|
| rule 3, the line | 108 |
| rule 6 | 54 |
| rule 4 | 35 |
| none to 15:29 | 19 |

48 of them are on an expiry day (NIFTY 09-22, SENSEX 09-24).

### D.7 The grid in rev d: the words at the units, scoring, and the writer population

**The 216 units read** (unchanged from rev c):

| word | units | scored (G): count · refusal |
|---|---|---|
| BUY | 26 (17 on the count · 9 by refusal) | {ts['BUY·count·']} · {ts['BUY·refusal·']} |
| LEANS BUY | 51 (24 · 27 by refusal, of which 14 ties) | {ts['LEANS BUY·count·']} · {ts['LEANS BUY·refusal·'] + ts['LEANS BUY·refusal·tie']} |
| EITHER | 35 | {ts['EITHER·count·']} |
| LEANS SELL | 41 | {ts['LEANS SELL·count·']} |
| SELL | 14 | {ts['SELL·count·']} |
| STAND ASIDE | 49 (35 both · 14 led) | {ts['STAND ASIDE·refusal·both']} · {ts['STAND ASIDE·refusal·led']} |

- **G is scored at 204 of 216 units** [M], where rev c scored 160. The sale is always priced now, so the R6 units are scored.
  - The 12 not scored are "no premium" (6) and "no greeks" (6).
- **The refusal populations will fill slowly.** On the grid, BUY · selling refused had 9 units and LEANS BUY · selling refused
  27. SELL and LEANS SELL · buying refused had none. §E.2's bar is 15 per word per direction, so these will take many
  sessions, and some may end DRAFT [I].

**The writer population (ii)** (§B.3), at the ATM sell leg of every unit [M]:

| | GO | WAIT | NO | all |
|---|---|---|---|---|
| the writer's word | 72 | 109 | 35 | 216 |
| in the stratum (line > noise and P ≥ X) | 72 | 77 | 21 | 170 |
| of which the line lies beyond the strike | 71 | 74 | 19 | 164 |

- **Rev d's could-not-check clause moved no unit's word** [M]. It is a guard for the forward record, and it did not bind on
  these days.
- **The line lies beyond the strike at 196 of 216 units,** as it must for a sale at the money (§B.1). The stratum keeps them,
  flagged (review B-M1).
- **Resolved within 30 minutes: 78, all inside the stratum. To 15:29: 127. Not scored: 38.** No word is crossed with an
  outcome here.

### D.8 Her practice, not a rule: nothing held or opened after 15:00

**Her words, 2026-09-26:**
> "we gonna close our position before 3 because due to new cas system is highly volatile i dont want to get into that no
> trade buying or selling after 3 om to be on safe side dont make any new rules but just telling you so that you know because
> maybe it change in future (cas system)"

**Her current practice:** no position held, and none opened, after 15:00. It may change with the CAS system. **It is not a
rule, a refusal or a gate here:** no word, fact, refusal, fold or falsifier reads the clock at 15:00. The only change is the
descriptive log flag `after_1500` (§E.3), so the forward record can be read with and without those rows.

**The evidence in this draft that falls after 15:00:**
- **The 09-24 seller rows (§D.6).** The folds are before 15:00, but the hindsight they are measured against is not. The calls
  "expired at 0.1–0.2" at 15:29. At 14:59 they stood at 22.15 (74,200), 33.55 (74,100), 50.2 (74,000), 76.1 (73,900) and
  111.2 (73,800) [M].
- **The grid:**
  - the units at 14:44, whose 30 minutes cross 15:00, and at 15:14 are 36 of the 216;
  - 18 of the 216 sold legs start at the 15:14 units;
  - 19 are not folded by 15:29, and run to the close.
- **Every "to 15:29" figure is after 15:00 by construction:** §D.4's "to 15:29", the writer word's to-15:29 read, and §B.3's
  to-15:29, which is shown and not judged. §D.4 now shows "to 14:59" beside it.
- **Not after 15:00:** her 29 entries, and their 30-minute windows (the last, #29 at 14:22, ends at 14:52), and her three 09-25
  entries.
- **§E.2's check with the `short` units removed** (after 14:59) was registered before her words, and is unchanged. It is a
  check on the falsifier, not her practice made a rule.

---

"""
s = s[:a] + D + s[z:]
open(P, "w", encoding="utf-8", newline="").write(s)
print("written")
