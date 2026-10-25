# DEV-SERVER: blind review of the TapeMap Python server, 2026-10-25

Scope: `tapemap/*.py`, `tools/`, tests (read only), and how data lands in `data/`. The server was not started and pytest was not run.
Each number is tagged [M] measured or [I] inferred. There are no rates.

## 1. Verdict

The server is careful in the small and sprawling in the large. Individual writers carry thoughtful guards, but one module of 6,544 lines wires 108 modules and eight or more in-trade reads together.
The record has four live holes, each with evidence:
- the frame scorer fills one index's rows with another index's bars;
- one hollow bar stops all scoring for the rest of the day;
- a feed gap becomes a fake one-sided print of up to 14,461 lots;
- `day_state` and `tape_log` writes have no lock.

All four fixes are size S. Ship them before building anything new, then cut the dead desk and the senses stream (275 MB a day).

## 2. Scorecard

| Area | /10 | Why |
|---|---|---|
| Architecture | 3 | `server.py` imports 81 modules (6,544 lines; `do_GET` alone is 1,003 lines). There are ≥8 in-trade reads, 7 definitions of "gave up" and 5 basis computations. |
| Live-day resilience | 5 | Strong: bind-first, the token is re-read on every reconnect, the feed backs off, fail-soft everywhere. Weak: gap slugs, a whole-file rewrite on the request thread, a log flood. |
| Forward-record integrity | 4 | `trigger_log` is now clean (5 legacy duplicate keys) [M]. Frame, tape and `day_state` are not. There are 11 hand-made `trigger_log` copies. |
| Tests | 5 | 1,824 test functions. They are welded to 331 private `server._*` names. The leak guard is an allow-list that has leaked. There are no concurrency or gap tests. |
| Ops and security | 5 | Good: the token probe in `start-v2.bat`, `127.0.0.1` on 8765. Bad: Vite on `0.0.0.0` proxies the API, `taskkill /F`, the log rotates the day away in hours. |

## 3. Architecture: the real graph

Reachability is from the AST import graph, including `importlib` [M].
- **Import-reachable from `server.py`:** 108 of 112 non-test root modules, 44,636 of 45,606 lines.
- **Not reachable:** `signal_review` (test-only, 308 lines) and three CLIs (`eod_capture`, `recover_tape`, `upstox_auth`).
- **tools/:** 17 files, 4,014 lines. One of them, `tools/rank_build.py`, is on the live path: it is loaded by file path (`server.py:2047`).

```
Upstox WS (upstox_feed thread, token re-read per connect)
  ├─ chain: upstox_chain/adapter → chain_live.ChainPoller → data/chain/ → chain_metrics, fronts, sides, trap, warmap…
  └─ book frames: feed.on_frame → book_log buffer → senses loop (0.5 s) → data/book/ → ladder/ux_log → data/tape/ux_*
Upstox REST (per-index refresh thread, 15 s) → live.build_session → engine + band_rotation → /api/data
  └─ trigger_log, confluence_log (FADE / RIDE / FADE-D), calls_log
Threads: senses (surface, desk_log, drag, warmap, vpin, day_state), hold (hold_log), sides, trap,
  fold (fold_live: the whole day's book + chain in RAM), reader (reader + xindex), daylog
Extension POST /api/frame → frame.build, frame_log, tape_log, decoder_log, fold_live, voice, trademap,
  story, validate_live, frame_v2 (+ rank_build), then score_frame (a whole-file rewrite) on the same thread
ui-v2 GETs → /api/read (read + decode over v2feed day files), /api/v2/data, /api/board, /api/fold*,
  /api/hold/*, /api/story, /api/calls, /api/oihist, /api/tape, /api/day/record (record_read)
```

**Routes with no caller in ui-v2 or orderflow-desk** (grep [M]):
- `/api/surface`, `/api/drag`, `/api/contract`, `/api/feed`;
- `/api/dext/parity`, `/api/dext/candles`;
- `/api/paper_fill`;
- `/api/senses` (only the old `ui/` calls it).

