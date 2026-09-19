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
