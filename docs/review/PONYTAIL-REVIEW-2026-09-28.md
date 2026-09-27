# PONYTAIL REVIEW — the whole app (tapemap), 2026-09-28

**Lens:** over-engineering only: what can be deleted, simplified, or replaced by the standard library or the platform.
Bugs, security and performance were out of scope. What the reviewers tripped over anyway is listed in §4, for a
correctness pass.

**How it was done:**
- Nine Opus reviewers, in parallel and read-only. Every line of tracked code was read, and every "dead" claim was checked
  with grep across the repo, the old `ui/`, `ui-v2/src`, `chrome-ext/` and the GoCharting extension.
- No test, server or script was run, and nothing was edited.
- The scopes were: A server and wiring · B tape core · C board and OI reads · D desk · E data plumbing · F hold / plan /
  validate / expression · G React UI part 1 · H React UI part 2, the old `ui/` and `chrome-ext` · I repo-wide duplication,
  legacy and docs.
- Their full findings follow in the appendix, one line each, in `<file>:L<lines>: <tag> <what>. <replacement>. (-N)`
  form.

## 1. The verdict

**About half of the app's code serves nothing she uses.** Of about 107,500 tracked lines of code (tests, vendored code and
mockups included), about **50,600 can go** once the reviewers' overlaps are removed. It falls into five groups:
- **screens she rejected**, and the backends that only they read;
- **charts**, which her "no charts, reads only" rule forbids;
- **dead research scorers**, which the §5 stop rule forbids re-running;
- **a lapsed broker** (Dhan);
- **prototypes, mockups and duplicated helpers.**

On top of that:
- **generated and legacy weight:** 91,479 lines. 84,769 of them are `graphify-out/`, which is tracked although
  `.gitignore` already ignores it;
- **docs:** 21,894 lines of executed plans, superseded handoffs and drafts kept beside their signed versions.

**The core she trades with is lean.** hold / plan / validate / expression: -168 lines (4%). Board and OI reads: -392. The
data plumbing, apart from Dhan, is mostly lean. The weight is around the core, not in it.

| area | net lines possible | the big one |
|---|---|---|
| H React tabs, vendor, old `ui/`, `chrome-ext` | -25,540 | `vendor/candl` (-14,075), a candle-chart library for charts she banned |
| G React UI part 1 | -13,300, and 6 npm deps | the Trade tab's chart stack (-4,380), `comps/` mockups (-3,323), the Glass board (-2,194) |
| D desk | -4,630 (up to -7,730) | the paper desk (-3,280), read only by the rejected desk screens |
| B tape core | -3,880 | the SMC chart layer (-1,160), the two-leg rotation stack (-950) |
| A server and wiring | -1,778 | a dead `/api/orderbook`; 895 lines of modules nothing in production uses |
| E data plumbing | -1,490 | the Dhan code (about -1,300) |
| I repo-wide | -554 code · -91,479 generated · -21,894 docs | `graphify-out` tracked against `.gitignore`; about 15 copies of the JSONL logger |
| C board and OI | -392 | `replay_dwell.py`, which grid-searches against the stop rule |
| F hold family | -168 | UI duplication; `expression.grade` written twice |
| **deduplicated total** | **≈ -50,600 code** (≈ -53,700 with two more of her decisions) | |

The overlaps removed from the sum (about 1,100 lines) are the modules two reviewers each flagged: `backtest.py`,
`run_score.py`, `squeeze_score.py`, `replay_dwell.py`, `test_docs_claims.py`, `/api/hold/side`, and I's stated overlaps.

## 2. Cuts that need no decision (dead by evidence, or already decided)

- **The old desk screens** (her decision of 2026-09-03): `ui/toolb.*` (-4,433), `ui/index.html` + `app.js` +
  `style.css` (-3,042), `ui/desk.html` (-1,863). Then the backends only they read: `/api/desk`, `/api/surface`,
  `/api/paperdesk`, `/api/drag`'s day trace, `/api/gex` (D: -4,630).
  - `/` still redirects to the rejected `desk.html` (`server.py:3246-3249`), and `start-v2.bat:97` opens it on every launch.
- **Not mounted or not imported:** `proto/` (-1,108, verdict recorded 08-05), `comps/*.html` mockups (-3,323), `OneTab`
  (-370), `MirrorTab` (-585), `BoardTab` (-530, imported but never rendered), the App's Tape tab (-420, which the 09-19
  spec already called a fossil), `chrome-ext/` (-469, the Kite panel, superseded 08-15), 2,224 `vendor` lines nothing
  imports.
- **Dead research code** (the §5 stop rule): `backtest.py`, `run_score.py`, `signal_review.py`, `squeeze_score.py`'s scorer,
  `replay_dwell.py`, `trigger_log.backfill` (together about -1,500 with their tests).
- **Dead routes and fields:** `/api/orderbook` (nothing posts to it), `/api/frame/bars`, `/api/hold/side`,
  `breadth`'s `fut_*`, `chainside`'s drain ranks, `trapped_inventory`'s unused modes, and about 30 unused params,
  functions and flags.
- **Duplication:**
  - the JSONL append / read / write-once code exists in about 15 copies (one ~30-line helper; -200);
  - "HH:MM" → minutes in 9 copies, ms → IST in 4, `market_hours` in 4, `IST` in 7 (one `clock.py`; -89);
  - `Rank` in 3 copies;
  - 6 hand-rolled UI poll loops (one `usePoll`);
  - `wash` × 6, `hhmm` × 5 and 4 lakh/crore formatters (`Intl.NumberFormat('en-IN', {notation: 'compact'})`);
  - `do_GET`: the query is parsed 16 times and the JSON reply built 33 times (a route table; -60).
- **Standard library:** `statistics.median` / `median_high`, `statistics.NormalDist` for `gamma`'s pdf and cdf,
  `itertools.accumulate`.
- **Repo weight:**
  - `git rm -r --cached graphify-out` (already gitignored);
  - `archive/` (-6,544);
  - the executed plans in `docs/superpowers/plans/` (-10,489);
  - `PREREG-rev5-DRAFT.md` and `VALIDATE-rev2-DRAFT.md` beside their signed versions (-1,591);
  - `test_docs_claims.py` (-136), which exists only to keep test counts written into seven docs;
  - `start.bat`, the Dhan-era launcher;
  - `trader.py.bak-before-shortstop`.
- **Unused dependencies:** Tailwind (loaded, but not one utility class used), `@types/node`, `oxfmt`, and the unused `@/`
  alias.

## 3. Cuts that need her word

1. **The charts:**
   - the Trade tab's candle panes and the SMC / levels overlay (G -4,380);
   - `vendor/candl` (H -11,850 of it in use);
   - the FlowTab price line (-300) and the VPIN polyline.
   Her rule "no charts, reads only" says delete, but these are on screens she may still look at. **Ask: do you ever use the
   Trade tab's candles?**
2. **Dhan.** CLAUDE.md calls it a documented fallback, but:
   - it is the **default broker** when `TAPEMAP_BROKER` is unset;
   - **the Upstox server cannot import without the Dhan SDK** (`live.py:27` → `dhan_fetch` → `dhanhq`);
   - the Upstox tape still downloads Dhan's 37 MB scrip master every day.
   About -1,500 lines. **Ask: is the Dhan fallback still wanted?**
3. **The paper desk** (`trader`, `book`, `quoting`, `hedge`: -3,280). Only the rejected screens read it, and the 3 tests that
   have failed for weeks live here. **Ask: is its 30-session record still wanted?**
4. **The desk's structure catalog** (-2,555). Its only live output is `desk_log`'s `deployable` field, which nothing reads
   back.
5. **Deferred tape decisions:**
   - the SMC chart layer (-1,160), marked dead, default OFF, yet computed on every refresh;
   - the two-leg rotation stack (-950), whose output nobody reads (START-HERE §7: "ship the pair chart or delete");
   - the trap=CLEAR compression read (-290), which the research record calls harmful and which still dims marks.
6. **The Glass board** `one/` (-2,194), a trial tab since 08-11 with no verdict, replaced by Board rev 3.
7. **Dark mode** (-250): she uses light only.
8. **`ui/console.html`** (-612): linked and launched by nothing. Does she open it by URL?
9. **Docs:** `context/HANDOFF.md`, a 2,137-line session diary whose state section is dated 08-25 (→ about 150 lines).

## 4. Outside this lens: found in passing, for a correctness pass (not checked here)

1. **First paint shows invented data.** `App.tsx`'s mock dataset (L79-388) fills the first render with random prices and
   invented signals (G).
2. **The broker default.**
   - Unset, `TAPEMAP_BROKER` means Dhan.
   - The Upstox path hard-imports the Dhan SDK.
   - `start.bat` launches Dhan (E, I).
3. **A registered shadow gate that cannot judge.**
   - No production caller passes `setups` to `regime`, so `would_block` is always `[]`.
   - The field its kill clock judges is therefore always empty (C).
4. **Test isolation gap.**
   - `server._isolate_mock_writers` does not re-point the senses, frame, calls, trigger_log or chain writers.
   - A mock or test run may write into real `data/` (A, I).
5. **The irreplaceable file.** CLAUDE.md says `data/trigger_log.jsonl` is deliberately not committed, but it is tracked in
   git. `.gitignore`'s note about `vpin_log.jsonl` is also wrong (I).
6. **The product fonts are not loaded.** Barlow and IBM Plex Mono appear nowhere. The CSS names Inter and Roboto Mono, and
   there are three monospace stacks (G).
7. **UI copy has drifted.** The hold UI hand-builds strings that the server already sends, and their wording has drifted
   from the registered rev 5 §B text. Using the server's strings would change what she reads, so this is her call (F).
8. **An unrendered network fetch.** Every `/api/warmap` poll starts an NSE network fetch for a `driver` output that no
   screen renders (D).
9. **A backfill that cannot fill.** `trigger_log.backfill`'s regex matches only receipts that `score` quarantines, so it can
   never fill a scored row (B).
10. **Stale ui-v2 docs.** `package.json` is named `figma-make-app`, and `ui-v2/AGENTS.md` describes a Figma Make
    environment (H).

