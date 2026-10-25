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


def test_a_bar_that_is_not_a_bar_is_skipped_and_the_rest_are_written(tdir):
    """The extension posts what GoCharting hands it. A non-dict entry, or a `t`
    that is not a number, used to raise INSIDE the POST handler and flip the
    whole frame POST's ok to False -- one bad entry cost the day."""
    doc = _doc(2)
    doc["closed"] = [doc["closed"][0], "not a bar", None, {"t": "abc", "o": 1}, doc["closed"][1]]
    assert tape_log.append(doc, "2026-09-19", "NIFTY") == {"bars": 2, "marks": 1}
    assert [r["t"] for r in _lines(tape_log.day_path("2026-09-19", "NIFTY"))] == [1789726200000, 1789726500000]


def test_a_numeric_string_t_is_not_a_bar(tdir):
    """bar_t() must accept only int/float -- a numeric string `t` (e.g. what a
    JSON round-trip through some other layer could hand back) is not a bar's
    clock and must be skipped, not silently coerced by `int()`."""
    doc = _doc(2)
    doc["closed"][0]["t"] = "1757563500000"
    assert tape_log.append(doc, "2026-09-19", "NIFTY") == {"bars": 1, "marks": 1}
    assert [r["t"] for r in _lines(tape_log.day_path("2026-09-19", "NIFTY"))] == [1789726500000]


def test_a_corrupt_row_in_the_file_does_not_break_the_restart_seed(tdir):
    tape_log.append(_doc(2), "2026-09-19", "NIFTY")
    with open(tape_log.day_path("2026-09-19", "NIFTY"), "a", encoding="utf-8") as f:
        f.write('{"t": "abc", "o": 1}\n{"o": 2}\n')     # rows with no usable clock
    tape_log._seen_bars.clear()                          # a new process
    tape_log._seen_marks.clear()
    assert tape_log.append(_doc(3), "2026-09-19", "NIFTY")["bars"] == 1      # the two real ones are still seen
    assert [r.get("t") for r in tape_log.read_bars("2026-09-19", "NIFTY")][-1:] == [1789726800000]


def test_an_event_with_an_empty_kind_is_not_a_mark(tdir):
    """`kind: ""` is not a kind. The writer and server._tape_reply share one
    filter (tape_log.keep_mark) so the file and the wire cannot hold two
    different populations under one name."""
    ev = [{"t": 1789726200000, "kind": "", "side": 1, "p": 23380.0, "size": 1},
          {"t": 1789726200000, "kind": "absorption", "side": 1, "p": 23380.0, "size": 2}]
    assert tape_log.append(_doc(1, events=ev), "2026-09-19", "NIFTY")["marks"] == 1
    assert [r["kind"] for r in _lines(tape_log.marks_path("2026-09-19", "NIFTY"))] == ["absorption"]
    assert tape_log.keep_mark(ev[0]) is False and tape_log.keep_mark(ev[1]) is True


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


def test_a_tape_row_declares_no_contract_and_says_why(tdir):
    """P1-04: GoCharting's continuous NIFTY-I bars never carry Upstox's contract."""
    tape_log.append(_doc(1), "2026-09-19", "NIFTY")
    r = _lines(tape_log.day_path("2026-09-19", "NIFTY"))[0]
    assert r["ik"] is None and r["ik_why"] == "GoCharting continuous NIFTY-I; contract not declared"


def _days(*days):
    for day in days:
        tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
        tape_log.append(_doc(2), day, "NIFTY")


def test_the_roll_cuts_prior_days_at_the_expired_futures_expiry(tdir):
    """P1-03: 22-29 Sep are the Sep contract's prices; 30 Sep is the Oct contract's, off by the
    calendar spread. On 30 Sep nothing is pooled and the why says so; 1 Oct pools 30 Sep alone."""
    _days("2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30")
    assert tape_log.prior_days("2026-09-30", "NIFTY", 5, after="2026-09-29") == []
    days, why = tape_log.prior_pool("2026-09-30", "NIFTY", 5, after="2026-09-29")
    assert days == [] and why == "the Sep future expired 29 Sep; earlier days are another contract"
    days, why = tape_log.prior_pool("2026-10-01", "NIFTY", 5, after="2026-09-29")
    assert days == ["2026-09-30"] and why.startswith("the Sep future expired 29 Sep")
    assert tape_log.prior_pool("2026-10-01", "NIFTY", 5) == (["2026-09-30", "2026-09-29", "2026-09-28", "2026-09-25", "2026-09-24"], None)


