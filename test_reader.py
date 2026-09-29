"""reader.py -- the shadow leg engine: determinism, restart equivalence, WHO classes, the batched-OI screen,
spread-print exclusion, warm-up silence and data holes. Synthetic minutes only; nothing touches data/."""
from datetime import datetime

import reader

T0 = int(datetime.fromisoformat("2026-09-29T09:15:00+05:30").timestamp() * 1000)


def M(i, c, prev=None, vol=200.0, oi=None, buy=None, bk=True, nf=100, prints=(), cvol=None, nx=0, lx=0.0):
    o = prev if prev is not None else c
    buy = vol / 2 if buy is None else buy
    return {"t": T0 + i * 60000, "o": o, "h": max(o, c) + 0.5, "l": min(o, c) - 0.5, "c": c, "notrade": False,
            "vol": vol, "oi": oi, "src": "book", "cvol": cvol, "bk": bk, "bvol": vol if bk else None,
            "buy": buy if bk else None, "sell": (vol - buy) if bk else None, "prints": list(prints),
            "nx": nx, "lx": lx, "nf": nf if bk else 0, "spr": 1.0}


def path(points, **kw):
    """Closes walked linearly through (minute, price) points; per-minute extras from kw callables."""
    out, prev = [], None
    for (i0, p0), (i1, p1) in zip(points, points[1:]):
        for i in range(i0, i1):
            c = p0 + (p1 - p0) * (i - i0 + 1) / (i1 - i0)
            extra = {k: f(i) for k, f in kw.items()}
            out.append(M(i, round(c, 2), prev, **extra))
            prev = round(c, 2)
    return out


def eng(minutes, **kw):
    base = dict(idx="NIFTY", day="2026-09-29", lot=65, unit=5.0, prior_sigma=5.0)   # delta 15
    base.update(kw)
    return reader.run(minutes, **base)


ZIG = [(0, 100), (10, 160), (15, 130), (25, 190), (30, 160), (40, 220), (45, 190), (55, 250), (60, 230)]


def test_the_ruler_is_frozen_at_the_open():
    e = eng(path(ZIG))
    assert e.delta == 15.0
    e2 = eng(path([(0, 100), (5, 400), (10, 100)]))
    assert e2.delta == 15.0                                  # a wild day never re-sizes it


def test_determinism_same_input_same_legs():
    a, b = eng(path(ZIG)), eng(path(ZIG))
    assert [L["en"] for L in a.legs] == [L["en"] for L in b.legs]
    assert [(L["t0"], L["t1"], L["px0"], L["px1"]) for L in a.legs] == [(L["t0"], L["t1"], L["px0"], L["px1"]) for L in b.legs]
    assert len(a.legs) >= 6


def test_restart_equivalence_and_no_repaint():
    ms = path(ZIG, oi=lambda i: 1000 + 10 * i)
    live = reader.Engine(idx="NIFTY", day="2026-09-29", lot=65, unit=5.0, prior_sigma=5.0)
    seen = []
    for k, m in enumerate(ms, 1):
        live.step(m)
        rebuilt = eng(ms[:k])
        assert [L["en"] for L in rebuilt.legs] == [L["en"] for L in live.legs]       # as-of rebuild == incremental
        assert [L["en"] for L in live.legs][:len(seen)] == seen                       # confirmed legs never change
        seen = [L["en"] for L in live.legs]
        assert all(L["confirmed_at"] >= L["t1"] + 60000 for L in live.legs)


def test_a_reversal_inside_one_minute_waits_for_a_later_close():
    ms = path([(0, 100), (10, 160)])
    ms.append({**M(10, 140, 160), "h": 170.0})               # new high 170 and a close 30 below it, same minute
    e = eng(ms)
    assert not e.legs                                        # the order inside the minute is unknown
    ms.append(M(11, 140, 140))
    e = eng(ms)
    assert e.legs and e.legs[0]["px1"] == 170.0


def _one_leg(dirn, oi_step, buy_share):
    """One confirmed leg from the open (+/-60 over 10 minutes, then a 20-point reversal)."""
    p = [(0, 100), (10, 100 + 60 * dirn), (12, 100 + 40 * dirn), (14, 100 + 45 * dirn)]
    return eng(path(p, oi=lambda i: 50000 + oi_step * min(i, 10), buy=lambda i: 200 * buy_share if i < 10 else 100))


def test_who_new_longs():
    L = _one_leg(1, +100, 0.8).legs[0]
    assert (L["dir"], L["who"]["class"], L["who"]["aggressor"]) == (1, "new_longs", 1)
    assert not L["who"]["absorbed"]


def test_who_short_covering():
    assert _one_leg(1, -100, 0.8).legs[0]["who"]["class"] == "short_covering"


def test_who_new_shorts():
    L = _one_leg(-1, +100, 0.2).legs[0]
    assert (L["who"]["class"], L["who"]["aggressor"]) == ("new_shorts", -1)


