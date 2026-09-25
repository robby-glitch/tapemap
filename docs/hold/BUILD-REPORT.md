# BUILD REPORT: the hold / fold window (2026-09-25, built 01:50–02:40 IST)

Built from `BUILD-BRIEF.md`, exactly to `PREREG-merged.md` rev 4 (sha256 checked
`e7f50391…709d0` before starting). **Nothing is committed**; that waits for her word.

## What exists
- `hold.py`: pure. The §3 order, the §4 writer clauses, the entry check, and the §10 side read.
- `hold_log.py`: the two §8 forward logs, write-once:
  - `data/hold/hold_<day>.jsonl`;
  - `data/hold/side_<day>.jsonl`, which carries `stamp_track` rows;
  - `data/hold` is now in `daylog.DIRS`.
- `server.py`, all additive; no existing route or rule changed:
  - **Per-minute facts per index, cached** (`_hold_facts`).
    - The running session peak as of each minute comes from the day's chain record (`_hold_peaks`), read once and then only its new lines.
  - **Routes:**
    - `GET /api/hold` (`?id=` or `?idx=&k=&side=&role=&t0=&p0=&qty=[&asof=][&rows=1]`);
    - `GET /api/hold/side?idx=`;
    - `GET /api/hold/trades`;
    - `POST /api/hold/trades` `{op: mark|exit|unmark}`, kept in `data/day_state/`;
    - `POST /api/hold/import`, which takes the tradebook CSV, or an empty body to only complete the day.
  - **A `hold` thread** writes the logs once a minute for session minutes only.
- `ui-v2/src/hold/HoldWindow.tsx`, mounted at the `App.tsx` root, so it shows on every tab.
  - Draggable, and collapses to one line with no P&L.
  - DRAFT stamp; Document Picture-in-Picture pop-out; an optional tone on FOLD only.
  - LIGHT only, no chart, no order path.

## Verified
- **pytest:** 1474 collected, 1471 passed. The 3 failures are the known `test_desk_numbers` ones.
  - `test_hold.py`, 9 tests:
    - all 33 rows of Opus's literal probe (`xreview/probe_rev3.txt`);
    - the M5 entry-check example;
    - the six 09-24 puts folding at 14:08–14:10 at +204.9 … −11.3;
    - the short ATM PE writer folding at entry;
    - the side read (SENSEX 09-24 PUTS 354 of 375; NIFTY 09-23 no side 233);
    - a trend-day case and a range-day case;
    - causality, and the latch surviving a blind minute.
  - `test_hold_route.py`, 7 tests:
    - a repeat read is served from the cache;
    - a restart reads identically (`day_state` save and reload);
    - an `asof` read is the first part of the close read;
    - the logs are write-once from entry to 15:29;
    - the import (a short trade, a match against a marked trade, the exit flag);
    - bad input is refused at the door;
    - the peak reader is exact to the minute and incremental.
- **`npx tsc --noEmit`:** clean.
- **End to end on the raw day records.** A fake poller was built from `data/chain`, with REST candles for 09-23 and the Upstox candles frozen for 09-24.
  - The server's per-minute facts equal the frozen probe facts on every minute of SENSEX 09-24, NIFTY 09-23 and SENSEX 09-23. The only difference: the first minute or two, before the first chain mark, where the server also reads the trend and the candle.
  - Her trades through `/api/hold`: **21 of 21** match the probe on the entry word, the first-FOLD minute and the rule (13 on 09-24, 8 on 09-23).
- **Two restarts outside market hours** (02:26 and 02:38). `data/trigger_log.jsonl` was 1934 lines before and after each.
- **Screens at 1536×695.**
  - Replay: her 12:32 74100PE reads WATCH at 13:05, then FOLD since 13:14 (the reason is gone) with the header red. The collapsed line carries no P&L.
  - The mark form works (after a fix: the price field refused 190.03).
  - The live app shows the window on Board, War, Trade, Signals and Heat, and says "could not check — no finished minute of today's session" before the open.

