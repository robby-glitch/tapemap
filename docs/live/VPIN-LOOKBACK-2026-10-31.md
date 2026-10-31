# VPIN slow line: scored on the draft's terms (look-back, 31 Oct 2026)

`her ask: "Yes, score VPIN"` `look-back, not the registered verdict` `KILL on both inputs` `her decision`

## What was scored
- **The registered clock** (`vpin.py`): "over 30 sessions, pct ≥ 0.90 must precede a range expansion at better than base
  rate, or the module dies". It never defined the expansion, the window or the base, so the 22 Oct review ruled it
  CANNOT CHECK (KILL-CLOCKS-2026-10-22.md §2, A35).
- **The draft** `VPIN-KILL-CONDITION-DRAFT.md` (25 Oct, unsigned) fixed all three terms and a KEEP / KILL / EXTEND bar
  before any row was read.
- **Applied here as written**, unchanged, to the sessions already logged. The draft says nothing counts until she signs,
  so this is a look-back (§1k), not the verdict.
- **Script:** `docs/live/vpin_score.py` (read-only). `--spot` runs the coverage check.

## The count [M]

| | NIFTY fut 1-min bars (the draft's input) | NIFTY spot, ~15 s (coverage check) |
|---|---|---|
| sessions logged / covering 10:00–14:30 | 40 / 30 | 40 / 30 |
| scored (bars on disk) | **20** (27 Aug – 17 Sep have no 1-min fut bars) | 30 |
| alarms (pct ≥ 0.90, first after 15 min quiet, 09:45–14:30) | 35 | 37 |
| alarm windows that expanded (30-min range ≥ 1.5× the slot's prior-20 median) | **14** | 12 |
| base blocks / expanded | 199 / 80 | 222 / 84 |
| base-expected expanded alarms (alarms × base expanded ÷ base blocks) | **14.1** | 14.0 |
| KEEP needs | ≥ 19.1 and ≥ 15 alarms | ≥ 19.0 |
| **the draft's bar** | **KILL** (14 ≤ 14.1) | **KILL** (12 ≤ 14.0) |

**In words:** after a VPIN alarm, the next 30 minutes expanded exactly as often as any half hour of the day. The alarm
added nothing.

## Checked
- **Volatile days did not rescue it.** Alarms cluster on wide days (1 Oct 3 of 3 expanded, 5 Oct 4 of 4), and still the
  total does not beat the base. 26, 29 and 30 Oct gave 10 alarms and 0 expansions (those days' prior-20 medians were
  already high).
- **Cluster rule:** 21 Oct was hot non-stop 09:39–12:13. That is one cluster that began before 09:45, so it gave no
  alarm. One more alarm cannot reach 19.1.
- **Overlap:** alarms 15–30 min apart share window minutes (29 Sep, 30 Oct). That flatters the alarms, not the base.
- **Input:** every session before her 26 Oct restart ran before the A67 feed-gap re-arm. Some alarm buckets may be gap
  artefacts. The tick rule misreads the aggressor on some minutes (A197: 3,098 vs the quote rule's 3,347 of 3,671).
- **The draft names `data/backtest/NIFTY/fut_<day>.json`.** That folder does not exist. The bars are
  `data/backtest/fut_<day>.json` (NIFTY), with the 1-s book's minute high / low from 22 Sep when no file exists.
- **"Prior 20 sessions"** = the 20 latest earlier days that have bars [I].

## Not covered by this test
- **The FAST line** (`vpin_fast.jsonl`) feeds the hold window's VPIN chip, which the one voice quotes as "VPIN saath". It
  has no kill clock. Fable's review (A198): at a stall it reads tape speed, not absorption.

## Her options
1. **Retire the slow line:** the VPIN tab's slow reading and its "hot" alarm leave the screens; its log stops. The fast
   line and the registered hold chip are untouched.
2. **Sign the draft as written** and count 30 sessions forward from her next restart (the clean A67 input).
3. **Keep it as is.**
