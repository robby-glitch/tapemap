# 5. Safety review of the final blueprint, the amendment and the build packages

**Written:** 2026-09-28, evening. This was a read-only review: nothing was edited, started or committed. The only thing run was the extension's node tests.
**Attacked:** `4-final-blueprint.md`, `4-amendment-draft.md`, and packages P1-01 to P2-04 as the orchestrator summarised them.
**Checked against:** the code in both repos, `git status` in both, and the recorded `tape_` / `ux_` / `book_` / `chain_` files for 22–28 Sep.
**Tags:** [M] measured tonight, [I] inferred.

---

## 1. What held up [M]

- **The extension's current tree passes.** The uncommitted tree gives fit 33/33, engine 43/43, shell 76/76 (against `dist/src/main.js`, the file that ships) and overlay 13/13.
- **A marked trade survives a restart.** Each successful POST to `/api/hold/trades` saves day_state straight away (`server.py:2933`), and `_load_day_state` restores `hold_trades`. `test_hold_route.py::test_a_restart_reads_the_same_window` already tests this.
- **The hold door refuses cross-site POSTs** (`server.py:2873`).
- **No signed rule reads `fut_oi`.** It is read only by `grounds.py`, `frame.py` and `breadth.py`; `hold.py`, `validate.py` and `expression.py` never read it. So P1-04 can go blind safely.
- **`trigger_log.py` imports only `band_rotation`, `contract_bars` and `fronts`.** No package edits any of them, so §1d is untouched as claimed.
- **The chart's PDH/PDL/PDC come from `live._pivots` on `cfg["fut_id"]`.** They are the contract's own on 30 Sep, provided BUGFIX #6 (the expired-future filter) is running.
- **GoCharting's bar OI and Upstox's ux bar OI are in the same units.** Both read 11,654,500 at 09:15 on 28 Sep. Exact agreement by bar: 67/67 on 28 Sep, 74/80 on 22 Sep, 73/78 on 24 Sep, 50/53 on 25 Sep. See §3 for why this matters.

---

## 2. The forward record

**trigger_log is exposed tonight.** `git status` shows `D  data/trigger_log.jsonl` (the untracking is staged) while HEAD still holds a 402-line copy. The working file has 2,005 lines [M].

- Before her commit, any `git stash`, `git reset --hard`, `git checkout .` or whole-tree checkout by a build agent writes HEAD's 402 lines over the live file.
- The newest backup, `trigger_log.jsonl.bak-untrack-2026-09-28`, has 1,995 lines. It **does not have today's 10 rows** [M].
- Six packages are about to run in this tree. That is the single largest risk in the plan, and no package mentions it.

**The amendment edits signed files.** §2 adds a line, "closed by rev 6 …", to the top of each closed PREREG. That changes each file's sha256, which `research-findings.md` §1e–§1h record. The amendment's own signature, time and sha blanks (§7) also sit inside the file that gets hashed: filling them in breaks the hash.

- **The fix:** record the closures and her signature only in `research-findings.md` §1i, and never edit a signed file.
- **Proof of order:** the draft calls the file's modification time "the proof of order". Any editor, copy or checkout changes an mtime. The proof should be her commit of the hash, made before P2-04 runs.

**When the amendment takes force.** The draft says each closed section stops "on the first session after she signs". The faces (P3) and the removal of the retired rules (P3-02) come after the signature.

- If she signs on Wednesday evening and P3 is not live by Thursday 09:15, the closed rev 5 rules keep running and keep writing rows under a registration that is already closed.
- **The fix:** it takes force on the first session in which the rev 6 face is live, and that date is written into §1i.

**The gate is in-sample.** P2-04 runs on 22–28 Sep. Those are the days the (h) thresholds were chosen on, and P2-01's acceptance is the 8 design exits themselves.

- That makes the gate a check on the noise budget, not evidence that the engine works. Hashing the draft before the gate runs does not change that.
- **The fix:** the gate must also run on **29 Sep (expiry) and 30 Sep (the roll)**. No design has seen those days. They are reported separately, and the amendment says in plain words which days were design days.

**The shadow line during hours (P2-03).** P2-03 puts "shadow · rev 6 says: HOLD" on DESK next to the signed rev 5 window. Her trouble is holding, so she will act on it.

