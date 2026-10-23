# PRE-REGISTRATION DRAFT — VALIDATE 2 (rev 3 of the VALIDATE word; the board; the three in-trade reads)

**DRAFT, NOT SIGNED, before any code (Fable, 2026-10-06 evening).** For her signature, in her words ("sign" or an
amendment). Until signed and built nothing here shows live. The in-trade HOLD / PAST GIVE-UP / FOLD is fold.py rev 6
and is **not changed by anything below**.

What this registers, in three parts:
- **(A) THE WORD** — GO / WAIT / NO for a buyer **and** a writer, on ten counted checks (nine for a writer). It
  supersedes VALIDATE rev 2 (four facts, buyers only; `VALIDATE-PREREG.md`) **on the Validate tab only**; rev 2 keeps
  writing its own `check_<day>.jsonl` rows through `/api/hold/check` and its clock is not touched. It also carries
  EXPRESSION rev e §B's writer word into the same count (its four facts map to checks 1, 4, 9 and the printed CLOCK).
- **(B) THE BOARD** — eighteen candidates ranked lexicographically; the three named slots; "your trade is the best on
  the board" / "nothing clean".
- **(C) THE IN-TRADE READS** — ZONE ALONE, PULLBACK / GAVE UP, W-BLEED: printed beside the engine's word, logged every
  minute, never a verdict, each with a kill condition.

It gates nothing. It is never a size, never an order, never a percentage. A WAIT or a NO stops no entry.

---

## 1. The checks (A), their inputs and fixed parameters

Direction `d` = +1 when the trade wants the future up (long CE, short PE), else −1. `own` = +1 bought, −1 sold.
`B` = the engine's one-candle unit (`fold.State.B_at`, median 1-min range, pooled priors). Every check reads an object
that already exists; the cell says which.

| # | check | input | WITH | AGAINST | NEITHER (read) | could not check |
|---|---|---|---|---|---|---|
| 1 | RIGHT NOW | `fold_live.ask_ifin(k, ty, side)` headline | HOLD | FOLD, PAST GIVE-UP | — | CAN'T CHECK (its reason) |
| 2 | DAY / TREND | `daytype.read` (`_daytype_reply`): type, dir | TREND with d; PIN/CHOP for a writer | TREND against d | TWO-SIDED, EARLY; PIN for a buyer | daytype's own could-not-check |
| 3 | EXPRESSION | `expression` rows for d and for −d at the last 3-min close (`_expr_reply`) | word's role = her role; EITHER | word's role ≠ her role; or her way STAND ASIDE while −d has a directional word | STAND ASIDE both ways | no close yet |
| 4 | WALL BEHIND | W from ifin; its state from the **day-long** OI series: `fronts._state(chg, peak, slope)` over the chain grid since the open, SLOPE_MARKS = 15 | BUILDING | UNWINDING | STALLED | no W yet / grid stale (fronts.STALE_MIN = 3) |
| 5 | WALL AHEAD (buyer only) | A from ifin; state as #4; `A.pts` (fut) | UNWINDING | BUILDING and `pts ≤ 2 B` | STALLED; BUILDING farther than 2 B | no A yet |
| 6 | ORDER FLOW | ifin `rows.flow.chip` | WITH | AGAINST | QUIET | CAN'T CHECK (disputed fight / hole) |
| 7 | VPIN | ifin `rows.vpin.chip` | WITH | AGAINST | QUIET | < 10 buckets; a non-NIFTY index (no gauge) |
| 8 | CROSS-INDEX | the latest 30-min push on the index (`leg`, its extreme) vs the index's own prior swing (TOOK / FAILED), and the same for the other two within MATCH = 10 min (xindex's own numbers: FROM 30 min, MATCH 10) | leg = d and 3 of 3 TOOK; leg = −d and ≤ 1 TOOK | leg = d and ≤ 1 TOOK; leg = −d and 3 of 3 TOOK | exactly 2 TOOK | < 10 prints in the window / no prior swing |
| 9 | ROOM | G (fut) and A.pts from ifin, B | `d·(fut − G) > B` and (no A or `A.pts ≥ d·(fut − G)`) | `d·(fut − G) ≤ B` or `A.pts < d·(fut − G)` (a tie is WITH) | — | no G yet |
| 10 | PAYING | the payers' side (CE for d = +1, PE for d = −1): top-2 by session-peak OI inside `fronts.nine`, **beyond spot**; states as #4 | any UNWINDING | all BUILDING | otherwise | no front beyond spot |

