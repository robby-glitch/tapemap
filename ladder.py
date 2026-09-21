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

A row with no last price on either side cannot place its volume: V is booked
unknown AND unpriced, with no fill -- the one branch where fills do not sum to V,
and the counter says so.
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
    the spread -- the tick fallback while no dump value is known. A level
    priced `null` (not a number) is skipped rather than raised on by `sorted`."""
    ps = sorted({p for p, _ in (row.get("b") or []) if isinstance(p, (int, float))} |
                {p for p, _ in (row.get("a") or []) if isinstance(p, (int, float))})
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
    return {"kind": kind, "V": V, "fills": [], "hidden": 0, "unknown": 0, "unpriced": 0}


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
        r = _empty("unknown", V)
        r["unknown"] = r["unpriced"] = V
        return r
    side = side_of(ltp, prev)
    ltq = cur.get("ltq")
    if ltq and V == int(ltq):
        r = _empty("exact", V)
        r["unknown"] = V if side == 0 else 0
        r["fills"] = [{"side": side, "p": ltp, "q": V, "hidden": False}]
        return r
    cur_at: Dict[float, int] = {p: int(q) for p, q in (cur.get("b") or [])}
    cur_at.update({p: int(q) for p, q in (cur.get("a") or [])})
    primary = side
    if primary == 0:
        db = sum(q for _, q in prev.get("b") or []) - sum(q for _, q in cur.get("b") or [])
        da = sum(q for _, q in prev.get("a") or []) - sum(q for _, q in cur.get("a") or [])
        primary = 1 if da > db else -1 if db > da else 0
    if primary == 0:
        r = _empty("unknown", V)
        r["unknown"] = V
        r["fills"] = [{"side": 0, "p": ltp, "q": V, "hidden": False}]
        return r
    first = prev.get("a") or [] if primary == 1 else prev.get("b") or []
    second = prev.get("b") or [] if primary == 1 else prev.get("a") or []
    fills, rem = _march(first, cur_at, primary, ltp, tick, V)
    more, rem = _march(second, cur_at, -primary, ltp, tick, rem)
    fills += more
    hidden = 0
    if rem > 0:
        fills.append({"side": primary, "p": ltp, "q": rem, "hidden": True})
        hidden = rem
    r = _empty("recon", V)
    r["fills"], r["hidden"] = fills, hidden
    return r


IST_MS = 19_800_000


def bin_of(t_ms: int, interval_s: int = INTERVAL_S) -> int:
    """The bar-open epoch ms holding t_ms. IST is +05:30, a multiple of five
    minutes, so 5- and 15-minute UTC boundaries ARE the IST boundaries -- no
    offset arithmetic, and byte-equal to spec 1's `t`."""
    w = interval_s * 1000
    return int(t_ms) // w * w


def hms_ist(ms: int) -> str:
    s = (int(ms) + IST_MS) // 1000 % 86400
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}"