- That puts an unsigned rule into her decisions.
- It also contaminates rev 5's forward rows from the day it goes up.
- **The fix:** during hours, log only. Show the shadow in RECORD after 15:30, or live only if she says so.

**The data-leak guard is manual and incomplete.**
- `conftest.py`'s autouse fixture redirects only `tape_log.DIR`, `book_log.DIR` and `live.STICK_F`.
- The packages' tests write to other places:
  - P1-06 and P2-03 write marks into `day_state` and `hold`;
  - P2-02 writes `data/fold/`;
  - P1-05 writes the backfill file.
- A test run on the morning of the 29th would write a fake marked trade into `data/day_state/day_2026-09-29.json`.
- There were leaks on 08-24, 09-19 and 09-28 (the FRAMETEST sticks).
- **The fix:** add `day_state.DIR`, `hold_log.DIR`, `chain_live.CHAIN_DIR`, `calls_log.DIR`, `frame_log.DIR`, `senses.DIR`, `trigger_log.PATH`, the fold directory and the backfill path to the autouse fixture.
- Also add the new paths to `server._isolate_mock_writers`, a hand-kept list that P2-02 and P1-05 never mention.

**P1-06 already exists.** `test_a_restart_reads_the_same_window` covers mark, save, clear, load and the same window. Extend it with exit and reopen assertions rather than adding a new file.

---

## 3. The extension (P1-01, P1-02)

**The P1-01 contract match compares GoCharting with itself.** `frame.py:402` takes `closed` from the tape doc the extension posts, and `frame.py:263` builds `fut_oi` from those same bars.

- So "GoCharting's bar OI against the frame's future-bar OI" always matches, including on the wrong contract. The pause can never fire.
- **The honest reference is the ux bar's `oi`,** which comes from Upstox's book for the watched `instrument_key`. That needs a new frame field (the last N ux bars `{t, oi}`) in `frame.py` / `server.py`. P1-01 lists only extension files, so it crosses repos and depends on the tapemap commit.

**Tolerance, not equality.** On the same contract the two feeds disagree on 5–8% of bars, because the last OI tick lands inside the bar at different times.
- Typical gap: ≤ 0.1%. Worst: 157,495, 0.93%, on 22 Sep at 14:55 [M].
- Sep and Oct OI differ by millions.
- **The fix:** match when |ΔOI| ≤ 2% of OI on the same bar `t`, compared on closed bars only. Exact equality would pause the marks on a normal day.

**Missing brain.** When TapeMap is unreachable, `frame.day` does not exist. The fit must then read "not trusted: TapeMap not reachable" and must never fall back to "every loaded day".

**Guard `g.ahead` with the date.** `ahead` offers minutes of the last loaded session. Pre-open, with Friday loaded incomplete, it offers Friday's minutes. Offer `ahead` only when the last loaded bar's date equals `frame.day`.

**Smaller points in the uncommitted `fit.js` diff:**
- `loaded` is keyed by day of month, so two loaded days in different months collide.
- The cells no longer veto a label fit.
- A disagreeing paint now needs 2 strikes, which means one frame drawn on a stale fit.

All three are acceptable, but they should be named in her commit message.

**An unexplained fixture change.** `test/session-2026-09-10.ofd.json` was rewritten from 15m to 5m in the working copy. Only `confirm-study.mjs` reads it. Confirm who rewrote it before her commit.

**P1-02 is over-scoped for the night before expiry.** It turns a 519-line template render (`panel.js:515`) into per-block patching, and P3-03 rebuilds every block anyway. The smallest safe change tonight:
- swap the tokens;
- before `innerHTML`, collect the open `<details>` and restore them afterwards;
- skip the write when the HTML string has not changed.

That covers the confirmed defect (a frame closes her `<details>`) with a small diff. Leave the full patching to P3-03. `test/panel.mjs` must go into `npm test` and `verify`, or it never runs. There is no jsdom in the repo, so the test uses a stub.

**Reload and the relay.** P1-01 and P1-02 need one extension reload, then an F5 on GoCharting (the relay orphans). This is expiry morning, so reload only if every node test passes and she is at the desk before 09:10. Otherwise, the extension as it runs today.

---

## 4. The recorders, the roll and expiry

