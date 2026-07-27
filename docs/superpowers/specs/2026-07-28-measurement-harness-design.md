# Signal Measurement Harness — Design Spec

**Date:** 2026-07-28
**Status:** Approved (brainstormed with user; adversarial review by Opus subagent incorporated)
**Owner phase:** Phase 1 of the "improve results overall" track

## Problem

Two audits (54-day replay + 2026-07-27 live day) showed the narration layer scores ~51%
at symmetric 1R — but the measurement itself was flawed (independent review findings):
close-only fills (lenient), overlapping events pseudo-replicated as independent trades,
no cost, no confidence intervals, R computed with same-day lookahead, "open" outcomes
dropped. **Every conclusion about this tool is soft until the ruler is fixed.**
The 2026-07-27 SWEEP-fade prototype failing its gate on a coherent harness (while the
naive harness said "maybe") proved the ruler decides the verdict.

## Goal

One canonical scorer — `measure.py` — used by ALL signal evaluation from now on:
nightly self-scoring of live days, multi-day backtest replays, and the acceptance gate
for any new engine (continuation signal, inverted CARRY, etc.). No signal ships or
survives except through this harness.

## Non-goals (this phase)

- No new trading signals (Phase 2: continuation "both-books" signal, separately spec'd).
- No UI badges yet (Phase 4) — but the stats file it will read is produced here.
- No engine.py changes — the canonical direction map lives in the harness, unit-tested.

## Design

### Scoring rules (each fixes a named audit flaw)

1. **Intrabar first-touch fills.** Stop/target checked against bar H/L, not closes.
   Both touched in the same bar → counted as LOSS (conservative).
2. **De-clustering via cooldown.** While a scored trade for signal-kind K is open, further
   K-signals in the same direction are collapsed (counted as `collapsed`, not scored).
   Opposite-direction K-signal closes the open trade at that bar's close (reversal) and
   opens the new one. Optional `--portfolio` mode: one open trade per direction across
   ALL kinds (portfolio-level truth); default is per-kind.
3. **Cost.** `cost_pts` (default 1.5, per index override) subtracted from every trade's
   point outcome.
4. **Asymmetric exits.** `stop_R` / `target_R` params, default 0.7 / 1.3. Window default
   45 min; trade still open at window end → marked to close ("timeout" outcome, kept,
   not dropped). Day end (15:25) → forced mark ("eod" outcome, kept).
5. **Causal R.** R_i = median of trailing 15-bar rolling ranges using bars ≤ i only,
   warm-up 45 bars. Before warm-up: use `prior_R` (previous session's final R) when
   provided, else the signal is `skipped_warmup` (counted, reported).
6. **Wilson 95% CI** on hit rate per kind; expectancy in R and points with a flag when
   the sample cannot exclude 50% / zero expectancy. No naked point estimates.

### Interfaces

```
score_day(bars, signals, *, stop_R, target_R, window, cost_pts, prior_R, portfolio)
    -> [TradeRecord]        # bars: engine-style fut bars; signals: [{t, kind, dir}]
direction(kind, msg, data) -> +1 | -1 | 0     # canonical map (moved from audits, tested)
report(records)            -> per-kind table + dict (n, collapsed, hit, ci_lo, ci_hi,
                              exp_R, exp_pts, outcomes breakdown, verdict flag)
```

CLI:
- `python measure.py --backtest` — replay all `data/backtest/` days through the engine
  (reuses `backtest.load_day`), score all event kinds, write `data/signal_stats.json`.
- `python measure.py --live <payload.json>` — score a saved `/api/data` payload (or
  fetch `http://127.0.0.1:8765/api/data?idx=X` for today) and append that day's records
  to the rolling stats file.

`data/signal_stats.json`: `{"params": {...}, "days": {"YYYY-MM-DD": {kind: {...}}},
"rolling": {kind: {...}}}` — the file the future UI badges and nightly cron read.

### Testing

`test_measure.py`, synthetic bars, no network:
win / loss / both-in-bar / timeout / eod-mark paths; cooldown collapse + reversal;
cost arithmetic; causal-R no-lookahead (mutating future bars must not change R_i);
warm-up skip; Wilson CI against known values.

## Acceptance

- All tests green; existing tests unaffected.
- `--backtest` runs the 54 days and reports per-kind stats with CIs — this becomes the
  new baseline table of record (expected: most kinds' CIs straddle 50%; that is the
  honest state of knowledge).
- `--live` scores 2026-07-27's saved payload without error.

## Follow-up phases (each needs its own plan)

- **Phase 2:** "both-books continuation" signal (strong pools, trade WITH the break,
  CE-unwind + PE-build confirmation as seen 2026-07-27 14:03) — walk-forward 35/19
  through this harness; ships only on +EV validation with CI reported.
- **Phase 3:** inverted-CARRY and gamma-sign tests with CIs.
- **Phase 4:** UI: rolling-stat badges beside events; event thinning (confluence-first
  narration); engine emits explicit `dir` in event data.
