# EXECUTE THE EDGE: an independent critique (Fable, 14 Nov 2026)

Scope: the 13–14 Nov study and build (NOTEPAD A313–A336, spec `2026-11-13-execute-edge-design.md`, `execute.py`, the server hook,
the forward log, the Dext panel 0.9.3, the Jarvis pages). Nothing was changed but this file. No server was touched.

What I ran (all read-only):
- `python -m pytest -q test_execute.py`: 19 pass.
- `check_execute_parity.py`: PASS (46 of 46 with the trigger log; PLAN A 257 / +1,028; PLAN B 119 / +1,650; with Dext 24 / +1,260).
- The extension's `test/exec.test.js`: 7 pass.
- My own script on the same 60 sessions, through the parity script's own loaders. Numbers from it are tagged **[R]**. All are
  futures points, fills at the level, read after the fact. Counts and points only.

Short answer: the build is careful and matches its study. The study is not yet evidence of an edge. The raw setup is about
break-even; the profit sits in filters chosen on the same days. The forward log is the right next step, but as built it cannot
judge the checks one by one.

---

## 1. Ratings

| | What | Score | Reason |
|---|---|---|---|
| a | Is there an edge; how good is the evidence | **4** | Every trigger: 257 trades, +1,028, days up 29 / down 30, +148 without the best five. Resampling the 60 days 5,000 times, 495 came out at zero or below [R]. The plan's +1,650 is measured on the days it was fitted on. |
| b | The execution rules (hold, stop, flip, 15:00) | **6** | "Hold, don't book" is the best-supported finding: VWAP booking negative in every month, stop-to-cost worse at all three arms. Hold-through rests on 22 days and acts through one check. |
| c | The four checks | **3.5** | About 50 cuts were tried on 60 (22) days. GAP was found in the split. TREND moves 7 trades. LEG costs points. FLOW's gain comes from 8 trades. Detail in §2.2. |
| d | The implementation | **7** | Pure brain, parity reproduced, no look-ahead found (0 of 90 signals differ with Dext [R]), fail-soft. Marked down for the write-once log, GAP unreadable on 10 of 60 days, and a paper position the screen shows as hers. |
| e | The screens and one voice | **5** | One word per signal is right. But the word is stronger than its evidence, the ticket lasts three minutes, and the Dext panel still carries other voices under the plan. |
| f | The forward test design | **4** | Three paper lines side by side is right. No pass bar is written, a skipped signal has no outcome of its own, GAP is counted in signals not days, and rows are frozen at first sight. |
| | **Overall** | **5** | Good engineering on a thin, in-sample result. Worth running forward as a paper line. Not yet worth trusting as rules. |

---

## 2. What is weak, wrong or risky

### 2.1 The evidence for the edge

| Line | Trades | Points | Without best 5 | Days up / down / flat | Day-resamples ≤ 0 (of 5,000) [R] |
|---|---|---|---|---|---|
| PLAN A, 60 days | 257 | +1,028 | +148 | 29 / 30 / 1 | 495 |
| PLAN A, 22 order-flow days | 83 | +206 | −637 | 9 / 12 / 1 | 1,905 |
| PLAN B, 60 days, no Dext | 119 | +1,650 | +858 | 26 / 13 / 21 | 1 |
| PLAN B, 22 days, with Dext | 24 | +1,260 | +283 | 10 / 3 / 9 | 6 |

- **The raw setup is not shown to pay.** About 4 points a trade, September supplies +799 of +1,028 (A320 says this itself).
- **The bottom two rows look strong because they were chosen.** The resample counts 1 and 6 do not know that the rules were
  picked on these days. They are not a test.
- **The full plan exists on 22 days only.** 24 trades. Five of them make +977 of +1,260; one is +384 [R]. Six trades held to
  15:00 make +852 [R]. The "60-day PLAN B" has no FLOW check, so it is a different plan.
- **About 50 cuts on one sample** (my count from A313–A334: 5 exits, 17 pieces, 3 CTC arms, 8 LEG variants, hold-through,
  FLIP-OK, OPEN-DRIVE, live-leg, careful flip, room, four clock/stop splits, K6 / K2 / K4, gap, held-break, wall, two sync reads).
  "Both halves up" was looked at each time and used to choose, so the halves are not a holdout.
