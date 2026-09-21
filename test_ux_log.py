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


def test_rebuild_on_the_live_path_leaves_the_last_bin_for_the_stream():
    """`close_last=False` (what `server._ux_drain` passes): the bin the book
    file ends inside is NOT landed by the rebuild -- the live stream continues
    it, and it lands once, whole, when a frame finally crosses its boundary."""
    rows = [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 2000, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 300_500, 1130, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 320_000, 1195, 100.05, 65, [[100.00, 65]], [[100.05, 65]])]
    p = book_log.day_path("2026-09-11", "NIFTY")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    n = ux_log.rebuild("2026-09-11", "NIFTY", 65, 0.05, close_last=False)
    bars = ux_log.read_bars("2026-09-11", "NIFTY")
    assert n == 1 and [b["t"] for b in bars] == [T0]
    assert ux_log.forming("NIFTY", "2026-09-11")["t"] == T0 + 300_000

    # the live stream continues bin 1 -- two more frames inside it, then one
    # in bin 2 that finally closes it.
    live = [R(T0 + 340_000, 1260, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 380_000, 1325, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 600_500, 1325, 100.05, 65, [[100.00, 65]], [[100.05, 65]])]
    ux_log.on_frames([("NIFTY", r) for r in live], "2026-09-11", lot=65, tick=0.05)
    bars = ux_log.read_bars("2026-09-11", "NIFTY")
    assert [b["t"] for b in bars] == [T0, T0 + 300_000]     # bin 1 landed exactly once
    landed = bars[1]
    # all four of bin 1's trades (1065->1130 from the file, 1130->1195,
    # 1195->1260, 1260->1325) in lots -- more than the file alone ever held
    # (it never landed bin 1 at all under close_last=False).
    assert landed["vol"] == 4.0 and landed["partial"] is False


def test_rebuild_without_a_book_file_writes_nothing():
    assert ux_log.rebuild("2026-09-11", "NIFTY") == 0 and ux_log.read_bars("2026-09-11", "NIFTY") == []


def test_a_day_roll_starts_a_fresh_ladder():
    ux_log.on_frames([("NIFTY", _rows()[0])], "2026-09-11", lot=65, tick=0.05)
    ux_log.on_frames([("NIFTY", _rows()[0])], "2026-09-12", lot=65, tick=0.05)
    assert ux_log.state("NIFTY", "2026-09-12")["day"] == "2026-09-12"
    assert ux_log.state("NIFTY", "2026-09-12")["bars"] == []


def test_read_bars_collapses_a_duplicate_t_last_row_wins():
    """A second writer (e.g. tools/gate_report.py run against a live day)
    can append a duplicate `t` -- read_bars must collapse it so no reader
    (prints.profile included) double-counts the bin."""
    p = ux_log.day_path("2026-09-11", "NIFTY")
    ux_log._write_lines(p, [{"t": T0, "vol": 1, "src": "ux"},
                            {"t": T0 + 300_000, "vol": 2, "src": "ux"},
                            {"t": T0, "vol": 9, "src": "ux"}])          # the duplicate, landed later
    bars = ux_log.read_bars("2026-09-11", "NIFTY")
    assert [b["t"] for b in bars] == [T0, T0 + 300_000]                # order of first appearance
    assert bars[0]["vol"] == 9                                         # the LAST row for that t wins


def test_write_failure_is_counted_never_raised(monkeypatch):
    monkeypatch.setattr(ux_log, "_write_lines", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    out = ux_log.on_frames([("NIFTY", r) for r in _rows()], "2026-09-11", lot=65, tick=0.05)
    assert len(out) == 2 and ux_log.failed >= 2


def test_the_ladder_step_and_the_forming_copy_survive_concurrent_readers(tmp_path, monkeypatch):
    """A writer thread steps ~2000 frames through `on_frames` while three
    reader threads call `forming` in a loop for 1.5 s -- `forming`'s deepcopy
    must never land mid-mutation of the same ladder the writer is stepping."""
    import threading
    import time as time_mod
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    ux_log._STATE.clear()
    day = "2026-09-21"

    def make_row(i):
        ltt = T0 + i * 100
        ltp = round(100.00 + (i % 7) * 0.05, 2)
        return R(ltt, 1000 + i * 65, ltp, 65, [[round(ltp - 0.05, 2), 65]], [[round(ltp + 0.05, 2), 65]], ltt=ltt)

    errors = []

    def write():
        for i in range(1, 2001):
            ux_log.on_frames([("NIFTY", make_row(i))], day, lot=65, tick=0.05)

    def read(deadline):
        while time_mod.monotonic() < deadline:
            try:
                ux_log.forming("NIFTY", day)
            except Exception as e:               # noqa: BLE001 -- any race raises here
                errors.append(e)

    deadline = time_mod.monotonic() + 1.5
    writer = threading.Thread(target=write)
    readers = [threading.Thread(target=read, args=(deadline,)) for _ in range(3)]
    writer.start()
    for r in readers:
        r.start()
    writer.join(timeout=3)
    finished = not writer.is_alive()
    for r in readers:
        r.join(timeout=3)
    assert errors == [] and finished
