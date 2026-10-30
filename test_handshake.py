"""A132: the HANDSHAKE (handshake.py) on synthetic days -- the first-crossing answer, the floor / cap only when writers
opened it, the fut leg, the FLOW stream line (answered only, never Telegram), the server pass write-once across a restart,
and the voice's HANDSHAKE line that never changes the verdict. Every file is under tmp_path (conftest STR_PATHS)."""
import copy
import json
import os
import time
from datetime import datetime

import handshake
import palat
import telegram_out
import voice
from chain_live import IST

DAY = "2026-10-28"
S = 22600


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def scene(d=-1, cut=True, fut=600, push=640):
    """Spot S flat; a push of 300 lots direction d at `push` (10:40); the attacked wall (S-50 PE for a sell, S+50 CE for a
    buy, 100L, bar 4L) cut 5L from push+2 (TOOT) or never (NAHI); price leans 10 the push's way (not through); the other
    side adds 5L one step behind price with its premium falling 5 more than delta explains (WRITERS); the future's OI
    rises `fut` lots from push."""
    wk, side, other = (S - 50, "pe", "ce") if d < 0 else (S + 50, "ce", "pe")
    bk = S + 50 if d < 0 else S - 50
    R = {}
    for m in range(560, 690):
        strikes = []
        for k in range(S - 200, S + 250, 50):
            leg = {"ce": {"oi": 1e6, "ltp": 50.0, "delta": 0.5}, "pe": {"oi": 1e6, "ltp": 50.0, "delta": -0.5}}
            if k == wk:
                leg[side]["oi"] = 1e7 - (5e5 if cut and m >= push + 2 else 0)
            if k == bk:
                leg[other]["oi"] = 1e6 + (5e5 if m >= push + 2 else 0)
                leg[other]["ltp"] = 100.0 - (10.0 if m >= push + 2 else 0)
            strikes.append({"k": k, **leg})
        R[m] = {"ts": hm(m) + ":59", "spot": S if m <= push else S + 10 * d, "strikes": strikes}
    F = {m: (10 if m % 2 else -10) for m in R}
    F[push - 1], F[push] = 100 * d, 200 * d
    return {"idx": "NIFTY", "R": R, "ms": sorted(R), "F": F, "src": {m: "D" for m in F}, "lot": 65, "fm": {},
            "oim": {m: 1e7 + (fut * 65 if m >= push else 0) for m in R}, "flow_of": "NIFTY", "min_push": 150, "pushes": []}


def test_palat_reads_the_one_copy():
    assert palat.pushes is handshake.pushes and palat.dext_flow is handshake.dext_flow and palat.flow is handshake.flow
    assert palat.who is handshake.who_opened and palat.book_flow is handshake.book_flow


def test_the_answer_is_the_first_minute_the_wall_crosses_its_bar():
    inp = scene()
    p = handshake.pushes(inp["F"], inp["ms"], 150)
    assert [(x["m"], x["dir"], x["lots"]) for x in p] == [(640, -1, -300)]
    R, ms = inp["R"], inp["ms"]
    assert handshake.answer(R, ms, p[0], 642) is None                     # 10:42 is not complete before 10:43
    assert handshake.answer(R, ms, p[0], 643) is None                     # crossed at 10:42; 10:43 has not confirmed it yet
    assert handshake.answer(R, ms, p[0], 644) == {"ans": "TOOT", "k": 22550, "chg": -5.0, "bar": 4.0, "am": 642, "held": 643}
    assert handshake.answer(R, ms, p[0], 644, first=False) is None        # palat: the fixed 4-min minute only
    assert handshake.answer(R, ms, p[0], 645, first=False)["am"] == 644
    assert handshake.answer(R, ms, p[0], 645, k=22600)["ans"] == "NAHI"   # read at a given wall (the voice's)
    nahi = scene(cut=False)
    assert handshake.answer(nahi["R"], ms, p[0], 644) is None             # no crossing yet, 4 min not passed: pending
    assert handshake.answer(nahi["R"], ms, p[0], 645) == {"ans": "NAHI", "k": 22550, "chg": 0.0, "bar": 4.0, "am": 644}


