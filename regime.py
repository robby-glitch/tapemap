"""regime.py -- which gear the machine is in, and therefore which game is legal.

THE ONE IDEA. The market is one machine in two gears. In PIN, dealer hedging
damps every excursion and premium selling works. In CASCADE, the same hedging
flips from stabiliser to accelerant and forced flow pays a buyer multiples in
minutes. Between them is TRANSITION -- compressed volatility sitting on
one-sided trapped inventory, a full tank with no ignition yet -- where BOTH
games lose: selling there is writing insurance on a building that is already
smoking, and buying there is guessing the detonation time.

Every setup in the playbook is legal in exactly one gear, so the
classification is not decoration: it decides whether a rule may fire at all.

**IT RUNS IN SHADOW AND CANNOT BLOCK ANYTHING. THAT IS THE POINT, NOT A
LIMITATION.** A gate is the only module here that can make the system WORSE
than doing nothing: every other one adds a reading that can be ignored, while
a gate subtracts trades that would have won. The risk is not hypothetical --
a sigma-width gate was proposed for this stack on 2026-08-19 and the operator's
own 15 sessions reversed it, showing the fade tested BETTER in exactly the
regime the gate would have switched it off in. Had it shipped it would have
filtered out the best setups, silently, and looked principled doing it.

So `decide()` reports `would_block`, never `block`. `allows()` answers "would
this setup be legal". `SHADOW` is asserted by a test rather than being a flag
someone flips in a hurry; making this a real gate is a separate, deliberate
change that has to argue with its own scoreboard first.

THE CUTOFFS ARE THE `[I]` LAYER AND ARE DECLARED AS SUCH. Everything above is
mechanism -- gamma sign, forced flow, the fuel/ignition sequence -- and rests
on structure. The NUMBERS below rest on one afternoon. They are what forward
scoring exists to judge, and the part most likely to be wrong.

KILL CONDITION, DECLARED AT BIRTH. If, after ~30 scored sessions, the shadow
record does not show that blocking would have helped -- that setups it would
have refused did worse than setups it would have allowed -- this module is
DELETED rather than tuned. A gate that cannot demonstrate it subtracts losses
is subtracting edge.

INPUTS ARE PASSED IN, NEVER FETCHED. Nothing here imports the engine, the
chain or the feed, so it replays against any session and tests without a
market. The caller assembles the measurements and owns whether each is `[M]`
or `[I]`.

Pure computation, stdlib only, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# --- the [I] layer: one afternoon's judgement, awaiting a scoreboard --------
SIGMA_TIGHT = 0.35      # sigma percentile-so-far at or below this reads compressed
FUEL_HIGH = 0.80        # trapped-inventory pain rank that counts as loaded
MAGNET_FLIPS = 6        # VWAP sign changes/hour that read as magnetism, not trend

SHADOW = True           # see the docstring. Not a convenience flag.

PIN, TRANSITION, CASCADE, UNKNOWN = "PIN", "TRANSITION", "CASCADE", "UNKNOWN"

# Which setups each gear permits. S5 -- the skip -- is legal everywhere by
# construction: refusing to trade is never the thing a regime call gets wrong.
LEGAL = {
    PIN:        ("S3", "S5"),
    CASCADE:    ("S1", "S2", "S5"),
    TRANSITION: ("S5",),
    UNKNOWN:    ("S5",),
}


@dataclass
class Verdict:
    gear: str
    why: List[str] = field(default_factory=list)
    would_block: List[str] = field(default_factory=list)
    shadow: bool = True
    tag: str = "I"


def decide(sigma_pctl: Optional[float] = None,
           fuel_rank: Optional[float] = None,
           one_sided: Optional[bool] = None,
           ignition: bool = False,
           drain: bool = False,
           vwap_flips_per_hr: Optional[float] = None,
           walls_holding: Optional[bool] = None,
           setups: Optional[List[str]] = None) -> Verdict:
    """Measurements in -> the gear, why, and what it WOULD have refused.

    Order matters and is not arbitrary. CASCADE is tested first because a
    detonation in progress outranks every quieter reading -- a tape looks
    pinned right up to the moment it stops being pinned, and on 2026-08-19 the
    24100CE wall read as a ceiling until the instant it became fuel.
    TRANSITION comes next because a loaded tank matters more than the calm
    sitting on top of it. PIN is what is left when neither applies AND the calm
    is positively evidenced -- never merely assumed from an absence of alarm.

    UNKNOWN when the inputs support none of them. It is a real answer:
    illegibility is a reading, and it permits only the skip.
    """
    why: List[str] = []

    if ignition and drain:
        why.append("ignition + drain confirmed: forced flow is under way")
        gear = CASCADE
    elif (sigma_pctl is not None and sigma_pctl <= SIGMA_TIGHT
            and fuel_rank is not None and fuel_rank >= FUEL_HIGH and one_sided):
        why.append(f"sigma at {sigma_pctl:.2f} pctl with one-sided pain rank "
                   f"{fuel_rank:.2f}: loaded, not yet lit")
        gear = TRANSITION
    elif (vwap_flips_per_hr is not None and vwap_flips_per_hr >= MAGNET_FLIPS
            and walls_holding):
        why.append(f"{vwap_flips_per_hr:.0f} VWAP flips/hr with walls holding: "
                   f"magnetism, not trend")
        gear = PIN
    else:
        why.append("inputs do not evidence any gear; illegibility is a reading")
        gear = UNKNOWN

    if ignition and not drain and gear != CASCADE:
        # 2/3 is never a signal. Said out loud so a reader is not left to infer
        # it from the absence of CASCADE.
        why.append("ignition without drain -- fakes die here, still not lit")

    asked = list(setups or LEGAL[gear])
    allowed = set(LEGAL[gear])
    return Verdict(gear=gear, why=why,
                   would_block=[s for s in asked if s not in allowed],
                   shadow=SHADOW)


def allows(gear: str, setup: str) -> bool:
    """Would `setup` be legal in `gear`. Advisory: nothing here enforces it."""
    return setup in LEGAL.get(gear, ())
