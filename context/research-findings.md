# Research findings — what has been scored, and what died

**Point a new session here for anything about "does X work".** `HANDOFF.md` §6
carries one-line verdicts; the evidence, the exact rule tested and the
failure modes live here. Every scorer named below is a standalone CLI in the
repo root and re-runs offline from `data/backtest/`.

Last updated: 2026-08-04.

---

## 1. The one surviving edge

**NIFTY (and SENSEX) — d3 band reversal, intraday, buy-side only.**

> ### ⚠️ VOID as of 2026-08-05 — measured on the wrong trigger
>
> Every number in this section describes a **one-candle** rule: a bar pierces
> d3 *and the same bar closes back above it*, enter at that close. Asked
> directly on 2026-08-05, the operator described a **two-candle** rule: a bar
> **touches** d3 (no close-back needed), and entry comes when a **later** bar
> closes above **that bar's high**. Entry is therefore later and higher.
>
> So **72% / +21.0 pts / −20.7 adverse swing are VOID — not disproven.**
> Correctly measured, wrong instrument. The same thing that happened to
> `confirm_score` (HANDOFF §6b). `band_rotation._trigger` still implements the
> old rule, so the pills on the chart do not mark the operator's entries.
>
> The real rule is pre-registered in **§5c** and must be scored before any of
> it is trusted or drawn. Keep this section as the record of what was measured.

The rule, as the data supports it (**the OLD, one-candle trigger — see the
VOID notice above**):

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

## 5d. PRE-REGISTERED — the u3 SELL mirror (written 2026-08-08, UNTESTED)

**Written BEFORE the run. Committed before the run. If this section is edited
after the result is known, the pre-registration is void and the result with
it.**

### Why this is allowed at all, given §5's stop rule

§5 says stop re-cutting `data/backtest/` and pre-register anything new. This
qualifies as new for one specific reason: **C3 rejected upper-band selling on
the OLD one-candle rule.** The §5c two-candle entry is a different trigger, and
moving from one to two candles is exactly the change that turned the buy side
from noise into the one surviving edge. So the mirror on the CURRENT entry has
never been tested.

That is a real distinction, not a loophole. It is also the LAST slice this
line of work gets without new live evidence: if it fails, the sell side stays
built (the operator asked for it over C3 and that stands, CHECKLIST C12) but is
never again presented as anything but a rule they follow.

### The rule under test, exactly

`band_rotation.detect_index_run(bars, side="SELL")` as it shipped 2026-08-08:
a bar's HIGH tags `u3`; that bar becomes the reference; within `RUN_WINDOW`
(10) bars a candle CLOSES below the reference candle's LOW; post-09:25;
first-of-run; stop `level + OPERATOR_STOP_PTS` (20). u3 only, never u2.

**Exits are NOT part of this test.** The operator's short exits were specified
on 2026-08-08 and are unbuilt, and one of their parameters (the CALL-heavy
threshold) is deliberately unanswered. So this scores the same way the BUY side
was scored — a fixed forward horizon with the stop applied — which is what
makes the two numbers comparable at all.

### Method

`run_score.py`'s existing apparatus, unchanged: `HORIZON_BARS` +6m/+15m/+30m,
`_stop_exit`, and the same unconditional control the buy side was measured
against. Favourable for a short means price FELL.

**Primary dataset: NIFTY only** (65 cached sessions, 18 signals emitted).
SENSEX and BANKNIFTY are reported but do NOT decide the verdict — picking the
best of three indices after the fact is the multiple-comparison fishing that
produced the two findings §5 says evaporated.

### The bar, stated before the numbers exist

**PASS** requires ALL THREE at +30m on NIFTY:
1. hit rate **≥ 60%**
2. median move **≥ +10 pts** in the trade's favour
3. median **≥ +10 pts above the unconditional control's median**

**FAIL** is anything else. There is no "promising", no "directionally right",
and no re-cutting to a different horizon to find a number that passes.

**INCONCLUSIVE** if n < 15 — the buy side's own verdict rests on n=18/19, and
anything thinner is not evidence either way.

