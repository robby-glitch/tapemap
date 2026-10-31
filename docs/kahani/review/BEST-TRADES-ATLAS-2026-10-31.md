# BEST-TRADES ATLAS · 31 Oct 2026 · what the best trades looked like (NIFTY, 25 days)

- **Her ask:** "tell me when the best trade happen how it look like because if i see them again more or less we can figure out".
- **Terms (research-findings §1k, as for LOOK-2026-10-21):**
  - descriptive only: rows and counts, **never a rate**;
  - nothing here is a rule. A rule taken from this is a NEW registration, judged on forward days only; these 25 days
    can never test it.
- **Data:** every replayable NIFTY day, 22 Sep → 30 Oct (25 days; 13 and 16 Oct are 45 / 32 min, 12 Oct ends 13:41).
  - Built with `jarvis.build(fill=True)`: holes filled from the saved tape.
  - Reads are causal: each minute as Jarvis knew it then. Futures points [M].
- **The trade measured:** Jarvis's own leg.
  - **In:** at the minute the word turns TREND ("CALL"), or at the first HOLD after it ("PULLBACK").
  - **Out:** when the lean flips (PALAT), or at 15:20.
  - No call after 15:00.
- **In-sample warning:** `legs.py`'s thresholds were set on 19–30 Oct. 22 Sep–16 Oct never touched them.
  - The main pattern is shown in both halves.

## 1. The headline: it is the DAY, not the read

- **The CALL trade:** 57 calls.
  - **Outcomes:** 12 kept ≥ +40 pts; 8 between 0 and +40; 37 lost.
  - **Points:** sum +340, best +284, **sum without the best +56**.
- **The PULLBACK trade:** 52 entries.
  - **Outcomes:** 12 kept ≥ +40; 34 lost.
  - **Points:** sum +288, **without the best −22**.
  - It is no better than the call.
- **Every big winner sits on one of two kinds of day.**
- **The first TREND call of the day, by when it came:**

| first call came | days | positive | ≥ +40 | the days |
|---|---|---|---|---|
| 09:27–09:56 | 11 | 9 | 7 | 28 Sep +98 · 6 Oct +51 · 8 Oct +209 · 12 Oct +122 · 13 Oct +38 · 21 Oct +284 · 23 Oct +65 · 26 Oct +25 · 29 Oct +197 · **5 Oct −58 · 19 Oct −77** |
| 10:00 or later | 9 | 1 (+1) | 0 | 22 Sep +1 · 25 Sep −17 · 29 Sep −48 · 30 Sep −47 · 9 Oct −35 · 22 Oct −24 · 27 Oct −24 · 28 Oct −20 · 30 Oct −25 |

- **The two halves:**
  - 22 Sep–13 Oct: early first calls positive on 5 of 6 days, late on 0 of 5.
  - 19–30 Oct (in-sample): early 4 of 5, late 0 of 4.
- **The exit leaks:** 23 of the 57 calls were +60 or more at some point.
  - Waiting for PALAT (half the leg back) gave back **3,779 pts** of open profit across the 57.
  - On the trend days it did not matter: 10 of the 12 winners ran to 15:20.

## 2. THE BEST TRADE: the first-hour trend day

**What the screen shows when it is there.** Counts are for the 12 winning calls against the 37 losing calls.

1. **The time:** Jarvis's word turns **TREND ▲/▼ between ~09:35 and 09:59**.
   - That was 7 of 12 winners and 2 of 37 losers. This is the strongest tell.
2. **The DAY line says "legs flipped 0 times so far"** (5 of 12 vs 1 of 37).
3. **Location:**
   - price **at the day's new high / low** (6 of 12 vs 5 of 37);
   - **1.5σ or more off VWAP and not coming back** (7 of 12 vs 7 of 37). On the early winners z was 1.7–2.6.
