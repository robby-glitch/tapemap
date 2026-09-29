"""The hold window's server half -- /api/hold, the trades she marks, the two forward
logs and the close-time import -- on the board's frozen NIFTY 09-24 grid with the
clock held and every REST / disk feeder replaced. Plumbing and determinism only:
what the rules SAY is test_hold.py's job, whether they are right is §7's."""
import io
import json

import pytest

import board
import day_state
import hold
import hold_log
import plan
import server
from test_board import PRIOR, _Cap, _Poller, fx  # noqa: F401  (fx is the module fixture)

DAY = "2026-09-24"
MARK = {"op": "mark", "idx": "NIFTY", "k": 23200, "side": "PE", "role": "long", "t0": "12:20:30", "p0": 100, "qty": 65}


class _Post(_Cap):
    def __init__(self, path, body, poller, headers=None):
        super().__init__(path, poller=poller)
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.headers = {"Content-Length": str(len(raw)), **(headers or {})}
        self.rfile = io.BytesIO(raw)

    def _json(self, body, code=200):
        self.status = code
        super()._json(body, code)


def _post(path, body, poller, headers=None):
    cap = _Post(path, body, poller, headers)
    server.Handler.do_POST(cap)
    return cap.sent


def _get(path, poller):
    cap = _Cap(path, poller=poller)
    server.Handler.do_GET(cap)
    return cap.sent


def _fresh():
    return {"facts": {}, "locks": {}, "trades": [], "trades_day": None, "sigma": {}, "peaks": {}}


@pytest.fixture
def srv(fx, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setattr(server, "_BOARD", server._board_fresh())
    monkeypatch.setattr(server, "_HOLD", _fresh())
    monkeypatch.setattr(day_state, "DIR", str(tmp_path / "day_state"))
    monkeypatch.setattr(hold_log, "DIR", str(tmp_path / "hold"))
    monkeypatch.setattr(hold_log, "_seen", {})
    monkeypatch.setitem(server._SENSES, "drag_day", {})
    monkeypatch.setitem(server._SENSES, "day_restored", 0)
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "15:45"))
    tr = fx["trend"]
    trd = {"m1_prior": tr["m1"][PRIOR[DAY]], "m30": tr["m30"], "d1": tr["d1"]}
    monkeypatch.setattr(server, "_hold_candles", lambda idx, day, asof: (trd, tr["m1"][DAY], None))
    monkeypatch.setattr(server, "_tape_reply", lambda idx, day: {"ok": False, "why": "no prints record in this test"})
    monkeypatch.setattr(server, "_hold_sigma", lambda *a: {"why": board.CC + "no REST in tests", "tag": "M"})
    monkeypatch.setattr(server, "_hold_peaks", lambda idx, day: {})     # no chain record: the grid's marks rank
    monkeypatch.setattr(server, "_hold_lot", lambda idx: 65)            # never the instrument dump (or its download)
    return _Poller(fx)


def _lines(kind):
    with open(hold_log.path(kind, DAY), encoding="utf-8") as f:
        return [json.loads(x) for x in f]


def test_a_marked_trade_is_read_and_a_repeat_is_served_from_the_cache(srv):
    got = _post("/api/hold/trades", MARK, srv)
    assert got["ok"] and got["trades"][0]["id"] == "NIFTY-23200PE-long-122030"
    a = _get("/api/hold?id=NIFTY-23200PE-long-122030", srv)
    assert a["ok"] and a["asof"] == "15:29" and a["draft"] == hold.DRAFT
    assert a["now"]["verdict"] in ("HOLD", "WATCH", "FOLD", "PATA NAHI") and a["now"]["line"]["tag"] == "M"
    assert a["entry"]["t"] == "12:19" and a["entry"]["text"].startswith("You entered into")
    assert a["side"]["text"] and a["side"]["agrees"] in ("agrees", "against", "no side — the rows do not agree")
    assert a["side"]["expiry"]["text"] == board.CC + "expiry not in the day's record"      # the test poller has none
    cn, rn = a["absent"]["checked_none"], a["absent"]["rule_note"]
    if a["fold"]:               # under a latch the rule is its own field (2026-09-29), never a "checked, none" sentence
        assert cn is None and rn == "nothing un-latches a FOLD; a re-entry is a new trade"
    else:
        assert rn is None and len({cn[:15], board.CC, a["absent"]["not_shown"][0][:13]}) == 3
    facts = server._HOLD["facts"]["NIFTY"]
    assert _get("/api/hold?id=NIFTY-23200PE-long-122030", srv) == a and server._HOLD["facts"]["NIFTY"] is facts
    assert _get("/api/hold/trades", srv)["trades"][0]["id"] == a["trade"]["id"]


