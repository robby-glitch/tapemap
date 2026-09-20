# tapemap/test_book_wiring.py
"""The book record is wired into the senses loop and isolated for a mock run."""
import inspect

import book_log
import server


def test_the_senses_state_owns_one_book():
    assert isinstance(server._SENSES.get("book"), book_log.Book)
    assert server._SENSES.get("book_rows") == []


def test_coverage_names_the_book_record_with_the_three_sentences(monkeypatch):
    b = book_log.Book(day="2026-09-21")
    monkeypatch.setitem(server._SENSES, "book", b)
    c = server._coverage()["book"]
    assert c["from"] == {} and c["dropped"] == 0 and c["written"] == 0
    assert c["why"] == "no frame recorded yet this process -- feed not connected, or before the first drain"
    b.book_from["NIFTY"] = "09:15:03"
    b.written = 10
    assert server._coverage()["book"] == {"from": {"NIFTY": "09:15:03"}, "dropped": 0, "written": 10, "why": None}


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