def test_prior_days_need_todays_contract_once_the_dump_forgets_the_expiry(tdir):
    """P1-03, from 1 Oct: the dump no longer lists the Sep future, so a prior day is kept only when
    its ux record (P1-04's stamp) carries today's contract key; one recorded before the stamp, or
    on another contract, is cut and named. Without a key nothing is cut."""
    _days("2026-09-29", "2026-09-30", "2026-10-01")
    tape_log._write_lines(tape_log.ux_path("2026-09-29", "NIFTY"), [{"t": 1, "ik": "NSE_FO|68407", "src": "ux"}])
    tape_log._write_lines(tape_log.ux_path("2026-09-30", "NIFTY"), [{"t": 1, "ik": "NSE_FO|48704", "src": "ux"}])
    days, why = tape_log.prior_pool("2026-10-02", "NIFTY", 5, ik="NSE_FO|48704")     # 1 Oct: no ux record at all
    assert days == ["2026-09-30"] and why == "earlier days are another contract (NSE_FO|68407, today NSE_FO|48704)"
    days, why = tape_log.prior_pool("2026-10-02", "NIFTY", 2, ik="NSE_FO|48704")     # only 1 Oct and 30 Sep in reach
    assert days == ["2026-09-30"] and why == "earlier days' contract was not recorded (before the contract stamp)"
    assert tape_log.prior_pool("2026-09-30", "NIFTY", 5, ik="NSE_FO|48704")[0] == []
    assert tape_log.prior_pool("2026-10-02", "NIFTY", 5) == (["2026-10-01", "2026-09-30", "2026-09-29"], None)


def test_two_posts_at_once_write_each_bar_once(tdir, monkeypatch):
    """25 Oct review D6 / A69: the seen-set was updated only after the write, so two frame POSTs on two server
    threads both wrote the same bars (41 duplicate rows over 8 NIFTY days)."""
    import threading
    import time
    real = tape_log._write_lines

    def slow(path, rows):
        time.sleep(0.05)                                 # widen the check-then-append window
        real(path, rows)
    monkeypatch.setattr(tape_log, "_write_lines", slow)
    doc = _doc(n=3)
    ts = [threading.Thread(target=tape_log.append, args=(doc, "2026-09-19", "NIFTY")) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    rows = _lines(tape_log.day_path("2026-09-19", "NIFTY"))
    assert sorted(r["t"] for r in rows) == sorted(b["t"] for b in doc["closed"])


def test_two_posts_at_once_write_each_marks2_row_once(tdir, monkeypatch):
    """Same race as the bars (25 Oct review D6), on the marks2 writer: on a cold start both threads seed their own
    seen-set from the file, the later one replaces the earlier, and each writes the rows. A restart is the cold start,
    so the set is cleared here and the seed read is slowed to make the threads overlap."""
    import threading
    import time
    real_read, real_write = tape_log._read, tape_log._write_lines

    def slow_read(path):
        time.sleep(0.05)                                 # widen the seed's check-then-assign window
        return real_read(path)

    def slow_write(path, rows):
        time.sleep(0.05)
        real_write(path, rows)
    monkeypatch.setattr(tape_log, "_read", slow_read)
    monkeypatch.setattr(tape_log, "_write_lines", slow_write)
    tape_log._seen_marks2.clear()
    doc = {"marks2": [{"id": f"trap@{i}", "t": 1789726200000 + i, "kind": "trap", "p": 23380.0, "status": "TIKA", "tier": "solid"}
                      for i in range(3)]}
    ts = [threading.Thread(target=tape_log.append_marks2, args=(doc, "2026-09-19", "NIFTY")) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    rows = real_read(tape_log.marks2_path("2026-09-19", "NIFTY"))
    assert sorted(r["id"] for r in rows) == ["trap@0", "trap@1", "trap@2"]
