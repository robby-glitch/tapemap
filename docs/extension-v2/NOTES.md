# extension-v2 mockup: notes (19 Oct 2026, pre-market)

`python -B build_mockup.py` rebuilds `frames.json` and `mockup.html` from the recorded files. It also runs a self-check: no data after T, every drawn mark passes all three rules, and the line and chip budgets hold. The supporting files are:
- `before.mjs`: runs the extension's own `board.js` and `decoder.js`, unchanged, for the "before" count.
- `template.html`: the page shell.
- `cache/`: the one `GET /api/contract`.
- `shots/`: the headless Chrome screenshots at 1366×768.

**T is the clock time.** A frame shows only the 5-min bars closed by T and the 3-min futures bars closed by T. The forming bar is never drawn. At 16 Oct 09:40, the 09:40 trap is not known yet (its bar closes at 09:45).

## Rules that fired, per frame
| Frame | READ → KHEL | Marks drawn (all 3 rules) | Lines | Tint strips |
|---|---|---|---|---|
| **16 Oct 09:40** | BAN RAHA → **KHEL ?** | **A** KHAREEDAR NE ROKA ▲ 22,908 · p92 · TIKA (−2σ, 7.1 of 9.0 pts; bar CLIMAX; GC+UX ✓) | VAL aaj 22,947f · KAL KA LOW 22,671f (off-chart chip) | 09:30, 09:35 CLIMAX |
| **16 Oct 10:25** | LEAN ▲ from 10:20 [I] → **RIDE ▲ ADHA**, PREM 2.98 KHARIDO | the 09:35 A (still TIKA) · **B** BADA KHARIDAR 606 @23,100 · p100 (N=6) · TIKA · GC only (+2σ, 0.1 of 12.6 pts; bar PUSH) | VAH aaj 23,111f (nothing real above price; FLIP 23,000 can't be placed, basis ?) | same |
| **12 Oct 10:30** | LEAN ▼ from 09:50 → **RIDE ▼ ADHA**, PREM 0.73 | **none** | **§E trade:** KILL VWAP 22,599f\|22,553s · T1 −2σ 22,490f · ENTRY 22,566f · FLIP 22,646f\|22,600s · POC aaj 22,540f (VAL aaj is over the 5-line budget) | 10:15 CLIMAX |

**12 Oct in-trade view.** The READ-V2 §E rule fired at 10:00 (LEAN ▼ SELL). The 3-min bar ending 10:00 had a high of 22,578 against a −1σ of 22,567 (high ≥ −1σ), a close below −1σ, and a 3-min delta of −52. Neither the stop nor T2 was hit by 10:30. The fold board:

| Reading | At entry → at 10:30 | Counts against? |
|---|---|---|
| ZONE | −1.0σ → −1.6σ | no |
| FLOW | −354 → −296 (p46) | no |
| OI | naye short | rank ? (not counted) |
| VPIN | 0.25 → 0.28 (p84), buyers' imbalance | **yes (ULTA)** |

**Verdict: WATCH.** No §E rule fired on 16 Oct before 10:25, so that frame shows no trade.

## Suppressed, and why (the full table is under each frame and in `frames.json`)
- **16 Oct.**
  - The 09:35 twin absorption at 22,915 is 14 pts from −2σ (the tolerance was 9).
  - The 09:40 trap at 22,915 ranks p100, but it is 12.5 pts off −2σ (tolerance 8.7) and its bar is *no read*.
  - At the top:
    - the 10:15 absorption at 23,140 ranks **p88** (< p90);
    - the 10:20 trap at 23,140 ranks p96, but it is 25.6 pts from +2σ (tolerance 17.4) and its bar is *noise*;
    - so **the 23,155 high carries no mark under these rules**.
  - Not drawn kinds:
    - the 10:15 climax (shown as a bar tint instead);
    - vacuum, initiative and the decoder's E5.
- **12 Oct.** The buyer marks at 22,520–22,525 are 10:15 absorption ×2 (p75, p72; 14–20 pts from −2σ, tolerance 12.9) and the 10:20 trap (p79; at VAL aaj, but its bar is *no read*). All three are **below p90** and all are **TOOTA by 10:30**. They show only in SIRF BADE, as struck-through TOOTA rows. **The chart stays quiet.** Also not drawn:
  - the 09:40 absorption (p29);
  - initiative, exhaustion and vacuum;
  - the decoder's E2, E3 and E5.

## Before → after (today's extension on the same bars → this redesign)
| Frame | Before | After |
|---|---|---|
| 16 Oct 09:40 | **2**: 0 glyphs; lines wall 22,950 and Kal ka low | **3**: 1 glyph, 2 lines, + 2 tints |
| 16 Oct 10:25 | **5**: E5 KHULA, E1 print, P 09:40, X floor toota; line wall 23,140 | **3**: 2 glyphs, 1 line, + 2 tints |
| 12 Oct 10:30 | **7**: E2, E3, E5, P 10:20, X; lines wall 22,525 and Kal ka low | **5**: 0 glyphs, 5 lines (3 of them the §E trade), + 1 tint |

The "before" count assumes she has no trade marked in the extension. Its own trade lines would add to it.

## Where data was missing
- **16 Oct basis.** The futures-minus-spot basis measured **+6 to +7**, against medians of +53 to +89 on 6–13 Oct. It is therefore "?":
  - every spot value is "?";
  - no strike could be placed in fut (FLIP 23,000, fresh-writing strikes).
- **16 Oct after 09:48.**
  - Upstox (UX) is missing, so it is GC only.
  - The chain recorder has a gap to 11:12. It is filled from `chain_backfill` (REST minutes) [I].
  - The futures ticks are gone. The READ's flow and price come from the GC bars [I].
  - GC open/close is null and is filled from the 3-min futures [I].
  - The 09:45–10:00 GC window has 1,621 lots against 1,861 in the futures, 240 short. These are bars recorded across the server gap.
  - PREMIUM uses the 09:48 IV [I].
- **16 Oct READ.** The live log froze on RANGE from 09:48. The gap-filled replay breaks RANGE at 10:00 and 10:20 and forms LEAN ▲ at 10:20, so the head says [I].
- **Yesterday's footprint.**
  - 15 Oct has no footprint, so 16 Oct's HVN/LVN are "?". PDH/PDL/PDC come from `index_series`.
  - 9 Oct's footprint runs only to 14:00, so 12 Oct's HVN/LVN ticks are partial.
- **index_series vs GC** for the same minutes:
  - bar highs and lows are within 1 pt, except 12 Oct 09:15 (8 pts on one low) and 10:00 (3 pts);
  - VWAP is within 0.07σ on every frame, so the bands come from `index_series`.
- **Not built, so not shown:**
  - RVOL12 before the 13th bar: ROKA is impossible before 10:15, and those bars read *no read*, not noise.
  - Fresh writing before 09:45.
  - OI rank: it never counts against her on the fold board.
  - The day-level rank: SIZE is therefore ADHA, never full.

## Ambiguities and how I resolved them
1. **Flow state.** `fs_lib.state()` is the pre-§6 rule. I applied the §6 states on top of fs_lib's loaders, features, R and quantile:
   - SIZE = |Δ| ÷ the same-slot median of prior days;
   - RVOL12 as defined in fs1.py;
   - thin = volume ≤ the slot's p10.

   The reference is the days before the frame, which is the study's leave-one-day-out set for both days. This reproduces the study's moments: 16 Oct 09:35 CLIMAX (R +0.07), 10:10 and 10:15 PUSH, and 12 Oct 10:15 CLIMAX (R −0.15).
2. **Rule 3 uses the GC state** of the mark's bar. A missing or disagreeing UX only adds "GC only". ABHI shows the strict both-sources rule.
3. **"Big".** Era-B marks from 5 Oct up to the day before, deduplicated, kind against kind. Prints are ranked against era-B decoder E1s: N=5–6, provisional.
4. **Drawn kinds** = trap, absorption and BADA print (the chip table). Everything else counts in "baaki". The trap's logged side is the trapped side.
5. **Fresh writing** has no spec definition. I used: a 30-min OI add at ATM±2 ranked ≥ p90 against the last 10 recorded days (pooled, not by day-part) [I].
6. **TIKA/TOOTA** = `board.js`'s broken test (a close beyond the level by more than one 5-pt row), on 3-min futures closes.
7. **Basis** is plausible only within +20 to +120.
8. **KHEL.** BAN RAHA gives "?". Zone shading starts at the bar where the READ formed.
9. **PREMIUM** = 30-min futures move ÷ (ATM IV × F × √(30/94500)).
10. **§E.**
    - A trade lasts until the stop or T2. T1 is noted, not an exit.
    - A PE wall nearer than T1 is not a T2.
    - A zone touch whose 3-min delta can't be read is "?", never an entry.
11. **Fold board.**
    - ZONE counts against her within 0.5σ of VWAP (P-OF4).
    - FLOW counts against her when the counter-trend 15-min delta is ≥ p80 of today's windows.
    - VPIN counts against her at ≥ p70 with the imbalance against her.
    - FOLD at 2 against, WATCH at 1. The "held 3 min" condition is not applied (bar data only).
12. **Kill and T1** are drawn flat at their value at T, so they are not drifting lines.
