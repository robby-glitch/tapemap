# TapeMap: blind trader review, Sun 25 Oct 2026

- **Scope:** read-only. I did not read `docs/review/`, `NOTEPAD.md` or `~/.claude`.
- **Tags:** [M] means measured from `data/`. [I] means inferred, or an in-sample replay.
- **Method:** no win rate, hit rate or expectancy is given anywhere. Any count under 15 per side is INCONCLUSIVE.
- **Prices:** premiums come from `data/chain/chain_<IDX>_<day>` LTP. Where there is no fill, the exit premium is the chain at her exit minute (marked `c`).
- **Scratch scripts:** `C:\Users\kaam\AppData\Local\Temp\claude\C--Users-kaam--claude-spares-spare-jIXWxw\c544a8cc-a7ea-42db-8fc4-b71280810174\scratchpad\` (`trades.py`, `table.py`, `counts.py`).

## 1. Verdict

1. **It is not making her money yet.** Across her 55 real trades, the tool's entry words split roughly evenly: they helped on 8, hurt on 10 and said nothing usable on 30. Its exit FOLDs helped on 4 and hurt on 4. Every bucket is n<15, so all of it is inconclusive [M].
2. **Her one measured leak is untouched.** She closes right-direction scalps fast: median hold 3.7 min, SENSEX 1.1 min. On 18 of 52 trades the premium paid at least 50 more points within the hour after she exited.
   - The newest exit line cuts winners too.
   - On 22 Oct the ANSWER band printed GO beside a READ of RANGE, right into her worst recent loss.
3. **Stop building; fix intake and noise first.** Evidence has stalled: 1 marked trade in the 12 sessions since 6 Oct, and the server recorded a full day on only 4 of the last 10 sessions. At this rate most locked rules cannot reach their bars in 2026 [I].

## 2. Scorecard

| area | /10 | why |
|---|---|---|
| entry help | 3 | Validate rev 3 said WAIT on 46 of 51 of her entries. The ANSWER band said GO↑ into the 22 Oct loss. No registered setup fired on either of her 2 trades since the setups went live. |
| in-trade help | 4 | One voice, verbatim on 3 surfaces: good. rev 6 said HOLD on 263/263 rows of her +155 winner. But the voice said HOLD for 23 minutes while the 22 Oct CE lost about half its premium, and up to 3 stop numbers are on screen. |
| exit help | 3 | rev 5 FOLD: 4 helped, 4 hurt, median Δ −6.8 premium pts. The voice EXIT came before the run on 21 Oct (+134 vs her +155) and on 1 Oct (EXIT 12:23, then the PE went 247→708). |
| seller support | 2 | Only 3 short trades on record, one of them an 8-second mis-mark. The EXPRESSION pill flips about 56 times a day. Theta only in [detail]; no gamma; no seller P&L path on the face. |
| noise | 2 | About 185 items on screen by default in a trade, about 250 with Validate's OI grid [I]. 4 day-type classifiers. 3 names for one state. 15 tabs. |
| evidence base | 2 | Marking has collapsed: 31, then 14, 8, 0 and 1 trades a week. Validate rev 3 is not logged. The VPIN clock is overdue. The §1d falsifier window has passed, unjudged. |

## 3. Her real trades (all 55 on disk)

**Sources:**
- `data/fixtures-private/tradebook_2026-09-21_24.csv`: 29 round trips, paired with `receipts.trips`.
- `data/day_state/day_*.json` `hold_trades`: 14 marked and 11 imported (1 Oct).
- The 22 Oct SENSEX CE: unmarked; its exit time is from `docs/hold/validate3/REPLAY-rev3.1.md:16` [I].

**Columns:**
- `pts` = her premium points [M]. `min` = minutes held.
- **C** = the ANSWER-band verdict at entry (`data/calls/`, live [M]).
- **V** = Validate rev 3 word (`REPLAY-rev3.1.md` table, in-sample replay [I]).
- **in-trade words:**
  - H5 = rev 5 window (`data/hold/hold_*`, live 25 Sep onward, now log-only);
  - F6 = rev 6 engine (`data/fold/`; the 1 Oct rows are a replay written 3 Oct);
  - VO = the one-voice replay (`docs/trade-map/BUILD-REPORT.md:85-102`, `REPLAY-rev3.1.md`).
  - `(x)` = her premium points had she acted on that word.
- **after 60m** = best / worst premium vs her exit, her side, in the hour after exit [M].

**How E and I are marked:**
- **E** (C vs her result): a don't-word (ASIDE/SPENT) on a loser = help; on a winner = hurt. GO the way she traded = agree if it won, hurt if it lost. WAIT/CAUTION = silent.
- **I** (exit word vs her pts): help or hurt; silent when the word was HOLD or nothing.

| # | date | idx | side | in→out | prem in→out | pts | min | C | V | in-trade words | after 60m | E | I |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 09-21 | NIF | L 23300CE | 14:00→14:10 | 179.6→168.0 | −11.6 | 10 | — | — | — | n/a (no chain) | silent | — |
| 2 | 09-22 | NIF | L 23300CE | 09:42→10:20 | 166.4→159.15 | −7.25 | 38 | — | WAIT | — | +0.8/−68.2 | silent | — |
| 3 | 09-22 | NIF | L 23550PE | 10:32→10:38 | 134.8→144.05 | +9.25 | 5 | — | WAIT | — | +46.4/−1.0 | silent | — |
| 4 | 09-22 | NIF | L 23550PE | 10:42→10:42 | 174.75→186.95 | +12.2 | 0.2 | — | WAIT | — | +3.5/−29.7 | silent | — |
| 5 | 09-22 | NIF | L 23550PE | 10:43→10:43 | 175.05→171.6 | −3.45 | 0.2 | — | WAIT | — | +18.8/−14.3 | silent | — |
| 6 | 09-22 | NIF | L 23550PE | 10:44→10:44 | 171.5→174.0 | +2.5 | 0.7 | — | WAIT | — | +16.4/−16.8 | silent | — |
| 7 | 09-22 | NIF | L 23500PE | 10:52→10:55 | 146.15→133.0 | −13.15 | 3 | — | WAIT | — | +25.6/−19.7 | silent | — |
| 8 | 09-22 | NIF | L 23500PE | 13:48→13:54 | 181.5→203.2 | +21.7 | 5 | — | WAIT | — | +19.3/−97.2 | silent | — |
| 9 | 09-23 | NIF | L 23450CE | 09:18→09:25 | 100.0→99.0 | −1.0 | 7 | — | WAIT | — | +4.8/−13.5 | silent | — |
| 10 | 09-23 | NIF | L 23450CE | 09:47→09:49 | 99.4→91.75 | −7.65 | 1.4 | — | WAIT | — | +20.0/−6.2 | silent | — |
| 11 | 09-23 | NIF | L 23400PE | 09:49→09:53 | 125.0→124.2 | −0.8 | 4 | — | WAIT | — | +9.6/−27.4 | silent | — |
| 12 | 09-23 | NIF | L 23450CE | 10:00→10:09 | 98.6→90.8 | −7.8 | 9 | — | WAIT | — | +24.8/−3.3 | silent | — |
| 13 | 09-23 | NIF | L 23450CE | 10:19→10:31 | 101.85→105.0 | +3.15 | 12 | — | WAIT | — | +12.3/−4.2 | silent | — |
| 14 | 09-23 | NIF | L 23450CE | 10:33→11:04 | 106.45→106.0 | −0.45 | 31 | — | WAIT | — | +18.8/−0.5 | silent | — |
| 15 | 09-23 | NIF | L 23450CE | 11:07→11:16 | 115.65→110.0 | −5.65 | 9 | — | WAIT | — | +24.3/−2.2 | silent | — |
| 16 | 09-23 | SEN | L 74900CE | 11:32→11:40 | 215.25→200.0 | −15.25 | 8 | — | WAIT | — | +65.8/−10.1 | silent | — |
| 17 | 09-24 | SEN | L 74200PE | 09:42→09:47 | 179.25→203.0 | +23.75 | 5 | GO↓ | WAIT | — | +31.8/−47.8 | agree | — |
| 18 | 09-24 | SEN | L 74200PE | 10:19→10:23 | 222.6→234.0 | +11.4 | 4 | WAIT | WAIT | — | −1.8/−83.6 | silent | — |
| 19 | 09-24 | SEN | L 74100PE | 12:32→12:33 | 202.35→216.0 | +13.65 | 1.1 | WAIT | WAIT | — | +88.8/−34.5 | silent | — |
| 20 | 09-24 | SEN | L 74000PE | 12:35→12:38 | 179.8→161.0 | −18.8 | 3 | SPENT | WAIT | — | +75.3/−27.7 | help | — |
| 21 | 09-24 | SEN | L 74000PE | 12:44→12:50 | 167.95→160.0 | −7.95 | 6 | SPENT | GO | — | +224.2/−26.7 | help | — |
| 22 | 09-24 | SEN | L 74000PE | 13:26→13:27 | 184.2→220.0 | +35.8 | 0.5 | WAIT | NO | — | +242.4/−32.5 | silent | — |
| 23 | 09-24 | SEN | L 73900PE | 13:41→13:43 | 190.03→192.98 | +2.95 | 2 | GO↓ | WAIT | — | +187.9/+6.8 | agree | — |
| 24 | 09-24 | SEN | L 73900PE | 13:43→13:43 | 206.55→207.3 | +0.75 | 0.2 | SPENT | WAIT | — | +173.6/+13.3 | hurt | — |
| 25 | 09-24 | SEN | L 73900PE | 13:44→13:44 | 230.45→237.6 | +7.15 | 0.2 | SPENT | WAIT | — | +143.3/−11.5 | hurt | — |
| 26 | 09-24 | SEN | L 73800PE | 13:45→13:46 | 211.05→217.05 | +6.0 | 0.2 | SPENT | WAIT | — | +92.5/−48.8 | hurt | — |
| 27 | 09-24 | SEN | L 73800PE | 13:54→13:55 | 252.15→240.0 | −12.15 | 1.0 | GO↓ | WAIT | — | +69.6/−97.8 | hurt | — |
| 28 | 09-24 | SEN | L 73800PE | 13:57→13:58 | 267.4→297.0 | +29.6 | 1.2 | GO↓ | WAIT | — | +12.6/−154.8 | agree | — |
| 29 | 09-24 | SEN | L 73800PE | 14:23→14:23 | 287.45→294.8 | +7.35 | 0.2 | GO↓ | WAIT | — | +10.3/−186.3 | agree | — |
| 30 | 09-25 | NIF | L 23100CE | 12:01→13:23 | 113.55→92.35c | −21.2 | 82 | WAIT | — | H5 FOLD 12:03 (−2.3) | +88.7/−3.1 | silent | help |
| 31 | 09-25 | NIF | L 23200PE | 12:05→13:23 | 155.4→177.3c | +21.9 | 78 | WAIT | — | H5 FOLD 12:31 (−10.8) | +5.7/−85.4 | silent | hurt |
| 32 | 09-28 | NIF | L 23000PE | 09:30→10:20 | 120.4→156.65c | +36.25 | 50 | CAUTION | — | H5 FOLD 09:35 (+7.0) | +27.4/−3.9 | silent | hurt |
| 33 | 09-29 | NIF | L 22800PE | 09:18→09:35 | 113.95→189.3c | +75.35 | 17 | CAUTION | NO | F6 HOLD · H5 WATCH 09:31 | +39.4/−8.7 | silent | silent |
| 34 | 09-30 | NIF | L 22750CE | 10:10→11:16 | 164.7→125.95c | −38.75 | 67 | ASIDE | WAIT | H5 FOLD 10:40 (−15.9) · VO EXIT 10:34 (−15.7) · F6 FOLD 11:16 = her exit | +30.5/−3.3 | help | help |
| 35 | 10-01 | NIF | L 22600PE | 09:21→09:23 | 142.4→155.5c | +13.1 | 2.5 | CAUTION | WAIT | F6 HOLD | +7.3/−41.2 | silent | silent |
| 36 | 10-01 | NIF | L 22600PE | 09:26→09:26 | 149.75→152.25c | +2.5 | 0.2 | CAUTION | WAIT | F6 HOLD | +6.9/−38.0 | silent | silent |
| 37 | 10-01 | SEN | L 72400CE | 09:30→09:31 | 209.4→218.5c | +9.1 | 0.3 | ASIDE | WAIT | F6 HOLD | +70.4/−62.2 | hurt | silent |
| 38 | 10-01 | SEN | L 72400CE | 10:00→10:01 | 237.25→266.8c | +29.55 | 0.6 | ASIDE | WAIT | F6 HOLD | +22.1/−97.9 | hurt | silent |
| 39 | 10-01 | SEN | L 72400CE | 10:02→10:06 | 276.05→269.45c | −6.6 | 4 | ASIDE | GO | F6 HOLD | +19.4/−103.0 | help | silent |
| 40 | 10-01 | SEN | L 72400PE | 12:06→12:08 | 223.97→235.65c | +11.68 | 1.5 | ASIDE | WAIT | F6 HOLD · VO EXIT 12:23 (after her) | +629.1/−7.6 | hurt | silent |
| 41 | 10-01 | SEN | L 72300PE | 12:10→12:11 | 224.1→219.5c | −4.6 | 0.8 | CAUTION | WAIT | F6 HOLD · VO EXIT 12:23 | +558.8/−43.1 | silent | silent |
| 42 | 10-01 | SEN | L 72400PE | 12:10→12:11 | 281.45→272.2c | −9.25 | 1.3 | CAUTION | WAIT | F6 HOLD · VO EXIT 12:23 | +592.5/−35.5 | silent | silent |
| 43 | 10-01 | SEN | L 72300PE | 12:19→12:20 | 232.0→226.0c | −6.0 | 1.0 | SPENT | WAIT | F6 HOLD · VO EXIT 12:23 | +552.2/−14.8 | help | silent |
| 44 | 10-01 | SEN | L 72300PE | 12:22→12:22 | 246.4→247.35c | +0.95 | 0.3 | SPENT | WAIT | F6 HOLD · VO EXIT 12:23 | +530.9/+0.8 | hurt | silent |
| 45 | 10-01 | SEN | L 72300PE | 12:27→12:29 | 296.9→320.45c | +23.55 | 1.6 | SPENT | WAIT | F6 HOLD · VO EXIT 12:23 | +457.8/−50.1 | hurt | silent |
| 46 | 10-05 | NIF | L 22600CE | 09:28→09:34 | 94.25→99.5c | +5.25 | 6 | CAUTION | WAIT | F6 HOLD · H5 WATCH | +15.2/−42.3 | silent | silent |
| 47 | 10-05 | NIF | L 22550CE | 09:35→09:44 | 134.95→123.9c | −11.05 | 9 | ASIDE | WAIT | F6 HOLD · H5 WATCH | +23.7/−46.4 | help | silent |
| 48 | 10-05 | NIF | L 22550PE | 12:09→12:18 | 174.75→153.6c | −21.15 | 8 | ASIDE | WAIT | F6 HOLD · H5 WATCH | +4.4/−30.3 | help | silent |
| 49 | 10-05 | NIF | S 22650PE | 13:41→15:42* | 131.35→133.75c | −2.4 | 120 | ASIDE | WAIT | F6 HOLD, 23 word changes (CAN'T CHECK flicker) | n/a | help | silent |
| 50 | 10-06 | NIF | S 22600CE | 09:35→09:48 | 65.8→81.5c | −15.7 | 13 | CAUTION | WAIT | H5 FOLD at entry (0) | +14.5/−21.9 | silent | help |
| 51 | 10-06 | NIF | S 22650PE | 10:02:51→10:02:59 | 55.9→56.4c | −0.5 | 0.1 | GO↑ | NO | mis-mark: long PE at 10:03:21 | — | n/a | n/a |
| 52 | 10-06 | NIF | L 22650PE | 10:03→13:17 | 55.0→17.8c | −37.2 | 194 | GO↑ (against her) | WAIT | H5 FOLD at entry (0) · F6 FOLD 11:45 (−21.9) | +7.4/−9.5 | help, ignored | help |
| 53 | 10-06 | NIF | L 22600CE | 14:12→15:24 | 133.0→141.5c | +8.5 | 73 | GO↑ | WAIT | H5 FOLD 14:29 (−38.9) | +35.2/+3.0 | agree | hurt |
| 54 | 10-21 | NIF | L 23000PE | 10:07→13:05 | 174.85→329.6c | +154.75 | 178 | CAUTION | WAIT | F6 HOLD 263/263 · H5 FOLD 11:03 (−7.8) · VO WARN 11:18, EXIT 12:34 (+134.4) · 384.35 @14:47 | +45.1/−10.7 | silent | hurt |
| 55 | 10-22 | SEN | L 73400CE | 13:00→13:25† | 191→81.7c | −109.3 | 25 | GO↑ CONTRADICTED | WAIT 6w1a | VO HOLD 13:01–13:24 (prem 201→107), EXIT 13:24 | +3.8/−50.9 | hurt | silent |

\* exit marked after the 15:30 chain close. † unmarked; exit time from the replay doc [I].

**Totals [M]:**
- **E** (ANSWER band): help 8, plus 1 she ignored (#52); hurt 10; agree 5; silent 30; mis-mark 1.
- **I:** help 4, hurt 4. These are all rev 5 FOLDs. The median "follow minus hers" is −6.8 premium pts, and the largest single cut is −162.6 on 21 Oct.
  - **Voice replay** [I]: helped on 30 Sep (+23), hurt on 21 Oct (−20), and on 22 Oct matched her exit.
  - **Validate rev 3** [I]: WAIT 46, GO 2, NO 3.
    - Her results on the GO entries: −6.6 and −7.95.
    - Her results on the NO entries: +75.35, +35.8 (followed by +242), and the mis-mark.
- **Context:** 34 of 54 trades were on the traded contract's expiry day, and 6 on the day before [M].
- Every bucket is under 15: **INCONCLUSIVE**.

## 4. Findings

| ID | Sev | Finding | Evidence | Action | Size |
|---|---|---|---|---|---|
| F01 | P0 | The ANSWER band printed GO↑ while its own grounds said CONTRADICTED and READ said RANGE. She bought the CE at that minute and lost about 57% of the premium in 30 min. | `data/calls/calls_2026-10-22.jsonl` SENSEX 12:54/12:57/13:00: GO, dir up, CONTRADICTED · `data/read/read_2026-10-22.jsonl` SENSEX 13:00 RANGE · chain 73400CE 201.4@13:00 → 65.5@13:30 · rendered at `ui-v2/src/App.tsx:1866-1867` | CUT the verdict, or never print GO on CONTRADICTED | S |
| F02 | P0 | In a trade the voice says HOLD while the premium halves. The only stop is an index line; no premium % is shown. | `REPLAY-rev3.1.md:352` HOLD 13:01→EXIT 13:24 · chain 73400CE 201.4@13:00, 129.05@13:14, 107.65@13:20 · `voice.py:179-183` (l1/l2) | FIX: show premium % of entry in l1, display only | S |
| F03 | P1 | The exit words cut her winners as often as they saved her losers, and the biggest cut was her best trade. | §3 I column: 4/4 · `hold_2026-10-21.jsonl` FOLD r5 11:03 at prem 167.1 vs her 329.6 · voice EXIT 12:34 (`BUILD-REPORT.md:90`) vs 384.35 at 14:47 · 1 Oct EXIT 12:23 (`REPLAY-rev3.1.md:274`), then 72300PE 320→708.75 at 13:00 | LOCKED (HOLD v2 §1m: judge at n≥20 per group); STOP-BUILDING exit layers | — |
| F04 | P1 | Her measured leak is early exits on right-direction trades, and the tool is slower than her trades. | median hold 3.7 min (SENSEX 1.1) · median captured +0.95 pts · 18/52 had ≥ +50 and 11/52 ≥ +100 more within 60 min · spot moved her way on 33/53 in the hour after exit · reads arrive at 3-min closes (`hold2.py:200`) and 15-min OI slopes (§1d) | FIX: show receipts' left-on-table and fear-exit (`receipts.py:172-193`) on the Float at exit | S |
| F05 | P1 | Validate rev 3 is a WAIT machine, and its NO fell on two of her best trades. Rev 3.1 (signed today) moves her 22 Oct loser one WITH closer to GO. | `REPLAY-rev3.1.md:30-87` (46 WAIT/2 GO/3 NO), `:104-105` (5 entries stay WAIT only because #9 ROOM is AGAINST) | LOCKED | — |
| F06 | P1 | Validate rev 3's word is never logged, so the locked rule can never be judged forward. | `ui-v2/public/validate2/app.js:453,461`: its only POSTs are trade marks · `data/hold/check_*`: 8 rows, last 29 Sep | FIX: a write-once log of word, rev and checks per press | S |
| F07 | P1 | Evidence intake has stalled. | marked/imported trades per week: 31, 14, 8, 0, 1 (+1 unmarked) · no tradebook import since 3 Oct (`day_2026-10-01.json.bak-before-import-2026-10-03`) · full-day `calls` rows (~375) on 4 of the last 10 sessions; none on 14–15 Oct; 13 Oct 45 and 16 Oct 36 rows | FIX: a daily tradebook import through the existing `/api/receipts/import`; a 09:20 "recording?" check | S |
| F08 | P1 | The setups being forward-tested are not the trades she takes. | `data/confluence_log.jsonl` 21 Oct NIFTY: FADE BUY ×4 against her PE, all non-entries; RIDE ▼ ×2 failing OI on every bar · her 22 Oct 13:00 SENSEX CE: no row · 0 of her 2 trades since 21 Oct sit on an entry | LOCKED; STOP-BUILDING new setups; FIX: stamp each marked trade with the nearest setup row | S |
| F09 | P1 | §1d's 10-session falsifier window has passed without a judgement, yet the gate already decides the beep. | `trigger_log.jsonl`: gate on 18 days · scored gated zone entries 144: legal 22 (11 BUY, 11 SELL), illegal 107 · median MAE illegal vs legal: NIFTY −93.8 vs −101.2, BANKNIFTY −96.8 vs −258.1, SENSEX −270.2 vs −329.0 (legal n 4/8/10; inconclusive) · 448 of 559 stamped arms are illegal (80%; §1d predicted "a minority") · `signals.py:546-575` | LOCKED: run its own falsifier now | S |
| F10 | P2 | The VPIN kill clock is overdue, but VPIN still speaks inside the one voice. | `context/HANDOFF.md:1150` (30 sessions from 25 Aug) · `data/vpin_log.jsonl` covers 35 days · `voice.py:24` "VPIN saath" · fold lamp `panel.js:358` · Validate #7 | CUT from the in-trade face until it is judged | S |
| F11 | P2 | No kill-clock reader exists, so overdue clocks stay invisible. | `tools/` has no `kill_clocks.py`, though `docs/board/real-vs-fake-2026-10-03.md:158` asks for one · see the clock table below | FIX: one read-only script | S |
| F12 | P1 | Four classifiers answer "what kind of day is it", independently. | DIN `panel.js:164` · READ `panel.js:248` · Validate IB daytype `engine.js:149-178` · ANSWER band `App.tsx:1359` · 21 Oct calls "pin/chop" at 10:33–11:06 (×5) while `read_2026-10-21` said LEAN ▼ | CUT to DIN (§1o) | M |
| F13 | P1 | Up to 3 stop numbers can be on screen for one trade. | voice l2 = HOLD v2 line (`voice.py:155-164`) · Float detail "out if G" + `inval` (`pro/Desk.tsx:134-145`) · Validate ladder falls back to its own G (`app.js:138,319`) · 21 Oct: G 23052 (fold seed) vs hold.py line 23120.9 (10:06) | FIX: one stop everywhere = `voice.stop` | S |
| F14 | P2 | One engine state has three names. | PAST GIVE-UP (`Float.tsx:13`) = WATCH (`panel.js:362`) = WARN (voice) | FIX copy | S |
| F15 | P2 | Noise: the voice block is surrounded. | panel in a trade: READ, KHEL, SIZE, EXPRESSION, DECODE ×6, DIN, setups, FLOW, writers, fuel, 3 BADE (`panel.js:236-252,415-436`) · about 185 items by default [I] · 15 tabs (`App.tsx:1694`) · decoder 44–168 events/day (`data/decoder/`) | CUT: in a trade the panel shows voice + l4/l5 | M |
| F16 | P2 | The EXPRESSION pill is too unstable to glance at. | `data/hold/expr_*`: 90 index-day-direction series, median 56 word changes per day, max 79 · `panel.js:241` | CUT from the face; keep the log | S |
| F17 | P2 | Expiry day is where she trades, and the face has no expiry mode for buyers. | 34/54 trades on 0DTE, 6 on 1DTE [M] · only fold's 13:30 row (`fold.py:49`) and a sale's theta/hr inside [detail] (`trademap.py:228-257`) | FIX: a display-only "0DTE · θ/15m" chip (no rule; §1i "no expiry rule" stands) | S |
| F18 | P2 | Seller evidence cannot accumulate, and the one short sample includes a mis-click. | short trades: 3 of 54 · `day_2026-10-06.json` 22650PE short 10:02:51→10:02:59, then long at 10:03:21 | STOP-BUILDING seller layers; FIX: a void tag in code (never edit `data/`) | S |
| F19 | P2 | No desk risk line on the live face: no day P&L, drawdown, or trade or re-entry count. | receipts live only on `pro.html` (`pro/Record.tsx`) · 24 Sep: 13 SENSEX round trips in 4.7 h · 1 Oct: 9 in 1 h · sizing stays hers (§1f) | FIX: a one-line day strip on the Float | S |
| F20 | P2 | rev 5's entry check is log-only now. It was the only word that pointed away from #50 and #52. | `hold_2026-10-06` entry FOLD r6 (n=2, inconclusive) · `HoldWindow`/`HoldTab` are not imported by `App.tsx` | LOCKED (§1e, judge at its bound) | — |
| F21 | P3 | The EM count includes holidays, which inflates "range used". | `trademap.py:69`; 30 Sep counted the 2 Oct holiday (`BUILD-REPORT.md:121`); Validate #2 `u` (§1p) | FIX l4; LOCKED for #2 | S |
| F22 | P3 | There is no event or holiday calendar. | grep finds no RBI, budget or event module | FIX later | S |

**The clocks [M counts, I rates].**

Median rows per day:
- read 239; decode 225 (1 day); calls 375; side 1,136; expr 822; sides 424; trap 303; reader 92; decoder 84;
- confluence 17 (3 days); onesided 3 (1 day); grade 1 (2 days); vpin 46–91; trigger_log 65–95;
- senses about 0.95M (bloat).

| rule | forward since | sessions | forward n | bar | at this rate |
|---|---|---|---|---|---|
| §1d FADE gate | 23 Sep | 18 | legal 22 / illegal 107 | 10 sessions, MAE | due now, unjudged |
| §1i FADE | 21 Oct | 3 | 2 (+7 in-sample) | n≥20 per cell | ~80–100 sessions per cell |
| §1j RIDE | 21 Oct | 3 | 2 (+18; cells 7/5/2/4) | n≥20 per cell | largest ~30–45; smallest >150 |
| §1l READ-2 | 22 Oct | 2 | 1 upgrade | kill at 20 | ~40 sessions |
| §1m HOLD v2 | 22 Oct | 2 | FADE 0 · RIDE 1 · FADE-D 5 | n≥20 per group | FADE group not in 2026 |
| §1n FADE-D | 22 Oct | 2 | 5 | §1i §4 | fastest of the set |
| §1o One-Sided | 23 Oct | 1 | 1 day | 11:30 type vs READ | open |
| §1p VALIDATE rev 3 | 23 Oct | — | **no log** | — | never, as built |
| §1q SENSEX-on-NIFTY | 25 Oct | 0 | 0 | — | starts Mon |
| §1e/§1f/§1g | 25 Sep | 21 | 13 trades · 2 rung touches · 8 presses | ≥15 each by 30 sessions | inconclusive by ~6 Nov |
| §1h EXPRESSION | 28 Sep | 17 | 11,379 rows; no scorer in `tools/` | ≥15 units by 30 sessions | ~9 Nov, nothing to judge it with |
| VPIN | 25 Aug | 35 | — | 30 sessions | **OVERDUE** |
| grounds/calls | 24 Sep | 18 | 5,528 rows | ~30 sessions | ~12 more full days |

## 5. Top 10 actions, ranked

1. **CUT the ANSWER-band verdict** (F01). Her reason: "a GO that its own check contradicts put me into the 22 Oct CE."
2. **FIX premium % in l1, and one stop number everywhere** (F02, F13). Her reason: "I trade premium; tell me I'm −45%, and show me one stop, not three."
3. **FIX intake: a daily tradebook import, and a 09:20 recording check** (F07). Her reason: "the forward record is the only judge; 4 of 10 days didn't record."
4. **FIX: log Validate's word** (F06). Her reason: "a signed rule nobody can score is decoration."
5. **Judge the overdue clocks now**: the §1d gate and VPIN, then remove VPIN from the voice's why (F09, F10, F11). Her reason: "the gate decides my beep; prove it, or mute it."
6. **CUT the panel to voice + l4/l5 in a trade; one day-type; drop the EXPRESSION pill** (F12, F15, F16). Her reason: "I glance; one answer per question."
7. **STOP-BUILDING new setups, exit layers and seller layers** until FADE, RIDE and HOLD v2 have forward n (F03, F08, F18). Her reason: "nothing new until something old is scored."
8. **FIX: show left-on-table and fear-exit on the Float at exit** (F04). Her reason: "my leak is closing winners in a minute; show me what I left."
9. **FIX: a 0DTE θ/15m chip, display only** (F17). Her reason: "two-thirds of my trades are on expiry day."
10. **FIX copy: one name per state; void-tag the mis-mark** (F14, F18). Her reason: "PAST GIVE-UP, WATCH and WARN are the same thing; say it once."