def test_who_long_liquidation():
    assert _one_leg(-1, -100, 0.2).legs[0]["who"]["class"] == "long_liquidation"


def test_who_rotation_when_oi_is_flat():
    assert _one_leg(1, 0, 0.8).legs[0]["who"]["class"] == "rotation"


def test_who_absorbed_when_price_moves_against_the_aggressor():
    L = _one_leg(1, +100, 0.2).legs[0]                       # price up on net selling
    assert L["who"]["aggressor"] == -1 and L["who"]["absorbed"]
    assert "ABSORBED" in L["en"] and "bullish" not in L["en"].lower() and "bearish" not in L["en"].lower()


def test_expiring_contract_reads_or_roll():
    e = eng(path([(0, 100), (10, 160), (12, 140), (14, 145)], oi=lambda i: 50000 - 100 * min(i, 10),
                 buy=lambda i: 160), expiry="2026-09-29")
    L = e.legs[0]
    assert L["expiring"] and L["who"]["roll"] and "or roll" in L["en"] and "(ya roll)" in L["chip"]


def test_roll_window_counts_sessions_to_the_master_expiry():
    assert reader.roll_window("2026-09-23", "2026-09-29") == (True, 5)
    assert reader.roll_window("2026-09-22", "2026-09-29") == (False, 6)
    assert reader.roll_window("2026-09-29", None) == (False, None)


def test_batched_oi_screen_flags_a_publication_step():
    ms = [M(i, 100.0, oi=1000.0 + i, vol=50) for i in range(5)] + [M(5, 100.0, oi=4000.0, vol=50)]
    flags = reader.screen_oi(ms)
    assert flags[-1] == (5, 4000.0 - 1004.0, True)            # 2,996 lots of OI on 50 lots traded
    assert not any(p for _, _, p in flags[:-1])


def test_one_publication_step_is_never_read_as_positioning():
    ms = path([(0, 100), (10, 160), (12, 140), (14, 145)],
              oi=lambda i: 50000 + (-3000 if 4 <= i else 0) + (-5 * i), buy=lambda i: 160)
    L = eng(ms).legs[0]
    assert L["oi"]["state"] == "pub" and L["who"]["class"] == "oi_cant"
    assert "publication step" in L["en"]


def test_oi_is_read_with_a_one_update_tolerance():
    ms = path([(0, 100), (10, 160), (12, 140), (14, 145)], oi=lambda i: 50000 + (40 if i >= 10 else 0))
    L = eng(ms, prior_sigma=1.0).legs[0]
    assert L["oi"]["lo"] <= 0 <= L["oi"]["hi"]                # the step lands right after the extreme minute
    assert L["oi"]["state"] == "ok" and L["oi"]["moved"] == 0 and L["who"]["class"] == "rotation"


def test_spread_print_is_excluded_by_print_on_both_tapes():
    ms = path([(0, 100), (17, 160), (19, 140), (21, 145)], oi=lambda i: 50000.0, buy=lambda i: 130, cvol=lambda i: 200.0)
    for m in ms:                                              # every minute is a normal, candle-matched minute...
        m["nx"], m["lx"] = 40, 200.0                          # ...of 40 prints of 5 lots
    blk = ms[6]                                               # ...except 09:21: one 4,000-lot print, not in the candle
    blk.update(vol=4200.0, bvol=4200.0, buy=4130.0, sell=70.0, cvol=200.0,
               prints=[{"t": blk["t"] + 30000, "lots": 4000.0, "side": 1, "p": 130.0, "exact": False}])
    gc = []
    for s in range(0, 20, 5):
        lad = [{"p": 100 + s, "b": 60, "s": 40, "bt": 20, "st": 20}]
        if s == 5:
            lad.append({"p": 130.0, "b": 4000, "s": 0, "bt": 1, "st": 0})
        gc.append({"t": T0 + s * 60000, "vol": 5000.0 if s == 5 else 1000.0,
                   "delta": sum(z["b"] - z["s"] for z in lad), "ladder": lad, "arrived": T0 + (s + 5) * 60000})
    L = eng(ms, gc=gc).legs[0]
    kinds = {(e["tape"], e["kind"]) for e in L["excluded"]}
    assert ("UX", "spread print") in kinds and ("GC", "spread print") in kinds
    ux_raw = sum(m["buy"] - m["sell"] for m in ms[1:17])      # the leg: after the 09:15 pivot minute, to 09:31
    assert L["ux"]["d"] == round(ux_raw - 4000, 1)
    assert L["gc"]["state"] == "ok" and L["gc"]["bars"] == 2
    assert L["gc"]["d"] == round(gc[1]["delta"] + gc[2]["delta"] - 4000, 1)


def test_warm_up_ranks_are_silent_until_three_legs():
    ms = path(ZIG, buy=lambda i: 160)                         # every minute net buying: up legs get an efficiency
    e = eng(ms)
    ranked = [L["ux"] for L in e.legs if L["ux"].get("lam") is not None]
    assert ranked[0]["rank"] is None and ranked[0]["warming"] == "0 of 3"
    assert all(x["rank"] is None for x in ranked[:3])
    assert ranked[3]["rank"] is not None and ranked[3]["rank"][1] == 4
    assert "rank warming" in e.legs[0]["en"]


