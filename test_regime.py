"""The regime gate, and above all the fact that it does not gate.

`test_it_cannot_block_anything` is the load-bearing one. This module is the
only piece of the stack that can make the system worse than doing nothing, and
a sigma-width gate proposed on 2026-08-19 was reversed by the operator's own
data -- it would have switched the fade off in precisely the regime the fade
tested best in. Shadow is what stands between that mistake and the account.

The Aug-19 session is the fixture in prose: compressed sigma (20th pctl) on
one-sided trapped CE inventory all afternoon = TRANSITION, then ignition and
drain together at 14:33 = CASCADE.
"""
import regime


# --------------------------------------------------------------------------
# the property that must never change quietly
# --------------------------------------------------------------------------

def test_it_cannot_block_anything():
    """Shadow is not a convenience flag. Flipping it is a deliberate change
    that has to argue with a scoreboard, so it is pinned here."""
    assert regime.SHADOW is True
    v = regime.decide(ignition=True, drain=True, setups=["S1", "S2", "S3"])
    assert v.shadow is True
    assert not hasattr(v, "block")          # the field does not exist at all
    assert v.would_block == ["S3"]          # reported, never enforced


def test_every_gear_still_permits_the_skip():
    """Refusing to trade is never what a regime call gets wrong."""
    for gear in (regime.PIN, regime.CASCADE, regime.TRANSITION, regime.UNKNOWN):
        assert regime.allows(gear, "S5")


# --------------------------------------------------------------------------
# the gears
# --------------------------------------------------------------------------

def test_ignition_plus_drain_is_a_cascade():
    v = regime.decide(ignition=True, drain=True)
    assert v.gear == regime.CASCADE
    assert regime.allows(v.gear, "S2") and not regime.allows(v.gear, "S3")


def test_a_cascade_outranks_a_calm_looking_tape():
    """Aug-19 at 14:33: the tape had looked pinned all afternoon and the 24100CE
    wall read as a ceiling until the instant it became fuel. A detonation in
    progress must beat every quieter reading, so it is tested first."""
    v = regime.decide(ignition=True, drain=True,
                      vwap_flips_per_hr=12, walls_holding=True)
    assert v.gear == regime.CASCADE


def test_compressed_sigma_on_one_sided_fuel_is_transition():
    """Aug-19's afternoon: 20th-pctl sigma, CE writers loaded and underwater.
    A full tank with no ignition -- and BOTH games lose here."""
    v = regime.decide(sigma_pctl=0.20, fuel_rank=0.9, one_sided=True,
                      setups=["S2", "S3", "S5"])
    assert v.gear == regime.TRANSITION
    assert v.would_block == ["S2", "S3"]     # neither buying nor selling


def test_magnetism_with_walls_holding_is_a_pin():
    v = regime.decide(vwap_flips_per_hr=12, walls_holding=True,
                      setups=["S2", "S3"])
    assert v.gear == regime.PIN
    assert v.would_block == ["S2"] and regime.allows(v.gear, "S3")


def test_a_pin_must_be_evidenced_not_merely_the_absence_of_alarm():
    """Nothing alarming is not the same as a pin. Assuming calm from silence is
    how yesterday's logic ends up running on today's loaded tape."""
    v = regime.decide()
    assert v.gear == regime.UNKNOWN
    v2 = regime.decide(vwap_flips_per_hr=12, walls_holding=False)
    assert v2.gear == regime.UNKNOWN         # flips alone are not a pin


def test_unknown_permits_only_the_skip():
    v = regime.decide(setups=["S1", "S2", "S3", "S5"])
    assert v.gear == regime.UNKNOWN
    assert v.would_block == ["S1", "S2", "S3"]


# --------------------------------------------------------------------------
# the sequence rule, said out loud
# --------------------------------------------------------------------------

def test_ignition_without_drain_is_not_a_cascade_and_says_so():
    """2/3 is never a signal. The reason has to appear in `why`, or a reader
    infers it from an absence -- which is how impatience supplies the third
    condition itself."""
    v = regime.decide(ignition=True, drain=False,
                      vwap_flips_per_hr=12, walls_holding=True)
    assert v.gear != regime.CASCADE
    assert any("fakes die here" in w for w in v.why)


def test_transition_needs_the_fuel_to_be_one_sided():
    """Compressed sigma alone is not a loaded tank -- that was the exact claim
    the operator's 15 sessions reversed."""
    assert regime.decide(sigma_pctl=0.20, fuel_rank=0.9,
                         one_sided=False).gear != regime.TRANSITION
    assert regime.decide(sigma_pctl=0.20).gear == regime.UNKNOWN


def test_every_verdict_explains_itself():
    for kw in ({"ignition": True, "drain": True},
               {"sigma_pctl": 0.2, "fuel_rank": 0.9, "one_sided": True},
               {"vwap_flips_per_hr": 12, "walls_holding": True},
               {}):
        assert regime.decide(**kw).why, "a verdict with no reason cannot be argued with"


def test_the_verdict_is_tagged_inferred_not_measured():
    """The cutoffs rest on one afternoon. The tag says so on every verdict."""
    assert regime.decide(ignition=True, drain=True).tag == "I"
