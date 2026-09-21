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

_LOCK guards the ladder between the senses thread's step and the request
thread's forming() copy; it is never held across disk.
"""
from __future__ import annotations

import copy
import json
import os
import threading
from collections import deque
from typing import Dict, List, Optional, Tuple

import book_log
import ladder
import tape_log

failed = 0
_STATE: Dict[str, dict] = {}          # idx -> {"day", "ladder", "bars", "fills", "written", "seen"}
_LOCK = threading.Lock()


def day_path(day: str, idx: str) -> str:
    return os.path.join(tape_log.DIR, f"ux_{idx}_{day}.jsonl")


def read_bars(day: str, idx: str) -> List[dict]:
    return tape_log._read(day_path(day, idx))


def _write_lines(path: str, rows: List[dict]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))


def state(idx: str, day: str, lot: Optional[int] = None, tick: Optional[float] = None,
          lot_src: Optional[str] = None) -> dict:
    """The per-index state for `day`; a new day replaces yesterday's ladder.
    `lot`/`tick`/`lot_src` are used only when the state is CREATED."""
    st = _STATE.get(idx)
    if st is None or st["day"] != day:
        bars = read_bars(day, idx)
        st = _STATE[idx] = {"day": day,
                            "ladder": ladder.Ladder(lot=lot, tick=tick, idx=idx, day=day, lot_src=lot_src),
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
    """Feed the rows a drain produced. Returns (idx, closed bar, the fills of the frames that went into it).

    `lot`/`tick` are used only when an index's state is CREATED; the server
    calls `state(idx, day, lot, tick)` per index first, then this without them.
    `observer(idx, row, fills)`, when given, is called once per row AFTER the
    ladder stepped it -- how runs.py and impact.py see every frame (Task 12)."""
    out: List[Tuple[str, dict, List[dict]]] = []
    fills_by: Dict[str, List[dict]] = {}
    for idx, row in rows:
        st = state(idx, day, lot, tick)
        with _LOCK:
            closed, fills = st["ladder"].step(row)
        if closed is not None and _land(st, idx, day, closed):
            out.append((idx, closed, fills_by.pop(idx, [])))
        if fills:
            st["fills"].extend(fills)
            fills_by.setdefault(idx, []).extend(fills)
        if observer is not None:
            observer(idx, row, fills)
    return out


def forming(idx: str, day: str) -> Optional[dict]:
    st = _STATE.get(idx)
    if st is None or st["day"] != day or st["ladder"].acc is None:
        return None
    with _LOCK:
        lad = copy.deepcopy(st["ladder"])
    return lad.close_open()


def rebuild(day: str, idx: str, lot: Optional[int] = None, tick: Optional[float] = None,
            lot_src: Optional[str] = None, observer=None, close_last: bool = True) -> int:
    """Stream today's book file; write every closed bin the file holds that the
    ux file lacks. `close_last` also closes the bin the file ends inside --
    right for `tools/gate_report.py`, which runs from files alone after close,
    but wrong for the live server: on a mid-day restart that bin is the
    CURRENT one, so closing it here would make the live stream's first frame
    in it look like a fresh bar and lose the rest to `_land`'s write-once
    guard -- `server._ux_drain` passes `close_last=False` and leaves it for
    the stream to finish, `forming()` serving it meanwhile. Returns bars
    written. `observer` as in `on_frames`, so runs/impact warm up on a restart
    too."""
    n = 0
    st = state(idx, day, lot, tick, lot_src)
    lad = st["ladder"]
    any_row = False
    for row in book_log.read_rows(day, idx):
        any_row = True
        with _LOCK:
            closed, fills = lad.step(row)
        st["fills"].extend(fills)
        if observer is not None:
            observer(idx, row, fills)
        if closed is not None and _land(st, idx, day, closed):
            n += 1
    if any_row and close_last:
        with _LOCK:
            last = lad.close_open()
        if last is not None and _land(st, idx, day, last):
            n += 1
    return n