**P1-03 stamps the GoCharting tape with Upstox's contract.** `tape_<IDX>_<day>` rows are GoCharting's NIFTY-I bars posted by the extension (`tape_log.py:4-6`). Putting Upstox's `ik` / `expiry` on them is a measured claim the source never made. Tape rows already carry `session: "NIFTY-I|5m|…"`, so:
- stamp only `book_`, `ux_` and `chain_` rows;
- tape rows get `ik: null` and `ik_why: "GoCharting continuous NIFTY-I; contract not declared"`.

**P1-03 also needs `server.py`.** `Book.watch(idx, key)` carries the key but not the expiry, and `ux_log` rows have neither. Threading the expiry through touches `server.py`. P2-03 claims to own that file, and BUGFIX has uncommitted edits in it. Build P1-03 after her commit, as one change in one sitting.

**The 30 Sep roll is not covered for the Trade tab's levels.** `server.py:1354` pools the 5 prior GoCharting tape days into `prints.prior_levels` and `prints.naked`. On 30 Sep those are Sep-contract prices, drawn on the Oct chart and off by the calendar spread [I]. The Trade tab is kept by her order, and no Phase 1 package fixes this.

- **The fix:** drop prior tape days on or before the expired front future's expiry, with `prior_why` "the Sep future expired 29 Sep; earlier days are another contract".
- It must be live before 30 Sep 09:15.
- **BUGFIX #6 must also be committed and running by then.** Uncommitted, a stray checkout drops the filter and the ladder, VPIN and book go back to the dead contract.

**Expiry day, 29 Sep.** Rev 5 is in force with no expiry handling.
- The Sep future's OI drained from 17.0M to 10.4M over 22–28 Sep while it still traded 4.46M on 28 Sep [M]. Much of that volume is the roll.
- FLOW and VPIN on the Sep future therefore include roll-spread legs [I, not measured].
- Expiring OI coming off its peak after 13:30 is partly expiry closing, not writers giving up [I].
- P1-04 blinds only `fut_oi`, and `breadth.py:227-230` has the same roll defect (not on any screen today [M]).
- **What to do:** add one display line in the header on expiry day, as a disclosure and never a rule, and tell her plainly.

**Rev 5's latch is still live on 29–30 Sep.** It froze a wrong FOLD all day on 28 Sep. No Phase 1 package touches it, and none can without her signature. She should hear this from us, not find it at 09:35.

**P1-05: low value, medium risk.** `backfill_minutes` re-fetches from REST on every start, so the morning is not lost on a restart today. The file matters only when `fold.py` needs a deterministic replay. Defer it to P2 and add its path to the leak guard.

---

## 5. The engine and its log (P2-01 to P2-03)

**A stale or blind engine must never print HOLD.** Neither the blueprint nor any package defines the headline for three states:
- G cannot be seeded (chain down, no fight and no wall);
- the book or chain has gone stale;
- TapeMap was down for a stretch, and while it is down no book rows are recorded.

HOLD is a positive claim. For a trader whose problem is holding, a HOLD that has stopped looking is the costliest lie on the screen.

**The fix, in `fold.py` and its tests:**
- the headline reads **"CAN'T CHECK since hh:mm — why"**, with the last live read under it;
- no acceptance tally or OI event spans a data hole; each restarts after it;
- G and W carry through the hole.

**P2-02's "replay to identical" is not defined for live use.** The row schema cannot restore an acceptance tally in progress, the TIRING window, chip hysteresis or the σ window. So a restart must recompute from the recorded inputs.

- Live, chain rows arrive about 2 minutes late, so the fixture test (the same inputs twice) proves nothing about a live restart.
- **The fix:**
  - recompute causally, admitting a book row by its `t` (arrival ms) and a chain row by its own `ts`;
  - compare the recomputed words with the log; the log wins on screen, and any difference writes a `diverged` row.
- **Row cadence:** one row per event and one per bucket close, never one per batch. At 1 Hz from the mark to 15:29 that is tens of MB a trade, the same kind of load that wedged the server on 09-18.

**P2-03 cost.** Running fold inside the `/api/hold` path must be incremental and must never read a day's book file (about 60 MB) on a request. Add a timing assertion to its acceptance, not only the exception isolation.

**F\* before 15 minutes of basis.** The chain starts at about 09:17. The blueprint wants every read from its first mark, so F\* needs a stated rule for its first minutes, "basis n of 15 min", tagged [I]. G, W and A all hang off it.

