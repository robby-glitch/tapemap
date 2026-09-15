"""The three numbers the rebuilt DESK screen had to declare as missing:
realized vol, forward daily theta, and margin at a shifted spot.

The theta block is the one with real derivation risk -- a sign error there
reads as free money and a basis error inflates daily decay by ~45% -- so it is
checked against finite differences of the pricer that already exists, not
against a remembered formula.
"""

import json
import math
from datetime import datetime
from types import SimpleNamespace

import gamma


# ---- Black-76 theta --------------------------------------------------------

F, K, IV, T = 24200.0, 24200.0, 0.14, 7.0 / 365.0


def test_theta_matches_a_finite_difference_of_the_pricer():
    """The derivation reduced two density terms to one via F n(d1) = K n(d2).
    If that collapse is wrong the closed form drifts from the pricer, so
    compare against the pricer itself rather than trusting the algebra."""
    for kind in ("C", "P"):
        h = 1e-7
        # theta is -dPrice/dT
        fd = -(gamma.bs_price(F, K, IV, T + h, kind)
               - gamma.bs_price(F, K, IV, T - h, kind)) / (2 * h)
        assert abs(gamma.theta(F, K, IV, T, kind) - fd) < 1e-3, kind


def test_a_long_option_loses_theta_and_it_is_negative():
    """Sign convention: theta is dPrice/dt, so a holder's option is worth less
    tomorrow. A positive number here would read as free money."""
    assert gamma.theta(F, K, IV, T, "C") < 0
    assert gamma.theta(F, K, IV, T, "P") < 0


def test_calls_and_puts_at_the_money_decay_almost_identically():
    """Both use the same density term; only the r*price term differs, and at
    the money those prices are close."""
    c, p = gamma.theta(F, K, IV, T, "C"), gamma.theta(F, K, IV, T, "P")
    assert abs(c - p) / abs(c) < 0.05


def test_daily_theta_uses_the_CALENDAR_basis_T_was_built_on():
    """`surface.years_to_expiry` and `chain_live.t_years` both divide by
    365*86400. Dividing an annual theta by 252 while T is a 365 basis inflates
    daily decay by ~45% -- a number the screen would show as income."""
    assert gamma.DAYS_PER_YEAR == 365.0
    assert (gamma.theta_day(F, K, IV, T, "C")
            == gamma.theta(F, K, IV, T, "C") / 365.0)


def test_decay_accelerates_as_expiry_approaches():
    near = abs(gamma.theta_day(F, K, IV, 1.0 / 365.0, "C"))
    far = abs(gamma.theta_day(F, K, IV, 30.0 / 365.0, "C"))
    assert near > far


def test_a_dead_or_vol_less_option_decays_nothing_rather_than_raising():
    assert gamma.theta(F, K, IV, 0.0, "C") == 0.0
    assert gamma.theta(F, K, 0.0, T, "C") == 0.0
    assert gamma.theta(F, K, None, T, "C") == 0.0


# ---- realized vol ----------------------------------------------------------

def _write_session(d, day, closes):
    (d / f"fut_{day}.json").write_text(
        json.dumps({"close": closes, "timestamp": list(range(len(closes)))}),
        encoding="utf-8")


def test_rv5_is_computed_from_the_last_close_of_each_cached_session(
        tmp_path, monkeypatch):
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    closes = [24000.0, 24120.0, 24000.0, 24180.0, 23980.0, 24100.0]
    for i, c in enumerate(closes):
        _write_session(d, f"2026-08-{10 + i:02d}", [c - 5, c])
    rv, why = server._rv5("NIFTY")
    assert why is None and rv["tag"] == "M"
    assert rv["sessions"] == 6 and rv["n_returns"] == 5

    rets = [math.log(b / a) for a, b in zip(closes, closes[1:])]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    assert rv["rv"] == round(math.sqrt(var) * math.sqrt(252.0), 4)


def test_too_few_sessions_is_a_reason_not_a_number(tmp_path, monkeypatch):
    """A vol printed off two sessions is noise wearing a number's clothes."""
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    _write_session(d, "2026-08-10", [24000.0])
    _write_session(d, "2026-08-11", [24100.0])
    rv, why = server._rv5("NIFTY")
    assert rv is None and "need at least" in why


def test_a_missing_cache_says_so_rather_than_returning_zero(tmp_path,
                                                            monkeypatch):
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    rv, why = server._rv5("BANKNIFTY")
    assert rv is None and why


def test_the_other_indices_are_read_from_their_own_subdirectory(tmp_path,
                                                                monkeypatch):
    """NIFTY sits at the top level of data/backtest/; BANKNIFTY and SENSEX
    under their own folders. Reading the wrong one would quietly report
    NIFTY's vol under another index's name."""
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest" / "BANKNIFTY"
    d.mkdir(parents=True)
    for i, c in enumerate([52000.0, 52400.0, 52100.0, 52600.0, 52200.0,
                           52500.0]):
        _write_session(d, f"2026-08-{10 + i:02d}", [c])
    rv, why = server._rv5("BANKNIFTY")
    assert why is None and rv["sessions"] == 6


