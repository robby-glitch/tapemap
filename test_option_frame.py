"""The option maths must run in the INDEX frame, not the futures tape's.

WHY (2026-08-04). The tape is the MONTHLY future; the legs the engine prices
are the NEAREST WEEKLY. That day the two sat 59 points apart -- more than a
full strike step -- and the carry was reaching the option maths: every CE came
back unsolvable (iv_ce null all session) and the PE's solved IV printed 0.2584
against the chain's own 0.1102. These tests pin the seam so the frame cannot
drift back silently.
"""

import engine
import live


def _sess(**kw):
    """A Session with no bars — enough to inspect how the frame was threaded."""
    return engine.Session("test", [], [], [], quiet=True,
                          strike=24700.0, t_days=0.25, **kw)


# --- the empty-book guard (2026-08-14) -----------------------------------
# Not a frame test; it lives here because `_sess()` IS the crash condition --
# a Session with no bars at all. At 09:16 on 2026-08-14 the live build reached
# carry_verdict before the chain poller had filled the option books, and
# bars[0] raised IndexError, killing that refresh for NIFTY and BANKNIFTY.


def test_carry_verdict_on_an_empty_book_says_nothing_instead_of_raising():
    s = _sess()
    s.carry_verdict()
    assert not [e for e in s.events if e[1] == "CARRY"]


# --- the basis plausibility guard (2026-08-05) ---------------------------
# `basis` is what moves every chain-derived level (walls, PIN, STK, max pain,
# GEX flip) from the INDEX frame onto the futures tape. A wrong one does not
# degrade the chart, it misplaces all of them -- so a basis we cannot trust
# must become an absence with a reason, never a number.

SPOT = 24600.0


def test_a_plausible_carry_passes_through():
    """Rounded only for the assertion: `_basis` returns the full float so the
    option maths keeps its precision, and the payload does its own round(2)."""
    b, why = live._basis(SPOT + 95.55, SPOT)
    assert round(b, 2) == 95.55 and why == ""


def test_the_2026_08_04_post_close_print_is_refused():
    """The print that exposed the bug: futures 53 points BELOW the index. The
    operator's read of the instrument is that a discount that deep does not
    happen, so one of the two prices was stale."""
    b, why = live._basis(24547.10, SPOT)
    assert b is None
    assert "-52.90" in why and "stale" in why


def test_a_failure_returns_none_not_a_fabricated_zero():
    """The whole bug in one assertion. 0.0 is not a safe default -- it is the
    positive claim 'futures and index are at the same price', and the UI draws
    chain levels on it."""
    for bad in (None, "x", float("nan"), 0.0):
        b, _ = live._basis(SPOT + 90.0, bad)
        assert b is None, f"spot={bad!r} must withhold, not return a number"


def test_a_small_discount_is_still_tolerated():
    """The guard catches breakage, not noise. Tightening it until every
    discount is refused would throw away good sessions."""
    b, why = live._basis(SPOT - 20.0, SPOT)
    assert b == -20.0 and why == ""


def test_an_absurd_premium_is_refused_too():
    """The band is generous upward -- carry is largest early in a monthly
    contract -- but not unbounded."""
    b, why = live._basis(SPOT + 500.0, SPOT)
    assert b is None and "+500.00" in why


def test_every_refusal_carries_a_reason_and_every_pass_carries_none():
    """'We checked and it is good' and 'we could not check' must stay
    different sentences."""
    ok_b, ok_why = live._basis(SPOT + 40.0, SPOT)
    bad_b, bad_why = live._basis(SPOT - 300.0, SPOT)
    assert ok_b is not None and ok_why == ""
    assert bad_b is None and bad_why.strip() != ""


def test_a_missing_spot_and_an_unusable_spot_say_different_things():
    _, no_spot = live._basis(SPOT + 90.0, None)
    _, zero_spot = live._basis(SPOT + 90.0, 0.0)
    assert no_spot != zero_spot


def test_basis_defaults_to_zero_so_backtests_are_untouched():
    """Nine backtest callers construct Session without a basis. They must keep
    the exact behaviour they had before the parameter existed."""
    s = _sess()
    assert s.basis == 0.0
    assert s.gamma.basis == 0.0


def test_basis_reaches_the_gamma_layer():
    s = _sess(basis=59.0)
    assert s.gamma.basis == 59.0


def test_none_basis_is_treated_as_zero_never_as_a_crash():
    """The chain can be down; `spot` is then None and build_payload passes 0.0.
    A missing basis must degrade to the old frame, not raise."""
    assert _sess(basis=None).gamma.basis == 0.0


def test_strike_is_picked_in_the_index_frame():
    """With a 59-point basis the futures price rounds to one strike and the
    index price to the one below it. Picking on the futures price puts the
    engine's whole pin/near/regime frame a full step too high."""
    cfg = {"under_sym": "FRAMETEST", "step": 50}
    fut_px = 24647.0
    basis = 59.0
    assert live._pick_strike(fut_px - basis, cfg) == 24600
    # and the two frames really do disagree here — otherwise this proves nothing
    cfg2 = {"under_sym": "FRAMETEST2", "step": 50}
    assert live._pick_strike(fut_px, cfg2) == 24650
