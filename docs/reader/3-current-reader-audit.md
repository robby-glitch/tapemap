# 3 - Current-reader audit: every order-flow read the tool makes today, graded on 29 Sep 2026

Role: the current-reader auditor in the order-flow reader design debate. Read-only: no code was edited, nothing was
written under `data/`, and the server was not touched.

## Sources and method

**The code as it stands:**
- the extension, `Go charting/orderflow-desk/src`;
- TapeMap, `tapemap/*.py`;
- the faces, `tapemap/ui-v2/src`.

**Live GETs, about 18:55 on 29 Sep:**
- `/api/fold/flat`;
- `/api/day/record`;
- `/api/tape`;
- `/api/data?interval=3`;
- `/api/calls`;
- `/api/board`;
- `/api/fold/record`;
- `/api/hold/trades`.

**Read-only streams of the day's files:**
- `data/frame/frame_2026-09-29.jsonl`;
- `data/tape/tape_NIFTY_2026-09-29.jsonl`;
- `data/tape/ofd_marks_NIFTY_2026-09-29.jsonl`.

**A scratch replay of `fold.State`.** It ran minute by minute over the day's recorded book, chain and VPIN rows, with the
same five prior sessions the live engine pooled. It reproduced the live `/api/fold/flat` marks exactly: 124 marks, a bucket
(BK) of 309 lots, B of about 10.5 points. So every fold row graded below is what the DESK and the extension panel showed
at that minute.

**The companion document.** `2-data-audit.md` owns the data facts: blocks, holes, the tick-unit defect and the Oct
contract. This file cites it rather than repeating it.

**Grades:**
- **RIGHT:** the right side, within about 1 bar or 15 points of the turn it names.
- **EARLY:** the right idea, more than 10 minutes or 15 points before the turn.
- **LATE:** fired after half of the move was done.
- **WRONG:** the opposite of what followed.
- **NOISE:** no bearing on the day's structure, or churn that reversed within minutes.

**Times:**
- For 5-minute GoCharting bars, the time is the bar's open (a mark at "10:05" is visible at 10:10).
- For fold, the time is the fight's end (`t1`); the time it was fixed is given where it matters.

---

## 0. The findings in brief

1. **The two data families disagree on the sign of the 5-minute delta in 23 of 74 bars (68.9% agree).**
   - The source is `/api/tape` `ux.agree.delta_sign_agree`, computed at `tapemap/ux_gate.py:93`. It is rendered nowhere; the
     only reference in `ui-v2` is a TypeScript type at `trade/tape.ts:63`.
   - The disagreement includes both of the day's turns:
     - The 09:35 low was **−25 on GoCharting but −603 on Upstox**.
     - The 12:30 flush was **−999 on GoCharting and −39 on Upstox**.

2. **Each family caught one extreme and missed the other.**
   - GoCharting's delta shows the low's exhaustion; on Upstox the CVD made a new low with price.
   - Only Upstox's CVD shows the top's divergence: `grounds.py`, 11:45–12:15, "new high 22,749 at 11:40 with CVD +3,320,
     under its 11:35 peak +3,393". The same rule on GoCharting's CVD finds nothing, because its CVD made new highs to
     12:05.
   - No read today compares the two families.

3. **The zone machine was the best reader on the day.**
   - It armed BUY on d2 at 09:27, triggered at 09:39 (level 22585.7, entry at the close 22630.5) and exited at VWAP at
     11:09.
   - It armed SELL on u2 at 11:30, triggered at 12:18 (level 22758.6, entry 22729.1) and exited at VWAP at 12:30.
   - There was no false trigger.
   - **Neither extreme rang:**
     - The buy was outside the 09:45–13:15 window (`visit.py:50`) on 1,783 frames.
     - The sell was silenced by the fade gate, "no fade · CE 22700 unwinding 10:59", on 958 frames. Ungated, it would
       have rung soft or firm.

4. **The P/A/E/C family had a mixed day.**
   - E fired on the second bar of the opening drive (09:20, 22672, 90 points above the low). By construction it cannot fire
     again on that leg (`board.js:109`), so the real exhaustion at 09:35 got no E.
   - The four base Ps (10:05–10:30, 22612–22618) said "buyers trapped" 40–65 minutes before a +83-point squeeze.
   - The best marks of the family:
     - the 11:30 E and the three 11:40 As under the top;
     - the 12:00 A at the CE 22761 row;
     - the expiry-hour As at 15:00, 15:10 and 15:15;
     - the 15:20 C.

5. **The marks are not reproducible.**
   - Two things rebuild the extension's board from scratch:
     - a change in the auto-detected row size (`main.js:247`); the posted rowSize went 5 → 10 → 5 → 2 → 5 today;
     - a reload.
   - Of the 57 events posted today (`ofd_marks_NIFTY_2026-09-29.jsonl`), 13 are no longer produced by the same extension
     from the bars it now holds (`/api/tape` `marks.ofd`, 44). All four base Ps are among them.

6. **The extension posted nothing from about 12:26 to 16:08, while the server was up from 08:55.**
   - The 12:25 bar is a truncated tick bar: 136 of 943 lots. It is kept forever over the snapshot (`session.js:27`,
     `adapter.js:142`), and the "exhaustion" at 12:25 is an artefact of it.
   - The record (the newest four events per frame, `frame.py:366`, `record_read.py:83-99`) has no event between 12:25 and
     15:05. So the Trade tab's P/A/E/C showed nothing for the whole afternoon, and her chart had no live marks.

7. **fold's flat read churns.** In 375 minutes:
   - ZONE flipped its chip 110 times;
   - NEXT FIGHT changed 150 times;
   - FLOW flipped 33 times.

   Worse, the reads are wrong or contradictory at the turns:
   - At the low (09:38–09:49), FLOW said SELLERS, "sellers won 09:36 at 22612".
   - Through the whole base (10:10–11:09), FLOW said QUIET.
   - At 12:03, FLOW said "sellers won 11:48 at 22725" while NEXT FIGHT, from the same fight, said "sellers trapped".

8. **fold's best reads:**
   - "sellers trapped" four times at the base, 10:56–11:00, 10–14 minutes before the squeeze; but they were released 3–8
     minutes later;
   - "sellers won 12:12 at 22756", the first seller win after the top;
   - "buyers trapped 22721/22728" at 12:28.

9. **Nothing joins delta, OI and price.** The supervisor's afternoon read (CVD +7,060, price +40, futures OI −11,400) has no
   detector:
   - futures OI is blind by design all expiry week (`grounds.py:55`, `frame.py:263`);
   - on the expiry day the near future's OI falls mechanically, so the read would need near-month plus next-month OI, and
     nothing subscribes to the Oct future.

10. **Duplicated concepts.** Over three different aggressor classifications:
    - "absorption" is computed six ways;
    - "trap" six ways;
    - "exhaustion" four ways;
    - "climax" three ways.

---

## A. Detector map

Data families:
- **GC** is GoCharting's footprint: 5-minute bars with per-price buy and sell lots, delta and OI. The side is a vendor
  classification.
- **UX** is the Upstox futures book. It is 1 Hz snapshots, reconstructed into fills by `ladder.py`, and every side is [I].
- **CH** is the option chain.
- **VP** is the VPIN fast buckets (the tick rule on UX frames).

Where a read shows:
- **Chart** is the GoCharting overlay.
- **Panel** is the extension panel. Since rev 6 it renders only TapeMap's `fold` and `flat`, and computes nothing
  (`panel.js:1-9`).
- **Trade** is the ui-v2 Trade tab.
- **DESK** is `/pro.html`: the Validate tab plus `/pro`.
- **Float** is the in-trade floating window: an iframe of the DESK.
- **BOARD** is the ui-v2 Board tab.
- **ANSWER** is the grounded-call chips on ui-v2 tabs (`App.tsx:167, 1417`).
- **Record** is `/api/day/record`, which the Trade and Flow tabs read.

