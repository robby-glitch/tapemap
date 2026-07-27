"""Tests for continuation.py BREAKGO generator — synthetic bars, no I/O."""
from continuation import SESSION_AGE, generate


def bar(t, c, ce_slope=0, pe_slope=0, h=None, l=None):
    return {"t": t, "fut": {"h": h if h is not None else c + 1,
                            "l": l if l is not None else c - 1, "c": c},
            "ce": {"oi_slope": ce_slope}, "pe": {"oi_slope": pe_slope}}


def mk(closes, **conf):
    return [bar(f"10:{i:02d}" if i < 60 else f"11:{i-60:02d}", c, **conf)
            for i, c in enumerate(closes)]


RS = lambda bars: [10.0] * len(bars)          # fixed R=10 -> margin 0.2 = 2pts


def test_pdh_break_with_both_books_fires_up():
    bars = mk([100, 100, 106], ce_slope=-5, pe_slope=5)
    sigs = generate(bars, pdh=103, pdl=90, Rs=RS(bars), prior_R=None,
                    margin=0.2, confirm="both")
    assert sigs == [{"t": "10:02", "kind": "BREAKGO", "dir": 1}]


def test_unconfirmed_break_is_silent_and_consumes_pool():
    bars = mk([100, 106, 107], ce_slope=5, pe_slope=5)   # CE building: no conf
    sigs = generate(bars, 103, 90, RS(bars), None, 0.2, "both")
    assert sigs == []                          # pool consumed, never re-fires


def test_pdl_break_mirror_confirmation():
    bars = mk([100, 94], ce_slope=5, pe_slope=-5)        # PE covering, CE add
    sigs = generate(bars, 200, 97, RS(bars), None, 0.2, "both")
    assert sigs == [{"t": "10:01", "kind": "BREAKGO", "dir": -1}]


def test_session_extreme_needs_age():
    # high set at bar 1 (105); broken 10 bars later -> too young, no signal
    closes = [100, 105] + [100] * 10 + [108]
    bars = mk(closes, ce_slope=-5, pe_slope=5)
    sigs = generate(bars, None, None, RS(bars), None, 0.2, "both")
    assert sigs == []

    # same break AFTER the extreme has aged >= SESSION_AGE bars -> fires
    # (session high is bar-1's h = 105+1 = 106; threshold 106 + 0.2*10 = 108,
    #  so the close must exceed 108)
    closes2 = [100, 105] + [100] * (SESSION_AGE + 1) + [110]
    bars2 = mk(closes2, ce_slope=-5, pe_slope=5)
    sigs2 = generate(bars2, None, None, RS(bars2), None, 0.2, "both")
    assert [s["dir"] for s in sigs2] == [1]


def test_no_R_no_signal():
    bars = mk([100, 106], ce_slope=-5, pe_slope=5)
    sigs = generate(bars, 103, 90, [None] * len(bars), None, 0.2, "both")
    assert sigs == []
