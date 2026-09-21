# tapemap/test_ux_log.py
"""The ux record: bars written once at bin close, rebuilt from the book on start."""
import json
import os

import book_log
import ladder
import tape_log
import ux_log
from test_ladder import R, T0


def _rows():
    return [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 2000, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 300_500, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 600_500, 1130, 100.00, 65, [[100.00, 65]], [[100.05, 65]])]


def test_on_frames_writes_each_closed_bar_once_and_returns_it_with_fills():
    out = ux_log.on_frames([("NIFTY", r) for r in _rows()], "2026-09-11", lot=65, tick=0.05)
    assert [(idx, b["t"]) for idx, b, _ in out] == [("NIFTY", T0), ("NIFTY", T0 + 300_000)]
    # the fills travel with the bar they went into: bin 0 had the one exact buy;
    # bin 1 had none (its closing frame's fill belongs to bin 2)
    assert [len(f) for _, _, f in out] == [1, 0] and out[0][2][0]["p"] == 100.05 and out[0][2][0]["side"] == 1
    bars = ux_log.read_bars("2026-09-11", "NIFTY")
    assert [b["t"] for b in bars] == [T0, T0 + 300_000] and bars[0]["src"] == "ux" and bars[0]["vol"] == 1
    assert bars[1]["vol"] == 0 and bars[1]["ladder"] == []
    st = ux_log.state("NIFTY", "2026-09-11")
    assert [b["t"] for b in st["bars"]] == [T0, T0 + 300_000] and len(st["fills"]) == 2
    # the same rows again land nothing: write-once by t
    ux_log.on_frames([("NIFTY", r) for r in _rows()], "2026-09-11", lot=65, tick=0.05)
    assert len(ux_log.read_bars("2026-09-11", "NIFTY")) == 2


def test_forming_is_the_open_bar_and_none_before_any_frame():
    assert ux_log.forming("NIFTY", "2026-09-11") is None
    ux_log.on_frames([("NIFTY", r) for r in _rows()[:2]], "2026-09-11", lot=65, tick=0.05)
    f = ux_log.forming("NIFTY", "2026-09-11")
    assert f["t"] == T0 and f["vol"] == 1 and f["src"] == "ux"
    assert ux_log.forming("NIFTY", "2026-09-11")["t"] == T0          # peeking closes nothing


def test_rebuild_streams_the_book_file_and_writes_only_missing_bins(monkeypatch):
    p = book_log.day_path("2026-09-11", "NIFTY")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        for r in _rows():
            f.write(json.dumps(r) + "\n")
    # a previous process already wrote bin 0
    ux_log.on_frames([("NIFTY", r) for r in _rows()[:3]], "2026-09-11", lot=65, tick=0.05)
    ux_log._STATE.clear()
    n = ux_log.rebuild("2026-09-11", "NIFTY", lot=65, tick=0.05)
    bars = ux_log.read_bars("2026-09-11", "NIFTY")
    assert n == 2 and [b["t"] for b in bars] == [T0, T0 + 300_000, T0 + 600_000]
    assert bars[-1]["vol"] == 1                                          # the open bin at file end, closed by rebuild
    assert ux_log.state("NIFTY", "2026-09-11")["bars"][-1]["t"] == T0 + 600_000


def test_rebuild_without_a_book_file_writes_nothing():
    assert ux_log.rebuild("2026-09-11", "NIFTY") == 0 and ux_log.read_bars("2026-09-11", "NIFTY") == []


def test_a_day_roll_starts_a_fresh_ladder():
    ux_log.on_frames([("NIFTY", _rows()[0])], "2026-09-11", lot=65, tick=0.05)
    ux_log.on_frames([("NIFTY", _rows()[0])], "2026-09-12", lot=65, tick=0.05)
    assert ux_log.state("NIFTY", "2026-09-12")["day"] == "2026-09-12"
    assert ux_log.state("NIFTY", "2026-09-12")["bars"] == []


def test_write_failure_is_counted_never_raised(monkeypatch):
    monkeypatch.setattr(ux_log, "_write_lines", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    out = ux_log.on_frames([("NIFTY", r) for r in _rows()], "2026-09-11", lot=65, tick=0.05)
    assert len(out) == 2 and ux_log.failed >= 2


def test_the_ladder_step_and_the_forming_copy_share_one_lock():
    import inspect
    assert "with _LOCK:" in inspect.getsource(ux_log.on_frames)
    assert "with _LOCK:" in inspect.getsource(ux_log.rebuild)
    assert "with _LOCK:" in inspect.getsource(ux_log.forming)
    # never across disk: _land (the writer) is not under it
    assert "_LOCK" not in inspect.getsource(ux_log._land)
