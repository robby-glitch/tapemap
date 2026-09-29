# 5 — Critique of the Opus design, by Fable (round 3)

Read-only. Sources: `4-design-opus.md` (line numbers below), `2-data-audit.md`, `3-current-reader-audit.md`, the new `data-2026-09-29\fut_SEP_1m.json` / `fut_OCT_1m.json` (385 one-minute bars each, checked in `scratchpad\fable`), and my own replays. Lots = units ÷ 65. Where I was wrong, I say so (§2, §5).

## 0. The Oct data changes the afternoon for both of us

| Window | Sep pts / OI (lots) | Oct pts / OI | Combined OI | Spread Oct−Sep |
|---|---|---|---|---|
| 09:15–11:05 | −139 / −11,964 | −101 / +15,978 | +4,014 | 111 → 148 |
| 11:05–12:05 | +156 / −2,355 | +156 / +5,372 | +3,017 | |
| 12:05–13:30 | −90 / −1,135 | −96 / +10,266 | +9,131 | 148 → 142 |
| **13:30–15:29** | **+46 / −10,761** | **+68 / +25,483** | **+14,722** | 142 → 164 |
| day 09:15–15:39 | −25 / −26,701 | +42 / +58,462 | +31,761 | 111 → 178 |

Oct out-traded Sep in 71 of 77 five-minute bins, from 09:20 (day: Oct 92.2k lots, Sep 61.7k). Rollover Oct÷(Sep+Oct): 60.5 % → 70.9 %. The 15:20 flush: Sep 22714.8 → 22616 (−99); Oct 22874.7 → 22840.4 (−34), the spread 157 → 228 at 15:21. **That low was a Sep-only settlement move.** The 10:07:42 block: Sep OI +4,651 and Oct OI +5,134 in the same minute (10:08), Sep −5,021 at 10:12 with Oct unchanged: a calendar-spread print, not a position.

Both designs wrote "not new buying". True of the Sep tape, false of the market: the continuing contract rose +68 on OI +25.5k with the spread going rich (carry ≈ 120), which the OI table both of us use reads as **new longs in Oct** (aggressor [I] from price; there is no Oct delta). Sep shorts covered and did not re-short Oct. Positioning rolled forward on the long side and grew. §5 carries my correction.

## 1. Where the Opus design is wrong

1. **A Upstox frame is treated as a print** (R-10, line 368; §6 12:05, line 799: "blocks at 11:28:57, 328 lots, and 12:01:06, 302 lots; UX only"). The audit measured that only 32 % of volume-bearing frames are single trades (`2-data-audit.md` §2, "Prints: None"). A 300-lot frame is a busy second, not a print. Excluding those "blocks" moved the top leg's UX λ (the 43/77 figures are built on it). Rule: a UX block exists only when `V == ltq` (one trade fills the frame), otherwise it is a burst.
2. **"A position opened in one print"** (line 370, 761) for the 10:07:42 block. Oct OI rose +5,134 in the same minute; Sep's +4,651 reversed within four minutes. It is a spread leg (research S49: spread legs carry no aggressor). The reader must say "spread print, not directional". Opus's OI-step line shows the +4.7k and stops.
3. **The R3 pass case is presented on two tapes while GoCharting was dead** (line 868: "Buyers Δ+6,117 GC / Δ+8,381 UX (block-excluded; both tapes …)"; line 859: "CVD higher on both tapes (GC 13.9k …)" at 15:22; line 395 the 12:30 and 15:20 lows "finished" from a ladder that arrived at 16:08). Its own R-01 (line 179) says marks and numbers from the silent span are "never drawn as live" and revisions are stamped "added 16:08". The as-of read at 15:40 is one tape; the two-tape sentence is a 16:08 revision. The walk-through blurs the line it drew.
4. **δ = 3·B(t) with B from today's first five completed minutes** (R-02, line 206: δ 29 → 50 → 34.5 on 29 Sep). The ruler is set by five minutes of the open and then shrinks all day. Legs cut with δ 50 and δ 34 are ranked together and compared "vs the last leg the same way" (R-03). That is the flow-rank bug moved from the rank to the unit. The K-sensitivity table (line 137–145, 909) already shows the structure is fragile: K 3.5 loses the 22 Sep 13:00 breakout.
5. **GC SILENT at 15 s** (line 172). The extension's cadence is its own timer; Chrome throttles timers in a tab hidden for more than five minutes to about once a minute [general Chrome behaviour, not measured in our data]. Our frame log measures ~1 row per 3.6 s only while the tab was visible. A 15 s rule fires SILENT, the black band and the sound every time GoCharting sits behind her broker window. The design's own prevention list ("own window", line 196) concedes the failure mode. The threshold must be measured against a hidden tab before it is signed.
6. **The block rule and its own example disagree** (line 368 vs 376): "lots per print ≥ 100 × today's median lots per print" (median 7–8 lots → 700–800) does not flag 15:00's 2,030 lots in 3 prints (677 each), yet §6 lists it as a block.
7. **OFI is over-read** (line 70–73, 308, 850: "resting offers refilled and bids were pulled", "offers refill ho rahe"). From 5-level 1 Hz snapshots a cancel and a fill between frames are the same event (research C4; audit: "cannot see iceberg refills, add/cancel"). "L1 OFI −1,986 [I]" is honest; "refilled" is a claim the data cannot make.
8. **Walls vanish from the chart.** §3.1 keeps the B/S walls with the lean label (line 447); the overlay table (§5.2, line 615–625) has no wall row. The audit's best base read on 29 Sep has no place to be drawn.

