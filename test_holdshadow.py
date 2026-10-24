"""holdshadow.py: the three HOLD v3 candidate lines (shadow, never a rule) -- each line's own exit, its pairing with HOLD
v2's exit, the could-not-check paths; plus decode.exhaust_of (VALIDATE rev 3's EXHAUST), the hold trade's entry stamp
and the write-once shadow log."""
import json

import decode
import holdshadow as H

M = lambda h, m: h * 60 + m      # noqa: E731


def ones(m0, m1, px=lambda m: 100.0, hi=None, lo=None):
    return [{"s": m * 60, "h": (hi or px)(m), "l": (lo or px)(m), "c": px(m)} for m in range(m0, m1)]


def bars5(m0, m1, px):
    return [{"s": m * 60, "o": px, "h": px, "l": px, "c": px, "vol": 100} for m in range(m0, m1, 5)]


def blk(t, typ=None, eff=None, ex=None):
    return {"T": t, "t": t, "idx": "NIFTY", "onesided": {"type": typ}, "effort": eff or {}, "exhaust": ex}


def dec(*rows):
    return H.dec_rows(list(rows), "NIFTY")


# ---- CHOP: a fade takes its profit at VWAP on a CHOP / PIN day -------------------------------------------------------

def test_chop_line_fade_exits_at_vwap_on_a_chop_day():
    b5 = bars5(M(9, 15), M(10, 0), 110.0)                    # VWAP 110 (fut)
    o = ones(M(10, 0), M(10, 30), px=lambda m: 100.0, hi=lambda m: 111.0 if m == M(10, 12) else 105.0)
    r = H.chop_line(1, 100.0, M(10, 1), M(10, 30), o, b5, dec(blk("10:05", "CHOP")))
    assert r == {"applies": True, "how": "vwap", "t": "10:13", "px": 110.0, "typ": "CHOP"}


def test_chop_line_not_a_fade_mixed_day_and_unread_type():
    b5 = bars5(M(9, 15), M(10, 0), 110.0)
    o = ones(M(10, 0), M(10, 30), hi=lambda m: 111.0)
    assert H.chop_line(1, 112.0, M(10, 1), M(10, 30), o, b5, {})["how"] == "n/a"            # entered above VWAP: no fade
    assert H.chop_line(-1, 100.0, M(10, 1), M(10, 30), o, b5, {})["applies"] is False       # short below VWAP: no fade
    mixed = H.chop_line(1, 100.0, M(10, 1), M(10, 30), o, b5, dec(blk("10:00", "MIXED")))
    assert mixed["how"] == "open" and mixed["typ"] == "MIXED"
    unread = H.chop_line(1, 100.0, M(10, 1), M(10, 5), o, b5, {})
    assert unread["how"] == "open" and unread["unread"] == ["10:01", "10:02", "10:03", "10:04"]
    late = H.chop_line(1, 100.0, M(10, 1), M(10, 30), o, b5, dec(blk("10:20", "PIN")))     # PIN readable from 10:21
    assert late["t"] == "10:22" and late["typ"] == "PIN"
    assert H.chop_line(1, 100.0, M(9, 16), M(9, 30), o, [], {})["how"] == "cnc"             # no 5-min VWAP yet


# ---- POP: bought into covering; fold when the covering stops at a fresh, exhausted high ---------------------------------

def test_pop_line_cnc_and_not_bought_into_covering(monkeypatch):
    assert H.pop_line(1, M(13, 1), M(13, 30), [], ({}, {}), {}, [], "SENSEX", 100, {})["how"] == "cnc"
    monkeypatch.setattr(H, "_payers", lambda d, chain, m: {"side": "CE", "k": [22700, 22750], "states": ["BUILDING", "STALLED"]})
    r = H.pop_line(1, M(13, 1), M(13, 30), [], ({}, {}), {}, [], "NIFTY", 50, {})
    assert r["applies"] is False and r["how"] == "n/a" and "covering me nahi" in r["why"]


