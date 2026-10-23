# VALIDATE 2 — the evidence rows (in-sample hindsight; counts and descriptions, never a rate)

Read-only replays off `data/book`, `data/chain`, `data/vpin_fast.jsonl`, `data/tape/ux_*`, `data/trap`, the expression
and side logs, with the rev 6 engine fed the way `fold_live` feeds it (`scratch/replay.py`; outputs `scratch/v2_*.txt`,
`scratch/path_*.txt`; the v1 outputs `scratch/out_*.txt` are kept). **Every row below knows the rest of the day** — the
trades were picked because their outcomes are known. The check rules are PREREG-DRAFT.md §1 (v2); §5 there says what
moved between v1 and v2 and why.

What differs from the live server, stated once: the prior-session pool is the five previous book files on disk (the
live engine applies the contract filter, so BK / B can differ a little — on 09-24 SENSEX the engine here FOLDs at
10:34, the live log held to 13:22); daytype is rebuilt without the sides slots and without peers (and without the
trap-FAIL ender on days before the trap log, 10-04); VPIN exists only for NIFTY; the expression and side logs start
09-25; the premium "there" is the chain's interpolation [I].

## 1. Today, 2026-10-06 (NIFTY expiry day)

### 1.1 Her 10:03 — BUY 22650 PE @ 55 (chain 56.35), fut 22,741 · F 22,659 · basis 84

| check | state | the fact |
|---|---|---|
| RIGHT NOW | WITH | HOLD · against you: flow, VPIN · behind you: OI · out if 22,788 is accepted |
| DAY / TREND | NEITHER | EARLY (the initial balance still building 22,640–22,750) [I] |
| EXPRESSION | AGAINST | the engine leans the OTHER way at 10:02: LEANS BUY CE (3 buy · 2 sell facts); her way: STAND ASIDE |
| WALL BEHIND | NEITHER | 22700 CE writers 226L, STALLED (day peak 09:46, 1.7 % off) [M] |
| WALL AHEAD | NEITHER | 22600 PE writers 382L, BUILDING, 57 pts ahead (fut) [M] |
| ORDER FLOW | AGAINST | buyers won 09:55 at 22,718 · CVD +606, peak 09:32 [I] |
| VPIN | AGAINST | 4 of 10 buckets one-sided against her · pct 0.93 (shadow) |
| CROSS-INDEX | AGAINST | the latest push is UP to 22,761 (10:00), against her, and all three took their prior swing |
| ROOM | WITH | invalid 22,788 fut (47 pts; B = 11) · next wall 57 pts |
| PAYING | AGAINST | PE 22600 and PE 22500 both BUILDING at their day peaks (10:02) [M] |
| printed | — | delta −0.48 · time value 56.4 of 56.35 (all time value, 0DTE) · spread 4 ticks · PCR(9) 1.36 · 22650 PE writers comfortable (ltp 56 vs avg 73) |

**Word: NO** — 2 with · 5 against · 3 neither (of 10); four of the five against are structural (expression, flow, cross-index) plus VPIN and paying.
**What happened [M]:** the PE went 55 → 44.65 by 10:44 → 31.05 at the engine's FOLD 11:45 → 29.2 at 11:47.
**The board at 10:03:** top NIFTY BUY 22650 CE @ 61.75 — WAIT 6 with · 1 against (ROOM: next wall 43 pts, invalid 45 pts); then NIFTY SELL 22650 PE @ 56.35 — WAIT 6 with · 1 against (EXPRESSION said BUY, not SELL). *Same thesis, better expression* for her down view: nothing (the sale of the CE reads NO 3w/6a). *Opposite thesis*: BUY 22650 CE, WAIT. **She had sold the 22650 PE at 10:02:51 for eight seconds and flipped into the long; the board's second line was the trade she abandoned.** [M] After: fut 22,741 → 22,790 by 11:45; the 22650 PE fell to 29.6 (the sale would have kept ~27 of 56) [M, hindsight].

### 1.2 Her 14:57 idea — BUY 22600 CE @ 111 (chain 112.55), fut 22,778 · F 22,710 · basis 67

