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


# ---- ANYTIME-START: the day's events as last known, for the chapters (story.chapters, src "log") ----------------------
_EV_CACHE: Dict[Tuple[str, str], Tuple[Tuple, List[dict]]] = {}


def read_events(day: str, idx: str) -> List[dict]:
    """Every event this log kept for (day, idx), with its newest state row folded in. Read again only when the file
    changed (size, mtime); a missing file is an empty day."""
    p = path(day)
    st = None
    for q in (p, p + ".gz"):                      # a week-old day is gzipped by daylog.py
        try:
            st = os.stat(q)
            break
        except OSError:
            continue
    if st is None:
        return []
    sig = (st.st_size, st.st_mtime)
    hit = _EV_CACHE.get((day, idx))
    if hit and hit[0] == sig:
        return hit[1]
    evs: Dict[str, dict] = {}
    import daylog
    with daylog.open_text(p) as f:
        for line in f:
            try:
                r = json.loads(line)
            except (ValueError, TypeError):
                continue
            if r.get("idx") != idx:
                continue
            if r.get("row") == "event" and isinstance(r.get("event"), dict):
                evs.setdefault(r["id"], dict(r["event"]))
            elif r.get("row") == "state" and r.get("id") in evs:
                e = evs[r["id"]]
                e.update({k: r[k] for k in ("state", "state_t", "split", "quad", "chip") if r.get(k) is not None})
    out = list(evs.values())
    _EV_CACHE[(day, idx)] = (sig, out)
    return out


# ---- HOLD vs DECODER: the engine's word and the decoder's count, side by side, once a minute while she is marked -------
_MIN_SEEN: Dict[str, Set[Tuple]] = {}


def minute_path(day: str) -> str:
    return os.path.join(DIR, f"hold_vs_decoder_{day}.jsonl")


def minute(day: str, idx: str, hhmm: str, fold: Optional[dict], read: Optional[dict], val: Optional[dict] = None) -> bool:
    """One row per (trade, minute): the engine's headline / clause / chips, the decoder's against / behind / word, and
    the Validate read beside them (validate_live: the lamp states, reversal N/4, the role prompt, the spec's shadow words,
    her acks). Called behind the server's market-hours gate only. Rows, never a rate: which was early is hers to read."""
    v = (fold or {}).get("view") or {}
    tid = (fold or {}).get("id") or v.get("trade_id")
    if not (fold or {}).get("ok") or not tid or v.get("headline") is None:
        return False
    k = (str(tid), hhmm)
    with _LOCK:
        if day not in _MIN_SEEN:
            seen: Set[Tuple] = set()
            if os.path.exists(minute_path(day)):
                with open(minute_path(day), encoding="utf-8") as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                            seen.add((str(r.get("trade_id")), r.get("minute")))
                        except (ValueError, TypeError):
                            continue
            _MIN_SEEN[day] = seen
        if k in _MIN_SEEN[day]:
            return False
        r = read or {}
        row = {"day": day, "idx": idx, "at": round(time.time(), 1), "minute": hhmm, "trade_id": tid,
               "engine": {"headline": v.get("headline"), "clause": v.get("clause"), "chips": v.get("chips"), "fut": v.get("fut")},
               "decoder": {"against": r.get("against"), "behind": r.get("behind"), "word": r.get("word"), "word_t": r.get("word_t"),
                           "chips": [x.get("chip") for x in (r.get("items") or [])][-6:]} if read else None,
               "decoder_why": None if read else "the decoder had no read (no events posted since her entry)",
               "validate": {"lamps": {k: x.get("state") for k, x in (val.get("lamps") or {}).items()},
                            "level": (val.get("level") or {}).get("state"), "reversal_met": (val.get("reversal") or {}).get("met"),
                            "prompt": val.get("prompt"), "shadow": {k: (val.get("shadow") or {}).get(k) for k in ("word", "amber_no_exit", "cut_2of4")},
                            "acks": val.get("acks") or []} if (val or {}).get("lamps") else None,
               "validate_why": None if (val or {}).get("lamps") else ((val or {}).get("word_why") or "no validate read this minute"),
               "tag": {"M": ["engine.fut"], "I": ["engine.headline", "decoder"]}}
        os.makedirs(DIR, exist_ok=True)
        with open(minute_path(day), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
        _MIN_SEEN[day].add(k)
    return True
