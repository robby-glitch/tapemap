# How we decode every scenario, and where it breaks

30 Oct 2026, 01:00 IST. Her words:

> "find all the gaps like we found think for every scenerio and hiw we are deciphering this"

Every number below was measured on the record of 27, 28 and 29 Oct (NIFTY unless named): Jarvis replayed to 15:41, the
29 Oct OI grid, the Speed tab's own engine. Nothing here is a hit rate. [M] measured, [I] inferred. This file extends
GAPS-AND-LIVE-CHECKLIST.md (29 Oct); it does not repeat it.

**Status, 30 Oct ~02:00:** G1–G4 FIXED (her word: "Yes, fix G1–G4"), live at her next restart. What they changed on the
record, replayed to 15:41:

| Day | NAHI before → after (G1) | band answers | TIKI by buyers, now BUYERS IN (G4) | RISK minutes before → after (G2) |
|---|---|---|---|---|
| 27 Oct | 15 → 10 | 9 | 3 | 32 → 11 |
| 28 Oct | 23 → 12 | 13 | 0 | 142 → 20 |
| 29 Oct | 24 → 16 | 11 | 4 | 149 → 22 |

G3: legs may now run on one side ("calls" / "puts" only) and turn two-sided when the other side joins; 29 Oct reads UP
(incl. BACK) 74 minutes, was 33 + BACK 4. The 29 Oct 10:38 TOP RISK still fires and ends at 10:44 when the writers came
back. The rest (G5–G14) are open.

---

## 0. The decode chain, as it runs today

| Step | Input | Rule | Output | Where |
|---|---|---|---|---|
| 1 | chain poll, 1/min (backfill when blind) | OI change since open, per strike, per side | the OI grid | `/api/oihist` |
| 2 | the grid | OI change over 5 min, per minute | speed (L/min) [M] | `speed.ts` |
| 3 | speed | vs 5 % of that strike's own size per 15 min | likh / ruke / chhod [I] | `speed.ts` |
| 4 | the state | holds 3 min | a stamp (Speed tab KRAM) | `speed.ts` |
| 5 | the stamp | holds 9 min, on a Board wall | a War mark | `WarTab.tsx` |
| 6 | the grid | 3-min change summed ATM ±7, each side | WRITER FLOW ±7: UP / DOWN / PAUSED / BACK / RISK | `jarvis.reads` |
| 7 | the grid | CE add/cover × PE add/cover, per 5 min | Sides: REAL / BACKED / CAPPED / SQUEEZE / HOLLOW / FLAT | `sides.py` |
| 8 | Dext footprint (else the book) | 2-min delta ≥ 2× its median | a PUSH | `handshake.py` |
| 9 | the push | OI at the ONE attacked strike within 4 min | TOOT / PHANS / TIKI / NAHI | `handshake.answer` |
| 10 | the answer | the next chain minute must agree | held, or wapas | handshake-2 |
| 11 | the answer | premium move minus what delta explains | who: WRITERS / KHAREEDAR (TIKI, PHANS only) | `handshake.who_opened` |
| 12 | walls + pushes | the wall behind / ahead, chapters | the FIGHT and its story | `jarvis` KAHANI |

Ruled out on the record: **OI does update every minute** (only 255 of 6,732 one-minute steps unchanged on 29 Oct, 4 %),
so speed is not reading stale exchange steps.

---

## 1. Every scenario: what the market does, how we decode it, where it breaks

Both ways: every UP row has its DOWN mirror with CE and PE swapped.

