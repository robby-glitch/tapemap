# tapemap/test_feed_health.py
"""FEED HEALTH (P3): the GoCharting tape's state from the data, never from a timer alone. LIVE -> SLOW -> DEAD -> LIVE,
STALLED by bar lag and by volume, NOT OPEN TODAY, AFTER CLOSE, a day roll, `since` from the data, and the wire."""
import json
import os
from datetime import datetime

import pytest

import feed_health as fh
import server
from chain_live import IST

DAY = "2026-09-29"


def at(h, m, s=0, day=DAY):
    y, mo, d = (int(x) for x in day.split("-"))
    return datetime(y, mo, d, h, m, s, tzinfo=IST).timestamp()


def bar_ms(h, m):
    return int(at(h, m) * 1000)


def doc(last_bar=(10, 0), vols=None, visible="visible"):
    ts = [bar_ms(9, 15) + 300000 * i for i in range(((last_bar[0] - 9) * 60 + last_bar[1] - 15) // 5 + 1)]
    vols = vols or {}
    return {"closed": [{"t": t, "vol": vols.get(t, 500)} for t in ts],
            "hb": {"t": 0, "seq": 1, "visible": visible, "last_bar_t": ts[-1] if ts else None, "tape_at": 0}}


@pytest.fixture(autouse=True)
def _fresh():
    fh.reset()
    fh.LOG = None
    yield
    fh.reset()


def test_no_post_today_is_not_open_not_dead():
    r = fh.read("NIFTY", now=at(10, 0))
    assert r["state"] == "NOT OPEN TODAY" and r["alarm"] is False and r["sound"] is False
    assert "no post" in r["why"] and r["chip"] == "GoCharting aaj khula nahi"
    # before the open, the same word with its own reason (three absences never collapse)
    assert "not opened" in fh.read("NIFTY", now=at(9, 0))["why"]


def test_live_slow_dead_live_with_since_from_the_data():
    t0 = at(10, 0)
    for i in range(3):
        fh.on_post("NIFTY", DAY, doc(), now=t0 + 2 * i)
    r = fh.read("NIFTY", now=t0 + 5)
    assert r["state"] == "LIVE" and r["posts"] == 3 and r["last_bar"] == "10:00" and r["visible"] == "visible"
    # SLOW: a gap past SLOW_S is throttled, not dead; since = the last post + SLOW_S, not the read time
    r = fh.read("NIFTY", now=t0 + 4 + fh.SLOW_S + 7)
    assert r["state"] == "SLOW" and r["alarm"] is False and r["since"] == fh._hms(t0 + 4 + fh.SLOW_S)
    # DEAD: past DEAD_S; since is the moment the condition began, whatever time the reader looked
    r = fh.read("NIFTY", now=t0 + 4 + fh.DEAD_S + 300)
    assert r["state"] == "DEAD" and r["alarm"] is True and r["since"] == fh._hms(t0 + 4 + fh.DEAD_S)
    assert "tab kholo / F5" in r["chip"] and "Memory Saver" in r["do"] and r["sound"] is False     # sound OFF until she signs N
    # a post brings it back
    fh.on_post("NIFTY", DAY, doc(last_bar=(10, 5)), now=t0 + 4 + fh.DEAD_S + 301)
    r = fh.read("NIFTY", now=t0 + 4 + fh.DEAD_S + 302)
    assert r["state"] == "LIVE"
    assert [(e["from"], e["to"]) for e in r["events"]] == [(None, "LIVE"), ("LIVE", "SLOW"), ("SLOW", "DEAD"), ("DEAD", "LIVE")]


def test_hidden_tab_is_slow_even_when_posts_are_fresh():
    fh.on_post("NIFTY", DAY, doc(visible="hidden"), now=at(10, 0))
    r = fh.read("NIFTY", now=at(10, 0, 3))
    assert r["state"] == "SLOW" and "hidden" in r["why"] and r["alarm"] is False


def test_stalled_when_the_due_bar_never_closes():
    # last closed bar 10:00 (closes 10:05); the 10:05 bar is due at 10:10; posts keep arriving
    t = at(10, 10, 0) + fh.BAR_LAG_S + 5
    fh.on_post("NIFTY", DAY, doc(last_bar=(10, 0)), now=t - 1)
    r = fh.read("NIFTY", now=t)
    assert r["state"] == "STALLED" and r["alarm"] is True and r["since"] == fh._hms(at(10, 10) + fh.BAR_LAG_S)
    assert "no bar has closed since 10:00" in r["why"]


def test_stalled_when_the_closed_bar_is_short_of_upstox_and_clears_on_the_next():
    t1225 = bar_ms(12, 25)
    fh.on_post("NIFTY", DAY, doc(last_bar=(12, 25), vols={t1225: 136}), now=at(12, 30, 2))
    r = fh.read("NIFTY", now=at(12, 30, 5), ux_vols={t1225: 943})
    assert r["state"] == "STALLED" and r["short_bar"] == {"t": "12:25", "gc": 136, "ux": 943} and r["since"] == "12:30:00"
    assert "136 of Upstox's 943" in r["why"] and "ticks ruke" in r["chip"]
    # the next bar closes complete: LIVE again (the hole stays in the record; the reader's completeness check owns it)
    fh.on_post("NIFTY", DAY, doc(last_bar=(12, 30), vols={t1225: 136, bar_ms(12, 30): 2013}), now=at(12, 35, 2))
    r = fh.read("NIFTY", now=at(12, 35, 5), ux_vols={t1225: 943, bar_ms(12, 30): 2013})
    assert r["state"] == "LIVE"


def test_after_close_keeps_the_last_post_but_a_tape_that_died_in_session_stays_dead():
    fh.on_post("NIFTY", DAY, doc(last_bar=(15, 25)), now=at(15, 29, 50))
    r = fh.read("NIFTY", now=at(15, 35))
    assert r["state"] == "AFTER CLOSE" and r["alarm"] is False and r["last_post"] == "15:29:50" and "15:29" in r["chip"]
    fh.reset()
    fh.on_post("NIFTY", DAY, doc(last_bar=(12, 20)), now=at(12, 25, 51))
    r = fh.read("NIFTY", now=at(15, 35))
    assert r["state"] == "DEAD" and r["since"] == fh._hms(at(12, 25, 51) + fh.DEAD_S) and "did not return" in r["why"]
    fh.on_post("NIFTY", DAY, doc(last_bar=(15, 25)), now=at(16, 8))
    assert fh.read("NIFTY", now=at(16, 9))["state"] == "AFTER CLOSE"


def test_yesterdays_session_reposted_before_the_open_is_not_a_post_today():
    fh.on_post("NIFTY", "2026-09-28", doc(), now=at(8, 50))           # the extension re-posts the kept day at boot
    r = fh.read("NIFTY", now=at(9, 30))
    assert r["state"] == "NOT OPEN TODAY" and r["posts"] == 0
    fh.on_post("NIFTY", DAY, doc(last_bar=(9, 15)), now=at(9, 21))
    assert fh.read("NIFTY", now=at(9, 21, 2))["state"] == "LIVE"


def test_transitions_are_logged_once_each(tmp_path):
    fh.LOG = str(tmp_path / "feed_log.jsonl")
    fh.on_post("NIFTY", DAY, doc(), now=at(10, 0))
    for s in (1, 2, 3):
        fh.read("NIFTY", now=at(10, 0, s))
    fh.read("NIFTY", now=at(10, 0) + fh.DEAD_S + 1)
    rows = [json.loads(l) for l in open(fh.LOG, encoding="utf-8")]
    assert [r["to"] for r in rows] == ["LIVE", "DEAD"] and rows[1]["since"] == fh._hms(at(10, 0) + fh.DEAD_S)


def test_read_never_raises(monkeypatch):
    monkeypatch.setattr(fh.Tracker, "read", lambda self, now, ux_vols=None: 1 / 0)
    r = fh.read("NIFTY", now=at(10, 0))
    assert r["state"] is None and "could not check" in r["why"] and r["alarm"] is False


# ---- the wire: the frame door feeds it, /api/feed/gc and the faces' replies carry it -------------------------------
from test_frame_api import _Cap, _Req, _tape    # the harnesses, one copy in the tree


def test_the_frame_door_feeds_it_and_the_wire_carries_it(tmp_path, monkeypatch):
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(server, "_ux_bars", lambda idx, day: [])
    import tape_log
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    import time
    today = time.strftime("%Y-%m-%d")                 # the tracker counts posts for TODAY's session only
    body = {**_tape(n=3), "session": f"NIFTY-I|5m|{today}", "hb": {"t": 1, "seq": 7, "visible": "visible", "last_bar_t": 1, "tape_at": 1}}
    req = _Req("/api/frame", body)
    server.Handler.do_POST(req)
    j = req.out[-1][1]
    assert j["ok"] is True and j["feed"]["idx"] == "NIFTY" and j["feed"]["hb"]["seq"] == 7   # the panel gets the band too
    g = _Cap("/api/feed/gc?idx=NIFTY")
    server.Handler.do_GET(g)
    assert g.sent["ok"] is True and g.sent["state"] in fh.STATES and g.sent["thresholds"]["signed"] is False
    assert g.sent["depends_on_gc"] and g.sent["upstox_only"] and g.sent["sound"] is False
    t = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(t)
    assert "feed" in t.sent and t.sent["feed"]["idx"] == "NIFTY"
    monkeypatch.setattr(server, "_hold_trades", lambda: [])
    f = _Cap("/api/fold/flat?idx=NIFTY")
    server.Handler.do_GET(f)
    assert isinstance(f.sent, dict) and "feed" in f.sent


def test_a_broken_feed_read_never_breaks_the_frame_door(tmp_path, monkeypatch):
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    import tape_log
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    monkeypatch.setattr(fh.Tracker, "on_post", lambda self, now, day, doc: 1 / 0)
    monkeypatch.setattr(fh, "read", lambda idx, now=None, ux_vols=None: 1 / 0)      # the deepest failure, past its own guard
    req = _Req("/api/frame", _tape(n=2))
    server.Handler.do_POST(req)
    j = req.out[-1][1]
    assert j["ok"] is True and j["have_bars"] == 2 and j["feed"]["state"] is None and "could not check" in j["feed"]["why"]


# ---- 29 Sep, replayed from the frame log's arrival minutes: DEAD at about 12:27, DEAD until the 16:08 post ----------
FRAME_LOG = os.path.join(os.path.dirname(__file__), "data", "frame", "frame_2026-09-29.jsonl")


@pytest.mark.skipif(not os.path.exists(FRAME_LOG), reason="the 29 Sep frame log is not on this machine")
def test_replay_2026_09_29_goes_dead_at_about_1227_and_stays_dead_until_1608():
    import re
    rows, top = [], 0
    with open(FRAME_LOG, encoding="utf-8") as f:
        for line in f:
            m = re.search(r'"ts":\s*"(\d\d):(\d\d)"', line[:400]); hb = re.search(r'"have_bars":\s*(\d+)', line[:800])
            if not m:
                continue
            h = int(m.group(1))
            top = max(top, h)
            # the session day only: the live file also gets a midnight re-post, and the NEXT morning's pre-open
            # posts (GoCharting still shows this session before 09:15, so 30 Sep 09:01-09:08 landed here)
            if 9 <= h <= 16 and not (top >= 15 and h < 12):
                rows.append((h, int(m.group(2)), int(hb.group(1)) if hb else 0))
    per_min = {}
    for h, m, n in rows:
        per_min.setdefault((h, m), []).append(n)
    posts = []
    for (h, m), ns in sorted(per_min.items()):
        step = 60.0 / len(ns)
        for i, n in enumerate(ns):
            posts.append((at(h, m) + i * step, n))
    posts.sort()
    seen = {}
    pi = 0
    for h in range(9, 17):
        for m in range(60):
            now = at(h, m, 30)
            while pi < len(posts) and posts[pi][0] <= now:
                t, n = posts[pi]
                d = {"closed": [{"t": bar_ms(9, 15) + 300000 * i, "vol": 1} for i in range(n)]}
                fh.on_post("NIFTY", DAY, d, now=t); pi += 1
            seen[(h, m)] = fh.read("NIFTY", now=now)
    assert seen[(9, 19)]["state"] == "NOT OPEN TODAY" and seen[(9, 30)]["state"] == "LIVE"
    assert seen[(12, 26)]["state"] in ("LIVE", "SLOW") and seen[(12, 28)]["state"] == "DEAD"
    assert seen[(12, 28)]["since"] >= "12:26:30" and seen[(12, 28)]["since"] <= "12:27:40"
    assert all(seen[(h, m)]["state"] == "DEAD" for h in (13, 14) for m in range(60))
    assert seen[(15, 35)]["state"] == "DEAD" and seen[(16, 7)]["state"] == "DEAD"
    assert seen[(16, 9)]["state"] == "AFTER CLOSE"
