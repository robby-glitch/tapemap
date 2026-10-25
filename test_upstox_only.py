"""Nothing on the Upstox path may depend on a Dhan file.

The switch itself is covered by test_broker_switch. This file covers the two
places that read or wrote `.dhan_token` REGARDLESS of the switch -- both found
on 2026-08-06 while checking whether the desktop launcher would come up on
Upstox:

  * `live._token()` opened `.dhan_token` unconditionally, so deleting a file
    the Upstox path never transmits would have killed the whole tape with a
    FileNotFoundError naming a broker it was not running on.
  * POST `/api/token` validated a Dhan JWT and wrote `.dhan_token` while the
    running tape and chain read `.upstox_token` -- an "accepted" that changed
    nothing the operator could see.

No token here is real: the Dhan-path test writes a placeholder into pytest's
tmp_path, never into the repo.
"""

import inspect
import json

import pytest

import live
import server
import upstox_chain


def _down_feed(last_error):
    """A source whose socket is down, with whatever the feed did or did not
    record. Built with __new__ so no websocket is created."""
    src = upstox_chain.UpstoxChainSource.__new__(upstox_chain.UpstoxChainSource)
    src.resolved = {"NIFTY": {"idx_key": "k", "meta": {}}}
    src.feed = type("_F", (), {"connected": False,
                               "last_error": last_error})()
    return src


def test_a_down_feed_with_no_recorded_error_still_gives_a_reason():
    """`last_error` is None before the first connect finishes, and the raw
    f-string printed "upstox feed down: None" -- an absence with no reason.
    On 2026-08-06 NIFTY showed that None while BANKNIFTY and SENSEX carried
    the real 401, so the watched index was the one hiding the cause."""
    with pytest.raises(RuntimeError) as e:
        _down_feed(None).poll({"under_sym": "NIFTY"}, "2026-08-07", None)
    msg = str(e.value)
    assert "None" not in msg
    assert "upstox_auth.py" in msg          # names the thing that fixes it


def test_a_real_feed_error_is_passed_through_untouched():
    """The fallback must not swallow a cause that WAS recorded."""
    with pytest.raises(RuntimeError) as e:
        _down_feed("WebSocketBadStatusException: Handshake status 401").poll(
            {"under_sym": "NIFTY"}, "2026-08-07", None)
    assert "401" in str(e.value)


def _broker(monkeypatch, value):
    """Select the broker for one test. `None` means "leave it unset", which
    is the shipped default: upstox since 25 Oct (review C10)."""
    if value is None:
        monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    else:
        monkeypatch.setenv("TAPEMAP_BROKER", value)


# ---- live._token() ---------------------------------------------------------

def test_the_tape_needs_no_dhan_token_on_upstox(tmp_path, monkeypatch):
    """Run from a directory with no `.dhan_token` at all. On Upstox that is
    not an error, because the value is never sent anywhere."""
    monkeypatch.chdir(tmp_path)
    _broker(monkeypatch, "upstox")
    assert live._token() == ""


