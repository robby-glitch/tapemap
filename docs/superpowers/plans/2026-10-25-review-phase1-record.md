# Review 25 Oct, Phase 1: The Record — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four holes in TapeMap's forward record, spec F1–F5 (`docs/superpowers/specs/2026-10-25-review-fix-cut-stop-design.md` §1, Phase 1):
- cross-index frame scores;
- a hollow bar killing the day's scoring;
- a feed gap booked as a fake one-sided print;
- unlocked `day_state` / `tape_log` writes.

**Architecture:** Five surgical server-side fixes, each pinned by a test that fails today.
- **The frame scorer:** filters rows by the posting index, and skips bars with no close.
- **The ux ladder:** treats a jump of more than 30 s in the feed's own clock (`cts`) as a gap, booked to no side and no price. The bar is marked partial with a why.
- **VPIN:** re-arms on the same 30 s bound, measured on the exchange `ltt`.
- **`day_state` and `tape_log`:** each gets one module lock.
- **A read-only tool:** lists the past slug bars. It rewrites nothing.

No face changes, and no registered rule changes.

**Tech Stack:** Python 3.13 (`C:\Python313`), stdlib only, pytest.

## Global Constraints

- **Paths and baseline.** Repo `C:\Users\kaam\Desktop\operator mode\tapemap`, branch `feature/operator-objects`. Run everything from the repo root.
  - Suite command: `python -m pytest -q`.
  - Baseline: 1944 collected = 1942 pass, 1 skipped, 1 known flaky (`test_v2feed.py::test_serve_caches_full_and_answers_delta`, NOTEPAD A49, passes alone).
- **Market hours.**
  - Never start, stop or restart the TapeMap server. Mary starts it herself; server changes go live at her restart after a close.
  - Don't edit files the live server imports between 09:15 and 15:40 IST, Mon–Fri.
- **Data.** Never write, move or delete anything under `data/`. Tests use `tmp_path` / `monkeypatch.chdir(tmp_path)` only. `tools/gap_slugs.py` only reads.
- **Editing.**
  - The repo mixes LF and CRLF. Edit with exact-string replacements only: no reformatting, renames or line-ending churn.
  - After each task, `git diff --stat` must show only the lines that task changed. If a file shows far more, its line endings flipped: redo that edit byte-safely.
- **Never touch:**
  - registered rules §1i–§1q;
  - `engine.py`, `band_rotation.py`, `fronts.py`, `signals.py`, `frame.py`;
  - any forward log's existing rows;
  - `data/trigger_log.jsonl`.
- **Commits.** No commit per task. Task 8 commits the whole phase **only after Mary says commit**. The commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Numbers and the gap bound.**
  - Numbers in docs are tagged [M] measured or [I] inferred. Never a win / hit rate.
  - **`GAP_MS = 30_000`**: a gap is more than 30 s on the feed's own clock. Measured 25 Oct [M]: 0 such gaps on the clean 23 Oct; it catches 16 Oct 11:12 (5,035 s, 934,635 units) and 12 Oct 12:58 (5,862 s). There were about 26 gaps a day over 5 s, so 5 s would flag quiet markets.
  - Rows whose `cts` is None never read as a gap. Every existing test row uses `cts: None`.

---

### Task 1: The frame scorer scores only the posting index's rows (F1, A65)

**Files:**
- Modify: `score_frame.py:85` (`write` signature, docstring) and `score_frame.py:103` (`rows = score(rows, bars)`)
- Modify: `server.py:4754`
- Test: `test_score_frame.py` (append)

**Interfaces:**
- Produces: `score_frame.write(day: str, bars: List[dict], path: Optional[str] = None, idx: Optional[str] = None) -> int`. With `idx=None` it behaves exactly as today.

- [ ] **Step 1: Write the failing test.** Append to `test_score_frame.py`:

```python
def test_write_scores_only_the_posting_index_rows(tmp_path):
    """25 Oct review D1 / A65: the day file holds every index, but the POST's bars belong to one. A SENSEX row
    filled from NIFTY's bars is a wrong outcome, written once and never corrected."""
    import json
    p = tmp_path / "frame_2026-09-11.jsonl"
    p.write_text(json.dumps(ROW) + "\n" + json.dumps(dict(ROW, idx="SENSEX")) + "\n", encoding="utf-8")
    score_frame.write("2026-09-11", BARS, path=str(p), idx="NIFTY")
    out = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
    assert out[0]["taps"][0]["ex"]["1"] == 1.0
    assert out[1]["taps"][0]["ex"] == {} and "resolved" not in out[1]["setup"]["tells"][0]
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_score_frame.py::test_write_scores_only_the_posting_index_rows`
Expected: FAIL with `TypeError: write() got an unexpected keyword argument 'idx'`

