# tapemap/test_visit.py
"""visit.py: one visit to a pocket, latched (spec §A.2, §A.3).

Pinned against the same two recorded sessions test_frame_zone.py uses, plus
synthetic tapes for the pre-arm and intrabar paths. Nothing here is tuned:
every assertion follows from the rule as written, and the two fixture
numbers below were read off band_rotation.run_states itself.
"""
import json
import os

import band_rotation
import frame
import visit

FIX = r"C:\Users\kaam\Desktop\Go charting\orderflow-desk\test"


def _tape(day, upto_hhmm):
    """The same loader test_frame_zone.py uses: real bars, bands rebuilt from
    the running VWAP/sigma so the band under each bar is that bar's own."""
    j = json.load(open(os.path.join(FIX, f"session-{day}.ofd.json"), encoding="utf-8"))
    bars = sorted(j["bars"], key=lambda b: b["t"])
    bars = [b for b in bars if frame._hhmm(b["t"]) <= upto_hhmm]
    pv = pv2 = vv = 0.0
    bands = []
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3
        pv += tp * b["vol"]; pv2 += tp * tp * b["vol"]; vv += b["vol"]
        m = pv / vv; s = max(0.0, pv2 / vv - m * m) ** 0.5
        bands.append({"t": b["t"], "vwap": m, "sigma": s, "u1": m + s, "d1": m - s,
                      "u2": m + 2 * s, "d2": m - 2 * s, "u3": m + 3 * s, "d3": m - 3 * s})
    return {"kind": "frame", "session": f"NIFTY-I|5m|{day}", "idx": "NIFTY", "interval": 5,
            "rowSize": 5, "futPx": bars[-1]["c"], "closed": bars, "forming": None,
            "bands": bands, "walls": [], "broke": [], "events": [], "taps": []}


def _machine(tape, side="BUY", band="d2"):
    bars = [{"t": frame._hhmm(b["t"]), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
             "vol": b["vol"], **{k: v for k, v in bd.items() if k != "t"}}
            for b, bd in zip(tape["closed"], tape["bands"])]
    return band_rotation.run_states(bars, stop_pts=band_rotation.OPERATOR_STOP_PTS,
                                    side=side, band=band)


def test_a_rearming_setup_is_one_visit_key_not_two():
    """THE DEFECT. On 2026-09-11 the buy machine arms at 09:25 and re-arms
    repeatedly down to the 09:55 trigger -- run_states' own re-arm rule, one
    setup. Keying on ref_i rewrote the key on every re-arm; keying on
    arm.first_t cannot."""
    t45, t50 = _tape("2026-09-11", "09:45"), _tape("2026-09-11", "09:50")
    v45 = visit.current(t45, _machine(t45), "buy")
    v50 = visit.current(t50, _machine(t50), "buy")
    assert v45["visit_key"] == v50["visit_key"] == "buy@09:25"
    assert v45["reached_at"] == "09:25" and v45["reached_src"] == "arm"
    assert len(visit.visits(t50, _machine(t50), "buy")) == 1


def test_the_reach_is_latched_and_does_not_go_false_when_price_leaves():
    """09:45 on 2026-09-11: the tap was at 09:25 and price is nowhere near
    d2 now. The visit is still the 09:25 one -- a printed low does not
    un-print. This is the 09:45 failure the verdict caught."""
    t = _tape("2026-09-11", "09:45")
    v = visit.current(t, _machine(t), "buy")
    bn = t["bands"][-1]
    assert not (bn["d3"] <= t["futPx"] <= bn["d2"]), "price is outside the pocket"
    assert v is not None and v["reached_at"] == "09:25"


def test_a_visit_the_machine_let_go_of_ends_and_the_next_touch_is_a_new_one():
    """2026-09-09 to 14:10: three separate buy setups (09:25, 09:45, 12:00),
    each dropped by the machine and then closed back inside; by 14:10 none is
    live, so there is no current visit at all."""
    t = _tape("2026-09-09", "14:10")
    vs = visit.visits(t, _machine(t), "buy")
    assert [v["visit_key"] for v in vs] == ["buy@09:25", "buy@09:45", "buy@12:00"]
    assert [v["visit_ordinal"] for v in vs] == [1, 2, 3]
    assert all(v["ended_at"] is not None for v in vs)
    assert visit.current(t, _machine(t), "buy") is None


def test_the_sell_side_is_the_same_machine_flipped():
    t = _tape("2026-09-11", "13:45")
    v = visit.current(t, _machine(t, "SELL", "u2"), "sell")
    assert v["visit_key"] == "sell@10:00" and v["side"] == "sell"


def test_window_and_edge_are_judged_on_reached_at():
    """09:25 is before the window opens, so the 2026-09-11 buy visit is not
    her edge however good it looks -- and 10:00 on the synthetic tape is."""
    t = _tape("2026-09-11", "09:45")
    v = visit.current(t, _machine(t), "buy")
    assert v["in_window"] is False and v["is_edge"] is False
    assert v["window"] == ["09:45", "13:15"]


def _synth(n=14):
    """A falling tape with a fixed band: bars 9..13 print lows at or under
    d2 = 23300, so the reach latches on bar 9 (10:00) and nothing after it
    closes 0.5 sigma back inside."""
    closed = [{"t": (1000 * 60 * 5 * i) + 1_780_026_340_000, "o": 23500 - 20 * i,
               "h": 23510 - 20 * i, "l": 23480 - 20 * i, "c": 23490 - 20 * i}
              for i in range(n)]
    bands = [{"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0, "d3": 23250.0,
              "u2": 23500.0, "u3": 23550.0}] * n
    return {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "interval": 5,
            "rowSize": 5, "closed": closed, "bands": bands, "futPx": 23222.0,
            "forming": None}


def test_with_no_machine_the_reach_is_the_earliest_bar_of_the_touch_run():
    """No zone_state at all: the touch is still a printed fact, read off each
    bar's OWN band row, and it anchors on the FIRST bar of the run so the key
    does not drift bar to bar while the touch is still running."""
    v = visit.current(_synth(), [], "buy")
    assert v["visit_key"] == "buy@10:00" and v["reached_src"] == "touch"
    assert v["is_edge"] is True and v["reached_provisional"] is False


def test_the_intrabar_latch_is_provisional_until_the_bar_closes():
    """No closed bar has touched and no machine has armed, but the live price
    is inside the pocket -- so the reach latches NOW, stamped with the forming
    bar's own opening minute, and says it is provisional."""
    t = _synth(3)                      # 09:15, 09:20, 09:25; no low reaches 23300
    t["futPx"] = 23270.0               # inside [d3 23250, d2 23300]
    v = visit.current(t, [], "buy")
    assert v["reached_provisional"] is True and v["reached_src"] == "forming"
    assert v["reached_at"] == "09:30" and v["visit_key"] == "buy@09:30"


def test_a_forming_bars_running_low_beats_the_last_print_when_it_is_on_the_wire():
    t = _synth(3)
    t["futPx"] = 23400.0                          # back out of the pocket
    t["forming"] = {"o": 23400.0, "h": 23410.0, "l": 23280.0, "c": 23400.0}
    v = visit.current(t, [], "buy")
    assert v is not None and v["reached_provisional"] is True
    assert v["reached_at"] == "09:30"


def test_no_touch_no_machine_no_price_in_the_pocket_is_no_visit():
    t = _synth(3)
    t["futPx"] = 23450.0
    assert visit.current(t, [], "buy") is None
    assert visit.visits(t, [], "buy") == []
