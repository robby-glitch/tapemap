# 4 (Fable) — The order-flow reader: design

**Designer A, blind.** Written 2026-09-29 after the close. Uses only what `1-research.md`, `2-data-audit.md` and `3-current-reader-audit.md` prove, plus two read-only replays in my scratch folder (`scratchpad\fable\replay.py`, `replay1m.py`; outputs `out_k2.txt`, `out_1m.txt`). No code edited, nothing under `data/`, no git, no server. The other designer's file was not opened.

**One sentence.** The reader cuts the day into legs on 1-minute price, and for each leg says who was aggressive (delta, two tapes), whether positions opened or closed (OI, snapshot-differenced), and what the effort bought (points per 1,000 lots, ranked); it feeds that one sentence to the FLOW row and draws her P/A/E/C at levels from a record that never repaints, and it says loudly when a tape is dead.

Tags: **[M]** measured from a feed, **[I]** inferred (any side, any reconstruction, any percentile), **CAN'T CHECK** with a reason. Session 09:15–15:40, 77 five-minute bars.

---

## 1. The five disputes: sides taken

| # | Side taken | Why (from the evidence) |
|---|---|---|
| **D1 order flow = traded delta or book imbalance?** | **Traded delta, on two tapes (GoCharting vendor side; Upstox quote-rule reconstruction), is primary. Book imbalance is a second-class witness, attached only to the absorption-at-level read as "offer/bid refilled k times [I]".** | Both tapes exist, per bar, all day; the book is 5 levels at ~1 Hz with 54–67 % of volume unlocated (audit §3f). OFI at the touch cannot be built honestly from that. Where the book *can* show the passive side (a level's displayed size restored after prints), it is evidence for a read that already exists, not a read of its own. `sweep.py`/`absorption.py` already produce this; they get one face, inside the A read. |
| **D2 absorption = signal or state?** | **A state of efficiency.** "Absorbed here" is said only when three things hold: location (a leg extreme, a wall, a prior-day level, or inside her zone), a run of ≥ 3 bars of one-sided aggression into the level with no acceptance beyond it, and the OI/effort read of the leg it sits in. It never says "reversal". | Split metaorders make one-sided low-impact flow the normal state (research A6, S22/S23). On 29 Sep the base's four P marks and the 10:05 "absorption" (one 4,528-lot print) were both wrong as signals; the walls with lean counts were right as a state (audit E3). |
| **D3 OI table on expiry/roll days** | **Near-month OI is a fact every day but a *direction* read only outside the roll window.** From the third session before expiry (calendar from instrument data, never a weekday) the near-month state carries the suffix "roll week" and open/close is read on Σ(near + next) OI; on expiry day the near month's state is "closing by construction" and positioning is read on the next month alone. Without the next month recorded, the positioning row is CAN'T CHECK: "Oct not recorded". | Sep OI −24,333 lots at the open and −25,287 on the day (audit §3a); the margin rule pushes rolls before expiry day (research A8); `grounds.py`'s 7-day blind threw the fact away with the direction. |
| **D4 VPIN** | **A gauge, shown as context, one of her four rows only as a number with its percentile and the word "shadow" until its 30-session record qualifies. It never flips a read.** Bucket: the existing fast line (20,000 units) for the row, slow for the tab; reference: percentile of today, mute until 10 buckets. | Critiques S25–S27; the project's own rejection of a cross-day reference; 29 Sep: pct 0.98 at 10:09 was the block, pct 1.0 at 11:10 was the squeeze, pct 0.28 at 13:58 was the afternoon base. It describes one-sidedness, not direction. |
| **D5 unit and reference** | **Unit = the leg** (a directional-change cut on 1-minute closes, reversal δ frozen at the open). **Reference = today's own completed legs with n shown, plus the last five sessions' legs on the same contract as a labelled second yardstick** that also covers warm-up. Warm-up is explicit: "warming, k of 3 legs" until three legs are complete. Expiry days are their own regime: the pool caveat is printed on them. | Bars are noise (S9/S11/S17); the flow-rank bug came from ranking the first minutes against themselves; the VPIN cross-day reference failed on regime. Two yardsticks with names avoid both. δ multiplier chosen on the pool, not on 29 Sep: k = 2 gives 5–9 legs per pool day on 1-minute closes; k = 3 gave 1–3 legs per day on 5-minute closes (too coarse for a 5-minute chart). |

Geometry constants (not thresholds in lots; declared here, frozen at the open, stamped in every read): reversal δ = 2 × B5, where B5 = median 5-minute range of the prior five sessions on the same contract (29 Sep: B5 = 17.5 pts [M] → δ = 35.0); reader row R = B5/20 rounded to the tick, floor 10 ticks (NIFTY 1.0 pt); block print = one price ≥ 50 % of a bar's lots with the bar ≥ 3 × the median bar (pool median until 12 bars today); bar completeness = GoCharting lots ≥ 90 % of Upstox lots for the same bin.

---

## 2. The reads

Every read below is an object with a stable id, a `t` (event time), an `asof` (data time), `tapes` (which tapes it used), `[M]/[I]` per number, and a `hole` field. The FLOW row and the chart draw from these objects; nothing on a face is computed twice.

### 2.0 FEED-HEALTH (the read that gates every other)

- **Definition.** Per tape, per index: `stale_s` = seconds since the last input; `bar_lag` = now − (newest closed bar's open + 5 min). States: LIVE (GoCharting: a POST within 60 s and `bar_lag` < 6 min; Upstox book: a frame within 30 s; chain: a snapshot within 30 s), STALE (up to 90 s / 60 s / 60 s), DEAD beyond that, inside the session only. A transition is one event with `since`; it is never re-derived from silence twice.
- **Inputs.** TapeMap's own receive times ([M]: `_SENSES["tape"][idx]["at"]`, `coverage.book`, the chain poller). New from the extension: a heartbeat in every POST — `hb: {tab_visible, ctx_alive, last_tick_ms, noSide}` — so "tab hidden but alive" and "context gone" are distinguishable from "discarded".
- **Output.** English: "GoCharting tape dead since 12:26 (74 min). Open the GoCharting tab; if the panel says 'extension context gone', press F5." Chip: **GC BAND since 12:26 — tab kholo / F5**. For Upstox: **UPSTOX BAND since hh:mm — server dekho**. For the chain: **CHAIN BAND**. When GC returns: "GoCharting back 16:08; 12:26–16:08 backfilled from snapshot bars" / **GC WAPAS 16:08 · beech ka backfill**.
- **What it does to other reads.** Every read that needs GoCharting (ladder edges, blocks, stacks, P/A/E/C, walls, GC delta, GC CVD) goes to CAN'T CHECK: "GC band since 12:26" — never a stale mark shown as live. Leg reads continue on the Upstox tape alone with the chip **EK HI TAPE (Upstox [I])**. On return, the reader appends *backfilled* reads (id suffix `.b`) for the gap; backfilled marks are drawn hollow; the live reads of the gap are not rewritten.
- **Where it shows.** A full-width band at the top of the GoCharting overlay, the panel, the Trade tab, the DESK and the float, the same text everywhere, plus one soft chime on the DEAD transition from the DESK (the extension cannot chime when it is the thing that died). Decision taken as the trader: one chime, once per transition. The chip is loud by being the only element with a dark background (§5).
- **Prevention on her side, marked as her settings, not ours:** Chrome → Settings → Performance → Memory Saver → "Always keep these sites active" → add `gocharting.com`; keep the GoCharting tab in its own window; never reload the extension during the session (an orphaned content script cannot post; after any reload, F5 the tab).
- **Rubric:** H3, H5, H8. **Tag:** [M]. **Hole:** the read is itself the hole record; 29 Sep would have shown it at 12:27:30.

### 2.1 LEG (the unit of reading) — R1

- **Definition.** Directional change on 1-minute closes [M]. State (dir, extreme). An up-leg ends when a 1-minute close ≤ extreme − δ; the leg's end is the minute of the extreme, its confirmation is the minute of that close; the next leg starts at the extreme. Symmetric for down. Extremes are 1-minute highs/lows. Before the first reversal the direction is "opening, not yet cut". A leg is *complete* at confirmation and frozen; the leg since the last extreme is *forming* and mutable.
- **Inputs.** Upstox book → 1-minute OHLC (the same price for all three indices); minutes before the recorder started or after a restart: Upstox REST intraday 1-minute candles (exact price/vol/OI, no side). GoCharting 5-minute bars are attached to a leg by their close time (a bar closing after the extreme minute belongs to the next leg; the straddle is stated in the leg's `bars` field). δ frozen at the open from `tape_log.prior_pool`.
- **Self-calibration.** δ = 2 × B5 from the pool; not from today (a moving δ would recut the day = repaint).
- **Lookback.** The session; nothing before 09:15 is spliced across a roll.
- **Output.** "UP leg from 22600 (11:06) to 22765 (12:01), 55 min, 11 bars, +165" / chip **UP LEG 11:06→12:01 · +165**. Forming: "forming UP since 22642 (13:40), +55, now −18 off the extreme (δ 35)" / **BAN RAHA · +55 · −18 wapas**.
- **Rubric:** R1, R14 (frozen), R15 (the context every single-bar mark is subordinate to). **Tag:** [M]. **Hole:** minutes with no price from any source are listed as holes in the leg (`holes: [...]`); a leg spanning a hole says so; a hole cannot create or end a leg.

### 2.2 EFFORT vs RESULT per leg — R2

- **Definition.** For a leg with attached bars: `net` = Σ bar delta (GC when the bar is live and complete, else Upstox), `net_x` = the same excluding block bars (§2.9), `vol` = Σ lots (the larger of GC and Upstox per bar), `pts` = extreme − start extreme. Efficiency (Kyle-style) `eff = dir·pts ÷ (dir·net_x ÷ 1000)` in points per 1,000 lots of net flow in the leg's direction; Amihud `ami = |pts| ÷ (vol ÷ 1000)`. If `sign(net_x) ≠ dir` the leg is **flow against price** and `eff` is not ranked (§2.3).
- **Self-calibration.** Rank of `eff` among today's completed legs with the same sign (k of n), and its percentile in the prior-five-session leg pool (29 Sep pool: n = 25, p25 94, median 127, p75 256 pts/1,000 lots [M]). Warm-up: until n = 3 the today-rank prints "warming, k of 3" and only the pool percentile speaks.
- **Lookback.** The leg.
- **Output.** "+3,177 lots net buying for +165 pts: 52 per 1,000, least efficient of 3 today (pool p4)" / chip **52 / 1k · 1 of 3 · heavy buying, kam chala**. When `eff` is below the pool's p25 the words "heavy buying, little progress" are added in English and **zyada kharid, kam chala** in the chip.
- **Rubric:** R2, R13. **Tag:** pts and vol [M]; net and eff [I] (side is inferred). **Hole:** a leg with any bar from one tape only carries **EK HI TAPE**; a leg with a bar missing from both tapes carries "n bars missing" and its sums are marked partial.

### 2.3 WHO ACTED — delta × OI × price per leg — R3

- **Definition.** Three signs per completed leg: `dir` (price), `sign(net_x)` (aggressor), and `oi_state` from ΔOI = OI(extreme minute) − OI(start minute) in lots (÷65), against a noise floor `2·σ·√(minutes/5)`, where σ = median |ΔOI| per 5-minute bar (pool until 12 bars today, then today's own). States:

| price | aggressor | OI | state | chip |
|---|---|---|---|---|
| up | buyers | up | new longs | **NAYE LONG** |
| up | buyers | down | short covering | **SHORT COVER** |
| down | sellers | up | new shorts | **NAYE SHORT** |
| down | sellers | down | long liquidation | **LONG NIKLE** |
| any | with price | flat | pressing, positions unchanged | **DABAV · OI same** |
| any | with price | as above, and `eff` < pool p25 | … **absorbed** (the fifth state) | **… ROKA GAYA** |
| any | against price | any | flow against price: passive-led move; no who-read | **ULTA FLOW** |

- **Inputs.** The leg (§2.1), its net (§2.2), OI from the Upstox book at minute cadence [M] (GoCharting bar OI as the check: equal on 70/74 bars on 29 Sep).
- **Expiry rule (§1 D3).** In roll week the state gets " · roll week" and ΔOI is also given on Σ(near + next); on expiry day the near-month OI is "closing by construction" and the state is "short covering *into expiry*"; the positioning sentence reads the next month or says CAN'T CHECK.
- **Lookback.** The leg. **Self-calibration.** The OI noise floor and the eff rank above; no fixed lot count.
- **Output.** "Short covering into expiry, absorbed: +3,177 net buying [I], OI −2,190 lots [M], +165 pts; 52 per 1,000 (least efficient of 3). Not new buying. Positioning: Oct CAN'T CHECK (not recorded)." Chip: **SHORT COVER ROKA · OI −2.2k · Oct pata nahi**.
- **Rubric:** R3, R4 (the suffix), R18 (the OI row's WITH/AGAINST comes from this state). **Tag:** OI [M] snapshot-differenced; state [I]. **Hole:** no OI at either end → "OI CAN'T CHECK: no OI frame within 2 min of hh:mm" and the state is reported without OI (only "buyers pressing"/"sellers pressing").

### 2.4 EXPIRY / ROLL MODE — R4

- **Definition.** From instrument data (`upstox_instruments` expiry field; the ux row's `expiry`): days-to-expiry of the front future. Modes: NORMAL; ROLL WEEK (T−3..T−1); EXPIRY DAY (T). On EXPIRY DAY the session line reads "Sep expiry today; Sep OI goes to zero; positioning is read in Oct" from the open. Rollover % = Oct OI ÷ (Sep + Oct OI); rollover cost = (Oct − Sep) ÷ Sep; volume cross = the minute Oct 5-minute volume first exceeds Sep's (from then on Oct is the leg-engine price and Sep is "expiring").
- **Inputs (what must be added).** The next-month future: `futs[1]` from `resolve()` subscribed in `full` mode and recorded as `book_NIFTY-2_<day>` / `ux_NIFTY-2_<day>` (a contract dimension, not a splice); REST intraday 1-minute for Oct as the anytime-start backfill (price, vol, OI; no side). GoCharting: if `NIFTY-II` serves a footprint, a second chart posts with `contract` in the doc; `main.js:259` must stop collapsing the symbol to `NIFTY` (audit §4). The calendar never comes from a weekday.
- **Output.** "Sep expiry today. 13:30–15:35: Sep OI −11,277 lots [M], Oct: CAN'T CHECK (not recorded). Rollover %: CAN'T CHECK." Chip: **EXPIRY AAJ · Sep OI −11.3k · Oct pata nahi**. With Oct: "(a) Oct OI +9.8k with Oct delta −7k: shorts rolled" / **SHORT ROLL HUA** or "(b) Oct OI flat: shorts closed, squeeze fuel gone" / **SHORT BAND HUE**.
- **Rubric:** R4, H6. **Tag:** [M] for OI/volume; the (a)/(b) resolution [I]. **Hole:** Oct absent → CAN'T CHECK with the reason; never "0".

### 2.5 ABSORPTION AT A LEVEL — R5

- **Definition.** In the last 12 bars, a run of ≥ 3 consecutive bars whose highs lie within B5 of the window's high with closes below it (a ceiling), or the mirror at a floor. Aggressor = sign(Σ delta_x over the run). Read: ceiling + net buying → "buyers absorbed at L, k bars, N lots"; floor + net selling → "sellers absorbed"; ceiling + net selling → "sellers leaning on L (responsive)"; floor + net buying → "floor held, buyers lifting, sellers not pressing". Magnitude test: |Σ delta_x| ≥ (median |bar delta| today) × k, else the run is "quiet at L". Location test: L within one reader row of a leg extreme, a wall, a prior-day level, an OI strike or inside her zone; elsewhere the run is recorded but not drawn.
- **Book witness (D1).** If `senses` shows the touch at L restored ≥ 3 times during the run, append "offer refilled 3× [I]".
- **Output.** "Buyers absorbed at 22718: 3 bars 13:00–13:10, +519 lots net [I] (median bar × 3 = 471); no acceptance above; inside the 12:57 leg extreme" / chip **ROK 22718 · buyers · 3 bars · +519**. Never "reversal".
- **Rubric:** R5, R9 (stacks inside the run are listed as evidence: "3 stacked buy imbalances at 22712–22715"). **Tag:** [I]. **Hole:** a run containing a short GC bar uses the Upstox bar for that bin and says so; with GC dead, the run is read from Upstox only and the chip carries **EK HI TAPE**.

### 2.6 CVD DIVERGENCE AT EXTREMES ONLY — R6

- **Definition.** Only when a leg completes and its extreme is a higher high (or lower low) than the previous same-direction leg's extreme: compare day-anchored CVD at the two extreme minutes, on each tape separately. Bearish: HH with lower CVD; bullish: LL with higher CVD. No scan across the session; no bar-to-bar comparison.
- **Output.** "12:01 high 22765 vs 22640: no divergence (GC 7,638 > 4,519; UX 6,374 > 3,308)"; "15:22 low 22616 vs 22654: bullish divergence on Upstox (CVD 15,229 > 10,148); GoCharting CAN'T CHECK (dead)". Chip: **DIV nahi** / **BULL DIV · UX · 15:22**.
- **Rubric:** R6, R16. **Tag:** [I]. **Hole:** a tape with a missing bar between the two extremes reports "CVD broken by a hole at hh:mm" for that tape.

### 2.7 AUCTION AT THE EXTREME — R7

- **Definition.** At a completed leg's extreme bar (the 5-minute bar containing the extreme minute), re-bin the tick ladder to the reader row R. High: `finished` iff buy-at-ask lots at the top row = 0 (nobody lifted at the top); otherwise unfinished (buyers still lifting at the top; the level tends to be revisited). Low: finished iff sell-at-bid lots at the bottom row = 0. Tail = rows from the extreme whose lots are < 25 % of the bar's POC row; tail 0 = poor extreme. Single prints = rows with one trade inside the leg's range, carried as levels until traded through.
- **Output.** "12:05 high 22764: unfinished (b 93, s 0 at the top row); tail 4 rows. Carried as a level, contract Sep (expires today)" / chip **ADHOORA HIGH 22764 · Sep**.
- **Rubric:** R7, H6. **Tag:** lots [M], side [I]. **Hole:** the extreme bar short or from Upstox → CAN'T CHECK: "no GoCharting ladder for hh:mm".

### 2.8 TWO TAPES — R16

- **Definition.** Per leg: `net_gc_x` and `net_ux_x` (Upstox rebuilt from the book with the rupee tick, the audit's §3f fix; never the recorded paise ladder). AGREE if same sign and both beyond the median |bar delta|; DISPUTED if opposite signs; THIN if either is inside the median; ONE TAPE if a tape is dead or the index has no GoCharting (BANKNIFTY, SENSEX). Per bar, the sign disagreement hatches any mark on that bar.
- **Output.** "Both tapes: net buying (GC +3,177, UX +2,963)" / **DONO SAHMAT**; "Disputed: GC +661, UX −632 ex-block" / **DO TAPE ALAG**; **EK HI TAPE**. A disputed leg drops its who-read to "NO READ: tapes disagree" (H7).
- **Rubric:** R16, H2. **Tag:** [I]. **Hole:** as ONE TAPE.

### 2.9 BLOCK PRINTS

- **Definition.** A bar with one price holding ≥ 50 % of its lots and the bar ≥ 3 × the median bar (pool median until 12 bars). The block is excluded from `net_x`, stacks, absorption and marks; it gets its own mark. OI step check: if OI within 10 minutes of the block moves by more than the block's lots and then reverses, the block reads "spread/roll or reporting artefact, not directional [I]".
- **Output.** "10:05: 4,528 lots at 22598.8 in one print, 70 % of the bar [M]; OI +4,576 then −5,177 lots within 10 min: not directional" / chip **BLOCK 4.5k · 22599 · direction nahi**. 15:00: "2,030 lots at 22684 in 3 prints, 59 %".
- **Rubric:** R2/R3 integrity, R15. **Tag:** lots and price [M], side [I]. **Hole:** with GC dead the block is seen on Upstox only (15:00: 1,995 lots at 22684.9, `ltq` 1) → **EK HI TAPE**.

### 2.10 VALUE CONTEXT (initiative/responsive) — R8, and PROFILE SHAPE — R10

- Value area = 70 % of ladder lots around the POC at row R, today developing and prior session's (same contract; on the first day of a new contract the prior value is CAN'T CHECK: "prior session on Sep"). A leg outside prior value moving away = initiative; toward = responsive; inside today's value = rotational.
- Shape of the current leg group (a box) and of the session: P if the POC sits in the upper third after a lift; b if in the lower third after a drop; else D; "double" if two POC rows > B5 apart hold ≥ 30 % each.
- **Output.** "Afternoon box 22616–22716: POC 22684 at 68 % of the range after the 12:33 lift: P-shape, short-covering signature, consistent with OI −11.3k" / **P-SHAPE · cover**. "Whole day below yesterday's value 22858–22970: initiative selling, responsive buying".
- **Tag:** [M] lots, [I] shape words. **Hole:** ladder missing → CAN'T CHECK.

### 2.11 OPTIONS CONFIRMATION — R11

- Per leg window: ΔOI at the 2 strikes above and below the leg's range (chain [M], 17 strikes); synthetic forward K + C − P at the ATM vs the future [I]; the expiring series labelled *expiring* and excluded from "positioning" on expiry day; the next series named when it is in the chain (today it is not: CAN'T CHECK).
- **Output.** "13:30→15:29: expiring series unwinding across strikes (22600 PE −224k lots, 22800 CE −120k); 22700 PE +45k added late; synthetic 22716 vs fut 22714 (gap +1.9, converged). Next week's series: CAN'T CHECK (chain holds one expiry)" / **EXPIRING · sab utar raha · agla hafta pata nahi**.

### 2.12 VPIN — R12

- The existing `vpin.py` fast line: percentile of today, mute for 10 buckets; caption "one-sidedness per unit of volume; not direction"; on expiry: "roll and unwind buckets inflate it". Chip: **VPIN 78 % · shadow**. Never flips a read.

### 2.13 STACKED IMBALANCES — R9

- `prints.py` stacks (3:1, ≥ 5 lots, run ≥ 3) at the reader row, listed as evidence inside the leg sentence ("initiative buying 22712–22715") and inside absorption runs. Never a standalone mark.

### 2.14 DAY STRUCTURE — R17

- The list of completed legs + the forming leg + the value context, in one sentence that appends (never rewrites): "09:17–09:38 long liquidation −153; base 22590–22640 disputed flow with a 4.5k block; 11:06–12:01 short covering +165, least efficient; 12:01–12:33 long liquidation −132; from 12:33 a box 22616–22723, buying absorbed, Sep OI −11.3k into expiry; Oct: not recorded."

### 2.15 HER POSITION FRAME — R18 (what the FLOW row receives)

- Given her marked trade (instrument, side, entry time/price), each factor is WITH/AGAINST with its evidence sentence: **flow** = the forming leg's aggressor vs her side, updated per minute (never per candle close); **OI** = the leg's who-state vs her side (covering ≠ new longs); **zone** = fold's; **VPIN** = the gauge. "Somebody gave up" is named the minute the *other* side's leg fails: a forming leg against her that reverses without reaching δ, or an absorption run against her that breaks (acceptance beyond L by one row). "Pullback" = a retrace inside her leg smaller than δ with no absorption run against her: "pullback −18 of δ 35, no seller run" / **PULLBACK · −18 · seller nahi aaye**.
- **Output for the rubric's hypothetical long CE at 13:45 (29 Sep):** flow WITH (forming UP from 22642, +706 net [I], one tape); OI AGAINST (short covering, OI −584 lots [M], not new longs; into expiry); zone: under the 22718–22723 ceiling where buyers were absorbed 13:00–13:10; VPIN 28 % shadow. Never "confirmed".

---

## 3. What happens to every current detector

| Detector (audit §A) | Decision | What changes |
|---|---|---|
| Zone machine (`band_rotation`) | **Keep, untouched** | Order-flow words are annotations beside it. Its silence at both extremes (window `visit.py:50`, fade gate) is put in front of her as evidence; not changed here. |
| P trap (`board.js:94`) | **Keep the letter; move the computation to TapeMap; add negation; demote inside a box** | Computed at the reader row R (never the chart's rowSize) → a zoom can no longer rebuild the day. Record once with id `P:t:row`. Negated ("released", greyed, kept) when price trades one row back through the trapped side's level. Inside a box (forming leg range < 2δ) a P is recorded, not drawn (R15). 29 Sep: the four base Ps become records, not marks. |
| A absorption, cluster and effort forms (`board.js:77-89`) | **Keep both forms under one letter, form carried in the event; block-screened; drawn only at a level** | The letter is placed by §2.5's location test. A bar that is a block (§2.9) gets a block mark, not an A. The 15:00/15:10/15:15 As survive as "effort form"; 10:05 becomes BLOCK. |
| E exhaustion (`board.js:103`) | **Keep; allow re-fire; self-calibrate; merge tm exhaustion as E2** | `!fired` removed: a later lower-effort new extreme in the same leg fires again (the 09:35 low gets its E). The 100-lot floor becomes a rank (top half of today's bar |delta|, pool during warm-up). E2 = the leg engine's "flow against price at a new extreme" (the tm 11:05 tell), labelled E2. |
| C climax (`board.js:92`) | **Keep; self-calibrate the 3×** | Rank: top decile of today's volume (pool during warm-up). 15:20 keeps its C. |
| Initiative (`board.js:82`) | **Keep as evidence, never drawn** | Feeds the leg sentence ("initiative buying at …") and the signals event vote as today. |
| Vacuum | **Retire** | Consumed by nothing; wrong at 09:35. |
| Walls B/S (`board.js:128`) | **Keep; computed in TapeMap at fixed 5-pt bins; lean count on the chip** | The best base read of the day stays; "B 22600 · 7 leans". |
| Defended/trapped levels | **Keep** as the placement source for A/E/P. |
| Nodes HVN/LVN | Keep in `prints.nodes`; not drawn. |
| Band taps and rings | Keep (the zone's neighbourhood). |
| Flow since a tap (`main.js:192`) | **Retire** (unshown since rev 6). |
| Prior levels (`market.js:64`) | **Retire** (dead, not contract-safe). |
| `decode.readBar`, `imbalances` | **Retire** (dead; `prints.py` is the live port). |
| tm absorption, tm climax (`prints.py`) | **Retire** (duplicates on the same bars). |
| tm exhaustion | **Merge** into E2 (above). |
| GC CVD (`prints.with_cvd`) | **Keep**; the only divergence rule is §2.6, on both tapes. |
| Frame tape block (newest 4 events) | **Replace** by the full mark record with ids and states. |
| Session aggressor (`frame.py:377`) | **Retire** (one block decided a day). |
| Zone + flow `fire` (3 rows) | **Keep, measure in points**: tolerance = B5/2 (≈ 9 pts on 29 Sep) instead of 3 chart rows (30 pts at rowSize 10). One line in the amendment she signs (audit D.10). |
| Signals ballot and sound | Unchanged except the 3-row tolerance above; the window and fade gate are hers. |
| Family agreement (`ux_gate`) | **Surface** as §2.8 per leg and per-bar hatching; fold's dispute checks the bar the fight is in (`fold.py:438`). |
| Contract match (`fit.js`) | **Keep; extend** with the next-month identity and `contract` in the POST. |
| fold flat FLOW row | **Fed by §2.15** (the forming leg's aggressor vs her side, with the leg sentence); no longer one fight. |
| fold fights / trapped / released | **Keep for her marked trade** (rev 6, signed). Out of this design's scope: the trap/release churn, ZONE hysteresis, GAVE UP freeze (audit D.6) — owed separately. |
| grounds CVD rank | **Retire** (the flow-rank bug's home); replaced by the leg rank. |
| grounds CVD divergence | **Merge** into §2.6. |
| grounds futures-OI quadrant (7-day blind) | **Replace** by §2.3 with the roll-week rule. |
| grounds FLOW (runs, `runs.py`) | **Keep** as evidence chips inside the leg ("prints of size: 5 buy runs [I]"). |
| board.py aggression / agreement | **Fed** by the leg read; unchanged consumers. |
| grounded calls (`/api/calls`) | Unchanged consumer of the new facts. |
| VPIN | Keep (§2.12). |
| sweeps (`sweep.py`) | Keep (depth vote). |
| `absorption.py` | **Give it its one face**: the "offer refilled k×" witness in §2.5. |
| `impact.py` (Kyle λ per minute) | **Merge**: §2.2 is λ at leg scale; park the per-minute one. |
| engine.py option events | **Rename on the face** with the prefix "OI " (audit D.9). |
| hold.py flow family | Retire with hold.py (outside this design). |

**Fix: zoom-recompute stability.** Root cause `main.js:247` (`P = new Map()` on rowSize change). The fix is structural: no detector runs in the extension; TapeMap computes at R and returns marks with ids; the extension draws the returned list and uses the chart's rowSize only to convert price to pixels. A reload or zoom redraws the same record. Parity gate before switch-over: the ported detectors replayed on the seven `ofd_marks` days must reproduce the posted events at the rows they were posted at (counts per kind per day; differences listed, not averaged).

**Fix: truncated bars.** Two layers. Extension: a bar whose tick stream died (no tick for > 20 s inside the bar while the tab is alive) is flagged `partial` so GoCharting's snapshot replaces it (`adapter.js:142`, `session.js:27`). TapeMap: every GoCharting bar is checked against the Upstox bin's lots ([M] from `vtt`); < 90 % → `short: [136, 943]`, excluded from marks, edges and stacks; the leg sums use the Upstox bar for that bin and the leg carries the chip. `tape_log.append` keeps first-writer-wins for the raw record but the reader's record stores the completeness verdict per bin. 29 Sep: 11:30, 11:35, 12:25 become `short` bars; the 12:25 E never exists.

---

## 4. Architecture

**Where each read is computed.** All of §2 in TapeMap, in one new module `reader.py` (pure: bars, book minutes, OI trace, chain, pool in; read objects out), called from the `/api/frame` handler after `tape_log.append` and from a 1-minute tick of the book (so the leg engine advances when GoCharting is dead). The extension computes nothing: it posts and draws.

**The wire.**

POST `/api/frame` (unchanged fields kept; added in bold): `{idx, interval: 5, session, closed: [bar…], forming: bar, `**`hb: {t, tab_visible, ctx_alive, last_tick_ms, noSide}, contract: {symbol, expiry|null}`**`}`. Each bar adds **`maxDelta, minDelta, buyTrades, sellTrades, partial`** (the exports already hold them; the tape file does not).

Reply (added to the existing `fr`): 
```
feed:   {gc:{state, since, stale_s, bar_lag_s, why, do}, ux:{…}, chain:{…}}
reader: {asof, delta_pts, row, pool:{days, n_legs, b5}, mode:{expiry, near, next, dte},
         legs:[{id, dir, t0, t1, p0, p1, pts, mins, bars, holes, net, net_x, net_ux_x, tapes, vol,
                doi, oi_state, oi_noise, eff, ami, rank:{k, n}, pool_pct, who, chip,
                edge:{p, b, s, finished, tail}, absorbed:[{L, side, bars, lots}], div:{gc, ux},
                value:{tag}, confirmed_at, state: complete|forming|backfilled}],
         blocks:[{t, p, lots, share, oi_step, chip}],
         marks:[{id, kind, form, side, t, p, at, state: live|released|backfilled, tape, hatched, chip}],
         walls:[…], sentence, day, position:{flow, oi, zone, vpin, gave_up, pullback}|null,
         flips:{legs, marks}, tag:{M:[…], I:[…]}}
```
`fold.flat.rows.flow` = `{chip, sentence}` taken from `reader.position.flow` (or, flat, from the forming leg).

**Record.** `data/reader/reader_<idx>_<day>.jsonl`: one row per read object at the time it is *created or changes state*, never rewritten; ids stable; a revision is a new row with `supersedes`. The DESK, Trade tab and float read the same objects through `/api/frame`.

**Anytime start (H8).** On start, the reader rebuilds from: the tape file (and the extension's first POST, which carries the whole day's `closed[]`), the book file for today (1-minute closes, OI), REST intraday 1-minute candles for minutes the book lacks (09:15–09:17 on every day; any restart gap) tagged `backfilled` with delta "not recorded", the chain file, the pool. δ, R and σ are read from `day_state` if the day already started them, else computed and stored. The guarantee: two engines fed the same day's inputs write byte-identical records except `asof`; a restarted engine cannot produce a read the uninterrupted one would not have, because every read is a function of inputs up to its `t` and frozen constants. Test: replay 29 Sep with a simulated stop at 11:00 and a restart at 11:20; diff the two records.

**No repaint (H5).** Complete legs and their numbers are frozen at confirmation (computed with that minute's σ and vref). The forming leg is the only mutable object and is drawn as such. Marks are never deleted; negation appends a state. Late GoCharting bars (a dead feed returning) produce `.b` rows and hollow marks; they never replace the live rows. The flip count is served.

**Feed death, end to end.** 12:26 silence → 12:27:30 DEAD event (server-side) → `feed.gc` in every reply → every face shows the band → GC-dependent reads CAN'T CHECK → the leg engine continues on the book tick → 16:08 the POST returns with 75 bars → backfilled rows for 12:25–15:25, band text changes to WAPAS → 17:00 the day record shows a 222-minute GC hole.

---

## 5. The face

**What is drawn, and how few.**

- **GoCharting overlay.** (1) The feed band, only when a tape is not LIVE. (2) One leg strip, top-left, one line: `UP 11:06→ · +165 · kharid +3.2k [I] · OI −2.2k [M] · SHORT COVER · 52/1k · 1 of 3 · DONO SAHMAT`. (3) Her letters at levels: P, A, E, C, as today; plus the block square. (4) Walls as thin lines with the chip `B 22600 · 7 leans`. (5) The unfinished-extreme tick at a completed leg's extreme (a short horizontal dash with `ADHOORA`). Nothing else: no zone shading (her order), no event strip, no fold glyphs (rev 6 already draws only the trade lines and ■ FOLD). On 29 Sep the design draws under a dozen objects for the day (two E, one A, two blocks, two unfinished-extreme dashes, the walls; the afternoon's letters are CAN'T CHECK with GC dead) against the audit's 57 posted events and 124 fold marks, which become records.
- **Panel (extension).** Order: feed line → her four chips (Z F O V, WITH/AGAINST/CAN'T CHECK) → the leg sentence → the expiry line → the last six marks with time, price and chip. The rev 6 fold/flat rendering stays; only the FLOW row's text source changes.
- **Trade tab (the playground).** On price: legs as thin brackets from start to extreme with one number chip each (`+165 · +3.2k · OI −2.2k`), the box outline when the forming leg has stayed inside 2δ for ≥ 6 bars, the marks. Nothing per bar.
- **DESK and float.** The feed line and the FLOW row (chip + one sentence). Nothing new.

**Marker grammar and sizes (pixels, never rows).** Letter 11 px semibold in a 14 px circle; C a 9 px diamond; block a 7 px filled square with `4.5k`; unfinished extreme a 12 px dash; walls 1 px lines. Placement: at the level, within one reader row. States: live = filled; released/negated = 40 % grey; backfilled = hollow with a 7 px `b`; disputed bar = 45° hatch. Size text from 12 px bar width up, as she decided.

**Colour language (light mode only).** Two hues plus grey: buyers **blue** `#1F5FBF`, sellers **vermilion** `#C8462B`, neutral/grey `#6B6B6B`, text `#1A1A1A`, background `#FFFFFF`, panel rule `#E3E3E3`. No green/red, no traffic lights, no gradients. The feed band is the one dark element: `#222222` with white text (loud by contrast, not by animation). CAN'T CHECK is grey italic. WITH/AGAINST chips take the hue of the side they favour; they are never green/red.

**Type and weights.** Inter (fallback: system UI), 12 px body, 11 px chips, tabular numbers everywhere (`font-variant-numeric: tabular-nums`), 600 for chips and letters, 400 for sentences, numbers never bold, no ALL CAPS except the four fold words and the chip words. Every number has its tag as a superscript `M`/`I` in 8 px grey.

**Density.** One sentence per leg; one line per feed; marks only at levels; a chip has at most four fields. If the leg sentence would exceed one line at 320 px, fields drop from the right (the tape agreement first, then the pool percentile).

**Chip vocabulary (Hinglish + number).** UP LEG / DOWN LEG · BAN RAHA (forming) · PULLBACK −18 · ULTA FLOW · DABAV (pressing) · ROKA GAYA (absorbed) · ROK 22718 (absorbed at) · PHANSA (trapped, P) · THAK GAYA (exhausted, E) · CLIMAX (C) · BLOCK 4.5k · NAYE LONG / NAYE SHORT / SHORT COVER / LONG NIKLE · ADHOORA HIGH/LOW (unfinished) · POORA (finished) · DONO SAHMAT / DO TAPE ALAG / EK HI TAPE · DIV nahi / BULL DIV / BEAR DIV · P-SHAPE / b-SHAPE · EXPIRY AAJ · ROLL HAFTA · Oct pata nahi · GC BAND since hh:mm — tab kholo / F5 · GC WAPAS · ABHI NAHI k of 3 (warming) · PATA NAHI: reason (CAN'T CHECK) · HAAR MANI (gave up) · VPIN 78 % shadow. Each chip carries its number; the English sentence carries the rest.

**Why it looks professional.** Few objects, each with one job; a fixed grid (chips 11 px, sentences 12 px, 8 px tag superscripts); numbers aligned; two hues that mean sides and nothing else; grey for everything uncertain; no colour for emphasis; the same band, the same words, on every face; nothing appears or disappears without a state (released/backfilled), so her screen changes only when the market does.

---

## 6. 29 Sep, as the reader would have read it (strict as-of)

Numbers from the replays: legs on 1-minute Upstox closes with δ 35.0 (B5 17.5 [M], pool 22–28 Sep); GoCharting bars live until 12:26, then the Upstox tape alone; the Upstox ladder rebuilt with the rupee tick; the Upstox record starts 09:17 (the 09:15 GoCharting bar: −794 lots, 22755.5→22695 [I]/[M]). Sides are [I] throughout; OI, points, lots [M].

**09:20** — Opening, not yet cut (no reversal yet). Bar 09:15: 2,702 lots, −794 net (GC) / −590 (UX, partial: record starts 09:17), from 22755 to 22695. Feed: GC LIVE, Upstox LIVE from 09:17:00 (band: "Upstox record from 09:17; 09:15–09:17 backfilled from REST, no side"). Rank: **ABHI NAHI 0 of 3**; pool yardstick only. VPIN: mute (4 of 10 buckets). Expiry line from the open: **EXPIRY AAJ · Sep OI zero hoga · Oct pata nahi**. Marks: none (the old E at 09:20 does not exist; the leg engine's first read of the drive is the leg itself). Sentence: "Opening drive down from 22761, sellers pressing, −794 net [I]; OI 135,316 lots at the 09:15 close [M] (the overnight change, −24.3k, is not a session read); no leg cut yet."

**09:35** — Forming DOWN 09:17→09:32, 22733.8→22625.5, −108 pts, net −982 (GC) / −1,339 (UX) **DONO SAHMAT**, OI −1,920 lots [down] → **LONG NIKLE** (long liquidation), 110 pts/1,000 (pool p40), VPIN 84 %. The 09:35 bar is still forming: its low 22580.5 is not yet a leg extreme. Her PE exit at 09:35:26 sees: flow WITH, OI WITH (liquidation), zone: d2 armed 09:27. No exhaustion read yet (nothing to compare: the leg's extreme is being made). Honest: the reader does not call the low at 09:35; it calls the *leg* at 09:41.

**09:41** (the first confirmation) — Leg 1 DOWN 09:17→09:38 complete: 22733.8→22580.5, −153 pts, 21 min, 4 bars, net −1,014 / −1,533 **DONO SAHMAT**, OI −3,369 lots [M] [down], **LONG NIKLE**, 151 pts/1,000 (pool p56; today "1 of 1, warming"). Edge at the low (09:35 bar, row 22580): b 0, s 14 → **ADHOORA LOW 22580 · Sep**, tail 9 rows. E fires at the low under the re-fire rule: the 09:35 bar made the leg's low on −25 net (GC) against the leg's strongest bar (−794) → "sellers did not press the low" [I]; the UX bar (−423) disagrees → the E is drawn **hatched** (DO TAPE ALAG on that bar). No E exists at 09:20 (that bar's effort ranks in the top half, not the bottom). The zone machine's BUY trigger at 09:39 stands beside it.

**10:10** — Legs: 1 DOWN (above); 2 UP 09:38→09:42 22580.5→22643.1 +63 on net −25 / −423: **ULTA FLOW** (price up on net selling: offers pulled, no who-read); forming DOWN 09:42→10:07, −48, net +754 (GC) / −414 (UX) ex-block: **DO TAPE ALAG → NO READ**. Block: **BLOCK 4.5k · 22599 · direction nahi** (10:05: 4,528 lots in one print, 70 % of the bar [M]; OI +4,576 then −5,177 lots within 10 minutes: not directional). No A at 10:05, no P at 10:05/10:10 (inside a box < 2δ, recorded not drawn). VPIN 98 % — the block, captioned so. Value: today's POC 22599, whole day below yesterday's value 22858–22970.

**11:10** — Legs complete: 3 DOWN 09:42→10:14 (−53, disputed, NO READ), 4 UP 10:14→10:58 22590→22640 +50, net +414 / +461 **DONO SAHMAT**, OI −2,886 [down] → **SHORT COVER**, 121 pts/1,000 (pool p40, today 1 of 1). Forming DOWN 10:58→11:06 22640→22600.3, −40 on net +89 / +103: **ULTA FLOW** — "new low 22600 on net buying: sellers did not come" (the tm 11:05 tell, now E2 at 22600, drawn: it is at the base floor). Runs in the last 12 bars: floor 22590, 9 bars, net +321 (< median × 9 = 828): "floor held, sellers not pressing, quiet"; ceiling 22640, 6 bars, net +240 (quiet). Walls: B 22600/22605 with 5–7 leans (kept from today's tool). Sentence: "Base 22590–22640 for 32 min; shorts covering (OI −2.9k [M]) while the floor holds; ceiling 22640 tested 6 bars." The 11:10 bar (+1,671 net, +65 pts) is then read as the forming UP leg at 11:15.

**12:05** — Forming UP 11:06→12:01: 22600.3→22764.9, **+165 pts, net +3,177 (GC) / +2,963 (UX) DONO SAHMAT, OI −2,190 lots [M] [down] → SHORT COVER, 52 pts/1,000 (pool p4; below both completed legs today, 121 and 151) → "heavy buying, little progress" / ZYADA KHARID, KAM CHALA.** (Frozen at 12:20 as "rank 1 of 3".) Not "buyers in control". Extreme bar 12:05 row 22764: b 93, s 0 → **ADHOORA HIGH 22764 · Sep**, tail 4. Divergence: none on either tape (CVD 7,638 > 4,519 GC; 6,374 > 3,308 UX) — **DIV nahi**; the "not bullish" comes from R2/R3. Ceiling run 12:00–12:15 (as of 12:20): 4 bars at 22764.5, net +19: quiet. Her u2 SELL trigger at 12:18 stands beside "short covering, least efficient, unfinished high". VPIN 50 %.

**12:30** — **Feed: GC STALE 12:27, DEAD 12:27:30 → the band on every face: "GoCharting bhej nahi raha since 12:26 — tab kholo / F5".** The 12:25 bin: GC 136 of 943 lots → `short`, replaced by the Upstox bar (−555 net [I]); no E at 12:25. Leg 5 UP 11:06→12:01 confirmed 12:20 (frozen as above). Forming DOWN 12:01→12:28: −85, net −332 / −489 agree, OI −1,373 [within the noise floor, ~1,480] → **DABAV · sellers · OI same**; the 12:30 bar (Upstox: 2,013 lots, −353 net) will complete it: leg DOWN 12:01→12:33, 22764.9→22633.0, −132, net −887 (GC to 12:20) / −1,044 (UX), OI −1,319 [down] → **LONG NIKLE**, 149 pts/1,000 (pool p56). Marks from here are **EK HI TAPE**: P/A/E/C are CAN'T CHECK (no ladder); the leg reads continue.

**14:00** — On the Upstox tape alone (band still up, 94 min). Legs since 12:33: UP 12:33→12:41 +84 on −217 (**ULTA FLOW**); DOWN −47 on +221 (ULTA); UP 12:46→12:57 +53 on +403, OI flat (**DABAV · buyers**); DOWN 12:57→13:40 22723→22642 −81 on **+2,120 net buying**: **ULTA FLOW — price fell 81 while buyers lifted 2.1k: supply stepping down over the buying**. Absorption runs: ceiling 22718, 3 bars 13:00–13:10, +519 (≥ 471) → **ROK 22718 · buyers · 3 bars** (drawn: at the 12:57 leg extreme); floor 22642, 3 bars 13:35–13:45, +1,106 → "floor held, buyers lifting". Forming UP 13:40→13:52 +55 on +706, OI −584 (flat vs noise) → DABAV, pullback −18 of δ 35, no seller run → **PULLBACK · −18 · seller nahi aaye**. Bullish divergence at the 13:40 low on UX (CVD 7,857 > 5,334) — **BULL DIV · UX**; GC CAN'T CHECK. Box: 22633–22723 since 12:33 (2δ not exceeded for 17 bars) → drawn as a box; Ps inside it are records only. R18 for a long CE from 13:45: flow WITH (one tape), OI AGAINST (covering, not new longs; into expiry; Oct pata nahi), zone: under ROK 22718, VPIN 28 % shadow. Sentence: "Box 22633–22723 since 12:33; buying absorbed (net +3.9k [I] 12:35–13:55 for +15 pts close-to-close, 22664 → 22679); Sep OI 120.8k → 120.3k lots [M]; expiry: read Oct — not recorded."

**15:00 → 15:40** —
- 15:00: leg UP 13:40→14:31 22642→22710 +68 on +1,538, OI −1,166 (flat vs noise 1,412 — the noise floor is high on expiry day; the fact is shown: "OI −1.2k, within noise") → DABAV, 44 pts/1,000 (least efficient today, pool p4). Forming DOWN 14:31→14:46 −41 on +329: ULTA. The 15:00 bar: **BLOCK 2.0k · 22685** (Upstox: 1,995 lots at 22684.9, `ltq` 1 [M]); with GC dead the A at 15:00 is CAN'T CHECK — the block mark stands instead. VPIN 56 %.
- 15:20: leg UP 15:02→15:10 22654→22714.8 +61 on +3,450 (ex-block +1,030), OI −2,567 [down] → **SHORT COVER**, 59 pts/1,000 (pool p8), confirmed 15:20. Since the extreme: 2 bars, +1,631 net, close 22688 = −27 off the high → **PULLBACK · −27 · thr 35**, still inside δ.
- 15:25: the 15:20 bar (low 22616) completes DOWN 15:10→15:22 22714.8→22616 −99 on **+1,631 net buying**: ULTA FLOW, OI −1,288 [down] — "price fell 99 on net buying: covering absorbed and pushed through" [I]. Bullish divergence at the 15:22 low on UX (15,229 > 10,148) — the C that today's tool drew at 15:20 is CAN'T CHECK (no ladder); the divergence and the leg say the same thing.
- 15:25–15:35: forming UP 15:22→15:30, 22616→22716, +100 on +78 net, **OI −4,283 lots in 8 minutes [M]** → SHORT COVER, 1,282 pts/1,000 (pool p96: a thin book at the close; captioned "closing book, expiry"). Ceiling 22716, 3 bars 15:25–15:35, +422 (quiet).
- **15:40, the day (R17):** "Morning: long liquidation −153 to 22580 (unfinished low); base with disputed flow and a 4.5k block; 11:06–12:01 short covering +165, least efficient leg of the day; 12:01–12:33 long liquidation −132. Afternoon: box 22616–22723 from 12:33, net +8,186 (UX) [I] for +40 pts close-to-close, 19 of 24 bars positive, Sep OI 120,790 → 110,029 lots (−10,761 [M], 13:30→15:29), P-shape (POC 22684 at 68 %): short covering into expiry, absorbed; not new buying; not bullish. Positioning moved to Oct: CAN'T CHECK (not recorded). Options: expiring series unwound across strikes; 22700 PE +45k late; synthetic 22716 vs fut 22714. Feed: GoCharting dead 12:26–16:08 (222 min); 12:25–15:25 backfilled at 16:08 (hollow). Two tapes agreed on every leg they both saw except 09:42–10:14 (disputed)."

What the reader does *not* say on 29 Sep: "buyers trapped" in the base; "buyers in control" on the +9k afternoon delta; an E at 09:20 or 12:25; "reversal" anywhere; a Sep OI direction without "into expiry"; anything about Oct except that it is not recorded.

---

## 7. Validation

**Descriptive replay protocol (no edge, no rates).** Days: Tier A 09-22, 09-23, 09-24, 09-25 (to 13:35), 09-28, 09-29; Tier B 09-11, 09-18, 09-21 (no Upstox check: GC holes unsized, ONE TAPE); Tier C exports 09-07/08/09/10/15/17 (with `maxDelta/minDelta`). For each day, run the reader strictly as-of at every minute, write the record, and check:
1. **Determinism** — two runs byte-identical except `asof`; a stop/restart at three random minutes reproduces the record (H8).
2. **Arithmetic integrity** — each leg's `net`, `vol`, `pts`, `doi` equal the sums recomputed from the raw bars and the book (a unit check per leg); every state word matches the sign table in §2.3 for its numbers; "absorbed" only where progress ≤ B5; "disputed" exactly where the two signs differ.
3. **Counts, per day** (n shown, never a rate): legs; marks drawn vs recorded; CAN'T CHECK minutes per tape; feed events; flips of the FLOW chip; backfilled rows.
4. **Truthfulness of description** — for each completed leg, the next leg's direction and size are appended as plain facts ("next: DOWN −132"); no scoring, no hit rate. The judge reads the pairs.
5. **Regime check** — on 09-23 (T−4, an ordinary day) the near-month OI states must be plain (no suffix) and the pool caveat absent; on 09-24, 09-25 and 09-28 (T−3..T−1) every state carries "roll week"; on 09-29 "into expiry". The calendar must come from the instrument dump's expiry field, not from a weekday; the test swaps the dump's date and expects the modes to follow it.
6. **The rubric's 29 Sep criteria** R1–R18, each pass/partial/fail with the line of the record that shows it.

**Shadow run from the next session.** The reader writes `data/reader/` from 09-30 with a 30-session clock; nothing it says reaches a WITH/AGAINST chip beyond what fold already shows until the clock runs, except the FLOW row text (replacing one-fight text with the leg sentence, which is a description, not a new rule). Pre-registered before it goes live: the geometry constants (§1), the state table (§2.3), the feed thresholds (§2.0), and the falsifiers below; she signs; the sha256 is anchored.

**Falsifiers (what would make each read wrong as a description).**
- LEG: a second replay cuts differently; or a leg's extreme is not the 1-minute extreme of its window.
- EFFORT/RESULT: a leg's rank changes after confirmation (repaint); or the pool percentile uses a day on another contract.
- WHO ACTED: the state word contradicts its own three signs; or an "absorbed" leg has progress > B5; or a Sep OI direction is printed on expiry day without the suffix. With Oct recorded: a "(a) rolled" call where Oct OI did not rise within noise, or "(b) closed" where it did.
- FEED-HEALTH: a DEAD state declared while a POST arrived within 60 s; or a live mark drawn from a bar posted after a DEAD transition without the `.b` state; or a stale mark on any face more than 90 s after silence began.
- ABSORPTION: a run drawn away from any level; the word "reversal" anywhere; a run counted across a `short` bar without the Upstox substitute.
- DIVERGENCE: a divergence reported between minutes that are not both leg extremes; or on one tape while the other is not stated.
- AUCTION EDGE: read from a `short` or Upstox bar; or a row size other than R.
- TWO TAPES: "agree" while a per-bar sign differed on the majority of the leg's bars; "one tape" not shown when GC was dead.
- BLOCK: a block bar's delta inside `net_x`; or an A drawn on a block bar.
- EXPIRY: the mode derived from a weekday; Sep and Oct spliced in one series.
- Kill condition for the whole reader (30 sessions): if on more than 5 sessions the record fails determinism or integrity, the FLOW row reverts to fold's text and the reader stays shadow.

---

## 8. Self-score

| Item | Score | Why |
|---|---|---|
| R1 leg segmentation | **pass** | 1-minute directional change, δ frozen; 29 Sep afternoon named as a box with sub-legs from 12:33; deterministic. |
| R2 effort vs result | **pass** | 52/1,000 at 12:05, "least efficient, pool p4", both yardsticks with n. |
| R3 delta × OI × price | **pass** (Sep); **partial** (resolution) | "Short covering into expiry, absorbed" with numbers; (a)/(b) needs Oct. |
| R4 expiry and roll | **partial** | Calendar from instrument data, the suffix, the CAN'T CHECK; Oct not recorded on 29 Sep, so rollover % and the Oct window fail *today* and pass once `futs[1]` is subscribed. |
| R5 absorption at a level | **pass** | ROK 22718, 3 bars, +519; "absorbed here", never "reversal". |
| R6 CVD divergence at structure | **pass** | None at 12:01 on either tape; bullish on UX at 13:40 and 15:22, GC CAN'T CHECK. |
| R7 auction completeness | **partial** | Finished/unfinished, tail, single prints on GC ladders (NIFTY only, side [I]); no TPO; not on the other indices. |
| R8 value context | **partial** | Value from ladder lots (GC [M] lots, side irrelevant); prior value on the same contract; BANKNIFTY/SENSEX from ux ladders [I]. |
| R9 stacks as evidence | **pass** | `prints.py` stacks, listed inside legs and runs; never a mark. |
| R10 profile shape | **partial** | P/b/D by POC position; descriptive only; 29 Sep afternoon P at 68 %. |
| R11 options confirmation | **partial** | Per-strike ΔOI and the synthetic forward; the expiring label; next week's series not in the chain. |
| R12 VPIN as regime | **pass** | Percentile of today, mute to 10 buckets, captioned, never flips a read. |
| R13 self-calibrated thresholds | **pass** | No lot count; warm-up explicit; geometry constants declared and frozen. |
| R14 persistence / one event = one mark | **pass** | Frozen legs, ids, states, flip count served; hatched not double-marked. |
| R15 sequence over single bars | **pass** | Zero standalone traps in the 13:30–15:30 box (P inside a box is a record). |
| R16 tape agreement | **pass** | Per leg and per bar; DISPUTED at 09:42–10:14; ONE TAPE from 12:26. |
| R17 day structure | **pass** | The 15:40 sentence in §6. |
| R18 position frame | **pass** | Flow/OI/zone/VPIN WITH/AGAINST per minute; gave-up and pullback named; never a candle close. |
| H1 no edge claims | **pass** | Counts with n; no rate anywhere. |
| H2 observed vs inferred | **pass** | Every side [I]; OI "snapshot-differenced"; tags travel with the number. |
| H3 holes visible | **pass** | FEED-HEALTH band; `short` bars; backfilled state. |
| H4 warm-up honesty | **pass** | "ABHI NAHI k of 3"; VPIN mute. |
| H5 as-of integrity | **pass** | Frozen at confirmation; `.b` rows; no overwrite. |
| H6 contract identity | **partial** | Every number names Sep/Oct; GoCharting's `ik` is null on the continuous symbol, so the contract is inferred from the Upstox `ik` and the OI match until the extension posts `contract`. |
| H7 "no read" | **pass** | NO READ on disputed legs and flow-against-price legs. |
| H8 anytime start | **pass** | REST 1-minute backfill for price/vol/OI; delta "not recorded" for those minutes; deterministic rebuild. |

**What our data can never reach (nobody should promise it):** the true aggressor (both tapes infer it; ~19–24 % mislabelling in the literature, 31 % bar-sign disagreement between our two tapes on 29 Sep); the time order of prints inside a GoCharting bar; icebergs and spoofing (no order-level data); OI per price; the Oct side of 29 Sep (never recorded); Upstox 15:30–15:40 since 09-24 (the recorder gate); the closing auction (cash stocks are not in the feed); a footprint for BANKNIFTY and SENSEX (Upstox-only, every side [I]).

**Three simplifications I chose on purpose (ponytail):** one leg engine for all reads instead of six absorption/trap/exhaustion definitions; two yardsticks (today, pool) instead of a time-of-day seasonality model that needs history the project has refused to trust; the feed band instead of a monitoring subsystem — one state machine, one sentence, one chime.

---

## Rev 2 (2026-09-29, after the cross-critique and the Oct 1-minute data) — appended, nothing above rewritten

**New evidence.** `data-2026-09-29\fut_SEP_1m.json` / `fut_OCT_1m.json` (385 bars each, 09:15–15:39, no side). Verified in `scratchpad\fable`: 13:30–15:29 Sep +46 pts / OI −10,761 lots, Oct +68 / +25,483, combined +14,722; day Sep −26,701, Oct +58,462, combined +31,761; spread Oct−Sep 111 → 178 (one-month carry ≈ 120); Oct out-traded Sep in 71 of 77 bins from 09:20; rollover Oct÷(Sep+Oct) 60.5 % → 70.9 %; 15:20 flush Sep −99 vs Oct −34 (spread 157 → 228 at 15:21); 10:08 Sep OI +4,651 and Oct OI +5,134 in the same minute, Sep −5,021 at 10:12.

### Changelog

1. **§2.3/§2.4 — expiry day reads two contracts.** From the first three consecutive 5-minute bins where the next month's volume exceeds the front's (29 Sep: 09:30), the *continuing* contract carries the positioning read (the OI table on Oct price × Oct OI, aggressor [I] from price until Oct delta exists) and the R18 OI factor; the expiring contract keeps the chart, the ladder reads and the marks, every number suffixed "expiring". The WHO row shows both: "Sep: short covering into expiry, absorbed under 22723 [tape]. Oct: new longs, +68 on OI +25.5k, spread 142 → 164 rich vs carry ≈ 120; combined OI +14.7k." The (a)/(b) resolution gains (c): **"carried forward on the long side: Sep shorts closed, Oct longs opened; positioning grew"** / chip **LONG AAGE GAYE · Oct OI +25.5k**. The 29 Sep afternoon sentence "not new buying; not bullish" is **withdrawn**: it described Sep and misdescribed the market.
2. **§2.1 — expiring-only move.** When the expiring contract's leg extreme exceeds the continuing contract's by more than δ/2 after the spread, the leg is tagged "Sep-only (settlement)" / **SIRF SEP · settlement**. 15:20: the C and the bullish divergence are Sep-only; Oct made no low.
3. **§2.9 — spread prints.** A block whose OI step is mirrored in the other month within two minutes reads "calendar spread print, not directional" / **SPREAD SAUDA**. Block = the print (GC ladder row), not the bar; Upstox blocks only when `V == ltq`, otherwise "burst".
4. **§2.7 — auction edge, corrected (I had it inverted).** Finished high ⇔ sold-at-bid = 0 at the top row; finished low ⇔ bought-at-ask = 0 at the bottom row; unfinished ⇔ both columns > 0; **one-sided** when the aggressor column alone printed (reported as its numbers, no auction word). 29 Sep: 09:35 low (buy 0 × sell 14) and 12:05 high (sell 0 × buy 93) are **POORA**; the 12:00 high (sell 3 × buy 137) is ADHOORA and was revisited at 12:05. §6 lines saying ADHOORA LOW 22580 / ADHOORA HIGH 22764 are superseded by this entry.
5. **§2.15 — FLOW words** become WITH / PULLBACK / AGAINST / SPLIT / CAN'T CHECK. PULLBACK = a leg against her with no named aggressor or λ below today's median, and her last with-leg's origin not traded through; AGAINST when the origin breaks or her side is absorbed for ≥ 3 visits; SPLIT when the tapes disagree in sign. The price-side "somebody gave up" is the counter-pivot break (29 Sep 12:30: 22676) / **HAAR MANI · 22676 toota**.
6. **§2.1 — RANGE / BREAKOUT** on top of legs: RANGE declared when both sides fail to extend by δ/2, band frozen at declaration, widenings appended; BREAKOUT when price trades beyond an edge by δ. P inside a RANGE is recorded, drawn grey, no chip. (No PAUSE state.)
7. **§2.0 — feed health.** Added the forming-bar stall check (open bin's GC lots < 80 % of Upstox lots and the bin ≥ 60 s old → **GC TICKS RUKE**); `bar_lag` (a closed bar not posted within 90 s of its close) is the DEAD guard; the 60/90 s silence thresholds are to be measured against a hidden GoCharting tab before signing, because Chrome throttles hidden tabs' timers. Short bars get the repair/rev flow (TapeMap replies `repair`, the extension re-posts the snapshot with `rev`), with the frame door's origin check on every rev.
8. **§2.4 — rollover line** from the open on expiry day: "Oct ÷ (Sep+Oct) 60.5 % · spread 111 vs carry ≈ 120" updating; Nov added when the chain of futures is captured.
9. **§5 — face.** Δ-prefixed inferred numbers plus one legend line replace the per-number superscripts; a leg table (one row per leg: time, pts, min, GC Δ, UX Δ, tapes, OI, pts/1k, who) sits under the Trade chart; walls stay on the overlay with the lean label; the same-print rule (no print is both A and P); "with GC alive" numbers are shown beside as-lived numbers in the record, never on the live face.
10. **§2.2 — earliest comparison** is pairwise vs the last same-way leg (from the second such leg), ahead of the rank and the pool percentile.
11. **§8 — self-score revised.** R3 on 29 Sep: **partial as written** (Sep described, market misdescribed; pass with item 1 and Oct captured). R7: **fail as written**, pass after item 4. R4: partial unchanged (Oct still unrecorded live; the after-the-fact pull proves the REST path works). Everything else unchanged.

### 29 Sep, corrected afternoon (with Oct)

"Box 22633–22723 on Sep from 12:33; Sep buying absorbed (net +8.2k UX [I], +40 close-to-close), Sep OI −10.8k 13:30→15:29 [M]: short covering into expiry. Oct: +68 on OI +25.5k [M], spread rich (142 → 164; carry ≈ 120): new longs in the continuing contract; combined OI +14.7k; rollover 66.5 % → 70.7 %. Positioning rolled forward on the long side and grew. 15:20: Sep-only settlement flush (Oct −34). 10:07:42: calendar spread print. GoCharting dead 12:26–16:08; Sep tape reads from Upstox alone until the 16:08 backfill."
