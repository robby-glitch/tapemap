# TRADER AUDIT — 2026-09-28

**What this is.** An audit of the whole decision path, read the way a 20-year Indian index-options trader reads it.
- **Scope:** OI, order flow, VPIN, the zone, the hold / Validate / expression words, the screen, and the data plumbing
  under all of it.
- **Why:** Mary's 09:35 FOLD on a winning NIFTY 23000 PE.
- **Her rule, in her words:** "i dont care about candle close or anything i have zone oderflow oi and vpin and if these
  are behind me i will hold and not i will fold."
- **How it was done:**
  - five read-only researchers, working during market hours;
  - nothing was edited, restarted or run against `data/`;
  - evidence from `data/hold/*_2026-09-28.jsonl`, `data/chain/`, `data/tape/ux_*`, `data/vpin_*.jsonl` and GETs on the live API;
  - three claims re-checked by hand: the rank bug, the 2-minute row lag, and that the UI never reads `unlatched`.

---

> **CORRECTION, 2026-09-28 about 12:50 (read this before §0 and §3.3).**
>
> **What was wrong.** "The 22900 put writers were 18 points in the money at 09:35" was measured against the chain's index
> **spot**. The options themselves price about 33–49 pts **above** that spot all day.
>
> **The evidence.** Strike + CE − PE near the money, from `data/chain/chain_NIFTY_2026-09-28.jsonl`:
>
> | time | spot | the options' forward | 22900 PE delta |
> |---|---|---|---|
> | 09:33 | 22,902 | 22,935 | −0.42 |
> | 09:36 | 22,877 | 22,913 | −0.46 |
> | 09:39 | 22,863 | 22,900 | −0.49 |
>
> The September future agrees with that forward. So against the price the options trade off, **22900 PE was just out of
> the money at 09:35**: a real floor under her put.
>
> **Why the FOLD's OI half was still false.** Those writers **covered from 09:33** (128.9L → 114.6L by 09:39). The 15-mark
> slope printed "still adding". So the floor was giving way, which was FOR her put.
>
> **What this means for §3.3.** "Either side of spot" still stands as a general defect. But **the larger bug is the
> reference itself**: every module that judges moneyness or ATM against the chain's `spot` (`board.itm`, `board.nearer`,
> the plan rung, hold's ITM/OTM, the expression's ATM) is off by about 35–45 pts today. The rebuild reads moneyness
> against the options' own forward (strike + CE − PE at the money), or against the same-expiry future.

## 0. The verdict

**At 09:35 all four of her reads were behind her put. The tool said FOLD in her best minute** (+16%, then +30% by
09:38). Both of its reasons were defects:

1. **FLOW "against": arithmetic, not the market.**
   - `grounds._rank` puts the current CVD change inside its own comparison list.
   - With 4 bars the rank is always 1.0 ("pressing"); with 5 bars it is at least 0.5 ("strong").
   - So every day from 09:35 to 09:44, any CVD reads strong.
   - The +56 lots was about 1% of volume, smaller than the 1,574 lots whose side the feed only guessed. And it was buyers
     lifting while the future fell 38 points. That is absorption: trapped buyers, which is **for** a put.
2. **PAYERS "against": the wrong strike, read the wrong way.**
   - The 22900 put writers were **18 points in the money** at 09:35. They had been covering every minute since 09:33:
     132.0L → 127.6L, and 114.6L by 09:38.
   - The tool printed "adding in your way … still adding [M]". Its OI state compares against 15 minutes ago, so it cannot
     see a turn until the drop passes the level of 15 minutes back. That took 7 minutes and a 26% give-back.
   - A put strike above spot is not a floor. It is underwater writers, which is her fuel.

**Then the latch froze FOLD for the rest of the day.**
- The live read went to WATCH at 09:39 and HOLD at 09:45.
- **The screen cannot show that.** No file in `ui-v2/src` reads `unlatched`.
- It told her, while still in: "a re-entry is a new trade".

