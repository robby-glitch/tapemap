# KAHANI review, round 1: Claude's answers to Fable's 90 questions (28 Oct 2026, after close)

**Method.** Data questions were measured on the record using `scripts/answers_m.py` and `scripts/oct27_check.py`. Both are read-only, print only, and never write under `data/`.
- **Coverage:** 16 recorded NIFTY book days (01–28 Oct); BANKNIFTY and SENSEX books on the same days; the chain grid; `trigger_log`.
- **Tags:** [M] measured, [I] inferred.
- **Decisions:** "Decided" means decided as the trader, under Mary's standing rule. "Hers" means it changes her own definitions, so it is hers to sign.

## Seven findings the measurements forced (they change the spec)

1. **The answer un-crosses. Q7 [M].** Of 103 NIFTY answers (TOOT / PHANS / TIKI) over 16 days, **17** read differently at m+4 than at the first crossing.
   - 13 of the 17 are first-crossing TOOTs that read NAHI at m+4. Examples:
     - 19 Oct 10:41▼: −12.8L, then +4.4L;
     - 27 Oct 14:04▼: −11.8L, then +4.1L;
     - 05 Oct 10:26▼: −12.4L, then −2.4L.
   - Both 28 Oct TOOTs held.
   - **Decided:**
     - TOOT shows live as `TOOT?` at the first crossing.
     - It is stamped TOOT only if the crossing still holds at the next chain minute (or at m+4, if that comes first).
     - Otherwise it is stamped `wapas`, which counts as NAHI in DASTAK.
   - This is handshake-2. Re-run every logged push.
2. **The verdict at the TRIGGER never read GHUMEGA on the five spec rows. Q44 / Q45 [M].**
   - **27 Oct 12:51 SELL:**
     - The ULTA PUSH TOOT (12:49▼, −9.9L at 22,750s PE) was known only at **12:53**, two minutes after the trigger.
     - FUEL is not readable on that day (finding 4).
     - So at the trigger it reads **SAAF NAHI 1/1** (NEXT PUSH ✓: 12:44 NAHI). It becomes GHUMEGA 2/2 at 12:53.
   - **27 Oct 14:18 BUY:**
     - 14:04▼ first-crossed TOOT −11.8L at 14:05 and then un-crossed (finding 1).
     - Under the hold rule it is NAHI, so the context is (a): FUEL ?, WALL ?, DASTAK ✓ (14:15 NAHI). That reads **SAAF NAHI 1/1**.
   - **Overall:** the spec's table claimed GHUMEGA twice; neither holds at the trigger. The verdict is honest only as a **timeline** (ARM → TRIGGER → +5 → +10 min), not as a single trigger stamp. See Q40 / Q44.
3. **12:12 SELL WALL is ✗, not ?. Q17 [M].** On the recorded chain, 22,700s CE reads §1d UNWINDING at 12:12. That is 16 % off its 11:08 peak, with slope −3.5L, and steady from 12:11. Before that it flickers STALL↔UNWIN 11 times between 11:40 and 12:09. CHALEGA now holds on two pieces, FUEL ✗ and WALL ✗.
4. **Roll week and expiry day poison the near-month fuel. Q29 [M].**
   - NIFTY's Oct contract read COVER in **10 of 10** runs on 21 Oct and 6 of 9 on 22 Oct.
   - By contrast, 01 Oct had 5 FRESH and 2 COVER.
   - On 27 Oct (the Oct expiry), the Nov contract alone ran **FRESH +44,325 lots from 09:20 to 14:16**: the roll arriving.
   - Near + next summed flips FRESH / COVER minute to minute.
   - **Decided:**
     - RASAD reads "? (roll hafta)" from T−3 sessions to the monthly expiry, unless near and next are both subscribed and summed.
     - On the near-month's expiry day it reads "?" even when summed.
   - The 27 Oct rows' FUEL is "?".
5. **The book alone gave a false KHATAM. Q27 [M].**
   - On the book's OI, 28 Oct's cover run ended "KHATAM 12:54" (−1,325 lots by 12:51), because minute 12:54 held only 12 s before the laptop slept.
   - REST shows the run went on to 12:59 (−2,153), with KHATAM at 13:02.
   - **Decided:** a minute whose last book row comes before :50 s is a hole.
