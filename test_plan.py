"""plan.py against its registration (docs/hold/PLAN-PREREG.md rev 2a, §1f), on synthetic
minutes whose answer is known by hand. In-sample by construction: these pin the CODE to
the TEXT, never the market."""
import hold
import plan


def rec(t, close, lo, hi, fr=(), folds=(), blind=None):
    return {"t": t, "spot": close, "ix": [close, hi, lo], "fr": [dict(f) for f in fr],
            "folds": list(folds), "blind": blind}


def F(k, side, state, built=True):
    return {"k": k, "side": side, "state": state, "built": built}


def row(t, L, room, c=None, verdict="HOLD"):
    return {"t": t, "verdict": verdict, "since": t, "fold_rule": None,
            "line": {"L": L, "room": room, "blind": None}, "prem": {"c": c}}


def day(n=375, close=100.0):
    """A whole session of flat synthetic minutes, 09:15 onward, session-aligned."""
    return [rec(hold.SESSION[i], close, close - 1, close + 1) for i in range(n)]


def test_the_rung_is_the_nearest_sized_payers_wall_beyond_the_index():
    m = rec("12:31", 74013.5, 74010, 74030, fr=[F(74000, "PE", "UNWINDING"), F(73900, "PE", "BUILDING"),
                                               F(74100, "PE", "BUILDING"), F(73800, "PE", "BUILDING", built=False),
                                               F(73900, "CE", "BUILDING")])
    r = plan.rung(m, -1, 74013.5, 74010.0)
    assert (r["src"], r["k"], r["room"], r["word"], r["state"]) == ("wall", 74000, 14, "GIVING WAY", "UNWINDING")
    assert r["favour"] == plan.WORDS["GIVING WAY"] and r["tag"] == "M"
    up = plan.rung(m, 1, 74013.5, 74030.5)              # a long CE's wall is a CE above: none here
    assert up["src"] == "session" and up["k"] == 74030.5 and up["room"] == 17


def test_no_wall_falls_back_to_the_session_extreme_then_to_price_discovery():
    m = rec("13:57", 73659.3, 73640, 73670)
    s = plan.rung(m, -1, 73659.3, 73633.7)
    assert s["src"] == "session" and s["room"] == 26 and s["label"] == "session low — no sized wall inside the nine"
    n = plan.rung(m, -1, 73659.3, 73659.3)
    assert n["src"] == "none" and n["label"] == "no wall in the way — price discovery" and n["room"] is None
    b = plan.rung({**m, "blind": "could not check — fronts forming: 9 of 15"}, -1, 73659.3, 73633.7)
    assert b["src"] == "session" and b["label"].startswith("session low — the walls could not be read")


def test_the_three_words_and_a_live_fold():
    assert plan.word("BUILDING") == "DEFENDED" and plan.word("STALLED") == "STALLED"
    assert plan.word("UNWINDING") == "GIVING WAY" and plan.word("STALLED", "12:27") == "GIVING WAY"
    m = rec("12:31", 74013.5, 74010, 74030, fr=[F(74000, "PE", "STALLED")],
            folds=[{"k": 74000, "side": "PE", "t": "12:27", "still": True}])
    r = plan.rung(m, -1, 74013.5, 74010.0)
    assert r["word"] == "GIVING WAY" and r["fold_t"] == "12:27"
    stale = {**m, "folds": [{"k": 74000, "side": "PE", "t": "12:10", "still": True}]}   # 21 min old: not live
    assert plan.rung(stale, -1, 74013.5, 74010.0)["word"] == "STALLED"


def test_the_premium_at_risk_by_role():
    # a buyer: |Δ|·R − ½Γ·R², clamped 0…premium; a PE's negative delta is read as |Δ|
    assert plan.risk(100, (-0.5, 0.002), "long", 200.0, 20) == (800.0, None)       # (50 − 10) × 20
    assert plan.risk(100, (-0.5, 0.002), "long", 30.0, 20) == (600.0, None)        # capped at the premium
    assert plan.risk(600, (0.3, 0.002), "long", 500.0, 1) == (0.0, None)           # never below 0
    assert plan.risk(100, (0.5, 0.002), "short", 200.0, 20) == (1200.0, None)      # (50 + 10) × 20
    assert plan.risk(100, None, "long", 200.0, 20) == (None, plan.CC + "no greeks for this strike in the chain record")
    assert plan.risk(None, (0.5, 0.002), "long", 200.0, 20) == (None, plan.CC + "the line is blind this minute")


