"""telegram_out.py (spec 2026-10-25-message-window-telegram §4): OFF without chat.txt, the token read from its line, the
alert subset, the gate (market hours, a fresh close, once per key), 6 sends a minute with the rest as one batch, the date on
the day's first line, two retries, a failure logged once an hour and never with the token. No test reaches the network:
every send goes through a faked `_open`, and conftest points DIR at tmp_path, so her real telegr/ is never read."""
import json
import os
import queue
import urllib.error
import urllib.parse
from datetime import datetime

import pytest

import messages
import telegram_out as tg
from chain_live import IST

FAKE = "4242" + ":" + "x" * 35        # token-shaped, made up here: never hers


def at(h, m, s=0, day="2026-10-23"):
    y, mo, d = (int(x) for x in day.split("-"))
    return datetime(y, mo, d, h, m, s, tzinfo=IST)


def msg(t, kind="SETUP", word="FADE-D BUY", ev=None):
    m = messages._msg(t, "NIFTY", kind, 1, word, "4/7 saath", None, None)
    return dict(m, ev=ev) if ev else m


def qm(t, line):
    """A queued message (the queue carries the message, so the gate can run again at send) with this line."""
    return dict(msg(t), line=line)


class _R:
    """A urlopen() reply."""
    def __init__(self, body):
        self.b = json.dumps(body).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(tg, "DIR", str(tmp_path / "telegr"))           # _config() writes a FAKE bot.txt: never her real one
    monkeypatch.setattr(tg, "_ON", False)
    monkeypatch.setattr(tg, "_Q", queue.SimpleQueue())
    monkeypatch.setattr(tg, "_SENT", set())
    monkeypatch.setattr(tg, "_HELD", [])
    monkeypatch.setattr(tg, "_USED", {"minute": None, "n": 0, "day": None})
    monkeypatch.setattr(tg, "_FAIL", {"at": 0.0})
    monkeypatch.setattr(tg, "_open", lambda *a, **k: pytest.fail("a test reached the network seam unfaked"))


def _config(chat=True):
    os.makedirs(tg.DIR, exist_ok=True)
    with open(os.path.join(tg.DIR, "bot.txt"), "w", encoding="utf-8") as f:
        f.write(f"key: {FAKE}\nbot: https://t.me/tapemap_x_bot\n")
    if chat:
        with open(os.path.join(tg.DIR, "chat.txt"), "w", encoding="utf-8") as f:
            f.write("777\n")


def test_off_without_chat_txt_and_the_token_is_found_on_its_line():
    assert tg.config() is None                                           # nothing there at all
    _config(chat=False)
    assert tg.token() == FAKE and tg.chat() is None and tg.config() is None
    _config()
    assert tg.config() == (FAKE, "777")


def test_the_alert_subset():
    """SETUP; READ to LEAN / TREND; TRADE WARN / EXIT; every HEALTH. QUIT (fires late), LEG, DIN, RANGE / WAIT churn stay home."""
    assert tg.wants(msg("10:05")) and tg.wants(msg("09:20", "HEALTH", "TapeMap live"))
    assert tg.wants(msg("10:05", "READ", "RANGE → LEAN ▼", "WORD"))
    assert tg.wants(msg("10:05", "READ", "TREND ▼ · flow+fuel → TREND ▼", "WORD"))
    assert not tg.wants(msg("10:05", "READ", "LEAN ▼ → RANGE", "WORD"))
    assert not tg.wants(msg("10:05", "READ", "TREND ▼ → WAIT", "WORD"))
    assert not tg.wants(msg("10:10", "READ", "22,600 PE likhne wale bhage", "QUIT"))     # 23 Oct: 23 of 32 lines, and late
    assert not tg.wants(msg("10:05", "LEG", "▼ leg jaari")) and not tg.wants(msg("10:05", "DIN", "din CHOP"))
    assert tg.wants(msg("11:07", "TRADE", "WARN")) and tg.wants(msg("11:07", "TRADE", "EXIT"))
    assert not tg.wants(msg("11:07", "TRADE", "TIGHTEN"))


def test_the_gate_is_market_hours_and_a_fresh_close():
    assert tg.gate(msg("10:05"), at(10, 6)) and tg.gate(msg("10:05"), at(10, 15))
    assert not tg.gate(msg("10:05"), at(10, 16))                         # a restart's rebuilt morning stays in the window
    assert not tg.gate(msg("10:05"), at(10, 6, day="2026-10-24"))        # Saturday
    assert not tg.gate(msg("09:10"), at(9, 12)) and not tg.gate(msg("15:35"), at(15, 40))
    assert tg.gate(msg("15:35"), at(15, 39))


def test_offer_queues_each_message_once_and_only_when_started(monkeypatch):
    assert tg.offer([msg("10:05")], at(10, 6).timestamp()) == 0           # not started: the suite, a mock run
    monkeypatch.setattr(tg, "_ON", True)
    m = msg("10:05")
    assert tg.offer([m, m, msg("10:05", "LEG", "▼ leg jaari"), msg("09:40")], at(10, 6).timestamp()) == 1
    assert tg.offer([m], at(10, 7).timestamp()) == 0
    assert tg._Q.get_nowait()["line"] == "10:05  NIFTY  FADE-D BUY · 4/7 saath" and tg._Q.empty()


