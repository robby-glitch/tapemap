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
