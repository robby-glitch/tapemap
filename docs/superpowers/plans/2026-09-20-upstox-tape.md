# The Upstox tape — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record every decoded frame of each index future off the Upstox socket, reconstruct a 5-minute per-price ladder from consecutive frames, write it beside GoCharting's record, measure the two by shape, and draw the Upstox family dotted on the Trade chart with one agreement line — spec `docs/superpowers/specs/2026-09-20-upstox-tape-design.md`.

**Architecture:** One hook in `upstox_feed._absorb` feeds a bounded deque (`book_log.Book`); the senses loop drains it to `data/book/` and into `ux_log`, which runs the pure `ladder` over frames and writes closed bars to `data/tape/ux_<idx>_<day>.jsonl`. `gate`, `runs` and `impact` are pure over those outputs; `server._tape_reply` gains a `ux` object; ui-v2 draws it. Nothing replaces GoCharting; §K is the operator's.

**Tech Stack:** Python 3.13 stdlib only for every module (`ThreadingHTTPServer`, no third-party); pytest; ui-v2 React 19 + TypeScript, vendored candl (pristine, never edited), `npx tsc --noEmit` as the only UI gate.

## Global Constraints

- **Commit trailer, exactly:** `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Nothing else.
- **Never `git add data/` or anything under it.** `data/trigger_log.jsonl` is modified in the tree and is never committed on this branch.
- **Never edit `ui-v2/src/vendor/candl/*` or `orderflow-desk/src/engine/*`.**
- **Never start, stop or restart the operator's server (8765), Vite (5173) or browser.** Verify with tests and `python -c` only.
- **Modules `ladder.py`, `gate.py`, `runs.py`, `impact.py` are pure: stdlib only, no I/O, no clock.** `book_log.py` and `ux_log.py` are the only new files that touch disk, fail-soft, opened per call in `"a"` mode (`senses.py:_append`).
- **Every number on the wire carries `tag` `"M"` or `"I"` as the spec's §A table says; every nullable field has a `*_why` sibling that is non-null exactly when the field is null.** Three sentences, never one (CLAUDE.md rule 6).
- **No hit rate, verdict or pass/fail is ever printed** (CLAUDE.md rule 4). `gate.py` returns numbers.
- **Constants from Order Flow Lab are named once and not tuned:** `RUN_N = 3`, `RUN_PCT = 0.90`, `RUN_WIN_S = 1200`, `RUN_GAP_S = 3`, `RUN_MIN_N = 50`, `IMPACT_WIN_S = 120`, `HALF_TICK = 0.55`.
- **Every task that adds tests bumps `context/DEFERRED.md` line 22 (`**Test count is now N**`) in the same commit** (ledger rule; `test_docs_claims.py` pins it). Run `python -m pytest -q 2>&1 | tail -3` to read N; the 3 pre-existing `test_desk_numbers.py` failures are not ours and stay.
- **Baseline before Task 1:** `python -m pytest -q` → `1266 passed, 3 failed`; `cd ui-v2 && npx tsc --noEmit` → exit 0.
- **Day strings are `YYYY-MM-DD`; bar `t` is the bar's open in epoch ms, IST session; `ltt` is epoch ms at second resolution; quantities on the book record are exchange units, on ladders lots.**

## File map

| file | responsibility |
|---|---|
| `book_log.py` (new) | frame → compact row; bounded deque; change-only, restart-safe append to `data/book/`; streamed read |
| `upstox_feed.py` (modify `:76–95`, `:179–200`) | `on_frame` attribute, called per key after the merge |
| `server.py` (modify `_SENSES` `:72–113`, `_senses_loop` `:786–848`, `_coverage` `:2468`, `_tape_reply` `:1054–1130`, `_isolate_mock_writers` `:2261–2289`) | wiring, the `ux` reply |
| `prints.py` (modify `rebin :33`, `profile :102`, `nodes :138`) | `u` pass-through |
| `upstox_instruments.py` (modify `_slice :91`) | `lot_size`, `tick_size` in the cached slice; `lot_tick(name)` |
| `ladder.py` (new) | `attribute(prev, cur, tick)`; `Ladder` (bins, bars, fills, counters, `infer_lot`, `infer_tick`) |
| `ux_log.py` (new) | per-index state, bar close → `data/tape/ux_<idx>_<day>.jsonl`, `rebuild`, `read_bars` |
| `gate.py` (new) | `per_bar`, `session` |
| `runs.py` (new) | `Runs.on_fill` |
| `impact.py` (new) | `Impact.on_frame`, `.read()` |
| `tools/gate_report.py` (new) | the day's `gate.session` from files, printed as a table |
| `ui-v2/src/trade/tape.ts`, `LevelsOverlay.ts`, `indicators.ts`, `TradeTab.tsx`, `ContractChart.tsx`, `Callout.tsx` | the face |
| `conftest.py`, `test_day_state.py`, `.gitignore`, `context/DEFERRED.md`, `context/HANDOFF.md`, `START-HERE.md`, `CLAUDE.md` | registrations and docs |

---

### Task 1: `book_log.py` — the book record

**Files:**
- Create: `book_log.py`
- Modify: `conftest.py` (add the `book_log.DIR` redirect to the existing autouse fixture)
- Test: `test_book_log.py`

**Interfaces:**
- Consumes: `upstox_adapter._core(feed)`, `upstox_adapter.depth_ladder(feed)`, `upstox_adapter._num(x)` (existing).
- Produces: `book_log.DIR`, `MAXLEN`, `day_path(day, idx) -> str`, `row_of(feed, cts=None, now_ms=None) -> dict | None`, `last_t(path) -> int`, `first_t(path) -> int | None`, `read_rows(day, idx) -> Iterator[dict]`, `class Book(day=None)` with `watch(idx, key)`, `on_frame(key, feed, cts=None, now_ms=None) -> bool`, `flush(day=None) -> list[tuple[str, dict]]`, attributes `dropped`, `written`, `book_from: dict[str, str]`.

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_book_log.py
"""The book record: one compact row per frame that changed, never on the feed thread."""
import builtins
import json
import os

import book_log

FUT = "NSE_FO|58072"


def _frame(vtt=1023750, ltp=24271.7, ltq=65, ltt=1787200010000, bids=((24270.6, 65), (24270.5, 130)),
           asks=((24272.0, 65), (24272.9, 65))):
    lv = [{"bidQ": bq, "bidP": bp, "askQ": aq, "askP": ap}
          for (bp, bq), (ap, aq) in zip(bids, asks)]
    return {"fullFeed": {"marketFF": {"ltpc": {"ltp": ltp, "ltt": ltt, "ltq": ltq, "cp": 24117.6},
                                      "marketLevel": {"bidAskQuote": lv},
                                      "vtt": vtt, "oi": 12873510.0, "tbq": 168090.0, "tsq": 292630.0}}}


def test_row_of_is_the_compact_shape_best_first():
    r = book_log.row_of(_frame(), cts=1787200010500, now_ms=1787200010600)
    assert r["t"] == 1787200010600 and r["cts"] == 1787200010500
    assert r["ltt"] == 1787200010000 and r["ltp"] == 24271.7 and r["ltq"] == 65 and r["vtt"] == 1023750
    assert r["oi"] == 12873510 and r["tbq"] == 168090 and r["tsq"] == 292630
    assert r["b"] == [[24270.6, 65], [24270.5, 130]] and r["a"] == [[24272.0, 65], [24272.9, 65]]


def test_row_of_is_none_for_an_index_feed_with_no_book():
    assert book_log.row_of({"fullFeed": {"indexFF": {"ltpc": {"ltp": 24200.0}}}}) is None


def test_on_frame_ignores_unwatched_keys_and_skips_identical_frames():
    b = book_log.Book(day="2026-09-21")
    assert b.on_frame(FUT, _frame(), now_ms=1) is False          # not watched yet
    b.watch("NIFTY", FUT)
    assert b.watched() == {"NIFTY"}
    assert b.on_frame(FUT, _frame(), now_ms=2) is True
    assert b.on_frame(FUT, _frame(), now_ms=3) is False           # heartbeat: same vtt/ltp/ltq/ltt/b/a
    assert b.on_frame(FUT, _frame(vtt=1023815), now_ms=4) is True


def test_on_frame_never_touches_disk(monkeypatch):
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    def boom(*a, **k):
        raise AssertionError("on_frame opened a file")
    monkeypatch.setattr(builtins, "open", boom)
    assert b.on_frame(FUT, _frame(), now_ms=5) is True


def test_flush_writes_one_line_per_row_and_reports_book_from(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    b.on_frame(FUT, _frame(), now_ms=1787200010600)
    b.on_frame(FUT, _frame(vtt=1023815), now_ms=1787200010900)
    out = b.flush()
    assert [idx for idx, _ in out] == ["NIFTY", "NIFTY"] and b.written == 2
    rows = list(book_log.read_rows("2026-09-21", "NIFTY"))
    assert [r["t"] for r in rows] == [1787200010600, 1787200010900]
    assert b.book_from["NIFTY"] == "09:56:50"          # IST, the machine clock (server._coverage)
    assert b.flush() == []


def test_flush_after_a_restart_refuses_rows_at_or_before_the_files_last_t(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    p = book_log.day_path("2026-09-21", "NIFTY")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": 100, "vtt": 1}) + "\n" + json.dumps({"t": 200, "vtt": 2}) + "\n")
    assert book_log.last_t(p) == 200 and book_log.first_t(p) == 100
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    b.on_frame(FUT, _frame(), now_ms=200)                     # a replayed frame from before the restart
    b.on_frame(FUT, _frame(vtt=1023815), now_ms=201)
    out = b.flush()
    assert [r["t"] for _, r in out] == [201]
    assert [r["t"] for r in book_log.read_rows("2026-09-21", "NIFTY")] == [100, 200, 201]


def test_overflow_is_counted_not_raised(monkeypatch):
    monkeypatch.setattr(book_log, "MAXLEN", 2)
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    for i in range(4):
        b.on_frame(FUT, _frame(vtt=1023750 + 65 * i), now_ms=i)
    assert b.dropped == 2


def test_a_torn_last_line_is_skipped_by_the_reader_and_by_last_t(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    p = book_log.day_path("2026-09-21", "NIFTY")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": 100}) + "\n" + '{"t": 2')
    assert [r["t"] for r in book_log.read_rows("2026-09-21", "NIFTY")] == [100]
    assert book_log.last_t(p) == 100


def test_every_test_runs_with_the_book_record_in_a_temp_dir():
    assert os.path.isabs(book_log.DIR) and "book" in book_log.DIR       # the conftest redirect
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest test_book_log.py -q`
Expected: `ModuleNotFoundError: No module named 'book_log'`

- [ ] **Step 3: Write `book_log.py`**

```python
# tapemap/book_log.py
"""book_log.py -- THE BOOK RECORD. data/book/book_<idx>_<day>.jsonl.

WHAT IT IS. Every decoded frame of each index future, one compact line per
frame THAT CHANGED, taken at the socket's decode step (upstox_feed._absorb via
`on_frame`) and never at the 0.5 s poll: `_latest` is last-value-wins, so a
record built off `snapshot()` would silently miss every frame between polls
(spec 2026-09-20-upstox-tape §B, §J.1).

THE ROW.  {"t": arrival ms, "cts": feed currentTs, "ltt": ms, "ltp", "ltq",
           "vtt", "oi", "tbq", "tsq", "b": [[p, q]..best first], "a": [[p, q]..]}
Quantities are exchange units (multiples of the lot -- sweep.py measured it);
`b`/`a` hold however many levels arrived, so len(b) measures the entitlement.

NEVER ON THE FEED THREAD. `on_frame` appends to a bounded deque and returns;
`flush` (the senses loop, once a pass) writes. Overflow is COUNTED on
`dropped` and reported by /api/health, never raised.

CHANGE-ONLY (frame_log.append_if_changed's rule): an identical consecutive
frame is a heartbeat; the first differing frame carries the change.

RESTART-SAFE: rows at or before the file's last `t` are refused, so a replayed
frame cannot duplicate the morning. Nothing before process start can be
reconstructed -- there is no REST for historical depth -- and `book_from`
says where the record starts (the anytime-start rule, honestly).

FAIL-SOFT, opened per call, "a" mode (senses.py:_append).
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from typing import Dict, Iterator, List, Optional, Tuple

import upstox_adapter

DIR = os.path.join("data", "book")
MAXLEN = 20_000
failed = 0


def day_path(day: str, idx: str) -> str:
    return os.path.join(DIR, f"book_{idx}_{day}.jsonl")


def row_of(feed, cts=None, now_ms=None) -> Optional[dict]:
    """One decoded frame -> the compact row, or None when it carries no book."""
    core = upstox_adapter._core(feed)
    lad = upstox_adapter.depth_ladder(feed)
    if not core or not lad:
        return None
    n = upstox_adapter._num
    ltpc = core.get("ltpc") or {}

    def _int(x):
        v = n(x)
        return None if v is None else int(v)

    return {"t": int(now_ms if now_ms is not None else time.time() * 1000),
            "cts": _int(cts), "ltt": _int(ltpc.get("ltt")), "ltp": n(ltpc.get("ltp")),
            "ltq": _int(ltpc.get("ltq")), "vtt": _int(core.get("vtt")), "oi": _int(core.get("oi")),
            "tbq": _int(lad.get("tbq")), "tsq": _int(lad.get("tsq")),
            "b": [[l["price"], l["qty"]] for l in lad["bid"]],
            "a": [[l["price"], l["qty"]] for l in lad["ask"]]}


def _sig(row: dict) -> tuple:
    return (row["vtt"], row["ltp"], row["ltq"], row["ltt"],
            tuple(map(tuple, row["b"])), tuple(map(tuple, row["a"])))


def _t_of(line) -> Optional[int]:
    try:
        t = json.loads(line).get("t")
        return int(t) if isinstance(t, (int, float)) and not isinstance(t, bool) else None
    except (ValueError, AttributeError, TypeError):
        return None


def last_t(path: str) -> int:
    """The file's last row's `t`, read from the tail; 0 when there is no file."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536))
            tail = f.read().splitlines()
    except OSError:
        return 0
    for line in reversed(tail):
        t = _t_of(line)
        if t is not None:
            return t
    return 0


def first_t(path: str) -> Optional[int]:
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                t = _t_of(line)
                if t is not None:
                    return t
    except OSError:
        pass
    return None


def read_rows(day: str, idx: str) -> Iterator[dict]:
    """Streamed, never json.load of the whole file; a torn line is skipped."""
    try:
        with open(day_path(day, idx), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict) and isinstance(row.get("t"), (int, float)):
                    yield row
    except OSError:
        return


def _hms(ms: int) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ms / 1000))


class Book:
    """The deque and the writer. One per process."""

    def __init__(self, day: Optional[str] = None):
        self.day = day
        self._lock = threading.Lock()
        self._q: deque = deque(maxlen=MAXLEN)
        self._watch: Dict[str, str] = {}          # key -> idx
        self._last_sig: Dict[str, tuple] = {}
        self._last_t: Dict[str, int] = {}         # idx -> last t written (or found in the file)
        self.dropped = 0
        self.written = 0
        self.book_from: Dict[str, str] = {}       # idx -> HH:MM:SS of the record's first row

    def watch(self, idx: str, key: Optional[str]) -> None:
        if key:
            self._watch[key] = idx

    def watched(self) -> set:
        """The indices with a watched key -- what ux_log has a ladder for."""
        return set(self._watch.values())

    def on_frame(self, key: str, feed, cts=None, now_ms=None) -> bool:
        """Feed thread. No disk, no lock beyond the deque's own."""
        idx = self._watch.get(key)
        if idx is None:
            return False
        row = row_of(feed, cts, now_ms)
        if row is None:
            return False
        sig = _sig(row)
        if self._last_sig.get(key) == sig:
            return False
        self._last_sig[key] = sig
        with self._lock:
            if len(self._q) == self._q.maxlen:
                self.dropped += 1
            self._q.append((idx, row))
        return True

    def flush(self, day: Optional[str] = None) -> List[Tuple[str, dict]]:
        """Senses loop. Writes what the deque holds; returns the rows written."""
        global failed
        with self._lock:
            rows = list(self._q)
            self._q.clear()
        if not rows:
            return []
        day = day or self.day or time.strftime("%Y-%m-%d")
        by: Dict[str, List[dict]] = {}
        for idx, row in rows:
            if idx not in self._last_t:
                p = day_path(day, idx)
                self._last_t[idx] = last_t(p)
                ft = first_t(p)
                if ft is not None:
                    self.book_from[idx] = _hms(ft)
            if row["t"] <= self._last_t[idx]:
                continue
            self._last_t[idx] = row["t"]
            self.book_from.setdefault(idx, _hms(row["t"]))
            by.setdefault(idx, []).append(row)
        out: List[Tuple[str, dict]] = []
        for idx, rs in by.items():
            p = day_path(day, idx)
            try:
                os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
                with open(p, "a", encoding="utf-8") as f:
                    f.write("".join(json.dumps(r) + "\n" for r in rs))
            except Exception:                  # never take the tape down
                failed += len(rs)
                continue
            self.written += len(rs)
            out.extend((idx, r) for r in rs)
        return out
```

Note: `MAXLEN` is read at `Book()` time (`deque(maxlen=MAXLEN)`), which is what the overflow test monkeypatches.

- [ ] **Step 4: Add the redirect to `conftest.py`**

Replace the file's imports and fixture so it reads:

```python
import pytest

import book_log
import tape_log


@pytest.fixture(autouse=True)
def _tape_record_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    # the book record (spec 2026-09-20 §B) is ~60 MB a day; the 2026-09-19 leak
    # must not recur with it. Same fixture, one more line.
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    yield
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
```

Keep the module docstring above the imports as it is.

- [ ] **Step 5: Run the tests**

Run: `python -m pytest test_book_log.py -q`
Expected: `9 passed`

- [ ] **Step 6: Bump the count and commit**

Run: `python -m pytest -q 2>&1 | tail -1` → read `N passed, 3 failed`; set `context/DEFERRED.md:22` to `**Test count is now <N+3>**` with the date 2026-09-20 and one clause naming this task.

```bash
git add book_log.py test_book_log.py conftest.py context/DEFERRED.md
git commit -m "book_log: the book record -- one compact row per changed frame, deque on the feed thread, disk on the loop

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `upstox_feed.on_frame` — the hook

**Files:**
- Modify: `upstox_feed.py:76–95` (`__init__`), `:179–200` (`_absorb`)
- Test: `test_upstox_feed.py` (append)

**Interfaces:**
- Produces: `UpstoxFeed.on_frame: Callable[[key, feed, current_ts], Any] | None`, an attribute assignable after construction (Task 3 assigns it from the senses loop once the chain source has built the feed — no constructor plumbing through `chain_live`).

- [ ] **Step 1: Write the failing tests** (append to `test_upstox_feed.py`)

```python
# --------------------------------------------------------------------------
# the on_frame hook (spec 2026-09-20-upstox-tape §B)
# --------------------------------------------------------------------------

def test_on_frame_fires_per_key_after_the_merge_with_the_feed_and_current_ts():
    f = _feed()
    seen = []
    def cb(key, feed, cts):
        seen.append((key, feed["firstLevelWithGreeks"]["ltpc"]["ltp"], cts, key in f.snapshot()))
    f.on_frame = cb
    f._absorb(response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011),
                        PE: greek_feed(164.50, 3740620, 0.1033, -0.5694, 0.0012)}))
    assert sorted(seen) == sorted([(CE, 114.10, 1785900000, True), (PE, 164.50, 1785900000, True)])


def test_a_raising_on_frame_is_recorded_and_the_mailbox_still_fills():
    f = _feed()
    def cb(key, feed, cts):
        raise RuntimeError("hook fault")
    f.on_frame = cb
    f._absorb(response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)}))
    assert CE in f.snapshot() and "hook fault" in f.last_error


def test_no_hook_means_no_change():
    f = _feed()
    assert f.on_frame is None
    f._absorb(response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)}))
    assert f.frames == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_upstox_feed.py -q -k on_frame`
Expected: 3 failed (`AttributeError: 'UpstoxFeed' object has no attribute 'on_frame'` on the third; the first two fail on their assertions).

- [ ] **Step 3: Implement**

In `__init__`, after `self.reconnects = 0`:

```python
        # THE BOOK RECORD'S HOOK (spec 2026-09-20-upstox-tape §B). Called on
        # this thread, once per key in each decoded frame, AFTER the merge and
        # OUTSIDE the lock, with (key, feed, currentTs). Assigned by the server
        # once the chain source has built the feed; None means no record.
        self.on_frame = None
```

At the end of `_absorb`, after the `with self._lock:` block:

```python
        if self.on_frame is not None:
            cts = resp.get("currentTs")
            for key, feed in feeds.items():
                try:
                    self.on_frame(key, feed, cts)
                except Exception as e:            # noqa: BLE001 -- a hook must never kill the reader
                    self.last_error = f"on_frame: {type(e).__name__}: {e}"
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_upstox_feed.py -q`
Expected: all pass (previous count + 3)

- [ ] **Step 5: Bump the count and commit**

```bash
git add upstox_feed.py test_upstox_feed.py context/DEFERRED.md
git commit -m "upstox_feed: on_frame -- one call per key per decoded frame, after the merge, never fatal

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Server wiring for the record — watch, hook, flush, coverage, isolation

**Files:**
- Modify: `server.py` — `_SENSES` literal (`:72–113`, add two keys), `_senses_loop` (the `if feed_ok:` block at `:786` and the post-lock section at `:842`), `_coverage()` (`:2468`), `_isolate_mock_writers()` (`:2261–2289`), imports (`:41–56`)
- Modify: `test_day_state.py:96–100` (pin list), `.gitignore` (after line 15)
- Test: `test_book_wiring.py`

**Interfaces:**
- Consumes: `book_log.Book` (Task 1), `UpstoxFeed.on_frame` (Task 2).
- Produces: `server._SENSES["book"]` (a `book_log.Book`), `server._SENSES["book_rows"]` (the list the last flush returned — Task 8's `ux_log` drains it), `_coverage()["book"] = {"from": {idx: "HH:MM:SS"}, "dropped": int, "written": int, "why": str | None}`.

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_book_wiring.py
"""The book record is wired into the senses loop and isolated for a mock run."""
import inspect

import book_log
import server


def test_the_senses_state_owns_one_book():
    assert isinstance(server._SENSES.get("book"), book_log.Book)
    assert server._SENSES.get("book_rows") == []


def test_coverage_names_the_book_record_with_the_three_sentences(monkeypatch):
    b = book_log.Book(day="2026-09-21")
    monkeypatch.setitem(server._SENSES, "book", b)
    c = server._coverage()["book"]
    assert c["from"] == {} and c["dropped"] == 0 and c["written"] == 0
    assert c["why"] == "no frame recorded yet this process -- feed not connected, or before the first drain"
    b.book_from["NIFTY"] = "09:15:03"
    b.written = 10
    assert server._coverage()["book"] == {"from": {"NIFTY": "09:15:03"}, "dropped": 0, "written": 10, "why": None}


def test_a_mock_run_cannot_write_into_the_live_book_record(monkeypatch):
    monkeypatch.setattr(book_log, "DIR", "data/book")
    server._isolate_mock_writers()
    assert book_log.DIR.replace("\\", "/") == "data/mock/book"


def test_the_loop_assigns_the_hook_watches_the_futures_and_flushes_outside_the_lock():
    """Source-pinned, the way test_day_state pins the isolation list: the four
    lines that make the record exist must be in the loop, in this order --
    hook, watch, flush -- and the flush must sit AFTER the lock block."""
    src = inspect.getsource(server._senses_loop)
    i_hook = src.index("feed.on_frame = _SENSES[\"book\"].on_frame")
    i_watch = src.index("_SENSES[\"book\"].watch(idx, r.get(\"fut_key\"))")
    i_flush = src.index("_SENSES[\"book_rows\"] = _SENSES[\"book\"].flush()")
    i_lock_end = src.index("# 5a/5b, OUTSIDE _SENSES_LOCK")
    assert i_hook < i_watch < i_lock_end < i_flush
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_book_wiring.py -q`
Expected: 4 failed (`KeyError: 'book'` / `AssertionError` / `ValueError: substring not found`)

- [ ] **Step 3: Implement**

`server.py` imports — after `import tape_log` (`:42`):

```python
import book_log
```

`_SENSES` literal — after the `"tape": {},` line (`:113`):

```python
           # THE BOOK RECORD (spec 2026-09-20-upstox-tape §B): the deque the
           # feed thread fills and the loop drains. `book_rows` is what the
           # last drain wrote, for ux_log to consume on the same pass.
           "book": book_log.Book(), "book_rows": [],
```

`_senses_loop`, inside `if feed_ok:` at `:786`, as the FIRST statement of the block (before the `for idx, r in ...` loop):

```python
                if feed_ok:
                    # The record's hook: assigned once the chain source has a
                    # feed, re-assigned harmlessly on every pass (an attribute
                    # store), so a reconnect that rebuilds the feed re-hooks.
                    if getattr(feed, "on_frame", None) is None:
                        feed.on_frame = _SENSES["book"].on_frame
                    for idx, r in (getattr(src, "resolved", None) or {}).items():
                        # The future's key is watched for the book record; a
                        # contract roll changes fut_key and this re-watches it.
                        _SENSES["book"].watch(idx, r.get("fut_key"))
```

(The existing loop body continues unchanged after the `watch` line.)

`_senses_loop`, at the post-lock section — immediately AFTER the comment block that begins `# 5a/5b, OUTSIDE _SENSES_LOCK` (`:842`) and BEFORE the `if vpin_due:` block:

```python
            # THE BOOK RECORD'S DRAIN, outside the lock with the other writers.
            # One call a pass: the feed thread's deque -> data/book/, and the
            # same rows handed on for the ladder (ux_log, Task 8) below.
            try:
                _SENSES["book_rows"] = _SENSES["book"].flush()
            except Exception:                   # a disk fault costs the rows, never the tape
                _SENSES["book_rows"] = []
```

`_coverage()` — add one key to the returned dict, after `"late_min": gap,`:

```python
        # THE BOOK RECORD (spec 2026-09-20 §B): where the socket record starts
        # today, per index, and what the deque dropped. Rule 6: an empty map
        # gets its sentence.
        "book": _book_coverage(),
```

and a helper directly above `_coverage`:

```python
def _book_coverage():
    b = _SENSES.get("book")
    if b is None:
        return {"from": {}, "dropped": 0, "written": 0, "why": "no book writer in this process"}
    frm = dict(b.book_from)
    return {"from": frm, "dropped": b.dropped, "written": b.written,
            "why": None if frm else
            "no frame recorded yet this process -- feed not connected, or before the first drain"}
```

`_isolate_mock_writers()` — after `tape_log.DIR = os.path.join(mock, "tape")`:

```python
    book_log.DIR = os.path.join(mock, "book")
```

`test_day_state.py:96–100` — add `"book_log.DIR"` to the tuple of names.

`.gitignore` — after the `data/tape/` line:

```
# the book record (book_log.py): every changed frame of each index future off
# the Upstox socket, ~60 MB/day [I, measured day one], not refetchable.
data/book/
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_book_wiring.py test_day_state.py test_senses_api.py -q`
Expected: all pass

- [ ] **Step 5: Bump the count and commit**

```bash
git add server.py test_book_wiring.py test_day_state.py .gitignore context/DEFERRED.md
git commit -m "server: the book record wired -- hook assigned, futures watched, deque drained outside the lock, coverage says where it starts

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `prints.py` carries the unknown side

**Files:**
- Modify: `prints.py:33–49` (`rebin`), `:102–110` (`profile`), `:78–101` (`bar_flags` — no change, pinned)
- Test: `test_prints.py` (append)

**Interfaces:**
- Produces: `rebin` rows gain `"u"` (sum); `profile` volume-at-price is `b + s + u`. `imbalances` and `bar_flags` ignore `u`. GoCharting rows (no `u`) behave byte-identically — the parity tests pin it.

- [ ] **Step 1: Write the failing tests** (append to `test_prints.py`)

```python
# --- the unknown side, u (spec 2026-09-20-upstox-tape §C) -------------------

def test_rebin_sums_u_and_defaults_it_to_zero():
    rows = prints.rebin([{"p": 100.0, "b": 1, "s": 2, "u": 3, "bt": 1, "st": 1},
                         {"p": 101.0, "b": 1, "s": 0, "bt": 1, "st": 0}], 5, 0)
    assert rows == [{"p": 100.0, "b": 2, "s": 2, "u": 3, "bt": 2, "st": 1}]


def test_profile_counts_u_as_volume_at_price():
    bars = [{"t": 1, "ladder": [{"p": 100.0, "b": 1, "s": 1, "u": 10}, {"p": 101.0, "b": 5, "s": 0}]}]
    pr = prints.profile(bars)
    assert pr["poc"] == 100.0 and pr["total"] == 17


def test_imbalances_and_bar_flags_ignore_u():
    bar = {"vol": 20, "ladder": [{"p": 100.0, "b": 0, "s": 1, "u": 50, "bt": 0, "st": 1},
                                 {"p": 105.0, "b": 6, "s": 0, "u": 50, "bt": 3, "st": 0}]}
    f = prints.bar_flags(bar, 5, 0)
    assert f["poc"] == 105.0                 # b+s only: 6 beats 1; u is not a side
    flags, _ = prints.imbalances(prints.rebin(bar["ladder"], 5, 0))
    assert flags == [0, 1]                   # 6 >= 3 * max(1, 1): a buy flag at 105, u never enters
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_prints.py -q -k "u_and or counts_u or ignore_u"`
Expected: 2 failed (the rebin row lacks `u`; profile total is 7), 1 passed (`ignore_u` already holds).

- [ ] **Step 3: Implement**

`rebin` — the bucket gains `"u": 0` and the loop sums it:

```python
        if q is None:
            q = {"p": p, "b": 0, "s": 0, "u": 0, "bt": 0, "st": 0}
            m[p] = q
        q["b"] += r.get("b") or 0
        q["s"] += r.get("s") or 0
        q["u"] += r.get("u") or 0
        q["bt"] += r.get("bt") or 0
        q["st"] += r.get("st") or 0
```

`profile` — the accumulator line becomes:

```python
            m[p] = m.get(p, 0) + (r.get("b") or 0) + (r.get("s") or 0) + (r.get("u") or 0)
```

`bar_flags` — unchanged: its `v = r["b"] + r["s"]` is the rule (a POC is a traded price with a side; `u` is volume without one, and the spec keeps the two flags side-blind). Add one comment above that line:

```python
        # b + s, never u: the unknown side (spec 2026-09-20 §C) is volume the
        # ladder cannot place on a side, and a flag is a side's claim.
```

- [ ] **Step 4: Run the whole prints suite — the parity fixtures must not move**

Run: `python -m pytest test_prints.py -q`
Expected: all pass, including `test_parity_per_bar_rows_flags_poc_and_unfinished_match_the_extension` for both fixtures (the fixture ladders carry no `u`, so `rebin` rows now carry `u: 0` — if the parity test compares whole row dicts, update the fixture-loading comparison to `{k: v for k, v in row.items() if k != "u"}` and say why in a comment; do NOT regenerate the fixtures).

- [ ] **Step 5: Bump the count and commit**

```bash
git add prints.py test_prints.py context/DEFERRED.md
git commit -m "prints: the unknown side rides the ladder -- rebin sums u, profile counts it, flags stay side-blind

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `upstox_instruments` — lot and tick in the slice

**Files:**
- Modify: `upstox_instruments.py:91–102` (`_slice`), add `lot_tick(name, rows=None)` after `fut_key` (`:177–189`)
- Test: `test_upstox_instruments.py` (append)

**Interfaces:**
- Produces: slice rows gain `"lot_size"` and `"tick_size"` (the dump's fields, `None` when absent); `lot_tick(name="NIFTY", rows=None) -> (lot: int | None, tick: float | None)` read off the nearest live future's row. A cached slice written before this task lacks the fields and yields `(None, None)` until the daily refresh — `ladder.infer_lot`/`infer_tick` (Task 7) cover that day.

- [ ] **Step 1: Write the failing tests** (append to `test_upstox_instruments.py`; use the module's existing `cached` fixture and the row helpers at the top of the file, adding `"lot_size": 65, "tick_size": 0.05` to the FUT row the fixture builds)

```python
def test_the_slice_keeps_lot_and_tick_from_the_dump(cached, monkeypatch):
    rows = upstox_instruments.load("NIFTY")
    fut = next(r for r in rows if r["instrument_type"] in upstox_instruments.FUT_TYPES)
    assert fut["lot_size"] == 65 and fut["tick_size"] == 0.05


def test_lot_tick_reads_the_nearest_future_and_is_none_none_on_an_old_slice(cached, monkeypatch):
    assert upstox_instruments.lot_tick("NIFTY") == (65, 0.05)
    old = [{k: v for k, v in r.items() if k not in ("lot_size", "tick_size")}
           for r in upstox_instruments.load("NIFTY")]
    assert upstox_instruments.lot_tick("NIFTY", rows=old) == (None, None)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_upstox_instruments.py -q -k "lot"`
Expected: 2 failed (`KeyError: 'lot_size'`, `AttributeError: lot_tick`)

- [ ] **Step 3: Implement**

`_slice` returns two more fields:

```python
    return [{"instrument_key": x.get("instrument_key"),
             "instrument_type": (x.get("instrument_type") or "").upper(),
             "strike_price": x.get("strike_price"),
             "expiry": x.get("expiry"),
             "trading_symbol": x.get("trading_symbol"),
             # spec 2026-09-20 §B: the ladder divides by the lot and stops at
             # half a tick; both come from the dump, never guessed here.
             "lot_size": x.get("lot_size"),
             "tick_size": x.get("tick_size")}
```

After `fut_key`:

```python
def lot_tick(name="NIFTY", rows=None):
    """(lot, tick) of the nearest live future, or (None, None) when the cached
    slice predates the two fields -- the caller (ladder.py) then infers and
    says so on the row (`lot_src`, `tick_src`)."""
    rows = rows if rows is not None else load(name)
    futs = sorted((x for x in rows if x["instrument_type"] in FUT_TYPES),
                  key=lambda x: x.get("expiry") or 0)
    if not futs:
        return None, None
    f = futs[0]
    lot, tick = f.get("lot_size"), f.get("tick_size")
    try:
        lot = int(lot) if lot else None
    except (TypeError, ValueError):
        lot = None
    try:
        tick = float(tick) if tick else None
    except (TypeError, ValueError):
        tick = None
    return lot, tick
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_upstox_instruments.py -q`
Expected: all pass

- [ ] **Step 5: Bump the count and commit**

```bash
git add upstox_instruments.py test_upstox_instruments.py context/DEFERRED.md
git commit -m "upstox_instruments: lot_size and tick_size ride the cached slice; lot_tick reads the nearest future

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: `ladder.attribute` — one pair of frames, volume conserved

**Files:**
- Create: `ladder.py` (the pairwise half; Task 7 adds the `Ladder` class to the same file)
- Test: `test_ladder.py`

**Interfaces:**
- Produces: `HALF_TICK = 0.55`, `side_of(ltp, prev) -> int` (+1 buy, −1 sell, 0 unknown), `min_gap(row) -> float | None`, `attribute(prev, cur, tick) -> dict` with keys `kind` (`"skip" | "reset" | "quiet" | "exact" | "recon" | "unknown"`), `V` (units), `fills` (list of `{"side": int, "p": float, "q": int, "hidden": bool}`, primary side first), `hidden` (units), `unknown` (units). Rows are `book_log` rows (`b`/`a` as `[[p, q], ...]` best first).

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_ladder.py
"""The reconstruction, one pair of frames at a time (spec 2026-09-20 §C)."""
import ladder

T0 = 1789098300000            # 2026-09-11 09:15:00 IST, the bar-open epoch spec 1 uses


def R(t, vtt, ltp, ltq, b, a, ltt=None, oi=None):
    return {"t": t, "cts": None, "ltt": t if ltt is None else ltt, "ltp": ltp, "ltq": ltq,
            "vtt": vtt, "oi": oi, "tbq": None, "tsq": None, "b": b, "a": a}


def test_side_is_judged_against_the_previous_touch():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    assert ladder.side_of(100.05, prev) == 1          # at or through the ask: a buy
    assert ladder.side_of(100.00, prev) == -1         # at or through the bid: a sell
    assert ladder.side_of(100.04, prev) == 1          # inside, above mid
    assert ladder.side_of(100.01, prev) == -1         # inside, below mid
    assert ladder.side_of(100.025, prev) == 0         # exactly mid: unknown


def test_exact_case_one_trade_at_ltp_of_size_ltq():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]])
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "exact" and r["V"] == 65 and r["hidden"] == 0 and r["unknown"] == 0
    assert r["fills"] == [{"side": 1, "p": 100.05, "q": 65, "hidden": False}]


def test_reconstruction_marches_the_attacked_side_best_first():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65], [100.10, 65], [100.15, 65]])
    cur = R(2, 1130, 100.10, 65, [[100.00, 65]], [[100.15, 65]])      # V = 130 != ltq: two prints
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["hidden"] == 0
    assert r["fills"] == [{"side": 1, "p": 100.05, "q": 65, "hidden": False},
                          {"side": 1, "p": 100.10, "q": 65, "hidden": False}]


def test_the_march_stops_past_the_last_print_by_half_a_tick():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65], [100.10, 65]])
    cur = R(2, 1130, 100.05, 65, [[100.00, 65]], [])          # both asks gone, but ltp is 100.05
    r = ladder.attribute(prev, cur, 0.05)
    assert r["fills"][0] == {"side": 1, "p": 100.05, "q": 65, "hidden": False}
    assert r["fills"][1] == {"side": 1, "p": 100.05, "q": 65, "hidden": True}   # 100.10 is past ltp: not eaten
    assert r["hidden"] == 65


def test_residual_is_booked_hidden_at_ltp_when_the_book_refilled():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1130, 100.05, 65, [[100.00, 65]], [[100.05, 65]])      # V = 130, nothing visibly eaten
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["fills"] == [{"side": 1, "p": 100.05, "q": 130, "hidden": True}]
    assert r["hidden"] == 130


def test_the_other_side_is_only_eaten_up_to_the_last_print():
    """A tick away from ltp on the other side is refused and lands hidden: the
    method's floor (Order Flow Lab marches each side toward cur.ltp)."""
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1130, 100.05, 65, [[99.95, 65]], [[100.10, 65]])
    r = ladder.attribute(prev, cur, 0.05)
    assert [f["p"] for f in r["fills"]] == [100.05, 100.05] and r["fills"][1]["hidden"] and r["hidden"] == 65


def test_a_stale_ltq_larger_than_v_is_not_trusted():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1065, 100.05, 130, [[100.00, 65]], [[100.10, 65]])     # V = 65 < ltq = 130
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["fills"] == [{"side": 1, "p": 100.05, "q": 65, "hidden": False}]


def test_a_print_at_mid_with_no_side_is_unknown_never_split():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1065, 100.025, 65, [[100.00, 65]], [[100.05, 65]])
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "exact" and r["unknown"] == 65 and r["fills"][0]["side"] == 0


def test_a_tie_in_the_reconstruction_falls_to_the_side_that_thinned_then_to_unknown():
    prev = R(1, 1000, 100.0, 65, [[100.00, 130]], [[100.05, 130]])
    cur = R(2, 1130, 100.025, 65, [[100.00, 130]], [[100.05, 0]])     # asks thinned: buys
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["fills"][0]["side"] == 1
    cur2 = R(2, 1130, 100.025, 65, [[100.00, 130]], [[100.05, 130]])  # nothing thinned: unknown
    r2 = ladder.attribute(prev, cur2, 0.05)
    assert r2["kind"] == "unknown" and r2["unknown"] == 130 and r2["fills"] == [{"side": 0, "p": 100.025, "q": 130, "hidden": False}]


def test_a_vtt_reset_and_a_quiet_frame_attribute_nothing():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    assert ladder.attribute(prev, R(2, 900, 100.0, 65, [[100.00, 65]], [[100.05, 65]]), 0.05)["kind"] == "reset"
    assert ladder.attribute(prev, R(2, 1000, 100.0, 65, [[99.95, 65]], [[100.05, 65]]), 0.05)["kind"] == "quiet"
    assert ladder.attribute(None, prev, 0.05)["kind"] == "skip"


def test_min_gap_is_the_smallest_adjacent_price_step_on_either_side():
    row = R(1, 1000, 100.0, 65, [[100.00, 65], [99.90, 65]], [[100.05, 65], [100.10, 65]])
    assert ladder.min_gap(row) == 0.05
    assert ladder.min_gap(R(1, 1000, 100.0, 65, [[100.0, 65]], [[100.05, 65]])) == 0.05   # across the spread
    assert ladder.min_gap(R(1, 1000, 100.0, 65, [], [])) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_ladder.py -q`
Expected: `ModuleNotFoundError: No module named 'ladder'`

- [ ] **Step 3: Write the pairwise half of `ladder.py`**

```python
# tapemap/ladder.py
"""ladder.py -- a 5-minute per-price ladder from consecutive book snapshots.

THE METHOD (spec 2026-09-20-upstox-tape §C; Order Flow Lab's reconstruct(),
orderflow.html:1478-1511, with this repo's side rule). Per consecutive pair
(prev, cur), V = cur.vtt - prev.vtt in exchange units:

  V < 0        the feed reset: skipped, counted.
  V == 0       nothing traded: nothing attributed (depth_pull owns the book).
  V == ltq     EXACT: one trade of V at cur.ltp. Price/size [M]; side [I] by the
               touch it hit, judged against prev's book (per-trade quote rule --
               NOT the interval rule sweep.py killed: each print against the
               touch that took it, not an interval against its last print).
               A print exactly at mid has no side and is booked `u`.
  otherwise    RECONSTRUCTION: march the attacked side best price first, each
               level's displayed decrease eaten up to what is left of V, stopping
               past cur.ltp by more than HALF_TICK ticks; then the other side the
               same way; the remainder is HIDDEN, booked at cur.ltp on the
               primary side. Volume is conserved: every unit lands somewhere,
               and the counters say how much by proof and how much by residual.

WHAT IS NOT DONE HERE. No half-and-half split of an unknown side (spec §J.11).
No lot division until a bar closes (Task 7). No I/O, no clock.

Pure, stdlib only. Every side is [I]; vol, OHLC and oi are [M].
"""
from __future__ import annotations

from collections import Counter
from math import gcd
from typing import Dict, List, Optional, Tuple

HALF_TICK = 0.55          # Order Flow Lab's tick*0.55: past this, the trade could not have reached the level
INTERVAL_S = 300


def side_of(ltp: float, prev: dict) -> int:
    """+1 buy / -1 sell / 0 unknown, judged against `prev`'s touch."""
    bb = prev["b"][0][0] if prev.get("b") else None
    ba = prev["a"][0][0] if prev.get("a") else None
    if ba is not None and ltp >= ba:
        return 1
    if bb is not None and ltp <= bb:
        return -1
    if bb is None or ba is None:
        return 0
    mid = (bb + ba) / 2
    return 1 if ltp > mid else -1 if ltp < mid else 0


def min_gap(row: dict) -> Optional[float]:
    """The smallest step between adjacent quoted prices, both sides and across
    the spread -- the tick fallback while no dump value is known."""
    ps = sorted({p for p, _ in (row.get("b") or [])} | {p for p, _ in (row.get("a") or [])})
    gaps = [round(b - a, 4) for a, b in zip(ps, ps[1:]) if b - a > 0]
    return min(gaps) if gaps else None


def _march(levels: List[list], cur_at: Dict[float, int], side: int, ltp: float,
           tick: float, remaining: int) -> Tuple[List[dict], int]:
    fills: List[dict] = []
    lim = tick * HALF_TICK
    for p, q0 in levels:
        if remaining <= 0:
            break
        if (p > ltp + lim) if side == 1 else (p < ltp - lim):
            break                                    # past the last print: unreachable
        eaten = min(max(0, int(q0) - int(cur_at.get(p, 0))), remaining)
        if eaten > 0:
            fills.append({"side": side, "p": p, "q": eaten, "hidden": False})
            remaining -= eaten
    return fills, remaining


def _empty(kind: str, V: int = 0) -> dict:
    return {"kind": kind, "V": V, "fills": [], "hidden": 0, "unknown": 0}


def attribute(prev: Optional[dict], cur: dict, tick: float) -> dict:
    """One pair of book rows -> what traded, where, on which side."""
    if not prev or prev.get("vtt") is None or cur.get("vtt") is None:
        return _empty("skip")
    V = int(cur["vtt"]) - int(prev["vtt"])
    if V < 0:
        return _empty("reset", V)
    if V == 0:
        return _empty("quiet")
    ltp = cur.get("ltp")
    if ltp is None:
        ltp = prev.get("ltp")
    if ltp is None:
        return {"kind": "unknown", "V": V, "fills": [], "hidden": 0, "unknown": V}
    side = side_of(ltp, prev)
    ltq = cur.get("ltq")
    if ltq and V == int(ltq):
        return {"kind": "exact", "V": V, "hidden": 0, "unknown": V if side == 0 else 0,
                "fills": [{"side": side, "p": ltp, "q": V, "hidden": False}]}
    cur_at: Dict[float, int] = {p: int(q) for p, q in (cur.get("b") or [])}
    cur_at.update({p: int(q) for p, q in (cur.get("a") or [])})
    primary = side
    if primary == 0:
        db = sum(q for _, q in prev.get("b") or []) - sum(q for _, q in cur.get("b") or [])
        da = sum(q for _, q in prev.get("a") or []) - sum(q for _, q in cur.get("a") or [])
        primary = 1 if da > db else -1 if db > da else 0
    if primary == 0:
        return {"kind": "unknown", "V": V, "hidden": 0, "unknown": V,
                "fills": [{"side": 0, "p": ltp, "q": V, "hidden": False}]}
    first = prev.get("a") or [] if primary == 1 else prev.get("b") or []
    second = prev.get("b") or [] if primary == 1 else prev.get("a") or []
    fills, rem = _march(first, cur_at, primary, ltp, tick, V)
    more, rem = _march(second, cur_at, -primary, ltp, tick, rem)
    fills += more
    hidden = 0
    if rem > 0:
        fills.append({"side": primary, "p": ltp, "q": rem, "hidden": True})
        hidden = rem
    return {"kind": "recon", "V": V, "fills": fills, "hidden": hidden, "unknown": 0}
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_ladder.py -q`
Expected: `11 passed`

- [ ] **Step 5: Bump the count and commit**

```bash
git add ladder.py test_ladder.py context/DEFERRED.md
git commit -m "ladder: attribute -- exact case by the per-trade touch, price-priority march otherwise, residual hidden, unknown never split

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: `ladder.Ladder` — bins, bars, fills, counters, lot and tick

**Files:**
- Modify: `ladder.py` (append)
- Test: `test_ladder.py` (append)

**Interfaces:**
- Consumes: `attribute`, `min_gap` (Task 6).
- Produces: `bin_of(t_ms, interval_s=300) -> int`, `hms_ist(ms) -> str`, `class Ladder(lot=None, tick=None, interval_s=300, idx="", day="")` with `step(row) -> (closed_bar | None, fills: list[dict])` where each fill is `{"ltt": int, "side": int, "p": float, "q": int, "hidden": bool}` (units), `close_open() -> bar | None`, and the bar dict exactly as spec §C lists it plus `lot_why`, `tick`, `tick_src`. Consumed by `ux_log` (Task 8), `runs` (Task 10), `impact` (Task 11).

- [ ] **Step 1: Write the failing tests** (append to `test_ladder.py`)

```python
# --- bars ---------------------------------------------------------------------

def test_bin_of_is_the_five_minute_open_in_epoch_ms():
    assert ladder.bin_of(T0) == T0 and ladder.bin_of(T0 + 299_999) == T0 and ladder.bin_of(T0 + 300_000) == T0 + 300_000
    assert ladder.hms_ist(T0) == "09:15:00"


def _four_frames():
    return [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 2000, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),           # exact buy at 100.05
            R(T0 + 3000, 1195, 100.05, 65, [[100.00, 65]], [[100.10, 65]], oi=500),   # recon: 65 eaten + 65 hidden
            R(T0 + 300_500, 1195, 100.05, 65, [[100.00, 65]], [[100.10, 65]])]        # next bin, quiet: closes bar 0


def test_a_bar_closes_when_a_frame_lands_in_the_next_bin_in_lots_with_counters():
    L = ladder.Ladder(lot=65, tick=0.05, idx="NIFTY", day="2026-09-11")
    out = [L.step(f) for f in _four_frames()]
    assert [b for b, _ in out[:3]] == [None, None, None]
    bar, fills = out[3]
    assert fills == [] and bar["t"] == T0 and bar["src"] == "ux" and bar["idx"] == "NIFTY" and bar["day"] == "2026-09-11"
    assert bar["o"] == 100.05 and bar["h"] == 100.05 and bar["l"] == 100.05 and bar["c"] == 100.05 and bar["oi"] == 500
    assert bar["vol"] == 3 and bar["buy"] == 3 and bar["sell"] == 0 and bar["unknown"] == 0 and bar["delta"] == 3
    assert bar["ladder"] == [{"p": 100.05, "b": 3, "s": 0, "u": 0, "bt": 3, "st": 0}]
    assert bar["frames"] == 3 and bar["exact"] == 1 and bar["reconstructed"] == 1 and bar["hidden"] == 1
    assert bar["vtt_resets"] == 0 and bar["lot_mismatch"] == 0 and bar["levels_seen"] == 2
    assert bar["lot"] == 65 and bar["lot_src"] == "given" and bar["tick"] == 0.05 and bar["tick_src"] == "given"
    assert bar["partial"] is False and bar["partial_why"] is None
    assert bar["rowSize"] is None and bar["rowAnchor"] == 0 and bar["fromTicks"] is True


def test_fill_events_carry_ltt_and_side_primary_first():
    L = ladder.Ladder(lot=65, tick=0.05)
    fs = [f for fr in _four_frames() for f in L.step(fr)[1]]
    assert fs[0] == {"ltt": T0 + 2000, "side": 1, "p": 100.05, "q": 65, "hidden": False}
    assert fs[1]["ltt"] == T0 + 3000 and fs[2]["hidden"] is True


def test_trading_frames_bin_by_ltt_not_arrival():
    L = ladder.Ladder(lot=65, tick=0.05)
    fr = _four_frames()
    late = R(T0 + 300_200, 1260, 100.05, 65, [[100.00, 65]], [[100.10, 65]], ltt=T0 + 299_000)   # arrived late, traded in bin 0
    for f in fr[:3]:
        L.step(f)
    assert L.step(late)[0] is None                    # still bin 0: no close
    bar, _ = L.step(fr[3])
    assert bar["vol"] == 4 and bar["exact"] == 2


def test_a_lot_mismatch_is_counted_and_kept_fractional():
    L = ladder.Ladder(lot=65, tick=0.05)
    L.step(R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    L.step(R(T0 + 2000, 1100, 100.05, 100, [[100.00, 65]], [[100.05, 65]]))
    bar = L.close_open()
    assert bar["lot_mismatch"] == 1 and abs(bar["vol"] - 100 / 65) < 1e-9


def test_lot_and_tick_are_inferred_and_say_so_when_not_given():
    L = ladder.Ladder()
    for f in _four_frames():
        bar, _ = L.step(f)
    assert bar["lot"] == 65 and bar["lot_src"] == "gcd" and bar["lot_why"] is None
    assert bar["tick"] == 0.05 and bar["tick_src"] == "inferred"


def test_no_trade_yet_means_no_lot_and_a_sentence():
    L = ladder.Ladder()
    L.step(R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    bar = L.close_open()
    assert bar["lot"] is None and bar["lot_src"] is None and bar["lot_why"] == "no traded volume yet to infer a lot from"
    assert bar["vol"] == 0 and bar["ladder"] == []


def test_the_first_bar_after_a_late_start_is_partial_with_the_record_start():
    L = ladder.Ladder(lot=65, tick=0.05)
    L.step(R(T0 + 120_000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    bar, _ = L.step(R(T0 + 300_500, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    assert bar["partial"] is True and bar["partial_why"] == "record starts at 09:17:00, bar opened at 09:15:00"


def test_a_vtt_reset_inside_the_bar_marks_it_partial():
    L = ladder.Ladder(lot=65, tick=0.05)
    L.step(R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    L.step(R(T0 + 2000, 900, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    bar = L.close_open()
    assert bar["vtt_resets"] == 1 and bar["partial"] is True and bar["partial_why"] == "vtt reset 1 time(s) inside the bar"


def test_close_open_is_none_before_any_frame():
    assert ladder.Ladder().close_open() is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_ladder.py -q -k "bar or bin or fill or lot or partial or reset_inside or close_open"`
Expected: failures with `AttributeError: module 'ladder' has no attribute 'bin_of'` / `'Ladder'`

- [ ] **Step 3: Append to `ladder.py`**

```python
IST_MS = 19_800_000


def bin_of(t_ms: int, interval_s: int = INTERVAL_S) -> int:
    """The bar-open epoch ms holding t_ms. IST is +05:30, a multiple of five
    minutes, so 5- and 15-minute UTC boundaries ARE the IST boundaries -- no
    offset arithmetic, and byte-equal to spec 1's `t`."""
    w = interval_s * 1000
    return int(t_ms) // w * w


def hms_ist(ms: int) -> str:
    s = (int(ms) + IST_MS) // 1000 % 86400
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"


class Ladder:
    """Frames in, bars out. One per instrument per day."""

    def __init__(self, lot: Optional[int] = None, tick: Optional[float] = None,
                 interval_s: int = INTERVAL_S, idx: str = "", day: str = ""):
        self.lot, self.tick, self.interval_s, self.idx, self.day = lot, tick, interval_s, idx, day
        self.prev: Optional[dict] = None
        self.bin: Optional[int] = None
        self.acc: Optional[dict] = None
        self.first_ms: Optional[int] = None       # the record's first frame, for `partial`
        self._g = 0                               # running gcd of V, the lot fallback
        self._gaps: Counter = Counter()           # adjacent price steps seen, the tick fallback

    # ---- lot and tick ----------------------------------------------------
    def _tick_now(self, row: dict) -> float:
        if self.tick:
            return self.tick
        g = min_gap(row)
        if g:
            self._gaps[g] += 1
        common = self._gaps.most_common(1)
        return common[0][0] if common else (g or 0.05)

    def _resolve(self) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[float], Optional[str]]:
        if self.lot:
            lot, lot_src, lot_why = self.lot, "given", None
        elif self._g:
            lot, lot_src, lot_why = self._g, "gcd", None
        else:
            lot, lot_src, lot_why = None, None, "no traded volume yet to infer a lot from"
        if self.tick:
            tick, tick_src = self.tick, "given"
        elif self._gaps:
            tick, tick_src = self._gaps.most_common(1)[0][0], "inferred"
        else:
            tick, tick_src = None, None
        return lot, lot_src, lot_why, tick, tick_src

    # ---- the bar --------------------------------------------------------
    def _open(self, b: int) -> None:
        self.bin = b
        self.acc = {"t": b, "o": None, "h": None, "l": None, "c": None, "oi": None,
                    "vol": 0, "buy": 0, "sell": 0, "unknown": 0, "hidden": 0,
                    "lad": {}, "frames": 0, "exact": 0, "reconstructed": 0,
                    "vtt_resets": 0, "levels_seen": 0, "first_ms": None}

    def _close(self) -> Optional[dict]:
        a = self.acc
        if a is None:
            return None
        lot, lot_src, lot_why, tick, tick_src = self._resolve()
        div = lot or 1
        mismatch = 0
        rows = []
        for p in sorted(a["lad"]):
            b, s, u, bt, st = a["lad"][p]
            if lot:
                mismatch += sum(1 for q in (b, s, u) if q % lot)
            rows.append({"p": p, "b": b / div, "s": s / div, "u": u / div, "bt": bt, "st": st})
        why = None
        if a["vtt_resets"]:
            why = f"vtt reset {a['vtt_resets']} time(s) inside the bar"
        elif a["first_ms"] is not None and self.first_ms == a["first_ms"] and a["first_ms"] > a["t"] + 1000:
            why = f"record starts at {hms_ist(a['first_ms'])}, bar opened at {hms_ist(a['t'])}"
        bar = {"t": a["t"], "o": a["o"], "h": a["h"], "l": a["l"], "c": a["c"],
               "vol": a["vol"] / div, "buy": a["buy"] / div, "sell": a["sell"] / div,
               "unknown": a["unknown"] / div, "delta": (a["buy"] - a["sell"]) / div, "oi": a["oi"],
               "fromTicks": True, "ladder": rows, "rowSize": None, "rowAnchor": 0,
               "lot": lot, "lot_src": lot_src, "lot_why": lot_why, "tick": tick, "tick_src": tick_src,
               "frames": a["frames"], "exact": a["exact"], "reconstructed": a["reconstructed"],
               "hidden": a["hidden"] / div, "vtt_resets": a["vtt_resets"], "lot_mismatch": mismatch,
               "levels_seen": a["levels_seen"], "partial": why is not None, "partial_why": why,
               "src": "ux", "idx": self.idx, "day": self.day}
        self.acc = None
        self.bin = None
        return bar

    def close_open(self) -> Optional[dict]:
        """The bar still open, closed now -- a rebuild's last bin, never live."""
        return self._close()

    def step(self, row: dict) -> Tuple[Optional[dict], List[dict]]:
        """One book row. Returns (the bar this frame closed or None, its fills in units)."""
        tick = self._tick_now(row)
        res = attribute(self.prev, row, tick)
        traded = res["kind"] in ("exact", "recon", "unknown")
        t_bin = row.get("ltt") if traded and row.get("ltt") else row["t"]
        b = bin_of(t_bin, self.interval_s)
        closed = None
        if self.bin is None:
            self._open(b)
        elif b > self.bin:
            closed = self._close()
            self._open(b)
        a = self.acc
        if self.first_ms is None:
            self.first_ms = t_bin
        if a["first_ms"] is None:
            a["first_ms"] = t_bin
        a["frames"] += 1
        a["levels_seen"] = max(a["levels_seen"], len(row.get("b") or []) + len(row.get("a") or []))
        if row.get("oi") is not None:
            a["oi"] = row["oi"]
        if res["kind"] == "reset":
            a["vtt_resets"] += 1
        fills: List[dict] = []
        if traded:
            V = res["V"]
            self._g = gcd(self._g, V)
            a["vol"] += V
            a["hidden"] += res["hidden"]
            a["unknown"] += res["unknown"]
            a["exact"] += res["kind"] == "exact"
            a["reconstructed"] += res["kind"] == "recon"
            ltp = row.get("ltp")
            if ltp is not None:
                a["o"] = ltp if a["o"] is None else a["o"]
                a["h"] = ltp if a["h"] is None else max(a["h"], ltp)
                a["l"] = ltp if a["l"] is None else min(a["l"], ltp)
                a["c"] = ltp
            for f in res["fills"]:
                r = a["lad"].setdefault(f["p"], [0, 0, 0, 0, 0])
                if f["side"] == 1:
                    r[0] += f["q"]; r[3] += 1
                    a["buy"] += f["q"]
                elif f["side"] == -1:
                    r[1] += f["q"]; r[4] += 1
                    a["sell"] += f["q"]
                else:
                    r[2] += f["q"]
                fills.append({"ltt": t_bin, **f})
        self.prev = row
        return closed, fills
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_ladder.py -q`
Expected: `21 passed`

- [ ] **Step 5: Bump the count and commit**

```bash
git add ladder.py test_ladder.py context/DEFERRED.md
git commit -m "ladder: bars -- bin by ltt, lots at close, counters that say how the ladder was made, partial with its reason

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: `ux_log.py` — the third file in `data/tape/`

**Files:**
- Create: `ux_log.py`
- Modify: `conftest.py` (clear `ux_log._STATE` in the autouse fixture)
- Test: `test_ux_log.py`

**Interfaces:**
- Consumes: `ladder.Ladder` (Task 7), `book_log.read_rows` (Task 1), `tape_log.DIR` / `tape_log._read` (existing), `upstox_instruments.lot_tick` (Task 5).
- Produces: `ux_log.day_path(day, idx) -> str` (`<tape_log.DIR>/ux_<idx>_<day>.jsonl`), `read_bars(day, idx) -> list[dict]`, `state(idx, day, lot=None, tick=None) -> dict` (the per-index state: `{"ladder": Ladder, "bars": [...], "day": day, "fills": deque(maxlen=20000), "written": int}`), `on_frames(rows: list[tuple[str, dict]], day) -> list[tuple[str, dict, list[dict]]]` (each closed bar with its index and the fills of the frames that produced this pass), `rebuild(day, idx, lot=None, tick=None) -> int` (bars written), `forming(idx, day) -> dict | None`, `_STATE: dict`.

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_ux_log.py
"""The ux record: bars written once at bin close, rebuilt from the book on start."""
import json
import os

import book_log
import ladder
import tape_log
import ux_log
from test_ladder import R, T0


def _rows():
    return [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 2000, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 300_500, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 600_500, 1130, 100.00, 65, [[100.00, 65]], [[100.05, 65]])]


def test_on_frames_writes_each_closed_bar_once_and_returns_it_with_fills():
    out = ux_log.on_frames([("NIFTY", r) for r in _rows()], "2026-09-11", lot=65, tick=0.05)
    assert [(idx, b["t"]) for idx, b, _ in out] == [("NIFTY", T0), ("NIFTY", T0 + 300_000)]
    bars = ux_log.read_bars("2026-09-11", "NIFTY")
    assert [b["t"] for b in bars] == [T0, T0 + 300_000] and bars[0]["src"] == "ux" and bars[0]["vol"] == 1
    assert bars[1]["vol"] == 0 and bars[1]["ladder"] == []
    st = ux_log.state("NIFTY", "2026-09-11")
    assert [b["t"] for b in st["bars"]] == [T0, T0 + 300_000] and len(st["fills"]) == 2
    # the same rows again land nothing: write-once by t
    ux_log.on_frames([("NIFTY", r) for r in _rows()], "2026-09-11", lot=65, tick=0.05)
    assert len(ux_log.read_bars("2026-09-11", "NIFTY")) == 2


def test_forming_is_the_open_bar_and_none_before_any_frame():
    assert ux_log.forming("NIFTY", "2026-09-11") is None
    ux_log.on_frames([("NIFTY", r) for r in _rows()[:2]], "2026-09-11", lot=65, tick=0.05)
    f = ux_log.forming("NIFTY", "2026-09-11")
    assert f["t"] == T0 and f["vol"] == 1 and f["src"] == "ux"
    assert ux_log.forming("NIFTY", "2026-09-11")["t"] == T0          # peeking closes nothing


def test_rebuild_streams_the_book_file_and_writes_only_missing_bins(monkeypatch):
    p = book_log.day_path("2026-09-11", "NIFTY")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        for r in _rows():
            f.write(json.dumps(r) + "\n")
    # a previous process already wrote bin 0
    ux_log.on_frames([("NIFTY", r) for r in _rows()[:3]], "2026-09-11", lot=65, tick=0.05)
    ux_log._STATE.clear()
    n = ux_log.rebuild("2026-09-11", "NIFTY", lot=65, tick=0.05)
    bars = ux_log.read_bars("2026-09-11", "NIFTY")
    assert n == 2 and [b["t"] for b in bars] == [T0, T0 + 300_000, T0 + 600_000]
    assert bars[-1]["vol"] == 1                                          # the open bin at file end, closed by rebuild
    assert ux_log.state("NIFTY", "2026-09-11")["bars"][-1]["t"] == T0 + 600_000


def test_rebuild_without_a_book_file_writes_nothing():
    assert ux_log.rebuild("2026-09-11", "NIFTY") == 0 and ux_log.read_bars("2026-09-11", "NIFTY") == []


def test_a_day_roll_starts_a_fresh_ladder():
    ux_log.on_frames([("NIFTY", _rows()[0])], "2026-09-11", lot=65, tick=0.05)
    ux_log.on_frames([("NIFTY", _rows()[0])], "2026-09-12", lot=65, tick=0.05)
    assert ux_log.state("NIFTY", "2026-09-12")["day"] == "2026-09-12"
    assert ux_log.state("NIFTY", "2026-09-12")["bars"] == []


def test_write_failure_is_counted_never_raised(monkeypatch):
    monkeypatch.setattr(ux_log, "_write_lines", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    out = ux_log.on_frames([("NIFTY", r) for r in _rows()], "2026-09-11", lot=65, tick=0.05)
    assert len(out) == 2 and ux_log.failed >= 2
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_ux_log.py -q`
Expected: `ModuleNotFoundError: No module named 'ux_log'`

- [ ] **Step 3: Write `ux_log.py`**

```python
# tapemap/ux_log.py
"""ux_log.py -- THE UPSTOX LADDER RECORD. data/tape/ux_<idx>_<day>.jsonl.

The third population in data/tape/ (spec 2026-09-20 §J.10): bars derived by
ladder.py from the book record, one row per closed bin, write-once by `t`,
src:"ux" on every row. GoCharting's bars (tape_<idx>) and the extension's
marks (ofd_marks_<idx>) are the other two; a reader of any one never has to
filter the others out.

WHO CALLS IT. The senses loop, once a pass, with the rows book_log.flush just
wrote (`on_frames`). On start, `rebuild` streams today's book file through a
fresh Ladder and writes every closed bin the previous process did not -- the
anytime-start rule in one function, and what lets tools/gate_report.py run
from files alone.

THE FORMING BAR IS NEVER WRITTEN (tape_log's rule); `forming` serves it from
the open accumulator by closing a COPY.

FAIL-SOFT, opened per call, "a" mode. A derivation written beside a
measurement is how vpin_backfill had to be split from vpin_log -- this file
holds only the derivation, and the book file holds only the measurement.
"""
from __future__ import annotations

import copy
import json
import os
from collections import deque
from typing import Dict, List, Optional, Tuple

import book_log
import ladder
import tape_log

failed = 0
_STATE: Dict[str, dict] = {}          # idx -> {"day", "ladder", "bars", "fills", "written", "seen"}


def day_path(day: str, idx: str) -> str:
    return os.path.join(tape_log.DIR, f"ux_{idx}_{day}.jsonl")


def read_bars(day: str, idx: str) -> List[dict]:
    return tape_log._read(day_path(day, idx))


def _write_lines(path: str, rows: List[dict]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))


def state(idx: str, day: str, lot: Optional[int] = None, tick: Optional[float] = None) -> dict:
    """The per-index state for `day`; a new day replaces yesterday's ladder."""
    st = _STATE.get(idx)
    if st is None or st["day"] != day:
        bars = read_bars(day, idx)
        st = _STATE[idx] = {"day": day, "ladder": ladder.Ladder(lot=lot, tick=tick, idx=idx, day=day),
                            "bars": bars, "fills": deque(maxlen=20_000), "written": 0,
                            "seen": {b["t"] for b in bars if isinstance(b.get("t"), int)}}
    return st


def _land(st: dict, idx: str, day: str, bar: dict) -> bool:
    """Write one closed bar once. Returns whether it was new."""
    global failed
    if bar["t"] in st["seen"]:
        return False
    st["seen"].add(bar["t"])
    st["bars"].append(bar)
    try:
        _write_lines(day_path(day, idx), [bar])
        st["written"] += 1
    except Exception:                       # never take the tape down
        failed += 1
    return True


def on_frames(rows: List[Tuple[str, dict]], day: str, lot: Optional[int] = None,
              tick: Optional[float] = None, observer=None) -> List[Tuple[str, dict, List[dict]]]:
    """Feed the rows a drain produced. Returns (idx, closed bar, fills this pass).

    `lot`/`tick` are used only when an index's state is CREATED; the server
    calls `state(idx, day, lot, tick)` per index first, then this without them.
    `observer(idx, row, fills)`, when given, is called once per row AFTER the
    ladder stepped it -- how runs.py and impact.py see every frame (Task 12)."""
    out: List[Tuple[str, dict, List[dict]]] = []
    fills_by: Dict[str, List[dict]] = {}
    for idx, row in rows:
        st = state(idx, day, lot, tick)
        closed, fills = st["ladder"].step(row)
        if fills:
            st["fills"].extend(fills)
            fills_by.setdefault(idx, []).extend(fills)
        if observer is not None:
            observer(idx, row, fills)
        if closed is not None and _land(st, idx, day, closed):
            out.append((idx, closed, fills_by.get(idx, [])))
    return out


def forming(idx: str, day: str) -> Optional[dict]:
    st = _STATE.get(idx)
    if st is None or st["day"] != day or st["ladder"].acc is None:
        return None
    return copy.deepcopy(st["ladder"]).close_open()


def rebuild(day: str, idx: str, lot: Optional[int] = None, tick: Optional[float] = None,
            observer=None) -> int:
    """Stream today's book file; write every closed bin the file holds that the
    ux file lacks, and close the bin the file ends inside. Returns bars written.
    `observer` as in `on_frames`, so runs/impact warm up on a restart too."""
    n = 0
    st = state(idx, day, lot, tick)
    lad = st["ladder"]
    any_row = False
    for row in book_log.read_rows(day, idx):
        any_row = True
        closed, fills = lad.step(row)
        st["fills"].extend(fills)
        if observer is not None:
            observer(idx, row, fills)
        if closed is not None and _land(st, idx, day, closed):
            n += 1
    if any_row:
        last = lad.close_open()
        if last is not None and _land(st, idx, day, last):
            n += 1
    return n
```

`conftest.py` — add to the autouse fixture, before `yield` and again after: `ux_log._STATE.clear()` (import `ux_log` beside `book_log`).

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_ux_log.py test_book_log.py -q`
Expected: all pass (`6` new)

- [ ] **Step 5: Bump the count and commit**

```bash
git add ux_log.py test_ux_log.py conftest.py context/DEFERRED.md
git commit -m "ux_log: the third file in data/tape/ -- bars once at bin close, rebuilt from the book on start, the forming bar never written

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: `gate.py` — two records on one grid, shape only

**Files:**
- Create: `gate.py`
- Test: `test_gate.py`

**Interfaces:**
- Consumes: `prints.rebin`, `prints.bar_flags`, `prints.profile`, `prints.nodes` (Task 4).
- Produces: `per_bar(ofd_bar, ux_bar, row_size, anchor) -> dict` (`poc_rows`, `delta_sign`, `vol_ratio`, `stacks`, `unfinished`, each with a `*_why` when null), `session(ofd_bars, ux_bars, row_size, anchor) -> dict` (spec §D's per-session fields, every one `tag: "M"`, nulls carrying a `why`).

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_gate.py
"""The gate: numbers about two records, never a verdict (spec 2026-09-20 §D)."""
import gate

T0 = 1789098300000


def _bar(t, ladder, vol=None, delta=None, h=None, l=None):
    lad = [{"p": p, "b": b, "s": s, "bt": 1, "st": 1} for p, b, s in ladder]
    v = vol if vol is not None else sum(b + s for _, b, s in ladder)
    d = delta if delta is not None else sum(b - s for _, b, s in ladder)
    ps = [p for p, _, _ in ladder]
    return {"t": t, "o": ps[0], "h": h if h is not None else max(ps), "l": l if l is not None else min(ps), "c": ps[-1],
            "vol": v, "buy": (v + d) / 2, "sell": (v - d) / 2, "delta": d, "ladder": lad}


def test_per_bar_measures_poc_distance_sign_and_ratio_on_the_given_grid():
    o = _bar(T0, [(100.0, 10, 2), (105.0, 3, 1)])
    u = _bar(T0, [(100.0, 2, 1), (105.0, 9, 1)])
    r = gate.per_bar(o, u, 5, 0)
    assert r["poc_rows"] == 1 and r["delta_sign"] == "agree" and abs(r["vol_ratio"] - 13 / 16) < 1e-9
    assert r["stacks"] == "neither" and r["unfinished"] == "neither" and r["tag"] == "M"


def test_per_bar_nulls_carry_a_why():
    o = _bar(T0, [(100.0, 5, 5)])
    u = _bar(T0, [(100.0, 5, 5)])
    r = gate.per_bar(o, u, 5, 0)
    assert r["delta_sign"] is None and r["delta_sign_why"] == "a delta of 0 has no sign"
    r2 = gate.per_bar(_bar(T0, [(100.0, 0, 0)], vol=0), u, 5, 0)
    assert r2["vol_ratio"] is None and r2["vol_ratio_why"] == "GoCharting volume is 0"
    r3 = gate.per_bar({"t": T0, "vol": 1, "delta": 1, "ladder": None}, u, 5, 0)
    assert r3["poc_rows"] is None and r3["poc_rows_why"] == "no POC on one side"


def test_session_joins_on_t_and_reports_the_named_fields():
    o = [_bar(T0, [(100.0, 10, 2), (105.0, 3, 1)]), _bar(T0 + 300_000, [(105.0, 1, 8)]), _bar(T0 + 600_000, [(110.0, 4, 4)])]
    u = [_bar(T0, [(100.0, 9, 1), (105.0, 3, 1)]), _bar(T0 + 300_000, [(110.0, 1, 8)])]
    for b in u:
        b["src"] = "ux"; b["exact"] = 2; b["reconstructed"] = 1; b["hidden"] = 1; b["unknown"] = 0
    s = gate.session(o, u, 5, 0)
    assert s["bars_joined"] == 2 and s["bars_ofd_only"] == 1 and s["bars_ux_only"] == 0
    assert s["poc_rows_median"] == 0.5 and s["poc_within_1"] == 1.0
    assert s["delta_sign_agree"] == 1.0
    assert abs(s["vol_ratio_median"] - (14 / 16 + 9 / 9) / 2) < 1e-9
    assert 0 < s["va_overlap"] <= 1 and s["hvn_jaccard"] is not None and s["tag"] == "M"
    assert s["exact_frac"] == 4 / 6 and s["hidden_frac"] == 2 / 23 and s["unknown_frac"] == 0.0


def test_session_with_nothing_to_join_says_so():
    s = gate.session([_bar(T0, [(100.0, 1, 1)])], [], 5, 0)
    assert s["bars_joined"] == 0 and s["poc_rows_median"] is None and s["poc_rows_median_why"] == "no joined bars"
    assert s["va_overlap"] is None and s["va_overlap_why"] == "no ux profile"
    assert s["lvn_jaccard"] is None and s["lvn_jaccard_why"] == "no LVN on one side"
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_gate.py -q`
Expected: `ModuleNotFoundError: No module named 'gate'`

- [ ] **Step 3: Write `gate.py`**

```python
# tapemap/gate.py
"""gate.py -- GoCharting's bars against the Upstox ladder, on one grid, by SHAPE.

WHAT IT RETURNS: numbers. POC distance in rows, delta sign agreement, value-
area overlap, node-set Jaccard, and one magnitude -- the volume ratio, [M]
against [M], a feed-integrity check, never a trading quantity. It returns no
verdict, no pass, no colour: the bar is the operator's (spec §K), stated after
five sessions. Every null carries its why (rule 6). Both records are re-binned
on GoCharting's grid (spec §J.4) -- the grid the operator's chart is on.

Pure, stdlib only, no I/O, no clock.
"""
from __future__ import annotations

from statistics import median
from typing import List, Optional

import prints


def _four(a: bool, b: bool) -> str:
    return "both" if a and b else "ofd" if a else "ux" if b else "neither"


def _sign(x) -> int:
    return 0 if not x else (1 if x > 0 else -1)


def per_bar(o: dict, u: dict, row_size: float, anchor: float = 0.0) -> dict:
    fo, fu = prints.bar_flags(o, row_size, anchor), prints.bar_flags(u, row_size, anchor)
    out: dict = {"t": o.get("t"), "tag": "M"}
    po, pu = (fo or {}).get("poc"), (fu or {}).get("poc")
    if po is None or pu is None:
        out["poc_rows"], out["poc_rows_why"] = None, "no POC on one side"
    else:
        out["poc_rows"], out["poc_rows_why"] = int(round(abs(pu - po) / row_size)), None
    so, su = _sign(o.get("delta")), _sign(u.get("delta"))
    if so == 0 or su == 0:
        out["delta_sign"], out["delta_sign_why"] = None, "a delta of 0 has no sign"
    else:
        out["delta_sign"], out["delta_sign_why"] = ("agree" if so == su else "disagree"), None
    vo = o.get("vol") or 0
    if not vo:
        out["vol_ratio"], out["vol_ratio_why"] = None, "GoCharting volume is 0"
    else:
        out["vol_ratio"], out["vol_ratio_why"] = (u.get("vol") or 0) / vo, None
    out["stacks"] = _four(bool((fo or {}).get("stacks")), bool((fu or {}).get("stacks")))
    out["unfinished"] = _four(bool((fo or {}).get("unfinished_high") or (fo or {}).get("unfinished_low")),
                              bool((fu or {}).get("unfinished_high") or (fu or {}).get("unfinished_low")))
    return out


def _jaccard(a: set, b: set) -> Optional[float]:
    return None if not a or not b else len(a & b) / len(a | b)


def _interval_overlap(x: Optional[dict], y: Optional[dict]) -> Optional[float]:
    if not x or not y:
        return None
    lo, hi = max(x["val"], y["val"]), min(x["vah"], y["vah"])
    union = max(x["vah"], y["vah"]) - min(x["val"], y["val"])
    return 1.0 if union <= 0 else max(0.0, hi - lo) / union


def rebinned(bars: List[dict], row_size: float, anchor: float) -> List[dict]:
    """Copies of `bars` with each ladder on the given grid -- the server's ux
    levels use this too, so profile and gate read one grid."""
    return [{**b, "ladder": prints.rebin(b.get("ladder") or [], row_size, anchor)} for b in bars]


def session(ofd: List[dict], ux: List[dict], row_size: float, anchor: float = 0.0) -> dict:
    by_o = {b["t"]: b for b in ofd if b.get("t") is not None}
    by_u = {b["t"]: b for b in ux if b.get("t") is not None}
    joined = sorted(set(by_o) & set(by_u))
    rows = [per_bar(by_o[t], by_u[t], row_size, anchor) for t in joined]
    out: dict = {"tag": "M", "bars_joined": len(joined),
                 "bars_ofd_only": len(set(by_o) - set(by_u)), "bars_ux_only": len(set(by_u) - set(by_o))}

    def med(key, name):
        v = [r[key] for r in rows if r.get(key) is not None]
        out[name] = median(v) if v else None
        out[name + "_why"] = None if v else ("no joined bars" if not rows else f"{key} null on every joined bar")

    med("poc_rows", "poc_rows_median")
    pr = [r["poc_rows"] for r in rows if r.get("poc_rows") is not None]
    out["poc_within_1"] = (sum(1 for x in pr if x <= 1) / len(pr)) if pr else None
    out["poc_within_1_why"] = None if pr else out["poc_rows_median_why"]
    ds = [r["delta_sign"] for r in rows if r.get("delta_sign") is not None]
    out["delta_sign_agree"] = (ds.count("agree") / len(ds)) if ds else None
    out["delta_sign_agree_why"] = None if ds else ("no joined bars" if not rows else "every joined bar has a 0 delta on one side")
    med("vol_ratio", "vol_ratio_median")

    po, pu = prints.profile(rebinned(ofd, row_size, anchor)), prints.profile(rebinned(ux, row_size, anchor))
    out["va_overlap"] = _interval_overlap(po, pu)
    out["va_overlap_why"] = None if out["va_overlap"] is not None else ("no ux profile" if not pu else "no GoCharting profile")
    no, nu = prints.nodes(po), prints.nodes(pu)
    for kind, key in (("HVN", "hvn_jaccard"), ("LVN", "lvn_jaccard")):
        a = {n["p"] for n in no if n["kind"] == kind}
        b = {n["p"] for n in nu if n["kind"] == kind}
        out[key] = _jaccard(a, b)
        out[key + "_why"] = None if out[key] is not None else f"no {kind} on one side"

    ex = sum(b.get("exact") or 0 for b in ux)
    rc = sum(b.get("reconstructed") or 0 for b in ux)
    vol = sum(b.get("vol") or 0 for b in ux)
    out["exact_frac"] = ex / (ex + rc) if (ex + rc) else None
    out["exact_frac_why"] = None if (ex + rc) else "no trading interval in the ux record"
    out["hidden_frac"] = (sum(b.get("hidden") or 0 for b in ux) / vol) if vol else None
    out["unknown_frac"] = (sum(b.get("unknown") or 0 for b in ux) / vol) if vol else None
    out["hidden_frac_why"] = out["unknown_frac_why"] = None if vol else "no ux volume"
    return out
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_gate.py -q`
Expected: `4 passed`. If `test_session_joins_on_t...`'s `va_overlap`/`hvn_jaccard` assertions fail on the toy ladders, read `prints.profile`'s paired expansion on the two-row profiles and adjust the toy ladders (not the assertions' shape) until both sides have a value area and at least one shared HVN bin — say so in the test docstring.

- [ ] **Step 5: Bump the count and commit**

```bash
git add gate.py test_gate.py context/DEFERRED.md
git commit -m "gate: two records on GoCharting's grid, by shape -- POC rows, sign, value area, nodes, one integrity ratio, no verdict

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: `runs.py` — three big same-side fills in a row

**Files:**
- Create: `runs.py`
- Test: `test_runs.py`

**Interfaces:**
- Consumes: fill events from `ladder.Ladder.step` (Task 7): `{"ltt": ms, "side": int, "p": float, "q": units, "hidden": bool}`.
- Produces: `RUN_N, RUN_PCT, RUN_WIN_S, RUN_GAP_S, RUN_MIN_N`, `class Runs(lot=None)` with `on_fill(f) -> dict | None` (the run the moment it FIRES — its third fill — else None; a continuing run grows in place), `events: list[dict]` (every fired run, mutated in place while it presses), `why() -> str | None`, `window_n -> int`. Run dict: `{t, kind: "run", side, n, qty, thr, from_t, to_t, src: "ux", tag: "I", why}` with `t = to_t` (ms), `qty`/`thr` in **lots** when `lot` is given, units otherwise.

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_runs.py
"""Runs of three: causal percentile, gap, side, in-place growth (spec 2026-09-20 §G)."""
import runs

T = 1789098300000


def F(sec, side, q, hidden=False):
    return {"ltt": T + sec * 1000, "side": side, "p": 100.0, "q": q, "hidden": hidden}


def _warm(r, n=50, sizes=(65, 130, 195, 260, 325), start=0):
    """Fifty fills, ten of each size, 10 s apart (no run can form): the sorted
    window is 10x65..10x325 and index int(50*0.9)=45 lands on 325 -- so 'big'
    is >= 325 units (5 lots) and a 65-unit fill is clearly small."""
    for i in range(n):
        r.on_fill(F(start + i * 10, 1 if i % 2 else -1, sizes[i % len(sizes)]))


def test_nothing_fires_under_min_n_and_why_says_so():
    r = runs.Runs(lot=65)
    assert r.why() == "fewer than 50 fills in the last 20 minutes — the percentile has nothing to rank against"
    for i in range(49):
        assert r.on_fill(F(i, 1, 65_000)) is None
    assert r.events == [] and r.window_n == 49


def test_three_big_same_side_fills_inside_three_seconds_fire_once_then_grow():
    r = runs.Runs(lot=65)
    _warm(r)                                         # threshold 325 units = 5 lots
    assert r.on_fill(F(600, 1, 650)) is None
    assert r.on_fill(F(602, 1, 650)) is None
    ev = r.on_fill(F(604, 1, 650))
    assert ev is not None and ev["kind"] == "run" and ev["side"] == 1 and ev["n"] == 3
    assert ev["from_t"] == T + 600_000 and ev["to_t"] == T + 604_000 and ev["t"] == ev["to_t"]
    assert ev["qty"] == 30 and ev["thr"] == 5 and ev["src"] == "ux" and ev["tag"] == "I" and ev["p"] == 100.0
    assert ev["why"] == "3 buys ≥ 5 lots inside 3 s — each in the top decile of the last 20 min"
    assert r.on_fill(F(606, 1, 650)) is None         # the same run, still pressing
    assert len(r.events) == 1 and r.events[0]["n"] == 4 and r.events[0]["to_t"] == T + 606_000 and r.events[0]["qty"] == 40
    assert r.why() is None


def test_a_gap_over_three_seconds_restarts_the_run():
    r = runs.Runs(lot=65)
    _warm(r)
    r.on_fill(F(600, 1, 650)); r.on_fill(F(602, 1, 650))
    assert r.on_fill(F(606, 1, 650)) is None         # 4 s after the last: a new run of one
    assert r.on_fill(F(607, 1, 650)) is None and r.on_fill(F(608, 1, 650)) is not None


def test_a_big_opposite_fill_breaks_the_run_a_small_one_does_not():
    r = runs.Runs(lot=65)
    _warm(r)
    r.on_fill(F(600, 1, 650)); r.on_fill(F(601, -1, 65)); r.on_fill(F(602, 1, 650))   # small sell ignored
    assert r.on_fill(F(603, 1, 650)) is not None
    r2 = runs.Runs(lot=65)
    _warm(r2)
    r2.on_fill(F(600, 1, 650)); r2.on_fill(F(601, -1, 650)); r2.on_fill(F(602, 1, 650))  # big sell breaks
    assert r2.on_fill(F(603, 1, 650)) is None


def test_the_percentile_is_causal_the_judged_fill_is_not_in_its_own_window():
    """Window = sizes 65*1..65*50, so the causal bar (index 45 of 50) is 46*65 = 2990.
    A fill of 45*65 = 2925 must NOT qualify. If the fill were inserted before being
    judged, the 51-value window's index 45 would be 2925 itself and it WOULD --
    and the second and third such fills would then complete a run at 602 s."""
    r = runs.Runs(lot=65)
    for i in range(50):
        r.on_fill(F(i * 10, 1 if i % 2 else -1, 65 * (i + 1)))
    assert r.on_fill(F(600, 1, 2925)) is None
    assert r.on_fill(F(601, 1, 2925)) is None           # once inserted, 2925 IS the bar: this one qualifies (run of 1)
    assert r.on_fill(F(602, 1, 2925)) is None           # run of 2 -- a non-causal window would have fired here
    assert r.on_fill(F(603, 1, 2925)) is not None       # run of 3


def test_a_fill_with_no_side_neither_joins_nor_breaks():
    r = runs.Runs(lot=65)
    _warm(r)
    r.on_fill(F(600, 1, 650)); r.on_fill(F(601, 0, 650)); r.on_fill(F(602, 1, 650))
    assert r.on_fill(F(603, 1, 650)) is not None


def test_the_window_forgets_fills_older_than_twenty_minutes():
    r = runs.Runs(lot=65)
    _warm(r)                                         # last at 490 s
    r.on_fill(F(490 + 1201, 1, 650))                 # everything before is out of the window
    assert r.window_n == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_runs.py -q`
Expected: `ModuleNotFoundError: No module named 'runs'`

- [ ] **Step 3: Write `runs.py`**

```python
# tapemap/runs.py
"""runs.py -- three big same-side fills in a row (spec 2026-09-20 §G).

Order Flow Lab's sweep sequence (orderflow.html:837-895), fed by ladder.py's
FILL EVENTS rather than sweep.py's rows: 485 sweep rows a day is ~26 per
twenty minutes, under the 50 the percentile needs; fills run in the thousands.

Five constants, carried verbatim and NOT tuned before spec §K:
  RUN_N      3     fills in a row before it counts
  RUN_PCT    0.90  "big" = at or above this percentile ...
  RUN_WIN_S  1200  ... of fill sizes in the last 20 minutes
  RUN_GAP_S  3     at most this many seconds between one fill and the next
  RUN_MIN_N  50    a percentile drawn from fewer fills is not trusted

CAUSAL: a fill is judged against the fills BEFORE it, then inserted. A run
breaks on a big fill from the OTHER side; a small fill (either side) is
ignored -- "three sells in a row" means nobody big bought in between. A run
fires once, at its third fill, and grows in place while the pressing continues.
Side is [I] because the fills' sides are; side 0 neither joins nor breaks.

Kill condition (spec §G): at n >= 30 runs on one index, the +6-bar excursion
in the run's direction must exceed the unconditional control by one sd, else
the glyph goes. Scored by spec 1's scorer, never printed as a rate.

Pure, stdlib only, no I/O, no clock.
"""
from __future__ import annotations

from bisect import bisect_left, insort
from collections import deque
from typing import List, Optional

RUN_N = 3
RUN_PCT = 0.90
RUN_WIN_S = 1200
RUN_GAP_S = 3
RUN_MIN_N = 50


class Runs:
    def __init__(self, lot: Optional[int] = None):
        self.lot = lot
        self._win: deque = deque()          # (ltt_ms, q) in arrival order
        self._sizes: List[int] = []         # the same q's, sorted
        self._run: Optional[dict] = None    # {"side", "fills": [f...], "ev": dict | None}
        self.events: List[dict] = []
        self._checked = False

    @property
    def window_n(self) -> int:
        return len(self._win)

    def _lots(self, units: float) -> float:
        return units / self.lot if self.lot else units

    @staticmethod
    def _wavg_p(fills: List[dict]) -> Optional[float]:
        """The run's price for the chart: its fills' quantity-weighted mean."""
        q = sum(f["q"] for f in fills)
        return round(sum(f["p"] * f["q"] for f in fills) / q, 4) if q else None

    def _forget(self, now_ms: int) -> None:
        while self._win and self._win[0][0] < now_ms - RUN_WIN_S * 1000:
            _, q = self._win.popleft()
            i = bisect_left(self._sizes, q)
            if i < len(self._sizes) and self._sizes[i] == q:
                del self._sizes[i]

    def _threshold(self) -> Optional[int]:
        if len(self._sizes) < RUN_MIN_N:
            return None
        return self._sizes[min(len(self._sizes) - 1, int(len(self._sizes) * RUN_PCT))]

    def why(self) -> Optional[str]:
        if len(self._sizes) < RUN_MIN_N:
            return "fewer than 50 fills in the last 20 minutes — the percentile has nothing to rank against"
        return None if self.events else "checked, none"

    def on_fill(self, f: dict) -> Optional[dict]:
        """Judge one fill against the window BEFORE inserting it. Returns the
        run the moment it fires (its third fill); a continuing run grows in
        place and returns None."""
        t, q, side = int(f["ltt"]), int(f["q"]), int(f.get("side") or 0)
        self._forget(t)
        thr = self._threshold()
        fired = None
        if thr is not None and q >= thr and side != 0:          # a BIG fill with a side
            run = self._run
            prev = run["fills"][-1] if run else None
            if run and run["side"] == side and t - prev["ltt"] <= RUN_GAP_S * 1000:
                run["fills"].append(f)
            else:
                # a new run -- which is also how a big fill from the OTHER side
                # breaks the old one (SEQ_STRICT = false: only a big opposite
                # fill breaks; a small fill of either side, or one with no
                # side, is ignored below and the run stands)
                run = self._run = {"side": side, "fills": [f], "ev": None}
            n = len(run["fills"])
            if n == RUN_N:
                fs = run["fills"]
                word = "buys" if side == 1 else "sells"
                ev = {"t": t, "kind": "run", "side": side, "n": n, "from_t": fs[0]["ltt"], "to_t": t,
                      "qty": self._lots(sum(x["q"] for x in fs)), "thr": self._lots(thr), "p": self._wavg_p(fs),
                      "src": "ux", "tag": "I",
                      "why": f"{n} {word} ≥ {self._lots(thr):g} lots inside {RUN_GAP_S} s — each in the top decile of the last 20 min"}
                run["ev"] = ev
                self.events.append(ev)
                fired = ev
            elif n > RUN_N and run["ev"] is not None:
                ev = run["ev"]
                ev["n"], ev["to_t"], ev["t"] = n, t, t
                ev["qty"] = self._lots(sum(x["q"] for x in run["fills"]))
                ev["p"] = self._wavg_p(run["fills"])
        self._win.append((t, q))
        insort(self._sizes, q)
        return fired
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_runs.py -q`
Expected: `7 passed`. Note in `test_three_big...`: with 50 warm fills of 65 the sorted sizes are all 65 and `int(50 * 0.9) = 45` → `thr = 65`, one lot; the run's three 650-unit fills are 10 lots each, `qty == 30`.

- [ ] **Step 5: Bump the count and commit**

```bash
git add runs.py test_runs.py context/DEFERRED.md
git commit -m "runs: three big same-side fills inside three seconds, causal decile over twenty minutes, constants named not tuned

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: `impact.py` — lots per tick, rolling 120 s

**Files:**
- Create: `impact.py`
- Test: `test_impact.py`

**Interfaces:**
- Consumes: book rows (Task 1 shape) and the fills each row produced (Task 7).
- Produces: `IMPACT_WIN_S = 120`, `class Impact(lot=None, tick=None)` with `on_frame(row, fills) -> None` and `read() -> dict` = `{"lambda": float | None, "lots_per_tick": float | None, "pct": float | None, "n": int, "why": str | None, "tag": "I"}`. `pct` is `prints.pct_rank` (strict) of λ against the session's earlier readings.

- [ ] **Step 1: Write the failing tests**

```python
# tapemap/test_impact.py
"""Kyle's lambda off attributed volume: a synthetic slope is recovered (spec 2026-09-20 §G)."""
import impact
from test_ladder import R, T0


def _row(sec, bid, ask):
    return R(T0 + sec * 1000, 1000, (bid + ask) / 2, 65, [[bid, 65]], [[ask, 65]])


def test_fewer_than_120s_of_frames_is_a_sentence():
    im = impact.Impact(lot=65, tick=0.05)
    im.on_frame(_row(0, 100.00, 100.05), [])
    r = im.read()
    assert r["lambda"] is None and r["why"] == "fewer than 120 s of frames" and r["tag"] == "I"


def test_a_known_slope_is_recovered_in_lots_per_tick():
    """Every 130 units (2 lots) of net buying moves mid one tick: lambda = 0.5 ticks/lot -> 2 lots per tick."""
    im = impact.Impact(lot=65, tick=0.05)
    mid = 100.00
    im.on_frame(_row(0, mid, mid + 0.05), [])
    for s in range(1, 130):
        mid = round(mid + 0.05, 2)
        im.on_frame(_row(s, mid, mid + 0.05), [{"ltt": T0 + s * 1000, "side": 1, "p": mid, "q": 130, "hidden": False}])
    r = im.read()
    assert r["n"] >= 120 and abs(r["lots_per_tick"] - 2.0) < 1e-6 and r["why"] is None


def test_no_signed_volume_in_the_window_is_its_own_sentence():
    im = impact.Impact(lot=65, tick=0.05)
    for s in range(0, 130):
        im.on_frame(_row(s, 100.00, 100.05), [])
    assert im.read()["why"] == "no signed volume in the window"


def test_pct_ranks_lambda_against_the_session_so_far():
    im = impact.Impact(lot=65, tick=0.05)
    mid = 100.00
    im.on_frame(_row(0, mid, mid + 0.05), [])
    for s in range(1, 400):
        q = 130 if s < 250 else 65                      # the market thins: fewer lots per tick later
        mid = round(mid + 0.05, 2)
        im.on_frame(_row(s, mid, mid + 0.05), [{"ltt": T0 + s * 1000, "side": 1, "p": mid, "q": q, "hidden": False}])
    r = im.read()
    assert r["lots_per_tick"] < 2.0 and r["pct"] is not None and r["pct"] > 0.5
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_impact.py -q`
Expected: `ModuleNotFoundError: No module named 'impact'`

- [ ] **Step 3: Write `impact.py`**

```python
# tapemap/impact.py
"""impact.py -- how many lots move price a tick (Kyle's lambda), rolling 120 s.

Order Flow Lab's buildLambda (orderflow.html:701-730): a regression through the
origin of mid change (ticks) on signed attributed volume, over the last
IMPACT_WIN_S seconds of frames. lambda = sum(sv*dp) / sum(sv^2) ticks per unit
when both sums are positive, else None with its why. Reported as LOTS PER TICK
(1 / (lambda * lot)) -- the desk trades lots -- and as pct: prints.pct_rank
(strict) of lambda against the session's earlier readings. A thin market is a
HIGH lambda. [I] throughout, because the signed volume is (spec §J.3).

Kill condition (spec §G): over 30 sessions, if top-quartile lambda readings
precede top-5% 6-bar moves no more often than any other reading, the figure
goes. Never printed as a rate.

Pure, stdlib only, no I/O, no clock -- time is the rows' own `t`.
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional

import prints

IMPACT_WIN_S = 120


class Impact:
    def __init__(self, lot: Optional[int] = None, tick: Optional[float] = None):
        self.lot, self.tick = lot, tick
        self._win: deque = deque()          # (t_ms, dp_ticks, sv_units)
        self._prev_mid: Optional[float] = None
        self._history: List[float] = []     # every lambda read so far, for pct

    def on_frame(self, row: dict, fills: List[dict]) -> None:
        b = row["b"][0][0] if row.get("b") else None
        a = row["a"][0][0] if row.get("a") else None
        if b is None or a is None:
            return
        mid = (b + a) / 2
        tick = self.tick or 0.05
        dp = 0.0 if self._prev_mid is None else (mid - self._prev_mid) / tick
        self._prev_mid = mid
        sv = sum(f["q"] * f["side"] for f in fills if f.get("side"))
        t = int(row["t"])
        self._win.append((t, dp, sv))
        while self._win and self._win[0][0] < t - IMPACT_WIN_S * 1000:
            self._win.popleft()
        lam, _ = self._lam()
        if lam is not None:
            self._history.append(lam)          # the session's readings, one per frame that had one

    def _lam(self):
        """(lambda in ticks per unit, None) or (None, why)."""
        if not self._win or self._win[-1][0] - self._win[0][0] < (IMPACT_WIN_S - 1) * 1000:
            return None, "fewer than 120 s of frames"
        num = sum(dp * sv for _, dp, sv in self._win)
        den = sum(sv * sv for _, _, sv in self._win)
        if den <= 0:
            return None, "no signed volume in the window"
        if num <= 0:
            return None, "price moved against the flow over the window"
        return num / den, None

    def read(self) -> dict:
        """Pure: safe to call from the request path any number of times."""
        out = {"lambda": None, "lots_per_tick": None, "pct": None, "n": len(self._win), "why": None, "tag": "I"}
        lam, why = self._lam()
        if lam is None:
            out["why"] = why
            return out
        out["lambda"] = lam
        out["lots_per_tick"] = 1 / (lam * (self.lot or 1))
        # rank against the readings BEFORE this one (the last history entry is this frame's own)
        out["pct"] = prints.pct_rank(self._history[:-1], lam)
        return out
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_impact.py -q`
Expected: `4 passed`

- [ ] **Step 5: Bump the count and commit**

```bash
git add impact.py test_impact.py context/DEFERRED.md
git commit -m "impact: lots per tick off attributed volume, rolling 120 s, ranked against the session, a sentence when it cannot be read

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: `/api/tape` gains `ux`; the loop drains into the ladder, runs and impact

**Files:**
- Modify: `server.py` — imports, `_SENSES` (`"ux": {}`), `_senses_loop` (replace Task 3's flush block), `_tape_reply` (`:1054–1130`), add `_ux_meta`, `_ux_observe`, `_ux_bars`, `_ux_reply` above `_tape_reply`
- Test: `test_frame_api.py` (append), `test_book_wiring.py` (append)

**Interfaces:**
- Consumes: `ux_log.state/on_frames/rebuild/forming/read_bars/_STATE`, `gate.session/rebinned`, `runs.Runs`, `impact.Impact`, `upstox_instruments.lot_tick`, `book_log.Book.watched/book_from`.
- Produces: the `ux` object of spec §E on every `/api/tape` reply; `_tape_reply` answers `ok: true` with `bars: []` when GoCharting is absent but `ux` exists.

- [ ] **Step 1: Write the failing tests** (append to `test_frame_api.py`)

```python
# --- spec 2026-09-20-upstox-tape §E: the ux object -------------------------------

def _ux_seed(day="2026-09-11"):
    """Two closed ux bars whose t match _ladder_doc's first two bars."""
    import ux_log
    from test_ladder import R
    T = 1757563500000
    rows = [R(T + 1000, 1000, 100.0, 65, [[100.0, 65]], [[101.0, 65]]),
            R(T + 2000, 1065, 101.0, 65, [[100.0, 65]], [[101.0, 65]]),            # exact buy at 101
            R(T + 300_500, 1130, 100.0, 65, [[100.0, 65]], [[101.0, 65]]),         # exact sell at 100, bin 1
            R(T + 600_500, 1130, 100.0, 65, [[100.0, 65]], [[101.0, 65]])]         # bin 2: closes bin 1
    ux_log.state("NIFTY", day, 65, 1.0)
    ux_log.on_frames([("NIFTY", r) for r in rows], day)


def _isolate_ux(tmp_path, monkeypatch):
    import book_log
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setitem(server._SENSES, "book", book_log.Book())
    server._SENSES["ux"].clear()


def test_api_tape_ux_absent_is_the_first_sentence(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    ux = cap.sent["ux"]
    assert ux["src"] == "ux" and ux["tag"] == "I" and ux["bars"] == [] and ux["agree"] is None
    assert ux["why"] == "no book record for NIFTY on 2026-09-11 — the server was not recording (book_log predates it, or the feed never connected)"
    assert ux["levels"]["why"] == ux["why"] and ux["agree_why"] == ux["why"] and ux["marks"]["runs_why"] == ux["why"]


def test_api_tape_ux_book_but_no_bar_yet_is_the_second_sentence(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    server._SENSES["book"].book_from["NIFTY"] = "09:15:03"
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["ux"]["why"] == "book record from 09:15:03, no bar closed yet"


def test_api_tape_ux_bars_levels_marks_impact_and_agreement(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    _ux_seed()
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and len(j["bars"]) == 8                       # GoCharting untouched
    ux = j["ux"]
    assert ux["why"] is None and len(ux["bars"]) == 2 and "ladder" not in ux["bars"][0]
    assert ux["bars"][0]["exact"] == 1 and ux["bars"][0]["cvd"] == 1 and ux["bars"][1]["cvd"] == 0
    assert ux["bars"][0]["poc"] == 100.0 and ux["bars"][0]["partial"] is False
    assert ux["levels"]["session"]["poc"] == 100.0 and ux["levels"]["why"] is None
    assert ux["lot"] == 65 and ux["lot_src"] == "given" and ux["frames_per_s"] is not None
    assert ux["marks"]["runs"] == [] and isinstance(ux["marks"]["runs_why"], str)
    assert ux["impact"]["tag"] == "I" and isinstance(ux["impact"]["why"], str)
    ag = ux["agree"]
    assert ag["tag"] == "M" and ag["bars_joined"] == 2 and ag["poc_rows_median"] == 0 and ux["agree_why"] is None


def test_api_tape_ux_without_gocharting_stands_alone(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    _ux_seed()
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and j["src"] == "file" and j["bars"] == [] and j["rowSize"] == 5
    assert j["levels"]["why"] == "no GoCharting record for NIFTY on 2026-09-11 — ux stands alone"
    assert j["ux"]["agree"] is None
    assert j["ux"]["agree_why"] == "GoCharting record absent for this day — ux stands alone, flags on the default grid"
    assert len(j["ux"]["bars"]) == 2


def test_api_tape_neither_record_is_still_the_third_sentence(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["ok"] is False and "no prints record for NIFTY on 2026-09-11" in cap.sent["why"]
```

Append to `test_book_wiring.py`:

```python
def test_the_loop_rebuilds_on_a_new_day_before_the_flush_and_drains_into_the_ladder():
    src = inspect.getsource(server._senses_loop)
    i_rebuild = src.index("ux_log.rebuild(day, idx, st[\"lot\"], st[\"tick\"], observer=_ux_observe)")
    i_flush = src.index("_SENSES[\"book_rows\"] = _SENSES[\"book\"].flush()")
    i_drain = src.index("ux_log.on_frames(rows, day, observer=_ux_observe)")
    assert i_rebuild < i_flush < i_drain


def test_ux_meta_falls_back_to_none_none_when_the_slice_cannot_be_read(monkeypatch):
    import upstox_instruments
    monkeypatch.setattr(upstox_instruments, "lot_tick", lambda name: (_ for _ in ()).throw(RuntimeError("no dump")))
    server._SENSES["ux"].clear()
    st = server._ux_meta("NIFTY")
    assert st["lot"] is None and st["tick"] is None and st["runs"].lot is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest test_frame_api.py test_book_wiring.py -q -k "ux or rebuilds"`
Expected: `KeyError: 'ux'` / `AttributeError: _ux_meta` / `ValueError: substring not found`

- [ ] **Step 3: Implement**

Imports, after `import book_log`:

```python
import ux_log
import gate as gate_mod
import runs as runs_mod
import impact as impact_mod
import upstox_instruments
```

(`upstox_instruments` may already be imported further down; keep one import.)

`_SENSES` literal, after `"book": book_log.Book(), "book_rows": [],`:

```python
           # per-index lot/tick and the two book-derived detectors (spec §G);
           # keyed by idx, reset on a day roll in the loop
           "ux": {},
```

Module-level helpers, placed directly above `_tape_reply`:

```python
def _ux_meta(idx):
    """lot/tick for the index once per process, and its runs/impact machines.
    (None, None) when the cached slice predates the fields or cannot be read --
    ladder.py then infers and the row says `lot_src: "gcd"`."""
    st = _SENSES["ux"].get(idx)
    if st is None:
        try:
            lot, tick = upstox_instruments.lot_tick(idx)
        except Exception:                      # noqa: BLE001 -- no dump is not a reason to stop recording
            lot, tick = None, None
        st = _SENSES["ux"][idx] = {"lot": lot, "tick": tick, "day": None,
                                    "runs": runs_mod.Runs(lot=lot),
                                    "impact": impact_mod.Impact(lot=lot, tick=tick)}
    return st


def _ux_observe(idx, row, fills):
    """ux_log's per-row observer: every fill to the run detector, every frame to the gauge."""
    st = _ux_meta(idx)
    for f in fills:
        st["runs"].on_fill(f)
    st["impact"].on_frame(row, fills)


def _ux_bars(idx, day):
    st = ux_log._STATE.get(idx)
    if st is not None and st["day"] == day:
        return list(st["bars"])
    return ux_log.read_bars(day, idx)


_UX_KEEP = ("t", "o", "h", "l", "c", "vol", "buy", "sell", "unknown", "delta", "cvd", "oi",
            "exact", "reconstructed", "hidden", "partial", "partial_why")


def _ux_reply(idx, day, row, anchor, ofd_raw):
    """The ux object (spec §E): bars, levels, runs, impact, agreement -- three sentences each."""
    bars_raw = [b for b in _ux_bars(idx, day) if tape_log.bar_t(b) is not None]
    book = _SENSES["book"]
    book_from = book.book_from.get(idx)
    st = _SENSES["ux"].get(idx) or {}
    out = {"src": "ux", "tag": "I", "bars": [], "forming": None,
           "levels": {"session": None, "nodes": [], "why": None},
           "marks": {"runs": [], "runs_why": None}, "impact": None,
           "agree": None, "agree_why": None, "book_from": book_from, "frames_per_s": None,
           "lot": st.get("lot"), "lot_src": None, "why": None}
    if not bars_raw:
        if book_from is None and not os.path.exists(book_log.day_path(day, idx)):
            why = (f"no book record for {idx} on {day} — the server was not recording "
                   f"(book_log predates it, or the feed never connected)")
        else:
            why = f"book record from {book_from or 'file'}, no bar closed yet"
        out["why"] = out["levels"]["why"] = out["agree_why"] = out["marks"]["runs_why"] = why
        return out
    for b in prints.with_cvd(bars_raw):
        f = prints.bar_flags(b, row, anchor)
        out["bars"].append({**{k: b.get(k) for k in _UX_KEEP}, **(f or _NO_FLAGS)})
    fm = ux_log.forming(idx, day)
    if fm is not None:
        out["forming"] = {**{k: fm.get(k) for k in _UX_KEEP}, **(prints.bar_flags(fm, row, anchor) or _NO_FLAGS)}
    prof = prints.profile(gate_mod.rebinned(bars_raw, row, anchor))
    out["levels"] = {"session": ({"poc": prof["poc"], "vah": prof["vah"], "val": prof["val"]} if prof else None),
                     "nodes": prints.nodes(prof), "why": None if prof else "no ux bar with a ladder yet"}
    out["lot"], out["lot_src"] = bars_raw[-1].get("lot"), bars_raw[-1].get("lot_src")
    frames = sum(b.get("frames") or 0 for b in bars_raw)
    out["frames_per_s"] = round(frames / (300.0 * len(bars_raw)), 2)
    r = st.get("runs")
    out["marks"] = {"runs": [dict(e) for e in r.events] if r else [],
                    "runs_why": r.why() if r else "no fill has reached the run detector yet this process"}
    im = st.get("impact")
    out["impact"] = im.read() if im else {"lambda": None, "lots_per_tick": None, "pct": None, "n": 0,
                                          "why": "no frame has reached the impact gauge yet this process", "tag": "I"}
    if not ofd_raw:
        out["agree_why"] = "GoCharting record absent for this day — ux stands alone, flags on the default grid"
    else:
        ag = gate_mod.session(ofd_raw, bars_raw, row, anchor)
        if ag["bars_joined"] == 0:
            out["agree_why"] = "no GoCharting bar shares a t with any ux bar — nothing to compare"
        else:
            out["agree"] = ag
    return out
```

`_tape_reply` — three edits:

(a) the `else:` (file) branch becomes:

```python
    else:
        raw = tape_log.read_bars(day, idx)
        if not raw and not _ux_bars(idx, day) and not os.path.exists(book_log.day_path(day, idx)) \
                and idx not in _SENSES["book"].book_from:
            return {"ok": False, "idx": idx, "day": day, "src": None,
                    "why": f"no prints record for {idx} on {day} — GoCharting was on another index, or the extension never posted"}
        forming, ofd = None, tape_log.read_marks(day, idx)
        # no GoCharting record but a ux one: the extension's defaults (rowSize 5,
        # anchor 0), and levels.why says the grid was assumed (spec 2 §E)
        meta = ({"rowSize": raw[0].get("rowSize"), "rowAnchor": raw[0].get("rowAnchor", 0), "lot": raw[0].get("lot")}
                if raw else {"rowSize": 5, "rowAnchor": 0, "lot": None})
        forming_why = (f"extension not posting for {int(time.time() - held['at'])}s — showing the record" if held
                       else "extension not posting since server start — showing the record")
```

(b) the `levels` block's `"why"` becomes:

```python
                   "why": (f"no GoCharting record for {idx} on {day} — ux stands alone" if not raw
                           else None if prof else "no bar with a ladder yet")},
```

(c) the returned dict gains, after `"marks": {...},`:

```python
        "ux": _ux_reply(idx, day, row, anchor, raw),
```

`_senses_loop` — replace Task 3's drain block with:

```python
            # THE BOOK RECORD'S DRAIN AND THE LADDER, outside the lock with the
            # other writers (spec 2 §B, §E). Order matters: on the first pass of
            # a day (or a late start) the ladder is REBUILT from the book file
            # BEFORE this pass's rows are written, so nothing is stepped twice.
            try:
                day = time.strftime("%Y-%m-%d")
                for idx in _SENSES["book"].watched():
                    st = _ux_meta(idx)
                    if st["day"] != day:
                        st["day"] = day
                        st["runs"] = runs_mod.Runs(lot=st["lot"])
                        st["impact"] = impact_mod.Impact(lot=st["lot"], tick=st["tick"])
                        ux_log.state(idx, day, st["lot"], st["tick"])
                        n_re = ux_log.rebuild(day, idx, st["lot"], st["tick"], observer=_ux_observe)
                        if n_re:
                            log.info("ux: rebuilt %s bar(s) for %s from today's book record", n_re, idx)
                rows = _SENSES["book_rows"] = _SENSES["book"].flush()
                if rows:
                    ux_log.on_frames(rows, day, observer=_ux_observe)
            except Exception:                   # a disk fault costs the rows, never the tape
                _SENSES["book_rows"] = []
                log.exception("ux drain")
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_frame_api.py test_book_wiring.py test_senses_api.py -q`
Expected: all pass. The pre-existing `test_api_tape_neither_is_the_third_sentence` still passes (no ux, no book → `ok: false`).

- [ ] **Step 5: Bump the count and commit**

```bash
git add server.py test_frame_api.py test_book_wiring.py context/DEFERRED.md
git commit -m "server: /api/tape carries ux -- bars, levels, runs, impact and the agreement numbers; the loop rebuilds before it flushes and drains into the ladder

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 13: `tools/gate_report.py` — the day's numbers, no verdict

**Files:**
- Create: `tools/gate_report.py`
- Test: `test_gate_report.py`

**Interfaces:**
- Consumes: `tape_log.read_bars`, `ux_log.read_bars/rebuild`, `book_log.day_path`, `gate.session`.
- Produces: `main(idx, day, lot=None, tick=None) -> int` (exit code: 0 printed, 2 nothing to compare), output lines `name<pad> value  why  [M]`.

- [ ] **Step 1: Write the failing test**

```python
# tapemap/test_gate_report.py
"""The nightly table: every §D field, its why when null, and never a verdict."""
import sys
import os

import tape_log
import ux_log
from test_frame_api import _ladder_doc, _ux_seed

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import gate_report  # noqa: E402


def test_report_prints_every_session_field_and_no_verdict(capsys):
    doc = _ladder_doc()
    tape_log.append(doc, "2026-09-11", "NIFTY")
    _ux_seed()
    ux_log._STATE.clear()
    assert gate_report.main("NIFTY", "2026-09-11") == 0
    out = capsys.readouterr().out
    for k in ("bars_joined", "poc_rows_median", "poc_within_1", "delta_sign_agree", "vol_ratio_median",
              "va_overlap", "hvn_jaccard", "lvn_jaccard", "exact_frac", "hidden_frac", "unknown_frac"):
        assert k in out, k
    assert "[M]" in out
    low = out.lower()
    assert "pass" not in low and "fail" not in low and "verdict" not in low


def test_report_says_which_record_is_missing(capsys):
    assert gate_report.main("NIFTY", "2026-09-11") == 2
    out = capsys.readouterr().out
    assert "no GoCharting record for NIFTY on 2026-09-11" in out and "no ux record for NIFTY on 2026-09-11" in out
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest test_gate_report.py -q`
Expected: `ModuleNotFoundError: No module named 'gate_report'`

- [ ] **Step 3: Write the tool**

```python
# tapemap/tools/gate_report.py
"""One day's gate numbers (spec 2026-09-20-upstox-tape §D) from the two record
files, printed as a table. It prints NUMBERS; the bar is the operator's (§K).

    python tools/gate_report.py NIFTY 2026-09-22 [LOT [TICK]]

If the ux file is missing but the book file exists, the ux bars are rebuilt
from the book first (ux_log.rebuild), so this runs from files alone.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_log  # noqa: E402
import gate  # noqa: E402
import tape_log  # noqa: E402
import ux_log  # noqa: E402

FIELDS = ("bars_joined", "bars_ofd_only", "bars_ux_only", "poc_rows_median", "poc_within_1",
          "delta_sign_agree", "vol_ratio_median", "va_overlap", "hvn_jaccard", "lvn_jaccard",
          "exact_frac", "hidden_frac", "unknown_frac")


def _fmt(v):
    if v is None:
        return "—"
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def main(idx: str, day: str, lot=None, tick=None) -> int:
    ofd = tape_log.read_bars(day, idx)
    ux = ux_log.read_bars(day, idx)
    if not ux and os.path.exists(book_log.day_path(day, idx)):
        ux_log.rebuild(day, idx, lot, tick)
        ux = ux_log.read_bars(day, idx)
    missing = []
    if not ofd:
        missing.append(f"no GoCharting record for {idx} on {day}")
    if not ux:
        missing.append(f"no ux record for {idx} on {day} — and no book file to rebuild one from")
    for m in missing:
        print(m)
    if missing:
        return 2
    row = float(ofd[0].get("rowSize") or 5)
    anchor = float(ofd[0].get("rowAnchor") or 0)
    s = gate.session(ofd, ux, row, anchor)
    print(f"{idx} {day} — GoCharting vs ux on rowSize {row:g} (shape metrics; the bar is yours, §K)")
    for k in FIELDS:
        why = s.get(k + "_why") or ""
        print(f"{k:<20} {_fmt(s.get(k)):>8}  {why}  [M]".rstrip())
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    lot = int(sys.argv[3]) if len(sys.argv) > 3 else None
    tick = float(sys.argv[4]) if len(sys.argv) > 4 else None
    sys.exit(main(sys.argv[1].upper(), sys.argv[2], lot, tick))
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest test_gate_report.py -q`
Expected: `2 passed`

- [ ] **Step 5: Bump the count and commit**

```bash
git add tools/gate_report.py test_gate_report.py context/DEFERRED.md
git commit -m "tools: gate_report -- the day's shape-agreement numbers from the two files, rebuilt from the book if needed, no verdict

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 14: ui-v2 — the wire types, the dotted `ux` lines, the `s` glyphs, the counts

**Files:**
- Modify: `ui-v2/src/trade/tape.ts` (types), `ui-v2/src/trade/LevelsOverlay.ts` (`MARK_PRIO :1115`, `TM_LETTER :1196`, `printsCounts :1211`, `drawPrints` session-lines block `:1281–1285` and the tm block `:1327–1372`, `printsKey :1623`)
- Test: `cd ui-v2 && npx tsc --noEmit` (no runner exists)

**Interfaces:**
- Produces: `TapeReply.ux: TapeUx` and the `UxBarRow`, `UxRun`, `UxAgree`, `UxImpact`, `TapeUx` interfaces; `printsCounts(...)` gains `runsServed`, `runsDrawn`; `uxLegend(ux, runsDrawn, runsServed): string` (pure, in `tape.ts`) — Task 15 renders it.

- [ ] **Step 1: Types — append to `tape.ts` and extend `TapeReply` / `TapeMark`**

```ts
export interface UxBarRow extends TapeBarRow {
  unknown: number
  exact: number | null; reconstructed: number | null; hidden: number | null
  partial: boolean | null; partial_why: string | null
}
export interface UxRun {
  t: number; kind: 'run'; side: -1 | 1; n: number; qty: number; thr: number; p: number | null
  from_t: number; to_t: number; src: 'ux'; tag: 'I'; why: string
}
export interface UxAgree {
  tag: 'M'
  bars_joined: number; bars_ofd_only: number; bars_ux_only: number
  poc_rows_median: number | null; poc_rows_median_why: string | null
  poc_within_1: number | null; poc_within_1_why: string | null
  delta_sign_agree: number | null; delta_sign_agree_why: string | null
  vol_ratio_median: number | null; vol_ratio_median_why: string | null
  va_overlap: number | null; va_overlap_why: string | null
  hvn_jaccard: number | null; hvn_jaccard_why: string | null
  lvn_jaccard: number | null; lvn_jaccard_why: string | null
  exact_frac: number | null; exact_frac_why: string | null
  hidden_frac: number | null; hidden_frac_why: string | null
  unknown_frac: number | null; unknown_frac_why: string | null
}
export interface UxImpact { lambda: number | null; lots_per_tick: number | null; pct: number | null; n: number; why: string | null; tag: 'I' }
export interface TapeUx {
  src: 'ux'; tag: 'I'
  bars: UxBarRow[]; forming: UxBarRow | null
  levels: { session: { poc: number; vah: number; val: number } | null; nodes: TapeNode[]; why: string | null }
  marks: { runs: UxRun[]; runs_why: string | null }
  impact: UxImpact | null
  agree: UxAgree | null; agree_why: string | null
  book_from: string | null; frames_per_s: number | null; lot: number | null; lot_src: string | null
  why: string | null
}

/** The one legend line for the Upstox family (spec 2 §F). Pure: a string off the wire, three
 *  sentences where the wire says so, never a verdict. */