| # | Scenario | What the OI / flow shows | How we decode it now | Verdict |
|---|---|---|---|---|
| 1 | Trend up, full fuel | CE writers cover + PE writers add | Sides REAL, ±7 UP, War: CE hatched / PE solid, TOOT at CE walls | **OK** |
| 2 | Trend up, one side only | CE cover with PE flat, or PE add with CE flat | ±7 needs BOTH sides ≥ 10L / 3 min | **GAP G3** |
| 3 | Range / pin | both sides add | Sides CAPPED, call RANGE, War both solid | OK |
| 4 | Squeeze / expansion | both sides cover | Sides SQUEEZE | OK (seller-line wording owed) |
| 5 | Nothing happening | both flat | NO TRADE | OK |
| 6 | Push breaks the wall | OI falls at the attacked strike | TOOT, held at the next minute | **GAP G5** (who covered is never asked) |
| 7 | Push meets new OI, wall holds | OI rises at the strike | TIKI = "deewar tiki" | **GAP G4** (half were buyers) |
| 8 | Push goes through new OI | OI rises, price passes 0.3 step | PHANS (writers trapped) | OK (none in 3 days) |
| 9 | Push, wall does not answer | strike OI moves < bar | NAHI, grey tick | **GAP G1** (the band answered) |
| 10 | Answer, then it comes back | crosses, next minute disagrees | wapas | OK |
| 11 | Writers pause mid-trend | the covering side stops | PAUSED (A165: a pause, not a top) | OK |
| 12 | Writers stop at the top + a delta spike | pause + 3-min delta ≥ 2× against | RISK, carried until the next state | **GAP G2** (carried for hours) |
| 13 | Writers move a strike | cover k, add k + 1 step | War shows both rows apart; nothing names it | **NOT READ G6** |
| 14 | The fight moves with price | the battle shifts to new walls | the fight stays on its first wall | **GAP G7** |
| 15 | OI up from buyers, not writers | long build-up in CE or PE | strips and marks say "likh" | **GAP G5** |
| 16 | OI down from buyers leaving | long unwinding | strips and marks say "chhod" | **GAP G5** |
| 17 | The open (first 30 min) | scale tiny, fast flips | same rule as all day | OK, noise is all day (G8) |
| 18 | Expiry day afternoon (NIFTY Tue, SENSEX Thu) | the expiring week unwinds everywhere | read as covering; no pin / gamma read | **NOT READ G9** |
| 19 | Roll week | OI moves to next month | fuel = sum or next month (disputed) | owed (already listed) |
| 20 | Late start / laptop asleep | holes, backfill, late-born pushes | backfill tagged; strips and arrows draw it like live | **GAP G10** (small) |
| 21 | Dext closed | flow from the book (src B) | pushes still fire; War does not say whose flow | **GAP G11** |
| 22 | 15:30–15:40 | chain stops, F&O trades on | named in health | OK |
| 23 | SENSEX | NIFTY's flow + SENSEX OI (§1q) | pushes use NIFTY flow; Jarvis's SENSEX speed / signs / RISK get no flow | **GAP G13** |
| 24 | BANKNIFTY | chain OI too small | 40 of 41 pushes NAHI on 29 Oct | **GAP G14** |
| 25 | All three in sync | 10 / 25 / 35 pts in 5 min | Jarvis chip only | not on War (small) |
| 26 | Big print at a level | BADA PRINT | decoder | not on War (small) |
| 27 | Replaying a past day after midnight | — | `/api/jarvis?day=` without `upto` reads "could not check" | **GAP G12** (tooling) |

---

## 2. The gaps, worst first

### G1. NAHI reads one strike; the answer was next door — biggest misread

- **Evidence [M], 29 Oct:** of 24 NAHI pushes, the band (attacked strike ±2) moved past the strike's own bar in **14**
  within the same 4 minutes, and past **twice** the bar in **8**.
  - 13:53 ▲ push at 22,900 CE: at the strike −1.3L (NAHI); the band **−14.2L** (call writers covering = a TOOT).
  - 11:09 ▼ push at 22,800 PE: at the strike −2.5L; the band **−11.1L** (put writers covering).
  - 13:34 ▲: band −10.5L. 14:25 ▲: −8.4L. 10:36 ▼: band +8.3L (put writers adding = defended).
- **Why:** the same gap she found on 29 Oct ("look at all the strikes ±5 to 7"), still inside the handshake.
- **Cost:** a TOOT that happened reads "no answer". 24 of 31 pushes NAHI on 29 Oct, 23 of 30 on 28 Oct.
- **Fix:** read the answer at the strike AND the band (±2); when the strike says NAHI and the band crosses 2× the bar
  [I], the word comes from the band, tagged "band". The handshake-2 hold applies to both. `handshake.answer`.

### G2. RISK is carried for hours

- **Evidence [M]:** RISK covered 149 of 386 minutes on 29 Oct and 142 on 28 Oct.
  - 29 Oct: RISK at 10:38, carried until 12:50 (132 min) on a day that closed +236.
  - 28 Oct: "TOP RISK since 13:19", still on at the close.
- **Fix:** RISK is an event, not a state. It holds 9 minutes [I], then falls back to PAUSED unless price confirms
  (a lower high for a top). `jarvis.reads` writers.

### G3. Writer flow ±7 only counts both sides together

- **Evidence [M]:** minutes with the 3-min fuel past 10L:

  | Day | both sides | CE covering only | PE adding only |
  |---|---|---|---|
  | 27 Oct | 50 | 60 | 123 |
  | 28 Oct | 14 | 22 | 27 |
  | 29 Oct (+236 pts) | 18 | 15 | 35 |

  On 29 Oct the state read UP for 33 minutes in all.
- **Fix:** one-sided legs get their own state ("UP · calls only" / "UP · puts only"), weaker than full UP, the way Sides
  separates REAL from BACKED. `jarvis.reads` writers.