def test_a_data_hole_says_cant_check():
    ms = path([(0, 100), (20, 160), (22, 140), (24, 145)])
    for m in ms[:18]:                                         # no Upstox book for most of the leg
        m.update(bk=False, bvol=None, buy=None, sell=None, nf=0)
    L = eng(ms, gc_expected=True).legs[0]
    assert L["ux"]["state"] == "cant" and "no Upstox book" in L["ux"]["why"]
    assert L["gc"]["state"] == "cant" and "not received" in L["gc"]["why"]
    assert "CAN'T CHECK" in L["en"]


def test_a_thin_tape_falls_back_to_price_times_oi():
    ms = path([(0, 100), (10, 160), (12, 140), (14, 145)], nf=lambda i: 2, oi=lambda i: 500 + 5 * min(i, 10),
              vol=lambda i: 4.0, buy=lambda i: 3.0)
    L = eng(ms, idx="SENSEX", lot=20, prior_sigma=1.0).legs[0]
    assert L["ux"]["state"] == "thin" and L["who"]["aggressor"] == 0 and L["who"]["thin"]
    assert L["who"]["class"] == "new_longs" and "price × OI only" in L["en"]


def test_a_leg_carries_what_a_cross_index_layer_needs():
    L = eng(path(ZIG, oi=lambda i: 1000 + 10 * i)).legs[0]
    for k in ("idx", "t0", "t1", "dir", "px0", "px1", "pts", "d_ux", "d_gc", "doi", "who", "rank_ux"):
        assert k in L["x"]
    assert isinstance(L["x"]["t0"], int) and isinstance(L["x"]["t1"], int) and L["x"]["idx"] == "NIFTY"


def test_book_minutes_side_by_the_rupee_tick():
    def R(t, vtt, ltp, ltq, b, a, oi=6500):
        return {"t": t, "ltt": t, "ltp": ltp, "ltq": ltq, "vtt": vtt, "oi": oi, "b": [[b, 650]], "a": [[a, 650]]}
    rows = [R(T0 + 1000, 1000, 100.0, 65, 99.9, 100.0), R(T0 + 2000, 1065, 100.0, 65, 99.9, 100.0),
            R(T0 + 3000, 1195, 99.9, 130, 99.9, 100.0)]
    mins = reader.book_minutes(rows, 65, reader.rupee_tick(10.0))
    assert reader.rupee_tick(10.0) == 0.1
    assert len(mins) == 1 and mins[0]["buy"] == 1.0 and mins[0]["sell"] == 2.0 and mins[0]["nx"] == 2
    cm = reader.canonical(mins)
    assert cm[0]["src"] == "book" and cm[0]["bk"] and cm[0]["oi"] == 100.0


def test_the_threshold_sheet_is_one_place_and_has_no_lot_counts():
    keys = [k for k, _, _ in reader.SHEET]
    assert len(keys) == len(set(keys)) and set(keys) == set(reader.TH)
    assert all(reason for _, _, reason in reader.SHEET)


def _effort_day(last_top):
    """Three light up legs (60 pts on 1,200 net lots: 50 pts/1k), then one up leg to `last_top` on ten times the
    volume (a low progress-per-lot rank), then a reversal that confirms it. delta = 15 (ruler)."""
    ups = [(0, 10), (13, 23), (26, 36), (39, 49)]
    up = lambda i: any(a <= i < b for a, b in ups)                                  # noqa: E731
    vol = lambda i: 2000.0 if 39 <= i < 49 else 200.0                               # noqa: E731
    p = [(0, 100), (10, 160), (13, 140), (23, 200), (26, 180), (36, 240), (39, 220), (49, last_top),
         (52, last_top - 20), (55, last_top - 15)]
    return eng(path(p, vol=vol, buy=lambda i: vol(i) * (0.8 if up(i) else 0.5), oi=lambda i: 50000.0))


def test_a_big_leg_is_never_heavy_effort_little_progress():
    L = _effort_day(310).legs[-1]                                                   # +90 pts = 6 rulers
    assert L["dir"] == 1 and L["ux"]["rank"][0] == 1 and L["ux"]["low"]              # the least progress per lot...
    assert not L["who"]["absorbed"] and L["who"]["paid"]                            # ...but the move was paid
    assert "heavy effort, move paid" in L["en"] and "zor laga, move mila" in L["chip"]
    assert "little progress" not in L["en"] and "least progress per lot, 1 of 4" in L["en"]


def test_a_small_leg_on_heavy_effort_is_absorbed():
    L = _effort_day(245).legs[-1]                                                   # +26 pts < 2 rulers
    assert L["ux"]["low"] and L["who"]["absorbed"] and not L["who"]["paid"]
    assert "heavy effort, little progress" in L["en"]
