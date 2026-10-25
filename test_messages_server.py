"""THE MESSAGE STREAM's server half (server._msg_*): the pass writes each message once, a restart rebuilds the same stream,
the voice's turn is one TRADE line even across a restart, a weekend writes nothing, and GET /api/messages serves NOW + the
lines after ?since=. Every writer is under tmp_path (conftest STR_PATHS); the clock is handed in."""
import json
import os
import time
from datetime import datetime

import pytest

import server
from chain_live import IST
from test_senses_api import _Cap

DAY = "2026-10-23"                                             # a Friday
OK = {"ok": True, "missing": [], "text": None}
READ = [{"kind": "mark", "idx": "NIFTY", "t": "09:50", "word": "WAIT", "dir": 0},
        {"kind": "mark", "idx": "NIFTY", "t": "09:55", "word": "LEAN", "dir": -1, "flip": 22800.0, "since": "09:55"},
        {"kind": "event", "idx": "NIFTY", "t": "09:55", "event": "FORM", "dir": -1, "text": "LEAN ▼ bana · FLIP 22,800",
         "en": "the read formed"}]
DECODE = [{"idx": "NIFTY", "T": "09:55", "call": {"text": "▼ leg jaari · 5/7", "kind": "JAARI", "d": 1, "c": 5, "of": 7,
                                                  "signs": ["CVD leg low pe"]},
           "leg": {"d": -1, "ext": {"t": "09:50", "fut": 22790.0, "spot": 22740.0}}, "setups": [],
           "onesided": {"type": "MIXED"}}]


def at(h, m, s=0, day=DAY):
    y, mo, d = (int(x) for x in day.split("-"))
    return datetime(y, mo, d, h, m, s, tzinfo=IST).timestamp()


def _put(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def _disk(day=DAY):
    p = os.path.join(server.MSG_DIR, f"msg_{day}.jsonl")
    return [json.loads(x) for x in open(p, encoding="utf-8")] if os.path.exists(p) else []


@pytest.fixture(autouse=True)
def _day(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "READ_DIR", str(tmp_path / "read"))
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    monkeypatch.setattr(server, "_recording", lambda now=None: OK)
    for day in (DAY, "2026-10-24"):
        _put(os.path.join(server.READ_DIR, f"read_{day}.jsonl"), READ)
        _put(os.path.join(server.DECODE_DIR, f"decode_{day}.jsonl"), DECODE)


def test_the_pass_writes_each_message_once_and_a_restart_rebuilds_the_same_stream(monkeypatch):
    server._msg_pass(at(10, 7))
    rows = _disk()
    assert [r["line"] for r in rows] == ["09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s",
                                         "09:55  NIFTY  ▼ leg jaari · 5/7 saath", "09:55  NIFTY  din MIXED · ▼5/7",
                                         "10:07  HEALTH  TapeMap live · recording ok"]
    assert {r["at"] for r in rows} == {round(at(10, 7), 3)}
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())          # a restart: memory gone, the record stays
    server._msg_pass(at(10, 8))
    assert _disk() == rows
    rep = server._msg_reply(0)
    assert [m["key"] for m in rep["msgs"]] == [r["key"] for r in rows] and rep["asof"] == "10:08:00"
    assert [r["line"] for r in rep["now"]] == ["NIFTY  LEAN ▼ · 5/7 saath · since 09:55", "BANKNIFTY  read abhi nahi",
                                               "SENSEX  read abhi nahi"]
    assert server._msg_reply(at(10, 7))["msgs"] == []


def test_the_route_serves_now_and_the_lines_after_since():
    cap = _Cap("/api/messages?since=0")
    server.Handler.do_GET(cap)
    assert cap.sent["ok"] is False and cap.sent["why"].startswith("could not check")    # before the first pass
    server._msg_pass(at(10, 7))
    for path in ("/api/messages?since=0", "/api/messages?since=abc", "/api/messages"):
        cap = _Cap(path)
        server.Handler.do_GET(cap)
        assert cap.sent["ok"] is True and len(cap.sent["msgs"]) == 4 and len(cap.sent["now"]) == 3
    cap = _Cap(f"/api/messages?since={at(10, 7)}")
    server.Handler.do_GET(cap)
    assert cap.sent["msgs"] == []


