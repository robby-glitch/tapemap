# The Upstox tape — a ladder off the socket, and the gate that decides whether GoCharting can go

**Status:** design, 2026-09-20. Spec 2 of the order-flow trajectory. Spec 1 (`2026-09-19-orderflow-levels-design.md`)
records GoCharting's ladder and draws levels from it; spec 1b (`2026-09-19-convergence-chips-design.md`) pairs book
and tape. This one builds the **same ladder from Mary's own Upstox socket**, records it beside GoCharting's, and
measures the two against each other for as long as she keeps both. Nothing here replaces anything. §K says what would.

**Where the pieces come from.** Three methods are taken from *Order Flow Lab* (TradeHull, MIT, `orderflow.html`
lines 1478–1511, 731–836, 837–964, 701–730): price-priority fill reconstruction, causal run-of-three detection, and a
rolling price-impact regression. They are ported as **methods with their constants named**; none of that project's
hit-rate claims travel with them (CLAUDE.md rule 4). Its recorder is not ported: it is Dhan-only, its packaged SDK
path unpacks five levels (`dhanhq/marketfeed.py`, `for i in range(5)`), and TapeMap already owns a socket.

**What this repo already has, and is not rebuilt.** `sweep.py` (levels gone + `vtt` → swept / pulled),
`depth_pull.py` (size gone, nothing traded), `absorption.py` (touch stable, traded > shown → replenished, a proof),
`senses.py` (the three, forward-logged to `data/senses/`). The Order Flow Lab iceberg episode is `absorption.py`'s
proof with a persistence wrapper; the wrapper is deferred (§I). Its sweep detector is `sweep.py`. Its pull ledger is
`depth_pull.py`.

**Facts this design stands on, all measured in this repo unless marked.**

| fact | where |
|---|---|
| The `full` frame carries `ltpc = {ltp, ltt, ltq, cp}`, `vtt`, `oi`, `tbq`, `tsq` and five `bidAskQuote` structs a side | `upstox_proto.py:33–49`; `data/feed_frame_2026-08-20.json` fut frame: `ltq 65`, `ltt 1787200010000` (second resolution), 5 levels |
| Depth `qty` and `vtt` are in the SAME unit, multiples of the lot (65 on NIFTY) | `sweep.py` docstring, measured 2026-08-20 10:10 |
| `UpstoxFeed._absorb` merges every decoded frame into `_latest` **last-value-wins**; `_senses_loop` reads `snapshot()` every 0.5 s | `upstox_feed.py:179–200`, `server.py:622, 911` |
| No raw book is recorded anywhere today: `data/frame/` rows carry no ladder, `data/senses/` carries events only | `frame_2026-09-18.jsonl` keys; `senses.py` docstring |
| Frame rate is undocumented in this repo; Upstox staff say ~2–3 frames/s per instrument in `full` mode | memory `upstox-api-facts` [I] — **measured on day one by this spec's record** |
| `full_d30` returned five structs, not thirty, after close on 2026-08-24 | memory `upstox-api-facts` — not assumed here, see §I |
| GoCharting's bar `t` is the bar's open in epoch ms, IST session (1789098300000 = 2026-09-11 09:15:00 IST); ladder rows are `{p, b, s, bt, st}` in **lots**; `rowSize 5`, `rowAnchor 0`, `lot 65` | `data/tape/tape_NIFTY_2026-09-18.jsonl` row 1 |
| The interval tick rule is dead here: attributing an interval to the side of its last print scores p²+(1−p)² — a coin flip when balanced, redundant when not | `sweep.py` `Sweep` docstring |
| Footprint data is trusted for **shape and sequence, never magnitude** | memory `stack-doctrine` |
| NIFTY-FUT produced **485** sweep rows on 2026-09-18 at the 0.5 s poll — about 26 per 20-minute window | `grep -c` on `senses_2026-09-18.jsonl` |
| The instrument slice cached in `data/upstox_<idx>.json` carries no `lot_size`; the full Upstox dump does (`lot_size`, `tick_size`) | `data/upstox_nifty.json` keys; Upstox instrument JSON [I] |

