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


def test_unpriced_volume_reaches_the_bar_and_never_shares_a_number_with_unknown():
    L = ladder.Ladder(lot=65, tick=0.05, idx="NIFTY", day="2026-09-11")
    noltp_prev = {"t": T0 + 1000, "ltt": T0 + 1000, "ltp": None, "ltq": None, "vtt": 1000, "oi": None,
                  "tbq": None, "tsq": None, "b": [[100.00, 65]], "a": [[100.05, 65]]}
    noltp_cur = dict(noltp_prev, t=T0 + 2000, ltt=T0 + 2000, vtt=1065)
    L.step(noltp_prev)
    L.step(noltp_cur)
    bar = L.close_open()
    assert bar["unpriced"] == 65 / 65
    total = sum(r["b"] + r["s"] + r["u"] for r in bar["ladder"]) + bar["unpriced"]
    assert abs(total - bar["vol"]) < 1e-9


def test_min_gap_is_the_smallest_adjacent_price_step_on_either_side():
    row = R(1, 1000, 100.0, 65, [[100.00, 65], [99.90, 65]], [[100.05, 65], [100.10, 65]])
    assert ladder.min_gap(row) == 0.05
    assert ladder.min_gap(R(1, 1000, 100.0, 65, [[100.0, 65]], [[100.05, 65]])) == 0.05   # across the spread
    assert ladder.min_gap(R(1, 1000, 100.0, 65, [], [])) is None


def test_min_gap_skips_a_null_price_and_uses_the_remaining_levels():
    row = R(1, 1000, 100.0, 65, [[100.00, 65], [None, 65]], [[100.05, 65], [100.10, 65]])
    assert ladder.min_gap(row) == 0.05


# --- bars ---------------------------------------------------------------------

def test_bin_of_is_the_five_minute_open_in_epoch_ms():
    assert ladder.bin_of(T0) == T0 and ladder.bin_of(T0 + 299_999) == T0 and ladder.bin_of(T0 + 300_000) == T0 + 300_000
    assert ladder.hms_ist(T0) == "09:15:00"


def _four_frames():
    return [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 2000, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),           # exact buy at 100.05
            R(T0 + 3000, 1195, 100.05, 65, [[100.00, 65]], [[100.10, 65]], oi=500),   # recon: 65 eaten + 65 hidden
            R(T0 + 300_500, 1195, 100.05, 65, [[100.00, 65]], [[100.10, 65]])]        # next bin, quiet: closes bar 0


def test_a_bar_closes_when_a_frame_lands_in_the_next_bin_in_lots_with_counters():
    L = ladder.Ladder(lot=65, tick=0.05, idx="NIFTY", day="2026-09-11")
    out = [L.step(f) for f in _four_frames()]
    assert [b for b, _ in out[:3]] == [None, None, None]
    bar, fills = out[3]
    assert fills == [] and bar["t"] == T0 and bar["src"] == "ux" and bar["idx"] == "NIFTY" and bar["day"] == "2026-09-11"
    assert bar["o"] == 100.05 and bar["h"] == 100.05 and bar["l"] == 100.05 and bar["c"] == 100.05 and bar["oi"] == 500
    assert bar["vol"] == 3 and bar["buy"] == 3 and bar["sell"] == 0 and bar["unknown"] == 0 and bar["delta"] == 3
    assert bar["ladder"] == [{"p": 100.05, "b": 3, "s": 0, "u": 0, "bt": 3, "st": 0}]
    assert bar["frames"] == 3 and bar["exact"] == 1 and bar["reconstructed"] == 1 and bar["hidden"] == 1
    assert bar["vtt_resets"] == 0 and bar["lot_mismatch"] == 0 and bar["levels_seen"] == 2
    assert bar["lot"] == 65 and bar["lot_src"] == "given" and bar["tick"] == 0.05 and bar["tick_src"] == "given"
    assert bar["partial"] is False and bar["partial_why"] is None
    assert bar["rowSize"] is None and bar["rowAnchor"] == 0 and bar["fromTicks"] is True


def test_fill_events_carry_ltt_and_side_primary_first():
    L = ladder.Ladder(lot=65, tick=0.05)
    fs = [f for fr in _four_frames() for f in L.step(fr)[1]]
    assert fs[0] == {"ltt": T0 + 2000, "side": 1, "p": 100.05, "q": 65, "hidden": False}
    assert fs[1]["ltt"] == T0 + 3000 and fs[2]["hidden"] is True


def test_trading_frames_bin_by_ltt_not_arrival():
    L = ladder.Ladder(lot=65, tick=0.05)
    fr = _four_frames()
    late = R(T0 + 300_200, 1260, 100.05, 65, [[100.00, 65]], [[100.10, 65]], ltt=T0 + 299_000)   # arrived late, traded in bin 0
    for f in fr[:3]:
        L.step(f)
    assert L.step(late)[0] is None                    # still bin 0: no close
    bar, _ = L.step(fr[3])
    assert bar["vol"] == 4 and bar["exact"] == 2


def test_a_lot_mismatch_is_counted_and_kept_fractional():
    L = ladder.Ladder(lot=65, tick=0.05)
    L.step(R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    L.step(R(T0 + 2000, 1100, 100.05, 100, [[100.00, 65]], [[100.05, 65]]))
    bar = L.close_open()
    assert bar["lot_mismatch"] == 1 and abs(bar["vol"] - 100 / 65) < 1e-9


def test_lot_and_tick_are_inferred_and_say_so_when_not_given():
    L = ladder.Ladder()
    for f in _four_frames():
        bar, _ = L.step(f)
    assert bar["lot"] == 65 and bar["lot_src"] == "gcd" and bar["lot_why"] is None
    assert bar["tick"] == 0.05 and bar["tick_src"] == "inferred"


def test_no_trade_yet_means_no_lot_and_a_sentence():
    L = ladder.Ladder()
    L.step(R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    bar = L.close_open()
    assert bar["lot"] is None and bar["lot_src"] is None and bar["lot_why"] == "no traded volume yet to infer a lot from"
    assert bar["vol"] == 0 and bar["ladder"] == []


def test_the_first_bar_after_a_late_start_is_partial_with_the_record_start():
    L = ladder.Ladder(lot=65, tick=0.05)
    L.step(R(T0 + 120_000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    bar, _ = L.step(R(T0 + 300_500, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    assert bar["partial"] is True and bar["partial_why"] == "record starts at 09:17:00, bar opened at 09:15:00"


def test_a_vtt_reset_inside_the_bar_marks_it_partial():
    L = ladder.Ladder(lot=65, tick=0.05)
    L.step(R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    L.step(R(T0 + 2000, 900, 100.00, 65, [[100.00, 65]], [[100.05, 65]]))
    bar = L.close_open()
    assert bar["vtt_resets"] == 1 and bar["partial"] is True and bar["partial_why"] == "vtt reset 1 time(s) inside the bar"


def test_close_open_is_none_before_any_frame():
    assert ladder.Ladder().close_open() is None
