"""jarvis_log.py -- the CALL LOG (Jarvis v3 Task 2): one row per index per live frame minute, write-once, its reader, the
self line, the card the faces render, and the server writing it only after a LIVE build of a new minute. Every DIR is
under tmp_path (conftest); the record test reads 29 Oct read-only and is skipped when the day is absent."""
import json
import os
import pathlib
import time

import pytest

import jarvis_log

DAY = "2026-11-02"


def row(t, word, fut, lean=-1, blind=False, idx="NIFTY", **kw):
    return dict({"day": DAY, "idx": idx, "t": t, "word": word, "state": None, "lean": lean, "since": None,
                 "count": {"with": 4, "against": 1, "N": 5}, "fut": fut, "spot": None if fut is None else fut - 43,
                 "blind": blind}, **kw)


TOY = [row("09:50", "PALAT? ▲", 23150.0, 1), row("09:51", "PALAT ▼", 23140.0),          # said, came true 1 min later
       row("09:56", "TREND ▼", 23100.0), row("10:05", "PALAT? ▼", 23050.0),           # said again: never came true
       row("10:06", "TREND ▼", 23020.0), row("10:42", "TREND ▼", 22950.0)]


def test_write_is_once_per_index_minute_and_read_keeps_the_order():
    assert jarvis_log.read(DAY, "NIFTY") == []                                          # absent: no rows, never a raise
    for r in TOY:
        assert jarvis_log.write(DAY, "NIFTY", r) is True
    assert jarvis_log.write(DAY, "NIFTY", dict(TOY[-1], word="HOLD ▼")) is False          # (idx, t) already written
    assert jarvis_log.write(DAY, "SENSEX", row("10:42", "HOLD ▲", 74100.0, 1, idx="SENSEX")) is True
    assert [r["t"] for r in jarvis_log.read(DAY, "NIFTY")] == [r["t"] for r in TOY]
    assert jarvis_log.read(DAY, "NIFTY")[-1]["word"] == "TREND ▼"                      # the first write stands
    assert [r["idx"] for r in jarvis_log.read(DAY, "SENSEX")] == ["SENSEX"]
    jarvis_log._SEEN.clear()                                                            # a restart: the file is the memory
    assert jarvis_log.write(DAY, "NIFTY", TOY[0]) is False


def dense(rows):
    """Each toy row repeated every minute up to the next one (t moved, nothing else): the shape of a real call log."""
    out = []
    for a, b in zip(rows, rows[1:] + [None]):
        m0 = jarvis_log._m(a["t"])
        m1 = jarvis_log._m(b["t"]) if b else m0 + 1
        out += [dict(a, t=f"{m // 60:02d}:{m % 60:02d}") for m in range(m0, m1)]
    return out


