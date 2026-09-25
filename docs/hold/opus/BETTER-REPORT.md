# The better-trade read: replay report (Opus)

Written 2026-09-25 00:59 IST (clock). The rules are in `BETTER-RULES.md`, written at
00:50, before this read was computed at any minute. Its §11.1 records one
proposal made after the data. **Nothing here is registered and nothing is evidence:
three sessions, two of them expiry days.**

Files (`docs/hold/opus/`):
- `better.js`: the read, written once;
- the panel in `hold-window.html`. The panel opens beside the window when her trade
  reads AGAINST, or when she entered into a broken setup. Tick "I am flat" to see it
  on its own;
- `scratch/better_replay.js`, and its outputs `better_out*.json`, `better_dist*.json`;
- `scratch/build_facts.py`, extended to all three indices on 09-22, 09-23 and 09-24.

## 1. The read, in plain words (what she sees)

1. **The first line, only when she is in a trade.**
   - "You entered into a broken setup" (the window read FOLD at her entry minute),
     and/or
   - "Your trade vs today: AGAINST / AGREES / UNCLEAR", with the one sentence why.
     For example: "NIFTY reads a SELLING day and you are a buyer — you are paying
     time on a writers' day."
2. **Three rows**, NIFTY / BANKNIFTY / SENSEX. Each shows:
   - the day word: BUYING day (calls or puts), SELLING day, or NEITHER is clean;
   - the side (buy CE, buy PE, write both sides, write CE, write PE);
   - "n for · m against". The cleanest index is in bold.
3. **The day on her index, with why:**
   - the REGIME halves (price rows, OI read);
   - four facts, marked ● / ✕ / ?:
     - STRONG,
     - folds in the last 15 min,
     - 15-min CVD,
     - the ATM mirror (both premiums against their own VWAP).
4. **Cleanest index:** the most facts for and none against. Ties are named, and
   "not clean" is said when every clear index has something against it.
5. **The engine's trade:**
   - the zone machine's latest arm or entry in 15 min;
   - its §1d gate as logged;
   - whether it agrees with the day;
   - the engine verdict's grounding (calls log).
   - It ends as "a good call / a bad call / thin", with the facts that decided it.
6. **Best · second best:** across all three indices and both roles (buy, or write
   the side whose writers are holding), ranked by counts. No size, strike or price.
7. Light, no charts, no sound, no odds. The three absence sentences are used as
   written: "checked, none — no zone arm…", "could not check — the calls log starts
   on 2026-09-24", and the rest.

## 2. What it said at each of her entries

The read is at the minute finished before the fill. "Window" is the HOLD/FOLD draft's
entry read. "Draft" is BETTER-RULES as written. "B-11.1" is the post-data proposal
(day word from the price rows). "Her 30′" is her contract's premium change over the
next 30 minutes, in points.