## 2. Where it is better than mine (I adopt these)

1. **Finished / unfinished at the extreme (R-11).** Opus is right and I was inverted: a finished high has 0 sold-at-bid at the top row (12:05: sell 0 × buy 93), a finished low has 0 bought-at-ask at the bottom (09:35: buy 0 × sell 14). My §2.7 said the opposite. Corrected in Rev 2, with a third word for a top that printed on one side only.
2. **FLOW words WITH / PULLBACK / AGAINST / SPLIT / CAN'T CHECK (R-13)** with PULLBACK defined as "against her, no named aggressor or low λ, and her leg's origin not traded through". That is her "pullback vs invalidation" in one rule. Mine had WITH/AGAINST plus prose. Adopted.
3. **Price-side give-up: the counter-pivot break ("Trend toota ↓ 22676" at 12:30:3x, line 820).** A named invalidation at a level that is not the obvious stop. Adopted as the flow-side "somebody gave up".
4. **RANGE / BREAKOUT on top of legs**, with P marks demoted inside a RANGE. Cleaner than my "box < 2δ for 6 bars". Adopted (two states; I skip PAUSE).
5. **Block = the print, not the bar** (GC ladder rows; my replay excluded the whole 10:05 bar, which threw away 1,900 honest lots). Adopted, with the frame rule from §1.1.
6. **Forming-bar stall detection ("GoCharting ticks ruke", 80 % of Upstox in the open bin)** and the **repair/rev flow** for short bars. Mine only flagged closed bars and substituted Upstox. Adopted, with a caveat on `tape_log` (§3.7).
7. **The leg table under the Trade chart** (line 664–672) and **"with GC alive" side-by-side numbers** as a validation device. Adopted.
8. **Δ-prefix plus a one-line legend** ("Δ = andaaza · OI, lots, pts = napa hua") instead of my 8 px M/I superscripts on every number. Cleaner. Adopted.
9. **Same-print rule** (no print is both A and P; line 445) and **pairwise "vs the last same-way leg"** as the earliest comparison. Adopted.
10. **Keeping `board.js` in the extension with a frozen row and the record in TapeMap** is the smaller first diff than my port; I take it as step one, the port as step two after parity.
11. **Pre-registered churn bars** (≤ 12 auction changes, ≤ 20 FLOW changes a day) and the 15:15 CAS clause. Adopted.

## 3. Where it is riskier

