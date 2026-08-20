"""Drag, checked against the session that produced the number.

The Aug-19 24050 PE is the reference: spot fell 93 points by 12:20 and the put
went 64.35 -> 92.75. These tests pin that arithmetic AND pin the refusals,
which matter more -- a drag reported on a leg the move went against would be a
huge meaningless percentage on an ordinary losing trade.
"""
import drag

# 2026-08-19, measured: index open 24152, 24050 PE from 64.35.
OPEN, PE0 = 24152.0, 64.35


def test_the_aug19_midday_reading_reproduces():
    """-93 on the index, the put paying +28.4, at the assumed delta of -0.5."""
    d = drag.between(OPEN, OPEN - 93, PE0, PE0 + 28.4,
                     delta_from=-0.5, delta_to=-0.5)
    assert d.owed == 46.5 and d.paid == 28.4
    assert round(d.frac, 2) == 0.39          # of what it was owed, at 0.5 delta


def test_the_final_hour_is_the_brutal_one():
    """13:20 -> 14:25: spot fell another 19 and the put paid 1.15. The tax rate
    is why 'right about direction' stopped being worth anything."""
    d = drag.between(24067.6, 24048.6, 97.85, 99.00,
                     delta_from=-0.5, delta_to=-0.5)
    assert d.owed == 9.5 and d.paid == 1.15
    assert round(d.frac, 2) == 0.88


def test_a_real_delta_changes_the_answer_which_is_the_whole_point():
    """Same move, same premium, delta pulled instead of assumed. If these two
    agreed there would be no reason for this module to exist."""
    assumed = drag.between(OPEN, OPEN - 93, PE0, PE0 + 28.4, delta_from=-0.5)
    real = drag.between(OPEN, OPEN - 93, PE0, PE0 + 28.4, delta_from=-0.42)
    assert real.owed < assumed.owed
    assert real.frac < assumed.frac          # less owed -> less of it eaten


def test_signs_need_no_special_case_for_puts_or_calls():
    """A put's negative delta times a falling index is a positive amount owed;
    a call's positive delta times a rising one is too. One expression."""
    put = drag.between(OPEN, OPEN - 100, 50.0, 60.0, delta_from=-0.5)
    call = drag.between(OPEN, OPEN + 100, 50.0, 60.0, delta_from=0.5)
    assert put.owed == call.owed == 50.0
    assert put.paid == call.paid == 10.0


def test_delta_is_averaged_across_the_interval():
    d = drag.between(OPEN, OPEN + 100, 50.0, 60.0,
                     delta_from=0.4, delta_to=0.6)
    assert d.delta == 0.5 and d.owed == 50.0


# --------------------------------------------------------------------------
# the refusals
# --------------------------------------------------------------------------

def test_a_move_against_the_leg_has_no_payoff_to_tax():
    """The index rose; the put lost. That is an ordinary losing trade, not a
    tax. Reporting a rate here would be a meaningless huge number on exactly
    the trades that failed for a normal reason."""
    assert drag.between(OPEN, OPEN + 93, PE0, PE0 - 20, delta_from=-0.5) is None


def test_no_delta_means_no_answer_rather_than_an_assumed_half():
    """The assumed 0.5 is the mistake this module exists to remove. It must
    not reappear as a default."""
    assert drag.between(OPEN, OPEN - 93, PE0, PE0 + 28.4) is None


def test_an_unmoved_underlying_asks_nothing():
    assert drag.between(OPEN, OPEN, PE0, PE0 - 2, delta_from=-0.5) is None


def test_missing_prices_report_nothing():
    for args in ((None, OPEN, PE0, PE0), (OPEN, None, PE0, PE0),
                 (OPEN, OPEN - 10, None, PE0), (OPEN, OPEN - 10, PE0, None)):
        assert drag.between(*args, delta_from=-0.5) is None


# --------------------------------------------------------------------------
# the anchored meter
# --------------------------------------------------------------------------

def test_the_meter_anchors_on_its_first_reading():
    m = drag.DragMeter()
    assert m.update(OPEN, PE0, -0.5) is None          # anchor, nothing to say
    d = m.update(OPEN - 93, PE0 + 28.4, -0.5)
    assert d.owed == 46.5


def test_the_meter_measures_from_the_anchor_not_from_the_last_tick():
    """The tax compounds; chaining short intervals answers a noisier question."""
    m = drag.DragMeter()
    m.update(OPEN, PE0, -0.5)
    m.update(OPEN - 50, PE0 + 15, -0.5)
    d = m.update(OPEN - 93, PE0 + 28.4, -0.5)
    assert d.d_under == -93.0                        # since the anchor


def test_reset_re_anchors_to_an_entry():
    m = drag.DragMeter()
    m.update(OPEN, PE0, -0.5)
    m.reset(OPEN - 50, PE0 + 15, -0.5)
    d = m.update(OPEN - 93, PE0 + 28.4, -0.5)
    assert d.d_under == -43.0
