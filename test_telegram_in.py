"""telegram_in.py (her word 26 Oct: "add read-only Telegram replies: /now and /last, only from my chat"): the right text for
/now and /last, nothing for any other chat (and its text never logged), the backlog skipped at start, the help line for
anything else, OFF without chat.txt, the token never in a log line, 10 replies a minute. No test reaches the network: every
call goes through a faked telegram_out._open, DIR is under tmp_path (her real telegr/ is never read), no thread is started
and the back-off never sleeps."""
import json
import os
import types
import urllib.error
import urllib.parse
from datetime import datetime

import pytest

import messages
import server
import telegram_in as tgi
import telegram_out as out
from chain_live import IST

FAKE = "4242" + ":" + "z" * 35        # token-shaped, made up here: never hers
CHAT = 777


def at(h, m, s=0, day="2026-10-23"):                    # a Friday
    y, mo, d = (int(x) for x in day.split("-"))
    return datetime(y, mo, d, h, m, s, tzinfo=IST).timestamp()


class _R:
    def __init__(self, body):
        self.b = json.dumps(body).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Stop(BaseException):
    """Ends _run's endless loop in a test (BaseException: _run's `except Exception` must not swallow it)."""


@pytest.fixture(autouse=True)
def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(out, "DIR", str(tmp_path / "telegr"))
    monkeypatch.setattr(tgi, "_ON", False)
    monkeypatch.setattr(tgi, "_SENT", [])
    monkeypatch.setattr(tgi, "_QUIET", {})
    monkeypatch.setattr(tgi, "_sleep", lambda s: pytest.fail("a test slept for real"))
    monkeypatch.setattr(out, "_open", lambda *a, **k: pytest.fail("a test reached the network seam unfaked"))


def _config(chat=True):
    os.makedirs(out.DIR, exist_ok=True)
    with open(os.path.join(out.DIR, "bot.txt"), "w", encoding="utf-8") as f:
        f.write(f"key: {FAKE}\nbot: https://t.me/tapemap_x_bot\n")
    if chat:
        with open(os.path.join(out.DIR, "chat.txt"), "w", encoding="utf-8") as f:
            f.write(f"{CHAT}\n")


CFG = (FAKE, str(CHAT))


def upd(i, text, chat=CHAT, kind="private"):
    return {"update_id": i, "message": {"chat": {"id": chat, "type": kind}, "text": text}}


def wire(monkeypatch, replies):
    """A fake telegram: each getUpdates GET answers with the next list in `replies` (a BaseException ends the run), each
    sendMessage POST is recorded. -> (gets, sent)."""
    gets, sent, it = [], [], iter(replies)

    def fake(req, timeout=None):
        if req.data is None:
            gets.append((urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query), timeout))
            nxt = next(it)
            if isinstance(nxt, BaseException):
                raise nxt
            return _R({"ok": True, "result": nxt})
        sent.append(urllib.parse.parse_qs(req.data.decode()))
        return _R({"ok": True})
    monkeypatch.setattr(out, "_open", fake)
    return gets, sent


NOW = [{"idx": "NIFTY", "dir": -1, "word": "TREND", "line": "NIFTY  ▼ TREND · 5/7 saath · since 09:55", "why": "mark 10:40"},
       {"idx": "SENSEX", "dir": 0, "word": None, "line": "SENSEX  read abhi nahi", "why": "could not check — no READ mark"}]


def mm(t, at_, kind="READ"):
    m = messages._msg(t, "NIFTY", kind, 1, f"w{t}", "4/7 saath", None, None)
    return dict(m, at=at_)


MSGS = [mm(f"10:{i:02d}", 1000.0 + i) for i in range(12)]     # written oldest first, as the stream keeps them


def prov(rep=None):
    return lambda: rep if rep is not None else {"ok": True, "day": "2026-10-23", "asof": "10:42:00", "now": NOW, "msgs": MSGS}


def texts(sent):
    return [s["text"][0] for s in sent]


def test_now_and_last_from_her_chat_send_the_right_text(monkeypatch):
    gets, sent = wire(monkeypatch, [[upd(10, "/now"), upd(11, "/last")]])
    assert tgi.poll(CFG, 3, prov(), at(10, 42)) == 12
    assert gets == [({"timeout": ["25"], "offset": ["3"]}, 25 + out.TIMEOUT_S)]            # a long-poll, from the next offset
    assert texts(sent) == ["NOW 10:42\nNIFTY  ▼ TREND · 5/7 saath · since 09:55\nSENSEX  read abhi nahi",
                           "\n".join(m["line"] for m in reversed(MSGS[2:]))]                  # the 10 newest, newest first
    assert [s["chat_id"] for s in sent] == [["777"], ["777"]]
    assert texts(sent)[1].splitlines()[0] == "10:11  NIFTY  w10:11 · 4/7 saath"               # each line carries its time


