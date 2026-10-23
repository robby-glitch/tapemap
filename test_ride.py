"""ride.py: one synthetic test per RIDE-PREREG.md rule, the no-look-ahead proof, the trail that only moves toward
price, STALLED holds / UNWINDING exits. Nothing here reads data/ (only synthetic inputs exercise outcome / expressions)."""
import fronts
import ride


def front(side, state, k=22500.0):
    return {"side": side, "k": k, "state": state, "peak_at": "10:00"}


def test_oi_ok_down_needs_ce_building_and_pe_not_building(monkeypatch):
    monkeypatch.setattr(fronts, "stale", lambda cut, at: None)
    monkeypatch.setattr(fronts, "cut", lambda m, at: m)
    cases = [((fronts.BUILDING, fronts.STALLED), True), ((fronts.BUILDING, fronts.UNWINDING), True),
             ((fronts.BUILDING, fronts.BUILDING), False), ((fronts.STALLED, fronts.UNWINDING), False)]
    for (ce, pe), want in cases:
        monkeypatch.setattr(fronts, "read", lambda cut, peaks, ce=ce, pe=pe: [front("CE", ce), front("PE", pe)])
        assert ride.oi_read(-1, {"10:00": {}}, {}, "10:00")["ok"] is want
    # up is the mirror: PE building, CE not building
    monkeypatch.setattr(fronts, "read", lambda cut, peaks: [front("CE", fronts.STALLED), front("PE", fronts.BUILDING)])
    assert ride.oi_read(+1, {"10:00": {}}, {}, "10:00")["ok"] is True


def test_oi_stale_grid_is_could_not_check(monkeypatch):
    monkeypatch.setattr(fronts, "cut", lambda m, at: m)
    monkeypatch.setattr(fronts, "stale", lambda cut, at: "grid 5 min stale")
    r = ride.oi_read(-1, {}, {}, "10:00")
    assert r["ok"] is None and r["why"] == "grid 5 min stale"


def book(mins):
    """mins: {minute: (buy, sell)} -> confluence's (flow, seen, bad)."""
    return ({m: list(v) for m, v in mins.items()}, set(mins), set())


def test_flow_down_needs_sellers_back_and_no_strong_counter_buying():
    close = 600                                                        # 10:00
    prev = {m: (55, 45) for m in range(close - 20, close - 5)}        # +0.10 counter tilt: allowed (<= +0.10)
    last = {m: (40, 60) for m in range(close - 5, close)}             # -0.20: sellers back
    assert ride.flow_read(-1, book({**prev, **last}), close)["ok"] is True
    strong = {m: (60, 40) for m in range(close - 20, close - 5)}      # +0.20 counter buying: not a weak pullback
    assert ride.flow_read(-1, book({**strong, **last}), close)["ok"] is False


def test_flow_nifty_gc_disagreement_and_absent_gc():
    close = 600
    b = book({**{m: (50, 50) for m in range(close - 20, close - 5)}, **{m: (40, 60) for m in range(close - 5, close)}})
    gc_up = [{"t": (close - 5) * 60000 - ride.IST_MS, "buy": 60, "sell": 40}]          # +0.20 on the same 5 min
    assert ride.flow_read(-1, b, close, gc_up)["why"] == "sources disagree"
    assert ride.flow_read(-1, b, close, [])["ok"] is True                              # absent GC is not disagreement


def bar(s, h, l, c, vw, sg):
    return {"s": s, "e": s + 180, "o": c, "h": h, "l": l, "c": c, "v": 10, "delta": -5, "vwap": vw, "sig": sg}


def test_trade_line_is_higher_of_trigger_high_and_vwap_plus_quarter_sigma_with_half_sigma_floor():
    trig = bar(36000, 22510, 22480, 22490, 22500, 20)
    tr = ride.trade(-1, trig, bar(36180, 22495, 22470, 22475, 22500, 20))
    assert tr["line0"] == 22510 + 5 and tr["E"] == 22475
    tight = ride.trade(-1, bar(36000, 22471, 22468, 22469, 22470, 20), bar(36180, 22472, 22468, 22470, 22470, 20))
    assert tight["line0"] == 22470 + 10                                # 22471+5 < E+0.5σ: the floor wins