| check | state | the fact |
|---|---|---|
| RIGHT NOW | WITH | HOLD · against you: flow · behind you: OI, VPIN · out if 22,764 is accepted |
| DAY / TREND | NEITHER | TWO-SIDED since 13:28 (trend ended: FAIL at ROUND 22,700, buyers phanse) [I] |
| EXPRESSION | WITH | BUY CE at 14:56 (3 buy · 1 sell facts) |
| WALL BEHIND | NEITHER | 22700 PE writers 402L, STALLED (day peak 14:17, 12.8 % off) [M] |
| WALL AHEAD | NEITHER | 22750 CE writers 301L, STALLED (peak 14:46, 5 % off), 39 pts ahead [M] |
| ORDER FLOW | AGAINST | sellers won 14:46 at 22,775 · CVD +461, peak 14:37 [I] |
| VPIN | WITH | 2 of 10 buckets her way · pct 0.28 |
| CROSS-INDEX | AGAINST | the 14:42 push UP to 22,792 is hers, and 0 of 3 took their prior swing: NIFTY failed 22,830 · BANKNIFTY failed 55,425 · SENSEX failed 73,350 (witness) |
| ROOM | WITH | invalid 22,764 fut (14 pts; B = 9) · next wall 39 pts |
| PAYING | NEITHER | CE 22800 STALLED (10 % off its 14:10 peak) · CE 22750 STALLED (5 % off) [M] |
| printed | — | delta 1.00 · time value 2.5 of 112.55 — **deep ITM: a futures long in option's clothing** · PCR(9) 1.18 (1.31 an hour ago) · 22700 PE writers comfortable (21.5 vs avg 45.5) |

**Word: NO** — 4 with · 2 against (both structural: order flow, cross-index) · 4 neither. Levels: invalid 22,764 fut / 22,697 spot where the 22700 PE writers stand, premium there ≈ 99.7 [I]; T1 22,817 fut / 22,750 spot (the 22750 CE wall), premium ≈ 151.6 [I]; +39 for −14 (fut).
**The hand-written 14:57 read said NO for the same reasons** (a futures long needing the 22,730 day high and the 22750 CE wall to break, nothing showing those writers leaving). Under rules v1 this row read WAIT 8-with; v2's fixes (PREREG §5) moved it — disclosed.
**What happened [M]:** the CE was 115.2 at 15:12 (+2.6); the index closed 22,714 spot — the wall held, the move did not come.

### 1.3 The 14:57 alternative — SELL 22700 CE @ 30 (chain 31.9)

| check | state | the fact |
|---|---|---|
| RIGHT NOW | WITH | HOLD · against you: VPIN · behind you: flow, OI · out if 22,794 is accepted |
| DAY / TREND | NEITHER | TWO-SIDED since 13:28 |
| EXPRESSION | WITH | EITHER at 14:56 |
| WALL BEHIND | NEITHER | 22750 CE writers 301L, STALLED (peak 14:46, 5 % off) |
| WALL AHEAD | not counted | a writer has no next wall; time is her target |
| ORDER FLOW | WITH | sellers won 14:46 at 22,775 · the move away from her strike |
| VPIN | AGAINST | 2 of 10 buckets against her |
| CROSS-INDEX | WITH | the 14:42 push UP is against her and 0 of 3 took their prior swing — a failed push |
| ROOM | WITH | invalid 22,794 fut (16 pts; B = 9) |
| PAYING | WITH | PE 22600 UNWINDING (24 % off its 12:37 peak) · PE 22700 STALLED (13 % off) — the floor is leaving |
| printed | — | delta 0.59 · time value 21.8 of 31.9 · keep all if close ≤ 22,700 spot · breakeven 22,731.9 spot |

**Word: WAIT** — 6 with · 1 against (VPIN, not structural) · 2 neither (of 9). **The board at 14:57:** 1 · SENSEX BUY 72900 PE @ 338.55 WAIT 7w/2a (day/trend, room) · 2 · **NIFTY SELL 22700 CE @ 31.9 WAIT 6w/1a** · 3 · NIFTY SELL 22650 CE (ITM) @ 67.9 WAIT 6w/1a. For her CE-buy press: *opposite thesis* = SELL 22700 CE (WAIT); *other index* = SENSEX BUY 72900 PE (WAIT); *same thesis, better expression* (SELL 22700 PE @ 21.5) reads NO (expression, order flow against). Nothing reads GO at 14:57: the honest line is *"nothing reads GO; the cleanest is the 22700 CE sale, with VPIN the one thing against it"*.
**What happened [M]:** 22700 CE 31.9 → ~16 at the close (spot 22,714): the sale kept ~16 of 32. SENSEX 72900 PE: SENSEX fell ~75 pts into 15:06 (73,240 → 73,165 fut) [M] — the PE gained; not measured to the tick here.

