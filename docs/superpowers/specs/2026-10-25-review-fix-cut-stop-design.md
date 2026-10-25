# Review 2026-10-25: FIX, CUT, STOP (design)

| | |
|---|---|
| Date | Sun 25 Oct 2026, written after the close |
| Status | **Approved by Mary, 25 Oct** ("rest is ok"), with F11 dropped. Not committed. Nothing is built. |
| Source | Three blind read-only reviews, `docs/review/2026-10-25/` (DEV-SERVER.md, DEV-FACES.md, TRADER.md). Every item below was checked against code or data before it went in. |
| Backlog rows | NOTEPAD A65–A81 |
| Her decisions so far | FIX list approved; CUT list approved; STOP list presented; **PaperDesk: leave for now. VPIN: stays, she wants to test it further.** |

## 0. Ground rules for every item

- **Surgical:**
  - Make the smallest root-cause diff.
  - Name what each change can affect and what stays untouched.
  - Every fix gets one test that fails without it.
  - Run the full pytest suite, the extension's 6 suites, `tsc --noEmit` and `vite build`.
- **Never touched by this work:**
  - the registered rules §1i–§1q and their browser computations (Validate `engine.js` rev 3 / 3.1, the extension's FADE KILL, READ-2's JAGAH push);
  - the engine, the zone machine and the §1d gate;
  - existing rows of any forward log;
  - `data/trigger_log.jsonl`.
- **Timing and approval:**
  - No edits that take effect during market hours, and no restarts during them. Server changes go live at her restart after a close; extension changes at her Reload + F5.
  - Commit only on her word, one commit per phase.
- **Monday 26 Oct runs on the committed code as it is.** Nothing here lands before Monday's close.

## 1. FIX (approved), in build order

### Phase 1: the record (server only; no face changes)

| # | Problem | Change | Test that fails today | Evidence |
|---|---|---|---|---|
| F1 | `score_frame` fills every row of the day file with the posting index's bars. | `score_frame.write(day, bars, idx)`: score only the rows where `r["idx"] == idx`. The server passes the POST's idx. | A day file with NIFTY + BANKNIFTY rows: BANKNIFTY's `ex` stays empty when NIFTY bars are posted. | A65 / D1 |
| F2 | One bar whose close is None makes the scorer throw, and every later write that day fails. | In `_fill_tap` and `_resolve`, skip any bar whose `c` is None. The key is left absent, so a later pass can fill it. | A hollow bar at i0 + 3 does not stop the other horizons from filling. | A66 / D4 |
| F3 | A feed gap is booked as one one-sided print. | In `ladder.attribute`: when the feed's own clock (`cts`) is more than 30 s apart between the two book rows, the pair is a gap (`kind="gap"`), booked to no side. Measured 25 Oct [M]: on the clean 23 Oct there were 0 such gaps (but about 26 a day over 5 s, so 5 s would flag quiet markets); the rule catches 16 Oct 11:12 (5,035 s, 934,635 units) and 12 Oct 12:58 (5,862 s). Rows with `cts` None (tests, old files) never read as a gap. In `vpin.on_frame`: the same 30 s bound on the frame's exchange `ltt`, live calls only (the 1-min backfill passes no time). The ux bar holding it gets `partial=True` and `why="feed gap Ns"`. Plus a read-only tool that lists past slug bars into a report; it never rewrites them. | Two rows 90 s apart with Δvtt 14,000 give no fill. | A67 / D3 |
| F4 | `day_state.save` has a shared `.tmp`, no lock, and 6 callers. A torn file loads silently as `{}`. | A module lock and a unique temp file in the same dir. On a corrupt file, `load` logs an ERROR, moves the file to `day_<d>.json.corrupt-<hhmmss>` and returns `{}`. `test_day_state.py:55`, which pins the silent behaviour, is updated. | Two threads saving at once leave a valid file. A corrupt file is kept and logged. | A68 / D2 |
| F5 | `tape_log`'s write-once is check-then-append with no lock. | One module lock around the seen-check and the append. | Two threads writing the same `t` produce one row. | A69 / D6 |

