"""The adapter's whole job is that nothing downstream can tell the difference.

So these tests do not check the adapter's own output shape in isolation -- they
push it through `chain_live.normalize`, the real function the real poller uses,
and assert on the snapshot contract `chain_metrics` and `engine` actually read.
If that passes, the broker swap is invisible to the engine.

The option numbers are the ones measured live on 2026-08-05 11:27 IST
(NIFTY 24700, 11 Aug expiry) so a regression shows up as a value that never
existed rather than as a plausible-looking round number.
"""

from datetime import datetime, timedelta, timezone

import chain_live
import upstox_adapter as ua

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 8, 5, 11, 27, 36, tzinfo=IST)
SPOT = 24613.45

CE_KEY, PE_KEY = "NSE_FO|CE24700", "NSE_FO|PE24700"
META = {CE_KEY: (24700, "ce"), PE_KEY: (24700, "pe")}


def _opt(ltp, oi, iv, delta, gamma, atp=None, mode="greeks"):
    """An Upstox option Feed as the socket delivers it."""
    core = {
        "ltpc": {"ltp": ltp, "ltt": 1, "ltq": 50, "cp": ltp},
        "optionGreeks": {"delta": delta, "gamma": gamma, "theta": -11.37,
                         "vega": 5.0, "rho": 0.1},
        "vtt": 123456, "oi": oi, "iv": iv,
    }
    if mode == "greeks":
        core["firstDepth"] = {"bidQ": 75, "bidP": ltp - 0.5,
                              "askQ": 75, "askP": ltp + 0.5}
        return {"firstLevelWithGreeks": core, "requestMode": 2}
    core["atp"] = atp
    core["marketLevel"] = {"bidAskQuote": [
        {"bidQ": 75, "bidP": ltp - 0.5, "askQ": 75, "askP": ltp + 0.5},
        {"bidQ": 50, "bidP": ltp - 1.0, "askQ": 50, "askP": ltp + 1.0}]}
    return {"fullFeed": {"marketFF": core}, "requestMode": 1}


def _feeds(**kw):
    return {CE_KEY: _opt(114.10, 8916050, 0.1112, 0.4359, 0.0011, **kw),
            PE_KEY: _opt(164.50, 3740620, 0.1033, -0.5694, 0.0012, **kw)}


def _snap(prev_oi=None, **kw):
    payload = ua.chain_payload(_feeds(**kw), META, SPOT, prev_oi)
    return chain_live.normalize(payload, NOW, window=500)


# --------------------------------------------------------------------------
# the round trip
# --------------------------------------------------------------------------

def test_upstox_feed_survives_the_real_normalizer():
    snap = _snap()
    assert snap["spot"] == SPOT
    assert snap["atm"] == 24700
    assert snap["ts"] == "11:27:36"
    assert [r["k"] for r in snap["strikes"]] == [24700]
    ce = snap["strikes"][0]["ce"]
    assert ce["ltp"] == 114.10
    assert ce["oi"] == 8916050
    assert ce["gamma"] == 0.0011
    assert ce["delta"] == 0.4359
    assert ce["vol"] == 123456


def test_iv_stays_a_fraction():
    """Dhan ships IV as a percent and `_side` divides by 100 above 1.5.
    Upstox already ships the fraction (0.1112 = 11.12% vol), so it must pass
    through untouched -- a second division would put every gamma out by 100x.
    """
    ce = _snap()["strikes"][0]["ce"]
    assert ce["iv"] == 0.1112


def test_full_mode_supplies_the_average_price():
    """`avg` is the chain's atp and only `full` mode carries it -- the reason
    this adapter subscribes full rather than option_greeks."""
    assert _snap(mode="greeks")["strikes"][0]["ce"]["avg"] is None
    assert _snap(mode="full", atp=113.4)["strikes"][0]["ce"]["avg"] == 113.4


def test_both_modes_yield_a_bid_and_an_ask():
    for mode, kw in (("greeks", {}), ("full", {"atp": 113.4})):
        ce = _snap(mode=mode, **kw)["strikes"][0]["ce"]
        assert ce["bid"] == 113.60, mode
        assert ce["ask"] == 114.60, mode


# --------------------------------------------------------------------------
# oi_chg -- the one field Upstox does not have
# --------------------------------------------------------------------------

def test_unknown_prior_oi_reports_no_change_rather_than_a_guess():
    assert _snap()["strikes"][0]["ce"]["oi_chg"] == 0


def test_a_supplied_prior_close_gives_the_real_change():
    snap = _snap(prev_oi={(24700, "ce"): 8_000_000, (24700, "pe"): 4_000_000})
    assert snap["strikes"][0]["ce"]["oi_chg"] == 916050
    assert snap["strikes"][0]["pe"]["oi_chg"] == -259380


# --------------------------------------------------------------------------
# partial data
# --------------------------------------------------------------------------

def test_a_strike_missing_one_leg_is_dropped_not_half_reported():
    """A lone CE would normalize into a row whose PE reads as a zeroed leg --
    downstream that is a wall that does not exist."""
    payload = ua.chain_payload({CE_KEY: _feeds()[CE_KEY]}, META, SPOT)
    assert payload["oc"] == {}