---

## §A Purpose and boundary

**What ships.**

| piece | module | kind | tag |
|---|---|---|---|
| every decoded frame of each index future, on disk | `book_log.py` + one hook in `upstox_feed.py` | record | `[M]` |
| the frames of one 5-minute bar → a ladder in spec 1's row shape | `ladder.py` (pure) | derivation | `[I]` (side, level); `[M]` (vol, OHLC, oi) |
| the day's `ux` bars, written once at bar close, rebuilt from the book on restart | `ux_log.py` | record of a derivation | — |
| GoCharting's bars vs `ux` bars on one grid: shape agreement, per bar and per session | `ux_gate.py` (pure) | measurement of two records | `[M]` |
| runs of three big same-side fills inside three seconds, causal percentile | `runs.py` (pure) | detector | `[I]` |
| price impact: ticks moved per lot of signed volume, rolling 120 s | `impact.py` (pure) | gauge | `[I]` |
| `/api/tape` gains a `ux` object; the Trade chart draws `ux` session levels dotted, `ux` delta as a second series, `s` glyphs for runs, one agreement line and one λ figure in the legend | `server._tape_reply`, `ui-v2/src/trade/*` | face | — |
| `tools/gate_report.py` — the day's §D numbers from the two files, no verdict | tool | — | — |

**What does not ship.** No replacement of GoCharting, no source switch, no scoring, no hit rate, no options legs, no
DOM or heatmap surface, no change to `sweep`/`absorption`/`depth_pull`, no change to the extension, no order path.

**The trajectory.** While GoCharting is open, its record is the ground truth (spec 1). This spec runs the Upstox
ladder **beside** it and measures agreement daily. After five sessions the operator states the bar (§K). If the bar
holds, the Trade tab can be pointed at `ux` by one flag and GoCharting becomes optional. If it fails, the failing
metric is named and `ux` stays a dotted second opinion. Either way the book record keeps running: it is the one
artefact no broker can refetch.

**Three families on the wire, never merged.** `ofd` (the extension's marks), `tm` (spec 1's second opinion),
and now **`ux`** (everything derived from the socket). Spec 1b's table lists a third `src` for exactly this
(`convergence-chips-design.md:197`); it grows by the operator's word, not by this spec.

---

## §B The book record — `book_log.py`

**Where the hook sits, and why it is not the poll.** `_senses_loop` reads `snapshot()` twice a second and
`_latest` is last-value-wins, so any frame that arrives between two polls is gone before anyone reads it. A record
built off the poll would be a record of the poll. So `UpstoxFeed.__init__` gains `on_frame=None`, and `_absorb`
calls `on_frame(key, feed, current_ts)` for every key in `feeds` **that is in the watched set**, after the merge and
outside the lock. The callback runs on the feed thread, so it must never touch disk: it appends a compact row to a
bounded `deque(maxlen=20_000)` and returns. Overflow increments `dropped`, which `/api/health` `coverage` reports.

**Who drains it.** `_senses_loop`, once per pass (0.5 s), calls `book_log.flush()` — writes the rows to disk and
hands the same rows to `ux_log.on_frames()` (§E). One drain point; disk never under `_SENSES_LOCK`, never on the
feed thread. This is the `senses.py` `_append` discipline.

**Watched set.** The three futures only: `book_log.watch(idx, fut_key)` is called from the senses loop where it
already has `r.get("fut_key")` (`server.py:800`), idempotent, re-called on every chain refresh so a contract roll
rewatches. Options legs are not recorded (§I).

**The row.** `data/book/book_<idx>_<day>.jsonl`, one line per frame **that differs from the previous written row
for that key** in any of `(vtt, ltp, ltq, ltt, b, a)` — the `frame_log.append_if_changed` rule. An identical frame
is a heartbeat; skipping it loses nothing because the first differing frame carries the change.

```
{"t": arrival_ms, "cts": currentTs_or_null, "ltt": ms, "ltp": 24271.7, "ltq": 65, "vtt": 1023750,
 "oi": 12873510, "tbq": 168090, "tsq": 292630, "b": [[p, q], ...best first], "a": [[p, q], ...best first]}
```