def test_one_touch_per_strike_a_retest_is_not_a_touch_a_new_strike_is():
    mins = day()
    i0 = hold.SESSION.index("12:30")
    mins[i0] = rec("12:30", 74020, 74015, 74030, fr=[F(74000, "PE", "BUILDING")])
    mins[i0 + 1] = rec("12:31", 74005, 73995, 74020, fr=[F(74000, "PE", "BUILDING")])          # touch 74,000
    mins[i0 + 2] = rec("12:32", 74008, 73990, 74015, fr=[F(74000, "PE", "BUILDING")])          # retest: no
    mins[i0 + 3] = rec("12:33", 73980, 73975, 74010, fr=[F(74000, "PE", "UNWINDING"), F(73900, "PE", "BUILDING")])
    mins[i0 + 4] = rec("12:34", 73910, 73895, 73985, fr=[F(73900, "PE", "UNWINDING")])         # touch 73,900
    rows = [row(hold.SESSION[i0 + j], 74100.0, 80 - j) for j in range(5)]
    tr = {"side": "PE", "role": "long", "qty": 20}
    out = plan.read(tr, mins, rows)
    assert [(t["t"], t["k"], t["word"]) for t in out["touches"]] == [("12:31", 74000, "DEFENDED"),
                                                                      ("12:34", 73900, "GIVING WAY")]
    assert out["rows"][0]["touch"] is None and out["rows"][2]["touch"] is None
    assert out["rows"][3]["rung"]["k"] == 73900                                   # the hand-over


def test_room_and_its_sentences():
    mins = day()
    i0 = hold.SESSION.index("12:30")
    mins[i0] = rec("12:30", 74020, 74015, 74030, fr=[F(74000, "PE", "BUILDING")])
    tr = {"side": "PE", "role": "long", "qty": 20}
    near = plan.read(tr, mins, [row("12:30", 74100.0, 80)])["rows"][0]
    assert near["room"] == {"rung": 20, "stop": 80, "text": "rung 20 pts · stop 80 pts",
                            "note": "you risk more points to the line than the next rung is away"}
    flat = day(close=74025.0)                                                     # every earlier low is 74,024
    flat[i0] = rec("12:30", 74020, 74020, 74030)                                  # the close IS the session low; no wall
    open_ = plan.read(tr, flat[:i0 + 1], [row("12:30", 74100.0, 80)])["rows"][0]
    assert open_["rung"]["src"] == "none" and open_["room"]["note"] == "no wall in the way — the stop is 80 pts behind you"


def test_the_two_exits_are_printed_side_by_side_never_merged():
    mins = day()
    out = plan.read({"side": "CE", "role": "long", "qty": 65}, mins, [row("10:00", 95.0, 5, verdict="FOLD")])
    ex = out["rows"][0]["exits"]
    assert ex["line"] == "the line: 95.0, 5 pts" and ex["window"].startswith("the window: FOLD")
    text = repr(out)
    assert "exit" not in text.replace("exits", "") and "book" not in text          # her decision: never an instruction


def test_next15_is_the_best_point_reached_not_the_last_and_waits_for_its_window():
    mins = day()
    i = hold.SESSION.index("12:00")
    mins[i] = rec("12:00", 100.0, 99.5, 100.5)
    mins[i + 2] = rec("12:02", 90.0, 80.0, 99.0)                                  # the best point: 20 pts
    mins[i + 15] = rec("12:15", 99.0, 98.5, 99.5)                                 # the last point: 1 pt
    assert plan.next15(mins, i, -1, i + 14) is None                               # the window has not finished
    got = plan.next15(mins, i, -1, i + 15)
    assert got == {"pts": 20.0, "to": "12:15", "short": False, "tag": "M"}
    late = hold.SESSION.index("15:20")
    assert plan.next15(mins, late, -1, 374) == {"pts": 1.0, "to": "15:29", "short": True, "tag": "M"}
    assert plan.next15(mins, i, 1, i + 15)["pts"] == 1.0                         # a long CE's side: the highest high, 101