| entry | window | draft: her index · check | B-11.1: her index · check | B-11.1 best | her 30′ | her ₹ |
|---|---|---|---|---|---|---|
| 09-21 14:00 NIFTY 23300CE | — | could not check (no chain record 09-21) | same | — | ? | −754 |
| 09-22 09:42 NIFTY 23300CE | WATCH | NEITHER · UNCLEAR | NEITHER · UNCLEAR | none clean | +3.5 | −471 |
| 09-22 10:32 NIFTY 23550PE | WATCH | NEITHER · UNCLEAR | BUY calls 1/3 · **AGAINST** | NIFTY buy CE | **+46.9** | +601 |
| 09-22 10:42/43/44 NIFTY 23550PE | WATCH | NEITHER · UNCLEAR | SELL 1/4 · AGAINST | NIFTY write CE | 0 / −2.4 / −3.2 | +793 / −224 / +163 |
| 09-22 10:52 NIFTY 23500PE | HOLD | NEITHER · UNCLEAR | SELL 0/5 · AGAINST | SENSEX write CE | −26.0 | −855 |
| 09-22 13:48 NIFTY 23500PE | FOLD | NEITHER · UNCLEAR | SELL 2/2 · AGAINST | none clean | **−61.9** | +1,410 |
| 09-23 09:18 NIFTY 23450CE | PATA NAHI | could not check (fronts forming) | same | — | −1.2 | −65 |
| **09-23 09:47 NIFTY 23450CE** | WATCH | **SELL 3/0 · AGAINST** | SELL 4/0 · AGAINST | SENSEX write both sides | −4.0 | −497 |
| **09-23 09:49 NIFTY 23400PE** | WATCH | **SELL 2/0 · AGAINST** | SELL 3/0 · AGAINST | SENSEX write both sides | −17.7 | −52 |
| **09-23 10:00 NIFTY 23450CE** | **FOLD** | **SELL 3/1 · AGAINST + "broken setup"** | SELL 4/1 · AGAINST | NIFTY write both sides | +4.3 | −507 |
| 09-23 10:19 NIFTY 23450CE | HOLD | NEITHER · UNCLEAR | SELL 3/1 · AGAINST | NIFTY write PE | +8.6 | **+205** |
| 09-23 10:33 / 11:07 NIFTY 23450CE | HOLD / WATCH | NEITHER · UNCLEAR | NEITHER · UNCLEAR | none clean | +3.4 / +1.5 | −29 / −367 |
| 09-23 11:32 SENSEX 74900CE | HOLD | NEITHER · UNCLEAR | NEITHER · UNCLEAR | none clean | −3.1 | −305 |
| 09-24 09:42 SENSEX 74200PE | WATCH | NEITHER · UNCLEAR | NEITHER · UNCLEAR | none clean | −4.7 | +475 |
| 09-24 10:19 SENSEX 74200PE | HOLD | NEITHER · UNCLEAR | BUY puts 2/1 · AGREES | SENSEX buy PE | −35.3 | +456 |
| 09-24 12:32 / 12:35 / 12:44 SENSEX PEs | HOLD | NEITHER · UNCLEAR | BUY puts 3/1, 3/1, 2/1 · AGREES | BANKNIFTY write PE / NIFTY buy PE | +11.5 / −38.3 / −27.0 | +546 / −752 / −159 |
| 09-24 13:26 SENSEX 74000PE | WATCH | NEITHER · UNCLEAR | NEITHER · UNCLEAR | none clean | **+196.9** | +716 |
| 09-24 13:41–13:57 SENSEX PEs (6 entries) | HOLD / WATCH / FOLD | NEITHER · UNCLEAR (best: **NIFTY buy PE, 3–5 for · 0 against**) | BUY puts 2/1 to 4/0 · AGREES | NIFTY buy PE | +15.9 to +133.1 | +30 to +592 |
| 09-24 14:23 SENSEX 73800PE | HOLD | NEITHER · UNCLEAR | BUY puts 3/1 · **AGREES** | NIFTY buy PE | **−125.3** | +147 |

**The engine check at her entries (draft):**
- **09-23 10:00:** "a bad call — zone BUY d2 entry 09:57, §1d gate ILLEGAL (PE 23400
  stopped building at 09:53)".
- **09-24, from 12:44 to 14:23**, every entry drew "a bad call". Each time it was the
  zone machine re-arming BUY d2 into the fall with the gate ILLEGAL: "engine says NO
  FADE", or "PE 74000 gave up its build at 11:12". The engine verdict in the calls log
  moved through CONTRADICTED ("SPENT — don't chase"), THIN ("GO") and BACKED ("GO", at
  14:23).
- **09-22:** "thin — §1d gate not logged". The gate was added to the log on 09-23.
- Everywhere else: "checked, none — no zone arm or entry in the last 15 min".

## 3. The same rule reads the range day and the trend day differently (P1)

Minutes per day word, stable for 3 minutes, over 375 minutes:

| index · day | draft (REGIME) | B-11.1 (price rows) |
|---|---|---|
| NIFTY 09-23 (range) | SELL 30 · NEITHER 330 · blind 15 | **SELL 212** · NEITHER 148 |
| SENSEX 09-23 | SELL 23 · BUY calls 7 · NEITHER 329 | SELL 165 · BUY calls 65 · NEITHER 129 |
| NIFTY 09-24 (trend down) | **BUY puts 30** · NEITHER 331 | **BUY puts 134** · SELL 25 · NEITHER 202 |
| SENSEX 09-24 | **BUY puts 27** · NEITHER 334 | **BUY puts 175** · NEITHER 186 |
| BANKNIFTY 09-24 | BUY puts 3 · NEITHER 356 | SELL 150 · BUY puts 23 · NEITHER 186 |
| NIFTY 09-22 (expiry, fell 10:20–10:50) | SELL 11 · BUY calls 11 · NEITHER 333 | SELL 199 · BUY calls 33 · NEITHER 123 |

- **The direction is right in both versions.** 09-23 reads SELLING, and 09-24 reads
  BUYING puts. **Neither reads SELLING on 09-24's SENSEX, and neither reads BUYING puts
  on 09-23.**
