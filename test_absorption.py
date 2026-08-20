"""Absorption, born against the real book and against its own proof.

The claim this module makes is arithmetic: while the touch stands still, every
trade happened at one of those two prices, so volume above the largest
displayed size proves the level was rebuilt. These tests attack that claim
from both ends -- it must fire when the book really was replenished, and stay
silent every time the proof does not actually hold (touch moved, feed gapped,
too few frames, volume no larger than what was on show).
"""
import json
from pathlib import Path

import absorption
import upstox_adapter as ua

FRAME = Path(__file__).parent / "data" / "feed_frame_2026-08-20.json"


def _real_fut():
    d = json.loads(FRAME.read_text(encoding="utf-8"))
    return ua.depth_ladder(d["frames"][d["fut_key"]])


def _touch_qty(lad):
    return lad["bid"][0]["qty"] + lad["ask"][0]["qty"]


def _moved(lad, by=1.0):
    """The same book with the touch shifted, which must end a window."""
    out = dict(lad)
    out["bid"] = [{"price": l["price"] + by, "qty": l["qty"]} for l in lad["bid"]]
    out["ask"] = [{"price": l["price"] + by, "qty": l["qty"]} for l in lad["ask"]]
    return out


# --------------------------------------------------------------------------
# it fires when the level really was rebuilt
# --------------------------------------------------------------------------

def test_more_traded_than_was_ever_shown_is_absorption():
    lad = _real_fut()
    shown = _touch_qty(lad)                       # 65 + 65 = 130 on the real fut
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 1_000)
    det.on_snapshot("10:01", lad, 1_000 + shown * 3)
    ev = det.on_snapshot("10:02", _moved(lad), 1_000 + shown * 3)
    assert ev is not None
    assert ev.absorbed == shown * 3 and ev.shown == shown
    assert ev.ratio == 3.0 and ev.frames == 2
    assert ev.bid_px == lad["bid"][0]["price"]
    assert ev.ask_px == lad["ask"][0]["price"]


def test_the_peak_display_is_what_must_be_beaten_not_the_first_one():
    """The book grew mid-window. Beating only the opening size would call a
    level absorbing when it merely showed more later."""
    lad = _real_fut()
    big = dict(lad)
    big["bid"] = [{"price": lad["bid"][0]["price"], "qty": 10_000}] + lad["bid"][1:]
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 0)
    det.on_snapshot("10:01", big, 500)            # 500 < the 10 065 now shown
    assert det.on_snapshot("10:02", _moved(lad), 500) is None


def test_pending_reports_the_window_still_running():
    lad = _real_fut()
    shown = _touch_qty(lad)
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 0)
    det.on_snapshot("10:01", lad, shown * 2)
    live = det.pending()
    assert live.ratio == 2.0 and det.events == []   # not emitted yet


# --------------------------------------------------------------------------
# it stays silent whenever the proof does not hold
# --------------------------------------------------------------------------

def test_volume_no_greater_than_the_display_proves_nothing():
    """The resting size could simply have been eaten once. Nothing says it was
    replenished, so nothing is claimed."""
    lad = _real_fut()
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 0)
    det.on_snapshot("10:01", lad, _touch_qty(lad))         # exactly consumed
    assert det.on_snapshot("10:02", _moved(lad), _touch_qty(lad)) is None


def test_a_single_frame_is_not_a_defended_level():
    lad = _real_fut()
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 0)
    assert det.on_snapshot("10:01", _moved(lad), 99_999) is None


def test_a_feed_gap_ends_the_window_rather_than_stitching_across_it():
    """Volume during a hole may have traded at any price. Carrying it into
    these two prices would manufacture an absorption out of missing data."""
    lad = _real_fut()
    shown = _touch_qty(lad)
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 0)
    det.on_snapshot("10:01", lad, shown)
    det.on_snapshot("10:02", None, None)                   # feed gap
    det.on_snapshot("10:03", lad, shown * 50)
    det.on_snapshot("10:04", _moved(lad), shown * 50)
    assert det.events == []


def test_vtt_missing_is_a_gap_not_a_zero():
    lad = _real_fut()
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, None)
    det.on_snapshot("10:01", lad, None)
    assert det.on_snapshot("10:02", _moved(lad), None) is None
    assert det.events == []


def test_a_book_with_only_one_side_has_no_touch_to_defend():
    lad = _real_fut()
    half = dict(lad, ask=[])
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", half, 0)
    assert det.on_snapshot("10:01", half, 99_999) is None


# --------------------------------------------------------------------------
# sequencing
# --------------------------------------------------------------------------

def test_each_new_touch_starts_a_fresh_window():
    """Two defended levels in a row must be two events, not one merged run --
    merging them would attribute the second level's volume to the first."""
    lad = _real_fut()
    shown = _touch_qty(lad)
    up = _moved(lad)
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 0)
    det.on_snapshot("10:01", lad, shown * 2)
    first = det.on_snapshot("10:02", up, shown * 2)         # touch moves
    det.on_snapshot("10:03", up, shown * 6)
    second = det.on_snapshot("10:04", _moved(lad, 2.0), shown * 6)
    assert first.ratio == 2.0 and first.bid_px == lad["bid"][0]["price"]
    assert second.bid_px == up["bid"][0]["price"]
    assert len(det.events) == 2


def test_the_spread_travels_with_the_event():
    """A window whose touch was abnormally wide cannot support the proof, so
    the consumer must be able to see how wide it was. Measured on the live
    tape: a 7-point FUT touch produced an absorption that should be distrusted."""
    lad = _real_fut()
    shown = _touch_qty(lad)
    det = absorption.AbsorptionDetector()
    det.on_snapshot("10:00", lad, 0)
    det.on_snapshot("10:01", lad, shown * 3)
    ev = det.on_snapshot("10:02", _moved(lad), shown * 3)
    assert ev.spread == round(lad["ask"][0]["price"] - lad["bid"][0]["price"], 4)
    assert ev.spread == 1.4                     # the real captured NIFTY touch