def test_self_line_counts_the_word_palat_episodes_and_blind_minutes():
    """The brief's 6-row toy: TREND ▼ from 09:56 at 23,100f, 22,900f now; two PALAT? episodes, one followed by PALAT in 20
    min. `so far` = the RAW signed move, fut now − fut at since (the coordinator's resolution: the arrow already says
    which way is good), so a ▼ word on a 200-point fall reads −200. The toy is filled to one row a minute (a real log's
    shape: I4 reads rows more than 2 min apart as a hole); it starts at 09:20, so the line says `log from 09:20`."""
    toy = dense([row("09:20", "PALAT? ▲", 23180.0, 1), row("09:40", "PALAT ▼", 23150.0),   # said, came true 20 min later
                 row("09:45", "PALAT? ▼", 23160.0), row("09:50", "HOLD ▼", 23120.0),       # said again, never came true
                 row("09:56", "TREND ▼", 23100.0), row("10:30", "TREND ▼", 23000.0)])
    assert jarvis_log.self_line([], 22900.0) is None
    assert jarvis_log.self_line(toy, 22900.0) == (
        "TREND ▼ since 09:56 · −200 so far · PALAT? said 2× · came true 1× · blind 0 min · log from 09:20")
    assert jarvis_log.self_line(toy, 23150.0).split(" · ")[1] == "+50 so far"            # up 50 against a ▼: says so
    two = [row("09:30", "PALAT? ▲", 23180.0, 1), row("09:31", "PALAT? ▲", 23170.0, 1),    # one episode, two rows
           row("09:50", "PALAT ▼", 23120.0)]                                             # 20 min after it was first said
    assert "PALAT? said 1× · came true 1×" in jarvis_log.self_line(two, 23100.0)
    blind = toy + [row("10:31", "CAN'T SEE", None, 0, blind=True), row("10:32", "CAN'T SEE", None, 0, blind=True)]
    assert jarvis_log.self_line(blind, None) == ("CAN'T SEE since 10:31 · so far could not check — no fut price · "
                                                 "PALAT? said 2× · came true 1× · blind 2 min · log from 09:20")
    assert "could not check" in jarvis_log.self_line(toy, None)                           # a missing price is never a zero
    late = [row("09:30", "PALAT? ▲", 23180.0, 1), row("10:16", "PALAT ▼", 23120.0)]        # 46 min later: not "came true"
    assert "came true 0×" in jarvis_log.self_line(late, 23100.0)
    long = [row("09:00", "PALAT? ▲", 23180.0, 1), row("09:40", "PALAT? ▲", 23170.0, 1),   # one 40-min episode, then PALAT
            row("09:50", "PALAT ▼", 23120.0)]                                             # at 50 min from its FIRST minute
    assert "said 1× · came true 0×" in jarvis_log.self_line(long, 23100.0)                # the evening sheet's measure (Task 4)


CALL = {"at": "10:42", "word": "TREND ▼", "state": "HOLD", "lean": -1, "since": "09:56",
        "count": {"with": 4, "against": 1, "N": 6, "unread": 2,
                  "pieces": [{"k": "answer", "side": "with", "text": "last answer 10:38 22,950s PE ±2 BROKEN"}]},
        "why": ["health: every source live", "call: TREND ▼ — the leg"], "wrong_line": "PALAT? if back past 22,938f",
        "up": "▲ if 23,000s (23,043f) CE breaks", "dn": "▼ if 22,900s (22,943f) PE breaks", "buyer": "buy the PE",
        "seller": "sell the CE", "missing": ["BLIND since 10:39: no market data for 3 min (internet or Upstox)",
                                             "Dext footprint missing since 10:39"],
        "leg": "leg ▼ TREND 103 pts", "pause": {"line": "PAUSE ▼ · hold", "alive": ["a"], "risk": ["r"], "notes": ["n"]},
        "lines": {"q35": 22938.0, "half": 22886.0},
        "walls": {"ce": {"k": 23000, "f": 23043.0, "oi": 147.0, "state": "BUILDING"},
                  "pe": {"k": 22900, "f": 22943.0, "oi": 186.0, "state": "BUILDING"}}}


def frame(call=CALL, **kw):
    return dict({"ok": True, "day": DAY, "idx": "NIFTY", "live": True, "asof": "10:42:51", "step": 50,
                 "mins": ["10:41", "10:42"], "fut": [23020.0, 23010.5], "spot": [22977.0, 22967.3],
                 "health": {"notes": ["Dext footprint missing since 10:39"]},
                 "pushes": [{"t": f"10:{i:02d}", "dir": -1, "lots": -600, "k": 22950, "side": "PE", "ans": "TOOT",
                             "held_at": "10:41", "via": "band", "norm": 3.1} for i in range(8)],
                 "call": call}, **kw)