def test_a_push_row_carries_its_answer_floor_fut_and_points():
    r, = handshake.read(scene(), 680)
    assert (r["t"], r["dir"], r["lots"], r["src"], r["k"], r["side"], r["oi_L"]) == ("10:40", -1, -300, "D", 22550, "PE", 100.0)
    assert (r["ans"], r["am"], r["after"], r["chg"], r["bar"]) == ("TOOT", "10:42", 2, -5.0, 4.0)
    assert r["behind"] == {"k": 22650, "side": "CE", "add": 5.0, "who": "WRITERS"} and r["floor_cap"] == 22650
    assert r["fut"] == {"lots": 600, "leg": "FRESH"} and r["effort"] is None
    assert (r["p15"], r["p30"], r["final"], r["key"]) == (10, 10, True, "NIFTY|FLOW|10:40|▼")
    early, = handshake.read(scene(), 660)
    assert early["p30"] is None and not early["final"]                    # the log waits for +30
    assert handshake.read(scene(fut=-600), 680)[0]["fut"]["leg"] == "COVER"
    assert handshake.read(scene(fut=100), 680)[0]["fut"]["leg"] == "FLAT"


def test_a_buyer_opened_add_behind_price_is_not_a_floor():
    inp = scene(d=1)
    for m, r in inp["R"].items():                                          # the PE add behind: premium UP -> buyers
        for s in r["strikes"]:
            if s["k"] == S - 50 and m >= 642:
                s["pe"]["ltp"] = 110.0
    r, = handshake.read(inp, 680)
    assert r["behind"]["who"] == "KHAREEDAR" and r["floor_cap"] is None
    assert handshake.message(r)["line"] == ("10:42  NIFTY  ◆ PUSH ▲ 10:40 +300 lots · CE 22,650s deewar toot rahi −5.0L "
                                            "(2 min) · peeche PE 22,550s +5.0L kharidar · floor nahi · fut fresh +600 lots")


def test_the_stream_line_is_answered_only_screen_only():
    m = handshake.message(handshake.read(scene(), 680)[0])
    assert m["line"] == ("10:42  NIFTY  ◆ PUSH ▼ 10:40 −300 lots · PE 22,550s deewar toot rahi −5.0L (2 min) · "
                         "cap 22,650s writers +5.0L · fut fresh +600 lots")
    assert (m["kind"], m["dir"], m["key"], m["quiet"]) == ("FLOW", -1, "NIFTY|FLOW|10:40|▼", True)
    assert not telegram_out.wants(m) and not telegram_out.wants(dict(m, quiet=False))
    assert handshake.message(handshake.read(scene(cut=False), 680)[0]) is None      # a NAHI never reaches the stream
    for i in ("SENSEX", "BANKNIFTY"):                                         # their bar is NIFTY's 3L: never said yet
        assert handshake.message(handshake.read(dict(scene(), idx=i), 680)[0]) is None
        assert handshake.defend(dict(scene(d=1), idx=i), -1, 22650, 646) is None


def test_the_server_says_each_push_once_and_logs_it_once_across_a_restart(monkeypatch):
    import server
    monkeypatch.setattr(handshake, "load", lambda day, idx: scene() if idx == "NIFTY" else dict(scene(cut=False), idx=idx))
    monkeypatch.setattr(server, "_HS", {"day": None, "upto": None, "inp": {}, "logged": None})
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    now = datetime(2026, 10, 28, 10, 43, 30, tzinfo=IST).timestamp()
    assert server._hs_pass(DAY, 643 * 60 + 19) == []                       # 10:42 not yet read (the 20 s grace)
    assert server._hs_pass(DAY, 643 * 60 + 20) == []                       # crossed at 10:42; 10:43 not read yet (handshake-2)
    got = server._hs_pass(DAY, 644 * 60 + 20)
    assert [m["key"] for m in got] == ["NIFTY|FLOW|10:40|▼"]               # BANKNIFTY / SENSEX here: NAHI, silent
    assert server._hs_pass(DAY, 644 * 60 + 40) == []                       # the same minute: not read again
    assert len(server._msg_write(DAY, got, now)) == 1
    assert server._msg_write(DAY, server._hs_pass(DAY, 645 * 60 + 20), now) == []
    path = os.path.join(server.HS_DIR, f"handshake_{DAY}.jsonl")
    assert not os.path.exists(path)                                        # +30 not known yet
    server._hs_pass(DAY, 671 * 60 + 20)                                    # +30 known: NIFTY's row
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert [(r["idx"], r["ans"], r["rev"], r["day"]) for r in rows] == [("NIFTY", "TOOT", handshake.REV, DAY)]
    monkeypatch.setattr(server, "_HS", {"day": None, "upto": None, "inp": {}, "logged": None})   # a restart
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    assert server._msg_write(DAY, server._hs_pass(DAY, 672 * 60 + 20), now) == []
    assert len(open(path, encoding="utf-8").readlines()) == 1
    assert [m["key"] for m in server._hs_pass(DAY, 932 * 60 + 20)] == ["NIFTY|FLOW|10:40|▼"]   # the close pass: + BNF / SENSEX
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert sorted((r["idx"], r["ans"]) for r in rows) == [("BANKNIFTY", "NAHI"), ("NIFTY", "TOOT"), ("SENSEX", "NAHI")]
    assert server._hs_pass(DAY, 940 * 60) == [] and len(rows) == 3          # then it rests


