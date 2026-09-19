# TapeMap v2 — handoff

**Point a new session at this file first.** It is the entry point; work that was
found, measured and consciously postponed is in **`context/DEFERRED.md`** — read
it before starting anything new, it exists so nobody re-derives a finding that
already has numbers. The rules themselves are consolidated in
**`context/CHECKLIST.md`** (every rule with its
source, plus a chart checklist showing what currently passes and fails); every
strategy verdict is in `context/research-findings.md`, and the deep UI
history is in `context/ui-v2-dashboard.md`, and the operator's own edge is
specified in `docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`.

Last updated: 2026-09-09. **1066 collected; 1063 pass, 3 fail** (`pytest -q`,
2026-08-26 — 1041 plus 21 in `test_day_trades.py` for the paper day read back
from the trade log;
before that 1041 — 1021 plus 20 in `test_desk_numbers.py` for RV(5d), forward daily
theta and margin-at-shifted-spot;
before that 1021 — 988 plus 33 in `test_hedge.py` for the short-variance paper
module (band math, brake, average-cost futures inventory, ledger rows, and
nine integration cases through the real `trader.on_chain` tick);
before that 988 — 981 plus 7 in `test_warmap.py` for the anytime-start audit
repairs (each `confidence()` state constructed through a real feed sequence,
after the arithmetic was found dead);
before that 981 — 972 plus 9 for the late-start follow-ups: per-strike PREMIUM off
the same candles the OI backfill already fetches (7 in
`test_chain_backfill.py`) and `trapped_inventory.confidence()` on the warmap
heat rows (2 in `test_warmap.py`);
before that 972 — 941 plus 31 for startup backfill + day persistence:
`test_vpin_backfill.py` (13), `test_day_state.py` (15) and three more in
`test_chain_backfill.py` (the backfill tag reaching `/api/oiflow`'s rows);
before that 941 —
2026-08-23 — 900 plus 22 across `test_book.py` / `test_quoting.py` /
`test_trader.py`, the paper desk (HANDOFF-DESK.md §8f: risk core, quoting
layer, the self-trading paper book at `/api/paperdesk`);
before that 900 — 873 plus 27 across `test_levels.py` / `test_dwell.py` /
`test_hunt.py` / `test_sequence.py` / `test_driver.py` / `test_warmap.py`,
the OI war map (HANDOFF-DESK.md §8d: levels / dwell / hunt / sequence /
driver / warmap, `/api/warmap`, the ladder on desk.html);
before that 873 — 871 plus 2 in `test_desk_log.py` for the restart-baseline marker
on `desk_log.log_transition` (reviewer fix for commit b71f991, Finding 1);
before that 871 — 845 plus 26: two in `test_pools.py` for the two `pools.orders_for`
defects the Kite-bridge audit found (a touch-only price coincidence accepted as
a match when the true twin was absent; counts misattributed by list position
instead of by price) and a new `desk_log.py` (Phase 4 — the surface forward
log at `data/surface/`, the desk verdict-transition log at
`data/desk_log.jsonl`, the 09:15-15:30 IST market-hours gate, and latency
ring buffers published under `/api/health.latency`), sixteen in
`test_desk_log.py`, five more in `test_senses_api.py` (the latency ring
buffers honest-when-empty and once populated, `/api/health` publishing them,
and `server._log_chain_pace`'s orchestration — writes the surface line on a
successful fit only, diffs gear/conviction/deployable and writes ONLY the
changed field), and three in `test_eod_capture.py` for `capture_desk_record`
(5c — preserving the day's surface log and a desk_log snapshot alongside the
OHLC bars, same never-clobber-without-force discipline as the bars capture);
before that 2026-08-22 — 842 minus 3 (`forcing.py` deleted, superseded by
`fuse.py`/`regime.py`, see the 2026-08-22 entry below, taking its coverage
in `test_operator_objects.py` with it) plus 6 new in `test_senses_api.py`:
a composed-path test proving PIN and TRANSITION are now reachable through
`server._view_for`, two guarding the new inputs stay honest (None, not a
fabricated 0/False) below the engine's own warm-up and without Kite's
order-count bridge, and three on routing (`/` redirects to `/desk.html`,
`/api/health.feed` is null with a reason off the Upstox path and published
verbatim when wired); before that 2026-08-21 — 775 plus eighteen in
`test_desk.py` for `desk.py`'s risk/margin/
sizing rebuild: legal structure shapes (a strangle wing must sit outside the
expected move AND be delta-balanced against its partner -- the exact live bug
where a 12-point-from-spot PE was named a wing), max loss and breakevens per
structure (naked structures report UNDEFINED risk, never a fake ceiling), a
documented [I] margin floor (defined-risk = max loss; naked legs = a
percentage-of-notional model, explicitly never SPAN), the real score (edge
per rupee of margin, ranked on that instead of raw edge), and sizing that
follows from stated capital and is capped by the thinnest leg's own OI and
by a bid/ask spread wide enough to swallow the edge; before that 775 after the
run 2026-08-15: 569 after the ponytail cleanup below, plus six in
`test_zone_state.py` pinning the §1b zone machine; `test_docs_claims.py`
pins this very number against the run). Branch:
`feature/dashboard-v2`, uncommitted cleanup in the tree at the time of
writing (see the 2026-08-15 entry). *No commit hash here on purpose: any hash this line names is stale the
moment this file is committed. `git log --oneline -1` and
`git status --short` are the live answer.*

### STATE OF THE APP — end of 2026-08-25, read this before anything else

Written for whoever picks this up cold (operator's order: "any body else work
so they exact know where we are"). Every claim below is verifiable — the
command or file that proves it is named.

**What this system is now.** One Python server (port 8765, Upstox feed,
`start-v2.bat`, ALWAYS launched detached — a 12:05 crash today killed it as a
child process and cost 30 min of every forward log) + two frontends + one
Chrome extension:

- **`ui/toolb.html`** (+ toolb.js/css) — THE NEW TOOL, built clean-room by a
  model that never saw the old design, through 5 reviewed rounds in one day.
  Five screens (asli jawab / maidan / flow aur zeher / vol aur tax / paper
  book), Hinglish voice, the OI battlefield (4-state OI×premium paint at
  5m/15m/day, fuel tank off the server's own trapped-inventory ledger with
  its confidence, migration arrows, acceleration with the NEW-wall sentence,
  pain curve, FUT patti, campaign timeline), a "kaisa din hai" day-type tile
  (5 rules, MIXED handled honestly), answer flip-changelog + 60-min stability
  meter + answer age, full persistence (localStorage per date+index,
  high-water snapshots, server-wins reconcile — survives refresh, server
  death, and a server that lost the day), and the server's coverage honesty
  rendered verbatim. **PENDING: the operator's "final kar" after one live
  morning — on her word, toolb.* replaces desk.html.** Old `ui/tool.html`
  (the parallel build that lost the judged comparison) is deleted; its best
  ideas were absorbed into toolb during cross-critique.
- **`ui/desk.html`** — the OLD desk, still the default screen, rejected
  wholesale by the operator 2026-08-25 ("data ki boilerplate") but left live
  until she approves the replacement. Do not invest in it.
- **PaperDesk extension** at `C:\Users\kaam\Downloads\paperdeskextension1.22.0`
  — v1.22.5 on disk (big-print reads OFF; its changelog file is
  `CHANGES-1.22.0-to-1.22.4.md` in that tree). NOT yet reloaded in Chrome —
  the operator still has to reload at chrome://extensions + refresh Kite.

**What happened today (the detailed entries below have the full accounts):**
VPIN shadow module's first live day validated its designed combo on the
expiry squeeze (wall-unwind alerts 11:56/13:55 → burst 14:39, three
one-second imb-1.0 buckets, pct 100% → box break 14:41; ~45 min of warning).
Post-close batch: drag OWED_FLOOR (tax-blowup dead), vpin same-day
seed/restore + `/api/vpin` (cross-day seeding was built, then REJECTED by
the operator the same evening — expiry/vol regimes reshape the distribution
daily; the mute morning is the honest price). Then the anytime-start rule
("start anytime, backfill gives exact info") produced: startup backfill
(FUT bars were already whole; per-strike OI+premium minute grid via
`chain_backfill` with `backfill` tags end-to-end; VPIN morning BVC from
1-min bars into `data/vpin_backfill.jsonl`, NEVER the promotion log,
display-only — `SEED_LIVE_GAUGE_FROM_BACKFILL=False` is the operator's
confirmed decision), `day_state.py` (drag ring survives restarts), and a
77-piece audit (35 safe / 22 fixable / 24 lost) whose repairs landed the
same night: `Ledger.confidence()` arithmetic was dead (could never say
"low" — now weighed against `unwatched`), EOD capture had been writing into
`Desktop\new tool nifty` for 4 sessions (scheduled task repointed via
schtasks, orphaned captures recovered, and the "44% truncation" theory in
old 0h DISPROVED — the 08-24 cache matches Upstox exactly), and two false
`_coverage()` sentences corrected.

**Later the same night (after this section was first written) — the seller
pivot completed the build.** The operator ran an independent-design exercise
(two models, no app context, "what would YOU want on a zero-cost seller's
desk") and the convergence rewrote the DESK screen: it is now the seller's
five questions in decision order — GATE (trade/half/no-new-risk) · SURVIVAL
(gap table with real shifted margins + square-off distance) · AM I BEING
PAID (ATM IV vs RV(5d) [M], 252-vs-365 basis warning shown verbatim) ·
WHERE AM I (strike distance in σ, delta lamps) · MONEY GREEKS (rupees only)
· HISAAB — with direction/gear/structures demoted to a collapsed "MACHINE
KI RAAY [I]" drill-down (flip history intact, never the headline again).
And the short-variance paper module shipped: `hedge.py` delta-hedges the
paper book with paper futures (band 1.0 lot, brake 8/day/index, inventory
kept OUT of book.Book), forward hedge ledger (theta − hedge bill = net
variance, overnight gap exposure named daily), `/api/paperdesk.hedge`,
rendered on the PAPER screen. Server also gained `fit.rv5` [M],
`theta_day_est` (new Black-76 theta in gamma.py, verified against finite
differences), and `margin_shift`. Suite: **1041**. The EOD scheduled task
was repointed AND verified (see 0h — done, next run 26-08 15:35). First
live day for all of it: 2026-08-26.

**The pipeline, in order:**
1. **Operator's morning review** → "final kar" → rename toolb.* over
   desk.html (nothing renames before her word).
2. **Desk answer hysteresis** (DEFERRED 0i) — measured 42 flips/60m; the
   hold-time is HER call, sketch is in 0i. The UIs' client-side confirmation
   gates cover the reading meanwhile.
3. **Warm-start the state machines** (dwell/sequences/narrative) from their
   own logs — `data/senses/` (~784k rows/day) and `data/warmap/` are
   replayable; scope WITH the operator, it is the last big anytime-start gap.
4. **DEFERRED 0g** — DIVERGENCE afternoon theta-bias (discount afternoon
   trap votes until fixed).
5. **PaperDesk 1.22.5 reload** (operator, 2 minutes).
6. VPIN 30-session kill clock runs; day 1 recorded. BANKNIFTY VPIN only
   after NIFTY survives it.

**Where the truth lives:** this file (history), `context/DEFERRED.md`
(postponed with evidence), `data/*` forward logs (the record),
`/api/health.coverage` (what this process actually knows today), and the
operator's memory files in the assistant workspace. The anytime-start audit
report: https://claude.ai/code/artifact/4b30ccb2-f146-4414-a7ec-be8abcfb5981

### 2026-09-19 — the ladder record, levels and a second opinion on the Trade chart (spec 2026-09-19-orderflow-levels)

**The suite was already red going in.** `python -m pytest -q`: **1250 collected, 1247 passing, 3
pre-existing failures in `test_desk_numbers.py`** (`theta_day_est` returns `None` on three cases) — the
desk's code, untouched by this work. Not fixed here; not ours.

**What shipped.** orderflow-desk 0.3.1 posts each bar's `ladder` and the chart's `rowAnchor`
(`main.js:234-235, :244`). `tape_log.py` writes bars once by `t` to `data/tape/tape_<idx>_<day>.jsonl`
and the extension's marks once by `(t, kind, p, side)` to `ofd_marks_<idx>_<day>.jsonl`; registered in
`_isolate_mock_writers`, pinned in `test_day_state.py`. `prints.py` (pure) ports `decode.js`/`market.js`/
`board.js` — rebin, diagonal imbalance, stacks, per-bar POC and unfinished auction, the paired-row value
area, HVN/LVN — **pinned bar by bar against a fixture generated by the extension's own code over
2026-09-11** (`tools/gen_prints_expected.mjs` → `test/fixtures/prints_expected_2026-09-11.json`) — plus
cvd, prior-day levels, naked POC, and the `tm` family (absorption effort-vs-result, exhaustion delta
divergence at a new extreme, climax volume-shape; percentile-so-far; 0.75/0.50/0.90/0.15/6, NOT tuned).
`GET /api/tape` serves it all with the three sentences. ui-v2: `trade/tape.ts` polls it (30 s);
`LevelsOverlay.drawPrints` draws levels, bands, stack brackets, unfinished ticks and hollow lowercase
`a/e/c` beside the filled A/E/C; delta/CVD is a candl pane at 5 and 15 min only.

**Spec amendment, found during implementation (§E, commit `56ef7d1`).** `pct(x)` is now defined as the
fraction of prior bars **strictly below** `x`. With `<=`, every bar of a constant-volume series ranked
1.0 and the spec's climax rule fired on every quiet bar. The five thresholds above are unchanged.

**A test leak, found and fixed (commit `836f89d`).** Once the POST handler was wired into `tape_log`, a
pre-existing route test started writing three toy rows into the **live** `data/tape/` on every run. Root
cause fixed with a root `conftest.py` autouse fixture that points `tape_log.DIR` at a temp dir for every
test, plus a pinning test so this cannot regress silently; the stray file was deleted (toy rows,
`ladder: null` — not a real record).

**What was seen live.** Nothing yet — no live session has run against this code. Before the next one:
(a) reload the extension at `chrome://extensions` and refresh the GoCharting tab — it is 0.3.1 on disk,
0.2.0 is still loaded; (b) restart the TapeMap server **detached** (`START-HERE.md` §0.6 — never as a
child of an assistant session); (c) open the Trade tab at 5 min and look at: session POC/VAH/VAL lines,
HVN washes, LVN dashed boxes, prior-day lines, stack brackets, unfinished ticks, the hollow lowercase
`a/e/c` beside the filled A/E/C, the delta/CVD pane (only at 5 or 15 min), and the hover rows listing
each mark's `why`, and **count the tm glyphs against the legend's `drawn of served`** — the legend now
reports what the overlay actually drew, not what the reply carried, and the two must agree; (d)
`data/tape/` currently holds only **seeded** records for 2026-09-11 and 2026-09-18 (rows `src: "seed"`,
from `tools/seed_tape_from_ofd.py`) — no socket-written day exists yet, and those two days hold **BAR
records only**. No `ofd_marks_*` file exists for either of them, so their extension-mark population is
**empty, not seeded**: an export carries no marks, and a day with no marks file is a different fact from
a day the extension watched and detected nothing on. That is exactly what `marks.ofd_why` now says,
in those two sentences.

**One measured thing she should know before session one.** The unfinished-auction flag measured **0**
across both recorded sessions, at rowSize 5 **and** at rowSize 1 [M]. The port is faithful — the
extension's own engine finds none on those days either, which is what the row-1 parity fixture pins —
and spec §J.4 keeps the extension's rule unchanged, deliberately. But the floor is
`max(3, 2 % of vol)` **on BOTH sides of a single extreme tick**, which on a 1,000–4,000-lot bar means
20–80 lots [M] resting on each side of one price, so she should not sit waiting for a tick that
essentially cannot appear on this instrument at these sizes. Stacks are a different story: 0 at rowSize
5, **68** at rowSize 1 on 2026-09-11 [M], which is why the second fixture exists.

**Two pre-existing conditions, disclosed.** orderflow-desk's rebuilt `dist/` (commit `7ef87e2`) also
bundles the operator's uncommitted `src/` WIP (`fit.js`, `taps.js`, `boot.js`, `overlay.js`) — the
bundler inlines everything under `src/`, so this was unavoidable and pre-existing, not introduced here.
`ui-v2` has no test runner; the Trade-chart UI work is typechecked (`npx tsc --noEmit`) only and stays
visually unverified until the live session in (c).

**The final review's fixes landed** (commits `90ab3be` Python + fixtures + tests, `16ca562` ui-v2, and
this docs commit): the record's bar loop no longer raises on a corrupt entry, one mark filter serves both
the file and the wire, the exhaustion window reads only bars that have both extremes, `/api/tape` stops
serving the ladder and says which absence an empty `ofd` list is, the tm glyphs fan out per bar and the
legend counts what was drawn, and the seed tool refuses to overwrite a real day or seed a non-5m export.
Suite after: **1267 collected, 1264 passing**, the same 3 pre-existing `test_desk_numbers.py` failures.

**Not done, on purpose.** No scoring of either mark family. The operator looks for five sessions
(spec §K); then she states the bar in `research-findings.md`, pre-registered; then a scorer exists.
The `tm` thresholds are not tuned before that. Spec 1b (`2026-09-19-convergence-chips-design.md`)
builds on this record next.

### 2026-08-25 night — when the tool is started stops deciding what it knows

Two halves of one complaint, both in the operator's words: *"i have to start
everything before 09:15 and by any chance if i m late let say i open my laptop
at 11 — pta chle morning ki koi info nhi h, phir to reliable he nhi hoga"*, and
*"7:30pm ko bhi kholu to dekh paaoun kya hua ... abhi to ui he khali ho
jaata"*.

**What was ALREADY solved, verified before writing anything** (the honest half
of this entry — two of the four asks needed no code):

- **FUT 1-minute bars.** `live.build_session` re-fetches the WHOLE session from
  REST on every refresh cycle (`_intraday` → `_upstox_bars` →
  `upstox_rest.intraday`). The tape has never had a late-start hole and does
  not need one built.
- **The per-strike OI timeline.** `chain_backfill.py` has existed since
  2026-08-07, born from this exact objection, and is wired at
  `ChainPoller._kick_backfill` — fired once per index after the first
  successful poll, on a daemon thread, rebuilding `ChainState.minutes` from
  per-leg intraday candles and never overwriting a mark the socket recorded.
  `/api/oiflow` and the war map's time dimension were already reconstructing.
  It was missing only its TAG (below).

**Rate limits: the throttle already is the compliance.** A full NIFTY window is
~61 strikes → 122 REST calls, ×3 indices ≈ 366 at startup, but every call goes
through `upstox_rest._throttle` (`MIN_GAP` 0.25s, one module-level lock shared
by every thread) — a hard ceiling of 240 req/min against Upstox's 250/min.
**The strike list was deliberately NOT capped to ~30.** `oi_flow` SUMS the row,
so a morning rebuilt on 30 strikes next to an afternoon observed on 61 produces
a step in call/put totals that reads as a real OI event — the same
"a partial sum is not a sum" rule `chain_backfill` already enforces per mark.
Fewer calls would have bought a plausible, wrong table.

**What was actually built:**

- **The tag, end to end.** `chain_backfill` writes `"src": "backfill"` into
  each rebuilt mark; `ChainState.oi_flow` republishes it as `backfill` on every
  row; `/api/oiflow` adds `backfill_marks` / `marks` for a header. The live
  writer sets no `src`, so ABSENT MEANS OBSERVED — pinned by a test that reads
  `ChainState.update`'s source.
- **`vpin.from_bars`** — the morning's toxicity buckets rebuilt BVC-style from
  1-minute FUT bars, reusing `Gauge` whole (same bucket size, same imb, same
  window mean, same Rank), primed at zero so 09:15's volume is not swallowed as
  the vtt baseline. Ceiling stated and TESTED: one sign per minute is smoother
  than the live frame path, so a backfilled reading is generally LOWER on the
  same tape. **Rows go to `data/vpin_backfill.jsonl`, never
  `data/vpin_log.jsonl`** — that file is the promotion evidence for a shadow
  module on a declared 30-session kill clock, and a reconstruction written into
  it is indistinguishable from an observation the moment it lands.
  `server._backfill_vpin` runs at startup, only when the gap is real, cut off
  at the first live bucket; `/api/vpin.series` concatenates the two with a
  per-row `backfill` + `src`, never summing or ranking across the join.
- **OPEN OPERATOR DECISION, parked OFF:** `server.SEED_LIVE_GAUGE_FROM_BACKFILL
  = False`. Seeding the live gauge's same-day percentile from backfilled
  buckets would end the mute morning a late start currently pays for — but a
  percentile is only honest over ONE population, and BVC's smoother
  distribution would push the reference DOWN and make the first live burst rank
  higher than it deserves, on exactly the mornings this would be switched on
  for. `/api/vpin` publishes the flag either way. Hers to flip.
- **`day_state.py`** — the day's RAM-only series written down, atomic rewrite,
  one file per day under `data/day_state/`, reloaded at startup for the SAME
  day only (`vpin.Gauge.seed`'s rule, same reasoning: a stale series that
  renders beats nothing only until tomorrow morning). `_SENSES["drag_day"]` was
  the one day series with no forward log behind it. Saved every 60s from the
  senses loop beside the other disk writers, and NOT market-hours gated —
  unlike `desk_log`/`sequence`, which are forward records where an out-of-hours
  row would corrupt the population; this is a snapshot of state, and 15:35 is
  when it most needs to be on disk.
  **Restored rows carry NO `backfill` tag**: they were observed, by an earlier
  process on the same day. `/api/drag`'s `day.restored` says only that this
  process did not gather them, so "since start" reads as the session's start.
- **`/api/health.coverage`** (also on `/api/vpin`, `/api/drag`, `/api/oiflow`)
  — `server_up`, `late_min`, and two named lists: what has a reconstructed
  morning and what has none and never will (IV/greeks/GEX/the fitted surface,
  the drag anchor, dwell + the sequence machines + every war-map narrative
  event, the paper desk's decisions). Rule 6 in one place: a screen opened at
  11:02 gets *"could not check — server started 11:02, 107 min after the
  open"*, not an empty chart. `/api/drag` also grew `day_why` so an empty trace
  cannot read as a zero tax.
- **`_isolate_mock_writers` grew two lines** (`day_state.DIR`,
  `VPIN_BACKFILL_LOG`), and a test now pins the whole list by reading that
  function's source — a writer added without a line there leaks silently and is
  found 33 hours later, which is exactly how 2026-08-24 went.

**IV surface morning: deliberately NOT attempted.** REST candles carry no IV
and no greeks, so a reconstructed smile would be a fit to inputs that do not
exist. `chain_backfill`'s docstring already drew that line in 2026-08-07 and it
still holds; the coverage list names it instead.

**Not proven:** zero live sessions. `_backfill_vpin` has run only against
synthetic bars; the first real test is a deliberate late start.

**Two follow-ups, same night** (operator: *"ye to kabhi start karu ye bhr lega
apne ap haina"*):

- **Per-strike PREMIUM now rides the OI backfill.** The option candles
  `chain_backfill` already fetches carry closes, and only OI was being kept —
  so a late start rebuilt one axis of the UI's OI×premium paint and left the
  other blind. `_minute_oi` → **`_minute_leg`**, returning a third element (the
  close series) from the SAME call: no extra request, no extra rate-limit
  budget. Marks gain `px: {strike: (ce, pe)}` on BOTH paths — `chain_backfill`
  and `ChainState.update` — so a rebuilt morning and a watched afternoon are
  one shape. `oi_flow` rows republish `px` for the **selected strikes only**
  (`/api/oiflow?strikes=…`), with `px_why` on the response when there is no
  selection: a premium sum across strikes is not a quantity, and the whole
  chain would be ~180KB per poll.
  **Premium is a LEVEL, OI is a CHANGE**, deliberately: the live chain
  publishes `oi_chg` so the grid matches it, but there is no house convention
  for premium change and baking one window in would fix the caller's choice
  forever. The UI joins on `row.time` + `row.px[strike]` and differences it.
  The existing `backfill` flag covers both axes — they come off the same mark,
  so they are always the same population.
  *Corrected on the way here:* a test was written asserting "OI present,
  premium missing" is possible. It is not — `candles_to_arrays` drops any row
  whose OHLC will not parse, so such a row reaches NEITHER series. The fixture
  that "proved" it was lying about the wire format. The test now pins the real
  invariant (`set(rec["px"]) == set(rec["k"])`); the defensive `.get(m)` stays
  as the honest shape if that ever changes.
- **`confidence()` on the warmap heat rows.** `heat[]` exposed `ce_pain` /
  `pe_pain` but not the ledger's own coverage, so the fuel tank could not tell
  a basis built watching 90% of a wall from one that saw 10% after an 11:00
  start — the two produce the same-looking number and the second is nearly
  worthless. One field per strike-side: `ce_conf` / `pe_conf`, straight from
  `trapped_inventory.Ledger.confidence()` (`none`/`low`/`session`).
  **`None` and `"none"` are two different answers** and a test pins both:
  `None` = there is no ledger for this leg; `"none"` = the ledger exists and
  has not seen a build yet. This is NOT a confidence score under house rule 4 —
  it is a coverage statement about the ledger's own observation, the same
  string `Ledger.snapshot()` has always published, carrying no claim about
  whether the read is right.

### 2026-08-26 — the paper day, read from the log; and the why that was not durably logged

Operator reviewed the paper desk's first full day and approved it (*"acha kaam
kiya h isne"*); the PAPER screen is being redesigned and needed a real source.
Her bar: *"isko bhi redesign kr pta chlna chaiye kya liya kb kyu liye"*.

**The durability asymmetry, biting a screen she reads.** `closed_today` comes
off the IN-MEMORY book, so the 23:32 restart truncated it to 20 rows while
`trades.jsonl` held all **62** round trips for 2026-08-25. Same class as the
drag-trace hole. `/api/paperdesk` now serves `day_trades` built from the LOG.
Measured after the fix: `closed_today` 20, `day_trades` 62, refusals 84.

**A WRITER DEFECT, found by checking rather than assuming — and it was real.**
The why was NOT durably joinable per trade:

- `trades.jsonl` open rows carried `pid` and **no why**.
- `decisions_<day>.jsonl` carried the rule-9 sentence (`detail` +
  `evidence.forced_why`) and **no pid**.

Two files, no join key. So "why did it take this trade" was unanswerable per
trade from the durable record the moment the process restarted. **Fixed at the
writer:** `_open_from_fill` now stamps `forced_who` / `forced_why` / `gear`
onto the trade row itself (one file answers it), and `_log` gained `pid` so
entries, exits and refusals are cross-referenceable. Both pinned by tests that
read the writers' source, not just the readers' output.

**Historical rows get a best-effort join, tagged as one.** For the 62 trades
already written, the why is recovered from the decisions log on
(idx, strategy, timestamp) and every recovered row says
`why_src: "decisions-log join [I] on idx+strategy+timestamp"`. **36 of 62
matched**; the rest are `why: null` with `why_missing` naming the reason. The
gap is honest: the decisions `ts` is wall-clock while the trade `ts` is the
CHAIN's, so they differ by a second or two. **The join was deliberately kept
EXACT rather than given a tolerance** — BUY_CASCADE fires repeatedly on the
same index, and a *wrong* why attached to a trade is worse than a null.

**Which day is served: the latest session PRESENT IN THE LOG, not the calendar
date** — she reviews after the close, often past midnight, and a calendar read
would blank the screen at 00:00 on the session she is still looking at. `day`
and `day_is_calendar_today` are always published so nothing is ambiguous.

**Accounting is rupees and counts only** — `by_index`, `by_strategy`, each
`{net, trades, open}`. A running position is counted under `open` rather than
summing as a zero-P&L trade. No hit rate, win rate or expectancy anywhere; a
test asserts the banned words never appear in `day_accounting`'s source, so a
helpful future edit fails loudly. Measured for 08-25: NIFTY +8,300.5 (30),
BANKNIFTY +6,795.0 (25), SENSEX −2,008.0 (7).

### 2026-08-25 night — the three numbers the desk screen had to declare missing

Closed server-side so tomorrow's screen is whole. Operator's standing bar:
*"proper tool k tarah chle... backfill to give exact info"*.

- **RV(5d) on `/api/surface`**, per index, as `fit.rv5` / `fit.rv5_why`. [M] —
  measured from `data/backtest/fut_*.json`, the tool's own captures (NIFTY at
  the top level, the others in their own subdirectory; reading the wrong one
  would report NIFTY's vol under another index's name, so a test pins it).
  Method stated in the payload: last close of each session, close-to-close LOG
  returns, SAMPLE stdev (n-1), annualized sqrt(252). Under 5 usable sessions
  it returns a REASON, not a number — a vol printed off two sessions is noise
  wearing a number's clothes. A corrupt capture is skipped, never zero-filled.
  **The 252-vs-365 basis is published, not buried** (`basis_note`): variance
  accrues on trading days, but IV's T here is 365 calendar
  (`gamma.DAYS_PER_YEAR`), and comparing RV to IV is the entire point of
  having this — so the mismatch travels with the number.
- **`gamma.theta()` / `theta_day()` — new, and the only real math in the
  batch.** Black-76 theta did not exist in the repo. Derived in the docstring:
  `theta = r*price - e^{-rT} F n(d1) sigma / (2 sqrt(T))`, one expression for
  both calls and puts because `F n(d1) = K n(d2)` collapses the density terms.
  **Verified against finite differences of the existing `bs_price`** rather
  than a remembered formula — a sign error here reads as free money. Daily
  decay divides by 365 CALENDAR, matching the basis `surface.years_to_expiry`
  and `chain_live.t_years` already use; dividing by 252 would have inflated
  daily decay ~45% and shown it as income.
- **`/api/paperdesk.theta_day_est`** — the forward answer to *"ek din nikal
  jaye = +Rs Z"*. Deliberately a SECOND theta number and the method says why:
  marks' `theta_gamma_resid` is a measured RESIDUAL with gamma fused in (what
  happened); this is a model estimate of one day ahead. Legs with no IV are
  NAMED and excluded — a partial theta shown as the whole book's understates
  income exactly when a leg is unquoted.
- **`/api/paperdesk.margin_shift`** — margin at spot ±1%/±2% on the current
  paper book, same `desk._naked_margin` model reused rather than a second one
  that could disagree. The survival table's "free margin" row had been
  assuming margin CONSTANT while spot moves; it is a percentage of NOTIONAL,
  so a short book's margin rises with the index — the mechanism the crowd
  doctrine (rule 5) turns on. Its could-not-check note can go.
  **Named ceiling:** spot shifts, IV does not. A real SPAN run raises both, so
  these are a FLOOR on the squeeze, and the payload says so.

### 2026-08-25 night — SHORT VARIANCE: the paper delta-hedger and its ledger

Operator approved (*"haan bna de"*). The premise is her broker arrangement, not
a model: at zero cost (rule 8) hedging becomes viable, because hedging is a
high-frequency low-edge activity that retail friction normally eats alive. With
the friction gone a strangle stops being a range bet and becomes **short
variance** — `IV sold − RV realized`, the identity HANDOFF-DESK §1 already
writes down, with the hedge as the mechanism that converts it to cash.

**New `hedge.py` + wiring in `trader.py`. PAPER ONLY** — paper futures against
a paper option book. A test asserts by source inspection that the module
contains no order path at all; rule 10 gets an assertion, not a comment.

**Two structural decisions, both about correctness rather than convenience:**

- **The hedge inventory is deliberately NOT in `book.Book`.** Hedge positions
  there would move `book.risk()` → `forced_ratio` → trader's `FORCED_MIN` entry
  gate — a *shadow* module silently steering the live paper desk. It reads net
  delta and never writes it. Pinned by a test that asserts no `FUT` leg ever
  appears in `book.positions` while a hedge is on.
- **Hedging is PER INDEX with that index's own future**, not NIFTY FUT against
  everything. Hedging BANKNIFTY delta with NIFTY futures would be wrong and it
  is the same code. Separate inventories, separate brakes.

**Constants, all [I], all with their starting rationale in the docstrings:**
`BAND_LOTS = 1.0` (the hedge instrument is a whole futures lot, so a
correction under one lot cannot be expressed — a tighter band would churn on
deltas the instrument cannot answer); `MAX_HEDGES_DAY = 8` (deliberately NOT
the manual-discipline 4, which is a human attention limit; a systematic
hedger's brake exists to cap a malfunctioning or whipsawed loop — 8 is ~one
rebalance per 45 min, loose enough not to bind on a trending day, tight enough
to stop a runaway inside an hour); `GAP_MOVE_EM = 1.0` (same value and shape as
`book.STRESS_MOVE_EM`, reused so the two readings cannot drift).

**A real defect found on the way in.** `book.mark_position` silently skipped
legs whose delta had not arrived, so `net_delta` came back a smaller number
with no hint it was partial. Harmless while nothing acted on it; **not**
harmless once a futures trade is sized from it. `mark_position` now publishes
`delta_why` naming the legs, and the hedger REFUSES to hedge while it is
non-empty rather than hedging a confidently understated delta.

**The brake is never silent.** On binding it logs a refusal once per index per
day (`BRAKE ... net delta N lots is now RUNNING UNHEDGED`), writes a refusal
row to the ledger, and `/api/paperdesk.hedge` carries `brake_hit` + `brake_why`
continuously. An unhedged book that looks hedged is the worst reading this
module could produce.

**EOD flattens the hedge, and the flatten does not consume a brake slot.** The
paper desk squares off options at 15:18; a hedge left on would become an
outright overnight futures position at that instant. Refusing to *close* because
a counter is full would be the worst possible reading of a risk limit. The
daily summary is taken BEFORE the square-off, on the book as it actually stood
— afterwards the gap number would read zero for a reason unrelated to hedging.

**Honest ceilings, all carried in the API note and the ledger rows:** fills
assume no spread paid (front-of-queue, so hedge cost is a LOWER bound and
`net_variance` an UPPER one), and the INDEX stands in for the future — carry
cancels on a round trip, only carry *drift* is unmodelled (`book.py` already
marks FUT legs this way). `theta_collected` is the sum of
`attribution.theta_gamma_resid`, which **bundles theta with gamma and
higher-order** and says so; isolating pure decay needs a per-snapshot greek
path that is not built.

**Gap risk stays unhedged by construction** and the daily row says so: the
short-variance identity holds for *continuous* rehedging, and overnight is the
discontinuity — which research-findings already calls informed repricing with
no edge to lean on.

**Evaluation is the ledger, over sessions, by the operator.** No rate, no win
count anywhere — a test asserts the banned key names never appear in a row.
Zero live sessions: every number here is arithmetic over synthetic ticks.

### 2026-08-25 night — the audit that checked the thing just built

The operator asked for exactly this: *"ek baar check bhi kr lena jo abhi tak
banaya h wo sb bhi... other wise it will be always wrong"*. Three findings,
all confirmed by tracing before anything was changed. Two of the three were
defects in code shipped HOURS earlier, which is the §9 lesson landing again:
the suite was green through all of it.

- **`Ledger.confidence()` was arithmetically dead — it could never return
  "low".** `seen_build` only grows (`feed` adds every build); `size` shrinks on
  every exit. So `seen_build >= size` is an invariant and the old test
  `seen_build < size * 0.5` was unsatisfiable. Every ledger with a basis
  reported `"session"`, so the `ce_conf`/`pe_conf` field shipped that evening
  **always claimed full coverage** — the precise overstatement it was added to
  prevent. Root cause: `size` is our own bookkeeping, so measuring our
  observations against it can only ever say "we saw what we saw". The missing
  denominator is what we did NOT watch: `Ledger.unwatched`, the OI already
  standing at the first observation, built on an earlier day or before a late
  start. Now `seen_build / (unwatched + seen_build)`. The operator's own case —
  11:00 start, 9.0M wall, +0.5M by the close — reads 5% → `"low"`; a strike
  watched from scratch reads 100% → `"session"`. Deliberately cautious on
  churn. **The old test asserted set membership** (`conf in (None,"none",
  "low","session")`), which passed happily while one member was unreachable;
  replaced by 7 tests that CONSTRUCT each state through real `feed` sequences,
  plus a source-level guard against the dead comparison returning.
- **EOD capture had been writing into the WRONG REPO.** The "TapeMap EOD
  capture" scheduled task executed `Desktop\new tool nifty\eod_capture.bat`.
  Both repos' `.bat` files are identical and correctly portable
  (`cd /d "%~dp0"`), so each ran fine into its own folder — last run
  2026-08-25 15:35, **result 0, a clean success into the wrong tree**. A
  directory diff found exactly THREE orphans (NIFTY, `BANKNIFTY/`, `SENSEX/`
  for 2026-08-25); everything older had been backfilled here by manual runs.
  All three were verified for day, shape and `_meta.source`, then copied in
  without clobbering. **Repointing the task was deliberately NOT done** — it is
  persistent machine configuration and an agent's request is not the
  operator's consent; the one-line `schtasks` command is in DEFERRED 0h.
- **DEFERRED 0h's "44% short" was DISPROVED** — see the rewritten entry. Upstox
  REST for 2026-08-24 returns 385 bars totalling **2,374,190**, which is
  EXACTLY what our cache holds. The TV export's 4,224,415 was the outlier and
  was never reconciled before being used to indict our file. Nothing truncated
  ate VPIN's BUCKET_V median. The real residual is ~1% and structural: the task
  fires at 15:35 while the last bars land 15:34–15:39.
- **Two false sentences in `_coverage()`, both mine from earlier that night.**
  It listed "the war map's time dimension" as RECONSTRUCTED while the same
  payload said four lines later that dwell and the sequence machines are not —
  `chain_backfill` fills `ChainState.minutes`, which only `/api/oiflow` reads;
  `warmap.py` never touches that grid and its boards start at process start.
  And it said no REST endpoint serves the drag anchor, which stopped being true
  the moment premium backfill landed: the 09:15 strikes and premiums are
  already fetched, nothing is wired to `drag.Board`. A wiring gap must not be
  filed under "never will". Both corrected, in `_coverage()` and in
  `/api/drag`'s `day_why`.

**NOT taken on:** warm-starting the dwell/sequence machines from
`data/senses/` and `data/warmap/` logs. That is the real remaining hole behind
an anytime start, and it is being scoped with the operator rather than guessed
at on a night shift.

### 2026-08-25 evening — the burst that validated the gauge, and the post-close batch

The first live day ended with the module's designed combination firing for
real: CE-wall unwind alerts at 11:56 and 13:55 (-7.7M, then -7.1M off the
24,200 wall), then at 14:39 THREE 60k buckets completed in one second, all
imb 1.0 buy-side, VPIN pct 100% — and the 24,100-24,200 expiry box broke UP
at 14:41 (spot 24,205.3). Max pain walked 24,150→24,200, the PE wall chased
to 24,150. Fuel (percentile) + side (the wall story) told it in order, ~45
minutes of warning first. One forward day proves nothing — the 30-session
clock runs — but day 1 is on the board.

Post-close batch shipped (942 tests, none fail):
- **drag.OWED_FLOOR = 0.5** premium points: `between()` refuses a rate when
  owed is a hair's width (expiry OTM legs printed "tax 15,543%" — arithmetic,
  not information). `/api/drag` frac now goes None instead.
- **vpin.Gauge.seed(rows, today)**: same-day replay ONLY — a mid-session
  restart resumes the gauge instead of going blind (the 12:36 crash-restart
  sat it out until 13:2x). server.py `_seed_vpin()` runs at startup, after
  `_isolate_mock_writers` so replays seed only from their isolated log.
  A cross-day percentile reference (trailing 30 sessions) was built first
  and REJECTED by the operator the same evening, correctly: expiry
  character and the vol regime reshape the imbalance distribution daily —
  this day WAS an expiry full of imb-1.0 buckets, and as a reference it
  would mark every normal morning "quiet" forever (the Andersen-Bondarenko
  critique, applied to ourselves). The percentile stays
  percentile-of-THIS-session; the mute morning is the honest price.
- **GET /api/vpin**: today's bucket series straight from the forward log
  (t/imb/vpin/pct) + live state. NOTE `_json()` takes BYTES — pass
  `json.dumps(...).encode()`, a dict dies after headers with an empty body.
- **The server must be launched DETACHED** (Start-Process, not a child of
  any assistant/terminal session): the 12:05 Claude-process restart killed
  the server with it and cost ~30 min of every forward log.

NOT done on purpose: /api/desk answer hysteresis (measured: 42 flips/60m,
4 flips in 35s — see DEFERRED 0i; the hold-time is the operator's call, not
a night-shift guess). eod_capture (0h) still open — tonight's capture is
equally suspect until fixed. The desk UI was rejected wholesale and two
clean-room replacements built and cross-critiqued (ui/tool.html by Sonnet,
ui/toolb.html by Opus — toolb judged the better base); desk.html stays live
until the operator picks.

### 2026-08-25 — VPIN shadow, the day strips, and one absorbed coin flip

**VPIN (order-flow toxicity), SHADOW, NIFTY FUT only.** `vpin.py` (pure,
stdlib, 9 tests): vtt-delta volume signed by tick rule, 60k-unit volume
buckets, |buy−sell|/V, mean of last 50, read as percentile-so-far.
BUCKET_V = 60,000 is ADV/50 with ADV the MEDIAN of the last 30 cached
sessions (2,936,408) — the first cut, 100k off the single session 07-17,
turned out to be one of the heaviest days in the cache and pushed warm-up
(MIN_HIST 10 buckets) to lunch. Wired in the senses loop (frame-paired ltp+vtt
via `ladder_of`), forward log `data/vpin_log.jsonl` (queued under the lock,
written outside it; --mock-chain redirects it), served on `/api/senses.vpin`.
Nothing downstream reads it. **Kill condition: 30 sessions from 2026-08-25's
open, pct ≥ 0.90 must precede range expansion at better than base rate.**
First live bucket 09:19:58 (imb 0.27). Replay check on the Aug-24 TV export:
warm-up done 10:07, the 11:03–11:24 one-sided run read 83→100% and the next
30 min ranged 2.2× base; the 13:52 flush (three buckets in one minute) was a
climax, not a warning — Andersen's critique, observed live.

**The day strips — first repair of the write-only-logs audit finding.**
`/api/surface` now carries per-index `day` (open/now/hi/lo of a, b at open vs
now, ~60-pt series; `_surface_day` reads the forward log back, size-keyed
cache, 3 tests in `test_surface_day.py`) and desk.html renders an "IV din"
strip with a verdict (vol aayi/nikli/flat + skew unwind vs steepening).
`/api/drag` grew the same: a chain-pace in-memory ring (`_SENSES["drag_day"]`,
Nones KEPT — a gap is a fact) and a "tax ka din" strip with worst-tax @ time.
Aug-24's story, now on screen: a 10.59→11.82% (+1.24), high 12.44 @ 11:32 —
the same minutes VPIN burst; skew −0.86→0.04, fear spent by close.

**engine.py ABSORPTION side was a coin flip, and it voted.** The event fires
only when the bar's range is near zero, so open-vs-close inside that bar is
noise — and that noise fed `trap_ev` as a TRAP-SETTING vote. Side now comes
from the 5-bar approach leg (who was winning INTO the wall got absorbed),
colour only as fallback when the approach is under one med60. The DIVERGENCE
afternoon theta-bias was found in the same audit and deliberately NOT fixed
(see DEFERRED). Thresholds untouched: they are [I], and the only legal tuner
in this house is a forward record, not a hand on a constant.

**The Aug-24 cache is ~44% short.** TV export total 4,224,415 vs cached
fut_2026-08-24.json 2,374,190 — the eod_capture gap does not just cost a
snapshot, it corrupts calibration inputs (the 30-session median above ate at
least one truncated session). Fixing eod_capture is now worth more than it
looked.

**PaperDesk went 1.22.1→1.22.4** (live tree `Downloads/paperdeskextension1.22.0`,
its own CHANGES-1.22.0-to-1.22.4.md): native VPIN in flow.js off the ws-tap
(bid/ask aggressor), TAPE cell in the mini bar (VPIN·IV·tax·trending-OI),
IV/tax chips on the chart's VPIN line, MARKET READS precision pass — every
read carries a [VPIN · IV · tax · OI] context suffix, a 09:15–15:30 gate
killed the 06:40 OI-noise reads, and a vpin burst read fires on the 90th-pct
crossing with the CVD lean. Version bumps are TWO places there: manifest.json
AND core.js PD.VERSION — one without the other trips its stale-files check.

### 2026-08-22 — Phase 0: wire the three dead gears, kill the orphans

`fuse.verdict()` (server.py, both call sites) never received `sigma_pctl`,
`vwap_flips_per_hr` or `walls_holding`, so `regime.decide()` could only ever
answer CASCADE or UNKNOWN and `direction.GAME` could never surface
SELL_PREMIUM (PIN) or STAND_ASIDE (TRANSITION) — 12 unit tests on
`regime.decide()` passed the whole time because nothing drove the composed
path. Fixed by wiring real, already-computed inputs: `sigma_pctl` and
`vwap_flips_per_hr` from the engine's own published session (`engine.Book.bw`
band-width rank and a flip-count over `z`, both gated on `engine.MATURITY`);
`walls_holding` from `pools.summary()`'s own `walls`/`orders_known` fields,
None (not False) when the Kite order-count bridge is not running. New
composed-path test in `test_senses_api.py` proves both gears reachable.