def test_pop_line_folds_when_the_covering_stops_at_a_fresh_high_with_the_tape_done(monkeypatch):
    states = lambda m: ["STALLED", "UNWINDING"] if m <= M(13, 6) else ["STALLED", "BUILDING"]  # noqa: E731
    monkeypatch.setattr(H, "_payers", lambda d, chain, m: {"side": "CE", "k": [22750, 22700], "states": states(m)})
    spot = {m: 22700.0 + (m - M(12, 40)) for m in range(M(12, 40), M(13, 30))}     # a new 30-min high every minute
    chain = ({H.hm(m): {"spot": p} for m, p in spot.items()}, {})
    o = ones(M(13, 0), M(13, 30), px=lambda m: 22720.0 + m - M(13, 0))
    ex = {"d": 1, "bar": "13:00", "close": "13:05", "ratio": 0.1}
    d = dec(blk("13:05", ex=ex))
    cache = {}
    r = H.pop_line(1, M(13, 1), M(13, 30), o, chain, d, [], "NIFTY", 50, cache)
    assert r["how"] == "pop" and r["t"] == "13:09" and r["ex"] == ["EXHAUST 13:00"]   # 13:06 still covering; 13:09 stopped
    assert cache[M(13, 6)]["stopped"] is False and cache[M(13, 9)]["fresh"] is True
    # the same, but the tape is not done: the line stays open
    assert H.pop_line(1, M(13, 1), M(13, 30), o, chain, dec(blk("13:05")), [], "NIFTY", 50, {})["how"] == "open"


def test_exhausted_and_fresh_windows():
    m = M(11, 0)
    e = lambda x, t: {"effort": {"at": "HIGH", "x": x, "t": t}}                              # noqa: E731
    assert H.exhausted(1, e(2.0, "10:45"), m, []) == ["effort 2.0x"]
    assert H.exhausted(1, e(2.0, "10:44"), m, []) == [] and H.exhausted(1, e(1.99, "10:59"), m, []) == []
    assert H.exhausted(-1, {"effort": {"at": "LOW", "x": 3.0, "t": "10:59"}}, m, []) == []   # >= 2x at a low: noise
    assert H.exhausted(-1, {}, m, [(M(10, 46), -1)]) == ["ABSORB"] and H.exhausted(-1, {}, m, [(M(10, 45), -1)]) == []
    assert H.exhausted(1, {"exhaust": {"d": -1, "close": "10:55"}}, m, []) == []
    spot = {M(10, 30) + k: 100.0 + k for k in range(31)}                                     # high 130 at 11:00
    assert H.fresh(1, spot, M(11, 0), 50) and not H.fresh(-1, spot, M(11, 0), 50)
    spot[M(11, 0)] = 116.4                                                                   # 12.6 under 129: > 1/4 of 50
    assert not H.fresh(1, spot, M(11, 0), 50)
    spot = {M(10, 30) + k: (100.0 if k != 24 else 140.0) for k in range(31)}                 # the high set 6 min ago
    spot[M(11, 0)] = 139.0
    assert not H.fresh(1, spot, M(11, 0), 50)


# ---- EFFORT: a long folds on an expensive high; a short holds while the low is cheap --------------------------------

def test_effort_line_long_folds_on_an_expensive_high():
    o = ones(M(10, 0), M(11, 0), px=lambda m: 200.0 + m - M(10, 0))
    d = dec(blk("10:20", eff={"at": "HIGH", "x": 1.99, "t": "10:19"}), blk("10:30", eff={"at": "HIGH", "x": 2.4, "t": "10:28"}))
    r = H.effort_line(1, M(10, 1), M(11, 0), o, d, None, "NIFTY")
    assert r == {"applies": True, "how": "effort", "t": "10:31", "px": 230.0, "x": 2.4}
    assert H.effort_line(1, M(10, 1), M(10, 31), o, d, None, "NIFTY")["how"] == "open"         # 10:31 bar not closed yet
    assert H.effort_line(1, M(10, 1), M(11, 0), o, d, None, "SENSEX")["how"] == "cnc"


