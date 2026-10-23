# Right panel v3 mockup: notes (20 Oct 2026, after the close)

`python -B build_panel.py` rebuilds `frames.json`, `mockup.html` and the self-check at the end of this file (about one
minute). It reads recorded files only: no HTTP, no server, nothing written outside this folder.
`mockup.html?only=<id>` shows one frame (that is how `shots/` were taken, with headless Chrome at 1720×860).

**What the mockup is.** The draft's four new blocks (KAUN DABA RAHA, KAUN LIKH RAHA, TREND, DOOSRE INDEX) are computed
here, cell by cell, by the draft's rules. The header, SIRF BADE, PLAN and `?` are today's v2.4 rules, shortened per
rule 10:
- the header READ / PLAN come from `tools/frame_v2_replay.py` (the server's own `_v2_parts`, cut to T);
- SIRF BADE / PLAN / `?` come from the real `dist-v2` bundle, booted through `test/shell.mjs` with the GC bars closed by T
  (the harness `test/replay-stats.mjs` uses).

**Frames.** The 12 fixed frames, plus 3 drawn with `random.Random(20261020)`: a day of the four, then a 5-min clock from
09:20 to 15:25, not one of the fixed frames. The draw happened before any output was looked at. The 3 drawn frames are:
- 19 Oct 12:40;
- 12 Oct 14:25;
- 9 Oct 14:35.

Two of the three land after that day's recorders stopped (12 Oct: 13:41; 9 Oct: 14:05), so they show the degraded panel.
There is no chart shot for the random frames; they show a grey box.

## Inputs, and what "as of T" means
| Input | File | At T, the panel uses |
|---|---|---|
| Upstox (UX) flow, 1 min | `../scratch/pr_1m_<IDX>.json` (rebuilt from `data/book` by `ladder.Ladder`, `pr_build1m.py`) | minutes that ended by T |
| GoCharting (GC) flow, 5 min | `data/tape/tape_NIFTY_<day>.jsonl` | bars closed by T |
| Option OI per strike | `data/chain/chain_<IDX>_<day>` [M]; `data/chain_backfill/` (REST minutes) [I] only for minutes the poller never saw | OI of minutes that ended by T |
| Futures OI | UX 1-min bar `oi` (book); else the GC bar's `oi` | the bar ending at T |
| Index spot (DOOSRE INDEX) | the chain rows' `spot` (backfill where the poller was down) | minutes that ended by T |

**Checks built into the run.**
- The UX 1-min rebuild, summed to 5 minutes, matches `data/tape/ux_*` volume on every bar of the four days (max difference
  0%).
- Two cells were recomputed by hand from the raw files, both matching. The cells are 16 Oct 11:05 BECHNE WALE (GC sell 333 ÷
  median 175 = 1.90×) and CALL (+78.96L).
- Backfill and recorded `oi_chg` agree where both exist (16 Oct 09:23–09:48): they share one baseline.

**References.**
- Only days strictly before the frame's day (asserted on every `ref` in the traces).
- Only days of the same kind, by `rank.day_kind`: NORMAL / EXPIRY / ROLL. Its inputs are the book `ik` / `expiry`, the chain
  `expiry`, else the surface file.
- 19 Oct is a NIFTY **EXPIRY** day. All four BANKNIFTY and SENSEX frame days are NORMAL.
- House constants from `rank.py`:
  - `MIN_DAYS` 5: under 5 days of a kind, nothing ranks;
  - `PROV_N` 30: under 30 days, the reference is provisional;
  - `pct_vals`: the mid-rank percentile;
  - `LOT_FLOOR` SENSEX 30.

## Each rule, exactly as built
Thresholds live in one block at the top of `build_panel.py`.

**Rule 1: noise stays silent.**
- A ranked cell below p70 prints its number in light grey and the bar as a grey `·`. This follows the draft's own example,
  `0.9× ·`. Words and arrows are dropped.
- p70–89: the side's colour, with a 2–3 cell bar.
- p90+: bold on a tinted background, with a 4–5 cell bar in full colour.
- Bar fill by rank: p70–79 → 2 cells, 80–89 → 3, 90–96 → 4, 97+ → 5.

**Colour has one meaning.**
- Green: favours up (buyers, put writing, call unwinding).
- Red: favours down (sellers, call writing, put unwinding).
- Grey: noise.
- Dark ink: attention with no side. Only `confirm nahi ✗` uses it.
- `?` is grey italic: "could not check".

**Rule 2: × normal.** For a side's W-minute lots ending at T:
- x = today ÷ the median of the *same clock window* on prior same-kind days. At least 5 days are needed, else `? ref kam`.
- The rank of x is taken against the same ratio, built on every prior same-kind day for every window ending in T's 30-min
  slot. Each of those days is divided by the median of the *other* days, so a day is never its own normal.
- A UX window counts only if every minute is whole. Whole means:
  - not the record's partial first minute;
  - **not the minute right after a recorder hole**, which carries the hole's whole volume (16 Oct 11:12: 14,387 lots;
    12 Oct 12:58: 8,273). The ladder does not flag these minutes as partial;
  - not the minute cut short before a hole.
