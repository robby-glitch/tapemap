# TapeMap — start here

**Last verified: 2026-08-22.** Every number below was measured on that date, not
remembered. If you are an AI or a person picking this project up, read this file
to the end before touching anything. It exists because handovers kept starting
from stale assumptions and re-doing work that is finished, dead, or forbidden.

---

## 0. The five things people get wrong

Read these first. Each one has cost real time.

1. **This is an UPSTOX project, not a Dhan project.** Dhan's Data API lapsed
   **2026-08-05**. Live data — index futures, the option chain, IV and greeks —
   comes from **Upstox**, over a websocket, on a **daily OAuth token**. Dhan code
   is still in the tree (`dhan_fetch.py`, the `_broker()` switch) as a documented
   fallback and for historical tests. Do not "fix" the project back onto Dhan,
   and do not read Dhan's presence as the live path.
2. **Do not run new backtests. Do not slice the cache looking for edges.**
   `context/research-findings.md` §5 is a **stop rule**, agreed with the
   operator: nine hypotheses were tested and killed, and further re-cutting of
   the same data produces noise, not knowledge. The one live question is
   answered by **forward** collection, which is already running. Filling
   outcomes on rows that were logged forward is allowed; searching new
   hypotheses out of the cache is not.
3. **The setup is a ZONE, not a line.** The operator trades the sky-blue
   2σ→3σ shading on their own Kite chart: **d2→d3 is the buy zone, u2→u3 is the
   sell zone. Reaching d2 IS the event**; d3 is only the far edge. **3-minute is
   the canonical interval.** Any earlier note implying the d3 line alone is the
   trigger describes a superseded reading.
4. **The tool's σ bands are WIDER than the operator's Kite bands** (ratio
   1.02–1.08). Cause is proven (granularity — bands computed on 1-minute and
   sampled into the display bucket, Kite computes on 3-minute) and the operator
   **decided not to fix it**. The error is **false-negative only**, so **every
   signal count this tool produces is a floor, not a total.** If the operator
   says "it poked the blue and nothing fired", believe them.
5. **`exit_why` is a re-fire lock, not a trade exit.** It marks when the
   detector may arm again. The operator trails their own stop; the tool does not
   model their exit.

---

## 1. What this tool is

A local, single-operator trading instrument for **intraday index options** on
NSE/BSE (NIFTY, BANKNIFTY, SENSEX). It is not a product, has no users but one,
and places **no orders** anywhere.

**IT IS NOW TWO INSTRUMENTS SHARING ONE SERVER, and confusing them is the
fastest way to waste a session.** They were built months apart, for opposite
sides of the same trade, and neither supersedes the other:

| | THE TAPE (older) | THE DESK (newer) |
|---|---|---|
| question | *when is a move coming* | *which instrument, and which structure* |
| side | a BUYER's question | a SELLER's desk |
| screen | `/console.html`, the Kite overlay | `/desk.html` |
| entry point | `engine.py` / `band_rotation.py` | `desk.py` / `surface.py` |
| record | `data/trigger_log.jsonl` | forward-only, none yet |
| read | this file, then §5 | **`HANDOFF-DESK.md` in full** |

If your task says *structure*, *strategy*, *vol*, *surface*, *margin*, *sizing*
or *recommendation*, you are working on THE DESK — read `HANDOFF-DESK.md`
before this file's §2, which is about the tape. If it says *zone*, *d2/d3*,
*arm*, *trigger*, *setup* or *the forward record*, you are on THE TAPE and this
file is the right one.

It does three things:

1. **Reads the tape.** A Python server ingests 1-minute index-futures bars plus
   the live option chain (Upstox websocket), and computes what a chart cannot:
   dealer/gamma regime, writer scores, OI walls, max pain and pin distance,
   squeeze detection that separates **short covering from a roll**, absorption
   (extreme effort, no result), and the band-rotation state machine.
2. **Detects and records the operator's setup.** The zone state machine
   (WAITING → ARMED → TRIGGERED → IN_TRADE) runs server-side and every arm and
   entry is appended to `data/trigger_log.jsonl` — a **forward** record, written
   before the outcome is known, which is the whole point.
3. **Paints it on the operator's own Kite chart**, through a Chrome extension
   (see §5). The React dashboard (`ui-v2/`) still exists but the operator has
   moved to chart-first; do not invest there without asking.

**The philosophy, and it is enforced in code:** when the tool does not know, it
says so. Missing data is `null` with a reason, never a plausible number. Every
signal carries a receipt sentence you can check against the candle. Counts are
never printed as rates until the sample is big enough and the operator has
stated the bar. Read a few docstrings — the narrative comments are load-bearing
incident history, not decoration. Do not "clean them up".

