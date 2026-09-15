"""dwell.py -- war-map object B: the trap detector.

WHAT IT ANSWERS. The operator's thesis step 2: price is walked to a reaction
point and LEFT there while retail loads positions -- the dwell IS the trap
being set. This watches for price holding within a band of a known level
(levels.py) and, while it holds, measures what is loading: OI added per side
near the level [M], and whether buyers are paying up to get in -- crossing to
the ask, the retail tell [M arithmetic, I attribution]. It DESCRIBES the trap
being set; it never predicts the spring.

THE BAND IS THE SESSION'S OWN, not a constant. `band()` is a multiple of the
session's median one-minute move measured so far (the house pattern: every
threshold ranks against the session's own distribution). The two numbers that
remain constants -- the multiple, and the minutes a hold must last before it
is a DWELL -- are the [I] layer, declared below, and are what forward scoring
exists to judge.

WHO IS "RETAIL" IS AN INFERENCE, FOREVER. OI added at a level during a dwell
is measured; that it is retail loading the trap is the thesis, not the data.
Every reading that leans on the attribution says [I]. Tools that print the
attribution as fact are the cheap ones this map exists to not be.

KILL CONDITION (declared at birth, per the plan): if after ~30 scored
sessions dwell readings do not precede expansions more often than random
level-touches do, this detector is DELETED, not tuned.

Forward-logged by sequence.py (the state machine owns the ledger); this
module holds no file handles. Pure computation, stdlib only, no I/O.
"""

from __future__ import annotations

from bisect import insort
from typing import Dict, List, Optional

# --- the [I] layer ----------------------------------------------------------
BAND_K = 2.0          # band = BAND_K x median 1-minute |move| so far
MIN_BAND_FRAC = 3e-4  # ...floored at this fraction of spot (a dead-calm open
                      # must not produce a zero-width band nothing can enter)
DWELL_MIN_S = 300     # in-band this long before a hold is called a DWELL
NEAR_STEPS = 2        # strikes either side of the level whose OI is "at" it
MOVE_STEP_S = 60      # the move samples the band calibrates on: ~1 minute
MIN_MOVES = 5         # fewer move samples than this -> band not trusted yet


