"""Tests for measure.py — synthetic bars, every scoring path, no network."""
import pytest

from measure import causal_R, direction, score_day, wilson


def mk_bars(closes, spread=1.0, start_min=0):
    """Flat-spread synthetic bars; times run from 10:00 + start_min."""
    bars = []
    for i, c in enumerate(closes):
        m = 600 + start_min + i
        bars.append({"t": f"{m//60:02d}:{m%60:02d}",
                     "h": c + spread, "l": c - spread, "c": c})
    return bars


# R fixed via prior_R (warmup > len) so exits are deterministic: R=10 ->
# stop 0.7R=7pts, target 1.3R=13pts.
KW = dict(warmup=999, prior_R=10.0)


def sig(t, dir_, kind="X"):
    return {"t": t, "kind": kind, "dir": dir_}


def test_win_first_touch_intrabar():
    closes = [100] * 5 + [100, 105, 112.5, 100]     # h=113.5 >= target 113
    bars = mk_bars(closes)
    recs = score_day(bars, [sig("10:05", 1)], **KW)
    assert [r["outcome"] for r in recs] == ["win"]
    assert recs[0]["pts"] == pytest.approx(13 - 1.5)


def test_loss_and_both_in_bar_is_loss():
    # bar at 10:06 has h=113.5 (target) AND l=92.5 (stop) -> conservative loss
    bars = mk_bars([100] * 6 + [103], spread=10.5)
    recs = score_day(bars, [sig("10:05", 1)], **KW)
    assert [r["outcome"] for r in recs] == ["loss"]
    assert recs[0]["pts"] == pytest.approx(-7 - 1.5)


def test_timeout_marks_to_close():
    bars = mk_bars([100] * 60, spread=0.5)          # never hits either side
    recs = score_day(bars, [sig("10:05", 1)], **KW)
    assert [r["outcome"] for r in recs] == ["timeout"]
    assert recs[0]["pts"] == pytest.approx(0 - 1.5)


def test_eod_marks_open_trade():
    bars = mk_bars([100] * 30, spread=0.5, start_min=310)   # 15:10..15:39
    recs = score_day(bars, [sig("15:12", 1)], **KW)
    assert [r["outcome"] for r in recs] == ["eod"]


def test_no_fresh_entries_at_eod():
    bars = mk_bars([100] * 10, spread=0.5, start_min=325)   # 15:25..
    recs = score_day(bars, [sig("15:26", 1)], **KW)
    assert recs == []


def test_cooldown_collapses_same_direction():
    closes = [100] * 5 + [101, 102, 103, 104, 113]
    bars = mk_bars(closes)
    recs = score_day(bars, [sig("10:05", 1), sig("10:07", 1)], **KW)
    outcomes = sorted(r["outcome"] for r in recs)
    assert outcomes == ["collapsed", "win"]


def test_reversal_closes_and_flips():
    closes = [100] * 5 + [100, 102, 104, 104, 104, 90]
    bars = mk_bars(closes)
    recs = score_day(bars, [sig("10:05", 1), sig("10:08", -1)], **KW)
    by = {r["outcome"]: r for r in recs}
    assert set(by) == {"reversal", "win"}            # long closed at 104 -> +4-1.5
    assert by["reversal"]["pts"] == pytest.approx(4 - 1.5)
    assert by["win"]["dir"] == -1                    # short target 104-13=91


def test_separate_kinds_do_not_cooldown():
    closes = [100] * 5 + [100, 105, 112.5, 100]
    bars = mk_bars(closes)
    recs = score_day(bars, [sig("10:05", 1, "A"), sig("10:05", 1, "B")], **KW)
    assert [r["outcome"] for r in recs] == ["win", "win"]


def test_portfolio_mode_single_slot():
    closes = [100] * 5 + [100, 105, 112.5, 100]
    bars = mk_bars(closes)
    recs = score_day(bars, [sig("10:05", 1, "A"), sig("10:05", 1, "B")],
                     portfolio=True, **KW)
    assert sorted(r["outcome"] for r in recs) == ["collapsed", "win"]


def test_warmup_skip_without_prior_R():
    bars = mk_bars([100] * 60)
    recs = score_day(bars, [sig("10:05", 1)], warmup=999, prior_R=None)
    assert [r["outcome"] for r in recs] == ["skipped_warmup"]


def test_causal_R_no_lookahead():
    closes = [100 + (i % 7) for i in range(120)]
    bars = mk_bars(closes)
    r60 = causal_R(bars, warmup=45)[60]
    bars2 = [dict(b) for b in bars]
    for b in bars2[61:]:                             # mutate ONLY the future
        b["h"] += 500
        b["l"] -= 500
    assert causal_R(bars2, warmup=45)[60] == r60


def test_wilson_known_value():
    lo, hi = wilson(50, 100)
    assert lo == pytest.approx(0.404, abs=0.003)
    assert hi == pytest.approx(0.596, abs=0.003)


def test_direction_map_core():
    assert direction("PRESS", "BULLISH rotation: ...") == 1
    assert direction("DIVERGENCE", "FUT new session high ...") == -1
    assert direction("TRAP-SPRUNG", "", {"side": "BULL"}) == -1
    assert direction("SQUEEZE-RISK", "... upside squeeze risk building") == 1
    assert direction("STATE", "BALANCE") == 0
