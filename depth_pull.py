"""depth_pull.py -- operator object #3c: liquidity leaving before the move.

WHAT IT ANSWERS. `sweep.py` reports levels being TAKEN. `absorption.py`
reports a level REFUSING to be taken. This one reports size quietly
disappearing without anyone trading against it -- a quoting engine deciding
the flow has turned toxic and stepping back. It is the market's own machinery
saying informed flow has arrived, often before price shows it.

WHY IT IS NOT ALREADY COVERED. `sweep` emits `kind="pulled"` when two or more
whole LEVELS vanish. But a side can lose most of its size without losing a
single level -- five prices still quoted, each a fraction of what it showed a
moment ago. That is invisible to a level count, and it is exactly what a
quoting engine does when it widens: keep the prices, shrink the size.

THE TEST, AND IT HAS NO KNOB IN IT. Displayed size on a side fell, and volume
across the interval was ZERO. Nothing traded, so nothing was consumed, so what
left was cancelled. That is a definition, not a threshold -- there is no
"materially" to tune. A consumer wanting "how big a pull for today" ranks
`gone` as percentile-so-far against the session, and that ranking is its `[I]`.

If volume was NOT zero, the interval is a mixture of trading and cancelling
that a snapshot cannot separate, so nothing is emitted. This module is
deliberately quiet rather than approximately right: `sweep` already owns the
intervals where trading happened.

**tbq / tsq ARE A DIFFERENT QUANTITY AND ARE PASSED THROUGH, NOT MIXED IN.**
`bid_qty`/`ask_qty` are the five quoted levels. `tbq`/`tsq` are the exchange's
totals for the whole book, far beyond what is displayed, and on the Aug-19
tape their asymmetry was the read (372k buy against 193k sell at 14:24; the
NIFTY future showed 168k/293k at capture on 2026-08-20). They ride on the
event so a consumer can watch the deep book and the quoted book diverge --
one thinning while the other does not is a different animal from both moving
together. They are never summed with the displayed figures, which would be
adding a subset to its own superset.

LIMITS. Cancels and re-posts inside one interval are invisible, so `gone` is a
NET figure and therefore a floor. A side that empties because its levels went
unquoted appears here as size lost and in `sweep` as levels lost; that is the
same event seen twice, deliberately, because neither view implies the other.
And zero volume is only evidence of no trading in THIS instrument -- a hedge
leg trading elsewhere leaves no mark here.

Pure computation, stdlib only, no I/O. Emits measurements `[M]`.
Forward-logged from day one; gates nothing until its line earns it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Pull:
    """One interval where quoted size left a side and nothing traded."""
    t: str
    side: str                  # bid | ask -- the side that thinned
    gone: float                # displayed size that disappeared (net)
    was: float                 # displayed size on that side before
    now: float                 # displayed size on that side after
    frac: float                # gone / was -- how much of the side left
    levels_lost: int           # quoted levels that also vanished, often 0
    tbq: Optional[float]       # exchange-wide totals, passed through
    tsq: Optional[float]
    tag: str = "M"


def between(prev: Optional[dict], now: Optional[dict], t: str = "",
            prev_vtt: Optional[float] = None,
            vtt: Optional[float] = None) -> Optional[Pull]:
    """Two consecutive ladders -> the pull between them, or None.

    Returns None unless volume across the interval was exactly zero and one
    side lost displayed size. Both are required; see the docstring on why a
    mixed interval is left to `sweep`.
    """
    if not prev or not now:
        return None
    if prev_vtt is None or vtt is None:
        return None                      # cannot claim "nothing traded"
    if vtt != prev_vtt:
        return None                      # something traded; not purely a pull

    best = None
    for side in ("bid", "ask"):
        was = prev.get(f"{side}_qty") or 0.0
        is_ = now.get(f"{side}_qty") or 0.0
        gone = was - is_
        if gone <= 0 or was <= 0:
            continue
        lost = max(0, len(prev.get(side) or []) - len(now.get(side) or []))
        cand = Pull(t=t, side=side, gone=gone, was=was, now=is_,
                    frac=round(gone / was, 4), levels_lost=lost,
                    tbq=now.get("tbq"), tsq=now.get("tsq"))
        if best is None or cand.gone > best.gone:
            best = cand
    return best


class DepthPullDetector:
    """Holds the previous ladder. One per instrument -- see `sweep`."""

    def __init__(self):
        self._prev: Optional[dict] = None
        self._prev_vtt: Optional[float] = None
        self.events: List[Pull] = []

    def on_snapshot(self, t: str, ladder: Optional[dict],
                    vtt: Optional[float] = None) -> Optional[Pull]:
        ev = between(self._prev, ladder, t, self._prev_vtt, vtt)
        self._prev, self._prev_vtt = ladder, vtt
        if ev:
            self.events.append(ev)
        return ev
