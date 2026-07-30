"""Guards for the 2026-07-30 chain freeze: dhan.option_chain() hung inside a
network call with no exception, so the poller wrote 71 snapshots then froze
at 09:29:58 while the tape kept ticking and nothing reached tapemap.log --
95 minutes of chain history lost. `_with_deadline` bounds any such call on a
wall clock (the SDK has no deadline= of its own, mirroring the 2026-07-27
fix in instruments.fetch_bytes), and `built_at` gives the UI a machine-
readable heartbeat to detect the freeze itself, should it recur."""
import json
import time

import pytest

from chain_live import ChainPoller, _with_deadline


def _snap(sec=34000, spot=24000.0):
    side = {"ltp": 50.0, "oi": 100_000, "oi_chg": 0, "iv": 0.12, "vol": 100,
            "bid": 49.9, "ask": 50.1, "avg": None, "gamma": None, "delta": None}
    return {"ts": "09:30:00", "sec": sec, "spot": spot, "atm": 24000,
            "strikes": [{"k": 24000, "ce": side, "pe": side}]}


def test_with_deadline_returns_value_when_fast():
    assert _with_deadline(lambda: 42, 1.0, "fast call") == 42


def test_with_deadline_raises_timeout_when_slow():
    def slow():
        time.sleep(2)
        return 1

    t0 = time.time()
    with pytest.raises(TimeoutError):
        _with_deadline(slow, 0.2, "slow call")
    # the poll loop must never be blocked past the deadline, even though the
    # hung worker thread (daemon=True) is left running behind it
    assert time.time() - t0 < 1.0


def test_with_deadline_propagates_exception():
    def boom():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        _with_deadline(boom, 1.0, "boom call")


def test_published_payload_has_numeric_built_at_and_unchanged_ts():
    poller = ChainPoller([{"under_sym": "TEST"}], mock=True)
    snap = _snap()
    metrics = poller.states["TEST"].update(snap, 0.004, None)
    t0 = time.time()
    poller._publish("TEST", snap, metrics, "2026-07-30", "live")
    t1 = time.time()
    pl = json.loads(poller.boxes["TEST"]["payload"])
    assert pl["ts"] == "09:30:00"
    assert isinstance(pl["built_at"], (int, float))
    assert t0 <= pl["built_at"] <= t1


def test_tag_error_does_not_advance_built_at():
    poller = ChainPoller([{"under_sym": "TEST"}], mock=True)
    snap = _snap()
    metrics = poller.states["TEST"].update(snap, 0.004, None)
    poller._publish("TEST", snap, metrics, "2026-07-30", "live")
    before = json.loads(poller.boxes["TEST"]["payload"])["built_at"]

    time.sleep(0.05)
    poller._tag_error("TEST", "live", "poll failed: boom")

    after = json.loads(poller.boxes["TEST"]["payload"])
    assert after["built_at"] == before          # stale payload must stay stale
    assert after["error"] == "poll failed: boom"