### ⚠️ MEASURED ON THE MANAGEMENT THE OPERATOR DOES NOT USE (noticed 2026-08-08)

The bar below is written at a **fixed +30m horizon**. §1's own management table
lists that as *"no stop, fixed 30-min exit"* — one of four managements measured,
and **not the one adopted**. The adopted management is *"hold the stop until
VWAP, then trail band-to-band; from +2σ, 15 pts under the high. Flat by 15:15."*
The operator had refused the 30-minute exit before; it was never written down,
which is why it came back.

So this result says: **the sell mirror fails under a management the operator
does not trade.** It is untested under the one they do. Same standing as §1's
VOID notice — correctly measured, wrong thing measured.

**It is deliberately NOT being re-run.** §5's stop rule forbids re-cutting
`data/backtest/` until a number agrees with us, and "the criterion was wrong so
let me try again" is exactly how that starts. The sell side keeps shipping as
it is — drawn because the operator asked, labelled as carrying no score. The
real management gets measured on LIVE data (§5e), where it cannot be re-cut.

### RESULT — run 2026-08-08. **FAILED**, and narrowly, which is the point.

NIFTY, 65 sessions, 18 signals. The BUY side was run through the same harness
in the same pass as a control on the harness itself, and it reproduced the
record's 68.4% at +30m — so the apparatus was working when it returned this.

| horizon | SELL hit | SELL med | control med | edge |
|---|---|---|---|---|
| +6m | 33.3% | −3.10 | −0.00 | −3.10 |
| +15m | 55.6% | +4.25 | −0.00 | +4.25 |
| **+30m** | **55.6%** | **+9.35** | −0.00 | **+9.35** |

Against the bar written before the run:

| | required | got | |
|---|---|---|---|
| hit @+30m | ≥ 60% | 55.6% | ✗ |
| median @+30m | ≥ +10 | +9.35 | ✗ |
| edge over control | ≥ +10 | +9.35 | ✗ |

n=18, so not inconclusive. **All three missed. FAIL.**

Two of them missed by almost nothing — 4.4 points of hit rate and 0.65 of a
point of median. That is precisely the shape of result the pre-registration
exists to handle, and the criterion said in advance: no "promising", no
"directionally right", no re-cutting to another horizon. It fails.

**One honest observation that is NOT a rescue.** The sell curve has the same
signature as the buy: negative at +6m, positive by +30m. The trade goes against
you first and then works — the property §1 already records for the buy side.
That makes the mirror behave like a mirror, which is a statement about the
DETECTOR being correct, not about the edge existing.

**BANKNIFTY inverts again, and it is still not evidence.** Its SELL ran 60% /
+25.00 at +30m while its BUY ran 37.5% / −75.90, consistent with C4's finding
that BANKNIFTY runs the other way. n=5. The pre-registration excluded
BANKNIFTY from the verdict for exactly this reason, and n=5 is under the
inconclusive line anyway. **Do not act on it and do not re-cut to chase it.**

**SENSEX is unreadable here, not negative.** Every median came back exactly
0.00 across both sides and all three horizons. That is a data artefact, not a
result; the SENSEX cache needs looking at before any SENSEX number from this
harness is quoted.

### What this changes

Nothing about what ships. The operator asked for the sell signal over C3's
rejection on 2026-08-08 and that stands (C12). It draws, and it is labelled as
carrying no score — and that label is now backed by a test rather than only by
an old verdict on a different entry.

**This was the last slice.** §5's stop rule applies with full force now: no
further re-cutting of `data/backtest/` on the sell side. The only route to a
different answer is `trigger_log.py` collecting live fires, which needs a
server restart to activate.

### What a PASS would and would not mean

It would NOT overturn C3. C3 measured a different entry across five datasets,
and one passing test on 65 NIFTY sessions does not retire that. A PASS means
"worth collecting live triggers on", which is `trigger_log.py`'s job — not
"the sell side is now an edge".

A FAIL changes nothing about what ships. The operator asked for the signal
over a rejection already.

