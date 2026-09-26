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

## 2026-09-26 — her 15:00 practice, as a reminder only

Her words: "we gonna close our position before 3 because due to new cas system is highly volatile ... no trade buying or
selling after 3 ... dont make any new rules". `parts.Cutoff` (display only, blocks nothing, feeds no word): from 14:45 the
window's one line and footer and the Validate tab show "your 15:00 cutoff (CAS) — N min"; after 15:00, "past your 15:00
cutoff (CAS)". No rule, registration or server change. The unsigned expression draft gains a disclosure note and an additive
`after_1500` log flag (descriptive only).

## 2026-09-26 — THE EXPRESSION (rev e), signed 20:48, BUILT

Signed text: `docs/hold/EXPRESSION-PREREG.md` rev e, sha256 `45d8d369957d50303ccda89cf4588a1cc1102ff3e3b9d33b29cfedf2de45fc1e`
(verified before building; anchored in `context/research-findings.md` §1h; not edited). Her word: *"sign"*. Built by an Opus
agent from the text, with the disclosure code in `docs/hold/scratch-2026-09-25/expr/` as the reference. Nothing is imported from
that folder. §D was reproduced from the production code before anything was wired. **Nothing is committed.**

**Built:** §A (the read), §B (the writer's word), §E.3 (the logs) and §F.1 (the tab).
**Unchanged (§C, and every buyer rule):**
- `hold.py`, `plan.py` and `validate.py` are byte-identical: the window, THE PLAN and the buyer's VALIDATE rev 2 do not move;
- the window's copy is untouched, including §H.3's owed fix, which is not part of this build;
- the UI files `HoldWindow.tsx`, `parts.tsx`, `store.ts` and `MarketNow.tsx` are untouched;
- every signed text is untouched.

### What exists

**`expression.py`** (new, pure: no I/O, no clock):
- **the read:** `read(D, i, d)` is §A at one close. It gives the five facts as `[name, state, absence, text]`, the codes R1–R6
  (`R4cnc` for R4's could-not-check branch), and `grade()`'s word, `named_by`, `lead` and `strength`. The legs sit at one ATM
  strike, each with its premium, greeks and entry check. It also carries S, the line and the noise;
- **the helpers:** `since()`, `straddle15()`, `straddle()`, `wall_behind()` and `leg()`;
- **the writer:** `writer(D, i, d, side, k)` is §B: the four facts, GO / WAIT / NO with rev d's could-not-check clause and
  rev e's wall clause, X, P, `beyond_strike` and `stratum`. `writer_outcome()` scores P − X before the static L;
- **the outcome:** `r_mults()` gives the R-multiples on the shared line, G and G/S, %, MFE, MAE and the move split;
- **the rows:** `row()` builds the `expr` row and `outcome_row()` the `expr_outcome` row; `regime_board()` gives the
  board's REGIME, both halves;
- **the flags:** `after_1500()` and `is_unit()`, plus `leg_spot()` (interpretation 1).

**`hold_log.key`:**
- a `check_outcome` row keys `(idx, t, d, role or "long", "outcome")`;
- an `expr` or `expr_outcome` row keys `(idx, t, d, kind)`.

**`server.py`** (CRLF preserved: 4,836 lines, all CRLF, and git shows 307 lines added and 12 changed, all intended):
- **new functions:** `_expr_day`, `_expr_cache`, `_expr_get`, `_expr_drag`, `_expr_tick`, `_expr_complete`,
  `_expr_verdict`, `_expr_setup_line`, `_expr_refused`, `_expr_press` and `_expr_reply`;
- **`_hold_tick(..., expr=True)`** writes the expression log. It runs inside a try, so a fault costs the expression's rows
  only, and those rows are not in the window's count;
- **`_hold_outcomes`:** the role key, plus the writer's outcome rows (role `short`);
- **`_hold_check`:** the `expr` block on every press. A SELL press's `validate` is §B's word (rev `2W`); if the expression
  fails, the press falls back to rev 2 §1.6's writer screen and never fails;
- **`_hold_import`:** no expression work on the request. It sets a flag, and `_hold_loop` completes the log on its own
  thread within about 10 s, in or out of session;
- **new routes:** `GET /api/hold/expr?idx=` (the slip's setup line; reads no close) and `GET /api/hold/sigma?idx=&k=&side=`
  (one leg's σ).

**The API the tab reads.** `/api/hold/check` gains `expr`:
- the word: `{ok, why?, d, dir, word, base, leg, leans, named_by, strength, lead, refusal, refused[], since, was{word,
  until}, since_gap, read_at, nb, ns, nn, count}`;
- the facts: `facts[{name, state, absence, text, tag}]`;
- the cards, `buy` and `sell`: `{side, role, k, atm, expiry, px, px_t, px_tag, delta, gamma, greeks_tag, greeks_why, entry,
  validate, named, refused[]}`. The sell card adds `wall`, `line_vs_strike` and `s4`;
- the rest: `zero_dte`, `printed{drag, expiry, regime}`, `not_shown[]`, `setup_line`, `draft`, `prereg`, `mine` and `log`.

A writer's `validate` is `{word, rev: "2W", count, n_for, n_against, n_neither, facts(4), needs, sentence, X, P, L, line,
noise, wall, beyond_strike, stratum, printed, draft}`.

**The logs:**
- **`data/hold/expr_<day>.jsonl`:** §E.3's `expr` row per close, per index, per direction (`prereg: "expr-e"`,
  `after_1500`, `unit`), plus one `expr_outcome` row per unit (09:44 + 30k) with the grid writer object and
  `beyond_strike`;
- **`check_<day>`:** every press gains `expr` and `after_1500`. A writer press is `rev: "2W"` with its word, the writer
  facts and `writer{X, P, L, line, noise, beyond_strike, stratum}`. Buyer presses keep `rev: "2"` and every earlier key.
  The writer outcome row has `role: "short"`, `target{P, X, level}`, `stop{L, pts}`, `first_30`, `first_1529` and
  `after_1500`. Buyer outcome rows gain only `after_1500`.

**The tab** (`ui-v2/src/hold/HoldTab.tsx` and `hold.css`, LIGHT, no charts):
- **THE EXPRESSION:** the word at 88 px, with LEANS above it at half size. The refused / tie / split / STAND ASIDE line is
  in caution ink, followed by the since-clock and the count (`… — of 5, a count, not odds`) and DRAFT;
- **two cards,** BUY left and SELL right, at the close's ATM strike. Each shows its premium and minute [I], Δ [M], its own
  VALIDATE word at 40 px, its entry check and σ. The sell card adds the wall behind it, the line against the strike and the
  S4 row on 0DTE. The named leg has a 2 px ink rule. A refused card is dimmed with its reason and never hidden. Each card
  has its own I'M IN;
- **below the cards:** the five-fact table (FOR BUY · FOR SELL · NEITHER, the sentence under each row with its tag and
  absence kind), then printed-not-counted (drag, expiry, the board's REGIME with both halves, each leg's σ), then not shown
  (a size, an order, odds);
- **the whole-read absence** is a hatched slot;
- **the slip** shows the quiet setup line;
- **her own contract's answer** stays below, unchanged, with its word at 40 px.

### Verified

**`test_expression.py`: 18 tests.**

The production code runs on the nine frozen index-days (NIFTY / SENSEX / BANKNIFTY × 09-22/23/24, both directions), under
the disclosure's reading of spot (interpretation 1). It matches §D exactly:
- **the words at the 2,250 closes:** BUY 293 · LEANS BUY 516 · EITHER 275 · LEANS SELL 325 · SELL 255 · STAND ASIDE 586,
  with the whole split (LEANS BUY · refusal · tie 169; STAND ASIDE both 360 · led 226);
- **stability:** 1,010 changes of 2,232; 562 of 1,028 runs last one read; 11 BUY ↔ SELL flips; 185 buy-side ↔ sell-side
  flips;
- **the refusals:** R1 355 · R2 311 · R3 98 · R4 24 · R4cnc 138 · R5 372 · R6 440, and the "behind the refusal words" table;
- **her 28 frozen entries:** the word, `named_by`, lead, b–s, refusals, since / was, the ATM sale and the writer's word,
  all as `revd/entries.json` and `reve/writer.json` (09-21 was never frozen);
- **the writer's word:** GO 633 · WAIT 1,262 · NO 355 at the closes, with no GO beside a sell refusal. At the 216 units,
  GO 60 · WAIT 121 · NO 35; in the stratum, 60 / 89 / 21; beyond the strike, 196. Resolved 78 in 30 minutes and 127 to
  15:29; 38 not scored;
- **G:** scored at 204 of 216 units (no premium 6, no greeks 6), with the words at the units as disclosed.

Under the text's reading of spot, one test pins that only 12 closes' words or refusals and 5 closes' writer words differ.
Each sits at a close where the chain spot and the index close name a different ATM strike or wall. None is unexplained.

**§H.7's owed tests, all written and passing:**
- the word order and `named_by`, including the refused tie as LEANS by refusal;
- `after_1500` changes no word or falsifier;
- R4 fails closed;
- ROOM's noise step;
- the sale at the buy's ATM strike, and an R6 unit still priced and scored;
- the writer's wall is §A's wall;
- could-not-check gives WAIT, never GO;
- no wall behind the sale gives WAIT, never GO;
- `beyond_strike` is written on the writer object;
- the stratum keeps units with the line beyond the strike;
- the outcome key collision.

**`test_expression_route.py`: 8 tests** on the frozen NIFTY 09-24 grid:
- a writer press gives rev `2W` and its row;
- a buyer press stays rev `2` and gains only additive keys;
- the press shows the last close's word, with both legs at its ATM;
- the tick writes 250 rows and 24 outcome rows, write-once;
- the import leaves the expression to the hold thread;
- a long CE and a short PE at one minute get two outcome rows;
- the setup-line route reads no close;
- a fault in the expression never costs the buyer's word.

**Totals and checks:**
- **pytest:** 1,565 collected, 1,562 passing, and the 3 pre-existing `test_desk_numbers.py` failures. Every earlier test
  passes unchanged: the 81 in hold, validate, plan and the route. The stated count is updated in `CLAUDE.md`,
  `START-HERE.md` and `context/DEFERRED.md`, which `test_docs_claims` requires.
- **The UI:** `tsc --noEmit` exits 0, and `pnpm run build` (vite build) is clean. The >500 kB chunk warning predates this
  build.
- **Nothing written** to `data/`; no `__pycache__` added under `docs/`. The running server was never started, stopped or
  called.

### Not verified (for after her restart)

**On live data:**
- a real press: the broker's greeks, the chain's minute closes, the resolved expiry text and the drag line;
- `/api/hold/sigma`, which makes REST calls;
- the expression log written by the loop at each close;
- the first-tick backfill after a restart. On the frozen days it cost about 1 s per index-day, but that has not been
  measured live;
- the unit outcome rows;
- the import's flag completing the log after the close.

**The tab in a browser.** No dev server was started against the live backend. **Her Vite dev server (the launcher's, 5173,
running since 09-25 22:17) hot-reloads the tab source.** So until her restart:
- the tab shows a hatched "not shown — the expression needs the server restarted on the new code" above the unchanged
  VALIDATE answer;
- the slip polls `/api/hold/expr` every 30 s, and the old server answers `ok:false` cheaply.

**Also:**
- the Document PiP (the window is untouched);
- expiry-day rendering (the 0DTE line and the S4 row).

**After her restart, check:**
1. A VALIDATE press on each index shows THE EXPRESSION. The two cards show premiums, Δ and both VALIDATE words, and σ
   arrives.
2. A SELL press shows GO / WAIT / NO with the four writer facts.
3. `data/hold/expr_2026-09-28.jsonl` fills: two rows per close per index. Outcome rows appear from 10:14 onward, or later
   when a unit's to-15:29 passage is still open.
4. `check_2026-09-28.jsonl` presses carry `expr` and `after_1500`, and writer presses carry `rev: "2W"`.
5. After the close, the empty-body import completes `expr_` within about 10 s.
6. `tapemap.log` has no "expression" tracebacks.

### Interpretation choices for her review (none tuned to data)

1. **"Spot" for the legs' ATM strike and the wall is the chain mark's spot.**
   - The text names it: "spot rounded to the step; the side log's `atm.k`", and the side log reads the chain spot. The
     index close is used only when a mark has none.
   - The §D disclosure read the index close for these, while it read the chain spot for fact 5 and S. Text over scratch,
     as instructed.
   - Under the text's reading on the frozen days, the words at the closes are BUY 292 · LEANS BUY 515 · EITHER 277 ·
     LEANS SELL 325 · SELL 254 · STAND ASIDE 587, and R6 is 436.
   - The writer's word is GO 636 · WAIT 1,259 · NO 355, and at the units GO 61 · WAIT 120 · NO 35.
   - Every difference is attributed (see Verified). `expression.leg_spot` is the one seam the test uses to prove both
     readings.
2. **Each close is read at its own bar,** without rev 5's late-candle refusal at the entry minute, as the close-time
   import reads. A close whose candle has not landed holds the log until it lands, or until 15:29, when it is written
   "could not check". A press reads its legs with `late`, as VALIDATE does.
3. **`strength`** is null for STAND ASIDE and could-not-check, which the schema does not name. `lead` for STAND ASIDE · led
   is the open leg minus the refused leg (negative), as the disclosure logs it; for both refused it is null.
4. **`word_1m` equals `word`:** at a close, the 1-minute read of that minute is the same read (§A.2 cuts every input to the
   close's minute).
5. **The `expr_outcome` rows and a writer press's outcome row are written only when whole,** meaning 30 finished minutes
   and the to-15:29 first passage known. The rows are write-once and carry `first_1529`, so an unresolved unit waits to
   15:29.
6. **One writer outcome row per (idx, t, d, short).** Two writer presses at one minute on different strikes are scored by
   the first press's strike, P and X, as the fixed key allows.
7. **The writer's P (you collect)** is the chain's minute close at the press [M], not a typed fill. X is PLAN §2.1's
   writer formula on the broker's Δ, Γ at that minute.
8. **Refusal codes are logged in R1…R6 order.** R4's could-not-check branch is the code `R4cnc`, printed "R4 — could not
   check: …".
9. **The drag number and σ:**
   - The drag number is logged only on a row written live within its own bar. A backfilled row says "not shown — read
     live".
   - σ is fetched by the tab after the answer, never inside the press: a REST call per leg could pass the tab's 8 s limit
     and fail the buyer's VALIDATE with it.
10. **§F.1's "hatched style" for the whole-read absence:** the word slot is hatched, and its chip keeps the
    could-not-check (dashed) kind. So the three absences stay distinct, as §F's own rule requires.
11. **Her pressed contract's full VALIDATE answer** (four facts, stop, wall, deeper detail) stays below the expression,
    with its word at 40 px. The cards are always the expression's legs at the close's ATM strike (§A.5), which may differ
    from her strike.
12. **A card's I'M IN** marks that leg: the ATM strike, now, the card's premium at the press minute and her lots.
13. **The backfill runs on the hold loop's thread.** The import only sets a flag. A thread started by the request could
    outlive a test and write into `data/`. The loop checks the flag before its in-session gate, so an import after the
    close still completes the log.
14. **A wall that reads BUILDING with no build today** is a read: "building, but with no build today — not counted". This
    is how the disclosure scored it.
15. **SPEED is tagged "M on I"** as §A.3 writes it. The other facts carry [M] or [I] as the text gives them.
16. **The quiet setup line** comes from `/api/hold/expr`, polled every 30 s. It reads only the zone machine's pick for the
    closed bar and never reads a close.
17. **A writer's printed-not-counted lines (§B.2)** are Your setup, the expiry line and X. σ is fetched separately, and the
    drag number is printed in the expression block.