- [ ] **Step 3: Implement.** In `score_frame.py`, replace

```python
def write(day: str, bars: List[dict], path: Optional[str] = None) -> int:
    """Rescore the day's file in place. The read and the scoring run outside frame_log.LOCK (seconds on a 200 MB
```

with

```python
def write(day: str, bars: List[dict], path: Optional[str] = None, idx: Optional[str] = None) -> int:
    """Rescore the day's file in place, only the rows of `idx` (the index whose bars these are; the day file holds
    every index -- 25 Oct review D1). The read and the scoring run outside frame_log.LOCK (seconds on a 200 MB
```

Then replace

```python
    rows = score(rows, bars)
```

with

```python
    mine = rows if idx is None else [r for r in rows if r.get("idx") == idx]
    score(mine, bars)                                 # in place: another index's rows are written back untouched
```

In `server.py`, replace

```python
                        score_frame.write(day, doc.get("closed") or [])
```

with

```python
                        score_frame.write(day, doc.get("closed") or [], idx=idx)
```

- [ ] **Step 4: Run the file and see it pass.**

Run: `python -m pytest -q test_score_frame.py test_frame_api.py`
Expected: all pass. `test_frame_api.py`'s fake `write` takes `**k`, so the new keyword is accepted. `test_write_survives_a_torn_line…` still passes because `score` fills rows in place.

---

### Task 2: A hollow bar never stops the day's scoring (F2, A66)

**Files:**
- Modify: `score_frame.py:29-52` (`_fill_tap`, `_resolve`)
- Test: `test_score_frame.py` (append)

**Interfaces:** none new.

- [ ] **Step 1: Write the failing test.** Append to `test_score_frame.py`:

```python
def test_a_hollow_bar_skips_its_own_cell_and_never_stops_the_rest():
    """25 Oct review D4 / A66: one bar with no close made every write that day raise (45 failures on 9 Oct,
    19 on 19 Oct), so nothing after it was ever scored."""
    bars = copy.deepcopy(BARS)
    bars[8]["c"] = None                                   # the tap's i0 5 + 3
    out = score_frame.score([copy.deepcopy(ROW)], bars)
    ex = out[0]["taps"][0]["ex"]
    assert ex["1"] == 1.0 and ex["6"] == 6.0 and "3" not in ex
    assert out[0]["setup"]["tells"][0]["resolved"] == "target"
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_score_frame.py::test_a_hollow_bar_skips_its_own_cell_and_never_stops_the_rest`
Expected: FAIL with `TypeError: unsupported operand type(s) for -: 'NoneType' and 'float'`

- [ ] **Step 3: Implement.** In `score_frame.py`, replace

```python
    c0, side = bars[i0]["c"], tp.get("side") or 1
    ex = tp.setdefault("ex", {})
    for n in HORIZ_BARS:
        key = str(n)
        if key not in ex and i0 + n < len(bars):
            ex[key] = round(side * (bars[i0 + n]["c"] - c0), 1)
    for mins in HORIZ_MIN:
        key = f"{mins}m"
        j = i0 + mins // 5
        if key not in ex and j < len(bars):
            ex[key] = round(side * (bars[j]["c"] - c0), 1)
```

with

```python
    c0, side = bars[i0]["c"], tp.get("side") or 1
    if c0 is None:
        return                                        # a hollow tap bar: nothing to measure from (D4)
    ex = tp.setdefault("ex", {})
    for n in HORIZ_BARS:
        key = str(n)
        if key not in ex and i0 + n < len(bars) and bars[i0 + n]["c"] is not None:
            ex[key] = round(side * (bars[i0 + n]["c"] - c0), 1)
    for mins in HORIZ_MIN:
        key = f"{mins}m"
        j = i0 + mins // 5
        if key not in ex and j < len(bars) and bars[j]["c"] is not None:
            ex[key] = round(side * (bars[j]["c"] - c0), 1)
```

Then replace

```python
    for b in after:
        if target is not None and ((up and b["c"] >= target) or (not up and b["c"] <= target)):
```

with

```python
    for b in after:
        if b["c"] is None:
            continue                                  # a hollow bar answers nothing (D4)
        if target is not None and ((up and b["c"] >= target) or (not up and b["c"] <= target)):
```

