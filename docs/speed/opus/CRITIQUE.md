# RAFTAAR round 2 — OPUS critiques FABLE (27 Oct 2026)

Both engines were run on the same index, day and minute with `compare.py` in this folder. It imports both
`raftaar.py` files read-only; the full outputs come from that script. NIFTY unless named. F = Fable, O = Opus.

## 0. Census on the same five days (minutes per big word · how often the big word changes · stamped lines)

| day | Fable | Opus |
|---|---|---|
| 8 Oct trend ▼ −310 | KHAMOSH 240 · LOAD 49 · CHAL▼ 32 · changes 42 · stamps 23 | CHAL▼ 242 · ? 57 · KHAMOSH 38 · changes 17 · stamps 18 |
| 21 Oct trend ▼ −470 | KHAMOSH 180 · CHAL▼ 83 · LOAD 31 · changes 52 · 24 | CHAL▼ 208 · KHAMOSH 66 · BINA OI 47 · changes 22 · 17 |
| 22 Oct chop | **CHOP 128** · KHAMOSH 78 · CHAL▲ 61 · CHAL▼ 40 · changes 70 · 37 | CHAL▼ 124 · CHAL▲ 103 · KHAMOSH 75 · **CHOP 24** · changes 27 · 20 |
| 26 Oct trend ▲ +300 | KHAMOSH 164 · LOAD 48 · CHOP 41 · CHAL▲ 39 · changes 59 · 28 | CHAL▲ 158 · KHAMOSH 90 · CHAL▼ 61 · changes 19 · 26 |
| 27 Oct expiry | KHAMOSH 110 · CHOP 29 · PIN 17 · changes 47 · 12 | CHAL▲ 73 · KHAMOSH 70 · CHAL▼ 21 · ATKA 20 · changes 16 · 15 |

## 1. STEAL — what Fable got right that I missed or did worse

1. **CHOP that actually says CHOP.** On 22 Oct Fable reads CHOP for 128 min; I read 24. Its rule is a leg each way inside
   30 min, with no OI-backed leg now. It is simpler than my swing sequence and it reads her stop-loss day as what it was.
2. **THAK RAHA from the fuel fading** (the with-flow over the last 5 min ≤ ½ its peak in this move). On 26 Oct it fired 10:06–10:09 while price made
   the 10:08 high of 22,699; I said `JAARI 10/10` at the top. On 22 Oct it fired at 11:55 (22,646) right after the low;
   I said `JAARI 7/10`.
