"""sequence.py -- war-map object D: the playbook machine. SHADOW. Gates nothing.

THE THESIS AS A STATE MACHINE, one per stable level per index:

    IDLE -> APPROACH -> DWELL -> BREAK -> RUN -> (HIT | FAILED)
                          \\-> REJECT -> IDLE

APPROACH: spot inside the approach zone (APPROACH_K x band) of the level.
DWELL:    dwell.py's detector active at this level -- the trap being set.
REJECT:   spot leaves the approach zone back the way it came.
BREAK:    spot through the level by more than one band, to the far side.
RUN:      after a break, the named target is the next reaction point in the
          break direction (hunt.py's runway target). Resolves HIT when spot
          reaches the target's band, FAILED when it comes back through the
          broken level. Both resolutions are logged; neither is an outcome
          score -- they are transitions with evidence, and the 30-session
          reading of them belongs to the operator.

EXPLICIT TIE TO THE GEARS (the plan's words): DWELL is what PIN looks like AT
a level; RUN is CASCADE with a destination. Same physics, now with an address.

ONLY STABLE LEVELS GET A MACHINE. Max pain and the walls drift with the
chain; a machine keyed to a drifting level counts phantom approaches. Levels
carry `stable` (levels.py) and unstable ones are refused here.

THE FORWARD LOG IS ITS OWN POPULATION: `data/warmap/warmap_<day>.jsonl`, one
file per day, gitignored, NEVER pooled with trigger_log.jsonl (three
quarantined populations already live there), desk_log.jsonl or the senses
rows. Same fail-soft append and injectable-clock market-hours gate as
desk_log.py. A restart mid-session starts machines at IDLE; the transitions
that follow are genuine observations picked up late, not restart noise, so
there is no baseline marker here.

KILL CONDITION (declared at birth, the regime.py precedent): after ~30
sessions, if RUN reaches its named target no more often than the opposite
level would have, the machine is DELETED rather than tuned. Nothing here
gates a setup; like regime, it must earn in the forward log the right to
ever block anything.

Stdlib only. The append is the one disk touch, fail-soft.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

APPROACH_K = 2.0        # approach zone = APPROACH_K x band  [I]
DIR = os.path.join("data", "warmap")

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)

SHADOW = True           # asserted by a test, like regime.SHADOW


def day_path(day: Optional[str] = None) -> str:
    day = day or datetime.now().strftime("%Y-%m-%d")
    return os.path.join(DIR, f"warmap_{day}.jsonl")


def market_hours(now: Optional[datetime] = None) -> bool:
    """Mon-Fri 09:15-15:30, machine clock (which IS IST -- house fact)."""
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= (now.hour, now.minute) <= MARKET_CLOSE


def _append(row: dict, path: Optional[str] = None) -> bool:
    try:
        p = path or day_path()
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return True
    except Exception:
        return False                      # never take the loop down


class LevelSeq:
    """The machine for ONE stable level."""

    def __init__(self, idx: str, kind: str, px: float):
        self.idx, self.kind, self.px = idx, kind, px
        self.state = "IDLE"
        self.approach_from: Optional[str] = None    # "above" | "below"
        self.target: Optional[dict] = None          # named on BREAK
        self.tests = 0                              # completed approach cycles
        self.last_outcome: Optional[str] = None     # REJECT | HIT | FAILED

    def _zone(self, spot: float, band: float) -> str:
        d = spot - self.px
        if abs(d) <= band:
            return "at"
        if abs(d) <= APPROACH_K * band:
            return "near"
        return "far"

    def step(self, spot: float, band: float, dwell_read: dict,
             levels: List[dict]) -> List[dict]:
        """One snapshot -> transitions fired (possibly several on one bar)."""
        out: List[dict] = []

        def go(to: str, **ev):
            out.append({"level": self.kind, "px": self.px,
                        "from": self.state, "to": to, "spot": round(spot, 1),
                        "band": round(band, 2), **ev})
            self.state = to

        zone = self._zone(spot, band)
        dw_here = (dwell_read.get("holding")
                   and (dwell_read.get("level") or {}).get("kind") == self.kind
                   and abs((dwell_read.get("level") or {}).get("px", 1e18)
                           - self.px) < 1e-6)

        if self.state == "IDLE":
            if zone in ("near", "at"):
                self.approach_from = "above" if spot > self.px else "below"
                go("APPROACH", side=self.approach_from)
        if self.state == "APPROACH":
            if dw_here and dwell_read.get("active"):
                go("DWELL",
                   oi_ce=dwell_read.get("oi_added_ce"),
                   oi_pe=dwell_read.get("oi_added_pe"),
                   crossing=dwell_read.get("buyers_crossing"))
            elif zone == "far":
                self.tests += 1
                if self._broke_through(spot, band):
                    self._name_target(spot, band, levels, go)
                else:
                    self.last_outcome = "REJECT"
                    go("REJECT", tests=self.tests)
                    self.state, self.approach_from = "IDLE", None
        if self.state == "DWELL":
            if self._broke_through(spot, band):
                self.tests += 1
                self._name_target(spot, band, levels, go)
            elif zone == "far":
                self.tests += 1
                self.last_outcome = "REJECT"
                go("REJECT", tests=self.tests, after="dwell")
                self.state, self.approach_from = "IDLE", None
        if self.state == "RUN":
            t = self.target or {}
            if t.get("px") is not None and abs(spot - t["px"]) <= band:
                self.last_outcome = "HIT"
                go("HIT", target=t)
                self.state, self.target = "IDLE", None
            elif self._back_through(spot, band):
                self.last_outcome = "FAILED"
                go("FAILED", target=t)
                self.state, self.target = "IDLE", None
        return out

    def _broke_through(self, spot: float, band: float) -> bool:
        if self.approach_from == "above":
            return spot < self.px - band
        if self.approach_from == "below":
            return spot > self.px + band
        return False

    def _back_through(self, spot: float, band: float) -> bool:
        # a run fails when spot comes back through the level it broke
        if self.approach_from == "above":      # broke DOWN, fails back above
            return spot > self.px + band
        return spot < self.px - band

    def _name_target(self, spot: float, band: float, levels: List[dict],
                     go) -> None:
        # The real band, not an epsilon: a "target" inside the current band
        # is where price already IS, and naming it would resolve HIT on the
        # same snapshot as the BREAK -- a run that never ran.
        import hunt
        up = self.approach_from == "below"     # broke upward
        t = hunt._target(spot, levels, up, band)
        self.target = ({"kind": t["kind"], "px": t["px"]} if t else None)
        go("BREAK", direction="UP" if up else "DOWN")
        go("RUN", target=self.target,
           why=("next reaction point in the break direction" if self.target
                else "no known level ahead; run is unaimed"))


class Sequencer:
    """All machines for one index, plus the forward log."""

    def __init__(self, idx: str, path: Optional[str] = None):
        self.idx = idx
        self.path = path                  # test seam; None -> day file
        self._by: Dict[str, LevelSeq] = {}
        self.written = 0
        self.failed = 0
        self.extra: dict = {}             # stamped on every row; warmap's replay sets backfill:true

    def on_snapshot(self, spot: Optional[float], band: Optional[float],
                    levels: List[dict], dwell_read: dict,
                    now: Optional[datetime] = None) -> List[dict]:
        if spot is None or band is None:
            return []
        fired: List[dict] = []
        live_keys = set()
        for l in levels or []:
            if not l.get("stable"):
                continue                  # drifting levels get no machine
            key = f"{l['kind']}@{l['px']:.1f}"
            live_keys.add(key)
            m = self._by.get(key)
            if m is None:
                m = self._by[key] = LevelSeq(self.idx, l["kind"], l["px"])
            fired.extend(m.step(spot, band, dwell_read or {}, levels))
        # Rounds slide out of the window as spot moves; their idle machines
        # go with them. A machine mid-sequence is kept -- its level is still
        # a fact even if the window walked away from it.
        for key in list(self._by):
            if key not in live_keys and self._by[key].state == "IDLE":
                del self._by[key]
        ts = (now or datetime.now()).isoformat(timespec="seconds")
        for row in fired:
            row.update({"ts": ts, "idx": self.idx, **self.extra})
            if market_hours(now):
                if _append(row, self.path):
                    self.written += 1
                else:
                    self.failed += 1
        return fired

    def state(self) -> dict:
        """Per-level machine state + test counts, for the map and the API."""
        return {key: {"state": m.state, "kind": m.kind, "px": m.px,
                      "tests": m.tests, "last_outcome": m.last_outcome,
                      "target": m.target}
                for key, m in sorted(self._by.items())}