export function uxLegend(ux: TapeUx | null | undefined, runsDrawn: number, runsServed: number): string {
  if (!ux) return 'Upstox tape: reply mein ux object nahi aaya'
  if (ux.why) return `Upstox tape: ${ux.why}`
  const pct = (v: number | null) => (v == null ? '—' : `${Math.round(v * 100)} %`)
  const head = `Upstox tape (ux · ${ux.bars.length} bars · ${ux.frames_per_s ?? '—'} frames/s · book from ${ux.book_from ?? '—'} · lot ${ux.lot ?? '—'}${ux.lot_src ? ` (${ux.lot_src})` : ''}) [I]`
  const a = ux.agree
  const agree = a
    ? ` · ux vs ofd: POC ±${a.poc_rows_median ?? '—'} rows (median) · VA overlap ${pct(a.va_overlap)} · delta sign ${pct(a.delta_sign_agree)} · vol ×${a.vol_ratio_median == null ? '—' : a.vol_ratio_median.toFixed(2)} · hidden ${pct(a.hidden_frac)} · unknown ${pct(a.unknown_frac)} [M]`
    : ` · ${ux.agree_why ?? 'agreement: wajah nahi mili'}`
  const runs = ` · runs ${runsDrawn} of ${runsServed} bane${runsServed === 0 && ux.marks.runs_why ? ` (${ux.marks.runs_why})` : ''} [I]`
  const im = ux.impact
  const lam = im && im.lots_per_tick != null
    ? ` · λ 1 tick / ~${im.lots_per_tick.toFixed(1)} lots${im.pct != null ? ` (pct ${im.pct.toFixed(2)})` : ''} [I]`
    : ` · λ: ${im?.why ?? 'gauge nahi mila'}`
  return head + agree + runs + lam
}
```

In `TapeMark`, change `src: 'ofd' | 'tm'` to `src: 'ofd' | 'tm' | 'ux'`. In `TapeReply`, after `marks: {...}`, add `ux: TapeUx`.

- [ ] **Step 2: `LevelsOverlay.ts`**

`MARK_PRIO` (`:1115`) gains `run: 4`. `TM_LETTER` (`:1196`) gains `run: 's'`.

`printsCounts` returns two more numbers:

```ts
export function printsCounts(
  reply: TapeReply | null, tCut: number,
): { tmServed: number; tmDrawn: number; stacks: number; unfinished: number; runsServed: number; runsDrawn: number } {
  let tmDrawn = 0
  let stacks = 0
  let unfinished = 0
  let runsDrawn = 0
  for (const m of reply?.marks.tm ?? []) {
    if (m.p == null || !Number.isFinite(m.p) || m.t > tCut) continue
    tmDrawn++
  }
  for (const r of reply?.ux?.marks.runs ?? []) {
    if (r.p == null || !Number.isFinite(r.p) || r.to_t > tCut) continue
    runsDrawn++
  }
  for (const b of reply?.bars ?? []) {
    if (b.t > tCut) continue
    stacks += b.stacks?.length ?? 0
    if (b.unfinished_high) unfinished++
    if (b.unfinished_low) unfinished++
  }
  return { tmServed: reply?.marks.tm.length ?? 0, tmDrawn, stacks, unfinished,
           runsServed: reply?.ux?.marks.runs.length ?? 0, runsDrawn }
}
```

`drawPrints` — after the `// session value area and POC` block (`:1281–1285`), add:

