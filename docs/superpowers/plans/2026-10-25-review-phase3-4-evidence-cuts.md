# Review 25 Oct, Phases 3 and 4: The Evidence and The Cuts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `docs/superpowers/specs/2026-10-25-review-fix-cut-stop-design.md`.
- **Phase 3 (§1, F12–F14), the evidence:**
  - Validate's word is logged at every press (F12, A75).
  - The record says when it is not being written, and the tradebook nudges after the close (F13, A76).
  - The voice's first line shows the premium from her entry (F14, TRADER F02).
- **Phase 4 (§2, C1–C12), the cuts Mary approved:** C1–C11 are planned. **C12 is DEFERRED: needs Mary** (see "C12, deferred" before Task 15).

**Architecture.** Logging, display and deletion only. Nothing decides anything new.
- **Server:**
  - `POST /api/validate/log`: a write-once press log.
  - `/api/health` carries `recording` and `tradebook`. A recording change writes one row through `feed_health`'s writer.
  - A confirmed tradebook import writes one marker row.
  - `voice.py` l1 gains `prem ±N%`.
  - The three dead hold routes and `/api/senses` stop being served. The broker default is upstox.
- **Faces:**
  - Validate posts its press.
  - 5173 and the Float show RECORDING NAHI and the tradebook nudge.
  - The ANSWER band becomes THE READ's row; six tabs and their components go; the dead `hold/*` and `BoardRev3` UI go.
  - The panel loses the EXPRESSION pill and folds everything but the voice under one `[detail ▸]` in a trade.

**Tech Stack:**
- Python 3.13 + pytest.
- React 19 + TypeScript 5.7 + Vite 8 (ui-v2). There is no test runner, and none is added.
- Plain JS Validate, through Phase 2's node harness `test/validate_app_harness.cjs`.
- The extension's six node suites.

## Global Constraints

- **Repos, branches.**
  - TapeMap: `C:\Users\kaam\Desktop\operator mode\tapemap`, branch `feature/operator-objects`.
  - Extension: `C:\Users\kaam\Desktop\Go charting\orderflow-desk`, branch `one-tool`.
  - Both repos have `core.autocrlf=true`. HEAD stores LF; the working copies are CRLF except where noted.
- **Phase 2 runs first, and its text is the base.** Phase 2 (`docs/superpowers/plans/2026-10-25-review-phase2-screens.md`) edits:
  - in TapeMap: `fold_live.py`, `server.py`, `ui-v2/src/pro/Float.tsx`, `pro/Desk.tsx`, `hold/hold.css`, `hold/store.ts`, `data.ts`, `ui-v2/public/validate2/app.js`, and its new `test/validate_app_harness.cjs` and `test_validate_app.py`;
  - in the extension: `src/shell/{main,panel,boot,sw,recorder}.js`, `src/engine/v2.js`, `test/{shell,panel,overlay}.mjs`.
  - Every old string below for those files is the text **as Phase 2's "with" blocks leave it**. A task that touches one says **"touches a Phase-2 file: re-verify the anchor"**.
  - **Phase 2's executor has already deviated from its plan text once** (the live `main.js:341` `away` line differs from Phase 2 Task 2's block). So before each edit to a Phase-2 file, read the lines around the anchor. Where the exact text differs, apply the same change to the text that is there. Never paste an old string blind.
- **Line endings, measured 25 Oct.** Edit only with exact-string replacements or `cut.py` (below). No reformatting, renames or whole-file writes, except the new test blocks this plan names.
  - LF: `chain_live.py`, `test_hold_route.py`, `test_receipts.py`, `test_feed_health.py`, `test_broker_switch.py`, `test_contract_upstox.py`, `ui-v2/src/data.ts`, `ui-v2/src/pro/Float.tsx`, `ui-v2/src/hold/parts.tsx`, `START-HERE.md`.
  - Mixed: `test_upstox_only.py`.
  - CRLF: every other file this plan touches.
  - After each task, `git diff --stat` in the repo(s) it touched shows only that task's lines.
- **`cut.py`, the one range-delete helper.** Executors save it in their own scratchpad, never in a repo, and run it with Git Bash's `python`. It deletes a block between two line anchors, keeping each kept line's own line ending:

