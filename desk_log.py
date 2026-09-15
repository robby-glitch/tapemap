"""desk_log.py -- the record a desk keeps: fitted coefficients, and verdict
transitions. Nothing else.

WHAT GOES HERE, AND WHAT NEVER DOES. Two files:

  data/surface/surface_<day>.jsonl   one line per successful fit, at chain
                                      pace (the trigger is server.py's own
                                      "new chain payload" detection -- see
                                      `_senses_loop`). {ts, idx, a, b, c,
                                      rmse, f_src, expiry, n_points}.

  data/desk_log.jsonl                TRANSITIONS ONLY -- a line is written
                                      only when gear, conviction or the desk's
                                      best structure actually CHANGES from the
                                      previous reading. {ts, idx, field, from,
                                      to, detail}. This is the ledger
                                      `direction.py`'s own declared 30-session
                                      kill condition needs to be judged
                                      against; today it has nothing.

A RESTART IS NOT A TRANSITION, AND MUST NOT LOOK LIKE ONE. The caller's
in-memory previous-state cache (`desk_state` in server.py's `_senses_loop`)
resets to empty on every process start, which the server is bounced
routinely. Without a marker, the first reading for an index after a restart
diffs against `{}` and every field reports "changed from None" -- a row with
the identical shape as a genuine mid-session change, silently inflating the
30-session ledger with restart noise it was never meant to count. The fix:
the caller passes `baseline=True` to `log_transition` for the first reading
of an index in a process (and only then); that row carries one extra key,
`"baseline": true`, alongside the usual six. Every later, genuinely-observed
change -- including a None -> value change on a field that simply had not
moved yet -- is a plain transition with no `baseline` key at all. A reader
that wants the true ledger filters `baseline` rows out; a reader that wants
"what does this index look like right now" keeps them.

NEVER A HIT RATE, NEVER AN OUTCOME. A transition says the state changed, not
whether it paid. Pooling this against `data/trigger_log.jsonl` or scoring it
here would be exactly the mistake that file's own quarantine discipline
exists to prevent -- this module never opens that path and never will.

A FAILED FIT LOGS NOTHING. `log_surface` is only called with real fitted
coefficients; a caller holding a fit that did not converge simply does not
call it. No fabricated `None`-filled row, no invented zero -- silence is the
honest answer to "there was nothing to fit" (constraint: absence gets a
reason, and here the reason is "no line" itself, which is what the surface
module's own `fit.ok` already gates on).

FAIL-SOFT DISK WRITES, MIRRORING `senses.py`. Opened per call in append mode,
directory created on demand, any exception swallowed. A log line that cannot
be written must never take the loop that feeds it down with it.

THE MARKET-HOURS GATE IS AT THE CALL SITE, NOT BAKED INTO THE CLOCK. Both
writers refuse outside 09:15-15:30 IST Mon-Fri -- constraint 6 -- but `now`
is a parameter, never read from the wall clock internally when supplied, so a
test (or a --mock-chain run exercising this at 02:00) can hand in a fixed
in-hours timestamp and drive the real write path rather than a special-cased
stub. The machine's local clock IS IST (HANDOFF-DESK.md Sec 7) -- no tz
conversion happens here, matching every other module in this stack.

Pure stdlib, no operator-layer imports (constraint 4): this module only
formats and writes what its caller already computed.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

SURF_DIR = os.path.join("data", "surface")
DESK_LOG_PATH = os.path.join("data", "desk_log.jsonl")

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)

# The three fields a transition can fire on, in the order a reader expects
# them named -- gear (the regime), conviction (the direction view's
# strength), deployable (the desk's own best-structure name, or None).
TRANSITION_FIELDS = ("gear", "conviction", "deployable", "oi_dir")


def market_hours(now: Optional[datetime] = None) -> bool:
    """Mon-Fri, 09:15-15:30, off the machine's own clock (which IS IST)."""
    now = now or datetime.now()
    if now.weekday() >= 5:                     # Sat=5, Sun=6
        return False
    hm = (now.hour, now.minute)
    return MARKET_OPEN <= hm <= MARKET_CLOSE


def _append(path: str, row: dict) -> bool:
    """Fail-soft append -- one JSON line, never raises."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return True
    except Exception:
        return False


def surface_path(day: Optional[str] = None, now: Optional[datetime] = None) -> str:
    day = day or (now or datetime.now()).strftime("%Y-%m-%d")
    return os.path.join(SURF_DIR, f"surface_{day}.jsonl")


def log_surface(idx: str, a, b, c, rmse, f_src: str, expiry: str, n_points: int,
                *, now: Optional[datetime] = None, day: Optional[str] = None,
                path: Optional[str] = None) -> bool:
    """One line for a SUCCESSFUL fit. Never called on a failed one -- see
    the module docstring. `path` overrides the computed day-file location --
    a test seam, mirroring `senses.Senses(path=...)` -- and is never used by
    the live loop."""
    if not market_hours(now):
        return False
    row = {"ts": (now or datetime.now()).isoformat(timespec="seconds"),
           "idx": idx, "a": a, "b": b, "c": c, "rmse": rmse, "f_src": f_src,
           "expiry": expiry, "n_points": n_points}
    return _append(path or surface_path(day, now), row)


def log_transition(idx: str, field: str, frm, to, detail: str = "",
                   *, now: Optional[datetime] = None,
                   path: Optional[str] = None,
                   baseline: bool = False) -> bool:
    """One TRANSITION line. The caller decides a change happened; this only
    writes it -- see `diff_transitions` for the comparison itself. `path`
    overrides `DESK_LOG_PATH` -- a test seam, never used by the live loop.

    `baseline=True` marks a row as the first reading for this index in this
    process -- a restart pseudo-transition, not an observed change -- and
    adds the one extra key `"baseline": true`. Never set it for a genuine
    mid-session change, including a None -> value move on a field that
    simply had not fired yet; see the module docstring."""
    if not market_hours(now):
        return False
    row = {"ts": (now or datetime.now()).isoformat(timespec="seconds"),
           "idx": idx, "field": field, "from": frm, "to": to,
           "detail": detail}
    if baseline:
        row["baseline"] = True
    return _append(path or DESK_LOG_PATH, row)


def diff_transitions(prev: Dict[str, object], curr: Dict[str, object],
                     fields: Tuple[str, ...] = TRANSITION_FIELDS
                     ) -> List[Tuple[str, object, object]]:
    """(field, from, to) for every field whose value changed. Pure, no I/O --
    the caller (server.py's senses loop) owns the previous-state cache and
    decides whether to write what this returns.

    A field absent from `prev` (first reading for this index) counts as a
    change FROM None -- the first observed state is itself worth keeping,
    not a value to suppress. That does NOT by itself make the row a genuine
    transition, though: `prev == {}` is exactly the shape a fresh process
    start hands in (`desk_state` resets on every restart), so it is the
    CALLER's job -- not this pure diff -- to notice `not prev` and log what
    comes back here with `log_transition(..., baseline=True)` instead of as
    a plain transition. See the module docstring and server.py's
    `_log_chain_pace`."""
    out = []
    for field in fields:
        p, c = prev.get(field), curr.get(field)
        if p != c:
            out.append((field, p, c))
    return out