```ts
  // the Upstox family's session levels: same colours, DOTTED, labelled ux, placed by
  // the same de-clutter so they never overprint the solid ones (spec 2 §F)
  const U = reply.ux
  if (U && !U.why && U.levels.session) {
    line(U.levels.session.vah, withAlpha(pal.textMuted, 0.7), [2, 3], `VAH ux ${U.levels.session.vah}`)
    line(U.levels.session.val, withAlpha(pal.textMuted, 0.7), [2, 3], `VAL ux ${U.levels.session.val}`)
    line(U.levels.session.poc, withAlpha(pal.accent, 0.75), [2, 3], `POC ux ${U.levels.session.poc}`)
  }
```

In the tm block, where `tmBy` is filled from `reply.marks.tm` (`:1337–1342`), also feed the runs as marks:

```ts
  const asMarks: TapeMark[] = [
    ...reply.marks.tm,
    ...((reply.ux && !reply.ux.why) ? reply.ux.marks.runs : []).map((r): TapeMark => ({
      t: r.to_t, kind: 'run', side: r.side, p: r.p, size: r.qty, src: 'ux', why: r.why, tag: 'I',
    })),
  ]
  for (const m of asMarks) {
    if (m.p == null || !Number.isFinite(m.p) || m.t > tCut) continue
    const g = tmBy.get(m.t)
    if (g) g.push(m)
    else tmBy.set(m.t, [m])
  }
```

