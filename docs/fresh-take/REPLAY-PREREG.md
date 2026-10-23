# REPLAY-PREREG — FADE and RIDE replay, frozen before any outcome is computed

**Status: DRAFT, UNSIGNED.** Mary signs §8 (the bar) before anyone reads a number. No outcome (target/kill/points/P&L) has been computed for anything below. The only numbers computed so far are data checks and event *frequencies* (§1). `read.py` revision and `ladder.py` revision to be written here at freeze: `[sha ________]`. After signing, any change = a new dated pre-registration, never an edit.

## 1. What the data can resolve (measured today)
- **`ux` bars are 5-minute** (75 per day, 09:15–15:25; the 09:15 bar holds data only from ~09:17). Not 1-minute.
- **A 1-minute footprint IS possible.** `ladder.py` rebuilds a per-price ladder from consecutive book snapshots at any `interval_s`; `fold.py` already runs it at 60 s. Limits: snapshots arrive every ~0.8–0.9 s (p90 1.65 s); in 44–45% of frames with volume, Δvtt exceeds ltq, i.e. several trades share a frame. Volume is conserved (vtt exact); its **price placement inside a frame and its side are inferred [I]**. Fine for blocks and 1-minute delta; weak for adjacent-row imbalance tests.
- **Both misses are in our data.** `ux` ladder, NIFTY: 30 Sep 12:50 — one sell cell of 3,013 lots (≈196K units) at 22,905 = 89% of that bar's 3,369 lots; 29 Sep 10:05 — one buy cell of 4,499 lots (≈292K units) at 22,598.8 = 70% of the bar's 6,443. Session median cell is 3–4 lots. `ofd_marks` also logged both (as "absorption", 3,096 and 4,483 lots). So the miss is in the decision/display layer, not the data. Caveat: a single-cell block can be a cross, and its side is [I].
- **Big-print frequency.** Decoder BADA PRINT: 4 events on 5–8 Oct (NIFTY). My re-implementation of its E1 rule on `ux` cells gives a NIFTY median 4 per day (43 in 11 days); the two counts disagree and I have not resolved why. Either way it is too rare to be a *required* confirmer.
- **Stacked imbalance** (`prints.bar_flags`, row sizes 5/10/10 as I assumed): bars with a stack — NIFTY 85/827, BANKNIFTY 141/827, SENSEX 13/792. A frequency that moves 10× with row size is not a signal. **Unfinished auction:** 6/827, 7/827, 2/792 bars.
- **Sizing (descriptive, from earlier checks):** 117 first ±1σ touches inside an allowed side and 129 ±2σ episodes (54 not vetoed by the held read) over 33 index-days. Her trigger plus confirmers will cut these further; the sample was a falling market, so the up side will be thin. **Expect most per-side cells under 15 → INCONCLUSIVE.**

## 2. Placement table
Roles: DAY READ · LOCATION · ENTRY CONFIRM · FOLD · CUT (CUT = "on tap": shown on request, never gates). Resolution column: ✓ supported · ~ approximate · ✗.

