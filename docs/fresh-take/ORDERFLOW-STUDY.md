# ORDERFLOW-STUDY — nodes, CVD, and the extension's marks, on recorded days

**Descriptive only.** Rows like "9 of 14". No verdicts; Mary signs no bar here, so every finding below is a **prereg candidate**, not a rule. Labels: **SEEN** = the 18 recorded sessions we have all looked at; **FORWARD-LOGGED** = the extension's marks and the decoder events, recorded live as the days happened (they were not tuned on, but the *code that produced them changed during the record*, §3.1). Every table says its n. Scripts: `fresh-take/scratch/study{1,2,3,3b,3c}.py`, `of_lib.py`. GET-only on the server; nothing outside `fresh-take/` was written.

## 0. Data, units, and what I added after looking
- **Price path.** 5–16 Oct: REST 3-min futures bars with VWAP ±σ (`/api/contract?days=10`, whole days incl. 14–15 Oct). 22 Sep–1 Oct: 3-min bars built from the Upstox book ticks. 21 Sep has no path, so its 82 marks are **excluded** from outcome tables. GoCharting (GC) 5-min closes agree with the path at 15-min boundaries (median difference 0.0 pt; max 30 pts on one 29 Sep boundary).
- **σ unit.** U = max(σ at the bar, 0.1% of price). The floor only bites in the first 30 minutes.
- **GC coverage is the binding constraint.** `tape_NIFTY`: full 75-bar days only on 21–24 Sep, 28–29 Sep, 1, 5, 6 Oct; 25 Sep ends 13:35; 30 Sep, 7, 8 Oct have 2–4 ten-minute holes; **9 Oct 54 bars to 13:55; 12 Oct 53 to 13:35; 13 Oct 9 bars to 09:55; 16 Oct 24 bars to 11:10; 14–15 Oct none.** Many GC rows carry `o`/`c` = null (footprint-only backfill); I filled those two fields from the path (flagged `filled`) and kept the ladder and delta as logged. Upstox `ux_*`: 5-min bars, full days 22 Sep–8 Oct, partial 9, 12 Oct, 8–9 bars on 13 and 16 Oct.
- **Marks cover:** NIFTY only. **Decoder rows:** 5, 6, 7, 8, 9, 12, 13 Oct (the 13 Oct file is short).
- **Added after seeing a first table (post-hoc, flagged where used):** the level-hold test and the baselines in Study 3; the shifted-level placebo in Study 1; 28 Sep and 6 Oct as extra trend days in Study 2 (chosen from my earlier survey, so hindsight); the 20-pt tolerance in the day-extreme table.
- **Multiple comparisons.** Roughly 150 cells are printed across the three studies (Study 3 alone ≈ 90: 6 kinds × eras, trend context, location, day type, hold). At that count a handful will look special by chance, and almost every cell below has n < 30. Read the tables as a map of where to look next, not as findings.

## 1. Study 1 — prior-day nodes: accept or reject

