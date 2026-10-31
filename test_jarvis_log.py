"""jarvis_log.py -- the CALL LOG (Jarvis v3 Task 2): one row per index per live frame minute, write-once, its reader, the
self line, the card the faces render, and the server writing it only after a LIVE build of a new minute. Every DIR is
under tmp_path (conftest); the record test reads 29 Oct read-only and is skipped when the day is absent."""
import json
import os
import pathlib

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


def test_self_line_counts_the_word_palat_episodes_and_blind_minutes():
    """The brief's 6-row toy: TREND ▼ from 09:56 at 23,100f, 22,900f now; two PALAT? episodes, one followed by PALAT in 20
    min. `so far` = lean × (fut now − fut at since): a ▼ word on a 200-point fall has EARNED 200, so +200 -- the contract's
    example string printed −200, which its own formula contradicts (named in the task report)."""
    toy = [row("09:20", "PALAT? ▲", 23180.0, 1), row("09:40", "PALAT ▼", 23150.0),        # said, came true 20 min later
           row("09:45", "PALAT? ▼", 23160.0), row("09:50", "HOLD ▼", 23120.0),            # said again, never came true
           row("09:56", "TREND ▼", 23100.0), row("10:30", "TREND ▼", 23000.0)]
    assert jarvis_log.self_line([], 22900.0) is None
    assert jarvis_log.self_line(toy, 22900.0) == (
        "TREND ▼ since 09:56 · +200 so far · PALAT? said 2× · came true 1× · blind 0 min")
    assert jarvis_log.self_line(toy, 23150.0).split(" · ")[1] == "−50 so far"            # wrong by 50: says so
    two = [row("09:30", "PALAT? ▲", 23180.0, 1), row("09:31", "PALAT? ▲", 23170.0, 1),    # one episode, two rows
           row("09:50", "PALAT ▼", 23120.0)]                                             # 20 min after it was first said
    assert "PALAT? said 1× · came true 1×" in jarvis_log.self_line(two, 23100.0)
    blind = toy + [row("10:31", "CAN'T SEE", None, 0, blind=True), row("10:32", "CAN'T SEE", None, 0, blind=True)]
    assert jarvis_log.self_line(blind, None) == "CAN'T SEE since 10:31 · no lean · PALAT? said 2× · came true 1× · blind 2 min"
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
                 "state": "HOLD", "lean": -1, "since": "09:56", "count": {"with": 4, "against": 1, "N": 6},
                 "fut": 23010.5, "spot": 22967.3, "leg": "leg ▼ TREND 103 pts", "wrong_line": "PALAT? if back past 22,938f",
                 "missing": CALL["missing"], "notes": ["Dext footprint missing since 10:39"], "blind": True}
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
    assert c["how_much"] is None and c["where"] is None and c["no_trade"] is None and c["voice"] is None   # Tasks 5 / 7
    assert c["health"] == {"missing": ["BLIND since 10:39: no market data for 3 min (internet or Upstox)"],
                           "notes": ["Dext footprint missing since 10:39", "note 10:05 RBI 11:00 today"]}
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
        t = f"{(upto - 1) // 60:02d}:{(upto - 1) % 60:02d}"                                # minutes < upto
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
    assert [r["t"] for r in jarvis_log.read(DAY, "NIFTY")] == ["10:41", "10:43"]
    assert server._JARVIS["NIFTY"][2]["live"] is True                                     # a replay never evicts the live frame
