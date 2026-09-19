"""prints.py: the extension's arithmetic, ported (spec §E). Hand cases here;
the parity pin against the extension's own code is test_parity_* (Task 6)."""
import prints


def _row(p, b=0, s=0, bt=0, st=0):
    return {"p": p, "b": b, "s": s, "bt": bt, "st": st}


def test_rebin_sums_into_row_buckets_and_sorts():
    # 23352.1/5 = 4670.42 -> 23350; 23350.8/5 = 4670.16 -> 23350; 23347.4/5 = 4669.48 -> 23345
    lad = [_row(23352.1, 1, 0, 1, 0), _row(23350.8, 0, 2, 0, 2), _row(23347.4, 3, 0, 2, 0)]
    rows = prints.rebin(lad, 5)
    assert [r["p"] for r in rows] == [23345.0, 23350.0]
    assert rows[1] == {"p": 23350.0, "b": 1, "s": 2, "bt": 1, "st": 2}
    assert rows[0] == {"p": 23345.0, "b": 3, "s": 0, "bt": 2, "st": 0}


def test_rebin_rounds_half_up_like_javascript():
    # 23352.5 / 5 = 4670.5 -> JS Math.round gives 4671 -> 23355; Python round() would give 23350
    assert prints.rebin([_row(23352.5, 1)], 5)[0]["p"] == 23355.0


def test_rebin_anchor_shifts_the_grid():
    assert prints.rebin([_row(23352.0, 1)], 5, anchor=2)[0]["p"] == 23352.0


def test_rebin_empty_or_missing_ladder_is_empty():
    assert prints.rebin([], 5) == [] and prints.rebin(None, 5) == []


def test_buy_imbalance_is_diagonal_ask_at_p_vs_bid_one_row_below():
    rows = [_row(100, b=1, s=1), _row(101, b=15, s=0)]      # ask 15 at 101 vs bid(=s) 1 at 100
    flags, stacks = prints.imbalances(rows)
    assert flags == [0, 1] and stacks == []


def test_sell_imbalance_is_bid_at_p_vs_ask_one_row_above():
    rows = [_row(100, b=0, s=15), _row(101, b=1, s=0)]      # bid 15 at 100 vs ask(=b) 1 at 101
    flags, _ = prints.imbalances(rows)
    assert flags == [-1, 0]


def test_min_lots_boundary_four_is_silent_five_fires():
    assert prints.imbalances([_row(100, s=1), _row(101, b=4)])[0] == [0, 0]
    assert prints.imbalances([_row(100, s=1), _row(101, b=5)])[0] == [0, 1]


def test_zero_side_floors_at_one_lot_the_extensions_rule():
    assert prints.imbalances([_row(100, s=0), _row(101, b=15)])[0] == [0, 1]   # 15 >= 3 * max(0, 1)
    assert prints.imbalances([_row(100, s=0), _row(101, b=2)])[0] == [0, 0]    # 2 < 5 lots


def test_a_sell_flag_never_overwrites_a_buy_flag_on_the_same_row():
    # row 101: buy imbalance vs row 100; row 101 also sell-dominant vs row 102 -> stays +1
    rows = [_row(100, s=1), _row(101, b=15, s=15), _row(102, b=1)]
    flags, _ = prints.imbalances(rows)
    assert flags == [0, 1, 0]


def test_stack_of_exactly_three_fires_and_two_does_not():
    three = [_row(100, s=1), _row(101, b=9), _row(102, b=9), _row(103, b=9)]
    flags, stacks = prints.imbalances(three)
    assert flags == [0, 1, 1, 1]
    assert stacks == [{"side": "buy", "low": 101, "high": 103, "run": 3}]
    two = [_row(100, s=1), _row(101, b=9), _row(102, b=9)]
    assert prints.imbalances(two)[1] == []


