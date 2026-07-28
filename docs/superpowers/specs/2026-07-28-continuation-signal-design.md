# BREAKGO — Both-Books Continuation Signal (Phase 2)

**Date:** 2026-07-28  ·  **Status:** **GATE FAILED 2026-07-28 — not shipped.**
Walk-forward result: best tune cell (margin 0.2R, confirm=both) +0.042R (n=17)
collapsed to **−0.190R on validation** (n=15); the `none` control scored −0.019R,
i.e. the ATM-book confirmation SUBTRACTED −0.171R out-of-sample. Raw momentum ≈
breakeven (consistent with the Opus prototype). Likely culprits for the failed
confirmation: rolling-ATM oi_slope is hop-noisy in the backtest data, and the
2026-07-27 template was full-chain (specific 23850CE/24100PE books), which the
54-day dataset does not contain. Iterate only with full-chain confirmation data
(accumulating daily in data/chain/ since 2026-07-21).
**Depends on:** measure.py harness (spec 2026-07-28-measurement-harness-design.md)

## Thesis

Breaks of strong liquidity levels CONTINUE (Opus prototype: fading them loses on
both walk-forward splits; momentum ~breakeven raw). The 2026-07-27 14:03 breakout
was the template: first close above 24,000 while the ATM call book unwound (fuel
burning upward) and the put book built (writers underwriting the move). Hypothesis:
requiring that both-books agreement turns raw ~breakeven momentum into +EV.

## Signal definition

Pools (strong only, v1): prior-day high/low (PDH/PDL) and session extremes that are
≥30 bars old. VWAP±2σ band breaks deferred (frequency risk; revisit in v2).

Trigger (continuation): first bar whose fut close crosses BEYOND pool ± margin·R
(margin tuned; R = causal R from measure.py). One trigger per pool per direction
per day. Direction = WITH the break.

Confirmation at trigger bar (ATM books from engine bars):
- UP break: CE oi_slope < 0 (call writers covering) AND PE oi_slope > 0 (put
  writers adding). DOWN break: mirror.
- Modes tested: `both` (as above), `either`, `none` (control — isolates the
  confirmation layer's lift, per Opus review).

Exits/costs: harness defaults (0.7R stop / 1.3R target / 45 min / 1.5 pt cost).

## Validation protocol

Walk-forward on the 54 backtest days: tune margin ∈ {0.10, 0.20, 0.30}·R ×
confirm ∈ {both, either, none} on days 1–35 (min 10 scored signals per cell),
freeze the best-expectancy cell, evaluate blind on days 36–54.

**PASS =** validation exp_R > 0 after costs, CI and signals/week reported, and the
`none` control shown alongside (confirmation must add, not just survive).
**FAIL =** report honestly, do not wire into engine/UI, iterate design later.

## Deliverables

`continuation.py` (pure generator + `--walkforward` runner through measure.py),
`test_continuation.py` (synthetic-bar unit tests). Engine/UI integration is a
separate step AFTER a pass, not part of this phase.
