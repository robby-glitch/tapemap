# Research findings — what has been scored, and what died

**Point a new session here for anything about "does X work".** `HANDOFF.md` §6
carries one-line verdicts; the evidence, the exact rule tested and the
failure modes live here. Every scorer named below is a standalone CLI in the
repo root and re-runs offline from `data/backtest/`.

Last updated: 2026-08-04.

---

## 1. The one surviving edge

**NIFTY (and SENSEX) — d3 band reversal, intraday, buy-side only.**

The rule, as the data supports it:

> After **09:30**, a 3-min candle's low pierces **d3 (−3σ of session VWAP)**
> and the *same candle closes back above it*. Enter at that close. Stop 20 pts
> below the band. **Touch nothing until VWAP.** Past VWAP, trail band-to-band;
> from +2σ, 15 pts under the high. Flat by 15:15.

| measure | value | source |
|---|---|---|
| hit rate @30m | **72%** (n=18, first-of-run post-09:25) | `rotation_score.py` |
| median move @30m | **+21.0 pts** (≈ +0.085%) | same |
| control (any bar, same horizon) | +0.3 pts, 50% | same |
| with 09:30 gate | 73%, med +23.7 (n=15) | ad-hoc, 2026-08-04 |
| typical adverse swing before it works | **−20.7 pts** | `trail_score.py` |

**Frequency ~1–2 per week.** SENSEX agrees (n=4, 100%). BANKNIFTY inverts.

### What management actually to use — measured, counter-intuitive