---

## 5e. PRE-REGISTERED — the LIVE forward test, both sides (written 2026-08-08)

**Written before a single row exists.** The operator: *"lets make it and we
will score everything from monday onwards buy and sell signal"*.

This is the clean kind of test. §5 closed `data/backtest/` to further slicing;
forward-collected triggers are the one route it leaves open, and a forward test
cannot be re-cut until it agrees with you.

### What is being collected

`trigger_log.py`, from the first session after 2026-08-08. Every fire of BOTH
sides, with the bar's gamma/ctx and the chain's OI strength at that moment.

**It needs a SERVER RESTART to activate.** Until that happens nothing is
collected and this section is measuring nothing.

### One thing had to be fixed first, and it was load-bearing

Until 2026-08-08 the logger read `rotation` — §1's ONE-CANDLE rule, which marks
the d3 TOUCH and which this file marks VOID. It never read `rotation_run`, the
two-candle ENTRY the chart actually draws, because the logger was written
2026-08-04 and `rotation_run` arrived on the 07th.

So a forward score started before this fix would have measured **a different
rule from the one on screen**, and nothing would have said so. The 256 rows
already on disk are from that path: they are **quarantined by `rule != "5c"`,
not deleted** — their gamma/ctx/OI context is real, only the rule is wrong.

**They do not count toward anything below. The sample starts at zero.**

### How it is measured — NOT on a clock

**Corrected 2026-08-08 after the operator caught it.** The first draft of this
section scored at a fixed +30m. That is §1's *"no stop, fixed 30-min exit"* —
a management that was measured and **not adopted**, and one the operator had
already refused. Scoring live trades on it would measure a trade they never
take.

The forward score uses the **adopted management**: hold the stop until VWAP,
then trail band-to-band; from +2σ, 15 pts under the high; flat by 15:15. On the
sell side, the operator's own exits
(`docs/superpowers/specs/2026-08-08-operator-short-exit.md`) once their two open
parameters are answered.

**This is why the logger captures the SIGNAL, not an outcome.** `trigger_log`
records the fire and its context; the bars afterwards are already cached, so
the exit can be scored later under whatever the settled rule is — and re-scored
if it changes, without throwing away a single collected signal. Nothing about
the exit has to be committed to now, which is the whole point.

### The bar — **OWED BY THE OPERATOR, do not invent it**

The pass criterion must be stated in the terms of the real management —
points per trade, hit rate, or a ratio against the 20-point stop — and that is
the operator's call. The previous draft picked "≥60% / ≥+10 pts at +30m"
without asking, which is the same mistake in a different place.

**Do not read the result before n ≥ 15 on that side.** This is the rule that
matters most in a forward test and the easiest to break: stopping to look the
moment the number is flattering, and calling that the answer, is how a live
sample manufactures the same false positive §5 was written about. n < 15 is
INCONCLUSIVE and gets no verdict, favourable or not.

### What each outcome means

- **BUY passes** — expected; it confirms live what 65 cached sessions already
  said. It is not new information, it is the control on the whole exercise.
  If the BUY side FAILS live, that is the most important result this project
  could produce and the cached verdict has to be re-opened.
- **SELL passes** — the backtest FAILED it narrowly on 2026-08-08 (55.6% /
  +9.35 against 60% / +10). A live pass would mean the two disagree, and the
  answer then is more data, not picking the friendlier one.
- **SELL fails** — it stays exactly as it ships now: drawn because the operator
  asked for it over C3, labelled as carrying no score.

### Not covered by this test

The operator's short EXIT rules (`docs/superpowers/specs/2026-08-08-operator-short-exit.md`)
are unbuilt and two of their parameters are unanswered. This measures ENTRIES
at a fixed horizon, which is the only thing comparable to the buy side's own
scoring. Exits will need their own pre-registration.

---

## 5f. OBSERVATION — both sides under the ADOPTED management (2026-08-08)