**The bigger finding: most of the machinery is not her method.**
- The hold window folds on a session-high line with a 3-min close, a trend vote, a 15-minute quiet clock and a latch.
  She uses none of them.
- **VPIN, one of her four, reaches no decision at all.**
- **The zone disappears once she is in a trade.**
- **Every Validate row lands about 2 minutes late.** The 09:35 row was written at 09:37:04.

---

## 1. Today's trade as the trader saw it versus the tool (long 23000 PE, 120.4 at 09:30)

B = behind her · A = against · N = neutral. The order-flow column uses the true reads (signed VPIN buckets plus
prints), not the bugged CVD.

| t | premium | Zone | Order flow | OI | VPIN | should say | tool said |
|---|---|---|---|---|---|---|---|
| 09:31 | +1.0% | B | B | 22900 PE still loading below spot: A | B | WATCH (a defended floor) | WATCH |
| 09:33 | +5.7% | future into the d2 pocket: B | B | spot through 22900; its OI peaks. Trapped writers: B | sell bucket: B | **HOLD** | WATCH ("in your way") |
| 09:35 | +16% | d2 BUY fade armed but gate-illegal: B | three one-sided sell buckets: B | 22900 PE covering, CE 23000 stacking: B | imbalance 1.0 sell: B | **HOLD, strongest minute** | **FOLD** (rule 6), latched |
| 09:37 | +27.7% | B | B | the 22900 fold event: B | B | HOLD | FOLD |
| 09:39 | +28.2% | N | buyers at the low: A | B | buy buckets: A | WATCH | FOLD (live: WATCH) |
| 09:41 | +23.8% | N | A | N | A | **FOLD** (2 against, held) | FOLD, for a stale reason |
| 09:43 | | N | N | N | back to sell | back toward HOLD | FOLD to the close |

**The entry checks at 09:26 and 09:27 said WAIT.** Setup, Room and Paying were all blind by construction, and "Right
now" was decided by "the line and trend", the two inputs she does not use. A live read of her four would have said
WATCH on the 22900 floor.

---

## 2. What comes out: rules she doesn't want

| rule | where | why it goes |
|---|---|---|
| **The session-high line with a 3-min close (rule 3)** | `hold.py:221-370`, `hold.py:51,121-123,326-341` | She exits on zones, levels, order flow, OI and VPIN, never on a candle close. Today the line was 172 pts away and did nothing, but it also drives PATA NAHI, Validate *Room*, expression *ROOM*, the writer's *Cushion* and the plan's ₹ "risk". |
| **Noise B** (15 candles) | `hold.py:142-149` | It exists only to buffer the candle-close line. |
| **Trend as a fold family (rule 6) and as WATCH** | `hold.py:485-486, 503-506`; expression REGIME `expression.py:248-256` | Not one of her four. The 1h row at 09:30 is mostly yesterday. It decided her 09:26 entry check. Keep it on screen only if she wants it. |
| **The quiet clock (rule 5)** | `hold.py:478-480, 495-498` | A time rule, not a market read. |
| **The FOLD latch and "heal"** | `hold.py:518-541, 620-630`; legend `HoldTab.tsx:567`; un-closable `HoldWindow.tsx:165-167` | Her rule is present tense. Log the first FOLD minute as the stamp for the record, but show the live word. |
| **PERSIST = 3 on OI** | `hold.py:47, 404-407` | Lag on top of a lagging read. It can't catch a stale BUILDING. |
| **The 15-mark OI warm-up** (blind to 09:29) | `fronts.py:49`, `server.py:1693-1695` | OI doesn't trade overnight, so it can read from the first mark (§6). |
| **Order flow needs 4 closed 5-min bars** (blind to 09:35) | `grounds.py:50, 78-80` | She wants live. §4 reads 1-minute bars. |
| **The expression reads only at 3-min closes, ATM only, with a t−15 straddle** | `expression.py:57, 80-94, 196`; `server.py:2524, 2616` | Candle cadence. Today it read 22900 while she held 23000. ROOM and REGIME come out with the line and trend. |
| **Rev 5 §C precedence: "adding" beats a live fold** | `hold.py:686-689` | At 09:37–09:38 the stale slope outvoted the fresh fold. |