Also this session: `/api/health` now publishes the Upstox feed's own status
dict (`upstox_feed.UpstoxFeed.status()` had zero callers); `ui/desk.html`
gained a 30s-amber/90s-red staleness tier on the age readout and feed dot,
red reserved for a dead feed; `/` now redirects to `/desk.html` (302);
`start-v2.bat` opens the desk directly instead of the abandoned `ui-v2`
Vite app on :5173 (that section existed only to serve `ui-v2` and is gone,
not just skipped); `/api/gex` and its `ui/app.js` fetch are removed (dead,
zero other callers); `gamma.py`'s "never imported by engine.py" claim was
false (`engine.py:36` imports `implied_vol`) and is corrected; **`forcing.py`
is deleted** — see the operator-layer table update in `HANDOFF-OPERATOR.md`
for why it is safe (`fuse.py`/`regime.py` already do the same job, replayably
and wired live, which `forcing.py` never was); `_setup_logging` now rotates
(5 MB x 3 backups) instead of growing `tapemap.log` forever.

### 2026-08-15 — the hybrid: TapeMap paints on the Kite chart through PaperDesk

The operator's own PaperDesk extension (Downloads/paperdeskextension (2))
became the canvas; this server stays the brain. Design + phases:
`~/.claude/plans/look-at-this-chart-agile-hammock.md` (discussed with Opus 5,
operator-approved after mockups).