def test_the_row_carries_the_contract_and_marks_a_blind_minute():
    r = jarvis_log.row(frame(), 1793596371.4)
    assert r == {"day": DAY, "idx": "NIFTY", "t": "10:42", "at": 1793596371, "shown": "10:42:51", "word": "TREND ▼",
                 "state": "HOLD", "lean": -1, "since": "09:56",
                 "count": {"with": 4, "against": 1, "N": 6, "flat": None, "blind": None, "pieces": {"answer": "with"}},
                 "fut": 23010.5, "spot": 22967.3, "leg": "leg ▼ TREND 103 pts", "wrong_line": "PALAT? if back past 22,938f",
                 "missing": CALL["missing"], "notes": ["Dext footprint missing since 10:39"], "blind": True,
                 "action": None, "vol": None}
    old = {k: v for k, v in CALL.items() if k not in ("state", "since", "count")}          # a frame from before Task 1
    r = jarvis_log.row(frame(old), 1.0)
    assert r["state"] is None and r["since"] is None and r["count"] is None               # absent is null, never invented


def test_the_card_is_the_contract_from_the_frame_only_and_absent_keys_are_null():
    c = jarvis_log.card(frame(), TOY, {"watches": [{"id": 1, "level": 22800.0, "frame": "s", "set": "10:12", "hit": None}],
                                       "lines": [], "zones": []}, ["note 10:05 RBI 11:00 today"])
    assert (c["ok"], c["idx"], c["day"], c["at"], c["asof"], c["live"]) == (True, "NIFTY", DAY, "10:42", "10:42:51", True)
    assert (c["word"], c["state"], c["lean"], c["since"]) == ("TREND ▼", "HOLD", -1, "09:56")
    assert c["count"] == CALL["count"] and c["leg"] == CALL["leg"] and c["wrong_line"] == CALL["wrong_line"]
    assert c["pause"] == {"line": "PAUSE ▼ · hold", "alive": ["a"], "risk": ["r"]}
    assert c["expression"] == {"buyer": "buy the PE", "seller": "sell the CE", "pick": None}
    for k in ("how_much", "where", "cross", "her_setup", "expiry", "bada", "no_trade", "voice", "brief"):
        assert c[k] is None, k                                                           # absent in the frame: null
    t5 = {"how_much": {"line": "day TREND ▼ · range used 0.5 of EM", "rows": []},
          "where": {"stop": "23,136f (zone)", "pool": None, "t1": "pVAH 23,058f", "t2": None, "room": "44 to MAX PAIN"},
          "expression": {"buyer": "buy the PE", "seller": "sell the CE", "pick": "seller", "pick_why": "TREND + Sides REAL",
                         "in_trade": None},
          "cross": {"read": "THE READ ▼ TREND 10:40", "decode": None, "board": None}, "her_setup": ["10:21 ZONE SELL"],
          "expiry": {"dte": 0, "mode": "EXPIRY DAY"}, "bada": "BADA PRINT: none at a wall in 15 min"}
    full = jarvis_log.card(frame(dict(CALL, **t5)), [], None, [])
    assert {k: full[k] for k in t5} == t5                                                # Task 5's keys, verbatim
    assert c["health"] == {"missing": ["BLIND since 10:39: no market data for 3 min (internet or Upstox)"],
                           "notes": ["Dext footprint missing since 10:39", "note 10:05 RBI 11:00 today"], "method": []}
    assert c["self"] == jarvis_log.self_line(TOY, 23010.5)

    assert len(c["pushes"]) == 5 and set(c["pushes"][0]) == {"t", "dir", "lots", "k", "side", "ans", "held_at", "via"}
    assert c["watches"][0]["level"] == 22800.0 and c["walls"] == CALL["walls"] and c["lines"] == CALL["lines"]
    assert "%" not in json.dumps(c, ensure_ascii=False)
    assert jarvis_log.answer(frame()) == "last answer 10:38 22,950s PE ±2 BROKEN"         # the count's own piece
    bf = frame({"at": "10:42", "word": "HOLD ▼", "lean": -1,
                "why": ["writers: ±7 UP · wall below 22,900s (22,943f) PE 186L building · last answer 10:07 22,950s PE ±2 TOOT"]})
    bare = jarvis_log.card(bf, [], None, [])
    assert bare["count"] is None and bare["state"] is None and bare["self"] is None and bare["watches"] == []
    assert jarvis_log.answer(bf) == "last answer 10:07 22,950s PE ±2 TOOT"              # no count yet: the why's clause, verbatim
    assert jarvis_log.answer(frame({"at": "10:42", "word": "HOLD ▼"})) is None
    assert jarvis_log.card({"ok": False, "why": "could not check — no minute yet"}, [], None, []) == \
        {"ok": False, "why": "could not check — no minute yet"}


DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _has(day):
    return any(os.path.exists(os.path.join(DATA, "book", f"book_NIFTY_{day}.jsonl{z}")) for z in ("", ".gz"))


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_the_card_of_a_real_29_oct_frame_is_under_10_kb(monkeypatch):
    import book_log
    import chain_backfill
    import chain_live
    import dext_log
    import jarvis
    import trigger_log
    monkeypatch.setattr(book_log, "DIR", os.path.join(DATA, "book"))                     # the real record, read-only
    monkeypatch.setattr(dext_log, "DIR", os.path.join(DATA, "dext"))
    monkeypatch.setattr(chain_backfill, "DIR", os.path.join(DATA, "chain_backfill"))
    monkeypatch.setattr(chain_live, "CHAIN_DIR", pathlib.Path(DATA, "chain"))
    monkeypatch.setattr(trigger_log, "PATH", os.path.join(DATA, "trigger_log.jsonl"))
    monkeypatch.setattr(jarvis, "MSG_DIR", os.path.join(DATA, "messages"))
    fr = dict(jarvis.build("2026-10-29", "NIFTY", 11 * 60), live=True, asof="11:00:30")
    c = jarvis_log.card(fr, [jarvis_log.row(fr, 1.0)], {"watches": [], "lines": [], "zones": []}, [])
    assert c["ok"] and c["word"] and len(json.dumps(c, default=str)) <= 10 * 1024
    assert "%" not in json.dumps(c, ensure_ascii=False, default=str)


# ---- the server writes it: a LIVE build of a new minute only ---------------------------------------------------------

def test_the_server_logs_a_live_build_once_per_minute_never_a_cache_hit_or_a_replay(monkeypatch):
    from datetime import datetime
    import jarvis
    import server
    from chain_live import IST
    clock = {"now": datetime(2026, 11, 2, 10, 43, 10, tzinfo=IST)}                       # a Monday in the session
    monkeypatch.setattr(server, "_ist", lambda now=None: clock["now"])
    monkeypatch.setattr(server, "_JARVIS", {})
    monkeypatch.setattr(server, "_LAST_LOGGED", {})
    built = []

    def fake(day, idx, upto, fill=False):
        built.append(upto)
        u = 15 * 60 + 41 if upto is None else upto                                       # None: the whole session so far
        t = f"{(u - 1) // 60:02d}:{(u - 1) % 60:02d}"                                    # minutes < upto
        return dict(frame(), day=day, idx=idx, mins=[t], call=dict(CALL, at=t))
    monkeypatch.setattr(jarvis, "build", fake)
    monkeypatch.setattr(jarvis, "calls", lambda d: [])
    q = {"idx": ["NIFTY"]}
    server._jarvis_reply(q)
    server._jarvis_reply(q)                                                               # a cache hit: no build, no row
    assert built == [10 * 60 + 42] and [r["t"] for r in jarvis_log.read(DAY, "NIFTY")] == ["10:41"]
    monkeypatch.setattr(server, "JARVIS_TTL_S", 0)
    server._jarvis_reply(q)                                                               # rebuilt, the same minute: no row
    clock["now"] = datetime(2026, 11, 2, 10, 44, 25, tzinfo=IST)
    server._jarvis_reply(q)                                                               # a new minute: one row
    server._jarvis_reply({"idx": ["NIFTY"], "upto": ["10:30"]})                           # a replay of today: never logged
    filled = server._jarvis_reply({"idx": ["NIFTY"], "fill": ["1"]})                      # the page's fill=1 on today
    assert filled["live"] is False and built[-1] is None                                  # a replay, in the replay slot
    assert [r["t"] for r in jarvis_log.read(DAY, "NIFTY")] == ["10:41", "10:43"]
    assert server._JARVIS["NIFTY"][2]["live"] is True                                     # a replay never evicts the live frame


