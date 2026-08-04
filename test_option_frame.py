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
