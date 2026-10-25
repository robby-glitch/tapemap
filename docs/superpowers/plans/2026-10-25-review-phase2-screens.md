# Review 25 Oct, Phase 2: The Screens — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five failure paths on her three faces, spec F6–F10 (`docs/superpowers/specs/2026-10-25-review-fix-cut-stop-design.md` §1, Phase 2; F11 dropped):
- her SENSEX trade is invisible on the NIFTY panel (F6);
- a stale frame turns the panel flat mid-trade (F7);
- the Float shows an unknown word as HOLD and a dead server's voice as live (F8);
- with the voice refused, each face shows its own stop (F9);
- pollers with no timeout or in-flight guard, and every missing reply blamed on an extension reload (F10).

**Architecture:** Display and plumbing only. Nothing decides anything new.
- **Server (F6):** `fold_live.frame` falls back to her most recent open marked trade on any index, with its idx and `open_n`. The NIFTY story and the HOLD-vs-DECODER log keep reading only NIFTY's own trade (`server._own_fold`).
- **Extension face (`main.js` `face()` + `panel.js`):**
  - F6: a trade whose idx is not the chart's draws no line here; the block says where its lines are.
  - F7: the last fresh in-trade frame is held, so a stale frame keeps the voice and the STOP / ENTRY lines, labelled STALE.
  - F9: the in-trade STOP is the voice's or none.
  - F10: one POST in flight, an 8 s bound in `sw.js`, and `boot.js` blames a reload only when `chrome.runtime.id` is gone.
- **ui-v2:**
  - `Float.tsx` (F8): `?` for an unknown word; the read's age, or `NOT LIVE since hh:mm:ss`.
  - `Desk.tsx` (F9): no inval when the voice cannot speak.
  - `data.ts` (F10): an 8 s bound and one read in flight.
- **Validate `app.js`:**
  - F9: one helper, `voiceStop`, for the ladder's STOP line and the to-stop cells.
  - F10: an 8 s bound and a busy flag on each poller.

**Tech Stack:**
- Python 3.13 + pytest (server).
- Node 22, no bundler, with the extension's own suites. `shell`, `overlay` and `panel` drive the BUILT bundle.
- React 19 + TypeScript 5.7 + Vite 8 (ui-v2). There is no test runner, and none is added.
- Plain JS + Preact/htm from CDN (Validate), tested through a node `vm` harness like `test/validate3_harness.cjs`.

## Global Constraints

- **Repos, branches, line endings.**
  - TapeMap: `C:\Users\kaam\Desktop\operator mode\tapemap`, branch `feature/operator-objects`. Phase 1's edits (`score_frame.py`, `server.py`, …) may already sit uncommitted in the tree. Leave them; this plan touches other lines.
  - Extension: `C:\Users\kaam\Desktop\Go charting\orderflow-desk`, its own git repo, branch `one-tool`.
  - **Every file this plan edits is CRLF.** Edit only with exact-string replacements: no reformatting, renames or whole-file writes. New files (`test/validate_app_harness.cjs`, `test_validate_app.py`) are the only `Write`s.
  - After each task, `git diff --stat` in the repo(s) it touched shows only that task's lines. If a file shows a whole-file change, its line endings flipped: redo that edit byte-safely.
- **Order.** Tasks run in order. Tasks 2, 3, 5 and 6 edit the same lines of `main.js` / `panel.js`; each later task's "old" strings are the text as the earlier task left it (they are written that way below).
- **Commands.**
  - **Server:** `python -m pytest -q` from the TapeMap root. The baseline is Phase 1's final count, measured 25 Oct: 1970 collected = 1968 pass, 1 skipped, 1 known flaky `test_v2feed.py::test_serve_caches_full_and_answers_delta` (NOTEPAD A49). This plan adds 3 tests.
  - **Extension: build to the scratch folder, never to `dist-v2`, until Task 8's gate.** Her Chrome loads `dist-v2` at its next start, so building there is shipping it. In Git Bash:
    `cd "/c/Users/kaam/Desktop/Go charting/orderflow-desk" && node build.mjs --out .baseline/v211-next`, then each suite as `OFD_DIST=.baseline/v211-next node test/<suite>.mjs`. `.baseline/` is gitignored, and `build.mjs` wipes its own `--out` folder on every build.
  - **ui-v2:** `cd "/c/Users/kaam/Desktop/operator mode/tapemap/ui-v2" && ./node_modules/.bin/tsc --noEmit -p . && npx vite build`. `tsc` is clean today (no output). `vite build` writes `ui-v2/dist`, which is gitignored and not served.
- **Hard limits.**
  - Never start, stop or restart the TapeMap server, nor any dev server on 5173 or 8765. Mary starts them herself.
  - Never write under `tapemap/data/`. Tests use `tmp_path` / `monkeypatch` only.
  - **No commits by implementers.** The controller commits once per repo in Task 8, and only after Mary says commit. The commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - No new dependency and no new test framework.
  - A PreToolUse "Fact-Forcing Gate" hook may ask an agent to state facts before its first Bash call or edit of a file: importers, affected API, data schemas, the user's instruction. State them briefly and retry. The user's instruction is, verbatim: "hey i am going out just fix everything i want evevyrhting fix by the time i am back you are incharge whatever you think is right do it".
- **Timing (spec §0).**
  - **SUPERSEDED 25 Oct 16:40 by Mary's delegation:** "hey i am going out just fix everything i want evevyrhting fix by the time i am back you are incharge whatever you think is right do it". The controller runs this plan now (Sunday 25 Oct) and commits each phase locally. The rollback is the tag `pre-review-2026-10-25` in both repos.
  - Server and ui-v2 edits take effect at her next start. ui-v2 takes effect at once through HMR if 5173 is running when a file is saved.
  - Never edit a file the live server imports, `ui-v2/src/` or `ui-v2/public/validate2/` between 09:15 and 15:40 IST, Mon–Fri.
  - **Order safety (controller decision):** the F6 other-index fallback is OPT-IN. Only a page that sends `away: 1` in its frame POST (0.5.11+) ever gets another index's trade in `fold`. A 0.5.10 page never sends it, so it can never draw SENSEX levels on a NIFTY chart, whatever order she restarts or reloads in.
- **Never touch.**
  - The registered rules §1i–§1q and their browser computations: VALIDATE rev 3 / 3.1 in `engine.js` (this plan does not open `engine.js`), the extension's FADE KILL (`fadeKills`, the PLAN's RANGE KILL rows), and READ-2's JAGAH `push` on the wire.
  - `voice.py`'s state logic, `fold.py`'s engine, `engine.py`, the zone machine and the §1d gate.
  - Existing rows of any forward log, and `data/trigger_log.jsonl`.
- **Copy rule.**
  - On-screen words are short, in the existing Hinglish/English style, at most 6 words per cell, with no paragraphs on the face. The new words are exactly: `lines: SENSEX chart`, `+1 open`, `STALE 10:05:12`, `stop: could not check — <why>`, `NOT LIVE since 11:04:10`, `TapeMap not answering`, `TapeMap not answering (8 s)`.
  - **Light only.** Use the existing CSS variables, with no new colour literals. `panel.mjs`'s LIGHT test must stay green.
- **Numbers** in docs are tagged [M] measured or [I] inferred. Never a win / hit rate.

---

### Task 1: The frame carries her open trade on any index (F6, server half, A70)

