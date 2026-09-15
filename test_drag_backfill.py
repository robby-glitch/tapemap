"""The buyer's tax on a late start: the board anchors on the EARLIEST minute
the grid holds -- REST-rebuilt or observed by an earlier process -- not on
the first snapshot this process happens to see. Started at 11:00, "owed since
I could have entered" still means 09:16."""

import drag


def _grid(marks, src="backfill"):
    out = {}
    for m, spot, ce_px, pe_px in marks:
        rec = {"spot": spot, "k": {25000: (0.0, 0.0), 25050: (0.0, 0.0)},
               "px": {25000: (ce_px, pe_px), 25050: (ce_px - 20, pe_px + 20)}}
        if src:
            rec["src"] = src
        out[m] = rec
    return out


def _strikes(ce_ltp, pe_ltp, delta=0.5):
    return [{"k": 25000, "ce": {"ltp": ce_ltp, "delta": delta}, "pe": {"ltp": pe_ltp, "delta": -delta}},
            {"k": 25050, "ce": {"ltp": ce_ltp - 20, "delta": delta}, "pe": {"ltp": pe_ltp + 20, "delta": -delta}}]


def test_a_late_start_anchors_on_the_earliest_grid_mark_not_the_first_snapshot():
    grid = _grid([("09:16", 25000.0, 100.0, 100.0), ("09:17", 25010.0, 104.0, 96.0)])
    b = drag.Board()
    b.on_snapshot(25100.0, _strikes(140.0, 60.0), "11:00:00", grid=grid)
    r = b.read()
    assert r["anchor_src"] == "backfill" and r["anchored_at"] == "09:16" and r["strike"] == 25000
    # owed = 0.5 x (25100 - 25000) = 50 from the 09:16 anchor; the call paid 40
    assert r["right_side"] == "ce" and r["owed"] == 50.0 and r["paid"] == 40.0
    assert "live delta alone" in r["anchor_why"]
    # observed rows (no src) qualify the same way and say so
    b2 = drag.Board()
    b2.on_snapshot(25100.0, _strikes(140.0, 60.0), "11:00:00",
                   grid=_grid([("09:16", 25000.0, 100.0, 100.0)], src=None))
    assert b2.read()["anchor_src"] == "restored" and b2.read()["anchored_at"] == "09:16"


def test_a_grid_that_starts_late_waits_then_anchors_and_names_the_gap():
    grid = _grid([("09:42", 25020.0, 90.0, 110.0)], src=None)
    b = drag.Board()
    b.on_snapshot(25100.0, _strikes(140.0, 60.0), "11:00:00", grid=grid)
    assert b.strike is None and "09:42" in b.anchor_why
    b.on_snapshot(25100.0, _strikes(140.0, 60.0), "11:10:01", grid=grid)
    r = b.read()
    assert r["anchor_src"] == "restored" and r["anchored_at"] == "09:42"
    assert "NOTHING before 09:42" in r["anchor_why"]


def test_a_start_at_the_open_anchors_live_at_once():
    b = drag.Board()
    b.on_snapshot(25000.0, _strikes(100.0, 100.0), "09:16:30", grid={})
    r = b.read()
    assert r["anchor_src"] == "live" and r["anchored_at"] == "09:16:30" and r["strike"] == 25000
    assert "at the open" in r["anchor_why"]
