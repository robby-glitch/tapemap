# Phase 3 — Pre-registered Inversion Tests: Results

**Date:** 2026-07-28 · **Runner:** `python contrarian.py --run` (measure.py harness,
54 backtest days, 0.7R/1.3R, 1.5-pt cost, de-clustered, intrabar) · **Status: none
of the three clears its confidence interval. Nothing ships.**

Pre-registered (from the 54-day naive baseline): BUYER-BUILD inverted,
gamma-agreement split, CARRY inverted. No grids, no further mining.

| Test | n | hit / result | CI95 | Exp | Verdict |
|---|---|---|---|---|---|
| BB-INVERTED | 42 | 37% | 23–54 | +0.04R | ≈ breakeven. The original's 16% hit does NOT invert into profit — asymmetric exits don't mirror. |
| DIR-FIGHT (ARMED/SPRING vs MM lean) | 42 | 36% | 21–54 | +0.03R | direction of naive finding persists, unproven |
| DIR-AGREE | 7 | 17% | 3–56 | −0.22R | n far too small; weak support for "don't fade WITH a strong MM lean" |
| CARRY-INVERTED (next-day open→close) | 30 | 63% profitable | 46–78 | **+10.0 pts/day avg, +35.9 median** | most promising; CI still includes 50% — track, don't trade |

## Conclusions

1. Every "clear" naive-scorer finding softens to statistical ambiguity under the
   honest ruler. Inverting a bad signal is not free money.
2. CARRY-INVERTED is the one to keep watching: +10 pts/day average with a fat
   losing tail (median ≫ mean ⇒ occasional large hits). The nightly scorer should
   accumulate live samples; revisit at n≈60.
3. UI implication (Phase 4): the CARRY verdict must render with its track record
   attached; BUYER-BUILD demotes to observation-only.