(replacing the existing `for (const m of reply.marks.tm)` loop). In the glyph `if/else` chain, add a `run` shape before the diamond `else`:

```ts
      } else if (m.kind === 'run') {            // ring: three prints, one press
        ctx.arc(xs, y, u * 0.8, 0, Math.PI * 2)
```

and its `ext`: `m.kind === 'run' ? u * 0.8 :` inserted into the `ext` expression before the final `u`.

`printsKey` (`:1623`) becomes:

```ts
    const printsKey = prints
      ? `${prints.src}:${prints.bars.length}:${prints.forming?.t ?? ''}:${prints.forming?.vol ?? ''}:${prints.marks.tm.length}`
        + `:${prints.ux?.bars.length ?? 'x'}:${prints.ux?.forming?.t ?? ''}:${prints.ux?.marks.runs.length ?? 'x'}:${prints.ux?.marks.runs.at(-1)?.n ?? ''}`
      : 'x'
```

- [ ] **Step 3: Typecheck**

Run: `cd ui-v2 && npx tsc --noEmit`
Expected: exit 0. (Every `printsCounts` caller destructures named fields, so the two new ones break nothing.)

- [ ] **Step 4: Commit**

```bash
git add ui-v2/src/trade/tape.ts ui-v2/src/trade/LevelsOverlay.ts
git commit -m "ui-v2: the ux family on the wire -- dotted session levels, run rings, drawn-of-served for runs, one legend string

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 15: ui-v2 — the `Δ ux` line, the legend line, the hover rows

**Files:**
- Modify: `ui-v2/src/trade/indicators.ts` (`alignDelta :243`, `buildIndicators :269–298`), `ui-v2/src/trade/TradeTab.tsx` (`printCount` memo `:531–539`, the legend block `:1054–1075`), `ui-v2/src/trade/ContractChart.tsx` (`:305–323`), `ui-v2/src/trade/Callout.tsx` (props `:26–30`, rows `:274–291`)
- Test: `cd ui-v2 && npx tsc --noEmit`

**Interfaces:**
- Consumes: `TapeUx`, `UxRun`, `UxBarRow`, `uxLegend`, `printsCounts` (Task 14).
- Produces: the delta pane's second output `delta_ux` (line), the legend's second line, Callout props `runs?: UxRun[]`, `uxBar?: UxBarRow | null`.

- [ ] **Step 1: `indicators.ts`**

`alignDelta` reads either family:

```ts
export function alignDelta(
  bars: TapeBar[], prints: TapeReply | null | undefined, interval: number | null | undefined,
  source: 'ofd' | 'ux' = 'ofd',
): { delta: (number | null)[]; cvd: (number | null)[] } | null {
  if (!prints || (interval !== 5 && interval !== 15)) return null
  const rows = source === 'ux' ? (prints.ux && !prints.ux.why ? prints.ux.bars : []) : prints.bars
  if (!rows.length) return null
  const per = new Map<string, number>()        // record label -> delta
  for (const b of rows) per.set(hhmmOf(b.t), b.delta)
  // ... the rest of the function unchanged ...
```

`buildIndicators` — after `const dc = alignDelta(bars, prints, publishedInterval)`:

```ts
  const du = alignDelta(bars, prints, publishedInterval, 'ux')
  if (dc) {
    const last = [...dc.delta].reverse().find((v) => v != null)
    const lastU = du ? [...du.delta].reverse().find((v) => v != null) : undefined
    out.push({
      instanceId: 'delta', placement: 'pane',
      label: `Δ prints [M] · last ${last == null ? '—' : (last > 0 ? '+' : '') + last} lots · CVD ${dc.cvd[dc.cvd.length - 1] ?? '—'}`
        + (du ? ` · Δ ux [I] last ${lastU == null ? '—' : (lastU > 0 ? '+' : '') + Math.round(lastU)} lots` : ' · Δ ux: is din ka ux record nahi'),
      outputs: [
        { name: 'delta', values: dc.delta, color: (last ?? 0) >= 0 ? DELTA_UP : DELTA_DOWN, style: 'histogram' },
        { name: 'cvd', values: dc.cvd, color: OI_LINE },
        ...(du ? [{ name: 'delta_ux', values: du.delta, color: UX_LINE, style: 'line' as const }] : []),
      ],
    })
  }
```

with `const UX_LINE = '#b388ff'` beside `DELTA_UP`. (The `IndicatorRenderData.outputs[].style` union is `'line' | 'histogram'` — `vendor/candl/indicators/types.ts:6`, untouched.)

- [ ] **Step 2: `TradeTab.tsx`**

Import `uxLegend` from `./tape`. Directly after the `Prints (ladder record, /api/tape):` legend `<div>` (`:1075`), add:

```tsx
      {day && tape.reply && (
        <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2 }}>
          {uxLegend(tape.reply.ux, printCount.runsDrawn, printCount.runsServed)}
        </div>
      )}