## Not verified
- **Chrome Document PiP.** The API is called on the click, and it correctly refuses a call made without one. The app's built-in browser leaves the request pending, so it has to be checked once in her Chrome (116+).
- **σ against the premium's VWAP** ([M], REST 1-min candles through `live.build_contract`). It could not be run at night because REST no longer serves 09-24 option candles. It is fail-soft: it says "could not check — why".
- **The live `hold` thread writing during a session.** No session has run since the build. Its tick is the tested `_hold_tick`.

## The server stopped after 02:50, and the cause was the launch
The server started at 02:38 (PID 12324) vanished with no log line. That was roughly when this agent session was paused by its usage limit.
- It was started with `Start-Process start-v2.bat` from the agent's shell, as the brief said. It still died with the session, which is CLAUDE.md's 2026-08-25 failure mode.
- Her Vite on 5173, started by her own launcher, survived.
- **Lesson: an agent never starts the live server.** Anything that must outlive the session is started by her, with `.\stop.bat; .\start-v2.bat`.

## Revision questions for her: interpretations, not changes
Each one follows the reference probe, so the registered examples are unaffected.
1. **§3 rule 7, "WATCH — exactly one of".**
   - The problem: two of those facts that make no FOLD rule (for example, holders leaving plus flow against) would be neither WATCH nor HOLD.
   - Built as: WATCH on one or more when no FOLD rule matched, as the probe does.
2. **§4, "spot has moved toward her strike".**
   - Built as: the danger direction (grounds' `dpx` against the thesis). This is identical for OTM and ATM writes.
   - For an ITM write, "toward the strike" read literally is the safe direction. Which does she mean?
3. **§4, the own-side squeeze clause.**
   - The front must be UNWINDING for 3 minutes; the squeeze is read at the current minute, as the probe does.
   - A holders' fold on her own side follows the same clause, as §4 says. The probe did not apply the clause to folds, but that changes only WATCH vs HOLD, never a FOLD minute.
4. **§8, `stamp_track`.**
   - Write-once cannot append to the stamp row, so the track is its own row, `{kind: "stamp_track", t: <stamp minute>, stamp_track: {k, from, to, short, ce: […], pe: […]}}`.
   - It is written once that strike's 30 minutes (or the minutes to 15:29) have finished.
5. **§8, "in session only".**
   - The 15:29 minute finishes at 15:30:00, so the writer reads the clock 90 s back.
   - The close-time import completes anything a dead minute missed.
6. **§10.3, expiry.**
   - Built from the chain poller's resolved expiry. The frame head's `expiry` is that same value, handed on.
   - The tradebook's `expiry_date` is stored on imported trades.
7. **The premium is [I].**
   - It is the chain poller's last trade of each minute, and the premium's "last candle" is minute close against the previous close.
   - It feeds only the noise tag, the P&L and the footer, never the verdict (§1).

## Already on the page, not new
- A pivot confirming at minute c is taken at the first candle minute after c (`verdict.js` took c + 1 exactly and skipped it across a candle gap).
- Holders "hold" needs a build today (peak change > 0), as `board.oi_read` and `verdict.js` require.
- A payers' fold must be still folded, per S3 (`verdict.js` did not check this; the probe did).
- A both-leaving minute is readable and OI-unpaid. The strict flow can still pay in it (probe).
- The clock counts readable minutes from the entry minute inclusive.

## THE PLAN built (2026-09-25 10:15–10:25 IST, during the session, on her word)

Her words: "plz make the hold or flod thing right now because its friday i might not more trade any
more". Built from `PLAN-BUILD.md` Tasks 1–4. The spec is `PLAN-PREREG.md` rev 2a (signed 09:31,
§1f); its hash was checked before building. `hold.py` is untouched.

**Files:**
- `plan.py` (pure) and `test_plan.py` (10 tests).
- `server.py`:
  - `rec["fr"]`, the top 2 per side per minute;
  - `_hold_peaks` also keeps the broker's greeks, and `_hold_greeks` reads them;
  - `/api/hold` gains a `plan` key;
  - log rows gain `plan`, and touches get their own `rung_touch` rows.
