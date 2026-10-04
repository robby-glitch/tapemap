# Real or fake? The OI flow split by side, against the index move: round 3 (analysis only)

Mary, 2026-10-03, after reading the 1 Oct three-index table:

> "are we looking at the rate of change because it goes to negative than positive to negative and we need to identify
> power move … the first sign where kind of across the strike write covers … suppose market is moving up and call
> writers are not closing there position … actually even increasing and also look at the rate if chanf on put side …
> so that way also we can check if the market moves are real or fake"

Nothing is built from this note. It is a display read [I] that gates nothing, and she decides whether it goes on the
Board.

## 1. First principles

**Why the OI Flow "chg in dir" column cannot answer her.** It is Δ(put added − call added) in a slot, so it **nets the
two sides**. All of these print as the same "+":
- call writers covering;
- put writers adding;
- both writers adding, as long as the put side adds more.

They mean opposite things for whether a rise is real. The column flips sign on noise for the same reason: a small
imbalance between two large, unrelated flows. So the two sides are read **separately**.

**Who is on the other side.** Near the money, intraday option OI changes are writer-dominated: `trapped_inventory.py`
assumption 3 [I], right on average and wrong on single strikes. So, per side:

| side | ΔOI > 0 (adding) | ΔOI < 0 (covering) |
|---|---|---|
| CALL | writers sell more calls: they defend or cap above | writers buy calls back: forced if price rises, fuel up |
| PUT | writers sell more puts: they underwrite a floor below | writers buy puts back: forced if price falls, fuel down |

**Against the index move in the same slot** (UP shown; DOWN is the mirror with CALL and PUT swapped):

| call writers | put writers | read | why |
|---|---|---|---|
| covering | adding | **REAL** | forced buying above and a new floor below; both sides of the book act for the move |
| covering | flat or covering | **SQUEEZE** | short-covering fuel with nobody underwriting it; it runs fast and can snap back |
| adding | adding | **CAPPED** | writers sell into the rise while puts build; a range or pin forming, which can be fake |
| adding | flat | **CAPPED** | writers sell into the rise and nobody underwrites; the call side caps it |
| adding | covering | **FAKE** | call writers confident enough to sell more into the rise, put writers taking profit and leaving; nobody in the book believes it |
| flat | adding | **BACKED** | the move's own side builds behind it; no forced flow yet |
| flat | covering | **HOLLOW** | the floor leaves into the rise and there is no fuel |
| flat | flat | **QUIET** | the book is not acting on the move |

**Index flat in the slot** (effort without result, the Wyckoff gap named in `docs/reader/1-research.md` §A1):
- one side **covering** at POWER size gives **PRESSURE** (dabaav), ▲ for calls and ▼ for puts. Writers are getting out
  while price holds, which is pressure building before the move. I did not use "building": on the Board, BUILDING / LIKH
  RAHE already means writers adding.
- one side **adding** at POWER size gives **WALL**: writers build at the level and price is held there.
- otherwise **FLAT**.

Caveats of mechanics, stated before the data:
- On expiry day, writers close for expiry, not because they are forced. Covering there is a weaker read.
- NIFTY weekly expiry is Tuesday; SENSEX weekly expiry is Thursday.
- BANKNIFTY options are monthly and thin: its OI changes are about 1% of NIFTY's. Every measure below is scale-free
  per index for that reason.

## 2. Definitions, FIXED 2026-10-03 23:38 IST, before any slot outcome was computed

Contamination, said plainly: in round 2 I had already seen the NETTED flow (diff, chg_dir, put Δ) and the 5-min spot
moves for these five sessions. I had not seen the per-side split, the breadth, the size ratios or any 15/30-minute
outcome. The numbers below are round, and nothing is moved after this line.