def test_effort_line_short_defers_hold_v2_while_the_low_is_cheap():
    o = ones(M(10, 0), M(11, 30), px=lambda m: 300.0 - (m - M(10, 0)))
    cheap = {"at": "LOW", "x": 0.4, "t": "10:24"}
    d = dec(blk("10:25", eff=cheap), blk("10:30", eff={"at": "LOW", "x": 0.45, "t": "10:29"}),
            blk("10:35", eff={"at": "LOW", "x": 1.1, "t": "10:34"}))
    v2 = {"how": "line_push", "t": "10:28", "px": 270.0, "R": 1.2}
    r = H.effort_line(-1, M(10, 1), M(11, 0), o, d, v2, "NIFTY")
    assert r["how"] == "effort" and r["t"] == "10:36" and r["deferred_from"] == "10:28" and r["px"] == 265.0
    assert H.effort_line(-1, M(10, 1), M(11, 0), o, d, dict(v2, t="10:40"), "NIFTY")["how"] == "v2"   # not cheap at 10:40
    assert H.effort_line(-1, M(10, 1), M(11, 0), o, d, {"how": "open"}, "NIFTY")["how"] == "open"


# ---- pairing with HOLD v2 ---------------------------------------------------------------------------------------------

def test_pair_first_exit_wins_and_final_needs_hold_v2_out():
    own = {"applies": True, "how": "vwap", "t": "10:13", "px": 110.0}
    v2o, v2late, v2early = {"how": "open"}, {"how": "line_init", "t": "11:00", "px": 95.0, "R": -1.0}, \
        {"how": "gave_up", "t": "10:05", "px": 99.0, "R": -0.2}
    a = H._pair("CHOP", own, 1, 100.0, 5.0, v2o)
    assert (a["how"], a["R"], a["final"], a["dR"]) == ("vwap", 2.0, False, None)
    b = H._pair("CHOP", own, 1, 100.0, 5.0, v2late)
    assert (b["how"], b["R"], b["final"], b["dR"]) == ("vwap", 2.0, True, 3.0)
    c = H._pair("CHOP", own, 1, 100.0, 5.0, v2early)
    assert (c["how"], c["t"], c["R"], c["dR"]) == ("v2", "10:05", -0.2, 0.0)
    na = H._pair("POP", {"applies": False, "how": "n/a", "why": "x"}, 1, 100.0, 5.0, v2late)
    assert na["how"] == "v2" and na["final"] and na["applies"] is False and na["dR"] == 0.0
    sh = H._pair("EFFORT", {"applies": True, "how": "effort", "t": "11:30", "px": 90.0}, -1, 100.0, 5.0, v2late)
    assert sh["how"] == "effort" and sh["R"] == 2.0 and sh["chip"] == "low sasta: ruke raho"     # after v2: deferred
    assert H.text(b, basis=20.0).startswith("CHOP · out 10:13 @110f|90s · +2.00R")


def test_lines_end_to_end_and_the_log_row():
    o = ones(M(10, 0), M(10, 30), px=lambda m: 100.0, hi=lambda m: 111.0 if m == M(10, 12) else 105.0)
    L = H.lines(1, 100.0, 95.0, M(10, 1), M(10, 30), o, bars5(M(9, 15), M(10, 0), 110.0), ({}, {}),
                dec(blk("10:05", "CHOP")), [], {"how": "open"}, "SENSEX", 100, {}, basis=10.0)
    assert [x["line"] for x in L] == ["CHOP", "POP", "EFFORT"]
    assert L[0]["how"] == "vwap" and L[0]["R"] == 2.0 and L[1]["own"]["how"] == "cnc" and L[2]["own"]["how"] == "cnc"
    row = H.row("2026-10-23", {"id": "T1", "idx": "SENSEX", "validate": {"rev": "3", "word": "WAIT"}}, L[0], 1.0)
    assert row["line"] == "CHOP" and row["sh"] == {"t": "10:13", "px": 110.0, "R": 2.0} and row["final"] is False
    assert row["validate"]["word"] == "WAIT" and json.dumps(row)


