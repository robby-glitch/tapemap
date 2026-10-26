"""ZONE-3M (docs/setup-review/ZONE-3M-PREREG.md, draft §1r): the zone machine on bands computed on its own 3-minute bars,
beside the 1-minute-sigma zone. Pure: the 26 Oct NIFTY candles are a literal below; nothing here reads data/."""
import json
import os

import band_rotation
import contract_bars
from band_rotation import run_states

# ---- Task 1: the 09:25 anchor's span, and the one date ---------------------------------------------------------------

VWAP, SD = 100.0, 5.0
D2, D3, U2, U3 = VWAP - 2 * SD, VWAP - 3 * SD, VWAP + 2 * SD, VWAP + 3 * SD


def _bar(t, low, high, close):
    """One flat bar on fixed bands: VWAP 100, sigma 5 (d2 90, d3 85, u2 110, u3 115)."""
    return {"t": t, "o": close, "h": high, "l": low, "c": close, "vwap": VWAP, "u1": VWAP + SD, "d1": VWAP - SD,
            "u2": U2, "d2": D2, "u3": U3, "d3": D3}


def test_span_one_is_the_label_rule_byte_for_byte():
    """Every existing caller passes no span: the default must be the old `minute >= 09:25`, on every machine."""
    bars = [_bar("09:18", 84.0, 116.0, 100.0), _bar("09:21", 84.0, 116.0, 100.0), _bar("09:24", 84.0, 116.0, 100.0),
            _bar("09:25", 84.0, 116.0, 100.0), _bar("09:27", 84.0, 116.0, 100.0), _bar("09:30", 95.0, 117.0, 116.5),
            _bar("09:33", 83.0, 105.0, 84.0), _bar("09:36", 90.0, 99.0, 98.0)]
    for kw in ({}, {"band": "d2"}, {"side": "SELL"}, {"side": "SELL", "band": "u2"}):
        for stop in (None, band_rotation.OPERATOR_STOP_PTS):
            old = run_states(bars, stop_pts=stop, **kw)
            assert json.dumps(old) == json.dumps(run_states(bars, stop_pts=stop, span=1, **kw)), kw
    assert [s["entry"] for s in run_states(bars)] == band_rotation.detect_index_run(bars)


def test_span_three_lets_the_0924_bar_arm_and_span_one_does_not():
    """Rule 4: a bar is eligible when it holds a minute at or after 09:25 (label + 3 > 09:25)."""
    bars = [_bar("09:21", 95.0, 99.0, 97.0), _bar("09:24", 89.5, 93.0, 91.0), _bar("09:27", 92.0, 96.0, 95.5)]
    one = run_states(bars, stop_pts=20.0, band="d2")
    three = run_states(bars, stop_pts=20.0, band="d2", span=3)
    assert [s["state"] for s in one] == ["WAITING", "WAITING", "WAITING"]
    assert [s["state"] for s in three] == ["WAITING", "ARMED", "TRIGGERED"]
    assert three[1]["arm"] == {"rearm": False, "band": "d2", "extreme": 89.5, "first_i": 1, "first_t": "09:24"}
    assert three[2]["entry"]["stop"] == D2 - 20.0


def test_the_0921_bar_never_arms_even_at_span_three():
    """09:21 + 3 = 09:24: the bar holds no minute at or after 09:25."""
    assert run_states([_bar("09:21", 89.0, 93.0, 91.0)], band="d2", span=3)[0]["state"] == "WAITING"


def test_zone3_from_is_the_one_date_the_first_november_session():
    """One switch, one date (27 Oct is NIFTY's monthly expiry and the roll)."""
    assert band_rotation.ZONE3_FROM == "2026-10-28"