def test_the_answers_when_the_stream_has_nothing_or_could_not_check():
    d = datetime.fromtimestamp(at(8, 50), IST)
    assert tgi.answer("/now", prov(), d) == "NOW 08:50 · market abhi khula nahi"             # before the open, never blank
    sat = datetime.fromtimestamp(at(11, 0, day="2026-10-24"), IST)
    assert tgi.answer("/now", prov(), sat) == "NOW 11:00 · market abhi khula nahi"
    why = "could not check — the message stream has not read today yet (its first pass runs at the start)"
    bad = prov({"ok": False, "why": why})
    d = datetime.fromtimestamp(at(10, 42), IST)
    assert tgi.answer("/now", bad, d) == "NOW 10:42 · " + why and tgi.answer("/last", bad, d) == why
    empty = prov({"ok": True, "now": [], "msgs": []})
    assert tgi.answer("/now", empty, d) == "NOW 10:42 · koi read nahi" and tgi.answer("/last", empty, d) == "koi message nahi"
    boom = lambda: (_ for _ in ()).throw(RuntimeError("secret"))                                 # noqa: E731
    assert tgi.answer("/now", boom, d) == "NOW 10:42 · could not check — RuntimeError"       # a raising provider is still a reply


def test_now_says_purana_when_the_streams_last_pass_is_over_two_minutes_old():
    d = datetime.fromtimestamp(at(10, 42), IST)
    old = prov({"ok": True, "asof": "10:31:05", "now": NOW, "msgs": []})
    assert tgi.answer("/now", old, d).splitlines()[0] == "NOW 10:42 · purana — stream 10:31 se ruka"
    fresh = prov({"ok": True, "asof": "10:40:30", "now": NOW, "msgs": []})
    assert tgi.answer("/now", fresh, d).splitlines()[0] == "NOW 10:42"


def test_last_orders_by_the_windows_own_key_time_then_written_at():
    d = datetime.fromtimestamp(at(11, 0), IST)
    ms = [mm("10:05", 1.0), mm("10:05", 2.0, "LEG"), mm("09:55", 9.0)]
    got = tgi.answer("/last", prov({"ok": True, "msgs": ms}), d).splitlines()
    assert got == [ms[1]["line"], ms[0]["line"], ms[2]["line"]]


def test_another_chat_gets_no_reply_and_its_text_is_never_logged(monkeypatch, caplog):
    gets, sent = wire(monkeypatch, [[upd(1, "SECRET-TEXT /now", chat=999), upd(2, "SECRET-TEXT", chat=777, kind="group"),
                                     upd(3, "SECRET-TEXT", chat=-777, kind="private"), {"update_id": 4, "edited_message": {}}]])
    with caplog.at_level("DEBUG", logger="tapemap"):
        assert tgi.poll(CFG, 0, prov(), at(10, 42)) == 5
        assert sent == []
        assert "SECRET-TEXT" not in caplog.text and FAKE not in caplog.text
        assert caplog.text.count("ignored update from another chat") == 1                       # three ignored, one line
        wire(monkeypatch, [[upd(9, "SECRET-TEXT", chat=999)]])
        tgi.poll(CFG, 5, prov(), at(10, 42) + 3601)
    assert caplog.text.count("ignored update from another chat") == 2                           # at most once an hour


def test_the_backlog_is_skipped_at_start_and_never_answered(monkeypatch):
    gets, sent = wire(monkeypatch, [[upd(5, "/now"), upd(6, "/last")], []])
    assert tgi.backlog(FAKE) == 7 and sent == []
    assert [g[0]["offset"] for g in gets] == [["0"], ["7"]] and [g[0]["timeout"] for g in gets] == [["0"], ["0"]]
    # and through the whole receiver: the queued 5 and 6 are acknowledged, only the command that arrives after is answered
    _config()
    gets, sent = wire(monkeypatch, [[upd(5, "/now"), upd(6, "/last")], [], [upd(7, "/last")], _Stop()])
    with pytest.raises(_Stop):
        tgi._run(prov({"ok": True, "msgs": MSGS[:1]}))
    assert texts(sent) == [MSGS[0]["line"]] and [g[0]["offset"][0] for g in gets] == ["0", "7", "7", "8"]


def test_anything_else_from_her_chat_gets_the_one_line_help(monkeypatch):
    gets, sent = wire(monkeypatch, [[upd(1, "/start"), upd(2, "hello"), {"update_id": 3, "message": {"chat": {"id": CHAT,
                      "type": "private"}, "photo": [{}]}}, upd(4, "/buy NIFTY"), upd(5, "/NOW@tapemap_x_bot")]])
    tgi.poll(CFG, 0, prov(), at(10, 42))
    assert texts(sent) == ["/now · /last"] * 4 + ["NOW 10:42\n" + NOW[0]["line"] + "\n" + NOW[1]["line"]]   # @botname and case are fine


def test_off_without_chat_txt_and_on_with_it(monkeypatch):
    def no_thread(*a, **k):
        pytest.fail("a thread was started")
    monkeypatch.setattr(tgi, "threading", types.SimpleNamespace(Thread=no_thread))
    assert tgi.start(prov()) is False and tgi._ON is False                    # no telegr/ at all: no receiver
    _config(chat=False)
    assert tgi.start(prov()) is False                                         # a token alone is not her chat
    _config()
    made = []

    class T:
        def __init__(self, target=None, args=(), name=None, daemon=None):
            made.append((target, args, name, daemon))

        def start(self):
            made.append("started")
    monkeypatch.setattr(tgi, "threading", types.SimpleNamespace(Thread=T))
    p = prov()
    assert tgi.start(p) is True and tgi.start(p) is False
    assert made == [(tgi._run, (p,), "telegram_in", True), "started"]


