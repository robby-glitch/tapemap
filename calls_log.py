"""calls_log.py -- the grounded calls, kept: one row per index per engine bar.

grounds.py's kill condition ("after ~30 sessions, if CONTRADICTED calls do not
resolve against their own claim more often than BACKED ones, delete it") had
nothing to be judged on: /api/calls computed each call per request and kept
none. The operator, 2026-09-24: "Log the checked calls" -- one small daily file,
09:15-15:30 only (the caller gates on chain_live.in_session), gzipped after a
week by daylog.py like every other daily record.

A row is the call AS FIRST SHOWN on its bar: written the first time a bar's
`t` is seen, never rewritten, so it is what the face said then, not a later
re-reading. Forward only; a restart does not rebuild the bars it missed.
"""
import json
import os
import threading

DIR = os.path.join("data", "calls")
_lock = threading.Lock()     # one refresh thread per index writes here
_seen = {}                   # {day: {(idx, t)}} -- this day's file, read once


def path(day: str) -> str:
    return os.path.join(DIR, f"calls_{day}.jsonl")


def append(day: str, idx: str, out: dict, at: float) -> bool:
    """Write `out` (an /api/calls reply) once per (day, idx, t). True if written."""
    t = out.get("t") if isinstance(out, dict) else None
    if not out or not out.get("ok") or t is None:
        return False
    with _lock:              # the whole read-check-write, so a restart's threads cannot race
        seen = _seen.get(day)
        if seen is None:
            seen = set()
            try:
                with open(path(day), encoding="utf-8") as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                            seen.add((r["idx"], r["t"]))
                        except (ValueError, KeyError, TypeError):
                            continue
            except OSError:
                pass
            _seen.clear()
            _seen[day] = seen
        if (idx, t) in seen:
            return False
        os.makedirs(DIR, exist_ok=True)
        with open(path(day), "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": day, "at": round(at, 1), **out}, default=str) + "\n")
        seen.add((idx, t))
        return True