- `hold_log.key` now includes `kind` for hold rows.
- `test_hold_route.py`: 3 new tests.
- `HoldWindow.tsx`: the STOP / RUNG / ROOM block, the rung on the collapsed line, and the plan's
  "not shown" lines.

**Verified:**
- **Tests:** the hold suites (29) pass, `tsc` is clean, and every line of `server.py` is still CRLF.
- **Her 09:36 NIFTY 23200 PE,** read through the new server code in a separate process on
  today's own chain record:
  - 09:35: RUNG PE 23,100 · 4 pts · DEFENDED against STOP 18 pts (the room warning);
  - 09:39 (her exit): RUNG PE 23,000 · 78 pts · DEFENDED, against STOP 44 pts;
  - 09:43: GIVING WAY;
  - 09:54: DEFENDED again, the minute BUY d2 triggered.

**Not live until SHE restarts the server.** The running process has the old code, and the UI
block stays hidden until `/api/hold` serves `plan`. The agent does not start the live server.

**Band rung:**
- `PLAN-ADDENDUM-rev3.md` rev 3a (sha256 `ea068017…bf26`).
- Reviewed NOT YET by Sonnet, fixed (M1 the fourth outcome; S1–S3).
- Awaiting her signature, and not built.

## THE VALIDATE TAB rebuilt as the hold window's home (2026-09-25 10:45–11:45 IST, on her word)

Her words: "go and build it nicely … think yourself the trader you are building this for your son".

**The old tab was deleted, not hidden.** It had:
- verdicts that were instructions and a size (TAKE / SMALL / AVOID, "size accordingly");
- an unregistered 0–100 score;
- the engine's BULL/BEAR headline used as a pass/fail gate;
- thresholds nobody signed;
- a "move priced for the rest of the session" that used the ATM straddle (priced to expiry)
  as if it were one session.

**BEFORE — `GET /api/hold/check?idx=&k=&side=&role=[&qty=][&p0=]`.** It reads a trade not yet
taken exactly as the window reads a fill at the latest finished minute:
- the registered entry check, worded "If you enter now, you enter into …";
- the four rows, THE PLAN and the side read;
- her setup: the zone machine's latest trigger and arm from `data/trigger_log.jsonl` (read-only,
  cached by the file's size and mtime, the `zone` population only), each with its own §1d gate and
  whether it agrees with the trade;
- the broker's Δ and Γ [M].

**Nothing is marked or logged by a check.** "What lines up" counts five registered facts as with
you / against / neither: a count, never odds, and never a confidence number.

**IN.** "I'm in" marks the trade, and the floating window follows (a `hold:select` event).
- The tab shows the same reading at full size, plus the record since entry as runs of the WORD
  (`?rows=brief`).
- One shared `ReadingView` renders both the tab and the floating window.
- On the Validate tab, the floating window and the engine's ANSWER band step aside; the MACHINE
  strip stays.

**Verified:**
- pytest 1491 collected, 1488 passing (the 3 known desk failures); `tsc` is clean; `server.py` is
  still all CRLF.
- Her 09:36 NIFTY 23200 PE, replayed on today's record with the new code, in a separate process on
  port 8766:
  - "SELL u2 triggered 09:33, gate legal, agrees";
  - "If you enter now, you enter into WATCH";
  - rung PE 23,100 4 pts DEFENDED, against a stop of 18 pts: 1 with you, 2 against, 2 neither;
  - marked, followed by the floating window, and at 10:00 HOLD since 09:56, with the record shown
    as runs.

**Live only after her restart.** Until then the new tab's check shows "could not check" (the
running server has no `/api/hold/check`), never wrong numbers.

## Found live after her 11:56 restart, fixed (12:05)

**The defect.** Upstox serves a minute's index 1-min candle a minute or more late. At 11:58:16 the
candles reached 11:56 while the chain grid held 11:57.
- The hold read of the newest grid minute had no candle, so the line was blind and the word read
  PATA NAHI.