| name | definition |
|---|---|
| grid | the minute grid the server holds: `data/chain_backfill/` marks plus `data/chain/` snapshots, the last snapshot per minute (what `ChainState.update` writes) |
| slot t | each 5-min mark of `ChainState.oi_flow(interval=5)`, which is the OI Flow tab's function; the slot covers (t−5, t] |
| strikes | the OI Flow tab's default set: every strike in the snapshot (a fixed 17-strike window per session; it did not move on 1 Oct) |
| ΔCE(t), ΔPE(t) | Σ over strikes of [oi_chg(t) − oi_chg(t−5)] per side: the OI added in the slot (Upstox's oi_chg is the day's cumulative change) |
| ΔI(t) | index print at t minus at t−5 (the chain poller's spot, the OI Flow tab's "LTP · IDX"). From 15:15 it is CAN'T CHECK: the spot indices freeze for the closing auction (`xindex` FREEZE, measured 29 Sep) |
| day scale M | per index and per series (ΔCE, ΔPE, ΔI): the median of \|Δ\| over that index's EARLIER slots today. **WARM = 6** earlier slots are needed, so the first read is at 09:50 |
| FLAT | \|Δ\| ≤ **0.5 × M**; otherwise ADDING / COVERING (ΔOI) or UP / DOWN (ΔI) |
| breadth | among §1d's nine strikes nearest spot at t (`fronts.nine`), how many moved the SAME way as that side's total (zero changes excluded). **BROAD** means at least **6 of 9** |
| POWER side | \|Δside\| ≥ **3 × M_side** AND broad |
| POWER slot | either side POWER |
| read word | the tables in §1, from the two side states and the index state |
| direction of a POWER slot | from its POWER side(s): CE covering ▲, PE adding ▲, PE covering ▼, CE adding ▼; two POWER sides pointing opposite ways give "both", no direction |
| first sign | a POWER slot with a direction, when the same index had no POWER slot in that direction in the previous **15 minutes**; later ones are continuation |
| three indices | per slot: how many indices are POWER, and whether all three gave the same read word |
| afterwards | the index move from t to t+15 and to t+30, in points, computed only after the above was fixed; listed, never scored |

## 2a. AMENDMENT rev `sides-2`: recorded 2026-10-04 00:25 IST, before Monday 2026-10-05's open

Adopted by the coordinator from Fable 5.1's critique (`FABLE-CRITIQUE-real-vs-fake-2026-10-04.md`); Mary had signed off
the build. The amendment **supersedes §2 where it differs**. The outcome numbers in §4 were computed under §2 (rev
`sides-1`); rev `sides-2` is judged only by forward rows from Monday on. Every number below is fixed now, and a
change is a new revision with its own date.

| # | what changes | the definition, as built in `tapemap/sides.py` |
|---|---|---|
| A1 | strikes | ΔCE and ΔPE are summed over **§1d's nine strikes nearest spot** (`fronts.nine`, at the slot's closing mark, among strikes present at both marks), not the 17-strike window fixed at the open. The 17-strike totals are logged as `dce17` / `dpe17` |
| A2 | breadth / POWER | Each side's **top two by OI inside the nine** are ranked at the closing mark by the OI at the open plus the running high of the day's change up to that mark. That is causal, and it is her §1d ranking as `board.first_fold` applies it. Without the open OI, the running high change alone is used (`fronts.read`'s own fallback), tagged `top2_basis`. A side is **POWER** when \|Δside\| ≥ 3 × its scale **and both top-2 fronts moved the side's way (2/2)**. n/9 is logged only |
| A3 | forced or voluntary | **Chip and log field only; it never re-words the read.** The fuel side is PE for a ▼ slot and CE for a ▲ slot (the POWER direction, else the index move). `fuel_top2_underwater` counts the fuel side's top-2 fronts with `ltp > avg` at the closing mark (`avg` is the contract's own day VWAP), 0–2. `fuel_dIV_med` is the median over the nine of the fuel side's IV change across the slot, in vol points. Both come from the saved chain snapshot at the mark; a mark with no snapshot (a REST-rebuilt one) is CAN'T CHECK |
| A4 | first sign | Each direction is armed at the open. A POWER slot in a direction **disarms** that direction and **re-arms the opposite one**. Later same-direction POWER is continuation (`phir se`). The 15-minute gap rule is gone; there is no number |
| A5 | morning scale | Slots with t ≤ 10:30 are sized against the **previous session's** median \|Δ\| over its slots with from ≥ 10:30 and t ≤ 15:00 ("kal ka scale"; same index, same nine-based sums). This covers the call side, the put side and the index move. *My reading:* the adopted text names "that index and side", and I apply the same basis to the index move so the three ratios are on one footing. Slots with t > 10:30 use today's own expanding median. **Both ratios are logged on every row** (`*_ratio_today`, `*_ratio_kal`). With no previous session on disk, a slot before 10:30 reads CAN'T CHECK with **"subah ka scale — kal ka data nahi"**. It never falls back silently |
| A6 | the chip | **`PUSHTI hh:mm`** (confirmation), not PEHLA SANKET, until kill condition K2 says otherwise |
| — | unchanged | FLAT_K 0.5; POWER_R 3.0; the read-word table; PRESSURE / WALL; the 15:15 freeze; the direction mapping; "a missing index never agrees" |
| — | the count shown | **Mary's decision, 2026-10-04:** count the weekly books, NIFTY + SENSEX (0/1/2), in their own direction. BANKNIFTY is a tagged witness (`BN · monthly · N DTE`), shown and never counted. This is the display default (`COUNT_MODEL = 'weekly'` in `Board.tsx`). Both `n_power` (all three) and `n_weekly_power` are logged on every row, and the three-index line is still computed (`line1`) |