- **House rule 2 / §5 was broken.** `context/research-findings.md` §5 (line 1178) says: no more slicing; a new idea is
  registered before the run. Only K6 / K2 / K4 had a direction fixed beforehand, and all three came back mixed or worse. The
  record is frank about this and calls every result a candidate. That frankness is the study's best feature. It does not
  make the numbers a test.
- **One index, one quarter, one contract regime** (after the 3 Aug CAS change). 60 sessions.
- **Futures points, not her instrument.** She trades options. The plan's profit is in long holds (15:00 exits: 14 trades,
  +840 on 60 days [R]). A bought option pays time value over exactly those hours; a sold one earns it. So the same signal
  list gives a different result for her buy and her sell. Nothing here measures either.
- **Fills.** Entry is the 3-min close; she sees the ticket 25–60 s later (20 s grace `server.py:4825`, 20 s frame cache
  `server.py:4770`, 15 s poll). Entering one minute late moves PLAN B's 60-day total by −193, two minutes late by −13; on
  the 22 days by +83 and +176 [R]. No steady cost, but the swing is ±200 on a 1,650 total. Stops fill exactly at the extreme
  (`execute.py:159`); a real stop sits beyond it: 52 stops × 2 points = −104 [R].
- **The drawdown to plan for is not 190.** That is the fitted plan's. The unfitted line's is 510, with 7 stops in a row (A320).

### 2.2 The four checks, one by one

Each row: what the check changes in the final plan when it alone is switched off [R].

| Check | 60 days (no Dext) | 22 days (Dext) | What I found |
|---|---|---|---|
| none off | 119 / +1,650 | 24 / +1,260 | |
| GAP off | 195 / +1,262 | 37 / +1,117 | 20 gap days of 50 readable: 14 down, 6 up, −388. Random 20-of-50 day picks did as badly 137 times in 10,000. Good for one test; with about 50 cuts tried, one this good by luck is ordinary. Both halves negative (−168 / −219). **10 of 60 days could not be read and made +628.** |
| TREND off | 126 / +1,633 | 27 / +1,153 | 7 trades, +17 on 60 days. On the 38 sessions outside the order-flow days its trades made +2 on 12 (won 6). The comment at `execute.py:20` ("held on 37 unseen sessions") is not supported. It counts from 09:30 (`execute.py:98`), so it cannot fire before 11:27; A325 says 12 of 20 losers triggered before 10:00. |
| LEG off | 148 / +1,775 | 34 / +1,251 | In the final plan LEG **costs** 125 points. It buys a smaller drawdown (342 → 190). Its quoted record (−182 on 44, A323) is from the plain flip walk, not from this plan. A323 already shows it changing sign between halves. |
| FLOW off | (not used) | 32 / +877 | +383 from 8 trades. Sign only (`execute.py:121`): 19 of 89 signals had a sum under 50 lots, 37 under 100; the median is 129 [R]. Its SELL side has 10 trades. The best of 17 pieces tried. |

- A consequence of LEG the spec does not spell out: once a 2R win is banked, every later opposite signal is "weak"
  (`execute.py:164`), so a later same-side trade can end only at its stop or at 15:00.
- Hold-through is neutral without FLOW (A327). So the plan's largest single lift (+720 → +1,117) rests on the least-sampled check.

### 2.3 The implementation

What is right: `day_state` is pure and rebuilt from the tape each pass, so a restart cannot corrupt it. Triggers equal the
trigger log 46 of 46. The stop was never inside the real extreme (0 of 285 signals [R]). No signal changed when read at its own
close, with Dext (0 of 90 [R]; the parity script checks this without Dext only, `check_execute_parity.py:90`). No signal lost
its entry minute (0 [R]).

What is weak:

