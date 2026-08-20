"""pools.py -- the terrain: where size rests, and where there is nothing.

WHAT IT ANSWERS. Price is not a thing that moves; price is where the last
trade happened. A trade needs an aggressor to meet a resting order, so price
can only travel where resting orders are, and it travels FASTEST where they
are not. That makes the book a map: shelves where price stalls, and gaps where
it gets from one shelf to the next in a hurry.

This is the folklore's "liquidity to liquidity" with the mysticism removed and
the traffic left out. It says where the terrain is. It says nothing about which
way anything is going -- that is `fuse` and `regime`, working off the
detectors. A map with no traffic data is astrology with better graphics, and
this module is deliberately only the map.

WHAT IT MEASURES, all of it arithmetic on one ladder:

  SHELF    a level holding far more than the book's own typical size, so price
           arriving there meets something. Ranked against the ladder it is in,
           never an absolute -- 780 lots is a wall on the future and nothing on
           an ATM call.
  VACUUM   a price GAP between adjacent levels much wider than that book's own
           typical gap. Nothing rests in it, so price crosses it fast. The
           Aug-19 retrace fell 40 points on almost no aggressive selling
           because there were no bids above 24,140: gravity through a vacuum,
           not conviction.

**WALL vs CLUSTER NEEDS THE ORDER COUNT, AND ONLY ONE FEED HAS IT.** A shelf
says size is resting; it does NOT say whether that is one algorithm's wall or
eighty retail limit orders on a round number. Those are different objects --
one gets defended, the other evaporates when touched. The difference is
visible only in the ORDER COUNT per level. Upstox sends qty and price;
**Kite's 184-byte packet sends `orders` too**, which is why PaperDesk's tap is
still worth running.

So `orders` is an OPTIONAL argument. Supply it and `kind` is answered; leave it
out and `kind` stays None with a stated reason, exactly as before. Nothing is
ever guessed from size alone -- 20,000 lots can be one order or two hundred,
and the two mean opposite things.

**AND IT ONLY ANSWERS THE UNAMBIGUOUS ENDS.** A handful of orders holding real
size is a wall; a crowd of small ones is a crowd. In between it declines --
`kind` None, `why` saying so. A classifier that forced every level into one of
two boxes would be most confident exactly where it has least reason to be.

Also deliberately absent: stop-cluster estimation. Stops are not in the book --
they are a hypothesis about where other people put their invalidation, and
while that hypothesis is usually right it is an `[I]` with no observable to
check inside this module. It belongs on the console as a tagged overlay, not
smuggled in here beside measured levels.

VISIBLE DEPTH ONLY. Five levels a side is a keyhole; the exchange's real book
is far deeper, and `tbq`/`tsq` say so. A ladder with no vacuum in it may simply
be a book whose gaps start past level five.

Pure computation, stdlib only, no I/O. Emits measurements `[M]`, except
`kind`, which is None because it cannot be measured from this feed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

# A level is a SHELF at this multiple of the ladder's own median size, and a
# gap is a VACUUM at this multiple of the ladder's own median gap. Ratios
# against the book itself, so they carry across instruments -- but the
# multiples are the [I] layer and are what forward scoring judges.
SHELF_X = 2.5
VACUUM_X = 2.5
MIN_LEVELS = 3          # fewer than this and "typical" has no meaning

# Wall vs cluster, when order counts are available. The gap between them is
# deliberate: levels landing inside it are left unclassified rather than
# forced. [I] -- these two numbers are what forward scoring judges.
WALL_ORDERS = 3         # at or below this many orders holding a shelf: a wall
CLUSTER_ORDERS = 20     # at or above this many: a crowd


@dataclass
class Pool:
    """One feature of the terrain on one side of one book."""
    side: str                  # bid | ask
    kind_of: str               # shelf | vacuum
    price: float               # the shelf's price, or the low edge of the gap
    to_price: Optional[float]  # vacuum only: the far edge
    qty: Optional[float]       # shelf only: what rests there
    times: float               # multiple of the book's own median
    kind: Optional[str] = None  # wall | cluster -- only when orders are known
    orders: Optional[int] = None   # participants holding it, from Kite's tap
    per_order: Optional[float] = None   # qty / orders
    why: str = "order counts absent from this feed; wall vs cluster unknowable"
    tag: str = "M"


def _median(xs: List[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if not n:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _classify(orders: Optional[int], qty: float):
    """(kind, why) from an order count, or (None, reason) without one."""
    if orders is None:
        return None, ("order counts absent from this feed; "
                      "wall vs cluster unknowable")
    if orders <= 0:
        return None, "order count of zero is not a count"
    if orders <= WALL_ORDERS:
        return "wall", (f"{orders} order(s) holding {qty:.0f} -- few hands, "
                        f"defended size")
    if orders >= CLUSTER_ORDERS:
        return "cluster", (f"{orders} orders averaging {qty / orders:.0f} -- "
                           f"a crowd on a level, not one participant")
    return None, (f"{orders} orders is between {WALL_ORDERS} and "
                  f"{CLUSTER_ORDERS}: neither clearly one hand nor a crowd")


def map_book(ladder: Optional[dict],
             orders: Optional[dict] = None) -> List[Pool]:
    """One `depth_ladder` result -> the shelves and vacuums it contains.

    `orders` is optional and shaped like the ladder -- {"bid": [n, n, ...],
    "ask": [...]}, aligned by index -- as PaperDesk's Kite tap supplies it.
    With it, shelves are classified wall or cluster; without it they are not.

    Empty when the book is missing, one-sided or too short for "typical" to
    mean anything. An empty list is not a flat book -- it is a book this
    module declines to describe.
    """
    if not ladder:
        return []
    out: List[Pool] = []
    for side in ("bid", "ask"):
        levels = ladder.get(side) or []
        if len(levels) < MIN_LEVELS:
            continue
        med_q = _median([l["qty"] for l in levels])
        gaps = [abs(levels[i + 1]["price"] - levels[i]["price"])
                for i in range(len(levels) - 1)]
        med_g = _median([g for g in gaps if g > 0])

        counts = (orders or {}).get(side) or []
        if med_q > 0:
            for i, l in enumerate(levels):
                if l["qty"] >= med_q * SHELF_X:
                    n = counts[i] if i < len(counts) else None
                    kind, why = _classify(n, l["qty"])
                    out.append(Pool(side=side, kind_of="shelf",
                                    price=l["price"], to_price=None,
                                    qty=l["qty"],
                                    times=round(l["qty"] / med_q, 2),
                                    kind=kind, orders=n, why=why,
                                    per_order=(round(l["qty"] / n, 1)
                                               if n else None)))
        if med_g > 0:
            for i, g in enumerate(gaps):
                if g >= med_g * VACUUM_X:
                    a, b = levels[i]["price"], levels[i + 1]["price"]
                    out.append(Pool(side=side, kind_of="vacuum",
                                    price=min(a, b), to_price=max(a, b),
                                    qty=None, times=round(g / med_g, 2)))
    return out


def summary(ladder: Optional[dict], orders: Optional[dict] = None) -> dict:
    """A compact reading for a panel: counts, and the biggest of each.

    `blind_past` is the honest footer -- the deepest prices this map can see.
    Beyond them the terrain is simply unobserved, and a panel that does not say
    so invites a reader to treat five levels as the whole book.
    """
    pools = map_book(ladder, orders)
    shelves = [p for p in pools if p.kind_of == "shelf"]
    vacs = [p for p in pools if p.kind_of == "vacuum"]
    deepest = None
    if ladder:
        edges = [(ladder.get("bid") or [{}])[-1].get("price"),
                 (ladder.get("ask") or [{}])[-1].get("price")]
        edges = [e for e in edges if e]
        deepest = (min(edges), max(edges)) if len(edges) == 2 else None
    return {"shelves": len(shelves), "vacuums": len(vacs),
            "walls": sum(1 for p in shelves if p.kind == "wall"),
            "clusters": sum(1 for p in shelves if p.kind == "cluster"),
            "orders_known": orders is not None,
            "biggest_shelf": max((p.times for p in shelves), default=None),
            "widest_vacuum": max((p.times for p in vacs), default=None),
            "blind_past": deepest,
            "pools": [p.__dict__ for p in pools]}


def orders_for(ladder: Optional[dict], books: Optional[dict],
               tol: float = 0.051) -> Optional[dict]:
    """Find the Kite book that IS this Upstox ladder, and return its counts.

    THE MATCHING PROBLEM, AND WHY IT IS SOLVED THIS WAY. Kite identifies
    instruments by numeric token; Upstox by an instrument key. Mapping one to
    the other means shipping symbol tables between two brokers and keeping
    them in step across expiries -- a whole subsystem, and one that fails
    silently on the day a contract rolls.

    It is unnecessary. Both feeds are watching the SAME EXCHANGE, so for the
    same instrument the top of book is the same two numbers. Matching on those
    needs no symbol table, no expiry logic, and cannot drift out of date: if
    the prices agree it is the same instrument, and if they do not it is not.

    Returns {"bid": [n, ...], "ask": [n, ...]} for the matching book, or None.
    None means "no Kite book matched" -- the bridge is not running, or that
    instrument is not subscribed there -- and `map_book` then leaves
    wall-vs-cluster unanswered, which is the honest result.

    `tol` defaults to just over a five-paisa tick, so a book that moved
    between the two feeds' snapshots still matches while a genuinely different
    strike cannot. AMBIGUITY IS REFUSED: if two books both match, None is
    returned rather than a coin flip -- attributing one instrument's order
    counts to another would be worse than having none.
    """
    if not ladder or not books:
        return None
    bid, ask = ladder.get("bid") or [], ladder.get("ask") or []
    if not bid or not ask:
        return None
    b0, a0 = bid[0]["price"], ask[0]["price"]

    hits = []
    for book in books.values():
        d = (book or {}).get("depth") or {}
        kb, ka = d.get("bid") or [], d.get("ask") or []
        if not kb or not ka:
            continue
        if abs(kb[0].get("price", 0) - b0) <= tol and            abs(ka[0].get("price", 0) - a0) <= tol:
            hits.append((kb, ka))
    if len(hits) != 1:
        return None                 # nothing matched, or too much did
    kb, ka = hits[0]
    return {"bid": [int(l.get("orders") or 0) for l in kb],
            "ask": [int(l.get("orders") or 0) for l in ka]}