- [ ] **Step 4: Run the file and see it pass.**

Run: `python -m pytest -q test_score_frame.py`
Expected: all pass.

---

### Task 3: A feed gap is booked to no side in the ux ladder (F3 part 1, A67)

**Files:**
- Modify: `ladder.py`:
  - the module docstring (after the `V == 0` line);
  - the constants (after `INTERVAL_S = 300`);
  - `attribute` (after the `quiet` return);
  - `Ladder._open`, `Ladder._close`, `Ladder.step`.
- Test: `test_ladder.py` (append)

**Interfaces:**
- Produces:
  - `ladder.GAP_MS: int = 30_000`, used by Task 4 and Task 5;
  - `attribute()` can return `{"kind": "gap", "V": int, "gap_s": int, "fills": [], ...}`;
  - the bar dict gains `"feed_gaps": int` and `"gap_vol": float` (lots);
  - `partial_why` starts with `"feed gap {N}s"`.

- [ ] **Step 1: Write the failing tests.** Append to `test_ladder.py`:

```python
def test_a_feed_gap_books_nothing_and_marks_the_bar_partial():
    """25 Oct review D3 / A67: after a dropped socket, the whole gap's volume used to land as ONE print on one
    side (16 Oct 11:10: delta +14,461 lots against a 779-lot median bar). The feed's own clock says it was a gap."""
    prev = dict(R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]), cts=T0 + 1000)
    cur = dict(R(T0 + 91_000, 14_975, 100.05, 65, [[100.00, 65]], [[100.05, 65]]), cts=T0 + 91_000)
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "gap" and r["V"] == 13_975 and r["fills"] == [] and r["gap_s"] == 90
    L = ladder.Ladder(lot=65, tick=0.05, idx="NIFTY", day="2026-09-11")
    L.step(prev)
    L.step(cur)
    bar = L.close_open()
    assert bar["vol"] == 0 and bar["delta"] == 0 and bar["feed_gaps"] == 1 and bar["gap_vol"] == 215
    assert bar["partial"] is True and bar["partial_why"].startswith("feed gap 90s")


def test_rows_without_the_feed_clock_never_read_as_a_gap():
    """Guard: test rows and old files carry cts None, so the rule stays off rather than guess from arrival time."""
    prev = R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(T0 + 291_000, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]])
    assert ladder.attribute(prev, cur, 0.05)["kind"] == "exact"
```

- [ ] **Step 2: Run them and see the first fail.**