**Kept, by her choice:** the zone's 09:25 anchor, so the forward record stays one clean population.

---

## 3. Code bugs: these measure wrong whatever the method

1. **The CVD rank ranks against itself** (`grounds.py:65-68`). Flow is "strong" 09:35–09:44 every day. It feeds hold,
   Validate *Paying*, expression SPEED / R1 / R5, `/api/calls`, and the futures-OI quadrant (`grounds.py:105`). A false
   "with" also resets the quiet clock.
2. **OI state compares against 15 marks ago and against today's change, not the book** (`fronts.py:95-102`, scale at
   `:97`).
   - It is slow on the turn: 22900 read BUILDING until 09:38.
   - A carried wall reads BUILDING on a bounce. 23000 PE is 146L carried, and a +2.1L bounce beat a 0.49L band.
   - Its first reading compares against 0.
3. **The payers front is picked on either side of spot** (`server.py:1709` → `board.nearer` `board.py:77-80` →
   `hold.py:392, 686-689`). An in-the-money payer strike is counted as a floor. **Five modules use five different rules
   for "the wall"**:
   - fade gate / grounds: #1 by OI, either side;
   - hold / board: nearer of the top 2, either side;
   - board headline: any sized build;
   - plan rung: strictly beyond spot, **the only correct one**;
   - expression WALL: within half a step, on the OTM side.

   At 09:35 they disagreed about the same strike in the same minute.
4. **"Writers" is tagged [M]; it can only be [I]** (`hold.py:688, 695, 727`; `board.py:84-132`; `expression.py:244`).
   OI up can be new buyers. The grid already stores premium and delta per strike to tell them apart
   (`chain_metrics.py:351`, `engine.py:257-261`), and nothing uses it.
5. **`paying()` prints "adding again, still 13.5L under its peak" when OI fell every minute** (`board.py:90-91`).
6. **"paid at 09:38: flow with you" when flow was against** (`expression.py:209-210`, `validate.py:225-226`). The text
   falls back to flow when PAYERS isn't "for".
7. **The OI baseline is the 09:15 candle, not the previous close** (`upstox_adapter.py:316-330`, `upstox_rest.py:119`).
   - Today's gap from 23140 to 22975 covered in-the-money puts: 23100 PE −26.3L, 23000 PE −10.9L, 22900 PE −2.7L.
   - That was the morning's biggest trapped-inventory event, and it is hidden inside the baseline.
   - A missing baseline becomes `oi_chg = 0` = "never built" (`chain_live.py:234-237`), a missing value rendered as zero.
8. **`built = peak > 0`** (`server.py:1667, 1706`). The board calls 23000 PE "CARRIED 94%", and the hold window counts it
   as built today.
9. **Ladder bars are read a minute late**: `+5 <= now` at `server.py:1505, 1717, 1924` and `board.py:319`. Nothing signed
   requires the extra minute.
10. **Every Validate row waits for Upstox's REST 1-min index candle** (`server.py:1889-1896`). Rows land about 2 minutes
    after the minute: 09:29 at 09:31:04, 09:35 at 09:37:04.
11. **VPIN's buy/sell classifier disagrees with the ladder.**
    - 09:56:37: 478 lots lifted at the offer. The ladder booked BUY (correct, a +605-lot run). VPIN's tick rule booked the
      bucket **sell 19,545 / 20,000**.
    - Two classifiers read one future. Feed VPIN from the ladder's fills.
12. **VPIN's first percentile is 10 buckets ranked against 1–9 of their own averages.** That makes it a "new high of the
    day" detector, not a toxicity level. `gate.py:39-42` prints "would be NO NEW RISK — VPIN burst" off this shadow
    gauge.
13. **The futures picker has no date filter** (`upstox_instruments.py:187-191, 298`, `futs[0]` by expiry; options *do*
    filter by now). On a roll morning, a cached instrument dump can hand the ladder, VPIN and book an **expired**
    future. See §7.