**Same concept, computed several ways:**

| Concept | Implementations |
|---|---|
| In-trade word | `hold.py` (§1e), fold rev 6 (`fold.py` + `fold_live`), `hold2` (§1m), `holdshadow` (3 lines), `voice`, `trademap`, `validate_live`, `story.trade_read`, `plan` (§1f), `expression` (§1h), `validate.py` (§1g), `engine.js` rev 3.1 (§1p, §1q). |
| "THE READ" | Two modules carry the name: `frame.py` ("THE READ, composed") and `read.py` ("THE READ"). `reader.py`/`reader_live` is the shadow leg engine. `record_read` only reads the frame file back. |
| Frame | `frame.py` (v1, composed per POST) and `frame_v2.py` (cached v2 parts). `v2feed` is the day-file feed under both `/api/read` and Validate. |
| Day type | `daytype.py` (AAJ KA DIN on `/api/calls`) and `onesided.py` (§1o, LOCKED). |
| "Gave up" | 7 definitions; see D8. |
| Basis | 5 computations; see D10. |

## 4. Findings

| ID | Sev | Finding | Evidence | Action | Size |
|---|---|---|---|---|---|
| D1 | P0 | `score_frame` fills EVERY row of the day file with the posting index's bars. `frame_<day>.jsonl` holds all indices, so a BANKNIFTY or SENSEX row is scored on NIFTY's moves, written once and never corrected. | `score_frame.py:55-60` has no idx filter. `server.py:4754` passes `doc.closed`. On 21 Sep, 4 BANKNIFTY rows share i0 (2, 8, 48) but carry different ex values (−60.6/−78.6 vs +5.4/+11.4). 18 Sep has 4 BANKNIFTY rows among 2,155 NIFTY rows. [M] | FIX: score only `r.idx == idx` | S |
| D2 | P0 | `day_state.save` uses one shared `.tmp` name with no lock and is called from ≥4 threads. `load` reads a torn file as `{}`, so her marked `hold_trades` vanish at the next restart with no log line. A test pins this silent cold start. | `day_state.py:62-65`, `day_state.py:85-90`; callers `server.py:918, 2344, 3906, 4295, 4342, 4552`; `test_day_state.py:55`. No incident measured [I]. | FIX: lock, a unique tmp, log and keep a corrupt file | S |
| D3 | P1 | A feed gap becomes a fake one-sided print. `ladder.attribute` and `vpin.on_frame` difference the cumulative `vtt` across any time gap and book the whole gap to one side at one price. The bar is not flagged, and the restart rebuild replays the same gap. | `ladder.py:84-100`, `vpin.py:146-160`. Book gaps over 60 s in session on 7 of the last 25 NIFTY days [M]. Resulting ux bars, all with `why=None` and `partial=False` [M]:<br>• 12 Oct 12:55: vol 8,312, Δ −8,162 (median 471);<br>• 16 Oct 11:10: vol 14,525, Δ +14,461 (median 779);<br>• 25 Sep 14:05: vol 3,889, Δ +2,781 (median 621). | FIX: treat Δt > ~5 s as a reset; mark the bar partial with a why; list the affected bars (never rewrite the record) | S |
| D4 | P1 | `score_frame` crashes on a bar whose close is None. Because that bar stays in `closed`, every later write that day fails, and the cells are never filled afterwards (the scorer runs in session only). | `score_frame.py:43`. Failures in `tapemap.log*`: 45 on 9 Oct (10:10–14:00), 11 on 12 Oct, 19 on 19 Oct (14:07–15:30). In 19 Oct's frame file, 14:xx has 4 of 373 taps filled and 15:xx has 0 of 115 [M]. | FIX: skip None closes | S |
| D5 | P2 | The frame record ("THE ONE DECISION RECORD") is rewritten whole on the extension's request thread at every closed bar. A torn line mid-file is silently dropped, and a test pins that. | `score_frame.py:85-115` (its own note: "~7 s CPU on 244 MB"), `server.py:4752-4756`, `test_score_frame.py:79` | FIX: run it on the hold thread; send torn lines to a sidecar | M |
| D6 | P2 | `tape_log`'s "write once by t" is check-then-append with no lock across server threads. Readers dedupe ad hoc; `fold_live`'s tape list does not. | `tape_log.py:173-216`: `seen_b` is updated only after the write. 41 duplicate bar-t rows over 8 NIFTY days, 18 of 71 on 12 Oct [M]. `fold_live.py:263`. The same unlocked pattern is in `server._read_log:1613`, `_shadow_log:3351`, `_map_log:3375` (0 duplicates measured there). | FIX: one module lock each | S |
| D7 | P1 | Vite binds `0.0.0.0` and proxies `/api` with no auth. Anyone on the same Wi-Fi can read receipts and trades, and can POST `/api/hold/trades` (curl sends no Sec-Fetch-Site, which passes the door). | `ui-v2/vite.config.ts:17`; the door rule in `server.py:4460-4475`. `../ngrok.log` (26 Aug) shows 8765 tunnelled publicly once [M]. | FIX: `host: '127.0.0.1'` | S |
| D8 | P1 | Seven definitions of "gave up". The voice can raise V2GU, PGU and GAVEUP as three WARN rows at once. | `fronts.py:293`, `board.py:99`, `ride.py:174` (§1j), `hold2.py:232` (§1m), `fold.py:1227-1240`, `voice.py:79-95`, `story.py:319-322` | LOCKED (`ride`, `hold2`); FIX the voice to show one gave-up row naming its source | M |
| D9 | P1 | Two day-type reads reach the faces: `daytype.py` (AAJ KA DIN) and §1o's one-sided meter. | `server.py:1522` (`/api/calls`), `onesided.py` | LOCKED (§1o); CUT `daytype` from the faces | S |
| D10 | P2 | Basis is computed 5 ways: 3-min median (frame and fold), 15-min median (`read.py`), 15-min of 5-min closes (`daytype`), and instantaneous twice (`live.py`, the `frame.py` fallback). One strike can sit at two futures heights on two panels. | `fold.py:44`, `read.py:269`, `daytype.py:368-370`, `live.py:959`, `frame.py:132-141` (the docstring still says 15-min) | LOCKED for RIDE's trail (§1k); FIX one function for the rest | M |
| D11 | P2 | ≥8 in-trade reads are computed side by side on every frame POST and hold poll; the voice exists to reconcile them. | `server.py:4687-4718`, `server.py:3260-3440`; §1e–§1h and §1m/§1p/§1q are signed | STOP-BUILDING: no new in-trade read until one is retired | L |
| D12 | P2 | `server.py` is a god module. Tests reach into its private names, so any split breaks hundreds of tests. | 186 functions, 77 module globals, 13 locks, 13 thread spawns, 94 `except Exception`. `do_GET` is 1,003 lines and `do_POST` 370. Tests reference private names 331 times (`_SENSES` 73×) [M]. | FIX: route table plus feature modules; no logic change | L |
| D13 | P2 | The deleted DESK is still computed and logged on every pass and copied at EOD. 8 routes have no caller. The Dext gate is mostly empty. | `desk_log.jsonl`'s last row is 23 Oct 15:26; surface is 1.3 MB a day. Dext: "no Dext candles" on 4 of the last 5 EOD runs. `signal_review` is test-only. [M]<br>CLAUDE.md still names PaperDesk as the reader of `/api/surface`, `/api/drag` and `/api/paper_fill`, but no PaperDesk folder is in `~/Downloads` [M]. | CUT, after she confirms PaperDesk is retired | M |
| D14 | P2 | The senses log writes 275.6 MB and 1,004,241 rows a day, which is 1.6 GB of `data/`'s 2.6 GB. Only `trap_log` (a shadow layer) reads it, and only for per-minute sums. | 23 Oct: "swept" 545,671 rows (152.7 MB), "pulled" 144,066 [M]; `trap_log.py:92`, `trap_log.py:152` | STOP-BUILDING: write the sums | M |
| D15 | P2 | A log flood rotates the session's evidence away. After a network loss, each refresh thread logs a 75-line traceback every 15 s. | 5 MB in 1 h 44 m on 23 Oct (16:11–17:55). The four 5 MB files together hold only 7–23 Oct [M]. | FIX: log once per state change; rotate daily | S |
| D16 | P2 | `stop.bat` runs `taskkill /F` and the server has no shutdown hook. Buffered book rows and up to 60 s of `day_state` are lost, and file tails tear. | `stop.bat`; no `signal`/`atexit` in `server.py`; `trigger_log.jsonl.torn.txt` [M] | FIX: a flush-on-exit handler | S |
| D17 | P2 | The test leak guard is a 31-path allow-list. It has leaked, and several writers are still not on it. | Leaks: `data/hold/_test_leak/shadow_2026-09-30.jsonl`, `stick_state.json.bak-leak-2026-09-28`, "197 rows" in the `conftest` note. Unguarded: `server.py:4599` (paper_fills), `eod_capture` and `recover_tape` BT, `voice_path`/`v2feed` DATA, `server.READ_DIR`. | FIX: one `TAPEMAP_DATA` root read at call time | M |
| D18 | P2 | Tests that pin real days rot into silent skips once `daylog` gzips those days. | `test_feed_health.py:174` points at `frame_2026-09-29.jsonl`, which now exists only as `.gz`, so it skips [M]. `test_effort.py:31`, `test_sensex_flow.py:149` and `test_onesided.py:163` read live 22 Oct files. | FIX: copy them to `test/fixtures` | S |
| D19 | P2 | The EOD desk snapshot is named by calendar day, so weekend runs create phantom sessions. Each copy is the whole running file since 24 Aug. | `eod_capture.py:292` vs `:285`. `desk_log_2026-10-24` (Sat 03:58) and `desk_log_2026-10-25` (Sun 00:41) are each 958,828 bytes, identical to 23 Oct's [M]. | FIX: use `session_day()`; CUT with the desk | S |
| D20 | P2 | A past-day replay holds the live locks. `v2feed` evicts by date, so an older day is evicted as it is inserted and reloaded on every request. Live `/api/read` and `/api/v2/data` stall meanwhile. | `server.py:1704-1772`, `v2feed.py:448-458` | FIX: replay outside the live lock; evict least-recently-used | S |
| D21 | P2 | `/api/health` coverage describes only the retired desk's reconstruction. It says nothing about READ, DECODE, fold, HOLD v2, the voice or the ux bars. | `server.py:6231-6306` | FIX | S |
| D22 | P2 | `trigger_log` has 11 hand-made sibling copies (22 MB) plus `data/backup` gz files. The record is uncommitted, so its history is ad-hoc `.bak` files. | `ls data/trigger_log*` [M] | FIX: one dated EOD snapshot; delete the strays on her OK | S |
| D23 | P3 | Dhan is still the default broker when `TAPEMAP_BROKER` is unset, and `start.bat` launches without it. | `chain_live.py:150`, `start.bat` | CUT `start.bat`; default to upstox | S |
| D24 | P3 | `/api/paper_fill` has no Sec-Fetch-Site guard (the hold, frame and dext doors do). Its only named sender, PaperDesk, is not on disk. | `server.py:4583-4604` | CUT (or guard it, if PaperDesk lives) | S |
| D25 | P3 | `fold_live` holds the whole day's book and chain rows in RAM: 77,438 book and 6,325 chain rows on 23 Oct, ≈0.37 GB by the close [I, sampled sizes]. | `fold_live.py:320-331` | Note only | – |
| D26 | P3 | No requirements file; `websocket-client` and `dhanhq` are unpinned. The server runs PATH `python`; EOD runs `C:\Python313`. | `where python`: a hermes venv python is second on PATH [M] | FIX | S |
| D27 | P3 | The EOD job captures and scores at 15:35, five minutes before the F&O close at 15:40. | `eod_capture.bat`; CLAUDE.md says the move to 15:45 awaits her OK | FIX on her word | S |
| D28 | P3 | Doc drift: START-HERE §8 cites `test_docs_claims.py`, which does not exist; `frame.py:133` says the basis is a 15-min median. | – | FIX | S |

