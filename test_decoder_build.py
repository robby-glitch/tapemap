# tapemap/test_decoder_build.py
"""The decoder build round (2026-10-04, orderflow-desk 0.4.0 + this server): the one market-hours gate on every forward
record a tape post reaches, one basis for every strike, the story sentence read off the events the extension posts
(never re-derived), and the decoder's forward log."""
import json
from types import SimpleNamespace

import daylog
import decoder_log
import fold_live
import frame
import server
import story
import tape_log
from test_frame_api import _Req, _tape

DAY = "2026-09-11"                       # a Friday
T0 = 1757563500000                       # 09:35 IST on DAY: _tape()'s first closed bar


def _dec(events=None, per=None):
    return {"v": 1, "row": {"cell": 0.1, "grid": 5}, "roll": False, "priors": [], "ledger": [],
            "per": per or [], "events": events if events is not None else []}


def _e1(t=T0, state="BAAKI", oi_state="BAAKI", p=22905.0, side=-1):
    return {"id": f"E1@{t}@{p}", "kind": "E1", "name": "BADA PRINT", "t": t, "time": "09:35", "p": p, "side": side, "lots": 3025,
            "trades": 6, "xcell": 504, "share": 0.9, "at": {"kind": "band", "name": "upar band", "z": 1.64}, "quad": "naye short ?",
            "split": "baaki", "oi": {"state": oi_state, "doi": 192660, "net": None, "step": False}, "state": state, "state_t": None,
            "shown": True, "chip": "BADA SELLER 197K @22,905 · 6 haath · confirm baaki",
            "chips": ["BADA SELLER 197K @22,905 · 6 haath", "upar band", "OI confirm baaki"],
            "en": "Big seller 3,025 lots (197K) at 22,905 in 6 trades at the upper band; OI +193K on the bar — confirm pending; direction confirm pending"}


# ---- THE GATE ----------------------------------------------------------------------------------------------------
def test_the_market_hours_gate_is_today_a_weekday_and_the_session_only():
    assert server._market_hours(DAY, DAY, "09:15") and server._market_hours(DAY, DAY, "15:34")
    assert not server._market_hours(DAY, DAY, "09:14"), "nothing before the open"
    assert not server._market_hours(DAY, DAY, "15:35"), "nothing after the close"
    assert not server._market_hours("2026-10-01", "2026-10-04", "19:21"), "not 1 Oct's record from a Sunday (the 144 rows)"
    assert not server._market_hours("2026-10-03", "2026-10-03", "11:00"), "not on a Saturday, even for its own date"
    assert not server._market_hours(DAY, "garbage", "10:00")


def _post_at(monkeypatch, now_day, now_hm, n=8):
    monkeypatch.setattr(server, "_board_clock", lambda: (now_day, now_hm))
    doc = _tape(n=n)
    for b in doc["closed"]:
        b["ladder"] = [{"p": 1.0, "b": 3, "s": 1, "bt": 2, "st": 1}]
    doc["events"] = [{"t": doc["closed"][0]["t"], "kind": "absorption", "side": 1, "p": 1.0, "size": 3}]
    doc["rowAnchor"] = 0
    doc["decoder"] = _dec([_e1(t=doc["closed"][0]["t"], p=1.0)])
    req = _Req("/api/frame", doc)
    server.Handler.do_POST(req)
    assert req.out[-1][1]["ok"] is True
    return doc


def test_off_hours_the_marks_writer_and_the_decoder_log_write_nothing(monkeypatch):
    for now_day, now_hm in (("2026-09-13", "19:21"),    # a Sunday, a tab left open on the 11th
                            ("2026-09-12", "11:00"),    # the next day (a Saturday)
                            (DAY, "16:10"), (DAY, "09:05")):
        tape_log._seen_bars.clear(); tape_log._seen_marks.clear(); decoder_log._SEEN.clear()
        _post_at(monkeypatch, now_day, now_hm)
        assert tape_log.read_bars(DAY, "NIFTY") == [] and tape_log.read_marks(DAY, "NIFTY") == [], (now_day, now_hm)
        assert not __import__("os").path.exists(decoder_log.path(DAY)), (now_day, now_hm)


def test_in_session_the_same_post_writes_bars_marks_and_decoder_rows(monkeypatch):
    _post_at(monkeypatch, DAY, "10:00")
    assert len(tape_log.read_bars(DAY, "NIFTY")) == 8 and len(tape_log.read_marks(DAY, "NIFTY")) == 1
    rows = [json.loads(l) for l in open(decoder_log.path(DAY), encoding="utf-8")]
    assert [r["row"] for r in rows][:2] == ["event", "state"] and rows[0]["event"]["kind"] == "E1"


