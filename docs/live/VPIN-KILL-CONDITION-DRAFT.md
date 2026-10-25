# VPIN kill condition — DRAFT for Mary's signature (25 Oct 2026)

`DRAFT · unsigned` `VPIN stays live (her call, 25 Oct: "vpin stay i want to test it further")` `nothing counts until signed`

## Why this exists
`vpin.py`'s own clock says: *over 30 sessions, pct ≥ 0.90 must precede a range expansion at better than base rate, or the
module dies.* On 22 Oct that clock could not be read (KILL-CLOCKS-2026-10-22.md §2, NOTEPAD A35), because none of its
three terms was ever defined: the size of an expansion, the window, the base rate. A test whose bar is chosen after the
numbers are seen is not a test (§5e). This page fixes all three **before** any new row is read.

## The terms (proposed — change any number before signing; after signing they are frozen)

| Term | Definition |
|---|---|
| Line | the SLOW line only: `data/vpin_log.jsonl`, NIFTY-FUT, 60,000-unit buckets. `vpin_fast.jsonl` and `vpin_backfill.jsonl` are other populations, never pooled. |
| Alarm | a bucket with `pct ≥ 0.90`, the first after ≥ 15 min with none (one alarm per cluster); time = the bucket's `at`; counted only 09:45–14:30, so the window closes before 15:00 and the percentile has its `MIN_HIST` |
| Window | the 30 minutes after the alarm |
| Expansion | NIFTY-FUT high − low over the window ≥ **1.5 ×** the median of the same 30-min clock slot over the prior 20 sessions (1-min bars, `data/backtest/NIFTY/fut_<day>.json`) |
| Base | the same expansion test on every 30-min block starting 09:45, 10:15 … 14:15 (10 blocks a session), same sessions |
| Session | a weekday with VPIN rows covering 10:00 → 14:30; a late start or an early end is listed, not counted |
| Start | the first session after her signature (Phase 1's feed-gap re-arm, A67, is live from her next restart, so the clock and the clean input start together) |

## The bar (proposed — counts, not rates; stated before any row is read)

After **30 counted sessions**:

| Outcome | When |
|---|---|
| **KEEP** | ≥ 15 alarms AND alarm windows that expanded ≥ (alarms × base blocks that expanded ÷ base blocks) **+ 5** |
| **KILL** | < 15 alarms, OR alarm windows that expanded ≤ that base-expected count |
| **EXTEND once** | anything between: 15 more sessions, same terms, then KEEP or KILL — never a second extension |

KEEP means VPIN may be read as an expansion warning (never an entry, never a direction — the gauge is direction-blind by
construction). KILL means it leaves the voice's reasons and the VPIN tab, and its log stops.

## What this changes today
Nothing. VPIN stays in the voice and its tab exactly as now. This page only decides how the test is read.

## Sign
- [ ] Mary accepts the terms and the bar as written (or with the numbers she changed above) — date / time:

Once signed: register it as §1r in `context/research-findings.md` with the sha256 of this text, as §1o–§1q were.
