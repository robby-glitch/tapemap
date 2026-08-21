"""direction.py -- which way the forced flow points, and how hard.

THIS MODULE MEASURES NOTHING NEW. Every input already exists and is already
forward-logged: the gear from `regime.decide`, and fuel / drain / trapped side
from `chainside.ChainRead`. What was missing was the last step -- turning
"which side of the book is in pain" into "which way does the hedging push" --
and until it existed, `desk.py` BLOCKED every directional structure for want of
a direction view. This is that step, and nothing else.

THE MECHANISM, WHICH IS WHY THIS IS NOT A GUESS. `chainside` builds a ledger
per (strike, side) on the standing assumption that near-ATM intraday OI is
WRITTEN -- the inventory is short. A short call is in pain when price rises. If
that writer covers, they buy the call back and the dealer on the other side
buys the future to stay hedged. The covering IS upward flow. So:

    trapped side = CE   ->  the pain relieves UPWARD   ->  BULL
    trapped side = PE   ->  the pain relieves DOWNWARD ->  BEAR

That is a statement about who is forced to transact, not a forecast. It is the
operator's own thesis (books force hedging -> hedging is the flow -> trapped
inventory is the fuel) read one step further than the existing modules read it.

CONVICTION IS A SEQUENCE, NOT A LEVEL, and the sequence is `forcing.py`'s:
pain alone is a loaded tank, and a loaded tank is not a move. So a named bias
comes in two strengths and they mean different things to a desk:

    FORCED    the trapped side is actually LEAVING (drain), inside CASCADE.
              The flow is happening. Buying convexity is legal.
    LEANING   the pain is loaded and one-sided, but nothing is draining yet.
              This is TRANSITION -- `regime.py`'s own docstring says BOTH
              games lose here. The bias is named so it can be watched; it is
              NOT a licence to put the trade on.
    NONE      no sided pain, or the gear damps everything (PIN). Sell premium
              or stand aside; direction is not the question being asked.

WHY BIAS AND GEAR ARE TWO FIELDS AND NEVER ONE. The gear says WHICH GAME is
legal (sell premium / buy convexity / stand aside). The bias says WHICH WAY.
Collapsing them produces the classic error this stack exists to avoid --
reading "BULL" as "buy calls" when the gear says the hedging damps every
excursion, which is the market paying you to SELL puts, not to buy calls.

THE `[I]` LAYER, DECLARED. The mechanism above rests on structure. What rests
on judgement is: the assumption that near-ATM OI is short (inherited from
`chainside`, not introduced here), and the requirement that pain be one-sided
before a side is named at all. Both are what forward scoring will judge.

KILL CONDITION, DECLARED AT BIRTH. If, after ~30 scored sessions, FORCED views
do not resolve in the named direction more often than LEANING ones do, the
conviction ladder is wrong and this module is rewritten rather than tuned. If
neither beats naming no direction at all, it is DELETED.

Forward-logged; gates nothing until its line earns it. Pure computation,
stdlib only, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import regime

BULL, BEAR, NEUTRAL, UNKNOWN = "BULL", "BEAR", "NEUTRAL", "UNKNOWN"
FORCED, LEANING, NONE = "FORCED", "LEANING", "NONE"

# Which game each gear permits. Straight out of `regime.py`'s docstring -- PIN
# damps, so premium selling works; CASCADE amplifies, so forced flow pays a
# buyer; TRANSITION is a full tank with no ignition, where both games lose.
SELL_PREMIUM, BUY_CONVEXITY, STAND_ASIDE, NO_GAME = (
    "SELL_PREMIUM", "BUY_CONVEXITY", "STAND_ASIDE", "NO_GAME")

GAME = {
    regime.PIN:        SELL_PREMIUM,
    regime.CASCADE:    BUY_CONVEXITY,
    regime.TRANSITION: STAND_ASIDE,
    regime.UNKNOWN:    NO_GAME,
}

# Pain must be this lopsided before a SIDE is named. `chainside` already
# computes `one_sided` against its own PAIN_SIDED (0.70); this is the same
# question asked of a caller that may only have the raw ranks. Deliberately
# the same number, restated rather than imported so `chainside`'s threshold
# can move without silently moving this one.
MIN_SIDED = 0.70

# A named side is worth nothing while the percentiles are still warming --
# `chainside.warm` is False until its ledgers have enough history for a rank
# to mean anything, and a rank of 1.00 out of three observations is not fuel.
# UNKNOWN is the honest answer there, and it is a reading, not a failure.


@dataclass
class View:
    """Which way, in which gear, and how hard -- with the reasons kept."""
    bias: str = UNKNOWN               # BULL | BEAR | NEUTRAL | UNKNOWN
    gear: str = regime.UNKNOWN        # PIN | TRANSITION | CASCADE | UNKNOWN
    game: str = NO_GAME               # what the gear permits
    conviction: str = NONE            # FORCED | LEANING | NONE
    trapped_side: Optional[str] = None    # ce | pe -- where the pain sits
    worst_leg: Optional[str] = None       # e.g. "24100CE"
    fuel_rank: Optional[float] = None
    drain: bool = False               # the TRAPPED side is leaving
    drain_other: bool = False         # the OTHER side is leaving -- a signal
                                      # AGAINST this view, not for it
    one_sided: Optional[bool] = None
    warm: bool = False
    why: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    tag: str = "I"

    @property
    def directional(self) -> bool:
        """May a DIRECTIONAL structure be built on this view at all?

        Only FORCED qualifies. LEANING names a side deliberately without
        licensing a trade on it -- see the conviction ladder in the module
        docstring -- and a structure built on LEANING would be exactly the
        "guessing the detonation time" `regime.py` warns against.
        """
        return self.conviction == FORCED and self.bias in (BULL, BEAR)


def _side_to_bias(side: Optional[str]) -> str:
    """ce -> BULL, pe -> BEAR. See the module docstring for why."""
    if side == "ce":
        return BULL
    if side == "pe":
        return BEAR
    return NEUTRAL


def read(chain: Optional[dict] = None, gear: Optional[str] = None,
         sided_frac: Optional[float] = None) -> View:
    """A chain read plus a gear -> the view.

    `chain` is `chainside.ChainRead` as a dict (which is exactly what
    `/api/senses` already publishes under `read[inst]["chain"]`), or None when
    no chain is available. `gear` is `regime.Verdict.gear`, or None when the
    gate has not run. `sided_frac` optionally supplies the raw one-sidedness
    when the caller has it and `chain["one_sided"]` does not.

    Nothing is fetched here. The caller assembles the measurements and owns
    whether each is `[M]` or `[I]`, per this stack's standing rule.
    """
    v = View()
    v.gear = gear if gear in GAME else regime.UNKNOWN
    v.game = GAME[v.gear]

    if not chain:
        v.missing.append("a chain read -- fuel and drain are chain quantities "
                         "and the book alone cannot see them")
        v.why.append("no chain: direction is UNKNOWN, which is a reading and "
                     "not a failure")
        return v

    v.fuel_rank = chain.get("fuel_rank")
    # `drain` NOW MEANS THE TRAPPED SIDE SPECIFICALLY. Until 2026-08-22 it was
    # a chain-wide aggregate summed across both sides, so this module printed
    # "the trapped side is actually leaving" off a number that could not
    # support it -- see chainside.ChainRead for the whole incident.
    v.drain = bool(chain.get("drain"))
    v.drain_other = bool(chain.get("drain_other"))
    v.one_sided = chain.get("one_sided")
    v.trapped_side = chain.get("trapped_side")
    v.worst_leg = chain.get("worst_leg")
    v.warm = bool(chain.get("warm"))

    if sided_frac is not None and v.one_sided is None:
        v.one_sided = sided_frac >= MIN_SIDED

    if not v.warm:
        v.missing.append("a warm chain -- percentiles are not trusted until "
                         "chainside has ranked enough snapshots")
        v.why.append("chain still warming: a rank of 1.00 out of a handful of "
                     "observations is not fuel")
        return v

    if not v.one_sided or not v.trapped_side:
        v.bias = NEUTRAL
        v.why.append("pain is not one-sided: both wings are carrying it, so no "
                     "side is forced and there is no direction to name")
        return v

    v.bias = _side_to_bias(v.trapped_side)
    leg = f" ({v.worst_leg})" if v.worst_leg else ""
    v.why.append(
        f"{v.trapped_side.upper()} writers are the trapped side{leg} -- "
        f"covering a short {v.trapped_side.upper()} is "
        f"{'buying' if v.bias == BULL else 'selling'}, so the pain relieves "
        f"{'UPWARD' if v.bias == BULL else 'DOWNWARD'}")

    # THE OTHER SIDE LEAVING IS EVIDENCE AGAINST, AND IS NOT ALLOWED TO PASS
    # SILENTLY. If the comfortable side is the one covering, the pain that
    # names this direction is being relieved from the wrong end: the move that
    # would follow is the one that RESCUES the trapped side rather than the one
    # its covering would force. Named, and downgraded, never ignored.
    if v.drain_other and not v.drain:
        v.conviction = LEANING
        v.why.append(
            f"the OTHER side is the one covering, not "
            f"{v.trapped_side.upper()} -- the pain naming this direction is "
            f"being relieved from the far end, which argues against the "
            f"trade rather than for it")
        return v

    # THE SEQUENCE. Drain is what separates a move from a loaded tank.
    if v.drain and v.gear == regime.CASCADE:
        v.conviction = FORCED
        v.why.append("the trapped side is actually leaving (drain) and the "
                     "gear is CASCADE -- hedging amplifies rather than damps. "
                     "The flow is happening, not pending.")
    elif v.drain:
        v.conviction = LEANING
        v.why.append(f"drain is printing but the gear reads {v.gear}, not "
                     f"CASCADE -- the side is leaving into hedging that still "
                     f"damps. Named, not tradeable as direction.")
    else:
        v.conviction = LEANING
        v.why.append("loaded but not draining: a full tank with no ignition. "
                     "regime.py's own reading of TRANSITION is that BOTH games "
                     "lose here -- this names the side to watch, and licenses "
                     "nothing.")
    return v


def describe(v: View) -> str:
    """One line a human can check against the chain. Never a probability."""
    if v.bias == UNKNOWN:
        return f"direction UNKNOWN in gear {v.gear}"
    if v.bias == NEUTRAL:
        return f"no side forced; gear {v.gear} -> {v.game}"
    return (f"{v.conviction} {v.bias} in gear {v.gear} -> {v.game}"
            + (f", pain on {v.worst_leg}" if v.worst_leg else ""))