- `kam data` appears once in each block's subtitle when any ranked cell in it has N < 30. Today that is every block, every
  frame.

**Source per flow block (judgement call; the draft does not say).**
- UX is used when it has the whole 30 minutes (or the 5 minutes, before 09:47).
- Otherwise GC is used when it has them. Otherwise whichever source has the 5 minutes.
- Each source is ranked only against its own history (INTERNAL §2.2).
- A GC-sourced block says `GC only` in its subtitle.
- Why UX first: it is the only source that is rolling at 1 minute, both live and in history. It is the same source the peers
  use, and the source INTERNAL measured the speed ratio on.
- GC took over on these frames: 9 Oct 09:40 / 10:30, all 16 Oct after 09:48, and 19 Oct 09:55 (a UX hole 09:33–09:39
  inside the 30 minutes).

**Rule 3: speed.**
- rate5 ÷ today's rate30, from the same source. `tez ↑` at ≥ 1.5, `dheema ↓` at ≤ 0.67, else `·`.
- Before 09:47 it reads `09:47 se`.
- A 30-min window that is not whole gives `? UX` / `? GC`.
- **Judgement call:** the speed's words print only while the side is not noise, meaning pace now *or* its 30-min peak is
  ≥ p70. Without this gate a dead side going from 3 to 5 lots/min would print `tez ↑`.
- When the side cannot be ranked at all (EXPIRY), the gate is off, and the ratio's own 1.5 / 0.67 speak.
- **Peak marker.**
  - The window end with the highest pace among the windows ending T−25…T (minute steps on UX, 5-min on GC).
  - It reads `peak HH:MM` while pace now ≥ 0.6 × peak, else `peak se neeche`.
  - With no reference, the peak is taken in raw lots.
  - **The peak is plain grey ink: never the side's colour, never loud.** The first render drew it loud, and a
    25-minute-old burst became the loudest cell on the row.

**Rule 4: windows.** NIFTY and BANKNIFTY pace are 5 min; SENSEX pace is 15 min with the 30-lot floor (`rank.LOT_FLOOR`).
Nothing is shorter than 5 min.

**Rule 5: EK-TARFA (15 min).**
- imb = (b − s) ÷ (b + s), printed as the winner's share, e.g. `sellers 64%`.
- |imb| is ranked per source, against the same 30-min slot and kind.
- Two-source rule, with `rank.two_source`'s semantics:
  - both sources ≥ p70 with the same winner → `GC+UX ✓`, and the weaker source's share is printed;
  - opposite winners with either source ≥ p70 → `sources ulte`, cell grey;
  - same winner but one below p70 → grey `·` tagged `GC+UX` (*judgement call*: "ulte", meaning opposite, would be false
    here);
  - one source absent or unrankable → the other, uncapped, tagged `GC only` / `UX only`.

**Rule 6: OI build (15 min, ATM±2).**
- Σ over the 5 strikes at ATM by spot at T: oi_chg(T) − oi_chg(T−15), in L (lakh units).
- |build| is ranked against |build| for every minute of the same 30-min slot on prior same-kind chain days (from 20 Aug;
  backfill minutes included, [I]).
- 19 Oct EXPIRY has 5 expiry chain days, enough to rank.
- Negative and ≥ p70 → `nikal rahe` in the bar cell.
- Colour: CALL add = red, PUT add = green, unwinding the opposite.
- **OI speed** = (build15 ÷ 15) ÷ (build60 ÷ 60), with flow's words. Rules for it:
  - its words show only if build15 or build60 (ranked the same way) is ≥ p70;
  - **opposite signs print `palat`** (judgement call: the draft has no word for a build that turned);
  - it needs 60 minutes of today's OI, so it reads `10:16 se` / `10:17 se` until then;
  - a missing minute 60 back reads `? OI`.
- **Sabse tez strike:** the ATM+j (j = −2…+2) whose 15-min change ranks highest against *ATM+j's own* slot and kind normal.
  It is shown when ≥ p70, else `·`.
- Missing pieces:
  - ATM±2 off the 17 recorded strikes → `? strike bahar`;
  - no OI minute → `? OI khali`.
- The subtitle says `REST [I]` when either end of the window is a backfill minute.

**Rule 7: FUT OI × price (15 min; the draft does not give the window).**
- ΔOI15 in L, so the block has one unit; Δprice15 in points. Each |value| is ranked on its own.
- Both ≥ p70 → `naye long` / `naye short` / `covering` / `long nikal`; else `flat`.
- Source: UX, else GC.
- A publication-step guard (`|ΔOI| > the window's lots traded` → `? OI step`) is built. It fired on none of the 15 frames.

**Rule 8: TREND.** Four arrows, each only when its own row is ≥ p70:
- price: the 15-min futures price change;
- flow: EK-TARFA, when coloured;
- OI: CALL/PUT, when they agree. Both ≥ p70 in opposite directions → `OI dono`, no arrow;
- fut: the FUT OI word.

