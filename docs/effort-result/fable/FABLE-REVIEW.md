# FABLE REVIEW: EFFORT / RESULT (spec 2026-10-31) — 31 Oct 2026

Reviewer: Fable (clean-room; oi-lab AUDIT). Read-only. Scripts and raw outputs beside this file.
Every number: [M] measured here, [I] inferred. Counts only. In-sample, descriptive, never a rule.

## VERDICT: DROP the module. USE CHANGED = one log column, zero new words.

| Part of the spec | Verdict | One line why |
|---|---|---|
| §2 A quote rule beats tick vs Dext | REAL [M] | reproduced exactly; but `handshake.book_flow` already IS the quote rule. Only `vpin.py` uses tick |
| §2 B one bucket = noise | REAL [M] | honest null, reproduced |
| §2 C "lead your way at a stall → 0 of 19" | NOT a finding | carried by tape speed + pre-signal buckets; 8 market moments; reversed on leg pauses (9 of 20 went on) |
| §2 D the 77-touch checklist table | ARTEFACT | outcome measured on a MOVING band; fixed at the touch: TURN 55 → 28, BREAK 11 → 42 |
| §4 `effort_result.py` + 6 words + stamps + log | DROP | a second copy of flow, pause and speed the frame already has; no measurement survives |
| §5 checklist → LEVEL LEDGER families | MOSTLY EXISTS | see §7 below; BOOK family: drop |
| §6 DISCOVERY state | DROP | = daytype TREND / outside IB; its evidence is the §2 D artefact |
| §9 acceptance (replay must give 0 of 19) | WRONG TEST | proves the code equals the script, on 8 moments |

**What to do instead (smallest diff):**
1. `legs.py` pause log: add two fields per pause row: signed flow since the extreme (from the frame's `flow`, already
   quote-signed), and whether a new extreme followed. Evening-review column. No face, no word, no gate.
2. VPIN: judge the slow line on its OWN registered kill condition first. `data/vpin_log.jsonl` has **40 sessions** [M]
   (clock was 30). Nobody has scored it. Do not change its input until that is done.
3. The hold chip stays as registered. At a stall it reads tape speed, not absorption (below). Say so in its line if
   anything: "10 buckets = N min".

## 1. What I re-ran (the spec's own scripts, unchanged)

| Claim | Spec | My re-run | File |
|---|---|---|---|
| tick same-sign vs Dext | 3,098 of 3,671 · corr 0.71 | 3,098 of 3,671 · 0.71 [M] | repro_vpin_lab.txt, fable_check_out.txt §C |
| quote same-sign vs Dext | 3,347 of 3,671 · 0.83 | 3,347 of 3,671 · 0.83 [M]; at ≥ 50 % Dext delta: 1,322 vs 1,261 of 1,379 | same |
| quote rule's tick fallback | — | 18 % of book volume traded inside the previous spread → tick-signed [M] | §C |
| stall, live log | WITH 0 of 21 · AGAINST 17 of 25 | same [M] | repro_vpin_turns_live.txt |
| stall, quote buckets | 0 of 19 · 17 of 29 | same [M] | repro_vpin_turns_quote.txt |
| stall, tick buckets | — | 1 of 25 · 15 of 25 [M] | repro_vpin_turns_tick.txt |
| 77 touches | TURN 55 · BREAK 11 · WALK 11 | same, with the moving band [M] | repro_vpin_lab.txt |
| Dext-matched days | 19 | 19: 5 days skipped (no `ik` 22–28 Sep), 1 skipped (29 Sep = 68407, no Dext) [M] | §C |

The scripts compute what they say. The problems are in what they measure.

## 2. The stall split is mechanics, not absorption

120 stalls, 3 indices × 4 setup groups, all reading ONE NIFTY bucket stream, 8 days.

**a. The window reaches back before the entry.** 10 buckets at the stall, quote rule [M]:

