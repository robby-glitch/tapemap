# 9. The cross-index read and LOOK HERE, rebuilt (design only), 2026-09-29 night

**Her words:** "look at the order flow and oi changes on nifty and banknifty and sensex because what i have seen that when they move in sync kind of the move is real and some time there tops matches etc for overall view … i want the engine to tell me where he is anticipating the move … look here i want it to work properly and has to data backed because in 1 look i figure where move is coming and where there is potential of a move."

**Status:**
- Nothing is built. No code, no `data/` writes, no git, no server.
- Every number below comes from read-only scripts in `…\scratchpad\xidx\` (`load.py`, `metrics.py`, `run_reader.py`, `day29.py`, `sim.py`, `sim2.py`).
- The replays import `reader.py` (the leg engine being built tonight), `band_rotation.py` and `contract_bars.py` read-only.

**Tags:**
- **[M]** measured; **[I]** inferred; **(h)** a hand-picked number for her threshold sheet.
- **δ** is each index's own ruler: K = 3 × its prior-session median 1-minute range, as in `reader.py`.

---

## 0. The answer in ten lines

1. **The three indices are really two voices.** SENSEX's 30 stocks are all in NIFTY 50 [S11].
   - On our data, NIFTY and SENSEX 5-minute returns correlate at a median of 0.95 [M].
   - Their day highs and lows fall in the same minute (median gap 0 minutes, 20 of 23 highs within 5 minutes) [M].
   - BANKNIFTY is the independent voice: correlation 0.80, and its day extremes are within 5 minutes of NIFTY's only 8 of 23 times [M].
   - So "all three in sync" mostly means **the banks agree with the heavyweights**.
2. **Sync is the normal state, not a signal.**
   - All three current legs point the same way in **74 % of minutes** [M] (23 days, index spot, reader-sized ruler).
   - Over NIFTY's own legs, BANKNIFTY and SENSEX moved the same direction in 134 of 136 [M].
   - What separates a real move from a thin one is **magnitude, positions and extremes**:
     - did each peer make a leg-sized move (≥ 1δ)?
     - did positions open in both (WHO)?
     - did every index take its own high or low at the turn?
3. **Her "tops match" is measurable, and it breaks often enough to be worth reading.**
   - At matched swing highs and lows, NIFTY and BANKNIFTY disagree on "new extreme or not" 18 of 73 times [M]. NIFTY and SENSEX disagree 12 of 90 times.
   - On our six book days there are three clean day-level cases: 22 Sep (BANKNIFTY failed the high), 23 Sep (BANKNIFTY held the low) and 25 Sep (NIFTY made a lower low alone).
   - **Hindsight caution:** those were picked with the day's extremes known. Nothing here is a hit rate.
4. **No index leads as a rule.**
   - At matched turns, BANKNIFTY turned first 33 times, NIFTY first 33 times, and 63 were the same minute [M].
   - Futures candles show the same split: 39, 32 and 25 [M].
   - So the engine says who turned first **this time**. It never says "X leads".
5. **The SENSEX future cannot carry a flow read.**
   - It traded 687–3,419 lots a day, with open interest of 3,100–4,500 lots and 66–127 minutes a day with no price range [M].
   - SENSEX is therefore read on the **index** (price legs) and its **options chain** (OI). Its WHO and flow read CAN'T CHECK.
6. **At 15:15 all three spot indices froze on 29 Sep** (NSE and BSE alike) until the auction print [M]. Every cross-index price read is CAN'T CHECK from 15:15.
7. **Cross-index reads are built on `reader.py`, not beside it.**
   - One `reader.Engine` per index runs on the index's own 1-minute candles, for price legs that are comparable and free of roll effects.
   - The futures engines supply WHO and effort.
   - Nothing re-implements a leg.
8. **LOOK HERE becomes a count of six named lines** (zone, flow, WHO, walls, sync, extremes).
   - It is shown as "4 of 6", never a percentage.
   - It is awarded on **her zone plus 2 more lines, or 4 lines without her zone**.
   - Hysteresis holds it steady. On 29 Sep the prototype awarded it 3 times, with 1 switch and 7 changes in all [M, prototype].
9. **Anticipation is honest only as conditions plus levels.** The engine says what is forming, where the move would start, what would confirm it and what would kill it. It never gives a probability.
10. **Built:** `xindex.py` (pure) + `/api/xindex` + three cards. Everything runs in **shadow for 10 sessions**, including the 27 Oct NSE monthly expiry and the 29 Oct SENSEX monthly expiry. The face goes live on her word.

---

## 1. What the research says (cited; [unsourced] where I found nothing)

| Topic | What holds | Source |
|---|---|---|
| **Dow confirmation** | Two averages must confirm each other. A new high in one must "soon" be followed by the other. Dow did not require simultaneity; a shorter gap is stronger confirmation. Non-confirmation means no reliable inference. | StockCharts ChartSchool, *Dow Theory* [S1]; Dukascopy [S2] |
| **Is confirmation worth anything?** | Hamilton's Dow-theory calls (255 WSJ editorials, 1902–1929) earned positive risk-adjusted returns. This is **daily, US, a century ago**, and says nothing about an intraday NSE read. | Brown, Goetzmann & Kumar (1998), *J. Finance* 53(4), 1311–1333 [S3] |
| **SMT divergence** | A practitioner (ICT) concept: correlated index futures (ES/NQ/YM) should make swing highs and lows together, and a failure to confirm marks a possible reversal. **I found no peer-reviewed test of intraday SMT.** The claims are practitioner claims [unsourced beyond S4–S5]. | TradingFinder [S4]; MetroTrade [S5] |
| **Intermarket divergence as a signal** | Tested as a trading rule on daily US markets (bonds/stocks/gold) by a practitioner. Not intraday, not India. | Ruggiero via EasyLanguage Mastery [S6b] |
| **Breadth** | The A/D line should confirm an index high. Failure means narrowing participation. The index cannot see constituent breadth; we do not record NIFTY advance/decline. | StockCharts, *Advance-Decline Line* [S7] |
| **Lead–lag, generally** | The most liquid instrument leads at high frequency, and the lag is **sub-second** for liquid futures (CAC40 future vs Total: 0.6 s). Asymmetric cross-correlations. | Huth & Abergel (2014), *J. Empirical Finance*; arXiv 1111.7103 [S8] |
| **Lead–lag, India** | NIFTY futures lead NIFTY spot in price discovery (1-minute data; Hasbrouck information share). For Bank Nifty, one study summary says spot led futures. I did not re-read that paper [unverified]. **No study found on NIFTY vs BANKNIFTY index-to-index lead** [unsourced]. | Khan et al. (2022), *J. Mathematics* 2164974 [S9]; ResearchGate 375121521 [S10, not re-read] |
| **Heavyweight overlap** | All 30 SENSEX stocks are in NIFTY 50 (100 % of SENSEX holdings, as of 2022). | Stable Investor overlap [S11] |
| **Weights, 29 Sep 2026** | NIFTY: Bank 20.4 % + Finance 6.9 %. BANKNIFTY: HDFC 24.4 %, ICICI 20.4 %, SBI 19.6 %. These are on a **full market-cap basis**, not NSE's capped free-float weights, so they exceed the SEBI cap [unverified vs the NSE factsheet; the NSE PDF would not parse]. | smart-investing.in, NIFTY [S12a] and BANKNIFTY [S12b] |
| **BANKNIFTY rules** | From 31 Mar 2026: at least 14 constituents, the top stock ≤ 20 %, the top three ≤ 45 %. This makes BANKNIFTY less of a two-stock index than before, but HDFC and ICICI still sit in both indices. | 5paisa [S13]; Zee Business [S14] |
| **When they decouple** | BANKNIFTY moves faster and further on bank-specific news (RBI, bank results) and is roughly 1.5–2× as volatile as NIFTY [practitioner]. Pair traders read the BANKNIFTY/NIFTY ratio. | niftypapertrade [S15]; Marketcalls ratio charts [S16] |
| **Expiry days** | NSE contracts expire on Tuesday and BSE on Thursday, from 1 Sep 2025. NIFTY/BANKNIFTY and SENSEX options therefore **never share an expiry day**. | Zerodha bulletin [S17]; Zee Business [S18] |
| **Where SENSEX lives** | BSE held about 31.5 % of Indian equity-options premium in the June-2026 quarter (NSE 68.48 %). SENSEX options are a real market; its future is not. | Multibagg summarising NSE's RHP [S19, secondary] |
| **Anticipation vs description** | Dow's rule is descriptive: it confirms a trend and gives no timing. Nothing I found gives a calibrated intraday probability from cross-index agreement [unsourced]. | S1, S3 |

**What this means for the design:**
- Confirmation and divergence are legitimate things to **describe**.
- Their predictive value intraday on NSE is **unknown**, and our house rules forbid us from estimating it by backtest.
- So the read counts agreeing evidence and names levels. It never prints odds.

---

## 2. What our data says (measured, descriptive; no outcome scoring)

### 2.1 Sources and their limits

| Source | Indices | Days | Use | Limit |
|---|---|---|---|---|
| Chain `spot` (~11 s) → minute OHLC | all 3 | 25 files, **23 usable** (21 Aug–29 Sep) | Price sync, extremes, lead–lag | 11-second sampling: minute ranges are understated, and the three pollers are not simultaneous (possible false ±1-minute lag) |
| Upstox book (1 Hz) → `reader.book_minutes` | all 3 futures | 6 (22–29 Sep) | reader.py legs, WHO, UX Δ | NIFTY and BANKNIFTY are **inside the Sep roll window on all 6 days**. The SENSEX future is thin (below). |
| `data/backtest/*/fut_*.json` 1-minute candles | N, B (S thin) | 52 common, **11 usable** (29 Jul–25 Aug) | NIFTY–BANKNIFTY check at exchange-candle timing | **Contracts are mixed.** BANKNIFTY June to mid-July is a far month with zero-range minutes (the ruler computes 0.0), so those days were dropped. No contract stamp. |
| 29 Sep NIFTY Sep candles (`data-2026-09-29/`) | N | 1 | The canonical minute for NIFTY | Oct was never recorded live |

**The SENSEX future, per day** [M]:

| Day | Volume (lots) | OI (lots) | Minutes with no range |
|---|---|---|---|
| 22 Sep | 687 | 3,847 → 3,692 | 102 |
| 23 Sep | 935 | 3,696 → 3,167 | 127 |
| 24 Sep | 2,826 | 3,216 → 3,103 | 108 |
| 25 Sep | 3,419 | 3,665 → 3,909 | 66 |
| 28 Sep | 1,210 | 3,920 → 4,279 | 83 |
| 29 Sep | 1,425 | 4,283 → 4,512 | 111 |

For comparison, the NIFTY future traded 26–67k lots a day and BANKNIFTY 9–29k.
- An earlier revision of `reader.py` gave SENSEX a ruler of **0 / 4.3 / 6.3 pts** on 22, 28 and 29 Sep.
- The current revision reads 41–89 pts. **Confirm the SENSEX ruler source before shadow.**

### 2.2 Co-movement

| Measure | NIFTY–BANKNIFTY | NIFTY–SENSEX | BANKNIFTY–SENSEX |
|---|---|---|---|
| 1-minute return correlation, spot, median of 23 days (range) | 0.72 (0.53–0.86) | 0.80 (0.53–0.93) | 0.69 (0.36–0.82) |
| 5-minute return correlation, spot | 0.80 (0.44–0.91) | **0.95** (0.68–0.98) | 0.77 (0.40–0.90) |
| 1-minute / 5-minute correlation, futures candles, 11 days | 0.38 / 0.63 | — | — |

Futures 1-minute returns carry bid-ask bounce, and the BANKNIFTY future is thinner. The index series is the cleaner cross-index price.

### 2.3 Sync base rate (causal "current leg" direction, reader-sized ruler, spot)

- **All three the same direction in 5,212 of 7,040 post-warm-up minutes = 74 %** [M].
- By day the range is **50 % (15 Sep) to 99 % (7 Sep)**.
- On the six book days:

| Day | Minutes all the same |
|---|---|
| 22 Sep | 256 / 300 |
| 23 Sep | 246 / 364 |
| 24 Sep | 244 / 358 |
| 25 Sep | 259 / 349 |
| 28 Sep | 230 / 370 |
| 29 Sep | 331 / 370 |

**Over each NIFTY leg's own window** (136 legs):

| Peers' move | Legs |
|---|---|
| Both peers the same direction and ≥ 1δ | 95 |
| One of them under 1δ | 28 |
| Both the same direction but under 1δ | 11 |
| Opposite | 2 |

**Consequence:** "same direction" is nearly automatic. The read must grade **size in δ** and **WHO**, or sync says nothing.

### 2.4 Tops and bottoms

**Day extremes (spot, 23 days):**

| | NIFTY vs SENSEX | NIFTY vs BANKNIFTY |
|---|---|---|
| Median gap, high / low | 0 / 0 min | 13 / 9 min |
| Within 5 minutes, highs | 20 of 23 | 8 of 23 |
| Within 5 minutes, lows | 19 of 23 | 9 of 23 |
| More than 60 minutes apart, highs | 1 | 7 |
| More than 60 minutes apart, lows | 2 | 5 |

On the NIFTY–BANKNIFTY futures candles (11 days), only 2 of 11 highs and 3 of 11 lows fell within 5 minutes.

**Swing pivots (reader-sized ruler, spot, 159 NIFTY pivots):**

| Same-type pivot in the peer | ≤ 1 min | ≤ 5 min | ≤ 10 min | ≤ 15 min | Matched ≤ 30 min |
|---|---|---|---|---|---|
| BANKNIFTY | 79 | 91 | **104** | 114 | 129 |
| SENSEX | 112 | 123 | **130** | 134 | 139 |

A 10-minute window catches 81 % (104 of 129) of matched NIFTY–BANKNIFTY turns and 94 % (130 of 139) of NIFTY–SENSEX turns. That window is the MATCH (h) below.

**Structure at matched pivots** (is each index beyond its own previous same-type pivot?):
- NIFTY vs BANKNIFTY disagree 18 of 73 (25 %).
- NIFTY vs SENSEX disagree 12 of 90 (13 %).
- On futures candles, NIFTY vs BANKNIFTY disagree 25 of 59 (42 %).

**Day-level divergences on the six book days** (described with hindsight, so they are not evidence of an edge):

| Day | What happened [M, spot] |
|---|---|
| 22 Sep | BANKNIFTY's high was 09:30 (56,665). NIFTY and SENSEX made higher highs at 10:10–10:11 while BANKNIFTY sat at 56,595. All three made their lows at 14:00–14:01. |
| 23 Sep | BANKNIFTY's low was 09:25 (56,303). NIFTY and SENSEX made lower lows at 09:54–09:55 while BANKNIFTY held 56,341. NIFTY/SENSEX highs came at 12:20, and BANKNIFTY's at 13:08. |
| 25 Sep | NIFTY made a lower low at 12:57 (23,021.1 vs 23,036.8 at 09:53). BANKNIFTY (+35) and SENSEX (+4) did not. All three made day highs at 14:05–14:38. |
| 28 Sep | All three highs at 09:17; lows at 14:38–14:43. In sync. |
| 29 Sep | See §5: a confirmed top, equal lows. |

### 2.5 Lead–lag

**Cross-correlation of 1-minute returns** peaks at lag 0 for every pair:
- NIFTY → SENSEX at +1 minute is 0.16, against 0.06 the other way. This is probably the 11-second chain-poll offset, not a real lead [I, unverified].
- On futures candles, NIFTY → BANKNIFTY at +1 minute is 0.066, against 0.016 the other way. That is weak, and in the direction Huth & Abergel [S8] predict for the more liquid contract.

**At matched turns:**

| Pair | Peer turned first | Same minute | NIFTY turned first | Source |
|---|---|---|---|---|
| NIFTY–BANKNIFTY | 33 | 63 | 33 | spot |
| NIFTY–SENSEX | 24 | 84 | 31 | spot |
| NIFTY–BANKNIFTY | 39 | 25 | 32 | candles |

There is no standing leader [M].

### 2.6 OI across the indices

**Futures WHO agreement** (`reader.py` legs, 6 book days, all inside the Sep roll window for NIFTY and BANKNIFTY): of 67 NIFTY legs,

| BANKNIFTY's overlapping leg | Legs |
|---|---|
| Opposite direction | 11 |
| OI unreadable on either | 13 |
| **Same WHO class** | **28** |
| Different class | 15 |

Most differences are "rotation" (OI inside noise) on one side against short covering or long liquidation on the other.
- SENSEX futures WHO: **CAN'T CHECK** (thin).
- Ordinary-day (non-roll) futures OI agreement **was not measurable**: the only candle days with front contracts for both are 29 Jul–18 Aug, and those files carry no contract stamp.

**Options walls:**
- The chain holds **one expiry per index**, 17 strikes.
- On 29 Sep, NIFTY and BANKNIFTY options were **0DTE** (monthly/weekly, Tuesday), while SENSEX's were 2 days out (Thursday).
- NIFTY's ATM strikes added 100k–380k lots of OI in 15-minute windows that day [M]. That is expiry-day mechanics, labelled [I].

---

## 3. The cross-index reads (`xindex.py`, pure, shadow)

**Common inputs, as-of stamped:**
- **Index engines:** one `reader.Engine` per index, run on that **index's own 1-minute candles**: `NSE_INDEX|Nifty 50`, `NSE_INDEX|Nifty Bank` and `BSE_INDEX|SENSEX` by Upstox REST. Keys to verify in the dump; REST gives anytime start. Settings:
  - no volume and no OI, so WHO = n/a;
  - K = 3, and δ from each index's own 5-session prior unit.
  - This gives comparable, roll-free price legs for all three and **reuses the leg engine unchanged**.
- **Futures engines:** `reader.py` as built, for NIFTY and BANKNIFTY (WHO, UX Δ effort, the "expiring" label). The SENSEX future engine runs, but its flow and WHO display the reader's own MIN_PRINTS verdict, "patla", and never vote.
- **Zone:** `zone_state` / `zone_state_sell` from `/api/data?idx=&interval=3`, her machine, untouched. It is read live, **not** from `trigger_log` (see §7, finding F3).
- **Chain:** `data/chain/chain_<idx>_<day>` plus `chain_backfill` for the first minutes.
- **Feed health:**
  - per index, the index-candle age, the book age, the chain age, and the zone payload's session label and last bar;
  - LIVE / SLOW / DEAD (thresholds measured before signing, per must-fix 11 of the judgement).

### X1. SYNC: do the three legs agree, and does WHO agree?

| Item | Definition |
|---|---|
| **Direction** | `dir` of each index engine's forming leg (after its first pivot). |
| **Size** | The forming leg's points ÷ that index's δ, e.g. "BANKNIFTY 2.1δ". |
| **States** | **SAATH** = 3 of 3 the same direction and every peer ≥ 1δ. **KAMZOR SAATH** (weak) = the same direction but a peer under 1δ. **ALAG** (split) = one index opposite, named. **CAN'T CHECK** = any index in warm-up or a hole. |
| **WHO agreement** [I] | The forming futures legs of NIFTY and BANKNIFTY, same class or not. SENSEX = "WHO nahi (future patla)". In a roll window, OI-down classes read "or roll" and do not count as agreement. |
| **Lookback** | The current forming leg only. No window. |
| **Self-calibration** | δ per index. No lot counts. |
| **Tag** | Direction and size [M] (index candles); WHO [I]. |
| **Data hole** | An index with no minute for 2 minutes or more gets a hollow grey dot. SYNC is then read on the remaining indices and says so ("2 of 3 checkable"). It never carries a direction across a hole. After 15:15: "cash auction · 15:15 se check nahi". |
| **Weighting note** | NIFTY and SENSEX agree almost by construction (§2.2), so the informative disagreement is **BANKNIFTY vs the other two**. The chip always names the odd one. |

**Chips:**
- "Teeno saath ▲ · BANKNIFTY 2.1δ · SENSEX 1.8δ"
- "Saath par kamzor ▲ · SENSEX sirf 0.4δ"
- "BANKNIFTY alag ▼ · NIFTY/SENSEX ▲"
- "WHO: dono mein naye long" or "WHO: NIFTY short cover, BANKNIFTY naye long"

### X2. EXTREMES: do tops and bottoms match? (two tiers)

**X2-live (on price, anticipatory; this is her "tops match").**
- **Reference extreme per index:** the session high/low so far, or its last confirmed same-type pivot (whichever is nearer to price).
- **Trigger:** any index trades beyond its reference by more than TOL.
- **Check:** each peer's position against **its own** reference, at that minute and for MATCH = 10 min after (h, §2.4).
- **Per-index result:**
  - **TOOK** = beyond by more than TOL;
  - **EQUAL** = within ±TOL;
  - **FAILED** = short by more than TOL.
  - TOL = δ/4 of that index (h).
- **Outcome:**
  - **CONFIRMED** = all TOOK;
  - **DIVERGENT** = at least one TOOK and at least one FAILED;
  - **BARABAR** (equal) = all EQUAL or EQUAL/TOOK mixed at a retest.
- **Lifetime:** a divergence stands until the failing index takes its own reference (live on price), or the next same-type extreme. **The note carries that level.**
- **NIFTY–SENSEX:** a divergence is shown with "chhota" (small) when the failing gap is under δ/2. They almost never truly split (§2.4), so a small split is first a data suspect.
- **Warm-up:** not before 09:30, because the session extremes of the first minutes are trivially new (h, beside her 09:25 anchor).
- **Tag:** [M].

**X2-confirmed (descriptive, lagging).** The same comparison at each engine's **confirmed** pivots. A swing is known only after a δ retrace, so this is the record, not the warning. It feeds the day story.

**Chips:**
- "Teeno ne naya high banaya · 12:07"
- "BANKNIFTY ne naya high banaya (54,392), NIFTY ne nahi (22,719 < 22,723)"
- "Retest par naya low kisi ne nahi banaya · NIFTY −0.1 · BANKNIFTY +3.9 · SENSEX +22.7"
- "Divergence khatam: NIFTY 22,723 ke upar"

**Data hole:** if a peer has a missing minute inside the MATCH window → "CAN'T CHECK: BANKNIFTY 12:03–12:06 missing".

### X3. LEAD: who moved first

| Item | Definition |
|---|---|
| **Events** | Matched pivots (X2), and leg-start confirmations: the minute each index engine confirms a new leg in the same direction within MATCH. |
| **Output** | Each index's minute stamp. A spread of ≤ 1 minute = **SAATH MEIN** (together). The canonical minute cannot resolve less; §2.4 shows 61 % of NIFTY–BANKNIFTY and 81 % of NIFTY–SENSEX matched turns fall within 1 minute. A gap of 2 minutes or more is named. |
| **Relative strength** | Over the same window, each index's move in δ, e.g. "BANKNIFTY 7.1δ · SENSEX 4.8δ · NIFTY 4.5δ → BANKNIFTY sabse tez". |
| **Never** | A standing "X leads" statement. §2.5 shows no stable leader. |
| **Tag** | [M] minute stamps. Sub-minute lead: X impossible on this series. |
| **Data hole** | A hole at the event → "pehle kaun: check nahi". |

**Chips:**
- "Saath mein palte · 11:06"
- "BANKNIFTY 4 min pehle palta"
- "Sabse tez: BANKNIFTY 7.1δ"

### X4. OI across the three: futures WHO plus the options walls

- **(a) Futures WHO.** X1's WHO agreement, per leg and forming.
  - In the roll window, every class says "expiring".
  - Once P2a/P2b exist (the continuing contract captured), the class comes from the continuing contract, as ruled in 7-final §3.2 item 5.
- **(b) Walls, per index.** Taken from the chain window:
  - the CE wall = maximum OI among strikes ≥ price;
  - the PE wall = maximum OI among strikes ≤ price.
  - **Writing within reach:** OI added in the last 15 minutes at strikes within REACH = 1.5δ of price (h).
  - **Noise floor:** 3 × the robust σ of all 34 per-strike 15-minute changes (h).
  - One side "votes" when its add beats the other side's by DOM = 1.5× (h). Otherwise the read is "dono taraf likh rahe" (both sides writing).
- **Cross-index:**
  - "teeno mein PE likh rahe neeche" = support being written in all three;
  - otherwise a split, which is named.
- **Labels:**
  - the chain's expiry per index, and **"expiry din"** on a 0DTE chain;
  - different expiries are never pooled across indices.
- **Tags:** OI [M]; "writing = sellers building a lid or floor" [I] (the buyer or seller of each option is unknown).
- **Data hole:** chain older than 60 s = SLOW, older than 180 s = DEAD → walls CAN'T CHECK. The first 15 minutes read "warming", with `chain_backfill` used where present.

**Chips:**
- "CE likh rahe 54,300 (+2.6k lots/15m)"
- "Teeno mein PE likh rahe neeche"
- "Walls: NIFTY PE 22,600 · BANKNIFTY CE 54,400 · alag"

### X5. POTENTIAL: "move ban sakta hai"

Per index, each condition is named with its level:

| Condition | Rule | Level shown |
|---|---|---|
| **Zone armed** (her machine, primary) | `zone_state` ARMED on BUY d2 or SELL u2 | The line she needs broken (`ref_high` for a buy, `ref_low` for a sell), plus candles left |
| **Range edge** | reader auction = RANGE and price within δ/2 of an edge | Breakout level = edge ± δ (reader's BREAK rule) |
| **Compression** | `band_rotation`'s existing rank < COMPRESSION_RANK 0.30 on the trailing band width. **Reused, not redefined.** | — |
| **OI building at a wall** | X4 writing within reach on one side | The strike |
| **Peers coiled too** | The same conditions in the other indices | Their levels |

**Output:**
- the count of conditions;
- the **start level**, plus **what confirms it** (the zone trigger close, or peers crossing their equivalent levels within MATCH);
- **what kills it** (the zone stop, the range's other edge).

**Chip:** "Ban sakta hai ▲ · zone d2 armed 22,612 · range kinara 22,643 · teeno armed".

---

## 4. LOOK HERE, rebuilt

### 4.1 What is replaced

**Today:**
- `ui-v2/src/data.ts:760-761` scores each index by the number of **BACKED** directional calls from the legacy engine (`engine.py` → `/api/calls` → `grounds.py`).
- `assemble()` (`data.ts:1150-1167`) picks the maximum.
- `App.tsx:251` draws the chip.
- The card words "move spent / running ✗ / go ?" also come from that engine.

**The new source** is `/api/xindex`, built from the reads above.

**Migration:**
- The old path stays until she signs.
- The two run side by side on a shadow toggle.

### 4.2 Direction per index (D)

1. Her zone state, if it is not WAITING (BUY → ▲, SELL → ▼). **Her setup outranks everything.**
2. Otherwise, the forming leg's direction if it is ≥ 1δ on the index engine.
3. Otherwise, in a RANGE: both directions are scored, and the larger is kept. A tie means "dono taraf khula" (open both ways), and there is no D.

### 4.3 The six lines

Each line votes **+** (with D), **−** (against D), **·** (no view) or **CAN'T CHECK**.

| # | Line | + (with D) | − (against D) | Source / tag |
|---|---|---|---|---|
| 1 | **ZONE** | Her machine ARMED, TRIGGERED or IN_TRADE on D | — | `zone_state` [M state] |
| 2 | **FLOW** (effort) | The forming leg in D, the aggressor on D, not absorbed ("pressing with the move"). **Or** the leg against D whose aggressor is being absorbed ("push against it absorbed", *bikri dabi*). | The leg against D winning ("push against it winning"). Or the leg in D absorbed. | Futures reader leg: UX Δ [I], λ rank. SENSEX: CAN'T CHECK. |
| 3 | **WHO** (positions) | The leg in D opening (new longs ▲ / new shorts ▼). Or the leg against D only closing ("neeche naye short nahi, sirf long nikal rahe"). | The leg against D opening new positions | Futures reader leg [I]. In the roll window a closing class = · ("or roll"). SENSEX: CAN'T CHECK. |
| 4 | **WALLS** | Writing within reach on the side that supports D: PE below for ▲, CE above for ▼ | Writing on the other side | X4 [M OI / I meaning] |
| 5 | **SYNC** | Both peers with D (leg or same-side zone) | Neither peer with D ("akela chal raha", moving alone) | X1 [M] |
| 6 | **EXTREMES** | Fade at a zone: a divergence at that extreme. Running move: CONFIRMED new extremes in D. | Fade: CONFIRMED against (all three took the extreme). Running: a divergence against D. | X2-live [M] |

**Feed gate:**
- A line whose feed is SLOW or DEAD is **CAN'T CHECK**. It leaves the count, and the chip says so ("5 of 6 checkable").
- LOOK HERE is never awarded to an index whose zone payload or index candle is DEAD.
- The zone line reads only her machine's served state or its log, never a reconstruction (F3, corrected).

### 4.4 Award, hold, switch, and the churn bar

All of these are (h) until she signs.

| Rule | Definition |
|---|---|
| **When evaluated** | At each 3-minute bar close, her canonical interval. Invalidations stay **live on price**: a zone stop, a range break, a trend break (the reader's live events). |
| **Award** | For ≥ 3 with **her zone among them**, or ≥ 4 without it. **And** for ≥ against + 2. **And** the state is not "ho gaya". |
| **Tie-break** | 1. Zone present. 2. Fewer lines against. 3. NIFTY > BANKNIFTY > SENSEX (liquidity order, deterministic). |
| **Hold** | Keeps LOOK HERE while for ≥ award bar − 1 and D is unchanged and nothing is invalidated. |
| **Switch** | Only to a challenger with at least 2 more lines, after the holder has held at least 2 bars (6 min). |
| **Release** | Goes blank ("koi saaf jagah nahi"), then a 1-bar cooldown before any new award. |
| **Churn bar (pre-registered, measured in shadow)** | ≤ 10 awards per session. ≤ 16 changes (award + switch + release). **0 flips inside 6 minutes.** The state word changes ≤ 12 times per index per session. |

**Prototype replay** [M, scratch `sim2.py`: reader.py futures legs, index-spot legs for SENSEX, reconstructed zone, chain walls; crude lines, unsigned numbers]:

| Day | Changes | Awards | Switches | 3-min bars with a LOOK HERE |
|---|---|---|---|---|
| 29 Sep | 7 | 3 | 1 | 50 / 120 |
| 28 Sep | 11 | 6 | 0 | 56 |
| 25 Sep | 10 | 5 | 1 | 58 |
| 24 Sep | 15 | 8 | 0 | 60 |
| 23 Sep | 2 | 1 | 0 | 17 |
| 22 Sep | 14 | 7 | 0 | 31 |

- Without hysteresis, the plain maximum under the same award rule changed **6–26 times a day**. With a flat 3-line bar and no hysteresis it changed 13–43 times.
- Four or more lines lined up on only 2–9 index-bars a day (of 360). **"4 of 6" is rare, and it should be.**
- *These prototype numbers used a reconstructed zone, which was wrong for BANKNIFTY on 29 Sep (see the correction). The built numbers are in `10-xindex-build.md` and supersede them.*

### 4.5 The one line (the format; the prototype's 12:27 BANKNIFTY example used a void zone line, see §7)

> **LOOK HERE · BANKNIFTY ▼ · 4 of 6 line up:** zone u2 trade mein · bikri dabav (sellers pressing) · CE likh rahe 54,300 (+2.6k/15m) · NIFTY/SENSEX saath
> *against 0 · check nahi 0 · (format example only)*

Rules for the line:
- Lines against are always printed ("1 against: PE likh rahe 22,700").
- CAN'T CHECK lines are always counted in the denominator text ("4 of 5 checkable · SENSEX flow patla").
- **Never** a %, a probability or "strong/weak signal".

### 4.6 The three state words (from the new reads only)

| Word | When | Evidence shown |
|---|---|---|
| **Move ban sakta hai** (potential) | Zone ARMED, **or** RANGE within δ/2 of an edge, **or** compression. Plus X5's count. | Start level · confirm condition · kill level · "teeno armed" if so |
| **Move chal raha hai** (running) | Zone TRIGGERED or IN_TRADE, **or** a forming leg in D of ≥ 1δ | Size so far in δ · SYNC state · WHO · "thak raha" (tiring) if the FLOW line has turned against (absorbed at the extreme) |
| **Move ho gaya** (spent) | The last confirmed leg was ≥ 2δ and the counter-leg is still under 1δ (the move happened, and a δ reversal has been confirmed) | "▼ −415 (7.1δ) 12:08→12:33 · pivot confirmed 12:36" |

A word changes only on a named event (leg confirmation, zone state change, pivot, live invalidation), never on a minute's wiggle.

---

## 5. Anticipation, honestly

**What the engine CAN say ahead of a move:**
- The **conditions forming**: her zone armed (in how many indices), a range at its edge, compression, writing building at a wall within reach, and peers coiled the same way.
- **Where it would start:** the zone's ref high or low, or the range edge ± δ.
- **What would confirm it:** the 3-minute trigger close in her machine, and the peers crossing their equivalent levels within MATCH (X2/X3).
- **What would kill it:** the zone stop, the range's other edge, or the failing index taking its own extreme (the divergence ends).
- **How many independent lines agree right now:** a count.

**What it CANNOT say:**
- A probability, a target, or a time to the move.
- That "sync = real move" as a law. Sync is the default state (74 % of minutes). Her observation stays a hypothesis the forward log lets her judge.
- Anything about SENSEX order flow.

**The forward log** (pre-registered; no rate is ever printed):
- **File:** `data/reader/xindex_<day>.jsonl`, append-only, one row per award / switch / release / state-word change / X2 event.
- **Each row holds:** as-of, index, D, the six lines with their reasons, the count, levels (start, confirm, kill), peers' states, the feed state and the reads' `REV`.
- **No outcome is computed or stored by the engine.**
  - What happened next is already in the reader's own leg log (`data/reader/`), joinable by time.
  - The judge's ruling against outcome pairs (§3.9 of the judgement) is respected.
- **Her review:**
  - Before she reads any rows, she writes and signs the pass bar in the same file as the thresholds (the §5e style). For example: what counts as "the move came", measured in δ from the start level before the kill level, and at least 15 awards per direction before any look, otherwise "inconclusive".
  - A 30-session kill clock runs from the first shadow session.
- **Populations stay apart:** never pooled with `trigger_log` (zone), 5c or `calls`.

---

## 6. The one-look face (LIGHT; §3.4 grammar)

- **Colour** means side only: blue for buyers / ▲, vermilion for sellers / ▼, grey for absence or uncertainty. **Black inverse is alarms only** (the feed band).
- Inter, tabular numbers, weights 400/600.
- The LOOK HERE chip is an **ink outline** with the count in tabular numbers. The arrow inside takes the side colour. It does not use the brass accent, because colour is reserved for side.

```
┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
│ NIFTY        22,748.5     │ │ BANKNIFTY    54,386.7     │ │ SENSEX       72,653.4     │
│ ▼ Ban sakta hai           │ │ ▼ Ban sakta hai           │ │ ▼ Chal raha hai           │
│ ● ● ●  teeno saath ▲      │ │ ● ● ●                     │ │ ● ● ●                     │
│ ┌ LOOK HERE ▼ 4/6 ┐       │ │ 2/6                       │ │ 2/4 · flow/WHO patla      │
└───────────────────────────┘ └───────────────────────────┘ └───────────────────────────┘
 LOOK HERE · NIFTY ▼ · 4 of 6: zone u2 armed 22,733 · upar ka dabav dab gaya · NIFTY/SENSEX saath ·
   NIFTY ne high liya, BANKNIFTY ne nahi   | 1 against: PE likh rahe 22,700 (expiry din) | 11:33
 Teeno ne naya high banaya · 12:07                                 (grey note row, arrows coloured)
```

**Per card:**
1. The index, its price and **its own** state word (colour by D).
2. The three sync dots in fixed order N·B·S, filled by leg direction. A hollow grey dot is warm-up or CAN'T CHECK. The odd one is ringed.
3. The count. **Only the holder** shows the LOOK HERE outline.

**Under the cards:**
- the holder's **why line**, including the lines against and the uncheckable ones;
- one **note row** for the latest X2 event, e.g. "BANKNIFTY ne naya high banaya, NIFTY ne nahi", with the level that ends it.

**When no index qualifies:** "LOOK HERE: koi saaf jagah nahi · best NIFTY 2/6" in grey. That keeps the three messages distinct: "we checked and found nothing", "we could not check" and "we are not showing you" (house rule 6).

**Feed band:** a black-inverse "SENSEX index data nahi aa raha · 11:32 se" when DEAD. The affected dots go hollow.

---

## 7. 29 Sep walk-through (what happened, and what the reads would have said)

**Series used:**
- Index spot from the chain (~11 s). Real index candles were not recorded.
- `reader.py` legs on the futures: NIFTY on the Sep exchange candle plus the book; BANKNIFTY on the book.
- Zone: NIFTY and SENSEX from `trigger_log`. **BANKNIFTY had no setup on 29 Sep: WAITING on all 125 served bars on both sides**, verified live by the supervisor (see the correction at the end).
  - My earlier rebuild did apply the 09:25 gate; its first arm was the 09:27 bar. Its bands were wrong. They came from book minutes that start at 09:17, so the 09:15–09:16 opening minutes were missing from VWAP and σ. The 09:27 low then touched a d2 that was too narrow, by only 7.7 pts.
  - Rule kept: **a reconstruction is never a zone source**; only her machine's served state or its log is.
- LOOK HERE lines come from the prototype. **The prototype's BANKNIFTY zone lines on 29 Sep came from that wrong rebuild.** The BANKNIFTY LOOK HERE awards below (09:36, 12:27) are therefore void, and the built replay (`docs/reader/replays/xindex_2026-09-29.txt`) supersedes them.

**Rulers:** NIFTY 27.3; BANKNIFTY 58.8; SENSEX 84.7 (spot, scaled from NIFTY's unit).

### 09:15–09:40: the morning low

**What happened [M]:**
- Spot fell from the open:
  - NIFTY: 22,715.7 → 22,572.7 at 09:38;
  - BANKNIFTY: 54,308.6 → 53,789.9 at 09:40;
  - SENSEX: 72,527.3 → 72,071.1 at 09:39.
- All three lows fell within **2 minutes**.
- Size of the fall: BANKNIFTY **9.6δ**, SENSEX 5.7δ, NIFTY 5.3δ.
- Futures WHO: NIFTY 09:15→09:38 −182 pts, **long liquidation** (OI −3,889 lots, "or roll": the expiring contract), UX −25.5 % [I]. BANKNIFTY 09:23→09:37 −306, long liquidation (OI −860).
- Her zone: **BUY d2 armed at 09:27 in NIFTY and SENSEX**, re-armed 09:30 / 09:33 / 09:36, and triggered at 09:39 in both (logged). **BANKNIFTY: WAITING.** Its only d2 touches were at 09:15–09:24, all before her 09:25 anchor (supervisor, verified).

**What the reads would have said:**
- X1: "Teeno saath ▼", BANKNIFTY the fastest.
- X2-live at 09:38–09:40: "**Teeno ne naya low banaya**" (CONFIRMED down). The broad selling was real.
- X5: "Ban sakta hai ▲ · zone d2 armed · NIFTY/SENSEX armed, BANKNIFTY nahi".
- LOOK HERE at 09:36: *(the prototype's "BANKNIFTY ▲, 3 of 6" is void: its zone line came from the wrong rebuild; see `xindex_2026-09-29.txt`)*.
  - NIFTY had **2 against** at the same bar: sellers still winning, and CE writing at 22,650 (+157k lots/15m, 0DTE).
- The honest reading: at 09:36 nothing said "the low is in". The confirmed new lows said the down move was broad. Her zone and the counts said a turn could start at the ref high.

### 10:11–10:21: the retest

**What happened [M, spot]:**
- NIFTY 22,572.5 (**−0.1** vs 09:38), BANKNIFTY 53,793.9 (**+3.9**), SENSEX 72,093.9 (**+22.7**).
- X2-live at TOL = δ/4:
  - NIFTY EQUAL;
  - BANKNIFTY EQUAL (tolerance 14.7);
  - SENSEX **FAILED by 22.7 against a tolerance of 21.2**: a marginal higher low.

**What the reads would have said:**
- The note: "**Retest par naya low kisi ne nahi banaya** · NIFTY −0.1 · BANKNIFTY +3.9 · SENSEX +22.7".
- The reader called RANGE on both futures: NIFTY 22,579–22,643 at 10:29; BANKNIFTY 53,819–53,991.
- X5: "range kinara", with the NIFTY breakout level 22,643 + δ = **22,670**.
- The 22.7 against 21.2 case shows why TOL is on her sheet.

### 11:06–11:14: the squeeze

**What happened [M]:**
- All three index legs start at **11:06, the same minute**. X3: "saath mein palte · 11:06".
- The reader's breakouts: NIFTY 11:12 (traded 22,684, past 22,643 + δ); BANKNIFTY 11:11.
- Futures WHO:
  - NIFTY +117.7 in 8 minutes, **short covering** (OI −1,028, "or roll"), UX +67 %, λ rank 1 of 5 (least efficient, "absorbed").
  - BANKNIFTY +303.6 (5.2δ), rotation (OI flat), UX thin.
- **WHO disagreed:** covering in NIFTY, no OI conviction in BANKNIFTY.
- Her SELL u2 armed at 11:12 in BANKNIFTY and SENSEX, and at 11:30 in NIFTY.

**What the reads would have said:**
- The prototype held **NIFTY ▲** from 10:54 to 11:12: zone buy in trade · PE likh rahe 22,600 · peers with it. One line was against it: the FLOW line said "move absorbed".
- It released at 11:12, when her buy trade closed (zone back to WAITING). Without the zone, 2 lines were left, under the hold bar.

### 12:05: the top

**What happened [M, spot]:**

| Index | New high | Previous high (11:40) | Gap |
|---|---|---|---|
| NIFTY | 22,752.7 at 12:07 | 22,732.2 | +20.5 = 0.75δ |
| BANKNIFTY | 54,392.7 at 12:08 | 54,295.8 | +96.9 = 1.65δ |
| SENSEX | 72,662.0 at 12:07 | 72,592.9 | +69.1 = 0.82δ |

- X2-live: "**Teeno ne naya high banaya · 12:07**". CONFIRMED, not divergent.
- Zone SELL triggers: SENSEX at 11:36 (its day high came 31 minutes later, 69 pts above its 11:32 high) and NIFTY at 12:18 (both logged). BANKNIFTY had no setup (WAITING).

**What the reads would have said:**
- LOOK HERE: **NIFTY ▼ from 11:33, 4 of 6**: zone u2 armed 22,733 · the push up absorbed · peers armed the same side · NIFTY took its high while BANKNIFTY's confirmed pivot had not.
  - 1 against: PE likh rahe 22,700 (+50k, expiry day).
  - It was held through the top, and turned "chal raha" at the 12:18 trigger.

**Honest note:**
- The top was **confirmed**. Confirmation described a broad up-move, and that minute was the high of the day. Confirmation is not continuation.
- The cross-index read and her zone said different, true things.
- **I cannot say which to weight; only her forward log can.**

### 12:07–12:33: the drop

**What happened [M]:**
- Spot moves: BANKNIFTY −415 (**7.1δ**), SENSEX −409 (4.8δ), NIFTY −124 (4.5δ). **BANKNIFTY led in size.**
- Futures:
  - NIFTY 12:01→12:33 −133.8, long liquidation (OI −1,319) with low efficiency;
  - BANKNIFTY 12:17→12:33 −458, long liquidation (OI −373), UX −15 %.
- The low: NIFTY 12:32, BANKNIFTY 12:33, SENSEX 12:33 (together).

**What the reads would have said:**
- *(Void: the prototype's switch to BANKNIFTY at 12:27 rested on the wrong zone rebuild. BANKNIFTY had no setup. See `xindex_2026-09-29.txt`.)*
- It released at 12:36, after the 12:33 low confirmed: "ho gaya ▼ 7.1δ".

### 12:33–15:15: the afternoon range

**What happened [M, spot]:**
- The afternoon highs, 12:35–13:10 against 13:40–15:14:
  - NIFTY 22,703.6 → 22,705.0 (**+1.4, EQUAL**);
  - BANKNIFTY 54,336.3 → 54,379.8 (+43.4 = 0.74δ, TOOK);
  - SENSEX 72,491.9 → 72,537.2 (+45.3 = 0.53δ, TOOK).
- The reader: NIFTY RANGE 22,631–22,723. BANKNIFTY's upper edge widened at 14:13 and 14:35 (futures engine).

**What the reads would have said:**
- The note: "**BANKNIFTY/SENSEX ne dopahar ka high thoda toda, NIFTY ne nahi (+1.4)**".
- Under the zone-weighted rule, the prototype gave **no LOOK HERE after 12:36**: "koi saaf jagah nahi". A range afternoon with no clean line-up.

### 15:15–15:29: the closing auction

**What happened [M]:**
- Spot frozen on **all three**: NIFTY 22,683.8, BANKNIFTY 54,364.9 and SENSEX 72,480.1, flat 15:15–15:28, then the auction print.
- The futures flushed: NIFTY Sep 15:17→15:22 −91 (Sep-only, per the judgement); BANKNIFTY Sep 15:20→15:22 −210. Both are **expiring** contracts on their own expiry day.

**What the reads would have said:**
- Every cross-index price read: **"cash auction · 15:15 se check nahi"**.
- A futures-based sync would have called the flush "teeno ▼". It was settlement mechanics in two expiring contracts, while SENSEX's Oct future (thin) could not say.
- The expiring labels must carry into X1.

### What 29 Sep could not check

- BANKNIFTY's zone state is now verified as WAITING (supervisor). The 28 Sep BANKNIFTY WAITING is still unverified.
- SENSEX flow and WHO.
- GoCharting for BANKNIFTY and SENSEX.
- NIFTY and BANKNIFTY **Oct** OI (the roll).
- 09:15–09:17 (the book and the chain start at 09:17).
- Everything after 15:15.
- Options walls are 0DTE for NIFTY and BANKNIFTY.

### Findings on the way (outside this read; flagged, not fixed)

| # | Finding | Why it matters |
|---|---|---|
| **F1** | The SENSEX future is too thin for legs or flow (§2.1). | The SENSEX price must come from the index. |
| **F2** | Spot freezes 15:15 → auction on NSE **and BSE** [M, 29 Sep]. | Extends the judgement's must-fix 5 to all three indices. |
| **F3 (corrected)** | `trigger_log` has no BANKNIFTY rows on 28 or 29 Sep. **29 Sep is not a bug**: every BANKNIFTY band touch was before the 09:25 anchor, so WAITING on both sides is her rule working (supervisor, verified on the served bars). My rebuild's "arms" came from bands missing the 09:15–09:16 minutes. **28 Sep is still unverified.** | A reconstruction is never a zone source. The replay reads 28 Sep BANKNIFTY's zone as CAN'T CHECK until that check is done. |
| **F4** | `band_rotation.OPERATOR_STOP_PTS = 20.0` applies the **same 20 points** to all three indices: 0.73δ on NIFTY, but 0.34δ on BANKNIFTY and about 0.24δ on SENSEX. In the replay, BANKNIFTY's u2 sell stopped out and re-armed after 12:09. | Her signed rule stays untouched. It goes on her sheet as a question, not a change. |
| **F5** | The backtest candle files mix contracts with no stamp. | Not usable for OI or roll-sensitive work. |

---

## 8. Build steps (on top of `reader.py`; shadow first)

| # | Step | Size | Risk | Ships as |
|---|---|---|---|---|
| X0 | **Read-only checks:** the index candle instrument keys and REST 1-minute availability for all three; the SENSEX ruler source in the current `reader.py`; the 28 Sep BANKNIFTY zone (29 Sep is verified WAITING). | S | Low | Notes |
| X1 | **Index engines:** `reader.Engine` on the index 1-minute candles, per index (no new leg code), with anytime start from REST. The futures engines are as built. | S | Low | SHADOW |
| X2 | **`xindex.py`**, pure: `sync()`, `extremes_live()`, `extremes_confirmed()`, `lead()`, `walls()`, `potential()`, `lines()` and `look_here(prev_state)` with hysteresis. Append-only `data/reader/xindex_<day>.jsonl`. **Tests:** byte-equal replays; restarts at 10:00, 12:00 and 14:00; the churn counters; the 15:15 freeze; a hole in one index; the SENSEX "patla" path. | M | Low–med | SHADOW |
| X3 | **`/api/xindex`**, GET, as-of stamped, `coverage` per line. | S | Low | SHADOW |
| X4 | **Shadow for 10 sessions**, including the 27 Oct NSE monthly expiry and the 29 Oct SENSEX monthly expiry, beside the legacy LOOK HERE. Measure the churn bars. Run a 60-read misdescription audit per day (7-final §4). | — | — | Logs |
| X5 | **Face, on her decision:** the three cards + why line + note row, behind a shadow toggle. Then the `data.ts` score path is replaced **on her signature**. The legacy `engine.py` words leave the cards at the same time. | S–M | Med (her main screen) | Live on her word |

**Her threshold sheet for this read** (one page; sha256-anchored with the reader's sheet):

| # | Name | Value (h) | Reason / measured support |
|---|---|---|---|
| 1 | K (index engines) | 3 | Same ruler as `reader.py` |
| 2 | MATCH | 10 min | Catches 81 % of NIFTY–BANKNIFTY and 94 % of NIFTY–SENSEX matched turns (§2.4) |
| 3 | TIE | 1 min | The canonical minute; 61 % / 81 % of matched turns fall within it |
| 4 | TOL | δ/4 | The EQUAL band. 29 Sep's SENSEX retest (+22.7 against 21.2) sits right on it. |
| 5 | X2 from | 09:30 | The first-minute session extremes are trivially new; beside her 09:25 anchor |
| 6 | REACH | 1.5δ | A wall "within reach" of the next leg |
| 7 | WRITE window / noise / DOM | 15 min / 3σ robust / 1.5× | Chain cadence is ~11 s; one side must dominate to vote |
| 8 | Award | zone + 2, or 4; and for ≥ against + 2 | Her setup is primary. At 4 without the zone, this is rare (2–9 index-bars a day). |
| 9 | Hold / switch / cooldown | award − 1 / +2 after 2 bars / 1 bar | The prototype: 2–15 changes a day, against 6–26 raw |
| 10 | SPENT | last leg ≥ 2δ and counter-leg < 1δ | "Ho gaya" only on confirmed facts |
| 11 | Churn bars | ≤ 10 awards, ≤ 16 changes, 0 flips under 6 min, ≤ 12 word changes per index | Pre-registered, measured in shadow |
| 12 | Feed SLOW / DEAD | measured first | The judgement's must-fix 11: no timer-only rules |
| — | Her F4 stop question | 20 pts on all three? | Hers to answer. Unchanged here. |

No lot count appears anywhere on this sheet.

---

## 9. Self-check

**Rubric items that apply** (1-research.md; the judgement's amendments):

| Item | How this design meets it | Verdict |
|---|---|---|
| R1 legs | Reuses `reader.Engine`. SENSEX legs are cut on the index. | PASS |
| R3 Δ × OI × price | NIFTY and BANKNIFTY per leg. **SENSEX CAN'T CHECK.** Roll window "or roll". | PARTIAL for good (SENSEX) |
| R4 expiry and roll | The expiring label carries into SYNC and WHO. The 15:20 flush is named as settlement. The continuing contract comes after P2a/P2b. | PARTIAL until P2 exists |
| R6 divergence at structure only | X2 fires only at swing or session extremes, never bar by bar | PASS |
| R11 options confirmation | Walls with writing within reach. One expiry, 17 strikes, 0DTE labelled. | PARTIAL for good |
| R13 self-calibration | δ per index, TOL and REACH in δ, no lot counts. DOM and noise are (h). | PASS |
| R14 persistence | Evaluated on 3-minute closes; hysteresis; churn bars; the word changes only on events | PASS by design (measured in shadow) |
| R15 sequence over bars | Lines are leg-, zone- and extreme-level reads, not single bars | PASS |
| R16 two tapes | BANKNIFTY and SENSEX are always one tape (UX / none) | PARTIAL for good |
| R17 day story | Adds a cross-index clause per leg ("BANKNIFTY sabse tez; teeno ne high liya 12:07") | PASS |
| R18 position frame | LOOK HERE is not position-relative. Her FLOW row stays the reader's (R-e). | Not claimed |

**Gates:**

| Gate | How this design meets it |
|---|---|
| H1 no edge claims | A count, not a %. No outcome fields in the log. The review is hers, under a pre-signed bar. |
| H2 observed vs inferred | Every line is tagged: sync, extremes, lead and OI are [M]; flow, WHO and "writing" are [I]. |
| H3 holes visible | Hollow dots; "N of 6 checkable"; the 15:15 freeze; the feed band. |
| H4 warm-up | The index engines need a prior unit (else the first 15 minutes, as in the reader); X2 from 09:30; walls after 15 minutes of chain; LOOK HERE from 09:27. |
| H5 as-of | Pure functions of data stamped at or before the as-of. Confirmed pivots are frozen. X2-live and X2-confirmed are kept apart, so the lag is explicit. |
| H6 contract identity | Index series are contract-free. Futures legs carry the contract and "expiring". The SENSEX future is stamped (Oct on 29 Sep). The chain expiry is shown per index. |
| H7 "no read" | "Koi saaf jagah nahi" is a first-class output. |
| H8 anytime start | Index candles, zone and chain are backfillable by REST. Flow inside a restart gap = CAN'T CHECK (the book cannot be backfilled), as in the reader. |

**What our data can never support:**
- The true aggressor for any index (inferred sides only).
- **SENSEX order flow** (the future trades 1–3k lots a day; the BSE options have no side).
- A GoCharting footprint for BANKNIFTY or SENSEX.
- Constituent breadth (A/D), which is not recorded.
- Sub-minute lead–lag (1-minute canonical series; 11-second chain).
- Intraday participant OI.
- Walls across expiries (one expiry per chain).
- Ordinary-day futures OI agreement across indices until contract-stamped captures exist.
- **Any probability that a move comes.**

---

## Sources

- [S1] StockCharts ChartSchool, *Dow Theory*: https://chartschool.stockcharts.com/table-of-contents/market-analysis/dow-theory
- [S2] Dukascopy, *Dow Theory*: https://www.dukascopy.com/swiss/english/marketwatch/articles/dow-theory/
- [S3] Brown, Goetzmann & Kumar (1998), *The Dow Theory: William Peter Hamilton's Track Record Reconsidered*, J. Finance 53(4): https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00054 (SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=58690)
- [S4] TradingFinder, *ICT SMT divergence*: https://tradingfinder.com/education/forex/ict-smt-divergence/
- [S5] MetroTrade, *SMT trading futures*: https://www.metrotrade.com/smt-trading-futures/
- [S6b] EasyLanguage Mastery (Ruggiero), *Intermarket divergence*: https://easylanguagemastery.com/building-strategies/intermarket-divergence-robust-method-signal-generation/
- [S7] StockCharts, *Advance-Decline Line*: https://chartschool.stockcharts.com/table-of-contents/market-indicators/advance-decline-line
- [S8] Huth & Abergel, *High Frequency Lead/lag Relationships: Empirical facts*: https://arxiv.org/abs/1111.7103
- [S9] Khan et al. (2022), *Intraday Price Discovery between Spot and Futures Markets of NIFTY 50*: https://onlinelibrary.wiley.com/doi/10.1155/2022/2164974 (abstract: https://doaj.org/article/bae21c7d0f314b7e8bcf3488c09fb91f)
- [S10] *Lead-Lag Relationship between the Spot and Futures in the Indian Equity Market* (not re-read): https://www.researchgate.net/publication/375121521
- [S11] Stable Investor, *Portfolio overlap: Nifty vs Sensex* (2022): https://stableinvestor.com/2022/04/portfolio-overlap-nifty-vs-sensex.html
- [S12a] smart-investing.in, NIFTY weights (29 Sep 2026): https://www.smart-investing.in/indices-bse-nse.php?index=NIFTY
- [S12b] smart-investing.in, BANKNIFTY weights (29 Sep 2026): https://www.smart-investing.in/indices-bse-nse.php?index=BANKNIFTY
- [S13] 5paisa, *SEBI expands Bank Nifty to 14 stocks*: https://www.5paisa.com/news/sebi-expands-bank-nifty-to-14-stocks-caps-top-stock-weight-at-20
- [S14] Zee Business, *SEBI raises Bank Nifty constituents*: https://www.zeebiz.com/market-news/news-sebi-raises-bank-nifty-constituents-limits-top-stock-weight-to-enhance-index-stability-382222
- [S15] niftypapertrade, *NIFTY vs BANKNIFTY*: https://niftypapertrade.in/learn/nifty-vs-banknifty
- [S16] Marketcalls, *Nifty vs Bank Nifty ratio charts*: https://www.marketcalls.in/trading-lessons/nifty-vs-bank-nifty-ratio-charts.html
- [S17] Zerodha bulletin, *Revision in expiry day*: https://zerodha.com/marketintel/bulletin/417370/revision-in-expiry-day-of-index-and-stock-derivatives-contracts
- [S18] Zee Business, *NSE Tuesday, BSE Thursday*: https://www.zeebiz.com/market-news/news-sebi-approves-nse-expiry-day-change-to-tuesday-and-bse-expiry-day-shifted-to-thursday-370127
- [S19] Multibagg (summarising NSE's RHP), *NSE options premium share 68.48 %*: https://www.multibagg.ai/market-pulse/articles/nse-options-premium-share-falls-rhp-cmu8gzs5m0071y6pi1worz0aj

---

## Supervisor correction (2026-09-29, 23:xx): "BANKNIFTY's zone setups missing on 28 and 29 Sep"

- **29 Sep: not a bug.** The live machine (`live.py:1093`, `band_rotation.run_states`, 3m, band d2/u2, stop 20) was checked against the served bars (`/api/data?idx=BANKNIFTY&interval=3`, 125 bars, 09:15–15:27):
  - BANKNIFTY's low reached d2 only at 09:15, 09:18, 09:21 and 09:24, and its high reached u2 only at 09:15;
  - every one of those touches is before the 09:25 zone anchor, her standing choice;
  - nothing after 09:24 touched either band;
  - so WAITING on all 125 bars on both sides is the rule working.

  This design's rebuild that "arms it on both sides" must have skipped the 09:25 gate; re-check it before shadow.
- **28 Sep: still unverified.** Only today's session is served live. A replay needs the day's bands. The same pre-09:25 explanation is plausible but not proven; that check is still owed.
