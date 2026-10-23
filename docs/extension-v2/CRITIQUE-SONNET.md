# CRITIQUE-SONNET: extension-v2 mockup, attacked before build (Mon 19 Oct 2026)

Read-only, apart from this file. No server touched. I read the three screenshots (zoomed), `NOTES.md`, `frames.json`, `build_mockup.py`, `template.html`, decode-loop spec §4/§5/§10b, ORDERFLOW-STUDY, FLOW-STATE-STUDY, REPLAY-PREREG's signal matrix, and today's extension (`overlay.js`, `panel.js`, the 4 Oct clutter audit). No win rates. Counts only.

**Added after looking (all mine, flagged [A]):**
- [A1] Same-clock rank of the futures-OI moves, from `cache/contract_NIFTY_10d.json` (9 days, 6-16 Oct, so N = 8 other days).
- [A2] A gate tally over the logged trap and absorption marks of 8, 9, 12 and 16 Oct (50 marks), re-using `build_mockup`'s own functions. Place levels = VWAP/σ bands + prior H/L/C + developing value, no strikes. The random-price base rate = every 5-min bar close on those days.
- [A3] Trap-vs-absorption pairing across all era-B days (5-16 Oct).
- [A4] Basis by day and time, from chain `spot` against the 3-min futures.
- [A5] The expiry-week carry arithmetic.
- [A6] The VPIN bucket table and a timestamp leak, found by reading `vpin_at`.
- Scratch scripts live in the session scratchpad (`oi_rank.py`, `gates*.py`), not in the repo.

---

## 0. Verdict in six lines

1. The skeleton is right: a budgeted chart, a ranked list, a plan or fold board, an honest "?" block, a before/after count, and a live TIKA/TOOTA status. The 4 Oct audit's pane (72 objects at 1 Oct 12:15; 2-7 on these three frames) becomes 3-5 objects, and no top tool ranks marks against same-clock history or says "?" this plainly.
2. **Two of the four spotted issues are confirmed outright** (FUEL, VPIN). A third (the 16 Oct high) is mostly implementation, not the studies. The fourth (basis) is honest but loud, and it has a latent expiry-week bug.
3. The mark filter is not "too strict". It is **arbitrary at the edges and wrongly built in the middle**. The p90 cut is a 2-mark cliff, and the place gate passes about two-thirds of random prices. The same 573-lot cluster is evaluated twice, once on the wrong bar's flow state, against a +2σ ring that moved up 34 pts in five minutes (23,132 to 23,166).
4. The chart's flat-line budget is spent on the least-evidenced levels (a 5-bar developing VAL, a prior low 264 pts away). Her own plan levels (trigger, kill, T1) are text only.
5. In two of three frames the 10-second test **fails for different reasons**: no action and no risk line at the low, and a bull chart against a bear list at the high.
6. The three frames are the two known extremes plus one failed-mark day. There is no boring frame, no FADE/BAITHO frame, no ROKA tint and no afternoon, so the mockup cannot show whether the screen says "nothing here" with a straight face.

---

## 1. The four spotted issues

### 1. FUEL labels tiny OI moves as positioning: **CONFIRMED, and worse than stated** [A1]
| Reading | Number | Same-clock rank (futures OI, 8 other days) |
|---|---|---|
| 16 Oct 10:25 DIN, "naye long" | OI +4,810 units since 09:18 = **+0.028% = about 74 lots** | smaller than **all 8** other days' since-open moves (their range 0.037% to 1.84%). That is BAHUT KAM, not a positioning word. |
| Same frame, last 30 / last 60 min | −32,045 (−0.19%) / −8,775 (−0.05%) | The sign **flips with the window**. |
| 16 Oct, anchored on the swing | +71,955 to the 09:36-09:39 low (price −123), then **−67,145 (−0.39%) with price +237** | The real story is short covering after fresh shorts. "Naye long" is the sum of two opposite halves. Spec §10b O3 says rallies were covering, and the screen says the opposite. |
| 12 Oct 10:30 DIN, "naye short" | +80,990 (+0.43%) since open, px −146 | 4 of 8 days smaller (about p50), noise class. |
| 12 Oct fold board, OI row (10:00 to 10:30) | 189.92L to 190.09L = +17,225 (+0.09%) | 30-min rank 3 of 8 smaller (about p37), noise. Labelled "naye short". |

