"""5 Nov: the chain's strike window froze at the edge of the strikes subscribed at the open (NIFTY 23950-24750,
SENSEX 77300-78900 with spot at 79,400), so the second half's call writers were never recorded. The window must
follow spot past that edge: re-resolve, subscribe the new legs on the open socket, keep them for a reconnect."""
import datetime
import json

import upstox_chain
import upstox_feed
import upstox_instruments


def _meta(lo, hi):
    return {f"k{k}{s}": (k, s) for k in range(lo, hi + 1, 50) for s in ("ce", "pe")}


def _leg():
    return {"fullFeed": {"marketFF": {"ltpc": {"ltp": 10.0}, "oi": 1000.0, "vtt": 1.0}}}


def test_window_follows_spot_past_the_subscribed_edge(monkeypatch):
    opened = _meta(21600, 23200)                                    # +/- 16 around a 22,400 prior close
    wide = _meta(22100, 23700)                                      # +/- 16 around the live 22,900
    feeds = {key: _leg() for key in {**opened, **wide}}
    feeds["idx"] = {"fullFeed": {"indexFF": {"ltpc": {"ltp": 22900.0}}}}
    calls, added = [], []
    monkeypatch.setattr(upstox_instruments, "resolve", lambda spot, name, each_side:
                        calls.append((spot, each_side)) or {"meta": wide, "expiry": "2026-11-10"})

    class Feed:
        connected, last_error = True, None

        def age(self):
            return 1.0

        def snapshot(self):
            return feeds

        def add(self, keys):
            added.extend(keys)

    src = upstox_chain.UpstoxChainSource.__new__(upstox_chain.UpstoxChainSource)
    src.each_side, src.sub_each_side, src.prev_oi = 8, 16, {}
    src.resolved = {"NIFTY": {"idx_key": "idx", "meta": dict(opened), "expiry": "2026-11-10"}}
    src.feed = Feed()
    now = datetime.datetime(2026, 11, 5, 13, 40)
    snap = src.poll({"under_sym": "NIFTY"}, "2026-11-10", now)
    assert [r["k"] for r in snap["strikes"]] == list(range(22500, 23301, 50))   # 17 around spot, not the edge's
    assert calls == [(22900.0, 16)]
    assert sorted({opened.get(k) or wide[k] for k in added}) == [(k, s) for k in range(23250, 23701, 50)
                                                                  for s in ("ce", "pe")]
    src.poll({"under_sym": "NIFTY"}, "2026-11-10", now)              # inside the wider window: no second look
    assert len(calls) == 1


def test_no_widen_across_an_expiry_roll(monkeypatch):
    opened = _meta(21600, 23200)
    feeds = {key: _leg() for key in opened}
    feeds["idx"] = {"fullFeed": {"indexFF": {"ltpc": {"ltp": 23100.0}}}}
    monkeypatch.setattr(upstox_instruments, "resolve", lambda spot, name, each_side:
                        {"meta": _meta(22300, 23900), "expiry": "2026-11-17"})
    added = []
    src = upstox_chain.UpstoxChainSource.__new__(upstox_chain.UpstoxChainSource)
    src.each_side, src.sub_each_side, src.prev_oi = 8, 16, {}
    src.resolved = {"NIFTY": {"idx_key": "idx", "meta": dict(opened), "expiry": "2026-11-10"}}
    src.feed = type("_F", (), {"connected": True, "last_error": None, "age": lambda self: 1.0,
                               "snapshot": lambda self: feeds, "add": lambda self, k: added.extend(k)})()
    src.poll({"under_sym": "NIFTY"}, "2026-11-10", datetime.datetime(2026, 11, 5, 14, 0))
    assert added == [] and len(src.resolved["NIFTY"]["meta"]) == len(opened)


def test_feed_add_subscribes_new_keys_on_the_open_socket_and_keeps_them():
    sent = []
    f = upstox_feed.UpstoxFeed(["a"], token="t")
    f._ws, f.connected = type("_W", (), {"send_binary": lambda self, b: sent.append(json.loads(b))})(), True
    assert f.add(["a", "b"]) == ["b"] and f.keys == ["a", "b"]
    assert sent[0]["method"] == "sub" and sent[0]["data"]["instrumentKeys"] == ["b"]
    f.connected = False
    assert f.add(["c"]) == ["c"] and f.keys == ["a", "b", "c"] and len(sent) == 1   # the reconnect subscribes it
