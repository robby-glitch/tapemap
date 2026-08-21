"""What direction.py must never get wrong.

The mapping itself (ce -> BULL) is one line and would be trivial to test into
tautology. The tests that matter are the ones guarding the DISTINCTIONS: that
a loaded tank never reads as a move, that an unwarm chain reads UNKNOWN rather
than NEUTRAL, and that `directional` refuses LEANING -- because each of those
collapsing is how a "direction view" turns into a guess.
"""

import direction as D
import regime


def _chain(**kw):
    """A chainside.ChainRead-shaped dict, warm and one-sided by default."""
    base = dict(fuel_rank=0.9, worst_pain=42.0, worst_leg="24100CE",
                trapped_side="ce", one_sided=True, drain=False,
                drain_rank=None, warm=True, notes=[], tag="I")
    base.update(kw)
    return base


# -- the mechanism --------------------------------------------------------

def test_trapped_calls_read_bull_because_covering_a_short_call_is_buying():
    v = D.read(_chain(trapped_side="ce", drain=True), regime.CASCADE)
    assert v.bias == D.BULL
    assert any("UPWARD" in w for w in v.why)


def test_trapped_puts_read_bear():
    v = D.read(_chain(trapped_side="pe", worst_leg="24000PE", drain=True),
               regime.CASCADE)
    assert v.bias == D.BEAR
    assert any("DOWNWARD" in w for w in v.why)


# -- the sequence: a loaded tank is not a move ----------------------------

def test_pain_without_drain_is_leaning_not_forced():
    """The whole point of forcing.py's sequence. Fuel alone licenses nothing."""
    v = D.read(_chain(fuel_rank=0.99, drain=False), regime.TRANSITION)
    assert v.bias == D.BULL           # the side is still named...
    assert v.conviction == D.LEANING  # ...and still not tradeable
    assert v.directional is False


def test_drain_outside_cascade_is_leaning_not_forced():
    """Draining into hedging that still damps is not forced flow."""
    v = D.read(_chain(drain=True), regime.PIN)
    assert v.conviction == D.LEANING
    assert v.directional is False


def test_drain_inside_cascade_is_forced_and_is_the_only_directional_case():
    v = D.read(_chain(drain=True), regime.CASCADE)
    assert v.conviction == D.FORCED
    assert v.directional is True


# -- absence is a reading, and the three absences differ ------------------

def test_no_chain_is_unknown_and_names_what_is_missing():
    v = D.read(None, regime.PIN)
    assert v.bias == D.UNKNOWN
    assert v.missing and "chain" in v.missing[0]
    assert v.directional is False


def test_unwarm_chain_is_unknown_not_neutral():
    """A rank of 1.00 out of three observations is not fuel. UNKNOWN and
    NEUTRAL are different claims and must not collapse."""
    v = D.read(_chain(warm=False, fuel_rank=1.0), regime.CASCADE)
    assert v.bias == D.UNKNOWN
    assert v.missing


def test_two_sided_pain_is_neutral_not_unknown():
    """Here we DID check and found no side forced -- a different sentence."""
    v = D.read(_chain(one_sided=False), regime.PIN)
    assert v.bias == D.NEUTRAL
    assert not v.missing


def test_sided_frac_fills_in_when_one_sided_absent():
    v = D.read(_chain(one_sided=None), regime.CASCADE, sided_frac=0.85)
    assert v.bias == D.BULL
    v2 = D.read(_chain(one_sided=None), regime.CASCADE, sided_frac=0.5)
    assert v2.bias == D.NEUTRAL


# -- gear and bias are two fields and never one ---------------------------

def test_gear_maps_to_the_game_it_permits():
    assert D.GAME[regime.PIN] == D.SELL_PREMIUM
    assert D.GAME[regime.CASCADE] == D.BUY_CONVEXITY
    assert D.GAME[regime.TRANSITION] == D.STAND_ASIDE
    assert D.GAME[regime.UNKNOWN] == D.NO_GAME


def test_bull_in_pin_is_still_a_sell_premium_game():
    """The error this stack exists to avoid: reading BULL as 'buy calls' when
    the gear says hedging damps every excursion."""
    v = D.read(_chain(drain=True), regime.PIN)
    assert v.bias == D.BULL
    assert v.game == D.SELL_PREMIUM
    assert v.directional is False


def test_unrecognised_gear_degrades_to_unknown_rather_than_raising():
    v = D.read(_chain(drain=True), "NONSENSE")
    assert v.gear == regime.UNKNOWN
    assert v.game == D.NO_GAME
    assert v.directional is False


def test_describe_never_prints_a_probability():
    for gear in (regime.PIN, regime.CASCADE, regime.TRANSITION):
        s = D.describe(D.read(_chain(drain=True), gear))
        assert "%" not in s


if __name__ == "__main__":
    import sys
    fails = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except AssertionError as e:
                fails += 1
                print("FAIL %s: %s" % (name, e))
    print("all green" if not fails else "%d failed" % fails)
    sys.exit(1 if fails else 0)
