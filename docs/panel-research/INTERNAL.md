# INTERNAL: what our data can honestly measure for a "rate and speed" panel (20 Oct 2026)

**What Mary asked for:** the rate and speed of change of buyers and sellers, each side separately, read as order flow; the
rate and build speed of OI; a clear read of trend; an eye on the other indices.

**What this file is.** An audit of what the recorded data supports. It does not design the panel.

**Rules followed:**
- Descriptive only, on SEEN days. These are distributions of the inputs themselves. Nothing here is a hit rate or a
  forward-return test.
- No server or extension was touched. No HTTP calls were made. Nothing was committed. Nothing was written outside
  `docs/panel-research/`.

**Scripts and outputs** (`docs/panel-research/scratch/`, run with `python -B`):

| Script | What it does | Output |
|---|---|---|
| `pr_build1m.py` | 1-min and 5-min bars rebuilt from the book ticks with the repo's own `ladder.Ladder` (FLOW-STATE's builder, now with 19 Oct) | `pr_1m_<IDX>.json` |
| `pr_cadence.py` | Update cadence of the feeds | `pr_cadence_out.txt` |
| `pr_flowrate.py` | Rates and speed | `pr_flowrate_out.txt` |
| `pr_flowrate2.py` | Variance ratio and delta speed | `pr_flowrate2_out.txt` |
| `pr_oi.py` | OI noise floors | `pr_oi_out.txt` |
| `pr_gc5.py` | GoCharting (GC) vs Upstox (UX) 5-min rates per side | `pr_gc5_out.txt` |
| `pr_rules.py` | The two Upstox side rules compared | `pr_rules_out.txt` |
| `pr_checks.py` | GC vs UX per side, OI publication steps, strike-window misses, feed latency, senses sweeps vs chain volume | `pr_checks_out.txt` |

**Day sets used:**

| Set | Days | Notes |
|---|---|---|
| Upstox full tick days, all three indices | 22, 23, 24, 25, 28, 29, 30 Sep; 1, 5, 6, 8, 19 Oct (12 days) | 7, 9, 12, 13 and 16 Oct have tick holes and are excluded |
| Option-chain full days | 19 per index (21 Aug – 19 Oct) | |
| GC NIFTY days with at least 60 bars | 15 | |

Expiry days in the Upstox set:
- NIFTY: 22 Sep, 29 Sep (also the futures roll), 6 Oct, 19 Oct.
- BANKNIFTY: 29 Sep (monthly options).
- SENSEX: 24 Sep, 1 Oct, 8 Oct.

**No session has been recorded since 19 Oct.** There are no book, chain or Upstox bar files for 20 Oct. The server log
shows `getaddrinfo` failures that day.

---

## 0. The answer in eight lines

1. **Buyer and seller volume, per side:**
   - NIFTY has two sources: GoCharting (per trade, side from GoCharting) and Upstox (about 1-second book frames, side
     inferred).
   - BANKNIFTY and SENSEX have Upstox only.
   - Every index has a buy/sell split. None of it is an exchange-stamped aggressor side.
2. **Resolution:**
   - Upstox can be rebuilt at 1 minute or finer, both live and in history.
   - GoCharting is tick-level live in the page, but its **history is 5-minute closed bars only**.
3. **A 3-minute rate is mostly noise.** About 74% of the within-half-hour variance of a NIFTY 3-min buy or sell rate is
   reproduced by randomly reordered minutes. Two more facts point the same way:
   - In 58% of the top-decile 3-min buy windows, one minute carries half or more of the volume.
   - Slot-ranked rate extremes are mostly a day-volume flag.
4. **Speed as a first difference is mostly noise.** In this file "speed" means the change in rate, and "first
   difference" means rate now minus rate 5 minutes ago (the 5-min windows on both sides do not overlap). Five minutes
   later that difference keeps its sign only 38% of the time. It is also mechanically tied (ρ −0.42) to its own previous
   window.
5. **The short/long ratio is more stable.** Rate over the last 5 min ÷ rate over the last 30 min:
   - keeps its side 62% of the time;
   - lag-5 ρ +0.30;
   - is not tied to its base;
   - exists only from 09:47.
6. **OI is published about every 60 s on NSE (futures and options) and about every 160 s on BSE.** One minute is the
   finest OI rate for NIFTY and BANKNIFTY; about 3 minutes for SENSEX. A 15-min OI build is only moderately persistent
   (ρ 0.29–0.40), and its first difference is as big as the build itself.
7. **Cross-index:**
   - TapeMap already computes, for all three indices: price, the READ word, VWAP crosses (ranked), Upstox flow ranks,
     fuel ranks, writers, plus a shadow cross-index read.
   - **The extension's frame carries none of the other indices.**
8. **What would close the gaps** (G1–G11, §8):
   - The smallest data additions: a per-minute GoCharting snapshot (server only), and recording the option frames that
     already arrive on the socket. Before that, the option sweep events the `senses` log already writes can be studied.
   - The rest are code, not data: a day-kind split in one reference, one Upstox side rule, and a `frame.peers` key.

---

## 1. Capability table

"Noise floor" is the measured spread, or the share of a reading that is noise; the numbers are in §§3–5. Units: lots per
minute for flow; L = lakh units for option OI; lots for futures OI.

**Order flow, per side**