6. **Futures OI is a once-a-minute publish. Q23 / Q63 [M].**
   - The median gap between OI changes is 60.2 s (27 Oct) and 60.6 s (28 Oct); the p90 is 62–64 s.
   - A minute holds at most 2 distinct values. The longest gap outside the sleep was 179 s.
   - So the 3-minute KHATAM means three publishes with no new extreme: a market fact at 1-minute resolution.
   - **Decided:** a minute with no OI change is "no publish", and it does not advance the KHATAM clock. In 385 minutes there were 377 changes, so an unchanged minute is almost always a missed publish.
7. **§1d's peak depends on when the laptop starts. Q17 [M].** On 28 Oct the chain began at 11:07, so the 22,700s CE peak read +49.8L at 11:08. A136's 10:37 peak (+57.1L) was never seen live. THAKAN and WALL therefore need the chain backfill to seed the peaks. This is a data-truth item (anytime-start), not a rule change.

---

## A. The handshake

1. Pushes start about 11 minutes after the flow begins, not 30. The rule needs 10 `d2` samples in the last 30 minutes.
   - [M] On days with the book from 09:15–09:17, the first push came at 09:26–09:30.
   - [M] 28 Oct: the book started at 11:07 and the first push came at 11:25.
   - **Decided:** coverage says `push padh nahi sakte: flow history (hh:mm tak)`. Until then the fight shows DEEWAR + RASAD only.
2. [M] Trend days are not silent. They show who wins the wall fights:

   | Day | Pushes | ▲ | ▼ |
   |---|---|---|---|
   | 08 Oct (−311 pts) | 28 | NAHI 12, TOOT 0 | NAHI 12, TOOT 4 |
   | 21 Oct (−315 pts) | 26 | NAHI 10, TOOT 0 | NAHI 10, TOOT 5 |
   | 26 Oct (+301 pts) | 35 | TOOT 4, PHANS 1, TIKI 3 | TOOT 1 |

   On trend days, counter-trend pushes almost never get a TOOT. This becomes an addition candidate: the session's TOOT tally by side (round 2).
3. No minimum wall. A fight needs a §1d top-2 front, and those are ranked by absolute OI within the nine nearest strikes. [M] 28 Oct, the day after an expiry: the walls were 15–50L of change on 50L+ of OI (22,700s PE OI 52.8L). The 3L bar was not loose there. Revisit on SENSEX's Friday.
4. **Decided:** KAHANI reads every push's answer **at the fight's wall** (`answer(..., k=wall)`, as `defend` does). The handshake row keeps its own attacked-strike answer. The ladder shows both stamps when they differ. A push counts as a DASTAK when it is into the fight's side and its attacked strike is the wall or nearer to price. [M] On 28 Oct every attack was at 22,700, so the two never differed.
5. `ans None` shows as `?` in the sequence and counts as a knock, never as NAHI: `DASTAK ×5 · jawab 0 · ? 1`.
6. A stamp is never edited. A later contradicting reading makes a new stamp (`TOOT → wapas`). See finding 1 for the hold rule that makes this rare.
7. Finding 1. The guard is adopted, as handshake-2.
8. [M] 12:49 → 12:51: the residual was −1.13 (−2.54 by 12:52) against a 2-tick bar of 0.10, with IV going 16.33 → 16.28.
   - [I] An ATM NIFTY weekly put at about 7 days has a vega of about 12–13 per vol point. So the residual is about 0.1–0.2 vol points: consistent with writing, but thin.
   - The 2-tick bar sits far below normal IV noise, so NAYA FLOOR at 12:49 stands on a weak WHO.
   - **Candidate:** a WHO bar in vol points (|residual| ≥ max(2 ticks, ~0.25 vol × vega)). It must be measured on the 16 days' rows before it is adopted.
9. Same strike, both sides:
   - **Decided:** NAYA FLOOR needs the same strike's other side to be UNWINDING or TOOT'd: a **flip**, the cap becoming the floor. That was 28 Oct 22,700: CE −34L off peak while PE +27L [M].
   - When both sides at one strike are BUILDING or STALLED, that is PIN evidence (straddle writing), not a floor.
