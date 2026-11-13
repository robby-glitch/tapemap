"""EXECUTE THE EDGE (execute.py): synthetic days only, no repo data. Spec docs/superpowers/specs/2026-11-13-execute-edge-design.md."""
import execute as X


def day_ones(path):
    """1-min candles 09:15..15:29 from {HH:MM: price} anchors, flat between them (h = l = c, so stops are exact)."""
    out, px = [], None
    for m in range(X.OPEN, 15 * 60 + 30):
        t = X.HM(m)
        px = path.get(t, px)
        out.append({"t": t, "o": px, "h": px, "l": px, "c": px, "v": 100})
    return out


def sig(t, side, px, ext, bad=False, z=1.5, **kw):
    S = -1 if side == "SELL" else 1
    e = {"t": t, "side": side, "px": px, "ext": ext, "S": S, "risk": abs(ext - px), "z": z, "bad": bad, "n": 1,
         "xb": X.M(t) - 3, "first": t, "level": px, "narm": 1, "fs": None, "vw": 30,
         "chk": {"GAP": False, "TREND": False, "FLOW": bad}}
    e.update(kw)
    return e


def test_contract_changed_on_the_day_after_a_monthly_expiry():
    assert X.contract_changed("2026-08-26", "2026-08-25")
    assert X.contract_changed("2026-09-30", "2026-09-29")
    assert X.contract_changed("2026-10-28", "2026-10-27")
    assert not X.contract_changed("2026-08-25", "2026-08-24")
    assert not X.contract_changed("2026-11-16", "2026-11-13")


def test_prev_weekday_skips_the_weekend():
    assert X.prev_weekday("2026-11-16") == "2026-11-13"
    assert X.prev_weekday("2026-11-13") == "2026-11-12"


def test_gap_reads_the_open_against_yesterday():
    prev = day_ones({"09:15": 95, "11:00": 99, "13:00": 90})
    assert X.gap(day_ones({"09:15": 100}), prev, False)["ok"] is False
    assert X.gap(day_ones({"09:15": 100}), prev, False)["text"] == "opened above yesterday's high 99f"
    assert X.gap(day_ones({"09:15": 85}), prev, False)["text"] == "opened below yesterday's low 90f"
    assert X.gap(day_ones({"09:15": 95}), prev, False)["ok"] is True
    assert X.gap(day_ones({"09:15": 95}), None, False)["ok"] is None
    assert X.gap(day_ones({"09:15": 95}), prev, True)["text"].startswith("could not check")


def test_flow_sum_from_the_bar_after_the_extreme_to_the_trigger_close():
    e = {"t": "10:03", "xb": X.M("10:00")}
    assert X.flow_sum({"10:03": -5, "10:04": 2, "10:05": None, "10:02": 99}, e) == -3
    assert X.flow_sum({}, e) is None


def test_vwap_untouched_counts_minutes_since_a_bar_held_vwap():
    bl = [{"t": X.HM(X.OPEN + 3 * k), "h": 101, "l": 99, "vwap": 100 if X.HM(X.OPEN + 3 * k) == "09:36" else 50}
          for k in range(12)]
    assert X.vwap_untouched(bl, "09:45") == 9
    assert X.vwap_untouched(bl[:4], "09:24") is None


def test_plan_a_flips_plan_b_holds_through_a_weak_signal():
    ones = day_ones({"09:15": 100, "10:20": 95, "10:40": 108, "11:00": 111})
    s = [sig("10:00", "SELL", 100, 110), sig("10:30", "BUY", 95, 90, bad=True)]
    a = X._walk(ones, s, "A")
    assert [(x["side"], x["why"], round(x["pts"])) for x in a["trades"]] == [("SELL", "FLIP", 5), ("BUY", "15:00", 16)]
    b = X._walk(ones, s, "B")
    assert [(x["side"], x["why"], round(x["pts"])) for x in b["trades"]] == [("SELL", "STOP", -10)]
    assert b["acts"][("10:30", "BUY")][0] == "HOLD"


