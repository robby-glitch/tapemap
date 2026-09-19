"""tape_log.py: the ladder record (spec §C). Write-once per bar and per mark; a
restart seeds from the file; forming is never written; fail-soft."""
import json
import os

import pytest

import tape_log


def _doc(n=3, ladder=True, forming=True, events=None):
    bars = []
    for i in range(n):
        b = {"t": 1789726200000 + i * 300000, "o": 23380 + i, "h": 23384 + i, "l": 23376 + i, "c": 23381 + i,
             "vol": 10 + i, "buy": 6, "sell": 4 + i, "delta": 2 - i, "oi": 17670380, "fromTicks": True}
        if ladder:
            b["ladder"] = [{"p": 23380.0 + i, "b": 4, "s": 2, "bt": 3, "st": 2}, {"p": 23381.0 + i, "b": 2, "s": 2, "bt": 1, "st": 1}]
        bars.append(b)
    return {"kind": "frame", "session": "NIFTY-I|5m|2026-09-19", "idx": "NIFTY", "interval": 5,
            "closed": bars,
            "forming": {"t": 1789726200000 + n * 300000, "o": 1, "h": 2, "l": 0, "c": 1, "vol": 1, "delta": 1, "buy": 1, "sell": 0,
                        "ladder": [{"p": 1.0, "b": 1, "s": 0, "bt": 1, "st": 0}]} if forming else None,
            "events": events if events is not None else [{"t": 1789726200000, "kind": "absorption", "side": 1, "p": 23380.0, "size": 120}],
            "rowSize": 5, "rowAnchor": 0, "lot": 65, "futPx": 23381.0}


@pytest.fixture
def tdir(tmp_path, monkeypatch):
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path))
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    return tmp_path


def _lines(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def test_append_writes_each_closed_bar_once_with_its_ladder(tdir):
    n = tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    assert n == {"bars": 3, "marks": 1}
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert [r["t"] for r in rows] == [1789726200000, 1789726500000, 1789726800000]
    assert rows[0]["ladder"][0] == {"p": 23380.0, "b": 4, "s": 2, "bt": 3, "st": 2}
    for k in ("rowSize", "rowAnchor", "lot", "session", "idx", "day", "fromTicks"):
        assert k in rows[0], k
    assert rows[0]["day"] == "2026-09-19" and rows[0]["idx"] == "NIFTY" and rows[0]["rowSize"] == 5


def test_the_same_post_again_writes_nothing(tdir):
    tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    assert tape_log.append(_doc(3), "2026-09-19", "NIFTY") == {"bars": 0, "marks": 0}
    assert len(_lines(tape_log.day_path("2026-09-19", "NIFTY"))) == 3


def test_a_new_bar_on_a_later_post_is_appended(tdir):
    tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    assert tape_log.append(_doc(4), "2026-09-19", "NIFTY") == {"bars": 1, "marks": 0}


def test_a_restart_seeds_the_seen_set_from_the_file(tdir):
    tape_log.append(_doc(3), "2026-09-19", "NIFTY")
    tape_log._seen_bars.clear()          # a new process
    tape_log._seen_marks.clear()
    assert tape_log.append(_doc(3), "2026-09-19", "NIFTY") == {"bars": 0, "marks": 0}
    assert len(_lines(tape_log.day_path("2026-09-19", "NIFTY"))) == 3


def test_forming_is_never_written(tdir):
    tape_log.append(_doc(2, forming=True), "2026-09-19", "NIFTY")
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert all(r["t"] != 1789726200000 + 2 * 300000 for r in rows)


def test_a_bar_without_a_ladder_is_written_with_null(tdir):
    tape_log.append(_doc(1, ladder=False), "2026-09-19", "NIFTY")
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert rows[0]["ladder"] is None


def test_marks_are_written_once_by_t_kind_p_side(tdir):
    ev = [{"t": 1789726200000, "kind": "absorption", "side": 1, "p": 23380.0, "size": 120},
          {"t": 1789726200000, "kind": "absorption", "side": 1, "p": 23380.0, "size": 999},   # same identity
          {"t": 1789726200000, "kind": "absorption", "side": -1, "p": 23380.0, "size": 5}]    # other side: new
    n = tape_log.append(_doc(1, events=ev), "2026-09-19", "NIFTY")
    assert n["marks"] == 2
    rows = _lines(tape_log.marks_path("2026-09-19", "NIFTY"))
    assert [r["side"] for r in rows] == [1, -1] and rows[0]["src"] == "ofd" and rows[0]["size"] == 120


def test_readers_return_file_order_and_prior_days_newest_first(tdir):
    for day in ("2026-09-15", "2026-09-17", "2026-09-18"):
        tape_log._seen_bars.clear()
        tape_log.append(_doc(2), day, "NIFTY")
    assert [r["t"] for r in tape_log.read_bars("2026-09-17", "NIFTY")] == [1789726200000, 1789726500000]
    assert tape_log.read_bars("2026-09-16", "NIFTY") == []
    assert tape_log.prior_days("2026-09-18", "NIFTY", n=5) == ["2026-09-17", "2026-09-15"]
    assert tape_log.prior_days("2026-09-18", "NIFTY", n=1) == ["2026-09-17"]
    assert tape_log.read_marks("2026-09-18", "NIFTY")[0]["kind"] == "absorption"


def test_a_torn_last_line_is_skipped_never_fatal(tdir):
    tape_log.append(_doc(2), "2026-09-19", "NIFTY")
    with open(tape_log.day_path("2026-09-19", "NIFTY"), "a", encoding="utf-8") as f:
        f.write('{"t": 1789727100000, "o": 1')          # the process died mid-write
    assert len(tape_log.read_bars("2026-09-19", "NIFTY")) == 2
    tape_log._seen_bars.clear()
    assert tape_log.append(_doc(2), "2026-09-19", "NIFTY")["bars"] == 0


def test_a_disk_error_is_counted_and_never_raised(tdir, monkeypatch):
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(tape_log, "_write_lines", boom)
    before = tape_log.failed
    assert tape_log.append(_doc(2), "2026-09-19", "NIFTY") == {"bars": 0, "marks": 0}
    assert tape_log.failed == before + 3      # 2 bars + 1 mark


def test_under_pytest_the_record_dir_is_never_the_live_one(tmp_path):
    """conftest.py's autouse fixture: a test that forgets to redirect DIR still
    cannot write into data/tape/ (the 2026-09-19 leak)."""
    assert tape_log.DIR.startswith(str(tmp_path))
    assert not os.path.normpath(tape_log.DIR).endswith(os.path.join("data", "tape"))