---

## 2. Current state — what is true today

### Live record (the only thing that will ever settle the question)

| population | rule tag | scored entries | note |
|---|---|---|---|
| §5c two-candle | `5c` | **17** | the d3-armed rule, measured |
| THE ZONE §1b | `zone` | **21** | d2/u2-armed — what the operator actually trades |
| arms | both | 100 rows (47 fresh setups) | a setup arming, never counted as a trade |
| legacy | untagged | 256 rows **quarantined** | §1's void one-candle rule, pre-2026-08-08, forming-bar prices — **never score these** |

Days covered 2026-08-04 → 2026-08-20. Only the **current** day's rows are ever
unscored; `eod_capture` fills them at 15:35 IST.

**What you may NOT do with those numbers:** print a hit rate, win rate or
expectancy. `research-findings.md` §5e records the pass criterion as **OWED BY
THE OPERATOR**, to be stated *before* the numbers are read, and calls anything
under **15 per side** INCONCLUSIVE. `trigger_log.py` refuses to print a rate for
exactly this reason. Do not invent a bar. Do not "just have a quick look at the
win rate". Describe rows if asked; leave the verdict to the operator.

### The one surviving edge, and its boundary

**NIFTY intraday d3 mean-reversion** is the only hypothesis that survived
testing. The boundary matters as much as the edge:

| instrument / context | behaviour |
|---|---|
| NIFTY, SENSEX — intraday σ-stretch | **mean-reverts** (liquidity noise) |
| BANKNIFTY | **trends** — inverts every reversion test |
| overnight gaps | no edge — informed repricing, not noise |
| single F&O stocks | no edge — a stock's −3σ is often news, and news continues |

### Dead — do not revive without new evidence (`research-findings.md` §2)

squeeze + falling OI fade · the engine event stream as a signal (scored
**−0.1 / −6.2 against a +4.1 do-nothing control** → default OFF) · the SMC layer
(4× over-fires vs LuxAlgo) · classic 15-min ORB · overnight gap-fade · d3 on
F&O stocks · **selling any upper band** (rejected on 5 independent datasets) ·
the compression / trap=CLEAR filter (actively harmful — it selected losers in
three separate datasets). Two further filters were pre-registered and
falsified: the morning window, and rotation-vs-trend state.

---

## 3. Architecture and where things live

```
Upstox WS ──► chain_live.py ──► chain_metrics.py ──┐
(token: .upstox_token, daily)                      │   gamma.py (Black-76, IV)
                                                   ▼
Upstox REST ─► contract_bars.py ─► live.py ─► engine.py ──► /api/data
(1-min bars)                          │                        │
                                      ├─ band_rotation.py   (the zone machine)
                                      ├─ structure.py       (ICT/SMC, default OFF)
                                      └─ trigger_log.py     (the forward record)
                                                   │
server.py :8765 ───────────────────────────────────┴──► Chrome extension overlay
                                                   └──► ui-v2/ (React, ABANDONED)

── THE DESK, a separate stack on the same server ─────────────────────────

Upstox chain ─► surface.py ──────────┐   (vega-weighted quadratic smile;
                (fits ONE expiry)    │    a=ATM vol, b=skew, c=convexity,
                                     │    per-point residual and z)
                                     ▼
chain_metrics.py ─► regime_from_chain ─► desk.py ──► /api/desk
(flip_px, gex, max_pain)                    ▲         (every structure,
                                            │          one STATUS each)
chainside.py ─► fuel / drain / trapped side │
     +         ──► direction.py ────────────┘
fuse.py + regime.py (the gear)  (BULL/BEAR/NEUTRAL + FORCED/LEANING/NONE)

drag.py     ──► /api/drag     (the buyer's tax, session-anchored)
surface.py  ──► /api/surface  (the fitted smile, per index)
                    │
                    └──► ui/desk.html  (THE screen. Plain HTML, no build step)
```

**Live path, by size:** `engine.py` (1339) · `band_rotation.py` (1274) ·
`live.py` (1197) · `trigger_log.py` (1121) · `server.py` (722) ·
`chain_metrics.py` (673) · `structure.py` (543) · `chain_live.py` (533) · the
Upstox adapter layer (~1375 lines across 7 files, split by axis: wire decode /
socket lifetime / REST / instrument resolution / pure translation / poll façade
/ OAuth CLI).

**Support:** `eod_capture.py` (Windows scheduled task, Mon–Fri 15:35 IST —
preserves the session tape so rows stay scoreable) · `recover_tape.py` (pulls a
missing session from Upstox historical; the road back when a tape is lost) ·
`signal_review.py` (read-only post-mortem against a running server) ·
`squeeze_score.py`, `run_score.py` (scorers still referenced by tests/imports).