def test_a_restart_reads_the_same_window(srv):
    _post("/api/hold/trades", MARK, srv)
    a = _get("/api/hold?id=NIFTY-23200PE-long-122030&rows=1", srv)
    server._save_day_state()
    server._HOLD.clear()
    server._HOLD.update(_fresh())
    server._BOARD.clear()
    server._BOARD.update(server._board_fresh())
    server._load_day_state()
    b = _get("/api/hold?id=NIFTY-23200PE-long-122030&rows=1", srv)
    assert b["trade"]["id"] == a["trade"]["id"]
    for k in ("now", "entry", "fold", "side", "rows"):
        assert b[k] == a[k], k
    # P1-01: her exit, and her undo of it, survive the same restart (each ok POST saves day_state)
    tid = a["trade"]["id"]

    def restart():
        server._HOLD.clear()
        server._HOLD.update(_fresh())
        server._BOARD.clear()
        server._BOARD.update(server._board_fresh())
        server._load_day_state()
    assert _post("/api/hold/trades", {"op": "exit", "id": tid, "exit_t": "13:10:00"}, srv)["ok"]
    restart()
    assert _get("/api/hold/trades", srv)["trades"][0]["exit_t"] == "13:10:00"
    assert _get(f"/api/hold?id={tid}", srv)["after_exit"] is True
    assert _post("/api/hold/trades", {"op": "reopen", "id": tid}, srv)["ok"]
    restart()
    assert _get("/api/hold/trades", srv)["trades"][0]["exit_t"] is None
    assert _get(f"/api/hold?id={tid}", srv)["after_exit"] is False


def test_an_asof_replay_is_the_first_part_of_the_close_read(srv):
    q = "/api/hold?idx=NIFTY&k=23200&side=PE&role=long&t0=12:20:30&p0=100&qty=65&rows=1"
    full, cut = _get(q, srv), _get(q + "&asof=13:00", srv)
    assert cut["asof"] == "13:00" and cut["now"]["t"] == "13:00"
    assert cut["rows"] == full["rows"][:len(cut["rows"])]
    assert _get(q + "&asof=12:00", srv)["ok"] is False                       # before the entry read


def test_the_logs_are_written_once_from_entry_to_the_close(srv):
    _post("/api/hold/trades", MARK, srv)
    n = server._hold_tick(srv, "NIFTY")
    side = [r for r in _lines("side") if r["kind"] == "minute"]
    trade = [r for r in _lines("hold") if r.get("kind", "minute") == "minute"]
    touches = [r for r in _lines("hold") if r.get("kind") == "rung_touch"]
    assert [r["t"] for r in side] == hold.SESSION                          # one per minute, flat or not
    assert all(r["atm"]["k"] and r["atm"]["k"] % 50 == 0 for r in side if r["t"] >= "09:16")
    assert [r["t"] for r in trade] == [t for t in hold.SESSION if t >= "12:19"]
    assert {r["src"] for r in trade} == {"marked"} and not any(r["after_exit"] for r in trade)
    assert all(r["side_read"]["side"] for r in trade) and trade[0]["entry_verdict"] == trade[0]["unlatched"]
    tracks = [r for r in _lines("side") if r["kind"] == "stamp_track"]
    assert len(tracks) == sum(r["stamp"] for r in side)
    assert all(len(t["stamp_track"]["ce"]) == hold.mm(t["stamp_track"]["to"]) - hold.mm(t["t"]) + 1 for t in tracks)
    assert n == len(side) + len(trade) + len(tracks) + len(touches)
    assert server._hold_tick(srv, "NIFTY") == 0                            # write-once: nothing twice


def test_the_close_time_import_replays_what_she_did_not_mark(srv):
    _post("/api/hold/trades", MARK, srv)
    csv = ("symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,"
           "order_execution_time,expiry_date\n"
           f"NIFTY2692923200PE,,{DAY},NSE,FO,,buy,false,65,100,1,1,{DAY}T12:21:10,2026-09-29\n"      # the marked one
           f"NIFTY2692923200PE,,{DAY},NSE,FO,,sell,false,65,140,2,2,{DAY}T13:05:00,2026-09-29\n"
           f"NIFTY2692923250CE,,{DAY},NSE,FO,,sell,false,65,80,3,3,{DAY}T13:30:05,2026-09-29\n"     # a short, not marked
           f"NIFTY2692923250CE,,{DAY},NSE,FO,,buy,false,65,60,4,4,{DAY}T14:00:00,2026-09-29\n"
           f"NIFTY2692923250CE,,2026-09-23,NSE,FO,,buy,false,65,60,5,5,2026-09-23T10:00:00,2026-09-29\n")
    got = _post("/api/hold/import", csv.encode(), srv)
    assert got["ok"] and got["trips"] == 2 and got["matched_marked"] == 1
    assert got["imported"] == ["NIFTY-23250CE-short-133005"]
    rows = [r for r in _lines("hold") if r["src"] == "import"]
    assert rows[0]["t"] == "13:29" and rows[-1]["t"] == "15:29" and rows[0]["role"] == "short"
    assert [r["after_exit"] for r in rows] == [r["t"] > "13:59" for r in rows]
    again = _post("/api/hold/import", csv.encode(), srv)
    assert again["rows_written"] == {i: 0 for i in again["rows_written"]}   # the same door, write-once
    marked = _get("/api/hold/trades", srv)["trades"][0]
    assert marked["exit_t_broker"] == "13:05:00" and marked["exit_t"] is None   # beside her click, never over it


