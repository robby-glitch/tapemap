# Order-flow levels and marks on the Trade chart — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry GoCharting's per-price ladder from the `orderflow-desk` extension into TapeMap, record it, compute levels / per-bar flags / a second-opinion mark family from it, and draw them on the existing Trade chart.

**Architecture:** One extension field (`ladder`) rides the existing `POST /api/frame`. `tape_log.py` records bars and the extension's marks write-once. `prints.py` (pure, stdlib) ports the extension's own arithmetic and adds the `tm` detectors. `GET /api/tape` serves bars + levels + two mark families with the three-sentence contract. `ui-v2` polls it and draws through `LevelsOverlay` and candl's indicator pane. Nothing in the extension's reading layer changes.

**Tech Stack:** Python 3 stdlib (server, `tape_log`, `prints`, pytest); Node ESM (extension, fixture generator); TypeScript + React 19 + vendored candl (`ui-v2`).

**Spec:** `docs/superpowers/specs/2026-09-19-orderflow-levels-design.md` — read it first; section refs below (§B…§K) are to it.

## Global Constraints

- `python -m pytest -q` stays green; **every `**N tests pass**` in `README.md`, `CLAUDE.md`, `START-HERE.md`, `context/research-findings.md` must equal the collected count** — `test_docs_claims.py:47–65` fails the suite otherwise.
- Every new forward-log writer is named in `server._isolate_mock_writers` **and** in `test_day_state.py:97–98`'s pin list, and its directory is in `.gitignore` with a reason.
- Never touch `orderflow-desk/src/engine/*` (`BRIEF-for-the-builder.md` §0) or `ui-v2/src/vendor/candl/*` (`VENDOR.md`: pristine).
- Three sentences, never two: `ok:false` always carries `why`; a null field always has a `*_why` sibling (CLAUDE.md rule 6).
- Every number is tagged: counts `[M]`, detections `[I]` (rule 7). No hit rate, no direction verdict, no sound (rules 4, 10; parked-deletions plan).
- The `tm` thresholds are exactly `0.75 / 0.50 / 0.90 / 0.15 / 6` and are not tuned (§J.3). Imbalance defaults are exactly `ratio 3, min 5 lots, run 3` (§E).
- JS `Math.round` rounds half **up**; Python `round` rounds half to even. Wherever this plan ports a `Math.round`, it uses `_jsround(x) = math.floor(x + 0.5)`. This is load-bearing for the parity test.
- Paths: `tapemap` = `C:\Users\kaam\Desktop\operator mode\tapemap`; `orderflow-desk` = `C:\Users\kaam\Desktop\Go charting\orderflow-desk`. All `tapemap` commands run from the `tapemap` root.
- Commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. `data/trigger_log.jsonl` is never staged (CLAUDE.md, last paragraph) — always `git add` by path.

---

## File structure

| file | responsibility | task |
|---|---|---|
| `orderflow-desk/src/shell/main.js` | the POST projection: `ladder` on closed + forming, `rowAnchor` | 1 |
| `orderflow-desk/manifest.src.json`, `src/shell/recorder.js` | version `0.3.1` | 1 |
| `tapemap/tape_log.py` (new) | write-once record of bars and extension marks; readers | 2 |
| `tapemap/test_tape_log.py` (new) | its tests | 2 |
| `tapemap/server.py` | POST hook; `_isolate_mock_writers`; `GET /api/tape` | 3, 8 |
| `tapemap/test_day_state.py`, `.gitignore` | registration pins | 3 |
| `tapemap/test_frame_api.py` | route tests (POST lands files; GET three sentences) | 3, 8 |
| `tapemap/prints.py` (new) | pure arithmetic: rebin, imbalances, flags, profile, nodes, cvd, prior levels, naked POC, `tm` marks | 4, 5, 7 |
| `tapemap/test_prints.py` (new) | hand cases + the parity pin | 4, 5, 6, 7 |
| `tapemap/tools/gen_prints_expected.mjs` (new), `tapemap/test/fixtures/prints_expected_2026-09-11.json` (new) | the parity fixture, generated once from the extension's own code | 6 |
| `tapemap/tools/seed_tape_from_ofd.py` (new) | one-off: a recorded `.ofd.json` → `data/tape/` for the visual check | 9 |
| `ui-v2/src/trade/tape.ts` (new) | `/api/tape` types and the 30 s poll hook | 10 |
| `ui-v2/src/trade/TradeTab.tsx`, `trade/ContractChart.tsx` | wire the reply down; legend line | 10 |
| `ui-v2/src/trade/LevelsOverlay.ts` | `drawPrints` pass: levels, bands, per-bar marks, hollow `tm` glyphs | 11 |
| `ui-v2/src/trade/Callout.tsx` | the hovered bar's `tm` and `ofd` marks, each with its `why` (or the sentence that it has none) | 11b |
| `ui-v2/src/trade/indicators.ts` | delta / CVD pane at 5 and 15 min only | 12 |
| docs (`context/HANDOFF.md`, `START-HERE.md`, `orderflow-desk/HANDOFF.md`, test counts) | | 13 |

---

### Task 1: The wire — `ladder` and `rowAnchor` in the extension's POST

**Files:**
- Modify: `orderflow-desk/src/shell/main.js:234–235`, `:244`
- Modify: `orderflow-desk/manifest.src.json:4`, `orderflow-desk/src/shell/recorder.js:39`
- Test: the extension's own suite, `npm test` (engine, fit, shell, overlay)

**Interfaces:**
- Produces: on the wire, each `closed[i]` and `forming` carry `ladder: [{p, b, s, bt, st}]` (lots, sorted by `p`), and the doc carries `rowAnchor: number` beside `rowSize`. Tasks 2–8 consume exactly these names.

- [ ] **Step 1: Confirm the extension suite is green before touching it**

Run (from `orderflow-desk`): `npm test`
Expected: the four suites print their check counts and exit 0. If not green, stop — the baseline is broken and this task must not be the thing that "fixed" it.

- [ ] **Step 2: Add `ladder` to both projections and `rowAnchor` to the doc**

In `src/shell/main.js`, the `out({...})` call at line 233. Change line 234 from:

```js
          closed: r.closed.map((b) => ({ t: b.t, o: b.o, h: b.h, l: b.l, c: b.c, vol: b.vol, delta: b.delta, buy: b.buy, sell: b.sell, oi: b.oi ?? null, fromTicks: !!b.fromTicks })),
```

to:

```js
          // the ladder travels: TapeMap records it (tape_log.py) and computes levels and prints from it. ~140 KB per
          // post at 15:30, budgeted at server.py:1170. ponytail: full-day ladders every post; send only bars past
          // the reply's have_bars if it ever costs.
          closed: r.closed.map((b) => ({ t: b.t, o: b.o, h: b.h, l: b.l, c: b.c, vol: b.vol, delta: b.delta, buy: b.buy, sell: b.sell, oi: b.oi ?? null, fromTicks: !!b.fromTicks, ladder: b.ladder || [] })),
```

Change line 235 from:

```js
          forming: r.forming ? { t: r.forming.t, o: r.forming.o, h: r.forming.h, l: r.forming.l, c: r.forming.c } : null,
```

to:

```js
          forming: r.forming ? { t: r.forming.t, o: r.forming.o, h: r.forming.h, l: r.forming.l, c: r.forming.c, vol: r.forming.vol, delta: r.forming.delta, buy: r.forming.buy, sell: r.forming.sell, ladder: r.forming.ladder || [] } : null,
```

Change line 244 from:

```js
          rowSize: rowEff, lot: S.lotSize, futPx: r.forming && r.forming.c != null ? r.forming.c : r.closed[r.closed.length - 1].c });
```

to:

```js
          // rowAnchor is the chart's own grid offset (main.js:219): cosmetic to the engine, load-bearing for a face that
          // must sit on GoCharting's rows to be compared with it (spec §J.4)
          rowSize: rowEff, rowAnchor, lot: S.lotSize, futPx: r.forming && r.forming.c != null ? r.forming.c : r.closed[r.closed.length - 1].c });
```

- [ ] **Step 3: Bump the version in both places**

`manifest.src.json` line 4: `"version": "0.2.0",` → `"version": "0.3.1",`
`src/shell/recorder.js` line 39: `const OFD_VERSION = '0.2.0';` → `const OFD_VERSION = '0.3.1';`

- [ ] **Step 4: Build and run the extension suite**

Run: `node build.mjs && npm test`
Expected: builds `dist/`, all four suites exit 0. `test/shell.mjs` boots `dist/src/main.js` against a recorded day and posts through the real wire; it asserts on frame *replies* (`m2.frame.head.gate…`), not on the doc's key set, so the added fields pass through. If it fails naming `ladder` or `rowAnchor`, read the assertion — do not delete it.

- [ ] **Step 5: Verify the posted doc carries the ladder**

Run: `node -e "import('./test/shell.mjs').then(async (M) => { const m = M.run(3); const d = M.win._posted.at(-1); console.log(Object.keys(d).sort().join(' ')); console.log('ladder rows on closed[0]:', (d.closed[0].ladder||[]).length, 'rowAnchor:', d.rowAnchor); })"`
Expected: the key list includes `rowAnchor`; `ladder rows on closed[0]:` is > 0. (If `M.win`/`M.run` are not exported by `shell.mjs`, read its top 40 lines for the export names and adjust the one-liner; do not edit the test.)

- [ ] **Step 6: Commit (the extension repo)**

```bash
git add src/shell/main.js manifest.src.json src/shell/recorder.js dist/
git commit -m "wire: the ladder and rowAnchor travel with every bar to TapeMap (0.3.1)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 7: Tell the operator** — the loaded extension is still 0.2.0 until she reloads it at `chrome://extensions` **and** reloads the GoCharting tab. Nothing downstream sees a ladder before that.

---

### Task 2: `tape_log.py` — the record

**Files:**
- Create: `tapemap/tape_log.py`
- Test: `tapemap/test_tape_log.py`

**Interfaces:**
- Produces:
  - `tape_log.DIR: str` (module-level, redirectable — `_isolate_mock_writers` sets it)
  - `tape_log.day_path(day: str, idx: str) -> str`, `tape_log.marks_path(day: str, idx: str) -> str`
  - `tape_log.append(doc: dict, day: str, idx: str) -> dict` → `{"bars": n_written, "marks": n_written}`
  - `tape_log.read_bars(day: str, idx: str) -> list[dict]` (file order), `tape_log.read_marks(day, idx) -> list[dict]`
  - `tape_log.prior_days(day: str, idx: str, n: int = 5) -> list[str]` (days with a bar file, `< day`, newest first)
  - `tape_log.failed: int`
- Bar row: `{t, o, h, l, c, vol, buy, sell, delta, oi, fromTicks, ladder, rowSize, rowAnchor, lot, session, idx, day}`. Mark row: `{t, kind, side, p, size, src: "ofd", idx, day}`.

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_tape_log.py
"""tape_log.py: the ladder record (spec §C). Write-once per bar and per mark; a
restart seeds from the file; forming is never written; fail-soft."""
import json
import os

import pytest

import tape_log


def _doc(n=3, ladder=True, forming=True, events=None):
    bars = []
    for i in range(n):
        b = {"t": 1789726200000 + i * 300000, "o": 23380 + i, "h": 23384 + i, "l": 23376 + i, "c": 23381 + i,
             "vol": 10 + i, "buy": 6, "sell": 4 + i, "delta": 2 - i, "oi": 17670380, "fromTicks": True}
        if ladder:
            b["ladder"] = [{"p": 23380.0 + i, "b": 4, "s": 2, "bt": 3, "st": 2}, {"p": 23381.0 + i, "b": 2, "s": 2, "bt": 1, "st": 1}]
        bars.append(b)
    return {"kind": "frame", "session": "NIFTY-I|5m|2026-09-19", "idx": "NIFTY", "interval": 5,
            "closed": bars,
            "forming": {"t": 1789726200000 + n * 300000, "o": 1, "h": 2, "l": 0, "c": 1, "vol": 1, "delta": 1, "buy": 1, "sell": 0,
                        "ladder": [{"p": 1.0, "b": 1, "s": 0, "bt": 1, "st": 0}]} if forming else None,
            "events": events if events is not None else [{"t": 1789726200000, "kind": "absorption", "side": 1, "p": 23380.0, "size": 120}],
            "rowSize": 5, "rowAnchor": 0, "lot": 65, "futPx": 23381.0}


@pytest.fixture
def tdir(tmp_path, monkeypatch):
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path))
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    return tmp_path