# ---- the hold and the exit (§2): no candle close, no fixed target ----------------------------------------------------

def one(m, h, l, c):
    return {"s": m * 60, "e": m * 60 + 60, "h": h, "l": l, "c": c}


TR = {"E": 22475.0, "sigma": 20.0, "line0": 22515.0}


def test_line_exit_is_intrabar_never_a_close():
    ones = [one(601, 22480, 22470, 22472), one(602, 22516, 22470, 22471)]    # high pokes the line, closes back below
    r = ride.outcome(-1, TR, 601, ones, {})
    assert r["how"] == "line" and r["exit"] == 22515.0 and r["R"] == -1.0


def test_trail_moves_only_toward_price():
    closes = {603: {"c": 22440, "flip_fut": 22480, "trend_state": fronts.BUILDING},   # line -> 22485
              606: {"c": 22430, "flip_fut": 22500, "trend_state": fronts.BUILDING}}   # farther: ignored
    ones = [one(m, 22450, 22420, 22440) for m in range(601, 607)] + [one(607, 22486, 22430, 22480)]
    r = ride.outcome(-1, TR, 601, ones, closes)
    assert r["how"] == "line" and r["exit"] == 22485.0
    assert round(r["R"], 4) == round((22475 - 22485) / 40, 4)              # initial risk throughout