def test_payers_read_the_payers_side_of_fronts():
    g = {f"10:{m:02d}": {"spot": 22720.0, "k": {22700: [100.0 * m, 50.0], 22750: [80.0 * m, 10.0]}} for m in range(0, 20)}
    p = H._payers(1, (g, {}), M(10, 20))
    assert p["side"] == "CE" and set(p["k"]) == {22700.0, 22750.0} and set(p["states"]) == {"BUILDING"}
    assert H._payers(-1, (g, {}), M(10, 20))["side"] == "PE"
    assert H._payers(1, (g, {}), M(10, 40)) is None                       # the grid is stale: no read, never a verdict


# ---- decode.exhaust_of (VALIDATE rev 3's EXHAUST) ---------------------------------------------------------------------

def test_exhaust_of_is_fade_d_2a_on_the_decode_leg():
    leg = {"d": 1}
    ok = {"bar": "12:50", "close": "12:55", "ratio": 0.12, "ok": True}
    assert decode.exhaust_of({"dleg": leg, "dfd": {"a": [dict(ok, ok=False), ok]}}) == {"d": 1, "bar": "12:50", "close": "12:55", "ratio": 0.12}
    assert decode.exhaust_of({"dleg": leg, "dfd": {"a": [ok, dict(ok, ok=False)]}}) is None     # the latest extreme only
    assert decode.exhaust_of({"dleg": None, "dfd": {"a": [ok]}}) is None
    assert decode.exhaust_of({"dleg": leg, "dfd": None}) is None


# ---- the server: the entry stamp and the write-once log ---------------------------------------------------------------

def test_hold_trade_keeps_a_sanitised_validate_stamp():
    import server
    doc = {"idx": "NIFTY", "k": 22700, "side": "CE", "role": "long", "t0": "10:05:00", "p0": 120,
           "validate": {"rev": "3 (VALIDATE-PREREG-rev3 a4186306)", "word": "WAIT", "w": 5, "a": 1, "n": 2, "c": 1, "of": 9, "x": "junk"}}
    tr, why = server._hold_trade(doc)
    assert why is None and tr["validate"] == {"rev": "3 (VALIDATE-PREREG-rev3 a4186306)", "word": "WAIT", "w": 5, "a": 1,
                                              "n": 2, "c": 1, "of": 9}
    assert server._hold_trade(dict(doc, validate="GO"))[0]["validate"] is None


def test_shadow_log_is_write_once_and_logs_open_lines_at_her_exit(tmp_path, monkeypatch):
    import server
    monkeypatch.setattr(server, "SHADOW_DIR", str(tmp_path))
    monkeypatch.setattr(server, "_SHADOW_SEEN", {})
    tr = {"id": "T1", "idx": "NIFTY"}
    v2 = {"how": "line_init", "t": "11:00", "px": 95.0, "R": -1.0}
    fin = H._pair("CHOP", {"applies": True, "how": "vwap", "t": "10:13", "px": 110.0}, 1, 100.0, 5.0, v2)
    opn = H._pair("POP", {"applies": True, "how": "open"}, 1, 100.0, 5.0, {"how": "open"})
    server._shadow_log("2026-10-23", tr, [fin, opn])
    server._shadow_log("2026-10-23", tr, [fin, opn])                    # again: nothing new
    path = tmp_path / "shadow_2026-10-23.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert [(r["line"], r["final"]) for r in rows] == [("CHOP", True)]
    monkeypatch.setattr(server, "_SHADOW_SEEN", {})                      # a restart: the file is read before writing
    server._shadow_log("2026-10-23", tr, [fin, opn], at_exit=True)
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert [(r["line"], r["final"]) for r in rows] == [("CHOP", True), ("POP", False)]
