"""The sweep detector, born against the book it will actually read.

The "before" ladder in most of these is the REAL NIFTY future captured off the
live v3 socket on 2026-08-20 09:56 IST, not an invented one -- so the prices,
the tick spacing and the lopsided level sizes are the ones the detector meets
in production. The "after" is that same ladder with levels removed, which is
precisely what an aggressor does to it.

The case that matters most is the pair `test_levels_gone_with_volume...` and
`test_levels_gone_with_no_volume...`: identical books, opposite readings, told
apart only by whether anything traded. Getting that backwards would call a
market maker stepping back an aggressor arriving.
"""
import json
from pathlib import Path

import sweep
import upstox_adapter as ua

FRAME = Path(__file__).parent / "data" / "feed_frame_2026-08-20.json"


def _real_fut():
    """The live NIFTY future's ladder: 5 levels a side, bids best-first."""
    d = json.loads(FRAME.read_text(encoding="utf-8"))
    return ua.depth_ladder(d["frames"][d["fut_key"]])


def _drop(ladder, side, n):
    """The book after `n` levels were taken off the top of `side`."""
    out = {k: (list(v) if isinstance(v, list) else v) for k, v in ladder.items()}
    out[side] = out[side][n:]
    return out


# --------------------------------------------------------------------------
# the discrimination the whole module exists for
# --------------------------------------------------------------------------

def test_levels_gone_with_volume_is_a_sweep():
    was = _real_fut()
    ev = sweep.between(was, _drop(was, "ask", 3), "09:57",
                       prev_vtt=100_000, vtt=101_250)
    assert ev.kind == "swept" and ev.side == "buy"
    assert ev.levels == 3
    assert ev.qty == sum(l["qty"] for l in was["ask"][:3])
    assert ev.from_px == was["ask"][0]["price"]
    assert ev.to_px == was["ask"][3]["price"]
    assert ev.traded == 1250


def test_levels_gone_with_no_volume_is_a_pull_not_a_sweep():
    """Same book, same levels gone, nothing traded -- makers withdrew.
    Calling this a sweep would read liquidity leaving as aggression arriving."""
    was = _real_fut()
    ev = sweep.between(was, _drop(was, "ask", 3), "09:57",
                       prev_vtt=100_000, vtt=100_000)
    assert ev.kind == "pulled" and ev.levels == 3 and ev.traded == 0


def test_without_vtt_it_says_unknown_rather_than_guessing():
    was = _real_fut()
    ev = sweep.between(was, _drop(was, "ask", 3), "09:57")
    assert ev.kind == "unknown" and ev.traded is None


# --------------------------------------------------------------------------
# sides, and the claim that a real sweep is one-sided
# --------------------------------------------------------------------------

def test_bids_taken_is_a_sell_sweep():
    was = _real_fut()
    ev = sweep.between(was, _drop(was, "bid", 2), "09:57",
                       prev_vtt=0, vtt=500)
    assert ev.side == "sell" and ev.levels == 2
    assert ev.from_px == was["bid"][0]["price"]
    assert ev.to_px == was["bid"][2]["price"]


def test_a_book_walking_up_reports_the_ask_side_only():
    """Price rising takes offers AND lifts the bids. The bids moved UP, so
    none of them sits above the new best bid -- they were not hit. If this
    ever reports 'sell', the direction logic is inverted."""
    was = _real_fut()
    up = {"bid": [{"price": l["price"] + 2.0, "qty": l["qty"]} for l in was["bid"]],
          "ask": was["ask"][3:], "bid_qty": 0, "ask_qty": 0,
          "tbq": None, "tsq": None}
    ev = sweep.between(was, up, "09:57", prev_vtt=0, vtt=900)
    assert ev.side == "buy"


# --------------------------------------------------------------------------
# what must NOT fire
# --------------------------------------------------------------------------

def test_one_level_is_an_ordinary_fill_not_a_sweep():
    was = _real_fut()
    assert sweep.between(was, _drop(was, "ask", 1), "09:57",
                         prev_vtt=0, vtt=900) is None


def test_an_unchanged_book_is_silent():
    was = _real_fut()
    assert sweep.between(was, was, "09:57", prev_vtt=0, vtt=900) is None


def test_a_missing_book_is_not_a_swept_one():
    """An index feed has no ladder at all; a dead feed has none either. Neither
    is an empty book that someone just cleared out."""
    was = _real_fut()
    for a, b in ((None, was), (was, None), (None, None)):
        assert sweep.between(a, b, "09:57", prev_vtt=0, vtt=900) is None
    empty = {"bid": [], "ask": [], "bid_qty": 0, "ask_qty": 0,
             "tbq": None, "tsq": None}
    assert sweep.between(was, empty, "09:57", prev_vtt=0, vtt=900) is None


# --------------------------------------------------------------------------
# the stateful wrapper
# --------------------------------------------------------------------------

def test_the_detector_compares_consecutive_snapshots():
    was = _real_fut()
    det = sweep.SweepDetector()
    assert det.on_snapshot("09:56", was, 100_000) is None       # nothing prior
    ev = det.on_snapshot("09:57", _drop(was, "ask", 3), 101_250)
    assert ev.kind == "swept" and det.events == [ev]


def test_a_gap_in_the_feed_does_not_join_the_frames_either_side_of_it():
    """The book vanished for a frame. The two live ladders around that hole are
    NOT consecutive, and comparing them would invent a sweep out of a gap."""
    was = _real_fut()
    det = sweep.SweepDetector()
    det.on_snapshot("09:56", was, 100_000)
    assert det.on_snapshot("09:57", None, None) is None          # feed gap
    assert det.on_snapshot("09:58", _drop(was, "ask", 3), 101_250) is None
    assert det.events == []