**Files:**
- Modify: `fold_live.py:650-658` (`frame`)
- Modify: `server.py:2256` (add `_own_fold` above `_story_for`), `server.py:2292` (the story's fold argument), `server.py:~4716` (the HOLD-vs-DECODER log guard), and the call site `server.py:4684`, which passes `any_idx=bool(doc.get("away"))`.
- Test: `test_fold_live.py` (insert above `class _ChainPoller:`, `:215`)

**Interfaces:**
- Produces: `fold_live.frame(idx, trades) -> (fold | None, flat | None)`.
  - `fold` is her open trade on `idx`, else her most recent open trade with `src == "marked"` on any index (by `t0`).
  - It is a shallow copy of the engine's reply plus `open_n: int`, the count of all open trades. `fold.trade.idx` (from `api_trade`) can now differ from `idx`.
  - `flat` is `idx`'s flat read whenever the trade is not `idx`'s own.
- Produces: `server._own_fold(fold, idx) -> fold | None`. It returns `fold` when `fold.trade.idx` is `idx` or absent.

**Can affect:**
- the panel's voice block, now reachable for a SENSEX trade on NIFTY's POST (`_in_trade` runs for it, as the Float's poll already does);
- `fr["receipt"]`, which is no longer sent while any trade is open.

**Untouched:**
- `frame_log` (written before `fold` is set);
- `_validate_for`: it finds the trade by idx, so a foreign fold reads as "no trade";
- the story's input and the `hold_vs_decoder` log: both get `_own_fold`, so they see what they saw before F6.

- [ ] **Step 1: Write the failing test.** In `test_fold_live.py`, replace

```python
class _ChainPoller:
```

with

```python
def test_the_frame_carries_her_open_trade_on_another_index_and_this_index_never_reads_it(live, monkeypatch, tmp_path):
    """25 Oct review F6 / A70 (DEV-FACES F04): she trades SENSEX on the NIFTY chart (§1q), and NIFTY's page is the one that
    posts. The frame carried `fold` only for an open trade on the POST's own index, so the panel read FLAT mid-trade with
    NIFTY MARK buttons. Now: her most recent open marked trade on any index, its idx in fold.trade, and open_n. NIFTY's own
    flat read still rides, and NIFTY's story (and the HOLD-vs-DECODER log) never take the SENSEX trade."""
    import story
    sx = dict(REC, id="SENSEX-81200CE-long-100500", idx="SENSEX", k=81200.0, side="CE", t0="10:05:00")
    bn = dict(REC, id="BANKNIFTY-54000PE-long-094000", idx="BANKNIFTY", k=54000.0, t0="09:40:00")
    live.extend([dict(REC, exit_t="09:30:00"), bn, sx])          # NIFTY's own trade is closed: nothing open on this index
    told = []
    monkeypatch.setattr(story, "compose_all", lambda *a, **k: told.append(a[5]) or {})   # a[5]: the fold the story reads
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    old = _Req("/api/frame", _tape(n=3))                         # a 0.5.10 page: no `away` -- it must never get another index's trade
    server.Handler.do_POST(old)
    assert old.out[-1][1]["fold"] is None
    req = _Req("/api/frame", dict(_tape(n=3), away=1))           # a 0.5.11 page opts in
    server.Handler.do_POST(req)
    fr = req.out[-1][1]
    assert fr["ok"] and fr["fold"]["id"] == sx["id"] and fr["fold"]["trade"]["idx"] == "SENSEX" and fr["fold"]["open_n"] == 2
    assert fr["flat"] is not None                                # NIFTY's flat read is this chart's own
    assert told == [None, None]                                  # the NIFTY story never reads the SENSEX trade


class _ChainPoller:
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_fold_live.py::test_the_frame_carries_her_open_trade_on_another_index_and_this_index_never_reads_it`
Expected: FAIL with `TypeError: 'NoneType' object is not subscriptable` (`fr["fold"]` is None today).

- [ ] **Step 3: Implement.**

In `fold_live.py`, replace

```python
def frame(idx, trades):
    """POST /api/frame's two extra fields: `fold` for the open marked trade on idx (else None), `flat` when none."""
    try:
        open_ = [t for t in trades if t["idx"] == idx and not t.get("exit_t")]
        if open_:
            return reply("/api/fold", {"id": [open_[0]["id"]]}, trades), None
        return None, reply("/api/fold/flat", {"idx": [idx]}, trades)
```

with

```python
def frame(idx, trades, any_idx=False):
    """POST /api/frame's two extra fields: `fold` for the open trade on idx -- else, when the page opted in (`any_idx`, its
    `away: 1`, extension 0.5.11+; an older page would draw another index's levels on this chart), her most recent open MARKED
    trade on any index, its own idx in fold.trade (25 Oct review F6: she trades SENSEX on the NIFTY chart, §1q, and NIFTY's
    page is the one that posts) -- with `open_n`, every trade she has open; `flat`, this index's read, unless the trade is
    this index's."""
    try:
        live = [t for t in trades if not t.get("exit_t")]
        mine = [t for t in live if t["idx"] == idx]
        away = [t for t in live if any_idx and t.get("src", "marked") == "marked"]
        flat = None if mine else reply("/api/fold/flat", {"idx": [idx]}, trades)
        if not (mine or away):
            return None, flat
        tr = mine[0] if mine else max(away, key=lambda t: t.get("t0") or "")
        return dict(reply("/api/fold", {"id": [tr["id"]]}, trades), open_n=len(live)), flat
```

(The `except` clause below it is unchanged.)

In `server.py`, replace

```python
def _story_for(idx, day, doc, fr, now_ms):
```

with

```python
def _own_fold(fold, idx):
    """The frame's fold when it is THIS index's trade (or names none), else None. Since 25 Oct (F6) the frame can carry her
    open trade on another index for the panel's voice; the story's count and the HOLD-vs-DECODER log read this index's
    decoder, so a SENSEX trade riding NIFTY's POST never enters them."""
    return fold if ((fold or {}).get("trade") or {}).get("idx") in (None, idx) else None


def _story_for(idx, day, doc, fr, now_ms):
```

Then replace

```python
fr.get("fold"), trap, three, fr.get("feed"), vp, logged, m["cant"])
```

with

```python
_own_fold(fr.get("fold"), idx), trap, three, fr.get("feed"), vp, logged, m["cant"])
```

Then replace

```python
                    fr["fold"], fr["flat"] = fold_live.frame(idx, trs)
```

with

```python
                    fr["fold"], fr["flat"] = fold_live.frame(idx, trs, any_idx=bool(doc.get("away")))
```

Then replace

```python
                if in_session and isinstance(fr.get("fold"), dict) and fr["fold"].get("ok"):
```

with

```python
                if in_session and isinstance(_own_fold(fr.get("fold"), idx), dict) and fr["fold"].get("ok"):
```

- [ ] **Step 4: Run the touched files and see them pass.**

Run: `python -m pytest -q test_fold_live.py test_frame_api.py test_frame_v2.py test_story_panel.py test_voice.py test_sensex_flow.py test_hold2.py test_feed_health.py`
Expected: all pass. `test_the_frame_carries_the_open_trades_view_whole` still sees `flat is None` for a NIFTY trade. The engine-failure test's `fr["fold"] == {...}` is the server's own except branch, which is unchanged.

---

### Task 2: The panel shows her SENSEX trade on the NIFTY chart, and draws none of its lines (F6, extension half, A70)

**Files:**
- Modify: `src/shell/main.js`:
  - `:61`: add `idxOf` after `dayKey`;
  - `:337`: add `away` / `more` after `t0`;
  - `:341`: the trade lines' gate;
  - `:372`: add the model fields;
  - `:455`: the POST's `idx:` (the same value, through `idxOf`).
- Modify: `src/shell/panel.js`:
  - `:98`: the `.vx` style;
  - `:371`: add `vtag` above `voiceBlock`;
  - `:375`: the block's first line;
  - `:379`: the could-not-speak line.
- Test: `test/shell.mjs` and `test/panel.mjs`. Each inserts a block before its one `console.log('');` (`shell.mjs:795`, `panel.mjs:550`).

**Interfaces:**
- Consumes: `frame.fold.trade.idx` and `frame.fold.open_n` (Task 1).
- Produces on the face model (`m.v2`):
  - `away: string | null`: the trade's idx when it is not this chart's;
  - `more: number`: her other open trades.
- Produces in the panel: `vtag(X) -> html` (Task 3 extends it).

**Can affect:**
- the chart's lines while she holds a trade on another index: none of that trade's lines; the chart's own flat lines (plan / walls) stay;
- the voice block's first line.

**Untouched:**
- the sound ladder (still keyed per trade id);
- the POST body (`idx` has the same value);
- READ-2's `push`;
- the FADE KILL;
- every NIFTY-trade case (`away` is null when `T.idx` is the chart's or absent).

- [ ] **Step 1: Write the failing tests.**

In `test/shell.mjs`, replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review F6 (A70): her SENSEX trade on the NIFTY chart (§1q) -- the block, never its lines here; +N for the others
guard('F6 a SENSEX trade on the NIFTY chart', () => {
  const app = run(bars.length), last = bars[bars.length - 1].c;
  const fold = (idx, open_n) => ({ id: idx + '-T1', open_n, trade: { idx, k: 23000, ty: 'CE', side: 'BUY', p0: 120, entry_t: '10:05:00', exit_t: null },
    view: { headline: 'HOLD', d: 1, E: last - 5, G: { px: last - 30, set_t: '10:05' }, A: { k: 23100, px: last + 40 }, events: [] },
    voice: { ok: true, state: 'HOLD', seq: 1, l1: '▲ 23000 CE · 9 min', l2: 'stop', l3: 'why: flow saath', stop_f: last - 20, active: [] } });
  app.win._reply = STUB({ fold: fold('SENSEX', 2) }); app.deliver(); app.tick();
  const sx = app.model().v2, sxL = app.overlay().v2.lines;
  ok(sx.inTrade && sx.away === 'SENSEX' && sx.more === 1 && !sxL.some((x) => x.mine),
    'F6 a SENSEX trade on the NIFTY chart: in the trade, tagged SENSEX, +1 open, none of its lines drawn here: ' + JSON.stringify({ away: sx.away, more: sx.more, lines: sxL.map((x) => x.kind) }));
  app.win._reply = STUB({ fold: fold('NIFTY', 1) }); app.deliver(); app.tick();
  const nf = app.model().v2, nfL = app.overlay().v2.lines;
  ok(nf.inTrade && nf.away === null && nf.more === 0 && nfL.some((x) => x.kind === 'kill' && x.p === last - 20) && nfL.some((x) => x.kind === 'entry'),
    'F6 her NIFTY trade on the NIFTY chart still draws its STOP and ENTRY: ' + nfL.map((x) => x.kind).join(','));
});
console.log('');
```

In `test/panel.mjs`, replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review F6 (A70): her SENSEX trade on the NIFTY chart -- the block wears its index, says where its lines are, +N open
{
  const VC = { ok: true, state: 'HOLD', seq: 1, l1: '▲ 81200 CE · 9 min · +0.4R', l2: 'stop 81,050f / 80,990s', l3: 'why: flow saath', stop_f: 81050, active: [] };
  const sx = (open_n) => ({ id: 'SX1', open_n, trade: { idx: 'SENSEX', k: 81200, ty: 'CE', side: 'BUY', p0: 210, entry_t: '10:05:00', exit_t: null }, view: { headline: 'HOLD', d: 1, E: 81100, G: { px: 81000 }, events: [] }, voice: VC });
  const P = boot(), m = modelOf(bars.length, { read: READ, fold: sx(2) }); P.panel.render(m);
  const vt = P.block('voice').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
  ok(/class="vc HOLD"/.test(P.block('voice')) && vt.includes('SENSEX · lines: SENSEX chart · +1 open') && vt.includes('▲ 81200 CE · 9 min') && !m.v2.lines.some((x) => x.mine),
    'F6 the voice block on the NIFTY panel says SENSEX, where its lines are, and +1 open; no line of it on this chart: ' + vt);
  P.panel.render(modelOf(bars.length, { read: READ, fold: sx(1) }));
  ok(!/\+\d+ open/.test(P.block('voice')) && /lines: SENSEX chart/.test(P.block('voice')), 'F6 one trade open: no +N chip');
}
console.log('');
```

- [ ] **Step 2: Run them and see them fail.**

Run: `cd "/c/Users/kaam/Desktop/Go charting/orderflow-desk" && node build.mjs --out .baseline/v211-next; OFD_DIST=.baseline/v211-next node test/shell.mjs; OFD_DIST=.baseline/v211-next node test/panel.mjs`
Expected:
- `shell` prints `FAIL F6 a SENSEX trade on the NIFTY chart: …`, because `away` is undefined and the SENSEX lines are drawn.
- `panel` prints `FAIL F6 the voice block on the NIFTY panel says SENSEX…`.
- Both exit 1. Every other check passes.

- [ ] **Step 3: Implement.**

In `src/shell/main.js`, replace

```js
  const dayKey = () => new Date(Date.now() + 19800000).toISOString().slice(0, 10);
```

with

```js
  const dayKey = () => new Date(Date.now() + 19800000).toISOString().slice(0, 10);
  const idxOf = (k) => String(k || '').split('|')[0].split('-')[0];   // a session key's index: the POST's idx, and F6's "is her trade this chart's"
```

Replace

```js
    const t0 = T ? String(T.t0 || T.entry_t || '').slice(0, 5) : null;
```

with

```js
    const t0 = T ? String(T.t0 || T.entry_t || '').slice(0, 5) : null;
    // F6 (25 Oct): the frame can carry her trade on ANOTHER index (fold_live.frame, §1q: SENSEX on the NIFTY chart). Its levels
    // are that index's futures: no line of it is drawn on this chart (frame discipline); the block says where they are
    const ci = idxOf(d.key), away = T && T.idx && /^(NIFTY|BANKNIFTY|SENSEX)$/.test(ci) && T.idx !== ci ? T.idx : null, more = fd && fd.open_n > 1 ? fd.open_n - 1 : 0;   // review fix: a parse miss never hides her own lines
```

Replace

```js
    const trade = inTrade ? [
```

with

```js
    const trade = inTrade && !away ? [
```

Replace

```js
writers: F && F.writers ? F.writers : null, inTrade, dir, trade: inTrade ? { T, V, VL } : null,
```

with

```js
writers: F && F.writers ? F.writers : null, inTrade, away, more, dir, trade: inTrade ? { T, V, VL } : null,
```

Replace

```js
out({ kind: 'frame', session: active, idx: active.split('|')[0].split('-')[0], interval:
```

with

```js
out({ kind: 'frame', away: 1, session: active, idx: idxOf(active), interval:
```

In `src/shell/panel.js`, replace

```js
cursor:pointer;font:11px var(--mono);padding:0 6px}`;
```

with

```js
cursor:pointer;font:11px var(--mono);padding:0 6px}
/* F6 / F7 (25 Oct): the voice's first line when it needs one -- STALE hh:mm:ss, her trade's own index and where its lines are, +N open */
.vx{display:block;font:700 10.5px/1.5 var(--sans);letter-spacing:.04em;color:var(--flip)}`;
```

Replace

```js
  // v2.9 THE ONE VOICE (fold.voice, TapeMap A52): three lines, the word coloured; v2.10 + l4 / l5, the TRADE MAP; the words are TapeMap's
```

with

```js
  // F6 (25 Oct): a trade on another index wears its tag and says where its lines are (frame discipline); +N: her other open trades
  const vtag = (X) => { const t = [X.away ? `<b>${esc(X.away)}</b> · lines: ${esc(X.away)} chart` : '', X.more ? `+${X.more} open` : ''].filter(Boolean);
    return t.length ? `<span class="vx">${t.join(' · ')}</span>` : ''; };
  // v2.9 THE ONE VOICE (fold.voice, TapeMap A52): three lines, the word coloured; v2.10 + l4 / l5, the TRADE MAP; the words are TapeMap's
```

Replace

```js
      + `<span class="v1">
```

with

```js
      + vtag(X) + `<span class="v1">
```

Replace

```js
`<div class="vc rc"><span class="abs cant">${esc(/^could not check/
```

with

```js
`<div class="vc rc">${vtag(X)}<span class="abs cant">${esc(/^could not check/
```

- [ ] **Step 4: Run the suites and see them pass.**

Run: `node build.mjs --out .baseline/v211-next; for s in shell panel overlay; do OFD_DIST=.baseline/v211-next node test/$s.mjs | tail -1; done`
Expected: `0 failed` on all three. `panel.mjs`'s "v2.6 2 byte-identical" check stays green, because `voice` is not among its compared blocks.

---

### Task 3: A stale frame mid-trade keeps her trade; no MARK while a trade is open (F7, A71)

**Files:**
- Modify: `src/shell/main.js`:
  - `:67`: `held`, after `TAPE_OK_MS`;
  - `:84`: set `held` on each fresh frame;
  - `:335`: `fd` from `held` when the frame is stale;
  - `:342`: the STOP line's name;
  - `:372`: the model fields.
- Modify: `src/shell/panel.js`:
  - `vtag` (from Task 2);
  - `:365`: the FOLD board's `fd`;
  - `:373`: `vc`;
  - `:388`: `actBlock`;
  - `:433-434`: `vcOk` / `mapDetail`.
- Test: `test/shell.mjs` and `test/panel.mjs` (each before `console.log('');`)

**Interfaces:**
- Produces in `main.js`: `held = { idx, day, fold, at } | null`. It is set by every fresh frame: the frame when it carries an open trade with a view, else null.
- Produces on `m.v2`:
  - `open`: the open trade (`T` with an id and no exit, view or not), else null;
  - `staleAt`: `'HH:MM:SS'` of the held frame while the frame is stale, else null;
  - `fold`: the fold the face read (the fresh frame's, or the held one's).
- The STOP line's name becomes `'STOP STALE HH:MM:SS'` while stale.
- The panel reads the voice from `X.fold`, no longer from `F.fold`.

**Can affect:**
- the panel and the chart while the frame is 15 s+ old and the last fresh frame had her trade;
- the act block whenever a trade is open (I'M OUT, never MARK).

**Untouched:**
- `m.frame` (still null when stale, so the header dots, the "?" block and the overlay's `day` / `uxOi` read "TapeMap not answering" as today);
- the sound ladder (rings only on fresh frames);
- flat faces.

- [ ] **Step 1: Write the failing tests.**

In `test/shell.mjs`, replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review F7 (A71): a frame gone stale mid-trade keeps her trade -- the block, the STOP / ENTRY lines, labelled STALE
guard('F7 a stale frame mid-trade', () => {
  const app = run(bars.length), last = bars[bars.length - 1].c;
  app.win._reply = STUB({ chain: { atm: 23000, ts: '10:05', strikes: [{ k: 23000, ce: 90, pe: 80 }] }, fold: { id: 'T7', trade: { idx: 'NIFTY', k: 23000, ty: 'PE', side: 'BUY', p0: 80, entry_t: '10:05:00', exit_t: null },
    view: { headline: 'HOLD', d: -1, E: last + 5, G: { px: last + 30, set_t: '10:05' }, events: [] }, voice: { ok: true, state: 'HOLD', seq: 1, l1: 'x', l2: 'y', l3: 'z', stop_f: last + 25, active: [] } } });
  app.deliver(); app.tick();
  app.win._reply = null; app.win._advanceClock(20000); app.tick();               // 20 s of silence
  const m = app.model(), v = m.v2, L = app.overlay().v2.lines;
  ok(m.frame === null && v.inTrade && /^\d\d:\d\d:\d\d$/.test(v.staleAt || '') && v.open && v.open.id === 'T7' && v.fold && v.fold.voice.ok,
    'F7 20 s stale mid-trade: still in the trade, off the held frame, STALE ' + v.staleAt);
  ok(L.some((x) => x.kind === 'kill' && x.p === last + 25 && x.name === 'STOP STALE ' + v.staleAt) && L.some((x) => x.kind === 'entry' && x.p === last + 5),
    'F7 the STOP and ENTRY lines stay, the STOP labelled STALE: ' + JSON.stringify(L.map((x) => [x.kind, x.name])));
  app.win._reply = STUB(); app.deliver(); app.tick();                             // a fresh frame without her trade: she is out
  ok(!app.model().v2.inTrade && app.model().v2.staleAt === null, 'F7 a fresh frame without her trade ends the hold');
  Date.now = REAL_NOW;
});
console.log('');
```

In `test/panel.mjs`, replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review F7 (A71): 20 s stale mid-trade the block stays (STALE hh:mm:ss) and MARK never comes back
{
  const app = run(bars.length);
  app.win._reply = { ok: true, idx: 'NIFTY', rank_ref_id: 'rank-test', rank_ref: REF, read: READ, chain: { atm: 23900, ts: '10:05', strikes: [{ k: 23900, ce: 101.5, pe: 96.2 }] },
    fold: { id: 'T7', trade: { idx: 'NIFTY', k: 23900, ty: 'PE', side: 'BUY', p0: 96.2, entry_t: '10:05:00', exit_t: null }, view: { headline: 'HOLD', d: -1, E: lastC + 5, G: { px: lastC + 30 }, events: [] },
      voice: { ok: true, state: 'HOLD', seq: 1, l1: '▼ 23900 PE · 9 min', l2: 'stop 23,960f', l3: 'why: flow saath', stop_f: lastC + 25, active: [] } } };
  app.deliver(); app.tick(); app.tick();
  app.win._reply = null; app.win._advanceClock(20000); app.tick();
  const P = boot(); P.panel.render(app.model());
  const vt = P.block('voice').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' '), act = P.block('act').replace(/&#39;/g, "'");
  ok(/STALE \d\d:\d\d:\d\d/.test(vt) && vt.includes('▼ 23900 PE · 9 min') && /I'M OUT/.test(act) && !/MARK/.test(act),
    'F7 the stale block keeps the voice with STALE, and I\'M OUT, never MARK off the old chain: ' + vt);
}
console.log('');
```

- [ ] **Step 2: Run them and see them fail.**

Run: `node build.mjs --out .baseline/v211-next; OFD_DIST=.baseline/v211-next node test/shell.mjs; OFD_DIST=.baseline/v211-next node test/panel.mjs`
Expected:
- `FAIL F7 20 s stale mid-trade…` and `FAIL F7 the STOP and ENTRY lines stay…`: today `inTrade` is false once the frame is stale.
- `FAIL F7 the stale block keeps the voice…`: the block is empty and the MARK buttons are back.
- Exit 1.

- [ ] **Step 3: Implement.**

In `src/shell/main.js`, replace

```js
  const TAPE_OK_MS = 5000;   // the tape dot's ok/stale boundary — same shape as FRAME_STALE_MS, for the book dot
```

with

```js
  const TAPE_OK_MS = 5000;   // the tape dot's ok/stale boundary — same shape as FRAME_STALE_MS, for the book dot
  let held = null;   // F7 (25 Oct): the last fresh frame that carried her open trade {idx, day, fold, at}: a stale frame keeps its voice and lines
```

Replace

```js
    frame = f; frameAt = Date.now(); lastOk = true;
```

with

```js
    frame = f; frameAt = Date.now(); lastOk = true;
    const ht = f.fold && f.fold.trade; held = ht && ht.id && !ht.exit_t && f.fold.view ? { idx: f.idx, day: f.day, fold: f.fold, at: frameAt } : null;
```

Replace

```js
    const fd = F && F.fold, T = fd && fd.trade, V = fd && fd.view, inTrade = !!(T && T.id && !T.exit_t && V);
```

with

```js
    // F7 (25 Oct): a stale frame (F null) mid-trade keeps her trade -- the held fold, its voice and its STOP / ENTRY lines, labelled
    // STALE; nothing else of the old frame is shown. open: her trade with or without the engine's view (no MARK while it is open)
    const fd = F ? F.fold : held && held.fold, T = fd && fd.trade, V = fd && fd.view, inTrade = !!(T && T.id && !T.exit_t && V);
    const staleAt = !F && held ? fmts(held.at) : null, open = T && T.id && !T.exit_t ? T : null;
```

Replace

```js
name: VS != null ? 'STOP' : 'KILL', bornHM:
```

with

```js
name: (VS != null ? 'STOP' : 'KILL') + (staleAt ? ' STALE ' + staleAt : ''), bornHM:
```

Replace

```js
inTrade, away, more, dir, trade: inTrade ? { T, V, VL } : null,
```

with

```js
inTrade, away, more, open, staleAt, fold: fd || null, dir, trade: inTrade ? { T, V, VL } : null,
```

In `src/shell/panel.js`, replace

```js
  const vtag = (X) => { const t = [X.away ? `<b>${esc(X.away)}</b> · lines: ${esc(X.away)} chart` : '', X.more ? `+${X.more} open` : ''].filter(Boolean);
```

with

```js
  const vtag = (X) => { const t = [X.staleAt ? `<span class="am">STALE ${esc(X.staleAt)}</span>` : '', X.away ? `<b>${esc(X.away)}</b> · lines: ${esc(X.away)} chart` : '', X.more ? `+${X.more} open` : ''].filter(Boolean);
```

Replace

```js
    const fd = F && F.fold, h2 = fd && fd.hold2;   // v2.9 the two voices the ladder reads, verbatim, in its detail
```

with

```js
    const fd = X.fold, h2 = fd && fd.hold2;   // v2.9 the two voices the ladder reads, verbatim, in its detail (F7: X.fold, held when stale)
```

Replace

```js
    const vc = X.inTrade && F && F.fold && F.fold.voice;
```

with

```js
    const vc = X.inTrade && X.fold && X.fold.voice;   // F7: X.fold is the held trade's while the frame is stale
```

Replace

```js
    if (X.inTrade) { const T = X.trade.T, armed = arm && T && arm.id === T.id;
```

with

```js
    if (X.inTrade || X.open) { const T = X.open || X.trade.T, armed = arm && T && arm.id === T.id;   // F7: never MARK while a trade is open
```

Replace

```js
    const vcOk = X.inTrade && F && F.fold && F.fold.voice && F.fold.voice.ok;   // v2.9: the FOLD board is the voice's detail
```

with

```js
    const vcOk = X.inTrade && X.fold && X.fold.voice && X.fold.voice.ok;   // v2.9: the FOLD board is the voice's detail (F7: X.fold)
```

Replace

```js
(vcOk ? mapDetail(F.fold.voice) : '')
```

with

```js
(vcOk ? mapDetail(X.fold.voice) : '')
```

- [ ] **Step 4: Run the suites and see them pass.**

Run: `node build.mjs --out .baseline/v211-next; for s in shell panel overlay; do OFD_DIST=.baseline/v211-next node test/$s.mjs | tail -1; done`
Expected: `0 failed` on all three. The "v2.6 2" check's hand-built "in trade" model (`inTrade: true`, no `open`) still gets I'M OUT, through `X.trade.T`.

---

### Task 4: The Float never shows an unknown word as HOLD, nor a dead server's voice as live (F8, A72)

**Files:**
- Modify: `ui-v2/src/pro/Float.tsx`:
  - `:10`: the import;
  - `:14-15`: `VCLS`, `RANK`;
  - `:18`: `ageOf` after `contract`;
  - `:28`: `wordOf`;
  - `:42`: the clock;
  - `:51`: `liveEl`;
  - `:136`: the one-line word;
  - `:152`: the voice's l1.
- Modify: `ui-v2/src/hold/hold.css:503` (append the `.vage` style)
- Test: none in a runner (ui-v2 has none, and none is added). The checks are `tsc`, `vite build` and the controller's render check below.

**Interfaces:**
- Consumes `api.ts`:
  - `isDown(engineWhy)`;
  - `notAnswering(t)`'s `(HH:MM:SS)` suffix (the first failed poll's time; api.ts keeps it, "no churn");
  - `FoldRead.asof` (`HH:MM:SS`, the engine's read time).

**Can affect:** the floating window's word cell, its l1 line and its one-line (collapsed) form.

**Untouched:**
- `api.ts`'s poller (it keeps the last read, as designed);
- `Desk.tsx`'s own `wordOf`;
- the title chime.

- [ ] **Step 1: The failing check (controller, browser; executors record it and go on).**
  - Use the controller's own ui-v2 preview on a free port, never 5173 or 8765, e.g. `npx vite --port 5175 --strictPort` in `ui-v2`. Open `/?fixture=1`: `FIXTURE` stops the Float's poller, so the console drives its store.
  - In the console:

```js
const api = await import('/src/pro/api.ts'), fx = await import('/src/pro/fixture.ts'); localStorage.removeItem('pro.float.closed');
const f = await fx.loadFixture(), t = f.float.trade, m = Object.values(f.float.moments).pop();
api.put({ loaded: true, trades: [t], fold: { [t.id]: { ok: true, id: t.id, trade: t, view: { ...m.view, headline: 'ODD WORD · test' }, asof: '11:04:08' } }, engineWhy: null });
```

  - Today the Float's word cell reads **HOLD**.
  - Then run:

```js
api.put({ fold: { [t.id]: { ok: true, id: t.id, trade: t, view: m.view, asof: '11:04:08', voice: { ok: true, state: 'HOLD', seq: 1, l1: '▲ 22750 CE · 14 min', l2: 'stop 22,640f', l3: 'why: flow saath' } } }, engineWhy: api.notAnswering('11:04:10') });
```

  - Today the voice block shows its three lines with nothing saying the server is dead.

- [ ] **Step 2: Implement.** In `ui-v2/src/pro/Float.tsx`, make eight replacements.

**(a) The import.** Replace

```tsx
import { hms, tradeOp, useStore, type Trade } from './api'
```

with

```tsx
import { hms, isDown, tradeOp, useStore, type Trade } from './api'
```

**(b) The word table.** Replace

```tsx
const VCLS: Record<string, string> = { HOLD: 'v-HOLD', 'PAST GIVE-UP': 'v-WATCH', FOLD: 'v-FOLD', "CAN'T CHECK": 'v-PATA' }
```

with

```tsx
const VCLS: Record<string, string> = { HOLD: 'v-HOLD', 'PAST GIVE-UP': 'v-WATCH', FOLD: 'v-FOLD', "CAN'T CHECK": 'v-PATA', '?': 'v-PATA' }
```

**(c) The rank table.** Replace

```tsx
const RANK: Record<string, number> = { FOLD: 0, 'PAST GIVE-UP': 1, "CAN'T CHECK": 2, HOLD: 3 }
```

with

```tsx
const RANK: Record<string, number> = { FOLD: 0, 'PAST GIVE-UP': 1, "CAN'T CHECK": 2, '?': 2, HOLD: 3 }
```

**(d) The age helper.** Replace

```tsx
const contract = (t: Trade) => `${t.k} ${t.side}`
```

with

```tsx
const contract = (t: Trade) => `${t.k} ${t.side}`
// F8 (25 Oct): the read's age off its own clock (/api/fold's asof, HH:MM:SS today), beside l1
const ageOf = (asof: string | undefined, now: number) => {
  const q = /^(\d\d):(\d\d):(\d\d)/.exec(asof ?? '')
  if (!q) return '?'
  const d = new Date(now)
  d.setHours(+q[1], +q[2], +q[3], 0)
  const s = Math.round((now - d.getTime()) / 1000)
  return s < 0 ? '?' : s < 90 ? `${s}s` : `${Math.round(s / 60)} min`
}
```

**(e) The unknown word.** Replace

```tsx
WORDS.find(w => h.toUpperCase().startsWith(w)) ?? 'HOLD'
```

with

```tsx
WORDS.find(w => h.toUpperCase().startsWith(w)) ?? '?'   // F8 (25 Oct, F09): an unknown word is ?, never the safe-looking HOLD
```

**(f) The clock.** Replace

```tsx
  const [h, setH] = useState(420)
```

with

```tsx
  const [h, setH] = useState(420)
  const [now, setNow] = useState(() => Date.now())                     // F8: the age ticks while the poller is quiet
  useEffect(() => { const t = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(t) }, [])
```

**(g) The live / NOT LIVE label.** Replace

```tsx
  const red = word === 'FOLD' || vc?.state === 'EXIT'
```

with

```tsx
  const red = word === 'FOLD' || vc?.state === 'EXIT'
  // F8 (25 Oct, F02): api.ts keeps the last read when a poll fails; say so -- NOT LIVE since the first failure (Pro.tsx:35's isDown)
  const down = isDown(st.engineWhy), since = /\((\d\d:\d\d:\d\d)\)$/.exec(st.engineWhy ?? '')?.[1] ?? '?'
  const liveEl = cur && <span className={`vage${down ? ' dead' : ''}`}>{down ? `NOT LIVE since ${since}` : ageOf(st.fold[cur.id]?.asof, now)}</span>
```

**(h) The two places it shows.** Replace

```tsx
    {vc && min ? <span className={`word fw ${VSTATE[vc.state]}`}>{vc.state}</span> : <span className={`word fw ${VCLS[word!]}`}>{word}</span>}
```

with

```tsx
    {vc && min ? <span className={`word fw ${VSTATE[vc.state]}`}>{vc.state}</span> : <span className={`word fw ${VCLS[word!]}`}>{word}</span>}
    {(!vc || min) && liveEl}
```

Then replace

```tsx
    <div className="v1">{vc.l1}</div>
```

with

```tsx
    <div className="v1">{vc.l1}{liveEl}</div>
```

In `ui-v2/src/hold/hold.css` (its last line, `:503`), replace

```css
.hv .voice .vd{position:absolute;right:var(--s2);bottom:var(--s2);border:1px solid var(--border-strong);border-radius:var(--r);background:var(--surface-raised);font:var(--t11)/16px var(--f-num);padding:0 6px;color:var(--text-secondary)}
```

with

```css
.hv .voice .vd{position:absolute;right:var(--s2);bottom:var(--s2);border:1px solid var(--border-strong);border-radius:var(--r);background:var(--surface-raised);font:var(--t11)/16px var(--f-num);padding:0 6px;color:var(--text-secondary)}
/* F8 (25 Oct): the read's age beside l1 -- and NOT LIVE since hh:mm:ss when the poller has no answer (api.ts isDown) */
.hv .vage{margin-left:var(--s2);font:500 var(--t11)/1 var(--f-num);color:var(--text-secondary);white-space:nowrap}
.hv .vage.dead{color:var(--negative);font-weight:700}
```

- [ ] **Step 3: Typecheck and build.**

Run: `cd "/c/Users/kaam/Desktop/operator mode/tapemap/ui-v2" && ./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: `tsc` prints nothing; `vite build` ends `✓ built in …`.

- [ ] **Step 4: The passing check (controller, browser, light mode, one screenshot each).** Run Step 1's two snippets again (reload the page first).
  - The first: the Float's word cell reads **`?`** in the `v-PATA` grey, never HOLD.
  - The second: the voice block's first line ends **`NOT LIVE since 11:04:10`** in red.
  - Then run `api.put({ engineWhy: null })`. The same place shows the read's age (e.g. `7 min`), and it ticks every second.
  - Collapse the window (chevron). The one-line form shows the same label after the word.

---

### Task 5: One stop, or "could not check": no fallback stop on any face (F9, A73)

**Files:**
- Modify: `src/shell/main.js:342` (the STOP line, as Task 3 left it)
- Modify: `src/shell/panel.js:379` (the could-not-speak line, as Task 2 left it)
- Modify: `ui-v2/public/validate2/app.js`:
  - `:138-139`: the ladder's STOP line;
  - `:319-320`: the to-stop cells;
  - above `:481`: add `voiceStop`.
- Modify: `ui-v2/src/pro/Desk.tsx:134` (the Float detail's inval)
- Test:
  - `test/shell.mjs:236`: the §4 in-trade fold now carries a voice, plus a new block;
  - `test/panel.mjs:525` (updated), plus a new block;
  - `test/overlay.mjs:156,158` (updated);
  - Create: `tapemap/test/validate_app_harness.cjs` and `tapemap/test_validate_app.py`.

**Interfaces:**
- Produces in Validate: `voiceStop(t, T) -> { f, s, src } | { why }`.
  - `{ f, s, src }` is the voice's `stop_f` / `stop_s` / `stop_src`.
  - `{ why }` is `"could not check — …"`, from the voice's why, else the refused fold's why (live), or the replay's why (off the clock).
- The panel's STOP line exists only when `fold.voice.ok && fold.voice.stop_f != null`. Its name is always `STOP` (with `STALE …` from Task 3).

**Can affect:** what the three faces show as the stop while the voice cannot speak (before the mark seeds, a refused fold, or an old server).

**Untouched:**
- the PLAN's flat KILL and T1 (§1i FADE KILL included);
- the PULLBACK line;
- `engine.js` and its prototype row (`app.js:309` and `:483` still print the prototype's "out if … fut accepted": DEV-FACES F12, not in Phase 2);
- the inval cell while the voice is ok (C6 cuts it).

- [ ] **Step 1: Write the failing tests.**

In `test/shell.mjs`, replace

```js
  const fold = { trade: { id: 'T9', k: 23000, side: 'PE', role: 'long', t0: '10:05:00' }, view: { headline: 'HOLD', d: -1, E: last + 5, G: { px: last + 30, set_t: '10:05' }, A: { k: 22900, px: last - 60 }, events: [] } };
```

with

```js
  const fold = { trade: { id: 'T9', k: 23000, side: 'PE', role: 'long', t0: '10:05:00' }, view: { headline: 'HOLD', d: -1, E: last + 5, G: { px: last + 30, set_t: '10:05' }, A: { k: 22900, px: last - 60 }, events: [] },
    voice: { ok: true, state: 'HOLD', seq: 1, l1: '', l2: '', l3: '', stop_f: last + 30 } };   // F9: the in-trade stop is the voice's, never a fallback
```

Then replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review F9 (A73): with the voice refused there is no stop on the chart -- not validate's inval, not the engine's G
guard('F9 no voice, no stop', () => {
  const app = run(bars.length), last = bars[bars.length - 1].c;
  const fold = (voice) => ({ id: 'T9', trade: { idx: 'NIFTY', k: 23000, ty: 'PE', side: 'BUY', p0: 120, entry_t: '10:05:00', exit_t: null },
    view: { headline: 'HOLD', d: -1, E: last + 5, G: { px: last + 30, set_t: '10:05' }, A: { px: last - 60 }, events: [] }, ...(voice ? { voice } : {}) });
  const kills = () => app.overlay().v2.lines.filter((x) => x.kind === 'kill');
  app.win._reply = STUB({ fold: fold(null), validate: { level: { inval: last + 25 } } }); app.deliver(); app.tick(); const none = kills();
  app.win._reply = STUB({ fold: fold({ ok: false, why: 'could not check — HOLD v2 has no line yet' }) }); app.deliver(); app.tick(); const refused = kills();
  app.win._reply = STUB({ fold: fold({ ok: true, state: 'HOLD', seq: 1, l1: '', l2: '', l3: '', stop_f: last + 20 }) }); app.deliver(); app.tick(); const one = kills();
  ok(none.length === 0 && refused.length === 0 && one.length === 1 && one[0].p === last + 20 && one[0].name === 'STOP',
    'F9 the chart\'s stop is the voice\'s or none: ' + JSON.stringify({ none, refused, one: one.map((x) => [x.name, x.p]) }));
});
console.log('');
```

In `test/panel.mjs`, replace

```js
  ok(/>could not check — catching up</.test(P.block('voice')) && /FOLD/.test(P.block('plan')), 'v2.9 a voice that cannot speak says why, and the FOLD board stays as it was');
```

with

```js
  ok(/>stop: could not check — catching up</.test(P.block('voice')) && /FOLD/.test(P.block('plan')) && !/<span>(KILL|STOP) [\d,]+ </.test(P.block('plan')),
    'v2.9 a voice that cannot speak says why (F9: as the stop, and no KILL / STOP level anywhere), and the FOLD board stays as it was');
```

Then replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review F9 (A73): before the mark seeds the engine has no view: the trade is open, the block says why, never MARK
{
  const P = boot();
  P.panel.render(modelOf(bars.length, { read: READ, chain: { atm: 23900, ts: '10:05', strikes: [{ k: 23900, ce: 101.5, pe: 96.2 }] },
    fold: { ok: false, id: 'T9', trade: { idx: 'NIFTY', k: 23900, ty: 'PE', side: 'BUY', p0: 96.2, entry_t: '10:05:00', exit_t: null }, why: 'could not check — the engine is catching up (12 of 40 rows)' } }));
  const act = P.block('act').replace(/&#39;/g, "'");
  ok(/>stop: could not check — the engine is catching up \(12 of 40 rows\)</.test(P.block('voice')) && /I'M OUT/.test(act) && !/MARK/.test(act),
    'F9 a trade the engine has not seeded: "stop: could not check — why", I\'M OUT, no MARK: ' + P.block('voice').replace(/<[^>]*>/g, ' '));
}
console.log('');
```

In `test/overlay.mjs`, replace

```js
  const T = handed({ read: READ(), plan: PLAN, fold: { trade: { id: 'T9', k: 23000, side: 'PE', role: 'long', t0: '10:05:00' }, view: { headline: 'HOLD', d: -1, E: lastC + 5, G: { px: lastC + 30, set_t: '10:05' }, A: { k: 22900, px: lastC - 60 }, events: [] } } });
```

with

```js
  const T = handed({ read: READ(), plan: PLAN, fold: { trade: { id: 'T9', k: 23000, side: 'PE', role: 'long', t0: '10:05:00' }, view: { headline: 'HOLD', d: -1, E: lastC + 5, G: { px: lastC + 30, set_t: '10:05' }, A: { k: 22900, px: lastC - 60 }, events: [] },
    voice: { ok: true, state: 'HOLD', seq: 1, l1: '', l2: '', l3: '', stop_f: lastC + 30 } } });   // F9: the stop is the voice's
```

and replace

```js
r.texts.includes('KILL')
```

with

```js
r.texts.includes('STOP')
```

Create `tapemap/test/validate_app_harness.cjs`:

```js
// validate_app_harness.cjs -- boots the Validate face's app.js (ui-v2/public/validate2/app.js) in node with its browser globals
// stubbed, for test_validate_app.py (25 Oct review F9 / F10). As shell.mjs does with main.js, a test seam is appended to the
// source as it is loaded (globalThis.__app); the shipped file is not changed. argv[2] names the scenario; stdout is its JSON.
const fs = require("fs"), vm = require("vm"), path = require("path");
const SRC = fs.readFileSync(path.join(__dirname, "..", "ui-v2", "public", "validate2", "app.js"), "utf8")
  .replace(/boot\(\);\s*\}\)\(\);\s*$/, "boot(); globalThis.__app = { S, voiceStop };\n})();\n");
const TRADE = { id: "NIFTY-23000PE-long-100000", idx: "NIFTY", k: 23000, side: "PE", role: "long", t0: "10:00:00", p0: 100, exit_t: null };
const DATA = { ok: true, live: true, day: "2026-10-26", now: 37000, idx: { NIFTY: { t: [36000] }, BANKNIFTY: { t: [36000] }, SENSEX: { t: [36000] } } };
const wait = () => new Promise((r) => setTimeout(r, 20));

// a route answers a body, or "hang": a request that answers only when its signal fires (and never, with no signal)
const routes = (over = {}) => (url) => {
  for (const [p, b] of Object.entries(over)) if (url.startsWith(p)) return typeof b === "function" ? b(url) : b;
  return url.startsWith("/api/v2/data") ? DATA : url.startsWith("/api/hold/trades") ? { ok: true, trades: [TRADE] } : { ok: true };
};

function boot(route) {
  const calls = [], fired = [], el = () => ({ hidden: true, style: {}, textContent: "", innerHTML: "" });
  const ctx = {
    console, URLSearchParams, performance, setTimeout, clearTimeout, setInterval: () => 0, requestAnimationFrame: () => 0,
    innerHeight: 900, innerWidth: 1600, location: { search: "" }, localStorage: { getItem: () => null, setItem() {} },
    document: { addEventListener() {}, getElementById: el, querySelector: () => null, body: {}, title: "" },
    preact: { h() {}, render() {} }, preactHooks: { useRef: () => ({}), useEffect() {}, useLayoutEffect() {} }, htm: { bind: () => () => null },
    Engine: { fmt: String, sgn: String, pct: String, L: String, hm: String, hms: String, IDX: ["NIFTY", "BANKNIFTY", "SENSEX"],
              OPEN: 33300, CLOSE: 55800, PRACTICE: 54000, data: null, load(d) { this.data = d; }, events: () => [], setDecode() {}, apply: () => "ok" },
    // the bound as app.js asks for it: a signal this harness fires, carrying the ms it was asked for
    AbortSignal: { timeout: (ms) => { const ac = new AbortController(); ac.signal.ms = ms; fired.push(ac); return ac.signal; } },
    fetch: (url, opts) => {
      const sig = opts && opts.signal, body = route(url);
      calls.push({ url, ms: sig ? sig.ms : null });
      if (body === "hang") return new Promise((_, no) => { if (sig) sig.addEventListener("abort", () => no(new Error("timed out"))); });
      return Promise.resolve({ ok: true, status: 200, json: async () => body });
    },
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { app: () => ctx.__app, calls, timeout: () => fired.splice(0).forEach((ac) => ac.abort()) };
}

const SCEN = {
  // F9: the stop is the voice's, or why there is none -- never engine.js's own give-up G
  async voice_stop() {
    const b = boot(routes());
    await wait();
    const A = b.app(), t = { id: TRADE.id }, at = (f) => { A.S.fold[t.id] = f; return A.voiceStop(t, A.S.T); };
    return { refused: at({ ok: false, id: t.id, why: "could not check — the engine is catching up (12 of 40 rows)" }),
             mute: at({ ok: true, voice: { ok: false, why: "could not check — HOLD v2 has no line yet" } }),
             none: at({ ok: true }),
             spoke: at({ ok: true, voice: { ok: true, stop_f: 23050, stop_s: 23010, stop_src: "HOLD v2" } }) };
  },
};

SCEN[process.argv[2]]().then((o) => process.stdout.write(JSON.stringify(o)),
  (e) => process.stdout.write(JSON.stringify({ err: String((e && e.stack) || e) })));
```

Create `tapemap/test_validate_app.py`:

```python
"""Validate's app.js (ui-v2/public/validate2) in node, through test/validate_app_harness.cjs (25 Oct review F9 / F10): the
one stop and the pollers. The face's engine.js keeps its own harness (test_validate3.py). Skipped when node is not installed."""
import json
import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, "test", "validate_app_harness.cjs")
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def run(scenario):
    r = subprocess.run(["node", HARNESS, scenario], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "err" not in out, out.get("err")
    return out


def test_the_stop_is_the_voices_or_could_not_check_never_engine_js_g():
    """F9 / A73 (DEV-FACES F03): with the voice refused, Validate drew engine.js's own give-up G as the STOP line and the
    to-stop cells -- a third stop beside the panel's and the Float's. Now it is the voice's stop, or "could not check — why"."""
    o = run("voice_stop")
    assert o["refused"] == {"why": "could not check — the engine is catching up (12 of 40 rows)"}
    assert o["mute"] == {"why": "could not check — HOLD v2 has no line yet"}
    assert o["none"] == {"why": "could not check — TapeMap ki voice nahi aayi"}
    assert o["spoke"] == {"f": 23050, "s": 23010, "src": "HOLD v2"}
```

- [ ] **Step 2: Run them and see them fail.**

Run (extension): `node build.mjs --out .baseline/v211-next; for s in shell panel overlay; do OFD_DIST=.baseline/v211-next node test/$s.mjs | grep -E "FAIL|passed"; done`
Expected:
- shell: `FAIL F9 the chart's stop is the voice's or none` (`none` holds the `inval` line, `refused` holds `V.G`).
- panel: `FAIL v2.9 a voice that cannot speak says why (F9…` and `FAIL F9 a trade the engine has not seeded…`.
- overlay: 0 failed (it already passes with a voice stop: `VS` is named STOP today).

Run (TapeMap): `python -m pytest -q test_validate_app.py`
Expected: FAIL. The harness's `err` is `ReferenceError: voiceStop is not defined`.

- [ ] **Step 3: Implement.**

In `src/shell/main.js`, replace

```js
      { kind: 'kill', p: VS != null ? VS : VL && VL.inval != null ? VL.inval : V.G && V.G.px != null ? V.G.px : null, name: (VS != null ? 'STOP' : 'KILL') + (staleAt ? ' STALE ' + staleAt : ''), bornHM: (V.G && V.G.set_t) || t0, mine: true },
```

with

```js
      // F9 (25 Oct): the stop is the voice's or none -- never validate's inval or the engine's G (the three faces showed three stops)
      { kind: 'kill', p: VS, name: 'STOP' + (staleAt ? ' STALE ' + staleAt : ''), bornHM: (V.G && V.G.set_t) || t0, mine: true },
```

In `src/shell/panel.js`, replace

```js
    if (vc) { const w = String(vc.why || 'TapeMap ki voice nahi aayi'); return `<div class="vc rc">${vtag(X)}<span class="abs cant">${esc(/^could not check/.test(w) ? w : 'could not check — ' + w)}</span></div>`; }
```

with

```js
    // F9 (25 Oct): a voice that cannot speak leaves no stop on this face (no KILL line, no fallback number); it says why
    if (X.inTrade || X.open) { const fd = X.fold, w = String((vc && vc.why) || (fd && !fd.ok && fd.why) || 'TapeMap ki voice nahi aayi');
      return `<div class="vc rc">${vtag(X)}<span class="abs cant">stop: ${esc(/^could not check/.test(w) ? w : 'could not check — ' + w)}</span></div>`; }
```

In `ui-v2/public/validate2/app.js`, replace

```js
const r = F.open.r, vs = voiceAt(F.open.t, F.T), on = vs && vs.stop_f != null && vs.stop_s != null, gs = on ? vs.stop_s : r.dist.Gspot, gf = on ? vs.stop_f : r.dist.G;   // A55: one stop on the screen
```

with

```js
const r = F.open.r, vs = voiceStop(F.open.t, F.T);   // A55 + F9 (25 Oct): the voice's stop, or no STOP line
```

Replace

```js
lines.push({ k: "g", y: yOf(gs), side: "R", a: `STOP ${fmt(gs)}`, b: `fut ${fmt(gf)}`, off: off(gs) }); }
```

with

```js
if (vs.f != null) lines.push({ k: "g", y: yOf(vs.s), side: "R", a: `STOP ${fmt(vs.s)}`, b: `fut ${fmt(vs.f)}`, off: off(vs.s) }); }
```

Replace

```js
      ${(() => { const on = vc && vc.stop_f != null && vc.stop_s != null, gf = on ? vc.stop_f : r.dist.G, gs = on ? vc.stop_s : r.dist.Gspot;   // A55: one stop
```

with

```js
      ${(() => { const vs = voiceStop(t, F.T);   // A55 + F9 (25 Oct): one stop, the voice's; without it the screen says why, never engine.js's G
        if (vs.f == null) return html`<div class="counts" data-tip="F9: the stop is the voice's (voice.py); engine.js's give-up is never shown as one"><span class="ca">stop: ${vs.why}</span></div>`;
```

Replace

```js
        const df = on ? Math.abs(r.s.fut - gf) : r.dist.fut, ds = on ? Math.abs(r.s.spot - gs) : r.dist.spot, who = on ? `the voice's stop: ${vc.stop_src} line` : `give-up · ${r.g.Gwhy} · out if accepted`;
```

with

```js
        const gf = vs.f, gs = vs.s, df = Math.abs(r.s.fut - gf), ds = Math.abs(r.s.spot - gs), who = `the voice's stop: ${vs.src} line`;
```

Replace

```js
  // ---------- ONE TRUTH: the engine's word (GET /api/fold?id= view.headline, or the record's headline history) ----------
```

with

```js
  // F9 (25 Oct): THE stop is the voice's -- {f, s, src} -- or why there is none; never engine.js's own give-up G (with the voice
  // refused, the three faces showed three different stops: DEV-FACES F03)
  function voiceStop(t, T) {
    const v = voiceAt(t, T);
    if (v && v.stop_f != null && v.stop_s != null) return { f: v.stop_f, s: v.stop_s, src: v.stop_src };
    const r = S.live && S.liveFollow ? S.fold[t.id] : S.vpath[t.id], w = String((r && r.voice && r.voice.why) || (r && !r.ok && r.why) || "TapeMap ki voice nahi aayi");
    return { why: /^could not check/.test(w) ? w : "could not check — " + w };
  }

  // ---------- ONE TRUTH: the engine's word (GET /api/fold?id= view.headline, or the record's headline history) ----------
```

In `ui-v2/src/pro/Desk.tsx`, replace

```tsx
        <span>inval {lv?.inval != null ? <><b className={(lv.to_inval ?? 1) <= 0 ? 'dn' : ''}>{pts(lv.to_inval)}</b> pts</> : <Abs text={cc(lv?.inval_why, 'no invalidation')} />}</span>
```

with

```tsx
        {/* F9 (25 Oct): no stop but the voice's -- when it cannot speak this says why, never validate's inval in its place */}
        <span>{r?.voice?.ok ? <>inval {lv?.inval != null ? <><b className={(lv.to_inval ?? 1) <= 0 ? 'dn' : ''}>{pts(lv.to_inval)}</b> pts</> : <Abs text={cc(lv?.inval_why, 'no invalidation')} />}</>
          : <>stop: <Abs text={cc(r?.voice?.why ?? (r && !r.ok ? r.why : null), 'TapeMap ki voice nahi aayi')} /></>}</span>
```

- [ ] **Step 4: Run everything touched and see it pass.**

Run (extension): `node build.mjs --out .baseline/v211-next; for s in shell panel overlay; do OFD_DIST=.baseline/v211-next node test/$s.mjs | tail -1; done`
Expected: `0 failed` on all three.

Run (TapeMap): `python -m pytest -q test_validate_app.py test_validate3.py`
Expected: all pass.

Run (ui-v2): `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean, then `✓ built`.

- [ ] **Step 5: The render check (controller, browser, light).**
  - On the controller's own ui-v2 preview, open `/pro.html?fixture=1&state=in&float=x`. That is the Float's detail on the fixture, which carries no voice.
  - If the fixture moment's validate read is live (the `N/M reversal` row shows), the cell after `T1 …` reads `stop: could not check — TapeMap ki voice nahi aayi`, and the word `inval` is absent.
  - Take one screenshot.

---

### Task 6: The extension: one POST in flight, an 8 s bound, and "reload" only when the context is gone (F10, extension half)

**Files:**
- Modify: `src/shell/main.js`:
  - `:71`: `waiting`, before `tapeAt`;
  - `:77`: an answer frees the next post;
  - `:453-454`: the post gate.
- Modify: `src/shell/sw.js:4,7`
- Modify: `src/shell/boot.js:4,7,8,10,11`
- Test: `test/shell.mjs`:
  - the D4 guard's two `run(20)` lines (`:491`, `:495`) get a TapeMap that answers;
  - three new blocks go before `console.log('');`.

**Interfaces:**
- Produces in `main.js`:
  - `waiting: boolean`;
  - `POST_WAIT_MS = 10000`: a post is given up after this, as `sw.js` always answers within 8 s.
- Produces in `sw.js`: `TIMEOUT_MS = 8000`. A timeout answers `{ ok: false, why: 'TapeMap not answering (8 s)' }`.
- Produces in `boot.js`: `gone()`. It returns `TapeMap not answering` while `chrome.runtime.id` exists, else `extension context gone — reload the tab`.

**Can affect:**
- post frequency against a slow or wedged TapeMap (at most one in flight);
- the hold door's mark / exit POSTs, which get the same 8 s bound;
- the "Extension reload hua" banner, which now shows only when the context really is gone.

**Untouched:**
- the POST body;
- the frame cadence while TapeMap answers (once a second);
- `panel.js`'s banner test (`/extension context gone/`).

- [ ] **Step 1: Write the failing tests.**

In `test/shell.mjs`, replace

```js
  const a = run(20);
```

with

```js
  const a = run(20); a.win._reply = STUB(); a.deliver();   // F19: TapeMap answers, so each post frees the next
```

and replace

```js
  const b = run(20);
```

with

```js
  const b = run(20); b.win._reply = STUB(); b.deliver();
```

Then replace

```js
console.log('');
```

with

```js
// ---- 25 Oct review F10 (F19): one frame post in flight -- a hung TapeMap gets no queue that replays as a burst
guard('F19 one post in flight', () => {
  const app = run(58), n = () => app.win._posted.filter((o) => o.kind === 'frame').length;
  const n0 = n();                                                           // the boot post: no answer comes
  app.win._advanceClock(1100); app.tick(); app.win._advanceClock(1100); app.tick(); const n1 = n();
  app.win._advanceClock(10000); app.tick(); const n2 = n();                // given up after 10 s: the next one goes
  app.win._reply = STUB(); app.deliver(); app.win._advanceClock(1100); app.tick(); app.win._advanceClock(1100); app.tick(); const n3 = n();
  ok(n0 === 1 && n1 === 1 && n2 === 2 && n3 === 4, 'F19 no second post while one is in flight; given up at 10 s; answered posts go once a second: ' + JSON.stringify([n0, n1, n2, n3]));
  Date.now = REAL_NOW;
});
// ---- 25 Oct review F10 (F06): a missing reply says "reload" only when the extension context is really gone
guard('F06 the relay blames a reload only when the context is gone', () => {
  const src = fs.readFileSync(path.join(root, '..', DIST, 'src', 'boot.js'), 'utf8');
  const relay = (runtime) => { const on = [], got = [], w = { addEventListener: (k, f) => on.push(f), postMessage: (m) => got.push(m) };
    new Function('window', 'chrome', src)(w, { runtime });
    on.forEach((f) => f({ source: w, data: { __ofdOut: { kind: 'frame' } } }));
    return got.map((m) => (m.__ofdFrame || {}).why); };
  const slow = relay({ id: 'ofd', sendMessage: (m, cb) => cb(undefined) });                            // the service worker gave no reply
  const dead = relay({ sendMessage: () => { throw new Error('Extension context invalidated.'); } });   // reloaded under the page: no id
  ok(JSON.stringify(slow) === '["TapeMap not answering"]' && JSON.stringify(dead) === '["extension context gone — reload the tab"]',
    'F06 a missing reply blames a reload only when chrome.runtime.id is gone: ' + JSON.stringify({ slow, dead }));
});
// ---- 25 Oct review F10 (F19): the service worker's fetch gives up at 8 s as "not answering", never a hang, never "reload"
{
  const src = fs.readFileSync(path.join(root, '..', DIST, 'src', 'sw.js'), 'utf8');
  let listen = null, asked = null; const ac = new AbortController();
  const chromeStub = { runtime: { onMessage: { addListener: (f) => { listen = f; } }, getURL: (x) => x }, notifications: { create() {} } };
  const hung = (url, o) => new Promise((res, rej) => { o.signal.addEventListener('abort', () => rej(o.signal.reason)); });
  new Function('chrome', 'fetch', 'AbortSignal', src)(chromeStub, hung, { timeout: (ms) => { asked = ms; return ac.signal; } });
  const reply = new Promise((res) => listen({ frame: { kind: 'frame' } }, {}, res));
  ac.abort(new DOMException('signal timed out', 'TimeoutError'));
  const r = await Promise.race([reply, new Promise((res) => setTimeout(() => res({ why: 'no reply in 1 s' }), 1000))]);
  ok(asked === 8000 && r.ok === false && /not answering/.test(r.why) && !/reload/.test(r.why), 'F19 a hung fetch times out at 8 s as "not answering": ' + JSON.stringify({ asked, r }));
}
console.log('');
```

(The last block uses a top-level `await`. It is legal in this ES module, inside its `if` block, and does not run when `panel.mjs` / `overlay.mjs` import `shell.mjs`.)

- [ ] **Step 2: Run them and see them fail.**

Run: `node build.mjs --out .baseline/v211-next; OFD_DIST=.baseline/v211-next node test/shell.mjs | grep -E "FAIL|passed"`
Expected:
- `FAIL F19 no second post while one is in flight…`: `[1,3,4,6]`, a post every tick.
- `FAIL F06 a missing reply blames a reload…`: `slow` is the reload sentence.
- `FAIL F19 a hung fetch times out at 8 s…`: `asked` null, why `tapemap not reachable — …`.
- The D4 checks still pass.

- [ ] **Step 3: Implement.**

In `src/shell/main.js`, replace

```js
  let tapeAt = 0;   // v2: no feed-loss tone and no feed-loss banner (Mary dropped it, 18 Oct)
```

with

```js
  // F19 (25 Oct): one post in flight. A wedged TapeMap used to get a post a second that queued and replayed as a burst; sw.js
  // answers every post within its 8 s bound, so a post with no answer in POST_WAIT_MS is given up and the next one goes
  let waiting = false; const POST_WAIT_MS = 10000;
  let tapeAt = 0;   // v2: no feed-loss tone and no feed-loss banner (Mary dropped it, 18 Oct)
```

Replace

```js
    const f = ev.data.__ofdFrame; dirty = true;
```

with

```js
    const f = ev.data.__ofdFrame; dirty = true; waiting = false;   // F19: any answer, ok or not, frees the next post
```

Replace

```js
      if (r.closed.length && nowT - lastPost >= 1000) {
```

with

```js
      if (r.closed.length && nowT - lastPost >= 1000 && (!waiting || nowT - lastPost >= POST_WAIT_MS)) {
```

Replace

```js
        lastPost = nowT;
```

with

```js
        lastPost = nowT; waiting = true;
```

In `src/shell/sw.js`, replace

```js
const post = (url, body, sendResponse) => fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
```

with

```js
const TIMEOUT_MS = 8000;   // F19 (25 Oct): a wedged TapeMap is "not answering" in 8 s, never a relay that hangs (ui-v2 hold/store.ts j()'s bound)
const post = (url, body, sendResponse) => fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal: AbortSignal.timeout(TIMEOUT_MS) })
```

and replace

```js
  .catch((e) => sendResponse({ ok: false, why: 'tapemap not reachable — ' + (e.message || e) }));
```

with

```js
  .catch((e) => sendResponse({ ok: false, why: e && e.name === 'TimeoutError' ? 'TapeMap not answering (8 s)' : 'tapemap not reachable — ' + (e.message || e) }));
```

In `src/shell/boot.js`, replace

```js
  const gone = { ok: false, why: 'extension context gone — reload the tab' };   // the extension was reloaded under this page: say so instead of blaming TapeMap
```

with

```js
  // no reply: blame an extension reload only when this page's context really is gone (chrome.runtime.id); a slow or wedged
  // TapeMap, a closed port, or a service worker restarted mid-fetch is "TapeMap not answering" (25 Oct review F06)
  const gone = () => (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id
    ? { ok: false, why: 'TapeMap not answering' } : { ok: false, why: 'extension context gone — reload the tab' });
```

Then make four one-token replacements:
- `{ __ofdFrame: resp || gone }` → `{ __ofdFrame: resp || gone() }`
- `{ __ofdHoldReply: resp || gone }` → `{ __ofdHoldReply: resp || gone() }`
- `{ __ofdFrame: gone }` → `{ __ofdFrame: gone() }`
- `{ __ofdHoldReply: gone }` → `{ __ofdHoldReply: gone() }`

- [ ] **Step 4: Run all six suites and see them pass.**

Run: `node build.mjs --out .baseline/v211-next; for s in fit engine shell overlay panel decoder; do OFD_DIST=.baseline/v211-next node test/$s.mjs | tail -1; done`
Expected: `0 failed` on all six.

---

### Task 7: ui-v2 and Validate: every poller gives up in 8 s and keeps one request in flight (F10, ui half)

**Files:**
- Modify: `ui-v2/src/hold/store.ts:14` (export `TIMEOUT_MS`)
- Modify: `ui-v2/src/data.ts`:
  - `:6`: the import;
  - `:1267`, `:1270-1271`, `:1314`: the signals;
  - `:1308`: `tick` → `read`;
  - `:1349-1350`: one read in flight.
- Modify: `ui-v2/public/validate2/app.js`:
  - `:533`: the bound and the busy flags;
  - `:541`: `poll`'s fetch;
  - `:554-559`: `pollTrades`;
  - `:563`, `:568-572`: `pollFold`;
  - `:594`: `pollFlat`.
- Test: `tapemap/test/validate_app_harness.cjs` (the seam, plus a `pollers` scenario) and `tapemap/test_validate_app.py` (append).

**Interfaces:**
- Produces: `hold/store.ts` `export const TIMEOUT_MS = 8000`. `j()` is unchanged.
- **Spec ambiguity, resolved.** The spec says to reuse `j()` in `data.ts`, but `j()` returns parsed JSON and drops the HTTP status. `fetchIdx` needs that status for its proxy-502 rule (`data.ts:1284`). So `data.ts` takes `j()`'s bound, `TIMEOUT_MS`, through the native `AbortSignal.timeout`.
- Validate is a static `public/` script and cannot import TypeScript, so it uses `AbortSignal.timeout(8000)` with the same number.
- `poll()` (`/api/v2/data`) is bounded too. Without that, the spec's own check ("a mock that never answers turns the bar NOT LIVE / FEED DEAD") can never pass.

**Can affect:**
- 5173's NOT LIVE banner: a wedged server now turns it on within 8 s of a tick;
- Validate's FEED DEAD band and its "not answering" voice;
- request load against a slow server.

**Untouched:**
- `fetchIdx`'s reachability rules;
- the poll intervals;
- `pro/api.ts` (already on `j()`);
- `engine.js`.

- [ ] **Step 1: Write the failing test.**

In `tapemap/test/validate_app_harness.cjs`, replace

```js
globalThis.__app = { S, voiceStop };
```

with

```js
globalThis.__app = { S, voiceStop, poll, pollTrades, pollFold, pollFlat };
```

and replace

```js
const SCEN = {
```

with

```js
const SCEN = {
  // F10 (DEV-FACES F20): each poller keeps one request in flight, bounded at 8 s; a request that timed out frees its poller
  async pollers() {
    let nT = 0;
    const b = boot(routes({ "/api/hold/trades": () => (++nT === 1 ? { ok: true, trades: [TRADE] } : "hang"),
                            "/api/fold?id=": "hang", "/api/fold/flat": "hang", "/api/v2/data?": "hang" }));
    await wait();                                                  // boot: its pollTrades answered, its pollFlat hangs
    const A = b.app(), n = (p) => b.calls.filter((c) => c.url.startsWith(p)).length;
    A.pollFold(); A.pollFold(); A.pollFlat(); A.pollTrades(); A.pollTrades(); A.poll(false); A.poll(false);
    await wait();
    const inFlight = { fold: n("/api/fold?id="), flat: n("/api/fold/flat"), trades: n("/api/hold/trades"), data: n("/api/v2/data?") };
    b.timeout();                                                   // the 8 s bound fires on every request still out
    await wait();
    A.pollFold(); A.pollFlat(); A.pollTrades();
    await wait();
    return { inFlight, after: { fold: n("/api/fold?id="), flat: n("/api/fold/flat"), trades: n("/api/hold/trades") },
             bounded: b.calls.filter((c) => /^\/api\/(fold|hold\/trades|v2\/data\?)/.test(c.url)).map((c) => c.ms),
             feed: A.S.feed, fold: A.S.fold[TRADE.id] };
  },
```

Append to `tapemap/test_validate_app.py`:

```python


def test_each_poller_has_one_request_in_flight_and_gives_up_in_8_s():
    """F10 (DEV-FACES F20, F05): pollFold / pollTrades / pollFlat had no in-flight guard and no timeout, so about 5 requests a
    second stacked on a wedged server and a late reply could overwrite a newer voice; /api/v2/data's poll hung for good and
    FEED DEAD never came. Now each keeps one request in flight, bounded at 8 s (ui-v2 hold/store.ts j()'s bound)."""
    o = run("pollers")
    assert o["inFlight"] == {"fold": 1, "flat": 1, "trades": 2, "data": 1}
    assert o["after"] == {"fold": 2, "flat": 2, "trades": 3}
    assert o["bounded"] and set(o["bounded"]) == {8000}
    assert o["feed"] == "dead" and o["fold"] == {"ok": False, "why": "not answering"}
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_validate_app.py::test_each_poller_has_one_request_in_flight_and_gives_up_in_8_s`
Expected: FAIL with `assert {'fold': 2, 'flat': 2, 'trades': 3, 'data': 1} == {'fold': 1, 'flat': 1, 'trades': 2, 'data': 1}`.

The failing check for `data.ts` (controller, browser; executors record it):
- On the controller's own ui-v2 preview, open `/` and run in the console `window.fetch = (u, o) => new Promise((_, no) => o && o.signal && o.signal.addEventListener('abort', () => no(o.signal.reason)))`.
- Today the top bar never turns NOT LIVE: every number freezes.

- [ ] **Step 3: Implement.**

In `ui-v2/src/hold/store.ts`, replace

```ts
const POLL_MS = 15000, TIMEOUT_MS = 8000
```

with

```ts
const POLL_MS = 15000
export const TIMEOUT_MS = 8000   // the one fetch bound: j() below, and data.ts's 5 s poll (25 Oct review F10)
```

In `ui-v2/src/data.ts`, make seven replacements.

**(a) The import.** Replace

```ts
import { useCallback, useEffect, useRef, useState } from 'react'
```

with

```ts
import { useCallback, useEffect, useRef, useState } from 'react'
import { TIMEOUT_MS } from './hold/store'   // F05 (25 Oct): the one fetch bound, j()'s 8 s
```

**(b)–(d) The signals.** Replace

```ts
const gP = fetch('/api/calls?idx=' + k).then(
```

with

```ts
const gP = fetch('/api/calls?idx=' + k, { signal: AbortSignal.timeout(TIMEOUT_MS) }).then(
```

Replace

```ts
          fetch('/api/data?idx=' + k + '&interval=' + interval),
          fetch('/api/chain?idx=' + k),
```

with

```ts
          fetch('/api/data?idx=' + k + '&interval=' + interval, { signal: AbortSignal.timeout(TIMEOUT_MS) }),
          fetch('/api/chain?idx=' + k, { signal: AbortSignal.timeout(TIMEOUT_MS) }),
```

Replace

```ts
fetch('/api/health').then(
```

with

```ts
fetch('/api/health', { signal: AbortSignal.timeout(TIMEOUT_MS) }).then(
```

**(e) The rename.** Replace

```ts
    async function tick() {
```

with

```ts
    async function read() {
```

**(f) One read in flight.** Replace

```ts
    tick()
    const id = window.setInterval(tick, 5000)
```

with

```ts
    // F05 (25 Oct): one read in flight, and every fetch in it gives up after 8 s, so a wedged server turns the bar NOT LIVE
    // (fetchIdx's catch: no answer on 8765) instead of freezing every number while the polls stack up
    let busy = false
    const tick = async () => { if (busy) return; busy = true; try { await read() } finally { busy = false } }
    tick()
    const id = window.setInterval(tick, 5000)
```

In `ui-v2/public/validate2/app.js`, make the bound and the flags first. Replace

```js
  let polling = false, lastPoll = 0;
```

with

```js
  // F10 (25 Oct): each poller keeps ONE request in flight and gives up after 8 s (ui-v2 hold/store.ts j()'s bound): a wedged
  // server turns FEED DEAD / "not answering" instead of stacking ~5 requests a second, and a late reply never overwrites a newer one
  const TIMEOUT_MS = 8000;
  let polling = false, lastPoll = 0, tradesBusy = false, foldBusy = false, flatBusy = false;
```

**`poll`.** Replace

```js
      const r = await fetch(`/api/v2/data?day=${E.data.day}&since=${since}`); if (!r.ok) throw new Error("HTTP " + r.status);
```

with

```js
      const r = await fetch(`/api/v2/data?day=${E.data.day}&since=${since}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); if (!r.ok) throw new Error("HTTP " + r.status);
```

**`pollTrades`.** Replace

```js
  async function pollTrades() {
```

with

```js
  async function pollTrades() {
    if (tradesBusy) return;
    tradesBusy = true;
```

Replace

```js
const r = await fetch("/api/hold/trades"); const d = await r.json();
```

with

```js
const r = await fetch("/api/hold/trades", { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json();
```

Replace

```js
const r = await fetch(`/api/fold/record?day=${E.data.day}`); const d = await r.json();
```

with

```js
const r = await fetch(`/api/fold/record?day=${E.data.day}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json();
```

Replace

```js
    } catch (e) { S.apiWhy = `trades: ${e.message || e} (GET ${S.live ? "/api/hold/trades" : "/api/fold/record?day=" + E.data.day})`; }
```

with

```js
    } catch (e) { S.apiWhy = `trades: ${e.message || e} (GET ${S.live ? "/api/hold/trades" : "/api/fold/record?day=" + E.data.day})`; } finally { tradesBusy = false; }
```

**`pollFold`.** Replace

```js
    if (!S.live) return;
```

with

```js
    if (!S.live || foldBusy) return;
    foldBusy = true;
```

Replace

```js
const r = await fetch(`/api/fold?id=${encodeURIComponent(t.id)}`); const d = await r.json(); S.fold[t.id] = d;
```

with

```js
const r = await fetch(`/api/fold?id=${encodeURIComponent(t.id)}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json(); S.fold[t.id] = d;
```

Replace

```js
    }
    up();
  }
  async function pollVpath() {
```

with

```js
    }
    foldBusy = false;
    up();
  }
  async function pollVpath() {
```

**`pollFlat`.** Replace

```js
    try { const r = await fetch(`/api/fold/flat?idx=${S.focus}`); const d = await r.json(); S.flat[S.focus] = d; } catch (e) { S.flat[S.focus] = { ok: false }; }
```

with

```js
    if (flatBusy) return;
    flatBusy = true;
    const i = S.focus;                                                // the index asked for, even if she switches mid-request
    try { const r = await fetch(`/api/fold/flat?idx=${i}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json(); S.flat[i] = d; } catch (e) { S.flat[i] = { ok: false }; }
    flatBusy = false;
```

- [ ] **Step 4: Run and see it pass.**

Run (TapeMap): `python -m pytest -q test_validate_app.py test_validate3.py`
Expected: all pass.

Run (ui-v2): `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean, then `✓ built`.

- [ ] **Step 5: The passing check (controller, browser, light).** Run Step 2's console line on `/`.
  - Within 13 s (the next 5 s tick plus the 8 s bound; from a fresh load it is 8 s), the top bar reads `NOT LIVE — no answer from the backend on 8765…`.
  - The Float, if a trade is in the store, reads `NOT LIVE since hh:mm:ss` (Task 4).
  - Take one screenshot.

---

### Task 8: Release 0.5.11, verify the phase, record it, commit on her word

**Files:**
- Modify (extension): `manifest.src.json:4`, `src/shell/recorder.js:39`, `src/engine/v2.js:12`, `docs/V2-BUILD-REPORT.md` (append).
  - The README holds no `0.5.10` (its title says "v0.3.0"; F32, not this phase). It is unchanged.
- Modify (TapeMap): `docs/live/NOTEPAD.md` (A70–A73 statuses, new row A82) and `CLAUDE.md` (the face's version and the pytest line).

- [ ] **Step 1: Bump the version.** Make three replacements:
  - `manifest.src.json`: `"version": "0.5.10",` → `"version": "0.5.11",`
  - `src/shell/recorder.js`: `const OFD_VERSION = '0.5.10';` → `const OFD_VERSION = '0.5.11';`
  - `src/engine/v2.js`: `BUILD: '0.5.10-v2.10',` → `BUILD: '0.5.11-v2.11',`

  Then run: `grep -rn "0\.5\.10" src manifest.src.json README.md`
  Expected: no output.

- [ ] **Step 2: The full server suite.**

Run: `python -m pytest -q`
Expected: Phase 1's count + 3 = 1973 collected. All pass but the 1 skipped and at most the 1 known flaky A49 test. Any other failure: stop, and fix the cause.

- [ ] **Step 3: The full extension verify, on the scratch build.**

Run: `node build.mjs --out .baseline/v211-next; for s in fit engine shell overlay panel decoder; do OFD_DIST=.baseline/v211-next node test/$s.mjs | tail -1; done`
Expected:
- `0 failed` on all six.
- Against v2.10's counts (engine 116, fit 46, shell 139, overlay 39, panel 99, decoder 21): shell 148 (+9), panel 103 (+4), the others unchanged.

- [ ] **Step 4: ui-v2.**

Run: `./node_modules/.bin/tsc --noEmit -p . && npx vite build`
Expected: clean, then `✓ built`.

- [ ] **Step 5: The diffs are only these changes.**

Run: `git diff --stat` in both repos.
Expected:
- **TapeMap:** `fold_live.py`, `server.py` (4 places), `test_fold_live.py`, `ui-v2/src/pro/Float.tsx`, `ui-v2/src/pro/Desk.tsx`, `ui-v2/src/hold/hold.css`, `ui-v2/src/hold/store.ts`, `ui-v2/src/data.ts`, `ui-v2/public/validate2/app.js`. New: `test/validate_app_harness.cjs`, `test_validate_app.py`. Plus Phase 1's own files if they are still uncommitted.
- **Extension:** `src/shell/{main,panel,boot,sw,recorder}.js`, `src/engine/v2.js`, `manifest.src.json`, `test/{shell,panel,overlay}.mjs`.
- No whole-file rewrite, and no `dist-v2` change yet.

- [ ] **Step 6: The controller's browser checks** (Tasks 4, 5 and 7, light, one screenshot each), done and saved with the build report.

- [ ] **Step 7: Build `dist-v2`, on Mary's word.** Her 25 Oct 16:40 delegation is that word. Her Chrome loads `dist-v2` at its next start or Reload, and the rollback copy is taken first:

```bash
cd "/c/Users/kaam/Desktop/Go charting/orderflow-desk" && cp -r dist-v2 .baseline/v210-dist-v2 && npm run verify
```

Expected: `built …dist-v2…`, then the six suites at `0 failed` against `dist-v2`. `git diff --stat dist-v2` shows `src/main.js`, `src/boot.js`, `src/sw.js` and `manifest.json`.

- [ ] **Step 8: Record it.**
  - **NOTEPAD:** in rows A70, A71, A72 and A73, set the last cell to `FIXED (25 Oct, uncommitted; live at the extension Reload 0.5.11 + F5 and her next TapeMap / 5173 start)`. Name the test in the fix cell:
    - A70: `test_fold_live …another_index…` + shell / panel `F6`;
    - A71: shell / panel `F7`;
    - A72: the Float render check;
    - A73: shell / panel `F9` + `test_validate_app …never_engine_js_g`.
  - **NOTEPAD:** add after the A81 row:

```
| A82 | 25 Oct review | **Pollers had no timeout or in-flight guard, and every missing reply was blamed on an extension reload** | DEV-FACES F05 (`data.ts:1263-1271,1349`), F06 (`boot.js:4-9`), F19 (`main.js:453`, `sw.js:4`), F20 (`validate2/app.js:554-596`) | An 8 s bound and one request in flight on every poller; "reload" only when `chrome.runtime.id` is gone | FIXED (25 Oct, uncommitted; live at the extension Reload 0.5.11 + F5 and 5173's next start) |
```

  - **`CLAUDE.md`:**
    - change `- **The face:** the GoCharting extension v2.10 (0.5.10) in` to `- **The face:** the GoCharting extension v2.11 (0.5.11) in`;
    - set the pytest line's counts to what Step 2 printed, with the date.
  - **`orderflow-desk/docs/V2-BUILD-REPORT.md`:** append:

```
# v2.11 — the screens: her trade on any index, a stale frame, one stop, one post (25 Oct 2026 review, Phase 2)

Plan `tapemap/docs/superpowers/plans/2026-10-25-review-phase2-screens.md` (spec `…/specs/2026-10-25-review-fix-cut-stop-design.md`,
F6–F10). Display and plumbing only; no state, stop rule or registered read changed.

- **F6** her open trade on another index (TapeMap `fold_live.frame`): the block wears `SENSEX · lines: SENSEX chart`, no line of
  it is drawn on this chart; `+N open` for her other open trades.
- **F7** a frame 15 s+ old mid-trade keeps the block and the STOP / ENTRY lines, `STALE hh:mm:ss`; no MARK while a trade is open.
- **F9** in a trade the STOP is the voice's or none (no KILL fallback to validate's inval or the engine's G); the block says
  `stop: could not check — <why>`.
- **F10** one frame POST in flight (given up at 10 s); `sw.js` fetch bound 8 s (`TapeMap not answering (8 s)`); `boot.js` says
  reload only when `chrome.runtime.id` is gone.
- **Version 0.5.11** (`manifest.src.json`, `recorder.js`, `v2.js BUILD 0.5.11-v2.11`); `dist-v2` rebuilt.
- **Tests:** shell 148 (+9), panel 103 (+4), overlay 39 (the in-trade line is now the voice's STOP); engine, fit, decoder unchanged.
- **Live at** her Reload of "Order Flow Desk v2" (Chrome shows 0.5.11) + F5 of the GoCharting tab. Any order with the TapeMap
  restart is safe: the other-index fold is opt-in (`away: 1`, sent only by 0.5.11), so a 0.5.10 page never receives one.
- **Rollback:** `.baseline/v210-dist-v2`.
```

- [ ] **Step 9: Show Mary, and wait for her word.** Show both `git diff --stat`s and the screenshots. Say plainly:
  - **What changes on screen:**
    - her SENSEX trade shows on the NIFTY panel (tagged, no lines);
    - a 20 s stale frame keeps the block with STALE, and no MARK;
    - with the voice down, every face says `stop: could not check — why`, never a second stop;
    - the Float says `?` for an unknown word and `NOT LIVE since hh:mm:ss` when the server is gone;
    - a slow server reads "TapeMap not answering", not "reload".
  - **What stays untouched:** §1i–§1q and their browser computations, the voice's states, `fold.py`, the zone machine, the §1d gate, every forward log's rows.
  - **When it goes live, in this order, after a close:**
    1. Reload the extension (0.5.11), then F5 the tab.
    2. Restart TapeMap (the server half of F6).
    3. 5173 picks up ui-v2 at its next start.

- [ ] **Step 10: Commit, ONLY after she says commit.** The controller makes two commits.

```bash
cd "/c/Users/kaam/Desktop/operator mode/tapemap" && git add fold_live.py server.py test_fold_live.py test_validate_app.py test/validate_app_harness.cjs ui-v2/src/pro/Float.tsx ui-v2/src/pro/Desk.tsx ui-v2/src/hold/hold.css ui-v2/src/hold/store.ts ui-v2/src/data.ts ui-v2/public/validate2/app.js docs/live/NOTEPAD.md CLAUDE.md docs/superpowers/plans/2026-10-25-review-phase2-screens.md
git commit -m "review 25 Oct phase 2: the screens, TapeMap half (A70-A73, A82)

- the frame carries her open trade on any index with its idx and open_n; the NIFTY story and log read only NIFTY's
- the Float: an unknown word is ?, the read's age, NOT LIVE since hh:mm:ss
- one stop: Validate and the Float detail show the voice's stop or 'stop: could not check'
- every ui-v2 / Validate poller gives up in 8 s and keeps one request in flight

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cd "/c/Users/kaam/Desktop/Go charting/orderflow-desk" && git add src/shell/main.js src/shell/panel.js src/shell/boot.js src/shell/sw.js src/shell/recorder.js src/engine/v2.js manifest.src.json test/shell.mjs test/panel.mjs test/overlay.mjs dist-v2 docs/V2-BUILD-REPORT.md
git commit -m "v2.11 (0.5.11): the screens (TapeMap review 25 Oct, phase 2)

- her trade on another index: the block with its tag, none of its lines on this chart, +N open
- a stale frame mid-trade keeps the block and STOP / ENTRY, STALE hh:mm:ss; no MARK while a trade is open
- the in-trade STOP is the voice's or none; the block says 'stop: could not check'
- one frame POST in flight; sw.js 8 s bound; boot.js says reload only when the context is gone

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Spec coverage (self-review)

| Spec row | Task | Test that fails today |
|---|---|---|
| F6, server: fold on any index with its idx | 1 | `test_fold_live …another_index…` |
| F6, extension: tag, no lines when idx ≠ chart, "lines: SENSEX chart", "+1 open" | 2 | shell `F6` ×2, panel `F6` ×2 |
| F7: stale keeps the block + STOP / ENTRY, `STALE hh:mm:ss`; no MARK while open | 3 | shell `F7` ×3, panel `F7` |
| F8: `?`; the age; `NOT LIVE since hh:mm:ss` via `engineWhy` / `isDown` | 4 | the controller's render check (no runner, by design) |
| F9: no fallback stop on the panel, Validate or the Float detail; `stop: could not check — <why>` | 5 | shell `F9`, panel `F9` + the v2.9 row, `test_validate_app …g` |
| F10: `data.ts` + Validate pollers bounded, with busy flags; one POST in flight; `sw.js` timeout; `boot.js` id check | 6, 7 | shell `F19` ×2 + `F06`, `test_validate_app …8_s`, the controller's NOT LIVE check |
| Release 0.5.11; verify; Reload + F5 | 8 | — |