10. SENSEX has one fuel: NIFTY's RASAD (§1q). [M] SENSEX's own futures at a bar of 10 give 2–22 "runs" a day, mostly one minute long (28 Oct: 9 runs, 5 of them single-minute). The handshake's SENSEX fut leg stays in the log but is never shown.
11. **Decided:** DASTAK counts pushes and its chip carries the span: `DASTAK ×5 · 75 min` vs `×3 · 8 min`. Pressure is frequency.
12. [M] Flow came from Dext on every push from 01 to 26 Oct; on 27 Oct, 10 from Dext and 20 from the book; on 28 Oct, all 18 from the book (Dext NSE-61471 never landed). A late Dext re-post after the 20 s grace can change a minute already read (see Q64).
    - **Decided:** step 1 first measures the scale of Dext delta against the book's quote-rule delta, on the same minutes (27 Oct morning). Then KAHANI's push median uses one source per index per session, the book (always there while the server runs).
    - Dext becomes a cross-check line only. A mid-session source flip can no longer make or hide a push.

## B. The fight and its chapters

13. A ▼ push during DASTAK is a chip on the same fight (`ulta dastak ▼ 12:49 · TIKI 22,700s PE +4.3L`), not a new fight. Only a TOOT, a change of the wall ahead, or price leaving changes the fight.
14. With no front within 2 steps, the hero reads `KHULA MAIDAN · aage deewar nahi (22,800s CE, 3 step)`. The WALL piece is **✗ "koi deewar nahi"**: checked, and no defender found. A fade into open ground has no supply behind it.
15. [M] 22,700s PE was **not** a §1d top-2 front at 12:49. The PE fronts were 22,500s STALLED and 22,600s UNWINDING; 22,700s PE entered at 13:00 (BUILDING +24.3L). So NAYA FLOOR lives off-front by design: it is the handshake's TIKI / floor_cap strike. It becomes the next fight's wall when it enters the top-2.
16. A wall UNWINDING with no push yet gets its own chapter, **KHISAK** (`deewar khisak rahi 22,700s CE −8L peak se`): writers leaving without being hit, a lead.
17. Finding 3 plus finding 7.
    - No separate off-peak ✗: §1d itself reads UNWINDING at 12:12.
    - **Decided:** the THAKAN / KHISAK *stamp* needs UNWINDING to hold for 3 minutes (stamped 12:13 [M]), because §1d flickers.
    - The verdict's WALL piece reads the raw §1d state, her registered read.
18. **Decided: PHANSE is its own chapter.** It means writers trapped under water: stored fuel. First principles: expect a pullback, then the squeeze when price comes back through. TOOT means cut: fuel released now.
19. A broken strike that rebuilds by ≥ the bar after its TOOT gets a `WAPSI` chip. [M] 22,700s CE turned BUILDING again at 13:30 (+19.2L). WAPSI after KHATAM is PIN or rotation evidence. After the ending, it is a new DEEWAR at the same strike.
20. Yes. `2/2 khisak` when both top fronts on the fight's side are UNWINDING. [M] 22,700s and 22,600s CE both read UNWINDING from 12:11.
21. A run with no TOOT appears in the fuel card always, and in the chain as `RASAD bina toot` (e.g. `DASTAK ×3 · RASAD cover ▲ −775`): the break is being funded.
22. A `?` add behind shows as `peeche +4.3L PE (kaun: ?)`. It is never a chapter.

## C. The fuel run rule

23. Finding 6.
24. [M] The two totals differ a lot: 27 Oct COVER 12:33 reads −4,970 from start−5 but −3,327 from start. Many roll-week "runs" never extend at all (lots from start = 0).
    - **Decided:** the lots run from OI(start−5), but never from before the previous run's last extreme (no double count).
25. **Decided:**
    - The direction is stamped at the run's start.
    - If the sign of p5 holds the other way for 3 minutes while the run lives, a new stamp is made (`cover ▲ → ▼: ab longs nikal rahe`).
    - The chip shows the latest stamp.
26. Per index: NIFTY |p5| < 5; BANKNIFTY 15 [I]. SENSEX never reads its own fuel.
    - FRESH at a flat price shows as `RASAD jama ho raha +2,000 · disha ?`: fuel loading.
    - It is never counted as a verdict piece. It does go into the scenario lines (`toota to +2,000 lots ka eendhan`).
27. REST is fetched in the first pass after a hole is seen (a book gap > 60 s, or a partial minute; finding 5).
    - KHATAM is stamped at its true minute (13:02) with its known-at (the wake).
    - Both times go to the log.
28. If REST has the hole too:
    - the run closes as `KHATAM ? (andhera)`;
    - a new run may start only after 5 clean minutes.
