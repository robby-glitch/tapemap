"""The leak guard (pro-tool P1-01): no test can reach data/. conftest.py's autouse fixture
redirects every forward-record writer to tmp_path, and server._isolate_mock_writers keeps
the same list under data/mock/ for a --mock-chain run. Both lists are checked here, so a
writer added to one and forgotten in the other fails a test instead of writing the record."""
import importlib
import os

import pytest

import conftest
import server


def _get(target):
    mod, attr = target.rsplit(".", 1)
    return getattr(importlib.import_module(mod), attr)


@pytest.mark.parametrize("target", sorted(conftest.STR_PATHS) + sorted(conftest.PATH_PATHS))
def test_every_writer_resolves_under_tmp_path(target, tmp_path):
    p = os.path.normpath(str(_get(target)))
    assert p.startswith(os.path.normpath(str(tmp_path))), f"{target} = {p}"
    assert os.sep + "data" + os.sep not in p[len(str(tmp_path)):], target


def test_the_mock_run_keeps_every_writer_under_data_mock():
    """The autouse fixture's teardown restores every attribute this call rewrites."""
    server._isolate_mock_writers()
    mock = os.path.normpath(os.path.join("data", "mock"))
    for target in sorted(conftest.STR_PATHS) + sorted(conftest.PATH_PATHS):
        if target in ("upstox_instruments.CACHE_FMT", "instruments.SCRIP_CACHE"):   # instrument caches, not records: read-only for a mock run
            continue
        p = os.path.normpath(str(_get(target)))
        assert mock in p and not p.endswith(mock), f"{target} = {p}"