4. **Needed but not enough** (just as common on losing calls):
   - a wall broke with the move, so the leg line shows "TOOT hh:mm" (12 of 12 vs 26 of 37);
   - writers ±7 pushing with it, UP / DOWN / BACK (11 of 12 vs 26 of 37);
   - the wall behind BUILDING (9 of 12 vs 26 of 37).
   - The early failure on 5 Oct had writers PAUSED at the call.
5. **After the call:**
   - pullbacks print HOLD, and the first HOLD was as good an entry as the call (21 Oct 09:57 +310 · 29 Oct 09:55 +208 ·
     8 Oct 09:44 +221);
   - the trade ran to 15:20.

**The two early calls that failed, and what was different:**
- **5 Oct 09:46 ▲ −58:** writers PAUSED, Sides CAPPED, the wall ahead BUILDING; best reach only +7.
- **19 Oct 09:27 ▼ −77:**
  - called before 09:30 at z 1.1 (not yet stretched), with the wall ahead BUILDING and Sides CAPPED;
  - the same day's real trend came at 11:35 (+135).

**Watch them (after 15:40, or at a weekend):**

| day | call | result | replay |
|---|---|---|---|
| 21 Oct ▼ | 09:56, leg 103, z 2.5, writers DOWN, ahead UNWINDING | +284 to 15:20 (MFE +372) | http://localhost:8787/jarvis2.html?day=2026-10-21 |
| 8 Oct ▼ | 09:43, leg 106, z 2.6, writers BACK | +209 to 15:20 | http://localhost:8787/jarvis2.html?day=2026-10-08 |
| 29 Oct ▲ | 09:54, leg 138, z 1.8, writers BACK, fut OI fresh longs | +197 to 15:20 | http://localhost:8787/jarvis2.html?day=2026-10-29 |
| 12 Oct ▼ | 09:53, leg 178, z 1.7, writers DOWN, fut OI fresh shorts | +122 (record ends 13:41) | http://localhost:8787/jarvis2.html?day=2026-10-12 |
| 28 Sep ▼ | 09:36, leg 104, z 2.1, writers DOWN, Sides BACKED | +98 to 15:20 | http://localhost:8787/jarvis2.html?day=2026-09-28 |
| 23 Oct ▼ | 09:55, leg 105, z 2.1, Sides REAL | +65 at PALAT 13:41 (MFE +245) | http://localhost:8787/jarvis2.html?day=2026-10-23 |
| 6 Oct ▲ | 09:56, leg 108, z 2.0, ahead UNWINDING, Sides REAL | +51 to 15:20 | http://localhost:8787/jarvis2.html?day=2026-10-06 |

## 3. THE SECOND KIND: a fresh afternoon leg after a choppy morning

- **The winners:**

| day | call | result | replay |
|---|---|---|---|
| 30 Sep ▼ | 13:42 | +151 | http://localhost:8787/jarvis2.html?day=2026-09-30 |
| 19 Oct ▼ | 11:35 | +135 | http://localhost:8787/jarvis2.html?day=2026-10-19 |
| 28 Oct ▲ | 11:00 | +97 | |
| 27 Oct ▲ | 14:37 | +68 | |
| 26 Oct ▲ | 13:19 | +64 | |

- **What they shared:** the leg was **young at the call (85–113 pts)**; speed FAST with it (4 of 5); no push against in 15
  min (4 of 5).
- **The same window (11:00–15:00) lost 21 times.** 3 more ended +3 to +16. Among the 21:
  - the leg was **already 120–213 pts when called** on 9 (0 of the 5 winners): the move was spent;
  - **Sides SQUEEZE** (a short-covering pop) on 9;
  - writers PAUSED on 4.
- **Worst:** 23 Oct 13:42 ▲, leg 213, SQUEEZE: −111.

## 4. THE TRAP: the rotation day (where following the leg loses)