**Data:** `data/backtest/` is the bar store (145 NIFTY files, plus 99 across
`SENSEX/` and `BANKNIFTY/`) · `data/trigger_log.jsonl` is the forward record ·
`data/chain/` is gitignored (200MB+/day).

**Docs, and what each owns:** `context/research-findings.md` = every strategy
verdict — **read before proposing any strategy work** · `context/HANDOFF.md` =
the build's running history · `context/DEFERRED.md` = measured work consciously
postponed · `context/CHECKLIST.md` = the rules register · `PRODUCT.md` and
`README.md` = the tool described for a reader.

---

## 4. Running it

```bash
start-v2.bat              # THE way to start. Upstox, port 8765.
start.bat                 # legacy: brings it up on DHAN (dead source) — avoid
stop.bat                  # kills only the process holding port 8765
python upstox_auth.py     # daily OAuth; opens a browser, catches the redirect
python -m pytest -q       # 842 tests, all green as of 2026-08-22
```

**The token expires daily at 03:30 IST.** A dead token looks exactly like a
quiet market — an empty chart with no error — which is why `/api/health` names
the broker actually serving, and why the extension shows it.

`python trigger_log.py show` prints the forward record (two tables — entries and
arms — never pooled). `python trigger_log.py score` fills outcomes, idempotently:
a second run over an unchanged log writes nothing.

---

## 5. The Chrome extension — two lines, one decision pending

The operator built their own MV3 extension, **PaperDesk**, which paper-trades on
Kite and draws directly on Kite's own ChartIQ canvas. It lives **outside this
repo** (in `~/Downloads/`), so repo-wide greps will not find it. It never places
a real order — that is its stated contract, and it has been verified twice.

Two diverged copies exist:

- **`paperdeskextension (2)/`** — v1.8.1 base **plus the TapeMap hybrid** built
  2026-08-15: `src/tape.js` polls this server every 15s and the chart renders the
  zone state (arm carets, ARMED reference line with countdown, stop), a WHY
  ribbon (squeeze / OI quadrant / gamma-pin), absorption and OI-peak-lag marks,
  premium-chart zone strips, and paper fills tagged with tape context that POST
  back to `/api/paper_fill`.
- **`paperdeskextension1.21.1.zip`** — the operator's own newer line (~11.8k
  lines): auto-pilot, hold assist, replay sandbox, self-diagnosis, and
  **studySnap**, which reads the operator's *actual SDVWAP band prices off the
  chart* and so solves §0.4's σ-mismatch by construction. It does **not** contain
  the hybrid.

**Decision pending: port the tape layer INTO 1.21.1** (~300 lines, 7 isolated
touch points, zero key collisions) rather than the reverse. Open bugs in the
1.21.1 line, worst first: blast entries have no time cutoff (the gate returns
early), the background inject list omits `auto.js`/`diag.js`, pad short-option
margin still falls back to 10× premium, MIS square-off uses the machine clock
instead of IST, and `instFor` caches `null` permanently. Its recovered 1.17.0
test suites are timezone-sensitive and fail on an IST machine unless run with
`TZ=UTC`.

`chrome-ext/` inside this repo is the **superseded** thin panel. It still works
and is still loadable, but do not add features there.

---

## 6. Traps that have already bitten

Each of these cost a session. They are guarded in code; do not remove the guards.

- **Frozen tape (2026-07-27).** A 37MB scrip master re-downloaded every cycle
  stalled the refresh loop. Heartbeat, deadline and logging fixes are in place.
- **The chain socket trap (2026-08-12).** A reload trigger matched its own
  "check the token" advice text, so a warming socket rebuilt itself forever. It
  looks exactly like a token problem, and is not.
- **The tape used to evaporate at midnight**, costing five rows — which were then
  declared "permanently unmeasurable" after checking only the tool's *own*
  copies. On 2026-08-20 they were recovered from Upstox in a single call.
  **Lesson: a session is not unrecoverable because our copies of it are gone.**
- **Never score a forming bar.** The last bar of a live refresh is still forming;
  a trigger read off it can un-fire when the minute closes. Measured: 5 of 12
  rows one morning did not survive their own bar's close.
- **Weekend-sensitive tests.** Four contract tests compared calendar-today
  against the session day and failed every Saturday and Sunday until fixed on
  2026-08-15.
- **Kite MCP is not a data source here** — login completes, but every
  API-hitting endpoint fails (no historical subscription). Upstox is the route.

---

## 6b. THE DESK, in one screen — and the trap that keeps catching it