def _lines(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def test_append_writes_each_closed_bar_once_with_its_ladder(tdir):
    n = tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    assert n == {"bars": 3, "marks": 1}
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert [r["t"] for r in rows] == [1789726200000, 1789726500000, 1789726800000]
    assert rows[0]["ladder"][0] == {"p": 23380.0, "b": 4, "s": 2, "bt": 3, "st": 2}
    for k in ("rowSize", "rowAnchor", "lot", "session", "idx", "day", "fromTicks"):
        assert k in rows[0], k
    assert rows[0]["day"] == "2026-09-19" and rows[0]["idx"] == "NIFTY" and rows[0]["rowSize"] == 5


def test_the_same_post_again_writes_nothing(tdir):
    tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    assert tape_log.append(_doc(3), "2026-09-19", "NIFTY") == {"bars": 0, "marks": 0}
    assert len(_lines(tape_log.day_path("2026-09-19", "NIFTY"))) == 3


def test_a_new_bar_on_a_later_post_is_appended(tdir):
    tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    assert tape_log.append(_doc(4), "2026-09-19", "NIFTY") == {"bars": 1, "marks": 0}


def test_a_restart_seeds_the_seen_set_from_the_file(tdir):
    tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    tape_log._seen_bars.clear()          # a new process
    tape_log._seen_marks.clear()
    assert tape_log.append(_doc(3), "2026-09-19", "NIFTY") == {"bars": 0, "marks": 0}
    assert len(_lines(tape_log.day_path("2026-09-19", "NIFTY"))) == 3


def test_forming_is_never_written(tdir):
    tape_log.append(_doc(2, forming=True), "2026-09-19", "NIFTY")
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert all(r["t"] != 1789726200000 + 2 * 300000 for r in rows)


def test_a_bar_without_a_ladder_is_written_with_null(tdir):
    tape_log.append(_doc(1, ladder=False), "2026-09-19", "NIFTY")
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert rows[0]["ladder"] is None


def test_marks_are_written_once_by_t_kind_p_side(tdir):
    ev = [{"t": 1789726200000, "kind": "absorption", "side": 1, "p": 23380.0, "size": 120},
          {"t": 1789726200000, "kind": "absorption", "side": 1, "p": 23380.0, "size": 999},   # same identity
          {"t": 1789726200000, "kind": "absorption", "side": -1, "p": 23380.0, "size": 5}]    # other side: new
    n = tape_log.append(_doc(1, events=ev), "2026-09-19", "NIFTY")
    assert n["marks"] == 2
    rows = _lines(tape_log.marks_path("2026-09-19", "NIFTY"))
    assert [r["side"] for r in rows] == [1, -1] and rows[0]["src"] == "ofd" and rows[0]["size"] == 120


def test_readers_return_file_order_and_prior_days_newest_first(tdir):
    for day in ("2026-09-15", "2026-09-17", "2026-09-18"):
        tape_log._seen_bars.clear()
        tape_log.append(_doc(2), day, "NIFTY")
    assert [r["t"] for r in tape_log.read_bars("2026-09-17", "NIFTY")] == [1789726200000, 1789726500000]
    assert tape_log.read_bars("2026-09-16", "NIFTY") == []
    assert tape_log.prior_days("2026-09-18", "NIFTY", n=5) == ["2026-09-17", "2026-09-15"]
    assert tape_log.prior_days("2026-09-18", "NIFTY", n=1) == ["2026-09-17"]
    assert tape_log.read_marks("2026-09-18", "NIFTY")[0]["kind"] == "absorption"


def test_a_torn_last_line_is_skipped_never_fatal(tdir):
    tape_log.append(_doc(2), "2026-09-19", "NIFTY")
    with open(tape_log.day_path("2026-09-19", "NIFTY"), "a", encoding="utf-8") as f:
        f.write('{"t": 1789727100000, "o": 1')          # the process died mid-write
    assert len(tape_log.read_bars("2026-09-19", "NIFTY")) == 2
    tape_log._seen_bars.clear()
    assert tape_log.append(_doc(2), "2026-09-19", "NIFTY")["bars"] == 0


def test_a_disk_error_is_counted_and_never_raised(tdir, monkeypatch):
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(tape_log, "_write_lines", boom)
    before = tape_log.failed
    assert tape_log.append(_doc(2), "2026-09-19", "NIFTY") == {"bars": 0, "marks": 0}
    assert tape_log.failed == before + 3      # 2 bars + 1 mark
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_tape_log.py -q`
Expected: `ModuleNotFoundError: No module named 'tape_log'`

- [ ] **Step 3: Write `tape_log.py`**

```python
# tapemap/tape_log.py
"""tape_log.py -- THE LADDER RECORD. data/tape/tape_<idx>_<day>.jsonl and
data/tape/ofd_marks_<idx>_<day>.jsonl.

WHAT IT IS. The extension posts the whole day's closed bars once a second,
each now carrying GoCharting's per-price ladder (orderflow-desk main.js:234),
and the whole day's marks. This writes each bar ONCE, by `t`, and each mark
ONCE, by (t, kind, p, side), so the every-second re-post costs nothing after
the first time and a restart never re-appends the day.

TWO FILES, TWO POPULATIONS. Bars are measurements; the extension's marks are
its detections. A reader of either must never have to filter the other out
(senses.py:13-22 states the rule for trigger_log.jsonl; it applies here).
The `tm` marks (prints.py) are NOT recorded: they recompute byte-identically
from the bar file, and a derivation written beside a measurement is how
vpin_backfill had to be split from vpin_log.

THE FORMING BAR IS NEVER WRITTEN. Its ladder changes every tick; a record of
it would be a record of nothing. It is served from memory (server.py
/api/tape) and discarded.

FAIL-SOFT, OPENED PER CALL, "a" MODE -- senses.py:_append verbatim. A write
failure is counted on `failed` and never reaches the POST reply's `ok`.

ANYTIME-START IS FREE: the extension replays GoCharting's loaded history on
tab open (record_read.py:9-12), so a server started at 11:00 receives 09:15
onward on the next post. Those bars carry fromTicks:false -- the backfill
tag, and it was there before this file.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Set, Tuple

DIR = os.path.join("data", "tape")
failed = 0

_seen_bars: Dict[Tuple[str, str], Set[int]] = {}
_seen_marks: Dict[Tuple[str, str], Set[tuple]] = {}

_BAR_KEYS = ("t", "o", "h", "l", "c", "vol", "buy", "sell", "delta", "oi", "fromTicks")


def day_path(day: str, idx: str) -> str:
    return os.path.join(DIR, f"tape_{idx}_{day}.jsonl")


def marks_path(day: str, idx: str) -> str:
    return os.path.join(DIR, f"ofd_marks_{idx}_{day}.jsonl")


def _read(path: str) -> List[dict]:
    """Streamed, never json.load of the whole file (record_read.py:54-62).
    A torn last line is skipped, never fatal."""
    out: List[dict] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    out.append(row)
    except OSError:
        return []
    return out


def read_bars(day: str, idx: str) -> List[dict]:
    return _read(day_path(day, idx))


def read_marks(day: str, idx: str) -> List[dict]:
    return _read(marks_path(day, idx))


def prior_days(day: str, idx: str, n: int = 5) -> List[str]:
    """Days with a bar file before `day`, newest first, at most n."""
    pre, suf = f"tape_{idx}_", ".jsonl"
    try:
        names = os.listdir(DIR)
    except OSError:
        return []
    days = [nm[len(pre):-len(suf)] for nm in names if nm.startswith(pre) and nm.endswith(suf)]
    return sorted((d for d in days if d < day), reverse=True)[:n]


def _mark_key(m: dict) -> tuple:
    return (m.get("t"), m.get("kind"), m.get("p"), m.get("side"))


def _seed(day: str, idx: str) -> None:
    key = (day, idx)
    if key not in _seen_bars:
        _seen_bars[key] = {int(r["t"]) for r in read_bars(day, idx) if r.get("t") is not None}
    if key not in _seen_marks:
        _seen_marks[key] = {_mark_key(r) for r in read_marks(day, idx)}


def _write_lines(path: str, rows: List[dict]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("".join(json.dumps(r, default=str) + "\n" for r in rows))


def append(doc: dict, day: str, idx: str) -> dict:
    """Write the doc's new closed bars and new marks. Returns how many landed."""
    global failed
    _seed(day, idx)
    seen_b, seen_m = _seen_bars[(day, idx)], _seen_marks[(day, idx)]
    meta = {"rowSize": doc.get("rowSize"), "rowAnchor": doc.get("rowAnchor", 0), "lot": doc.get("lot"),
            "session": doc.get("session"), "idx": idx, "day": day}
    bars = []
    for b in doc.get("closed") or []:
        t = b.get("t")
        if t is None or int(t) in seen_b:
            continue
        row = {k: b.get(k) for k in _BAR_KEYS}
        row["ladder"] = b.get("ladder") if isinstance(b.get("ladder"), list) else None
        row.update(meta)
        bars.append(row)
    marks = []
    for m in doc.get("events") or []:
        if not isinstance(m, dict) or m.get("t") is None or m.get("kind") is None:
            continue
        k = _mark_key(m)
        if k in seen_m:
            continue
        seen_m.add(k)
        marks.append({"t": m["t"], "kind": m["kind"], "side": m.get("side"), "p": m.get("p"),
                      "size": m.get("size"), "src": "ofd", "idx": idx, "day": day})
    out = {"bars": 0, "marks": 0}
    for rows, path, key in ((bars, day_path(day, idx), "bars"), (marks, marks_path(day, idx), "marks")):
        if not rows:
            continue
        try:
            _write_lines(path, rows)
        except Exception:                      # never take the tape down
            failed += len(rows)
            if key == "marks":
                for m in rows:
                    seen_m.discard(_mark_key(m))
            continue
        if key == "bars":
            seen_b.update(int(r["t"]) for r in rows)
        out[key] = len(rows)
    return out
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_tape_log.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add tape_log.py test_tape_log.py
git commit -m "tape_log: the ladder record -- each bar and each extension mark written once, seeded from the file on restart" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Registration and the POST hook

**Files:**
- Modify: `tapemap/server.py` (imports near line 41; `do_POST` at line 1191; `_isolate_mock_writers` at ~2177–2198)
- Modify: `tapemap/test_day_state.py:97–98`
- Modify: `tapemap/.gitignore` (after the `data/senses/` block, line 11)
- Test: `tapemap/test_frame_api.py`, `tapemap/test_day_state.py`

**Interfaces:**
- Consumes: `tape_log.append(doc, day, idx)`, `tape_log.DIR`.
- Produces: every `POST /api/frame` lands its new bars and marks in `data/tape/`; a `--mock-chain` run writes under `data/mock/tape/`.

- [ ] **Step 1: Write the failing tests**

Append to `test_frame_api.py`:

```python
def test_frame_post_records_the_ladder_bars_and_marks(tmp_path, monkeypatch):
    import tape_log
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
    doc = _tape(n=2)
    for b in doc["closed"]:
        b["ladder"] = [{"p": 1.0, "b": 3, "s": 1, "bt": 2, "st": 1}]
    doc["events"] = [{"t": doc["closed"][0]["t"], "kind": "absorption", "side": 1, "p": 1.0, "size": 3}]
    doc["rowAnchor"] = 0
    req = _Req("/api/frame", doc)
    server.Handler.do_POST(req)
    assert req.out[-1][1]["ok"] is True
    bars = tape_log.read_bars("2026-09-11", "NIFTY")
    assert len(bars) == 2 and bars[0]["ladder"] == [{"p": 1.0, "b": 3, "s": 1, "bt": 2, "st": 1}]
    assert len(tape_log.read_marks("2026-09-11", "NIFTY")) == 1
    server.Handler.do_POST(_Req("/api/frame", doc))     # the every-second re-post
    assert len(tape_log.read_bars("2026-09-11", "NIFTY")) == 2
```

In `test_day_state.py`, the pin list at lines 97–98 — add the name:

```python
    for name in ("day_state.DIR", "VPIN_BACKFILL_LOG", "VPIN_LOG",
                 "desk_log.SURF_DIR", "trader_mod.STATE", "sequence_mod.DIR",
                 "tape_log.DIR"):
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_frame_api.py::test_frame_post_records_the_ladder_bars_and_marks test_day_state.py::test_every_new_writer_is_named_in_the_isolation_function -q`
Expected: 2 failed — the first because no bars were recorded, the second because `tape_log.DIR` is not in the function's source.

- [ ] **Step 3: Import, hook, register**

`server.py`, beside `import frame_log` (line 41):

```python
import frame_log
import tape_log
```

`server.py` `do_POST`, after line 1191 (`fr["record"] = {"written": frame_log.append_if_changed(fr, day, idx)}`), before `with _SENSES_LOCK:`:

```python
                # THE LADDER RECORD (tape_log.py): each new closed bar and each
                # new extension mark, once. Fail-soft inside; nothing here can
                # change `ok`. Before the lock, like the frame write above.
                tape_log.append(doc, day, idx)
```

`server.py` `_isolate_mock_writers`, after the line `VPIN_BACKFILL_LOG = os.path.join(mock, "vpin_backfill.jsonl")`:

```python
    tape_log.DIR = os.path.join(mock, "tape")
```

`.gitignore`, after the `data/senses/` line (line 11):

```gitignore
# the ladder record (tape_log.py): GoCharting's per-price prints as posted by
# orderflow-desk, ~0.3MB/day, not refetchable from any broker. Two forward
# populations in their own files (bars; the extension's marks), never pooled.
data/tape/
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_frame_api.py test_day_state.py -q`
Expected: all pass (the two new ones included).

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -q`
Expected: green, count = previous + 11 (10 in `test_tape_log.py`, 1 in `test_frame_api.py`). `test_docs_claims.py` will FAIL on the stated counts — that is expected until Task 13; note the new total.

- [ ] **Step 6: Commit**

```bash
git add server.py test_frame_api.py test_day_state.py .gitignore
git commit -m "server: every /api/frame post lands its new bars and marks in data/tape/; writer registered and pinned" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `prints.py` — rebin, imbalances, per-bar flags

**Files:**
- Create: `tapemap/prints.py`
- Test: `tapemap/test_prints.py`

**Interfaces:**
- Produces:
  - `prints.IMB_RATIO = 3`, `prints.IMB_MIN_LOTS = 5`, `prints.STACK_RUN = 3`, `prints.MIN_N = 6`
  - `prints.rebin(ladder: list[dict], row_size: float, anchor: float = 0.0) -> list[dict]` rows `{p, b, s, bt, st}` sorted by `p`
  - `prints.imbalances(rows) -> tuple[list[int], list[dict]]` — flags `+1/-1/0` per row; stacks `{side: "buy"|"sell", low, high, run}`
  - `prints.bar_flags(bar: dict, row_size: float, anchor: float = 0.0) -> dict | None` → `{stacks, unfinished_high, unfinished_low, poc}`; `None` when `bar["ladder"]` is not a non-empty list

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_prints.py
"""prints.py: the extension's arithmetic, ported (spec §E). Hand cases here;
the parity pin against the extension's own code is test_parity_* (Task 6)."""
import prints


def _row(p, b=0, s=0, bt=0, st=0):
    return {"p": p, "b": b, "s": s, "bt": bt, "st": st}


def test_rebin_sums_into_row_buckets_and_sorts():
    # 23352.1/5 = 4670.42 -> 23350; 23350.8/5 = 4670.16 -> 23350; 23347.4/5 = 4669.48 -> 23345
    lad = [_row(23352.1, 1, 0, 1, 0), _row(23350.8, 0, 2, 0, 2), _row(23347.4, 3, 0, 2, 0)]
    rows = prints.rebin(lad, 5)
    assert [r["p"] for r in rows] == [23345.0, 23350.0]
    assert rows[1] == {"p": 23350.0, "b": 1, "s": 2, "bt": 1, "st": 2}
    assert rows[0] == {"p": 23345.0, "b": 3, "s": 0, "bt": 2, "st": 0}


def test_rebin_rounds_half_up_like_javascript():
    # 23352.5 / 5 = 4670.5 -> JS Math.round gives 4671 -> 23355; Python round() would give 23350
    assert prints.rebin([_row(23352.5, 1)], 5)[0]["p"] == 23355.0


def test_rebin_anchor_shifts_the_grid():
    assert prints.rebin([_row(23352.0, 1)], 5, anchor=2)[0]["p"] == 23352.0


def test_rebin_empty_or_missing_ladder_is_empty():
    assert prints.rebin([], 5) == [] and prints.rebin(None, 5) == []


def test_buy_imbalance_is_diagonal_ask_at_p_vs_bid_one_row_below():
    rows = [_row(100, b=1, s=1), _row(101, b=15, s=0)]      # ask 15 at 101 vs bid(=s) 1 at 100
    flags, stacks = prints.imbalances(rows)
    assert flags == [0, 1] and stacks == []


def test_sell_imbalance_is_bid_at_p_vs_ask_one_row_above():
    rows = [_row(100, b=0, s=15), _row(101, b=1, s=0)]      # bid 15 at 100 vs ask(=b) 1 at 101
    flags, _ = prints.imbalances(rows)
    assert flags == [-1, 0]


def test_min_lots_boundary_four_is_silent_five_fires():
    assert prints.imbalances([_row(100, s=1), _row(101, b=4)])[0] == [0, 0]
    assert prints.imbalances([_row(100, s=1), _row(101, b=5)])[0] == [0, 1]


def test_zero_side_floors_at_one_lot_the_extensions_rule():
    assert prints.imbalances([_row(100, s=0), _row(101, b=15)])[0] == [0, 1]   # 15 >= 3 * max(0, 1)
    assert prints.imbalances([_row(100, s=0), _row(101, b=2)])[0] == [0, 0]    # 2 < 5 lots


def test_a_sell_flag_never_overwrites_a_buy_flag_on_the_same_row():
    # row 101: buy imbalance vs row 100; row 101 also sell-dominant vs row 102 -> stays +1
    rows = [_row(100, s=1), _row(101, b=15, s=15), _row(102, b=1)]
    flags, _ = prints.imbalances(rows)
    assert flags == [0, 1, 0]


def test_stack_of_exactly_three_fires_and_two_does_not():
    three = [_row(100, s=1), _row(101, b=9), _row(102, b=9), _row(103, b=9)]
    flags, stacks = prints.imbalances(three)
    assert flags == [0, 1, 1, 1]
    assert stacks == [{"side": "buy", "low": 101, "high": 103, "run": 3}]
    two = [_row(100, s=1), _row(101, b=9), _row(102, b=9)]
    assert prints.imbalances(two)[1] == []


def test_bar_flags_poc_is_the_first_largest_row_and_unfinished_reads_the_raw_extremes():
    bar = {"vol": 100, "ladder": [_row(23350.0, 3, 3), _row(23355.0, 10, 2), _row(23360.0, 6, 6)]}
    f = prints.bar_flags(bar, 5)
    assert f["poc"] == 23355.0
    # unfinished: top row 23360 has b=6,s=6 >= max(3, 2) -> unfinished high; bottom 23350 b=3,s=3 -> unfinished low
    assert f["unfinished_high"] is True and f["unfinished_low"] is True
    bar2 = {"vol": 1000, "ladder": [_row(23350.0, 3, 3), _row(23360.0, 30, 0)]}   # floor is max(3, 20) = 20
    f2 = prints.bar_flags(bar2, 5)
    assert f2["unfinished_high"] is False and f2["unfinished_low"] is False


def test_bar_flags_none_without_a_ladder():
    assert prints.bar_flags({"vol": 5, "ladder": None}, 5) is None
    assert prints.bar_flags({"vol": 5, "ladder": []}, 5) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_prints.py -q`
Expected: `ModuleNotFoundError: No module named 'prints'`

- [ ] **Step 3: Write `prints.py` (this task's part)**

```python
# tapemap/prints.py
"""prints.py -- the extension's own arithmetic over a bar's ladder, ported
function for function so the two tools cannot disagree about a cell. Pure,
stdlib, no I/O, no clock. Every number here is a COUNT of prints, [M].

SOURCE OF EACH RULE (orderflow-desk/src/engine/):
  rebin, imbalances, stacks      decode.js:12-43
  poc, unfinished auction        decode.js:50-58
  profile (paired 70% expansion) market.js:47-63
  nodes (HVN / LVN)              board.js:192-200
  naked POC                      market.js:75
The parity test (test_prints.py::test_parity_*) pins this file against a
fixture GENERATED BY THAT CODE over a recorded day. If they ever diverge,
the failure names the bar and the field.

JS `Math.round` rounds half UP; Python `round` rounds half to even. Every
port of a Math.round below goes through _jsround. Load-bearing for parity.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

IMB_RATIO = 3          # decode.js DEFAULTS.imbRatio
IMB_MIN_LOTS = 5       # decode.js DEFAULTS.imbMinLots
STACK_RUN = 3          # decode.js DEFAULTS.stackRun
MIN_N = 6              # board.js MIN_N: six samples before a rank means anything


def _jsround(x: float) -> int:
    return int(math.floor(x + 0.5))


def rebin(ladder, row_size: float, anchor: float = 0.0) -> List[dict]:
    """Re-bin the tick ladder to the chart's row size; sums stay exact."""
    if not ladder or not row_size:
        return []
    m: Dict[float, dict] = {}
    for r in ladder:
        p = round(_jsround((float(r["p"]) - anchor) / row_size) * row_size + anchor, 4)
        q = m.get(p)
        if q is None:
            q = {"p": p, "b": 0, "s": 0, "bt": 0, "st": 0}
            m[p] = q
        q["b"] += r.get("b") or 0
        q["s"] += r.get("s") or 0
        q["bt"] += r.get("bt") or 0
        q["st"] += r.get("st") or 0
    return sorted(m.values(), key=lambda q: q["p"])


def imbalances(rows: List[dict]) -> Tuple[List[int], List[dict]]:
    """Diagonal: buy at row i vs sell one row below; sell at row i-1 vs buy at i.
    The max(., 1) floor is the extension's zero-side rule (spec §J.1)."""
    flags = [0] * len(rows)
    for i in range(1, len(rows)):
        up, dn = rows[i], rows[i - 1]
        if up["b"] >= IMB_MIN_LOTS and up["b"] >= IMB_RATIO * max(dn["s"], 1):
            flags[i] = 1
        if dn["s"] >= IMB_MIN_LOTS and dn["s"] >= IMB_RATIO * max(up["b"], 1):
            flags[i - 1] = flags[i - 1] or -1
    stacks = []
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(flags) and flags[j + 1] == flags[i]:
            j += 1
        run = j - i + 1
        if run >= STACK_RUN:
            stacks.append({"side": "buy" if flags[i] > 0 else "sell",
                           "low": rows[i]["p"], "high": rows[j]["p"], "run": run})
        i = j + 1
    return flags, stacks


def bar_flags(bar: dict, row_size: float, anchor: float = 0.0) -> Optional[dict]:
    """{stacks, unfinished_high, unfinished_low, poc} for one bar, or None
    without a ladder. poc on the REBINNED rows (first largest, strict >);
    unfinished on the RAW extreme rows (decode.js:54-58)."""
    lad = bar.get("ladder")
    if not isinstance(lad, list) or not lad:
        return None
    rows = rebin(lad, row_size, anchor)
    _, stacks = imbalances(rows)
    poc, best = None, -1
    for r in rows:
        v = r["b"] + r["s"]
        if v > best:
            best, poc = v, r["p"]
    raw = sorted(lad, key=lambda r: float(r["p"]))
    top, bot = raw[-1], raw[0]
    vol = float(bar.get("vol") or 0)
    unf_min = max(3, vol * 0.02)
    return {"stacks": stacks,
            "unfinished_high": bool((top.get("b") or 0) >= unf_min and (top.get("s") or 0) >= unf_min),
            "unfinished_low": bool((bot.get("b") or 0) >= unf_min and (bot.get("s") or 0) >= unf_min),
            "poc": poc}
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_prints.py -q`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add prints.py test_prints.py
git commit -m "prints: rebin, diagonal imbalance, stacks, per-bar poc and unfinished auction -- decode.js ported" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `prints.py` — profile, nodes, delta/CVD, prior-day levels, naked POC

**Files:**
- Modify: `tapemap/prints.py` (append)
- Test: `tapemap/test_prints.py` (append)

**Interfaces:**
- Produces:
  - `prints.profile(bars: list[dict]) -> dict | None` → `{poc, vah, val, total, rows: [{p, v}]}` over **raw** ladder prices (market.js)
  - `prints.nodes(prof: dict | None) -> list[dict]` → `[{p, vol, kind: "HVN"|"LVN"}]` sorted by `p`
  - `prints.with_cvd(bars: list[dict]) -> list[dict]` → copies sorted by `t`, each with `delta` (as posted, `buy - sell` if absent) and `cvd`
  - `prints.prior_levels(days: list[tuple[str, list[dict]]]) -> list[dict]` → `[{day, poc, vah, val}]`, input newest first
  - `prints.naked(days: list[tuple[str, list[dict]]], today_bars: list[dict]) -> list[dict]` → `[{day, poc, touched_t}]`

- [ ] **Step 1: Write the failing tests** (append to `test_prints.py`)

```python
def _bar(t, ladder, o=None, h=None, l=None, c=None, buy=None, sell=None, delta=None, vol=None):
    b = {"t": t, "ladder": ladder, "o": o, "h": h, "l": l, "c": c}
    if buy is not None: b["buy"] = buy
    if sell is not None: b["sell"] = sell
    if delta is not None: b["delta"] = delta
    if vol is not None: b["vol"] = vol
    return b


def test_profile_sums_raw_ladder_prices_and_expands_two_rows_a_side():
    # rows: 100:1 101:2 102:10 103:2 104:1 105:1  total 17, 70% = 11.9
    # poc=102 (acc 10); up pair 103+104=3 vs down pair 101+100=3 -> tie goes up -> acc 13 >= 11.9 -> vah 104, val 102
    lad = [_row(100, 1), _row(101, 2), _row(102, 10), _row(103, 2), _row(104, 1), _row(105, 1)]
    pr = prints.profile([_bar(1, lad)])
    assert (pr["poc"], pr["vah"], pr["val"], pr["total"]) == (102, 104, 102, 17)
    assert [r["p"] for r in pr["rows"]] == [100, 101, 102, 103, 104, 105]


def test_profile_takes_the_larger_pair_whole():
    # poc=102(10); down pair 101+100 = 8 > up pair 103+104 = 2 -> take both down rows
    lad = [_row(100, 4), _row(101, 4), _row(102, 10), _row(103, 1), _row(104, 1)]
    pr = prints.profile([_bar(1, lad)])
    assert (pr["val"], pr["vah"]) == (100, 102)


def test_profile_ignores_bars_without_a_ladder_and_is_none_when_nothing_has_one():
    assert prints.profile([_bar(1, None), _bar(2, [])]) is None
    pr = prints.profile([_bar(1, None), _bar(2, [_row(100, 1)])])
    assert pr["poc"] == 100


def test_nodes_top_three_are_hvn_and_at_most_a_third_of_median_is_lvn():
    # 5-point bins: 100:50 105:40 110:30 115:10 120:2 125:9   median of [2,9,10,30,40,50] -> vals[3]=30 -> LVN <= 10.5
    lad = [_row(100, 50), _row(105, 40), _row(110, 30), _row(115, 10), _row(120, 2), _row(125, 9)]
    nd = prints.nodes(prints.profile([_bar(1, lad)]))
    assert [(n["p"], n["kind"]) for n in nd] == [(100, "HVN"), (105, "HVN"), (110, "HVN"), (115, "LVN"), (120, "LVN"), (125, "LVN")]
    assert prints.nodes(None) == []


def test_nodes_bin_rounds_half_up():
    # 23352.5 / 5 = 4670.5 -> bin 23355 (JS), not 23350
    nd = prints.nodes(prints.profile([_bar(1, [_row(23352.5, 5)])]))
    assert nd[0]["p"] == 23355


def test_with_cvd_is_a_prefix_sum_in_time_order():
    bars = [_bar(3, [], buy=1, sell=4), _bar(1, [], delta=5), _bar(2, [], buy=2, sell=1)]
    out = prints.with_cvd(bars)
    assert [(b["t"], b["delta"], b["cvd"]) for b in out] == [(1, 5, 5), (2, 1, 6), (3, -3, 3)]
    assert bars[0].get("cvd") is None          # inputs untouched


def test_prior_levels_one_per_day_newest_first():
    d1 = ("2026-09-18", [_bar(1, [_row(100, 1), _row(101, 5), _row(102, 1)])])
    d2 = ("2026-09-17", [_bar(1, [_row(200, 5)])])
    out = prints.prior_levels([d1, d2])
    assert [(o["day"], o["poc"]) for o in out] == [("2026-09-18", 101), ("2026-09-17", 200)]


def test_naked_poc_survives_until_a_later_bar_straddles_it_wick_counts():
    older = ("2026-09-17", [_bar(1, [_row(200, 5)])])                 # poc 200
    newer = ("2026-09-18", [_bar(1, [_row(300, 5)], h=310, l=295)])   # never touched 200
    today = [_bar(10, [], h=250, l=240), _bar(11, [], h=205, l=199), _bar(12, [], h=201, l=200)]
    out = prints.naked([newer, older], today)
    assert {o["day"]: o for o in out}["2026-09-17"] == {"day": "2026-09-17", "poc": 200, "touched_t": 11}
    assert {o["day"]: o for o in out}["2026-09-18"] == {"day": "2026-09-18", "poc": 300, "touched_t": None}


def test_naked_poc_touched_on_a_prior_newer_day_is_not_listed():
    older = ("2026-09-17", [_bar(1, [_row(200, 5)])])
    newer = ("2026-09-18", [_bar(1, [_row(300, 5)], h=210, l=190)])   # traded through 200
    out = prints.naked([newer, older], [])
    assert [o["day"] for o in out] == ["2026-09-18"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_prints.py -q`
Expected: 9 failed with `AttributeError: module 'prints' has no attribute 'profile'` (and siblings).

- [ ] **Step 3: Append to `prints.py`**

```python


def profile(bars: List[dict]) -> Optional[dict]:
    """Volume-at-price over the RAW ladder prices (market.js:47-63): POC and
    the 70% value area by the PAIRED expansion -- compare the next two rows up
    against the next two rows down, take the larger pair whole, ties go up."""
    m: Dict[float, float] = {}
    for b in bars:
        for r in (b.get("ladder") or []) if isinstance(b.get("ladder"), list) else []:
            p = float(r["p"])
            m[p] = m.get(p, 0) + (r.get("b") or 0) + (r.get("s") or 0)
    rows = [{"p": p, "v": v} for p, v in sorted(m.items())]
    if not rows:
        return None
    total = sum(r["v"] for r in rows)
    poc = 0
    for i in range(1, len(rows)):
        if rows[i]["v"] > rows[poc]["v"]:
            poc = i
    lo = hi = poc
    acc = rows[poc]["v"]
    n = len(rows)
    while acc < total * 0.7 and (lo > 0 or hi < n - 1):
        dn = (rows[lo - 1]["v"] + (rows[lo - 2]["v"] if lo > 1 else 0)) if lo > 0 else -1
        up = (rows[hi + 1]["v"] + (rows[hi + 2]["v"] if hi < n - 2 else 0)) if hi < n - 1 else -1
        if up >= dn:
            for _ in range(2):
                if hi < n - 1:
                    hi += 1
                    acc += rows[hi]["v"]
        else:
            for _ in range(2):
                if lo > 0:
                    lo -= 1
                    acc += rows[lo]["v"]
    return {"poc": rows[poc]["p"], "vah": rows[hi]["p"], "val": rows[lo]["p"], "total": total, "rows": rows}


def nodes(prof: Optional[dict]) -> List[dict]:
    """board.js:192-200: 5-point bins; the top three by volume are HVN; a bin
    at or under 0.35 x the median bin is LVN; the rest are dropped."""
    if not prof:
        return []
    bins: Dict[int, float] = {}
    for r in prof["rows"]:
        k = _jsround(r["p"] / 5) * 5
        bins[k] = bins.get(k, 0) + r["v"]
    vals = sorted(bins.values())
    med = vals[len(vals) >> 1] if vals else 1
    med = med or 1
    all_ = [{"p": p, "vol": _jsround(v)} for p, v in bins.items()]        # insertion order = ascending p
    top = {n["p"] for n in sorted(all_, key=lambda n: -n["vol"])[:3]}
    out = []
    for n in all_:
        kind = "HVN" if n["p"] in top else ("LVN" if n["vol"] <= med * 0.35 else "")
        if kind:
            out.append({"p": n["p"], "vol": n["vol"], "kind": kind})
    return sorted(out, key=lambda n: n["p"])


def with_cvd(bars: List[dict]) -> List[dict]:
    """Copies, sorted by t, each with delta and the running cvd -- anchored at
    the session open, reset daily (spec §J.1)."""
    out = []
    run = 0
    for b in sorted(bars, key=lambda b: b["t"]):
        d = b.get("delta")
        if d is None:
            d = (b.get("buy") or 0) - (b.get("sell") or 0)
        run += d
        out.append({**b, "delta": d, "cvd": run})
    return out


def prior_levels(days: List[Tuple[str, List[dict]]]) -> List[dict]:
    out = []
    for day, bars in days:
        pr = profile(bars)
        if pr:
            out.append({"day": day, "poc": pr["poc"], "vah": pr["vah"], "val": pr["val"]})
    return out


def _straddles(b: dict, p: float) -> bool:
    lo = b.get("l") if b.get("l") is not None else b.get("c")
    hi = b.get("h") if b.get("h") is not None else b.get("c")
    return lo is not None and hi is not None and lo <= p <= hi


def naked(days: List[Tuple[str, List[dict]]], today_bars: List[dict]) -> List[dict]:
    """A prior day's POC is naked until a LATER bar's range straddles it, a
    wick counts (market.js:75). `days` newest first. Touched on a newer prior
    day: not listed. Touched today: touched_t is that bar's t. Else None."""
    out = []
    for i, (day, bars) in enumerate(days):
        pr = profile(bars)
        if not pr:
            continue
        p = pr["poc"]
        if any(_straddles(b, p) for _, newer in days[:i] for b in newer):
            continue
        touched = None
        for b in sorted(today_bars, key=lambda b: b["t"]):
            if _straddles(b, p):
                touched = b["t"]
                break
        out.append({"day": day, "poc": p, "touched_t": touched})
    return out
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_prints.py -q`
Expected: `21 passed`

- [ ] **Step 5: Commit**

```bash
git add prints.py test_prints.py
git commit -m "prints: session profile with the paired value area, HVN/LVN nodes, cvd, prior-day levels and naked POC" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: The parity pin — generated once from the extension's own code

**Files:**
- Create: `tapemap/tools/gen_prints_expected.mjs`
- Create: `tapemap/test/fixtures/prints_expected_2026-09-11.json` (generated, committed)
- Test: `tapemap/test_prints.py` (append)

**Interfaces:**
- Consumes: `prints.rebin`, `prints.bar_flags`, `prints.profile`, `prints.nodes`.
- Produces: the fixture `{source, rowSize, rowAnchor, bars: [{t, rows, stacks, poc, unfinished_high, unfinished_low}], profile: {poc, vah, val, total}, nodes}`.

- [ ] **Step 1: Write the generator**

```js
// tapemap/tools/gen_prints_expected.mjs
// Runs the EXTENSION'S OWN decode.js / market.js / board.js over a recorded day
// and writes what they say, so test_prints.py can pin prints.py against it.
// Generated ONCE and committed; re-run only if the extension's engine changes
// (then the commit that re-runs it says why).
//   node tools/gen_prints_expected.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const ENG = 'C:/Users/kaam/Desktop/Go charting/orderflow-desk/src/engine/';
const FIX = 'C:/Users/kaam/Desktop/Go charting/orderflow-desk/test/session-2026-09-11.ofd.json';
const OUT = 'test/fixtures/prints_expected_2026-09-11.json';
const ROW = 5, ANCHOR = 0;

const { rebin, readBar, DEFAULTS } = await import(pathToFileURL(ENG + 'decode.js').href);
const { profile } = await import(pathToFileURL(ENG + 'market.js').href);
const { board } = await import(pathToFileURL(ENG + 'board.js').href);

const j = JSON.parse(readFileSync(FIX, 'utf8'));
const bars = j.bars.filter((b) => Array.isArray(b.ladder) && b.ladder.length).sort((a, b) => a.t - b.t);
const cfg = { ...DEFAULTS, rowSize: ROW, rowAnchor: ANCHOR };
// readBar's `base` only shapes sizeClass/lopsided, which are not pinned; poc, stacks and the
// unfinished flags do not read it.
const perBar = bars.map((b) => {
  const r = readBar(b, null, { medVol: b.vol || 1, medRange: 0, p75Lop: 0 }, cfg);
  return { t: b.t, rows: rebin(b.ladder, ROW, ANCHOR), stacks: r.stacks, poc: r.poc,
           unfinished_high: r.unfinishedHigh, unfinished_low: r.unfinishedLow };
});
const pr = profile(bars);
const B = board(bars, { rowSize: ROW });
mkdirSync('test/fixtures', { recursive: true });
writeFileSync(OUT, JSON.stringify({
  source: 'orderflow-desk/test/session-2026-09-11.ofd.json', rowSize: ROW, rowAnchor: ANCHOR,
  bars: perBar, profile: { poc: pr.poc, vah: pr.vah, val: pr.val, total: pr.total }, nodes: B.nodes,
}));
console.log(`wrote ${OUT}: ${perBar.length} bars, profile poc ${pr.poc} vah ${pr.vah} val ${pr.val}, ${B.nodes.length} nodes`);
```

- [ ] **Step 2: Generate the fixture**

Run (from `tapemap`): `node tools/gen_prints_expected.mjs`
Expected: `wrote test/fixtures/prints_expected_2026-09-11.json: 77 bars, profile poc <n> vah <n> val <n>, <k> nodes`. If node complains about `import` inside `board.js` (e.g. `hhmm` from `market.js`), the engine files are ESM and import each other by relative path — the `pathToFileURL` import resolves them; do not copy the engine files into `tapemap`.

- [ ] **Step 3: Write the parity test** (append to `test_prints.py`)

```python
import json
import os

FIXTURE = os.path.join("test", "fixtures", "prints_expected_2026-09-11.json")
OFD = r"C:\Users\kaam\Desktop\Go charting\orderflow-desk\test\session-2026-09-11.ofd.json"


def _parity():
    exp = json.load(open(FIXTURE, encoding="utf-8"))
    bars = [b for b in json.load(open(OFD, encoding="utf-8"))["bars"] if isinstance(b.get("ladder"), list) and b["ladder"]]
    bars.sort(key=lambda b: b["t"])
    assert len(bars) == len(exp["bars"]) == 77
    return exp, bars


def test_parity_per_bar_rows_flags_poc_and_unfinished_match_the_extension():
    exp, bars = _parity()
    for e, b in zip(exp["bars"], bars):
        assert e["t"] == b["t"]
        rows = prints.rebin(b["ladder"], exp["rowSize"], exp["rowAnchor"])
        assert rows == e["rows"], f"rows differ at t={b['t']}"
        f = prints.bar_flags(b, exp["rowSize"], exp["rowAnchor"])
        assert f["stacks"] == e["stacks"], f"stacks differ at t={b['t']}"
        assert f["poc"] == e["poc"], f"poc differs at t={b['t']}"
        assert f["unfinished_high"] == e["unfinished_high"] and f["unfinished_low"] == e["unfinished_low"], f"unfinished differs at t={b['t']}"


def test_parity_session_profile_and_nodes_match_the_extension():
    exp, bars = _parity()
    pr = prints.profile(bars)
    assert (pr["poc"], pr["vah"], pr["val"], pr["total"]) == (exp["profile"]["poc"], exp["profile"]["vah"], exp["profile"]["val"], exp["profile"]["total"])
    assert prints.nodes(pr) == exp["nodes"]
```

- [ ] **Step 4: Run the parity tests**

Run: `python -m pytest test_prints.py -k parity -q`
Expected: `2 passed`. If `rows differ` on a bar, the first suspect is `_jsround` vs a `.toFixed(4)` float edge; print both sides for that bar and compare the offending row — fix `prints.py`, never the fixture.

- [ ] **Step 5: Commit**

```bash
git add tools/gen_prints_expected.mjs test/fixtures/prints_expected_2026-09-11.json test_prints.py
git commit -m "prints: parity pinned bar by bar against decode.js/market.js/board.js over the recorded 2026-09-11 session" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: `prints.py` — the `tm` family

**Files:**
- Modify: `tapemap/prints.py` (append)
- Test: `tapemap/test_prints.py` (append)

**Interfaces:**
- Produces:
  - `prints.TM_ABS_DELTA_PCT = 0.75`, `prints.TM_ABS_RANGE_PCT = 0.50`, `prints.TM_CLIMAX_VOL_PCT = 0.90`, `prints.TM_CLIMAX_LOP = 0.15`, `prints.TM_EXH_LOOKBACK = 6`
  - `prints.pct_rank(prior: list[float], x: float) -> float | None` — fraction of `prior` `<= x`; `None` when `len(prior) < MIN_N`
  - `prints.tm_marks(bars: list[dict]) -> tuple[list[dict], str | None]` → marks `{t, kind, side, p, size, why, src: "tm", tag: "I"}` and `tm_why` (`"first six bars: nothing to rank against"` when nothing could be ranked, else `None`)

- [ ] **Step 1: Write the failing tests** (append to `test_prints.py`)

```python
def _seq(n, delta=1, rng=10, vol=100, base=23000, step=0):
    """n closed bars with a flat profile: delta, range, volume as given."""
    return [_bar(1000 + i, [], o=base + i * step, h=base + i * step + rng, l=base + i * step, c=base + i * step + 1,
                 delta=delta, vol=vol) for i in range(n)]


def test_pct_rank_needs_six_priors_and_is_the_fraction_at_or_below():
    assert prints.pct_rank([1, 2, 3, 4, 5], 3) is None
    assert prints.pct_rank([1, 2, 3, 4, 5, 6], 3) == 0.5
    assert prints.pct_rank([1, 2, 3, 4, 5, 6], 6) == 1.0


def test_tm_absorption_fires_on_big_delta_small_range_close_against_it():
    bars = _seq(6) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23000, delta=50, vol=100)]   # |delta| top, range 4 <= median 10, delta>0 & c<=o
    marks, why = prints.tm_marks(bars)
    assert why is None
    abs_ = [m for m in marks if m["kind"] == "absorption"]
    assert len(abs_) == 1 and abs_[0]["side"] == -1 and abs_[0]["p"] == 23004 and abs_[0]["src"] == "tm" and abs_[0]["tag"] == "I"
    assert "absorbed" in abs_[0]["why"]