```python
# cut.py FILE START STOP -- delete FILE's lines from the one that starts with START up to (not including) the first later
# line that starts with STOP ("EOF": to the end). Anchors are ASCII; write any other character as \uXXXX (e.g. \u2500 for ─).
# START must start exactly one line. Bytes in, bytes out: every kept line keeps its own line ending.
import sys

f, a, b = sys.argv[1:4]
dec = lambda s: s.encode("ascii").decode("unicode_escape").encode("utf-8")
L = open(f, "rb").read().splitlines(keepends=True)
body = [x.rstrip(b"\r\n") for x in L]
hits = [k for k, x in enumerate(body) if x.startswith(dec(a))]
assert len(hits) == 1, f"START {a!r} starts {len(hits)} lines"
i = hits[0]
j = len(L) if b == "EOF" else next((k for k in range(i + 1, len(L)) if body[k].startswith(dec(b))), None)
assert j is not None, f"STOP {b!r} not found after line {i + 1}"
open(f, "wb").write(b"".join(L[:i] + L[j:]))
print(f"{f}: deleted lines {i + 1}-{j} ({j - i})")
```

  - Usage: `python "$CUT" <file> "<START>" "<STOP>"`, where `CUT` is the scratchpad path.
  - Quote an anchor in double quotes, or in single quotes when it holds a backtick or `$`.
  - Each run prints the line range it deleted. That range must match the one the step states (±2 lines for Phase 2's shifts), or stop and read the file.
- **Deleting files.**
  - A tracked file: `git rm` (history and the tag `pre-review-2026-10-25` keep it).
  - An untracked file: the Windows Recycle Bin (Task 14). Never `rm -rf`, and never anything under `data/`.
- **Commands.**
  - **Server:** `python -m pytest -q` from the TapeMap root.
    - The baseline after Phase 2 is 1973 collected = 1971 pass, 1 skip, 1 known flaky (`test_v2feed.py::test_serve_caches_full_and_answers_delta`, A49).
    - Phase 3 adds 7: 5 tests, plus 2 leak-guard cases → **1980**.
    - Phase 4 adds 1 → **1981**.
  - **ui-v2:** `cd "/c/Users/kaam/Desktop/operator mode/tapemap/ui-v2" && ./node_modules/.bin/tsc --noEmit -p . && npx vite build`.
    - `tsc` prints nothing today, and `noUnusedLocals` is off.
    - `vite build` writes `ui-v2/dist`, which is gitignored and not served.
  - **Extension, during tasks:** `cd "/c/Users/kaam/Desktop/Go charting/orderflow-desk" && node build.mjs --out .baseline/v212-next`, then `OFD_DIST=.baseline/v212-next node test/<suite>.mjs`.
    - Never build `dist-v2` before Task 15's gate.
    - Phase 2's counts: engine 116, fit 46, shell 148, overlay 39, panel 103, decoder 21.
- **Hard limits.**
  - Never start, stop or restart the TapeMap server, nor any dev server on 5173 or 8765. Mary starts them herself.
  - A controller preview runs on its own port (e.g. `npx vite --port 5175 --strictPort` in `ui-v2`), and only for the render checks.
  - Never write under `tapemap/data/`. Tests use `tmp_path` / `monkeypatch`; conftest redirects every writer. Reading a data file to measure is allowed.
  - **No commits by implementers.** The controller commits once per phase (Tasks 6 and 15). Mary's 25 Oct 16:40 delegation is the word: "hey i am going out just fix everything i want evevyrhting fix by the time i am back you are incharge whatever you think is right do it".
  - The commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. The rollback is the tag `pre-review-2026-10-25` in both repos.
  - No new dependency and no new test framework.
  - A PreToolUse "Fact-Forcing Gate" hook may ask for facts before the first Bash call or edit of a file. State them briefly, then retry:
    - the importers;
    - the affected API;
    - the data schema;
    - the user's instruction, the delegation quoted above.
- **Timing.**
  - Server edits take effect at her next start, ui-v2 edits at once through HMR if 5173 is running, and extension edits at her Reload + F5.
  - Never edit a file the live server imports, `ui-v2/src/` or `ui-v2/public/validate2/` between 09:15 and 15:40 IST, Mon–Fri.
  - **Every task leaves the full suite green**: her next start runs whatever is in the tree.
- **Never touch.**
  - The registered rules §1i–§1q and their browser computations: VALIDATE rev 3 / 3.1 in `engine.js` (F12 only logs its output; `engine.js` is never opened for writing), the extension's FADE KILL, and READ-2's JAGAH `push` on the wire.
  - `voice.py`'s state logic (F14 changes only the l1 string), `fold.py`, `engine.py`, the zone machine, the §1d gate and `signals.py`.
  - Existing rows of any forward log, and `data/trigger_log.jsonl`.
  - The rev 5 hold loop's server functions. C8 cuts routes, not `_hold_reply` / `_hold_check` / `_expr_reply` (judged ~6 Nov).
  - Mary's launchers `start-v2.bat`, `stop.bat` and `eod_capture.bat`.
- **Copy rule.**
  - On-screen words are short, Hinglish/English, at most 6 words a cell, and never a paragraph on a face.
  - The new words are exactly:
    - `RECORDING NAHI: <which>`, where which is any of `book, chain, calls, read, GoCharting`;
    - `tradebook aaj import nahi`, linked as `import karo`;
    - `prem −47%` / `prem +9%` / `prem ?`;
    - `not served` (an API reply, not a face).
  - **Light only.** Use the existing CSS variables or palette tokens, with no new colour literals. `panel.mjs`'s LIGHT test stays green.
- **Numbers** in docs are tagged [M] measured or [I] inferred. Never a win / hit rate.

---

# PHASE 3 — THE EVIDENCE

### Task 1: Validate's press is logged once (F12, server half, A75)

**Touches a Phase-2 file (`server.py`): re-verify the anchor.**

**Files:**
- Modify: `server.py`:
  - add `VALIDATE_DIR`, `_VALIDATE_LOCK`, `_PRESS_KEY` and `_validate_press` above `def _frame_chain`;
  - add the `POST /api/validate/log` door above the PaperDesk comment in `do_POST`;
  - add `VALIDATE_DIR` to `_isolate_mock_writers`.
- Modify: `conftest.py` (`STR_PATHS`).
- Test: `test_hold_route.py` (one import, one test at the end).

**Interfaces:**
- **`POST /api/validate/log`** takes `{t, idx, K, ty, side, px, rev, word, counts, checks}`.
  - It replies `{ok: True, new: True | False}`, or `{ok: False, why}`.
  - Another site's page gets 403 `refused — a POST from another site`, the hold door's rule verbatim.
- **`server._validate_press(doc) -> dict`.**
  - It writes one row per `(t, idx, K, ty, side)` to `data/validate/press_<day>.jsonl`.
  - The day is the server's own (`_board_clock`), never the page's.
  - It writes only in market hours (`_market_hours`, THE ONE GATE).
  - The row is the press as sent, plus `day` and `at`.
- `server.VALIDATE_DIR` is redirected by conftest and by `--mock-chain`.

**Can affect:** a new file per day under `data/validate/`.

**Untouched:**
- `engine.js` and every rule;
- the hold doors;
- every other log.

- [ ] **Step 1: Write the failing test.** In `test_hold_route.py`, replace

```python
import io
import json
```

with

```python
import io
import json
import os
```

and replace

```python
    assert len(late) == 1 and (late[0]["to"], late[0]["short"]) == ("15:29", True)
```

with

```python
    assert len(late) == 1 and (late[0]["to"], late[0]["short"]) == ("15:29", True)


def test_a_validate_press_is_logged_once_and_another_sites_post_is_refused(monkeypatch):
    """25 Oct review F12 / A75 (TRADER F06): VALIDATE rev 3's word was never logged, so §1p could never be judged forward.
    POST /api/validate/log keeps each press once by (t, idx, K, ty, side) in data/validate/press_<day>.jsonl -- the word as
    Validate's engine.js sent it, never recomputed here -- on the server's own day, in market hours. Another site's page is
    refused, as at the hold door."""
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-10-26", "10:05"))
    press = {"t": "10:05:12", "idx": "NIFTY", "K": 23000, "ty": "PE", "side": "BUY", "px": 96.2,
             "rev": "3.1 (SENSEX-NIFTY-FLOW 9e2831b5)", "word": "WAIT", "counts": {"w": 4, "a": 1, "n": 2, "c": 2, "of": 9},
             "checks": [{"name": "RIGHT NOW", "st": "WITH", "cell": "flow saath"}]}
    path = os.path.join(server.VALIDATE_DIR, "press_2026-10-26.jsonl")
    rows = lambda: [json.loads(x) for x in open(path, encoding="utf-8")]   # noqa: E731
    assert _post("/api/validate/log", press, None) == {"ok": True, "new": True}
    assert _post("/api/validate/log", dict(press), None) == {"ok": True, "new": False}        # the same press twice: one row
    assert len(rows()) == 1 and {k: rows()[0][k] for k in press} == press and rows()[0]["day"] == "2026-10-26"
    assert _post("/api/validate/log", dict(press, t="10:05:40"), None)["new"] and len(rows()) == 2   # a later press: its own row
    away = _post("/api/validate/log", press, None, {"Sec-Fetch-Site": "cross-site", "Origin": "https://example.com"})
    bad = _post("/api/validate/log", dict(press, idx="FINNIFTY"), None)
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-10-26", "15:50"))
    late = _post("/api/validate/log", dict(press, t="15:50:00"), None)
    assert away["ok"] is False and "another site" in away["why"] and bad["ok"] is False and late["ok"] is False and len(rows()) == 2
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_hold_route.py::test_a_validate_press_is_logged_once_and_another_sites_post_is_refused`
Expected: FAIL with `AttributeError: module 'server' has no attribute 'VALIDATE_DIR'`. It fails on the `path` line, before any post, so nothing is written.

- [ ] **Step 3: Implement.**

In `server.py`, replace

```python
def _frame_chain(poller, idx):
```

with

```python
VALIDATE_DIR = os.path.join("data", "validate")    # F12 (25 Oct review, A75): her VALIDATE presses, press_<day>.jsonl
_VALIDATE_LOCK = threading.Lock()
_PRESS_KEY = ("t", "idx", "K", "ty", "side")


def _validate_press(doc):
    """POST /api/validate/log (F12, A75): one VALIDATE press as Validate's engine.js computed it (rev 3 / 3.1, §1p / §1q) --
    the word, its counts and its checks -- kept once per (t, idx, K, ty, side) in data/validate/press_<day>.jsonl, on the
    server's own day, market hours only (_market_hours, the one gate). A LOG ONLY: nothing reads it back, nothing is
    recomputed here, and no rule changes on it."""
    day, hm = _board_clock()
    row = {k: doc.get(k) for k in _PRESS_KEY + ("px", "rev", "word", "counts", "checks")}
    if not (isinstance(row["t"], str) and _HOLD_T.match(row["t"]) and row["idx"] in instruments.ENABLED
            and isinstance(row["K"], (int, float)) and row["ty"] in ("CE", "PE") and row["side"] in ("BUY", "SELL")
            and isinstance(row["word"], str) and isinstance(row["rev"], str)):
        return {"ok": False, "why": "not logged — a press needs t, idx, K, ty, side, rev and word"}
    if not _market_hours(day, day, hm):
        return {"ok": False, "why": "not logged — outside market hours"}
    key, path = tuple(row[k] for k in _PRESS_KEY), os.path.join(VALIDATE_DIR, f"press_{day}.jsonl")
    with _VALIDATE_LOCK:
        try:
            with open(path, encoding="utf-8") as f:   # ponytail: a scan per press (tens a day); a seen-set if they run to thousands
                for line in f:
                    try:
                        if tuple(json.loads(line).get(k) for k in _PRESS_KEY) == key:
                            return {"ok": True, "new": False}
                    except (ValueError, AttributeError):
                        continue
        except FileNotFoundError:
            pass
        os.makedirs(VALIDATE_DIR, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(row, day=day, at=time.strftime("%H:%M:%S")), ensure_ascii=False, default=str) + "\n")
    return {"ok": True, "new": True}


def _frame_chain(poller, idx):
```

(`_HOLD_T` and `_market_hours` are module-level and resolve at call time.)

Then replace

```python
        # PaperDesk's paper fills, tagged with the tape context they were
```

with

```python
        if self.path.startswith("/api/validate/log"):
            # F12 (25 Oct review, A75): Validate's press log, the word engine.js computed, kept once (_validate_press).
            # Same-origin only, the hold doors' rule; CAPPED; a log -- never an order, never a rule.
            site, origin = self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin") or ""
            if site is not None and site not in ("same-origin", "same-site", "none") and not origin.startswith("chrome-extension://"):
                self._json(json.dumps({"ok": False, "why": "refused — a POST from another site"}).encode(), 403)
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if not 0 < n < 65536:
                    self._json(b'{"ok":false,"why":"bad request"}', 400)
                    return
                out = _validate_press(json.loads(self.rfile.read(n) or b"{}"))
            except Exception as e:           # never 500 a log
                log.exception("validate press")
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
            return
        # PaperDesk's paper fills, tagged with the tape context they were
```

Then, in `_isolate_mock_writers`, replace

```python
    chain_live.CHAIN_DIR = ROOT / mock / "chain"
```

with

```python
    global VALIDATE_DIR
    VALIDATE_DIR = os.path.join(mock, "validate")                   # F12: Validate's press log (_validate_press)
    chain_live.CHAIN_DIR = ROOT / mock / "chain"
```

In `conftest.py`, replace

```python
             # the instrument dump cache: a stale cache would be RE-FETCHED and rewritten under data/
```

with

```python
             "server.VALIDATE_DIR": "validate",               # F12: Validate's press log (server._validate_press)
             # the instrument dump cache: a stale cache would be RE-FETCHED and rewritten under data/
```

- [ ] **Step 4: Run and see it pass.**

Run: `python -m pytest -q test_hold_route.py test_leak_guard.py test_frame_api.py test_receipts.py`
Expected: all pass. `test_leak_guard.py` gains one case (`server.VALIDATE_DIR`), and its mock-run test sees the path under `data/mock`.

---

### Task 2: The VALIDATE press posts its word (F12, face half)

**Touches Phase-2 files (`validate2/app.js`, `test/validate_app_harness.cjs`, `test_validate_app.py`): re-verify the anchors.**

**Files:**
- Modify: `ui-v2/public/validate2/app.js`:
  - add `check` above `openTrade`;
  - the Slip's VALIDATE button;
  - the two Enter keys.
- Modify: `tapemap/test/validate_app_harness.cjs` (Phase 2's file):
  - its `hms` stub;
  - the recorded POST body;
  - the seam;
  - a `press` scenario.
- Test: `tapemap/test_validate_app.py` (append).

**Interfaces:**
- **`check()`.** It sets mode validate and redraws, as Enter did.
- While the live clock is followed (`S.live && S.liveFollow && !S.closed`), it POSTs `engine.js`'s `E.validate(...)` output to `/api/validate/log`:
  - the body is `{t: hms(S.T), idx, K, ty, side, px, rev, word, counts, checks: [{name, st, cell}]}`;
  - checks drop their hover tips.
- A refused log toasts `press log nahi hua — <why>`.
- A press in a replay, or scrubbed back, is not logged: it is not forward evidence.

**Can affect:** one POST per press on the live clock.

**Untouched:**
- `engine.js` (not opened);
- the word on screen;
- `markTrade`;
- the palette's `validate` command (it fills the slip; the press is VALIDATE / Enter).

- [ ] **Step 1: Write the failing test.**

In `tapemap/test/validate_app_harness.cjs`, make four replacements.

(1) Replace

```js
hm: String, hms: String,
```

with

```js
hm: String, hms: (s) => new Date(s * 1000).toISOString().slice(11, 19),
```

(2) Replace

```js
      calls.push({ url, ms: sig ? sig.ms : null });
```

with

```js
      calls.push({ url, ms: sig ? sig.ms : null, body: opts && opts.body ? JSON.parse(opts.body) : null });
```

(3) Replace

```js
globalThis.__app = { S, voiceStop, poll, pollTrades, pollFold, pollFlat };
```

with

```js
globalThis.__app = { S, voiceStop, poll, pollTrades, pollFold, pollFlat, check, E };
```

(4) Replace

```js
const SCEN = {
```

with

```js
const SCEN = {
  // F12 (25 Oct review, A75): her VALIDATE press posts engine.js's word, once per press, on the live clock only
  async press() {
    const b = boot(routes());
    await wait();
    const A = b.app(), sent = () => b.calls.filter((c) => c.url === "/api/validate/log").map((c) => c.body);
    A.E.validate = () => ({ ok: true, rev: "3.1 (SENSEX-NIFTY-FLOW 9e2831b5)", idx: "NIFTY", K: 23000, ty: "PE", side: "BUY", px: 96.2, word: "WAIT",
      counts: { w: 4, a: 1, n: 2, c: 2, of: 9 }, checks: [{ name: "RIGHT NOW", st: "WITH", cell: "flow saath", tip: "a long hover" }] });
    Object.assign(A.S, { live: true, liveFollow: true, closed: false, T: 36312, slip: { idx: "NIFTY", K: 23000, ty: "PE", side: "BUY", px: "" } });
    A.check();
    await wait();
    const live = sent();
    A.S.liveFollow = false;                                        // scrubbed back: a replay press is not forward evidence
    A.check();
    await wait();
    return { live, after: sent().length, mode: A.S.mode };
  },
```

Append to `tapemap/test_validate_app.py`, replacing

```python
    assert o["feed"] == "dead" and o["fold"] == {"ok": False, "why": "not answering"}
```

with

```python
    assert o["feed"] == "dead" and o["fold"] == {"ok": False, "why": "not answering"}


def test_a_validate_press_posts_engine_js_word_once_on_the_live_clock_only():
    """F12 / A75 (TRADER F06): the VALIDATE button and Enter now POST the word engine.js computed (rev 3 / 3.1, unchanged)
    to /api/validate/log, its checks without their hovers. A press scrubbed back into the replay is not forward evidence."""
    o = run("press")
    assert o["live"] == [{"t": "10:05:12", "idx": "NIFTY", "K": 23000, "ty": "PE", "side": "BUY", "px": 96.2,
                          "rev": "3.1 (SENSEX-NIFTY-FLOW 9e2831b5)", "word": "WAIT", "counts": {"w": 4, "a": 1, "n": 2, "c": 2, "of": 9},
                          "checks": [{"name": "RIGHT NOW", "st": "WITH", "cell": "flow saath"}]}]
    assert o["after"] == 1 and o["mode"] == "validate"
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_validate_app.py`
Expected:
- The new test FAILS: the harness's `err` is `ReferenceError: check is not defined` (the seam names a function `app.js` does not have yet).
- Phase 2's two tests also fail, because the seam cannot load. That is expected, and Step 4 must show all three pass.

- [ ] **Step 3: Implement.** In `ui-v2/public/validate2/app.js`, make four replacements.

(1) Replace

```js
  function openTrade() {
```

with

```js
  // F12 (25 Oct review, A75): a VALIDATE press (the button, Enter) logs the word engine.js computed -- rev 3 / 3.1, §1p / §1q,
  // unchanged -- to POST /api/validate/log, kept once per (t, idx, K, ty, side). Live clock only: a press in a replay is not
  // forward evidence. A log: nothing reads it back here
  function check() {
    S.mode = "validate"; up();
    if (!S.live || !S.liveFollow || S.closed) return;
    const sl = S.slip, v = E.validate(sl.idx, Number(sl.K), sl.ty, sl.side, sl.px === "" ? null : Number(sl.px), S.T, feedT());
    if (!v.ok) return;
    post("/api/validate/log", { t: hms(S.T), idx: v.idx, K: v.K, ty: v.ty, side: v.side, px: v.px, rev: v.rev, word: v.word, counts: v.counts,
                                checks: v.checks.map(c => ({ name: c.name, st: c.st, cell: c.cell })) })
      .then(r => { if (!r.ok) toast(`press log nahi hua — ${r.why || "?"}`); });
  }
  function openTrade() {
```

(2) Replace

```js
onClick=${() => up()}>${icon("check")} VALIDATE
```

with

```js
onClick=${check}>${icon("check")} VALIDATE
```

(3) Replace

```js
if (inField) { if (e.key === "Enter") { e.preventDefault(); S.mode = "validate"; up(); } return; }
```

with

```js
if (inField) { if (e.key === "Enter") { e.preventDefault(); check(); } return; }
```

(4) Replace

```js
else if (k === "Enter") { S.mode = "validate"; up(); }
```

with

```js
else if (k === "Enter") check();
```

- [ ] **Step 4: Run and see it pass.**

Run: `python -m pytest -q test_validate_app.py test_validate3.py`
Expected: all pass (Phase 2's two, the new one, and `engine.js`'s own harness).

---

### Task 3: The record says when it is not being written (F13, server half, A76)

**Touches a Phase-2 file (`server.py`): re-verify the anchors.**

**Files:**
- Modify: `feed_health.py`: add `last_post` above `def reset`.
- Modify: `server.py`:
  - add `REC_DUE`, `REC_END`, `FRAME_QUIET_S`, `IMPORT_DIR`, `_REC`, `_REC_LOCK`, `_ist`, `_recording` and `_tradebook_due` above `def _frame_chain`;
  - add the import mark in `_receipts_import`;
  - add two keys in `/api/health`;
  - add `IMPORT_DIR` in `_isolate_mock_writers`.
- Modify: `conftest.py` (`STR_PATHS`).
- Test:
  - `test_feed_health.py` (append);
  - `test_receipts.py` (one fix, one test).

**Interfaces:**
- **`feed_health.last_post(day) -> float | None`:** the newest frame POST today on any index (epoch s).
- **`server._recording(now=None)`.**
  - It returns `None` outside 09:20–15:30 IST and on weekends.
  - Otherwise it returns `{ok, missing: [...], text}`.
    - `missing` names, in order: `book`, `chain`, `calls` (each from 09:20), `read` (from 09:25), and `GoCharting` (from 09:20).
    - A log is missing when no file of today has a byte.
    - `read` waits until 09:25 because its 09:20 mark is logged at about 09:21, after its 60 s grace [M: 23 Oct's first `read` row is 09:20].
    - `GoCharting` is missing when no frame POST came in `FRAME_QUIET_S` = 120 s.
  - `text` is `RECORDING NAHI: <missing, comma-joined>`, or `None`.
  - Each change of `text` within a day writes ONE row through `feed_health._log` (the existing writer, `data/feed_log.jsonl`): `{t, day, idx: "RECORD", from, to, since, why}`, with `to` the text or `RECORDING OK`. The day's first look writes a row only when something is missing.
- **`server._tradebook_due(now=None) -> {due: bool}`.** It is due after 15:30 on a weekday whose book recorded today, while `data/receipts/import_<day>.jsonl` does not exist.
- **`_receipts_import(csv, confirm=True)`** appends one row `{day, t, fills, wrote, today}` to that file. That includes an import with nothing new; a preview writes nothing.
- **`/api/health`** gains `"recording": _recording()` and `"tradebook": _tradebook_due()`.
  - The check runs whenever `/api/health` is read: 5173 reads it every 5 s, and Validate every 60 s on a live day.

**Can affect:**
- `/api/health`'s reply (two new keys);
- `data/feed_log.jsonl` (new `RECORD` rows; the GoCharting transition rows are unchanged);
- a new marker file per import day.

**Untouched:**
- every recorder (this only stats their files);
- the import's own writes and backups;
- `feed_health`'s six states.

- [ ] **Step 1: Write the failing tests.**

Append to `test_feed_health.py`, replacing

```python
    assert seen[(16, 9)]["state"] == "AFTER CLOSE"
```

with

```python
    assert seen[(16, 9)]["state"] == "AFTER CLOSE"


def test_the_recording_check_names_each_silent_log_and_logs_each_change_once(tmp_path, monkeypatch):
    """25 Oct review F13b / A76 (TRADER F07): 4 of her last 10 sessions recorded in full and nothing said so. From 09:20 on a
    weekday (the read log from 09:25: its 09:20 mark lands after its 60 s grace) each log with no row today is named, and
    GoCharting when no frame POST came in 2 min; each change is ONE row in data/feed_log.jsonl (feed_health's writer).
    /api/health carries it, and the tradebook nudge, for 5173, the Float and Validate."""
    import book_log
    import calls_log
    import chain_live
    monkeypatch.setattr(server, "_REC", {"day": None, "text": None})
    monkeypatch.setattr(server, "READ_DIR", str(tmp_path / "read"))
    logged = lambda: [json.loads(x) for x in open(fh.LOG, encoding="utf-8")] if os.path.exists(fh.LOG) else []   # noqa: E731
    assert server._recording(at(9, 19)) is None and server._recording(at(10, 0, day="2026-09-27")) is None   # before 09:20; a Sunday
    assert logged() == []
    assert server._recording(at(9, 21)) == {"ok": False, "missing": ["book", "chain", "calls", "GoCharting"],
                                            "text": "RECORDING NAHI: book, chain, calls, GoCharting"}
    server._recording(at(9, 22))
    assert [r["to"] for r in logged()] == ["RECORDING NAHI: book, chain, calls, GoCharting"]   # the same list: no second row
    for p in (book_log.day_path(DAY, "NIFTY"), str(chain_live.CHAIN_DIR / f"chain_SENSEX_{DAY}.jsonl"), calls_log.path(DAY),
              os.path.join(server.READ_DIR, f"read_{DAY}.jsonl")):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("{}\n")
    fh.on_post("NIFTY", DAY, {}, now=at(9, 25, 30))
    assert server._recording(at(9, 26)) == {"ok": True, "missing": [], "text": None}
    assert server._recording(at(9, 28))["text"] == "RECORDING NAHI: GoCharting"           # 150 s since the last frame POST
    assert [r["to"] for r in logged()] == ["RECORDING NAHI: book, chain, calls, GoCharting", "RECORDING OK", "RECORDING NAHI: GoCharting"]
    assert logged()[0]["idx"] == "RECORD" and logged()[1]["from"] == "RECORDING NAHI: book, chain, calls, GoCharting"
    cap = _Cap("/api/health")
    server.Handler.do_GET(cap)
    assert "recording" in cap.sent and "tradebook" in cap.sent
```

(`_Cap` is already imported at module level in this file, at `:133`, and its autouse fixture resets `feed_health`.)

In `test_receipts.py`, replace

```python
    d = str(tmp_path)
    monkeypatch.setattr(day_state, "DIR", d)
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-10-05", None))
```

with

```python
    d = str(tmp_path / "day_state")         # its own folder: the import mark (F13a) lands beside it, in tmp_path/receipts
    os.makedirs(d, exist_ok=True)
    monkeypatch.setattr(day_state, "DIR", d)
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-10-05", None))
```

(The test counted `os.listdir(tmp_path)`. It used the temp root as the day folder, so any writer landing beside it changes the count. That is its own root cause, fixed here and named.)

Then replace

```python
    assert out["ok"] and out["scoreboard"]["all"]["n"] == 3 and out["scoreboard"]["all"]["adds_dumped"] == 1
```

with

```python
    assert out["ok"] and out["scoreboard"]["all"]["n"] == 3 and out["scoreboard"]["all"]["adds_dumped"] == 1


def test_after_1530_a_recorded_day_with_no_import_is_due_and_a_confirmed_import_ends_it(tmp_path, monkeypatch):
    """25 Oct review F13a / A76 (TRADER F07): no tradebook import since 3 Oct. After 15:30 on a weekday whose book recorded,
    no confirmed import today makes /api/health's `tradebook.due` true (5173, the Float and Validate say "tradebook aaj
    import nahi" and link pro.html's RECORD, the existing import door). A confirmed import writes one row to
    data/receipts/import_<day>.jsonl and the nudge stops; a preview does not."""
    from datetime import datetime

    import book_log
    import day_state
    import server
    from chain_live import IST
    at = lambda h, m: datetime(2026, 10, 5, h, m, tzinfo=IST).timestamp()   # noqa: E731  (a Monday)
    assert server._tradebook_due(at(15, 45)) == {"due": False}             # no book rows today: no session, no nudge
    p = book_log.day_path("2026-10-05", "NIFTY")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("{}\n")
    assert server._tradebook_due(at(15, 29)) == {"due": False} and server._tradebook_due(at(15, 45)) == {"due": True}
    os.makedirs(str(tmp_path / "day_state"), exist_ok=True)
    monkeypatch.setattr(day_state, "DIR", str(tmp_path / "day_state"))
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-10-05", "15:45"))
    monkeypatch.setattr(server, "_save_day_state", lambda: None)
    monkeypatch.setitem(server._HOLD, "trades", [])
    monkeypatch.setitem(server._HOLD, "trades_day", "2026-10-05")
    assert server._receipts_import(syn(), False)["ok"] and server._tradebook_due(at(15, 46)) == {"due": True}   # a preview
    assert server._receipts_import(syn(), True)["ok"] and server._tradebook_due(at(15, 47)) == {"due": False}
    with open(os.path.join(server.IMPORT_DIR, "import_2026-10-05.jsonl"), encoding="utf-8") as f:
        assert len(f.readlines()) == 1
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_feed_health.py test_receipts.py`
Expected:
- `test_the_recording_check…` FAILS with `AttributeError: <module 'server'…> has no attribute '_REC'` (on its first `monkeypatch.setattr`).
- `test_after_1530…` FAILS with `AttributeError: module 'server' has no attribute '_tradebook_due'`.
- Every other test passes, including the fixed import test.

- [ ] **Step 3: Implement.**

In `feed_health.py`, replace

```python
def reset() -> None:
```

with

```python
def last_post(day: str):
    """The newest frame POST today on any index (epoch s), or None: the server's recording check (25 Oct review F13b)."""
    with _LOCK:
        return max((t.last_post for t in _T.values() if t.day == day and t.last_post is not None), default=None)


def reset() -> None:
```

In `server.py`, replace

```python
def _frame_chain(poller, idx):
```

with

```python
# F13 (25 Oct review, A76; TRADER F07): intake had stalled -- 4 of her last 10 sessions recorded in full, no tradebook import
# since 3 Oct -- and nothing said so. Two display-only checks ride /api/health for 5173, the Float and Validate.
REC_DUE = (("book", "09:20"), ("chain", "09:20"), ("calls", "09:20"), ("read", "09:25"), ("GoCharting", "09:20"))   # read: its 09:20 mark lands after its grace
REC_END = "15:30"
FRAME_QUIET_S = 120                                # no frame POST for 2 min: the panel's record is not being written
IMPORT_DIR = os.path.join("data", "receipts")      # one row per confirmed tradebook import, import_<day>.jsonl (_receipts_import)
_REC = {"day": None, "text": None}                 # the last recording state logged to data/feed_log.jsonl
_REC_LOCK = threading.Lock()


def _ist(now=None):
    from datetime import datetime
    from chain_live import IST
    return datetime.fromtimestamp(time.time() if now is None else now, IST)


def _recording(now=None):
    """F13b: which of today's logs is not being written, 09:20-15:30 IST on a weekday; None outside it. {ok, missing, text}:
    `missing` names each log with no row today (book, chain, calls; read from 09:25) and GoCharting when no frame POST came in
    FRAME_QUIET_S. Each change of `text` within a day is ONE row in data/feed_log.jsonl through feed_health's writer (the
    day's first look only when something is missing). Display only: nothing reads it but the faces."""
    from chain_live import CHAIN_DIR
    d = _ist(now)
    day, hm = d.strftime("%Y-%m-%d"), d.strftime("%H:%M")
    if d.weekday() >= 5 or not "09:20" <= hm < REC_END:
        return None

    def wrote(paths):
        for p in paths:
            try:
                if os.path.getsize(p) > 0:
                    return True
            except OSError:
                continue
        return False
    files = {"book": [book_log.day_path(day, i) for i in instruments.ENABLED],
             "chain": [str(CHAIN_DIR / f"chain_{i}_{day}.jsonl") for i in instruments.ENABLED],
             "calls": [calls_log.path(day)], "read": [os.path.join(READ_DIR, f"read_{day}.jsonl")]}
    last = feed_health.last_post(day)
    missing = [k for k, due in REC_DUE if hm >= due and (
        (last is None or d.timestamp() - last > FRAME_QUIET_S) if k == "GoCharting" else not wrote(files[k]))]
    text = "RECORDING NAHI: " + ", ".join(missing) if missing else None
    with _REC_LOCK:
        if (_REC["day"], _REC["text"]) != (day, text) and (_REC["day"] == day or text):
            feed_health._log({"t": d.strftime("%H:%M:%S"), "day": day, "idx": "RECORD",
                              "from": _REC["text"] if _REC["day"] == day else None, "to": text or "RECORDING OK",
                              "since": d.strftime("%H:%M:%S"), "why": "the recording check (25 Oct review F13b)"})
        _REC.update(day=day, text=text)
    return {"ok": not missing, "missing": missing, "text": text}


def _tradebook_due(now=None):
    """F13a: after 15:30 on a weekday whose book recorded today, no confirmed tradebook import today -> {"due": True}. The faces
    say "tradebook aaj import nahi" and link pro.html's RECORD, the existing import door; she exports the CSV from Kite
    herself and nothing here logs in for her. Display only."""
    d = _ist(now)
    day = d.strftime("%Y-%m-%d")
    ran = d.weekday() < 5 and d.strftime("%H:%M") >= REC_END and any(os.path.isfile(book_log.day_path(day, i)) for i in instruments.ENABLED)
    return {"due": bool(ran) and not os.path.isfile(os.path.join(IMPORT_DIR, f"import_{day}.jsonl"))}


def _frame_chain(poller, idx):
```

Then, in `_receipts_import`, replace

```python
    if add:
        _save_day_state()
    return {**out, "wrote": {**w["wrote"], **({day: [t["id"] for t in add]} if add else {})}, "backups": w["backups"]}
```

with

```python
    if add:
        _save_day_state()
    try:                                    # F13a (25 Oct review, A76): today's import is on record, so the after-close nudge stops
        os.makedirs(IMPORT_DIR, exist_ok=True)
        with open(os.path.join(IMPORT_DIR, f"import_{day}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": day, "t": time.strftime("%H:%M:%S"), "fills": plan["fills"], "wrote": w["wrote"],
                                "today": [t["id"] for t in add]}) + "\n")
    except OSError:
        log.exception("tradebook import mark")
    return {**out, "wrote": {**w["wrote"], **({day: [t["id"] for t in add]} if add else {})}, "backups": w["backups"]}
```

Then, in `/api/health`, replace

```python
                "day_restored": _SENSES.get("day_restored") or 0,
```

with

```python
                "day_restored": _SENSES.get("day_restored") or 0,
                # F13 (25 Oct review, A76): is today's record being written, and is today's tradebook imported (display only)
                "recording": _recording(),
                "tradebook": _tradebook_due(),
```

Then, in `_isolate_mock_writers`, replace (as Task 1 left it)

```python
    global VALIDATE_DIR
    VALIDATE_DIR = os.path.join(mock, "validate")                   # F12: Validate's press log (_validate_press)
```

with

```python
    global VALIDATE_DIR, IMPORT_DIR
    VALIDATE_DIR = os.path.join(mock, "validate")                   # F12: Validate's press log (_validate_press)
    IMPORT_DIR = os.path.join(mock, "receipts")                     # F13a: the tradebook import marks (_receipts_import)
```

In `conftest.py`, replace (as Task 1 left it)

```python
             "server.VALIDATE_DIR": "validate",               # F12: Validate's press log (server._validate_press)
```

with

```python
             "server.VALIDATE_DIR": "validate",               # F12: Validate's press log (server._validate_press)
             "server.IMPORT_DIR": "receipts",                 # F13a: the tradebook import marks (server._receipts_import)
```

- [ ] **Step 4: Run and see them pass.**

Run: `python -m pytest -q test_feed_health.py test_receipts.py test_leak_guard.py test_senses_api.py test_upstox_only.py`
Expected: all pass. The leak guard has one more case (`server.IMPORT_DIR`), and the health tests still see `feed` / `latency` / `coverage` verbatim.

---

### Task 4: RECORDING NAHI and the tradebook nudge on the faces (F13, face half)

**Touches Phase-2 files (`data.ts`, `Float.tsx`, `hold.css`, `validate2/app.js`): re-verify the anchors.**

**Files:**
- Modify: `ui-v2/src/data.ts`:
  - the `Intake` type above `LiveError`;
  - the state after `broker`;
  - its set beside `setBroker`;
  - the return.
- Modify: `ui-v2/src/App.tsx`:
  - the destructure;
  - two bars above the ANSWER band's comment;
  - `<Float intake=…/>`.
- Modify: `ui-v2/src/pro/Float.tsx`:
  - the import;
  - `Float` / `Win` props;
  - the alarm line.
- Modify: `ui-v2/src/hold/hold.css` (append after Phase 2's last line).
- Modify: `ui-v2/public/validate2/app.js`:
  - `health()` keeps `S.book`;
  - `FeedBand` gets the nudge.
- Test: `tsc`, `vite build`, the harness suite, and the controller's render check (no runner, by design).

**Interfaces:**
- `data.ts` `export type Intake = { recording: {ok, missing, text} | null; tradebook: {due} | null }`.
- `useLiveData()` returns `intake`. It is `null` when `/api/health` did not answer: the NOT LIVE banner speaks then.
- `Float({ intake })`: the alarm rides the top of the window. The window exists only in a trade (`Float.tsx:124`), so when flat the 5173 bar carries both lines.
- Validate's `S.book = /api/health.tradebook`, polled every 60 s on a live day.

**Can affect:**
- two new bars under the 5173 banners, on every tab (the tradebook one not on the Validate tab, where Validate's band says it);
- a line on top of the Float;
- Validate's band after 15:30.

**Untouched:**
- the NOT LIVE / NO TAPE / CHAIN STALE banners;
- the Float's voice and buttons;
- `pro/api.ts`'s poller.

- [ ] **Step 1: The failing check (controller, browser; executors record it and go on).**
  - On the controller's own preview (port 5175), open `/` and run in the console:

```js
const f0 = window.fetch; window.fetch = (u, o) => String(u).startsWith('/api/health') ? Promise.resolve(new Response(JSON.stringify({ ok: true, broker: 'upstox', coverage: {}, recording: { ok: false, missing: ['book', 'GoCharting'], text: 'RECORDING NAHI: book, GoCharting' }, tradebook: { due: true } }))) : f0(u, o)
```

  - Today nothing changes on screen: the reply's two keys are read by no one.

- [ ] **Step 2: Implement.**

In `ui-v2/src/data.ts`, replace

```ts
export type LiveError = 'unreachable' | 'no-data'
```

with

```ts
/** F13 (25 Oct review, A76): /api/health's two record checks, verbatim (server._recording / _tradebook_due); null = not read */
export type Intake = { recording: { ok: boolean; missing: string[]; text: string | null } | null; tradebook: { due: boolean } | null }
export type LiveError = 'unreachable' | 'no-data'
```

Replace

```ts
  const [broker, setBroker] = useState<string | null>(null)
```

with

```ts
  const [broker, setBroker] = useState<string | null>(null)
  /** F13: the recording check and the tradebook nudge off /api/health; null when the backend did not answer */
  const [intake, setIntake] = useState<Intake | null>(null)
```

Replace

```ts
      setBroker(health?.broker ?? null)
```

with

```ts
      setBroker(health?.broker ?? null)
      setIntake(health ? { recording: health.recording ?? null, tradebook: health.tradebook ?? null } : null)
```

Replace

```ts
  return { data, loading, error, errorWhy, broker, lastUpdated, barCount, at, dead, tapeBars,
```

with

```ts
  return { data, loading, error, errorWhy, broker, intake, lastUpdated, barCount, at, dead, tapeBars,
```

In `ui-v2/src/App.tsx`, replace

```tsx
  const { data: liveData, loading, error, errorWhy, broker, lastUpdated, barCount, at, dead, tapeBars,
```

with

```tsx
  const { data: liveData, loading, error, errorWhy, broker, intake, lastUpdated, barCount, at, dead, tapeBars,
```

Replace

```tsx
      {/* not on Trade either (2026-09-29): its left panel is the rev 6 engine's read, and the legacy
```

with

```tsx
      {/* F13 (25 Oct review, A76): the record must be written. /api/health's two checks, the server's words verbatim: from 09:20
          a log with no row today (RECORDING NAHI: book, chain, ...), and after 15:30 a recorded day with no tradebook import,
          linked to the import door (pro.html's RECORD tab). On the Validate tab Validate's own band says the second. */}
      {intake?.recording && !intake.recording.ok && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.bear, 0.12),
          borderBottom: `1px solid ${pal.bear}`, color: pal.bear,
          fontSize: 12.5, fontWeight: 700, letterSpacing: '0.02em',
        }}>
          {intake.recording.text}
        </div>
      )}
      {intake?.tradebook?.due && !onValidate && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.caution, 0.12),
          borderBottom: `1px solid ${pal.caution}`, color: pal.caution,
          fontSize: 12.5, fontWeight: 600,
        }}>
          tradebook aaj import nahi · <a href="/pro.html?tab=record" target="_blank" rel="noopener" style={{ color: pal.caution }}>import karo</a>
        </div>
      )}

      {/* not on Trade either (2026-09-29): its left panel is the rev 6 engine's read, and the legacy
```

Replace

```tsx
<Float />
```

with

```tsx
<Float intake={intake} />
```

In `ui-v2/src/pro/Float.tsx`, make four replacements.

(1) Replace

```tsx
import { Guard, Ico } from '../hold/parts'
```

with

```tsx
import { Guard, Ico } from '../hold/parts'
import type { Intake } from '../data'
```

(2) Replace

```tsx
export default function Float() {
  return <Guard name="floating window"><Win /></Guard>
}

function Win() {
```

with

```tsx
export default function Float({ intake }: { intake?: Intake | null }) {
  return <Guard name="floating window"><Win intake={intake} /></Guard>
}

function Win({ intake }: { intake?: Intake | null }) {
```

(3) Replace

```tsx
  const win = <div ref={box} className={cls} style={style}>
```

with

```tsx
  // F13 (25 Oct review, A76): the record's two alarms ride the window too, above the voice -- RECORDING NAHI (the server's
  // words) and, after 15:30, the tradebook import; the window exists only in a trade, so flat the 5173 bar carries both
  const rec = intake?.recording && !intake.recording.ok ? intake.recording.text : null
  const alarm = (rec || intake?.tradebook?.due) && <div className="fl-rec">
    {rec && <b className="no">{rec}</b>}
    {intake?.tradebook?.due && <a href={new URL('/pro.html?tab=record', location.href).href} target="_blank" rel="noopener">tradebook aaj import nahi</a>}
  </div>
  const win = <div ref={box} className={cls} style={style}>
    {alarm}
```

(4) None further: `{vc && !min ? voiceEl : line}` follows unchanged.

In `ui-v2/src/hold/hold.css`, replace (Phase 2's last line)

```css
.hv .vage.dead{color:var(--negative);font-weight:700}
```

with

```css
.hv .vage.dead{color:var(--negative);font-weight:700}
/* F13 (25 Oct): the record's alarms on the window -- RECORDING NAHI and, after 15:30, the tradebook import */
.hv .fl-rec{display:flex;flex-wrap:wrap;gap:var(--s1) var(--s3);padding:var(--s1) var(--s3);border-bottom:1px solid var(--border-strong);background:var(--surface-raised);font:600 var(--t12)/1.4 var(--f-ui)}
.hv .fl-rec .no{color:var(--negative)}.hv .fl-rec a{color:var(--caution)}
```

In `ui-v2/public/validate2/app.js`, replace

```js
S.late = c.late_min > 0 ? { up: c.server_up, min: c.late_min, from: fr ? fr.slice(0, 5) : c.server_up } : null; up(); }
```

with

```js
S.late = c.late_min > 0 ? { up: c.server_up, min: c.late_min, from: fr ? fr.slice(0, 5) : c.server_up } : null; S.book = h.tradebook || null; up(); }
```

and replace

```js
    if (S.feed !== "dead" && S.live && (S.late || bf)) return html
```

with

```js
    // F13 (25 Oct review, A76): after 15:30 a recorded day with no tradebook import says so, with the import door (pro.html RECORD)
    if (S.feed !== "dead" && S.live && S.book && S.book.due) return html`<div class="band on slow">${icon("clock")}<b>tradebook aaj import nahi</b><span class="sp"></span><a class="fix" href="/pro.html?tab=record" target="_blank" rel="noopener">import karo</a></div>`;
    if (S.feed !== "dead" && S.live && (S.late || bf)) return html
```

- [ ] **Step 3: Typecheck, build, and the harness.**

Run (ui-v2): `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: `tsc` prints nothing; `✓ built`.

Run (TapeMap): `python -m pytest -q test_validate_app.py test_validate3.py`
Expected: all pass.

- [ ] **Step 4: The passing check (controller, browser, light, one screenshot each).**
  - Reload `/`, run Step 1's console line, and wait up to 5 s (the next poll):
    - a red bar reads **`RECORDING NAHI: book, GoCharting`**;
    - an amber bar under it reads **`tradebook aaj import nahi · import karo`**, and the link opens `/pro.html?tab=record` (RECORD, with IMPORT TRADEBOOK).
  - On `/?fixture=1`, put a trade with Phase 2 Task 4's first snippet. The Float's top line shows both alarms.
  - Validate's band shows only on a live day after 15:30, because `health()` runs only live. It is **unverified until Monday 26 Oct after 15:30**; record that in NOTEPAD (Task 6).

---

### Task 5: The voice's first line shows the premium from her entry (F14, TRADER F02)

**Files:**
- Modify: `voice.py:173` (after `pnl`) and `:180` (l1's last segment).
- Test: `test_voice.py`:
  - `:37`, the pinned l1, updated;
  - one test appended.

**Interfaces:**
- `ladder(...)["l1"]` now ends ` · prem <sign><N>%`.
  - N is `round(100 × own × (now − p0) / p0)`, with `own` = −1 for a sale.
  - `now` is `view.prem.now`, the same LTP the ₹ figure beside it uses. `p0` is the trade's entry premium.
  - The sign is `−` (U+2212) or `+`, and nothing for 0.
- When the LTP or the entry is unknown (or the entry is 0): `prem ?`.
- No field, state, seq, stop or trigger changes.
- `fold.py`'s own `view.prem.pct` uses the same formula. The voice computes from its own `pn` / `p0`, so the ₹ and the % on one line can never disagree.

**Can affect:**
- l1's text on the panel, the Float and Validate, all verbatim;
- the voice path replays (`voice_path.py`), which carry the new l1 on new replays.

**Untouched:**
- the ladder, `_triggers`, l2–l5;
- `trademap.py`;
- every existing log row.

- [ ] **Step 1: Write the failing test.** In `test_voice.py`, replace

```python
"▼ 23000 PE · 22 min · +13 pts (₹+15)"
```

with

```python
"▼ 23000 PE · 22 min · +13 pts (₹+15) · prem +9%"
```

(190 vs 174.85 is +8.66 % → `+9%`.) Then replace

```python
    assert voice.bleed(v["W"])
```

with

```python
    assert voice.bleed(v["W"])


def test_l1_shows_the_premium_from_her_entry_signed_by_her_side():
    """25 Oct review F14 (TRADER F02): on 22 Oct she held the SENSEX 73400 CE from the 13:00 mark at 201.4 while the voice said
    HOLD and the premium halved -- 107.65 at 13:20 -- and no face showed it. l1 now ends `prem −47%`: (now − entry) / entry,
    signed by her side, so a sale's rising premium reads against her. Display only: the state is the same without it."""
    ce = dict(TR, idx="SENSEX", k=73400, ty="CE", p0=201.4, entry_t="13:00:00")
    v = run(dict(rep(now="13:20:00", d=1, prem={"now": 107.65, "at_G": 90.0}), trade=ce), h2(), now="13:20:00")
    assert v["l1"] == "▲ 73400 CE · 20 min · -13 pts (₹-94) · prem −47%"
    sale = run(dict(rep(prem={"now": 120.0, "at_G": 150.0}), trade=dict(TR, side="SELL", p0=100.0)), h2())
    assert sale["l1"].endswith(" · prem −20%")                              # a sale: the premium up is against her
    blind = run(dict(rep(prem={"at_G": 150.0}), trade=TR), h2())
    assert blind["l1"].endswith(" · prem ?") and blind["state"] == run(rep(), h2())["state"] == "HOLD"
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_voice.py`
Expected:
- `test_hold_reads_the_two_strongest_with_facts_oi_first` FAILS: `assert '▼ 23000 PE · 22 min · +13 pts (₹+15)' == '… · prem +9%'`.
- `test_l1_shows_the_premium…` FAILS the same way.

- [ ] **Step 3: Implement.** In `voice.py`, replace

```python
    pnl = None if None in (pn, p0) else round(own * (pn - float(p0)), 1)
```

with

```python
    pnl = None if None in (pn, p0) else round(own * (pn - float(p0)), 1)
    # F14 (25 Oct review, TRADER F02): she trades premium -- l1 ends with the premium's move from her entry, signed by her side
    # (a sale's rising premium reads against her). Display only: no state, stop or seq reads it
    pq = None if pnl is None or not float(p0) else round(100 * own * (pn - float(p0)) / float(p0))
    prem = "prem ?" if pq is None else f"prem {'−' if pq < 0 else '+' if pq > 0 else ''}{abs(pq)}%"
```

and replace

```python
          f"{'?' if pts is None else f'{pts:+d}'} pts ({'₹?' if pnl is None else f'₹{pnl:+.0f}'})")
```

with

```python
          f"{'?' if pts is None else f'{pts:+d}'} pts ({'₹?' if pnl is None else f'₹{pnl:+.0f}'}) · {prem}")
```

- [ ] **Step 4: Run and see it pass.**

Run: `python -m pytest -q test_voice.py test_trademap.py test_voice_path.py test_sensex_flow.py test_fold_live.py`
Expected: all pass. A file the tree does not have is skipped by pytest's "file not found"; drop it from the command.

---

### Task 6: Phase 3 — verify, record, commit

**Touches Phase-2 files (`CLAUDE.md`, `docs/live/NOTEPAD.md`, as Phase 2 Task 8 left them): re-verify the anchors.**

**Files:**
- Modify: `docs/live/NOTEPAD.md` (A75, A76, A78).
- Modify: `CLAUDE.md` (a review bullet, and the pytest line).
- Commit: TapeMap only. Phase 3 touches no extension file.

- [ ] **Step 1: The full server suite.**

Run: `python -m pytest -q`
Expected: **1980 collected**. All pass but the 1 skipped and at most the 1 known flaky A49 test. Any other failure: stop and fix its cause.

- [ ] **Step 2: ui-v2.**

Run: `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean; `✓ built`.

- [ ] **Step 3: The diff is only Phase 3.**

Run: `git diff --stat`
Expected: `server.py`, `feed_health.py`, `voice.py`, `conftest.py`, `test_hold_route.py`, `test_feed_health.py`, `test_receipts.py`, `test_voice.py`, `test_validate_app.py`, `test/validate_app_harness.cjs`, `ui-v2/src/{data.ts,App.tsx,pro/Float.tsx,hold/hold.css}`, `ui-v2/public/validate2/app.js`. No whole-file rewrite.

- [ ] **Step 4: Record it.** Make these NOTEPAD replacements.

(1) A75: replace

```
| A write-once log per press (log only, no rule change) | OPEN |
```

with

```
| A write-once log per press (log only, no rule change) | FIXED (25 Oct, Phase 3): `POST /api/validate/log`, write-once by (t, idx, K, ty, side) in `data/validate/press_<day>.jsonl`, the server's day, market hours only; Validate posts on VALIDATE / Enter while following the live clock (`test_hold_route …validate_press…`, `test_validate_app …press…`). Live at her next TapeMap + 5173 start |
```

(2) A76: replace

```
| A daily tradebook import via `/api/receipts/import`; a 09:20 "recording?" check | OPEN (extends A22) |
```

with

```
| A daily tradebook import via `/api/receipts/import`; a 09:20 "recording?" check | FIXED (25 Oct, Phase 3): `/api/health` `recording` (09:20–15:30: book, chain, calls, read from 09:25, GoCharting in 2 min → `RECORDING NAHI: …` on 5173 and the Float; one `data/feed_log.jsonl` row `idx RECORD` per change) and `tradebook` (after 15:30 on a recorded weekday with no import today → `tradebook aaj import nahi` on 5173 / the Float / Validate, linking pro.html RECORD; a confirmed import writes `data/receipts/import_<day>.jsonl`). The check runs when a face reads /api/health. Validate's band unverified until a live day after 15:30 |
```

(3) A78: replace

```
| RESOLVED into the STOP list (25 Oct) |
```

with

```
| RESOLVED into the STOP list (25 Oct); F14 BUILT (Phase 3): l1 ends `prem ±N%` from her entry, signed by side, `prem ?` without an LTP (`test_voice …premium_from_her_entry…`) |
```

`CLAUDE.md`: replace

```
- **Locked setups and registrations:** `context/research-findings.md`:
```

with

```
- **Review 25 Oct (FIX / CUT / STOP)**, spec `docs/superpowers/specs/2026-10-25-review-fix-cut-stop-design.md`, plans `docs/superpowers/plans/2026-10-25-review-*`. Phase 3: every Validate press is logged (`POST /api/validate/log` → `data/validate/press_<day>.jsonl`); `/api/health` carries `recording` (RECORDING NAHI on 5173 and the Float, a `data/feed_log.jsonl` row per change) and `tradebook` (after 15:30, no import today; `data/receipts/import_<day>.jsonl`); the voice's l1 ends `prem ±N%`.
- **Locked setups and registrations:** `context/research-findings.md`:
```

Then set the `python -m pytest -q` line in `## Running it` to Step 1's count: `1980 collected: 1978 pass, 1 skipped, 1 known flaky (test_v2feed serve-cache, NOTEPAD A49), as of 2026-10-25 (review Phase 3, the evidence)`.

- [ ] **Step 5: The controller's browser checks** (Task 4 Step 4), saved beside the plan's run notes.

- [ ] **Step 6: Commit (the controller, on her 25 Oct delegation).**

```bash
cd "/c/Users/kaam/Desktop/operator mode/tapemap" && git add server.py feed_health.py voice.py conftest.py test_hold_route.py test_feed_health.py test_receipts.py test_voice.py test_validate_app.py test/validate_app_harness.cjs ui-v2/src/data.ts ui-v2/src/App.tsx ui-v2/src/pro/Float.tsx ui-v2/src/hold/hold.css ui-v2/public/validate2/app.js docs/live/NOTEPAD.md CLAUDE.md docs/superpowers/plans/2026-10-25-review-phase3-4-evidence-cuts.md
git commit -m "review 25 Oct phase 3: the evidence (A75, A76, F14)

- POST /api/validate/log: every Validate press, write-once, data/validate/press_<day>.jsonl
- /api/health recording (RECORDING NAHI on 5173 + Float, a feed_log row per change) and tradebook (after 15:30)
- the voice's l1 ends prem +-N% from her entry, signed by side

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

# PHASE 4 — THE CUTS

Each cut's test is:
- the full suite stays green;
- `tsc` and `vite build` are clean;
- a grep proves the removed names are gone;
- where the screen changes, the controller's render check in light mode.

A pinned test that covers removed behaviour is named where it is deleted or changed.

### Task 7: The ANSWER band is THE READ's row (C1 + C4, A74)

**Files:**
- Modify: `ui-v2/src/App.tsx`:
  - imports `:3`, `:18`;
  - delete `TimingChip` / `Grounds` / `DirectionChip` (`:153-207`);
  - replace the band (`:1353-1554`);
  - delete the dead `tradeLevels` memo (`:1717-1747`);
  - the call site `:1867`;
  - the CHAIN STALE sentence `:1859`.
- Test: grep, `tsc`, `vite build`, render check.

**Interfaces:**
- `AnswerBand({ index, stale })`: the price column (unchanged) and `<ReadLine index={index} />`. The stale warning stays.
- Cut:
  - the engine verdict (its held copy, "engine ka verdict", the timing and direction chips, the headline, Grounds, sub, "Engine changes if");
  - MAX PAIN / GEX / PCR / SQUEEZE;
  - AAJ KA DIN (`DayTypeLine`, its "Changes if" row): this is C4, the only face it was on [M: grep];
  - max pain as a level (`tradeLevels`).
- `tradeLevels` was computed and **read by nothing**. Its removal changes no pixel.

**Can affect:** the band on every tab but Read / Board / Validate / Trade.

**Untouched:**
- `data.ts` (it still maps `READS[].daytype` and `ground`, read by no face now);
- `calls_log` and `/api/calls` (the forward log keeps writing);
- DIN (§1o, on the panel);
- THE READ.

- [ ] **Step 1: The failing check.**

Run: `grep -nE "DayTypeLine|TimingChip|DirectionChip|Grounds|DT_HOLD_MS|engineVsRead|tradeLevels|MAX PAIN|Aaj ka din|engine ka verdict|maxPain" ui-v2/src/App.tsx | wc -l`
Expected today: about 30 lines.

- [ ] **Step 2: Implement.**

(1) Run (Git Bash, from `tapemap/ui-v2/src`):
- `python "$CUT" App.tsx "function TimingChip(" "function IndexCell("`. It deletes about lines 153–207.
- `python "$CUT" App.tsx "/* \u2500\u2500 ANSWER band" "/* \u2500\u2500 Machine strip"`. It deletes the band comment, `DT_HOLD_MS`, `DayTypeLine` and `AnswerBand`, about 145 lines after the first cut.
- `python "$CUT" App.tsx "  // MAP levels are bar-derived and causal under replay." "  const barTime = data.CHART_DATA"`. It deletes about 31 lines.

(2) Insert the new band. Replace

```tsx
/* ── Machine strip
```

with

```tsx
/* ANSWER band: above the tabs on every tab but Read, Board, Validate and Trade -- the price and THE READ's one row (read.py).
   Since the 25 Oct review (C1 + C4, A74) nothing else: the engine's verdict said GO up, CONTRADICTED, at 13:00 on 22 Oct into
   her 73400 CE, so the verdict, its timing and direction chips and headline, MAX PAIN / PCR / GEX / SQUEEZE, AAJ KA DIN and
   max pain as a chart level are cut. The `calls` forward log keeps writing (calls_log.py); DIN (§1o) is the day type kept. */
function AnswerBand({ index, stale }: { index: IndexKey; stale: boolean }) {
  const { INDICES } = useData()
  const pal = usePalette()
  const info = INDICES[index]
  const has = hasRead(info)
  const dirCol = info.change > 0 ? pal.bull : info.change < 0 ? pal.bear : pal.textSecondary

  return (
    <div style={{ backgroundColor: pal.bg, borderBottom: `1px solid ${pal.border}`, flexShrink: 0 }}>
      {/* Grid lives in index.css (.answer-band) because it needs a breakpoint
          and an inline style cannot carry one — see the note there. */}
      <div className="answer-band">
        <div style={{ whiteSpace: 'nowrap' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <div className="mono" style={{
              fontSize: 32, lineHeight: 1, fontWeight: 600, letterSpacing: '-0.02em',
              // a price you cannot trust must not look like one you can
              color: stale ? pal.textMuted : pal.textPrimary,
              textDecoration: stale ? 'line-through' : 'none',
            }}>
              {has ? info.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
            </div>
            {/* Frame discipline: this is the futures tape, and OI Flow's LTP
                column is the index print — 70+ points apart some afternoons.
                Both carry their frame so neither reads as the other. */}
            <span title="Futures frame — the tape this app draws"
              style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: pal.textMuted }}>
              FUT
            </span>
          </div>
          <div className="mono" style={{ fontSize: 12, color: stale ? pal.textMuted : dirCol, marginTop: 5 }}>
            {!has ? 'not shown' : stale ? 'not live' : `${info.change > 0 ? '+' : ''}${info.change.toFixed(2)} · ${info.pct > 0 ? '+' : ''}${info.pct.toFixed(2)}%`}
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          {stale && (
            <div style={{
              fontSize: 11, letterSpacing: '0.15em', textTransform: 'uppercase',
              color: pal.bear, fontWeight: 700, marginBottom: 4,
            }}>
              No live data — do not trade from this screen
            </div>
          )}
          <ReadLine index={index} />
        </div>
      </div>
    </div>
  )
}

/* ── Machine strip
```

(3) Replace

```tsx
        <AnswerBand index={activeIndex} stale={!!error || idxDead} replaying={scrub != null} />
```

with

```tsx
        <AnswerBand index={activeIndex} stale={!!error || idxDead} />
```

(4) Replace

```tsx
import type { IndexKey, IndexInfo, Dataset, HeatTone, Chain, MapLevelKind, FlowRow, RunState, TapeBar, Interval, GroundedCall, Read, DayType } from './data'
```

with

```tsx
import type { IndexKey, IndexInfo, Dataset, HeatTone, Chain, MapLevelKind, FlowRow, RunState, TapeBar, Interval } from './data'
```

(5) Replace

```tsx
import ReadTab, { ReadLine, useRead, engineVsRead } from './read/ReadTab'
```

with

```tsx
import ReadTab, { ReadLine, useRead } from './read/ReadTab'
```

(6) Replace

```tsx
          Max pain, GEX, PCR and the chain-derived chart levels below are from that moment, not now.
```

with

```tsx
          OI and the chain-derived reads below are from that moment, not now.
```

- [ ] **Step 3: Pass.**

Run: the Step 1 grep without `| wc -l`.
Expected: exactly one line, `EMPTY_CHAIN`'s `pcr: '—', maxPain: 0, gex: '—', squeeze: '—', strikes: [],`. The `Chain` type's field stays.

Run: `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean; `✓ built`.

- [ ] **Step 4: Render check (controller, light, one screenshot).** On the preview, open the OI Flow tab.
  - The band shows the futures price and THE READ's row only.
  - There is no `engine ka verdict` button, no MAX PAIN / GEX / PCR chip, no `Aaj ka din` line and no `Changes if` row.

---

### Task 8: Nine tabs (C2)

**Files:**
- Modify: `ui-v2/src/App.tsx`:
  - imports `:2`, `:3`, `:5`, `:8`;
  - the Tab type and its Glass comment (`:39-51`, `:70`);
  - helpers `NotShown`, `formatOI` … `kindStyle`;
  - the six tab components (`TapeTab` … `HeatTab`, `:466-1108`);
  - the tab array `:1694`;
  - the content area.
- Modify: `ui-v2/src/index.css`: the Liquid glass block, `:60-297`, the Glass board's only material.
- Delete: `ui-v2/src/one/` (`GlassBoard.tsx` 990, `glass.tsx` 696, `wire.ts` 218 lines; imported only by `App.tsx` [M: grep]).
- Test: grep, `tsc`, `vite build`, render check.

**Interfaces:**
- `Tab = 'Read' | 'Board' | 'Trade' | 'Flow' | 'VPIN' | 'OI Flow' | 'War' | 'Validate' | 'Signals'`, in the same order on the bar.

**Can affect:** the tab bar and the content area.

**Untouched:**
- OI Flow (`OiFlowTab`, her keeper);
- Read, Board, Trade, Flow, VPIN, War, Validate, Signals;
- `machine.ts`;
- `data.ts`. Its `HEAT`, `PRESSURE`, `EVENTS_BY_IDX`, `FOCUS_BY_IDX`, `ORDER_FLOW`, `KEY_LEVELS` and `MAP` stay computed: they are a live shared mapper in a Phase-2 file with no test runner, and are read by no tab now. They are logged as A87 (Task 15), and cut when `data.ts` is next opened.

- [ ] **Step 1: The failing check.**

Run: `grep -cE "GlassBoard|HeatTab|TapeTab|ChainTab|EventsTab|MapTab|OffPeak|HEAT_COLS|heatColor|kindStyle|formatOI|NotShown" ui-v2/src/App.tsx; ls ui-v2/src/one`
Expected today: a count above 20; three files.

- [ ] **Step 2: Implement.**

(1) Run (from `tapemap/ui-v2/src`), in this order:

```bash
python "$CUT" App.tsx "function TapeTab({ index }: { index: IndexKey }) {" "// \u2500\u2500 App"
python "$CUT" App.tsx "/** The empty dataset's rendering for a whole tab" "const DataCtx = createContext<Dataset>(EMPTY)"
python "$CUT" App.tsx "// Real OI is large" "// \u2500\u2500 Sub-components"
python "$CUT" App.tsx "        {/* key={activeIndex} for the same reason TradeTab carries one: the" "        {activeTab === 'Trade'    && <TradeTab"
python "$CUT" App.tsx "        {/* key={activeIndex}: the pins are per index" "        {/* Mounted only while active, which is also what stops its 30s poll:"
python "$CUT" App.tsx "        {activeTab === 'Chain'" "        {activeTab === 'OI Flow'"
python "$CUT" App.tsx "        {activeTab === 'Events'" "        {/* her order 2026-09-29: Validate is the rev 6 DESK"
python "$CUT" App.tsx "        {activeTab === 'Map'" '        {/* No `index` prop, deliberately'
python "$CUT" index.css "/* \u2500\u2500 Liquid glass" "/* \u2500\u2500 ANSWER band layout"
git rm -r one
```

Expected deletions, in order:
- the six tab components (about 643 lines);
- `NotShown` (about 14);
- `formatOI` … `kindStyle` (about 25);
- the Glass and Heat content lines with their comments (17);
- Tape (2), Chain (1), Events (1), Map (1);
- the glass CSS (about 238).

(2) Replace

```tsx
import { useLiveData, HEAT_COLS, chainAgeS, CHAIN_STALE_S } from './data'
import type { IndexKey, IndexInfo, Dataset, HeatTone, Chain, MapLevelKind, FlowRow, RunState, TapeBar, Interval } from './data'
import { usePalette, rgbOf } from './theme'
import type { Palette } from './theme'
```

with

```tsx
import { useLiveData, chainAgeS, CHAIN_STALE_S } from './data'
import type { IndexKey, IndexInfo, Dataset, Chain, FlowRow, RunState, TapeBar, Interval } from './data'
import { usePalette, rgbOf } from './theme'
```

(3) Replace

```tsx
import GlassBoard from './one/GlassBoard'
import SignalsTab from './signals/SignalsTab'
```

with

```tsx
import SignalsTab from './signals/SignalsTab'
```

(4) Replace

```tsx
// IndexKey now comes from ./data (single source of truth for the live layer).
// 'Glass' is the glance BOARD (src/one/GlassBoard.tsx): the machine and seven
// instruments as movable panes of glass, each one a launcher into the tab that
// owns its evidence. It replaces the one-screen chart trial that used to sit
// here — that trial answered "what has to happen next" with a bigger chart,
// which is the thing the operator already has in Kite.
//
// It is listed FIRST and is NOT the default tab — the operator judges it
// against the nine that already exist, and a board that seizes the landing
// screen would be judging itself.
//
// Exported because GlassBoard takes `setActiveTab` and must name the tab each
// pane opens. A type-only import is erased at compile time, so this does not
// make the two modules cyclic at runtime.
```

with

```tsx
// IndexKey now comes from ./data (single source of truth for the live layer).
// Nine tabs since the 25 Oct review (C2): Heat, Glass, Tape, Events, Map and Chain are cut (the 3 Oct cut list, F28).
```

(5) Replace

```tsx
export type Tab = 'Read' | 'Board' | 'Glass' | 'Heat' | 'Trade' | 'Tape' | 'Flow' | 'VPIN' | 'Chain' | 'OI Flow' | 'War' | 'Events' | 'Validate' | 'Map' | 'Signals'
```

with

```tsx
export type Tab = 'Read' | 'Board' | 'Trade' | 'Flow' | 'VPIN' | 'OI Flow' | 'War' | 'Validate' | 'Signals'
```

(6) Replace

```tsx
  const tabs: Tab[] = ['Read', 'Board', 'Glass', 'Heat', 'Trade', 'Tape', 'Flow', 'VPIN', 'Chain', 'OI Flow', 'War', 'Events', 'Validate', 'Map', 'Signals']
```

with

```tsx
  const tabs: Tab[] = ['Read', 'Board', 'Trade', 'Flow', 'VPIN', 'OI Flow', 'War', 'Validate', 'Signals']
```

- [ ] **Step 3: Pass.**

Run: `grep -nE "GlassBoard|HeatTab|TapeTab|ChainTab|EventsTab|MapTab|OffPeak|HEAT_COLS|heatColor|heatRgb|kindStyle|formatOI|NotShown|\bPalette\b|'Glass'|'Heat'|'Tape'|'Events'|'Map'|'Chain'" ui-v2/src/App.tsx; grep -c "glass" ui-v2/src/index.css; grep -rn "one/" ui-v2/src --include=*.ts --include=*.tsx`
Expected: no line; `0`; no line.

Run: `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean; `✓ built`.

- [ ] **Step 4: Render check (controller, light, one screenshot).** The bar reads `Read · Board · Trade · Flow · VPIN · OI Flow · War · Validate · Signals`. Each opens, and OI Flow's table renders as before.

---

### Task 9: The panel: no EXPRESSION pill; in a trade, the voice and one [detail ▸] (C3 + C5, A79, TRADER F15)

**Touches Phase-2 files (`src/shell/panel.js`, `test/panel.mjs`): re-verify the anchors.** The `vcOk` / `put('plan', …)` lines are Phase 2 Task 3's.

**Files:**
- Modify: `src/shell/panel.js`:
  - the header comment `:7`;
  - `header()` (`:238`, `:243`, `:251-252`);
  - the voice's `vd` title (`:383`);
  - `render()` (`:425-441`).
- Test: `test/panel.mjs`:
  - `:68`, the §5 head check;
  - `:291`, `:301`, the v2.6 byte-identity check;
  - a C5 block before the one `console.log('');`.

**Interfaces:**
- `header(m, X, F, slim)`. Slim keeps:
  - the index, the price, the clock, the bell (mute in a trade);
  - the two feed dots;
  - the 15:00 reminder.
- In `render()`, `shut = vcOk && !vOpen`, where `vcOk` keeps Phase 2's expression and moves to the top of `render()`.
- While shut, these blocks are blank: `decode`, `khil`, `card`, `din`, `abhi`, `bade`, `plan` (the FOLD board, the map detail, JAGAH) and `q`.
- `voice`, `banner`, `act` (I'M OUT), `msg`, `foot` and `rail` render as before.
- The one `[detail ▸]` is the voice's existing `vdet` (`ofd.vdet`, shut by default, remembered).
- A voice that cannot speak folds nothing.

**Can affect:** the panel's head, always (no pill), and every block while she holds a trade with the voice speaking.

**Untouched:**
- the chart's lines (`overlay.js`, `main.js`);
- `frame.read.expr` on the wire and TapeMap's §1h log;
- the sound ladder;
- the flat panel (apart from the pill);
- the FADE KILL and READ-2's `push`.

- [ ] **Step 1: Write the failing tests.**

In `test/panel.mjs`, replace

```js
/BUY PE/.test(hd) && /f \| ≈[\d,]+s/.test(hd), '§5 the head: NIFTY · KHEL · SIZE (LEAN only) · PREMIUM · fut | ≈spot: '
```

with

```js
!/BUY PE/.test(hd) && /f \| ≈[\d,]+s/.test(hd), '§5 the head: NIFTY · KHEL · SIZE (LEAN only) · fut | ≈spot, no EXPRESSION pill (C3, 25 Oct): '
```

Replace

```js
    const V27 = { hd: (h) => h.replace('<b>O</b> naye · ', ''), din: null, bade: null };   // null: changed on purpose (checked in the v2.7 block)
```

with

```js
    const V27 = { hd: (h) => h.replace('<b>O</b> naye · ', ''), din: null, bade: null };   // null: changed on purpose (checked in the v2.7 block)
    const C3 = { hd: (h) => h.replace(' · <span class="pill">BUY PE</span>', '') };   // 25 Oct C3: the v2.6 head's EXPRESSION pill is cut
```

Replace

```js
if ((V27[id] ? V27[id](a[i]) : a[i]) !== was[i]) bad.push(name + ' ' + id);
```

with

```js
if ((V27[id] ? V27[id](a[i]) : a[i]) !== (C3[id] ? C3[id](was[i]) : was[i])) bad.push(name + ' ' + id);
```

Then replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review C5 (TRADER F15): in a trade the panel is the voice block and the chart's lines; the rest waits under its
// one [detail ▸], shut by default and remembered. A voice that cannot speak folds nothing (the v2.9 / F9 checks above)
{
  const VC = { ok: true, state: 'HOLD', seq: 1, l1: '▼ 23900 PE · 9 min · +12 pts (₹+8) · prem +8%', l2: 'stop 23,960f / 23,920s', l3: 'why: flow saath', stop_f: lastC + 25, active: [] };
  const fold = { id: 'T5', trade: { id: 'T5', idx: 'NIFTY', k: 23900, ty: 'PE', side: 'BUY', p0: 96.2, entry_t: '10:05:00', exit_t: null },
    view: { headline: 'HOLD', clause: 'behind you: flow', d: -1, E: lastC + 5, G: { px: lastC + 30 }, events: [] }, voice: VC };
  const store = {}, P = boot(store);
  P.panel.render(modelOf(bars.length, { read: READ, plan: PLAN, writers: WRITERS, fold }));
  const hd = P.block('hd'), left = ['decode', 'khil', 'card', 'din', 'abhi', 'bade', 'plan', 'q'].filter((b) => P.block(b) !== '');
  ok(/class="vc HOLD"/.test(P.block('voice')) && left.length === 0 && !/>READ |RIDE|ADHA|class="lg"/.test(hd) && /class="clk"/.test(hd) && /id="bell"/.test(hd)
    && /I'M OUT/.test(P.block('act').replace(/&#39;/g, "'")), 'C5 in a trade, [detail] shut: the voice block, a slim head (clock, bell, feed dots) and I\'M OUT, nothing else: ' + JSON.stringify(left));
  P.click({ act: 'vdet' });
  ok(/>READ LEAN/.test(P.block('hd')) && /SIRF BADE/.test(P.block('bade')) && /FOLD/.test(P.block('plan')) && P.block('din') !== '' && store['ofd.vdet'] === '1',
    'C5 her click opens the one [detail ▾]: READ, KHEL, SIRF BADE, the FOLD board, DIN; the choice is stored');
  const F0 = boot(); F0.panel.render(modelOf(bars.length, { read: READ, plan: PLAN, writers: WRITERS }));
  ok(/>READ LEAN/.test(F0.block('hd')) && /SIRF BADE/.test(F0.block('bade')) && /PLAN/.test(F0.block('plan')), 'C5 flat: the panel is as it was');
}
console.log('');
```

- [ ] **Step 2: Run them and see them fail.**

Run: `node build.mjs --out .baseline/v212-next; OFD_DIST=.baseline/v212-next node test/panel.mjs | grep -E "FAIL|passed"`
Expected:
- `FAIL §5 the head: … no EXPRESSION pill`.
- `FAIL v2.6 2 … ["7 Sep hd","in trade hd"]`: the old head has the pill and the C3 strip now removes it, so the two no longer match.
- `FAIL C5 in a trade, [detail] shut …` (`left` lists `din`, `abhi`, `bade`…).
- The other two C5 checks pass: opened and flat are today's panel.

- [ ] **Step 3: Implement.** In `src/shell/panel.js`, make these replacements.

(1) Replace

```js
 *   NIFTY {KHEL} · {SIZE} · {PREMIUM}          {fut}f | {spot}s   {time}
```

with

```js
 *   NIFTY {KHEL} · {SIZE}          {fut}f | {spot}s   {time}   (C3, 25 Oct: no EXPRESSION pill; C5: in a trade, see render())
```

(2) Replace

```js
  function header(m, X, F) {
```

with

```js
  function header(m, X, F, slim) {
```

(3) Replace

```js
    const prem = rd && rd.expr && rd.expr.word ? ` · <span class="pill">${esc(rd.expr.word)}</span>` : '';
```

with

```js
    // C3 (25 Oct review, A79): no EXPRESSION pill here (a median 65 word changes a day [M]); the §1h log keeps writing
```

(4) Replace

```js
    const ref = X.ref && X.ref.ok ? `ref ✓` : `<span class="am">ref ?</span>`;
```

with

```js
    const ref = X.ref && X.ref.ok ? `ref ✓` : `<span class="am">ref ?</span>`;
    // C5 (25 Oct): in a trade with [detail] shut the head keeps the index, the price, the clock, the bell, the two feed dots and
    // the 15:00 reminder; READ, KHEL, SIZE, ref and the legend wait in the detail
    if (slim) return `<div class="hd"><div class="l1"><span class="idx">${esc((F && F.idx) || idx)}</span><span class="px">${spotP}</span><span class="sp"></span><span class="clk">${esc(clock)}</span>${bell}</div>`
      + `<div class="l2">${dot(tape.state)}GC ${dot(book.state)}TapeMap${practice ? ' · ' + practice : ''}</div></div>`;
```

(5) Replace

```js
${size}${prem}</div>`
```

with

```js
${size}</div>`
```

(6) Replace

```js
title="${vOpen ? 'detail band karo' : 'FOLD board · engine · HOLD v2'}"
```

with

```js
title="${vOpen ? 'detail band karo' : 'READ · DECODE · BADE · FOLD · DIN'}"
```

(7) Replace

```js
    put('hd', header(m, X, F));
```

with

```js
    // C5 (25 Oct review, TRADER F15): in a trade with the voice speaking the panel is the voice block (l1-l5) and the chart's
    // lines; READ, KHEL, SIZE, DECODE, khilaaf, SIRF BADE, the FOLD board, JAGAH, the 09:45 card, DIN, ABHI and ? wait under its
    // one [detail ▸] (vOpen: shut by default, remembered). A voice that cannot speak folds nothing: the board is all she has
    const vcOk = X.inTrade && X.fold && X.fold.voice && X.fold.voice.ok, shut = !!vcOk && !vOpen;   // v2.9: the FOLD board is the voice's detail (F7: X.fold)
    put('hd', header(m, X, F, shut));
```

The `vcOk` expression is Phase 2 Task 3's. If Phase 2 left a different one, use that one here.

(8) Replace

```js
    put('decode', dec ? decodeBlock(dec) : '');
```

with

```js
    put('decode', dec && !shut ? decodeBlock(dec) : '');
```

(9) Replace

```js
    put('khil', kh.length ? blk(
```

with

```js
    put('khil', kh.length && !shut ? blk(
```

(10) Replace

```js
    put('card', dayCard(X));
    put('din', din(X, F));
    put('abhi', abhi(X));
    put('bade', bade(X, bOpen ? 6 : 3));
```

with

```js
    put('card', shut ? '' : dayCard(X));
    put('din', shut ? '' : din(X, F));
    put('abhi', shut ? '' : abhi(X));
    put('bade', shut ? '' : bade(X, bOpen ? 6 : 3));
```

(11) Replace (as Phase 2 Task 3 left it)

```js
    const vcOk = X.inTrade && X.fold && X.fold.voice && X.fold.voice.ok;   // v2.9: the FOLD board is the voice's detail (F7: X.fold)
    put('plan', (vcOk && !vOpen ? '' : (vcOk ? mapDetail(X.fold.voice) : '') + planBlock(X, F)) + jagah(X.read));
```

with

```js
    put('plan', shut ? '' : (vcOk ? mapDetail(X.fold.voice) : '') + planBlock(X, F) + jagah(X.read));   // C5: JAGAH waits in the detail too
```

(12) Replace

```js
    put('q', qBlock(X, F, m));
```

with

```js
    put('q', shut ? '' : qBlock(X, F, m));
```

- [ ] **Step 4: Run all six suites and see them pass.**

Run: `node build.mjs --out .baseline/v212-next; for s in fit engine shell overlay panel decoder; do OFD_DIST=.baseline/v212-next node test/$s.mjs | tail -1; done`
Expected:
- `0 failed` on all six;
- panel **106** (+3), the others unchanged.
- `grep -n "rd.expr" src/shell/panel.js` prints nothing.

---

### Task 10: The Float detail: no T1, no inval (C6)

**Touches a Phase-2 file (`pro/Desk.tsx`, as Phase 2 Task 5 left `:134`): re-verify the anchor.**

**Files:**
- Modify: `ui-v2/src/pro/Desk.tsx`:
  - `:117`: `lv`;
  - `:133-136`: the T1 cell, plus Phase 2's three inval / stop lines.
- Test: `tsc`, `vite build`, render check.

**Interfaces:**
- The `fl` row keeps the reversal count and `line2`.
- When the voice cannot speak it keeps Phase 2's `stop: could not check — <why>` (F9). It never shows a level in place of the voice's.

**Can affect:** the Float's [detail] (`FloatBody`) and pro.html's in-trade block.

**Untouched:**
- the voice's l2 (the one stop) and l5 (PULLBACK);
- `/api/validate`'s fields (read by nothing here now);
- the prompts and acks.

- [ ] **Step 1: The failing check.**

Run: `grep -nE "lv\?\.t1|inval" ui-v2/src/pro/Desk.tsx`
Expected today: 2–3 lines.

- [ ] **Step 2: Implement.** In `ui-v2/src/pro/Desk.tsx`, replace

```tsx
  const p = v?.prem, lv = live?.level, rv = live?.reversal
```

with

```tsx
  const p = v?.prem, rv = live?.reversal
```

and replace (Phase 2's text)

```tsx
        <span>T1 {lv?.t1 != null ? lv.t1_hit ? <b className="up">touched</b> : <><b>{pts(lv.to_t1)}</b> pts</> : <Abs text={cc(lv?.t1_why, 'no T1')} />}</span>
        {/* F9 (25 Oct): no stop but the voice's -- when it cannot speak this says why, never validate's inval in its place */}
        <span>{r?.voice?.ok ? <>inval {lv?.inval != null ? <><b className={(lv.to_inval ?? 1) <= 0 ? 'dn' : ''}>{pts(lv.to_inval)}</b> pts</> : <Abs text={cc(lv?.inval_why, 'no invalidation')} />}</>
          : <>stop: <Abs text={cc(r?.voice?.why ?? (r && !r.ok ? r.why : null), 'TapeMap ki voice nahi aayi')} /></>}</span>
```

with

```tsx
        {/* C6 (25 Oct review): no T1 and no inval here -- the voice's l2 is the one stop and its l5 PULLBACK the one level
            ahead; with the voice down this says why (F9), never a level in its place */}
        {!r?.voice?.ok && <span>stop: <Abs text={cc(r?.voice?.why ?? (r && !r.ok ? r.why : null), 'TapeMap ki voice nahi aayi')} /></span>}
```

- [ ] **Step 3: Pass.**

Run: the Step 1 grep. Expected: no line.
Run: `./node_modules/.bin/tsc --noEmit -p . && npx vite build`. Expected: clean; `✓ built`.

- [ ] **Step 4: Render check (controller, light, one screenshot).** On `/pro.html?fixture=1&state=in&float=x`, as in Phase 2 Task 5 Step 5:
  - the row after the reversal count shows no `T1` and no `inval`;
  - the fixture carries no voice, so it reads `stop: could not check — TapeMap ki voice nahi aayi`.

---

### Task 11: The dead hold / board UI and its three routes (C8)

**Touches Phase-2 files (`hold/store.ts`, `server.py`): re-verify the anchors.**

**Files:**
- Delete (`git rm`): `ui-v2/src/hold/HoldTab.tsx` (635 lines), `hold/MarketNow.tsx` (104), `hold/HoldWindow.tsx` (331), `board/BoardRev3.tsx` (892).
- Modify:
  - `ui-v2/src/App.tsx`: the BoardRev3 import goes; `useBoardGlance` and `GlanceRead` move here, unchanged.
  - `ui-v2/src/pro/api.ts`: the `Trade` / `Voice` types move here from `HoldWindow`.
  - `ui-v2/src/hold/parts.tsx`: trimmed to `Ico`, `Guard` and the CSS import, the only pieces a survivor (`Float.tsx`) imports.
  - `ui-v2/src/hold/store.ts`: trimmed to `TIMEOUT_MS`, `j()` and `tone()`. The 15 s poller that called `/api/hold?id=` goes with the windows it fed.
  - `server.py` (`GET /api/hold`): the `?id=`, `/check` and `/expr` dispatch go.
  - `test_hold_route.py`: `_get` calls the kept functions directly, plus one test.
- Grep evidence, 25 Oct [M]. The three routes' callers in TapeMap's `ui-v2/src` + `ui-v2/public`, in the extension's `src` + `test`, and in `operator mode/paperdesk` are:
  - `hold/HoldTab.tsx:99,136` and `hold/store.ts:59`, all deleted here;
  - none in the extension, paperdesk, `eod_capture.*` or `tools/`.

**Interfaces:**
- `GET /api/hold?…`, `/api/hold/check?…` and `/api/hold/expr?…` answer `{ok: False, why: "not served: <path> (cut 25 Oct, review C8)"}`.
- `/api/hold/trades` and `/api/hold/sigma` are unchanged.
- **Kept on purpose** (spec §2 "Kept on purpose"; the rev 5 loop's signed §1e/§1g/§1h population is judged ~6 Nov):
  - `_hold_reply`, `_hold_check`, `_expr_reply` and their helpers, now unreachable;
  - `hold.py`, `plan.py`, `validate.py`, `expression.py`;
  - `_hold_loop`.
- The 23 tests that read them through HTTP keep running through the `_get` shim. None is deleted.

**Can affect:** nothing on her screens (the deleted UI was unmounted [M]); the Board tab's GlanceBar line (moved code, same behaviour).

**Untouched:**
- the Board (`board/Board.tsx`);
- the Float (`Guard`, `Ico`, `hold.css`);
- `pro/api.ts`'s poller;
- `trade/engine.ts`'s `j`;
- the rev 5 loop and its logs.

- [ ] **Step 1: The failing test.** In `test_hold_route.py`, replace (as Task 1 left it)

```python
import io
import json
import os
```

with

```python
import io
import json
import os
from urllib.parse import parse_qs, urlsplit
```

Replace

```python
def _get(path, poller):
    cap = _Cap(path, poller=poller)
    server.Handler.do_GET(cap)
    return cap.sent
```

with

```python
_CUT = ("/api/hold", "/api/hold/check", "/api/hold/expr")


def _get(path, poller):
    """25 Oct review C8: /api/hold?id=, /api/hold/check and /api/hold/expr are no longer served (their one caller, the hold/*
    UI, is deleted). The functions behind them stay -- the rev 5 loop's signed §1e/§1g/§1h population is judged ~6 Nov --
    so the tests that read them call them as the routes did, through the same JSON."""
    u = urlsplit(path)
    cap = _Cap(path, poller=poller)
    if u.path not in _CUT:
        server.Handler.do_GET(cap)
        return cap.sent
    q = parse_qs(u.query)
    try:
        out = (server._hold_check(poller, q, cap.payloads) if u.path == "/api/hold/check"
               else server._expr_reply(poller, cap.payloads, cap._idx()) if u.path == "/api/hold/expr"
               else server._hold_reply(poller, q))
    except Exception as e:                   # as the route did: a bad read is a why
        out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
    return json.loads(json.dumps(out, default=str))
```

Append after the Task 1 test (replace its last line)

```python
    assert away["ok"] is False and "another site" in away["why"] and bad["ok"] is False and late["ok"] is False and len(rows()) == 2
```

with

```python
    assert away["ok"] is False and "another site" in away["why"] and bad["ok"] is False and late["ok"] is False and len(rows()) == 2


def test_the_cut_hold_routes_are_not_served():
    """25 Oct review C8 (DEV-FACES F14, F27): /api/hold?id=, /api/hold/check (VALIDATE rev 2) and /api/hold/expr had one caller,
    the unmounted hold/* UI, now deleted. The routes answer `not served`; the functions behind them stay for the rev 5
    judgement, and this file's tests call them directly (_get)."""
    for path in ("/api/hold?id=NIFTY-23200PE-long-122030", "/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100",
                 "/api/hold/expr?idx=NIFTY"):
        cap = _Cap(path, poller=None)
        server.Handler.do_GET(cap)
        assert cap.sent["ok"] is False and cap.sent["why"].startswith("not served"), path
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_hold_route.py test_expression_route.py test_fold_live.py`
Expected:
- `test_the_cut_hold_routes_are_not_served` FAILS: today `/api/hold?id=` answers a read, and `ok` is not False or `why` is not "not served".
- Every other test passes, through the shim.

- [ ] **Step 3: Implement the server half.** In `server.py`, replace

```python
            # THE HOLD / FOLD WINDOW (hold.py; docs/hold/PREREG-merged.md rev 4):
            # /api/hold?id= a marked trade, or ?idx=&k=&side=&role=&t0=&p0=&qty=
            # [&asof=HH:MM][&rows=1]; /api/hold/trades today's marked trades.
            # GET only here.
```

with

```python
            # THE HOLD DOOR's reads: /api/hold/trades (today's marked trades) and /api/hold/sigma. Since 25 Oct (review C8)
            # /api/hold?id=, /api/hold/check and /api/hold/expr are not served: their one caller, the hold/* UI, is deleted.
            # GET only here.
```

Replace

```python
                elif path == "/api/hold/check":
                    out = _hold_check(self.poller, q, self.payloads)
                elif path == "/api/hold/expr":
                    out = _expr_reply(self.poller, self.payloads, self._idx())
                elif path == "/api/hold/sigma":
```

with

```python
                elif path == "/api/hold/sigma":
```

Run: `python "$CUT" server.py "                    out = _hold_reply(self.poller, q)" "            except Exception as e:"`. It deletes the old `else` body, 12 lines.

Then replace

```python
                else:
            except Exception as e:
```

with

```python
                else:
                    # C8 (25 Oct review): not served. _hold_reply / _hold_check / _expr_reply stay for the rev 5 judgement (~6 Nov)
                    out = {"ok": False, "why": f"not served: {path} (cut 25 Oct, review C8)"}
            except Exception as e:
```

- [ ] **Step 4: Implement the ui-v2 half.** From `tapemap/ui-v2/src`, in order.

(1) Run:

```bash
python "$CUT" hold/store.ts "// THE ONE HOLD POLLER." "/** fetch with an 8 s abort"
python "$CUT" hold/store.ts "export const why = (e: unknown)" "// one tone on a transition into FOLD"
python "$CUT" hold/store.ts "// A52 the ladder's sounds:" "EOF"
python "$CUT" hold/parts.tsx "// The pieces the Validate tab and the floating hold window share" "const PATHS = {"
python "$CUT" hold/parts.tsx "export const inr = (x: number" "/** One broken render must never take the app"
git rm hold/HoldTab.tsx hold/MarketNow.tsx hold/HoldWindow.tsx board/BoardRev3.tsx
```

(2) In `hold/store.ts`, replace

```ts
/** fetch with an 8 s abort
```

with

```ts
// The two fetch pieces the faces share since the 25 Oct review (C8): j(), an 8 s bound on every fetch (pro/api.ts,
// trade/engine.ts, data.ts's TIMEOUT_MS), and tone(). The hold poller that lived here (/api/hold?id=, for the deleted hold/*
// windows) is gone with its route.
export const TIMEOUT_MS = 8000   // the one fetch bound: j() below, and data.ts's 5 s poll (25 Oct review F10)

/** fetch with an 8 s abort
```

(3) In `hold/parts.tsx`, replace

```tsx
const PATHS = {
```

with

```tsx
// The two pieces the floating window (pro/Float.tsx) takes from here since the 25 Oct review (C8): the icons and the error
// guard. The rest went with the hold/* windows. Styles: ./hold.css (the Float's .hv classes).
import { Component } from 'react'
import type { ReactNode } from 'react'
import './hold.css'

const PATHS = {
```

(4) In `pro/api.ts`, replace

```ts
import type { Trade, Voice } from '../hold/HoldWindow'
export type { Trade }
```

with

```ts
// her trade and THE ONE VOICE (A52, server voice.py): the shapes that lived in hold/HoldWindow.tsx until the 25 Oct review (C8)
export type Trade = { id: string; idx: string; k: number; side: 'CE' | 'PE'; role: 'long' | 'short'; t0: string; p0: number | null; qty: number
                      exit_t: string | null; exit_t_broker?: string | null; src?: string }
export type Voice = { ok: boolean; why?: string; state: 'HOLD' | 'TIGHTEN' | 'WARN' | 'EXIT'; seq: number; l1: string; l2: string; l3: string
                      trig_t?: string | null; note?: string; active?: { t: string; state: string; reason: string }[]
                      l4?: string; l5?: string; detail?: { text: string; tip?: string | null }[]; map_why?: string }   // the TRADE MAP (trademap.py)
```

(5) In `App.tsx`, replace

```tsx
// BOARD rev 3 (docs/mockups/board-chess-rev3-2026-09-24-notes.md).
import BoardRev3, { useBoardGlance } from './board/BoardRev3'
import type { GlanceRead } from './board/BoardRev3'
// THE BOARD, overhaul 2026-10-03 (docs/board/BOARD-OVERHAUL-2026-10-03.md). BoardRev3 stays on disk, unmounted.
```

with

```tsx
// THE BOARD, overhaul 2026-10-03 (docs/board/BOARD-OVERHAUL-2026-10-03.md).
```

and replace

```tsx
import { glossOf, pillText, dirText } from './trade/hinglish'
```

with

```tsx
import { glossOf, pillText, dirText } from './trade/hinglish'

// THE GlanceBar's one line per index on the Board tab, off /api/board's headline. Moved here from board/BoardRev3.tsx, the
// unmounted rev 3 board, when it was deleted (25 Oct review C8); unchanged: one gentle poll of all three, only while the Board
// tab shows; a failed poll keeps the last good line for that index and retries.
type GlanceRead = { line: string; title: string }
type BoardHead = { ok: boolean; why?: string; idx?: string; asof?: string | null; spot?: number
                   headline?: { text: string; fold: { k: number; side: string; t: string } | null } }
const GLANCE_CC = 'could not check — '
function glanceLine(b: BoardHead | null): GlanceRead {
  const f0 = (x: number) => Math.round(x).toLocaleString('en-IN')
  if (!b) return { line: GLANCE_CC + 'the backend did not answer', title: '' }
  if (!b.ok || typeof b.spot !== 'number' || !Number.isFinite(b.spot))
    return { line: GLANCE_CC + String(b.why ?? 'no board read yet').replace(/^could not check — /, ''), title: b.why ?? '' }
  const f = b.headline?.fold
  return {
    // "writers left", never "fold": on the DESK, FOLD means get out of your trade.
    line: `idx ${f0(b.spot)} · ${f ? `${f.side} writers left ${f0(f.k)} ${f.t}` : 'no writers leaving near spot'}`,
    title: `${b.idx} at ${b.asof} (the last finished minute) [I]: ${b.headline?.text ?? ''}`,
  }
}
function useBoardGlance(on: boolean): Partial<Record<IndexKey, GlanceRead>> {
  const [reads, setReads] = useState<Partial<Record<IndexKey, GlanceRead>>>({})
  useEffect(() => {
    if (!on) return
    let alive = true, retry = 0
    const load = async () => {
      // one after another, not a burst: the dev proxy drops the odd request
      // when several land at once (a 502 with an empty body, measured 23:20)
      let failed = false
      for (const k of ['NIFTY', 'BANKNIFTY', 'SENSEX'] as IndexKey[]) {
        let r: GlanceRead, bad = false
        try {
          const res = await fetch(`/api/board?idx=${k}`)
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          r = glanceLine((await res.json()) as BoardHead)
        } catch { r = glanceLine(null); bad = failed = true }
        if (!alive) return
        // a failed poll keeps the last good line for that index, and retries soon
        setReads((p) => (bad && p[k] ? p : { ...p, [k]: r }))
      }
      if (failed && alive) retry = window.setTimeout(load, 5000)
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 60000)
    return () => { alive = false; window.clearInterval(id); window.clearTimeout(retry) }
  }, [on])
  return reads
}
```

- [ ] **Step 5: Run everything touched and see it pass.**

Run (TapeMap): `python -m pytest -q test_hold_route.py test_expression_route.py test_fold_live.py test_hold.py`
Expected: all pass, `test_the_cut_hold_routes_are_not_served` included.

Run (ui-v2): `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean; `✓ built`.

Run: `grep -rnE "HoldWindow|HoldTab|MarketNow|BoardRev3|useHold|/api/hold\?id|/api/hold/check|/api/hold/expr" ui-v2/src ui-v2/public; wc -l ui-v2/src/hold/store.ts ui-v2/src/hold/parts.tsx`
Expected: exactly three lines, the moved-code comments that name what was deleted (`App.tsx` "board/BoardRev3.tsx", `api.ts` "hold/HoldWindow.tsx", `store.ts` "/api/hold?id="); about 35 and 45 lines.

- [ ] **Step 6: Render check (controller, light, one screenshot).**
  - On the Board tab, each GlanceBar cell carries its line as before: `idx …`, or `could not check — …` with no server.
  - On `/?fixture=1` with Phase 2 Task 4's snippet, the Float renders (Guard and icons intact).

---

### Task 12: console.html and /api/senses (C9)

**Touches a Phase-2 file (`server.py`): re-verify the anchor.**

**Files:**
- Delete (`git rm`): `ui/console.html`, and `ui/fmt.js` and `ui/theme.css` (used only by `console.html` [M: grep]). Keep `ui/stop.ico` and `ui/tapemap.ico`: her shortcuts use them.
- Modify: `server.py`: the `/api/senses` branch of `do_GET`, `:5524-5596`.
- Modify: `CLAUDE.md` (`:43`, `:96`, `:98`) and `START-HERE.md` (`:98`).
- Callers [M, 25 Oct]:
  - `/api/senses`: only `ui/console.html:464`, plus docs and history in `.superpowers/` and the extension's `.superpowers/` / `docs/`;
  - `console.html`: docs only.
  - The extension's `README.md` names neither (grep 0). Spec §6 is wrong there, and it needs no edit.

**Interfaces:** `GET /api/senses` falls through to static serving, a 404.

**Can affect:** nothing she uses (ui-v2 never called it).

**Untouched:**
- the senses loop and its forward log (`data/senses/`);
- `_regime_engine_read` / `_walls_holding` (`server.py:1046`, `:5874` read them);
- `/api/health`;
- the root redirect to 5173.

- [ ] **Step 1: The failing check.**

Run: `grep -c 'startswith("/api/senses")' server.py; ls ui`
Expected today: `1`; `console.html fmt.js stop.ico tapemap.ico theme.css`.

- [ ] **Step 2: Implement.**

Run (TapeMap root):

```bash
python "$CUT" server.py '        elif self.path.startswith("/api/senses"):' '        elif self.path.startswith("/api/reader"):'
git rm ui/console.html ui/fmt.js ui/theme.css
```

Expected: about 73 lines deleted.

In `CLAUDE.md`, replace

```
  `band_rotation.py`, the zone machine, `data/trigger_log.jsonl`,
  `/console.html`. START-HERE.md is its document.
```

with

```
  `band_rotation.py`, the zone machine, `data/trigger_log.jsonl`.
  START-HERE.md is its document. (`/console.html` was cut 25 Oct, review C9.)
```

and replace

```
Screens: ui-v2 on `http://127.0.0.1:5173/` (the live UI; `/` redirects there) ·
`/console.html` (the tape detectors).
APIs: `/api/surface` · `/api/drag` (both read by her PaperDesk extension) ·
`/api/chain` · `/api/senses` · `/api/vpin` · `/api/oiflow` · `/api/warmap` ·
```

with

```
Screens: ui-v2 on `http://127.0.0.1:5173/` (the live UI; `/` redirects there).
APIs: `/api/surface` · `/api/drag` (both read by her PaperDesk extension) ·
`/api/chain` · `/api/vpin` · `/api/oiflow` · `/api/warmap` ·
```

In `START-HERE.md`, replace

```
| screen | `/console.html`, the Kite overlay | `/desk.html` |
```

with

```
| screen | ui-v2 on 5173 and the GoCharting panel (`/console.html` cut 25 Oct) | `/desk.html` (deleted 28 Sep) |
```

- [ ] **Step 3: Pass.**

Run: `grep -c 'startswith("/api/senses")' server.py; ls ui; grep -n "console.html\|/api/senses" CLAUDE.md START-HERE.md`
Expected: `0`; `stop.ico tapemap.ico`; only the two "cut 25 Oct" mentions.

Run: `python -m pytest -q test_senses_api.py test_senses.py test_upstox_only.py test_board.py`
Expected: all pass. No test called the route [M: grep].

---

### Task 13: start.bat goes; the default broker is upstox (C10)

**Touches a Phase-2 file (`server.py`, `_backfill_vpin`): re-verify the anchor.**

**Files:**
- Delete (`git rm`): `start.bat`. It started `python server.py live` with no `TAPEMAP_BROKER` (Dhan, dead since 5 Aug).
- Modify:
  - `chain_live.py:142-150` (`_broker`);
  - `server.py:6035` (`_backfill_vpin`).
- Modify (tests):
  - `conftest.py` (the env);
  - `test_broker_switch.py`;
  - `test_upstox_only.py`;
  - `test_contract_upstox.py`.
- Modify: `START-HERE.md:245`.

**Spec gap, resolved.** The Dhan default lives in **two** places: `chain_live.py:150` and `server.py:6035`. The second reads the env itself, so a no-env server on upstox would still skip the VPIN backfill. It now calls `chain_live._broker()`, so there is one default.

Four tests pin the unset default as Dhan, and the rest of the suite ran on Dhan's mocked path because the env was unset. So conftest now pins `TAPEMAP_BROKER=dhan` for every test. The tests of the unset default `delenv` it and assert upstox. The two Dhan-path tests that used "unset" now choose `dhan` by name.

**Interfaces:**
- `chain_live._broker()` returns `upstox` when `TAPEMAP_BROKER` is unset. `dhan` selects the documented fallback.
- Anything not exactly `upstox` (trimmed, lower-cased) is still not upstox, as today.

**Can affect:**
- a server started without the env: on Upstox now, its `/api/health` broker, and the VPIN backfill attempted;
- `start-v2.bat`'s reuse check, which passes such a server now.

**Untouched:**
- the Dhan code (`dhan_*`, `.dhan_token`, `TokenCapture`);
- `start-v2.bat` (it sets upstox itself; its "started without TAPEMAP_BROKER, so it is on Dhan" hint is now half-true and is left for her to judge, A87);
- `eod_capture.bat`.

- [ ] **Step 1: Write the failing tests.**

In `conftest.py`, replace

```python
    for target, name in PATH_PATHS.items():
        monkeypatch.setattr(target, tmp_path / name)
```

with

```python
    for target, name in PATH_PATHS.items():
        monkeypatch.setattr(target, tmp_path / name)
    # C10 (25 Oct review): the shipped default is upstox; the suite keeps running on the mocked Dhan path it was written on,
    # whatever the shell has set. A test of the unset default delenv's it (test_broker_switch, test_upstox_only)
    monkeypatch.setenv("TAPEMAP_BROKER", "dhan")
```

In `test_broker_switch.py`, replace

```python
def test_setting_nothing_keeps_dhan():
    """The behaviour that has been running stays the behaviour that runs."""
    assert _with(None) == "dhan"
```

with

```python
def test_setting_nothing_is_upstox():
    """25 Oct review C10: Dhan's Data API lapsed 2026-08-05 and the one launcher that set nothing (start.bat) is deleted, so
    setting nothing is the live source. Dhan is chosen by name."""
    assert _with(None) == "upstox" and _with("dhan") == "dhan"
```

In `test_upstox_only.py`, replace

```python
    """Select the broker for one test. `None` means "leave it unset", which
    is the shipped default and must stay Dhan."""
```

with

```python
    """Select the broker for one test. `None` means "leave it unset", which
    is the shipped default: upstox since 25 Oct (review C10)."""
```

Replace

```python
    _broker(monkeypatch, None)                    # unset == dhan
```

with

```python
    _broker(monkeypatch, "dhan")                  # the Dhan fallback, chosen by name (C10)
```

Replace

```python
    monkeypatch.chdir(tmp_path)
    _broker(monkeypatch, None)
    with pytest.raises(FileNotFoundError):
```

with

```python
    monkeypatch.chdir(tmp_path)
    _broker(monkeypatch, "dhan")
    with pytest.raises(FileNotFoundError):
```

Replace

```python
def test_health_says_dhan_when_nothing_selected_it(monkeypatch):
    """It must report what is TRUE, not what the launcher intended -- the
    launcher's whole check depends on this being able to say "dhan"."""
    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    assert _get("/api/health")["broker"] == "dhan"
```

with

```python
def test_health_says_upstox_when_nothing_selected_it(monkeypatch):
    """It must report what is TRUE, not what the launcher intended -- the
    launcher's whole check depends on it. Since 25 Oct (review C10) setting
    nothing is upstox; dhan is said only when chosen."""
    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    assert _get("/api/health")["broker"] == "upstox"
    monkeypatch.setenv("TAPEMAP_BROKER", "dhan")
    assert _get("/api/health")["broker"] == "dhan"
```

In `test_contract_upstox.py`, replace

```python
def test_default_broker_still_builds_the_contract_through_dhan(monkeypatch):
    """Setting nothing keeps the behaviour that has been running -- including
    the Dhan token gate and the Dhan expiry resolve."""
    import chain_live

    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
```

with

```python
def test_the_dhan_fallback_still_builds_the_contract_through_dhan(monkeypatch):
    """Dhan chosen by name keeps its behaviour -- including the Dhan token
    gate and the Dhan expiry resolve (the documented fallback, C10)."""
    import chain_live

    monkeypatch.setenv("TAPEMAP_BROKER", "dhan")
```

and replace

```python
def test_an_expired_dhan_token_still_fails_loudly(monkeypatch):
    import chain_live

    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
```

with

```python
def test_an_expired_dhan_token_still_fails_loudly(monkeypatch):
    import chain_live

    monkeypatch.setenv("TAPEMAP_BROKER", "dhan")
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_broker_switch.py test_upstox_only.py test_contract_upstox.py`
Expected:
- `test_setting_nothing_is_upstox` FAILS: `assert 'dhan' == 'upstox'`.
- `test_health_says_upstox_when_nothing_selected_it` FAILS: `assert 'dhan' == 'upstox'`.
- The rest pass.

- [ ] **Step 3: Implement.**

In `chain_live.py`, replace

```python
def _broker():
    """Which data source the live poller uses. Dhan unless told otherwise.

    `TAPEMAP_BROKER=upstox` switches the chain to the Upstox socket. Default
    is dhan so that setting nothing keeps the behaviour that has been running,
    and so a missing or misspelled env var can never silently move the tool
    onto a different broker mid-session.
    """
    return os.environ.get("TAPEMAP_BROKER", "dhan").strip().lower()
```

with

```python
def _broker():
    """Which data source the live poller uses. Upstox unless told otherwise
    (25 Oct review C10: Dhan's Data API lapsed 2026-08-05, and start.bat, the
    one launcher that set nothing, is deleted).

    `TAPEMAP_BROKER=dhan` selects the documented Dhan fallback. Anything that
    is not exactly "upstox" after trimming and lower-casing is NOT upstox, so a
    misspelling never silently becomes the live socket.
    """
    return os.environ.get("TAPEMAP_BROKER", "upstox").strip().lower()
```

In `server.py` (`_backfill_vpin`), replace

```python
    if os.environ.get("TAPEMAP_BROKER", "dhan").strip().lower() != "upstox":
```

with

```python
    from chain_live import _broker
    if _broker() != "upstox":                     # C10 (25 Oct): the one broker default, chain_live._broker's
```

Run: `git rm start.bat`

In `START-HERE.md`, replace

```
start.bat                 # legacy: brings it up on DHAN (dead source) — avoid
```

with

```
                          # (start.bat, the Dhan launcher, was deleted 25 Oct; the default broker is upstox)
```

- [ ] **Step 4: Run and see them pass.**

Run: `python -m pytest -q test_broker_switch.py test_upstox_only.py test_contract_upstox.py test_chainside_seed.py test_live.py`
Expected: all pass. Drop a file the tree does not have.

Run: `grep -rn '"TAPEMAP_BROKER", "dhan"' --include=*.py . ; ls start.bat`
Expected: no line; `No such file`.

---

### Task 14: LOOK HERE, the August logs, the Figma boilerplate, fs2 (C7 + C11)

**Touches a Phase-2 file (`src/shell/panel.js`): re-verify the anchor.**

**Files:**
- Modify: `ui-v2/src/App.tsx` (`IndexCell`, `:225-262`): C7.
- Modify: `ui-v2/src/index.css` (`:34-48`): the `trending-glow` rules, C2's leftover.
- Recycle Bin (untracked and gitignored [M: `git check-ignore`]): `_srv.err`, `_srv.log`, `_srv_restart.log`, `_srv_restart2.log`, `tapemap-8765.log`, all of 14–21 Aug. **Never `tapemap.log*`**: the live rotating log.
- Delete (`git rm`): `ui-v2/AGENTS.md` (Figma Make boilerplate), and `ui-v2/CLAUDE.md`, whose whole text is `@AGENTS.md` and would dangle.
- Modify: `src/shell/panel.js:115-118`, the unused `fs2`. The overlay's `fs2` is `v2.js`'s, which stays.

**Interfaces:** none. An index cell no longer glows or wears LOOK HERE; the active cell keeps its border.

**Can affect:** the GlanceBar cells.

**Untouched:**
- `data.ts`'s `highlight` (still computed, read by nothing now: A87);
- `trade/legs.tsx`'s shadow `LOOK HERE · SHADOW` (not the GlanceBar);
- `xindex_live`'s LOOK HERE log;
- `v2.js` `fs2`.

- [ ] **Step 1: The failing check.**

Run: `grep -cE "LOOK HERE|trending-glow" ui-v2/src/App.tsx ui-v2/src/index.css; grep -c "const fs2" "/c/Users/kaam/Desktop/Go charting/orderflow-desk/src/shell/panel.js"`
Expected today: `App.tsx:2`, `index.css:3` (Task 8 already took the glass block's mention); `1`.

- [ ] **Step 2: Implement.**

In `ui-v2/src/App.tsx`, replace

```tsx
      className={data.highlight ? 'trending-glow' : ''}
      style={{
        // #1B2130 / #141926 were the dark palette's inset and card, inlined.
        backgroundColor: active ? pal.inset : pal.card,
        border: data.highlight
          ? `1px solid ${pal.accent}`
          : active
          ? `1px solid ${wash(pal.ink, 0.12)}`
          : `1px solid ${pal.border}`,
```

with

```tsx
      style={{
        // #1B2130 / #141926 were the dark palette's inset and card, inlined.
        backgroundColor: active ? pal.inset : pal.card,
        // C7 (25 Oct review): no LOOK HERE and no glow -- the active cell is the only one marked
        border: active ? `1px solid ${wash(pal.ink, 0.12)}` : `1px solid ${pal.border}`,
```

then run, from `tapemap/ui-v2/src`: `python "$CUT" App.tsx "      {data.highlight && (" "      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>"`. It deletes 18 lines.

In `ui-v2/src/index.css`, replace

```css
/* brass, not purple — the glow marks structure, never direction */
@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 12px 2px rgba(var(--page-brass),0.22); }
  50% { box-shadow: 0 0 24px 6px rgba(var(--page-brass),0.40); }
}

.live-dot { animation: pulse-live 1.8s ease-in-out infinite; }
.trending-glow { animation: glow-pulse 2.4s ease-in-out infinite; }

/* The dot and the glow stay visible when motion is off — only the pulse goes.
   The glow freezes at its brighter keyframe so the marker still reads. */
@media (prefers-reduced-motion: reduce) {
  .live-dot, .trending-glow { animation: none; }
  .trending-glow { box-shadow: 0 0 24px 6px rgba(var(--page-brass), 0.40); }
}
```

with

```css
.live-dot { animation: pulse-live 1.8s ease-in-out infinite; }

/* The dot stays visible when motion is off -- only the pulse goes. (C7, 25 Oct: the LOOK HERE glow is cut.) */
@media (prefers-reduced-motion: reduce) {
  .live-dot { animation: none; }
}
```

The August logs go to the Recycle Bin (PowerShell; recoverable, never a hard delete):

```powershell
Add-Type -AssemblyName Microsoft.VisualBasic
foreach ($f in '_srv.err','_srv.log','_srv_restart.log','_srv_restart2.log','tapemap-8765.log') { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile((Join-Path 'C:\Users\kaam\Desktop\operator mode\tapemap' $f), 'OnlyErrorDialogs', 'SendToRecycleBin') }
```

Run (TapeMap root): `git rm ui-v2/AGENTS.md ui-v2/CLAUDE.md`

In `src/shell/panel.js`, replace

```js
// fut | spot: fut-native levels say "≈ spot" (tens), strike-native levels are exact in spot; a bad basis prints no spot
const fs2 = (p, b, strike) => { const ok = b && b.ok && b.v != null;
  if (strike) return ok ? `${pxs(p)}s | ≈${pxs(Math.round((p + b.v) / 10) * 10)}f` : `${pxs(p)}s`;
  return ok ? `${pxs(p)}f | ≈${pxs(Math.round((p - b.v) / 10) * 10)}s` : `${pxs(p)}f`; };
const CC = (why) =>
```

with

```js
const CC = (why) =>
```

- [ ] **Step 3: Pass.**

Run: Step 1's greps. Expected: `0`, `0`; `0`.

Run: `ls _srv* tapemap-8765.log ui-v2/AGENTS.md ui-v2/CLAUDE.md 2>&1 | head -3; ls tapemap.log`
Expected: `No such file` for each cut file; `tapemap.log` still there.

Run (ui-v2): `./node_modules/.bin/tsc --noEmit -p . && npx vite build`. Expected: clean; `✓ built`.

Run (extension): `node build.mjs --out .baseline/v212-next; for s in fit engine shell overlay panel decoder; do OFD_DIST=.baseline/v212-next node test/$s.mjs | tail -1; done`. Expected: `0 failed` on all six (panel 106).

---

### C12, deferred: needs Mary

**Not planned.** The user's rule applies: "If C12 … touches a registered rule, mark it DEFER: needs Mary". The spec's premise is wrong against the code.

- **`trap_log` is NOT the only reader of `data/senses/`.**
  - `senses.restore_sweeps` (`server.py:665`) streams today's raw sweep rows back on every start after the open. It seeds the ring that `signals._depth_vote` reads (`server.py:1065`).
  - That ring is one of the four votes upstream of the §1d gate's beep (`signals.votes` → `gate_sound`).
  - Writing only `trap_log`'s per-minute sums would leave every late start's DEPTH vote at "no sweep rows" again. That reverses the anytime-start fix of 18 Sep.
- **Measured on 23 Oct [M]:**
  - 1,004,241 rows / 275.6 MB a day;
  - `det == "sweep"` rows: 689,737 / 192.3 MB;
  - the three `-FUT` sweep rows: 20,866 / 5.8 MB. These are exactly the rows `trap_log`'s byte filter keeps; 0 other rows pass it.
- **Two options for her** (NOTEPAD A86, Task 15):
  - **(A)** Write only `det == "sweep"` rows: −83 MB a day, with both readers byte-identical. Neither absorption nor pull rows have a reader [M: grep].
  - **(B)** Write only the `-FUT` sweep rows: −270 MB a day, and `trap_log` is identical. But a late start's restored ring then holds more of the morning's FUT sweeps, so a DEPTH vote that read "no sweep rows" may read measured: a signal input moves on restart days.
- The past raw files stay as they are, under either option.

---

### Task 15: Phase 4 — release 0.5.12, verify, record, commit

**Touches Phase-2 files (`recorder.js`, `v2.js`, `manifest.src.json`, `V2-BUILD-REPORT.md`, `CLAUDE.md`, `NOTEPAD.md`): re-verify the anchors.**

**Files:**
- Modify (extension): `manifest.src.json:4`, `src/shell/recorder.js:39`, `src/engine/v2.js:12`, `docs/V2-BUILD-REPORT.md` (append).
- Modify (TapeMap): `docs/live/NOTEPAD.md` (A74, A79, new A85–A87) and `CLAUDE.md` (the face, the review bullet, the pytest line).

- [ ] **Step 1: Bump the version.** Make three replacements:
  - `"version": "0.5.11",` → `"version": "0.5.12",`
  - `const OFD_VERSION = '0.5.11';` → `const OFD_VERSION = '0.5.12';`
  - `BUILD: '0.5.11-v2.11',` → `BUILD: '0.5.12-v2.12',`

  Run: `grep -rn "0\.5\.11" src manifest.src.json`
  Expected: no output.

- [ ] **Step 2: The full server suite.**

Run: `python -m pytest -q`
Expected: **1981 collected**. All pass but the 1 skipped and at most the 1 known flaky A49 test.

- [ ] **Step 3: ui-v2.**

Run: `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean; `✓ built`.

- [ ] **Step 4: The extension on the scratch build.**

Run: `node build.mjs --out .baseline/v212-next; for s in fit engine shell overlay panel decoder; do OFD_DIST=.baseline/v212-next node test/$s.mjs | tail -1; done`
Expected: `0 failed` on all six (engine 116, fit 46, shell 148, overlay 39, panel 106, decoder 21).

- [ ] **Step 5: The diffs are only Phase 4.**

Run: `git status --short` and `git diff --stat` in both repos.
Expected:
- **TapeMap** modified: `ui-v2/src/{App.tsx,index.css}`, `ui-v2/src/pro/{Desk.tsx,api.ts}`, `ui-v2/src/hold/{parts.tsx,store.ts}`, `server.py`, `chain_live.py`, `conftest.py`, `test_hold_route.py`, `test_broker_switch.py`, `test_upstox_only.py`, `test_contract_upstox.py`, `START-HERE.md`.
- **TapeMap** deleted (staged by `git rm`): `ui-v2/src/one/*`, `ui-v2/src/hold/{HoldTab,MarketNow,HoldWindow}.tsx`, `ui-v2/src/board/BoardRev3.tsx`, `ui/{console.html,fmt.js,theme.css}`, `start.bat`, `ui-v2/{AGENTS.md,CLAUDE.md}`.
- **Extension:** `src/shell/{panel,recorder}.js`, `src/engine/v2.js`, `manifest.src.json`, `test/panel.mjs`. No `dist-v2` change yet.

- [ ] **Step 6: Build `dist-v2`, on Mary's word** (her 25 Oct 16:40 delegation). Her Chrome loads `dist-v2` at its next start or Reload, so the rollback copy goes first:

```bash
cd "/c/Users/kaam/Desktop/Go charting/orderflow-desk" && cp -r dist-v2 .baseline/v211-dist-v2 && npm run verify
```

Expected: `built …dist-v2…`, then the six suites at `0 failed`. `git diff --stat dist-v2` shows `manifest.json` and `src/main.js` (the bundle that carries `panel.js`).

- [ ] **Step 7: Record it.**

**NOTEPAD**, A74: replace

```
| CUT the verdict, on her word | OPEN |
```

with

```
| CUT the verdict, on her word | CUT (25 Oct, Phase 4 C1 + C4): the ANSWER band is the price and THE READ's row only; the calls log keeps writing. Live at 5173's next start |
```

**NOTEPAD**, A79: replace

```
| Off the panel face; keep the §1h log; show it in Validate at a press | OPEN (CUT list, her word) |
```

with

```
| Off the panel face; keep the §1h log; show it in Validate at a press | CUT (25 Oct, Phase 4 C3): off the panel head; the §1h log untouched; Validate's "same thesis, better expression" slot already serves the press. Live at the extension Reload 0.5.12 + F5 |
```

**NOTEPAD**, after the `| A82 |` row (Phase 2's), add:

```
| A85 | 25 Oct review (Phase 4) | **The CUT list, C1–C12** | spec §2 | C1 + C4 the ANSWER band is THE READ's row (the verdict, chips, headline, MAX PAIN / PCR / GEX / SQUEEZE, AAJ KA DIN and the dead max-pain level memo cut) · C2 nine tabs (Heat, Glass, Tape, Events, Map, Chain and `src/one/` deleted) · C3 no EXPRESSION pill · C5 in a trade the panel is the voice + one `[detail ▸]` · C6 no T1 / inval on the Float detail · C7 no LOOK HERE / glow · C8 `hold/*`, `BoardRev3` and `/api/hold?id=` `/check` `/expr` cut (their server functions kept for the rev 5 judgement; tests call them directly) · C9 `ui/console.html` (+ `fmt.js`, `theme.css`) and `/api/senses` cut · C10 `start.bat` deleted, broker default upstox (`chain_live._broker`; `_backfill_vpin` reads it) · C11 the August logs to the Recycle Bin, `ui-v2/AGENTS.md` + `CLAUDE.md`, panel `fs2` | DONE (25 Oct, Phase 4; live at her TapeMap restart, 5173's start and the extension Reload 0.5.12 + F5) · C12 DEFERRED, A86 |
| A86 | 25 Oct review (Phase 4 planning) | **C12 as worded would blind every late start's DEPTH vote** | `trap_log` is not the only reader of `data/senses/`: `senses.restore_sweeps` (`server.py:665`) streams today's raw sweep rows back on every start after the open to seed the ring `signals._depth_vote` reads (`server.py:1065`), a vote upstream of the §1d beep. 23 Oct [M]: 1,004,241 rows / 275.6 MB; `det` sweep 689,737 / 192.3 MB; the `-FUT` sweep rows 20,866 / 5.8 MB, exactly what `trap_log` sums (0 other rows pass its filter) | (A) write only `det` sweep rows: −83 MB a day, both readers byte-identical; (B) write only the `-FUT` sweep rows: −270 MB a day, `trap_log` identical, but a late start's restored ring then holds more of the morning, so a DEPTH vote that read "no sweep rows" may read measured. Past raw files kept either way | DEFERRED: needs Mary (B moves a signal input on restart days) |
| A87 | 25 Oct review (Phases 3–4) | **Left in place on purpose, now unreachable or stale** | `/api/hold/sigma` and `POST /api/hold/import` (their one caller was `hold/HoldTab.tsx`); `server._hold_reply` / `_hold_check` / `_expr_reply` and their helpers (kept for the rev 5 §1e/§1g/§1h judgement ~6 Nov); `data.ts`'s `HEAT` / `PRESSURE` / `EVENTS_BY_IDX` / `FOCUS_BY_IDX` / `ORDER_FLOW` / `KEY_LEVELS` / `MAP` / `highlight` (computed, read by no tab); `hold/hold.css`'s HoldTab rules; `/api/senses` named in `server.py` comments; `start-v2.bat`'s "started without TAPEMAP_BROKER, so it is on Dhan" hint; the F13 check flags a weekday holiday (no calendar, A80) | Cut with the rev 5 loop after its judgement; the rest at the next pass | OPEN |
```

**`CLAUDE.md`:**
- Replace ``- **The face:** the GoCharting extension v2.11 (0.5.11) in`` with ``- **The face:** the GoCharting extension v2.12 (0.5.12) in``.
- In the review bullet (Task 6), replace ``the voice's l1 ends `prem ±N%`.`` with:

```
the voice's l1 ends `prem ±N%`. Phase 4 cut: nine tabs (Read, Board, Trade, Flow, VPIN, OI Flow, War, Validate, Signals); the ANSWER band is THE READ's row; in a trade the panel is the voice + one `[detail ▸]`; `/console.html`, `/api/senses`, `/api/hold?id=` / `/check` / `/expr` and `start.bat` are gone; the broker default is upstox. C12 (the senses write) waits on Mary (NOTEPAD A86).
```

- Set the pytest line to Step 2's count, as Phase 4 (the cuts).

**`orderflow-desk/docs/V2-BUILD-REPORT.md`**, append after Phase 2's v2.11 section:

```
# v2.12 — the cuts: no EXPRESSION pill, one [detail ▸] in a trade (25 Oct 2026 review, Phase 4)

Plan `tapemap/docs/superpowers/plans/2026-10-25-review-phase3-4-evidence-cuts.md` (spec `…/specs/2026-10-25-review-fix-cut-stop-design.md`
§2, C3 / C5 / C11). Display only; no state, stop, rule or wire field changed.

- **C3** the panel head drops the EXPRESSION pill (`frame.read.expr.word`; a median 65 word changes a day, TapeMap A79). TapeMap's
  §1h log keeps writing; Validate's "same thesis, better expression" slot serves the both-ways rule at the press.
- **C5** in a trade with the voice speaking, the panel is the voice block (l1–l5), a slim head (index, price, clock, bell, the two
  feed dots, the 15:00 reminder), I'M OUT and the chart's lines. READ, KHEL, SIZE, ref, the legend, DECODE, khilaaf, SIRF BADE,
  the FOLD board, JAGAH, the 09:45 card, DIN, ABHI and ? wait under the voice's one `[detail ▸]` (`ofd.vdet`, shut by default,
  remembered). A voice that cannot speak folds nothing.
- **C11** `panel.js`'s unused `fs2` is gone (the overlay's is `v2.js`'s).
- **Version 0.5.12** (`manifest.src.json`, `recorder.js`, `v2.js BUILD 0.5.12-v2.12`); `dist-v2` rebuilt.
- **Tests:** panel 106 (+3 C5; the §5 head check asserts no EXPRESSION pill; the v2.6 byte-identity check strips the v2.6 head's
  pill), the other five unchanged.
- **Live at** her Reload of "Order Flow Desk v2" (Chrome shows 0.5.12) + F5 of the GoCharting tab. It needs no TapeMap change.
- **Rollback:** `.baseline/v211-dist-v2`.
```

- [ ] **Step 8: The controller's render checks** (Tasks 7, 8, 10, 11, light, one screenshot each), saved with the build report.

- [ ] **Step 9: Tell Mary (in the report she reads when back).**
  - **What changes on screen:**
    - nine tabs;
    - the band is price + THE READ;
    - the Float detail has no T1 / inval;
    - no LOOK HERE;
    - the panel head has no EXPRESSION pill, and in a trade it is the voice + `[detail ▸]`.
  - **What is gone from disk:** the dead hold / board / glass UI, `console.html`, `start.bat`, the August logs (in the Recycle Bin).
  - **Untouched:** §1i–§1q, the voice's states, `fold.py`, the zone machine, the §1d gate, `signals.py`, every forward log's rows.
  - **Her call:** C12 (A86), (A) or (B).
  - **Live, after a close, in this order:**
    1. Reload the extension (0.5.12) and F5 the tab.
    2. Restart TapeMap (routes, broker default, Phase 3's server half).
    3. 5173 picks up ui-v2 at its next start.

- [ ] **Step 10: Commit (the controller, on her 25 Oct delegation).** Two commits. The `git rm`'d paths are already staged.

```bash
cd "/c/Users/kaam/Desktop/operator mode/tapemap" && git add ui-v2/src/App.tsx ui-v2/src/index.css ui-v2/src/pro/Desk.tsx ui-v2/src/pro/api.ts ui-v2/src/hold/parts.tsx ui-v2/src/hold/store.ts server.py chain_live.py conftest.py test_hold_route.py test_broker_switch.py test_upstox_only.py test_contract_upstox.py START-HERE.md CLAUDE.md docs/live/NOTEPAD.md docs/superpowers/plans/2026-10-25-review-phase3-4-evidence-cuts.md
git commit -m "review 25 Oct phase 4: the cuts (C1-C11; C12 deferred, A86)

- the ANSWER band is THE READ's row; nine tabs; no LOOK HERE; the Float detail drops T1 / inval
- the dead hold/*, BoardRev3 and Glass UI deleted; /api/hold?id=, /check, /expr and /api/senses not served
- console.html and start.bat deleted; the default broker is upstox

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cd "/c/Users/kaam/Desktop/Go charting/orderflow-desk" && git add src/shell/panel.js src/shell/recorder.js src/engine/v2.js manifest.src.json test/panel.mjs dist-v2 docs/V2-BUILD-REPORT.md
git commit -m "v2.12 (0.5.12): the cuts (TapeMap review 25 Oct, phase 4)

- no EXPRESSION pill on the panel head
- in a trade the panel is the voice block + one [detail >], shut by default and remembered
- the unused fs2 is gone

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Spec coverage (self-review)

| Spec row | Task | Test that fails today |
|---|---|---|
| F12: `POST /api/validate/log`, write-once `(t, idx, K, ty, side)`, `data/validate/press_<day>.jsonl`, log only | 1, 2 | `test_hold_route …validate_press…`; `test_validate_app …press…` |
| F13a: after 15:30 no import → `tradebook aaj import nahi` on the Float and Validate, with the import door | 3, 4 | `test_receipts …after_1530…`; render check (Validate: Monday after 15:30) |
| F13b: 09:20 check → `RECORDING NAHI: <which>` on 5173 and the Float, one `feed_log` row | 3, 4 | `test_feed_health …recording_check…`; render check |
| F14: `prem −45%` on l1, signed by side, `prem ?`; the 22 Oct 73400 CE `−47%` | 5 | `test_voice …premium_from_her_entry…` + the pinned l1 |
| C1 the ANSWER band cuts (verdict, chips, headline, MAX PAIN / PCR / GEX / SQUEEZE, day-type, max pain as a level); calls log keeps writing | 7 | grep + `tsc` / build + render |
| C2 six tabs, their components, `trending-glow`; nine remain | 8 (+ 14 for the glow CSS) | grep + build + render |
| C3 EXPRESSION pill off the panel; §1h log stays | 9 | panel `§5 head`, `v2.6 2` |
| C4 AAJ KA DIN off every face (only the band had it) | 7 | grep |
| C5 in a trade: voice + chart lines; the rest under one `[detail ▸]` | 9 | panel `C5` ×3 |
| C6 T1 and inval off the Float detail | 10 | grep + render |
| C7 LOOK HERE | 14 | grep |
| C8 `hold/*`, `HoldWindow`, `BoardRev3` + the three routes; types and `useBoardGlance` moved first; grep both repos + paperdesk; server modules stay | 11 | `test_hold_route …cut_hold_routes…` + grep |
| C9 `ui/console.html` + `/api/senses`; icons kept; CLAUDE.md / START-HERE.md | 12 | grep |
| C10 `start.bat`; default broker upstox | 13 | `test_broker_switch …is_upstox`, `test_upstox_only …says_upstox…` |
| C11 August logs, `ui-v2/AGENTS.md`, `fs2` | 14 | grep / ls |
| C12 the senses raw write | — | **DEFERRED: needs Mary** (A86) |
| Kept on purpose (OI Flow, VPIN, PaperDesk routes, rev 5 loop) | all | untouched; C8 keeps the rev 5 functions |
| Last task per phase: verify, record, commit; extension 0.5.12 | 6, 15 | — |
