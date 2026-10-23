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
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

DIR = os.path.join("data", "tape")
failed = 0

_seen_bars: Dict[Tuple[str, str], Set[int]] = {}
_seen_marks: Dict[Tuple[str, str], Set[tuple]] = {}

_BAR_KEYS = ("t", "o", "h", "l", "c", "vol", "buy", "sell", "delta", "oi", "fromTicks", "partial")   # partial: v2.2 D4, a bar the page joined late


def day_path(day: str, idx: str) -> str:
    return os.path.join(DIR, f"tape_{idx}_{day}.jsonl")


def marks_path(day: str, idx: str) -> str:
    return os.path.join(DIR, f"ofd_marks_{idx}_{day}.jsonl")


def ux_path(day: str, idx: str) -> str:
    """The Upstox ladder record beside the tape (ux_log.day_path reads it from here)."""
    return os.path.join(DIR, f"ux_{idx}_{day}.jsonl")


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


def prior_days(day: str, idx: str, n: int = 5, after: Optional[str] = None) -> List[str]:
    """Days with a bar file before `day`, newest first, at most n. `after` (YYYY-MM-DD) also
    drops the days on or before it -- the expired front future's expiry (pro-tool P1-03)."""
    pre, suf = f"tape_{idx}_", ".jsonl"
    try:
        names = os.listdir(DIR)
    except OSError:
        return []
    days = [nm[len(pre):-len(suf)] for nm in names if nm.startswith(pre) and nm.endswith(suf)]
    return sorted((d for d in days if d < day and (after is None or d > after)), reverse=True)[:n]


def _ux_ik(day: str, idx: str) -> Optional[str]:
    """The contract key the day's ux record was measured on (P1-04's stamp), or None."""
    return next((r.get("ik") for r in _read(ux_path(day, idx)) if r.get("ik")), None)


