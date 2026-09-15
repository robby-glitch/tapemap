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


OWED_FLOOR = 0.5   # premium points; below this a tax RATE is not measurable


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
    move, a move that went AGAINST the leg so there was no payoff to tax, or
    an owed payoff under OWED_FLOOR -- a rate against a hair's width of owed
    is arithmetic, not information.
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
    # OWED_FLOOR: a rate needs a denominator worth measuring. On expiry day
    # 2026-08-25 an OTM leg was "owed" ~0.1 points and the board printed a
    # 15,543% tax -- arithmetic, not information. Below half a premium point
    # the honest answer is the same as a missing delta: no rate.
    if owed < OWED_FLOOR:
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


class Board:
    """Session drag for one index, on the two legs a buyer would have used.

    THE QUESTION THIS ANSWERS, IN THE OPERATOR'S OWN WORDS: *even getting the
    right side, the buyer could not make money.* So it anchors ONE call and
    ONE put -- the strikes nearest spot at the session's first snapshot -- and
    then just watches. Whichever way the index goes, one of the two was RIGHT,
    and `between` refuses to speak for the other (a leg the move went against
    has no payoff to tax). The reading that survives is therefore always the
    correct-side one, which is the only version of the number worth showing.

    ANCHORED ONCE, NOT RE-ANCHORED ON DRIFT. Following spot to a new strike
    every time it crosses one would restart the meter mid-session and report
    the tax on the last few minutes rather than on the day -- and the tax is
    cumulative, which is the whole point. The leg stays where it started and
    `strike` is published so a reader can see it drifted.

    Pure computation, stdlib only, no I/O. Feed it what `/api/chain` already
    publishes.
    """

    # THE ANCHOR ON A LATE START (the anytime-start rule). "Since I could have
    # entered" means the session's first minutes, not the process's. When the
    # backfilled minute grid (chain_backfill -> ChainState.minutes, rows with
    # src=backfill and a `px` premium per strike) is offered, the board
    # anchors on its EARLIEST mark instead of the first live snapshot. The
    # grid carries no delta, so the anchor's delta is None and `between`
    # averages the live end alone -- stated in `anchor_src`, never faked.
    # Waits up to SEED_WAIT_S for the grid to land; a start by 09:17 has no
    # morning to rebuild and anchors live at once.
    SEED_OPEN_S = 9 * 3600 + 17 * 60
    SEED_OPEN_M = "09:20"       # a grid whose first mark is by here has its open
    SEED_WAIT_S = 600

    def __init__(self):
        self.strike = None          # the anchored strike, once chosen
        self.at = None              # the snapshot it was anchored on
        self.anchor_src = None      # "live" | "backfill" | None
        self.anchor_why = "no snapshot yet"
        self._first_sec = None
        self._ce = DragMeter()
        self._pe = DragMeter()
        self.ce: Optional[Drag] = None
        self.pe: Optional[Drag] = None

    @staticmethod
    def _sec(t) -> Optional[int]:
        t = str(t or "")
        if len(t) >= 5 and t[2] == ":":
            return int(t[:2]) * 3600 + int(t[3:5]) * 60 + (int(t[6:8]) if len(t) >= 8 else 0)
        return None

    def _anchor_from_grid(self, grid) -> bool:
        """Anchor on the EARLIEST grid mark that prices a strike both sides --
        a REST-rebuilt row (src=backfill) or one an earlier process today
        observed (no src). True when it did; False when no mark qualifies."""
        rows = sorted((m, r) for m, r in dict(grid or {}).items()
                      if r.get("spot") and r.get("px"))
        for m, r in rows:
            ks = [k for k, p in r["px"].items()
                  if p and p[0] is not None and p[1] is not None]
            if not ks:
                continue
            k = min(ks, key=lambda x: abs(x - r["spot"]))
            src = "backfill" if r.get("src") == "backfill" else "restored"
            self.strike, self.at, self.anchor_src = k, m, src
            self.anchor_why = (f"anchored on the {m} mark ({'rebuilt from REST candles' if src == 'backfill' else 'observed by an earlier process today'}), "
                               f"strike {k}; the grid carries no delta, so the rate "
                               f"uses the live delta alone")
            self._ce.reset(r["spot"], r["px"][k][0], None)
            self._pe.reset(r["spot"], r["px"][k][1], None)
            return True
        return False

    @staticmethod
    def _leg(strikes, k, side):
        for row in strikes or []:
            if row.get("k") == k:
                return row.get(side) or {}
        return {}

    def on_snapshot(self, spot, strikes, t=None, grid=None):
        """One chain snapshot -> the drag on each anchored leg, or None each.

        None is a real answer here and appears constantly: before the anchor
        exists, when the index has not moved, and -- most often -- on the leg
        the move went against. Do not render it as zero.
        """
        if not spot or not strikes:
            return self
        if self.strike is None:
            sec = self._sec(t)
            if self._first_sec is None:
                self._first_sec = sec
            late = sec is not None and self._first_sec is not None \
                and self._first_sec > self.SEED_OPEN_S
            if late and grid is not None:
                g = {m: r for m, r in dict(grid).items() if r.get("spot") and r.get("px")}
                first = min(g) if g else None
                # ready once the grid reaches the open; else wait for the REST
                # walk, then anchor on what there is and name the gap
                if (first is None or first > self.SEED_OPEN_M) \
                        and sec - self._first_sec <= self.SEED_WAIT_S:
                    self.anchor_why = ("waiting for the backfilled minute grid to anchor on"
                                       if first is None else
                                       f"grid starts {first}; waiting for the REST walk to fill the open")
                    return self
                if not self._anchor_from_grid(g):
                    self.anchor_why = ("no grid mark prices a strike both sides; anchored "
                                       f"live at {t}, {(sec - 9 * 3600 - 15 * 60) // 60} min after the open")
                elif first > self.SEED_OPEN_M:
                    self.anchor_why += (f"; NOTHING before {first} -- the REST walk did not "
                                        f"land, the open's owed is not in this number")
            if self.strike is None:
                ks = [r.get("k") for r in strikes if r.get("k")]
                if not ks:
                    return self
                self.strike, self.at = min(ks, key=lambda k: abs(k - spot)), t
                self.anchor_src = "live"
                if not late:
                    self.anchor_why = "anchored live at the open"
        ce = self._leg(strikes, self.strike, "ce")
        pe = self._leg(strikes, self.strike, "pe")
        self.ce = self._ce.update(spot, ce.get("ltp"), ce.get("delta"))
        self.pe = self._pe.update(spot, pe.get("ltp"), pe.get("delta"))
        return self

    def right_side(self) -> Optional[str]:
        """"ce" or "pe" -- whichever leg the move actually favoured, or None.

        Both being present at once is possible only if the underlying both
        rose and fell, which it cannot; `between` returns None on `owed <= 0`.
        """
        if self.ce and not self.pe:
            return "ce"
        if self.pe and not self.ce:
            return "pe"
        return None

    def read(self) -> dict:
        """A publishable dict. Every absence stays an absence."""
        side = self.right_side()
        d = self.ce if side == "ce" else self.pe if side == "pe" else None
        return {
            "strike": self.strike, "anchored_at": self.at,
            "anchor_src": self.anchor_src, "anchor_why": self.anchor_why,
            "right_side": side,
            "ce": self.ce.__dict__ if self.ce else None,
            "pe": self.pe.__dict__ if self.pe else None,
            "owed": d.owed if d else None,
            "paid": d.paid if d else None,
            "drag": d.drag if d else None,
            "frac": d.frac if d else None,
            "d_under": d.d_under if d else None,
            "delta": d.delta if d else None,
            "tag": "M",
        }