def test_bar_flags_poc_is_the_first_largest_row_and_unfinished_reads_the_raw_extremes():
    bar = {"vol": 100, "ladder": [_row(23350.0, 3, 3), _row(23355.0, 10, 2), _row(23360.0, 6, 6)]}
    f = prints.bar_flags(bar, 5)
    assert f["poc"] == 23355.0
    # unfinished: top row 23360 has b=6,s=6 >= max(3, 2) -> unfinished high; bottom 23350 b=3,s=3 -> unfinished low
    assert f["unfinished_high"] is True and f["unfinished_low"] is True
    bar2 = {"vol": 1000, "ladder": [_row(23350.0, 3, 3), _row(23360.0, 30, 0)]}   # floor is max(3, 20) = 20
    f2 = prints.bar_flags(bar2, 5)
    assert f2["unfinished_high"] is False and f2["unfinished_low"] is False


def test_bar_flags_none_without_a_ladder():
    assert prints.bar_flags({"vol": 5, "ladder": None}, 5) is None
    assert prints.bar_flags({"vol": 5, "ladder": []}, 5) is None


def _bar(t, ladder, o=None, h=None, l=None, c=None, buy=None, sell=None, delta=None, vol=None):
    b = {"t": t, "ladder": ladder, "o": o, "h": h, "l": l, "c": c}
    if buy is not None: b["buy"] = buy
    if sell is not None: b["sell"] = sell
    if delta is not None: b["delta"] = delta
    if vol is not None: b["vol"] = vol
    return b


def test_profile_sums_raw_ladder_prices_and_expands_two_rows_a_side():
    # rows: 100:1 101:2 102:10 103:2 104:1 105:1  total 17, 70% = 11.9
    # poc=102 (acc 10); up pair 103+104=3 vs down pair 101+100=3 -> tie goes up -> acc 13 >= 11.9 -> vah 104, val 102
    lad = [_row(100, 1), _row(101, 2), _row(102, 10), _row(103, 2), _row(104, 1), _row(105, 1)]
    pr = prints.profile([_bar(1, lad)])
    assert (pr["poc"], pr["vah"], pr["val"], pr["total"]) == (102, 104, 102, 17)
    assert [r["p"] for r in pr["rows"]] == [100, 101, 102, 103, 104, 105]


def test_profile_takes_the_larger_pair_whole():
    # poc=102(10); down pair 101+100 = 8 > up pair 103+104 = 2 -> take both down rows
    lad = [_row(100, 4), _row(101, 4), _row(102, 10), _row(103, 1), _row(104, 1)]
    pr = prints.profile([_bar(1, lad)])
    assert (pr["val"], pr["vah"]) == (100, 102)


def test_profile_ignores_bars_without_a_ladder_and_is_none_when_nothing_has_one():
    assert prints.profile([_bar(1, None), _bar(2, [])]) is None
    pr = prints.profile([_bar(1, None), _bar(2, [_row(100, 1)])])
    assert pr["poc"] == 100


def test_nodes_top_three_are_hvn_and_at_most_a_third_of_median_is_lvn():
    # 5-point bins: 100:50 105:40 110:30 115:10 120:2 125:9   median of [2,9,10,30,40,50] -> vals[3]=30 -> LVN <= 10.5
    lad = [_row(100, 50), _row(105, 40), _row(110, 30), _row(115, 10), _row(120, 2), _row(125, 9)]
    nd = prints.nodes(prints.profile([_bar(1, lad)]))
    assert [(n["p"], n["kind"]) for n in nd] == [(100, "HVN"), (105, "HVN"), (110, "HVN"), (115, "LVN"), (120, "LVN"), (125, "LVN")]
    assert prints.nodes(None) == []


def test_nodes_bin_rounds_half_up():
    # 23352.5 / 5 = 4670.5 -> bin 23355 (JS), not 23350
    nd = prints.nodes(prints.profile([_bar(1, [_row(23352.5, 5)])]))
    assert nd[0]["p"] == 23355


def test_with_cvd_is_a_prefix_sum_in_time_order():
    bars = [_bar(3, [], buy=1, sell=4), _bar(1, [], delta=5), _bar(2, [], buy=2, sell=1)]
    out = prints.with_cvd(bars)
    assert [(b["t"], b["delta"], b["cvd"]) for b in out] == [(1, 5, 5), (2, 1, 6), (3, -3, 3)]
    assert bars[0].get("cvd") is None          # inputs untouched