def test_stalled_holds_and_unwinding_exits_at_that_close():
    closes = {603: {"c": 22440, "flip_fut": None, "trend_state": fronts.STALLED},
              606: {"c": 22420, "flip_fut": None, "trend_state": fronts.UNWINDING}}
    ones = [one(m, 22450, 22410, 22440 if m < 605 else 22420) for m in range(601, 610)]
    r = ride.outcome(-1, TR, 601, ones, closes)
    assert r["how"] == "gave_up" and r["exit"] == 22420 and r["exit_t"] == "10:06"
    assert r["stalled"] == ["10:03"]
    # a 1-min hole on the 3-min close's minute does not skip "somebody gave up": it is read at the next bar's open
    holed = [b for b in ones if b["s"] // 60 != 605]
    assert ride.outcome(-1, TR, 601, holed, closes)["exit_t"] == "10:06"


def test_marked_at_1520_when_nothing_fires():
    ones = [one(m, 22450, 22440, 22445) for m in range(601, 925)]
    r = ride.outcome(-1, TR, 601, ones, {})
    # the 15:19 bar's close, i.e. the 15:20 price; named 15:20 because every RIDE time is a bar END (the plan's draft
    # said "15:19", the bar's label, while naming the line / gave-up exits by their END -- one convention here)
    assert r["how"] == "mark" and r["exit_t"] == "15:20" and r["exit"] == 22445


def test_no_look_ahead_entry_is_identical_when_inputs_are_cut_at_the_bar(monkeypatch):
    """evaluate() at a §E entry gives the same answer whether book/chain/bars hold the whole day or only data to the
    window's last close."""
    import random
    random.seed(7)
    close0 = 603                                       # the §E bar (b3[1], 10:00-10:03) closes at minute 603
    full = {m: (random.randint(30, 70), random.randint(30, 70)) for m in range(560, 700)}
    cut = {m: v for m, v in full.items() if m < close0 + 9}            # the window's last close is 612
    monkeypatch.setattr(fronts, "cut", lambda m, at: {k: v for k, v in m.items() if k <= at})
    monkeypatch.setattr(fronts, "stale", lambda c, at: None)
    monkeypatch.setattr(fronts, "read", lambda c, p: [front("CE", fronts.BUILDING if len(c) % 2 else fronts.STALLED),
                                                      front("PE", fronts.STALLED)])
    grid = {hm: {} for hm in (f"{h:02d}:{m:02d}" for h in range(9, 12) for m in range(60))}
    b3 = [bar(36000 - 180 + 180 * j, 22510, 22470, 22480, 22500, 20) for j in range(6)]
    ent = {"i": 1, "d": -1}
    a = ride.evaluate(ent, b3, (grid, {}), book(full))
    b = ride.evaluate(ent, b3[:5], ({k: v for k, v in grid.items() if k <= "10:11"}, {}), book(cut))  # last OI read 10:11
    assert a == b and len(a["bars"]) == 4


def test_no_look_ahead_on_varied_bars_each_window_bar_reads_only_up_to_its_own_close(monkeypatch):
    """Every bar of the window, read with the inputs cut at THAT bar's close (bars, book, chain), must equal the full
    read: with bars that differ, a peek at the next bar (or a later minute) shows up."""
    import random
    random.seed(11)
    monkeypatch.setattr(fronts, "cut", lambda m, at: {k: v for k, v in m.items() if k <= at})
    monkeypatch.setattr(fronts, "stale", lambda c, at: None)
    monkeypatch.setattr(fronts, "read", lambda c, p: [front("CE", fronts.BUILDING if len(c) % 3 else fronts.STALLED),
                                                      front("PE", fronts.UNWINDING if len(c) % 2 else fronts.BUILDING)])
    full = {m: (random.randint(20, 80), random.randint(20, 80)) for m in range(560, 700)}
    grid = {f"{h:02d}:{m:02d}": {} for h in range(9, 12) for m in range(60)}
    b3 = [bar(35820 + 180 * j, 22510 - 3 * j, 22470 - 5 * j, 22480 - 4 * j + 9 * (j % 2), 22500 - 2 * j, 20 + j)
          for j in range(7)]
    ent = {"i": 1, "d": -1}
    a = ride.evaluate(ent, b3, (grid, {}), book(full))
    for T in range(4):
        close = b3[1 + T]["e"] // 60
        cut = ride.evaluate(ent, b3[:2 + T], ({k: v for k, v in grid.items() if k <= ride.hm(close - 1)}, {}),
                            book({m: v for m, v in full.items() if m < close}))
        assert cut["bars"] == a["bars"][:T + 1]
        if a["entry"] is not None and a["entry"]["bar"] <= T:
            assert cut["entry"] == a["entry"]
    assert len({b["loc"]["c"] for b in a["bars"]}) == 4                  # the bars really differ


def test_up_ride_mirrors_the_line_and_the_exits():
    up = ride.trade(+1, bar(36000, 22530, 22490, 22520, 22500, 20), bar(36180, 22540, 22515, 22525, 22500, 20))
    assert up["line0"] == 22490 - 5 and up["E"] == 22525                  # below the lower of trigger low and VWAP
    ones = [one(601, 22530, 22500, 22528), one(602, 22540, 22484, 22520)]   # the low pokes the line, closes back up
    r = ride.outcome(+1, up, 601, ones, {})
    assert r["how"] == "line" and r["exit"] == 22485 and r["R"] == -1.0
    closes = {603: {"c": 22560, "flip_fut": 22540, "trend_state": fronts.BUILDING},   # line -> 22535, toward price
              606: {"c": 22570, "flip_fut": None, "trend_state": fronts.UNWINDING}}   # the PE writers gave up
    ones = [one(m, 22580, 22540, 22560 if m < 605 else 22570) for m in range(601, 610)]
    r = ride.outcome(+1, up, 601, ones, closes)
    assert r["how"] == "gave_up" and r["exit"] == 22570 and r["R"] == round((22570 - 22525) / 40, 4)


def test_the_trail_never_moves_the_line_past_price():
    closes = {603: {"c": 22470, "flip_fut": 22460, "trend_state": fronts.BUILDING}}   # FLIP+0.25σ = 22465 < close
    ones = [one(601, 22480, 22460, 22472), one(602, 22480, 22465, 22470), one(603, 22490, 22466, 22488)]
    r = ride.outcome(-1, TR, 601, ones, closes)
    assert r["how"] == "mark"                                             # 22465 below price: no line there, no exit


def test_expressions_buy_atm_buy_itm_and_sell_the_opposite_atm_with_equal_weight():
    minutes = {"10:02": {"spot": 22490.0, "px": {22450: (60, 20), 22500: (30, 40), 22550: (10, 70)}},
               "10:14": {"spot": 22440.0, "px": {22450: (20, 50), 22500: (8, 80), 22550: (2, 120)}}}
    dn = ride.expressions(-1, minutes, "10:03", "10:15")                 # END times: read at 10:02 / 10:14
    assert (dn["k"], dn["itm_k"], dn["buy"], dn["sell"]) == (22500, 22550, "PE", "CE")
    assert [dn[x]["pts"] for x in ("buy_atm", "buy_itm", "sell_atm")] == [40, 50, 22]
    up = ride.expressions(+1, minutes, "10:03", "10:15")                 # the same fall against a ▲ ride
    assert (up["itm_k"], up["buy"], up["sell"]) == (22450, "CE", "PE")
    assert [up[x]["pts"] for x in ("buy_atm", "buy_itm", "sell_atm")] == [-22, -40, -40]
    assert ride.expressions(-1, {"10:02": dict(minutes["10:02"], src="backfill")}, "10:03", "10:15") is None


def test_entries_calls_plan_causally_once_per_closed_bar(monkeypatch):
    import frame_v2
    b3 = [bar(36000 + 180 * j, 22510, 22470, 22480, 22500, 20) for j in range(5)]
    rows = [{"t": frame_v2.hm(36000 + 300 * j), "word": "TREND", "dir": -1} for j in range(6)]
    seen = []

    def plan(bk, rk, basis, now):
        assert now == bk[-1]["e"] and all(frame_v2._sec(r["t"]) <= now for r in rk)    # nothing after the close
        assert basis == {"as_of": now}                    # the basis the frame had at this close, never a later one
        seen.append(len(bk))
        third = frame_v2.hm(b3[2]["e"])
        return ({"d": -1, "word": "TREND", "rows": [{"t": third, "what": "ENTRY", "px": 22480}]} if len(bk) >= 3
                else {"d": -1, "rows": []}), None
    monkeypatch.setattr(frame_v2, "plan", plan)
    got = ride.entries(b3, rows, lambda e: {"as_of": e})
    assert seen == [1, 2, 3, 4, 5] and got == [{"i": 2, "t": "10:09", "d": -1, "word": "TREND", "px": 22480}]


def test_trail_reads_only_a_flip_of_the_rides_own_direction(monkeypatch):
    monkeypatch.setattr(fronts, "stale", lambda c, at: None)
    monkeypatch.setattr(fronts, "read", lambda c, p: [front("CE", fronts.BUILDING)])
    b3 = [bar(36000 + 180 * j, 22510, 22470, 22480, 22500, 20) for j in range(4)]
    rows = [{"t": "10:00", "word": "TREND", "dir": -1, "flip": 22550, "basis": 40},
            {"t": "10:10", "word": "TREND", "dir": 1, "flip": 22450, "basis": 40}]   # the READ turned ▲ at 10:10
    cl = ride.closes_after(-1, 603, b3, rows, ({"10:04": {}}, {}))
    assert sorted(cl) == [606, 609, 612]                                  # closes after entry only
    assert cl[606] == {"c": 22480, "flip_fut": 22590, "trend_state": fronts.BUILDING}
    assert cl[609]["flip_fut"] == 22590 and cl[612]["flip_fut"] is None  # a ▲ FLIP is no line for a ▼ ride


def test_stamps_leg_age_pullback_depth_flip_distance_and_gate():
    """A realistic ▼ leg: 22,605 top, down to 22,500, an earlier deeper bounce to 22,580, then the §E bar pokes 22,560.
    THIS pullback is the §E bar's own high against the leg's top and its low before the bar: 57.1%, inside 0..100."""
    legs = [bar(36000, 22605, 22580, 22585, 22650, 20), bar(36180, 22585, 22500, 22510, 22640, 20),
            bar(36360, 22580, 22505, 22530, 22630, 20), bar(36540, 22560, 22520, 22525, 22620, 20)]
    legs[0]["o"] = 22600
    rows = [{"t": "10:00", "word": "TREND", "dir": -1, "since": "10:00", "flip": 22600, "basis": 40}]
    s = ride.stamps({"i": 3, "t": "10:12", "d": -1, "word": "TREND"}, legs, rows, None, peers={"SENSEX": "TREND ▼"}, dte=3)
    assert (s["leg_age_min"], s["pullback_depth_pct"], s["dte"]) == (12, 57.1, 3)
    assert s["pullback"] == {"start": 22605, "ext": 22500, "pull": 22560} and 0 < s["pullback_depth_pct"] < 100
    assert s["flip_dist"] == 22640 - 22525                                # no RIDE entry: FLIP and price at the §E bar
    assert s["gate"] is None and s["gate_why"] == "no §1d gate is logged for §E entries"
    # ▲ is the mirror: a leg up 22,395 -> 22,500, the §E bar's low pokes back to 22,440: 57.1%
    up = [bar(36000, 22420, 22395, 22410, 22350, 20), bar(36180, 22500, 22410, 22495, 22360, 20),
          bar(36360, 22490, 22440, 22470, 22370, 20)]
    s = ride.stamps({"i": 2, "t": "10:09", "d": 1, "word": "TREND"}, up, [dict(rows[0], dir=1)], None)
    assert s["pullback"] == {"start": 22395, "ext": 22500, "pull": 22440} and s["pullback_depth_pct"] == 57.1


def test_flip_distance_reads_the_flip_at_the_ride_entry_bar():
    legs = [bar(36000 + 180 * j, 22560, 22500, 22520, 22600, 20) for j in range(4)]
    rows = [{"t": "10:00", "word": "TREND", "dir": -1, "since": "10:00", "flip": 22600, "basis": 40},
            {"t": "10:10", "word": "TREND", "dir": -1, "since": "10:00", "flip": 22580, "basis": 40}]   # FLIP trailed
    s = ride.stamps({"i": 0, "t": "10:03", "d": -1}, legs, rows, {"E": 22510.0, "t": "10:12"})
    assert s["flip_dist"] == 22580 + 40 - 22510                          # the 10:10 FLIP, the entry bar's own


# ---- tools/ride_score.py: the §6 gate (dry counts only until a cell can reach n >= 20) ---------------------------------

def _score():
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import ride_score
    return ride_score


def test_sha_ok_refuses_a_changed_prereg(tmp_path):
    rs = _score()
    assert rs.sha_ok() is True                                          # the signed text, untouched
    p = tmp_path / "RIDE-PREREG.md"
    with open(rs.PREREG, "rb") as f:
        p.write_bytes(f.read() + b" ")
    assert rs.sha_ok(str(p)) is False


def test_run_refuses_until_some_cell_can_reach_twenty():
    rs = _score()
    cell = rs.CELLS[0]
    assert rs.can_run({cell: 2}, {}) is False and rs.can_run({}, {}) is False
    assert rs.can_run({cell: 12}, {rs.CELLS[1]: 8}) is False            # cells are never pooled
    assert rs.can_run({cell: 12}, {cell: 8}) is True                    # dry + forward in one cell


def test_run_is_refused_by_main_while_the_gate_is_shut(tmp_path, monkeypatch, capsys):
    import os
    monkeypatch.chdir(os.getcwd())                                      # main() chdirs; give the cwd back after
    rs = _score()
    monkeypatch.setattr(rs, "OUT_JSON", str(tmp_path / "ride_first_look.json"))   # never the real one-shot's file
    called = []
    monkeypatch.setattr(rs, "collect", lambda recs, run=False: (called.append(run), [])[1])
    monkeypatch.setattr(rs, "days", lambda: [])
    monkeypatch.setattr(rs, "forward", lambda scanned, path=None: {})
    assert rs.main(["--run"]) == 2 and called == [False]               # counted dry, never scored
    assert "REFUSED" in capsys.readouterr().out


def test_dry_counts_keep_late_triggers_in_their_own_column():
    rs = _score()
    ok = {"ok": True}
    late = {"cell": rs.CELLS[0], "late": True, "row": {"entry": None, "bars": [
        {"late": True, "loc": ok, "oi": {"ok": None}, "flow": {"ok": None}}]}}
    real = {"cell": rs.CELLS[0], "late": False, "row": {"entry": None, "bars": [
        {"late": False, "loc": ok, "oi": {"ok": None}, "flow": {"ok": False}}]}}
    t = rs.counts([late, real])[rs.CELLS[0]]
    assert (t["e"], t["late"], t["oi_cnc"], t["flow_cnc"], t["flow_ok"], t["loc_ok"]) == (2, 1, 1, 0, 0, 1)


# ---- §1k: the one look's descriptive extras (in no rule, no bar) ------------------------------------------------------

def test_excursion_mfe_mae_and_the_moves_30_and_60_minutes_on():
    ones = [one(m, 22480, 22470, 22475) for m in range(590, 601)]                      # before entry: 22470..22480
    ones += [one(601, 22478, 22460, 22465), one(602, 22490, 22455, 22458), one(603, 22470, 22440, 22450)]
    ones += [one(m, 22460, 22430, 22445 - (m - 604)) for m in range(604, 670)]
    x = ride.excursion(-1, 22475.0, 601, 603, ones)                                  # exit at 10:03: bars 601, 602
    assert (x["mfe"], x["mae"]) == (20.0, 15.0)                                      # 22475-22455 / 22490-22475
    assert x["move30"] == 22475 - (22445 - (630 - 604)) and x["move60"] == 22475 - (22445 - (660 - 604))
    assert x["range"] == [22470, 22480] and x["close_at_entry"] == 22475
    assert ride.excursion(+1, 22475.0, 601, 603, ones)["mfe"] == 15.0               # ▲ mirrored
    assert ride.excursion(-1, 22475.0, 900, 920, ones)["move30"] is None              # no bar then: never a zero


def test_look_amendment_2_scores_once_marks_1k_and_refuses_a_second_time(tmp_path, monkeypatch, capsys):
    import json
    import os
    monkeypatch.chdir(os.getcwd())
    rs = _score()
    out = tmp_path / "ride_first_look.json"
    monkeypatch.setattr(rs, "OUT_JSON", str(out))
    runs = []
    monkeypatch.setattr(rs, "days", lambda: [])
    monkeypatch.setattr(rs, "forward", lambda scanned, path=None: {})
    monkeypatch.setattr(rs, "collect", lambda recs, run=False: (runs.append(run), [])[1])
    assert rs.main(["--look-amendment-2"]) == 0 and runs == [False, True]     # the gate is shut; §1k scores anyway
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["amendment"].startswith("§1k") and res["readings"] == rs.READINGS and res["sha256"] == rs.SHA
    assert rs.main(["--look-amendment-2"]) == 2 and runs == [False, True]     # once: refused, nothing scored
    assert rs.main(["--run"]) == 2                                            # and the one-shot has been spent
    assert "REFUSED" in capsys.readouterr().out


def test_dry_header_prints_the_readings(capsys):
    rs = _score()
    rs.print_dry([], [], {})
    o = capsys.readouterr().out
    assert "READINGS" in o and all(f"{k}. " in o for k in range(1, len(rs.READINGS) + 1))


def test_look_report_sanity_flags_catch_what_a_trader_would():
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import look_report as lr
    clean = {"index": "NIFTY", "d": -1, "time": "10:03", "E": 25000.0, "spot": 24950.0, "exit": 24960.0,
             "exit_time": "10:30", "how": "line", "R": 1.0, "risk0": 40.0, "mfe": 55.0, "mae": 10.0,
             "range": [24990.0, 25080.0], "close_at_entry": 25000.0,
             "opts": {"k": 24950, "buy": "PE", "atm_in": [120.0, 95.0], "atm_out": [80.0, 130.0], "itm_in": 140.0},
             "move30": 30.0, "move60": 45.0}
    assert lr.flags(clean) == []
    bad = dict(clean, R=0.5, exit_time="10:03", E=25100.0, spot=24000.0,
               opts={"k": 24800, "buy": "PE", "atm_in": [1500.0, 95.0], "atm_out": [None, 130.0], "itm_in": 90.0})
    got = " | ".join(lr.flags(bad))
    for word in ("R ", "exit not after entry", "outside the session range", "1-min close", "basis",
                 "strike", "premium", "exit premium", "ITM"):
        assert word in got, word

    # 28 Sep SENSEX's shape: the options price the underlying ~180 above the strike chosen by the chain's spot
    fwd = dict(clean, index="SENSEX", E=73589.6, spot=72909.9, exit=73446.0, R=1.0, risk0=143.6, mfe=240.0, mae=74.0,
               range=[73400.0, 73700.0], close_at_entry=73589.6,
               opts={"k": 72900, "buy": "PE", "atm_in": [371.0, 553.0], "atm_out": [401.5, 444.1], "itm_in": 415.05})
    assert any("forward" in f for f in lr.flags(fwd))
    odd = dict(clean, mfe=-17.8, exit=25040.0, R=-1.0, mae=45.0, move60=None)
    got = " | ".join(lr.flags(odd))
    assert "never traded back to E" in got and "+60m" in got
