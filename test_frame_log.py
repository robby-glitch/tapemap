# tapemap/test_frame_log.py
"""One decision record per signature change, write-once, fail-soft."""
import json
import frame_log


def _fr(setup_state="WAITING", wall_state="held", tell_target="23400", missing=None, px=23222.0, window="early", n=1):
    return {"idx": "NIFTY", "ts": "10:00:00",
            "walls": {"rows": [{"p": 23400.0, "kind": "S", "state": wall_state}]},
            "setup": {"state": setup_state, "fire": False,
                      "tells": [{"name": "PIN", "target": tell_target, "negation": "close under 23300", "tag": "I"}]},
            "where": {"px": px}, "trapped": {"window": window}, "taps": [], "missing": missing or [], "n": n}


def test_signature_ignores_raw_counters_and_changes_on_state(tmp_path):
    assert frame_log.sig(_fr(n=1)) == frame_log.sig(_fr(n=2))
    assert frame_log.sig(_fr("WAITING")) != frame_log.sig(_fr("ARMED"))


def test_signature_changes_when_a_wall_row_state_changes():
    assert frame_log.sig(_fr(wall_state="held")) != frame_log.sig(_fr(wall_state="broken"))


def test_signature_changes_when_a_tells_target_changes():
    assert frame_log.sig(_fr(tell_target="23400")) != frame_log.sig(_fr(tell_target="23300"))


def test_signature_ignores_a_walls_basis_drift_but_not_its_state():
    """8 Oct: p = strike + the live basis; signing on p wrote ~650 whole frames that only the basis had moved."""
    a, b = _fr(), _fr()
    a["walls"]["rows"][0].update(p=23450.4, strike=23400.0)
    b["walls"]["rows"][0].update(p=23452.9, strike=23400.0)
    a["setup"]["tells"][0].update(k=23400.0, target="23450")
    b["setup"]["tells"][0].update(k=23400.0, target="23453")
    assert frame_log.sig(a) == frame_log.sig(b)
    b["walls"]["rows"][0]["state"] = "broken"
    assert frame_log.sig(a) != frame_log.sig(b)


def test_signature_changes_when_missing_changes():
    assert frame_log.sig(_fr(missing=[])) != frame_log.sig(_fr(missing=["warmap"]))


def test_signature_ignores_where_px_and_trapped_window():
    assert frame_log.sig(_fr(px=23222.0, window="early")) == frame_log.sig(_fr(px=19999.0, window="late"))


def test_append_only_when_the_signature_changes(tmp_path):
    p = str(tmp_path / "frame_2026-09-11.jsonl")
    frame_log._last_sig.clear()
    assert frame_log.append_if_changed(_fr(), "2026-09-11", path=p) is True
    assert frame_log.append_if_changed(_fr(n=5), "2026-09-11", path=p) is False
    assert frame_log.append_if_changed(_fr("ARMED"), "2026-09-11", path=p) is True
    rows = [json.loads(l) for l in open(p, encoding="utf-8")]
    assert [r["setup"]["state"] for r in rows] == ["WAITING", "ARMED"]
    assert all(r["day"] == "2026-09-11" for r in rows)
    # keyed by (day, idx) -- a second index on the same day must not stomp
    # the first index's cache (Task 1 review finding: was keyed by day alone).
    assert ("2026-09-11", "NIFTY") in frame_log._last_sig
    p2 = str(tmp_path / "frame_2026-09-11_bn.jsonl")
    assert frame_log.append_if_changed(_fr(), "2026-09-11", idx="BANKNIFTY", path=p2) is True


def test_a_signal_transition_is_its_own_record_row(tmp_path):
    """A visit going ARMED -> LIVE with the ladder unchanged used to write no
    row at all, so the scorer had nothing to fill forward cells against."""
    a = _fr()
    a["setup"]["signal"] = {"state": "ARMED", "visit_key": "buy@09:45", "sound": "soft"}
    a["setup"]["votes"] = {"n": 0, "passed": False}
    b = _fr()
    b["setup"]["signal"] = {"state": "LIVE", "visit_key": "buy@09:45", "sound": "firm"}
    b["setup"]["votes"] = {"n": 1, "passed": True}
    assert frame_log.sig(a) != frame_log.sig(b)
    p = str(tmp_path / "frame_2026-09-18.jsonl")
    frame_log._last_sig.clear()
    assert frame_log.append_if_changed(a, "2026-09-18", path=p) is True
    assert frame_log.append_if_changed(b, "2026-09-18", path=p) is True
    assert frame_log.append_if_changed(b, "2026-09-18", path=p) is False
    assert sum(1 for _ in open(p, encoding="utf-8")) == 2
