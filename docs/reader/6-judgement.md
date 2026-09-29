# 6. Judgement: the order-flow reader debate, round 4

**Role:** the judge. I took no part in rounds 1–3.
**Written:** 2026-09-29, night.
**Read in full:**
- `1-research.md`, `2-data-audit.md` and `3-current-reader-audit.md`;
- `4-design-fable.md` (Design A) and `4-design-opus.md` (Design B), both including their Rev 2 sections;
- both critiques;
- the two 1-minute candle files in `data-2026-09-29\`.

**Constraints kept:** read-only. No code edited, nothing written under `data/`, no git, no server. Scripts are in `...\scratchpad\judge\` (`v1.py`–`v5.py`).

**Tags:** as the designers use them. [M] means measured, [I] means inferred, and (h) means a hand-picked threshold. Lots = units ÷ 65.

---

## 0. The verdict in eight lines

1. **The current tool fails.** It fails 12 of 18 rubric items and 3 of the 8 gates (H3, H4, H5).
2. **Neither Rev 2 design clears every gate as written.** A is partial on H6 and H8. B is partial on H2, H5 and H6. Every partial is fixable, and §3 lists the fixes.
3. **B is the stronger base design.** Merge A's frozen ruler, heartbeat, spread-print OI check and conservative face into it.
4. **Both designers got the 29 Sep afternoon wrong at first, and so did the research's pass line (R3, and R18's OI factor).**
   - The Sep tape says "short covering, absorbed".
   - The market said "positions built long in Oct": Oct OI rose +25.7k lots [M] with price up, and combined OI rose +14.9k.
   - Both Rev 2s now say this. The rubric must be amended to match (§3, item 17).
5. **I found three data facts that no round caught.** Each changes the design:
   - **(a) Spot freezes in the closing auction.** The chain's spot was frozen at 22683.75 from 15:15:23 to 15:29:06. Every basis, convergence or synthetic-forward read after 15:15 is invalid.
   - **(b) Minute OI is batched.** On 59 of 384 Sep minutes, |ΔOI| exceeds that minute's traded volume. The worst case is −5,021 lots at 10:12:32 on almost no volume.
   - **(c) B's Rev 2 finished/unfinished rule is inverted against the ATAS source the research cites.** Its "64 of 76" problem comes from that inversion.
6. **Build order:** plumbing first (15:40, the next-month capture, feed health), then the reads, all in shadow, then the face on her word.
7. **Is it "world class"?**
   - It is **professional-grade for NSE index futures on the data a retail desk can get.**
   - It is **ahead of the western platforms on the one read Indian index traders need**: who opened, who closed and where the positions rolled.
   - It is **not world-class order flow in the Bookmap/ATAS sense** while every side is inferred from 1-second snapshots.

---

## 1. What I verified (don't trust, check)

| Claim | Who | Measured | Verdict |
|---|---|---|---|
| Sep 13:30–15:29: pts, OI | A: +46 / −10,761; B: +40 / −10,791 | +40.5 close-to-close; OI −10,791 (13:29 close → 15:29 close), −10,761 from the 13:30 close | B right; A's "+46" is a slip (A's own corrected sentence says +40) |
| Oct 13:30–15:29 | A: +68 / +25,483; B: +69 / +25,726 | +68.4 / +25,726; combined **+14,935** | Both right (window convention) |
| Day: Sep OI −26,701, Oct +58,462, combined +31,761; spread 111 → 178; rollover 60.5 → 70.9 % | both | exactly those | ✓ |
| Oct out-traded Sep in 71 of 77 five-minute bins, from 09:20 | A | 71/77; first three consecutive bins 09:20–09:30; Sep led only at 09:15, 11:10, 11:25, 12:05, 15:00, 15:25 | ✓ |
| 15:20 flush was Sep-only | both Rev 2 | Sep 22714.8 → 22616 (−99); Oct 22874.7 → 22840.4 (−34); spread 157 → 228 at 15:21 | ✓ |
| 10:07:42 print: not in the exchange candle; Oct OI mirrored it | B (candle), A (OI) | Sep candle 10:07 = 684 lots vs `vtt` 5,990. OI at 10:08: Sep +4,651, Oct +5,134. At 10:12:32: Sep −5,021 **on a frame with ΔV = 0** (48 lots in the candle) | ✓, **plus a new fact:** the 10:12 step is an OI publication artefact, not trading |
| `vtt` exceeds candle volume by 22 % | B | 16,554 lots of 74,995 (22.1 %); median 20 lots a minute; 10:07 alone is 5,306 | ✓. Hypothesis [I], one day |
| 15:00 block is a regular print | B | candle 2,245 of `vtt` 2,302 lots | ✓ |
| Oct traded 22905.5 at 15:32 while Sep held 22714–22716 | B | ✓. Note Oct's day high was 22915.3 at 12:07 | ✓ |
| Sep−spot 14.2 → −1.9; spot +56.5 over 13:30–15:29 | B | −1.9 and +56.5 reproduce. **But spot is frozen at 22683.75 from 15:15:23 to 15:29:06**, and 15:29:37 (22716.2) is the auction print. The endpoint is not a live spot | Numbers ✓; the method is invalid after 15:15 |
| B5 = 17.5 | A | 17.4 (median of 358 bars, 22–28 Sep) | ✓ (B's correction right) |
| PRIOR_B ≈ 9.8 | B | median of the per-day medians = 9.6 | ✓ (within pooling) |
| A's ULTA FLOW at 09:38–09:42 and 12:33–12:41 comes from bar attachment | B (W4) | UX quote rule 09:39–09:42 **+251** (1,205 lots); 12:34–12:41 **+352**. The −25/−423 and −217 are the pivot bars | B right |
| No bearish divergence at the 12:01 high on the corrected UX tape | B | quote-rule CVD 11:14 = 5,186; 12:01 = 6,972 | ✓. The current tool's "UX top divergence" came from the paise-tick ladder |
| UX afternoon Δ | A +8,186 | 13:30–15:29 = +8,178 | ✓ |
| Research test case (§0.1) | research | GC Δ 13:30–15:25 = **+7,483** (not ~+7,060); 19 of 24 bars positive (not 18 of 25); OI −10,791 lots = −8.9 % (not −11,385, −9.4 %) | Small slips; the direction of the read is unaffected |
| B's block rule does not flag 15:00 | A (W6) | Median lots per print is **4** per ladder level (100× = 400) but 7–8 per trade by volume. The 15:00 print is 677 lots per print | The rule is **underspecified**: it flags 15:00 under one definition of the median and not under the other |
| Finished/unfinished convention | A Rev 2 vs B Rev 2 | ATAS (S9), worked example: *"At the high: bid = 0, ask = 52. At the low: bid = 85, ask = 0."* So a finished high has **0 sold at the bid**, and a finished low has **0 bought at the ask** | A Rev 2 right on "finished"; B Rev 2's rule text inverted |
| Unfinished share at leg extremes | B: 20 of 76 two-way | My replay (δ 29.4, 1-minute close cut on the book, 6 days): **19 of 70** two-way at a 1.0-pt row, **0 of 70** at tick level | ✓, and the row is decisive |
| OI noise σ₁ = 37 lots | B | robust σ 36.3; **70 of 384 minutes beyond 3σ**; 56 % of the day's \|ΔOI\| sits in 20 minutes | ✓, but heavy-tailed (see must-fix 4) |
| GC posts are timer-driven | A (Chrome throttling) | `main.js:296` `setInterval(loop, 250)`; the post sits inside `loop` (`main.js:257`) | ✓ The timer is throttled when the tab is hidden |

**Not re-verified** (taken as the designers' own measurements, flagged as such):
- B's OFI correlations (0.47 / 0.46 / 0.40);
- A's pool efficiency percentiles;
- B's 6-day tape-agreement counts (39 agree, 5 split);
- B's end-of-day Sep OI table for 22–28 Sep.

---

## 2. Scorecard

**How to read the columns:**
- **Current tool** is what ran on 29 Sep, per the audit.
- **Design A Rev 2 and Design B Rev 2** are each design as written, replayed on 29 Sep with the data that exists: GoCharting (GC) died at 12:26, and Oct is available only from the after-close pull.
- **(self: X)** marks a self-score I lowered.

| # | Current tool | Design A Rev 2 | Design B Rev 2 |
|---|---|---|---|
| **R1** legs | **FAIL.** No leg object. `board.js legs()` is private to E, and nothing publishes legs (audit C.5). | **PASS.** δ = 2·B5 = 34.8 (verified 17.4), frozen, cut on the 1-minute close. My replay gives its 16 legs and the 12:33 box. | **PASS.** δ = 3·PRIOR_B ≈ 29.4, frozen in Rev 2. Auction states. The 12:33 range is named with sub-legs. |
| **R2** effort vs result | **FAIL.** No leg efficiency (C.2). | **PARTIAL (self: pass).** Whole 5-minute bars are attached "by close time", so the pivot bar lands in the next leg. That produces two false ULTA FLOW calls: at 09:39–09:42 UX was +251, and at 12:34–12:41 it was +352. "Absorbed" is judged against a cross-day, roll-week pool that is empty on a contract's first day. δ 34.8 lumps the 11:06–11:14 burst (+118) with the grind. | **PASS, with fixes.** UX Δ at minute resolution, per tape, pairwise, then rank with n. Defects: UX "blocks" are 1-second frames, not prints; the spot-adjusted λ uses a spot that is frozen from 15:15. |
| **R3** Δ × OI × price | **FAIL.** Nothing joins the three. Futures OI is blind all expiry week (C.1). | **PARTIAL.** The Sep five-state read is right. The market read is Oct price × OI with no Oct aggressor. The fifth state rests on the pool's p25. | **PARTIAL.** The Sep five-state read is right. The curve classes read Oct with no aggressor. Sep is scoped "closing flow". |
| **R4** expiry and roll | **FAIL.** No Oct anywhere; the flat read has no expiry rule; only the 7-day blind. | **PARTIAL.** Calendar from the dump; volume cross at 09:30 (verified); Sep-only move flag. Oct is not live. "Oct−Sep vs carry ≈ 120" is unsourced and contaminated by Sep's convergence. | **PARTIAL.** Curve classes with an Oct−spot basis and a MIXED class. Oct is not live. The basis after 15:15 uses a frozen spot. |
| **R5** absorption at a level | **PARTIAL.** The walls' lean counts (B 22600/22605, 5–7 leans) were the best base read. The A marks are single-bar, and one fired on the 10:05 block. | **PASS.** A run of ≥3 bars at a located ceiling or floor; "absorbed here", never "reversal". The run test uses closes. | **PASS.** ≥3 visits, net Δ in the zone, less than 1 BK accepted beyond it, Sep-only translation. The wording "offers refilled" over-reads OFI (see H2). |
| **R6** divergence at structure | **FAIL.** grounds compares against the day's CVD best (session-scale). Its "top divergence" came from the paise-tick ladder; the corrected quote rule shows none (verified). | **PASS.** Leg extremes only, both tapes. | **PASS.** Pivots and edge re-tests only; subsumed under absorption. |
| **R7** auction at extremes | **FAIL.** `prints.py` flags each bar and shows the flags nowhere; `decode.readBar` is dead. | **PARTIAL (self: pass after item 4).** The finished rule matches ATAS. But its new "one-sided" class is the same condition: 12:05 is both POORA and one-sided. | **PARTIAL.** The rule text is inverted against ATAS. The drawn "two-way" object is the correct ATAS unfinished. "64 of 76" is an artefact of the inversion. |
| **R8** initiative / responsive | **FAIL.** Prior levels are dead in the extension; no initiative/responsive tag. | **PASS on 29 Sep (self: partial).** Prior same-contract value; legs tagged. Blind on a contract's first day. | **PASS on 29 Sep.** Same. Blind on a contract's first day. |
| **R9** stacks as evidence | **PARTIAL.** Stacks feed grounds as evidence, but there is no leg to attach them to. | **PARTIAL (self: pass).** Evidence-only by design. As lived, GC was dead from 12:26, so afternoon stacks are CAN'T CHECK. Depends on the row size. | **PARTIAL.** Same (it self-scored partial). |
| **R10** profile shape | **FAIL.** None. | **PARTIAL.** "P at 68 %" sits on the ⅔ boundary and flips with the bin. It was then used to confirm a story the Oct data overturned. | **PARTIAL.** Names D; coarse, but not forced. |
| **R11** options side | **PARTIAL.** Named-wall OI only. The expiring series' collapse was read as positioning ("22650 PE off −36.5 %"). | **PARTIAL.** Per-strike ΔOI (cross-checked by B) plus the synthetic forward. The chain holds one expiry, so the carrying series cannot be named. | **PARTIAL.** Adopted A's read; same limits. |
| **R12** VPIN as regime | **PARTIAL.** fold's row printed a side ("SELLERS" 09:36–09:38). | **PASS.** Percentile, "shadow", never flips a read. | **PARTIAL.** Keeps fold's side word under the caption "disha nahi" (not direction). The caption contradicts the row. |
| **R13** self-calibration | **PARTIAL.** A fixed 100-lot E floor, and the flow-rank bug. | **PASS by the rubric's letter.** But its claim of "four geometry constants" is generous: I count about 20 hand-picked numbers (§3.10). | **PASS.** No lot counts; ranks with n; warm-up said. |
| **R14** persistence | **FAIL.** ZONE flipped 110 times, NEXT FIGHT 150, FLOW 33. 13 of 57 posted marks were gone on rebuild. The same print was both A and P. | **PASS.** Frozen legs, ids and states. The parity gate counts marks only, which is weak. | **PASS.** Append-only log, named reasons, pre-registered churn bars, id-level parity. |
| **R15** sequence over bars | **FAIL.** Four base Ps; in the afternoon, fold's 14 trapped and 18 released. | **PASS.** P inside a RANGE is grey, with no chip. | **PASS.** Same. It also demotes A/E/C away from the edges, which goes too far (§3.8). |
| **R16** two tapes | **FAIL.** The 68.9 % sign agreement is rendered nowhere; fold found 0 disputes. | **PASS.** Per leg and per bar; ONE TAPE from 12:26. | **PASS.** AGREE / DIFFER / SPLIT / ONE per leg. |
| **R17** day story | **FAIL.** Called a +184-point morning a "sellers' day" at the high. | **PASS.** Rev 2's day sentence includes Oct. | **PASS.** Rev 2's story includes the curve clause. |
| **R18** position frame | **PARTIAL.** Four rows exist, but FLOW reads one fight, OI reads option walls, and the rows churn. | **PARTIAL (self: pass).** VPIN is shown only as a percentile, with no WITH/AGAINST. Flow, OI and zone update per minute; gave-up is the counter-pivot break. | **PASS.** Five FLOW words, WHO as context, the zone level and the VPIN row. |
| **H1** no edge claims | **PASS.** No rates on screen. | **PASS**, but its validation appends next-leg outcomes "for the judge to read the pairs". Remove that (§3.9). | **PASS.** |
| **H2** observed vs inferred | **PARTIAL.** Tags exist in the APIs; the chart letters and the FLOW row carry none. | **PASS** (Rev 2: Δ prefix plus a legend). "OI [M]" needs the batched-OI caveat. | **PARTIAL.** "Offers refilled and bids were pulled", from L1 OFI, asserts what 1 Hz snapshots cannot see (research C4). |
| **H3** holes visible | **FAIL.** GC dead 12:26–16:08 with no alarm on TapeMap faces; the 136-lot 12:25 bar is kept forever. | **PASS.** Feed band, short bars, hollow backfill. | **PASS.** Its 15-second SILENT rule will cry wolf, but that is a false alarm, not a hidden hole. |
| **H4** warm-up | **FAIL.** The flow-rank bug; grounds and tm are blind without saying so. | **PASS.** | **PASS.** |
| **H5** as-of | **FAIL.** Marks rebuild on zoom and reload; GAVE UP is recomputed; the afternoon was rebuilt at 16:08. | **PASS.** | **PARTIAL.** The rule is right. But its own 15:40 pass-case sentence and its 15:22 CVD use GC numbers that arrived at 16:08, and Rev 2 did not correct them. |
| **H6** contract identity | **PARTIAL.** `fit.contract` pauses; `ik` is null on tape rows. | **PARTIAL.** GC's POST carries no contract until `contract` is added (A does propose adding it). | **PARTIAL (self: pass).** The same GC gap, and B never adds the contract to the POST. |
| **H7** "no read" | **PARTIAL.** QUIET was used where the read was missed. | **PASS.** | **PASS.** |
| **H8** anytime start | **PARTIAL.** Marks are not reproducible; 09:15–09:17 is absent; the 15:30 cut. | **PARTIAL (self: pass).** It claims byte-identical restarts, but it cuts on book-built closes live and on REST closes after a restart, and these differ. | **PASS.** The difference inside a restart gap is admitted and labelled. |

**Tallies:**

| | Pass | Partial | Fail |
|---|---|---|---|
| Current tool | 1 | 10 | 15 |
| Design A Rev 2 | 16 | 10 | 0 |
| Design B Rev 2 | 16 | 10 | 0 |

The two designs tie on the count. B is the better base because it wins where the read lives:
- effort attribution (R2);
- the curve classes;
- the today-only yardstick;
- id-level parity;
- the validation protocol;
- honest restarts (H8).

A wins on:
- VPIN labelling (R12);
- H2 and H5;
- restraint on the face.

**Gates:**
- The current tool fails H3, H4 and H5.
- Neither design fails a gate outright, but neither passes all eight as written.

**Generous self-scores:**
- **Design A:** R2, R7, R9, R13 (the constant count), R18, H8.
- **Design B:** H2, H5, H6, and R12 (it did not see the caption contradicting the row).

---

## 3. Adjudication of every disagreement

### 3.1 Leg segmentation

**δ: frozen, not δ(t).** Both Rev 2s agree.
- B's δ(t) moved 29 → 50 → 34.5 inside one morning. That is a ruler that re-scales the legs it is ranking.
- Freezing it at 09:15 also makes a restart trivially exact.

**Multiplier: B's K = 3 × fold's PRIOR_B (≈ 29.4), not A's 2 × B5 (34.8).**
- **It is one ruler with fold.** fold's w, θ and BK are already in B, so the reader and the hold engine speak the same unit.
- **It keeps the most informative split of the day.** My close-cut replay at 29.4 gives:
  - 11:06–11:14: +117.7 pts (the burst);
  - 11:14–11:18: −42;
  - 11:18–12:01: +88.9 pts (the grind).

  At 34.8 these merge into one +164.6 leg. That is exactly B's W8 complaint against A's "least efficient" +165 leg.
- Afternoon sub-legs multiply at 29.4 (24 legs in the day against 16). That is acceptable, because the RANGE state groups them.

**Confirmation: on the 1-minute close of a canonical minute series, not B's intra-minute price event.**
- A price-event cut needs the order of the high and low inside the minute. REST minutes, the anytime-start source, do not carry it.
- Replaying price events on the exchange candles without that order gave me 44 legs on 29 Sep, including zero-length legs at 11:10, 12:30 and 15:20.
- A close cut costs at most 60 seconds of latency.
- It is not a candle-close gate in her sense:
  - the leg is a description;
  - the invalidations she acts on (origin broken, range broken) stay **live on price**, in both designs.

**Canonical minute:** the exchange's 1-minute candle (Upstox REST, polled each minute) for price, volume and OI. The book supplies only the side (Δ) and the live price events. Live and restart then cut identically (must-fix 3).

**GC's 5-minute delta on 1-minute legs.**
- Neither "by close time" (A) nor "by majority volume" (B) is honest at a pivot.
- **Ruling:**
  - UX Δ is attached by minute, which is exact.
  - GC Δ is attached only to legs that contain two or more whole GC bars. Shorter legs read "GC: leg shorter than a GC bar", with one tape.
  - A straddling pivot bar never produces a flow-against-price word.

### 3.2 Roll and expiry with no Oct delta

**The four-case read.** Take B's classes (PURE ROLL / ROLL + BUILD / ROLL + CUT / CLOSED / MIXED) over A's (a)/(b)/(c).
- B's classes need no Oct aggressor.
- They name 29 Sep correctly:
  - 15:01–15:29: pure roll (Sep −7,972 lots, Oct +8,476, net +504, verified);
  - 13:30–15:29: roll + build (net +14,935).

**Witnesses:**
- **Combined OI:** yes.
- **Oct−spot basis (B):** preferred over A's Oct−Sep spread. On expiry day the Oct−Sep spread widens mechanically as Sep's premium dies. A's "≈ 120 carry" is unsourced.
- **Premium or basis after 15:15: CAN'T CHECK.** Spot is frozen in the closing auction (§1).

**Sep convergence:** state it as a clause ("Sep premium 15 → −2 into settlement").
- Do **not** re-base Sep's λ on spot, as B's R2.3 does.
  - That imports a cash-market move into the Sep tape's result.
  - The spot endpoint is an auction print.
- After the volume cross (A's rule: three consecutive 5-minute bins; 09:30 on 29 Sep), every Sep efficiency is scoped **"expiring, arbitrage-tied"**. Sep's low efficiency is still true of the Sep book. It is not evidence of a defender.

**Which contract carries what:** A's split is right.
- The chart, the ladder reads and her marks stay on the expiring contract, labelled.
- Positioning (R3's market sentence, and R18's OI factor) moves to the continuing contract at the cross.
- A's "Sep-only move" flag, plus B's level translation, together name the 15:20 flush and the 22723 cap as Sep-only.

**Roll window:** B's 5 sessions over A's T−3.
- B's end-of-day table (not re-verified) shows Sep OI falling 262k → 206k lots by T−2.
- The fall is already large by T−4.

### 3.3 Blocks vs spread prints

**A block is a print, not a bar.** This is agreed.
- **GC:** a ladder level's lots per trade, (b+s)/(bt+st), at or above 100× today's median lots per trade, **and** at least 25 % of its bar (h).
- **The median must be defined:** use Σlots/Σtrades. On 29 Sep the per-level median (4) and the volume-weighted figure (7–8) decide whether 15:00 qualifies.
- **UX:** a block only when V == ltq. Otherwise it is a "burst" (A's rule). B's 300-lot "UX blocks" are frames.

**A spread or roll print is a block with at least one of two witnesses:**
- it is absent from the exchange candle (B);
- the other month's OI steps by at least ½ the print within 2 minutes (A).

10:07:42 meets both. It is excluded from Δ, λ and absorption, and drawn once as "spread print, not direction".

**New rule, from the 10:12 artefact.** An OI step larger than the volume traded since the previous OI update is labelled "OI publication step", and it enters no who-state.

### 3.4 Where P/A/E/C is computed, and the zoom fix

**Root cause:** `main.js:247` (`P = new Map()` on a rowSize change). Both designs fix it the same way: detect at a fixed row, and place marks with the chart's row.

**Row: B's per-day rule**, the nearest of {2.5, 5, 10} to PRIOR_B/2 (5 on 29 Sep).
- It is the row family her marks were born and trusted in (posted rows 5 → 10 → 5 → 2 → 5).
- A's 1.0-pt reader row would change what `board.js`'s row-denominated rules fire on. Those rules are "3 rows", "2 rows" and "5:1 at a price".
- The 1.0-pt row is for the extreme read only (§3.5).

**Sequence:**
1. Freeze the row in the extension, and make TapeMap's record the authority on reload. This is A's own critique, point 10: the smaller diff.
2. Port `board.js` to TapeMap (one brain, anytime start) **last**. It is gated by event-id parity against `board.js` run **at the same fixed row** on the same bars.

**Parity:** the posted history cannot be the parity target, because it was posted at five different rows. The marks that change against what she saw are listed for her as a behaviour change, never averaged.

### 3.5 Finished vs unfinished, and the "64 of 76" problem

**The source settles it.** ATAS's worked example gives a finished high as bid 0, ask 52: nothing was sold at the bid at the top.
- The research's phrase "the losing side" is ambiguous.
- B Rev 2 read it as "buyers at a high". That inversion produced the 64/76.

**Ruling:**
- **Finished high** ⇔ sold-at-bid = 0 in the top row.
- **Finished low** ⇔ bought-at-ask = 0 in the bottom row.
- **Unfinished** ⇔ both are above 0. Only unfinished is drawn, as a dotted level labelled with its contract, and it dies at that contract's last close.
- A's extra "one-sided" class is deleted: it duplicates finished.

**Discrimination exists at a 1.0-pt row:**
- 19 of 70 extremes were unfinished in my replay (B: 20 of 76);
- **0 of 70 at tick level.**

**Why 1.0 pt is defensible (h):**
- 1.0 / 22,700 = 0.0044 % of price, which is one ES tick in relative terms (0.25 / 5,500 = 0.0045 %);
- NIFTY's 0.1 tick is ten times finer than any footprint canon assumes.

R7 stays **partial for good**, because the side at the extreme row is inferred.

### 3.6 The FLOW-row words

**Converged:** WITH / PULLBACK / AGAINST / SPLIT / CAN'T CHECK (B), plus A's sub-δ pullback size ("PULLBACK −18 of δ 29"). Changes happen only on named events.

**Two gaps both designs left:**
1. **Warm-up.** PULLBACK's "λ below today's median" is undefined until n ≥ 3. Fall back to pairwise against the last same-way leg; with no prior leg, only "no named aggressor" applies.
2. **Expiry day.**
   - Her options track spot and the continuing contract, not the expiring future.
   - After the roll cross, FLOW reads the **continuing contract's** UX Δ. That needs the `futs[1]` book (must-fix 2).
   - Without it, FLOW says "expiring tape only". It must not keep reading the Sep tape as her flow.

**Signature:** the FLOW source change amends her signed rev 6 row.
- It runs in shadow beside fold's row until she signs (B).
- A's "text change on day 1" is rejected.

### 3.7 Feed-health thresholds under Chrome's background throttling

**The mechanism.** The extension posts from `setInterval(loop, 250)` (`main.js:296`).
- Chrome throttles timers in hidden tabs.
- After about 5 minutes hidden, chained timers are aligned to roughly once a minute. That is documented Chrome behaviour, not measured here.
- On Windows, a fully covered window also counts as hidden. So "keep GoCharting in its own window" helps only if the window stays partly visible.
- **B's 15-second SILENT rule will fire, with a black band and a sound, every time the tab sits behind her broker.**

**Ruling: DEAD must come from data, not from timer silence.**
- **Bar lag:** a closed 5-minute bar not posted within N seconds of its close. N is measured in one hidden-tab session before signing, and must be ≥ 75 seconds to survive a one-minute alignment.
- **Stall:** the open bin's GC lots are under 80 % of Upstox's, and the bin is at least 60 seconds old (B).
- **Heartbeat** `{tab_visible, ctx_alive, last_tick_ms}` (A). "Hidden but alive" shows as **SLOW (tab hidden)**, not DEAD.
- **Sound** only on DEAD.
- **Worth measuring:** posting from the data callback (`onItem`) instead of the timer. Network callbacks are not timer-throttled.

29 Sep's failure was a hard stop (no posts for 222 minutes), so any of these catches it.

### 3.8 Chart objects and the colour language

**Colour: converged.**
- Blue for buyers and vermilion for sellers. Colour means side only.
- Grey for anything uncertain or demoted.
- The alarm is inverse black-on-white.
- Light mode.
- Her glyph shapes stay the same, recoloured by side.

**Objects on the GoCharting chart:** at most **10 reader objects** at once, plus her marks.
- the feed band (only when not LIVE);
- one leg strip (A's single line, instead of B's two pivot labels, because the leg table carries the pivots);
- the RANGE band;
- one breakout or trend-break marker;
- at most 2 absorbed levels;
- at most 2 unfinished extremes;
- the blocks and spread prints as they print;
- **walls restored**, at most 2 per side, with the lean count.
  - B dropped walls from its overlay table.
  - They were the audit's best base read.

**The leg table** sits under the Trade chart (both designs).

**Demotion inside a RANGE applies to P only**, as R15 asks. A, E and C at a level keep their weight: the audit graded the 14:15–14:40 A/P group RIGHT.

**PAUSE is dropped** (A). The pullback line says the same thing with one state and one threshold fewer.

### 3.9 Validation: descriptive replay, not scoring by eye

**B's protocol, plus A's determinism and regime-swap tests.** The checks:
- byte-equal replays;
- as-of stamps;
- restarts at 10:00, 12:00 and 14:00;
- churn bars;
- a 60-read misdescription audit per day;
- block and feed replays;
- swapping the dump's expiry date must move the modes.

**A's "next leg appended … the judge reads the pairs" is removed.** It is outcome-reading, the back door to the backtest that house rules 2 and 4 close.

**Shadow:**
- at least 10 sessions, and it must include the 27 Oct expiry;
- then she decides;
- the 30-session kill clock keeps running.

### 3.10 How many hand-picked numbers she signs

**A's "four geometry constants" undercounts.** I count about 20:
- 90 % completeness;
- 50 % / 3× blocks;
- a 25 % tail;
- 3-bar runs in a 12-bar window;
- 2σ√(m/5);
- pool p25;
- 60/90/30/60-second feeds;
- 20-second tick death;
- a 2δ/6-bar box;
- B5/2;
- T−3;
- the 3-bin cross;
- δ/2 edges;
- 30 % double distributions.

**B lists 11 and adds more in Rev 2.**

**Ruling: one sheet, sha256-anchored, about 15 lines. None is a lot count.**
1. K = 3;
2. the P/A/E/C row rule;
3. the 1.0-pt extreme row;
4. aggressor share 0.10, thin 0.05;
5. OI 3σ√n on batch-screened OI with a one-update tolerance;
6. block 100× / 25 %, spread witnesses ½ within 2 minutes;
7. level: zone δ/2, 3 visits, 1 BK;
8. low/easy = bottom/top third, or ½ of the last same-way leg;
9. warm-up n = 3;
10. roll window 5 sessions, cross 3 bins;
11. basis witness 2σ;
12. RANGE δ/2 and BREAKOUT δ;
13. GC short < 97 % and > 10 lots;
14. feed N and stall %: **measured**, then signed;
15. churn bars (≤ 12 auction and ≤ 20 FLOW changes a day).

### 3.11 Smaller disputes

| Dispute | Ruling | Reason |
|---|---|---|
| The book witness: OFI (B) or `absorption.py` refill (A) | **OFI**, as one number: "L1 OFI −1,986 [I] against net buying". Retire `absorption.py`'s face. | One computation on the same minute series, rebuildable from the book file. Neither may say "refilled" or "pulled". |
| Divergence chips inside a box | **B's subsumption.** | A's rule repeats the absorption read as fresh chips (13:40 and 15:22). |
| "Absorbed" yardstick | **Today only:** pairwise first, then rank from n ≥ 3. | A's cross-day pool is roll-week regime and empty on a contract's first day. That is the flow-rank lesson in a new place. |
| GC short-bar threshold | **97 % and > 10 lots** (the audit's rule), not A's 90 %. | A's 90 % misses the truncated 11:35 bar (550 of 600 lots). |
| `tape_log` revisions | Allow `rev > stored` with a `why`, append-only, **with the origin check on every rev**. | `server.py:3033` says write-once exists because "a forged bar that lands first locks the real one out". |

---

## 4. The merged design's must-fixes

Each item is a defect that must be resolved before building.

1. **The session ends at 15:40 everywhere.**
   - About 30 sites (audit §8.3): the recorder gate `chain_live.SESS_CLOSE`, `server.SESSION_END_HHMM`, `live.SESSION_END_HHMM`, the `hold.SESSION` 375-minute grid, the UI axes, and the tests.
   - The dead EOD task: last result 0x80070002 (file not found), and no FUT file since 08-25.
   - This is a live data-loss bug.
2. **Next-month capture.**
   - Poll REST 1-minute candles for the front, next and Nov contracts every minute.
   - Subscribe `futs[1]` in `full` mode during the roll window, with a contract dimension in the file names. Check Upstox's `full` subscription limit first.
   - The GC POST carries `contract`. `main.js:259` must stop collapsing `NIFTY-II` into `NIFTY`.
3. **One canonical minute.**
   - The exchange candle gives price, volume and OI, and drives the cut. The book gives Δ and live price events.
   - Each ratio uses one volume universe: Δ share on `vtt` volume, never on candle volume.
   - Without this, neither design's H8 claim holds.
4. **The batched-OI screen.**
   - Flag any OI step larger than the volume traded since the previous OI update (43 of 365 Sep updates on 29 Sep).
   - Read leg OI with a one-update tolerance at both ends.
   - Never present one minute's OI step as that minute's positioning, as in B's "−3.3k in the 15:29 minute alone" (182 lots traded in that minute).
5. **Spot freeze in the closing auction.** From 15:15 until the auction print, every spot-derived number reads **CAN'T CHECK: "cash in closing auction"**. That covers the Oct−spot basis, Sep convergence, the synthetic forward against spot, and B's spot-adjusted λ.
6. **The finished/unfinished rule follows ATAS** (§3.5). Correct `1-research.md` §A3's "losing side" sentence, B's R2.7 text, and A's duplicate "one-sided" class.
7. **Leg effort attribution** (§3.1). UX by minute; GC only on legs of two or more whole bars. This deletes A's false ULTA FLOW at 09:38–09:42 and 12:33–12:41.
8. **The block and spread-print rules** (§3.3):
   - the median defined as Σlots/Σtrades;
   - UX blocks only when V == ltq;
   - exclusion by print;
   - the "OI publication step" label.
9. **"Absorbed" is measured against today only** (§3.11). No cross-day pool in any state word.
10. **The expiring contract after the cross:**
    - every Sep number and level is labelled "expiring";
    - Sep λ is "arbitrage-tied", not "absorbed by a defender";
    - FLOW and the R18 OI factor read the continuing contract, or say "expiring tape only".
11. **Feed health from data, not from timers** (§3.7). Measure N on a hidden tab before signing. SLOW is distinct from DEAD. Sound only on DEAD.
12. **The P/A/E/C row is frozen per day** from {2.5, 5, 10}.
    - TapeMap's record is the authority on reload.
    - Any port is gated by event-id parity at the same row.
    - The behaviour changes against what she saw are listed for her.
    - Only P is demoted inside a RANGE.
13. **Wording:**
    - no "offers refilled" or "bids pulled";
    - VPIN's side is labelled "tick-rule imbalance [I]", which settles B's caption that contradicts its own row;
    - never "bullish" or "bearish";
    - A's absorption witness reads "displayed offer restored k× (cancel vs fill unknown)".
14. **B's §6 as-of breach is corrected.** At 15:40 on 29 Sep the pass-case sentence is **one tape (UX)**. The GC figures are a 16:08 revision.
15. **Validation:** remove A's outcome pairs. B's churn and misdescription bars are pre-registered. The replay set must include 28 Sep (an ordinary day) and the 27 Oct expiry.
16. **Walls go back on the overlay** with their lean count (B omitted them). Cap: 2 per side.
17. **Amend the rubric before judging the build.**
    - **R3's pass line:** "Sep: covering into expiry, absorbed on the expiring tape. Oct: positions added long (+25.7k [M], price up, basis rich). Combined +14.9k."
    - **R18's expected OI factor** for a long CE at 13:45: OI **WITH** on Oct (built long), with Sep covering as context.
    - **R7's wording**, per ATAS.
18. **The single threshold sheet** (§3.10), signed, before anything reaches her chart.

---

## 5. Build order

**Sizes:**
- **S** means about a day or less.
- **M** means 2–4 days.
- **L** means more than a week.

**Risk** is what breaks for her if the step is wrong.

| # | Step | Size | Risk | Ships as |
|---|---|---|---|---|
| **Plumbing** | | | | |
| P1 | Session end 15:40 (must-fix 1), plus repairing the EOD task. After the close, on her word. | M | **Med.** It touches recorder gates and the signed hold/fold 375-minute grids. Replay-diff hold and fold before and after. | Live (fix, not a read) |
| P2a | REST 1-minute poll of front, next and Nov candles; write `min_<contract>_<day>`. | S | Low: read-only REST, new files. | Live recorder |
| P2b | `futs[1]` full-mode subscription with the contract dimension; `contract` in the GC POST; the `main.js:259` fix. | M | Med: the subscription limit is unknown, and the file layout changes. | Live recorder |
| P3 | Feed health: server-side state from post arrival, bar lag, Upstox-volume stall and the heartbeat; the band on TapeMap faces. | S–M | Low. One hidden-tab measurement first; sound off until N is signed. | **Live band** (an integrity alarm, not a read) |
| P4 | Short-bar repair: `repair` reply, `rev` re-post, `tape_log` revisions with the origin check. | M | **Med.** It reopens the write-once door. | Live, behind the origin check |
| P5 | Batched-OI screen and CAS-freeze flags (must-fixes 4 and 5). | S | Low | Library, used by the reads |
| **Reads** (pure `reader.py`; append-only `data/reader/`) | | | | |
| R-a | Canonical minute, frozen δ, leg cut, TREND/RANGE/BREAKOUT; determinism and restart tests. | M | Low (pure function) | **SHADOW** |
| R-b | Effort vs result per leg on two tapes, minute attribution, blocks and spread prints. | M | Med (vocabulary) | **SHADOW** |
| R-c | WHO on the expiring contract, plus the curve read (classes, combined OI, basis before 15:15, the cross). | M | Med | **SHADOW** |
| R-d | Absorbed levels (with OFI), divergence at structure, unfinished extremes (ATAS, 1.0 pt), value and shape, options confirmation. | M | Low–med | **SHADOW** |
| R-e | The FLOW-row word beside fold's row, logged each minute. | S | Med (her signed row) | **SHADOW** until she signs |
| R-f | Day story. | S | Low | **SHADOW** |
| **Face** | | | | |
| F1 | Feed band on the chart, panel, DESK, float and Trade tab. | S | Low | Live, with P3 |
| F2 | Leg table and shadow toggle on the Trade tab. | S | Low | Shadow toggle |
| F3 | Freeze the P/A/E/C row in the extension; TapeMap record on reload. Show her the list of marks that change first. | S | **Med–high** (her trusted marks) | Live after she sees the diff |
| F4 | Overlay objects (§3.8). | M | Med (density) | After 10 shadow sessions including 27 Oct, **on her decision** |
| F5 | FLOW row sourced from R-e. | S | Med | **On her signature** |
| F6 | Port `board.js` to TapeMap with id-level parity. | M–L | Med | Last. Optional until parity drift or anytime start needs it |

Total: about 4–6 weeks of careful work. The first 10 sessions of shadow data start as soon as R-a lands.

---

## 6. The honest answer

**The question:** "if we build the merged design and it passes its replays, is it a world-class, professional-grade order-flow reader?"

### 6.1 What it would pass, what stays partial, and what is impossible

**It would pass:**
- R1, R2, R5, R6;
- R12 to R15, R17 and R18;
- the eight honesty gates;
- R3 and R4, from the first roll window where the next month is captured live. On 29 Sep itself they stay partial, because Oct was never recorded live and has no side.

**It would stay partial, and should say so on screen:**

| Item | Why it stays partial |
|---|---|
| R7 unfinished extremes | The side at the extreme row is inferred, and the answer depends on the (h) row. |
| R8 value context | Blind on a contract's first day, unless the next month's value is built from its captured data. |
| R9 stacks | Inferred side, and they depend on the row. |
| R10 profile shape | A coarse rule. |
| R11 options | The chain holds one expiry and 17 strikes, so the carrying series cannot be named. |
| R16 two tapes | Both "tapes" are inferred. GoCharting exists for NIFTY only, so BANKNIFTY and SENSEX are always one tape. |

**Impossible with our data, and what would move each one:**

| Impossible now | Why | What would move it |
|---|---|---|
| True aggressor side | Upstox sends about 1 Hz snapshots, and only 32 % of volume frames are single trades. GoCharting's method is undisclosed. Our two tapes disagree in sign on 31 % of bars. | An NSE tick-by-tick (TBT/MTBT) feed through a licensed vendor. The trade message names both orders, and replaying the book gives the aggressor exactly. Failing that, GoCharting disclosing its method. |
| Oct delta for 29 Sep | Never recorded. The REST candles carry no side. | Nothing, for that day. From now on, the `futs[1]` book subscription (must-fix 2). |
| Icebergs, spoofing, cancel vs fill | Market-by-price, 5 levels, about 1 Hz, and no order ids. | NSE MTBT order-level data (colocation or TBT licence). Upstox D30 depth (NSE only) would improve OFI but still cannot see orders. |
| The tick feed and individual trade sizes | Snapshot feed. | NSE TBT. |
| Time order inside a GoCharting bar | The ladder has no timestamps. | GoCharting's raw ticks recorded client-side (the extension already sees `RECEIEVEDTRADE`), or TBT. |
| Per-price and participant OI | OI is whole-contract, minute-batched. Participant OI is published end of day only. | NSE's end-of-day participant-wise OI as next-day context. Intraday, nothing. |
| Separating spread legs exactly | Spread prints mix into the tape. We have only two witnesses: candle absence and OI mirrors. | TBT with the spread contract's own trade stream. |
| The closing auction | The cash stocks are not in our feed; spot freezes. | The cash-market CAS order book for the index constituents. |
| BANKNIFTY and SENSEX footprints | No GoCharting recording for them. | A second and third GoCharting chart (SENSEX also needs BSE data). |

### 6.2 Against the professional platforms

**Bookmap, ATAS and Sierra Chart on CME give a professional:**
- an **exchange-flagged aggressor** on every trade (Sierra's rule 1, "100 % accurate");
- per-tick footprints;
- market-by-order icebergs and stop detection (Bookmap through Rithmic);
- re-aggregated tape (ATAS Smart Tape);
- full-depth heatmaps.

**On our side:**
- The design's delta, stacks, absorption and extremes are **inferences from snapshots**. On those reads it cannot match them, and it must not pretend to.
- Those platforms fed the same NSE retail snapshot data would be exactly as blind. Sierra's own documentation says its accuracy drops without 1-tick bid/ask data.

**What none of them gives:**
- **A per-leg read of delta × OI × price** that separates "the aggressor closed" from "the aggressor opened".
- **Awareness of the roll and expiry mechanics:**
  - expiring against continuing contract;
  - combined OI;
  - the basis as a witness;
  - spread prints caught by mirrored OI;
  - levels that die with their contract;
  - "Sep-only" settlement moves.
- **An honest CAN'T CHECK / feed-health grammar.**
- **Her hold-or-fold frame** in her words.

On 29 Sep that is the read that mattered. Every western tool would have shown "strong buying delta, little progress". Only this design, with Oct captured, says: Sep shorts covered into settlement while positions were built long in October.

### 6.3 One-sentence verdict

**Built and passed, this is a professional-grade reader of NSE index futures on the data a retail desk can get, better than Bookmap, ATAS or Sierra at the positioning-and-roll read Indian index traders actually need, but it is not a world-class order-flow reader in the full sense until it reads an exchange tick-by-tick feed with a known aggressor.**
