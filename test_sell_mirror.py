"""The SELL mirror of the operator's two-candle rule (band_rotation).

Built 2026-08-08 on the operator's explicit instruction -- "sell is reverse
from upper band that sit just genrate signal no need backtesting" -- after
being shown CHECKLIST C3, which records upper-band selling as measured across
five datasets and REJECTED. These tests do NOT claim the rule works. They
claim two things only: that it is the exact MIRROR of the buy rule, and that
adding it changed nothing about the buy rule.
"""
import band_rotation as br

STOP = br.OPERATOR_STOP_PTS


def _bar(t, o, h, l, c, u3=None, d3=None, vwap=None):
    return {"t": t, "o": o, "h": h, "l": l, "c": c,
            "u3": u3, "d3": d3, "vwap": vwap}


def test_sell_arms_on_a_u3_tag_and_triggers_below_the_reference_low():
    # 09:30 tags u3 and 09:33 closes under that candle's low -> one SELL.
    bars = [
        _bar("09:30", 100, 110, 95, 105, u3=108, d3=80, vwap=100),
        _bar("09:33", 105, 106, 90, 92, u3=108, d3=80, vwap=100),
    ]
    out = [r for r in br.detect_index_run(bars, stop_pts=STOP, side="SELL") if r]
    assert len(out) == 1
    r = out[0]
    assert r["side"] == "SELL"
    assert r["band"] == br.SELL_RUN_BAND == "u3"
    # The line that had to break is a LOW, so it is named one.
    assert r["ref_low"] == 95
    assert "ref_high" not in r
    assert "below that candle's low" in r["trigger"]


def test_the_same_bars_produce_no_buy():
    """The two sides read opposite ends of the bar. If one set of bars fired
    both, the mirror would be reading something other than the mirror image."""
    bars = [
        _bar("09:30", 100, 110, 95, 105, u3=108, d3=80, vwap=100),
        _bar("09:33", 105, 106, 90, 92, u3=108, d3=80, vwap=100),
    ]
    assert [r for r in br.detect_index_run(bars, stop_pts=STOP) if r] == []


def test_a_sell_stop_sits_above_the_band_it_armed_on():
    """A short's risk is upward, so the re-fire lock must clear on a HIGH
    through level + stop, never on a low under it."""
    bars = [
        _bar("09:30", 100, 110, 95, 105, u3=108, d3=80, vwap=100),
        _bar("09:33", 105, 106, 90, 92, u3=108, d3=80, vwap=100),
        # level 108 + 20 = 128; this bar's high clears it, so the lock lifts.
        _bar("09:36", 92, 130, 91, 129, u3=108, d3=80, vwap=100),
    ]
    st = br.run_states(bars, stop_pts=STOP, side="SELL")
    assert st[1]["state"] == "TRIGGERED"
    assert st[2]["exit_why"] == "stop"


def test_the_default_side_is_buy_and_is_untouched():
    """Nothing may reach the buy rule through the new parameter."""
    bars = [
        _bar("09:30", 100, 105, 90, 95, u3=120, d3=92, vwap=100),
        _bar("09:33", 95, 108, 94, 107, u3=120, d3=92, vwap=100),
    ]
    default = br.detect_index_run(bars, stop_pts=STOP)
    explicit = br.detect_index_run(bars, stop_pts=STOP, side="BUY")
    assert default == explicit
    got = [r for r in default if r]
    assert len(got) == 1 and got[0]["side"] == "BUY"
    assert got[0]["ref_high"] == 105 and "ref_low" not in got[0]


def test_an_unknown_side_reads_as_buy_rather_than_inventing_a_third_rule():
    bars = [
        _bar("09:30", 100, 105, 90, 95, u3=120, d3=92, vwap=100),
        _bar("09:33", 95, 108, 94, 107, u3=120, d3=92, vwap=100),
    ]
    assert (br.detect_index_run(bars, stop_pts=STOP, side="sideways")
            == br.detect_index_run(bars, stop_pts=STOP))


def test_the_0925_anchor_applies_to_the_sell_side_too():
    """The gate lives in run_states for both sides -- it is not a buy-only
    rule that the mirror quietly skipped."""
    bars = [
        _bar("09:20", 100, 110, 95, 105, u3=108, d3=80, vwap=100),
        _bar("09:23", 105, 106, 90, 92, u3=108, d3=80, vwap=100),
    ]
    assert [r for r in br.detect_index_run(bars, stop_pts=STOP, side="SELL") if r] == []