def _voice(mp, r, d_push, cut, fut, at_m):
    """The voice for test_voice's trade (d -1, a short; her wall W = 22,650 CE above) plus the server's l6 at minute at_m."""
    import server
    import test_voice
    mp.setattr(server.time, "localtime", lambda *a: time.struct_time((2026, 10, 28, at_m // 60, at_m % 60, 0, 2, 301, 0)))
    base = test_voice.run(r, test_voice.h2())
    inp = scene(d=d_push, cut=cut, fut=fut)
    handshake.read(inp, at_m)
    server._HS.update(day="2026-10-28", upto=at_m, inp={"NIFTY": inp})
    vc = copy.deepcopy(base)
    server._hs_voice({"idx": "NIFTY"}, r, vc)
    return base, vc


def test_the_voice_line_never_changes_the_verdict(monkeypatch):
    import server
    import test_voice
    monkeypatch.setattr(server, "_HS", {"day": None, "upto": None, "inp": {}, "logged": None})
    W = {"k": 22650, "side": "CE", "oi": 9.0e6, "peak": 10.0e6, "upd": 3, "off": 0.0, "bleed_t": None}
    for words, want in ((("HOLD", None), "HOLD"), (("PAST GIVE-UP", "give-up crossed · x"), "WARN")):
        r = test_voice.rep(W=W, headline=words[0], clause=words[1] or "behind you: flow, OI")
        base, vc = _voice(monkeypatch, r, 1, True, 600, 646)                             # a buy push at her: TOOT at her wall + FRESH
        assert vc.pop("l6") == "HANDSHAKE: deewar 22,650s CE toot rahi −5.0L + fut fresh → khatra"
        assert vc == base and base["state"] == want                         # the state, the stop, seq: untouched
        base, vc = _voice(monkeypatch, r, 1, False, 0, 646)                              # no answer at her wall: a pullback
        assert vc.pop("l6") == "HANDSHAKE: push ▲ 10:40 +300 lots · 22,650s CE jawab nahi → pullback lagta hai"
        assert vc == base
    r = test_voice.rep(W=W)
    assert "l6" not in _voice(monkeypatch, r, 1, True, 600, 655)[1]                     # older than 10 min: no line
    assert "l6" not in _voice(monkeypatch, r, -1, True, 600, 646)[1]                    # a push WITH her: no line
    assert "l6" not in _voice(monkeypatch, test_voice.rep(W=None), 1, True, 600, 646)[1]   # no wall known: no line
    base, vc = _voice(monkeypatch, r, 1, True, 0, 646)                                   # TOOT without fresh: facts, no verdict word
    assert vc["l6"] == "HANDSHAKE: push ▲ 10:40 +300 lots · deewar 22,650s CE toot rahi −5.0L · fut flat"


def test_the_flow_kind_renders_through_the_one_line():
    m = handshake.message(handshake.read(scene(), 680)[0])
    assert m["line"].startswith("10:42  NIFTY  ◆ PUSH") and "%" not in m["line"]


def _book(t0_ms, secs, gap_at=None, gap_s=0, buy_after_gap=0):
    """1-second book rows from t0, 1 lot at the ask each; a gap of gap_s seconds before row gap_at, whose first row carries
    buy_after_gap lots of catch-up volume (the laptop waking)."""
    rows, t, vtt = [], t0_ms, 0
    for i in range(secs):
        if gap_at is not None and i == gap_at:
            t += gap_s * 1000
            vtt += buy_after_gap * 65
        rows.append({"t": t, "ltp": 101.0, "b": [[100.0, 1]], "a": [[101.0, 1]], "vtt": vtt, "oi": 1000 + i})
        t += 1000
        vtt += 65
    return rows


def test_a_book_hole_drops_every_minute_it_touches_from_the_flow():
    """J1 (A142): the laptop slept 12:54:12-13:00:20 on 28 Oct and the book's catch-up came back as one +3,534-lot 'push'."""
    t0 = int(datetime(2026, 10, 28, 12, 50, tzinfo=IST).timestamp() * 1000)
    rows = _book(t0, 600, gap_at=250, gap_s=374, buy_after_gap=3534)
    hs = handshake.holes(rows)
    assert len(hs) == 1 and hs[0][1] - hs[0][0] == 375 * 1000
    blind = handshake.hole_minutes(hs)
    d, v = handshake.book_flow(rows, 65)
    assert blind and not (blind & set(d)) and not (blind & set(v))   # no flow is read in a minute the book could not see
    assert max(abs(x) for x in d.values()) < 100                     # the catch-up's 3,534 lots never become a minute's delta
    assert handshake.holes(_book(t0, 600)) == []


def test_a_crossing_that_comes_back_the_next_minute_is_wapas_not_toot():
    """J1 handshake-2 (A143): 17 of 103 NIFTY answers over 16 days read differently at m+4 than at the first crossing; 13
    were a TOOT that read NAHI (19 Oct 10:41: -12.8L, then +4.4L). Here the wall is cut 5L at 10:42 only, back at 10:43."""
    inp = scene()
    p = handshake.pushes(inp["F"], inp["ms"], 150)[0]
    R = copy.deepcopy(inp["R"])
    for m in range(643, 690):
        for s in R[m]["strikes"]:
            if s["k"] == S - 50:
                s["pe"]["oi"] = 1e7
    assert handshake.answer(R, inp["ms"], p, 644) is None                 # un-crossed at 10:43: read on to 10:44 (m+4)
    assert handshake.answer(R, inp["ms"], p, 645) == {"ans": "NAHI", "k": S - 50, "chg": 0.0, "bar": 4.0, "am": 644,
                                                      "wapas": True}
    row = handshake.read(dict(inp, R=R), 646)[0]
    assert row["ans"] == "NAHI" and row["wapas"] is True and row["held"] is None


def _band(inp, each, ks=(S - 100, S), side="pe", frm=642):
    """The attacked strike stays flat (scene cut=False); `ks`, in its band, change `each` L from `frm` on."""
    R = copy.deepcopy(inp["R"])
    for m in range(frm, 690):
        for s in R[m]["strikes"]:
            if s["k"] in ks:
                s[side]["oi"] += each * 1e5
    return dict(inp, R=R)


def test_where_the_strike_says_nothing_its_band_answers():
    """G1 (30 Oct, DECODE-GAPS): 29 Oct, of 24 NAHI pushes the band (strike +/- 2) crossed the bar in 14 (13:53: strike
    -1.3L, band -14.2L). The strike first; the band only where the strike says nothing, at 2x its bar, with the hold."""
    inp = scene(cut=False)
    p = handshake.pushes(inp["F"], inp["ms"], 150)[0]
    cut = _band(inp, -4.0)                                                # 22,500 and 22,600 PE each -4L: band -8L = 2x bar
    assert handshake.answer(cut["R"], inp["ms"], p, 643) is None          # crossed at 10:42, not yet held
    assert handshake.answer(cut["R"], inp["ms"], p, 644) == {
        "ans": "TOOT", "k": S - 50, "chg": -8.0, "bar": 8.0, "am": 642, "via": "band",
        "band": [S - 150, S - 100, S - 50, S, S + 50], "wk": S - 100, "held": 643}
    assert handshake.answer(cut["R"], inp["ms"], p, 645, first=False)["ans"] == "NAHI"   # palat: the one strike, unchanged
    assert handshake.answer(cut["R"], inp["ms"], p, 645, k=S - 50)["ans"] == "NAHI"      # the voice's wall: unchanged
    weak = _band(inp, -3.0)                                               # band -6L: under 2x the bar
    assert handshake.answer(weak["R"], inp["ms"], p, 645)["ans"] == "NAHI"
    row = handshake.read(cut, 680)[0]
    assert (row["ans"], row["via"], row["chg"]) == ("TOOT", "band", -8.0)
    assert "PE 22,550s ±2 deewar toot rahi −8.0L" in handshake.message(row)["line"]
    plain = handshake.read(scene(), 680)[0]                               # the strike crossed itself: no band tag
    assert plain["via"] is None and "±2" not in handshake.message(plain)["line"]


def test_an_add_at_the_wall_by_buyers_is_not_a_defence():
    """G4 (30 Oct): 5 of 11 TIKIs on 27-29 Oct were opened by BUYERS (premium up more than delta explains): buyers betting
    the wall breaks, fuel FOR the push. The word follows who; the voice at her wall says the same."""
    def tiki(prem):
        inp = scene(d=1, cut=False)                                       # a buy push at the 22,650 CE wall
        for m in range(642, 690):
            for s in inp["R"][m]["strikes"]:
                if s["k"] == S + 50:
                    s["ce"]["oi"] += 5e5
                    s["ce"]["ltp"] = prem
        return handshake.read(inp, 680)[0]
    buyers, writers = tiki(60.0), tiki(50.0)                              # spot +10 x delta 0.5 explains +5: 60 = buyers
    assert (buyers["ans"], buyers["who"], writers["ans"], writers["who"]) == ("TIKI", "KHAREEDAR", "TIKI", "WRITERS")
    assert "CE 22,650s kharidar ghuse (deewar nahi) +5.0L (2 min)" in handshake.message(buyers)["line"]
    assert "CE 22,650s deewar tiki +5.0L (2 min)" in handshake.message(writers)["line"]
    h = {"p": {"dir": 1, "m": 640, "lots": 300}, "a": {"ans": "TIKI", "who": "KHAREEDAR", "chg": 5.0}, "fut": {"leg": "FLAT"}}
    assert "kharidar ghuse +5.0L (deewar nahi)" in voice.handshake_line(h, 22650, "CE")
    assert "deewar 22,650s CE tiki" in voice.handshake_line(dict(h, a=dict(h["a"], who="WRITERS")), 22650, "CE")


def test_the_chain_backfill_fills_only_the_minutes_the_recorder_never_saw():
    """J1b: the REST backfill (chain_backfill: per strike the OI CHANGE + premiums) fills the chain minutes a hole left empty,
    as absolute OI = the observed base (oi - oi_chg, constant for the day) + the change; an observed minute is never touched."""
    seen = {"ts": "11:40:58", "spot": S, "strikes": [{"k": 22550, "ce": {"oi": 5e6, "oi_chg": 1e6, "ltp": 9.0},
                                                      "pe": {"oi": 1e7, "oi_chg": 2e6, "ltp": 50.0, "delta": -0.5}}]}
    R = {700: seen}
    grid = {"11:40": {"spot": 1.0, "k": {22550: (0.0, 0.0)}, "px": {}, "src": "backfill"},       # observed: untouched
            "11:41": {"spot": S + 5, "k": {22550: (1.2e6, 1.5e6), 22600: (1.0, 1.0)}, "px": {22550: (8.0, 55.0)},
                      "src": "backfill"}}
    out = handshake.with_backfill(R, grid)
    assert out[700] is seen
    leg = handshake._leg(out[701], 22550, "pe")
    assert out[701]["src"] == "backfill" and out[701]["spot"] == S + 5
    assert leg["oi"] == 9.5e6 and leg["ltp"] == 55.0 and "delta" not in leg      # base 8e6 + 1.5e6; WHO stays "?"
    assert handshake._leg(out[701], 22600, "ce").get("oi") is None                # never seen live: no base, no OI
    assert handshake.with_backfill(R, {}) == R


def test_a_push_first_answered_late_is_tagged_backfilled(monkeypatch):
    """A175: a push whose answer is first seen > 3 min after its confirmation minute (a Dext refill rewrote past minutes,
    or a restart) is said once, quiet, its line ending '· backfilled'; one seen on time is not."""
    import server
    monkeypatch.setattr(handshake, "load", lambda day, idx: scene() if idx == "NIFTY" else dict(scene(cut=False), idx=idx))
    monkeypatch.setattr(server, "_HS", {"day": None, "upto": None, "inp": {}, "logged": None})
    got = server._hs_pass(DAY, 644 * 60 + 20)                              # confirmed 10:43, read at upto 10:44: on time
    assert [m["key"] for m in got] == ["NIFTY|FLOW|10:40|▼"] and not got[0]["line"].endswith("· backfilled")
    monkeypatch.setattr(server, "_HS", {"day": None, "upto": None, "inp": {}, "logged": None})
    late = server._hs_pass(DAY, 649 * 60 + 20)                             # first seen at upto 10:49: 6 min late
    assert [m["key"] for m in late] == ["NIFTY|FLOW|10:40|▼"]
    assert late[0]["quiet"] and late[0]["line"].endswith("· backfilled") and not telegram_out.wants(late[0])