| management | mean | hit |
|---|---|---|
| no stop, fixed 30-min exit | +9.3 | 72% |
| **hold stop till VWAP, then trail** | **+4.8** | **56%** |
| band-to-band trail from entry | +2.5 | 44% |
| breakeven-if-narrow, then trail (operator's first description) | **−3.9** | 22% |

Two leaks, both measured: **moving to breakeven costs ~13 pts/trade** (NIFTY
re-tests the entry zone before rotating — 6 of 18 winners became scratches),
and **trailing below VWAP costs ~7 pts/trade** (compressed σ puts two rungs
inside one 3-min bar and parks the stop ~8 pts from price). The trail is
correct *above* VWAP: the 5 runners that reached u1+ kept +19 to +44.

The residual gap to the no-stop number is the 20-pt stop itself sitting
exactly at the typical adverse swing. Widening it is a **risk decision owed
by the operator** — deliberately not grid-searched.

---

## 2. Dead — do not revive without new evidence

| hypothesis | verdict | scorer |
|---|---|---|
| squeeze + falling OI = fade | REJECTED — BANKNIFTY inverts the sign | `squeeze_score.py` |
| engine event stream | `risk` −0.1 / `lean` −6.2 vs +4.1 control → default OFF | `signal_review.py` |
| SMC layer | 4× over-fires vs LuxAlgo, ⅔ UNKNOWN → default OFF | — |
| classic 15-min ORB | REJECTED — NIFTY breakouts *fade* (39% hit, −21.1 to close) | `orb_score.py` |
| overnight gap-fade | REJECTED — NIFTY fade ≈ 0 and under its long control | `gap_score.py` |
| d3 on F&O **stocks** | REJECTED — pooled 47% hit, med 0.000% (n=47, 7 names) | `stock_score.py` |
| d2 (−2σ) entries | noise everywhere — 180 NIFTY signals ≈ coin flip | `rotation_score.py` |
| **selling** any upper band | REJECTED on 5 independent datasets, every depth | multiple |
| compression / trap=CLEAR filter | HARMFUL — selected losers in 3 separate datasets | multiple |

### Two filters that were pre-registered and falsified (2026-08-04)

1. **Morning window.** Found post-hoc on ADANIGREEN (09:30–10:00 = 71% hit),
   echoed on NIFTY (83%) — then **died on RELIANCE** (50%, −0.21R), the
   largest sample of the three. Classic small-sample mirage: two of three
   agreeing is what randomness looks like at n≈7.
2. **Rotation-vs-trend state** (≥80% of last 20 closes below VWAP + falling
   VWAP = TREND). Pooled **ROTATION 43%/−0.21R vs TREND 38%/−0.25R — no
   separation**; ADANIGREEN's ROTATION bucket was 0/3. *Design flaw worth
   fixing if ever retried:* the 20-bar lookback silently dropped every
   pre-10:15 trigger (n fell 16→9, 28→18, 17→9), so it never tested the
   morning trades it was built to explain.

---

## 3. The regime map — the most reusable thing learned

Four independent tests drew the same boundary:

| instrument / context | behaviour |
|---|---|
| NIFTY, SENSEX — intraday σ-stretch | **mean-reverts** (liquidity noise) |
| BANKNIFTY | **trends** — inverts every reversion test |
| Overnight gaps | no edge — informed repricing, not noise |
| Single F&O stocks | no edge — a stock's −3σ is often *news*, and news continues |

**The edge is specific to broad-index intraday liquidity noise.** A stretch
caused by information does not revert; a stretch caused by flow does.

### Why stocks fail, quantitatively

1σ as a share of price at a d3 trigger: **NIFTY 0.076% · RELIANCE 0.171% ·
ADANIGREEN 0.249%.** So NIFTY's 20-pt stop is 1.55σ, while the same σ-scaled
stop on a high-beta stock is 3× wider in price terms — for a bounce that is
not 3× bigger. Risk-reward inverts. (Verified across 1.0σ / 1.55σ / 2.0σ
stops; negative at all three, and negative at every width after dropping the
single best trade.)

---

## 4. Two conditions the operator watches that are NOT yet scored

Both are logged live by `trigger_log.py` and need ~20–25 signals.

- **Gamma regime at trigger** (their #17). Mechanically sound — negative
  gamma amplifies the move that made the d3, pin/positive damps it — but
  there is no per-trigger gamma history in the cache, so it is untestable
  backwards.
- **OI strength ≥40% on the side being bought** (their #18). The available
  proxy (single-strike monthly-leg ΔOI) says a **40% put-heavy entry veto
  would have removed 10 of 12 signals including 9 winners** — at a d3 low the
  flow is structurally CALL-heavy; put-heaviness arrives *after* the turn.
  **Recommendation: use it as a hold/add confirmation past VWAP, not an entry
  veto.** Post-hoc hint only (n=12, not pre-registered): the two worst trades
  were the only ones where ΔCE ≥ 3.5× ΔPE — a one-sided call-writing ceiling.

---

## 5. Stop rule for this line of work

**As of 2026-08-04, seven consecutive tests outside NIFTY/SENSEX d3 came back
negative or falsified.** Two "findings" appeared mid-search and both
evaporated on the next dataset.

> Further slicing of `data/backtest/` (incl. the ADANIGREEN / RELIANCE
> TradingView exports) will manufacture a false positive by multiple
> comparisons. **The next evidence must come from forward live logging
> (`trigger_log.py`), not from re-cutting this cache.**

If a new idea is worth testing, it must be **pre-registered in this file
before the run** — prediction first, then the number.

### The methodological lessons, both paid for today

1. **Hit rate without a stop is a mirage.** ADANIGREEN's d3 looked like 67% at
   a fixed 30-min horizon; with a real stop it was 25% hit and 15 of 16 trades
   stopped out.
2. **Always ask what remains after dropping the single best trade.** That one
   ADANIGREEN winner (+13.6R) carried an entire "positive" mean that was
   negative without it.

---

## 5b. PRE-REGISTERED — two-leg OI sign divergence (written 2026-08-04, UNTESTED)

Registered **before** any scoring run, per §5. Nothing below is a result.

**H1.** On a premium-matched leg pair (both legs ≥ ₹100, premiums within ±₹25 —
the operator's selection rule), the **sign relationship between the two legs'
ΔOI** separates directional moves from chop, and does so *earlier* than the
level of either leg's OI.

Metric, per 15-minute bucket:

```
strength = (ΔOI_CE - ΔOI_PE) / max(|ΔOI_CE|, |ΔOI_PE|)
```

**Predictions, committed in advance:**

1. `|strength| < 1` (both legs' OI moving the SAME way) → the index is
   ranging in that bucket; band triggers inside it underperform.
2. `|strength| > 1` (OPPOSITE signs) → directional bucket. **strength < 0 →
   index up** (call writers covering while put writers build); **strength > 0
   → index down**.
3. The sign of `strength` leads or coincides with the index's move for the
   bucket at a rate materially above 50%.
4. On the d3 setup specifically, `strength` turning negative is a **hold/add**
   signal after the VWAP cross — *not* an entry filter (same conclusion §4
   reached for chain-level OI; predicted to repeat per-leg).

**Falsifier:** prediction 3 at or below ~55% across ≥15 sessions, or
prediction 1 failing to separate at all.

**Provenance — this must not be forgotten.** The hypothesis was *generated*
from 2026-08-04, where all 6 buckets matched (0.07 ranging, then −1.13/−1.35
into the rally, then +1.51/+1.79/+1.35 into the fall). **That day therefore
cannot test it.** 2026-08-04 was also a weekly expiry, when OI unwinds
atypically — expiry days should be bucketed separately, not pooled.

**Data required, and why it does not exist yet:** per-leg 1-min OI for a
premium-matched pair. Expired weeklies drop out of Dhan's scrip master, so
this is forward-capture only. First capture:
`data/backtest/WEEKLY_LEGS/NIFTY_2026-08-04_*.json` (partial, to 10:52).
Needs ~15 sessions before any number is worth reading.

---

## 6. Known gap the code cannot yet see

The operator reads *"is price rejecting the band or walking along it"* off the
chart in one second (Kite screenshots, RELIANCE 31-Jul and 3-Aug, 2026-08-04).
Nothing in the repo measures band-riding vs band-rejection. The one attempt
(§2.2) was falsified, but the attempt was flawed rather than the idea being
disproven. **This is the most promising un-encoded piece of the operator's
read** — if it is retried, it must avoid a lookback that silently excludes the
morning, and it must be pre-registered.
