"""The volatility surface, tested against a curve whose answer is known.

The load-bearing test is `test_a_known_smile_is_recovered`: build a chain from
chosen coefficients, price every leg with Black-76, and check the fit hands
those coefficients back. A fit that cannot round-trip its own generator cannot
be trusted to say which real point is rich.

The second is `test_one_planted_rich_option_is_found`. Everything downstream --
which strategy, which strikes -- reduces to that one question, and a surface
that cannot find an option deliberately marked 2 vol points over the curve is
answering a different question than the one asked of it.
"""
import math

import gamma
import surface

F = 24_400.0            # forward
T = 7.0 / 365.0         # one week

# A smile with a real downward tilt: puts bid over calls, as index skew is.
A, B, C = 0.130, -0.55, 4.0


def _iv_at(x):
    return A + B * x + C * x * x


def _chain(strikes=None, bump=None):
    """A chain priced from the known smile. `bump` = {strike: extra vol}."""
    strikes = strikes or [F + i * 50 for i in range(-8, 9)]
    rows = []
    for k in strikes:
        x = math.log(k / F)
        iv = _iv_at(x) + (bump or {}).get(k, 0.0)
        rows.append({
            "k": k,
            "ce": {"ltp": gamma.bs_price(F, k, iv, T, "C"), "iv": iv,
                   "oi": 100_000.0},
            "pe": {"ltp": gamma.bs_price(F, k, iv, T, "P"), "iv": iv,
                   "oi": 100_000.0},
        })
    return rows


# --------------------------------------------------------------------------
# the fit must round-trip its own generator
# --------------------------------------------------------------------------

def test_a_known_smile_is_recovered():
    r = surface.read("NIFTY", "2026-08-28", _chain(), F, T)
    assert r.fit.ok, r.fit.why
    assert abs(r.fit.atm_iv - A) < 0.002
    assert abs(r.fit.convexity - C) < 0.5
    # skew is the curve's own quote: fit(-x) - fit(+x) = -2*B*SKEW_X
    assert abs(r.fit.skew - (-2 * B * surface.SKEW_X)) < 0.002
    assert r.fit.rmse < 1e-6          # points came off the curve exactly


def test_skew_sign_says_which_side_is_bid():
    """Index skew is puts over calls. A positive `skew` must mean exactly
    that, or every downstream structure choice inverts."""
    assert surface.read("NIFTY", "x", _chain(), F, T).fit.skew > 0
    flat = [{"k": k,
             "ce": {"ltp": gamma.bs_price(F, k, 0.13, T, "C"), "iv": 0.13,
                    "oi": 1.0},
             "pe": {"ltp": gamma.bs_price(F, k, 0.13, T, "P"), "iv": 0.13,
                    "oi": 1.0}}
            for k in [F + i * 50 for i in range(-8, 9)]]
    assert abs(surface.read("NIFTY", "x", flat, F, T).fit.skew) < 1e-6


# --------------------------------------------------------------------------
# the question everything downstream reduces to
# --------------------------------------------------------------------------

def test_one_planted_rich_option_is_found():
    """A single strike marked 2 vol points over the curve must come back as
    the richest point, with a positive residual."""
    k = F + 300
    r = surface.read("NIFTY", "x", _chain(bump={k: 0.02}), F, T)
    assert r.fit.ok
    assert r.richest[0].k == k
    assert r.richest[0].resid > 0.015
    assert r.richest[0].right == "CE"        # above the forward


def test_a_planted_cheap_option_is_found():
    k = F - 300
    r = surface.read("NIFTY", "x", _chain(bump={k: -0.02}), F, T)
    assert r.cheapest[0].k == k
    assert r.cheapest[0].resid < -0.015
    assert r.cheapest[0].right == "PE"       # below the forward


def test_an_unblemished_surface_has_nothing_much_to_say():
    """No planted mispricing -> residuals near zero. A surface that always
    finds something rich is finding noise."""
    r = surface.read("NIFTY", "x", _chain(), F, T)
    assert max(abs(p.resid) for p in r.points) < 1e-4


# --------------------------------------------------------------------------
# only OTM, because ITM IVs are noise
# --------------------------------------------------------------------------

def test_only_out_of_the_money_legs_are_used():
    r = surface.read("NIFTY", "x", _chain(), F, T)
    for p in r.points:
        # k == F is the boundary: by parity either right prices the same
        # vol there, so the ATM strike is admissible under both.
        assert ((p.right == "CE" and p.k >= F)
                or (p.right == "PE" and p.k <= F))


def test_an_option_with_no_time_value_is_refused():
    """Trading at intrinsic leaves the solver nothing to fit -- the failure
    chain_metrics._sane_iv exists to gate."""
    # ITM put: strike ABOVE the forward, so intrinsic is 400 and only two
    # paise of time value remain.
    iv, why = surface.believable_iv({"ltp": 400.02, "iv": 0.13}, F + 400, F,
                                    T, "PE")
    assert iv is None and "time value" in why


# --------------------------------------------------------------------------
# a feed IV we cannot reproduce is not a measurement
# --------------------------------------------------------------------------

def test_a_feed_iv_that_matches_our_own_inversion_is_kept():
    k = F + 200
    px = gamma.bs_price(F, k, 0.14, T, "C")
    iv, why = surface.believable_iv({"ltp": px, "iv": 0.14}, k, F, T, "CE")
    assert why == "agreed" and abs(iv - 0.14) < 1e-9


def test_a_feed_iv_that_contradicts_the_price_loses_to_our_inversion():
    """The broker says 40%; the price it sent says 14%. The price is the
    thing that trades."""
    k = F + 200
    px = gamma.bs_price(F, k, 0.14, T, "C")
    iv, why = surface.believable_iv({"ltp": px, "iv": 0.40}, k, F, T, "CE")
    assert why == "derived" and abs(iv - 0.14) < 0.005


