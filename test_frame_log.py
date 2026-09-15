# tapemap/test_frame_log.py
"""One decision record per signature change, write-once, fail-soft."""
import json
import frame_log


def _fr(zone="WAITING", n=1):
    return {"idx": "NIFTY", "ts": "10:00:00", "ladder": {"rows": [{"p": 23400.0, "kind": "S", "state": "held"}]},
            "zone": {"state": zone, "fire": False}, "watch": {"tells": []}, "missing": [], "n": n}


def test_signature_ignores_raw_counters_and_changes_on_state(tmp_path):
    assert frame_log.sig(_fr(n=1)) == frame_log.sig(_fr(n=2))
    assert frame_log.sig(_fr("WAITING")) != frame_log.sig(_fr("ARMED"))


def test_append_only_when_the_signature_changes(tmp_path):
    p = str(tmp_path / "frame_2026-09-11.jsonl")
    frame_log._last_sig.clear()
    assert frame_log.append_if_changed(_fr(), "2026-09-11", path=p) is True
    assert frame_log.append_if_changed(_fr(n=5), "2026-09-11", path=p) is False
    assert frame_log.append_if_changed(_fr("ARMED"), "2026-09-11", path=p) is True
    rows = [json.loads(l) for l in open(p, encoding="utf-8")]
    assert [r["zone"]["state"] for r in rows] == ["WAITING", "ARMED"]
    assert all(r["day"] == "2026-09-11" for r in rows)
    # keyed by (day, idx) -- a second index on the same day must not stomp
    # the first index's cache (Task 1 review finding: was keyed by day alone).
    assert ("2026-09-11", "NIFTY") in frame_log._last_sig
    p2 = str(tmp_path / "frame_2026-09-11_bn.jsonl")
    assert frame_log.append_if_changed(_fr(), "2026-09-11", idx="BANKNIFTY", path=p2) is True