def test_with_cvd_restarts_from_zero_on_the_next_day():
    """CVD is anchored at the session open and reset daily (spec §J.1): it is
    called once PER DAY, and the second day's first cvd is its own first delta,
    not yesterday's carry."""
    d1 = [_bar(1, [], delta=5), _bar(2, [], delta=7)]
    d2 = [_bar(11, [], delta=-3), _bar(12, [], delta=1)]
    a, b = prints.with_cvd(d1), prints.with_cvd(d2)
    assert [x["cvd"] for x in a] == [5, 12]
    assert b[0]["cvd"] == b[0]["delta"] == -3 and b[1]["cvd"] == -2


def test_with_cvd_skips_a_bar_with_no_clock():
    """A record row with no `t` cannot be placed on any axis; it is skipped,
    never sorted against None (final review, 2026-09-19)."""
    out = prints.with_cvd([_bar(2, [], delta=1), {"ladder": [], "delta": 99}, _bar(1, [], delta=4)])
    assert [(x["t"], x["cvd"]) for x in out] == [(1, 4), (2, 5)]


def test_tm_marks_survive_a_prior_bar_with_no_extremes():
    """The exhaustion window reads only bars that HAVE both extremes -- a prior
    bar missing h/l used to raise KeyError and take the whole reply down."""
    bars = _seq(6) + [_bar(1500, [], delta=1, vol=100),
                      _bar(2000, [], o=23000, h=23020, l=22990, c=23010, delta=-5, vol=100)]
    marks, _ = prints.tm_marks(bars)
    assert [m["kind"] for m in marks if m["kind"] == "exhaustion"] == ["exhaustion"]


def test_prior_levels_one_per_day_newest_first():
    d1 = ("2026-09-18", [_bar(1, [_row(100, 1), _row(101, 5), _row(102, 1)])])
    d2 = ("2026-09-17", [_bar(1, [_row(200, 5)])])
    out = prints.prior_levels([d1, d2])
    assert [(o["day"], o["poc"]) for o in out] == [("2026-09-18", 101), ("2026-09-17", 200)]


def test_naked_poc_survives_until_a_later_bar_straddles_it_wick_counts():
    older = ("2026-09-17", [_bar(1, [_row(200, 5)])])                 # poc 200
    newer = ("2026-09-18", [_bar(1, [_row(300, 5)], h=310, l=295)])   # never touched 200
    today = [_bar(10, [], h=250, l=240), _bar(11, [], h=205, l=199), _bar(12, [], h=201, l=200)]
    out = prints.naked([newer, older], today)
    assert {o["day"]: o for o in out}["2026-09-17"] == {"day": "2026-09-17", "poc": 200, "touched_t": 11}
    assert {o["day"]: o for o in out}["2026-09-18"] == {"day": "2026-09-18", "poc": 300, "touched_t": None}


def test_naked_poc_gapped_over_stays_naked_the_extensions_own_rule():
    """A later bar whose WHOLE range is above the POC never straddles it, so the
    POC stays naked -- market.js:75, and spec §J.2 keeps it that way so the
    two tools agree on which POCs are naked."""
    older = ("2026-09-17", [_bar(1, [_row(200, 5)])])                 # poc 200
    today = [_bar(10, [], h=230, l=210), _bar(11, [], h=240, l=220)]  # gapped over, never back
    out = prints.naked([older], today)
    assert out == [{"day": "2026-09-17", "poc": 200, "touched_t": None}]


def test_naked_poc_touched_on_a_prior_newer_day_is_not_listed():
    older = ("2026-09-17", [_bar(1, [_row(200, 5)])])
    newer = ("2026-09-18", [_bar(1, [_row(300, 5)], h=210, l=190)])   # traded through 200
    out = prints.naked([newer, older], [])
    assert [o["day"] for o in out] == ["2026-09-18"]


import json
import os

import pytest