def test_the_server_starts_the_receiver_beside_the_sender_with_the_streams_own_reply():
    import inspect
    src = inspect.getsource(server.main)
    assert "telegram_in.start(_msg_reply)" in src and src.index("telegram_out.start()") < src.index("telegram_in.start(")


def test_a_failing_poll_backs_off_5_to_60_logs_once_and_never_the_token(monkeypatch, caplog):
    _config()
    waits = []

    def down(req, timeout=None):
        raise urllib.error.URLError(f"no route to {req.full_url}")           # the URL carries the token
    monkeypatch.setattr(out, "_open", down)

    def sleep(s):
        waits.append(s)
        if len(waits) == 7:
            raise _Stop()
    monkeypatch.setattr(tgi, "_sleep", sleep)
    with caplog.at_level("DEBUG", logger="tapemap"), pytest.raises(_Stop):
        tgi._run(prov())
    assert waits == [5, 10, 20, 40, 60, 60, 60]
    assert caplog.text.count("could not poll") == 1 and FAKE not in caplog.text and "<token>" in caplog.text


def test_a_telegram_not_ok_such_as_a_409_backs_off_and_the_wait_resets_after_a_good_poll(monkeypatch):
    _config()
    waits = []
    seq = iter([{"ok": False, "description": "Conflict: terminated by other getUpdates request"}, {"ok": True, "result": []},
                {"ok": True, "result": []}, {"ok": False, "description": "x"}, None])

    def fake(req, timeout=None):
        nxt = next(seq)
        if nxt is None:
            raise _Stop()
        return _R(nxt)
    monkeypatch.setattr(out, "_open", fake)
    monkeypatch.setattr(tgi, "_sleep", waits.append)
    with pytest.raises(_Stop):
        tgi._run(prov())
    assert waits == [5, 5]                          # 409 (5), a good backlog and a good poll reset it, then not ok: 5 again


def test_ten_replies_a_minute_then_none_until_the_next_minute(monkeypatch):
    gets, sent = wire(monkeypatch, [[upd(i, "/now") for i in range(12)], [upd(20, "/now")], [upd(21, "/now")]])
    assert tgi.poll(CFG, 0, prov(), at(10, 42, 5)) == 12 and len(sent) == 10
    assert tgi.poll(CFG, 12, prov(), at(10, 42, 59)) == 21 and len(sent) == 10          # the 11th in the same minute: silence
    assert tgi.poll(CFG, 21, prov(), at(10, 43, 6)) == 22 and len(sent) == 11           # 60 s after the first reply it has room


def test_one_bad_update_never_stops_the_receiver(monkeypatch, caplog):
    gets, sent = wire(monkeypatch, [[upd(1, "/last"), upd(2, "/now")]])
    bad = {"ok": True, "msgs": [{"t": "10:00"}], "now": NOW}                         # a message with no `line`
    with caplog.at_level("DEBUG", logger="tapemap"):
        assert tgi.poll(CFG, 0, prov(bad), at(10, 42)) == 3
    assert len(sent) == 1 and sent[0]["text"][0].startswith("NOW 10:42") and "a reply failed" in caplog.text


def test_any_other_text_from_her_chat_goes_to_the_command_grammar(monkeypatch):
    """Jarvis v3 Task 2: with the server's command door wired (telegram_in.CMD, set in server.main), any text other than
    /now and /last is a command (a leading / and an @botname stripped; the index NIFTY unless the first word names one);
    the reply is the command's reply and lines. /now and /last are untouched; an order word is refused."""
    from datetime import datetime as _dt
    import inspect
    monkeypatch.setattr(server, "_ist", lambda now=None: _dt(2026, 10, 23, 10, 42, tzinfo=IST))
    monkeypatch.setattr(server, "_JARVIS", {})
    monkeypatch.setattr(server, "_JCMD", {})
    monkeypatch.setattr(tgi, "CMD", server._jarvis_tg)
    gets, sent = wire(monkeypatch, [[upd(1, "/watch@tapemap_x_bot 22800s"), upd(2, "/now"), upd(3, "SENSEX watch 74000s"),
                                     upd(4, "/buy 5 lots"), upd(5, "why")]])
    tgi.poll(CFG, 0, prov(), at(10, 42))
    assert texts(sent) == ["watching 22,800s (1 of 10 today)",
                           "NOW 10:42\n" + NOW[0]["line"] + "\n" + NOW[1]["line"],
                           "watching 74,000s (2 of 10 today)", "I read, I don't place.",
                           "could not check — no frame built yet"]
    assert server._jcmd().state("SENSEX")["watches"][0]["level"] == 74000.0
    assert "telegram_in.CMD = _jarvis_tg" in inspect.getsource(server.main)
