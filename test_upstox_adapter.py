"""The adapter's whole job is that nothing downstream can tell the difference.

So these tests do not check the adapter's own output shape in isolation -- they
push it through `chain_live.normalize`, the real function the real poller uses,
and assert on the snapshot contract `chain_metrics` and `engine` actually read.
If that passes, the broker swap is invisible to the engine.

The option numbers are the ones measured live on 2026-08-05 11:27 IST
(NIFTY 24700, 11 Aug expiry) so a regression shows up as a value that never
existed rather than as a plausible-looking round number.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


# --------------------------------------------------------------------------
# the depth ladder -- five levels that were arriving and being thrown away
# --------------------------------------------------------------------------

def _book(levels, tbq=None, tsq=None):
    """A `full` option Feed carrying an explicit ladder.

    `levels` is [(bidQ, bidP, askQ, askP), ...], best first, exactly the order
    the socket sends. A pair of zeros is how a thin book pads a level it has
    nothing to put in.
    """
    core = {"ltpc": {"ltp": 114.10, "ltt": 1, "ltq": 50, "cp": 113.0},
            "vtt": 123456, "oi": 8916050, "iv": 0.1112,
            "marketLevel": {"bidAskQuote": [
                {"bidQ": b_q, "bidP": b_p, "askQ": a_q, "askP": a_p}
                for b_q, b_p, a_q, a_p in levels]}}
    if tbq is not None:
        core["tbq"] = tbq
    if tsq is not None:
        core["tsq"] = tsq
    return {"fullFeed": {"marketFF": core}}


FIVE = [(75, 113.6, 50, 114.5), (150, 113.5, 100, 114.6),
        (225, 113.4, 300, 114.7), (75, 113.3, 125, 114.8),
        (600, 113.2, 25, 114.9)]


def test_every_level_survives_not_just_the_top():
    """The whole point: `_depth` kept one level, this keeps all five."""
    lad = ua.depth_ladder(_book(FIVE))
    assert [l["price"] for l in lad["bid"]] == [113.6, 113.5, 113.4, 113.3, 113.2]
    assert [l["qty"] for l in lad["ask"]] == [50, 100, 300, 125, 25]
    assert lad["bid_qty"] == 1125 and lad["ask_qty"] == 600


def test_padded_empty_levels_are_dropped_rather_than_counted_as_size():
    """A zero-priced level is padding, not resting size at a price of 0."""
    lad = ua.depth_ladder(_book(FIVE[:2] + [(0, 0, 0, 0)] * 3))
    assert len(lad["bid"]) == 2 and len(lad["ask"]) == 2
    assert lad["bid_qty"] == 225                 # 75 + 150, not 75 + 150 + 0s
    assert all(l["price"] for l in lad["bid"] + lad["ask"])


def test_a_one_sided_level_keeps_the_side_that_is_real():
    """Bid present, ask padded: the ladders end up different lengths."""
    lad = ua.depth_ladder(_book([(75, 113.6, 50, 114.5), (150, 113.5, 0, 0)]))
    assert len(lad["bid"]) == 2 and len(lad["ask"]) == 1


def test_totals_ride_along_when_full_mode_supplies_them():
    lad = ua.depth_ladder(_book(FIVE, tbq=372450, tsq=193600))
    assert lad["tbq"] == 372450 and lad["tsq"] == 193600


def test_missing_totals_are_unknown_not_zero():
    """`option_greeks` has no tbq/tsq. None, so 'not subscribed' and 'nobody
    is bidding' cannot render the same."""
    lad = ua.depth_ladder(_feeds()[CE_KEY])              # greeks mode
    assert lad["tbq"] is None and lad["tsq"] is None
    assert len(lad["bid"]) == 1                          # firstDepth only


def test_a_feed_with_no_book_is_none_not_an_empty_ladder():
    """An index feed carries no depth. None means 'no book here'; an empty
    ladder would read as a market with nobody in it."""
    idx = {"fullFeed": {"indexFF": {"ltpc": {"ltp": 24613.45}}}}
    assert ua.depth_ladder(idx) is None
    for junk in (None, {}, {"fullFeed": {}}, "nope"):
        assert ua.depth_ladder(junk) is None


def test_the_chain_payload_still_reads_the_top_of_that_same_book():
    """The extension must not move the chain's bid/ask by a paisa: the
    payload's top-of-book is the ladder's first level, still."""
    feed = _book(FIVE)
    lad = ua.depth_ladder(feed)
    side = ua.side_payload(feed)
    assert side["top_bid_price"] == lad["bid"][0]["price"] == 113.6
    assert side["top_ask_price"] == lad["ask"][0]["price"] == 114.5


def test_the_normalizer_output_is_byte_for_byte_what_it_was():
    """The real regression guard: push the unchanged fixtures through the real
    normalizer and assert the snapshot contract did not move."""
    snap = _snap(mode="full", atp=113.9)
    ce = snap["strikes"][0]["ce"]
    assert ce["bid"] == 114.10 - 0.5 and ce["ask"] == 114.10 + 0.5


# --------------------------------------------------------------------------
# the ladder against real bytes
# --------------------------------------------------------------------------

REAL_FRAME = Path(__file__).parent / "data" / "feed_frame_2026-08-20.json"


def _real():
    return json.loads(REAL_FRAME.read_text(encoding="utf-8"))


def test_a_captured_live_frame_still_yields_five_levels():
    """Captured 2026-08-20 09:56 IST off the live v3 socket, NIFTY 25-Aug.

    Everything above builds its own frames, which only proves the parse agrees
    with the test's idea of the wire format. This one is real bytes, so it
    fails if Upstox changes the shape under us -- the only way that stops being
    a surprise mid-session.
    """
    d = _real()
    lad = ua.depth_ladder(d["frames"][d["fut_key"]])
    assert len(lad["bid"]) == 5 and len(lad["ask"]) == 5
    assert lad["tbq"] and lad["tsq"]


def test_the_real_book_is_ordered_best_first():
    """`_levels` promises index 0 is top of book. This is where that stops
    being an assumption: bids must fall away from the touch, asks must rise.
    A feed that ever sends them reversed would put the sweep detector's
    'levels consumed' count on the wrong side of the book."""
    d = _real()
    for key, feed in d["frames"].items():
        lad = ua.depth_ladder(feed)
        if not lad:
            continue
        bids = [l["price"] for l in lad["bid"]]
        asks = [l["price"] for l in lad["ask"]]
        assert bids == sorted(bids, reverse=True), f"{key} bids not best-first"
        assert asks == sorted(asks), f"{key} asks not best-first"
        assert not bids or not asks or bids[0] < asks[0], f"{key} book crossed"


def test_the_real_index_leg_has_no_book_at_all():
    """An index is not traded, so it carries no depth. None, not an empty
    ladder -- the distinction the docstring promises, on real data."""
    d = _real()
    assert ua.depth_ladder(d["frames"][d["idx_key"]]) is None


def test_every_real_option_leg_carries_a_full_book():
    """11 of the 12 captured frames are tradeable legs; all of them had five
    levels a side. If this ever drops, the feed mode changed."""
    d = _real()
    ladders = [ua.depth_ladder(f) for f in d["frames"].values()]
    books = [l for l in ladders if l]
    assert len(books) == len(d["frames"]) - 1        # all but the index
    assert all(len(l["bid"]) == 5 and len(l["ask"]) == 5 for l in books)
