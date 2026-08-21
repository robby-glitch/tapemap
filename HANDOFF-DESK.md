# The desk — handoff

**Written 2026-08-21, after the first live session.** Branch
`feature/operator-objects`. 805 tests pass.

This describes what exists, why it is the way it is, and what comes next. Where
a decision has a reason, the reason is written down — so you can weigh it and
change your mind rather than ask. Use your judgement; you do not need
permission to improve this. §7 lists the handful of things worth being slow
about, and each says *why*, not *don't*.

---

## 1. What this is

An **advisory** options desk for Indian index options. It answers two
questions: **which instrument**, and **which structure**. It does not execute,
holds no position limits, and never sees the operator's book — those are hers
and private. That is why every recommendation is self-contained: a whole
structure with its own risk and invalidation, not an adjustment to something
unseen.

The operator trades at prop scale (₹1–10cr), pays **zero brokerage**, has
direct broker access, and **posts rather than crosses** — so the bid-ask is
revenue, not cost, and the only real cost to sell is statutory (~0.14% of
premium). Reasoning that assumes retail friction is wrong here; it was assumed
twice and produced two wrong conclusions.

### The economics everything serves

```
short vol P&L  ≈  premium collected − realised hedging cost
               ≈  ½ · Γ · ( σ²implied − σ²realised )
```

The edge is not directional — direction gets hedged away. The operator's own
"drag number" (33% / 37% / 88%: how little of a paid-for move a buyer actually
collected) is this same quantity seen from the other side of the trade.

---

## 2. Running it

```bash
cd "C:\Users\kaam\Desktop\operator mode\tapemap"; .\stop.bat; .\start-v2.bat
```

- The Upstox token expires **03:30 IST daily**. `start-v2.bat` probes it and
  opens the login only when the probe fails — no login window usually means
  the token is still good, not that something broke.
- Screens: `/desk.html` (the desk), `/console.html` (the tape detectors).
- APIs: `/api/surface`, `/api/desk?capital=<rupees>`, `/api/chain`,
  `/api/senses`, `/api/health`.
- `stop.bat` first matters: `start-v2.bat` reuses a healthy TapeMap already on
  8765, which is how the *other* folder's server stayed up for an hour while
  every new endpoint returned 404.
- The gamma flip needs ~50 seconds of chain history after a restart. Before
  that, `flip_status` reads `NO_CROSSING` for the wrong reason.

---

## 3. What is built

### The measurement layer — the sound part

| module | what it does |
|---|---|
| `surface.py` | Fits the vol smile: vega-weighted quadratic in log-moneyness within ±3 expected moves. Its coefficients **are** the descriptors — `a` = ATM vol, `b` = skew, `c` = convexity. Emits per-point residual and z. |
| `gamma.py` | Black-76: `bs_price`, `implied_vol`, `vega`, `gamma`, `delta`, `gex_profile`. Predates this work. |
| `chain_metrics.py` | Publishes `flip_px`, `flip_status`, `gex_total`, `gex_regime`, `max_pain` under a **`metrics`** key. |
| `desk.py` | The selector: structure legality, risk, margin, score, sizing, net delta. |

### The tape layer — 11 detectors, built earlier

`sweep`, `absorption`, `depth_pull`, `pools`, `fuse`, `regime`, `chainside`,
`trapped_inventory`, `forcing`, `drag`, `senses`.

Built to answer *when is a move coming* — a buyer's question. They are natively
an **adverse-selection layer** for a desk that posts size: a sweep through your
side means you were the liquidity; a pull means the other makers are leaving;
absorption marks a level you can lean on. They forward-log to `data/senses/`
and currently feed nothing that decides.

`drag.py` computes the buyer's tax on real delta and has **no callers**. It is
the most operator-native module here and belongs in whatever P&L attribution
gets built.

---

## 4. Why the selector works the way it does

**Status, never a confidence score.** Each structure is `DEPLOYABLE`,
`STAND_ASIDE`, or `BLOCKED` with the missing input *named*. A confidence number
collapses three different claims — confidence in the fit, in the mispricing
being real, and in the trade making money — into one figure a reader takes as
the third. Only the first is computable with no track record.

**Blocked structures are listed, not hidden.** An absent row reads as "not
considered"; a blocked row with a reason reads as "considered, here is the gap".

**Shape before richness.** A structure must be legal *first* — a strangle's
wings sit outside the expected move and are delta-balanced — and richness picks
among legal strikes. Ranking by residual alone produced a "strangle" with a leg
12 points from spot.

**A z-score says how unusual, never how much.** With a tight fit (rmse 0.08 vol
points), z ≥ 1.5 needs only 0.12 vol points — worth ₹0.23 a unit. So every
mispricing structure also clears an absolute rupee floor (`MIN_EDGE_RS`).

**The score is edge per rupee of margin**, not raw edge. A ₹3/unit edge on a
350-point-wide spread and the same edge on a tight one are not the same trade.

**Every structure reports net delta and a hedge.** A vertical is neutral in
*vol* and emphatically not in *spot* — one live example carried +0.359 delta a
unit. A position whose largest risk goes unnamed is not a recommendation.