# ---- the JARVIS PASS: the card and the log stay live with no face polling /api/jarvis -------------------------------

def test_the_jarvis_pass_keeps_nifty_and_sensex_live_without_any_face(monkeypatch):
    """Monday's faces poll /api/jarvis/card, which never builds. The message loop's pass rebuilds the LIVE frame once a
    minute for NIFTY and SENSEX (BANKNIFTY on demand) through _jarvis_reply when the live slot is over 40 s old, writes the
    call log as a poll would, skips while another build holds the lock, says when it is slow, and rests outside 09:15-15:45."""
    import threading
    from datetime import datetime
    import jarvis
    import server
    from chain_live import IST
    from test_senses_api import _Cap
    clock = {"now": datetime(2026, 11, 2, 10, 43, 10, tzinfo=IST)}
    monkeypatch.setattr(server, "_ist", lambda now=None: clock["now"])
    monkeypatch.setattr(server, "_JARVIS", {})
    monkeypatch.setattr(server, "_LAST_LOGGED", {})
    monkeypatch.setattr(server, "_JPASS", {"m": {}, "s": None, "at": None, "slow": None, "skipped": None, "last": None})
    monkeypatch.setattr(server, "_JCMD", {})
    built = []

    def fake(day, idx, upto, fill=False):
        built.append((idx, upto))
        t = f"{(upto - 1) // 60:02d}:{(upto - 1) % 60:02d}"
        return dict(frame(), day=day, idx=idx, mins=[t], call=dict(CALL, at=t, word="TREND ▼" if upto < 644 else "HOLD ▼"))
    monkeypatch.setattr(jarvis, "build", fake)

    def card(idx="NIFTY"):
        cap = _Cap(f"/api/jarvis/card?idx={idx}")
        server.Handler.do_GET(cap)
        return cap.sent

    def age(s=60):
        for k, (key, at_, fr) in list(server._JARVIS.items()):
            server._JARVIS[k] = (key, at_ - s, fr)
    server._jarvis_pass()
    assert built == [("NIFTY", 642), ("SENSEX", 642)]                                     # never BANKNIFTY
    assert [r["t"] for r in jarvis_log.read(DAY, "NIFTY")] == ["10:41"] and card()["word"] == "TREND ▼"
    age()
    server._jarvis_pass()                                                                 # the same minute: no rebuild
    assert len(built) == 2
    clock["now"] = datetime(2026, 11, 2, 10, 44, 25, tzinfo=IST)
    key, _, fr = server._JARVIS["NIFTY"]
    server._JARVIS["NIFTY"] = (key, time.time(), fr)                                     # a face has just polled
    server._jarvis_pass()
    assert built[2:] == [("SENSEX", 644)]                                                 # a fresh live slot is not rebuilt
    age()
    clock["now"] = datetime(2026, 11, 2, 10, 45, 25, tzinfo=IST)
    held, go = threading.Event(), threading.Event()

    def builder():                                                                        # a replay build holds the lock
        with server._JARVIS_LOCK:
            held.set()
            go.wait(5)
    th = threading.Thread(target=builder)
    th.start()
    held.wait(5)
    server._jarvis_pass()
    go.set()
    th.join()
    assert len(built) == 3                                                                # never stacked behind a build
    assert server._JPASS["skipped"] == "jarvis pass skipped 10:45 (lock held)"           # a minute it could not build
    assert server._JPASS["skipped"] in card()["health"]["notes"]
    monkeypatch.setattr(server, "JARVIS_SLOW_S", -1)
    server._jarvis_pass()
    assert built[3:] == [("NIFTY", 645), ("SENSEX", 645)]
    assert [r["t"] for r in jarvis_log.read(DAY, "NIFTY")] == ["10:41", "10:44"] and card()["word"] == "HOLD ▼"
    slow = server._JPASS["slow"]
    assert slow.startswith("Jarvis pass took") and slow in card()["health"]["notes"]
    assert server._JPASS["skipped"] not in card()["health"]["notes"]                     # the last pass built: no skip note
    cap = _Cap("/api/health")
    server.Handler.do_GET(cap)
    assert cap.sent["jarvis_pass"]["slow"] == slow and card()["voice"] is None            # Task 7's seam: _VOICE
    age()
    clock["now"] = datetime(2026, 11, 2, 16, 0, 0, tzinfo=IST)
    server._jarvis_pass()                                                                 # after the close it rests
    assert len(built) == 5