**This is an OBSERVATION, not a test.** No pass criterion was set before the
run; the operator asked to see raw numbers first and was told, in the question
they answered, that this is the exact shape §5's stop rule exists to guard
against. It is recorded so nobody later mistakes it for a scored verdict.

Management = `patient="hold"` (hold the stop until VWAP, then trail
band-to-band) — the adopted arm, not the fixed 30-minute exit C13 refuses.
`trail_score.simulate` was made side-aware for this; the BUY path was proved
byte-identical against a baseline captured before the edit (md5
`4a24a97fcd5fb7d6b1846535e9a65bd1`).

NIFTY, 65 cached sessions:

| | n | mean | median | hit | losers |
|---|---|---|---|---|---|
| BUY d3 | 19 | **+0.32** | **+6.90** | 63.2% | 7/19 |
| SELL u3 | 18 | **+10.18** | **−0.75** | 44.4% | 10/18 |

### The mean is a lie on BOTH sides, and that is the finding

| strip the top… | BUY mean | BUY med | SELL mean | SELL med |
|---|---|---|---|---|
| — | +0.32 | +6.90 | +10.18 | −0.75 |
| 1 | −6.99 | +5.05 | +0.65 | −1.00 |
| 2 | −10.09 | +3.20 | −6.99 | −1.10 |
| 3 | −12.72 | +2.05 | −9.37 | −1.20 |

BUY's top 2 trades are +177.5 against a **+6.0 net** — the other 17 sum to
−171.5. SELL's top 2 are +295.1 against a **+183.3 net** — the other 16 sum to
−111.8. Neither side's mean survives its own tail at n≈19.

**The two differ in SHAPE, not size, and that is what matters:**

- **BUY has a centre.** 63% of trades win, the median is +6.90 and it HOLDS as
  winners are stripped (+5.05, +3.20, +2.05). Its mean is eaten by a few large
  losses (−87.5, −69.3, −63.5). The case for it rests on median and hit rate —
  **not on the mean**, which is barely above zero.
- **SELL has no centre.** The median is NEGATIVE and gets worse as winners are
  stripped (−1.00, −1.10, −1.20), with 44.4% hit. Mostly small losses,
  occasionally a jackpot (+172.2 on 2026-06-08, +122.9 on 2026-04-29). Reading
  its higher mean as "better than the buy" is exactly the misread this table
  exists to prevent.

### What this does NOT establish

n=18/19 is far too small to lean on tail-driven means, and no bar was set
beforehand, so nothing here passes or fails anything. It does not overturn C3,
does not promote the sell side, and does not demote the buy side.

**One thing it does flag for the buy side**, and it is new: §1's management
table (+4.8 mean / 56% hit) was measured on the VOID one-candle trigger. On the
CURRENT §5c entries under the same adopted management the mean is **+0.32**.
The scored edge's case is median-and-hit-rate, not mean, and any surface that
quotes a mean for it is quoting the wrong statistic.

**Nothing was re-cut to reach these numbers** — one run, both sides, all three
management arms, reported whole. The verdict route remains live collection
(§5e), where a number cannot be re-cut until it agrees.

---

## 6. Known gap the code cannot yet see

## 5c. PRE-REGISTERED — the operator's ACTUAL d3 rule (written 2026-08-05, UNTESTED)

Registered **before** any scoring run, per §5. **Nothing below is a result.**

**Why this exists.** §1's rule is not the rule the operator trades. `_trigger`
(`band_rotation.py:275`) implements a one-candle setup; the operator described a
two-candle one. §1 is therefore VOID, and this is what must be scored.

**The rule, as the operator specified it.** NIFTY index, 3-min bars, after
**09:25**, **d3 only**:

1. **ARM** — a candle whose **low touches or pierces d3**. *No close-back
   requirement.* That candle is the **reference**; remember its **high**.
2. **RE-ARM** — a later candle printing a **new lower low** becomes the new
   reference. Falling lows collapse into one setup; they do not stack.
3. **TRIGGER** — a candle **closes above the reference candle's high**.
   Entry at **that candle's close**.
