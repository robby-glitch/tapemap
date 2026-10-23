"""HOLD v2 (hold2.py, HOLD-V2-PREREG.md, research-findings §1m): one test per rule, the port against the extension, the
scorer's gate. Prices are futures; minutes are IST minutes of the day (600 = 10:00)."""
import json
import os

import pytest

import fronts
import hold2


def one(m, h, l, c, vwap=None):
    b = {"s": m * 60, "h": h, "l": l, "c": c}
    if vwap is not None:
        b["vwap"] = vwap
    return b


def push(close, d, origin, U, c=None):
    return {"s": (close - 5) * 60, "t": hold2.hm(close - 5), "close": close, "d": d, "origin": origin,
            "c": origin if c is None else c, "U": U, "src": "gc"}


TR = {"E": 22475.0, "line0": 22515.0}          # a DOWN position, risk 40


def flat(m0, m1, h=22480, l=22460, c=22470):
    return [one(m, h, l, c) for m in range(m0, m1)]


# ---- the push: v2.js flowState's PUSH, ported ---------------------------------------------------------------------

F = {"slot_absd": {str(k): 100.0 for k in range(37, 62)}, "slot_range": {str(k): 20.0 for k in range(37, 62)},
     "slot_vp10": {str(k): 50.0 for k in range(37, 62)},
     "size": {"q": [i / 30 for i in range(101)], "n": 500}, "res_min": 0.25}       # q[90] = 3.0


def bar5(m, o, c, delta, vol=1000, src="gc"):
    px = [x for x in (o, c) if x is not None]
    return {"s": m * 60, "o": o, "h": max(px) + 2 if px else None, "l": min(px) - 2 if px else None,
            "c": c, "vol": vol, "delta": delta, "src": src}


def test_push_is_size_p90_and_result_quarter_of_the_slot_range_and_never_thin():
    m = 600                                                     # slot 40 = 10:00-10:15
    assert hold2.state(bar5(m, 22500, 22490, -400), F)["state"] == "PUSH"           # SIZE 4 >= 3, R 0.5
    assert hold2.state(bar5(m, 22500, 22490, -400), F)["dir"] == -1
    assert hold2.state(bar5(m, 22500, 22496, -400), F)["state"] == "CLIMAX"         # R 0.2 < 0.25
    assert hold2.state(bar5(m, 22500, 22490, -250), F)["state"] is None             # SIZE 2.5 < p90
    assert hold2.state(bar5(m, 22500, 22490, -400, vol=50), F)["state"] is None     # thin: vol <= the slot's p10
    assert hold2.state(bar5(m, None, 22490, -400), F)["state"] == "?"               # R cannot be read
    p = hold2.pushes([bar5(m, 22500, 22490, -400)], {"gc": F})
    assert [(x["close"], x["d"], x["origin"]) for x in p] == [(605, -1, 22500)]
    assert p[0]["U"] == pytest.approx(max(hold2.sigmas([bar5(m, 22500, 22490, -400)])[0], 22.5))
    assert hold2.pushes([bar5(m, 22500, 22490, -400, src="ux")], {"gc": F}) == []    # its own source's table only