| Measure | Index | Source | Resolution | Latency | Noise floor | Already computed where |
|---|---|---|---|---|---|---|
| Buy and sell volume per side, live | NIFTY | GC ticks (`RECEIEVEDTRADE`, GoCharting's BUY/SELL per trade, `adapter.js:127-134`) | Per trade in the page. Posted as the forming 5-min bar every 1 s (`main.js:400`) | Sub-second in the page. TapeMap gets the forming bar every 1 s and never records it | Live only. No history below 5 min, so it cannot be ranked below 5 min | The page builds the forming bar. `session.since()` can give buy/sell since any time; no panel row uses it |
| Buy and sell per side, history | NIFTY | GC `tape_NIFTY_<day>` (`buy`, `sell`, ladder per bar) | 5-min closed bars; 20 days; 15 with at least 60 bars | Bar close plus the next tick | 5-min buy rate by slot: p10/p50/p90 = 13/29/86 (10:45) to 37/95/180 (09:15) | `rank_build.flow_ref` (SIZE, SHARE, RVOL), `v2.flowState` |
| Buy and sell per side, live and history | NIFTY, BANKNIFTY, SENSEX | Upstox book frames (`book_log`): median frame gap 0.9 / 1.2 / 0.9 s; arrival is 0.46 s after the feed timestamp | Live 1-s bars (`v2feed._tick`); 5-min Upstox bars (`ux_log`); 1-min rebuildable from the book | 1-s bars at once. Upstox 5-min bar at its close. On the frame: up to 20 s (`V2_EVERY`, `server.py:1719`) | 3-min: 74% (NIFTY) / 79–80% (BANKNIFTY) / 91–93% (SENSEX) of within-slot variance is i.i.d. minute noise | `read.Flow` (CVD since the open), `rank.card_ranks` (bar SIZE, cvd40), `frame_v2.ux_part` (sign check only) |
| Delta per bar, two-source agreement | NIFTY | GC vs Upstox on the same bars | 5 min | — | Sign agrees in 601 of 851 bars (70.6%); per-side volume r 0.91 / 0.90; Upstox leans sell (median buy share 0.451 vs 0.495) | `rank.two_source`; the ABHI "GC+UX ✓ / sources disagree" tag |
| Flow rate at 1 / 3 / 5 / 15 min | NIFTY, BANKNIFTY | Upstox, 1-min from the book | Any window of 1 min or more, ranked leave-one-day-out by slot | Live from the 1-s bars | Slot p10–p90 spread is 6–11× (e.g. NIFTY 3-min buy, 10:45: 12–79); extremes track day volume (ρ 0.76 / 0.90) | **Not computed.** Nothing ranks a sub-5-min rate today |
| Flow rate | SENSEX | Upstox | 15-min bars with a 30-lot floor are the honest grain | Median 42 s since the last trade at a frame | 3-min rate p10 = 0 in every slot; 91–93% i.i.d. | `rank.LOT_FLOOR`, `BAR_MIN` (15 min) |
| Speed: first difference (rate now minus 5 min ago) | All | Upstox, 1 min | From 09:27 | — | Sign kept at +5 min 38%; ρ −0.42 with its own previous window; tracks day volume (ρ 0.27–0.85) | Not computed. FLOW-STATE dropped the 5-min-bar version (§4.1) |
| Speed: ratio (5-min rate ÷ 30-min rate) | All | Upstox, 1 min | From 09:47 | — | Side kept at +5 min 56–62%; ρ −0.07 with its base; tails above the shuffle null on NIFTY and BANKNIFTY | Not computed |

**OI**

| Measure | Index | Source | Resolution | Latency | Noise floor | Already computed where |
|---|---|---|---|---|---|---|
| Option OI per strike | NIFTY, BANKNIFTY, SENSEX | Upstox chain (`chain_<IDX>_<day>`), 17 strikes, one row every 11 s | OI changes every 63 s (NSE) / 158 s (BSE); 82.5% / 93.5% of rows repeat the last OI | About 11 s plus the exchange's 60–160 s | ATM±2 per strike-leg, 5 min, NIFTY normal days: median 0.8–1.9 L (1.2–2.7% of the leg's OI); expiry days 3–5× that | `read.writers` (nine strikes, A, ce30/pe30); `frame_v2.writers_part` (ATM±2, 30 min, ranked); `read._quits`; `rank.ce30/pe30` |
| OI build speed (15-min build minus the previous 15 min) | All | chain | 1 min | — | Median size of the change in pace is 1.11–1.15× the median build; persistence ρ 0.40 (NIFTY), 0.34 (BANKNIFTY), 0.29 (SENSEX) | Not computed |
| Futures OI | All | Upstox book `oi`; GC bar `oi` (NIFTY) | Changes every 60 s (NSE) / 162 s (BSE); about 366 / 100 changes a day | About 1 s plus the exchange cadence | NIFTY 5-min \|ΔOI\| median 58–238 lots (0.02–0.09%); 15-min persistence ρ 0.37. Publication steps (\|ΔOI\| > the bar's volume) in 3.4% of 5-min bars | `rank.foi` + `fuel_word` (40 min, /api/read); `v2.fuel` (GC, current 25-pt leg, the extension's DIN row) |

**Trend and cross-index**

| Measure | Index | Source | Resolution | Latency | Noise floor | Already computed where |
|---|---|---|---|---|---|---|
| Writing vs buying (the IV residual) | All | chain IV | 30 min | — | ±0.25 vol-point dead band | `read.writing_vs_buying` (display only, /api/read card `wb`; not on the frame) |
| Option-side sweeps, sided [I] | All, ATM±3 legs (`SENSES_EACH_SIDE = 3`) | `data/senses/senses_<day>` sweep, absorption and pull rows on option frames (36 days since 20 Aug; 258 MB on 19 Oct) | Per event (a frame that took levels), not a volume series | Live | Not measured. On 19 Oct, swept `traded` summed to 47–56% of the chain's day volume on the six busiest NIFTY legs | `senses.py` (forward-logged, gates nothing). **Unstudied for flow** |
| Trend: VWAP crosses so far | NIFTY on the panel; all three in /api/read | GC bars (panel); Upstox bars (rank `x`) | 5-min closes | Bar close | Ranked per checkpoint (N ≈ 15–17 days) | `v2.crosses` + `ref.crosses`; `rank.cross_closes` |
| Cross-index | All | Upstox book, chain, reader legs | 3 min (xindex), 5 min (READ) | — | — | `xindex.py` (shadow; /api/xindex; `data/xindex/`). **None of it is on the frame** |

---

## 2. Buyer and seller flow, side by side (Q1)

### 2.1 Sources

**GoCharting (NIFTY only).**
- **How the side is set.** The extension reads GoCharting's own `RECEIEVEDTRADE` ticks, each with `side` BUY/SELL. A
  tick with no side is skipped and counted (`adapter.js:127-134`). The method behind GoCharting's side is unknown to us.
- **The forming bar.** It is built tick by tick. Each second the page posts `closed` plus `forming`, with buy, sell,
  delta and the ladder (`main.js:391-400`).
- **Every v2 read uses closed bars only:** `flowState`, the ABHI tag, the marks. A bar counts as closed once the next
  bar's first tick arrives (`session.js:51`). So **the 5-min flow tag is known only at the bar's close.**