def test_a_corrupt_capture_is_skipped_not_zero_filled(tmp_path, monkeypatch):
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    for i, c in enumerate([24000.0, 24120.0, 24000.0, 24180.0, 23980.0]):
        _write_session(d, f"2026-08-{10 + i:02d}", [c])
    (d / "fut_2026-08-20.json").write_text("{not json", encoding="utf-8")
    rv, why = server._rv5("NIFTY")
    # five good sessions remain -> four returns, still publishable
    assert why is None and rv["n_returns"] == 4


def test_the_annualization_basis_travels_with_the_number(tmp_path,
                                                          monkeypatch):
    """252 trading days here vs 365 calendar in T. Comparing RV to IV is the
    whole point of having this, so the mismatch must not be silent."""
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    for i, c in enumerate([24000.0, 24120.0, 24000.0, 24180.0, 23980.0,
                           24100.0]):
        _write_session(d, f"2026-08-{10 + i:02d}", [c])
    rv, _ = server._rv5("NIFTY")
    assert "252" in rv["basis_note"] and "365" in rv["basis_note"]


# ---- the paper book's two new fields ---------------------------------------

import book as book_mod                                          # noqa: E402
from test_trader import _doc, _t, _view                          # noqa: E402

IN_HOURS = datetime(2026, 8, 24, 10, 30)


def _short_straddle(t):
    for right, d0 in (("CE", 0.5), ("PE", -0.5)):
        leg = book_mod.PaperLeg(strike=25000.0, right=right, side="SELL",
                                qty=130, entry_px=100.0, entry_ts="10:00",
                                iv0=0.14, delta0=d0, vega0=1.0)
        t.book.open(idx="NIFTY", strategy="TEST", lots=2, legs=[leg],
                    ts="10:00", spot0=25000.0, forced_who="t", forced_why="t",
                    gear="PIN")


def test_a_short_book_collects_theta_so_the_estimate_is_positive(tmp_path):
    """*ek din nikal jaye = +Rs Z*. A short straddle earns decay; a negative
    number here would invert the desk's whole thesis on screen."""
    t = _t(tmp_path)
    _short_straddle(t)
    d = _doc()
    st = t.state({"NIFTY": d})["theta_day_est"]
    assert st["rupees"] > 0 and st["legs"] == 2 and st["tag"] == "I"


def test_a_long_book_pays_theta(tmp_path):
    t = _t(tmp_path)
    leg = book_mod.PaperLeg(strike=25000.0, right="CE", side="BUY", qty=130,
                            entry_px=100.0, entry_ts="10:00", iv0=0.14,
                            delta0=0.5, vega0=1.0)
    t.book.open(idx="NIFTY", strategy="TEST", lots=2, legs=[leg], ts="10:00",
                spot0=25000.0, forced_who="t", forced_why="t", gear="PIN")
    assert t.state({"NIFTY": _doc()})["theta_day_est"]["rupees"] < 0


def test_a_leg_with_no_iv_is_named_not_silently_dropped(tmp_path):
    """A partial theta reported as the whole book's understates income exactly
    when a leg is unquoted -- which is when it matters."""
    t = _t(tmp_path)
    _short_straddle(t)
    d = _doc()
    for s in d["strikes"]:
        s["ce"].pop("iv")
    st = t.state({"NIFTY": d})["theta_day_est"]
    assert st["legs"] == 1
    assert any("no IV" in w for w in st["why"])


def test_an_empty_book_gives_a_reason_not_a_zero(tmp_path):
    st = _t(tmp_path).state({"NIFTY": _doc()})["theta_day_est"]
    assert st["rupees"] is None and st["no_legs_why"]


def test_the_forward_theta_is_not_the_measured_residual(tmp_path):
    """Two different quantities with similar names, kept apart on purpose:
    marks carry `theta_gamma_resid` (measured, gamma fused in); this is a
    forward model number."""
    t = _t(tmp_path)
    _short_straddle(t)
    st = t.state({"NIFTY": _doc()})["theta_day_est"]
    assert "theta_gamma_resid" in st["method"] and "MODEL" in st["method"]


def test_margin_grows_with_spot_for_a_short_book(tmp_path):
    """The survival table used to hold margin CONSTANT while spot moved.
    `desk._naked_margin` is a percentage of NOTIONAL, so a short book's margin
    rises with the index -- the mechanism the crowd doctrine turns on."""
    t = _t(tmp_path)
    _short_straddle(t)
    ms = t.state({"NIFTY": _doc()})["margin_shift"]
    assert ms["base"] > 0 and ms["positions_priced"] == 2
    at = ms["at"]
    assert at["-2%"] < at["-1%"] < ms["base"] < at["+1%"] < at["+2%"]
    assert ms["tag"] == "I" and ms["model"]


def test_margin_shift_on_an_empty_book_is_a_stated_absence(tmp_path):
    ms = _t(tmp_path).state({"NIFTY": _doc()})["margin_shift"]
    assert ms["base"] is None and ms["no_base_why"]


def test_the_shift_says_it_moves_spot_only(tmp_path):
    """A real SPAN run raises IV with spot, so these are a FLOOR. Claiming
    otherwise would make the survival row read safer than it is."""
    t = _t(tmp_path)
    _short_straddle(t)
    assert "FLOOR" in t.state({"NIFTY": _doc()})["margin_shift"]["note"]