def test_unknown_instrument_keys_are_ignored():
    feeds = dict(_feeds())
    feeds["NSE_FO|SOMETHING_ELSE"] = _opt(1.0, 1, 0.1, 0.1, 0.1)
    payload = ua.chain_payload(feeds, META, SPOT)
    assert list(payload["oc"]) == ["24700.000000"]


def test_no_spot_is_an_error_not_a_zero():
    """spot 0 would put every strike infinitely far from ATM."""
    try:
        ua.chain_payload(_feeds(), META, None)
    except ValueError:
        return
    raise AssertionError("a missing spot must raise, not produce a chain")


# --------------------------------------------------------------------------
# candles
# --------------------------------------------------------------------------

NEWEST_FIRST = [
    ["2026-08-05T09:53:00+05:30", 24695.7, 24699.0, 24684.7, 24689.8, 9165, 11768965],
    ["2026-08-05T09:52:00+05:30", 24690.0, 24696.0, 24688.0, 24695.7, 8000, 11768000],
    ["2026-08-05T09:51:00+05:30", 24680.0, 24692.0, 24679.0, 24690.0, 7000, 11767000],
]


def test_candles_come_out_oldest_first():
    """Upstox sends newest first. Reversed, VWAP and the sigma bands would run
    backwards through the session."""
    a = ua.candles_to_arrays(NEWEST_FIRST)
    assert a["close"] == [24690.0, 24695.7, 24689.8]
    assert a["timestamp"] == sorted(a["timestamp"])


def test_the_iso_stamp_becomes_the_right_epoch():
    a = ua.candles_to_arrays(NEWEST_FIRST)
    last = datetime.fromtimestamp(a["timestamp"][-1], IST)
    assert last.strftime("%Y-%m-%d %H:%M") == "2026-08-05 09:53"


def test_open_interest_rides_along():
    assert ua.candles_to_arrays(NEWEST_FIRST)["open_interest"][-1] == 11768965


def test_an_unparseable_row_is_dropped_not_zero_filled():
    """A zero-filled row is a price of 0.0 and prints as a candle collapsing
    to the axis -- worse than a missing minute."""
    rows = [["not-a-time", 1, 2, 3, 4, 5, 6],
            ["2026-08-05T09:52:00+05:30", None, 2, 3, 4, 5, 6]] + NEWEST_FIRST
    a = ua.candles_to_arrays(rows)
    assert len(a["close"]) == 3
    assert 0.0 not in a["close"]


def test_no_candles_is_empty_not_an_exception():
    assert ua.candles_to_arrays([])["close"] == []
    assert ua.candles_to_arrays(None)["timestamp"] == []


# --------------------------------------------------------------------------
# the oi_chg baseline, which comes out of these same candles
# --------------------------------------------------------------------------

def test_the_baseline_is_the_first_bar_not_the_last():
    """Measured 2026-08-05: the 24700 CE opened at OI 5,513,235 and was at
    9,919,000 by 11:54. Taking the newest bar would report no change at all."""
    assert ua.session_open_oi(NEWEST_FIRST) == 11767000


def test_a_missing_baseline_stays_unknown():
    """None keeps oi_chg at "not known". A 0 baseline would report a change
    equal to the entire book."""
    assert ua.session_open_oi([]) is None
    assert ua.session_open_oi(
        [["2026-08-05T09:15:00+05:30", 1, 2, 0.5, 1.5, 10, 0]]) is None


def test_the_baseline_drives_a_real_change_through_the_normalizer():
    base = ua.session_open_oi(NEWEST_FIRST)
    snap = _snap(prev_oi={(24700, "ce"): base, (24700, "pe"): base})
    assert snap["strikes"][0]["ce"]["oi_chg"] == 8916050 - 11767000


def test_the_oi_history_comes_back_oldest_first():
    """The process does not always start at 09:15; this is what recovers the
    session before it came up."""
    series = ua.oi_series(NEWEST_FIRST)
    assert [oi for _, oi in series] == [11767000, 11768000, 11768965]
    assert [t for t, _ in series] == sorted(t for t, _ in series)


def test_bars_without_oi_are_dropped_from_the_history():
    """A zero would read as the whole book closing in one minute."""
    rows = NEWEST_FIRST + [["2026-08-05T09:50:00+05:30", 1, 2, 0.5, 1.5, 10, 0]]
    assert len(ua.oi_series(rows)) == 3


# --------------------------------------------------------------------------
# the index leg
# --------------------------------------------------------------------------

def test_the_index_feed_yields_a_spot():
    idx = {"fullFeed": {"indexFF": {
        "ltpc": {"ltp": 24613.45, "ltt": 1, "ltq": 0, "cp": 24550.0},
        "marketOHLC": {"ohlc": [{"interval": "1d", "open": 24600.0,
                                 "high": 24650.0, "low": 24580.0,
                                 "close": 24613.45, "vol": 0, "ts": 1}]}}}}
    assert ua.ltp_of(idx) == 24613.45


def test_ltp_of_tolerates_junk():
    for junk in (None, {}, {"fullFeed": {}}, "nope"):
        assert ua.ltp_of(junk) is None