| # | Where | Problem |
|---|---|---|
| 1 | `execute.py:344-370`, `server.py:4788-4790` | **The log is write-once at first sight.** A signal row is written about 20 s after the bar closes, with whatever Dext and the tape held then (Dext re-posts a bar as it fills, `server.py:4703`). If the delta or the last candle changes later, the plan's walk changes but the signal row does not. Close rows from the new walk are then appended beside the old signal row. On the saved record no flow window was partial (0 of 90 [R]), but that is the final data, not what was live. |
| 2 | `execute.py:346` | **Rows carry no time of writing and no live / backfilled tag.** After a mid-day restart every earlier signal is written at once and looks observed. This breaks the anytime-start rule (backfill tagged, never blended). `_hs_log` (`server.py:4760`) already stamps `at` and `rev`; this log does not. |
| 3 | `execute.py:33-37, 56-59` | **GAP reads the strict previous weekday.** After a holiday or an expiry it says "could not check" and does not block. 10 of 60 days: 8 with no candles for that weekday (4 Aug, 13 Aug, 27 Aug, 9 Sep, 15 Sep, 5 Oct, 21 Oct, 11 Nov) and 2 rollovers [R]. Some are true holidays; some are only holes in the candle store. Forward, about one session in six will carry no GAP read. |
| 4 | `execute.py:105-108` | FLOW sums whatever minutes are readable. One readable minute of six gives a full ✓ or ✗. Not seen on the record; possible live when Dext lags. |
| 5 | `execute.py:274-299` | **IN TRADE is the paper plan's position, not hers.** If she skipped a TAKE, or took a SKIP, the line still says `HOLD SELL … wrong only at …`, later signals read "IN A SELL ALREADY", and LEG PAID fires off a win she may not have. Nothing joins it to her marked trades (`_hold_list` is only counted at DAY END, `server.py:4796`). |
| 6 | `execute.py:281-285` | The TRIGGER state lasts one 3-min bar. A SKIP while flat then falls back to `WAIT · no zone armed` and leaves no trace on the Dext panel. |
| 7 | `test_execute.py` | No test drives `triggers` or `_signals` on a real band path (line 97 says why). The only cover is the parity script, by hand, on local data. Acceptable, but a change to `band_rotation` will not fail a test. |
| 8 | `execute.py:201-229` | `OTHER SIDE adding (fuel)` and `cutting (being paid)` both mean hold (spec §3). A line that cannot change the action is noise. SYNC is a restated "price is going your way" (A334 says so) and prints `ALL 3 WITH YOU · hold`, an instruction from an untested read. |

Spec against code: the spec's GAP says "previous weekday with candles" (§3); the code takes the calendar weekday. Spec §8
promises per-check counts "kept / skipped, won / stopped, points"; the log cannot produce them (see 2.5). Otherwise the code
follows the spec.

### 2.4 The screens: what she will misread

- **TAKE / SKIP / ✓ / ✗ read as rules.** The spec says "candidates until she signs" (§3). The screen has no word for that. The
  one-voice change (A336) removed the three older reads that used to disagree, so the least-tested read is now the only voice.
- **The Dext panel is not one voice.** The plan block is drawn first (`lib/panel-render.js:70-73`), then Jarvis's own word,
  WITH / AGAINST, buyer / seller picks and the hold voice (`:74-87`). In a trade the plan says HOLD while `voice.py` can say
  TIGHTEN or EXIT beside it (spec §4 keeps it "as information"). That is the moment the study says matters most.
- **DAY END `PLAN B +188 (2) · PLAN A … · PLAN C …`** will be read as "what I should have made". It is futures points at
  perfect fills.
- **A ✓ on FLOW at −6 lots** looks the same as one at −2,943.
- **`GAP could not check`** carries no mark, which is correct (rule 6), but on a real gap day after a holiday she gets no warning.
- **"wrong only at 25,285f"** is a futures level; her option stop is hers to translate. The f tag is there, which is good.

### 2.5 The forward test

- **No pass bar.** §5e's principle: the bar is stated before the numbers are read. Spec §8 says only "the counts go to her".
- **A skipped signal has no outcome.** The log holds signal rows and each plan's closed trades. PLAN A does not take a signal
  while it holds the same side, and its exit differs from B's. So "what would this skipped trade have done" is not in the log.
  The checks also overlap. The test can compare plan totals; it cannot judge one check.
- **"≥15 skips a side" is the wrong unit for GAP.** On the 22 days GAP fired on 16 BUY and 15 SELL signals [R], from about 8
  days. Signals in one gap day are not independent. FLOW fired 16 / 11, TREND 9 / 7. LEG fires about once in two sessions and
  will take months.
- **No stop date.** Without one, the log is read whenever it looks good.
- **No option premium, no fill price, no record of her own take / skip** (A315 left that open).

---

## 3. What to do, ranked by value