**What the 37 losing calls looked like:**
- **When:** called 10:00–12:59 (23 of 37).
- **The lean had already flipped twice or more** (32 of 37).
- **Location:** price **within 1σ of VWAP** (25 of 37) and **mid-range** (32 of 37 not at the day's extreme).
- **The leg was already ≥ 120 pts at the call** (13 of 37, vs 2 of 12 winners): called late.
- **Sides SQUEEZE** (10 of 37, vs 2 of 12).
- **The days:**
  - 29 Sep: 5 calls, 4 lost, one +4;
  - 22 Oct: 7 calls, 6 lost;
  - the mornings of 19, 26, 27 and 30 Oct.
- **On these days** most flips cost 15–70 pts. The move often went 30–75 pts their way first, and the PALAT exit gave it
  back.

## 5. What did NOT separate winners from losers (so do not wait for it)

- **ALL 3 indices in sync:** 7 of 12 winners vs 29 of 37 losers.
- **Fut-OI fuel with the move at the call:** 3 of 12 vs 6 of 37.
- **Sides REAL / BACKED:** 4 of 12 vs 6 of 37.
- **The wall ahead UNWINDING:** 3 of 12 vs 11 of 37.
- **When the move was first visible** (at 40 pts), the moves that became trends of ≥ 120 pts had more:
  - a wall breaking with them (10 of 40 vs 6 of 92 that died);
  - the wall ahead unwinding (11 of 40 vs 5 of 92);
  - Sides SQUEEZE (9 of 40 vs 3 of 92).
  - The moves that died mostly ran into a BUILDING wall ahead (71 of 92), and 57 of the 92 were born before 10:00:
    the open's noise.

## 6. How this sits with what was already measured (not re-tested here)

- **At a pause on a trend day:**
  - writers ±7 / Sides LAG: they were with the leg in 17 of 19 reversals, so PAUSED writers mid-trend are not an exit;
  - k1 OI loading during the pause meant continuation (14 of 34 vs 2 of 19).
- **Effort per point at highs / lows** is the one order-flow read that survived the 291-row audit (oi-lab).
- **CVD divergence at highs** was inverted.
- **OI speed at extremes** does not separate holds from breaks.
- **LOOK-2026-10-21:**
  - its best rows sit on this atlas's trend days: RIDE ▼ 8 Oct 11:09 +3.5R, RIDE ▲ SENSEX 6 Oct +2.99R;
  - its FADE POCKET rows that worked sit on rotation days: SENSEX 29 Sep, 30 Sep, 5 Oct;
  - n is tiny everywhere: INCONCLUSIVE.
- **Her two regimes:**
  - the first hour decides which gear the day is in;
  - trend day: ride the leg (RIDE, hold to 15:20);
  - rotation day: the leg is a trap, and the band (her zone, d2→d3 / u2→u3) is the place. The zone's bar is still owed
    forward.

## 7. Not covered

- **SENSEX and BANKNIFTY legs.** SENSEX reads NIFTY's flow (§1q), so the day type is shared. Its own legs were not
  run.
- **Expiry days** are mixed in: 27 Oct NIFTY, and the SENSEX Thursdays.
- **Option premiums:** futures points only.
- **A better exit.** Any trail is a new registration, judged forward.

## 8. Where tops and bottoms formed against the VWAP bands (her ask, 31 Oct)

- **Her words:** "usually market top or bottom forms in which bands of vwap".
- **Method:** z = (price − VWAP) / σ at the extreme's own minute, on Jarvis's 1-min σ (it matches her zone's u2 within
  ~1 pt).
- **Counts only.** This says where extremes formed. It is NOT how often a touch of a band turned (her zone's bar is
  still owed forward).

**The day's high and low** (20 full days; 4 sat at 09:15–09:17, before the bands exist):

| band | all | rotation days | trend days |
|---|---|---|---|
| inside 1σ (VWAP–u1 / d1) | **0** | 0 | 0 |
| 1–2σ (u1–u2 / d1–d2) | 10 | 4 | 6 |
| **2–3σ (u2–u3 / d2–d3)** | **20** | **17** | 3 |
| beyond 3σ | 6 | 4 | 2 |

- **On a rotation day the high and low were made between u2 and u3 / d2 and d3** (17 of 25 readable). That is her
  zone.
- **On a trend day:**
  - one end is the open (09:15–09:22, no bands yet);
  - the other end, late in the day, sits at only 1.3–1.7σ (8 Oct 1.3, 23 Oct 1.4, 21 Oct 1.7, 29 Oct 1.7). VWAP chases
    a trend, so the bands do not mark its end.

**Every swing turn** (≥ 40 pts into it and ≥ 40 back; 124):

| when | inside 1σ | 1–2σ | 2–3σ | beyond 3σ |
|---|---|---|---|---|
| before 09:45 (44) | 4 | 12 | 19 | 7 |
| 09:45–12:00 (48) | 11 | 18 | 17 | 0 |
| 12:00+ (32) | **14** | 11 | 6 | 1 |
| after 09:45, ≥ 80 back (45) | 13 | 15 | 15 | 1 |

- **Swing turns inside the day happen at every band.** In the afternoon they come closer to VWAP: 14 of 32 inside 1σ.
- **Before 09:45 the bands are thin** (σ is still small), so 26 of 44 early turns read beyond 2σ. Do not read the bands
  in the first half hour.
- **u3 / d3 is the outer wall.** After 09:45, price was beyond u3 or d3 for **15 minutes in total over 20 days**:
  - the worst was 24 Sep, 10 minutes;
  - only 1 of 45 big turns formed out there.
- **u2 / d2 is not a wall.** Price lived beyond it for 30–89 minutes on 8 of 20 days (24 Sep 89 min beyond d2, 21 Oct
  57, 28 Oct 44 beyond u2). So the 2–3σ band is where extremes form, but price can sit in it for an hour before it
  turns. On a trend day (21 Oct) it walked d2 without turning.

## 9. Can zone + OI + delta catch the top / bottom, and where to exit (her ask, 31 Oct, before any wiring)

- **Her words:** "check from the past day what happened exactly can we catch the top or bottom using all three … how
  long we hold and where should be look for exit … i get out if the move is stalling … delta is not following the price".
- **Terms:** §1k. §1i (CONFLUENCE) and §1n (FADE-D) stay frozen. Their bar (n ≥ 20 per cell) and R are **not** scored
  here.
- **What this is:** the paths after every band signal the server logged live 21–30 Oct (`data/confluence_log.jsonl`,
  3 indices). Futures points, σ = the band's at the signal, 60 min after.
- **Script:** `scripts/atlas/band_turns.py`.

**A. Did the signal catch the turn?** (which came first, +1σ or −1σ)

| signal | n | +1σ first | −1σ first | neither | reached VWAP | median best / worst |
|---|---|---|---|---|---|---|
| CONFLUENCE (zone + OI + flow) | 8 | 2 | 2 | 4 | 2 | 0.72σ / 0.55σ |
| zone touch, not confirmed | 84 | 33 | 33 | 18 | 46 | 0.89σ / 0.96σ |
| FADE-D (weak delta + CVD turned + OI lead broke) | 11 | 5 | 4 | 2 | 9 | 0.84σ / 1.01σ |
| FADE-D location, not confirmed | 44 | 18 | 20 | 3 | 26 | 1.48σ / 2.62σ |

- **The exact catches:**
  - 21 Oct SENSEX CONFLUENCE SELL 09:45: the day's top, best +501, worst 0;
  - 22 Oct SENSEX FADE-D BUY 09:35: the day's bottom, +610;
  - 23 Oct BANKNIFTY FADE-D BUY 13:15: +355.
- **The misses are one story.** 29 Oct was a first-hour trend-up day. It fired sells against it:
  - CONFLUENCE: BANKNIFTY 09:51 (−255 first), 10:37, 10:39; SENSEX 10:54; NIFTY 14:45;
  - FADE-D: BANKNIFTY 09:25 (−347), SENSEX 10:00 (−393).
  - This is §2 / §8 again: on a first-hour trend day the band is not a top.
- **Verdict:** none. n = 8 and 11: INCONCLUSIVE.
  - Confirmed signals do not yet look different from unconfirmed band touches, which split 33 / 33.

**B. Where real band turns ended** (NIFTY, 25 days; turns made at ≥ 2σ after 09:45 that reversed ≥ 40 pts; 24 turns).
These are turns that DID turn, so the table says where the move went, not whether to enter.

| the move from the band ended | n | points | minutes |
|---|---|---|---|
| short of VWAP | 1 | 64 | 5 |
| VWAP → the far 1σ | 9 | 41–175 | 3–122 (most 3–32) |
| far 1σ–2σ | 4 | 43–195 | 17–64 |
| **the opposite band (≥ 2σ, band to band)** | **10** | **81–308** | **27–160** |

- **VWAP is the first stop:** 23 of 24 crossed it.
- **10 of 24 went band to band**, and those were the big moves: 30 Sep ×3, 5 Oct, 30 Oct ×2, 28 Oct (+308), 9 Oct,
  27 Oct.
- **Median 37 min** from the turn to the end of the move.

**C. Her exit: "stalling + delta not following".** The first stall = 6 min with no new extreme of 0.25U (legs.py's own
pause), on all 147 band signals.

| at the first stall | n | went on ≥ +0.5σ more | came back to entry within the hour | median more after it |
|---|---|---|---|---|
| delta still WITH the trade | 35 | 16 | 27 | 0.45σ |
| **delta AGAINST the trade** | **47** | **27** | 40 | **0.88σ** |

- **Delta against at a stall did NOT mean the move was over.** It went on more often, and further.
  - This is the oi-lab finding again (CVD divergence at highs inverted): counter-delta into a stall is often absorbed,
    and the move resumes.
  - So exiting on "delta not following" cut the band-to-band moves short.
- **Most trades also came back to entry within the hour** after the stall (27 of 35 and 40 of 47).
  - A band trade that is not converted into a ride usually gives the move back.
- **The registered answer is HOLD v2 (§1m, signed 21 Oct, frozen, forward from 22 Oct):**
  - a trail to the last PUSH origin + 0.25U, intrabar, never a candle close;
  - a breakeven lock at MFE ≥ 2R;
  - "gave up" only when the trend front unwinds on the writers' LOSING side;
  - 15:20;
  - **FADE → RIDE at VWAP** when RIDE's OI and FLOW checks agree.
  - That is the band-to-band case in B. Its bar is still owed.
- **Not done (forking paths, n = 24):** what separates a VWAP-stop from a band-to-band move. That is a forward
  question.

## 10. Does VPIN help during the move? (her ask, 31 Oct)

> **RETRACTED, 31 Oct (Fable's review, `docs/effort-result/fable/FABLE-REVIEW.md`, verified by me):** A's split is
> mechanics, not absorption.
> - **The window reaches back before the entry.** The 10-bucket window at a stall holds the push into the band (AGAINST:
>   median 5 of 10 buckets pre-signal). On since-signal buckets only: WITH went on 1 of 19, AGAINST 4 of 10.
> - **A sign-blind count of buckets since the signal splits the same way:** 0–5 buckets went on 21 of 30; ≥ 10 went on
>   13 of 43.
> - **It is a few moments, not many:** WITH = about 8 market moments, 8 of 19 from the 27 Oct expiry.
> - **On leg pauses it does not hold:** lead WITH the leg went on 9 of 20. That population is selected on legs ≥ 40 pts,
>   so it is weak too.
>
> **No VPIN read here is an exit sign. The hold chip stays as registered.**

- **Her words:** "can you check if vpin is helping us in some way during the move because it works and help so check
  along with it".
- **What was read:** the LIVE fast line (`data/vpin_fast.jsonl`, NIFTY-FUT, 20k buckets, what her panel showed). It is
  read the way the hold window's VPIN chip reads it (`fold.py`):
  - the last 10 buckets, one-sided at imb ≥ 0.5;
  - **WITH** = one-sided your way by ≥ 2, **AGAINST** = against you by ≥ 2, else QUIET;
  - stateless (fold's hold-the-chip hysteresis is left out);
  - a log hole of > 15 min = no read.
- **Also read:** pct ≥ 0.90 as "hot".
- **Same signals and turns as §9.** SENSEX reads NIFTY's VPIN (§1q). BANKNIFTY's is a proxy, shown apart.
- **Script:** `scripts/atlas/vpin_turns.py`. §1k terms [M]: counts, no rule.

**A. At the first stall, her exit point.** This is where VPIN said the most.

| VPIN at the stall | n (episodes, days) | went on ≥ +0.5σ more | came back to entry |
|---|---|---|---|
| **WITH you (one-sided your way)** | **21 (10, 7)** | **0** | **20** |
| QUIET | 65 (35, 8) | 34 | 52 |
| **AGAINST you** | **25 (17, 8)** | **17** | 22 |
| pct ≥ 0.90 (hot) | 14 | 1 | 13 |

- **Read it backwards from the chip's label.** One-sided flow still your way while price makes no new extreme is
  effort with no result: the push is spent.
  - One-sided flow against you while price holds is the other side being absorbed, and the move goes on. This is §9 C's
    delta finding, sharper.
- **It is not "the move had already gone far":**
  - stalls ≥ 1σ in: WITH 0 of 11 went on, QUIET 17 of 23;
  - stalls under 0.75σ in: WITH 0 of 7, AGAINST 11 of 18.
- **Not the 60-minute window ending:** stalls with ≥ 30 min left: WITH 0 of 18.
- **Without BANKNIFTY:** WITH 0 of 16.
- **With delta at the stall:**
  - delta against + VPIN against: went on 12 of 16;
  - delta against + VPIN with: 0 of 6;
  - delta with + VPIN with: 0 of 6.
- **This matters for the hold window.** Its VPIN chip shows WITH as "behind you". At a stall, that chip was the exit
  sign, not a reason to hold.

**B. At the band signal (entry).**
- VPIN WITH the fade: +1σ first 0, −1σ first 4, neither 4 (n 9).
- AGAINST: 24 / 17 / 8 (n 49).
- QUIET: 29 / 32 / 15.
- **pct ≥ 0.90 at the signal:** 4 / **10** / 5 (n 19).
  - A hot VPIN as price reaches the band leaned against the fade: the push into the band was still toxic.
- No chip separated a good entry.

**C. Real NIFTY band turns (§9 B, 24 turns, 10 band to band).**
- **VPIN at the turn, in the turn's direction:**
  - AGAINST (the old side still one-sided into the extreme): **8 of 12 went band to band**;
  - QUIET: 1 of 8;
  - WITH: 0 of 1.
  - When one-sided flow into the band fails, that side is trapped, and that is fuel (the operator thesis).
  - This is known only once the turn has happened. At entry (B), AGAINST did not tell whether the turn would come.
- **At the VWAP crossing (the FADE → RIDE point):**
  - AGAINST: 3 of 3 band to band;
  - QUIET: 5 of 12;
  - WITH: **1 of 6**.
  - The same shape as A, on n 3 and 6.

**Verdict:** none. 10 independent episodes for the headline, 8 days of band signals, in-sample, NIFTY VPIN only.
- Under 15 per side is INCONCLUSIVE (house rule 4), so this is a shape, not a proven rule.
- The hold window's VPIN chip (registered) is unchanged. Reading it the other way at a stall would be a new
  registration, judged forward, on her word.

**Regenerate:** `docs/kahani/review/scripts/atlas/` (build → atlas → trade → join · bands · band_turns · vpin_turns; frames cached in `%TEMP%\jarvis_atlas`).