def test_leg_paid_is_read_after_the_flip_for_the_entry():
    ones = day_ones({"09:15": 100, "10:20": 80, "11:30": 85, "12:30": 90})
    s = [sig("10:00", "SELL", 100, 105), sig("11:00", "BUY", 80, 75), sig("12:00", "BUY", 85, 79)]
    b = X._walk(ones, s, "B")
    assert [(x["side"], x["why"], round(x["pts"])) for x in b["trades"]] == [("SELL", "FLIP", 20)]
    assert b["won"] == "SELL"
    assert b["acts"][("11:00", "BUY")] == ("SKIP", "SELL") and b["acts"][("12:00", "BUY")][0] == "SKIP"
    assert [x["side"] for x in X._walk(ones, s, "A")["trades"]] == ["SELL", "BUY"]
    w = {k: X._walk(ones, s[:2], k, X.M("11:02")) for k in "ABC"}         # the valid BUY closes the SELL: the ticket says so
    tk = X._screen(ones, s[:2], w, {"ok": True, "text": ""}, {}, X.M("11:02"), None, None, 50)[2]
    assert tk[-1] == "EXIT SELL +20 · SKIP (LEG ✗) · wait"


def test_plan_c_keeps_a_working_trade_through_a_signal_without_room():
    ones = day_ones({"09:15": 100, "10:20": 90, "11:00": 70})
    s = [sig("10:00", "SELL", 100, 110), sig("10:30", "BUY", 90, 85, z=0.5)]
    assert [round(x["pts"]) for x in X._walk(ones, s, "C")["trades"]] == [30]
    assert [round(x["pts"]) for x in X._walk(ones, s, "B")["trades"]] == [10, -5]


def test_upto_keeps_the_trade_open():
    ones = day_ones({"09:15": 100, "10:20": 95, "10:40": 108, "11:00": 111})
    b = X._walk(ones, [sig("10:00", "SELL", 100, 110)], "B", X.M("10:45"))
    assert b["trades"] == [] and b["pos"]["side"] == "SELL" and b["pos"]["stop"] == 110


def test_day_state_reads_upto_and_names_a_gap_day():
    # A flat synthetic day has zero sigma, so the zone machine arms on every bar (as it would live): the state is not asserted
    # here; the WAIT and GAP DAY lines are asserted on the screen itself below.
    ones = day_ones({"09:15": 100})
    assert X.day_state("2026-11-13", ones)["state"] == "DAY END"
    ex = X.day_state("2026-11-13", ones, upto="10:00")
    assert ex["ok"] and ex["upto"] == "10:00" and ex["gap"]["ok"] is None
    ex = X.day_state("2026-11-13", ones, prev_ones=day_ones({"09:15": 95, "11:00": 99}), upto="10:00")
    assert ex["gap"]["ok"] is False and ex["line"].startswith("GAP DAY · opened above yesterday's high 99f · no fades")
    assert X.day_state("2026-11-13", [])["ok"] is False


def test_screen_wait_and_gap_day_lines():
    ones = day_ones({"09:15": 100})
    w = {k: X._walk(ones, [], k, X.M("10:00")) for k in "ABC"}
    assert X._screen(ones, [], w, {"ok": True, "text": ""}, {}, X.M("10:00"), None, None, 50) == ("WAIT", "WAIT · no zone armed", None)
    gp = {"ok": False, "text": "opened above yesterday's high 99f"}
    assert X._screen(ones, [], w, gp, {}, X.M("10:00"), None, None, 50)[1] == "GAP DAY · opened above yesterday's high 99f · no fades"
    armed = {"SELL": {"first": "10:03", "ext": 25261.0, "band": "u2"}}
    assert X._screen(ones, [], w, {"ok": True, "text": ""}, armed, X.M("10:05"), None, None, 50)[1] == "ARMED SELL · u2 touched 10:03 · extreme 25,261f"


def test_screen_trigger_ticket_and_in_trade_line():
    ones = day_ones({"09:15": 100, "10:20": 95, "10:40": 108, "11:00": 111})
    s = [sig("10:00", "SELL", 100, 110, fs=-50),
         sig("10:30", "BUY", 95, 90, bad=True, fs=-40, chk={"GAP": False, "TREND": False, "FLOW": True})]
    gp = {"ok": True, "text": "opened inside yesterday's range"}
    w = {k: X._walk(ones, s, k, X.M("10:32")) for k in "ABC"}
    st, line, tk = X._screen(ones, s, w, gp, {}, X.M("10:32"), None, None, 50)
    assert st == "TRIGGER" and line == "SKIP (FLOW ✗) · HOLD SELL" and tk[-1] == line
    assert tk[0].startswith("BUY 10:30 · try 1 · entry 95f · stop 90f (5)") and "FLOW   no buyers since the bottom -40 ✗" in tk
    w = {k: X._walk(ones, s, k, X.M("10:45")) for k in "ABC"}
    st, line, tk = X._screen(ones, s, w, gp, {}, X.M("10:45"), None, None, 50)
    assert st == "IN TRADE" and line == "HOLD SELL 100f · wrong only at 110f · out on a valid BUY or 15:00" and tk is None


