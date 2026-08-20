"""Depth pull: size leaving a side with nothing traded against it.

The whole claim rests on one condition -- zero volume across the interval --
so most of these tests are about refusing to speak when that condition is not
met. A pull reported on an interval where trading happened would be a
cancellation number contaminated by consumption, and the two have opposite
readings.
"""
import json
from pathlib import Path

import depth_pull
import upstox_adapter as ua

FRAME = Path(__file__).parent / "data" / "feed_frame_2026-08-20.json"


def _real_fut():
    d = json.loads(FRAME.read_text(encoding="utf-8"))
    return ua.depth_ladder(d["frames"][d["fut_key"]])


def _shrink(lad, side, factor):
    """Same prices, less size -- a quoting engine widening without unquoting."""
    out = dict(lad)
    out[side] = [{"price": l["price"], "qty": l["qty"] * factor} for l in lad[side]]
    out[f"{side}_qty"] = sum(l["qty"] for l in out[side])
    return out


def test_size_leaving_with_no_volume_is_a_pull():
    was = _real_fut()
    ev = depth_pull.between(was, _shrink(was, "ask", 0.25), "11:00",
                            prev_vtt=5_000, vtt=5_000)
    assert ev.side == "ask"
    assert ev.was == was["ask_qty"]
    assert ev.frac == 0.75 and ev.gone == was["ask_qty"] * 0.75
    assert ev.levels_lost == 0            # prices all still quoted


def test_a_side_can_thin_without_losing_a_single_level():
    """The case `sweep` structurally cannot see: five prices still there, a
    tenth of the size. If levels_lost is ever nonzero here the fixture, not
    the logic, changed."""
    was = _real_fut()
    now = _shrink(was, "bid", 0.1)
    assert len(now["bid"]) == len(was["bid"]) == 5
    ev = depth_pull.between(was, now, "11:00", prev_vtt=0, vtt=0)
    assert ev.side == "bid" and ev.levels_lost == 0 and ev.frac == 0.9


def test_the_bigger_side_is_the_one_reported():
    was = _real_fut()
    now = _shrink(_shrink(was, "ask", 0.9), "bid", 0.1)   # bid loses far more
    ev = depth_pull.between(was, now, "11:00", prev_vtt=0, vtt=0)
    assert ev.side == "bid"


def test_volume_in_the_interval_means_this_module_says_nothing():
    """Something traded, so some of what left was consumed. `sweep` owns that
    interval; reporting a 'pull' here would mix consumption into a
    cancellation figure."""
    was = _real_fut()
    assert depth_pull.between(was, _shrink(was, "ask", 0.25), "11:00",
                              prev_vtt=5_000, vtt=5_065) is None


def test_unknown_volume_cannot_claim_nothing_traded():
    was = _real_fut()
    assert depth_pull.between(was, _shrink(was, "ask", 0.25), "11:00") is None


def test_a_side_growing_is_not_a_pull():
    was = _real_fut()
    assert depth_pull.between(was, _shrink(was, "ask", 2.0), "11:00",
                              prev_vtt=0, vtt=0) is None


def test_a_missing_book_reports_nothing():
    was = _real_fut()
    for a, b in ((None, was), (was, None), (None, None)):
        assert depth_pull.between(a, b, "11:00", prev_vtt=0, vtt=0) is None


def test_the_exchange_totals_ride_along_untouched():
    """tbq/tsq are the whole book, not the five quoted levels. They must be
    passed through, never folded into the displayed figures."""
    was = _real_fut()
    now = _shrink(was, "ask", 0.25)
    ev = depth_pull.between(was, now, "11:00", prev_vtt=0, vtt=0)
    assert ev.tbq == was["tbq"] and ev.tsq == was["tsq"]
    assert ev.was != ev.tbq              # displayed is not the exchange total


def test_the_detector_walks_snapshots_and_keeps_its_events():
    was = _real_fut()
    det = depth_pull.DepthPullDetector()
    assert det.on_snapshot("11:00", was, 0) is None      # nothing prior
    ev = det.on_snapshot("11:01", _shrink(was, "ask", 0.5), 0)
    assert ev and det.events == [ev]
    assert det.on_snapshot("11:02", was, 0) is None      # side refilled
