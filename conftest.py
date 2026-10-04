# tapemap/conftest.py
"""Every test runs with the ladder record pointed at a temp dir.

THE LEAK (2026-09-19): server.do_POST now writes each posted bar to
tape_log.DIR (data/tape/, the live forward record). A pre-existing route
test that posts a toy doc without redirecting DIR wrote three toy rows into
the real record -- the same class of incident as the 2026-08-24 replay leak
(server._isolate_mock_writers). One autouse fixture, so no test can ever
reach data/tape/ by forgetting a monkeypatch; tests that set DIR themselves
still win, because their monkeypatch is applied after this one.

2026-09-28 (pro-tool P1-01): EVERY forward-record writer, the same way. The
fixture had three of them; a morning test run would have written a fake marked
trade into today's day_state and a FRAMETEST stick did land in data/ that day.
The list here and the one in server._isolate_mock_writers are the same list;
test_leak_guard.py asserts each path is under tmp_path.
"""
import pytest

import tape_log
import ux_log

# module attribute -> the tmp name (monkeypatch imports each module by name).
# Strings where the module holds a string, Paths where it holds a Path.
STR_PATHS = {"tape_log.DIR": "tape", "book_log.DIR": "book", "day_state.DIR": "day_state",
             "hold_log.DIR": "hold", "calls_log.DIR": "calls", "frame_log.DIR": "frame",
             "senses.DIR": "senses", "trigger_log.PATH": "trigger_log.jsonl",
             "sequence.DIR": "warmap", "desk_log.SURF_DIR": "surface", "desk_log.DESK_LOG_PATH": "desk_log.jsonl",
             "server.VPIN_LOG": "vpin_log.jsonl", "server.VPIN_BACKFILL_LOG": "vpin_backfill.jsonl",
             "server.VPIN_FAST_LOG": "vpin_fast.jsonl",
             "chain_backfill.DIR": "chain_backfill",           # the 09:15 REST backfill on disk (pro-tool P2-06)
             "reader_live.DIR": "reader",                      # the shadow leg engine's log (docs/reader/8-shadow-build.md)
             "xindex_live.DIR": "xindex",                      # the shadow cross-index log (docs/reader/10-xindex-build.md)
             "sides_log.DIR": "sides",                         # the sides read's forward log (sides_log.py)
             "trap_log.DIR": "trap",                           # the trap layer's forward log (trap_log.py)
             # the instrument dump cache: a stale cache would be RE-FETCHED and rewritten under data/
             "upstox_instruments.CACHE_FMT": "upstox_{}.json"}
PATH_PATHS = {"chain_live.CHAIN_DIR": "chain", "live.STICK_F": "stick_state.json",
              # the Dhan scrip-master cache (a fallback path, but it lives under data/ and a stale one is re-downloaded)
              "instruments.SCRIP_CACHE": "scrip_master.csv"}


@pytest.fixture(autouse=True)
def _tape_record_in_tmp(tmp_path, monkeypatch):
    for target, name in STR_PATHS.items():
        monkeypatch.setattr(target, str(tmp_path / name))
    for target, name in PATH_PATHS.items():
        monkeypatch.setattr(target, tmp_path / name)
    # the rev 6 event log (P2-02) is being written beside this; guarded until it lands
    try:
        import fold_log
        monkeypatch.setattr(fold_log, "DIR", str(tmp_path / "fold"))
    except ImportError:
        pass
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    ux_log._STATE.clear()
    yield
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    ux_log._STATE.clear()
