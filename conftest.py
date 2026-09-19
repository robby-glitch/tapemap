# tapemap/conftest.py
"""Every test runs with the ladder record pointed at a temp dir.

THE LEAK (2026-09-19): server.do_POST now writes each posted bar to
tape_log.DIR (data/tape/, the live forward record). A pre-existing route
test that posts a toy doc without redirecting DIR wrote three toy rows into
the real record -- the same class of incident as the 2026-08-24 replay leak
(server._isolate_mock_writers). One autouse fixture, so no test can ever
reach data/tape/ by forgetting a monkeypatch; tests that set DIR themselves
still win, because their monkeypatch is applied after this one.
"""
import pytest

import tape_log


@pytest.fixture(autouse=True)
def _tape_record_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    yield
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
