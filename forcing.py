"""forcing.py -- operator object #2: the moment pain converts to forced action.

The S2 checklist as code. Three conditions, ALL required, evaluated per bar:

  FUEL      trapped inventory exists and its pain ranks high against the
            session's own pain distribution        (from trapped_inventory)
  IGNITION  bar volume ranks extreme against the session-so-far
            distribution (percentile, self-calibrating -- no absolute
            thresholds, per TapeMap doctrine)
  DRAIN     the trapped side is actually leaving: forced_exit flow ranks
            high vs session-so-far drain distribution

SEQUENCE, NOT STATE (learned from the fixture itself): the covering that
produces the DRAIN print also relieves the pain that was the FUEL, so the
three conditions never co-occur on one bar. FUEL+IGNITION therefore ARM a
window (ARM_BARS); DRAIN confirming inside that window is the FIRE. The
trapped side is captured AT ARMING -- by confirmation time it has already
been rescued by its own exit. 2/3 alone is never a signal: "fakes die here."

Self-calibration: every rank is percentile-so-far within the session, so the
same code runs on NIFTY, BANKNIFTY, SENSEX or a single option leg without
retuning. The percentile cutoffs themselves (FUEL_P, IGN_P, DRAIN_P) are
tuned constants and are declared as such -- they are the [I] layer here, and
they are what forward scoring will judge.

Forward-logged from day one; gates nothing until its line earns it.
Pure computation, stdlib only, no I/O.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
from trapped_inventory import Ledger, drain_rate

FUEL_P, IGN_P, DRAIN_P = 0.80, 0.97, 0.90     # tuned constants, [I]
ARM_BARS = 4                                   # confirmation window, [I]
MIN_HISTORY = 12                               # bars before percentiles mean anything


def _pctl(x: float, hist: List[float]) -> float:
    """Percentile-so-far of x within hist (0..1). Empty hist -> 0."""
    if not hist:
        return 0.0
    return sum(1 for h in hist if h < x) / len(hist)


@dataclass
class Verdict:
    t: str
    state: str                 # QUIET | ARMING | FIRE
    conditions: dict           # each: {"ok": bool, "rank": float, "value": float}
    direction: Optional[str]   # long | short | None
    note: str


class ForcingDetector:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self._vols: List[float] = []
        self._pains: List[float] = []
        self._drains: List[float] = []
        self._armed_left: int = 0          # bars remaining in the confirm window
        self._armed_side: str = "none"     # trapped side captured at arming

    def on_bar(self, t: str, oi: Optional[float], close: Optional[float],
               volume: Optional[float]) -> Verdict:
        ev = self.ledger.feed(t, oi, close)

        # ranks are computed against history EXCLUDING this bar, then recorded
        vol_rank = _pctl(volume, self._vols) if volume is not None else 0.0
        side, pain = self.ledger.trapped(close) if close is not None else ("none", 0.0)
        pain_rank = _pctl(pain, self._pains) if pain > 0 else 0.0
        dr = drain_rate(self.ledger.events)
        drain_rank = _pctl(dr, self._drains) if dr > 0 else 0.0

        if volume is not None: self._vols.append(volume)
        self._pains.append(max(pain, 0.0))
        self._drains.append(max(dr, 0.0))

        warm = len(self._vols) >= MIN_HISTORY
        conds = {
            "fuel":     {"ok": warm and side != "none" and pain_rank >= FUEL_P,
                         "rank": round(pain_rank, 2), "value": round(pain, 2)},
            "ignition": {"ok": warm and vol_rank >= IGN_P,
                         "rank": round(vol_rank, 2),
                         "value": volume if volume is not None else 0},
            "drain":    {"ok": warm and drain_rank >= DRAIN_P,
                         "rank": round(drain_rank, 2), "value": round(dr, 0)},
        }
        if conds["fuel"]["ok"] and conds["ignition"]["ok"]:
            self._armed_left = ARM_BARS
            self._armed_side = side

        if conds["drain"]["ok"] and (self._armed_left > 0 or
                                     (conds["fuel"]["ok"] and conds["ignition"]["ok"])):
            trapped = self._armed_side if self._armed_side != "none" else side
            direction = "long" if trapped == "short" else "short"
            state = "FIRE"
            note = f"drain confirmed inside armed window -- forced {trapped}-side exit, go with the covering"
            self._armed_left, self._armed_side = 0, "none"
        elif self._armed_left > 0:
            state, direction = "ARMING", None
            note = "fuel+ignition armed -- drain not confirmed; fakes die here, wait"
            self._armed_left -= 1
        else:
            state, direction, note = "QUIET", None, ""
        return Verdict(t=t, state=state, conditions=conds,
                       direction=direction, note=note)
