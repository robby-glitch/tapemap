"""sweep.py -- operator object #3a: one aggressive order eating several levels.

WHAT IT ANSWERS. Not "was there volume" -- any bar shows that -- but "did
someone cross the spread hard enough to take out more than the top of book",
which is the earliest tradeable tell the Aug-19 tape produced. The 14:29-14:31
delta flip preceded the 14:33 detonation by four minutes; at bar resolution it
was invisible until the candle closed. A sweep is that flip, measured on the
book rather than inferred from the candle afterwards.

METHOD. Two consecutive depth ladders, nothing else:

  * best ask ROSE   -> every prior ask level priced below the new best ask
                       stopped being there.  Offers were lifted: a BUY sweep.
  * best bid FELL   -> every prior bid level priced above the new best bid
                       stopped being there.  Bids were hit: a SELL sweep.

That definition is naturally one-sided, which is worth checking rather than
trusting: when price walks up, the bid side walks up with it, and a bid that
moved UP never satisfies "priced above the new best bid". So a clean sweep
reports levels on one side and zero on the other, and a frame reporting both
is a book that gapped, not an aggressor.

**GONE IS NOT THE SAME AS TRADED, AND THIS IS THE WHOLE DISCRIMINATION.** A
level can stop being there because someone bought it, or because the maker
cancelled it. Those are opposite readings -- the first is aggression arriving,
the second is liquidity leaving before a move -- and they look identical in
the ladder alone. The tie-breaker is `vtt`: trades happened, or they did not.
So this module reports `kind`:

    "swept"    levels gone AND volume traded across the interval
    "pulled"   levels gone AND no volume at all -- quotes withdrawn
    "unknown"  levels gone AND vtt was not supplied, so it cannot be told

`pulled` is not a failed sweep. It is the depth-pull read -- market makers
stepping back -- and it is emitted rather than discarded because on Aug-19 the
useful thing at 14:24 was the book thinning, not the print that followed.

**`kind` IS BINARY AND REALITY IS A MIXTURE, SO READ `traded` AGAINST `qty`.**
Measured live 2026-08-20 10:10-10:12 on the NIFTY future: every displayed
quantity and every volume delta came back an exact multiple of 65 -- 130, 195,
325, 845, 975, 1040, 3250, 8320 -- so `vtt` and depth `qty` are in the SAME
unit and the two are directly comparable. That was an open question when this
was written and it is now answered, which matters because:

    traded >= qty   the standing size was taken, and then some -- hidden
                    size, or a level refilled and taken again inside the
                    interval
    traded <  qty   part of what vanished was CANCELLED, not bought

One real frame from that run: `sell levels=3 qty=845 traded=325`. It is
reported `swept` because something traded, but under a third of the book that
disappeared was actually consumed -- mostly a pull wearing a sweep's label.
The ratio is deliberately NOT computed here and NOT turned into a third
`kind`, because any cutoff dividing "mostly swept" from "mostly pulled" would
be a tuned constant, and this module has none to defend. Both numbers are
emitted; the consumer that needs the distinction can divide, and its cutoff
is then its own `[I]` to be scored.

OBSERVED RATE, so a future reader knows what normal looks like: 180 polls at
0.5s over a quiet 90 seconds produced 8 events, all `swept`, 5 buy and 3 sell.
Roughly one every eleven seconds on a mid-morning tape. A detector firing on
most polls is broken; one firing never has probably lost its `vtt`.

WHAT IT CANNOT SEE, ALL THREE OF WHICH ARE THE SNAPSHOT'S FAULT, NOT THE
LOGIC'S:

  1. **Two sweeps inside one interval read as one.** The feed batches; this
     compares snapshots, not orders. Magnitudes are therefore floors.
  2. **A level swept and instantly refilled reads as no sweep at all**, because
     the best price came back to where it was. That is the refill detector's
     job, not this one's, and it is why a quiet `None` here must never be read
     as "nothing happened".
  3. **`qty` is the size that was DISPLAYED.** Icebergs rest larger than they
     show, so real consumption can exceed it.

WHY NO THRESHOLD, AND WHY NO RANK. `MIN_LEVELS` is a definition -- taking the
whole top level is an ordinary fill, taking two is a sweep -- not a tuned
constant, so it is not the `[I]` layer and forward scoring has nothing to
judge in it. And nothing here ranks its own output: "how big for today" is
percentile-so-far against the session, which is `engine.Rank`'s job at the
consumer. A detector that both measures and grades its own measurement is two
modules wearing one name.

Pure computation, stdlib only, no I/O -- TapeMap module discipline. Emits
measurements, tagged `[M]`: every field is a difference between two numbers
that arrived on the wire. The reading laid on top ("ignition") belongs to the
fusion layer and is `[I]`.

Forward-logged from day one; gates nothing until its line earns it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

# A sweep takes MORE than the top of book. One level is an ordinary fill.
# This is the definition of the word, not a tuning knob -- see the docstring.
MIN_LEVELS = 2


@dataclass
class Sweep:
    """One interval's worth of book consumed, or withdrawn.

    **`side` IS INFERRED AND THE REST IS NOT, WHICH IS WHY THERE ARE TWO TAGS.**
    `levels`, `qty`, `from_px`, `to_px` and `traded` are differences taken off
    the wire -- levels that stopped being there, the size that had stood on
    them, the volume across the interval. Those are `[M]`.

    `side` is not. `traded` comes from `vtt`, which is an INSTRUMENT TOTAL and
    carries no direction at all, so the side is picked from whichever ladder
    lost more -- a reading of the book, not a reading of the trades. Cancel the
    asks while sell aggression hits the bid and this reports `buy`. It is
    therefore `[I]`, and `side_tag` says so on every row.

    Why not infer it properly from `ltp` (the quote rule): attributing a whole
    interval to the side implied by its LAST print scores p^2+(1-p)^2 of the
    volume correctly -- 50% on a balanced interval, a coin flip, and better
    than chance only when the interval is already lopsided, which is exactly
    when the ladder already says so. It would carry information only where it
    is redundant. Worse, a per-side VOLUME is a magnitude, and this project's
    footprint rule permits shape and sequence and never magnitude.

    `opp_levels`/`opp_qty` are the other side's loss, kept rather than thrown
    away, so a reader can see how one-sided the interval actually was instead
    of taking `side` on trust.
    """
    t: str
    side: str                  # buy  = offers lifted | sell = bids hit  [I]
    kind: str                  # swept | pulled | unknown
    levels: int                # resting levels that stopped being there
    qty: float                 # displayed size that had been standing on them
    traded: Optional[float]    # volume across the interval, None if unknown
    from_px: float             # best price on that side before
    to_px: float               # best price on that side after
    opp_levels: int = 0        # levels the OTHER side lost in the same interval
    opp_qty: float = 0.0       # and the size that had stood on them
    tag: str = "M"             # levels / qty / traded / prices
    side_tag: str = "I"        # `side` alone -- see the class docstring


def _gone(levels: List[dict], edge: float, above: bool) -> tuple:
    """Levels priced past `edge`, and their displayed size.

    `above` picks the direction: bids that sat ABOVE the new best bid were
    hit; asks that sat BELOW the new best ask were lifted.
    """
    hit = [l for l in levels
           if (l["price"] > edge if above else l["price"] < edge)]
    return len(hit), sum(l["qty"] for l in hit)


def between(prev: Optional[dict], now: Optional[dict], t: str = "",
            prev_vtt: Optional[float] = None,
            vtt: Optional[float] = None) -> Optional[Sweep]:
    """Two consecutive `upstox_adapter.depth_ladder` results -> a Sweep, or None.

    None means "no side lost MIN_LEVELS levels", which includes the ordinary
    case of a book that simply moved a tick. It does NOT mean nothing traded --
    see limitation 2 in the module docstring.

    Either ladder being None, or empty on the relevant side, also returns
    None: a missing book is not a swept one, and an index feed has no book at
    all.
    """
    if not prev or not now:
        return None
    traded = None if (prev_vtt is None or vtt is None) else vtt - prev_vtt

    best = {}
    for side, key, above in (("buy", "ask", False), ("sell", "bid", True)):
        was, is_ = prev.get(key) or [], now.get(key) or []
        if not was or not is_:
            continue
        edge = is_[0]["price"]
        n, qty = _gone(was, edge, above)
        if n >= MIN_LEVELS:
            best[side] = (n, qty, was[0]["price"], edge)

    if not best:
        return None
    # A genuine aggressor is one-sided; if both moved, the larger side is the
    # one that was consumed and the other is the book following it. That is an
    # ASSUMPTION about the book, not an observation of the trades -- hence
    # side_tag "I" on the result.
    side = max(best, key=lambda s: (best[s][0], best[s][1]))
    n, qty, from_px, to_px = best[side]
    # The loser is KEPT, not discarded. A two-sided collapse and a clean
    # one-sided sweep produce the same `side` today, and only these two fields
    # tell them apart -- which is what `fuse` needs to stop counting a
    # coin-flip row at full strength.
    opp = [v for s, v in best.items() if s != side]
    opp_levels, opp_qty = (opp[0][0], opp[0][1]) if opp else (0, 0.0)

    if traded is None:
        kind = "unknown"
    elif traded > 0:
        kind = "swept"
    else:
        kind = "pulled"
    return Sweep(t=t, side=side, kind=kind, levels=n, qty=qty, traded=traded,
                 from_px=from_px, to_px=to_px,
                 opp_levels=opp_levels, opp_qty=opp_qty)


class SweepDetector:
    """Holds the previous ladder so a caller can just feed it snapshots.

    One per instrument -- the state is that instrument's last book, and
    comparing NIFTY's ladder against BANKNIFTY's would report a sweep of the
    entire distance between them.
    """

    def __init__(self):
        self._prev: Optional[dict] = None
        self._prev_vtt: Optional[float] = None
        self.events: List[Sweep] = []

    def on_snapshot(self, t: str, ladder: Optional[dict],
                    vtt: Optional[float] = None) -> Optional[Sweep]:
        """Feed the newest ladder; get the sweep since the last one, or None.

        A None ladder is REMEMBERED as None rather than skipped, so the two
        live frames either side of a dead or absent book are never compared as
        though they were consecutive.
        """
        ev = between(self._prev, ladder, t, self._prev_vtt, vtt)
        self._prev, self._prev_vtt = ladder, vtt
        if ev:
            self.events.append(ev)
        return ev
