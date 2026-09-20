"""ladder.py -- a 5-minute per-price ladder from consecutive book snapshots.

THE METHOD (spec 2026-09-20-upstox-tape §C; Order Flow Lab's reconstruct(),
orderflow.html:1478-1511, with this repo's side rule). Per consecutive pair
(prev, cur), V = cur.vtt - prev.vtt in exchange units:

  V < 0        the feed reset: skipped, counted.
  V == 0       nothing traded: nothing attributed (depth_pull owns the book).
  V == ltq     EXACT: one trade of V at cur.ltp. Price/size [M]; side [I] by the
               touch it hit, judged against prev's book (per-trade quote rule --
               NOT the interval rule sweep.py killed: each print against the
               touch that took it, not an interval against its last print).
               A print exactly at mid has no side and is booked `u`.
  otherwise    RECONSTRUCTION: march the attacked side best price first, each
               level's displayed decrease eaten up to what is left of V, stopping
               past cur.ltp by more than HALF_TICK ticks; then the other side the
               same way; the remainder is HIDDEN, booked at cur.ltp on the
               primary side. Volume is conserved: every unit lands somewhere,
               and the counters say how much by proof and how much by residual.

WHAT IS NOT DONE HERE. No half-and-half split of an unknown side (spec §J.11).
No lot division until a bar closes (Task 7). No I/O, no clock.

Pure, stdlib only. Every side is [I]; vol, OHLC and oi are [M].
"""
from __future__ import annotations

from collections import Counter
from math import gcd
from typing import Dict, List, Optional, Tuple

HALF_TICK = 0.55          # Order Flow Lab's tick*0.55: past this, the trade could not have reached the level
INTERVAL_S = 300


def side_of(ltp: float, prev: dict) -> int:
    """+1 buy / -1 sell / 0 unknown, judged against `prev`'s touch."""
    bb = prev["b"][0][0] if prev.get("b") else None
    ba = prev["a"][0][0] if prev.get("a") else None
    if ba is not None and ltp >= ba:
        return 1
    if bb is not None and ltp <= bb:
        return -1
    if bb is None or ba is None:
        return 0
    mid = (bb + ba) / 2
    return 1 if ltp > mid else -1 if ltp < mid else 0


def min_gap(row: dict) -> Optional[float]:
    """The smallest step between adjacent quoted prices, both sides and across
    the spread -- the tick fallback while no dump value is known."""
    ps = sorted({p for p, _ in (row.get("b") or [])} | {p for p, _ in (row.get("a") or [])})
    gaps = [round(b - a, 4) for a, b in zip(ps, ps[1:]) if b - a > 0]
    return min(gaps) if gaps else None


def _march(levels: List[list], cur_at: Dict[float, int], side: int, ltp: float,
           tick: float, remaining: int) -> Tuple[List[dict], int]:
    fills: List[dict] = []
    lim = tick * HALF_TICK
    for p, q0 in levels:
        if remaining <= 0:
            break
        if (p > ltp + lim) if side == 1 else (p < ltp - lim):
            break                                    # past the last print: unreachable
        eaten = min(max(0, int(q0) - int(cur_at.get(p, 0))), remaining)
        if eaten > 0:
            fills.append({"side": side, "p": p, "q": eaten, "hidden": False})
            remaining -= eaten
    return fills, remaining


def _empty(kind: str, V: int = 0) -> dict:
    return {"kind": kind, "V": V, "fills": [], "hidden": 0, "unknown": 0}


def attribute(prev: Optional[dict], cur: dict, tick: float) -> dict:
    """One pair of book rows -> what traded, where, on which side."""
    if not prev or prev.get("vtt") is None or cur.get("vtt") is None:
        return _empty("skip")
    V = int(cur["vtt"]) - int(prev["vtt"])
    if V < 0:
        return _empty("reset", V)
    if V == 0:
        return _empty("quiet")
    ltp = cur.get("ltp")
    if ltp is None:
        ltp = prev.get("ltp")
    if ltp is None:
        return {"kind": "unknown", "V": V, "fills": [], "hidden": 0, "unknown": V}
    side = side_of(ltp, prev)
    ltq = cur.get("ltq")
    if ltq and V == int(ltq):
        return {"kind": "exact", "V": V, "hidden": 0, "unknown": V if side == 0 else 0,
                "fills": [{"side": side, "p": ltp, "q": V, "hidden": False}]}
    cur_at: Dict[float, int] = {p: int(q) for p, q in (cur.get("b") or [])}
    cur_at.update({p: int(q) for p, q in (cur.get("a") or [])})
    primary = side
    if primary == 0:
        db = sum(q for _, q in prev.get("b") or []) - sum(q for _, q in cur.get("b") or [])
        da = sum(q for _, q in prev.get("a") or []) - sum(q for _, q in cur.get("a") or [])
        primary = 1 if da > db else -1 if db > da else 0
    if primary == 0:
        return {"kind": "unknown", "V": V, "hidden": 0, "unknown": V,
                "fills": [{"side": 0, "p": ltp, "q": V, "hidden": False}]}
    first = prev.get("a") or [] if primary == 1 else prev.get("b") or []
    second = prev.get("b") or [] if primary == 1 else prev.get("a") or []
    fills, rem = _march(first, cur_at, primary, ltp, tick, V)
    more, rem = _march(second, cur_at, -primary, ltp, tick, rem)
    fills += more
    hidden = 0
    if rem > 0:
        fills.append({"side": primary, "p": ltp, "q": rem, "hidden": True})
        hidden = rem
    return {"kind": "recon", "V": V, "fills": fills, "hidden": hidden, "unknown": 0}