- **What uses the forming bar:** only the live BADA-print bubble (`main.js:248`) and band taps.
- **What TapeMap keeps.** It gets the forming bar every second but never records it. `tape_log` writes closed bars only
  (`tape_log.py:17-19`). **GC history is therefore 5-minute bars: 20 days, 15 with at least 60 bars.**
- **On a mid-day tab open,** GoCharting replays history as coarser snapshot bars (`fromTicks:false`).
- **One index at a time.** The page locks to one symbol (`S.symbol = 'NIFTY-I'`, `panel.js:95`; `main.js:125`). Only
  `tape_NIFTY_*` exists.

**Upstox (all three indices).**
- **The feed.** The book recorder keeps every changed frame of each future. Median gap between frames: 0.91 s (NIFTY),
  1.19 s (BANKNIFTY), 0.90 s (SENSEX), over the 12 full days. On 19 Oct, arrival was a median 0.46 s after the feed's
  `currentTs` (p90 0.70 s; this includes the PC clock offset).
- **Side is inferred per frame pair, not per trade.** Each frame aggregates about 1 s of trading, so several trades share
  one side.
- **How thin SENSEX is.** On 19 Oct, at a SENSEX frame, the time since its last trade was a median of **42 s** (p90
  187 s). For NIFTY it was 1.2 s; for BANKNIFTY 3.7 s.
- **BANKNIFTY and SENSEX have a buy/sell split.** It is Upstox's alone, so single-source by rule (`rank.py`: "UX only").

### 2.2 GoCharting vs Upstox, per side (NIFTY, 851 matched 5-min bars, 12 days; the 09:15 bar left out)

| | GC vs Upstox |
|---|---|
| Buy volume | Pearson 0.91; median Upstox/GC 0.94; per-bar \|log ratio\| p50 0.19, p90 0.58 |
| Sell volume | Pearson 0.90; median Upstox/GC 1.07; \|log ratio\| p50 0.17, p90 0.46 |
| Buy share b/(b+s) | Pearson 0.58; median GC 0.495, Upstox 0.451 (Upstox leans sell) |
| Delta sign | agrees in 601 of 851 bars (70.6%); FLOW-STATE found 543 of 766 |

**Per-side rate by slot is source-dependent** (`pr_gc5_out.txt`, 5-min bars, lots/min, p50):

| Slot | GC sell | Upstox sell |
|---|---|---|
| 10:15 | 46 | 54 |
| 14:15 | 61 | 81 |
| 14:45 | 69 | 100 |

**So one source's rank cannot be read against the other's history.**

### 2.3 Three Upstox side rules on the same frames (a finding)

| Rule | Where | How it sets the side |
|---|---|---|
| ladder | `ladder.py`, the Upstox 5-min bars that `rank.py` ranks against | Quote rule, then the mid rule, then a depth march that splits the frame's volume across sides |
| v2feed | `v2feed._tick`, THE READ's FLOW | Gives the frame's whole volume to one side: quote rule, then the tick rule, else the last side |
| vpin | `vpin.py` | Tick rule |

THE READ's CVD (v2feed rule) is ranked against the ladder-rule history (`rank.card_ranks`, `read_side`). Re-run on 6
days (`pr_rules_out.txt`), comparing the v2feed rule with the ladder:

| Index | 5-min increments correlate | Sign agrees |
|---|---|---|
| NIFTY | 0.78–0.96 | 75–97% |
| BANKNIFTY | 0.93–0.99 | 86–96% |
| SENSEX | 0.95–1.00 | 84–97% |

NIFTY day CVD at the close, v2feed rule vs ladder, on three of the six days:
- 23 Sep: **+1,725 vs −2,653**, opposite signs.
- 19 Oct: −2,427 vs −32.
- 5 Oct: −727 vs −1,787.

Under the two rules this is two numbers, not one.

### 2.4 Latency, summarised

| Source | When it is known |
|---|---|
| GC 5-min flow tag | At the bar's close (plus the next tick) |
| Upstox 1-s flow | Live, inside TapeMap only |
| Upstox 5-min bar | At its close. Reaches the page within about 20 s (the v2 parts recompute at most every 20 s) |
| Option-chain row | Every about 11 s |
| OI | Every about 60 s (NSE) / 160 s (BSE) |

FLOW-STATE §1.7 measured the cost of waiting for the 5-min close:
- A rolling 5-min window first showed p90 a **median of about 2 minutes before** the grid bar closed.
- 34 of 108 rolling episodes never showed on the grid at all.

---

## 3. Rate: windows and noise floor (Q2)

### 3.1 Which windows are possible

| Window | Upstox live | Upstox history | GC live | GC history |
|---|---|---|---|---|
| 1 min | yes (1-s bars) | yes, rebuilt from the book, 12 full days | yes (ticks in the page) | **no** |
| 3 min | yes | yes | yes | **no** |
| 5 / 15 / 30 min | yes | yes | yes | yes (5-min bars and their sums) |

Every rank is provisional: 12 full Upstox tick days, 15–18 GC days, against `PROV_N` 30.

### 3.2 NIFTY buy and sell rate by 30-minute slot

Units are lots per minute. Upstox, 12 full days, pooled over days and minutes. The slot is the 30-min block of the
window's end minute; "09:15" is 09:15–09:44. All values are p10 / p50 / p90.

| Slot | Buy, 3-min | Buy, 15-min | Sell, 3-min | Sell, 15-min |
|---|---|---|---|---|
| 09:15 | 34 / 91 / 227 | 43 / 90 / 179 | 54 / 113 / 282 | 78 / 119 / 220 |
| 09:45 | 20 / 52 / 139 | 35 / 69 / 138 | 26 / 68 / 168 | 38 / 89 / 163 |
| 10:15 | 15 / 40 / 97 | 26 / 48 / 77 | 24 / 54 / 148 | 32 / 56 / 138 |
| 10:45 | 12 / 30 / 79 | 20 / 41 / 73 | 17 / 44 / 118 | 29 / 61 / 104 |
| 11:15 | 12 / 31 / 92 | 18 / 35 / 95 | 15 / 35 / 89 | 23 / 39 / 81 |
| 11:45 | 15 / 37 / 99 | 24 / 41 / 74 | 13 / 40 / 104 | 18 / 44 / 92 |
| 12:15 | 16 / 45 / 100 | 27 / 50 / 90 | 14 / 44 / 139 | 23 / 50 / 139 |
| 12:45 | 14 / 44 / 155 | 16 / 52 / 122 | 14 / 47 / 176 | 20 / 56 / 213 |
| 13:15 | 11 / 38 / 108 | 16 / 46 / 96 | 14 / 49 / 147 | 19 / 58 / 137 |
| 13:45 | 16 / 54 / 140 | 18 / 60 / 118 | 14 / 50 / 151 | 23 / 53 / 199 |
| 14:15 | 17 / 54 / 163 | 32 / 67 / 141 | 19 / 81 / 180 | 31 / 80 / 152 |
| 14:45 | 19 / 60 / 183 | 24 / 59 / 153 | 33 / 92 / 199 | 37 / 93 / 194 |
| 15:15 | 20 / 65 / 162 | 25 / 66 / 228 | 26 / 75 / 183 | 46 / 92 / 201 |