29. Finding 4. `FUT_LOTS` is in lots, and the lot comes from `v2feed.LOTS` live, so a lot change keeps the bar in the trader's unit.
30. **Decided:** w5 needs both of its minutes ≥ 09:16, so the first run can come at 09:21. 09:15 carries the opening auction.
31. p5 is the book's last LTP of the minute, the same feed as the OI. The REST close is used only inside a hole, tagged `rest`.
32. [M] Runs per day at the current bars:
    - BANKNIFTY (200): 1–11 a day over the recorded days;
    - NIFTY (500): 0–17;
    - SENSEX (10): 2–22, mostly single minutes.

    BANKNIFTY's bar works. SENSEX's does not, which confirms Q10.
33. Confirmed [M, code]: `oi` is the contract's total OI level (units; divided by the lot it gives lots), and `fut_minutes` keeps the last value of each minute.

## D. The endings

34. **Decided: PALAT has two forms.**
    - **The wall form:** an opposite push answered TOOT at the floor or cap.
    - **The fuel form:** after KHATAM, a run the other way (`RASAD ulta: naye short ▼ +x`).

    Either one stamps PALAT; both make it `PALAT 2/2`. Fresh shorts at the top after the cover are the classic top.
35. **Decided:** PIN's second clause is dropped as an ending and becomes a context chip (`dono taraf deewar 1 step`). Twenty minutes with no push after KHATAM reads `KHAMOSH`.
36. Yes. PALAT reads the answer at the floor or cap strike (`k=floor`), and at the attacked strike too. Both are shown.
37. After PALAT, the new fight is the next wall ahead in the new direction. The reversed run is its RASAD.
38. Endings are live stamps carrying their known-at. The evening view also shows when each one really began.
39. A run still open at 15:30 reads `KHATAM nahi (band 15:30)`. The next morning starts fresh, and the gap tells the overnight story.

## E. The band verdict

40. **Decided:**
    - Recomputed every minute and stamped on change, at most one stamp a minute, each with its pieces.
    - The screen shows the timeline ARM → TRIGGER → +5 → +10.
    - The evening scores the TRIGGER stamp and also shows the +5 and +10 stamps, so we see whether waiting helps.
41. Agreed: context (b) lasts until the fight ends (an ending, or a new fight), not a 30-minute clock.
42. **Decided, for (a) only:** FUEL ✗ also when a run drove against the trade in the last 30 minutes and no opposite run has come since. Within a trend, a KHATAM is a pause.
    - In (b), KHATAM stays ✓, because "is the fuel spent?" is (b)'s whole question.
    - The TOOT tally (Q2) is a round-2 candidate.
43. Yes, on screen. The verdict line keeps updating while the zone trade lives (`ab CHALEGA: naya run ▲`). In a marked trade, l6 speaks.
44. Confirmed, and it is worse than you thought (finding 2). **Decided:**
    - the timeline (Q40);
    - Telegram carries the TRIGGER verdict;
    - **one** follow-up Telegram line if the verdict upgrades or downgrades within 10 minutes of the trigger while price is within 1 step of entry. It counts in the budget.

    Your soft ✓ (silence at the extreme for N minutes) is a candidate for round 2, to be reproduced on the replay rows before anyone reads it as more.
45. [M] At the 27 Oct 12:42 ARM the 12:40 TOOT was not known yet (am 12:43). So it read (a): FUEL ? (expiry), WALL ?, DASTAK ? (12:40 pending): **SAAF NAHI**. The TRIGGER read SAAF NAHI 1/1, and it became GHUMEGA 2/2 at 12:53. She acts on the trigger stamp plus the one follow-up.
46. **Decided:** stated on the face: `jawab padh nahi sakte → GHUMEGA mumkin nahi · sirf FUEL + WALL`. WALL does not count in (b) for them; it answers a different question.
    - [M] At a pure 4 % bar, SENSEX's 12:40▲ and 12:44▲ (−1.1L on 15.7L and −2.5L on 14.6L at 73,200s) would have read TOOT. Those are NIFTY's minutes.
    - So the owed bar matters. It is set in step 2 from 330 SENSEX and 394 BANKNIFTY logged pushes [M].