def test_a_writer_gets_the_stop_only():
    mins = day()
    out = plan.read({"side": "CE", "role": "short", "qty": 20}, mins, [row("10:00", 105.0, 5, c=50.0)],
                    greeks=[(0.4, 0.001)] * 375)
    r = out["rows"][0]
    assert r["rung"] is None and r["room"] is None and out["touches"] == []
    assert r["stop"]["risk"] == round((0.4 * 5 + 0.5 * 0.001 * 25) * 20, 2) and r["stop"]["risk_tag"] == "I"


def test_a_plan_cut_at_a_minute_is_the_first_part_of_the_close_plan():
    mins = day()
    rows = [row(hold.SESSION[i], 110.0, 10) for i in range(100, 200)]
    tr = {"side": "CE", "role": "long", "qty": 1}
    full, cut = plan.read(tr, mins, rows), plan.read(tr, mins, rows[:50])
    assert cut["rows"] == full["rows"][:50]


def test_a_room_past_the_line_is_never_printed_negative():
    """After a close through the line the room is negative: "64 pts past it", never "-64 pts";
    L carries its thousands separator."""
    mins = day()
    i0 = hold.SESSION.index("12:30")
    mins[i0] = rec("12:30", 23119.5, 23110, 23125)                                 # no wall, the session low below
    tr = {"side": "CE", "role": "long", "qty": 65}
    r = plan.read(tr, mins, [row("12:30", 23055.45, -64, verdict="FOLD")])["rows"][0]
    assert r["exits"]["line"] == "the line: 23,055.5, 64 pts past it"
    assert r["room"]["text"] == "rung 6 pts · stop 64 pts past it" and r["room"]["stop"] == -64   # the number stays data
    ok = plan.read(tr, mins, [row("12:30", 23055.45, 64)])["rows"][0]
    assert ok["exits"]["line"] == "the line: 23,055.5, 64 pts"


def test_the_signed_band_rung_is_declared_not_built():
    assert plan.NOT_SHOWN_LINES[-1] == plan.NOT_SHOWN + "the band rung (PLAN rev 3, signed 13:20) — not built yet"
    assert "rev 3" in plan.DRAFT


def test_rev5_the_stop_sentence_the_break_level_and_the_stop_after_a_fold():
    """rev 5 §D item 12: "≈ ₹X [I] of premium between here and the line" -- no exit, no break rule; §A.2: the
    break level is its own line; §B: after a FOLD the STOP shows the line that broke, the logged L stays the
    trailed one, and NEXT WALL is hidden."""
    mins = day()
    live = row("10:00", 95.0, 5)
    live["line"].update(level=90.1, print="line 95.0 · breaks on a 3-min close below 90.1 — one median candle, 4.9 pts [M], read 09:59")
    r = plan.read({"side": "CE", "role": "long", "qty": 20}, mins, [live], greeks=[(0.5, 0.0)] * 375)["rows"][0]
    assert r["stop"]["text"] == "≈ ₹50 [I] of premium between here and the line" and "exit" not in r["stop"]["text"]
    assert r["stop"]["level"] == 90.1 and r["stop"]["level_text"].startswith("line 95.0 · breaks on a 3-min close below 90.1")
    assert r["stop"]["after_fold"] is None and r["next_wall"] is None
    folded = row("10:05", 99.0, -2, verdict="FOLD")
    folded["after_fold"] = {"L": 95.0, "src": "5m swing low 09:40", "text": "broke 10:02 by 1.4 pts [M] · past it by 2 pts",
                            "detail": "the line has since moved to 99.0 (5m swing low 09:55) — detail; a re-entry is a new trade with its own line",
                            "collapsed": "FOLD · NIFTY 100 CE · line 95.0 broke 10:02 by 1.4 pts · since 10:02"}
    f = plan.read({"side": "CE", "role": "long", "qty": 20}, mins, [folded])["rows"][0]
    assert f["stop"]["L"] == 99.0 and f["stop"]["after_fold"]["L"] == 95.0                  # the log keeps the trailed L
    assert f["stop"]["after_fold"]["text"].startswith("broke 10:02") and f["next_wall"] == plan.NOT_SHOWN + "the next wall — the plan ended at the FOLD"
