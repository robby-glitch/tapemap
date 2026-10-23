# FLOW-STATE-STUDY — delta / CVD rate of change × volume, tested on recorded days (18 Oct 2026)

**Descriptive only.** Rows like "22 of 38". No verdicts, no success rates; Mary signs no bar here, so everything below is a **prereg candidate**, not a rule. **SEEN** = the recorded sessions we have all looked at (the spec §4 numbers were built on them); **FORWARD-LOGGED** = the extension's marks as logged live. Every table says its n. Scripts and raw outputs: `fresh-take/scratch/fs_lib.py, fs_build1m.py, fs1.py, fs1m.py … fs7.py` and `fs*_out.txt` (run with `python -B`). GET-only on the server (one `GET /api/health` to see it was up; the `/api/contract` pulls used are the cached ones already in `scratch/`); nothing outside `fresh-take/` was written.

## 0. Data, what I rebuilt, and what I added after looking

- **GC NIFTY 5-min:** the 17 days / 1,169 bars of `roc.py` (days with ≥ 40 bars, 11 Sep–12 Oct). My `fs_lib.py` **reproduces the spec §4 table exactly** (|Δ| 77/139/338, Δ÷vol 0.18/0.27/0.43, flip 173/269/549, slope 11.9/21.7/48.5, acc 16.5/29.3/63.0, RVOL 1.01/1.50/2.58, vacc 0.88/1.20/1.94), so every number below sits on the same base. 13 and 16 Oct (9 and 24 bars) are used only for the marks and two named moments.
- **Upstox 5-min, all three indices:** the `ux_*` files, full-session days only: 11 days (22 Sep–8 Oct; 7, 9, 12, 13, 16 Oct are partial).
- **1-min bars:** rebuilt from the book ticks with the repo's own `ladder.Ladder` at the live settings (lot by gcd, tick 10 / 20 / 5; 22 Sep inferred, as the live file did). Their 5-minute sums equal the shipped `ux` bars **exactly (955 of 955 NIFTY, 955 of 955 BANKNIFTY, 953 of 953 SENSEX)**, so the 1-min series is the same delta, just finer. Ticks are complete only on the 11 full days.
- **Price path for outcomes:** `of_lib.path` (REST 3-min bars 5–16 Oct, tick-built 3-min bars 22 Sep–1 Oct). Outcome = **0.5U first within 60 min** from the bar close, U = max(VWAP σ, 0.1% of price) — the same method as ORDERFLOW-STUDY, so tables are comparable. Outcome days: 22 Sep–12 Oct (11 Sep, 18 Sep, 21 Sep have no path).
- **Ranks:** all states use **leave-one-day-out** thresholds (the reference days' features are themselves built with a base that excludes the target day and themselves). The spec's thresholds are in-sample; LODO is stricter.
- **Fixed before the first outcome table was printed (in code):** the concrete state rules and their priority; the price-result definition and its 0.25 cut; the sign-agreement requirement on slope/acceleration inside PUSH (**my addition — the spec does not say it**); the comparators (BIG_other, VOL_other, LOWVOL_other, ALL, time-shifted ±30/60 min); the at-60-min-extreme split; the 1-min lead test; the GC-vs-Upstox design (same bars, GC prices injected into both).
- **Added after looking at results (flagged where used):** episode clustering (§3.1); flip swing as its own row (§3.4); next-bar failure (§3.5); clock buckets and roll/expiry table (§1.8); the sign-shuffle null on **state counts** (§3.1); SENSEX with empty bars kept and at 15 minutes (§5); the close-location check of 16 Oct 10:15 (§1.9); day-block bootstrap of thresholds (§1.6); delta–price coupling stats (§2).
- **Cells and multiple comparisons.** About **72 outcome rows (≈ 290 outcome cells)** are printed (fs2 ≈ 26 rows, fs3 ≈ 38, fs5 ≈ 8), plus ≈ 100 measurement numbers in §1. About 24 "state vs comparator" contrasts were read. Almost every outcome row has n < 60 and many have n < 15; **bars cluster** (39 PUSH bars are 25 episodes; §3.1), so effective n is smaller than the row n. A handful of rows will look special by chance. Read the tables as a map of where to look, not as findings.

## 1. Critique of the metrics and the rules

### 1.1 Delta ÷ volume is the right scale-free measure, and "light" is not a small-count artifact (NIFTY)
- log|Δ| on log volume has slope **0.97** (0.5 would be pure sampling noise, 1.0 means the share is constant). Spearman(|Δ|, vol) 0.63; **Spearman(|Δ|÷vol, vol) 0.00**; Spearman(|Δ|÷√vol, vol) 0.40.
- Bars with |Δ÷v| ≥ p90 by volume tercile (low / mid / top): **35 / 42 / 40**. With |Δ|÷√v instead: 3 / 23 / 91 (it is a volume rank in disguise).
- So scaling by volume (share) is correct on NIFTY; the worry that PATLA EK-TARFA fires on tiny bars by sampling noise does not show up. SENSEX is different (§5).
- Raw |Δ| rank is largely a volume rank: Spearman(|Δ|, RVOL) 0.62 (same 442 bars).

### 1.2 RVOL by slot is mostly a day-volume flag
- Spearman(day's mean bar volume, share of the day's bars with RVOL ≥ p70) = **0.95** over 17 days. The share per day runs from **3% to 59%** (neutral 30%). Day mean bar volume runs 284–1,151 lots (4×).
- Adaptive RVOL (bar ÷ median of the previous 12 bars of the same day): per-day share 18%–44%.
- The reference itself is soft: bootstrap over reference days gives a slot-median half-width of **±30% (median over 25 slots, max ±59%)**; leave-one-day-out range of the slot median 12% (max 19%).
- On PUSH the RVOL ≥ p70 gate removes 13 of 118 |Δ| ≥ p90 bars (105 pass): it adds almost nothing there.

### 1.3 Pooled ranks are not time-of-day neutral
|Δ| ≥ pooled p90 in **18 of 101** bars at 09:15–09:44, 22/153 at 09:45–10:29, 15/202, 23/302, **10/188** at 13:00–13:59, 30/223 at 14:00–15:15 (neutral 10%). Δ÷v goes the other way (2 of 101 in the first slot). Dividing |Δ| by the same-slot median |Δ| of other days is flat across the same six slots (12 / 12 / 10 / 8 / 11 / 9% of the slot's bars in the top tenth) — and costs no new parameter. This is the flow-rank first-minutes problem in measured form.

### 1.4 The flip definition
- 498 of 1,152 bars flip sign against the previous bar. Lag-1 correlation of the 5-min delta is only **0.108** (same sign 636 of 1,139), so half of all consecutive bars "flip" by default; 151 of the 498 flips have |Δ| below the 30th percentile (37 lots).
- Flip swing = |Δ_now| + |Δ_prev| by identity when the sign changes; Spearman(|Δ|, flip) **0.75** (on the 442 bars where every metric is defined). Of 32 bars with |Δ| ≥ p90 and a sign change, 23 are flip ≥ p90. It is the delta rank counted again.
- **Flip swing appears in no state rule of the spec** (PUSH, ROKA/CLIMAX, PATLA, noise use Δ, slope/acc, RVOL, vacc, Δ÷v, price). Mary's ask was about the flip; the state machine ignores it.
- As its own row (§3.4) it does not separate from the shifted placebo.

### 1.5 Double counting and noise in slope / acceleration
- Of 118 bars with |Δ| ≥ p90: slope ≥ p90 in 49 of 104 defined, acceleration ≥ p90 in 29 of 94, flip ≥ p90 in 23 of 32. Slope has the current bar as 1 of its 3 terms (corr(slope, Δ) 0.31).
- Acceleration = slope − slope₀ is mechanically anti-correlated with the previous window: **corr(acc, slope₀) = −0.69**, corr(acc, slope) 0.60. It needs 6 bars of the day, so it cannot exist before 09:40 (146 of 1,169 bars have none); slope needs 3 (59 bars have none), so a PUSH cannot fire on the 09:15 or 09:20 bar at all (13 Oct 09:15, Δ +2,089, is "no state").
- **Sign-shuffle null** (keep each bar's |Δ| and slot, give it a random sign, 300 shuffles): p90 |slope| real 48.6 vs 42.6 (5–95%: 39.9–44.6) — the real tail is above the null; **p90 |acc| real 64.0 vs 62.3 (58.5–66.3) — inside the null**; p90 |flip| real 551 vs 629 (579–675) and flips 498 vs 560 — real flips are fewer and smaller. So slope carries some directional persistence; the acceleration tail cannot be told from random signs at this n.

### 1.6 Thresholds are fuzzier than their decimals
Day-block bootstrap (1,000 resamples of the 17 days), 5–95%: p90 |Δ| **338 [281–397]**; p90 |slope| 48.6 [36.7–62.3]; p90 |acc| 64.0 [47.1–77.4]; p90 flip 551 [471–656]; p90 RVOL 2.58 [2.20–2.92]; p90 Δ÷v 0.43 [0.41–0.45] (tight). Quote them as ranges and with N.

### 1.7 Are 5-min bars too coarse? (Upstox 1-min from ticks, 11 full days, 825 aligned bars)
- **Inside a big bar:** of 83 bars with |Δ₅| ≥ p90 (496 lots), one single minute carries ≥ 50% of the bar's |Δ| in **36**; all five minutes agree with the bar sign in 44, four in 22, three in 13, ≤ 2 in 4 (all bars: 172 / 288 / 233 / 130). Nearly half the "PUSH-sized" bars are one-minute events. BANKNIFTY: 42 of 83; 28 / 36 / 15 / 4.
- **Latency:** a rolling 5-min window stepped each minute first showed the same sign and ≥ p90 this many minutes before the grid bar closed: 4 min 29, 3 min 11, 2 min 12, 1 min 12, 0 min 19 (never inside the bar: 0). Median lead ≈ 2 minutes. (Lead 4 includes flow from the previous bar's minutes; it is a latency measure, not an arrival-time measure.)
- **Dilution:** the rolling window shows **108 p90 episodes**; **34 of them have no grid bar ≥ p90 of the same sign overlapping them** — the 5-min grid splits an event across two bars and neither crosses. BANKNIFTY: 121 episodes, 37 missed.
- **Volume is fine at 5 minutes:** all 34 bars containing a 1-min volume ≥ p99 are themselves ≥ p70 in 5-min volume. The grain problem is delta and timing, not volume.
- **The top that was named in the spec:** 16 Oct 10:15, high 23,154.6 at 10:18, **inside the 10:15–10:20 bar**. The bar closed at 23,131 (close location 0.60 of its range) after moving +1.34 slot-ranges with the delta. A bar-close state cannot see that top (§1.9).
- Recommendation: keep the 5-min bar as the unit of rank, but evaluate it **every minute on a rolling window** (candidate; costs more alerts: 108 episodes vs 83 grid bars).

### 1.8 Expiry and roll days (NIFTY GC, 17 days)
Upstox book: Sep contract to 29 Sep (expiry), Oct contract from 30 Sep; Sep OI at close 17.0 → 16.2 → 15.5 → 13.4 → 10.4 → **7.4M** (22→29 Sep), Oct 18.2M on 30 Sep. Tue weekly expiries in the sample: 22 Sep, 29 Sep, 6 Oct (13 Oct is short).

| days | bars | active-state bars (PUSH + CLIMAX_a/b + PATLA) | bars with \|Δ\| ≥ p90 |
|---|---|---|---|
| 3 Tue expiry days | 219 | 33 | 24 |
| roll week 25, 28, 29 Sep (OI falling) | 199 | 34 | 25 |
| 12 other days (29 Sep is in both rows above) | 824 | 147 | 86 |

No visible difference in frequency. **But two things need a tag, not a threshold:** (i) the expiring Sep contract after 15:00 on 29 Sep: 15:00 CLIMAX_a (Δ +2,084, R −0.70), 15:05 PUSH (+878), 15:15 CLIMAX_a (+1,171) — settlement/square-off flow, not a read; (ii) 30 Sep is the first day on the new contract (OI 7.4M → 18.2M), so a "vs other days" reference mixes two contracts' liquidity. The 15:00–15:15 bars hold 15 active bars in 56 (09:15–09:44: 9 in 101), and Mary does not trade after 15:00.

### 1.9 The spec's own hand-checked moments, re-run under the concrete rules
The spec lists 7 moments as illustrations. Under the written rules (made concrete in §2), **4 of 7 reproduce**:

| Moment | Spec reading | Rule output (LODO) | Match |
|---|---|---|---|
| 9 Oct 10:15 "sell flip" | noise | NONE (RVOL p73 ≥ p70, so not "all ≤ p70") | no |
| 9 Oct 12:00 | ROKA | CLIMAX_b (RVOL p94) | yes |
| 12 Oct 10:15 | "the real sell PUSH" | CLIMAX_a: price result R = −0.15 (the bar closed up); slope p84 and acceleration are **below p90, so it fails the spec's own PUSH rule** | no |
| 13 Oct 09:45 | PUSH ▲ | PUSH | yes |
| 16 Oct 09:35 | CLIMAX at the low | CLIMAX_a (R +0.07) | yes |
| 16 Oct 10:10 | PUSH ▲ | PUSH | yes |
| 16 Oct 10:15 | CLIMAX at the top | **PUSH** (R +1.34, RVOL 5.2): the top came at 10:18, inside the bar | no |

12 Oct 09:50 (−450, "notable single bar") → PATLA, R +2.09. The hand readings used hindsight the bar-close rules cannot have.

## 2. "Price result" defined (effort vs result)

**R = sign(Δ) × (close − open) ÷ the median (high − low) of the same 15-minute slot on the other days.** + means price moved with the delta; − means it went the other way; units are slot-typical ranges, so it is volatility-regime scaled and needs no VWAP band. "Moves with it" = R ≥ +0.25; "no result" = R < +0.25 (R < 0 shown as ulta). The 0.25 is my choice, fixed before counting; 0.0 and 0.5 are reported.

- R across all 1,169 bars: p10 −0.48, p25 −0.14, p50 +0.23, p75 +0.63, p90 +1.14; R < 0.25 in 603, R < 0 in 375.
- **The coupling is the whole story of "effort vs result":** Spearman(Δ, bar move) 0.48. R < 0 in 167 of 351 bars with the lowest-third Δ÷v, 153 of 467 in the middle, **55 of 351** in the top third.
- Of 121 bars with |Δ| ≥ p90: R ≥ 0.25 in 95, R < 0.25 in 26, R < 0 in 17.
- Untested, owed: a **rejection** term (close in the opposite 40% of the bar's range) and a **next-bar failure** term. Close location alone would not have caught 16 Oct 10:15 (0.60); only 1-min price would.
- ORDERFLOW-STUDY already warned that the 0.5U-first score mis-scores holds; level-hold is the better outcome for CLIMAX (§4 reports both).

## 3. States and outcomes (GC NIFTY, SEEN)

### 3.1 How often, and how clustered
| State (rule, in rank terms) | bars | episodes (≤ 30 min merged) | days | under sign-shuffle (100 runs, 5–95%) |
|---|---|---|---|---|
| PUSH: \|Δ\| ≥ p90, slope or acc ≥ p90 same sign, RVOL ≥ p70, R ≥ 0.25 | **39** | 25 | 13 | 14–24 (mean 19) |
| CLIMAX_a: \|Δ\| ≥ p90, R < 0.25 | **26** | 21 | 13 | 58–75 (mean 67) |
| CLIMAX_b (ROKA): RVOL or vacc ≥ p90 and \|Δ\| ≤ p70 | 61 | 42 | 17 | 61 (price- and sign-free) |
| PATLA: \|Δ÷v\| ≥ p90 and RVOL < p70 | 74 | 37 | 15 | 70–74 |
| NOISE: all of \|Δ\|, Δ÷v, slope, acc, RVOL, vacc ≤ p70 | 310 | — | — | — |
| **none of the above** | **659** | — | — | — |

- **The spec's four states leave 659 of 1,169 bars (56%) in no state**, and its "noise" row ("all ≤ p70") is never defined for the seven metrics; I named the leftover **NONE (no read)**. Rule overlap before priority: 3 bars (CLIMAX_a/b with PATLA).
- Sign-shuffle: if delta had no relation to price, **PUSH would show 14–24 bars (39 seen) and CLIMAX_a 58–75 (26 seen)**. Roughly half of PUSH bars are what random signs on the same magnitudes would give; "effort without result" is about 2.5× rarer than the null, i.e. a real, unusual event — but its direction after the fact is the question (§3.2).
- Sensitivity of the price cut: R ≥ 0.00 → PUSH 44, CLIMAX_a 17; R ≥ 0.50 → PUSH 34, CLIMAX_a 39. Without the sign requirement PUSH is 43. Per day PUSH+CLIMAX_a: 29 Sep 10, 1 Oct 10, 9 Oct 7; 0–3 on 9 of 17 days.

### 3.2 Outcomes — do PUSH bars precede continuation, do CLIMAX/ROKA bars precede turns?
Direction w = sign of the effort (sign Δ), except CLIMAX_b / VOL_other use the **prior 15-minute price move** (a high-volume small-delta bar has no delta side). WITH = price trades 0.5U in w first. Hypothesis: PUSH → WITH; CLIMAX → AGAINST. Days 22 Sep–12 Oct.

| Group | n | WITH | AGAINST | TIE | NONE/END | fwd 30 min, median in U (positive k of n) |
|---|---|---|---|---|---|---|
| **PUSH** | 38 | 22 | 13 | 0 | 3 | +0.33 (20 of 33) |
| — same bars, same w, shifted ±30/60 min | 136 | 73 | 44 | 1 | 18 | +0.25 (79 of 122) |
| BIG_other (\|Δ\| ≥ p90, R ≥ 0.25, not PUSH) | 52 | 28 | 18 | 1 | 5 | +0.21 (29 of 51) |
| **CLIMAX_a** | 25 | 13 | 10 | 0 | 2 | 0.00 (11 of 21) |
| — shifted ±30/60 min | 90 | 43 | 31 | 0 | 16 | +0.18 (44 of 74) |
| **CLIMAX_b (ROKA)** | 43 | 18 | 21 | 1 | 3 | −0.05 (18 of 42) |
| — shifted ±30/60 min | 170 | 80 | 76 | 0 | 14 | +0.12 (91 of 159) |
| VOL_other (volume spike, \|Δ\| > p70, not CLIMAX_b) | 93 | 46 | 41 | 0 | 6 | −0.03 (40 of 87) |
| PATLA | 56 | 28 | 27 | 0 | 1 | −0.06 (26 of 55) |
| — shifted ±30/60 min | 219 | 112 | 96 | 2 | 9 | +0.02 (111 of 213) |
| LOWVOL_other (RVOL < p70, not PATLA) | 561 | 257 | 268 | 4 | 32 | 0.00 (266 of 536) |
| ALL bars with a price result | 943 | 449 | 429 | 6 | 59 | +0.02 (464 of 904) |

Read plainly:
- **PUSH 22 : 13 is the same ratio as its own shifted placebo (73 : 44) and as BIG_other (28 : 18).** PUSH bars sit on trend days, where the same direction half an hour either side also went WITH-first. The extra PUSH conditions (slope/acc, RVOL) add nothing visible over "big delta that price followed".
- **CLIMAX_a: AGAINST 10 of 23 decided; CLIMAX_b: AGAINST 21 of 39 decided** — no turn above the shifted (31 of 74; 76 of 156), volume-matched (VOL_other 41 of 87) or all-bar (429 of 878) rows. n is 25 and 43 with 21 and 42 episodes.
- Power: to tell 60 : 40 from 50 : 50 at 80% power needs about **190 decided rows**; at ~1.2–1.5 episodes a day that is 130–160 sessions per state. A 30-session clock cannot separate these.

### 3.3 At a 60-minute extreme? (effort direction; added as a split before counting)
| Group | at extreme: n (WITH / AGAINST) | not at extreme: n (WITH / AGAINST) |
|---|---|---|
| PUSH | 17 (10 / 7) | 11 (5 / 3) |
| CLIMAX_a | 6 (4 / 2) | 11 (4 / 5) |
| CLIMAX_b | 20 (6 / 12) | 21 (12 / 8) |
| BIG_other | 22 (14 / 6) | 14 (9 / 2) |
| ALL | 171 (75 / 84) | 604 (305 / 252) |

CLIMAX_b at an extreme went AGAINST 12 of 18 decided (the one cell leaning the way the spec says; 20 bars; one of ~20 splits read). CLIMAX_a at an extreme: 4 : 2 WITH (6 bars).

### 3.4 Flip as its own row (added after looking)
Flip swing ≥ p90 (LODO), direction = the new bar's sign: n 47 → WITH 20, AGAINST 23, TIE 1, none 3; shifted placebo 159 → 66 / 69; flip with price following (R ≥ 0.25) 32 → 14 / 15; flip where price did not follow 15 → 6 / 8. Nothing separates it.

### 3.5 Next-bar failure (added after looking; the "causal climax" idea)
Effort bar = |Δ| ≥ p90 and RVOL ≥ p70, outcome counted from the *next* bar close, split by whether that next bar continued in the effort direction: effort + continues 53 → 28 WITH / 20 AGAINST; effort + fails 48 → 25 / 18; all bars + continues 426 → 217 / 178; all bars + fails 490 → 211 / 247. The split moves on all bars (ordinary short-term mean reversion) and not on effort bars.

## 4. Do extension marks that coincide with CLIMAX/ROKA behave differently? (the untested filter)

Winner convention as ORDERFLOW-STUDY (trap = −logged side; climax-kind has no side). Mark counts match that study exactly (era A 103/200/66/90/37/25; era B 34/64/28/56/22/17 for trap/absorption/exhaustion/initiative/vacuum/climax). The mark's bar is the GC bar starting at the mark's time (state known at its close, when the mark is drawn). 21 Sep excluded (no path). 18 era-A and 3 era-B marks have no GC bar.

**Where marks sit** (state of the bar): era A, 503 marks on a GC bar — PUSH 32, CLIMAX_a 27, CLIMAX_b 26, PATLA 22, NOISE 73, NONE 323; all 560 bars those days: 22 / 16 / 32 / 24 / 128 / 338. Era B, 218 marks: 16 / 10 / 9 / 22 / 26 / 135; all 423 bars: 22 / 11 / 13 / 34 / 93 / 250. Marks land on CLIMAX bars slightly more often than bars in general (53 of 503 vs 48 of 560; 19 of 218 vs 24 of 423), which is expected: both read the same footprint.

**Reversal-type marks (trap, absorption, exhaustion): WITH / AGAINST / TIE / none-or-end** (WITH = the mark's winner direction).

| Mark sits on… | Era A: n | WITH / AGAINST / TIE / none | Era B: n | WITH / AGAINST / TIE / none |
|---|---|---|---|---|
| CLIMAX_a or CLIMAX_b | 46 | 27 / 18 / 0 / 1 | **17** | **3 / 9 / 0 / 5** |
| &nbsp;&nbsp;CLIMAX_a only | 26 | 14 / 11 / 0 / 1 | 10 | 2 / 7 / 0 / 1 |
| &nbsp;&nbsp;CLIMAX_b only | 20 | 13 / 7 / 0 / 0 | 7 | 1 / 2 / 0 / 4 |
| PUSH | 10 | 3 / 6 / 0 / 1 | 6 | 3 / 3 / 0 / 0 |
| PATLA | 11 | 7 / 4 / 0 / 0 | 8 | 0 / 7 / 0 / 1 |
| NOISE or NONE (the "other marks") | 287 | 156 / 121 / 2 / 8 | 93 | 46 / 39 / 0 / 8 |

Both eras pooled: on CLIMAX 63 → 30 / 27 / 0 / 6; other (NOISE/NONE) 380 → 202 / 160 / 2 / 16.

- **Era A (different logic, row-size followed her zoom):** marks on CLIMAX bars 27 : 18, the others 156 : 121 — no difference.
- **Era B (the build that counts):** marks on CLIMAX bars went **3 WITH / 9 AGAINST** (12 decided, 5 unresolved) — the *opposite* of "CLIMAX lifts the marks"; the others 46 : 39. n is 17 in one cell of ~70 read; I would not lean on it either way, but there is **no sign the filter helps**.
- By kind (CLIMAX-coincident vs not, WITH / AGAINST): trap A 5/3 vs 50/39, B 0/3 vs 15/11; absorption A 20/13 vs 86/62, B 3/5 vs 25/22; exhaustion A 2/2 vs 30/30, B 0/1 vs 9/16. Initiative on PUSH: A 10/7 vs 45/22 off-PUSH, B 4/4 vs 23/20. No vacuum mark sat on a PUSH bar.
- **Coherence check:** on CLIMAX_a bars the reversal mark's winner was the side *opposite the spent delta* in 16 of 26 (era A) and **9 of 10 (era B)** — the two read the same exhaustion, as they should. They are not independent evidence.
- **Level hold** (bar extreme the winner needs, 0.25U beyond it within 60 min = BROKE): marks on CLIMAX 63 → HELD 23 / BROKE 40; other reversal marks 415 → 163 / 252.

So the filter claim is **not supported on these rows and not refuted** (era-B n = 17). A clean test needs the fixed build, ≥ 25 decided rows per cell, and the mark stamped with the state at the time it is drawn.

## 5. BANKNIFTY and SENSEX on Upstox; NIFTY GoCharting vs Upstox

**Thresholds (pooled, in-sample, 11 full days 22 Sep–8 Oct, 802 bars; lots; median / p70 / p90).** Rebuild after each close.

| Metric | NIFTY GC (17 d, spec) | NIFTY Upstox | BANKNIFTY Upstox | SENSEX Upstox (empty bars kept) |
|---|---|---|---|---|
| bar volume, median (p10) | 494 (163) | 577 (209) | 182 (53) | **11 (3)** |
| \|Δ\| | 77 / 139 / 338 | 123 / 221 / 492 | 47 / 90 / 207 | 4 / 9 / 25 |
| \|Δ÷v\| | 0.18 / 0.27 / 0.43 | 0.24 / 0.36 / 0.53 | 0.31 / 0.44 / 0.63 | 0.44 / 0.67 / 1.00 |
| flip swing | 173 / 269 / 549 | 235 / 379 / 758 | 89 / 154 / 289 | — |
| CVD slope /min | 11.9 / 21.7 / 48.5 | 20.5 / 38.5 / 79.5 | 8.5 / 15.7 / 31.3 | 0.73 / 1.5 / 3.7 |
| slope change /min | 16.5 / 29.3 / 63.0 | 24.3 / 42.9 / 90.7 | 10.9 / 18.0 / 40.7 | 1.3 / 2.3 / 5.9 |
| RVOL | 1.01 / 1.50 / 2.58 | 1.00 / 1.44 / 2.37 | 1.00 / 1.62 / 2.85 | 1.00 / 1.91 / 5.00 |
| vol acceleration | 0.88 / 1.20 / 1.94 | 0.90 / 1.21 / 1.94 | 0.86 / 1.19 / 2.08 | 0.75 / 1.43 / 3.38 |
| states LODO: PUSH / CL_a / CL_b / PATLA / NOISE / NONE | 39 / 26 / 61 / 74 / 310 / 659 of 1,169 | 24 / 27 / 42 / 49 / 233 / 427 of 802 | 24 / 23 / 34 / 49 / 220 / 452 of 802 | 22 / 41 / 30 / 122 / 222 / 365 of 802 |
| log\|Δ\|–log v slope; lag-1 corr | 0.97; 0.11 | 1.04; 0.15 | 1.02; 0.23 | 0.83; 0.09 (7-day set) |

- **NIFTY and BANKNIFTY behave alike** (Δ ∝ volume, Δ÷v independent of volume, ρ 0.04 / 0.02) and their RVOL has the same day-volume problem (per-day share ≥ p70: 3–52% and 5–71%).
- **SENSEX at 5 minutes is not rankable:** median bar 11–13 lots; in the 7-day set that survives the shipped file's dropping of empty bars (501 bars), 208 are ≤ 10 lots and |Δ÷v| is exactly 1.0 in 66. 33 five-minute bars on the 11 days are empty (volume 0); the shipped file's non-empty bars leave only 7 days with ≥ 70 bars, so the table above keeps the empties (11 days). Ranks are lattice values. At **15 minutes**: median 42 lots (p10 9), |Δ| 10 / 22 / 51.8, |Δ÷v| 0.33 / 0.49 / 0.73, exactly 1.0 in 7 of 275. Read SENSEX on 15-minute bars with a ≥ 30-lot floor, or not at all.
- NIFTY 15-min for scale: Upstox |Δ| 294 / 578 / 1,342, BANKNIFTY 131 / 238 / 524.

**GC vs Upstox, NIFTY — same 771 bars (11 days), GC prices injected into both, each ranked against its own source on the same reference days.**
- Bar delta: Pearson 0.69; **sign agrees in 543 of 766** non-zero bars; volume Pearson 0.93, median ratio 1.000. Median per-day offset (Upstox − GC) −4,726 lots; per-day correlation over days 0.16 / 0.59 / 0.94 (min / median / max). Upstox |Δ| runs ~50% larger than GC on the same bars (medians 123 vs 81), so thresholds do not transfer. fromTicks=True GC rows: sign agreement 442 of 624; backfilled rows 101 of 142.
- Single metric (both flag / GC only / Upstox only): |Δ| ≥ p90 **43 / 38 / 39**; |Δ| ≥ p70 143 / 91 / 95; Δ÷v ≥ p90 25 / 53 / 58; slope ≥ p90 37 / 38 / 42; acc ≥ p90 42 / 30 / 28; **RVOL ≥ p70 216 / 11 / 18** (volume agrees; delta does not).
- The spec's both-sources rule (both ≥ p70, same sign): of 81 GC |Δ| ≥ p90 bars, 61 pass; of 82 Upstox, 50 pass.
- **State agreement:** same state in 504 of 771 bars, but that is the NONE/NOISE bulk. Where GC is in an active state (PUSH/CLIMAX/PATLA, 127 bars): Upstox in the same state 56, another active state 10, NOISE/NONE 61. GC PUSH 25 → Upstox PUSH 9 (same direction 9), CLIMAX 2, NONE 14. GC CLIMAX 57 → Upstox CLIMAX 34. PATLA 45 → 13. Active-state rows should be shown **per source**, and "both agree" is the strict version.

## 6. What is missing, what to drop, and the candidate spec text

**Missing**
1. A written **price result** (done in §2) with a rejection term and a next-bar failure term, tested on 1-min price; today CLIMAX at a top cannot be seen from a bar close.
2. A **"no read" state**: 56% of bars are neither PUSH, CLIMAX, PATLA nor noise, and the flip the ask began with feeds no state.
3. **Location** (VWAP σ ring, level, OI front): a CLIMAX in mid-range and at a 60-min extreme are different events; the only cell that leaned the spec's way was at an extreme (§3.3, 20 bars).
4. A **time-of-day-neutral size rank** and a **day-volume-adjusted RVOL**.
5. **Contract tags**: expiring-contract close, first day on a new contract, roll week.
6. **Forward logging of the state row** (inputs, ranks, R, state, source, 1-min-step version). Every table here needed a path reconstruction; the study cannot be redone cleanly without the row logged at the time.

**Drop (on this sample; each is a prereg candidate, not a deletion)**
- **Flip swing as a state input** (identity with \|Δ\|; no state uses it; its own row is flat). Keep it as a display fact.
- **Acceleration (slope change)** as a PUSH alternative (inside the sign-shuffle null; −0.69 with the old window; blind before 09:40).
- **Volume acceleration** next to RVOL (Spearman 0.55); keep one volume measure, the adaptive one.
- **PATLA EK-TARFA as a state** (74 bars, 28 : 27 WITH/AGAINST, same as the LOWVOL comparator). Keep "one-sided but light" as a chip.
- **The RVOL ≥ p70 gate and the slope/acc condition inside PUSH** (PUSH 22 : 13 vs BIG_other 28 : 18); keep slope-same-sign as a chip.
- **Vacuum and exhaustion-on-trend-days** stay dropped (ORDERFLOW-STUDY §4.3); nothing here changes that.

**Candidate spec text — replaces the "Rate of change and volume" paragraph's state table (SEEN, provisional, no gate until a dated prereg).**

> **Rate of change and volume — FLOW STATE (candidate).** A delta, a CVD move or a flip is judged by **how big it is against normal, whether price followed, and the volume behind it** — never by its level. The unit is the last 5 minutes **re-evaluated every minute** (rolling), per index and per source (GoCharting and Upstox are ranked apart, leave-one-day-out, rebuilt after each close; every threshold shows its day-bootstrap range and N). SENSEX is read on 15-minute bars with a ≥ 30-lot floor.
>
> | Number | Definition | NIFTY GC normal (median / p70 / p90) [M] |
> |---|---|---|
> | SIZE | \|Δ\| lots ÷ the same-slot median \|Δ\| of other days (first 30 min ranked on their own slots) | rank, not lots |
> | SHARE | \|Δ\| ÷ volume — scale-free (log-log slope 0.97) | 0.18 / 0.27 / **0.43** [0.41–0.45] |
> | RVOL | bar volume ÷ median of the previous 12 bars today; beside it the same-slot RVOL, which tracks day volume (ρ 0.95) | 1.0 / 1.5 / **2.6** [2.2–2.9] |
> | RESULT R | sign(Δ) × (close − open) ÷ the same-slot median bar range | − means price went against the delta |
> | RUN | Δ over the last 15 min, same sign as the bar? | chip, not a gate |
>
> | State | Rule (ranks) | Meaning |
> |---|---|---|
> | **PUSH ▲/▼** | SIZE ≥ p90 **and** R ≥ +0.25 | big delta, price followed |
> | **CLIMAX** | SIZE ≥ p90 **and** R < +0.25 (R < 0: *ulta*) | effort without result: a turn warning, direction not yet shown by the rows |
> | **ROKA** | RVOL ≥ p90 **and** SIZE ≤ p70 | volume without delta: absorption-type |
> | **noise** | SIZE, SHARE, RVOL all ≤ p70 | ignore |
> | **no read** | every other bar | *not* noise; absence of a state, said so |
>
> Chips, never states: **EK-TARFA** (SHARE ≥ p90 on RVOL < p70), RUN, flip swing (shown as "−X → +Y", not ranked). **Thin gate:** volume ≤ p10 of the slot cannot be PUSH or CLIMAX. **Sources:** a state is shown when both sources agree; otherwise "sources disagree" (GC and Upstox deltas disagree on sign in 223 of 766 bars; Upstox \|Δ\| runs ~50% larger). **Tags, not suppression:** expiring contract after 15:00 on expiry day; first day on a new contract; roll week. **A missing input is "cannot compute", never noise.** States make **no claim about the next move**: PUSH 22 : 13 WITH/AGAINST sits at its own shifted placebo (73 : 44); CLIMAX 13 : 10 and ROKA 18 : 21 sit at theirs. Each state logs its row (inputs, ranks, R, source) so the rows can be counted forward.

## 7. Prereg candidates (for Mary; none is a rule)
- **P-FS1 log the row:** per index, per source, every minute: SIZE, SHARE, RVOL (both), R, RUN, state, source flag, contract tag. No outcome fields.
- **P-FS2 states and comparators fixed in advance:** PUSH/CLIMAX/ROKA as in §6; comparators BIG_other, VOL_other and the shifted ±30/60 min placebo; outcome both 0.5U-first and 0.25U level-hold; a cell is read only at ≥ 25 decided rows (≈ 130–160 sessions at today's rates) — until then rows only.
- **P-FS3 marks filter:** reversal marks × state at draw time, fixed build (no era mixing), ≥ 25 decided per cell.
- **P-FS4 sources:** daily agreement counts (sign, state) as a health number; the both-agree rule scored against the single-source rows.
- **P-FS5 grain:** the every-minute rolling version against the 5-min grid, compared on lead time and episodes missed.
- **P-FS6 SENSEX:** 15-min with a lot floor, or excluded.

## 8. Limits
- All SEEN; thresholds and the spec's hand moments were built on the same 17 days. 17 days; PUSH bars occur on 13 of them; bars within a day are not independent.
- The 1-min work covers 11 full days; 9 and 12 Oct tick files have holes (12 Oct a 98-minute gap), 13 and 16 Oct are nearly empty.
- GC rows mix tick-built and backfilled bars (844 vs 325); Upstox delta is a reconstruction ([I]) and the live tick settings changed between 22 Sep and 23 Sep.
- Price-result cut (0.25), the direction of CLIMAX_b (prior 15-min move), and "episode = 30 min" are my choices. Contract tags rest on the book's expiry field and OI, not on the GC symbol (unknown).
- Nothing here is a hit rate, and nothing should be quoted as one.