---

## 6. Package conflicts and ordering

| file | touched by | the conflict |
|---|---|---|
| `server.py` | uncommitted BUGFIX, P1-03 (in fact), P2-03, the §4 roll fix | three builders in one file |
| `grounds.py` | uncommitted BUGFIX, P1-04 | P1-04 must follow her commit |
| `frame.py` | the P1-01 contract field (in fact) | not listed in any package |
| `panel.js` | P1-02, P3-03 | full patching done twice |
| `fit.js`, `overlay.js`, `main.js`, `dist/` | uncommitted work, P1-01 | build P1-01 on top of it, then run `npm run verify` |

**The order:**
1. her commits (the untracking, BUGFIX, the extension diff);
2. P1-04;
3. the roll fix;
4. P1-03 with the server threading;
5. P1-01 with its frame field;
6. P1-02 (minimal);
7. then P2.

---

## 7. Also found (not a package)

**`/api/frame` accepts a POST from any site.** Unlike `/api/hold/*`, it has no `Sec-Fetch-Site` check.
- A page she visits could send a no-cors text/plain POST with a fake tape.
- `tape_log` writes each bar once by `t`, so a forged bar that arrives first locks out the real one.
- The frame also feeds the band machine and, through it, trigger_log [I].
- **The fix:** the same one-line guard on every POST.

**Other smaller points:**
- **The §6.3 kill rule** lets any one of three alternatives replace the trailed rule. That is three chances at a false replacement. Name one primary alternative, the held breach alone, before the forward rows exist.
- **Calls and hold rows carry no code version.** BUGFIX and P1-04 change the grounds text partway through a population, so the rows can be told apart only by date. That holds only while every restart happens after the close.

---

## MUST-FIX, ranked

1. **Protect trigger_log before any agent builds.**
   - Copy `data/trigger_log.jsonl` (2,005 rows) outside the repo now.
   - Forbid `git stash`, `reset --hard`, `checkout .` and `clean` in every build brief.
   - Have her commit the staged untracking first. HEAD's 402-line copy overwrites the live file on any stash or reset, and the newest backup lacks today's 10 rows.
2. **P1-01's contract match is circular:** the frame's `fut_oi` is GoCharting's own OI.
   - Match against the ux bar `oi` (Upstox), exposed through a new frame field.
   - Use a 2% tolerance on closed bars.
   - TapeMap down means "not trusted".
   - Guard `g.ahead` by `frame.day`.
3. **The engine never prints HOLD when it cannot see.**
   - It prints "CAN'T CHECK since hh:mm" when there is no G, a stale feed or a downtime hole.
   - No tally or OI event spans a hole.
   - P2-01 and P2-02 tests prove it.
4. **Leak guard:** add `day_state`, `hold`, `chain`, `calls`, `frame`, `senses`, the trigger_log path, `data/fold` and the backfill path to the conftest autouse fixture and to `_isolate_mock_writers`. P1-06 extends the existing restart test with exit and reopen.
5. **The 30 Sep roll:**
   - the Trade tab's prior levels and naked POCs stop at the Sep expiry;
   - BUGFIX #6 is committed and running before 09:15 on 30 Sep.
6. **P1-03:** no Upstox contract stamp on GoCharting tape rows (`ik: null` with a why). Build it after her commit, together with the `server.py` threading it really needs.
7. **The amendment:**
   - never edit signed files;
   - sign and hash in §1i, not inside the draft;
   - in force from the first session the rev 6 face is live;
   - her commit of the hash, not an mtime, is the proof of order.
8. **The gate:** add 29 and 30 Sep as unseen days, reported separately, and state that 22–28 Sep are the design days.
9. **The shadow verdict** is logged only during market hours and shown after 15:30 (or live only on her say-so), so rev 5's rows and her signature stay clean.
10. **P2-02 resume:**
    - causal recompute on the arrival clock;
    - the log wins on screen, and a `diverged` row records any difference;
    - rows on events and bucket closes only.
11. **P2-03:** incremental fold with a timing test, and no day-file reads on a request.
12. **P1-02 cut to the minimum:** tokens, `<details>` state kept across the rebuild, and skip when the HTML is unchanged. Add `test/panel.mjs` to `npm test` / `verify`. Reload on 29 Sep only if every node test passes and she is at the desk.