def test_the_jarvis_pass_runs_on_its_own_thread_never_inside_the_message_pass():
    import inspect
    import server
    assert "_jarvis_pass" not in inspect.getsource(server._msg_loop)                      # a 10 s build never delays FLOW
    assert "_jarvis_pass()" in inspect.getsource(server._jarvis_loop)
    assert "target=_jarvis_loop" in inspect.getsource(server.main)


# ---- I1 (final review): the card never serves an old or frozen frame as live ----------------------------------------

def _srv(monkeypatch, now):
    from datetime import datetime
    import server
    from chain_live import IST
    clock = {"now": datetime(*now, tzinfo=IST)}
    monkeypatch.setattr(server, "_ist", lambda now=None: clock["now"])
    monkeypatch.setattr(server, "_JARVIS", {})
    monkeypatch.setattr(server, "_LAST_LOGGED", {})
    monkeypatch.setattr(server, "_JPASS", {"m": {}, "s": None, "at": None, "slow": None, "skipped": None, "last": None})
    monkeypatch.setattr(server, "_JCMD", {})
    monkeypatch.setattr(server, "_JVOICE", {})
    return server, clock


def test_the_card_never_serves_another_days_frame_or_an_old_one_as_live(monkeypatch):
    from datetime import datetime
    from chain_live import IST
    server, clock = _srv(monkeypatch, (2026, 11, 2, 10, 43, 10))
    key = ("NIFTY", DAY, None, False)
    server._JARVIS["NIFTY"] = (key, time.time(), frame(day="2026-10-30", asof="15:44:50"))     # left running overnight
    c = server._jarvis_card("NIFTY")
    why = "could not check — last frame is from 2026-10-30"
    assert c == {"ok": False, "live": False, "why": why, "stale": why}                       # never yesterday's word
    r = server._jarvis_cmd("NIFTY", "why", "page")
    assert not r["ok"] and r["reply"] == why                                                 # the commands read the same guard
    server._JARVIS["NIFTY"] = (key, time.time() - 7 * 60 - 5, frame(asof="10:36:05"))          # frozen: no build for 7 min
    c = server._jarvis_card("NIFTY")
    assert c["ok"] is False and c["live"] is False and c["stale"] == "could not check — last frame 10:36, 7 min old"
    assert "word" not in c and "count" not in c                                              # nothing invented
    r = server._jarvis_cmd("NIFTY", "watch 22800s", "page")
    assert r["ok"] and jarvis_cmd_rows()[-1]["px0"] is None                                  # an old price is never the reference
    clock["now"] = datetime(2026, 11, 2, 16, 0, 0, tzinfo=IST)                               # after the close the day's last frame
    assert server._jarvis_card("NIFTY")["ok"] is True                                        # stands (today's, the pass rests)
    clock["now"] = datetime(2026, 11, 2, 10, 43, 10, tzinfo=IST)
    server._JARVIS["NIFTY"] = (key, time.time() - 30, frame())
    c = server._jarvis_card("NIFTY")
    assert c["ok"] and c["live"] is True and "stale" not in c


def jarvis_cmd_rows():
    import jarvis_cmd
    return jarvis_cmd.rows(DAY)