def test_bad_marks_are_refused_at_the_door(srv):
    for bad in ({**MARK, "op": "buy"}, {**MARK, "t0": "9:20"}, {**MARK, "idx": "FINNIFTY"},
                {**MARK, "side": "XX"}, {**MARK, "k": "abc"}, {"op": "exit", "id": "nope"}):
        got = _post("/api/hold/trades", bad, srv)
        assert got["ok"] is False and got["why"].startswith(board.CC), bad
    tid = _post("/api/hold/trades", MARK, srv)["trades"][0]["id"]
    assert _post("/api/hold/trades", {"op": "exit", "id": tid, "exit_t": "12:00:00"}, srv)["ok"] is False
    out = _post("/api/hold/trades", {"op": "exit", "id": tid, "exit_t": "13:10:00"}, srv)
    assert out["trades"][0]["exit_t"] == "13:10:00"
    assert _get(f"/api/hold?id={tid}", srv)["after_exit"] is True
    assert _post("/api/hold/trades", {"op": "unmark", "id": tid}, srv)["trades"] == []


def test_the_running_peak_is_read_off_the_chain_record_as_it_stood(monkeypatch, tmp_path):
    """§2: the peak as of t, never the day's end -- off the day's record, read once and
    then only what was appended; a half-written last line waits for the next read."""
    import chain_live
    monkeypatch.setattr(chain_live, "CHAIN_DIR", tmp_path)
    monkeypatch.setattr(server, "_HOLD", _fresh())
    p = tmp_path / "chain_NIFTY_2026-09-24.jsonl"

    def snap(ts, ce, pe):
        return json.dumps({"ts": ts, "spot": 23200.0, "strikes": [{"k": 23200, "ce": {"oi": ce}, "pe": {"oi": pe}}]}) + "\n"
    p.write_text(snap("09:15:05", 100, 50) + snap("09:15:40", 300, 40) + snap("09:16:10", 200, 60) + snap("09:14:59", 999, 999))
    got = server._hold_peaks("NIFTY", DAY)
    assert got["09:15"] == {(23200.0, "ce"): 300.0, (23200.0, "pe"): 50.0}      # an intra-minute high is kept
    assert got["09:16"] == {(23200.0, "ce"): 300.0, (23200.0, "pe"): 60.0}      # never the pre-open print
    with open(p, "a", encoding="utf-8") as f:
        f.write(snap("09:17:00", 400, 10) + snap("09:18:00", 500, 10)[:20])     # the poller mid-write
    got = server._hold_peaks("NIFTY", DAY)
    assert got["09:17"][(23200.0, "ce")] == 400.0 and "09:18" not in got
    assert got["09:15"][(23200.0, "ce")] == 300.0                               # the past is never re-decided


def test_the_greeks_are_read_off_the_chain_record_and_carried_forward(monkeypatch, tmp_path):
    """PLAN §2.1: the broker's delta and gamma for her strike-side at the latest snapshot
    at or before each minute [M]; a strike the record never carried reads None."""
    import chain_live
    monkeypatch.setattr(chain_live, "CHAIN_DIR", tmp_path)
    monkeypatch.setattr(server, "_HOLD", _fresh())
    p = tmp_path / "chain_NIFTY_2026-09-24.jsonl"
    leg = lambda oi, dl, g: {"oi": oi, "delta": dl, "gamma": g}                       # noqa: E731
    p.write_text(json.dumps({"ts": "09:15:05", "spot": 23200.0, "strikes": [
        {"k": 23200, "ce": leg(100, 0.52, 0.0014), "pe": leg(90, -0.48, 0.0013)}]}) + "\n"
                 + json.dumps({"ts": "09:17:30", "spot": 23210.0, "strikes": [
        {"k": 23200, "ce": leg(110, 0.55, 0.0015), "pe": leg(95, -0.45, 0.0012)}]}) + "\n")
    server._hold_peaks("NIFTY", DAY)
    assert server._hold_greeks("NIFTY", DAY, 23200, "PE", 4) == [(-0.48, 0.0013), (-0.48, 0.0013),
                                                                (-0.45, 0.0012), (-0.45, 0.0012)]
    assert server._hold_greeks("NIFTY", DAY, 23250, "CE", 2) == [None, None]


def test_the_reply_carries_the_plan_beside_the_window(srv):
    _post("/api/hold/trades", MARK, srv)
    a = _get("/api/hold?id=NIFTY-23200PE-long-122030", srv)
    p = a["plan"]
    assert p["draft"] == plan.DRAFT and p["not_shown"] == plan.NOT_SHOWN_LINES
    assert p["t"] == a["now"]["t"] and p["entry"]["t"] == a["entry"]["t"]
    assert p["stop"]["L"] == a["now"]["line"]["L"] and p["stop"]["risk"] is None       # the test poller has no greeks
    assert p["stop"]["risk_why"] == board.CC + "no greeks for this strike in the chain record"
    assert p["rung"]["src"] in ("wall", "session", "none") and p["exits"]["window"].startswith("the window: ")