**Server changes (this repo, all tested):**
* `band_rotation.run_states(band=)` — THE ZONE (§1b, UNSCORED) runs on the
  SAME machine armed at d2/u2; receipts name the band they armed on; the
  default path stays byte-identical to §5c (pinned by `test_zone_state.py`).
* `live._at_interval` publishes `zone_state`/`zone_state_sell` beside
  `run_state` — additive keys, live mode only (the legacy replay payload
  never carried `run_state` either).
* `trigger_log.log_new` writes the zone population under `rule:"zone"` —
  arms via the SAME `_arm_rows` (parameterized), entries via the same loop,
  never pooled with `5c` (the dedupe key already carries `rule`). §5e's
  operator-side record now builds itself.
* `POST /api/paper_fill` → `data/paper_fills.jsonl` (SEPARATE from
  trigger_log by design; join on index/day/t). Verified live on the mock.

**PaperDesk changes (outside this repo):** two Phase-0 correctness fixes
(short-option margin was ~24× understated from the order pad — now strike-
based via `PD.strikeOf`; `tryFill` refuses quotes >30s old), a `tape.js`
poller (leader-tab only, 15s, worker-fetched for CORS) reducing the payload
to `pd_tape_v1`, and `chart-draw.js` renderers: zone carets/REF/countdown/
stop on index+FUT charts (price-anchored lines FUT-only — the ~80-pt basis),
WHY ribbon (squeeze verbatim-receipted, buildup quadrant, GEX/pin), the two
mechanics marks (ABSORPTION, OI-PEAK-LAG), premium-chart zone strips +
per-leg quadrant ticks + strike wall chips, and 17 opt-in narrative kinds
gated behind their scored verdict. Fills carry a `ctx` tape stamp and mirror
to `/api/paper_fill`. Checks: `node tests/phase0.js` + `tests/phase1.js`.