def test_a_voice_turn_is_one_trade_line_even_across_a_restart(monkeypatch):
    tr = {"id": "t1", "idx": "NIFTY"}
    v = {"ok": True, "state": "WARN", "d": -1, "trig_t": "11:07", "stop_f": 22780.0,
         "reason": "CE front gave up @ 22,780f · line 22,780f (HOLD v2)"}
    server._msg_voice(tr, v, at(11, 7, 30))
    server._msg_voice(tr, v, at(11, 7, 40))                              # every face's poll: still one line
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    server._msg_voice(tr, v, at(11, 8))                                  # a restart while it is still WARN
    server._msg_voice(tr, dict(v, state="HOLD"), at(11, 20))             # HOLD is quiet
    server._msg_voice(tr, dict(v, trig_t="11:30"), at(11, 30, 10))       # a new WARN
    assert [r["line"] for r in _disk()] == ["11:07  TRADE  WARN · CE front gave up @ 22,780f · 5/7 saath · stop 22,780f",
                                            "11:30  TRADE  WARN · CE front gave up @ 22,780f · 5/7 saath · stop 22,780f"]


def test_a_weekend_writes_nothing():
    """24 Oct is a Saturday: a stray DECODE row (the server ran on 25 Oct and logged SAAF_NAHI rows) is not a session."""
    server._msg_pass(at(10, 7, day="2026-10-24"))
    assert _disk("2026-10-24") == []
    rep = server._msg_reply(0)
    assert rep["ok"] is True and rep["msgs"] == [] and rep["now"][0]["line"].startswith("NIFTY  LEAN ▼")


def test_new_lines_reach_the_telegram_queue_once(monkeypatch):
    """server._msg_write hands every NEW message to telegram_out.offer; its subset and freshness gate pick the two that go."""
    import queue
    import telegram_out
    monkeypatch.setattr(telegram_out, "_ON", True)
    monkeypatch.setattr(telegram_out, "_Q", queue.SimpleQueue())
    monkeypatch.setattr(telegram_out, "_SENT", set())
    server._msg_pass(at(10, 0))
    server._msg_pass(at(10, 1))                                          # nothing new: nothing offered
    got = []
    while not telegram_out._Q.empty():
        got.append(telegram_out._Q.get_nowait()["line"])
    assert got == ["09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s", "10:00  HEALTH  TapeMap live · recording ok"]


def test_no_false_recording_nahi_right_after_a_restart(monkeypatch):
    """feed_health.last_post is memory-only and the first pass runs before the extension posts: a restart used to send
    RECORDING NAHI · GoCharting, then RECORDING OK 20-40 s later. Only GoCharting missing, inside FRAME_QUIET_S of the start,
    is not yet knowable; anything else missing, or the same state later, is said."""
    gc = {"ok": False, "missing": ["GoCharting"], "text": "RECORDING NAHI: GoCharting"}
    monkeypatch.setattr(server, "_recording", lambda now=None: gc)
    monkeypatch.setattr(server, "_STARTED", time.time())
    server._msg_pass(at(10, 7))
    assert [r for r in _disk() if r["kind"] == "HEALTH"] == []
    monkeypatch.setattr(server, "_recording", lambda now=None: dict(gc, missing=["book", "GoCharting"]))
    server._msg_pass(at(10, 8))                                          # a real hole alongside it: said at once
    assert [r["word"] for r in _disk() if r["kind"] == "HEALTH"] == ["RECORDING NAHI"]


def test_gocharting_missing_after_the_quiet_window_is_said(monkeypatch):
    monkeypatch.setattr(server, "_recording", lambda now=None: {"ok": False, "missing": ["GoCharting"],
                                                                "text": "RECORDING NAHI: GoCharting"})
    monkeypatch.setattr(server, "_STARTED", time.time() - server.FRAME_QUIET_S - 1)
    server._msg_pass(at(10, 7))
    assert [(r["word"], r["why"]) for r in _disk() if r["kind"] == "HEALTH"] == [("RECORDING NAHI", "GoCharting")]


def test_a_raising_telegram_offer_never_breaks_the_pass(monkeypatch, caplog):
    """offer raising must not skip the pass's HEALTH / NOW update: the lines are already on disk and in memory."""
    import telegram_out

    def boom(*a, **k):
        raise RuntimeError("offer broke")
    monkeypatch.setattr(telegram_out, "offer", boom)
    with caplog.at_level("ERROR", logger="tapemap"):
        server._msg_pass(at(10, 7))
    assert len(_disk()) == 4 and "telegram offer" in caplog.text
    assert server._MSG["health"] == "TapeMap live" and server._msg_reply(0)["asof"] == "10:07:00"