Then the count, shown as the block's first line:
- the line reads `k/4 saath`, coloured at k ≥ 2 and loud at k ≥ 3;
- equal ups and downs give `bata hua`; otherwise `·`;
- the READ's since-time is appended only when the READ points the same way; `READ ulta` when it points the other way.

It is a count. Nothing is a probability.

**Rule 9: DOOSRE INDEX.**
- **σ (judgement call):** the draft's "own σ".
  - Taken as the VWAP-band σ, it printed −4.0σ to −4.9σ on ordinary mornings: early σ is tiny, and the move from the open
    is not the distance from VWAP.
  - So σ = the RMS of the index's open-to-T spot move on prior same-kind days at the same clock (≥ 5 days).
  - Move = spot(T) − the first spot minute, which must be by 09:20, else `? spot`.
  - |move| is ranked at the same clock for rule 1.
- **Spot, not futures:** the row is about the index, and the chain backfill covers 16 Oct's UX gap.
- **Pace:** total lots (b + s), UX, 5 min (SENSEX 15 min, 30-lot floor).
- **OI state:**
  - the stronger ATM±2 leg at p70+ → `call likh` / `put likh` / `call nikal` / `put nikal`, plus `tez` when its OI speed
    ≥ 1.5;
  - both legs the same sign → `dono likh` / `dono nikal`;
  - else `OI flat`.
- **Confirm:** on spot minute closes for all three indices.
  - NIFTY's session high (low) is first reached within the last 15 min, and the peer's last-15-min high is below its own
    session high by more than 0.25σ → `high confirm nahi ✗` (`low` likewise).
  - Otherwise the draft's literal `saath ✓`, **grey**, with the hover saying nothing was tested.
  - Peer data missing at T → `?` takes precedence over the literal ✓.
  - Over the 30 peer cells: 10 vacuous `saath ✓` (nothing tested), 11 tested `saath ✓`, 2 `confirm nahi ✗`, 7 `?`.

**Rule 10: the rest.**
- SIRF BADE: v2.4's own order (TIKA first, then newest), first 3 rows; `+N aur · baaki M chhote` in the subtitle.
- PLAN: ≤ 2 rows. A plan without a zone reads `WAIT 0945 · koi zone nahi`; a missing plan reads its reason in ≤ 6 words
  (`plan ?: fut ticks 18/25 nahi`).
- `?`: one line, the first could-not-check (else checked-nothing, else not-shown) plus `+N …`. All three lists are in its
  hover, never merged.
- Header: as today, plus `READ 09:50 ka` when the READ row is more than 5 min older than T (16 Oct 10:00–11:05, when
  TapeMap had no feed).

**Rule 11: no look-ahead.**
- Every window ends at T, and every level is the bar ending at T.
- References are strictly earlier days (asserted).
- Note: on 16 Oct the GC bars 09:50–11:10 are `fromTicks:false` snapshot bars, and the backfill was fetched at 11:12. Both
  describe market time ≤ T, but live, on that day, the panel would not have had them at T, because the recorder was down.

## What was impossible, and what the face says
| Gap | Where it hit | Cell |
|---|---|---|
| Speed before 09:47 | 9 Oct 09:40, 16 Oct 09:40 | `09:47 se` |
| OI speed before 60 min of OI | every frame before 10:16 | `10:16 se` |
| Fewer than 5 same-kind days | **every 19 Oct flow cell** (2–3 prior NIFTY expiry days in UX and GC); 19 Oct FUT OI | `? ref kam` (the `?` line: `bechne ref kam: 2 expiry din`) |
| No whole UX / GC window | random frames after the recorders stopped; peers on 16 Oct after 09:48 | `? feed nahi`, `? UX` |
| Chain gap 60 min back, no backfill | 12 Oct 13:30 OI speed (chain gap 11:20–12:58) | `? OI` |
| ATM±2 outside the 17 strikes | SENSEX on 12 Oct 13:30, 19 Oct 12:40 / 14:30 | `? strike bahar` |
| No futures OI at both ends | 9 Oct 09:40; 16 Oct 10:00–11:05 (UX gone, GC snapshot bars have `oi` null) | `? OI nahi` |
| Index spot not from 09:20 | SENSEX on 9 Oct (backfill begins 09:25); 9 Oct 14:35 / 12 Oct 14:25 (no chain) | `? spot` |
| SENSEX below 30 lots in 15 min | (floor built; did not bite on these frames) | `·` |
| GC second source for BANKNIFTY / SENSEX | always | the peer row has no EK-TARFA |
| A sub-5-min pace | never built (rule 4) | — |

No value is ever filled with a zero or a guess. Every `?` cell carries its reason in the hover and in the `?` line.

## Looked at as a trader (from the screenshots)
These were fixed after looking at the renders:
- columns cut `peak se neeche`, `23,200 +19L` and `? strike bahar`;
- EK-TARFA wrapped to two lines;
- `?` cells printed whole sentences;
- a past peak drawn loud;
- a loud spanning cell tinted three columns;
- `−0.0σ`.

Still true, by the rules:
- On a quiet frame the four blocks are mostly light grey, which is the point of rule 1. The eye goes to the 1–3 tinted
  cells.
