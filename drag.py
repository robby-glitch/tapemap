"""drag.py -- the buyer's tax, measured instead of assumed.

WHAT IT ANSWERS. An option buyer is not betting on direction, they are RENTING
it. The bet is never "which way" -- it is "will the move arrive faster than the
rent burns". This puts a number on the rent:

    owed  = delta x the underlying's move        what the position should pay
    paid  = the premium's actual change          what it did pay
    drag  = owed - paid                          the tax, in points
    frac  = drag / owed                          the tax RATE

On 2026-08-19 that rate ran 33% by midday, 37% by 13:20, and 88% in the final
measured hour -- a put buyer who was exactly right about direction collected
1.15 against 9.5 owed. That is the whole argument for why this stack only buys
forced flow: at 88%, being correct is not enough.

WHY THIS EXISTS GIVEN THE NUMBER ALREADY GOT QUOTED. Every one of those
figures rested on an ASSUMED delta of 0.5. Nobody pulled the real one. The
chain already carries `delta` per leg (`chain_live._side`, from `gamma`'s
Black-76 inversion), so the assumption was never necessary -- it was just
never removed. With a real delta the number stops being "roughly a third" and
becomes a measurement, which is the difference between a talking point and
something a screen can gate on.

SIGNS ARE HANDLED BY ARITHMETIC, NOT BY CASES. A call's delta is positive, a
put's negative, so `owed = delta * d_underlying` is already right for both: a
falling index times a put's negative delta is a positive amount owed. There is
no "if put" branch here and there should not be one.

**IT REFUSES TO SPEAK WHEN THE LEG WAS ON THE WRONG SIDE.** If `owed` is zero
or negative the move went against the position, and "what fraction of the
payoff was eaten" has no answer -- there was no payoff to eat. Reporting a
drag there would produce enormous meaningless percentages on exactly the
trades that lost for an ordinary reason. None, instead.

WHAT IT IS NOT. It is not theta. `drag` bundles theta, vega and the spread
into one honest figure, and on a day when implied volatility is being marked
down -- 2026-08-19 closed with VIX DOWN on a falling index -- a real part of
it is vega, not time. Anyone reporting this as "theta" is naming one term of
a sum after the whole.

DELTA MOVES TOO, so the average of the two ends is used rather than either
one. Over a small move that is nearly exact; over a large one gamma makes it
an approximation -- and a move fast enough for gamma to matter is one where
the tax is irrelevant anyway, which is the point the whole stack turns on.

Pure computation, stdlib only, no I/O. `[M]` when the deltas are real;
None rather than a guess when they are not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Drag:
    """The tax on being right, over one interval, for one leg."""
    owed: float                # delta x underlying move, in premium points
    paid: float                # what the premium actually did
    drag: float                # owed - paid
    frac: float                # drag / owed -- the tax RATE
    d_under: float             # the underlying's move
    delta: float               # the average delta used
    tag: str = "M"


def between(under_from: Optional[float], under_to: Optional[float],
            prem_from: Optional[float], prem_to: Optional[float],
            delta_from: Optional[float] = None,
            delta_to: Optional[float] = None) -> Optional[Drag]:
    """One leg across one interval -> its drag, or None.

    None whenever the question does not apply or cannot be answered honestly:
    a missing price, a missing delta (there is no assumed 0.5 here -- that
    assumption is the reason this module exists), an underlying that did not
    move, or a move that went AGAINST the leg so there was no payoff to tax.
    """
    if None in (under_from, under_to, prem_from, prem_to):
        return None
    if delta_from is None and delta_to is None:
        return None
    deltas = [d for d in (delta_from, delta_to) if d is not None]
    delta = sum(deltas) / len(deltas)

    d_under = under_to - under_from
    if d_under == 0:
        return None
    owed = delta * d_under
    if owed <= 0:                       # the move went against this leg
        return None
    paid = prem_to - prem_from
    drag = owed - paid
    return Drag(owed=round(owed, 4), paid=round(paid, 4), drag=round(drag, 4),
                frac=round(drag / owed, 4), d_under=round(d_under, 4),
                delta=round(delta, 4))


class DragMeter:
    """Drag for one leg, anchored to a fixed start -- usually the session's.

    Anchored rather than interval-to-interval because the tax compounds: the
    useful reading is "of everything this position was owed since I could have
    entered, how much has been taken", and chaining short intervals answers a
    different, noisier question. Feed it the session open and it reports the
    day's rate; re-anchor with `reset` to measure from an entry instead.
    """

    def __init__(self):
        self._under0 = None
        self._prem0 = None
        self._delta0 = None

    def reset(self, under: Optional[float], prem: Optional[float],
              delta: Optional[float] = None) -> None:
        self._under0, self._prem0, self._delta0 = under, prem, delta

    def update(self, under: Optional[float], prem: Optional[float],
               delta: Optional[float] = None) -> Optional[Drag]:
        """Drag from the anchor to now. Anchors itself on the first call."""
        if self._under0 is None:
            self.reset(under, prem, delta)
            return None
        return between(self._under0, under, self._prem0, prem,
                       self._delta0, delta)