- The mock itself says "OI rank bana nahi: against nahi gina" on the fold board. It then prints the same unranked word in DIN, which contradicts its own rule.
- **Fix:**
  - rank it (the spec's RANK, same clock);
  - below p70 print "OI flat" in ink as a checked absence;
  - anchor FUEL to the last swing leg, not since-open.

### 2. 12 Oct fold board says WATCH because of VPIN: **CONFIRMED** [A6]
- The registered rule (REPLAY-PREREG matrix): "VPIN: FOLD (direction-blind; only with flow against)". On 12 Oct FLOW was with the short (−354 to −296) and ZONE was theek. Under the rule the board is **HOLD**, with VPIN as an expansion-risk note.
- The mock built its own direction for a direction-blind gauge: the tick-rule net of the last 3 buckets. At 10:30 that was +3,830 on about 60k units, about 6% net. The buckets were:

| Bucket | Buy | Sell | Note |
|---|---|---|---|
| 10:23:55 | 16,800 | 3,200 | |
| 10:29:04 | 12,200 | 7,800 | |
| 10:30:22 | 2,915 | 17,085 | the freshest bucket, sell-heavy |

- The 10:30:22 bucket is **22 seconds after T**. `vpin_at` uses `sec_hm(r['at']) <= t`, which truncates seconds, so the "no data after T" claim leaks. Without it the figure is p81, not p84. The verdict doesn't change, but the self-check missed it.
- Also unregistered:
  - WATCH (1 against) and FOLD (2 against) are new, and so is the "held 3 min" condition (skipped, bars only);
  - the OI row can never count, so FOLD is reachable only through ZONE + FLOW + VPIN;
  - the FLOW rank (p46) is against **13 overlapping windows of today** (about 5 independent). That is the live "flow rank first-minutes" bug, in a new place. Rank against same-slot history (FLOW-STATE §1.3: pooled/self ranks over-flag the open, 18 of 101 bars in the first half-hour at "p90").

### 3. The 16 Oct high lost its mark: **mostly implementation; the cut itself is a display budget, not evidence**

The high is one 573-lot cluster at 23,140, evaluated twice:

| Object | Rank | Place | Flow state | Why it failed |
|---|---|---|---|---|
| 10:15 absorption | p88 of N=63 (55 prior marks below; p90 needs 57) | passes: 8.0 pts from +2σ 23,132 at 10:20 (σ 60.1, tol 15.0) | PUSH ✓ (rv12 2.98) | **rank only**, a 2-mark cliff on a pool that ignores the clock and spans days with 4x volume differences. The spec says rank within the day-part. |
| 10:20 trap, same 573 @ 23,140 | p96 of N=32 | 25.6 pts from +2σ, tol 17.4 (σ now 69.6) | "noise" | place fails because σ grew **60.1 to 69.6 in 5 minutes** (+16%) on the spike itself and pushed +2σ up 34 pts, and flow is read on the confirmation bar (10:20), not the cluster's bar (10:15, PUSH). |

- **Pairing is systematic [A3].** In era B (5-16 Oct), **26 of 34 traps** have an absorption within 10 pts in the previous bar, and **24 of 34** have identical size and price. A trap is the confirmation of the previous bar's cluster. The mock ranks them in separate pools and lists both. On 16 Oct both the low (22,915) and the high (23,140) are such pairs. ORDERFLOW-STUDY §4.5 already said to merge them.
- **The σ ring drifts.** The B print (606 @ 23,100) was at +2σ at 10:15 (σ 50.4, VWAP about 22,999). By 10:25 the same price is **+1.06σ** (σ 69.6, VWAP 23,026), with no price move.
  - The chip claims "+2σ" and the +2σ line now sits at 23,166.
  - "At a place" must be frozen at birth ("+2σ @10:15") or tested on the bar's reach.
- **The low was caught by luck.** The same 657/656-lot cluster printed at 22,915 and 22,908. The twin 7.1 pts from −2σ passed (tol 9.0). The one 14.0 pts away failed. One mark is drawn and one dies on a 5-pt difference.
- **Gate tally [A2], 50 marks on 8/9/12/16 Oct (about 1 per day pass):**

| Gate | Marks passing | Note |
|---|---|---|
| BIG (≥ p90) | 7 of 50 | p80-89 holds 5 more |
| At a place | 36 of 50 | random 5-min closes pass **132 of 199** (66%); marks 72%. 27 pass on a σ band; 9 pass **only** via prior-day or developing-value levels (the placebo class). |
| Flow state active | 15 of 50 | |
| All three | **4 of 50** | 9 Oct x3, 16 Oct x1. 8 and 12 Oct: 0. |
| BIG + place | 4 | the flow gate removes none of these four; it is not what binds here |

- **Is the p90 cut too strict?** No, and moving it is no better evidenced. A p80 cut gives 6 instead of 4 over 4 days (+0.5 per day). The studies found the marks near the information-free baseline as a stream (era B WITH/AGAINST: trap 15/14, absorption 28/27). Only one of the three gates has any study behind it, and the study that tested the flow gate found 3 WITH / 9 AGAINST on era-B marks sitting on CLIMAX bars.
- **Nothing in the studies justifies keeping "the 16 Oct high".** Era B caught 4 of 13 day extremes at 10 pts (6 of 13 at 20 pts); 16 Oct supplies two of the 13, the low at 10 pts and the high only at 20. What I would change, with no fitting to one day:
  1. one cluster = one object (absorption→trap merged), the gates run once on the **cluster's bar**;
  2. place = "the cluster's bar **reached** the ring" (her rule: reaching d2 IS the event), band values frozen at the cluster's close, chip stamped "+2σ @10:15"; prior-day and developing-value levels are removed from the gate;
  3. rank within day-part, N shown;
  4. two display tiers rather than one cliff: BADA (≥ p90) = glyph + chip; notable (p70-89) at a place = a small hollow glyph, no chip. Cost: 6 hollow glyphs over 4 days (about 1.5/day); with the flow gate kept it is 2. On 12 Oct it would have shown one p79 trap that went TOOTA, and on 16 Oct the p88 absorption at the high. The cut stays pre-registered, and the ghost tier shows the cliff.
  5. flow state becomes a tag on the chip (PUSH / CLIMAX), not a gate. It describes the bar and claims nothing about the next move (§6 of the study), 50% of bars are "no read" (103 of 206 here), and the 09:50-10:20 states on 16 Oct rest on o/c filled [I] from 3-min futures.

### 4. Basis +6 on 16 Oct and the "?": **honest, but too loud and too coarse** [A4][A5]
- It does not fabricate and it says why. That follows rule 6.
- Chain-spot minus 3-min futures, median of the last 15 min:

| Day | Basis at 09:30 / 10:00 / 10:30 / ... | Note |
|---|---|---|
| 8 Oct | 47 / 53 / 55 / 52 (11:30) / 62 (13:00) / 85 (14:30) | |
| 12 Oct | 67 / 51 / 46 / 45 (11:30) / 55 (13:00) | |
| 13 Oct | 88 / 92 | |
| 16 Oct | 5 / 6.5 / -12.6 (11:30) | a negative basis on a futures that carries; the spot field was bad, not the market |

- **Too loud.** F2 prints 8 "?s" tokens plus 3 coverage lines for one cause, and F1 has "basis ?" in the head, the lines and the ? block. One banner is enough: "SPOT ?: basis +6, normal +53..+89".
- **Too coarse.**
  - FLIP's strike (23,000) is spot-native and known, but F2 drops it to a "?" line. Show the strike, with its fut position "≈ ?".
  - Fresh-writing strikes (her OI-at-levels thesis) vanish entirely ("likhna strike ?" appears 3 times across F1 and F2). On 16 Oct two frames have **no OI-at-levels content at all**.
- **The plausibility band is wrong in the final days to expiry.** [20,120] is fixed.
  - The Oct future expires Tue 27 Oct. Carry decays about 4-6 pts a day (+90 at 14 days to expiry on 13 Oct), so a **correct** basis falls under +20 around 23-27 Oct, and the mock will print "?" on good data (roll week).
  - Use a carry model ± a band, expiry-aware (carry arithmetic is mine, [I]).
- **Even good days drift.** 12 Oct fell 22 pts between 09:30 and 10:30, and 8 Oct rose 38 pts across the day. A "22,520s" label computed with the current basis on a fut-native level moves 20-40 pts intraday. That is the same drift the 4 Oct audit deleted from the old chart. Label fut-native levels' spot as "≈" with tens-rounding; keep strike-native levels exact.

---

## 2. Trader's seat: what Mary does at each frame

**F1, 16 Oct 09:40 (just after the low).**
- Decode in ≤ 10 s: yes. A at the −2σ low (p92, TIKA), FLOW CLIMAX ▼ p92 (sellers' effort without result), KHEL "?".
- Act: nothing. "09:45 se pehle zone nahi" is the registered rule (the opening drive is a known gap; the spec's DRIVE row is unregistered).
- Missing for a trader at the lows:
  - the **break level** for the mark (TIKA is a word, not a price: "tika > 22,903");
  - VWAP 22,973 and −1σ 22,937 as bounce references.
- The only two lines drawn: VAL aaj (a "value area" from **5 bars**) and KAL KA LOW as an off-chart chip **264 pts (about 7σ)** away.
- Verdict: it informs, it doesn't equip.

**F2, 16 Oct 10:25 (just after the high).**
- Head: RIDE ▲ half-size, PREM 2.98 KHARIDO (stale 09:48 IV, [I] only in the ? block). Chart: a bullish B (a 606-lot print at 23,100). List: p96 "buyers trapped ▼ @23,140 TIKA", right at price (23,145, **TIKA by exactly 0 pts**; the 3-min close 23,145 is not "more than one row" past 23,140).
- Three directions on one screen, no arbitration. **10-second test fails.** Opposing ranked evidence within a row of price must sit next to the READ.
- The plan (buy a dip to +1σ 23,096, kill VWAP 23,026, T1 23,166) is text with no live "49 pts away, not armed". PREM 2.98 after the move is complete reads as a chase.

**F3, 12 Oct 10:30 (in the short).**
- About 10 s is fine: ENTRY, KILL and T1 lines plus a four-row board.
- The verdict (WATCH) is wrong by the registered rule (§1.2).
- No "+55 in favour / T1 −21 / KILL +88" numbers.
- The three failed buyer marks (p72-79, all TOOTA) are the best news for a seller and appear as struck-through grey rows.
- The ENTRY line starts at the chart's left edge (09:15) for a trade born at 10:00.

**Frame set.** Two known extremes plus a failure day is hindsight by construction (memory: "never design off one day"). Add before build:
- three seeded-random quiet frames;
- one FADE frame (14 Oct is the only range day and has no GC data, so use another);
- one frame after 11:00 with UX present.

---

## 3. Marks

**Naming.**
- Two grammars for one idea. Trap names the **loser** ("BECHNE WALE PHANSE ▲"); absorption names the **winner** ("KHAREEDAR NE ROKA ▲"). "BECHNE WALE..." appears with opposite arrows and opposite fates ("...PHANSE ▲" up, "...NE ROKA ▼" down), so she must read the verb to read the side.
- Arrows mean two things in one panel. F1: "FLOW CLIMAX ▼" is the effort's direction; "KHAREEDAR NE ROKA ▲" on the same bar is the expected move. VPIN's ▲ is a third meaning (an invented imbalance side).
- Spelling: KHAREEDAR / KHARIDAR / KHARIDNE / KHARIDO, four spellings in one view.
- Proposal: one pattern, **arrow first**: "▲ ROKA 22,908 · kharidar", "▲ PHANSE 22,915 · bechne wale". The arrow always means expected move.
- TIKA/TOOTA are good, short words.

**Status.**
- TIKA means "not yet broken", including marks 230 pts away (the 09:40 trap is "TIKA" at 10:25). Show the break price and the distance, and dim marks more than 2σ away.
- The break test is 5 pts (0.07σ at 10:25); the study's hold test, which she used on 16 Oct, is 0.25σ. Scale it to σ like the place unit.

**Rank display.**
- "p100" with **N=6** (the B print) breaks the spec's provisional rule (N shown under 30); the chart chip omits N.
- The chip prints the percentile and never the tag word. BADA / notable / noise (the spec's tags) would make p88-vs-p92 legible; today the list shows p88 and the chart hides it with no reason.

**Tint.**
- CLIMAX is brown with no sign. F1 has two consecutive CLIMAX bars with **opposite** deltas (09:30 +696, 09:35 −656) in one colour. Add the effort sign.
- The tint ignores the two-source rule (drawn from GC alone, source untagged).
- ROKA never renders in any frame (RVOL12 needs 13 bars, so it can't exist before 10:15), so its colour is untested.

**6-chip cap.** Moot: the filter leaves 0-2 drawn marks, so the cap never binds, and the risk is now too few, not too many.

**Chart vs panel split.**
- The list is newest-first with a 4-row limit, so F2's drawn A (p92, oldest) falls off as "+1 bade upar" while a p88 non-drawn row stays.
- The "◆ = drawn" marker is not in the legend.
- Add a row-hover ring on the chart (today's overlay already has `lit`).
- Chart chips run to 49 chars ("BADA KHARIDAR 606 @23,100 · p100 · TIKA · GC only"); keep ≤ 28 on the chart and rank, N and source in the panel.
- The B/A badges sit **on** the cell whose number justifies them (the "606" cell is hidden under B). Put the glyph in the bar's gutter with a leader.

---

## 4. Lines

- **The 2/5 budget is the right idea** (13 and 12 lines to 2 in the 4 Oct audit) and the in-trade 5 is sensible.
- **The selection spends it badly.**
  - Flat F1: VAL aaj (5 bars old, 22,947) and KAL KA LOW (264 pts, about 7σ). F2: VAH aaj only. F3's fifth line: POC aaj. All are the **developing profile** (REPLAY-PREREG: CUT, "VWAP±σ already is her location") or prior-day levels (placebo, 10/22 vs 18/44).
  - The plan's trigger, kill and T1 are text only. When a plan is armed, draw those three, and say how many pts away each is.
  - Show developing value only after enough bars (not at 09:40), and never a level beyond about 3σ.
- ENTRY, KILL and the other trade lines start at the left edge, not at their birth bar (overlay.js uses birth `x0`).
- The shading is the +1σ to +2σ lane, while the plan's entry band reads "VWAP…+1σ": say which.
- Only RIDE is rendered. FADE (u2→u3 / d2→d3) and BAITHO are the likelier states on non-trend days and are untested.
- spot|fut labels: the format is right; see §1.4 for the drift.

---

## 5. Panel

- **Order** (head, DIN, ABHI, SIRF BADE, PLAN or TRADE, ?) is right. The head owns the answer.
- **SIZE is a constant** (always ADHA or "—": the day-level rank isn't built). Remove it until it can vary.
- **DIN has no ranks.** Spec §5.2's DIN carries RECORD / BAHUT KAM tags (opening CVD, CE writing, crosses). The mock's DIN is A, crosses and an unranked FUEL. That is why issue 1 slips through.
- **Prose left:** "§E" in a trader's panel ("09:45 se pehle zone nahi · §E"), and the PLAN rows fuse trigger, confirm and kill into one line ("close upar, Δ+ · KILL VWAP ..."). Use a four-cell grid: TRIGGER | CONFIRM | KILL | T1, each with live distance.
- **The "?" block is too noisy.** F1 has 6 lines, F2 has 9, F3 has 1. Three of F2's lines change what she would do: spot ?, UX gone (GC-only), READ rebuilt [I]. The rest are plumbing or repeats: "GC o/c 8 bars", and "HVN/LVN ?" is a coverage note on a feature that is not shown, and it appears in **all 3 frames**. Duplicate "?" appears in the head and the ? block.
- **The three absences collapse.** CLAUDE.md rule 6 and today's panel.js keep "checked, found nothing" (ink), "could not check" (grey italic + reason) and "not shown" (grey) apart. The mock has one grey "?" list, and "09:45 se pehle" (a rule, not an inability) is mixed in with real gaps.
- **Not tagged [M]/[I] inline:** PREM (IV 09:48, [I]), FUEL, the filled-o/c R behind the B mark.
- **Missing vs the spec:** the cross-index line (BANKNIFTY/SENSEX; the panel is NIFTY-only), and the expression (CE kharido / PE becho) under PLAN (memory: both ways).

---

## 6. What the top tools have

| Feature (ATAS, Bookmap, Sierra, Quantower) | Fits her method? | In the mock? | Call |
|---|---|---|---|
| Big-trade bubbles at print time, sized by lots | Yes (her BADA PRINT, the 198K/300K misses) | A bar-level B, ranked against **N=6**; no use of GC's trade counts (`bt/st` per level, "1 trade vs many") | Could: bubble at the print time, flagged by lots per trade |
| Developing VA / POC | Evidence says no | Drawn: VAL aaj (F1), VAH aaj (F2), POC aaj (F3) | Cut (§4) |
| Imbalance / stacked imbalance | GC already draws it; row-size dependent (CUT in the study) | No | Skip |
| Alerts | **Yes, essential** | **None defined** | Must: a short list (§8) |
| Replay | Yes, after close | Every frame is "as of T" from the same code | Could: expose `?at=HH:MM` |
| Opening range / IB, gap vs yesterday's value | Yes (spec §10b O2/O5, "I'll miss the drive") | No 09:45 day card | Should |
| Cross-instrument strip | Yes (spec §5.2, 9 Oct BANKNIFTY miss) | No | Should |
| DOM / heatmap | GC has no depth | No | Skip |
| Open P&L / R in a trade | Partly (she posts, no order path) | Lines only, no numbers | Should: pts to T1/KILL |

- **Where it already beats them:**
  - rank-vs-history with N and "BAHUT KAM";
  - fut|spot tags for an Indian futures chart;
  - TIKA/TOOTA revisits a mark live (top tools draw a signal and forget it);
  - a ledger of what was suppressed, with reasons;
  - a 2/5 object budget (ATAS and Bookmap tend to clutter).
- **Intrabar.** Bar-close marks are late. The 16 Oct top was inside the 10:15 bar (10:18), invisible until the bar closes (FLOW-STATE §1.7: a rolling 1-min read leads by a median of 2 min and 34 of 108 episodes split across bars).

---

## 7. Feasibility inside the extension on GoCharting

- **Draw cost: trivial.** `overlay.js` clears and redraws every `requestAnimationFrame`. The mock adds at most about 6 chips, about 30 tint strips, 5 lines and a per-bar shading polygon, under about 60 primitives. Panel DOM is already patched per block.
- **The real risks:**
  - The price/time **fit** from the `fillText` hook: when it is lost, all price-anchored layers hide. The mock shows no "fit lost" state.
  - The GoCharting timeframe must be 5m; marks are bar-close and appear up to 5 min after the event.
  - The extension reload orphans the relay (memory: 16 Sep), and a GC tab that is not open means no marks at all (GC coverage: 13 Oct 9 bars, 14-15 Oct none, 16 Oct to 11:10).
- **Per-minute work:**
  - the heavy part is the reference build (leave-one-day-out ranks, rebuilt **after the close** per spec, cached);
  - live it is lookups plus a 3-min scan for TIKA/TOOTA and a 13-distance place test;
  - the fold board's few-second cadence is cheap. A frame is under 20 KB if the cells (about 36 KB per frame in the mock) are not sent, because GC draws them;
  - bound compute per request: memory says the server WEDGED on a 55 MB rewrite per POST.
- **Rolling vs grid.** Re-evaluate the flow state every minute for the **panel**, and stamp the tint on the chart at bar close, or tints flicker on the forming bar.
- **One-tool design holds:** brain in TapeMap, the page senses and draws.

---

## 8. Ranked changes

**MUST (before build)**
1. **Rank FUEL and the fold-board OI row, or delete the words.** Below p70 print "OI flat"; anchor FUEL to the last swing leg. Evidence: +0.03% (74 lots) < all 8 days; low→now −0.39% is covering (§1.1).
2. **VPIN counts only with flow against; otherwise a context chip "expansion risk p84".** Remove the invented ULTA direction and the 22-s leak. Registered rule; 12 Oct goes HOLD (§1.2).
3. **One cluster = one object.** Merge absorption→trap and run the gates on the cluster's bar. Evidence: 24 of 34 era-B traps duplicate their absorption (§1.3).
4. **Place = the bar reached the ring, with σ frozen at birth and "@time" stamped.** Drop prior-day/developing-value levels from the gate. Evidence: passes 66% of random closes; 9 of 36 passes are node-class; σ 50→70 in 10 min.
5. **Show N and a provisional tag; rank by day-part.** No "p100" at N=6. Spec §4.
6. **Put opposing ranked, TIKA evidence within a row of price next to the READ.** F2 fails the 10-second test without it.
7. **Spend the flat lines on the armed plan** (trigger/kill/T1 with live distance). Remove the developing VAL/VAH/POC lines and any level > 3σ away.

**SHOULD**
8. Hollow ghost tier for p70-89 at a place (6 glyphs over 4 days).
9. Demote the flow state from gate to chip tag, and add the effort sign to the tint.
10. Chip text ≤ 28 chars; the glyph goes in the bar gutter, not on the cell; the row-hover ring.
11. The TIKA break at σ-scale with break price and distance; dim marks more than 2σ away.
12. Arrow-first naming; one meaning for arrows; fix the KHARIDAR spellings.
13. Rebuild coverage: one basis banner, the three-absence typography, drop the HVN/LVN and GC-o/c lines, rank by decision impact, ≤ 3 lines on a bad day.
14. Basis: a carry-model plausibility band (expiry-aware, before 23 Oct), strike-native levels exact, "≈" spot for fut-native levels.
15. Fold board: OI = writers at the strike plus a rank, the "held 3 min" condition, FLOW rank against same-slot history.
16. Alerts (§8a) and the cross-index line.
17. Remove SIZE until it varies; DIN ranks per spec §5.2; show pts-to-T1/KILL in a trade.
18. Draw trade lines from their birth bar.
19. Add 3 random-time frames, 1 FADE frame and 1 afternoon frame to the mock before building.

**COULD**
20. Print bubbles at print time with lots per trade (`bt/st`).
21. A replay-as-of-T control (the code already does it).
22. The 09:45 day card (|A| and the absent side, opening-flow rank, gap vs yesterday's value).
23. An expression line (CE kharido / PE becho) under PLAN.

**8a. Alert list (≤ 4, never WATCH):** a drawn mark is born; the READ/KHEL word changes; the board reaches FOLD; the plan trigger hits (zone touched with agreeing 3-min delta). Plus a silent banner when the feed or basis is lost.

---

## 9. Limits of this critique

- The gate tally covers 4 days (8, 9, 12, 16 Oct; 13 Oct had no trap/absorption rows; 5-7 Oct excluded for pool size under 16). Place levels exclude strikes (which can only add passes), and "random price" is the bar close. Effective N is small and marks cluster within days.
- The OI ranks have N=8 (the cache starts 6 Oct), so they are provisional; the sign of the 16 Oct leg is robust, the exact percentiles are not.
- The carry/expiry band is my arithmetic ([I]), not a measured series.
- The 3-bar and 2-mark cliffs are descriptive. They say the cut is fragile, not that p90 or p80 is better.
- I did not render the mock's interactions beyond the screenshots, and I did not test TOOTA's scoring on afternoon data (none exists for 16 Oct).