def test_a_missing_feed_iv_is_derived_rather_than_dropped():
    k = F + 200
    px = gamma.bs_price(F, k, 0.14, T, "C")
    iv, why = surface.believable_iv({"ltp": px}, k, F, T, "CE")
    assert why == "derived" and abs(iv - 0.14) < 0.005


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------

def test_too_few_points_is_declined_not_fitted():
    """Two strikes and a quadratic is interpolation, not a fit."""
    r = surface.read("NIFTY", "x", _chain([F - 50, F + 50]), F, T)
    assert not r.fit.ok and "need" in r.fit.why


def test_a_missing_forward_or_expiry_is_declined():
    for f, t in ((None, T), (F, None), (F, 0.0), (F, -1.0)):
        r = surface.read("NIFTY", "x", _chain(), f, t)
        assert not r.fit.ok
        assert any("nothing to fit" in w for w in r.why)


def test_an_empty_chain_is_declined():
    assert not surface.read("NIFTY", "x", [], F, T).fit.ok
    assert not surface.read("NIFTY", "x", None, F, T).fit.ok


def test_using_spot_instead_of_the_forward_is_declared():
    """The basis tilts the whole fitted skew, which a reader would otherwise
    take for a market view."""
    r = surface.read("NIFTY", "x", _chain(), F, T, f_src="spot")
    assert any("SPOT" in w for w in r.why)


def test_the_missing_half_is_stated_on_every_read():
    """Cross-sectional richness is not the same claim as 'the surface is
    rich'. A reader must not be able to confuse them."""
    r = surface.read("NIFTY", "x", _chain(), F, T)
    assert any("cross-sectional only" in w for w in r.why)


# --------------------------------------------------------------------------
# put-call parity, as a data-quality alarm
# --------------------------------------------------------------------------

def test_a_stale_leg_shows_up_as_a_parity_gap():
    """CE and PE at one strike must price the same vol. When they do not, one
    of them is stale and the surface built on it is suspect."""
    rows = _chain()
    atm = min(rows, key=lambda s: abs(s["k"] - F))
    atm["pe"] = {"ltp": gamma.bs_price(F, atm["k"], 0.30, T, "P"),
                 "iv": 0.30, "oi": 1.0}
    r = surface.read("NIFTY", "x", rows, F, T)
    assert r.parity_gap is not None and r.parity_gap > 0.1
    assert any("parity gap" in w for w in r.why)


def test_a_clean_chain_has_no_parity_gap():
    r = surface.read("NIFTY", "x", _chain(), F, T)
    assert r.parity_gap is not None and r.parity_gap < 1e-6


# --------------------------------------------------------------------------
# the weighting, which is what keeps a dead wing from steering the curve
# --------------------------------------------------------------------------

def test_a_far_wing_cannot_drag_the_curve():
    """A junk print 1500 points out has almost no vega. Unweighted it would
    swing the fit; vega-weighted it barely moves it."""
    clean = surface.read("NIFTY", "x", _chain(), F, T).fit
    rows = _chain([F + i * 50 for i in range(-8, 9)] + [F + 1500])
    for s in rows:
        if s["k"] == F + 1500:
            s["ce"] = {"ltp": gamma.bs_price(F, s["k"], 0.60, T, "C"),
                       "iv": 0.60, "oi": 1.0}
    dirty = surface.read("NIFTY", "x", rows, F, T).fit
    # Vega weighting ALONE did not hold: unwindowed, this junk print moved
    # convexity from 4.0 to 139 and ATM vol by 1.2 points, because a large
    # |x| has huge leverage on the x^2 term whatever its weight.
    assert dirty.excluded == 1, "the wing must fall outside the window"
    assert abs(dirty.atm_iv - clean.atm_iv) < 1e-6
    assert abs(dirty.convexity - clean.convexity) < 1e-6


# --------------------------------------------------------------------------
# the clock -- IST, never the local machine
# --------------------------------------------------------------------------

def test_time_to_expiry_is_measured_to_1530_ist():
    from datetime import datetime
    now = datetime(2026, 8, 20, 15, 30, tzinfo=surface.IST)
    assert abs(surface.years_to_expiry("2026-08-27", now) - 7 / 365) < 1e-9
    assert surface.years_to_expiry("2026-08-20", now) == 0.0


def test_a_local_clock_ahead_of_ist_cannot_shift_the_expiry():
    """This machine runs 5.5h ahead of IST, so at 02:29 local it is already
    'tomorrow' while IST is still tonight. An aware datetime in ANY zone must
    give the same answer as its IST equivalent, or every option is mispriced
    by a day."""
    from datetime import datetime, timedelta, timezone
    local = timezone(timedelta(hours=11))                 # IST + 5:30
    a = surface.years_to_expiry("2026-08-28",
                                datetime(2026, 8, 21, 2, 29, tzinfo=local))
    b = surface.years_to_expiry("2026-08-28",
                                datetime(2026, 8, 20, 20, 59, tzinfo=surface.IST))
    assert abs(a - b) < 1e-12


def test_an_expired_contract_is_zero_not_negative():
    """A negative T puts an imaginary number inside the solver."""
    from datetime import datetime
    now = datetime(2026, 8, 25, 10, 0, tzinfo=surface.IST)
    assert surface.years_to_expiry("2026-08-20", now) == 0.0


def test_an_unparseable_expiry_is_declined():
    for bad in (None, "", "not-a-date", "28-08-2026"):
        assert surface.years_to_expiry(bad) is None