- On 19 Oct, the expiry day, the top block is `? ref kam` all day.
- EK-TARFA reached `GC+UX ✓` on 1 of the 5 frames where both sources were present.
- The panel uses about 620 of its 820 px. Its width, not its height, is the constraint.

<!-- SELF-CHECK: generated by build_panel.py; everything below this line is rewritten on every run -->

## Self-check: the inputs behind every cell (generated)

Units: flow in lots; option OI in units (÷ 1e5 = L); futures OI in units; prices in points. "p70 / p90" are the pool's cut points: a value at or above p70 is coloured, at or above p90 is loud. `?` cells name what was missing.

### 2026-10-16 10:00 (NORMAL day)

```
NIFTY  FADE 09:45 se            23,034f | ≈23,030s  10:00  [READ 09:50 ka]
P phase · R roka · T thakan · Z zor · B bada · ✕ toota
KAUN DABA RAHA   (5m × normal · GC only · kam data)
  BECHNE WALE  1.6×  ·  ·  peak 09:40
  KHARIDNE WALE  1.8×  ·  ·  peak 09:35
  EK-TARFA 15m  ·  GC only
KAUN LIKH RAHA   (15m · ATM±2 · REST [I] · kam data)
  CALL  +35L  ·  10:16 se  23,000 +12L
  PUT  +23L  ·  10:16 se  ·
  FUT OI  ? OI nahi
TREND   (15m · count, no %)
  ·
  · price  · flow  · OI  · fut
DOOSRE INDEX   (spot σ · pace · OI · confirm · kam data)
  BANKNIFTY  −0.6σ  ? UX  OI flat  saath ✓
  SENSEX 15m  −0.1σ  ? UX  OI flat  saath ✓
SIRF BADE   (baaki 0 chhote)
  09:35  P  Sellers phase 22,915f 43K
  09:25  T  Sellers thake 22,946f  ✕
PLAN
  plan ?: fut ticks 5/15 nahi
?
  could not check: fut OI nahi · +6 …
```

**KAUN DABA RAHA**

- **BECHNE WALE** (GC, 5-min window to 10:00): today's lots = 430  [09:55 b499 s430]
  - same window on prior NORMAL days: 09-11 194, 09-18 132, 09-21 124, 09-23 119, 09-24 457, 09-25 265, 09-28 1097, 10-01 406, 10-05 567, 10-07 426, 10-08 236, 10-09 735, 10-12 209 → median **265**; x = 430 ÷ 265 = **1.62×**
  - rank of x: pool 78 values over 13 NORMAL day(s) · p70 = 1.77×, p90 = 2.89× → **p64.1**
- **BECHNE WALE speed**: rate5 86.0 ÷ rate30 86.3 lots/min = **1.0×** · gate True · peak 2.37 at 09:40 (p93.5) · now 1.62
- **KHARIDNE WALE** (GC, 5-min window to 10:00): today's lots = 499  [09:55 b499 s430]
  - same window on prior NORMAL days: 09-11 275, 09-18 125, 09-21 135, 09-23 179, 09-24 369, 09-25 490, 09-28 400, 10-01 254, 10-05 494, 10-07 503, 10-08 214, 10-09 1081, 10-12 245 → median **275**; x = 499 ÷ 275 = **1.81×**
  - rank of x: pool 78 values over 13 NORMAL day(s) · p70 = 1.87×, p90 = 3.65× → **p67.9**
- **KHARIDNE WALE speed**: rate5 99.8 ÷ rate30 98.7 lots/min = **1.01×** · gate True · peak 2.97 at 09:35 (p90.9) · now 1.81
- **EK-TARFA GC**: buy 846, sell 775 → (b − s) ÷ (b + s) = **+0.044** (winner 52%) · rank of |imb|: pool 78 values over 13 NORMAL day(s) · p70 = 0.15, p90 = 0.26 → **p29.5**
- **EK-TARFA UX**: Upstox minutes not whole in the window: 09:48..09:59 (12 of 15)

**KAUN LIKH RAHA**

- **CALL**: spot 23026.95 → ATM 23050; oi_chg (units) end − start per strike: 22950: 8014565 − 8230300; 23000: 12831845 − 11680500; 23050: 5585320 − 4288245; 23100: 8448375 − 7871760; 23150: 2732665 − 1998490 [sources I/M]
  - Σ ÷ 1e5 = **35.43L** · rank of |build|: pool 594 values over 22 NORMAL day(s) · p70 = 44.36L, p90 = 87.57L → **p62.8**
