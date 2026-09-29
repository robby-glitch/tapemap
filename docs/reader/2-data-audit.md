# 2 - Data audit for the order-flow reader

Audited 2026-09-29, after the close. Read-only: no code edited, nothing written under `data/`, no server start/stop, no git writes. Every number below was measured from files by scripts in the session scratchpad (`...\scratchpad\*.py`: `inv_all.py`, `inv_tape.py`, `gc_checks.py`, `cmp_gc_ux.py`, `book_stats.py`, `chain_stats.py`, `completeness.py`, `final_delta.py`, `replay_tick_all.py`, `ofd_exports.py`). Times are IST. Lots: NIFTY 65, BANKNIFTY 30, SENSEX 20 (from the instrument dump and the ux rows). Tags: [M] measured, [I] inferred, X impossible. Where I did not verify something it is under "Not verified" at the end.

## 0. Headline findings (what a designer must know before drawing anything)

0. **PRIORITY, live data loss: the F&O session ends 15:40, not 15:30, and TapeMap cuts at 15:30.** NSE moved the normal market close for equity derivatives from 15:30 to 15:40 effective 2026-08-03 (circular of 2026-05-30, per five secondary sources; section 8). Our own files confirm it: NIFTY futures traded 1,800 lots between 15:30 and 15:40 on 09-22 (GC bars, Upstox book and `vtt` agree exactly), 551 lots on 09-23, and GC shows 15:30 and 15:35 bars with 300-2,650 lots on every one of the 13 days 09-07..09-29 for which bars exist (2.1-8.6% of the day's volume, OI moving). Since the operator's 2026-09-23 cut, every recorder drops 15:30-15:40 (tape, book, ux, senses, VPIN, chain, frame, marks, 1-minute bars, EOD capture). Before that the book, senses and VPIN kept them and labelled them "after close". About 30 places in the code carry a 15:30 constant (section 8.3). Wherever this document says "post-close", read "15:30-15:40, the last ten minutes of the session".
1. **GoCharting (GC) order flow exists for NIFTY only.** `data/tape/tape_*` and `ofd_marks_*` are NIFTY files. BANKNIFTY and SENSEX have only the Upstox-derived record (book, ux, chain). No GC footprint was ever recorded for them.
2. **The GC bar is internally exact.** On all 9 recorded days, for every unique bar: sum(ladder buy) = buy, sum(ladder sell) = sell, buy + sell = vol, buy - sell = delta, all whole lots. There is no "unknown" bucket. The side of each lot is a vendor classification of undisclosed method (see 3b).
3. **GC tick-built bars have permanent holes.** On 2026-09-29 the GC tick stream stalled twice (about 11:32:35 and 12:25:51). The 12:25 bar holds 136 lots against 943 traded (Upstox), with open/high/low/close wrong. The extension never replaces a tick-built bar with GoCharting's later snapshot (`session.js:31`), and `tape_log` writes each bar once by `t`, so the hole is permanent in the record. This repeats on every day (3d).
4. **Upstox has no print feed and no aggressor side.** It gives ~1 Hz conflated snapshots: last trade (price, time, qty), cumulative volume `vtt`, OI, 5 levels of depth, and total resting quantity. Only 32% of volume-bearing frames on 09-29 are a single trade (`V == ltq`). Everything per-price and every side from Upstox is a reconstruction [I].
5. **The recorded ux ladder is wrong from 2026-09-23 onward, by a unit error.** `ux` rows carry `tick: 10.0` (NIFTY), 20.0 (BANKNIFTY), 5.0 (SENSEX): the dump's paise value, used as rupees. The book's real price step is 0.1 / 0.2 / 0.05. `ladder.py` uses `tick * 0.55` as a reach limit (5.5 points instead of 0.055). 09-22 was recorded with the inferred rupee tick (0.1) and is different. Replaying the same book with the rupee tick raises the ux-vs-GC delta correlation from 0.58 to 0.70 (pooled, 394 bars, blocks excluded) and raises the "hidden" (not attributed to a displayed level) share from 24-36% to 54-67% (3f).
6. **Both Upstox recorders start about 09:17, not 09:15,** on all 6 days, with the server up from 08:55 on 09-29. The first two minutes are absent from book, ux, chain and VPIN. GC has 09:15 if the tab was open.
7. **Futures OI updates once a minute** (NIFTY and BANKNIFTY median gap between changes 60.2 s and 60.4 s; SENSEX 162 s). OI is in **units (quantity)**, not lots; every value is divisible by 65. GC bar OI equals the Upstox OI at the bar's close on 70 of 74 bars (09-29).
8. **Blocks dominate single bars.** 09-29 10:05: one print of 4,528 lots at 22598.8 is 70% of the bar's 6,441 lots and is the whole of its delta (+4,483). 15:00: 2,030 lots at 22684.0 (3 trades) is 59% of 3,416. The extension's absorption mark at 10:05 is that single print.
9. **The Oct future is not recorded or subscribed anywhere.** Sep expires today (09-29) for NIFTY and BANKNIFTY. GC's `NIFTY-I` is Sep until 15:30 today and Oct from 09-30 (a calendar-spread price offset, OI reset).
10. **More GC days exist outside `data/`:** extension exports (`Go charting\NIFTY-I_*.ofd.json`, `orderflow-desk\test\session-*.ofd.json`) hold full-day ladders + OI + per-bar `maxDelta`/`minDelta` + trade counts for 09-07, 09-08, 09-09, 09-10, 09-15, 09-17 (days with no tape file) and more (section 1d).

## 1. Inventory: every recorded day, per index and per source

### 1a. GoCharting footprint bars (`data/tape/tape_NIFTY_<day>.jsonl`, plain, never gzipped: `daylog.DIRS` excludes tape)

Fields written per bar (`tape_log._BAR_KEYS` + meta): `t o h l c vol buy sell delta oi fromTicks ladder[] rowSize rowAnchor lot session idx day ik(null) ik_why`. NIFTY only.

| Day | Rows (unique t) | First-last | Bars 09:15-15:25 | Bars 15:30-15:40 (real session, see section 8) | Avg ladder levels/bar | Day vol lots (bars < 15:30) | Tick-built T / snapshot F | Notes |
|---|---|---|---|---|---|---|---|---|
| 09-11 | 77 (77) | 09:15-15:35 | 75 | 15:30, 15:35 | 49.9 | 48,832 | 63 / 14 | 14 rows `fromTicks` null (older schema) |
| 09-18 | 78 (78) | 09:15-15:40 | 75 | 15:30, 15:35, 15:40 | 28.5 | 22,342 | 46 / 32 | |
| 09-21 | 77 (77) | 09:15-15:35 | 75 | 15:30, 15:35 | 34.8 | 24,050 | 14 / 63 | rowSize 2 on 70 rows |
| 09-22 | 82 (78) | 09:15-15:40 | 75 | 15:30, 15:35, 15:40 | 43.5 | 38,432 | 50 / 28 | 4 duplicate identical rows (15:00-15:15); 09:15 bar only 154 lots |
| 09-23 | 77 (77) | 09:15-15:35 | 75 | 15:30, 15:35 | 40.6 | 26,045 | 51 / 26 | |
| 09-24 | 78 (75) | 09:15-15:25 | 75 | none in the tape file (the export has 15:30 and 15:35: 2,186 lots) | 60.4 | 63,250 | 57 / 18 | 3 duplicate identical rows (13:30-13:40) |
| 09-25 | 53 (53) | 09:15-13:35 | 53 | none | 33.7 | 37,963 | 39 / 14 | recording stops 13:35; 22 bars (13:40-15:25) absent |
| 09-28 | 75 (75) | 09:15-15:25 | 75 | none in the tape file (no export for this day) | 49.5 | 68,384 | 68 / 7 | |
| 09-29 | 75 (75) | 09:15-15:25 | 75 | none in the tape file (the export has 15:30: 1,102 lots, 15:35: 698) | 58.3 | 75,693 | 37 / 38 | Sep expiry day |

No tape file exists before 09-11, or for 09-14..09-17, 09-19/20. Every bar is a 5-minute bar (session key `NIFTY-I|5m|<day>`). `ik` is null on every row: GC's continuous front contract, contract not declared.

`fromTicks` T = built client-side from GoCharting's live `RECEIEVEDTRADE` ticks (`adapter.js:trades`); F (false/null) = GoCharting's `FOOTPRINT/V2` snapshot (`adapter.js:footprint`).

**Extension marks** (`ofd_marks_NIFTY_<day>.jsonl`): detections, not measurements. Fields `t kind side p size src idx day`.

| Day | Marks | First-last | Kinds |
|---|---|---|---|
| 09-21 | 82 | 09:25-15:30 | absorption 41, trap 18, initiative 14, vacuum 6, climax 2, exhaustion 1 |
| 09-22 | 88 | 09:15-15:35 | absorption 42, trap 15, initiative 11, exhaustion 10, climax 6, vacuum 4 |
| 09-23 | 72 | 09:15-15:05 | absorption 31, trap 12, initiative 12, exhaustion 9, vacuum 6, climax 2 |
| 09-24 | 71 | 09:15-14:55 | absorption 31, trap 19, exhaustion 9, initiative 7, vacuum 4, climax 1 |
| 09-25 | 66 | 09:30-13:35 | absorption 34, trap 11, exhaustion 10, initiative 6, vacuum 5 |
| 09-28 | 118 | 09:15-14:25 | absorption 62, trap 36, exhaustion 7, initiative 9, vacuum 3, climax 1 |
| 09-29 | 57 | 09:15-15:00 | absorption 21, initiative 15, exhaustion 7, trap 7, vacuum 6, climax 1 |

Total 554 marks over 7 days (absorption 262, trap 118, initiative 74, exhaustion 53, vacuum 34, climax 13). The `tm` marks are not recorded (`tape_log` docstring: recomputed from the bar file).

### 1b. Upstox: book (`data/book/book_<idx>_<day>.jsonl`) and ux bars (`data/tape/ux_<idx>_<day>.jsonl`)

Book starts 2026-09-22 (no earlier book file, plain or gz; the 09-22 files are plain and will be gzipped by `daylog` after the 7-day window; read through `daylog.open_text`). Book rows are change-only frames written at the socket decode step.

| Day | NIFTY book rows | BANKNIFTY | SENSEX | First row (all three) | Last row | ux bars N / B / S |
|---|---|---|---|---|---|---|
| 09-22 | 20,589 | 20,600 | 29,735 | 09:17:19-20 | 15:40:00-01 | 76 / 76 / 75 |
| 09-23 | 20,739 | 22,215 | 30,589 | 09:17:00 | 15:39:59-15:40:00 | 77 / 77 / 76 |
| 09-24 | 22,641 | 22,521 | 31,091 | 09:17:01-02 | 15:30:00-01 | 75 / 75 / 75 |
| 09-25 | 19,306 | 20,600 | 27,787 | 09:17:15-16 | 15:30:00 | 75 / 75 / 74 |
| 09-28 | 22,017 | 21,635 | 28,492 | 09:17:19 | 15:30:01 | 75 / 75 / 75 |
| 09-29 | 23,395 | 23,366 | 29,726 | 09:17:00 | 15:29:59-15:30:01 | 74 / 75 / 75 |

Book row size 6.7-11.4 MB per index-day. The 09-22 and 09-23 books run to 15:40 (before the 2026-09-23 "nothing recorded after 15:30" rule). Those two days are the **only** Upstox record of the last ten minutes of the session (section 8): NIFTY +1,800 lots on 09-22 and +551 on 09-23 after 15:30:00. From 09-24 the book holds 1-4 rows at 15:30:00-15:30:01 and stops.

ux bars: derived by `ladder.py` from the book, 5-minute bins, write-once by `t`, `src:"ux"`. NIFTY/BANKNIFTY extras: 09-22 and 09-23 have 15:30 and 15:35 bins (real session bins); SENSEX 09-22 and 09-23 have 15:30. Missing bins: 09-22 13:10 (all three, book outage), 09-25 SENSEX 15:25, 09-29 NIFTY 15:25 (last bin never closed live; book ends 15:29:59; a replay closes it: 15:25 bin exists in `replay_tick_all.py`).

Book outages (gaps of 30 s or more between rows; all three indices show the same gaps, so it is the feed, not one instrument):

| Day | Gaps >= 30 s |
|---|---|
| 09-22 | 13:08:41 (413.7 s), 13:16:34 (278.4 s) |
| 09-23 | 15:26:32 (44.6 s) |
| 09-24 | none (max 6.8 s NIFTY) |
| 09-25 | 11:55:47 (48.6 s), 13:20:36 (46.1 s), 14:02:04 (214.8 s), 14:08:45 (169.4 s) |
| 09-28 | none (max 7.1 s NIFTY, 11.0 s BANKNIFTY) |
| 09-29 | none (max 5.0 s) |

Minutes with no book row: 09-22 10, 09-25 4, others 0.

**Contract stamp:** `ik`/`expiry` on book and ux rows only from 09-29 (`NSE_FO|68407` NIFTY Sep, expiry 2026-09-29; `NSE_FO|68390` BANKNIFTY Sep; `BSE_FO|864571` SENSEX Oct, expiry 2026-10-29 - the SENSEX Sep future had already expired). Earlier rows have `ik: null`.

### 1c. Chain, VPIN, frame, trigger_log, and other derived logs

| Source | Path | Days / rows | Cadence / notes |
|---|---|---|---|
| Option chain (Upstox socket) | `data/chain/chain_<idx>_<day>.jsonl[.gz]` | 25 days per index, 08-20 .. 09-29 (no file for 08-28, 09-08, 09-14, 09-21); ~2,060-2,130 rows on a full day | One snapshot per 11.0 s (median, max 13 s on 09-29; 09-25 gaps of 64, 103, 199, 147 s = the book outages). 17 strikes (ATM +/-8, window fixed at start: NIFTY 09-29 22300-23100 all day). Full days (>= ~2,000 rows, first <= 09:19): 08-24, 08-27, 08-31, 09-01, 09-11, 09-22, 09-23, 09-24, 09-25, 09-28, 09-29. Partial: 08-20 (52 rows), 08-26 (to 11:18), 09-02 (from 11:51), 09-03 (from 10:22), 09-04 (to 14:11), 09-07 (from 09:46), 09-09 (from 11:22), 09-10 (from 09:41), 09-15 (from 09:42), 09-16 (from 09:45), 09-17 (from 09:33), 09-18 (from 09:50, 812 rows) |
| Chain REST backfill | `data/chain_backfill/backfill_<idx>_2026-09-29.jsonl` | 09-29 only: NIFTY 2 rows (09:15, 09:16), BANKNIFTY 1, SENSEX 1 | 1-minute per-strike OI-change and premium grid rebuilt from REST for minutes before the first live snapshot; tagged `backfilled`. Older warmap backfills at `data/warmap/*_backfill.jsonl` |
| VPIN slow | `data/vpin_log.jsonl` | 917 rows, 21 days 08-25 .. 09-29 (`NIFTY-FUT`); 09-29: 81 buckets 09:19:38-15:28:25 | One row per completed 60,000-unit volume bucket (923 lots) |
| VPIN fast | `data/vpin_fast.jsonl` | 930 rows, 5 days 09-23 .. 09-29; 09-29: 244 buckets 09:17:42-15:28:54 | 20,000-unit bucket (308 lots) |
| VPIN backfill | `data/vpin_backfill.jsonl` | 1 row (09-25) | |
| Frame log | `data/frame/frame_<day>.jsonl[.gz]` | 11 files 09-15 .. 09-29, NIFTY only: 46 / 5,556 / 5,923 / 2,160 / 40 (gz, 09-15..09-21), 2,803 / 3,574 / 4,424 / 2,333 / 4,962 / 3,320 (plain, 09-22..09-29) | A derived decision record (walls, setup, tells), one ~29 KB row when its signature changes. Not raw. Contains `tape.events`, `tape.aggressor`, `ux_oi` ([t, oi]). Rows are stamped with ts outside the session too (09-24: 00:00-23:29; 09-28: 00:00-19:37): posts made while GoCharting still showed the prior session |
| trigger_log | `data/trigger_log.jsonl` | 2,025 rows, 40 days 08-04 .. 09-29 (NIFTY 789, BANKNIFTY 569, SENSEX 667); 09-29 NIFTY 9 rows (09:27-12:18) | Band-touch triggers + forward scoring. Derived |
| senses | `data/senses/senses_<day>.jsonl[.gz]` | 08-20 .. 09-29 (gz to 09-18); plain 09-22..09-29 = 893k / 909k / 907k / 912k / 962k / 1,026k rows | Sweep/wall detections on the futures and near-ATM option books (`inst`, `kind`, `qty`, `tag M`, `side_tag I`). Derived |
| Other derived | `calls/` (375 rows/day, 09-24..09-29), `hold/` (hold, expr, side, check), `fold/` (09-29, 494), `surface/` (6.1-6.4k rows/day), `warmap/` (+ `_backfill`), `day_state/` (daily, 08-26..09-29), `paper_desk/` (to 09-25) | | Derived |
| 1-minute FUT bars (older) | `data/backtest/fut_2026-04-29.json` .. `fut_2026-08-25.json` (74 days) | keys `open high low close volume open_interest timestamp` | [M] 1-minute OHLCV+OI, no side. Ends 2026-08-25; does not overlap any tape day |

### 1d. GoCharting extension exports (outside `data/`)

`C:\Users\kaam\Desktop\Go charting\NIFTY-I_*.ofd.json` and `...\orderflow-desk\test\session-*.ofd.json`. IndexedDB exports written by `recorder.js`. Each bar carries the fields the tape file lacks: `maxDelta`, `minDelta`, `buyTrades`, `sellTrades`, `partial`, `joined`, `lotOk`, plus ladder and OI. The exports hold no intrabar `diffs` (all empty).

| Day | 5m bars (first-last) | Where |
|---|---|---|
| 09-07 | 78 (09:15-15:40) | test/session-2026-09-07 |
| 09-08 | 77 (09:15-15:35) | Go charting/ and test/ |
| 09-09 | 78 (09:15-15:40) | Go charting/ and test/ |
| 09-10 | 77 (test, 5m); 26 (Go charting, 15m) | both |
| 09-11 | 77 | both (tape file also exists) |
| 09-15 | 77 | test/session-2026-09-15 |
| 09-16 | 15 (09:15-10:30) | Go charting/ (partial) |
| 09-17 | 75 | Go charting/ |
| 09-18, 09-21, 09-22, 09-24, 09-29 | 78, 77, 78, 77, 77 | Go charting/ (tape file also exists) |
| 09-23 | 76 | Go charting/ (tape file also exists) |

For 09-29 the export is bar-for-bar identical to the tape file on `vol` and `delta` (75 of 75) and adds two bars the tape file does not have (15:30: 1,102 lots; 15:35: 698 lots; both real session bars, section 8). No export for 09-25 or 09-28.

## 2. Fields and units per source

### GoCharting bar (tape file and export)

| Field | Unit / meaning |
|---|---|
| `vol`, `buy`, `sell`, `delta` | **Lots** (`adapter.js` divides feed units by `lotSize` 65). All whole numbers on every bar (fractional ladder levels: 0 of 23,000+). `delta = buy - sell`, the bar's closing delta (`close_delta`) |
| `oi` | **Present on every bar of every day** (rows with `oi` = rows, 9 of 9 days). **Units (quantity), not lots**: every value divisible by 65 (checked on 09-29, GC and Upstox). NIFTY-I 09-29: 8,795,540 at 09:15 = 135,316 lots. Value = OI at bar close (matches Upstox's last frame in the bin). Tick-built bars take OI from the last tick (`open_interest`); snapshot bars from `OHLC_DATA` |
| `ladder[]` | One entry per traded price, **tick-level** (0.1 pt steps; most common step 0.1, then 0.2, 0.3): `{p, b, s, bt, st}` = price, buy lots, sell lots, buy trade count, sell trade count. Per bar on 09-29: min 7, median 58, max 108 levels; 09-24 up to 123. Rows are sparse (only traded prices). No time order inside a bar. No resting (quote) size. 0.1-0.6% of levels have zero lots but a trade count (a rounding artefact). About 9,800 trades/day, 7-8 lots per trade |
| `rowSize`, `rowAnchor` | The chart's zoom row size at post time (2, 2.5, 5, 10 within one day on 09-24 and 09-28). Cosmetic; the ladder is stored at tick level so any reader can re-bin |
| `fromTicks` | T tick-built vs F snapshot (above) |
| `maxDelta`, `minDelta` | Extremes of the running intrabar delta. **Only in the exports**; not posted, not in the tape file |
| Per-bar cumulative delta | **No.** GC gives only the bar's own delta. TapeMap computes `cvd` (`prints.with_cvd`, running sum from the first bar of the day) and stacks/POC when it serves `/api/tape` |
| Side | Every lot is BUY or SELL (buy + sell = vol on 100% of bars). GC ticks carry a `side` (BUY/SELL; ticks without a side are dropped and counted in `adapter.stats.noSide`). **Method undisclosed.** By measurement it is closer to a quote (touch) rule than a tick rule: pooled over 6 days, 389 bars, corr(GC delta, frame-level quote-rule signed volume) = 0.67, corr(GC delta, tick-rule signed volume) = 0.37. Not an exchange-tagged aggressor (the NSE feed via Upstox has no such field) |

### Upstox book row (`book_<idx>_<day>.jsonl`)

`{t arrival ms, cts exchange currentTs, ltt last trade ms, ltp, ltq, vtt, oi, tbq, tsq, b [[price, qty] x5], a [[price, qty] x5], ik, expiry}`. Source: Upstox v3 `full` mode (`upstox_proto.py`: `ltpc` = ltp/ltt/ltq/cp, `marketLevel.bidAskQuote`, `atp`, `vtt`, `oi`, `tbq`, `tsq`).

| Item | Measured |
|---|---|
| Depth | **5 levels each side on 100% of rows**, all 18 index-days. 5th bid sits 4.4 pts (median) from the best bid, max 12.4 (NIFTY, first 5,000 rows 09-29). Median spread 2.9 pts, p90 7.4 (first 20,000 rows) |
| Quantities | Units (multiples of the lot, e.g. 6,955 = 107 x 65). `vtt` cumulative traded units. `oi` units. `tbq`/`tsq` = total resting buy/sell qty across the **whole** book (greater than the top-5 sum on 20,000 of 20,000 rows; median 54x) |
| Update cadence | Change-only rows. Median gap 0.84-1.20 s (per index-day), p90 1.05-1.83 s, p99 1.1-2.6 s. Arrival lag vs exchange `cts` median 0.35-0.45 s (BANKNIFTY/SENSEX 09-24 show -1.5 s: clock skew, not lag) |
| Prints | **None.** `ltq` is the last trade only. Volume-bearing frames on 09-29 (first 20,000 rows): 8,059; single-trade (`V == ltq`) 2,579 = 32%. The rest hold several trades |
| Aggressor side | **Not in the feed.** Inferred (`ladder.side_of`: print vs the prior frame's touch; print at the mid = "unknown", 46 lots = 0.06% on 09-29) |
| `vtt` resets | 0 on all 18 index-days |
| OI cadence | Futures OI changes about once per minute: median gap between changes NIFTY 60.2 s, BANKNIFTY 60.4 s, SENSEX 162 s (BSE). 365 / 360 / 101 change events on 09-29 |

### ux bar (`ux_<idx>_<day>.jsonl`)

Same bar shape as GC plus reconstruction counters: `unknown`, `unpriced`, `hidden`, `exact`, `reconstructed`, `frames`, `late_frames`, `lot_mismatch` (0), `vtt_resets`, `partial`/`partial_why`, `tick`, `tick_src`, `lot_src`, `ik`. Volume `vol` is [M] (from `vtt`; equals GC volume within 1% on complete bars). Buy/sell per price is [I]. Levels per bar (NIFTY 09-29): 62-299, median 118 (a denser ladder than GC's 58: it contains the book-derived fills).

| Reconstruction share NIFTY | 09-22 | 09-23 | 09-24 | 09-25 | 09-28 | 09-29 |
|---|---|---|---|---|---|---|
| tick stamped on the rows | 0.1 inferred | **10.0 given** | 10.0 | 10.0 | 10.0 | 10.0 |
| `hidden` share of volume as recorded | 59% | 24% | 25% | 36% | 30% | 31% |
| `hidden` share replayed with tick 0.1 | 59% | 54% | 64% | 67% | 66% | 62% |

BANKNIFTY (tick 20.0 recorded vs 0.2 real): hidden 19-30% recorded from 09-23. SENSEX (5.0 vs 0.05): 9-64%. "Hidden" volume is booked at the frame's `ltp` on the primary side, not at a true price: on 09-29 15:00 the 2,030-lot GC print is at 22684.0, ux places 1,995 at 22684.9.

### Option chain row (`chain_<idx>_<day>.jsonl`)

`{ts, sec, spot, atm, expiry, ik, strikes[17] {k, ce{...}, pe{...}}}`. Leg fields: `ltp, oi, oi_chg, iv, vol, bid, ask, avg, gamma, delta`. All OI/volume in units (e.g. 5,239,325 = 80,605 x 65). `oi_chg` = change since the 09:15 baseline, not since the prior close. `iv`/greeks null on deep ITM legs. Only top-of-book bid/ask per leg: no depth, no prints, no per-leg ladder. ATM leg OI changes in 373 of 2,128 consecutive NIFTY snapshots (about once per minute, like the future). `expiry`/`ik` on rows from 09-29 only.

### VPIN

`{at, bucket, buy, sell, imb, vpin, pct, tag, shadow, inst, day}`. Units per bucket (60,000 slow, 20,000 fast). Buy/sell split by the **tick rule at frame cadence** on Upstox future frames (`vpin.py` docstring); volume with no sign yet is split half-half. `pct` is null until 10 buckets. Shadow, untested forward. Direction-blind.

## 3. Consistency checks, 2026-09-29 NIFTY

### 3a. GC bar OI vs Upstox futures OI

Equal on **70 of 74** bars (the 74 bars present in both). The four differences: 11:40 (GC - Upstox = +6,890 units = 106 lots), 11:50 (+975 = 15 lots), 12:25 (+6,565 = 101 lots), 15:10 (+585 = 9 lots): a one-minute sampling offset. Over the six Upstox days: equal on 68/74, 71/75, 71/75, 50/53, 74/75, 70/74. The large mismatches sit on GC stall bars where OI stops updating with the ticks: 09-22 14:55 (-157,495 units = -2,423 lots), 09-24 13:30 (-17,095 = -263 lots), 09-25 10:20 (-9,620 = -148 lots).

OI context: 09-28 last bar 10,377,185; 09-29 first bar 8,795,540 = -1,581,645 units (-24,333 lots) overnight/at the open; day 09:15 -> 15:25: -1,643,655 units (-25,287 lots). Do not compute the 09:15 bar's change against the prior close.

### 3b. GC delta vs Upstox signed volume per 5 minutes

Two Upstox-side signed-volume series exist: the recorded ux delta (with the paise tick), and the same book replayed through `ladder.py` with the rupee tick (equals a plain frame-level quote rule: replay and independent quote rule day sums agree to within 6 lots on 09-22, 09-25, 09-28, 09-29). Bars used: both present, 09:20-15:25, GC volume within 3% of Upstox volume (so GC stall bars are excluded). 

| Set | Bars | corr(GC, recorded ux) | corr(GC, ux with rupee tick) | Bar-sign agreement (recorded / rupee) |
|---|---|---|---|---|
| 09-29 all | 70 | 0.92 | 0.97 | 47/70 (67%) / 54/70 (77%) |
| 09-29 without 10:05, 15:00 (blocks) | 68 | 0.64 | 0.87 | 45/68 / 52/68 |
| Six days pooled, all | 397 | 0.82 | 0.87 | 68% / 72% |
| Six days pooled, blocks removed (one level >= 50% of bar volume and bar >= 3x the day's median) | 394 | 0.58 | 0.70 | 67% / 72% |

Per day corr(GC, ux rupee tick): 09-22 0.84, 09-23 0.88, 09-24 0.43, 09-25 0.26, 09-28 0.59, 09-29 0.97. 09-24 and 09-25 are poor: on tick-built bars corr(GC, frame quote rule) is 0.29 and 0.16 (snapshot F bars on the same days 0.79 and 0.51). Pooled, T bars 0.64, F bars 0.72.

Session delta (09:20-15:25, bars present in all series), lots:

| Day | GC | ux recorded | ux rupee tick | Frame quote rule | Frame tick rule |
|---|---|---|---|---|---|
| 09-22 | -4,088 | -11,686 | -11,686 | -11,681 | -3,336 |
| 09-23 | +1,599 | -3,020 | -380 | -385 | +460 |
| 09-24 | -3,486 | -16,166 | -6,710 | -6,754 | -4,920 |
| 09-25 | +1,078 | -2,994 | +182 | +143 | -460 |
| 09-28 | -1,529 | -6,530 | -6,722 | -6,701 | -4,142 |
| 09-29 | +14,391 | +8,385 | +15,279 | +15,313 | +5,840 |
| 09-29 without 10:05, 15:00, 15:15 | +6,653 | -521 | +6,195 | +6,242 | +9,360 |

GC and the rupee-tick quote rule share the sign of the session delta on 5 of 6 days (09-23 differs, magnitude tiny), and differ in size by up to 2x (09-24: -3,486 vs -6,710). The recorded ux delta disagrees more (09-23, 09-25, 09-29-without-blocks). Neither side is an exchange aggressor tag.

### 3c. The abnormal bars (10:05, 15:00, 15:15)

| Bar | GC (tape) | Upstox / ux | OI (GC) | Mark |
|---|---|---|---|---|
| 10:05 (T) | 6,441 lots; buy 5,462, sell 979, delta +4,483; one level: 22598.8 buy 4,528 lots in 1 trade (70% of the bar); ohlc 22608.8/22615/22595/22606.4 | 6,443 lots; delta +5,389; 4,499 lots at 22598.8; `hidden` 5,769; the book shows one frame at 10:07:42 with `vtt` +4,523 lots while `ltq` = 1 lot (a burst between frames), followed by 10:07:50-55 frames of 308, 365, 402, 128 lots as price ran 22599 -> 22616 | 8,358,740 -> 8,628,165 = +269,425 units (+4,145 lots); next bar 8,291,660 = -336,505 (-5,177 lots). The book's OI trace: 8,330,725 at 10:07:30, 8,633,040 at 10:08:32 | `absorption` side -1 @22615 size 4,483 (= the bar delta) |
| 15:00 (F) | 3,416; buy 2,750, sell 666, delta +2,084; 2,030 lots at 22684.0 in 3 buy trades (59%) | 3,416; delta +2,298; 1,995 lots at 22684.9; 2,002 lots in one frame at 15:00:33 with `ltq` 1 | 7,570,810 -> 7,650,045 = +79,235 (+1,219 lots); next bar -143,000 (-2,200 lots) | `absorption` -1 @22685 size 2,098 and @22680 size 2,078 |
| 15:15 (F) | 3,167; buy 2,169, sell 998, delta +1,171; 849 lots at 22704.0 in 23 buy trades (27%) | 3,177; delta +1,219; 643 lots at 22704.0; the largest frame is 266 lots (`ltq` 5) | 7,489,170 -> 7,445,880 = -43,290 (-666 lots) | `absorption` -1 @22705 size 874 |

The volume is identical in both sources (within 0.3%); the delta differs by 200-900 lots per bar because the two sides classify differently, and the block's price differs by 0.9 pt at 15:00 (Upstox uses the frame's last price). The first two are single-print blocks; the third is a sustained buying level. Per-bar delta, CVD, stacks and the extension's absorption mark all take one print as a whole bar's story.

### 3d. The 12:25 -> 12:30 gap: a data hole in GC, not in the market

GC 12:25 bar: 136 lots (buy 56, sell 80), ohlc 22725 / 22726.4 / 22716.6 / 22720, OI 7,853,755, `fromTicks: True`. GC 12:30 bar opens 22691.5, a 28.5-pt gap from the 12:25 close.

Upstox (all volume through `vtt`, no book gap over 5.0 s that day) shows the 12:25 bin holding 943 lots: price fell 22713.1 (12:26:21) -> 22690.1 (12:27:37, a 110-lot frame) and reached 22680.1; ux ohlc 22725 / 22726.4 / 22680.1 / 22690.0; OI 7,847,190. Cumulative Upstox volume in the bin reaches GC's 136 lots at 12:25:51. So GC's tick stream stopped at about 12:25:51 and resumed only with the 12:30 snapshot bar (12:30 volume 2,013 lots = Upstox 2,013). Missing from GC: 807 lots (86% of the bar), the low and the close.

Same failure earlier that day: 11:30 bar 611 vs 981 lots (stall at about 11:32:35; -370 lots) and 11:35 bar 550 vs 600 (last ~36 s, from 11:39:24). Total: about 6.6 minutes and 1,227 lots lost of about 76,900 (1.6%). After 12:30 every bar is F and matches Upstox volume within 15 lots. Why it is permanent: `session.js:31` keeps a tick-built bar over a snapshot unless `partial`; `tape_log.append` writes each `t` once.

Across the six Upstox days GC bars short of Upstox by more than 3% and 10 lots: 09-22 (12:10, 13:15, 13:20, 14:55: 128 vs 2,956 lots), 09-23 (11:20, 12:10, 12:30, 14:25: 179 vs 922), 09-24 (10:25, 10:35, 11:20, 13:30: 14 vs 832, 14:00: 7 vs 1,291), 09-25 (10:20, 12:20), 09-28 (14:50), 09-29 (11:30, 11:35, 12:25). Almost all are T bars; 09-22 13:15 and 13:20 are F bars and coincide with the Upstox outage 13:08-13:20.

### 3e. Minutes missing per source (09-29 NIFTY, and per day)

| Source | 09-29 | Other days |
|---|---|---|
| GC bars present | 75 of 75 bins 09:15-15:25 (375 min); **the session is 385 min (to 15:40): bins 15:30 and 15:35 are absent from the tape file** (present in the export, 1,800 lots) | 09-25: 53 of 77 (22 bars in-session plus 15:30/15:35, i.e. 110+10 min absent after 13:35). 09-22 09:15 bar 154 lots (record starts late) |
| GC bars short (>3%, >10 lots vs Upstox) | 3 bars (11:30, 11:35, 12:25) | 09-22 4, 09-23 4, 09-24 4-5, 09-25 2, 09-28 1 |
| Upstox book | 09:17:00-15:29:59, max gap 5.0 s, 0 empty minutes; **15:30-15:40 absent (10 min, the recorder gate)**; **09:15-09:17:00 absent** (2 min; GC 09:15 bar is 2,702 lots vs ux 1,126 flagged `partial`: 1,576 lots = 58% of the first bar traded before the record started) | 09-22 10 min of outage, 09-25 4 min, 09-23 one 44.6 s gap |
| ux bins | 74 (15:25 not closed live; replay gives it) | 09-22 13:10 absent, and the volume of the 13:08-13:15 outage lands in the 13:15 bin (ux 13:15 = 615 lots vs GC 316) |
| Chain | 2,129 snapshots 09:17:10-15:29:58, max gap 13 s; 09:15-09:17:10 absent (REST backfill rows at 09:15 and 09:16) | 09-25 gaps 64-199 s |
| VPIN | fast 09:17:42, slow 09:19:38 first bucket (volume time) | |

Cause of the 09:17 start: not established. The server was up at 08:55 (`/api/health` `coverage.server_up`). The book hook is installed only when `in_session` is true and the poller has `resolved` (`server.py:748-766`), and chain first rows also land 09:17:00-09:17:29 every day, so both look gated by the poller's first in-session resolve rather than by the feed. Untested.

### 3f. The tick-unit defect in the recorded ux ladder

Measured facts: the dump slice (`data/upstox_nifty.json`) lists NIFTY FUT `tick_size 10.0`, BANKNIFTY 20.0, SENSEX 5.0; `upstox_instruments.lot_tick` returns them unchanged; `ux` rows from 09-23 carry `tick: 10.0/20.0/5.0, tick_src: given`; the book's smallest price step is 0.1 / 0.2 / 0.05 rupees; `ladder._march` limits its march by `tick * HALF_TICK (0.55)` in price units. The only unit test asserts the fixture's 0.05 (`test_upstox_instruments.py:146`), so the paise value never met a test. I did not change code. In-memory replay of each day's book (`ladder.Ladder(lot=65, tick=0.1)`) vs the recorded tick 10.0 gives the corr and hidden shares in the section 2 table and section 3b. The rupee-tick replay is closer to GC on every day (0.81 -> 0.84... see 3b) but leaves more volume "hidden" (54-67% of volume has no displayed-level decrease to sit on; it is booked at the frame's last price). Either way the ux per-price side is [I].

## 4. The next-month contract

- **Recorded or subscribed: no.** `upstox_instruments._futs` keeps futures whose expiry is live and `resolve()` builds `keys = [index] + [futs[0]] + option legs` (`upstox_instruments.py:resolve`); `server.py` watches only `fut_key`; `live.py` fetches REST bars for `fut_key`. A fixed-string search of `data/` for the Oct keys (`NSE_FO|48704`, `NSE_FO|48699`, `BSE_FO|1100929`) finds them only in the instrument cache (`data/upstox_nifty.json`, `upstox_banknifty.json`, `upstox_sensex.json`), never in a record.
- **What exists in the dump (cached 09-29 12:04):** NIFTY FUT 27 OCT 26 = `NSE_FO|48704` (lot 65, tick 10.0 = 0.10), 23 NOV 26 = `NSE_FO|61471`; BANKNIFTY 27 OCT = `NSE_FO|48699` (lot 30), 23 NOV = `NSE_FO|61466`; SENSEX already Oct 29 = `BSE_FO|864571` (lot 20), Nov 26 = `BSE_FO|1100929`.
- **GC:** the extension records the chart's own symbol, `NIFTY-I`; `main.js:259` derives `idx = symbol.split('|')[0].split('-')[0]`, so a second symbol such as `NIFTY-II` would be posted as `NIFTY` and merge into `tape_NIFTY_<day>` by `t` with first-writer-wins. Whether GoCharting serves a second-month NSE symbol was not checked.
- **Expiry day today (09-29):** the Sep contract (`ik NSE_FO|68407`) is what every source holds until 15:30. Its OI fell from 8.80M to 7.15M units on the day (-18.7%). Oct's OI and volume for the roll (who is rolling, and whether Sep OI leaving = Oct OI arriving) cannot be read from anything recorded.
- **What it would take (described, not built):**
  1. Live depth/OI/volume for Oct: add `futs[1]["instrument_key"]` to the subscribe list in `resolve()` and `book.watch` it under a distinct name (the book and ux files are keyed by `idx`, so a new name or a contract dimension is needed); cost ~7-9 MB/day per index of book, plus one more ux ladder. The Upstox subscription limit for `full` mode was not checked.
  2. Anytime-start, no live socket: Upstox REST `historical-candle/intraday/<key>/1minute` (already wrapped as `upstox_rest.intraday`) returns `[ts, o, h, l, c, vol, oi]` per minute for today, so Oct 1-minute volume and OI could be pulled for the whole day after the fact, with no depth and no side. `upstox_rest.historical(key, tok, day)` does the same for past days; whether earlier Oct history and the expired Sep contract are still served after 09-29 is unverified (the dump lists live instruments only; `upstox_instruments` notes an expired weekly is "absent").
  3. GC: a second footprint chart on the next-month symbol plus a `contract` dimension in `tape_log` (the file is keyed by `idx` only).
  4. Roll handling for replay: `tape_log.prior_pool` already cuts days on an older contract by `ik` and by `after` = the expired future's expiry; price levels do not carry across the roll (calendar spread), OI on 09-30 restarts from Oct's own book.
- **Only front-month data will be comparable through 09-29.** From 09-30 the Upstox `ik` is `NSE_FO|48704` and GC `NIFTY-I` is Oct.

## 5. What can be computed honestly, with the data as it is

"Leg" is read as a swing leg of price (a run of bars between pivots, additive over bars) and, where it matters, as an option leg (CE/PE strike).

| Quantity | Per bar | Per leg (swing) | Tag and reason |
|---|---|---|---|
| Volume, points, range | GC `vol`/ohlc, exact; check against ux `vol` (complete on stall bars) | sum / max-min | **[M]** |
| Delta | `buy - sell` from GC; from ux | sum of bar deltas | Volume base [M]; **side [I]**: vendor classification of unknown method, 67-72% bar-sign agreement with an independent Upstox rule, corr 0.58-0.70 without block bars. Stall bars understate. A single block sets the bar's sign |
| CVD | running sum of bar deltas from 09:15 (TapeMap `prints.with_cvd`) | difference of two CVD readings | **[I]**: cumulative errors (12:25: GC -24 vs Upstox-quote -381). Only inside one day. Session-sign agrees on 5/6 days between GC and the Upstox quote rule; level up to 2x apart. Intrabar CVD path: X in the tape files; only `maxDelta`/`minDelta` in extension exports |
| OI change | `OI[t] - OI[t-1]` from GC, in units (divide by 65) | OI(end) - OI(start) | **[M]** at 60 s resolution (SENSEX 162 s), equal to Upstox at bar close on 70/74 bars. Not per price; not intra-minute. Interpreting long/short build-up from OI x price is **[I]**. Not valid across the roll or against the prior close (09-29: -24,333 lots at the open) |
| OI per option leg | chain `oi`, `oi_chg` at 11 s (changes ~1/min) | | **[M]**, 17 strikes, top-of-book only; leg volume delta per snapshot [M]; leg side by bid/ask vs `ltp` [I] |
| Effort vs result (points per 1,000 lots) | (close - open) or (high - low) over `vol` | same, summed | **[M]**: both terms measured. Use the larger of GC and ux `vol` (GC stalls). Blocks (10:05) inflate effort: report with and without the largest print. First bar partial on 09-22 (GC 154 lots) |
| Per-price volume at tick level | GC `ladder` `b`+`s` | sum over the leg's bars | **[M]** volume at price, **[I]** its side. NIFTY only |
| Imbalance stacks | diagonal ratio on the re-binned ladder (`decode.js` 3x, min 5 lots, run 3) | | **[I]**: needs per-price side. Depends on the row size chosen (the recorded `rowSize` drifts 2-10 within a day); the reader should fix its own. NIFTY only. Available live in TapeMap (`prints.py`, parity-tested against `decode.js`) |
| Per-price absorption | aggressive volume at a price (GC) with resting size absorbing it | | **[I]** only. The aggressive side [M vol, I side]. GC never sees resting size; Upstox sees the top 5 levels at ~1 Hz, and attribution of fills to displayed size is a reconstruction with 24-67% of volume unlocated. Cannot see iceberg refills, add/cancel, or orders beyond 5 levels. The extension's own `absorption` marks (262 in 7 days) are detections and fire on single blocks |
| VPIN | none per bar (volume-time buckets, 60,000 / 20,000 units) | resample by bucket close time | **[I]**: tick rule at 1 Hz frame cadence on the future; pct mute for 10 buckets; shadow, untested forward. Inputs `vtt`/`ltp` [M]. Direction-blind expansion gauge only |
| Exact aggressor per trade | | | **X**: not in any feed |
| Intra-bar timing of GC prints | | | **X** from GC (no time order). Upstox gives ~1 s frames; GC extension `diffs` are empty in every export |
| Book add/cancel, iceberg, depth beyond 5 levels | | | **X** (5 levels; `tbq`/`tsq` give only the whole-book totals) |
| BANKNIFTY / SENSEX footprint | | | **X** from GC; Upstox-derived only, side [I] |
| Oct future OI / volume / ladder | | | **X** today (not recorded); REST 1-minute would give volume + OI only (section 4) |
| Per-price OI on the future | | | **X** (OI is whole-contract). Option-strike OI is per strike [M] |

## 6. Replay material

**Tier A: GC bars + ladder + OI, Upstox book/ux, chain, VPIN alongside (NIFTY):**

| Day | Verdict | Cautions |
|---|---|---|
| 09-29 | Good, full session. Sep expiry day. `ik` stamped. 10:05 and 15:00 blocks; GC holes 11:30, 11:35, 12:25 | ux tick 10.0 (rebuild from the book); book starts 09:17; ux 15:25 bin unwritten |
| 09-28 | Good, full session. Only one short GC bar (14:50) | ux tick 10.0; `ik` null; rowSize varied 2-10 |
| 09-24 | Full session, richest ladder (60 levels/bar, 63,250 lots). GC corr with Upstox delta poor (0.18-0.43) | 4-5 GC stall bars (13:30: 14 vs 832 lots, 14:00: 7 vs 1,291); 3 duplicate rows; rowSize 2-10 |
| 09-23 | Full session, quiet (26,045 lots) | GC stalls (14:25: 179 vs 922); book 15:26 gap 44.6 s; book/ux run to 15:40 |
| 09-22 | Usable with care | 09:15 GC bar 154 lots; book outage 13:08:41-13:20 (10 min); ux 13:10 absent and 13:15 inflated; 4 duplicate GC rows; ux recorded with the correct (inferred) tick |
| 09-25 | Half day only on GC (09:15-13:35, 53 bars); book and ux full to 15:30 | GC recording stops; book outages 14:02 (215 s) and 14:08 (169 s) |

**Tier B: GC bars + ladder + OI, no Upstox book:**

| Day | Chain | Note |
|---|---|---|
| 09-11 | from 09:18:28 (2,123 rows) | 75 bars, 48,832 lots, 3,772-lot first bar |
| 09-18 | from 09:50:56 (812 rows) | 75 bars, 22,342 lots, sparse ladder (28.5 levels) |
| 09-21 | none (no chain file) | 75 bars, 24,050 lots, 63 F bars |

No independent volume check exists for these three (no book; 1-minute FUT files end 08-25). Their GC bar holes cannot be sized.

**Tier C: extension exports only (no TapeMap record; carry `maxDelta`/`minDelta`, trade counts):** 09-07, 09-08, 09-09, 09-10, 09-15, 09-17 (full), 09-16 (15 bars, to 10:30). Partial chain files exist for 09-07 (from 09:46), 09-09 (from 11:22), 09-10 (from 09:41), 09-15 (from 09:42), 09-17 (from 09:33). All are on the Sep contract front, so prices are comparable through 09-29.

**Not enough for a replay:** 09-14, 09-16 (except the partial export), any day before 09-07 (only 1-minute FUT bars to 08-25, no ladder).

**Upstox alongside:** 09-22 .. 09-29 (six days) for NIFTY, BANKNIFTY and SENSEX book/ux/chain; GC alongside only for NIFTY. **VPIN alongside:** every Tier A/B day from 09-11 (`vpin_log`); fast line from 09-23.

Do NOT cut bars at 15:30: the session runs to 15:40 (section 8). GC bars 15:30 and 15:35 (and a 15:40 bar of 3-12 lots, the closing print) are real session bars and exist for 13 of these days in the extension exports (09-07..09-29, not 09-16, 09-25, 09-28) and in the tape files for 09-11, 09-18, 09-21, 09-22, 09-23. A replay of the full session is 77 five-minute bins (09:15..15:35). Prefer the per-price GC ladder for place and the Upstox volume for completeness; use `vpin`, `oi` and chain for context (chain has nothing after 15:30).

## 7. Traps for the designers (each one measured above)

1. A GC bar is not proof of a complete bar: check its `vol` against the ux `vol`, and check `fromTicks`. The record cannot self-heal.
2. Do not read the ux ladder from 09-23 on without rebuilding it with the rupee tick from the book file; comparing 09-22 with 09-23+ compares two methods.
3. The first 2 minutes of the Upstox side and the first bar of some GC days are partial. 09-22's GC 09:15 bar is 154 lots.
4. A single print can be the whole bar (10:05: 70%, 15:00: 59%). Delta, stacks, absorption and effort-vs-result need a block-aware view.
5. OI is quantity, minute-cadence, whole-contract, and steps on block days (10:05: +4,145 lots then -5,177 lots).
6. Only NIFTY has GC order flow. BANKNIFTY and SENSEX can only ever show Upstox-derived side [I].
7. After a feed outage the ux bin timing is wrong (volume of the gap lands in the next bin); GC's time base is the reference there.
8. The frame log and every `data/senses`/`calls`/`hold`/`fold` row are derived; they are not a source of order flow and contain rows stamped outside the session.
9. Sep -> Oct roll on 09-30: cross-day price and OI comparisons break there; `ik` is null on every tape row and on book/ux before 09-29.
10. The session is 09:15-15:40 (385 minutes, 77 five-minute bars). Anything written in this repo as "09:15-15:30", "375 minutes", "15:29 is the last minute" or "after 15:30 = closed" is out of date since 2026-08-03 (section 8.3).

## 8. Session end: 15:30 or 15:40?

**Verdict: 15:40 since 2026-08-03. TapeMap's 15:30 cut discards real trading and is a live data-loss bug.** Nothing was changed; this is evidence only.

### 8.1 The rule (external, secondary sources)

Web search (2026-09-29): NSE circular dated **2026-05-30** moves the normal market close for equity derivatives (index and stock futures and options) from 15:30 to **15:40, effective 2026-08-03**. Unchanged: pre-open 09:00-09:08, trade-modification end 16:15. The cash market gets a Closing Auction Session (15:15-15:35 per the summaries); derivatives keep trading through it, and the derivatives closing-price VWAP window moves from 15:00-15:30 to **15:10-15:40**. Stated by Angel One (WebFetch confirmed: "normal market close 3:40 PM", "effective August 3, 2026", VWAP 3:10-3:40 PM), and by BusinessToday, Kotak Neo, Flattrade, Anand Rathi, Sharekhan, NiftyTrader in the search summaries. **I did not read the circular itself** (nseindia.com timed out), and none of the pages I read states the expiry-day option last-trading/settlement time. Sources: [Angel One](https://www.angelone.in/news/market-updates/nse-extends-equity-derivatives-trading-hours-till-3-40-pm-starting-august-3-2026-set-to-introduce-closing-auction-session-in-equity-cash-segment), [Flattrade Kosh](https://flattrade.in/kosh/nse-extends-fo-trading-hours-till-340-pm-from-august-3-2026-what-it-means-for-traders/), [BusinessToday](https://www.businesstoday.in/markets/stocks/story/nse-extends-trading-hours-for-this-segment-check-revised-market-close-timing-534078-2026-05-30), [Kotak Neo](https://www.kotakneo.com/news/market-news/nse-derivatives-trading-extended-3-40-pm-august-2026-closing-auction/), [Anand Rathi](https://anandrathi.com/blog/nse-extends-trading-hours), [NSE CAS page](https://www.nseindia.com/static/products-services/closing-auction-session) (not readable).

### 8.2 Our own data (measured)

**Q1: does any recorded source hold data stamped 15:30-15:40?** Yes, five of them, and the trading is real and continuous:

| Source | 15:30-15:40 content | Days |
|---|---|---|
| GC bars (posted by the extension; IndexedDB exports; tape files) | 15:30 and 15:35 bars with 252-2,648 lots each, OI moving; a 15:40 bar of 3-12 lots at a single price (the closing print) on 09-07, 09-09, 09-18, 09-22. Share of the day's volume 2.1-8.6% | Exports: 09-07, 08, 09, 10, 11, 15, 17, 18, 21, 22, 23, 24, 29. Tape files: 09-11, 09-18, 09-21, 09-22, 09-23 (dropped from 09-24 on) |
| Upstox book (`vtt`, `ltt`) | NIFTY 09-22: 666 rows, +1,800 lots, `ltt` to 15:39:59, ltp 23391.2-23415.0; 09-23: 534 rows, +551 lots. BANKNIFTY +713 / +676 lots. SENSEX +21 / +50 lots. Volume per minute 15:30-15:39 is the same size as 15:20-15:29 (09-22: 203, 92, 216, 113, 69, 163, 185, 103, **512**, 142 lots at 15:30..15:39); median spread 1.55 pts (09-22). GC's 09-22 15:30 + 15:35 + 15:40 bars sum to 694 + 1,103 + 3 = 1,800 lots: the two sources agree exactly. From 09-24: 1-4 rows at 15:30:00-01, nothing after | 09-22, 09-23 only |
| 1-minute FUT REST candles (`data/backtest/fut_*.json`, eod_capture) | Up to 07-31: 375 bars ending 15:29 (every day 04-29..07-31). **08-13..08-25: 379-385 bars**: 08-13, 08-18, 08-24 have 385 (09:15-15:39); volume after 15:30 in lots (units/65): 08-13 901, 08-14 391, 08-17 1,507, 08-18 1,892, 08-19 490, 08-20 924, 08-21 307, 08-24 1,981, 08-25 574. No file exists for 08-03..08-12, so the exact start day cannot be seen in our data: between 07-31 and 08-13, consistent with 08-03 | 08-13..08-25 |
| `senses` (per-frame rows) | 9,985-18,987 rows/day stamped 15:30:00-15:40:01 on every full day 08-21..09-23 (09-03 and 09-04 have only ~50 rows stamped 16:16-16:55, and 09-11 has 1,499 rows running to 17:42; 08-20 and 08-26 are partial days); 9-34 rows at 15:30:00 from 09-24 | 08-21 .. 09-23 |
| `vpin_log` / `vpin_fast` | Buckets completed 15:30:11-15:39:42 on 14 of 21 days (08-25 .. 09-22; 09-03, 09-04 and 09-11 also carry stray 16:16-17:42 buckets) and 2 fast buckets on 09-23; none from 09-24 (VPIN buckets close on volume, so they need trades) | |
| `trigger_log` | 32 rows with `t` 15:30, 15:33 or 15:36 (3-minute bars) on 08-25, 08-27, 09-03, 09-04, 09-09, 09-10, 09-15, 09-16: signals fired on the last-ten-minutes bars | |
| `ofd_marks` | Marks stamped 15:30 (09-21) and 15:35 (09-22) | |

**Nothing recorded after 15:30 on any day:** the option chain (poller gate, last rows 15:29:50-15:30:07; one stray SENSEX row 09-04 16:16:19), `chain_backfill` (cut at 15:30 though Upstox serves candles to ~15:39, `chain_backfill.py:52`), `calls`, `desk_log`, `sequence`, `hold`, fold. Options trade in the same window (assumed from the circular: "equity derivatives"); the record has no option data for it.

**Q1 for Upstox ticks and prints:** there is no tick or print feed (section 2); the book is the only Upstox record and is 15:30-15:40 on 09-22 and 09-23 only.

### 8.3 Q2: every place TapeMap cuts at 15:30 (file:line, no code changed)

*Recorder and write gates (they decide what reaches disk):*

| file:line | What it does |
|---|---|
| `chain_live.py:52` `SESS_CLOSE = 15*3600 + 30*60`; `:59-65` `in_session()` (`SESS_OPEN <= sec <= SESS_CLOSE`); `:441-468` warm start filter; `:299` comment | The gate the chain poller, `calls`, the hold loop and the book hook all use. Nothing polls or is recorded after 15:30:00 |
| `server.py:753-756` `live = in_session(now)` -> `_hook_book(feed, live)` `:1147-1153` (`feed.on_frame = None` outside) | Turns the book, ux, senses and VPIN recorders off at 15:30. The comment says the feed "runs on to ~15:40 and every recorder wrote it down -- ~6 MB of a closed book a day (operator, 2026-09-23)". That book was a live book |
| `server.py:1125-1128` `SESSION_END_HHMM = "15:30"`; `:1131-1143` `_session_only`; `:3064-3068` (the call site) | Trims the extension's POST (bars, marks, forming bar) before the frame build, `frame_log`, `tape_log`, the ladder file and the scorer. This is why `tape_NIFTY_*` stops at 15:25 from 09-24 |
| `server.py:974-1000` `_session_payload` | /api/data served without bars at or after 15:30 |
| `server.py:1460-1463` `_board_asof` (`min(now, SESSION_END_HHMM)`); `:1798` (`"09:15" <= m < "15:30"` for the chain minute grid); `:2732-2746` `_hold_loop` (`in_session(now - 90 s)`, comment "the 15:29 minute finishes at 15:30:00"); `:4636` (calls minute gate); `:588-592` (desk_log refusal note); `:2651` ("09:15-09:17 close"); `:882` (the day-state save is deliberately unconditional) | Board, chain grid, hold forward log and calls cut at 15:30 |
| `live.py:430` `SESSION_END_HHMM = "15:30"`; `:552-555` (1-minute FUT bars cut `b["t"] < SESSION_END_HHMM`, comment "15:30 and 15:35 on 2026-09-24"); `:355-363` (prior-day option candles cut); `:1191` (`expiry + " 15:30"` for T) | The FUT 1-minute tape drops 15:30-15:39 at build time; the prior-day H/L/C is cut |
| `chain_backfill.py:56` `SESSION_END = "15:30"`; `:315`, `:321` | REST backfill cut |
| `calls_log.py:7`, `desk_log.py:53,84` (`market_hours`: Mon-Fri 09:15-15:30), `sequence.py:65` (Mon-Fri 09:15-15:30) | Forward-log write gates |
| `eod_capture.py:23` ("Run it after 15:30"); the scheduled task "TapeMap EOD capture": **Start 15:35:00 Mon-Fri**, action `...\tapemap\eod_capture.bat`, Last Run 29-09-2026 15:35:00, **Last Result -2147024894 (0x80070002, file not found)**; `data/eod_capture.log` last entry 19-08-2026; last `fut_*.json` is 08-25 | Runs while the session is still open (a 15:35 run stores 379-382 bars; the same capture at 17:56 on 08-18 stored 385) and is not writing files now. A file once written is never replaced without `--force` (`eod_capture.py` docstring) |

*Session-time constants in engines and views:*

| file:line | What it does |
|---|---|
| `fold.py:50` `SESSION_OPEN, SESSION_CLOSE = "09:15:00", "15:30:00"`; `:270` (`SESSION_OPEN <= hms(t) <= SESSION_CLOSE`); `fold_live.py:179` (`close_ms = fold.ms(day, fold.SESSION_CLOSE)`) | The fold/hold engine treats 15:30:00 as the end of the day |
| `hold.py:24,60` (`SESSION = range(9*60+15, 15*60+30)`, "one record per session minute 09:15..15:29"); `plan.py:24` (`LAST = len(hold.SESSION) - 1  # 15:29`); `expression.py:525`, `validate.py:311`, `hold_log.py:4` ("15:29") | 375-minute grid; every "to 15:29" outcome |
| `visit.py:57` `SESSION_END = "15:30"`, `:182-183`; `trendbox.py:36` `OPEN, CLOSE = "09:15", "15:30"` | Visit and trend-box session bounds |
| `surface.py:61,163`, `chain_live.py:210` (`t_years`), `engine.py:1260` ("On expiry day ... SETTLE at 15:30"), `live.py:1191` | Time-to-expiry ends 15:30; option settle assumption. Whether expiry-day options also run to 15:40 is unverified |
| `server.py:4420` (`min(late, 375)`), `trigger_log.py:701` (`FLAT_BY_MIN = 15*60+15`, a scoring choice, not a session bound) | 375-minute cap; scoring cut at 15:15 |
| `band_rotation.py` | No 15:30 literal (checked); works on whatever bars and labels it is given, so it is fed the cut series |
| UI: `ui/console.html:176` (`mins <= 930`); `ui-v2/src/App.tsx:56`; `board/BoardRev3.tsx:97` (`LAST_M = 15*60+29`), `:437` (`m >= 15*60+30` = after close); `flow/FlowTab.tsx:66` (`CLOSE = 15*60+30`); `war/WarTab.tsx:76`; `vpin/VpinTab.tsx:176`, `:286`; `hold/HoldTab.tsx:181`; `hold/parts.tsx:119-120`; `pro/Pro.tsx:56` | Axes and "after close" states end at 15:30 |
| Extension (`orderflow-desk/src`) | **No session cut at all**: `main.js` posts every closed bar; `panel.js:227` only shows "flat by 15:00" before 15:30. The 15:30 cut is server-side |

Tests carry the same constant (`test_*.py`); not listed.

### 8.4 What this cost, and what is recoverable

- **Lost for good** (not in any file): Upstox book, ux, senses, VPIN for 15:30-15:40 on 09-24, 09-25, 09-28, 09-29; the option chain for 15:30-15:40 on every day since 08-20; NIFTY tape bars 15:30/15:35 for 09-24 (export has them), 09-28 (no export) and 09-29 (export has them). 09-29 is the Sep expiry day: its last ten minutes hold 1,800 lots and OI 7,151,885 -> 7,120,295 (-31,590 units, -486 lots, 15:25 -> 15:35).
- **Recoverable now:** GC bars 15:30/15:35 for 09-24 and 09-29 from the IndexedDB exports; 09-22 and 09-23 book rows (already on disk; from the 7-day rule they are gzipped after 09-29); FUT 1-minute candles through 15:39 for today (09-29) from Upstox `historical-candle/intraday` (`upstox_rest.intraday`), which serves only the current day, and a Sep-contract key that leaves the dump after today (section 4).
- **Mislabelled in old data:** the 15:30-15:40 rows in senses, VPIN, `trigger_log` and the 09-22/09-23 book were treated as "after close" (32 trigger rows scored, 14 VPIN days with extra buckets).
- **For the reader design:** the session axis is 09:15-15:40, 77 five-minute bars; the first 15:30 bar and the 15:40 closing print are inside it. The derivatives closing price is the VWAP of 15:10-15:40 (per the circular summaries), not 15:00-15:30.

## Not verified

- The circular itself (secondary sources only); expiry-day option settlement and last trading time.
- How GoCharting decides BUY/SELL on a tick (only its behaviour: closer to a quote rule than a tick rule).
- Whether GoCharting serves footprints for a second-month NSE symbol; the Upstox `full` subscription limit; whether expired Sep candles stay available by REST after today.
- Why the Upstox record starts at 09:17 on every day (only that both book and chain start there).
- That the dump's `tick_size` is in paise: inferred from the observed 0.1 / 0.2 / 0.05 price steps and the values 10 / 20 / 5.
- Data written after this audit began (server was running, `tape_NIFTY_2026-09-29` last modified 16:08; the day was closed and complete at read time).
