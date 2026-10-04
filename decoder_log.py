# tapemap/decoder_log.py
"""decoder_log.py -- the decoder's forward log (Fable, docs/reader/FABLE-DECODER-DESIGN-2026-10-04.md §6.1-6.2).

data/decoder/decoder_<day>.jsonl, append-only, written from the tape the GoCharting extension posts (its `decoder`
object, schema v1, and its closed bars). Three kinds of row, each written ONCE:
  "event"   an event the first time its id is seen, exactly as the page posted it (one definition: never re-derived)
  "state"   every change of its confirm state or its OI read (BAAKI -> CONFIRMED / FAILED; OI BAAKI -> CONFIRMED /
            REVERSED), keyed (id, state, oi.state, split) -- the history is never edited, a state only moves on
  "outcome" +6 and +12 bars after the event's bar, filled live from the posted closed bars: points from that bar's
            close in the event's direction (side), and the max favourable / adverse excursion. Never recomputed later
            from a re-cut cache. side 0 is written unsigned.
These are ROWS for her to read against the kill conditions she signs (Fable §6.2): no rate is computed here or anywhere.

MARKET HOURS ONLY: the server calls append() behind its one gate (server._market_hours), the same gate as the frame log
and the marks writer. A restart resumes: the keys already on disk are read once per day and never written twice.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

DIR = os.path.join("data", "decoder")
HORIZONS = (6, 12)
_SEEN: Dict[str, Set[Tuple]] = {}
_LOCK = threading.Lock()


def path(day: str) -> str:
    return os.path.join(DIR, f"decoder_{day}.jsonl")


def _key(r: dict) -> Tuple:
    if r.get("row") == "event":
        return ("event", r.get("id"))
    if r.get("row") == "state":
        return ("state", r.get("id"), r.get("state"), r.get("oi_state"), r.get("split"))
    return ("outcome", r.get("id"), r.get("h"))


def _keys(day: str) -> Set[Tuple]:
    if day not in _SEEN:
        seen: Set[Tuple] = set()
        p = path(day)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        seen.add(_key(json.loads(line)))
                    except (ValueError, TypeError):
                        continue          # a torn line is skipped, never fatal
        _SEEN[day] = seen
    return _SEEN[day]


def outcome(closed: List[dict], e: dict, h: int) -> Optional[dict]:
    """+h bars after the event's bar, from the closed bars as posted; None until those bars exist."""
    ts = [b.get("t") for b in closed]
    if e.get("t") not in ts:
        return None
    j = ts.index(e["t"])
    if j + h >= len(closed):
        return None
    base, win, side = closed[j].get("c"), closed[j + 1: j + 1 + h], e.get("side") or 0
    if base is None or any(b.get("c") is None or b.get("h") is None or b.get("l") is None for b in win):
        return None
    s = side if side else 1
    move = round(s * (win[-1]["c"] - base), 1)
    hi, lo = max(b["h"] for b in win), min(b["l"] for b in win)
    mfe = round((hi - base) if s > 0 else (base - lo), 1)
    mae = round((lo - base) if s > 0 else (base - hi), 1)
    return {"h": h, "from": base, "to": win[-1]["c"], "move": move, "mfe": mfe, "mae": mae, "signed": bool(side)}


def append(dec: Optional[dict], closed: List[dict], day: str, idx: str) -> int:
    """Write what is new in this post; returns the number of rows written. Never raises at the caller."""
    if not isinstance(dec, dict) or dec.get("v") != 1:
        return 0
    rows: List[dict] = []
    with _LOCK:
        seen = _keys(day)
        now = round(time.time(), 1)
        for e in dec.get("events") or []:
            if not isinstance(e, dict) or not e.get("id"):
                continue
            base = {"day": day, "idx": idx, "at": now, "id": e["id"], "kind": e.get("kind")}
            ev = {**base, "row": "event", "event": e}
            if ("event", e["id"]) not in seen:
                rows.append(ev)
            oi = e.get("oi") or {}
            st = {**base, "row": "state", "state": e.get("state"), "state_t": e.get("state_t"), "oi_state": oi.get("state"),
                  "split": e.get("split"), "quad": e.get("quad"), "chip": e.get("chip")}
            if _key(st) not in seen:
                rows.append(st)
            for h in HORIZONS:
                if ("outcome", e["id"], h) in seen:
                    continue
                o = outcome(closed, e, h)
                if o is not None:
                    rows.append({**base, "row": "outcome", **o})
        if rows:
            os.makedirs(DIR, exist_ok=True)
            with open(path(day), "a", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, default=str) + "\n")
            seen.update(_key(r) for r in rows)
    return len(rows)
