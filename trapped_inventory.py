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
        # The book that ALREADY EXISTED when this ledger started watching --
        # the first observation's OI, before any delta could be attributed.
        # This is the inventory whose basis we can never know: built on an
        # earlier day, or this morning before a late start. It is the
        # denominator `confidence()` was always missing.
        self.unwatched: Optional[float] = None
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
        """How much of the book the ledger actually watched build.

        "none"    -- no basis, or the tracked inventory has fully drained.
        "low"     -- under half the book was watched being built; `basis` and
                     therefore `pain` describe a minority of the position.
        "session" -- at least half was watched.

        THE ARITHMETIC WAS DEAD UNTIL 2026-08-25 and this is the fix, recorded
        because the field it feeds shipped wrong for a few hours. It read
        `seen_build < self.size * 0.5`. But `seen_build` only ever GROWS
        (`feed` adds every build to it) while `size` is REDUCED on every exit,
        so `seen_build >= size` is an invariant and `seen_build < size * 0.5`
        could not be true unless size were negative. `"low"` was unreachable:
        every ledger with a basis reported `"session"`, so the warmap's
        `ce_conf`/`pe_conf` always claimed full coverage -- exactly the
        overstatement the field was added to prevent.

        THE REAL DENOMINATOR is the whole book, not the part we tracked.
        `size` was never a measure of ignorance -- it is our own bookkeeping,
        so comparing our observations against it could only ever say
        "we saw what we saw". What we do NOT know is the inventory that was
        already sitting there on the first observation: built on an earlier
        day, or this morning before an 11:00 start. That is `unwatched`, and
        the honest ratio is watched / (watched + unwatched).

        Worked, with the operator's own case: an 11:00 start on a 9.0M CE wall
        that adds 0.5M by the close reads 0.5 / 9.5 = 5% -> "low", and the
        basis is correctly flagged as describing a twentieth of the wall. The
        same wall watched from 09:15, listed fresh that morning, reads
        1.0 / 1.0 = 100% -> "session".

        Deliberately cautious on churn: a book that builds and unwinds
        repeatedly accumulates `seen_build` without the pre-existing tranche
        ever becoming knowable, so it stays "low" until watched flow genuinely
        outweighs the opening book. Overstating coverage is the failure that
        just happened; understating it costs nothing but a caveat.
        """
        if self.basis is None or self.size <= 0:
            return "none"
        if self.unwatched is None:
            return "none"          # never saw a first observation: nothing to divide by
        total = self.unwatched + self.seen_build
        if total <= 0:
            return "none"
        return "low" if self.seen_build < total * 0.5 else "session"

    # ── feed ────────────────────────────────────────────────────────────
    def feed(self, t: str, oi: Optional[float], price: Optional[float]) -> Optional[FlowEvent]:
        """One observation. oi/price may be None (sparse fixture, gappy feed) --
        the ledger simply waits; it never interpolates."""
        if oi is None or price is None:
            return None
        if self._last is None:
            # The book as it stood before we could attribute anything to it.
            # Whatever is here was built at prices this ledger never saw, so
            # it is permanently outside `basis` -- which is precisely what
            # `confidence()` needs to weigh its own coverage against.
            self.unwatched = float(oi)
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