- **CALL speed**: no value (see the cell's `?`)
- **CALL strike**: ATM-1, 15-min change **11.51L** · against ATM-1's own normal: pool 594 values over 22 NORMAL day(s) · p70 = 9.87L, p90 = 19.77L → **p74.9**
- **PUT**: spot 23026.95 → ATM 23050; oi_chg (units) end − start per strike: 22950: 7070310 − 6438965; 23000: 3888950 − 2598700; 23050: 1376700 − 1274000; 23100: 1133015 − 915525; 23150: 340275 − 285350 [sources I/M]
  - Σ ÷ 1e5 = **22.97L** · rank of |build|: pool 594 values over 22 NORMAL day(s) · p70 = 46.82L, p90 = 92.55L → **p47.5**
- **PUT speed**: no value (see the cell's `?`)
- **PUT strike**: ATM-1, 15-min change **12.90L** · against ATM-1's own normal: pool 594 values over 22 NORMAL day(s) · p70 = 13.12L, p90 = 27.43L → **p69.0**
- **FUT**: no value (see the cell's `?`)

**TREND**

- **count**: price +0, flow +0, OI +0, fut +0 → 0 up, 0 down

**DOOSRE INDEX**

- **BANKNIFTY σ move**: spot -104.0 pts since the 09:16 open; prior NORMAL same-clock moves 08-21 192.9, 08-24 -124.5, 08-26 145.5, 08-27 38.8, 08-31 -103.4, 09-01 -142.4, 09-04 -74.5, 09-11 160.8, 09-22 58.4, 09-23 90, 09-24 -136.3, 09-25 -160.3, 09-28 -283.4, 10-01 138.3, 10-05 -230.1, 10-06 45.3, 10-07 56.9, 10-08 32.1, 10-09 358.8, 10-12 -224.1, 10-13 468.6 → σ = RMS = 189.1 → **-0.55σ**, |move| p38.1
- **BANKNIFTY pace** (UX, NORMAL): Upstox minutes not whole in the window: 09:55..09:59 (5 of 5)
- **BANKNIFTY ce15**: 0.68L · pool 719 values over 27 NORMAL day(s) · p70 = 0.69L, p90 = 2.51L → **p69.8**
- **BANKNIFTY pe15**: 0.56L · pool 719 values over 27 NORMAL day(s) · p70 = 0.93L, p90 = 1.90L → **p54.4**
- **BANKNIFTY confirm**: NIFTY high 23050.25 @09:15, low 22916.0 @09:36 (new high False, new low False); BANKNIFTY session H 55802.05 / L 55545.2, last-15m h 55639.95 / l 55547.55; tol 47.3 pts
- **SENSEX σ move**: spot -31.2 pts since the 09:15 open; prior NORMAL same-clock moves 08-21 89.2, 08-24 -165.1, 08-25 0.2, 08-26 89, 08-31 -128.2, 09-01 -82.4, 09-04 20.6, 09-11 60.6, 09-22 69.9, 09-23 -38, 09-25 -111.4, 09-28 -327.9, 09-29 -392.5, 09-30 271, 10-05 119.2, 10-06 268.3, 10-07 -6.3, 10-12 -480.8, 10-13 797.3 → σ = RMS = 269.2 → **-0.12σ**, |move| p15.8
- **SENSEX pace** (UX, NORMAL): Upstox minutes not whole in the window: 09:48..09:59 (12 of 15)
- **SENSEX ce15**: 1.88L · pool 627 values over 23 NORMAL day(s) · p70 = 4.23L, p90 = 8.21L → **p40.2**
- **SENSEX pe15**: 1.32L · pool 627 values over 23 NORMAL day(s) · p70 = 4.69L, p90 = 9.02L → **p20.6**
- **SENSEX confirm**: NIFTY high 23050.25 @09:15, low 22916.0 @09:36 (new high False, new low False); SENSEX session H 74409.94 / L 74026.56, last-15m h 74378.69 / l 74126.1; tol 67.3 pts

### 2026-10-16 11:05 (NORMAL day)

```
NIFTY  FADE 09:45 se            23,110f | spot ?  11:05  [READ 09:50 ka]
P phase · R roka · T thakan · Z zor · B bada · ✕ toota
KAUN DABA RAHA   (5m × normal · GC only · kam data)
  BECHNE WALE  1.9×  ▮▮▯▯▯  ·  peak se neeche
  KHARIDNE WALE  1.4×  ·  ·  peak 10:40
  EK-TARFA 15m  sellers 64%  GC only
KAUN LIKH RAHA   (15m · ATM±2 · REST [I] · kam data)
  CALL  +79L  ▮▮▮▮▮  tez ↑  23,200 +19L
  PUT  −6.7L  ·  palat  23,000 −4.7L
  FUT OI  ? OI nahi
TREND   (15m · count, no %)
  2/4 saath
  · price  ▼ flow  ▼ call likh  · fut
DOOSRE INDEX   (spot σ · pace · OI · confirm · kam data)
  BANKNIFTY  −0.1σ  ? UX  call likh tez  saath ✓
  SENSEX 15m  +0.8σ  ? UX  OI flat  saath ✓
SIRF BADE   (+6 aur · baaki 5 chhote)
  10:50  B  Bada seller 23,092f 20K
  10:45  T  Sellers thake 23,080f
  10:40  Z  Sellers ka zor 23,095f
PLAN
  plan ?: fut ticks 26/36 nahi
?
  could not check: fut OI nahi · +8 …
```

**KAUN DABA RAHA**

- **BECHNE WALE** (GC, 5-min window to 11:05): today's lots = 333  [11:00 b197 s333]
  - same window on prior NORMAL days: 09-11 146, 09-18 41, 09-21 44, 09-23 65, 09-24 401, 09-25 464, 09-28 459, 10-01 146, 10-05 131, 10-07 188, 10-08 175, 10-09 191, 10-12 418 → median **175**; x = 333 ÷ 175 = **1.90×**
  - rank of x: pool 78 values over 13 NORMAL day(s) · p70 = 1.55×, p90 = 3.27× → **p76.9**
- **BECHNE WALE speed**: rate5 66.6 ÷ rate30 71.8 lots/min = **0.93×** · gate True · peak 3.84 at 10:55 (p93.6) · now 1.90
- **KHARIDNE WALE** (GC, 5-min window to 11:05): today's lots = 197  [11:00 b197 s333]
  - same window on prior NORMAL days: 09-11 102, 09-18 69, 09-21 117, 09-23 112, 09-24 238, 09-25 561, 09-28 189, 10-01 120, 10-05 132, 10-07 189, 10-08 143, 10-09 202, 10-12 362 → median **143**; x = 197 ÷ 143 = **1.38×**
  - rank of x: pool 78 values over 13 NORMAL day(s) · p70 = 1.63×, p90 = 2.62× → **p62.8**
- **KHARIDNE WALE speed**: rate5 39.4 ÷ rate30 45.4 lots/min = **0.87×** · gate True · peak 2.11 at 10:40 (p88.5) · now 1.38
- **EK-TARFA GC**: buy 649, sell 1132 → (b − s) ÷ (b + s) = **-0.271** (winner 64%) · rank of |imb|: pool 78 values over 13 NORMAL day(s) · p70 = 0.19, p90 = 0.33 → **p87.2**
- **EK-TARFA UX**: Upstox minutes not whole in the window: 10:50..11:04 (15 of 15)

**KAUN LIKH RAHA**

- **CALL**: spot 23104.2 → ATM 23100; oi_chg (units) end − start per strike: 23000: 2729415 − 2157480; 23050: 1948960 − 968565; 23100: 10180235 − 7602985; 23150: 8893820 − 7065370; 23200: 8222370 − 6284460 [sources I/I]
  - Σ ÷ 1e5 = **78.96L** · rank of |build|: pool 654 values over 23 NORMAL day(s) · p70 = 23.96L, p90 = 48.62L → **p97.4**
- **CALL speed**: build15 78.96L, build60 9.89L → (15m/15) ÷ (60m/60) = **31.94×** · build60 p17.0 · gate True
- **CALL strike**: ATM+2, 15-min change **19.38L** · against ATM+2's own normal: pool 654 values over 23 NORMAL day(s) · p70 = 3.91L, p90 = 9.40L → **p98.3**
- **PUT**: spot 23104.2 → ATM 23100; oi_chg (units) end − start per strike: 23000: 9483760 − 9950460; 23050: 5784870 − 5956665; 23100: 10423660 − 9834045; 23150: 4455490 − 5060250; 23200: 2539485 − 2556645 [sources I/I]
  - Σ ÷ 1e5 = **-6.71L** · rank of |build|: pool 654 values over 23 NORMAL day(s) · p70 = 22.58L, p90 = 37.82L → **p27.5**
- **PUT speed**: build15 -6.71L, build60 224.54L → (15m/15) ÷ (60m/60) = **-0.12×** · build60 p97.3 · gate True
- **PUT strike**: ATM-2, 15-min change **-4.67L** · against ATM-2's own normal: pool 654 values over 23 NORMAL day(s) · p70 = 3.00L, p90 = 5.61L → **p84.6**
- **FUT**: no value (see the cell's `?`)

**TREND**

- **count**: price +0, flow -1, call likh -1, fut +0 → 0 up, 2 down

**DOOSRE INDEX**

- **BANKNIFTY σ move**: spot -28.5 pts since the 09:16 open; prior NORMAL same-clock moves 08-21 201.5, 08-24 -301, 08-26 34, 08-27 -40.7, 08-31 -166.8, 09-01 7.8, 09-04 14.7, 09-11 229, 09-22 -227.5, 09-23 209.9, 09-24 -100.3, 09-25 -50.6, 09-28 -466.8, 10-01 111.8, 10-05 -477.5, 10-06 55.3, 10-07 550.4, 10-08 79.5, 10-09 345.4, 10-12 -547.1 → σ = RMS = 275.0 → **-0.10σ**, |move| p10.0
- **BANKNIFTY pace** (UX, NORMAL): Upstox minutes not whole in the window: 11:00..11:04 (5 of 5)
- **BANKNIFTY ce15**: 0.84L · pool 758 values over 27 NORMAL day(s) · p70 = 0.52L, p90 = 1.35L → **p83.0**
- **BANKNIFTY pe15**: 0.16L · pool 758 values over 27 NORMAL day(s) · p70 = 0.50L, p90 = 1.27L → **p35.9**
- **BANKNIFTY confirm**: NIFTY high 23145.9 @10:36, low 22916.0 @09:36 (new high False, new low False); BANKNIFTY session H 55863.2 / L 55545.2, last-15m h 55706.75 / l 55632.55; tol 68.7 pts
- **SENSEX σ move**: spot +234.5 pts since the 09:15 open; prior NORMAL same-clock moves 08-21 153, 08-24 -303.4, 08-25 1.4, 08-26 -99.7, 08-31 -188.2, 09-01 153, 09-04 78.8, 09-11 105.5, 09-22 -195.2, 09-23 117.3, 09-25 -6.9, 09-28 -489.6, 09-29 -404.5, 09-30 290.4, 10-05 -170.1, 10-06 336.4, 10-07 316.1, 10-12 -811.6 → σ = RMS = 302.0 → **+0.78σ**, |move| p61.1
- **SENSEX pace** (UX, NORMAL): Upstox minutes not whole in the window: 10:50..11:04 (15 of 15)
- **SENSEX ce15**: 1.72L · pool 628 values over 23 NORMAL day(s) · p70 = 2.19L, p90 = 5.96L → **p62.7**
- **SENSEX pe15**: 0.03L · pool 628 values over 23 NORMAL day(s) · p70 = 2.55L, p90 = 8.26L → **p1.0**
- **SENSEX confirm**: NIFTY high 23145.9 @10:36, low 22916.0 @09:36 (new high False, new low False); SENSEX session H 74768.78 / L 74026.56, last-15m h 74679.87 / l 74557.26; tol 75.5 pts

### 2026-10-19 14:30 (EXPIRY day)

```
NIFTY  RIDE ▼ 13:15 se          22,888f | ≈22,860s  14:30
P phase · R roka · T thakan · Z zor · B bada · ✕ toota
KAUN DABA RAHA   (5m × normal)
  BECHNE WALE  ? ref kam  ·  peak se neeche
  KHARIDNE WALE  ? ref kam  ·  peak se neeche
  EK-TARFA 15m  ? ref kam
KAUN LIKH RAHA   (15m · ATM±2 · kam data)
  CALL  +54L  ·  ·  22,950 −15L
  PUT  +17L  ·  ·  22,750 +30L
  FUT OI  +0.1L  price ↓  ? ref kam
TREND   (15m · count, no %)
  ·
  · price  · flow  · OI  · fut
DOOSRE INDEX   (spot σ · pace · OI · confirm · kam data)
  BANKNIFTY  −0.5σ  ·  OI flat  low confirm nahi ✗
  SENSEX 15m  ▼−3.0σ  ·  ? strike bahar  saath ✓
SIRF BADE   (+14 aur · baaki 25 chhote)
  14:25  B  Bada seller 22,878f 14K
  13:20  Z  Sellers ka zor 22,915f
  13:20  Z  Sellers ka zor 22,888f
PLAN   (TREND)
  SELL ▼ ARMED  ZONE 22,923–23,002f  +35
  KILL VWAP 23,002f  T1 −2σ 22,844f  +114 / −44
?
  could not check: bechne ref kam: 2 expiry din · +7 …
```

**KAUN DABA RAHA**

- **BECHNE WALE** (UX, EXPIRY): only 2 EXPIRY day(s) with this UX window before 2026-10-19 (rank needs 5)
- **BECHNE WALE speed**: rate5 68.0 ÷ rate30 58.4 lots/min = **1.16×** · gate True · peak 641.00 at 14:26 (p?) · now 340.00
- **KHARIDNE WALE** (UX, EXPIRY): only 2 EXPIRY day(s) with this UX window before 2026-10-19 (rank needs 5)
- **KHARIDNE WALE speed**: rate5 64.2 ÷ rate30 69.2 lots/min = **0.93×** · gate True · peak 887.00 at 14:24 (p?) · now 321.00
- **EK-TARFA GC**: only 2 EXPIRY day(s) in the GC reference for this slot (rank needs 5)
- **EK-TARFA UX**: only 2 EXPIRY day(s) in the UX reference for this slot (rank needs 5)

**KAUN LIKH RAHA**

- **CALL**: spot 22856.05 → ATM 22850; oi_chg (units) end − start per strike: 22750: 899600 − 685165; 22800: 6613165 − 4978545; 22850: 16137485 − 12081680; 22900: 32523140 − 31556200; 22950: 25683710 − 27147055 [sources M/M]
  - Σ ÷ 1e5 = **54.08L** · rank of |build|: pool 120 values over 5 EXPIRY day(s) · p70 = 126.46L, p90 = 408.50L → **p50.8**
- **CALL speed**: build15 54.08L, build60 228.12L → (15m/15) ÷ (60m/60) = **0.95×** · build60 p30.4 · gate False
- **CALL strike**: ATM+2, 15-min change **-14.63L** · against ATM+2's own normal: pool 120 values over 5 EXPIRY day(s) · p70 = 14.20L, p90 = 22.16L → **p71.7**
- **PUT**: spot 22856.05 → ATM 22850; oi_chg (units) end − start per strike: 22750: 16406845 − 13422695; 22800: 23236005 − 19864650; 22850: 19083675 − 19304025; 22900: 7063550 − 10144355; 22950: 782340 − 2170935 [sources M/M]
  - Σ ÷ 1e5 = **16.66L** · rank of |build|: pool 120 values over 5 EXPIRY day(s) · p70 = 105.76L, p90 = 199.24L → **p25.0**
- **PUT speed**: build15 16.66L, build60 189.25L → (15m/15) ÷ (60m/60) = **0.35×** · build60 p54.4 · gate False
- **PUT strike**: ATM-2, 15-min change **29.84L** · against ATM-2's own normal: pool 120 values over 5 EXPIRY day(s) · p70 = 20.24L, p90 = 25.26L → **p95.0**
- **FUT** (UX): (close, oi) at T = (22887.9, 16548350), at T−15 = (22903.3, 16543215); lots traded in the 15 min 2670; step guard False
  - ΔOI = **0.051L** · NOT RANKED: only 2 EXPIRY day(s) in the UX reference for this slot (rank needs 5)
  - Δprice = **-15.4 pts** · NOT RANKED: only 2 EXPIRY day(s) in the UX reference for this slot (rank needs 5)
  - word: —

**TREND**

- **count**: price +0, flow +0, OI +0, fut +0 → 0 up, 0 down

**DOOSRE INDEX**

- **BANKNIFTY σ move**: spot -170.3 pts since the 09:15 open; prior NORMAL same-clock moves 08-21 158.5, 08-24 -466.9, 08-27 -137.1, 08-31 -145, 09-01 -265.6, 09-11 797.2, 09-22 -205, 09-23 246.3, 09-24 -284.3, 09-25 40.8, 09-28 -508.4, 10-01 -505.3, 10-05 -362.6, 10-06 71.5, 10-07 486.5, 10-08 -377.4 → σ = RMS = 371.1 → **-0.46σ**, |move| p31.2
- **BANKNIFTY pace** (UX, 5-min window to 14:30): today's lots = 88  [14:25 b19 s15 14:26 b11 s6 14:27 b20 s5 14:28 b3 s1 14:29 b7 s1]
  - same window on prior NORMAL days: 09-22 117, 09-23 48, 09-24 82, 09-25 271, 09-28 357, 10-01 250, 10-05 37, 10-06 370, 10-07 1493, 10-08 507 → median **260.5**; x = 88 ÷ 260.5 = **0.34×**
  - rank of x: pool 299 values over 10 NORMAL day(s) · p70 = 2.08×, p90 = 4.12× → **p15.7**
- **BANKNIFTY ce15**: -0.01L · pool 653 values over 23 NORMAL day(s) · p70 = 0.40L, p90 = 1.07L → **p2.7**
- **BANKNIFTY pe15**: 0.30L · pool 653 values over 23 NORMAL day(s) · p70 = 0.36L, p90 = 0.84L → **p65.4**
- **BANKNIFTY confirm**: NIFTY high 23170.7 @09:18, low 22848.95 @14:27 (new high False, new low True); BANKNIFTY session H 55729.95 / L 55342.3, last-15m h 55502.35 / l 55438.7; tol 92.8 pts
- **SENSEX σ move**: spot -916.5 pts since the 09:15 open; prior NORMAL same-clock moves 08-21 58.2, 08-24 -532.6, 08-31 -180.3, 09-01 -152.2, 09-11 599.9, 09-22 -156.8, 09-23 195.2, 09-25 148.6, 09-28 -555.7, 09-29 -192.7, 09-30 38.7, 10-05 26.7, 10-06 412.6, 10-07 107 → σ = RMS = 306.7 → **-2.99σ**, |move| p100.0
- **SENSEX pace** (UX, 15-min window to 14:30): today's lots = 40  [14:15 b5 s4 14:16 b0 s0 14:17 b0 s0 14:18 b0 s0 14:19 b0 s0 14:20 b0 s0 14:21 b0 s0 14:22 b0 s0 14:23 b5 s0 14:24 b0 s1 14:25 b0 s10 14:26 b0 s13 14:27 b0 s0 14:28 b0 s1 14:29 b1 s0]
  - same window on prior NORMAL days: 09-22 54, 09-23 24, 09-25 549, 09-28 41, 09-29 5, 09-30 63, 10-05 19, 10-06 24, 10-07 84 → median **41**; x = 40 ÷ 41 = **0.98×**
  - rank of x: pool 259 values over 9 NORMAL day(s) · p70 = 1.93×, p90 = 4.51× → **p51.7**
- **SENSEX ce15**: ? · NOT RANKED: ATM 73,700 ±2 is outside the recorded 17 strikes (73,900..75,500)
- **SENSEX pe15**: ? · NOT RANKED: ATM 73,700 ±2 is outside the recorded 17 strikes (73,900..75,500)
- **SENSEX confirm**: NIFTY high 23170.7 @09:18, low 22848.95 @14:27 (new high False, new low True); SENSEX session H 74806.06 / L 73722.19, last-15m h 73811.06 / l 73722.19; tol 76.7 pts