FIXTURE = os.path.join("test", "fixtures", "prints_expected_2026-09-11.json")
FIXTURE_ROW1 = os.path.join("test", "fixtures", "prints_expected_2026-09-11_row1.json")
# Row 5 is the chart's own row size and this day has ZERO stacks and ZERO
# unfinished auctions at it -- a true-negative pin for both fields. Row 1 is
# decode.js's own DEFAULTS.rowSize and the same day carries 68 stacks there, so
# the stack code is pinned against the extension on real rows, not on nothing.
FIXTURES = [FIXTURE, FIXTURE_ROW1]
OFD = r"C:\Users\kaam\Desktop\Go charting\orderflow-desk\test\session-2026-09-11.ofd.json"


def _parity(fixture=FIXTURE):
    if not os.path.exists(OFD):
        pytest.skip(f"the extension's recorded day is not at {OFD} \u2014 parity unpinned")
    exp = json.load(open(fixture, encoding="utf-8"))
    bars = [b for b in json.load(open(OFD, encoding="utf-8"))["bars"] if isinstance(b.get("ladder"), list) and b["ladder"]]
    bars.sort(key=lambda b: b["t"])
    assert len(bars) == len(exp["bars"]) == 77
    return exp, bars


def test_the_row_one_fixture_carries_the_stacks_the_row_five_one_cannot():
    """The reason the second fixture exists, pinned so it can never quietly
    become another true-negative: 68 stacks [M], measured 2026-09-19."""
    exp = json.load(open(FIXTURE_ROW1, encoding="utf-8"))
    assert exp["rowSize"] == 1
    assert sum(len(b["stacks"]) for b in exp["bars"]) == 68


@pytest.mark.parametrize("fixture", FIXTURES)
def test_parity_per_bar_rows_flags_poc_and_unfinished_match_the_extension(fixture):
    exp, bars = _parity(fixture)
    for e, b in zip(exp["bars"], bars):
        assert e["t"] == b["t"]
        rows = prints.rebin(b["ladder"], exp["rowSize"], exp["rowAnchor"])
        assert rows == e["rows"], f"rows differ at t={b['t']}"
        f = prints.bar_flags(b, exp["rowSize"], exp["rowAnchor"])
        assert f["stacks"] == e["stacks"], f"stacks differ at t={b['t']}"
        assert f["poc"] == e["poc"], f"poc differs at t={b['t']}"
        assert f["unfinished_high"] == e["unfinished_high"] and f["unfinished_low"] == e["unfinished_low"], f"unfinished differs at t={b['t']}"


@pytest.mark.parametrize("fixture", FIXTURES)
def test_parity_session_profile_and_nodes_match_the_extension(fixture):
    exp, bars = _parity(fixture)
    pr = prints.profile(bars)
    assert (pr["poc"], pr["vah"], pr["val"], pr["total"]) == (exp["profile"]["poc"], exp["profile"]["vah"], exp["profile"]["val"], exp["profile"]["total"])
    assert prints.nodes(pr) == exp["nodes"]

def _seq(n, delta=1, rng=10, vol=100, base=23000, step=0):
    """n closed bars with a flat profile: delta, range, volume as given."""
    return [_bar(1000 + i, [], o=base + i * step, h=base + i * step + rng, l=base + i * step, c=base + i * step + 1,
                 delta=delta, vol=vol) for i in range(n)]


def test_pct_rank_needs_six_priors_and_is_the_fraction_strictly_below():
    assert prints.pct_rank([1, 2, 3, 4, 5], 3) is None
    assert prints.pct_rank([1, 2, 3, 4, 5, 6], 3) == 2 / 6
    assert prints.pct_rank([1, 2, 3, 4, 5, 6], 6) == 5 / 6


def test_tm_absorption_fires_on_big_delta_small_range_close_against_it():
    bars = _seq(6) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23000, delta=50, vol=100)]   # |delta| top, range 4 <= median 10, delta>0 & c<=o
    marks, why = prints.tm_marks(bars)
    assert why is None
    abs_ = [m for m in marks if m["kind"] == "absorption"]
    assert len(abs_) == 1 and abs_[0]["side"] == -1 and abs_[0]["p"] == 23004 and abs_[0]["src"] == "tm" and abs_[0]["tag"] == "I"
    assert "absorbed" in abs_[0]["why"]