def test_a_build_that_raises_is_said_on_the_card_until_one_succeeds_and_never_stops_the_pass(monkeypatch):
    from datetime import datetime
    import jarvis
    from chain_live import IST
    server, clock = _srv(monkeypatch, (2026, 11, 2, 10, 43, 10))
    bad = {"on": True}

    def fake(day, idx, upto, fill=False):
        if idx == "NIFTY" and bad["on"]:
            raise KeyError("pieces")
        t = f"{(upto - 1) // 60:02d}:{(upto - 1) % 60:02d}"
        return dict(frame(), day=day, idx=idx, mins=[t], call=dict(CALL, at=t))
    monkeypatch.setattr(jarvis, "build", fake)
    good = dict(frame(), asof="10:42:20")
    server._JARVIS["NIFTY"] = (("NIFTY", DAY, None, False), time.time() - 60, good)          # the 10:42 build was the last good one
    server._jarvis_pass()                                                                    # never raises
    note = "could not check — the last build failed at 10:43: KeyError"
    assert server._JPASS["last"] == "failed" and server._JPASS["failed"] == {"NIFTY": note}
    c = server._jarvis_card("NIFTY")
    assert c["ok"] and note in c["health"]["notes"]                                          # a minute old: shown, and said
    assert note not in server._jarvis_card("SENSEX")["health"]["notes"]                      # SENSEX built
    clock["now"] = datetime(2026, 11, 2, 10, 46, 10, tzinfo=IST)
    key, _, fr = server._JARVIS["NIFTY"]
    server._JARVIS["NIFTY"] = (key, time.time() - 4 * 60, fr)
    server._jarvis_pass()
    c = server._jarvis_card("NIFTY")
    assert c == {"ok": False, "live": False, "why": c["stale"],
                 "stale": "could not check — last frame 10:42, 4 min old · the last build failed at 10:46: KeyError"}
    bad["on"] = False
    clock["now"] = datetime(2026, 11, 2, 10, 47, 10, tzinfo=IST)
    server._jarvis_pass()
    c = server._jarvis_card("NIFTY")
    assert c["ok"] and c["live"] and not any("failed" in n for n in c["health"]["notes"])
    assert server._JPASS["last"] == "ok" and server._JPASS["failed"] == {}


def test_a_torn_byte_and_a_malformed_row_cost_themselves_never_the_card_the_commands_or_the_sheet(monkeypatch):
    """I3 (final review): one row cut inside `▼` and one malformed row between two good rows, in the call log AND the
    command log -> the card, its self line, the commands, the watch rebuild, the call log's write-once seed and the evening
    sheet all still work, and the good rows are read."""
    import sys
    import jarvis_cmd
    server, _ = _srv(monkeypatch, (2026, 11, 2, 10, 43, 10))
    torn, bad = b'{"day": "2026-11-02", "idx": "NIFTY", "t": "10:01", "word": "TREND \xe2\x96\n', b'{"idx": "NIFTY", "t"\n'
    os.makedirs(jarvis_log.DIR, exist_ok=True)

    def line(r):
        return (json.dumps(r, ensure_ascii=False) + "\n").encode()
    with open(jarvis_log._path(DAY), "wb") as f:
        f.write(line(row("10:00", "TREND ▼", 23100.0)) + torn + bad + line(row("10:02", "TREND ▼", 23050.0)))
    with open(os.path.join(jarvis_cmd.DIR, f"cmd_{DAY}.jsonl"), "wb") as f:
        f.write(line({"at": 1, "t": "10:00:05", "idx": "NIFTY", "kind": "watch", "text": "watch 22800s", "ok": True,
                      "reply": "watching 22,800s (1 of 10 today)", "src": "page", "id": 1, "px0": 22830.0})
                + b'{"at": 2, "t": "10:01:00", "idx": "NIFTY", "kind": "note", "text": "note RBI \xe2\x96\n' + bad
                + line({"at": 3, "t": "10:02:00", "idx": "NIFTY", "kind": "line", "text": "line 22750f", "ok": True,
                        "reply": "line 22,750f drawn", "src": "page", "id": 1}))
    assert [r["t"] for r in jarvis_log.read(DAY, "NIFTY")] == ["10:00", "10:02"]
    assert jarvis_log.self_line(jarvis_log.read(DAY, "NIFTY"), 23000.0).startswith("TREND ▼ since 10:00 · −100 so far")
    assert jarvis_log.write(DAY, "NIFTY", row("10:03", "TREND ▼", 23040.0)) is True          # the seed reads past the tear
    server._JARVIS["NIFTY"] = (("NIFTY", DAY, None, False), time.time(), frame())
    c = server._jarvis_card("NIFTY")
    assert c["ok"] and c["self"].startswith("TREND ▼ since 10:00") and c["watches"][0]["level"] == 22800.0
    st = server._jarvis_cmd("NIFTY", "list", "page")
    assert st["ok"] and st["lines"] == ["line 22,750f · set 10:02", "watch 22,800s · set 10:00"]
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import jarvis_review
    sheet = jarvis_review.sheet(DAY, data_dir=jarvis_log.DIR)
    assert "watches set 1 · hit 0" in sheet and "NIFTY · word changes: 0" in sheet