## 5. Live-day failure modes

- **Token expired at 09:14.** `start-v2.bat` probes `/v2/user/profile` and re-auths before starting.
  - If a server is left running, the feed's reconnect loop re-reads `.upstox_token` on every attempt (`upstox_feed.py:149`, back-off up to 30 s), so a new token heals it.
  - REST builds fail and log a traceback every 15 s (D15) while the last good payload keeps serving. `built_at` ages, but nothing says "stale" [I].
- **Websocket drops mid-session.** The thread survives and `healthy()` goes false after 30 s.
  - On reconnect, the whole gap's volume lands in one bar as one-sided delta (D3).
  - That bar feeds VPIN, the ux bars and "BADA PRINT"-style reads.
- **Torn last line.**
  - Every JSONL reader skips it (`tape_log._read`, `confluence_log._rows`, `trigger_log.read` counts it).
  - `score_frame` deletes torn mid-file lines on rewrite (D5).
  - `day_state` treats torn as missing, which drops her marked trades (D2).
- **Restart at 11:00.** Done well:
  - `_load_day_state` runs before threads start;
  - the ux bars are rebuilt from the book file (but they replay the downtime gap as a slug, D3);
  - `fold_live` reloads the day's files;
  - `trigger_log` re-seeds `_seen` under a lock;
  - the voice re-dates its triggers at first look and says so (`seen`).
  - Not done: coverage does not describe any of this (D21).