Full detail is in `HANDOFF-DESK.md`; this is the minimum a new agent needs so
it does not re-derive the wrong model.

**The catalog is 13 structures with a STATUS each**, never a confidence score:
`DEPLOYABLE` / `STAND_ASIDE` / `BLOCKED` with the missing input named. Blocked
rows are always rendered — an absent row reads as "not considered".

**Every candidate carries a `case`, and the case decides which ruler ranks it.**
Getting this wrong is the single most repeated bug in this stack:

| case | the trade's argument is | ranked by | the floor |
|---|---|---|---|
| `MISPRICING` | the RESIDUAL — a point off its own curve | edge per rupee of margin | `MIN_EDGE_RS` applies |
| `FLOW` | forced flow — someone must transact | **convexity** per rupee of margin | exempt; `edge` is only a caveat |
| `REGIME` | the GEAR — hedging damps, so sell premium | edge per rupee of margin | exempt, but a NEGATIVE edge stands aside |

**The gear picks the case before anything is ranked.** CASCADE wants `FLOW`,
PIN wants `REGIME`, TRANSITION wants nothing at all. Ranking across cases mixes
quantities three orders of magnitude apart, and has twice produced a
confidently wrong "best".

**The direction view is `direction.py`, and it measures nothing new.** A short
call is in pain when price rises, so a trapped CE side relieves UPWARD:
`ce -> BULL`, `pe -> BEAR`. `FORCED` — the trapped side actually draining,
inside CASCADE — is the ONLY state that licenses a directional structure;
`LEANING` names a side and licenses nothing. **Bias and gear are two fields and
must never collapse into one**: a bull view in PIN is the market paying you to
SELL PUTS, not to buy calls.

**Costs are ZERO and that is deliberate.** `desk.STATUTORY_PCT = 0.0` — the
operator's broker charges no brokerage and rebates statutory charges on any
position closing at least ₹1 positive. `STATUTORY_PCT_IF_CHARGED` holds the old
0.0014 for the day that arrangement ends. Do not "fix" this back.

**THE TRAP, stated once because it has now caught three sessions running: a
passing test suite is not evidence the model is right.** Every serious defect
in the desk has been found by live data or an adversarial reader, never by
pytest — which passed at 707, at 829, and at every stage between, over a future
out-ranking convexity, a credit spread deploying in the wrong gear, a drain
counter that summed both sides, a rank that could never fire, and a margin
rendered as a bold ₹0. Before reporting that anything works, ask the only
question that matters: **would a desk take this trade?**

## 7. What is open

- **The forward test needs more rows.** NIFTY BUY is the biggest zone cell at
  n=9. There is nothing to do but let it run — `eod_capture` and the logger are
  automatic.
- **The desk has NO track record at all.** `direction.py`, the flow catalog and
  the drag meter were built 2026-08-21/22 and have never run through a live
  session end to end. `direction.py` carries a kill condition in its docstring:
  if after ~30 scored sessions `FORCED` views do not resolve in the named
  direction more often than `LEANING` ones, it is rewritten; if neither beats
  naming no direction at all, it is deleted rather than tuned.
- **Multi-day surface history** is the biggest unlock left. Until it exists,
  richness is CROSS-SECTIONAL only — a point against today's curve, never "the
  surface is rich". `HANDOFF-DESK.md` §8 lists the rest in dependency order.
- **The operator owes §5e's pass bar**, stated before the numbers are read.
- **Port the tape layer into PaperDesk 1.21.1** (§5), and fix that line's five
  open bugs.
- **`/api/contract` and the two-leg confirm stack** (~850 lines, fully tested)
  still have no UI consumer. Ship the pair chart or delete the stack — mockups
  are at `ui-v2/comps/pair-chart-mockups.html`; the operator has seen them and
  deferred the decision.
- Small residuals in `context/DEFERRED.md` §0f (two unexplained band figures).

---

## 8. How to work here

- **Ask before strategy work.** If a task smells like "let me test whether X
  predicts Y", check `research-findings.md` first — it is probably already dead,
  and if it is not, it must be **pre-registered** before it is measured.
- **Never quietly delete an inconvenient record.** When something written down
  turns out to be wrong, correct it *in place, with the reasoning error named*
  (`DEFERRED.md` §0d is the pattern). The record of having been wrong is worth
  more than a tidy file.
- **Keep the populations apart.** `5c`, `zone` and legacy rows are three
  different things. Pooling them is the single easiest way to destroy months of
  record.
- **Tests are the house style.** `pytest -q` stays green (842), and non-trivial
  logic leaves one runnable check behind. Doc claims about test counts are pinned
  by `test_docs_claims.py` — update the docs when the count moves, or the suite
  fails on purpose.
