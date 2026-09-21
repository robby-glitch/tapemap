"""runs.py -- three big same-side fills in a row (spec 2026-09-20 §G).

Order Flow Lab's sweep sequence (orderflow.html:837-895), fed by ladder.py's
FILL EVENTS rather than sweep.py's rows: 485 sweep rows a day is ~26 per
twenty minutes, under the 50 the percentile needs; fills run in the thousands.

Five constants, carried verbatim and NOT tuned before spec §K:
  RUN_N      3     fills in a row before it counts
  RUN_PCT    0.90  "big" = at or above this percentile ...
  RUN_WIN_S  1200  ... of fill sizes in the last 20 minutes
  RUN_GAP_S  3     at most this many seconds between one fill and the next
  RUN_MIN_N  50    a percentile drawn from fewer fills is not trusted

CAUSAL: a fill is judged against the fills BEFORE it, then inserted. A run
breaks on a big fill from the OTHER side; a small fill (either side) is
ignored -- "three sells in a row" means nobody big bought in between. A run
fires once, at its third fill, and grows in place while the pressing continues.
Side is [I] because the fills' sides are; side 0 neither joins nor breaks.

Kill condition (spec §G): at n >= 30 runs on one index, the +6-bar excursion
in the run's direction must exceed the unconditional control by one sd, else
the glyph goes. Scored by spec 1's scorer, never printed as a rate.

Pure, stdlib only, no I/O, no clock.
"""
from __future__ import annotations

from bisect import bisect_left, insort
from collections import deque
from typing import List, Optional

RUN_N = 3
RUN_PCT = 0.90
RUN_WIN_S = 1200
RUN_GAP_S = 3
RUN_MIN_N = 50


class Runs:
    def __init__(self, lot: Optional[int] = None):
        self.lot = lot
        self._win: deque = deque()          # (ltt_ms, q) in arrival order
        self._sizes: List[int] = []         # the same q's, sorted
        self._run: Optional[dict] = None    # {"side", "fills": [f...], "ev": dict | None}
        self.events: List[dict] = []
        self._checked = False

    @property
    def window_n(self) -> int:
        return len(self._win)

    def _lots(self, units: float) -> float:
        return units / self.lot if self.lot else units

    @staticmethod
    def _wavg_p(fills: List[dict]) -> Optional[float]:
        """The run's price for the chart: its fills' quantity-weighted mean."""
        q = sum(f["q"] for f in fills)
        return round(sum(f["p"] * f["q"] for f in fills) / q, 4) if q else None

    def _forget(self, now_ms: int) -> None:
        while self._win and self._win[0][0] < now_ms - RUN_WIN_S * 1000:
            _, q = self._win.popleft()
            i = bisect_left(self._sizes, q)
            if i < len(self._sizes) and self._sizes[i] == q:
                del self._sizes[i]

    def _threshold(self) -> Optional[int]:
        if len(self._sizes) < RUN_MIN_N:
            return None
        return self._sizes[min(len(self._sizes) - 1, int(len(self._sizes) * RUN_PCT))]

    def why(self) -> Optional[str]:
        if len(self._sizes) < RUN_MIN_N:
            return "fewer than 50 fills in the last 20 minutes — the percentile has nothing to rank against"
        return None if self.events else "checked, none"

    def on_fill(self, f: dict) -> Optional[dict]:
        """Judge one fill against the window BEFORE inserting it. Returns the
        run the moment it fires (its third fill); a continuing run grows in
        place and returns None."""
        t, q, side = int(f["ltt"]), int(f["q"]), int(f.get("side") or 0)
        self._forget(t)
        thr = self._threshold()
        fired = None
        if thr is not None and q >= thr and side != 0:          # a BIG fill with a side
            run = self._run
            prev = run["fills"][-1] if run else None
            if run and run["side"] == side and t - prev["ltt"] <= RUN_GAP_S * 1000:
                run["fills"].append(f)
            else:
                # a new run -- which is also how a big fill from the OTHER side
                # breaks the old one (SEQ_STRICT = false: only a big opposite
                # fill breaks; a small fill of either side, or one with no
                # side, is ignored below and the run stands)
                run = self._run = {"side": side, "fills": [f], "ev": None}
            n = len(run["fills"])
            if n == RUN_N:
                fs = run["fills"]
                word = "buys" if side == 1 else "sells"
                unit = "lots" if self.lot else "units"
                ev = {"t": t, "kind": "run", "side": side, "n": n, "from_t": fs[0]["ltt"], "to_t": t,
                      "qty": self._lots(sum(x["q"] for x in fs)), "thr": self._lots(thr), "p": self._wavg_p(fs),
                      "src": "ux", "tag": "I", "unit": unit,
                      "why": f"{n} {word} ≥ {self._lots(thr):g} {unit} inside {RUN_GAP_S} s — each in the top decile of the last 20 min"}
                run["ev"] = ev
                self.events.append(ev)
                fired = ev
            elif n > RUN_N and run["ev"] is not None:
                ev = run["ev"]
                ev["n"], ev["to_t"], ev["t"] = n, t, t
                ev["qty"] = self._lots(sum(x["q"] for x in run["fills"]))
                ev["p"] = self._wavg_p(run["fills"])
        self._win.append((t, q))
        insort(self._sizes, q)
        return fired