Day volume runs 26,099–84,235 lots (3.2×). The buy share of day volume runs 0.36–0.55.

BANKNIFTY at 11:15, 3-min buy: 2.3 / 10.3 / 35 lots/min. SENSEX at 11:15, 3-min buy: 0 / 0.33 / 4.0 lots/min.

### 3.3 How much of a short-window rate is noise

All rows are NIFTY, Upstox, slot-ranked leave-one-day-out. The null shuffles the minutes inside each day × 30-min slot:
time of day and day level are kept, the order inside the half hour is destroyed.

**1. Variance share of log rate** (time of day / day level / within day × slot):

| Rate | Time of day | Day level | Within day × slot |
|---|---|---|---|
| 3-min buy | 0.10 | 0.16 | **0.74** |
| 3-min sell | 0.13 | 0.13 | 0.74 |
| 15-min buy | 0.13 | 0.25 | 0.62 |

**2. Share of that within-slot variance that i.i.d. minutes reproduce** (variance ratio, `pr_flowrate2`):

| Window | NIFTY | BANKNIFTY | SENSEX |
|---|---|---|---|
| 1 min | 1.00 | 1.00 | 1.00 |
| **3 min** | **0.74** | 0.79–0.80 | 0.91–0.93 |
| 5 min | 0.65 | 0.70–0.73 | 0.85–0.88 |
| 15 min (60-min shuffle block) | 0.46–0.51 | 0.48–0.52 | 0.76–0.78 |

Read: about three quarters of a 3-min rate's swing inside its half hour is what randomly ordered minutes give. Real
clustering, meaning bursts that last several minutes, shows up only at 5–15 min.

**3. Swing of the slot rank between adjacent 3-min windows.** Median 16.1 percentile points, against 17.3 [16.8–17.9]
under the shuffle (sell: 14.7 vs 15.7). At 1 min: 17.0 vs 22.3, so single minutes do persist a little.

**4. One minute carries the window.** Of the top-decile windows, the share where the biggest minute holds half or more
of the window's volume:

| Window | Buy | Sell |
|---|---|---|
| 3 min | **0.58** | 0.53 |
| 5 min | 0.27 | 0.21 |
| 15 min | 0.06 | 0.05 |

This matches FLOW-STATE §1.7, where nearly half of PUSH-sized 5-min bars were one-minute events.

**5. A day-volume flag.** The share of a day's 3-min windows at or above the slot p90 runs **2%–30%** by day (buy). Its
Spearman with day volume:

| Rate | ρ with day volume |
|---|---|
| 3-min buy | **0.76** |
| 3-min sell | 0.90 |
| 15-min buy | 0.69 |
| 15-min sell | 0.90 |

The same trap FLOW-STATE §1.2 found for RVOL (ρ 0.95).

**6. The delta rate itself barely persists.** Adjacent-window Pearson:

| Window | NIFTY | BANKNIFTY | SENSEX |
|---|---|---|---|
| 1 min | 0.12 | 0.21 | 0.09 |
| 3 min | 0.18 | 0.24 | 0.07 |
| 5 min | 0.16 | 0.26 | 0.06 |

The NIFTY 3-min delta keeps its sign 64% of the time. FLOW-STATE's 5-min GC lag-1 correlation was 0.108.

**Answer to "is a 3-min rate's swing mostly noise relative to its slot's spread?"** Yes. On NIFTY:
- about 74% of it is reproduced without any time order;
- its rank moves about 16 points between adjacent windows, as shuffled minutes do;
- 58% of its extremes are one minute;
- its extremes cluster on high-volume days.

SENSEX below 15 min is lattice noise.

---

## 4. Speed: the acceleration finding (Q2)

### 4.1 Why FLOW-STATE dropped acceleration, volume acceleration and the flip (exact reasons)

**Acceleration** (CVD slope now minus the slope 15 min ago; FLOW-STATE §1.5, §1.6, §6):
- It is mechanically anti-correlated with the previous window: corr(acc, slope₀) = **−0.69**.
- It needs six bars, so it is blind before 09:40 (146 of 1,169 bars have none).
- Its tail sits **inside the sign-shuffle null**: real p90 |acc| 64.0 vs null 62.3 [58.5–66.3].
- The day bootstrap puts its p90 at 47–77.
- Inside PUSH it adds nothing over "big delta that price followed" (22 : 13 vs BIG_other 28 : 18).

**Volume acceleration** (bar volume ÷ the mean of the last 15 min) overlaps RVOL: Spearman 0.55. Only one volume
measure is kept, the adaptive one.

**Delta flip:**
- Flip swing = |Δ_now| + |Δ_prev| by identity. Spearman with |Δ| is 0.75, and 23 of the 32 big sign-change bars are flip
  ≥ p90.
- Half of all bars flip by default: lag-1 r 0.108; 498 flips in 1,152 bars, 151 of them under p30.
- No state rule uses it.
- Its own row sits at its placebo: 20 WITH / 23 AGAINST against 66 / 69.
- It is kept as a display fact, written "−X → +Y".

The decode-loop spec §4 (the "Revised" block) records all three drops.

### 4.2 New measurement, 1-minute grain

Three ways to read speed were measured side by side on the Upstox 1-min data:

| Measure | Definition |
|---|---|
| First difference | `acc` = rate₅(t) − rate₅(t−5) |
| Ratio | `rel` = rate₅ ÷ rate₃₀ |
| Rank gap | `gap` = pct(rate₅) − pct(rate₃₀), each ranked against its slot on other days |