| chip | n | went on | buckets closed signal→stall (median) | pre-signal buckets inside the 10 (median) | none pre-signal | ≥ 5 pre-signal |
|---|---|---|---|---|---|---|
| WITH | 19 | 0 | 14 | 0 | 15 | 0 |
| QUIET | 63 | 34 | 7 | 3 | 25 | 22 |
| AGAINST | 29 | 17 | 5 | 5 | 3 | 15 |

A fade sells into buying. At a stall 9 min after the signal (AGAINST's median), half the window is the push INTO
the band: against the trade by construction. "AGAINST = the other side absorbed" is "the window still holds the move
you faded".

**b. Drop the pre-signal buckets (read since the signal only, lead ≥ 2)** [M]:
WITH 1 of 19 · QUIET 51 of 91 · AGAINST **4 of 10**. The AGAINST half of the claim is gone.

**c. A sign-blind proxy splits the same way** [M]: buckets closed since the signal < 5 → went on 26 of 38; 5–9 → 17
of 39; ≥ 10 → 13 of 43. Fast tape since the entry = the move is spent. No sign needed.

**d. Inside the fast-tape stalls (≥ 10 buckets since the signal)** [M]: WITH 0 of 15 · QUIET 13 of 25 · AGAINST 0 of 3.
Something remains on the WITH side after the speed control. But:

**e. The 19 WITH stalls are ~8 market moments.** By (day, 5-min slot): 12. By eye (list in fable_check2_out.txt):
22 Oct 09:42/10:09/10:10; 27 Oct 10:26–10:27 (NIFTY ×2, BANKNIFTY, SENSEX = one moment); 27 Oct 12:49; 27 Oct
15:00; 28 Oct 13:26; 29 Oct 11:03–11:08 (×4 = one moment); 29 Oct 12:51; 30 Oct 10:22–10:25 (×2). **27 Oct (monthly
expiry; the book stayed on the expiring 48704, 4.84 M units of roll volume, OI 8.2 M → 6.5 M) supplies 8 of 19.**
26–27 Oct supply 26 of the 120 stalls. 0 of 8 moments is INCONCLUSIVE (house rule 4).

**f. It reverses on a different population.** First pause of every leg ≥ 40 pts, 25 NIFTY days, 79 pauses on 18
days, lead in the LEG's direction, quote buckets [M]:

| lead at the pause | n | went on ≥ 0.5σ | gave back ≥ 1U |
|---|---|---|---|
| WITH the leg | 20 | **9** | 15 |
| QUIET | 46 | 25 | 38 |
| AGAINST | 8 | 2 | 8 |

"BUYERS ABSORBED at a long's stall = exit" would have exited 9 of 20 continuations. INCONCLUSIVE, but it is not 0 of N.

**g. The stall is a pullback, not a flat tape.** 115 of 120 stalls pulled back ≥ 0.25U during the 6 minutes [M]. The
honest "effort vs result" is then: since the extreme, who hit and what did price do. Measured (quote, since the last
favourable extreme): your side ≥ +0.2 → went on 6 of 21; flat 36 of 73; other side 9 of 18 [M]. Nothing separates.

**h. Her exit habit.** Atlas §9 C: delta against at a stall went on 27 of 47 vs 16 of 35 with it. §10 then says the
opposite with the VPIN chip. Both are the same 8 days. Neither is an exit rule.

## 3. The 77-touch table is an outcome artefact

vpin_lab §3 calls TURN when price is back inside **the live 1σ at minute k** (`vwap[k]`, `sd[k]`). After a 2σ touch
σ grows and VWAP drifts toward price, so the 1σ line walks out to meet price. "Bands expanding → turn 16 of 20" is
the 1σ line moving, not price.

| yardstick | TURN | BREAK | WALK | before 10:15 turn |
|---|---|---|---|---|
| spec (moving band) | 55 | 11 | 11 | 20 of 22 |
| band fixed at the touch (same 1σ / 3σ) | 28 | 42 | 7 | 9 of 22 |
| ±1σ from the touch PRICE | 42 | 29 | 6 | 15 of 22 |
| the spec's FIRST definition (0.5σ further = BREAK) | 29 | 44 | 4 | 10 of 22 |

23 of the 55 "TURN"s had gone ≥ 3σ (touch-time σ) further first [M]. Under the fixed yardsticks every item in §2 D
flips or flattens: big limits 11 / 13 (fixed band) vs 17 / 8 (price-anchored) turn / break on the same 26 yeses;
bands expanding 7 / 11 vs 12 / 6. A lean that changes sign with the yardstick is not a lean. Forking path #1 (the
redefinition from 0.5σ to the live band's edges) created the table.

Item 4 (fut OI into the touch) on 26–27 Oct is roll OI. Forking path #2 (0.5 % never fired → use the sign) ran on a
contaminated input.

My AUDIT, same instrument, 19 days, two holdouts: 5-level depth imbalance → 0 lift; whole-book tbq/tsq stacking →
INVERTED (a stacking bid was a target). Item 3 is a known trap read on this feed.

## 4. Can it be done better?

| Piece | Spec | Better | Why |
|---|---|---|---|
| sign | quote rule, new | `handshake.book_flow` (quote rule, M5) / `ladder.attribute` (per level) — exists | the frame's `flow` is already quote-signed; Dext when present |
| clock | 20k buckets, 10-bucket window | the leg event: since the extreme (legs.py's pause) | a 10-bucket window spans 10–36 min [M] and reaches before the entry; the pause is the question's own anchor |
| result | new extreme ≤ 6 min | legs.py PAUSE_MIN / NEW_U — exists | identical |
| speed | bucket time vs day median | jarvis `speed` (3-min delta vs median) / AUDIT's "trading seconds" — exists; URGENT fired 8 of 77 | n 8 |
| HOT | VPIN pct ≥ 0.90 | keep as the VPIN gauge's own word, judged on its own clock | at the band it leaned against the fade (−1σ first 10 of 19): consistent with VPIN's registered purpose (toxicity precedes expansion) |
| absorption proper | — | `effort.py` (lots/pt ≥ 2× at a fresh high → reversal): the only flow read that passed two holdouts | it IS effort vs result, unsigned, tested |
| footprint absorption (volume at the extreme price, no progress) | — | Dext per-price levels: recording only today; gate 3 of retiring GoCharting | not now |
| words | 6 states + 2 stamps | none on the face until one measures forward | a word needs a number behind it |

## 5. Existing modules already cover it — the specific changes

| Spec piece | Where it already lives | Change |
|---|---|---|
| EFFORT (signed lead) | frame `flow` (Dext else book_flow, quote rule); legs.py D3_AGAINST risk item | add `flow_since_ext` (lots, signed) to each row of legs.py's `pauses` output — the forward pause log |
| RESULT (no new extreme 6 min) | legs.py pause object | nothing |
| SPEED | jarvis `speed` FAST / SLOW | nothing |
| HOT | `/api/vpin` pct | nothing; score the kill clock |
| VPIN's tick input | `vpin.py` | leave until the slow line is judged (40 sessions logged); then, if kept, switch to `book_flow`'s sign as a NEW registration with a new log |
| hold chip at a stall | `fold.py` VPIN chip (registered; hysteresis) | nothing; note the script's stateless chip is not the chip she sees (live holds WITH while net > 0) |
| absorption at an extreme | `effort.py`, DECODE EFFORT line, HOLD v3 EFFORT shadow line | nothing; its §D bar is already running |
| DISCOVERY | daytype TREND + IB; onesided TREND; legs quality TREND | nothing |
| exit rule "ABSORBED" | HOLD v3 shadow (§D bar) | do NOT register: 9 of 20 continuations on legs |

## 6. Her checklist, item by item

| Item | Keep / drop / change | From |
|---|---|---|
| absorption | KEEP, as `effort.py` (unsigned, tested) + the pause-log column (signed, untested) | effort.py; legs.py pauses |
| big limit orders | DROP as a signal; SHOW only (tbq/tsq, 5 levels) tagged "not predictive on 19 days" | book; AUDIT §3.2 / §3.4 |
| trapped traders | KEEP; this is what separated holds from breaks in oi-lab (composition + trapped + futures leg) | fold `trapped`, Sides top-2 under water, AUDIT_OI |
| aggressive traders | KEEP; already pushes + handshake (push → the wall's answer) + speed | jarvis pushes, RAFTAAR |
| change in delta | KEEP; after the touch, never at it (4 of 77 at the touch [M]) | CONFLUENCE FLOW ✓, legs D3_AGAINST |
| VWAP band expansion | CHANGE: a σ-trend stamp only (σ now vs 30 min ago); never a lean | frame `sd` |
| IB range | CHANGE: a stamp (forming / inside / outside) only; the "before 10:15 → turn" was the moving band | daytype IB |
| price discovery | DROP as a new state; = TREND day / outside IB, which three modules already say | daytype, onesided, legs |

## 7. Bugs and misreads in the scripts / numbers

1. **vpin_lab §3 outcome uses the moving band** (`sd[k]`, `vwap[k]` at minute k). TURN inflated 55 vs 28–42. Every
   "lean to turn" item follows from it. Bands-expanding is mechanically tied to it.
2. **vpin_turns's 10-bucket window at a stall includes the push into the band** (AGAINST: median 5 of 10 buckets
   pre-signal). "AGAINST → went on 17 of 29" becomes 4 of 10 on since-signal buckets.
3. **Overlap:** one NIFTY stream read by 3 indices × 4 setup groups. 120 stalls ≈ 70 (day, 5-min slot) episodes;
   19 WITH ≈ 8 moments; 27 Oct expiry = 8 of 19.
4. **Roll:** 26–27 Oct = 26 of 120 stalls on the expiring contract's volume and OI.
5. **Spec §2 C's controls** (depth in σ, time left, no BANKNIFTY) do not touch the confound that matters (buckets since
   the signal, pre-signal buckets). Time left is not it: ≥ 30 min left WITH 0 of 16 vs AGAINST 17 of 28 [M].
6. **§9 acceptance** reproduces the in-sample split; it cannot say the read is real.
7. Brief's "ik missing before ~5 Oct": it is missing 22–28 Sep only; 29 Sep carries 68407 (no Dext file). The day
   count 19 is right.
8. Live `vpin_fast.jsonl` holes [M]: 22 Sep 0 of 141 buckets; 16 Oct 63 of 125; 28 Oct 89 of 110; 30 Oct 137 of 157.
   9 of 120 stalls read "no read" live. The spec's anytime-start point (rebuild from the book) is correct.
9. The slow VPIN line's 30-session kill clock has **40 sessions** logged and no judgement. That is the first thing
   owed on VPIN, before any redesign.

## 8. As a trader

The question "who is hitting at the pause, and are they getting paid" is the right question. The tool already asks it
three ways (effort per point at the extreme, 3-min delta against at the pause, the push → wall handshake). The spec
adds a fourth copy on a volume clock, with six words, a log and a stamp, on evidence that is 8 moments of one
expiry-heavy week plus a table built on a moving yardstick. On the only broader population I could find (79 leg
pauses, 25 days) the headline reverses. Build nothing. Log one column. Score the VPIN clock that is already overdue.

## Files
- `fable_check.py` → `fable_check_out.txt` (A stalls, B leg pauses, C tick/quote/Dext, D live holes, E fixed band)
- `fable_check2.py` → `fable_check2_out.txt` (sign vs bucket count; the 19 WITH stalls listed; price-anchored touches)
- `repro_*.txt`: the spec's own scripts, unchanged, as run today