| # | What | Why | How to check | Size |
|---|---|---|---|---|
| 1 | **Score the plan in option premium.** For every PLAN A and PLAN B trade on the 22 order-flow days, read the chain's premium at entry and exit: ATM buy, and her ATM / ITM sell. Log the same forward. | It is the instrument she trades. Long holds help a seller and tax a buyer; the study cannot say which side this plan suits. | On the record: the frames hold the chain per minute. Two totals per plan, in ₹ a lot. Forward: two fields on each close row. | M |
| 2 | **Write the pass bar and a stop date before the first forward row.** Per check: what keeps it, what cuts it. GAP in days (≥15 gap days). A fixed end (for example 40 sessions). Freeze `TREND_MIN`, `LOCK_R`, `ROOM_S`; a change is a new registration. | Without it the forward test repeats the backtest's flaw. | A dated paragraph in `research-findings.md`, signed by her, before the restart. | S |
| 3 | **Give every signal its own outcome in the log.** After the close, one row per signal: points at its stop or at 15:00, taken alone, whatever the plans did. | Only this lets each check be judged apart, and lets a SKIP be scored. | Rebuild 11–13 Nov offline; each of the day's signals has one outcome row. | S |
| 4 | **Make the log honest about time.** Stamp `at` and live / backfilled on every row. At the close, recompute the day and write `final` rows; count where first ≠ final. | Fixes 2.3 #1 and #2. The count of differences is itself the measure of how much the live read drifts. | A restart at 11:00 in replay: morning rows say backfilled. A day's first / final difference count is printed at DAY END. | S |
| 5 | **Say PAPER, or follow her trade.** Smallest step: when PLAN B holds a trade she has not marked, the line starts `PLAN (paper)`. Better: IN TRADE and LEG PAID follow her marked trade when one is open. | Today the screen can tell her to hold a trade she is not in. | Replay a day with a mark that differs from the plan; the line names whose trade it is. | S, then M |
| 6 | **Make GAP readable.** Use the last session that has candles; on a rollover day read yesterday's candles of the new contract. | 10 of 60 days unread, +628 on them. The check's own record is incomplete. | Re-run the parity script; the unreadable count falls to near 0. Record the new totals as a new number, not a correction. | S |
| 7 | **Log her call at the trigger** (take / skip, one tap, and why). | The only way to learn whether her eye beats the four checks. Her reads on 12–13 Nov were right twice. | The DAY END row shows YOU beside A / B / C on the same signals. | S |
| 8 | **Log FLOW's size against the day's noise** (`ruler.noise` exists) and the futures price when the card first carried the ticket. No threshold now. | Shows forward whether small sums carry the FLOW result, and what her real entry is. | Two fields on the signal row. | S |
| 9 | **Trim the screen.** Keep the last ticket visible, greyed, until the next signal. Drop the OTHER SIDE line. On the Dext panel, in a trade, show one hold line; fold Jarvis's word and the hold voice under it. Put "candidate" beside each ✓ / ✗ until she signs. | Fewer lines, and none that contradict at the hold. | Her eyes on a replay of 11 Nov (four skipped BUYs while holding a SELL). | S |
| 10 | **Add one trigger-path test** from a saved real day (a small fixture of one session's candles). | A change in `band_rotation` should fail a test, not wait for a hand-run script. | The test fails when a trigger time is edited. | S |

Order to do them: 2, 3, 4 and 6 before her restart (they shape the first forward rows). Then 5 and 9. Then 1, 7, 8.

---

## 4. What NOT to do

- **No more cuts on these 60 days.** Not "just the before-10:00 losers", not a FLOW size threshold, not a better TREND number.
  Each new cut that shows "both halves up" is one more pick from the same bag.
- **Do not size up on +1,650 or +1,260.** Plan on the unfitted line: about 4 points a trade, a 500-point drawdown, 7 stops in a row.
- **Do not change a check during the forward run.** If one must change, it restarts that check's count.
- **Do not read the forward log early.** Fix the date in item 2 and hold to it.
- **Do not turn the before-10:00 pattern into a clock rule** (her 11 Nov standing rule; A326 shows the early winners too).
- **Do not make CAREFUL FLIP live.** It adds points and nearly doubles the drawdown (A329) on the same fitted sample.
- **Do not take parity PASS as proof of edge.** It proves the code equals the study, nothing more (house rule 9).
- **Do not read futures points as rupees**, on DAY END or anywhere.
- **Do not let the tool's SKIP silently overrule her.** Until a check is signed, her override is data: log it (item 7).
- **Do not drop TREND or LEG now because this critique found them weak.** That would be one more after-the-fact choice. Let
  the pass bar decide.
- **No order path.** The ticket is advice. Keep it that way.