class Ladder:
    """Frames in, bars out. One per instrument per day."""

    def __init__(self, lot: Optional[int] = None, tick: Optional[float] = None,
                 interval_s: int = INTERVAL_S, idx: str = "", day: str = ""):
        self.lot, self.tick, self.interval_s, self.idx, self.day = lot, tick, interval_s, idx, day
        self.prev: Optional[dict] = None
        self.bin: Optional[int] = None
        self.acc: Optional[dict] = None
        self.first_ms: Optional[int] = None       # the record's first frame, for `partial`
        self._g = 0                               # running gcd of V, the lot fallback
        self._gaps: Counter = Counter()           # adjacent price steps seen, the tick fallback

    # ---- lot and tick ----------------------------------------------------
    def _tick_now(self, row: dict) -> float:
        if self.tick:
            return self.tick
        g = min_gap(row)
        if g:
            self._gaps[g] += 1
        common = self._gaps.most_common(1)
        return common[0][0] if common else (g or 0.05)

    def _resolve(self) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[float], Optional[str]]:
        if self.lot:
            lot, lot_src, lot_why = self.lot, "given", None
        elif self._g:
            lot, lot_src, lot_why = self._g, "gcd", None
        else:
            lot, lot_src, lot_why = None, None, "no traded volume yet to infer a lot from"
        if self.tick:
            tick, tick_src = self.tick, "given"
        elif self._gaps:
            tick, tick_src = self._gaps.most_common(1)[0][0], "inferred"
        else:
            tick, tick_src = None, None
        return lot, lot_src, lot_why, tick, tick_src

    # ---- the bar --------------------------------------------------------
    def _open(self, b: int) -> None:
        self.bin = b
        self.acc = {"t": b, "o": None, "h": None, "l": None, "c": None, "oi": None,
                    "vol": 0, "buy": 0, "sell": 0, "unknown": 0, "unpriced": 0, "hidden": 0,
                    "lad": {}, "frames": 0, "exact": 0, "reconstructed": 0,
                    "vtt_resets": 0, "levels_seen": 0, "first_ms": None}

    def _close(self) -> Optional[dict]:
        a = self.acc
        if a is None:
            return None
        lot, lot_src, lot_why, tick, tick_src = self._resolve()
        div = lot or 1
        mismatch = 0
        rows = []
        for p in sorted(a["lad"]):
            b, s, u, bt, st = a["lad"][p]
            if lot:
                mismatch += sum(1 for q in (b, s, u) if q % lot)
            rows.append({"p": p, "b": b / div, "s": s / div, "u": u / div, "bt": bt, "st": st})
        why = None
        if a["vtt_resets"]:
            why = f"vtt reset {a['vtt_resets']} time(s) inside the bar"
        elif a["first_ms"] is not None and self.first_ms == a["first_ms"] and a["first_ms"] > a["t"] + 1000:
            why = f"record starts at {hms_ist(a['first_ms'])}, bar opened at {hms_ist(a['t'])}"
        bar = {"t": a["t"], "o": a["o"], "h": a["h"], "l": a["l"], "c": a["c"],
               "vol": a["vol"] / div, "buy": a["buy"] / div, "sell": a["sell"] / div,
               "unknown": a["unknown"] / div, "unpriced": a["unpriced"] / div,
               "delta": (a["buy"] - a["sell"]) / div, "oi": a["oi"],
               "fromTicks": True, "ladder": rows, "rowSize": None, "rowAnchor": 0,
               "lot": lot, "lot_src": lot_src, "lot_why": lot_why, "tick": tick, "tick_src": tick_src,
               "frames": a["frames"], "exact": a["exact"], "reconstructed": a["reconstructed"],
               "hidden": a["hidden"] / div, "vtt_resets": a["vtt_resets"], "lot_mismatch": mismatch,
               "levels_seen": a["levels_seen"], "partial": why is not None, "partial_why": why,
               "src": "ux", "idx": self.idx, "day": self.day}
        self.acc = None
        self.bin = None
        return bar

    def close_open(self) -> Optional[dict]:
        """The bar still open, closed now -- a rebuild's last bin, never live."""
        return self._close()

    def step(self, row: dict) -> Tuple[Optional[dict], List[dict]]:
        """One book row. Returns (the bar this frame closed or None, its fills in units)."""
        tick = self._tick_now(row)
        res = attribute(self.prev, row, tick)
        traded = res["kind"] in ("exact", "recon", "unknown")
        t_bin = row.get("ltt") if traded and row.get("ltt") else row["t"]
        b = bin_of(t_bin, self.interval_s)
        closed = None
        if self.bin is None:
            self._open(b)
        elif b > self.bin:
            closed = self._close()
            self._open(b)
        a = self.acc
        if self.first_ms is None:
            self.first_ms = t_bin
        if a["first_ms"] is None:
            a["first_ms"] = t_bin
        a["frames"] += 1
        a["levels_seen"] = max(a["levels_seen"], len(row.get("b") or []) + len(row.get("a") or []))
        if row.get("oi") is not None:
            a["oi"] = row["oi"]
        if res["kind"] == "reset":
            a["vtt_resets"] += 1
        fills: List[dict] = []
        if traded:
            V = res["V"]
            self._g = gcd(self._g, V)
            a["vol"] += V
            a["hidden"] += res["hidden"]
            a["unknown"] += res["unknown"]
            a["unpriced"] += res["unpriced"]
            a["exact"] += res["kind"] == "exact"
            a["reconstructed"] += res["kind"] == "recon"
            ltp = row.get("ltp")
            if ltp is not None:
                a["o"] = ltp if a["o"] is None else a["o"]
                a["h"] = ltp if a["h"] is None else max(a["h"], ltp)
                a["l"] = ltp if a["l"] is None else min(a["l"], ltp)
                a["c"] = ltp
            for f in res["fills"]:
                r = a["lad"].setdefault(f["p"], [0, 0, 0, 0, 0])
                if f["side"] == 1:
                    r[0] += f["q"]; r[3] += 1
                    a["buy"] += f["q"]
                elif f["side"] == -1:
                    r[1] += f["q"]; r[4] += 1
                    a["sell"] += f["q"]
                else:
                    r[2] += f["q"]
                fills.append({"ltt": t_bin, **f})
        self.prev = row
        return closed, fills