def test_the_tape_still_reads_the_dhan_token_on_dhan(tmp_path, monkeypatch):
    """The fix must not quietly disarm the path it was not aimed at."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dhan_token").write_text(
        "  eyJtest.token.value  \n", encoding="utf-8")
    _broker(monkeypatch, "dhan")                  # the Dhan fallback, chosen by name (C10)
    assert live._token() == "eyJtest.token.value"


def test_a_missing_dhan_token_still_fails_loudly_on_dhan(tmp_path, monkeypatch):
    """Returning "" for everyone would have been the easy fix, and it would
    have turned a real Dhan misconfiguration into a silently empty chart."""
    monkeypatch.chdir(tmp_path)
    _broker(monkeypatch, "dhan")
    with pytest.raises(FileNotFoundError):
        live._token()


# ---- POST /api/token -------------------------------------------------------

def test_the_token_button_refuses_upstox_before_writing_anything():
    """Ordering, not just presence. A refusal placed after the write would
    still leave a Dhan file on disk and a poller reload behind it."""
    src = inspect.getsource(server.Handler.do_POST)
    refuse = src.index('_broker() == "upstox"')
    write = src.index("write_text")
    assert refuse < write, "the Upstox refusal must come before the write"


def test_the_refusal_names_what_actually_re_auths():
    """HANDOFF section 9: an absence gets a reason. "rejected" with no next
    step sends the operator to the Dhan dashboard at 09:15, which is exactly
    the wrong place."""
    assert "upstox_auth.py" in inspect.getsource(server.Handler.do_POST)


# ---- GET /api/health -------------------------------------------------------

class _Cap:
    """A Handler with the socket machinery removed.

    `__init__` is skipped and `_json` captures instead of writing, so routing
    can be exercised without binding a port or owning a real request.
    """

    def __init__(self, path, payloads=None):
        self.path = path
        self.payloads = payloads or {}
        self.chains = None
        self.poller = None
        self.sent = None

    def _json(self, body, code=200):
        self.sent = json.loads(body.decode())


def _get(path, payloads=None):
    cap = _Cap(path, payloads)
    server.Handler.do_GET(cap)
    return cap.sent


def test_health_reports_the_broker_actually_in_force(monkeypatch):
    monkeypatch.setenv("TAPEMAP_BROKER", "upstox")
    out = _get("/api/health", payloads={"NIFTY": {}, "SENSEX": {}})
    assert out["ok"] is True
    assert out["broker"] == "upstox"
    assert out["indices"] == ["NIFTY", "SENSEX"]
    assert isinstance(out["started_at"], float)


def test_health_says_upstox_when_nothing_selected_it(monkeypatch):
    """It must report what is TRUE, not what the launcher intended -- the
    launcher's whole check depends on it. Since 25 Oct (review C10) setting
    nothing is upstox; dhan is said only when chosen."""
    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    assert _get("/api/health")["broker"] == "upstox"
    monkeypatch.setenv("TAPEMAP_BROKER", "dhan")
    assert _get("/api/health")["broker"] == "dhan"


def test_only_one_server_may_hold_the_port():
    """Python's HTTPServer sets allow_reuse_address = 1, and on Windows that
    lets a second process TAKE a port the first is listening on. Two servers
    came up 2s apart on 2026-08-06 and the loser kept an Upstox socket."""
    assert server._Server.allow_reuse_address is False


def test_the_port_is_claimed_before_the_chain_poller_starts():
    """The ordering IS the fix. Both lines present in the wrong order is
    exactly the bug: the poller opened a websocket, and only then did the
    process find out it had lost the port -- and it kept the socket."""
    src = inspect.getsource(server.main)
    assert src.index("_Server((") < src.index("_start_chain(mock_chain")


def test_health_answers_with_no_tape_at_all(monkeypatch):
    """The point of the route. Both callers need an answer precisely when the
    tape has nothing: the launcher before deciding to reuse port 8765, and the
    banner before deciding whether "unreachable" is the truth."""
    monkeypatch.setenv("TAPEMAP_BROKER", "upstox")
    out = _get("/api/health", payloads={})
    assert out["ok"] is True
    assert out["indices"] == []


def test_today_s_bars_are_today_s_only_after_midnight(monkeypatch):
    """00:00:06 on 1 Oct: the intraday endpoint still served 30 Sep's candles, build_session labelled them
    with the new date, and 57 of 30 Sep's arms went into trigger_log again as 1 Oct rows."""
    from datetime import datetime
    import live
    import upstox_feed
    import upstox_rest
    today = datetime.now(live.IST).strftime("%Y-%m-%d")
    old = ["2026-09-30T15:29:00+05:30", 1, 2, 0.5, 1.5, 10, 0]
    monkeypatch.setattr(upstox_feed, "read_token", lambda: "t")
    monkeypatch.setattr(upstox_rest, "intraday", lambda key, tok: [old])
    assert not live._upstox_bars("NSE_FO|1", "OPTIDX", today).get("close")       # yesterday's session is not today's
    new = [f"{today}T09:15:00+05:30", 1, 2, 0.5, 1.5, 10, 0]
    monkeypatch.setattr(upstox_rest, "intraday", lambda key, tok: [new, old])
    assert live._upstox_bars("NSE_FO|1", "OPTIDX", today)["close"] == [1.5]



def test_d1_each_poll_recentres_the_window_on_the_live_spot():
    """The socket carries +/- 16 strikes; a poll hands downstream the 17 nearest the LIVE spot (8 Oct: the opening
    window ended two strikes from spot's side). Old code: the opening 17, lopsided once spot walks 300 points."""
    import upstox_instruments
    ks = [22000 + 50 * n for n in range(33)]                         # 22,000 .. 23,600, opened at 22,800
    meta = {f"k{k}{s}": (k, s) for k in ks for s in ("ce", "pe")}

    def leg(k, s):
        return {"fullFeed": {"marketFF": {"ltpc": {"ltp": 10.0}, "oi": 1000.0, "vtt": 1.0}}}
    feeds = {key: leg(*who) for key, who in meta.items()}
    feeds["idx"] = {"fullFeed": {"indexFF": {"ltpc": {"ltp": 22500.0}}}}
    src = upstox_chain.UpstoxChainSource.__new__(upstox_chain.UpstoxChainSource)
    src.each_side, src.prev_oi = upstox_instruments.STRIKES_EACH_SIDE, {}
    src.resolved = {"NIFTY": {"idx_key": "idx", "meta": meta}}
    src.feed = type("_F", (), {"connected": True, "last_error": None, "age": lambda self: 1.0,
                               "snapshot": lambda self: feeds})()
    import datetime
    snap = src.poll({"under_sym": "NIFTY"}, "2026-10-20", datetime.datetime(2026, 10, 20, 11, 0))
    got = [r["k"] for r in snap["strikes"]]
    assert got == list(range(22100, 22901, 50)) and snap["atm"] == 22500
    assert upstox_instruments.SUBSCRIBE_EACH_SIDE >= 2 * upstox_instruments.STRIKES_EACH_SIDE