**Not done on purpose:** `chrome-ext/` is banner-superseded, not deleted —
it is the panel currently loaded in the operator's Chrome, and it stays
until the hybrid survives a live session. The server on 8765 was left
running old code; it needs one restart (`start-v2.bat`) to serve
`zone_state`, and the operator must reload PaperDesk in
`chrome://extensions` to pick up the new files.

### 2026-08-15 — the ponytail cleanup: ~4,300 lines gone, nothing live touched

A repo-wide lean pass (four parallel audits + verification). What left, and
why it was safe:

* **19 dead scripts deleted** (~4,000 lines): `upstox_probe.py` /
  `upstox_ws_probe.py` (self-declared throwaways whose measurements are
  recorded in `upstox_auth.py` / `upstox_feed.py` docstrings), `backfill.py`
  (fetches from Dhan's Data API, which lapsed 2026-08-05 — `eod_capture.py`
  is the living replacement), and the research-phase scorers whose verdicts
  are on the record in `research-findings.md` §2 (`orb_score`, `gap_score`,
  `stock_score`, `rotation_score`, `trail_score`, `confirm_score`,
  `band_backtest`, `expression_backtest`, `cross_*`, `continuation`,
  `contrarian`, `measure`, `gex_run`, `make_chain_fixture`) plus their two
  orphaned test files. §5's stop rule means they will not be re-run; git
  history keeps them if new evidence ever reopens one. **Kept on purpose:**
  `squeeze_score.py` (trigger_log imports it), `run_score.py`
  (test_band_rotation_run pins its constants), `signal_review.py` (live
  post-mortem CLI), `backtest.py` (test fixture loader).
* **Dead attributes/functions cut**: `GammaLayer.oi0/px0/oi_rank`, `Rank.n`,
  `Book.name/min_c`, `upstox_adapter.oi_series`, `upstox_proto.MODE_NAME` —
  each verified written-but-never-read across the whole tree.
* **Per-cycle waste removed** (the "fast" half): the refresh loop no longer
  `json.loads`es the full chain payload to read one spot float (the poller
  now publishes `box["spot"]` beside the bytes); `_tag_error` no longer
  re-parses/re-dumps the same "market closed" tag every 30s all night;
  `stick_state.json` is written only when the strike/drift actually changed
  (was ~4,500 unchanged writes a session); `upstox_instruments._blob` memoizes
  the parsed cache on (path, mtime); `engine.minute()` computes its
  60-bar median tolerance once per bar instead of five times, and the SPRING
  block reads the tracked `oi_peak` instead of rescanning every bar's OI.
* **Weekend-proof tests**: the four `test_contract_upstox.py` tests that
  failed every Sat/Sun (calendar-today vs session-day, caught on the first
  weekend run 2026-08-15) now pin their clock to the session day the code
  under test actually resolves. Suite went 589-with-4-weekend-failures →
  **569, all green any day of the week**.
* **Small consolidations**: trigger_log's `show`/`score`/`backfill` now parse
  through `read()` (one row-shape authority, as its docstring always wanted),
  `_mins` is `band_rotation._minute`, `structure._num` now rejects ±inf, and
  `chain_metrics._squeeze` calls `fl.window()` once per row.

