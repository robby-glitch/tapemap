"""senses.py -- the three book detectors, run together and forward-logged.

WHAT IT IS. `sweep`, `absorption` and `depth_pull` are pure and know nothing
about feeds, files or time. This is the thin layer that owns one set of them
per instrument, feeds them the ladder off a frame, and writes what they say to
a forward record. It is the only file in the group that touches disk.

**IT WRITES TO ITS OWN LOG, NOT TO `trigger_log.jsonl`, AND THAT IS
DELIBERATE.** That file holds three populations -- `5c`, `zone`, and the
quarantined legacy rows -- and the standing rule is that pooling them is the
easiest way to destroy months of record. Detector events are a FOURTH thing
with no outcome, no side and no entry price; putting them in the same file
would mean every future reader has to remember to filter them out, and one who
forgets corrupts the only irreplaceable artefact in the project. So they live
under `data/senses/`, one file per trading day, and nothing here can touch the
other file.

A ROW'S SHAPE. The event's own fields, then an envelope laid over the top:
`day`, `t`, `inst`, `key`, and **`det`** -- which detector spoke. `det` is
deliberately not called `kind`, because `Sweep` already owns a `kind`
("swept" / "pulled" / "unknown") and the two would collide; the envelope wins
every clash, so a detector field can never rewrite the row's identity.

WHAT A ROW IS, AND WHAT IT IS NOT. A row is a MEASUREMENT with a timestamp:
this many levels were taken, this much size left, this level ate this much
more than it showed. It is not a signal, carries no direction, and predicts
nothing. Scoring it means asking, later, what followed -- and that question
cannot be asked at all unless the rows exist first, which is the entire reason
this runs from day one while gating nothing.

FAIL-SOFT, LIKE `trigger_log.log_new`. Any exception while writing is
swallowed and counted. The tape must never go down because a log line could
not be written, and a detector that can crash the feed is worse than no
detector.

THE FRAME IS THE UNIT, NOT THE POLL. `observe` takes what it is given; a
caller polling faster than the feed flushes will hand it the same frame twice.
That double-counts nothing in `sweep` or `depth_pull` -- an unchanged book
produces no event -- but it does inflate `absorption.frames`, which counts
observations rather than distinct updates. Poll no faster than the feed and
the two agree; poll faster and read `frames` as "snapshots seen".
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional

import absorption
import depth_pull
import sweep
import upstox_adapter

# ONE FILE PER DAY, IN ITS OWN DIRECTORY, GITIGNORED -- exactly what
# `data/chain/` already does and for the same measured reason. A first live
# run on 2026-08-20 wrote 2,186 rows in 73 seconds across 101 instruments,
# which extrapolates to roughly 670k rows and ~170MB for one session. A single
# growing file at that rate is the chain-snapshot problem rebuilt: too big for
# git, too big to open, and impossible to hand one day of to a scorer.
DIR = os.path.join("data", "senses")


def day_path(day=None):
    """The log for one trading day. Resolved at WRITE time, not at start, so a
    process left running across midnight rolls into the next day's file rather
    than appending tomorrow's rows to today's."""
    day = day or datetime.now().strftime("%Y-%m-%d")
    return os.path.join(DIR, f"senses_{day}.jsonl")


def ladder_of(feed):
    """(ladder, vtt) out of one decoded frame -- the two things all three want.

    `vtt` is read from the SAME frame as the book, never from a later one: a
    volume figure taken a moment after the ladder would attribute trades to a
    book that had already moved.
    """
    core = upstox_adapter._core(feed)
    lad = upstox_adapter.depth_ladder(feed)
    vtt = upstox_adapter._num((core or {}).get("vtt"))
    return lad, vtt


class Senses:
    """One set of detectors per instrument, plus a forward log.

    `observe` returns the events from ONE frame so a live panel can render
    them; the same events are appended to the log. Nothing is returned that
    was not written, and nothing is written that was not returned.
    """

    def __init__(self, path: Optional[str] = None, day: Optional[str] = None):
        self.path = path            # None -> one file per day, see day_path
        self.day = day
        self._det: Dict[str, tuple] = {}
        self.written = 0
        self.failed = 0

    def _for(self, inst: str):
        if inst not in self._det:
            self._det[inst] = (sweep.SweepDetector(),
                               absorption.AbsorptionDetector(),
                               depth_pull.DepthPullDetector())
        return self._det[inst]

    def observe(self, inst: str, t: str, feed, key: str = "") -> List[dict]:
        """One instrument, one frame -> the rows it produced (also logged)."""
        lad, vtt = ladder_of(feed)
        sw, ab, dp = self._for(inst)
        rows = []
        for kind, ev in (("sweep", sw.on_snapshot(t, lad, vtt)),
                         ("absorption", ab.on_snapshot(t, lad, vtt)),
                         ("pull", dp.on_snapshot(t, lad, vtt))):
            if ev is None:
                continue
            # THE ENVELOPE WINS, AND `det` IS NOT CALLED `kind`. `Sweep` has
            # its own `kind` ("swept" / "pulled" / "unknown"), so an envelope
            # field of that name was silently overwritten by it -- which made
            # a sweep row and an absorption row indistinguishable in the log.
            # Caught by a test before a single row was written; the record
            # would have been unreadable and there is no repairing a forward
            # log after the fact.
            row = dict(asdict(ev))
            row.update({"day": self.day or datetime.now().strftime("%Y-%m-%d"),
                        "t": t, "inst": inst, "key": key, "det": kind})
            rows.append(row)
        self._append(rows)
        return rows

    def _append(self, rows: List[dict]) -> int:
        """Append rows, fail-soft. Returns how many landed.

        Opened per call in append mode rather than held open, so a crash
        cannot truncate the record and an external reader always sees whole
        lines. At detector rates this is a handful of writes a minute, not a
        hot path.
        """
        if not rows:
            return 0
        try:
            path = self.path or day_path(self.day)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r) + "\n" for r in rows))
            self.written += len(rows)
            return len(rows)
        except Exception:
            self.failed += len(rows)          # never take the tape down
            return 0

    def pending(self) -> Dict[str, dict]:
        """Absorption windows still open, per instrument, for a live panel.

        These are RUNNING TOTALS and are not logged -- a row is written when a
        window closes and its number stops changing. Anything rendering these
        must say so, or a reader will quote a figure that keeps growing after
        they looked at it.
        """
        out = {}
        for inst, (_sw, ab, _dp) in self._det.items():
            live = ab.pending()
            if live:
                out[inst] = asdict(live)
        return out
