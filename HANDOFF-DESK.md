# The desk — handoff

**Written 2026-08-21, after the first live session.** Branch
`feature/operator-objects`. 842 tests pass.

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
revenue, not cost. Reasoning that assumes retail friction is wrong here; it
was assumed twice and produced two wrong conclusions.

**COSTS ARE NOW ZERO, 2026-08-21.** She moved to a broker on a two-year
arrangement (one-time fee, already paid) with no brokerage, which **rebates the
remaining statutory charges on any position closing at least Rs 1 positive**.
`desk.STATUTORY_PCT` is therefore `0.0`, and `MIN_EDGE_RS` dropped 1.00 → 0.25
with it. Two things follow, and both are written into the code:

- The floor was never a COST floor. It is a SIGNIFICANCE floor and it stays —
  a 16-paise edge is still not a trade. Only the headroom changed.
- The rebate is an **arrangement, not a law**: it has a term, and it is
  conditional on the position finishing positive. `STATUTORY_PCT_IF_CHARGED`
  holds the old 0.0014 so restoring it is an edit, not a rewrite. Note the
  asymmetry the model does not carry — charges come back on winners, not on
  losers — so zero is exactly right for pricing an edge and slightly
  optimistic for pricing a loss. The desk prices edges.

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
  **`/desk.html` was rebuilt 2026-08-21** and is now four things stacked: the
  GEAR (gear + direction + conviction + game + expected move + gamma flip,
  which is the overall market view before any structure), a three-index
  SCANNER answering "which instrument is paying", a CHART column carrying the
  payoff-at-expiry curve and the vol smile, and a RAIL of every structure
  ranked with the blocked ones kept visible behind a disclosure. Two controls:
  capital (a round trip) and **test lots, default 5** (pure display math — she
  is sizing every recommendation at 5 lots while the tool earns trust). Plain
  HTML served straight out of `ui/`; no build step, no framework, no
  dependencies.
- APIs: `/api/surface`, `/api/desk?capital=<rupees>`, `/api/chain`,
  `/api/senses`, `/api/drag`, `/api/health`.
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
| `direction.py` | **New 2026-08-21.** Which way the forced flow points, and how hard. Composition only — no new measurement. Turns `chainside.trapped_side` plus the gear into `BULL`/`BEAR`/`NEUTRAL`/`UNKNOWN`, with a conviction of `FORCED`/`LEANING`/`NONE`. |
| `desk.py` | The selector: structure legality, risk, margin, score, sizing, net delta. |

### The tape layer — 11 detectors, built earlier

`sweep`, `absorption`, `depth_pull`, `pools`, `fuse`, `regime`, `chainside`,
`trapped_inventory`, `forcing`, `drag`, `senses`.

Built to answer *when is a move coming* — a buyer's question. They are natively
an **adverse-selection layer** for a desk that posts size: a sweep through your
side means you were the liquidity; a pull means the other makers are leaving;
absorption marks a level you can lean on. They forward-log to `data/senses/`
and currently feed nothing that decides.

`drag.py` computes the buyer's tax on real delta and **now has its first
caller** (2026-08-22). `drag.Board` anchors one call and one put at the strike
nearest spot on the session's first snapshot and then only watches; the senses
loop feeds it the same chain snapshot `chainside` already gets, and
`/api/drag` publishes it. Whichever way the index goes one of the two legs was
RIGHT, and `between` refuses to speak for the other -- so the reading that
survives is always the correct-side one. That is the number in the operator's
own words: *even getting the right side, the buyer could not make money.*
It still belongs in P&L attribution when that gets built; it is a meter, not a
gate, and gates nothing.

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

- ~~**No direction view.**~~ **CLOSED 2026-08-21** by `direction.py`. The
  mechanism is the operator's own thesis read one step further: a short call
  is in pain when price rises, so a trapped CE side relieves UPWARD. That is a
  statement about who is forced to transact, not a forecast. Eight directional
  structures now build — long call/put, debit verticals, credit verticals, and
  the future itself. **Nothing here has a track record**; the module carries
  its kill condition in its own docstring.
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
6. ~~**A direction view.**~~ **DONE 2026-08-21** — see `direction.py` and §6.
   The warning it was written under still stands and is honoured: GEX and max
   pain are regime and pin reads, NOT direction, and neither is used as one.
   The direction comes from trapped inventory and drain.
7. **Score the direction view forward.** The only thing that can settle
   whether the conviction ladder is real. `FORCED` views should resolve in the
   named direction more often than `LEANING` ones; if after ~30 scored
   sessions neither beats naming no direction at all, the module is deleted
   rather than tuned.

---

## 8b. What an adversarial read found on 2026-08-22

Two Sonnet reviews, one on the engine and one on the screen. Six real defects,
all confirmed by tracing or by reproducing against a cached live chain. The
pattern from §9 held exactly: **the 829-test suite passed through every one of
them.**

- **`chainside` summed drain across BOTH sides** and `trapped_side` was
  computed separately, so `drain=True` meant "something somewhere is leaving".
  `direction.py` printed it as *"the trapped side is actually leaving"* -- a
  receipt sentence the data could not support, which licensed buying
  convexity. Drain is now attributed per side, `drain_other` is published as
  the counter-signal it is, and a far side covering DOWNGRADES the view.
- **The drain Rank was never fed a quiet snapshot** (`rank(x) if x > 0`), so
  the first real covering burst of a session was ranked against an empty
  history and scored 0.5 -- under the 0.90 bar. Drain could barely fire at
  all. It survived because **no test ever asserted `drain is True`**; the only
  drain test asserted a quiet chain does NOT drain, which passes either way.
- **`_view_for` never picked the future.** It filtered on `count("-") <= 1`,
  but `NIFTY-FUT` and `NIFTY-24450CE` both have exactly one hyphen, so the
  filter matched everything and `sorted()` returned a strike leg. Ignition was
  read off a thin single leg -- the volume-scoping trap of
  HANDOFF-OPERATOR §2.6, two lines under a comment citing it.
- **PIN could not name a credit spread `best`.** `want` mapped SELL_PREMIUM to
  `None`, which ranked MISPRICING (edge/margin) against FLOW
  (convexity/margin) on one key, three orders of magnitude apart. Worse, a
  credit spread is deliberately SHORT gamma, so ranking it by convexity meant
  *more short gamma scored better*. Credit verticals are now `REGIME`, ranked
  on the credit they collect.
- **The screen rendered a missing margin as a bold `₹0`** and used the single
  word `UNDEFINED` for both "risk is genuinely unbounded" and "never priced" --
  the exact collapse the house rules forbid, in the state the screen is in
  five days a week.
- **The empty-state copy was gated so it could not appear in the empty state**
  (`live` counted STAND_ASIDE rows), and the 5s poll destroyed focus, rail
  scroll and any opened blocked-list disclosure on every cycle.

Also fixed: light theme was unreachable (a dark-in-dark media block), the
payoff footer claimed the curve "continues" for DEFINED-risk structures whose
own panel said the loss was capped, and two money formatters disagreed on sign
placement.

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