```

(`printCount` already comes from `printsCounts`, which Task 14 extended.)

- [ ] **Step 3: `ContractChart.tsx` and `Callout.tsx`**

`ContractChart.tsx`, beside `tmHere` (`:305`):

```tsx
  const runsHere = prints?.ux && !prints.ux.why && hoverT != null && hoverTNext != null
    ? prints.ux.marks.runs.filter((r) => r.to_t >= hoverT && r.to_t < hoverTNext) : []
  const uxBarHere = prints?.ux && !prints.ux.why && hoverT != null
    ? (prints.ux.bars.find((b) => b.t === hoverT) ?? null) : null
```

and pass `runs={runsHere}` and `uxBar={uxBarHere}` to `<Callout>`.

`Callout.tsx` props:

```ts
  /** The Upstox family's runs that completed inside this bar's span (each with a `why`). */
  runs?: UxRun[]
  /** The Upstox ladder's own bar, for the residual sentence. */
  uxBar?: UxBarRow | null
```

(import `UxRun`, `UxBarRow` from `./tape`; add `runs, uxBar` to the destructured props.) The marks section's condition becomes `((tm && tm.length) || (ofd && ofd.length) || (runs && runs.length) || uxBar)` and inside it, after the `tm` rows:

```tsx
          {runs?.map((r, i) => (
            <div key={`r${i}`} style={{ fontSize: 11, color: pal.textSecondary, lineHeight: 1.4 }}>
              run{r.p != null ? ` @ ${r.p}` : ''} · {r.n} {r.side === 1 ? 'buys' : 'sells'} · tapemap (ux) [I] — {r.why}
            </div>
          ))}
          {uxBar && uxBar.vol > 0 && (uxBar.hidden ?? 0) / uxBar.vol > 0.5 && (
            <div style={{ fontSize: 11, color: pal.caution, lineHeight: 1.4 }}>
              {/* spec 2 §F: a ladder built mostly by residual must not read like one built by proof */}
              ux ladder here is mostly residual — the visible book explained {Math.round(100 * (1 - (uxBar.hidden ?? 0) / uxBar.vol))} %
            </div>
          )}
          {uxBar?.partial && (
            <div style={{ fontSize: 11, color: pal.textMuted, lineHeight: 1.4 }}>ux bar partial — {uxBar.partial_why}</div>
          )}
