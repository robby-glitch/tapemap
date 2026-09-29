"""The anytime-start rule, at the chain poller.

`server.py`'s senses loop gates the war map, the drag board, the OI ladder,
trapped writers and the paper tick on a chain payload with `ok:true`. The
poller only publishes inside 09:15-15:30, and `_warm_start` used to rebuild
`ChainState` from `data/chain/chain_<IDX>_<day>.jsonl` while publishing
nothing -- so a start after the close, over a weekend or straight after a
crash left every one of those boards dead, in the same process and at the same
moment that `/api/oiflow` served the whole day correctly out of
`poller.states[idx].minutes`. That asymmetry was the bug.

A warm start now publishes the last replayed snapshot. It is a
RECONSTRUCTION, so it carries `mode="restored"` and an `error` naming both
facts, and a later live payload replaces it outright rather than merging with
it -- an observation is never blended with a rebuild.
"""
import json

from chain_live import ChainPoller

DAY = "2026-09-18"
EXPIRY = "2026-09-25"


def _side(ltp, oi):
    return {"ltp": ltp, "oi": oi, "oi_chg": 0, "iv": 0.12, "vol": 100,
            "bid": ltp - 0.1, "ask": ltp + 0.1, "avg": None,
            "gamma": None, "delta": None}


def _snap(ts, spot, ks=(24000, 24100), ltp=50.0, oi=100_000):
    hh, mm, ss = (int(x) for x in ts.split(":"))
    return {"ts": ts, "sec": hh * 3600 + mm * 60 + ss, "spot": spot,
            "atm": 24000,
            "strikes": [{"k": k, "ce": _side(ltp, oi), "pe": _side(ltp, oi)}
                        for k in ks]}


def _day_file(tmp_path, snaps):
    p = tmp_path / f"chain_TEST_{DAY}.jsonl"
    p.write_text("".join(json.dumps(s) + "\n" for s in snaps), encoding="utf-8")
    return p


def _poller(spy=None):
    poller = ChainPoller([{"under_sym": "TEST"}], mock=True)
    # `_kick_backfill` fires ~34 REST calls per index against the live broker.
    # A test has no business on the network; the one-shot guard is the door
    # the poller itself uses, so use it rather than patching the method out.
    poller._backfilled.add("TEST")
    if spy is not None:
        orig = poller._publish

        def wrapped(idx, snap, metrics, expiry, mode, error=None):
            spy.append({"idx": idx, "snap": snap, "mode": mode, "error": error})
            return orig(idx, snap, metrics, expiry, mode, error)

        poller._publish = wrapped
    return poller


def test_warm_start_publishes_the_last_replayed_snapshot_once_as_restored(tmp_path):
    snaps = [_snap("09:20:00", 24010.0), _snap("09:21:00", 24020.0),
             _snap("09:22:00", 24030.0)]
    calls = []
    poller = _poller(calls)

    poller._warm_start("TEST", _day_file(tmp_path, snaps), EXPIRY)

    assert len(calls) == 1, "a warm start publishes exactly once"
    assert calls[0]["mode"] == "restored"
    # Read back off disk, so equal content rather than the same object.
    assert calls[0]["snap"] == snaps[-1], "the LAST replayed snapshot, not the first"

    doc = json.loads(poller.boxes["TEST"]["payload"])
    assert doc["ok"] is True                      # the senses-loop gate opens
    assert doc["mode"] == "restored"
    assert doc["ts"] == "09:22:00"
    assert doc["spot"] == 24030.0
    # Distinguishable at every consumer: the mode alone is not enough, the
    # sentence has to say the market was closed AND that this was rebuilt.
    assert "rebuilt from persisted snapshots" in doc["error"]
    # The spot rides outside the bytes too -- `frame.basis` reads it there, and
    # `_publish` is its only writer, which is why the OI ladder died with it.
    assert poller.boxes["TEST"]["spot"] == 24030.0
    assert poller.boxes["TEST"]["mode"] == "restored"


def test_a_live_publish_replaces_the_restored_one_rather_than_merging(tmp_path):
    snaps = [_snap("09:20:00", 24010.0), _snap("09:21:00", 24020.0)]
    poller = _poller()
    poller._warm_start("TEST", _day_file(tmp_path, snaps), EXPIRY)
    assert json.loads(poller.boxes["TEST"]["payload"])["mode"] == "restored"

    live = _snap("13:05:00", 24500.0, ks=(24500,))
    metrics = poller.states["TEST"].update(live, 0.004, poller.prevs["TEST"])
    poller._publish("TEST", live, metrics, EXPIRY, "live")

    doc = json.loads(poller.boxes["TEST"]["payload"])
    assert doc["mode"] == "live"
    assert doc["error"] is None, "the restored sentence must not survive"
    assert doc["ts"] == "13:05:00"
    assert doc["spot"] == 24500.0
    assert [s["k"] for s in doc["strikes"]] == [24500], \
        "the live snapshot replaces the restored one; the two are never pooled"
    assert poller.boxes["TEST"]["mode"] == "live"


def test_no_day_file_publishes_nothing(tmp_path):
    """Absence is not a reconstruction: with nothing replayed there is nothing
    to restore, and an empty publish would be an invention."""
    calls = []
    poller = _poller(calls)

    poller._warm_start("TEST", tmp_path / f"chain_TEST_{DAY}.jsonl", EXPIRY)

    assert calls == []
    assert poller.boxes["TEST"]["payload"] is None


def test_a_republish_keeps_the_per_strike_columns(tmp_path):
    """`_publish` pops "per_strike" off the metrics it is handed, and the
    closed-market tick republishes the SAME metrics every 30 s until the
    boards seed. Without a copy the second pass would blank ce_w/pe_w/gex and
    the war map's heat with it."""
    snaps = [_snap("09:20:00", 24010.0), _snap("09:21:00", 24020.0)]
    poller = _poller()
    poller._warm_start("TEST", _day_file(tmp_path, snaps), EXPIRY)
    first = json.loads(poller.boxes["TEST"]["payload"])["strikes"]

    poller._publish_restored("TEST")
    again = json.loads(poller.boxes["TEST"]["payload"])["strikes"]

    assert [s["ce_w"] for s in again] == [s["ce_w"] for s in first]
    assert [s["ce_pk"] for s in again] == [s["ce_pk"] for s in first]
    assert all(s["ce_pk"] is not None for s in again)


def test_the_chain_row_names_its_own_contract():
    """P1-04: the day-file row carries the underlying's key and the expiry it was polled on;
    without an Upstox source (Dhan, mock) the key is null. The snapshot itself is unchanged."""
    poller = _poller()
    snap = _snap("09:20:00", 24010.0)
    assert poller._stamped("TEST", snap, EXPIRY) == {**snap, "ik": None, "expiry": EXPIRY}

    class Src:
        resolved = {"TEST": {"idx_key": "NSE_INDEX|Nifty 50"}}
    poller.src = Src()
    row = poller._stamped("TEST", snap, EXPIRY)
    assert row["ik"] == "NSE_INDEX|Nifty 50" and row["expiry"] == EXPIRY and row["strikes"] == snap["strikes"]
    assert "ik" not in snap