class DwellWatch:
    """One per index. Feed it chain-pace snapshots; it tracks at most one
    dwell at a time -- the level price is nearest to. Price cannot dwell in
    two places at once, and the nearest level is the one being defended."""

    def __init__(self):
        self._moves: List[float] = []          # sorted |1-min move| samples
        self._last_move_ref: Optional[tuple] = None   # (sec, spot)
        self._cur: Optional[dict] = None       # the active/candidate dwell
        self.read: dict = {"active": False, "why": "no snapshot yet"}

    # -- band calibration ---------------------------------------------------
    def _feed_move(self, sec: float, spot: float):
        if self._last_move_ref is None:
            self._last_move_ref = (sec, spot)
            return
        s0, p0 = self._last_move_ref
        if sec - s0 >= MOVE_STEP_S:
            insort(self._moves, abs(spot - p0))
            self._last_move_ref = (sec, spot)

    def band(self, spot: Optional[float] = None) -> Optional[float]:
        """Half-width of "at the level", in points; None until calibrated."""
        if len(self._moves) < MIN_MOVES:
            return None
        med = self._moves[len(self._moves) // 2]
        floor = (spot or 0.0) * MIN_BAND_FRAC
        return max(BAND_K * med, floor)

    # -- the dwell ----------------------------------------------------------
    def _near_oi(self, strikes: List[dict], px: float, step: float) -> Dict[str, float]:
        out = {"ce": 0.0, "pe": 0.0}
        for s in strikes or []:
            k = s.get("k")
            if k is None or abs(k - px) > NEAR_STEPS * step:
                continue
            for side in ("ce", "pe"):
                out[side] += (s.get(side) or {}).get("oi") or 0.0
        return out

    def _crossing(self, strikes: List[dict], px: float, step: float) -> Optional[float]:
        """Share of near legs trading at/above mid -- buyers paying up.
        None when no near leg publishes a two-sided quote."""
        hit = tot = 0
        for s in strikes or []:
            k = s.get("k")
            if k is None or abs(k - px) > NEAR_STEPS * step:
                continue
            for side in ("ce", "pe"):
                leg = s.get(side) or {}
                bid, ask, ltp = leg.get("bid"), leg.get("ask"), leg.get("ltp")
                if not bid or not ask or not ltp or ask <= bid:
                    continue
                tot += 1
                if ltp >= (bid + ask) / 2.0:
                    hit += 1
        return (hit / tot) if tot else None

    @staticmethod
    def _step(strikes: List[dict]) -> float:
        ks = sorted(s["k"] for s in strikes or [] if s.get("k") is not None)
        return min((b - a) for a, b in zip(ks, ks[1:])) if len(ks) > 1 else 50.0

    def on_snapshot(self, sec: float, spot: Optional[float],
                    strikes: Optional[List[dict]],
                    levels: List[dict]) -> dict:
        """One chain snapshot -> the dwell reading, always."""
        if spot is None:
            self.read = {"active": False, "why": "no spot in this snapshot"}
            return self.read
        self._feed_move(sec, spot)
        band = self.band(spot)
        if band is None:
            self.read = {"active": False,
                         "why": f"band calibrating: {len(self._moves)} move "
                                f"sample(s), need {MIN_MOVES}"}
            return self.read

        near = [(abs(spot - l["px"]), l) for l in levels or []
                if abs(spot - l["px"]) <= band]
        if not near:
            if self._cur:
                self._cur = None            # left the band: the hold is over
            self.read = {"active": False, "band": round(band, 2),
                         "why": "price is not at any known level"}
            return self.read

        _, lvl = min(near, key=lambda p: p[0])
        key = f"{lvl['kind']}@{lvl['px']:.0f}"
        step = self._step(strikes)
        if not self._cur or self._cur["key"] != key:
            self._cur = {"key": key, "kind": lvl["kind"], "px": lvl["px"],
                         "t0": sec, "oi0": self._near_oi(strikes, lvl["px"], step),
                         "cross": []}
        cur = self._cur
        held_s = sec - cur["t0"]
        oi_now = self._near_oi(strikes, lvl["px"], step)
        added = {s: oi_now[s] - cur["oi0"][s] for s in ("ce", "pe")}
        cx = self._crossing(strikes, lvl["px"], step)
        if cx is not None:
            cur["cross"].append(cx)
        tot_added = abs(added["ce"]) + abs(added["pe"])
        side_share = (max(abs(added["ce"]), abs(added["pe"])) / tot_added
                      if tot_added else None)
        loaded_side = (None if not tot_added
                       else ("ce" if abs(added["ce"]) >= abs(added["pe"]) else "pe"))
        crossing = (sum(cur["cross"]) / len(cur["cross"])
                    if cur["cross"] else None)
        self.read = {
            "active": held_s >= DWELL_MIN_S,
            "holding": True, "level": {"kind": cur["kind"], "px": cur["px"]},
            "held_s": round(held_s), "band": round(band, 2),
            # [M]: the arithmetic. [I]: that what loaded is retail's trap.
            "oi_added_ce": round(added["ce"]), "oi_added_pe": round(added["pe"]),
            "loaded_side": loaded_side,
            "side_share": round(side_share, 2) if side_share is not None else None,
            "buyers_crossing": round(crossing, 2) if crossing is not None else None,
            "why": (f"{held_s / 60:.0f} min at {cur['kind']} {cur['px']:,.0f}"
                    if held_s >= DWELL_MIN_S else
                    f"holding at {cur['kind']} {cur['px']:,.0f}, "
                    f"{held_s:.0f}s of {DWELL_MIN_S}s"),
            "tag": "I",
        }
        return self.read