# ---- ONE BASIS -----------------------------------------------------------------------------------------------------
def test_the_frame_places_strikes_on_the_fold_engines_basis():
    assert frame.basis({"futPx": 22900.0}, {"spot": 22800.0, "basis": 71.46}) == 71.5, "the engine's basis wins"
    assert frame.basis({"futPx": 22900.0}, {"spot": 22800.0}) == 100.0, "fut - spot only while the engine has no forward"
    rows = frame._walls({"futPx": 22900.0, "lot": 65, "rowSize": 5, "walls": []},
                        {"spot": 22800.0, "basis": 71.5, "warmap": {"heat": [{"k": 22850, "ce_oi": 9e6, "pe_oi": 4e6}]}}, [])["rows"]
    ce = next(r for r in rows if r["kind"] == "CE")
    assert ce["p"] == 22921.5 and ce["strike"] == 22850.0, "a strike sits at K + the fold basis, where her W / A lines sit"


def test_the_book_carries_the_fold_engines_basis(monkeypatch):
    monkeypatch.setattr(fold_live, "_ENG", {"NIFTY": SimpleNamespace(flat=SimpleNamespace(bas=71.46))})
    assert fold_live.basis("NIFTY") == 71.5 and fold_live.basis("SENSEX") is None
    book = server._book_for(_Req("/api/frame", _tape()), "NIFTY")
    assert book["basis"] == 71.5


# ---- THE STORY -----------------------------------------------------------------------------------------------------
def test_the_story_reads_the_posted_event_and_says_where_price_is_now():
    s = story.compose(_dec([_e1()]), fut=22914.0)
    assert s["sentence"].startswith("Big seller 3,025 lots (197K) at 22,905 in 6 trades") and "price now 9 pts above his price" in s["sentence"]
    assert s["chips"] == ["BADA SELLER 197K @22,905 · 6 haath", "upar band", "OI confirm baaki"] and s["sentence_why"] is None
    assert s["event"]["state"] == "BAAKI" and s["open_prints"] == 1


def test_the_story_never_rederives_and_says_why_when_silent():
    done = story.compose(_dec([_e1(state="CONFIRMED")]), fut=22830.0)
    assert done["sentence"] is not None and "price now" not in done["sentence"], "a decided print is told as the page told it"
    assert story.compose(None)["sentence"] is None and "predates 0.4.0" in story.compose(None)["sentence_why"]
    assert story.compose(_dec([]))["sentence_why"] == "no decoder event yet today"
    assert "schema" in story.compose({"v": 2, "events": []})["sentence_why"]


def test_the_frame_and_the_desk_route_carry_the_story(monkeypatch):
    t = dict(_tape(n=3), decoder=_dec([_e1()]), futPx=22914.0)
    fr = frame.build(t, {}, "10:00")
    assert fr["story"]["sentence"] and fr["story"]["sentence_why"] is None
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-09-13", "10:00"))   # off hours: the frame still answers
    req = _Req("/api/frame", t)
    server.Handler.do_POST(req)
    got = []
    h = SimpleNamespace(path="/api/story?idx=NIFTY", _json=lambda b, code=200: got.append(json.loads(b)))
    server.Handler.do_GET(h)
    assert got and got[-1]["ok"] is True and got[-1]["sentence"].startswith("Big seller")


# ---- THE FORWARD LOG -----------------------------------------------------------------------------------------------
def _bars(n, c0=100.0):
    return [{"t": T0 + i * 300000, "o": c0, "h": c0 + 2 + i, "l": c0 - 1 - i, "c": c0 - i} for i in range(n)]


def test_the_log_writes_each_event_once_each_state_once_and_outcomes_live():
    e = _e1(t=T0, p=100.0, side=-1)
    assert decoder_log.append(_dec([e]), _bars(3), DAY, "NIFTY") == 2                 # the event and its first state
    assert decoder_log.append(_dec([e]), _bars(4), DAY, "NIFTY") == 0                 # the every-second re-post
    e2 = dict(e, state="CONFIRMED", state_t=T0 + 600000, oi={"state": "REVERSED", "doi": 192660, "net": -3705, "step": False})
    assert decoder_log.append(_dec([e2]), _bars(7), DAY, "NIFTY") == 2                # the state change + the +6 outcome
    rows = [json.loads(l) for l in open(decoder_log.path(DAY), encoding="utf-8")]
    out6 = next(r for r in rows if r["row"] == "outcome" and r["h"] == 6)
    assert out6["from"] == 100.0 and out6["to"] == 94.0 and out6["move"] == 6.0 and out6["signed"], "a seller's +6 bars: 6 points his way"
    assert decoder_log.append(_dec([e2]), _bars(13), DAY, "NIFTY") == 1               # the +12 outcome, once
    decoder_log._SEEN.clear()                                                         # a restart: the keys come back from disk
    assert decoder_log.append(_dec([e2]), _bars(13), DAY, "NIFTY") == 0


def test_the_decoder_log_is_gzipped_with_the_other_daily_records():
    assert any(d.endswith("decoder") for d in daylog.DIRS)