def test_tm_absorption_silent_one_step_off_each_rule():
    # range not small enough (11 > median 10)
    assert not [m for m in prints.tm_marks(_seq(6) + [_bar(2000, [], o=23000, h=23011, l=23000, c=23000, delta=50, vol=100)])[0] if m["kind"] == "absorption"]
    # close agrees with delta
    assert not [m for m in prints.tm_marks(_seq(6) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23003, delta=50, vol=100)])[0] if m["kind"] == "absorption"]
    # |delta| not in the top quarter (priors all 50, this bar 10 -> rank 0)
    assert not [m for m in prints.tm_marks(_seq(6, delta=50) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23000, delta=10, vol=100)])[0] if m["kind"] == "absorption"]


def test_tm_exhaustion_new_high_on_non_positive_delta_is_bearish_at_the_high():
    bars = _seq(6, rng=10, step=0) + [_bar(2000, [], o=23005, h=23020, l=23004, c=23010, delta=-5, vol=100)]   # h 23020 > prior max 23010
    ex = [m for m in prints.tm_marks(bars)[0] if m["kind"] == "exhaustion"]
    assert len(ex) == 1 and ex[0]["side"] == -1 and ex[0]["p"] == 23020


def test_tm_exhaustion_new_low_on_non_negative_delta_is_bullish_and_needs_six_priors():
    bars = _seq(6, rng=10) + [_bar(2000, [], o=22999, h=23001, l=22990, c=22995, delta=3, vol=100)]     # l 22990 < prior min 23000
    ex = [m for m in prints.tm_marks(bars)[0] if m["kind"] == "exhaustion"]
    assert len(ex) == 1 and ex[0]["side"] == 1 and ex[0]["p"] == 22990
    assert prints.tm_marks(_seq(5) + bars[-1:])[0] == []


def test_tm_exhaustion_silent_when_delta_agrees_with_the_extreme():
    bars = _seq(6, rng=10) + [_bar(2000, [], o=23005, h=23020, l=23004, c=23010, delta=5, vol=100)]
    assert not [m for m in prints.tm_marks(bars)[0] if m["kind"] == "exhaustion"]


def test_tm_climax_top_decile_volume_with_two_sided_prints():
    bars = _seq(9, vol=100) + [_bar(2000, [], o=23000, h=23010, l=23000, c=23008, delta=10, vol=1000)]   # vol rank 1.0, |d|/vol 0.01
    cl = [m for m in prints.tm_marks(bars)[0] if m["kind"] == "climax"]
    assert len(cl) == 1 and cl[0]["side"] == 0 and cl[0]["p"] == 23010          # closed near the high
    bars[-1]["delta"] = 200                                                       # 0.2 > 0.15 lopsided -> not a climax
    assert not [m for m in prints.tm_marks(bars)[0] if m["kind"] == "climax"]


def test_tm_first_six_bars_fire_nothing_and_say_why():
    marks, why = prints.tm_marks(_seq(4))
    assert marks == [] and why == "first six bars: nothing to rank against"


def test_tm_is_pure():
    bars = _seq(8) + [_bar(2000, [], o=23000, h=23004, l=23000, c=23000, delta=50, vol=100)]
    assert prints.tm_marks(bars) == prints.tm_marks(bars)


def test_tm_climax_fires_on_a_repeated_top_decile_volume_not_only_a_new_max():
    # nine quiet bars, then two 1000-lot bars: the second ties the max, is in the top decile, and must still fire
    bars = _seq(9, vol=100) + [_bar(2000, [], o=23000, h=23010, l=23000, c=23008, delta=10, vol=1000),
                               _bar(2001, [], o=23008, h=23016, l=23006, c=23014, delta=12, vol=1000)]
    cl = [m for m in prints.tm_marks(bars)[0] if m["kind"] == "climax"]
    assert [m["t"] for m in cl] == [2000, 2001]
