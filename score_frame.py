"""score_frame.py -- fills the frame record's forward cells, ONCE.

Taps: favourable excursion from the tap bar's close at +1/+3/+6 bars and
+90/+180 minutes, filled only where those bars exist. Tells: resolved as
target (a close at/through the target), falsified (a close through the
negation price), expired (session ended). CONTROL: every walls row that was
not the target, resolved the same way -- logged with the tell from day one
so the kill condition (spec §8.4) can execute. A cell that exists is never
rewritten; a second pass is byte-identical. `write` is the one I/O function."""
from __future__ import annotations

import json
import os
import re
from typing import List, Optional

import frame_log
from frame import _hhmm

HORIZ_BARS = (1, 3, 6)
HORIZ_MIN = (90, 180)


def _num(s) -> Optional[float]:
    m = re.search(r"-?\d+(?:\.\d+)?", str(s or ""))
    return float(m.group()) if m else None


def _fill_tap(tp: dict, bars: List[dict]) -> None:
    i0 = tp.get("i0")
    if i0 is None or i0 >= len(bars):
        return
    c0, side = bars[i0]["c"], tp.get("side") or 1
    ex = tp.setdefault("ex", {})
    for n in HORIZ_BARS:
        key = str(n)
        if key not in ex and i0 + n < len(bars):
            ex[key] = round(side * (bars[i0 + n]["c"] - c0), 1)
    for mins in HORIZ_MIN:
        key = f"{mins}m"
        j = i0 + mins // 5
        if key not in ex and j < len(bars):
            ex[key] = round(side * (bars[j]["c"] - c0), 1)


def _resolve(target, negation, after: List[dict], up: bool):
    for b in after:
        if target is not None and ((up and b["c"] >= target) or (not up and b["c"] <= target)):
            return "target"
        if negation is not None and ((up and b["c"] <= negation) or (not up and b["c"] >= negation)):
            return "falsified"
    return "expired" if after else None


def score(rows: List[dict], bars: List[dict]) -> List[dict]:
    bars = sorted(bars, key=lambda b: b["t"])
    for r in rows:
        for tp in r.get("taps") or []:
            _fill_tap(tp, bars)
        w = r.get("setup") or {}
        after = [b for b in bars if _hhmm(b["t"]) > (r.get("ts") or "00:00")]
        px0 = after[0]["o"] if after else None
        for tell in w.get("tells") or []:
            if "resolved" in tell:
                continue
            tgt, neg = _num(tell.get("target")), _num(tell.get("negation"))
            if px0 is None:
                continue  # no bars after this row's time yet -- leave the key ABSENT (not None) so a later pass can still fill it
            if tgt is None:
                tell["resolved"] = None  # no parsable target -- terminal, write-once
                continue
            up = tgt > px0
            tell["resolved"] = _resolve(tgt, neg, after, up)
            dist = abs(tgt - px0)
            if "control" not in w:
                w["control"] = [{"p": lr["p"], "kind": lr.get("kind"), "dist": round(abs(lr["p"] - px0), 1),
                                 "same_distance": abs(abs(lr["p"] - px0) - dist) <= dist * 0.25,
                                 "resolved": _resolve(lr["p"], None, after, lr["p"] > px0)}
                                for lr in (r.get("walls") or {}).get("rows") or []
                                # exact float equality on purpose: tgt and lr["p"] are both prices walls itself emitted
                                if lr.get("p") is not None and lr["p"] != tgt]
    return rows


def write(day: str, bars: List[dict], path: Optional[str] = None) -> int:
    p = path or frame_log.day_path(day)
    if not os.path.exists(p):
        return 0
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    rows = score(rows, bars)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    os.replace(tmp, p)
    return len(rows)