def test_rung_touches_are_their_own_write_once_rows(srv):
    _post("/api/hold/trades", MARK, srv)
    server._hold_tick(srv, "NIFTY")
    rows = _lines("hold")
    minute = [r for r in rows if r.get("kind", "minute") == "minute"]
    touch = [r for r in rows if r.get("kind") == "rung_touch"]
    assert all("plan" in r and set(r["plan"]) == {"stop", "rung", "touch"} for r in minute)
    assert [r["t"] for r in touch] == [r["t"] for r in minute if (r["plan"]["touch"] or {}).get("word")]
    assert all(r["next15"]["tag"] == "M" and r["word"] in plan.WORDS for r in touch)
    assert server._hold_tick(srv, "NIFTY") == 0                                         # write-once


# ---------------------------------------------------------------- the pre-trade check (Validate tab)
ZONE = [  # the zone machine's own rows, as trigger_log writes them (trigger rows carry no `kind`)
    {"rule": "zone", "day": DAY, "index": "NIFTY", "t": "12:30", "side": "SELL", "band": "u2", "px": 23250.0,
     "gate": {"legal": True, "why": "CE 23300 still building"}},
    {"rule": "zone", "day": DAY, "index": "NIFTY", "t": "12:57", "kind": "arm", "side": "BUY", "band": "d2",
     "gate": {"legal": False, "why": "PE 23100 gave up its build at 12:40"}},
    {"rule": "zone", "day": DAY, "index": "NIFTY", "t": "13:03", "side": "BUY", "band": "d2", "px": 23120.0,
     "gate": {"legal": True, "why": "PE 23100 still building"}},              # its bar closes at 13:05: not seen at 13:04
    {"rule": "zone", "day": DAY, "index": "SENSEX", "t": "12:00", "side": "BUY", "band": "d2", "gate": {}},
    {"rule": "5c", "day": DAY, "index": "NIFTY", "t": "12:45", "side": "BUY"},
]


@pytest.fixture
def pre(srv, monkeypatch):
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "13:05"))       # mid-session: the latest finished minute is 13:04
    monkeypatch.setattr(server, "_hold_zone_rows", lambda: ZONE)
    monkeypatch.setattr(server, "_hold_lot", lambda idx: 65)
    return srv


def test_the_check_reads_the_trade_as_if_entered_now_and_marks_nothing(pre, tmp_path):
    a = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100", pre)
    assert a["ok"] and a["asof"] == "13:04" and a["entry"]["t"] == "13:04"
    assert a["entry"]["text"].startswith("If you enter now, you enter into")
    assert a["trade"]["qty"] == 65 and a["lot"] == 65 and a["qty_src"] == "1 lot (65)"
    assert a["now"]["t"] == "13:04" and a["plan"]["t"] == "13:04" and a["side"]["agrees"]
    assert a["note"].startswith("a check marks no trade")
    assert _get("/api/hold/trades", pre)["trades"] == []                       # nothing was marked
    assert not (tmp_path / "hold").exists()                                     # nothing was logged


def test_the_check_names_your_setup_from_the_zone_machine(pre):
    z = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100", pre)["zone"]
    assert (z["trigger"]["t"], z["trigger"]["side"], z["trigger"]["legal"], z["trigger"]["agrees"]) == ("12:30", "SELL", True, "agrees")
    assert z["trigger"]["seen"] == "12:32" and z["trigger"]["ago"] == 32 and z["trigger"]["tag"] == "M"
    assert (z["arm"]["t"], z["arm"]["side"], z["arm"]["legal"], z["arm"]["agrees"]) == ("12:57", "BUY", False, "against")
    call = _get("/api/hold/check?idx=NIFTY&k=23200&side=CE&role=long&p0=100", pre)["zone"]
    assert call["trigger"]["agrees"] == "against" and call["arm"]["agrees"] == "agrees"
    none = _get("/api/hold/check?idx=BANKNIFTY&k=55500&side=CE&role=long&p0=100", pre)
    assert none["ok"] is False                                                  # the test poller carries NIFTY only


def test_the_check_refuses_bad_input_and_a_closed_session(pre, monkeypatch):
    for q in ("idx=FINNIFTY&k=1&side=CE&role=long", "idx=NIFTY&k=23200&side=XX&role=long",
              "idx=NIFTY&k=abc&side=CE&role=long"):
        got = _get("/api/hold/check?" + q, pre)
        assert got["ok"] is False and got["why"].startswith(board.CC), q
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "15:45"))
    shut = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100", pre)
    assert shut["ok"] is False and shut["why"].startswith(board.NOT_SHOWN)


def test_a_brief_history_is_the_runs_of_the_word(srv):
    _post("/api/hold/trades", MARK, srv)
    a = _get("/api/hold?id=NIFTY-23200PE-long-122030&rows=brief", srv)
    runs = a["runs"]
    assert runs[0]["from"] == "12:19" and runs[-1]["to"] == "15:29" and a["rows"] is None
    assert all(r["to"] < n["from"] for r, n in zip(runs, runs[1:]))            # contiguous, never overlapping
    assert {r["verdict"] for r in runs} <= {"HOLD", "WATCH", "FOLD", "PATA NAHI"}
    assert all(r["verdict"] != n["verdict"] for r, n in zip(runs, runs[1:]))   # a run ends only when the WORD changes


