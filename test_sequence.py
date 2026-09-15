"""sequence.py -- the playbook machine walks the thesis, logs its own
population, and stays in shadow. Positive transitions are asserted first."""

import json
from datetime import datetime

import sequence

IN_HOURS = datetime(2026, 8, 21, 10, 30)       # a Friday, mid-session
OFF_HOURS = datetime(2026, 8, 22, 10, 30)      # a Saturday

LEVELS = [
    {"kind": "PDL", "px": 25000.0, "stable": True},
    {"kind": "PDH", "px": 25300.0, "stable": True},
    {"kind": "ROUND", "px": 24800.0, "stable": True},
    {"kind": "MAX_PAIN", "px": 25100.0, "stable": False},
]

QUIET = {"active": False}


def _dwell_at(kind, px):
    return {"active": True, "holding": True, "level": {"kind": kind, "px": px},
            "oi_added_ce": 0, "oi_added_pe": 4000, "buyers_crossing": 0.8}


def test_shadow_is_asserted_not_hoped():
    assert sequence.SHADOW is True


def test_approach_then_reject_counts_a_test(tmp_path):
    s = sequence.Sequencer("NIFTY", path=str(tmp_path / "w.jsonl"))
    band = 10.0
    s.on_snapshot(25500.0, band, LEVELS, QUIET, now=IN_HOURS)   # far
    s.on_snapshot(25015.0, band, LEVELS, QUIET, now=IN_HOURS)   # approach
    fired = s.on_snapshot(25500.0, band, LEVELS, QUIET, now=IN_HOURS)
    tos = [f["to"] for f in fired]
    assert "REJECT" in tos
    st = s.state()["PDL@25000.0"]
    assert st["tests"] == 1 and st["last_outcome"] == "REJECT"


def test_the_full_playbook_dwell_break_run_hit(tmp_path):
    path = tmp_path / "w.jsonl"
    s = sequence.Sequencer("NIFTY", path=str(path))
    band = 10.0
    s.on_snapshot(25015.0, band, LEVELS, QUIET, now=IN_HOURS)          # approach from above
    fired = s.on_snapshot(25005.0, band, LEVELS,
                          _dwell_at("PDL", 25000.0), now=IN_HOURS)     # the trap loads
    assert [f["to"] for f in fired] == ["DWELL"]
    fired = s.on_snapshot(24960.0, band, LEVELS, QUIET, now=IN_HOURS)  # through it
    tos = [f["to"] for f in fired]
    assert tos[:2] == ["BREAK", "RUN"]
    run = [f for f in fired if f["to"] == "RUN"][0]
    assert run["target"] == {"kind": "ROUND", "px": 24800.0}           # named ahead
    fired = s.on_snapshot(24805.0, band, LEVELS, QUIET, now=IN_HOURS)  # reaches it
    assert [f["to"] for f in fired if f["level"] == "PDL"] == ["HIT"]
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    assert all(r["idx"] == "NIFTY" for r in rows)
    assert s.written == len(rows) and s.failed == 0


def test_a_failed_run_comes_back_through_the_level(tmp_path):
    s = sequence.Sequencer("NIFTY", path=str(tmp_path / "w.jsonl"))
    band = 10.0
    s.on_snapshot(25015.0, band, LEVELS, QUIET, now=IN_HOURS)
    s.on_snapshot(24960.0, band, LEVELS, QUIET, now=IN_HOURS)          # break + run
    fired = s.on_snapshot(25050.0, band, LEVELS, QUIET, now=IN_HOURS)  # back through
    assert "FAILED" in [f["to"] for f in fired if f["level"] == "PDL"]


def test_drifting_levels_get_no_machine_and_off_hours_writes_nothing(tmp_path):
    path = tmp_path / "w.jsonl"
    s = sequence.Sequencer("NIFTY", path=str(path))
    fired = s.on_snapshot(25095.0, 10.0, LEVELS, QUIET, now=OFF_HOURS)
    assert all(f["level"] != "MAX_PAIN" for f in fired)
    assert "MAX_PAIN@25100.0" not in s.state()
    # the transition still FIRES (state is real); only the ledger is gated
    assert not path.exists() and s.written == 0