**Lot size is measured, not assumed.** Every OI and volume figure is a whole
number of lots expressed in units, so the **GCD across the chain is the lot
size** — 65 / 30 / 20 for NIFTY / BANKNIFTY / SENSEX, confirmed live and by the
operator. It was hardcoded 75/35/20 and wrong, scaling every sizing figure by
~15%. `LOT_SIZE` survives as a fallback only, and a reading that uses it says
`ASSUMED [I]` out loud.

**`NO_CROSSING` is information, not ignorance.** GEX never changing sign means
the whole chain sits on one side of the gear — a stronger statement than a
flip, not a weaker one. Read as UNKNOWN it blocked everything on three indices
at once.

---

## 5. Measured vs inferred

Everything carries `[M]` or `[I]`.

**Measured:** the fitted surface and every residual; the IVs — *cross-checked
against our own Black-76 inversion, 0 disagreements live, so Upstox's IV is
reproducible*; the regime; lot size; OI, volume and quotes.

**Inferred and labelled:** the margin model (**11% of notional per naked leg,
+60% per extra leg — a documented shape, not SPAN**, and every reading says so
in words); the structure choice itself; the fitted curve's functional form.

---

## 6. Not built

- **No direction view.** Nothing computes bullish or bearish, so every
  directional structure is BLOCKED rather than guessed.
- **One expiry at a time**, so no calendars or diagonals.
- **No multi-day history**, so richness is *cross-sectional only* — a point
  against its own curve, never "the surface is rich". This is the biggest gap,
  and it closes itself as the forward log accumulates.
- No position model, no P&L attribution, no paper-trade loop wired up.
- Nothing has a track record. Validation is forward-only.

---

## 7. Things that cost real time to learn

Facts with reasons, so you can decide — not prohibitions.

**`data/trigger_log.jsonl` is the forward record** for the older `5c` and
`zone` strategies and is the one artefact here that cannot be regenerated. The
copy in `new tool nifty` is authoritative; this folder's copy has been written
by a sandbox server and kept out of commits for that reason. Changing how it is
written changes a record that is actively being scored.

**Two folders run the same code.** `new tool nifty` is the original;
`operator mode/tapemap` (this one) is where the desk was built. Both bind 8765.
Check which is serving before concluding anything about an endpoint — a
`/api/health` 200 does not tell you *which* server answered.

**`TZ="Asia/Kolkata"` silently returns UTC in this Git Bash** (no tzdata
installed). The machine's local clock *is* IST. A whole session's reasoning was
built on a 5½-hour error from this. Use `date` plainly, or an explicit offset
in code — `surface.years_to_expiry` does the latter and is correct.

**Backtesting is off the table** by the operator's own decision: she does not
believe an AI can backtest as dynamically as trading demands. Everything is
settled forward instead, roughly a month per verdict, which is why modules
carry kill conditions in their docstrings.

**Hit rates and win rates are not printed.** The §5e pass bar is stated by the
operator *before* the numbers are read, and under 15 per side is inconclusive.
The `5c`, `zone` and legacy populations are three different things; pooling
them makes all three meaningless.

**`scratchpad/desk-mockup.html` is a drawing** — most of its panels are
hand-typed constants. `ui/desk.html` is the real one and takes every number
from the two endpoints.

---

## 8. What to do next

In dependency order. Each is worth doing on its own.

1. **Accumulate multi-day surface history** and rank richness against it. This
   turns "this point is off today's curve" into "this surface is rich" — the
   difference between a relative-value tool and a vol desk. Nothing else
   unlocks as much.
2. **A second expiry** in `surface.read`, which makes calendars and diagonals
   expressible and gives a term-structure read.
3. **SVI or SABR instead of the quadratic.** The quadratic is fine near the
   money and misbehaves at the wings — one junk print once moved fitted
   convexity from 4.0 to 139, which is why the ±3-move window exists. An
   arbitrage-consistent fit would not need the window as a crutch.
4. **Wire the paper loop.** PaperDesk already has a matching engine, an
   automation harness with rails, multi-leg margin, an Indian charge model and
   round-trip stats. Missing: the extension never calls `/api/paper_fill`, and
   `auto.js` trades a buyer's playbook rather than a desk signal.
5. **P&L attribution** — theta earned, vega mark, gamma from hedging, skew. A
   desk that cannot say which of the four made the money cannot repeat it.
   `drag.py` belongs here.
6. **A direction view**, if one can be justified honestly. Half the catalog is
   blocked without it. GEX and max pain are regime and pin reads, not
   direction; treating them as direction would be the error the `[M]`/`[I]`
   discipline exists to prevent.

---

## 9. How this went wrong, so it does not again

Every serious defect this session was found by **live data or an adversarial
reader** — never by the test suite, which passed at every stage.

- 707 tests passed over a thread race, an unbounded POST body, a rank that
  fired on ties, and a dead branch that could never return its own value.
- The tests could not find the nested `metrics` key, the `NO_CROSSING`
  misreading, the one-legged straddle, the negative-edge ranking, the wrong lot
  size, or the unnamed delta. **Live data found all six in one morning.**

A passing suite proves the code does what its author believed. It cannot prove
the belief was right.

The check that matters is not "did the endpoint return 200" but **"would a desk
take this trade?"** Ask that of every output before reporting that anything
works.