def test_a_minute_is_not_read_before_its_index_candle_has_landed(pre, fx, monkeypatch):  # noqa: F811
    """Live, 2026-09-25 11:58: Upstox had served index candles to 11:56 while the grid held 11:57,
    so the newest minute's line was blind (PATA NAHI) -- and the write-once log would have kept it.
    The read waits for the candle, at most fronts.STALE_MIN minutes; past that it reads blind."""
    tr = fx["trend"]
    trd = {"m1_prior": tr["m1"][PRIOR[DAY]], "m30": tr["m30"], "d1": tr["d1"]}

    def upto(hhmm):
        return [c for c in tr["m1"][DAY] if str(c[0])[11:16] <= hhmm]
    monkeypatch.setattr(server, "_hold_candles", lambda idx, day, asof: (trd, upto("13:03"), None))
    a = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100", pre)
    assert a["asof"] == "13:03" and a["entry"]["verdict"] != "PATA NAHI"            # waited one minute for 13:04's candle
    server._HOLD["facts"].clear()
    monkeypatch.setattr(server, "_hold_candles", lambda idx, day, asof: (trd, upto("12:59"), None))
    b = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100", pre)
    assert b["asof"] == "13:04" and b["entry"]["verdict"] == "PATA NAHI"            # 5 min behind: stale, read blind, said so
    assert "no NIFTY candle for 13:04" in b["now"]["line"]["blind"]                 # rev 5 §D item 14's words


def test_the_check_carries_the_word_and_a_press_is_logged_once(pre, tmp_path):
    q = "/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100"
    a = _get(q, pre)
    v = a["validate"]
    assert v["word"] in ("GO", "WAIT", "NO") and v["count"].endswith("of 4, a count, not odds") and len(v["facts"]) == 4
    assert not (tmp_path / "hold").exists()                                     # a read without a press logs nothing
    _get(q + "&log=1", pre)
    _get(q + "&log=1", pre)                                                     # the same minute, the same contract: once
    rows = [json.loads(x) for x in open(hold_log.path("check", DAY), encoding="utf-8")]
    assert len(rows) == 1 and rows[0]["word"] == v["word"] and rows[0]["t"] == "13:04"
    assert rows[0]["k"] == 23200 and rows[0]["side"] == "PE" and rows[0]["role"] == "long" and rows[0]["tag"] == "I"
    _get("/api/hold/check?idx=NIFTY&k=23250&side=PE&role=long&p0=100&log=1", pre)   # another strike: its own row
    assert len(open(hold_log.path("check", DAY), encoding="utf-8").readlines()) == 2


# ---------------------------------------------------------------- REVIEW 2026-09-25, the server half
def test_the_trades_carry_the_lot_of_every_index(srv):
    """REVIEW P1-7: the lot size at mount, not with the first answer."""
    import instruments
    assert _get("/api/hold/trades", srv)["lots"] == {i: 65 for i in instruments.ENABLED}


def test_a_double_click_marks_one_trade(srv):
    """REVIEW P1-8: the same open contract within 60 s is refused; past 60 s it is a second trade."""
    _post("/api/hold/trades", MARK, srv)
    assert _post("/api/hold/trades", {**MARK, "t0": "12:21:20"}, srv) == {
        "ok": False, "why": "already marked — NIFTY 23200 PE long in at 12:20:30 is open"}
    assert _post("/api/hold/trades", MARK, srv)["ok"] is False                   # the very same click too
    assert len(_post("/api/hold/trades", {**MARK, "t0": "12:21:31"}, srv)["trades"]) == 2
    assert _post("/api/hold/trades", {**MARK, "t0": "12:20:40", "side": "CE"}, srv)["ok"]   # another contract


def test_i_am_out_defaults_to_now_is_checked_and_can_be_undone(srv, monkeypatch):
    """REVIEW P1-8/P1-9: the exit time is validated and defaults to now; `reopen` undoes an exit
    clicked in the last 120 s, never an older one."""
    real = server.time.strftime
    monkeypatch.setattr(server.time, "strftime", lambda f, *a: "13:10:05" if f == "%H:%M:%S" else real(f, *a))
    tid = _post("/api/hold/trades", MARK, srv)["trades"][0]["id"]
    for bad in ("25:00", "13:61:00", "1310", "12:00:00"):
        got = _post("/api/hold/trades", {"op": "exit", "id": tid, "exit_t": bad}, srv)
        assert got["ok"] is False and got["why"].startswith(board.CC), bad
    tr = _post("/api/hold/trades", {"op": "exit", "id": tid}, srv)["trades"][0]
    assert tr["exit_t"] == "13:10:05" and tr["exit_at"]
    server._HOLD["trades"][0]["exit_t_broker"] = "13:10:00"
    tr = _post("/api/hold/trades", {"op": "reopen", "id": tid}, srv)["trades"][0]
    assert tr["exit_t"] is None and "exit_t_broker" not in tr and "exit_at" not in tr
    assert _post("/api/hold/trades", {"op": "reopen", "id": tid}, srv)["ok"] is False    # nothing to undo
    _post("/api/hold/trades", {"op": "exit", "id": tid, "exit_t": "13:00"}, srv)
    server._HOLD["trades"][0]["exit_at"] -= 121
    got = _post("/api/hold/trades", {"op": "reopen", "id": tid}, srv)
    assert got == {"ok": False, "why": "nothing to undo — no exit in the last 120 s"}
    assert _get("/api/hold/trades", srv)["trades"][0]["exit_t"] == "13:00"


