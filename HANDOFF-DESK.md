# The desk — handoff

**Written 2026-08-21, after the first live session** (842 tests then; the
suite is **1041** as of 2026-08-25 — `context/HANDOFF.md` holds the running
count and the day-by-day history). **Sections are appended, not rewritten:
§8d the war map, §8f the paper desk, §8g the seller pivot + the
short-variance book — read §8g first if you are picking this up cold, it is
the current shape of the screen and the newest module.** Branch
`feature/operator-objects`.

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
| `desk_log.py` | **New 2026-08-22.** The record: a surface forward log (`data/surface/surface_<day>.jsonl`, one line per successful fit) and a desk verdict-TRANSITION log (`data/desk_log.jsonl` — gear/conviction/deployable, only on change). Both gated to 09:15-15:30 IST, both fail-soft like `senses.py`. This is §8's item 7 — direction.py's own 30-session kill condition finally has something to be judged against. |

### The tape layer — 10 detectors, built earlier

`sweep`, `absorption`, `depth_pull`, `pools`, `fuse`, `regime`, `chainside`,
`trapped_inventory`, `drag`, `senses`. (`forcing.py` was deleted Phase 0 —
see HANDOFF-OPERATOR.md §1 for why.)

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

## 8c. Phase 4 — the record a desk keeps + instrumentation (2026-08-22)

New module `desk_log.py`, pure stdlib, no operator-layer imports of its own —
it only formats and writes what `server.py` already computed, same division
of labour as `senses.py`. Two forward logs, both TRANSITIONS/FITS ONLY, never
an outcome or a hit rate:

- **The surface log** (`data/surface/surface_<day>.jsonl`) — `{ts, idx, a, b,
  c, rmse, f_src, expiry, n_points}`, one line per successful fit. A failed
  fit logs nothing, never a fabricated coefficient.
- **The desk verdict-transition log** (`data/desk_log.jsonl`, one running
  file, not per-day) — `{ts, idx, field, from, to, detail}` for `gear`,
  `conviction` and `deployable` (the desk's own `best` candidate name),
  written ONLY when the value actually changes from the previous reading.
  This is **§8 item 7**: `direction.py`'s own declared 30-session kill
  condition had nothing to be judged against until this existed.

Both gated to 09:15-15:30 IST Mon-Fri, and the gate is an injectable `now`
parameter rather than a wall-clock read baked into the function — a test (or
a --mock-chain run at any hour) can drive the real write path with a fixed
in-hours timestamp.

**Where it hooks in.** The trigger is the senses loop's own "new chain
payload per index" detection — the same point that already feeds
`chainside.on_snapshot` and `drag.Board`. `_log_chain_pace` (server.py) runs
there: fits the surface, computes the desk decision + direction view exactly
as `/api/desk` does, diffs the result against a per-index state cache, and
writes only what changed. Because the trigger is the chain refresh (~10s per
index), `desk.decide` — real work, a whole candidate catalog — never runs
against the loop's 0.5s tick budget.

**The feed gate moved.** Until this task, a missing/disconnected book feed
skipped the WHOLE senses-loop tick, including the chain-payload half that
needs no feed at all (`chainside`, `drag.Board`, and now `desk_log`). That
also meant `--mock-chain` — which never opens a feed — could not exercise
5a/5b even though nothing they do depends on one. The feed check now only
gates the near-ATM book-detector pass; the chain half, and the senses thread
itself, run under `--mock-chain` too. Verified live on a throwaway port
(8877, not the sandbox on 8765): the loop ran clean, `/api/health.latency`
accumulated real samples, and — correctly, since it was a Saturday —
`data/surface/` and `data/desk_log.jsonl` stayed empty, the market-hours gate
doing exactly what it should.

**5d — latency.** Two `deque(maxlen=500)` ring buffers, `senses_ms` (timed
around each senses-loop pass) and `http_ms` (timed by overriding
`Handler.handle_one_request` — the one seam every GET/POST/OPTIONS already
passes through in `http.server`, chosen specifically so `do_GET`/`do_POST`
themselves stay un-decorated: `test_upstox_only.py` introspects
`inspect.getsource(server.Handler.do_POST)`, which a decorator would have
broken for a reason having nothing to do with what that test checks).
`/api/health.latency` publishes `{p50, p99, n}` per bucket once
`MIN_LAT_SAMPLES` (5) exist, else `{p50: None, p99: None, n, why}` — never a
zero standing in for "not enough data yet."

**5e — the two `pools.orders_for` defects that gate the Kite bridge**, both
reproduced against the old code first, then fixed:

1. **Touch-only coincidence.** A single candidate book whose ONLY agreement
   with the Upstox ladder was the touch price used to be accepted once it
   was the sole match — but deep OTM books routinely sit at the exchange's
   minimum tick (0.05/0.10) by coincidence, not because they are the same
   instrument. Being the sole candidate handed over is not the same as being
   confirmed. A match with more levels to check must now be confirmed on at
   least one level beyond the touch, or it is refused as a coincidence.
2. **Index-carry misalignment.** `orders_for` used to return Kite's own
   list, in Kite's own order — `map_book` then paired `counts[i]` with
   `ladder[i]` by POSITION, which silently misattributes a count the moment
   the two books disagree by even one level (a stale Kite quote, a level
   Upstox has that Kite does not). `orders_for` now aligns every count to
   the UPSTOX ladder's own levels BY PRICE (`pools._by_price`, greedy
   nearest-first, each Kite level claimed once) before returning it, so
   `map_book`'s existing `counts[i]` already means "this ladder level," with
   no coordination required on `map_book`'s side.

