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


# ---- Task 2: bands computed on the bars themselves -------------------------------------------------------------------

def _row(t, h, l, c, v):
    """A composite 3-min index row (resample_index's shape), sampled 1-min bands deliberately WRONG (999)."""
    return {"t": t, "fut": {"o": c, "h": h, "l": l, "c": c, "v": v, "oi": None,
                            **{k: 999.0 for k in contract_bars.BAND_KEYS}}, "ce": None, "pe": None}


def test_bands_on_is_the_session_recurrence_on_the_rows_own_hlcv():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), _row("09:18", 108.0, 98.0, 99.0, 200.0),
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    want = contract_bars.vwap_sigma([(r["fut"]["h"], r["fut"]["l"], r["fut"]["c"], r["fut"]["v"]) for r in rows])
    assert contract_bars.bands_on(rows) == want
    flat = [dict(r["fut"], t=r["t"]) for r in rows]                       # resample's flat shape, same numbers
    assert contract_bars.bands_on(flat) == want


def test_an_unreadable_row_is_none_and_adds_nothing():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), {"t": "09:18", "fut": None, "ce": None, "pe": None},
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    got = contract_bars.bands_on(rows)
    assert got[1] is None
    assert got[2] == contract_bars.vwap_sigma([(110.0, 100.0, 105.0, 300.0), (101.0, 95.0, 96.0, 100.0)])[1]
    assert contract_bars.bands_on([{"t": "09:15", "h": None, "l": 1.0, "c": 1.0, "v": 1.0}]) == [None]


def test_with_bands_replaces_only_the_band_keys_on_a_copy():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), {"t": "09:18", "fut": None, "ce": None, "pe": None},
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    before = json.dumps(rows)
    b = contract_bars.bands_on(rows)
    out = contract_bars.with_bands(rows, b)
    assert json.dumps(rows) == before                                       # not mutated
    assert {k: out[0]["fut"][k] for k in contract_bars.BAND_KEYS} == b[0]
    assert out[0]["fut"]["h"] == 110.0 and out[0]["ce"] is None
    assert out[1] == rows[1]                                                # the future did not print: left as it is
    flat = contract_bars.with_bands([{"t": "09:15", "h": None, "l": 1.0, "c": 1.0, "v": 1.0, "d2": 5.0}], [None])
    assert flat[0]["d2"] is None and flat[0]["l"] == 1.0                     # unreadable: None, never the old value