def test_a_post_from_another_site_is_refused(srv):
    """REVIEW §P2 (CSRF): a cross-site POST changes nothing; the Vite proxy's same-origin passes."""
    for path, body in (("/api/hold/trades", MARK), ("/api/hold/import", b"")):
        cap = _Post(path, body, srv, {"Sec-Fetch-Site": "cross-site"})
        server.Handler.do_POST(cap)
        assert cap.status == 403 and cap.sent == {"ok": False, "why": "refused — a POST from another site"}
    assert _get("/api/hold/trades", srv)["trades"] == []
    for i, site in enumerate(("same-origin", "same-site", "none")):
        got = _post("/api/hold/trades", {**MARK, "t0": f"12:2{i}:30", "k": 23200 + 50 * i}, srv, {"Sec-Fetch-Site": site})
        assert got["ok"], site


def test_the_extensions_service_worker_is_let_in_by_its_origin_a_web_page_is_not(srv):
    """2026-09-29: the GoCharting panel marks from sw.js (Origin chrome-extension://<id>, cross-site by nature) --
    the frame door's rule (P1-07). A web origin with cross-site stays refused; no header (curl) passes."""
    ext = {"Sec-Fetch-Site": "cross-site", "Origin": "chrome-extension://abcdefghijklmnopabcdefghijklmnop"}
    assert _post("/api/hold/trades", MARK, srv, ext)["ok"]
    cap = _Post("/api/hold/trades", {**MARK, "k": 23250}, srv, {"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example"})
    server.Handler.do_POST(cap)
    assert cap.status == 403 and cap.sent["why"] == "refused — a POST from another site"
    assert _post("/api/hold/trades", {**MARK, "k": 23300, "t0": "12:25:30"}, srv)["ok"]          # no header at all
    assert [t["k"] for t in _get("/api/hold/trades", srv)["trades"]] == [23200, 23300]


def test_the_check_names_its_absences_by_kind(pre, monkeypatch):
    """REVIEW §P2: an order / size / confidence is withheld by policy (not shown), not a search
    that came back empty; before 09:16 nothing is missing yet; no doc path in her copy."""
    a = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100", pre)
    assert a["absent"]["checked_none"] == board.NOT_SHOWN + "an order, a size or a confidence number — never computed here"
    assert a["absent"]["not_shown"][0] == board.NOT_SHOWN + "the engine's own headline word — it read CONTRADICTED on 09-24"
    assert "§" not in a["note"] and "docs/" not in a["note"]
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "09:15"))
    early = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100", pre)
    assert early == {"ok": False, "idx": "NIFTY", "why": board.NOT_SHOWN + "the first check reads the 09:15 minute, from 09:16"}


def test_the_candle_refetch_runs_outside_the_index_lock(pre, fx, monkeypatch):  # noqa: F811
    """REVIEW P1-18: a late candle's REST re-ask must not hold every read of the index behind it."""
    tr = fx["trend"]
    trd = {"m1_prior": tr["m1"][PRIOR[DAY]], "m30": tr["m30"], "d1": tr["d1"]}
    held = []

    def candles(idx, day, asof):
        lk = server._HOLD["locks"].get(idx)
        held.append(lk is not None and lk.locked())
        return trd, tr["m1"][DAY], None
    monkeypatch.setattr(server, "_hold_candles", candles)
    server._hold_facts(pre, "NIFTY")
    server._HOLD["facts"].clear()
    server._hold_facts(pre, "NIFTY")
    assert held == [False, False]


def _bar(hhmm, cvd):
    from datetime import datetime, timedelta, timezone
    t = datetime.strptime(f"{DAY} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
    return {"t": int(t.timestamp() * 1000), "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "cvd": cvd}


def test_a_bar_or_run_that_lands_after_a_minute_was_read_reaches_it(pre, monkeypatch):
    """REVIEW §P2 (live vs restart): read t, a ladder bar closing at t and a fill run begun before
    it land, read t again -- the live cache now reads that minute as a restart does."""
    bars = [_bar(x, c) for x, c in (("12:30", 10), ("12:35", 40), ("12:40", 20), ("12:45", 90), ("12:50", -30))]
    ux = {"bars": bars[:-1], "marks": {"runs": [], "runs_why": None}, "why": None}
    monkeypatch.setattr(server, "_tape_reply", lambda idx, day: {"ok": True, "ux": ux})
    before = server._hold_facts(pre, "NIFTY")["recs"]["12:55"]
    ux["bars"] = bars                                               # the 12:50 bar closes at 12:55, late
    run = _bar("12:52", 0)["t"]
    ux["marks"]["runs"] = [{"t": run + 2000, "from_t": run, "side": 1, "kind": "run"}]
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "13:06"))   # the next minute's read
    live = server._hold_facts(pre, "NIFTY")["recs"]["12:55"]
    server._HOLD["facts"].clear()                                   # a restart
    fresh = server._hold_facts(pre, "NIFTY")["recs"]["12:55"]
    assert live == fresh and live["cvd"] != before["cvd"] and live["flow"]["b"] == before["flow"]["b"] + 1