4. **EXPIRY** — no trigger within **10 candles (30 min)** → setup cancels.
   *(Assumption, flagged: a new lower low restarts this countdown.)*
5. **STOP** — d3 − 20 pts.
6. **MANAGE** — unchanged from §1: hold the stop until VWAP; past VWAP trail
   band-to-band; from +2σ, 15 pts under the high; flat by 15:15.
7. **RE-FIRE** — after an entry: if **stopped out**, the next setup may arm
   immediately; otherwise **not until VWAP is touched**.

**Predictions, committed in advance:**

1. It fires **less often** than the old rule on the same sessions — a
   close-above-the-high is a stricter second condition than a same-bar reclaim.
2. Its **mean MAE is smaller in magnitude than −20.7**, because entry is later
   and higher.
3. Therefore the **20-pt stop is no longer sized to the adverse swing** and is
   probably loose. (Widening or tightening it stays a risk decision for the
   operator — this predicts the measurement, not the choice.)
4. Hit rate at +30m is **materially above** the ~50% / +0.3 pt control.

**Falsifier:** hit rate at +30m at or below **~55%**, **or** a median at or
below the control, **or** the result collapsing once the single best trade is
dropped (§5 lesson 2).

**Provenance and hazards — record these now, not after the number.**

- The rule was **not** mined from `data/backtest/`; it came from the operator's
  own description. That makes this a legitimate first test rather than another
  slice, so §5's stop-rule is satisfied.
- It is **one** rule with **one** parameter set. Do **not** grid-search the
  10-candle window, the 20-pt stop, or the band. If N is ever varied, **every**
  variant must be reported, never the best one.
- 2026-08-04 sits in the cache and was on screen while the rule was being
  specified. The rule was not derived from it, so it is not disqualified — but
  it is not independent evidence either.

**Data:** NIFTY 3-min bars via `squeeze_score.load` (`vwap_bands` → `resample(3)`
— that order is load-bearing: 0.972 vs 0.948 reversed).

**Scorer:** `run_score.py`, head-to-head against the old rule on identical
sessions, with a real stop applied (`rotation_score.py` is deliberately
stop-free).

### RESULT — run 2026-08-05. NOT falsified, but not for the predicted reason.

`run_score.py` reproduces §1's headline exactly on the old rule's own
population (d3 BUY, first-of-run, post-09:25: **n=18, 72.2%, med +21.00**),
which is what validates the scorer before anything new is read off it.

**NIFTY, 65 cached sessions, +30m:**

| | OLD d3 BUY (§1) | **NEW two-candle** | control |
|---|---|---|---|
| trades | 18 (0.28/session) | **19 (0.29/session)** | — |
| hit | 72.2% | **68.4%** | 49.5% |
| median | +21.00 | **+12.80** | +0.00 |
| MAE median | −22.20 | **−13.90** | — |
| **with the 20-pt stop** | 61.1%, med +15.65 | **68.4%, med +12.80** | — |
| **stopped out** | 5/18 = **27.8%** | **3/19 = 15.8%** | — |
| less the best trade | 70.6%, +18.70 | **66.7%, +11.40** | — |

**Falsifier not triggered:** 68.4% > 55%, median +12.80 > control, and it
survives dropping the single best trade. **The edge is real on NIFTY.**

**Prediction scorecard, scored honestly:**

1. *"fires less often"* — **WRONG.** 19 vs 18. Essentially identical frequency.
   The reasoning (a stricter second condition) was sound but the arming
   condition is looser (a touch, not a pierce-and-reclaim), and the two cancel.
2. *"MAE smaller than −20.7"* — **MIXED.** Median −13.90 (smaller), mean −29.97
   (larger). Outlier-driven; the median is the honest read of "typical".
3. *"the 20-pt stop is loose"* — **SUPPORTED**, by the halved stop-out rate.
4. *"hit materially above control"* — **CONFIRMED**, 68.4% vs 49.5%.