Printed, never counted: MONEYNESS (delta, intrinsic, time value; "deep ITM" at |delta| ≥ 0.85 — chain_metrics' convention), SPREAD (ticks), CLOCK (DTE, expiry-day theta per 15 min [I], the 15:00 practice), WHO IS IN PAIN (ltp vs the day's avg at her strike and both walls; UNDERWATER at ltp ≥ 1.30 × avg = chain_metrics.UW_PREM, COMFORTABLE at ≤ 0.85), PCR(9) now / 09:30 / −60 min.

### 1.1 The word
- **NO**: #1 AGAINST, **or** ≥ 2 AGAINST among the six structural checks {#2, #3, #4, #5, #6, #8}.
- **GO**: #1 WITH, 0 AGAINST among the counted checks, ≤ 1 could-not-check, ≥ 6 WITH.
- **WAIT**: otherwise. It names each AGAINST as *what would have to change*; with none against, each NEITHER as *not there yet*.
- Shown: *{w} with · {a} against · {n} neither · {c} could not check — of {10 | 9}, a count, not odds.*

### 1.2 The levels (printed with every word, both frames)
invalid = G (fut) and G − basis_ix (spot), with its person (W's writers) and the interpolated premium there [I]; T1 = A (fut / spot) with its premium [I]; T2 = the payers' side second front beyond A, with its premium [I] and *only if {wall} comes off its peak* when BUILDING; reward vs invalidation as two numbers in fut points. A writer: keep-all level, breakeven (K ∓ p0, spot), invalid.

### 1.3 Parameters — inherited unless named

| item | value | from |
|---|---|---|
| the mark's engine | fold rev 6 as it stands (BK, B, w = B/2, CONFIRM 2, OI_Z 3, OI_NOISE_N 15, …) | `fold.THRESHOLDS` |
| wall state | fronts' BUILDING / STALLED / UNWINDING: UNWIND_FRAC 0.15 off its own peak with a falling slope; STALL_FRAC 0.05; SLOPE_MARKS 15 | `fronts.py` §1d |
| the nine | `fronts.NEAR` = 9 strikes nearest spot | §1d |
| wall-ahead reach | `A.pts ≤ 2 B` (the engine's own θ = 2 B) | fold `units.theta` |
| cross-index window / match | 30 min / 10 min | `xindex.SHEET` FROM, MATCH |
| deep ITM | |delta| ≥ 0.85 | **named choice** (chain_metrics uses 0.3 for the forward; 0.85 is the "futures in option's clothing" line) |
| pain | ltp / avg ≥ 1.30 under water, ≤ 0.85 comfortable | `chain_metrics.UW_PREM`; 0.85 **named** (its mirror) |
| GO | 0 against, ≤ 1 could-not-check, ≥ 6 with | rev 2's "none against, one allowed not-with" widened to ten checks: **named** (6 = more than half of ten, and of nine) |
| NO | FOLD at the door, or two structural families against | rev 2 rule 4; hold rev 4 rule 6 ("two families") |

No number is grid-searched. A change is a new revision with its own date.

---

## 2. The board (B)

- Candidates per index with a running engine: ATM BUY CE, ATM SELL PE, ATM BUY PE, ATM SELL CE, (ATM + 1 step) SELL PE, (ATM − 1 step) SELL CE. ATM = the chain's `atm`. 18 at most.
- Each candidate = one ifin read + the ten checks + the word.
- Rank key, lexicographic: (word GO < WAIT < NO, −WITH, AGAINST, could-not-check, `instruments.ENABLED` order, ATM before ITM).
- Slots: *same thesis, better expression* (her idx, her d, the other role, best by key); *opposite thesis* (her idx, −d, best); *other index* (best outside her idx). Plus the top three overall.
- *your trade is the best on the board*: no candidate's key is strictly smaller than hers.
- *nothing clean — stand aside*: the top of the board is NO, or WAIT with < 5 WITH. Then *it changes if* = the top candidate's AGAINST checks.
- The same table runs for MARKET READ's "best trade now" (no press trade: the top three and the slots are the whole answer).

---

## 3. The in-trade reads (C) — printed, logged, never a verdict

All three are computed every second from the engine's own state for the open marked trade and logged **once a minute**
to `data/validate2/intrade_<day>.jsonl` (new, write-once, key (trade_id, minute)). Each line shows its facts; the
engine's word stays above it.

### 3.1 ZONE ALONE
On when the engine's ZONE chip is WITH and neither FLOW nor OI is WITH, for ≥ CONFIRM = 2 bucket closes. Off when OI or
FLOW turns WITH, or on the engine's FOLD. Text: the three chips with their *since*, W's bleed line (§3.3), the engine's
out-if (G and the premium there), and the fixed sentence: *"on this row the record holds both: losers held here and
winners that ran from here — your call"*. It never changes a word.

### 3.2 PULLBACK / GAVE UP (her definition, 2026-10-06)
Printed only while the future is on the wrong side of her entry (`d·(fut − E) < 0`).
- **OFF** := the engine's OI event on W (z ≥ 3, n ≥ 3, ≥ 3 %) **or** W ≥ 10 % off its peak with ≥ 15 OI updates since the peak (§3.3), not yet REBUILT (no new W peak since OFF began).
- **PULLBACK · HOLD stands** := not OFF, and no fight won against her inside the last VPIN_WIN = 10 buckets (or the last one against her was ABSORBED).
- **GAVE UP** := OFF.
- **UNDECIDED** := not OFF, but a fight was won against her inside the last 10 buckets (flow pressing, wall holding).
Each prints the two facts (W's state and % off with its peak time; the last fight against her with its time) and the
line *"turns back to PULLBACK if W makes a new peak"* / *"turns to GAVE UP if W leaves or {G} is accepted"*.

### 3.3 W-BLEED gauge
*W {k} {ty}: peak {pk}L {t} → {oi}L (−{pct} %) over {min} min, {n} updates [M]*, every second; its chip turns amber at
≥ 10 % off (**named**, h) with ≥ 15 updates (OI_NOISE_N, inherited) and clears on a new peak. It is the input to §3.2's
OFF and a row in the ledger.

### 3.4 The ledger (KYA BADLA SINCE ENTRY)
Not a rule: a frozen entry snapshot diffed against now, each row tagged WITH / AGAINST / — by d. Rows: fut / spot, W
oi vs peak, the writers of her own strike (OI), A oi vs peak, PCR(9), CVD since entry [I], VWAP side, fights since
entry (by winner), VPIN pct, premium (now / peak / given back), zone (behind / at / broken), daytype word.

---

## 4. The record and the outcomes (forward only)

### 4.1 Press rows — `data/validate2/check_<day>.jsonl`, write-once
Key (idx, read second, k, ty, side, role). Fields: `rev: "3"`, `d`, `own`, the ten checks `[name, state, absence, text]`,
`word`, `counts {with, against, neither, cant}`, `levels {G, G_spot, T1, T2, prem_at_G, prem_at_T1}`, `board {top3,
slots, best_is_hers}`, `after_1500`, `pressed: true|false` (a board candidate written by a press is `pressed: false`).
Written only with `log=1` (the face), never by a test.

### 4.2 The unit and the outcome (inherits VALIDATE rev 2 §3 word for word, widened to writers)
- Unit: the first press per (idx, d, role) per 30 minutes.
- Outcome: first passage on the index's 1-min highs / lows over the 30 finished minutes after the press to the **static**
  invalid (G − basis_ix, spot) and the **static** T1 (A − basis_ix, spot): `target` / `stop` / `same minute` / `neither`;
  `short` after 14:59. A writer has no T1: her outcome is `stop` (invalid reached) or `kept` (not reached in 30 min).
- Stratum for judging: ROOM's WITH geometry (`d·(fut − G) > B` and `A.pts ≥ d·(fut − G)`), as rev 2 §4.

### 4.3 Predictions and falsifiers — counts described, never a rate
- **P1 (GO)**: inside the stratum, GO units reach `target` before `stop` more often relative to WAIT units: `GO(target) × WAIT(stop) > WAIT(target) × GO(stop)`. Judged at ≥ 15 resolved GO and ≥ 15 resolved WAIT units and ≥ 10 sessions; in any case at 30 sessions. **If it fails, or reverses with its best day removed, the word GO is deleted**; the ten checks stay as a printed checklist.
- **P2 (NO)**: inside the stratum, NO units reach `target` before `stop` less often than WAIT units (the mirror). Fail → NO withdrawn; the screen prints *"the engine reads FOLD at the door"* in its place and the check reads WAIT.
- **P3 (writers)**: GO writer units are `kept` more often, relative to `stop`, than WAIT writer units. Fail → the writer's word is deleted (she gets the nine checks and the levels).
- **P4 (the board)**: every press also logs the top-of-board candidate as its own unit (`pressed: false`, same outcome rule). The board stands if top-of-board GO units beat WAIT units as in P1. Fail → the ranking is deleted; the 18 candidates stay printed, unranked, each with its own word.
- **P5 (ZONE ALONE)**: minutes flagged ZONE ALONE end in the engine's FOLD within 30 min more often, relative to minutes with a plain HOLD and ≥ 2 chips WITH. Fail at 30 sessions → the line is deleted.
- **P6 (GAVE UP)**: GAVE UP minutes are followed by the engine's FOLD within 30 min more often than PULLBACK minutes. Fail → the read is deleted; the W-BLEED gauge stays a printed number (it claims nothing).
- Pooling: across indices, shown per index; the verdict must also hold with co-timed sets reduced to one unit (ENABLED order), as rev 2.
- The best day = the session whose removal moves the judged comparison most toward failing (rev 5 §F.2).

---

## 5. Disclosure — what was seen, and what moved

- **Rules v1** (the ten checks and the word) were written before any row was run. Then today's 10:03 (her 22650 PE) and 14:57 (the CE buy idea and the CE sale) rows were run.
- **Rules v2** changed four inputs **after seeing those two moments**, each for a stated defect, not for the answer:
  1. #4 / #5 read the **day-long** OI series, because the ifin watch starts at the mark and reads *building, 0 % off* for every wall by construction (seen on every v1 row).
  2. #8 judges the push against each index's **own prior swing** (xindex's TOOK / FAILED), because v1's "matched within 10 min" called three lower highs at 14:42 a confirmed push.
  3. #10 reads the payers' fronts **beyond spot** only, because on 0DTE the ITM 22700 CE's unwind at 14:50 is mechanical and v1 counted it as paying for an up move.
  4. #2 reads `daytype.read` rebuilt from the ux bars + the chain grid + the trap log (the side log's trend rows stand in on days without ux bars).
- Under v1 the 14:57 CE buy read WAIT 8-with and the CE sale NO; under v2 the buy reads NO and the sale WAIT (REPLAY.md §1). The direction of that change is the direction of the hand-written 14:57 read she liked, which was known when v2 was written. **That is in-sample, and is the reason the word carries DRAFT until §4.3 judges it on forward rows.**
- The past-trade rows (09-22, 09-24, 09-28, 10-05 ×2) were first run under v1 and re-run under v2; both are kept in `scratch/` (`out_*.txt`, `v2_*.txt`). No rule was changed after the past-trade rows were seen.
- Replay inputs that differ from the live server, stated: the prior-session pool is the five previous book files on disk (the live engine applies the contract filter), so BK and B can differ slightly; daytype in the replay has no sides slots and no peers; VPIN exists for NIFTY only; EXPRESSION and the side log do not exist before 09-25.
- Nothing here is a result. The 09-24 SENSEX winner reads NO at 10:19 under both v1 and v2 (REPLAY.md §2) and that row is kept, not explained away.

---

## 6. Signing

On her "sign": this file is finalised with her words in the header, hashed (sha256), anchored in
`context/research-findings.md` as §1i beside rev 2's hash, marked `-text`; the forward clock starts at the first
session after the code lands. Until then every word on the new tab carries **DRAFT**.