14. **SENSEX order flow isn't a real read.** 4–185 lots per 5 minutes; one bar decides it. It should read blind, with the
    lot count as the reason.
15. **The screen:**
    - It never reads `unlatched` or `healed_since`.
    - The word (FOLD) and the count ("3 for · 0 against") contradict each other.
    - The sentence stays frozen at 09:35 while the live rows hide in a collapsed panel.
    - Row changes make no sound under a latch, so the real turn at 09:56 was silent.
    - The target vanishes at a FOLD while she is still in.
    - "(buffer 0 until the candle is read)" is invented (`HoldWindow.tsx:242`).
    - "nothing un-latches a FOLD" is styled as *checked, found nothing* (`parts.tsx:61`).
    - The premium mirror says "checked, none" for "not yet" (`board.py:597-599`).
    - Details: UI audit (§8).

---

## 4. Her four reads, rebuilt: live every minute from 09:15

Each read says **BEHIND / AGAINST / NEUTRAL**, or "could not check — <why>". d, Q (the payers' side) and R (the
holders' side) come from the existing thesis table (`hold.py:74-77`, correct for all four roles).

### ZONE [M]
- **What it reads:** the zone machine (d2→d3 buy, u2→u3 sell), with the 09:25 anchor kept, and the §1d fade gate.
  Price position is read on the live future each minute. The zone machine's 3-min bars are the zone's own definition,
  which she chose to keep; nothing else waits on a close.
- **Long CE / short PE (d = +1):**
  - behind: the BUY machine is armed, triggered or in trade with a legal gate; or price is mid-channel with SELL waiting;
  - against: SELL is triggered with a legal gate; or price is in d2→d3 with the BUY fade gate illegal (the defenders
    gone).
- **Long PE / short CE:** the mirror image.
- **Could not check:** until the first gated bar (about 09:29). The row says so; the other three still read.

### ORDER FLOW [I]: the NIFTY future, 1-minute ladder bars
- **The window:** the last 5 finished 1-minute bars. From 09:15 it uses all bars so far, printed "n of 5".
  - ΔC = net aggression, V = volume, G = volume whose side was guessed, Δp = the future's move, B = a typical 1-min
    range from today's candles so far.
1. **V < 50 lots** → could not check: "future too thin".
2. **|ΔC| ≤ G** → **neutral**: "two-sided — the net is inside the guessed volume". *(At 09:35 today: +56 ≤ 1,574, so
   neutral, not against.)*
3. **Price follows the aggressors** (same sign, at least half of B) → **initiative**: behind if with d, against if not.
4. **Price does not follow** → **absorption**:
   - near a level (a wall strike, the session high or low, the zone band) it reads for the *passive* side;
   - away from a level → neutral.
5. **A run of 100+ lots now at least B beyond its own price, against its side, is trapped.** It can break a neutral but
   never decides alone.
6. **SENSEX:** could not check while its future trades too thin to read.

### OI [M change, I who]: read at levels
- **Position against spot:**
  - **WALL** = the nearer of the two biggest OTM Q strikes ahead of price;
  - **TRAP** = Q's in-the-money / ATM top two;
  - **BACK** = the nearer of the two biggest OTM R strikes behind price.

  This is the plan rung's rule, and it becomes the one rule every screen uses.
- **The move:** d5 = OI now − 5 marks ago, d2 = now − 2 marks ago, X = 1% of OI.
  - FLAT if |d5| < X;
  - TURNING if d2 opposes d5 by at least X;
  - otherwise ADDING or SHEDDING.
- **Who [I]:** the strike's premium move, net of delta × the index move, against the median of its neighbours.
  - Adding with rich premium → "buyers"; otherwise "writers (assumed)".
  - Shedding with cheap premium → "longs out"; otherwise "writers covering (assumed)".
- **The verdict:**
  - **AGAINST:** the WALL is adding by writers, or the BACK is shedding by writers covering. A writer keeps her
    own-side squeeze clause (`hold.py:470-471`).
  - **FOR:** a TRAP is shedding by writers covering, or the WALL is shedding, or the BACK is adding.
  - A TRAP that is adding is never against. If FOR and AGAINST both fire, the read is neutral and both facts are printed.
  - No PERSIST. FOLD_LIVE = 15 stays.
- **At 09:35 today:**
  - TRAP 23000 PE shedding −4.1L → for;
  - TRAP 22900 PE turning;
  - WALL 22800 PE flat;
  - BACK 23000 CE +23.9L → for.
  - **The read is FOR.** The tool said AGAINST.

### VPIN [I]: signed, built from the ladder's fills
- **The window:** the last 10 buckets of 20,000 units. A bucket is one-sided if its imbalance is at least 0.5.
- **TOXIC** when at least 5 of the 10 are one-sided. Its side is buy or sell if one side is at least twice the other;
  otherwise mixed.
- **Buyer:** toxic with d is behind; toxic against d is against; not toxic or mixed is neutral.
- **Writer:** toxic toward her danger (or mixed) is against; not toxic is behind; toxic with her is neutral.
- **Printed as:** "7 of the last 10 buckets one-sided, 6 sell [I]". The percentile is printed, never counted.
- **Could not check:** fewer than 10 buckets (the first is about 09:18 on the fast line).
- **Her call:** VPIN is a shadow gauge on an unfinished 30-session kill test. Making it a vote is her decision, and
  it would be recorded as such.

---

## 5. The word: a proposal she sets when signing

- **HOLD:** nothing against you, at least one behind.
- **WATCH:** something against short of FOLD, or nothing behind. It always names what would turn it to FOLD.
- **FOLD:** at least 2 against, and against outnumbers behind.
- **PATA NAHI:** fewer than 2 of the four could be read. It names each one that couldn't.
- **No latch.** The screen shows the live word, e.g. "was FOLD 09:41–09:42". The first FOLD minute is still logged as the
  stamp for the record.

**Her two numbers:**
1. How many against = FOLD. (The proposal is 2; her words could also mean 1.)
2. Whether a FOLD must hold a second minute before it shows. The proposal is **no**: live, as she asked.

---

## 6. The plumbing: reading from 09:15

| gap today | fix |
|---|---|
| **The chain's first mark lands at about 09:17 every day** (`upstox_chain.py:56-80`, `chain_live.py:563-566`). It waits for today's candle to centre the strikes. | Centre on the future's price or the previous close, and subscribe before 09:15. |
| **The book / ladder record starts at 09:17** (09:17:01, 09:17:15 and 09:17:19 on three days), so the 09:15 bar is partial. | Same: be subscribed before the open. |
| **Rows wait for the REST 1-min candle** (about 2 min late). | Build the 1-min index candle from the socket's ticks. Reconcile with REST later, tagged. |
| **The OI baseline is the 09:15 candle.** | The previous session's last snapshot, **same expiry only**. Otherwise the 09:15 candle, and say so. |
| **The morning backfill (09:15–09:16) lives only in memory** (`chain_backfill.py:241-268`). | Write it to disk, tagged backfilled. |
| **No contract on the records.** Chain snapshots have no expiry; ux and VPIN rows have no contract key. | Stamp `expiry` / `instrument_key` on every row. The tail-carry and the baseline use it to refuse a splice across two contracts. |

- **OI and futures CVD don't change overnight,** so the previous session's tail can seed any window, same contract only.
- **Premium and price gap overnight,** so they start from the open.
- **With the §4 reads, OI needs 5 marks and flow reads from its first 1-minute bar.** The tail carry becomes a
  nice-to-have, not the thing everything waits for.

---

## 7. Expiry and roll risks (this week)

- **Tuesday 09-29 is a triple expiry:** the NIFTY weekly, the NIFTY September future, and BANKNIFTY's monthly options
  and future.
  - One day out, in-the-money writers carry high delta and gamma (23000 PE delta −0.62 at 09:35), so their covering is
    fast and forced. That is exactly what the 15-mark slope smears.
  - The September future's OI went 15.56M → 14.01M → 11.65M over three opens. The `fut_oi` quadrant ("longs exiting")
    is reading the roll, not positioning. **Blind it for the near contract in expiry week.**
- **Wednesday 09-30: a dead-future risk** (bug 13).
  - If the instrument dump in use was cached on the 29th, `fut_key` can pick the **expired September future**.
  - The ladder, VPIN and book would then watch a dead contract, and order flow would read "could not check" all day.
  - **The fix is a one-line date filter, the same one options already use. It should go in before Wednesday's open.**
- **Also on Wednesday:** every NIFTY and BANKNIFTY tail on disk is a different contract. No tail may be carried, and the
  expiry stamp (§6) is what lets the code know.

---

## 8. What stays (correct, keep)

- The thesis table for all four roles (`hold.py:74-77`) and the writer's own-side squeeze clause (`hold.py:470`).
- The premium is never an input to the verdict (`hold.py:513`).
- FOLD_LIVE = 15 minutes.
- NEAR = 9 strikes, and top two by session-high OI (applied within each zone).
- The board's carried vs built-today labels (`board.py:144-159`).
- The §1d fade gate; today it correctly called the 09:48 BUY d2 illegal.
- The zone machine and its 09:25 anchor.
- `ladder.side_of`: it correctly booked the 09:56 lift as a buy.
- The NIFTY future as the direction instrument (dealers hedge there).
- The three absence sentences, [M]/[I] tags, no order path, LIGHT only, and one shared poller so the tab and the float
  can't disagree.

---

## 9. Signed sections this touches (one amendment for her to sign)

- **PREREG-merged rev 4:**
  - §1: which strike each role reads;
  - §2: the line, "nearer", order flow, trend and the blind rules;
  - §3: rules 1–8 and the entry-check copy;
  - §4 and §5: the line;
  - §6: SLOPE 15, which front, the ladder window, trend rows, the quiet clock, the latch;
  - §7 and §8: clauses and log fields keyed to rules 3, 5 and 6;
  - §10: the side read, which is built on trend.
- **PREREG-rev5:** §A.0 (incl. A.0.5 latch, A.0.6 heal), §A.2 (option B), §B, §C (precedence), §D.1–2, §F.1–4, §G.
- **VALIDATE rev 2:** §1.1 stays as ZONE; §1.2–1.4, §2, §3, §4 (the stratum) and §5 change.
- **EXPRESSION rev e:**
  - §A.2 (the 3-min cadence);
  - §A.3 facts 1–4;
  - §A.4 (R1, R2, R5);
  - §A.5 (ATM only);
  - §B.1–B.3;
  - §C ("window unchanged" is no longer true);
  - §E.1–E.2.
- **PLAN rev 3:** §2.1 (stop and risk measured to L), §2.2 (the rung becomes the one wall rule), §3, §5, §6.
- **`context/research-findings.md`:** re-anchor §1e–§1h. §1d stands.

---

## 10. Order of work (nothing during market hours; commit on her word)

1. **Tonight, bug fixes only, which change no method:**
   - the futures date filter (bug 13, before Wednesday);
   - the rank fix (bug 1);
   - the ladder minute (bug 9);
   - the [I] tags (bug 4);
   - the false "paid" and "adding again" text (bugs 5 and 6);
   - `built` (bug 8);
   - SENSEX flow reading blind (bug 14).

   The rank fix changes flow words on every screen, so it gets a line in the §2 change log.
2. **The amendment (§4 and §5), written for her signature,** then built:
   - the four reads;
   - the live word and no latch;
   - the one wall rule everywhere;
   - Validate's entry check = the window's word at t, with ZONE as *Your setup*;
   - the expression reads her strike every minute, with SPEED = order flow + VPIN and WALL = the one wall rule;
   - the screen shows the live word and the four rows in the band, sounds on row changes, and keeps the target visible.
3. **The plumbing (§6):**
   - subscribe before 09:15;
   - tick-built 1-min candles;
   - the previous-close baseline;
   - contract stamps on every record;
   - the backfill written to disk.
