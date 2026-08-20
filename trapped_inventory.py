"""trapped_inventory.py -- operator object #1: the fuel gauge.

WHAT IT ANSWERS. Not "where is the OI" (any chain shows that) but "is the
inventory behind that OI comfortable or in pain" -- because pain is what
converts positions into forced flow, and forced flow is the only edge this
whole stack trades. On 2026-08-19 the 24100CE wall at day-high OI read as a
ceiling on every conventional screen; it was fuel, and it detonated 43 points
in thirteen minutes. This module exists so that misread cannot happen silently
again.

METHOD. A volume-weighted basis ledger over (t, oi, price) observations:
  * dOI > 0: new inventory joins at current price -> basis reweights.
  * dOI < 0: inventory leaves; basis unchanged (proportional-decay assumption:
    exits are drawn evenly from the book, since we cannot see which lots left).
Pain is then signed distance between price and basis, per side:
  * long side underwater when basis > price;  short side when price > basis.
For FUTURES both sides exist symmetrically (every contract has one of each),
so the ledger is side-neutral and reports both pains; the TRAPPED side is
whichever is positive. For OPTIONS the ledger is instantiated per contract
with side="short" by default -- the standing structural assumption that
near-ATM intraday OI builds are writer-dominated.

ASSUMPTIONS, STATED [I]:
  1. Proportional decay on exits (unknowable which lots closed).
  2. Session anchoring: the ledger sees only intraday builds. Overnight
     inventory has an invisible basis. In expiry week much of the book
     predates today -- treat absolute basis as an estimate, treat CHANGES in
     pain and the classify() stream as the reliable layer.
  3. Options: writer-dominated builds near ATM. Right on average, wrong on
     specific strikes on specific days.

KILL CONDITION (declared at birth, per plan): if after ~30 scored sessions
high-pain readings do not precede forced-flow events at better than base
rate, this module is retired. It is forward-logged from day one; it gates
nothing until its scoreboard line earns it.

Pure computation, stdlib only, no I/O -- TapeMap module discipline.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class FlowEvent:
    """One classified (dOI, dPrice) observation."""
    t: str
    d_oi: float
    d_price: float
    kind: str            # building | forced_exit | profit_exit | flat
    trapped_side: str    # long | short | none  (side in pain when it happened)
    pain: float          # pain of the trapped side at classification time
    tag: str = "M"       # the flow arithmetic is measured; basis behind it is [I]


class Ledger:
    """Volume-weighted basis + pain for one instrument's open interest."""

    def __init__(self, side: str = "both", min_flow: float = 0.0):
        # side: "both" for futures, "short"/"long" for a single option book.
        assert side in ("both", "short", "long")
        self.side = side
        self.min_flow = min_flow          # ignore |dOI| below this (noise floor)
        self.size: float = 0.0            # inventory the ledger has SEEN built
        self.basis: Optional[float] = None
        self.seen_build: float = 0.0      # cumulative builds (for confidence)
        self.events: List[FlowEvent] = []
        self._last: Optional[tuple] = None  # (t, oi, price)

    # ── pain ────────────────────────────────────────────────────────────
    def pain_long(self, price: float) -> Optional[float]:
        return None if self.basis is None else self.basis - price

    def pain_short(self, price: float) -> Optional[float]:
        return None if self.basis is None else price - self.basis

    def trapped(self, price: float) -> tuple:
        """(side, pain) of whoever is underwater; ('none', 0) if nobody/unknown."""
        if self.basis is None:
            return ("none", 0.0)
        pl, ps = self.pain_long(price), self.pain_short(price)
        if self.side == "long":
            return ("long", pl) if pl > 0 else ("none", 0.0)
        if self.side == "short":
            return ("short", ps) if ps > 0 else ("none", 0.0)
        return ("long", pl) if pl > 0 else ("short", ps) if ps > 0 else ("none", 0.0)

    def confidence(self) -> str:
        """How much of the current book the ledger actually watched build."""
        if self.basis is None or self.size <= 0:
            return "none"
        return "low" if self.seen_build < self.size * 0.5 else "session"

    # ── feed ────────────────────────────────────────────────────────────
    def feed(self, t: str, oi: Optional[float], price: Optional[float]) -> Optional[FlowEvent]:
        """One observation. oi/price may be None (sparse fixture, gappy feed) --
        the ledger simply waits; it never interpolates."""
        if oi is None or price is None:
            return None
        if self._last is None:
            self._last = (t, oi, price)
            return None
        _, oi0, px0 = self._last
        d_oi, d_px = oi - oi0, price - px0
        self._last = (t, oi, price)
        if abs(d_oi) <= self.min_flow:
            return self._emit(t, d_oi, d_px, "flat", price)

        if d_oi > 0:
            # build joins at (approximately) the traversed price midpoint
            join = (price + px0) / 2.0
            if self.basis is None:
                self.basis, self.size = join, d_oi
            else:
                self.basis = (self.basis * self.size + join * d_oi) / (self.size + d_oi)
                self.size += d_oi
            self.seen_build += d_oi
            return self._emit(t, d_oi, d_px, "building", price)

        # d_oi < 0 : inventory leaving. Who left tells the story.
        self.size = max(self.size + d_oi, 0.0)
        side, pain = self.trapped(price)
        kind = "forced_exit" if pain > 0 else "profit_exit"
        return self._emit(t, d_oi, d_px, kind, price)

    def _emit(self, t, d_oi, d_px, kind, price) -> FlowEvent:
        side, pain = self.trapped(price)
        ev = FlowEvent(t=t, d_oi=d_oi, d_price=d_px, kind=kind,
                       trapped_side=side, pain=round(pain, 2))
        self.events.append(ev)
        return ev

    # ── panel payload ───────────────────────────────────────────────────
    def snapshot(self, price: float) -> dict:
        side, pain = self.trapped(price)
        return {"basis": None if self.basis is None else round(self.basis, 2),
                "size": round(self.size, 0),
                "trapped_side": side, "pain": round(pain, 2),
                "confidence": self.confidence(), "tag": "I"}


def drain_rate(events: List[FlowEvent], window: int = 5) -> float:
    """Forced-exit flow over the last `window` events: how fast the trapped
    side is leaving. The forcing detector's third condition reads this."""
    recent = events[-window:]
    return sum(-e.d_oi for e in recent if e.kind == "forced_exit")
