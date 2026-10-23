# EVIDENCE AUDIT: what is established, what is not, where the records disagree

**Written:** 2026-10-20. Read-only audit; nothing in the repo was changed except this file.
**Lens:** evidence status and internal contradictions. Market mechanics are covered separately in `MECHANICS-ATTACK.md`.
**House rule kept:** no hit rate, win rate, expectancy, average P&L or any other outcome statistic is computed or printed
here. Historical numbers from her records are named only by their status (VOID, FAIL, OBSERVATION). The forward-record
section counts rows only; every count script read no outcome field (`mfe`, `mae`, `stop_hit`, `f15`, `f30`, `triggered`).
**Tags:** [M] = measured off a file today. [I] = inferred.

---

## 0. The short version

1. **Nothing she trades has a measured result.** Every positive number in the repo is either VOID (wrong trigger) or
   measured on the d3 *line*, which §1b says she does not trade. The zone, its trigger, its stop, its management, the
   u2 SELL, the fade gate, S1–S5 and the hold/fold reads are all either pre-registered and UNTESTED, or never written down.
2. **Her 5-year spine and the zone are different setups, and they disagree about where the edge is.** As recorded in
   PaperDesk, the 5-year result says that fades deeper than 2.4σ, after 13:15, or with fewer than 2 days to expiry lose.
   The zone arms anywhere from 2σ to past 3σ, re-arms on deeper lows, and has no 13:15 cutoff and no expiry gate.
   The repo's only measured positive (§5c) sits at 3σ, which is exactly the depth the 5-year result refuses. The
   5-year result itself has no data, scorer, date range, index or placebo definition anywhere on disk.
3. **The forward record is big by count, but it cannot settle anything yet.** The pass bar has been "owed by the
   operator" since 2026-08-08. The file still carries 375 midnight-copy rows and one torn line. The subset she would
   actually trade (zone entries the gate calls LEGAL) is 13 BUY and 9 SELL across all three indices, under the
   15-per-side line.
4. **Several kill clocks are due now and nobody has read them:** VPIN (32 sessions logged against a 30-session clock),
   `direction.py` (34 days of `desk_log` against ~30), and §1d (15 gated sessions against 10).

---

## 1. Evidence status, component by component

