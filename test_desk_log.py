"""desk_log.py -- the market-hours gate, the fail-soft write, and the
transition diff, in isolation from the senses loop that drives them live.
"""
import json
from datetime import datetime

import desk_log as DL

# A Monday, safely inside 09:15-15:30.
IN_HOURS = datetime(2026, 8, 24, 11, 0, 0)


# --------------------------------------------------------------------------
# the market-hours gate
# --------------------------------------------------------------------------

def test_market_hours_true_inside_the_window_on_a_weekday():
    assert DL.market_hours(IN_HOURS)


def test_market_hours_false_one_minute_before_open():
    assert not DL.market_hours(datetime(2026, 8, 24, 9, 14, 0))


def test_market_hours_true_at_the_open_boundary():
    assert DL.market_hours(datetime(2026, 8, 24, 9, 15, 0))


def test_market_hours_true_at_the_close_boundary():
    assert DL.market_hours(datetime(2026, 8, 24, 15, 30, 0))


def test_market_hours_false_one_minute_after_close():
    assert not DL.market_hours(datetime(2026, 8, 24, 15, 31, 0))


def test_market_hours_false_on_saturday():
    # 2026-08-22 is a Saturday.
    assert not DL.market_hours(datetime(2026, 8, 22, 11, 0, 0))


def test_market_hours_false_on_sunday():
    assert not DL.market_hours(datetime(2026, 8, 23, 11, 0, 0))


# --------------------------------------------------------------------------
# the gate applies to both writers, and is injectable (constraint 6) --
# a caller (or a test) hands `now` in rather than the module reading the
# wall clock, so a --mock-chain run at any hour can still drive the real
# write path.
# --------------------------------------------------------------------------

def test_log_surface_writes_nothing_outside_market_hours(tmp_path):
    path = str(tmp_path / "surface.jsonl")
    off_hours = datetime(2026, 8, 24, 20, 0, 0)
    wrote = DL.log_surface("NIFTY", 0.15, -0.02, 0.5, 0.01, "future",
                           "2026-08-27", 12, now=off_hours, path=path)
    assert wrote is False
    assert not (tmp_path / "surface.jsonl").exists()


def test_log_transition_writes_nothing_outside_market_hours(tmp_path):
    path = str(tmp_path / "desk_log.jsonl")
    off_hours = datetime(2026, 8, 24, 20, 0, 0)
    wrote = DL.log_transition("NIFTY", "gear", None, "CASCADE",
                              now=off_hours, path=path)
    assert wrote is False
    assert not (tmp_path / "desk_log.jsonl").exists()


# --------------------------------------------------------------------------
# a successful write, and its exact shape
# --------------------------------------------------------------------------

def test_log_surface_row_shape(tmp_path):
    path = str(tmp_path / "surface.jsonl")
    assert DL.log_surface("NIFTY", 0.155, -0.021, 0.48, 0.011, "future",
                          "2026-08-27", 42, now=IN_HOURS, path=path)
    row = json.loads((tmp_path / "surface.jsonl").read_text().strip())
    assert set(row) == {"ts", "idx", "a", "b", "c", "rmse", "f_src",
                        "expiry", "n_points"}
    assert row["idx"] == "NIFTY" and row["n_points"] == 42
    assert row["a"] == 0.155 and row["f_src"] == "future"
    # No outcome, no hit rate, no fabricated field -- constraint 2/3.
    assert "outcome" not in row and "hit" not in row and "score" not in row


def test_log_transition_row_shape(tmp_path):
    path = str(tmp_path / "desk_log.jsonl")
    assert DL.log_transition("NIFTY", "gear", "TRANSITION", "CASCADE",
                             detail="NIFTY gear: TRANSITION -> CASCADE",
                             now=IN_HOURS, path=path)
    row = json.loads((tmp_path / "desk_log.jsonl").read_text().strip())
    assert set(row) == {"ts", "idx", "field", "from", "to", "detail"}
    assert row["field"] == "gear"
    assert row["from"] == "TRANSITION" and row["to"] == "CASCADE"
    # Never an outcome, never a hit/win rate (constraint 2).
    assert "outcome" not in row and "hit" not in row and "won" not in row


def test_appended_lines_accumulate_one_json_object_per_line(tmp_path):
    path = str(tmp_path / "desk_log.jsonl")
    DL.log_transition("NIFTY", "gear", None, "PIN", now=IN_HOURS, path=path)
    DL.log_transition("NIFTY", "gear", "PIN", "CASCADE", now=IN_HOURS,
                      path=path)
    lines = (tmp_path / "desk_log.jsonl").read_text().splitlines()
    assert len(lines) == 2
    rows = [json.loads(l) for l in lines]
    assert [r["to"] for r in rows] == ["PIN", "CASCADE"]


# --------------------------------------------------------------------------
# fail-soft, mirroring senses.py's own discipline
# --------------------------------------------------------------------------

def test_a_write_failure_does_not_raise(tmp_path):
    """A path that cannot be opened for writing -- here, a directory sitting
    where the log file needs to go -- must cost a False return, never an
    exception. The loop that calls this must never die for a log line."""
    blocker = tmp_path / "blocked"
    blocker.mkdir()                      # a directory, not a file
    bad_path = str(blocker)              # open(bad_path, "a") cannot succeed
    assert DL.log_surface("NIFTY", 0.1, 0.0, 0.4, 0.02, "future",
                          "2026-08-27", 10, now=IN_HOURS, path=bad_path) is False
    assert DL.log_transition("NIFTY", "gear", "PIN", "CASCADE",
                             now=IN_HOURS, path=bad_path) is False


# --------------------------------------------------------------------------
# diff_transitions -- pure, no I/O
# --------------------------------------------------------------------------

def test_diff_transitions_reports_only_changed_fields():
    prev = {"gear": "PIN", "conviction": "NONE", "deployable": None}
    curr = {"gear": "CASCADE", "conviction": "NONE", "deployable": "long_call"}
    out = DL.diff_transitions(prev, curr)
    assert ("gear", "PIN", "CASCADE") in out
    assert ("deployable", None, "long_call") in out
    assert not any(f == "conviction" for f, _, _ in out)


def test_diff_transitions_first_reading_is_a_transition_from_none():
    """No prior state at all -- the first observed reading still counts,
    from None, rather than being suppressed as 'nothing to compare against'."""
    out = DL.diff_transitions({}, {"gear": "PIN", "conviction": "NONE",
                                   "deployable": None})
    assert ("gear", None, "PIN") in out
    assert ("conviction", None, "NONE") in out
    # deployable stayed None -> None: genuinely unchanged, not a transition.
    assert not any(f == "deployable" for f, _, _ in out)


def test_diff_transitions_reports_nothing_when_nothing_changed():
    state = {"gear": "PIN", "conviction": "NONE", "deployable": None}
    assert DL.diff_transitions(state, dict(state)) == []