1. **Eleven hand-picked numbers signed at once** (§7.4, line 945–955: K, 0.10, 0.05, 100×, 25 %, δ/2, 3 visits, 1 BK, 80 %, BK/3, 15 s). Each is a fitting surface (research S64). Mine has four geometry constants; the rest are ranks.
2. **Intraday δ(t)** (§1.4): a unit that moves by 70 % inside a morning cannot make R14's "changes only on a named event" hold across legs.
3. **Four auction states with δ/2 rules** (line 215–219): PAUSE adds a state and a threshold for little; the reported 4–7 changes a day is on six days.
4. **Chart density**: up to 9 reader objects plus her marks (line 611), with her P/A/E/C greyed inside a RANGE (line 627). She said the P marks "work great"; greying them is a decision she will notice. Mine draws one strip and the letters.
5. **`tape_log` revisions** (line 498): write-once was a deliberate door (`server.py:3033`: "a forged bar that lands first locks the real one out"). Revisions reopen it; the rule needs the frame door's origin check on every `rev`.
6. **Two code paths for one record**: the extension GETs frozen marks, then runs `board()` for later bars (line 490–493). The extension's detector and the frozen record can drift after any change to `board.js`.
7. **15 s SILENT + sound** (§1.5): the loudest element in the design is the one most likely to cry wolf.

## 4. The three hardest questions it must answer before the judge

1. **With Oct captured, what does R-05 say at 15:40 on 29 Sep?** Its rule resolves ROLLED (Oct OI up ≥ ½ the Sep fall *with Oct delta negative*) or CLOSED (Oct flat). The data is Oct OI +25.5k (2.4× the Sep fall) with Oct +68 and the spread richening, and there is no Oct delta at all. Which word, on what rule, and does "not new buying" survive?
2. **Which contract is the leg engine's price on expiry day**, given Oct out-volumed Sep from 09:20 while her chart (`NIFTY-I`) is Sep, and what do marks placed on Sep prices mean at 15:20, when Sep fell 99 and Oct 34?
3. **Is δ = 3·B(t) a ruler or a repaint by another name?** Two legs cut with δ 29 and δ 50 are ranked in one list and compared pairwise; B is set by five minutes of the open. What is the pre-registered answer to a day where B halves at 10:00?

## 5. Corrections to my own design (Rev 2 changelog; appended to `4-design-fable.md`)

1. **Expiry day reads two contracts.** The WHO row shows Sep and Oct side by side; positioning (R3/R18 OI factor) is read on the *continuing* contract from the first three consecutive bins where its volume exceeds the expiring one (29 Sep: 09:30); Sep stays the chart tape with "expiring" on every Sep number. Afternoon corrected: "Sep: short covering into expiry, absorbed under 22723. Oct: +68 on OI +25.5k, spread 142 → 164 (carry ≈ 120): new longs; combined OI +14.7k. Positioning rolled forward on the long side and grew." "Not new buying" withdrawn.
2. **Expiring-only move flag**: when Sep's leg extreme exceeds Oct's by more than δ/2 after the spread, the leg is "Sep-only (settlement)". 15:20: Sep −99, Oct −34 → the C and the bullish divergence are Sep-only.
3. **Block at 10:07:42 = calendar spread** (Oct OI +5,134 same minute); rule added: a block whose OI step is mirrored in the other month within two minutes reads "spread print".
4. **Auction edge definition inverted → fixed** (finished high: sold-at-bid = 0 at the top; finished low: bought-at-ask = 0 at the bottom; "one-sided" when the other column is 0 too). 09:35 low and 12:05 high become POORA; 12:00 high (3 × 137) stays ADHOORA and was revisited.
5. **Block = print, not bar**; UX block only when `V == ltq`.
6. **FLOW words** WITH / PULLBACK / AGAINST / SPLIT / CAN'T CHECK adopted; price-side give-up = counter-pivot break.
7. **RANGE / BREAKOUT** states on top of legs; P demoted inside RANGE.
8. **Feed health**: forming-bar stall check added; bar-lag is the DEAD guard; SILENT/DEAD thresholds to be measured against a hidden tab before signing.
9. **Rollover line** on expiry day: Oct÷(Sep+Oct) and the spread vs carry, from the open.
10. **Face**: Δ-prefix + legend replaces per-number superscripts; leg table on the Trade tab.
11. **Self-score**: R3 on 29 Sep drops to partial as written (the sentence described Sep, not the market); R7 was fail as written (inverted), pass after the fix.