```

Use `pal.caution` if the palette has it (it does: the REPLAY badge uses `T.caution`); else `pal.textMuted`.

- [ ] **Step 4: Typecheck**

Run: `cd ui-v2 && npx tsc --noEmit`
Expected: exit 0

- [ ] **Step 5: Commit**

```bash
git add ui-v2/src/trade/indicators.ts ui-v2/src/trade/TradeTab.tsx ui-v2/src/trade/ContractChart.tsx ui-v2/src/trade/Callout.tsx
git commit -m "ui-v2: the ux delta line on the pane, the agreement line in the legend, runs and the residual sentence on hover

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 16: Docs, registrations, the spec amendment, the handoff

**Files:**
- Modify: `context/HANDOFF.md` (new entry above the 2026-09-19 one at `:179`), `START-HERE.md:180` (two lines beside `tape_log.py`), `START-HERE.md` and `CLAUDE.md:58` (the count sentences), `docs/superpowers/specs/2026-09-20-upstox-tape-design.md` (§F amendment), `.gitignore` (already done in Task 3 — verify)
- Test: `python -m pytest test_docs_claims.py -q`

- [ ] **Step 1: The spec amendment (§F, "Hidden-heavy bars")**

Replace the paragraph with:

> **Hidden-heavy bars.** Spec 1 draws no per-bar POC mark, so there is nothing to draw hollow (found at Task 15). The Callout carries the sentence instead: *"ux ladder here is mostly residual — the visible book explained NN %"* when `hidden / vol > 0.5`, and *"ux bar partial — <why>"* when the bar is partial. A ladder built mostly by residual must not read like one built by proof.