### G4. TIKI by buyers reads "deewar tiki"

- **Evidence [M]:** TIKI where the OI was opened by **buyers** (premium rose more than delta explains):
  29 Oct 2 of 2, 28 Oct 1 of 2, 27 Oct 2 of 7. Five of 11.
- **What it really says:** buyers opening at the wall are betting it breaks. It is fuel FOR the push, the opposite of a
  defended wall.
- **Fix:** the word follows who.
  - TIKI + WRITERS = "deewar tiki".
  - TIKI + KHAREEDAR = "kharidar ghuse" (buyers in).
  - "?" says so.

  War chip and rail, the stream line, Jarvis. `handshake` + `WarTab.tsx`.

### G5. "Who" is never asked for covering, nor for the strips

- **TOOT:** OI falling at the wall can be writers buying back (fuel) or buyers selling out (no fuel). `who_opened` runs
  only for TIKI and PHANS.
- **Strips and marks:** every OI rise is "likh" and every fall "chhod", whoever did it.
- **Fix:**
  - TOOT: the same premium-minus-delta test, mirrored (premium up more than delta = shorts buying back). One function.
  - Strips: need delta per strike per minute in `/api/oihist` (the chain record has it); then a strip says
    likh / kharid / chhod / bech. Server side, bigger.

### G7. The fight sticks to its first wall

- **Evidence [M]:** 29 Oct, one fight all day, 22,700 PE from 09:15 to 14:04, while spot sat 97–241 pts above it from
  10:15. The day's battles were at 22,800, 22,900 and 23,000.
- **Fix:** a fight ends when spot has been more than 2 steps [I] past its wall for 15 minutes [I]; a new one starts at
  the nearest wall ahead. `jarvis` KAHANI.

### G6. Writers moving a strike is not named

- **Example:** cover 22,800 CE and add 22,900 CE in the same minutes means the cap moved up, not that the writers gave
  up.
- **Fix:** on War and in Jarvis, a SHIFT mark when one side covers at k and adds at k ± 1–2 steps within 6 minutes
  [I]. Listed in the 29 Oct checklist as "wall migration"; it is still unbuilt.

### G8. The 5-minute state flips about 30 times per strike-side a day

- **Evidence [M]:** 551 stamps on nine strikes on 29 Oct, spread evenly: 35 at 09:15–09:45, then 33–58 every half hour.
- **Effect:** the rule describes noise as often as moves. War already waits 9 minutes; the Speed tab's KRAM lists every
  flip.
- **Fix:** the Speed tab's KRAM uses War's 9-minute settle.

### G9. Expiry day has no mode

- **What happens:** on 0 DTE the expiring week's OI unwinds all afternoon, so every strike reads "chhod". Pin and gamma
  after 14:30 are not read.
- **Fix:** tag 0 DTE on every OI read; after 14:00 on 0 DTE, covering is labelled "expiry unwind", not fuel.

### G13. SENSEX reads have no flow in Jarvis

- **Evidence [M], 29 Oct:** SENSEX pushes came from NIFTY's Dext flow (31, as §1q says). But Jarvis's SENSEX `flow` is
  empty for 384 of 384 minutes, so its speed, signs and RISK for SENSEX read "?".
- **Fix:** the SENSEX frame's flow = NIFTY's flow, as the pushes already do.

### G14. BANKNIFTY pushes mean nothing

- **Evidence [M], 29 Oct:** 40 of 41 BANKNIFTY pushes NAHI; its chain OI is too small to cross the 3L bar (Jarvis's own
  health says so).
- **Fix:** on BANKNIFTY say "OI too small to answer" instead of drawing 40 NAHI ticks.

### Small ones (no method change)

- **G10.** War strips and arrows draw backfilled minutes and late-born pushes like live ones. Fix: draw them lighter,
  as the bands already are.
- **G11.** War never says whose flow made the pushes (Dext or the book) or when the flow was blind. Fix: one health
  line from Jarvis's `health`.
- **G12.** `/api/jarvis` for a past day without `upto` uses the clock after midnight and answers "could not check".
  Fix: a past day defaults to the whole session.

---

## 3. What is solid (checked, keep)

- **OI updates every minute** (96 % of steps change), so speed is real.
- **The hold rule (handshake-2):** every answered TOOT and TIKI on 27–29 Oct (28 of them) held at the next minute.
- **The full-fuel case:** Sides REAL plus ±7 UP agree when both sides move.
- **A pause is not a top (A165):** PAUSED with no delta spike stays a pause.
- **Health names its holes:** Dext missing, chain missing, the late start, BANKNIFTY too small.
