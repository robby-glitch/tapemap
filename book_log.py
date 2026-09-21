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
        """Senses loop. Writes what the deque holds; returns the rows written.

        A failed write loses those rows and says so on `failed`; it never
        advances the record past them -- `_last_t` (and `book_from`) move only
        after a batch's write actually lands, to that batch's own last `t`, so
        a later flush's filter is checked against what was truly written, not
        against rows the write never landed."""
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
            by.setdefault(idx, []).append(row)
        out: List[Tuple[str, dict]] = []
        for idx, rs in by.items():
            p = day_path(day, idx)
            try:
                os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
                with open(p, "a", encoding="utf-8") as f:
                    f.write("".join(json.dumps(r) + "\n" for r in rs))
            except Exception:                  # never take the tape down; the rows
                                                # are gone from the deque regardless,
                                                # but `_last_t` does not move past
                                                # what was never actually written
                failed += len(rs)
                continue
            self.written += len(rs)
            self._last_t[idx] = rs[-1]["t"]
            self.book_from.setdefault(idx, _hms(rs[0]["t"]))
            out.extend((idx, r) for r in rs)
        return out
