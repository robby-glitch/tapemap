"""ux_gate: numbers about two records, never a verdict (spec 2026-09-20 §D)."""
import ux_gate as gate

T0 = 1789098300000


def _bar(t, ladder, vol=None, delta=None, h=None, l=None):
    lad = [{"p": p, "b": b, "s": s, "bt": 1, "st": 1} for p, b, s in ladder]
    v = vol if vol is not None else sum(b + s for _, b, s in ladder)
    d = delta if delta is not None else sum(b - s for _, b, s in ladder)
    ps = [p for p, _, _ in ladder]
    return {"t": t, "o": ps[0], "h": h if h is not None else max(ps), "l": l if l is not None else min(ps), "c": ps[-1],
            "vol": v, "buy": (v + d) / 2, "sell": (v - d) / 2, "delta": d, "ladder": lad}


def test_per_bar_measures_poc_distance_sign_and_ratio_on_the_given_grid():
    o = _bar(T0, [(100.0, 10, 2), (105.0, 3, 1)])
    u = _bar(T0, [(100.0, 2, 1), (105.0, 9, 1)])
    r = gate.per_bar(o, u, 5, 0)
    assert r["poc_rows"] == 1 and r["delta_sign"] == "agree" and abs(r["vol_ratio"] - 13 / 16) < 1e-9
    assert r["stacks"] == "neither" and r["unfinished"] == "neither" and r["tag"] == "M"


def test_per_bar_nulls_carry_a_why():
    o = _bar(T0, [(100.0, 5, 5)])
    u = _bar(T0, [(100.0, 5, 5)])
    r = gate.per_bar(o, u, 5, 0)
    assert r["delta_sign"] is None and r["delta_sign_why"] == "a delta of 0 has no sign"
    r2 = gate.per_bar(_bar(T0, [(100.0, 0, 0)], vol=0), u, 5, 0)
    assert r2["vol_ratio"] is None and r2["vol_ratio_why"] == "GoCharting volume is 0"
    r3 = gate.per_bar({"t": T0, "vol": 1, "delta": 1, "ladder": None}, u, 5, 0)
    assert r3["poc_rows"] is None and r3["poc_rows_why"] == "no POC on one side"


def test_session_joins_on_t_and_reports_the_named_fields():
    o = [_bar(T0, [(100.0, 10, 2), (105.0, 3, 1)]), _bar(T0 + 300_000, [(105.0, 1, 8)]), _bar(T0 + 600_000, [(110.0, 4, 4)])]
    u = [_bar(T0, [(100.0, 9, 1), (105.0, 3, 1)]), _bar(T0 + 300_000, [(110.0, 1, 8)])]
    for b in u:
        b["src"] = "ux"; b["exact"] = 2; b["reconstructed"] = 1; b["hidden"] = 1; b["unknown"] = 0; b["unpriced"] = 1
    s = gate.session(o, u, 5, 0)
    assert s["bars_joined"] == 2 and s["bars_ofd_only"] == 1 and s["bars_ux_only"] == 0
    assert s["poc_rows_median"] == 0.5 and s["poc_within_1"] == 1.0
    assert s["delta_sign_agree"] == 1.0
    assert abs(s["vol_ratio_median"] - (14 / 16 + 9 / 9) / 2) < 1e-9
    assert 0 < s["va_overlap"] <= 1 and s["hvn_jaccard"] is not None and s["tag"] == "M"
    assert s["exact_frac"] == 4 / 6 and s["hidden_frac"] == 2 / 23 and s["unknown_frac"] == 0.0
    assert s["unpriced_frac"] == 2 / 23


def test_session_with_nothing_to_join_says_so():
    s = gate.session([_bar(T0, [(100.0, 1, 1)])], [], 5, 0)
    assert s["bars_joined"] == 0 and s["poc_rows_median"] is None and s["poc_rows_median_why"] == "no joined bars"
    assert s["va_overlap"] is None and s["va_overlap_why"] == "no ux profile"
    assert s["lvn_jaccard"] is None and s["lvn_jaccard_why"] == "no LVN on one side"
