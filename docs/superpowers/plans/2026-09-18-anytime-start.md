# Anytime start — fix every series that can be rebuilt

**Requirement (owner, 2026-09-18):** "every tool every brain every logic anywhere should be able to backfill. i want the view from morning 09:15 am no matter what time i turn on." Her machine dies without warning. A start at 09:15, 13:00 or 15:20 must produce the same screen. What REST can serve is rebuilt; what nothing can serve says so with its reason.

**Source of truth:** the audit at `scratchpad/anytime-start-audit.md` — §2 names each break with its `file:line` and its smallest change, §5 is the acceptance method.

**Binding rules.** Backfill is tagged and never blended with observation. An observation is never overwritten by a reconstruction. A missing value is never a zero and never an empty list without a sentence. No hit rates. No order path. Every nullable field carries a `*_why` of at most 48 characters, non-null exactly when the field is null.

**Baseline:** `python -m pytest -q` reports `3 failed, 1184 passed`. The three are pre-existing in `test_desk_numbers.py` and must never be chased. `context/DEFERRED.md` carries a stated test count that `test_docs_claims.py` asserts — bump it in the same commit as any new test.

**Server:** live on 8765. Never start, stop or POST to it. Read-only GETs are how a route is proved. Python changes reach the owner only when she restarts.

**One task per commit. Each task: the change, then its smallest failing test, then the full suite, then commit.** A task that cannot match its anchor stops and reports; it does not improvise.

---

## Task 1 — B1: republish a restored snapshot so the boards live at any hour

**The break.** `server.py:677-686` gates every chain-derived board on a fresh payload with `ok:true`. The poller never publishes outside 09:15–15:30 (`chain_live.py:522-527`), and today's `_warm_start` rebuilds `ChainState` while publishing nothing (`chain_live.py:411-451`). So on any post-close or weekend start the war map, the drag board, the OI ladder, trapped writers and the paper tick are all dead — while `/api/oiflow` in the same process serves the day correctly from `poller.states[idx].minutes`. `_publish` is also the only writer of `boxes[idx]["spot"]` (`chain_live.py:318`), which `frame.basis` needs (`frame.py:121-125`).

**The change.** After `_warm_start` replays, publish the last replayed snapshot with `mode="restored"` and an `error` string that says so. Because `warmap._try_seed` fires once and needs the daily levels first (`warmap.py:159-161`), the closed-market branch (`chain_live.py:522-527`) must re-publish on its 30 s tick until the boards report `backfill.done`. A restored publish must stay distinguishable from a live one at every consumer: it carries its `mode` and its own `why`, and is never laundered into looking live.

**Test.** `test_chain_live.py`: a warm start with a persisted day file publishes exactly once with `mode == "restored"`, the published snapshot is the last replayed one, and a later live publish replaces it rather than merging.

**Acceptance.** `/api/warmap?idx=NIFTY` returns `ok: true` at a post-close start. `/api/drag` returns a non-empty `indices`, or each index carries its own `why`. `frame.walls.oi_why` no longer reads `no index spot`.

---

## Task 2 — B2: a level that broke this morning still says so after a restart

**The break.** `watch.py:277-279` seeds `broken` only from `prior`, which is the previous frame held in RAM (`server.py:978-979`). The `why` at `watch.py:295-300` covers `rows` only, so an empty `broken` gets no sentence — a level that ran at 10:30 is indistinguishable from a day where nothing ran. Verified live: `broken: []`, `why: null`.

**The change.** The replay already re-fires BREAK and RUN transitions (`warmap.py:216-220`) into `warmap_<day>_backfill.jsonl` and then discards them. Keep them on the board as `seq_fired_backfill`, each row carrying its `src`, and pass them to `watch.build`. If that proves larger than it looks, stop and instead give `broken` its own `broken_why` naming the start time — and say which you did.

**Test.** `test_watch.py`: a broken level supplied from a replayed transition appears in `broken` tagged as restored; with no prior and no replay, `broken` is empty **and** `broken_why` is a sentence.

**Acceptance.** `walls.watch.broken` lists the morning's breaks after a 13:00 start, or carries a sentence. Never `[]` with `why: null`.

---

## Task 3 — B3: the depth vote reads the log it already writes

