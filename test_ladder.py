"""The reconstruction, one pair of frames at a time (spec 2026-09-20 §C)."""
import ladder

T0 = 1789098300000            # 2026-09-11 09:15:00 IST, the bar-open epoch spec 1 uses


def R(t, vtt, ltp, ltq, b, a, ltt=None, oi=None):
    return {"t": t, "cts": None, "ltt": t if ltt is None else ltt, "ltp": ltp, "ltq": ltq,
            "vtt": vtt, "oi": oi, "tbq": None, "tsq": None, "b": b, "a": a}


def test_side_is_judged_against_the_previous_touch():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    assert ladder.side_of(100.05, prev) == 1          # at or through the ask: a buy
    assert ladder.side_of(100.00, prev) == -1         # at or through the bid: a sell
    assert ladder.side_of(100.04, prev) == 1          # inside, above mid
    assert ladder.side_of(100.01, prev) == -1         # inside, below mid
    assert ladder.side_of(100.025, prev) == 0         # exactly mid: unknown


def test_exact_case_one_trade_at_ltp_of_size_ltq():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]])
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "exact" and r["V"] == 65 and r["hidden"] == 0 and r["unknown"] == 0
    assert r["fills"] == [{"side": 1, "p": 100.05, "q": 65, "hidden": False}]


def test_reconstruction_marches_the_attacked_side_best_first():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65], [100.10, 65], [100.15, 65]])
    cur = R(2, 1130, 100.10, 65, [[100.00, 65]], [[100.15, 65]])      # V = 130 != ltq: two prints
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["hidden"] == 0
    assert r["fills"] == [{"side": 1, "p": 100.05, "q": 65, "hidden": False},
                          {"side": 1, "p": 100.10, "q": 65, "hidden": False}]


def test_the_march_stops_past_the_last_print_by_half_a_tick():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65], [100.10, 65]])
    cur = R(2, 1130, 100.05, 65, [[100.00, 65]], [])          # both asks gone, but ltp is 100.05
    r = ladder.attribute(prev, cur, 0.05)
    assert r["fills"][0] == {"side": 1, "p": 100.05, "q": 65, "hidden": False}
    assert r["fills"][1] == {"side": 1, "p": 100.05, "q": 65, "hidden": True}   # 100.10 is past ltp: not eaten
    assert r["hidden"] == 65


def test_residual_is_booked_hidden_at_ltp_when_the_book_refilled():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1130, 100.05, 65, [[100.00, 65]], [[100.05, 65]])      # V = 130, nothing visibly eaten
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["fills"] == [{"side": 1, "p": 100.05, "q": 130, "hidden": True}]
    assert r["hidden"] == 130


def test_the_other_side_is_only_eaten_up_to_the_last_print():
    """A tick away from ltp on the other side is refused and lands hidden: the
    method's floor (Order Flow Lab marches each side toward cur.ltp)."""
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1130, 100.05, 65, [[99.95, 65]], [[100.10, 65]])
    r = ladder.attribute(prev, cur, 0.05)
    assert [f["p"] for f in r["fills"]] == [100.05, 100.05] and r["fills"][1]["hidden"] and r["hidden"] == 65


def test_a_stale_ltq_larger_than_v_is_not_trusted():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1065, 100.05, 130, [[100.00, 65]], [[100.10, 65]])     # V = 65 < ltq = 130
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["fills"] == [{"side": 1, "p": 100.05, "q": 65, "hidden": False}]


def test_a_print_at_mid_with_no_side_is_unknown_never_split():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    cur = R(2, 1065, 100.025, 65, [[100.00, 65]], [[100.05, 65]])
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "exact" and r["unknown"] == 65 and r["fills"][0]["side"] == 0


def test_a_tie_in_the_reconstruction_falls_to_the_side_that_thinned_then_to_unknown():
    prev = R(1, 1000, 100.0, 65, [[100.00, 130]], [[100.05, 130]])
    cur = R(2, 1130, 100.025, 65, [[100.00, 130]], [[100.05, 0]])     # asks thinned: buys
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "recon" and r["fills"][0]["side"] == 1
    cur2 = R(2, 1130, 100.025, 65, [[100.00, 130]], [[100.05, 130]])  # nothing thinned: unknown
    r2 = ladder.attribute(prev, cur2, 0.05)
    assert r2["kind"] == "unknown" and r2["unknown"] == 130 and r2["fills"] == [{"side": 0, "p": 100.025, "q": 130, "hidden": False}]


def test_a_vtt_reset_and_a_quiet_frame_attribute_nothing():
    prev = R(1, 1000, 100.0, 65, [[100.00, 65]], [[100.05, 65]])
    assert ladder.attribute(prev, R(2, 900, 100.0, 65, [[100.00, 65]], [[100.05, 65]]), 0.05)["kind"] == "reset"
    assert ladder.attribute(prev, R(2, 1000, 100.0, 65, [[99.95, 65]], [[100.05, 65]]), 0.05)["kind"] == "quiet"
    assert ladder.attribute(None, prev, 0.05)["kind"] == "skip"


def test_volume_with_no_last_price_is_unpriced_and_says_so():
    """The one branch where fills do not sum to V: nothing can place it, so the
    counter carries it instead of the ladder."""
    prev = {"t": 1, "ltt": 1, "ltp": None, "ltq": None, "vtt": 1000, "oi": None, "tbq": None, "tsq": None,
            "b": [[100.00, 65]], "a": [[100.05, 65]]}
    cur = dict(prev, t=2, ltt=2, vtt=1130)
    r = ladder.attribute(prev, cur, 0.05)
    assert r["kind"] == "unknown" and r["fills"] == [] and r["unknown"] == 130 and r["unpriced"] == 130
    ok = ladder.attribute(prev, R(2, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]), 0.05)
    assert ok["unpriced"] == 0 and sum(f["q"] for f in ok["fills"]) + ok["unpriced"] == ok["V"]


def test_min_gap_is_the_smallest_adjacent_price_step_on_either_side():
    row = R(1, 1000, 100.0, 65, [[100.00, 65], [99.90, 65]], [[100.05, 65], [100.10, 65]])
    assert ladder.min_gap(row) == 0.05
    assert ladder.min_gap(R(1, 1000, 100.0, 65, [[100.0, 65]], [[100.05, 65]])) == 0.05   # across the spread
    assert ladder.min_gap(R(1, 1000, 100.0, 65, [], [])) is None
