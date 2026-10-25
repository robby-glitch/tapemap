"""The day's RAM-only series, written down so the evening can see the morning.

WHY THIS EXISTS. Most of what this stack learns in a session already survives a
restart, because it was written to a forward log as it happened: the trigger
record, the surface fits, the desk verdict transitions, the war map's sequence
rows, the paper book, the toxicity buckets. One thing was not. The buyer's-tax
day trace (`server._SENSES["drag_day"]`) is assembled at chain pace and lives
only in the process, so a post-close restart erased the whole day and the
screen went blank -- the operator, verbatim: *"7:30pm ko bhi kholu to dekh
paaoun kya hua"* and *"abhi to ui he khali ho jaata"*.

WHAT THIS IS NOT. It is not a backfill and nothing here is reconstructed. Every
row was OBSERVED by the process that wrote it; this only stops the observation
from dying with the process. That distinction is why these rows carry no
`backfill` tag: tagging them would say the tool guessed, and it did not. The
one thing a reader is told is that the trace was read back from disk rather
than gathered by the running process, so "since start" can be read correctly.

SAME DAY ONLY, and that is deliberate rather than lazy. `load` refuses a file
whose `day` is not the day asked for, so tomorrow morning starts cold instead
of opening on yesterday's tax as if it were today's -- the same same-day-only
rule `vpin.Gauge.seed` states at length, and for the same reason: a stale
series that renders is worse than an empty one that says so.

ATOMIC REWRITE, not an append. The whole ring is the value, so a torn write
would corrupt the file rather than truncate it; `os.replace` on a sibling temp
file makes a half-written save impossible to read back. Same discipline as
`trader.py`'s `state.json`.

`DIR` is read at CALL time, never bound at import, so `server._isolate_mock_
writers` can redirect it -- the 2026-08-24 replay leak rule: a --mock-chain
replay must never share a path with the record it exists to rehearse for.

Pure stdlib, no imports from the operator layer: like `desk_log.py`, this only
formats and stores what the caller already computed.
"""

import json
import logging
import os
import tempfile
import threading
import time

DIR = os.path.join("data", "day_state")
log = logging.getLogger("tapemap")
_LOCK = threading.Lock()   # ponytail: one lock for every day file -- six server threads save (25 Oct review D2)


def path_for(day, dir_=None):
    """The one file for `day`. Per-day, so nothing has to be pruned or
    filtered on read -- a stale file simply never matches a `load`."""
    return os.path.join(dir_ or DIR, f"day_{day}.json")


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
