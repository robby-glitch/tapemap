# tapemap/test_breadth.py
"""breadth.py: positioning breadth (spec §C.2). Counts of strikes, never a
direction -- the object is built with no direction field IN it, which is the
enforcement, and the last test here is what enforces the enforcement."""
import json

import breadth


def _minutes():
    """Three marks, 15 minutes apart at the ends. `k` is cumulative OI change
    since the open (ChainState.minutes' own meaning); `px` is a LEVEL."""
    return {
        "12:45": {"spot": 23200.0,
                  "k": {23200: (1.0e6, 2.0e6), 23300: (1.2e6, 1.0e6),
                        23100: (0.0, 3.0e6)},
                  "px": {23200: (120.0, 90.0), 23300: (60.0, 180.0),
                         23100: (210.0, 40.0)}},
        "12:52": {"spot": 23230.0,
                  "k": {23200: (1.4e6, 2.4e6), 23300: (1.5e6, 9.0e5),
                        23100: (0.0, 3.4e6)},
                  "px": {23200: (110.0, 95.0), 23300: (55.0, 190.0),
                         23100: (220.0, 38.0)},
                  "src": "backfill"},
        "13:00": {"spot": 23270.0,
                  "k": {23200: (2.0e6, 3.0e6), 23300: (1.0e6, 8.0e5),
                        23100: (0.0, 4.0e6)},
                  "px": {23200: (100.0, 99.0), 23300: (50.0, 200.0),
                         23100: (230.0, 35.0)}},
    }


def _fut():
    return [{"t": 1_780_026_340_000, "o": 23195.0, "h": 23210.0, "l": 23190.0,
             "c": 23200.0, "oi": 1_000_000},
            {"t": 1_780_026_340_000 + 300000 * 3, "o": 23200.0, "h": 23240.0,
             "l": 23195.0, "c": 23230.0, "oi": 940_000},
            {"t": 1_780_026_340_000 + 300000 * 6, "o": 23230.0, "h": 23280.0,
             "l": 23225.0, "c": 23270.0, "oi": 588_000}]


def _b(**kw):
    a = dict(minutes=_minutes(), fut_bars=_fut(),
             watched_strikes=[(23200, "pe"), (23300, "ce"), (23100, "pe")],
             regime="PINNED", pinned=True, now_hhmm="13:00")
    a.update(kw)
    return breadth.build(**a)


def test_the_window_is_named_and_both_ends_are_real_marks():
    b = _b()
    assert b["window_min"] == 15 and b["t0"] == "12:45" and b["t1"] == "13:00"


def test_four_counts_never_a_ratio_and_never_a_word():
    """23200 adds on both legs, 23300 sheds CE and PE, 23100 adds PE and does
    not move CE -- a strike that did not move is neither, not a zero."""
    b = _b()
    assert b["written_ce"] == 1 and b["unwound_ce"] == 1
    assert b["written_pe"] == 2 and b["unwound_pe"] == 1
    assert b["strikes_seen"] == 3 and b["counts_why"] is None


def test_concentration_says_one_wall_or_a_curtain():
    b = _b()
    assert 0.0 < b["concentration_top1"] <= 1.0
    assert b["concentration_top1"] <= b["concentration_top3"] <= 1.0
    assert b["concentration_why"] is None


def test_advancing_and_retreating_are_measured_off_each_front_s_own_peak():
    """23300 CE peaked at 1.5M mid-window and sits at 1.0M: a third given
    back, past the retreating threshold. The two PE fronts are still at their
    own peaks and still rising."""
    b = _b()
    assert b["fronts_seen"] == 3 and b["fronts_why"] is None
    assert b["advancing"] == 2 and b["retreating"] == 1


def test_pressed_and_bought_read_the_axis_minutes_px_was_stored_for():
    """Of the strikes that ADDED OI this window, how many saw premium fall
    (writers pressing) against rise (buyers building) -- the axis
    ChainState.minutes["px"] was stored for and nothing has ever read."""
    b = _b()
    assert b["pressed"] == 2 and b["bought"] == 1 and b["premium_why"] is None


def test_the_futures_lane_is_oi_against_price_session_and_window():
    b = _b()
    assert b["fut_oi_day"] == -412000 and b["fut_px_day"] == 75.0
    assert b["fut_oi_window"] is not None and b["fut_why"] is None


def test_regime_is_a_ported_fact_and_carries_its_tag():
    b = _b()
    assert b["regime"] == "PINNED" and b["pinned"] is True
    assert b["regime_tag"] == "I" and b["regime_why"] is None
    b2 = _b(regime=None, pinned=None)
    assert b2["regime"] is None and b2["regime_why"] and len(b2["regime_why"]) <= 48


def test_backfilled_minutes_are_counted_and_flagged_never_blended_silently():
    b = _b()
    assert b["backfill_minutes"] == 1


def test_a_window_with_one_mark_says_it_could_not_check():
    b = _b(minutes={"13:00": _minutes()["13:00"]})
    assert b["written_ce"] is None and b["counts_why"] and len(b["counts_why"]) <= 48
    assert b["t0"] is None and b["t1"] == "13:00"


def test_there_is_no_direction_field_anywhere_in_the_object():
    """§C.4's enforcement, and §H.5's guardrail: you cannot render a BULL/BEAR
    banner from data that does not contain one. This is the test that keeps it
    true after someone adds a field in six months."""
    b = _b()
    blob = json.dumps(b).upper()
    for banned in breadth.BANNED_WORDS:
        assert banned not in blob, f"{banned} reached the breadth object"
    for k in b:
        assert k not in ("direction", "bias", "lean", "verdict", "sentiment", "net")


def test_the_caption_is_permanent_and_names_both_readings():
    b = _b()
    assert b["note"] == breadth.NOTE
    assert "ceiling" in breadth.NOTE and "or" in breadth.NOTE
