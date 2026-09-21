# tapemap/test_book_wiring.py
"""The book record is wired into the senses loop and isolated for a mock run."""
import inspect

import book_log
import server
import ux_log


def test_the_senses_state_owns_one_book():
    assert isinstance(server._SENSES.get("book"), book_log.Book)
    assert server._SENSES.get("book_rows") == []


def test_coverage_names_the_book_record_with_the_three_sentences(monkeypatch):
    monkeypatch.setattr(book_log, "failed", 0)
    monkeypatch.setattr(ux_log, "failed", 0)
    b = book_log.Book(day="2026-09-21")
    monkeypatch.setitem(server._SENSES, "book", b)
    c = server._coverage()["book"]
    assert c["from"] == {} and c["dropped"] == 0 and c["written"] == 0
    assert c["why"] == "no frame recorded yet this process -- feed not connected, or before the first drain"
    b.book_from["NIFTY"] = "09:15:03"
    b.written = 10
    assert server._coverage()["book"] == {"from": {"NIFTY": "09:15:03"}, "dropped": 0, "written": 10,
                                          "rebuild_why": {}, "failed": 0, "ux_failed": 0, "why": None}


def test_coverage_carries_a_failed_rebuilds_reason_by_index(monkeypatch):
    monkeypatch.setitem(server._SENSES, "ux", {"NIFTY": {"rebuild_why": "rebuild failed: RuntimeError: boom"}})
    assert server._coverage()["book"]["rebuild_why"] == {"NIFTY": "rebuild failed: RuntimeError: boom"}


def test_coverage_carries_the_two_write_failure_counters_and_notes_them_in_why(monkeypatch):
    monkeypatch.setattr(book_log, "failed", 0)
    monkeypatch.setattr(ux_log, "failed", 0)
    b = book_log.Book(day="2026-09-21")
    monkeypatch.setitem(server._SENSES, "book", b)
    c = server._coverage()["book"]
    assert c["failed"] == 0 and c["ux_failed"] == 0
    monkeypatch.setattr(book_log, "failed", 2)
    monkeypatch.setattr(ux_log, "failed", 1)
    c2 = server._coverage()["book"]
    assert c2["failed"] == 2 and c2["ux_failed"] == 1
    assert c2["why"] == ("no frame recorded yet this process -- feed not connected, or before the first drain"
                         " — 3 row(s) lost to a write failure this process")
    b.book_from["NIFTY"] = "09:15:03"
    assert server._coverage()["book"]["why"] == "3 row(s) lost to a write failure this process"


def test_a_mock_run_cannot_write_into_the_live_book_record(monkeypatch):
    monkeypatch.setattr(book_log, "DIR", "data/book")
    server._isolate_mock_writers()
    assert book_log.DIR.replace("\\", "/") == "data/mock/book"


def test_the_loop_assigns_the_hook_watches_the_futures_and_flushes_outside_the_lock():
    """Source-pinned, the way test_day_state pins the isolation list: the four
    lines that make the record exist must be in the loop, in this order --
    hook, watch, flush -- and the flush must sit AFTER the lock block."""
    src = inspect.getsource(server._senses_loop)
    i_hook = src.index("feed.on_frame = _SENSES[\"book\"].on_frame")
    i_watch = src.index("_SENSES[\"book\"].watch(idx, r.get(\"fut_key\"))")
    i_flush = src.index("_SENSES[\"book_rows\"] = _SENSES[\"book\"].flush()")
    i_lock_end = src.index("# 5a/5b, OUTSIDE _SENSES_LOCK")
    assert i_hook < i_watch < i_lock_end < i_flush


def test_the_loop_rebuilds_on_a_new_day_before_the_flush_and_drains_into_the_ladder():
    src = inspect.getsource(server._senses_loop)
    i_rebuild = src.index("ux_log.rebuild(day, idx, lot, st[\"tick\"], lot_src=lot_src, observer=_ux_observe)")
    i_flush = src.index("_SENSES[\"book_rows\"] = _SENSES[\"book\"].flush()")
    i_drain = src.index("ux_log.on_frames(rows, day, observer=_ux_observe)")
    assert i_rebuild < i_flush < i_drain


def test_ofd_lot_reads_the_live_doc_then_the_file_then_none(tmp_path, monkeypatch):
    import tape_log
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    monkeypatch.setitem(server._SENSES, "tape", {})
    assert server._ofd_lot("NIFTY", "2026-09-21") is None       # neither doc nor file
    tape_log._write_lines(tape_log.day_path("2026-09-21", "NIFTY"), [{"t": 1, "lot": 65}])
    assert server._ofd_lot("NIFTY", "2026-09-21") == 65          # the file, no live doc
    server._SENSES["tape"]["NIFTY"] = {"doc": {"lot": 75}}
    assert server._ofd_lot("NIFTY", "2026-09-21") == 75          # the live doc wins


def test_ux_meta_falls_back_to_none_none_when_the_slice_cannot_be_read(monkeypatch):
    import upstox_instruments
    monkeypatch.setattr(upstox_instruments, "lot_tick", lambda name: (_ for _ in ()).throw(RuntimeError("no dump")))
    server._SENSES["ux"].clear()
    st = server._ux_meta("NIFTY")
    assert st["lot"] is None and st["tick"] is None and st["runs"].lot is None