Files touched: `desk_log.py` (new), `server.py` (`_senses_loop` restructured,
`_log_chain_pace` new, latency ring buffers + `Handler.handle_one_request`,
`/api/health.latency`), `eod_capture.py` (`capture_desk_record`, 5c),
`pools.py` (`_by_price`, `orders_for` rewritten), `.gitignore`
(`data/surface/`, `data/desk_log.jsonl`). New tests: `test_desk_log.py`
(16), plus additions to `test_senses_api.py` (5), `test_pools.py` (2 new +
4 rewritten for price-based alignment) and `test_eod_capture.py` (3). No
order path touched; no backtest; no hit rate anywhere in either new log.

## 8d. The OI war map (2026-08-22)

Born from the operator's own thesis, stated 2026-08-22 (memory note
`oi-liquidity-hunt-thesis`; plan in the "OI War Map" artifact): smart money
walks price to a retail reaction point, lets positions load during the dwell,
uses the stops beyond it as liquidity, and runs the move to the next point.
The gap it closes, exactly: nothing in this stack knew what PDH was, nothing
remembered a dwell, nothing attributed the driver, and no screen drew the
battlefield. Everything below is SHADOW, forward-logged, gates nothing.

**Six objects, five new modules plus an orchestrator:**

| module | answers | tag |
|---|---|---|
| `levels.py` | where are the reaction points (PDH/PDL/PWH/PWL/OPEN/rounds/max-pain/flip/walls), each with FRAME (index vs chain) and stable-vs-drifting | [M] mostly |
| `dwell.py` | is price parked at a level while positions load -- OI added per side, buyers paying up | [M] arithmetic, [I] attribution |
| `hunt.py` | which side pays more to run: fuel (OI x pain added) itemized per runway to the next level, plus inferred stop zones | [I] end to end |
| `sequence.py` | the playbook per stable level: APPROACH -> DWELL -> BREAK/REJECT -> RUN -> HIT/FAILED, forward-logged | [I] |
| `driver.py` | futures-led vs option-led intraday [I]; NSE participant-wise OI EOD (the only true Client/Pro split, one day lagged) | [I] / [M] |
| `warmap.py` | composition only, one board per index; `state()` serves the last chain-pace assembly | -- |

**Wiring:** fed in `_senses_loop`'s chain-payload block (same lock, same
snapshot as `chainside`/`drag`), served at `/api/warmap`. The ladder screen
sits on `/desk.html` above the trending-OI table: levels + OI heat (CE left,
PE right, fresh brighter, underwater outlined) + stop zones + spot + the two
runways, with the dwell/driver/participant/playbook readout beside it. Two
new alerts ride the existing tone layer: DWELL forming at a named level, and
BREAK running with a named target.

