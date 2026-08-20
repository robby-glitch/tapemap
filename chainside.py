"""chainside.py -- the two things the book cannot see: fuel, and drain.

WHY IT EXISTS. `fuse` reads the order book and can say when aggression
arrives. It cannot say whether anyone is TRAPPED, or whether they are getting
out, because both live in open interest and open interest is not in the book --
it comes on the chain, at chain cadence. So `fuse.verdict()` takes `fuel_rank`
and `drain` as arguments and refuses to invent them. This supplies them, and it
is the last piece that lets the gate reach CASCADE from live data instead of
from a keyword argument in a test.

THE THREE CONDITIONS, FINALLY IN ONE PLACE:

    FUEL      trapped inventory exists and its pain is high for this session
              -> here, from `trapped_inventory` ledgers, one per (strike, side)
    IGNITION  aggression arriving at extreme size for this instrument
              -> `fuse`, from the book
    DRAIN     the trapped side actually leaving
              -> here, from forced-exit flow across those same ledgers

SEQUENCE, NOT STATE -- INHERITED, NOT REDISCOVERED. `forcing.py` learned on the
Aug-19 fixture that the covering which prints DRAIN also relieves the pain that
was the FUEL, so the three never co-occur on one bar. That is why `regime` arms
on fuel+ignition and fires when drain confirms, and why nothing here tries to
report all three at once. This module reports what the chain shows NOW; the
sequencing belongs to the gate.

ONE-SIDEDNESS HERE IS THE CHAIN'S, NOT THE BOOK'S. `fuse` measures which way
sweeps are arriving; this measures whether the PAIN sits on one side -- CE
writers underwater while PE writers are comfortable, or the reverse. Different
questions, and they can disagree, which is why the caller passes this one in
explicitly rather than letting `fuse` default to its own.

EVERY RANK IS PERCENTILE-SO-FAR, session-local, same discipline as everywhere
else: "pain of 9.4 points" means nothing until you know whether this session
has seen 2 or 200.

**THE LEDGER'S ASSUMPTIONS TRAVEL WITH ITS OUTPUT.** `trapped_inventory` is
explicitly `[I]`: it assumes near-ATM intraday OI builds are writer-dominated,
and it sees only intraday builds, so in expiry week much of the book predates
today and the absolute basis is an estimate -- changes and the classify stream
are the reliable layer. Everything here is therefore `[I]` too, and says so,
rather than laundering an inference into a measurement by passing it through
one more function.

Pure computation, stdlib only, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import trapped_inventory
from fuse import Rank

# --- the [I] layer ---------------------------------------------------------
DRAIN_P = 0.90      # forced-exit flow percentile that counts as draining
PAIN_SIDED = 0.70   # share of total pain on one side to call the chain lopsided
MIN_HIST = 8        # ranks below this much history are not trusted


@dataclass
class ChainRead:
    """What the chain says about fuel and drain, right now."""
    fuel_rank: Optional[float] = None       # percentile-so-far of worst pain
    worst_pain: Optional[float] = None      # points underwater, worst leg
    worst_leg: Optional[str] = None         # e.g. "24100CE"
    trapped_side: Optional[str] = None      # ce | pe -- where the pain sits
    one_sided: Optional[bool] = None        # chain pain lopsided?
    drain: bool = False
    drain_rank: Optional[float] = None
    warm: bool = False
    notes: List[str] = field(default_factory=list)
    tag: str = "I"


class ChainSide:
    """One per index. Feed it chain snapshots; it reports fuel and drain.

    A ledger per (strike, side), because a wall is built at a price and the
    pain is that price against the live premium -- aggregating first would
    average an underwater leg with a comfortable one and report neither.
    """

    def __init__(self):
        self._led: Dict[Tuple[float, str], trapped_inventory.Ledger] = {}
        self._pain_rank = Rank()
        self._drain_rank = Rank()
        self.read = ChainRead()

    def _ledger(self, strike: float, side: str) -> trapped_inventory.Ledger:
        key = (strike, side)
        if key not in self._led:
            # side="short": the standing assumption that near-ATM intraday OI
            # builds are writer-dominated. Stated in trapped_inventory, carried
            # here unchanged rather than quietly re-decided.
            self._led[key] = trapped_inventory.Ledger(side="short")
        return self._led[key]

    def on_snapshot(self, t: str, strikes: Optional[List[dict]]) -> ChainRead:
        """One normalized chain snapshot -> the fuel and drain reading.

        A snapshot with no strikes returns an EMPTY read rather than the last
        good one: a chain that stopped arriving must not look like a chain
        reporting calm, which is the rule `upstox_feed.age()` enforces one
        layer down.
        """
        if not strikes:
            self.read = ChainRead(
                notes=["no chain snapshot; fuel and drain unknown"])
            return self.read

        pains: Dict[str, float] = {}
        worst, worst_leg, worst_side = 0.0, None, None
        drained = 0.0
        for row in strikes:
            k = row.get("k")
            if k is None:
                continue
            for side in ("ce", "pe"):
                leg = row.get(side) or {}
                oi, ltp = leg.get("oi"), leg.get("ltp")
                if not oi or not ltp:
                    continue
                led = self._ledger(k, side)
                led.feed(t, float(oi), float(ltp))
                _s, pain = led.trapped(float(ltp))
                if pain > 0:
                    pains[side] = pains.get(side, 0.0) + pain
                    if pain > worst:
                        worst, worst_leg, worst_side = (
                            pain, f"{k:.0f}{side.upper()}", side)
                drained += trapped_inventory.drain_rate(led.events)

        warm = len(self._pain_rank) >= MIN_HIST
        fuel_rank = self._pain_rank.rank(worst)
        d_rank = self._drain_rank.rank(drained) if drained > 0 else 0.0

        r = ChainRead(
            fuel_rank=round(fuel_rank, 3) if warm else None,
            worst_pain=round(worst, 2) if worst else None,
            worst_leg=worst_leg, trapped_side=worst_side,
            drain=bool(warm and drained > 0 and d_rank >= DRAIN_P),
            drain_rank=round(d_rank, 3) if warm else None,
            warm=warm)
        total = sum(pains.values())
        if total > 0:
            r.one_sided = max(pains.values()) / total >= PAIN_SIDED
        if not warm:
            r.notes.append(f"only {len(self._pain_rank)} chain snapshots ranked; "
                           f"fuel and drain are not trusted below {MIN_HIST}")
        if r.worst_leg:
            r.notes.append(f"worst leg {r.worst_leg} underwater "
                           f"{r.worst_pain} pts [I: writer-dominated assumed]")
        self.read = r
        return r


class Chains:
    """One ChainSide per index, so NIFTY's pain never ranks against SENSEX's."""

    def __init__(self):
        self._by: Dict[str, ChainSide] = {}

    def for_index(self, idx: str) -> ChainSide:
        if idx not in self._by:
            self._by[idx] = ChainSide()
        return self._by[idx]

    def on_snapshot(self, idx: str, t: str,
                    strikes: Optional[List[dict]]) -> ChainRead:
        return self.for_index(idx).on_snapshot(t, strikes)