def test_the_port_gives_the_extensions_own_flow_state_on_its_recorded_days():
    """tools/gen_push_expected.mjs ran v2.js flowState + market.js vwapSeries over the extension's own test days; the port
    must give the same state (PUSH / CLIMAX / '?'), side and U on every bar."""
    exp = json.load(open(os.path.join("test", "fixtures", "push_expected.json"), encoding="utf-8"))
    ofd = r"C:\Users\kaam\Desktop\Go charting\orderflow-desk\test"
    if not os.path.exists(ofd):
        pytest.skip(f"the extension's recorded days are not at {ofd}")
    n_push = 0
    for day, e in exp["days"].items():
        bars = json.load(open(os.path.join(ofd, f"session-{day}.ofd.json"), encoding="utf-8"))["bars"]
        Fd = json.load(open(os.path.join(ofd, f"rank_ref_NIFTY_{day}.json"), encoding="utf-8"))["flow"]
        bs = [dict(b, s=(b["t"] // 1000 + 19800) % 86400, src="gc") for b in bars]
        got = [hold2.state(b, Fd) for b in bs]
        for b, g, x, sg in zip(bs, got, e["bars"], hold2.sigmas(bs)):
            want = x["state"] if x["state"] in ("PUSH", "CLIMAX", "?") else None
            assert g["state"] == want, (day, b["t"])
            if want == "PUSH":
                assert g["dir"] == x["dir"] and max(sg, 0.001 * b["o"]) == pytest.approx(x["U"], abs=1e-9)
        n_push += sum(1 for x in e["bars"] if x["state"] == "PUSH")
        assert len(hold2.pushes(bs, {"gc": Fd})) == sum(1 for x in e["bars"] if x["state"] == "PUSH")
    assert n_push == 33                                         # 7 + 4 + 4 + 3 + 7 + 8: real pushes were pinned


def test_nifty_uses_gocharting_and_falls_back_to_upstox_only_for_a_bar_it_lacks():
    gc = [bar5(600, 22500, 22490, -400), bar5(605, None, None, 10)]                  # 10:05 has no candle
    ux = [bar5(600, 22501, 22491, -999, src=None), bar5(605, 22490, 22480, -300, src=None),
          bar5(610, 22480, 22470, -50, src=None)]
    got = hold2.source_bars(gc, ux)
    assert [(b["s"] // 60, b["src"], b["delta"]) for b in got] == [(600, "gc", -400), (605, "ux", -300), (610, "ux", -50)]


# ---- the line ------------------------------------------------------------------------------------------------------

def test_the_trail_moves_only_toward_price():
    ones = flat(601, 640)
    ps = [push(610, -1, 22490, 20),                           # -> 22495 (from 22515)
          push(615, -1, 22492, 40),                           # 22502: farther from price than 22495 -> ignored
          push(620, -1, 22480, 8)]                            # -> 22482
    r = hold2.exit_v2(-1, TR, 601, ones + [one(640, 22483, 22460, 22470)], ps, {})
    assert [m["to"] for m in r["moves"]] == [22495.0, 22482.0]
    assert r["how"] == "line_push" and r["exit"] == 22482.0 and r["exit_t"] == "10:41"
    assert r["R"] == pytest.approx((22475 - 22482) / 40, abs=1e-4)        # on the initial risk


def test_a_push_origin_outside_the_line_and_price_moves_nothing():
    ones = flat(601, 640)                                      # price 22470, line 22515
    ps = [push(610, -1, 22520, 10),                           # origin beyond the line
          push(615, -1, 22465, 10),                           # origin beyond price (22470 > 22465)
          push(620, +1, 22490, 10),                           # the other side's push
          push(601, -1, 22490, 10)]                           # closed at the entry close: not after entry
    r = hold2.exit_v2(-1, TR, 601, ones, ps, {})
    assert r["moves"] == [] and r["how"] == "mark" and r["line"] == 22515.0


def test_the_lock_holds_breakeven_once_mfe_reaches_2r():
    ones = flat(601, 605) + [one(605, 22470, 22396, 22400)]    # MFE 79 < 80: no lock
    r = hold2.exit_v2(-1, TR, 601, ones + [one(606, 22476, 22400, 22470)], [], {})
    assert r["lock_t"] is None and r["how"] == "mark"
    ones = flat(601, 605) + [one(605, 22470, 22395, 22400)]    # MFE 80 = 2R: locked from the next bar
    r = hold2.exit_v2(-1, TR, 601, ones + [one(606, 22476, 22400, 22470)], [], {})
    assert r["lock_t"] == "10:06" and r["how"] == "line_lock" and r["exit"] == 22475.0 and r["R"] == 0.0


def test_the_line_is_touched_intrabar_never_on_a_close():
    ones = [one(601, 22480, 22470, 22472), one(602, 22516, 22470, 22471)]    # the high pokes it, closes back below
    r = hold2.exit_v2(-1, TR, 601, ones, [], {})
    assert r["how"] == "line_init" and r["exit"] == 22515.0 and r["R"] == -1.0 and r["exit_t"] == "10:03"


def unw(c, spot, peak_spot, k=22500.0, peak_at="10:01", U=0.0):
    """A 3-min close whose trend-side front reads UNWINDING, with the chain spot then and at the front's peak minute, and
    the U of the break buffer (Amendment 2; 0 = no buffer, Amendment 1's bare test)."""
    return {"c": c, "trend_state": fronts.UNWINDING, "k": k, "peak_at": peak_at, "spot": spot, "peak_spot": peak_spot,
            "U": U}


def test_stalled_never_exits_and_unwinding_against_the_writers_exits_at_that_close():
    # AMENDMENT 1: DOWN = CE writers; spot 22450 above the 22440 at their peak minute -> they are losing: gave up
    closes = {603: {"c": 22440, "trend_state": fronts.STALLED}, 606: unw(22420, 22450, 22440)}
    ones = [one(m, 22450, 22410, 22440 if m < 605 else 22420) for m in range(601, 610)]
    r = hold2.exit_v2(-1, TR, 601, ones, [], closes)
    assert r["how"] == "gave_up" and r["exit"] == 22420 and r["exit_t"] == "10:06" and r["stalled"] == ["10:03"]


def test_unwinding_with_price_still_in_the_writers_favour_is_munafa_booking_never_an_exit():
    closes = {606: unw(22420, 22430, 22440)}                    # spot still below the peak minute's: CE writers winning
    ones = [one(m, 22450, 22410, 22440) for m in range(601, 640)]
    r = hold2.exit_v2(-1, TR, 601, ones, [], closes)
    assert r["how"] == "mark" and r["munafa"] == [{"t": "10:06", "k": 22500.0, "spot": 22430, "peak_spot": 22440,
                                                  "peak_at": "10:01", "U": 0.0, "read": "munafa"}]
    eq = hold2.exit_v2(-1, TR, 601, ones, [], {606: unw(22420, 22440, 22440)})     # level: not losing, not an exit
    assert eq["how"] == "mark" and len(eq["munafa"]) == 1
    unk = hold2.exit_v2(-1, TR, 601, ones, [], {606: unw(22420, None, 22440)})     # price side unread: never a verdict
    assert unk["how"] == "mark" and unk["munafa"] == [] and unk["unwind_cnc"] == ["10:06"]


def test_the_gave_up_side_test_mirrors_for_up_and_pe_writers():
    ones = [one(m, 22450, 22410, 22440) for m in range(601, 640)]
    up = {"E": 22430.0, "line0": 22390.0}
    assert hold2.exit_v2(1, up, 601, ones, [], {606: unw(22420, 22430, 22440)})["how"] == "gave_up"   # spot below: PE losing
    r = hold2.exit_v2(1, up, 601, ones, [], {606: unw(22420, 22450, 22440)})                         # spot above: PE winning
    assert r["how"] == "mark" and r["munafa"][0]["t"] == "10:06"


def test_amendment_2_the_losing_side_needs_a_quarter_u_beyond_the_peak_minutes_spot():
    ones = [one(m, 22450, 22410, 22440) for m in range(601, 640)]
    # DOWN / CE writers, peak spot 22440, U 40 -> the edge is 22450
    inside = hold2.exit_v2(-1, TR, 601, ones, [], {606: unw(22420, 22449, 22440, U=40.0)})
    assert inside["how"] == "mark" and inside["munafa"][0]["read"] == "chop"            # within 0.25U: no exit
    assert hold2.exit_v2(-1, TR, 601, ones, [], {606: unw(22420, 22450, 22440, U=40.0)})["how"] == "mark"   # at the edge
    out = hold2.exit_v2(-1, TR, 601, ones, [], {606: unw(22420, 22451, 22440, U=40.0)})
    assert out["how"] == "gave_up" and out["exit_t"] == "10:06"                          # beyond it: gave up
    up = {"E": 22430.0, "line0": 22390.0}                                                # UP / PE writers: mirrored
    r = hold2.exit_v2(1, up, 601, ones, [], {606: unw(22420, 22431, 22440, U=40.0)})
    assert r["how"] == "mark" and r["munafa"][0]["read"] == "chop"
    assert hold2.exit_v2(1, up, 601, ones, [], {606: unw(22420, 22429, 22440, U=40.0)})["how"] == "gave_up"
    assert hold2.losing(-1, 22451, 22440, 40.0) == "lose" and hold2.losing(1, 22429, 22440, 40.0) == "lose"
    assert hold2.losing(-1, 22430, 22440, 40.0) == "munafa" and hold2.losing(-1, 22451, 22440, None) is None


def test_marked_at_1520_when_nothing_fires():
    r = hold2.exit_v2(-1, TR, 601, [one(m, 22450, 22440, 22445) for m in range(601, 925)], [], {})
    assert r["how"] == "mark" and r["exit_t"] == "15:20" and r["exit"] == 22445


def test_with_no_push_reference_the_trail_is_inactive_and_says_so():
    why = "push ? ref nahi — SENSEX 5-min bars are not rankable"
    r = hold2.exit_v2(-1, TR, 601, flat(601, 630), None, {}, trail_why=why)
    assert r["trail"] == why and r["moves"] == [] and r["line"] == 22515.0


# ---- FADE -> RIDE at VWAP ----------------------------------------------------------------------------------------------

FT = {"E": 22400.0, "line0": 22370.0}                         # a FADE BUY, risk 30, VWAP above at 22450


def fade_bars():
    return ([one(m, 22420, 22395, 22410, vwap=22450) for m in range(601, 610)]
            + [one(610, 22452, 22420, 22448, vwap=22450)]                        # touches VWAP at 10:10
            + [one(m, 22470, 22445, 22460, vwap=22451) for m in range(611, 620)]
            + [one(620, 22465, 22439, 22445, vwap=22452)])                       # back through 22440


def test_a_fade_that_reaches_vwap_without_oi_and_flow_exits_at_vwap_as_v1():
    seen = []
    r = hold2.exit_v2(1, FT, 601, fade_bars(), [], {}, target=True,
                      convert=lambda k: (seen.append(k), {"ok": False, "line": 22440.0, "t": hold2.hm(k)})[1])
    assert seen == [612]                                       # the 10:10 bar's 3-min close: 10:12 on the 09:15 grid
    assert r["how"] == "vwap" and r["exit"] == 22450 and r["R"] == pytest.approx(50 / 30, abs=1e-4)


def test_a_fade_that_reaches_vwap_with_oi_and_flow_converts_and_rides_the_restarted_line():
    r = hold2.exit_v2(1, FT, 601, fade_bars(), [], {}, target=True,
                      convert=lambda k: {"ok": True, "line": 22440.0, "t": hold2.hm(k)})
    assert r["converted"]["ok"] is True and r["how"] == "line_conv" and r["exit"] == 22440.0
    assert r["R"] == pytest.approx(40 / 30, abs=1e-4)          # R stays on the FADE's initial risk
    # never worse than the line it had: a push already holding 22444 keeps it
    r = hold2.exit_v2(1, FT, 601, fade_bars(), [push(611, 1, 22447, 12, c=22447)], {}, target=True,
                      convert=lambda k: {"ok": True, "line": 22440.0, "t": hold2.hm(k)})
    assert r["line"] == 22444.0 and r["how"] == "line_push"


def test_fade_convert_needs_both_oi_and_flow_to_hold(monkeypatch):
    import ride
    for oi, fl, want in ((True, True, True), (True, False, False), (None, True, False)):
        monkeypatch.setattr(ride, "oi_read", lambda d, mi, pk, at, v=oi: {"ok": v})
        monkeypatch.setattr(ride, "flow_read", lambda d, bk, c, gc=None, v=fl: {"ok": v})
        r = hold2.fade_convert(1, 612, 22450.0, 20.0, ({}, {}), None)
        assert r["ok"] is want and r["line"] == 22440.0          # VWAP - 0.5 sigma for an UP fade
    assert hold2.fade_convert(-1, 612, 22450.0, 20.0, ({}, {}), None)["line"] == 22460.0


# ---- mirror and causality ----------------------------------------------------------------------------------------------

def test_up_mirrors_down():
    X = 45000.0
    mir = lambda p: X - p                                       # noqa: E731
    ones = flat(601, 605) + [one(605, 22470, 22395, 22400)] + [one(m, 22420, 22390, 22410) for m in range(606, 620)]
    ones += [one(620, 22430, 22400, 22420)]
    ps = [push(610, -1, 22425, 20)]
    down = hold2.exit_v2(-1, TR, 601, ones, ps, {})
    up = hold2.exit_v2(1, {"E": mir(TR["E"]), "line0": mir(TR["line0"])}, 601,
                       [one(b["s"] // 60, mir(b["l"]), mir(b["h"]), mir(b["c"])) for b in ones],
                       [dict(p, d=1, origin=mir(p["origin"]), c=mir(p["c"])) for p in ps], {})
    assert (up["how"], up["exit_t"], up["R"], up["lock_t"]) == (down["how"], down["exit_t"], down["R"], down["lock_t"])
    assert up["exit"] == pytest.approx(mir(down["exit"])) and len(up["moves"]) == len(down["moves"]) == 1


def test_no_look_ahead_inputs_cut_at_each_bar_give_identical_results():
    bars5 = [bar5(600 + 5 * i, 22500 - 6 * i, 22494 - 6 * i, -400 if i % 3 == 0 else -100) for i in range(12)]
    ones = [one(m, 22500 - (m - 601) * 1.2 + 4, 22500 - (m - 601) * 1.2 - 4, 22500 - (m - 601) * 1.2)
            for m in range(601, 655)] + [one(m, 22470, 22420, 22460) for m in range(655, 670)]
    closes = {k: {"c": 22450, "trend_state": fronts.BUILDING} for k in range(603, 670, 3)}
    tr = {"E": 22500.0, "line0": 22530.0}
    full_p = hold2.pushes(bars5, {"gc": F})
    full = hold2.exit_v2(-1, tr, 601, ones, full_p, closes)
    assert full["how"].startswith("line_") and full["moves"]
    t_ex = int(full["exit_t"][:2]) * 60 + int(full["exit_t"][3:])
    for M in range(602, 670):
        cut5 = [b for b in bars5 if b["s"] // 60 + 5 <= M]
        p = hold2.pushes(cut5, {"gc": F})
        assert p == [x for x in full_p if x["close"] <= M]        # a push is known only once its bar has closed
        r = hold2.exit_v2(-1, tr, 601, [b for b in ones if b["s"] // 60 < M], p,
                          {k: v for k, v in closes.items() if k <= M}, end=M)
        if M < t_ex:
            assert r["how"] == "open" and r["exit"] is None
            assert r["moves"] == [x for x in full["moves"] if int(x["at"][:2]) * 60 + int(x["at"][3:]) <= M]
        else:
            assert {k: r[k] for k in ("how", "exit", "exit_t", "R")} == {k: full[k] for k in ("how", "exit", "exit_t", "R")}


# ---- her hold window: display only -----------------------------------------------------------------------------------

def test_the_window_line_reads_spot_and_fut_why_points_and_the_front_and_stamps_gave_up():
    ones = flat(601, 625)
    ps = [push(615, -1, 22490, 20)]
    front = {"side": "CE", "k": 22500.0, "state": fronts.BUILDING, "price": None, "why": None}
    w = hold2.window_line(-1, 22475.0, 22515.0, 601, ones, ps, {}, 625, 22470.0, 25.0, front, entry_t="10:00")
    assert w["ok"] and w["line_fut"] == 22495.0 and w["line_spot"] == 22470.0 and w["pts"] == 25
    assert w["text"] == "HOLD v2 · line 22,470s|22,495f (PUSH ▼ 10:10) · 25 pts · CE front BUILDING"
    assert "her trade" in w["note"] and "inval 22,515f" in w["note"] and "display only" in w["note"]
    gave = {606: unw(22470, 22450, 22440)}
    w = hold2.window_line(-1, 22475.0, 22515.0, 601, ones, ps, gave, 625, 22470.0, 25.0, front)
    assert w["line_fut"] == 22495.0 and w["gave_up_t"] == "10:06" and w["text"].endswith("v2 out 10:06 (CE gave up)")
    assert "headline" not in w and "word" not in w                 # it never carries, so never changes, the word
    # AMENDMENT 1 on the face: unwinding read now, with price still neeche (CE writers winning) or upar (losing)
    mun = dict(front, k=23000.0, state=fronts.UNWINDING, price="munafa")
    w = hold2.window_line(-1, 22475.0, 22515.0, 601, ones, ps, {606: unw(22470, 22430, 22440)}, 625, 22470.0, 25.0, mun)
    assert "CE 23000 munafa booking (unwinding, price still neeche)" in w["text"] and w["gave_up_t"] is None
    w = hold2.window_line(-1, 22475.0, 22515.0, 601, ones, ps, {}, 625, 22470.0, 25.0, dict(mun, price="lose"))
    assert "CE 23000 gave up (unwinding, price upar)" in w["text"]
    w = hold2.window_line(-1, 22475.0, 22515.0, 601, ones, ps, {}, 625, 22470.0, 25.0, dict(mun, price="chop"))
    assert "CE 23000 munafa / chop (within 0.25U)" in w["text"]
    w = hold2.window_line(1, 22475.0, 22435.0, 601, ones, [], {}, 625, 22470.0, 25.0,
                          dict(mun, side="PE", k=22400.0, price="munafa"))
    assert "PE 22400 munafa booking (unwinding, price still upar)" in w["text"]


# ---- AMENDMENT 1's read off the chain: the front's peak minute and the spot then, cut causally -------------------------

def chain(spots, ce):
    """A minute grid from 09:16: spot and one CE strike's change since the open per mark (fronts.read's input)."""
    mins = {}
    for i, (sp, x) in enumerate(zip(spots, ce)):
        mins[hold2.hm(556 + i)] = {"spot": sp, "k": {23000.0: (x, 10.0 * i), 23050.0: (x / 10, 0.0)}}
    return mins, {}


def test_the_close_read_takes_the_peak_minute_and_its_spot_from_the_grid_cut_at_the_close():
    n = 75                                                      # 09:16 .. 10:30; the CE build peaks at 10:00
    ce = [1000.0 * i / 44 if i <= 44 else 1000.0 - 400.0 * (i - 44) / 30 for i in range(n)]
    falling = [23100.0 - 200.0 * i / n for i in range(n)]       # price kept falling: the CE writers are winning
    r = hold2.close_read(-1, chain(falling, ce), 621, 22950.0)   # the 10:21 close, read at 10:20
    assert r["trend_state"] == fronts.UNWINDING and r["peak_at"] == "10:00" and r["k"] == 23000.0
    assert r["spot"] == falling[64] and r["peak_spot"] == falling[44] and r["price"] == "munafa"
    back = falling[:45] + [falling[44] + 2.0 * (i - 44) for i in range(45, n)]       # price back 40 above the peak's
    assert hold2.close_read(-1, chain(back, ce), 621, 22950.0)["price"] == "lose"      # U = 0.1% floor: edge ~5.8
    assert hold2.close_read(-1, chain(back, ce), 621, 22950.0, sigma=200.0)["price"] == "chop"   # 0.25 x 200 = 50 > 40
    assert hold2.close_read(-1, chain(back, ce), 621, 22950.0, sigma=200.0)["U"] == 200.0
    # causal: the full day's grid and the grid cut at the close's last minute read the same
    mins, pk = chain(falling, ce)
    for k in range(573, 631, 3):
        cut = {t: v for t, v in mins.items() if t <= hold2.hm(k - 1)}
        assert hold2.close_read(-1, (mins, pk), k, 1.0) == hold2.close_read(-1, (cut, pk), k, 1.0)
    b3 = [{"e": k * 60, "c": 22950.0} for k in range(573, 631, 3)]
    full = hold2.closes(-1, 600, b3, (mins, pk))
    assert sorted(full) == list(range(603, 631, 3))
    assert all(full[k] == hold2.close_read(-1, ({t: v for t, v in mins.items() if t <= hold2.hm(k - 1)}, pk), k, 22950.0)
               for k in full)


# ---- tools/hold2_score.py --------------------------------------------------------------------------------------------

def _score():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import hold2_score
    return hold2_score


def test_sha_ok_refuses_a_changed_prereg(tmp_path):
    hs = _score()
    assert hs.sha_ok() is True
    p = tmp_path / "HOLD-V2-PREREG.md"
    with open(hs.PREREG, "rb") as f:
        p.write_bytes(f.read() + b" ")
    assert hs.sha_ok(str(p)) is False


def test_the_bar_paired_on_delta_r_with_drop_best_and_the_day_share():
    hs = _score()
    pairs = [{"day": f"2026-10-{22 + i // 4:02d}", "r1": 0.0, "r2": 0.3} for i in range(20)]
    v = hs.verdict(pairs)
    assert v["n"] == 20 and v["mean_dR"] == 0.3 and v["verdict"] == "PASS" and v["largest_day_share"] == 0.2
    assert hs.verdict(pairs[:19])["verdict"] == "INCONCLUSIVE"                     # n < 20
    assert hs.verdict([dict(p, r2=-0.1) for p in pairs])["verdict"] == "FAIL"
    one_day = [dict(p, day="2026-10-22") if i < 9 else p for i, p in enumerate(pairs)]
    assert hs.verdict(one_day)["verdict"] == "INCONCLUSIVE"                        # a day supplies 45%
    best = [dict(p, r2=0.0) for p in pairs[:19]] + [dict(pairs[19], r2=5.0)]
    assert hs.verdict(best)["mean_dR_ex_best"] == 0.0 and hs.verdict(best)["verdict"] == "INCONCLUSIVE"


def test_run_refuses_until_a_group_has_twenty_forward_entries_and_judges_each_group_once(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(os.getcwd())
    hs = _score()
    monkeypatch.setattr(hs, "OUT_JSON", str(tmp_path / "hold2_verdict.json"))
    old = [{"setup": "FADE", "day": "2026-10-21", "index": "SENSEX", "d": -1, "en": {"t": "09:42"}}] * 30
    new = [{"setup": "RIDE", "day": "2026-10-22", "index": "NIFTY", "d": -1, "en": {"t": "10:00"}}] * 19
    monkeypatch.setattr(hs, "forward_entries", lambda path=None: old + new)
    scored = []
    monkeypatch.setattr(hs, "score", lambda e, D: (scored.append(e), {"dR": 0.1, "v1": {"R": 0.0}, "v2": {"R": 0.1}})[1])
    assert hs.main(["--run"]) == 2 and scored == []            # 21 Oct is in-sample; RIDE has 19
    assert "REFUSED" in capsys.readouterr().out
    monkeypatch.setattr(hs, "forward_entries", lambda path=None: old + new * 2)
    assert hs.main(["--run"]) == 0 and len(scored) == 38       # RIDE judged on its 38 forward rows only
    assert hs.main(["--run"]) == 2                              # judged once: refused, nothing re-scored
    assert len(scored) == 38


def test_describe_labels_every_row_in_sample_and_prints_no_rate(monkeypatch):
    hs = _score()
    e = {"setup": "RIDE", "day": "2026-10-12", "index": "BANKNIFTY", "d": -1, "trig": "10:12",
         "en": {"E": 55250.6, "t": "10:21"}, "src": "§1k look"}
    monkeypatch.setattr(hs, "score", lambda e, D: {"v1": {"how": "line", "exit_t": "10:38", "R": 1.16},
                                                     "v2": {"how": "line_push", "exit_t": "13:00", "R": 3.08,
                                                            "n_moves": 1, "moves": [], "mfe": 311.0, "mae": 2.4},
                                                     "dR": 1.92, "refs": {"ux": 12}, "why": None})
    lines = []
    hs.describe([e], None, out=lines.append)
    txt = "\n".join(lines)
    assert "IN-SAMPLE" in txt and "NEVER counted" in txt and "line_push" in txt and "+1.92" in txt
    rows = " ".join(lines[next(i for i, x in enumerate(lines) if x.strip().startswith("entry")):])
    assert "%" not in rows and "win" not in rows.lower()        # rows only: no rate, no share, no count of winners


def _ms(m):
    return (m * 60 - 19800) * 1000 + 86400000 * 20000         # any day: IST minute m


def test_live_starts_at_her_thesis_inval_runs_from_her_entry_and_never_writes_the_view():
    import copy
    view = {"headline": "HOLD · sellers in control", "d": -1, "E": 22475.0, "G": {"px": 22530}, "fut": 22470.0,
            "units": {"basis_ix": 25.0}}
    keep = copy.deepcopy(view)
    tr = {"id": "x", "idx": "SENSEX", "t0": "10:00:30", "thesis": {"inval": 22515.0}}
    bars1 = [{"t": _ms(m), "o": 22470, "h": 22480, "l": 22460, "c": 22470} for m in range(595, 625)]
    w = hold2.live(tr, view, 625, bars1, [], [], {}, "push ? ref nahi — SENSEX", {})
    assert view == keep and w["ok"] and w["line_fut"] == 22515.0 and w["line_spot"] == 22490.0
    assert w["text"].startswith("HOLD v2 · line 22,490s|22,515f (initial) · 45 pts · CE front ?") and "ref nahi" in w["text"]
    assert "from her entry 10:00" in w["note"]
    w = hold2.live(dict(tr, thesis={}), view, 625, bars1, [], [], {}, None, {})
    assert w["line_fut"] == 22530                               # no thesis inval: the engine's give-up G
    assert hold2.live(tr, dict(view, E=None), 625, bars1, [], [], {}, None, {})["ok"] is False


def test_the_server_block_is_fail_soft_and_leaves_the_reply_word_alone(monkeypatch):
    import copy
    import server
    monkeypatch.setattr(server.fold_live, "hold2_rows", lambda idx: None)
    tr = {"id": "NIFTY-23000PE-long-100730", "idx": "NIFTY", "t0": "10:07:30", "k": 23000, "side": "PE", "role": "long"}
    rep = {"ok": True, "id": tr["id"], "view": {"headline": "HOLD", "d": -1, "E": 23003.2}}
    keep = copy.deepcopy(rep)
    server._hold2_run(tr, rep["view"], 600)
    assert server._HOLD2["out"][tr["id"]][1]["why"].startswith("could not check — the fold engine")
    assert server._hold2(rep, [dict(tr, exit_t="13:05:04")]) is None          # out of the trade: no block
    assert rep == keep
    server._HOLD2["out"].pop(tr["id"], None)


def test_the_fade_decision_is_taken_at_its_close_never_before_it():
    calls = []

    def conv(ok):
        return lambda k: (calls.append(k), {"ok": ok, "line": 22440.0, "t": hold2.hm(k)})[1]
    full = hold2.exit_v2(1, FT, 601, fade_bars(), [], {}, target=True, convert=conv(True))
    for M in range(602, 621):
        calls.clear()
        r = hold2.exit_v2(1, FT, 601, [b for b in fade_bars() if b["s"] // 60 < M], [], {}, target=True,
                          convert=conv(True), end=M)
        assert all(k <= M for k in calls)                      # convert(k) runs only once minute k has closed
        assert r["how"] == ("open" if M <= 620 else full["how"])
    # a line touch while the decision waits: it is the exit only if the close converts; otherwise v1's VWAP exit
    bars = [one(m, 22420, 22395, 22410, vwap=22450) for m in range(601, 610)] + [one(610, 22452, 22360, 22400, vwap=22450)]
    assert hold2.exit_v2(1, FT, 601, bars, [], {}, target=True, convert=conv(False))["how"] == "line_init"   # one bar: line first
    bars = [one(m, 22420, 22395, 22410, vwap=22450) for m in range(601, 610)] + [one(610, 22452, 22420, 22448, vwap=22450),
                                                                                  one(611, 22430, 22360, 22380, vwap=22450)]
    r = hold2.exit_v2(1, FT, 601, bars, [], {}, target=True, convert=conv(True))
    assert r["how"] == "line_init" and r["exit"] == 22370.0 and r["exit_t"] == "10:12"
    assert hold2.exit_v2(1, FT, 601, bars, [], {}, target=True, convert=conv(False))["how"] == "vwap"


def test_api_fold_carries_the_block_beside_the_reply_and_never_touches_the_word(monkeypatch):
    import server
    from test_frame_api import _Cap
    tr = {"id": "NIFTY-23000PE-long-100730", "idx": "NIFTY", "t0": "10:07:30", "k": 23000, "side": "PE", "role": "long"}
    cached = {"ok": True, "id": tr["id"], "view": {"headline": "HOLD", "clause": "sellers in control", "d": -1}}
    monkeypatch.setattr(server, "_hold_trades", lambda: [tr])
    monkeypatch.setattr(server.fold_live, "reply", lambda path, q, trades: cached)
    monkeypatch.setattr(server, "_feed_read", lambda idx, day: {"idx": idx})
    monkeypatch.setattr(server, "_hold2", lambda rep, trades: {"ok": True, "text": "HOLD v2 · line 22,755s|22,780f"})
    g = _Cap(f"/api/fold?id={tr['id']}")
    server.Handler.do_GET(g)
    assert g.sent["hold2"]["text"].startswith("HOLD v2") and g.sent["view"] == cached["view"]
    assert "hold2" not in cached                                    # the engine's cached reply is never written
    monkeypatch.setattr(server, "_hold2", lambda rep, trades: 1 / 0)
    g = _Cap(f"/api/fold?id={tr['id']}")
    server.Handler.do_GET(g)
    assert g.sent["ok"] is True and g.sent["hold2"]["why"].startswith("could not check — HOLD v2 failed")
