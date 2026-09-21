# tapemap/test_book_wiring.py
"""The book record is wired into the senses loop and isolated for a mock run."""
import inspect
import json
import os

import book_log
import server
import ux_log


def test_the_senses_state_owns_one_book():
    assert isinstance(server._SENSES.get("book"), book_log.Book)
    assert server._SENSES.get("book_rows") == []


def test_coverage_names_the_book_record_with_the_three_sentences(monkeypatch):
    monkeypatch.setattr(book_log, "failed", 0)
    monkeypatch.setattr(ux_log, "failed", 0)
    monkeypatch.setitem(server._SENSES, "ux_drain_why", None)
    b = book_log.Book(day="2026-09-21")
    monkeypatch.setitem(server._SENSES, "book", b)
    c = server._coverage()["book"]
    assert c["from"] == {} and c["dropped"] == 0 and c["written"] == 0
    assert c["why"] == "no frame recorded yet this process -- feed not connected, or before the first drain"
    b.book_from["NIFTY"] = "09:15:03"
    b.written = 10
    assert server._coverage()["book"] == {"from": {"NIFTY": "09:15:03"}, "dropped": 0, "written": 10,
                                          "rebuild_why": {}, "failed": 0, "ux_failed": 0,
                                          "drain_why": None, "why": None}


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


def test_the_loop_assigns_the_hook_watches_the_futures_and_drains_outside_the_lock():
    """Source-pinned, the way test_day_state pins the isolation list: the
    three lines that make the record exist must be in the loop, in this
    order -- hook, watch, drain -- and the drain must sit AFTER the lock
    block (the drain itself, book_log.flush included, is `_ux_drain`, tested
    end to end below)."""
    src = inspect.getsource(server._senses_loop)
    i_hook = src.index("feed.on_frame = _SENSES[\"book\"].on_frame")
    i_watch = src.index("_SENSES[\"book\"].watch(idx, r.get(\"fut_key\"))")
    i_lock_end = src.index("# 5a/5b, OUTSIDE _SENSES_LOCK")
    i_drain = src.index("_ux_drain(")
    assert i_hook < i_watch < i_lock_end < i_drain


def test_ux_drain_rebuilds_before_it_flushes_before_it_feeds_the_ladder():
    src = inspect.getsource(server._ux_drain)
    i_rebuild = src.index("ux_log.rebuild(")
    i_flush = src.index(".flush(day)")
    i_onframes = src.index("ux_log.on_frames(")
    assert i_rebuild < i_flush < i_onframes


