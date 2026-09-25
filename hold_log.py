"""hold_log.py -- the hold window's two forward logs (docs/hold/PREREG-merged.md §8).

  data/hold/hold_<day>.jsonl  one row per finished minute per trade, entry to
                              15:29, `after_exit` flagged, `src` marked | import
  data/hold/side_<day>.jsonl  one row per finished minute per index, flat or in a
                              trade, plus one `stamp_track` row per side stamp
                              once that strike's next 30 finished minutes are in
  data/hold/check_<day>.jsonl one row per VALIDATE press (VALIDATE-PREREG rev 2 §3),
                              plus one `check_outcome` row per (idx, t, d) once
                              its 30 finished minutes are in

§7 and §10.6 are answered from these rows and nowhere else, so a row is written
ONCE and never rewritten -- the calls_log discipline. A restart reads what is on
disk and appends only what is missing (the facts are exact, so a row written
after a restart is the row that would have been written live). The caller gates
the live writer on chain_live.in_session; the close-time import writes through
the same door. gzipped after a week by daylog.py like every other daily record.
"""
import json
import os
import threading

DIR = os.path.join("data", "hold")
_lock = threading.Lock()
_seen = {}                   # {(kind, day): {key}} -- that file, read once


def path(kind: str, day: str) -> str:
    return os.path.join(DIR, f"{kind}_{day}.jsonl")


def key(kind: str, r: dict):
    if kind == "hold":                       # a minute row and a rung_touch row at the same t are two rows
        return r.get("trade_id"), r.get("t"), r.get("kind") or "minute"
    if kind == "check":
        if r.get("kind") == "check_outcome":    # VALIDATE rev 2 §3 (M1b): a long CE and a long PE at one minute, two rows
            return r.get("idx"), r.get("t"), r.get("d"), "outcome"
        return r.get("idx"), r.get("t"), r.get("k"), r.get("side"), r.get("role")   # one press per minute per contract
    return r.get("idx"), r.get("t"), r.get("kind") or "minute"


def seen(kind: str, day: str) -> set:
    """The keys already on disk for (kind, day). Call under _lock."""
    s = _seen.get((kind, day))
    if s is None:
        s = set()
        try:
            with open(path(kind, day), encoding="utf-8") as f:
                for line in f:
                    try:
                        s.add(key(kind, json.loads(line)))
                    except (ValueError, TypeError, AttributeError):
                        continue
        except OSError:
            pass
        for k in [k for k in _seen if k[1] != day]:
            del _seen[k]
        _seen[(kind, day)] = s
    return s


def read(kind: str, day: str) -> list:
    """Every row on disk for (kind, day); a torn last line is skipped. The check file is a handful of presses a
    day -- the outcome writer (VALIDATE rev 2 §3) reads it back each minute."""
    out = []
    try:
        with open(path(kind, day), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def has(kind: str, day: str, k) -> bool:
    with _lock:
        return k in seen(kind, day)


def append(kind: str, day: str, rows) -> int:
    """Write each row whose key is not on disk yet. Returns how many were written."""
    with _lock:              # the whole read-check-write: a restart's threads cannot race
        s = seen(kind, day)
        new = [r for r in rows if key(kind, r) not in s]
        if not new:
            return 0
        os.makedirs(DIR, exist_ok=True)
        with open(path(kind, day), "a", encoding="utf-8") as f:
            for r in new:
                f.write(json.dumps(r, default=str) + "\n")
                s.add(key(kind, r))
        return len(new)