**Display and log only (any day):**
- Under the chip, the exhaustion facts: age, index points since the PUSHTI, `fuel N% gaya` (how much of the fuel
  side's build that stood over the PUSHTI slot's nine has been given back), and `asar` (\|ΔI\| per × of the fuel side,
  PUSHTI slot vs now). No thresholds, no words from them.
- Grinds: `koi power nahi · PE likh rahe 6 slots se` (the side's run of same non-flat states), and that side's §1d
  front state. Never QUIET on a grind, never blank.
- The screen collapses to Fable §6's two lines. The raw side states are logged, so a re-wording never breaks the log.
- Each slot's real minute span and `nine_below_spot` are logged.

**Forward log (`data/sides/sides_YYYY-MM-DD.jsonl`), Fable §5's spec:**
- One `kind:"slot"` row per index per slot, every slot, written once when the slot closes.
- One `kind:"outcome"` row per slot, written once by the live process when t+30 has closed: `f15 f30 mfe30 mae30
  outcome_src`, from the same process's 1-minute grid and never recomputed later.
  - Outcome rows for slots after 14:55 are never written: their window crosses the 15:15 freeze and the 15:30 write
    guard.
- `her_read` and `leg_traded` are empty fields for her.
- The market-hours guard and once-per-row rule are unchanged.

### 2b. AMENDMENT rev `sides-3`: the morning scale. Recorded 2026-10-04 01:25 IST, before Monday's open. **POST-HOC.**

This change was made **after the rows were seen**. The frozen rev `sides-2` run put 146 of 294 PUSHTI at or before
10:30. Fable then measured 723 morning index-slots (`FABLE-TRAP-FRAMEWORK-2026-10-04.md` §6): sized against the
previous session's midday, 472 of them cleared 3×; sized against the previous session's same window, 254 did. The
coordinator decided the change. Only the forward log from Monday on can judge it.

| # | rule |
|---|---|
| B1 | Slots with t ≤ 10:30 are sized against the **previous session's same window**: the median \|Δ\| over its slots with 09:20 ≤ t ≤ 10:30, per index, separately for the call side, the put side and the index move. Not its 10:30–15:00 midday |
| B2 | The morning is shown from the 09:20 slot, tagged `subah · kal ki subah ka scale` |
| B3 | **CAN'T CHECK, with the reason,** when the previous session is missing (`subah ka scale — kal ka data nahi`) or **was that index's expiry day** (`subah ka scale — kal expiry din tha`, because a 0DTE morning is not a like for a fresh-series one). The previous day's expiry comes from its saved chain file (`expiry` on every snapshot since late September). For older files with no `expiry`, the frozen all-sessions run uses the weekday rule, said in its header. Live, the file always has it |
| B4 | **Morning POWER is a WITNESS, not a vote.** For t ≤ 10:30, `n_power` and `n_weekly_power` are 0. The morning counts are logged as `n_power_witness` and `n_weekly_power_witness`, and the screen shows them as `subah · … gina nahi`. This holds until the forward log says otherwise |
| B6 | (01:27 IST, follows from B4) **A morning witness never consumes the day's first sign.** Slots at t ≤ 10:30 keep their own PUSHTI state (a morning PUSHTI is marked and logged as a witness). The counted day starts with both directions armed at the first slot after 10:30. Without this, an uncounted 09:25 POWER ▼ would make 1 Oct 12:10 read as continuation |
| B5 | Every row logs all three bases for the call side, the put side and the index move: `*_ratio_kal_morning`, `*_ratio_kal_midday`, `*_ratio_today`. `*_ratio` is the one the read used, and `M_basis` names it (`kal_morning` / `today`) |

Everything else in §2a is unchanged.

### 2c. Kill bars, SIGNED

**Signed by Mary, 2026-10-04 ~11:10 IST: sab haan.** Every bar K1–K7, K-A–K-D and the optional K-Z is signed **HAAN** as drafted, unchanged, together with the three standing lines. Her words were "yes do all fixes and sab haan", relayed by the coordinator. By the sheet's own rule the clock starts at the first session after signing, Mon 2026-10-05. The 27 sides sessions and the ten trap sessions already seen never count.

These are the bars for this read, copied verbatim from `FABLE-DAYS-ZONE-KILLBARS-2026-10-04.md` §3, which holds the sheet's rules: `f30` signed in the read's direction, `base30` = the session's median |f30| over non-POWER slots, 15 per cell. The trap bars K-A–K-D are signed in `TRAP-PREREG-2026-10-04.md` §5, and the optional zone chip K-Z is in the Fable sheet.

| # | what is compared | fields | judge at | PROPOSED bar | if it fails | sign |
|---|---|---|---|---|---|---|
| **K1** premise | PUSHTI rows with `n_weekly_power = 2`, same direction, 09:50–15:00, not a morning witness, fuel side not on its own expiry day — against `base30` of the same sessions | `first, pdir, n_weekly_power, expiry_day, f30, base30` | 15 rows ▲ **and** 15 rows ▼ | median signed `f30` ≥ **0.75 × base30** in each direction, **and** no more than **5 of each 15** with signed `f30` ≤ 0 | the three-index line leaves the Board; the per-index side rows stay as display | **HAAN** |
| **K2** lag honesty | the firing slot's own move `dI` against what followed | `dI, f30` on K1's rows | the same 15 + 15 | the word PEHLA SANKET may be used only if in **≥ 10 of 15** rows per direction `f30` ≥ **2 × |dI|**; otherwise the chip stays **PUSHTI** for good | (default is already PUSHTI; this bar can only promote) | **HAAN** |
| **K3** BANKNIFTY | BN POWER rows where `n_weekly_power = 0` against BN's own `base30` | `bn_power, n_weekly_power, f30, base30` (BN) | 15 rows per direction | median signed `f30` ≥ **1.0 × base30(BN)** per direction | BN stays a witness only (today's state); passing promotes it to a vote, and that is pre-registered here | **HAAN** |
| **K4** FAKE | rows whose word is FAKE (fuel adding, back covering, on an index move), scored **against** the slot's move (FAKE predicts reversal) | `word, I_state, f30` | 15 up-slot FAKE and 15 down-slot FAKE | median reversal ≥ **0.50 × base30** in both cells | the word FAKE is deleted; the two side states remain on the row | **HAAN** |
| **K5** expiry | covering PUSHTI after 12:00 on the fuel side's own expiry day, split `fuel_top2_underwater` 2/2 vs 0–1/2 | `expiry_day, first, fuel_top2_underwater, f30` | 15 rows in each of the two cells | the 2/2 cell's median signed `f30` ≥ **0.50 × base30 and** the 0–1/2 cell's median ≤ **0** | covering reads are muted after 12:00 on that index's expiry day (`expiry squaring · check nahi`) | **HAAN** |
| **K6** exhaustion | continuation POWER rows (not PUSHTI) with `fuel_left ≥ 100%` against continuation rows with `fuel_left < 50%` | `first = False, fuel_left, f30` | 15 rows in each cell | the ≥ 100% cell's median signed `f30` ≤ **0.25 ×** the < 50% cell's median | `fuel_left` stays a number; passing makes `KHATAM` a word on the chip at ≥ 100% | **HAAN** |
| **K7** grind | her after-close note of the legs she traded or would have traded, against whether a POWER slot occurred in the leg's first 30 minutes | `leg_traded` (hers), `power` rows | 15 noted legs | at most **7 of 15** legs without a POWER slot in their first 30 min | the burst marker is demoted to a chip on the §1d rows and stops being a headline | **HAAN** |

