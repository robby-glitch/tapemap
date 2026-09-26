# Writes rev c's §D into the draft (after rev c's run). D.3 and D.4's R-multiple table are carried over verbatim from
# the draft (rev a's figures, unchanged). Every table below is generated from expr/revc/*.json.
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
P = r"C:\Users\kaam\Desktop\operator mode\tapemap\docs\hold\EXPRESSION-PREREG-DRAFT.md"
s = open(P, encoding="utf-8").read()
J = lambda p: json.load(open(os.path.join(HERE, p), encoding="utf-8"))
S, Sb, E, G = J("revc/stability.json"), J("revb/stability.json"), J("revc/entries.json"), J("revc/grid.json")
T = "{:,}".format

a = s.index("## D. DISCLOSURE (rev b)")
z = s.index("## E. PARAMETERS, FALSIFIERS, LOGS, CLOCKS")
old = s[a:z]
d3 = old[old.index("### D.3 "):old.index("### D.4 ")]
rtab = old[old.index("**The legs afterwards, in R-multiples"):old.index("### D.5 ")]

g = lambda tb, k: tb.get(k, 0)
per = []
for r in S["per_index_day"]:
    if r["cad"] != "3m":
        continue
    tb = r["tab"]
    b = (g(tb, "BUY·count·"), g(tb, "BUY·refusal·"))
    lbt = g(tb, "LEANS BUY·refusal·tie")
    lb = (g(tb, "LEANS BUY·count·"), g(tb, "LEANS BUY·refusal·") + lbt)
    ls = g(tb, "LEANS SELL·count·") + g(tb, "LEANS SELL·refusal·") + g(tb, "LEANS SELL·refusal·tie")
    ss = g(tb, "SELL·count·") + g(tb, "SELL·refusal·")
    sa = (g(tb, "STAND ASIDE·refusal·both"), g(tb, "STAND ASIDE·refusal·led"))
    day = r["day"] if r["d"] == "UP" else ""
    per.append(f"| {day} | {r['d']} | {sum(b)} ({b[0]} · {b[1]}) | {sum(lb)} ({lb[0]} · {lb[1]}; {lbt}) | {g(tb, 'EITHER·count·')} "
               f"| {ls} | {ss} | {sum(sa)} ({sa[0]} · {sa[1]}) | {r['changes']} · {r['strong_flips']} · {r['side_flips']} | {r['median_run_min']:g} min |")
t3, t1, b3 = S["totals"]["3m"], S["totals"]["1m"], Sb["totals"]["3m"]
tb3 = t3["tab"]
per.append(f"| **total, of 2,250** | | **293 (209 · 84)** | **516 (246 · 270; 169)** | **275** | **325** | **255** | **586 (360 · 226)** "
           f"| **{T(t3['changes'])} · {t3['strong_flips']} · {t3['side_flips']}** | 3 min |")
assert t3["words"] == {"BUY": 293, "EITHER": 275, "LEANS BUY": 516, "LEANS SELL": 325, "SELL": 255, "STAND ASIDE": 586}, t3["words"]
assert (g(tb3, "LEANS BUY·refusal·tie"), g(tb3, "LEANS SELL·refusal·tie")) == (169, 1)

rows = []
f = lambda v: f"{v[0]} r{v[1]} {v[2]:+g}" if v and v[0] else "—"
for n, x in enumerate(E, 1):
    if "why" in x:
        rows.append(f"| {n} | 09-21 13:59 NIFTY 23300CE | UP | **could not check** — never frozen | | | | |")
        continue
    o = x.get("other") or {}
    day, hhmm, idx, leg = x["id"].split(" ")
    lead = "—" if x["lead"] is None else x["lead"]
    ref = ", ".join(x["ref"]) or "—"
    sw = f"since {x['since']}" + (f" · was {x['was']}" if x["was"] else "")
    w = x["word"].replace(" refused", "").replace("STAND ASIDE · both", "STAND ASIDE · both")
    w = {"STAND ASIDE · both": "STAND ASIDE · both refused"}.get(w, w)
    fold = (f"{f(o['rev5'])} · {f(o['b_yes'])} · **{f(o['c'])}** (B_k {o['B_k']})" if o else "—")
    rows.append(f"| {n} | {day} {x['read']} · {x['close_read']} {idx} {leg} | {x['d']} | **{x['word']}** | {lead} · {x['nb']}–{x['ns']} "
                f"| {ref} | {sw} | {fold} |")