def test_a_chain_mark_without_a_spot_reads_blind_and_costs_only_its_minute(srv):
    """Live 2026-09-25: one such mark raised in _hold_rec, and every hold read and log row of
    SENSEX and BANKNIFTY that day went with it."""
    st = srv.states["NIFTY"]
    st.minutes = {**st.minutes, "12:00": {**st.minutes["12:00"], "spot": None}}
    recs = server._hold_facts(srv, "NIFTY")["recs"]
    assert recs["12:00"]["blind"] == board.CC + "no spot on the 12:00 chain mark" and "spot" not in recs["12:00"]
    assert recs["12:01"]["spot"] and recs["11:59"]["spot"]
    assert server._hold_tick(srv, "NIFTY") > 0


# ---------------------------------------------------------------- rev 5 (option B) and VALIDATE rev 2, the server half
def _check_rows():
    return [json.loads(x) for x in open(hold_log.path("check", DAY), encoding="utf-8")]


def test_closes_no_live_read_carried_are_read_from_backfill_and_tagged(srv):
    """rev 5 §A.0.4 (S-b): a first read at 15:45 carries every earlier close off the record, never live -- each
    is read at its own bar, tagged backfill with the minute of that first read, never blended with a live read.
    The logged row carries §G's keys and `prereg`."""
    _post("/api/hold/trades", MARK, srv)
    server._hold_tick(srv, "NIFTY")
    land = server._HOLD["land"]["NIFTY"]
    assert land["late"]["12:23"] == {"read_at": None, "backfill": "15:29"} and "15:29" not in land["late"]
    rows = [r for r in _lines("hold") if r.get("kind", "minute") == "minute"]
    assert {r["prereg"] for r in rows} == {"rev5-B"}
    assert set(rows[0]["line"]) == {"L", "src", "room", "broken_at", "blind", "px", "bar_close", "bar", "read_at",
                                    "backfill", "B", "B_at", "level", "clamped"}
    reads = [r["line"] for r in rows if r["line"]["bar_close"]]
    assert reads and all(x["backfill"] and x["read_at"] is None for x in reads if x["bar"][-5:] < "15:29")
    assert all(r["latch"] is None for r in rows if r["verdict"] != "FOLD")
    assert all(r["latch"]["t"] == r["since"] for r in rows if r["verdict"] == "FOLD")


def test_a_late_close_is_read_when_it_lands_and_a_restart_reads_the_same(pre, fx, monkeypatch):  # noqa: F811
    """rev 5 §A.0.4: 13:02 (the 13:00 bar's close) is read without its candle; when it lands the minute after
    the next read, it is read THEN (read_at), written once into day state with the trade's B reads, and a
    restart re-reads the same window."""
    tr = fx["trend"]
    trd = {"m1_prior": tr["m1"][PRIOR[DAY]], "m30": tr["m30"], "d1": tr["d1"]}
    full = tr["m1"][DAY]
    gap = [c for c in full if str(c[0])[11:16] != "13:02"]
    monkeypatch.setattr(server, "_hold_candles", lambda idx, day, asof: (trd, gap, None))
    _post("/api/hold/trades", MARK, pre)
    server._hold_tick(pre, "NIFTY")                                            # 13:04: 13:02 has no candle
    land = server._HOLD["land"]["NIFTY"]
    assert "13:02" in land["blind"] and "13:02" not in land["late"]
    assert _get("/api/hold?id=NIFTY-23200PE-long-122030", pre)["now"]["line"]["blind"] == \
        board.CC + "the 13:00–13:02 bar's close has not landed"
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "13:08"))
    monkeypatch.setattr(server, "_hold_candles", lambda idx, day, asof: (trd, full, None))
    server._hold_tick(pre, "NIFTY")
    assert land["late"]["13:02"] == {"read_at": "13:07"} and "13:02" not in land["blind"]
    frozen = server._HOLD["frozen_b"]["NIFTY-23200PE-long-122030"]
    assert frozen and all(set(b) == {"L", "L_at", "B", "B_at", "level", "clamped"} for b in frozen)
    a = _get("/api/hold?id=NIFTY-23200PE-long-122030&rows=1", pre)
    row = next(x for x in a["rows"] if x["t"] == "13:07")["line"]
    assert (row["bar_close"], row["bar"], row["read_at"]) == (True, "13:00–13:02", "13:07")
    server._HOLD.clear()                                                       # a restart
    server._HOLD.update(_fresh())
    server._BOARD.clear()
    server._BOARD.update(server._board_fresh())
    server._load_day_state()
    assert server._HOLD["land"]["NIFTY"]["late"]["13:02"] == {"read_at": "13:07"}
    assert server._HOLD["frozen_b"]["NIFTY-23200PE-long-122030"] == frozen
    b = _get("/api/hold?id=NIFTY-23200PE-long-122030&rows=1", pre)
    for k in ("now", "entry", "fold", "rows"):
        assert b[k] == a[k], k