def test_ux_drain_names_a_raised_rebuild_and_still_flushes_this_pass(monkeypatch):
    """A rebuild failure must not swallow this pass's flush -- it is named on
    `rebuild_why` (item 2) and the loop moves on to drain the deque."""
    st = {"lot": None, "tick": None, "day": None, "rebuild_why": None, "runs": None, "impact": None}
    monkeypatch.setitem(server._SENSES, "ux", {"NIFTY": st})
    monkeypatch.setattr(ux_log, "rebuild", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", "FUT_KEY")
    monkeypatch.setitem(server._SENSES, "book", b)
    out = server._ux_drain("2026-09-21")
    assert out == [] and st["day"] == "2026-09-21"
    assert st["rebuild_why"] == "rebuild failed: RuntimeError: boom"
    assert server._coverage()["book"]["rebuild_why"] == {"NIFTY": "rebuild failed: RuntimeError: boom"}


def test_ux_drain_resets_runs_and_impact_even_when_ofd_lot_raises(monkeypatch):
    """A raise inside `_ofd_lot` happens BEFORE `lot` is resolved, so the old
    code path (which reset runs/impact inline, after the lot lookup) would
    leave yesterday's machines in place under `st["day"] == today`. The reset
    now lives in `finally`, so it runs regardless of where the exception
    lands."""
    import runs as runs_mod
    import impact as impact_mod
    stale_impact = impact_mod.Impact(lot=65, tick=0.05)
    stale_impact.on_frame({"t": 1, "b": [[100.0, 65]], "a": [[100.05, 65]]}, [{"q": 65, "side": 1}])
    assert stale_impact.read()["n"] == 1                # proof it is not already fresh
    st = {"lot": None, "tick": None, "day": "2026-09-20", "rebuild_why": None,
          "runs": runs_mod.Runs(lot=65), "impact": stale_impact}
    monkeypatch.setitem(server._SENSES, "ux", {"NIFTY": st})
    monkeypatch.setattr(server, "_ofd_lot", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no lot")))
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", "FUT_KEY")
    monkeypatch.setitem(server._SENSES, "book", b)
    server._ux_drain("2026-09-21")
    assert st["rebuild_why"] == "rebuild failed: RuntimeError: no lot"
    assert st["impact"] is not stale_impact and st["impact"].read()["n"] == 0
    assert st["day"] == "2026-09-21"


def test_ux_drain_names_a_failed_flush_on_drain_why_and_clears_it_on_the_next_clean_pass(monkeypatch):
    """The flush/on_frames half is the shared, per-process step -- its own
    failure is named on `ux_drain_why` (served in coverage), separate from
    any per-index `rebuild_why`, and cleared again the next time it succeeds."""
    monkeypatch.setitem(server._SENSES, "ux_drain_why", None)
    st = {"lot": 65, "tick": 0.05, "day": "2026-09-21", "rebuild_why": None, "runs": None, "impact": None}
    monkeypatch.setitem(server._SENSES, "ux", {"NIFTY": st})
    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", "FUT_KEY")
    monkeypatch.setitem(server._SENSES, "book", b)
    monkeypatch.setattr(b, "flush", lambda day=None: [("NIFTY", {"t": 1})])
    monkeypatch.setattr(ux_log, "on_frames", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = server._ux_drain("2026-09-21")
    assert out == []
    assert server._SENSES["ux_drain_why"] == "drain failed: RuntimeError: boom"
    assert server._coverage()["book"]["drain_why"] == "drain failed: RuntimeError: boom"

    monkeypatch.setattr(ux_log, "on_frames", lambda *a, **k: [])
    out2 = server._ux_drain("2026-09-21")
    assert out2 == [("NIFTY", {"t": 1})] and server._SENSES["ux_drain_why"] is None


def test_ux_drain_lands_bars_once_across_the_rebuild_flush_boundary(tmp_path, monkeypatch):
    """End to end: a book file rebuilt with the restart bin left open (`_ux_drain`
    passes `close_last=False`), then more frames drained through `on_frame`/
    `flush` on a SECOND `_ux_drain` call, landing in the SAME bin the file
    ended inside -- the ladder must continue from where the rebuild left off,
    never re-step the rebuilt frames, land that bin exactly once with BOTH
    halves in it, and runs/impact must have seen every frame."""
    import runs as runs_mod
    import impact as impact_mod
    import tape_log
    from test_ladder import R, T0
    from test_book_log import _frame, FUT

    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    ux_log._STATE.clear()

    # the rebuild half: three frames written straight to the book file, all
    # inside bin 0 -- the restart-bin fix leaves bin 0 open at file end
    # (close_last=False) instead of closing it early.
    rows = [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 2000, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 3000, 1195, 100.05, 65, [[100.00, 65]], [[100.10, 65]])]
    p = book_log.day_path("2026-09-21", "NIFTY")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))

    b = book_log.Book(day="2026-09-21")
    b.watch("NIFTY", FUT)
    monkeypatch.setitem(server._SENSES, "book", b)
    st = {"lot": 65, "tick": 0.05, "day": None, "rebuild_why": None,
          "runs": runs_mod.Runs(lot=65), "impact": impact_mod.Impact(lot=65, tick=0.05)}
    monkeypatch.setitem(server._SENSES, "ux", {"NIFTY": st})

    out1 = server._ux_drain("2026-09-21")
    assert out1 == []                                  # nothing in the deque yet
    assert ux_log.read_bars("2026-09-21", "NIFTY") == []     # bin 0 left open, not landed
    assert ux_log.forming("NIFTY", "2026-09-21")["t"] == T0

    # the flush half: one frame still inside bin 0, then one that crosses into
    # bin 1 and so closes bin 0 -- must NOT trigger a second rebuild
    # (st["day"] is already today).
    b.on_frame(FUT, _frame(vtt=1260, ltp=100.10, ltq=65, ltt=T0 + 150_000,
                           bids=((100.05, 65),), asks=((100.15, 65),)), now_ms=T0 + 150_000)
    b.on_frame(FUT, _frame(vtt=1325, ltp=100.15, ltq=65, ltt=T0 + 300_100,
                           bids=((100.10, 65),), asks=((100.20, 65),)), now_ms=T0 + 300_100)
    out2 = server._ux_drain("2026-09-21")
    assert [idx for idx, _ in out2] == ["NIFTY", "NIFTY"]     # the two flushed rows

    bars = ux_log.read_bars("2026-09-21", "NIFTY")
    assert [bar["t"] for bar in bars] == [T0]           # bin 0 landed exactly once, not re-stepped
    landed = bars[0]
    assert landed["frames"] == 4                        # 3 file rows + the one live frame still inside bin 0
    assert landed["vol"] == 4.0 and landed["partial"] is False   # file's two trades plus the live one, in lots
    assert st["impact"].read()["n"] > 0                 # every frame reached the gauge
    assert st["runs"].window_n > 0                      # every fill reached the run detector

    bars = ux_log.read_bars("2026-09-21", "NIFTY")
    assert [bar["t"] for bar in bars] == [T0]           # bin 0 landed exactly once, not re-stepped
    assert st["impact"].read()["n"] > 0                 # every frame reached the gauge
    assert st["runs"].window_n > 0                      # every fill reached the run detector


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