net: -50,600 lines of code possible (≈ -53,700 with §3's items 3–4), plus -91,479 generated / legacy lines and
-21,894 lines of docs.

---

# Appendix — the nine reviewers' full findings, verbatim


---

## Appendix A-server

# Ponytail review A: server.py and its wiring

Scope: server.py (4,836 lines), conftest.py, start.bat, start-v2.bat, stop.bat, eod_capture.bat, tools/, and the
route/API tests. Lens: complexity only. Correctness, security and perf are out of scope. The one exception is
that `_isolate_mock_writers` is incomplete, which is noted for the correctness pass.

Evidence base for "dead": grep across tapemap/ui, tapemap/ui-v2/src, tapemap/chrome-ext, the installed PaperDesk
(operator mode/paperdesk/v1.22.6/src) and the GoCharting extension (Desktop/Go charting/orderflow-desk/src+dist),
plus every *.py and *.bat. The import graph was built by AST over every root *.py and tools/*.py, local imports
included.

## Findings (biggest cut first)

- server.py:L232-284,L92-95,L907-914,L3063-3094,L4058-4065 + test_senses_api.py:L19-75,L121-153: delete POST /api/orderbook, `_clean_books`, `_MAX_BOOKS`, `_SENSES["orders"/"orders_at"/"orders_n"]` and `/api/senses.orders_bridge`. Nothing posts to it. `orderbook-bridge.js` is gone from paperdesk/v1.22.6/src, where the extension's only POST is /api/paper_fill, and chrome-ext, orderflow-desk, ui and ui-v2 have 0 hits. The workspace README still describes v1.21.1. Replacement: `pools_mod.summary(lad, None)`. The absence sentence ("order counts absent… unknowable") is unchanged. (-190 lines incl. ~90 test lines)
- test_docs_claims.py:L1-136: delete. It is a doc linter that forces every new test to edit the "N collected" count in 7 docs (CLAUDE.md, START-HERE.md, HANDOFF, DEFERRED, PRODUCT, README, research-findings). It also pins ui-v2's SetupCheck.tsx imports and the HANDOFF header wording. Replacement: stop stating test counts in docs, since `pytest -q` already states them. (-136 lines)
- server.py:L3186-3227 + L4213-4244 + start.bat + test_upstox_only.py:L96-112: yagni. POST /api/token only writes `.dhan_token` and refuses on Upstox. `_build_why` only phrases Dhan errors, so on the live Upstox path a 401 reads "Dhan refused…". start.bat starts on Dhan, no shortcut targets it (both desktop .lnk point at start-v2.bat), and START-HERE:236 already says "legacy… avoid". The Dhan fallback itself is a DOCUMENTED decision (CLAUDE.md rule 1), so this is the operator's call. If the fallback stays, still delete start.bat. (-100 lines)
- server.py:L3-4,L76,L1057-1058,L2925-2933,L3297-3307,L3315-3317,L4820-4832 + analyze.py (43): yagni. This is replay mode (`python server.py [port] [data_dir] [strike]`) over the July 3-day CSVs. No .bat, test or launcher runs it; README.md:18 lists it as an "offline demo". Delete the branch, `analyze.py`, `payload_at`'s raw-bytes case, the `box is None` /api/data body, /api/chain's no-poller 404 and Handler's `chains=`/`poller=` kwargs, leaving `late` only. (-77 lines)
- server.py:L3229-4138: shrink. `do_GET` is a 24-branch if/elif with 16× `parse_qs(urlsplit(self.path).query)`, 33× `self._json(json.dumps(...).encode())`, 8 hand-copied "never 500" try/excepts and 8 ad-hoc `(q.get("idx") or [...])[0]` reads, 3 of them unclamped. Replacement: one `ROUTES = {path: fn(q) -> dict}` table with a single dispatcher that parses q once, dumps once and catches once. (-60 lines)
- test_upstox_only.py:L116-136, test_senses_api.py:L226-249, test_frame_api.py:L7-18,L131-137, test_board.py:L288-289, test_hold_route.py:L22-31: shrink. There are 5 fake-Handler harnesses (`_Cap` ×3, `_Req`, `_Post`), and `_Req` hand-rolls an rfile class where `io.BytesIO` works. test_frame_api's comment says "one copy in the tree", which is false. Replacement: one `_Cap` (with `_idx` bound and BytesIO body) in conftest.py. (-40 lines)
- server.py:L3000-3009,L3077-3083,L3097-3103,L3119-3125,L3208-3214: shrink. The Content-Length parse + cap + 400 reply is copied 5 times. Replacement: one `_body(cap) -> bytes|None`. (-30 lines)
- server.py:L4122-4129 and L2213-2222,L4088-4089: delete dead routes. GET /api/frame/bars has 0 callers (only docs/plans). /api/hold/side and `_hold_side_reply` have 0 callers in ui-v2 and 0 tests. (-21 lines)
- server.py:L292,L693,L722-723,L1630-1631,L1659,L1856,L1943-1944,L2103,L2823-2824,L3192,L3253,L3308,L3435-3436,L4248,L4269,L4298-4301,L4461,L4656-4658,L4702-4703,L4806: shrink. There are ~25 function-local imports. Several re-import names already at module top (`os`, `threading`, `time as _t`, `upstox_adapter as ua`, `upstox_instruments`), and `deque` is imported three times. chain_live is safe at module scope because test_broker_switch only forbids *chain_live* importing upstox. Hoist them. (-20 lines)
- server.py:L3723-3777 vs L612-663: shrink. /api/desk re-runs `desk.decide` per request for the same inputs `_log_chain_pace` already decides at chain pace, then patches the result with `_DESK_GATE.held_for`, which is the "PEEK, DO NOT FILTER" comment. Replacement: store the gated decision in `_SENSES["desk"][idx]` at chain pace and serve it. The only consumers are ui/desk.html (rejected, CLAUDE.md) and ui/toolb.js, which always passes the default capital. (-20 lines)
- server.py:L1925-1952 vs L1626-1653: shrink. There are two caches of the same "today's index 1-min candles": `_BOARD["trend_1m"]` and `_HOLD["c1"]`, the second with its own refetch clock. Replacement: one cache with the HOLD_REFETCH_S re-ask inside `_board_trend`. (-15 lines)
- tools/gate_report.py:L33-54 vs server.py:L1206-1215,L1303-1304: shrink. The dump→ofd→gcd lot resolution is written twice. Replacement: one `ux_log.resolve_lot(idx, day)` for both. (-15 lines)
- server.py:L1126,L1195,L1198 (+frame.py:L266-272,L403-410, gate.state's ivrv branch): delete. `"senses": None` and `"ivrv": None` are hard-coded constants, so the non-None branches downstream never run in production. Drop both keys and the dead branches. The absence reason text stays. (-15 lines, cross-file)
- server.py:L3360-3370,L3426-3434,L3904-3912: shrink. The chain box JSON is parsed by hand three more times while `_chain_doc` (L344) exists for exactly this. /api/desk also calls `_chain_doc` twice per index (L3743,L3750). Use it. (-12 lines)
- server.py:L4257-4287: shrink. `_isolate_mock_writers` hand-patches 14 module globals, and every writer builds `os.path.join("data", X)`. Replacement: one `DATA = os.environ.get("TAPEMAP_DATA", "data")` read by each writer, so `--mock-chain` sets one env var. (Correctness pass: the list already misses senses.DIR, frame_log.DIR, calls_log.DIR, trigger_log.PATH, CHAIN_DIR and data/paper_fills.jsonl.) (-12 lines)
- server.py:L882-906: shrink. The slow and fast VPIN gauge blocks are identical apart from key, bucket and queue. Replacement: a loop over `((name, None, vpin_due), (VPIN_FAST_INST, FAST_BUCKET_V, vpin_fast_due))`. (-12 lines)
- server.py:L937-952,L3111-3115,L4366-4370: shrink. There are four hand-written JSONL writers. Replacement: one `_write_jsonl(path, rows, mode="a")` next to the existing `_read_jsonl`. (-10 lines)
- server.py:L4025-4047 vs L4197-4209: shrink. The `_regime_engine_read` + `_walls_holding` + `f.verdict(six kwargs)` assembly is copied between /api/senses and `_view_for`. Replacement: one `_verdict(idx, inst, f, chain, payloads)`. (-10 lines)
- server.py:L2162-2222 vs L2317-2366: shrink. `def one(n)` appears twice, the "no finished minute of today's session on the chain grid yet" sentence 4×, and the `SESSION.index → sides(...)[-1] → {**side_line, "agrees"}` block 3×. Factor them out. (-10 lines)
- server.py:L3948-3966,L4383-4403: shrink. /api/vpin opens VPIN_LOG only to probe it before `_read_jsonl`, and `_vpin_fast_rows` re-probes and re-declares `_vpin_series`'s row shape. Replacement: one `_vpin_rows(path, day, inst)` that returns None on a read error and [] on a missing file, as the fast line's docstring argues, then `_vpin_series(rows, bf)`. (-10 lines)
- server.py:L2091-2093,L2340-2343,L2459-2461,L2594-2599: shrink. The same `fronts._at(...)` → `cell[0 if CE else 1]` → positive-float read is copied 4 times. Replacement: one `_leg_px(grid, t, k, side)`. (-8 lines)
- server.py:L127-131,L148-151,L920-932: delete stale or misplaced comments. "frame.py does not exist yet" and "Placeholder until frame.py lands" are false now, since frame.py is imported and wired. The 11-line 5a/5b lock comment sits above `_ux_drain`, which it does not describe. (-8 lines)
- start-v2.bat:L85-95,L117-124: shrink. There are two copies of the netstat poll loop (`:wait`, `:waitv2`). Replacement: one `:waitport <port> <tries>` subroutine. (-8 lines)
- server.py:L1148-1154,L1498-1501,L2287-2291: shrink. `payload_at(..., SCORED_INTERVAL)` → `json.loads if bytes` → `days[0]` is copied 3 times. Replacement: one `_day0(payloads, idx)`. (-6 lines)
- server.py:L2927-2933 (+every `self.chains`): shrink. `chains` IS `poller.boxes` (main L4692), so Handler carries two handles to one dict. Use `self.poller.boxes`. (-6 lines)
- test_frame_api.py:L55,L114-115,L156-157: delete. They re-set `tape_log.DIR` and clear `_seen_*`, which conftest's autouse fixture already does. (-6 lines)
- server.py:L3797-3809: shrink. The rv5 try/except assigns the same two fit keys in both arms. Replacement: compute `(rv, why)` in the try, assign once. (-5 lines)
- server.py:L1727,L2457,L2591: shrink. The strike-step expression is copied 3 times. Replacement: `_step(ks)`. (-4 lines)
- server.py:L446-448: stdlib. The hand-rolled sample variance is `statistics.stdev(rets)`. Also L276-279, L1692 and L2151 hand-roll NaN/inf checks where `math.isfinite` works. (-4 lines)
- server.py:L3522-3532: shrink. The `kind` filter re-derives lists already built as `arms`/`entries`: `sel = {"arm": arms, "entry": entries}.get(kind, rows)`. (-4 lines)
- server.py:L2131-2133: delete `_hold_sec`, a one-line wrapper with 1 caller (L3024). Inline it. (-4 lines)
- test_senses_api.py:L114-117: delete. The test only asserts that `threading.RLock` is reentrant, which is testing the stdlib. (-4 lines)
- test_broker_switch.py:L16-30: native. `_with` hand-rolls env save/restore. Use pytest's `monkeypatch.setenv/delenv`, as test_upstox_only already does. (-12 lines)
- server.py:L4706-4712: shrink. The `first` flag in `refresh_one` goes away if the sleep moves to the end of the loop body. (-3 lines)
- repo root: delete. `_srv.err`, `_srv.log`, `_srv_restart.log`, `_srv_restart2.log`, `tapemap-8765.log` and `trader.py.bak-before-shortstop` are untracked, and nothing in the tree writes them. (0 code lines)

Structural note (no net lines): server.py L1513-2922 holds ~1,400 lines of board/hold/validate/expression composition
inside the HTTP module. Moving it to a `hold_routes.py` would cut server.py by a third, with nothing deleted. The signed
rules stay exactly as they are.

Lean already: conftest.py, stop.bat, eod_capture.bat, tools/seed_tape_from_ofd.py, tools/gen_prints_expected.mjs,
test_session_json.py, test_hold_route.py/test_expression_route.py (fixtures aside), `_Server`, `handle_one_request`
latency seam, `_latency_summary`, `_coverage` (product absence sentences, not bloat).

Misnamed, not cut: test_contract_route.py (683) never touches the route. It tests `live.build_contract` through
Dhan-shaped fakes (`chain_live._client`, `token_status`, SECURITY_ID rows). If the Dhan fallback is ever dropped,
most of it goes too.

## Dead or unreachable modules

Import graph from server.py (AST, local imports included) reaches 78 root modules. What it does not reach, or reaches
only through dead code:

- backtest.py (288): imported by nothing but test_contract_bars.py:L245-295. Those two tests exist only to keep
  backtest.py's third copy of `_bands` identical to contract_bars. It is a backtest harness, which CLAUDE.md rule 2
  (stop rule) retires. Delete it with both tests. (-339)
- run_score.py (230): imported by nothing but test_band_rotation_run.py:L524-526, which pins one constant alias.
  It is a head-to-head research reproducer for dead hypotheses. Move it to archive/ and drop the pin. (-233)
- replay_dwell.py (128): 0 tests. It is reachable only as `python oi_dwell.py replay` (oi_dwell.py:L216-219) and
  re-scores oi_dwell calls over captured chain logs, which is the cache-slicing the stop rule forbids. Archive it and
  drop the CLI branch. (-133)
- squeeze_score.py (287): production uses only `load`/`_paths`/`_is_expiry` (L60-99, via trigger_log.py:L656 in
  `score`). L100-287 (`breakouts/outcome/collect/report/main`) is a killed hypothesis's scorer whose only other
  importer is run_score. Keep the loader (or fold it into trigger_log) and archive the rest. (-190)
- analyze.py (43): reachable only through server.py's replay-mode branch (see the finding above), with 0 tests.
  Dies with replay mode. (counted above)
- dhan_fetch.py: reachable (chain_live, live) only on the documented Dhan fallback path.
- Entry points, NOT dead: eod_capture.py (eod_capture.bat, a scheduled task), upstox_auth.py (start-v2.bat),
  recover_tape.py (manual CLI, named in `_rv5`), signal_review.py (manual CLI that writes
  ui-v2/src/trade/signalScore.json, which TradeTab reads).

Totals: server/wiring/tools ≈ -685, tests ≈ -198, dead modules ≈ -895.

net: -1778 lines possible.


---

## Appendix B-tape-core

# Ponytail review B: THE TAPE's core (complexity only)

Scope: engine, band_rotation, trigger_log, signals, signal_review, structure, levels, gate, ux_gate, ux_log,
sequence, sweep, runs, run_score, squeeze_score, score_frame, backtest, analyze, tape_log, recover_tape, driver
and the tests that import them. I read every file in scope, and every "dead" or "single caller" claim below
was checked with a grep across the Python, ui/, ui-v2/src/, chrome-ext/ and server.py (archive/, docs/,
graphify-out/, data/ and node_modules/ were excluded).

Nothing below changes the format of `data/trigger_log.jsonl`, weakens any of the three absence sentences,
drops an [M]/[I] tag or alters a signed rule's behaviour.

## Findings, biggest cut first

1. `structure.py:L184-316,L379-543` (+ SMC part of L1-179 docstring) — **delete** — The SMC layer's `compute()` is dead per research-findings §2 ("4x over-fires vs LuxAlgo, 2/3 UNKNOWN → default OFF"). It still runs on every refresh (`live.py:1047`, `analyze.py:29`). TradeTab still offers an SMC toggle, default OFF. Only `prior_day_hlc`/`_invert_pivots` stay live (`frame.py:312`). Keep those two plus `_num` and `PIVOT_RTOL`. Delete the rest and `test_structure.py` L1-616 and L737-888 (keep only the prior-day-hlc tests). Drop the `structures` key and the UI toggle. Needs her word, because the overlay can still be switched on. (-1160: ~400 code, ~760 test)

2. `band_rotation.py:L157-173,L243-273,L308-426,L1175-1274` — **delete** — This is the two-leg `detect()` path: `_view/_bar/_band/_oi_at/_rotating/_oi_slopes/_decelerating/_confirm`, `_SIGMA/_LEGS`, `ROTATION_WINDOW/OI_WINDOW` and interpretations 2-6.
   - Its only output is `/api/contract`'s `rotation` (`live.py:887`).
   - The only UI fetcher of `/api/contract` is `ui-v2/src/mirror/MirrorTab.tsx`, and it never reads `rotation` (0 matches). No `ui/` or chrome-ext file fetches `/api/contract` at all.
   - START-HERE §7 already says "ship the pair chart or delete the stack".
   - With it goes `test_band_rotation.py` L1-735 (`_run`→`detect`) and the rotation asserts in `test_contract_route.py`. (-950: ~300 code, ~650 test)

3. `signal_review.py:L1-308` + `test_signal_snapshot.py` — **delete** — This is the scorer that killed the engine event stream (§2), so its job is finished.
   - Its `--json` output (`ui-v2/src/trade/signalScore.json`) does not exist and nothing in `ui-v2/src` imports it.
   - It prints per-kind hit percentages (rule 4).
   - Only the snapshot test imports it. (-460)

4. `backtest.py:L1-288` + `test_contract_bars.py:L245-290` — **delete** — CLAUDE.md rule 2 means no new backtests, and no production code imports this file.
   - The only importer is the "third copy anti-drift lock" test on `backtest._bands`. That test exists only because the copy exists.
   - Update the `backtest.py::_pivots` mentions in `structure.py:100,119,365`. (-333)

5. `band_rotation.py:L176-228,L443-698` — **delete (her word)** — This is the compression read: `_index_rows/_index_by_day/_rank/_dwell/_direction/_trap` and `WIDTH_BANDS/TRAIL_*/TREND_WINDOW/COMPRESSION_RANK`.
   - It is the "compression / trap=CLEAR filter", which §2 records as HARMFUL.
   - It is still computed on every `detect_index` and `run_states` entry.
   - It still acts as a visual filter: CLEAR is drawn at full alpha in `LevelsOverlay.ts:886`, and it is a checklist item in `SetupCheck.tsx:394` and `Callout.tsx:210`.
   - Replace it with `trap: "UNKNOWN"` plus one sentence, or drop the keys.
   - `trigger_log` rows do not carry `trap`, so the log format is untouched. (-290)

6. `run_score.py:L1-230` + `test_band_rotation_run.py:L525-527` — **delete** — The §5c head-to-head ran on 2026-08-05 and is finished, and rule 2 forbids re-running it.
   - It prints `hit=` percentages.
   - Its only importer is a one-line test.
   - It carries its own `_minute` (L53-58), which duplicates `band_rotation._minute`. (-233)

7. `squeeze_score.py:L1-37,L100-287` — **delete** — This is the dead "squeeze + falling OI" scorer (§2 REJECTED): `breakouts/outcome/collect/_fmt/report/main`.
   - The only live code is `load()`+`_paths()` (L60-97), called by `trigger_log._load_sessions`. Move those ~25 lines into trigger_log (`_is_expiry` goes too, because trigger_log reads only `bars`).
   - Repoint `test_eod_capture.py:151` (it reads `squeeze_score.py` source text), `test_index_interval.py:343`, and the docstrings in `recover_tape`/`eod_capture`. (-210)

8. `trigger_log.py:L593-639,L595,L80-84,L1227-1228` + `test_trigger_log.py:L248-268,L612` — **delete** — `backfill()` can never fire on a scoreable row.
   - `_CLOSED_RE` matches only `_trigger_why`'s wording ("closed X back above"). That is the one-candle rule, and `score` quarantines it (L1044).
   - Every 5c and zone row carries `_run_why`'s wording ("closed X above that candle's high"), which has no "back", so the regex never matches it. (-75)

9. `trigger_log.py:L405-414,L499-506,L461-495,L549-553` — **shrink** — Three pieces of `log_new` are written twice or re-implemented:
   - The buy/sell one-slot merge is written twice. Replace it with one `_one_slot(buy, sell)`.
   - The 5c and zone arm blocks are two identical try-blocks. Replace them with a loop over `(("run_state","run_state_sell"),"5c"), (("zone_state","zone_state_sell"),"zone")`, keeping one try per rule.
   - The entry loop re-implements `_dedupe` inline. Collect the rows, then call `_dedupe`.
   - Row bytes are unchanged. (-25)

10. `engine.py:L1363-1380` + quiet prints `L489-490,L511-512,L556-559,L1274-1275,L1305-1306` — **delete** — `main()` is a CSV console printer that duplicates `analyze.analyze`. `quiet=False` is reachable only from it: every caller passes `quiet=True` (analyze, backtest, live, tests). Drop the `quiet` param, the prints and `import sys`. (-30)

11. `band_rotation.py:L938-966` — **yagni** — Once item 6 is gone, `detect_index_run` is a one-line wrapper over `run_states` with a 28-line docstring, and only tests call it (`live.py:1068` says it inlines the comprehension). The tests can do `[s["entry"] for s in run_states(...)]`. (-29)

12. `engine.py:L91-101,L171-173` — **stdlib** —
    - `Rank` is a third copy: `fuse.Rank` says it "mirrors engine.Rank exactly", and `vpin.Rank` is another. The engine can import `fuse.Rank`, because fuse is the side that refuses the engine dependency, not the other way round.
    - `median()` returns `s[len//2]`, the upper median. Replace it with `statistics.median_high(v) if v else 0.0`. (-12)

13. `tape_log.py:L130-133` / `ux_log.py:L71-74` / `sequence.py:L72-80` / `trigger_log.py:L555-558` — **shrink** — There are four copies of makedirs+open("a")+dumps+"\n". Replace them with one `append_jsonl(path, rows)` in `tape_log`. It writes the same bytes: tape_log keeps `default=str` as an argument, and trigger_log lines stay `json.dumps(row)`. (-12)

14. `ux_log.py:L48-64` — **stdlib** — `_dedupe_by_t` hand-rolls ordered last-wins. Replace it with `list({t: r for r in rows if (t := tape_log.bar_t(r)) is not None}.values())`; `bar_t` already has the same bool/number guard. (-15)

15. `sequence.py:L53-69,L56` — **delete** — `market_hours` plus `MARKET_OPEN/CLOSE` duplicate `desk_log.market_hours` (and trader.py has a third copy), so import it. `SHADOW = True` gates nothing and is read only by `test_sequence.py:28`. `LevelSeq.idx` is stored and never read. (-13)

16. `band_rotation.py:L231-236`, `structure.py:L213-217` — **delete** — Both duplicate `contract_bars._num` (and so do `fronts._num` and `contract_pair._finite`). Import it; contract_bars is equally pure and stdlib. (-10)

17. `signals.py:L63-65,L280,L384,L401-417` — **delete/shrink** —
    - `_hhmm` duplicates `visit._hhmm`, which is already imported as `visit_mod` and already used at L333.
    - `_ACTIVE` is never read.
    - `_state(tape, …, side, …)` never uses `tape` or `side`.
    - `_after_fire`'s second return value is discarded as `_at`. (-8)

18. `engine.py:L1229-1236` — **yagni** — `t_real`/`t_floored` are published in `ctx` for "a panel that must disclose". No UI, extension or Python reader exists; the only readers are tests on `GammaLayer`. Keep the GammaLayer attributes and drop the payload keys until a panel exists. (-6)

19. `runs.py:L46,L48-50` — **delete** — `_checked` is never read. `window_n` is read only by tests; they can use `len(r._win)`. (-5)

20. `sweep.py:L218,L230-231` — **delete** — `SweepDetector.events` is an unbounded list that production never reads (`senses.py` uses only the return value). Only `test_sweep.py:127,138` read it. (-4)

21. `gate.py:L43-46` — **yagni** — The `squeeze` parameter is always `None`: the only caller is `frame.py:194`, which passes `None`. So the `elif squeeze:` branch is dead. Make "day type: not measured yet" a fixed hole, the same way "event calendar not wired" is. (-4)

22. `levels.py:L162` — **yagni** — `n_static` rebuilds `static_levels` a second time per read, and only `test_levels.py:47` reads it. (-1)

## Not bloat, left alone

- **Lean files:** `ux_gate.py`, `tape_log.py`, `score_frame.py`, `recover_tape.py`, `driver.py`, `analyze.py`. `analyze.py` is the offline `--mock-chain` demo path from the README, and it is the only reason `engine.load`/`days_to_expiry` live.
- **`engine.py` event detectors:** every sampled kind still has a UI reader (checked for CAMPAIGN, BUYER-BUILD, PRESS and IGNITION; the grep over the rest was stopped). `ctx.plays` feeds the §1d veto, and the gamma layer feeds trigger_log rows. The "default OFF" verdict is enforced in the UI and is entangled with live outputs, so none of it is counted here.
- **`detect_index` (§1 one-candle rule, VOID):** still drawn by `LevelsOverlay`, `Callout` and `chrome-ext/content.js`, and the logger refuses it by design. Whether to stop publishing it is her call, not a complexity finding.
- **`trigger_log`'s f15/f30, `_level_of` receipt recovery and `show`:** these are record format and a CLI that START-HERE documents.
- **Narrative incident comments:** load-bearing by house rule.

net: -3,880 lines possible (≈2,250 production, ≈1,650 tests of dead code). About 2,400 of that needs her word first (items 1, 2 and 5, which are still rendered or explicitly deferred). About 1,400 can go without asking.


---

## Appendix C-board-oi

# Ponytail review C: board, frame, OI and order-flow reads

Scope: the 25 modules named in the brief plus the tests that import them. Every line was read, and every "dead" or "no caller" claim below was checked by grep across `*.py`, `ui/`, `ui-v2/src/`, `chrome-ext/` and the GoCharting extension at `C:\Users\kaam\Desktop\Go charting\orderflow-desk\src`, which consumes `/api/frame`.

## Findings (ranked, biggest cut first)

replay_dwell.py:L1-128: delete. This is an offline CLI that replays `data/chain/*.jsonl` through oi_dwell, and its `--sweep` grid-searches MIN_BASE over cached sessions. That is exactly the cache-slicing that research-findings §5 forbids. Nothing imports it except oi_dwell's own `__main__` (oi_dwell.py:L218), and no test exists. Replacement: nothing. Also drop oi_dwell.py:L28-31 ("TUNE... re-run replay") and the replay branch in L215-221, keeping `demo()`. (-134 lines)

trapped_inventory.py:L60-62,L64,L78-93,L159: yagni. The futures `side="both"` / `"long"` modes and `min_flow` are never used in production: chainside.py:137,195 only ever builds `Ledger(side="short")`, and nothing passes `min_flow`. Replacement: `trapped()` keeps only the short branch, `pain_long`/`pain_short` are inlined, and the flat check becomes `if d_oi == 0`. Their only users are test_operator_objects.py L37-67 (two futures tests), which go too. (-14 module, -31 tests)

frame.py:L98,L110 / watch.py:L71 / breadth.py:L68 / fronts.py:L193 / board.py:L44 / trendbox.py:L39 / grounds.py:L56 / visit.py:L60 / ladder.py:L144: shrink. There are 6 copies of "HH:MM -> minutes" and 3 copies of "epoch ms -> IST HH:MM" (signals.py has a 4th). visit.py:L61 justifies its copy by an import cycle, and that cycle only exists because the helper lives in frame. Replacement: one leaf helper (for example in fronts.py, which frame, board and watch already import), imported everywhere. (-22 lines)

regime.py:L61-68,L75,L125-134 + fuse.py:L194,L206: yagni. `setups` is never passed in production (server.py:4033 and :4204 omit it), so `asked = LEGAL[gear]` and `would_block` is always `[]`. console.html:339 renders an empty list forever. `allows()` (L132) is called only by test_regime.py. Regime is a registered SHADOW gate on a 30-session kill clock, and the field that clock is meant to judge is structurally empty. Replacement: either the caller passes `setups`, or `LEGAL`/`setups`/`would_block`/`allows` go. (-16 module, -20 tests: test_regime.py L24-83 would_block/allows asserts, test_fuse.py L121-122)

breadth.py:L115-126,L142-143,L226-232 + frame.py:L81-82: delete. `_fut` and `fut_oi_day/fut_px_day/fut_oi_window/fut_px_window/fut_why` have no reader in panel.js (breadthSec L268-280 renders counts, concentration, fronts, pressed and backfill only), in ui-v2 or in score_frame. `fut_oi_day/fut_px_day` is also the same arithmetic as frame._trapped `fut_oi` (frame.py:L262-263), computed twice in one frame. Replacement: nothing; frame's `trapped.fut_oi` stays. (-20 module, -3 tests at test_breadth.py L90-91)

frame.py:L403-410,L266-272,L69: yagni. `_book_for` hard-codes `senses: None` (server.py:1126), so the `senses.get("confirm")` branch and the `trapped.gear` branch can never run live. ui-v2 BoardTab.tsx:246-249 already calls gear "a STRUCTURAL hole". test_frame_zone.py passes `senses={"confirm": ...}` only to exercise the dead branch. Replacement: `confirm` becomes the constant "not wired" dict, which is still printed with its reason per the spec; `gear/gear_why/gear_tag` go, along with panel.js's never-true `gearLine`. (-12 module, -4 tests)

vpin.py:L95-109,L213-220: shrink. `Rank` is a byte-for-byte copy of `fuse.Rank`. Its stated reason, "this group replays without the engine", does not apply, because fuse is pure and imports no engine. `seed()` also re-types the event dict that `_close()` builds. Replacement: `from fuse import Rank`, plus one `_event(stamp, buy, sell, imb)` helper shared by `_close` and `seed`. Separately, as yagni noted only because this is a registered SHADOW gauge with a kill clock: the FAST line (FAST_BUCKET_V, its own log) is a second unpromoted population on the same clock. (-22 lines)

watch.py:L145-174 + breadth.py:L86-112: shrink. The per-strike peak-change scan is written three times: `watch._peak_chg` (its `upto` param is never passed; the only call is at L190), `watch._chg_now`, and `breadth._peak_chg`. `breadth._pair` and `breadth._px` are the same function with a different key, and `pair[0] if side=="ce" else pair[1]` is inlined four more times. Replacement: one `_leg(rec, field, k, side)` and one peak scan, shared. (-20 lines)

frame.py:L75-84: shrink. `_EMPTY_BREADTH` re-lists the 25-key default that breadth.build writes at L133-146, so it is two copies of one shape that can drift. Replacement: `breadth.empty(why)` used by both. (-9 lines)

test_operator_objects.py:L45-47,L80-92: delete. L45-47 is a dead loop (`snap_basis=None; for ...: pass`), and L80-92 is a hand-rolled test runner in a pytest repo. (-15 lines)

prints.py:L44-48,L118-121,L176-178: shrink. The five `q[k] += r.get(k) or 0` lines become a loop over `("b","s","u","bt","st")`. The POC loop becomes `max(range(n), key=...)`, which also keeps the first maximum. `with_cvd` re-inlines `_delta_of`. (-10 lines)

pools.py:L95-100: stdlib. `_median` is `statistics.median`, which has the same even-n averaging. (-6 lines)

trapped_inventory.py:L187-192: delete `Ledger.snapshot()`. It has zero callers; warmap.py:138 only names it in a comment. (-6 lines)

board.py:L53-54,L66-68 + frame.py:L56: shrink. `board.dom` re-types grounds' nested `dom` (grounds.py:L202-203), `board.sgn` duplicates `prints._sign`, and `frame.CONFIRMS` duplicates `signals.CONFIRMS` even though frame already imports signals. Replacement: make `grounds.dom` module-level and use `signal_mod.CONFIRMS`. (-6 lines)

watch.py:L49 / breadth.py:L115,L130 / trendbox.py:L76-77 / visit.py:L106: yagni. `watch.FLAGS` is never referenced. `_fut(t0_ms)` and `build(window_min=)` are never passed. `one_h` is `agg(rows, 60)`, since all inputs are in-session. `_fresh_arms(side)` is an unused parameter. (-6 lines)

gamma.py:L24-29: stdlib. `_pdf` and `_cdf` are `statistics.NormalDist().pdf` / `.cdf`. The docstring at L4 cites `gex_run.py`, which does not exist. (-5 lines)

ladder.py:L233-235,L153: delete `Ladder.close_open()`. It has no caller in the repo or tests; ux_log never calls it. `interval_s` is never passed. (-4 lines)

fronts.py:L324-327: stdlib. The running high is `list(itertools.accumulate(v, max))`. (-3 lines)

absorption.py:L124,L133: delete `AbsorptionDetector.events`. It is an unbounded per-instrument list (101 instruments, all session) that only tests read. senses.py uses the return value. (-2 module, test asserts switch to return values)

frame.py:L471-474: delete. `elif closed: S["visit"] = None` is a no-op because `_EMPTY_SETUP["visit"]` is already None. (-2 lines)

## Overlap verdicts (what the live path uses)

- **dwell vs oi_dwell vs replay_dwell:** no shared computation, only the name.
  - dwell.py is the war-map trap detector: warmap -> `walls.watch` DWELL flag -> extension.
  - oi_dwell.py is a hysteresis gate plus an OI-divergence direction: `/api/desk` -> toolb.js, so it is live.
  - replay_dwell.py is dead (first finding).
- **regime vs trendbox vs breadth:** three different "regime" words, none a duplicate of another.
  - regime.gear comes from fuse -> `/api/senses` and direction.py.
  - trendbox.regime (TREND / PIN-CHOP) comes from `/api/board` and hold.
  - breadth.regime/pinned is an echo of the engine's `pin.regime`. Its only reader is ui-v2 BoardTab, which is imported but NOT mounted in App.tsx ("one-line rollback"). It goes when that rollback is retired (UI scope).
- **fronts vs pools vs trapped_inventory vs ladder:** distinct inputs and distinct questions.
  - fronts is §1d chain-OI build/stall/unwind: the frame gate, board, oihist and hold.
  - pools is depth shelves and vacuums: `/api/senses` and `walls_holding`.
  - trapped_inventory is writer basis and pain: chainside -> warmap heat -> frame `trapped.writers` and wall-row pain.
  - ladder is footprint bars: ux_log -> prints/grounds CVD.
  - The frame publishes both `trapped.writers` (max pain) and `fronts` (§1d). The comment at frame.py:589-592 says this is deliberate, so it is not flagged.

## Lean already

frame_log.py, calls_log.py, grounds.py (apart from `_hh`), hunt.py, impact.py, dwell.py, senses.py, visit.py and fronts.py are otherwise fine. The `[M]`/`[I]` tags, the three absence sentences, `_forbid`, BANNED_WORDS, write-once logs, the §1d gate, the tells kill clock and the `__main__` self-checks were all respected and none is counted above.

net: -392 lines possible.


---

## Appendix D-desk

# D — THE DESK: ponytail review (complexity only)

Scope: desk.py, surface.py, direction.py, drag.py, warmap.py, book.py, book_log.py,
quoting.py, trader.py (+ trader.py.bak-before-shortstop), hedge.py, desk_log.py,
chainside.py, contract_bars.py, contract_pair.py, and every test importing them.
Read-only review, 2026-09-28. Every line read; every "dead" claim grepped across
*.py, ui/, ui-v2/src/, chrome-ext/, and server.py routes.

## Who reads what (the evidence everything below rests on)

Live screens: ui-v2 (mounted tabs in App.tsx:2311-2364) + chrome-ext (/api/health, /api/senses only).
Condemned screens: ui/desk.html (rejected 2026-08-25, "do not invest") and ui/toolb.html+toolb.js
(scored 18/40 on 2026-09-03; Mary: "create a new ui and will remove everything else").
Both are still served, and start-v2.bat:97 + server.py:3248 (`/` -> 302 /desk.html) still open
desk.html on every start. That redirect is the only thing keeping most of this scope "live".

| desk object | live reader | condemned-only reader |
|---|---|---|
| /api/paperdesk (trader, book, quoting, hedge) | none | desk.html:568, toolb.js:3056 |
| /api/desk (desk.decide catalog) | none | desk.html, toolb.js |
| desk.decide in the loop | desk_log `deployable` field only (server.py:640); desk_log.jsonl is read by nobody (eod_capture only copies it) | — |
| /api/surface (+ server `_rv5`, `_surface_day`) | none | desk.html, toolb.js |
| surface fit -> desk_log.log_surface | forward log (kept: product rule) | — |
| /api/drag (+ `drag_day` trace, day_state persist) | none — ui-v2 BoardTab.tsx:137 is imported (App.tsx:16) but never mounted | desk.html, toolb.js |
| drag.Board | yes: server `_expr_drag` (Validate tab) | — |
| /api/warmap | yes: WarTab.tsx:194, BoardRev3.tsx:345, frame.py | — |
| warmap `driver` key + /api/warmap `participant` | none (no hit in ui-v2, frame.py, chrome-ext) | toolb.js:2006, desk.html:1425,1442 |
| direction.read | desk_log gear/conviction (via server `_view_for`), decide, trader | — |
| chainside.Chains | yes: fuse/regime/senses/frame via `_SENSES["chain"]` | — |
| book_log | yes: the book record, /api/day/record, ux_log, frame | — |
| contract_bars | yes: live.py, trigger_log.py, squeeze_score.py, eod_capture.py | — |
| contract_pair.pick_pair | only via /api/contract when chain_rows are passed (live.py:765-766); /api/contract's only UI caller is MirrorTab.tsx:180, which App.tsx never imports | — |

Black-76 is NOT duplicated: desk/surface/trader all call gamma.py. Good.
Order path: none. quoting.py's Quote/Fill/take() is order-shaped *simulation* (dicts matched
against chain quotes); test_hedge.py:198 asserts no broker tokens. It goes with the paper desk.

## Findings (ranked, biggest cut first)

trader.py:L1-1183 + book.py:L1-290 + quoting.py:L1-142 + hedge.py:L1-363: delete the paper desk. Its only reader is /api/paperdesk -> desk.html/toolb.js (grep: zero hits in ui-v2/src, chrome-ext, frame.py, board.py, hold.py); hedge.py:21 even says "Nothing downstream reads anything here". Goes with the old UIs Mary already condemned. Also takes server.py:L72,96-99,718,969-988,3892-3914,4270-4276, gamma.py theta/theta_day L78-122 (only caller trader.py:71), and tests test_trader.py(300) test_day_trades.py(229) test_book.py(98) test_quoting.py(60) test_hedge.py(377) test_desk_numbers.py:L18-68,L161-250 (the 3 known-failing tests live here — failing tests on dead code). If she still wants its 30-session record, ask first; nothing on screen reads it. (-3,280 lines)
desk.py:L1-1575 + test_desk.py(919) + server.py:L3723-3777 (/api/desk) + L612-622,640: yagni the structure catalog. 19 structures, sizing, margin, ranking — the only live output is `decision.best` written as desk_log's `deployable` transition (server.py:640), a file nobody reads back. With the paper desk gone, regime_from_chain/lot_size_from_chain have no other caller. Her call: retire `deployable` from the forward log and the whole module goes (one-tool convergence already said "delete the decision layer"). (-2,555 lines, conditional)
trader.py.bak-before-shortstop:L1-570: delete. Gitignored (.gitignore:71 `*.bak-*`), superseded by trader.py, imported by nothing. Git is the backup. (-570 lines)
contract_pair.py:L1-270 + test_contract_pair.py(234) + live.py pair branch (~L730-770, ~40): yagni. pick_pair runs only inside /api/contract with chain_rows; that route's one UI caller, MirrorTab.tsx, is not imported anywhere in the current ui-v2 tree. board/hold call build_contract with an explicit strike and no chain_rows, so they never reach it. Confirm Mirror is not coming back, then delete. (-544 lines, conditional)
warmap.py:L32,50,204,225,273,281 + driver.py(222) + test_driver.py(64) + server.py:L37,3936: yagni the driver. `driver` state key and `/api/warmap.participant` are read only by toolb.js/desk.html; worse, every live WarTab/BoardRev3 poll of /api/warmap calls participant_context(), which kicks an NSE network fetch whose result no live screen renders. (-293 lines)
server.py:L395-502 (_rv5, _surface_day, RV_* consts, _SURF_DAY_CACHE) + L3778-3827 (/api/surface) + surface.py:L151-153,L327-348,L368,L385-394 (richest/cheapest/parity_gap/`top`) + test_desk_numbers.py:L70-160: yagni the surface API. Only desk.html/toolb.js fetch /api/surface. Keep surface.read's fit + desk_log.log_surface (forward log). `_rv5` also hand-rolls sample stdev -> statistics.stdev. (-282 lines)
server.py:L3828-3891 (/api/drag) + L779-789 (drag_day ring) + L4464-4475,4500 (day_state drag_day restore/save) + L115: yagni the drag trace. drag.Board stays (Validate reads it via _expr_drag); the per-snapshot trace and its restart persistence exist only for /api/drag, whose ui-v2 reader BoardTab.tsx is unmounted "rollback" code. (-89 lines)
desk_log.py:L1-62,L146-167: shrink. 45 lines of code under 90 lines of docstring; diff_transitions is `[(f, prev.get(f), curr.get(f)) for f in FIELDS if prev.get(f) != curr.get(f)]`, and its `fields` param is never passed (server.py:652). Keep the log and the baseline marker; cut the essay. (-45 lines)
direction.py:L79-89,L132-133,L168-169,L226-233 + test_direction.py:L85-89,L115-122: delete `sided_frac`/MIN_SIDED (never passed: the only call is server.py:4210 `read(chain, v.gear)`) and `describe()` (only test_direction.py:119 calls it; desk.direction_line is the one used). (-35 lines)
chainside.py:L68-76,L100-101,L327-337: delete ChainRead.drain_rank_ce/drain_rank_pe/fuel_hist_restored. Zero readers in py, ui-v2, chrome-ext, old ui; fuel_hist_restored duplicates the note at L350. (-18 lines)
drag.py:L170-172,L185-190 vs warmap.py:L153-155,L255-259 vs trader.py:L157-163: shrink. SEED_OPEN_S/SEED_OPEN_M/SEED_WAIT_S copied verbatim into both boards; three HH:MM:SS->seconds parsers. One constant set, one parser. (-10 lines)
surface.py:L131,L379 + server.py:L615: shrink. Fit stores skew as fit(-x)-fit(+x), then read() and server both invert it back to `b = -skew/(2*SKEW_X)`. Store `b` on Fit. (-3 lines)

## If Mary keeps the paper desk / catalog anyway (not counted in net — subsumed above)

trader.py:L900-905: delete `closed_today` — L916-919 says it is truncated by a restart and superseded by `day_trades`. (-6)
trader.py:L179-223,L244-248,L966-985: delete the pre-2026-08-26 why-join (`why_by`, `_why_from_decisions`, `why_missing`). `_day_from_log` only serves the latest day in the log, which is always post-08-26 now. (-40)
trader.py:L110-133: stdlib-dup of desk_log.py:L74-100 (`MARKET_OPEN/CLOSE`, `market_hours`, `_append` byte-identical; sequence.py:53-72 is a third copy). Import one. (-20)
trader.py:L563-565 vs L1140-1142: theta-sum written twice; hedge.py:L284-314 gap_exposure restates book.py:L249-253 stress math and GAP_MOVE_EM restates book.STRESS_MOVE_EM. (-12)
hedge.py:L103-107,L128: `_round_half_up` + abs() -> `lots = int(abs(residual) + 0.5)`. (-5)
desk.py:L132-134: delete COST_NOTE — referenced nowhere (STATUTORY_PCT and _IF_CHARGED are deliberate per rule 8 and stay). (-3)
desk.py:L201-216: stdlib `g = math.gcd(*vals)` for the hand loop; better, native: upstox_instruments.lot_tick() already reads lot_size from the instrument master, making the GCD guess + LOT_SIZE table (L161-179) a second and third derivation (ladder.py:269 is a fourth). (-5 to -30)
desk.py:L1071-1084,L1467-1468,L1502-1503: yagni `_UNSUPPORTED` — six permanently-BLOCKED placeholder rows emitted on every decide call. (-18)
desk.py:L1060-1068,L1484-1501: yagni `_SIBLINGS` — synthesized mirror-image BLOCKED rows. (-26)
contract_pair.py:L144-149: `_finite` is contract_bars.py:L100-105 `_num` verbatim (7 copies repo-wide). L159,L183 `row.get("k", row.get("strike"))`: docstring L27-28 admits the feed only sends `k`. L170-192 + L239-254 `_atm_proxy` and the no-ATM branch: both callers pass atm (server.py:3432, live.py:762). L223-225,L249,L260 `sorted(...)[0]` -> `min(...)`. Docstring L1-137 for 73 lines of code; the "why it changed" history belongs in the spec. (-150)

## Lean already

book_log.py — lean. contract_bars.py — lean (one `_num` copy of seven, one IST copy of seven repo-wide; not worth a module). quoting.py — lean for what it is (dies with the paper desk). chainside.py and warmap.py — lean apart from the items above; the heavy comments are incident receipts the house keeps on purpose.

net: -4,630 lines possible on her standing decision to remove desk.html/toolb.html; -7,730 if she also retires desk_log's `deployable` field and confirms the Mirror tab is not coming back.


---

## Appendix E-plumbing

# E: data plumbing, over-engineering review (ponytail)

Scope: live.py, chain_live.py, chain_metrics.py, chain_backfill.py, upstox_adapter.py, upstox_auth.py,
upstox_chain.py, upstox_feed.py, upstox_instruments.py, upstox_proto.py, upstox_rest.py, dhan_fetch.py,
instruments.py, day_state.py, daylog.py, eod_capture.py, depth_pull.py, record_read.py, plus the tests that
import them. Read-only. Nothing was run.

## Headline: the Dhan "fallback" is not a fallback

CLAUDE.md rule 1 calls the Dhan code "a documented fallback, not the live path". The tree says otherwise.

- **The default broker is the dead one.** `chain_live._broker()` returns `os.environ.get("TAPEMAP_BROKER", "dhan")` (chain_live.py:L150). The Data API lapsed 2026-08-05, eight weeks ago. `start.bat` still exists and starts the server with no `TAPEMAP_BROKER`, which puts it on Dhan. It still tells her to "copy your fresh Dhan token and click the TOKEN button". `start-v2.bat:L13-20` and `L56-78` spend about 25 lines guarding against this default. `test_broker_switch.py` (55 lines) asserts the dead default: `test_setting_nothing_keeps_dhan`.
- **The Upstox live path still depends on Dhan code.**
  - `live.py:L27` has a top-level `from dhan_fetch import _intraday_body, _one_session`, and `dhan_fetch.py:L18` has a top-level `from dhanhq import DhanContext, dhanhq`. So the live Upstox server cannot import `live` without the Dhan SDK installed.
  - `live.build_session` (L1172) calls `_nearest_opt_expiry` unconditionally. That function (L310) scans `instruments._load_scrip()`, which is Dhan's 37 MB scrip master.
  - `server.refresh_one` (server.py:4714-4716) calls `instruments.resolve_dynamic` on every index, for a `fut_id` that the Upstox branch throws away (`_upstox_bars` re-resolves the future itself, live.py:L163-169).
  - `upstox_instruments.option_expiry` and `fut_key` already answer both questions from the Upstox dump, which is already cached.
- **Most of the contract-route tests exercise the dead branch.** `test_contract_route.py` has four fixtures (L286-293, L355-362, L462-467, L539-544) that stub `chain_live.read_token/token_status/_client/_with_deadline/resolve_expiry`. That only runs because the default broker is Dhan. The live branch is covered separately in `test_contract_upstox.py`.

Verdict: delete it. If Dhan ever comes back, git has it. The CLAUDE.md caveat is the operator's call to lift, and the cut is laid out below so she can.

## Findings, ranked biggest cut first

- `dhan_fetch.py:L1-102,L212-372`: **delete**. This is the July research CLI: `resolve`, `validate`, `fetch_day`, `client`, `rest_intraday`, `resolve_chain_ids`, `_series`, `_dup_times`, `chain`, `__main__`. It hardcodes `FUT_ID="61093"` and `CHAIN_EXPIRY="2026-07-21"`. It writes `data/chain_<day>.json` for `gex_run.py`, which no longer exists: `ls gex_run.py backfill.py` returns "No such file". Keep `_one_session` (L157-209) because the Upstox `_leg_series` uses it, and move it into `live.py` or `contract_bars.py`. That also drops the top-level `dhanhq` import from the live path. (-320 lines)
- `test_dhan_fetch.py:L1-193`: **delete**. It tests the `chain()` writer for the dead `gex_run` consumer and the Dhan `toDate` body. Move the two `_one_session` slice tests with the function. (-170 lines)
- `live.py:L66-82,L109-142,L179-208,L211-255,L292-319,L703-857,L352,L1174,L1176`: **yagni**, the Dhan branches of the live module. The pieces:
  - `_token` (the Upstox branch returns "", and the `tok` is then threaded through five functions and ignored)
  - `_throttle`, which duplicates `upstox_rest._throttle`
  - `_upstox`/`_broker_name`
  - the POST half of `_intraday`, including `fetch_bytes` and `INTRADAY_URL`
  - the scrip-master half of `_atm_ids`, including `_ids_cache`
  - `_nearest_opt_expiry`, which becomes `upstox_instruments.option_expiry(sym)`
  - the four `on_upstox` if/else forks in `build_contract`
  - three `time.sleep(0.22)` "Dhan pacing" sleeps stacked on top of upstox_rest's own `MIN_GAP`
  - `_upstox_bars`' FUTIDX/`name` special case, which exists only because `cfg["fut_id"]` is a Dhan id

  (-215 lines)
- `chain_live.py:L68-92,L95-130,L133-162,L189-206,L408-409,L509-547,L606-613`: **yagni**, the Dhan half of the poller:
  - `read_token`/`token_status`, a hand-rolled JWT exp decode
  - `_with_deadline`, a thread-abandoning deadline wrapper whose only real targets are the Dhan SDK calls here and in live.py
  - `_client`
  - `_broker`/`_upstox_source`, which becomes a plain `from upstox_chain import UpstoxChainSource`
  - `_inner`/`resolve_expiry`
  - the Dhan branches of `_run_live` and the Dhan gate in `_kick_backfill`

  Keep `is_auth_error`, mock mode, warm start, and restored-publish. Those are product. (-145 lines)
- `instruments.py:L1-27,L43-123,L134-145`: **delete**, the Dhan scrip master machinery: the `fetch_bytes` wall-clock reader, `_cache_fresh`, the three-deep `_load_scrip` cache, `resolve_futures_id`, `resolve_dynamic` and the `COL_*` constants. What survives is `INSTRUMENTS` (`under_sym`/`step`/`window`), `get` and `_prev_trading_day`. `under_id`/`under_seg`/`fut_seg`/`chain_seg` are Dhan-only config. `chain_seg` is documented at L10-11 as unused even by Dhan. (-95 lines)
- `test_live_cache.py:L1-110`: **delete**. It covers the Dhan `_atm_ids` cache, `_cache_fresh` and `_nearest_opt_expiry`, all on scrip-master rows. Keep `test_floor_pivots_*` and `test_opt_pivots_*`. (-110 lines)
- `upstox_adapter.py:L218-274` + `chain_live.py:L216-273`: **shrink**. This is a double translation kept for one broker. `side_payload`/`chain_payload` rebuild Dhan's wire shape: `last_price`, `implied_volatility`, `top_bid_price`, `previous_oi`, and `f"{float(strike):.6f}"` string keys. The only reason is so that `chain_live._side`/`normalize` can parse it straight back into `{ltp, oi, oi_chg, iv, ...}`, including the Dhan percent-to-fraction IV guard that Upstox never needs (`test_iv_stays_a_fraction`). With Dhan gone, emit snapshot rows directly in one function. (-40 lines)
- `test_upstox_only.py:L114-208`, `test_contract_upstox.py:L121-137,L320-357`, `test_broker_switch.py:L1-55`, `test_instruments.py:L1-31`, `test_chain_deadline.py:L1-46`, `test_chain_backfill.py:L213-224`, `test_chainside_seed.py:L60-65`: **delete**. These are tests of the switch, the Dhan token file, the `/api/token` Dhan refusal ordering, the "health says dhan" default, the `no_dhan` tripwire fixture, `resolve_futures_id`, `_with_deadline`, and "doesn't backfill on Dhan". None of them has anything to guard once the branch is gone. (-230 lines)
- `test_contract_route.py:L286-293,L355-362,L462-467,L539-544`: **shrink**. Swap the four Dhan stub blocks for the `upstox` fixture pattern already in test_contract_upstox. This also makes the route's main tests exercise the path she actually runs. (-20 lines)
- `upstox_rest.py:L58-116`: **shrink**. `intraday`, `historical` and `daily_range` are the same three lines each: build a URL, then `try _get / except HTTPError 404 -> [] / raise`, then unwrap `data.candles`. Replace them with one `_candles(path, tok)` and three one-line callers. (-14 lines)
- `upstox_instruments.py:L179-213,L280-287`: **shrink**. The "nearest future" sort is written three times, in `fut_key`, `lot_tick` and `resolve`. `resolve` also re-implements `_near_opts` inline (L282-287), and `_near_opts` exists, per its own docstring, so that there is ONE answer. Use one `_near_fut(rows)` and call `_near_opts` from `resolve`. (-12 lines)
- `upstox_proto.py:L55-59,L24` + `upstox_adapter.py:L119-120,L144-146` + `upstox_feed.py:L66-70,L76-79`: **yagni**, the `option_greeks` mode. Production only ever subscribes `full`: `UpstoxFeed(keys, token=tok)` at upstox_chain.py:L81 is the only constructor call, and no caller passes `mode=` or `method=`. Even so, `GREEK_FEED`, the `firstLevelWithGreeks` and `firstDepth` branches, and the `mode`/`method` params all remain. `TYPE_NAME` is read only by a test. The adapter and feed tests default to `mode="greeks"` (test_upstox_adapter.py:L28, test_upstox_feed.py:L54-64), so the main fixtures test the shape that is never subscribed. Rebase the fixtures on `fullFeed.marketFF`. (-13 lines)
- `upstox_auth.py:L180-197`: **yagni, unverified**. `ask_code` is the paste-the-URL fallback for a non-localhost `redirect_uri`. It is dead if her app is registered on localhost, as the docstring recommends. I did not read `.upstox_app.json` because it holds secrets, so check before cutting. (-18 lines)
- `live.py:L1120-1128`: **delete**. `build_payload` is a one-caller wrapper. Its docstring says it serves "`python live.py`, the tests", but grep finds no test calling it, only `live.__main__` (L1245). Inline `derive_payload(build_session(cfg))` there. (-9 lines)
- `upstox_auth.py:L72-73`, `upstox_feed.py:L49-50`, `upstox_rest.py:L34-35`: **shrink**. The Cloudflare `UA` string is pasted three times with the same comment, a fourth time in start-v2.bat, and a fifth in driver.py. Define it once in `upstox_rest` and import it. (-8 lines)
- `daylog.py:L47-52,L73-75`: **stdlib**. Replace the hand-rolled chunked `_digest` with `hashlib.file_digest(fh, "sha256").hexdigest()` (Python 3.11+, and the box runs 3.13). Equal sha256 already implies equal length, so the byte count is redundant. Replace the gzip copy loop with `shutil.copyfileobj(fi, fo)`. (-7 lines)
- `chain_backfill.py:L82,L107,L131,L174,L189`: **delete**:
  - the unreachable `return {}, None, {}` after the retry loop
  - `from datetime import datetime` imported locally in two functions for no reason
  - the duplicated `keys_of` default lambda in `leg_grid` and `minute_grid`

  (-5 lines)
- `chain_live.py:L216-221` vs `upstox_adapter.py:L100-106`: **shrink**. There are two `_num` helpers. The adapter's version also rejects NaN. Keep one. (-3 lines)
- `live.py:L32`, `chain_live.py:L28`, `instruments.py:L25`: **shrink**. `IST` is defined again in each file. Import it from `contract_bars` as eod_capture already does. Keep the fixed offset: `zoneinfo` on Windows needs the `tzdata` package, so the fixed offset is the right call. (-2 lines)
- `live.py:L430`, `chain_backfill.py:L49`, `chain_live.py:L51-52`: **shrink**. The 15:30 session close is spelled three ways in scope and a fourth time in server.py:1221. Use one constant. (-2 lines)
- `eod_capture.py:L73-74,L188,L238`: **stdlib**. The manual read/write copy becomes `shutil.copyfile(src, tmp)`, and `datetime.fromtimestamp(time.time(), IST)` becomes `datetime.now(IST)`. (-2 lines)
- `upstox_chain.py:L47-49,L62`: **yagni**. The `token=` and `each_side=` constructor params are never passed. The only construction is `UpstoxChainSource()` at chain_live.py:L162. (-3 lines)
- `record_read.py:L17,L121`: **stdlib**. `import io` is used only for `io.open` in the demo. Plain `open` does the same. (-1 line)

## Lean, leave alone

- `upstox_proto.py`: **justified**. It is 128 lines against a protoc step, generated bindings and a `protobuf` runtime pin. The only cut is the unused option_greeks schema listed above. The "no deps" argument is weaker than its docstring implies, because `websocket-client` is already a third-party dependency. It holds anyway.
- `chain_metrics.py`: lean. It is domain math and every constant is read.
- `day_state.py`, `depth_pull.py`, `record_read.py`: lean.
- `daylog.py`, `eod_capture.py`: lean apart from the stdlib swaps above. The sha256 check before delete and the no-clobber `--force` rule are product rules (write-once logs), not bloat.
- `chain_backfill.py`: lean apart from the lines above. The backfill is tagged and never blended (anytime-start rule).
- The anytime-start plumbing: `_stick` persistence, warm start, `_restored` republish, `src:"backfill"`. It is all product, keep it.

## Outside scope, same cut (not counted)

Deleting Dhan also removes these:
- server.py's `/api/token` Dhan route (~40 lines, server.py:3185-3228)
- the broker check at server.py:4335
- `chainside.py:149-151`'s broker gate
- `start.bat` in full (a Dhan-era launcher)
- start-v2.bat's `TAPEMAP_BROKER` and verify-the-broker block (~25 lines)

net: -1,490 lines possible (~-910 production, ~-580 tests).


---

## Appendix F-hold

# F-hold — ponytail review, the hold / fold family

Scope read line by line: hold.py (892), hold_log.py (101), plan.py (187), validate.py (355), expression.py (547),
ui-v2/src/hold/* (HoldTab 646, HoldWindow 301, MarketNow 103, parts 272, store 109, hold.css 465), server.py
`_hold_*` / `_expr_*` (L1770–2921), test_hold.py, test_hold_route.py, test_plan.py, test_validate.py,
test_expression.py, test_expression_route.py (grep: no other test imports these modules).

Verdict: the Python rule modules are dense but mostly earn their lines. Almost every string in them is registered copy,
and none of it is cut here. The fat is in three places: UI duplication (two views hand-roll the same ops), a handful of
dead branches or constants, and places where `expression.py` / `_expr_press` rebuild what `validate` / `hold` already
have. No finding below changes a registered word, fact, absence kind or log field.

## Findings (ranked, biggest cut first)

1. `ui-v2/src/hold/HoldTab.tsx:L329-347` + `hold.css:L253-254`: yagni. The `Loading` skeleton (fake bars and a pulse
   keyframe) is shown for a local check whose button already says "CHECKING…". Replace it with
   `<div className="empty"><span className="label">Checking…</span></div>`. It came from the mockup
   (DESIGN-NOTES.md), not from a REVIEW fix, so it is the design's call. (-20 lines)

2. `expression.py:L141-168`: shrink. `grade()` writes the one-leg-refused branch twice, mirrored, and the count branch
   as four ifs. Collapse it: `lead, w, why = (nb-ns, f"BUY {bs}", "selling") if ref_s else (ns-nb, f"SELL {ss}", "buying")`,
   then one `<0 → led / >=2 → lead / else leans` ladder. The count branch becomes `w = BUY if lead>0 else SELL` on
   `abs(lead)`. test_H7_the_word_order_and_named_by pins all 15 outputs. (-15 lines)

3. `hold.css:L282, L294, L295-298, L305, L306-309, L316 (".fl-head .odds" part), L412+L414`: delete. These are dead
   selectors, and grep of hold/*.tsx confirms it:
   - `.fl-form` (4 rules) is never rendered;
   - `.fl-rows .rrow` (4 rules) is dead because Rows renders `.drow`;
   - `.fl-trades .tr[aria-current]` is dead because no `aria-current` is set;
   - `.fl-sec.fl-rows / .fl-sec.fl-runs` is dead because those divs are not `.fl-sec`;
   - `.fl-head .cnt .odds` is dead because the float head renders no `.odds`;
   - `.mkt-now` is declared twice; merge the two rules.

   (-12 lines)

4. `server.py:L2213-2222` + route `L4088-4089`: delete `/api/hold/side` / `_hold_side_reply`. Grep across `*.py`,
   `*.ts*`, `*.js` and `*.html` (outside docs/) finds no caller: the UI never calls it, and no test does. The side read
   ships inside `/api/hold` and `/api/hold/check`, and the side log is written by `_hold_tick`. (-12 lines)

5. `server.py:L2750-2771` (`_expr_press`): shrink.
   - Lr and Sr are `hold.read({...t0: asof+1...}, Dl["minutes"], F["pivots"], idx, late)`, which is exactly
     `expression.leg(Dl, ip, side, role, k)`. `qty` is irrelevant with no `prem`, and `upto` resolves to `asof` either
     way. Call `expression.leg` for both.
   - The since/was walk re-implements `expression.since`. Build the series back to the first missing read, call
     `since()`, and set `gap` when it was truncated with `was` None.

   (-9 lines)

6. `expression.py:L40-46` + `server.py:L2720` (`or expression.R_TEXT[c]`): delete. `R_TEXT` is unreachable, because
   `read()` sets a non-empty `why[c]` in the same branch as every code it appends (R1–R6, R4cnc), so `why_ref[c]` is
   always truthy. `R_TEXT`'s phrases are not in EXPRESSION-PREREG either (grep). (-8 lines)

7. `hold_log.py:L48-65`: shrink. `seen()` hand-parses the same file `read()` parses. Replace it with
   `s = {key(kind, r) for r in read(kind, day) if isinstance(r, dict)}` and keep the day-eviction loop. One edge
   changes: a dict row with an unhashable key part would raise instead of being skipped, and no writer produces one.
   (-8 lines)

8. `server.py:L2091-2093, L2340-2343, L2459-2461, L2595-2599`: shrink. The chain px-cell unpack
   (`fronts._at(...px, k)` → `cell[0 if CE else 1]` → positive float) is written four times, in `_hold_prem`,
   `_hold_check`, `_hold_tick.px` and `_expr_day.px`. Replace them with one `_hold_px(grid, t, k, side)`. (-8 lines)

9. `HoldWindow.tsx:L140-158` + `HoldTab.tsx:L144-157`: shrink. Both views hand-roll the exit with its 10 s undo
   (`tradeOp exit` → `setUndo` → `setTimeout` → `reopen`). Put it in store.ts as `exitTrade(t, exit_t)` / `undoExit()`,
   and let each view keep only its own after-effect. (-8 lines)

10. `HoldTab.tsx:L111-133`: shrink. `imIn` and `imInCard` are the same 10-line mark-then-select. Replace them with one
    `mark(body)`; matching the returned trade on `body.idx/k/side/role` is equivalent for both. (-7 lines)

11. `HoldTab.tsx:L135-143`: shrink. The hand-rolled 30 s poll of `/api/hold/expr` duplicates `MarketNow.usePoll`
    (L331-342). Export `usePoll` and use `usePoll(`/api/hold/expr?idx=${index}`)?.setup_line`. (-7 lines)

12. `expression.py:L342-347`: shrink. The writer's "Right now" fact is `validate._right_now` verbatim: the same text
    split, the same three sentences, the same absence rule, and `Sr["entry"]["verdict"] == rows[0]["unlatched"]`.
    Replace it with `s, tx, a = validate._right_now(Sr); facts.append(["Right now", s, a, tx])`. (-6 lines)

13. `HoldTab.tsx:L47-50` + `HoldWindow.tsx:L52-55`: the same `ls()` localStorage helper appears twice. Export it once
    from store.ts. Separately, `HoldTab.tsx:L349-352` `useTick` is re-inlined in `parts.tsx` Age (L88-89) and Cutoff
    (L101-102); export one `useTick` from parts. (-6 lines)

14. `plan.py:L129-135` + `validate.py:L160-165`: shrink. The running session extreme in her direction is computed
    twice with the same loop. Replace both with one `plan.extremes(minutes, d)` and have validate take `[i]`.
    (-5 lines)

15. `plan.py:L70-76`, `expression.py:L454-458`, `expression.py:L378`: shrink. PLAN §2.1's `|Δ|R ∓ ½ΓR²` is written
    three times. Replace them with one unrounded `plan._per(dl, g, R, long)`. The callers keep their own clamp and
    rounding, so no number changes, and the registered formula has one home. (-4 lines)

16. `test_hold_route.py:L60-61/L294-295/L389-390/L465-466` and `L93-98/L485-489`; `test_expression.py:L291-292`:
    shrink.
    - The `trd = {...}` trend fixture is rebuilt four times; use one `_trd(fx)`.
    - The "a restart" 5-line block appears twice; use `_restart()`.
    - `hm_` is a wrapper for `hold.hm`.

    (-10 lines)

17. `plan.py:L31, L38-39`: delete. `RULE` is `hold.RULE_NAME` word for word, and `_strip` is `hold._strip`, with one
    caller at L98. Use hold's copies, as validate and expression already do. (-3 lines)

18. `hold.py:L620-630, L598, L343-344`: shrink.
    - `_latch`'s `"i"` is written and then stripped. Grep finds no reader, so drop it and return `latch` as `fold`.
    - `if pend: pass elif …` becomes `if not pend and not c: … elif not pend and …`.

    (-3 lines)

19. UI branches that serve an older server:
    - `HoldWindow.tsx:L56`: the `counts()` regex fallback, dead because hold.read always sends `n_for`/`n_against`.
    - `parts.tsx:L183`: WatchList's `n.watch` parse, dead because `watch_items` is always sent with `watch`.
    - `store.ts:L76`: `refresh`, which has no importer.
    - `store.ts:L10`: `Flip.from/to`, never read.
    - `parts.tsx:L75`: `QUAL['structure only']`. No Python ever emits that tag.

    (-3 lines)

20. `expression.py:L99-105, L282`: `straddle()` returns K, which the only caller discards (`_SK`); return S.
    `expression.py:L171-180` `base()` becomes `next((p for p in (...) if word.startswith(p)), word)`. (-4 lines)

21. `HoldTab.tsx:L523` (and `L518` for the sell card): delete. Each card prints σ again, although §F.1 item 4 registers
    σ once, under "Printed, not counted" (L497-498). The sell card also prints Δ in its header and again in its body.
    (-2 lines)

22. The UI re-builds copy that the server already sends:
    - `parts.tsx:L127` "the line has since trailed to X — a new trade would use it" vs `after_fold.detail`, rev 5 §B's
      registered "the line has since moved to … — detail; a re-entry is a new trade with its own line";
    - `HoldWindow.tsx:L178` vs `after_fold.collapsed`;
    - `parts.tsx:L154` / `HoldWindow.tsx:L245` vs `plan.next_wall`;
    - `parts.tsx:L141` vs `plan.stop.text`;
    - `parts.tsx:L155` "…: time is her target" vs validate's "…; time is her target".

    Render the server's strings. The TSX wording has drifted from the registered text, so the switch is hers to see.
    (-3 lines)

23. `HoldWindow.tsx:L232-233` = `HoldTab.tsx:L610-611`: the same two `Abs` literals (two-family FOLDs, two-leg). Make
    them one const each in parts. The σ, Δ and P&L sign formatting (`${z>0?'+':''}${z}σ`, `fmtD`, `−/+rs(abs)`) is
    written 4, 2 and 2 times; use `fmtD`/one `sig()`. (-3 lines)

24. `server.py:L2457` = `L2591`: the strike-step `min(b-a …) or 1.0` is computed twice. Use one `_hold_step(F)`.
    (-2 lines)

## Considered and kept (not bloat)

- `hold.heal7a`, `validate.units`, `validate.in_stratum`: grep shows test-only callers. They are the registered
  §F.1 / §3 / §4 judge definitions, pinned before the owed judge. Keep.
- `expression.leg_spot` vs `_spot`: `leg_spot` is the seam test_expression swaps to prove both readings of spot. Keep.
- `expression.NAMES` / `W_NAMES`: only tests read them (the code uses literals). This is a one-line pin, fine.
- `/api/hold` `asof=`, `rows=1` and the query-mode trade have test-only callers. They are the replay door. Keep.
- `HoldWindow` compact Stop / Next-wall (L237-249) resembles `StopBlock`/`WallBlock`, but the content differs. Merging
  would need a `compact` prop, which is more knobs, not fewer. Keep.
- The three absences, [M]/[I] tags, write-once `hold_log`, `word_1m` (registered in §E.3), LIGHT tokens and the
  Document-PiP stylesheet copy are all product rules or platform necessity.
- `hold.read` / `hold.line` are long (170 / 150 lines) because the registration is long; no safe cut without touching
  copy.
- The tests are lean. Each one pins a distinct registered clause; nothing is re-tested beyond the helper duplication
  in item 16.

net: -168 lines possible.


---

## Appendix G-ui-a

# Ponytail review G-ui-a: ui-v2 shell, trade/, one/, proto/, comps/, config

Scope read: App.tsx, data.ts, theme.ts, machine.ts, main.tsx, index.css, vite-env.d.ts, src/imports/, trade/* (15), one/* (4), proto/* (8, headers + import graph), comps/* (8, headers + references), package.json, vite.config.ts, tsconfig.json, index.html, ui-v2 CLAUDE.md/AGENTS.md/README.md.
Evidence greps were run across `ui-v2/src`. Lens: complexity only.

## Findings (ranked, biggest cut first)

1. `ui-v2/trade/{ContractChart.tsx,LegChart.tsx,LevelsOverlay.ts,Callout.tsx,Ribbon.tsx,narration.ts,zones.ts,tape.ts}` + `indicators.ts:L1-312` (except `dayPrecision`) + `TradeTab.tsx:L3-16,L364-623,L694-907,L959-1117,L1128-1137`: delete. This is a full candle chart stack: an FUT candle chart, CE/PE candle panes, a 2,094-line canvas overlay, a hover callout, a ribbon and legends. It breaks the "no charts, reads only" rule (memory no-charts-reads-only, 2026-09-24: "Never add candlestick or price-line panes"). Keep SetupCheck, ZoneRead, EngineReadPanel, FlowLine and the stat strip as the Trade tab. `vendor/candl` then has no importer left, which is for the vendor reviewer. (-4380 lines)
2. `ui-v2/comps/*.html` (8 files): delete. These are static design mockups that nothing imports. `grep comps/` finds only prose references: SetupCheck.tsx:26, START-HERE.md:416 and DEFERRED.md:354. Four of them are chart mockups, which the no-charts rule rules out. Git history keeps them. (-3323 lines)
3. `ui-v2/src/one/GlassBoard.tsx`, `glass.tsx`, `wire.ts` + `index.css:L70-360`: yagni, delete. This is the "judge it against the others" trial tab (App.tsx:L45-55), mounted since 2026-08-11. No verdict was ever recorded, and Board rev3 has since become the one-screen board. It also carries drag-to-reorder (glass.tsx:L569-696), a `dark` prop threaded through 116 call sites, and `wire.ts`, which re-polls `/api/chain` and `/api/data` even though `useLiveData` already holds both raw payloads every 5 s (data.ts:L1252-1256). If Mary keeps the board: drop the drag (-150 lines), drop `dark` and `labelInk` (a no-op that ignores `_dark`, with a duplicated docblock, glass.tsx:L12-27), and read the chain fields from `useLiveData`'s `raw` instead of wire.ts (-100 lines). (-2194 lines)
4. `ui-v2/src/proto/` (8 files) + `App.tsx:L13,L42-44,L2361-2366` + the `'Proto'` entry in `Tab`/`tabs` + the `lightweight-charts` dependency: delete. The verdict was recorded on 2026-08-05 (research-findings §6, "keep candl"). HANDOFF.md:2059 already says to delete the directory, revert the App lines and `pnpm remove lightweight-charts`. It is still mounted 7 weeks later. (-1108 lines, -1 dep)
5. `ui-v2/src/one/OneTab.tsx` + `SetupCheck.tsx:L171-179,L831-834,L941-985,L990-992` (the `compact` branch): delete. Nothing imports OneTab: grep finds only comments (App.tsx:49, SetupCheck.tsx:159/171/625). `compact` is passed only by OneTab (OneTab.tsx:259), so SetupCheck's `<details>` fold and the duplicated two-tally footer text (L975-978 = L1010-1013) are dead too. (-370 lines)
6. `ui-v2/src/App.tsx:L747-1057` (ChartTooltip + TapeTab) + `data.ts:L823-855,L979-988,L1020-1045,L546-554` (ORDER_FLOW, CHART_DATA, PRESSURE, MM_TEXT) + the `ChartPoint`/`OrderFlow`/`PressCell` types + the `recharts` dependency: delete. This is a Recharts price+VWAP chart. The prints spec (2026-09-19 §F) already calls it "a fossil… `TapeTab` is deleted". grep shows CHART_DATA, PRESSURE and ORDER_FLOW are read only here (and CHART_DATA also by barTime at L2071, which can use `tape.bars.at(-1).t`). Recharts has no other importer. (-420 lines, -1 dep)
7. `ui-v2/src/App.tsx:L79-388` (the MOCK dataset, the `Math.random` intraday walk, mock heat, mock pressure and mock map): yagni. It exists only so the first paint is not empty, and then every screen has to carry banners saying "placeholder data" (L2143-2168). HeatTab's `isDead` guard exists only to hide the invented "AMPLIFIED-UP" cells (L1391-1397). Replace with an EMPTY Dataset of about 25 lines: empty arrays, `price: 0`, and the existing banners. (-285 lines)
8. `ui-v2/src/theme.ts:L8-29,L99-100,L144-213` + `main.tsx:L4,L7-16` + `index.css:L3-21,L81-100,L139-148,L272-279,L326-342` + `TradeTab.tsx:L730-743` (the LIGHT/DARK toggle) + App `mode === 'light'` branches (L502-540, L752-767, L782/L885, L1388/L1504) + the `Record<Mode,…>` tables in LevelsOverlay: delete the dark palette, the mode context and the toggle. The operator uses LIGHT only (memory light-mode-only). `export const pal = TL` plus a direct import replaces `ModeProvider`, `useMode`, `palette(mode)` and `usePalette` (30 call sites). About 25 comments of the form "dark renders byte-identically" go with it. (-250 lines outside the files already deleted)
9. Changelog prose in comments in the files that survive (App.tsx, data.ts, SetupCheck.tsx, footprint.ts, theme.ts, flow.tsx): shrink. About 24% of the scoped TS is comments (3,093 of 12,889 lines), mostly dated history: "until 2026-08-07…", "measured…", "was X". Examples are App.tsx:L42-76 (a tab essay that still talks about "the nine that already exist" and OneTab) and TradeTab:L587-610 (24 lines explaining a `void node`). Keep the rule comments and let git hold the history. (-500 lines)
10. `ui-v2/CLAUDE.md`, `ui-v2/AGENTS.md`, `ui-v2/src/imports/pasted_text/tapemap-brief.md`: delete. They are Figma Make boilerplate and wrong ("dev server always running on $PORT 8443", a `.mise.toml` that does not exist). The brief is an unreferenced Figma import artifact (grep `pasted_text`: 0 hits). README.md is stale too (Recharts, "components unchanged", mock fallback), so trim it to the run steps. The package name `figma-make-app` is a leftover. (-136 lines)
11. `ui-v2/src/App.tsx:L569-656,L736-738,L2150-2156` (TokenCapture, Dhan): yagni. Dhan's Data API lapsed on 2026-08-05 (CLAUDE.md rule 1). The GlanceBar still renders the button on Upstox, where server.py refuses the write anyway (App.tsx:L2150-2155 says so). (-95 lines)
12. `ui-v2/src/data.ts:L505-536,L1123-1180` (the `Dataset` column-of-records vs `PerIndex` row transpose): shrink. `Dataset = Record<IndexKey, PerIndex>` removes `perFromFallback` and cuts `assemble` down to the highlight line. Consumers read `data[idx].map` instead of `data.MAP[idx]`. (-55 lines)
13. `ui-v2/src/trade/{flow.tsx:L32-61,footprint.ts:L69-104}` + `App.tsx:L1556-1578` (+ tape.ts/wire.ts if they survive): stdlib. Six hand-rolled `alive`/`setInterval`/`clearInterval` fetch loops sit in this scope, with about 15 more app-wide. One `usePoll(url, ms, hiddenGuard)` of about 15 lines replaces them. (-40 lines in scope)
14. `ui-v2/src/App.tsx:L1092-1095,L1847-1855,L478-492` + `data.ts:L767-771`: delete. These are the direction chip, the MAX PAIN / GEX / PCR / SQUEEZE verdict chips and the ChainTab verdict notes. Mary accepted this deletion on 2026-09-18 and parked it (docs/superpowers/plans/2026-09-18-ui-v2-doctrine-deletions.md). (-50 lines)
15. `ui-v2/src/data.ts:L1405-1461`: shrink. The `rotation` block re-implements `alignPerBar` inline, and the confirm-normalising map is written out twice (structures L1420-1427, rotation L1452-1460). Use `alignPerBar` plus one `normConfirm()`. (-25 lines)
16. Lakh/crore formatters `App.tsx:L396,L404,L1532`, `ZoneRead.tsx:L40-46` (`crl`), `indicators.ts:L23-29` (`lakh`), `GlassBoard.tsx:L66-93`, `narration.ts:L73-80` = `Callout.tsx:L97-104` (the same function twice) and `TradeTab.tsx:L717`: stdlib. `new Intl.NumberFormat('en-IN', {notation:'compact', maximumFractionDigits:2, signDisplay})` already prints K/L/Cr and the sign. (-25 lines after the deletions above)
17. `ui-v2/src/trade/TradeTab.tsx:L171-186`: delete. `verdictColor` has zero callers (grep: its definition is the only hit), and its `VERDICT_CLS` is a hand copy of zones.ts:L31-38. (-16 lines)
18. `ui-v2/src/trade/ZoneRead.tsx:L192-207`: delete. The "Flow" group renders the same CALL/PUT/DIFF/PCR/Δ/brk row that `FlowLine` (TradeTab.tsx:L997) already prints on the same screen. (-16 lines)
19. `ui-v2/src/trade/SetupCheck.tsx:L254-259,L601-603,L739,L906`: shrink. The side pick, the state word and the "stop chhua / VWAP chhua" strings are re-typed copies of `machine.ts` `liveMachine`/`machineWord`/`lockNote`. machine.ts:L31 even says "SetupCheck's rule verbatim". Import them. (-12 lines)
20. `ui-v2/vite.config.ts:L4,L9-13,L17` + `tsconfig.json:L10-13,L19` + devDeps `@types/node`, `tailwindcss`, `@tailwindcss/vite`, `oxfmt` + `index.css:L1`: delete.
    - The `@/` alias has zero importers (grep `from '@/'`: 0), and dropping it takes `path` and `@types/node` with it.
    - Tailwind is imported, but not one utility class is used (grep for flex/p-/text-/bg- and similar: 0, the only hits are hold.css's own `deep-grid`/`mkt-grid`). Only its preflight is live.
    - `server.host` duplicates the `--host 0.0.0.0` in the `dev` script.
    - oxfmt has no config and the code is not formatted by it.

    (-12 lines, -4 deps)
21. `ui-v2/src/one/glass.tsx:L151-163,L651`: delete. `Figure` has no importer, and `persist` is returned but never destructured (GlassBoard.tsx:862). This goes anyway if #3 lands. (-15 lines)
22. `ui-v2/src/App.tsx:L402` `wash` + `glass.tsx:L243-247` `wash` + `LevelsOverlay.ts:L307` `withAlpha` + `theme.ts:L90-93` `rgbOf`: native. That is four hex-to-rgba helpers. CSS `color-mix(in srgb, <token> N%, transparent)` does this inline. (-10 lines in survivors)
23. `ui-v2/src/App.tsx:L2004-2005`, `L1207/L1217`, `TradeTab.tsx:L376-420`: shrink. The pattern `useState(() => localStorage…)` + setter + `setItem` appears five times. Replace with one `usePersisted(key, init)`. (-8 lines in survivors)
24. `ui-v2/src/trade/TradeTab.tsx:L568-623`: native. It uses a `useLayoutEffect` + a `ResizeObserver` + a resize listener + state to compute `window.innerHeight - 12` (its own comment admits "a pure function of the window"). `height: 'max(320px, calc(100vh - 12px))'` does the same. This is moot if #1 lands. (-55 lines, not counted)
25. `ui-v2/src/App.tsx:L1211,L1235-1236,L1241-1244`: native. The EventsTab `hovered` state only paints a hover background and shows the tag. A CSS class with `:hover` replaces the state and both handlers. (-8 lines)
26. `ui-v2/src/App.tsx:L692-696`: delete. `lastUpdated` is printed twice, in the GlanceBar and at the right of the tab bar (L2239-2241). Keep one. (-4 lines)
27. Leftovers across files: delete or shrink.
    - `data.ts:L747,L772`: `breadth` is assigned and then only `void`ed.
    - `data.ts:L1127-1128`: `void highlight` should be a rest destructure.
    - `App.tsx:L77/L2018`: `Tab` duplicates the `tabs` array. Use `as const` + `typeof`.
    - `['NIFTY','BANKNIFTY','SENSEX']` appears three times (data.ts:520, App.tsx:1390, TradeTab.tsx:118). Export `KEYS` once.
    - `Ribbon.tsx:L16,L63,L72`: `onScrub` is never passed.

    (-10 lines)
28. `ui-v2/src/App.tsx:L16-18`: delete. `BoardTab` is imported but never rendered; only `BoardRev3` is mounted at L2346. The "one-line rollback" is `git revert`. BoardTab.tsx itself belongs to the board reviewer. (-3 lines)

Lean already: `machine.ts`, `hinglish.ts` (a data table), `ZoneRead.tsx` apart from #18, `footprint.ts` `lookUnder`, `index.html`, `main.tsx` apart from #8.

## Notes (not counted)
- If Mary keeps the Trade chart (#1), findings #24, #16 (narration/Callout copy) and #27 (Ribbon) still apply inside it, and the net drops to about -8.9k.
- Product rule drift, not bloat: index.css uses `'Inter'` and `.mono` uses `'Roboto Mono'`, `theme.MONO` is a `ui-monospace` stack, and `LevelsOverlay.MONO_STACK` is a third one. None of these is Barlow or IBM Plex Mono, and no font is loaded in index.html. One CSS var would replace all three stacks.
- The Heat tab, Map tab, ChainTab ladder, OI Flow table, AnswerBand "Changes if" row and MachineStrip are reads and stay; they are fine apart from the items above.

net: -13300 lines possible (about 10k src + 3.3k comps HTML), and -6 dependencies (recharts, lightweight-charts, tailwindcss, @tailwindcss/vite, @types/node, oxfmt).


---

## Appendix H-ui-b-legacy

# Ponytail review H: ui-v2 tabs (board/signals/war/mirror/flow/vpin), vendor/, old ui/, chrome-ext/

Read-only. Complexity lens only. Every "dead" claim below has grep evidence.

## Evidence

- **vendor importers** (`grep -rn "vendor/" ui-v2/src` outside vendor): only `trade/ContractChart.tsx:2-3`, `trade/LegChart.tsx:12-13`, `trade/LevelsOverlay.ts:4-5` (types), `trade/indicators.ts:4-5` (types), `proto/ProtoDraw.tsx:21-23`. Nothing imports `vendor/candl/index.ts`.
- **Engine features in use**: `createChartEngine(host, { ..., chartType: 'candles' })` (ContractChart.tsx:151). Calls made: setData, updateLast, setIndicators, setSettings, setTheme, setReplayCursor, resize, destroy. No drawing tool, no renko/kagi/P&F. The engine still pulls in the whole drawing registry (`chart/engine.ts:8-17` imports `../drawings`, which imports all 12 tool files through `drawings/registry.ts`).
- **Unreachable vendor files** (no import path from engine.ts or app code): `index.ts`, `indicators/*` except `types.ts`, `lab/*` (6 files), `alerts/notify.ts`, `alerts/tunes.ts`, `components/format.ts`, `data/types.ts` = 2,224 lines.
- **Product rule**: memory `no-charts-reads-only` (2026-09-24): "Never add candlestick or price-line panes to TapeMap screens." The only live candl consumer is the Trade tab's candle panes (ContractChart, LegChart). `lightweight-charts` is already in package.json, used only by the Proto spike, which App.tsx:42-44 calls "throwaway ... gets deleted with its directory once the verdict is recorded."
- **Tabs mounted** (App.tsx:2311-2366): Glass, Heat, Trade, Tape, Board→`BoardRev3`, Flow, VPIN, Chain, OI Flow, War, Events, Validate, Map, Signals, Proto. `BoardTab` is imported (App.tsx:16) and rendered nowhere. `MirrorTab` has zero importers (`grep -rn MirrorTab` hits only its own `export default` at MirrorTab.tsx:426).
- **Old ui/ routing**: `server.py:2934` serves `ui/` as static (`directory=str(ROOT / "ui")`). `server.py:3240-3252` redirects `/` to `/desk.html`. `start-v2.bat:97` opens `http://127.0.0.1:8765/desk.html` on every launch. `test_senses_api.py:257` asserts that redirect. No page in ui/ links to another (grep for `desk.html|toolb.html|console.html|index.html` finds only comments). ui-v2 links to none of them. Script deps: desk.html and console.html load `theme.css` + `fmt.js`; index.html loads `style.css` + `app.js`; toolb.html loads `toolb.css` + `toolb.js` + `tapemap.ico`.
- **API endpoints consumed only by old UIs**: `/api/desk`, `/api/surface`, `/api/paperdesk` (desk.html, toolb.js), `/api/gex` (app.js). This is a pointer for the backend reviewer.
- **chrome-ext/** is the **Kite** panel, not the GoCharting extension. The GoCharting one is `Go charting\orderflow-desk`, a separate repo (context/HANDOFF.md:426). chrome-ext/README.md:3: "SUPERSEDED (2026-08-15) ... then this folder goes. Do not add features here." context/HANDOFF.md:1252: stays "until the hybrid survives a live session". Six weeks of live sessions have passed since. No code references it (grep over *.py/*.ts/*.js/*.bat/*.json: only graphify caches).
- **Tailwind**: `index.css:1 @import 'tailwindcss'`, but a grep for utility classes across ui-v2/src finds zero. Every "flex/grid/hidden" match is an inline-style value or a custom class. Out of my scope; pointer only.

## Findings (ranked, biggest cut first)

ui-v2/src/vendor/candl/ (58 files): delete. It is 14,075 lines of vendored canvas-chart library whose only live job is drawing candlestick panes in the Trade tab (ContractChart, LegChart). The 2026-09-24 rule forbids those panes. Delete candl together with those panes and the Proto spike. If Trade's candles get an explicit rule exception, switch to `lightweight-charts`, which is already an npm dependency; the Proto spike was built to decide exactly that. Even with a do-nothing keep, 2,224 lines are unreachable (lab/, indicators impls, alerts/notify+tunes, components/format, data/types, index.ts), and 6,897 lines of drawing tools plus 459 of chartTransforms ship for a `chartType: 'candles'` that uses none of them. (-14075 lines)
ui/toolb.html + ui/toolb.js + ui/toolb.css (+ ui/tapemap.ico): delete. Rejected 2026-09-03 (18/40; Mary: "create a new ui and will remove everything else"). Nothing links or launches it. Its one idea worth keeping, `gateState`, is already ported to `gate.py:2`. (-4433 lines)
ui/index.html + ui/app.js + ui/style.css: delete. This is v1 "TapeMap V2 Replay Dashboard" with a Dhan TOKEN button (index.html:31), dark colours hardcoded (app.js:3-27), reachable only by typing its name (server.py:3244 comment). Nothing links it. The backend reviewer can then drop `live.py`'s kept-for-app.js `rotation` key (test_band_rotation_run.py:499 "v1's ui/app.js still reads it") and `/api/gex`. (-3042 lines)
ui/desk.html: delete. Rejected 2026-08-25 ("do not invest"), yet still auto-opened by `start-v2.bat:97` and the `/` redirect at `server.py:3246-3249` (pinned by test_senses_api.py:257). Delete it, and point both at ui-v2 on 5173 (or just remove the line and the redirect). The backend reviewer can then drop `/api/desk`, `/api/surface` and `/api/paperdesk` if no one else reads them. (-1863 lines)
ui-v2/src/mirror/MirrorTab.tsx:L1-585: delete. It has zero importers, was unhooked 2026-09-24 under the no-charts rule, and it is a candle chart. Its "mirror read in words" already ships in BoardRev3's `Mirror` (L707-752). (-585 lines)
ui-v2/src/board/BoardTab.tsx:L1-527 + App.tsx:L16-18: delete. It is imported and never rendered; the Board tab mounts `BoardRev3` (App.tsx:2346). "Stays importable as the one-line rollback" is what git is for. (-530 lines)
chrome-ext/ (manifest.json, background.js, content.js, panel.css, README.md): delete. It is the superseded Kite panel, not the GoCharting extension. It carries its own SUPERSEDED banner from 2026-08-15, and nothing in code references it. (-469 lines)
ui-v2/src/flow/FlowTab.tsx:L183-227,L329-353: yagni. The tab is a price-line pane: a price polyline, price gridlines and a price domain, built 09-18 and forbidden by the 09-24 rule. With price gone, events have no y-axis, so the tab becomes a time-ordered list of footprint events (time · kind · price · level) plus the machine-state runs. Rewrite it as that list; the SVG geometry, the `Mark` shape set and the legend go. (-300 lines)
ui-v2/src/signals/SignalsTab.tsx:L519-580,L650-686/L774-821,L283-299: shrink. The four copy-pasted `<Section>` blocks become one array `.map` (-40). The header row duplicated between `Row` and `ArmRow` becomes one `RowHead`; the bodies stay separate, which respects the file's own "an arm is not a trade" argument (-25). Field-by-field coalescing for "a backend older than 2026-08-12" goes, because the server restarts every day (-12). (-77 lines)
ui-v2/src/{signals/SignalsTab.tsx:L260-281, war/WarTab.tsx:L177-212, flow/FlowTab.tsx:L146-170, vpin/VpinTab.tsx:L101-113}: shrink. Four hand-rolled `alive/load/setInterval/document.hidden` poll loops re-implement `usePoll` in board/BoardRev3.tsx:L124-149; export it and use it (-60). `wash` is defined 6 times (App:402, Flow:59, Signals:229, War:72, Mirror:22, Vpin:93); `hhmm` 5 times, `mins` 3 times, and 09:15/15:30 constants 5 times. Put one copy of each in theme.ts (-20). (-80 lines)
ui/theme.css:L24-63: shrink. Dark is the `:root` default, which violates the LIGHT-only rule, and the light palette is written twice (media query plus `data-theme="light"`; the file admits "no toggle button wires this yet"). Make `:root` the light palette and delete the rest. This applies only if console.html stays. (-45 lines)
ui/fmt.js:L1-35: shrink. Once desk.html goes, console.html uses only `n()` and `esc()`; `rs/pct/shortRs/num` are dead (console redefines `num` at console.html:144). Inline the two functions into console.html and delete the file. (-30 lines)
ui/console.html:L409,L417-418: delete. The `<details>` open-state snapshot/restore is dead because `buildMainHTML` never emits `<details>`. More broadly, console.html (504 lines) is unlinked, not launched, and its `/api/senses` gear/sweep/terrain read is rendered nowhere in ui-v2 (the only mention is a comment in dead BoardTab.tsx:247). If she no longer types that URL, delete console.html + theme.css + fmt.js + stop.ico outright (-612 instead of -79). (-4 lines)
ui-v2/src/vpin/VpinTab.tsx:L179-181,L275-278,L297: delete. The price polyline and last-close label draw a price line on screen, against the rule. The sustain sentence (L158-162) already states the price move in words ("Price down 42 pts in 30m"). Keep `useTape`; it feeds that sentence. (-7 lines)

## Lean / keep (not bloat)

- board/BoardRev3.tsx: lean for its spec. The floating, draggable, dockable trend box looks like yagni but is spec'd (docs/mockups/board-chess-rev3-2026-09-24-notes.md:94, item 5). The scoped CSS string is fine. `useBoardGlance` serializes three fetches on purpose (the dev-proxy 502 note). The only cut is exporting `usePoll`.
- war/WarTab.tsx: lean. OI-over-time is an allowed OI visual. The hole/provenance handling and the three absence sentences are product rules. The only cut is the shared helpers. (The spot polyline is rule-adjacent. It is an index line on an OI map, and I did not count it.)
- vpin/VpinTab.tsx: lean apart from the price line.
- SignalsTab's three absence branches, the separate ARM rendering, the void-legacy section and the [M]/[I] tags are product rules, not bloat.

## Cross-scope pointers (not counted; other reviewers own these files)

- Tailwind is dead. `ui-v2/src/index.css:1 @import 'tailwindcss'`, `vite.config.ts` `tailwindcss()`, and package.json `tailwindcss` + `@tailwindcss/vite` have zero utility classes in use. Remove all four.
- `ui-v2/package.json` `"name": "figma-make-app"` and `ui-v2/AGENTS.md` (behind `ui-v2/CLAUDE.md`) describe a Figma Make sandbox ("dev server always running on $PORT 8443") that does not exist here. This stale boilerplate misleads every agent that loads it.
- `lightweight-charts` goes with proto/. `recharts` is used only by App.tsx; check it against the same no-charts rule.
- Backend endpoints orphaned by the ui/ deletions: `/api/desk`, `/api/surface`, `/api/paperdesk`, `/api/gex`, plus `live.py`'s legacy `rotation` key. CLAUDE.md's "Screens:" line needs updating when ui/ goes.

net: -25540 lines possible.
(Without the vendor cut, if Trade's candle panes get an explicit rule exception: -11465, plus -2224 unreachable vendor files.)


---

## Appendix I-hygiene

# I: repo hygiene: cross-cutting duplication, repo weight, docs sprawl (ponytail)

Read-only. Complexity lens only. Evidence is `git ls-files`, `grep`, `wc`. Other reviewers own
modules (A server, B tape-core, C board/oi, D desk, E plumbing, F hold, G/H ui). Where a sibling already
flagged one copy of a helper, it is marked `(overlap: X)` so the parent does not count it twice.

Scale: 1,316 tracked files. 93 root `*.py` modules, 95 root `test_*.py` files.
Docs: 6 root md (1,557 lines), 14 context/ (7,296), 289 docs/ files (docs/hold alone is 216 files, 101,607 lines).
Generated: graphify-out/ has 69 files and 84,769 lines, tracked although `.gitignore:78` ignores it.

---

## 1. Cross-cutting duplication (code)

The one ~30-line helper. Put it in `daylog.py`, which is already the stdlib-only leaf that owns
`open_text`/`exists` for the same day files:

```python
def rows(path):                      # streamed, gz-aware, torn lines skipped, OSError -> nothing
    try:
        with open_text(path) as f:
            for line in f:
                try: r = json.loads(line)
                except ValueError: continue
                if isinstance(r, dict): yield r
    except OSError: return

def append(path, rs) -> int:         # fail-soft, one open per call, "a" mode
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(json.dumps(r, default=str) + "\n" for r in rs))
        return len(rs)
    except OSError: return 0

class Once:                          # write-once by key, seeded from disk, one lock
    def __init__(self, key): self.key, self.seen, self.lock = key, {}, threading.Lock()
    def append(self, path, rs):
        with self.lock:
            if path not in self.seen:
                self.seen[path] = {self.key(r) for r in rows(path)}
            s = self.seen[path]
            new = [r for r in rs if self.key(r) not in s]
            if append(path, new): s.update(map(self.key, new))
            return len(new)
```

Findings, biggest first:

- hold_log.py:L48-101 + calls_log.py:L27-54 + tape_log.py:L52-70,L122-133 + ux_log.py:L71-74 + book_log.py:L100-128 + desk_log.py:L92-100 + sequence.py:L72-80 + trader.py:L126-133,L928-935,L987-998 + senses.py:L103-115,L186-196 + frame_log.py:L56-62 + trigger_log.py:L159-170 + server.py:L476-483,L938-952,L3112-3115,L4430-4446 + replay_dwell.py:L28-35 + score_frame.py:L89: shrink. The JSONL plumbing is written about 15 times for reads and 15 times for appends. It is one pattern: stream the lines, skip torn ones, return empty on OSError; append fail-soft with makedirs; for write-once, keep a seen-set seeded from disk under a lock. `ux_log._write_lines` is `tape_log._write_lines` verbatim minus `default=str`. `server._read_jsonl` (L4430) already exists and nobody outside server.py uses it. `hold_log` and `calls_log` are the same write-once module written twice. Replace all of them with `daylog.rows` / `daylog.append` / `daylog.Once` above; `hold_log` shrinks to `path()` + `key()`, and `calls_log` to one `Once` call. `trigger_log.read` stays, because it counts bad lines on purpose. (-200)
- server.py:L4257-4287 + conftest.py:L1-31 + about 20 `DIR`/`PATH` constants (book_log:40, calls_log:18, day_state:42, desk_log:71-72, frame_log:20, hedge:91, hold_log:26, senses:64, sequence:51, tape_log:35, trader:106, trigger_log:97, server:155/168/174, chain_live:30-31, driver:132, eod_capture:58-59): shrink. Every record module hard-codes its own `"data"` root. `_isolate_mock_writers` then re-points them one by one (it already misses `frame_log`, `calls_log`, `senses`, `trigger_log`), and conftest re-points a different subset one by one. Use one root, `daylog.DATA = os.environ.get("TAPEMAP_DATA", "data")`, joined at call time. A mock run sets one env var and conftest is one `monkeypatch.setenv`. (-45)
- board.py:L44-50 (keep `mm`/`hm`) vs breadth.py:L68-70, frame.py:L110-112, fronts.py:L193-195, watch.py:L71-73, trendbox.py:L39-40, run_score.py:L53-58, band_rotation.py:L429-440, chain_metrics.py:L453, contract_bars.py:L213; and epoch-ms to IST "HH:MM" at frame.py:L98-100, signals.py:L63-65, visit.py:L60-65, grounds.py:L56-58: shrink. There are 9 copies of "HH:MM" to minutes and 4 of ms to "HH:MM". `visit._hhmm` says a cycle forces the copy, but the cycle goes away if the helpers live in a leaf. Add a leaf `clock.py` (about 20 lines: `IST`, `mm`, `hm`, `hhmm(ms)`, `in_session`) and make `board.mm/hm` re-export it; `hold`, `plan` and `expression` already alias `board.mm`. (-55) (overlap: B flagged frame's `_hhmm`)
- desk_log.py:L74-89, sequence.py:L53-69, trader.py:L110-123: delete. There are three `market_hours` functions plus `MARKET_OPEN/CLOSE` pairs, and `chain_live.in_session` (L59) is a fourth. The docstrings of hold_log and calls_log already name `chain_live.in_session` as the gate. Keep that one, in `clock.py`. (-24) (overlap: B, D)
- test_docs_claims.py:L1-136 + CLAUDE.md:L58 + START-HERE.md:L239 + context/HANDOFF.md:L14-15,229,324: delete. The docs state the pytest count, and a 136-line test exists to keep that number true. Stop writing the count in docs and the test has nothing to guard. The other two asserts pin one sentence each in PRODUCT/HANDOFF, both of which are deleted below. (-136)
- engine.py:L91-100, fuse.py:L55-70, vpin.py:L95-109: delete two. These are three copies of `Rank`, two of them commented "copied, not imported". The stated reason is to stay free of the engine, which a leaf module satisfies. (-30) (overlap: B, C)
- band_rotation.py:L231-236, contract_bars.py:L100-105, contract_pair.py:L144-149 (`_finite`), structure.py:L213-217: delete three. "A finite float, or None. Bools are not numbers here." is copied word for word 4 times. Also chain_live.py:L216-221, fronts.py:L64-69 and upstox_adapter.py:L100-106 are 3 more float-or-None copies. Put both in the leaf. (-30) (overlap: E, 3 lines)
- backtest.py:L27, chain_live.py:L28, contract_bars.py:L68, dhan_fetch.py:L20, instruments.py:L25, live.py:L32, surface.py:L63 (`IST = timezone(...)`), plus `SESSION_END` at server.py:L1221, live.py:L430 ("server.SESSION_END_HHMM"), chain_backfill.py:L49, visit.py:L57: shrink. That is 7 IST constants and 4 "15:30" constants. Keep one of each in `clock.py`. (-10) (overlap: E)
- board.py:L533, chain_metrics.py:L363, dwell.py:L105-107, server.py:L1727, L2457, L2591 (strike step = min gap) and expression.py:L73-76 (keep `atm`) vs live.py:L92, server.py:L1728, L2463-2464 (ATM = round(s/step)*step): shrink. There are 6 strike-step inferences and 4 ATM roundings. Keep one `strike_step(ks)` and `expression.atm`. (-12)
- pools.py:L95-100: stdlib. `_median` is `statistics.median`. engine.py:L171-173 is `statistics.median_high`. board.py:L53 `sgn`, prints.py:L243 `_sign` and ux_gate.py:L24 `_sign` are three copies of the same function. (-12)
- hold.py:L367,L515,L758,L768,L786,L790,L792 + server.py:L4610: shrink. "could not check — " is spelled inline 8 times even though `board.CC` exists and hold.py:L55 imports it. expression.py:L44,174,317 and validate.py:L39 spell it without the dash, so there are two grammars for one absence. Use `CC` everywhere. (-0, one vocabulary)
- `datetime.now().strftime("%Y-%m-%d")` appears 59 times across 17 files (server.py 20, trader.py 8, live.py 8): shrink. Replace with `clock.today()`. It saves no lines, but it gives one place to look.

## 2. Repo weight (legacy and generated)

- graphify-out/ (69 files, 84,769 lines, 6.1 MB): delete from git with `git rm -r --cached graphify-out`. `.gitignore:78` already ignores it, so the rule does nothing while the files are tracked. It is a regenerable graph cache (hash-named `cache/ast/*.json`, `cost.json`), already stale against today's tree, and 62 cache files are untracked beside it. Generated output does not belong in git. (-84,769 generated)
- archive/ (25 files, 6,544 lines, 611 KB): delete. The four old HTML UIs (redesign, tapemap, tapescroll, meridian), three `variant-*.html` and eighteen `replay_*.txt` outputs of dead hypotheses. Only the July context docs reference it, and those are deleted below. Git history keeps it. (-6,544)
- .claude/proven-config.json + .claude/.proven-config-version: delete. This is ruflo tool-selection state ("ruflo.proven-config/v1", corpus hashes) and has nothing to do with this app. (-41)
- .claude/launch.json:L1-41: shrink. It has six launch configs, and three of them start a LIVE server on 8765/8767. Standing rule: "agent never starts the live server". Keep `tapemap-mock` and `tapemap-v2`. (-25)
- start.bat:L1-14: delete. The Dhan-era launcher never sets `TAPEMAP_BROKER`, so it starts on the dead Dhan source, and its text still says "copy your fresh Dhan token". CLAUDE.md calls `start-v2.bat` "THE way to start". Fix the 4 prose mentions (START-HERE, chrome-ext/README, context/mental-map, eod_capture.bat comment). (-14)
- gan-harness/ (spec.md, eval-rubric.md): delete. A 2026-07-20 design-loop brief, referenced only by July context docs. (-71)
- .gitignore:L50-80: shrink and fix. (a) `graphify-out/` (L78) is dead while the files stay tracked. (b) `.impeccable/` (L79) contradicts the L56-59 comment that says "critique snapshots stay tracked". It makes L60-62 redundant, and it leaves one critique tracked and two untracked; pick one rule. (c) `tape_desktop.png` (L80) is a one-file rule while `warmap_desktop.png` and `warmap_fixed.png` sit tracked beside it; ignore `/*.png` and delete the rule. (d) Missing entries, so `git status` is permanent noise: `data/calls/`, `data/frame/`, `data/hold/`, `data/mock/`, `data/void-*/`, `data/vpin_fast.jsonl`, and `data/trigger_log.backup-*` (the `*.bak-*` rule misses the `backup-` spelling). (e) L39 says `data/vpin_log.jsonl` "stays tracked on purpose", but it is untracked (`?? data/vpin_log.jsonl`). (-15)
- warmap_desktop.png, warmap_fixed.png (root, tracked, 348 KB, referenced nowhere) and docs/trade-tab-2026-09-18.png: delete. (-0 lines, 0.56 MB)
- data/backtest/ (556 tracked files, 2 MB): shrink. 14 newer days (`fut_2026-08-20..25`, `desk_log_2026-08-24.jsonl`, `surface_2026-08-24.jsonl`) are untracked beside the tracked ones. Pick one: commit every captured day or ignore them all. As it stands, half of one population is in git. (-0)
- Disk only, already ignored: tapemap.log.1-3 (15.7 MB), `_srv.err`, `_srv.log`, `_srv_restart*.log`, `tapemap-8765.log`, `trader.py.bak-before-shortstop` (the rewrite shipped 2026-08-25), `tape_desktop.png`, 4× `data/trigger_log.jsonl.bak-before-*`, 2× `data/trigger_log.backup-2026-09-2*-before-*dedupe.jsonl`: delete. That is 23 MB of stale safety copies and logs. The trigger_log copies are hers to drop, since the live file is her irreplaceable record. (-0 lines, 23 MB)
- Not counted here, owned by G/H: ui/ desk+toolb (about 8.7k lines), ui-v2/comps (3,323), ui-v2/AGENTS.md+CLAUDE.md (24). I agree with those deletions.
- Kept on purpose: test/fixtures (3 fixture files, not empty), tools/ (3 scripts), the `.pine` files (charting indicators, not repo weight).

## 3. Docs sprawl

Kept by the brief's rule, and verified: `docs/hold/scratch-2026-09-25/expr/` (the signed EXPRESSION-PREREG §D.0 names it as the disclosure source, and every `rules_rev*_before_run.md` is a fingerprinted anchor); `scratch-2026-09-25/rev5/` (PREREG-rev5.md:531, VALIDATE-PREREG.md:580); `docs/hold/opus/` and `docs/hold/fable/` (PREREG-merged.md:9,504,553 and hold.py:16-25 name them as the port source, including `fable/data.js`, the 22 MB frozen replay record); `EXPRESSION-PREREG-DRAFT.md` (sha256-anchored by EXPRESSION-PREREG.md:25); every signed PREREG and every REVIEW.

- docs/superpowers/plans/ (11 of 12 files, 10,489 lines): delete. These are executed task-by-task agent scripts for features that are built and live: signal-layer 3,067, upstox-tape 3,017, orderflow-levels 2,206, tape-chart phase1-3 1,272, multi-index 448, phase5 205, band-rotation 145, anytime-start 93, doctrine-deletions 36. The code cites the specs (`docs/superpowers/specs/`, kept), not the plans. Keep only `2026-09-16-operator-desk.md` (4,705), which is still unbuilt. (-10,489)
- docs/mockups/ board-chess-2026-09-24.html + -notes.md + -gen.py, board-chess-rev2-2026-09-24.html + -notes.md, war-compact-2026-09-24.html + -notes.md, gen_war_compact.py, board-2026-09-22.html: delete. These are superseded revisions: rev 3 is built, and board.py:3 and trendbox.py:3 cite only `board-chess-rev3-2026-09-24-notes.md`. They are also about 9 MB of HTML with embedded data. The rev1 generator describes itself as the reference for layers that "do not exist yet", and those now exist in board.py. The rev3 HTML (10.5 MB, 709 lines) goes the same way once she stops comparing against it. (-3,987)
- context/HANDOFF.md:L1-2137: shrink to about 150 lines. It is a 2,137-line reverse-chronological session diary. Its "STATE OF THE APP" (L84) is dated 2026-08-25, and its newest entry (L186) says to go read another file. Git log is the diary. Move §8 "decisions owed" and "Settled — no longer to be asked" (L1771) into START-HERE, then delete the rest. (-2,000)
- context/progress-tracker.md (782), project-overview.md (108), code-standards.md (76), ai-workflow-rules.md (91), architecture.md (128), mental-map.md (96), ui-context.md (149), docs/2026-07-28-product-notes.md (248): delete. All were last touched 2026-07-29/30, and they describe the July dashboard, `archive/`, `gan-harness` and `analyze.py` pipelines. Three have zero inbound references, and the rest are referenced only by each other (plus one live.py comment pointing at mental-map). (-1,678)
- docs/hold/PREREG-rev5-DRAFT.md (876) + docs/hold/VALIDATE-rev2-DRAFT.md (715): delete. These are drafts kept beside their signed texts (62 and 86 differing lines). No signed text hash-anchors them, unlike EXPRESSION's draft. REV5-VALIDATE2-REVIEW names the revisions it read (5a, 5b, 2a, 2b) by clock time, and the file in git is neither of them; git history holds every revision the review saw. (-1,591)
- docs/hold/PLAN-BUILD.md (750) + docs/hold/BUILD-BRIEF.md (95): delete. The executed build plan ("REQUIRED SUB-SKILL: …executing-plans") and the builder's brief for a window that is built, reviewed and live. BUILD-REPORT and the REVIEWs are the record. (-845)
- docs/review/fresh-screen.html (633): delete. It is the generated output of `fresh-screen-build/template.html` + `build.py`, committed beside its own generator. (-633)
- README.md (142), PRODUCT.md (144), HANDOFF-OPERATOR.md (179): delete. README says "older than START-HERE", and README.md:22 runs `band_backtest.py`, which does not exist. PRODUCT was written 2026-08-05 "for v3's design work", and v3 was superseded by the one-tool design. HANDOFF-OPERATOR is a 2026-08-20 branch handoff (`feature/operator-objects`). Their live facts are already in START-HERE and research-findings. (-465)
- docs/hold/HANDOFF-2026-09-25.md (146): delete after one merge. HANDOFF-2026-09-26 supersedes it, and the only reason START-HERE sends readers there ("the signed rules and their hashes") is duplicated in research-findings §1e-§1g. (-146)
- CLAUDE.md:L1-81 vs START-HERE.md:L1-80: shrink. The entry chain is 5 hops for "what is current": CLAUDE.md → START-HERE (verified 2026-08-22) → context/HANDOFF "STATE OF THE APP" (08-25) → HANDOFF-DESK §8g (09-15) → docs/hold/HANDOFF-2026-09-26 → HANDOFF-2026-09-25. START-HERE §0 repeats CLAUDE.md rules 1-6 and its "Running it" block, including the detached `Start-Process` line and the test count. Make CLAUDE.md the rules and START-HERE the state, and link rather than restate. (-60)
- Doctrine restated everywhere: "Dhan lapsed 2026-08-05" has 65 hits in 27 md files; anytime-start 38 hits/26 files; the no-hit-rate rule 54 hits/26 files; no-order-path 36 hits/24 files. shrink. State each rule once, in CLAUDE.md, and make every other mention a link. (-0 counted; this is the maintenance tax that let the next item happen)
- Drift that proves the sprawl cannot be maintained: CLAUDE.md:79 says `data/trigger_log.jsonl` is "deliberately NOT committed", but it is tracked (`git ls-files`, and modified right now). CLAUDE.md:62-64 describes `/toolb.html` as "pending approval", but it was rejected 2026-09-03. .gitignore:39's vpin_log claim is wrong (see §2).
- Not counted, owned by the next reader: ui-audit.md (139), CHECKLIST.md (181), logic-plain-english.md (190) and ui-v2-dashboard.md (829) are August-era and describe the ui-v2 Trade tab. Delete them if G confirms that tab is gone.

---

net: -554 lines possible in code (about -65 of it overlaps B/C/D/E), -91,479 generated/legacy (-84,769 graphify-out, -6,710 archive/.claude/start.bat/gan-harness/.gitignore), -21,894 lines of docs, plus about 23 MB of ignored disk clutter and 0.56 MB of tracked PNGs.