- **15:30 and 15:40.**
  - The chain stops at 15:30 and the futures recorders at 15:40 (`server.py:1182`).
  - The forward-record gate is `09:15 ≤ now < 15:35` and weekday-only, with no holiday calendar (`server.py:2239-2251`).
  - Session constants are defined in 12 places (`chain_live` / `desk_log` / `sequence` / `validate_live` 15:30, `read` / `sides` 15:15, `confluence` / `faded` 15:00).
  - EOD runs at 15:35 (D27).
- **Request path.**
  - The frame POST builds ~10 sub-reads synchronously, then may do a whole-file rescore (D5).
  - `/api/read` is serialized under `_READ_LOCK` plus `v2feed._LOCK` (D20).
  - `record_read`'s cache keys on mtime and size, so during the session every append forces a re-parse of the 20–35 MB frame file per `/api/day/record` call [I].
- **Memory.** Most caches are bounded (decode 64, v2feed 3 days, `drag_day` deque 3,000). `fold_live` is day-bounded but large (D25).

## 6. Forward-record integrity

| Log | Write-once? | Evidence |
|---|---|---|
| `trigger_log.jsonl` | Rewritten by `score` (outcome fields only). It abandons if the log grew, with a small time-of-check/time-of-use window between the count and `os.replace`. | 2,459 rows, 0 torn, 5 duplicate keys (all from the two-server morning of 6 Aug) [M]. |
| `frame/` | No: a whole-file rescore per closed bar. | D1, D4, D5. |
| `tape/tape_*` | Claimed write-once; it is not. | D6. |
| `tape/ux_*` | Yes, but the content is wrong after a gap. | D3. |
| `day_state/` | An atomic rewrite, but the tmp is shared. | D2. 12 weekend-dated files exist (e.g. 5–6 Sep, 3–4 Oct, 17–18 Oct) because the save is unconditional. |
| `read/`, `hold/`, `decode/`, `calls/`, `sides/`, `trap/`, `decoder/` | Yes, via in-memory seen sets. | 290 files and 73,135 rows scanned: 0 torn, and 41 duplicates, all in `tape_*` [M]. |