### Phase 2: the screens

| # | Problem | Change | Test | Evidence |
|---|---|---|---|---|
| F6 | The GoCharting panel can't see a SENSEX trade on the NIFTY chart, which is her §1q setup. | `fold_live.frame(idx, trades)`: when no open trade exists on idx, carry her most recent open marked trade on **any** index, with its idx. The panel shows the voice block with an index tag (e.g. "SENSEX"). **No chart lines when the trade's idx ≠ the chart's idx**: a SENSEX stop can't be drawn on a NIFTY chart (frame discipline). The block says "lines: SENSEX chart". If more than one trade is open, show a "+1 open" chip. | Server: a SENSEX trade under a NIFTY POST carries `fold`. Extension shell suite: a SENSEX fold on a NIFTY session renders the block and draws no lines. | A70 / F04 |
| F7 | A frame older than 15 s makes the panel flat mid-trade. | While the last good frame had an open trade, keep its voice block and its STOP / ENTRY lines, labelled `STALE hh:mm:ss`. No MARK buttons while a trade is open. | Shell suite: an in-trade frame left stale for 20 s still shows the block, now with STALE. | A71 / F01 |
| F8 | The Float shows an unknown headline as HOLD, and shows a dead server's last voice as live. | An unknown headline renders as `?`. The voice block shows its age, and `NOT LIVE since hh:mm:ss` when the poll failed (it reads `engineWhy`, as `Pro.tsx:35` does). | ui-v2 has no test runner, and none is added. Instead: `tsc` plus a render against `pro/fixture.ts` (the way A63 was checked), with an unknown headline → `?` and a failed poll → NOT LIVE, each screenshotted in light mode. | A72 / F02, F09 |
| F9 | When the voice is not ok, each face shows its own stop. | On all three faces (`main.js:342`, `validate2/app.js:138,319`, `pro/Desk.tsx:134`): no fallback stop. Show `stop: could not check — <why>`. | Shell suite plus a node harness: voice not ok means no KILL line and the text says could not check. | A73 / F03, TRADER F13 |
| F10 | Pollers have no timeout or in-flight guard, and every missing reply is blamed on an extension reload. | Reuse `hold/store.ts`'s `j()` (an 8 s abort) in `data.ts` and Validate's `pollFold` / `pollTrades` / `pollFlat`, with a busy flag. The extension skips a POST while one is in flight; `sw.js` fetch gets a timeout. `boot.js`: blame a reload only when `chrome.runtime.id` is gone; otherwise say "TapeMap not answering". | Extension: a shell-suite case where a hung fetch never says reload and a second POST is skipped while one is in flight. ui-v2 and Validate: a local mock that never answers turns the top bar NOT LIVE within 10 s, checked in the browser preview (no new test framework). | F05, F06, F19, F20 |
| ~~F11~~ | ~~Vite binds `0.0.0.0`~~ | **DROPPED 25 Oct, her call:** "dont worry about wifi thing it my home network". Not built. | — | A77 WONTFIX |

### Phase 3: the evidence