Status words: **CLAIMED** (her 5-year record, not on disk) · **MEASURED** (in the repo, with n and scorer) · **VOID** ·
**PREREG-UNTESTED** · **DEAD** (on §2's Dead list) · **NEVER WRITTEN** (no rule text in the repo) · **SHADOW**
(computed and shown, with no record yet that judges it).

`RF` = `context/research-findings.md`. `MEM/` = `C:/Users/kaam/.claude/projects/C--Users-kaam-Desktop-operator-mode/memory/`.
`PD/` = `C:/Users/kaam/Desktop/operator mode/paperdesk/v1.22.6/`.

| # | Component | Status | Source line |
|---|---|---|---|
| 1 | **Zone arm at d2/u2** | PREREG-UNTESTED (§1b, 2026-08-14). The d2 *line* on the one-candle trigger is DEAD. The 2.0–2.4σ pocket is CLAIMED as the edge. | RF:144-146 "a bar whose **low enters the lower azure** (low ≤ **d2**) arms a BUY"; RF:723 "d2 (−2σ) entries \| noise everywhere — 180 NIFTY signals ≈ coin flip \| `rotation_score.py`"; PD/src/core.js:56 "frozen pocket — is 2.0–2.4σ, before 13:15, DTE >= 2" |
| 2 | **Arm at d3/u3** | One-candle d3: VOID. Two-candle d3 line: MEASURED, NIFTY n=19 over 65 cached sessions, `run_score.py`, verdict "NOT falsified", but RF:124-125 calls it "wrong instrument". ≥3σ is a CLAIMED refusal. | RF:16-24 (VOID); RF:1240, 1258-1259 "**The edge is real on NIFTY.**"; RF:124 "§5c ("d3 only"...) — wrong instrument. Not disproven; **unmeasured**"; PD/src/bands.js:369-373 "3σ se gehra ... Ye fade nahi hai" |
| 3 | **Reversal trigger** (a later close beyond the reference bar) | MEASURED only on the d3 line (§5c). For the zone it is PREREG-UNTESTED, and open question (a), two-candle vs one-candle, is unanswered. The code ships two-candle by default. | RF:147-148 "carried over from §5c unchanged, pending the operator's answer"; RF:155-156 (a); `context/HANDOFF.md`:485 "Still open, hers to answer (§1b (a) and the u2 question)"; `band_rotation.py`:1112 |
| 4 | **Stop** | d3−20 was MEASURED on the line (§5c). The zone's d2−20 is NEVER WRITTEN as her answer: the code picked it. Open question (b) is unanswered. | RF:157-158 "(b) ... `d3 − 20` ... or `d2 − 20`?"; `live.py`:1103-1107 (zone = `band="d2"` with `OPERATOR_STOP_PTS`); `band_rotation.py`:1138 `_stop_px(ref["level"], ...)` |
| 5 | **Management** | §1's management table: VOID trigger. The `hold` arm on the d3 line: MEASURED, n=19 NIFTY (`trail_score.py`). §5f is an OBSERVATION with no bar set before the run. Zone management: never measured. | RF:50-57 (VOID population); RF:1297-1325; RF:1116-1121 "This is an OBSERVATION, not a test"; START-HERE.md:51-53 "`exit_why` is a re-fire lock, not a trade exit" |
| 6 | **Opening gate** | 09:25: carried over and never tested as a gate (its basis is σ warm-up); open question (d). 09:30: an ad-hoc cut on the VOID rule. 09:45: CLAIMED, and found only in the memory profile, not in PaperDesk's gate. S5's "first 25 min" lives in the memo only. | RF:151, 161-163; `band_rotation.py`:227 `ANCHOR_HHMM = "09:25"`; RF:45 "with 09:30 gate ... ad-hoc"; MEM/user-mary-trader-profile.md:15 "between 09:45 and 13:15"; MEM/how-she-sells.md "leave the zone's 09:25 anchor as it is" |
| 7 | **13:15 cutoff** | CLAIMED. Enforced in PaperDesk only. Absent from the zone machine and never measured in the repo. | PD/src/core.js:69 `pocketCutoff: "13:15"`; PD/CHANGES-1.17.0-to-1.19.1.md:104-107 |
| 8 | **SELL side** | Upper-band selling: DEAD on 5 datasets (one-candle). u3 two-candle at a fixed +30m: MEASURED FAIL (n=18), but on a management she does not use. §5f: OBSERVATION. u2 SELL: never measured. It is built on her instruction, with no score. | RF:724 "**selling** any upper band \| REJECTED on 5 independent datasets, every depth"; RF:865-866 "C3 rejected upper-band selling on the OLD one-candle rule"; RF:951 "**All three missed. FAIL.**"; RF:921-923; RF:472-474 "whether **u2 SELL survives at all**"; `live.py`:1089-1092 "no need backtesting" |
| 9 | **Fade gate §1d** | PREREG-UNTESTED (2026-09-23 00:40). It has been in charge of beeps and marks since 2026-09-23 (an illegal tap is silent and grey). Its falsifier is due. | RF:380-382; RF:460-463 (falsifier, "over 10 sessions"); MEM/fade-gate-on-the-face.md "must drive the tool now, not after a 5-day sample" |
| 10 | **90-minute write guard** | CLAIMED, and NEVER WRITTEN. | `docs/hold/EXPRESSION-PREREG.md`:91 "her "90-minute write guard" has no text in the repo"; also :1049, :1587 |
| 11 | **Both-legs-rising skip (8/8)** | CLAIMED. Never measured in the repo. It is used as a refusal (R4) inside the expression read. | MEM/user-mary-trader-profile.md:15 "the both-legs-rising skip filter (8/8)"; `docs/hold/EXPRESSION-PREREG.md`:258-261 |
| 12 | **S1 sweep-and-reclaim** | Exists in the memo only. Its legality comes from `regime.py`, a SHADOW layer with [I] thresholds. No detector logs S1 setups. | MEM/two-regimes-and-setups.md:22 "S1/S2/S4 sit on one afternoon's observation"; `regime.py`:52 "the [I] layer: one afternoon's judgement, awaiting a scoreboard", :56 `SHADOW = True` |
| 13 | **S2 cascade** | Memo only, as S1. Next to the dead ORB row. No log. | MEM/two-regimes-and-setups.md:13; RF:720 |
| 14 | **S3 pin income** | Memo only. The memo says it "sits on" the 5-year record, but no pin or credit-structure result exists in any text. The gear entered PIN 9 times in 102 index-days [M]. The paper desk was deleted 2026-09-28. | MEM/two-regimes-and-setups.md:22 "S3 and S5 sit on Mary's 5-year placebo-corrected record → normal size"; `data/desk_log.jsonl` |
| 15 | **S4 expiry flush** | Memo only: "logged, not traded — paper 20 expiries first". No log exists. | MEM/two-regimes-and-setups.md:15; `expression.py`:39 (a printed line, not a log) |
| 16 | **S5 skip** | Memo only. "Logged as an executed trade with a skip tag": no such log exists. Its only forward trace is the expression's R4 "both legs rose" reads. | MEM/two-regimes-and-setups.md:16; `data/hold/expr_*` |
| 17 | **CE/PE pair must rotate; OI build-rate deceleration** | Her rule per the profile, but NOT on the logged rule. Every zone record carries `confirm: "UNKNOWN"`. | MEM/user-mary-trader-profile.md:15; `band_rotation.py`:712-716 "this is trigger plus compression context only and is never CONFIRMED" |
| 18 | **Hold/fold reads** (zone, flow, OI, VPIN) | rev 4 + rev 5 B: SIGNED, PREREG-UNTESTED, and off the face since 2026-09-29. rev 6: "not yet signable", never signed (no §1i in RF), running `shadow: true` on the face. The four reads are her statement of 2026-09-28. VPIN is SHADOW, NIFTY-FUT only. Two in-sample reviews (not results) record that the reads and the word did not separate her losers from her winners. | RF:479-549; `docs/pro-tool/6-amendment.md`:1 "REV 6: THE PRO TOOL, one amendment (not yet signable)"; MEM/hold-fold-window-2026-09-24.md (2026-09-29 entry); MEM/how-she-sells.md:26; `docs/review/TRADER-REVIEW-2026-10-03.md`; MEM/validate2-rebuild-2026-10-06.md "did NOT separate winners from losers" |

---

## 2. Internal contradictions

Each item gives both quotes and a verdict: **STANDS**, **PARTLY DISSOLVES**, or **DISSOLVES**.

### C1. The d2 entry is "noise" vs "reaching d2 IS the event": PARTLY DISSOLVES
- RF:723: *"d2 (−2σ) entries | noise everywhere — 180 NIFTY signals ≈ coin flip | `rotation_score.py`"*
- RF:106 / CLAUDE.md rule 3: *"Entering the zone means the bar reached d2"*, *"Reaching d2 IS the event."*
- **Why it partly dissolves:** `rotation_score.py` is the scorer of §1's one-candle rule, which §5c calls "deliberately
  stop-free" (RF:1237). So the d2 row was measured on the same trigger that made §1 VOID. By the repo's own standard
  it should read "VOID, wrong trigger", not "dead". The Dead list was never re-labelled. [I: the row does not restate
  its trigger; this is inferred from the scorer.]
- **What remains:** on the one trigger where both depths were measured, depth mattered (d2 was noise, d3 was the edge).
  The zone pools d2-only setups with setups that went on to reach d3. §1b's falsifier clause 2 (RF:166-168) exists for
  exactly this. The arm rows carry `level` (d2) and `extreme` but not d3, so the split must be re-derived from stored
  tapes. That counts as filling forward rows, so it is allowed.

### C2. Upper-band selling is DEAD vs the u2→u3 SELL zone: STANDS (the trigger point dissolves; the substance does not)
- RF:724: *"**selling** any upper band | REJECTED on 5 independent datasets, every depth"*
- RF:83-84 (her words, 2026-08-14): *"the upper band is where i look for sell if market condition is right"*
- **Why the trigger point dissolves:** C3 was the one-candle rule (RF:865-866).
- **Why the substance stands:** the only two-candle test, §5d u3, FAILED (RF:951), and that was on a fixed horizon
  she does not use (RF:921-923). §5f is observation only. **u2 SELL has never been measured on any trigger.**
- **She also contradicts herself.** On 2026-07-31, `band_rotation.py`:878-882 records that *"they buy at -2 or -3
  sigma but sell only at +3"*, and §5d registers *"u3 only, never u2"* (RF:880). Then the 2026-08-14 zone puts the
  SELL at u2.

### C3. The classic 15-min ORB is dead ("NIFTY breakouts fade") vs S2 cascade entries in minutes 1–5: MOSTLY DISSOLVES
- RF:720: *"classic 15-min ORB | REJECTED — NIFTY breakouts *fade*"*
- MEM/two-regimes-and-setups.md:13: *"Buy nearest-expiry ATM, **minutes 1–5 only**"*
- **Why it dissolves:** "minutes 1–5" counts from the ignition, not from the open. S2 needs OI fuel, then ignition,
  then drain. That is a different trigger from a time-boxed range break.
- **What remains:** the regime map (RF:748, "NIFTY ... mean-reverts") and the ORB result both point against buying
  NIFTY continuation. S2's own support is "one afternoon's observation" (memo line 22). Nothing measures it and nothing
  logs it.

### C4. "BANKNIFTY inverts every reversion test" vs her trading BANKNIFTY with the same zone: STANDS, and it cuts both ways
- RF:749: *"BANKNIFTY | **trends** — inverts every reversion test"*
- The zone machine arms and enters on BANKNIFTY exactly as on NIFTY: 358 arms and 123 entries in clean live rows [M].
  The face plays them, capped at a soft beep (MEM/fade-gate-on-the-face.md). MEM/how-she-sells.md says *"She trades
  options on all three"*.
- **The evidence behind "inverts" is itself under the repo's own inconclusive line.** BANKNIFTY n=8 (§5c, RF:1283),
  n=7 (old rule), n=5 (§5d, RF:966-968, *"n=5 is under the inconclusive line anyway"*). The regime map still calls it
  "the most reusable thing learned" (RF:742). So the repo holds one evidence standard for its verdicts and a looser
  one for its boundaries.
- Since 2024-11-20, BANKNIFTY options have been monthly-only (verified, §4). Every BANKNIFTY number in the repo and in
  the forward record is on the monthly series.

### C5. The §4 put-heavy veto vs §1d requiring the PE front to be building at a BUY fade: PARTLY DISSOLVES
- RF:776-780: *"a 40% put-heavy entry veto would have removed 10 of 12 signals including 9 winners — at a d3 low the
  flow is structurally CALL-heavy; put-heaviness arrives after the turn. Recommendation: use it as a hold/add
  confirmation past VWAP, not an entry veto."* `context/CHECKLIST.md`:52, C11: *"NOT an entry veto"*.
- RF:411-415 (§1d): *"For a BUY fade that is the **PE** front ... 'building' means its 15-minute OI-change slope is
  **rising**"*
- **Why it partly dissolves:** the two measures differ. §4 used a single-strike monthly-leg ΔOI share as a proxy, with
  n=12, post-hoc. §1d uses the near-ATM top-2 strikes by peak OI and the direction of their slope.
- **What remains:** the mechanism is the same (put writers adding at the low), and §4 predicts §1d will mark most
  turning BUY fades illegal. Since 2026-09-23 an illegal tap is silent and grey on the face: a de facto entry veto,
  which is the use C11 forbids. **Gate output, counted, not scored:** in the gated period, zone BUY arms read ILLEGAL
  229 / LEGAL 45 / PATA NAHI 13 [M]. §1d's prediction 1 (RF:453) was *"a large minority"* illegal; the count is a
  majority. That is a description of the gate, not an outcome.

### C6. The compression filter is HARMFUL vs S5's "transition = compressed σ + one-sided OI → skip": LARGELY DISSOLVES
- RF:725: *"compression / trap=CLEAR filter | HARMFUL — selected losers in 3 separate datasets"*. CLEAR means
  *"broke out of an index squeeze"* (`band_rotation.py`:689).
- MEM/two-regimes-and-setups.md:18: *"Transition (compressed σ + one-sided trapped OI) → neither"*
- **Why it dissolves:** "fades out of compression selected losers" points the same way as "skip compressed
  transitions".
- **What remains:** S5 adds "one-sided trapped OI", and that conjunction has never been tested. §1b's 2026-08-14
  observation (RF:220-225: compressed morning faded, expanding afternoon walked) points the **opposite** way. That
  observation was n=1, post-hoc, and used a different measure (the 30-minute range percentile, not band-width rank).

### C7. The 5-year pocket vs the zone and the repo's "one surviving edge": STANDS. This is the largest one.
- PD/src/bands.js:313-320: *"depth > pocketMax the band is breaking, not holding — deep fades lost ... The surviving
  rule is the frozen pocket: 2.0–2.4σ, before 13:15, DTE >= 2."*
  PD/src/bands.js:390: *"expiry-day fades were the worst bucket in five years of data."*
- RF:14: *"NIFTY (and SENSEX) — d3 band reversal ... The one surviving edge"*; START-HERE.md:147.
- The zone arms from 2σ, re-arms on every lower low (RF:149), so setups run through 2.4σ and 3σ. It has no 13:15
  cutoff and no DTE gate. The profile's "*first* 2.0–2.4σ touch" sits against the zone's re-arms.
- **Counted [M] on the 415 clean zone entries:**
  - 80 came after 13:15.
  - 130 came with `t_exp` < 2 days [I: `t_exp` is the chain's nearest expiry].
  - 58 came before 09:45.
  - Only 188 sit inside both the 5-year clock window and its DTE window. Touch depth in σ is not stored on the rows,
    so the depth refusal cannot be checked from the record.
- Her two tools on the same chart give opposite instructions at 2.5σ and later. PaperDesk shades 2.4–3σ as
  "refused"; TapeMap arms on it.
- Her standing rule is *"When a 15-day sample disagrees with it, the 15-day sample is wrong by default"*
  (MEM/user-mary-trader-profile.md:22). Under that rule, the zone's deep, late and expiry fades should be refused.
  Nobody has reconciled this.

### C8. The target: "+2 and +3 std" vs "fade toward VWAP" vs the adopted management: PARTLY DISSOLVES
- `band_rotation.py`:864-866 (2026-08-07): *"20 points is good and i ll manage trade my self and target is always +2
  and +3 std."*
- MEM/user-mary-trader-profile.md:15: *"fade toward VWAP"*. RF:36-37: *"Touch nothing until VWAP. Past VWAP, trail
  band-to-band"*.
- **Why it partly dissolves:** they can be read as one ladder, with VWAP as the first milestone and +2/+3σ as later
  rungs.
- **What remains:** the 5-year exit ("toward VWAP") is a different exit from anything TapeMap measured, so the 5-year
  result cannot vouch for TapeMap's management, and the reverse holds too.

### C9. Five stops: STANDS
- d3−20 (§5c, RF:1200).
- d2−20 (the zone code, by default).
- *"the stop at d3 − 20"* on the pill state (`context/HANDOFF.md`:1876).
- S1: *"stop beyond the sweep extreme"*.
- The hold-window line (rev 5 B: *"a 3-minute index close beyond L"*, RF:527-528), signed on her delegation. On
  2026-09-28 she said *"i dont care about candle close or anything"* (MEM/how-she-sells.md:26). So the signed, in-force
  hold rule is a candle-close rule she has rejected, and the rule on her face (rev 6) is unsigned.

### C10. "VPIN behind me" vs VPIN "never directional": STANDS
- MEM/how-she-sells.md:26: *"zone oderflow oi and vpin and if these are behind me i will hold"*
- MEM/vpin-shadow-module.md: *"never directional, never an entry ... nothing downstream reads it"*;
  MEM/hold-fold-window-2026-09-24.md: *"never make VPIN vote before its shadow record qualifies"*.
- By its own design, VPIN cannot be "behind" a side.

### C11. "One regime classification per morning" vs the gear's own log: STANDS
- MEM/two-regimes-and-setups.md:8: *"One regime classification per morning ... Revisable intraday only by mechanical
  tells"*
- `data/desk_log.jsonl` [M]: in-session gear changes, with restart baselines excluded, number a **median of 24 per
  index-day** (102 index-days, max 122). PIN was entered 9 times across those 102 index-days.

### C12. S3 and S5 sized "normal" on the 5-year record vs what the 5-year spine names: STANDS
- MEM/two-regimes-and-setups.md:22: *"S3 and S5 sit on Mary's 5-year placebo-corrected record → normal size"*
- The spine as written names a fade, a write guard and a skip (MEM/user-mary-trader-profile.md:15). No pin-income or
  credit-structure result appears in any text. The "90-minute write guard" might be the S3 link, but it has no text.

### C13. Frequency "1–2 per week" vs the zone's fire rate: DISSOLVES as a contradiction, but it is a warning
- RF:48 *"Frequency ~1–2 per week"*; RF:1290-1291.
- Zone NIFTY BUY: 83 clean entries in 39 sessions, a median of 10 zone entries per session across indices [M].
- §1b predicted this (RF:170-171: *"More signals is not evidence; it is the thing that must be paid for"*). It
  dissolves as a contradiction, but nothing she has written says which of the ~10 a day she actually takes.

### C14. Four opening gates: STANDS
09:25 (zone/§5c), 09:30 (§1, ad hoc), "first 25 min" ≈ 09:40 (S5), 09:45 (the 5-year spine, profile only). The zone
logged 58 entries between 09:25 and 09:44 [M].

### C15. A naming collision: S1–S4 vs S1–S5: needs a fix, not a ruling
- MEM/how-she-sells.md:51-53: her **S1–S4 are GoCharting reference lines**, *"not inflication any decision making"*
- S1–S5 in the memo are setups. `context/HANDOFF.md`:556 has the Board lighting "S1 fade". One label means two things.

---

## 3. The forward record, described (rows only, no outcome read)

**File:** `data/trigger_log.jsonl`: 2,605 lines, **1 unparseable** (line 2529, a torn fragment), 2,604 rows [M].
**Identity-key duplicates:** 5 [M].

**Midnight copies still in the file.** 375 rows were written before 09:15 IST of their own `day`, on 16 (day, index)
pairs from 2026-08-06 to 2026-09-18. They include two Saturdays (08-22 and 09-05), which are BANKNIFTY copies stamped
00:00. By population: legacy 51, `5c` 62, `zone` 262 (arms 193, entries 69) [M]. They match the 375 that
MEM/hold-desk-review-2026-10-03.md:35 lists as *"not yet asked ... They pollute the forward record's counts"*.
**Every count below excludes them.**

### Populations
| rule | rows | sessions | range | note |
|---|---|---|---|---|
| legacy (no `rule`) | 256 | 4 | 08-04 → 08-07 | §1 one-candle, quarantined; 57 forming-bar |
| `5c` (d3/u3 line) | 394 clean | 32 | 08-10 → 10-08 | no 5c row after 2026-10-08 |
| `zone` (d2/u2) | 1,630 clean | 39 | 08-18 → 10-19 | the setup she trades |

Weekdays with no zone row: 09-08, 09-14, 10-02, 10-13, 10-14, 10-15. Holidays and server-down days are not
distinguished. 10-12 had 4 arms only.

### Zone, clean live rows
| index | side | arms | fresh setups (`rearm:false`) | entries |
|---|---|---|---|---|
| NIFTY | BUY | 243 | 84 | 83 |
| NIFTY | SELL | 182 | 68 | 59 |
| SENSEX | BUY | 245 | 96 | 85 |
| SENSEX | SELL | 187 | 70 | 65 |
| BANKNIFTY | BUY | 187 | 62 | 60 |
| BANKNIFTY | SELL | 171 | 66 | 63 |
| **all** | BUY / SELL | 675 / 540 | 242 / 204 | **228 / 187** |

- Every zone entry is banded d2/u2. No zone row records whether the setup reached d3.
- Entries per session: min 0, median 10, max 24.
- Entries by clock, BUY / SELL:
  - 09:25–09:44: 32 / 26
  - 09:45–13:15: 150 / 127
  - 13:16–14:59: 38 / 29
  - 15:00 or later: 8 / 5

### §5c line, clean live rows
| index | side | arms | fresh | entries |
|---|---|---|---|---|
| NIFTY | BUY | 50 | 11 | **11** |
| NIFTY | SELL | 48 | 18 | 15 |
| SENSEX | BUY | 76 | 25 | 21 |
| SENSEX | SELL | 49 | 23 | 23 |
| BANKNIFTY | BUY | 44 | 12 | 13 |
| BANKNIFTY | SELL | 35 | 11 | **9** |

### The gate field (§1d), stamped from 2026-09-23 (zone, 15 sessions) and 2026-09-24 (5c)
| population | side | ILLEGAL | LEGAL | PATA NAHI |
|---|---|---|---|---|
| zone arms | BUY | 229 | 45 | 13 |
| zone arms | SELL | 94 | 28 | 61 |
| zone fresh arms | BUY | 71 | 24 | 9 |
| zone fresh arms | SELL | 29 | 14 | 15 |
| **zone entries** | BUY | 78 | **13** | 8 |
| **zone entries** | SELL | 34 | **9** | 13 |
| 5c entries | BUY | 14 | 2 | 2 |
| 5c entries | SELL | 5 | 0 | 4 |

- LEGAL zone entries per index: NIFTY BUY 5, NIFTY SELL 2, SENSEX BUY 4, SENSEX SELL 2, BANKNIFTY BUY 4,
  BANKNIFTY SELL 5.
- Why PATA NAHI (zone): "near-ATM fronts not read" 74; "chain grid stale since …" 21.
- Outcome fields exist on 926 rows (filled by `trigger_log.py score`). They were not read for this audit.

### Against §5e's "under 15 per side is inconclusive" (RF:1089-1093)
- **Raw zone cells:** all six index-side cells are ≥59 entries, so the count floor is passed everywhere. That does not
  make anything readable. The pass bar is still owed (RF:1082-1087). Entries cluster inside legs, so sessions (39) are
  closer to the independent unit than entries are [I]. §5e was written for §5c, and the zone's "operator's horizon"
  (RF:165) has never been stated.
- **The population she would actually trade** (zone entries the gate calls LEGAL) is 13 BUY / 9 SELL pooled over three
  indices, and ≤5 per index-side cell. That is under 15 on every cut.
- **§5c:** NIFTY BUY (11) and BANKNIFTY SELL (9) are still under 15.

### Related logs [M]
| log | span | rows | what it holds |
|---|---|---|---|
| `data/hold/hold_<day>` (rev 5) | 6 files, 09-25 → 10-06 | 3,607 (13 `rung_touch`) | ~13 marked trades |
| `data/fold/fold_<idx>_<day>` (rev 6, `shadow:true`) | 7 files, 09-29 → 10-06 | 5,527 | 14 marked trades, 13 imported, 36 "if-in" presses |
| `data/hold/check_<day>` (VALIDATE) | 3 files | 5 presses + 3 outcomes | — |
| `data/hold/expr_<day>` (§1h) | 14 files, 09-28 → 10-20 | 8,200 expr + 736 outcome | PREMIUM read "both legs rose" 48 times |
| `data/vpin_log.jsonl` | 32 sessions, 08-25 → 10-19 | — | the 30-session clock is due |
| `data/desk_log.jsonl` | 34 days, 08-24 → 10-19 | 2,847 gear rows | the `direction.py` 30-session clock is due |

No marked-trade rows exist after 2026-10-06 in either hold log.

---

## 4. The 5-year claim

### Where it lives
- **Only in PaperDesk and in memory:**
  - PD/src/core.js:52-63
  - PD/src/bands.js:305-320, 369-401
  - PD/CHANGES-1.17.0-to-1.19.1.md:104-107
  - PD/HANDOVER.txt:1137-1143, 1507
  - MEM/user-mary-trader-profile.md:15
  - MEM/two-regimes-and-setups.md:22
- **Nothing in `tapemap/`** has it, except `EXPRESSION-PREREG.md` citing the profile.

### What can be known
- Its stated findings, as PaperDesk recorded them:
  - the edge is in the refusals;
  - fades on expiry day, after about 13:15, and deeper than about 3σ (2.4σ in code) showed "negative excess return";
  - the surviving pocket is 2.0–2.4σ, before 13:15, DTE ≥ 2.
- The profile adds "~1,200 sessions", "09:45", "first touch", "fade toward VWAP", the 90-minute write guard, and
  "8/8" for the both-legs skip.

### What cannot be known
None of the following appears anywhere on disk:
- the data;
- the scorer;
- the index or indices;
- the date range;
- the σ basis (Kite SDVWAP on 1-minute or 3-minute bars? `PD/CHANGES…`:251-253 notes her FUT ladder "looks like
  0.5/1.5/2.5/3.5");
- the exit and horizon;
- n per refusal bucket;
- **what "placebo-corrected" means.** In this repo the word appears only in later, unrelated studies (shifted-level
  placebos in `docs/fresh-take/`).

"8/8" is a count of 8. "Excess return" implies a benchmark that is not named.

### The window and market structure
~1,200 sessions is about 4.8 years [I], so roughly mid-2021 to mid-2026 if the backtest was run before PaperDesk
1.18.0. That window crosses:

| change | date | verified |
|---|---|---|
| SEBI circular: weekly expiry for **one benchmark index per exchange** | effective 2024-11-20; circular dated 2024-10-01 (sources differ on the date) | yes |
| BANKNIFTY last weekly expiry; monthly-only after | 2024-11-13 | yes |
| Minimum contract value ₹15 lakh: NIFTY lot 25→75, BANKNIFTY 15→30, SENSEX 10→20, for new contracts | from 2024-11-20 | yes |
| NIFTY weekly moves Thu→**Tue**; SENSEX moves to **Thu** (first: NIFTY 2025-09-02, SENSEX 2025-09-04) | 2025-09-01 | yes |
| SENSEX weekly earlier on Tuesday (moved from Friday) | ~2025-01 | implied by sources, **not verified** |
| NIFTY lot 75→65, BANKNIFTY 35→30 (first NIFTY weekly at the new lot: 2026-01-06) | announced Oct 2025 | yes (the BANKNIFTY 30→35 step before it: **not verified**) |
| Upfront premium collection, removal of the calendar-spread benefit on expiry day, extra ELM on expiry days | 2025 | **not verified** here |
| SENSEX options relaunched by BSE | 2023 | **not verified**. If true, a 5-year SENSEX series cannot exist |

### What that implies for a backtest spanning those changes [I]
1. **"DTE < 2" is not one population across the window.** With BANKNIFTY weeklies, two of every five days fell under
   DTE < 2. Now about two days a month do. NIFTY's expiry weekday changed. The "worst bucket" pools at least three
   expiry regimes.
2. **Expiry-day dynamics changed.** From November 2024, 0DTE flow was concentrated onto two indices, and lot and
   margin changes followed. An expiry-day verdict from 2022–24 does not transfer by default.
3. **The edge is "liquidity noise".** RF:754: *"A stretch caused by information does not revert; a stretch caused by
   flow does."* The late-2024 measures were aimed at the retail flow that supplies that noise. A pooled five-year
   number can be carried by its pre-change years, which are about 70% of the window [I].
4. **The repo's 65-session cache is entirely post-change** (2026, ending 2026-07-31), and so is the forward record.
   That is one honest way C7 could dissolve: the two results could both be right about different markets. **It cannot
   be checked without the 5-year data split by era**, and §5 forbids re-cutting the repo's own cache.

Sources:
- [Share.Market, weekly expiry days](https://www.share.market/buzz/insights/weekly-expiry-days-in-indian-fo-markets/)
- [Angel One, Bank Nifty weekly expiry ends](https://www.angelone.in/news/market-updates/bank-nifty-weekly-expiry-bids-adieu-2)
- [HDFC Sec, weekly expiries restricted](https://www.hdfcsec.com/blog/details/derivative-weekly-expiry-contracts-to-be-restricted-to-benchmark-indices)
- [Arihant, NSE/BSE expiry shift Sep 2025](https://www.arihantplus.com/blogs/market-updates/tuesday-is-the-new-thursday-nse-and-bse-expiry-shift-from-sep-2025)
- [Business Today, expiry-day history](https://www.businesstoday.in/amp/markets/stocks/story/nse-bse-fo-expiry-days-what-has-changed-for-stock-investors-history-more-480781-2025-06-18)
- [Zerodha, lot sizes from 2024-11-20](https://zerodha.com/marketintel/bulletin/393605/revision-in-lot-size-of-index-derivative-contracts-from-november-20-2024)
- [Zerodha, lot sizes from 2025-12-30](https://zerodha.com/marketintel/bulletin/429705/revision-in-lot-size-of-index-derivative-contracts-from-december-30-2025)
- [Kotak Neo, lot size changes Dec 2025](https://www.kotakneo.com/bulletins/lot-size-changes-in-index-derivatives-effective-december-30-2025/)

---

## 5. What would settle each open item, forward data only

Rates are today's clean rates: 39 sessions in about 9 weeks, about 4.3 sessions a week [M]. **Nothing here needs a
new backtest or a cache slice.** Filling fields on rows already logged forward is allowed (START-HERE.md:36-39).

| open item | what settles it | the blocker | time at current rate |
|---|---|---|---|
| **Zone (§1b)** | Her pass bar, plus her horizon, plus the control, judged on the forward zone rows. Falsifier clause 2 also needs a `reached_d3` flag filled from stored tapes. | **Her bar and horizon** (owed since 2026-08-08) | **0 sessions** once she states them; every cell already exceeds 15 |
| **Trigger (a) and stop (b)** | Her answer, recorded in §1b. Until then the forward rows are a test of a default the code chose. | Her word | 0 |
| **u2 SELL** | Same bar, applied to the SELL rows (187 entries). | Her bar | 0 |
| **§1d gate** | Its own falsifier: MAE of the ILLEGAL set vs the LEGAL set, plus the "single worst leg removed" check. Prediction 2 also needs a day type declared each morning. | Read the filled rows (10 sessions passed; 15 logged) | **due now** |
| **Gate-legal subset, per index** | ≥15 LEGAL entries per index-side cell. | Rate: NIFTY BUY ~5 per 15 sessions | NIFTY BUY ~30 more sessions (~7 weeks); NIFTY SELL ~100 more (~5–6 months) [I] |
| **5-year pocket refusals** (depth, 13:15, DTE, first touch) | Pre-register the pocket vs the refused populations on zone rows. Clock and DTE are already on the rows (80 entries after 13:15, 130 with `t_exp` < 2). Depth in σ at the touch is not; it needs a new stamp on arm rows (a logging change, her call). | The depth stamp | Clock/DTE: answerable now with her bar. Depth: from the stamp date, about 2 eligible NIFTY BUY entries per session [I] |
| **90-minute write guard** | Its text, written by her; then a forward field. | Text | unknown |
| **Both-legs-rising skip** | A per-entry field joining zone rows to the expression's PREMIUM read (48 "both legs rose" reads in 14 files so far). | The join | months [I]; rare by nature |
| **S1 / S2** | A pre-registered detector, a forward log, and n ≥ 20 each (the memo's own line). | No detector logs them | unknown until built |
| **S3** | A gear-PIN day log plus the structure taken. PIN was entered 9 times in 102 index-days. | Rarity | quarters, not weeks [I] |
| **S4** | The memo's own rule: paper 20 expiries. NIFTY (Tue) plus SENSEX (Thu) gives 2 a week. | No log exists | ~10 weeks from the first logged expiry |
| **S5** | The skip log the memo promises ("logged as an executed trade"). | No log exists | unknown |
| **VPIN** | Its declared kill test: pct ≥ 0.90 preceding a range expansion more often than the base rate. | Read it | **due now** (32/30) |
| **`direction.py`** | Its declared kill test (FORCED vs LEANING vs no direction). | Read it | **due now** (34/~30) |
| **Hold/fold (rev 5 signed; rev 6 shadow)** | rev 6 needs her commit, the gate table, then her signature. Its falsifiers need ≥15 trailed folds. She marked ~14 trades in 4 sessions, then none after 10-06. | Marking stopped; rev 6 unsigned | ~1–2 weeks of marking at the 09-29 → 10-06 pace [I] |
| **BANKNIFTY "inverts"** | The same bar on the 123 BANKNIFTY zone entries. | Her bar | 0 |

**Record hygiene comes first, and it is her word, not a rule change:**
- remove or tag the 375 midnight copies (MEM/hold-desk-review-2026-10-03.md:35);
- repair or quarantine the torn line 2529;
- resolve the 5 duplicate identity keys.

Every count above already excludes the copies, but any scorer pass over the raw file will not.