- **Backups:** 11 `trigger_log` copies, a `.bak` of `day_state` on 1 Oct, `ofd_marks` `.bak` on 1 Oct, `stick_state` `.bak-leak`, `void-2026-08-24-mock-leak/`, `hold/_test_leak/`, `mock/`.
- **gz rotation:** `daylog` covers 9 directories, keeps 7 days plain and verifies each gz against its source (sound). `tape/`, `dext/` (84 MB), `xindex/` and `surface/` are never compressed.

## 7. Tests

- **Size:** 131 files, 28,589 lines, 1,824 test functions [M].
- **They pin behaviour that matters:**
  - the `trigger_log` restart race (`test_trigger_log.py:111`);
  - the feed lifecycle and the no-token-in-status rule (`test_upstox_feed.py`);
  - `day_state`'s same-day refusal;
  - `daylog`'s digest.
- **They mirror the implementation:**
  - 331 `server._*` references;
  - Hinglish strings asserted verbatim;
  - tests that pin bad behaviour (`test_day_state.py:55`, `test_score_frame.py:79`).
- **Critical paths with no test:**
  - mixed-index frame scoring (D1);
  - a None close in the scorer (D4);
  - concurrent writers (D2, D6);
  - gap attribution (D3);
  - the EOD desk-record date (D19);
  - the Vite host;
  - shutdown flush (D16).