| Concept | Role | Trader reason | Resolution |
|---|---|---|---|
| Volume (bar / 1-min) | CUT (feeds effort-vs-result only) | alone it has no side | ✓ vtt exact |
| Delta (1-min) | **ENTRY CONFIRM** (FADE #1, RIDE #1) | who is hitting *now*; timing, not direction | ~ 1-min via `ladder.py`; side [I]; my tick-rule vs `ux` 5-min delta correlated 0.75–0.93 |
| CVD (session cumulative) | CUT | drifts all day; only changes over 15–30 min mean anything | ✓ |
| CVD divergence (new extreme, no new CVD extreme) | **ENTRY CONFIRM** (FADE #2) · FOLD tell (RIDE) | "the move is not being paid for" | ~ 15 min on closed bars (`grounds.py`) |
| Big single-price print (E1) | LOCATION event · FOLD tell (against me) · size tag | a 3,000-lot cell is a level someone defended; rare, so it splits rows, never gates | ✓ cells, ~ side |
| Stacked imbalance | CUT | row-size dependent (above) | ✗ at 1-min / ~ at 5-min |
| Absorption (book) | FOLD tell (against me) · tag | proves the touch was refilled; does not say which side | ✓ ticks (side not given) |
| Sweep | CUT | duplicates delta; no setup needs it | ~ |
| Depth pull | CUT | makers stepping back ≈ what VPIN says; shadow-only today | ~ |
| Exhaustion / climax (extension marks) | CUT | same arithmetic as divergence + absorption | ✓ |
| Unfinished auction / naked POC | CUT | too rare (above) | ✓ |
| Prior-day POC/VAH/VAL | LOCATION | open-vs-value; targets/kills as ladder rows | ✓ (last *full* day) |
| HVN / LVN | LOCATION (ladder rows only) | magnets vs fast-travel; my profile code found no HVN on several days, so not a gate | ~ |
| Developing intraday profile | CUT | VWAP±σ already is her location; a second centre adds noise | ✓ |
| VPIN | FOLD (direction-blind; only with flow against) | expansion-risk, never an entry (`vpin.py`) | ~ percentile mute until ~09:56 |
| Futures OI × price | **ENTRY CONFIRM** (RIDE #2) · DAY READ context | new positions vs squaring off | ~ OI updates are batched |
| OI writers | **DAY READ** (the KHEL gate) | her trend/flip rule | ~ needs the window + residual fixes |
| OI dwell / walls | LOCATION · FOLD (the OI light) | OI read at levels, not in aggregate | ✓ ±8 strikes only |
| Writing-vs-buying residual | DAY READ input (data fix) | OI up does not say sold or bought | ✓ chain IV, ltp |
| Realized-vs-implied (moved ÷ priced) | PREMIUM call (buy vs sell) | cheap options → buy, rich → sell | ✓ (junk on the expiring contract) |
| Displacement / expected-move-to-date | DAY READ gate on TREND | a drift day is not a trend | ✓ |
| Basis (fut − spot) | LOCATION tag | one axis; she confuses spot and futures | ✓ measured live |

**Discipline kept.** FADE confirmers (2): first agreeing 1-minute delta; CVD divergence at the extreme. RIDE confirmers (2): agreeing 1-minute delta; futures OI × price showing new positions. Fold tells beyond zone/flow/OI/VPIN (2): big print / absorption against me near my level; CVD divergence against me. Big prints, absorption, stacks are **tags** that split reported rows; they never gate an entry.

## 3. Setups (futures, near-month, three indices)
**Common.** Bands = VWAP ±1/2/3σ from tick VWAP (matches her broker's within ~3 pts / ~1–4 pts of σ after 10:15). Decisions at **3-minute bar closes** (09:15 grid), using only data ≤ that close. Entries 09:48–14:30 only. **Time stop 15:00.** KHEL at the decision minute = THE READ held word: TREND → RIDE full, LEAN → RIDE half, RANGE → FADE, WAIT → BAITHO, with the data fixes (symmetric window, IV residual, displacement gate, fast-veto/slow-permit). Each row carries `khel_source` (read.py or the fresh-take fallback) — never mixed silently.

**Barriers are symmetric: one σ-zone to target, one to kill.** Reason: the null is then 50/50 and the bar can be written in rows. VWAP-target and ride-to-next-σ are *management* and are tested forward, not here. σ is the value at the decision bar, frozen.

**FADE** (signed trigger, `band_rotation._trigger` on index futures): BUY when the 3-min bar's low ≤ d3 (else d2) **and its close is back above the band it pierced**; SELL when the high ≥ u3 and the close is back below. (Her signed code sells only at u3; the u2 sell in the brief is **arm B**, reported separately, never pooled.) Armed only if KHEL ≠ RIDE-against. Confirmers: F1 first agreeing 1-minute delta within 3 minutes after the trigger close; F2 CVD at the extreme minute did not make a new 15-minute low (high for sells). Entry when both hold. Target = one σ toward VWAP; kill = one σ beyond the band (d3 trigger: d3 − 1σ).
**RIDE:** inside a held TREND/LEAN lane in direction d, the **first** minute z·d ≥ 1.0 after z·d was < 0.75; one per lane. HALF at the touch; second HALF at the first agreeing 1-minute delta (immediately if the preceding minute already agrees), else within 5 minutes or the first half is closed at market and the row is **PENDING-FAIL**. Confirmer R2: futures OI up ≥ 0.1% over 30 min with price moving in d (else UNCONFIRMED). Target = +1σ beyond the band (z·d = 2); kill = VWAP.
**What-if rows** (same barriers, labelled, never counted as entries): FADE triggers vetoed by KHEL; triggers failing F1/F2; RIDE failing R2; BAITHO minutes with a FADE trigger.

## 4. Fills and costs
Zero brokerage, no statutory charges. Entry = first frame **after** the decision, ltp plus 1 tick adverse. Target filled only if ltp trades **through** it by 1 tick (fills at the level). Kill and time stop fill at the first frame at/after the breach, ltp plus 1 tick adverse. Same frame touching both barriers = kill-first. 1 tick = the smallest positive ltp step seen that day (measured, expected 0.1 NIFTY). This is **pessimistic against her limit-order practice** (she posts and earns spread); the gap is not tested here.

## 5. PREMIUM arm (BUY vs SELL)
On every FADE/RIDE entry, same strike (`atm` at the entry snapshot), same entry and exit times, chain `ltp`: bullish → **Buy CE vs Sell PE**, bearish → **Buy PE vs Sell CE**. Per row: which expression gained more premium points. Reported twice: at `ltp`, and spread-adjusted (buys at ask, sells at bid, reversed on exit). Rows are bucketed by the moved ÷ priced gauge at entry: ≥0.8 (buy predicted), ≤0.5 (sell predicted), between (no call).

## 6. Output
One row file: `label` (IN-SAMPLE / HOLDOUT / FORWARD), idx, day, setup (FADE/FADE-B/RIDE), side, KHEL, size, confirmers, tags (big print / absorption / stack at the trigger), class ∈ {TARGET-FIRST, KILL-FIRST, NEITHER, PENDING-FAIL}, option arms. **Reports are counts only**: class × index × setup × KHEL × side; BUY>SELL / SELL>BUY by gauge bucket; distinct days. No rate, no mean, no sum of points. Points live in the row file for audit.

## 7. Holdout: the writers read (19 OI-only days, 20 Aug – 18 Sep)
Neither of us has looked at them. Coverage is uneven: ~8 days start by 09:21; the rest start 09:33–11:51; 20 Aug has 52 snapshots. Checkpoints 10:30, 11:30, 12:30, 13:30, only if the feed has run ≥ 30 min. Verdict = READ's WRITERS family after the fixes: A = (CE − PE) / (|CE| + |PE|) on the symmetric window (±4 strikes, shrunk to what both sides have), day build = OI now − OI at the previous close (`oi_chg`); a strike's build counts as **writing** only if its IV change since the feed's first snapshot is ≤ the ATM-wide IV change, else buying. One-sided (|A| ≥ 0.40): CE → bearish bias, PE → bullish. Outcome on **chain spot**: target/kill ±X with X = 0.3 × mean spot range of the previous ≤ 3 available sessions (≥ 1 needed), stop 15:00. One row per index-day per direction (first qualifying checkpoint). Report counts of TARGET-FIRST / KILL-FIRST / NEITHER by index, bias side; late-start days flagged PARTIAL. Same rules, no tuning.

## 8. Proposed pass bar (for Mary to sign) — in rows
- **Inconclusive:** fewer than **15** entries on a side. A cell passes only if **both** sides reach 15; otherwise the short side is INCONCLUSIVE and the pooled cell cannot pass.
- **Primary cells (only these may pass):** P1 FADE pooled; P2 RIDE pooled; P3 PREMIUM (the predicted-buy bucket); P4 the veto (vetoed FADE what-ifs); P5 writers (holdout). Everything else is descriptive.
- **Fair-coin table** (decisive rows = target-first + kill-first; minimum target-first so a fair coin would produce it ≤ 5% one-sided): 15→12 · 20→15 · 25→18 · 30→20 · 35→23 · 40→26 · 50→32 · 60→37 · 80→48.
- **PASS** needs all of: the table minimum; the same sign in each chronological half; still true after removing the best single day; entries on ≥ 10 distinct days. P3: BUY>SELL rows meet the table in the buy-predicted bucket (and SELL>BUY in the sell-predicted bucket, if it has ≥ 15). P4: the veto is *justified* if kill-first rows in vetoed what-ifs meet the table; it is *harmful* if target-first rows do.
- **FAIL:** ≥ 15 entries per side and kill-first ≥ target-first. Otherwise NO VERDICT.
- **IN-SAMPLE rows can FAIL a cell but never PASS one** (we tuned on them). PASS comes only from HOLDOUT (P5) or FORWARD rows.

## 9. What this replay can and cannot tell Mary
We tuned the day read, the fold lights and several constants on exactly these 12 full days, and the futures-based setups have no untouched futures days — the 19 older days have no futures at all. So the FADE/RIDE replay can only **kill** a rule: if it cannot beat a fair coin on its own tuning days with ≥ 15 entries a side, it is dead; if it clears the bar, that is a necessary condition, not evidence. It will also show what the sample can support (most cells will be too thin, and the sample was a falling market with almost no up-trends), whether the veto and the two confirmers look harmful, and whether BUY or SELL looks better by the cheap/rich gauge. Only the writers read gets a genuine test, on the 19-day holdout, and only on spot, on uneven coverage. Confirmation needs forward days, set before they happen.

## 9b. Opus review — amendments (2026-10-09, before any outcome was read)
- **A1 — FADE is already under a FORWARD test; don't redefine it.**
  - **Where it lives.** `context/research-findings.md` §5e (pre-registered 2026-08-08) collects her zone setup live in `data/trigger_log.jsonl`. Rule 3 defines it: d2→d3 buy, u2→u3 sell, on 3-min index-futures bands.
  - **What's on disk** (counted only, no outcomes read): `rule == "zone"`, 1,809 rows on 37 days (18 Aug – 8 Oct), 3 indices, BUY d2 1,026 / SELL u2 783, with 126 arm rows triggered. Separately, `rule == "5c"` has 154 arm rows triggered. Populations are never pooled (rule 5).
  - **Fade gate.** The gate verdict is on 542 rows (from ~23 Sep).
  - **What counts as the FADE result.** These FORWARD rows under §5e's adopted management: the 20-pt stop held to VWAP, then trail; flat 15:15. KHEL/fade gate (legal vs vetoed) is the P4 split.
  - **§3's futures re-implementation** becomes descriptive only.
  - **u2 sell.** It is primary, per rule 3 and the zone population. `band_rotation._trigger`'s u3-only sell is the OPTION-PREMIUM setup, a different instrument.
- **A2 — RIDE primary = the pullback touch of the 1σ band from the lane side.**
  - For a down lane: z rises back to ≥ −1.0 after being ≤ −1.25.
  - It re-arms only after a fresh 2σ excursion.
  - Her CSV: 9 of 9 −1σ touches on 8 Oct reached −2σ.
  - §3's "break into the lane" becomes arm R-B, descriptive.
- **A3 — confirmers and order-flow marks are SPLITS, never required.** That means 1-min delta, CVD divergence, big print, absorption and stack, so her signed rule is tested unchanged.
- **A4 — bar for FADE in the §8 row table.** The decisive classes are VWAP reached before the 20-pt stop vs the stop first. That gives §5e its owed bar in rows, once she signs.

## 10. Sign-off
Bar (§8) accepted / amended: ______________  Mary, date/time: ______________
FADE u2-sell arm B: keep reporting / drop: ______  Barrier width (1σ each way): accept / amend: ______