The standing lines, signed with them:

1. **Seen rows never count.** The 27 sides sessions and the ten trap sessions in this and the two earlier Fable
   documents are the record of how the bars were chosen, not evidence for them.
2. **Under 15 per cell is INCONCLUSIVE** and gets no verdict and no screen change, favourable or not.
3. **The scorer must run.** `trigger_log.py score` after each close (or scheduled), or K-Z and every zone question
   above stay unanswerable; the fold outcome rows and the kill-clock reader the review asked for (`tools/kill_clocks.py`)
   are the same need in one file.

## 3. Reuse

| piece | used for |
|---|---|
| `chain_metrics.ChainState.oi_flow` | the slot marks and the spot per mark: the OI Flow tab's own function |
| `fronts.nine` | the near-ATM window for breadth (§1d's nine) |
| `reader.py` WHO | the template: the futures quadrant (price × OI gives new longs, short covering, …) extended here to two option sides |
| `docs/reader/1-research.md` effort vs result | PRESSURE and WALL (big OI effort, no price result) |
| `trapped_inventory.py` | the writer-dominated assumption, quoted, not re-derived |
| `xindex` | the 15:15 freeze and the "a missing index never agrees" rule |
| not reusable | `squeeze_score.py` (retired, only its loader remains); `fronts` §1d states (per front over 15 one-minute marks, not a 5-min per-side aggregate; kept as the Board's verdict) |
| added | the per-side split with breadth and the day-median size ratio: `docs/board/analysis/sides.py` (analysis only; read-only on `data/`; it imports `replay.py` beside it) |

## 4. Results (computed after §2 was fixed; nothing was changed afterwards)

Files:
- `sides-slots-2026-10-01.txt`: every 1 Oct slot, all three indices, with the read word, each side's state ×size (and
  how many of the nine strikes moved that way), and the index move.
- `sides-power-slots-5-sessions.txt`: every POWER slot of the five sessions, with the next 15 and 30 minutes.

Notation:
- `!` marks a first sign.
- ×n is that side's size against its own day median, and n/9 is the breadth.
- "+30" is the index move from that mark to 30 minutes later. Marks after 15:15 have none (the auction freeze).
- These are rows described; there is no tally of how often they "worked".

### 1 Oct (trend down; NIFTY 22,547 → low 22,235; Thursday, SENSEX weekly expiry)

| time | index | read | what moved | 3 indices | +15 / +30 |
|---|---|---|---|---|---|
| 10:35 | BANKNIFTY ! ▲ | REAL | CE covering ×4.2, 7/9 | alone | −71 / −174 |
| **12:10** | NIFTY ! ▼ | REAL | PE covering ×9.0, 9/9; CE adding ×2.8, 9/9 | 2 of 3 POWER (BANKNIFTY's first sign came at 12:25) | −29 / −32 |
| **12:10** | SENSEX ! ▼ | REAL | PE covering ×4.4, 8/9 | | −88 / −107 |
| 12:25 | all three ▼ | REAL · SQUEEZE (BN !) · REAL | PE covering ×3.8 / ×4.8 / ×4.7 | **first slot with 3 of 3 POWER** | −3/−141 · +47/−336 · −18/−467 |
| 12:30 | NIFTY, SENSEX ▼ | REAL | PE covering ×3.6 / ×6.7 | 3 of 3 the same read: REAL | −128 / −420 at +30 |
| 12:35 | BANKNIFTY ▼ | FAKE (on an up slot, +73) | CE adding ×4.3, 8/9 | | −255 / −284 |
| 12:50 | all three ▼ | REAL ×3 (NIFTY !, SENSEX !) | PE covering ×5.0 / ×10.1; BN CE adding ×3.6 | 3 of 3 POWER, 3 of 3 REAL | −30 / −86 / −96 at +30 |
| 13:00 | all three ▼ | PRESSURE · REAL · SQUEEZE | PE covering | 3 of 3 POWER | +30: −19 / +43 / −25 |
| 13:45–14:05 | NIFTY !, BANKNIFTY ! ▼ | SQUEEZE, REAL, SQUEEZE | PE covering ×3.3–3.7 | 1 of 3 each | at the day's low: NIFTY 14:00 +83, BN 14:05 +274 |
| 14:15 | BANKNIFTY | WALL | CE adding ×3.9, price flat | | +157 |
| **14:35** | NIFTY ! ▲, SENSEX ! ▲ | REAL | NIFTY CE covering ×6.2, 9/9; SENSEX CE covering ×3.0 and PE adding ×3.6 | 2 of 3 POWER, 3 of 3 REAL | +54 / +208 at +30 |
| 14:40 | SENSEX | WALL | PE adding ×3.3, price flat | | +242 |
| 15:00 | NIFTY ! ▲ | FAKE (on a −18 dip) | CE covering ×3.4 and PE adding ×3.3 | 3 of 3 FAKE | +53 at +15 |

Her three questions:
- **The 12:10 turn.** Yes, it is found: a first sign ▼ at 12:10 in NIFTY and SENSEX, read REAL. Put writers covered on
  9 of 9 and 8 of 9 strikes at 9.0× and 4.4× the day's median, while call writers added. BANKNIFTY joined at 12:25,
  the first 3-of-3 POWER slot. The netted column showed only "chg_dir ▼"; the split shows both sides acting for the
  fall.
- **10:05–10:25 and 10:40–10:45 ("3/3 BULLISH, no rise").** The method does not call these FAKE, as she expected.
  - It calls them **powerless**: no POWER slot in any index.
  - At 10:05 NIFTY and SENSEX read REAL ▲, but small (sides 1.3–2.0× the median).
  - At 10:10 the dip reads FAKE: the book leaned bullish while price fell.
  - From 10:15 most slots read FLAT or QUIET. BANKNIFTY read CAPPED at 10:20, 10:25, 10:40 and 10:45 (both sides
    adding).
  - So the honest reading of that stretch is "nobody in the book is acting", not "fake". The BULLISH word was the
    cumulative morning put writing, not anything happening in those minutes.
- **The 14:35–15:00 bounce.** It reads **REAL ▲** at 14:35 in NIFTY and SENSEX. Call writers covered on 9 of 9 strikes
  at 6.2× in NIFTY, and put writers underwrote it in SENSEX (×3.6). SENSEX then showed a WALL of put writing at 14:40.
  The 15:00 NIFTY dip reads FAKE. The bounce ran +54 / +208 over the next 30 minutes.

### The other sessions, one paragraph each

- **24 Sep (trend down).**
  - Scattered single-index first signs ▼ from 11:15 (PRESSURE, FAKE on up slots, REAL) were mixed over the next 30 minutes:
    12:30 SENSEX FAKE (up slot) was followed by −57; 12:35 NIFTY and SENSEX REAL ▼ were followed by +12 / +61.
  - At **13:30 all three gave a first sign ▼ in the same slot.** Put writers covered at ×8.7 / ×14.1 / ×8.4 on 9 of 9
    strikes, read REAL, REAL, SQUEEZE. Over the next 30 minutes the indices fell −79 / −179 / −286: the day's main leg.
  - The 14:00 REAL / SQUEEZE ▼ slots came at the low and were followed by +28 / +5.
- **23 Sep (range, Wednesday).**
  - The morning rise (NIFTY 23,375 → 23,46x, put writing in every slot) has **no POWER slot at all**. The writing was
    steady, so it never reached 3× its own median.
  - Midday first signs ▲ (12:05 NIFTY REAL, 12:10 SENSEX REAL, 13:05 BANKNIFTY SQUEEZE) went nowhere (+6 / +10 / −56
    at +30).
  - The late 3-of-3 put covering (15:00–15:15) reads **SQUEEZE ▼, not REAL**: call writers were flat or also
    covering, so nobody built a lid. No fall followed (BANKNIFTY +35 at +15). The split separates it from 1 Oct's
    12:10, where call writers were adding. Still, a first-sign ▼ fired there, and it marked nothing.
- **29 Sep (Tuesday, NIFTY weekly expiry).**
  - **11:15: all three first signs ▲.** Call writers covered at ×8.9 / ×8.8 / ×12.9 on 8–9 of 9 strikes, read SQUEEZE,
    REAL, REAL. Next 30 minutes: +30 / +103 / +75.
  - **12:35: all three ▼.** Put writers covered at ×7.1 / ×5.6 / ×4.1 with price nearly flat (PRESSURE, REAL,
    PRESSURE). **Then all three rose** (+18 / +159 / +73). That was expiry day; writers squaring puts for expiry are not
    forced, which is the caveat stated in §1 before the data.
- **30 Sep (Wednesday).**
  - **12:25: all three first signs ▲** (REAL, REAL, SQUEEZE; call writers covering ×3.6 / ×8.5 / ×4.7). Next 30
    minutes: +36 / +94 / +108.
  - **12:50: 3 of 3 ▲ again**, mostly continuation. **It marked the top:** −17 / −25 / −71 at +30.
  - **14:25: all three first signs ▼** (REAL, SQUEEZE, REAL; put writers covering ×5.0 / ×3.4 / ×4.1 on 9 of 9).
    +15: −53 / −150 / −182. The 14:30 continuation was followed by a snap-back (+19 / +51 / +55 at +30).
  - SENSEX FAKE reads on up slots: 10:40 was followed by −38 at +15 (−16 at +30). 11:20 was followed by +124, wrong.

## 5. Where it fails or stays silent

1. **Silent on steady grinds.** A move built by even writing every slot (23 Sep morning, and 1 Oct 10:50–11:25 call
   writing everywhere) never reaches 3× its own median. POWER finds bursts, not trends that are written in slowly.
2. **It does not know a run is late.** Continuation slots read REAL or SQUEEZE right at exhaustion:
   - 30 Sep 12:50, 3 of 3 ▲, then down;
   - 1 Oct 14:00 NIFTY REAL ▼ and 14:05 BANKNIFTY SQUEEZE ▼ at the day's low, then +83 / +274;
   - 30 Sep 14:30 ▼, then a snap-back.
   SQUEEZE did snap back as the word says, but REAL did too.
3. **Expiry days.** Hard covering on expiry day (29 Sep 12:35, all three ▼) was followed by a rise. Writers closing
   for expiry look identical to writers being forced. The read cannot tell them apart without knowing the day.
4. **Late session.** From about 15:00 writers square off, and from 15:15 there is no spot to read against. 23 Sep
   15:00–15:15 fired first signs that marked nothing (read SQUEEZE, not REAL).
5. **Single-index first signs** often go nowhere: 1 Oct 10:35 BANKNIFTY REAL ▲ (then −174), and 23 Sep's midday
   signs. The three-index slots carried the moves on these days: 24 Sep 13:30, 29 Sep 11:15, 30 Sep 12:25 and 14:25,
   and 1 Oct 12:25 and 12:50.
6. **FAKE on an up slot** was followed by a fall in some rows (1 Oct 12:35 BANKNIFTY; 24 Sep 12:30, 30 Sep 10:40
   SENSEX) and by a rise in others (30 Sep 11:20 SENSEX +124). It is not a clean read.
7. **BANKNIFTY** is monthly and thin. Its ratios run on OI changes about 1% the size of NIFTY's. It behaved like the
   others here, but any single BANKNIFTY slot is the weakest evidence on the screen.
8. The five sessions include three expiry-adjacent days. This is a description of 5 days, not evidence of an edge.
   Per CLAUDE.md §2 it is not a backtest. If Mary wants it on screen, it goes in as a shadow display and is judged by
   forward rows.

## 6. How it could sit on the Board (described only; nothing built, TEENO untouched)

**Per index (inside TEENO's rows or under them):** two thin rows per index, CALL and PUT, over the last 6 slots.
- Each cell is a word chip: `likh` (adding) or `kaat` (covering), or blank when flat.
- A POWER cell is boxed and carries its numbers, e.g. `kaat ×9 · 9/9`.
- Under the two rows sits that slot's read word: REAL / SQUEEZE / CAPPED / FAKE / PRESSURE / WALL / QUIET.

**The first sign** gets one chip with time and index, e.g. `PEHLA SANKET ▼ 12:10 · NIFTY, SENSEX`. It stays until the
episode's 15-minute gap closes it.

**TEENO's count line** could then count the split read instead of the netted chg_dir. For example:
- `3 of 3 REAL ▼ · put writers covering 8–9/9 strikes`;
- `2 of 3 POWER · BANKNIFTY quiet`;
- `alag alag — saavdhaan` when the reads differ.

Mary decides first. Every word stays [I], gates nothing, and shows only counts.

**Guard rails the screen must carry:**
- an "expiry din" tag (finding 3);
- "15:15 se check nahi" (finding 4);
- a marker for continuation vs first sign (finding 2);
- "steady writing, no power" written as words, never as an empty cell (finding 1). Otherwise "quiet" would lie on a
  grind day.