| # | Problem | Change | Test | Evidence |
|---|---|---|---|---|
| F12 | VALIDATE rev 3's word is never logged, so §1p can never be judged. | On every Validate check press, `app.js` POSTs `{t, idx, K, ty, side, rev, word, counts, checks}` to a new `POST /api/validate/log`. The server writes it once by `(t, idx, K, ty, side)` to `data/validate/press_<day>.jsonl`. It is a log only; the word is still computed in `engine.js` as signed. | A route test: two identical posts give one row. | A75 / TRADER F06 |
| F13 | Intake has stalled: trades a week went 31 → 1, with no tradebook import since 3 Oct, and 4 of the last 10 sessions recorded in full. | (a) **After 15:30**, if today has no import, the Float and Validate show `tradebook aaj import nahi`, with the existing `/api/receipts/import` drop target. She exports the CSV from Kite herself; nothing logs in for her. (b) **09:20 recording check**: if the book, chain, calls and read logs have no rows today, or no frame POST came in 2 min, a red bar on 5173 and the Float says `RECORDING NAHI: <which>`, and one row goes to `data/feed_log.jsonl`. | A unit test for each: empty logs at 09:20 → the bar names them. | A76 / TRADER F07 |
| F14 | In a trade, the voice says HOLD while the premium halves, and no premium % is shown. | `voice.py` l1 appends `prem −45%`: (LTP now − entry) / entry, sign by side, so a sale shows premium up as against. Display only; no state changes on it. When there is no LTP: `prem ?`. | The 22 Oct 73400 CE at 13:20 shows `prem −47%` (107.65 vs 201.4 at the 13:00 mark). | TRADER F02 |

## 2. CUT (approved)

### Off her screens

| # | Cut | Keep | Evidence |
|---|---|---|---|
| C1 | In the ANSWER band (`App.tsx` AnswerBand, rendered at `:1866`): the engine verdict, timing and direction chips, the engine headline, MAX PAIN / PCR / GEX / SQUEEZE, the day-type chip, and max pain as a level. | **THE READ's one-row form** in the band. The `calls` forward log keeps writing until its clock completes. | A74: GO↑ CONTRADICTED at 13:00 on 22 Oct |
| C2 | The tabs Heat, Glass, Tape, Events, Map and Chain (the type, the tab array, and their inline components; about 3,700 lines in `App.tsx`), plus `trending-glow`. | Read, Board, **OI Flow**, War, Validate, Signals, VPIN, Flow and Trade (9 tabs). | 3 Oct cut list; F28 |
| C3 | The EXPRESSION pill on the panel (`panel.js:241`). | The §1h log. Validate's "same thesis, better expression" slots already serve her both-ways rule at the press. | A79: median 65 flips a day |
| C4 | `daytype.py`'s AAJ KA DIN on every face (today that is only the ANSWER band). | DIN (§1o). `daytype` keeps feeding the `calls` log. | D9, TRADER F12 |
| C5 | In a trade, the panel shows only the voice block (l1–l5) and the chart lines. READ, KHEL, SIZE, DECODE, DIN, setups, FLOW, writers, fuel and BADE go under one `[detail ▸]` (shut by default, remembered). | Everything; it is only folded. | TRADER F15: about 185 items |
| C6 | T1 and `inval` in the Float detail (`pro/Desk.tsx:133-134`). | The voice's l5 PULLBACK. | F11 |
| C7 | LOOK HERE in the GlanceBar (`App.tsx:~260`). | — | 3 Oct |

### Dead code

| # | Cut | Note |
|---|---|---|
| C8 | `hold/HoldTab.tsx`, `hold/MarketNow.tsx`, the `HoldWindow` component, and `BoardRev3.tsx`, plus the routes `/api/hold?id=`, `/api/hold/check` and `/api/hold/expr`. | First move the types still imported from `HoldWindow`, and `useBoardGlance`, to where they are used. Grep both repos for each route before cutting. The server modules stay, because the rev 5 loop uses them. |
| C9 | `ui/console.html` and `/api/senses`. | Keep `ui/`'s icons, which her shortcuts use. |
| C10 | `start.bat`. The default broker becomes `upstox` (`chain_live.py:150`). | The Dhan code stays as the documented fallback. |
| C11 | The August `_srv*.log` / `tapemap-8765.log` in the repo root, `ui-v2/AGENTS.md` (Figma boilerplate), and the unused `fs2` in `panel.js`. | — |

### Server weight

| # | Cut | Note |
|---|---|---|
| C12 | The raw senses write (275 MB a day, 1.6 GB of 2.6 GB). | Write the per-minute sums `trap_log` reads instead. Test: on one past day, the sums from raw equal the sums written. The past raw files are kept. |