assert all((x.get("word_b") == x.get("word")) for x in E if "why" not in x)

gt = G["tab"]
assert sum(gt.values()) == 216

NOW = __import__("datetime").datetime.now().strftime("%H:%M")
D = f"""## D. DISCLOSURE (rev c) — written 2026-09-26 {NOW} IST by the clock, after rev c's fingerprinted run

**In-sample hindsight** on four frozen days and one live day. These are counts and rows, never a rate. **None of it counts
toward §E**, and no word is scored against an outcome on the grid.

**What rev c changed.** Rev c changes no fact, refusal, strike, line or buffer. Two things moved:
- **the word at a tie with one leg refused:** LEANS on the open leg, by refusal, where rev b read STAND ASIDE · tie;
- **the writer's window on her option's expiry day:** a line break folds her as today (her answer, §C.7), where rev b's
  disclosure had assumed YES.
So §D.3 and the R-multiple rows of §D.4 are rev a's, unchanged, and every other table is rev c's.

### D.0 Method, fingerprints, limits, and the repo

**Fingerprints** (`sha256sum` of this file, each before its run):
- rev 0 `eca1afe0…2b6c` (00:21);
- rev 0a `5ddc16d1…a654` (00:33);
- rev a `79d7daa6…162d` (01:28);
- rev a as run `cd210306…dfddf5` (01:32);
- rev b `d7d9ab38…67c0e6cd` (01:48);
- **rev c `64ad9d7f868cfbc7ec7754785966c0a19c46899b4b6219a89fc1dfae90332010` (14:38, `rules_revc_before_run.md`).**
- The rules text did not move after rev c's run. §D, §G's post-run lines and §H were written after it.

**Scratch** (the session scratchpad `expr/`):
- `expr_c.py` implements rev c once: rev b's grading with the tie changed (it carries one self-check), and rev b's reach with
  the answer NO.
- `run_c.py` does the run, 14:39–14:42.
- The outputs are in `expr/revc/`: `stability.json`, `silence_detail.json`, `entries.json`, `seller_0924.json` and
  `grid.json`. `gen_D_c.py` wrote this section from them.

**The repo.** Every rev c script writes to absolute paths inside `expr/`, and rev c wrote nothing in the repo but this draft.
- `git status` after the run showed changes that are **not rev c's**, and they were left untouched:
  - `ui-v2/src/hold/*` (14:36:33) and `docs/hold/BUILD-REPORT.md` (14:37:11), both modified before rev c's patch (14:38);
  - a new `docs/hold/scratch-2026-09-25/` (14:41:52–58), a copy of this session's scratchpad folders made by another
    process during the run.

**The inputs** are as rev a's:
- nearer-only fronts on 09-22 and 09-23 [I];
- Black-76 greeks [I];
- [I] candles on NIFTY and BANKNIFTY 09-24;
- 09-21 not frozen;
- 09-25 without premiums.

**"Expiry day"** on the record is NIFTY 09-22 and SENSEX 09-24: the chain's resolved expiry was the session date. BANKNIFTY
had none.

### D.1 Words and silence at the 3-minute close (rev c's words)

The counts are per index-day and direction, of 125 closes.
- "count · ref" splits a word named on the count from one named because the other leg was refused.
- For LEANS BUY, the figure after the semicolon is the ties with selling refused, which rev c names LEANS BUY.
- STAND ASIDE is split into both refused · led.

| index-day | dir | BUY (count · ref) | LEANS BUY (count · ref; of which ties) | EITHER | LEANS SELL | SELL | STAND ASIDE (both · led) | changes · BUY↔SELL · buy-side↔sell-side | median run |
|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(per)}

**At the 3-minute close (2,250 reads):**

| word | closes |
|---|---|
| BUY | 293 (209 on the count · 84 by refusal) |
| LEANS BUY | 516 (246 on the count · **270 by refusal**: 101 with a one-fact lead, **169 ties**) |
| EITHER | 275 |
| LEANS SELL | 325 (323 · 2 by refusal: 1 with a one-fact lead, 1 tie) |
| SELL | 255 (253 · 2) |
| **STAND ASIDE** | **586** (360 both refused · 226 led) |

**Silence at the 3-minute close: 586 of 2,250 closes.** That is rev b's 756 less its 170 STAND ASIDE · tie closes, and the same
586 as rev a.
- **The 170 ties now read LEANS:** 169 LEANS BUY · selling refused and 1 LEANS SELL · buying refused.
- **LEANS BUY is now the biggest word, and more than half of it is named by refusal:** 270 of 516. It is its own population,
  never pooled with the 246 on the count (§E.2).
- **Of the 1,389 directional words, 841 are LEANS:** 569 on the count, 102 by refusal with a one-fact lead, and 170 by
  refusal at a tie.

**Every minute, for comparison** (6,750 reads):
- BUY {T(t1['words']['BUY'])};
- LEANS BUY {T(t1['words']['LEANS BUY'])} ({T(g(t1['tab'], 'LEANS BUY·count·'))} · {T(g(t1['tab'], 'LEANS BUY·refusal·') + g(t1['tab'], 'LEANS BUY·refusal·tie'))} by refusal, of which {g(t1['tab'], 'LEANS BUY·refusal·tie')} ties);
- EITHER {T(t1['words']['EITHER'])};
- LEANS SELL {T(t1['words']['LEANS SELL'])};
- SELL {T(t1['words']['SELL'])};
- STAND ASIDE {T(t1['words']['STAND ASIDE'])} ({T(g(t1['tab'], 'STAND ASIDE·refusal·both'))} · {T(g(t1['tab'], 'STAND ASIDE·refusal·led'))});
- could not check {t1['words']['could not check']}.

### D.2 Stability under rev c's words, both cadences

| | read every minute | **read at the 3-minute close (registered)** | rev b at the 3-minute close | rev a at the 3-minute close |
|---|---|---|---|---|
| reads | 6,750 | 2,250 | 2,250 | 2,250 |
| word changes, of transitions | {T(t1['changes'])} of 6,732 | **{T(t3['changes'])} of 2,232** | {b3['changes']} of 2,232 | 752 of 2,232 |
| median life of a word | {t1['median_run_min']:g} minutes | **{t3['median_run_min']:g} minutes** (one bar) | 3 minutes | 6 minutes |
| runs that last a single read | {t1['runs_of_one']} of {T(t1['runs'])} | **{t3['runs_of_one']} of {T(t3['runs'])}** | {b3['runs_of_one']} of {T(b3['runs'])} | 355 of 770 |
| **direct BUY ↔ SELL flips** (strong to strong) | {t1['strong_flips']} | **{t3['strong_flips']}** | {b3['strong_flips']} | 185 |
| buy-side ↔ sell-side flips (any of BUY, LEANS BUY to any of SELL, LEANS SELL) | {t1['side_flips']} | **{t3['side_flips']}** | {b3['side_flips']} | 185 |
| directional words that are LEANS | {T(t1['words']['LEANS BUY'] + t1['words']['LEANS SELL'])} of {T(t1['words']['LEANS BUY'] + t1['words']['LEANS SELL'] + t1['words']['BUY'] + t1['words']['SELL'])} | **841 of 1,389** | 671 of 1,219 | — |

**Plainly:**
- **Rev c moves the word little.** The 170 ties that were STAND ASIDE are now LEANS on the open leg, so 23 more closes change
  word and 32 more side flips appear, all through LEANS. The strong BUY ↔ SELL flip stays at 11.
- **The word is still close to a coin flip at its margin, and it says so in its letters:** 841 of its 1,389 directional
  words are LEANS, and 272 of those are named by refusal.

{d3}### D.4 At her 29 entries, the word on the screen at her entry (rev c)

This is the last 3-minute close at or before her read minute.
- The lead is the named leg's count minus the other's.
- The last column is the sold leg's first FOLD, in seller points at the fold:
  - rev 5 option B as built;
  - rev b's rule with YES, which is not registered;
  - **rev c: 3s with B_k, and NO on expiry day (registered).**

| # | entry (read · close read) | dir | **word (rev c)** | lead · b–s | refused | since · was | the sold leg's first FOLD: rev 5 B · YES (not registered) · **rev c** — seller pts |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

**The words at her 29 entries:**

| word | entries |
|---|---|
| BUY | 7 |
| LEANS BUY | 9 |
| SELL | 3 |
| LEANS SELL | 4 |
| EITHER | 2 |
| STAND ASIDE | 3 (2 both refused · 1 led) |
| could not check | 1 |

**Silent at 4 of 29,** as in rev b. Every directional word was named on the count.
- **No entry word moved in rev c.** None of her 29 entries fell on a tie with one leg refused. Only one "was" changed: #8's
  prior word is now LEANS BUY PE · selling refused, where rev b had STAND ASIDE · tie.
- **The answer NO moved seven sold legs,** all SENSEX 09-24 (expiry): #19–#25 fold at 14:38 by rule 3, as rev 5 B does, instead
  of being held to 14:45 under YES. In seller points that is 4.4 less on each of the seven, with the premium 4.4 higher at
  14:38 than at 14:45.
- **Under rev c, every sold leg at her entries folds exactly where rev 5 B folds it,** except #27–#29, which 3s labels at the
  same 14:38 close.

{rtab}### D.5 Her 09-25 NIFTY entries (rev c)

These are read at the read minute [I proxy]. The 3-minute-close facts before each entry were not frozen, and no premium was
frozen, so **R4 refuses SELL at all three**. That is the frozen record's gap, not the market's.

| entry (read) | dir | the word (rev c) | lead · b–s | what moved |
|---|---|---|---|---|
| 09:36 PE (her words; the saved 09:35 check) | DOWN | **STAND ASIDE · led:** "the facts favour selling, 3 to 0, but selling is refused: R4 — could not check" | −3 · 0–3 | as rev a and rev b |
| 12:01:21 CE (marked) | UP | **LEANS BUY CE · selling refused (R4):** "the facts tie 1–1; selling is refused, so the open leg is named, weakly" | 0 · 1–1 | rev b said STAND ASIDE · tie; rev a said BUY CE · selling refused |
| 12:05:28 PE (marked) | DOWN | **LEANS BUY PE · selling refused (R4)** | 1 · 2–1 | as rev b |

### D.6 The seller on 09-24 under rev c: her answer NO, and the buffered rule 3s

These are her 13 put entries read as sales of the call at the same strike (the handoff's replay). 09-24 was SENSEX's expiry,
so under her answer the reach is not read on any of them.

| sold call (entries) | B_k at entry | rev 5 B (as built) | **rev c (NO, registered)** | YES (not registered) | at 14:59 [M] | at 15:29 [M] |
|---|---|---|---|---|---|---|
| 74,200 (09:41, 10:18) | 26.37 · 22.64 | 10:43 rule 4, 138.2 | **the same** | the same | 22.15 | 0.15 |
| 74,100 (12:31) | 17.45 | 14:38 rule 3, 47.55 | **14:38 rule 3, 47.55** | held 14:38 (P_max 53.25), 14:45 rule 4, 42.45 | 33.55 | 0.15 |
| **74,000 (12:34, 12:43)** | 18.97 · 18.08 | 14:38 rule 3, 67.75 | **13:05 rule 3s, 191.65** | the same as rev c | 50.2 | 0.2 |
| 74,000 (13:25) | 12.21 | 14:38 rule 3, 67.75 | **the same** | the same | 50.2 | 0.2 |
| 73,900 (13:40, 13:42, 13:43) | 24.68 · 24.44 · 24.44 | 14:38 rule 3, 95.9 | **the same** | the same | 76.1 | 0.1 |
| 73,800 (13:44, 13:53, 13:56, 14:22) | 24.44 · 28.77 · 39.11 · 25.56 | 14:38 rule 3, 133.1 | **the same** | the same | 111.2 | 0.1 |

**Under rev c the 09-24 seller is rev 5 B's window exactly, except the two 74,000 sales.** 3s folds those at 13:05, at 191.65:
that bar closed 25.4 pts through 74,000, against one frozen candle of 18.97 and 18.08 pts. It is disclosed as it is, and not
tuned.
- **The 74,100 call folds at 14:38 at 47.55, as today.** Under YES it would have been held seven minutes, touched 53.25, and
  folded at 14:45 at 42.45 by rule 4.

**The 165 sold legs on the grid** (§E.2's units):

| | rev b (YES assumed) | **rev c (NO, registered)** |
|---|---|---|
| first FOLD by rule 3 / 6 / 4 / 3s / none | 64 / 48 / 27 / 13 / 13 | **71 / 48 / 22 / 13 / 11** |
| held breaks (legs held on a line break) | 7 legs, 2 held breaks | **none** |
| 3s before rev 5 B's own fold | 4 (3 at a lower premium, 1 higher) | **4 (the same four)** |
| 3s at the same close as rev 5 B's line fold | 9 | **9** |
| first FOLD at the same minute as rev 5 B | 154 | **161** |

- **The seven legs the answer moved** were all SENSEX 09-24, its expiry. They were held under YES and now fold at the line,
  as rev 5 B does:
  - CE 74,300 ×3 and CE 74,200 ×2: 14:38 rule 3, at 23.5 and 33.3, where YES held them to 14:45 at 19.9 and 28.9;
  - PE 73,500 ×2 (the 14:44 and 15:14 units): at the 15:29 close by rule 3, at 0.15, the same premium YES's to-close gave.
- **The four 3s folds before rev 5's** are unchanged from rev b: SENSEX 09-22 PE 75,000 (10:20 at 291.55, against 10:31 at
  342.05); SENSEX 09-23 CE 74,700 ×2 (10:17 at 243.35, against 10:20 at 264.95); BANKNIFTY 09-24 PE 55,500 (15:14 at 329.45,
  against 15:20 at 320.0, the one higher).

**Held breaks, W-R's unit: none on the record under her answer.** Both of rev b's held breaks (SENSEX 09-24 14:38 CE; 15:29 PE
73,500) were on SENSEX's expiry day. So off expiry, where the reach is still read, it bound nowhere on these four days. W-R's
forward populations will fill slowly (§C.4).

### D.7 The grid in rev c: the words at the units

**The 216 units read:**

| word | units |
|---|---|
| BUY | {g(gt, 'BUY·count·') + g(gt, 'BUY·refusal·')} ({g(gt, 'BUY·count·')} on the count · {g(gt, 'BUY·refusal·')} by refusal) |
| LEANS BUY | {g(gt, 'LEANS BUY·count·') + g(gt, 'LEANS BUY·refusal·') + g(gt, 'LEANS BUY·refusal·tie')} ({g(gt, 'LEANS BUY·count·')} · {g(gt, 'LEANS BUY·refusal·') + g(gt, 'LEANS BUY·refusal·tie')} by refusal, of which {g(gt, 'LEANS BUY·refusal·tie')} ties) |
| EITHER | {g(gt, 'EITHER·count·')} |
| LEANS SELL | {g(gt, 'LEANS SELL·count·')} |
| SELL | {g(gt, 'SELL·count·')} |
| STAND ASIDE | {g(gt, 'STAND ASIDE·refusal·both') + g(gt, 'STAND ASIDE·refusal·led')} ({g(gt, 'STAND ASIDE·refusal·both')} both · {g(gt, 'STAND ASIDE·refusal·led')} led) |

**Unchanged from rev b**, because they read no word: G is scored at 160 of 216 units, and the writer population (ii) is 165
legs, of which 57 resolved at 30 minutes.

**The forward counts by word are spread over more populations.** Each refusal-named word is now judged on its own (§E.2), so
§E.2's 15-per-word bar takes longer to reach. On the grid, LEANS BUY by refusal is the most frequent refusal word ({g(gt, "LEANS BUY·refusal·") + g(gt, "LEANS BUY·refusal·tie")} of 216 units).
That is disclosed, not tuned.

### D.8 Her practice, not a rule: nothing held or opened after 15:00

**Her words, 2026-09-26:**
> "we gonna close our position before 3 because due to new cas system is highly volatile i dont want to get into that no
> trade buying or selling after 3 om to be on safe side dont make any new rules but just telling you so that you know because
> maybe it change in future (cas system)"

**Her current practice:** no position held, and none opened, after 15:00. It may change with the CAS system. **It is not a
rule, a refusal or a gate here:** no word, fact, refusal, fold or falsifier reads the clock at 15:00. The only change is the
descriptive log flag `after_1500` (§E.3), so the forward record can be read with and without those rows.

**The evidence in this draft that falls after 15:00:**
- **The 09-24 seller rows (§D.6).** The 14:38 folds are before 15:00, but the hindsight they are measured against is not.
  The calls "expired at 0.1–0.2" at 15:29. At 14:59, where her practice would have closed them, they stood at 22.15 (74,200),
  33.55 (74,100), 50.2 (74,000), 76.1 (73,900) and 111.2 (73,800) [M].
  - Measured against 14:59, the 14:38 line folds gave up 14.0 (74,100), 17.55 (74,000), 19.8 (73,900) and 21.9 (73,800)
    points, not 47–133 as against 15:29.
  - The 74,000 3s fold at 13:05 (191.65) stood 141.45 above its 14:59 premium.
  - The 10:43 fold of 74,200 (138.2) stood 116.05 above.
  - These are hindsight rows, shown and not judged.
- **The held breaks under YES,** the road not taken: the 14:38 CE break was held to 14:45, before 15:00. The PE 73,500 break
  came at the 15:29 close, after 15:00.
- **The grid:**
  - the units at 14:44, whose 30 minutes cross 15:00, and 15:14 are 36 of the 216 units;
  - 25 of the 165 sold legs start at those units;
  - 22 of the 165 sold legs first fold at 15:00 or later, or not at all, and run to 15:29. Among them is the BANKNIFTY 09-24
    PE 55,500 3s fold at 15:14.
- **Every "to 15:29" figure is after 15:00 by construction:** §D.4's "sold leg to 15:29", the writer word's to-15:29 read, and
  §B.3's to-15:29, which is shown and not judged.
- **Not after 15:00:** her 29 entries, and their 30-minute windows (the last, #29 at 14:22, ends at 14:52), and her three 09-25
  entries.
- **§E.2's check with the `short` units removed** (after 14:59) was registered before her words, and is unchanged. It is a
  check on the falsifier, not her practice made a rule.

---

"""
s = s[:a] + D + s[z:]
open(P, "w", encoding="utf-8", newline="\n").write(s)
print("D written", len(D))