def prior_pool(day: str, idx: str, n: int = 5, after: Optional[str] = None,
               ik: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
    """THE ROLL (P1-03): the prior days whose prices are this contract's, and why when none are.
    Sep expired 29 Sep and 30 Sep is the Oct contract, off by the calendar spread: a day on or
    before `after` is cut. Once the dump no longer lists the expired future (`after` None), a
    day is kept only when its ux record carries today's `ik`; one recorded before the stamp
    existed, or on another contract, is cut and named."""
    cand = prior_days(day, idx, n)
    days = prior_days(day, idx, n, after) if after else cand
    why = None
    if after and len(days) < len(cand):
        e = date.fromisoformat(after)
        why = f"the {e:%b} future expired {e.day} {e:%b}; earlier days are another contract"
    if ik:
        keep, other, unstamped = [], [], []
        for d in days:
            k = _ux_ik(d, idx)
            (keep if k == ik else other if k else unstamped).append(d)
        if keep != days:
            why = (f"earlier days are another contract ({_ux_ik(other[0], idx)}, today {ik})" if other
                   else "earlier days' contract was not recorded (before the contract stamp)")
        days = keep
    return days, why


def _mark_key(m: dict) -> tuple:
    return (m.get("t"), m.get("kind"), m.get("p"), m.get("side"))


def bar_t(b) -> Optional[int]:
    """The bar's `t` as an int, or None when the entry is not a bar at all --
    a non-dict, no `t`, or a `t` that is not a number. A corrupt entry in a
    POST (or a corrupt row already in the file) is SKIPPED: raising here would
    take the whole frame POST down with it. Shared by the writer and by
    server._tape_reply, so the record and the wire hold the same population.
    Only int/float: `bool` is a `int` subclass and a numeric string would
    otherwise sail through `int()` -- neither is a bar timestamp."""
    if not isinstance(b, dict):
        return None
    t = b.get("t")
    if isinstance(t, bool) or not isinstance(t, (int, float)):
        return None
    try:
        return int(t)
    except (TypeError, ValueError):
        return None


def keep_mark(m) -> bool:
    """The ofd-mark filter, shared by the writer and the live GET. An empty
    `kind` is not a kind: it would be dropped by one path and kept by the
    other, which is two populations wearing one name."""
    return isinstance(m, dict) and m.get("t") is not None and bool(m.get("kind"))


def _seed(day: str, idx: str) -> None:
    key = (day, idx)
    if key not in _seen_bars:
        _seen_bars[key] = {t for t in (bar_t(r) for r in read_bars(day, idx)) if t is not None}
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
    # ik: null on purpose (P1-04): these are GoCharting's continuous NIFTY-I bars; stamping Upstox's
    # contract on them would be a measured claim the source never made. The why says so on every row.
    sym = str(doc.get("session") or "").split("|")[0] or f"{idx}-I"
    meta = {"rowSize": doc.get("rowSize"), "rowAnchor": doc.get("rowAnchor", 0), "lot": doc.get("lot"),
            "session": doc.get("session"), "idx": idx, "day": day,
            "ik": None, "ik_why": f"GoCharting continuous {sym}; contract not declared"}
    bars = []
    for b in doc.get("closed") or []:
        t = bar_t(b)
        if t is None or t in seen_b:
            continue
        row = {k: b.get(k) for k in _BAR_KEYS}
        row["ladder"] = b.get("ladder") if isinstance(b.get("ladder"), list) else None
        row.update(meta)
        bars.append(row)
    marks = []
    for m in doc.get("events") or []:
        if not keep_mark(m):
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
            seen_b.update(bar_t(r) for r in rows)
        out[key] = len(rows)
    return out


# THE V2 PAGE'S MARK LOG (extension v2 spec §3.8): doc.marks2, one row per drawn or ghost mark per status change,
# written once per (id, status, tier) into its own file -- a third population beside the bars and the old marks.
_seen_marks2: Dict[Tuple[str, str], Set[tuple]] = {}
M2_KEYS = ("id", "t", "kind", "name", "p", "lots", "trapped", "winner", "rank", "n", "prov", "ring", "ring_px",
           "sigma", "flow", "flow_dir", "tier", "status", "status_t", "break_px", "build", "row", "merged", "src",
           "khel", "hold", "first")            # v2.3: the forward record -- the KHEL it was born under, the 60-min hold, 0.5U-first
M2_CAP = 2000                                  # rows read per post: v2.1 logs EVERY mark the board and decoder produce


def marks2_path(day: str, idx: str) -> str:
    return os.path.join(DIR, f"ofd_marks2_{idx}_{day}.jsonl")


def _m2_key(m: dict) -> tuple:
    # v2.3: a row is written again when its forward record resolves (hold / first move on from "open"); an older page sends
    # neither field, so its rows key exactly as before
    return (str(m.get("id")), str(m.get("status")), str(m.get("tier")), str(m.get("hold")), str(m.get("first")), str(m.get("khel")))


def append_marks2(doc: dict, day: str, idx: str) -> int:
    """Write the post's new v2 mark rows (whitelisted fields + day/idx). Returns how many landed."""
    global failed
    rows = doc.get("marks2")
    if not isinstance(rows, list) or not rows:
        return 0
    key = (day, idx)
    if key not in _seen_marks2:                # anytime-start: what the file already holds is not written again
        _seen_marks2[key] = {_m2_key(r) for r in _read(marks2_path(day, idx))}
    seen = _seen_marks2[key]
    out = []
    for m in rows[:M2_CAP]:
        if not isinstance(m, dict) or m.get("id") is None:
            continue
        k = _m2_key(m)
        if k in seen:
            continue
        seen.add(k)
        out.append(dict({f: m[f] for f in M2_KEYS if f in m}, day=day, idx=idx))
    if not out:
        return 0
    try:
        _write_lines(marks2_path(day, idx), out)
    except Exception:                          # never take the tape down
        failed += len(out)
        for r in out:
            seen.discard(_m2_key(r))
        return 0
    return len(out)
