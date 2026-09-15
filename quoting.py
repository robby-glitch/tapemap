"""quoting.py -- the quoting layer: how the paper desk gets filled.

THE POINT. This operator POSTS rather than crosses -- the bid-ask is revenue,
not cost, and forced flow is the customer (crowd doctrine, rule 8). So the
paper desk's default entry is a RESTING order that waits to be crossed, and
every fill records whether it was maker (posted, paid the spread TO us) or
taker (we crossed, urgency bought). The daily review then shows what the
posting discipline actually earned versus what urgency actually cost --
a number no signal module can produce.

THE FILL MODEL IS [I] AND OPTIMISTIC, SAID OUT LOUD. Fills are simulated
against ~10s chain quotes: a resting SELL fills when the market bid reaches
it, a resting BUY when the market ask falls to it, always at OUR price. Real
fills are worse in two ways this model cannot see: queue position (we assume
we are first at our price) and everything that happens between snapshots.
Therefore PAPER MAKER P&L IS AN UPPER BOUND on real maker capture, and any
review of this book must say so. Taker fills (at the touch, plus nothing)
are closer to honest since this size is small against index-option depth.

NO ORDER PATH, EVER. Nothing here talks to a broker, and nothing ever will --
these "orders" are dict entries matched against quotes we already receive.
The house law (CLAUDE.md rule 10) binds this file like every other.

Pure computation, stdlib only, no I/O. trader.py owns the disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional, Tuple

# A resting quote that has not been touched in this many on_quotes passes is
# stale intent and is cancelled with a reason -- a quote from a thesis that
# died must not fill an hour later. [I]
DEFAULT_TTL = 30


@dataclass
class Quote:
    qid: str
    idx: str
    strike: float
    right: str                   # CE | PE
    side: str                    # BUY | SELL
    px: float
    qty: int                     # units
    strategy: str
    posted_ts: str
    ttl: int = DEFAULT_TTL
    age: int = 0
    # carried through to the fill so the trader can build the leg
    context: dict = field(default_factory=dict)


@dataclass
class Fill:
    qid: str
    idx: str
    strike: float
    right: str
    side: str
    px: float
    qty: int
    strategy: str
    ts: str
    mode: str                    # maker | taker
    context: dict = field(default_factory=dict)


class Quoter:
    """One per paper desk. Post, cancel, and match against chain quotes."""

    def __init__(self):
        self.resting: List[Quote] = []
        self._next = 1
        self.expired: int = 0

    def post(self, idx: str, strike: float, right: str, side: str, px: float,
             qty: int, strategy: str, ts: str, ttl: int = DEFAULT_TTL,
             context: Optional[dict] = None) -> Quote:
        q = Quote(qid=f"Q{self._next}", idx=idx, strike=strike, right=right,
                  side=side, px=px, qty=qty, strategy=strategy, posted_ts=ts,
                  ttl=ttl, context=context or {})
        self._next += 1
        self.resting.append(q)
        return q

    def cancel(self, pred: Callable[[Quote], bool]) -> int:
        """Cancel every resting quote pred matches; returns how many."""
        n0 = len(self.resting)
        self.resting = [q for q in self.resting if not pred(q)]
        return n0 - len(self.resting)

    def on_quotes(self, idx: str, by_k: Dict[tuple, dict],
                  ts: str) -> List[Fill]:
        """One chain snapshot for `idx` -> maker fills. A SELL fills when the
        bid reaches our price; a BUY when the ask falls to it. At our price,
        whole quantity -- the optimistic model the docstring declares."""
        fills, keep = [], []
        for q in self.resting:
            if q.idx != idx:
                keep.append(q)
                continue
            leg = by_k.get((q.strike, q.right)) or {}
            bid, ask = leg.get("bid"), leg.get("ask")
            crossed = ((q.side == "SELL" and bid is not None and bid >= q.px)
                       or (q.side == "BUY" and ask is not None and ask <= q.px))
            if crossed:
                fills.append(Fill(qid=q.qid, idx=q.idx, strike=q.strike,
                                  right=q.right, side=q.side, px=q.px,
                                  qty=q.qty, strategy=q.strategy, ts=ts,
                                  mode="maker", context=q.context))
                continue
            q.age += 1
            if q.age >= q.ttl:
                self.expired += 1        # stale intent dies, counted
                continue
            keep.append(q)
        self.resting = keep
        return fills

    def take(self, idx: str, strike: float, right: str, side: str, qty: int,
             strategy: str, by_k: Dict[tuple, dict], ts: str,
             context: Optional[dict] = None
             ) -> Tuple[Optional[Fill], Optional[str]]:
        """Cross the spread now: BUY at the ask, SELL at the bid. Returns
        (fill, why_not) -- a one-sided or absent book refuses with a reason,
        never fills at an invented price."""
        leg = by_k.get((strike, right)) or {}
        px = leg.get("ask") if side == "BUY" else leg.get("bid")
        if not px:
            return None, (f"{strike:.0f} {right}: no "
                          f"{'ask' if side == 'BUY' else 'bid'} to cross")
        f = Fill(qid=f"T{self._next}", idx=idx, strike=strike, right=right,
                 side=side, px=px, qty=qty, strategy=strategy, ts=ts,
                 mode="taker", context=context or {})
        self._next += 1
        return f, None

    def state(self) -> dict:
        return {"resting": [asdict(q) for q in self.resting],
                "expired": self.expired}