47. Yes: `2/2 · 1 ?`.
48. Renamed **`pehla padav`** (first stop) = her VWAP / u1, because the rotation she trades runs to VWAP. NAYA FLOOR / CAP shows as `raste mein deewar`. Her rule "the wall ahead, never a target" stands.
49. Yes. The wrong-line is any new run against the trade, signed per side: `galat agar: naya run ▲ ≥500/5m (cover ya fresh long)`.
50. The evening uses the zone's own logged stop, never a KAHANI stop. **Added:** a "max adverse before +30" column.
51. Telegram carries whatever the verdict is, CHALEGA included (`CHALEGA · fuel ✗ wall ✗`). That warning is the most valuable thing it can send. It is 12:12's lesson.
52. **Hers.** My proposal:
    - **GHUMEGA right:** her VWAP / u1 is reached before the zone stop.
    - **CHALEGA right:** the stop is hit before +15, or price clears the wall by 1 step.
    - **SAAF NAHI:** recorded only.
53. [M] 28 Oct NIFTY had zone3 20 arms / 6 triggers and zone 19 / 6. The verdict rides **inside** the existing ZONE Telegram alert, so it adds no message. ARM verdicts never enter the stream or the Float; they live in the LADAI tab's verdict rows.

## F. Indices

54. No.
    - Borrowing NIFTY's TOOT means reading NIFTY's OI for SENSEX, and §1q is "NIFTY flow + SENSEX's own OI".
    - SENSEX's hero shows a context chip, `NIFTY ki kahani: TOOT 12:44`. It is never counted.
    - SENSEX's own answers come once its bar is set (Q46).
55. ANSWER is 4 *minutes*, not steps. The attacked-strike band is −½ … +2 strikes: 200 pts on BANKNIFTY against NIFTY's 100. Since BANKNIFTY runs at about 2.3× NIFTY's price, that is about the same distance in σ terms [I]. No accident.
    - [M] 28 Oct BANKNIFTY: the attacked strikes carried 1.3–1.4L of OI, with a change of 0.0L in 4 minutes on three pushes. BANKNIFTY (monthly only) may not show readable minute OI changes; its answer is "?" until measured.
