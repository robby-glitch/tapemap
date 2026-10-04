"""sides_log.py -- the sides read's I/O: its forward log, and the saved-chain reads it needs.

THE LOG, data/sides/sides_YYYY-MM-DD.jsonl (Fable §5's field spec, rev sides-2):
  * one kind:"slot" row per index per CLOSED 5-minute slot -- every slot, not only POWER --
    written ONCE, with `src` / `grid_src` (live, or rebuilt after a restart) and empty
    `her_read` / `leg_traded` fields for her;
  * one kind:"outcome" row per slot, written ONCE by the live process when t+30 has closed
    (f15 f30 mfe30 mae30 outcome_src), never recomputed from a re-cut cache later.
A restart re-reads the day's file first, so nothing already written is written again.

WRITTEN ONLY IN MARKET HOURS, AND ONLY FOR TODAY'S OWN SESSION. On 1 Oct 98 duplicate
rows landed in trigger_log at midnight because a process past the date line wrote the
previous session under the new date. So `append` writes nothing:
  * before 09:15:00 or from 15:31:00, or on a Saturday or Sunday;
  * when the rows' session day is not the wall clock's date -- the caller passes the grid's
    own day (the chain payload's build date), never the wall date.

THE SAVED CHAIN (read-only): `load_session` parses a day's data/chain file into the grid,
the open OI and the snapshot at each 5-minute mark (the previous session's scale is read
from it); `BookTail` follows today's file incrementally for the forced chip, so a 13 MB day
is never re-read per tick (the 2026-09-18 wedge).

Display [I], gates nothing. The rows are raw material for forward reading, never a score.
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
import threading

DIR = os.path.join("data", "sides")
OPEN, LAST = "09:15", "15:30"          # writes allowed while HH:MM is in [OPEN, LAST]
_LOCK = threading.Lock()
_SEEN = {}                              # (path, idx, kind) -> set of slot times already in the file


def path_for(day, d=None, stem="sides"):
    return os.path.join(d or DIR, f"{stem}_{day}.jsonl")


def _seen(path, idx, kind):
    key = (path, idx, kind)
    if key not in _SEEN:
        s = set()
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if r.get("idx") == idx and r.get("kind", "slot") == kind and isinstance(r.get("t"), str):
                        s.add(r.get("key") or r["t"])
        except OSError:
            pass
        _SEEN[key] = s
    return _SEEN[key]


def unwritten(day, idx, kind, times, d=None, stem="sides"):
    """The subset of `times` with no `kind` row for `idx` in the day's file yet."""
    with _LOCK:
        seen = _seen(path_for(day, d, stem), idx, kind)
        return {t for t in times if t not in seen}


def may_write(now, day):
    """(ok, why): the market-hours and same-session guard, on its own so it can be tested."""
    hm = now.strftime("%H:%M")
    if now.weekday() >= 5:
        return False, "weekend"
    if not (OPEN <= hm <= LAST):
        return False, f"outside market hours ({hm})"
    if day != now.strftime("%Y-%m-%d"):
        return False, f"the rows are from {day}, not today"
    return True, None


def append(day, idx, rows, now, d=None, stem="sides"):
    """Append each row of `idx` (kind "slot" by default) not yet in the day's file. A row is written
    only once its slot has closed (t < now); a row with its own `key` is once-only on that key.
    `d` and `stem` point it at another recorder's file (trap_log reuses this guard). -> rows written."""
    ok, _ = may_write(now, day)
    if not ok:
        return 0
    hm = now.strftime("%H:%M")
    path = path_for(day, d, stem)
    stamp = now.isoformat(timespec="seconds")
    out = 0
    with _LOCK:
        for r in rows or ():
            if not isinstance(r, dict) or not isinstance(r.get("t"), str) or r["t"] >= hm:
                continue
            kind = r.get("kind", "slot")
            seen = _seen(path, idx, kind)
            rk = r.get("key") or r["t"]          # a row's once-only key: its slot time, or its own `key`
            if rk in seen:
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"day": day, "idx": idx, **r, "kind": kind, "logged_at": stamp}, default=str) + "\n")
            seen.add(rk)
            out += 1
    return out


# ---- the saved chain -----------------------------------------------------------------------------------
def _leg(x):
    return (x.get("ltp"), x.get("avg"), x.get("iv"), x.get("vol"))


def take(snap, minutes, opens, book, info=None):
    """Fold one saved chain snapshot into the grid (the last snapshot of a minute wins, as
    ChainState.update writes it), the open OI (oi - oi_chg) and the snapshot at each 5-min mark.
    `info` collects the option expiry the poller stamped on the snapshot (files since late Sep)."""
    if info is not None and snap.get("expiry"):
        info["expiry"] = snap["expiry"]
    ts = (snap.get("ts") or "")[:5]
    if not re.match(r"^\d\d:\d\d$", ts) or not (OPEN <= ts <= LAST):
        return
    cells, legs = {}, {}
    for r in snap.get("strikes") or ():
        try:
            k = float(r["k"])
        except (KeyError, TypeError, ValueError):
            continue
        ce, pe = r.get("ce") or {}, r.get("pe") or {}
        cells[k] = ((ce.get("oi_chg") or 0.0), (pe.get("oi_chg") or 0.0))
        for side, x in (("ce", ce), ("pe", pe)):
            if isinstance(x.get("oi"), (int, float)):
                opens[(k, side)] = float(x["oi"]) - float(x.get("oi_chg") or 0)
        legs[k] = {"ce": _leg(ce), "pe": _leg(pe)}
    minutes[ts] = {"spot": snap.get("spot"), "k": cells}
    if int(ts[3:5]) % 5 == 0:
        book[ts] = legs


def load_session(path, info=None):
    """(minutes, opens, book) of one saved chain day file (.jsonl or .jsonl.gz); `info` gets its
    "expiry" when the file carries one."""
    minutes, opens, book = {}, {}, {}
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                take(json.loads(line), minutes, opens, book, info)
            except ValueError:
                continue
    return minutes, opens, book


def prev_session_path(chain_dir, idx, day):
    """The latest saved chain day for `idx` before `day` (weekends and holidays skipped), or None."""
    best = None
    for p in glob.glob(os.path.join(str(chain_dir), f"chain_{idx}_*.jsonl*")):
        m = re.search(r"_(\d{4}-\d{2}-\d{2})\.jsonl(\.gz)?$", p)
        if m and m.group(1) < day and (best is None or m.group(1) > best[0]):
            best = (m.group(1), p)
    return best


class BookTail:
    """Today's saved chain file, followed incrementally: only new bytes are parsed each call."""

    def __init__(self, path):
        self.path, self.off, self.rest = path, 0, b""
        self.minutes, self.opens, self.book = {}, {}, {}

    def read(self):
        try:
            with open(self.path, "rb") as f:
                f.seek(self.off)
                chunk = f.read()
        except OSError:
            return self.book
        self.off += len(chunk)
        lines = (self.rest + chunk).split(b"\n")
        self.rest = lines.pop()
        for ln in lines:
            try:
                take(json.loads(ln), self.minutes, self.opens, self.book)
            except ValueError:
                continue
        return self.book