NIFTY, buy side (sell in brackets):

| Measure | First value | Lag-5 ρ | Same side at +5 min | ρ with its own base (mechanical) | p90 \|x\| real vs shuffle null [5–95%] | Top decile carried by one minute | Day-volume ρ of top-decile share |
|---|---|---|---|---|---|---|---|
| acc | 09:27 | **−0.33** (−0.31) | **0.38** (0.38) | −0.42 (−0.39) with rate₅(t−5) | 84.9 vs 71.2 [68.8–74.6] | 35 of 431 | 0.27 (0.48) |
| rel (log) | 09:47 | **+0.30** (+0.35) | **0.62** (0.62) | −0.07 (−0.09) with rate₃₀ | 1.00 vs 0.83 [0.80–0.86] | 44 of 402 | −0.34 (−0.18) |
| gap | 09:47 | +0.46 (+0.46) | 0.65 (0.67) | −0.44 (−0.42) with pct₃₀, by construction | 45.8 vs 38.5 [37.1–39.7] | 51 of 403 | −0.29 (−0.29) |

How to read the columns:
- **Same side at +5 min:** for acc, its sign; for rel, the side of 1.0; for gap, its sign.
- **Top decile carried by one minute:** the count whose value drops below its own p70 when the 5-min window's biggest
  minute is replaced by the window's median minute.

**BANKNIFTY** has the same shape:
- acc: lag-5 ρ −0.34, same side 0.37, ρ with its base −0.44, day-volume ρ 0.54 / 0.82.
- rel: lag-5 ρ +0.22 to +0.27, same side 0.58–0.61, ρ with its base −0.03 to −0.07.
- One difference: **rel's top-decile share is skewed toward low-volume days** (ρ −0.73 buy, −0.59 sell). Lumpy minutes on
  a quiet day give extreme ratios.

**SENSEX:**
- acc sits at the null: 5.20 vs 5.17 [4.80–5.40].
- rel is barely above it: 1.72 vs 1.66 [1.62–1.69].

### 4.3 The delta side

Measured on NIFTY. Two speed measures of the delta:

| Measure | Definition |
|---|---|
| First difference | `accΔ` = rate₅(Δ) now minus 5 min ago |
| One-sidedness shift | `shiftΔ` = Δ₅ ÷ V₅ − Δ₃₀ ÷ V₃₀ |