## 2. Her past trades (the same rules, the same inputs)

| trade | word · counts | against | board top (and what it was) | after [M, hindsight] |
|---|---|---|---|---|
| **09-24 SENSEX BUY 74200 PE @ 222.6, 10:19** (chain 209.1) | **NO** · 2 with · 4 against · 2 neither · 2 could not check (expression log absent; no SENSEX VPIN) | WALL AHEAD (74100 PE building 12 pts ahead) · ORDER FLOW (buyers won 10:16, pullback) · ROOM (next wall 12 pts vs invalid 178) · PAYING (74000 / 74100 PE building) | BANKNIFTY SELL 55600 CE @ 410 — WAIT 5w/0a | **ran 222 → 641 (14:24)**. DAY/TREND alone read WITH (TREND ▼ since 09:35). The checks called a trend-day pullback entry NO because the next wall sat 12 pts under price and the last fight went against her. Kept as the row that shows the word is not a crystal ball. |
| **09-28 NIFTY BUY 23000 PE @ 120.4, 09:30** (chain 125.2) | **WAIT** · 4 with · 3 against · 2 neither · 1 could not check (no prior swing yet at 09:30) | WALL AHEAD (22900 PE at the money, 0 pts, building) · ROOM (next wall 0 pts) · PAYING (22900 / 22800 PE building) | NIFTY SELL 22900 CE @ 108.55 — WAIT 5w/1a (paying) | **held winner: 120 → 206 at 15:00** (the 22900 PE writers were run over). The mirror sale the board named also won (the index fell ~100 pts from 22,900). |
| **09-22 NIFTY BUY 23550 PE @ 134.8, 10:32** (chain 130.1) | **WAIT** · 5 with · 0 against · 3 neither · 2 could not check (expression, VPIN) | — (nothing against; not there yet: day type TWO-SIDED, flow quiet, cross-index 2 of 3) | hers is the best on the board (NIFTY BUY 23450 PE ties at 5w/0a) | **winner: 134.8 → 238.55 (14:12)**; deep ITM (delta −0.87) printed as a futures short in option's clothing. |
| **10-05 NIFTY BUY 22600 CE @ 94.25, 09:28** | **WAIT** · 4 with · 2 against · 3 neither · 1 could not check | ORDER FLOW (sellers won 09:21, pullback) · PAYING (22600 / 22700 CE building at their peaks) | BANKNIFTY BUY 55100 CE @ 987 — WAIT 5w/1a | **loser: 94 → 48 at the engine's FOLD 11:50.** |
| **10-05 NIFTY SELL 22650 PE @ 131.35, 13:41** (chain 130.25) | **WAIT** · 7 with · 1 against · 1 neither (of 9) | CROSS-INDEX (the 13:41 push UP is hers and 0 of 3 took their prior swing — a lower high everywhere) | hers is the best on the board (SELL 22550 PE ties) | **flat: 131 → 133.75 at the close**, its worst minute 161 at 14:05. |
| 10-06 10:03 / 14:57 | §1 | | | |