- The write-once logs would have kept that blindness.
- Replays never showed it, because their candles were complete.

**The fix, in `_hold_facts`, the one place every reader goes through** (the check, the window, the
logs and the side read):
- A minute is read only once its index candle has landed, at most `fronts.STALE_MIN` (3) minutes
  behind the grid. Past that, the candle feed is stale: the minute reads blind, and says so.
- `_hold_candles` re-asks Upstox for a late candle every 15 s, into its own cache; the board's cache
  is not touched.

**Verified live, offline** (the new code on today's record and live REST):
- 12:02:01: read 12:00, WATCH, the line readable;
- 12:02:21: read 12:01, caught up about 20 s after the minute ended.

pytest 1492 collected, 1489 passing. **Live after her next restart.**

## The Validate tab redesigned, and the GO / WAIT / NO word (12:10–12:30 IST)

Her words: "the ui is shit hardly able to understand anything there … i want the validate button …
it should tell weather the app the thinks i should take it or not or confidence score maybe".

**The rule, written first.**
- `docs/hold/VALIDATE-PREREG.md`, SIGNED 13:20 (research-findings §1g); the word shows DRAFT until her forward checks judge it.
- Five registered facts, each with you / against / neither: your setup, right now, market side, room
  to run, and the next wall.
- **NO:** a broken setup, or 3 or more against. **GO:** nothing against, and 4 or more with you.
  **WAIT:** otherwise, and it says what would have to change.
- A COUNT ("4 of 5 line up"), never a percentage: a % would be a number with no forward record
  (rule 4).

**The code.**
- `validate.py` (pure) and `test_validate.py` (4 tests).
- `/api/hold/check` carries `validate`, and `&log=1` writes the press write-once to
  `data/hold/check_<day>.jsonl`, keyed (index, minute, strike, side, role). `hold_log.key` gains a
  `check` branch.

**The UI** (`HoldTab.tsx`, rewritten):
1. index chips, strike, CE/PE, BUY/SELL, qty, then one big VALIDATE; no auto-refresh;
2. the word big, the count, one sentence, the five facts with ✓ ✕ ·, and for a WAIT what would
   have to change;
3. the stop, next wall, premium and delta, then "I'M IN — WATCH IT FOR ME";
4. everything else under "more detail".

The IN half follows the same shape: a big word, one sentence, the numbers, then what the window
said since entry.

**Verified on the replay of today's record at 09:44:** her 23200 PE reads WAIT, 4 of 5, room
against (next wall 49 pts away, stop 73). pytest 1497 collected, 1494 passing. **Live after her
next restart.**

## 2026-09-25 14:20 — the designer's layout ported onto the live tab and window (her word: "just do it")

- Source: `docs/mockups/validate-2026-09-25/validate-design.html` + `DESIGN-NOTES.md` (a clean-room Opus design agent, her designer prompt, real server replies only).
- `ui-v2/src/hold/hold.css` (new; every rule scoped under `.hv`, so no other tab changes),
  `ui-v2/src/hold/parts.tsx` (new; the shared marks, the three absences, [M]/[I] tags, stop/wall blocks, rows, plan, side read),
  `HoldTab.tsx` and `HoldWindow.tsx` rewritten on them. No server file, no rule, no log changed.
- Behaviour kept: VALIDATE logs each press, the answer goes stale when the contract changes, "I'm in" marks, the window follows
  the tab's selection, collapse / drag / Document PiP / tone on FOLD / mark form / after-close import.
- New on the tab: lots stepper (the lot size is learnt from the first answer), "I'M OUT — STOP WATCHING" (op exit), today's
  trades list, the runs of the word as the in-trade record. The window now fetches `rows=brief` so it shows the runs too.
- Found on the live FOLD: a broken line printed "−64 pts · ≈ ₹0 at risk"; it now says "N pts past it · the line broke at HH:MM".
- Checked on the live server at 14:12–14:18 in an isolated browser with VALIDATE's `&log=1` stripped and marking stubbed,
  so the checks did not enter her forward record (`data/hold/check_2026-09-25.jsonl` not created by the test).
  `npx tsc --noEmit` clean. Screenshots: `docs/mockups/validate-2026-09-25/shots/live-*.png`.
- Not seen yet: Document PiP with the new stylesheet copy (needs her click in Chrome).

- 14:45, her word ("if i m not in trade it should not show up and a cross sign to close"): the window shows ONLY for a marked,
  not-exited trade (no flat side read any more; the Validate tab still carries the side read as fact 3). A ✕ closes it for that
  trade (`hold.closed` in the browser); it comes back by itself for a new trade, or on the transition into FOLD, so closing
  can never hide the FOLD. The after-close tradebook import moved to the Validate tab's slip. Checked in an isolated browser.

## 2026-09-25 evening — every review finding fixed that changes no rule (her word: "fix every issue there is")

Source: `docs/hold/REVIEW-2026-09-25.md` (Opus, 4.5/10). Three streams, run in parallel:

**1. The rule changes, drafted for her signature and NOT built.** They are `docs/hold/PREREG-rev5-DRAFT.md` (the line break,
the display after a FOLD, the payers precedence, the copy) and `docs/hold/VALIDATE-rev2-DRAFT.md` (stop room vs noise, setup
age and arm, one wall one vote, holdability, GO needs HOLD, writers, press unit, outcome). An adversarial review follows before
she signs (P1-16). Disclosed by the drafter: the 3-minute close does NOT change the 12:02 CE FOLD (12:02 closes a 3-min bar);
7 of 8 breaks were smaller than one median 1-min candle.

**2. Server (no rule change), 1512 collected / 1509 passing (the 3 known desk failures):**
- `n_for` / `n_against` / `watch_items` on every row; `fold.L / px / by` for a line FOLD.
- `_payers` precedence: writers adding in her way for 3 min outranks a live fold on the row (the word never changed; probe green).
- VALIDATE facts carry `absence`; `writer_note`; fact 1 shows the trigger's age and the latest arm.
- `/api/hold/trades` carries `lots`; `mark` refuses a double-click; `reopen` (10 s undo); `exit_t` validated; the import writes
  `exit_t_broker` beside the clicked exit.
- CSRF: a POST from a foreign site (`Sec-Fetch-Site`) is refused.
- Absence kinds and copy fixed (P2); plan never prints a negative room; band rung declared "not built yet".
- The late-candle REST runs outside the per-index lock; a cached minute is re-read when later ladder bars / fill runs land (the
  live-vs-restart FLOW divergence, test written first and failed on the old code).
- `test_hold.py` fails loudly when its fixtures are missing.
- **FOUND, NOT ON THE LIST:** `_hold_rec` raised on a chain mark with no spot, so every SENSEX and BANKNIFTY hold read failed
  09:19–15:31 today (759 traceback lines in tapemap.log). Now read blind with the reason. Today's SENSEX/BANKNIFTY side rows
  are missing; an empty-body `POST /api/hold/import` after her restart would complete them (her call).

**3. The screens:** `ui-v2/src/hold/store.ts` (new: ONE poller for tab + window, every open trade, 8 s fetch timeout, no
overlapping polls, FOLD transitions, one AudioContext); `parts.tsx`, `HoldTab.tsx`, `HoldWindow.tsx`, `hold.css` rewritten:
- the word carries its qualifier (NOISE / STRUCTURE ONLY / NOTHING PAYING); the quiet clock and the read's age on every surface;
- a FOLD is cleared only by I'M OUT (✕ hidden); every open trade watched, the worst word in the head, "also open" with words;
- after a FOLD the stop is the line that broke, the wall is "not shown — the plan ended at the FOLD";
- the count as five marks + "n with · n against · n neither"; absences inside the facts; the writer note;
- lots out of the stale key, lot preloaded; I'M IN busy / idempotent; exit-time field; 10 s undo; slip collapses after an
  answer (I'M IN above the fold); strike stepper with ITM/ATM/OTM; keys C/P B/S ↑↓ Enter I O; side/role remembered;
- the answer dims past 60 s; "what changed" when the word flips; the word in the browser title; σ vs VWAP shown;
- straddle and order-flow-blind declared; error boundaries; window docked bottom-right, ≤ 600 px collapsed; PiP 380×110/600.
- Checked in an isolated browser with every write stubbed; `npx tsc --noEmit` clean.

Not done, and why: Playwright UI tests (a new dependency — ask); "I'm staying because…" and the entry commitment (new records —
ask); the post-close exit review (a new view — ask); PiP still to be clicked once in her Chrome.

## 2026-09-25 ~21:00 — rev 5 option B and VALIDATE rev 2, signed 19:40 on her delegation, BUILT

Signed texts: `docs/hold/PREREG-rev5.md` (06a54cee…5189) and `docs/hold/VALIDATE-PREREG.md` rev 2 (4a9b5963…4423);
PLAN rev 3a pointer (b7549d79…f0c4). Her words: "but i dont get it or capable enough to answer as a trader you think is
best take that for now". Built by an Opus agent from the signed text; reproduction checked before acceptance:
- rev 5 §E.1 option B: 33/33 frozen trades match (entry word, first FOLD minute and rule); the clamp binds on exactly the
  2 disclosed trails; today's CE folds 12:05 (8.0 past L, 3.1 past 23,070.3, B 4.9 @12:00, heals 12:11); the PE 13:59.
- VALIDATE §6: 09:35 WAIT 1·1·2 · 09:43 WAIT 2·1·1 · 14:12 NO 0·2·2, outcomes as disclosed.
- pytest 1539 collected / 1536 passing (the 3 known desk failures); the four hold files 81/81. server.py CRLF intact.
- Screens adapted to the new fields (4 facts, break level, after-fold, "OI blind", `against`); checked in an isolated
  browser on the new replies with writes stubbed. MACHINE strip, title and Glass board now read the ZONE machine.

**Interpretation choices the builder had to make (none tuned to data; for her review, like Q1–Q7 above):**
1. two closes read in one minute (late + on-time): broken if either broke; 2. a late close is judged against the level in
force at its own bar; 3. B read on a bar-close minute applies to that same close (as the disclosure's probe); 4. a trail
whose B cannot be read drops to buffer 0 on the new L, no clamp against a fallback level; 5. an entry-minute candle that
lands later than STALE_MIN: the line is never set and the trade reads PATA NAHI throughout (never a back-dated FOLD);
6. backfill tagging is per server read — after tonight's restart today's closes are tagged backfill (cosmetic, after the
close); 7. `late` is kept per index; 8. pivots can still move when a late candle lands (as rev 4); 9. `bar` added to the
logged line (clause 7a's key needs it); 10. template over example where they differ (punctuation, 2-dp distances);
11. copy the text never registered was composed (writer forms, some hints, "Line could not check — no candle for HH:MM");
12. Paying's "OI blind" = both payers and holders rows blind. Owed: saving the 14:12 check reply; a §7 judge.

## 2026-09-25 ~22:15 — MARKET NOW strip on the Validate tab (her word: "yeah a strip will be cool")

`ui-v2/src/hold/MarketNow.tsx` (new, display only, "conditions, not a vote"): the Board's own reads off `/api/board` —
trend or chop (the regime: price and OI, agreed or not, strong), who is pressing (the 5-family agreement with each family's
arrow), OI call- or put-heavy (PCR), the walls and who built them (built today / carried, and what they are doing now),
the mirror (each leg's premium vs its own VWAP in σ, and its pivots), the Board's headline — plus VPIN (`/api/vpin`,
NIFTY futures only, SHADOW, "not counted anywhere"). It feeds no word. It folds to one summary line whenever an answer
or a trade is on screen (I'M IN stays above the fold); a click opens it. UI only; no server change, no restart needed.