- **The draft almost never binds.** It gave a clear word on 6–8 % of readable minutes.
  REGIME needs price **and** `board.oi_read` to agree, and the OI half reads BOTH
  LEAVING on about half of every day's minutes. So P1 as written ("most SENSEX minutes
  after 10:15 are BUYING puts") **failed**. By its own falsifier (a clear word on fewer
  than 1 in 10 minutes), the draft is heading for deletion.
- **B-11.1 binds on roughly half the minutes.** It is a post-data proposal (§11.1),
  shown only as a toggle.

## 4. Where it would have misled her

**The draft misled by silence.**
- It said "NEITHER is clean / UNCLEAR" at 21 of her 26 readable entries. That includes
  the whole 09-24 afternoon, where the puts paid +15.9 to +196.9 points in 30 min.
- A read that is silent on the day's clearest trend cannot answer "is it a buying
  day".
- It did say something useful there: best = "NIFTY buy PE" (3–5 for, 0 against). The
  index next door was clean while hers was not. SENSEX's OI half read BOTH LEAVING.

**Where it was right, and said so plainly: the 09-23 re-entries.**
- 09:47, 09:49 (the put) and 10:00 all read "SELLING day — you are a buyer on a
  writers' day — AGAINST". 10:00 also carried "you entered into a broken setup".
  Those three lost ₹497, ₹52 and ₹507.
- The suggested trade instead was "write both sides" (SENSEX or NIFTY ATM). Its ATM
  straddle premium fell 9.5, 5.9 and 1.9 points in the next 30 min, which is the
  writer's way.

**B-11.1 misled at the turns, because the price rows lag:**
- **09-22 10:32 (put):** it read "BUYING calls — AGAINST" while NIFTY was starting to
  fall. Her put went +46.9 in 30 min; its best, "buy CE", went −13.2.
- **09-23 10:19 (call):** "SELLING day — AGAINST". That was her one winning re-entry,
  +₹205.
- **09-24 14:23 (put):** "BUYING puts — AGREES" one minute before the low. The put
  lost 125.3 points in 30 min, and the best, "NIFTY buy PE", lost 33.9.
- **09-24 10:19, 12:35 and 12:44:** AGREES into consolidations (−35, −38, −27 in 30
  min). Those put trades paid later in the afternoon.

**B-11.1 was right:**
- 09-22 13:48: "SELLING 2/2 — AGAINST", and the put gave back 61.9 points;
- the 09-23 re-entries, as the draft;
- the 09-24 13:41–13:57 entries: AGREES, +15.9 to +133.1.

**Engine check:** it never called a zone arm a good call. On 09-24 it called the
repeated d2 BUY arms into the fall "a bad call" every time, which the afternoon
agreed with.

**Other limits.**
- BANKNIFTY has almost no fills in its ladder, and SENSEX prints are mostly blind, so
  CVD carries most of the order-flow count there.
- The ATM mirror is [I] (the chain record's LTP) on 09-22, and on BANKNIFTY and SENSEX
  09-22.
- The 09-24 index candles for NIFTY and BANKNIFTY had to be rebuilt from the chain
  record's spot snapshots [I]. REST stopped serving them after midnight, and I had not
  frozen them. On SENSEX, where both exist, the rebuilt close is within 2.2 points of
  the REST close at the median (8.5 at p90).

## 5. What would have to be registered

1. **The draft as written**, or **B-11.1**, not both. My recommendation is B-11.1's
   price-led day word with OI as a counted fact, **plus a turn guard taken from the
   window**: when the HOLD/FOLD read on the day's own direction is FOLD, the day word
   becomes "changing". That guard is a new idea, not yet written as a rule.
2. **The wrong-trade check (§7):** buyer on a SELLING day = AGAINST. This is her
   failure (b) exactly, and on these rows it was right three times out of three on
   09-23.
3. **The best / second-best ranking (§6)** and its falsifier (§10, P3).
4. **The engine check (§5)** as it is. It needs no new number.

## 6. Found on the way, not mine to fix

**`data/trigger_log.jsonl` mislabels a day at the midnight roll.** At 2026-09-25
00:00:05 the server wrote nine BANKNIFTY zone rows stamped `day: 2026-09-25`. They are
byte-for-byte the 09-24 rows (same bar times 09:36–14:00, same levels). That file is
the repo's one irreplaceable artefact, so this is worth a look after the close. I did
not touch it.
