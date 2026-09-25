# Deferred — decided to do later, not forgotten

Opened 2026-08-07 at the operator's request: *"isko baad m krte h ek file m ye
sb rkhna jo baad m krna h"*.

**What belongs here.** Work that was found, measured, and consciously postponed.
Not a wishlist — every entry carries the measurement that found it, so the next
session can act without re-deriving anything. An entry with no evidence does not
belong in this file.

**What does NOT belong here.** The rules register is `CHECKLIST.md`; strategy
verdicts are `research-findings.md`; the styling backlog is `ui-audit.md`;
finished work is `progress-tracker.md`. This file links to those rather than
restating them.

---

## Reconciled 2026-08-14 — what has since shipped

Checked against `git log`, the source and `data/trigger_log.jsonl`, not memory.

- **Test count is now 1539** (`pytest -q`, 2026-09-25 20:40 - REV 5 OPTION B AND VALIDATE REV 2, BUILT (both signed 19:40 on her delegation: docs/hold/PREREG-rev5.md, docs/hold/VALIDATE-PREREG.md rev 2): the window's line breaks on a 3-min index close past one frozen median 1-min candle, printed as a level (never away on a trail, buffer 0 until 15 candles), a late close is read when its candle lands and never back-dated, a backfilled close is tagged, and both -- with each marked trade's B reads -- are kept in day state; the STOP after a FOLD shows the line that broke; the §C payers precedence and the §D copy; `prereg`, `latch` and the line's close keys on every trade row; VALIDATE's four facts (the zone machine's own state on the closed bar by §1.1's pick, Right now, Room against one candle's noise and the target with leaving walls removed, Paying), GO needs HOLD, the rev 2 press row, and a write-once `check_outcome` row per (idx, t, d) from the per-minute tick; the 33-trade probe re-pinned to rev 5 §E.1's option B column: 10 in `test_hold.py`, 12 in `test_validate.py` (its seven rev 1 tests rewritten to rev 2), 1 in `test_plan.py`, 4 in `test_hold_route.py` (1512+27=1539); before that 1512, 2026-09-25 16:47 - THE HOLD / VALIDATE SERVER FIXES from docs/hold/REVIEW-2026-09-25.md, no rule changed and the word unmoved on the 33-trade probe: the payers' BUILDING-held-3-min fact now outranks a live fold (P0-4), rows carry n_for / n_against / watch_items, a rule-3 latch keeps the line that broke (L, px, by), each VALIDATE fact names its absence kind and a writer is told she cannot get GO, lots at mount, a double-click marks one trade, `reopen` undoes an exit of the last 120 s, the import writes `exit_t_broker` beside her click, a cross-site POST is refused 403, the late-candle REST runs outside the index lock, a minute is re-read when its ladder bars or fill runs move (live now reads as a restart does), and a chain mark with no spot reads blind instead of raising (it had cost SENSEX and BANKNIFTY every hold row of 09-25); `test_hold.py` fails instead of skipping without its fixtures: 2 in `test_hold.py`, 3 in `test_validate.py`, 2 in `test_plan.py`, 8 in `test_hold_route.py` (1497+15=1512); before that 1497, 2026-09-25 12:25 - THE VALIDATE WORD (operator: "i want the validate button there ... it should tell weather the app the thinks i should take it or not"): `validate.py` (pure) turns five registered facts into GO / WAIT / NO by a fixed rule, pre-registered in docs/hold/VALIDATE-PREREG.md (signed 13:20, research-findings 1g; DRAFT), a COUNT never a percentage; `/api/hold/check` carries it and `&log=1` (the VALIDATE button) writes each press write-once to data/hold/check_<day>.jsonl; the Validate tab redesigned around one button and one word: 4 in `test_validate.py`, 1 in `test_hold_route.py` (1492+5=1497); before that 1492, 2026-09-25 12:05 - FOUND LIVE AFTER THE RESTART: Upstox serves a minute's index candle a minute or more late, so the hold read of the newest grid minute had a blind line (PATA NAHI) and the write-once logs would have kept it; `server._hold_facts` now reads a minute only once its candle has landed (at most fronts.STALE_MIN behind, then blind and said so), and `_hold_candles` re-asks for a late candle every 15 s into its own cache: 1 in `test_hold_route.py` (1491+1=1492); before that 1491, 2026-09-25 11:40 - THE VALIDATE TAB REBUILT as the hold window's home (operator: "go and build it nicely"): `GET /api/hold/check` reads a trade not yet taken exactly as the window reads a fill (the registered entry check, the four rows, THE PLAN, the side read) plus her setup from the zone machine's own rows; `?rows=brief` gives the record as runs of the word; the old validator (TAKE / SMALL / AVOID, an unregistered score, the engine headline as a gate, a straddle mis-scaled to one session) deleted: 4 in `test_hold_route.py` (1487+4=1491); before that 1487, 2026-09-25 10:25 - THE PLAN, signed 09:31 (research-findings section 1f): a pure `plan.py` (stop, next rung, room, the touch word, the two exits side by side), the top-2 fronts and the broker's greeks per minute in `server._hold_facts` / `_hold_peaks`, `/api/hold.plan`, the plan on every hold-log row and write-once `rung_touch` rows: 10 in `test_plan.py`, 3 in `test_hold_route.py` (1474+13=1487); before that 1474, 2026-09-25 03:00 - THE HOLD / FOLD WINDOW (operator, signed 01:42: "build it"), exactly as registered in `docs/hold/PREREG-merged.md` rev 4: a pure `hold.py` (the section 3 order, the writer clauses, the entry check, the side read), per-minute facts per index cached in `server._hold_facts` (the running peak read off the day's chain record as it stood at each minute), `GET /api/hold`, `/api/hold/side`, `/api/hold/trades`, `POST /api/hold/trades` (kept in data/day_state/) and `/api/hold/import`, the two write-once logs in data/hold/ (`hold_log.py`, gzipped by daylog), and the floating window at the ui-v2 App root: 9 in `test_hold.py` (the registration's own examples, and all 33 rows of Opus's literal probe), 7 in `test_hold_route.py` (1458+16=1474); before that 1458, 2026-09-25 01:10 - THE MIDNIGHT RE-WRITE: at 00:00:05 BANKNIFTY's refresh still held the 09-24 session and `log_new` stamped its 9 zone rows with the wall-clock date, so they were written again as 09-25 rows (removed on the operator's word, backup kept in data/); a payload whose session label is not today now never logs: 1 in `test_trigger_log.py` (1457+1=1458); before that 1457, 2026-09-24 - BOARD REV 3, WHAT CAN HAPPEN (operator: "ok continue with batch b"): a pure `board.squares` (the next square up and down off the war map's static levels, the fronts' strikes, round strikes and the day's high / low; who pays there, paying now?, pressing?, refused if -- conditions, never odds; the draft level-under-attack read is NOT in it) on `/api/board.squares`, the board cache re-keyed when the war map's daily levels land after the close: 3 in `test_board.py` (1454+3=1457); before that 1454, 2026-09-24 - BOARD REV 3, THE SERVER HALF (operator: "start wiring rev 3 step by step"): `fronts.folds` (§6.1, display on §1d, reusing `_state`), a pure `board.py` (headline, carried/built, the defender described, agreement counted never scored, PCR, the mirror read) and `trendbox.py` (7 rows on the index's own Upstox candles, REGIME, STRONG), composed at a new `GET /api/board` cached per index per finished minute; `/api/oihist` gains `open`, `folds` and FIRST (FIRST persisted in data/day_state/); `live._opt_pivots` builds the prior day from candles before 15:30 only (0j.9.2) and `/api/data` serves nothing stamped 15:30 or later (0j.8 follow-up 3, served-only, `payload_at` untouched): 29 in `test_board.py` on both reference days, 1 each in `test_fronts.py`, `test_index_interval.py` and `test_contract_route.py` (1422+32=1454); before that 1422, 2026-09-24 - THE MIRROR TAB (operator: "along with futures chart i look at the mirror chart of options as well"): each `/api/contract` leg now carries its own contract's prior-session floor pivots (`live.leg_pivots` through `_opt_pivots`/`_floor_pivots`; null plus `pivots_why` when there is no prior session, never zeros) and nothing stamped 15:30 or later (cut at the minute in `live._leg_series`, before the bands and the resample); 6 in `test_contract_route.py` (1416+6=1422); before that 1416, 2026-09-24 - THE GROUNDED CALLS, KEPT (operator: "Log the checked calls"): grounds.py's kill condition had nothing to be judged on because /api/calls kept nothing; `calls_log.py` writes one row per index per engine bar to data/calls/, 09:15-15:30 only, the call as first shown, deduped against the file under one lock; the route and the log share `server._calls_for`: 2 in `test_calls_log.py` (1414+2=1416); before that 1414, 2026-09-24 - THE LOGGER'S STARTUP RACE: at the 2026-09-23 17:43 restart BANKNIFTY's refresh thread deduped against the `_seen` set NIFTY's thread was still reading and re-wrote 7 of its morning rows (removed 2026-09-24 on the operator's word, backup kept in data/); `log_new` now loads `_seen` under `_seen_lock`: 1 in `test_trigger_log.py` (1413+1=1414); before that 1413, 2026-09-23 - WEEK-OLD DAYS COMPRESSED (operator: "my personal laptop with like 120 gb left"): each trading day wrote ~400 MB (senses ~240, frame ~100, chain ~37, book ~25) and nothing was ever pruned. `daylog.py` gzips `data/{senses,frame,book,chain}/*_<day>.jsonl` older than 7 days at every server start (background thread), deleting the original only after the .gz decompresses to the same sha256; today and the last week stay plain because the extension posts the previous session's frames before 09:15. Every past-day reader goes through `daylog.open_text`/`exists` (record_read, book_log.read_rows, server's two book-exists checks, tools/gate_report, replay_dwell); 3 tests in `test_daylog.py`); 1410 (`pytest -q`, 2026-09-23 - NOTHING IS BUILT OR RECORDED AFTER THE CLOSE (operator: "the app should show the last snapshot and not build anything after that"): the book/senses/VPIN recorders run only inside `chain_live.in_session` (09:15-15:30, the chain poller's own clock) -- `watch()` still runs so a post-close restart rebuilds the day -- and `POST /api/frame` drops bars/marks stamped 15:30 or later (`server._session_only`), so the frame after the close IS the last session snapshot and the frame record, ladder file and scorer stop growing; 1 test in `test_book_wiring.py`, 1 in `test_frame_api.py`, 1 source-pin updated); 1408 (`pytest -q`, 2026-09-23 - the anytime-start rule, again: a restart after the close backfilled 15:30-15:39 (Upstox serves option candles past the close, with no index spot) because the cutoff was NOW, so `fronts.read` found spot None on the last mark and the fade gate and the grounding went blind; `chain_backfill.SESSION_END` keeps the backfill inside the session exactly as `_warm_start` already did; 1 test in `test_chain_backfill.py`); 1407 (`pytest -q`, 2026-09-23 - found checking the header on the closing tape: `server._ux_drain` reset the run/impact machines in `finally`, AFTER the restart rebuild fed them, so every fill run before a restart vanished and the flow grounding read that blind window as "quiet"; the reset now runs before the rebuild and again on a raise; 1 test in `test_book_wiring.py`. Same pass, `grounds.py` (self-check, no pytest): both near-ATM fronts unwinding is FLAT for a directional call, not "for" both ways; a run detector that could not rank is BLIND, not "quiet"; a futures-OI quadrant is named only when the move is real for the day); 1406 (`pytest -q`, 2026-09-23 - the re-review's restart blocker: a tap's/trigger's gate uses THAT bar's own engine plays (`book['plays_at']`, the ctx trigger_log stamps from) and freezes only once the grid holds the bar's last minute (`final`), so a restart cannot re-read a vetoed trigger as legal; 1 test in `test_gate_sound.py`); 1405 (`pytest -q`, 2026-09-23 - the independent review's fixes: the tap and trigger gates FROZEN per visit (`book['signal_prior']`), every reader takes a bar's gate at its last minute (`fronts.bar_last_minute`), a gate error never leaves a firm beep, the record signature uses `sound_ungated`, `/api/signals` counts `zone` apart from `legacy` and takes `?day=`; 2 tests in `test_gate_sound.py`); 1403 (`pytest -q`, 2026-09-23 - THE FADE GATE ON THE FACE (§1d "rendered on the face"): `signals.gate_sound` makes the rule decide what rings -- illegal fade silent with its reason, legal trigger firm, PATA NAHI never firm, a one-off `warn` for stand-down / reason-gone, BANKNIFTY capped at soft -- and `sound_ungated` keeps what would have rung; `fronts.fade_gate` now reads an unread NO FADE check as PATA NAHI (not legal) and a grid >3 min stale as PATA NAHI; the forward log still writes every row; 7 tests in `test_gate_sound.py`, 2 in `test_fronts.py`); 1394 (`pytest -q`, 2026-09-23 - caught on the fast line's FIRST restart: `vpin_fast.jsonl` does not exist until the first bucket completes, and the handler read that missing file as "could not be read" -- a never-written file is "nothing yet" (`[]`), not a failure (`null`). Extracted as `server._vpin_fast_rows` so the three absences are testable; 2 tests in `test_vpin.py`); 1392 (`pytest -q`, 2026-09-23 - THE VPIN FAST LINE: `vpin.FAST_BUCKET_V = 20_000` beside the 60_000 slow bucket, measured on the same 30-session cache the original came from (median day 2,963,090 units; the slow line's first rank needs 20.2% of it and lands ~09:58, the fast line's 6.8% and lands ~09:25). Own gauge key `NIFTY-FUT:fast`, own log `data/vpin_fast.jsonl` so the promotion record stays ONE population, served on /api/vpin as `fast_series`; the ui-v2 VPIN tab draws both and says which line its read leaned on; 3 tests in `test_vpin.py`); 1389 (`pytest -q`, 2026-09-23 - THE FADE GATE, pre-registered as research-findings §1d before any code: `fronts.py` reads the near-ATM fronts (nine nearest strikes, top two per side by session-peak OI, each one's build -> stall -> unwind off its own OI-change series) and answers whether a fade is legal; wired into `/api/oihist` (extension-independent), `frame.build` as `fronts` + `setup.gate`, and stamped on every `trigger_log` row as `gate` -- SUPPRESSING NOTHING, so the gate can be judged later from rows logged forward; 11 tests in `test_fronts.py` and 3 in `test_trigger_log.py`); 1375 (`pytest -q`, 2026-09-22 - the sentinel fix: `engine.session_extremes` drops an unset `fut_lo`/`fut_hi` instead of publishing it as a level, after the operator's playbook printed "FADE a test of 1000000000000000000 (session low)" live at 09:27; 5 tests in `test_session_extremes.py`); 1370 (`pytest -q`, 2026-09-21 - final review fix wave 4: the session's closing bar reaches the record -- gate_report always rebuilds a PAST day so the last bin lands, gate_report resolves lot the way the server does (dump/ofd/gcd) and prints its source, a mixed-provenance day says so on /api/tape instead of the gcd sentence, _dedupe_by_t skips a corrupt t instead of raising, and runs.py pluralises "1 lot"/"1 unit"); 1364 (`pytest -q`, 2026-09-21 - final review fix wave 3: no second writer can land the open bin -- gate_report leaves today's last bin alone and read_bars collapses a duplicate t, a failed drain stays sticky on the wire until the day rolls, a lotless run says units not lots, and the collected count is pinned in CLAUDE.md/START-HERE.md); 1361 (`pytest -q`, 2026-09-21 - final review fix wave 2: the restart bin left open for the live stream instead of truncated, the drain resolving one day and naming its own failure, runs/impact reset before a day roll can raise mid-resolution, and lot_why for a lotless day); 1357 (`pytest -q`, 2026-09-21 - the final whole-run review's fix wave: unpriced volume on the wire, a named rebuild failure, the dump/GoCharting/gcd lot fallback, both write-loss counters on /api/health, three minors, and the ux drain as a tested function); 1345 (`pytest -q`, 2026-09-20 - finding 1 fix (tools/gate_report.py Rule 6: distinguish empty book file from missing book file, added test_an_empty_book_file_gets_its_own_sentence); task 13 (tools/gate_report.py: one day's shape-agreement numbers from the two files, rebuilds ux from the book if needed, prints NUMBERS never verdicts; 3 tests in test_gate_report.py pinning every §D field and that missing records name which, with exit 2 for incomplete, 0 for printed); task 12 follow-up (impact.py: `_lam` takes a snapshot `list(self._win)` instead of iterating the live deque, so the request thread's `read()` can never collide with the senses thread's `on_frame` append; ux_log.py: a module `_LOCK` guards `Ladder.step` in `on_frames`/`rebuild` and the `deepcopy` in `forming`, so the request thread's ladder copy can never land mid-mutation — 2 tests added, in `test_impact.py` and `test_ux_log.py`); task 12 (server.py: `/api/tape` gains `ux` — bars, levels, runs, impact and the agreement numbers; the senses loop rebuilds from the book file before it flushes and drains into the ladder); task 10 (runs.py) — three big same-side fills inside three seconds causal percentile over twenty minutes; task 11 (impact.py): task 9 (ux_gate.py): 4 tests in `test_ux_gate.py` pinning that two-record per-bar grids compare POC distance (rows), delta sign agreement (agree/disagree/null with why), volume ratio as feed-integrity check, structural flags (stacks, unfinished), with session-level aggregations: median POC rows, fraction within 1, delta agreement rate, value-area overlap by interval union, node Jaccard (HVN/LVN), and feed confidence fractions (exact/hidden/unknown)—all with `tag: "M"` and null siblings—on the rebinned GoCharting grid (`gate.py` is the seller's gate, imported by `frame.py:36`, and was restored byte-for-byte after Task 9's build wrongly overwrote it — see the Fix report in `.superpowers/sdd/task-9-report.md`); task 8 (ux_log.py): 6 tests in `test_ux_log.py` pinning that `on_frames` writes each closed bar once by `t` and returns it with that pass's fills, `forming` serves the open bin from a closed copy without landing it, `rebuild` streams the book file and writes only the bins the ux file lacks (closing the file-end bin too), a day roll starts a fresh ladder, and a write failure is counted on `failed` and never raised; task 7 (ladder.Ladder): 10 tests in `test_ladder.py` pinning bar-open by ltt not arrival time, lot inference by gcd, tick inference by most-common gap, fills tagged with ltt and side order, lot mismatch counted and kept fractional, partial bars marked for late start and vtt resets, and close_open returning None before any frame; task 6 (ladder.attribute): 12 tests in `test_ladder.py` pinning exact case by per-trade touch, price-priority march, residual hidden, unknown never split, plus the unpriced counter in the no-last-price branch; task 5 (upstox_instruments: lot_size and tick_size ride the cached slice; lot_tick reads the nearest future): 2 tests in `test_upstox_instruments.py` pinning that slice rows keep lot_size/tick_size from the dump and lot_tick returns (lot, tick) or (None, None) on old slices; task 4 (prints.py carries the unknown side): 3 tests in `test_prints.py` pinning that `rebin` sums `u` and defaults it to zero, that `profile` counts `u` as volume at price, and that `imbalances` and `bar_flags` ignore `u`; task 3 (server wiring for the book record): 4 tests in `test_book_wiring.py` pinning that `_SENSES` owns one `book_log.Book`, that `_coverage()["book"]` carries the three-sentence rule, that `_isolate_mock_writers` redirects `book_log.DIR`, and that the senses loop assigns the hook, watches the futures and flushes the deque outside `_SENSES_LOCK`, in that order; task 2 (upstox_feed.on_frame): the hook that fires after the merge, once per key, with (key, feed, currentTs), and catches all exceptions to record them without killing the reader; task 1 (book_log): the record module with 9 tests for row encoding, deque overflow, disk safety, restart-safety, and tear handling; the anytime-start rule
  at the fuel rank: 2 in `test_chainside.py` pinning that the REST morning the
  ledger seed already fetched is ranked too, so `fuel_rank` is a number on the
  first snapshot after a late start and sits inside a distribution that spans
  the session, tagged with its count of reconstructed marks; and that the same
  seed does NOT warm the drain ranks, whose `drain_rate` window is five EVENTS
  and so measures a different span at seed cadence than at socket cadence
  (1198+2=1200); before that 1198, 2026-09-18 - the anytime-start rule
  at the trigger record: 1 in `test_trigger_log.py` pinning that a row written
  after a restart carries the OI mark covering ITS OWN minute, and a null plus
  an `oi_why` where no mark covers it, never the newest mark (1197+1=1198);
  before that 1197, 2026-09-18 - the anytime-start rule
  at the depth vote: 2 in `test_senses.py` pinning that the senses log reads
  back sweep rows only, each tagged `src: "restored"`, and that a day-sized
  file is streamed so the seed costs the rows it keeps and not the rows it
  reads past (1195+2=1197); before that 1195, 2026-09-18 - the anytime-start rule
  at the watch list: 3 in `test_watch.py` pinning that a level broken before
  this process started comes back from the war map replay tagged
  `src: "restored"`, that a live break is never restated as a reconstruction
  of itself, and that nothing broken is `None` with its own sentence rather
  than a silent empty list (1192+3=1195); before that 1192, 2026-09-18 - the anytime-start rule
  at the chain poller: 4 in `test_chain_live.py` pinning that a warm start
  publishes the last replayed snapshot exactly once as `mode="restored"`, that
  a live payload replaces it rather than merging, and that an absent day file
  publishes nothing (1187+4=1191); before that 1187, 2026-09-16 - the five-question frame; 2026-09-15 - the paper day read
  back from the LOG: 21 in `test_day_trades.py` (pairing math, partial fills
  averaged quantity-weighted, restart-survives-via-log, the why join, and no
  rate printed) (1041+21=1062); before that 1041 - the three numbers the
  rebuilt desk screen had to declare missing: 20 in `test_desk_numbers.py`
  (Black-76 theta against finite differences of the existing pricer, RV(5d)
  from the bar cache, margin at shifted spot) (1021+20=1041); before that
  1021 - the short-variance
  paper module: 33 in `test_hedge.py` (band math, the brake, the average-cost
  futures inventory, ledger rows, and nine integration cases through the real
  `trader.on_chain` tick) (988+33=1021); before that 988 - the anytime-start
  audit repairs: 7 in `test_warmap.py` constructing each `confidence()` state
  through real feed sequences, after the arithmetic was found dead
  (981+7=988); before that 981 - the late-start
  follow-ups: per-strike PREMIUM riding the same candles as the OI backfill
  (7 in `test_chain_backfill.py`) and `trapped_inventory.confidence()` on the
  warmap heat rows (2 in `test_warmap.py`) (972+9=981); before that 972 -
  startup backfill and
  the day that survives the evening: 31 across `test_vpin_backfill.py` (13),
  `test_day_state.py` (15) and `test_chain_backfill.py` (+3, the backfill tag
  reaching the trending-OI rows) (941+31=972); before that 941 - the
  cascade-flicker
  debounce guard: 1 - the mock-isolation
  guard after the replay leak: 1 - the paper desk:
  22 tests across `test_book.py` / `test_quoting.py` / `test_trader.py`
  (900+22=922); before that 900 - the OI war map: 27
  tests across `test_levels.py` / `test_dwell.py` / `test_hunt.py` /
  `test_sequence.py` / `test_driver.py` / `test_warmap.py` (873+27=900);
  before that 873 - reviewer fix on commit
  b71f991 (Finding 1): `desk_log.log_transition` gained a `baseline` marker
  for restart pseudo-transitions, plus 2 tests in `test_desk_log.py`
  (871+2=873); before that 871 - Phase 4 (the record a
  desk keeps + instrumentation): new `desk_log.py` (surface forward log,
  desk verdict-transition log, market-hours gate, latency ring buffers) plus
  the two `pools.orders_for` fixes below (845+26=871); before that 845 -
  Phase 0 deleted
  `forcing.py` (superseded by `fuse.py`/`regime.py`, wired live where
  `forcing.py` never was) and its 3 tests in `test_operator_objects.py`
  (842-3=839), and added 6 to `test_senses_api.py` (839+6=845): a
  composed-path test proving PIN/TRANSITION now reachable through
  `server._view_for`, two honesty guards on the new inputs, and three on
  routing (root redirect to `/desk.html`, `/api/health`'s new `feed` dict);
  before that 842, 2026-08-21 - 805 plus thirteen in
  `test_direction.py` and eight added to `test_desk.py` for the flow half of
  the catalog; previously 775 plus eighteen in
  `test_desk.py` for the desk.py risk/margin/sizing rebuild -- legal
  structure shapes, max loss and breakevens, a documented [I] margin floor,
  edge-per-margin scoring, and capital/liquidity-capped sizing; before that
  775, 2026-08-20 - 699 plus eight in `test_pools.py` for wall-vs-cluster and the Kite order-count match; before that 699, 2026-08-20 - 689 plus ten in `test_chainside.py`, which supplies the fuel and drain the order book cannot see, completing the three conditions; before that 689, 2026-08-20 - 663 plus sixteen in `test_fuse.py` (the seam turning detector magnitudes into a regime verdict) and ten in `test_pools.py` (book terrain: shelves and vacuums); before that 663, 2026-08-20 - 639 plus twelve in `test_drag.py` (the honest drag meter, real delta instead of an assumed 0.5) and twelve in `test_regime.py` (the PIN/TRANSITION/CASCADE gate, shadow-only); before that 639, 2026-08-20 - 637 plus two pinning the per-day senses log; before that 637, 2026-08-20 - 609 plus ten in `test_absorption.py`, nine in `test_depth_pull.py` and nine in `test_senses.py`, the book detectors and the wiring that forward-logs them; before that 609, 2026-08-20 - 599 plus ten in `test_sweep.py`, the depth-consumption detector born against the live frame; before that 599, 2026-08-20 - 595 plus four pinning the depth ladder against a live frame captured 09:56 IST (`data/feed_frame_2026-08-20.json`); before that 595, 2026-08-20 — 587 plus eight in `test_upstox_adapter.py` for the depth ladder; before that 587 — 581 plus six in `test_operator_objects.py`, the trapped-inventory ledger and forcing detector wired in beside `chain_metrics.py`; before that 581 — 575 plus the zone-scorer pin in `test_zone_state.py` and five in `test_recover_tape.py`; before that 575, 2026-08-15 evening — 569 plus six
  in `test_zone_state.py` for the §1b zone machine behind the PaperDesk
  chart overlay). Earlier the same day: **569** — the ponytail cleanup
  removed 20 tests along with the code they covered (the dead research
  scorers' `test_continuation.py` / `test_measure.py`, `oi_series`'s two, and
  the four weekend-broken contract tests were rewritten, not removed), after
  589 on 2026-08-14 16:00: one added that
  afternoon pinning the `carry_verdict` empty-book guard in
  `test_option_frame.py`. The earlier reconciliation, still accurate as
  history: **588** — 576, plus nine in
  `test_eod_capture.py` and three in `test_docs_claims.py`. The §1 figure and
  the 2026-08-13 note below are both superseded. **This number is now pinned by
  a test**: `test_stated_test_count_matches_reality` compares every stated
  count against what pytest actually collected, so it cannot go stale quietly.
- **The session tape is now preserved.** `eod_capture.py` + `eod_capture.bat`
  (`2499a12`), scheduled Mon–Fri 15:35 IST. The gap it closes is described in
  §0d below, which is what made it necessary.
- **`exit_why`'s half-landed correction is CLOSED** (`654d17c`): `machine.ts`
  exports `lockNote` and all three screens render the re-fire lock through it.

## 0j · FOUND LIVE 2026-09-24 — her list, worked AFTER THE CLOSE

The operator, mid-session: *"so whatever i m going to find today put in this
file we will work after market"*.
- One item per finding, in the order found, each with the evidence checked at
  the time.
- **Nothing here is changed while the market is open.**
- Each item is marked OPEN → DONE (with the commit) or → NOT A BUG (with why).

### 0j.1 · Board wall labels print the futures price, not the strike — 10:07 · OPEN

**The operator:** *"ok fix the strike labels after market close keep in a
file so to track it later"*. UI-only, no restart.

**What she saw.** NIFTY opened at 23,221.8. The Board tab's tape strip and its
"Walls · breadth" table read `CE 23,310.2`, `PE 23,310.2`, `ROUND 23,310.2`,
`CE 23,210.2`, `OPEN 23,232`. Those look like strikes nobody trades, and like
state left over from yesterday. **It is not stale data.** Checked the same
minute:
- the OI grid re-centred on today's open (22,850–23,650);
- the minutes start 09:15 today;
- the frame is stamped 2026-09-24 10:06;
- today's fronts were written today: CE 23300 +75.6L, CE 23400 +50.4L,
  PE 23200 +27.0L since 09:15.

**Cause.** The board's axis is the FUTURES price, so `frame._walls` shifts
every index-frame row by the basis (`basis(tape, book)`, +10.2 to +11.7 that
morning). Each row keeps `p` = the futures-frame price. CE and PE rows also
carry `strike` (e.g. `{"kind":"CE","p":23311.7,"strike":23300.0}`), but ROUND,
OPEN and the prior-day levels carry no index value at all. `BoardTab.tsx`
prints `p` in both places:
- the tape-strip label `{w.kind} {n0(w.p, 0)}`, next to the `walls.filter(...)`
  line map (~l.436);
- the table cell `n0(w.p, 1)` (~l.484).

**The fix (presentation only; she approved it).**
- **Label by what the trader trades:** `CE 23300` from `strike`. ROUND, OPEN
  and the levels show their INDEX value (`p − basis`, where the basis is the
  same shift the CE/PE rows show: `p − strike`).
- **The futures price stays as small muted text** ("fut 23,311.7"). It is
  where the line is drawn, so it must stay visible.
- **Keep drawing at `p`,** because the axis is futures.
- **Check the same pattern on War / Trade / LevelsOverlay** before closing
  this, so one fix covers every sibling.
- **Verify on the live payload after the close,** then run tsc.

### 0j.2 · Board "WHO IS TRAPPED" headlines a front that never built; the live front is buried — 12:48 · OPEN

**Found from her question** "is our board able to tell us exactly that", about
PE 23200 giving back as spot broke under 23,200.

**Evidence at 12:47–12:48** (`/api/oihist`, `/api/frame`, the Board text, and
raw Upstox 1-min option OI checked independently):
- **PE 23200** built to +46.0L (change since 09:15), peaking at **12:31**.
  It then gave back while spot fell to 23,168: raw Upstox shows 109.2L →
  104.3L by 12:34, and the server read −7.0L off peak with a 15-min slope of
  −6.2L, i.e. UNWINDING by §1d.
- **The Board headline** instead read *"PE 23000 writers unwind kar rahe hain —
  pehle ruke 09:15 pe"*. PE 23000 never built today: it was −13.5L from the
  open, "peak 0.0L @09:15". It wins because it is top-2 by absolute OI and
  `broke` picks the earliest stop, and a front that never built "stops" at
  09:15. PE 23200 appears only in the small detail line. `/api/calls`' OI
  fact also leads with PE 23000.
- **Two smaller things.**
  - The state flickers exactly on the 15% line: 12:47 UNWINDING (−7.0L =
    15.2%), 12:48 STALLED (−6.8L = 14.8%). This is her open method question
    (should UNWINDING have to persist?); she answered "no preference" on
    2026-09-24, so do not smooth the rule.
  - The Board doesn't show the put ladder turning together. Raw Upstox showed
    PE 23150 / 23100 / 23250 giving back in the same minutes.

**Direction for the fix** (presentation, decided as the trader; check it with
her). The headline should be the front whose **build → stall → unwind happened
most recently near spot**, i.e. the one being forced now. It should never be a
front that never built today. "First to stop" stays as a stamp, not the
headline. The board rev 2 mockup's "first stamped once / latest stop" split
already addresses this.

### 0j.3 · The frame log went silent 14:40–15:30, and its scorer now rewrites 136 MB · after-close check · OPEN

**Evidence (18:46):**
- **Rows per 10 min:** normally 135–209, then 13:30 → 4, 14:00–14:19 → 2,
  14:40–15:30 → **0**, and one row at 18:38. BANKNIFTY and SENSEX have no
  frames at all; that is expected, since the extension charts NIFTY only.
- **`tapemap.log` has nothing between 14:36 and 18:38.** The only errors are a
  one-off Upstox read timeout at 14:36, and
  `18:38:56 ERROR score_frame write … PermissionError [WinError 5]` on
  `os.replace(tmp, p)`. That failure left an orphaned
  **`data/frame/frame_2026-09-24.jsonl.tmp` (136.7 MB)**.
- **Why the cause is still unknown.** The POST `/api/frame` handler's
  `except Exception` returns `{"ok": False}` **without logging**, so "the
  extension stopped posting" and "every post failed" cannot be told apart
  afterwards.
- **The rewrite has outgrown its own ceiling.** `score_frame.write` reads and
  rewrites the WHOLE day file on every closed bar: 55 MB wedged the server on
  2026-09-18, and today's file is 136 MB. Its `ponytail:` note says to go
  incremental when the file outgrows a bar's worth of time; it has.

**Direction.**
1. `log.exception` in the POST handler's `except`: one line.
2. The scorer stops rewriting the whole file, e.g. scores go to a small
   sidecar keyed by row.
3. The orphaned `.tmp` goes to the Recycle Bin, on her word.

The other recorders stopped at 15:30 as designed: book, senses, chain and
calls all last wrote at 15:29–15:30. The call log holds 375 rows (125 per
index), with no duplicates.

### 0j.4 · The NIFTY fade gate's defender all day was PE 23000, a wall that never built today · METHOD, hers

**Evidence** (`trigger_log` 2026-09-24, `/api/oihist`, raw Upstox):
- **Every NIFTY gate decision after 09:45 named PE 23000**, e.g. "PE 23000
  adding again, still 13.8L under its 09:15 peak" or "PE 23000 gave up its
  build at 09:15". Spot sat at 23,190–23,260 until 12:30, so PE 23000 was
  about 200 pts below: the edge of the nine, with the largest absolute OI
  (~116L, mostly carried in). Its change since the open was ≤ 0 all day.
- **The strike actually defending was PE 23200.** It was the #2 PE front by
  absolute OI, AT the money, and built +46L today to a peak at **12:31**.
  §1d then read it UNWINDING by 12:47, as spot broke 23,200.
- **Two NIFTY zone rows were stamped LEGAL on PE 23000's wiggle:** the zone
  BUY ARM at 12:54 and ENTRY at 13:00, at d2 23,191.7. That was after PE 23200
  had peaked and started giving back. Spot then fell to 23,046 at 14:24
  (n=1, a description, not a verdict).
- **Where the gate was right, the defender was a real near-ATM front:**
  - SENSEX: illegal from 12:33 on "PE 74000 gave up its build at 11:12"; spot
    then fell ~450.
  - BANKNIFTY: illegal on "PE 56000 gave up its build at 09:31".
  - NIFTY 11:57/12:00: illegal on the engine's NO FADE, 30 min before the
    break.

**Why it happens.** `fronts.fade_gate` takes ONE defender, the largest
session-peak absolute OI among the nine nearest strikes. Absolute OI includes
prior days' inventory, so a legacy wall at the edge of the window outranks
the strike being fought over. Her stated rule says **"the strike with most of
OI and second best"**, i.e. both.

**Options for her (pre-register the choice in §1d first; the old gate stays
logged alongside, nothing suppressed):**
- (a) the defender is the NEARER of the top-2 fronts on that side;
- (b) LEGAL only if BOTH top-2 defending fronts are building;
- (c) rank by today's build instead of absolute OI.

### 0j.5 · The headline shows the engine's verdict, which its own grounding contradicted on 87 of 125 NIFTY bars · presentation

**Evidence** (`data/calls/calls_2026-09-24.jsonl`):

| index | CONTRADICTED | BACKED | THIN | word flips | status flips |
|---|---|---|---|---|---|
| NIFTY | 87 | 26 | 11 | 16 | 22 |
| BANKNIFTY | 94 | 17 | 14 | — | — |
| SENSEX | 56 | 13 | 56 | — | — |

- **Through the 12:30 break** the headline read "WAIT — trend stalled — range
  … compression not continuation", CONTRADICTED, for ~55 min. "GO — MOVE
  RUNNING DOWN" (BACKED) first appeared at **13:27**, about 60 pts after the
  floor went.
  *(Corrected 2026-09-24 evening, found by the rev 3 designer: the verdict
  "GO — one-sided tape" was already BACKED on the 12:33–12:45 bars, then
  flickered back to WAIT. 13:27 is when the "MOVE RUNNING DOWN" episode string
  first appeared. So the engine did say GO within ~3 min of the break; it could
  not hold it. The case for demoting its headline still stands: 16 word flips,
  22 status flips.)*
- **The OI clause "futures OI … too small against today's own 15-min changes
  to read"** printed on nearly every bar: noise text.

**Direction** (as the board rev 2 mockup already does):
- The headline becomes the grounded position sentence; the engine's words
  drop under it, small.
- The futures-OI clause shows only when it reads.

### 0j.6 · No object says "the defended level is breaking"; the pieces were all there by 12:24–12:34 · METHOD, pre-register

**Evidence:**
- **GoCharting**, from 11:40 to 12:24:
  - lower highs, 23,256 → 23,228;
  - the first stacked sell imbalances of the day (11:30, 12:05) and
    `initiative` marks (11:30, 12:10, 12:30);
  - CVD −1,356 → −2,074, with the floor swept at 11:55.
- **Raw Upstox OI:** PE 23200 at its session peak at 12:30–12:31, then −4.9L
  by 12:34 as spot went under the strike, with the put ladder (23150, 23100,
  23250) turning in the same minutes.
- **The tool shows these pieces on different panels** and composed none of
  them into one statement.

**Direction.** A "level under attack" read per defended level: the defender
front's §1d state plus the tape AT that level (absorption vs initiative,
stacked imbalances, CVD against price). States HOLDING / TESTED / BREAKING,
the chess board's "threatened square".
- Display and forward-log only.
- Pre-register the rule and its falsifier before it may gate anything
  (§5 stop rule: no backtest).

### 0j.7 · Her asks after the close: a time-based OI read, the "flush candle", deep-OTM covering, the option mirror chart · OPEN

**The operator, verbatim:** *"we need to mark the 5 candle after which the
most significant drop in oi happened … it happens like after a break … and
deep otm option also start to cover"*; *"along with futures chart i look at the
mirror chart of options as well … same vwap setup +-3 std deviation pivots"*;
*"we need i think some a real time oi analysis because all the action is
there"*.

**Measured on 2026-09-24** (raw Upstox 1-min OI for 78 NIFTY 09-29 contracts,
22,300–24,200, bucketed to 5 min; scratchpad `oi_day.py`):

1. **"Almost no wall": true.**
   - At 09:15, CE 23200 held 16.2L, CE 23250 16.9L and CE 23150 2.4L. The
     23,200–23,300 call walls were built from almost nothing TODAY: CE 23200
     reached 159L, CE 23300 142L.
   - The big carried walls (24000CE 150L, 23000PE 127L, 23500CE 103L) were
     all far from spot.
   - A gap day starts in open space. Absolute-OI ranking favours exactly those
     legacy walls; this links to 0j.4 option (c).
2. **PCR carried no timing information: true.** The PCR over all strikes in
   range drifted smoothly: 0.96 (09:19) → 0.75 (11:44) → 0.71 (12:39) → 0.62
   (14:04) → 0.68 (close). There was no inflection at the 12:30 break or the
   13:29 drop. Near-ATM PCR swung 0.73–1.45 only because its window moves
   with spot.
3. **The put ladder folded one strike at a time, each about an hour apart:**

   | put front | peak | spot at peak | given back after peak |
   |---|---|---|---|
   | PE 23300 | 09:41 | 23,235 | −32.7L |
   | PE 23250 | 11:04 | 23,233 | −25.7L |
   | PE 23200 | 12:30 | 23,189 | −53.5L (built at avg 23,212; closed below its open) |
   | PE 23150 | 13:23 | 23,176 | all of today's build |

   The call writers rolled down with price (23400CE peaked 12:57, 23300CE
   13:57, 23200CE 14:18, 23100CE 15:24), then covered in the afternoon.
4. **The flush candle is 13:25–13:29.**
   - It was the largest 5-min OI drop of the session so far: total −30L,
     ITM + near puts −42L (PE 23200 −13L, PE 23150 −5L), spot −30 in the bar.
   - **Deep OTM puts (≤22,800) covered alongside it:** 358.8L at 13:25 →
     343.3L at 13:50 (−15.5L).
   - The next 30 minutes ran 23,147 → 23,057. The deep puts then rebuilt
     (368.6L at the close) as PE 23000 and PE 23100 were written, and the
     session low was 23,046 at 14:24.
   - n=1: this is a description, not evidence.
5. **The mirror chart is half-built.** `/api/contract` already serves
   option-premium bars (Upstox) with session VWAP ±1/2/3σ (`contract_bars.
   BAND_KEYS`) and OI per bar. It has **no UI consumer** (START-HERE §7; the
   pair-chart mockups are in `ui-v2/comps/`, and she deferred them). Missing:
   - a panel beside the futures chart;
   - ATM CE/PE by default (the pair picker chose CE 23150 / PE 23050);
   - pivots on the premium;
   - bars stopping at 15:30. It served 15:30/15:35 candles, a small leak of
     the after-close rule.

**Direction.**
- **A real-time OI panel:** strike×5-min ΔOI (the WAR rev 2 heatmap) plus a
  deep-OTM strip per side, **flush-candle** marks, and a "folded" stamp as
  each put or call front gives up.
- **The flush-candle rule is new signal logic.** Pre-register it (threshold,
  deep-OTM confirmation, falsifier) before it marks or gates anything, and
  forward-log only.
- **The mirror chart is presentation on data that is already measured;** it
  can be built on her word.

### 0j.8 · Mirror tab: BUILT 2026-09-24 evening, then UNHOOKED on her word; three follow-ups · OPEN

> **Later the same evening:** *"i dont want them as chart on my screen at all
> because i have them on my broker screen"*.
> - The tab is removed from the strip (`App.tsx`), tsc 0.
> - The server parts stay: per-contract pivots on `/api/contract` and the 15:30
>   cut. They feed a **"mirror read" in words** on the board/brief: premium z vs
>   its VWAP bands, the nearest pivots, CONFIRMS/DIVERGES vs futures.
> - `ui-v2/src/mirror/MirrorTab.tsx` is unreferenced until that read replaces
>   it.
> - Follow-up 2 below is moot.

**Built and live since the evening restart.**
- `ui-v2/src/mirror/MirrorTab.tsx`: FUT on top, CE | PE below, each with
  session VWAP ±1/2/3σ, its own contract's prior-day floor pivots, an OI strip,
  one 09:15→15:30 axis and a synced crosshair.
- Strike chips (ATM ±8, OI Flow style): ATM · following by default; CE and PE
  can be pinned independently; FOLLOW ATM returns. Each strike is its own
  series, never stitched.
- 5-min default, 3-min one click away.
- Server: `/api/contract` legs carry `pivots` / `pivots_why` /
  `pivots_day`, and nothing at or after 15:30.
- 6 tests in `test_contract_route.py`. Suite 1422 collected, 1419 passing.
  trigger_log 1934 → 1934 across the restart.

**Follow-ups:**
1. **ATM · following can flip** between two strikes when spot sits at the
   midpoint. Follow the engine's sticky ATM (`days[-1].strike` /
   `live._pick_strike` hysteresis) instead of the chain's nearest strike.
2. **It scrolls ~90 px on her 1536×864 screen,** because the shell takes the
   height. Use the same fix as the board: hide the answer band and MACHINE
   strip on this tab.
3. **`/api/data` still serves 15:30/15:35 FUT bars.** It breaks the after-close
   rule for every other tab; the Mirror hides them and says so. Cut them at
   the source, like `_session_only`.

### 0j.9 · Found by the board rev 3 designer: two data issues · OPEN

1. **The server's opening OI baseline differs from Upstox's finished 09:15
   candle on 9 of 34 NIFTY legs.**
   - On the server's grid PE 23300 "never built" today, while raw Upstox shows
     it peaking at 09:41 (+5L).
   - The same family as the 15:27 restart re-baseline (09-23), which she
     declined to fix for now. The OI clock and "built today" depend on the
     baseline being the real 09:15 OI; take this back to her with this
     evidence.
2. **`live._opt_pivots` builds the prior-day H/L/C from candles that run past
   15:30.** Upstox serves option candles to ~15:39. The option pivots then
   include post-close prints. Cut at 15:30, the same rule as
   `chain_backfill.SESSION_END`.

### 0j.10 · Board rev 3 wiring, batch A (server) DONE in the tree 2026-09-24 22:40; one twin left for her · OPEN

**Done (uncommitted):**
- `fronts.folds / grid / nine`, and a new pure `board.py` and `trendbox.py`.
- `GET /api/board`, cached per index per minute: repeats in ~5 ms, a first read
  per minute 1.8–3.5 s of REST.
- `/api/oihist` gains `open`, `folds` and `first`. FIRST is persisted in
  `day_state`.
- `/api/data` no longer serves bars at or after 15:30 (fixes 0j.8
  follow-up 3); `live._opt_pivots` uses only candles before 15:30 (fixes
  0j.9.2).
- 32 new tests, including a frozen NIFTY 09-23/09-24 fixture pinning both a
  trend day and a range day. Suite 1454 / 1451. trigger_log 1934 → 1934 across
  the restart.

**Left for her: `live._pivots`,** the FUTURES prior-day PDH/PDL/PDC and floor
pivots, very likely has the same post-15:30 leak as `_opt_pivots` did. It
feeds the zone machine's levels, so it is her call, not a silent fix.
Measure the difference on a few days first (it is a data correctness fix,
not an edge search).

### 0j.11 · "It should be able to tell me to hold": her trades vs what the data said · METHOD, pre-register

**The operator, 2026-09-24 evening:** *"we have momentum in consideration here
right and since its a trend day it should be able to tell to hold my trade
because my honest problem is i m not able to hold my trades"*.
- Her orders: 13 round trips in SENSEX weekly PEs (expiry 09-24), mostly held
  10 s–5 min, ₹2,368 realised (broker P&L).

**Evidence, replayed at each exit minute** (scratchpad `trades_review.py`:
`trendbox.rows` on raw Upstox SENSEX 1-min, `data/calls`, `/api/oihist`
folds):
- **The trend rows never wavered.** 5m / 15m / 1h read DOWN at every exit from
  10:23 on, with STRONG = BEARS (09:47: DN / DN / RANGE).
- **The engine headline at her exits said the move was over.** "WAIT — trend
  stalled" (09:47, 10:23) and "SPENT — leg released" (12:33, 12:50, 13:43–46),
  each marked CONTRADICTED or THIN by its own grounding. Links to 0j.5.
- **Put writers kept folding strike by strike:** 74000/74200 at 09:46, 73800
  at 10:23, 73700 at 12:27, 73600 at 13:27 and 13:46.
- **The call side then folded near spot:** CE 74200 at 13:39, CE 74000 at
  14:12. The low was 14:24 (73,564), followed by a ~190 pt bounce.
  - Entries AFTER that (13:54–14:23) held to expiry would have lost, so this
    is not "hold forever".
- **Hindsight scale, not a rule:** the same entries held to expiry come to
  ≈ ₹68k against ₹2.4k taken.

**Direction: a HOLD READ for a position she declares** (side and strike, typed
in; no order path).
- It shows a live checklist, not a verdict:
  1. the trend rows 5m and 15m are with the position;
  2. the losing writers are still folding, with no fresh sized build at spot
     on their side;
  3. the other side is still writing; its first sized fold near spot is the
     warning;
  4. the held premium sits above its own session VWAP (mirror read).
- It says "conditions intact" or names the one that flipped, and when.

**Check that it is not biased to one day:**
- 09-23 (a range day): STRONG read NEITHER on 319 of 375 minutes, so it would
  not say "intact".

**Before building:**
- Pre-register the four conditions, the thresholds and the falsifier, then
  forward-log it with a kill clock.
- Until then, display-only [I]. Never a score or probability.

### 0j.12 · The midnight re-write: 9 BANKNIFTY rows written again as 09-25 · FIXED 2026-09-25 01:10 (uncommitted)

- **Found by the Opus hold-window designer** at 00:00:05 on 2026-09-25.
  BANKNIFTY's refresh still held the 09-24 session ("Sep 24 LIVE").
  `trigger_log.log_new` stamped each row with the wall clock
  (`time.strftime`), so all 9 of 09-24's BANKNIFTY zone rows got new 09-25
  keys and were written again.
- **The risk:** those fake keys would have silently deduped any genuine 09-25
  BANKNIFTY zone row on the same bars (09:36 / 09:39 / 09:42 / 09:45 / 13:42 /
  13:45 / 13:57 arms, 09:48 / 14:00 entries).
- **Fix:** a payload whose session label does not start with today's
  `%b %d` (the label `live.py` builds) never logs. There is 1 test, which
  fails without the fix.
- **The rows, on her word ("Yes, all three"):**
  - backup `data/trigger_log.backup-2026-09-25-before-midnight-dedupe.jsonl`
    (byte-identical);
  - removed only the 9 rows with an identical 09-24 twin, written at
    00:00:05.
- **Restart at 01:10:** 1934 → 1934 lines, 0 rows dated 09-25, 68 rows dated
  09-24.
- Suite 1458 / 1455.

## 0g · DIVERGENCE HAS AN AFTERNOON THETA-BIAS — found 2026-08-25, deliberately not fixed

`engine.py`'s DIVERGENCE ("FUT new extreme, confirming option can't better its
own best") thresholds the option's gap from its OWN session peak at
`2·med60 × (prem/FUT) × 8` ≈ 0.6 premium points on NIFTY. Theta alone drags
an option that far below its morning peak by early afternoon, so late-day new
FUT extremes fire DIVERGENCE (and cast a trap_ev vote) with no real
divergence present. The honest fix needs the expected premium move — delta
(and theta) from `surface.py`, which already computes both — not a price
ratio and a magic 8. Until then: discount afternoon DIVERGENCE votes when
reading TRAP-SETTING. Not fixed same-day because it changes a scored stream's
behaviour mid-forward-log and deserves its own measured change.

## 0h · ~~THE AUG-24 CACHE IS ~44% SHORT~~ — DISPROVED 2026-08-25. The defect was the PATH, and it is fixed. Captures are ~1% short by design.

**The original claim, kept because being wrong in writing is worth more than a
tidy file:** *"TV export of NIFTY AUG FUT 2026-08-24 totals 4,224,415 units;
cached `data/backtest/fut_2026-08-24.json` totals 2,374,190 ... truncated
sessions sit inside any ADV computed from the cache (VPIN's BUCKET_V median ate
at least this one)."*

**The reasoning error:** a disagreement between our cache and a TradingView
export was read as OUR file being truncated, without ever asking the SOURCE.
Two numbers differing tells you they differ; it does not tell you which one is
wrong. The check that settles it costs one REST call.

**Measured 2026-08-25, against Upstox itself:**

| session | Upstox REST | our cache | verdict |
|---|---|---|---|
| 2026-08-24 | 385 bars, **2,374,190** | 385 bars, **2,374,190** | **exact match** |
| 2026-08-25 | 385 bars, 3,786,835 (09:15–15:39) | 379 bars, 3,746,860 (09:15–15:33) | **1.06% short** |

The Aug-24 capture is byte-for-byte what the broker serves. **The 4,224,415 TV
figure is the outlier, not our file** — a different contract, unit convention
or aggregation; it was never reconciled before being used to indict the cache.
Nothing truncated ate the BUCKET_V median, and `vpin.BUCKET_V = 60_000` needs
no recalibration on this account.

**The real defect, found the same night:** the "TapeMap EOD capture" scheduled
task executed
`C:\Users\kaam\Desktop\new tool nifty\eod_capture.bat` — the OTHER repo. Both
repos' `.bat` files are identical and correctly portable (`cd /d "%~dp0"`), so
each ran fine and wrote into its own folder; the live repo simply never
received them. Last run 2026-08-25 15:35, result 0 — a clean success into the
wrong tree. `data/backtest/fut_2026-08-25.json` was missing here and present
there.

**Recovered:** the three orphaned 2026-08-25 captures (NIFTY, `BANKNIFTY/`,
`SENSEX/`) were verified for day, shape and `_meta.source` and copied into this
repo's cache, never clobbering an existing file. A directory diff showed those
three were the ONLY files missing — 08-24 and earlier had been backfilled here
by manual runs (this repo's 08-24 carries `captured_at 19:02` and is the FULLER
385-bar version).

**DONE 2026-08-25 night, on the operator's word ("chala de tu he"):** the
scheduled task was repointed with the schtasks line below and VERIFIED via
`schtasks /Query /V`: Task To Run = the live repo's eod_capture.bat, Status
Ready, Logon Mode "Interactive only" (no run-as password needed — she just
has to be logged in at 15:35), Next Run 26-08-2026 15:35. First capture
into the right repo is tomorrow's.

```
schtasks /Change /TN "TapeMap EOD capture" /TR "C:\Users\kaam\Desktop\operator mode\tapemap\eod_capture.bat"
```

**The residual ~1% is BY DESIGN, not a bug:** the task fires at 15:35 and the
exchange's last bars land 15:34–15:39, so a capture always misses a ~6-bar
tail. `recover_tape.py` pulls the full 385-bar session from Upstox when the
tail matters. Worth knowing before anyone reads a 1% gap as a new truncation.

## 0i · THE DESK ANSWER OSCILLATES — measured 2026-08-25, hysteresis owed, hold-time is the operator's call

Measured live, twice, independently of any UI: `/api/desk`'s answer changed
4 times in 35 seconds (~14:00: SENSEX NEUTRAL→BULL→NEUTRAL→BEAR in 20s,
BANKNIFTY gear TRANSITION→UNKNOWN), and a client counting confirmed flips saw
42 in 60 minutes. The answer is recomputed per chain snapshot with no memory,
so inputs sitting on a boundary flicker the headline. This is the operator's
single loudest complaint about the old desk ("baar baar change hota rehta h").

Sketch, deliberately not built on the night shift: hold the published answer
per index; a NEW answer must persist N consecutive snapshots (or T seconds)
before it replaces the held one; publish BOTH `answer` (held) and `raw`
(this snapshot) so nothing is hidden; every promotion is a dated line the
UIs can log. N/T changes what the desk SAYS, so the operator picks it with
the flip evidence in front of her — both replacement UIs already count and
display the raw churn client-side (tool.html / toolb.html), which covers the
reading until then. Related same-day findings from the clean-room builds:
`best` is a string inconsistent with `candidates[]` and can name a
non-deployable structure; top-level `ok:false` while all indices are valid;
`/api/data` leaks ±1e18 sentinels into narrative text; warmap `seq_log` is
write-stats, not the event log its name implies; paperdesk restart
durability is asymmetric (decisions reset, closed_today survives).

## 0d · ~~THE TAPE EVAPORATES AT MIDNIGHT~~ · **CLOSED 2026-08-20 — the five "permanently unmeasurable" rows ARE measured**

**The claim below is FALSE and is kept as the record of how it was wrong.**
On 2026-08-20 `upstox_auth.py` was re-run and `recover_tape.py` pulled
1-minute futures candles for the four missing sessions — SENSEX 08-10 (370
bars), SENSEX 08-13 (385), NIFTY 08-13 (385), BANKNIFTY 08-10 (385) — from
Upstox historical, on the same August contracts the live captures used. Every
logged price falls inside its recovered session's range, which is the check
that says the contract is right. `score` then filled **20 rows**, including
all five SENSEX 2026-08-13 entries this entry called permanently lost.
§5c's scored population went 8 → **17**.

**What was actually wrong with the reasoning:** "verified against every
surviving source" surveyed the sources the tool already used (its own API
cache, its own chain log) and concluded from their emptiness that the data
did not exist. It existed at the broker the whole time. A session is not
unrecoverable because *our* copies of it are gone.

**Both items below are now closed:** item 1 by `recover_tape.py` (Upstox, not
Kite — Kite MCP's login completed but every API-hitting endpoint failed);
item 2 by the same file, which is what `backfill.py` should have become
before it was deleted. The only unscored rows left are the CURRENT day's,
which `eod_capture` fills at 15:35.

The rest of this entry is the original, preserved:

## 0d (original) · THE TAPE EVAPORATES AT MIDNIGHT — closed forward, five rows lost

**Evidence, 2026-08-13/14.** Signals are logged forward correctly, but the bars
they are scored against arrived only through `backfill.py` → `dhan_fetch`, and
**the Dhan data API lapsed 2026-08-05**. So `data/backtest/` ends 2026-07-31,
every one of the 20 live §5c rows carries `unscored`, and a running session is
scoreable only between the close and the server's midnight roll.

On 2026-08-13 that window passed mid-conversation. **Five SENSEX entries —
09:36, 11:09, 12:09, 12:48, 14:03 — are permanently unmeasurable.** Verified
against every surviving source: the API had rolled (`days: []`), the cache had
nothing, and `data/chain/chain_SENSEX_2026-08-13.jsonl` (2047 rows) holds only
`spot` and per-strike OI — **no futures OHLC and no volume**, so the VWAP-banded
bars the rule runs on cannot be rebuilt from it. Two rows from that session were
scored in time and are recorded in HANDOFF's 2026-08-14 entry.

**Closed forward, not backward.** `eod_capture.py` preserves every session from
2026-08-14 on. It does **not** recover 2026-08-13.

**Still open, and both are cheap:**

1. **Recovering 2026-08-13 (and 2026-08-10).** Kite MCP exposes
   `get_historical_data`, which could supply SENSEX 3-minute futures for those
   days and materialise the missing `fut_<day>.json`. It needs an interactive
   OAuth login that a non-interactive session cannot perform. **Operator action,
   not code.** Note this does NOT cross §5's stop rule: filling outcomes on rows
   logged FORWARD is the route `trigger_log._session_bars`' own docstring names
   as allowed; what is forbidden is searching a new hypothesis out of the cache.
2. **`backfill.py` has no working data source.** It still imports `dhan_fetch`.
   Re-pointing it at Upstox historical (daily OAuth token — see the
   `upstox-data-source` memory) or at Kite would restore bulk backfill. Until
   then it is dead code for any date after 2026-08-05.

## 0f · ~~THE σ BANDS ARE WIDER THAN THE OPERATOR'S~~ · **CAUSE FOUND, NOT FIXED — the operator's decision (2026-08-15)**

**Do not reopen this as a bug.** The cause is proven and the operator chose to
live with it: *"thats not required the difference is small we can manage with
out it."*

**Cause: granularity.** Bands are computed on the 1-minute series and only
SAMPLED into the display bucket (`contract_bars.py:218`, deliberate); Kite
computes SDVWAP on the 3-minute series. Recomputing on 3-minute bars matches
Kite to 0.1–0.3% after 13:45 and reproduces its σ = 0 first bar exactly. The
seeding theory was WRONG, and the variance recurrence is NOT at fault — full
experiment and table in `research-findings.md` §1c.

**Standing consequence, quote it wherever counts appear:** the bands stay wider
than the operator's chart, the error is **false-negative-only**, and therefore
**every TapeMap signal count is a FLOOR, not a total.** A touch that fires on
their screen and not in the tool is expected, not a new bug.

**Two residuals still genuinely unexplained** (small, nobody is waiting on
them): the 3-minute rebuild is 8.6% off at 10:30 though near-exact after 13:45,
and VWAP is 1.83 out even on 3-minute bars — granularity cannot explain that,
suspect volume.

The rest of this entry is kept as the measurement record.

**The measurement** (full detail: `research-findings.md` §1c). Against the
operator's own Kite CSV export of `NIFTY AUG FUT`, 3-min, 2026-08-14:
TapeMap σ / Kite σ ran **1.023 at 10:30 → 1.084 at 13:45 → 1.048 at 14:06**,
with the VWAP itself off by up to **1.70**. Wider σ = every band further from
price = **false negatives only**. Two confirmed misses that day: the **14:00**
u3 tag-and-reject the operator circled on their chart (high 24477.00 cleared
Kite's u3 24476.88 and closed back below; TapeMap's u3 was 24482.10, so the
high fell 5.10 short) and an **11:36** d2 entry missed by 0.25.

**The lead, explicitly NOT the answer yet.** On the 09:15 bar Kite has σ = 0
(all bands = VWAP 24416.67); TapeMap already has σ = 8.75. A seeding
difference is the obvious suspect but does not explain the ratio *rising* to
1.084 and then falling back. **Do not "fix" the seed and declare victory** —
measure the whole curve before and after.

**Everything needed is already on disk**, so this needs no live session:
- `data/backtest/fut_2026-08-14.json` — 379 RAW 1-minute bars, captured 15:35
- the operator's Kite CSV (`VWAP`, `SDVWAP1±`, `SDVWAP2±`, `SDVWAP3±` columns)
- `vwap_bands` in the engine is the code under suspicion

**When it is fixed**, HANDOFF §6's σ-bands row goes back to ✅ *with the new
ratio stated*, and §1b's 2026-08-14 signal counts must be re-derived — they
are currently a floor, not a total.

## 0e · CANDIDATE QUESTION — the target side never printed (observed 2026-08-13)

**Not a finding. One session, two scored rows.** Both showed the OPPOSITE side's
`d1`/`d2`/`d3` **untouched**, best excursions −0.38σ and −0.88σ — price never
crossed VWAP on either. The operator's exit plan trails toward −2σ/−3σ when OI
is heavy that side, so a session where that target never prints is worth
counting.

**Do not act on this yet, and do not go looking for it in `data/backtest/`** —
§5's stop rule forbids exactly that search. The legitimate route is the one
already running: `bands` is recorded on every scored row, so after n rows the
question answers itself from forward data. **If it is to be tested, pre-register
it in `research-findings.md` §5e first**, with the bar stated before the count
is read.

## Reconciled 2026-08-13 — what has since shipped

Checked against `git log` and the source, not against memory.

- **§4, the published stop — actually shipped 2026-08-12, not 2026-08-09.** The
  heading below carried the wrong date for three days. `_stop_px` and the
  per-bar `stop` field first exist in `8760d15` (`git log -S'"stop": _stop_px'`
  returns that commit and no other); on 2026-08-09 the entry was a
  specification, not a shipped field. Date corrected in place below.
- **§0b's "still open" stop item is CLOSED** by the same commit — the 20-point
  stop is published beside `level` on every `run_state` bar and on the entry
  record. The **68.4% vs 63.2%** reconciliation is **still open**, though not
  currently visible: `grep -rn "63.2" ui-v2/src` returns nothing, so no screen
  shows two hit rates for one rule today. The written reconciliation naming
  which exit each assumes is still owed.
- **§0's three operator decisions are all still owed** — nothing in the log
  answers them.
- **Not from this file, but it corrects it:** the tape published 1-minute bars
  until 2026-08-12 while §5c was scored on 3-minute
  (`band_rotation.SCORED_INTERVAL = 3`). Any measurement in this file taken off
  a LIVE payload before that date was taken at the wrong interval. The
  backtest-derived numbers here are unaffected — the scorer always used 3.
- Test count in §1 was 432; it is **576** as of 2026-08-13 (`pytest -q`).

## 0 · THREE DECISIONS OWED BY THE OPERATOR — nothing waits on code

These block real work and must not be guessed. Two of them were guessed once
already today and both guesses were wrong (CHECKLIST C13).

1. **The CALL-heavy threshold** for the short's target extension. No percentage
   given. 40% is the only number in the record and it sits there as a REJECTED
   entry filter (C11) — borrowing it would borrow a number from a question it
   was never asked. Best answered by watching the live CALL-heavy % for a
   session or two rather than picking in the abstract.
2. **Does an ARMED buy close a short, or only a TRIGGERED one?** ARMED exits
   sooner and more often; TRIGGERED is the actual signal.
3. **What "pass" means for the live forward test** (§5e) — per-trade points,
   hit rate, or a ratio against the 20-point stop. §5f's evidence argues for
   **median and hit rate, not mean**: at n≈19 the mean is hostage to one or two
   trades on BOTH sides.

Once 1 and 2 land, the short-exit rules in
`docs/superpowers/specs/2026-08-08-operator-short-exit.md` can be built.

## 0b · Callout v3 — five findings from the 2026-08-09 design review

Found by adversarial review of the callout redesign plan and **verified against
source**. None is a bug today; each is a trap the redesign would have walked
into. Plan: `~/.claude/plans/elegant-frolicking-pebble.md`.

1. **SQUEEZE-RELEASE is filed inconsistently.** It sits in `narration.ts:20`'s
   TIER3 (top billing on the chart) but is absent from `hinglish.ts`'s CLAIM
   table — so `claimOf` returns the `lean` default — and absent from `evDir`
   (`data.ts:517-548`), so its tone is neutral. A pill can therefore shout
   while its direction chip says "direction saaf nahi". Whether it should gain
   a CLAIM entry is a **vocabulary** decision needing its own reasoned commit;
   it is not the card's call. **Operator decision owed.**
2. **`ceW`/`peW` is the live chain ladder** — no per-strike history,
   `aligned=false` while scrubbing. Any per-bar surface must use
   `BarGamma.w_ce`/`w_pe` (`data.ts:137`) instead. The callout plan originally
   named the wrong field, which would have attributed live positioning to a
   past bar.
3. **CONFLICT is unreachable.** `buildNarration` returns `titleCase(best.tag)`
   and never synthesises it; CONFLICT exists only inside `buildFocusFeed`,
   which TradeTab does not consume (it passes the raw stream). Two costed
   options: repoint narration at the focus feed (also changes pills and
   ribbon), or detect it in the UI (violates "UI renders, engine decides").
   Neither taken.
4. **`hinglish.ts` holds 31 glosses, not 25.** HANDOFF's count is stale. The
   eight with no callout state were TRAP, TRAP-SETTING, BREAK, FLIP-TEST,
   OI-PEAK-LAG, CARRY, CHOP, STATE — and the "unknown kind" fallback does not
   catch them, because they *have* glosses. CARRY fires every session at 15:29.
   Also unfiled in CLAIM: BREAK and FLIP-TEST, which default to `lean` though
   BREAK is tier-2 and reads like a call.
5. **Per-kind hit rates must not be rendered.** `signal_review.py` prints them,
   but per-kind n runs 1–5 on one session; "100% · 2/2" reads as a measurement
   at any type size. The `--json` export therefore emits **claim buckets only**
   (n≈16–18) plus the control, and `test_signal_snapshot.py` pins that
   exclusion. Per-kind waits on multi-session live logging — the stop-rule on
   backtest slicing means re-slicing will not supply it.

**Still open from the same plan:** reconcile SetupCheck's **68.4%** against
`trail_score`'s **63.2%** for the same rule, naming which exit each assumes. Two
"measured" hit rates for one rule on one screen is an A1 failure. *(The other
item here — publish the 20-point stop beside `level` in `run_state` — SHIPPED
2026-08-12, `8760d15`; see the reconciliation section at the top.)*

## 1 · Premium / discount is measured on the wrong range · BACKEND

**Status:** operator has seen the numbers and deferred the fix. The three
options below were put to them; none chosen yet.

`structure.py:482` takes the working range from `prev_sh` / `prev_sl` — the
previous confirmed swing high/low pair. Those are 1-minute fractal pivots, so
two consecutive swings sit 8–16 points apart on NIFTY.

Measured live, 2026-08-07 (NIFTY, 385 bars):

| | |
|---|---|
| session range | 24601 → 24707 (106 pts), equilibrium **24654** |
| published PREMIUM | 24655 → 24663 |
| published DISCOUNT | 24647 → 24655 |
| so the range used | **16 points** |
| PD pairs per session | **56** |

So it publishes the premium/discount of the last 1-minute micro-swing, not of
the leg being traded. ICT's premium/discount is a **dealing range** read.

**This is not a crash and must not be smuggled in as a "bug fix".**
`structure.py`'s own comment records the box counts (44/43/57 per day) as
measured, so the current behaviour is deliberate. Changing it is a change of
DEFINITION, which is the operator's call, and a backend change, which CHECKLIST
F2 says must be separate and explicitly agreed.

Options as put to the operator:
1. **Swing pair with a minimum size** (e.g. range ≥ 1σ, ~22 pts today) — the
   ICT dealing range. Recommended. Collapses 56 pairs to a handful.
2. **Session high → low** — one stable pair all day; goes wide by the close and
   on a trending day the "discount" half marks where price was this morning.
3. **Leave it** — then the 16-point band keeps claiming to be a premium/discount
   zone, which is the thing that looked wrong.

Needs: the change, tests (**576** as of 2026-08-13; the 432 here was stale), and
a note in `CHECKLIST.md`.

## 2 · Structure lines carry no text · FRONTEND

**Status:** operator deferred — *"isko rehnde filhall"*.

`LevelsOverlay.drawStructures` labels only `confirm === 'CONFIRMED'`.

**Measured on the live 2026-08-07 payload: that yields ZERO.** Not "few" —
nothing in the session is CONFIRMED, so the rule deletes 100% of the labels.
Of ~93 marks actually drawn (12 OB boxes, 58 swing ticks, 18 EQH/EQL pools,
3 PD lines, 2 range bands) only the 3 prior-day lines carry text, because those
have their own always-label branch.

The rule was written to thin 479 labels off ~180 structures. That pressure is
gone: FVG (~85 boxes) and BOS/CHOCH were dropped on 2026-08-07, so a label
budget now exists.

Direction proposed, not yet chosen: label by KIND, not by `confirm` — OB /
EQH / EQL / PD always named (~35 labels), swings left unlabelled (58 is the
noise problem), and let confirmation keep doing what it already does through
opacity and the dashed border.

## 2b · ~~The SETUP CHECK panel is BUY-only~~ · **DONE 2026-08-08**

The panel now reads both machines and NAMES the side it is showing (a
`BUY · d3` / `SELL · u3` badge beside the state word). A side that is not
WAITING wins; with both live the BUY side shows and a caution line says the
sell side is armed too, because picking silently would hide half the machine
and preferring the scored side is the only defensible tie-break.

The 68.4% / n=19 note is swapped out on a sell for the sentence saying that
side has no score. A number belonging to one rule must not ride along beside
another.

## 3 · Left-edge level labels · FRONTEND

**Status:** open in `ui-audit.md` under Readability as **FAILING**; the operator
circled it on 2026-08-07 and then redirected to the line weights instead.

Three faults in one place:
- the price is drawn **twice** — in the left label and again in the right-axis
  chip;
- on collision the left label is **dropped**, so a level can end up with no name
  anywhere;
- 8.5–11px against the σ ribbon fills is under-contrast.

Direction proposed, not yet chosen: name on the left in a filled chip, price on
the right axis only, and de-collide by **nudging** rather than dropping.

**2026-08-13 — taken for TWO lines only, uncommitted.** `LevelsOverlay` now
draws `d3 · ARMS THE BUY` and `u3 · ARMS THE SELL` as left-edge **filled** chips
against solid 2.5px brass lines, deliberately unlike the 1px dashes every other
level uses. That is this entry's proposed treatment, applied to the two bands
§5c actually reads and to nothing else — the reason is the d2/d3 reading trap
(HANDOFF, 2026-08-13), not this entry. The three faults above still hold for
every other level.

## 4 · ~~The stop is not published~~ · **DONE 2026-08-12** (`8760d15`)

*Dated 2026-08-09 until 2026-08-13; that was the day it was specified. The field
did not exist until `8760d15`.*

Done exactly as specified: one field. `band_rotation._stop_px(level, stop_pts,
sell)` is now the single expression, called by BOTH the re-fire lock and the
published field — the file's own warning above `OPERATOR_STOP_PTS` says two
copies of a risk parameter drift silently, and a stop the chart draws differing
from the stop the lock enforces is that failure. It is emitted on every
`run_state` bar beside `level`, and on the entry record.

`RunState.stop` is **optional** in TypeScript on purpose: a server on older code
omits it, and the panel then shows NO stop line rather than computing `level`
minus 20. Absence is the correct rendering of "the server did not say".

SETUP CHECK now pairs it with the line to beat (`Todna hai > X` / `Stop < Y`),
muted rather than red — theme.ts reserves red for direction, and a stop is not
a bearish call.

Tests: `test_band_rotation_run.py` §7, six of them, including the BUY/SELL
mirror (a short's stop sits ABOVE the band) and the assertion that a moving
reference does NOT move the stop.

~~**Not yet seen on screen.** 2026-08-09 is a Sunday and the session carries no
bars, so no setup can arm and the line cannot render.~~ **2026-08-13:** the
field ships and two SENSEX setups armed on 2026-08-13 (`trigger_log.jsonl`,
09:33 and 11:06), so a `level` and its stop have existed live. Whether the
operator has *looked* at the rendered line is not recorded here and is not
claimed.

## 5 · MERA READ ships empty · needs the OPERATOR, not code

The panel's third group is the operator's own rules and starts empty. Asked
twice on 2026-08-07 what those rules are; not answered. Seeding it with three
invented lines is exactly what CHECKLIST A2 forbids, so it stays empty until
they say what goes in it.

## 6 · Hinglish stops at the Trade tab's chrome

Done: the SETUP CHECK panel, the stat strip, the toggles and their tooltips,
the disclosure lines, the legend, the `Chhupa hua:` line, EngineReadPanel's
labels, ZoneRead's `Kahan` group.

Still English: **ZoneRead's body sentences** ("no EQH pool above", "formed;
sweep not tracked"), the **leg panes** (`LegChart`), and **`App.tsx`'s CHAIN
STALE banner** plus the glance bar and ANSWER band.

Deliberately never translated, and this must survive any future pass: every
string the BACKEND authored and the UI quotes verbatim — `ctx.vwhy`, `ctx.line`,
`ctx.breadth`, `ctx.plays`, the setup fields, `trap_why`, `confirm_why`,
`structuresWhy`, `rotationRunWhy`, `flowWhy`. Translating a quote breaks
EngineReadPanel's stated promise that it shows the engine's own read.

## 7 · The session key reads oddly

`day` arrives as the literal string **`"Aug 07 LIVE"`** — no year, and with
`LIVE` inside the key. The UI renders it verbatim (A2), and `dayPrecision`
already discloses the missing year. Owed decision: fix the key at source, or
have the panel show only the date part.

## 8 · The styling backlog is elsewhere

`ui-audit.md` holds the P1/P2 items — contrast, focus indicators, ARIA,
`prefers-reduced-motion`, `transition: width`, the side-tab borders, 22
hard-coded hex values, `tabular-nums`. The operator's standing decision on
2026-08-06 is *"changes live market mein karenge"*. The SETUP CHECK panel meets
all of them from the start; the rest of the app does not.
