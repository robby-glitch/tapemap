"""impact.py -- how many lots move price a tick (Kyle's lambda), rolling 120 s.

Order Flow Lab's buildLambda (orderflow.html:701-730): a regression through the
origin of mid change (ticks) on signed attributed volume, over the last
IMPACT_WIN_S seconds of frames. lambda = sum(sv*dp) / sum(sv^2) ticks per unit
when both sums are positive, else None with its why. Reported as LOTS PER TICK
(1 / (lambda * lot)) -- the desk trades lots -- and as pct: prints.pct_rank
(strict) of lambda against the session's earlier readings. A thin market is a
HIGH lambda. [I] throughout, because the signed volume is (spec §J.3).

Kill condition (spec §G): over 30 sessions, if top-quartile lambda readings
precede top-5% 6-bar moves no more often than any other reading, the figure
goes. Never printed as a rate.

Pure, stdlib only, no I/O, no clock -- time is the rows' own `t`.
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional

import prints

IMPACT_WIN_S = 120


class Impact:
    def __init__(self, lot: Optional[int] = None, tick: Optional[float] = None):
        self.lot, self.tick = lot, tick
        self._win: deque = deque()          # (t_ms, dp_ticks, sv_units)
        self._prev_mid: Optional[float] = None
        self._history: List[float] = []     # every lambda read so far, for pct

    def on_frame(self, row: dict, fills: List[dict]) -> None:
        b = row["b"][0][0] if row.get("b") else None
        a = row["a"][0][0] if row.get("a") else None
        if b is None or a is None:
            return
        mid = (b + a) / 2
        tick = self.tick or 0.05
        dp = 0.0 if self._prev_mid is None else (mid - self._prev_mid) / tick
        self._prev_mid = mid
        sv = sum(f["q"] * f["side"] for f in fills if f.get("side"))
        t = int(row["t"])
        self._win.append((t, dp, sv))
        while self._win and self._win[0][0] < t - IMPACT_WIN_S * 1000:
            self._win.popleft()
        lam, _ = self._lam()
        if lam is not None:
            self._history.append(lam)          # the session's readings, one per frame that had one

    def _lam(self):
        """(lambda in ticks per unit, None) or (None, why)."""
        if not self._win or self._win[-1][0] - self._win[0][0] < (IMPACT_WIN_S - 1) * 1000:
            return None, "fewer than 120 s of frames"
        num = sum(dp * sv for _, dp, sv in self._win)
        den = sum(sv * sv for _, _, sv in self._win)
        if den <= 0:
            return None, "no signed volume in the window"
        if num <= 0:
            return None, "price moved against the flow over the window"
        return num / den, None

    def read(self) -> dict:
        """Pure: safe to call from the request path any number of times."""
        out = {"lambda": None, "lots_per_tick": None, "pct": None, "n": len(self._win), "why": None, "tag": "I"}
        lam, why = self._lam()
        if lam is None:
            out["why"] = why
            return out
        out["lambda"] = lam
        out["lots_per_tick"] = 1 / (lam * (self.lot or 1))
        # rank against the readings BEFORE this one (the last history entry is this frame's own)
        out["pct"] = prints.pct_rank(self._history[:-1], lam)
        return out