- [ ] **Step 2: `START-HERE.md:180`** — after the `tape_log.py` line add:

```
book_log.py  data/book/  (the book record: every changed frame of each index future off the socket, write-once by t)
ux_log.py    data/tape/ux_<idx>_<day>.jsonl  (the Upstox ladder, derived by ladder.py, written once at bin close; gate.py measures it against GoCharting's)
```

- [ ] **Step 3: The counts** — run `python -m pytest -q 2>&1 | tail -1`, then set `CLAUDE.md:58` to `# <collected> collected, <passed> passing, 3 pre-existing failures in test_desk_numbers.py (theta_day_est returns None -- the desk's code, untouched by this work), as of 2026-09-2x` and the matching sentence in `START-HERE.md` (grep `passing` to find it; it was `:233` on 2026-09-19).

- [ ] **Step 4: `context/HANDOFF.md`** — a new entry above `### 2026-09-19 — the ladder record...`, titled `### 2026-09-2x — the Upstox tape: the book record, the ux ladder and the gate (spec 2026-09-20-upstox-tape)`, in the 2026-09-19 entry's voice, covering in this order: the baseline (still 3 red in `test_desk_numbers.py`); what shipped (each module in one sentence with its file and the wire object); **what was seen live: nothing yet** and the exact before-next-session list — (a) restart the server DETACHED (`START-HERE.md` §0.6), (b) `/api/health` → `coverage.book` shows `from` per index within a minute of the open and `dropped` stays 0, (c) after the first bar closes, `/api/tape?idx=NIFTY` carries `ux.bars` and the legend's second line prints the agreement numbers, (d) count the run rings against `runs N of M bane`, (e) `python tools/gate_report.py NIFTY <day>` after close; **the measurements this spec owes and where they land**: frames per second per instrument (`ux.frames_per_s`), the day's book file size (`ls -la data/book/`), `levels_seen` (5 or 30 — the `full_d30` question), `exact_frac` / `hidden_frac` / `unknown_frac` on day one; the §F amendment; and the reminder that §K step 2 is hers after five sessions and nothing here prints a verdict.

