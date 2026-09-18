"""Read the day's frame record back over HTTP — the one thing nothing has ever done.

`data/frame/frame_<day>.jsonl` holds one whole frame per signature change: on 2026-09-18
that was 2,064 rows and 55 MB. Every row carries the full coverage blob and every walls
row, which is most of the bytes and none of what a screen wants. So this streams the file
line by line and emits a compact row, and it NEVER loads the file into memory — a
whole-file read on this path is exactly what wedged the server twice on 2026-09-18.

The day's order flow is in here and is the reason this exists. The extension replays
GoCharting's loaded footprint when the tab opens late, so a file whose first frame landed
at 09:50 still carries events stamped 09:15; those events are what a chart wants to draw
from the open, whatever time the process started.

ponytail: cached by (mtime, size, idx) — a re-read only when the file actually changed.
Swap for a tail-seek if the record ever outgrows one poll's worth of parse time.
"""
import io
import json
import os
from typing import Optional

import frame_log
import signals

_cache = {}          # path -> (key, rows, events)


def _row(fr: dict) -> dict:
    """One record row, small enough to send a few thousand of."""
    w = fr.get("where") or {}
    s = fr.get("setup") or {}
    sig = s.get("signal") or {}
    return {
        "t": fr.get("ts"),
        "state": s.get("state"),
        "fire": bool(s.get("fire")),
        "signal": sig.get("state"),
        "visit": s.get("visit"),
        "gate": ((fr.get("head") or {}).get("gate") or {}).get("level"),
        "z": w.get("z"),
        "px": w.get("px"),
        "missing": fr.get("missing") or [],
    }


def read(day: str, idx: str = "NIFTY", path: Optional[str] = None):
    """`(rows, events)` for one index and day, streamed.

    `rows` is one entry per signature change, in file order. `events` is the day's tape
    events de-duplicated on (t, kind, p) and sorted by time — the order flow, including
    whatever the extension replayed out of the chart before it started posting.
    """
    p = path or frame_log.day_path(day)
    if not os.path.exists(p):
        return [], []
    try:
        st = os.stat(p)
        key = (st.st_mtime, st.st_size, idx)
    except OSError:
        return [], []
    hit = _cache.get(p)
    if hit and hit[0] == key:
        return hit[1], hit[2]

    rows, seen = [], {}
    try:
        with io.open(p, encoding="utf-8") as fh:
            for line in fh:                      # streamed: never the whole file
                line = line.strip()
                if not line:
                    continue
                try:
                    fr = json.loads(line)
                except ValueError:
                    continue                     # a torn row is skipped, never fatal
                if fr.get("idx") != idx:
                    continue
                rows.append(_row(fr))
                for e in ((fr.get("tape") or {}).get("events") or []):
                    t = e.get("t")
                    if not t:
                        continue
                    seen[(t, e.get("kind"), e.get("p"))] = {
                        "t": t, "kind": e.get("kind"), "p": e.get("p"),
                        "at": (e.get("at") or {}).get("label"),
                        # colour on her chart is the SIDE; without it a screen
                        # draws neutral or invents one, and invented is a verdict
                        "side": e.get("side"),
                        # Which kinds count as CONFIRMING evidence, decided
                        # HERE so no screen carries a second copy of the list.
                        # `signals.CONFIRMS` is the one vocabulary; a UI that
                        # spelled out absorption/exhaustion/trap for itself is
                        # the same rule in two languages, which is how the
                        # 09:25 gate drifted for weeks.
                        "confirm": e.get("kind") in signals.CONFIRMS,
                    }
    except OSError:
        return [], []

    events = sorted(seen.values(), key=lambda e: e["t"])
    _cache[p] = (key, rows, events)
    return rows, events


def demo():
    """Self-check: streaming, per-index filtering, event de-duplication, the cache."""
    import tempfile
    day = "2026-09-18"
    a = {"idx": "NIFTY", "ts": "09:50", "where": {"z": -2.1, "px": 100.0},
         "setup": {"state": "ARMED", "fire": False, "visit": "buy@09:45",
                   "signal": {"state": "ARMED"}},
         "head": {"gate": {"level": "PATA NAHI"}}, "missing": [],
         "tape": {"events": [{"t": "09:15", "kind": "absorption", "p": 99.0,
                              "at": {"label": "at PDL 99"}},
                             {"t": "09:20", "kind": "initiative", "p": 101.0}]}}
    b = dict(a, ts="09:55")                       # the same event again -> one row
    c = dict(a, idx="BANKNIFTY", ts="09:56")      # another index -> filtered out
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.jsonl")
        with io.open(p, "w", encoding="utf-8") as fh:
            for r in (a, b, c):
                fh.write(json.dumps(r) + "\n")
            fh.write("{ torn\n")                  # must not be fatal
        rows, events = read(day, "NIFTY", path=p)
        assert len(rows) == 2, rows
        assert rows[0]["t"] == "09:50" and rows[0]["signal"] == "ARMED"
        assert rows[0]["gate"] == "PATA NAHI"
        assert len(events) == 2, events           # de-duplicated
        # The CONFIRMS vocabulary lives in signals.py and only there: an
        # absorption confirms, an initiative does not, and a screen reads the
        # flag rather than keeping its own list of kinds.
        assert events[0]["confirm"] is True, events
        assert events[1]["kind"] == "initiative" and events[1]["confirm"] is False
        assert events[0]["t"] == "09:15", events  # BEFORE the first frame: the replay
        assert events[0]["at"] == "at PDL 99"
        again, _ = read(day, "NIFTY", path=p)
        assert again is rows, "second read must come from the cache"
        other, _ = read(day, "BANKNIFTY", path=p)
        assert len(other) == 1 and other[0]["t"] == "09:56"
    print("record_read demo ok")


if __name__ == "__main__":
    demo()
