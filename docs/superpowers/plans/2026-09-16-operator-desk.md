# Operator Desk — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A three-screen seller's desk at `http://127.0.0.1:8765/desk/` that owns TIME, MONEY, MORE THAN ONE INDEX and HEALTH — the four things the GoCharting chart tab structurally cannot — backed by five new pure Python modules and six new read-only JSON routes.

**Architecture:** Brain before face. Every computation lives in a pure stdlib module in `tapemap/` with one pytest; every route is a thin `elif` in `Handler.do_GET` that parses the query, calls one pure function and calls `self._json(...)`. The face is three static files under `ui/desk/` — no framework, no bundler, no CDN, ES modules, same-origin `fetch`, polling only (no SSE exists anywhere in this server).

**Tech Stack:** Python 3.13 stdlib + pytest (`python -m pytest -q`, 1118 tests). Node ≥ 18 for `node --test ui/desk/test.mjs`. Browser: plain ES modules + `<canvas>`.

## Global Constraints

- **Rulings (binding, and they WIN):** the head-of-desk rulings of 2026-09-16 round 2 — D1–D10, the accepted items from the designer's list, and the contract fixes. Where a §-reference below and a ruling disagree, the ruling is the decision and this plan already carries it. The two items under "Not accepted" (deleting the candidate book; moving the money strip to TODAY) are **not** applied: the candidate stays behind `c`, and the money strip stays on RECORD.
- **Spec:** `docs/superpowers/specs/2026-09-16-operator-desk-design.md`. Every §-reference below points into it.
- **Repo:** `C:\Users\kaam\Desktop\operator mode\tapemap`, branch `feature/operator-objects`. All commands run with that directory as cwd.
- **THE SERVER IS LIVE ON PORT 8765.** Never start it, never stop it, never POST to it. `GET` against it is allowed and is how routes are proved. Python changes take effect only when the owner restarts after 15:30 IST. Static files under `ui/` are served with **no restart and no code change** (`directory=ROOT/"ui"` at server.py:994, final `else: super().do_GET()` at server.py:1922-1923).
- **Pre-existing test failures — DO NOT CHASE THEM.** `python -m pytest -q` reports `3 failed, 1115 passed`. The three are all in `test_desk_numbers.py`:
  `test_a_short_book_collects_theta_so_the_estimate_is_positive`, `test_a_long_book_pays_theta`, `test_a_leg_with_no_iv_is_named_not_silently_dropped`. They were failing before this plan started. Any task that says "only the 3 pre-existing failures" means exactly these three.
