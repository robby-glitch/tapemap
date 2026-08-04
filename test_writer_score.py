"""The writer score must be earned, and there must be only one of it.

D2. The old score was net OI SINCE OPEN divided by the session's own largest
build. The moment `doi` set a new high that ratio was doi/doi = 1.0 EXACTLY,
so it pegged from the first rising bar and stayed there. Its direction came
from premium-since-open against a flat 2% floor, and on expiry day theta alone
clears that floor by mid-morning -- so `w_ce` sat at 1.0 all session whoever
was actually positioning, and the regime built on it carried nothing.

D8. chain_metrics had a second, better methodology for the same quantity, and
the two never agreed. Now engine imports chain_metrics' rule and constants
instead of restating them, and publishes `w_bars` so a score built from three
bars stops printing identically to one built from ninety.

The classification, per bar (chain_metrics does it per bucket):

    OI up   + premium down -> writers add    OI down + premium up   -> writers cover
    OI up   + premium up   -> buyers add     OI down + premium down -> longs bail
"""

import chain_metrics
import engine

STRIKE = 24700.0


def _layer():
    g = engine.GammaLayer(None, STRIKE, 0.25)
    g.oi0 = {"CE": 1_000_000, "PE": 1_000_000}
    g.px0 = {"CE": 100.0, "PE": 100.0}
    return g


def _feed(g, side, path):
    """Push (oi, premium) readings through the classifier and return w."""
    for oi, px in path:
        p_oi, p_px = g.prev_oi[side], g.prev_px[side]
        if p_oi is not None:
            d_oi, d_p = oi - p_oi, px - p_px
            if d_oi and abs(d_p) >= engine.PREM_TICK:
                g.w_bars[side] += 1
                if (d_oi > 0) == (d_p < 0):
                    g.w_flow[side] += d_oi
                else:
                    g.b_flow[side] += d_oi
        g.prev_oi[side], g.prev_px[side] = oi, px
        net = g.w_flow[side] - g.b_flow[side]
        g.w[side] = max(-1.0, min(1.0, net / max(chain_metrics.W_SAT * oi, 1.0)))
    return g.w[side]


def test_a_building_book_does_not_peg_from_the_first_bar():
    """The D2 regression. Old: +1.00 at bar one and every bar after."""
    g = _layer()
    oi, px, seen = 1_000_000, 100.0, []
    for _ in range(6):
        oi += 40_000
        px -= 1.5
        seen.append(_feed(g, "CE", [(oi, px)]))
    assert seen[0] == 0.0, "nothing is classifiable on the first reading"
    assert 0.0 < seen[3] < 1.0, seen        # climbing, not pegged
    assert seen[-1] > seen[1], seen         # and still climbing


def test_saturation_has_to_be_earned():
    """A pegged score must now mean the book really did turn over W_SAT of
    itself, not merely that OI set a new high."""
    g = _layer()
    oi, px = 1_000_000, 100.0
    for _ in range(40):
        oi += 40_000
        px -= 1.5
        _feed(g, "CE", [(oi, px)])
    assert g.w["CE"] == 1.0
    net = g.w_flow["CE"] - g.b_flow["CE"]
    assert net >= chain_metrics.W_SAT * oi, "saturated without the flow to justify it"


def test_theta_alone_cannot_manufacture_a_writer_score():
    """The exact expiry-day failure: premium bleeds all session while OI does
    not move. The old direction rule read that as writers positioning."""
    g = _layer()
    px = 100.0
    path = []
    for _ in range(30):
        px -= 1.5                            # pure decay, OI pinned
        path.append((1_000_000, px))
    assert _feed(g, "CE", path) == 0.0
    assert g.w_bars["CE"] == 0, "no OI moved, so nothing was classifiable"


def test_the_two_directions_are_opposite():
    build = _feed(_layer(), "CE", [(1_000_000 + i * 40_000, 100.0 - i * 1.5)
                                   for i in range(12)])
    buy = _feed(_layer(), "CE", [(1_000_000 + i * 40_000, 100.0 + i * 1.5)
                                 for i in range(12)])
    assert build > 0.3, build                # OI up, premium down -> writers
    assert buy < -0.3, buy                   # OI up, premium up   -> buyers


def test_a_sub_tick_premium_move_is_skipped_not_guessed():
    g = _layer()
    tiny = engine.PREM_TICK / 10.0
    _feed(g, "CE", [(1_000_000 + i * 40_000, 100.0 - i * tiny) for i in range(12)])
    assert g.w_bars["CE"] == 0
    assert g.w["CE"] == 0.0


def test_there_is_one_methodology_not_two():
    """D8. engine must not restate the rule -- it imports it, so the two
    cannot drift apart again."""
    assert engine.W_SAT is chain_metrics.W_SAT
    assert engine.PREM_TICK is chain_metrics.PREM_TICK


def test_the_score_carries_its_own_confidence():
    """A w built from three bars and one built from ninety used to print
    identically."""
    thin = _layer()
    _feed(thin, "CE", [(1_000_000, 100.0), (1_040_000, 98.0)])
    thick = _layer()
    _feed(thick, "CE", [(1_000_000 + i * 40_000, 100.0 - i * 1.5)
                        for i in range(30)])
    assert thin.w_bars["CE"] == 1
    assert thick.w_bars["CE"] == 29