Described, never a rate: of the eight moments, NO came three times (today's two losers / non-movers and the 09-24 winner), WAIT five times; the word did not separate the 09-24 winner from today's loser at the door, and the board's named alternative was the better side in today's three moments and on 09-28. That is what the forward count in PREREG §4 exists to settle.

## 3. In a trade — the three reads on the recorded paths (`scratch/path_*.txt`)

### 3.1 Today's 22650 PE from 10:03 (W = 22700 CE until 10:28, then 22650 CE; peak 252.3L at 10:18)

| time | engine | chips Z/F/O/V | W off its peak · updates | the new reads would have printed |
|---|---|---|---|---|
| 10:42 | HOLD | WITH/WITH/WITH/QUIET | −10.0 % · n9 | W-BLEED amber needs 15 updates: not yet (printed: −10 %, 9 updates) |
| 10:45 | HOLD | WITH/AGAINST/WITH/QUIET | −11.1 % · n12 | ledger: W −11 %, buyers won 10:43 at 22,745 — two rows AGAINST while the chips said *behind you: zone, OI* |
| **10:48** | HOLD | WITH/AGAINST/WITH/QUIET | **−12.6 % · n15** | **W-BLEED amber · GAVE UP** (price +8 against, W off ≥ 10 % with 15 updates, no new peak; buyers won 10:43 inside the last 10 buckets) · premium 48.65 |
| 11:01 | HOLD | WITH/AGAINST/WITH/QUIET | −2.4 % · n28 | the wall came back near its peak but never above it: OFF stands; the line says *turns back to PULLBACK if 22650 CE makes a new peak* |
| **11:05** | HOLD | WITH/AGAINST/QUIET/QUIET | −4.1 % · n32 | **ZONE ALONE on** (zone the only chip WITH; OI quiet since 11:05, flow against since 10:43) · premium 42.45 |
| 11:08 | HOLD | QUIET/AGAINST/QUIET/QUIET | −15.6 % · n35 | GAVE UP, W −15.6 % |
| 11:17 | HOLD | WITH/WITH/QUIET/QUIET | −14.5 % · n44 | ZONE ALONE off (flow WITH); GAVE UP stands on OI alone, with the fact printed |
| 11:45 | **FOLD · 22770 accepted** | | −18.7 % · n73 | the engine's word; premium 31.05 |

The GAVE UP line would have been on the screen from 10:48 at 48.65 — 57 minutes before the engine's FOLD at 31.05 — with its own falsifier printed (a new W peak), which never came. The chips alone read *HOLD · behind you: zone, OI* through 11:04. **This is one row and it is in-sample.**

### 3.2 09-24 SENSEX 74200 PE from 10:19 (the big winner; W = 74200 CE)

| time | W off its peak · updates | the new reads |
|---|---|---|
| 10:54 | −6.2 % · n8 | — |
| 11:02 | −10.5 % · n11 | printed −10.5 %, 11 updates: **amber needs 15 — not on**; price 74,211 vs entry 74,134 (77 pts against); flow AGAINST → the pullback/gave-up read prints UNDECIDED (W not OFF, a fight won against her) |
| 11:05–11:12 | −11.9 % · n12 → −11.6 % · n14 | still 14 updates: not on |
| 11:13 | −9.4 % · n15 | at 15 updates the bleed is under 10 %: not on |
| 11:27 | **new peak** (0 %) | the wall rebuilt; flow WITH; the run to 641 followed (13:28 onward) |

The 10 % / 15-update rule as written does **not** flag this winner's pullback (it reached 10 % with 11–14 updates and was back under 10 % at the 15th). That is a near miss, not a separation: with a chain 10 s faster it would have printed GAVE UP for eleven minutes before clearing on the new peak. The screen would have shown the number either way; the word is unsigned until the forward count.

### 3.3 09-28 NIFTY 23000 PE from 09:30 (her held winner; W = 22950 CE then 22900 CE)
W's bleed never exceeded 6.7 %; the engine's own OI event fired at 11:52 (−4.2 %, z ≥ 3) and again 13:32–14:19 (≈ 5 %) — the chip read OI AGAINST — while the future was on her side of the entry (22,877 vs 22,942), so the PULLBACK / GAVE UP read would have printed nothing (it prints only when price is against her), and ZONE ALONE was never on (OI or FLOW stayed WITH, or both QUIET). The engine never folded; the PE went 120 → 206.

### 3.4 Today's open 22600 CE from 14:12 (W = 22700 PE)
W off its peak ≥ 10 % from 14:33 (−11.4 %) with the engine's OI event already AGAINST at 14:30; price against her (22,773 vs entry 22,816) → GAVE UP from 14:30 by the event clause; the ledger: fut −43 against, W −11 %, flow quiet → against from 14:50. The engine read HOLD throughout (G 22,764 never accepted); the CE 133 → 95 (14:30) → 114 (15:12). A pullback, by outcome, that the read would have called GAVE UP for 45 minutes. Kept.

## 4. What could not be checked
- The live `daytype` (sides slots, peers) and `xindex` replies at the past moments: rebuilt from inputs here, not read from logs (xindex logs start 09-30; its X2 at the 14:42 push today agrees: "koi taaza extreme nahi").
- EXPRESSION and the trend rows before 09-25 (09-22, 09-24): could not check, counted as such.
- VPIN on BANKNIFTY / SENSEX: no gauge exists (NIFTY-only).
- The premium "there" at T2 beyond the chain's interpolation range.
- The 09-21 trade: no book or chain file.
- The GoCharting-side reads (decoder E1 prints, reversal N/4) at the past moments: the tape files were not replayed here; the book's own absorption / fights stand in.