def test_the_cap_is_six_a_minute_and_the_rest_go_as_one_batch():
    L = [f"l{i}" for i in range(9)]
    assert tg.plan(L, 0) == (["l0", "l1", "l2", "l3", "l4", "+4 ek saath:\nl5\nl6\nl7\nl8"], 6)
    assert tg.plan(L[:3], 4) == (["l0", "+2 ek saath:\nl1\nl2"], 2)
    assert tg.plan(L[:3], 6) == ([], 0) and tg.plan([], 0) == ([], 0) and tg.plan(L[:2], 0) == (["l0", "l1"], 2)


def test_drain_sends_the_days_first_line_with_the_date(monkeypatch):
    _config()
    sent = []

    def fake(req, timeout=None):
        assert timeout == tg.TIMEOUT_S
        sent.append(urllib.parse.parse_qs(req.data.decode()))
        return _R({"ok": True})
    monkeypatch.setattr(tg, "_open", fake)
    tg._Q.put(qm("10:05", "10:05  NIFTY  FADE-D BUY"))
    tg._Q.put(qm("10:06", "10:06  NIFTY  b"))
    assert tg._drain(at(10, 6, 2).timestamp()) == ["Fri 23 Oct\n10:05  NIFTY  FADE-D BUY", "10:06  NIFTY  b"]
    assert [s["chat_id"] for s in sent] == [["777"], ["777"]]
    tg._Q.put(qm("10:07", "x"))
    assert tg._drain(at(10, 7).timestamp()) == ["x"]                      # same day: no second date
    for i in range(7):
        tg._Q.put(qm("10:07", f"y{i}"))
    out = tg._drain(at(10, 7, 30).timestamp())                            # 10:07 has sent one: 5 sends left
    assert out == ["y0", "y1", "y2", "y3", "+3 ek saath:\ny4\ny5\ny6"] and len(sent) == 8


def test_a_failing_send_retries_twice_and_logs_once_an_hour_without_the_token(monkeypatch, caplog):
    calls = []

    def down(req, timeout=None):
        calls.append(req.full_url)
        raise urllib.error.URLError(f"no route to {req.full_url}")       # the URL carries the token
    monkeypatch.setattr(tg, "_open", down)
    with caplog.at_level("WARNING", logger="tapemap"):
        assert tg.send(FAKE, "777", "x") is False and len(calls) == 3
        assert tg.send(FAKE, "777", "x") is False and len(calls) == 6
    assert caplog.text.count("telegram: a send failed") == 1
    assert FAKE not in caplog.text and "<token>" in caplog.text
    seq = iter([urllib.error.URLError("flaky"), None])

    def flaky(req, timeout=None):
        e = next(seq)
        if e:
            raise e
        return _R({"ok": True})
    monkeypatch.setattr(tg, "_open", flaky)
    assert tg.send(FAKE, "777", "x") is True


def test_a_trade_line_is_gated_on_when_it_was_said_not_its_triggers_time(monkeypatch):
    """A TRADE line takes the voice trigger's time as its `t`: a WARN whose trigger began 20 min ago was never fresh. The
    gate reads its write time (`at`) for TRADE only; every other kind keeps its own close."""
    m = dict(msg("10:30", "TRADE", "WARN"), at=at(10, 50).timestamp())          # trigger 10:30, said at 10:50
    assert tg.wants(m) and tg.gate(m, at(10, 50, 5)) and tg.gate(m, at(11, 0))
    assert not tg.gate(m, at(11, 1))                                           # 10 min after it was said: stale like any line
    assert not tg.gate(dict(m, at=None), at(10, 50, 5))                         # no `at`: falls back to the trigger's time
    assert not tg.gate(dict(m, kind="SETUP"), at(10, 50, 5))                    # only TRADE is read by `at`
    monkeypatch.setattr(tg, "_ON", True)
    assert tg.offer([m], at(10, 50, 5).timestamp()) == 1 and tg._Q.get_nowait() is m


def test_a_line_that_went_stale_in_the_queue_is_not_sent(monkeypatch):
    """The gate runs again at send: a line queued fresh, then held (cap) or delayed past FRESH_S, is dropped, never sent late."""
    _config()
    sent = []
    monkeypatch.setattr(tg, "_open", lambda req, timeout=None: sent.append(req) or _R({"ok": True}))
    tg._Q.put(qm("10:05", "10:05  NIFTY  old"))
    assert tg._drain(at(10, 20).timestamp()) == [] and sent == [] and tg._HELD == []      # 15 min in the queue
    tg._USED.update(minute="2026-10-23 10:06", n=tg.CAP)                                   # this minute's cap is spent
    tg._Q.put(qm("10:05", "10:05  NIFTY  held"))
    assert tg._drain(at(10, 6, 30).timestamp()) == [] and len(tg._HELD) == 1               # held, still fresh
    assert tg._drain(at(10, 20).timestamp()) == [] and sent == [] and tg._HELD == []       # went stale while held
    tg._Q.put(qm("10:19", "10:19  NIFTY  fresh"))
    assert tg._drain(at(10, 20, 5).timestamp()) == ["Fri 23 Oct\n10:19  NIFTY  fresh"] and len(sent) == 1