| Measure | Lag-5 r | Sign kept at +5 min | r with its base | p90 \|x\| real vs sign-shuffle null (FLOW-STATE's null, 100 runs) |
|---|---|---|---|---|
| accΔ | **−0.47** (i.i.d. gives −0.5) | 0.37 | −0.65 (FLOW-STATE: −0.69) | 110 vs 99 [95–104] (just above, at 1-min grain) |
| shiftΔ | +0.30 | 0.57 | −0.20 | 0.47 vs 0.39 [0.38–0.40] |

On BANKNIFTY the pattern is the same. On SENSEX the shift is lattice-bound: 1.0 means a fully one-sided 5 minutes.

### 4.4 Reading

- **A first-difference "speed" is mostly the noise of its two windows.**
  - On NIFTY its lag-5 r is −0.47, close to the −0.5 that independent windows give.
  - It flips sign within 5 minutes about 6 times in 10.
  - It is mechanically the negative of the previous window.
  - In lots per minute it is partly a day-volume number.
- **The short/long ratio, or the rank gap, is the stable form of "speed".**
  - It keeps its side about 6 times in 10.
  - It has positive persistence.
  - Its tail is above the minute-shuffle null on NIFTY and BANKNIFTY, so bursts lasting several minutes are real
    structure, not reordering.
  - The ratio form is free of its base and of day volume on NIFTY.
- **Costs of the ratio:**
  - It cannot exist before 09:47.
  - It overstates on thin days (BANKNIFTY ρ −0.73).
  - On SENSEX it is close to the null.
- **This describes the inputs. It says nothing about what follows.** FLOW-STATE's rule stands: flow states describe and
  do not predict.

---

## 5. OI: rate and speed (Q3)

### 5.1 Resolution, strikes, artefacts

**The option chain** (`chain_live` + `upstox_chain`; all three indices):
- A row every 10–11 s per index (p10/p50/p90 10 / 11 / 11 s).
- **The option OI inside it changes every 63 s on NSE and every 158 s on BSE** (ATM±2 update gap p10–p90: 52–63 s and
  157–168 s). So 82.5% (NSE) and 93.5% (BSE) of rows repeat the last OI.
- The rows also carry per-leg cumulative `vol`, `bid`, `ask`, `ltp`, `iv`, `delta` and `gamma`.

**Strike window:**
- **Every recorded day has 17 strikes fixed at the opening ATM** (one distinct strike set per full day).
- Over 19 full days, ATM±2 fell off the window on **0.9%** (NIFTY), **2.2%** (BANKNIFTY) and **6.8%** (SENSEX) of rows.
  ATM±4, THE READ's nine, fell off on 4.6%, 12.1% and 18.9%.
- On 19 Oct SENSEX spot (73,716) went below the window's floor (73,900).

**The 19 Oct change:**
- It is uncommitted (files dated 19 Oct 17:39) and has no recorded session yet.
- It *subscribes* ±16 (`upstox_instruments.py:72`) but *hands downstream and records* ±8, recentred on the live spot
  (`upstox_instruments.py:65`, `upstox_chain.near` at `upstox_chain.py:46`).
- **So the file stays 17 strikes. It will follow spot, but it will not be 33 strikes.**

**Futures OI:**

| Source | Index | Cadence |
|---|---|---|
| Upstox book `oi` | NIFTY, BANKNIFTY | Changes every 60 s (p10–p90 57–64 s NIFTY); about 366 changes a day |
| Upstox book `oi` | SENSEX | Every 162 s; about 100 changes a day |
| GC bar `oi` | NIFTY | Rides each bar |

Jump size per NIFTY update: p50 1,560 units (24 lots), p90 8,515 (131 lots); p99 0.25% of OI.

**Artefacts:**
- **Publication steps.** |ΔOI| larger than the bar's own volume shows in 29 of 889 Upstox and 30 of 813 GC NIFTY 5-min
  bars. It is the same exchange series on the same bars (for example 22 Sep 11:05, −73,710 on 18,460 traded). The
  decoder's OI guard (`decoder.js:11-14`) exists for this.
- **The open.** The book and chain recorders start 09:17:00–09:17:30 every day, so 09:15–09:17 is not in the Upstox
  record. The 09:15 Upstox 5-min bar is partial on every day (`rank.py:124`). The chain's "aaj likha" uses the 09:15 REST
  baseline (`oi_chg`), but there is no minute path before 09:17.
- **Blank OI.** No zero or blank OI leg appears in the first 5 minutes of any of the 12 full chain days (0 of 986 legs each
  day). **The blank OI lives in GC:** a bar whose OHLC was not joined has `oi` null, 4–46 bars a day on 5, 6, 7, 9, 12, 16
  and 19 Oct. The first bar's `oi` is null on 6, 7, 9 and 16 Oct.
- **Churn.** At one strike-leg, the gross minute-by-minute OI movement over 30 min is a median **2.3×** the net change
  (p10 1.15, p90 13). On a single strike, about half the OI movement cancels within the half hour.

### 5.2 Noise floor: option OI at ATM±2

Normal days, per strike-leg, lakh units (`pr_oi_out.txt`). The NIFTY figures are 12 normal chain days.

| | 5 min | 15 min | 30 min |
|---|---|---|---|
| NIFTY 10:15 slot, p10 / p50 / p90 | 0.22 / 1.47 / 6.36 | 0.61 / 3.58 / 13.98 | 1.13 / 6.31 / 27.3 |
| NIFTY 12:15 slot | 0.14 / 0.91 / 3.19 | 0.37 / 2.33 / 8.66 | 0.76 / 4.36 / 17.95 |
| NIFTY 09:15 slot | 0.75 / 3.97 / 15.45 (6.7% of OI) | 2.13 / 11.0 / 37.6 | — |
| NIFTY 15:15 slot | 0.4 / 2.4 / 9.0 | 1.21 / 7.15 / 22.9 | 2.42 / 10.5 / 33.5 |
| NIFTY expiry days, p50 / p90, mid-session | 3.5–6.4 / 12–29 | 8–19 / 26–70 | 14–26 / 55–115 |
| BANKNIFTY (monthly options) mid-session, p50 / p90 | 0.02–0.04 / 0.10–0.24 (0.7–1.5% of OI) | 0.04–0.08 / 0.18–0.46 | 0.07–0.15 / 0.31–0.82 |
| SENSEX mid-session, p50 / p90 | 0.07–0.17 / 0.44–0.67 (1.4–3.5%) | 0.18–0.49 / 0.94–1.8 | 0.27–0.62 / 1.8–3.2 |

**The NIFTY ATM±2 side sum over 15 min** (5 strikes, signed, L, p10 / p50 / p90, normal days):

| Day part | CE | PE |
|---|---|---|
| 09:15–10:00 | +5 / +59 / +162 | −2 / +29 / +126 |
| 10:00–12:00 | −15 / +12 / +52 | −17 / +9 / +42 |
| 12:00–13:30 | −11 / +8 / +30 | −23 / +4 / +28 |
| 13:30–15:15 | −58 / −7 / +23 | −59 / −4 / +25 |

The afternoon median is negative: OI unwinds.

**Persistence of the side sum** (adjacent windows, same ATM):

| Window | NIFTY | BANKNIFTY | SENSEX |
|---|---|---|---|
| 15 min | ρ **0.40**, same sign 0.66 | 0.34 | 0.29 |
| 30 min | 0.30 | 0.23 | 0.20 |

**Speed of build** (the 15-min build minus the previous 15-min build): its median size is **1.15×** the median build
itself on NIFTY (1.14 BANKNIFTY, 1.11 SENSEX). As with flow, a first difference of OI build is as large as the build it
differences.

### 5.3 Noise floor: futures OI

Normal days, non-roll, Upstox book.

| | 5-min \|ΔOI\| median (p90) | 15-min median | 30-min median (p90) | Persistence, 15 / 30 min |
|---|---|---|---|---|
| NIFTY, 7 normal days | 58–238 lots (203–824); 0.02–0.09% of OI | 182–1,140 | 306–1,155 (774–5,996; up to 3.6%) | 0.37 / **0.56** |
| BANKNIFTY, 10 days | 18–84 lots | 40–180 | 51–348 | 0.13 / 0.16 |
| SENSEX, 9 days | 1–6 lots | 3–21 | 6–26 | 0.19 / 0.31 |

The late-session slots (14:15–15:15) carry the largest NIFTY moves: 30-min p90 2,570–5,996 lots.

### 5.4 Can "OI build speed" per strike be ranked against prior days?

**Partly, and it already is, coarsely.** There are three existing ranks:

| Rank | What it pools | Days | Where it shows |
|---|---|---|---|
| `writers30` | ATM±2 30-min change, both legs pooled | Last 10 chain days | The extension's DIN "30m pNN" |
| `rank.ce30` / `pe30` | Nine-strike sum | By day-part and day kind | The Read tab |
| `foi40` | Futures OI change, 40 min | — | The Read tab |

**The defect.** `writers30` mixes day kinds:
- `rank_build.writers30` (`tools/rank_build.py:262-266`) takes the last 10 chain days with no kind filter.
- For NIFTY that means 1–19 Oct, which includes three expiry days (6, 13, 19 Oct) and five partial days (7, 9, 12, 13,
  16 Oct).
- Expiry-day ATM±2 moves are 3–5× normal (§5.2). So a normal day under-ranks and an expiry day over-ranks.

**Per-strike ranking (ATM+k × slot × day kind):**
- Feasible from the 19 full chain days per index.
- All provisional (N < 30).
- The EXPIRY bucket is too thin outside NIFTY: BANKNIFTY has 1 monthly expiry in the record (rank_ref `EXPIRY.chain`
  nd = 1), and SENSEX has 4–7. NIFTY reaches `MIN_DAYS` 5 barely, with 5–6 days.

### 5.5 What is already computed

| What | Where | Detail | Reaches the extension? |
|---|---|---|---|
| Writers, A and class | `read.writers` (`read.py:148`) | Nine strikes ATM±4 on the grid. aaj likha = OI now − yesterday's close. A = (CE−PE) ÷ (\|CE\|+\|PE\|). Classes CALL / PUT / BOTH_WRITE / BOTH_COVER / QUIET / MIXED / BLIND. Also ce30 / pe30 | Via `frame.read.writers` (A, class, ce30, pe30) |
| QUIT events | `read._quits` (`read.py:467`) | A strike-side within 2 steps of spot whose aaj likha peaked at ≥ 25% of the day's biggest single-strike add, then fell to ≤ 50% of its peak. Once per strike-side a day | In `frame.writers.quits`; the panel does not print them |
| Writing vs buying | `read.writing_vs_buying` (`read.py:254`) | Per strike of the nine: IV change minus the ATM IV change, weighted by the OI added over 30 min. Dead band ±0.25 vol point; [I] | **No**: only on /api/read (`card.wb`) |
| Fuel, TapeMap side | `rank.foi` + `rank.fuel_word` (`rank.py:162-181`) | Futures OI % over 40 min from the Upstox bars, × the price change. Words: naye long / naye short / covering / long chhod rahe, only at ≥ p70, else "OI flat" | /api/read only |
| Fuel, extension side | `v2.fuel` | GC bar OI over the current 25-pt zigzag leg, ranked against `ref.fuel` | **Yes**: the extension's DIN row |
| Writers on the frame | `frame_v2.writers_part` (`frame_v2.py:330`) | ATM±2 per strike, 30-min CE/PE change, rank against `writers30`, `fresh` = an add ≥ p90, the absent side, QUITs | Yes |

---

## 6. Cross-index (Q4)

**Live in TapeMap for BANKNIFTY and SENSEX:**

| What | Source |
|---|---|
| Futures price | Book `ltp`, about 1 frame a second; SENSEX trades about every 40 s |
| Spot | Chain row, about 11 s |
| VWAP and σ | The zone machine (`fold_live` runs all three: `ALWAYS = NIFTY, BANKNIFTY, SENSEX`); /api/contract (REST 3-min bars with VWAP ±σ); `rank.cross_closes` (Upstox hlc3 VWAP crosses) |
| Chain OI | 17 strikes; NSE OI every 60 s, BSE every 160 s |
| Futures OI | Book |
| Flow | Upstox only: READ FLOW CVD; `rank.py` bar SIZE, cvd40, foi40, crosses `x`; SENSEX on 15-min bars with a 30-lot floor |
| THE READ word | Per index (/api/read) |
| VPIN | Per future (story) |

**What the frame carries for other indices: nothing.**
- `frame.build` is built for the posting index (`frame.py:493`).
- `_frame_v2(idx, day)` is too (`server.py:1837`).
- The `fold`, `chain`, `story` and `validate` objects are per-index.
- The page posts only its locked symbol.

**Cross-index already computed:**
- **`xindex.py`, SHADOW** (`/api/xindex`, `data/xindex/xindex_<day>.jsonl`, every 3 min, unsigned threshold sheet):
  - X1 SYNC: do the legs point the same way, each in its index's own ruler;
  - X2 EXTREMES: TOOK / EQUAL / FAILED, then CONFIRMED / DIVERGENT;
  - X3 LEAD: who turned first;
  - X4 WALLS;
  - a LOOK HERE count;
  - a state word per index, from structure only.
  - SENSEX flow is a witness and never votes.
- **Per-index VWAP crosses-so-far** (rank `x`) and the READ word on /api/read. This is the O1 / "trend vs chop" measure.
- **Nothing combines them into one cross-index line.** The spec's §5.2 cross-index pass is not built.
- **Numbering note.** The spec's "NIFTY trended, BANKNIFTY chopped more" is **O7**. O9 is "if-then plans".

---

## 7. What the v2.4 panel shows today (Q5, `src/shell/panel.js`)

| Row | What it shows | Source | Ranked against normal? |
|---|---|---|---|
| Head, line 1 | Index · KHEL pill (RIDE ▲/▼ / FADE / BAITHO / ?) · SIZE pill (ADHA on a LEAN) · PREMIUM pill (the expression word, e.g. "BUY PE") | `frame.read.khel`, `.size`, `.expr` (READ and TapeMap's expression) | No: rule words |
| Head, line 2 | `fut f \| ≈spot s` · clock · bell | GC last price; `read.basis` | — |
| Head, line 3 | Feed dots (GC, TapeMap) · `ref ✓/?` · READ word, arrow, "since" · the 15:00 practice note · legend (P/R/T/Z/B/✕) | Frame; `rank_ref` | No |
| banner | "Extension reload hua", or "SPOT ? · basis …" when the basis is implausible | `read.basis` (carry band plus the options' parity) | Rule, not rank |
| khilaaf | Opposing, ranked, standing evidence within a row of price | `v2.khilaaf` (marks, deewars) | Yes: the marks and walls are ranked |
| 09:45 card (09:45–10:15 only) | \|A\| · absent side · open flow (GC Σ delta 09:15–09:40) · VWAP crosses · gap vs yesterday's close | `read.writers.A`, `frame.writers.absent`, GC bars, prior levels | Open flow: yes (`ref.open_flow`, one value a day). Crosses: yes (`ref.crosses[checkpoint]`). A and gap: no |
| DIN | Writers A · absent side + "30m pNN", or the class word · VWAP crosses × rank · fuel word + rank + "since" | READ writers; `frame.writers` (ATM±2, 30 min); GC crosses; GC OI over the current 25-pt leg | 30m: yes, but against a pool that mixes day kinds (§5.4). Crosses: yes. Fuel: yes (`ref.fuel`); below p70 it reads "OI flat". **A: not ranked here** (rank.py ranks \|A\| only on the Read tab) |
| ABHI | FLOW state of the **last closed GC 5-min bar** (PUSH↑/↓ (kharid/bech), CLIMAX · nateeja nahi, ROKA, noise, no read) · SIZE pNN · GC+UX ✓ / GC only / sources disagree | `v2.flowState` on GC bars; the Upstox bar's sign from `frame.ux_flow` | Yes: SIZE against the slot (`ref.flow`, all day kinds pooled). The Upstox check is sign only. **No rate, no speed, no rolling minute** (P-FS5 deferred) |
| SIRF BADE | Up to 6 marks: time · letter · name · price · rank N · ring @time · flow tag · TIKA/TOOTA · record counts; "baaki N chhote"; "pass bar: Mary ka" | `v2` episodes and marks (GC ladder, decoder) | Yes: by kind, other days, era B |
| PLAN | READ-V2 §E zone / kill / T1 with live points; RANGE fade zones with the page's [I] kill. In a trade: the FOLD board (ZONE / FLOW / OI / VPIN lamps, entry → now, HOLD / WATCH / FOLD) | `frame.plan` (3-min futures bars from the Upstox 1-s bars); `validate.lamps`; `fold.py` | No. Lamp ranks are deferred |
| act | MARK buttons at the money (chain slip) / I'M OUT | `frame.chain` | — |
| ? | Checked-nothing / could-not-check / not-shown | — | — |

**There is no row for:**
- buy rate and sell rate separately;
- any sub-5-min flow;
- any speed;
- futures-OI rate;
- per-strike OI speed;
- writing vs buying;
- any other index.

---

## 8. Gaps: what she asked for that we cannot measure honestly, and the smallest fix

**G1 · GoCharting buy/sell below 5 minutes (NIFTY).**
- The problem: it is live only. There is no history, so a 1- or 3-min GoCharting rate cannot be ranked against normal.
- Smallest fix, data: have TapeMap write a per-minute snapshot of the `forming` bar it already receives every second (t,
  minute, buy, sell, vol, delta, close) into a separate file, for example `tape/gcmin_NIFTY_<day>.jsonl`.
- Cost: about 375 rows a day; no extension change.
- When it can rank: provisionally from about 10 sessions; properly at 30.

**G2 · No GoCharting second source for BANKNIFTY or SENSEX.**
- The problem: those indices are Upstox only, and Upstox per-frame side inference agrees with GoCharting on delta sign
  only 70.6% of the time on NIFTY.
- Smallest fix: none small. A second GoCharting chart and post per symbol would be needed, because `main.js` locks to one
  `S.symbol`.
- Until then: tag the reading "UX only", as `rank.py` already does.

**G3 · SENSEX flow below 15 minutes.**
- The problem: a median day trades 1,430 lots, the median frame is 42 s after the last trade, the 3-min rate p10 is 0,
  and 91–93% of the 3-min variance is i.i.d.
- Fix: no data addition helps. Read SENSEX at 15 min with a 30-lot floor (as `rank.py` does), or show volume only.

**G4 · OI rate below 1 minute (NSE) or about 3 minutes (BSE).**
- The problem: the exchange publishes OI every about 60 s and about 160 s. It cannot be measured finer.
- Fix: none. A "3-min OI rate" on SENSEX is one or two updates.

**G5 · OI build speed ranked by day kind and by strike.**
- The problem: the extension's `writers30` pools normal, expiry and partial days.
- Smallest fix, code only: filter `writers30`'s days by `rank.day_kind` and skip partial days.
- Limit: EXPIRY cannot be ranked for BANKNIFTY (1 monthly expiry) and is marginal for SENSEX.

**G6 · Options-side buyers vs sellers** (who is buying or writing calls and puts as order flow).
- The problem: it is not measured as a volume series. Spec §10 says "no data".
- **What already exists:**
  - The option frames arrive on the same `full` socket (±16 subscribed). `book_log.Book.on_frame` drops every key it does
    not watch (`book_log.py:159-163`).
  - The `senses` log already writes sided [I] sweep events on the ATM±3 legs of all three indices (36 days, since 20 Aug).
    On 19 Oct their swept `traded` came to about half of the busiest NIFTY legs' day volume. Nobody has studied these rows
    as flow.
- Smallest step, no new data: describe the existing senses sweep rows per leg × minute, the way §3 does for the futures.
- Smallest fix, data: watch the ATM±2 option keys into their own book file, then run `ladder.Ladder` on it offline. That
  gives per-leg buy/sell on about 1-s frames, the same method and caveats as the futures.
- Cost: about 8 MB per leg per day, or about 240 MB a day for 30 legs before `daylog` gzips them [I].
- Until then the only proxies are the IV residual, which is not on the frame, and the senses sweeps, which are not on
  any screen.

**G7 · READ FLOW is ranked against a differently classified history.**
- The problem: `v2feed`'s rule (whole frame to one side) is ranked against `ladder`'s (depth split). On 23 Sep the NIFTY
  day CVD was +1,725 under one and −2,653 under the other.
- Smallest fix, code only: one rule. Either rank READ FLOW against v2feed-rule history, or read FLOW off the Upstox ladder
  bars.

**G8 · The other indices are not on the panel.**
- The problem: none of it is a data gap.
- Smallest fix, code only: an additive `frame.peers` key. For each other index it would carry the READ word and
  direction, the crosses-so-far rank, the cvd40 rank, the `foi40` fuel word and rank, and the writers class and A. All of
  these are already computed by `rank.card_ranks` for /api/read. Optionally add `xindex`'s SYNC and EXTREMES chips
  (shadow, unsigned).

**G9 · History depth.**
- The problem: every rank is provisional. The record holds 12 full Upstox tick days, 15–18 GC days and 19 full chain days.
  9, 12, 13 and 16 Oct have tick holes.
- Fix: no data addition. Keep the recorders up; time is the fix.

**G10 · The first minutes.**
- The problem: the Upstox book and chain begin 09:17:00–09:17:30 every day, so there is no Upstox rate and no OI path for
  09:15–09:17. A 30-min ratio and a 30-min OI change cannot exist before 09:47.
- What already covers part of it: GC covers NIFTY flow from 09:15.
- Smallest fix: find why both recorders start at 09:17. It is an operations question, not data.

**G11 · Speed as a first difference.**
- The problem: it can be measured, but it is mostly noise (§4).
- Fix: none needed in the data. The stable alternative is the 5 ÷ 30 ratio or the rank gap. Choosing one is a definition,
  and showing it is vocabulary, not a rule.

---

## 9. Limits

**The data:**
- All of it is SEEN: 12 full Upstox days and 19 chain days, and bars within a day are not independent.
- Nulls are minute shuffles within a 30-min (or 60-min) block. At a 15-min window the 30-min-block null is too smooth by
  construction, so swing comparisons are read only for windows of 5 min or less.
- Upstox side is a reconstruction [I]. GoCharting's side method is unknown.

**Day composition:**
- NIFTY expiry days (4 of 12) are pooled in the flow rate tables.
- They are separated in the OI tables.

**What the numbers are not:**
- Nothing here is a hit rate, and nothing should be quoted as one.
- No threshold, state or rule is proposed. Each number is a description of an input.
