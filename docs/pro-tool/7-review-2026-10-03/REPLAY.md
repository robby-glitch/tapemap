# 7-review: the hold-or-fold replay (2026-10-03)

**Read-only.** No .py/.ts edited, no server touched, nothing written under `data/`. Every number is [M] measured from the recorded rows, or [I] inferred (premium at a level, chips). Rows are described; no rate is printed anywhere. (h) = hand-set.

## 0. How this was run (verify, don't trust)

- **Engine:** `fold.py` rev 6 as on disk (mtime 2026-09-29 17:33), fed exactly as `fold_live.Engine._build` feeds it (VPIN + tape first, then book and chain rows in key order), but in 1-minute chunks so a snapshot is taken at every minute. Harness: `harness/replay7.py` (it imports `fold`, writes only to its output folder). Two variants for the candidates are subclasses in the harness, not edits.
- **It reproduces the live log.** 30 Sep replayed gives the same events, times and numbers as `data/fold/fold_NIFTY_2026-09-30.jsonl`: seed 10:10:12, G 22769 from "22700 PE writers 109.3L"; OI event 10:35:05 (119.4L to 113.0L, -5.4 %, z 3.1, 4 updates); reset 11:11:11 to G 22803; FOLD 11:16:33 at 127.55; second FOLD 14:16:11 at 134.7 [M].
- **`tools/fold_replay.py` (run, read-only):** 9 of 9 design trades MATCH blueprint §4.9 (A4 prints flow_oi 10:09:25 where the table says held 10:09:29: same exit, same %) [M].
- **Sessions:** every NIFTY day with a book file: 22, 23, 24, 25, 28, 29, 30 Sep and 1 Oct (2 Oct was a holiday). Prior pools via `tape_log.prior_pool`, as live. Expiry days: 22 Sep (fold_replay's convention) and 29 Sep (the chain's own field). Basis (future minus the options' forward): 22 Sep 8 to 15 pts, 23 to 25 Sep about 0, 28 to 29 Sep 1 to 8, **30 Sep and 1 Oct 61 to 78 pts** (Oct future against the 6 Oct weekly) [M].
- **Three populations, never pooled:**
  - **marked**: her 5 trades from `data/day_state/*.json` `hold_trades`. 25 Sep has two, a CE and a PE marked 4 minutes apart.
  - **design**: the 9 trades in `tools/fold_replay.py`.
  - **zone**: 31 IF-YOU-WERE-IN marks at her zone triggers (`trigger_log.jsonl`, `rule: zone`, NIFTY).
    - d2→d3 BUY marks a long ATM CE; u2→u3 SELL marks a long ATM PE.
    - The mark is at the trigger bar's close (t + 3 min). The live row was written about 1.5 min after that [M].
    - ATM is the strike with the smallest |CE − PE|. p0 is the chain LTP of the last row at or before the mark.
    - The sold mirror (short the other side, same second, same d) has the identical engine read; only its premium differs (§4.3).
- **Skipped zone rows, and why:**
  - 7 rows dated 2026-10-01 were written at 10-01 00:00:06. They are copies of 30 Sep's rows (same t, side and px), a midnight mis-date in `trigger_log.jsonl`, reported and not touched.
  - 2 rows triggered after 15:00 (her practice).
- **Data note:** the day_state record for 28 Sep says she exited at 10:20:27 (+30 %). Blueprint §0 says she left at 14:12 at 164.8. I used the record. Rows 3 and 13 below are the same engine read; only the exit differs.
- **Re-run** from the tapemap root (it reads relative `data/` paths, as the server does): `python docs/pro-tool/7-review-2026-10-03/harness/replay7.py <scratch dir> <day,day> <tag>` writes `replays_<tag>.json` and `minutes_<tag>.csv` there. Then `analyze8.py <scratch dir>`, `analyze9.py`, `analyze10.py`, `tables.py`, `mirror.py` and `pullback.py` read them (run them from `harness/`). About 15 s per trade, with variants.
- **Full minute-by-minute** (fut, premium, %, four chips, headline, G, points to G, premium at G as shown and corrected, W, mode): `minutes.csv`, 9,904 rows over 45 replays.

**Legend.** % = % of entry premium, the trade's own sign [M]. Chips Z F O V = ZONE · FLOW · OI · VPIN: W = WITH, A = AGAINST, q = QUIET, ? = CAN'T CHECK, - = not read yet. "to G" = points the future is still on her side of G (negative = beyond it). "at G" = the premium if the future were at G now [I]. "Shown" is `fold._prem_at`, the number on the DESK. "Corrected" is the same interpolation at K + (fut − G); see §3, D2.

## 1. Every replay, one line (entry → 15:00)

| # | replay | trade @ p0, mark | G at mark: pts away / premium there [I] | her exit | rev 6 first FOLD | low | high | 15:00 |
|---|---|---|---|---|---|---|---|---|
| 1 | 23100CE 120121 | 09-25 long 23100CE @ 113.55, 12:01 | 23100: 22 / -11 % | -19 13:23 | -10 12:47 accept | -21 13:35 | +59 14:06 | +29 |
| 2 | 23200PE 120528 | 09-25 long 23200PE @ 155.4, 12:05 | 23146: 36 / -14 % | +14 13:23 | -17 14:01 flow_oi | -41 14:06 | +23 12:57 | -32 |
| 3 | 23000PE 093027 | 09-28 long 23000PE @ 120.4, 09:30 | 22997: 52 / -25 % | +30 10:20 | none | -3 09:31 | +97 14:38 | +71 |
| 4 | 22800PE 091807 | 09-29 long 22800PE @ 113.95, 09:18 | 22805: 103 / -42 % | +66 09:35 | +25 11:11 flow_oi | -30 12:07 | +101 09:38 | +11 |
| 5 | 22750CE 101012 | 09-30 long 22750CE @ 164.7, 10:10 | 22769: 100 / -31 % | -24 11:16 | -23 11:16 accept | -45 14:43 | +23 12:48 | -41 |
| 6 | A1 | 09-22 long 23450PE @ 47.75, 09:39 | 23470: 16 / -10 % | - | +199 14:12 expiry | -25 10:10 | +264 14:00 | +108 |
| 7 | A2 | 09-22 long 23350CE @ 43.65, 12:01 | 23309: 58 / -47 % | - | -42 13:51 accept | -61 14:00 | +78 14:21 | -11 |
| 8 | R-A2 | 09-22 long 23350CE @ 68.35, 14:15 | 23337: 43 / -58 % | - | none | -47 14:59 | +14 14:21 | -43 |
| 9 | A3 | 09-23 long 23450PE @ 122.3, 10:40 | 23503: 66 / -24 % | - | -12 12:04 accept | -22 14:29 | +3 10:42 | -8 |
| 10 | H1 | 09-24 long 23250PE @ 102.65, 09:30 | 23273: 16 / -1 % | - | +98 14:39 held | -2 09:32 | +154 13:59 | +98 |
| 11 | A4 | 09-25 long 23150PE @ 111.6, 09:31 | 23205: 61 / -19 % | - | +7 10:09 flow_oi | -35 14:06 | +42 12:57 | -26 |
| 12 | A5 | 09-25 long 23150CE @ 96.5, 09:39 | 23094: 16 / -11 % | - | -10 09:47 accept | -29 13:35 | +53 14:06 | +20 |
| 13 | H2 | 09-28 long 23000PE @ 120.4, 09:30 | 22997: 52 / -25 % | - | none | -3 09:31 | +97 14:38 | +71 |
| 14 | A6 | 09-28 long 22950CE @ 84.05, 09:31 | 22902: 48 / -27 % | - | -17 10:16 accept | -63 14:38 | +0 09:31 | -61 |
| 15 | Z 09-22 09:39 BUY | 09-22 long 23450CE @ 47.8, 09:42 | 23402: 65 / -47 % | - | -53 10:45 accept | -91 14:00 | +9 10:10 | -85 |
| 16 | Z 09-22 09:57 SELL | 09-22 long 23450PE @ 42.0, 10:00 | 23469: 1 / -6 % | - | +240 14:12 expiry | -15 10:10 | +314 14:00 | +137 |
| 17 | Z 09-22 11:12 BUY | 09-22 long 23400CE @ 42.2, 11:15 | 23310: 90 / -67 % | - | -71 13:51 accept | -80 14:01 | +11 14:21 | -58 |
| 18 | Z 09-22 12:03 BUY | 09-22 long 23350CE @ 47.7, 12:06 | 23309: 63 / -54 % | - | -47 13:51 accept | -64 14:00 | +63 14:21 | -18 |
| 19 | Z 09-22 14:09 BUY | 09-22 long 23300CE @ 50.9, 14:12 | 23308: 42 / -19 % | - | +65 14:41 expiry | -5 14:12 | +132 14:21 | +42 |
| 20 | Z 09-23 09:57 BUY | 09-23 long 23400CE @ 120.2, 10:00 | 23294: 118 / -40 % | - | +14 14:45 flow_oi | -7 10:11 | +37 12:20 | +9 |
| 21 | Z 09-23 11:15 SELL | 09-23 long 23450PE @ 121.4, 11:18 | 23454: 18 / -6 % | - | -11 12:04 accept | -21 14:29 | +1 11:18 | -7 |
| 22 | Z 09-23 12:24 SELL | 09-23 long 23450PE @ 107.8, 12:27 | 23502: 38 / -15 % | - | -5 14:17 held | -11 14:29 | +11 13:36 | +5 |
| 23 | Z 09-24 09:57 BUY | 09-24 long 23250CE @ 111.1, 10:00 | 23196: 42 / -17 % | - | -13 11:58 accept | -41 14:24 | +5 10:55 | -35 |
| 24 | Z 09-24 10:30 BUY | 09-24 long 23250CE @ 108.1, 10:33 | 23196: 47 / -21 % | - | -11 11:58 accept | -39 14:24 | +8 10:55 | -33 |
| 25 | Z 09-24 12:00 BUY | 09-24 long 23250CE @ 101.55, 12:03 | 23193: 32 / -16 % | - | -8 12:48 accept | -35 14:24 | +1 12:06 | -29 |
| 26 | Z 09-24 13:00 BUY | 09-24 long 23200CE @ 121.45, 13:03 | 23169: 40 / -16 % | - | -13 13:27 accept | -32 14:24 | +4 13:08 | -25 |
| 27 | Z 09-24 13:30 BUY | 09-24 long 23200CE @ 111.35, 13:33 | 23136: 39 / -17 % | - | -11 13:44 accept | -26 14:24 | +0 13:33 | -18 |
| 28 | Z 09-24 14:00 BUY | 09-24 long 23100CE @ 144.45, 14:03 | 23090: 12 / -5 % | - | -6 14:07 accept | -13 14:24 | +3 14:55 | -3 |
| 29 | Z 09-24 14:30 BUY | 09-24 long 23100CE @ 134.2, 14:33 | 22992: 99 / -33 % | - | none | -1 14:33 | +11 14:55 | +4 |
| 30 | Z 09-25 09:33 SELL | 09-25 long 23150PE @ 116.4, 09:36 | 23206: 78 / -25 % | - | +2 10:09 flow_oi | -38 14:06 | +36 12:57 | -29 |
| 31 | Z 09-25 09:54 BUY | 09-25 long 23100CE @ 115.65, 09:57 | 22993: 105 / -41 % | - | -12 12:47 accept | -23 13:35 | +57 14:06 | +27 |
| 32 | Z 09-25 13:00 BUY | 09-25 long 23100CE @ 99.1, 13:03 | 23066: 16 / -7 % | - | -9 13:35 accept | -10 13:35 | +83 14:06 | +48 |
| 33 | Z 09-28 09:48 BUY | 09-28 long 22900CE @ 98.9, 09:51 | 22892: 26 / -11 % | - | -16 10:18 accept | -57 14:38 | +4 09:58 | -54 |
| 34 | Z 09-28 14:45 BUY | 09-28 long 22800CE @ 86.35, 14:48 | 22800: 20 / -8 % | - | none | -1 14:48 | +9 14:53 | +2 |
| 35 | Z 09-29 09:39 BUY | 09-29 long 22600CE @ 77.7, 09:42 | 22596: 39 / -17 % | - | -25 10:15 accept | -34 10:21 | +124 12:08 | +13 |
| 36 | Z 09-29 12:18 SELL | 09-29 long 22750PE @ 64.4, 12:21 | 22777: 48 / -34 % | - | +64 13:34 expiry | +0 12:21 | +110 12:33 | +28 |
| 37 | Z 09-30 09:30 SELL | 09-30 long 22750PE @ 145.6, 09:33 | 22886: 54 / -13 % | - | -19 10:22 accept | -35 12:48 | +49 14:43 | +31 |
| 38 | Z 09-30 10:27 SELL | 09-30 long 22800PE @ 143.4, 10:30 | 22984: 121 / -31 % | - | none | -21 12:48 | +73 14:43 | +55 |
| 39 | Z 09-30 11:00 BUY | 09-30 long 22750CE @ 148.6, 11:03 | 22769: 68 / -24 % | - | -14 11:16 accept | -39 14:43 | +36 12:48 | -34 |
| 40 | Z 09-30 11:27 BUY | 09-30 long 22750CE @ 136.2, 11:30 | 22803: 22 / -4 % | - | -1 14:16 flow_oi | -34 14:43 | +49 12:48 | -28 |
| 41 | Z 09-30 13:03 SELL | 09-30 long 22850PE @ 144.85, 13:06 | 22979: 74 / -22 % | - | none | -3 13:09 | +95 14:43 | +77 |
| 42 | Z 09-30 14:45 BUY | 09-30 long 22650CE @ 146.65, 14:48 | 22721: 7 / -4 % | - | none | -4 14:56 | +3 14:49 | -2 |
| 43 | Z 10-01 10:12 SELL | 10-01 long 22600PE @ 130.25, 10:15 | 22676: 20 / -2 % | - | -11 10:36 accept | -12 10:36 | +196 14:05 | +81 |
| 44 | Z 10-01 10:39 SELL | 10-01 long 22600PE @ 122.85, 10:42 | 22684: 12 / -2 % | - | none | -1 10:52 | +213 14:05 | +92 |
| 45 | Z 10-01 13:00 BUY | 10-01 long 22400CE @ 141.45, 13:03 | 22358: 102 / -32 % | - | -29 13:59 accept | -34 14:05 | +11 14:56 | +3 |

"her exit" and "rev 6 first FOLD" are premium % at that second. low and high run from the mark to 15:00. The premium path is the chain LTP, about every 10 s [M].

## 2. Her five marked trades, minute by minute (compact)

Rows are printed every 5 minutes until 30 minutes after her exit, then every 30 minutes. A row is also printed whenever a chip, G or the headline changes, and at each mark. Marks: (a) her exit, (b) rev 6's first FOLD, (c) the premium low and high after entry, (iv-g) the recommended rule's GAVE UP (AMENDMENT-DRAFT.md). After a FOLD the headline stays frozen, as rev 6 does. The rows go on to 15:00 as "what holding would have done".

#### NIFTY-23100CE-long-120121 · 2026-09-25 · long 23100 CE @ 113.55 · mark 12:01:21 (fut 23123.0) · her exit 13:23:20

| min | fut | prem (% of entry) | Z F O V | headline | G | fut to G (pts) | at G: shown / corrected (%) | W | marks |
|---|---|---|---|---|---|---|---|---|---|
| 12:02 | 23122 | 111.7 (-2) | -AWq | HOLD | 23100 | +22 | 104.3 / 101.6 (-11) | 23100 building |  |
| 12:05 | 23110 | 111.6 (-2) | qAWq | HOLD | 23100 | +10 | 110.2 / 107.6 (-5) | 23100 building |  |
| 12:07 | 23110 | 109.1 (-4) | WAWq | HOLD | 23100 | +10 | 109.1 / 106.7 (-6) | 23100 building |  |
| 12:08 | 23110 | 108.6 (-4) | WAAq | HOLD | 23100 | +10 | 106.1 / 103.7 (-9) | 23100 off | (iv-g) GAVE UP 12:07:04 |
| 12:09 | 23107 | 110.25 (-3) | WWAq | HOLD | 23100 | +7 | 109.1 / 106.8 (-6) | 23100 off |  |
| 12:10 | 23113 | 113.25 (-0) | WWAq | HOLD | 23100 | +13 | 108.8 / 106.6 (-6) | 23100 off |  |
| 12:12 | 23120 | 114.9 (+1) | qWAq | HOLD | 23100 | +20 | 105.7 / 104.7 (-8) | 23100 off |  |
| 12:15 | 23119 | 113.55 (+0) | qWAq | HOLD | 23100 | +19 | 104.4 / 104.0 (-8) | 23100 off |  |
| 12:20 | 23117 | 112.75 (-1) | qWAq | HOLD | 23100 | +17 | 105.7 / 105.9 (-7) | 23100 off |  |
| 12:22 | 23116 | 108.55 (-4) | qWAW | HOLD | 23100 | +16 | 101.2 / 101.2 (-11) | 23100 off |  |
| 12:25 | 23113 | 110.05 (-3) | qWAW | HOLD | 23100 | +13 | 104.4 / 103.6 (-9) | 23100 off |  |
| 12:30 | 23114 | 113.45 (-0) | qWAW | HOLD | 23100 | +14 | 106.7 / 105.9 (-7) | 23100 off |  |
| 12:35 | 23120 | 112.35 (-1) | qWAW | HOLD | 23100 | +20 | 103.1 / 102.2 (-10) | 23100 off |  |
| 12:40 | 23109 | 110.65 (-3) | WWAW | HOLD | 23100 | +9 | 105.7 / 106.2 (-6) | 23100 off |  |
| 12:44 | 23098 | 102.95 (-9) | WAAW | HOLD | 23100 | -2 | 102.5 / 102.8 (-9) | 23100 off |  |
| 12:45 | 23095 | 101.5 (-11) | WAAW | HOLD | 23100 | -5 | 105.0 / 104.9 (-8) | 23100 off |  |
| 12:48 | 23098 | 103.3 (-9) | WAAW | FOLD | 23100 | -2 | 106.0 / 105.9 (-7) | 23100 off | (b) rev 6 FOLD · 23100 accepted · 12:47 |
| 12:50 | 23089 | 100.8 (-11) | WAAq | FOLD | 23100 | -11 | 103.8 / 104.1 (-8) | 23100 off |  |
| 12:53 | 23090 | 99.3 (-12) | qAAq | FOLD | 23100 | -10 | 107.2 / 107.6 (-5) | 23100 off |  |
| 12:55 | 23080 | 97.55 (-14) | qAAA | FOLD | 23100 | -20 | 106.8 / 106.7 (-6) | 23100 off |  |
| 13:00 | 23079 | 97.45 (-14) | qAAA | FOLD | 23100 | -21 | 106.0 / 106.4 (-6) | 23100 off |  |
| 13:03 | 23096 | 99.1 (-13) | qAAW | FOLD | 23100 | -4 | 105.4 / 105.6 (-7) | 23100 off |  |
| 13:05 | 23090 | 98.15 (-14) | qAAW | FOLD | 23100 | -10 | 103.5 / 103.6 (-9) | 23100 off |  |
| 13:10 | 23091 | 100.4 (-12) | qAAW | FOLD | 23100 | -9 | 107.6 / 108.1 (-5) | 23100 off |  |
| 13:15 | 23080 | 97.2 (-14) | qAAW | FOLD | 23100 | -20 | 103.4 / 103.7 (-9) | 23100 off |  |
| 13:20 | 23077 | 94.25 (-17) | qAAq | FOLD | 23100 | -23 | 103.2 / 103.5 (-9) | 23100 off |  |
| 13:23 | 23073 | 93.8 (-17) | qAWq | FOLD | 23100 | -27 | 104.2 / 104.4 (-8) | 23100 building |  |
| 13:24 | 23077 | 93.65 (-18) | qAWq | FOLD | 23100 | -23 | 105.0 / 105.3 (-7) | 23100 building | (a) her exit 13:23:20 |
| 13:25 | 23072 | 90.9 (-20) | qAWq | FOLD | 23100 | -28 | 105.7 / 106.0 (-7) | 23100 building |  |
| 13:30 | 23084 | 94.4 (-17) | qAWq | FOLD | 23100 | -16 | 103.8 / 104.3 (-8) | 23100 building |  |
| 13:35 | 23072 | 90.0 (-21) | qAWq | FOLD | 23100 | -28 | 104.4 / 104.6 (-8) | 23100 building |  |
| 13:36 | 23071 | 90.15 (-21) | qAWq | FOLD | 23100 | -29 | 105.4 / 105.6 (-7) | 23100 stopped | (c) low -21 % 13:35 |
| 13:39 | 23077 | 92.9 (-18) | qAqq | FOLD | 23100 | -23 | 104.9 / 105.0 (-8) | 23100 stopped |  |
| 13:40 | 23080 | 92.8 (-18) | qAqq | FOLD | 23100 | -20 | 105.5 / 105.3 (-7) | 23100 stopped |  |
| 13:45 | 23086 | 95.85 (-16) | qAqq | FOLD | 23100 | -14 | 103.5 / 103.2 (-9) | 23100 stopped |  |
| 13:48 | 23090 | 96.95 (-15) | qAqW | FOLD | 23100 | -10 | 102.9 / 102.5 (-10) | 23100 stopped |  |
| 13:50 | 23084 | 96.55 (-15) | qAqW | FOLD | 23100 | -16 | 103.3 / 103.1 (-9) | 23100 stopped |  |
| 13:51 | 23084 | 95.45 (-16) | WAqW | FOLD | 23100 | -16 | 104.2 / 103.9 (-8) | 23100 stopped |  |
| 14:00 | 23109 | 106.55 (-6) | WAqW | FOLD | 23100 | +9 | 100.6 / 100.5 (-11) | 23100 stopped |  |
| 14:06 | 23206 | 171.75 (+51) | qqWq | FOLD | 23125 | +80 | 114.1 / 114.5 (+1) | 23150 building |  |
| 14:07 | 23218 | 176.5 (+55) | qqWW | FOLD | 23125 | +93 | 114.1 / 114.6 (+1) | 23150 building | (c) high +59 % 14:06 |
| 14:29 | 23194 | 156.35 (+38) | WWWq | FOLD | 23174 | +20 | 143.5 / 143.7 (+27) | 23150 building |  |
| 14:30 | 23192 | 154.55 (+36) | WWWq | FOLD | 23174 | +18 | 144.4 / 144.6 (+27) | 23150 building |  |
| 15:00 | 23182 | 146.85 (+29) | qAWq | FOLD | 23174 | +8 | 140.9 / 141.9 (+25) | 23150 stopped |  |

#### NIFTY-23200PE-long-120528 · 2026-09-25 · long 23200 PE @ 155.4 · mark 12:05:28 (fut 23110.0) · her exit 13:23:18

| min | fut | prem (% of entry) | Z F O V | headline | G | fut to G (pts) | at G: shown / corrected (%) | W | marks |
|---|---|---|---|---|---|---|---|---|---|
| 12:06 | 23110 | 154.55 (-0) | -WWq | HOLD | 23146 | +36 | 130.5 / 133.5 (-14) | 23150 building |  |
| 12:07 | 23110 | 158.65 (+2) | AWWq | HOLD | 23146 | +36 | 131.7 / 134.6 (-13) | 23150 building |  |
| 12:09 | 23107 | 156.7 (+1) | AAWq | HOLD | 23146 | +39 | 130.8 / 133.6 (-14) | 23150 building |  |
| 12:10 | 23113 | 151.5 (-2) | AAWq | HOLD | 23146 | +33 | 129.9 / 132.5 (-15) | 23150 building |  |
| 12:14 | 23120 | 149.65 (-4) | qAWq | HOLD | 23146 | +26 | 134.4 / 135.2 (-13) | 23150 building |  |
| 12:15 | 23119 | 149.45 (-4) | qAWq | HOLD | 23146 | +27 | 133.6 / 134.1 (-14) | 23150 building |  |
| 12:20 | 23117 | 149.85 (-4) | qAWq | HOLD | 23146 | +29 | 131.2 / 130.9 (-16) | 23150 building |  |
| 12:22 | 23116 | 155.45 (+0) | qAWA | HOLD | 23146 | +30 | 136.9 / 136.9 (-12) | 23150 building |  |
| 12:25 | 23113 | 153.5 (-1) | qAWA | HOLD | 23146 | +33 | 133.3 / 134.2 (-14) | 23150 building |  |
| 12:28 | 23110 | 152.7 (-2) | AAWA | HOLD | 23146 | +36 | 131.5 / 132.6 (-15) | 23150 building |  |
| 12:29 | 23115 | 149.75 (-4) | qAWA | HOLD | 23146 | +31 | 130.2 / 131.2 (-16) | 23150 building |  |
| 12:30 | 23114 | 148.25 (-5) | qAWA | HOLD | 23146 | +32 | 129.3 / 130.2 (-16) | 23150 building |  |
| 12:34 | 23115 | 148.95 (-4) | WAWA | HOLD | 23146 | +31 | 129.6 / 130.1 (-16) | 23150 building |  |
| 12:35 | 23120 | 149.4 (-4) | WAWA | HOLD | 23146 | +26 | 133.2 / 134.2 (-14) | 23150 building |  |
| 12:38 | 23110 | 156.3 (+1) | qAWA | HOLD | 23146 | +36 | 134.7 / 134.8 (-13) | 23150 building |  |
| 12:40 | 23109 | 151.5 (-2) | AAWA | HOLD | 23146 | +37 | 130.1 / 129.5 (-17) | 23150 building |  |
| 12:44 | 23098 | 162.1 (+4) | AWWA | HOLD | 23146 | +48 | 134.6 / 134.3 (-14) | 23150 building |  |
| 12:45 | 23095 | 163.8 (+5) | AWWA | HOLD | 23146 | +51 | 131.8 / 131.9 (-15) | 23150 building |  |
| 12:48 | 23098 | 160.6 (+3) | WWWA | HOLD | 23146 | +48 | 129.9 / 130.0 (-16) | 23150 stopped |  |
| 12:50 | 23089 | 165.85 (+7) | WWqq | HOLD | 23146 | +57 | 133.9 / 133.7 (-14) | 23150 stopped |  |
| 12:54 | 23089 | 170.85 (+10) | WWqq | HOLD | 23122 | +33 | 150.1 / 150.1 (-3) | 23100 building |  |
| 12:55 | 23080 | 173.7 (+12) | WWWW | HOLD | 23122 | +42 | 148.8 / 148.9 (-4) | 23100 building |  |
| 12:58 | 23068 | 184.15 (+18) | WWWW | HOLD | 23116 | +48 | 152.4 / 152.2 (-2) | 23100 building | (c) high +23 % 12:57 |
| 13:00 | 23079 | 173.45 (+12) | WWWW | HOLD | 23116 | +37 | 153.3 / 152.9 (-2) | 23100 building |  |
| 13:02 | 23094 | 165.4 (+6) | WAWW | HOLD | 23116 | +22 | 149.1 / 148.6 (-4) | 23100 building |  |
| 13:03 | 23096 | 172.3 (+11) | WAWA | HOLD | 23116 | +20 | 154.9 / 154.7 (+0) | 23100 building |  |
| 13:05 | 23090 | 172.0 (+11) | WAWA | HOLD | 23116 | +26 | 155.5 / 155.4 (+0) | 23100 building |  |
| 13:09 | 23086 | 170.05 (+9) | WWWA | HOLD | 23116 | +30 | 153.5 / 153.0 (-2) | 23100 building |  |
| 13:10 | 23091 | 166.4 (+7) | WWWA | HOLD | 23116 | +25 | 148.5 / 148.0 (-5) | 23100 building |  |
| 13:12 | 23097 | 163.0 (+5) | WAWA | HOLD | 23116 | +19 | 153.7 / 153.3 (-1) | 23100 building |  |
| 13:15 | 23080 | 170.85 (+10) | WAWA | HOLD | 23116 | +36 | 153.4 / 153.0 (-2) | 23100 building |  |
| 13:20 | 23077 | 174.8 (+12) | WWWq | HOLD | 23116 | +39 | 153.7 / 153.4 (-1) | 23100 building |  |
| 13:22 | 23082 | 173.3 (+12) | WW?q | HOLD | 23116 | +34 | None / None | 23100  |  |
| 13:23 | 23073 | 174.65 (+12) | WWWq | HOLD | 23116 | +43 | 151.7 / 151.4 (-3) | 23100 building |  |
| 13:24 | 23077 | 175.2 (+13) | WWWq | HOLD | 23114 | +37 | 152.4 / 152.1 (-2) | 23100 building | (a) her exit 13:23:18 |
| 13:25 | 23072 | 180.0 (+16) | WWWq | HOLD | 23114 | +42 | 152.4 / 152.0 (-2) | 23100 building |  |
| 13:28 | 23076 | 176.8 (+14) | WWWq | HOLD | 23109 | +33 | 155.8 / 155.2 (+0) | 23100 building |  |
| 13:30 | 23084 | 173.45 (+12) | WWWq | HOLD | 23109 | +25 | 156.4 / 155.9 (+0) | 23100 building |  |
| 13:35 | 23072 | 180.2 (+16) | WWWq | HOLD | 23109 | +37 | 156.3 / 156.0 (+0) | 23100 building |  |
| 13:40 | 23080 | 177.55 (+14) | WWWq | HOLD | 23109 | +30 | 156.1 / 156.3 (+1) | 23100 building |  |
| 13:43 | 23080 | 173.15 (+11) | WAWq | HOLD | 23109 | +29 | 154.5 / 154.7 (+0) | 23100 building |  |
| 13:45 | 23086 | 171.0 (+10) | WAWq | HOLD | 23109 | +23 | 156.2 / 156.6 (+1) | 23100 building |  |
| 13:48 | 23090 | 168.55 (+8) | WAWA | HOLD | 23109 | +19 | 156.2 / 156.5 (+1) | 23100 building |  |
| 13:50 | 23084 | 169.65 (+9) | WAWA | HOLD | 23109 | +26 | 155.9 / 156.2 (+1) | 23100 building |  |
| 14:00 | 23109 | 151.3 (-3) | WqWA | HOLD | 23109 | -0 | 153.6 / 153.7 (-1) | 23100 building |  |
| 14:02 | 23156 | 124.0 (-20) | WAAq | FOLD | 23109 | -47 | 147.7 / 147.7 (-5) | 23100 off | (b) rev 6 FOLD · 23100 CE writers gave up 14:01, 2 |
| 14:07 | 23218 | 95.1 (-39) | qAWA | FOLD | 23109 | -109 | 156.6 / 156.2 (+1) | 23100 building | (c) low -41 % 14:06 |
| 14:30 | 23192 | 107.45 (-31) | AAWq | FOLD | 23109 | -83 | 153.6 / 153.4 (-1) | 23100 building |  |
| 15:00 | 23182 | 105.75 (-32) | qAWq | FOLD | 23109 | -73 | 149.3 / 148.3 (-5) | 23100 building |  |

#### NIFTY-23000PE-long-093027 · 2026-09-28 · long 23000 PE @ 120.4 · mark 09:30:27 (fut 22941.4) · her exit 10:20:27

| min | fut | prem (% of entry) | Z F O V | headline | G | fut to G (pts) | at G: shown / corrected (%) | W | marks |
|---|---|---|---|---|---|---|---|---|---|
| 09:31 | 22945 | 122.0 (+1) | WWWW | HOLD | 22997 | +52 | 87.0 / 90.5 (-25) | 22950 building |  |
| 09:32 | 22950 | 121.55 (+1) | WWWW | HOLD | 22997 | +47 | 92.1 / 96.1 (-20) | 22950 building | (c) low -3 % 09:31 |
| 09:35 | 22932 | 127.45 (+6) | WWWW | HOLD | 22997 | +65 | 87.7 / 91.6 (-24) | 22950 building |  |
| 09:38 | 22905 | 153.7 (+28) | AWWW | HOLD | 22997 | +92 | 97.0 / 101.6 (-16) | 22950 building |  |
| 09:39 | 22897 | 156.05 (+30) | WqWW | HOLD | 22997 | +100 | 91.6 / 95.3 (-21) | 22950 building |  |
| 09:40 | 22902 | 154.4 (+28) | WqWW | HOLD | 22997 | +95 | 94.2 / 98.5 (-18) | 22950 building |  |
| 09:43 | 22903 | 151.9 (+26) | WAWW | HOLD | 22997 | +94 | 97.0 / 101.3 (-16) | 22950 building |  |
| 09:45 | 22896 | 156.05 (+30) | WAWW | HOLD | 22997 | +100 | 94.1 / 97.5 (-19) | 22950 building |  |
| 09:48 | 22924 | 142.3 (+18) | WAWq | HOLD | 22997 | +72 | 97.2 / 101.0 (-16) | 22950 building |  |
| 09:50 | 22925 | 141.5 (+18) | AAWq | HOLD | 22997 | +72 | 89.9 / 93.7 (-22) | 22950 building |  |
| 09:51 | 22923 | 144.3 (+20) | WAWq | HOLD | 22997 | +74 | 94.3 / 98.2 (-18) | 22950 building |  |
| 09:55 | 22916 | 142.4 (+18) | WAWq | HOLD | 22997 | +81 | 91.1 / 94.9 (-21) | 22950 building |  |
| 09:57 | 22915 | 140.85 (+17) | AAWW | HOLD | 22997 | +82 | 91.5 / 94.6 (-21) | 22950 building |  |
| 09:59 | 22921 | 136.9 (+14) | A?WW | HOLD | 22997 | +76 | 91.9 / 94.6 (-21) | 22950 building |  |
| 10:00 | 22915 | 138.9 (+15) | A?WW | HOLD | 22997 | +82 | 92.4 / 95.0 (-21) | 22950 building |  |
| 10:01 | 22915 | 143.3 (+19) | W?WW | HOLD | 22997 | +82 | 96.1 / 98.7 (-18) | 22950 building |  |
| 10:03 | 22918 | 137.75 (+14) | A?WW | HOLD | 22997 | +80 | 88.8 / 90.9 (-25) | 22950 building |  |
| 10:05 | 22916 | 140.0 (+16) | W?WW | HOLD | 22997 | +81 | 92.3 / 93.6 (-22) | 22950 building |  |
| 10:08 | 22904 | 147.0 (+22) | AWWW | HOLD | 22969 | +65 | 107.9 / 108.8 (-10) | 22950 building |  |
| 10:09 | 22904 | 149.2 (+24) | AWWW | HOLD | 22959 | +55 | 114.9 / 115.6 (-4) | 22950 building |  |
| 10:10 | 22900 | 154.6 (+28) | WWWW | HOLD | 22959 | +59 | 114.5 / 115.2 (-4) | 22950 building |  |
| 10:15 | 22904 | 149.65 (+24) | WWWW | HOLD | 22959 | +55 | 113.8 / 114.2 (-5) | 22950 building |  |
| 10:17 | 22897 | 151.45 (+26) | WWWq | HOLD | 22959 | +62 | 113.6 / 113.8 (-5) | 22950 building |  |
| 10:18 | 22876 | 166.0 (+38) | WWWq | HOLD | 22927 | +51 | 132.4 / 132.6 (+10) | 22900 building |  |
| 10:20 | 22886 | 158.45 (+32) | WWWW | HOLD | 22927 | +41 | 134.0 / 134.3 (+12) | 22900 building |  |
| 10:21 | 22898 | 154.65 (+28) | WWWW | HOLD | 22927 | +29 | 133.9 / 134.1 (+11) | 22900 building | (a) her exit 10:20:27 |
| 10:23 | 22886 | 160.7 (+34) | AAWW | HOLD | 22927 | +41 | 132.5 / 132.7 (+10) | 22900 building |  |
| 10:25 | 22879 | 166.75 (+38) | qAWq | HOLD | 22927 | +48 | 134.5 / 134.5 (+12) | 22900 building |  |
| 10:30 | 22881 | 162.65 (+35) | qWWq | HOLD | 22926 | +45 | 137.4 / 137.4 (+14) | 22900 building |  |
| 10:35 | 22890 | 165.55 (+38) | qWWq | HOLD | 22926 | +36 | 132.6 / 132.8 (+10) | 22900 building |  |
| 10:40 | 22876 | 168.8 (+40) | qWWq | HOLD | 22926 | +50 | 134.2 / 134.9 (+12) | 22900 building |  |
| 10:44 | 22872 | 172.75 (+44) | qqWq | HOLD | 22926 | +54 | 134.6 / 135.4 (+12) | 22900 building |  |
| 10:45 | 22870 | 170.1 (+41) | qqWq | HOLD | 22926 | +56 | 131.3 / 131.9 (+10) | 22900 building |  |
| 10:50 | 22870 | 173.95 (+44) | qqWq | HOLD | 22926 | +56 | 133.8 / 134.3 (+12) | 22900 building |  |
| 11:00 | 22884 | 166.0 (+38) | qqWq | HOLD | 22926 | +42 | 137.6 / 138.4 (+15) | 22900 building |  |
| 11:07 | 22874 | 168.8 (+40) | qWWq | HOLD | 22925 | +52 | 132.9 / 133.6 (+11) | 22900 building |  |
| 11:30 | 22883 | 168.6 (+40) | qqWW | HOLD | 22925 | +42 | 133.4 / 139.0 (+15) | 22900 building |  |
| 12:00 | 22867 | 174.0 (+44) | qqAq | HOLD | 22925 | +58 | 128.8 / 132.9 (+10) | 22900 off |  |
| 12:30 | 22909 | 148.2 (+23) | qAWA | HOLD | 22925 | +16 | 132.0 / 136.8 (+14) | 22900 building |  |
| 13:00 | 22879 | 165.25 (+37) | qqqq | HOLD | 22925 | +46 | 125.5 / 130.1 (+8) | 22900 stopped |  |
| 13:10 | 22865 | 172.6 (+43) | AWWq | HOLD | 22913 | +48 | 135.3 / 138.9 (+15) | 22900 building |  |
| 13:30 | 22900 | 152.05 (+26) | qqWq | HOLD | 22913 | +14 | 140.3 / 143.1 (+19) | 22900 building |  |
| 14:00 | 22894 | 156.1 (+30) | qqAW | HOLD | 22913 | +19 | 134.0 / 139.7 (+16) | 22900 off |  |
| 14:30 | 22823 | 207.15 (+72) | qqAq | HOLD | 22913 | +90 | 134.9 / 139.4 (+16) | 22900 off |  |
| 14:31 | 22840 | 197.0 (+64) | qWWq | HOLD | 22844 | +4 | 187.6 / 192.5 (+60) | 22850 building |  |
| 14:39 | 22795 | 231.7 (+92) | WWWq | HOLD | 22831 | +36 | 198.4 / 203.0 (+69) | 22800 building | (c) high +97 % 14:38 |
| 15:00 | 22820 | 205.35 (+71) | qqWq | HOLD | 22831 | +10 | 192.5 / 197.7 (+64) | 22800 building |  |

#### NIFTY-22800PE-long-091807 · 2026-09-29 · long 22800 PE @ 113.95 · mark 09:18:07 (fut 22721.5) · her exit 09:35:26

| min | fut | prem (% of entry) | Z F O V | headline | G | fut to G (pts) | at G: shown / corrected (%) | W | marks |
|---|---|---|---|---|---|---|---|---|---|
| 09:19 | 22702 | 130.65 (+15) | qqW? | HOLD | 22805 | +103 | 65.2 / 65.6 (-42) | 22800 building |  |
| 09:20 | 22702 | 131.65 (+16) | qWW? | HOLD | 22734 | +32 | 103.7 / 104.9 (-8) | 22750 building |  |
| 09:21 | 22692 | 137.3 (+20) | AAW? | HOLD | 22734 | +42 | 102.5 / 104.1 (-9) | 22750 building |  |
| 09:23 | 22690 | 146.1 (+28) | qWW? | HOLD | 22724 | +34 | 112.6 / 114.0 (+0) | 22700 building |  |
| 09:25 | 22688 | 140.45 (+23) | qWW? | HOLD | 22724 | +36 | 106.2 / 108.0 (-5) | 22700 building |  |
| 09:28 | 22668 | 158.1 (+39) | qWWq | HOLD | 22724 | +56 | 110.7 / 113.5 (+0) | 22700 building |  |
| 09:30 | 22641 | 177.2 (+56) | qWWq | HOLD | 22724 | +83 | 110.4 / 113.2 (-1) | 22700 building |  |
| 09:32 | 22639 | 178.45 (+57) | qqWq | HOLD | 22724 | +85 | 108.6 / 111.4 (-2) | 22700 building |  |
| 09:33 | 22627 | 186.3 (+64) | qWWq | HOLD | 22711 | +84 | 122.3 / 125.2 (+10) | 22700 building |  |
| 09:35 | 22628 | 185.3 (+63) | AAWq | HOLD | 22711 | +84 | 119.0 / 121.7 (+7) | 22700 building |  |
| 09:36 | 22615 | 197.2 (+73) | AAWq | HOLD | 22711 | +96 | 125.0 / 127.7 (+12) | 22700 building | (a) her exit 09:35:26 |
| 09:37 | 22596 | 215.65 (+89) | AAWW | HOLD | 22711 | +115 | 121.4 / 123.9 (+9) | 22700 building |  |
| 09:38 | 22586 | 222.15 (+95) | qWWW | HOLD | 22654 | +68 | 171.1 / 174.2 (+53) | 22650 building |  |
| 09:39 | 22600 | 217.25 (+91) | qWWW | HOLD | 22654 | +54 | 167.6 / 170.6 (+50) | 22650 building | (c) high +101 % 09:38 |
| 09:40 | 22591 | 223.15 (+96) | qWWW | HOLD | 22654 | +63 | 167.7 / 170.7 (+50) | 22650 building |  |
| 09:43 | 22635 | 180.65 (+58) | qWWq | HOLD | 22654 | +19 | 161.2 / 163.9 (+44) | 22650 building |  |
| 09:45 | 22621 | 190.95 (+68) | qWWq | HOLD | 22654 | +33 | 160.8 / 163.2 (+43) | 22650 building |  |
| 09:50 | 22614 | 203.7 (+79) | qWWA | HOLD | 22654 | +40 | 162.9 / 165.2 (+45) | 22650 building |  |
| 09:51 | 22613 | 209.6 (+84) | AWWA | HOLD | 22654 | +41 | 168.5 / 171.5 (+51) | 22650 building |  |
| 09:53 | 22614 | 204.8 (+80) | AAWA | HOLD | 22654 | +40 | 167.9 / 170.7 (+50) | 22650 building |  |
| 09:55 | 22620 | 197.3 (+73) | AAWA | HOLD | 22654 | +34 | 163.6 / 166.3 (+46) | 22650 building |  |
| 09:58 | 22622 | 192.6 (+69) | qAWA | HOLD | 22654 | +32 | 163.3 / 166.0 (+46) | 22650 building |  |
| 10:00 | 22622 | 198.0 (+74) | qAWA | HOLD | 22654 | +32 | 167.8 / 170.8 (+50) | 22650 building |  |
| 10:03 | 22604 | 206.55 (+81) | AAWA | HOLD | 22654 | +50 | 163.9 / 167.6 (+47) | 22650 building |  |
| 10:05 | 22608 | 209.45 (+84) | AWWA | HOLD | 22653 | +45 | 166.1 / 170.2 (+49) | 22650 building |  |
| 10:30 | 22618 | 203.2 (+78) | qqWq | HOLD | 22653 | +35 | 168.6 / 173.1 (+52) | 22650 building |  |
| 11:00 | 22630 | 186.0 (+63) | qqWq | HOLD | 22653 | +23 | 163.2 / 166.2 (+46) | 22650 building |  |
| 11:12 | 22666 | 153.45 (+35) | qAAA | FOLD | 22653 | -13 | 165.1 / 168.2 (+48) | 22650 off | (b) rev 6 FOLD · 22650 CE writers gave up 11:10, 2 |
| 11:30 | 22710 | 121.25 (+6) | qAAA | FOLD | 22653 | -57 | 164.3 / 167.8 (+47) | 22650 off |  |
| 12:00 | 22737 | 97.3 (-15) | qAAA | FOLD | 22653 | -84 | 162.4 / 161.0 (+41) | 22650 off |  |
| 12:08 | 22762 | 79.5 (-30) | qAAA | FOLD | 22653 | -109 | 161.8 / 161.2 (+41) | 22650 off | (c) low -30 % 12:07 |
| 12:30 | 22692 | 134.5 (+18) | qAAW | FOLD | 22653 | -39 | 152.0 / 155.5 (+36) | 22650 off |  |
| 13:00 | 22700 | 122.2 (+7) | qAAW | FOLD | 22653 | -47 | 154.6 / 162.1 (+42) | 22650 off |  |
| 13:30 | 22674 | 147.4 (+29) | WAAq | FOLD | 22653 | -21 | 156.4 / 164.1 (+44) | 22650 off |  |
| 13:32 | 22672 | 142.5 (+25) | WWWq | FOLD | 22600 | -72 | 203.8 / 211.6 (+86) | 22600 building |  |
| 13:44 | 22654 | 162.6 (+43) | WWWq | FOLD | 22599 | -55 | 204.9 / 213.9 (+88) | 22600 building |  |
| 14:00 | 22679 | 141.0 (+24) | WAAA | FOLD | 22599 | -80 | 206.2 / 215.7 (+89) | 22600 off |  |
| 14:30 | 22674 | 132.1 (+16) | qAAq | FOLD | 22599 | -75 | 202.0 / 202.9 (+78) | 22600 off |  |
| 15:00 | 22678 | 126.05 (+11) | qAAA | FOLD | 22599 | -78 | 202.1 / 200.8 (+76) | 22600 off |  |

#### NIFTY-22750CE-long-101012 · 2026-09-30 · long 22750 CE @ 164.7 · mark 10:10:12 (fut 22864.9) · her exit 11:16:50

| min | fut | prem (% of entry) | Z F O V | headline | G | fut to G (pts) | at G: shown / corrected (%) | W | marks |
|---|---|---|---|---|---|---|---|---|---|
| 10:11 | 22869 | 164.7 (+0) | -qWA | HOLD | 22769 | +100 | 152.1 / 113.1 (-31) | 22700 building |  |
| 10:13 | 22869 | 164.0 (-0) | AqWA | HOLD | 22769 | +100 | 154.8 / 115.3 (-30) | 22700 building |  |
| 10:15 | 22880 | 171.4 (+4) | AqWA | HOLD | 22769 | +111 | 152.0 / 113.0 (-31) | 22700 building |  |
| 10:18 | 22884 | 171.25 (+4) | WqWA | HOLD | 22769 | +115 | 151.1 / 112.7 (-32) | 22700 building |  |
| 10:20 | 22881 | 174.1 (+6) | WqWA | HOLD | 22769 | +112 | 153.9 / 115.0 (-30) | 22700 building |  |
| 10:22 | 22887 | 175.3 (+6) | WqWq | HOLD | 22769 | +118 | 151.5 / 113.0 (-31) | 22700 building |  |
| 10:25 | 22882 | 169.9 (+3) | WqWq | HOLD | 22769 | +113 | 149.6 / 111.0 (-33) | 22700 building |  |
| 10:30 | 22880 | 170.0 (+3) | WqWq | HOLD | 22769 | +111 | 151.4 / 112.5 (-32) | 22700 building |  |
| 10:35 | 22828 | 144.95 (-12) | WqWq | HOLD | 22769 | +59 | 156.3 / 116.3 (-29) | 22700 building |  |
| 10:36 | 22824 | 141.15 (-14) | WqAq | HOLD | 22769 | +54 | 154.9 / 115.3 (-30) | 22700 off | (iv-g) GAVE UP 10:35:05 |
| 10:40 | 22839 | 148.8 (-10) | WqAq | HOLD | 22769 | +70 | 153.7 / 115.0 (-30) | 22700 off |  |
| 10:45 | 22818 | 139.9 (-15) | WqAA | HOLD | 22769 | +48 | 156.2 / 117.0 (-29) | 22700 off |  |
| 10:50 | 22821 | 142.65 (-13) | WqAA | HOLD | 22769 | +52 | 156.4 / 118.1 (-28) | 22700 off |  |
| 10:55 | 22827 | 144.0 (-13) | WqAA | HOLD | 22769 | +58 | 154.0 / 116.0 (-30) | 22700 off |  |
| 11:00 | 22800 | 134.35 (-18) | WqAA | HOLD | 22769 | +31 | 158.2 / 119.9 (-27) | 22700 off |  |
| 11:05 | 22835 | 145.75 (-12) | WqAA | HOLD | 22769 | +66 | 149.3 / 112.3 (-32) | 22700 off |  |
| 11:10 | 22826 | 139.5 (-15) | WqAA | HOLD | 22769 | +58 | 153.0 / 114.8 (-30) | 22700 off |  |
| 11:12 | 22822 | 136.65 (-17) | WWWA | HOLD | 22803 | +20 | 172.2 / 130.5 (-21) | 22750 building |  |
| 11:15 | 22802 | 132.05 (-20) | WWWA | HOLD | 22803 | -0 | 174.8 / 133.1 (-19) | 22750 building |  |
| 11:17 | 22785 | 125.45 (-24) | WAAA | FOLD | 22803 | -18 | 176.7 / 135.4 (-18) | 22750 off | (a) her exit 11:16:50; (b) rev 6 FOLD · 22803 accepted · 11:16 |
| 11:20 | 22793 | 127.7 (-22) | WAAA | FOLD | 22803 | -10 | 173.9 / 132.7 (-19) | 22750 off |  |
| 11:25 | 22790 | 127.15 (-23) | WAAA | FOLD | 22803 | -13 | 173.7 / 132.9 (-19) | 22750 off |  |
| 11:30 | 22820 | 136.2 (-17) | WAAA | FOLD | 22803 | +16 | 167.5 / 127.9 (-22) | 22750 off |  |
| 11:35 | 22814 | 137.9 (-16) | WAAA | FOLD | 22803 | +11 | 173.4 / 132.6 (-19) | 22750 off |  |
| 11:40 | 22820 | 136.85 (-17) | WAAA | FOLD | 22803 | +17 | 175.3 / 133.4 (-19) | 22750 off |  |
| 11:45 | 22825 | 139.95 (-15) | WAAA | FOLD | 22803 | +22 | 169.7 / 128.9 (-22) | 22750 off |  |
| 12:00 | 22844 | 150.35 (-9) | WAAA | FOLD | 22803 | +41 | 168.9 / 129.4 (-21) | 22750 off |  |
| 12:27 | 22864 | 160.65 (-2) | WWWq | FOLD | 22821 | +43 | 181.5 / 139.3 (-15) | 22750 building |  |
| 12:30 | 22860 | 154.15 (-6) | WWWq | FOLD | 22821 | +39 | 174.0 / 133.9 (-19) | 22750 building |  |
| 12:49 | 22934 | 202.3 (+23) | WqWW | FOLD | 22821 | +113 | 180.5 / 139.0 (-16) | 22750 building | (c) high +23 % 12:48 |
| 13:00 | 22914 | 183.8 (+12) | WqWA | FOLD | 22821 | +93 | 177.5 / 136.2 (-17) | 22750 building |  |
| 13:30 | 22884 | 167.5 (+2) | WqWA | FOLD | 22821 | +63 | 172.8 / 132.6 (-19) | 22750 building |  |
| 14:00 | 22848 | 148.05 (-10) | WWAA | FOLD | 22821 | +27 | 174.1 / 134.0 (-19) | 22750 off |  |
| 14:30 | 22747 | 108.15 (-34) | qAAA | FOLD | 22821 | -74 | 181.8 / 144.0 (-13) | 22750 off |  |
| 14:44 | 22698 | 91.8 (-44) | qAAA | FOLD | 22821 | -123 | 185.3 / 147.7 (-10) | 22750 off | (c) low -45 % 14:43 |
| 15:00 | 22719 | 97.45 (-41) | qAAq | FOLD | 22821 | -102 | 181.1 / 145.6 (-12) | 22750 off |  |

## 3. Where rev 6's word misleads her (rows, not rates)

### D1. HOLD while 2 or more of her four reads are AGAINST, price is against her and the premium bleeds

Condition on the minute rows: the headline is HOLD, at least 2 chips are AGAINST, the future is ≥ w against her entry, and the premium is below entry. **224 minute rows on 17 of 45 replays** [M]. On 14 of those 17, rev 6's FOLD came later and at a lower premium than at the first such minute. On 2 it came at a slightly higher premium (Z 09-24 12:00, Z 09-30 11:27). On 1 it never came: Z 09-30 10:27 SELL, which went on to +55 % by 15:00.

| replay | minutes | first such minute | worst under HOLD | against | rev 6 FOLD |
|---|---|---|---|---|---|
| **30 Sep 22750 CE (hers)** | **27** | **10:45, -15 %** | -18 % 11:00 | **OI, VPIN** | 11:16, -23 % |
| A3 | 23 | 11:42, -5 % | -13 % 12:04 | flow, VPIN | 12:04, -12 % |
| Z 09-23 11:15 SELL | 22 | 11:42, -4 % | -12 % 12:04 | flow, VPIN | 12:04, -11 % |
| A2 · Z 09-22 11:12 · Z 09-22 12:03 (one 22 Sep afternoon) | 21 each | 12:50, -19 / -57 / -26 % | -42 / -71 / -47 % | flow, OI | 13:51, -42 / -71 / -47 % |
| Z 09-30 10:27 SELL | 18 | 12:38, -10 % | -21 % 12:49 | flow, OI | none; +55 % at 15:00, +73 % at 14:43 |
| A6 | 14 | 09:34, -6 % | -17 % | flow, VPIN | 10:16, -17 % |
| Z 09-24 12:00 | 13 | 12:36, -9 % | -9 % | flow, OI, VPIN | 12:48, -8 % |
| Z 09-22 09:39 | 12 | 10:34, -38 % | -53 % | flow, OI | 10:45, -53 % |
| 25 Sep 23200 PE (hers) · Z 09-28 09:48 · Z 09-25 09:54 · 25 Sep 23100 CE (hers) · A5 · Z 09-24 13:30 · Z 09-30 11:27 | 8 · 9 · 6 · 5 · 2 · 1 · 1 | -5 · -2 · -2 · -4 · -4 · -10 · -4 % | | | |

**30 Sep, hers:**

- From 10:35 the clause under HOLD read "against you: OI since 10:35". From 10:44 it read "against you: OI since 10:35, VPIN since 10:44 · behind you: zone". Flow was QUIET ("tiring 38 min").
- By her own rule (OI and VPIN not behind her), that is a fold at about -15 %. The word said HOLD for 41 minutes.

### D2. A give-up so far that the premium there is a -30 % loss, and a premium-at-G number that was wrong

- **13 of 45 replays seed a G whose corrected premium is -30 % or worse at the mark** [I]:
  - hers on 29 Sep: 103 pts, -42 %;
  - hers on 30 Sep: 100 pts, -31 %;
  - A2 -47 %, R-A2 -58 %;
  - zone 22 Sep 09:39 / 11:12 / 12:03: -47 / -67 / -54 %;
  - zone 23 Sep 09:57 -40 %, 24 Sep 14:30 -33 %, 25 Sep 09:54 -41 %, 29 Sep 12:18 -34 %, 30 Sep 10:27 -31 %, 1 Oct 13:00 -32 %.
- On the 22 Sep expiry, -50 % is a few points of a 40 to 50 rupee premium.
- **The DESK's "at your give-up" number is mis-priced by the basis (a defect, not a rule).**
  - `fold._prem_at` interpolates the chain at K′ = K + F* − px. But G (and A, passed as `ak + bas`) is a futures-chart price, and F* is the options' forward (future − basis).
  - The strike with the moneyness K would have with the future at G is K + (fut − G) = K + F* + basis − G.
  - Checked against what actually happened: for each minute, I compared the predicted premium at G with the premium when the future later traded within 3 pts of that G (≤ 30 min later) [M]:

| day | basis | minute rows | median abs error, shown | median abs error, corrected |
|---|---|---|---|---|
| 22 Sep | 15 | 522 | 5.4 | 1.8 |
| 23 / 24 / 25 Sep | -2 / -2 / 0 | 479 / 367 / 885 | 1.8 / 2.4 / 1.9 | 1.5 / 2.5 / 2.0 |
| 28 / 29 Sep | 6 / 6 | 383 / 198 | 4.4 / 7.1 | 2.3 / 3.4 |
| **30 Sep** | **72** | 277 | **34.0** | **2.5** |
| **1 Oct** | **65** | 68 | **29.3** | **2.8** |

- **What she saw on 30 Sep:**
  - At the mark, "at your give-up" read **152.1 (-8 %)**. The corrected value was **113.1 (-31 %)**.
  - At 11:16:33 the future was at the give-up and the call traded 127.55, yet the screen read **178.1**, above her entry premium.
  - The direction of the error: a call's give-up looks cheaper to hit than it is, and a put's looks dearer. Zone 30 Sep 11:27 showed +25 % at G where the corrected value was -4 %.
  - The same error hits the wall-ahead premium (at A) and IF YOU WERE IN. No test pins the value (`test_fold.py` checks presence only).

### D3. FOLD landing at the low

36 replays have a rev 6 FOLD: 24 at-entry acceptance, 6 flow + OI, 4 expiry afternoon, 2 held breach.

- **6 landed at a local low.** That means the premium was within 3 points of its worst over the next 30 minutes, and at least 10 points higher within 60 minutes:
  - **30 Sep, hers:** -23 % at 11:16, -5 % by 12:03, then +23 % at 12:48 before -45 % at 14:43;
  - A5: -10 %, then +12 % by 10:13;
  - Z 09-25 13:00: -9 %, then +83 % by 14:06;
  - Z 09-30 09:30: -19 %, then +17 %;
  - Z 09-30 11:00: -14 %, then +5 %;
  - Z 10-01 10:12: -11 %, then +14 %, and +196 % by 14:05.
- **Rev 6's own at-entry falsifier** ("trading comes back w inside G within 20 min", the whipsaw column) **is met on 12 of the 24 at-entry FOLDs, and not met on the other 12** [M, minute rows]. Replay rows don't count toward §6.3's kill; they show the column is already even.

### D4. G stepping toward price on a small win while she is losing

The material rows are at entry, with the future below her entry:

- **30 Sep, hers, 11:11:**
  - "buyers won at 22826" moved G 22769 → 22803 at -15 %.
  - **In the same second** the 22700 PE event was withdrawn ("your side won again") and W swapped to the thinner 22750 PE (37.4L against 119L).
  - The OI chip flipped **AGAINST → WITH** ("writers adding").
  - Five minutes later the 22750 PE writers left (-9.4 % of 38L) and 22803 was accepted: FOLD at -23 %, the local low.
- **Z 09-30 11:00:** the same moment, -6 % → FOLD at -14 % at 11:16.
- **Z 09-22 11:12, 12:18:** 23310 → 23342 at -41 % → FOLD at -71 % at 13:51.
- After an exit or a FOLD, the same W swap flipped OI AGAINST → WITH on two more rows: 30 Sep 12:26 and Z 09-22 11:12 at 14:33.
- Stopping the step (candidate v) is no cure. It changes 5 rows and leaves a lower premium at exit on 3 of them (hers on 30 Sep: -23 → -34 %). **The harm is not the tighter G. It is the W swap that erases "OI against" in the same second.**

## 4. The candidates, side by side, on every replay

- Each cell is the exit the rule gives: its first speak, else rev 6's FOLD (every candidate is added to rev 6), else 15:00. "=" means the same as rev 6.
- (iii) and (v) are full engine re-runs (subclasses in `harness/replay7.py`). The others are read off rev 6's own event rows, which are exact up to the first speak.
- **(i)** pre-trail, a live OI event on W and the future ≥ w against her → FOLD.
- **(ii-F)** her rule literally: at entry, HOLD with ≥ 2 reads AGAINST and the future ≥ w against → FOLD.
- **(iii)** at the mark, G no further than the future level where the premium would be -25 % (h).
- **(iv-g) recommended:** (i) only when the OI event was **born while she was ≥ w under water**, and only while **neither FLOW nor VPIN is WITH** her.
- **(iv-b)** (iv-g) without the flow guard.
- **(iv-a)** (i) plus FLOW or VPIN AGAINST.
- **(v)** at entry and under water, a win by her side does not move G.
- **(ii) AT RISK** is a word, not an exit; see §4.2.


| # | replay | rev 6 | (i) OI + price | (ii-F) 2 of 4 | (iii) cap -25 % | **(iv-g) GAVE UP** | (iv-b) no flow guard | (iv-a) (i)+flow | (v) no step | 15:00 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 23100CE 120121 | -10 12:47 | -3 12:07 | -3 12:07 | = | -3 12:07 | -3 12:07 | -3 12:07 | = | +29 |
| 2 | 23200PE 120528 | -17 14:01 | = | -5 12:11 | = | = | = | = | = | -32 |
| 3 | 23000PE 093027 | +71 15:00 | = | = | = | = | = | = | = | +71 |
| 4 | 22800PE 091807 | +25 11:11 | = | = | = | = | = | = | = | +11 |
| 5 | 22750CE 101012 | -23 11:16 | -14 10:35 | -15 10:44 | = | -14 10:35 | -14 10:35 | -15 10:44 | -34 14:29 | -41 |
| 6 | A1 | +199 14:12 | = | = | = | = | = | = | = | +108 |
| 7 | A2 | -42 13:51 | -14 12:46 | -15 12:49 | = | -15 12:49 | -14 12:46 | -15 12:49 | = | -11 |
| 8 | R-A2 | -43 15:00 | = | = | = | = | = | = | = | -43 |
| 9 | A3 | -12 12:04 | -13 12:03 | -6 11:41 | = | -13 12:03 | -13 12:03 | -13 12:03 | -8 15:00 | -8 |
| 10 | H1 | +98 14:39 | = | = | = | = | = | = | = | +98 |
| 11 | A4 | +7 10:09 | = | = | = | = | = | = | = | -26 |
| 12 | A5 | -10 09:47 | = | -4 09:41 | = | = | = | = | = | +20 |
| 13 | H2 | +71 15:00 | = | = | = | = | = | = | = | +71 |
| 14 | A6 | -17 10:16 | = | -5 09:33 | -18 09:38 | = | = | = | = | -61 |
| 15 | Z 09-22 09:39 BUY | -53 10:45 | -34 10:31 | -38 10:33 | -39 10:35 | -34 10:31 | -34 10:31 | -38 10:33 | = | -85 |
| 16 | Z 09-22 09:57 SELL | +240 14:12 | = | = | = | = | = | = | = | +137 |
| 17 | Z 09-22 11:12 BUY | -71 13:51 | -44 11:57 | -55 12:49 | -36 11:47 | -44 11:57 | -44 11:57 | -55 12:49 | -79 14:02 | -58 |
| 18 | Z 09-22 12:03 BUY | -47 13:51 | -22 12:46 | -22 12:49 | = | -22 12:49 | -22 12:46 | -22 12:49 | = | -18 |
| 19 | Z 09-22 14:09 BUY | +65 14:41 | = | = | = | = | = | = | = | +42 |
| 20 | Z 09-23 09:57 BUY | +14 14:45 | = | = | = | = | = | = | = | +9 |
| 21 | Z 09-23 11:15 SELL | -11 12:04 | -12 12:03 | -5 11:41 | = | -12 12:03 | -12 12:03 | -12 12:03 | = | -7 |
| 22 | Z 09-23 12:24 SELL | -5 14:17 | = | = | = | = | = | = | = | +5 |
| 23 | Z 09-24 09:57 BUY | -13 11:58 | -8 11:25 | = | = | = | = | = | = | -35 |
| 24 | Z 09-24 10:30 BUY | -11 11:58 | -2 11:16 | = | = | = | = | = | = | -33 |
| 25 | Z 09-24 12:00 BUY | -8 12:48 | -9 12:35 | -9 12:34 | = | -9 12:35 | -9 12:35 | -9 12:35 | -14 13:26 | -29 |
| 26 | Z 09-24 13:00 BUY | -13 13:27 | -10 13:27 | -10 13:27 | = | -10 13:27 | -10 13:27 | -10 13:27 | = | -25 |
| 27 | Z 09-24 13:30 BUY | -11 13:44 | = | -9 13:43 | = | = | = | = | = | -18 |
| 28 | Z 09-24 14:00 BUY | -6 14:07 | = | = | = | = | = | = | = | -3 |
| 29 | Z 09-24 14:30 BUY | +4 15:00 | = | = | = | = | = | = | = | +4 |
| 30 | Z 09-25 09:33 SELL | +2 10:09 | = | = | = | = | = | = | = | -29 |
| 31 | Z 09-25 09:54 BUY | -12 12:47 | -1 10:37 | +0 10:02 | = | = | -1 10:37 | -10 12:43 | = | +27 |
| 32 | Z 09-25 13:00 BUY | -9 13:35 | = | = | = | = | = | = | = | +48 |
| 33 | Z 09-28 09:48 BUY | -16 10:18 | = | -3 10:07 | = | = | = | = | = | -54 |
| 34 | Z 09-28 14:45 BUY | +2 15:00 | = | = | = | = | = | = | = | +2 |
| 35 | Z 09-29 09:39 BUY | -25 10:15 | = | = | = | = | = | = | = | +13 |
| 36 | Z 09-29 12:18 SELL | +64 13:34 | = | = | = | = | = | = | = | +28 |
| 37 | Z 09-30 09:30 SELL | -19 10:22 | = | = | = | = | = | = | = | +31 |
| 38 | Z 09-30 10:27 SELL | +55 15:00 | -11 12:39 | -11 12:39 | = | = | = | -11 12:39 | = | +55 |
| 39 | Z 09-30 11:00 BUY | -14 11:16 | = | = | = | = | = | = | -9 14:16 | -34 |
| 40 | Z 09-30 11:27 BUY | -1 14:16 | = | = | = | = | = | = | = | -28 |
| 41 | Z 09-30 13:03 SELL | +77 15:00 | = | = | = | = | = | = | = | +77 |
| 42 | Z 09-30 14:45 BUY | -2 15:00 | = | = | = | = | = | = | = | -2 |
| 43 | Z 10-01 10:12 SELL | -11 10:36 | = | = | = | = | = | = | = | +81 |
| 44 | Z 10-01 10:39 SELL | +92 15:00 | = | = | = | = | = | = | = | +92 |
| 45 | Z 10-01 13:00 BUY | -29 13:59 | = | = | -27 13:59 | = | = | = | = | +3 |

### 4.1 What each candidate changes

"Changes" means it speaks ≥ 2 minutes before rev 6's FOLD, or speaks where rev 6 never folds.

| candidate | rows changed | premium at exit higher than rev 6 | lower | the rows that decide it |
|---|---|---|---|---|
| (i) OI + price | 11 | 9 | 2 | **Z 09-30 10:27 SELL +55 → -11** (the 22900 CE writers bled 7.6 % at 12:06 while she was +8 %, i.e. covering on her win; the price came against her 33 min later; then +73 % at 14:43) |
| (ii-F) 2 of 4 | 15 | 13 | 2 | the same Z 09-30 10:27 kill; and 8 of its 15 fire on ZONE + FLOW or FLOW + VPIN with no OI, at 0 to -9 % (A5, A6, A3, 23200 PE hers, Z 09-25 09:54, Z 09-28 09:48, Z 09-23 11:15, Z 09-24 12:00) |
| (iii) cap -25 % | 3 (+1 same minute) | 2 | 1 | A6 -17 → -18 at 09:38, premium back to -8 % within 20 min; never touches 30 Sep |
| **(iv-g) GAVE UP** | **7** | **6** | **1 (by 1 point)** | none killed: it never cuts a trade rev 6 held to a gain |
| (iv-b) no flow guard | 8 | 7 | 1 | adds Z 09-25 09:54 at -1 % with FLOW and VPIN WITH; price was back over entry at 10:40, 3 min later |
| (iv-a) (i) + flow | 9 | 7 | 2 | the same Z 09-30 10:27 kill |
| (v) no G step | 5 | 2 | 3 | hers 30 Sep -23 → -34; Z 09-22 11:12 -71 → -79; Z 09-24 12:00 -8 → -14 |

**(iv-g)'s seven rows**, with what the premium did after it spoke [M]:

| replay | rev 6 | (iv-g) | OI event it acted on | after: worst / best / +20 min / 15:00 | its falsifier (20 min) |
|---|---|---|---|---|---|
| 25 Sep 23100 CE (hers) | -10 12:47 | **-3 12:07** | 23100 PE 193.7L → 187.8L (-3.1 %, z 3.1) | -21 / +59 (14:06) / -1 / +29 | real |
| **30 Sep 22750 CE (hers)** | -23 11:16 | **-14 10:35** | 22700 PE 119.4L → 113.0L (-5.4 %, z 3.1) | -45 / +23 (12:48) / -12 / -41 | real |
| A2 | -42 13:51 | **-15 12:49** | 23350 PE 281.7L → 271.3L (-3.7 %); waited 3 min for FLOW to leave WITH | -61 / +78 (14:21) / -30 / -11 | real |
| Z 09-22 09:39 | -53 10:45 | **-34 10:31** | 23400 PE 402.8L → 373.9L (-7.2 %, z 4.4) | -91 / -32 / -58 / -85 | real |
| Z 09-22 11:12 | -71 13:51 | **-44 11:57** | 23300 PE 323.5L → 295.9L (-8.5 %, z 5.4) | -80 / +11 (14:21) / -43 / -58 | **noise: W rebuilt 12:17** (the premium still fell to -80 %) |
| Z 09-22 12:03 | -47 13:51 | **-22 12:49** | as A2 | -64 / +63 (14:21) / -36 / -18 | real |
| Z 09-24 12:00 | -8 12:48 | -9 12:35 | 23200 PE 108.7L → 104.2L (-4.1 %, z 5.3) | -35 / -2 / -9 / -29 | real |

- It speaks on 4 sessions only: 22 Sep (4 rows, one expiry afternoon), 24 Sep, 25 Sep and 30 Sep. A2 and Z 09-22 12:03 are the same OI event.
- It is silent on these, by its own two conditions:
  - Z 09-30 10:27 SELL: the writers left while she was winning.
  - Z 09-25 09:54: FLOW and VPIN were WITH her.
  - Z 09-24 09:57 and 10:30: the writers left before the price came. These wait for G, at -13 / -11 %, where (i) gave -8 / -2 %.
- It is silent on every trailed trade, by design: H1, A1, A4, her 28 Sep and her 29 Sep.

### 4.2 (ii) AT RISK as a word

It would show on the 17 replays of D1. **On 7 of those 17 the premium later printed above +20 % of entry**:

- 25 Sep 23100 CE (hers): +59 %
- 25 Sep 23200 PE (hers): +23 %
- A2: +78 %
- A5: +53 %
- Z 09-22 12:03: +63 %
- Z 09-25 09:54: +57 %
- Z 09-30 10:27: +73 %

A loud warning with no out-condition, shown before 7 run-ups, is the panic trigger she is trying to remove.

### 4.3 The sold mirrors (the other side, sold at the same second; same d, same speak)

| replay | short | rev 6 | (iv-g) | 15:00 |
|---|---|---|---|---|
| 25 Sep 23100 CE (hers) | 23100 PE @ 99.6 | -7 12:47 | -4 12:07 | +35 |
| 30 Sep 22750 CE (hers) | 22750 PE @ 125.25 | -29 11:16 | -17 10:35 | -52 |
| A2 | 23350 PE @ 43.25 | -40 13:51 | +0 12:49 | +28 |
| Z 09-22 09:39 | 23450 PE @ 42.8 | -126 10:45 | -36 10:31 | -132 |
| Z 09-22 11:12 | 23400 PE @ 51.4 | -91 13:51 | -42 11:57 | -17 |
| Z 09-22 12:03 | 23350 PE @ 37.1 | -63 13:51 | -17 12:49 | +16 |
| Z 09-24 12:00 | 23250 PE @ 125.9 | -15 12:48 | -15 12:35 | -61 |

### 4.4 Pullback or invalidation: what the rows show

The pullback state, on the minute rows: HOLD at entry, the future ≥ w against her entry, and W still building or stopped (not off).

- **117 spells; 54 lasted 3 minutes or more, on 28 replays** [M].
- How those 54 ended:
  - **30 with price back within w of her entry;**
  - 11 at rev 6's FOLD (G accepted);
  - 11 with W coming off its peak (the GAVE UP condition);
  - 2 at 15:00.

Writers still standing while price is against her mostly meant a pullback in this sample. Writers leaving while price came at them is the row that preceded the losses in §4.1.