def test_tm_absorption_silent_one_step_off_each_rule():
    # range not small enough (11 > median 10)
    assert not [m for m in prints.tm_marks(_seq(6) + [_bar(2000, [], o=23000, h=23011, l=23000, c=23000, delta=50, vol=100)])[0] if m["kind"] == "absorption"]
    # close agrees with delta
    assert not [m for m in prints.tm_marks(_seq(6) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23003, delta=50, vol=100)])[0] if m["kind"] == "absorption"]
    # |delta| not in the top quarter (priors all 50, this bar 10 -> rank 0)
    assert not [m for m in prints.tm_marks(_seq(6, delta=50) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23000, delta=10, vol=100)])[0] if m["kind"] == "absorption"]


def test_tm_exhaustion_new_high_on_non_positive_delta_is_bearish_at_the_high():
    bars = _seq(6, rng=10, step=0) + [_bar(2000, [], o=23005, h=23020, l=23004, c=23010, delta=-5, vol=100)]   # h 23020 > prior max 23010
    ex = [m for m in prints.tm_marks(bars)[0] if m["kind"] == "exhaustion"]
    assert len(ex) == 1 and ex[0]["side"] == -1 and ex[0]["p"] == 23020


def test_tm_exhaustion_new_low_on_non_negative_delta_is_bullish_and_needs_six_priors():
    bars = _seq(6, rng=10) + [_bar(2000, [], o=22999, h=23001, l=22990, c=22995, delta=3, vol=100)]     # l 22990 < prior min 23000
    ex = [m for m in prints.tm_marks(bars)[0] if m["kind"] == "exhaustion"]
    assert len(ex) == 1 and ex[0]["side"] == 1 and ex[0]["p"] == 22990
    assert prints.tm_marks(_seq(5) + bars[-1:])[0] == []