- **Absence grammar (house rule 6, spec §C).** Every nullable field carries a sibling `*_why` of **≤ 48 characters** that is non-null exactly when the field is null. A missing value is never a zero, never a blank, never a default.
- **Tags:** `~` prefix = inferred, plain = measured. Nothing else is tagged. Python objects carry `"tag": "I"` or `"M"` where the existing objects already do.
- **Never print** a hit rate, win rate, expectancy, confidence score, probability of profit, payoff diagram, BULL/BEAR or any direction verdict, max pain as a number with a verdict, PCR, India VIX as a headline, live flashing MTM, or an order path. There is no order path in this stack and nothing here adds one.
- **Route insertion point, every route task:** insert the new `elif` **immediately above** the line
  `        elif self.path.startswith("/api/desk"):`
  (server.py:1570 before any of this plan's insertions; the number moves down as each task inserts, so **anchor on the string, never the number** — it is the only occurrence in the file). The preceding line is `            }).encode())`. This placement satisfies the spec's ordering rule: the dispatch is an ordered `startswith` chain with no route table, so `/api/desk/health` and `/api/desk/today` must sit above `/api/desk`.
- **Route idioms, copy verbatim:** query = `q = parse_qs(urlsplit(self.path).query)`; index = `idx = self._idx()` (server.py:996-1000, clamps to an enabled index); reply = `self._json(json.dumps({...}, default=str).encode())` (server.py:1031-1037).
- **`ROOT`** is `Path(__file__).parent` (server.py:53). Build every server-side file path as `str(ROOT / "data" / ...)`.
- **Commit messages** end with the trailer:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **Task 17 is marked DO NOT EXECUTE.** Do not run it, and do not commit anything in it, without the owner's written approval.

## File structure

| file | new? | owns |
|---|---|---|
| `tapemap/frame_log.py` | modify | quantised signature + the append lock |
| `tapemap/record_read.py` | **create** | the streaming record reader: `rows`, `visits`, `series` |
| `tapemap/events.py` | **create** | the hand-maintained event calendar: `today` |
| `tapemap/gate.py` | modify | `squeeze` out, `event` in, `level` no longer hard-coded |
| `tapemap/day_oi.py` | **create** | the campaign grid and the futures lane: `build`, `state4` |
| `tapemap/desk_health.py` | **create** | the one health object and the transition ring: `build` |
| `tapemap/survival.py` | **create** | gap table, square-off distance, days of income: `build` |
| `tapemap/frame.py` | modify | line 157 only — the new `gate.state` call |
| `tapemap/server.py` | modify | `_book_for` wires + one `elif` per route + the POST `row=` argument |
| `ui/desk/index.html` | **create** | three fixed skeletons, rail, two drawers, pre-paint theme stamp |
| `ui/desk/desk.css` | **create** | ten tokens × two themes, four type sizes, four level geometries |
| `ui/desk/desk.js` | **create** | polling, keys, screens, TODAY, RECORD cards/series/money, theme |
| `ui/desk/lanes.js` | **create** | canvas: axis, scrubber, CAMPAIGN, RECORD lanes |
| `ui/desk/test.mjs` | **create** | `node --test` over the pure functions |
| `data/events.json` | **create** | the hand-maintained calendar file |

Tests created: `test_record_read.py`, `test_events.py`, `test_day_oi.py`, `test_desk_health.py`, `test_survival.py`, plus new cases in `test_gate.py` and `test_frame_log.py`.

---

## PHASE A — THE BRAIN (Tasks 1–9). No UI file is touched until Task 9 passes.

### Task 1: The record churn fix — quantised `sig()` and the append lock

**Goal:** a price jitter smaller than one row stops rewriting the signature, and two threads cannot interleave the read-append-write.

**Files:**
- Modify: `tapemap/frame_log.py` (whole file replaced below)
- Modify: `tapemap/server.py` line 1128 (one line)
- Test: `tapemap/test_frame_log.py` (append two tests)

**Interfaces:**
- Produces: `frame_log.sig(fr: dict, row: float = 5.0) -> str` and `frame_log.append_if_changed(fr: dict, day: str, idx: str = "NIFTY", path: Optional[str] = None, row: float = 5.0) -> bool`. Both keep their existing positional order, so every existing call site still works.

**Why:** `sig()` hashes raw `r.get("p")` floats, so basis jitter alone rewrote the signature — 5552 rows / 116.3 MB on 2026-09-16 against 46 rows / 525 KB on 2026-09-15. The unguarded `_last_sig` read-then-append under `ThreadingHTTPServer` (server.py:2507) produced the 39 corrupted rows of 10:16–10:23.

- [ ] **Step 1: Write the failing tests** — append to `tapemap/test_frame_log.py`:

```python
def test_a_sub_row_price_jitter_is_one_signature_and_one_append(tmp_path):
    """The churn defect: 5552 rows / 116 MB on 2026-09-16 against 46 rows on
    2026-09-15, because the signature hashed raw basis-jittered floats."""
    a, b = _fr(), _fr()
    a["walls"]["rows"][0]["p"] = 23400.0
    b["walls"]["rows"][0]["p"] = 23401.4          # 1.4 points: less than one 5-point row
    assert frame_log.sig(a, row=5.0) == frame_log.sig(b, row=5.0)
    p = str(tmp_path / "frame_2026-09-16.jsonl")
    frame_log._last_sig.clear()
    assert frame_log.append_if_changed(a, "2026-09-16", path=p, row=5.0) is True
    assert frame_log.append_if_changed(b, "2026-09-16", path=p, row=5.0) is False
    assert sum(1 for _ in open(p, encoding="utf-8")) == 1


def test_a_whole_row_away_is_still_a_new_signature(tmp_path):
    a, c = _fr(), _fr()
    a["walls"]["rows"][0]["p"] = 23400.0
    c["walls"]["rows"][0]["p"] = 23406.0          # quantises to 23405: a different row
    assert frame_log.sig(a, row=5.0) != frame_log.sig(c, row=5.0)
    p = str(tmp_path / "frame_2026-09-16.jsonl")
    frame_log._last_sig.clear()
    assert frame_log.append_if_changed(a, "2026-09-16", path=p, row=5.0) is True
    assert frame_log.append_if_changed(c, "2026-09-16", path=p, row=5.0) is True
    assert sum(1 for _ in open(p, encoding="utf-8")) == 2
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_frame_log.py -k jitter`
Expected: FAIL — `TypeError: sig() got an unexpected keyword argument 'row'`

- [ ] **Step 3: Replace `tapemap/frame_log.py` in full**

```python
# tapemap/frame_log.py
"""frame_log.py -- THE ONE DECISION RECORD. `data/frame/frame_<day>.jsonl`.

Appended when the frame's SIGNATURE changes -- walls rows and their state,
setup state, tells, the missing list -- never on a raw counter or a tick of
OI. The categorical-signature idea is receive.mjs's `sig()` (the extension's
retired sink), moved into the process that survives the browser, so a
morning like 2026-09-11 (tool right all day, record empty) cannot recur.

PRICES ARE QUANTISED TO ONE ROW (2026-09-16). The signature used to hash the
raw `p` floats, so basis jitter of a point or two -- not a new level, not a
new state, nothing a reader would call a decision -- rewrote it. That wrote
5552 rows / 116.3 MB on 2026-09-16 against 46 rows / 525 KB on 2026-09-15.
`row` is the tape's own `rowSize`, passed in because the BUILT frame does not
carry it; server.py hands over the same `float(doc.get("rowSize") or 5)`
expression frame.py:247 uses.

THE APPEND IS LOCKED. `_last_sig` read, the append, and the `_last_sig`
write are one critical section: this runs under ThreadingHTTPServer
(server.py:2507) and three indices post concurrently, which is how 39 rows
of 10:16-10:23 on 2026-09-16 came out interleaved.

Forward cells (`ex`, `resolved`) are written ONCE by score_frame.py and never
edited here. Raw sense logs (senses/, warmap/, chain/) stay as inputs; this
file is the only decision record. Fail-soft append, same as sequence.py.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Optional

DIR = os.path.join("data", "frame")
_last_sig: dict = {}      # (day, idx) -> last signature written
_LOCK = threading.Lock()  # read _last_sig + append + write _last_sig = ONE critical section


def day_path(day: str) -> str:
    return os.path.join(DIR, f"frame_{day}.jsonl")


def _q(p, row: float):
    """A price snapped to the nearest `row`. None stays None -- a missing
    price is not price zero."""
    if p is None:
        return None
    try:
        return round(float(p) / row) * row
    except (TypeError, ValueError):
        return None


def sig(fr: dict, row: float = 5.0) -> str:
    try:
        row = float(row) or 5.0
    except (TypeError, ValueError):
        row = 5.0
    rows = [(_q(r.get("p"), row), r.get("kind"), r.get("state"))
            for r in (fr.get("walls") or {}).get("rows") or []]
    s = fr.get("setup") or {}
    tells = [(t.get("name"), t.get("target")) for t in s.get("tells") or []]
    return json.dumps([fr.get("idx"), rows, s.get("state"), s.get("fire"), tells,
                       sorted(fr.get("missing") or [])], default=str)


def append_if_changed(fr: dict, day: str, idx: str = "NIFTY", path: Optional[str] = None,
                      row: float = 5.0) -> bool:
    s = sig(fr, row)
    key = (day, idx)
    p = path or day_path(day)
    with _LOCK:
        if _last_sig.get(key) == s:
            return False
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps({"day": day, **fr}, default=str) + "\n")
        except OSError:
            return False          # never drop the feed for a disk error
        _last_sig[key] = s
        return True
```

- [ ] **Step 4: Pass the tape's own row size in from the POST handler**

In `tapemap/server.py`, find this exact line (server.py:1128):

```python
                fr["record"] = {"written": frame_log.append_if_changed(fr, day, idx)}
```

Replace with:

```python
                fr["record"] = {"written": frame_log.append_if_changed(
                    fr, day, idx, row=float(doc.get("rowSize") or 5))}
```

- [ ] **Step 5: Run the tests**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_frame_log.py && python -c "import server"`
Expected: `8 passed` from pytest, and `import server` prints nothing and exits 0.

- [ ] **Step 6: Commit**

```bash
git add frame_log.py test_frame_log.py server.py
git commit -m "frame_log: quantise the signature to one row and lock the append -- the 116 MB record churn"
```

---

### Task 2: `record_read.rows()` — the streaming reader, and `GET /api/day/record`

**Goal:** read the decision record back over HTTP for the first time, one line at a time, never loading the file into memory.

**Files:**
- Create: `tapemap/record_read.py`
- Create: `tapemap/test_record_read.py`
- Modify: `tapemap/server.py` (one `elif` at the insertion point, one import)

**Interfaces:**
- Produces: `record_read.rows(path: str, idx: str = "NIFTY") -> list[dict]`, each row `{t, state, fire, gate, z, z_why, px, px_why, visit, missing}` per spec §H.4. `record_read._iter(path, idx)` and `record_read._cached(fn_name, path, idx, build)` are the internals Tasks 8 reuses.
- Produces: `record_read.yesterday(path: str, idx: str = "NIFTY", heat_today=None) -> dict | None` — ruling D9, THE YESTERDAY LINE. The same streaming reader, pointed at the PREVIOUS day's file: prior close, prior range, the closing wall ladder and the overnight OI change on the two biggest strikes. `None` means there is no readable row for that day, and the caller prints `PATA NAHI — no record for <prev day>`. Task 7's `/api/desk/today` is its only consumer.

**Why:** spec §H.4 and the §M decision — a 116 MB file must never be read into memory on a 10 s poll. `json.loads` over a whole file of full frames is forbidden; the reader streams and keeps ten fields per row. Ruling D9 rides the same reader rather than adding a route: the prior session is a file this module already knows how to stream.

**Field check against the real code:** a record row is `{"day": day, **frame}` (frame_log.py), so `ts` is `"HH:MM"` (frame.py:445), `where.z` and `where.px` exist (frame.py:174, 168), `setup.state`/`.fire`/`.visit` exist (frame.py:378, 388, 407), `head.gate.level` exists (frame.py:160), `missing` exists (frame.py:446).

- [ ] **Step 1: Write the failing test** — create `tapemap/test_record_read.py`:

```python
# tapemap/test_record_read.py
"""The one decision record, read back. Streamed, never loaded."""
import json

import record_read


def _row(ts, state, fire, z, px, visit, gate="PATA NAHI", missing=None, idx="NIFTY"):
    # sigma is `where.sigma`: the VWAP BAND HALF-WIDTH in points, the unit the
    # zone itself is cut in (d2 = 2 sigma). 18 points on NIFTY, not 71 -- the
    # 2 sigma / 1 sigma thresholds of the outcome ladder are read against this.
    return {"day": "2026-09-16", "idx": idx, "ts": ts,
            "head": {"gate": {"level": gate}},
            "where": {"px": px, "z": z, "sigma": 18.0, "px_why": None, "zone_why": None},
            "setup": {"state": state, "fire": fire, "visit": visit, "flow": [],
                      "confirm": {"value": "not wired"}},
            "walls": {"rows": [{"p": 23400.0, "kind": "S", "state": "held"}]},
            "taps": [], "missing": missing or []}


def _file(tmp_path, rows):
    p = tmp_path / "frame_2026-09-16.jsonl"
    with open(p, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return str(p)


def test_three_lines_give_three_rows_and_only_the_fields_the_desk_needs(tmp_path):
    record_read._CACHE.clear()
    p = _file(tmp_path, [
        _row("09:45", "WAITING", False, -0.42, 23301.0, None, missing=["warmap"]),
        _row("09:52", "ARMED", False, -1.91, 23244.0, "buy@09:45"),
        _row("10:07", "TRIGGERED", True, -2.10, 23238.0, "buy@09:45"),
    ])
    rows = record_read.rows(p, "NIFTY")
    assert [r["t"] for r in rows] == ["09:45", "09:52", "10:07"]
    assert [r["state"] for r in rows] == ["WAITING", "ARMED", "TRIGGERED"]
    assert rows[2]["fire"] is True and rows[0]["fire"] is False
    assert rows[0]["missing"] == ["warmap"] and rows[1]["missing"] == []
    assert rows[1]["visit"] == "buy@09:45"
    # the 21 KB half of the row is NOT carried
    assert set(rows[0]) == {"t", "state", "fire", "gate", "z", "z_why", "px", "px_why", "visit", "missing"}


def test_a_null_z_carries_its_why_and_another_index_is_not_mine(tmp_path):
    record_read._CACHE.clear()
    mine = _row("09:45", "WAITING", False, None, 23301.0, None)
    mine["where"]["zone_why"] = "no bands on the tape yet"
    p = _file(tmp_path, [mine, _row("09:46", "WAITING", False, -0.1, 55.0, None, idx="SENSEX")])
    rows = record_read.rows(p, "NIFTY")
    assert len(rows) == 1
    assert rows[0]["z"] is None and rows[0]["z_why"] == "no bands on the tape yet"
    assert rows[0]["px"] == 23301.0 and rows[0]["px_why"] is None


def test_a_torn_last_line_costs_that_line_and_not_the_day(tmp_path):
    record_read._CACHE.clear()
    p = _file(tmp_path, [_row("09:45", "WAITING", False, -0.4, 23301.0, None)])
    with open(p, "a", encoding="utf-8") as fh:
        fh.write('{"day": "2026-09-16", "idx": "NIFT')
    assert len(record_read.rows(p, "NIFTY")) == 1


def test_the_result_is_cached_by_path_mtime_size(tmp_path):
    record_read._CACHE.clear()
    p = _file(tmp_path, [_row("09:45", "WAITING", False, -0.4, 23301.0, None)])
    first = record_read.rows(p, "NIFTY")
    assert record_read.rows(p, "NIFTY") is first        # same object: not re-read


def test_yesterday_is_the_last_row_of_the_previous_days_file(tmp_path):
    """Ruling D9. Prior close, prior range, the closing ladder, and the
    overnight change on the two biggest strikes -- all off one file this
    module already streams. A day with no readable row is None, never a zero."""
    record_read._CACHE.clear()
    a = _row("15:10", "WAITING", False, -0.4, 23301.0, None)
    b = _row("15:29", "WAITING", False, -0.2, 23280.0, None)
    b["walls"]["rows"] = [
        {"p": 23400.0, "kind": "CE", "state": "held", "oi": 9.0e6, "strike": 23400.0},
        {"p": 23200.0, "kind": "PE", "state": "held", "oi": 7.0e6, "strike": 23200.0},
        {"p": 23100.0, "kind": "PE", "state": "held", "oi": 1.0e6, "strike": 23100.0},
    ]
    p = _file(tmp_path, [a, b])
    y = record_read.yesterday(p, "NIFTY", heat_today=[
        {"k": 23400.0, "ce_oi": 1.1e7, "pe_oi": 0.0},
        {"k": 23200.0, "ce_oi": 0.0, "pe_oi": 6.0e6}])
    assert y["close"] == 23280.0 and y["hi"] == 23301.0 and y["lo"] == 23280.0
    assert y["range"] == 21.0
    assert [w["kind"] for w in y["ladder"]] == ["CE", "PE", "PE"]
    assert [(g["side"], g["k"]) for g in y["big"]] == [("CE", 23400.0), ("PE", 23200.0)]
    assert y["big"][0]["overnight"] == 2.0e6 and y["big"][1]["overnight"] == -1.0e6
    # no chain today: the overnight cell is a sentence, not a zero
    record_read._CACHE.clear()
    y2 = record_read.yesterday(p, "NIFTY", heat_today=None)
    assert y2["big"][0]["overnight"] is None
    assert y2["big"][0]["overnight_why"] == "no chain today to compare against"
    assert record_read.yesterday(str(tmp_path / "frame_1999-01-01.jsonl"), "NIFTY") is None
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_record_read.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'record_read'`

- [ ] **Step 3: Create `tapemap/record_read.py`**

```python
# tapemap/record_read.py
"""record_read.py -- THE ONE DECISION RECORD, READ BACK.

Until now nothing opened `data/frame/frame_<day>.jsonl` over HTTP: the file
was written by frame_log and rewritten by score_frame and read by nobody
(inventory 2026-09-16 §3, §7). This module is its reader.

HOW IT READS, AND WHY THAT IS THE WHOLE DESIGN. Every row is the ENTIRE
frame -- roughly 21 KB, the coverage blob and every walls row included -- and
the file reached 116 MB in one session. So: one line at a time, parse it,
keep ten fields, throw the frame away before the next line is read. The file
is never a list of frames in memory, and the result is cached by
(path, mtime, size) so a 10 s poll landing between two appends costs one
os.stat.

BOUNDED BY DESIGN. `MAX_BYTES` stops the scan and sets `truncated` rather
than letting a pre-churn-fix file (before frame_log's quantised signature)
stall a request. `SERIES_MAX_MB` refuses `series()` outright on such a file
and says so in words -- an honest refusal beats a request that never returns.

Pure except for the file read. No clock: `day` and the paths come from the
caller.
"""
from __future__ import annotations

import json
import os
from typing import Iterator, List, Optional

MAX_BYTES = 64 * 1024 * 1024     # stop the scan here and flag `truncated`
SERIES_MAX_MB = 20.0             # a day file larger than this is not scanned for series
HORIZON_MIN = 30                 # the card's near horizon (6 five-minute bars, spec §F)
HORIZON_FAR_MIN = 90             # the card's far horizon, the scorer's own "90m"
_CACHE: dict = {}                # (fn, path, idx) -> ((mtime, size) | None, value)


def _stamp(path: str):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_mtime, st.st_size)


def _cached(fn_name: str, path: str, idx: str, build):
    stamp = _stamp(path)
    key = (fn_name, path, idx)
    hit = _CACHE.get(key)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    val = build()
    _CACHE[key] = (stamp, val)
    return val


def _iter(path: str, idx: Optional[str]) -> Iterator[dict]:
    """One parsed frame at a time, for `idx` only. A torn line -- these files
    are appended to by a running process, so the last one can be a partial
    write -- is skipped, never fatal."""
    read = 0
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                read += len(line)
                if read > MAX_BYTES:
                    return
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if idx and r.get("idx") != idx:
                    continue
                yield r
    except OSError:
        return


def rows(path: str, idx: str = "NIFTY") -> List[dict]:
    """One compact row per record append (spec §H.4). No coverage blob, no
    walls rows -- those are most of the 21 KB."""
    def build() -> List[dict]:
        out = []
        for r in _iter(path, idx):
            w = r.get("where") or {}
            s = r.get("setup") or {}
            g = (r.get("head") or {}).get("gate") or {}
            z, px = w.get("z"), w.get("px")
            out.append({
                "t": str(r.get("ts") or "")[:5],
                "state": s.get("state"),
                "fire": bool(s.get("fire")),
                "gate": g.get("level") or "PATA NAHI",
                "z": z,
                "z_why": None if z is not None else (w.get("zone_why") or "no sigma on this row"),
                "px": px,
                "px_why": None if px is not None else (w.get("px_why") or "no price on this row"),
                "visit": s.get("visit"),
                "missing": list(r.get("missing") or []),
            })
        return out
    return _cached("rows", path, idx, build)


def yesterday(path: str, idx: str = "NIFTY", heat_today=None) -> Optional[dict]:
    """THE PRIOR SESSION, ONE LINE (ruling D9).

    Four facts a seller wants at 09:14 and no route serves: where it closed,
    how far it ranged, where the walls stood at that close, and what happened
    to the two biggest strikes overnight. All four are in the PREVIOUS day's
    `frame_<prev>.jsonl`, which this module already streams -- so this is a
    second pointing of the same reader, not a new route and not a new file.

    close and hi/lo are the record's OWN `where.px` series, so they are the
    last price and the range THIS TOOL SAW, not an exchange OHLC: the face
    tags them `~`. The ladder is the last frame's walls rows. `overnight` is
    today's chain OI minus that strike's OI at the close, and is None with a
    clause when there is no chain today -- never a zero.

    Returns None when no row of that day is readable, and the caller prints
    `PATA NAHI -- no record for <prev day>`.

    `heat_today` is NOT cached: the file half is, the join is recomputed, so a
    10 s poll never serves an overnight number built against a stale chain."""
    def build() -> Optional[dict]:
        last = None
        pxs = []
        for r in _iter(path, idx):
            last = r
            px = (r.get("where") or {}).get("px")
            if px is not None:
                try:
                    pxs.append(float(px))
                except (TypeError, ValueError):
                    continue
        if last is None:
            return None
        walls = [w for w in (((last.get("walls") or {}).get("rows")) or [])
                 if isinstance(w, dict) and w.get("p") is not None]
        ladder = [{"p": w.get("p"), "kind": w.get("kind"), "state": w.get("state")}
                  for w in walls][:6]
        big = []
        for w in sorted((w for w in walls
                         if w.get("kind") in ("CE", "PE") and w.get("oi") is not None),
                        key=lambda w: -float(w["oi"]))[:2]:
            big.append({"k": float(w.get("strike") if w.get("strike") is not None else w["p"]),
                        "side": w["kind"], "oi": float(w["oi"])})
        return {"t": str(last.get("ts") or "")[:5],
                "close": pxs[-1] if pxs else None,
                "close_why": None if pxs else "no price on any row of that day",
                "hi": max(pxs) if pxs else None,
                "lo": min(pxs) if pxs else None,
                "range": round(max(pxs) - min(pxs), 1) if pxs else None,
                "ladder": ladder,
                "ladder_why": None if ladder else "the closing frame carried no walls",
                "big": big,
                "big_why": None if big else "no OI strike in the closing frame"}

    base = _cached("yesterday", path, idx, build)
    if base is None:
        return None
    by_k = {}
    for h in (heat_today or []):
        try:
            by_k[float(h.get("k"))] = h
        except (TypeError, ValueError):
            continue
    out = dict(base)
    out["big"] = []
    for g in base["big"]:
        h = by_k.get(g["k"])
        now_oi = None if h is None else h.get(("ce_oi" if g["side"] == "CE" else "pe_oi"))
        if now_oi is None:
            out["big"].append({**g, "overnight": None,
                               "overnight_why": ("no chain today to compare against"
                                                 if h is None else
                                                 f"no {g['side']} OI at {g['k']:.0f} today")})
        else:
            out["big"].append({**g, "overnight": round(float(now_oi) - g["oi"], 1),
                               "overnight_why": None})
    return out
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_record_read.py`
Expected: `5 passed`

- [ ] **Step 5: Add the route**

In `tapemap/server.py`, add the import next to the existing one at line 44 — find:

```python
import score_frame
```

and replace with:

```python
import record_read
import score_frame
```

Then find the insertion anchor (the only occurrence in the file):

```python
        elif self.path.startswith("/api/desk"):
```

and insert **directly above it**:

```python
        elif self.path.startswith("/api/day/record"):
            # THE DECISION RECORD, READ BACK -- the first HTTP reader this
            # file has ever had. Streamed line by line inside record_read;
            # a 116 MB day must never become a list of frames in RAM.
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            idx = self._idx()
            path = str(ROOT / frame_log.day_path(day))
            self._json(json.dumps(record_read.rows(path, idx), default=str).encode())
```

- [ ] **Step 6: Prove it against the live server (GET only, never POST)**

Run: `curl -s -o NUL -w "%{http_code} %{time_total}\n" "http://127.0.0.1:8765/api/day/record?day=2026-09-16&idx=NIFTY"`
Expected: `404 ...` — **this is correct and expected.** The live server is running the OLD Python; it has no such route and will not until the owner restarts after 15:30 IST. `python -c "import server"` exiting 0 is the only import proof available before the restart. Record the 404 and move on.

- [ ] **Step 7: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server" && python -m pytest -q 2>&1 | tail -5`
Expected: `import server` exits 0; pytest ends `3 failed, 1120 passed` — only the three pre-existing `test_desk_numbers.py` failures.

- [ ] **Step 8: Commit**

```bash
git add record_read.py test_record_read.py server.py
git commit -m "record_read: stream the decision record back, cached by (path, mtime, size); GET /api/day/record"
```

---

### Task 3: `events.py` — the hand-maintained calendar

**Goal:** three answers, never two — the calendar was not checked (`None`), was checked and is clear (`{}`), or names today's event (a dict).

**Files:**
- Create: `tapemap/events.py`
- Create: `tapemap/test_events.py`
- Create: `data/events.json`

**Interfaces:**
- Produces: `events.today(path: str, day: str) -> dict | None`. A returned dict is either `{}` or `{"name": str, "level": "HALF SIZE" | "NO NEW RISK"}`. Task 4 consumes it as `gate.state(..., event=<this>)`.

**Why:** `gate.py` carries an unconditional `holes.append("event calendar not wired")`, which pins the gate at `PATA NAHI` forever (spec §H.7, R3). There is no free feed of RBI/Fed/budget dates worth trusting, so the operator edits a file.

- [ ] **Step 1: Write the failing test** — create `tapemap/test_events.py`:

```python
# tapemap/test_events.py
"""Three answers, never two (house rule 6): not checked, checked and clear,
or the entry. A missing file is not an empty calendar."""
import json

import events


def _write(tmp_path, rows):
    p = tmp_path / "events.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    return str(p)


def test_an_absent_file_is_not_checked():
    events._CACHE.clear()
    assert events.today("data/no-such-events-file.json", "2026-09-30") is None


def test_present_with_no_entry_today_is_checked_and_clear(tmp_path):
    events._CACHE.clear()
    p = _write(tmp_path, [{"date": "2026-09-30", "name": "RBI policy", "level": "HALF SIZE"}])
    assert events.today(p, "2026-09-16") == {}


def test_an_entry_today_is_the_dict(tmp_path):
    events._CACHE.clear()
    p = _write(tmp_path, [{"date": "2026-09-30", "name": "RBI policy", "level": "HALF SIZE"},
                          {"date": "2026-10-28", "name": "Fed decision", "level": "NO NEW RISK"}])
    assert events.today(p, "2026-10-28") == {"name": "Fed decision", "level": "NO NEW RISK"}


def test_a_row_with_a_level_the_gate_cannot_rank_is_ignored_not_guessed(tmp_path):
    events._CACHE.clear()
    p = _write(tmp_path, [{"date": "2026-09-16", "name": "typo", "level": "MAYBE"}])
    assert events.today(p, "2026-09-16") == {}


def test_a_corrupt_file_reads_as_checked_and_clear_never_as_unchecked(tmp_path):
    events._CACHE.clear()
    p = tmp_path / "events.json"
    p.write_text("{not json", encoding="utf-8")
    assert events.today(str(p), "2026-09-16") == {}
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_events.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'events'`

- [ ] **Step 3: Create `tapemap/events.py`**

```python
# tapemap/events.py
"""events.py -- the hand-maintained event calendar, and nothing more.

WHY IT EXISTS. gate.py has appended "event calendar not wired" on every
single call since it was ported, which pinned the gate at PATA NAHI forever:
a permanently unmeasured input is not a hole, it is a broken gauge. There is
no free feed of RBI / Fed / budget dates this stack would trust, and
inventing one would be the most dangerous number on the screen -- so the
operator edits a file by hand and this reads it.

THREE ANSWERS, NEVER TWO (house rule 6):
  None  -- the file is absent: the calendar was NOT CHECKED. A hole.
  {}    -- the file is there and has no entry for `day`: CHECKED, CLEAR.
           Not a hole, and no effect on the gate.
  {...} -- today's entry; the gate worsens to its `level` and the reason is
           its `name`.

A file that will not parse reads as CHECKED, CLEAR rather than as unchecked:
the operator did create it, and a typo must not silently re-grey the gate
for a reason no screen would name.

Cached by (mtime, size): this runs on the frame POST path and a disk read
per post for a four-line file would be the wrong kind of honest.

`data/events.json` shape:
  [{"date": "2026-09-30", "name": "RBI policy", "level": "HALF SIZE"},
   {"date": "2026-10-28", "name": "Fed decision", "level": "NO NEW RISK"}]
"""
from __future__ import annotations

import json
import os
from typing import Optional

PATH = os.path.join("data", "events.json")
LEVELS = ("HALF SIZE", "NO NEW RISK")   # the only two gate.RANK levels an event may force
_CACHE: dict = {}                       # path -> ((mtime, size), rows)


def _load(path: str):
    try:
        st = os.stat(path)
    except OSError:
        return None                     # absent: NOT CHECKED
    stamp = (st.st_mtime, st.st_size)
    hit = _CACHE.get(path)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        doc = []                        # present but unreadable: checked, clear
    rows = doc if isinstance(doc, list) else []
    _CACHE[path] = (stamp, rows)
    return rows


def today(path: str, day: str) -> Optional[dict]:
    rows = _load(path)
    if rows is None:
        return None
    for r in rows:
        if not isinstance(r, dict):
            continue
        if str(r.get("date")) == str(day) and r.get("level") in LEVELS:
            return {"name": str(r.get("name") or "event"), "level": r["level"]}
    return {}
```

- [ ] **Step 4: Create the calendar file** — write `data/events.json` with exactly this content:

```json
[{"date": "2026-09-30", "name": "RBI policy", "level": "HALF SIZE"},
 {"date": "2026-10-28", "name": "Fed decision", "level": "NO NEW RISK"}]
```

- [ ] **Step 5: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_events.py`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add events.py test_events.py data/events.json
git commit -m "events: the hand-maintained calendar -- absent is not checked, present and clear is not a hole"
```

---

### Task 4: The gate leaves grey — `squeeze` out, `event` and `ivrv` in

**Goal:** `gate.level` can read `TRADE` / `HALF SIZE` / `NO NEW RISK` when every input is present, instead of being hard-coded `"PATA NAHI"` on every call.

**Files:**
- Modify: `tapemap/gate.py` (whole file replaced below)
- Modify: `tapemap/test_gate.py` (whole file replaced below — every existing call site passes `squeeze=`)
- Modify: `tapemap/frame.py` lines 156-157
- Modify: `tapemap/server.py` — a new `_ivrv_for` helper above `_book_for`, and three lines inside `_book_for`; `_book_for` gains an optional `day`; the POST handler passes it.

**Interfaces:**
- Consumes: `events.today(path, day)` from Task 3.
- Produces: `gate.state(ivrv, expiry_iso, today_iso, vpin_pct, event, ivrv_why=None) -> {level, reason, holes, would_be, would_be_reason}`. `event` is `None` (not checked — a hole), `{}` (checked, nothing today — no hole, no effect) or `{"name", "level"}` (worsen to that level, reason = the name).
  Produces on the book: `book["ivrv"]`, `book["ivrv_why"]`, `book["event"]`.

**Verified against the real code before writing:** `squeeze` is passed as a literal `None` at frame.py:157 and is documented there as "never measured here" — a permanent `None` is a permanent hole. `gate.py:47` is the unconditional `holes.append("event calendar not wired")`; `gate.py:48` is `return {"level": "PATA NAHI", ...}`. (The 2026-09-16 inventory cited these as lines 50 and 51; the real file is 49 lines and they are 47 and 48. Use the strings below, not line numbers.)

**Verified against the real code — three spec field names that do NOT exist:**
1. **`_surface_for(idx)` does not exist** anywhere in server.py. The real accessor is `_surface_read(poller, idx)` (server.py:307), which returns a `surface.SurfaceRead` **dataclass**, not a dict — `.get()` on it raises. Every existing caller wraps it in `asdict(...)` (server.py:1640). This task does the same.
2. **`rv5` is not a sibling of `fit`.** `_rv5(idx)` (server.py:352) returns `(dict_or_None, why_or_None)` and the `/api/surface` route grafts it **into** `fit` as `fit["rv5"]` / `fit["rv5_why"]` (server.py:1648-1651). So the live path is `indices.<idx>.fit.rv5.rv`, and this task calls `_rv5(idx)` directly.
3. `atm_iv` **does** exist on the fit (server.py:1670 reads `fit["atm_iv"]`).

- [ ] **Step 1: Replace `tapemap/test_gate.py` in full** (the failing test)

```python
# tapemap/test_gate.py
"""The seller's gate, ported from ui/toolb.js:826 with the P0 fixed: a hole
WINS. The old gate initialised to TRADE and holes never downgraded it, so it
said GO in green at 09:20 with IV/RV, VPIN and expiry all unknown.

2026-09-16: `squeeze` is gone -- it was never measured, so a permanent None
kept the gate grey forever -- and `event` replaces the unconditional calendar
hole. The gate can now leave grey."""
import gate


def test_a_hole_wins_and_reads_grey():
    g = gate.state(ivrv=None, expiry_iso="2026-09-15", today_iso="2026-09-15",
                   vpin_pct=0.2, event={})
    assert g["level"] == "PATA NAHI" and any("IV vs RV" in h for h in g["holes"])


def test_the_gate_can_leave_grey():
    """§J: event={}, ivrv=1.2, a future expiry, vpin_pct=0.1 -> TRADE."""
    g = gate.state(ivrv=1.2, expiry_iso="2026-09-30", today_iso="2026-09-16",
                   vpin_pct=0.1, event={})
    assert g["level"] == "TRADE" and g["holes"] == []
    assert g["reason"] == "no block seen"


def test_an_unchecked_calendar_is_a_hole_and_names_only_the_state():
    """Ruling D8: the hole NAMES THE STATE and nothing else. "create it" is an
    instruction, and §A excludes instruction sentences from the screen -- it
    lives in the legend drawer, where someone who wants to act can find it."""
    g = gate.state(ivrv=1.3, expiry_iso="2026-09-15", today_iso="2026-09-15",
                   vpin_pct=0.2, event=None)
    assert g["level"] == "PATA NAHI"
    assert g["holes"] == ["event calendar: not checked"]
    assert "create" not in g["holes"][0]
    assert g["would_be"] == "HALF SIZE" and "expiry" in g["would_be_reason"]


def test_an_event_today_worsens_the_level_and_names_itself():
    g = gate.state(ivrv=1.3, expiry_iso="2026-09-30", today_iso="2026-09-16",
                   vpin_pct=0.2, event={"name": "RBI policy", "level": "NO NEW RISK"})
    assert g["level"] == "NO NEW RISK" and g["holes"] == []
    assert g["reason"] == "RBI policy" and g["would_be"] == "NO NEW RISK"


def test_an_event_level_the_gate_cannot_rank_is_treated_as_half_size():
    g = gate.state(ivrv=1.3, expiry_iso="2026-09-30", today_iso="2026-09-16",
                   vpin_pct=0.2, event={"name": "typo", "level": "GO AWAY"})
    assert g["level"] == "HALF SIZE"


def test_worst_reason_leads():
    g = gate.state(ivrv=0.9, expiry_iso="2026-09-15", today_iso="2026-09-15",
                   vpin_pct=0.9, event={})
    assert g["would_be"] == "NO NEW RISK" and g["would_be_reason"] in ("vol cheap", "VPIN burst")


def test_the_ivrv_hole_carries_the_callers_own_clause():
    g = gate.state(None, "2026-09-30", "2026-09-16", 0.1, {}, ivrv_why="iv/rv — rv5 missing")
    assert g["holes"] == ["iv/rv — rv5 missing"]
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_gate.py`
Expected: FAIL — `TypeError: state() got an unexpected keyword argument 'event'`

- [ ] **Step 3: Replace `tapemap/gate.py` in full**

```python
# tapemap/gate.py
"""gate.py -- the seller's GATE, ported from ui/toolb.js:826 gateState().

It may say only three things -- TRADE / HALF SIZE / NO NEW RISK -- and a
fourth that the old code could not: PATA NAHI. The P0 the port fixes: the
old gate initialised to TRADE and holes never downgraded it, so it showed GO
in green at 09:20 with IV/RV, VPIN and expiry all unknown. Here a hole WINS.

2026-09-16, THE GATE LEAVES GREY (spec R3). Two changes, both because a
permanently unmeasured input is not a hole, it is a broken gauge:

  * `squeeze` is GONE. frame.py passed a literal None on every call and said
    so in a comment; the "day type: not measured yet" hole could therefore
    never be filled, and the level could never be anything but PATA NAHI.
  * the unconditional `holes.append("event calendar not wired")` is replaced
    by an `event` argument with THREE meanings, so "not checked" and
    "checked, nothing today" stop collapsing into one rendering:
        None  -> a hole, named "event calendar: not checked". It names the
                 STATE, never an instruction (ruling D8, spec A): "create
                 data/events.json" lives in the legend drawer.
        {}    -> checked and clear: no hole, no effect
        {...} -> {"name", "level"}: worsen to that level, reason = the name

`level` is no longer hard-coded: it is the computed level when `holes` is
empty and PATA NAHI otherwise. `would_be` still carries what the gate would
say with every hole filled. `ivrv_why` lets the caller name WHICH half of
the ratio was missing instead of the generic clause. Pure, stdlib only."""
from __future__ import annotations

from typing import Optional

RANK = {"TRADE": 0, "HALF SIZE": 1, "NO NEW RISK": 2}


def state(ivrv: Optional[float], expiry_iso: Optional[str], today_iso: str,
          vpin_pct: Optional[float], event: Optional[dict],
          ivrv_why: Optional[str] = None) -> dict:
    holes = []
    level, lead = "TRADE", None

    def worse(l, why):
        nonlocal level, lead
        if l not in RANK:
            l = "HALF SIZE"     # a hand-typed level the gate cannot rank: the cautious read
        if RANK[l] > RANK[level]:
            level, lead = l, why

    if ivrv is None:
        holes.append(ivrv_why or "IV vs RV: not measured")
    elif ivrv < 1.0:
        worse("NO NEW RISK", "vol cheap")
    elif ivrv < 1.1:
        worse("HALF SIZE", "IV barely above RV")
    if not expiry_iso:
        holes.append("expiry date: chain did not give one")
    elif expiry_iso == today_iso:
        worse("HALF SIZE", "expiry day, gamma fast")
    if vpin_pct is None:
        holes.append("VPIN: not measured yet")
    elif vpin_pct >= 0.8:
        worse("NO NEW RISK", "VPIN burst")
    if event is None:
        holes.append("event calendar: not checked")
    elif event:
        worse(event.get("level"), event.get("name") or "event today")
    return {"level": "PATA NAHI" if holes else level,
            "reason": "; ".join(holes) if holes else (lead or "no block seen"),
            "holes": holes,
            "would_be": level, "would_be_reason": lead or "no block seen"}
```

- [ ] **Step 4: Run the gate test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_gate.py`
Expected: `7 passed`

- [ ] **Step 5: Update the one caller in `frame.py`** — find these two lines (frame.py:156-157):

```python
    # squeeze is never measured here: None is the honest absence
    g = gate_mod.state(book.get("ivrv"), book.get("expiry"), day or "", book.get("vpin_pct"), None)
```

Replace with:

```python
    # `event` is three-valued: None = the calendar was not checked, {} = checked and clear,
    # a dict = today's entry. server._book_for does the one file read; frame.py stays pure.
    g = gate_mod.state(book.get("ivrv"), book.get("expiry"), day or "", book.get("vpin_pct"),
                       book.get("event"), book.get("ivrv_why"))
```

- [ ] **Step 6: Wire `ivrv` and `event` into the book** — in `tapemap/server.py`, find the import line:

```python
import instruments
```

and replace with:

```python
import events as events_mod
import instruments
```

Then find the start of `_book_for` (server.py:944):

```python
def _book_for(handler, idx):
```

and insert **directly above it**:

```python
_IVRV_CACHE: dict = {}       # idx -> (expires_at, ivrv, ivrv_why)
_IVRV_TTL_S = 30.0
# ponytail: a 30 s time cache, not an invalidation. `_surface_read` refits the
# live chain and `_rv5` globs data/backtest on every call; both run on the frame
# POST path, three indices at ~2 s. atm_iv moves at chain pace (~10.5 s) anyway,
# so a TTL is the honest ceiling. Swap for a chain-snapshot-keyed cache if the
# poll ever gets faster than the TTL.


def _ivrv_for(handler, idx):
    """THE ONE MISSING WIRE between the surface and the gate (inventory §5):
    nothing joined atm_iv to rv5 into a ratio, so gate.py's IV-vs-RV input was
    hard-coded None here and the gate could never leave grey.

    Returns `(ivrv, ivrv_why)`, exactly one of them not None. The clause names
    WHICH half is missing, because "no ratio" and "no realized vol" are two
    different sentences."""
    now = time.time()
    hit = _IVRV_CACHE.get(idx)
    if hit and hit[0] > now:
        return hit[1], hit[2]
    ivrv = why = None
    try:
        fit = (asdict(_surface_read(handler.poller, idx)) or {}).get("fit") or {}
        rv5, rv5_why = _rv5(idx)
        iv, rv = fit.get("atm_iv"), (rv5 or {}).get("rv")
        if iv and rv:
            ivrv = round(iv / rv, 4)
        else:
            why = "iv/rv — atm_iv missing" if not iv else "iv/rv — rv5 missing"
    except Exception as e:      # a bad chain must never cost the whole frame
        why = f"iv/rv — {type(e).__name__}"
    _IVRV_CACHE[idx] = (now + _IVRV_TTL_S, ivrv, why)
    return ivrv, why
```

- [ ] **Step 7: Give `_book_for` the day and the two new fields** — find this line (server.py:944):

```python
def _book_for(handler, idx):
```

and replace with:

```python
def _book_for(handler, idx, day=None):
```

Then find the return statement at the end of `_book_for` (server.py:975-981):

```python
    return {"warmap": wm, "minutes": getattr(st, "minutes", None),
            "spot": box.get("spot") if box else None,
            "expiry": (box or {}).get("expiry") or (pj.get("expiry") if isinstance(pj, dict) else None),
            "zone_state": _day0.get("zone_state"), "zone_state_sell": _day0.get("zone_state_sell"),
            "pivots": _day0.get("pivots"),      # the prior session's floor pivots; frame._walls inverts them to PDH/PDL/PDC
            "vpin_pct": vpin_pct, "senses": senses, "ivrv": None,
            "coverage": _coverage()}
```

and replace with:

```python
    ivrv, ivrv_why = _ivrv_for(handler, idx)
    try:
        event = events_mod.today(str(ROOT / "data" / "events.json"),
                                 day or time.strftime("%Y-%m-%d"))
    except Exception:
        event = None            # unreadable for a reason we cannot name: NOT CHECKED
    return {"warmap": wm, "minutes": getattr(st, "minutes", None),
            "spot": box.get("spot") if box else None,
            "expiry": (box or {}).get("expiry") or (pj.get("expiry") if isinstance(pj, dict) else None),
            "zone_state": _day0.get("zone_state"), "zone_state_sell": _day0.get("zone_state_sell"),
            "pivots": _day0.get("pivots"),      # the prior session's floor pivots; frame._walls inverts them to PDH/PDL/PDC
            "vpin_pct": vpin_pct, "senses": senses,
            "ivrv": ivrv, "ivrv_why": ivrv_why, "event": event,
            "coverage": _coverage()}
```

- [ ] **Step 8: Pass the tape's own day from the POST handler** — find (server.py:1126):

```python
                fr = frame.build(doc, _book_for(self, idx), time.strftime("%H:%M"))
```

and replace with:

```python
                fr = frame.build(doc, _book_for(self, idx, day), time.strftime("%H:%M"))
```

(`day` is already computed seven lines above, at server.py:1119.)

- [ ] **Step 9: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server" && python -m pytest -q 2>&1 | tail -5`
Expected: `import server` exits 0; pytest ends `3 failed, 1128 passed` — only the three pre-existing `test_desk_numbers.py` failures. `test_frame_api.py::test_book_for_reads_zone_state_from_days0` still passes because `day` is optional.

- [ ] **Step 10: Commit**

```bash
git add gate.py test_gate.py frame.py server.py
git commit -m "gate: drop the never-measured squeeze, take a three-valued event, stop hard-coding PATA NAHI; server wires ivrv from the surface"
```

---

### Task 5: `day_oi.py` — the campaign grid and the futures lane, and `GET /api/day/oi`

**Goal:** per-strike wall-build time, peak time and retreat — the time dimension no route serves today — out of `ChainState.minutes`, which has held it in RAM all session and been read only as a sum.

**Files:** Create `tapemap/day_oi.py`, `tapemap/test_day_oi.py`. Modify `tapemap/server.py` (import + one `elif`).

**Interfaces:**
- Produces: `day_oi.build(minutes, spot, win=15, bf_before=None, bars=None) -> dict` (spec §H.3) and `day_oi.state4(d_oi, d_prem) -> str` — one pure function used for **both** the strike lanes and `fut`, so the four-state table exists once (anti-pattern 7).

**The real input shape, verified at chain_metrics.py:339-353:** `ChainState.minutes` is a plain dict keyed `"HH:MM"`, value `{"spot": float, "k": {strike: (ce_oi_chg, pe_oi_chg)}, "px": {strike: (ce_ltp, pe_ltp)}}`. `k` holds **change since open** (cumulative); `px` holds a **level**. Strike keys are numbers in RAM and strings after a JSON round-trip, so `_kf()` normalises both. There is **no pruning anywhere** in that file, so the whole session is available.

**Window rule (spec §E, ruling on the designer's list):** `w` cycles 5 m → 15 m → day. The window is the aggregation bucket: 5 → five-minute segments (75 across the session), 15 → fifteen-minute segments (25), `"day"` → **thirty-minute segments (13)**, never one segment per lane. A single bar per lane is the snapshot the war-map brief rejected: `day` is the coarsest *reading* of the day, not the abolition of its time axis. Default 15.

**Lane rule (spec §E):** one lane per strike; side is `CE` for strikes above spot, `PE` for strikes at or below it — the seller's read, calls above and puts below. ±7 strikes around spot, cap 14, the rest counted in `capped`.

- [ ] **Step 1: Write the failing test** — create `tapemap/test_day_oi.py`:

```python
# tapemap/test_day_oi.py
"""The campaign grid: when a wall was built, when it peaked, when it retreated.
None of that was available from any route before this module (inventory §4)."""
import day_oi


def _minutes():
    """PE 23200 rises to a peak at 09:20 then gives half of it back."""
    return {
        "09:15": {"spot": 23200.0, "k": {23200: (0.0, 1.0e6)}, "px": {23200: (100.0, 120.0)}},
        "09:20": {"spot": 23188.0, "k": {23200: (0.0, 3.0e6)}, "px": {23200: (100.0, 110.0)}},
        "09:25": {"spot": 23244.0, "k": {23200: (0.0, 1.5e6)}, "px": {23200: (100.0, 118.0)}},
    }


def test_state4_is_one_table_used_twice():
    assert day_oi.state4(+1, -1) == "writing"        # OI up, premium down
    assert day_oi.state4(+1, +1) == "loading"        # OI up, premium up
    assert day_oi.state4(-1, +1) == "covering"       # OI down, premium up
    assert day_oi.state4(-1, -1) == "liquidation"    # OI down, premium down
    assert day_oi.state4(+1, 0) == "writing"         # flat premium is not a bid


def test_a_three_minute_lane_peaks_in_the_middle_and_retreats():
    d = day_oi.build(_minutes(), spot=23200.0, win=5, bf_before=None, bars=None)
    assert d["ok"] is True and d["ts"] == "09:25" and d["win"] == 5
    lane = d["lanes"][0]
    assert lane["strike"] == 23200.0 and lane["side"] == "PE"
    assert lane["peak"]["t"] == "09:20"
    assert lane["peak"]["added"] == 3.0e6 and lane["peak"]["spot"] == 23188.0
    assert lane["ghost_hi"] == 3.0e6
    assert lane["added"] == 1.5e6 and lane["retreat"] is True
    assert [s["state4"] for s in lane["segments"]] == ["writing", "writing", "covering"]
    assert lane["since"] == "09:15"                  # first minute past 25,000 contracts
    assert lane["since_why"] is None
    assert all(s["bf"] is False for s in lane["segments"])


def test_the_peak_and_the_retreat_are_the_days_maximum_whatever_the_window():
    """`peak` is the day maximum of the cumulative added-since-open series and
    `retreat` is `added(now) < 0.85 x peak.added`. Both are read off the raw
    minutes, so changing `w` re-buckets the SEGMENTS and nothing else."""
    a = day_oi.build(_minutes(), spot=23200.0, win=5, bf_before=None, bars=None)["lanes"][0]
    b = day_oi.build(_minutes(), spot=23200.0, win=15, bf_before=None, bars=None)["lanes"][0]
    c = day_oi.build(_minutes(), spot=23200.0, win="day", bf_before=None, bars=None)["lanes"][0]
    for lane in (a, b, c):
        assert lane["peak"] == {"added": 3.0e6, "t": "09:20", "spot": 23188.0}
        assert lane["retreat"] is True and lane["ghost_hi"] == 3.0e6
        assert lane["since"] == "09:15"
    assert len(a["segments"]) == 3 and len(b["segments"]) == 1 and len(c["segments"]) == 1


def test_a_wall_that_never_crosses_the_threshold_has_no_start_and_says_so():
    tiny = {"09:15": {"spot": 23200.0, "k": {23200: (0.0, 900.0)},
                      "px": {23200: (100.0, 120.0)}}}
    lane = day_oi.build(tiny, spot=23200.0, win=15, bf_before=None, bars=None)["lanes"][0]
    assert lane["since"] is None
    assert lane["since_why"] == "never crossed 25,000 contracts"


def test_backfilled_segments_are_marked_and_never_blended():
    d = day_oi.build(_minutes(), spot=23200.0, win=5, bf_before="09:20", bars=None)
    assert d["bf_at"] == "09:20"
    assert [s["bf"] for s in d["lanes"][0]["segments"]] == [True, True, False]
    # a late-started chain may never print a confident total
    assert d["totals_why"] == "chain started 09:20: the open is reconstructed"


def test_totals_are_labelled_and_carry_every_strike_not_only_the_lanes():
    d = day_oi.build(_minutes(), spot=23200.0, win=15, bf_before=None, bars=None)
    assert d["totals"] == {"ce_added_since_open": 0.0, "pe_added_since_open": 1.5e6}
    assert d["totals_why"] is None                   # nothing backfilled: the total is whole


def test_no_chain_minutes_is_a_sentence_not_an_empty_chart():
    d = day_oi.build({}, spot=None, win=15, bf_before=None, bars=None)
    assert d["ok"] is False and d["lanes"] == []
    assert d["lanes_why"] == "no chain minutes in this process"
    assert d["totals_why"] == "no chain minutes in this process"


def test_the_futures_lane_refuses_rather_than_faking_a_single_delta():
    d = day_oi.build(_minutes(), spot=23200.0, win=5, bf_before=None, bars=None)
    assert d["fut"]["segments"] == []
    assert d["fut"]["why"] == "no tape held for that day in this process"
    no_oi = [{"t": 0, "o": 23200.0, "c": 23210.0}, {"t": 300000, "o": 23210.0, "c": 23220.0}]
    d2 = day_oi.build(_minutes(), spot=23200.0, win=5, bf_before=None, bars=no_oi)
    assert d2["fut"]["segments"] == [] and d2["fut"]["why"] == "bars carry no OI"


def test_the_futures_lane_uses_the_same_four_state_table():
    # 09:15 and 09:20 bars: OI up with price down = writing; then OI down, price up = covering
    bars = [{"t": 13500000, "o": 23200.0, "c": 23190.0, "oi": 1_000_000},
            {"t": 13800000, "o": 23190.0, "c": 23205.0, "oi": 900_000}]
    d = day_oi.build(_minutes(), spot=23200.0, win=5, bf_before=None, bars=bars)
    assert [s["state4"] for s in d["fut"]["segments"]] == ["writing", "covering"]
    assert d["fut"]["why"] is None


def test_the_lane_cap_is_fourteen_and_the_rest_are_counted():
    ks = [23000.0 + 50 * i for i in range(21)]            # 21 strikes around 23500
    mins = {"09:15": {"spot": 23500.0, "k": {k: (1.0e5, 2.0e5) for k in ks},
                      "px": {k: (100.0, 100.0) for k in ks}}}
    d = day_oi.build(mins, spot=23500.0, win=15, bf_before=None, bars=None)
    assert len(d["lanes"]) == 14 and d["capped"] == 7
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_day_oi.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'day_oi'`

- [ ] **Step 3: Create `tapemap/day_oi.py`**

```python
# tapemap/day_oi.py
"""day_oi.py -- THE CAMPAIGN GRID: when a wall was built, when it peaked, and
when its builders started retreating.

WHY IT EXISTS. `ChainState.minutes` (chain_metrics.py:339-353) has held the
whole session's per-strike OI-change and premium grid in RAM all day, with no
pruning, since the chain poller was written -- and the only route that ever
touched it (/api/oiflow) SUMS it across the selected strikes. So per-strike
build time, peak-OI time and retreat time were unavailable from any route
(inventory 2026-09-16 §4, "TIME DIMENSION SUMMARY"). This module reads that
same grid as a time series and answers those three questions.

ONE BASE, ALWAYS. Every bar's thickness is OI ADDED SINCE OPEN at the
segment's end -- never a total, never mixed with one. Totals live in their
own labelled block. This is the toolb units bug (a wall total printed beside
an added-since-open, unlabelled) made structurally impossible.

ONE FOUR-STATE TABLE. `state4()` is used for the strike lanes AND for the
futures lane, so OI x premium is defined once (anti-pattern 7: the same fact
computed twice from disjoint data).

BUILD VS RETREAT is server-computed, not left to the canvas: `retreat` is
`added(now) < 0.85 x peak.added`, where `peak` is the DAY MAXIMUM of the
cumulative added-since-open series and is therefore INDEPENDENT OF `win` --
changing the window re-buckets the segments and nothing else. `ghost_hi` is
that same high-water mark, which the face outlines so the trench stays
visible after the fill shrinks inside it.

`since` IS AN ABSOLUTE THRESHOLD: the first minute cumulative added crosses
SINCE_MIN contracts. It used to be a fraction of the day peak -- but the day
peak is unknown until the close, so a lane's left edge MOVED during the
session as the peak grew. A bar that slides while you are watching it is not
a record of when the wall was built.

BACKFILL NEVER BLENDS. A segment whose bucket STARTS at or before `bf_before`
carries `bf: true` -- a bucket straddling the boundary is part reconstructed,
and a blend is exactly what must not pass as watched. The face paints it at
55% and outline-only, and marks the axis once. An observed segment and a
reconstructed one are never one shape. Same rule in `_fut`, so the strike
lanes and the futures lane cannot disagree about what was watched.
`totals_why` is non-null whenever `bf_at` is, so a late-started chain cannot
print a confident partial total.

Pure, stdlib only, no I/O, no clock -- `spot`, the window and the backfill
boundary are passed in.
"""
from __future__ import annotations

from typing import List, Optional

SESSION_OPEN = "09:15"
BUCKET = {5: 5, 15: 15, "day": 30}       # window -> segment length in minutes
LANE_CAP = 14                            # +-7 strikes around spot (spec §E)
SINCE_MIN = 25_000                       # contracts: a wall "starts" when added crosses this
RETREAT_FRAC = 0.85                      # solid fill below this fraction of the DAY peak = retreating
MIGRATIONS_PER_HOUR = 3
MIGRATION_FRAC = 0.30                    # the smaller leg must be >=30% of the larger


def state4(d_oi, d_prem) -> str:
    """OI x premium, the only two axes that separate writing from loading.
    A FLAT premium is not a bid: 0 counts as "not up"."""
    if (d_oi or 0) >= 0:
        return "loading" if (d_prem or 0) > 0 else "writing"
    return "covering" if (d_prem or 0) > 0 else "liquidation"


def _m(hhmm) -> int:
    h, m = str(hhmm).split(":")[:2]
    return int(h) * 60 + int(m)


def _hm(mins: int) -> str:
    mins = max(0, int(mins))
    return f"{mins // 60:02d}:{mins % 60:02d}"


def _bucket(hhmm: str, step: int) -> str:
    o = _m(SESSION_OPEN)
    n = _m(hhmm)
    return SESSION_OPEN if n <= o else _hm(o + ((n - o) // step) * step)


def _kf(k) -> Optional[float]:
    """A strike key, numeric in RAM and a string after a JSON round-trip."""
    try:
        return float(k)
    except (TypeError, ValueError):
        return None


def _pair(v, j):
    """Index j of a (ce, pe) pair that may be a tuple or a list."""
    try:
        return float(v[j])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def _segments(series, step: int, bf_before: Optional[str], prem):
    """One segment per bucket: cumulative `added` at the bucket end, and the
    four-state word from the DELTA across the bucket."""
    out, prev_oi, prev_px = [], 0.0, (prem[0][1] if prem else None)
    by_bucket = {}
    for t, v in series:
        by_bucket.setdefault(_bucket(t, step), []).append((t, v))
    px_by_bucket = {}
    for t, v in prem:
        px_by_bucket.setdefault(_bucket(t, step), []).append((t, v))
    for b in sorted(by_bucket):
        t_end, v_end = by_bucket[b][-1]
        px_end = px_by_bucket.get(b, [(None, prev_px)])[-1][1]
        d_px = None if (px_end is None or prev_px is None) else (px_end - prev_px)
        out.append({"t": b, "added": v_end,
                    "state4": state4(v_end - prev_oi, d_px if d_px is not None else 0.0),
                    # A bucket that STARTS at or before `bf_before` is at least
                    # partly reconstructed, so it is marked -- backfill never
                    # blends, and a bucket straddling the boundary is a blend.
                    # Identical to `_fut`'s rule, so the strike lanes and the
                    # futures lane cannot disagree about what was watched.
                    "bf": bool(bf_before) and _m(b) <= _m(bf_before)})
        prev_oi, prev_px = v_end, (px_end if px_end is not None else prev_px)
    return out


def _migrations(lanes, step: int) -> List[dict]:
    """Paired unwind at A and build at B, same side, same bucket -> one arrow.
    Capped at MIGRATIONS_PER_HOUR per clock hour (spec §E)."""
    per_bucket = {}
    for ln in lanes:
        prev = 0.0
        for s in ln["segments"]:
            per_bucket.setdefault(s["t"], []).append((ln["side"], ln["strike"], s["added"] - prev))
            prev = s["added"]
    out, per_hour = [], {}
    for t in sorted(per_bucket):
        for side in ("CE", "PE"):
            rows = [(k, d) for sd, k, d in per_bucket[t] if sd == side]
            if len(rows) < 2:
                continue
            down = min(rows, key=lambda kd: kd[1])
            up = max(rows, key=lambda kd: kd[1])
            if down[1] >= 0 or up[1] <= 0:
                continue
            if min(abs(down[1]), up[1]) < MIGRATION_FRAC * max(abs(down[1]), up[1]):
                continue
            hour = t[:2]
            if per_hour.get(hour, 0) >= MIGRATIONS_PER_HOUR:
                continue
            per_hour[hour] = per_hour.get(hour, 0) + 1
            out.append({"t": t, "from": down[0], "to": up[0], "side": side})
    return out


def _fut(bars, step: int, bf_before: Optional[str]) -> dict:
    """The second army. From the posted 5 m bars frame.py:222 already reads
    (`closed[].oi`, `.o`, `.c`), NEVER faked from the frame's single delta."""
    rows = [b for b in (bars or []) if isinstance(b, dict) and b.get("t") is not None]
    if not rows:
        return {"segments": [], "why": "no tape held for that day in this process"}
    if not any(b.get("oi") is not None for b in rows):
        return {"segments": [], "why": "bars carry no OI"}
    from frame import _hhmm
    out, prev_oi = [], None
    for b in sorted(rows, key=lambda r: r["t"]):
        oi = b.get("oi")
        if oi is None:
            continue
        t = _bucket(_hhmm(int(b["t"])), step)
        d_oi = 0.0 if prev_oi is None else float(oi) - prev_oi
        d_px = float((b.get("c") or 0) - (b.get("o") or 0))
        out.append({"t": t, "d_oi": d_oi, "d_px": round(d_px, 1),
                    "state4": state4(d_oi if prev_oi is not None else 1.0, d_px),
                    "bf": bool(bf_before) and _m(t) <= _m(bf_before)})
        prev_oi = float(oi)
    return {"segments": out, "why": None}


def build(minutes, spot, win=15, bf_before=None, bars=None) -> dict:
    step = BUCKET.get(win) or BUCKET[15]
    mins = {k: v for k, v in (minutes or {}).items() if isinstance(v, dict)}
    marks = sorted(mins)
    empty_totals = {"ce_added_since_open": None, "pe_added_since_open": None}
    if not marks:
        return {"ok": False, "win": win, "spot": spot, "ts": None, "bf_at": bf_before,
                "capped": 0, "lanes": [], "lanes_why": "no chain minutes in this process",
                "totals": empty_totals, "totals_why": "no chain minutes in this process",
                "migrations": [], "fut": _fut(bars, step, bf_before)}
    last = marks[-1]
    if spot is None:
        spot = mins[last].get("spot")
    if spot is None:
        return {"ok": False, "win": win, "spot": None, "ts": last, "bf_at": bf_before,
                "capped": 0, "lanes": [], "lanes_why": "no spot on the last chain minute",
                "totals": empty_totals, "totals_why": "no spot on the last chain minute",
                "migrations": [], "fut": _fut(bars, step, bf_before)}
    spot = float(spot)

    all_k = sorted({kf for kf in (_kf(k) for k in (mins[last].get("k") or {})) if kf is not None})
    keep = sorted(sorted(all_k, key=lambda k: abs(k - spot))[:LANE_CAP])
    lanes = []
    for k in keep:
        side = "CE" if k > spot else "PE"
        j = 0 if side == "CE" else 1
        series, prem = [], []
        for t in marks:
            kk = mins[t].get("k") or {}
            src = kk.get(k, kk.get(str(k), kk.get(int(k) if k == int(k) else k)))
            v = _pair(src, j) if src is not None else None
            if v is None:
                continue
            series.append((t, v))
            pk = mins[t].get("px") or {}
            psrc = pk.get(k, pk.get(str(k), pk.get(int(k) if k == int(k) else k)))
            pv = _pair(psrc, j) if psrc is not None else None
            if pv is not None:
                prem.append((t, pv))
        if not series:
            continue
        # THE DAY MAXIMUM, off the raw minutes -- not off `segments`, so `win`
        # cannot move a peak, a ghost or a retreat verdict.
        peak_t, peak_v = max(series, key=lambda tv: tv[1])
        added = series[-1][1]
        since = next((t for t, v in series if v >= SINCE_MIN), None)
        lanes.append({
            "strike": k, "side": side, "added": added, "since": since,
            "since_why": None if since else f"never crossed {SINCE_MIN:,} contracts",
            "ghost_hi": peak_v, "retreat": bool(peak_v > 0 and added < RETREAT_FRAC * peak_v),
            "peak": {"added": peak_v, "t": peak_t, "spot": mins[peak_t].get("spot")},
            "segments": _segments(series, step, bf_before, prem),
        })

    ce = pe = 0.0
    for k, v in (mins[last].get("k") or {}).items():
        if _kf(k) is None:
            continue
        ce += _pair(v, 0) or 0.0
        pe += _pair(v, 1) or 0.0
    return {"ok": True, "win": win, "spot": spot, "ts": last, "bf_at": bf_before,
            "capped": max(0, len(all_k) - len(keep)),
            "lanes": lanes, "lanes_why": None if lanes else "no strike held a series today",
            "totals": {"ce_added_since_open": ce, "pe_added_since_open": pe},
            # REQUIRED whenever `bf_at` is non-null: part of this total was
            # reconstructed, and a confident partial total is the lie.
            "totals_why": (f"chain started {bf_before}: the open is reconstructed"
                           if bf_before else None),
            "migrations": _migrations(lanes, step),
            "fut": _fut(bars, step, bf_before)}
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_day_oi.py`
Expected: `10 passed`

- [ ] **Step 5: Add the route** — in `tapemap/server.py`, find the import line `import day_state` and replace with:

```python
import day_oi
import day_state
```

Then insert **directly above** `        elif self.path.startswith("/api/desk"):`:

```python
        elif self.path.startswith("/api/day/oi"):
            # THE BATTLEFIELD, with its time axis. Read from ChainState.minutes,
            # which has held the whole session in RAM all day and been served
            # only summed. `bars` is the posted 5 m tape the futures strip rides
            # on -- the same array /api/frame/bars serves.
            q = parse_qs(urlsplit(self.path).query)
            idx = self._idx()
            w = (q.get("win") or ["15"])[0]
            win = "day" if w == "day" else (5 if w == "5" else 15)
            st = (getattr(self.poller, "states", None) or {}).get(idx) if self.poller else None
            box = self.chains.get(idx) if self.chains else None
            with _SENSES_LOCK:
                doc = (_SENSES["tape"].get(idx) or {}).get("doc") or {}
            bars = doc.get("closed") or []
            bf = None
            try:
                bf = (_coverage() or {}).get("server_up") if (_coverage() or {}).get("late_min") else None
            except Exception:
                bf = None
            out = day_oi.build(getattr(st, "minutes", None), (box or {}).get("spot"),
                               win=win, bf_before=bf, bars=bars)
            self._json(json.dumps({**out, "idx": idx}, default=str).encode())
```

- [ ] **Step 6: Run the suite and commit**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server" && python -m pytest -q 2>&1 | tail -5`
Expected: `3 failed, 1138 passed` — only the three pre-existing `test_desk_numbers.py` failures.

```bash
git add day_oi.py test_day_oi.py server.py
git commit -m "day_oi: the campaign grid off ChainState.minutes -- build time, peak, retreat, one four-state table; GET /api/day/oi"
```

---

### Task 6: `desk_health.py` — one health object and the transition ring, and `GET /api/desk/health`

**Goal:** the blind-check a reader must currently assemble from four routes becomes one object, so 2026-09-16 (the tool went blind at 09:51 and she learned it after the session) cannot repeat.

**Files:** Create `tapemap/desk_health.py`, `tapemap/test_desk_health.py`. Modify `tapemap/server.py` (import + one `elif`).

**Interfaces:**
- Produces: `desk_health.build(health, senses, chains, tape_ats, record_stat, now) -> dict` per spec §H.1. `desk_health._RING` is a module-level `collections.deque(maxlen=200)`; `desk_health.RING_MAX = 200`.
- Argument shapes the route must build (all plain, so the module stays pure):
  `health` = `{"feed": <the /api/health feed dict or None>, "feed_why": str|None, "coverage": <_coverage()>}`
  `senses` = `{"error": str|None, "up_s": float|None, "orders_at": float|None}`
  `chains` = `{idx: built_at_epoch_or_None}`
  `tape_ats` = `{idx: last_post_epoch_or_None}` for every enabled index
  `record_stat` = `{"last_seen": float|None, "rows_today": int, "file_mb": float, "exists": bool}`
  `now` = `time.time()`

**Two spec claims checked against the real code:**
1. `_SENSES["tape"][idx]["at"]` **does** exist (server.py:1130) and is read nowhere — this route is its first consumer.
2. `self.chains[idx]["ts"]` **does not exist.** A chain box is `{"payload": bytes, "spot": float, "err_tag": str|None}` (chain_live.py:284, 308-319). The epoch the box really carries is `built_at` **inside the JSON payload** (chain_live.py:310). Parsing a ~200 KB payload every 2 s for one float is not acceptable, so the route pulls `built_at` out of the first 300 bytes with a regex and says so in a comment.

**Cadences (spec §M decision):** tape 1 · chain 12 · depth 15 · chart 5 · record 300 · senses 5.

- [ ] **Step 1: Write the failing test** — create `tapemap/test_desk_health.py`:

```python
# tapemap/test_desk_health.py
"""Is the tool blind right now. One object, six sources, four levels."""
import desk_health


def _args(**kw):
    a = {"health": {"feed": {"connected": True, "healthy": True, "age_s": 1.0}, "feed_why": None,
                    "coverage": {"server_up": "09:45", "session_open": "09:15", "late_min": 30,
                                 "reconstructed": ["chain minutes"],
                                 "not_reconstructable": ["tape events 09:15-09:45"],
                                 "why": "server started 30 min after the open"}},
         "senses": {"error": None, "up_s": 5400.0, "orders_at": 1000.0},
         "chains": {"NIFTY": 994.0},
         "tape_ats": {"NIFTY": 998.0, "BANKNIFTY": None},
         "record_stat": {"last_seen": 900.0, "rows_today": 46, "file_mb": 0.5, "exists": True},
         "now": 1000.0}
    a.update(kw)
    return a


def _by(d, name):
    return next(s for s in d["sources"] if s["source"] == name)


def test_three_times_the_cadence_is_late_and_five_times_is_dead():
    d = desk_health.build(**_args(chains={"NIFTY": 1000.0 - 36.0}))     # cadence 12 -> 3x
    assert _by(d, "chain poller")["level"] == "late"
    d = desk_health.build(**_args(chains={"NIFTY": 1000.0 - 60.0}))     # 5x
    assert _by(d, "chain poller")["level"] == "dead"
    d = desk_health.build(**_args(chains={"NIFTY": 1000.0 - 6.0}))      # under 2x
    assert _by(d, "chain poller")["level"] == "live"


def test_a_socket_that_is_up_with_no_ticks_is_late_and_says_which():
    d = desk_health.build(**_args(health={
        "feed": {"connected": True, "healthy": False, "age_s": 2240.3}, "feed_why": None,
        "coverage": {}}))
    f = _by(d, "tape feed")
    assert f["level"] == "late"
    assert f["why"] == "socket up, no ticks 2240s"


def test_the_chart_relay_is_one_row_per_posting_index_and_never_one_combined_cell():
    """Ruling D3. Three charts behind one `chart` cell is how 09:51 went
    unnoticed: NIFTY kept posting, so the combined cell stayed green while
    BANKNIFTY had never started. A source that never started serves age_s
    null -- an age ladder cannot say "was never alive", and a screen that
    renders that as a very large age is lying by arithmetic."""
    d = desk_health.build(**_args())
    names = [s["source"] for s in d["sources"]]
    assert "chart" not in names                       # never one cell for three
    assert names.count("chart NIFTY") == 1 and names.count("chart BANKNIFTY") == 1
    b = _by(d, "chart BANKNIFTY")
    assert b["level"] == "never started" and b["age_s"] is None and b["last_seen"] is None
    assert b["why"] == "no frame posted this process"
    # every row serves an AGE or a null -- never a clock time for the rail to print
    for s in d["sources"]:
        assert s["age_s"] is None or isinstance(s["age_s"], (int, float))


def test_the_record_writer_carries_its_rows_and_size():
    r = _by(desk_health.build(**_args()), "record writer")
    assert r["rows_today"] == 46 and r["file_mb"] == 0.5 and r["level"] == "live"
    r0 = _by(desk_health.build(**_args(record_stat={
        "last_seen": None, "rows_today": 0, "file_mb": 0.0, "exists": False})), "record writer")
    assert r0["level"] == "never started" and r0["why"] == "no record file today"


def test_an_error_is_dead_whatever_the_age():
    d = desk_health.build(**_args(senses={"error": "ConnectionReset", "up_s": 5400.0, "orders_at": 1000.0}))
    s = _by(d, "senses loop")
    assert s["level"] == "dead" and s["why"] == "ConnectionReset"


def test_only_a_transition_lands_in_the_ring():
    desk_health._RING.clear()
    desk_health._LAST.clear()
    desk_health.build(**_args())
    n = len(desk_health._RING)
    desk_health.build(**_args())                       # nothing changed
    assert len(desk_health._RING) == n
    desk_health.build(**_args(chains={"NIFTY": 1000.0 - 600.0}))
    last = desk_health._RING[-1]
    assert last["source"] == "chain poller" and last["from"] == "live" and last["to"] == "dead"


def test_every_null_in_a_row_carries_a_why_and_coverage_travels():
    d = desk_health.build(**_args())
    for s in d["sources"]:
        assert (s["last_seen"] is None) == (s["why"] is not None) or s["level"] == "dead"
        assert len(s["why"] or "") <= 48
    assert d["coverage"]["late_min"] == 30 and d["ok"] is True and d["muted"] is False
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_desk_health.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'desk_health'`

- [ ] **Step 3: Create `tapemap/desk_health.py`**

```python
# tapemap/desk_health.py
"""desk_health.py -- IS THE TOOL BLIND RIGHT NOW.

On 2026-09-16 the tool went blind at 09:51 and the operator learned it after
the session. Nothing was hidden: the evidence was spread across /api/health,
/api/senses, /api/oiflow and /api/warmap, and a reader had to fan out to four
routes and correlate them (inventory §6). This is that correlation, once,
server-side.

FOUR LEVELS, THE SAME FOUR THE WHOLE DESK USES (spec §C):
  live          age <  2 x cadence
  late          age <  5 x cadence
  dead          age >= 5 x cadence, or the source reports an error
  never started the source has produced NOTHING in this process -- an age
                ladder cannot express "was never alive", and a screen that
                renders that as a very large age is lying by arithmetic.

THE TONE RULE (ruling D3). An outage is an ABSENCE, not a fault. Every `why`
says what stopped and when it was last seen. Nothing here says ERROR, nothing
is red, and nothing asks the operator to do anything. The DESK tones once per
transition to dead for ALL SIX SOURCES -- the earlier rule routed the alarm
for a blind chart back to the panel living in the tab that went blind, and a
tone duplicated with that panel is a far smaller sin than a silent blind spot.

ONE ROW PER POSTING INDEX (ruling D3). The chart relay is `chart NIFTY`,
`chart BANKNIFTY`, ... -- never one `chart` cell for three. One green cell
fed by the only index still posting is exactly how 09:51 went unnoticed.
Every row carries an AGE (or null), never a clock time: the rail prints ages.

THE RING is the last 200 transitions {source, t, from, to} and is the ONLY
place the RECORD screen's marks lane reads outage gaps from. A poll that
changes nothing appends nothing.

Pure: no I/O, no clock. Every age is measured against the `now` passed in,
and every input is a plain number the route dug out.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

RING_MAX = 200
CADENCE = {"tape feed": 1, "chain poller": 12, "depth relay": 15,
           "chart": 5, "record writer": 300, "senses loop": 5}
LATE_X, DEAD_X = 2, 5

_RING = deque(maxlen=RING_MAX)   # {"source", "t", "from", "to"}
_LAST: dict = {}                 # source -> last level published


def _why48(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s)
    return s if len(s) <= 48 else s[:47] + "…"


def _level(age_s: Optional[float], cadence: int, error: Optional[str],
           ever: bool) -> str:
    if error:
        return "dead"
    if not ever or age_s is None:
        return "never started"
    if age_s < LATE_X * cadence:
        return "live"
    if age_s < DEAD_X * cadence:
        return "late"
    return "dead"


def _row(source, last_seen, cadence, now, error=None, why=None, ever=None, **extra):
    ever = (last_seen is not None) if ever is None else ever
    age = None if last_seen is None else round(now - last_seen, 1)
    lvl = _level(age, cadence, error, ever)
    if why is None and lvl == "never started":
        why = "never produced anything this process"
    if why is None and error:
        why = error
    return {"source": source, "last_seen": last_seen, "age_s": age, "cadence_s": cadence,
            "level": lvl, "backfilled": False, "why": _why48(why), **extra}


def _transition(rows) -> None:
    for r in rows:
        prev = _LAST.get(r["source"])
        if prev is not None and prev != r["level"]:
            _RING.append({"source": r["source"], "t": r.get("last_seen"),
                          "from": prev, "to": r["level"]})
        _LAST[r["source"]] = r["level"]


def build(health, senses, chains, tape_ats, record_stat, now) -> dict:
    health, senses = health or {}, senses or {}
    rows = []

    # 1 TAPE FEED -- the Upstox socket. connected:true with healthy:false is the
    # live state of 2026-09-16 and had no explanation field anywhere.
    feed = health.get("feed") or {}
    if not feed:
        rows.append(_row("tape feed", None, CADENCE["tape feed"], now, ever=False,
                         why=health.get("feed_why") or "no feed in this server mode"))
    else:
        age = feed.get("age_s")
        seen = None if age is None else now - float(age)
        if feed.get("connected") and not feed.get("healthy"):
            rows.append({"source": "tape feed", "last_seen": seen,
                         "age_s": None if age is None else round(float(age), 1),
                         "cadence_s": CADENCE["tape feed"], "level": "late", "backfilled": False,
                         "why": _why48(f"socket up, no ticks {float(age or 0):.0f}s")})
        else:
            rows.append(_row("tape feed", seen, CADENCE["tape feed"], now,
                             error=feed.get("error")))

    # 2 CHAIN POLLER -- one row, the freshest index; a stale index is named.
    fresh = [v for v in (chains or {}).values() if v is not None]
    stale = sorted(k for k, v in (chains or {}).items() if v is None)
    rows.append(_row("chain poller", max(fresh) if fresh else None, CADENCE["chain poller"], now,
                     ever=bool(fresh),
                     why=("no chain payload yet" if not fresh else
                          (f"no payload for {', '.join(stale)}" if stale else None))))

    # 3 DEPTH RELAY -- PaperDesk's Kite bridge, the one relay recency the
    # server already publishes (/api/senses.orders_bridge.age_s).
    oat = senses.get("orders_at")
    rows.append(_row("depth relay", oat, CADENCE["depth relay"], now, ever=oat is not None,
                     why=None if oat is not None else "the Kite bridge has not posted"))

    # 4 CHART RELAY, PER INDEX -- _SENSES["tape"][idx]["at"] (server.py:1130),
    # recorded since the frame route was written and read by nothing until now.
    for idx in sorted(tape_ats or {}):
        at = (tape_ats or {}).get(idx)
        rows.append(_row(f"chart {idx}", at, CADENCE["chart"], now, ever=at is not None,
                         why=None if at is not None else "no frame posted this process"))

    # 5 RECORD WRITER -- a quiet market genuinely writes no row for minutes, so
    # the cadence is 300; absent file with zero rows is "never started".
    rs = record_stat or {}
    rows.append(_row("record writer", rs.get("last_seen"), CADENCE["record writer"], now,
                     ever=bool(rs.get("exists")) and bool(rs.get("rows_today")),
                     why=None if rs.get("exists") else "no record file today",
                     rows_today=int(rs.get("rows_today") or 0),
                     file_mb=round(float(rs.get("file_mb") or 0.0), 1)))

    # 6 SENSES LOOP -- a thread that has quietly stopped must not read as a
    # quiet market, which is why /api/senses publishes `error` at all.
    up = senses.get("up_s")
    rows.append(_row("senses loop", None if up is None else now - 0.0,
                     CADENCE["senses loop"], now, error=senses.get("error"),
                     ever=up is not None,
                     why=None if up is not None else "the senses loop has not started",
                     up_s=int(up or 0)))

    _transition(rows)
    return {"ok": True, "now": now, "muted": False,
            "sources": rows,
            "coverage": health.get("coverage") or {},
            "ring": list(_RING)}
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_desk_health.py`
Expected: `7 passed`

- [ ] **Step 5: Add the route** — in `tapemap/server.py`, find `import desk_log` and replace with:

```python
import desk_health
import desk_log
```

Then insert **directly above** `        elif self.path.startswith("/api/desk"):` (this MUST sit above it — the dispatch is an ordered `startswith` chain):

```python
        elif self.path.startswith("/api/desk/health"):
            # ONE health object. A blind-check today has to fan out to four
            # routes and correlate them itself (inventory §6); this is that
            # correlation done once, server-side, plus the 200-transition ring
            # the RECORD screen's marks lane reads outage gaps from.
            from chain_live import _broker          # noqa: F401 -- parity with /api/health
            feed, feed_why = None, None
            src = getattr(self.poller, "src", None) if self.poller else None
            status_fn = getattr(src, "status", None)
            if callable(status_fn):
                feed = status_fn() or None
                if feed is None:
                    feed_why = "chain source has no feed yet (starting up)"
            else:
                feed_why = "no Upstox chain source in this server mode"
            # ponytail: `built_at` scraped from the head of the payload bytes.
            # A chain box is {"payload", "spot", "err_tag"} (chain_live.py:284)
            # -- there is no "ts" key on it -- and json.loads of a ~200 KB
            # payload every 2 s for one float is the wrong trade. The key is
            # emitted sixth (chain_live.py:310), so 300 bytes always contains
            # it. Parse the payload properly if the shape ever changes.
            chains_at = {}
            for i in (self.chains or {}):
                pl = (self.chains.get(i) or {}).get("payload")
                m = re.search(rb'"built_at":\s*([0-9.]+)', (pl or b"")[:300]) if pl else None
                chains_at[i] = float(m.group(1)) if m else None
            with _SENSES_LOCK:
                tape_ats = {i: (_SENSES["tape"].get(i) or {}).get("at")
                            for i in instruments.ENABLED}
                s_err, s_up, o_at = _SENSES["err"], _SENSES["started"], _SENSES["orders_at"]
            rpath = str(ROOT / frame_log.day_path(time.strftime("%Y-%m-%d")))
            try:
                rst = os.stat(rpath)
                rec = {"last_seen": rst.st_mtime, "file_mb": rst.st_size / 1048576.0,
                       "exists": True,
                       "rows_today": len(record_read.rows(rpath, self._idx()))}
            except OSError:
                rec = {"last_seen": None, "file_mb": 0.0, "exists": False, "rows_today": 0}
            self._json(json.dumps(desk_health.build(
                {"feed": feed, "feed_why": feed_why, "coverage": _coverage()},
                {"error": str(s_err) if s_err else None,
                 "up_s": (time.time() - s_up) if s_up else None, "orders_at": o_at},
                chains_at, tape_ats, rec, time.time()), default=str).encode())
```

- [ ] **Step 6: Add the `re` import if it is missing**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && grep -n "^import re$" server.py`
If that prints nothing, find `import os` (server.py:19) and replace with:

```python
import os
import re
```

- [ ] **Step 7: Run the suite and commit**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server" && python -m pytest -q 2>&1 | tail -5`
Expected: `3 failed, 1145 passed` — only the three pre-existing `test_desk_numbers.py` failures.

```bash
git add desk_health.py test_desk_health.py server.py
git commit -m "desk_health: one health object, six sources, four levels, a 200-transition ring; GET /api/desk/health"
```

---

### Task 7: `survival.py` — will I survive being wrong, and `GET /api/desk/today`

**Goal:** the gap table, the square-off distance and the days of income at risk, computed for a book that is **named** — never for a hypothetical printed as hers (spec R3b, anti-pattern 13).

**Files:** Create `tapemap/survival.py`, `tapemap/test_survival.py`. Modify `tapemap/server.py` (import + one `elif`).

**Interfaces:**
- Produces: `survival.build(legs, strikes, spot, capital, lot, theta_day) -> dict` per spec §H.2, where
  `legs` = `[{"k": float, "side": "CE"|"PE", "qty": int}]` (qty negative = short, in lots),
  `strikes` = `/api/chain.strikes` rows `{"k": float, "ce": {...,"delta","gamma"}, "pe": {...}}`,
  `theta_day` = rupees per day, **a float**.
- Also produced by the `/api/desk/today` route: the whole §H.2 body — `gate`, `board` (each row now carrying `yesterday` / `yesterday_why`, ruling D9), `survival` (**the PAPER book**, ruling D5), `candidate` (the hand-entered `data/book.json` hypothetical, the second row-group behind `c`), `adjust` (the adjustment brake, ruling D10) and `paid`.
- Consumes: `record_read.yesterday(prev_path, idx, heat_today)` from Task 2. D9 and D10 both ride this one route rather than adding a seventh.

**Three real-code facts the spec's field names glossed:**
1. `desk._naked_margin(f, lot_size, n_naked_legs)` is at **desk.py:1120** and `NAKED_MARGIN_PCT = 0.11` at **desk.py:149** (the spec said 147). `_NAKED_MODEL_NOTE` (desk.py:1130) is the sentence to print; it already says "NOT the broker's SPAN number".
2. **`theta_day_est` is an OBJECT, not a number.** `/api/paperdesk.desk.theta_day_est` is `{"rupees", "legs", "why", "no_legs_why", "tag", "method"}` (trader.py:1058-1070). The number is `.rupees` and it is `None` when no leg was priceable. The route below reads `.rupees`; `survival.build` takes the float.
3. `/api/paperdesk.desk.risk.capital` and `/api/paperdesk.desk.lots` are the two fields the region title is built from (trader.py:889-897) — `lots` is a **sibling of** `risk`, not inside it.

**The gap table includes a `"0"` column** (ruling D5 confirms it). The spec's §H.2 JSON lists only `-2/-1/+1/+2`, but its own mockup prints five margin cells including `now`, and §J's check is `margin == desk._naked_margin(spot, lot, 2)` — which is the `now` column. `"0"` exists, with `pnl` 0.

**Paper is the table; the candidate is a second row-group (ruling D5).** The route builds `survival` from the PAPER desk's own open legs (`desk.open[].legs`, `book.py:48-62` — `strike`, `right`, `side`, `qty` in units) and `candidate` from `data/book.json`. They are two separate `survival.build` calls with two separate `whose` labels, never one merged leg list named with both books.

- [ ] **Step 1: Write the failing test** — create `tapemap/test_survival.py`:

```python
# tapemap/test_survival.py
"""Will I survive being wrong. The naked-leg FLOOR, never a broker's number."""
import desk as desk_mod
import survival


LOT = 75
SPOT = 23244.0


def _strikes():
    """A chain slice with real per-strike greeks, the shape /api/chain serves."""
    out = []
    for k in range(22800, 23801, 100):
        m = (k - SPOT) / SPOT
        out.append({"k": float(k),
                    "ce": {"ltp": 120.0, "delta": max(0.02, 0.5 - 6 * m), "gamma": 0.0004},
                    "pe": {"ltp": 110.0, "delta": min(-0.02, -0.5 - 6 * m), "gamma": 0.0004}})
    return out


def _strangle():
    return [{"k": 23600.0, "side": "CE", "qty": -1}, {"k": 22900.0, "side": "PE", "qty": -1}]


def test_a_two_leg_short_strangle_prices_at_the_naked_leg_floor():
    d = survival.build(_strangle(), _strikes(), SPOT, capital=2500000.0, lot=LOT, theta_day=8200.0)
    # FIVE columns including "0" (now) -- the mockup always printed five and
    # §J's own check is against the `now` margin (ruling D5).
    assert list(d["gap"]) == ["-2", "-1", "0", "+1", "+2"]
    assert d["gap"]["0"]["margin"] == round(desk_mod._naked_margin(SPOT, LOT, 2), 2)
    assert d["gap"]["0"]["pnl"] == 0.0
    assert d["basis"] == "~ floor, not SPAN"
    assert "SPAN" in d["margin_model"]


def test_free_crosses_zero_exactly_once_on_each_side_and_the_nearer_wins():
    # The naked-leg floor for this book is ~₹3.07L, so capital has to sit just
    # above it for free to cross inside the ±5 % scan at all. At ₹7L it never
    # crosses and the assertion below is unreachable.
    d = survival.build(_strangle(), _strikes(), SPOT, capital=340000.0, lot=LOT, theta_day=8200.0)
    assert d["sq_off"] is not None and d["sq_off_why"] is None
    assert d["sq_off"]["pct"] != 0 and d["sq_off"]["px"] > 0


def test_a_book_that_never_crosses_says_so_instead_of_printing_a_number():
    d = survival.build(_strangle(), _strikes(), SPOT, capital=50_000_000.0, lot=LOT, theta_day=8200.0)
    assert d["sq_off"] is None and d["sq_off_why"] == "free never crosses"


def test_days_of_income_is_the_worst_gap_over_the_theta_bill():
    d = survival.build(_strangle(), _strikes(), SPOT, capital=2500000.0, lot=LOT, theta_day=8200.0)
    worst = -min(g["pnl"] for g in d["gap"].values())
    assert d["days_of_income"] == round(worst / 8200.0, 1)
    # A ZERO OR NULL DIVISOR IS A HOLE, NEVER inf (ruling, contract fixes).
    d0 = survival.build(_strangle(), _strikes(), SPOT, capital=2500000.0, lot=LOT, theta_day=None)
    assert d0["days_of_income"] is None
    assert d0["days_of_income_why"] == "no theta collected yet"
    dz = survival.build(_strangle(), _strikes(), SPOT, capital=2500000.0, lot=LOT, theta_day=0.0)
    assert dz["days_of_income"] is None
    assert dz["days_of_income_why"] == "no theta collected yet"
    dn = survival.build(_strangle(), _strikes(), SPOT, capital=2500000.0, lot=LOT, theta_day=-500.0)
    assert dn["days_of_income"] is None
    assert dn["days_of_income_why"] == "no theta collected yet"


def test_no_legs_and_no_greeks_are_two_different_sentences():
    d = survival.build([], _strikes(), SPOT, capital=2500000.0, lot=LOT, theta_day=8200.0)
    assert d["gap"] == {} and d["gap_why"] == "no legs to price"
    bare = [{"k": 23600.0, "ce": {"ltp": 120.0}, "pe": {"ltp": 110.0}},
            {"k": 22900.0, "ce": {"ltp": 120.0}, "pe": {"ltp": 110.0}}]
    d2 = survival.build(_strangle(), bare, SPOT, capital=2500000.0, lot=LOT, theta_day=8200.0)
    assert d2["gap"] == {} and d2["gap_why"] == "chain has no greeks"


def test_the_book_is_always_named():
    d = survival.build(_strangle(), _strikes(), SPOT, capital=2500000.0, lot=LOT,
                       theta_day=8200.0, whose=["paper ₹25L · 2 lots"])
    assert d["whose"] == ["paper ₹25L · 2 lots"]
    assert survival.build([], [], SPOT, 2500000.0, LOT, None)["whose"] == []
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_survival.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'survival'`

- [ ] **Step 3: Create `tapemap/survival.py`**

```python
# tapemap/survival.py
"""survival.py -- WILL I SURVIVE BEING WRONG.

Not P&L. The hunt kills through MARGIN, not through opinion: the question a
seller's 09:14 screen has to answer is how far spot can move before free
capital crosses zero and something is FORCED. That is this module.

THE MARGIN IS desk.py's DOCUMENTED FLOOR, REUSED NOT RE-INVENTED:
`desk._naked_margin` (desk.py:1120) -- 11% of notional per naked leg, +60%
for each additional one (desk.py:149, 154). This stack cannot run SPAN
(desk.py:136-148) and must never print a number that reads like a broker's,
so `basis` is "~ floor, not SPAN" and travels in the region title, always.

THE BOOK IS ALWAYS NAMED (spec R3b). `whose` is a list of labels the caller
built -- "paper Rs 25L * 2 lots", "candidate * 5 lots". The operator's REAL
book is never wired into this stack; a survival number computed for a
hypothetical and printed as hers is exactly the toolb defect this replaces.

THE GAP TABLE is first-order-plus-gamma off the chain's OWN per-strike delta
and gamma (/api/chain.strikes; the broker supplies them). No greeks -> no
table and a sentence saying which, never a zero.

Pure, stdlib only, no I/O, no clock.
"""
from __future__ import annotations

from typing import List, Optional

import desk as desk_mod

GAPS_PCT = (-2.0, -1.0, 0.0, 1.0, 2.0)
SCAN_MAX_PCT = 5.0
SCAN_STEP_PCT = 0.05
BASIS = "~ floor, not SPAN"


def _leg_greeks(strikes, k, side):
    for s in strikes or []:
        try:
            if abs(float(s.get("k")) - float(k)) < 0.5:
                q = s.get("ce" if side == "CE" else "pe") or {}
                d, g = q.get("delta"), q.get("gamma")
                return (None, None) if d is None or g is None else (float(d), float(g))
        except (TypeError, ValueError):
            continue
    return (None, None)


def _pnl(legs, greeks, lot, dS) -> float:
    """First order plus gamma, per lot, summed over the book. Signed by qty:
    a short leg's qty is negative, so a rising call costs money."""
    total = 0.0
    for lg in legs:
        d, g = greeks[(lg["k"], lg["side"])]
        total += float(lg["qty"]) * lot * (d * dS + 0.5 * g * dS * dS)
    return total


def _margin(legs, spot_at, lot) -> float:
    shorts = [lg for lg in legs if float(lg.get("qty") or 0) < 0]
    if not shorts:
        return sum(abs(float(lg["qty"])) * lot * 0.0 for lg in legs)
    lots = max(abs(float(lg["qty"])) for lg in shorts)
    return desk_mod._naked_margin(spot_at, lot, len(shorts)) * lots


def build(legs, strikes, spot, capital, lot, theta_day, whose=None) -> dict:
    legs = [lg for lg in (legs or []) if lg.get("k") is not None and lg.get("side") in ("CE", "PE")]
    out = {"whose": list(whose or []), "capital": capital, "basis": BASIS,
           "margin_model": desk_mod._NAKED_MODEL_NOTE,
           "gap": {}, "gap_why": None,
           "sq_off": None, "sq_off_why": None,
           "days_of_income": None, "days_of_income_why": None}
    if not legs:
        out["gap_why"] = "no legs to price"
        out["sq_off_why"] = "no legs to price"
        out["days_of_income_why"] = "no legs to price"
        return out
    if spot is None or not lot:
        out["gap_why"] = "no spot or lot size"
        out["sq_off_why"] = out["days_of_income_why"] = "no spot or lot size"
        return out

    greeks = {(lg["k"], lg["side"]): _leg_greeks(strikes, lg["k"], lg["side"]) for lg in legs}
    if any(d is None for d, _ in greeks.values()):
        out["gap_why"] = "chain has no greeks"
        out["sq_off_why"] = out["days_of_income_why"] = "chain has no greeks"
        return out

    spot = float(spot)
    for pct in GAPS_PCT:
        dS = spot * pct / 100.0
        m = round(_margin(legs, spot + dS, lot), 2)
        key = "0" if pct == 0 else ("%+g" % pct)
        out["gap"][key] = {"pnl": round(_pnl(legs, greeks, lot, dS), 2),
                           "margin": m, "free": round(float(capital) - m, 2)}

    # THE SQUARE-OFF DISTANCE: the first move, either way, where free crosses 0
    # under the floor. Scanned rather than solved -- the margin floor is a
    # step-shaped model, not a differentiable one.
    best = None
    for sign in (-1.0, 1.0):
        pct = 0.0
        while pct <= SCAN_MAX_PCT:
            pct += SCAN_STEP_PCT
            dS = spot * sign * pct / 100.0
            if float(capital) - _margin(legs, spot + dS, lot) + _pnl(legs, greeks, lot, dS) < 0:
                cand = round(sign * pct, 2)
                if best is None or abs(cand) < abs(best):
                    best = cand
                break
    if best is None:
        out["sq_off_why"] = "free never crosses"
    else:
        out["sq_off"] = {"pct": best, "px": round(spot * (1 + best / 100.0), 0)}

    worst = -min(g["pnl"] for g in out["gap"].values())
    # A ZERO OR NULL DIVISOR IS A HOLE, NEVER `inf`. A book that is paying
    # theta rather than collecting it has no days of income to lose, and
    # printing an infinity (or a huge number) there reads as safety.
    if theta_day is None or not theta_day or float(theta_day) <= 0:
        out["days_of_income_why"] = "no theta collected yet"
    elif worst <= 0:
        out["days_of_income_why"] = "no gap in the table loses money"
    else:
        out["days_of_income"] = round(worst / float(theta_day), 1)
    return out
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_survival.py`
Expected: `6 passed`

- [ ] **Step 5: Add the route** — in `tapemap/server.py`, insert **directly above** `        elif self.path.startswith("/api/desk"):` and **below** the `/api/desk/health` branch added in Task 6:

```python
        elif self.path.startswith("/api/desk/today"):
            # THE 09:14 SCREEN: can I sell today and on which index, will I
            # survive being wrong, is anyone paying me. The gate is the FRAME's
            # own head.gate -- never recomputed here, so TODAY and the
            # extension's chip can never disagree.
            idx = self._idx()
            with _SENSES_LOCK:
                frames = {i: _SENSES["frame"].get(i) for i in instruments.ENABLED}
                pt, boards = _SENSES.get("ptrader"), _SENSES.get("warmap")
                wm = boards.states() if boards is not None else {}
                tape_ats = {i: (_SENSES["tape"].get(i) or {}).get("at") for i in instruments.ENABLED}
            fr = frames.get(idx) or {}
            gate = ((fr.get("head") or {}).get("gate")
                    or {"level": "PATA NAHI", "reason": "no frame posted this process",
                        "holes": ["no frame posted this process"], "would_be": None,
                        "would_be_reason": None, "tag": "I"})
            # YESTERDAY (ruling D9): the newest day file BEFORE today. The
            # record already streams any day, so the prior session costs one
            # more pointing of the same reader -- not a seventh route.
            import glob as _glob
            _today_day = time.strftime("%Y-%m-%d")
            _prev = sorted(p for p in _glob.glob(str(ROOT / "data" / "frame" / "frame_*.jsonl"))
                           if os.path.basename(p)[6:16] < _today_day)
            prev_path = _prev[-1] if _prev else None
            prev_day = os.path.basename(prev_path)[6:16] if prev_path else None
            board = []
            for i in instruments.ENABLED:
                f = frames.get(i) or {}
                z = ((f.get("where") or {}).get("z"))
                heat = ((wm.get(i) or {}).get("heat")) or []
                worst = max(heat, key=lambda h: max(h.get("ce_pain") or 0, h.get("pe_pain") or 0)) if heat else None
                carry = None
                if worst:
                    sidew = "CE" if (worst.get("ce_pain") or 0) >= (worst.get("pe_pain") or 0) else "PE"
                    carry = f"{sidew} {int(worst.get('k') or 0)}"
                yday = record_read.yesterday(prev_path, i, heat_today=heat) if prev_path else None
                board.append({
                    "idx": i, "z": z,
                    "z_why": None if z is not None else "no chart posting",
                    "carry": carry,
                    "carry_why": None if carry else f"no warmap for {i}",
                    "yesterday": yday,
                    "yesterday_why": (None if yday else
                                      (f"no record for {prev_day}" if prev_day
                                       else "no prior day file on disk")),
                    "health": "live" if tape_ats.get(i) else "never started"})
            desk_state = pt.state({}) if pt is not None else {}
            risk = (desk_state.get("risk") or {})
            lots, cap = desk_state.get("lots"), risk.get("capital")
            lot = fr.get("lot") or 0
            chain = _chain_doc(self.poller, idx) or {}
            theta = ((desk_state.get("theta_day_est") or {}).get("rupees"))
            # PAPER IS THE TABLE (ruling D5). The open paper legs are
            # book.Position.legs (book.py:48-62): `strike`, `right` CE|PE|FUT,
            # `side` BUY|SELL, `qty` in UNITS. survival wants LOTS, signed, so
            # a short is negative. A FUT leg has no strike and no naked-leg
            # floor here, so it is skipped rather than guessed at.
            paper_legs = []
            for pos in (desk_state.get("open") or []):
                for lg in (pos.get("legs") or []):
                    if lg.get("right") not in ("CE", "PE") or lg.get("strike") is None:
                        continue
                    n = (float(lg.get("qty") or 0) / lot) if lot else 0.0
                    paper_legs.append({"k": float(lg["strike"]), "side": lg["right"],
                                       "qty": (-n if lg.get("side") == "SELL" else n)})
            surv = survival.build(paper_legs, chain.get("strikes"), chain.get("spot"),
                                  cap or 0.0, lot, theta,
                                  whose=([f"paper ₹{(cap or 0) / 100000:.0f}L · {lots} lots"]
                                         if cap else []))
            # THE CANDIDATE IS A SECOND ROW-GROUP, OFF BY DEFAULT, BEHIND `c`
            # (ruling D5). She has no wired book and will not get one, so a
            # hand-entered candidate is the only way the survival question is
            # answerable at all -- but it is never the default table, and its
            # numbers are never printed under her name.
            try:
                import json as _json
                bk = _json.loads((ROOT / "data" / "book.json").read_text(encoding="utf-8"))
            except Exception:
                bk = None                 # absent renders NOTHING, not a hole (spec §M)
            cand = None
            if bk:
                cand = survival.build(
                    [{"k": l["k"], "side": l["side"], "qty": l["qty"]}
                     for l in (bk.get("legs") or [])],
                    chain.get("strikes"), chain.get("spot"), cap or 0.0, lot, theta,
                    whose=[f"{bk.get('whose') or 'candidate'} · {bk.get('lots')} lots"])
            # THE ADJUSTMENT BRAKE (ruling D10). Free execution's failure mode
            # is over-adjustment, so the brake must be deliberate and visible.
            # `day_trades` is ONE ROUND TRIP PER PID (trader.py:179), so a
            # second round trip on a leg already traded today is a re-entry on
            # the same position -- that is what is counted. It advises; it
            # blocks nothing, because there is no order path.
            trades = desk_state.get("day_trades")
            adjust_cap = int((bk or {}).get("adjust_cap") or 6)
            if trades is None:
                adjust = {"n": None, "cap": adjust_cap,
                          "why": (desk_state.get("day_trades_why")
                                  or "the paper desk has no trade log")}
            else:
                seen, n_adj = set(), 0
                for t in trades:
                    key = (t.get("idx"), t.get("strike"), t.get("right"))
                    if key in seen:
                        n_adj += 1
                    seen.add(key)
                adjust = {"n": n_adj, "cap": adjust_cap, "why": None}
            fit = (asdict(_surface_read(self.poller, idx)) or {}).get("fit") or {}
            rv5, rv5_why = _rv5(idx)
            iv, rv = fit.get("atm_iv"), (rv5 or {}).get("rv")
            ivrv, ivrv_why = _ivrv_for(self, idx)
            ser = chain.get("series") or []
            atm = chain.get("atm")
            def _straddle(row):
                if not row or atm is None:
                    return None
                return None
            paid = {"atm_iv": iv, "atm_iv_why": None if iv else "surface did not fit",
                    "rv": rv, "rv_why": None if rv else (rv5_why or "no rv5"),
                    "ivrv": ivrv, "ivrv_why": ivrv_why,
                    "straddle": None, "straddle_why": "no chain series row for the open"
                                      if not ser else None,
                    "spot_move_pct": None, "vega_attack": False, "sigma_pct": None,
                    # THE LEG sigma-DISTANCE, PRINTED ONCE (ruling, designer's
                    # list). Every leg on screen appears here and nowhere else,
                    # and each says whose book it belongs to.
                    "strikes": ([{"k": l["k"], "side": l["side"], "sigma": None,
                                  "whose": "paper"} for l in paper_legs]
                                + [{"k": l["k"], "side": l["side"], "sigma": None,
                                    "whose": (bk or {}).get("whose") or "candidate"}
                                   for l in ((bk or {}).get("legs") or [])])}
            if ser:
                first, now_row = ser[0], ser[-1]
                o = (first.get("ce_ltp") or 0) + (first.get("pe_ltp") or 0)
                n = (now_row.get("ce_ltp") or 0) + (now_row.get("pe_ltp") or 0)
                if o and n:
                    paid["straddle"] = {"open": round(o, 1), "now": round(n, 1),
                                        "d": round(n - o, 1)}
                    sp = chain.get("spot")
                    if sp:
                        paid["sigma_pct"] = round(100.0 * n / float(sp), 2)
                        mv = 100.0 * (float(sp) - float(first.get("spot") or sp)) / float(sp)
                        paid["spot_move_pct"] = round(mv, 3)
                        paid["vega_attack"] = bool(n >= 1.05 * o and abs(mv) < 0.15)
                else:
                    paid["straddle_why"] = "chain series carries no ATM premiums"
            self._json(json.dumps({"ok": True, "idx": idx, "ts": fr.get("ts"),
                                   "gate": gate, "board": board,
                                   "survival": surv, "candidate": cand,
                                   "adjust": adjust, "paid": paid}, default=str).encode())
```

- [ ] **Step 6: Add the import** — find `import structure` or, if absent, find `import score_frame` and add `import survival` in alphabetical position. Run:

`cd "C:/Users/kaam/Desktop/operator mode/tapemap" && grep -n "^import surface as surface_mod$" server.py`

Then replace that line with:

```python
import surface as surface_mod
import survival
```

- [ ] **Step 7: Delete the dead helper** — the `_straddle` inner function above is a leftover stub with no caller. Remove these three lines from the branch you just inserted:

```python
            def _straddle(row):
                if not row or atm is None:
                    return None
                return None
```

and the now-unused `atm = chain.get("atm")` line directly above them.

- [ ] **Step 8: Run the suite and commit**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server" && python -m pytest -q 2>&1 | tail -5`
Expected: `3 failed, 1151 passed` — only the three pre-existing `test_desk_numbers.py` failures.

```bash
git add survival.py test_survival.py server.py
git commit -m "survival: the gap table, square-off distance and days of income on the naked-leg floor; GET /api/desk/today"
```

---

### Task 8: `record_read.visits()` and `.series()`, and `GET /api/day/visits` + `GET /api/series`

**Goal:** the honest ledger — every zone visit with the miss as the first word, and every forward population with its level, which tops out at `SHAK` because no kill rule is written.

**Files:** Modify `tapemap/record_read.py` (append two functions), `tapemap/test_record_read.py` (append tests). Modify `tapemap/server.py` (two `elif` branches).

**Interfaces:**
- Consumes: `record_read._iter`, `record_read._cached`, `record_read.HORIZON_MIN`, `record_read.SERIES_MAX_MB` from Task 2.
- Produces: `record_read.visits(path, idx) -> list[dict]` (spec §H.5) and `record_read.series(day_paths: list[str]) -> list[dict]` (spec §H.6).

**Where the forward cells really live:** `score_frame` fills **`taps[].ex`** — the tap dicts on the row's own top-level `taps` list (frame.py:447, score_frame.py:29-43), keyed `"1"`, `"3"`, `"6"`, `"90m"`, `"180m"`. There is no `ex` block on a visit and no visit population in the scorer. So `visits()` matches each visit to the nearest same-side tap and reads **that tap's** cells: no new horizon population is created (spec R5), and the card shows the scorer's own `+30 m (6 bars)` and `+90 m`.

**`adverse` is not in the scorer at all.** It is computed here from the record's own `where.px` series inside the 30-minute window, and `adverse_src` says so on every row rather than letting a reader assume the scorer produced it.

**σ AND EARNED, DEFINED ONCE (ruling D2).** `sigma` is `where.sigma` **at `t0`** — the VWAP band half-width in points, the unit the zone itself is cut in (`d2 = 2σ`). The rotation trade is entered at the 2σ edge and pays on the way back, so **EARNED = favourable excursion ≥ 2σ within 6 bars** and **adverse ≥ 1σ** is the WRONG/SPARED threshold. One source, one unit, one pair of thresholds.

**THE OUTCOME LADDER IS ORDERED AND EXHAUSTIVE (ruling D1).** First match wins:

| # | word | condition |
|---|---|---|
| 1 | `WRONG` | fired ∧ adverse ≥ 1σ |
| 2 | `CALLED` | fired ∧ EARNED |
| 3 | `FALSE` | fired ∧ neither |
| 4 | `MISSED` | not fired ∧ EARNED |
| 5 | `SPARED` | not fired ∧ adverse ≥ 1σ |
| 6 | `QUIET` | not fired ∧ neither |
| 7 | `PATA NAHI` | a cell the ladder needs is null — carries `outcome_why` |

`FALSE` is the whole point: **a visit where the tool fired and nothing happened must never sit in the same bucket as a visit where it correctly said nothing.** Rules 1 and 2 are evaluated before rule 7 because a decidable WRONG or CALLED is still decidable when some *other* cell is missing; everything below them needs every cell. Tally order on the card is **missed · false · wrong · called · spared · quiet (n)** — the two ways the tool is wrong print first.

**Level rule (spec §M):** `PATA NAHI` until `n >= 20`, then `SHAK`. It never says "works", and `NAHI` needs a kill rule that exists and fires — none is written. **No `measure`, no `base` (ruling D6):** a series row serves `name`, `n`, `sessions`, `started`, `horizon`, `kill`, `level`, `why` and nothing else. `0.54 vs base 0.49` is a hit rate in a moustache and violates CLAUDE.md rule 4.

- [ ] **Step 1: Write the failing tests** — append to `tapemap/test_record_read.py`:

```python
def _tap(t_ms, side, ex):
    return {"t": t_ms, "tx": t_ms, "i0": 6, "side": side, "price": 23244.0, "z": -2.0, "ex": ex}


def _visit_rows(fire=False, ex=None, px1=23238.0):
    """One visit, 09:45 -> 10:07. σ is 18 points (`where.sigma` at t0), so
    EARNED is +36 and adverse is -18. The default cell is +137 in 6 bars: a
    clean 7.6σ favourable excursion with nothing adverse behind it."""
    taps = [_tap(13500000, 1, ex if ex is not None
                 else {"1": 20.0, "3": 90.0, "6": 137.0, "90m": 151.0})]
    a = _row("09:45", "WAITING", False, -1.9, 23244.0, "buy@09:45")
    b = _row("10:07", "WAITING", fire, -1.2, px1, "buy@09:45")
    for r in (a, b):
        r["taps"] = taps
    return [a, b]


def test_a_visit_that_earned_and_was_never_called_is_MISSED(tmp_path):
    record_read._CACHE.clear()
    p = _file(tmp_path, _visit_rows())
    v = record_read.visits(p, "NIFTY")
    assert len(v) == 1
    c = v[0]
    assert c["t0"] == "09:45" and c["t1"] == "10:07" and c["side"] == "buy" and c["band"] == "d2"
    assert c["sigma"] == 18.0 and c["sigma_why"] is None
    assert c["ex"]["6"] == 137.0 and c["ex"]["90m"] == 151.0
    assert c["fired"] is False
    assert c["outcome"] == "MISSED"      # >= 2 sigma in 6 bars and never fired
    assert c["outcome_why"] is None
    assert c["said"]["confirm"] == "not wired"
    assert c["votes"] is None and c["votes_why"] == "ballot not built"


def test_the_outcome_ladder_is_ordered_and_first_match_wins(tmp_path):
    """Ruling D1. WRONG -> CALLED -> FALSE -> MISSED -> SPARED -> QUIET, and
    PATA NAHI when a cell the ladder needs is null. The two ways the tool is
    WRONG are separable from the two ways it was right, and a fired-and-nothing
    visit never shares a bucket with a correct silence."""
    def outcome(rows):
        record_read._CACHE.clear()
        return record_read.visits(_file(tmp_path, rows), "NIFTY")[0]

    # fired, +137 = 7.6 sigma, nothing adverse -> CALLED
    assert outcome(_visit_rows(fire=True))["outcome"] == "CALLED"

    # FIRED AND NOTHING HAPPENED -> FALSE, and never QUIET. This is the whole
    # reason the ladder was rewritten: a false alarm is not a correct silence.
    c = outcome(_visit_rows(fire=True, ex={"6": 4.0, "90m": 6.0}))
    assert c["outcome"] == "FALSE"
    assert c["outcome"] != "QUIET"

    # fired with BOTH a 2 sigma favourable and a 1 sigma adverse excursion:
    # WRONG wins, because it is first on the ladder.
    assert outcome(_visit_rows(fire=True, px1=23220.0))["outcome"] == "WRONG"

    # never fired, 1 sigma adverse, nothing earned -> SPARED
    assert outcome(_visit_rows(ex={"6": 4.0, "90m": 6.0}, px1=23220.0))["outcome"] == "SPARED"

    # never fired, neither -> QUIET
    assert outcome(_visit_rows(ex={"6": 4.0, "90m": 6.0}))["outcome"] == "QUIET"

    # no tap of this side: the excursion cell is null, so the visit is not
    # adjudicable and says why -- it is not quietly filed as QUIET.
    blind = _visit_rows()
    for r in blind:
        r["taps"] = []
    c = outcome(blind)
    assert c["outcome"] == "PATA NAHI"
    assert c["outcome_why"] == "no +6-bar excursion for this visit"


def test_a_visit_with_no_sigma_is_not_adjudicable_rather_than_scored_at_zero(tmp_path):
    record_read._CACHE.clear()
    rows = _visit_rows()
    for r in rows:
        r["where"]["sigma"] = None
    p = _file(tmp_path, rows)
    c = record_read.visits(p, "NIFTY")[0]
    assert c["sigma"] is None and c["sigma_why"] == "no sigma on the first row of the visit"
    # sigma IS the threshold: with no sigma there is no 2 sigma and no 1 sigma,
    # so the ladder cannot be walked at all.
    assert c["outcome"] == "PATA NAHI" and c["outcome_why"] == "no sigma at t0"


def test_series_tops_out_at_SHAK_and_never_says_works(tmp_path):
    record_read._CACHE.clear()
    rows = []
    for i in range(25):
        r = _row(f"09:{45 + i % 14:02d}", "WAITING", False, -1.0, 23244.0, None)
        r["taps"] = [_tap(13500000 + i, 1, {"6": 30.0})]
        r["setup"]["tells"] = [{"name": "PIN", "target": "23400", "resolved": "target"}]
        r["setup"]["control"] = [{"p": 23100.0, "kind": "PE", "dist": 10.0,
                                  "same_distance": True, "resolved": "expired"}]
        rows.append(r)
    p = _file(tmp_path, rows)
    s = {r["name"]: r for r in record_read.series([p])}
    assert s["tells resolved"]["level"] == "SHAK" and s["tells resolved"]["why"] == "no kill rule"
    assert s["control"]["level"] == "SHAK"
    assert all(r["level"] in ("PATA NAHI", "SHAK", "NAHI") for r in s.values())
    assert all(r["horizon"] == 30 for r in s.values())
    assert s["tells resolved"]["sessions"] == 1
    # RULING D6: no `measure`, no `base`. A row serves these eight fields and
    # nothing else -- "0.54 vs base 0.49" is a hit rate in a moustache.
    for r in s.values():
        assert set(r) == {"name", "n", "sessions", "started", "horizon",
                          "kill", "level", "why"}


def test_a_thin_population_is_PATA_NAHI_with_its_n(tmp_path):
    record_read._CACHE.clear()
    r = _row("09:45", "WAITING", False, -1.0, 23244.0, None)
    r["taps"] = [_tap(13500000, 1, {"6": 30.0})]
    p = _file(tmp_path, [r])
    taps = next(x for x in record_read.series([p]) if x["name"] == "taps")
    assert taps["n"] == 1 and taps["level"] == "PATA NAHI" and taps["why"] == "n<20"
```

- [ ] **Step 2: Run to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_record_read.py -k "visit or series or outcome"`
Expected: FAIL — `AttributeError: module 'record_read' has no attribute 'visits'`

- [ ] **Step 3: Append to `tapemap/record_read.py`**

```python
# ── the honest ledger ───────────────────────────────────────────────────────

# THE OUTCOME LADDER, IN TALLY ORDER (ruling D1): the two ways the tool is
# wrong print first. The ladder itself is EVALUATED in a different order --
# WRONG, CALLED, then the rest -- and that order lives in `visits()` below.
_OUTCOMES = ("MISSED", "FALSE", "WRONG", "CALLED", "SPARED", "QUIET", "PATA NAHI")
EARNED_SIGMA = 2.0           # favourable >= 2 sigma within 6 bars IS the rotation trade
ADVERSE_SIGMA = 1.0          # adverse >= 1 sigma is the WRONG / SPARED threshold
SERIES_MIN_N = 20            # below this a population is PATA NAHI, not a reading


def _hhmm_of(t_ms):
    try:
        s = (int(t_ms) // 1000 + 19800) % 86400
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"
    except (TypeError, ValueError):
        return None


def _mins(hhmm) -> Optional[int]:
    try:
        h, m = str(hhmm).split(":")[:2]
        return int(h) * 60 + int(m)
    except (TypeError, ValueError):
        return None


def visits(path: str, idx: str = "NIFTY") -> List[dict]:
    """One card per zone visit, grouped by `setup.visit` (frame.py:389-407).

    THE FORWARD CELLS ARE THE SCORER'S OWN. score_frame fills `taps[].ex` at
    +1/+3/+6 bars and +90/+180 minutes (score_frame.py:20, 29-43); the card
    shows +30 m (6 bars) and +90 m, which are two of those five. No new
    horizon population is created here (spec R5).

    `adverse` is NOT in the scorer -- it is measured from this record's own
    `where.px` inside the 30-minute window, and `adverse_src` says so.

    SIGMA IS `where.sigma` AT t0 (ruling D2): the VWAP band half-width in
    points, the unit the zone itself is cut in (d2 = 2 sigma). The rotation
    trade is entered at the 2 sigma edge and pays on the way back, so EARNED
    is a favourable excursion >= 2 sigma within 6 bars and adverse >= 1 sigma
    is the WRONG / SPARED threshold. One source, one unit, one pair of
    thresholds -- the 4x disagreement that produced this ruling is gone.

    THE OUTCOME LADDER IS ORDERED AND EXHAUSTIVE (ruling D1), first match wins:
        1 WRONG      fired and adverse >= 1 sigma
        2 CALLED     fired and EARNED
        3 FALSE      fired and neither
        4 MISSED     not fired and EARNED
        5 SPARED     not fired and adverse >= 1 sigma
        6 QUIET      not fired and neither
        7 PATA NAHI  a cell the ladder needs is null; carries `outcome_why`
    FALSE is the point of the rewrite: a visit where the tool FIRED AND
    NOTHING HAPPENED must never sit in the same bucket as a visit where it
    correctly said nothing. Rules 1 and 2 are tested before rule 7 because a
    decidable WRONG or CALLED stays decidable when some other cell is missing;
    everything below them needs every cell.

    THE MISS IS THE FIRST WORD, and the tally is counts only. No percentage,
    no hit rate: house rule 4."""
    def build() -> List[dict]:
        groups: dict = {}
        order: List[str] = []
        for r in _iter(path, idx):
            key = (r.get("setup") or {}).get("visit")
            if not key:
                continue
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(r)
        out = []
        for key in order:
            rs = groups[key]
            first, last = rs[0], rs[-1]
            w0, s0 = first.get("where") or {}, first.get("setup") or {}
            t0 = str(first.get("ts") or "")[:5]
            t1 = str(last.get("ts") or "")[:5]
            side = str(key).split("@")[0] if "@" in str(key) else (s0.get("side") or "buy")
            sigma = w0.get("sigma")
            want = 1 if side == "buy" else -1
            m0 = _mins(t0)
            # the scorer's own cells, from the nearest same-side tap of this visit
            cand = [t for t in (last.get("taps") or [])
                    if (t.get("side") or 1) == want and _hhmm_of(t.get("t")) is not None]
            tap = None
            if cand and m0 is not None:
                tap = min(cand, key=lambda t: abs((_mins(_hhmm_of(t["t"])) or 0) - m0))
            ex_raw = (tap or {}).get("ex") or {}
            ex = {"6": ex_raw.get("6"), "90m": ex_raw.get("90m")}
            ex_why = None if tap else "no tap of this side in the record"
            # adverse, from this record's own prices inside the window
            base = w0.get("px")
            adv = None
            if base is not None and m0 is not None:
                moves = [float(rr["where"]["px"]) - float(base) for rr in rs
                         if (rr.get("where") or {}).get("px") is not None
                         and (_mins(str(rr.get("ts") or "")[:5]) or 0) - m0 <= HORIZON_MIN]
                if moves:
                    adv = round(min(want * m for m in moves), 1)
            fired = any(bool((rr.get("setup") or {}).get("fire")) for rr in rs)
            # THE LADDER (ruling D1), against sigma = where.sigma at t0 (D2).
            earned = (sigma is not None and ex["6"] is not None
                      and ex["6"] >= EARNED_SIGMA * sigma)
            hurt = (sigma is not None and adv is not None
                    and adv <= -ADVERSE_SIGMA * sigma)
            if sigma is None:
                blind = "no sigma at t0"
            elif ex["6"] is None:
                blind = "no +6-bar excursion for this visit"
            elif adv is None:
                blind = "no price in the 30-minute window"
            else:
                blind = None
            outcome_why = None
            if fired and hurt:
                outcome = "WRONG"              # 1
            elif fired and earned:
                outcome = "CALLED"             # 2
            elif blind:
                outcome, outcome_why = "PATA NAHI", blind      # 7
            elif fired:
                outcome = "FALSE"              # 3: fired and nothing happened
            elif earned:
                outcome = "MISSED"             # 4
            elif hurt:
                outcome = "SPARED"             # 5
            else:
                outcome = "QUIET"              # 6: it correctly said nothing
            flow_n = max(len((rr.get("setup") or {}).get("flow") or []) for rr in rs)
            out.append({
                "t0": t0, "t1": t1, "side": side, "band": "d2" if side == "buy" else "u2",
                "ref": w0.get("px"), "sigma": sigma,
                "sigma_why": None if sigma is not None else "no sigma on the first row of the visit",
                "fired": fired,
                "said": {"state": s0.get("state"), "flow_n": flow_n,
                         "confirm": ((s0.get("confirm") or {}).get("value") or "not wired")},
                "ex": ex, "ex_why": ex_why,
                "adverse": {"6": adv},
                "adverse_src": "this record's own prices, not the scorer",
                "outcome": outcome, "outcome_why": outcome_why,
                "votes": None, "votes_why": "ballot not built",
            })
        return out
    return _cached("visits", path, idx, build)


def _level_for(n: int) -> tuple:
    """PATA NAHI until n>=20, then SHAK until a kill rule is WRITTEN and FIRES.
    It never says "works" (spec §M): NAHI needs a rule that exists."""
    return ("PATA NAHI", f"n<{SERIES_MIN_N}") if n < SERIES_MIN_N else ("SHAK", "no kill rule")


def series(day_paths) -> List[dict]:
    """The forward populations, one row each, across the day files given.

    Cached per day path by (mtime, size), so counting `sessions` is not an
    O(days x rows) rescan on every 10 s poll.

    A day file larger than SERIES_MAX_MB is REFUSED, in words. That only
    happens on a record written before frame_log's quantised signature landed
    (116 MB on 2026-09-16); scanning it would stall the request, and a
    request that never returns is worse than a named refusal."""
    names = ("taps", "tells resolved", "control", "vpin ≥ 0.9", "paper strategies")
    agg = {k: {"n": 0, "sessions": 0, "started": None} for k in names}
    refused = []
    for p in sorted(day_paths or []):
        st = _stamp(p)
        if st is None:
            continue
        if st[1] / 1048576.0 > SERIES_MAX_MB:
            refused.append(os.path.basename(p))
            continue

        def build(p=p):
            day_n = {k: 0 for k in names}
            seen_taps = set()
            for r in _iter(p, None):
                s = r.get("setup") or {}
                for t in r.get("taps") or []:
                    if (t.get("ex") or {}).get("6") is not None:
                        seen_taps.add((t.get("i0"), t.get("side"), t.get("t")))
                day_n["tells resolved"] += sum(1 for t in s.get("tells") or []
                                               if t.get("resolved"))
                day_n["control"] += sum(1 for c in s.get("control") or []
                                        if c.get("same_distance") and c.get("resolved"))
            day_n["taps"] = len(seen_taps)
            return day_n
        day_n = _cached("series", p, "", build)
        stamp_day = os.path.basename(p).replace("frame_", "").replace(".jsonl", "")
        for k in names:
            if day_n.get(k):
                agg[k]["n"] += day_n[k]
                agg[k]["sessions"] += 1
                if agg[k]["started"] is None or stamp_day < agg[k]["started"]:
                    agg[k]["started"] = stamp_day

    out = []
    for k in names:
        a = agg[k]
        # EIGHT FIELDS, NO `measure`, NO `base` (ruling D6). A hit rate with a
        # baseline beside it is still a hit rate, and house rule 4 forbids it.
        if k in ("vpin ≥ 0.9", "paper strategies"):
            out.append({"name": k, "n": 0, "sessions": 0, "started": None, "horizon": HORIZON_MIN,
                        "kill": None, "level": "PATA NAHI",
                        "why": "not counted from the record"})
            continue
        lvl, why = _level_for(a["n"])
        if refused and a["n"] == 0:
            lvl, why = "PATA NAHI", "record file too large to scan"
        out.append({"name": k, "n": a["n"], "sessions": a["sessions"], "started": a["started"],
                    "horizon": HORIZON_MIN, "kill": None, "level": lvl, "why": why})
    return out
```

- [ ] **Step 4: Run the tests**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_record_read.py`
Expected: `10 passed`

- [ ] **Step 5: Add the two routes** — insert **directly above** `        elif self.path.startswith("/api/desk"):`:

```python
        elif self.path.startswith("/api/day/visits"):
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            idx = self._idx()
            path = str(ROOT / frame_log.day_path(day))
            self._json(json.dumps(record_read.visits(path, idx), default=str).encode())
        elif self.path.startswith("/api/series"):
            # THE FORWARD POPULATIONS. Level tops out at SHAK: NAHI needs a
            # kill rule that exists and fires, and none is written. It never
            # says "works" -- house rule 4. A row serves name, n, sessions,
            # started, horizon, kill, level, why -- no `measure`, no `base`
            # (ruling D6).
            import glob as _glob
            paths = sorted(_glob.glob(str(ROOT / "data" / "frame" / "frame_*.jsonl")))
            self._json(json.dumps(record_read.series(paths), default=str).encode())
```

- [ ] **Step 6: Run the suite and commit**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server" && python -m pytest -q 2>&1 | tail -5`
Expected: `3 failed, 1156 passed` — only the three pre-existing `test_desk_numbers.py` failures.

```bash
git add record_read.py test_record_read.py server.py
git commit -m "record_read: visit cards off the scorer's own horizons and the forward series that tops out at SHAK; GET /api/day/visits, /api/series"
```

---

### Task 9: Phase A gate — prove the brain before a single UI file is written

**Goal:** the three things spec §K says must be true before Phase B starts.

**Files:** none. This task edits nothing and commits nothing.

- [ ] **Step 1: The whole suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q 2>&1 | tail -5`
Expected: `3 failed, 1156 passed`. The three are `test_desk_numbers.py::test_a_short_book_collects_theta_so_the_estimate_is_positive`, `::test_a_long_book_pays_theta`, `::test_a_leg_with_no_iv_is_named_not_silently_dropped` — pre-existing, DO NOT FIX THEM.

- [ ] **Step 2: The gate can leave grey on a fixture with every input present**

Run:
```bash
cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import gate; print(gate.state(1.2, '2026-09-30', '2026-09-16', 0.1, {}))"
```
Expected output contains `'level': 'TRADE'` and `'holes': []`.

- [ ] **Step 3: The record file grows at yesterday's rate, not today's**

Run:
```bash
cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import frame_log as F; f={'idx':'NIFTY','walls':{'rows':[{'p':23400.0,'kind':'S','state':'held'}]},'setup':{'state':'WAITING','fire':False,'tells':[]},'missing':[]}; import copy; g=copy.deepcopy(f); g['walls']['rows'][0]['p']=23401.9; print(F.sig(f)==F.sig(g))"
```
Expected: `True`

- [ ] **Step 4: Record what the executor must hand the owner**

Write one line into the session notes (no file in the repo): "Phase A complete on `feature/operator-objects`; six new routes exist in source but NOT on the live server — the owner restarts after 15:30 IST. Until then every `/api/desk/*`, `/api/day/*` and `/api/series` GET against 8765 returns 404, which is correct."

- [ ] **Step 5: Confirm no Python restart was attempted**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && git log --oneline -8`
Expected: eight commits from Tasks 1–8, no process started or stopped in this session.

---

## PHASE B — THE SHELL (Tasks 10–12)

**Static files need no restart and no code change.** `ui/desk/index.html` is live at `http://127.0.0.1:8765/desk/` the moment it is written (server.py:994 sets `directory=ROOT/"ui"`; the final `else: super().do_GET()` at server.py:1922-1923 serves it; `SimpleHTTPRequestHandler` resolves a trailing-slash directory to its `index.html`). **The Phase A routes are NOT live until the owner restarts after 15:30 IST**, so every screen must render its hole clause when a fetch 404s — that is not a bug to work around, it is the state the desk is built to show.

### Task 10: the skeleton — `ui/desk/index.html` and `ui/desk/desk.css`

**Goal:** three fixed skeletons, a 22 px rail, two drawers and a pre-paint theme stamp, so a poll changes ink only and nothing ever moves.

**Files:** Create `ui/desk/index.html`, `ui/desk/desk.css`.

**Interfaces:** Produces the DOM ids Tasks 11–15 write into: `#rail`, `#head-word`, `#head-sub`, `#head-rule`, `#head-stamp`, `#s-today`, `#s-campaign`, `#s-record`, `#board`, `#survival`, `#paid`, `#cv-campaign`, `#rail-campaign`, `#cv-record`, `#card`, `#series`, `#money`, `#foot`, `#dr-health`, `#dr-legend`, `#tabs`.

- [ ] **Step 1: Create `ui/desk/index.html`**

```html
<!doctype html>
<html lang="en" data-theme="light">
<head>
<!-- FIRST LINE OF THE HEAD, AND IT MUST STAY FIRST (ruling D8). The static
     handler sends no charset with this file; without this meta the browser
     falls back to its locale default and ₹ σ · − all render as mojibake --
     which is every currency, every sigma and every minus sign on the desk. -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Operator Desk</title>
<script>
// Three lines before first paint: no flash of the wrong theme. localStorage
// WINS over the media query, because her chart is white and the OS is not.
try { var t = localStorage.getItem('deskTheme');
  document.documentElement.dataset.theme = t || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); } catch (e) {}
</script>
<link rel="stylesheet" href="desk.css">
</head>
<body>
<div id="rail" class="rail" role="status" aria-live="off">tape — · chain — · depth — · chart — · record —</div>

<header class="head">
  <div class="head-l">
    <div id="head-word" class="head-word">PATA NAHI</div>
    <div id="head-sub" class="head-sub">waiting for the first poll</div>
  </div>
  <div class="head-r">
    <div id="tabs" class="tabs"><b data-k="1">1 TODAY</b><b data-k="2">2 CAMPAIGN</b><b data-k="3">3 RECORD</b></div>
    <div id="head-stamp" class="mark">—</div>
  </div>
  <div id="head-rule" class="rule lvl-pata"></div>
</header>

<main class="body">
  <section id="s-today" class="screen">
    <div id="board" class="region region-board"></div>
    <div id="survival" class="region region-surv"></div>
    <div id="paid" class="region region-paid"></div>
  </section>

  <section id="s-campaign" class="screen" hidden>
    <div class="map-wrap">
      <canvas id="cv-campaign" class="cv"></canvas>
      <div id="rail-campaign" class="side-rail"></div>
    </div>
  </section>

  <section id="s-record" class="screen" hidden>
    <div class="map-wrap">
      <canvas id="cv-record" class="cv"></canvas>
      <div id="card" class="side-rail"></div>
    </div>
    <div id="series" class="region region-series"></div>
    <div id="money" class="region region-money"></div>
  </section>
</main>

<footer class="foot"><span id="foot">coverage —</span><span class="mark">legend ? · health 5</span></footer>

<aside id="dr-health" class="drawer" hidden><h3>HEALTH</h3><div class="drawer-body"></div></aside>
<aside id="dr-legend" class="drawer" hidden><h3>LEGEND</h3><div class="drawer-body">
  <p><b>PAKKA</b> measured, current, actionable — solid 3 px rule, full width.</p>
  <p><b>SHAK</b> present but degraded — inferred, stale, thin n — half-width hatched rule.</p>
  <p><b>NAHI</b> actively negative — no new risk, source dead, series killed — reversed block.</p>
  <p><b>PATA NAHI</b> a hole; it wins whenever any input is a hole — dashed outline.</p>
  <p><b>~</b> inferred. Plain = measured. Nothing else is tagged.</p>
  <p><b>SHAK beats ~.</b> A value that is both inferred and degraded takes the SHAK
     geometry and KEEPS its <b>~</b>. <b>~</b> alone means inferred but current.</p>
  <p>Hue carries SIDE only: gold = CE, teal = PE. State is geometry, never hue.</p>
  <p>Keys: 1/2/3 screens · 5 health · ? legend · n/b next/previous index ·
     j/k row (its own cursor per screen) · c candidate book · [ ] scrub ∓5m ·
     space replay 60× · g now · w window · m mute · t theme · Esc close.</p>
  <p>Event calendar not checked? Create <code>data/events.json</code> —
     <code>[{"date":"2026-09-30","name":"RBI policy","level":"HALF SIZE"}]</code>.
     The gate prints the hole; the instruction lives here only.</p>
</div></aside>

<script type="module">
import { mount } from './desk.js';
mount();
</script>
</body>
</html>
```

- [ ] **Step 2: Create `ui/desk/desk.css`**

```css
/* ui/desk/desk.css -- ten tokens x two themes, four type sizes, four level
   geometries. LIGHT IS FIRST-CLASS: her chart is white, and a desk that is
   only legible in dark is a desk she reads with a squint. The ink / ground /
   hair values are the chart overlay's own (overlay.js:82-83), so one palette
   serves the chart and the desk.

   STATE IS CARRIED BY GEOMETRY, NEVER HUE. Hue carries SIDE only -- gold CE,
   teal PE -- which is what keeps the four levels legible on white and to a
   colour-blind glance.

   FIXED SKELETON: every region reserves its height at first paint from its
   row cap, so a poll changes ink only. Numbers are tabular, so a change in
   digit count cannot move a row.

   ONE BREAKPOINT, 960 px, and it appears exactly once in this file. There is
   no "content column max 1600 px": it was never referenced by anything and a
   second width rule is a second way for two screens to disagree.

   --lane-pitch IS A CONSTANT SHARED WITH lanes.js (LANE_PITCH = 18). The
   canvas draws a lane at that pitch and the campaign rail pins its row height
   to the same token, so NEITHER SIDE EVER MEASURES THE OTHER (ruling D7). */

:root {
  --ce:#a8791a; --pe:#1f7f8f; --buy:#0f7b6c; --sell:#c0392b; --accent:#b26b00;
  --ink:#0b0e13; --muted:#4a5568; --ground:#ffffff; --panel:#f4f5f7; --hair:#d8dce2;
  --head:30px; --num:17px; --body:13px; --mark:11px;
  --rail-h:22px; --head-h:56px; --foot-h:20px;
  --lane-pitch:18px; --rail-foot-h:46px;
  color-scheme: light;
}
:root[data-theme="dark"] {
  --ce:#e0b04e; --pe:#4fb8c8; --buy:#2fbf8f; --sell:#f0605a; --accent:#d99b2e;
  --ink:#e8edf2; --muted:#8d99a7; --ground:#0b0e13; --panel:#141926; --hair:#242b36;
  color-scheme: dark;
}

* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0; background: var(--ground); color: var(--ink);
  font: var(--body)/1.45 "Segoe UI", system-ui, sans-serif;
  overflow-x: hidden;
}
b, h3 { font-weight: 600; }
.mark { font-size: var(--mark); color: var(--muted); }
.num  { font: var(--num)/1.2 Consolas, ui-monospace, monospace; font-variant-numeric: tabular-nums; }
.hole { color: var(--muted); font-style: italic; }

/* ---- rail: 22 px, on every screen, never a screen of its own ------------ */
.rail {
  height: var(--rail-h); line-height: var(--rail-h); font-size: var(--mark);
  padding: 0 10px; color: var(--muted); background: var(--panel);
  border-bottom: 1px solid var(--hair); white-space: nowrap; overflow: hidden;
}
/* `late` is GEOMETRY, not amber alone: it takes the SHAK hatch, so a degraded
   source reads as degraded on white and to a colour-blind glance. */
.rail .late { color: var(--accent);
  background: repeating-linear-gradient(45deg, var(--hair) 0 3px, transparent 3px 6px);
  padding: 0 4px; }
.rail .dead { background: var(--ink); color: var(--ground); padding: 0 4px; }

/* ---- headline band: 56 px ---------------------------------------------- */
.head {
  height: var(--head-h); display: flex; align-items: center; gap: 16px;
  padding: 0 10px; position: relative; margin: 0 auto;
}
.head-l { flex: 1 1 auto; min-width: 0; }
.head-r { display: flex; align-items: center; gap: 12px; }
.head-word { font-size: var(--head); font-weight: 600; line-height: 1; }
.head-sub  { font-size: var(--body); color: var(--muted); white-space: nowrap;
             overflow: hidden; text-overflow: ellipsis; }
.tabs b { font-size: var(--mark); color: var(--muted); margin-left: 8px; cursor: default; }
.tabs b.on { color: var(--ink); border-bottom: 2px solid var(--accent); }

/* ---- the four levels, as geometry -------------------------------------- */
.rule { position: absolute; left: 10px; right: 10px; bottom: 0; height: 3px; }
.lvl-pakka { background: var(--accent); }
.lvl-shak  { background: repeating-linear-gradient(45deg, var(--accent) 0 3px, transparent 3px 6px);
             right: 50%; }
.lvl-nahi  { background: var(--ink); height: 3px; }
.lvl-pata  { background: none; height: 0; border-top: 1px dashed var(--muted); }
.head-word.lvl-nahi-word { background: var(--ink); color: var(--ground); padding: 0 6px; }
/* "PATA NAHI" DROPS TO NUM SIZE. The dashed rule under it already carries the
   level; the biggest word on the 09:14 screen must not be "don't know". */
.head-word.pata-word { font-size: var(--num); font-weight: 600; line-height: 1.6; }

/* ---- body: 100vh - 98px, three fixed skeletons -------------------------- */
.body { height: calc(100vh - 98px); margin: 0 auto; padding: 0 10px; }
.screen { height: 100%; display: flex; flex-direction: column; gap: 6px; }
.region { border: 1px solid var(--hair); background: var(--panel); padding: 6px 8px;
          overflow: hidden; }
.region-board { flex: 0 0 18%; }
.region-surv  { flex: 0 0 42%; }
.region-paid  { flex: 0 0 40%; }
.region-series{ flex: 0 0 22%; }
/* RECORD has no visit-ledger table -- j/k walks the card -- so the money strip
   takes the height that would have gone to it. */
.region-money { flex: 0 0 20%; }
.region h3 { margin: 0 0 4px; font-size: var(--body); color: var(--muted);
             display: flex; justify-content: space-between; }

/* board: three columns, 34/33/33, one row per index */
.board-cols { display: grid; grid-template-columns: 34% 33% 33%; gap: 8px; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%;
       border: 1px solid var(--muted); }
.dot.live { background: var(--muted); }
.yday { color: var(--muted); font-size: var(--mark); white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; }

/* survival: ONE gap table at FULL REGION WIDTH, a fixed column grid so a digit
   can never move a row. The candidate book is a second ROW-GROUP inside the
   same grid, hidden until `c`; a column that will not fit is DROPPED by the
   renderer and labelled, never clipped. */
.gap-grid { display: grid; grid-template-columns: 110px repeat(var(--gap-cols, 5), 1fr);
            gap: 2px 8px; width: 100%; font-variant-numeric: tabular-nums; }
.gap-grid > span { text-align: right; overflow: hidden; text-overflow: ellipsis;
                   white-space: nowrap; }
.gap-grid > span.lab { text-align: left; color: var(--muted); }
.gap-grid > span.grp { grid-column: 1 / -1; text-align: left; color: var(--muted);
                       border-top: 1px solid var(--hair); margin-top: 3px; padding-top: 3px; }
.pos { color: var(--buy); } .neg { color: var(--sell); }
.shak { background: repeating-linear-gradient(45deg, var(--hair) 0 3px, transparent 3px 6px); }

/* ---- canvas screens: map + fixed right rail ---------------------------- */
.map-wrap { flex: 1 1 auto; display: flex; gap: 8px; min-height: 0; }
.cv { flex: 1 1 auto; min-width: 0; display: block; }
.side-rail { flex: 0 0 300px; border-left: 1px solid var(--hair); padding-left: 8px;
             font-size: var(--mark); overflow: hidden;
             font-variant-numeric: tabular-nums; }
/* FIVE FIXED COLUMNS, EACH WITH ITS OWN ELLIPSIS, NO CELL WRAPS, and the row
   height PINNED to the canvas lane pitch (ruling D7). Row height comes from
   the --lane-pitch token, never from a measured canvas, and the footer below
   is a constant height -- so the canvas and the DOM never read each other. */
.side-rail .row { display: grid; grid-template-columns: 78px 60px 74px 40px 48px;
                  gap: 4px; height: var(--lane-pitch); line-height: var(--lane-pitch);
                  align-items: center; }
.side-rail .row > span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                         min-width: 0; }
.side-rail .row.on { color: var(--ink); }
.rail-foot { height: var(--rail-foot-h); overflow: hidden; border-top: 1px solid var(--hair);
             margin-top: 4px; padding-top: 3px; color: var(--muted); }
.ce { color: var(--ce); } .pe { color: var(--pe); }

/* ---- footer + drawers --------------------------------------------------- */
.foot { height: var(--foot-h); line-height: var(--foot-h); font-size: var(--mark);
        color: var(--muted); padding: 0 10px; display: flex; justify-content: space-between;
        margin: 0 auto; }
.drawer { position: fixed; right: 0; top: var(--rail-h); width: 380px;
          height: calc(100vh - var(--rail-h)); background: var(--panel);
          border-left: 1px solid var(--hair); padding: 10px; overflow-y: auto;
          font-size: var(--body); }
.drawer h3 { margin: 0 0 8px; font-size: var(--body); color: var(--muted); }
.drawer p { margin: 0 0 6px; }

/* ---- THE ONE BREAKPOINT, 960 px: the right rail narrows, NOTHING stacks -- */
@media (max-width: 960px) {
  .side-rail { flex-basis: 220px; }
  .side-rail .row { grid-template-columns: 62px 48px 54px 32px 36px; }
  .drawer { width: 300px; }
}
```

- [ ] **Step 3: Look at it**

Open `http://127.0.0.1:8765/desk/` in a browser (no restart needed — the file is already served).
Expected: the rail, the headline band with a dashed rule under `PATA NAHI`, three empty bordered regions that do not move, and the footer. No console errors except `desk.js` 404 — that is Task 11.

- [ ] **Step 4: Commit**

```bash
git add ui/desk/index.html ui/desk/desk.css
git commit -m "desk ui: the fixed skeleton -- 22 px rail, 56 px headline, three regions by body height, four levels as geometry, light first-class"
```

---

### Task 11: `ui/desk/desk.js` — the pure core, the poller, the keys, and `ui/desk/test.mjs`

**Goal:** the vocabulary functions, one poll loop per cadence, **all 18 keys**, the theme toggle — and a `node --test` that fails if the vocabulary breaks.

**The keyboard table, and every key in it ships in this file:** `1` `2` `3` screens · `5` health drawer · `?` legend drawer · `n` next index · `b` previous index · `j` `k` row cursor (**its own index per screen**) · `c` candidate book row-group · `[` `]` scrub ∓5 m · `space` replay 60× · `g` now · `w` window · `m` mute · `t` theme · `Esc` close. Eighteen keys, eighteen `case` arms.

**Files:** Create `ui/desk/desk.js`, `ui/desk/test.mjs`.

**Interfaces:**
- Produces (imported by `test.mjs` and by `lanes.js` in Phase C):
  `level(...vals) -> "PATA NAHI"|"PAKKA"|"SHAK"|"NAHI"`, `geom(level) -> string` (a CSS class),
  `state4Class(dOi, dPrem) -> "writing"|"loading"|"covering"|"liquidation"`,
  `cur(n?) -> number` (the CURRENT SCREEN's `j`/`k` index — one per screen, never shared),
  `fmt.num`, `fmt.pct`, `fmt.rs`, `fmt.age`, `fmt.hhmm`, `hole(why)`, `mount()`.
- Produces on `window`: nothing. Everything is a module export; `mount()` is the only side effect and is called once from `index.html`.

**Cadences (spec §B):** `/api/desk/health` 2 s · `/api/desk/today` + `/api/frame` + `/api/paperdesk` 3 s · `/api/day/oi` + `/api/day/record` + `/api/day/visits` + `/api/series` + `/api/warmap` 10 s and on every scrub key.

- [ ] **Step 1: Write the failing test** — create `ui/desk/test.mjs`:

```js
// ui/desk/test.mjs -- node --test over the pure functions. Canvas pixels are
// an acceptance step (spec R7), not a unit test; these are the four things
// that would silently corrupt every screen if they broke.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { level, geom, state4Class, fmt, hole } from './desk.js';

test('a hole wins whenever any input is a hole', () => {
  assert.equal(level(1, null), 'PATA NAHI');
  assert.equal(level(undefined), 'PATA NAHI');
  assert.equal(level(1, 2, 3), 'PAKKA');
  assert.equal(level('SHAK', 1), 'SHAK');
  assert.equal(level('NAHI', 1), 'NAHI');
  assert.equal(level('NAHI', null), 'PATA NAHI');   // the hole still wins
});

test('geom returns the half-width hatched rule for SHAK', () => {
  assert.equal(geom('PAKKA'), 'lvl-pakka');
  assert.equal(geom('SHAK'), 'lvl-shak');
  assert.equal(geom('NAHI'), 'lvl-nahi');
  assert.equal(geom('PATA NAHI'), 'lvl-pata');
  assert.equal(geom('anything else'), 'lvl-pata');
  // SHAK BEATS `~`: geometry comes from the LEVEL and the `~` rides on the
  // number, so a value that is both inferred and degraded hatches AND keeps
  // its tag. `~` alone never changes geometry.
  assert.equal(geom('SHAK'), 'lvl-shak');
  assert.equal(geom('PAKKA'), 'lvl-pakka');
});

test('the four-state table is OI x premium, and a flat premium is not a bid', () => {
  assert.equal(state4Class(+1, -1), 'writing');
  assert.equal(state4Class(+1, +1), 'loading');
  assert.equal(state4Class(-1, +1), 'covering');
  assert.equal(state4Class(-1, -1), 'liquidation');
  assert.equal(state4Class(+1, 0), 'writing');
});

test('a null never formats as a zero', () => {
  assert.equal(fmt.num(null), '—');
  assert.equal(fmt.rs(null), '—');
  assert.equal(fmt.pct(null), '—');
  assert.equal(fmt.age(null), '—');
  assert.equal(fmt.num(8100000), '8.1M');
  assert.equal(fmt.rs(-241000), '−₹2,41,000');
  assert.equal(fmt.pct(-1.7), '−1.7 %');
  assert.equal(fmt.age(4.2), '4s');
  assert.equal(fmt.hhmm('11:19:04'), '11:19');
});

test('a hole is a sentence, never a red error and never a blank', () => {
  assert.equal(hole('no chart posting'), 'PATA NAHI — no chart posting');
  assert.equal(hole(null), 'PATA NAHI');
  assert.ok(hole('x'.repeat(80)).length <= 60);
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: FAIL — `Cannot find module .../ui/desk/desk.js`

- [ ] **Step 3: Create `ui/desk/desk.js`**

```js
// ui/desk/desk.js -- the Operator Desk's brain-free face.
//
// IT COMPUTES NOTHING. Every number on every screen arrives from a route that
// already decided it; this file formats, places, and states absences. The one
// exception is `level()`, which re-asserts the hole-wins rule client-side so a
// renderer can never see a null and paint it as a fact (spec §C: enforced
// twice, gate.py server-side and here).
//
// No framework, no bundler, no CDN. ES modules, same-origin fetch, polling --
// there is no SSE anywhere in this server, so a UI must poll.
//
// FIXED SKELETON: a poll changes textContent and class, never layout.

export const SCREENS = ['today', 'campaign', 'record'];

// ---- the vocabulary -------------------------------------------------------

/** The four levels. A hole WINS whenever any input is null or undefined --
 *  the whole point, and anti-pattern 1 (a gate that initialises green). */
export function level(...vals) {
  if (vals.some((v) => v === null || v === undefined)) return 'PATA NAHI';
  if (vals.includes('NAHI')) return 'NAHI';
  if (vals.includes('SHAK')) return 'SHAK';
  if (vals.includes('PATA NAHI')) return 'PATA NAHI';
  return 'PAKKA';
}

/** State as GEOMETRY, never hue: survives both themes and a colour-blind glance. */
export function geom(lvl) {
  return { 'PAKKA': 'lvl-pakka', 'SHAK': 'lvl-shak', 'NAHI': 'lvl-nahi' }[lvl] || 'lvl-pata';
}

/** OI x premium. The same table day_oi.state4() uses server-side; this copy
 *  exists only so the canvas can pick a texture without a round trip. */
export function state4Class(dOi, dPrem) {
  if ((dOi || 0) >= 0) return (dPrem || 0) > 0 ? 'loading' : 'writing';
  return (dPrem || 0) > 0 ? 'covering' : 'liquidation';
}

const MINUS = '\u2212';   // a real minus sign: a hyphen at 17 px reads as a dash

export const fmt = {
  num(v) {
    if (v === null || v === undefined || Number.isNaN(v)) return '—';
    const a = Math.abs(v);
    const s = a >= 1e7 ? (v / 1e7).toFixed(1) + 'cr'
      : a >= 1e6 ? (v / 1e6).toFixed(1) + 'M'
      : a >= 1e3 ? (v / 1e3).toFixed(1) + 'k' : String(Math.round(v * 100) / 100);
    return s.replace('-', MINUS);
  },
  /** Indian grouping: 2,41,000 not 241,000. */
  rs(v) {
    if (v === null || v === undefined || Number.isNaN(v)) return '—';
    const n = Math.round(Math.abs(v));
    const s = String(n);
    const head = s.length > 3 ? s.slice(0, -3) : '';
    const tail = s.slice(-3);
    const grouped = (head ? head.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' : '') + tail;
    return (v < 0 ? MINUS : '') + '₹' + grouped;
  },
  pct(v, d = 1) {
    if (v === null || v === undefined || Number.isNaN(v)) return '—';
    return (v < 0 ? MINUS : '') + Math.abs(v).toFixed(d) + ' %';
  },
  age(s) {
    if (s === null || s === undefined || Number.isNaN(s)) return '—';
    return s < 90 ? Math.round(s) + 's' : Math.round(s / 60) + 'm';
  },
  hhmm(t) { return t ? String(t).slice(0, 5) : '—'; },
};

/** Absence grammar: dim italic, one clause, in the place the value would be.
 *  Never a red error, never a zero, never a blank, never a row of its own. */
export function hole(why) {
  if (!why) return 'PATA NAHI';
  const w = String(why);
  return 'PATA NAHI — ' + (w.length <= 48 ? w : w.slice(0, 47) + '…');
}

// ---- state ----------------------------------------------------------------

export const S = {
  screen: 'today', idx: 'NIFTY', indices: ['NIFTY', 'BANKNIFTY', 'SENSEX'],
  win: 15, scrub: null, playing: false, muted: false,
  // ONE CURSOR PER SCREEN, never one shared. CAMPAIGN's j/k walks lanes and
  // RECORD's walks visits; a shared index makes `k` on one screen silently
  // move the other, and the two lists are not even the same length.
  cursors: { today: 0, campaign: 0, record: 0 },
  candidate: false,        // the `c` row-group, OFF by default (ruling D5)
  data: { health: null, today: null, frame: null, paperdesk: null,
          oi: null, record: null, visits: null, series: null, warmap: null },
  why: {},
};

/** The cursor of the screen being painted. */
export function cur(n) {
  if (n !== undefined) S.cursors[S.screen] = Math.max(0, n);
  return S.cursors[S.screen] || 0;
}

const WINS = [5, 15, 'day'];

async function get(path, key) {
  try {
    const r = await fetch(path, { cache: 'no-store' });
    if (!r.ok) { S.why[key] = 'route not on the running server (' + r.status + ')'; S.data[key] = null; return; }
    S.data[key] = await r.json();
    S.why[key] = null;
  } catch (e) {
    S.data[key] = null;
    S.why[key] = 'fetch failed: ' + (e && e.message ? e.message : 'unknown');
  }
}

const asOf = () => (S.scrub ? '&as_of=' + S.scrub : '');

async function pollFast() { await get('/api/desk/health', 'health'); paintRail(); }

async function pollMid() {
  await Promise.all([
    get('/api/desk/today?idx=' + S.idx, 'today'),
    get('/api/frame?idx=' + S.idx, 'frame'),
    get('/api/paperdesk', 'paperdesk'),
  ]);
  paint();
}

async function pollSlow() {
  const day = new Date().toISOString().slice(0, 10);
  await Promise.all([
    get('/api/day/oi?idx=' + S.idx + '&win=' + S.win + asOf(), 'oi'),
    get('/api/day/record?idx=' + S.idx + '&day=' + day + asOf(), 'record'),
    get('/api/day/visits?idx=' + S.idx + '&day=' + day + asOf(), 'visits'),
    get('/api/series', 'series'),
    get('/api/warmap?idx=' + S.idx, 'warmap'),
  ]);
  paint();
}

// ---- keys -----------------------------------------------------------------

function setScreen(name) {
  S.screen = name;
  for (const n of SCREENS) document.getElementById('s-' + n).hidden = (n !== name);
  for (const b of document.querySelectorAll('#tabs b')) {
    b.classList.toggle('on', SCREENS[+b.dataset.k - 1] === name);
  }
  paint();
}

function drawer(id) {
  const d = document.getElementById(id);
  const other = document.getElementById(id === 'dr-health' ? 'dr-legend' : 'dr-health');
  other.hidden = true;
  d.hidden = !d.hidden;
  if (!d.hidden && id === 'dr-health') paintHealthDrawer();
}

function theme() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('deskTheme', next); } catch (e) {}
  paint();
}

function scrub(deltaMin) {
  const base = S.scrub || nowHHMM();
  const [h, m] = base.split(':').map(Number);
  let t = h * 60 + m + deltaMin;
  t = Math.max(9 * 60 + 15, Math.min(15 * 60 + 30, t));
  S.scrub = String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0');
  pollSlow();                       // a scrub key re-fetches OUTSIDE the poll
  pollMid();
}

function nowHHMM() {
  const d = new Date();
  return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

function onKey(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key;
  const idxAt = S.indices.indexOf(S.idx);
  switch (k) {
    case '1': setScreen('today'); break;
    case '2': setScreen('campaign'); break;
    case '3': setScreen('record'); break;
    case '5': drawer('dr-health'); break;
    case '?': drawer('dr-legend'); break;
    case 'n': S.idx = S.indices[(idxAt + 1) % S.indices.length]; pollMid(); pollSlow(); break;
    case 'b': S.idx = S.indices[(idxAt + S.indices.length - 1) % S.indices.length]; pollMid(); pollSlow(); break;
    case 'j': cur(cur() + 1); paint(); break;
    case 'k': cur(cur() - 1); paint(); break;
    case 'c': S.candidate = !S.candidate; paint(); break;
    case '[': scrub(-5); break;
    case ']': scrub(+5); break;
    case ' ': e.preventDefault(); S.playing = !S.playing; paint(); break;
    case 'g': S.scrub = null; S.playing = false; pollSlow(); pollMid(); break;
    case 'w': S.win = WINS[(WINS.indexOf(S.win) + 1) % WINS.length]; pollSlow(); break;
    case 'm': S.muted = !S.muted; paintRail(); break;
    case 't': theme(); break;
    case 'Escape': document.getElementById('dr-health').hidden = true;
                   document.getElementById('dr-legend').hidden = true; break;
    default: return;
  }
}

// ---- the sound: one tone, ALL SIX SOURCES, once per transition to dead -----
//
// RULING D3. The earlier rule toned for three sources only and routed the
// alarm for a blind chart relay back to the panel that lives in the tab that
// went blind -- which is how 09:51 passed unnoticed. The desk tones for every
// source it watches, including each `chart <IDX>` row. A tone duplicated with
// the extension's panel is a far smaller sin than a silent blind spot, and
// `m` mutes.

let audio = null;
const lastLevel = new Map();

function tone() {
  if (S.muted) return;
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    const o = audio.createOscillator(), g = audio.createGain();
    o.frequency.value = 440; o.connect(g); g.connect(audio.destination);
    o.start(); o.stop(audio.currentTime + 0.4);
  } catch (e) { /* no audio device is not an error worth a screen */ }
}

// ---- the rail -------------------------------------------------------------

function paintRail() {
  const el = document.getElementById('rail');
  const h = S.data.health;
  if (!h || !h.sources) { el.textContent = hole(S.why.health || 'health route not answering'); return; }
  const parts = [];
  for (const s of h.sources) {
    const cls = s.level === 'dead' ? 'dead' : s.level === 'late' ? 'late' : '';
    const name = s.source.replace('tape feed', 'tape').replace('chain poller', 'chain')
      .replace('depth relay', 'depth').replace('record writer', 'record')
      .replace('senses loop', 'senses');
    // EVERY CELL PRINTS AN AGE, NEVER A CLOCK TIME, and a source that never
    // started prints `—` rather than `0s` -- "was never alive" is not an age.
    const txt = (s.level === 'never started' || s.age_s === null || s.age_s === undefined)
      ? '—' : fmt.age(s.age_s);
    parts.push('<span class="' + cls + '">' + name + ' ' + txt + '</span>');
    // ALL SIX SOURCES tone, `chart <IDX>` rows included (ruling D3).
    if (lastLevel.get(s.source) !== 'dead' && s.level === 'dead') tone();
    lastLevel.set(s.source, s.level);
  }
  if (S.muted) parts.push('<span>muted</span>');
  el.innerHTML = parts.join(' · ');
  const cov = h.coverage || {};
  document.getElementById('foot').textContent = cov.server_up
    ? 'started ' + cov.server_up + ' · ' + (cov.late_min || 0) + ' min late · '
      + (cov.reconstructed || []).length + ' rebuilt · ' + (cov.not_reconstructable || []).length + ' not'
    : hole('coverage not answered');
}

function paintHealthDrawer() {
  const b = document.querySelector('#dr-health .drawer-body');
  const h = S.data.health;
  if (!h || !h.sources) { b.innerHTML = '<p class="hole">' + hole(S.why.health) + '</p>'; return; }
  const rows = h.sources.map((s) =>
    '<p><b>' + s.source + '</b> — ' + s.level + ' · last seen ' + fmt.age(s.age_s)
    + (s.why ? ' · <span class="hole">' + s.why + '</span>' : '')
    + (s.rows_today !== undefined ? ' · ' + s.rows_today + ' rows · ' + s.file_mb + ' MB' : '')
    + '</p>');
  const cov = h.coverage || {};
  rows.push('<h3>REBUILT</h3>' + (cov.reconstructed || []).map((x) => '<p>' + x + '</p>').join(''));
  rows.push('<h3>NOT REBUILDABLE</h3>' + (cov.not_reconstructable || []).map((x) => '<p>' + x + '</p>').join(''));
  b.innerHTML = rows.join('');
}

// ---- paint ----------------------------------------------------------------

export const renderers = { today: () => {}, campaign: () => {}, record: () => {} };

export function paint() {
  const stamp = document.getElementById('head-stamp');
  stamp.textContent = S.scrub ? 'as of ' + S.scrub + ' (scrubbed)' : nowHHMM();
  (renderers[S.screen] || (() => {}))();
}

export function mount() {
  document.addEventListener('keydown', onKey);
  setScreen('today');
  pollFast(); pollMid(); pollSlow();
  setInterval(pollFast, 2000);
  setInterval(pollMid, 3000);
  setInterval(pollSlow, 10000);
}
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: `# pass 5` and `# fail 0`.

- [ ] **Step 5: Look at it**

Open `http://127.0.0.1:8765/desk/`, press `2`, `3`, `1`, `5`, `?`, `Esc`, `t`, `n`, `b`, `j`, `k`, `c`, `w`, `m`, `[`, `]`, `g`, and `space`.
Expected: every key responds with no mouse; the rail reads `PATA NAHI — route not on the running server (404)` because the Phase A routes are not live yet; `t` toggles light↔dark and survives a reload; `j` on CAMPAIGN does not move RECORD's cursor; the layout does not move.

- [ ] **Step 6: Commit**

```bash
git add ui/desk/desk.js ui/desk/test.mjs
git commit -m "desk ui: the vocabulary, three poll cadences, all 18 keys, one cursor per screen, the 440 Hz tone on all six sources"
```

---

### Task 12: TODAY — the 09:14 screen

**Goal:** board / survival / paid, each answering its question, the question in BODY and the number in NUM behind it.

**Files:** Modify `ui/desk/desk.js` (replace the `renderers` stub).

**Interfaces:** Consumes `/api/desk/today` (Task 7), `/api/frame` and `/api/paperdesk`.

- [ ] **Step 1: Replace the `renderers` stub** — in `ui/desk/desk.js`, find:

```js
export const renderers = { today: () => {}, campaign: () => {}, record: () => {} };
```

and replace with:

```js
// ---- screen 1: TODAY ------------------------------------------------------

function headline(word, sub, lvl) {
  const w = document.getElementById('head-word');
  w.textContent = word;
  // `PATA NAHI` DROPS TO NUM SIZE: the dashed rule under the headline already
  // carries the level, and the biggest word on the 09:14 screen must not be
  // "don't know". A NAHI verdict still takes the reversed block.
  w.className = 'head-word'
    + (lvl === 'NAHI' ? ' lvl-nahi-word' : '')
    + (String(word).indexOf('PATA NAHI') >= 0 ? ' pata-word' : '');
  document.getElementById('head-sub').textContent = sub || '';
  document.getElementById('head-rule').className = 'rule ' + geom(lvl);
}

function renderToday() {
  const d = S.data.today;
  if (!d || !d.ok) {
    headline('PATA NAHI', hole(S.why.today || 'today route not answering'), 'PATA NAHI');
    document.getElementById('board').innerHTML = '<span class="hole">' + hole(S.why.today) + '</span>';
    document.getElementById('survival').innerHTML = '<span class="hole">' + hole(S.why.today) + '</span>';
    document.getElementById('paid').innerHTML = '<span class="hole">' + hole(S.why.today) + '</span>';
    return;
  }
  const g = d.gate || {};
  const lvl = g.level === 'PATA NAHI' ? 'PATA NAHI'
    : g.level === 'NO NEW RISK' ? 'NAHI' : g.level === 'HALF SIZE' ? 'SHAK' : 'PAKKA';
  headline('GATE  ' + (g.level || 'PATA NAHI'),
    (g.holes && g.holes.length ? g.holes.join(' · ') : (g.reason || '')), lvl);

  // BOARD -- can I sell today, on which index, and what happened YESTERDAY
  const cols = (d.board || []).map((b) => {
    const z = b.z === null || b.z === undefined
      ? '<span class="hole">' + hole(b.z_why) + '</span>'
      : 'z <span class="num">' + (b.z < 0 ? '\u2212' : '') + Math.abs(b.z).toFixed(2) + '</span>';
    const carry = b.carry ? 'carry ' + b.carry + ' ~'
      : '<span class="hole">' + hole(b.carry_why) + '</span>';
    return '<div><b>' + b.idx + '</b> ' + z + '<br>' + carry
      + ' <span class="dot ' + (b.health === 'live' ? 'live' : '') + '"></span>'
      + '<br>' + yesterdayLine(b) + '</div>';
  }).join('');
  document.getElementById('board').innerHTML =
    '<h3><span>can I sell today, on which index</span><span class="mark">' + fmt.hhmm(d.ts) + '</span></h3>'
    + '<div class="board-cols">' + cols + '</div>';

  // SURVIVAL -- ONE gap table at FULL REGION WIDTH. The title ALWAYS names the
  // book, the table is the PAPER book, and the candidate is a second ROW-GROUP
  // behind `c`, off by default (ruling D5).
  const s = d.survival || {};
  const who = (s.whose || []).join(' · ') || 'no book named';
  // A COLUMN THAT DOES NOT FIT IS DROPPED EXPLICITLY AND LABELLED, never
  // clipped: at the one breakpoint the +-2 % pair goes and says that it went.
  const narrow = window.innerWidth <= 960;
  const keys = narrow ? ['-1', '0', '+1'] : ['-2', '-1', '0', '+1', '+2'];
  const heads = { '-2': '−2 %', '-1': '−1 %', '0': 'now', '+1': '+1 %', '+2': '+2 %' };
  const cells = (blk, pick, cls) => keys.map((k) => {
    const g2 = (blk.gap || {})[k];
    if (!g2) return '<span class="hole">—</span>';
    const v = g2[pick];
    const c = cls && v < 0 ? ' neg' : cls && v > 0 ? ' pos' : '';
    return '<span class="num' + c + '">' + fmt.rs(v) + ' ~</span>';
  }).join('');
  const group = (blk, label) =>
    (label ? '<span class="grp">' + label + '</span>' : '')
    + '<span class="lab">P&amp;L</span>' + cells(blk, 'pnl', true)
    + '<span class="lab">margin</span>' + cells(blk, 'margin', false)
    + '<span class="lab">free</span>' + cells(blk, 'free', true);
  const tail = (blk) =>
    '<div>square-off distance ' + (blk.sq_off
        ? '~ ' + fmt.pct(blk.sq_off.pct) + ' (' + fmt.rs(blk.sq_off.px).replace('₹', '') + ')'
        : '<span class="hole">' + hole(blk.sq_off_why) + '</span>')
    + ' · days of income at risk ' + (blk.days_of_income !== null && blk.days_of_income !== undefined
        ? '<span class="num">' + blk.days_of_income + '</span> ~'
        : '<span class="hole">' + hole(blk.days_of_income_why) + '</span>') + '</div>';
  const cnd = S.candidate ? d.candidate : null;
  document.getElementById('survival').innerHTML =
    '<h3><span>will I survive being wrong — ' + who + '</span><span class="mark">' + s.basis + '</span></h3>'
    + (s.gap_why
      ? '<span class="hole">' + hole(s.gap_why) + '</span>'
      : ('<div class="gap-grid" style="--gap-cols:' + keys.length + '">'
        + '<span class="lab"></span>' + keys.map((k) => '<span>' + heads[k] + '</span>').join('')
        + group(s, null)
        + (cnd ? group(cnd, (cnd.whose || []).join(' · ') || 'candidate') : '')
        + '</div>'))
    + (narrow ? '<div class="mark">±2 % hidden — narrow</div>' : '')
    + tail(s)
    + (cnd ? tail(cnd) : '')
    + (d.candidate && !S.candidate
        ? '<div class="mark">candidate book hidden (c)</div>' : '');

  // AM I PAID -- is anyone paying me
  const p = d.paid || {};
  const one = (v, why, f) => (v === null || v === undefined)
    ? '<span class="hole">' + hole(why) + '</span>'
    : '<span class="num">' + (f ? f(v) : v) + '</span>';
  const strad = p.straddle
    ? p.straddle.open + ' → ' + p.straddle.now + ' (' + (p.straddle.d >= 0 ? '+' : '\u2212')
      + Math.abs(p.straddle.d) + ')' + (p.vega_attack ? '  VEGA ATTACK ~' : '')
    : '<span class="hole">' + hole(p.straddle_why) + '</span>';
  const mine = (p.strikes || []).length
    ? (p.strikes || []).map((k) => k.k + ' ' + k.side
        + (k.sigma === null || k.sigma === undefined ? ' —' : ' ' + k.sigma + 'σ')
        + ' (' + k.whose + ')').join(' · ')
    : '<span class="hole">' + hole('no open legs') + '</span>';
  document.getElementById('paid').innerHTML =
    '<h3><span>is anyone paying me</span><span class="mark">as of ' + fmt.hhmm(d.ts) + '</span></h3>'
    + '<div>ATM IV ' + one(p.atm_iv, p.atm_iv_why)
    + '   RV(5d) ' + one(p.rv, p.rv_why, (v) => (v * 100).toFixed(1))
    + '   ratio ' + one(p.ivrv, p.ivrv_why, (v) => v.toFixed(2))
    // THE IV/RV VERDICT IS A MARK CLAUSE, never a reversed NAHI block: a
    // second verdict louder than the gate, on the gate's own screen, is two
    // verdicts. The gate leads; this qualifies it.
    + (p.ivrv !== null && p.ivrv !== undefined && p.ivrv < 1.0
        ? ' <span class="mark">ratio ' + p.ivrv.toFixed(2) + ' · below 1.0, no business</span>'
        : '') + '</div>'
    + '<div>straddle ' + strad
    + '  ·  σ of straddle ' + one(p.sigma_pct, 'no straddle to measure', (v) => v + ' %') + '</div>'
    // THE LEG σ-DISTANCE, ONCE. It is printed here and in no other region;
    // the events hole is printed in the headline and in no other region.
    + '<div>my strikes: ' + mine + '</div>';
}

/** YESTERDAY, one line (ruling D9): prior close, prior range, where the walls
 *  stood at that close, and the overnight change on the two biggest strikes.
 *  Close and range are the record's OWN prices, so they carry `~`. */
function yesterdayLine(b) {
  const y = b.yesterday;
  if (!y) return '<div class="yday hole">' + hole(b.yesterday_why) + '</div>';
  const close = y.close == null ? hole(y.close_why) : fmt.num(y.close) + ' ~';
  const range = y.range == null ? '—' : fmt.num(y.lo) + '–' + fmt.num(y.hi) + ' ~';
  const walls = (y.ladder || []).length
    ? y.ladder.slice(0, 3).map((w) => w.kind + ' ' + fmt.num(w.p)).join(' ')
    : hole(y.ladder_why);
  const big = (y.big || []).length
    ? y.big.map((g) => g.side + ' ' + fmt.num(g.k) + ' '
        + (g.overnight == null ? hole(g.overnight_why)
           : (g.overnight >= 0 ? '+' : '−') + fmt.num(Math.abs(g.overnight)))).join(' · ')
    : hole(y.big_why);
  return '<div class="yday">yday ' + close + ' · ' + range + ' · ' + walls
    + ' · overnight ' + big + '</div>';
}

export const renderers = { today: renderToday, campaign: () => {}, record: () => {} };
```

- [ ] **Step 2: Move the export** — `renderers` is referenced by `paint()`, which is declared after it, so no reordering is needed. Confirm the file still parses:

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --check ui/desk/desk.js 2>&1 || node --input-type=module -e "import('./ui/desk/desk.js').then(()=>console.log('parsed')).catch(e=>{console.error(e.message);process.exit(1)})"`
Expected: `parsed` (or no output from `node --check`).

- [ ] **Step 3: Run the JS test again**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: `# pass 5`, `# fail 0` — the pure exports are unchanged.

- [ ] **Step 4: Look at it, at both widths and both themes**

Open `http://127.0.0.1:8765/desk/` at 1920 and at 960 wide, press `t` in each, then `c` in each.
Expected (against the spec §D mockup): three regions at 18 / 42 / 40 % of the body; the gap table fills the region's full width; at 960 it shows three columns and prints `±2 % hidden — narrow` rather than clipping two; `c` adds the candidate row-group under the paper one and `c` again removes it; every value that the not-yet-restarted server cannot supply reads `PATA NAHI — <clause>` in dim italic **in the place the value would be**, never as a zero and never as a red error; the headline's `PATA NAHI` is at NUM size, not headline size; no horizontal scrollbar; nothing moves across twenty polls.

- [ ] **Step 5: Commit**

```bash
git add ui/desk/desk.js
git commit -m "desk ui: TODAY -- board with the yesterday line, one full-width gap table for the paper book with the candidate behind c, am I paid; every hole a sentence in place"
```

- [ ] **Step 6: Phase B gate (spec §K)** — tick each of these four by eye before starting Task 13:
  - [ ] all 18 keys work with no mouse (`1 2 3 5 ? n b j k c [ ] space g w m t Esc`)
  - [ ] nothing moves across 20 polls (watch one region for a minute)
  - [ ] light and dark are both legible at 960 px wide
  - [ ] the events hole appears in the headline only, and each leg's σ-distance is printed once

---

## PHASE C — THE CAMPAIGN CANVAS (Tasks 13–14)

### Task 13: `ui/desk/lanes.js` — the shared axis, the textures, the campaign map, the record lanes

**Goal:** one canvas module that draws both time-axis screens, so CAMPAIGN and RECORD can never disagree about where 11:00 is.

**Files:** Create `ui/desk/lanes.js`. Modify `ui/desk/test.mjs` (append three tests).

**Interfaces:**
- Consumes: `state4Class` from `./desk.js`.
- Produces: `axis(ctx, box, t0, t1) -> {x, xInv, y0, y1}` · `campaign(ctx, box, day, opts)` · `record(ctx, box, rows, visits, ring, opts)` · `scrub(ctx, box, t, t0, t1)` · `tex(ctx, x0, x1, y, h, state4, opts)` · `xOfHHMM(hhmm, box, t0, t1)`.
- `box` is `{x, y, w, h}` in CSS pixels. Every function is pure of DOM except the `ctx` calls, so `test.mjs` drives them with a recording stub.

**THE AXIS FOLLOWS THE DAY (ruling D4).** `09:15 → clamp(now + 60 min, 11:30, 15:30)`, recomputed on **every poll and every scrub**, and locked to `15:30` from 14:30 onward. The old rule — a fixed 09:15→15:30 axis, defended by "an empty right third at 11:00 is information" — spent 55 % of the map on a session that has not happened; that sentence is deleted, not softened. The hour that has not happened yet is still shown (the `+ 60 min` head-room), so a wall being built right now is not pinned to the right edge. **CAMPAIGN and RECORD share the axis**, so they still cannot disagree about where 11:00 is.

**Why these numbers:** at 1920 the map is 1100 px; at 11:05 the axis spans 09:15→12:05 = 170 minutes = **6.5 px/min**, and at the close it spans 375 minutes = **2.9 px/min** (**1.9 px/min** at 960). Two times of day are therefore not directly comparable by eye, which is exactly why **the rail footer prints px-per-minute**. A 5 m window at the close is 75 segments at 9 px on the 700 px map, and **9 px cannot carry four textures** — so at `win === 5` the textures collapse to two, solid build and outline retreat, and the four-state word moves to the rail line (spec R4, §M).

**`LANE_PITCH` is a constant, not a measurement (ruling D7).** The canvas draws a lane at `LANE_PITCH` px and `desk.css`'s `--lane-pitch` pins the rail row to the same number. Neither side ever reads the other's measured height.

- [ ] **Step 1: Append the failing tests to `ui/desk/test.mjs`**

```js
import { axis, tex, xOfHHMM, TEXTURES, t1For } from './lanes.js';

/** A recording 2D context: every call becomes a string, so a canvas test can
 *  assert on WHAT was drawn without a DOM. */
function stub() {
  const calls = [];
  const rec = (n) => (...a) => calls.push(n + '(' + a.join(',') + ')');
  const c = new Proxy({ calls, canvas: { width: 1100, height: 400 } }, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === 'measureText') return () => ({ width: 10 });
      if (typeof k === 'string' && k[0] === k[0].toLowerCase()) return rec(k);
      return undefined;
    },
    set(t, k, v) { calls.push('set ' + String(k) + '=' + v); return true; },
  });
  return c;
}

test('the axis follows the day: 09:15 to clamp(now + 60, 11:30, 15:30)', () => {
  // RULING D4. The old fixed 09:15->15:30 axis spent 55 % of the map on a
  // session that had not happened. One hour of head-room stays, so a wall
  // being built right now is never pinned to the right edge.
  assert.equal(t1For('09:20'), '11:30');      // before 10:30 the floor holds
  assert.equal(t1For('10:30'), '11:30');
  assert.equal(t1For('11:05'), '12:05');
  assert.equal(t1For('14:30'), '15:30');      // locked from 14:30 onward
  assert.equal(t1For('14:45'), '15:30');
  assert.equal(t1For('15:29'), '15:30');
  const box = { x: 0, y: 0, w: 1100, h: 300 };
  const a = axis(stub(), box, '09:15', t1For('11:05'));
  assert.equal(Math.round(a.x('09:15')), 0);
  assert.equal(Math.round(a.x('12:05')), 1100);
  // 11:05 is 110 of the 170 minutes on screen
  assert.equal(Math.round(a.x('11:05')), Math.round(1100 * 110 / 170));
  assert.equal(Math.round(xOfHHMM('11:05', box, '09:15', '12:05')), Math.round(a.x('11:05')));
});

test('at the 5 m window the four textures collapse to two', () => {
  assert.deepEqual(TEXTURES(15), ['writing', 'loading', 'covering', 'liquidation']);
  assert.deepEqual(TEXTURES(5), ['build', 'retreat']);
  assert.deepEqual(TEXTURES('day'), ['writing', 'loading', 'covering', 'liquidation']);
});

test('a backfilled segment is 55 percent AND outline-only, and never merged', () => {
  const c = stub();
  tex(c, 0, 20, 10, 8, 'writing', { bf: true, ce: '#a8791a', pe: '#1f7f8f', side: 'CE' });
  assert.ok(c.calls.some((s) => s.startsWith('set globalAlpha=0.55')));
  // 55 % of a mid-tone on a DARK ground still reads as full strength, so the
  // fill is dropped as well: a reconstructed segment is an outline.
  assert.ok(c.calls.some((s) => s.startsWith('strokeRect(')));
  assert.ok(!c.calls.some((s) => s.startsWith('fillRect(')));
  const c2 = stub();
  tex(c2, 0, 20, 10, 8, 'writing', { bf: false, ce: '#a8791a', pe: '#1f7f8f', side: 'CE' });
  assert.ok(!c2.calls.some((s) => s.startsWith('set globalAlpha=0.55')));
  assert.ok(c2.calls.some((s) => s.startsWith('fillRect(')));
});
```

- [ ] **Step 2: Run to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: FAIL — `Cannot find module .../ui/desk/lanes.js`

- [ ] **Step 3: Create `ui/desk/lanes.js`**

```js
// ui/desk/lanes.js -- the two time-axis screens, on one canvas module.
//
// ONE AXIS, SHARED, AND IT FOLLOWS THE DAY. CAMPAIGN and RECORD are the same
// x axis, the same pixels per minute, one scrubber -- so they can never
// disagree about where 11:00 is. The right edge is
// `clamp(now + 60 min, 11:30, 15:30)`, recomputed on every poll and every
// scrub and LOCKED at 15:30 from 14:30 onward. The old axis was fixed
// 09:15 -> 15:30 and defended by "an empty right third at 11:00 is
// information"; at 11:00 that third is in fact 55 % of the map, spent on a
// session that has not happened. One hour of head-room stays, so a wall being
// built right now is never pinned to the right edge.
//
// TWO TIMES OF DAY ARE THEREFORE NOT COMPARABLE BY EYE -- 6.5 px/min at 11:05
// against 2.9 px/min at the close -- which is why the rail footer prints
// px-per-minute. A 5 m window at the close is 75 segments at 9 px, and 9 px
// CANNOT CARRY FOUR TEXTURES -- exactly how the last ladder became illegible.
// So at win === 5 the textures collapse to two (solid build, outline retreat)
// and the four-state word moves to the rail line.
//
// LANE_PITCH IS A CONSTANT, NOT A MEASUREMENT. desk.css pins its rail row
// height to the same number (--lane-pitch), so the canvas and the DOM never
// read each other's measured heights.
//
// HUE CARRIES SIDE ONLY. Gold CE, teal PE. Build vs retreat, backfill vs
// observed, peak vs now are all GEOMETRY -- fill against outline, 55 % alpha,
// a notch -- so they survive both themes and a colour-blind glance.
//
// ONE BASE. Every bar's thickness is OI ADDED SINCE OPEN. Totals live only in
// the right rail and are labelled there, so the toolb units bug cannot return.

import { state4Class } from './desk.js';

export const T0 = '09:15';
export const T1 = '15:30';          // the hard right edge of the session
export const T1_MIN = '11:30';      // ...and the earliest the axis may end
export const HEADROOM_MIN = 60;
export const LANE_CAP = 14;
export const LANE_PITCH = 18;       // MUST equal desk.css --lane-pitch
export const FUT_H = 28;

export const TEXTURES = (win) =>
  (win === 5 ? ['build', 'retreat'] : ['writing', 'loading', 'covering', 'liquidation']);

const mins = (hhmm) => {
  const p = String(hhmm || '').split(':');
  return (+p[0] || 0) * 60 + (+p[1] || 0);
};

const hhmmOf = (m) =>
  String((m / 60) | 0).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');

/** THE RIGHT EDGE OF THE DAY (ruling D4). Call it on every poll and every
 *  scrub; from 14:30 it returns 15:30 and stops moving. */
export function t1For(now) {
  const m = mins(now) + HEADROOM_MIN;
  return hhmmOf(Math.max(mins(T1_MIN), Math.min(mins(T1), m)));
}

/** Pixels per minute on the axis as it currently stands -- printed in the rail
 *  footer, because a 6.5 px/min map and a 2.9 px/min map are not the same
 *  picture and the reader has to be told which one is in front of her. */
export function pxPerMin(box, t0 = T0, t1 = T1) {
  return box.w / Math.max(1, mins(t1) - mins(t0));
}

export function xOfHHMM(hhmm, box, t0 = T0, t1 = T1) {
  const a = mins(t0), b = mins(t1);
  return box.x + box.w * Math.max(0, Math.min(1, (mins(hhmm) - a) / (b - a)));
}

/** Draws the hour ticks and returns the two mappings the callers share. */
export function axis(ctx, box, t0 = T0, t1 = T1, opts = {}) {
  const a = mins(t0), b = mins(t1);
  const x = (hhmm) => xOfHHMM(hhmm, box, t0, t1);
  const xInv = (px) => {
    const m = a + ((px - box.x) / box.w) * (b - a);
    const c = Math.max(a, Math.min(b, Math.round(m)));
    return String((c / 60) | 0).padStart(2, '0') + ':' + String(c % 60).padStart(2, '0');
  };
  ctx.save();
  ctx.strokeStyle = opts.hair || '#d8dce2';
  ctx.fillStyle = opts.muted || '#4a5568';
  ctx.font = '11px Consolas, ui-monospace, monospace';
  for (let m = a; m <= b; m += 60) {
    const hh = String((m / 60) | 0).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
    const px = x(hh);
    ctx.beginPath(); ctx.moveTo(px, box.y); ctx.lineTo(px, box.y + box.h); ctx.stroke();
    ctx.fillText(hh, px + 2, box.y + box.h - 2);
  }
  if (opts.bf_at) {
    const px = x(opts.bf_at);
    ctx.setLineDash([2, 2]);
    ctx.beginPath(); ctx.moveTo(px, box.y); ctx.lineTo(px, box.y + box.h); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillText('bf → ' + opts.bf_at, px + 2, box.y + 10);
  }
  ctx.restore();
  return { x, xInv, y0: box.y, y1: box.y + box.h };
}

/** One segment of one lane.
 *
 *  `bf` paints at 55 % AND OUTLINE-ONLY, and never merges with an observed
 *  segment. 55 % alone was not enough: 55 % of a mid-tone on a dark ground
 *  still reads as full strength, so a reconstructed morning looked exactly as
 *  watched as the afternoon. Dropping the fill as well makes the difference
 *  survive both themes.
 *
 *  `o.colour` overrides the side hue (the FUT strip is painted in --ink) and
 *  `o.alpha` its opacity. */
export function tex(ctx, x0, x1, y, h, kind, o) {
  const col = o.colour || (o.side === 'CE' ? o.ce : o.pe);
  const w = Math.max(1, x1 - x0);
  ctx.save();
  if (o.bf) ctx.globalAlpha = 0.55;
  else if (o.alpha !== undefined) ctx.globalAlpha = o.alpha;
  ctx.fillStyle = col;
  ctx.strokeStyle = col;
  ctx.lineWidth = 1;
  if (o.bf) {                                                    // OUTLINE ONLY
    ctx.strokeRect(x0 + 0.5, y + 0.5, w - 1, Math.max(1, h - 1));
  } else if (kind === 'writing' || kind === 'build') {
    ctx.fillRect(x0, y, w, h);                                   // solid
  } else if (kind === 'loading') {
    for (let i = x0; i < x1; i += 4) ctx.fillRect(i, y, 2, h);   // dotted
  } else if (kind === 'covering' || kind === 'retreat') {
    ctx.strokeRect(x0 + 0.5, y + 0.5, w - 1, h - 1);             // hollow
  } else {                                                       // liquidation
    ctx.strokeRect(x0 + 0.5, y + 0.5, w - 1, h - 1);
    for (let i = x0; i < x1; i += 3) {
      ctx.beginPath(); ctx.moveTo(i, y + h); ctx.lineTo(i + h, y); ctx.stroke();
    }
  }
  ctx.restore();
}

export function scrub(ctx, box, t, t0 = T0, t1 = T1, opts = {}) {
  if (!t) return;
  const px = xOfHHMM(t, box, t0, t1);
  ctx.save();
  ctx.fillStyle = opts.dim || 'rgba(128,128,128,0.18)';
  ctx.fillRect(px, box.y, box.x + box.w - px, box.h);      // everything right of the cursor dims
  ctx.strokeStyle = opts.accent || '#b26b00';
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(px, box.y); ctx.lineTo(px, box.y + box.h); ctx.stroke();
  ctx.restore();
}

/** THE BATTLEFIELD. `day` is the /api/day/oi body. `opts` carries the palette,
 *  the window, the fuel block from /api/warmap.<idx>.runways, `opts.t1` (the
 *  axis right edge for this poll, from `t1For`), and `opts.cursor` — the lane
 *  index j/k is on. Returns the lane order so the rail can print one aligned
 *  line per lane, in the same order, at the same y. */
export function campaign(ctx, box, day, opts = {}) {
  const lanes = (day && day.lanes ? day.lanes : []).slice(0, LANE_CAP);
  const t1 = opts.t1 || T1;
  const fuelW = opts.fuelW || 120;
  const mapBox = { x: box.x, y: box.y, w: Math.max(80, box.w - fuelW - 8), h: box.h - FUT_H - 14 };
  ctx.clearRect(box.x, box.y, box.w, box.h);
  const A = axis(ctx, mapBox, T0, t1, { ...opts, bf_at: day && day.bf_at });
  if (!lanes.length) {
    ctx.save();
    ctx.fillStyle = opts.muted || '#4a5568';
    ctx.font = 'italic 13px "Segoe UI", system-ui, sans-serif';
    ctx.fillText('PATA NAHI — ' + ((day && day.lanes_why) || 'no campaign yet'),
      mapBox.x + 8, mapBox.y + 20);
    ctx.restore();
    return { lanes: [], laneY: [], mapBox, t1, pxmin: pxPerMin(mapBox, T0, t1) };
  }
  // y = price: each strike is a lane at its own price, spot the contested line
  const ks = lanes.map((l) => l.strike);
  const hi = Math.max(...ks, day.spot), lo = Math.min(...ks, day.spot);
  const pad = Math.max(1, (hi - lo) * 0.08);
  const yOf = (p) => mapBox.y + mapBox.h * (1 - (p - (lo - pad)) / ((hi + pad) - (lo - pad)));
  // THE LANE PITCH IS THE CONSTANT, not a fraction of a measured canvas: the
  // rail row in desk.css is pinned to the same number (ruling D7).
  const laneH = LANE_PITCH;

  // THE SPOT DOT IS DRAWN FOR THREE LANES ONLY: the j/k cursor row and the two
  // largest. Fourteen anonymous dots on the contested line are noise, and the
  // dot is only readable when you know which lane put it there.
  const cursor = ((opts.cursor || 0) % lanes.length + lanes.length) % lanes.length;
  const dotFor = new Set([lanes[cursor] && lanes[cursor].strike].concat(
    lanes.slice().sort((a, b) => Math.abs(b.added || 0) - Math.abs(a.added || 0))
      .slice(0, 2).map((l) => l.strike)));

  const laneY = [];
  const maxAdded = Math.max(1, ...lanes.map((l) => Math.abs(l.ghost_hi || l.added || 0)));
  lanes.forEach((l, i) => {
    const y = yOf(l.strike) - laneH / 2;
    laneY.push(y + laneH / 2);
    const thick = (v) => Math.max(1, laneH * Math.min(1, Math.abs(v) / maxAdded));
    // the GHOST: the high-water outline stays so the trench is visible after
    // the fill retreats inside it
    if (l.retreat && l.since) {
      ctx.save();
      ctx.globalAlpha = 0.35;
      ctx.strokeStyle = l.side === 'CE' ? opts.ce : opts.pe;
      ctx.strokeRect(A.x(l.since) + 0.5, y + 0.5, Math.max(1, A.x(day.ts) - A.x(l.since)) - 1,
        thick(l.ghost_hi) - 1);
      ctx.restore();
    }
    for (let s = 0; s < (l.segments || []).length; s++) {
      const seg = l.segments[s];
      const next = l.segments[s + 1];
      const x0 = A.x(seg.t);
      const x1 = next ? A.x(next.t) : A.x(day.ts);
      const kind = opts.win === 5
        ? ((seg.added >= (l.segments[s - 1] ? l.segments[s - 1].added : 0)) ? 'build' : 'retreat')
        : seg.state4;
      tex(ctx, x0, x1, y, thick(seg.added), kind,
        { ...opts, side: l.side, bf: !!seg.bf });
    }
    // the PEAK: a 1 px notch at its time, on EVERY lane, plus a dot at that
    // minute's spot for the cursor row and the two largest ONLY. The words
    // live in the rail line -- labels cannot collide because they are not here.
    if (l.peak && l.peak.t) {
      const px = A.x(l.peak.t);
      ctx.save();
      ctx.strokeStyle = opts.ink || '#0b0e13';
      ctx.beginPath(); ctx.moveTo(px, y - 2); ctx.lineTo(px, y + laneH + 2); ctx.stroke();
      if (l.peak.spot != null && dotFor.has(l.strike)) {
        ctx.fillStyle = opts.ink || '#0b0e13';
        ctx.beginPath(); ctx.arc(px, yOf(l.peak.spot), 1.6, 0, 6.3); ctx.fill();
      }
      ctx.restore();
    }
  });

  // MIGRATION ARROWS: paired unwind at A, build at B, same side, same window
  ctx.save();
  ctx.strokeStyle = opts.muted || '#4a5568';
  for (const m of (day.migrations || [])) {
    const px = A.x(m.t);
    ctx.beginPath(); ctx.moveTo(px, yOf(m.from)); ctx.lineTo(px + 10, yOf(m.to)); ctx.stroke();
  }
  ctx.restore();

  // THE CONTESTED LINE: spot through the strike lanes
  if (day.spot != null) {
    ctx.save();
    ctx.strokeStyle = opts.ink || '#0b0e13';
    ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(mapBox.x, yOf(day.spot)); ctx.lineTo(mapBox.x + mapBox.w, yOf(day.spot));
    ctx.stroke(); ctx.setLineDash([]); ctx.restore();
  }

  // THE FUTURES STRIP: 28 px under the map, same x axis, same textures,
  // painted in --ink at 70 % -- it is the SECOND ARMY, not a footnote, and
  // --dim made it read as one. Its holes are its own: never faked from the
  // frame's single delta.
  const fy = mapBox.y + mapBox.h + 6;
  const fut = day.fut || {};
  if (!(fut.segments || []).length) {
    ctx.save();
    ctx.fillStyle = opts.muted || '#4a5568';
    ctx.font = 'italic 11px "Segoe UI", system-ui, sans-serif';
    ctx.fillText('FUT  PATA NAHI — ' + (fut.why || 'no bars'), mapBox.x + 4, fy + 16);
    ctx.restore();
  } else {
    fut.segments.forEach((seg, i) => {
      const nx = fut.segments[i + 1];
      tex(ctx, A.x(seg.t), nx ? A.x(nx.t) : A.x(day.ts), fy, FUT_H - 6,
        opts.win === 5 ? (seg.d_oi >= 0 ? 'build' : 'retreat') : seg.state4,
        { ...opts, colour: opts.ink || '#0b0e13', alpha: 0.7, bf: !!seg.bf });
    });
  }

  // THE FUEL TANK: a vertical bar outside the map at the far right, full map
  // height, split at spot -- CE notional above, PE below.
  const fx = box.x + box.w - fuelW + 8;
  const run = opts.runways;
  ctx.save();
  if (!run || !run.ok) {
    ctx.fillStyle = opts.muted || '#4a5568';
    ctx.font = 'italic 11px "Segoe UI", system-ui, sans-serif';
    ctx.fillText('PATA NAHI —', fx, mapBox.y + 14);
    ctx.fillText('runways not ok', fx, mapBox.y + 26);
  } else {
    const ySpot = day.spot != null ? yOf(day.spot) : mapBox.y + mapBox.h / 2;
    const cap = Math.max(1, (run.up && run.up.fuel) || 0, (run.down && run.down.fuel) || 0);
    const bw = Math.max(6, fuelW - 40);
    ctx.fillStyle = opts.ce;
    const hUp = (mapBox.h / 2) * Math.min(1, ((run.up && run.up.fuel) || 0) / cap);
    ctx.fillRect(fx, ySpot - hUp, bw, hUp);
    ctx.fillStyle = opts.pe;
    const hDn = (mapBox.h / 2) * Math.min(1, ((run.down && run.down.fuel) || 0) / cap);
    ctx.fillRect(fx, ySpot, bw, hDn);
    // the trigger price per side: a tick on the shared price axis
    ctx.strokeStyle = opts.accent || '#b26b00';
    for (const side of ['up', 'down']) {
      const t = run[side] && run[side].target;
      if (t && t.px != null) {
        const yy = yOf(t.px);
        ctx.beginPath(); ctx.moveTo(fx - 6, yy); ctx.lineTo(fx + bw, yy); ctx.stroke();
      }
    }
  }
  ctx.restore();

  scrub(ctx, mapBox, opts.scrub, T0, t1, opts);
  return { lanes, laneY, mapBox, t1, pxmin: pxPerMin(mapBox, T0, t1) };
}

/** THE HONEST LEDGER's four lanes: price 90, state 30 (+ gate 12), visits 60,
 *  marks 26 -- THE SAME x axis, the same right edge `opts.t1` and the same
 *  scrubber as CAMPAIGN, so switching 2 <-> 3 never moves a minute. */
export function record(ctx, box, rows, visits, ring, opts = {}) {
  ctx.clearRect(box.x, box.y, box.w, box.h);
  const t1 = opts.t1 || T1;
  const H = { price: 90, state: 30, gate: 12, visits: 60, marks: 26 };
  const lane = (k, prev) => ({ x: box.x, y: prev, w: box.w, h: H[k] });
  let y = box.y;
  const bPrice = lane('price', y); y += H.price + 4;
  const bState = lane('state', y); y += H.state;
  const bGate = lane('gate', y); y += H.gate + 4;
  const bVisit = lane('visits', y); y += H.visits + 4;
  const bMark = lane('marks', y);
  const A = axis(ctx, { x: box.x, y: box.y, w: box.w, h: y + H.marks - box.y }, T0, t1, opts);

  const label = (b, s) => {
    ctx.save(); ctx.fillStyle = opts.muted || '#4a5568';
    ctx.font = '11px "Segoe UI", system-ui, sans-serif';
    ctx.fillText(s, box.x + 2, b.y + 10); ctx.restore();
  };
  label(bPrice, 'price'); label(bState, 'state'); label(bGate, 'gate');
  label(bVisit, 'visits'); label(bMark, 'marks');

  const px = (rows || []).filter((r) => r.px != null);
  if (px.length) {
    const hi = Math.max(...px.map((r) => r.px)), lo = Math.min(...px.map((r) => r.px));
    const pad = Math.max(1, (hi - lo) * 0.1);
    const yP = (p) => bPrice.y + bPrice.h * (1 - (p - (lo - pad)) / ((hi + pad) - (lo - pad)));
    ctx.save(); ctx.strokeStyle = opts.ink || '#0b0e13'; ctx.beginPath();
    px.forEach((r, i) => (i ? ctx.lineTo(A.x(r.t), yP(r.px)) : ctx.moveTo(A.x(r.t), yP(r.px))));
    ctx.stroke(); ctx.restore();
  } else {
    ctx.save(); ctx.fillStyle = opts.muted || '#4a5568';
    ctx.font = 'italic 11px "Segoe UI", system-ui, sans-serif';
    ctx.fillText('PATA NAHI — no record rows for this day', box.x + 40, bPrice.y + 20);
    ctx.restore();
  }

  // state and gate as SEGMENTS, one per run of the same word.
  //
  // `TRIGGERED` TAKES THE SOLID PAKKA RULE, NEVER THE REVERSED BLOCK. The
  // reversed block means NAHI -- actively negative -- and the state lane
  // painting a fired setup that way told the reader the opposite of what
  // happened. Only a KILLED or DEAD thing is reversed.
  const SOLID = new Set(['TRIGGERED']);
  const REVERSED = new Set(['NAHI', 'killed', 'dead']);
  const band = (b, key, colour) => {
    let i = 0;
    while (i < (rows || []).length) {
      let j = i;
      while (j + 1 < rows.length && rows[j + 1][key] === rows[i][key]) j++;
      const x0 = A.x(rows[i].t), x1 = j + 1 < rows.length ? A.x(rows[j + 1].t) : box.x + box.w;
      const word = String(rows[i][key] || '—');
      const w = Math.max(1, x1 - x0);
      ctx.save();
      ctx.strokeStyle = colour; ctx.fillStyle = colour;
      if (word === 'PATA NAHI') { ctx.globalAlpha = 0.25; ctx.setLineDash([2, 2]); }
      if (REVERSED.has(word)) {
        ctx.fillRect(x0, b.y, w, b.h);
        ctx.fillStyle = opts.ground || '#ffffff';
      } else if (SOLID.has(word)) {
        ctx.fillRect(x0, b.y + b.h - 3, w, 3);       // the solid PAKKA rule
        ctx.strokeRect(x0 + 0.5, b.y + 0.5, w - 1, b.h - 1);
      } else {
        ctx.strokeRect(x0 + 0.5, b.y + 0.5, w - 1, b.h - 1);
      }
      ctx.font = '10px Consolas, ui-monospace, monospace';
      if (x1 - x0 > 34) ctx.fillText(word.slice(0, 9), x0 + 3, b.y + b.h - 5);
      ctx.restore();
      i = j + 1;
    }
  };
  band(bState, 'state', opts.ink || '#0b0e13');
  band(bGate, 'gate', opts.muted || '#4a5568');

  // VISITS: one glyph per visit with a +30 m outcome bar, up-tint favourable
  for (const v of (visits || [])) {
    const x0 = A.x(v.t0);
    const ex = (v.ex || {})['6'];
    const good = ex != null && v.sigma != null && ex >= v.sigma;
    ctx.save();
    ctx.strokeStyle = good ? (opts.buy || '#0f7b6c') : (opts.sell || '#c0392b');
    ctx.beginPath(); ctx.arc(x0, bVisit.y + bVisit.h / 2, 4, 0, 6.3); ctx.stroke();
    const x1 = A.x(addMin(v.t0, 30));
    ctx.beginPath(); ctx.moveTo(x0 + 5, bVisit.y + bVisit.h / 2);
    ctx.lineTo(x1, bVisit.y + bVisit.h / 2); ctx.stroke();
    ctx.font = '10px Consolas, ui-monospace, monospace';
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fillText((ex == null ? '—' : (ex >= 0 ? '+' : '') + Math.round(ex)), x1 + 3,
      bVisit.y + bVisit.h / 2 + 3);
    ctx.restore();
  }

  // MARKS: the lane where the desk indicts itself -- record appends, fire
  // transitions, source outages from the health ring, paper refusals.
  ctx.save();
  ctx.fillStyle = opts.muted || '#4a5568';
  ctx.font = '10px Consolas, ui-monospace, monospace';
  for (const m of (opts.marks || [])) {
    const x0 = A.x(m.t);
    ctx.fillRect(x0, bMark.y + 6, 3, 3);
    ctx.fillText(m.label, x0 + 5, bMark.y + 12);
  }
  ctx.restore();

  scrub(ctx, { x: box.x, y: box.y, w: box.w, h: y + H.marks - box.y }, opts.scrub, T0, t1, opts);
}

function addMin(hhmm, n) {
  const t = mins(hhmm) + n;
  return String((t / 60) | 0).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0');
}
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: `# pass 8`, `# fail 0`.

- [ ] **Step 5: Commit**

```bash
git add ui/desk/lanes.js ui/desk/test.mjs
git commit -m "lanes: one shared axis that follows the day (09:15 to clamp(now+60, 11:30, 15:30)), four textures at 15m/day and two at 5m, outline-only backfill, three spot dots, fut strip in ink"
```

---

### Task 14: CAMPAIGN on screen — the rail lines, the labelled totals, the `w` windows

**Goal:** all text lives in the fixed right rail, one aligned line per lane, so labels cannot collide by construction.

**Files:** Modify `ui/desk/desk.js` (import `lanes.js`, add `renderCampaign`, register it).

**Rail line grammar, five fixed columns (spec §E, §M, ruling D7):**
`<SIDE strike>` · `<+added since open>` · `<peak marker or state word>` · `<time>` · `<migration target>`
e.g. `PE 23200 · +8.1M · peak 11:30 @23,188 · 11:30 · ← 23150`. Each column has its **own fixed width and its own ellipsis**, **no cell wraps**, and the row height is **pinned to `--lane-pitch`** — the same constant `lanes.js` exports as `LANE_PITCH`. The rail footer is a **constant height** (`--rail-foot-h`). Together those three are what stop a poll from reflowing a row, and they mean **neither the canvas nor the DOM ever reads the other's measured height**. The CSS is already in `desk.css` (`.side-rail .row`, `.rail-foot`).

**The footer prints px-per-minute (ruling D4).** The axis now follows the day, so a 6.5 px/min map at 11:05 and a 2.9 px/min map at the close are not the same picture. The reader is told which one is in front of her.

- [ ] **Step 1: Add the import** — at the top of `ui/desk/desk.js`, immediately after the file's opening comment block and before `export const SCREENS`, add:

```js
import { campaign as drawCampaign, record as drawRecord,
         LANE_CAP, t1For } from './lanes.js';
```

- [ ] **Step 2: Add a palette reader and the renderer** — insert directly above the line `export const renderers = { today: renderToday, campaign: () => {}, record: () => {} };`:

```js
// ---- screen 2: CAMPAIGN ---------------------------------------------------

/** The canvas needs real hex, and the tokens are the single source. Read them
 *  from the computed style so `t` (theme) repaints correctly with no second
 *  palette to drift. */
function palette() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n) => cs.getPropertyValue(n).trim();
  return { ce: v('--ce'), pe: v('--pe'), buy: v('--buy'), sell: v('--sell'),
           accent: v('--accent'), ink: v('--ink'), muted: v('--muted'),
           ground: v('--ground'), panel: v('--panel'), hair: v('--hair') };
}

/** Canvas at device pixel ratio, sized from its CSS box. Called on every
 *  paint: the box is fixed by the skeleton, so this never changes layout. */
function fitCanvas(cv) {
  const r = cv.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  cv.width = Math.max(1, Math.round(r.width * dpr));
  cv.height = Math.max(1, Math.round(r.height * dpr));
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, box: { x: 0, y: 0, w: r.width, h: r.height } };
}

function renderCampaign() {
  const d = S.data.oi;
  const wm = ((S.data.warmap || {}).indices || {})[S.idx] || {};
  const heat = wm.heat || [];
  const run = wm.runways || null;

  // THE CARRY -- the one coloured state element on this screen: worst pain
  // side and strike from warmap.heat, trip price from runways.<side>.target.px
  let word = 'THE CARRY', sub, lvl;
  if (!heat.length) {
    sub = hole('no warmap for ' + S.idx); lvl = 'PATA NAHI';
  } else {
    const w = heat.reduce((a, h) =>
      Math.max(h.ce_pain || 0, h.pe_pain || 0) > Math.max(a.ce_pain || 0, a.pe_pain || 0) ? h : a);
    const side = (w.ce_pain || 0) >= (w.pe_pain || 0) ? 'CE' : 'PE';
    const pain = side === 'CE' ? w.ce_pain : w.pe_pain;
    const trip = run && run.ok && run[side === 'CE' ? 'up' : 'down']
      && run[side === 'CE' ? 'up' : 'down'].target;
    sub = side + ' ' + w.k + ' under water · pain ' + fmt.pct(pain, 0) + ' ~'
      + (trip && trip.px != null ? ' · trips ' + fmt.rs(trip.px).replace('₹', '') + ' ~'
                                 : ' · ' + hole('runways not ok'));
    lvl = 'SHAK';                   // pain is inferred, never measured
  }
  headline(word, sub, lvl);

  const { ctx, box } = fitCanvas(document.getElementById('cv-campaign'));
  const p = palette();
  // THE AXIS RIGHT EDGE IS RECOMPUTED HERE, on every poll and every scrub --
  // `paint()` runs on both, so there is no second clock to fall behind.
  const t1 = t1For(S.scrub || nowHHMM());
  const drawn = drawCampaign(ctx, box,
    d || { lanes: [], lanes_why: S.why.oi || 'day/oi not answering' },
    { ...p, win: S.win, scrub: S.scrub, runways: run, t1, cursor: cur(),
      fuelW: window.innerWidth <= 960 ? 40 : 120 });

  // THE RAIL: five fixed columns, one aligned line per lane, in the canvas's
  // own lane order. Totals are LABELLED and sit in their own block -- a total
  // beside an added-since-open, unlabelled, is the toolb units bug.
  const el = document.getElementById('rail-campaign');
  if (!d || !(d.lanes || []).length) {
    el.innerHTML = '<div class="hole">' + hole((d && d.lanes_why) || S.why.oi) + '</div>';
    return;
  }
  const lanes = d.lanes.slice(0, LANE_CAP);
  const biggest = lanes.slice().sort((a, b) => Math.abs(b.added) - Math.abs(a.added))
    .slice(0, 2).map((l) => l.strike);
  const migTo = {};
  for (const m of (d.migrations || [])) migTo[m.from] = m.to;
  // FIVE FIXED COLUMNS, one per lane, in the canvas's own lane order and at
  // the same row height. No cell wraps; each has its own ellipsis in the CSS.
  el.innerHTML = lanes.map((l, i) => {
    const full = i === (cur() % lanes.length) || biggest.includes(l.strike);
    const last = (l.segments || [])[(l.segments || []).length - 1] || {};
    const third = full && l.peak
      ? 'peak ' + l.peak.t + ' @' + fmt.rs(l.peak.spot).replace('₹', '')
      : (S.win === 5 ? (last.state4 || '—') : (l.retreat ? 'retreat' : (last.state4 || '—')));
    return '<div class="row' + (full ? ' on' : '') + '">'
      + '<span class="' + l.side.toLowerCase() + '">' + l.side + ' ' + l.strike + '</span>'
      + '<span>+' + fmt.num(l.added) + '</span>'
      + '<span>' + third + '</span>'
      + '<span>' + (l.since || '—') + '</span>'
      + '<span>' + (migTo[l.strike] ? '← ' + migTo[l.strike] : '') + '</span></div>';
  }).join('')
    // THE FOOTER IS A CONSTANT HEIGHT (.rail-foot) -- totals labelled, the
    // cap, the window, and px-per-minute so two times of day stay comparable.
    + '<div class="rail-foot mark">'
    + 'CE added since open ' + fmt.num((d.totals || {}).ce_added_since_open)
    + ' · PE added since open ' + fmt.num((d.totals || {}).pe_added_since_open)
    + (d.totals_why ? ' <span class="hole">' + hole(d.totals_why) + '</span>' : '')
    + (d.capped ? '<br>+' + d.capped + ' more' : '')
    + '<br>win ' + (S.win === 'day' ? 'day' : S.win + 'm') + ' (w) · as of ' + fmt.hhmm(d.ts)
    + ' · axis 09:15–' + drawn.t1 + ' · ' + drawn.pxmin.toFixed(1) + ' px/min'
    + '</div>';
}
```

- [ ] **Step 3: Register the renderer** — replace:

```js
export const renderers = { today: renderToday, campaign: () => {}, record: () => {} };
```

with:

```js
export const renderers = { today: renderToday, campaign: renderCampaign, record: () => {} };
```

- [ ] **Step 4: Repaint on resize** — in `mount()`, find:

```js
  document.addEventListener('keydown', onKey);
```

and replace with:

```js
  document.addEventListener('keydown', onKey);
  window.addEventListener('resize', paint);
```

- [ ] **Step 5: Run the test and look**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: `# pass 8`, `# fail 0`.

Open `http://127.0.0.1:8765/desk/`, press `2`, then `w` three times, then `[` a few times.
Expected: until the owner restarts the server, the map prints `PATA NAHI — route not on the running server (404)` in place and the rail prints the same clause; the canvas is the right size at both 1920 and 960; `w` cycles the label `win 5m → win 15m → win day`; the footer's `axis 09:15–HH:MM · N.N px/min` changes as you scrub and stops changing once the right edge is 15:30.

- [ ] **Step 6: Commit**

```bash
git add ui/desk/desk.js
git commit -m "desk ui: CAMPAIGN -- the carry headline, the canvas battlefield on the axis that follows the day, five fixed rail columns with per-column ellipsis, labelled totals, px/min in the footer"
```

- [ ] **Step 7: Phase C gate (spec §K)** — tick each by eye once the server has been restarted by the owner:
  - [ ] 15 m textures readable at 960 px on white
  - [ ] the ±7 cap holds with `+N more` in the rail
  - [ ] the totals row is labelled `CE added since open` / `PE added since open`, and carries its `totals_why` whenever the chain started late
  - [ ] backfilled segments are visibly at 55 % **and outline-only** and the `bf → HH:MM` marker is on the axis
  - [ ] the axis right edge is `clamp(now + 60 min, 11:30, 15:30)` and the footer prints its px/min
  - [ ] every rail row is exactly one lane pitch high and no cell wraps; a long cell ellipses inside its own column
  - [ ] the spot dot appears on three lanes only — the `j`/`k` cursor row and the two largest

---

## PHASE D — RECORD (Task 15)

### Task 15: RECORD — four lanes, visit cards, the series table, the money strip

**Goal:** the honest ledger — the miss is the first word, counts only, never a percentage.

**Files:** Modify `ui/desk/desk.js` (add `renderRecord`, register it).

**Interfaces:** Consumes `/api/day/record`, `/api/day/visits`, `/api/series`, `/api/paperdesk`, `/api/desk/today.adjust`, and `/api/desk/health.ring`.

**THERE IS NO VISIT-LEDGER TABLE.** `j`/`k` walks the card; a table of every visit is the card repeated seven times, and the ruling deletes it. The money strip keeps the height (`.region-money` is 20 %, not 14 %) — the day's ledger of money belongs beside the day's ledger of calls, and TODAY is a sixty-second screen.

**Tally order (ruling D1):** `missed · false · wrong · called · spared · quiet (n)`. **The two ways the tool is wrong print first.** Counts only, never a percentage — house rule 4.

**The card prints σ in points beside the multiple (ruling D2):** `+137 = 7.6σ · σ 18 @ 09:45`. Source, unit and threshold travel together, so no reader has to guess what a σ is here.

- [ ] **Step 1: Add the renderer** — insert directly above the `export const renderers = ...` line:

```js
// ---- screen 3: RECORD -----------------------------------------------------

function renderRecord() {
  const rows = S.data.record || [];
  const visits = S.data.visits || [];
  const ser = S.data.series || [];

  // the headline names the population the cursor is on, and its level
  const taps = ser.find((r) => r.name === 'taps');
  headline('SCORE',
    taps ? 'taps n=' + taps.n + ' of 20 · ' + (taps.level === 'PATA NAHI'
            ? hole(taps.why) : taps.level + ' — ' + taps.why)
         : hole(S.why.series || 'series route not answering'),
    taps ? (taps.level === 'SHAK' ? 'SHAK' : 'PATA NAHI') : 'PATA NAHI');

  // MARKS: record appends, fire transitions, source outages, paper refusals --
  // the lane where the desk indicts itself.
  const marks = [];
  for (const r of rows) if (r.fire) marks.push({ t: r.t, label: 'fire' });
  for (const t of ((S.data.health || {}).ring || [])) {
    marks.push({ t: fmt.hhmm(new Date((t.t || 0) * 1000).toTimeString().slice(0, 5)),
                 label: t.source + ' ' + t.to });
  }
  for (const rf of (((S.data.paperdesk || {}).desk || {}).day_refusals || [])) {
    marks.push({ t: fmt.hhmm(String(rf.ts || '')), label: 'refuse' });
  }

  const { ctx, box } = fitCanvas(document.getElementById('cv-record'));
  // THE SAME AXIS RIGHT EDGE AS CAMPAIGN, so 2 <-> 3 never moves a minute.
  drawRecord(ctx, box, rows, visits, (S.data.health || {}).ring || [],
    { ...palette(), scrub: S.scrub, t1: t1For(S.scrub || nowHHMM()), marks });

  // THE VISIT CARD for the j/k cursor row -- THERE IS NO VISIT TABLE, the card
  // IS the ledger and j/k walks it. The outcome is the FIRST word.
  const card = document.getElementById('card');
  if (!visits.length) {
    card.innerHTML = '<div class="hole">' + hole(S.why.visits || 'no zone visit in the record yet') + '</div>';
  } else {
    const v = visits[cur() % visits.length];
    const ex6 = (v.ex || {})['6'], ex90 = (v.ex || {})['90m'], adv = (v.adverse || {})['6'];
    // σ IN POINTS BESIDE THE MULTIPLE: `+137 = 7.6σ · σ 18 @ 09:45`.
    const sigLine = (v.sigma == null || ex6 == null)
      ? '<span class="hole">' + hole(v.sigma_why || v.ex_why) + '</span>'
      : (ex6 >= 0 ? '+' : '−') + Math.abs(ex6) + ' = ' + (ex6 / v.sigma).toFixed(1)
        + 'σ · σ ' + v.sigma + ' @ ' + v.t0;
    card.innerHTML =
      '<div><b>' + v.t0 + '</b>  ' + v.band + ' visit  ' + v.side + '  <b>' + v.outcome + '</b>'
      + (v.outcome_why ? ' <span class="hole">' + hole(v.outcome_why) + '</span>' : '') + '</div>'
      + '<div>' + (ex6 == null ? hole(v.ex_why) : (ex6 >= 0 ? '+' : '') + ex6)
      + ' / ' + (adv == null ? '—' : adv) + ' in 30m · '
      + (ex90 == null ? '—' : (ex90 >= 0 ? '+' : '') + ex90) + ' in 90m</div>'
      + '<div>' + sigLine + '</div>'
      + '<div>screen said: ' + (v.said.state || '—') + ' · fire ' + v.fired + '</div>'
      + '<div>flow ' + (v.said.flow_n || 'none') + ' · confirm ' + v.said.confirm + '</div>'
      + '<div>votes ' + (v.votes == null ? '<span class="hole">' + v.votes_why + '</span>' : v.votes) + '</div>'
      + '<div class="mark">' + v.adverse_src + '</div>'
      + '<div>' + tally(visits) + '</div>';
  }

  // SERIES: <=12 rows. Level is PATA NAHI until n>=20, then SHAK. It NEVER
  // says "works" -- NAHI needs a kill rule that exists and fires.
  document.getElementById('series').innerHTML =
    '<h3><span>the forward populations</span><span class="mark">horizon 30</span></h3>'
    + (ser.length
      ? ser.slice(0, 12).map((r) =>
        '<div>' + r.name.padEnd(16, ' ') + '  n ' + r.n + '  sessions ' + r.sessions
        + '  started ' + (r.started || '—') + '  horizon ' + r.horizon + '  '
        + (r.level === 'PATA NAHI' ? '<span class="hole">' + hole(r.why) + '</span>'
                                   : r.level + ' — ' + r.why) + '</div>').join('')
      : '<div class="hole">' + hole(S.why.series) + '</div>');

  // MONEY: paper only, labelled, the maker-fill caveat travels with it, and it
  // carries THE ADJUSTMENT BRAKE. It inherits the height the deleted
  // visit-ledger table would have taken.
  const pd = (S.data.paperdesk || {}).desk || {};
  const risk = pd.risk || {};
  const th = pd.theta_day_est || {};
  const adj = (S.data.today || {}).adjust || {};
  // `adjustments 4 of 6`. Free execution's failure mode is over-adjustment, so
  // the brake is deliberate and visible; at the cap the number takes the SHAK
  // hatch. IT ADVISES AND BLOCKS NOTHING -- there is no order path.
  const brake = adj.n == null
    ? '<span class="hole">' + hole(adj.why || 'adjustments not counted') + '</span>'
    : '<span class="num' + (adj.n >= adj.cap ? ' shak' : '') + '">adjustments '
      + adj.n + ' of ' + adj.cap + '</span>';
  document.getElementById('money').innerHTML =
    '<h3><span>paper ₹' + fmt.num(risk.capital) + ' · maker fills are an UPPER bound</span>'
    + '<span class="mark">' + (pd.day || '—') + '</span></h3>'
    + '<div>theta ' + (th.rupees == null
        ? '<span class="hole">' + hole(th.no_legs_why || 'theta not built') + '</span>'
        : fmt.rs(th.rupees) + ' ~')
    + ' · forced_ratio ' + (risk.forced_ratio == null
        ? '<span class="hole">' + hole(risk.forced_why) + '</span>' : risk.forced_ratio)
    + ' · headroom ' + (risk.headroom == null
        ? '<span class="hole">' + hole(risk.margin_why) + '</span>' : fmt.rs(risk.headroom) + ' ~')
    + '</div>'
    + '<div>' + brake + ' <span class="mark">advisory — this stack has no order path</span></div>'
    + '<div>refusals today ' + (pd.day_refusals || []).length
    + (pd.day_refusals && pd.day_refusals.length
        ? ': ' + pd.day_refusals.slice(0, 3).map((r) => r.why).join(' · ') : '') + '</div>';
}

/** THE TALLY, IN LADDER ORDER (ruling D1): missed · false · wrong · called ·
 *  spared · quiet (n). The two ways the tool is WRONG print first -- a false
 *  alarm and a correct silence are different facts and no longer share a
 *  bucket. Counts only, no percentage: house rule 4. */
function tally(visits) {
  const c = { MISSED: 0, FALSE: 0, WRONG: 0, CALLED: 0, SPARED: 0, QUIET: 0, 'PATA NAHI': 0 };
  for (const v of visits) if (c[v.outcome] !== undefined) c[v.outcome]++;
  return 'missed ' + c.MISSED + ' · false ' + c.FALSE + ' · wrong ' + c.WRONG
    + ' · called ' + c.CALLED + ' · spared ' + c.SPARED + ' · quiet ' + c.QUIET
    + (c['PATA NAHI'] ? ' · pata nahi ' + c['PATA NAHI'] : '')
    + '   (n ' + visits.length + ')';
}
```

- [ ] **Step 2: Register the renderer** — replace:

```js
export const renderers = { today: renderToday, campaign: renderCampaign, record: () => {} };
```

with:

```js
export const renderers = { today: renderToday, campaign: renderCampaign, record: renderRecord };
```

- [ ] **Step 3: Run the test and look**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: `# pass 8`, `# fail 0`.

Open `http://127.0.0.1:8765/desk/`, press `3`, then `[` `]` `g` and `j` `k`.
Expected: the four lanes draw their axis and each prints its own hole clause; `[` and `]` move the headline stamp to `as of HH:MM (scrubbed)`; `g` returns it to the clock; `j`/`k` move the visit card **and leave CAMPAIGN's lane cursor where it was**.

- [ ] **Step 4: Commit**

```bash
git add ui/desk/desk.js
git commit -m "desk ui: RECORD -- four lanes on the shared axis, visit cards with the outcome first and sigma in points, the series table that tops out at SHAK, the money strip with the adjustment brake"
```

- [ ] **Step 5: Phase D gate (spec §K)** — tick each once the owner has restarted the server:
  - [ ] `[` `]` `space` `g` move both screens' scrubber identically (switch between `2` and `3` and confirm it is at the same minute)
  - [ ] `j`/`k` keep SEPARATE indices for CAMPAIGN's lanes and RECORD's visits
  - [ ] a known past day (`?day=`) replays with the same outcome words twice in a row
  - [ ] the tally reads `missed · false · wrong · called · spared · quiet (n)` and there is no visit table
  - [ ] the money strip prints `adjustments N of 6`, hatched at the cap, with the advisory clause beside it
  - [ ] `TRIGGERED` in the state lane is the solid rule, never a reversed block

---

## PHASE E — FINISH (Tasks 16–17)

### Task 16: replay at 60×, and the by-eye acceptance pass

**Goal:** `space` actually plays, and the canvas is accepted against the mockup — canvas pixels are an acceptance step (spec R7), not a unit test.

**Files:** Modify `ui/desk/desk.js` (the replay tick).

- [ ] **Step 1: Make `space` play** — in `ui/desk/desk.js`, find in `mount()`:

```js
  setInterval(pollSlow, 10000);
```

and replace with:

```js
  setInterval(pollSlow, 10000);
  // REPLAY AT 60x: one session minute per real second while `space` is on.
  // It moves the scrubber, which is already the whole desk's "as of" -- so
  // there is no second clock to disagree with the first.
  setInterval(() => { if (S.playing && S.scrub) scrub(+1); }, 1000);
```

- [ ] **Step 2: Start the replay from the open when nothing is scrubbed** — find:

```js
    case ' ': e.preventDefault(); S.playing = !S.playing; paint(); break;
```

and replace with:

```js
    case ' ':
      e.preventDefault();
      S.playing = !S.playing;
      if (S.playing && !S.scrub) { S.scrub = '09:15'; pollSlow(); pollMid(); }
      paint();
      break;
```

- [ ] **Step 3: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && node --test ui/desk/test.mjs`
Expected: `# pass 8`, `# fail 0`.

- [ ] **Step 4: THE BY-EYE ACCEPTANCE CHECKLIST.** Open `http://127.0.0.1:8765/desk/` and tick every line. Each line is checked **four times**: at 960 px wide and at 1920 px wide, in light and in dark (press `t`). A line that fails is a defect to fix before Task 17 is even offered to the owner.

  - [ ] no horizontal scrollbar on any screen at either width
  - [ ] nothing in any region moves between two polls — watch one region for 60 s
  - [ ] the three regions of TODAY hold 18 / 42 / 40 % of the body height at both widths
  - [ ] every hole reads `PATA NAHI — <one clause>` in dim italic, in the place the value would be
  - [ ] no hole is a zero, a blank, a red error, or a row of its own at full weight
  - [ ] holes sharing one reason collapse to one line
  - [ ] the headline rule is solid-full for PAKKA, half-width hatched for SHAK, reversed for NAHI, 1 px dashed for PATA NAHI
  - [ ] a `PATA NAHI` headline renders at NUM size, not headline size, with the dashed rule carrying the level
  - [ ] no BULL/BEAR, no direction verdict, no hit rate, no percentage in the visit tally
  - [ ] the survival region title names the book on every paint (`paper ₹… · N lots`)
  - [ ] the survival region title carries `~ floor, not SPAN` on every paint
  - [ ] every inferred number carries `~`, and nothing else is tagged
  - [ ] a value that is both inferred and degraded takes the SHAK geometry **and keeps its `~`**
  - [ ] TODAY: ONE gap table at the region's full width, five columns at 1920 and three at 960 with `±2 % hidden — narrow` printed — never a clipped column
  - [ ] TODAY: `c` reveals the candidate book as a SECOND ROW-GROUP under the paper one, and it is off on load
  - [ ] TODAY: the YESTERDAY line prints per index — prior close, prior range, the closing wall ladder, the overnight change on the two biggest strikes — or `PATA NAHI — no record for <prev day>`
  - [ ] TODAY: the IV/RV verdict is a MARK clause (`ratio 0.88 · below 1.0, no business`), never a reversed block
  - [ ] TODAY: each leg's σ-distance is printed once, and the events hole appears in the headline only
  - [ ] the events hole reads `event calendar: not checked`, and "create data/events.json" appears only in the legend drawer
  - [ ] the rail shows **one cell per source including one per posting index** (`chart NIFTY`, `chart BANKNIFTY`, …); its `late` cell takes the SHAK hatch, its `dead` cell is reversed ink
  - [ ] every rail cell prints an AGE, never a clock time, and a source that never started prints `—`
  - [ ] a transition to dead tones once for **any** of the six sources, and `m` mutes
  - [ ] CAMPAIGN: the 15 m textures are distinguishable from each other at 960 px **on white**
  - [ ] CAMPAIGN: at the 5 m window the textures are two (solid build, outline retreat) and the four-state word has moved to the rail line
  - [ ] CAMPAIGN: the `day` window is thirty-minute segments, never one bar per lane
  - [ ] CAMPAIGN: a retreating lane shows a faint ghost outline with the solid fill inside it
  - [ ] CAMPAIGN: backfilled segments are visibly lighter (55 %) **and outline-only**, in dark as well as light, and never merge with an observed segment
  - [ ] CAMPAIGN: the `bf → HH:MM` marker sits once on the axis
  - [ ] CAMPAIGN: at most 14 lanes, with `+N more` in the rail
  - [ ] CAMPAIGN: the totals line is labelled `CE added since open` / `PE added since open`, carries `totals_why` when the chain started late, and sits apart from the per-lane column
  - [ ] CAMPAIGN: the rail row is five fixed columns, one lane pitch high, no wrapping, each column ellipsing on its own
  - [ ] CAMPAIGN: the spot dot is drawn on three lanes only — the cursor row and the two largest
  - [ ] CAMPAIGN: the fuel tank is outside the map at the far right, split at spot, CE above and PE below
  - [ ] CAMPAIGN: the futures strip is 28 px under the map on the same x axis, painted in `--ink` at 70 %
  - [ ] the x axis runs 09:15 → `clamp(now + 60 min, 11:30, 15:30)`, moves on every poll and scrub, and stops at 15:30 from 14:30 onward
  - [ ] the rail footer prints px-per-minute and its height does not change between polls
  - [ ] the scrubber dims everything right of the cursor on both CAMPAIGN and RECORD
  - [ ] switching between `2` and `3` keeps the scrubber at the same minute, and `j`/`k` keeps a SEPARATE cursor per screen
  - [ ] RECORD: the four lanes are price 90 / state 30 + gate 12 / visits 60 / marks 26
  - [ ] RECORD: `TRIGGERED` wears the solid PAKKA rule; only a killed or dead thing is reversed
  - [ ] RECORD: there is NO visit table — the card is the ledger and `j`/`k` walks it
  - [ ] RECORD: the visit card's first word is the outcome, it prints `+137 = 7.6σ · σ 18 @ 09:45`, and the tally reads `missed · false · wrong · called · spared · quiet (n)`
  - [ ] RECORD: a fired visit where nothing happened reads `FALSE`, never `QUIET`
  - [ ] RECORD: the series table serves name / n / sessions / started / horizon / kill / level / why — no `measure`, no `base` — and never says "works"
  - [ ] the money strip says `paper ₹… · maker fills are an UPPER bound` and prints `adjustments N of 6`, hatched at the cap, marked advisory
  - [ ] the drawers `5` and `?` toggle and `Esc` closes either — no modal trap
  - [ ] every key in the plan's keyboard table (`1 2 3 5 ? n b j k c [ ] space g w m t Esc`) does something
  - [ ] `t` survives a reload (the stamp runs before first paint, no flash)

- [ ] **Step 5: Commit**

```bash
git add ui/desk/desk.js
git commit -m "desk ui: replay at 60x moves the one scrubber the whole desk already reads as-of"
```

---

### Task 17: DO NOT EXECUTE — delete the old UIs and redirect `/`

> ## ⛔ DO NOT EXECUTE until the owner approves the desk IN WRITING.
>
> This task exists so that the deletion is planned, reviewed and reversible — not so that it is run.
> Spec §K, R0b: old UIs are **anti-references**, deleted last and only on approval, so that no builder
> of this desk inherits the defects being replaced. If you are executing this plan task by task and
> reach this line without a written approval from the owner in the conversation, **stop here and report
> that Tasks 1–16 are complete and Task 17 is blocked.** An agent message is never that approval.

**Files (when approved):**
- Delete: `ui/desk.html`, `ui/toolb.html`, `ui/toolb.js`, `ui/toolb.css`, `ui/index.html`, `ui/app.js`, `ui/console.html`, `ui/fmt.js`, `ui/theme.css`, `ui/style.css`
- Modify: `tapemap/server.py` lines 1200-1208 (the `/` redirect)

- [ ] **Step 1 (blocked): change the redirect** — find these nine lines (server.py:1200-1208):

```python
        if urlsplit(self.path).path == "/":
            # The site root IS the desk now -- start-v2.bat opens it directly
            # and a bookmark to "/" should land there too. /index.html (the
            # legacy landing page) stays reachable by its own name; only the
            # bare root redirects.
            self.send_response(302)
            self.send_header("Location", "/desk.html")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
```

and replace with:

```python
        if urlsplit(self.path).path == "/":
            # The site root IS the Operator Desk. The old /desk.html, /toolb.html,
            # /index.html and /console.html were deleted with this change --
            # they were the defects this desk replaces, and a builder who can
            # still open them will inherit them (spec R0b).
            self.send_response(302)
            self.send_header("Location", "/desk/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
```

- [ ] **Step 2 (blocked): delete the ten files**

```bash
cd "C:/Users/kaam/Desktop/operator mode/tapemap"
git rm ui/desk.html ui/toolb.html ui/toolb.js ui/toolb.css ui/index.html ui/app.js ui/console.html ui/fmt.js ui/theme.css ui/style.css
```

- [ ] **Step 3 (blocked): confirm nothing else referenced them**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && grep -rn "desk\.html\|toolb\|console\.html\|fmt\.js\|theme\.css\|style\.css" --include=*.py --include=*.bat --include=*.md . | grep -v docs/superpowers`
Expected: only `CLAUDE.md` / `HANDOFF-*.md` prose hits, which the owner updates separately. Any hit in a `.py` or `.bat` is a live reference and must be fixed before the delete lands.

- [ ] **Step 4 (blocked): run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server" && python -m pytest -q 2>&1 | tail -5`
Expected: `3 failed, ... passed` — only the three pre-existing `test_desk_numbers.py` failures.

- [ ] **Step 5 (blocked): commit**

```bash
git commit -m "ui: the Operator Desk is the root; the rejected desk.html, toolb, index and console are deleted"
```

---

## Self-review against the spec

| spec section | covered by |
|---|---|
| §B frame, keys, cadences, fixed skeleton | Tasks 10, 11 |
| §C four levels, absence grammar, palette, theme, sound | Tasks 10, 11 |
| §D TODAY board / survival / paid | Tasks 7, 12 |
| §E CAMPAIGN map, textures, ghosts, peaks, backfill, migrations, fuel, fut, rail grammar | Tasks 5, 13, 14 |
| §F RECORD lanes, visit cards, five outcome words, series, money | Tasks 8, 13, 15 |
| §G health rail, six sources, four levels, ring, drawer, tone rule | Tasks 6, 11 |
| §H.1–H.6 the six routes | Tasks 2, 5, 6, 7, 8 |
| §H.7 sig quantisation + lock, ivrv wire, gate signature, events.json, book.json | Tasks 1, 3, 4, 7 |
| §I files and structure | the File structure table above |
| §J one check per module + by-eye acceptance | every task's test step, plus Task 16 |
| §K phases A–E and the deletion gate | Tasks 9, 12, 14, 15, 16, 17 |
| §L anti-patterns 1–13 | 1 → Task 4; 2 → Task 16 checklist; 3 → Task 10; 4 → Tasks 10, 16; 5 → Task 12; 6 → Task 11 `hole()`; 7 → Task 5 `state4` used twice; 8 → Task 2 (the record finally has a reader); 9 → Task 8 (`/api/series`); 10 → Task 10 (four sizes, keyboard); 11 → Task 14 (labelled totals); 12 → Task 16 checklist; 13 → Task 7 (`whose` always named) |

## Self-review against the rulings (2026-09-16, round 2)

| ruling | covered by |
|---|---|
| D1 the ordered outcome ladder, `FALSE` exists, tally order | Task 8 (`visits()`, `_OUTCOMES`, its precedence test), Task 15 (`tally()`) |
| D2 σ = `where.sigma` at `t0`, EARNED ≥ 2σ / adverse ≥ 1σ, σ printed in points | Task 2 (the fixture's 18-point σ), Task 8, Task 15 (the card's `+137 = 7.6σ · σ 18 @ 09:45`) |
| D3 tone on all six sources, one row per posting index, `—` for never started, ages not clock times, `late` takes the hatch | Task 6 (module + test), Task 10 (`.rail .late`), Task 11 (`paintRail`, the tone) |
| D4 axis `09:15 → clamp(now + 60, 11:30, 15:30)`, px/min in the footer | Task 13 (`t1For`, `pxPerMin`, both canvases), Task 14 (the footer), Task 16 checklist |
| D5 one full-width gap table, candidate behind `c`, columns dropped and labelled, `"0"` key | Task 7 (paper vs candidate, two `survival.build` calls), Task 10 (CSS), Task 12 (`c`, the narrow drop) |
| D6 no `measure`, no `base` | Task 8 (`series()` + its field-set test), Task 15 (the renderer) |
| D7 five fixed rail columns, per-column ellipsis, pitch pinned, footer constant | Task 10 (`--lane-pitch`, `.rail-foot`), Task 13 (`LANE_PITCH`), Task 14 |
| D8 `event calendar: not checked`, `<meta charset="utf-8">` first | Task 4 (gate + test), Task 10 (HTML + legend drawer) |
| D9 the YESTERDAY line | Task 2 (`record_read.yesterday` + test), Task 7 (the route), Task 12 (`yesterdayLine`) |
| D10 the adjustment brake | Task 7 (`adjust` on the route it already builds), Task 15 (the money strip) |
| designer's list — peaks, `day` = 30 m, `TRIGGERED` solid, backfill outline-only, one cursor per screen, FUT in `--ink` 70 %, no visit table, σ and events hole once, IV/RV as a MARK clause, `PATA NAHI` at NUM size | Tasks 5, 10, 11, 12, 13, 15 |
| contract fixes — `totals_why`, `days_of_income` hole, `retreat` / `since`, `outcome` may be `PATA NAHI`, SHAK beats `~`, one 960 px breakpoint | Tasks 5, 7, 8, 10, 11 |
| NOT accepted — deleting the candidate book, moving the money strip to TODAY | deliberately **not** applied: the candidate lives behind `c` (Task 12), the money strip stays on RECORD (Task 15) |