**The finding that matters, and it is not the headline.** On raw forward move
the old rule looks *better* (72.2% / +21.00 vs 68.4% / +12.80). **With the stop
applied — which is how it is actually traded — the new rule wins:** 68.4% vs
61.1%, and it is stopped out **half as often** (15.8% vs 27.8%). Entering later
and higher buys a trade that survives. The operator's rule trades median gain
for durability, which is exactly the trade a real stop rewards.

**Corroborating detail:** the new rule's **+6m is negative** (42.1%, med −2.70)
and only turns at +15m. The trade goes against you first and then works — which
is independent support for §1's measured management finding that moving to
breakeven costs ~13 pts/trade. Do not move the stop early.

**Where it fails, as expected.** BANKNIFTY: 37.5% hit, med −75.90 (n=8) — and
the old rule fails there too (14.3%, n=7). §3's regime map holds; BANKNIFTY
still inverts. SENSEX agrees with NIFTY (58.3%, med +23.28, **0/12 stopped
out**, n=12), though its own control is an odd 42% and the old rule's n=4 there
is not readable.

**Caveats that must travel with these numbers.**
- **n=19.** That is ~1.4 signals a week, matching the operator's own "1–2 per
  week" — but it is a small sample and one bad month would move it.
- Old and new were measured on the **same 65 sessions**, so they are not
  independent samples; the comparison is paired, the significance is not.
- Nothing here tests the **option-leg expression**. The operator trades
  premium-matched legs (ATM when its premium is > ₹100, else strikes > ₹100 on
  both sides), and this scores the **index** only.
### Management, re-run on the new entries (`trail_score.py`, 2026-08-05)

The `"hold"` arm existed in `simulate` from the start but was never wired into
`main` — so the operator's OWN chosen management was the one arm never printed.
Now wired, and run against both rules' entries.

**Pooled d3, all three indices** (pooling is a warning, not a result):

| entries | arm | mean | **median** | **hit** | scratches |
|---|---|---|---|---|---|
| OLD one-candle (n=29) | ladder | +3.6 | −9.0 | 41% | 0 |
| | patient | +0.1 | −9.0 | 28% | **6** |
| | hold | +4.5 | −15.2 | 48% | 0 |
| **NEW two-candle (n=39)** | ladder | +33.2 | +1.8 | 54% | 0 |
| | patient | +32.3 | +0.9 | 51% | 0 |
| | **hold** | +31.9 | **+6.9** | **59%** | 0 |

**Two things fall out, and they point the same way as §1's original management
finding rather than against it.**

1. **The new entries are better under EVERY arm.** Every OLD median is
   negative (−9.0 / −9.0 / −15.2); every NEW median is positive
   (+1.8 / +0.9 / +6.9). The entry rule, not the management, is what moved.
2. **`hold` buys consistency, not size.** It has the best hit rate (59% vs 54%
   / 51%) and much the best median (+6.9 vs +1.8 / +0.9), but the *lowest*
   mean (+31.9). Leaving the stop alone until VWAP wins more trades and gives
   up some tail. On NIFTY alone (n=19) the same shape: hold 63% hit and +6.9
   median against ladder's 58% and +3.2, while ladder's mean is higher (+4.8
   vs +0.3).

**`patient` produced 6 breakeven scratches on the old d3 entries and `hold`
produced none** — a direct, independent replay of §1's measured "moving to
breakeven costs ~13 pts/trade". The operator's instinct to leave the stop alone
is supported by a second, separate measurement.

Also visible: `hold`'s median exit rung is **u1** on NIFTY and SENSEX where
`patient` stops at **vwap**. Not touching the stop lets the runners run.

BANKNIFTY is negative on every arm (hold worst, −74.4, n=8). §3's regime map
holds.

**Still not measured:** the option-leg expression. Every number above is the
index. The operator trades premium-matched legs (ATM when its premium is
> ₹100, else strikes > ₹100 on both sides), and that has never been scored.

---

## 6. VERDICT — v3's charting foundation (2026-08-05)

The throwaway `/proto` spike ran against live bars and the 04-Aug fixture.
**Decision: keep `candl`.** Not because lightweight-charts failed — it passed
all three pre-registered proofs — but because the rubric asked the wrong
question.

