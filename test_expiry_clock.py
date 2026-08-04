"""The expiry clock must not freeze silently (D7, fixed 2026-08-05).

WHY. Black-Scholes gamma diverges at the money as time-to-expiry goes to zero,
so the greeks are priced against a floored `t`. That floor is legitimate. What
was not legitimate is that it bound from about 09:30 on expiry day and nothing
said so: at 15:00, with roughly thirty minutes left, every greek was being
computed as though six hours remained, and no consumer could tell.

Worse, the floor was applied TWICE -- once in live.build_payload and again in
GammaLayer.__init__ -- so neither site looked like the one that mattered. And
the literal 0.25 meant two different things in the same module: an ADDITIVE
intraday stub in days_to_expiry, a FLOOR here.

The fix keeps the floor and publishes the truth beside it. These tests pin
that: `t` is what the greeks were priced with, `t_real` is what the clock
says, and `t_floored` is how a panel knows the two have parted.
"""

import engine

STRIKE = 24700.0


def _g(t_days):
    return engine.GammaLayer(None, STRIKE, t_days)


def test_away_from_expiry_the_two_clocks_agree():
    g = _g(1.25)
    assert g.t == 1.25 and g.t_real == 1.25
    assert g.t_floored is False


def test_on_expiry_afternoon_the_floor_binds_and_says_so():
    """15:00 on expiry: ~30 minutes left. The greeks are still priced at the
    floor -- that is deliberate -- but t_floored is now how anyone drawing
    them finds out."""
    g = _g(0.021)
    assert g.t == engine.GAMMA_T_FLOOR
    assert g.t_real == 0.021
    assert g.t_floored is True


def test_the_boundary_itself_is_not_reported_as_floored():
    g = _g(engine.GAMMA_T_FLOOR)
    assert g.t == engine.GAMMA_T_FLOOR and g.t_floored is False


def test_the_real_clock_keeps_moving_after_the_floor_binds():
    """The bug in one assertion: priced time stops, real time must not."""
    noon, three = _g(0.146), _g(0.021)
    assert noon.t == three.t, "both are floored, so the priced clock is frozen"
    assert noon.t_real > three.t_real, "the real clock still has to decay"


def test_the_floor_and_the_intraday_stub_are_different_things():
    """They shared the literal 0.25 and were repeatedly confused, which is why
    D7 survived so long. days_to_expiry ADDS its 0.25 (the fraction of the
    expiry day itself); GAMMA_T_FLOOR is a lower bound. Same number today,
    different meanings, and now different names."""
    on_expiry_day = engine.days_to_expiry("Aug 04", 2026, "2026-08-04")
    assert on_expiry_day == 0.25          # 0 whole days + the additive stub
    day_before = engine.days_to_expiry("Aug 03", 2026, "2026-08-04")
    assert day_before == 1.25             # additive, not a floor


def test_no_time_at_all_falls_back_rather_than_dividing_by_zero():
    g = _g(0.0)
    assert g.t == 1.0 and g.t_real is None and g.t_floored is False