Flagged but **not** touched — operator decisions, not cleanups:
`/api/contract` + the two-leg `detect` stack (~850 lines, fully tested, zero
UI consumers since 2026-07-31 — ship the pair chart or delete it), the v1
`ui/` + `/api/gex` (still what 8765 serves at root; retiring them needs
server.py to serve ui-v2's build first), `dhan_fetch`'s CLI half (welded to
expired July-2026 ids), and `trigger_log.backfill` (completed one-time
repair, kept as cheap insurance).

### 2026-08-14 — the tape stops evaporating, and NIFTY finally fires

**NIFTY produced its FIRST §5c entry, 2026-08-13 12:09, SELL u3 @ 24485.0**
(level 24514.38, trigger *"index high touched u3 24514.38 at 12:03, then closed
24485.00 below that candle's low 24488.60 2 bars later"*). It also armed three
times that session — 11:57, 12:00, 12:03, all `rearm` chains off `first_t
11:57`. **This falsifies two claims in the 2026-08-13 entry below**, which read
*"not one NIFTY row exists"* and *"it is NIFTY that has never armed"*. Both were
true when written and are not true now. NIFTY's live §5c record is no longer an
empty set; it is one entry and three arms.

**The record as counted 2026-08-14 02:00 from `data/trigger_log.jsonl`:**

| | |
|---|---|
| rows on disk | **276** |
| carrying `rule: "5c"` | **20** — 9 entries, 11 arms |
| by index | SENSEX 7 entries + 8 arms · NIFTY 1 entry + 3 arms · BANKNIFTY 1 entry |
| §5c days | 2026-08-10 · 2026-08-13 (17 rows, the busiest session on record) |
| carrying `unscored` | **20** — every §5c row |

**Still nothing is scored, and the reason is now named on every row.** All 20
carry the `unscored` sentence — *"no cached … session in `data/backtest/`, so no
bar after this row could be read — this row is UNMEASURED, not flat"*. The cache
still ends **2026-07-31**, because `backfill.py` fetches through `dhan_fetch`
and **the Dhan data API lapsed 2026-08-05**. No August session has ever been
materialised.

**Two 2026-08-13 rows WERE scored, off the live tape before it rolled** — by
feeding `trigger_log._outcome` the running server's bars rather than the cache.
Same function, same measures, full window to `FLAT_BY` 15:15:

| row | MFE | MAE | stop | opposite side |
|---|---|---|---|---|
| NIFTY 12:09 SELL u3 entry @ 24485 | **+34.5** @ 13:30 | −14.0 @ 13:54 | 24534.38, **never hit** | **none** — best −0.38σ |
| SENSEX 12:12 SELL u3 **arm** (level 78318.62) | +55.0 @ 13:24 | −91.15 @ 13:54 | 78338.62, **hit 12:15** | **none** — best −0.88σ |

The NIFTY short closed at 24472.9, **+12.1 from entry**, having peaked at +34.5
and given two-thirds back. The SENSEX arm **never triggered** — a new setup
armed at 12:45 before any candle closed below its reference low — and that is
the arm log earning its keep: price broke the stop level three minutes after
arming and ran to −91. **Stopped-out and would-have-worked are both recorded and
both true**, which is exactly what the operator's spec asked for.

**Not one signal reached the opposite side all day.** Both scored rows show
`d1`/`d2`/`d3` untouched, best excursion −0.88σ. The operator's exit plan trails
toward −2σ/−3σ when OI supports it; on 2026-08-13 that target never printed. One
session is not evidence — but if it repeats, the hold-for-target premise and the
tape are disagreeing and that is worth a pre-registered question.

**THE GAP THAT COST FIVE ROWS, and the fix.** The remaining five SENSEX entries
(09:36, 11:09, 12:09, 12:48, 14:03) are **permanently unmeasurable**. The live
tape is reachable only until the server rolls at midnight; `data/backtest/` had
nothing; and the chain snapshots that do survive
(`data/chain/chain_SENSEX_2026-08-13.jsonl`, 2047 rows) hold only `spot` and
per-strike OI — no futures OHLC, no volume, so the VWAP-banded bars the rule
runs on cannot be rebuilt from them. **`eod_capture.py` (`2499a12`) closes
this**: it reads the running server's `interval=1` tape and writes the RAW
`rest_intraday` shape — seven parallel arrays plus `_meta` — because
`squeeze_score.load` re-derives every session itself, and storing the served
3-minute banded bars would band them a second time on load. It **refuses rather
than writes** on a rolled server, a missing `built_at`, or a session under 60
bars, because `load` swallows bad files with a bare `continue` and a malformed
capture is indistinguishable from one that never happened. A broker-fetched
session still outranks a capture and is never clobbered without `--force`.
Scheduled **Mon–Fri 15:35 IST** as the `TapeMap EOD capture` task via
`eod_capture.bat`, which carries an absolute interpreter because a scheduled
task's PATH is not a shell's; verified by firing it once (`LastTaskResult 1`,
the correct refusal, logged to `data\eod_capture.log`).

**`exit_why` is now fully corrected** (`654d17c`). The 2026-08-13 entry below
records this as half-landed and **owed**; that debt is paid. No screen claims
an exit the tool never saw. **Precisely: `machine.ts` exports `lockNote`, and
`App.tsx` and `GlassBoard.tsx` render through it. `SetupCheck.tsx` does NOT
import it** — it was fixed separately on 2026-08-12 and renders from its own
`lockWhy: 'stop' | 'vwap' | null` prop. The wording is correct in all three;
the *shared helper* covers two. `lockNote`'s own docstring says it exists "so a
fourth screen cannot invent a fifth wording", and SetupCheck is a standing
exception to that guarantee — worth routing through `lockNote` next time
SetupCheck is opened, but it is not wrong today.

**Operational note:** the live server listens on **8765**.
`ui-v2/.impeccable/live/server.json` records a dead PID and port **8400** — a
stale artifact of the design harness that nothing in the app reads. Do not
diagnose a "dead server" from that file; check `netstat` for 8765.

### 2026-08-13 — 3-minute is canonical, and the live record is seven rows

**THE TAPE PUBLISHES 3-MINUTE CANDLES, and until 2026-08-12 it did not.**
`1002d52` splits `live.build_session` from `live.derive_payload`, `/api/data`
takes `?interval=`, `band_rotation.SCORED_INTERVAL = 3` names the one interval
§5c's 68.4% was ever measured at, and the Trade tab carries a switcher. Before
that the tape published 1-minute bars — so `RUN_WINDOW = 10` meant **ten
minutes live against the thirty the backtest measured**, and the arm and
trigger tests read 1-minute lows and closes. *Live was not running the rule
that was scored.* `band_rotation.py:850-862` states the standing rule: at any
other interval it is a different setup carrying no measured number.

**Signals differ by interval — asserted, NOT verifiable here.** The claim
carried into this session is that NIFTY on 2026-08-12 produced one SELL entry
at 1-minute (09:29, u3 24551.25, ref_low 24540.00, stop 24571.25) and none at
3m/5m/15m. Nothing in the repo holds it: `trigger_log.jsonl` has no NIFTY §5c
row at all, and `data/backtest/` has no August bars to re-derive from. Treat it
as an observation from a screen, not a record.

**What the live §5c record actually is** — counted 2026-08-13 from
`data/trigger_log.jsonl`:

| | |
|---|---|
| rows on disk | **263** |
| carrying `rule: "5c"` | **7** — 5 entries, 2 arms (`kind: "arm"`) |
| quarantined §1 one-candle rows | **256**, days 2026-08-04/05/06/07 |
| §5c days | 2026-08-10 (3 entries) · 2026-08-13 (2 entries, 2 arms) |
| §5c indices | SENSEX ×6, BANKNIFTY ×1 — **not one NIFTY row exists** |

**Nothing is scored.** `f15`/`f30` were never filled, and neither were the
outcome measures `69d3da0` added. The three 2026-08-10 rows carry their own
`unscored` sentence — *"no cached … session for 2026-08-10 in `data/backtest/`,
so no bar after this row could be read — this row is UNMEASURED, not flat"* —
and it is correct: the cache ends **2026-07-31** (NIFTY `fut_`/`opt_`
2026-04-01→2026-07-31; BANKNIFTY and SENSEX `fut_` 2026-06-01→2026-07-31). The
two 2026-08-13 entries carry no measure either.

**The operator's scoring spec, given 2026-08-13, is built** (`trigger_log.py`,
`score`): `anchor`/`anchor_px`/`anchor_t` name which price everything is
measured from; `mfe`/`mae` with their clocks are the max favourable and adverse
moves; `stop_px`/`stop_hit`/`stop_t` record whether the 20-point stop broke —
**recorded, not obeyed**, measurement continues past it; `bands` says how far
the OPPOSITE side's u1/u2/u3 (or d1/d2/d3) was reached, **read LIVE off each
arriving bar, never off the anchor bar's frozen numbers**, window to 15:15. The
rationale is the operator's: they hold when OI is heavy that side.

**`exit_why` is the RE-FIRE LOCK clearing — not a trade exit.** §5c point 7:
after an entry the next setup may arm immediately if stopped out, otherwise not
until VWAP is touched. `run_states` implements it as `lock` and its own
docstring calls `exit_why` "the bar the re-fire lock cleared". The operator
manages the trade and TRAILS; the tool records entry and stop only and has no
idea where they left. **This correction is only half landed:**
`trade/SetupCheck.tsx:868-877` was fixed on 2026-08-12 and now reads *"Re-fire
lock khula"* — but `App.tsx:2051` still renders `nikal gaye — VWAP par`,
`App.tsx:2217` puts `BAAHAR` in `document.title`, `GlassBoard.tsx:232-234`
still heroes `VWAP / par nikle / "the run is closed"`, and `machine.ts:37` is
the shared word that feeds both. **Owed: BAAHAR out of the machine strip and
the Glass board.**

**Arms are logged, and only since 2026-08-12** (`69d3da0`). `_arm_rows` writes
BOTH sides, d3 BUY and u3 SELL, at `interval: 3` **and no other interval**,
never off a forming bar, with `t_1m`/`extreme_1m` naming the minute inside the
bucket that made the extreme (`t_1m: null` plus `t_1m_why` on any doubt) and
`rearm` separating a moved reference from a fresh one. Earlier sessions hold no
arms by construction. **On disk: two arms, both 2026-08-13, both SENSEX d3 BUY,
both `rearm: false` — 09:33 (level 78072.89) and 11:06 (level 78061.59).**
*Correction to what was believed going in:* 2026-08-13 was **not** armless. It
is **NIFTY** that has never armed — zero NIFTY arm rows exist, and 2026-08-11
and 2026-08-12 have no arms of any kind because the logger did not exist yet.

**The NIFTY chain outage of 2026-08-12 — root cause found, fixed, uncommitted.**
`chain_live`'s reload trigger matched the substring `"token"`, and
`upstox_chain.poll`'s warming-up error ends with *"check the token first: python
upstox_auth.py"*. A socket that had merely not finished connecting therefore
forced a reload, the outer loop tore the socket down and rebuilt it, and
because the poller is a **round-robin** the FIRST index polled straight into the
next connect and tripped it again. **NIFTY was dead all session while BANKNIFTY
and SENSEX, polled 3.5s and 7s later, were fine on the same socket.** Fixed at
both ends: `chain_live.is_auth_error` matches 401 / unauthorized / invalid token
— the failure, never the advice — and `UpstoxChainSource.start` now waits up to
`upstox_chain.CONNECT_WAIT_S` (10.0s) for the socket instead of handing back a
feed still dialling. Covered by `test_chain_auth_error.py`.

**⚠️ THE d2/d3 READING TRAP — it cost two rounds of argument, 2026-08-11 and
2026-08-13.** The outer σ wash spans d2→d3, so a candle entering the blue reads
as touching the extreme when it has only reached **d2**; both times the low was
6–10 pts short of d3 with d2 tagged, and both times it was called a missed
signal. The chart now draws **d3 and u3 only** as solid 2.5px brass lines with
filled chips (`d3 · ARMS THE BUY` / `u3 · ARMS THE SELL`) — deliberately unlike
the 1px dashes every other level uses, because the first cut drew them as dashes
and they became the fifth indistinguishable dashed line. No other band edge is
drawn: `ba76dab` took the VWAP polyline and σ band edge strokes off, `12bae52`
dropped VWAP/±1σ from the chart's level list.

**Also landed 2026-08-11/12:** `8d85b7e` machine strip at shell level with a
`document.title` mirror · `ae76a05` a wall strike is compared in its own frame,
so call/put wall marks draw again (they never had) · `8760d15` the stop travels
with the level (`band_rotation._stop_px`) · `3dd9977` glance-bar scanner shrink
· `12bae52` the §5c SELL finally draws (`runDrawPlan` had rejected SELL/u3 as
"unexpected") · `f2c6c46` the day's §5c signals stay on the setup panel ·
`aedbd51` `/api/oiflow` publishes `chain_ok`/`chain_why` · `b2bf31d`
signal_review JSON snapshot · `69d3da0` Signals tab, `/api/signals`, ARM logging
and the scorer · `ba4be66` the Glass board · `daa2d51` critique and comps
committed, run logs gitignored.

**Uncommitted in the working tree** (`git status`, 2026-08-13): `chain_live.py`,
`upstox_chain.py`, `test_chain_auth_error.py` (the chain fix above) and
`ui-v2/src/trade/LevelsOverlay.ts` (the d3/u3 arming lines). `data/trigger_log.jsonl`
is also dirty — that is the live log appending, not an edit.

### 2026-08-09 — live collection is ARMED, and unverified until Monday

**The server was restarted 03:12 IST.** `/api/health` answers, broker `upstox`,
all three indices, uptime confirmed at 2.4 min so it is a fresh process on the
current code.

**What is NOT yet verified, and must not be called verified:** that a live
payload actually carries `rotation_run_sell`, and that a sell fire reaches the
log. Both need bars, and 2026-08-09 is a Sunday. A fresh process makes it very
likely; likely is not measured, and the last `trigger_log` bug lived in exactly
that gap.

**MONDAY, after 09:15 — run this first:**

```bash
python -c "import json,urllib.request as u;d=(json.load(u.urlopen('http://127.0.0.1:8765/api/data?idx=NIFTY')).get('days') or [{}])[-1];print({k:(len(d[k]) if isinstance(d.get(k),list) else d.get(k)) for k in ('rotation_run','rotation_run_sell','run_state','run_state_sell')})"
```

All four keys must return numbers. **`rotation_run_sell` missing = the server
is on old code and collection is half-blind.** After the close: `python trigger_log.py`.

**An empty table is NOT a failure.** The setup fires 1–2× a week. Whether
collection works is answered by the key check, never by the row count.

The 256 rows already on disk are quarantined (`rule != "5c"`) — they were
logged from `rotation`, §1's one-candle TOUCH, not the entry the chart draws.
The new sample starts at zero.

### The numbers that changed today, and one correction

`trail_score.simulate` is side-aware now (BUY proved byte-identical against a
pre-edit baseline, md5 `4a24a97f…`). Under the ADOPTED management on the
current §5c entries, NIFTY:

| | n | mean | median | hit |
|---|---|---|---|---|
| BUY d3 | 19 | +0.32 | **+6.90** | **63.2%** |
| SELL u3 | 18 | +10.18 | **−0.75** | 44.4% |

**Neither mean survives its own tail.** Strip one winner and BUY → −6.99,
SELL → +0.65. BUY's top two are +177.5 against a +6.0 net. Full table: §5f.

**CORRECTION worth carrying forward:** §1's "+4.8 mean / 56% hit" is from the
VOID one-candle trigger and was quoted twice today as if current. On the real
entries the buy's mean is +0.32. **The scored edge's case rests on median and
hit rate, not mean** — any surface quoting a mean for it quotes the wrong
statistic.

**C13 (new):** the fixed 30-minute exit is REFUSED. §1's own table measured it
and did not adopt it; it has no stop, so it is not a trade. It reappeared twice
today as a scoring bar because the refusal had never been written down.

### 2026-08-08 — the rail is full, and the sell side exists

- **SETUP CHECK panel** fills the 260px rail (`trade/SetupCheck.tsx`). Two
  tallies that are NEVER summed — TRIGGER (scored) and SAATH (unscored) —
  because C7 and C11 both measured "more conditions = better" as false. Three
  tick marks, not two: brass = the tool measured it, ink = the operator's hand,
  dashed amber = could not be checked. Ticks are keyed by session day, so the
  daily reset needs no clock.
- **The structure layer narrowed.** FVG, BOS and CHOCH are no longer drawn;
  SWING_H/SWING_L are, for the first time. Withheld kinds are COUNTED and
  disclosed in the `Chhupa hua:` line even with the toggle on.
- **Levels light up by proximity**, in σ so it self-scales across indices. Only
  ONE level takes a directional hue — the next one price is moving toward — and
  trap levels are excluded so their red keeps meaning "trap", not "down".
- **The u3 SELL mirror ships** (`band_rotation.run_states(..., side="SELL")`),
  built over C3's rejection at the operator's explicit instruction. `BUY 19 /
  SELL 18` over the 65-session NIFTY cache; the 19 matches the scored rule's
  own n exactly, which is the proof the buy path did not move. A `run_score`
  baseline was taken BEFORE the edit (`md5 50846ca6…`) and is unchanged.
- **The Trade tab speaks Hinglish** — chrome only. Every string the BACKEND
  authored and the UI quotes verbatim is deliberately untranslated.

**Read `context/DEFERRED.md`** for what was found, measured and postponed.

---

## 1. Boot sequence

Run BOTH in your own terminal windows. **Do not let the assistant start them** —
assistant-spawned processes die when its tool session recycles, which caused two
mid-session "disconnects" on 2026-08-03. The backend the operator started at
09:16 that day ran until close, untouched.

```bash
python server.py live 8765
```
```bash
corepack pnpm --dir "C:\Users\kaam\Desktop\new tool nifty\ui-v2" dev
```

### Running on Upstox instead (2026-08-05)

Dhan's **Data API subscription lapsed** on 2026-08-05 (401 / DH-902) and the
tape went dark. Upstox drives the whole stack for free, and both the chain and
the bars are wired behind one switch:

```bash
python upstox_auth.py          # once each morning; token dies 03:30 IST
```
```bash
TAPEMAP_BROKER=upstox python server.py live 8765
```

PowerShell: `$env:TAPEMAP_BROKER = "upstox"` on its own line first.

**The desktop shortcut does all of that now (2026-08-06).** `start-v2.bat` — the
`TapeMap v2` shortcut — sets `TAPEMAP_BROKER=upstox` itself and runs
`upstox_auth.py` whenever `.upstox_token` was not written today. Until this it
set **nothing**, so the shortcut launched both halves on Dhan, and the only
symptom would have been an empty chart. The commands above remain the manual
path; the shortcut is the one-click one.

Three things that were still reaching for Dhan on the Upstox path, all closed
the same day (`test_upstox_only.py`, 5 tests):

- `live._token()` opened `.dhan_token` **unconditionally**, so deleting a file
  the Upstox path never transmits would have killed the whole tape. It now
  returns `""` on Upstox — and still raises on Dhan, because a missing Dhan
  token there is a real misconfiguration, not something to paper over.
- `POST /api/token` (the **⟳ TOKEN button**) validated a Dhan JWT and wrote
  `.dhan_token` while the running tape and chain read `.upstox_token` — an
  "accepted" that changed nothing the operator could see. It now refuses on
  Upstox and names `upstox_auth.py`. The button itself is Dhan-only; there is
  no Upstox equivalent to click.
- A server **already up on 8765** has its broker fixed at *its* startup, not by
  the launcher. On the very first run of the fixed launcher this fired: a Dhan
  server from the previous afternoon (started 05-08 14:16) still held 8765, the
  launcher reused it, and the whole dashboard was placeholder data. Warning
  about it was not enough, so the launcher now **asks the server** via
  `GET /api/health` and offers to stop it. Verified against that exact stale
  process: the probe exits 1 (no such route), both Y and N branches correct.

**`GET /api/health` (2026-08-06).** Answers whatever the tape is doing —
`{ok, broker, started_at, indices}`. It exists because every other route
conflates two different failures: `/api/data` returns a `live_error` body BOTH
when the broker is dead and when the market simply has not opened. Two callers
need them apart — `start-v2.bat` before reusing a port, and the UI banner.

**The NOT LIVE banner was lying (2026-08-06).** At 02:50 it read *"the backend
is unreachable… An expired Dhan token is the usual cause"* while the backend
was up, answering, and correct — it had said `no bars yet for 2026-08-06`,
because the market had not opened. `data.ts`'s `fetchIdx` collapsed every
failure into one `null`, so "we checked and found nothing" and "we could not
check" rendered identically (§9 A1). It now returns `{reachable, why}`: only a
rejected `fetch` means unreachable; any HTTP answer means reachable, and the
backend's own sentence is shown verbatim. The ⟳ TOKEN button now appears only
where it can change something — never on Upstox, never when nothing answers.

- **Dhan stays the default.** Anything not exactly `upstox` runs Dhan, so a
  typo fails safe rather than moving the tool to another source while the tape
  keeps printing plausible numbers (`test_broker_switch.py`).
- `.upstox_app.json` holds the api key/secret (gitignored); `upstox_auth.py`
  writes `.upstox_token` and preserves the old one at `.upstox_token.bak`.
- **`oi_chg` means "since 09:15", not "since prior close"** — it will not match
  the OI Chg column on a broker chain. Deliberate: the 09:15 bar includes the
  pre-open auction, and today's positioning is what the writer score wants.
- Startup costs ~9s (34 throttled baseline fetches + resolve + connect); a poll
  touches **no network at all**.
- A connected-but-silent socket **raises** past 30s rather than re-serving its
  last snapshot — the 2026-07-27 frozen-tape lesson.
- `UDAPI100050` from Upstox means the WRONG TOKEN CLASS, not an expired one.
  An Analytics Token opens history only.

**`/api/contract` moved too, 2026-08-05.** The leg charts were the last thing
wired to Dhan — `chain_live.read_token`, a `dhanhq` client for the expiry, and
`dhan_fetch.rest_intraday` per option bar — so with the subscription gone the
CE/PE panes were a 500, not an empty pane. `build_contract` now branches on the
same `TAPEMAP_BROKER` switch (`test_contract_upstox.py`, 16 tests, offline).
Verified live 2026-08-05: NIFTY 24600 both legs, 129 3-min bars, no gaps, OI
7.98M / 5.13M, index series resolved to `NSE_FO|58072` from the dump.

Three things about that path that are NOT the same as Dhan's, and are disclosed
rather than smoothed over:

- **The pair needs the poller's snapshot.** On Upstox the chain arrives over
  the websocket `ChainPoller` owns, and this route will not open a second one.
  `server.py` already passes `chain_rows`; a direct call without one gets a
  refusal sentence, not a guessed strike.
- **Backfill charts the CURRENT front contract.** Upstox's dump carries live
  instruments only — an expired weekly is *absent*, not merely unresolvable —
  so `day != today` publishes `expiry_why` saying the bars are real but belong
  to a different instrument than the one that was front that day. Today is the
  only faithful reproduction.
- **The session is 10 minutes longer.** Measured 2026-08-05: Upstox serves
  **385** 1-min bars (09:15→**15:39**, with real volume — 424,385 on the 15:39
  CE bar) where Dhan served **375** (09:15→15:29). Nothing is wrong with either;
  the consequence is that the VWAP/σ tail differs between brokers. The operator
  is flat by 15:15, so it does not touch the d3 rule — but do not compare a
  Dhan-era band print against an Upstox one at the close and call it a bug.

Still on Dhan: everything in `dhan_fetch.py` (backtest tooling).

- UI at `http://localhost:5173`; Vite proxies `/api` → `127.0.0.1:8765`.
- **The Dhan token expires daily** — first click of the day is **⟳ TOKEN**.
- `corepack pnpm`, never bare `pnpm` (not on PATH).
- **"The app stopped" → check BOTH ports:**
  `netstat -ano | grep -E ":(8765|5173)"`. Backend alive + Vite dead is the
  common case; no data is lost, just restart Vite.
- For maximum stability during a live session, `pnpm --dir ui-v2 preview`
  serves the built `dist/` (own proxy block, no HMR to fall over). Trade-off:
  code edits need a rebuild.

## 2. Gates — all three before any commit

```bash
corepack pnpm --dir ui-v2 exec tsc --noEmit
corepack pnpm --dir ui-v2 build
python -m pytest -q
```
**432 tests as of 2026-08-07.** `vite build` does **not** typecheck — run `tsc` too.

---

## 2026-08-07 — the chart marks the entry now, and the morning survives a restart

Four things landed. Read this before touching the rotation layer or the chain.

**The chart was marking the wrong bar, and no longer is.** `rotation` is §1's
one-candle rule, which `research-findings` marks **VOID** — it fires when a bar
tags d3 and reverses inside that same bar, so every pill sat on the **touch**.
The operator enters on the **close that breaks the touching bar's high**, one or
more bars later. `live.py` now publishes, additively:

    rotation_run   §5c's two-candle ENTRIES, 1:1 with bars
    run_state      the same machine per bar — WAITING / ARMED / TRIGGERED /
                   IN_TRADE, plus ref_high, candles_left, exit_why

`rotation` is still published and still read by v1's `ui/app.js`. The two mark
different bars, so **neither is a fallback for the other**; the UI says so when
`rotation_run` is missing rather than substituting.

`band_rotation.run_states` is the one loop; `detect_index_run` is a one-line
view of it. The refactor was proven byte-identical over the whole cached corpus
(152 sessions, 39 signals, same sha256 before and after — the baseline was
captured BEFORE the edit, which is the only reason it proves anything), and
`run_score.py` still reproduces every published figure.

**The 09:25 and first-of-run filters left the frontend.** They were in the
scorer AND hand-written in `LevelsOverlay` — one rule in two languages, which
is how the original gap opened. Both now live in `run_states`. `rotDrawPlan`
became `runDrawPlan` and no longer filters: it VERIFIES, counting anything §5c
cannot legally emit as a *backend disagreement*. That count should never print.

**`chain_backfill` rebuilds the morning.** The chain is only ever recorded live
— Upstox's socket has no history and `_warm_start` replays only this tool's own
file — so a poller starting at 12:18 had no morning while the chart beside it
showed 09:15 onward. It now refills `ChainState.minutes` from REST after the
first successful poll, on a daemon thread, writing **only marks earlier than
anything recorded**. Verified against the socket's own file: 122 overlapping
marks, per-strike `oi_chg` exact on 82% of 4,148 values, aggregate within a
median 1.45%. **It fills `minutes` and nothing else** — REST candles carry no
IV or greeks, so GEX and anything gamma-weighted stay honestly absent.

**The OI pane says what happened.** It was one grey line of the LEVEL, which
answers "how much" — a question nobody asks mid-session, and explicitly not
what the operator's rule uses (*"oi is lagging so we need to prempt by the
change"*). The pane label is now a sentence:

    PE 24600 · SHORT COVERING — writers covered 4.57 L · 79.78 L open · -5.37 L today

Four states, and the noun follows the contract: **writers/buyers** on an
option, **shorts/longs** on the future. A flat close or flat OI says "no read"
instead of guessing one of four directions.

### Settled — no longer to be asked

- **Stop is 20 points; targets +2σ and +3σ**; the operator manages the exit by
  hand (this closes CHECKLIST D6). One definition: `OPERATOR_STOP_PTS`.
- **Draw the setup on BANKNIFTY too.** Told that C4 measures d3 there at 37.5%
  hit / median −75.90 (n=8), the operator said do it anyway. That stands — do
  not re-litigate. What must not happen is the screen implying BANKNIFTY d3
  carries NIFTY's 68.4%.
- ~~**The hover callout is theirs.**~~ **LIFTED 2026-08-08.** The hands-off was
  always conditional — *"i am thinking of modifying it in some way but later"* —
  and the operator has now called that later: *"dusre session m hum apne dynamic
  callout jo h uspe kaam karunga and the other thing like wall khiski trap
  sprung band se palta everyhting"*. It is the next session's subject. Do not
  refuse to touch it on the strength of the old rule.

### Next session starts here

**FIRST, and only if it is a trading day after 09:15 — the collection check.**
It takes ten seconds and it is time-boxed in a way the rest of this is not.
The command and what a failure looks like are in the 2026-08-09 section at the
top of this file. If `rotation_run_sell` is missing, stop and fix that before
anything else: collection is half-blind and every session that passes is a
session of evidence lost. An empty log is fine; a missing key is not.

**Then, the actual subject — the callout and the event vocabulary.**


The operator's own words, 2026-08-08: *"dusre session m hum apne dynamic
callout jo h uspe kaam karunga and the other thing like wall khiski trap sprung
band se palta everyhting i m gonna work on it"*. This is a DESIGN session with
them, not a build-it-and-show-them one — ask before building, three designs
have been rejected before.

**Where it lives.** `trade/Callout.tsx` renders it; `trade/narration.ts` joins
the engine's event stream to bars and tiers it; `trade/hinglish.ts` holds every
gloss (`WALL KHISKI`, `TRAP LAGA`, `BAND SE PALTA`, 25 kinds) plus the
`call | risk | lean` claim table; `LevelsOverlay.drawBalloons` draws the pills.
The kinds themselves are emitted by `engine.py` and `chain_metrics.py`.

**Four things that constrain any redesign — none of them are style.**

1. **A gloss describes the KIND only.** It states no number and never infers a
   direction. Direction comes from `tone`, decided upstream in `data.ts`'s
   `evDir`; the gloss only puts a Hinglish word on a direction already decided.
   An unrecognised kind returns null and the UI shows the engine's own string —
   untranslated, never mistranslated, never silently dropped.
2. **The three claim strengths are load-bearing, not decoration.** `call` (the
   market DID something), `risk` (could happen NEXT, explicitly not yet),
   `lean` (positioning tilts, no prediction). They exist because the direction
   chip once worded all three identically as "ishaara", and on 2026-07-30 the
   `call` kinds ran 15/18 at +30m while `lean` and `risk` ran 11/27. A warning
   dressed as a read is the thing that gets acted on.
3. **STORY is default OFF on measurement, not taste.** `signal_review.py`
   scored the engine's directional events at −0.1 pts (`risk`, n=16) and −6.2
   (`lean`, n=16) at +30m against a +4.1 control — two of three buckets did
   worse than doing nothing, at ~83 events a session drawn at equal weight.
   Any redesign that turns the layer back on by default is re-opening that.
4. **The engine's own sentence is quoted verbatim beside every gloss.** Nothing
   in the callout may strengthen, soften or re-word a claim the engine made.

**Already fixed, so do not "discover" them again:** wall migrations have
hysteresis (`WALL_HOLD = 3`, P2) after 12 headlines in one hour on 2026-08-04;
`GAMMA-PIN`'s gloss is deliberately regime-neutral because the kind fires as
FLOOR, CEILING and PINNED alike.

### ~~The left panel~~ — DONE 2026-08-08

The three questions below were answered: the panel was FILLED (the watchlist
idea dropped — the three indices already render in App's glance bar off the
same payload), scroll-snap was not needed once the chart took a screenful, and
the level labels remain open in `DEFERRED.md §3`. Kept for the reasoning.

### The original note

The Trade tab now has Kite's shape: a 260px panel down the left
(`CHART_SIDE_W` in `TradeTab.tsx`), the chart owning the rest, leg charts off
by default (`LEGS OFF` cycles OFF → SPLIT → STACKED). The chart takes a full
screenful — 76% of the viewport, measured — and anything above it is one
scroll up.

**The panel is empty and says so.** That is where the work resumes. The
operator's words when it was sized: *"left side m watchlist k liye space h."*

Three things to settle there, none of them guessed yet:

1. **Fill it or drop it.** The three indices already render in the glance bar
   at the top of `App.tsx` — same data, so a watchlist here would be a second
   view of it, not a new fetch. If it stays empty, 260px of dead space is worse
   than no panel at all and the chart should take the width back.
2. **Scroll-snap.** The height is right but the landing is approximate; the
   operator asked for *"1 scroll k baad"*. CSS `scroll-snap-type: y proximity`
   would land it exactly. Deliberately NOT added — a snap that feels wrong is
   worse than none, so it wants trying, not assuming.
3. **The level labels still overlap** at the chart's left edge — MAX PAIN, ±1σ,
   S2, S3, TRAP stacked on each other. Open in `ui-audit.md` under Readability,
   and it is the single ugliest thing next to Kite's clean scale.

Layout rules that now apply: **E6b** — the chart owns a screenful, do not
"reclaim" it by subtracting the header again. **E7** — a side rail is safe
where a row below the chart is not, and E4 says verify by measuring the canvas,
not by eye.

### Still open

Phase 5 — the state machine ON the pills. `run_state` is published and unread:
the ARMED countdown, the `ref_high` line to beat, the stop at d3 − 20. Then
`ui-audit.md`'s P1s (contrast, focus indicators). And the OI Flow header still
reads "since the open", which is true once the backfill runs and a lie when it
fails.

**GateGuard hook:** the first Write/Edit per file, and the first Bash call per
session, are denied with a request for facts (importers, affected API, data
schemas, the user's verbatim instruction). State them, retry the identical call.
Not a permission failure.

## 3. What is on screen (Trade tab, top to bottom)

| region | file | notes |
|---|---|---|
| stat strip + toggles | `trade/TradeTab.tsx` | LIGHT/DARK, FOCUS, SMC, STORY, LEGS, index switcher |
| disclosure lines | `TradeTab.tsx` | stale tape, date precision, chain stale, layer unavailable |
| **index chart** | `trade/ContractChart.tsx` + `trade/LevelsOverlay.ts` | candles, VWAP+σ ribbons, MAP levels, rotation pills |
| **OI strip** | `TradeTab.tsx` | latest `/api/oiflow` mark; 15s tab-local poll, no Dhan cost |
| ribbon + legend + "Hidden:" line | `TradeTab.tsx` | the Hidden line reports what the toggles withhold |
| **CE / PE premium panes** | `trade/LegChart.tsx` | own VWAP+σ, own OI pane, own prior-day pivots |
| **ZONE READ** | `trade/ZoneRead.tsx` | WHERE / BOOKS / GEX / FLOW / GAMMA / STRUCTURE / SETUP |
| ENGINE READ | `TradeTab.tsx` (`EngineReadPanel`) | verdict, setup, plays, floor/cap |

**localStorage keys:** `tape.mode`, `tape.focus`, `tape.smc` (default **OFF**),
`tape.story` (default **OFF**), `tape.legstack` (default OFF = side by side).
SMC and STORY default off deliberately — see §6.

## 4. ⚠️ The layout trap — read before touching TradeTab (cost two bad edits on 2026-08-03)

`TradeTab`'s root column **must** keep a definite `height: availH`, because
`ContractChart`'s root is `height:100%` and a percentage cannot resolve against
an auto-height flex container. Switching it to `minHeight` collapses the index
chart to **zero** (measured: `CANVAS 0 → DIV 0 → DIV 0` inside a 420px box).
The leg panes survive that, because they size from a real pixel `minHeight`.

Consequence: the column cannot grow, so **anything added after the chart goes in
the section BELOW the column**, never inside it. Rows inside compete for the
chart's pixels and, once the chart hits its floor, spill out and paint over the
CE pane. Current guards: chart `minHeight: 180`, column `overflow: hidden`.

**If you add a row under the chart, verify the index chart still renders** — not
just that your new row looks right. That is exactly the check that was skipped.

## 5. Backend map

| file | role |
|---|---|
| `server.py` | routes: `/api/data`, `/api/chain`, `/api/oiflow`, `/api/contract` |
| `live.py` | `build_payload`, `_nearest_opt_expiry`, `_floor_pivots`, `_opt_pivots`, `_atm_ids`, `_pivots`, `build_contract` |
| `engine.py` | `Session` / `session_json` — per-bar `ctx`, `gamma`, `setup`, and `fut`/`ce`/`pe` legs |
| `chain_metrics.py` | `ChainState`, `oi_flow` (minute grid; no Dhan call) |
| `structure.py` | SMC layer (FVG/OB/BOS/CHOCH/EQH/EQL/PDH/PDL/PREMIUM/DISCOUNT) |
| `band_rotation.py` | **the operator's own setup** — `detect_index` + two-leg `detect` |
| `contract_bars.py` / `contract_pair.py` | premium bars + σ bands; the 09:20 pair picker |
| `backfill.py` / `squeeze_score.py` | extend `data/backtest/`; score the squeeze hypothesis |
| `signal_review.py` | the scoring harness — **underused, see §7** |
| `trigger_log.py` | **live trigger logger (2026-08-04)** — server.py's refresh thread appends every NEW band-rotation record to `data/trigger_log.jsonl` with the bar's gamma/ctx + chain OI strength at that moment (fail-soft: can never stall the tape). `python trigger_log.py` = table, `score` = fill f15/f30 later. **Needs a server restart to activate.** Scores checklist items #17 (gamma regime) and #18 (ΔCE/ΔPE ratio) after ~20-25 live signals. |

**Ops gotchas:**
- Dhan `toDate` is exclusive for the newest session but INCLUSIVE for older
  ones — always slice with `_one_session`.
- `FUT_ID "61093"` in `dhan_fetch.py` is stale; the resolver gives 58072.
- **Dhan serves nothing before 2026-06-01** — expired contracts drop out of the
  scrip master, and `resolve_dynamic` silently returns the CURRENT contract for
  any historical date rather than failing.
- Contract OI ramps mechanically through rollover week (1.2M → 18M). Never
  compare front-month and far-month captures on OI *level*.
- `data/backtest/`: NIFTY flat (`fut_<ISO>.json`), other indices in
  subdirectories. An index PREFIX would corrupt eight readers that slice the
  date with `basename(p)[4:14]`.
- The Bash tool is Git Bash, not PowerShell: `@'…'@` here-strings mangle commit
  messages. Use `git commit -F - <<'MSG'`.

## 6. Verified vs unverified — the honest table

| claim | status |
|---|---|
| σ bands match the operator's Kite export | ❌ **DOWNGRADED 2026-08-14 — was ✅ (VWAP 0.078 median, ±3σ ratio 0.981); that no longer holds.** Measured against the operator's own Kite CSV the same day: TapeMap σ is **WIDER**, ratio **1.023 → 1.084** through the session, VWAP gap up to **1.70**. Wider σ pushes every band further from price, so the error yields **false negatives only** — two confirmed misses on 2026-08-14 (a 14:00 u3 tag-and-reject the operator saw and the tool did not; an 11:36 d2 entry). **This is upstream of every signal in the repo.** Detail, the unproven seeding lead, and the re-measure recipe: **`research-findings.md` §1c** |
| backfilled Dhan == operator's Kite CSV | ✅ close diff 0.00, OI ratio 1.0000 |
| band pipeline order (`vwap_bands` → `resample`) | ✅ 0.972; reversed order 0.948 |
| option legs on the current weekly expiry | ✅ live 2026-08-03, held through a 24600→24700 strike hop |
| leg pivots vs Kite on the same contracts | ❌ **never cross-checked — do this first** |
| SMC layer | ❌ 4× over-fires vs LuxAlgo; ~⅔ UNKNOWN by construction → default OFF |
| engine event stream | ❌ `risk` −0.1, `lean` −6.2 vs a +4.1 control → default OFF |
| squeeze + falling OI = fade | ❌ **tested and REJECTED** — BANKNIFTY inverts the sign |
| d3 reversal on F&O STOCK futures | ❌ **REJECTED 2026-08-04** — pooled 47% hit, med 0.000% (n=47, 7 names + operator's own ADANIGREEN/RELIANCE TV exports). `stock_score.py`. Why, and the σ-scale arithmetic: **`research-findings.md` §3** |
| overnight gap-fade | ❌ **REJECTED 2026-08-03** — NIFTY fade ≈ 0 and below its own long control; reversion is intraday-only. `gap_score.py`. Detail: **`research-findings.md` §2** |
| classic 15-min ORB | ❌ **REJECTED 2026-08-03** — NIFTY breakouts *fade* (39% hit, −21.1 to close). `orb_score.py`. Detail: **`research-findings.md` §2** |
| **the setup is a ZONE, not a line** | ⚠️ **STATED BY THE OPERATOR 2026-08-14 — read before the row below.** The sky-blue 2σ→3σ shading *is* the setup: **d2→d3 = buy zone, u2→u3 = sell zone**. Reaching **d2 IS the event**; d3 is only the far edge. Every pre-registration in the repo (§5c "d3 only", §5d "u3 only, never u2", §5e/§5f) therefore tests an instrument nobody trades — **unmeasured, not disproven**, same failure as §1. **`research-findings.md` §1b** |
| **`band_rotation` — the operator's edge** | ⚠️ **SCORED, but on the LINE — see the ZONE row above.** NIFTY d3 buy: 72% hit, med +21 @30m vs +0.3 control (n=18). ~~d2 = noise~~ — **that verdict is void**: d2 was measured as a d3 substitute, never as the near edge of the traded zone. Selling = dead and compression filter = harmful carry the same caveat. Management measured too (`trail_score.py`): **hold the stop until VWAP, never breakeven**. Two-leg confirm scored (`confirm_score.py`): does not help buys. **Full rule + numbers: `research-findings.md` §1** |
| ZONE READ confluence | ❌ makes no claim by design; unvalidated as a read |

## 6b. 2026-08-04 — the frame-bug day, and where v3 starts

**One class of bug produced most of what felt broken.** The tape is the MONTHLY
future; the option legs are the NEAREST WEEKLY. The carry between them ran
59→104 points that day — more than a strike step — and it was reaching both the
maths and the pixels. Fixed end to end (commit `67b9e6a`, `19ab6df`, `32e1db0`):
the engine's option forward and strike pick, `ctx.pin.dist`, `ctx.cap/floor`,
and on the UI side the walls, PIN, STK, max pain and gamma flip. The rule now
is one sentence: **anything DRAWN on the chart is futures-frame; any DISTANCE
to a strike is index-frame; `basis` is published in the payload and a level
whose frame is unknown is not drawn at all.**

Also fixed: `trigger_log` was logging forming bars (5 of 12 rows that morning
did not survive their own bar's close); `flip_px` conflated three kinds of
missing; `gex_regime` labelled off `gex_total` while the near-money book said
the opposite.

**A verdict went VOID.** `confirm_score.py` measured the two-leg confirm on
**monthly ATM** legs. The operator does not trade ATM — they take
**premium-matched legs, both above ₹100, within ±₹25 of each other**, going deep
ITM when the near strike gets cheap (see the `operator-trading-style` memory).
On 2026-08-04 the ₹11 ATM CE tagged no band all session — no entry signal and,
worse, no exit — while their real 24500 CE gave both. So "confirm does not help
buys" was measured on the wrong instrument: **void, not disproven.** Re-run it.

**✅ ALL SEVEN FIXED, 2026-08-05.** The table below is kept as the record of
what was wrong and where. Each row now names its fix; each has tests.

| | fix |
|---|---|
| D2 | writer score classifies PER BAR (chain_metrics' rule) and saturates against W_SAT of the CURRENT book, so pegging must be earned. `test_writer_score.py` |
| D3 | the IV gate is one shared `_sane_iv`, used by the GEX computation as well as the display. `test_chain_metrics.py` |
| D5 | `gex_spot` widened to `GEX_SPOT_STEPS = 2` and publishes `gex_spot_band`. Deliberately not wider — it earns its keep by disagreeing with `gex_total` |
| D7 | the floor lives in one place (`GAMMA_T_FLOOR`) and `t_real`/`t_floored` travel beside it. `test_expiry_clock.py` |
| D8 | engine imports chain_metrics' rule and constants instead of restating them; `w_bars_ce`/`w_bars_pe` publish the confidence. **Correction:** there were **two** producers, not three — the third was a display-side read |
| P2 | a wall must hold `WALL_HOLD = 3` readings before it announces. Flicker resets the candidate, so it can never accumulate |
| basis | implausible carry → `basis: null` + `basis_why`, never a fabricated 0.0. Band is asymmetric (−0.15%..+1.0%) because futures trade above the index. `test_option_frame.py` |

**Two things these fixes deliberately did NOT do**, so nobody reads them as
finished:
- The **UI discloses none of it.** `basis_why`, `t_floored`, `w_bars_*` and
  `gex_spot_band` are all published and all unread. The backend tells the
  truth; the screen is still silent. v3's job.
- When `basis` is null the engine still runs at `basis=0.0`, so `ctx.pin.dist`,
  `cap` and `floor` are computed as if carry were zero. Teaching the engine
  "basis unknown" is a larger change and was not folded in.

**Still broken** (the original independent audit, 2026-08-04) — none of these
were cosmetic:

| | what |
|---|---|
| D2 | `engine.py` writer score self-scales off its own running max and reads direction from cumulative premium vs open with a 2% floor — on expiry day theta alone trips it, so `w_ce` pegs at 1.0 and the regime carries no information |
| D3 | raw Dhan IV feeds GEX with no clamp; the sanity gates exist but only on the display path |
| D5 | `gex_spot` sums ±1 strike (2 strikes) — too narrow to be stable |
| D7 | `t_days` floors at 0.25 and freezes through expiry afternoon |
| D8 | three independent writer-score methodologies feed three panels, with no confidence anywhere |
| P2 | wall migrations have no hysteresis — 12 "headlines" in one hour on 2026-08-04 |
| new | no sanity guard on `basis`; the post-close chain print gave −52.9 |

**UI audit** (`/impeccable audit`, scored 7/20): both P0s fixed. Seven left —
zero `@media` queries anywhere, no focus indicators, no `prefers-reduced-motion`,
`transition: width`, four side-tab accent borders, Inter/Roboto (a terminal needs
tabular figures), and ~30 hard-coded colours outside `theme.ts`.

**v3, agreed 2026-08-04.** Not a dashboard — a **state machine**: WAITING →
ARMED → TRIGGERED → IN TRADE → OUT, where the screen is mostly EMPTY because the
setup fires 1-2× a week. It is a **new frontend on this same backend**; if v3
touches the backend it is not v3, it is a third unfinished app. Order agreed:
commit (done) → D2 + basis guard → whale/`confirm_score` measurement → v3.
**Charting foundation — SETTLED 2026-08-05. Keep `candl`.** The throwaway
`/proto` spike ran. lightweight-charts **passed all three** pre-registered
proofs (σ envelope with `drawRibbon` reused at a one-line diff, OI pane from a
bare `paneIndex`, pills anchored with no rAF loop) — and the answer is still
candl, because the rubric missed the axis that decides it: **drawing tools.**
`candl` ships **61** with a full lifecycle API; lightweight-charts ships
**zero**. Full scoring, and the three things worth salvaging from the spike:
**`research-findings.md` §6.**

**The live finding underneath it:** ui-v2 turns **none** of those 61 tools on.
The entire app-side reference to candl's drawings module is
`LevelsOverlay.ts:5` importing the `Converters` *type*. The operator has never
been able to draw on their own chart, and the fix is a toolbar, not an engine —
`setActiveTool` / `setDrawings` / `onDrawingsChange` / `setMagnet` are already
on `IChartEngine`. Verified working 2026-08-05 (`ui-v2/src/proto/ProtoDraw.tsx`,
11 of the 61 exercised, drawings surviving a refresh via localStorage).

**So v3's first chart task is exposing that toolbar, not replacing the engine.**
Mind §4 when it lands in TradeTab — a row under the chart is exactly what
collapsed it twice.

`ui-v2/src/proto/` is a **throwaway**: delete the directory, revert the five
`App.tsx` lines, `corepack pnpm --dir ui-v2 remove lightweight-charts`. Kept
for now only as the evidence behind this verdict.

**Whale/volume-anomaly layer** (operator's TradingView indicator, source read
2026-08-04): buy/sell volume split by close position in the bar's range
(`(close-low)/range × volume`), flagged at 3/4.5/6σ over a 5-bar rolling mean.
Fully reproducible from data we already cache — no tick data needed — and better
on futures than on the index, where volume is synthetic. Two caveats: it is not
real delta (close position ≠ aggression), and a 5-bar σ window makes it fire in
clusters. Score it as a **d3 co-condition**, pre-registered, before it draws.

## 7. Open work, in priority order

**Read `context/research-findings.md` first** — it holds every verdict, the
surviving rule in full, and the stop-rule below.

1. **Collect live triggers.** `trigger_log.py` is wired into `server.py`'s
   refresh loop and needs a **server restart** to activate. It records every
   band-rotation fire with the bar's gamma/ctx and the chain's OI strength —
   the two conditions the operator watches that the cache cannot test.
   `python trigger_log.py score` fills outcomes once the day is cached.
   ~20-25 signals settles both. **This is the only source of new evidence.**
2. **🛑 STOP re-cutting `data/backtest/`.** Seven consecutive negative or
   falsified tests outside NIFTY/SENSEX d3 (2026-08-03/04), and two mid-search
   "findings" that evaporated on the next dataset. More slices will manufacture
   a false positive. Any new hypothesis must be **pre-registered in
   `research-findings.md` before the run**. See §5 there.
3. **The 20-pt stop is a RISK decision owed by the operator** — it sits exactly
   at the typical adverse swing (−20.7). Deliberately not grid-searched.
4. **Capture weekly option legs forward.** Expired weeklies vanish from Dhan's
   scrip master, so this data is unrecoverable later. Needed for the premium
   sell-side test (the only expression never fairly tested) and for the
   two-leg confirm on the expiry the operator actually trades.
5. **Cross-check the leg pivots against Kite** — one session, five minutes.
6. **The `/api/contract` pair chart** — premium-matched pair across strikes
   with the two-leg `confirm`. Still unbuilt.
7. **UI/UX overhaul** (dual review 2026-08-03, consensus 5/10): boot into
   Trade, delete the 7 fossil tabs, ZONE READ → price ladder on the chart's own
   axis, real type/spacing system, keyboard. Detail in `ui-v2-dashboard.md`.
8. **SWEEP/FILL events** in `structure.py`; **SUPPORTS/AGAINST** tagging in
   ZONE READ (rules belong in the engine and must be scored first).

## 8. Decisions still owed by the operator — do not guess

**Still owed:** compression as context vs co-condition (`CONFIRMED`+`CLEAR` = 0
of 64; they describe different phases of a move) · the expiry-day rule · a
seller's stop and decay target · Setup B's expression · whether the ±1σ interior
is no-trade with the edges as the working zones. Three more sit in
`DEFERRED.md §0`.

**SETTLED 2026-08-05, corrected here 2026-08-13** — this list carried both of
these as open for eight days after they were answered, and `PRODUCT.md` copied
the stale version:

- **The 09:25 trigger gate.** `research-findings.md §5c` specifies "after
  **09:25**"; `band_rotation.ANCHOR_MINUTE` (line 228) is that minute and
  `run_states` branch 4 refuses to arm before it — and refuses to assume a bar
  with no readable clock is late enough.
- **Re-fire suppression on the same level.** §5c point 7: after an entry, if
  stopped out the next setup may arm immediately, otherwise not until VWAP is
  touched. `run_states` implements it as `lock`, cleared by stop or VWAP, and
  the bar that clears it may still arm the next setup within the same bar —
  which is why OUT is not one of the state words. `exit_why` is that clearing
  and **nothing else**; see the 2026-08-13 entry for where the UI still reads it
  as a trade exit.

## 9. Working agreement that has held up

- Honesty rules are load-bearing: *"we checked and found nothing"*, *"we could
  not check"*, and *"we are not showing you"* are three different sentences and
  must never collapse into one rendering. Every panel follows this.
- Never invent a level, a greek, or a pivot. An absence gets a reason.
- Score before trusting. The one hypothesis that got that treatment died — which
  is the argument for doing it more, not less.
- Answer the operator's trading questions straight; no "not a licensed advisor"
  deflection.
- Ship a thin visible slice early. Weeks of backend-only work landed with
  nothing on their screen, and the chart they finally saw was unreadable.