def test_a18_the_socket_is_up_for_0915_and_the_baselines_wait_for_the_0915_bar(monkeypatch):
    """A18: every recorder began at ~09:17 -- the socket waited for the first 1-min index bar (~09:16) to centre its
    strikes, then for ~200 per-leg REST baselines. From 09:14 the prior close centres it; the 09:15 OI baselines are
    fetched once the 09:15 bar exists (from 09:16), by the first poll after it. Before 09:14 nothing changes."""
    import datetime as dt
    import chain_live
    import upstox_feed
    import upstox_instruments
    import upstox_rest
    clock = {"now": dt.datetime(2026, 10, 23, 9, 14, 30, tzinfo=chain_live.IST)}       # a Friday
    monkeypatch.setattr(upstox_chain, "datetime", type("_D", (), {"now": staticmethod(lambda tz=None: clock["now"])}))
    centred, based = [], []
    monkeypatch.setattr(upstox_rest, "intraday", lambda key, tok, interval="1minute": [])          # no bar yet
    monkeypatch.setattr(upstox_rest, "daily_range", lambda key, tok, frm, to, interval="day":
                        [["2026-10-22T00:00:00+05:30", 0, 0, 0, 22811.35, 0, 0]])
    meta = {f"k{k}{s}": (k, s) for k in range(22400, 23201, 50) for s in ("ce", "pe")}
    monkeypatch.setattr(upstox_instruments, "index_key", lambda idx: "idx")
    monkeypatch.setattr(upstox_instruments, "resolve", lambda spot, name, each_side:
                        centred.append(spot) or {"keys": ["idx", *meta], "meta": meta, "expiry": "2026-10-27",
                                                 "idx_key": "idx"})
    monkeypatch.setattr(upstox_rest, "baselines", lambda m, tok, on_error=None: based.append(len(m)) or {})
    feeds = {key: {"fullFeed": {"marketFF": {"ltpc": {"ltp": 10.0}, "oi": 1000.0, "vtt": 1.0}}} for key in meta}
    feeds["idx"] = {"fullFeed": {"indexFF": {"ltpc": {"ltp": 22700.0}}}}

    class Feed:
        connected, last_error = True, None

        def __init__(self, keys, token=None):
            self.keys = keys

        def start(self):
            pass

        def age(self):
            return 1.0

        def snapshot(self):
            return feeds
    monkeypatch.setattr(upstox_feed, "UpstoxFeed", Feed)
    src = upstox_chain.UpstoxChainSource(token="tok")
    assert src.start([{"under_sym": "NIFTY"}]) == {"NIFTY": "2026-10-27"}
    assert centred == [22811.35] and src.feed.keys[0] == "idx" and based == []     # socket up, no baselines yet
    with pytest.raises(RuntimeError, match="wait for the 09:15 bar"):
        src.poll({"under_sym": "NIFTY"}, "2026-10-27", dt.datetime(2026, 10, 23, 9, 15, 30))
    assert based == []
    snap = src.poll({"under_sym": "NIFTY"}, "2026-10-27", dt.datetime(2026, 10, 23, 9, 16, 5))
    assert based == [len(meta)] and snap["atm"] == 22700
    src.poll({"under_sym": "NIFTY"}, "2026-10-27", dt.datetime(2026, 10, 23, 9, 16, 15))
    assert based == [len(meta)]                                                       # once a day
    clock["now"] = dt.datetime(2026, 10, 23, 9, 13, 59, tzinfo=chain_live.IST)
    with pytest.raises(RuntimeError, match="Before 09:15"):                          # overnight: unchanged
        upstox_chain.UpstoxChainSource(token="tok").start([{"under_sym": "NIFTY"}])
    clock["now"] = dt.datetime(2026, 10, 23, 11, 0, tzinfo=chain_live.IST)            # a mid-day start: eager
    centred.clear()
    monkeypatch.setattr(upstox_rest, "intraday", lambda key, tok, interval="1minute":
                        [["2026-10-23T10:59:00+05:30", 22650.0, 22660.0, 22640.0, 22655.0, 0, 0]])
    src2 = upstox_chain.UpstoxChainSource(token="tok")
    src2.start([{"under_sym": "NIFTY"}])
    assert centred == [22655.0] and based == [len(meta), len(meta)] and not src2._deferred