Run: `python -m pytest -q test_ladder.py -k "feed_gap or feed_clock"`
Expected: `test_a_feed_gap_books_nothing…` FAILS (`kind` is `recon`/`exact`, not `gap`). The guard test passes (it pins today's behaviour).

- [ ] **Step 3: Implement.** In `ladder.py`, make six replacements.

**(a) The module docstring.** Replace

```python
  V == 0       nothing traded: nothing attributed (depth_pull owns the book).
```

with

```python
  V == 0       nothing traded: nothing attributed (depth_pull owns the book).
  cts jump     a GAP (25 Oct, A67): the feed's own clock moved > GAP_MS between the
               two rows -- a dropped socket or a restart. V traded unseen: booked to
               no side and no price, counted, and the bar is marked partial.
```

**(b) The constant.** Replace

```python
INTERVAL_S = 300
```

with

```python
INTERVAL_S = 300
GAP_MS = 30_000           # ponytail: one bound for every index; 0 such gaps on 23 Oct, the 12/16 Oct slugs caught [M]
```

**(c) `attribute`.** Replace

```python
    if V == 0:
        return _empty("quiet")
```

with

```python
    if V == 0:
        return _empty("quiet")
    if prev.get("cts") is not None and cur.get("cts") is not None and cur["cts"] - prev["cts"] > GAP_MS:
        r = _empty("gap", V)
        r["gap_s"] = int((cur["cts"] - prev["cts"]) // 1000)
        return r
```

**(d) `_open`.** Replace

```python
                    "vtt_resets": 0, "levels_seen": 0, "first_ms": None, "late_frames": 0}
```

with

```python
                    "vtt_resets": 0, "levels_seen": 0, "first_ms": None, "late_frames": 0,
                    "gaps": 0, "gap_vol": 0, "gap_s": 0}
```

**(e) `_close`.** Replace

```python
        if a["vtt_resets"]:
            why = f"vtt reset {a['vtt_resets']} time(s) inside the bar"
```

with

```python
        if a["vtt_resets"]:
            why = f"vtt reset {a['vtt_resets']} time(s) inside the bar"
        elif a["gaps"]:
            why = f"feed gap {a['gap_s']}s: {round(a['gap_vol'] / div, 1)} lots traded unseen, not placed"
```

Then replace

```python
               "hidden": a["hidden"] / div, "vtt_resets": a["vtt_resets"], "lot_mismatch": mismatch,
```

with

```python
               "hidden": a["hidden"] / div, "vtt_resets": a["vtt_resets"], "lot_mismatch": mismatch,
               "feed_gaps": a["gaps"], "gap_vol": a["gap_vol"] / div,
```

**(f) `step`.** Replace

```python
        if res["kind"] == "reset":
            a["vtt_resets"] += 1
```

with

```python
        if res["kind"] == "reset":
            a["vtt_resets"] += 1
        if res["kind"] == "gap":                      # A67: no side, no price, no ladder row -- counted and said
            a["gaps"] += 1
            a["gap_vol"] += res["V"]
            a["gap_s"] = max(a["gap_s"], res["gap_s"])
```

- [ ] **Step 4: Run the ladder and ux files and see them pass.**

Run: `python -m pytest -q test_ladder.py test_ux_log.py test_book_wiring.py test_gate_report.py test_frame_api.py`
Expected: all pass. Their synthetic rows use `cts: None`, so nothing in them reads as a gap.

---

### Task 4: VPIN re-arms on a feed gap (F3 part 2, A67)

**Files:**
- Modify: `upstox_adapter.py` (add `ltt_of` after `ltp_of`).
- Modify: `vpin.py`:
  - the imports;
  - `Gauge.__init__`;
  - `Gauge.on_frame`.
- Modify: `server.py:843-845` and `server.py:858-860`.
- Test: `test_vpin.py` (append) and `test_upstox_adapter.py` (append).

**Interfaces:**
- Consumes: `ladder.GAP_MS` (Task 3).
- Produces:
  - `upstox_adapter.ltt_of(feed) -> Optional[int]`;
  - `vpin.Gauge.on_frame(ltp, vtt, stamp="", t_ms=None) -> List[Dict]`;
  - `vpin.Gauge.gaps: int`.

The 1-min backfill (`vpin.py:285-288`) passes no `t_ms` and is unchanged.

- [ ] **Step 1: Write the failing tests.** Append to `test_vpin.py`:

```python
def test_a_feed_gap_rearms_and_books_nothing():
    """25 Oct review D3 / A67: on reconnect, the whole gap's volume used to close buckets on one side."""
    g = _gauge(v=100)
    g.on_frame(100.0, 0, t_ms=0)
    g.on_frame(101.0, 0, t_ms=1_000)                      # uptick: sign = buy
    assert g.on_frame(101.0, 5_000, t_ms=91_000) == []    # 90 s on the exchange clock: 50 buckets' worth, booked nowhere
    assert g.gaps == 1 and g.buckets == 0
    assert len(g.on_frame(101.0, 5_100, t_ms=92_000)) == 1  # the next 100 close one bucket, as normal
```

Append to `test_upstox_adapter.py`:

```python
def test_ltt_of_reads_the_exchange_trade_time_in_ms():
    assert ua.ltt_of({"fullFeed": {"marketFF": {"ltpc": {"ltp": 1.0, "ltt": "1789098300000"}}}}) == 1789098300000
    assert ua.ltt_of({"fullFeed": {"marketFF": {"ltpc": {}}}}) is None
    assert ua.ltt_of(None) is None
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_vpin.py::test_a_feed_gap_rearms_and_books_nothing test_upstox_adapter.py::test_ltt_of_reads_the_exchange_trade_time_in_ms`
Expected: FAIL with `TypeError: on_frame() got an unexpected keyword argument 't_ms'` and `AttributeError: module 'upstox_adapter' has no attribute 'ltt_of'`.

- [ ] **Step 3: Implement.** Make four sets of replacements.

**(a) `upstox_adapter.py`.** Replace

```python
    return _num((core.get("ltpc") or {}).get("ltp"))
```

with

```python
    return _num((core.get("ltpc") or {}).get("ltp"))


def ltt_of(feed):
    """Last trade time (exchange epoch ms) out of any feed shape, or None -- VPIN's gap clock (A67)."""
    core = _core(feed)
    if not core:
        return None
    v = _num((core.get("ltpc") or {}).get("ltt"))
    return None if v is None else int(v)
```

(If that line is not unique, include the `def ltp_of(feed):` docstring line above it in the match.)

**(b) `vpin.py`.** Replace

```python
from typing import Dict, List, Optional
```

with

```python
from typing import Dict, List, Optional

from ladder import GAP_MS
```

Replace

```python
        self.resets = 0                # vtt went backwards
```

with

```python
        self.resets = 0                # vtt went backwards
        self.gaps = 0                  # the exchange clock jumped > GAP_MS: re-armed, booked nowhere (A67)
        self._t_ms: Optional[int] = None
```

Replace

```python
                 stamp: str = "") -> List[Dict]:
```

with

```python
                 stamp: str = "", t_ms: Optional[int] = None) -> List[Dict]:
```

Replace

```python
        if vtt is None:
            return []
        if self._vtt is None or vtt < self._vtt:   # first frame, or feed reset
```

with

```python
        if vtt is None:
            return []
        last_t = self._t_ms
        if t_ms is not None:
            self._t_ms = t_ms
        if self._vtt is None or vtt < self._vtt:   # first frame, or feed reset
```

Replace

```python
        dv, self._vtt = vtt - self._vtt, vtt
```

with

```python
        if t_ms is not None and last_t is not None and vtt > self._vtt and t_ms - last_t > GAP_MS:
            # A67: a dropped socket's whole gap would close buckets on one side. Re-arm, book nothing.
            self.gaps += 1
            self._vtt = vtt
            return []
        dv, self._vtt = vtt - self._vtt, vtt
```

**(c) `server.py`, the first call** (`gv`). Replace

```python
                                    for ev in gv.on_frame(
                                            upstox_adapter.ltp_of(frame),
                                            _v, stamp):
```

with

```python
                                    for ev in gv.on_frame(
                                            upstox_adapter.ltp_of(frame),
                                            _v, stamp, t_ms=upstox_adapter.ltt_of(frame)):
```

**(d) `server.py`, the second call** (`gf`). Replace

```python
                                    for ev in gf.on_frame(
                                            upstox_adapter.ltp_of(frame),
                                            _v, stamp):
```

with

```python
                                    for ev in gf.on_frame(
                                            upstox_adapter.ltp_of(frame),
                                            _v, stamp, t_ms=upstox_adapter.ltt_of(frame)):
```

- [ ] **Step 4: Run the VPIN and adapter files and see them pass.**

Run: `python -m pytest -q test_vpin.py test_vpin_backfill.py test_upstox_adapter.py test_book_wiring.py`
Expected: all pass.

---

### Task 5: A read-only list of the past slug bars (F3 part 3, A67)

**Files:**
- Create: `tools/gap_slugs.py`
- Test: `test_gap_slugs.py`

**Interfaces:**
- Consumes: `ladder.GAP_MS`, `ladder.bin_of`, `ladder.hms_ist`.
- Produces: `gap_slugs.main(days: set) -> None`. It prints a markdown table to stdout and writes nothing.

- [ ] **Step 1: Write the failing test.** Create `test_gap_slugs.py`:

```python
"""tools/gap_slugs.py lists, never rewrites: the ux bars a feed gap turned into a slug (25 Oct review, A67)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import gap_slugs  # noqa: E402


def test_lists_a_gap_with_volume_and_skips_a_clean_pair(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs("data/book")
    os.makedirs("data/tape")
    T0 = 1789098300000                                     # 09:15:00 IST
    rows = [{"t": T0 + 1000, "cts": T0 + 1000, "ltt": T0 + 1000, "vtt": 1000},
            {"t": T0 + 2000, "cts": T0 + 2000, "ltt": T0 + 2000, "vtt": 1065},      # clean: 1 s
            {"t": T0 + 92_000, "cts": T0 + 92_000, "ltt": T0 + 92_000, "vtt": 14_975}]  # 90 s gap
    with open("data/book/book_NIFTY_2026-09-11.jsonl", "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    with open("data/tape/ux_NIFTY_2026-09-11.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": T0, "delta": 215, "vol": 216}) + "\n")
    gap_slugs.main(set())
    out = capsys.readouterr().out.splitlines()
    assert out[2:] == ["| 2026-09-11 | NIFTY | 09:15 | 90s | 13910 | 215 | 216 |"]
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_gap_slugs.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'gap_slugs'`

- [ ] **Step 3: Implement.** Create `tools/gap_slugs.py`:

```python
"""gap_slugs.py -- READ-ONLY: list the ux bars a feed gap turned into a one-sided slug (25 Oct review, A67).

Before the fix, ladder.attribute booked a dropped socket's whole gap as ONE print on one side. This lists every
such pair in the book files -- the rule the fix uses: the feed clock `cts` jumped > ladder.GAP_MS with volume --
and the ux bar it landed in, so a reader of those days knows which bars to distrust. It never rewrites a file.

    python tools/gap_slugs.py              # every day on disk
    python tools/gap_slugs.py 2026-10-16   # one day (several may be given)
"""
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ladder  # noqa: E402


def _rows(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError:
                    continue                      # a torn line is skipped, never fatal


def _ux(day, idx):
    for p in (f"data/tape/ux_{idx}_{day}.jsonl", f"data/tape/ux_{idx}_{day}.jsonl.gz"):
        if os.path.exists(p):
            return {b["t"]: b for b in _rows(p) if b.get("t") is not None}
    return {}


def main(days):
    print("| day | idx | bar | gap | units | ux delta | ux vol |")
    print("|---|---|---|---|---|---|---|")
    for path in sorted(glob.glob("data/book/book_*_*.jsonl*")):
        _, idx, day = os.path.basename(path).split(".")[0].split("_")
        if days and day not in days:
            continue
        ux, prev = None, None
        for r in _rows(path):
            if prev and r.get("cts") and prev.get("cts") and r.get("vtt") and prev.get("vtt"):
                dv = r["vtt"] - prev["vtt"]
                if dv > 0 and r["cts"] - prev["cts"] > ladder.GAP_MS:
                    ux = _ux(day, idx) if ux is None else ux
                    t = ladder.bin_of(r.get("ltt") or r["t"])    # where the old code booked it
                    b = ux.get(t, {})
                    print(f"| {day} | {idx} | {ladder.hms_ist(t)[:5]} | {(r['cts'] - prev['cts']) // 1000}s "
                          f"| {dv} | {b.get('delta', '—')} | {b.get('vol', '—')} |")
            prev = r


if __name__ == "__main__":
    main(set(sys.argv[1:]))
```

- [ ] **Step 4: Run it and see it pass.**

Run: `python -m pytest -q test_gap_slugs.py`
Expected: PASS.

---

### Task 6: `day_state` saves under a lock; a torn file is kept and logged (F4, A68)

**Files:**
- Modify: `day_state.py`. Change the imports, and replace everything from `def save(` to the end of the file.
- Test: `test_day_state.py` (append). The existing tests stay unchanged and still pass. `test_missing_and_unreadable_both_start_the_day_cold` still gets `{}`; the torn file is now also kept aside.

**Interfaces:** `day_state.save(day, state, dir_=None) -> str` and `day_state.load(day, dir_=None) -> dict` keep their signatures. New module names: `day_state._LOCK` and `day_state.log` (the `"tapemap"` logger, the same one as `server.log`).

- [ ] **Step 1: Write the failing tests.** Append to `test_day_state.py`:

```python
# ---- one writer at a time; a torn file is evidence, not a missing one (25 Oct review D2 / A68) ------------

def test_two_threads_saving_at_once_leave_one_valid_file(tmp_path, monkeypatch):
    """Six server threads call save, and every one used the same .tmp name with no lock. On Windows a second
    open handle makes os.replace fail, or interleaved writes tear the file -- which then loads as {}."""
    import threading
    import time as _t
    real = day_state.json.dump

    def slow_dump(obj, fh):
        _t.sleep(0.05)                                  # hold the temp file open long enough to collide
        real(obj, fh)
    monkeypatch.setattr(day_state.json, "dump", slow_dump)
    errors = []

    def go(i):
        try:
            day_state.save("2026-08-25", {"hold_trades": [i]}, dir_=tmp_path)
        except Exception as e:                          # noqa: BLE001 -- the test collects whatever a thread raised
            errors.append(e)
    ts = [threading.Thread(target=go, args=(i,)) for i in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert errors == []
    assert day_state.load("2026-08-25", dir_=tmp_path)["hold_trades"] in ([0], [1], [2], [3])
    assert [p.name for p in tmp_path.iterdir()] == ["day_2026-08-25.json"]


def test_a_torn_file_is_kept_aside_and_logged_not_silently_lost(tmp_path, caplog):
    """A torn file used to load as {} with no log line, and the next save overwrote the trades it held. It
    still starts the day cold, but the file is kept and the log says so."""
    (tmp_path / "day_2026-08-25.json").write_text('{"day": "2026-08-25", "hold_trades": [{"id"', encoding="utf-8")
    with caplog.at_level("ERROR", logger="tapemap"):
        assert day_state.load("2026-08-25", dir_=tmp_path) == {}
    kept = [p.name for p in tmp_path.iterdir()]
    assert len(kept) == 1 and kept[0].startswith("day_2026-08-25.json.corrupt-")
    assert "unreadable" in caplog.text
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_day_state.py -k "two_threads or torn_file"`
Expected: both FAIL.
- The thread test fails with a `PermissionError` collected from a thread (Windows), or with a torn load.
- The torn-file test fails on `kept[0].startswith(...)`, because the file was never moved.

- [ ] **Step 3: Implement.** In `day_state.py`, replace

```python
import json
import os
import time

DIR = os.path.join("data", "day_state")
```

with

```python
import json
import logging
import os
import tempfile
import threading
import time

DIR = os.path.join("data", "day_state")
log = logging.getLogger("tapemap")
_LOCK = threading.Lock()   # ponytail: one lock for every day file -- six server threads save (25 Oct review D2)
```

Replace everything from `def save(day, state, dir_=None):` to the end of the file with:

```python
def save(day, state, dir_=None):
    """Write `state` as today's file, atomically. Returns the path.

    `state` is merged under the envelope (`day`, `saved_at`), so a caller adds
    a new series by adding a key -- no schema change here, and an older reader
    that does not know the key simply ignores it.

    One writer at a time, through a temp file of its own: six server threads
    call this, and a shared `.tmp` let two of them collide (25 Oct review D2).
    """
    p = path_for(day, dir_)
    parent = os.path.dirname(p)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with _LOCK:
        fd, tmp = tempfile.mkstemp(prefix=os.path.basename(p) + ".", suffix=".tmp", dir=parent or ".")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(dict(state, day=day, saved_at=time.time()), fh)
            os.replace(tmp, p)
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
    return p


def load(day, dir_=None):
    """Today's saved state, or `{}`.

    `{}` for missing, unreadable and belongs-to-another-day: in every case the
    day starts cold. But an UNREADABLE file is not a missing one -- it held her
    marked trades -- so it is moved aside as `<name>.corrupt-HHMMSS` and logged
    as an ERROR, never overwritten by the next save (25 Oct review D2).
    """
    p = path_for(day, dir_)
    try:
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError:
        return {}
    except ValueError:
        bad = f"{p}.corrupt-{time.strftime('%H%M%S')}"
        try:
            os.replace(p, bad)
        except OSError:
            bad = p
        log.error("day state %s is unreadable -- kept as %s; the day starts cold", p, bad)
        return {}
    return doc if isinstance(doc, dict) and doc.get("day") == day else {}
```

- [ ] **Step 4: Run the file and see it pass.**

Run: `python -m pytest -q test_day_state.py`
Expected: all pass, including `test_a_save_leaves_no_temp_file_behind` and the isolation tests.

---

### Task 7: `tape_log`'s write-once is one step under a lock (F5, A69)

**Files:**
- Modify: `tape_log.py`:
  - the imports (after `import os`);
  - after `failed = 0`;
  - `append` (lines 173-175).
- Test: `test_tape_log.py` (append)

**Interfaces:** `tape_log.append(doc, day, idx) -> dict` is unchanged. Its body moves to `tape_log._append`, unchanged, and is called under `tape_log._LOCK`.

- [ ] **Step 1: Write the failing test.** Append to `test_tape_log.py`:

```python
def test_two_posts_at_once_write_each_bar_once(tdir, monkeypatch):
    """25 Oct review D6 / A69: the seen-set was updated only after the write, so two frame POSTs on two server
    threads both wrote the same bars (41 duplicate rows over 8 NIFTY days)."""
    import threading
    import time
    real = tape_log._write_lines

    def slow(path, rows):
        time.sleep(0.05)                                 # widen the check-then-append window
        real(path, rows)
    monkeypatch.setattr(tape_log, "_write_lines", slow)
    doc = _doc(n=3)
    ts = [threading.Thread(target=tape_log.append, args=(doc, "2026-09-19", "NIFTY")) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert sorted(r["t"] for r in rows) == sorted(b["t"] for b in doc["closed"])
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_tape_log.py::test_two_posts_at_once_write_each_bar_once`
Expected: FAIL. 6 rows are written for 3 bars.

- [ ] **Step 3: Implement.** In `tape_log.py`, make three replacements.

Replace

```python
import json
import os
```

with

```python
import json
import os
import threading
```

Replace

```python
failed = 0
```

with

```python
failed = 0
_LOCK = threading.Lock()   # frame POSTs run on server threads: the seen-check and the append are one step (D6)
```

(If `failed = 0` is not unique, include the next line, `_seen_bars: Dict[Tuple[str, str], Set[int]] = {}`, in both strings.)

Replace

```python
def append(doc: dict, day: str, idx: str) -> dict:
    """Write the doc's new closed bars and new marks. Returns how many landed."""
    global failed
```

with

```python
def append(doc: dict, day: str, idx: str) -> dict:
    """Write the doc's new closed bars and new marks. Returns how many landed. Frame POSTs run on server
    threads, so the seen-check and the append happen as one step under _LOCK (25 Oct review D6)."""
    with _LOCK:
        return _append(doc, day, idx)


def _append(doc: dict, day: str, idx: str) -> dict:
    global failed
```

- [ ] **Step 4: Run the file and see it pass.**

Run: `python -m pytest -q test_tape_log.py test_frame_api.py`
Expected: all pass.

---

### Task 8: Verify the phase, record it, commit on her word

**Files:**
- Modify: `docs/live/NOTEPAD.md` (the A65–A69 statuses, plus the A67 slug table).
- Modify: `CLAUDE.md` (the test-count line under "Running it").

- [ ] **Step 1: Run the full suite.**

Run: `python -m pytest -q`
Expected: 1954 collected (1944 + 10 new) = 1952 pass, 1 skipped, and at most the 1 known flaky A49 test. Any other failure: stop, and fix the cause before going on.

- [ ] **Step 2: Check the diff is only these changes.**

Run: `git diff --stat`
Expected: changes only in `score_frame.py`, `server.py` (3 lines), `ladder.py`, `vpin.py`, `upstox_adapter.py`, `day_state.py`, `tape_log.py`, and the tests. New files: `tools/gap_slugs.py`, `test_gap_slugs.py`. No file shows a whole-file rewrite.

- [ ] **Step 3: List the past slugs (read-only).**

Run: `python -I tools/gap_slugs.py 2026-10-12 2026-10-16`
Expected: at least the rows `| 2026-10-12 | NIFTY | 12:55 | 5862s | 536575 | … |` and `| 2026-10-16 | NIFTY | 11:10 | 5035s | 934635 | … |`. Paste the table under NOTEPAD A67, tagged [M].

- [ ] **Step 4: Update NOTEPAD and CLAUDE.md.**
  - NOTEPAD A65–A69: change the Status to `FIXED (25 Oct, uncommitted, live at her restart)`, citing the test name.
  - `CLAUDE.md`, the pytest line: change the counts to 1954 collected, with the date.

- [ ] **Step 5: Show Mary, and wait for her word.** Show `git diff --stat` and the diff. Say plainly:
  - **What it changes on screen:** nothing.
  - **What changes in the logs:**
    - frame rows of other indices stop getting wrong scores;
    - ux bars after a socket drop are partial with a why, instead of a giant one-sided print;
    - VPIN skips the gap;
    - a torn `day_state` file is kept.
  - **What stays untouched:** the rules §1i–§1q, the engine, the zone machine, the §1d gate, past log rows, `trigger_log`.
  - **When it goes live:** at her next restart after a close.
  - **One trader-visible effect:** the bar right after a feed drop shows less delta (the slug is gone). That is the point.

- [ ] **Step 6: Commit, ONLY after she says commit.**

```bash
git add score_frame.py server.py ladder.py vpin.py upstox_adapter.py day_state.py tape_log.py tools/gap_slugs.py test_score_frame.py test_ladder.py test_vpin.py test_upstox_adapter.py test_gap_slugs.py test_day_state.py test_tape_log.py docs/live/NOTEPAD.md CLAUDE.md docs/superpowers/specs/2026-10-25-review-fix-cut-stop-design.md docs/superpowers/plans/2026-10-25-review-phase1-record.md docs/review/2026-10-25
git commit -m "review 25 Oct phase 1: the record (A65-A69)

- score_frame scores only the posting index's rows; a hollow bar no longer stops the day's scoring
- a feed gap (cts > 30 s) is booked to no side in the ux ladder and re-arms VPIN; tools/gap_slugs.py lists past slugs
- day_state saves under a lock with its own temp file; a torn file is kept and logged
- tape_log's write-once is one step under a lock

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: After her first restart after a close.** Read-only checks:
  - `tapemap.log` has no `score_frame write` traceback that day.
  - A frame day file has no SENSEX/BANKNIFTY tap whose `ex` was filled at a minute when only NIFTY posted. Spot-check 3 rows.