- **Leaks and rot:** D17 and D18.

## 8. Ops

- **Launch:**
  - `start-v2.bat` probes the token, refuses to reuse a non-Upstox server, and starts `cmd /k python server.py live`, which is detached enough.
  - `stop.bat` hard-kills (D16).
  - The legacy `start.bat` starts on the dead Dhan source (D23).
- **Secrets:** `.upstox_token`, `.upstox_token.bak`, `.upstox_app.json` (API key and secret) and `.dhan_token` sit in plaintext in the repo root. All are gitignored (`git check-ignore` [M]).
  - They are not reachable over HTTP, because static files are served from `ui/` only.
  - The token is never logged (`upstox_feed.status`).
- **Binding:** 8765 binds `127.0.0.1` with `allow_reuse_address=False` (good). 5173 binds `0.0.0.0` (D7).
- **Logging:** a rotating handler at 5 MB × 3 that loses days to tracebacks (D15). Stale `_srv*.log` and `tapemap-8765.log` files from August sit in the repo root.
- **EOD:** a weekly scheduled task, Mon–Fri 15:35, last run 23 Oct 15:35, next run 26 Oct [M]. It runs capture, the score, `mark_grade` and `dext_parity`.
  - The weekend files in D19 came from a manual run, not from the task [I].

## 9. Top 10 actions, ranked

1. **D1:** filter `score_frame.score` by `r["idx"] == idx`. One line. Add a mixed-index test.
2. **D4:** skip bars whose close is None in `_fill_tap` and `_resolve`. One guard. Add a test with a hollow bar.
3. **D3:** add a gap reset in `ladder.attribute` and `vpin.on_frame` (Δt > 5 s → reset; bar marked partial with a why). Then publish the list of slug bars already in `ux_*`: 12 Oct 12:55, 16 Oct 11:10, 25 Sep 14:05, 19 Oct 09:35, …
4. **D2:** add a lock and a unique tmp to `day_state.save`. Make `load` log a corrupt file and move it aside, never return a silent `{}`.
5. **D7:** set the Vite host to `127.0.0.1`.
6. **D6:** add locks around the seen-set appends in `tape_log`, `_read_log`, `_shadow_log`, `_map_log` and `decoder_log`.
7. **D5 + D20:** move `score_frame.write` off the request thread, and run replays outside the live locks.
8. **D15 + D16:** log once per error state with daily rotation; add a flush-on-exit hook and make `stop.bat` send it.
9. **D13 + D14 + D23 + D24:** CUT the desk compute and logs, the uncalled routes, `start.bat`, the Dhan default and `paper_fill`. Write trap's per-minute sums instead of 275 MB of quotes.
10. **D11 + D8 + D10:** STOP-BUILDING new in-trade reads. In the unlocked code, collapse to one gave-up row in the voice and one basis function; the LOCKED ones stay.