### The three proofs, scored against the rubric written before the run

| proof | verdict | evidence |
|---|---|---|
| 1 · filled σ envelope | **PASS** | `drawRibbon` reused with **zero body changes** — `diff` vs `LevelsOverlay.ts:227-271` is exactly **one line** (`conv: Converters` → `conv: Conv`). Five annuli, distinct hues. `autoscaleInfo` exists in v5.2.0 and keeps ±3σ in view. |
| 2 · synced OI pane | **PASS** | `chart.addSeries(LineSeries, {}, 1)` creates the pane outright: `panes()` → 2, series `[2,1]`, 385 points, shared time axis, **zero glue code**. |
| 3 · rotation pill | **PASS** | Anchored by `logicalToCoordinate` + `priceToCoordinate`; 21 pills on their own candles at their own σ levels. **No rAF loop and no frame-skip signature needed** — the chart's own paint drives it. |
| time axis | **PASS** | `LWC holds 2026-08-04T14:51:00.000Z` for the bar the payload calls `14:51`. Machine-timezone independent (verified at offsets 0 and −330). |
| gates | **PASS** | tsc 0 · build 0 · pytest 278. |

### Why the verdict is still "keep candl"

**Drawing tools — the axis the rubric never covered.** `candl` ships **61**
tools with a full lifecycle API (`setActiveTool` / `setDrawings` /
`onDrawingsChange` / `onSelectionChange` / `setMagnet`). lightweight-charts
ships **zero**, by design — every tool would be hand-built as a primitive, with
hit-testing, drag handles, selection, persistence and undo.

The operator trades ICT/SMC. Trendlines, channels, fibs and boxes are the
method, not decoration. Verified working on 2026-08-05 via `ProtoDraw.tsx`.

**The thing nobody had noticed:** ui-v2 turns **none** of those 61 on. The only
app-side reference to the entire drawings module is `LevelsOverlay.ts:5`
importing the `Converters` *type*. The capability has been one toolbar away the
whole time — which is why the operator could never draw on their own chart.

### What the spike genuinely established (worth keeping)

- **`LevelsOverlay` was never candl-coupled.** Its whole runtime surface is two
  calls (`getMainConverters`, `getMainPaneRect`) and two methods off them. The
  migration was always cheap — it simply is not worth making.
- The **series-primitive + 2-method adapter** pattern works, if this is ever
  revisited. Use `logicalToCoordinate`, **not** `timeToCoordinate`: the latter
  returns null off-screen and `drawRibbon` treats non-finite as a run break, so
  the envelope would fragment under pan.
- lightweight-charts renders **UTC only**. Bars carry `"HH:MM"` IST and no
  epoch, so stamps must be built as *the epoch whose UTC clock is the IST wall
  clock* (`protoTime.ts`). Naive `dayBase()/1000` puts the axis 5:30 out.

### Costs that going LWC would have had to pay

61 drawing tools · the replay cursor (`candl` has native `setReplayCursor`
driven at 25× / 40 ms; LWC has no equivalent) · an OHLC legend (LWC draws none)
· `LegChart`, never proven · +55 kB gzip.

### Not measured — do not read this verdict as covering them

- The **replay cursor** port (the operator scoped the spike to three proofs).
- **`LegChart`**: its σ bands are plain *lines*, plus seven pivot lines, its own
  OI pane and a `map[]` for skipped bars. Three passing proofs say nothing
  about it.
- **50 of the 61** drawing tools. Eleven were exercised.

---

## 7. Known gap the code cannot yet see

The operator reads *"is price rejecting the band or walking along it"* off the
chart in one second (Kite screenshots, RELIANCE 31-Jul and 3-Aug, 2026-08-04).
Nothing in the repo measures band-riding vs band-rejection. The one attempt
(§2.2) was falsified, but the attempt was flawed rather than the idea being
disproven. **This is the most promising un-encoded piece of the operator's
read** — if it is retried, it must avoid a lookback that silently excludes the
morning, and it must be pre-registered.
