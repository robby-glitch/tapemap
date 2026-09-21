"""The book record: one compact row per frame that changed, never on the feed thread."""
import builtins
import json
import os

import book_log

FUT = "NSE_FO|58072"


def _frame(vtt=1023750, ltp=24271.7, ltq=65, ltt=1787200010000, bids=((24270.6, 65), (24270.5, 130)),
           asks=((24272.0, 65), (24272.9, 65))):
    lv = [{"bidQ": bq, "bidP": bp, "askQ": aq, "askP": ap}
          for (bp, bq), (ap, aq) in zip(bids, asks)]
    return {"fullFeed": {"marketFF": {"ltpc": {"ltp": ltp, "ltt": ltt, "ltq": ltq, "cp": 24117.6},
                                      "marketLevel": {"bidAskQuote": lv},
                                      "vtt": vtt, "oi": 12873510.0, "tbq": 168090.0, "tsq": 292630.0}}}


def test_row_of_is_the_compact_shape_best_first():
    r = book_log.row_of(_frame(), cts=1787200010500, now_ms=1787200010600)
    assert r["t"] == 1787200010600 and r["cts"] == 1787200010500
    assert r["ltt"] == 1787200010000 and r["ltp"] == 24271.7 and r["ltq"] == 65 and r["vtt"] == 1023750
    assert r["oi"] == 12873510 and r["tbq"] == 168090 and r["tsq"] == 292630
    assert r["b"] == [[24270.6, 65], [24270.5, 130]] and r["a"] == [[24272.0, 65], [24272.9, 65]]


def test_row_of_is_none_for_an_index_feed_with_no_book():
    assert book_log.row_of({"fullFeed": {"indexFF": {"ltpc": {"ltp": 24200.0}}}}) is None


def test_on_frame_ignores_unwatched_keys_and_skips_identical_frames():
    b = book_log.Book(day="2026-09-21")
    assert b.on_frame(FUT, _frame(), now_ms=1) is False          # not watched yet
    b.watch("NIFTY", FUT)
    assert b.watched() == {"NIFTY"}
    assert b.on_frame(FUT, _frame(), now_ms=2) is True
    assert b.on_frame(FUT, _frame(), now_ms=3) is False           # heartbeat: same vtt/ltp/ltq/ltt/b/a
    assert b.on_frame(FUT, _frame(vtt=1023815), now_ms=4) is True


def test_on_frame_never_touches_disk(monkeypatch):
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    def boom(*a, **k):
        raise AssertionError("on_frame opened a file")
    monkeypatch.setattr(builtins, "open", boom)
    assert b.on_frame(FUT, _frame(), now_ms=5) is True


def test_flush_writes_one_line_per_row_and_reports_book_from(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    b.on_frame(FUT, _frame(), now_ms=1787200010600)
    b.on_frame(FUT, _frame(vtt=1023815), now_ms=1787200010900)
    out = b.flush()
    assert [idx for idx, _ in out] == ["NIFTY", "NIFTY"] and b.written == 2
    rows = list(book_log.read_rows("2026-09-21", "NIFTY"))
    assert [r["t"] for r in rows] == [1787200010600, 1787200010900]
    assert b.book_from["NIFTY"] == "09:56:50"          # IST, the machine clock (server._coverage)
    assert b.flush() == []


def test_flush_after_a_restart_refuses_rows_at_or_before_the_files_last_t(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    p = book_log.day_path("2026-09-21", "NIFTY")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": 100, "vtt": 1}) + "\n" + json.dumps({"t": 200, "vtt": 2}) + "\n")
    assert book_log.last_t(p) == 200 and book_log.first_t(p) == 100
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    b.on_frame(FUT, _frame(), now_ms=200)                     # a replayed frame from before the restart
    b.on_frame(FUT, _frame(vtt=1023815), now_ms=201)
    out = b.flush()
    assert [r["t"] for _, r in out] == [201]
    assert [r["t"] for r in book_log.read_rows("2026-09-21", "NIFTY")] == [100, 200, 201]


def test_a_failed_write_never_advances_the_record_and_a_later_row_still_lands(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    b.on_frame(FUT, _frame(), now_ms=100)
    before = book_log.failed
    real_open = builtins.open
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    assert b.flush() == []
    assert book_log.failed == before + 1
    monkeypatch.setattr(builtins, "open", real_open)
    b.on_frame(FUT, _frame(vtt=1023815), now_ms=101)          # a later row
    out = b.flush()
    assert [r["t"] for _, r in out] == [101]                  # lands: `_last_t` never moved past the lost row
    assert [r["t"] for r in book_log.read_rows("2026-09-21", "NIFTY")] == [101]


def test_overflow_is_counted_not_raised(monkeypatch):
    monkeypatch.setattr(book_log, "MAXLEN", 2)
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    for i in range(4):
        b.on_frame(FUT, _frame(vtt=1023750 + 65 * i), now_ms=i)
    assert b.dropped == 2


def test_a_torn_last_line_is_skipped_by_the_reader_and_by_last_t(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    p = book_log.day_path("2026-09-21", "NIFTY")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": 100}) + "\n" + '{"t": 2')
    assert [r["t"] for r in book_log.read_rows("2026-09-21", "NIFTY")] == [100]
    assert book_log.last_t(p) == 100


def test_every_test_runs_with_the_book_record_in_a_temp_dir():
    assert os.path.isabs(book_log.DIR) and "book" in book_log.DIR       # the conftest redirect