56. [M] 394 BANKNIFTY and 330 SENSEX pushes over 16 days: enough rows to set the bars in step 2. SENSEX changes of −1.1, −2.5, +0.4 and +0.7L are granular, not rounding.
57. **Decided:**
    - one chip, `NIFTY TOOT 12:44 · SENSEX dastak ×3 · BNF dastak ×2 (bar baaki)`;
    - **"teeno saath"** when same-direction pushes land within 2 minutes in ≥ 2 indices.

    [M] 12:40–12:48: SENSEX ▲ 12:40 / 12:44 / 12:48 (NIFTY's minutes) and BANKNIFTY ▲ 12:42 / 12:46. That would have read "teeno saath ▲" at 12:44.
58. On NIFTY's expiry day, SENSEX's fuel (NIFTY's) carries `NIFTY expiry` after 14:30 and reads "?".

## G. Data truth

59. Coverage names the cause from the book gap. Where the Windows power log can be read (Kernel-Power sleep / wake events), it reads `laptop soya 12:54–13:00`. Push silence after a hole gets its own line: `push padh nahi sakte 13:00–13:11 (flow history)`.
60. **Decided:** after a chain hole, REST-backfill the nine near strikes × 2 sides for the hole's minutes, once, tagged `rest`. Without that, the answer and the §1d slope over the gap are "?".
61. 30 s from the chain minute **landing** (achievable). The floor from the OI change to the screen is about 60–80 s (the publish cadence plus a 1-minute chain). Said plainly on the face's help line.
62. The first pass after waking (≤ 20 s) sees the hole and fetches REST before computing anything.
63. Finding 6.
64. Yes, that can happen. A Dext minute re-posted after the 20 s grace can change `F[m]` after it was read. The book is complete at the minute's close. Hence Q12: the book is primary for KAHANI.
65. Yes. Every stamp carries `known_at` and `shown_at`.
66. **Declared:**
    - the fight's geometry (2 steps, 0.3-step through, the answer band) is **spot**, because strikes are spot and `handshake` reads the chain's `spot` [M, code];
    - fuel is **fut**;
    - her zone3 levels are on fut bars; the verdict converts a zone level to spot with `fold.BIX_MS` (A60's 3-minute basis) before comparing it to strikes;
    - every shown level carries s / f.

## H. Expiry, gaps, news, the open, the last hour, roll

67. **Decided:** every chip carries `EXPIRY` on the index's own expiry day. After 14:30 the verdict is computed but TOOT and PALAT pieces count as "?" (`expiry: TOOT = writers profit book`).
68. Q3 [M]: no minimum is needed on NIFTY.
69. `oi_chg` is measured against the previous close and the top-2 are ranked by absolute OI, so the morning picks the big legacy walls. §1d's slope needs 15 marks, so the morning reads `deewar ki halat ~09:30 se`.
70. Your context (c) for the open is a **candidate**. It rests on one row (09:54 SELL: +133 / −10 [M]); it goes to the replay rows first.
71. **Decided:**
    - a jhatka guard: when the 1-minute fut move is ≥ 3× its 30-minute median and both sides' near fronts drop, the chip reads `JHATKA (news?)` and the verdict is "?" for 5 minutes;
    - §1o's day type rides on the hero as a chip.
72. Yes:
    - spot pieces freeze at 15:15 (CAS);
    - the chain runs to 15:30, fuel on fut to 15:40;
    - after 15:00 every verdict carries `3 baje ke baad` (display only, her practice).
73. [M] The book's `ik` switched to Nov (61471) on 28 Oct. The morning after the monthly expiry, run history starts fresh (`naya contract`). Near + next subscription during roll week is a step-1 item.

## I. What the trader sees and hears

74. **Decided:** yes. One ribbon line (chapter chip + DASTAK count + fuel arrow) ships with step 3. The extension reload is hers.
75. KAHANI lines go on the stream only for TOOT, KHATAM and endings, capped at 12 per index per day. ARM verdicts never go on it.
76. No new sound. Her two bells stay; the trigger verdict rides on the existing ZONE alert.
77. Fixed templates: each ≤ 6 words plus numbers, every one checked by `test_kahani.py`.
78. Every chip carries its number. ✓ / ✗ are from the trade's side in a verdict; on the ladder, colour is by CE / PE side.
79. Yes. Colour by side on the ladder, and by meaning only on the verdict words. Light mode.
80. Both: the logged stamps (`dikhaya tha`) and the rule recomputed now (`rule ab kehta`), with a marker where they differ.

## J. Anything else

81. [M] Two populations, never pooled:
    - `zone` (3-min interval): 572 arms since 01 Oct, all on recorded book days;
    - `zone3` (its own 3-min bands): from 28 Oct, 58 arms.

    The replay runs each separately. The spec's rows table must tag each row's population.
82. **Hers.** My proposal: no word retires before 15 triggers per side (rule 4). After that, GHUMEGA retires if its rows hit the stop before `pehla padav` at least as often as CHALEGA's rows do. Rows, not rates.
83. **Decided:** the in-trade line never uses the ladder's words. It is a `khatra` line under the ladder, as l6 is today.
84. THE READ keeps its own fuel. When it says "could not check", it cites RASAD. The LADAI tab shows one fuel: RASAD.
85. In a trade, l6 reads the fight at **her** defending wall (fold W). The hero shows the market's fight. When they differ: `teri deewar 22,700s PE · ladai 22,800s CE pe`.
86. **Decided:** price through by 2 steps with no TOOT means PHANSE (writers run over: stored fuel ahead). "Ghoom gaya" applies only when price leaves *away* from the wall.
87. §1h (EXPRESSION rev e, signed) keeps the pick. KAHANI's defender state is shown beside it, display only. Any change is hers.
88. Strikes on purpose: walls live at strikes, as §1d's NEAR does. A σ-scaled distance is a round-2 candidate.
89. The test's truth is the record as it was (book + REST as backfilled), each fuel minute tagged by its source. The causality test runs on a frozen fixture.
90. Shorts under water are in scope as an addition. The price-at-build ledger is doable from the book: per minute, the OI added × price gives the VWAP of open interest still standing. It is round 2's first "more powerful" candidate.

## Spec corrections owed after round 2

- 12:12 WALL becomes ✗ [M].
- 27 Oct FUEL becomes "?" (expiry). 27 Oct 12:51 and 14:18 read SAAF NAHI at the trigger. So zero of five rows read GHUMEGA at the trigger; one upgrades at +2 minutes.
- handshake-2's hold rule.
- The book's partial-minute hole.
- Roll-week fuel.
- The PHANSE and KHISAK chapters.
- PALAT's two forms.
- PIN's clause 2 dropped.
- Context (b) lasts until the fight ends.
- `pehla padav`.
- The verdict timeline plus one follow-up Telegram line.
- Book-primary flow for KAHANI.
- Populations tagged.
- Spot / fut declared.