**Forward log:** `data/warmap/warmap_<day>.jsonl` -- its OWN population,
never pooled with trigger_log/desk_log/senses. Market-hours gated,
injectable clock, fail-soft (the desk_log pattern). Kill conditions are in
each module's docstring, declared at birth; the 30-session clocks start at
the next open.

**Traps found while building, so they are not rediscovered:** the published
chain payload carries `ts` but NOT `sec` (that field dies inside
`chain_live._publish`), so the dwell clock must derive from `ts` --
found because the first mock run showed `dwell: snapshot carries no clock`.
And the percentile-of-zero-in-zeros trap struck twice more: a flat chain's
d_oi=0 ranks 1.00, which would have read "OPTION-LED extreme" on a dead
tape (`driver.py` requires real flow before "hot", and publishes None rather
than a rank when the window held nothing -- chainside's drain_rank rule).

**Not proven yet:** no live session has run through it. The dwell detector,
sequence machines and runway ranking have unit tests plus one mock-server
pass (levels fetched real candles, participant CSV fetched and parsed real
NSE data for 2026-08-21, ladder rendered with zero console errors) -- but
would-a-desk-take-this-trade is Monday's question, not pytest's.

## 8f. The paper desk -- risk core, quoting layer, the tool trading itself (2026-08-23)

Built on the operator's instruction after the "my vision" review: the missing
HALF of the desk (hands, not more eyes), plus a judge -- the tool paper-trades
its own readings at 2 lots, both sides, manages its book, and logs every
decision AND every refusal, so the record decides whether the readings ever
deserve real capital. PAPER FOREVER; deployment is the operator's decision,
made outside the code; the no-order-path law binds it doubly.

**Three modules:**

| module | what it is |
|---|---|
| `book.py` | the risk core: positions, marks (mid-else-ltp, source stated), margin (desk.py's naked-floor model, reused), first-order P&L attribution (delta / vega / theta+gamma residual, [I], refuses partial answers), and **distance-to-forced** -- capital over stressed need (margin x2 + one adverse expected-move on net delta/gamma) as the book's headline number |
| `quoting.py` | the quoting layer: resting orders matched against chain quotes; maker fills only on a real cross, AT our price; taker at the touch; TTL kills stale intent; every fill records maker/taker. **Fill model is [I] and optimistic (front-of-queue), so maker P&L is an UPPER bound -- the caveat travels with every number** |
| `trader.py` | the brain, BOTH sides by the operator's explicit correction: SELL_PIN (post wings beyond the expected move), BUY_CASCADE (take the short-covering scalp while the trapped side drains), DIR_AFTER_GRAB (take the break direction when a dwell resolves BREAK->RUN with a named target), SELL_CREST (post into post-squeeze inflated premium). Single-leg positions only, on purpose. Every entry carries its rule-9 sentence: who is forced, and why |

**Risk before signals:** no new risk when forced_ratio < 1.5 (rule 5 as
software); one position per (strategy, index); MAX_OPEN 2; day-loss cap
flattens the book; no entries after 15:00, square-off 15:18; a strategy
closed on a snapshot cannot re-enter on the same snapshot (the churn guard --
found by a test, a target-exit while the trigger was still live re-bought at
a worse price in the same breath). EVERY refusal is logged with its reason.

**Wiring:** fed at chain pace in `_senses_loop`, outside `_SENSES_LOCK`
(it touches disk), after the war map so it reads this tick's own sequence
state. Served at `/api/paperdesk`; the review panel sits on `/desk.html`
above the war map. Files: `data/paper_desk/state.json` (the book, atomic
rewrite), `trades.jsonl`, `decisions_<day>.jsonl` -- own populations, never
pooled, gitignored.

**Kill condition (declared at birth):** ~30 paper sessions doing no better
than the flat book -- the S5 skip -- and the brain is rewritten or deleted,
not tuned. Its numbers are accounting, never an expectancy claim; the daily
review is the operator's and the reviewer's, not the module's.

**Not proven:** zero live sessions. The strategy thresholds (scalp +25/-15%,
short decay 40%, crest TTL) are the [I] layer -- one build's judgement,
awaiting the record.

## 8g. The seller pivot and the short-variance book (2026-08-25 night)

Two changes on one night, and the second follows from the first.

**The screen stopped leading with an opinion.** The operator rejected the old
desk outright ("data ki boilerplate... sab kuch UNKNOWN... baar baar change
hota rehta h"), and a measurement backed her: `/api/desk`'s answer changed
**4 times in 35 seconds**, 42 times in an hour (DEFERRED 0i). So she ran an
independent-design exercise — two models, no app context, one question:
*what does a zero-cost NIFTY seller actually need on screen every day?* Both
converged, and neither put a BULL/BEAR headline on it. The new screen
(`ui/toolb.html`, pending her final approval to replace `desk.html`) is the
seller's five questions in decision order:

| tile | the question | source |
|---|---|---|
| GATE | am I allowed to sell today at all | IV/RV ratio, expiry flag, VPIN burst, day-type |
| SURVIVAL | how much does a gap hurt, and where is the margin call | paper book greeks + `margin_shift` at ±1/2% + square-off distance |
| AM I BEING PAID | is the insurance expensive right now | `fit.atm_iv` vs `fit.rv5` [M] |
| WHERE AM I | how close is price, in units that mean the same on Monday and Thursday | strike distance in σ of the expected move, delta lamps |
| MONEY GREEKS | what does each risk cost in RUPEES | book greeks, `theta_day_est`, gamma as "the second 100 points" |
| HISAAB | what did today actually pay | fills, refusals, net variance |

Direction, gear, conviction and the 19-structure catalog still exist and are
still honest — they are one collapsed drill-down, "MACHINE KI RAAY [I]",
with their own flip history. **The machinery was never the problem; the
machinery as the headline was.**

**`hedge.py` — the paper book becomes short variance.** Zero cost is not a
discount, it is a different game: a normal retail seller cannot delta-hedge
a strangle (the charges eat the theta), so he prays for a range. She can
hedge for free, which converts the position from *"I hope it stays in the
range"* into **IV sold − RV realized**, where the hedge round-trips ARE the
realized-vol bill. The module hedges the paper option book with PAPER
futures and keeps the ledger that proves or kills the premise.

- **Band 1.0 lot-equivalent** — the hedge instrument is a whole lot, so a
  correction under one lot cannot be expressed; a tighter band churns
  round trips that reduce no risk.
- **Brake 8 hedges/day/index** — deliberately not the human "4"; a
  systematic brake exists to cap a whipsawed loop, not decision fatigue.
  Hitting it stops hedging and logs the refusal loudly.
- **The hedge inventory is kept OUT of `book.Book`** (test-pinned): inside
  it, hedge legs would move `risk()` → `forced_ratio` → the entry gate, and
  a shadow module would be silently steering the live paper desk.
- **EOD flattens the hedge and that flatten does not consume a brake slot** —
  refusing to CLOSE because a counter is full is the worst reading of a risk
  limit; an unflattened hedge is an outright overnight futures position.
- **The ledger** (`data/paper_desk/hedge_<day>.jsonl`, hedge/refusal/daily
  rows, `/api/paperdesk.hedge`): `theta_collected − hedge_cost =
  net_variance`, with the **unhedged overnight gap exposure written into
  every daily row** — hedging does not cover gaps and the record must not
  imply it does.
- **Both optimisms are named, not hidden:** fills assume no slippage and no
  spread, so **hedge cost is a LOWER bound and net_variance an UPPER one**;
  and `theta_collected` sums the marks' `theta_gamma_resid`, which bundles
  gamma — the field says so rather than claiming clean decay. (The separate
  `theta_day_est` is the model number: new Black-76 theta in `gamma.py`,
  derived in its docstring and **verified against finite differences of
  `bs_price`** — a sign error there reads as free money on screen.)

Found on the way in, and worth more than the feature: `book.mark_position`
silently skipped legs whose delta had not arrived, so `net_delta` came back
smaller with no hint it was partial. Harmless while nothing acted on it —
not harmless the moment a futures trade is sized from it. It now publishes
`delta_why`, and **the hedger refuses to hedge while that is non-empty.**

**Not proven:** zero live sessions for any of it. The first is 2026-08-26.
The premise at least has a measured foot to stand on — NIFTY `rv5` read
**8.53%** against an ATM IV of 11–14% the same night, which is the shape the
module needs to be true. One reading is not a record.

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