### A.1 The GoCharting extension: board.js and its wiring (data: GC)

The engine's baseline is the median volume and median range of the last 20 closed bars, skipping the first two
(`market.js:91-99`). "Rank" means rank against the session's own values so far, with no read under 6 samples
(`board.js:18-23`).

#### Initiative
- **Code:** `board.js:82-83`
- **Definition:** a bar where \|Δ\|/vol ≥ 0.25, vol ≥ 0.7 × the median, and the body (c − o) ≥ max(2, 0.3 × the median
  range), in the delta's direction.
- **Lookback:** 1 bar against the baseline.
- **Thresholds:** fixed ratios on self-calibrated medians. Partly self-calibrating.
- **Output:** event `{initiative, side, p = open, size = |Δ|}`.
- **Shows:** posted only.
  - It is not drawn on the chart (`MARK_KINDS`, `main.js:30`).
  - The Trade tab does not draw it (`ContractChart.tsx:190`).
  - It feeds the signals event vote (`signals.py:137-173`) and BOARD's TAPE family (`board.py:316-333`).

#### Absorption, cluster form ("A")
- **Code:** `board.js:77-87`
- **Definition:** one of the bar's three biggest one-sided clusters.
  - A cluster is at least 5:1 at a price, with rows within 3 rows merged.
  - It must rank in the top 20% of the session's clusters so far and sit at or above their median.
  - The bar then closed half a row past the cluster against its side, so that side was absorbed.
  - The side is the defender.
- **Lookback:** 1 bar.
- **Thresholds:** the cluster rank and floor are self-calibrating; the 5:1 ratio is fixed; everything is in rowSize units.
- **Output:** event `{side = defender, p = cluster}`.
- **Shows:**
  - the chart's A shelf, only when placed at a level (`overlay.js:294`, placement at `main.js:126-141`);
  - the record;
  - the Trade tab;
  - `signals.CONFIRMS`;
  - BOARD's TAPE family.

#### Absorption, effort/no-result form (also "A")
- **Code:** `board.js:88-89`
- **Definition:** \|Δ\|/vol ≥ 0.25, vol ≥ the median, and \|c − o\| < dispT, so the pushing side was absorbed.
  - p is the bar's low if the push was selling, its high if buying.
- **Lookback:** 1 bar.
- **Thresholds:** as initiative.
- **Output and shows:** as the cluster form, under the same letter.

#### Vacuum
- **Code:** `board.js:90-91`
- **Definition:** \|body\| ≥ 1.5 × dispT on \|Δ\|/vol < 0.1 and vol ≤ the median ("nobody on the other side").
- **Lookback:** 1 bar.
- **Thresholds:** as initiative.
- **Output:** an event.
- **Shows:** posted and recorded, and consumed by nothing. It is not a mark kind, not in `signals.CONFIRMS`, not in BOARD's
  `TAPE_KINDS`, and not in the Trade tab's filter.

#### Climax ("C")
- **Code:** `board.js:92-93`
- **Definition:** vol ≥ 3 × the median, with both buy and sell at least 35% of it; p is the high or the low, by the close.
- **Lookback:** 1 bar.
- **Thresholds:** fixed ratios.
- **Output:** an event.
- **Shows:** the chart's C diamond, always (heavy when placed at a level); the record; the Trade tab.

