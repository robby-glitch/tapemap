# Zone alone — C1 / C2 / C3 replayed, 2026-10-06

READ-ONLY replay. In-sample hindsight throughout: today's trade is the case C1–C3 were written from, and every
"winner" / "loser" read below knows the rest of the day. Counts, never rates. [M] measured from the recorded rows,
[I] inferred.

**How.** `fold.py` as it is (rev 6; its uncommitted diff is the display-only index basis), fed the way `fold_live`
feeds it: book, chain, `vpin_fast.jsonl`, tape, and the 5 prior sessions the live engine pooled. C1, C2, C3 are
subclasses in a scratch script (`scratchpad/zone_alone/zone_alone.py`): no tracked file edited, no server touched,
no POST. Check: the replay of NIFTY-22650PE-long-100321 reproduces all 54 logged live events word for word (time,
text, headline, clause, G, chips) and the live FOLD at 11:45:33 at 31.05 [M]. C2 is read as the two strikes' OI
summed (her strike + the next strike her way, her option's type; the other type for a sale) against the last OI at
or before entry. C3 reads the chips she sees (after CONFIRM) on every fill and chain row; "tiring" = the engine's
stall clock; "W building" = W's watch state. prem = her strike's chain LTP, the last snapshot at or before the time
[M]. Today's data ends 11:47:20.

## Findings

1. **Today C3 FOLDs her 22650 PE at 11:04:56 at 45.3** [M] (entry 55: −9.7); C1+C2+C3 at 10:44:36 at 44.5 (−10.5); the current engine (and C1 alone, C2 alone) at 11:45:33 "22770 accepted" at 31.05 (−23.95); 29.2 at the 11:47 cut [M]. After the 10:44 fold the PE was back to 55.7 at 10:58 [M] before failing — that fold came on a pullback that returned to entry.
2. Why then [M]: FLOW AGAINST from 10:43; the OI chip went WITH → QUIET only at 11:04:56 (W raw "stopped" from ~10:48, the chip waits 2 bucket closes). With C1 the 22650 CE bleed (200.7L → 178.5L, −11.1 %, z 1.7, 12 updates) is an event at 10:44:36 and OI reads AGAINST.
3. **C1 alone and C2 alone never move a first FOLD** — today or on any of the 50 past trades [M]; they only turn the OI chip AGAINST (today 10:44:36 / 10:47:37), because the fold rule reads an OI event only once G is accepted. On the 09-24 10:19 SENSEX winner they show OI AGAINST at 11:01 / 11:12, in the pullback before the run [M].
4. **Winners C3 cuts short** [I, hindsight]: 09-22 10:32 NIFTY 23550PE (C3 11:39 @ 184.3 v current 14:12 @ 238.55; 270.9 at 14:00) · 09-24 10:19 SENSEX 74200PE (C3 11:18 @ 171.25, C1+C2+C3 11:01 @ 162.7, v current 13:22 @ 264.15; 640.8 at 14:24) · 09-28 NIFTY 23000PE, her held winner (C3 11:52 @ 165.5 v no current FOLD; 205.35 at 15:00) · 09-23 09:18 and 09:47 NIFTY 23450CE (C3 09:58 @ 93.65 v current 14:45 @ 108.5; 134.9 at 12:20).
5. Those cuts are not artifacts: OI and FLOW really were not WITH (09-23, 09-28: OI AGAINST, a z ≥ 3 event in the current engine; 09-24: FLOW AGAINST, OI QUIET; 09-22: FLOW WITH but tiring 29 min) and the trades ran anyway [M].
6. **Losers C3 folds earlier at a better premium than current** [I]: 09-22 09:42 23300CE (+34.75 pts), 09-22 13:48 23500PE (+9.85; C1+C2+C3 +52.0), 09-23 11:07 23450CE (+14.9), 09-25 23100CE (+8.25), 09-30 22750CE (+14.45), 10-01 SENSEX 72400CE 09:30 (+96.45), 10-05 22600CE (+36.55), 10-05 22550PE (+37.6), 10-06 short 22600CE (+28.5); earlier and better also on 4 current winners (09-23 10:00/10:19/10:33 23450CE, 09-29 22800PE).
7. C3 defects seen [M]: it counts CAN'T CHECK as "not behind" — 10-05 short 22650PE folded 13:51:38 because a 38 s order-flow hole reset W's watch to "no wall read yet". No C3 FOLD came sooner than 10 min after a mark (W starts "building").
8. C1 inside C1+C2+C3 moves 5 folds earlier than C3 alone — better on 1 (09-22 13:48: 176.1 v 133.95), worse on 4 (09-24 10:19: 162.7 v 171.25; 10-01 SENSEX CE 09:30: 156.5 v 186.55; 10-06 short 22600CE: 95.25 v 85.15; today: 44.5 v 45.3) — and adds one (10-06 short 22650PE 10:13 @ 64.1; that PE then fell to 29.6; she held that sale 8 s) [M].
9. Could not check: 09-21 NIFTY 23300CE (no book or chain file on disk). Design trades A1–A6, H1 are not hers and were not replayed.

## 1. Today — long NIFTY 22650 PE from 10:03:21 at 55.0 (entry fut 22740)

Each row is the state at the start of the minute; a row is printed when a word, a chip, G or W's state changes
(the full minute table is `scratchpad/zone_alone/today_minutes.csv`). Chips Z/F/O/V = zone / flow / OI / VPIN as she
sees them [I]; G = 22788 and W = 22700 CE until 10:27:58, then G = 22770 and W = 22650 CE [M].

| min | fut [M] | PE prem [M] | current: word · Z/F/O/V | tiring min | W (state, OI) [M] | C1: OI → word | C2: OI → word | C3 word | C1+C2+C3: OI → word |
|---|---|---|---|---|---|---|---|---|---|
| 10:04 | 22740 | 60.15 | HOLD · –/AGAINST/WITH/AGAINST | 0 | building, 229.4L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:05 | 22737 | 58.7 | HOLD · WITH/AGAINST/WITH/AGAINST | 0 | building, 225.7L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:07 | 22727 | 62.2 | HOLD · QUIET/AGAINST/WITH/AGAINST | 4 | building, 227.7L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:14 | 22719 | 62.7 | HOLD · QUIET/QUIET/WITH/AGAINST | 11 | building, 243.2L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:18 | 22737 | 55.8 | HOLD · WITH/QUIET/WITH/QUIET | 15 | building, 252.3L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:23 | 22725 | 59.35 | HOLD · QUIET/AGAINST/WITH/QUIET | 20 | building, 246.0L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:29 | 22724 | 58.75 | HOLD · QUIET/WITH/WITH/QUIET | 26 | building, 191.3L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:39 | 22750 | 48.25 | HOLD · WITH/WITH/WITH/QUIET | 0 | building, 184.5L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:44 | 22758 | 44.65 | HOLD · WITH/AGAINST/WITH/QUIET | 0 | building, 181.8L | WITH → HOLD | WITH → HOLD | HOLD | WITH → HOLD |
| 10:45 | 22757 | 44.35 | HOLD · WITH/AGAINST/WITH/QUIET | 0 | building, 178.5L | AGAINST → HOLD | WITH → HOLD | HOLD | AGAINST → FOLD |
| 10:48 | 22748 | 48.9 | HOLD · WITH/AGAINST/WITH/QUIET | 0 | stopped, 175.5L | AGAINST → HOLD | AGAINST → HOLD | HOLD | AGAINST → FOLD |
| 11:05 | 22756 | 45.3 | HOLD · WITH/AGAINST/QUIET/QUIET | 21 | stopped, 192.6L | AGAINST → HOLD | AGAINST → HOLD | FOLD | AGAINST → FOLD |
| 11:06 | 22778 | 37.75 | HOLD · QUIET/AGAINST/QUIET/QUIET | 22 | stopped, 180.0L | AGAINST → HOLD | AGAINST → HOLD | FOLD | AGAINST → FOLD |
| 11:14 | 22754 | 41.5 | HOLD · WITH/AGAINST/QUIET/QUIET | 30 | stopped, 172.0L | AGAINST → HOLD | AGAINST → HOLD | FOLD | AGAINST → FOLD |
| 11:18 | 22758 | 42.25 | HOLD · WITH/WITH/QUIET/QUIET | 34 | stopped, 172.0L | AGAINST → HOLD | AGAINST → HOLD | FOLD | AGAINST → FOLD |
| 11:46 | 22789 | 29.75 | FOLD · QUIET/AGAINST/QUIET/QUIET | 0 | stopped, 174.1L | AGAINST → FOLD | AGAINST → FOLD | FOLD | AGAINST → FOLD |
| 11:47:20 cut | 22789 | 29.2 | FOLD · QUIET/AGAINST/QUIET/AGAINST | 4 | stopped, 161.6L | AGAINST → FOLD | AGAINST → FOLD | FOLD | AGAINST → FOLD |

**First FOLD under each variant** (prem [M]; after = to the 11:47:20 cut)

| variant | first FOLD | why | prem at FOLD [M] | vs entry 55 | low after (time) [M] | high after (time) [M] | prem at 11:47 [M] |
|---|---|---|---|---|---|---|---|
| current | 11:45:33 | accept | 31.05 | -23.95 | 28.5 (11:47) | 30.95 (11:46) | 29.2 |
| C1 | 11:45:33 | accept | 31.05 | -23.95 | 28.5 (11:47) | 30.95 (11:46) | 29.2 |
| C2 | 11:45:33 | accept | 31.05 | -23.95 | 28.5 (11:47) | 30.95 (11:46) | 29.2 |
| C3 | 11:04:56 | zone only (Z WITH, F AGAINST, O QUIET, tiring 21, W stopped) | 45.3 | -9.70 | 28.5 (11:47) | 45.6 (11:32) | 29.2 |
| C1+C2+C3 | 10:44:36 | zone only (Z WITH, F AGAINST, O AGAINST, tiring 0, W off) | 44.5 | -10.50 | 28.5 (11:47) | 55.7 (10:58) | 29.2 |

## 2. Her earlier recorded trades

`data/day_state` hold trades (marked or imported) and the tradebook rows in `docs/hold/opus/scratch/trades.json`
("mine"). The engine reads on past her exit, so a FOLD after her exit is what holding would have heard. Her exit
price is [M] from the tradebook and [I] (the chain LTP at her exit) for marked trades. "read" compares each
variant's FOLD premium with the current engine's FOLD premium (or with the last premium when current never
folds): WINNER CUT = earlier and worse while holding paid; LOSER FOLDED EARLIER = earlier and better on a trade
current closes at a loss [I]. The 10-06 rows end at the 11:47 cut.

| day | trade | in @ p0 [M] | her out @ prem | current FOLD @ prem [M] | C1 / C2 alone | C3 FOLD @ prem [M] | C1+C2+C3 FOLD @ prem [M] | after the earliest FOLD: best (time) · 15:30 or cut [M] | OI chip AGAINST first: cur · C1 · C2 | read [I] |
|---|---|---|---|---|---|---|---|---|---|---|
| 09-21 | long NIFTY 23300CE | 14:00 @ 179.6 | 14:10 @ 168.0 [M] | could not check: no book or chain file for NIFTY 2026-09-21 | | | | | | |
| 09-22 | long NIFTY 23300CE | 09:42 @ 166.4 | 10:20 @ 159.15 [M] | 10:45 accept @ 100.8 | = current | 10:31 zone only @ 135.55 | 10:31 zone only @ 135.55 | 138.65 (10:31) · 28.85 | 10:31 · 10:31 · 10:31 | C3: LOSER FOLDED EARLIER (+34.75 pts v current); C1+2+3: LOSER FOLDED EARLIER (+34.75 pts v current) |
| 09-22 | long NIFTY 23550PE | 10:32 @ 134.8 | 10:38 @ 144.05 [M] | 14:12 expiry @ 238.55 | = current | 11:39 zone only @ 184.3 | 11:39 zone only @ 184.3 | 270.9 (14:00) · 220.7 | 12:46 · 12:46 · 12:46 | C3: WINNER CUT (-54.25 pts v current); C1+2+3: WINNER CUT (-54.25 pts v current) |
| 09-22 | long NIFTY 23550PE | 10:42 @ 174.75 | 10:42 @ 186.95 [M] | 11:28 accept @ 164.3 | = current | 11:28 accept @ 164.3 | 11:28 accept @ 164.3 | 270.9 (14:00) · 220.7 | – · – · – | same as current |
| 09-22 | long NIFTY 23550PE | 10:43 @ 175.05 | 10:43 @ 171.6 [M] | 11:28 accept @ 164.3 | = current | 11:28 accept @ 164.3 | 11:28 accept @ 164.3 | 270.9 (14:00) · 220.7 | – · – · – | same as current |
| 09-22 | long NIFTY 23550PE | 10:44 @ 171.5 | 10:44 @ 174.0 [M] | 11:28 accept @ 164.3 | = current | 11:28 accept @ 164.3 | 11:28 accept @ 164.3 | 270.9 (14:00) · 220.7 | – · – · – | same as current |
| 09-22 | long NIFTY 23500PE | 10:52 @ 146.15 | 10:55 @ 133.0 [M] | 11:28 accept @ 120.05 | = current | 11:28 accept @ 120.05 | 11:28 accept @ 120.05 | 222.5 (14:00) · 170.6 | – · – · – | same as current |
| 09-22 | long NIFTY 23500PE | 13:48 @ 181.5 | 13:54 @ 203.2 [M] | 14:19 accept @ 124.1 | = current | 14:14 zone only @ 133.95 | 14:13 zone only @ 176.1 | 191.35 (15:20) · 170.6 | 14:14 · 14:13 · 14:14 | C3: LOSER FOLDED EARLIER (+9.85 pts v current); C1+2+3: LOSER FOLDED EARLIER (+52.0 pts v current) |
| 09-23 | long NIFTY 23450CE | 09:18 @ 100.0 | 09:25 @ 99.0 [M] | 14:45 flow_oi @ 108.5 | = current | 09:58 zone only @ 93.65 | 09:58 zone only @ 93.65 | 134.9 (12:20) · 107.0 | 09:57 · 09:57 · 09:57 | C3: WINNER CUT (-14.85 pts v current); C1+2+3: WINNER CUT (-14.85 pts v current) |
| 09-23 | long NIFTY 23450CE | 09:47 @ 99.4 | 09:49 @ 91.75 [M] | 14:45 flow_oi @ 108.5 | = current | 09:58 zone only @ 93.65 | 09:58 zone only @ 93.65 | 134.9 (12:20) · 107.0 | 09:57 · 09:57 · 09:57 | C3: WINNER CUT (-14.85 pts v current); C1+2+3: WINNER CUT (-14.85 pts v current) |
| 09-23 | long NIFTY 23400PE | 09:49 @ 125.0 | 09:53 @ 124.2 [M] | 10:19 accept @ 108.1 | = current | 10:19 accept @ 108.1 | 10:19 accept @ 108.1 | 110.0 (10:25) · 81.8 | 10:19 · 10:19 · 10:19 | same as current |
| 09-23 | long NIFTY 23450CE | 10:00 @ 98.6 | 10:09 @ 90.8 [M] | 14:45 flow_oi @ 108.5 | = current | 11:33 zone only @ 118.9 | 11:33 zone only @ 118.9 | 134.9 (12:20) · 107.0 | 13:36 · 13:36 · 13:36 | C3: earlier, better (+10.4 pts v current); C1+2+3: earlier, better (+10.4 pts v current) |
| 09-23 | long NIFTY 23450CE | 10:19 @ 101.85 | 10:31 @ 105.0 [M] | 14:45 flow_oi @ 108.5 | = current | 13:09 zone only @ 123.4 | 13:09 zone only @ 123.4 | 129.95 (14:29) · 107.0 | 13:36 · 13:36 · 13:36 | C3: earlier, better (+14.9 pts v current); C1+2+3: earlier, better (+14.9 pts v current) |
| 09-23 | long NIFTY 23450CE | 10:33 @ 106.45 | 11:04 @ 106.0 [M] | 14:45 flow_oi @ 108.5 | = current | 13:09 zone only @ 123.4 | 13:09 zone only @ 123.4 | 129.95 (14:29) · 107.0 | 13:36 · 13:36 · 13:36 | C3: earlier, better (+14.9 pts v current); C1+2+3: earlier, better (+14.9 pts v current) |
| 09-23 | long NIFTY 23450CE | 11:07 @ 115.65 | 11:16 @ 110.0 [M] | 14:45 flow_oi @ 108.5 | = current | 13:09 zone only @ 123.4 | 13:09 zone only @ 123.4 | 129.95 (14:29) · 107.0 | 13:36 · 13:36 · 13:36 | C3: LOSER FOLDED EARLIER (+14.9 pts v current); C1+2+3: LOSER FOLDED EARLIER (+14.9 pts v current) |
| 09-23 | long SENSEX 74900CE | 11:32 @ 215.25 | 11:40 @ 200.0 [M] | 11:43 accept @ 206.05 | = current | 11:43 accept @ 206.05 | 11:43 accept @ 206.05 | 265.8 (12:19) · 166.15 | – · – · – | same as current |
| 09-24 | long SENSEX 74200PE | 09:42 @ 179.25 | 09:47 @ 203.0 [M] | 10:56 backstop @ 161.7 | = current | 10:56 backstop @ 161.7 | 10:56 backstop @ 161.7 | 640.8 (14:24) · 620.05 | – · – · – | same as current |
| 09-24 | long SENSEX 74200PE | 10:19 @ 222.6 | 10:23 @ 234.0 [M] | 13:22 held @ 264.15 | = current | 11:18 zone only @ 171.25 | 11:01 zone only @ 162.7 | 640.8 (14:24) · 620.05 | – · 11:01 · 11:12 | C3: WINNER CUT (-92.9 pts v current); C1+2+3: WINNER CUT (-101.45 pts v current) |
| 09-24 | long SENSEX 74100PE | 12:32 @ 202.35 | 12:33 @ 216.0 [M] | 13:22 held @ 201.2 | = current | 13:22 held @ 201.2 | 13:22 held @ 201.2 | 547.05 (14:24) · 519.85 | – · – · – | same as current |
| 09-24 | long SENSEX 74000PE | 12:35 @ 179.8 | 12:38 @ 161.0 [M] | 13:06 backstop @ 144.85 | = current | 13:06 backstop @ 144.85 | 13:06 backstop @ 144.85 | 462.45 (14:24) · 418.25 | – · – · – | same as current |
| 09-24 | long SENSEX 74000PE | 12:44 @ 167.95 | 12:50 @ 160.0 [M] | 13:06 backstop @ 144.85 | = current | 13:06 backstop @ 144.85 | 13:06 backstop @ 144.85 | 462.45 (14:24) · 418.25 | – · – · – | same as current |
| 09-24 | long SENSEX 74000PE | 13:26 @ 184.2 | 13:27 @ 220.0 [M] | 13:50 expiry @ 330.0 | = current | 13:50 expiry @ 330.0 | 13:50 expiry @ 330.0 | 462.45 (14:24) · 418.25 | – · – · – | same as current |
| 09-24 | long SENSEX 73900PE | 13:41 @ 190.03 | 13:43 @ 192.98 [M] | 14:02 expiry @ 314.7 | = current | 14:02 expiry @ 314.7 | 14:02 expiry @ 314.7 | 380.9 (14:24) · 318.75 | – · – · – | same as current |
| 09-24 | long SENSEX 73900PE | 13:43 @ 206.55 | 13:43 @ 207.3 [M] | 13:50 expiry @ 263.85 | = current | 13:50 expiry @ 263.85 | 13:50 expiry @ 263.85 | 380.9 (14:24) · 318.75 | – · – · – | same as current |
| 09-24 | long SENSEX 73900PE | 13:44 @ 230.45 | 13:44 @ 237.6 [M] | 14:02 expiry @ 314.7 | = current | 14:02 expiry @ 314.7 | 14:02 expiry @ 314.7 | 380.9 (14:24) · 318.75 | – · – · – | same as current |
| 09-24 | long SENSEX 73800PE | 13:45 @ 211.05 | 13:46 @ 217.05 [M] | 14:02 expiry @ 247.8 | = current | 14:02 expiry @ 247.8 | 14:02 expiry @ 247.8 | 305.1 (14:24) · 219.2 | – · – · – | same as current |
| 09-24 | long SENSEX 73800PE | 13:54 @ 252.15 | 13:55 @ 240.0 [M] | 14:04 backstop @ 229.2 | = current | 14:04 backstop @ 229.2 | 14:04 backstop @ 229.2 | 305.1 (14:24) · 219.2 | – · – · – | same as current |
| 09-24 | long SENSEX 73800PE | 13:57 @ 267.4 | 13:58 @ 297.0 [M] | 14:04 backstop @ 229.2 | = current | 14:04 backstop @ 229.2 | 14:04 backstop @ 229.2 | 305.1 (14:24) · 219.2 | – · – · – | same as current |
| 09-24 | long SENSEX 73800PE | 14:23 @ 287.45 | 14:23 @ 294.8 [M] | 14:35 accept @ 226.85 | = current | 14:35 accept @ 226.85 | 14:35 accept @ 226.85 | 243.95 (15:20) · 219.2 | – · – · – | same as current |
| 09-25 | long NIFTY 23100CE | 12:01 @ 113.55 | 13:23 @ 92.35 [I] | 12:47 accept @ 101.7 | = current | 12:07 zone only @ 109.95 | 12:07 zone only @ 109.95 | 181.05 (14:06) · 146.95 | 12:07 · 12:07 · 12:07 | C3: LOSER FOLDED EARLIER (+8.25 pts v current); C1+2+3: LOSER FOLDED EARLIER (+8.25 pts v current) |
| 09-25 | long NIFTY 23200PE | 12:05 @ 155.4 | 13:23 @ 177.3 [I] | 14:01 flow_oi @ 128.45 | = current | 14:01 flow_oi @ 128.45 | 14:01 flow_oi @ 128.45 | 132.0 (14:01) · 99.05 | 14:01 · 14:01 · 14:01 | same as current |
| 09-28 | long NIFTY 23000PE | 09:30 @ 120.4 | 10:20 @ 156.65 [I] | none | = current | 11:52 zone only @ 165.5 | 11:52 zone only @ 165.5 | 236.95 (14:38) · 206.05 | 11:52 · 11:52 · 11:52 | C3: WINNER CUT (-40.55 pts v current at 15:30); C1+2+3: WINNER CUT (-40.55 pts v current at 15:30) |
| 09-29 | long NIFTY 22800PE | 09:18 @ 113.95 | 09:35 @ 189.3 [I] | 11:11 flow_oi @ 142.8 | = current | 11:10 zone only @ 153.15 | 11:10 zone only @ 153.15 | 186.1 (15:21) · 83.95 | 11:10 · 11:10 · 11:10 | C3: earlier, better (+10.35 pts v current); C1+2+3: earlier, better (+10.35 pts v current) |
| 09-30 | long NIFTY 22750CE | 10:10 @ 164.7 | 11:16 @ 125.95 [I] | 11:16 accept @ 127.55 | = current | 10:35 zone only @ 142.0 | 10:35 zone only @ 142.0 | 202.3 (12:48) · 93.45 | 10:35 · 10:35 · 10:35 | C3: LOSER FOLDED EARLIER (+14.45 pts v current); C1+2+3: LOSER FOLDED EARLIER (+14.45 pts v current) |
| 10-01 | long NIFTY 22600PE | 09:21 @ 142.4 | 09:23 @ 155.5 [I] | 10:02 accept @ 120.1 | = current | 10:02 accept @ 120.1 | 10:02 accept @ 120.1 | 384.95 (14:05) · 200.0 | – · – · – | same as current |
| 10-01 | long NIFTY 22600PE | 09:26 @ 149.75 | 09:26 @ 152.25 [I] | 10:02 accept @ 117.3 | = current | 10:02 accept @ 117.3 | 10:02 accept @ 117.3 | 384.95 (14:05) · 200.0 | – · – · – | same as current |
| 10-01 | long SENSEX 72400CE | 09:30 @ 209.4 | 09:31 @ 218.5 [I] | 12:10 flow_oi @ 90.1 | = current | 11:42 zone only @ 186.55 | 11:39 zone only @ 156.5 | 187.4 (11:44) · 0.1 | 12:09 · 12:09 · 11:39 | C3: LOSER FOLDED EARLIER (+96.45 pts v current); C1+2+3: LOSER FOLDED EARLIER (+66.4 pts v current) |
| 10-01 | long SENSEX 72400CE | 10:00 @ 237.25 | 10:01 @ 266.8 [I] | 11:26 accept @ 143.6 | = current | 11:26 accept @ 143.6 | 11:26 accept @ 143.6 | 187.4 (11:44) · 0.1 | – · – · – | same as current |
| 10-01 | long SENSEX 72400CE | 10:02 @ 276.05 | 10:06 @ 269.45 [I] | 11:26 accept @ 143.6 | = current | 11:26 accept @ 143.6 | 11:26 accept @ 143.6 | 187.4 (11:44) · 0.1 | – · – · – | same as current |
| 10-01 | long SENSEX 72400PE | 12:06 @ 223.97 | 12:08 @ 235.65 [I] | 13:05 held @ 668.3 | = current | 13:05 held @ 668.3 | 13:05 held @ 668.3 | 1057.05 (14:03) · 489.15 | – · – · – | same as current |
| 10-01 | long SENSEX 72400PE | 12:10 @ 281.45 | 12:11 @ 272.2 [I] | 13:05 held @ 668.3 | = current | 13:05 held @ 668.3 | 13:05 held @ 668.3 | 1057.05 (14:03) · 489.15 | – · – · – | same as current |
| 10-01 | long SENSEX 72300PE | 12:10 @ 224.1 | 12:11 @ 219.5 [I] | 13:05 held @ 580.3 | = current | 13:05 held @ 580.3 | 13:05 held @ 580.3 | 960.8 (14:04) · 390.05 | – · – · – | same as current |
| 10-01 | long SENSEX 72300PE | 12:19 @ 232.0 | 12:20 @ 226.0 [I] | 13:05 held @ 580.3 | = current | 13:05 held @ 580.3 | 13:05 held @ 580.3 | 960.8 (14:04) · 390.05 | – · – · – | same as current |
| 10-01 | long SENSEX 72300PE | 12:22 @ 246.4 | 12:22 @ 247.35 [I] | 13:05 held @ 580.3 | = current | 13:05 held @ 580.3 | 13:05 held @ 580.3 | 960.8 (14:04) · 390.05 | – · – · – | same as current |
| 10-01 | long SENSEX 72300PE | 12:27 @ 296.9 | 12:29 @ 320.45 [I] | 12:41 accept @ 274.0 | = current | 12:41 accept @ 274.0 | 12:41 accept @ 274.0 | 960.8 (14:04) · 390.05 | – · – · – | same as current |
| 10-05 | long NIFTY 22600CE | 09:28 @ 94.25 | 09:34 @ 99.5 [I] | 11:50 accept @ 48.2 | = current | 10:02 zone only @ 84.75 | 10:02 zone only @ 84.75 | 90.6 (13:45) · 58.7 | 10:02 · 10:02 · 10:02 | C3: LOSER FOLDED EARLIER (+36.55 pts v current); C1+2+3: LOSER FOLDED EARLIER (+36.55 pts v current) |
| 10-05 | long NIFTY 22550CE | 09:35 @ 134.95 | 09:44 @ 123.9 [I] | 10:02 accept @ 112.2 | = current | 10:02 zone only @ 112.25 | 10:02 zone only @ 112.25 | 119.6 (13:45) · 82.65 | 10:02 · 10:02 · 10:02 | same as current |
| 10-05 | long NIFTY 22550PE | 12:09 @ 174.75 | 12:18 @ 153.6 [I] | 13:38 accept @ 112.25 | = current | 12:54 zone only @ 149.85 | 12:54 zone only @ 149.85 | 152.05 (12:54) · 76.4 | 12:54 · 12:54 · 12:54 | C3: LOSER FOLDED EARLIER (+37.6 pts v current); C1+2+3: LOSER FOLDED EARLIER (+37.6 pts v current) |
| 10-05 | short NIFTY 22650PE | 13:41 @ 131.35 | 15:42 @ 133.75 [I] | none | = current | 13:51 zone only @ 132.85 | 13:51 zone only @ 132.85 | 124.1 (13:52) · 133.75 | 14:05 · 14:05 · 14:05 | C3: LOSER FOLDED EARLIER (+0.9 pts v current at 15:30); C1+2+3: LOSER FOLDED EARLIER (+0.9 pts v current at 15:30) |
| 10-06 | short NIFTY 22600CE | 09:35 @ 65.8 | 09:48 @ 81.5 [I] | 11:45 accept @ 113.65 | = current | 10:04 zone only @ 85.15 | 10:01 zone only @ 95.25 | 67.0 (10:10) · 114.9 (11:47 cut) | – · 10:44 · 10:01 | C3: LOSER FOLDED EARLIER (+28.5 pts v current); C1+2+3: LOSER FOLDED EARLIER (+18.4 pts v current) |
| 10-06 | short NIFTY 22650PE | 10:02 @ 55.9 | 10:02 @ 56.4 [I] | none | = current | none | 10:13 zone only @ 64.1 | 29.6 (11:45) · 29.85 (11:47 cut) | – · 10:11 · – | C1+2+3: WINNER CUT (-34.25 pts v current at 15:30) |

## C3' (at the line)

Decided before the replay: FOLD only when (a) the last future print is within B (`B_at(t)`) of G on her losing side
or beyond it, i.e. d·(fut − G) ≤ B; (b) OI is not WITH and FLOW is not WITH (or WITH but tiring ≥ 20 min); (c) neither
chip reads CAN'T CHECK (or is unread); and W is not building. Same scripts, same rows. "to G" = d·(fut − G) at the
FOLD: + is still on her side, − is past G. prem = chain LTP at or before the FOLD second [M]. Rows below are the 20
trades (of 51, today included) where any of C3, C3' or C1+C2+C3' differs from current; the other 31 read the same
under all of them [M]. Today ends 11:54:40.

| trade | current FOLD @ prem [M] | old C3 FOLD @ prem (v current) · to G (B) [M] | C3' FOLD @ prem (v current) · to G (B) [M] | C1+C2+C3' FOLD @ prem (v current) [M] | read [I, hindsight] |
|---|---|---|---|---|---|
| 10-06 long NIFTY 22650PE 10:03 | 11:45:33 @ 31.05 accept | 11:04:56 @ 45.3 (+14.25) · to G +16.0 (B 9.5) | 11:05:26 @ 41.9 (+10.85) · to G +9.0 (B 9.4) | 10:44:35 @ 45.15 (+14.10) | today: C3' folds at the line, 40 min before current |
| 09-22 long NIFTY 23300CE 09:42 | 10:45:52 @ 100.8 accept | 10:31:43 @ 135.55 (+34.75) · to G +26.6 (B 9.9) | 10:39:26 @ 122.65 (+21.85) · to G +9.3 (B 10.0) | 10:39:26 @ 122.65 (+21.85) | loser: still folded earlier |
| 09-22 long NIFTY 23550PE 10:32 | 14:12:45 @ 238.55 expiry | 11:39:33 @ 184.3 (-54.25) · to G +21.8 (B 10.5) | 13:43:39 @ 211.35 (-27.20) · to G -10.6 (B 10.6) | 13:43:39 @ 211.35 (-27.20) | **WINNER still cut** (past G; 270.9 at 14:00) |
| 09-22 long NIFTY 23500PE 13:48 | 14:19:49 @ 124.1 accept | 14:14:54 @ 133.95 (+9.85) · to G +7.0 (B 11.1) | 14:14:54 @ 133.95 (+9.85) · to G +7.0 (B 11.1) | 14:14:50 @ 158.4 (+34.30) | loser: still folded earlier |
| 09-23 long NIFTY 23450CE 09:18 | 14:45:47 @ 108.5 flow_oi | 09:58:47 @ 93.65 (-14.85) · to G +18.3 (B 10.0) | 14:45:47 @ 108.5 | 14:45:47 @ 108.5 | winner: no longer cut |
| 09-23 long NIFTY 23450CE 09:47 | 14:45:47 @ 108.5 flow_oi | 09:58:47 @ 93.65 (-14.85) · to G +15.3 (B 10.0) | 14:45:47 @ 108.5 | 14:45:47 @ 108.5 | winner: no longer cut |
| 09-23 long NIFTY 23450CE 10:00 | 14:45:47 @ 108.5 flow_oi | 11:33:07 @ 118.9 (+10.40) · to G +164.4 (B 9.1) | 14:45:47 @ 108.5 | 14:45:47 @ 108.5 | = current (old C3 was earlier, better) |
| 09-23 long NIFTY 23450CE 10:19 | 14:45:47 @ 108.5 flow_oi | 13:09:59 @ 123.4 (+14.90) · to G +44.0 (B 7.2) | 14:45:47 @ 108.5 | 14:45:47 @ 108.5 | = current (old C3 was earlier, better) |
| 09-23 long NIFTY 23450CE 10:33 | 14:45:47 @ 108.5 flow_oi | 13:09:59 @ 123.4 (+14.90) · to G +44.0 (B 7.2) | 14:45:47 @ 108.5 | 14:45:47 @ 108.5 | = current (old C3 was earlier, better) |
| 09-23 long NIFTY 23450CE 11:07 | 14:45:47 @ 108.5 flow_oi | 13:09:59 @ 123.4 (+14.90) · to G +44.0 (B 7.2) | 14:45:47 @ 108.5 | 14:45:47 @ 108.5 | loser: no longer folded earlier |
| 09-24 long SENSEX 74200PE 10:19 | 13:22:06 @ 264.15 held | 11:18:06 @ 171.25 (-92.90) · to G +46.0 (B 6.1) | 11:19:57 @ 154.25 (-109.90) · to G +6.0 (B 6.2) | 11:02:22 @ 162.3 (-101.85) | **WINNER still cut** (640.8 at 14:24) |
| 09-25 long NIFTY 23100CE 12:01 | 12:47:13 @ 101.7 accept | 12:07:04 @ 109.95 (+8.25) · to G +9.9 (B 9.0) | 12:07:13 @ 109.95 (+8.25) · to G +6.5 (B 9.0) | 12:07:13 @ 109.95 (+8.25) | loser: still folded earlier |
| 09-28 long NIFTY 23000PE 09:30 | none (last 206.05) | 11:52:04 @ 165.5 (-40.55) · to G +45.0 (B 10.1) | 15:10:26 @ 206.45 (+0.40) · to G +6.0 (B 9.3) | 15:10:26 @ 206.45 (+0.40) | winner: no longer cut (15:10, after her 15:00 close) |
| 09-29 long NIFTY 22800PE 09:18 | 11:11:37 @ 142.8 flow_oi | 11:10:58 @ 153.15 (+10.35) · to G -17.0 (B 10.5) | 11:10:58 @ 153.15 (+10.35) · to G -17.0 (B 10.5) | 11:10:58 @ 153.15 (+10.35) | winner: earlier and better (past G) |
| 09-30 long NIFTY 22750CE 10:10 | 11:16:33 @ 127.55 accept | 10:35:05 @ 142.0 (+14.45) · to G +56.8 (B 12.4) | 11:16:33 @ 127.55 | 11:16:33 @ 127.55 | loser: no longer folded earlier |
| 10-01 long SENSEX 72400CE 09:30 | 12:10:11 @ 90.1 flow_oi | 11:42:29 @ 186.55 (+96.45) · to G +31.8 (B 14.0) | 12:09:05 @ 101.65 (+11.55) · to G -137.4 (B 11.4) | 11:39:27 @ 156.5 (+66.40) | loser: still earlier, by 1 min |
| 10-05 long NIFTY 22600CE 09:28 | 11:50:45 @ 48.2 accept | 10:02:20 @ 84.75 (+36.55) · to G +93.0 (B 12.6) | 10:55:07 @ 54.6 (+6.40) · to G +1.6 (B 12.6) | 10:52:26 @ 58.8 (+10.60) | loser: still folded earlier |
| 10-05 long NIFTY 22550PE 12:09 | 13:38:15 @ 112.25 accept | 12:54:11 @ 149.85 (+37.60) · to G +29.0 (B 11.7) | 12:57:30 @ 136.65 (+24.40) · to G +8.7 (B 11.8) | 12:57:30 @ 136.65 (+24.40) | loser: still folded earlier |
| 10-05 short NIFTY 22650PE 13:41 | none (last 133.75) | 13:51:38 @ 132.85 (+0.90) · to G +60.0 (B 11.6) | 14:05:31 @ 161.45 (-27.70) · to G +11.0 (B 11.6) | 14:05:31 @ 161.45 (-27.70) | **NEW cost**: the sale folded at its worst minute |
| 10-06 short NIFTY 22600CE 09:35 | 11:45:33 @ 113.65 accept | 10:04:20 @ 85.15 (+28.50) · to G +37.9 (B 10.7) | 11:05:26 @ 102.2 (+11.45) · to G +9.0 (B 9.4) | 10:44:35 @ 100.2 (+13.45) | loser: still folded earlier |

1. **Today C3' FOLDs at 11:05:26 at 41.9** [M] (entry 55: −13.1). That is +10.85 against current's 11:45:33 at 31.05, with fut 9.0 inside G 22770 (B 9.4). C1+C2+C3' FOLDs at 10:44:35 at 45.15 (+14.10). The premium was 33.2 at 11:54 [M].
2. **Winners** [I, hindsight]: C3' no longer cuts 09-23 09:18 and 09:47 23450CE, or 09-28 23000PE (its 15:10 FOLD at 206.45 comes after her 15:00 close). It **still cuts 09-22 10:32 23550PE** (13:43:39, 10.6 past G, −27.20) **and 09-24 10:19 SENSEX 74200PE** (11:19:57, 6.0 from G, −109.90). Both came to the line with OI and FLOW not behind her, and then ran.
3. Distance to G at the old C3 folds on those winners [M]: 09-22 +21.8 (B 10.5); 09-23 +18.3 and +15.3 (B 10.0); 09-24 SENSEX +46.0 (B 6.1); 09-28 +45.0 (B 10.1). Every one was 1.5 B to 7.5 B on her side, none at the line. "At the line" separates the old cuts at that minute, but it does not stop two of them being cut later, once price reaches the line.
4. **Losers**: C3' still folds 7 of the 9 earlier than current, by +6.40 to +24.40 pts (C3: +8.25 to +96.45). They are 09-22 09:42, 09-22 13:48, 09-25 23100CE, 10-01 SENSEX CE (by 1 min), 10-05 22600CE, 10-05 22550PE and 10-06 short 22600CE. It no longer folds 09-23 11:07 23450CE or 09-30 22750CE earlier.
5. **New cost** [M]: on the 10-05 short 22650PE, C3' FOLDs at 14:05:31 at 161.45 (11.0 from G, B 11.6), the sale's worst minute. The PE was 127.35 at 15:20 and 133.75 at the close (−27.70 against current, which never folds).
6. The CAN'T CHECK guard removes the old 10-05 13:51:38 fold, which came from a feed hole [M]. Inside C1+C2+C3', C1 again pulls folds earlier: 09-24 SENSEX to 11:02:22, 10-01 SENSEX CE to 11:39:27, 10-05 22600CE to 10:52:26, and 10-06 short 22600CE and today both to 10:44:35.