### Kept on purpose

- **OI Flow:** her keeper.
- **VPIN, in the voice and its tab:** her call, 25 Oct: "vpin stay i want to test it further". Its honest test needs a written kill condition (A35: range expansion, window, base rate). Drafted separately for her signature, then counted forward from the signature. Not built here.
- **PaperDesk, the desk compute and the routes** `/api/surface`, `/api/drag`, `/api/paper_fill`: her call, 25 Oct: "leave paperdesk for now". `paperdesk/v1.22.6` still calls them (A81).
- **The rev 5 hold loop:** cut it only after its signed §1e/§1f/§1g population reaches 30 sessions (around 6 Nov) and is judged.

### Data strays (only on her separate OK; backup first)

- 11 `trigger_log` copies;
- `data/hold/_test_leak/`;
- `data/void-2026-08-24-mock-leak/`;
- `desk_log` copies of 24–25 Oct.

## 3. STOP-BUILDING (presented 25 Oct)

| # | Freeze | Lifts when |
|---|---|---|
| S1 | New in-trade reads or exit layers. HOLD v3 lines stay in shadow; Fable's "BE lock after a 2nd push" and "take a third at the first wall" stay logged. | One in, one out (an old read retired first), or the voice has 20 scored forward trades. |
| S2 | New setups or registrations: A38, A50 window, A58, A36 fill, A9, A37. | The live setups reach their own bars. |
| S3 | Trading logic in the browser. | Never. New reads go in the server. |
| S4 | New instruments: Edge Reader live (A42), the shadow algo, A39, the Dext / retire-GoCharting track. | This FIX list has landed and 10 sessions in a row are recorded in full. |
| S5 | Face redesigns. | This CUT list has landed; then one tab at a time. |
| S6 | A forward log without its scorer and kill-clock line. | Never (a standing rule). |
| S7 | Anything for sub-5-minute scalps. | Not needed: on her table, ≤ 5 min has n 31, sum +192 pts, median +6, worst −18.8 [M]. |
| S8 | Seller-only layers. | 15 seller trades on record. |

## 4. Her decisions still owed (none blocks Phases 1–3)

1. **§1d gate:** read on 22 Oct (`docs/live/KILL-CLOCKS-2026-10-22.md`): KILL or CANNOT CHECK.
2. **VPIN kill condition:** sign the drafted definitions (see "Kept on purpose" above).
3. **`direction.py`:** log the bias, or retire it (A34).
4. **The EOD job to 15:45** (`schtasks /Change /TN "TapeMap EOD capture" /ST 15:45`; A40 / D27).
5. **The data strays** listed above.

## 5. Out of scope

- Splitting `server.py` (D12), and moving locked browser rules into the server (F14–F16).
- Vendoring Validate's CDN libraries (F24), and `pro.html` in the build (F26).
- An NSE holiday list for the logs (A80); the remaining P2/P3 findings in the three reports.

All of these stay OPEN in NOTEPAD for a later pass.

## 6. Done means

- Each phase's tests fail before and pass after. The full suite and the extension suites are green, `tsc` is clean, and `vite build` passes.
- **After her first restart following Phase 1:** a frame day file has no cross-index scores, and the log shows no `score_frame` exceptions.
- **After Phase 2** (extension 0.5.11), checked on the replay frames:
  - a SENSEX trade shows on the NIFTY panel;
  - a 20-second stale frame keeps the block with STALE on it;
  - a dead server shows NOT LIVE on the Float.
- **After Phase 3:** `data/validate/press_<day>.jsonl` gets one row per press, and the 09:20 check stays quiet on a recorded day.
- **After the cuts:** 9 tabs remain; the ANSWER band shows only THE READ; in a trade the panel shows the block plus `[detail ▸]`.
  - The cut screens and routes are removed from `CLAUDE.md`, `START-HERE.md` and the extension's `README.md` (they name `/console.html` and `/api/senses`).
  - NOTEPAD statuses are updated per item.