**The break.** `server.py:973-974` takes sweeps from a 2000-row RAM ring while the same rows sit on disk at `data/senses/senses_<day>.jsonl` (`senses.py:144-146`), which nothing in the repo reads back. On a 13:00 start every morning visit's DEPTH vote is permanently `ok: None`, and the ring covers only about fifteen minutes of a busy tape even mid-session.

**The change.** Seed the ring at startup from today's senses file, filtered to `det == "sweep"`, tagged `src: "restored"` — the `day_state` precedent, since these are observations this tool wrote rather than reconstructions. **The file runs 94–220 MB a day: stream it line by line, keep sweep rows only, and never read it whole.** `_depth_vote` counts a restored row like any other.

**Test.** Beside the seeder: a synthetic three-row file yields only the sweep rows, each tagged `restored`; a large synthetic file is streamed, asserted on the retained list length rather than on file size.

**Acceptance.** After a 13:00 start, a morning visit's DEPTH vote is measured rather than `None`.

---

## Task 4 — B4: a recovered trigger row carries its own minute's OI, or none

**The break.** `trigger_log.py:328-338` reads `oi_flow` once per call and takes the latest mark, then stamps it on every row at `:432-433`. A 13:00 start re-derives the morning's arms correctly from re-fetched bars, then writes 13:00's OI divergence onto a 09:50 row with no tag — quietly corrupting the one irreplaceable artefact in this repo.

**The change.** Look the OI context up at the row's own `t` in the mark series. Where that mark does not exist, write `null` plus an `oi_why`. Never the latest value.

**Test.** `test_trigger_log.py`: a row at 09:50 written at 13:00 carries the 09:50 mark; a row whose minute is absent carries `null` and a why, and never the newest mark.

**Acceptance.** No untagged present-time OI on a recovered row.

---

## Task 5 — B5 and B7: rank history, and a reason that names the cause

**B5** — `chainside.py:163-204` rebuilds the ledgers from `leg_grid` and stops, leaving `_pain_rank` and `_drain_rank` (`:246,264`) empty, so `fuel_rank` is `None` for the first `MIN_HIST=8` snapshots and then ranks the afternoon against an afternoon-only distribution for the rest of the day. Feed the seeded history into the ranks so the distribution spans the session.

**B7** — `breadth.fronts_why` names the symptom; make it name the cause.

**Test.** `test_chainside.py`: after a seed, `fuel_rank` is not `None` on the first snapshot and its distribution includes morning marks.

**Acceptance.** `fuel_rank` is a number at a 13:00 start, ranked against the whole session.

---

## Deferred, deliberately

**B6** — resting paper quotes vanish without a row. The paper book is advisory and she does not trade from it. Fix after the five above, or never.

## Genuinely unreconstructable — must say so, must never be drawn

IV, greeks and GEX before the process started, because REST candles carry no IV. Order-book depth. Kite order counts. The drag *rate*, whose anchor rebuilds but whose rate cannot. Tape events from before the browser tab was open. Paper-desk decisions taken during the absence. Each already has a `why`, and Task 1 must not accidentally fabricate any of them into looking present.

## Verification, end to end (audit §5)

After all five, on a weekday after 15:30: copy `data/chain/chain_*_<day>.jsonl`, `data/warmap/`, `data/vpin_log.jsonl` and `data/day_state/day_<day>.json` aside. Capture the seven endpoints from the all-day process. Filter each chain log to `ts >= 13:00`, move the day state and warmap files aside, restart detached, re-capture and diff.

**Identical:** `/api/oiflow.rows` from 09:15, where the only permitted change is `backfill: true` where the reference read `false` and a larger `backfill_marks`; `/api/data` and the frame's `where`, `bars` and `zone_state`, being re-derived from REST.

**Stated, not identical:** `coverage.late_min`, every `not_reconstructable` entry, `drag.anchor_src == "backfill"`, `warmap.backfill.from`, and VPIN's pre-13:00 rows flipped to `backfill: true, src: "bars_1m_bvc"` with a coarser `imb`.

**The three that fail today:** `warmap.ok` true at any hour; `drag.indices` non-empty or carrying a per-index `why`; `walls.watch.broken` listed or explained.