**Definitions, fixed before counting.** Prior-day profile from the GC ladder (`prints.profile`, `prints.nodes`): POC, VAH, VAL as points; HVN (top-3 five-point bins by volume) and LVN (bins ≤ 0.35 × median bin) merged into zones when adjacent. **Touch** = the first bar of the day whose range comes within 5 pts of the zone, arriving from outside (previous close outside); first touch per zone per day only. Within the next 30 minutes (6 bars): **ACCEPT** = 2 consecutive 5-min closes beyond the far edge; **REJECT** = a turn of ≥ max(0.5U, 10 pts) away from the near edge with no close beyond; else **NEITHER**. **Splits (two, chosen first):** ranked delta of the touch bar (rank among the session's bars so far, big = ≥ p80, with/against the approach) and day type (full-day VWAP crosses after 09:30: ≤ 4 / 5–8 / ≥ 9; hindsight). Test days need a full prior-day GC profile and no contract roll: **22, 23, 25 Sep; 5, 6, 7, 9 Oct** yielded touches (24 Sep, 29 Sep, 1 Oct, 8 Oct had none from outside or no usable prior profile; 28 and 30 Sep excluded: partial prior day and the Sep→Oct roll).

**GC ladders — 34 first-touches on 7 days (SEEN):**

| Node | touches | ACCEPT | REJECT | NEITHER | accept lag (bars after the touch bar) |
|---|---|---|---|---|---|
| POC | 4 | 1 | 3 | 0 | 5 |
| VAH | 5 | 2 | 3 | 0 | 3, 4 |
| VAL | 3 | 1 | 2 | 0 | 2 |
| HVN | 7 | 3 | 3 | 1 | 2, 3, 4 |
| LVN | 15 | 3 | 11 | 1 | 1, 2, 3 |
| **all** | **34** | **10** | **22** | **2** | |

- **Placebo (added post-hoc):** the same zones shifted −30 and +30 pts, same rules: 65 touches — ACCEPT 18, REJECT 44, NEITHER 3. By day type the placebo gives trend 9 / 18 / 1, mid 6 / 21 / 2, chop 3 / 5 / 0 (accept / reject / neither). **The real nodes look like the placebo at this n.**
- **Split 1 (delta at the touch):** big-with 7 → 3 / 4 / 0; big-against 0; noise (< p80 or < 6 bars) 27 → 7 / 18 / 2. No "against" cell exists to compare.
- **Split 2 (day type):** trend days (23 Sep, 6, 9 Oct) 14 → 7 / 6 / 1; mid (22, 25 Sep, 5 Oct) 15 → 3 / 11 / 1; **chop (7 Oct, one day) 5 → 0 / 5 / 0.** One chop day cannot carry a split.
- **Do LVNs get crossed fast?** 3 of 15 LVN touches were accepted (lags 1–3 bars, i.e. 5–15 min); 11 were rejected. Not seen. Note what `prints.nodes` calls an LVN: bins at or under 0.35 × the median bin, which on these profiles are mostly the thin **tails** of the prior day's range (its extremes), not interior air pockets. A "rejected LVN" is largely "the prior day's high/low held".
- **Do HVNs act as magnets?** Nodes within 0.75 × prior-day range of the 09:15 open that the day later touched: POC 4 of 9, VAH 5 of 8, VAL 3 of 9, HVN 8 of 18, LVN 16 of 27; shifted placebo levels 63 of 139. Not distinguishable. Dwell (bars closing inside the zone in the next 30 min, summed): HVN 7 over 7 touches, LVN 19 over 15.
- **Upstox ladders as a second source (SEEN, 4 days: 23, 25 Sep; 5, 6 Oct):** 20 touches — POC 0/1/0, VAH 1/2/0, VAL 1/0/0, HVN 1/3/0, LVN 2/9/0; placebo 39 touches 8 / 29 / 2. Same picture; the two sources are not independent days.

**Should nodes be LOCATION rows, entry zones, or both?** From this sample: **LOCATION rows only.** Nothing here separates a prior-day node from an arbitrary level, so there is no support for an entry zone, and the standard rules (practitioner sources describe LVNs as fast-travel air pockets and HVNs as sticky, with approach direction mattering — [LuxAlgo](https://www.luxalgo.com/library/concept/high-low-volume-nodes/), [Tradezella](https://www.tradezella.com/strategies/low-volume-node), none backtested) are neither confirmed nor refuted at n = 34. Candidate for a prereg: test **interior** LVNs (smoothed local minima inside the prior value area) with the placebo as a mandatory control.

## 2. Study 2 — delta / CVD for holding

**What pro order-flow traders do (practitioner sources, no statistics in them; the hold/trim/exit mapping is the search tool's synthesis):** hold while a new price extreme comes with a new CVD extreme; treat price making a new extreme while CVD does not as an early warning that needs price confirmation, not a reversal signal; read heavy volume with no progress as absorption and watch whether the level holds or gives way; trim on divergence at an extreme, exit the rest if absorption holds or a reversal confirms ([MQL5](https://www.mql5.com/de/blogs/post/772518), [LuxAlgo CVD](https://www.luxalgo.com/library/concept/cumulative-volume-delta.md), [TradingView script](https://www.tradingview.com/script/Vgitqk52-Order-Flow-Volume-Delta-CVD-Absorption-Divergence-LunqFX/)).

**Definitions, fixed before counting.** Trend direction per day by close vs open and VWAP side (hindsight): 28 Sep ↓ (added), 6 Oct ↑ (added), 8 Oct ↓, 9 Oct ↑, 12 Oct ↓, 13 Oct ↑, 16 Oct ↑. **Pullback** = from a new trend extreme, a retrace of ≥ max(0.75σ, 15 pts). **HELD** = a new trend extreme follows; **BROKE** = two consecutive closes beyond VWAP ∓ 0.25σ against the trend, or a close beyond the previous pullback's extreme, before one (re-armed only after a close back on the trend side). **Features (two):** (F1) CVD change during the pullback in trend terms (moved against / with); (F2) CVD made a new 60-min extreme against the trend at the pullback's end. **Extremes:** each new trend-extreme bar, CVD *confirmed* (at or beyond its prior-12-bar extreme) or *diverged*, and whether price made a further extreme within 60 min. Pullbacks with a data gap inside are dropped. GC delta for NIFTY, Upstox delta for BANKNIFTY.

**Coverage (what the named days actually support):** NIFTY 8 Oct 68 bars (5 gaps), 9 Oct 54 to 13:55, 12 Oct 53 to 13:35, 13 Oct 9 bars to 09:55, 16 Oct 24 bars to 11:10; BANKNIFTY full only on 8 Oct (plus 28 Sep, 6 Oct added); 9 and 12 Oct partial; 13, 16 Oct not usable.

| Set (SEEN) | qualified pullbacks, no gap | HELD | BROKE | CVD moved against / with during the pullback (HELD · BROKE) | CVD new 60-min extreme against (HELD · BROKE) |
|---|---|---|---|---|---|
| NIFTY, 7 days | 19 | 18 | 1 | 9 / 9 · 0 / 1 | 1 · 0 |
| BANKNIFTY, 5 days | 29 | 18 | 11 | 7 / 11 · 6 / 5 | 0 · 1 |

- **Pullbacks that held vs broke:** CVD during the pullback does **not** separate them here: about half moved against the trend and half with it in both groups. A new 60-min CVD extreme against the trend was rare in both (2 of 48). NIFTY has a single BROKE (16 Oct's opening bars, where the day's direction was not yet known), so NIFTY cannot be compared at all. BANKNIFTY's 11 BROKEs are mostly VWAP breaks on a market that crossed VWAP 11 / 9 / 17 times on 8 / 14 / 16 Oct.
- **Divergence at new extremes:** NIFTY, 54 extremes with CVD confirmed → each followed by a further extreme within 60 min (54 of 54); 13 diverged → 11 followed, 2 not. BANKNIFTY: confirmed 40 → 35 followed, 5 not; diverged 6 → 5 followed, 1 not. **On these trend days a divergence at a new extreme did not warn** (it was followed by a further extreme 16 of 19 times).
- **Divergence before each day's final extreme (within our bars):** NIFTY — 28 Sep diverged, 6 Oct confirmed, 8 Oct diverged (15:05), 16 Oct confirmed (the 10:15 high, 23,155); 9, 12, 13 Oct end before the day's real extreme. BANKNIFTY — 28 Sep confirmed, 6 Oct diverged, 8 Oct confirmed. **3 of 7 diverged.** On 16 Oct the top came with CVD *confirming*; the warning there was the absorption mark (Study 3), not CVD.
- **Candidate hold/fold wording, in ranked terms, consistent with Mary's rule (zone, flow, OI, VPIN, never a candle):** *HOLD* while the zone holds (price on the trend side of VWAP) and counter-trend **15-minute delta ranks below p80 of today's own 15-min windows**. *FLOW fold* = counter-trend 15-min delta ≥ p80 **and** price back inside 0.5σ of VWAP for 3 minutes. **CVD ulta stays an information chip, not a fold tell** on this evidence. *Candidate extra fold tells (max 2):* an opposite BADA / ranked absorption at the level you traded from; the supporting OI quitting its strike. Both need logging that does not exist yet (§4).

## 3. Study 3 — the extension's marks

### 3.1 Which build produced which rows (from the code and git, `orderflow-desk`)
| Period | Build facts | What it means for the rows |
|---|---|---|
| to 15 Sep | baseline 9 Sep | before the record |
| from 15 Sep 18:55 | `board.js`: thresholds rank within the session | all rows from 21 Sep |
| **21 Sep – 1 Oct** (**era A**) | the board binned at the **chart's** row size (`rowAuto`): "the same 1 Oct tape gave 36, 15 or 144 marks" (0.4.0 commit message); an in-bar rule graded **big print cells** as absorption | counts depend on her zoom; the 29 Sep 10:05 300K buyer is logged as `absorption −1, 4,483` and the 30 Sep 12:50 198K seller as `absorption +1, 3,096` — read **backwards** (buyers' print called "sellers defended") |
| **4 Oct 22:29 decoder 0.4.0** → rows from **5 Oct** (**era B**) | fixed 5-pt row; print cells no longer emit absorption or trap; decoder E1–E7 added; 6-object overlay budget | marks per day fall (collapsed: era A median 63, range 52–83; era B median 36, range 4–41); the largest era-B absorption row is 1,751 lots (a bar-level one, 9 Oct 09:15) |
| 5 Oct 03:26 | overlay: marks visible again | display only |

The installed build is **not stamped in any row**; the era boundary is inferred from commit time and row counts. Decoder rows exist only for era B (5–13 Oct).

### 3.2 What the sides mean (this is where it confuses)
- **The log is the board's raw `events`** (`main.js:254` → `tape_log.append`), all six kinds, not the four drawn marks (`MARK_KINDS` = trap, climax, absorption, exhaustion).
- **`trap` side in the log = the TRAPPED side** (+1 = buyers bought the prior high and price is now below them; −1 = sellers sold the prior low and price is now above them). Every other kind's side is the **winner / the direction**. One file, two conventions.
- **The chart inverts the trap for colour only** (`main.js:190`: `-e.side`), so the glyph wears the winner's colour, while the chip says `who(-m.side) + ' phase (P)'` (`overlay.js:233`) — the **trapped** side's name. Hence Mary's 16 Oct report: at the bottom (22,915, day low 22,908) the log has `trap −1` (sellers trapped), the chart says **"Sellers phase (P)"**; at the top (23,140, day high 23,155) the log has `trap +1` (buyers trapped), the chart says **"Buyers phase (P)"**. Both were right about direction (price went with the *other* side), but "sellers phase" at a bottom **reads as "sellers in control"** — it means the sellers are the ones caught.
- A reader who takes `side` as the winner for every logged kind gets every trap backwards. The overlay comment (`overlay.js:232`) is right that the **drawn** mark's side is the winner's; the **logged** rows come from a different object (the raw events).
- **Data cannot settle the sign by itself:** the trap rows read as winner = −logged side give WITH 55 / AGAINST 43 (era A, n = 103) and 15 / 14 (era B, n = 34); read the other way they invert. Near-even, so the convention rests on the code and on the 16 Oct pair.

### 3.3 Outcome definitions (fixed before the first table; the hold test was added after)
Reference P0 = close of the last path bar ending at or before the bar's close (mark time + 5 min); window 60 min; **WITH-first / AGAINST-first** = price trades ±0.5U in the winner's direction first (TIE = both inside one 3-min bar; NONE = neither in 60 min; END = the session ended). Winner = logged side, except `trap` = −side; `climax` has no side (UP-first / DOWN-first). **Post-hoc:** the first score mis-scored the 16 Oct 09:40 trap (price dipped 0.5U before rallying to 23,155 and never retested the low), so I added a **level-hold** test: BROKE = price trades 0.25U beyond the mark price against the winner within 60 min, HELD otherwise. **Baselines** (same days, every 5-min bar close 09:30–14:30): era A UP-first 210 / DOWN-first 276 (a falling sample); era B 223 / 205 / 59 none; bar-low held 243 / broke 599; sellers-at-high 349 / 493; within 10 pts of the 30-min extreme 721 of 1,684 readings; within 10 pts of the **day** extreme 62 of 1,684.

### 3.4 Results — board marks (FORWARD-LOGGED, NIFTY; WITH / AGAINST / TIE / NONE+END)
| Kind | Era A n | A: WITH / AGAINST | A: expected-by-drift WITH | Era B n | B: WITH / AGAINST | B: expected-by-drift WITH |
|---|---|---|---|---|---|---|
| trap | 103 | 55 / 43 (END 5) | 50 | 34 | 15 / 14 (3 none, 2 end) | 15 |
| absorption | 200 | 106 / 75 (2 tie, 17 end) | 91 | 64 | 28 / 27 | 27 |
| exhaustion | 66 | 32 / 32 | 32 | 28 | 9 / 17 | 13 |
| initiative | 90 | 55 / 29 | 43 | 56 | 27 / 24 | 26 |
| vacuum | 37 | 19 / 16 | 17 | 22 | 10 / 10 | 10 |
| climax | 25 | UP 8 / DOWN 15 | — | 17 | UP 5 / DOWN 10 | — |

("Expected-by-drift" = the WITH count a no-information mark would show, from the era's baseline UP/DOWN-first and the mark's winner mix: era A drifted down.)

**Level hold (post-hoc):** HELD / BROKE — trap A 40 / 54, B 16 / 16; absorption A 58 / 121, B 22 / 38; exhaustion A 17 / 45, B 5 / 21; initiative A 42 / 42, B 29 / 24; **vacuum A 2 / 35, B 4 / 18**. Baseline for a random bar's extreme: held 243 / broke 599 (buyers-at-low), 349 / 493 (sellers-at-high).

**By context (both eras; with-trend = winner on the VWAP side price is on; WITH / AGAINST):**
| | with-trend | counter-trend | flat |
|---|---|---|---|
| trap | 29 / 22 (n 57) | 34 / 26 (n 62) | 7 / 9 |
| absorption | 40 / 29 (n 83) | 77 / 61 (n 150) | 17 / 12 |
| exhaustion | 10 / 7 (n 17) | 29 / 34 (n 67) | 2 / 8 |
| initiative | 59 / 43 (n 109) | **17 / 6 (n 26)** | 6 / 4 |
| vacuum | 8 / 13 | 14 / 11 | 7 / 2 |

**By day type (full-day crosses):** exhaustion on **trend days 10 / 22 (n 35)** vs mid 30 / 25 (n 56); initiative on trend days 37 / 18 (n 60), mid 43 / 31, chop 2 / 4 (n 6); traps trend 29 / 22, mid 39 / 33. **By location** (days with a prior profile; node = POC/VAH/VAL/HVN/LVN/PDH/PDL/PDC within 10 pts): trap node 16 / 16, ring 7 / 9, VWAP 1 / 4, nowhere 20 / 12; absorption node 34 / 33, ring 22 / 19, nowhere 33 / 19; initiative node 19 / 11, ring 15 / 7, nowhere 30 / 19. No location separates a kind from the baseline in this sample.

**Near an extreme.** Within 10 pts of the 30-min local extreme: trap 79 of 137, absorption 154 of 264, exhaustion 75 of 94 (baseline 721 of 1,684). Within 10 pts of the **day's** extreme (hindsight): trap 13, absorption 17, exhaustion 6, initiative 5, vacuum 0 (baseline 62 of 1,684). **Day extremes caught** (a trap / absorption / exhaustion mark whose winner is opposite the extreme, within the tolerance, dated −5 to +20 min of it): era A 9 of 15 covered extremes (369 such marks on those days; ~46 a day over a ~190-pt range, so a mark lands within 10 pts of any given price often); era B 4 of 13 at 10 pts and 6 of 13 at 20 pts (126 marks). Caught: 22 Sep both, 30 Sep both, 7 Oct both, 16 Oct low (and the high at 20 pts). Not marked include: 28 Sep high, 6 Oct both, 8 Oct both, 9 Oct low, 12 Oct high, 13 Oct low (mostly opening-bar extremes or trend days) and, in era A, 23 Sep high, 24 Sep low, 25 Sep low, 29 Sep low, 1 Oct low.

**Sequence absorption → trap at the same price within 10 pts the next bar:** 120 pairs (one mark can pair twice; heavily era A) → trap bar WITH 60 / AGAINST 50 / none 10. Nothing beyond the singles.

**16 Oct (FORWARD-LOGGED, as logged; winner = trap side flipped; 0.5U / level):**
| Time | Mark | logged side → winner | price | 0.5U-first | note |
|---|---|---|---|---|---|
| 09:30 | exhaustion | +1 → buyers | 22,931 | AGAINST 6 min | 11 pts above the day low |
| 09:35 | absorption | +1 → buyers | 22,915 (657) | WITH 3 min | day low 22,908 at 09:36, 7 pts away; not retested |
| 09:40 | trap | −1 → buyers (sellers trapped) | 22,915 (657) | AGAINST 3 min | a pullback of 0.5U before the move; the low held |
| 10:15 | absorption ×2 | −1 → sellers | 23,125 / 23,140 (573) | WITH 27 min | day high 23,155 at 10:18 |
| 10:15 | climax | 0 | 23,096 (2,817) | DOWN-first 27 min | |
| 10:20 | trap | +1 → sellers (buyers trapped) | 23,140 (573) | WITH 21 min | high 15 pts away |
The 09:25 initiative (−1) and the 10:00 absorption (−1, 99) went AGAINST. **So on 16 Oct the marks caught both extremes, with noise around them** (10 marks, 4 of them at the two extremes).

**The days they failed.** 12 Oct (down-trend): six buyer-winner absorption/trap marks at 22,525 / 22,502 / 22,500 / 22,410 / 22,415 — 4 AGAINST, 1 WITH, 1 NONE, price kept falling to 22,382 (counter-trend buyer absorption on a trend day). Per-day, marks decided WITH / AGAINST: 28 Sep trend 47 / 32; 6 Oct trend 16 / 17; 7 Oct chop 13 / 16; 8 Oct trend 12 / 10 (12 unresolved); 12 Oct trend 5 / 8 (6 unresolved); 1 Oct 33 / 34. No day is clean.

### 3.5 Results — decoder events (FORWARD-LOGGED, era B, 5–13 Oct, NIFTY)
Winner map fixed first: E1 BADA PRINT = printer side; E2 PEHAL = side; E3 DABAAV absorbed = −side, positioning = +side; E4 DHER = side; E5 KHULA = side (the unfinished extreme gets revisited); E6 THAKAAN = −side; E7 CVD ulta = side.
| Event | n | WITH / AGAINST / none | level HELD / BROKE |
|---|---|---|---|
| E1 BADA PRINT | 6 | 5 / 1 / 0 | 2 / 4 |
| E2 PEHAL | 28 | 9 / 12 / 7 | 3 / 24 |
| E3 DABAAV | 30 (28 unsided: OI split `baaki`) | 2 / 0 | 1 / 1 |
| E4 DHER | 1 | 1 / 0 | 1 / 0 |
| E5 KHULA | 38 | 16 / 17 / 5 | 2 / 35 |
| E6 THAKAAN | 1 | 0 / 1 | 0 / 1 |
| E7 CVD ulta | 12 | 5 / 4 / 3 | 3 / 9 |
E1 rows: 6 Oct 11:05 and 12:35 buyers (385 and 353 lots, decoder state FAILED = printer trapped; both went WITH 0.5U first); 7 Oct 14:30 buyer 385 FAILED, AGAINST; 8 Oct 12:20 seller 254 CONFIRMED, WITH; 9 Oct 13:55 buyer 394 BAAKI; 12 Oct 10:50 seller 311 CONFIRMED, WITH. All six sit at the ±1.5σ ring. The decoder's own E1 state (3 FAILED, 2 CONFIRMED, 1 pending) is the only part that tells printer-wins from printer-trapped, and only after the fact. n is far too small to say more; none of the 2 big prints Mary named (29, 30 Sep) falls in era B.

## 4. Improvements (candidates, ranked by how little they need)
1. **Fix the labels first.** Name the trapped side and the expected move: the P chip becomes **"BECHNE WALE PHANSE ▲ 22,915 · 657"** at a bottom and **"KHARIDNE WALE PHANSE ▼ 23,140 · 573"** at a top; absorption **"KHAREEDAR NE ROKA ▲"** / **"BECHNE WALE NE ROKA ▼"** (who held the level, arrow = where price should go); exhaustion **"THAKAAN ▼"**; initiative **"PEHAL ▲/▼"**. Retire "phase".
2. **Log the truth, once.** Write `trapped_side` and `winner` as separate fields, plus `rowSize`, the build version (manifest `0.4.0`), the placed `at`, and the drawn marks (`st.marks`) beside the raw events; dedupe re-posts by (bar, kind, side, price on the 5-pt grid). Today the era cannot be read from a row.
3. **Drop as noise (on this sample):** **vacuum** (level held 6 of 59; WITH/AGAINST 29 / 26); the **climax** chart mark (no side); **exhaustion on trend days** (10 WITH / 22 AGAINST, n = 35; it fires against the lane) — keep it as a warning chip only when price is inside 0.5σ of VWAP.
4. **Filter by rank, place, context before a mark is drawn:** ranked ≥ p90 of the session's own cluster sizes (today p80; era A drew ~46 a day), **and** at a place (σ ring ≥ 1.5, a prior node/level, or VWAP ±0.25σ). Everything else goes on tap. Show **counter-trend initiative** (17 / 6, n = 26) as its own chip: the lane's opposite side lighting up is the rarest mark and the only split that moved.
5. **Combine, don't multiply.** Absorption → trap at the same price within 10 pts in the next bar becomes one chip with both numbers ("ROKA → PHANSE 22,915 · 657"), not two glyphs. (The pairs showed no extra edge; this is display hygiene.)
6. **Marks become a LEDGER with a level status.** Each ranked mark carries: rank, place, trend context, and a live **HELD / BROKE** against its own price (the 0.25U-in-60-min test, or the decoder's E1 FAILED/CONFIRMED rule). Level-hold is how Mary used them on 16 Oct; the 0.5U-first score mis-scored the low.
7. **Fold board:** a mark *against the position at its level* is a candidate fold tell (opposite BADA or ranked absorption within a row of the entry zone) — max 2 tells beyond zone, flow, OI, VPIN. Do not use the extension's exhaustion or CVD ulta as a fold tell on trend days (Study 2).
8. **Coverage.** The binding constraint on all three studies was missing GC bars (9 Oct, 12–16 Oct partial; 14–15 Oct none). A gap alarm and a tab-open backfill check are worth more than any new mark.

## 5. What to add to the spec (§10c candidates; each needs a dated prereg before it is a rule)
- **P-OF1 marks:** rank ≥ p90 and at a place, per §4.4; the forward hold test (0.25U in 60 min) and the 0.5U-first test both logged, both reported as rows, per kind × era-free (fixed build) × trend context.
- **P-OF2 labels:** the Hinglish names in §4.1; the trap convention written in the spec once (log = trapped side + winner field).
- **P-OF3 nodes:** LOCATION rows only; a prereg for *interior* LVNs with the shifted-level placebo built in, and ≥ 25 first-touches per class before any split.
- **P-OF4 CVD / flow:** CVD ulta = information chip; hold/fold stated in ranked flow terms (§2); log opposite-BADA / ranked-absorption-against as candidate fold tells.
- **P-OF5 data:** marks-file schema in §4.2; a bar-gap alarm; a stamp of the extension build on every row.

## 6. Limits
- Era A is not reproducible (row size followed her zoom); era B has 8 sessions, three of them short. The 29 and 30 Sep big prints exist only in era A and were mis-graded there.
- 3-min path bars hide order inside a bar (TIE); GC bars with filled `o`/`c` slightly distort VWAP/σ for those bars; the day type and trend direction are hindsight; day-extreme proximity counts a mark per extreme but marks cluster.
- GC and Upstox delta differ by a median of −2,029 lots a day on matched bars (earlier check), so Study 2's BANKNIFTY (Upstox) and NIFTY (GC) CVD are not interchangeable.
- Nothing here is a hit rate, and nothing should be quoted as one.