#### Trap ("P")
- **Code:** `board.js:94-98`
- **Definition:** in the previous bar, a top-20% one-sided cluster sat within max(2 rows, 25% of that bar's range) of its
  high (buyers) or low (sellers). This bar closes at least 2 rows beyond it, so that side is trapped.
- **Lookback:** 2 bars.
- **Thresholds:** the cluster rank is self-calibrating; the row counts are fixed.
- **Output:** event `{side = the TRAPPED side}`. The chart paints the winner (`main.js:169` inverts it).
- **Negation:** there is no release and no negation.
- **Shows:**
  - the chart's P disc, always;
  - the record;
  - the Trade tab, which labels it "top ban sakta" or "chhota trap" (`TradeTab.tsx:216-233`);
  - `signals.CONFIRMS`.

#### Exhaustion ("E")
- **Code:** `board.js:36-54, 103-118`
- **Definition:** zigzag legs on closes, where a reversal is at least max(0.6 × the median range, 6 points). Inside a leg,
  the first bar that makes a new leg extreme with its with-leg delta at or under 60% of the leg's strongest bar so far fires
  E. That strongest bar must be at least 100 lots per 5 minutes.
- **One per leg:** `!fired`, `board.js:109`.
- **Lookback:** the leg.
- **Thresholds:** the 60% and the 100 lots are fixed. **Not self-calibrating**; `peakMin` is at `board.js:105`.
- **Output:** an event.
- **Shows:**
  - the chart's E chevron, only when placed at a level;
  - the record;
  - the Trade tab;
  - `signals.CONFIRMS`;
  - BOARD's TAPE family.

#### Walls (B/S lines)
- **Code:** `board.js:128-159`
- **Definition:** 5-point bins of net flow from 09:20.
  - A bin qualifies in the top 20% of \|net\|, with volume at or above the median and at least 2 bars of trade.
  - The holder is the side of the last two closes clear of the row.
  - A wall is "built" or "absorbed".
  - Leans are returns into the row that closed back.
  - The top three per side are kept.
- **Lookback:** the session.
- **Thresholds:** the rank is self-calibrating.
- **Output:** `walls[]` and `broke[]`.
- **Shows:**
  - chart lines with chips, and a ✕ on a broken wall (`overlay.js:184-201`);
  - TapeMap's ladder rows S and B (`frame.py:294-296`);
  - the signals wall vote.

#### Defended and trapped levels
- **Code:** `board.js:162-185`
- **Definition:** every absorption becomes a "defended" level, merged within a row with retests++. It is broken when a close
  goes a row through. Traps become "trapped" levels.
- **Lookback:** the session.
- **Output:** `B.levels`.
- **Shows:** mark placement (`heldL`, `main.js:38`); the nearest 8 are drawn as wall lines.

#### Nodes (HVN / LVN)
- **Code:** `board.js:192-201`
- **Definition:** 5-point volume bins; the top three are HVN, and a bin at or under 0.35 × the median is LVN.
- **Lookback:** the session.
- **Shows:** cut from the chart. It is ported to `prints.nodes` and served on `/api/tape` levels.

#### Band taps
- **Code:** `taps.js:17-40`, `main.js:183-186`
- **Definition:** a low or high reaching (2 − 0.15)σ of the session hlc3 VWAP (`market.js:16-36`), or a live wick at
  \|z\| ≥ 1.85.
- **Lookback:** 1 bar.
- **Output:** taps.
- **Shows:** the chart's rings (`overlay.js:220-228`).

#### Flow since a tap
- **Code:** `main.js:192-193`, `session.js` `since()`
- **Definition:** the buy and sell ticks since a tap.
- **Output:** `tapRows`.
- **Shows:** computed, and shown nowhere since the rev 6 panel.

#### Prior levels
- **Code:** `market.js:64-83`
- **Definition:** PDH, PDL, PDC, POC, VA and NPOC from the prior sessions in the page.
- **Output:** passed into `board()`.
- **Shows:** never drawn or used. `heldL` needs a side; there is no contract check. **Dead.**

#### readBar and imbalances
- **Code:** `decode.js:24-80`
- **Definition:** stacks, unfinished auctions and size class.
- **Shows:** not called anywhere in `src`. **Dead.** The live port is `tapemap/prints.py`.

#### The marking rules (main.js)
- A mark is decided when its bar closes and frozen (`main.js:164-170`).
- Its `at` is the nearest held shelf, strike or prior row within one row, or else the zone (`main.js:126-141`).
- **The freeze breaks** on a rowSize change or a settings change: `P = new Map()` recomputes the whole day
  (`main.js:247, 98`).
- A frame from TapeMap can fill in a missing `at` later (`main.js:281`).

### A.2 TapeMap reads over the GoCharting bars (data: the extension's posted bars and events)

#### tm absorption
- **Code:** `prints.py:275-280`
- **Definition:** \|Δ\| in the top quarter so far, range at or under the median so far, and the close against the delta.
- **Lookback:** 1 bar against the session so far.
- **Thresholds:** self-calibrating, but blind for the first 6 bars.
- **Output:** `/api/tape` `marks.tm`.
- **Shows:** no mark anywhere. The TypeScript type is at `trade/tape.ts:34-43`. It is counted in BOARD's TAPE family.

#### tm exhaustion
- **Code:** `prints.py:282-291`
- **Definition:** a new high or low over the previous 6 bars, with delta ≤ 0 or ≥ 0 respectively (the sign only).
- **Lookback:** 6 bars.
- **Thresholds:** the 6 bars are fixed.
- **Output and shows:** as tm absorption.

#### tm climax
- **Code:** `prints.py:293-298`
- **Definition:** volume in the top decile so far, with \|Δ\|/vol ≤ 0.15.
- **Lookback:** 1 bar.
- **Thresholds:** self-calibrating.
- **Output:** as above.
- **Shows:** not even counted, because it is not in BOARD's `TAPE_KINDS`.

#### Bar flags
- **Code:** `prints.py:52-102`
- **Definition:** diagonal stacks (3:1, at least 5 lots, a run of at least 3), unfinished high or low, and the POC.
- **Lookback:** 1 bar.
- **Thresholds:** fixed.
- **Output:** `/api/tape` bars, and ux bars.
- **Shows:** grounds FLOW, through the ux stacks.

#### GC CVD
- **Code:** `prints.py:170-181`
- **Definition:** the running sum of GC delta.
- **Lookback:** the session.
- **Output:** `/api/tape` bars.
- **Shows:** no divergence rule reads it.

#### Frame tape block
- **Code:** `frame.py:363-378`, `348-360`
- **Definition:** the newest 4 posted events, each placed with `at`.
- **Output:** `frame.tape` and the record.
- **Shows:** the record, the Trade tab's P/A/E/C, and the Flow tab.

#### Session aggressor
- **Code:** `frame.py:377`
- **Definition:** the sign of the whole session's summed GC delta.
- **Lookback:** the session.
- **Output:** `frame.tape.aggressor`.
- **Shows:** the frame. It was "buyers" from the 10:05 block onward.

#### Zone + flow `fire`
- **Code:** `frame.py:443-446, 473`
- **Definition:** the visit reached, and an absorption, exhaustion or trap within 3 × rowSize of the band edge or the
  machine's level.
- **Lookback:** the visit.
- **Thresholds:** 3 rows, which **scales with the chart zoom**.
- **Output:** `setup.fire`.
- **Shows:** the record rows, and the beep fallback.

#### Signals ballot and sound
- **Code:** `signals.py:103-240, 519-612`, `visit.py:50`
- **Definition:** four votes:
  - **wall:** a tape wall at the edge, built this visit;
  - **event:** an initiative in the pocket, or a CONFIRMS event within 3 rows of the edge;
  - **depth:** at least 5 sweeps at 1.5× the other side;
  - **OI:** never alone.
- **States:** REACHED, ARMED, LIVE, SPENT.
- **Sound:** soft or firm, only inside 09:45–13:15, only on the first visit, and fade-gated.
- **Lookback:** the visit.
- **Output:** `setup.signal`.
- **Shows:** the chart's tap ring, the extension's beep, and the record.

#### Family agreement
- **Code:** `ux_gate.py:88-96`
- **Definition:** POC within 1 row, delta-sign agreement, value-area overlap, HVN/LVN overlap, and the exact and hidden
  shares.
- **Lookback:** the session.
- **Output:** `/api/tape` `ux.agree`.
- **Shows:** **nowhere.**

#### Contract match
- **Code:** `fit.js` `contract()`, `overlay.js:139-142`
- **Definition:** GC bar OI against the Upstox ladder's OI. The marks pause on a mismatch.
- **Lookback:** 2 bars.
- **Output:** trust.
- **Shows:** the panel header ("contract ✓/✗") and a pause of the marks.

### A.3 fold.py, the rev 6 engine (data: UX fills; CH; VP; GC only to dispute a fight)

#### The units
- **Code:** `fold.py:29-50, 191-205, 251-262`
- **Definition:**
  - BK is 3 × the median 1-minute volume over at most 5 prior sessions: 309 lots today.
  - B is the median 1-minute range: about 10.5 points.
  - w = B/2 and θ = 2B.
  - The ladder tick is `LADDER_TICK = 10.0` (`fold.py:49`). This is the paise-as-rupees value that `2-data-audit.md` §3f
    calls a defect, **kept deliberately**.
- **Lookback:** the prior sessions, or the day's first 15 bars.
- **Thresholds:** "(h)", hand-picked on 22–28 Sep.
- **Shows:** `view.units`.

#### Bucket side
- **Code:** `fold.py:478-489`
- **Definition:**
  - "book" if \|b − s\|/(b + s) ≥ 0.5 and \|b − s\| > hidden + unknown;
  - "two-sided" if (\|b − s\| + hidden)/v < 0.5;
  - "price" if \|Δp\| ≥ 2B;
  - otherwise "unproven".
- **Robust to blocks:** volume booked as hidden is discounted by this rule, and the 10:05 block made no buyers' fight.
- **Lookback:** 1 bucket.
- **Thresholds:** 0.5, fixed.
- **Output:** `bk[]`.

#### Fight (run)
- **Code:** `fold.py:453-476, 490-512`
- **Definition:** consecutive buckets of the same side and source, fixed when the run breaks.
  - Progress of at least m (the median \|Δp\| per bucket) is INITIATIVE; progress above 0 but under m is PRESSING; progress
    at or under 0 is ABSORBED.
  - The winner is the aggressor, unless absorbed.
  - A price run is "won by price".
  - A fight is **disputed** if the VPIN tape or GoCharting, over the same window, is at least 0.5 one-sided the other way
    (`fold.py:496-451`).
- **Lookback:** the run (minutes).
- **Thresholds:** m is self-calibrating.
- **Output:** marks won, absorbed and disputed.
- **Shows:**
  - the Trade tab's ▲▼ and ▬ (`LevelsOverlay.ts:503-541`);
  - the FLOW row;
  - NEXT FIGHT;
  - THE DAY.
  - **Not on the chart:** `overlay.js:267` draws only FOLD.

#### Trapped and released
- **Code:** `fold.py:339-347`
- **Definition:** a fixed run is trapped when its VWAP sits at least 2B beyond a later 1-minute bar's VWAP. It is released,
  **for good** (it can never re-trap), when a bar trades back to its VWAP.
- **Lookback:** 1 one-minute bar.
- **Thresholds:** 2B, self-calibrating.
- **Output:** marks trapped and released.
- **Shows:** the Trade tab's shelves until released (`LevelsOverlay.ts:544-556`), NEXT FIGHT and ZONE.

#### Levels
- **Code:** `fold.py:515-540`
- **Definition:**
  - priority 5: prior H, L, C, POC and VA;
  - priority 6: the open and the day's high and low;
  - priority 7: today's POC;
  - fights: trapped at priority 1, held at 2, and disputed or won at 3;
  - priority 4: the named CE and PE walls.
- **Lookback:** the session.
- **Output:** `levels()`.
- **Shows:** ZONE and NEXT FIGHT.

#### Named OI walls
- **Code:** `fold.py:542-600`
- **Definition:** of the 19 strikes nearest F*, beyond F* by w, the top-2 current OI; the nearer one wins. A change must
  stand 2 bucket closes.
- **Lookback:** the chain.
- **Thresholds:** CONFIRM = 2 (h).
- **Output:** wall marks. **30 renamings today.**
- **Shows:** the Trade tab's chips, and W and A in a trade.

#### The flat rows
- **Code:** `fold.py:1162-1286`
- **Definition:** four rows:
  - **ZONE:** the strong level within w of F*, and its side;
  - **FLOW:** the winner of the newest fight fixed within the last 10 buckets;
  - **OI:** the named walls' building, stopped or off votes;
  - **VPIN:** 10 fast buckets, with a one-sided lead of at least 2.
- **Lookback:**
  - ZONE: now;
  - FLOW: 10 buckets, **one fight**;
  - OI: from 09:15;
  - VPIN: 10 buckets.
- **Output:** `flat.rows`.
- **Shows:** the panel (`panel.js:249`, `renderFlat`), the DESK and the Float.

#### NEXT FIGHT
- **Code:** `fold.py:1175-1200`
- **Definition:** the nearest strong level beyond w, above and below.
- **The "confirm" is a template:** "lifts at X…followed by price and no absorption there · VPIN turning…". Nothing in it is
  measured.
- **Lookback:** now.
- **Output:** `flat.next_fight`.
- **Shows:** the panel, the DESK, and the Trade tab's lines.

#### GAVE UP
- **Code:** `fold.py:1201-1218`
- **Definition:** a named wall off its OI peak, plus a fight won at it within the last 10 buckets.
- **Not frozen in the flat read:** the docstring says "frozen, silent", but it is recomputed every minute and drops out when
  the fight ages past 10 buckets.
- **Lookback:** 10 buckets.
- **Output:** `flat.gave_up`.
- **Shows:** the panel, the DESK, and the Trade tab.

#### THE DAY
- **Code:** `fold.py:1274-1286`
- **Definition:** a count of fights won by each side, plus the POC and value area, and "boxed" or "trending".
- **Lookback:** the session.
- **Output:** `flat.day`.
- **Shows:** the panel and the DESK.

#### In-trade only (seeded at her mark)
- **Code:** `fold.py:400, 603, 680-889`
- **Definition:**
  - acceptance past G, held and the backstop;
  - the OI event on W (3σ√n, n ≥ 3, at least 3%);
  - **TIRING:** 5 buckets with no progress by w and no win;
  - **FAILED** extreme;
  - the PULLBACK and BEHIND words;
  - FOLD.
- **The flat read computes none of these,** because it is never seeded.
- **Lookback:** buckets.
- **Output:** the view's headline, rows and events.
- **Shows:** the panel, DESK and Float headline, and on the chart ■ FOLD and the G staircase.

### A.4 UX ladder bars and the grounds family (data: UX, plus runs)

#### Fill classification
- **Code:** `ladder.py:40-51, 84-130`
- **Definition:** an exact print (V == ltq) is sided by the prior touch. Otherwise the fill is reconstructed by marching the
  attacked side, and the remainder is "hidden".
- **Lookback:** a frame pair.
- **Thresholds:** `tick × 0.55`, where the tick is 10.0 (the defect in `2-data-audit.md` §3f).
- **Output:** fills and ux bars.
- **Shows:** today 28.6% of prints were exact and 30.8% hidden.

#### CVD rank
- **Code:** `grounds.py:83-127`
- **Definition:** the 15-minute ΔCVD (3 closed ux bars), ranked against today's earlier 15-minute changes, of which it needs
  3. STRONG is at least 0.5 and ONE_SIDED at least 0.8.
- **Lookback:** 3 bars.
- **Thresholds:** self-calibrating. It is blind until about 09:40.
- **Output:** `facts.cvd`.
- **Shows:** ANSWER, BOARD, and the hold record.

#### CVD divergence
- **Code:** `grounds.py:113-121`
- **Definition:** a new day high or low within the last 3 bars, whose CVD is under its own earlier day best (or above its
  trough).
- **Lookback:** the session.
- **Output:** `div_top` and `div_bottom`.
- **Shows:** **only as text** inside ANSWER's CVD chip. It is not in the DESK, the panel or BOARD's agreement.

#### Futures-OI quadrant
- **Code:** `grounds.py:55-71, 124-142`
- **Definition:** ΔOI × Δprice over 15 minutes, both ranked at least 0.5.
  - It is **blind** within 7 days of expiry, which covers 22–29 Sep.
- **Lookback:** 3 bars.
- **Output:** `facts.fut_oi`.
- **Shows:** ANSWER.

#### FLOW (prints of size)
- **Code:** `grounds.py:143-150`, `runs.py`
- **Definition:** fill runs (3 fills at or above p90 of the last 20 minutes' sizes, at most 3 seconds apart) plus ux
  stacks, over 15 minutes. One side dominates at 2 or more and twice the other.
- **Lookback:** 15 minutes.
- **Output:** `facts.flow`.
- **Shows:** ANSWER and BOARD.

#### Aggression
- **Code:** `board.py:102-127`
- **Definition:** "pressing" or "leaning" only if the CVD is STRONG and FLOW dominates the same way.
- **Lookback:** 15 minutes.
- **Output:** a word.
- **Shows:** the BOARD headline and squares.

#### Agreement
- **Code:** `board.py:356-414`
- **Definition:** OI, CVD, FLOW, TAPE (GC and tm events over 15 minutes) and TREND, counted.
- **Lookback:** 15 minutes.
- **Output:** "n of 5".
- **Shows:** BOARD.

#### Grounded calls
- **Code:** `grounds.ground`
- **Definition:** every engine call is held against OI, CVD and FLOW, and graded CONTRADICTED, BACKED or THIN.
- **Lookback:** 15 minutes.
- **Output:** `/api/calls`.
- **Shows:** ANSWER.

#### VPIN
- **Code:** `vpin.py:11-20, 64-92`
- **Definition:** the tick rule on ltp across frames, in 60,000-unit and 20,000-unit buckets; \|b − s\|/V, as a percentile
  so far.
- **Lookback:** buckets.
- **Output:** the gauge and the fast rows.
- **Shows:** the VPIN tab, fold's VPIN row, and fold's disputes.

#### Sweeps, book absorption and λ
- **Code:** `sweep.py`, `absorption.py`, `impact.py`
- **Definition:** depth sweeps, a proof that size at the touch was replenished, and Kyle's λ.
- **Output:** senses rows, and `ux.impact`.
- **Shows:** the sweeps feed the signals depth vote. The other two have **no face.**

#### The hold.py flow family (rev 5)
- **Code:** `hold.py:155-165`
- **Definition:** the same rule as aggression.
- **Lookback:** 15 minutes.
- **Shows:** its HoldWindow and HoldTab are **unmounted** (`App.tsx:17, 1596`).

### A.5 Next to order flow (price or OI only, graded because she reads them with the tape)

#### The zone machine
- **Code:** `band_rotation.py:969-1172`, `live.py:1093-1097`
- **Definition:**
  - It runs on 3-minute futures bars against TapeMap's own session bands.
  - It ARMS on a touch of d2 (or u2) after 09:25.
  - It re-arms on each lower low; that stays one setup.
  - It TRIGGERS on a close past the reference bar's high within 10 bars.
  - It locks until VWAP or a 20-point stop.
- **No order-flow input.**
- **Lookback:** 10 bars.
- **Thresholds:** RUN_WINDOW = 10 and the 20-point stop are fixed.
- **Output:** `zone_state` and `zone_state_sell`.
- **Shows:** `frame.setup`, the record, and the Trade tab (zone3).

#### engine.py events
- **Code:** `engine.py:21-22, 831-862`
- **Definition:** option OI and premium, with futures price and volume ranks: TRAP, TRAP-SETTING and TRAP-SPRUNG, SPRING,
  PRESS, SQUEEZE, IGNITION, CLIMAX, and ABSORPTION (futures volume rank above 0.95, range rank under 0.55).
- **No delta.**
- **Lookback:** minutes.
- **Output:** `/api/data` events.
- **Shows:** the Events and Glass tabs. **The vocabulary collides** with the tape's.

---

## B. The 29 Sep scorecard

### B.1 First, the two tapes at the turns

Both columns are lots per 5-minute bar, from `/api/tape` bars and `ux.bars`.

| Bar | Supervisor's read | GC Δ | UX Δ | Note |
|---|---|---|---|---|
| 09:15 | drive from 22755 | −794 | −644 | UX starts 09:17 (partial) |
| 09:35 | the low 22580.5 | **−25** | **−603** | GC: exhaustion; UX: real selling |
| 09:40 / 09:45 | base starts | +138 / +354 | −138 / −292 | opposite signs |
| 10:05 | (block) | +4,483 | +5,389 | one 4,528-lot print, 70% of the bar |
| base 09:40–11:05 | "positive delta, no progress" | +5,739 (+1,256 ex-10:05) | +4,039 (**−1,350** ex-10:05) | "positive" is GC-only once the block is out |
| 11:10 | squeeze | +1,671 | +1,433 | agree |
| 11:35–12:05 | grind to the high | **+1,169** | **−389** | the "weak delta" is UX's |
| 12:25 | hole | −24 (136 lots) | −381 (943 lots) | GC truncated |
| 12:30 | flush | **−999** | **−39** | |
| 13:30–15:25 | CVD +7,060 | +7,483 | +4,106 (to 15:20) | same sign, 1.8× apart |

### B.2 By episode

**E1. The opening drive, 09:15–09:30 (22755 → 22625).**
- **The extension:**
  - Initiative at 09:15, sellers 22755.5: RIGHT (not drawn).
  - A at 09:20 (22690) and 09:25 (22666), sellers defending: RIGHT (continuation).
  - **E at 09:20, buyers' exhaustion at 22672: WRONG.** It came 90 points above the low. It was drawn "at S 22675", and it
    later "confirmed" the buy visit (`setup.fire` 09:31–09:34) only because rowSize was 10 at that moment, so "3 rows" was
    30 points.
  - A at 09:30, buyers defending 22628: EARLY, 48 points above the low.
  - The S walls at 22675–22690 from 09:25: RIGHT.
- **fold:**
  - Sellers won by price at 09:18, 22716: RIGHT.
  - **Sellers absorbed at 09:19, 22700: WRONG** (the drive ran another 120 points).
  - Sellers won at 09:22 (22690) and 09:31 (22647): RIGHT.
  - FLOW read SELLERS from 09:20 to 09:34: RIGHT.
- **Zone:** armed at 09:27 on d2 at 22644: RIGHT. The lower-band taps at 09:25 and 09:30: RIGHT.
- **grounds:** blind until about 09:40; it needs 3 earlier 15-minute CVD changes (`grounds.py:83-91`).

**E2. The selling exhaustion at 09:35 (22580.5).**
- **The extension:**
  - **Vacuum at 09:35, sellers, 22592: WRONG.** It is a continuation word on the exhaustion bar, and it is not drawn.
  - **No E** (spent at 09:20), and no P, A or C: MISSED.
- **tm:** blind; it needs 6 prior bars, so its first read was at 09:45.
- **fold:**
  - Sellers absorbed at 09:33 at 22631 (fixed 09:34:47): **RIGHT-EARLY.** It was the only warning, 3 minutes and 50 points
    before the low. FLOW read BUYERS at 09:36.
  - **Sellers won at 22612 at 09:36, 460 lots initiative (fixed 09:37:39): WRONG.** FLOW then read SELLERS from 09:38 to
    09:49, and VPIN read SELLERS from 09:36 to 09:38.
- **UX CVD:** made a new low with price, so there was no bottom divergence. The Upstox family says the selling was real.
- **Zone:** BUY triggered at 09:39 (d2 22585.7; entry 22630.5): RIGHT, but **silent**, because the visit was outside 09:45–13:15.
- **Tap:** the 09:35 tap at 22580.5 (−2.12σ) was followed by +51 points in 30 minutes: RIGHT.
- **Her trade:** long 22800 PE, out at 09:35:26 at 189.3 (+66%), at the low.
  - Her in-trade clause at 09:34:47, "against you: zone, flow", was the correct warning.

**E3. The base, 22590–22640, from 09:40 to 11:05.**
- **The extension:**
  - A at 10:00 (22618) and at 10:05 (22615, the 4,483-lot block, "absorbed"), sellers defending: WRONG.
  - **P at 10:05 (22618), 10:10 (22616 and 22612) and 10:30 (22618), buyers trapped: WRONG.** They sat in the base 40–65
    minutes before +83 points. All four are gone from the rebuilt board.
  - E at 10:40 (22629) and the vacuums at 10:45 and 10:50: NOISE, and not drawn.
  - Initiative at 11:00, sellers: NOISE.
- **The walls:**
  - B 22595 from 09:40, with 3 leans by 10:30.
  - **B 22600 and 22605 from 10:25, with 5–7 leans by 11:05: RIGHT.** This was the best base read in the tool.
- **tm:**
  - A at 09:45 (22629.5) and at 10:05: WRONG.
  - **E at 11:05, "new low 22600.3 over 6 bars on delta +92: sellers did not come": RIGHT.** It came 5 minutes before the
    squeeze, and it is **shown nowhere.**
- **fold:**
  - Sellers won at 09:45 (22625), 10:02 (22614) and 10:07 (22607): WRONG (sellers "winning" a base).
  - Sellers absorbed at 09:50 (22611): RIGHT.
  - **Sellers trapped four times at 10:56–11:00 (22607–22614): RIGHT-EARLY.** Released at 11:02–11:04: NOISE, 6 minutes
    before the squeeze.
  - **FLOW read QUIET from 10:10 to 11:09** ("no fight in the last 10 buckets"): the accumulation was MISSED.
- **The frame's aggressor** turned "buyers" at 10:05 on the block, and stayed that way all day: NOISE.
- **The signals state** flickered ARMED, LIVE and SPENT more than 20 times as the OI vote toggled.

**E4. The squeeze at 11:10 (+83).**
- **The extension:** initiative at 11:10, 11:25 and 11:30, buyers: RIGHT. The first is late by construction (visible at
  11:15), and none is drawn.
- **fold:**
  - Buyers won by price at 11:10 (fixed 11:10:33): RIGHT.
  - Sellers trapped at 22631, 22625 and 22647 at 11:11–11:12: RIGHT.
  - FLOW read BUYERS from 11:12: RIGHT.
  - **GAVE UP**, "SELLERS GAVE UP AT 22703 · 11:14", was on screen **only 11:28–11:29**: right, but 14–18 minutes late, and
    it flashed for 2 minutes.
- **grounds:** "leaning" at 11:15–11:20 and "pressing" at 11:25: LATE.
- **engine.py:** SQUEEZE-RELEASE UPWARD at 11:12 was RIGHT; "BEARISH SPRING / BULL TRAP SETTING" at 11:12 was WRONG.
- **Tap:** the upper-band tap at 11:10 (22717.9): EARLY, since +47 points followed.

**E5. The grind to the high, 22764.5 at 12:05, under PDL 22793 and the 22800 CE.**
- **The extension:**
  - **E at 11:30 (22746, "in the sell zone"): EARLY**, 35 minutes and 18 points before the high, but in the right zone.
  - **A at 11:40 at 22735, 22740 and 22749, sellers defending: RIGHT-EARLY.**
  - **A at 12:00 at 22760, "at CE 22761": RIGHT** (the top bar).
  - A at 12:05 at 22750, buyers defending: WRONG (posted once; gone from the rebuilt board).
  - Initiative at 12:00, buyers: LATE.
  - `setup.fire` from 11:35 and the event vote from 11:45 to 12:04 (the 11:30 E and the 11:40 As): RIGHT.
  - The S wall at 22735 with 3 leans at 12:05: RIGHT.
- **grounds (UX):** **the CVD divergence from 11:45 to 12:15: RIGHT-EARLY.** It was the best top read in TapeMap, and it
  appears only as text in ANSWER. On GC's CVD the same rule is silent.
- **fold:**
  - Sellers won at 11:48 (22725), so FLOW read SELLERS from 12:00 to 12:08: RIGHT.
  - **Sellers trapped at 22731 and 22725 at 12:02: WRONG**, 3 minutes before the top. NEXT FIGHT below read "379 lots of
    sellers trapped" **while FLOW said "sellers won"**.
  - NEXT FIGHT above, 22793 "yesterday's low": RIGHT.
  - **THE DAY at 12:05 said "sellers' day (9 fights to 8) · trending above value"**, at the day high after +184 points:
    misleading.
- **Zone:** SELL armed at 11:30: RIGHT.

**E6. The reversal, 12:10–12:30, and the flush to 22633.**
- **The extension:**
  - Initiative at 12:10 and 12:20, sellers: RIGHT.
  - Initiative at 12:30 (the −999 flush bar): RIGHT but LATE.
  - A at 12:15, buyers defending 22745: WRONG.
  - **E at 12:25 at 22716.6, "new low on 24": WRONG**, an artefact of the truncated bar.
  - **No P for the trapped longs: MISSED.**
- **fold:**
  - Sellers won at 12:12 (22756, 510 lots): RIGHT.
  - Sellers won at 12:21 (22745, 896 lots): RIGHT, together with the release of the 12:02 trapped sellers.
  - Sellers won at 12:27 (22719): RIGHT.
  - **Buyers trapped at 22721 and 22728 at 12:28, and at 22700 at 12:31: RIGHT.**
  - Won by price at 12:31: LATE.
  - FLOW read QUIET from 12:10 to 12:19 (missed the first 10 minutes), then SELLERS from 12:20: RIGHT.
- **Zone:** SELL triggered at 12:18: RIGHT, and silent (the fade gate); exit at VWAP at 12:30.
- **The extension stopped posting at about 12:26.**

**E7. The afternoon balance, 22642–22723, from 12:35 to 15:00.**
- **The extension:** these marks were rebuilt at 16:08 from snapshots, and **none of them was on her chart live.**
  - Initiative at 13:40 and 13:45, buyers at the low: RIGHT.
  - E at 13:50 (22697) and 14:10 (22690): RIGHT.
  - A at 14:15, 14:20, 14:30 and 14:35 (22690–22710), sellers defending: RIGHT.
  - P at 14:20 (22695) and 14:40 (22690): RIGHT.
  - A at 13:55 (22675), buyers defending: NOISE.
- **tm:** E at 13:20, 13:25, 13:35 and 13:40, walking 22667 down to 22642: the first is RIGHT, the other three NOISE.
- **fold:**
  - **50 marks** (12 won, 6 absorbed, 14 trapped, 18 released); typically a trap was released 3–13 minutes later: NOISE.
  - Buyers absorbed at 12:44 (22701) and 13:15 (22698): RIGHT.
  - **GAVE UP, "SELLERS GAVE UP AT 22700 · 14:32", 14:39–14:50: WRONG**; price went to 22668.
  - ZONE did most of its 110 flips here.

**E8. The expiry hour (big delta, no progress).**
- **The extension:**
  - **A at 15:00 at 22685 (2,084 net bought, the bar closed 14 points lower), sellers defending: RIGHT.** 59% of that bar is
    one block (`2-data-audit.md` §3c).
  - A at 15:10 (22700) and 15:15 (22705): RIGHT.
  - E at 15:05 at 22695 (at CE 22699): RIGHT.
  - **C at 15:20 at 22616: RIGHT**; the spike low, then +98 into the close.
  - P at 15:20, buyers trapped at 22705: WRONG (the close was 22714).
- **tm:** E at 15:00 (22656.5) and C at 15:20: RIGHT.
- **fold:** 15:21–15:22 produced six "buyers trapped", all released at 15:26: NOISE.
- **grounds:** GC's CVD "pressing" at 15:30 (rank 0.9) with price flat reads effort as direction: WRONG framing.
- **Delta × OI × price:** no detector (C.1).

### B.3 The tally by detector

Columns: R = RIGHT, E = EARLY, L = LATE, W = WRONG, N = NOISE.

These are counts of graded marks on one day, against one supervisor's read. They are not rates, and no rate is implied
(house rule 4). The fold replay reproduced the live read; it is not a backtest.

| Detector | Marks | R | E | L | W | N | Seen live on her screen |
|---|---|---|---|---|---|---|---|
| board.js initiative | 15 | 9 | 0 | 2 | 0 | 4 | never (not drawn) |
| board.js absorption (A, both forms) | 21 | 11 | 4 | 0 | 5 | 1 | only when placed at a level; none after 12:26 |
| board.js vacuum | 6 | 2 | 0 | 0 | 1 | 3 | never |
| board.js climax (C) | 1 | 1 | 0 | 0 | 0 | 0 | rebuilt at 16:08, not live |
| board.js trap (P) | 7 | 2 | 0 | 0 | 5 | 0 | the 4 base Ps live; the afternoon ones not |
| board.js exhaustion (E) | 7 | 3 | 1 | 0 | 2 | 1 | 11:30 live; 09:20 once its placement was fixed that morning |
| board.js walls | 5 shelves | 4 | 0 | 0 | 0 | 1 | yes |
| tm_marks (A/E/C) | 9 | 4 | 0 | 0 | 2 | 3 | never |
| fold won | 30 | 11 | 1 | 1 | 4 | 13 | Trade tab; FLOW row |
| fold absorbed | 9 | 3 | 1 | 0 | 1 | 4 | Trade tab |
| fold trapped | 28 | 8 | 4 | 0 | 2 | 14 | Trade tab; NEXT FIGHT |
| fold released | 27 | 2 | 0 | 0 | 0 | 25 | Trade tab (removes shelves) |
| fold FLOW row at the six turns | 6 | 3 | 0 | 1 | 1 | 0 | QUIET through the base and the first 10 minutes of the reversal |
| fold GAVE UP | 3 | 0 | 0 | 1 | 1 | 1 | on screen 2 + 12 + 1 minutes |
| grounds CVD divergence | 1 episode | 0 | 1 | 0 | 0 | 0 | ANSWER text only |
| grounds aggression | 2 episodes | 0 | 0 | 1 | 1 | 0 | BOARD, ANSWER |
| zone machine triggers | 2 | 2 | 0 | 0 | 0 | 0 | both silent |
| signals sound | 0 bells | – | – | – | – | – | 41 state flips, no sound all day |

The fold FLOW row at the six turns is 5 graded reads: the sixth, the base, was the MISS.

The "live" column matters as much as the grades:
- The best order-flow reads of the day were the base walls, the tm 11:05 E, the UX top divergence, the fold 10:56 traps,
  and the 11:30/11:40/12:00 E and As.
- Of those, only the walls and the E/A group reached her chart.

### B.4 What nothing said

- **The 09:35 low as exhaustion:** only fold's 09:33 "sellers absorbed". E was spent, tm was blind, the vacuum said the
  opposite, and grounds was blind.
- **Accumulation in the base:** no read joined "price flat" with "delta positive (GC)" or "OI falling".
- **Trapped longs at the top on the extension:** none. Only fold's 12:28 traps caught them.
- **The afternoon's short covering into expiry:** see C.1.
- **A bell at either extreme.**

---

## C. Structural gaps (each one checked in the code)

### C.1 Delta × OI × price: absent
- **The extension ignores OI.** `board.js` never reads `oi`, although every bar carries it (`main.js:263`). `fit.contract`
  uses OI only to match contracts.
- **grounds uses no delta.** It names a quadrant from ΔOI × Δprice (`grounds.py:137-142`), and is blind within 7 days of
  expiry (`grounds.py:55, 132`). `frame._trapped.fut_oi` is the same (`frame.py:263-266`).
- **fold reads only option OI**, at the named walls.
- **engine.py joins option OI with futures price and volume ranks**, with no delta.
- **So no module can say** "CVD +7,060, price +40, futures OI −11,400: shorts covering into supply".
- **On the expiry day the near future's OI falls mechanically** (roll and settlement), so the read needs Sep plus Oct OI.
  `upstox_instruments._futs` watches only `futs[0]`, and the Oct future is recorded nowhere (`2-data-audit.md` §4).

### C.2 Effort against result over a leg: absent
- **board.js exhaustion:**
  - `legs()` (`board.js:36-54`) exists only inside the exhaustion rule.
  - That rule compares **one bar's** delta against the leg's single strongest bar, never the leg's cumulative delta against
    its displacement.
  - It fires once per leg (`board.js:109`).
  - Its floor is a fixed 100 lots (`board.js:105`).
- **fold's fights** are effort against result (lots against progress, `fold.py:455-456`), but a fight is 1 to n
  consecutive 309-lot buckets (minutes), not a leg.
- **fold's TIRING** is progress against time, and runs only inside a trade (`fold.py:400`).
- **grounds** prints ΔCVD next to Δprice for 15 minutes (`grounds.py:127`), without a ratio and without comparing legs.
- **No module** can say "this leg down took 2× the delta of the last one for half the points".

### C.3 CVD divergence: three partial forms, no cross-family form
| Form | Code | Data | Scope | Where it shows | Today |
|---|---|---|---|---|---|
| grounds | `grounds.py:113-121` | UX | a day extreme against the CVD's own day best | ANSWER text | top RIGHT-EARLY; no bottom |
| board.js E | `board.js:103-118` | GC | one bar against the leg peak | chart | wrong bar at the low |
| tm E | `prints.py:282-291` | GC | the sign only, against 6 bars | nowhere | the 11:05 squeeze tell |

- GC's CVD, `prints.with_cvd`, is never tested for divergence.
- No form compares the two families.

### C.4 Expiry and roll
**What exists:**
- the futures-OI blind for the whole expiry week (`grounds.py:55-71`);
- prior days cut by contract, for `/api/tape` levels and fold's priors (`tape_log.prior_pool`, `tape_log.py:104-126`);
- fold's in-trade expiry afternoon from 13:30, where G trails the best minus 2B and FOLD comes on plain acceptance
  (`fold.py:47, 709, 862-870`);
- the chart's pause on an OI mismatch (`fit.contract`).

**What is missing:**
- **The flat read has no expiry rule.**
- **The expiry-afternoon collapse of option OI reaches fold's OI watch as "off" events.** For example, "22650 PE off since
  15:21, −36.5%" was read as positioning.
- **Blocks and possible spread prints are not screened anywhere.** The 10:05 block (4,528 lots in one print; futures OI
  +270k then −337k) became:
  - a board.js A;
  - a tm A;
  - the session aggressor for the rest of the day;
  - most of the base's "positive delta".
- **Tomorrow `NIFTY-I` is the Oct contract.** The extension's `priorLevels` (`market.js:64-83`) has no contract check.
  They are unused on screen today, but any future use would inherit the calendar spread.

### C.5 Leg segmentation: absent as an object
- **Legs:** only `board.js legs()`, private to exhaustion.
- **The zone machine** folds falling lows into one setup (`band_rotation.py:1085-1110`).
- **fold** has runs and a 5-bucket stall window.
- **grounds** has a fixed 3-bar window.
- **Nothing publishes** "leg n of this move, its delta, its points, its duration" to any face.

### C.6 Single-bar lookbacks
The following read one bar against a 20-bar median:
- the board.js initiative, absorption, vacuum and climax (P is 2 bars);
- the tm absorption and climax, against the session rank;
- fold's trap check, one 1-minute bar's VWAP against the run's VWAP.

fold's FLOW row reads **one fight**: the newest within 10 buckets.

Consequences today:
- the block at 10:05 was a "whole bar's story" twice;
- the truncated 12:25 bar made an E;
- one 11:48 fight decided FLOW at the top.

### C.7 The two data families disagree, and the disagreement is hidden

**The size of the disagreement:**
- The sign agrees on 68.9% of bars (`ux_gate.py:93`). It is served in `/api/tape` `ux.agree` and **rendered nowhere.**
- The Upstox side is itself a reconstruction: 28.6% exact prints and 30.8% hidden. It is built on the tick-unit defect,
  which fold keeps on purpose (`LADDER_TICK = 10.0`, `fold.py:49`).
- VPIN uses a third siding method, the tick rule (`vpin.py:11-20`).

**Where the disagreement could surface, and why it does not:**
- **fold's dispute** (`fold.py:496-451`) produced **0 disputed fights today**, on a day with 31% sign disagreement.
  - The GoCharting check skips any bar not yet closed at the fixing time (`fold.py:438`, `r["t"] + 300000 > now`), so a
    fresh fight is never checked against the bar it happened in.
  - GoCharting sent no bars from 12:26 to 16:08.
  - A disputed glyph is no longer drawn on the chart (`overlay.js:267`).
- **The face puts two families side by side with no reconciliation.** The chart's P/A/E/C are GC (`board.js`); the panel's
  rows are UX (`fold.py`).
  - At 10:10 the chart said "buyers trapped" while the panel's FLOW said QUIET.
  - At 12:03 the panel's FLOW said SELLERS while the Trade tab drew "sellers trapped" shelves.
- **BOARD's "TAPE" family is not a second opinion.** It merges ofd and tm events, and both are GC (`board.py:316-333`).

### C.8 Duplicated concepts

| Concept | Implementations (data) | Where each shows |
|---|---|---|
| Absorption (6) | `board.js:77-87` cluster (GC); `board.js:88-89` effort (GC); `prints.py:275-280` (GC); `fold.py:456` ABSORBED (UX); `absorption.py` book replenishment (UX depth); `engine.py:842-862` volume/range (futures, no delta) | chart A, Trade tab A; nowhere; Trade tab ▬ and the rows; no face; the Events tab |
| Trap (6) | `board.js:94-98` P (GC); `fold.py:339-347` trapped/released (UX); `engine.py` TRAP, TRAP-SETTING, TRAP-SPRUNG (CH); `dwell.py` war-map trap (CH); `band_rotation._trap` compression; `frame._trapped` writers' pain | chart P; Trade tab shelves; Events; War; zone records; the frame |
| Exhaustion (4) | `board.js:103-118` (GC); `prints.py:282-291` (GC); `grounds.py` divergence (UX); fold TIRING/FAILED (UX, in-trade) | chart E; nowhere; ANSWER; the in-trade headline |
| Climax (3) | `board.js:92-93` (GC); `prints.py:293-298` (GC); `engine.py:831-840` (CH) | chart C; nowhere; Events |
| Initiative / aggression (6) | `board.js:82-83`; fold INITIATIVE/PRESSING; `board.py:102-127`; `runs.py`; `sweep.py`; `frame.py:377` session sign | none drawn; rows; BOARD; ANSWER; depth vote; the frame |
| Walls (3) | board.js net-flow shelves; fold's named OI walls (renamed 30 times today); the frame's ladder rows (tape plus OI plus levels, `agree`) | chart; Trade tab and in-trade; chart chips |
| Prior-day levels (4) | `market.js:64-83` (unused); `prints.prior_levels` and `naked`; fold's PRIOR (UX book); `structure.prior_day_hlc` (pivots) | none; Trade tab; ZONE and NEXT FIGHT; chart lines |
| VWAP bands (2) | `market.js:16-36` (GC 5-minute hlc3); TapeMap's 3-minute futures bands (the zone machine). Their σ differs by 2–8% (`trade/footprint.ts` note) | chart taps and zone words; the zone machine |
| Stacks (2) | `decode.js:24` (dead); `prints.py:52` (live) | –; `/api/tape`, grounds FLOW |
| Aggressor siding (3) | GoCharting vendor; the `ladder.py` quote rule and reconstruction; the `vpin.py` tick rule | everything above |

---

## D. Keep, retire, merge

Her proven favourites are treated first. Nothing here is a code change; each item is a proposal to be replayed on every
recorded day before it touches her screen, as her standing rules require.

### D.1 Keep, untouched in logic: the zone machine
**Why:** it caught both extremes today, with no false trigger, and it reads price only.

**What to do:**
- Add order flow as annotation beside it, never as a gate.
- The silence at both extremes is not the machine's fault. It is the window rule (`visit.py:50`) and the fade gate
  (`signals.gate_sound`). Put both in front of her as a decision, with today's evidence:
  - the buy at the low was outside the window;
  - the sell at the top was vetoed by "CE 22700 unwinding 10:59".

### D.2 Keep the P/A/E/C family (her words, 09-16 and 09-29: "they really work great … shows potential tops"), and fix why it misfires
Keep the letters, the glyphs and the placement rule, including A and E only at a level. Candidate fixes, each to be
replayed:

1. **Freeze the detector geometry.**
   - Run the detectors at a fixed row, and use the chart's rowSize only to place a mark.
   - Then a zoom can never rebuild the day (`main.js:247`). This is the "marks come and go" root cause.
   - Record every posted event once, as `ofd_marks` already does, and let the chart draw that record rather than a
     recomputation.
2. **E: allow a re-fire on a lower-effort new extreme later in the same leg,** instead of once per leg (`board.js:109`).
   Self-calibrate the fixed 100-lot peak (`board.js:105`).
   - Replay test: the 09:35 low must get an E, and the 09:20 E must stay or go on evidence.
3. **Mark a feed-died bar as partial** (`adapter.js:142`), so that GoCharting's snapshot replaces it (`session.js:27`).
   This removes artefacts like the 12:25 E.
4. **P: add a negation.** Price back through the trapped side's level by one row should grey the P, as fold's release does.
   - The base Ps were never negated.
   - P never fired on the actual trapped longs at 12:05–12:30. Test fold's run-VWAP definition against board.js's
     cluster-at-the-extreme on the recorded days.
5. **A: the two definitions under one letter.**
   - The effort form gave the best expiry-hour reads.
   - The cluster form gave the 11:40 top reads.
   - Keep both, but carry the form in the event, so a trader or a replay can tell them apart.
6. **Screen single-print blocks.** If one level is at least 50% of a bar and the bar is at least 3× the median, label the
   bar "block" rather than "absorbed". This affects the 10:05 bar and half of the 15:00 bar.

### D.3 Keep and promote: the grounds CVD divergence
**Why:** it was today's best top read, and it lives as text inside ANSWER.
- Compute it on both families.
- Put it beside P/A/E/C as an E-class read, with the family named ("UX divergence; GC not diverging").

### D.4 Merge: tm_marks into board.js
**Why:** tm_marks is the same data family, a duplicate concept, and shown nowhere. But its 11:05 six-bar exhaustion ("new
low on positive delta") was the best-timed squeeze tell.

**What to do:**
- Fold that trigger into E as a second, labelled form.
- Retire tm's absorption and climax, which duplicate board.js on the same bars.
- Keep it in BOARD's TAPE only until the merge.

### D.5 Surface, don't retire: the family agreement (`ux_gate`)
- Put the per-bar sign agreement on the face, for example as a hatched or "disputed" P/A/E/C wherever UX's delta disagrees
  in sign.
- Repair fold's dispute so that it checks the bar the fight is in (`fold.py:438`).
- Show a disputed fight again (`overlay.js:267`).
- The designers should pick which family a read uses by evidence, per read. Today GC caught the low and UX caught the top.

### D.6 Keep fold's fight engine for her marked trade (rev 6, signed); rework the flat read
- **FLOW:** read the run's current state. A trapped run is not "won", which removes the 12:03 contradiction. Read over a
  window, not one fight.
- **ZONE and NEXT FIGHT:** add hysteresis, or freeze on an event. At 110 and 150 changes a day, they are not glanceable.
- **GAVE UP:** freeze it as the docstring promises, instead of recomputing it (`fold.py:1201-1218`).
- **THE DAY:** replace the fight count with displacement or legs. At 12:05 it called a +184-point morning "sellers' day".
- **The trap/release churn:** 39 of 55 trapped and released marks were NOISE. It needs a minimum dwell before "trapped".
- **Out of scope for order flow, but related:**
  - the named-wall hopping (30 renamings);
  - `LADDER_TICK = 10.0` (`2-data-audit.md` §3f).

### D.7 Keep: the board.js walls
The lean count on B 22600/22605 was the clearest base read of the day. Keep it, and make the lean count prominent.

### D.8 Retire
Each of these has evidence that it is dead or misleading:
- **The vacuum:** consumed by nothing, and it mislabelled the 09:35 exhaustion as continuation.
- **The frame's session aggressor** (`frame.py:377`): one block decided it for the whole day.
- **`decode.readBar` and `imbalances`** in the extension: dead code.
- **`market.priorLevels` in the board context:** unused, and not contract-safe.
- **The flow-since-tap rows** (`main.js:192-193`): not shown since rev 6.
- **`absorption.py` and `impact.py`:** no face and no consumer. Let their kill clocks run in the logs, or park them.
- **The hold.py flow family:** its window is unmounted. Retire it with hold.py once `validate.py`, `expression.py` and
  `plan.py` stop importing it; that decision is outside this audit.

### D.9 Rename on the face (not the code)
- The engine.py option-OI events TRAP, CLIMAX and ABSORPTION share words with the tape's P/C/A, but mean option-writer
  events.
- A reader who sees "trap" in two places with two meanings will trust neither. Prefix them, for example "OI trap".

### D.10 Do not change without her, but show her
The 3-row tolerance in `setup.fire` and the signals event vote (`frame.py:445`, `signals.EDGE_ROWS`) is measured in chart
rows. At rowSize 10 it became 30 points, and a failed exhaustion 60 points above the low "confirmed" the buy visit at
09:31. Tie it to points or to B.

---

## Appendix: how the numbers were produced (reproducible, read-only)

- **The fold replay:**
  - `scratchpad/a3/replay_fold.py` feeds `fold.State(None, …)` the day's `book_NIFTY_2026-09-29`, `chain_NIFTY_2026-09-29`,
    `vpin_fast` (day rows) and tape bars, in the engine's own key order, one minute at a time.
  - The prior sessions are `tape_log.prior_pool` (22, 23, 24, 25 and 28 Sep) through `fold.session_from_book`.
  - It calls `flat_view` each minute.
  - The final marks equal the live `/api/fold/flat` marks: 124, with the same kinds and counts.
- **The chip flips and NEXT FIGHT changes** are counted over the 375 minutes from 09:16 to 15:30.
- **The GC and UX bars:** `/api/tape` `bars` and `ux.bars`. The sign agreement is `ux.agree` (ux_gate); a recount gives
  51 of 74.
- **The extension events:** the union is `data/tape/ofd_marks_NIFTY_2026-09-29.jsonl` (57); the rebuilt board is
  `/api/tape` `marks.ofd` (44, "live", posted after 16:08); the placements are `/api/day/record` `events[].at`.
- **The signals, sound and fire:** streamed from `data/frame/frame_2026-09-29.jsonl`. The frame rows stop at 12:25 and
  resume at 16:08.
- **grounds on both families:** `grounds.facts` and `board.aggression`, run on growing prefixes of the ux bars and the GC
  bars, with `roll` set (as live) and the runs empty.