def test_tm_exhaustion_silent_when_delta_agrees_with_the_extreme():
    bars = _seq(6, rng=10) + [_bar(2000, [], o=23005, h=23020, l=23004, c=23010, delta=5, vol=100)]
    assert not [m for m in prints.tm_marks(bars)[0] if m["kind"] == "exhaustion"]


def test_tm_climax_top_decile_volume_with_two_sided_prints():
    bars = _seq(9, vol=100) + [_bar(2000, [], o=23000, h=23010, l=23000, c=23008, delta=10, vol=1000)]   # vol rank 1.0, |d|/vol 0.01
    cl = [m for m in prints.tm_marks(bars)[0] if m["kind"] == "climax"]
    assert len(cl) == 1 and cl[0]["side"] == 0 and cl[0]["p"] == 23010          # closed near the high
    bars[-1]["delta"] = 200                                                       # 0.2 > 0.15 lopsided -> not a climax
    assert not [m for m in prints.tm_marks(bars)[0] if m["kind"] == "climax"]


def test_tm_first_six_bars_fire_nothing_and_say_why():
    marks, why = prints.tm_marks(_seq(4))
    assert marks == [] and why == "first six bars: nothing to rank against"


def test_tm_is_pure():
    bars = _seq(8) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23000, delta=50, vol=100)]
    assert prints.tm_marks(bars) == prints.tm_marks(bars)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_prints.py -k "tm_ or pct_rank" -q`
Expected: 9 failed, `AttributeError`.

- [ ] **Step 3: Append to `prints.py`**

```python