- [ ] **Step 5: Run the docs pin and the whole suite**

Run: `python -m pytest -q 2>&1 | tail -3`
Expected: `<N> passed, 3 failed` (the three pre-existing), `test_docs_claims.py` green.

- [ ] **Step 6: Commit**

```bash
git add context/HANDOFF.md START-HERE.md CLAUDE.md docs/superpowers/specs/2026-09-20-upstox-tape-design.md
git commit -m "docs: the Upstox tape -- handoff entry, the two record lines, the real test count, and the §F amendment

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Self-review (done at authoring, 2026-09-20)

- **Spec coverage.** §B → Tasks 1–3; §C → 4, 6, 7 (+5 for lot/tick); §D → 9; §E → 8, 12; §F → 14, 15 (with the §F amendment in 16); §G → 10, 11; §H → each task's tests; §I → nothing built (`full_d30` measured via `levels_seen`; no legs, no episodes, no heatmap); §J.1 → Task 1's hook placement; §J.2 → `Ladder.step`'s `t_bin`; §J.3 → `attribute`; §J.4/5 → `gate`; §J.6/7 → `runs`; §J.9 → `impact.lots_per_tick`; §J.10 → `ux_log.day_path`; §J.11 → `u`; §J.12 → `lot_src`/`tick_src`; §K → `tools/gate_report.py` and the HANDOFF reminder. `TAPE_SOURCE` (§K.3) is deliberately NOT built: it follows her bar.
- **Type consistency.** `book_log` row keys (`t, cts, ltt, ltp, ltq, vtt, oi, tbq, tsq, b, a`) are what `ladder.attribute`/`Ladder.step`, `impact.on_frame` and the tests' `R()` use. `Ladder.step` returns `(bar | None, fills)` with fills `{ltt, side, p, q, hidden}` — what `runs.on_fill` and `impact.on_frame` read. `ux_log.on_frames(rows, day, lot, tick, observer)` matches Task 12's call. `gate.session` fields match `UxAgree` in `tape.ts` and `FIELDS` in `gate_report.py`. `runs` events carry `p` (added for the glyph) and `to_t` (the glyph's `t`).
- **Known deviation from the spec, recorded:** §E lists `unknown` inside the ux bar row — it is there; §C's "`rowSize` null on the record" — implemented; §F "POC row drawn hollow" — replaced by the Callout sentence (Task 16 amends the spec).