`b`/`a` hold however many levels arrived — five today, thirty if `full_d30` ever delivers them live — and
`len(b)` is therefore a measurement of the entitlement, per frame, for free.

**Write-once, restart-safe.** Rows are appended in arrival order; on start the writer reads the file's last `t` and
refuses anything at or before it. A restart cannot duplicate (a different process, a later `t`), and the morning's
rows stay.

**Anytime-start, honestly.** Nothing before process start can be reconstructed — there is no REST endpoint for
historical depth. `coverage.book_from = "HH:MM:SS"` per index in `/api/health`; a `ux` bar whose frames do not span
its whole five minutes is written with `partial: true` and `partial_why` (§E). That is the rule's "honest
degradation for the rest".

**Lot and tick.** `upstox_instruments`' filtered slice gains `lot_size` and `tick_size` from the dump (two fields,
one place). Until a slice carries them, `lot` falls back to GoCharting's `lot` for the same index and day when that
record exists, else to the greatest common divisor of the day's first 200 non-zero `vtt` deltas, and the row says
which (`lot_src: "dump" | "ofd" | "gcd"`, the last tagged `[I]`). `tick` falls back the same way: the dump's
`tick_size`, else the smallest gap between adjacent levels that recurs at least three times across the day's first
50 frames sampled evenly (Order Flow Lab's `initDerived`, `orderflow.html:1251`), `tick_src` says which.

**Size, to be measured.** At the forum's 2–3 frames/s and ~350 bytes a row: 50–70 k rows and ~20 MB per future per
session, ~60 MB a day for three [I]. Day one's HANDOFF entry replaces this with the measured figure.

**Registrations.** `.gitignore` gains `data/book/` (socket-sourced, ~60 MB/day, not refetchable);
`_isolate_mock_writers` gains `book_log.DIR`; `test_day_state.py` pins the name; the root `conftest.py` autouse
fixture redirects `book_log.DIR` like `tape_log.DIR` (the 2026-09-19 leak must not recur with a 60 MB file).

---

## §C The reconstruction — `ladder.py`, pure, stdlib, no I/O, no clock

**Inputs.** The frames of one instrument in arrival order, `lot`, `tick`, `interval_s = 300`, session open `09:15`
IST. **Output.** Closed bars in `tape_log`'s row shape, plus counters, `src: "ux"`:

```
{"t": bar_open_ms, "o", "h", "l", "c", "vol", "buy", "sell", "unknown", "delta", "oi", "fromTicks": true,
 "ladder": [{"p", "b", "s", "u", "bt", "st"}], "rowSize": null, "rowAnchor": 0, "lot", "lot_src",
 "frames", "exact", "reconstructed", "hidden", "vtt_resets", "lot_mismatch", "levels_seen",
 "partial", "partial_why", "src": "ux", "idx", "day"}
```

`rowSize` is **null on the record**: the ladder is kept at raw prices (spec 1 keeps GoCharting's raw ladder too)
and re-binned at read time to whatever grid the comparison needs (§D). Lots, not units: every quantity is divided
by `lot`; a non-multiple increments `lot_mismatch` and is kept fractional rather than rounded.

**Binning.** A frame belongs to the bar containing its **`ltt`** when it carries a trade (`vtt` rose), else its
arrival `t`. GoCharting bins on the exchange's trade time; arrival time is skewed by the network. Bar `t` is the
bar's open in epoch ms, IST session — byte-equal to spec 1's `t`, which is the join key.

**Per consecutive pair `(prev, cur)`**, `V = cur.vtt − prev.vtt` in units:

1. `V < 0` → the feed reset (rollover, reconnect after a burst). The pair is skipped, `vtt_resets += 1`, `prev` is
   replaced. Nothing is attributed.
2. `V == 0` → no trade. Nothing is attributed; what the book did is `depth_pull`'s business, not this module's.
3. **Exact case: `V == cur.ltq`.** One trade of `V` units at `cur.ltp`. Price and size are `[M]`. Side `[I]` by the
   touch it hit, judged **against `prev`'s book**: `ltp ≥ prev best ask` → buy; `ltp ≤ prev best bid` → sell;
   strictly inside the spread → above `prev` mid → buy, below → sell, **equal to mid → unknown `u`**. This is the
   per-trade quote rule, and it is not the interval rule `sweep.py` killed: each print is judged against the touch
   that took it, not an interval against its last print. `exact += 1`, one trade counted (`bt`/`st`).
4. **Reconstruction case: `V ≠ cur.ltq`, or `ltq` absent.** Several trades in one interval when `V > ltq`; a
   stale `ltq` when `V < ltq` (the frame's last-trade fields lag its `vtt`) — either way `ltq` is not trusted and
   the book decides. The exchange fills best price first, so march the book:
   - The **primary side** is the side of `cur.ltp` against `prev` (as in 3); on a tie, the side whose displayed
     size fell more; on a second tie, unknown, and the whole `V` is booked `u` at `cur.ltp`.
   - Buys eat **asks** from `prev`'s best upward; sells eat **bids** from best downward. At each level
     `eaten = min(max(0, q_prev − q_cur_at_that_price), remaining)`; stop at the first level priced **past
     `cur.ltp`** by more than half a tick (Order Flow Lab's `tick*0.55`) — the trade cannot have reached it.
   - After the primary side is exhausted or `remaining` is spent, march the **other** side the same way, for the
     rest. A two-sided interval attributes to both, each at its own levels.
   - **Residual** `= V − attributed` is booked at `cur.ltp` on the primary side with `hidden += residual`. It is
     volume the visible book cannot explain: an iceberg, or more trades than frames. Volume is conserved: every
     unit of `V` lands somewhere, and the counters say how much landed by proof and how much by residual.
   - Each level-eat is one trade for `bt`/`st` — a **floor**, as `sweep.py` says of its magnitudes.
   - `reconstructed += 1`.
5. Every attributed unit lands at its **level price** (the resting order's price), `b` for buys, `s` for sells,
   `u` for unknown. OHLC from `ltp` of trading frames; `oi` is the bar's last; `vol = Σ V`; `delta = buy − sell`
   (unknown excluded, by definition of a sign); `unknown = Σ u`.

A row with no last price on either side cannot place its volume: V is booked `unknown` and `unpriced`, with no
fill — the one branch where fills do not sum to V (amended at Task 6).

The bar carries `unpriced` beside `unknown`; `unpriced` is the part of `unknown` that has no price at all, so
the two never share a field, and a reader must not add them (final review, 2026-09-21).

**Fill events.** Besides bars, `ladder.step` yields each attribution as a fill event
`{ltt, side: +1|−1|0, p, q_units, hidden: bool}` in tape order — the input of `runs.py` and `impact.py` (§G).
Within one interval the primary side's fills are listed first, then the other side's (their true interleave is
unknowable from snapshots, and this is Order Flow Lab's tie-break too).

**What the counters are for.** `exact / (exact + reconstructed)` is how often the interval held one trade, which is
the feed's cadence relative to the tape; `hidden / vol` is how much of the day the visible book could not explain;
`unknown / vol` is how much had no side. All three are `[M]` about the derivation and go on the wire (§E) so the
operator reads the `ux` ladder knowing how it was made. A `ux` bar with `hidden / vol > 0.5` is not a ladder, it is
a residual with a ladder's shape — the legend says so (§F).

**`u` on the ladder.** `prints.rebin` (`prints.py:33`) gains `u` in its sum; `prints.profile` (`:102`) and
`prints.nodes` count `b + s + u` as volume-at-price. `imbalances` and `bar_flags` ignore `u` — a diagonal ratio has
no unknown side. GoCharting rows carry no `u`, so the spec 1 parity fixtures pin that this changes nothing there.

**Fixture-first.** A synthetic twelve-frame fixture with hand-computed expectations covers: one exact trade at the
ask; two lots taking two ask levels; residual booked hidden; a `vtt` reset; a print at mid → `u`; lot mismatch;
a frame whose `ltt` crosses a bar boundary. A real fixture — the first recorded day's first 200 frames — is added
the day it exists and the test skips until then (the spec 1 parity pattern).

---

## §D The gate — `ux_gate.py`, pure

Named `ux_gate` (amended at implementation, Task 9): `gate.py` already existed — the seller's gate, imported by
`frame.py`.

Two records for one index and day: GoCharting's bars (`tape_log.read_bars`) and `ux` bars (`ux_log.read_bars`).
Both are re-binned with `prints.rebin` on **GoCharting's grid** (`rowSize`, `rowAnchor` from its record) — the
grid the operator's chart is on. Joined on `t`. **Shape is compared, never magnitude** (stack doctrine), with one
exception that is a feed-integrity check between two `[M]` totals.

**Per joined bar.**

| field | value | null when |
|---|---|---|
| `poc_rows` | `abs(poc_ux − poc_ofd) / rowSize`, an integer | either POC null |
| `delta_sign` | `agree` / `disagree` | either delta is 0 |
| `vol_ratio` | `vol_ux / vol_ofd` | `vol_ofd == 0` |
| `stacks` | `both` / `ofd` / `ux` / `neither` — any stack in the bar | never |
| `unfinished` | same four-way, either end | never |

**Per session.**

| field | value |
|---|---|
| `bars_joined`, `bars_ofd_only`, `bars_ux_only` | counts |
| `poc_rows_median`, `poc_within_1` | median rows apart; fraction of joined bars with `poc_rows ≤ 1` |
| `delta_sign_agree` | agreeing / non-null |
| `vol_ratio_median` | over non-null |
| `va_overlap` | Jaccard of the two session `[val, vah]` intervals, from `prints.profile` on each record |
| `hvn_jaccard`, `lvn_jaccard` | over row prices from `prints.nodes` on each |
| `exact_frac`, `hidden_frac`, `unknown_frac` | from the `ux` counters, session totals |

Every field carries `tag: "M"` — each is a comparison of two records that exist. **The module returns numbers and
returns no verdict**, no "pass", no colour. Empty sets (a day with no HVN on one side) yield `null` with a `why`,
never `0`.

---

## §E Where it runs, and the API

**`ux_log.py`.** Owns `_STATE[idx] = {frames of the open bin, prev frame, bars: []}`. `on_frames(rows)` (from the
drain, §B) feeds `ladder.step()`; when a frame's bin exceeds the open bin, the open bar closes, is appended once by
`t` to `data/tape/ux_<idx>_<day>.jsonl` (same directory as spec 1's two files, third population, third file), and
kept in RAM. **On start** `rebuild(day, idx)` streams today's book file through `ladder` and writes every closed bin
the previous process did not — the anytime-start rule in one function, and what lets `tools/gate_report.py` run
from files alone. `partial` is set on the first bar after `book_from` and on any bar with a `vtt_reset`.

**`/api/tape` gains `ux`** (spec 1 §D's reply, one new object):

```
"ux": {"src": "ux", "tag": "I",
       "bars": [ {t, o, h, l, c, vol, buy, sell, unknown, delta, cvd, oi, stacks, unfinished_high, unfinished_low,
                  poc, exact, reconstructed, hidden, partial, partial_why} ],
       "forming": {...} | null,
       "levels": {"session": {poc, vah, val} | null, "nodes": [...], "why": ...},
       "marks": {"runs": [ {t, kind: "run", side, n, qty, thr, from_t, to_t, src: "ux", tag: "I", why} ], "runs_why"},
       "impact": {"lots_per_tick", "pct", "n", "why"} | null,
       "agree": ux_gate.session(...) | null, "agree_why": ...,
       "book_from": "HH:MM:SS" | null, "frames_per_s": measured | null, "lot", "lot_src",
       "why": ...}
```

`ux` ladders are **not served** (spec 1's 81 %-of-bytes finding). `bars[].stacks/unfinished/poc` come from
`prints.bar_flags` on GoCharting's grid, so the two families' flags are comparable; when no GoCharting record
exists for the day they are computed on `rowSize 5`, `rowAnchor 0` — the extension's defaults as recorded — and
`agree_why` says the grid was assumed. `cvd` from `prints.with_cvd`.

**Three sentences, as ever.** `ux.why`: *"no book record for `<idx>` on `<day>` — the server was not recording
(book_log predates it, or the feed never connected)"* / *"book record from HH:MM:SS, no bar closed yet"* /
`null`. `agree_why`: *"no GoCharting bar shares a `t` with any ux bar — nothing to compare"* /
*"GoCharting record absent for this day — ux stands alone, flags on the default grid"* / `null`. `runs_why`:
*"fewer than 50 fills in the last 20 minutes — the percentile has nothing to rank against"* / *"checked, none"* /
`null`. `impact.why`: *"fewer than 120 s of frames"* / *"no signed volume in the window"* / `null`.

**Cost.** `ladder.step` is O(levels) per frame; a bar closes over ~750 frames; `ux_gate.session` runs once per bar
close over ≤ 78 bars; `impact` keeps a 120 s deque. Nothing here parses a file on the request path.

---

## §F Drawing — the Trade tab, existing seams only

| what | where | how |
|---|---|---|
| `ux` session POC / VAH / VAL | `LevelsOverlay.drawPrints` (`:1230`), the block that draws `levels.session` | the same three colours, **dotted**, label suffix ` ux`; placed by `makePlaceLabel` (`:480`) so they never overprint the solid ones |
| `ux` delta | `indicators.alignDelta` (`:243`) / `buildIndicators` (`:269`) | a second series `Δ ux [I]` as a **line** over the histogram, only at 5/15 min, only where both records have the bar |
| runs | the hollow-glyph path `drawPrints` uses for `tm` | hollow lowercase **`s`**, side-coloured, at the run's `to_t` bar and `qty`-weighted price; the Callout row reads `why` (`Callout.tsx` `tm`/`ofd` rows, one more branch) |
| the agreement line | `TradeTab.tsx` legend block (`:1063–1071`) | one line: `ux vs ofd · POC ±N rows (median) · VA overlap NN % · delta sign N/M · vol ×R.RR · hidden NN % · unknown NN % [M]` — or `agree_why`, or `ux.why` |
| λ | the same legend line's tail | `· λ 1 tick / ~N lots (pct .NN) [I]` or `impact.why` |
| `printsKey` | `LevelsOverlay.ts:1623` | gains `ux.bars.length`, `ux.forming?.t`, `ux.marks.runs.length` so a new ux bar repaints |
| types | `tape.ts` | `TapeReply.ux` typed to the wire, `TapeBarRow` gains the optional counters, `TapeMark.src` gains `'ux'` |

`ux` nodes (HVN/LVN) are **not drawn** — two sets of bands is ink, and their agreement is a number on the legend.
The operator asked for marks on her candle chart, not a second chart; the trader's call is that the three session
lines and the delta line are the read, and the numbers carry the rest.

**Hidden-heavy bars.** Spec 1 draws no per-bar POC mark, so there is nothing to draw hollow (found at Task 15). The
Callout carries the sentence instead: *"ux ladder here is mostly residual — the visible book explained NN %"* when
`hidden / vol > 0.5`, and *"ux bar partial — <why>"* when the bar is partial. A ladder built mostly by residual must
not read like one built by proof.

---

## §G `runs.py` and `impact.py` — the two book-derived pieces

**`runs.py` — three big same-side fills in a row.** Input: the reconstruction's **fill events** in tape order
(§C, both sides, residual included as a hidden fill), not `senses` sweep rows — 485 sweep rows a day is ~26 per
twenty minutes, under the 50 the percentile needs, whereas fills run in the thousands. Method, constants carried
from Order Flow Lab **verbatim and named, not tuned**:

| constant | value | meaning |
|---|---|---|
| `RUN_N` | 3 | fills in a row before it counts |
| `RUN_PCT` | 0.90 | "big" = at or above this percentile … |
| `RUN_WIN_S` | 1200 | … of fill sizes in the last 20 minutes |
| `RUN_GAP_S` | 3 | at most this many seconds between one fill and the next (by `ltt`) |
| `RUN_MIN_N` | 50 | a percentile drawn from fewer fills is not trusted |

The percentile is **causal**: a fill is judged against the fills before it, then inserted. A run breaks on a **big
fill from the other side**; a small same-side or small opposite fill is ignored (`SEQ_STRICT = false`, with Order Flow
Lab's reason: "three sells in a row" means nobody big bought in between). A run fires once, at its third fill, and
grows in place while the pressing continues. Side is `[I]` because the fills' sides are; a fill with side 0 neither
joins nor breaks a run. Emits `{t, kind: "run", side, n, qty, thr, from_t, to_t, src: "ux", tag: "I", why}` with
`why` in words: *"3 buys ≥ 195 lots inside 3 s — each in the top decile of the last 20 min"*.

**`impact.py` — how many lots move price a tick.** Over the last 120 s of frames: `dp` = mid change in ticks
per frame, `sv` = signed attributed volume per frame (`b − s`, unknown excluded). Regression through the origin:
`λ = Σ(sv·dp) / Σ(sv²)` when both sums are positive, else `None` with `why`. Reported as
`lots_per_tick = 1 / (λ · lot)` — the desk thinks in lots — and `pct` = `prints.pct_rank` (strict) of `λ` against
the session so far. Kyle's λ by name in the docstring; a thin market is a **high** λ. `[I]` throughout, because `sv`
is. Drawn on the legend only (§F).

**Kill conditions, declared now, in the `frame.py:19–26` form.** *runs:* at n ≥ 30 runs on one index, if the
+6-bar excursion in the run's direction does not exceed the unconditional control by one standard deviation, the
glyph goes. *impact:* over 30 sessions, if top-quartile λ readings precede top-5 % 6-bar moves no more often than
any other reading, the figure goes. Scored by the §K scorer, never printed as a rate.

---

## §H Tests

- **`book_log`:** change-only write; identical consecutive frame skipped; deque overflow counted; `on_frame` never
  opens a file (monkeypatch `open` to raise, call it, assert no raise); restart appends after the file's last `t`;
  `_isolate_mock_writers` and the `conftest` redirect pinned like `tape_log`.
- **`upstox_feed`:** `on_frame` fires once per watched key per decoded frame, not for unwatched keys, after the
  merge, outside the lock (`test_upstox_feed.py`'s injected-connect harness).
- **`ladder`:** the seven synthetic cases in §C; `rebin`/`profile` carry `u`; every spec 1 parity test unchanged;
  fill events listed primary side first.
- **`gate`:** hand-built two-bar records → every §D field; each `null` case with its `why`; Jaccard on empty sets.
- **`runs`:** causal (the judged fill is not in its own window); gap; opposite-side break; small same-side ignored;
  side-0 fills inert; under `RUN_MIN_N` nothing fires; a run grows in place.
- **`impact`:** a synthetic slope is recovered; zero denominators → `None` with `why`.
- **`server`:** `/api/tape` carries `ux` with the three whys; ladders absent from the wire; live vs file branches;
  `rebuild` writes only missing bins; the default-grid `agree_why` when no GoCharting record exists.
- **ui-v2:** `npx tsc --noEmit` only (no runner), as spec 1.
- Every task that adds tests bumps `context/DEFERRED.md` "Test count is now N" in the same commit (ledger rule).

---

## §I Out of scope, deliberately

| not here | why | where |
|---|---|---|
| `full_d30` | five structs came back after close; not assumed. The record stores whatever arrives and `levels_seen` measures it live | day one's HANDOFF entry says what the socket delivered |
| iceberg episodes | `absorption.py` already proves replenishment; a persistence wrapper is a fourth absorption opinion | after §K, if the operator asks |
| options legs | GoCharting's record is the future; the comparison is on the future | spec 3, if the gate holds |
| tape commentary | the story layer is spec 1b | — |
| switching the Trade tab to `ux` | §K step 3, by flag, after her bar | — |
| Dhan, Kite, the extension's engine | untouched | — |
| a heatmap / DOM surface | a new surface, not this chart | a later spec, once the book record has days in it |

---

## §J Spec decisions — choices neither source named

1. **Record from `_absorb`, not the poll.** `_latest.update(feeds)` is last-value-wins; a record built off
   `snapshot()` would silently miss every frame between polls. The record is the feed or it is not a record.
2. **Bin by `ltt`.** GoCharting bins on exchange trade time; arrival time carries the network. Second resolution is
   what `ltt` has (measured), and a bar boundary at second resolution is what GoCharting has too.
3. **Side: per-trade quote rule in the exact case, book-decrease in the rest, `u` otherwise — never split.** The
   interval rule is dead in `sweep.py` by arithmetic. The per-trade rule judges each print against the touch it
   took, which is a different question; the literature's accuracy figure for it is not carried, because the only
   ground truth available here is GoCharting's side, which is itself inferred. §D therefore measures **agreement
   between two inferences** and the legend says `[I]` on every `ux` side-derived number.
4. **Compare on GoCharting's grid.** The operator's chart is on it, and spec 1's flags are computed on it.
5. **Shape metrics only, plus one magnitude check.** POC rows, VA overlap, delta sign, node sets are shape.
   `vol_ratio` is `[M]` against `[M]` and tests the feed, not a trade.
6. **Order Flow Lab's five constants carried verbatim.** 3 / 0.90 / 1200 s / 3 s / 50 are named once and not tuned
   until §K; its hit-rate claims are not carried at all.
7. **Runs feed on fills, not on `sweep` rows** — measured: 485 sweep rows a day is too thin for a causal decile.
8. **Futures only; `ux` is `[I]` except `vol`, OHLC and `oi`.** Options legs multiply the record by thirty and
   answer no question the gate asks.
9. **λ in lots per tick.** The desk trades lots. Ticks per share is the paper's unit, not the operator's.
10. **A third file in `data/tape/`, not a fourth directory.** Three populations, three files, one directory whose
    name already says "tape"; `book/` is a different thing (frames, not bars) and gets its own.
11. **`u` is a ladder field, not a half-and-half split.** Splitting an unknown side is inventing a measurement.
12. **Lot from the dump first, GoCharting second, gcd last, and the row says which.** A lot that is wrong by a
    factor turns every ladder into nonsense silently; `lot_src` makes the provenance a field.

---

## §K Pre-registration — the replacement gate, the operator's, in order

1. **Five live sessions** with the book record, the `ux` family and spec 1's `ofd`/`tm` all drawn. The legend's
   agreement line is read daily; `tools/gate_report.py --idx NIFTY --day YYYY-MM-DD` prints §D's numbers for the
   day and the running medians. **Nothing prints a verdict.**
2. **Then the operator states the bar**, in `context/research-findings.md` as a pre-registered section (§5's
   rule): which §D metrics, the threshold for each, and how many consecutive sessions it must hold. This spec does
   not write that section; the names in §D are field names, not thresholds.
3. **If the bar holds:** one flag, `TAPE_SOURCE = "ofd" | "ux"` in `server.py`, points `levels`, the delta pane
   and the prints legend at `ux`. The GoCharting record keeps writing as long as the extension posts. Whether the
   subscription continues is her decision, made with the numbers in front of her.
   **If it fails:** the failing metric is named in the HANDOFF entry, `ux` stays dotted and faint, and the next
   question is whether the failure is the feed's cadence (`exact_frac` low, `hidden_frac` high) or the method's
   (`delta_sign_agree` low with `vol_ratio ≈ 1`) — two different next specs.
4. **Kill conditions** for `runs` and `impact` as §G, scored by the §K scorer of spec 1 (its `score_frame.py`
   shape, `HORIZ_BARS = (1, 3, 6)`), never as a printed rate.
5. **The one thing this spec must not do is answer step 2 for her.**