3. **WITH vs AGAINST as two numbers** (losing side's cuts + winning side's adds, against the losing side's adds), plus
   the LOSING / WINNING side frame. This reads her addendum directly ("price up while CE adds = absorbing or trapped") and
   is clearer than my net Z plus push table.
4. **LOAD** (one side ≥ 3× its floor, price flat) is her dwell-and-load, named. **UNWIND** (both sides covering;
   after 15:00 "band ka unwind") is a state I never had (26 Oct 15:06, 8 Oct 15:13).
5. **The 5-min fallback ("abhi")** when the 15-min window is QUIET. On 22 Oct Fable says `CHAL ▼ SAATH` at **11:43 /
   22,690** and reaches PAKKA at 11:46. I said it at **11:48 / 22,626**, 64 pts later (my CHOP gate wanted BADA price
   plus OI).
6. **§1d front stamps in her Board's own words** ("phir BUILDING", SHIFT → k2), kept under "sab". The header
   `15m +167 · 60m +227 · din +197` puts a swing read in day context, which my design lacks.
7. **P = 0.18 % of spot** is effort.py's existing yardstick, not a new number. Its exploration also stated plainly that
   the lean does not predict the next 5 min (26 Oct inverts, 34/108).

## 2. WRONG — where Fable's design would mislead her (both outputs quoted)

**W1. A trend day reads as "kuch khaas nahi"** (rolling-hour floor, no move memory). 8 Oct 12:22–12:40, spot
22,324 → 22,276:
```
12:28 22325 | F: LOAD CE 22300 THEEK 4/6            | O: CHAL RAHA ▼ · SHURU 5/10  PUT BHAAG + CALL LIKHAI ▼
12:33 22283 | F: CHAL ▼ SAATH SHURU THEEK 3/6       | O: CHAL RAHA ▼ · JAARI 7/10  PUT BHAAG + CALL LIKHAI ▼
12:39 22276 | F: LOAD CE 22300 PAKKA 5/6            | O: CHAL RAHA ▼ · JAARI 7/10  PUT FLOOR NEECHE SHIFT ▼
```
Over the whole day Fable shows KHAMOSH for 240 min and CHAL ▼ for 32 min on a −310 pt day; Fable's own §9c concedes
this on 6 Oct.

**W2. "Nothing" stamped right after the day's biggest push.** On 26 Oct the move ran +250 pts in 20 min to the 10:08 high:
```
10:13 22671 | F: KHAMOSH              | O: CHAL RAHA ▲ · JAARI 8/10  ATKA ▲ (pause, pressure still up)
10:15 22674 | F: KHAMOSH  (stamped)   | O: CHAL RAHA ▲ · JAARI 9/10
```

**W3. Blind in the first hour** (its floors are the medians of the opening churn). 21 Oct 10:03:
```
F: CHAL ▼ BINA OI ("price akela")   CE adds +45L, PE cuts −28L in 15m, spot −74 — floors T PE 45.6L, TA CE 51.6L
O: CHAL RAHA ▼ · JAARI 10/10  PUT BHAAG + CALL LIKHAI  [23100CE +13L 23000CE +11L | 23100PE −16L]
```
Between 09:49 and 10:14 Fable flips BINA OI ↔ SAATH 8 times.

**W4. PIN when one side out-writes the other 3–8×.** "Balanced" is judged on the OI stock at k, not on the writing:
- 27 Oct 11:24: `F: PIN 22750 · baari-baari balanced · net45 CE +28L PE +227L`, while `O: ATKA ▼ 5/9`: CALL writing
  22750/22800 +80L in 15 min, PUT covering −49L, price flat. Those exact call strikes then covered −103L at 12:43 (+70 pts).
- 8 Oct 10:14, on the trend-down day: `F: PIN 22500 balanced · CE +133L PE +46L`. Price was −140 pts by 11:30.

**W5. "Could not check" shown as quiet.** On SENSEX 8 Oct, spot is 71,558 at 13:30 and the lowest recorded strike is
71,600. Fable's "nine nearest" sit at or above spot and the PE floor zone is empty:
```
13:30 SENSEX 71558 | F: KHAMOSH (13:00-15:00: KHAMOSH / CHOP) | O: ? PADH NAHI SAKE — spot at the chain window's edge
```
This breaks house rule 6 (three absences are three sentences).

**W6. SENSEX runs on 5-min windows.** At 73,200 CE on 22 Oct, 55 of 367 five-minute windows hold one OI update and 312
hold two, so the 5-min speed halves on the clock about 15 % of the time. The effect on its stamps is small (0–2 TEZ/THAK a
day), but every speed word is affected.

**My own wrongs, from the same runs** (they go into the converged design):
- I was late on 22 Oct 11:43 (above).
- I held a KAMZOR leg as the big word: 26 Oct 12:11–12:45 showed `CHAL RAHA ▲ · RUKA 3/10` for 34 min while price sat at
  22,580–22,630. Fable's KHAMOSH was right there.
- I kept a stale flat picture: 27 Oct 12:36–12:41 showed `ATKA ▼` while price rose 22,774 → 22,792.
- I was late on 21 Oct: `BINA OI 3/10` from 09:51 to 09:59 while Fable already read CE PRESS (THEEK 3/6) at 23,039. Moving my reference
  to 15-min slots did not fix it (tested).

## 3. THE DECISIONS

| decision | my vote | Fable's case | evidence |
|---|---|---|---|
| **Noise bar** | A flow is notable when it clears **either** bar: its rank vs prior sessions (same index, same day kind, same 15-min slot; rank.py) **or** 1.5× today's own median (Fable). Each one that clears is a separate grade check. History alone can never adapt a trend away; today's own catches a quiet day's first burst. | the brief says "the day's own distribution at that time"; no history needed; separates calendar sizes (BNF 0.3–4L vs 64L) | 8 Oct KHAMOSH 240 (F) vs CHAL▼ 242 (O); 21 Oct 10:03 BINA OI (F) vs 10/10 (O); 21 Oct 09:51 F early, O 3/10 until 10:00; 6 Oct grind invisible (F §9c) |
| **When a move ends · trend day** | Keep a **held leg**: a pause is RUKA, never KHAMOSH. Add Fable's THAK RAHA (fuel fading). The leg drops to the flat word after **10 min at KAMZOR**. The day-scale trend stays with §1o / THE READ, and the header shows `15m · 60m · din` (Fable's). Both of us read 26 Oct as swings, and that is correct at this scale. | a minute is a move or it is not; fewer rules | 26 Oct 10:15 KHAMOSH after +250 (F); 8 Oct W1; 26 Oct 12:11–12:45 KAMZOR leg (O) |
| **CHOP vs PIN vs alternating moves** | CHOP = Fable's rule (a leg each way inside 30 min, no OI-backed leg now). The legs that come out of it carry my `[CHOP ke andar]` tag and a failed grade check. A leg inside chop needs OI behind it (not BADA price plus OI). PIN only when both sides' 45-min writing is **within 1:2**; otherwise it is LOAD of the bigger side. | stock balance at k plus turn-taking loads = PIN | 22 Oct CHOP 128 (F) vs 24 (O); 22 Oct 11:43 vs 11:48; 27 Oct 11:24 1:8 "PIN"; 8 Oct 10:14 3:1 "PIN" |
| **Grade** | A count n/N over the checks that could be read. A missing check is dropped, never counted as a miss. The **size gate**: no story rises above the bottom word unless its own OI flow clears the bar. Checks: size-history · size-today · held 3 · held 15 · 2+ strikes · both peers · fut leg (where recorded) · price still moving. Words **MAZBOOT / THEEK / KAMZOR**, never PAKKA, because "pakka" reads as certainty. | 6 checks, shorter; PAKKA / THEEK / HALKA | Fable never checks the futures leg or whether price is still moving; O's 10/10 at 21 Oct 10:03 vs F's BINA OI |
| **Stamp volume** | Stamp a picture only when it reaches THEEK; inside a leg, only TEZ, the first THAK RAHA and the END; KHAMOSH once if it lasts ≥ 5 min; PADH NAHI SAKE always; side events only for a roll or a BADA cover into price. §1d front changes go under "sab" (Fable's). **Target ≤ 15 per index on a non-chop day.** | every key change held 3 marks | NIFTY on the five days: F 23 / 24 / 37 / 28 / 12, O 18 / 17 / 20 / 26 / 15; F changes its word 42–70 times a day, O 16–27 |
| **SENSEX cadence · BNF thin OI** | SENSEX windows sized in OI updates: 8 / 16 min, hold 6. Its order flow comes from NIFTY (§1q) and its OI is its own. BNF: the relative unit, with absolute lakh always printed (ATM 1.7L a side on 8 Oct). BNF's monthly expiry uses today's own (one prior expiry). | the same windows everywhere | 55/367 single-update 5-min windows on SENSEX; Fable notes BNF "numbers in thousands" |
| **One vocabulary** (face words) | **CHAL RAHA ▲/▼** · SHURU / TEZ / JAARI / RUKA / **THAK RAHA** · **BINA OI** (Fable's: clearer than my KHAALI) · **CHOP** · **PIN @k** · **LOAD · CALL/PUT likh rahe** · **ATKA** (both engines pushing one way, price flat) · **UNWIND · dono nikal rahe** · **KHAMOSH · kuch khaas nahi** · **PADH RAHE** (warming up) vs **PADH NAHI SAKE · reason** (two sentences; not SOCH RAHA). Side words: bhaag rahe · cap/floor roll · ulta likh rahe · saath likh rahe · deewar ban rahi / hati · booking. | — | — |

Files: `compare.py` (side-by-side, read-only on both folders). Nothing was written outside `docs/speed/opus/`.