def _mins(a, b, word, fut0, step=-1.0):
    """One row a minute from a to b (HH:MM, inclusive), fut moving `step` a minute: a real log's shape."""
    m0, m1 = int(a[:2]) * 60 + int(a[3:]), int(b[:2]) * 60 + int(b[3:])
    return [row(f"{m // 60:02d}:{m % 60:02d}", word, fut0 + step * (m - m0)) for m in range(m0, m1 + 1)]


def test_the_self_line_never_walks_across_a_log_gap_and_names_a_late_start():
    """I4 (final review): a restart or a late start leaves the call log with holes. `since` / `so far` start after the last
    hole of more than 2 min (never joined across it as if continuous), the hole is named, and a log that starts after
    09:16 says so (its counts cover only what is on disk). PALAT? said / came true keep their rule."""
    rows = _mins("10:00", "10:05", "TREND ▼", 23100.0) + _mins("10:30", "10:35", "TREND ▼", 23040.0)
    assert jarvis_log.self_line(rows, 23000.0) == (
        "TREND ▼ since 10:30 · −40 so far · PALAT? said 0× · came true 0× · blind 0 min · log from 10:00 · "
        "log gap 10:06–10:29")
    late = _mins("11:06", "11:20", "TREND ▼", 23000.0)                                    # started 11:07, the word since 09:56
    assert jarvis_log.self_line(late, 22980.0).endswith("· log from 11:06")
    full = _mins("09:15", "10:00", "TREND ▼", 23100.0)
    assert "log" not in jarvis_log.self_line(full, 23000.0)                                # a whole morning: nothing to say
    hiccup = _mins("09:15", "09:40", "TREND ▼", 23100.0)
    hiccup = hiccup[:10] + hiccup[11:]                                                     # one skipped pass (2 min apart)
    assert jarvis_log.self_line(hiccup, 23000.0).startswith("TREND ▼ since 09:15 · −100 so far")
    assert "gap" not in jarvis_log.self_line(hiccup, 23000.0)
    word = _mins("09:15", "09:30", "HOLD ▼", 23100.0) + _mins("09:50", "09:55", "TREND ▼", 23080.0)
    assert jarvis_log.self_line(word, 23070.0).endswith("· log gap 09:31–09:49")           # a word that changed unseen too


def test_the_card_carries_how_a_number_was_made_apart_from_the_gaps():
    """Task 6 / fixes B: health.method (chain ends 15:30 (scheduled), re-read from HH:MM, thresholds file unreadable) is
    how a number was made, never a gap: the card carries it beside notes so the CLI and the faces can show it."""
    fr = frame(health={"notes": ["Dext footprint missing since 10:39"], "method": ["chain ends 15:30 (scheduled)"]})
    c = jarvis_log.card(fr)
    assert c["health"]["method"] == ["chain ends 15:30 (scheduled)"]
    assert "chain ends 15:30 (scheduled)" not in c["health"]["notes"] + c["health"]["missing"]