def test_screen_day_end_and_the_card():
    ones = day_ones({"09:15": 100, "10:20": 95})
    s = [sig("10:00", "SELL", 100, 110)]
    w = {k: X._walk(ones, s, k) for k in "ABC"}
    st, line, _ = X._screen(ones, s, w, {"ok": True, "text": ""}, {}, X.M("15:10"), None, None, 50)
    assert st == "DAY END" and line == "PLAN B +5 (1) · PLAN A +5 (1) · PLAN C +5 (1)"
    c = X.card({"ok": True, "day": "d", "upto": "15:10", "state": st, "line": line, "ticket": None, "signals": [1]})
    assert c == {"ok": True, "day": "d", "upto": "15:10", "state": st, "line": line, "ticket": None}
    assert X.card({"ok": False, "why": "x"}) == {"ok": False, "why": "x"}


def test_other_side_oi_reads_writers_near_the_money():
    lad = {"10:02": {"pe": {"24900.0": 10.0, "25000.0": 20.0, "25300.0": 5.0}},
           "10:30": {"pe": {"24900.0": 12.0, "25000.0": 25.0, "25300.0": 1.0}}}
    pos = {"t": "10:00", "S": -1}
    assert X._other_side(lad, {"10:02": 25010.0}, pos, "10:30", 50) == 7.0
    assert X._other_side(None, {}, pos, "10:30", 50) is None


def test_sync_reads_banknifty_and_sensex_from_30_minutes_in():
    pos = {"t": "10:00", "S": -1}
    down, up = day_ones({"09:15": 500, "10:20": 480}), day_ones({"09:15": 500, "10:20": 520})
    assert X._sync({"BANKNIFTY": down, "SENSEX": down}, pos, X.M("10:20")) is None           # under 30 min in: not read
    assert X._sync({"BANKNIFTY": down, "SENSEX": down}, pos, X.M("10:40")) == "ALL 3 WITH YOU · hold"
    assert X._sync({"BANKNIFTY": down, "SENSEX": up}, pos, X.M("10:40")) == "1 of 2 with you"
    assert X._sync({"BANKNIFTY": up, "SENSEX": up}, pos, X.M("10:40")) == "NIFTY alone"
    assert X._sync({"BANKNIFTY": down, "SENSEX": []}, pos, X.M("10:40")) == "SYNC could not check: no SENSEX candles"


def test_log_rows_and_append_log_never_write_twice(tmp_path):
    ex = {"signals": [{"t": "10:00", "side": "SELL", "b": "TAKEN"}],
          "plan_b": {"trades": [{"t": "10:00", "side": "SELL", "x": "11:00", "why": "STOP", "pts": -10.0}]}}
    rows = X.log_rows(ex)
    assert [r["key"] for r in rows] == ["S|10:00|SELL", "C|B|10:00|SELL"]
    p = str(tmp_path / "exec" / "2026-11-13.jsonl")
    assert X.append_log(p, rows) == 2 and X.append_log(p, rows) == 0


def test_for_frame_reads_the_tape_and_the_frame(monkeypatch):
    monkeypatch.setattr(X.ruler, "ones_of", lambda day, idx="NIFTY": day_ones({"09:15": 100}) if day == "2026-11-13" else [])
    ex = X.for_frame({"day": "2026-11-13", "mins": ["09:15", "10:00"], "delta": [None, 5]})
    assert ex["ok"] and ex["upto"] == "10:00" and ex["gap"]["text"] == "could not check: no candles for the previous weekday"
    assert X.for_frame({"day": "2026-11-13", "mins": []})["ok"] is False


def test_the_jarvis_card_carries_the_block():
    import jarvis_log
    c = jarvis_log.card({"ok": True, "call": {}, "fut": [100.0], "exec": {"ok": True, "line": "WAIT · no zone armed"}})
    assert c["exec"] == {"ok": True, "line": "WAIT · no zone armed"}