# --- the tm family: vendor-standard definitions, self-calibrated on the
# session so far (README Principles: percentile-so-far, no absolute lot
# counts). Spec §E table and §J.3. These five numbers are stated once,
# pinned by test, and NOT tuned before spec §K.
TM_ABS_DELTA_PCT = 0.75    # absorption: |delta| in the top quarter so far
TM_ABS_RANGE_PCT = 0.50    # absorption: range at or under the median so far
TM_CLIMAX_VOL_PCT = 0.90   # climax: volume in the top decile so far
TM_CLIMAX_LOP = 0.15       # climax: |delta| / vol at or under this
TM_EXH_LOOKBACK = 6        # exhaustion: a new extreme over the previous six bars
TM_WHY_EARLY = "first six bars: nothing to rank against"


def pct_rank(prior: List[float], x: float) -> Optional[float]:
    """Fraction of `prior` at or below x; None under MIN_N (board.js rankIn)."""
    v = [y for y in prior if y is not None]
    if len(v) < MIN_N:
        return None
    return sum(1 for y in v if y <= x) / len(v)


def _sign(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


def _delta_of(b: dict) -> float:
    d = b.get("delta")
    return d if d is not None else (b.get("buy") or 0) - (b.get("sell") or 0)


def tm_marks(bars: List[dict]) -> Tuple[List[dict], Optional[str]]:
    """The second opinion. Each mark: {t, kind, side, p, size, why, src, tag}."""
    bs = sorted(bars, key=lambda b: b["t"])
    out: List[dict] = []
    ranked_any = False
    for i, b in enumerate(bs):
        prior = bs[:i]
        h, l, o, c = b.get("h"), b.get("l"), b.get("o"), b.get("c")
        if None in (h, l, o, c):
            continue
        d = _delta_of(b)
        vol = float(b.get("vol") or 0)
        rng = h - l
        abs_d = abs(d)
        r_d = pct_rank([abs(_delta_of(p)) for p in prior], abs_d)
        r_r = pct_rank([(p["h"] - p["l"]) for p in prior if p.get("h") is not None and p.get("l") is not None], rng)
        r_v = pct_rank([float(p.get("vol") or 0) for p in prior], vol)
        if r_d is not None:
            ranked_any = True
        # absorption -- Sierra effort vs result: big effort, no range, and the close disagrees with the delta
        if (r_d is not None and r_r is not None and r_d >= TM_ABS_DELTA_PCT and r_r <= TM_ABS_RANGE_PCT
                and ((d > 0 and c <= o) or (d < 0 and c >= o))):
            out.append({"t": b["t"], "kind": "absorption", "side": -_sign(d), "p": h if d > 0 else l, "size": int(abs_d),
                        "why": f"{int(abs_d)} lots net {'bought' if d > 0 else 'sold'} for {rng:.1f} points and the bar closed "
                               f"{'at or below' if d > 0 else 'at or above'} its open: absorbed",
                        "src": "tm", "tag": "I"})
        # exhaustion -- ATAS delta divergence at a new extreme, sign only, over the previous six bars
        if len(prior) >= TM_EXH_LOOKBACK:
            win = prior[-TM_EXH_LOOKBACK:]
            if h > max(p["h"] for p in win) and d <= 0:
                out.append({"t": b["t"], "kind": "exhaustion", "side": -1, "p": h, "size": int(abs_d),
                            "why": f"new high {h:.1f} over the last {TM_EXH_LOOKBACK} bars on delta {int(d)}: buyers did not come",
                            "src": "tm", "tag": "I"})
            if l < min(p["l"] for p in win) and d >= 0:
                out.append({"t": b["t"], "kind": "exhaustion", "side": 1, "p": l, "size": int(abs_d),
                            "why": f"new low {l:.1f} over the last {TM_EXH_LOOKBACK} bars on delta {int(d)}: sellers did not come",
                            "src": "tm", "tag": "I"})
        # climax -- volume shape: top-decile volume that resolved nothing
        if r_v is not None and vol > 0 and r_v >= TM_CLIMAX_VOL_PCT and abs_d / vol <= TM_CLIMAX_LOP:
            near_high = c > (h + l) / 2
            out.append({"t": b["t"], "kind": "climax", "side": 0, "p": h if near_high else l, "size": int(vol),
                        "why": f"{int(vol)} lots, |delta| {int(abs_d)} ({abs_d / vol * 100:.0f}%), closed near the "
                               f"{'high' if near_high else 'low'}: unresolved",
                        "src": "tm", "tag": "I"})
    return out, (None if ranked_any else TM_WHY_EARLY)
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_prints.py -q`
Expected: `32 passed`

- [ ] **Step 5: Commit**

```bash
git add prints.py test_prints.py
git commit -m "prints: the tm family -- absorption (effort vs result), exhaustion (delta divergence at a new extreme), climax (volume shape), percentile-so-far" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: `GET /api/tape`

**Files:**
- Modify: `tapemap/server.py` (a module-level `_tape_reply`; a `do_GET` branch before `elif self.path.startswith("/api/frame/bars")` at line 2036; `import prints` beside `import tape_log`)
- Test: `tapemap/test_frame_api.py` (append)

**Interfaces:**
- Consumes: `tape_log.read_bars/read_marks/prior_days`, `prints.*`, `_SENSES["tape"]`, `_SENSES_LOCK`.
- Produces: `server.TAPE_LIVE_S = 15`; `server._tape_reply(idx: str, day: str) -> dict` (the §D reply); the route.

- [ ] **Step 1: Write the failing tests** (append to `test_frame_api.py`)

```python
from test_senses_api import _Cap          # the GET harness, one copy in the tree


def _ladder_doc(day="2026-09-11", n=8):
    doc = _tape(n=n)
    doc["session"] = f"NIFTY-I|5m|{day}"
    doc["rowAnchor"] = 0
    for i, b in enumerate(doc["closed"]):
        b.update({"o": 100 + i, "h": 104 + i, "l": 99 + i, "c": 101 + i, "vol": 20 + i, "buy": 12, "sell": 8 + i, "delta": 4 - i})
        b["ladder"] = [{"p": 100.0 + i, "b": 9, "s": 1, "bt": 3, "st": 1}, {"p": 101.0 + i, "b": 2, "s": 8, "bt": 1, "st": 2}]
    doc["events"] = [{"t": doc["closed"][1]["t"], "kind": "absorption", "side": 1, "p": 101.0, "size": 9}]
    doc["forming"] = {"t": doc["closed"][-1]["t"] + 300000, "o": 1, "h": 2, "l": 0, "c": 1, "vol": 3, "delta": 1, "buy": 2, "sell": 1,
                      "ladder": [{"p": 1.0, "b": 2, "s": 1, "bt": 1, "st": 1}]}
    return doc


def _isolate(tmp_path, monkeypatch):
    import tape_log
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
    server._SENSES["tape"].pop("NIFTY", None)


def test_api_tape_live_when_the_extension_posted_within_15s(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and j["src"] == "live" and j["interval"] == 5 and j["tag"] == "M"
    assert len(j["bars"]) == 8 and j["bars"][0]["ladder"] and "cvd" in j["bars"][0] and "stacks" in j["bars"][0]
    assert j["forming"]["ladder"] and j["forming_why"] is None
    assert j["levels"]["session"]["poc"] is not None and isinstance(j["levels"]["nodes"], list)
    assert j["levels"]["prior"] == [] and j["levels"]["prior_why"] == "no earlier day in the record yet"
    assert j["marks"]["ofd"][0]["src"] == "ofd" and all(m["src"] == "tm" and m["tag"] == "I" for m in j["marks"]["tm"])
    assert j["rowSize"] == 5 and j["rowAnchor"] == 0


def test_api_tape_file_when_the_extension_is_silent(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    server._SENSES["tape"]["NIFTY"]["at"] -= 60          # a minute of silence
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and j["src"] == "file" and len(j["bars"]) == 8
    assert j["forming"] is None and "not posting" in j["forming_why"]
    assert j["marks"]["ofd"] and j["marks"]["ofd"][0]["kind"] == "absorption"


def test_api_tape_neither_is_the_third_sentence(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["ok"] is False and "no prints record for NIFTY on 2026-09-11" in cap.sent["why"]


def test_api_tape_prior_days_and_naked_from_the_record(tmp_path, monkeypatch):
    import tape_log
    _isolate(tmp_path, monkeypatch)
    for day in ("2026-09-09", "2026-09-10"):
        tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
        server.Handler.do_POST(_Req("/api/frame", _ladder_doc(day=day)))
    tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc(day="2026-09-11")))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert [p["day"] for p in j["levels"]["prior"]] == ["2026-09-10", "2026-09-09"]
    assert j["levels"]["prior_why"] is None
    assert isinstance(j["levels"]["naked"], list)


def test_api_tape_ladder_why_when_a_bar_lacks_one(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    doc = _ladder_doc()
    del doc["closed"][0]["ladder"]
    server.Handler.do_POST(_Req("/api/frame", doc))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert "predates ladders" in cap.sent["ladder_why"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_frame_api.py -k api_tape -q`
Expected: 5 failed (`cap.sent` is None — the route fell through to the static handler, or an `AttributeError` on `_Cap`).

- [ ] **Step 3: Implement**

`server.py` imports: `import prints` beside `import tape_log`.

`server.py`, a module-level function (place it just above `class Handler`):

```python
TAPE_LIVE_S = 15      # the extension's own FRAME_STALE_MS boundary (orderflow-desk main.js:53)
_LADDER_WHY = "extension predates ladders (orderflow-desk < 0.3.1)"
_NO_FLAGS = {"stacks": None, "unfinished_high": None, "unfinished_low": None, "poc": None}


def _tape_reply(idx: str, day: str) -> dict:
    """GET /api/tape: bars + levels + two mark families, three sentences (spec §D)."""
    with _SENSES_LOCK:
        held = _SENSES["tape"].get(idx)
    doc = (held or {}).get("doc") or {}
    live = bool(held) and str(doc.get("session", "")).endswith(day) and (time.time() - held["at"]) < TAPE_LIVE_S
    if live:
        raw, forming, ofd = list(doc.get("closed") or []), doc.get("forming"), list(doc.get("events") or [])
        meta = {"rowSize": doc.get("rowSize"), "rowAnchor": doc.get("rowAnchor", 0), "lot": doc.get("lot")}
        forming_why = None
    else:
        raw = tape_log.read_bars(day, idx)
        if not raw:
            return {"ok": False, "idx": idx, "day": day, "src": None,
                    "why": f"no prints record for {idx} on {day} — GoCharting was on another index, or the extension never posted"}
        forming, ofd = None, tape_log.read_marks(day, idx)
        meta = {"rowSize": raw[0].get("rowSize"), "rowAnchor": raw[0].get("rowAnchor", 0), "lot": raw[0].get("lot")}
        forming_why = (f"extension not posting for {int(time.time() - held['at'])}s — showing the record" if held
                       else "extension not posting since server start — showing the record")
    row, anchor = float(meta["rowSize"] or 5), float(meta["rowAnchor"] or 0)
    bars = []
    for b in prints.with_cvd(raw):
        f = prints.bar_flags(b, row, anchor)
        bars.append({**{k: b.get(k) for k in ("t", "o", "h", "l", "c", "vol", "buy", "sell", "delta", "cvd", "oi", "fromTicks", "ladder")},
                     **(f or _NO_FLAGS)})
    ladder_why = _LADDER_WHY if any(b.get("ladder") is None for b in bars) else None
    if forming is not None:
        forming = {**forming, **(prints.bar_flags(forming, row, anchor) or _NO_FLAGS)}
    prof = prints.profile(raw)
    prior_days = [(d, tape_log.read_bars(d, idx)) for d in tape_log.prior_days(day, idx, 5)]
    prior = prints.prior_levels(prior_days)
    tm, tm_why = prints.tm_marks(raw)
    return {
        "ok": True, "idx": idx, "day": day, "interval": 5, "src": "live" if live else "file", "tag": "M", **meta,
        "bars": bars, "forming": forming, "forming_why": forming_why, "ladder_why": ladder_why,
        "levels": {"session": ({"poc": prof["poc"], "vah": prof["vah"], "val": prof["val"]} if prof else None),
                   "prior": prior, "prior_why": None if prior else "no earlier day in the record yet",
                   "naked": prints.naked(prior_days, raw), "nodes": prints.nodes(prof), "tag": "M",
                   "why": None if prof else "no bar with a ladder yet"},
        "marks": {"ofd": ofd, "tm": tm, "tm_why": tm_why},
        "why": None,
    }
```

`server.py` `do_GET`, immediately before `elif self.path.startswith("/api/frame/bars"):` (line 2036):

```python
        elif self.path.startswith("/api/tape"):
            # the ladder record and what prints.py reads off it (spec §D) --
            # live from the extension's last post, else from data/tape/, else
            # the third sentence. Streamed readers only; never a whole-file
            # json.load on this thread (record_read.py:1-15).
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            self._json(json.dumps(_tape_reply(self._idx(), day), default=str).encode())
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_frame_api.py -q`
Expected: all pass. (`instruments.ENABLED` must contain `NIFTY` for `_idx()` — it does; the other route tests rely on it.)

- [ ] **Step 5: Run the suite**

Run: `python -m pytest -q`
Expected: green apart from `test_docs_claims` counts (Task 13).

- [ ] **Step 6: Commit**

```bash
git add server.py test_frame_api.py
git commit -m "server: GET /api/tape -- bars, levels, and both mark families off the ladder record, live or from file, three sentences" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Seed the record from a recorded day (for the visual check)

**Files:**
- Create: `tapemap/tools/seed_tape_from_ofd.py`

**Interfaces:**
- Consumes: the `.ofd.json` export shape (`bars[]` with `ladder`), `tape_log.append`.
- Produces: `data/tape/tape_<idx>_<day>.jsonl` for a past day, so `/api/tape?day=` and the UI have something to draw off-hours.

- [ ] **Step 1: Write the tool**

```python
# tapemap/tools/seed_tape_from_ofd.py
"""One-off: a recorded orderflow-desk export -> the ladder record, so a past
day can be drawn without the extension. Rows are tagged src:"seed" so a
scorer can never mistake them for what the socket wrote.

    python tools/seed_tape_from_ofd.py "C:\\Users\\kaam\\Desktop\\Go charting\\NIFTY-I_5m_2026-09-18.ofd.json" [NIFTY]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tape_log  # noqa: E402


def main(path: str, idx: str = "NIFTY") -> None:
    j = json.load(open(path, encoding="utf-8"))
    bars = sorted((b for b in j["bars"] if isinstance(b.get("ladder"), list) and b["ladder"]), key=lambda b: b["t"])
    if not bars:
        raise SystemExit("no bars with a ladder in that file")
    day = str(j.get("session", "")).split("|")[-1] or bars[0].get("date")
    doc = {"session": j.get("session"), "closed": bars, "events": j.get("events") or [], "forming": None,
           "rowSize": 5, "rowAnchor": 0, "lot": 65}
    n = tape_log.append(doc, day, idx)
    # the seed tag, added after the fact so tape_log's row shape stays one shape
    p = tape_log.day_path(day, idx)
    rows = tape_log.read_bars(day, idx)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            r["src"] = "seed"
            f.write(json.dumps(r) + "\n")
    print(f"seeded {n['bars']} bars and {n['marks']} marks for {idx} {day} -> {p}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "NIFTY")
```

- [ ] **Step 2: Seed the 11-Sep and 18-Sep sessions and read them back**

Run:
```bash
python tools/seed_tape_from_ofd.py "C:\Users\kaam\Desktop\Go charting\orderflow-desk\test\session-2026-09-11.ofd.json"
python tools/seed_tape_from_ofd.py "C:\Users\kaam\Desktop\Go charting\NIFTY-I_5m_2026-09-18.ofd.json"
curl -s "http://127.0.0.1:8765/api/tape?idx=NIFTY&day=2026-09-18" | python -c "import json,sys; j=json.load(sys.stdin); print(j['ok'], j['src'], len(j['bars']), j['levels']['session'], len(j['levels']['nodes']), 'prior', [p['day'] for p in j['levels']['prior']], 'tm', len(j['marks']['tm']))"
```
Expected: two `seeded …` lines; then `True file 78 {...poc/vah/val...} <n> prior ['2026-09-11'] tm <n>`. The server must be running with Task 8's code; if the running server predates it, restart it **detached** (`START-HERE.md` §0.6) — never as a child of this session.

- [ ] **Step 3: Commit**

```bash
git add tools/seed_tape_from_ofd.py
git commit -m "tools: seed the ladder record from a recorded orderflow-desk export, rows tagged seed" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: `ui-v2` — the poll and the wiring

**Files:**
- Create: `ui-v2/src/trade/tape.ts`
- Modify: `ui-v2/src/trade/TradeTab.tsx` (import; beside line 428 `const footprint = useFootprint(index)`; the `<ContractChart …>` props at ~949–954; the legend block at ~1011–1030)
- Modify: `ui-v2/src/trade/ContractChart.tsx` (Props; refs at ~116–121; the `startLevelsOverlay(...)` call at ~165–178)
- Modify: `ui-v2/src/trade/LevelsOverlay.ts` (signature only, this task — the pass is Task 11)

**Interfaces:**
- Produces: `TapeReply`, `TapeBarRow`, `TapeLevels`, `TapeMark` types; `useTape(index): { reply: TapeReply | null; why: string }`; `ContractChart` prop `prints?: TapeReply | null`; `startLevelsOverlay` gains a final getter `getPrints: () => TapeReply | null`.

- [ ] **Step 1: Write `tape.ts`**

```ts
// ui-v2/src/trade/tape.ts
import { useEffect, useState } from 'react'
import type { IndexKey } from '../data'

/**
 * `/api/tape` — the ladder record and what the server reads off it (spec
 * 2026-09-19-orderflow-levels §D). One fetch, one cadence, any number of
 * mounts — the `./footprint` shape. This file computes NOTHING: levels, flags
 * and marks arrive computed and tagged; the overlay draws them.
 *
 * 30 s, not faster: levels move once per 5-minute bar, and 30 s is the cadence
 * this endpoint family already settled on (footprint.ts). The poll dies with
 * the tab.
 */
export interface TapeLadderRow { p: number; b: number; s: number; bt: number; st: number }
export interface TapeStack { side: 'buy' | 'sell'; low: number; high: number; run: number }
export interface TapeBarRow {
  t: number; o: number; h: number; l: number; c: number
  vol: number; buy: number; sell: number; delta: number; cvd: number
  oi: number | null; fromTicks: boolean
  ladder: TapeLadderRow[] | null
  stacks: TapeStack[] | null; unfinished_high: boolean | null; unfinished_low: boolean | null; poc: number | null
}
export interface TapeNode { p: number; vol: number; kind: 'HVN' | 'LVN' }
export interface TapeLevels {
  session: { poc: number; vah: number; val: number } | null
  prior: { day: string; poc: number; vah: number; val: number }[]
  prior_why: string | null
  naked: { day: string; poc: number; touched_t: number | null }[]
  nodes: TapeNode[]
  tag: 'M'
  why: string | null
}
export interface TapeMark {
  t: number; kind: string; side: -1 | 0 | 1 | null; p: number | null; size: number | null
  src: 'ofd' | 'tm'; why?: string; tag?: 'I'
}
export interface TapeReply {
  ok: true; idx: string; day: string; interval: 5; src: 'live' | 'file'; tag: 'M'
  rowSize: number | null; rowAnchor: number; lot: number | null
  bars: TapeBarRow[]
  forming: TapeBarRow | null; forming_why: string | null
  ladder_why: string | null
  levels: TapeLevels
  marks: { ofd: TapeMark[]; tm: TapeMark[]; tm_why: string | null }
  why: null
}

export function useTape(index: IndexKey): { reply: TapeReply | null; why: string } {
  const [reply, setReply] = useState<TapeReply | null>(null)
  const [why, setWhy] = useState<string>('prints record abhi padha ja raha hai')
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/tape?idx=${index}`)
        const j = await r.json()
        if (!alive) return
        if (!j.ok) {
          setWhy(`prints record padha nahi ja saka — ${j.why || 'server ne wajah nahi batayi'}`)
          setReply(null); return
        }
        setReply(j as TapeReply)
        setWhy('')
      } catch (e) {
        // the backend not answering is "could not check", not "no prints today"
        if (alive) { setWhy(`prints record padha nahi ja saka — backend ne jawab nahi diya (${String(e)})`); setReply(null) }
      }
    }
    // the first read ALWAYS happens; the hidden-tab guard is on the repeat only (footprint.ts measured why)
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 30000)
    return () => { alive = false; window.clearInterval(id) }
  }, [index])
  return { reply, why }
}
```

- [ ] **Step 2: Thread it through `ContractChart`**

`ContractChart.tsx` imports — add:

```ts
import type { TapeReply } from './tape'
```

`Props` — add after `marks?: FootEvent[] | null`:

```ts
  /** The ladder record's levels, flags and marks (`/api/tape`, ./tape.ts), from
   *  the SAME `useTape` poll TradeTab's legend reads. Null = could not be read,
   *  which is not an empty day and is not drawn as one; TradeTab prints the why. */
  prints?: TapeReply | null
```

Refs — after `marksRef.current = marks` (line 121):

```ts
  const printsRef = useRef<TapeReply | null>(prints ?? null)
  printsRef.current = prints ?? null
```

The `startLevelsOverlay(...)` call — add a final getter after `() => marksRef.current,`:

```ts
      () => printsRef.current,
```

`LevelsOverlay.ts` `startLevelsOverlay` signature — add the last parameter after `getMarks: () => FootEvent[] | null,`:

```ts
  /** The ladder record (`/api/tape`): levels, per-bar flags, and the `tm`
   *  mark family. Null draws nothing; TradeTab prints the reason. */
  getPrints: () => TapeReply | null,
```

and its import block:

```ts
import type { TapeReply } from './tape'
```

Inside `draw`, where the other getters are read (`const marks = getMarks()`), add:

```ts
    const prints = getPrints()
```

and fold it into the redraw signature: find the line that builds the per-frame signature string (search `lastSig`), and add this key to whatever it concatenates:

```ts
    const printsKey = prints ? `${prints.src}:${prints.bars.length}:${prints.forming?.t ?? ''}:${prints.forming?.vol ?? ''}:${prints.marks.tm.length}` : 'x'
```

(For this task `prints` is read and keyed but not yet drawn; Task 11 adds the pass. The typecheck must pass with the variable used — the key uses it.)

- [ ] **Step 3: Thread it through `TradeTab`**

`TradeTab.tsx` imports — add `import { useTape } from './tape'`.
Beside line 428:

```ts
  const tape = useTape(index)
```

The `<ContractChart …>` props — add `prints={tape.reply}` after `marks={footprint.events}`.

The legend block (~1011–1030), after the existing marks sentence's closing `</div>`, add a sibling line:

```tsx
      {day && (
        <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
          Prints (ladder record, /api/tape):
          {tape.reply == null
            ? ` ${tape.why}`
            : ` ${tape.reply.src === 'live' ? 'live' : 'record'} · ${tape.reply.bars.length} bars`
              + (tape.reply.levels.session ? ` · POC ${tape.reply.levels.session.poc} VAH ${tape.reply.levels.session.vah} VAL ${tape.reply.levels.session.val}` : ` · ${tape.reply.levels.why}`)
              + ` · ${tape.reply.levels.nodes.length} nodes · ${tape.reply.marks.tm.length} tm marks [I]`
              + (tape.reply.forming_why ? ` · ${tape.reply.forming_why}` : '')
              + (tape.reply.ladder_why ? ` · ${tape.reply.ladder_why}` : '')
              + (tape.reply.levels.prior_why ? ` · ${tape.reply.levels.prior_why}` : '')}
        </div>
      )}
```

- [ ] **Step 4: Typecheck**

Run (from `ui-v2`): `npm run typecheck`
Expected: exit 0. A "declared but never read" error on `printsKey` means the signature line was not found — read `LevelsOverlay.ts` around `lastSig` and concatenate `printsKey` into the string that is compared to `lastSig`.

- [ ] **Step 5: Commit**

```bash
git add ui-v2/src/trade/tape.ts ui-v2/src/trade/TradeTab.tsx ui-v2/src/trade/ContractChart.tsx ui-v2/src/trade/LevelsOverlay.ts
git commit -m "ui-v2: the /api/tape poll, threaded to the overlay and the legend line" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: `ui-v2` — the `drawPrints` pass

**Files:**
- Modify: `ui-v2/src/trade/LevelsOverlay.ts` (a new `drawPrints` function; its call at the end of `draw`, after the `drawMarks` block at ~1826–1835)

**Interfaces:**
- Consumes: `prints: TapeReply | null`, `conv`, `pane`, `pal`, `dTimes`, `lastIdx`, `hhmmMins` (exists in the file), `placeLabel` (exists), `withAlpha` (exists), `halfBarPx` (exists, line 355).
- Produces: levels lines, HVN/LVN bands, per-bar stack brackets and unfinished ticks, hollow `tm` glyphs.

- [ ] **Step 1: Add the pass**

Insert this function above `function drawMarks(` (line ~1178):

```ts
/* ── The ladder record: levels, per-bar flags, and the tm family ──────────
   Spec 2026-09-19-orderflow-levels §F. Levels are prices and draw at any
   interval. Per-bar marks are placed by their own t and prices, never
   snapped to a candle (footprint.ts:21-27). The tm glyphs are HOLLOW
   versions of the ofd family's shapes with a lowercase letter, on the
   opposite side of the bar, so the two families read as two readers and
   never share a de-overlap pool. */
const TM_LETTER: Record<string, string> = { absorption: 'a', exhaustion: 'e', climax: 'c' }

function drawPrints(
  ctx: CanvasRenderingContext2D,
  conv: Converters,
  pane: PaneRect,
  pal: Palette,
  times: number[],
  reply: TapeReply,
  lastIdx: number,
) {
  const yOf = (p: number) => conv.priceToY(p)
  const inPane = (y: number) => Number.isFinite(y) && y >= pane.y + LEGEND_BAND_PX && y <= pane.y + pane.height - 2
  const line = (p: number, style: string, dash: number[], label: string) => {
    const y = yOf(p)
    if (!inPane(y)) return
    ctx.strokeStyle = style
    ctx.setLineDash(dash)
    ctx.beginPath(); ctx.moveTo(pane.x, y); ctx.lineTo(pane.x + pane.width, y); ctx.stroke()
    ctx.setLineDash([])
    placeLabel(label, pane.x + 3, y - STRUCT_LABEL_PX, style)
  }
  const row = reply.rowSize ?? 5
  const L = reply.levels

  // nodes first, underneath everything: HVN a wash, LVN a dashed box (5-point bins)
  for (const n of L.nodes) {
    const yt = yOf(n.p + 2.5), yb = yOf(n.p - 2.5)
    if (!Number.isFinite(yt) || !Number.isFinite(yb)) continue
    if (n.kind === 'HVN') {
      ctx.fillStyle = withAlpha(pal.ink, 0.10)
      ctx.fillRect(pane.x, yt, pane.width, yb - yt)
    } else {
      ctx.strokeStyle = withAlpha(pal.textMuted, 0.8)
      ctx.setLineDash([3, 4])
      ctx.strokeRect(pane.x + 0.5, yt + 0.5, pane.width - 1, Math.max(1, yb - yt - 1))
      ctx.setLineDash([])
    }
  }
  // session value area and POC
  if (L.session) {
    line(L.session.vah, withAlpha(pal.textMuted, 0.9), [6, 5], `VAH ${L.session.vah}`)
    line(L.session.val, withAlpha(pal.textMuted, 0.9), [6, 5], `VAL ${L.session.val}`)
    line(L.session.poc, withAlpha(pal.accent, 0.95), [6, 5], `POC ${L.session.poc}`)
  }
  // prior days, fainter, labelled with the day
  for (const p of L.prior) {
    line(p.poc, withAlpha(pal.accent, 0.45), [2, 4], `POC ${p.day.slice(5)}`)
    line(p.vah, withAlpha(pal.textMuted, 0.45), [2, 4], `VAH ${p.day.slice(5)}`)
    line(p.val, withAlpha(pal.textMuted, 0.45), [2, 4], `VAL ${p.day.slice(5)}`)
  }
  // naked POCs: from the pane's left edge to the touching bar, or to the right edge
  for (const n of L.naked) {
    const y = yOf(n.poc)
    if (!inPane(y)) continue
    const xEnd = n.touched_t != null ? conv.timeToX(n.touched_t) : pane.x + pane.width
    ctx.strokeStyle = withAlpha(pal.accent, 0.8)
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(pane.x, y); ctx.lineTo(xEnd, y); ctx.stroke()
    placeLabel(`NPOC ${n.day.slice(5)}`, pane.x + 3, y - STRUCT_LABEL_PX, withAlpha(pal.accent, 0.9))
  }

  // per-bar flags: a stack is a bracket on its price span; unfinished is a tick outside the extreme
  const half = halfBarPx(conv, times)
  const tCut = lastIdx >= 0 && times[lastIdx] != null ? times[lastIdx] + 300000 : Infinity
  for (const b of reply.bars) {
    if (b.t > tCut) continue
    const x = conv.timeToX(b.t)
    if (!Number.isFinite(x) || x < pane.x || x > pane.x + pane.width) continue
    for (const s of b.stacks ?? []) {
      const yt = yOf(s.high + row / 2), yb = yOf(s.low - row / 2)
      if (!Number.isFinite(yt) || !Number.isFinite(yb)) continue
      ctx.strokeStyle = s.side === 'buy' ? pal.bull : pal.bear
      ctx.lineWidth = 1.5
      ctx.strokeRect(x - half + 1.5, yt + 0.5, Math.max(2, half * 2 - 3), Math.max(2, yb - yt - 1))
      ctx.lineWidth = 1
    }
    if (b.unfinished_high) {
      const y = yOf(b.h)
      if (Number.isFinite(y)) { ctx.strokeStyle = pal.textMuted; ctx.beginPath(); ctx.moveTo(x - 3, y - 4); ctx.lineTo(x + 3, y - 4); ctx.stroke() }
    }
    if (b.unfinished_low) {
      const y = yOf(b.l)
      if (Number.isFinite(y)) { ctx.strokeStyle = pal.textMuted; ctx.beginPath(); ctx.moveTo(x - 3, y + 4); ctx.lineTo(x + 3, y + 4); ctx.stroke() }
    }
  }

  // the tm family: hollow shelf (absorption), chevron (exhaustion), diamond (climax), lowercase letter
  ctx.font = `bold 9px ${MARK_FONT}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  for (const m of reply.marks.tm) {
    if (m.p == null || m.t > tCut) continue
    const x = conv.timeToX(m.t), y = yOf(m.p)
    if (!Number.isFinite(x) || !inPane(y)) continue
    const col = m.side === 1 ? pal.bull : m.side === -1 ? pal.bear : pal.textMuted
    ctx.strokeStyle = col
    ctx.lineWidth = 1.25
    const u = Math.max(MARK_U_MIN, Math.min(MARK_U_MAX, half))
    const xs = x + half + u   // the opposite side of the bar from the ofd glyphs
    ctx.beginPath()
    if (m.kind === 'absorption') {            // shelf
      ctx.rect(xs - u * 1.8, y - u * 0.5, u * 3.6, u)
    } else if (m.kind === 'exhaustion') {     // chevron, apex away from the candle
      const dir = m.side === -1 ? -1 : 1
      ctx.moveTo(xs - u, y + dir * u); ctx.lineTo(xs, y - dir * u * 0.2); ctx.lineTo(xs + u, y + dir * u)
    } else {                                   // diamond
      ctx.moveTo(xs, y - u); ctx.lineTo(xs + u, y); ctx.lineTo(xs, y + u); ctx.lineTo(xs - u, y); ctx.closePath()
    }
    ctx.stroke()
    ctx.fillStyle = col
    ctx.fillText(TM_LETTER[m.kind] ?? '?', xs, y + (m.kind === 'exhaustion' ? (m.side === -1 ? u * 0.7 : -u * 0.7) : 0))
    ctx.lineWidth = 1
  }
}
```

Then at the end of `draw`, after the `drawMarks` block (the `if (lastIdx >= 0 && marks && marks.length) { … }`), add:

```ts
    if (prints) {
      ctx.save()
      ctx.beginPath()
      ctx.rect(pane.x, pane.y, pane.width, pane.height)
      ctx.clip()
      drawPrints(ctx, conv, pane, pal, dTimes, prints, lastIdx)
      ctx.restore()
    }
```

`MARK_FONT`, `MARK_U_MIN`, `MARK_U_MAX`, `LEGEND_BAND_PX`, `STRUCT_LABEL_PX`, `placeLabel`, `withAlpha`, `halfBarPx` all exist in the file (lines 355–370, 1104–1133, and the structures pass). If `placeLabel` is scoped inside `draw` rather than module-level, pass it in as a parameter — mirror how `drawStructures` receives `takenLabels`.

- [ ] **Step 2: Typecheck**

Run (from `ui-v2`): `npm run typecheck`
Expected: exit 0.

- [ ] **Step 3: The visual check — the honest one, not automated**

With the server on Task 8's code and the 18-Sep day seeded (Task 9): the Trade tab reads today's day by default, so for an off-hours check confirm the reply the overlay would draw from the browser console: `fetch('/api/tape?idx=NIFTY&day=2026-09-18').then(r=>r.json()).then(j=>console.log(j.levels, j.marks.tm.length))`. On the next live session, confirm in the pane at **3 min** and at **5 min**: session POC/VAH/VAL lines with labels, HVN washes, LVN dashed boxes, prior-day lines when a prior day exists, stack brackets and unfinished ticks on 5-minute bars, hollow lowercase `a`/`e`/`c` glyphs on the right of bars beside the filled A/E/C. Record what was seen in the Task 13 HANDOFF entry — including anything wrong.

- [ ] **Step 4: Commit**

```bash
git add ui-v2/src/trade/LevelsOverlay.ts
git commit -m "ui-v2: drawPrints -- session and prior-day levels, naked POCs, HVN/LVN, stack brackets, unfinished ticks, and the hollow tm glyphs" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11b: `ui-v2` — hover shows a mark's `why`

**Files:**
- Modify: `ui-v2/src/trade/Callout.tsx` (`Props` at lines 15–30; the render tail after the `narr` / "koi event nahi" ternary, ~line 268)
- Modify: `ui-v2/src/trade/ContractChart.tsx` (the `<Callout …>` element at ~294–305)

**Interfaces:**
- Consumes: `TapeMark` (`./tape`), `FootEvent` (`./footprint`), `prints` and `marks` props, `timesRef`, `barsRef`.
- Produces: `Callout` props `tm?: TapeMark[]`, `ofd?: FootEvent[]` — the marks whose own stamp falls inside the hovered bar's span, listed with their `why`. Spec §F: *"Hover on either family shows its `why` (the extension's marks carry none — the tooltip says so)."*

- [ ] **Step 1: Extend `Callout`**

Imports — add:

```ts
import type { TapeMark } from './tape'
import type { FootEvent } from './footprint'
```

`Props` — add after `rot?: RotationSignal | null`:

```ts
  /** The tm marks stamped inside this bar's span (server-side, each with a `why`). */
  tm?: TapeMark[]
  /** The extension's marks stamped inside this bar's span. They carry no `why`
   *  on the wire, and the row says so rather than inventing one. */
  ofd?: FootEvent[]
```

Render — the component's root `<div>` ends with the `narr ? (…) : (…)` ternary followed by `</div>`. Insert this block **between** the ternary's closing `)}` and that final `</div>`:

```tsx
      {((tm && tm.length) || (ofd && ofd.length)) ? (
        <div style={{ padding: '7px 11px 9px', borderTop: `1px solid ${pal.border}` }}>
          <div style={{ fontSize: 10, color: pal.textMuted, marginBottom: 2 }}>prints · is bar ke marks</div>
          {ofd?.map((e, i) => (
            <div key={`o${i}`} style={{ fontSize: 11, color: pal.textSecondary, lineHeight: 1.4 }}>
              {e.kind}{e.p != null ? ` @ ${e.p}` : ''} · extension (ofd) [I] — extension ne wajah nahi bheji
            </div>
          ))}
          {tm?.map((m, i) => (
            <div key={`t${i}`} style={{ fontSize: 11, color: pal.textSecondary, lineHeight: 1.4 }}>
              {m.kind}{m.p != null ? ` @ ${m.p}` : ''} · tapemap (tm) [I] — {m.why}
            </div>
          ))}
        </div>
      ) : null}
```

Destructure `tm` and `ofd` from props where the component reads `narr` and `rot`.

- [ ] **Step 2: Pass the hovered bar's marks from `ContractChart`**

Above the `return (` in `ContractChart`, after `const hoverBar = …`:

```ts
  // The marks whose OWN stamp falls inside the hovered bar's span — never
  // snapped: a 5-minute mark lists under whichever 3-minute bar contains it.
  const hoverT = hover != null ? timesRef.current[hover] : null
  const hoverTNext = hover != null ? (timesRef.current[hover + 1] ?? (hoverT != null ? hoverT + 300000 : null)) : null
  const tmHere = prints && hoverT != null && hoverTNext != null
    ? prints.marks.tm.filter((m) => m.t >= hoverT && m.t < hoverTNext) : []
  const ofdHere = marks && hoverBar
    ? marks.filter((e) => e.t >= hoverBar.t && (hover != null && bars[hover + 1] ? e.t < bars[hover + 1].t : true)) : []
```

and on the `<Callout …>` element add:

```tsx
          tm={tmHere}
          ofd={ofdHere}
```

- [ ] **Step 3: Typecheck**

Run (from `ui-v2`): `npm run typecheck`
Expected: exit 0. (`FootEvent.t` and `TapeBar.t` are both zero-padded `"HH:MM"`, so the string comparison orders correctly — the same comparison `footprint.ts:lookUnder` already relies on.)

- [ ] **Step 4: Commit**

```bash
git add ui-v2/src/trade/Callout.tsx ui-v2/src/trade/ContractChart.tsx
git commit -m "ui-v2: hovering a bar lists its tm and ofd marks with their why, or says the extension sent none" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: `ui-v2` — the delta / CVD pane, 5 and 15 minutes only

**Files:**
- Modify: `ui-v2/src/trade/indicators.ts` (`buildIndicators` signature and body, line 230)
- Modify: `ui-v2/src/trade/ContractChart.tsx` (the `setIndicators` call at line 245; a new prop `publishedInterval`)
- Modify: `ui-v2/src/trade/TradeTab.tsx` (pass `publishedInterval` to `ContractChart`; the legend line)

**Interfaces:**
- Consumes: `TapeReply.bars[].{t, delta, cvd}`, `TapeBar.t` ("HH:MM"), `publishedInterval: number | null`.
- Produces: `buildIndicators(bars: TapeBar[], prints?: TapeReply | null, publishedInterval?: number | null): IndicatorRenderData[]`; `alignDelta(bars, prints, interval): { delta: (number|null)[]; cvd: (number|null)[] } | null` (exported for a future test).

- [ ] **Step 1: Extend `indicators.ts`**

Imports — add `import type { TapeReply } from './tape'`.

Add above `buildIndicators`:

```ts
const IST_MS = 5.5 * 3600000
/** "HH:MM" IST for a tape-bar epoch, the label convention the chart's bars use. */
function hhmmOf(t: number): string {
  const d = new Date(t + IST_MS)
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
}
const DELTA_UP = '#26a69a'   // the CHART_UP pair, one meaning: sign of the delta
const DELTA_DOWN = '#ef5350'

/** Delta and CVD aligned 1:1 with the chart's bars, or null when they cannot be:
 *  the record is 5-minute; 15 sums three record bars exactly; 3 and 1 do not
 *  divide it (spec §J.5). Alignment is by "HH:MM" label, never by index. */
export function alignDelta(
  bars: TapeBar[], prints: TapeReply | null | undefined, interval: number | null | undefined,
): { delta: (number | null)[]; cvd: (number | null)[] } | null {
  if (!prints || (interval !== 5 && interval !== 15)) return null
  const per = new Map<string, number>()        // record label -> delta
  for (const b of prints.bars) per.set(hhmmOf(b.t), b.delta)
  const delta: (number | null)[] = []
  const cvd: (number | null)[] = []
  let run: number | null = null
  for (const bar of bars) {
    let d: number | null = null
    if (interval === 5) {
      d = per.has(bar.t) ? per.get(bar.t)! : null
    } else {
      // 15: the record bars whose minute-of-hour floors into this bar's 15-minute bucket
      const [hh, mm] = bar.t.split(':').map(Number)
      const parts = [0, 5, 10].map((k) => per.get(`${String(hh).padStart(2, '0')}:${String(mm + k).padStart(2, '0')}`))
      d = parts.every((v) => v != null) ? parts.reduce((a, v) => a + (v as number), 0) : null
    }
    delta.push(d)
    if (d != null) run = (run ?? 0) + d
    cvd.push(d != null ? run : null)
  }
  return delta.some((v) => v != null) ? { delta, cvd } : null
}
```

Change `buildIndicators`:

```ts
export function buildIndicators(bars: TapeBar[], prints?: TapeReply | null, publishedInterval?: number | null): IndicatorRenderData[] {
  const out: IndicatorRenderData[] = [
    {
      instanceId: 'oi', placement: 'pane',
      label: oiLabel(series(bars, (b) => b.oi), series(bars, (b) => b.c), 'FUT', false),
      outputs: [{ name: 'oi', values: series(bars, (b) => b.oi), color: OI_LINE }],
    },
  ]
  // delta / CVD off the ladder record, only where the two series line up (5 / 15 min)
  const dc = alignDelta(bars, prints, publishedInterval)
  if (dc) {
    const last = [...dc.delta].reverse().find((v) => v != null)
    out.push({
      instanceId: 'delta', placement: 'pane',
      label: `Δ prints [M] · last ${last == null ? '—' : (last > 0 ? '+' : '') + last} lots · CVD ${dc.cvd[dc.cvd.length - 1] ?? '—'}`,
      outputs: [
        { name: 'delta', values: dc.delta, color: (last ?? 0) >= 0 ? DELTA_UP : DELTA_DOWN, style: 'histogram' },
        { name: 'cvd', values: dc.cvd, color: OI_LINE },
      ],
    })
  }
  return out
}
```

(The existing comment block inside the `oi` entry can stay; keep it — only the surrounding structure changes.)

- [ ] **Step 2: Wire the props**

`ContractChart.tsx` `Props` — add:

```ts
  /** The interval the backend says the bars ARE (TradeTab's `publishedInterval`).
   *  The delta pane draws only at 5 or 15 — see indicators.alignDelta. */
  publishedInterval?: number | null
```

and change line 245 `engine.setIndicators(buildIndicators(bars))` to:

```ts
    engine.setIndicators(buildIndicators(bars, prints ?? null, publishedInterval ?? null))
```

and add `prints, publishedInterval` to that effect's dependency array (it is the effect keyed on `[index, day, bars]` — make it `[index, day, bars, prints, publishedInterval]`).

`TradeTab.tsx` — pass `publishedInterval={publishedInterval}` to `<ContractChart …>`. In the legend line from Task 10, append before the closing of the template:

```tsx
              + (tape.reply && publishedInterval !== 5 && publishedInterval !== 15
                  ? ` · delta 5-min record se hai — is chart ke ${publishedInterval ?? '?'}-min bars se nahi jud sakta; 5 ya 15 par dekho`
                  : '')
```

- [ ] **Step 3: Typecheck**

Run (from `ui-v2`): `npm run typecheck`
Expected: exit 0. If candl's `IndicatorRenderData` requires fields beyond `instanceId/placement/label/outputs`, mirror exactly what the `oi` entry provides.

- [ ] **Step 4: Visual check** — at 5 min a second pane appears under OI with a signed histogram and a line; at 3 min it is absent and the legend prints the sentence. Note the result for Task 13.

- [ ] **Step 5: Commit**

```bash
git add ui-v2/src/trade/indicators.ts ui-v2/src/trade/ContractChart.tsx ui-v2/src/trade/TradeTab.tsx
git commit -m "ui-v2: delta and CVD as a candl pane off the ladder record, drawn only where the intervals line up" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 13: Docs, counts, and the handoff entry

**Files:**
- Modify: `tapemap/README.md`, `CLAUDE.md`, `START-HERE.md`, `context/research-findings.md` (every `**N tests pass**`), `START-HERE.md` §3 architecture block
- Modify: `tapemap/context/HANDOFF.md` (a dated entry at the top of "STATE OF THE APP"'s journal)
- Modify: `orderflow-desk/HANDOFF.md` (file map line for `main.js`; version)

- [ ] **Step 1: Get the real count**

Run: `python -m pytest -q 2>&1 | tail -3`
Expected: `N passed` (with only `test_docs_claims` failing on the stated number). Note N.

- [ ] **Step 2: Update every pinned count**

Run: `grep -rn "tests pass\|est count is now" README.md CLAUDE.md START-HERE.md context/research-findings.md`
Edit each hit's number to N (and the "as of" date to 2026-09-19 where one is printed beside it, e.g. `CLAUDE.md` "1062 tests, green as of 2026-08-26").

- [ ] **Step 3: `START-HERE.md` §3** — in the architecture block, beside the line that names `frame.py`/the frame log, add one line: `tape_log.py  data/tape/  (the ladder record: bars + the extension's marks, write-once)` and change `ui-v2/ (React, ABANDONED)` to `ui-v2/ (React on Vite, 5173 — restored 2026-09-18)`.

- [ ] **Step 4: `context/HANDOFF.md`** — a new dated entry at the top of the journal:

```markdown
### 2026-09-19 — the ladder record, levels and a second opinion on the Trade chart (spec 2026-09-19-orderflow-levels)

**What shipped.** orderflow-desk 0.3.1 posts each bar's `ladder` and the chart's `rowAnchor`
(`main.js:234-235, :244`). `tape_log.py` writes bars once by `t` to `data/tape/tape_<idx>_<day>.jsonl`
and the extension's marks once by `(t, kind, p, side)` to `ofd_marks_<idx>_<day>.jsonl`; registered in
`_isolate_mock_writers`, pinned in `test_day_state.py`. `prints.py` (pure) ports `decode.js`/`market.js`/
`board.js` — rebin, diagonal imbalance, stacks, per-bar POC and unfinished auction, the paired-row value
area, HVN/LVN — **pinned bar by bar against a fixture generated by the extension's own code over
2026-09-11** (`tools/gen_prints_expected.mjs` → `test/fixtures/prints_expected_2026-09-11.json`) — plus
cvd, prior-day levels, naked POC, and the `tm` family (absorption effort-vs-result, exhaustion delta
divergence at a new extreme, climax volume-shape; percentile-so-far; 0.75/0.50/0.90/0.15/6, NOT tuned).
`GET /api/tape` serves it all with the three sentences. ui-v2: `trade/tape.ts` polls it (30 s);
`LevelsOverlay.drawPrints` draws levels, bands, stack brackets, unfinished ticks and hollow lowercase
`a/e/c` beside the filled A/E/C; delta/CVD is a candl pane at 5 and 15 min only.

**What was seen live** (fill in on the first session): …

**Not done, on purpose.** No scoring of either mark family. The operator looks for five sessions
(spec §K); then she states the bar in `research-findings.md`, pre-registered; then a scorer exists.
The `tm` thresholds are not tuned before that. Spec 1b (convergence chips) builds on this record.
```

- [ ] **Step 5: `orderflow-desk/HANDOFF.md`** — in the file map, the `src/shell/main.js` line gains: `posts each bar's ladder and rowAnchor to TapeMap (0.3.1, 2026-09-19)`; the header's version reference becomes 0.3.1.

- [ ] **Step 6: Run the suite green**

Run: `python -m pytest -q`
Expected: `N passed`, no failures — `test_docs_claims` now agrees.

- [ ] **Step 7: Commit both repos**

```bash
git add README.md CLAUDE.md START-HERE.md context/research-findings.md context/HANDOFF.md
git commit -m "docs: the ladder record and prints on the Trade chart -- counts, architecture line, handoff entry" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```
and in `orderflow-desk`:
```bash
git add HANDOFF.md
git commit -m "docs: main.js posts the ladder and rowAnchor (0.3.1)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 8: Tell the operator** what to do that no test can: reload the extension at `chrome://extensions` and the GoCharting tab; restart the TapeMap server **detached**; open the Trade tab at 5 min on the next session and look.
