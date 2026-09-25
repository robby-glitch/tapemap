# BUILD BRIEF: the hold / fold window (for a fresh session)

Written 2026-09-25 01:45 IST, at the end of the session that designed it. **Start here.**

## What Mary asked for, and signed
> "a floting windows which should be present on any windows or tab i open in our tool … i select the
> extact trade i m in and than the engine is able to track all the things … keeping oder flow in check …
> it would help me either hold my trade or fold my trade. it has to be the greatest piece of the tool"

Signed 2026-09-25 01:42: *"build it we have enough time till tommorrow open and i might not trade at all
tommorrow so build it and than let me know . but this sesiion is very long . so do it new session"*.

## The spec is fixed: build exactly this, nothing more
- **`docs/hold/PREREG-merged.md` rev 4**, sha256 `e7f50391da94a6a14b76ccc6dff5bc993c1b306859baaee8a78e36a7744709d0`
  (anchored in `context/research-findings.md` §1e). Do not change a rule while building. If the text is
  ambiguous or wrong, stop and write it up as a revision question for her. Never fix it silently.
- **Reference implementations** (prototype JS, already replayed against her trades; port them, don't
  reinvent):
  - `docs/hold/fable/hold.js`: the BASE engine (the price line, the verdict map, writers).
  - `docs/hold/opus/verdict.js`: the nearer-front OI ledger, folds as events with `still_folded`, the
    paid-last clock, PATA NAHI while fronts are forming.
  - `docs/hold/opus/scratch/build_facts.py`: per-minute facts built from TapeMap's own `fronts` / `board`
    / `grounds` / `trendbox`. It matched `/api/oihist` 373 of 373 minutes and 47 of 47 folds.
  - `docs/hold/fable/better.js` + `scratch/side_report.js`: the §10 side read.
  - `docs/hold/fable/index.html`: the window's look (the base). Opus's `hold-window.html` has the
    ledger rows and the clock ticks.
- **The review trail** (why each rule is worded as it is): `docs/hold/opus/PREREG-REVIEW*.md`,
  `docs/hold/*/CRITIQUE.md`.

## Build, smallest first (each step tested before the next)
1. **`hold.py` (pure, stdlib):** the verdict order §3, the writer rules §4, the entry check, and the
   side read §10, exactly as registered.
   - Tests on frozen fixtures that reproduce the registration's own stated examples:
     - the M5 entry-check example (NIFTY 09-23 09:46, two families against);
     - the quiet-clock result (six 09-24 SENSEX puts fold at 14:08–14:10);
     - the 09-24 short ATM PE writer folding at entry;
     - the side read (SENSEX 09-24 PUTS on 354 of 375 minutes; NIFTY 09-23 "no side" on ~233).
   - Also a trend-day case and a range-day case.
2. **Per-minute facts per index, cached server-side.**
   - Reuse `board.py` / `server._board_core`, `_board_facts`, `_board_trend`, and
     `live.build_contract` for the held premium.
   - Nothing heavy per request (a 55 MB per-POST parse once wedged this server).
3. **`GET /api/hold?idx=&k=&side=CE|PE&role=long|short&t0=HH:MM&p0=&qty=[&asof=HH:MM]`.** It returns:
   - the verdict, the four reads, the entry check and the side read, with [M]/[I] on every fact;
   - three distinct absence sentences;
   - DRAFT.

   `asof` exists for replay and tests.
4. **The forward logs (§8), written in session only** (`chain_live.in_session`), write-once:
   - `data/hold/hold_<day>.jsonl`: per marked trade, entry to 15:29, with `after_exit` and `fold_rule`;
   - `data/hold/side_<day>.jsonl`: per index per finished minute, with `atm.k` and `stamp_track`;
   - add `data/hold` to `daylog`'s dirs;
   - an end-of-day import of her Zerodha tradebook CSV (format as in
     `C:\Users\kaam\Downloads\tradebook-ZVP031-FO (2).csv`), rows marked `src: import`.
5. **Trade state** (the trades she marks) persisted in `day_state`, so a restart keeps them
   (anytime-start).
6. **UI: a floating component mounted at the `App.tsx` root,** so it shows on EVERY tab.
   - A trade form: index, strike, CE/PE, long/short, entry time, entry price, qty. localStorage
     wrapped in try/catch.
   - Draggable, collapses to one line, which carries the price line and the fact against, **never
     P&L**.
   - A DRAFT stamp.
   - **Chrome Document Picture-in-Picture** as the "pop out" button, so it can sit on top of her broker
     screen.
   - One optional tone, on FOLD only.
   - LIGHT only; **NO charts** (she has them on her broker screen); no order path, ever.
7. **Verify.**
   - pytest: update the stated count in CLAUDE.md, START-HERE.md and context/DEFERRED.md; it is pinned
     by `test_docs_claims.py`. Today: 1458 collected, 1455 passing, 3 pre-existing `test_desk_numbers`
     failures.
   - `npx tsc --noEmit` from inside `ui-v2`.
   - **One detached restart, outside market hours only:** Stop-Process on the PID listening on :8765,
     then `Start-Process start-v2.bat -WindowStyle Minimized`. `data/trigger_log.jsonl`'s line count
     must be equal before and after.
   - Restart equivalence: the window must read the same after a restart.
   - Replay her 13 09-24 trades and the 09-23 re-entries through `/api/hold?asof=`, and match the
     prototypes' stated reads.
   - Screenshots at 1536×695.

## Hard rules
- **Surgical:** the tool is "almost done". Touch no other tab's behaviour.
- **§1d is unchanged.** The window gates nothing (not `setup.gate`, not the zone machine, not
  trigger_log).
- **No restart between 09:15 and 15:30.** If the build is not verified by 08:30, leave it unwired, and
  say so.
- **Commit only on her word.** Never commit `data/trigger_log.jsonl` or its backups.
- **A GateGuard hook** asks for facts before the first Bash command and before each file's first edit:
  state them and retry.

## Open, and registered as unsolved (§9 / §11), so don't "fix" these while building
- The ceiling stepping down a strike vs the trend ending.
- Expiry afternoons when both sides unwind.
- Sub-minute trades.
- The side read lagging at turns (observed 9, 19 and 60 min).
- BANKNIFTY 09-24 as the day-label edge case.