def test_the_check_reads_your_setup_off_the_zone_machine_and_logs_a_rev2_press(pre, monkeypatch):
    """VALIDATE rev 2 §1.1 / §3: the zone machine's own state on the closed 13:00 bar (the 12:57 BUY re-arm, its
    gate illegal) -- not the latest trigger -- and the press row's additive rev 2 keys."""
    bars = [{"t": hold.hm(hold.mm("09:15") + 3 * i), "fut": {"c": 23150.0, "d3": 23080.0, "d2": 23100.0,
                                                          "u2": 23200.0, "u3": 23220.0}} for i in range(125)]
    wait = {"state": "WAITING", "ref_i": None, "candles_left": None, "exit_why": None}
    buy, sell = [dict(wait) for _ in bars], [dict(wait) for _ in bars]
    ref = next(i for i, b in enumerate(bars) if b["t"] == "12:57")
    for i in range(ref, len(bars)):
        buy[i] = {"state": "ARMED", "ref_i": ref, "candles_left": 10 - (i - ref), "exit_why": None}
    monkeypatch.setattr(server, "_hold_machine", lambda payloads, idx: (bars, buy, sell))
    a = _get("/api/hold/check?idx=NIFTY&k=23200&side=PE&role=long&p0=100&log=1", pre)
    s = a["setup"]
    assert (s["bar"], s["side"], s["state"], s["ref_t"], s["candles_left"], s["legal"]) == ("13:00", "BUY", "ARMED", "12:57", 9, False)
    assert a["validate"]["facts"][0]["state"] == "neither" and a["validate"]["facts"][0]["text"].endswith("the other side's fade is refused")
    g = a["room"]
    assert set(g) >= {"line", "noise", "n", "target", "L", "close"} and g["L"] == a["now"]["line"]["L"]
    press = _check_rows()[0]
    assert (press["rev"], press["d"], press["word"]) == ("2", -1, a["validate"]["word"])
    assert [len(f) for f in press["facts"]] == [4, 4, 4, 4] and press["facts"][0][:3] == ["Your setup", "neither", None]
    assert press["setup"] == {"machine": "zone", "state": "ARMED", "band": "d2", "ref_t": "12:57", "candles_left": 9,
                              "legal": False, "why": "PE 23100 gave up its build at 12:40"}
    assert set(press["room"]) == {"line", "noise", "n", "target"} and press["paid"] in (True, False, None)
    assert press["zone_t"] == "12:30" and set(press) >= {"k", "side", "role", "stop", "rung", "entry_verdict", "n_for"}   # rev 1's keys kept


def test_the_outcome_row_is_written_once_per_direction_and_short_after_1459(pre, monkeypatch):
    """VALIDATE rev 2 §3: the per-minute tick writes one outcome row per (idx, t, d) once its 30 minutes are in
    -- a long CE and a long PE at one minute are two rows (the key's outcome branch), strike-shopping is one --
    never twice; a check after 14:59 is scored to 15:29 and flagged short."""
    q = "/api/hold/check?idx=NIFTY&k={}&side={}&role=long&p0=100&log=1"
    for k, side in ((23200, "PE"), (23250, "PE"), (23200, "CE")):
        _get(q.format(k, side), pre)
    server._hold_tick(pre, "NIFTY")                                            # 13:04: the window has not finished
    assert not [r for r in _check_rows() if r.get("kind") == "check_outcome"]
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "13:40"))
    server._hold_tick(pre, "NIFTY")
    out = [r for r in _check_rows() if r.get("kind") == "check_outcome"]
    assert sorted(r["d"] for r in out) == [-1, 1]
    assert all((r["t"], r["to"], r["short"], r["tag"], r["co_timed"], r["opposite_same_minute"]) ==
               ("13:04", "13:34", False, "M", [], True) for r in out)
    assert all(r["first"] in ("target", "stop", "same minute", "neither", "not scored") for r in out)
    assert all(set(r) >= {"target", "stop", "noise", "why", "at", "gaps", "word"} for r in out)
    server._hold_tick(pre, "NIFTY")
    assert len([r for r in _check_rows() if r.get("kind") == "check_outcome"]) == 2        # write-once
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "15:06"))
    _get(q.format(23200, "PE"), pre)
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "15:45"))
    server._hold_tick(pre, "NIFTY")
    late = [r for r in _check_rows() if r.get("kind") == "check_outcome" and r["t"] == "15:05"]
    assert len(late) == 1 and (late[0]["to"], late[0]["short"]) == ("15:29", True)
